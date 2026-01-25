# Security Audit Log Extractor
# Extracts from SAP Security Audit Log (SM20) for GOVERNEX+ Firefighter

"""
Security Audit Log Extractor for SAP SM20/RSAU data.

Source: Security Audit Log
Transaction: SM20
Function Module: RSAU_READ_LOG

Fields:
- AUDIT_CLASS: Event class (LOGON, LOGOFF, TCODE, etc.)
- USER: User ID
- TERMINAL: Client IP/terminal
- DATE: Log date
- TIME: Log time
- MESSAGE: Event message

Used by GOVERNEX+ for:
- Session start/end timeline reconstruction
- Logon/logoff event tracking
- Security event correlation
- Failed logon attempts monitoring
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
import logging

from .base import BaseExtractor, ExtractionResult
from .connection import SAPRFCConnectionManager
from .config import SAPExtractorConfig

logger = logging.getLogger(__name__)


@dataclass
class SessionWindow:
    """
    Represents a firefighter session window from audit log.

    Derived from LOGON/LOGOFF events in security audit log.
    """
    user: str
    logon_time: datetime
    logoff_time: Optional[datetime]
    terminal: str
    duration_minutes: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user": self.user,
            "logon_time": self.logon_time.isoformat() if self.logon_time else None,
            "logoff_time": self.logoff_time.isoformat() if self.logoff_time else None,
            "terminal": self.terminal,
            "duration_minutes": self.duration_minutes,
            "is_complete": self.logoff_time is not None,
        }


class SecurityAuditLogExtractor(BaseExtractor):
    """
    Extractor for SAP Security Audit Log (SM20).

    Uses RSAU_READ_LOG RFC function to read security events.
    """

    # Common audit event classes
    EVENT_CLASSES = {
        "AU1": "Logon successful",
        "AU2": "Logoff",
        "AU3": "Transaction start",
        "AU4": "Report start",
        "AU5": "RFC/CPIC logon",
        "AU6": "RFC function call",
        "AU7": "User master change",
        "AU8": "User master deletion",
        "AU9": "User locked",
        "AUA": "Wrong password",
        "AUB": "User unlocked",
        "AUC": "Successful RFC call",
        "AUD": "Failed RFC call",
        "AUE": "Failed transaction",
        "AUF": "Successful file access",
        "AUG": "Failed file access",
        "AUH": "Changed system settings",
        "AUI": "Read system settings",
        "AUJ": "Other security event",
        "AUK": "HTTP/HTTPS",
        "AUL": "Generic table access",
        "AUM": "Program start (debugging)",
        "AUN": "Authority check",
    }

    def __init__(
        self,
        connection_manager: Optional[SAPRFCConnectionManager] = None,
        config: Optional[SAPExtractorConfig] = None
    ):
        super().__init__(connection_manager, config)

    def extract(
        self,
        from_date: str,
        to_date: str,
        username: Optional[str] = None,
        event_class: Optional[str] = None,
        offset: int = 0,
        limit: int = 10000
    ) -> ExtractionResult:
        """
        Extract security audit log entries.

        Args:
            from_date: Start date (YYYYMMDD format)
            to_date: End date (YYYYMMDD format)
            username: Filter by specific user
            event_class: Filter by event class (AU1, AU2, etc.)
            offset: Starting offset for pagination
            limit: Maximum records to return

        Returns:
            ExtractionResult with audit log entries
        """
        start_time = datetime.now()
        errors = []

        try:
            # Call RSAU_READ_LOG
            result = self._call_rfc(
                "RSAU_READ_LOG",
                FROM_DATE=from_date,
                TO_DATE=to_date
            )

            log_data = result.get("LOG_DATA", [])

            # Transform and filter
            entries = []
            for entry in log_data:
                log_entry = self._transform_log_entry(entry)

                # Apply filters
                if username and log_entry["user"] != username:
                    continue
                if event_class and log_entry["event_code"] != event_class:
                    continue

                entries.append(log_entry)

            # Apply pagination
            paginated = entries[offset:offset + limit]

            return self._create_result(paginated, "RSAU_LOG", start_time, errors)

        except Exception as e:
            logger.error(f"Error extracting security audit log: {e}")
            errors.append(str(e))
            return self._create_result([], "RSAU_LOG", start_time, errors)

    def get_logon_events(
        self,
        from_date: str,
        to_date: str,
        username: Optional[str] = None
    ) -> ExtractionResult:
        """
        Extract only logon/logoff events.

        Args:
            from_date: Start date (YYYYMMDD format)
            to_date: End date (YYYYMMDD format)
            username: Filter by specific user

        Returns:
            ExtractionResult with logon/logoff events
        """
        start_time = datetime.now()
        errors = []

        try:
            # Get all audit log entries
            result = self.extract(from_date, to_date, username)

            # Filter for logon/logoff events
            logon_events = []
            for entry in result.data:
                if entry["event_code"] in ["AU1", "AU2", "AU5", "AUA"]:
                    entry["event_type"] = self._classify_logon_event(entry["event_code"])
                    logon_events.append(entry)

            return self._create_result(logon_events, "RSAU_LOG", start_time, errors)

        except Exception as e:
            logger.error(f"Error extracting logon events: {e}")
            errors.append(str(e))
            return self._create_result([], "RSAU_LOG", start_time, errors)

    def get_session_windows(
        self,
        from_date: str,
        to_date: str,
        username: str
    ) -> List[SessionWindow]:
        """
        Reconstruct session windows from logon/logoff events.

        Matches LOGON events with corresponding LOGOFF events
        to determine session duration.

        Args:
            from_date: Start date (YYYYMMDD format)
            to_date: End date (YYYYMMDD format)
            username: User ID to analyze

        Returns:
            List of SessionWindow objects
        """
        try:
            # Get logon events
            logon_result = self.get_logon_events(from_date, to_date, username)

            # Separate logons and logoffs
            logons = [e for e in logon_result.data if e["event_code"] == "AU1"]
            logoffs = [e for e in logon_result.data if e["event_code"] == "AU2"]

            # Match logons with logoffs
            sessions = []
            used_logoffs = set()

            for logon in logons:
                logon_dt = self._parse_event_datetime(logon)
                terminal = logon.get("terminal", "")

                # Find matching logoff (same terminal, after logon)
                matching_logoff = None
                for i, logoff in enumerate(logoffs):
                    if i in used_logoffs:
                        continue

                    logoff_dt = self._parse_event_datetime(logoff)
                    if logoff_dt and logon_dt and logoff_dt > logon_dt:
                        if logoff.get("terminal", "") == terminal:
                            matching_logoff = logoff
                            used_logoffs.add(i)
                            break

                # Create session window
                session = SessionWindow(
                    user=username,
                    logon_time=logon_dt,
                    logoff_time=self._parse_event_datetime(matching_logoff) if matching_logoff else None,
                    terminal=terminal,
                )

                # Calculate duration
                if session.logon_time and session.logoff_time:
                    duration = session.logoff_time - session.logon_time
                    session.duration_minutes = int(duration.total_seconds() / 60)

                sessions.append(session)

            return sessions

        except Exception as e:
            logger.error(f"Error reconstructing session windows: {e}")
            return []

    def get_failed_logons(
        self,
        from_date: str,
        to_date: str,
        username: Optional[str] = None
    ) -> ExtractionResult:
        """
        Extract failed logon attempts.

        Args:
            from_date: Start date (YYYYMMDD format)
            to_date: End date (YYYYMMDD format)
            username: Filter by specific user

        Returns:
            ExtractionResult with failed logon attempts
        """
        start_time = datetime.now()
        errors = []

        try:
            result = self.extract(from_date, to_date, username)

            failed_logons = []
            for entry in result.data:
                if entry["event_code"] == "AUA":  # Wrong password
                    entry["failure_reason"] = "Wrong password"
                    failed_logons.append(entry)

            return self._create_result(failed_logons, "RSAU_LOG", start_time, errors)

        except Exception as e:
            logger.error(f"Error extracting failed logons: {e}")
            errors.append(str(e))
            return self._create_result([], "RSAU_LOG", start_time, errors)

    def get_security_events(
        self,
        from_date: str,
        to_date: str,
        username: str,
        include_events: Optional[List[str]] = None
    ) -> ExtractionResult:
        """
        Extract security-relevant events for a user.

        Args:
            from_date: Start date
            to_date: End date
            username: User to analyze
            include_events: List of event codes to include (None = all)

        Returns:
            ExtractionResult with security events
        """
        start_time = datetime.now()
        errors = []

        # Default sensitive events
        if include_events is None:
            include_events = [
                "AU1",  # Logon
                "AU2",  # Logoff
                "AU3",  # Transaction start
                "AU7",  # User master change
                "AU9",  # User locked
                "AUA",  # Wrong password
                "AUB",  # User unlocked
                "AUH",  # Changed system settings
                "AUL",  # Generic table access
            ]

        try:
            result = self.extract(from_date, to_date, username)

            security_events = []
            for entry in result.data:
                if entry["event_code"] in include_events:
                    entry["security_classification"] = self._classify_security_event(
                        entry["event_code"]
                    )
                    security_events.append(entry)

            return self._create_result(security_events, "RSAU_LOG", start_time, errors)

        except Exception as e:
            logger.error(f"Error extracting security events: {e}")
            errors.append(str(e))
            return self._create_result([], "RSAU_LOG", start_time, errors)

    def _transform_log_entry(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        """Transform raw audit log entry to structured format."""
        event_code = raw.get("EVENT", raw.get("AUDIT_CLASS", ""))

        return {
            "user": raw.get("USER", ""),
            "event_code": event_code,
            "event_description": self.EVENT_CLASSES.get(event_code, "Unknown event"),
            "date": self._format_date(raw.get("DATE", "")),
            "time": self._format_time(raw.get("TIME", "")),
            "datetime": self._format_datetime(raw.get("DATE", ""), raw.get("TIME", "")),
            "terminal": raw.get("TERMINAL", ""),
            "message": raw.get("MESSAGE", ""),
            "transaction": raw.get("TCODE", ""),
            "program": raw.get("REPORT", ""),
        }

    def _classify_logon_event(self, event_code: str) -> str:
        """Classify logon event type."""
        classifications = {
            "AU1": "logon_success",
            "AU2": "logoff",
            "AU5": "rfc_logon",
            "AUA": "logon_failed",
        }
        return classifications.get(event_code, "unknown")

    def _classify_security_event(self, event_code: str) -> str:
        """Classify security level of event."""
        high_risk = ["AU7", "AU9", "AUB", "AUH"]
        medium_risk = ["AU3", "AUL", "AUA"]

        if event_code in high_risk:
            return "high"
        elif event_code in medium_risk:
            return "medium"
        else:
            return "low"

    def _parse_event_datetime(self, event: Optional[Dict]) -> Optional[datetime]:
        """Parse event datetime into Python datetime object."""
        if not event:
            return None

        dt_str = event.get("datetime")
        if not dt_str:
            return None

        try:
            return datetime.fromisoformat(dt_str)
        except:
            return None
