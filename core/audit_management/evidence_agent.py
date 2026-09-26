"""
Audit Evidence Agent
Given a control requirement, automatically finds and assembles evidence from connected systems.
"""
import uuid
import hashlib
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func


class AuditEvidenceAgent:
    """AI agent that auto-collects audit evidence based on control requirements."""

    # Control requirement → evidence source mapping
    EVIDENCE_SOURCES = {
        "access_review": {
            "description": "User access must be reviewed periodically",
            "sources": ["user_roles", "certification_campaigns", "access_requests"],
            "validation": "Check certification completion rate and recency",
        },
        "sod_monitoring": {
            "description": "SoD violations must be monitored and mitigated",
            "sources": ["risk_violations", "mitigation_controls"],
            "validation": "Check violation count, mitigation coverage, open vs resolved",
        },
        "privileged_access": {
            "description": "Privileged/emergency access must be controlled and reviewed",
            "sources": ["firefighter_sessions", "firefighter_requests"],
            "validation": "Check session review completion, reason code compliance",
        },
        "password_policy": {
            "description": "Password policy must meet standards",
            "sources": ["ccm_executions"],
            "validation": "Check CCM rule results for password policy checks",
        },
        "change_management": {
            "description": "Changes must follow approval workflow",
            "sources": ["access_requests", "orchestration_contexts"],
            "validation": "Check approval chain completeness",
        },
        "terminated_access": {
            "description": "Terminated employees must lose access within SLA",
            "sources": ["users", "user_roles"],
            "validation": "Check disabled/expired users still have active roles",
        },
        "vendor_controls": {
            "description": "Vendor master data changes must be authorized",
            "sources": ["risk_violations", "user_entitlements"],
            "validation": "Check SoD on vendor-related tcodes, approval evidence",
        },
    }

    def __init__(self, tenant_id: str, db: Session):
        self.tenant_id = tenant_id
        self.db = db

    def collect_evidence(
        self,
        requirement_type: str,
        period_start: str = None,
        period_end: str = None,
    ) -> dict:
        """Auto-collect evidence for a control requirement."""
        if requirement_type not in self.EVIDENCE_SOURCES:
            return {
                "error": (
                    f"Unknown requirement type. "
                    f"Available: {list(self.EVIDENCE_SOURCES.keys())}"
                )
            }

        spec = self.EVIDENCE_SOURCES[requirement_type]
        start = (
            datetime.fromisoformat(period_start)
            if period_start
            else datetime.utcnow() - timedelta(days=90)
        )
        end = datetime.fromisoformat(period_end) if period_end else datetime.utcnow()

        evidence_items = []
        gaps = []

        for source in spec["sources"]:
            result = self._collect_from_source(source, start, end)
            if result["row_count"] > 0:
                evidence_items.append(result)
            else:
                gaps.append({"source": source, "reason": "No data found for the period"})

        total_rows = sum(e["row_count"] for e in evidence_items)
        completeness = round(
            len(evidence_items) / max(len(spec["sources"]), 1) * 100
        )

        # Generate hash for the evidence package
        payload = json.dumps(
            [e["summary"] for e in evidence_items], default=str, sort_keys=True
        )
        package_hash = hashlib.sha256(payload.encode()).hexdigest()

        return {
            "evidence_id": f"EVP-{uuid.uuid4().hex[:8].upper()}",
            "requirement_type": requirement_type,
            "requirement_description": spec["description"],
            "period": {"start": start.isoformat(), "end": end.isoformat()},
            "collected_at": datetime.utcnow().isoformat(),
            "completeness_pct": completeness,
            "total_records": total_rows,
            "evidence_items": evidence_items,
            "gaps": gaps,
            "validation": spec["validation"],
            "package_hash": package_hash,
            "status": "complete" if completeness == 100 else "incomplete",
            "ai_assessment": self._assess_evidence(requirement_type, evidence_items, gaps),
        }

    def _collect_from_source(self, source: str, start: datetime, end: datetime) -> dict:
        """Collect evidence from a specific data source."""
        if source == "user_roles":
            from db.models.user import UserRole
            count = (
                self.db.query(func.count(UserRole.id))
                .filter(
                    UserRole.tenant_id == self.tenant_id,
                    UserRole.is_active == True,
                )
                .scalar()
                or 0
            )
            return {
                "source": source,
                "row_count": count,
                "summary": f"{count} active user-role assignments",
            }

        elif source == "certification_campaigns":
            from db.models.audit import CertificationCampaignLog
            campaigns = (
                self.db.query(CertificationCampaignLog)
                .filter(CertificationCampaignLog.tenant_id == self.tenant_id)
                .all()
            )
            completed = sum(
                1 for c in campaigns if c.status in ("completed", "closed")
            )
            return {
                "source": source,
                "row_count": len(campaigns),
                "summary": f"{len(campaigns)} campaigns, {completed} completed",
                "detail": {"total": len(campaigns), "completed": completed},
            }

        elif source == "access_requests":
            from db.models.audit import AccessRequestLog
            reqs = (
                self.db.query(func.count(AccessRequestLog.id))
                .filter(
                    AccessRequestLog.tenant_id == self.tenant_id,
                    AccessRequestLog.submitted_at >= start,
                    AccessRequestLog.submitted_at <= end,
                )
                .scalar()
                or 0
            )
            return {
                "source": source,
                "row_count": reqs,
                "summary": f"{reqs} access requests in period",
            }

        elif source == "risk_violations":
            from db.models.risk import RiskViolation, ViolationStatus
            total = (
                self.db.query(func.count(RiskViolation.id))
                .filter(RiskViolation.tenant_id == self.tenant_id)
                .scalar()
                or 0
            )
            open_v = (
                self.db.query(func.count(RiskViolation.id))
                .filter(
                    RiskViolation.tenant_id == self.tenant_id,
                    RiskViolation.status == ViolationStatus.OPEN,
                )
                .scalar()
                or 0
            )
            mitigated = (
                self.db.query(func.count(RiskViolation.id))
                .filter(
                    RiskViolation.tenant_id == self.tenant_id,
                    RiskViolation.is_mitigated == True,
                )
                .scalar()
                or 0
            )
            return {
                "source": source,
                "row_count": total,
                "summary": f"{total} violations ({open_v} open, {mitigated} mitigated)",
                "detail": {"total": total, "open": open_v, "mitigated": mitigated},
            }

        elif source == "mitigation_controls":
            from db.models.risk import MitigationControl
            count = (
                self.db.query(func.count(MitigationControl.id))
                .filter(
                    MitigationControl.tenant_id == self.tenant_id,
                    MitigationControl.is_active == True,
                )
                .scalar()
                or 0
            )
            return {
                "source": source,
                "row_count": count,
                "summary": f"{count} active mitigation controls",
            }

        elif source == "firefighter_sessions":
            from db.models.firefighter import FirefighterSession
            sessions = (
                self.db.query(func.count(FirefighterSession.id))
                .filter(FirefighterSession.tenant_id == self.tenant_id)
                .scalar()
                or 0
            )
            return {
                "source": source,
                "row_count": sessions,
                "summary": f"{sessions} firefighter sessions",
            }

        elif source == "firefighter_requests":
            from db.models.firefighter import FirefighterRequest
            reqs = (
                self.db.query(func.count(FirefighterRequest.id))
                .filter(FirefighterRequest.tenant_id == self.tenant_id)
                .scalar()
                or 0
            )
            return {
                "source": source,
                "row_count": reqs,
                "summary": f"{reqs} firefighter requests",
            }

        elif source == "ccm_executions":
            from db.models.process_control import CCMExecution
            execs = (
                self.db.query(func.count(CCMExecution.id))
                .filter(
                    CCMExecution.tenant_id == self.tenant_id,
                    CCMExecution.executed_at >= start,
                )
                .scalar()
                or 0
            )
            return {
                "source": source,
                "row_count": execs,
                "summary": f"{execs} CCM executions in period",
            }

        elif source == "users":
            from db.models.user import User
            disabled = (
                self.db.query(func.count(User.id))
                .filter(
                    User.tenant_id == self.tenant_id,
                    User.status.in_(["disabled", "locked", "expired"]),
                )
                .scalar()
                or 0
            )
            total = (
                self.db.query(func.count(User.id))
                .filter(User.tenant_id == self.tenant_id)
                .scalar()
                or 0
            )
            return {
                "source": source,
                "row_count": total,
                "summary": f"{total} users ({disabled} disabled/locked/expired)",
            }

        elif source == "user_entitlements":
            from db.models.user import UserEntitlement
            count = (
                self.db.query(func.count(UserEntitlement.id))
                .filter(UserEntitlement.source_role.isnot(None))
                .scalar()
                or 0
            )
            return {
                "source": source,
                "row_count": count,
                "summary": f"{count} user entitlements",
            }

        elif source == "orchestration_contexts":
            from db.models.operations import OrchestrationContextRecord
            count = (
                self.db.query(func.count(OrchestrationContextRecord.id))
                .filter(OrchestrationContextRecord.tenant_id == self.tenant_id)
                .scalar()
                or 0
            )
            return {
                "source": source,
                "row_count": count,
                "summary": f"{count} workflow execution records",
            }

        return {"source": source, "row_count": 0, "summary": "Source not available"}

    def _assess_evidence(
        self, requirement_type: str, items: list, gaps: list
    ) -> str:
        """AI assessment of evidence completeness and quality."""
        if not items:
            return (
                "No evidence collected. "
                "All required data sources are empty for this period."
            )

        if gaps:
            gap_sources = ", ".join(g["source"] for g in gaps)
            return (
                f"Evidence is partially complete. Missing data from: {gap_sources}. "
                f"Collected {sum(e['row_count'] for e in items)} records from "
                f"{len(items)} sources. Manual evidence may be needed for gaps."
            )

        total = sum(e["row_count"] for e in items)
        return (
            f"Evidence package is complete with {total} records from {len(items)} sources. "
            f"All required data sources have data for the review period."
        )

    def list_available_requirements(self) -> list:
        """List all requirement types the agent can collect evidence for."""
        return [
            {
                "type": k,
                "description": v["description"],
                "sources": v["sources"],
            }
            for k, v in self.EVIDENCE_SOURCES.items()
        ]

    def assess_control_evidence(self, control_id: str) -> dict:
        """Assess evidence coverage for a specific PC control."""
        from db.models.process_control import ProcessControl, ControlTest, GRCEvidence

        control = (
            self.db.query(ProcessControl)
            .filter_by(tenant_id=self.tenant_id, control_id=control_id)
            .first()
        )
        if not control:
            return {"error": "Control not found"}

        tests = (
            self.db.query(ControlTest)
            .filter_by(tenant_id=self.tenant_id, control_id=control.id)
            .all()
        )

        evidence = (
            self.db.query(GRCEvidence)
            .filter(
                GRCEvidence.tenant_id == self.tenant_id,
                GRCEvidence.linked_object_type.in_(["control_test", "control"]),
            )
            .all()
        )

        # Check what's missing
        missing = []
        if not tests:
            missing.append("No operating effectiveness tests recorded")
        else:
            latest = max(tests, key=lambda t: t.created_at)
            age_days = (datetime.utcnow() - latest.created_at).days
            if age_days > 180:
                missing.append(
                    f"Latest test is {age_days} days old — may need retest"
                )

        if not evidence:
            missing.append("No evidence documents attached")

        return {
            "control_id": control_id,
            "control_name": control.name,
            "tests_count": len(tests),
            "evidence_count": len(evidence),
            "missing_items": missing,
            "coverage_pct": 100 - (len(missing) * 25),
            "recommendation": (
                missing[0] if missing else "Evidence coverage is adequate"
            ),
        }
