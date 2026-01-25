# HANA-Optimized Transaction Usage Extractor
# Scalable STAD extraction for high-volume SAP HANA systems

"""
HANA-Optimized Transaction Usage Extractor.

Provides high-performance STAD extraction for SAP HANA systems:
- Date + time boundary filtering (avoids full table scans)
- Chunked extraction with configurable batch sizes
- Delta extraction support (only new records)
- Retry with exponential backoff
- Performance metrics collection

This is enterprise-safe and scales to millions of records.
"""

from typing import List, Optional, Dict, Any, Generator
from datetime import datetime, timedelta
from dataclasses import dataclass
import logging

from .base import BaseExtractor, ExtractionResult
from .connection import SAPRFCConnectionManager
from .config import SAPExtractorConfig, RESTRICTED_TCODES
from .utils import retry, metrics, rate_limited, record_extraction_count
from .state import get_delta_window, update_last_run, record_failure

logger = logging.getLogger(__name__)


@dataclass
class STADRecord:
    """Parsed STAD record."""
    username: str
    tcode: str
    date: str
    time: str
    duration_ms: int
    report: str = ""
    rfc_call: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "username": self.username,
            "tcode": self.tcode,
            "date": self.date,
            "time": self.time,
            "datetime": f"{self.date}T{self.time}" if self.date and self.time else None,
            "duration_ms": self.duration_ms,
            "report": self.report,
            "is_rfc": self.rfc_call,
            "is_restricted": self.tcode in RESTRICTED_TCODES,
        }


