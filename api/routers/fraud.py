"""
Fraud Detection API Router

Rule-based fraud detection with alert triage and case management:
  - Rule catalogue: define thresholds, patterns, ML model hooks
  - Automated alert ingestion and risk scoring
  - Alert lifecycle: investigate → confirm / dismiss
  - Case management: evidence, assignment, resolution
  - Dashboard: open alerts, case KPIs, false-positive rate
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import uuid

from db.database import get_db
from db.models.extended_modules import (
    FraudRule, FraudAlert, FraudCase,
    FraudAlertStatus, FraudCaseStatus,
)

router = APIRouter(tags=["Fraud Detection"])


# ---------------------------------------------------------------------------
# Tenant helper
# ---------------------------------------------------------------------------

def _get_tenant_id() -> str:
    from core.tenant import get_current_tenant
    ctx = get_current_tenant()
    return ctx.tenant_id if ctx else "default"


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


# ---------------------------------------------------------------------------
# 404 helpers
# ---------------------------------------------------------------------------

def _rule_or_404(db: Session, rule_id: str, tenant_id: str) -> FraudRule:
    obj = db.query(FraudRule).filter(
        FraudRule.id == rule_id,
        FraudRule.tenant_id == tenant_id,
    ).first()
    if not obj:
        raise HTTPException(status_code=404, detail=f"Fraud rule '{rule_id}' not found")
    return obj


def _alert_or_404(db: Session, alert_id: str, tenant_id: str) -> FraudAlert:
    obj = db.query(FraudAlert).filter(
        FraudAlert.id == alert_id,
        FraudAlert.tenant_id == tenant_id,
    ).first()
    if not obj:
        raise HTTPException(status_code=404, detail=f"Fraud alert '{alert_id}' not found")
    return obj


def _case_or_404(db: Session, case_id: str, tenant_id: str) -> FraudCase:
    obj = db.query(FraudCase).filter(
        FraudCase.id == case_id,
        FraudCase.tenant_id == tenant_id,
    ).first()
    if not obj:
        raise HTTPException(status_code=404, detail=f"Fraud case '{case_id}' not found")
    return obj


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class RuleCreate(BaseModel):
    rule_name: str
    rule_type: str = Field(..., description="threshold | pattern | velocity | ml_model | composite")
    description: Optional[str] = None
    condition_expression: Optional[str] = None
    threshold_value: Optional[float] = None
    risk_score_weight: float = Field(default=1.0, ge=0.0, le=10.0)
    is_active: bool = True
    data_sources: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None


class RuleUpdate(BaseModel):
    rule_name: Optional[str] = None
    description: Optional[str] = None
    condition_expression: Optional[str] = None
    threshold_value: Optional[float] = None
    risk_score_weight: Optional[float] = None
    is_active: Optional[bool] = None
    data_sources: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None


class AlertStatusUpdate(BaseModel):
    status: str = Field(..., description="investigating | confirmed | dismissed | escalated")
    notes: Optional[str] = None
    assigned_to: Optional[str] = None


class CaseCreate(BaseModel):
    title: str
    description: Optional[str] = None
    severity: str = Field(default="medium", description="critical | high | medium | low")
    source_alert_id: Optional[str] = None
    subject_user_id: Optional[str] = None
    subject_name: Optional[str] = None
    assigned_to: Optional[str] = None
    estimated_loss: Optional[float] = None
    currency: Optional[str] = "USD"
    evidence: Optional[List[Dict[str, Any]]] = None
    metadata: Optional[Dict[str, Any]] = None


class CaseUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    severity: Optional[str] = None
    status: Optional[str] = None
    assigned_to: Optional[str] = None
    resolution_notes: Optional[str] = None
    estimated_loss: Optional[float] = None
    confirmed_loss: Optional[float] = None
    evidence: Optional[List[Dict[str, Any]]] = None
    metadata: Optional[Dict[str, Any]] = None


# ---------------------------------------------------------------------------
# Rules
# ---------------------------------------------------------------------------

@router.get("/rules")
def list_rules(
    rule_type: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """List fraud detection rules."""
    q = db.query(FraudRule).filter(FraudRule.tenant_id == tenant_id)
    if rule_type:
        q = q.filter(FraudRule.rule_type == rule_type)
    if is_active is not None:
        q = q.filter(FraudRule.is_active == is_active)
    rules = q.order_by(FraudRule.rule_name).all()
    return {"total": len(rules), "rules": [r.to_dict() for r in rules]}


@router.post("/rules", status_code=201)
def create_rule(
    body: RuleCreate,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Create a new fraud detection rule."""
    rule = FraudRule(
        id=_new_id("FRR"),
        tenant_id=tenant_id,
        rule_name=body.rule_name,
        rule_type=body.rule_type,
        description=body.description,
        condition_expression=body.condition_expression,
        threshold_value=body.threshold_value,
        risk_score_weight=body.risk_score_weight,
        is_active=body.is_active,
        data_sources=body.data_sources or [],
        metadata_=body.metadata,
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule.to_dict()


@router.put("/rules/{id}")
def update_rule(
    id: str,
    body: RuleUpdate,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Update a fraud detection rule."""
    rule = _rule_or_404(db, id, tenant_id)
    updatable = [
        "rule_name", "description", "condition_expression",
        "threshold_value", "risk_score_weight", "is_active", "data_sources",
    ]
    for field in updatable:
        val = getattr(body, field)
        if val is not None:
            setattr(rule, field, val)
    if body.metadata is not None:
        rule.metadata_ = body.metadata
    db.commit()
    db.refresh(rule)
    return rule.to_dict()


@router.delete("/rules/{id}", status_code=204)
def delete_rule(
    id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Delete a fraud rule (soft-delete via is_active=False)."""
    rule = _rule_or_404(db, id, tenant_id)
    rule.is_active = False
    db.commit()


# ---------------------------------------------------------------------------
# Alerts
# ---------------------------------------------------------------------------

@router.get("/alerts")
def list_alerts(
    status: Optional[str] = Query(None),
    rule_id: Optional[str] = Query(None),
    risk_score_min: Optional[float] = Query(None, ge=0.0, le=100.0),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """List fraud alerts with filters and pagination."""
    q = db.query(FraudAlert).filter(FraudAlert.tenant_id == tenant_id)
    if status:
        q = q.filter(FraudAlert.status == status)
    if rule_id:
        q = q.filter(FraudAlert.rule_id == rule_id)
    if risk_score_min is not None:
        q = q.filter(FraudAlert.risk_score >= risk_score_min)
    total = q.count()
    alerts = q.order_by(FraudAlert.risk_score.desc(), FraudAlert.created_at.desc()) \
               .offset(offset).limit(limit).all()
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "alerts": [a.to_dict() for a in alerts],
    }


@router.get("/alerts/{id}")
def get_alert(
    id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Get full detail of a fraud alert."""
    return _alert_or_404(db, id, tenant_id).to_dict()


@router.put("/alerts/{id}/status")
def update_alert_status(
    id: str,
    body: AlertStatusUpdate,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """
    Transition an alert through its lifecycle.
    Valid transitions: open → investigating → confirmed | dismissed | escalated
    """
    alert = _alert_or_404(db, id, tenant_id)
    valid_statuses = {"investigating", "confirmed", "dismissed", "escalated"}
    if body.status not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status '{body.status}'. Must be one of: {valid_statuses}",
        )
    alert.status = body.status
    if body.notes:
        alert.investigator_notes = body.notes
    if body.assigned_to:
        alert.assigned_to = body.assigned_to
    if body.status in ("confirmed", "dismissed"):
        alert.closed_at = datetime.utcnow()
    db.commit()
    db.refresh(alert)
    return alert.to_dict()


@router.post("/alerts/{id}/open-case", status_code=201)
def open_case_from_alert(
    id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Convert a confirmed alert into a fraud investigation case."""
    alert = _alert_or_404(db, id, tenant_id)
    if alert.status not in ("confirmed", "escalated", "investigating"):
        raise HTTPException(
            status_code=400,
            detail="Alert must be in 'confirmed', 'escalated', or 'investigating' status to open a case",
        )
    # Check if a case already exists for this alert
    existing = db.query(FraudCase).filter(
        FraudCase.source_alert_id == id,
        FraudCase.tenant_id == tenant_id,
    ).first()
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Case '{existing.id}' already exists for this alert",
        )
    case = FraudCase(
        id=_new_id("FRC"),
        tenant_id=tenant_id,
        title=f"Case from Alert {id}",
        description=alert.alert_description if hasattr(alert, "alert_description") else None,
        severity="high" if alert.risk_score >= 75 else "medium",
        source_alert_id=id,
        subject_user_id=getattr(alert, "subject_user_id", None),
        status="open",
        evidence=[],
    )
    db.add(case)
    alert.status = "case_opened"
    alert.case_id = case.id
    db.commit()
    db.refresh(case)
    return case.to_dict()


# ---------------------------------------------------------------------------
# Cases
# ---------------------------------------------------------------------------

@router.get("/cases")
def list_cases(
    status: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    assigned_to: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """List fraud investigation cases."""
    q = db.query(FraudCase).filter(FraudCase.tenant_id == tenant_id)
    if status:
        q = q.filter(FraudCase.status == status)
    if severity:
        q = q.filter(FraudCase.severity == severity)
    if assigned_to:
        q = q.filter(FraudCase.assigned_to == assigned_to)
    cases = q.order_by(FraudCase.created_at.desc()).all()
    return {"total": len(cases), "cases": [c.to_dict() for c in cases]}


@router.get("/cases/{id}")
def get_case(
    id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Get full fraud case detail."""
    return _case_or_404(db, id, tenant_id).to_dict()


@router.post("/cases", status_code=201)
def create_case(
    body: CaseCreate,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Manually create a fraud investigation case."""
    case = FraudCase(
        id=_new_id("FRC"),
        tenant_id=tenant_id,
        title=body.title,
        description=body.description,
        severity=body.severity,
        source_alert_id=body.source_alert_id,
        subject_user_id=body.subject_user_id,
        subject_name=body.subject_name,
        assigned_to=body.assigned_to,
        estimated_loss=body.estimated_loss,
        currency=body.currency,
        evidence=body.evidence or [],
        status="open",
        metadata_=body.metadata,
    )
    db.add(case)
    db.commit()
    db.refresh(case)
    return case.to_dict()


@router.put("/cases/{id}")
def update_case(
    id: str,
    body: CaseUpdate,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Update a fraud case — add evidence, change status, record resolution."""
    case = _case_or_404(db, id, tenant_id)
    updatable = [
        "title", "description", "severity", "status", "assigned_to",
        "resolution_notes", "estimated_loss", "confirmed_loss", "evidence",
    ]
    for field in updatable:
        val = getattr(body, field)
        if val is not None:
            setattr(case, field, val)
    if body.status in ("closed", "resolved"):
        case.closed_at = datetime.utcnow()
    if body.metadata is not None:
        case.metadata_ = body.metadata
    db.commit()
    db.refresh(case)
    return case.to_dict()


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@router.get("/dashboard")
def get_fraud_dashboard(
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Fraud detection executive dashboard."""
    cutoff_30d = datetime.utcnow() - timedelta(days=30)

    open_alerts = db.query(FraudAlert).filter(
        FraudAlert.tenant_id == tenant_id,
        FraudAlert.status.in_([FraudAlertStatus.OPEN, FraudAlertStatus.INVESTIGATING]),
    ).count()

    open_cases = db.query(FraudCase).filter(
        FraudCase.tenant_id == tenant_id,
        FraudCase.status == FraudCaseStatus.OPEN,
    ).count()

    confirmed_fraud_30d = db.query(FraudAlert).filter(
        FraudAlert.tenant_id == tenant_id,
        FraudAlert.status == FraudAlertStatus.CONFIRMED_FRAUD,
        FraudAlert.reviewed_at >= cutoff_30d,
    ).count()

    dismissed_30d = db.query(FraudAlert).filter(
        FraudAlert.tenant_id == tenant_id,
        FraudAlert.status == FraudAlertStatus.DISMISSED,
        FraudAlert.reviewed_at >= cutoff_30d,
    ).count()

    total_closed_30d = confirmed_fraud_30d + dismissed_30d
    false_positive_rate = round(
        dismissed_30d / total_closed_30d * 100, 1
    ) if total_closed_30d > 0 else 0.0

    total_alerts = db.query(FraudAlert).filter(FraudAlert.tenant_id == tenant_id).count()
    active_rules = db.query(FraudRule).filter(
        FraudRule.tenant_id == tenant_id,
        FraudRule.is_active == True,
    ).count()

    return {
        "open_alerts": open_alerts,
        "open_cases": open_cases,
        "confirmed_fraud_30d": confirmed_fraud_30d,
        "false_positive_rate": false_positive_rate,
        "total_alerts": total_alerts,
        "active_rules": active_rules,
    }
