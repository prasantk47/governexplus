# Firefighter Session Extractor
# Comprehensive audit data extraction for GOVERNEX+ Firefighter sessions

"""
Firefighter Session Extractor - Core integration module.

This is the main extractor that combines all SAP data sources to
provide complete audit evidence for firefighter sessions.

Correlation Logic:
- Links SAP data using Firefighter ID (USR02-BNAME)
- Correlates with Session Window (SM20 logon/logoff times)
- Includes TCODE usage (STAD) within session
- Includes Change logs (CDHDR/CDPOS) during session

This enables full session reconstruction for audit purposes.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import logging
import hashlib
import json

from .base import BaseExtractor, ExtractionResult
from .connection import SAPRFCConnectionManager
from .config import SAPExtractorConfig, RESTRICTED_TCODES
from .users import UserMasterExtractor
from .roles import RoleExtractor
from .authorizations import AuthorizationExtractor
from .audit_logs import SecurityAuditLogExtractor, SessionWindow
from .tcode_usage import TransactionUsageExtractor
from .change_documents import ChangeDocumentExtractor

logger = logging.getLogger(__name__)


@dataclass
class FirefighterSessionEvidence:
    """
    Complete audit evidence package for a firefighter session.

    Contains all correlated data from SAP for audit/compliance purposes.
    """
    # Session identification
    session_id: str
    firefighter_id: str
    system_id: str

    # Session timing
    session_start: datetime
    session_end: Optional[datetime]
    duration_minutes: Optional[int]

    # User context
    firefighter_status: Dict[str, Any]
    assigned_roles: List[Dict[str, Any]]
    role_authorizations: List[Dict[str, Any]]

    # Activity data
    logon_events: List[Dict[str, Any]]
    transaction_usage: List[Dict[str, Any]]
    change_documents: List[Dict[str, Any]]

    # Statistics
    statistics: Dict[str, Any]

    # Audit metadata
    extraction_timestamp: datetime
    evidence_checksum: str
    extractor_version: str = "1.0.0"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "session_id": self.session_id,
            "firefighter_id": self.firefighter_id,
            "system_id": self.system_id,
            "session_start": self.session_start.isoformat() if self.session_start else None,
            "session_end": self.session_end.isoformat() if self.session_end else None,
            "duration_minutes": self.duration_minutes,
            "firefighter_status": self.firefighter_status,
            "assigned_roles": self.assigned_roles,
            "role_authorizations": self.role_authorizations,
            "logon_events": self.logon_events,
            "transaction_usage": self.transaction_usage,
            "change_documents": self.change_documents,
            "statistics": self.statistics,
            "extraction_timestamp": self.extraction_timestamp.isoformat(),
            "evidence_checksum": self.evidence_checksum,
            "extractor_version": self.extractor_version,
        }

    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=indent, default=str)


class FirefighterSessionExtractor(BaseExtractor):
    """
    Main firefighter session extractor.

    Combines all individual extractors to provide complete
    session evidence for audit and compliance.
    """

    def __init__(
        self,
        connection_manager: Optional[SAPRFCConnectionManager] = None,
        config: Optional[SAPExtractorConfig] = None
    ):
        super().__init__(connection_manager, config)

        # Initialize component extractors with shared connection
        self.users = UserMasterExtractor(self.conn_manager)
        self.roles = RoleExtractor(self.conn_manager)
        self.authorizations = AuthorizationExtractor(self.conn_manager)
        self.audit_logs = SecurityAuditLogExtractor(self.conn_manager)
        self.tcode_usage = TransactionUsageExtractor(self.conn_manager)
        self.change_docs = ChangeDocumentExtractor(self.conn_manager)

        # System identifier (populated from connection)
        self._system_id = "SAP"

    def extract(
        self,
        firefighter_id: str,
        from_date: str,
        to_date: str,
        session_id: Optional[str] = None,
        **kwargs
    ) -> ExtractionResult:
        """
        Extract firefighter session data.

        This is the simplified interface matching BaseExtractor.
        For full session evidence, use extract_session().

        Args:
            firefighter_id: Firefighter user ID
            from_date: Start date (YYYYMMDD)
            to_date: End date (YYYYMMDD)
            session_id: Optional session identifier

        Returns:
            ExtractionResult with session data
        """
        start_time = datetime.now()
        errors = []

        try:
            # Extract basic session data
            evidence = self.extract_session(
                firefighter_id=firefighter_id,
                from_date=from_date,
                to_date=to_date,
                session_id=session_id
            )

            return self._create_result(
                [evidence.to_dict()],
                "FF_SESSION",
                start_time,
                errors
            )

        except Exception as e:
            logger.error(f"Error extracting firefighter session: {e}")
            errors.append(str(e))
            return self._create_result([], "FF_SESSION", start_time, errors)

    def extract_session(
        self,
        firefighter_id: str,
        from_date: str,
        to_date: str,
        session_id: Optional[str] = None,
        include_authorizations: bool = True,
        include_changes: bool = True
    ) -> FirefighterSessionEvidence:
        """
        Extract complete session evidence for a firefighter.

        This is the primary method for audit evidence generation.

        Args:
            firefighter_id: Firefighter user ID
            from_date: Start date (YYYYMMDD)
            to_date: End date (YYYYMMDD)
            session_id: Optional session identifier
            include_authorizations: Include role authorization details
            include_changes: Include change documents

        Returns:
            FirefighterSessionEvidence with complete audit package
        """
        logger.info(f"Extracting session evidence for {firefighter_id}")

        # Generate session ID if not provided
        if not session_id:
            session_id = self._generate_session_id(firefighter_id, from_date, to_date)

        # 1. Get firefighter user status
        logger.debug(f"Getting user status for {firefighter_id}")
        ff_status = self.users.get_firefighter_status(firefighter_id)

        # 2. Get role assignments
        logger.debug(f"Getting role assignments for {firefighter_id}")
        roles = self.roles.get_roles_for_user(firefighter_id)

        # 3. Get role authorizations (optional)
        role_auths = []
        if include_authorizations:
            logger.debug(f"Getting role authorizations")
            for role in roles[:10]:  # Limit to first 10 roles
                try:
                    auth = self.authorizations.get_role_authorizations(role["role_name"])
                    role_auths.append(auth)
                except Exception as e:
                    logger.warning(f"Could not get auth for role {role['role_name']}: {e}")

        # 4. Get session window from audit log
        logger.debug(f"Getting session windows")
        session_windows = self.audit_logs.get_session_windows(
            from_date, to_date, firefighter_id
        )

        # Determine session timing
        session_start = None
        session_end = None
        duration = None

        if session_windows:
            # Use first session window
            window = session_windows[0]
            session_start = window.logon_time
            session_end = window.logoff_time
            duration = window.duration_minutes
        else:
            # Fallback to date range
            session_start = datetime.strptime(from_date, "%Y%m%d")
            session_end = datetime.strptime(to_date, "%Y%m%d") + timedelta(days=1)

        # 5. Get logon events
        logger.debug(f"Getting logon events")
        logon_result = self.audit_logs.get_logon_events(
            from_date, to_date, firefighter_id
        )
        logon_events = logon_result.data

        # 6. Get transaction usage
        logger.debug(f"Getting transaction usage")
        if session_start and session_end:
            usage_result = self.tcode_usage.get_session_activity(
                firefighter_id, session_start, session_end
            )
        else:
            usage_result = self.tcode_usage.extract(
                firefighter_id, from_date, to_date
            )
        tcode_usage = usage_result.data

        # 7. Get change documents (optional)
        changes = []
        if include_changes:
            logger.debug(f"Getting change documents")
            if session_start and session_end:
                change_result = self.change_docs.get_session_changes(
                    firefighter_id, session_start, session_end
                )
            else:
                change_result = self.change_docs.extract(
                    username=firefighter_id,
                    from_date=from_date,
                    to_date=to_date
                )
            changes = change_result.data

        # 8. Calculate statistics
        statistics = self._calculate_session_statistics(
            tcode_usage, changes, roles, session_start, session_end
        )

        # 9. Build evidence package
        evidence = FirefighterSessionEvidence(
            session_id=session_id,
            firefighter_id=firefighter_id,
            system_id=self._system_id,
            session_start=session_start,
            session_end=session_end,
            duration_minutes=duration,
            firefighter_status=ff_status,
            assigned_roles=roles,
            role_authorizations=role_auths,
            logon_events=logon_events,
            transaction_usage=tcode_usage,
            change_documents=changes,
            statistics=statistics,
            extraction_timestamp=datetime.now(),
            evidence_checksum=""
        )

        # Calculate checksum for integrity
        evidence.evidence_checksum = self._calculate_evidence_checksum(evidence)

        logger.info(f"Session evidence extracted: {statistics['summary']}")
        return evidence

    def extract_audit_report(
        self,
        firefighter_id: str,
        from_date: str,
        to_date: str
    ) -> Dict[str, Any]:
        """
        Generate audit report for a firefighter session.

        Returns a structured report suitable for auditors.

        Args:
            firefighter_id: Firefighter user ID
            from_date: Start date
            to_date: End date

        Returns:
            Audit report dictionary
        """
        # Extract full evidence
        evidence = self.extract_session(
            firefighter_id=firefighter_id,
            from_date=from_date,
            to_date=to_date,
            include_authorizations=True,
            include_changes=True
        )

        # Build audit report
        report = {
            "report_type": "firefighter_session_audit",
            "generated_at": datetime.now().isoformat(),
            "report_version": "1.0",

            # Executive Summary
            "executive_summary": {
                "firefighter_id": firefighter_id,
                "system": self._system_id,
                "session_period": {
                    "from": from_date,
                    "to": to_date,
                },
                "duration_minutes": evidence.duration_minutes,
                "total_transactions": evidence.statistics["transaction_count"],
                "total_changes": evidence.statistics["change_count"],
                "risk_score": evidence.statistics["risk_score"],
                "compliance_status": self._determine_compliance_status(evidence),
            },

            # User Context
            "user_context": {
                "firefighter_status": evidence.firefighter_status,
                "role_count": len(evidence.assigned_roles),
                "roles": evidence.assigned_roles,
            },

            # Session Timeline
            "session_timeline": {
                "logon_time": evidence.session_start.isoformat() if evidence.session_start else None,
                "logoff_time": evidence.session_end.isoformat() if evidence.session_end else None,
                "logon_events": evidence.logon_events,
            },

            # Activity Analysis
            "activity_analysis": {
                "total_transactions": evidence.statistics["transaction_count"],
                "unique_tcodes": evidence.statistics["unique_tcodes"],
                "restricted_tcode_usage": evidence.statistics.get("restricted_tcodes", []),
                "transaction_details": evidence.transaction_usage[:100],  # Limit for report
            },

            # Change Analysis
            "change_analysis": {
                "total_changes": evidence.statistics["change_count"],
                "by_object_class": evidence.statistics.get("changes_by_class", {}),
                "high_risk_changes": [
                    c for c in evidence.change_documents
                    if c.get("risk_assessment", {}).get("risk_level") == "high"
                ],
                "change_details": evidence.change_documents[:50],  # Limit for report
            },

            # Risk Assessment
            "risk_assessment": {
                "overall_risk_score": evidence.statistics["risk_score"],
                "risk_factors": evidence.statistics.get("risk_factors", []),
                "flags": evidence.statistics.get("audit_flags", []),
            },

            # Evidence Integrity
            "evidence_integrity": {
                "checksum": evidence.evidence_checksum,
                "extraction_timestamp": evidence.extraction_timestamp.isoformat(),
                "extractor_version": evidence.extractor_version,
            },
        }

        return report

    def verify_session_evidence(
        self,
        evidence: FirefighterSessionEvidence
    ) -> Dict[str, Any]:
        """
        Verify integrity of session evidence.

        Args:
            evidence: Previously extracted evidence

        Returns:
            Verification result
        """
        # Recalculate checksum
        calculated_checksum = self._calculate_evidence_checksum(evidence)

        # Compare
        is_valid = calculated_checksum == evidence.evidence_checksum

        return {
            "is_valid": is_valid,
            "stored_checksum": evidence.evidence_checksum,
            "calculated_checksum": calculated_checksum,
            "verification_timestamp": datetime.now().isoformat(),
            "discrepancy": None if is_valid else "Checksum mismatch - evidence may have been modified",
        }

    def _generate_session_id(
        self,
        firefighter_id: str,
        from_date: str,
        to_date: str
    ) -> str:
        """Generate unique session identifier."""
        data = f"{firefighter_id}_{from_date}_{to_date}_{datetime.now().isoformat()}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]

    def _calculate_session_statistics(
        self,
        tcode_usage: List[Dict],
        changes: List[Dict],
        roles: List[Dict],
        session_start: Optional[datetime],
        session_end: Optional[datetime]
    ) -> Dict[str, Any]:
        """Calculate comprehensive session statistics."""
        # Transaction statistics
        unique_tcodes = set(t["tcode"] for t in tcode_usage)
        restricted_usage = [
            t for t in tcode_usage
            if t.get("is_restricted") or t.get("is_high_risk")
        ]

        # Change statistics
        changes_by_class = {}
        for change in changes:
            obj_class = change.get("object_class", "unknown")
            changes_by_class[obj_class] = changes_by_class.get(obj_class, 0) + 1

        # Risk calculation
        risk_score, risk_factors = self._calculate_risk_score(
            tcode_usage, changes, roles
        )

        # Audit flags
        audit_flags = self._generate_audit_flags(
            tcode_usage, changes, restricted_usage
        )

        # Duration
        duration_hours = None
        if session_start and session_end:
            duration = session_end - session_start
            duration_hours = round(duration.total_seconds() / 3600, 2)

        return {
            "transaction_count": len(tcode_usage),
            "unique_tcodes": len(unique_tcodes),
            "restricted_tcode_count": len(restricted_usage),
            "restricted_tcodes": list(set(t["tcode"] for t in restricted_usage)),
            "change_count": len(changes),
            "changes_by_class": changes_by_class,
            "role_count": len(roles),
            "duration_hours": duration_hours,
            "risk_score": risk_score,
            "risk_factors": risk_factors,
            "audit_flags": audit_flags,
            "summary": (
                f"Session: {len(tcode_usage)} transactions, "
                f"{len(changes)} changes, risk score {risk_score}"
            ),
        }

    def _calculate_risk_score(
        self,
        tcode_usage: List[Dict],
        changes: List[Dict],
        roles: List[Dict]
    ) -> tuple:
        """Calculate overall session risk score."""
        score = 0
        factors = []

        # Restricted tcode usage
        restricted_count = len([t for t in tcode_usage if t.get("is_restricted")])
        if restricted_count > 0:
            score += min(restricted_count * 5, 30)
            factors.append(f"Restricted transactions: {restricted_count}")

        # High-risk tcode usage
        high_risk_count = len([t for t in tcode_usage if t.get("is_high_risk")])
        if high_risk_count > 0:
            score += min(high_risk_count * 10, 40)
            factors.append(f"High-risk transactions: {high_risk_count}")

        # User/role changes
        sensitive_changes = len([
            c for c in changes
            if c.get("object_class") in ["USER", "ROLE", "PFCG"]
        ])
        if sensitive_changes > 0:
            score += min(sensitive_changes * 15, 30)
            factors.append(f"Sensitive changes: {sensitive_changes}")

        # SAP_ALL or equivalent
        for role in roles:
            if role.get("role_name") in ["SAP_ALL", "SAP_NEW"]:
                score += 20
                factors.append(f"Privileged role: {role['role_name']}")

        return min(score, 100), factors

    def _generate_audit_flags(
        self,
        tcode_usage: List[Dict],
        changes: List[Dict],
        restricted_usage: List[Dict]
    ) -> List[str]:
        """Generate audit flags for session."""
        flags = []

        # Check for user maintenance
        user_maint = [t for t in tcode_usage if t["tcode"] == "SU01"]
        if user_maint:
            flags.append("FLAG: User maintenance (SU01) executed")

        # Check for role maintenance
        role_maint = [t for t in tcode_usage if t["tcode"] == "PFCG"]
        if role_maint:
            flags.append("FLAG: Role maintenance (PFCG) executed")

        # Check for table access
        table_access = [t for t in tcode_usage if t["tcode"] in ["SE16", "SE16N"]]
        if table_access:
            flags.append("FLAG: Direct table access executed")

        # Check for user changes
        user_changes = [c for c in changes if c.get("object_class") == "USER"]
        if user_changes:
            flags.append(f"FLAG: {len(user_changes)} user master change(s)")

        # Check for role changes
        role_changes = [c for c in changes if c.get("object_class") in ["ROLE", "PFCG"]]
        if role_changes:
            flags.append(f"FLAG: {len(role_changes)} role/authorization change(s)")

        # High volume
        if len(tcode_usage) > 100:
            flags.append(f"FLAG: High transaction volume ({len(tcode_usage)})")

        return flags

    def _determine_compliance_status(
        self,
        evidence: FirefighterSessionEvidence
    ) -> str:
        """Determine overall compliance status."""
        risk_score = evidence.statistics.get("risk_score", 0)
        flags = evidence.statistics.get("audit_flags", [])

        if risk_score >= 70 or len(flags) >= 5:
            return "REQUIRES_REVIEW"
        elif risk_score >= 40 or len(flags) >= 3:
            return "ATTENTION_NEEDED"
        else:
            return "COMPLIANT"

    def _calculate_evidence_checksum(
        self,
        evidence: FirefighterSessionEvidence
    ) -> str:
        """Calculate SHA256 checksum of evidence for integrity."""
        # Create deterministic representation
        data = {
            "session_id": evidence.session_id,
            "firefighter_id": evidence.firefighter_id,
            "session_start": evidence.session_start.isoformat() if evidence.session_start else None,
            "session_end": evidence.session_end.isoformat() if evidence.session_end else None,
            "transaction_count": len(evidence.transaction_usage),
            "change_count": len(evidence.change_documents),
            "transactions": sorted([t["tcode"] for t in evidence.transaction_usage]),
            "changes": sorted([c.get("change_number", "") for c in evidence.change_documents]),
        }

        data_str = json.dumps(data, sort_keys=True)
        return hashlib.sha256(data_str.encode()).hexdigest()
