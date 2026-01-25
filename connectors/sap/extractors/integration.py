# SAP Extractor Integration with GOVERNEX+ Firefighter Module
# Bridges RFC extractors with existing firefighter workflow

"""
Integration module for connecting SAP RFC extractors with the
existing GOVERNEX+ Firefighter module.

This provides:
- Session evidence extraction for controller review
- Audit evidence export integration
- Real-time session monitoring data
- Compliance reporting data
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
import logging

from .firefighter import FirefighterSessionExtractor, FirefighterSessionEvidence
from .config import SAPExtractorConfig

logger = logging.getLogger(__name__)


class FirefighterSAPIntegration:
    """
    Integration layer between SAP extractors and GOVERNEX+ Firefighter module.

    Provides methods that match the expected interfaces of the
    existing firefighter manager and monitoring modules.
    """

    def __init__(self, config: Optional[SAPExtractorConfig] = None):
        """
        Initialize integration.

        Args:
            config: Optional SAP connection configuration
        """
        self.extractor = FirefighterSessionExtractor(config=config)
        self._cache = {}

    def extract_session_for_review(
        self,
        session_id: str,
        firefighter_id: str,
        start_time: datetime,
        end_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Extract SAP evidence for controller review.

        Called by the firefighter manager when generating
        review evidence packages.

        Args:
            session_id: GOVERNEX+ session ID
            firefighter_id: Firefighter user ID
            start_time: Session start datetime
            end_time: Session end datetime (optional)

        Returns:
            Evidence package for controller review
        """
        # Convert to SAP date format
        from_date = start_time.strftime("%Y%m%d")
        to_date = (end_time or datetime.now()).strftime("%Y%m%d")

        # Extract evidence
        evidence = self.extractor.extract_session(
            firefighter_id=firefighter_id,
            from_date=from_date,
            to_date=to_date,
            session_id=session_id,
            include_authorizations=True,
            include_changes=True
        )

        # Convert to review-friendly format
        return self._format_for_review(evidence)

    def get_session_activity_summary(
        self,
        firefighter_id: str,
        start_time: datetime,
        end_time: datetime
    ) -> Dict[str, Any]:
        """
        Get activity summary for real-time monitoring.

        Called by the firefighter monitoring module for
        live session dashboards.

        Args:
            firefighter_id: Firefighter user ID
            start_time: Session start
            end_time: Current time

        Returns:
            Activity summary for monitoring display
        """
        from_date = start_time.strftime("%Y%m%d")
        to_date = end_time.strftime("%Y%m%d")

        # Get transaction usage
        usage_result = self.extractor.tcode_usage.extract(
            firefighter_id, from_date, to_date
        )

        # Get change count
        change_result = self.extractor.change_docs.extract(
            username=firefighter_id,
            from_date=from_date,
            to_date=to_date,
            include_details=False
        )

        # Count restricted activities
        restricted_count = len([
            t for t in usage_result.data
            if t.get("is_restricted") or t.get("is_high_risk")
        ])

        sensitive_changes = len([
            c for c in change_result.data
            if c.get("object_class") in ["USER", "ROLE", "PFCG"]
        ])

        return {
            "firefighter_id": firefighter_id,
            "timestamp": datetime.now().isoformat(),
            "transaction_count": usage_result.record_count,
            "change_count": change_result.record_count,
            "restricted_activity_count": restricted_count,
            "sensitive_change_count": sensitive_changes,
            "latest_transactions": usage_result.data[-10:] if usage_result.data else [],
            "alert_indicators": {
                "high_activity": usage_result.record_count > 50,
                "restricted_usage": restricted_count > 0,
                "sensitive_changes": sensitive_changes > 0,
            }
        }

    def generate_audit_evidence_package(
        self,
        session_id: str,
        firefighter_id: str,
        start_time: datetime,
        end_time: datetime,
        format: str = "json"
    ) -> Dict[str, Any]:
        """
        Generate complete audit evidence package.

        Called by the firefighter manager for audit exports.

        Args:
            session_id: GOVERNEX+ session ID
            firefighter_id: Firefighter user ID
            start_time: Session start
            end_time: Session end
            format: Output format (json, csv_ready)

        Returns:
            Complete audit evidence package
        """
        from_date = start_time.strftime("%Y%m%d")
        to_date = end_time.strftime("%Y%m%d")

        # Get full audit report
        report = self.extractor.extract_audit_report(
            firefighter_id=firefighter_id,
            from_date=from_date,
            to_date=to_date
        )

        # Add GOVERNEX+ metadata
        report["governex_metadata"] = {
            "session_id": session_id,
            "export_timestamp": datetime.now().isoformat(),
            "export_format": format,
            "retention_days": 2555,  # 7 years for SOX
            "compliance_frameworks": ["SOX", "GDPR", "SOC2"],
        }

        if format == "csv_ready":
            return self._convert_to_csv_format(report)

        return report

    def get_user_eligibility(self, firefighter_id: str) -> Dict[str, Any]:
        """
        Check firefighter user eligibility.

        Called during session creation to validate
        firefighter account status.

        Args:
            firefighter_id: Firefighter user ID

        Returns:
            Eligibility status
        """
        status = self.extractor.users.get_firefighter_status(firefighter_id)

        return {
            "firefighter_id": firefighter_id,
            "eligible": status["available"],
            "is_locked": status["is_locked"],
            "is_valid": status["is_valid"],
            "user_type": status["user_type"],
            "compliance": status.get("compliance", {}),
            "role_count": status.get("role_count", 0),
            "check_timestamp": datetime.now().isoformat(),
        }

    def get_role_analysis(self, firefighter_id: str) -> Dict[str, Any]:
        """
        Analyze roles assigned to firefighter.

        Provides risk assessment of firefighter privileges.

        Args:
            firefighter_id: Firefighter user ID

        Returns:
            Role analysis with risk indicators
        """
        roles = self.extractor.roles.get_roles_for_user(firefighter_id)

        # Analyze each role
        role_analyses = []
        total_risk_score = 0

        for role in roles[:10]:  # Limit to 10 roles
            try:
                analysis = self.extractor.authorizations.analyze_firefighter_role(
                    role["role_name"]
                )
                role_analyses.append(analysis)
                total_risk_score += analysis["summary"]["risk_score"]
            except Exception as e:
                logger.warning(f"Could not analyze role {role['role_name']}: {e}")

        return {
            "firefighter_id": firefighter_id,
            "total_roles": len(roles),
            "analyzed_roles": len(role_analyses),
            "average_risk_score": total_risk_score / len(role_analyses) if role_analyses else 0,
            "role_analyses": role_analyses,
            "privileged_roles": [
                r for r in roles
                if r["role_name"] in ["SAP_ALL", "SAP_NEW", "S_A.ADMIN"]
            ],
        }

    def _format_for_review(self, evidence: FirefighterSessionEvidence) -> Dict[str, Any]:
        """Format evidence for controller review interface."""
        return {
            "session_info": {
                "session_id": evidence.session_id,
                "firefighter_id": evidence.firefighter_id,
                "system": evidence.system_id,
                "start_time": evidence.session_start.isoformat() if evidence.session_start else None,
                "end_time": evidence.session_end.isoformat() if evidence.session_end else None,
                "duration_minutes": evidence.duration_minutes,
            },
            "user_context": {
                "status": evidence.firefighter_status,
                "roles": evidence.assigned_roles,
            },
            "activity_summary": {
                "total_transactions": len(evidence.transaction_usage),
                "total_changes": len(evidence.change_documents),
                "risk_score": evidence.statistics["risk_score"],
                "flags": evidence.statistics.get("audit_flags", []),
            },
            "detailed_activity": {
                "transactions": evidence.transaction_usage,
                "changes": evidence.change_documents,
                "logon_events": evidence.logon_events,
            },
            "integrity": {
                "checksum": evidence.evidence_checksum,
                "extraction_time": evidence.extraction_timestamp.isoformat(),
            },
        }

    def _convert_to_csv_format(self, report: Dict) -> Dict[str, Any]:
        """Convert report to CSV-friendly format."""
        csv_data = {
            "summary": [report["executive_summary"]],
            "transactions": report["activity_analysis"].get("transaction_details", []),
            "changes": report["change_analysis"].get("change_details", []),
            "flags": [{"flag": f} for f in report["risk_assessment"].get("flags", [])],
        }

        return {
            "format": "csv_ready",
            "tables": csv_data,
            "metadata": report.get("governex_metadata", {}),
        }


# Factory function for easy instantiation
def create_sap_integration(
    config: Optional[Dict[str, Any]] = None
) -> FirefighterSAPIntegration:
    """
    Create SAP integration instance.

    Args:
        config: Optional configuration dictionary

    Returns:
        Configured FirefighterSAPIntegration instance
    """
    if config:
        sap_config = SAPExtractorConfig(**config)
    else:
        sap_config = None

    return FirefighterSAPIntegration(config=sap_config)
