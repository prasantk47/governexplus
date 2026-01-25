# Change Document Extractor
# Extracts from SAP CDHDR/CDPOS tables for GOVERNEX+ Firefighter

"""
Change Document Extractor for SAP CDHDR/CDPOS tables.

Source Tables:
- CDHDR: Change Document Header
- CDPOS: Change Document Items (Positions)

CDHDR Fields:
- OBJECTCLAS: Object class (USER, ROLE, MATERIAL, etc.)
- OBJECTID: Changed object identifier
- USERNAME: Who made the change
- UDATE: Change date
- UTIME: Change time
- CHANGENR: Change document number (links to CDPOS)

CDPOS Fields:
- CHANGENR: Change document number (from CDHDR)
- FNAME: Field name changed
- VALUE_OLD: Previous value
- VALUE_NEW: New value

Used by GOVERNEX+ for:
- Detecting user changes during firefighter sessions
- Role modification tracking
- Configuration change monitoring
- Complete audit trail of all modifications
"""

from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from collections import defaultdict
import logging

from .base import BaseExtractor, ExtractionResult
from .connection import SAPRFCConnectionManager
from .config import SAPExtractorConfig, SENSITIVE_TABLES

logger = logging.getLogger(__name__)


class ChangeDocumentExtractor(BaseExtractor):
    """
    Extractor for SAP Change Documents (CDHDR/CDPOS).

    Provides complete change tracking for audit purposes.
    """

    # CDHDR fields
    CDHDR_FIELDS = [
        "OBJECTCLAS",  # Object class
        "OBJECTID",    # Object ID
        "USERNAME",    # Changed by user
        "UDATE",       # Change date
        "UTIME",       # Change time
        "CHANGENR",    # Change document number
        "TCODE",       # Transaction code used
    ]

    # CDPOS fields
    CDPOS_FIELDS = [
        "CHANGENR",    # Change document number
        "TABNAME",     # Table name
        "FNAME",       # Field name
        "VALUE_OLD",   # Old value
        "VALUE_NEW",   # New value
        "CHNGIND",     # Change indicator (I=Insert, U=Update, D=Delete)
    ]

    # Sensitive object classes for monitoring
    SENSITIVE_OBJECT_CLASSES = [
        "USER",        # User master changes
        "ROLE",        # Role changes
        "PFCG",        # Authorization changes
        "USMD",        # User management
        "VENDOR",      # Vendor master
        "CUSTOMER",    # Customer master
        "MATERIAL",    # Material master
        "BANF",        # Purchase requisition
        "EINKBELEG",   # Purchasing document
    ]

    def __init__(
        self,
        connection_manager: Optional[SAPRFCConnectionManager] = None,
        config: Optional[SAPExtractorConfig] = None
    ):
        super().__init__(connection_manager, config)

    def extract(
        self,
        username: Optional[str] = None,
        object_class: Optional[str] = None,
        from_date: str = None,
        to_date: str = None,
        include_details: bool = True,
        offset: int = 0,
        limit: int = 5000
    ) -> ExtractionResult:
        """
        Extract change documents from CDHDR/CDPOS.

        Args:
            username: Filter by user who made changes
            object_class: Filter by object class (USER, ROLE, etc.)
            from_date: Start date (YYYYMMDD format)
            to_date: End date (YYYYMMDD format)
            include_details: Include CDPOS details
            offset: Starting offset
            limit: Maximum records

        Returns:
            ExtractionResult with change documents
        """
        start_time = datetime.now()
        errors = []

        try:
            # Build WHERE clauses for CDHDR
            where_clauses = []

            if username:
                where_clauses.append(f"USERNAME = '{username}'")

            if object_class:
                where_clauses.append(f"OBJECTCLAS = '{object_class}'")

            if from_date:
                where_clauses.append(f"UDATE >= '{from_date}'")

            if to_date:
                where_clauses.append(f"UDATE <= '{to_date}'")

            # Read from CDHDR
            header_data = self._read_table(
                table_name="CDHDR",
                fields=self.CDHDR_FIELDS,
                where_clauses=where_clauses if where_clauses else None,
                max_rows=limit
            )

            # Transform header data
            changes = []
            for row in header_data:
                change = self._transform_header(row)

                # Get details from CDPOS if requested
                if include_details:
                    details = self._get_change_details(change["change_number"])
                    change["details"] = details
                    change["field_count"] = len(details)

                changes.append(change)

            return self._create_result(changes, "CDHDR/CDPOS", start_time, errors)

        except Exception as e:
            logger.error(f"Error extracting change documents: {e}")
            errors.append(str(e))
            return self._create_result([], "CDHDR/CDPOS", start_time, errors)

    def get_user_changes(
        self,
        from_date: str,
        to_date: str,
        changed_user: Optional[str] = None,
        changed_by: Optional[str] = None
    ) -> ExtractionResult:
        """
        Extract user master changes.

        Args:
            from_date: Start date
            to_date: End date
            changed_user: Filter by which user was changed (OBJECTID)
            changed_by: Filter by who made the change (USERNAME)

        Returns:
            ExtractionResult with user changes
        """
        start_time = datetime.now()
        errors = []

        try:
            # Get changes for USER object class
            result = self.extract(
                username=changed_by,
                object_class="USER",
                from_date=from_date,
                to_date=to_date,
                include_details=True
            )

            # Filter by changed user if specified
            if changed_user:
                result.data = [
                    c for c in result.data
                    if c["object_id"] == changed_user
                ]

            # Classify changes
            for change in result.data:
                change["change_classification"] = self._classify_user_change(change)

            return self._create_result(result.data, "CDHDR/CDPOS", start_time, errors)

        except Exception as e:
            logger.error(f"Error extracting user changes: {e}")
            errors.append(str(e))
            return self._create_result([], "CDHDR/CDPOS", start_time, errors)

    def get_role_changes(
        self,
        from_date: str,
        to_date: str,
        role_name: Optional[str] = None,
        changed_by: Optional[str] = None
    ) -> ExtractionResult:
        """
        Extract role/authorization changes.

        Args:
            from_date: Start date
            to_date: End date
            role_name: Filter by role name
            changed_by: Filter by who made changes

        Returns:
            ExtractionResult with role changes
        """
        start_time = datetime.now()
        errors = []

        try:
            # Get changes for ROLE and PFCG object classes
            role_changes = []

            for obj_class in ["ROLE", "PFCG"]:
                result = self.extract(
                    username=changed_by,
                    object_class=obj_class,
                    from_date=from_date,
                    to_date=to_date,
                    include_details=True
                )
                role_changes.extend(result.data)

            # Filter by role name if specified
            if role_name:
                role_changes = [
                    c for c in role_changes
                    if role_name in c.get("object_id", "")
                ]

            # Sort by datetime
            role_changes.sort(
                key=lambda x: x.get("datetime", ""),
                reverse=True
            )

            return self._create_result(role_changes, "CDHDR/CDPOS", start_time, errors)

        except Exception as e:
            logger.error(f"Error extracting role changes: {e}")
            errors.append(str(e))
            return self._create_result([], "CDHDR/CDPOS", start_time, errors)

    def get_session_changes(
        self,
        username: str,
        session_start: datetime,
        session_end: datetime
    ) -> ExtractionResult:
        """
        Extract all changes made during a firefighter session.

        Args:
            username: Firefighter user ID
            session_start: Session start datetime
            session_end: Session end datetime

        Returns:
            ExtractionResult with session changes
        """
        from_date = session_start.strftime("%Y%m%d")
        to_date = session_end.strftime("%Y%m%d")

        result = self.extract(
            username=username,
            from_date=from_date,
            to_date=to_date,
            include_details=True
        )

        # Filter to exact session window
        session_changes = []
        for change in result.data:
            change_dt = self._parse_change_datetime(change)
            if change_dt and session_start <= change_dt <= session_end:
                change["within_session"] = True
                change["risk_assessment"] = self._assess_change_risk(change)
                session_changes.append(change)

        start_time = datetime.now()
        return self._create_result(session_changes, "CDHDR/CDPOS", start_time, result.errors)

    def get_sensitive_changes(
        self,
        from_date: str,
        to_date: str,
        username: Optional[str] = None
    ) -> ExtractionResult:
        """
        Extract only sensitive/security-relevant changes.

        Args:
            from_date: Start date
            to_date: End date
            username: Filter by user

        Returns:
            ExtractionResult with sensitive changes
        """
        start_time = datetime.now()
        errors = []

        try:
            sensitive_changes = []

            for obj_class in self.SENSITIVE_OBJECT_CLASSES:
                result = self.extract(
                    username=username,
                    object_class=obj_class,
                    from_date=from_date,
                    to_date=to_date,
                    include_details=True
                )

                for change in result.data:
                    change["sensitivity_reason"] = f"Sensitive object class: {obj_class}"
                    change["risk_level"] = self._get_object_class_risk_level(obj_class)
                    sensitive_changes.append(change)

            # Sort by datetime
            sensitive_changes.sort(
                key=lambda x: x.get("datetime", ""),
                reverse=True
            )

            return self._create_result(sensitive_changes, "CDHDR/CDPOS", start_time, errors)

        except Exception as e:
            logger.error(f"Error extracting sensitive changes: {e}")
            errors.append(str(e))
            return self._create_result([], "CDHDR/CDPOS", start_time, errors)

    def get_change_summary(
        self,
        username: str,
        from_date: str,
        to_date: str
    ) -> Dict[str, Any]:
        """
        Generate change summary with statistics.

        Args:
            username: User ID
            from_date: Start date
            to_date: End date

        Returns:
            Summary dictionary
        """
        try:
            result = self.extract(
                username=username,
                from_date=from_date,
                to_date=to_date,
                include_details=True
            )

            # Group by object class
            by_object_class = defaultdict(list)
            for change in result.data:
                by_object_class[change["object_class"]].append(change)

            # Count change types
            change_types = defaultdict(int)
            for change in result.data:
                for detail in change.get("details", []):
                    indicator = detail.get("change_indicator", "U")
                    if indicator == "I":
                        change_types["inserts"] += 1
                    elif indicator == "D":
                        change_types["deletes"] += 1
                    else:
                        change_types["updates"] += 1

            # Identify high-risk changes
            high_risk_changes = [
                c for c in result.data
                if c.get("object_class") in ["USER", "ROLE", "PFCG"]
            ]

            return {
                "username": username,
                "period": {"from": from_date, "to": to_date},
                "total_changes": result.record_count,
                "by_object_class": {
                    k: len(v) for k, v in by_object_class.items()
                },
                "change_types": dict(change_types),
                "high_risk_changes": len(high_risk_changes),
                "total_fields_changed": sum(
                    c.get("field_count", 0) for c in result.data
                ),
                "unique_objects_changed": len(set(
                    c["object_id"] for c in result.data
                )),
                "transactions_used": list(set(
                    c.get("transaction") for c in result.data if c.get("transaction")
                )),
            }

        except Exception as e:
            logger.error(f"Error generating change summary: {e}")
            raise

    def _get_change_details(self, change_number: str) -> List[Dict[str, Any]]:
        """Get CDPOS details for a change document."""
        try:
            raw_data = self._read_table(
                table_name="CDPOS",
                fields=self.CDPOS_FIELDS,
                where_clauses=[f"CHANGENR = '{change_number}'"],
                max_rows=100
            )

            details = []
            for row in raw_data:
                detail = self._transform_detail(row)
                details.append(detail)

            return details

        except Exception as e:
            logger.warning(f"Could not get details for change {change_number}: {e}")
            return []

    def _transform_header(self, raw: Dict[str, str]) -> Dict[str, Any]:
        """Transform raw CDHDR record to structured format."""
        return {
            "object_class": raw.get("OBJECTCLAS", ""),
            "object_id": raw.get("OBJECTID", ""),
            "changed_by": raw.get("USERNAME", ""),
            "date": self._format_date(raw.get("UDATE", "")),
            "time": self._format_time(raw.get("UTIME", "")),
            "datetime": self._format_datetime(raw.get("UDATE", ""), raw.get("UTIME", "")),
            "change_number": raw.get("CHANGENR", ""),
            "transaction": raw.get("TCODE", ""),
        }

    def _transform_detail(self, raw: Dict[str, str]) -> Dict[str, Any]:
        """Transform raw CDPOS record to structured format."""
        indicator = raw.get("CHNGIND", "U")
        indicator_text = {
            "I": "Insert",
            "U": "Update",
            "D": "Delete",
            "E": "Single field",
        }.get(indicator, "Unknown")

        return {
            "change_number": raw.get("CHANGENR", ""),
            "table_name": raw.get("TABNAME", ""),
            "field_name": raw.get("FNAME", ""),
            "old_value": raw.get("VALUE_OLD", ""),
            "new_value": raw.get("VALUE_NEW", ""),
            "change_indicator": indicator,
            "change_type": indicator_text,
        }

    def _parse_change_datetime(self, change: Dict) -> Optional[datetime]:
        """Parse change datetime to Python datetime object."""
        dt_str = change.get("datetime")
        if not dt_str:
            return None
        try:
            return datetime.fromisoformat(dt_str)
        except:
            return None

    def _classify_user_change(self, change: Dict) -> Dict[str, Any]:
        """Classify a user master change."""
        classification = {
            "category": "unknown",
            "severity": "low",
            "description": "",
        }

        details = change.get("details", [])
        for detail in details:
            field = detail.get("field_name", "")

            if field in ["UFLAG", "USLOCK"]:
                classification["category"] = "lock_status"
                classification["severity"] = "high"
                classification["description"] = "User lock status changed"
            elif field in ["AGR_NAME"]:
                classification["category"] = "role_assignment"
                classification["severity"] = "high"
                classification["description"] = "Role assignment changed"
            elif field in ["BCODE", "CODVN", "PASSCODE"]:
                classification["category"] = "password"
                classification["severity"] = "medium"
                classification["description"] = "Password changed"
            elif field in ["GLTGV", "GLTGB"]:
                classification["category"] = "validity"
                classification["severity"] = "medium"
                classification["description"] = "Validity dates changed"
            elif field in ["USTYP"]:
                classification["category"] = "user_type"
                classification["severity"] = "high"
                classification["description"] = "User type changed"

        return classification

    def _assess_change_risk(self, change: Dict) -> Dict[str, Any]:
        """Assess risk level of a change."""
        risk_score = 0
        risk_factors = []

        obj_class = change.get("object_class", "")

        # Object class risk
        if obj_class in ["USER", "ROLE", "PFCG"]:
            risk_score += 30
            risk_factors.append(f"Sensitive object class: {obj_class}")

        # Number of fields changed
        field_count = change.get("field_count", 0)
        if field_count > 5:
            risk_score += 10
            risk_factors.append(f"Multiple fields changed: {field_count}")

        # Check for high-risk field changes
        details = change.get("details", [])
        for detail in details:
            field = detail.get("field_name", "")
            if field in ["UFLAG", "AGR_NAME", "USTYP", "BCODE"]:
                risk_score += 20
                risk_factors.append(f"High-risk field: {field}")

        # Determine risk level
        if risk_score >= 50:
            level = "high"
        elif risk_score >= 30:
            level = "medium"
        else:
            level = "low"

        return {
            "risk_level": level,
            "risk_score": min(risk_score, 100),
            "risk_factors": risk_factors,
        }

    def _get_object_class_risk_level(self, obj_class: str) -> str:
        """Get risk level for an object class."""
        high_risk = ["USER", "ROLE", "PFCG", "USMD"]
        medium_risk = ["VENDOR", "CUSTOMER", "BANF", "EINKBELEG"]

        if obj_class in high_risk:
            return "high"
        elif obj_class in medium_risk:
            return "medium"
        else:
            return "low"
