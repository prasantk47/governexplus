"""
GRC Dashboard API Router

Unified executive GRC dashboard (XI-05) and risk-control matrix (XI-03).

Queries span all GRC module tables:
  - Access Risk (SoD violations, severity breakdown)
  - Control Health (process controls, deficiencies)
  - Enterprise Risk (top risks, appetite breaches)
  - Audit Status (engagements, findings, overdue actions)

Uses direct DB queries — no manager class needed.
"""

from fastapi import APIRouter, Depends, Query
from typing import Dict, List, Optional, Any
from datetime import datetime
from sqlalchemy.orm import Session

from db.database import get_db

# Access control models
from db.models.risk import RiskViolation, ViolationStatus

# Process control models
from db.models.process_control import (
    ProcessControl, ControlStatus, ControlDeficiency, DeficiencyStatus,
    ControlTest, TestResult,
)

# Risk management models
from db.models.risk_management import (
    EnterpriseRisk, RiskStatus, RiskAppetite,
)

# Audit management models
from db.models.audit_management import (
    AuditEngagement, EngagementStatus,
    AuditFinding, FindingSeverity, FindingStatus,
    AuditManagementAction, ActionStatus,
)

router = APIRouter(tags=["GRC Dashboard"])


# ---------------------------------------------------------------------------
# Tenant helper
# ---------------------------------------------------------------------------

def _get_tenant_id() -> str:
    from core.tenant import get_current_tenant
    ctx = get_current_tenant()
    return ctx.tenant_id if ctx else "default"


# ---------------------------------------------------------------------------
# Internal query helpers
# ---------------------------------------------------------------------------

def _access_risk_summary(db: Session, tenant_id: str) -> Dict[str, Any]:
    """Aggregate access-risk metrics from the SoD violation table."""
    violations = db.query(RiskViolation).filter(
        RiskViolation.tenant_id == tenant_id,
        RiskViolation.status == ViolationStatus.OPEN,
    ).all()

    by_severity: Dict[str, int] = {}
    for v in violations:
        sev = v.severity.value if v.severity else "unknown"
        by_severity[sev] = by_severity.get(sev, 0) + 1

    return {
        "open_violations": len(violations),
        "by_severity": by_severity,
        "critical": by_severity.get("critical", 0),
        "high": by_severity.get("high", 0),
        "medium": by_severity.get("medium", 0),
        "low": by_severity.get("low", 0),
    }


def _control_health_summary(db: Session, tenant_id: str) -> Dict[str, Any]:
    """Aggregate process control effectiveness metrics."""
    total = db.query(ProcessControl).filter(
        ProcessControl.tenant_id == tenant_id,
        ProcessControl.is_active.is_(True),
    ).count()

    active = db.query(ProcessControl).filter(
        ProcessControl.tenant_id == tenant_id,
        ProcessControl.is_active.is_(True),
        ProcessControl.status == ControlStatus.ACTIVE,
    ).count()

    open_deficiencies = db.query(ControlDeficiency).filter(
        ControlDeficiency.tenant_id == tenant_id,
        ControlDeficiency.status == DeficiencyStatus.OPEN,
    ).count()

    effective_tests = db.query(ControlTest).filter(
        ControlTest.tenant_id == tenant_id,
        ControlTest.result == TestResult.EFFECTIVE,
    ).count()

    total_tested = db.query(ControlTest).filter(
        ControlTest.tenant_id == tenant_id,
        ControlTest.result.isnot(None),
    ).count()

    effectiveness_pct = round(effective_tests / total_tested * 100, 1) if total_tested else None

    return {
        "total_controls": total,
        "active_controls": active,
        "open_deficiencies": open_deficiencies,
        "effectiveness_pct": effectiveness_pct,
        "total_tested": total_tested,
    }


