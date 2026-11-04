"""
Board / Executive Reporting API Router

Aggregates cross-module KPIs into board-ready risk and compliance snapshots.
Provides executive dashboard data, committee pack generation, and trend analysis.
"""

from fastapi import APIRouter, Depends, Query, Body
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from db.database import get_db

router = APIRouter(tags=["Board Reporting"])


def _get_tenant_id() -> str:
    from core.tenant import get_current_tenant
    ctx = get_current_tenant()
    return ctx.tenant_id if ctx else "default"


@router.get("/executive-summary")
def executive_summary(
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Cross-module executive summary aggregation."""
    from db.models.risk_management import EnterpriseRisk, KRIIndicator, RiskViolation
    from db.models.audit_management import AuditFinding, AuditEngagement
    from db.models.governance_extended import OperationalLossEvent
    from db.models.sox_icfr import ICFRControl, SOXSignoff
    from db.models.privacy import DataBreachIncident, DSARRequest

    now = datetime.utcnow()
    thirty_days_ago = now - timedelta(days=30)

    # Risk metrics
    risks = db.query(EnterpriseRisk).filter(
        EnterpriseRisk.tenant_id == tenant_id,
        EnterpriseRisk.is_active.is_(True),
    ).all()
    critical_risks = [r for r in risks if (r.residual_score or 0) >= 15]
    high_risks = [r for r in risks if 9 <= (r.residual_score or 0) < 15]

    # SOD violations
    violations = db.query(RiskViolation).filter(
        RiskViolation.tenant_id == tenant_id,
        RiskViolation.status.in_(["open", "pending_review"]),
    ).all()
    critical_violations = [v for v in violations if getattr(v.severity, 'value', v.severity) in ("critical", "high")]

    # Audit findings
    findings = db.query(AuditFinding).filter(
        AuditFinding.tenant_id == tenant_id,
        AuditFinding.status.notin_(["closed", "accepted"]),
    ).all() if hasattr(AuditFinding, 'tenant_id') else []
    critical_findings = [f for f in findings if getattr(f.severity, 'value', f.severity) in ("critical", "high")]

    # KRIs in breach
    kris = db.query(KRIIndicator).filter(
        KRIIndicator.tenant_id == tenant_id,
        KRIIndicator.is_active.is_(True),
    ).all()
    kris_in_breach = [k for k in kris if getattr(k.status, 'value', k.status) == "breach"]

    # SOX
    icfr = db.query(ICFRControl).filter(
        ICFRControl.tenant_id == tenant_id,
        ICFRControl.is_active.is_(True),
        ICFRControl.is_key_control.is_(True),
    ).all()
    material_weaknesses = [c for c in icfr if c.deficiency_type == "material_weakness"]

    # Privacy
    open_breaches = db.query(DataBreachIncident).filter(
        DataBreachIncident.tenant_id == tenant_id,
        DataBreachIncident.status.notin_(["closed"]),
    ).all()
    overdue_dsars = db.query(DSARRequest).filter(
        DSARRequest.tenant_id == tenant_id,
        DSARRequest.deadline < now,
        DSARRequest.status.notin_(["completed", "rejected"]),
    ).all()

    # Operational losses (last 30 days)
    recent_losses = db.query(OperationalLossEvent).filter(
        OperationalLossEvent.tenant_id == tenant_id,
        OperationalLossEvent.occurred_at >= thirty_days_ago,
        OperationalLossEvent.is_active.is_(True),
    ).all()
    total_loss_30d = sum(float(e.gross_loss or 0) for e in recent_losses)

    return {
        "as_of": now.isoformat(),
        "risk": {
            "total_risks": len(risks),
            "critical": len(critical_risks),
            "high": len(high_risks),
            "kris_in_breach": len(kris_in_breach),
        },
        "access_risk": {
            "open_violations": len(violations),
            "critical_violations": len(critical_violations),
        },
        "audit": {
            "open_findings": len(findings),
            "critical_findings": len(critical_findings),
        },
        "sox": {
            "key_controls": len(icfr),
            "material_weaknesses": len(material_weaknesses),
        },
        "privacy": {
            "open_breaches": len(open_breaches),
            "overdue_dsars": len(overdue_dsars),
        },
        "operational_loss": {
            "incidents_30d": len(recent_losses),
            "gross_loss_30d": round(total_loss_30d, 2),
        },
    }


@router.get("/risk-heat-snapshot")
def risk_heat_snapshot(
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Risk distribution by residual score for heat map visualization."""
    from db.models.risk_management import EnterpriseRisk
    risks = db.query(EnterpriseRisk).filter(
        EnterpriseRisk.tenant_id == tenant_id,
        EnterpriseRisk.is_active.is_(True),
    ).all()
    matrix: Dict[str, Dict[str, int]] = {}
    for r in risks:
        impact = str(r.impact_score or 0)
        likelihood = str(r.likelihood_score or 0)
        if impact not in matrix:
            matrix[impact] = {}
        matrix[impact][likelihood] = matrix[impact].get(likelihood, 0) + 1
    return {"matrix": matrix, "total": len(risks)}


@router.get("/compliance-status")
def compliance_status(
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Compliance assessment status across frameworks."""
    from db.models.governance import ComplianceControl
    controls = db.query(ComplianceControl).filter(
        ComplianceControl.tenant_id == tenant_id,
        ComplianceControl.is_active.is_(True),
    ).all() if _has_model("ComplianceControl") else []
    by_framework: Dict[str, Dict[str, int]] = {}
    for c in controls:
        fw = c.framework or "unknown"
        status = getattr(c.status, 'value', c.status) or "unknown"
        if fw not in by_framework:
            by_framework[fw] = {"compliant": 0, "non_compliant": 0, "partial": 0, "not_assessed": 0}
        key = "compliant" if status == "compliant" else ("non_compliant" if status == "non_compliant" else ("partial" if status == "partial" else "not_assessed"))
        by_framework[fw][key] = by_framework[fw].get(key, 0) + 1
    return {"frameworks": by_framework}


@router.get("/trend-data")
def trend_data(
    days: int = Query(90, ge=7, le=365),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Historical trend for open risks, violations, and findings."""
    from db.models.risk_management import EnterpriseRisk, RiskViolation
    now = datetime.utcnow()
    start = now - timedelta(days=days)
    # Return weekly buckets
    buckets: List[Dict[str, Any]] = []
    current = start
    while current <= now:
        week_end = current + timedelta(days=7)
        buckets.append({
            "week_start": current.date().isoformat(),
            "risks_created": db.query(EnterpriseRisk).filter(
                EnterpriseRisk.tenant_id == tenant_id,
                EnterpriseRisk.created_at >= current,
                EnterpriseRisk.created_at < week_end,
            ).count(),
            "violations_detected": db.query(RiskViolation).filter(
                RiskViolation.tenant_id == tenant_id,
                RiskViolation.created_at >= current,
                RiskViolation.created_at < week_end,
            ).count(),
        })
        current = week_end
    return {"buckets": buckets, "period_days": days}


def _has_model(name: str) -> bool:
    try:
        import db.models.governance  # noqa
        return hasattr(db.models.governance, name)
    except ImportError:
        return False
