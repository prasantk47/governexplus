# Base Extractor Class
# Foundation for all GOVERNEX+ SAP RFC extractors

"""
Base extractor class providing common functionality for all SAP data extractors.

Features:
- Automatic connection management
- Result parsing and transformation
- Error handling and logging
- Batch processing support
- Audit trail generation
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Generator
from datetime import datetime
from dataclasses import dataclass, field
import logging
import hashlib
import json

from .connection import SAPRFCConnectionManager
from .config import SAPExtractorConfig

logger = logging.getLogger(__name__)


@dataclass
class ExtractionResult:
    """
    Result of an extraction operation.

    Attributes:
        success: Whether extraction succeeded
        data: Extracted data (list of records)
        record_count: Number of records extracted
        extraction_time: Timestamp of extraction
        duration_ms: Duration of extraction in milliseconds
        source_table: SAP source table
        checksum: SHA256 hash of data for integrity verification
        errors: List of errors if any
    """
    success: bool
    data: List[Dict[str, Any]]
    record_count: int
    extraction_time: datetime
    duration_ms: int
    source_table: str
    checksum: str = ""
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "success": self.success,
            "record_count": self.record_count,
            "extraction_time": self.extraction_time.isoformat(),
            "duration_ms": self.duration_ms,
            "source_table": self.source_table,
            "checksum": self.checksum,
            "errors": self.errors,
            "data": self.data,
        }


class BaseExtractor(ABC):
    """
    Abstract base class for SAP RFC extractors.

    All extractors inherit from this class and implement the extract() method.
    """

    def __init__(
        self,
        connection_manager: Optional[SAPRFCConnectionManager] = None,
        config: Optional[SAPExtractorConfig] = None
    ):
        """
        Initialize extractor.

        Args:
            connection_manager: Shared connection manager (creates new if not provided)
            config: Configuration for new connection manager
        """
        if connection_manager:
            self.conn_manager = connection_manager
        else:
            self.conn_manager = SAPRFCConnectionManager(config)

    @abstractmethod
    def extract(self, **kwargs) -> ExtractionResult:
        """
        Execute extraction.

        Must be implemented by subclasses.
        """
        pass

    def _call_rfc(self, function_name: str, **kwargs) -> Dict[str, Any]:
        """Execute RFC call through connection manager."""
        return self.conn_manager.call(function_name, **kwargs)

    def _read_table(
        self,
        table_name: str,
        fields: List[str],
        where_clauses: Optional[List[str]] = None,
        max_rows: int = 10000,
        delimiter: str = "|"
    ) -> List[Dict[str, Any]]:
        """
        Read data from SAP table using RFC_READ_TABLE.

        Args:
            table_name: SAP table name (e.g., USR02, AGR_USERS)
            fields: List of field names to retrieve
            where_clauses: Optional WHERE conditions
            max_rows: Maximum rows to retrieve
            delimiter: Field delimiter

        Returns:
            List of dictionaries with field values
        """
        options = []
        if where_clauses:
            for clause in where_clauses:
                options.append({"TEXT": clause})

        field_specs = [{"FIELDNAME": f} for f in fields]

        result = self._call_rfc(
            "RFC_READ_TABLE",
            QUERY_TABLE=table_name,
            DELIMITER=delimiter,
            OPTIONS=options,
            FIELDS=field_specs,
            ROWCOUNT=max_rows
        )

        return self._parse_table_result(result, fields, delimiter)

    def _parse_table_result(
        self,
        result: Dict[str, Any],
        fields: List[str],
        delimiter: str = "|"
    ) -> List[Dict[str, Any]]:
        """Parse RFC_READ_TABLE result into list of dictionaries."""
        records = []
        data_rows = result.get("DATA", [])

        for row in data_rows:
            row_data = row.get("WA", "")
            values = row_data.split(delimiter)

            record = {}
            for i, field_name in enumerate(fields):
                if i < len(values):
                    record[field_name] = values[i].strip()
                else:
                    record[field_name] = ""

            records.append(record)

        return records

    def _calculate_checksum(self, data: List[Dict]) -> str:
        """Calculate SHA256 checksum of extracted data."""
        data_str = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(data_str.encode()).hexdigest()

    def _create_result(
        self,
        data: List[Dict],
        source_table: str,
        start_time: datetime,
        errors: Optional[List[str]] = None
    ) -> ExtractionResult:
        """Create extraction result with metadata."""
        end_time = datetime.now()
        duration_ms = int((end_time - start_time).total_seconds() * 1000)

        return ExtractionResult(
            success=not errors,
            data=data,
            record_count=len(data),
            extraction_time=end_time,
            duration_ms=duration_ms,
            source_table=source_table,
            checksum=self._calculate_checksum(data),
            errors=errors or []
        )

    def extract_batched(
        self,
        batch_size: int = 1000,
        **kwargs
    ) -> Generator[ExtractionResult, None, None]:
        """
        Extract data in batches.

        Yields ExtractionResult for each batch.

        Args:
            batch_size: Records per batch
            **kwargs: Additional extraction parameters
        """
        offset = 0
        while True:
            result = self.extract(offset=offset, limit=batch_size, **kwargs)
            yield result

            if result.record_count < batch_size:
                break

            offset += batch_size

    def _format_date(self, date_str: str) -> Optional[str]:
        """
        Convert SAP date format (YYYYMMDD) to ISO format.

        Args:
            date_str: Date in YYYYMMDD format

        Returns:
            Date in ISO format (YYYY-MM-DD) or None if invalid
        """
        if not date_str or date_str == "00000000":
            return None

        try:
            return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
        except:
            return None

    def _format_time(self, time_str: str) -> Optional[str]:
        """
        Convert SAP time format (HHMMSS) to ISO format.

        Args:
            time_str: Time in HHMMSS format

        Returns:
            Time in ISO format (HH:MM:SS) or None if invalid
        """
        if not time_str or len(time_str) < 6:
            return None

        try:
            return f"{time_str[:2]}:{time_str[2:4]}:{time_str[4:6]}"
        except:
            return None

    def _format_datetime(self, date_str: str, time_str: str) -> Optional[str]:
        """
        Combine SAP date and time into ISO datetime.

        Args:
            date_str: Date in YYYYMMDD format
            time_str: Time in HHMMSS format

        Returns:
            ISO datetime string or None if invalid
        """
        date_part = self._format_date(date_str)
        time_part = self._format_time(time_str)

        if date_part and time_part:
            return f"{date_part}T{time_part}"
        return date_part

    def _parse_lock_status(self, uflag: str) -> Dict[str, bool]:
        """
        Parse SAP lock status flags (UFLAG from USR02).

        Args:
            uflag: Lock status value

        Returns:
            Dictionary with lock status details
        """
        try:
            flag_value = int(uflag) if uflag else 0
        except ValueError:
            flag_value = 0

        return {
            "locked": flag_value != 0,
            "admin_lock": bool(flag_value & 64),      # Bit 6: Administrator lock
            "wrong_password": bool(flag_value & 128), # Bit 7: Wrong password lock
            "no_user_pwd": bool(flag_value & 32),     # Bit 5: No user password
            "global_lock": bool(flag_value & 16),     # Bit 4: Global lock
        }
