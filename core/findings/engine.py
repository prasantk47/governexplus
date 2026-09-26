"""
Findings Engine

Central engine that:
1. Accepts findings from any source module
2. Deduplicates (same user + same rule + same scope = one finding)
3. Enriches with recommendations
4. Tracks lifecycle (open → in_progress → remediated/mitigated)
5. Provides query/filter/aggregate interface
"""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime
from typing import Optional

from core.risk_engine.models import (
    RiskAnalysisResult,
    SoDViolation,
    SensitiveAccessViolation,
    CriticalActionViolation,
)
from core.effective_access.models import (
    UserEffectiveAccess,
    ReconciliationStatus,
    AccessReconciliation,
)

from .models import (
    Finding,
    FindingType,
    FindingSeverity,
    FindingSource,
    FindingStatus,
    Recommendation,
    RecommendationType,
    RecommendationStatus,
)

logger = logging.getLogger(__name__)

SEVERITY_MAP = {
    "critical": FindingSeverity.CRITICAL,
    "high": FindingSeverity.HIGH,
    "medium": FindingSeverity.MEDIUM,
    "low": FindingSeverity.LOW,
}


class FindingsEngine:
    """Central findings repository and lifecycle manager.

    This is an in-memory engine.  For persistence, callers should
    serialize findings to the database after processing.
    """

    def __init__(self):
        self._findings: dict[str, Finding] = {}  # finding_id → Finding

    @property
    def findings(self) -> list[Finding]:
        return list(self._findings.values())

    # ------------------------------------------------------------------
    # Ingest from Risk Engine
    # ------------------------------------------------------------------

    def ingest_risk_analysis(
        self,
        result: RiskAnalysisResult,
        tenant_id: str,
    ) -> list[Finding]:
        """Convert RiskAnalysisResult into normalized Findings."""
        created = []

        for v in result.sod_violations:
            f = self._sod_violation_to_finding(v, tenant_id)
            self._add_finding(f)
            created.append(f)

        for v in result.sensitive_access:
            f = self._sensitive_to_finding(v, tenant_id)
            self._add_finding(f)
            created.append(f)

        for v in result.critical_actions:
            f = self._critical_to_finding(v, tenant_id)
            self._add_finding(f)
            created.append(f)

        return created

    # ------------------------------------------------------------------
    # Ingest from Effective Access (reconciliation)
    # ------------------------------------------------------------------

    def ingest_reconciliation(
        self,
        user_id: str,
        tenant_id: str,
        reconciliations: list[AccessReconciliation],
    ) -> list[Finding]:
        """Convert access reconciliation results into Findings."""
        created = []

        for rec in reconciliations:
            if rec.status == ReconciliationStatus.MATCHED:
                continue

            ftype = {
                ReconciliationStatus.OVER_PROVISIONED: FindingType.OVER_PROVISIONED,
                ReconciliationStatus.UNDER_PROVISIONED: FindingType.UNDER_PROVISIONED,
                ReconciliationStatus.STALE: FindingType.STALE_ACCESS,
                ReconciliationStatus.PROVISIONING_FAILED: FindingType.UNDER_PROVISIONED,
                ReconciliationStatus.PENDING: FindingType.UNDER_PROVISIONED,
            }.get(rec.status, FindingType.OVER_PROVISIONED)

            severity = FindingSeverity.HIGH if rec.status == ReconciliationStatus.OVER_PROVISIONED \
                else FindingSeverity.MEDIUM

            fid = _make_id("RECON", user_id, rec.role_id, rec.status.value)
            f = Finding(
                finding_id=fid,
                finding_type=ftype,
                severity=severity,
                source=FindingSource.EFFECTIVE_ACCESS,
                user_id=user_id,
                tenant_id=tenant_id,
                title=f"{rec.status.value.replace('_', ' ').title()}: {rec.role_id}",
                description=rec.discrepancy_details or f"Role {rec.role_id} is {rec.status.value}",
                related_roles=[rec.role_id],
                details=rec.to_dict(),
            )

            # Add recommendation
            if rec.status == ReconciliationStatus.OVER_PROVISIONED:
                f.recommendations.append(Recommendation(
                    recommendation_id=f"REC-{fid}",
                    finding_id=fid,
                    recommendation_type=RecommendationType.REMOVE_ROLE,
                    description=f"Remove unauthorized role {rec.role_id}",
                    target_user_id=user_id,
                    target_role_id=rec.role_id,
                ))
            elif rec.status == ReconciliationStatus.STALE:
                f.recommendations.append(Recommendation(
                    recommendation_id=f"REC-{fid}",
                    finding_id=fid,
                    recommendation_type=RecommendationType.REMOVE_ROLE,
                    description=f"Remove expired role {rec.role_id}",
                    target_user_id=user_id,
                    target_role_id=rec.role_id,
                ))

            self._add_finding(f)
            created.append(f)

        return created

    # ------------------------------------------------------------------
    # Ingest from other modules
    # ------------------------------------------------------------------

    def add_finding(self, finding: Finding) -> None:
        """Add a finding from any source."""
        self._add_finding(finding)

    def add_findings(self, findings: list[Finding]) -> None:
        for f in findings:
            self._add_finding(f)

    # ------------------------------------------------------------------
    # Lifecycle management
    # ------------------------------------------------------------------

    def update_status(
        self,
        finding_id: str,
        new_status: FindingStatus,
        resolved_by: Optional[str] = None,
    ) -> Optional[Finding]:
        """Update a finding's status."""
        f = self._findings.get(finding_id)
        if not f:
            return None

        f.status = new_status
        if new_status in (FindingStatus.REMEDIATED, FindingStatus.MITIGATED,
                          FindingStatus.ACCEPTED, FindingStatus.FALSE_POSITIVE):
            f.resolved_at = datetime.utcnow()
            f.resolved_by = resolved_by

        return f

    # ------------------------------------------------------------------
    # Query interface
    # ------------------------------------------------------------------

    def get_findings_for_user(self, user_id: str) -> list[Finding]:
        return [f for f in self._findings.values() if f.user_id == user_id]

    def get_open_findings(self) -> list[Finding]:
        return [f for f in self._findings.values()
                if f.status in (FindingStatus.OPEN, FindingStatus.IN_PROGRESS)]

    def get_findings_by_type(self, finding_type: FindingType) -> list[Finding]:
        return [f for f in self._findings.values() if f.finding_type == finding_type]

    def get_findings_by_severity(self, severity: FindingSeverity) -> list[Finding]:
        return [f for f in self._findings.values() if f.severity == severity]

    def get_findings_by_source(self, source: FindingSource) -> list[Finding]:
        return [f for f in self._findings.values() if f.source == source]

    def get_summary(self) -> dict:
        """Dashboard-ready summary of all findings."""
        all_findings = list(self._findings.values())
        open_findings = [f for f in all_findings if f.status == FindingStatus.OPEN]

        by_severity = {}
        by_type = {}
        by_source = {}
        for f in open_findings:
            by_severity[f.severity.value] = by_severity.get(f.severity.value, 0) + 1
            by_type[f.finding_type.value] = by_type.get(f.finding_type.value, 0) + 1
            by_source[f.source.value] = by_source.get(f.source.value, 0) + 1

        return {
            "total_findings": len(all_findings),
            "open_findings": len(open_findings),
            "by_severity": by_severity,
            "by_type": by_type,
            "by_source": by_source,
            "pending_recommendations": sum(
                len([r for r in f.recommendations
                     if r.status == RecommendationStatus.PROPOSED])
                for f in open_findings
            ),
        }

    # ------------------------------------------------------------------
    # Conversion helpers
    # ------------------------------------------------------------------

    def _sod_violation_to_finding(
        self, v: SoDViolation, tenant_id: str,
    ) -> Finding:
        fid = _make_id("SOD", v.user_id, v.conflict.rule_id)
        severity = SEVERITY_MAP.get(v.risk_level, FindingSeverity.HIGH)

        f = Finding(
            finding_id=fid,
            finding_type=FindingType.SOD_VIOLATION,
            severity=severity,
            source=FindingSource.RISK_ENGINE,
            user_id=v.user_id,
            tenant_id=tenant_id,
            title=f"SoD: {v.conflict.function_a_name} × {v.conflict.function_b_name}",
            description=v.risk_description,
            details=v.to_dict(),
            related_roles=v.source_roles_a + v.source_roles_b,
            related_transactions=v.conflict.conflicting_txn_a + v.conflict.conflicting_txn_b,
            org_scope=v.conflict.org_overlap,
            risk_score={"critical": 100, "high": 60, "medium": 30, "low": 10}.get(v.risk_level, 0),
            business_impact=v.business_impact,
            rule_id=v.conflict.rule_id,
            violation_id=v.violation_id,
            sox_relevant=v.sox_relevant,
            regulatory_refs=v.regulatory_refs,
            status=FindingStatus.MITIGATED if v.is_mitigated else FindingStatus.OPEN,
        )

        # Auto-generate recommendations
        if not v.is_mitigated:
            # Recommend removing the less-critical role
            for role in v.source_roles_b:
                f.recommendations.append(Recommendation(
                    recommendation_id=_make_id("REC", fid, role),
                    finding_id=fid,
                    recommendation_type=RecommendationType.REMOVE_ROLE,
                    description=f"Remove role {role} to resolve SoD conflict",
                    target_user_id=v.user_id,
                    target_role_id=role,
                    priority=2,
                ))

            f.recommendations.append(Recommendation(
                recommendation_id=_make_id("REC", fid, "mitigate"),
                finding_id=fid,
                recommendation_type=RecommendationType.ADD_MITIGATION,
                description=f"Add mitigation control for {v.conflict.rule_name}",
                target_user_id=v.user_id,
                priority=1,
            ))

        return f

    def _sensitive_to_finding(
        self, v: SensitiveAccessViolation, tenant_id: str,
    ) -> Finding:
        fid = _make_id("SA", v.user_id, v.transaction)
        severity = SEVERITY_MAP.get(v.risk_level, FindingSeverity.MEDIUM)

        f = Finding(
            finding_id=fid,
            finding_type=FindingType.SENSITIVE_ACCESS,
            severity=severity,
            source=FindingSource.RISK_ENGINE,
            user_id=v.user_id,
            tenant_id=tenant_id,
            title=f"Sensitive Access: {v.transaction}",
            description=f"User has {'change' if v.has_change_access else 'display'} access to sensitive transaction {v.transaction}",
            related_roles=v.source_roles,
            related_transactions=[v.transaction],
            related_auth_objects=v.auth_objects,
            org_scope=v.org_scope,
            risk_score=60.0 if v.has_change_access else 30.0,
        )

        if v.has_change_access:
            f.recommendations.append(Recommendation(
                recommendation_id=_make_id("REC", fid, "review"),
                finding_id=fid,
                recommendation_type=RecommendationType.REVIEW_ACCESS,
                description=f"Review change access to {v.transaction}",
                target_user_id=v.user_id,
                target_transaction=v.transaction,
            ))

        return f

    def _critical_to_finding(
        self, v: CriticalActionViolation, tenant_id: str,
    ) -> Finding:
        fid = _make_id("CA", v.user_id, v.transaction)

        f = Finding(
            finding_id=fid,
            finding_type=FindingType.CRITICAL_ACTION,
            severity=FindingSeverity.CRITICAL,
            source=FindingSource.RISK_ENGINE,
            user_id=v.user_id,
            tenant_id=tenant_id,
            title=f"Critical: {v.transaction}",
            description=v.action_description,
            related_roles=v.source_roles,
            related_transactions=[v.transaction],
            risk_score=100.0,
        )

        f.recommendations.append(Recommendation(
            recommendation_id=_make_id("REC", fid, "review"),
            finding_id=fid,
            recommendation_type=RecommendationType.REVIEW_ACCESS,
            description=f"Urgent: review access to critical transaction {v.transaction}",
            target_user_id=v.user_id,
            target_transaction=v.transaction,
            priority=1,
        ))

        return f

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _add_finding(self, finding: Finding) -> None:
        """Add or update a finding (dedup by finding_id)."""
        existing = self._findings.get(finding.finding_id)
        if existing:
            # Update if the new finding is more severe or has more detail
            if finding.severity.value > existing.severity.value:
                existing.severity = finding.severity
            if finding.recommendations:
                existing.recommendations = finding.recommendations
            # Don't reopen resolved findings
        else:
            self._findings[finding.finding_id] = finding
            self._persist_to_db(finding)

    def _persist_to_db(self, finding: Finding) -> None:
        """Write-through: persist finding to database."""
        try:
            from db.database import db_manager
            from db.models.engines import FindingRecord as FindingRecordDB

            with db_manager.session_scope() as session:
                row = FindingRecordDB(
                    finding_id=finding.finding_id,
                    tenant_id=finding.tenant_id or "tenant_default",
                    finding_type=finding.finding_type.value,
                    severity=finding.severity.value,
                    source=finding.source.value,
                    status=finding.status.value,
                    user_id=finding.user_id,
                    title=finding.title,
                    description=finding.description,
                    risk_score=finding.risk_score,
                    business_impact=finding.business_impact,
                    sox_relevant=finding.sox_relevant,
                    rule_id=finding.rule_id,
                    violation_id=finding.violation_id,
                    campaign_id=finding.campaign_id,
                    request_id=finding.request_id,
                    related_roles=finding.related_roles,
                    related_transactions=finding.related_transactions,
                    related_auth_objects=finding.related_auth_objects,
                    org_scope=finding.org_scope,
                    regulatory_refs=finding.regulatory_refs,
                    recommendations=[
                        {"id": r.recommendation_id, "type": r.recommendation_type.value,
                         "description": r.description, "status": r.status.value}
                        for r in finding.recommendations
                    ],
                    evidence_ids=finding.evidence_ids,
                    detected_at=finding.detected_at,
                )
                session.add(row)
        except Exception as exc:
            logger.warning(f"Finding DB persist failed (in-memory intact): {exc}")


def _make_id(*parts: str) -> str:
    raw = ":".join(parts)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]