def _enterprise_risk_summary(db: Session, tenant_id: str) -> Dict[str, Any]:
    """Aggregate enterprise risk register metrics."""
    all_risks = db.query(EnterpriseRisk).filter(
        EnterpriseRisk.tenant_id == tenant_id,
        EnterpriseRisk.is_active.is_(True),
        EnterpriseRisk.status.notin_([RiskStatus.CLOSED]),
    ).order_by(EnterpriseRisk.residual_score.desc().nullslast()).all()

    top5 = all_risks[:5]
    scored = [r for r in all_risks if r.residual_score is not None]
    avg_residual = (
        round(sum(r.residual_score for r in scored) / len(scored), 2)
        if scored else None
    )

    # Appetite breaches: residual > appetite
    appetites = db.query(RiskAppetite).filter(
        RiskAppetite.tenant_id == tenant_id,
    ).all()
    appetite_by_category = {a.category: a.appetite_score for a in appetites}
    all_appetite = appetite_by_category.get("all")

    breaches = 0
    for r in all_risks:
        threshold = appetite_by_category.get(r.category.value if r.category else "") or all_appetite
        if threshold and r.residual_score and r.residual_score > threshold:
            breaches += 1

    return {
        "total_open_risks": len(all_risks),
        "avg_residual_score": avg_residual,
        "appetite_breaches": breaches,
        "top_5_risks": [
            {
                "risk_id": r.risk_id,
                "title": r.title,
                "category": r.category.value if r.category else None,
                "residual_score": r.residual_score,
                "status": r.status.value if r.status else None,
            }
            for r in top5
        ],
    }


def _audit_status_summary(db: Session, tenant_id: str) -> Dict[str, Any]:
    """Aggregate internal audit status metrics."""
    in_progress = db.query(AuditEngagement).filter(
        AuditEngagement.tenant_id == tenant_id,
        AuditEngagement.status.in_([
            EngagementStatus.ANNOUNCED,
            EngagementStatus.FIELDWORK,
            EngagementStatus.DRAFT_REPORT,
        ]),
    ).count()

    open_findings = db.query(AuditFinding).filter(
        AuditFinding.tenant_id == tenant_id,
        AuditFinding.status.notin_([FindingStatus.CLOSED]),
    ).all()

    findings_by_severity: Dict[str, int] = {}
    for f in open_findings:
        sev = f.severity.value if f.severity else "unknown"
        findings_by_severity[sev] = findings_by_severity.get(sev, 0) + 1

    overdue_actions = db.query(AuditManagementAction).filter(
        AuditManagementAction.tenant_id == tenant_id,
        AuditManagementAction.status == ActionStatus.OVERDUE,
    ).count()

    return {
        "engagements_in_progress": in_progress,
        "open_findings": len(open_findings),
        "findings_by_severity": findings_by_severity,
        "critical_findings": findings_by_severity.get("critical", 0),
        "high_findings": findings_by_severity.get("high", 0),
        "overdue_actions": overdue_actions,
    }


# ===========================================================================
# Endpoints
# ===========================================================================

