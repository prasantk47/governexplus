"""
GRC Analytics — Cross-module dashboards, trend analysis, and enterprise reporting.
Pulls live data from all modules and aggregates into executive-level insights.
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from api.dependencies import get_current_user
from db.database import get_db

router = APIRouter(tags=["GRC Analytics"])


def _get_tenant_id(user: dict = Depends(get_current_user)) -> str:
    return user.get("tenant_id", "default")


@router.get("/analytics/executive-summary")
def executive_summary(
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Executive GRC posture summary across all modules."""
    from db.models.risk_management import EnterpriseRisk
    from db.models.process_control import ProcessControl, ControlDeficiency, CCMExecution, CCMResult
    from db.models.audit_management import AuditFinding, FindingSeverity, FindingStatus
    from db.models.issue_tracker import GRCIssue
    from db.models.risk import RiskViolation
    from db.models.extended_modules import VendorIssue, FraudCase

    now = datetime.utcnow()
    thirty_days_ago = now - timedelta(days=30)

    # Risk
    total_risks = db.query(EnterpriseRisk).filter(EnterpriseRisk.tenant_id == tenant_id).count()
    open_risks = db.query(EnterpriseRisk).filter(
        EnterpriseRisk.tenant_id == tenant_id,
        EnterpriseRisk.status.notin_(["closed", "retired"])
    ).count()
    critical_risks = db.query(EnterpriseRisk).filter(
        EnterpriseRisk.tenant_id == tenant_id,
        EnterpriseRisk.inherent_impact >= 4,
        EnterpriseRisk.inherent_likelihood >= 4,
        EnterpriseRisk.status.notin_(["closed", "retired"])
    ).count()

    # Access violations
    total_violations = db.query(RiskViolation).filter(RiskViolation.tenant_id == tenant_id).count()
    open_violations = db.query(RiskViolation).filter(
        RiskViolation.tenant_id == tenant_id,
        RiskViolation.status.notin_(["resolved", "accepted", "mitigated"])
    ).count()

    # Controls
    total_controls = db.query(ProcessControl).filter(ProcessControl.tenant_id == tenant_id).count()
    deficiencies = db.query(ControlDeficiency).filter(
        ControlDeficiency.tenant_id == tenant_id,
        ControlDeficiency.status.notin_(["closed", "remediated"])
    ).count()

    # CCM
    ccm_failures = db.query(CCMExecution).filter(
        CCMExecution.tenant_id == tenant_id,
        CCMExecution.result == "fail",
        CCMExecution.executed_at >= thirty_days_ago,
    ).count()

    # Audit
    open_findings = db.query(AuditFinding).filter(
        AuditFinding.tenant_id == tenant_id,
        AuditFinding.status.notin_(["closed", "resolved"])
    ).count()
    critical_findings = db.query(AuditFinding).filter(
        AuditFinding.tenant_id == tenant_id,
        AuditFinding.severity == "critical",
        AuditFinding.status.notin_(["closed", "resolved"])
    ).count()

    # Issues
    open_issues = db.query(GRCIssue).filter(
        GRCIssue.tenant_id == tenant_id,
        GRCIssue.status.notin_(["closed", "accepted"])
    ).count()
    overdue_issues = db.query(GRCIssue).filter(
        GRCIssue.tenant_id == tenant_id,
        GRCIssue.due_date < now,
        GRCIssue.status.notin_(["closed", "accepted"])
    ).count()

    # Fraud
    open_fraud = db.query(FraudCase).filter(
        FraudCase.tenant_id == tenant_id,
        FraudCase.status.notin_(["closed", "dismissed"])
    ).count()

    return {
        "as_of": now.isoformat(),
        "risk": {
            "total": total_risks,
            "open": open_risks,
            "critical": critical_risks,
        },
        "access_conflicts": {
            "total_violations": total_violations,
            "open": open_violations,
        },
        "controls": {
            "total": total_controls,
            "open_deficiencies": deficiencies,
            "ccm_failures_30d": ccm_failures,
        },
        "audit": {
            "open_findings": open_findings,
            "critical_findings": critical_findings,
        },
        "issues": {
            "open": open_issues,
            "overdue": overdue_issues,
        },
        "fraud": {
            "open_cases": open_fraud,
        },
    }