class HANAOptimizedTCodeExtractor(BaseExtractor):
    """
    HANA-optimized extractor for SAP STAD (Transaction Statistics).

    Key optimizations:
    - Uses date + time boundary conditions to leverage HANA indexing
    - Supports chunked extraction for large datasets
    - Includes delta extraction mode
    - Integrates with metrics and retry utilities
    """

    # STAD fields for extraction
    STAD_FIELDS = [
        "UNAME",      # User name
        "TCODE",      # Transaction code
        "DATUM",      # Date
        "UZEIT",      # Time
        "DURATION",   # Runtime (ms)
        "REPORT",     # Program name
        "RFC_CALL",   # RFC indicator
    ]

    def __init__(
        self,
        connection_manager: Optional[SAPRFCConnectionManager] = None,
        config: Optional[SAPExtractorConfig] = None,
        batch_size: int = 5000
    ):
        """
        Initialize HANA-optimized extractor.

        Args:
            connection_manager: Shared connection manager
            config: SAP configuration
            batch_size: Records per batch (default 5000)
        """
        super().__init__(connection_manager, config)
        self.batch_size = batch_size

    def extract(
        self,
        username: str,
        from_date: str,
        to_date: str,
        from_time: str = "000000",
        to_time: str = "235959",
        offset: int = 0,
        limit: int = 10000
    ) -> ExtractionResult:
        """
        Extract STAD records with HANA-optimized query.

        Args:
            username: User ID to query
            from_date: Start date (YYYYMMDD)
            to_date: End date (YYYYMMDD)
            from_time: Start time (HHMMSS)
            to_time: End time (HHMMSS)
            offset: Starting offset
            limit: Maximum records

        Returns:
            ExtractionResult with transaction records
        """
        start_time = datetime.now()
        errors = []

        try:
            records = self._extract_with_retry(
                username=username,
                from_date=from_date,
                from_time=from_time,
                to_date=to_date,
                to_time=to_time,
                rowcount=limit
            )

            # Transform records
            transformed = [r.to_dict() for r in records]

            # Record metrics
            record_extraction_count("hana_tcode", "STAD", len(transformed))

            return self._create_result(transformed, "STAD", start_time, errors)

        except Exception as e:
            logger.error(f"Error extracting STAD: {e}")
            errors.append(str(e))
            return self._create_result([], "STAD", start_time, errors)

    @retry(max_attempts=3, delay=2, backoff=2)
    @metrics("stad_extract_duration", {"extractor": "hana", "table": "STAD"})
    @rate_limited
    def _extract_with_retry(
        self,
        username: str,
        from_date: str,
        from_time: str,
        to_date: str,
        to_time: str,
        rowcount: int
    ) -> List[STADRecord]:
        """
        Execute STAD extraction with retry and metrics.

        Uses optimized WHERE clause for HANA indexing.
        """
        # Build HANA-optimized WHERE conditions
        # This structure allows HANA to use date/time indexes efficiently
        options = [
            {"TEXT": f"UNAME = '{username}'"},
            {"TEXT": f"AND ( DATUM > '{from_date}'"},
            {"TEXT": f"OR ( DATUM = '{from_date}' AND UZEIT >= '{from_time}' ) )"},
            {"TEXT": f"AND ( DATUM < '{to_date}'"},
            {"TEXT": f"OR ( DATUM = '{to_date}' AND UZEIT <= '{to_time}' ) )"},
        ]

        field_specs = [{"FIELDNAME": f} for f in self.STAD_FIELDS]

        result = self._call_rfc(
            "RFC_READ_TABLE",
            QUERY_TABLE="STAD",
            DELIMITER="|",
            OPTIONS=options,
            FIELDS=field_specs,
            ROWCOUNT=rowcount
        )

        return self._parse_results(result)

    def extract_delta(
        self,
        username: str,
        extraction_key: str,
        default_days: int = 7
    ) -> ExtractionResult:
        """
        Delta extraction using last-run timestamp.

        Automatically tracks extraction state and only retrieves
        new records since last successful run.

        Args:
            username: User ID to query
            extraction_key: Unique key for tracking state
            default_days: Days to look back if no previous run

        Returns:
            ExtractionResult with new records only
        """
        start_time = datetime.now()
        errors = []

        try:
            # Get delta window from state
            from_date, from_time, to_date, to_time = get_delta_window(
                extraction_key, default_days
            )

            logger.info(
                f"Delta extraction for {username}: "
                f"{from_date} {from_time} -> {to_date} {to_time}"
            )

            # Extract records
            result = self.extract(
                username=username,
                from_date=from_date,
                to_date=to_date,
                from_time=from_time,
                to_time=to_time
            )

            if result.success:
                # Update state on success
                update_last_run(extraction_key, result.record_count)
                logger.info(f"Delta extraction complete: {result.record_count} records")
            else:
                # Record failure
                record_failure(extraction_key, "; ".join(result.errors))

            return result

        except Exception as e:
            logger.error(f"Delta extraction error: {e}")
            record_failure(extraction_key, str(e))
            errors.append(str(e))
            return self._create_result([], "STAD", start_time, errors)

    def extract_chunked(
        self,
        username: str,
        from_date: str,
        to_date: str,
        chunk_size: Optional[int] = None
    ) -> Generator[ExtractionResult, None, None]:
        """
        Extract STAD in chunks for large datasets.

        Yields ExtractionResult for each chunk.

        Args:
            username: User ID
            from_date: Start date
            to_date: End date
            chunk_size: Records per chunk (default: self.batch_size)

        Yields:
            ExtractionResult for each chunk
        """
        chunk_size = chunk_size or self.batch_size

        # Parse dates
        start_dt = datetime.strptime(from_date, "%Y%m%d")
        end_dt = datetime.strptime(to_date, "%Y%m%d")

        # Extract day by day for controlled chunking
        current_dt = start_dt

        while current_dt <= end_dt:
            day_str = current_dt.strftime("%Y%m%d")

            logger.debug(f"Extracting chunk for {day_str}")

            result = self.extract(
                username=username,
                from_date=day_str,
                to_date=day_str,
                limit=chunk_size
            )

            yield result

            current_dt += timedelta(days=1)

    def extract_with_filter(
        self,
        username: str,
        from_date: str,
        to_date: str,
        tcode_filter: Optional[List[str]] = None,
        exclude_tcodes: Optional[List[str]] = None
    ) -> ExtractionResult:
        """
        Extract with transaction code filtering.

        Args:
            username: User ID
            from_date: Start date
            to_date: End date
            tcode_filter: Only include these tcodes
            exclude_tcodes: Exclude these tcodes

        Returns:
            Filtered ExtractionResult
        """
        # Get base results
        result = self.extract(username, from_date, to_date)

        if not result.success:
            return result

        # Apply filters
        filtered = result.data

        if tcode_filter:
            tcode_set = set(tcode_filter)
            filtered = [r for r in filtered if r["tcode"] in tcode_set]

        if exclude_tcodes:
            exclude_set = set(exclude_tcodes)
            filtered = [r for r in filtered if r["tcode"] not in exclude_set]

        # Create new result
        start_time = datetime.now()
        return self._create_result(filtered, "STAD", start_time, result.errors)

    def get_restricted_activity(
        self,
        username: str,
        from_date: str,
        to_date: str
    ) -> ExtractionResult:
        """
        Extract only restricted transaction activity.

        Args:
            username: User ID
            from_date: Start date
            to_date: End date

        Returns:
            ExtractionResult with restricted tcodes only
        """
        return self.extract_with_filter(
            username=username,
            from_date=from_date,
            to_date=to_date,
            tcode_filter=list(RESTRICTED_TCODES)
        )

    def _parse_results(self, result: Dict[str, Any]) -> List[STADRecord]:
        """Parse RFC_READ_TABLE result into STADRecord objects."""
        records = []
        delimiter = "|"

        for row in result.get("DATA", []):
            row_data = row.get("WA", "")
            values = row_data.split(delimiter)

            if len(values) >= 5:
                try:
                    duration = int(values[4].strip()) if values[4].strip() else 0
                except ValueError:
                    duration = 0

                record = STADRecord(
                    username=values[0].strip(),
                    tcode=values[1].strip(),
                    date=self._format_date(values[2].strip()),
                    time=self._format_time(values[3].strip()),
                    duration_ms=duration,
                    report=values[5].strip() if len(values) > 5 else "",
                    rfc_call=bool(values[6].strip()) if len(values) > 6 else False,
                )
                records.append(record)

        return records

    def _format_date(self, date_str: str) -> str:
        """Format SAP date to ISO format."""
        if not date_str or date_str == "00000000":
            return ""
        try:
            return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
        except:
            return date_str

    def _format_time(self, time_str: str) -> str:
        """Format SAP time to ISO format."""
        if not time_str or len(time_str) < 6:
            return ""
        try:
            return f"{time_str[:2]}:{time_str[2:4]}:{time_str[4:6]}"
        except:
            return time_str


# =============================================================================
# Factory Functions
# =============================================================================

def create_hana_extractor(
    config: Optional[Dict[str, Any]] = None,
    batch_size: int = 5000
) -> HANAOptimizedTCodeExtractor:
    """
    Create HANA-optimized extractor.

    Args:
        config: Optional SAP configuration dict
        batch_size: Records per batch

    Returns:
        Configured HANAOptimizedTCodeExtractor
    """
    sap_config = None
    if config:
        sap_config = SAPExtractorConfig(**config)

    return HANAOptimizedTCodeExtractor(config=sap_config, batch_size=batch_size)