@router.get("/dashboard")
def get_grc_dashboard(
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """
    Unified executive GRC dashboard (XI-05).

    Returns aggregated metrics across all four GRC pillars:
      1. Access Risk (SoD violations)
      2. Control Health (process controls)
      3. Enterprise Risk (risk register)
      4. Audit Status (engagements and findings)
    """
    return {
        "generated_at": datetime.utcnow().isoformat(),
        "tenant_id": tenant_id,
        "access_risk": _access_risk_summary(db, tenant_id),
        "control_health": _control_health_summary(db, tenant_id),
        "enterprise_risk": _enterprise_risk_summary(db, tenant_id),
        "audit_status": _audit_status_summary(db, tenant_id),
    }


@router.get("/risk-control-matrix")
def get_risk_control_matrix(
    category: Optional[str] = Query(None, description="Filter by risk category"),
    org_unit_id: Optional[int] = Query(None, description="Filter by org unit PK"),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """
    Risk-Control Matrix (XI-03).

    Shows which enterprise risks are linked to which process controls and
    highlights coverage gaps (risks with no controls and controls with no risks).
    """
    # Fetch active risks
    risk_q = db.query(EnterpriseRisk).filter(
        EnterpriseRisk.tenant_id == tenant_id,
        EnterpriseRisk.is_active.is_(True),
        EnterpriseRisk.status.notin_([RiskStatus.CLOSED]),
    )
    if category:
        from db.models.risk_management import RiskCategory
        try:
            risk_q = risk_q.filter(EnterpriseRisk.category == RiskCategory(category))
        except ValueError:
            pass
    if org_unit_id is not None:
        risk_q = risk_q.filter(EnterpriseRisk.org_unit_id == org_unit_id)

    risks = risk_q.all()

    # Fetch active controls
    controls = db.query(ProcessControl).filter(
        ProcessControl.tenant_id == tenant_id,
        ProcessControl.is_active.is_(True),
    ).all()

    # Build lookup: control PK -> control_id string
    ctrl_pk_to_id: Dict[int, str] = {c.id: c.control_id for c in controls}
    ctrl_id_to_data: Dict[str, Dict[str, Any]] = {c.control_id: c.to_dict() for c in controls}

    # Build risk rows with their linked controls
    risk_rows: List[Dict[str, Any]] = []
    covered_risk_ids: set = set()

    for r in risks:
        linked_ctrl_ids = r.related_control_ids or []
        linked_controls_detail = [
            ctrl_id_to_data[cid]
            for cid in linked_ctrl_ids
            if cid in ctrl_id_to_data
        ]
        has_coverage = len(linked_controls_detail) > 0
        if has_coverage:
            covered_risk_ids.add(r.risk_id)

        # Effectiveness of linked controls
        effectiveness_ratings: List[Optional[float]] = []
        for ctrl in linked_controls_detail:
            test = db.query(ControlTest).filter(
                ControlTest.control_id.in_(
                    [c.id for c in controls if c.control_id == ctrl["control_id"]]
                ),
                ControlTest.tenant_id == tenant_id,
                ControlTest.result.isnot(None),
            ).order_by(ControlTest.created_at.desc()).first()
            if test and test.result:
                effectiveness_ratings.append(
                    1.0 if test.result == TestResult.EFFECTIVE
                    else 0.5 if test.result == TestResult.PARTIALLY_EFFECTIVE
                    else 0.0
                )

        avg_effectiveness = (
            round(sum(effectiveness_ratings) / len(effectiveness_ratings), 2)
            if effectiveness_ratings else None
        )

        risk_rows.append({
            "risk_id": r.risk_id,
            "risk_title": r.title,
            "category": r.category.value if r.category else None,
            "residual_score": r.residual_score,
            "status": r.status.value if r.status else None,
            "linked_control_count": len(linked_controls_detail),
            "linked_controls": [
                {"control_id": c["control_id"], "name": c["name"], "status": c["status"]}
                for c in linked_controls_detail
            ],
            "coverage_gap": not has_coverage,
            "avg_control_effectiveness": avg_effectiveness,
        })

    # Controls that are not linked to any risk
    all_linked_ctrl_ids_in_risks: set = set()
    for r in risks:
        for cid in (r.related_control_ids or []):
            all_linked_ctrl_ids_in_risks.add(cid)

    orphan_controls = [
        {"control_id": c.control_id, "name": c.name, "status": c.status.value if c.status else None}
        for c in controls
        if c.control_id not in all_linked_ctrl_ids_in_risks
    ]

    # Unlinked risks (no controls at all)
    uncovered_risks = [row for row in risk_rows if row["coverage_gap"]]

    return {
        "generated_at": datetime.utcnow().isoformat(),
        "summary": {
            "total_risks": len(risks),
            "risks_with_coverage": len(covered_risk_ids),
            "risks_without_coverage": len(uncovered_risks),
            "total_controls": len(controls),
            "orphan_controls": len(orphan_controls),
            "coverage_pct": round(len(covered_risk_ids) / len(risks) * 100, 1) if risks else 0,
        },
        "risk_control_matrix": risk_rows,
        "orphan_controls": orphan_controls,
    }