@router.get("/analytics/risk-trend")
def risk_trend(
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
    months: int = Query(6, ge=1, le=24),
):
    """Risk count trend over the past N months."""
    from db.models.risk_management import EnterpriseRisk
    now = datetime.utcnow()
    result = []
    for i in range(months - 1, -1, -1):
        period_end = now.replace(day=1) - timedelta(days=i * 30)
        period_label = period_end.strftime("%b %Y")
        count = db.query(EnterpriseRisk).filter(
            EnterpriseRisk.tenant_id == tenant_id,
            EnterpriseRisk.created_at <= period_end,
        ).count()
        result.append({"period": period_label, "count": count})
    return {"trend": result}


@router.get("/analytics/violations-by-module")
def violations_by_module(
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Access conflict violations breakdown by risk category."""
    from db.models.risk import RiskViolation
    rows = (db.query(RiskViolation.risk_type, func.count(RiskViolation.id))
              .filter(RiskViolation.tenant_id == tenant_id)
              .group_by(RiskViolation.risk_type)
              .all())
    return {"by_category": [{"category": r[0] or "other", "count": r[1]} for r in rows]}


@router.get("/analytics/control-effectiveness")
def control_effectiveness(
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Control effectiveness distribution across all controls."""
    from db.models.process_control import ProcessControl, ControlTest, TestResult
    controls = db.query(ProcessControl).filter(ProcessControl.tenant_id == tenant_id).all()
    if not controls:
        return {"controls_tested": 0, "effective": 0, "partially_effective": 0, "ineffective": 0, "not_tested": 0}

    effective = partially_effective = ineffective = not_tested = 0
    for ctrl in controls:
        tests = db.query(ControlTest).filter(
            ControlTest.control_id == ctrl.control_id,
            ControlTest.tenant_id == tenant_id,
        ).order_by(ControlTest.created_at.desc()).first()

        if not tests:
            not_tested += 1
        elif tests.result == "pass":
            effective += 1
        elif tests.result == "partial":
            partially_effective += 1
        else:
            ineffective += 1

    total = len(controls)
    return {
        "total_controls": total,
        "controls_tested": total - not_tested,
        "effective": effective,
        "partially_effective": partially_effective,
        "ineffective": ineffective,
        "not_tested": not_tested,
        "effectiveness_rate": round((effective / total * 100), 1) if total > 0 else 0,
    }


@router.get("/analytics/audit-findings-by-severity")
def findings_by_severity(
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Open audit findings grouped by severity."""
    from db.models.audit_management import AuditFinding
    rows = (db.query(AuditFinding.severity, func.count(AuditFinding.finding_id))
              .filter(
                  AuditFinding.tenant_id == tenant_id,
                  AuditFinding.status.notin_(["closed", "resolved"])
              )
              .group_by(AuditFinding.severity)
              .all())
    return {"by_severity": [{"severity": r[0] or "unknown", "count": r[1]} for r in rows]}


@router.get("/analytics/issues-aging")
def issues_aging(
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Open issues grouped by how long they've been open."""
    from db.models.issue_tracker import GRCIssue
    now = datetime.utcnow()
    open_issues = db.query(GRCIssue).filter(
        GRCIssue.tenant_id == tenant_id,
        GRCIssue.status.notin_(["closed", "accepted"])
    ).all()

    buckets = {"0-7d": 0, "8-30d": 0, "31-90d": 0, "91-180d": 0, "180d+": 0}
    for issue in open_issues:
        age = (now - issue.created_at).days if issue.created_at else 0
        if age <= 7:
            buckets["0-7d"] += 1
        elif age <= 30:
            buckets["8-30d"] += 1
        elif age <= 90:
            buckets["31-90d"] += 1
        elif age <= 180:
            buckets["91-180d"] += 1
        else:
            buckets["180d+"] += 1

    return {"total_open": len(open_issues), "aging_buckets": buckets}


@router.get("/analytics/vendor-risk-distribution")
def vendor_risk(
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Vendor risk rating distribution."""
    from db.models.extended_modules import Vendor
    rows = (db.query(Vendor.risk_rating, func.count(Vendor.vendor_id))
              .filter(Vendor.tenant_id == tenant_id)
              .group_by(Vendor.risk_rating)
              .all())
    return {"by_rating": [{"rating": r[0] or "unknown", "count": r[1]} for r in rows]}


@router.get("/analytics/kri-breach-trend")
def kri_breach_trend(
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
    months: int = Query(6, ge=1, le=12),
):
    """KRI breach events over time."""
    from db.models.risk_management import KRIMeasurement
    now = datetime.utcnow()
    result = []
    for i in range(months - 1, -1, -1):
        period_start = (now.replace(day=1) - timedelta(days=i * 30))
        period_end = period_start + timedelta(days=30)
        label = period_start.strftime("%b %Y")
        breaches = db.query(KRIMeasurement).filter(
            KRIMeasurement.tenant_id == tenant_id,
            KRIMeasurement.breach_flag == True,
            KRIMeasurement.measurement_date >= period_start,
            KRIMeasurement.measurement_date < period_end,
        ).count()
        result.append({"period": label, "breaches": breaches})
    return {"trend": result}


@router.get("/analytics/module-health")
def module_health(
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """High-level health score per GRC module for the operations dashboard."""
    from db.models.risk_management import EnterpriseRisk, KeyRiskIndicator
    from db.models.process_control import ProcessControl, ControlDeficiency
    from db.models.audit_management import AuditFinding, AuditEngagement
    from db.models.extended_modules import Vendor, VendorIssue
    from db.models.issue_tracker import GRCIssue

    def pct_healthy(good: int, total: int) -> int:
        if total == 0:
            return 100
        return round(good / total * 100)

    # Risk
    all_risks = db.query(EnterpriseRisk).filter(EnterpriseRisk.tenant_id == tenant_id).count()
    treated_risks = db.query(EnterpriseRisk).filter(
        EnterpriseRisk.tenant_id == tenant_id,
        EnterpriseRisk.status.in_(["closed", "mitigated", "accepted"])
    ).count()

    # Controls
    all_controls = db.query(ProcessControl).filter(ProcessControl.tenant_id == tenant_id).count()
    open_deficiencies = db.query(ControlDeficiency).filter(
        ControlDeficiency.tenant_id == tenant_id,
        ControlDeficiency.status.notin_(["closed", "remediated"])
    ).count()

    # Audit
    all_findings = db.query(AuditFinding).filter(AuditFinding.tenant_id == tenant_id).count()
    closed_findings = db.query(AuditFinding).filter(
        AuditFinding.tenant_id == tenant_id,
        AuditFinding.status.in_(["closed", "resolved"])
    ).count()

    # Issues
    all_issues = db.query(GRCIssue).filter(GRCIssue.tenant_id == tenant_id).count()
    closed_issues = db.query(GRCIssue).filter(
        GRCIssue.tenant_id == tenant_id,
        GRCIssue.status.in_(["closed", "accepted"])
    ).count()

    # TPRM
    all_vendors = db.query(Vendor).filter(Vendor.tenant_id == tenant_id).count()
    open_vendor_issues = db.query(VendorIssue).filter(
        VendorIssue.tenant_id == tenant_id,
        VendorIssue.status.notin_(["resolved", "closed"])
    ).count()

    return {
        "modules": [
            {
                "module": "Enterprise Risk Engine",
                "health_score": pct_healthy(treated_risks, all_risks),
                "total": all_risks,
                "open": all_risks - treated_risks,
            },
            {
                "module": "Control Intelligence",
                "health_score": pct_healthy(all_controls - open_deficiencies, all_controls) if all_controls else 100,
                "total": all_controls,
                "open_deficiencies": open_deficiencies,
            },
            {
                "module": "Audit Command Center",
                "health_score": pct_healthy(closed_findings, all_findings),
                "total": all_findings,
                "open": all_findings - closed_findings,
            },
            {
                "module": "Issue Tracker",
                "health_score": pct_healthy(closed_issues, all_issues),
                "total": all_issues,
                "open": all_issues - closed_issues,
            },
            {
                "module": "Third-Party Risk",
                "health_score": pct_healthy(all_vendors - open_vendor_issues, all_vendors) if all_vendors else 100,
                "total": all_vendors,
                "open_issues": open_vendor_issues,
            },
        ]
    }
