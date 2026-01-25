# Transaction Usage Extractor
# Extracts from SAP STAD table for GOVERNEX+ Firefighter

"""
Transaction Usage Extractor for SAP STAD (Statistic Records).

Source Table: STAD
Fields:
- UNAME: User ID
- TCODE: Transaction code
- REPORT: Program/report name
- DATUM: Date
- UZEIT: Time
- DURATION: Runtime in milliseconds
- RFC_CALL: RFC indicator

Used by GOVERNEX+ for:
- Execution tracking during firefighter sessions
- Deep audit trail of all transactions
- Anomaly detection (duration analysis)
- Attribution of activities to session windows
"""

from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from collections import Counter
import logging

from .base import BaseExtractor, ExtractionResult
from .connection import SAPRFCConnectionManager
from .config import SAPExtractorConfig, RESTRICTED_TCODES, SENSITIVE_TABLES

logger = logging.getLogger(__name__)


class TransactionUsageExtractor(BaseExtractor):
    """
    Extractor for SAP STAD (Transaction Usage Statistics).

    Provides detailed execution tracking for audit purposes.
    """

    # STAD fields for extraction
    STAD_FIELDS = [
        "UNAME",      # User name
        "TCODE",      # Transaction code
        "REPORT",     # Program name
        "DATUM",      # Date
        "UZEIT",      # Time
        "DURATION",   # Runtime (ms)
        "RFC_CALL",   # RFC indicator
    ]

    # High-risk transactions that require special monitoring
    HIGH_RISK_TCODES = [
        "SE38",   # ABAP Editor
        "SA38",   # ABAP Reporting
        "SE16",   # Data Browser
        "SE16N",  # General Table Display
        "SM59",   # RFC Destinations
        "SU01",   # User Maintenance
        "PFCG",   # Role Maintenance
        "STMS",   # Transport Management
        "SCC4",   # Client Administration
        "SM21",   # System Log
        "SM37",   # Background Jobs
        "SE11",   # ABAP Dictionary
        "SE80",   # Object Navigator
    ]

    def __init__(
        self,
        connection_manager: Optional[SAPRFCConnectionManager] = None,
        config: Optional[SAPExtractorConfig] = None
    ):
        super().__init__(connection_manager, config)

    def extract(
        self,
        username: str,
        from_date: str,
        to_date: str,
        tcode_filter: Optional[List[str]] = None,
        offset: int = 0,
        limit: int = 10000
    ) -> ExtractionResult:
        """
        Extract transaction usage data from STAD.

        Args:
            username: User ID to query
            from_date: Start date (YYYYMMDD format)
            to_date: End date (YYYYMMDD format)
            tcode_filter: Optional list of tcodes to include
            offset: Starting offset for pagination
            limit: Maximum records to return

        Returns:
            ExtractionResult with transaction usage data
        """
        start_time = datetime.now()
        errors = []

        try:
            # Build WHERE clauses
            where_clauses = [
                f"UNAME = '{username}'",
                f"DATUM BETWEEN '{from_date}' AND '{to_date}'"
            ]

            if tcode_filter:
                tcode_list = "', '".join(tcode_filter)
                where_clauses.append(f"TCODE IN ('{tcode_list}')")

            # Read from STAD
            raw_data = self._read_table(
                table_name="STAD",
                fields=self.STAD_FIELDS,
                where_clauses=where_clauses,
                max_rows=limit
            )

            # Transform data
            usage_records = []
            for row in raw_data:
                record = self._transform_usage_record(row)
                usage_records.append(record)

            return self._create_result(usage_records, "STAD", start_time, errors)

        except Exception as e:
            logger.error(f"Error extracting transaction usage: {e}")
            errors.append(str(e))
            return self._create_result([], "STAD", start_time, errors)

    def get_session_activity(
        self,
        username: str,
        session_start: datetime,
        session_end: datetime
    ) -> ExtractionResult:
        """
        Extract all activity within a firefighter session window.

        Args:
            username: Firefighter user ID
            session_start: Session start datetime
            session_end: Session end datetime

        Returns:
            ExtractionResult with session activity
        """
        from_date = session_start.strftime("%Y%m%d")
        to_date = session_end.strftime("%Y%m%d")

        result = self.extract(username, from_date, to_date)

        # Filter to exact session window
        session_activity = []
        for record in result.data:
            record_dt = self._parse_record_datetime(record)
            if record_dt and session_start <= record_dt <= session_end:
                record["within_session"] = True
                session_activity.append(record)

        # Recalculate result
        start_time = datetime.now()
        return self._create_result(session_activity, "STAD", start_time, result.errors)

    def get_restricted_tcode_usage(
        self,
        username: str,
        from_date: str,
        to_date: str
    ) -> ExtractionResult:
        """
        Extract usage of restricted/sensitive transaction codes.

        Args:
            username: User ID to query
            from_date: Start date
            to_date: End date

        Returns:
            ExtractionResult with restricted tcode usage only
        """
        start_time = datetime.now()
        errors = []

        try:
            # Extract with filter for restricted tcodes
            result = self.extract(
                username=username,
                from_date=from_date,
                to_date=to_date,
                tcode_filter=RESTRICTED_TCODES + self.HIGH_RISK_TCODES
            )

            # Enrich with risk information
            enriched = []
            for record in result.data:
                record["risk_level"] = self._get_tcode_risk_level(record["tcode"])
                record["risk_reason"] = self._get_risk_reason(record["tcode"])
                enriched.append(record)

            return self._create_result(enriched, "STAD", start_time, errors)

        except Exception as e:
            logger.error(f"Error extracting restricted tcode usage: {e}")
            errors.append(str(e))
            return self._create_result([], "STAD", start_time, errors)

    def get_usage_summary(
        self,
        username: str,
        from_date: str,
        to_date: str
    ) -> Dict[str, Any]:
        """
        Generate usage summary with aggregated statistics.

        Args:
            username: User ID to analyze
            from_date: Start date
            to_date: End date

        Returns:
            Summary dictionary with statistics
        """
        try:
            result = self.extract(username, from_date, to_date)

            # Calculate statistics
            tcode_counts = Counter(r["tcode"] for r in result.data)
            program_counts = Counter(r["program"] for r in result.data)

            # Duration statistics
            durations = [r["duration_ms"] for r in result.data if r["duration_ms"]]
            avg_duration = sum(durations) / len(durations) if durations else 0
            max_duration = max(durations) if durations else 0

            # Identify restricted usage
            restricted_usage = [
                r for r in result.data
                if r["tcode"] in (RESTRICTED_TCODES + self.HIGH_RISK_TCODES)
            ]

            # Time distribution
            hourly_distribution = self._calculate_hourly_distribution(result.data)

            return {
                "username": username,
                "period": {"from": from_date, "to": to_date},
                "total_executions": result.record_count,
                "unique_tcodes": len(tcode_counts),
                "top_tcodes": tcode_counts.most_common(10),
                "unique_programs": len(program_counts),
                "top_programs": program_counts.most_common(10),
                "duration_stats": {
                    "average_ms": round(avg_duration, 2),
                    "max_ms": max_duration,
                    "total_ms": sum(durations),
                },
                "restricted_usage": {
                    "count": len(restricted_usage),
                    "tcodes": list(set(r["tcode"] for r in restricted_usage)),
                },
                "rfc_calls": len([r for r in result.data if r.get("is_rfc")]),
                "hourly_distribution": hourly_distribution,
            }

        except Exception as e:
            logger.error(f"Error generating usage summary: {e}")
            raise

    def get_execution_counts(
        self,
        username: str,
        from_date: str,
        to_date: str
    ) -> Dict[str, int]:
        """
        Get aggregated execution counts by transaction code.

        Similar to STAT table data.

        Args:
            username: User ID
            from_date: Start date
            to_date: End date

        Returns:
            Dictionary mapping tcode to execution count
        """
        result = self.extract(username, from_date, to_date)
        return dict(Counter(r["tcode"] for r in result.data))

    def detect_anomalies(
        self,
        username: str,
        from_date: str,
        to_date: str,
        baseline_days: int = 30
    ) -> Dict[str, Any]:
        """
        Detect anomalous usage patterns.

        Compares current period against baseline.

        Args:
            username: User ID
            from_date: Current period start
            to_date: Current period end
            baseline_days: Days to use for baseline

        Returns:
            Anomaly detection results
        """
        try:
            # Get current period data
            current_result = self.extract(username, from_date, to_date)

            # Calculate baseline period
            to_dt = datetime.strptime(to_date, "%Y%m%d")
            baseline_start = (to_dt - timedelta(days=baseline_days)).strftime("%Y%m%d")
            baseline_end = (to_dt - timedelta(days=1)).strftime("%Y%m%d")

            baseline_result = self.extract(username, baseline_start, baseline_end)

            # Compare patterns
            anomalies = []

            # Check for new tcodes
            current_tcodes = set(r["tcode"] for r in current_result.data)
            baseline_tcodes = set(r["tcode"] for r in baseline_result.data)
            new_tcodes = current_tcodes - baseline_tcodes

            if new_tcodes:
                for tcode in new_tcodes:
                    anomalies.append({
                        "type": "new_tcode",
                        "tcode": tcode,
                        "severity": "medium" if tcode not in self.HIGH_RISK_TCODES else "high",
                        "description": f"Transaction {tcode} not used in baseline period",
                    })

            # Check for unusual volume
            current_count = len(current_result.data)
            baseline_avg = len(baseline_result.data) / max(baseline_days, 1)

            if current_count > baseline_avg * 3:
                anomalies.append({
                    "type": "high_volume",
                    "current_count": current_count,
                    "baseline_average": round(baseline_avg, 2),
                    "severity": "medium",
                    "description": f"Transaction volume {current_count} exceeds baseline average {baseline_avg:.2f}",
                })

            # Check for unusual timing
            timing_anomalies = self._detect_timing_anomalies(current_result.data)
            anomalies.extend(timing_anomalies)

            # Check for long-running transactions
            duration_anomalies = self._detect_duration_anomalies(
                current_result.data,
                baseline_result.data
            )
            anomalies.extend(duration_anomalies)

            return {
                "username": username,
                "analysis_period": {"from": from_date, "to": to_date},
                "baseline_period": {"from": baseline_start, "to": baseline_end},
                "anomaly_count": len(anomalies),
                "anomalies": anomalies,
                "risk_score": self._calculate_anomaly_risk_score(anomalies),
            }

        except Exception as e:
            logger.error(f"Error detecting anomalies: {e}")
            raise

    def _transform_usage_record(self, raw: Dict[str, str]) -> Dict[str, Any]:
        """Transform raw STAD record to structured format."""
        tcode = raw.get("TCODE", "")
        duration = raw.get("DURATION", "0")

        try:
            duration_ms = int(duration) if duration else 0
        except ValueError:
            duration_ms = 0

        return {
            "username": raw.get("UNAME", ""),
            "tcode": tcode,
            "program": raw.get("REPORT", ""),
            "date": self._format_date(raw.get("DATUM", "")),
            "time": self._format_time(raw.get("UZEIT", "")),
            "datetime": self._format_datetime(raw.get("DATUM", ""), raw.get("UZEIT", "")),
            "duration_ms": duration_ms,
            "is_rfc": bool(raw.get("RFC_CALL", "")),
            "is_restricted": tcode in RESTRICTED_TCODES,
            "is_high_risk": tcode in self.HIGH_RISK_TCODES,
        }

    def _parse_record_datetime(self, record: Dict) -> Optional[datetime]:
        """Parse record datetime string to datetime object."""
        dt_str = record.get("datetime")
        if not dt_str:
            return None
        try:
            return datetime.fromisoformat(dt_str)
        except:
            return None

    def _get_tcode_risk_level(self, tcode: str) -> str:
        """Get risk level for a transaction code."""
        critical_tcodes = ["SE38", "SA38", "SE16", "SE16N", "SU01", "PFCG"]
        high_tcodes = ["SM59", "STMS", "SCC4", "SE11", "SE80"]

        if tcode in critical_tcodes:
            return "critical"
        elif tcode in high_tcodes:
            return "high"
        elif tcode in RESTRICTED_TCODES:
            return "medium"
        else:
            return "low"

    def _get_risk_reason(self, tcode: str) -> str:
        """Get risk description for a transaction code."""
        reasons = {
            "SE38": "ABAP program editor - can modify system code",
            "SA38": "ABAP program execution - can run arbitrary programs",
            "SE16": "Direct table access - can view/modify database tables",
            "SE16N": "General table display - enhanced table access",
            "SU01": "User maintenance - can modify user accounts",
            "PFCG": "Role maintenance - can modify authorizations",
            "SM59": "RFC destinations - can modify external connections",
            "STMS": "Transport management - can move changes to production",
            "SCC4": "Client administration - system-wide settings",
            "SM21": "System log - access to security logs",
            "SM37": "Background jobs - can schedule/monitor batch jobs",
            "SE11": "Data dictionary - can modify table structures",
            "SE80": "Object navigator - development environment access",
        }
        return reasons.get(tcode, "Sensitive transaction")

    def _calculate_hourly_distribution(self, records: List[Dict]) -> Dict[str, int]:
        """Calculate distribution of activity by hour."""
        distribution = {f"{h:02d}:00": 0 for h in range(24)}

        for record in records:
            time_str = record.get("time", "")
            if time_str and len(time_str) >= 2:
                hour = time_str[:2]
                key = f"{hour}:00"
                if key in distribution:
                    distribution[key] += 1

        return distribution

    def _detect_timing_anomalies(self, records: List[Dict]) -> List[Dict]:
        """Detect unusual timing patterns."""
        anomalies = []

        # Check for off-hours activity
        off_hours_records = []
        for record in records:
            time_str = record.get("time", "")
            if time_str:
                try:
                    hour = int(time_str[:2])
                    if hour < 6 or hour > 22:  # Before 6 AM or after 10 PM
                        off_hours_records.append(record)
                except:
                    pass

        if off_hours_records:
            anomalies.append({
                "type": "off_hours_activity",
                "count": len(off_hours_records),
                "severity": "medium",
                "description": f"{len(off_hours_records)} transactions executed outside normal hours",
                "samples": [r["tcode"] for r in off_hours_records[:5]],
            })

        return anomalies

    def _detect_duration_anomalies(
        self,
        current: List[Dict],
        baseline: List[Dict]
    ) -> List[Dict]:
        """Detect unusually long-running transactions."""
        anomalies = []

        # Calculate baseline average durations by tcode
        baseline_durations: Dict[str, List[int]] = {}
        for record in baseline:
            tcode = record["tcode"]
            duration = record.get("duration_ms", 0)
            if duration:
                if tcode not in baseline_durations:
                    baseline_durations[tcode] = []
                baseline_durations[tcode].append(duration)

        # Check current against baseline
        for record in current:
            tcode = record["tcode"]
            duration = record.get("duration_ms", 0)

            if tcode in baseline_durations and duration:
                baseline_avg = sum(baseline_durations[tcode]) / len(baseline_durations[tcode])
                if duration > baseline_avg * 5:  # 5x baseline
                    anomalies.append({
                        "type": "long_duration",
                        "tcode": tcode,
                        "duration_ms": duration,
                        "baseline_avg_ms": round(baseline_avg, 2),
                        "severity": "low",
                        "description": f"Transaction {tcode} ran {duration}ms vs baseline {baseline_avg:.2f}ms",
                    })

        return anomalies

    def _calculate_anomaly_risk_score(self, anomalies: List[Dict]) -> int:
        """Calculate overall risk score from anomalies."""
        score = 0
        severity_weights = {"critical": 25, "high": 15, "medium": 10, "low": 5}

        for anomaly in anomalies:
            severity = anomaly.get("severity", "low")
            score += severity_weights.get(severity, 5)

        return min(score, 100)
