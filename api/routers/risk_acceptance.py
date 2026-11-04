"""
Risk Acceptance Register API Router

Manages formal risk acceptance decisions with rationale, authorized signatories,
expiry dates, and renewal tracking (RM-ACC).
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import uuid

from db.database import get_db
from db.models.risk_management import EnterpriseRisk, RiskAcceptance

router = APIRouter(prefix="/risk-management/acceptances", tags=["Risk Acceptance Register"])


def _get_tenant_id() -> str:
    from core.tenant import get_current_tenant
    ctx = get_current_tenant()
    return ctx.tenant_id if ctx else "default"


def _new_id() -> str:
    return f"ACC_{uuid.uuid4().hex[:12].upper()}"


def _acc_or_404(db: Session, acceptance_id: str, tenant_id: str) -> RiskAcceptance:
    a = db.query(RiskAcceptance).filter(
        RiskAcceptance.acceptance_id == acceptance_id,
        RiskAcceptance.tenant_id == tenant_id,
        RiskAcceptance.is_active.is_(True),
    ).first()
    if not a:
        raise HTTPException(status_code=404, detail=f"Acceptance '{acceptance_id}' not found")
    return a


def _risk_level(score: Optional[float]) -> str:
    if score is None:
        return "unknown"
    if score >= 20:
        return "critical"
    if score >= 12:
        return "high"
    if score >= 6:
        return "medium"
    return "low"


# ===========================================================================
# CRUD
# ===========================================================================

@router.post("", status_code=201)
def create_acceptance(
    body: Dict[str, Any] = Body(default={}),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Formally accept a risk with rationale and authorization."""
    risk_id = body.get("risk_id", "")
    if not risk_id:
        raise HTTPException(status_code=400, detail="risk_id is required")

    # Snapshot risk details
    risk = db.query(EnterpriseRisk).filter(
        EnterpriseRisk.risk_id == risk_id,
        EnterpriseRisk.tenant_id == tenant_id,
        EnterpriseRisk.is_active.is_(True),
    ).first()

    expiry_str = body.get("expiry_date")
    expiry_date = datetime.fromisoformat(expiry_str) if expiry_str else datetime.utcnow() + timedelta(days=365)

    effective_str = body.get("effective_date")
    effective_date = datetime.fromisoformat(effective_str) if effective_str else datetime.utcnow()

    a = RiskAcceptance(
        acceptance_id=_new_id(),
        tenant_id=tenant_id,
        risk_id=risk_id,
        risk_title=risk.title if risk else body.get("risk_title", risk_id),
        decision=body.get("decision", "accepted"),
        rationale=body.get("rationale", ""),
        conditions=body.get("conditions"),
        financial_exposure=body.get("financial_exposure"),
        authorized_by=body.get("authorized_by", ""),
        authorized_by_role=body.get("authorized_by_role"),
        authorized_at=datetime.utcnow(),
        second_approver=body.get("second_approver"),
        effective_date=effective_date,
        expiry_date=expiry_date,
        renewal_reminder_days=body.get("renewal_reminder_days", 30),
        residual_score_snapshot=risk.residual_score if risk else None,
        risk_level_snapshot=_risk_level(risk.residual_score if risk else None),
        is_active=True,
        extra=body.get("extra"),
    )

    # Update the risk status to accepted
    if risk:
        risk.status = "accepted"

    db.add(a)
    db.commit()
    db.refresh(a)
    return a.to_dict()


@router.get("")
def list_acceptances(
    decision: Optional[str] = Query(None),
    expiring_days: Optional[int] = Query(None, description="Expiring within N days"),
    include_expired: bool = Query(False),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """List all risk acceptances with optional filters."""
    q = db.query(RiskAcceptance).filter(
        RiskAcceptance.tenant_id == tenant_id,
        RiskAcceptance.is_active.is_(True),
    )

    if decision:
        q = q.filter(RiskAcceptance.decision == decision)

    if not include_expired:
        q = q.filter(
            (RiskAcceptance.expiry_date == None) |
            (RiskAcceptance.expiry_date > datetime.utcnow())
        )

    if expiring_days is not None:
        cutoff = datetime.utcnow() + timedelta(days=expiring_days)
        q = q.filter(
            RiskAcceptance.expiry_date != None,
            RiskAcceptance.expiry_date <= cutoff,
            RiskAcceptance.expiry_date > datetime.utcnow(),
        )

    acceptances = q.order_by(RiskAcceptance.created_at.desc()).all()

    # Annotate expiry status
    now = datetime.utcnow()
    result = []
    for a in acceptances:
        d = a.to_dict()
        if a.expiry_date:
            days_left = (a.expiry_date - now).days
            d["days_until_expiry"] = days_left
            d["is_expired"] = days_left < 0
            d["expiring_soon"] = 0 <= days_left <= (a.renewal_reminder_days or 30)
        else:
            d["days_until_expiry"] = None
            d["is_expired"] = False
            d["expiring_soon"] = False
        result.append(d)

    return {"total": len(result), "acceptances": result}


@router.get("/summary")
def acceptances_summary(
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Summary dashboard for risk acceptance register."""
    all_active = db.query(RiskAcceptance).filter(
        RiskAcceptance.tenant_id == tenant_id,
        RiskAcceptance.is_active.is_(True),
    ).all()

    now = datetime.utcnow()
    total = len(all_active)
    expired = sum(1 for a in all_active if a.expiry_date and a.expiry_date < now)
    expiring_30d = sum(
        1 for a in all_active
        if a.expiry_date and now < a.expiry_date <= now + timedelta(days=30)
    )
    by_decision = {}
    by_risk_level = {}
    for a in all_active:
        d = getattr(a.decision, 'value', a.decision) or "accepted"
        by_decision[d] = by_decision.get(d, 0) + 1
        rl = a.risk_level_snapshot or "unknown"
        by_risk_level[rl] = by_risk_level.get(rl, 0) + 1

    return {
        "total": total,
        "expired": expired,
        "expiring_30d": expiring_30d,
        "active": total - expired,
        "by_decision": by_decision,
        "by_risk_level": by_risk_level,
    }


@router.get("/{acceptance_id}")
def get_acceptance(
    acceptance_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    return _acc_or_404(db, acceptance_id, tenant_id).to_dict()


@router.put("/{acceptance_id}")
def update_acceptance(
    acceptance_id: str,
    body: Dict[str, Any] = Body(default={}),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Update acceptance details (conditions, expiry, etc.)."""
    a = _acc_or_404(db, acceptance_id, tenant_id)
    for field in ["rationale", "conditions", "financial_exposure", "authorized_by_role",
                  "second_approver", "renewal_reminder_days", "risk_level_snapshot", "extra"]:
        if field in body:
            setattr(a, field, body[field])

    if "expiry_date" in body:
        a.expiry_date = datetime.fromisoformat(body["expiry_date"])
    if "effective_date" in body:
        a.effective_date = datetime.fromisoformat(body["effective_date"])
    if "next_review_date" in body:
        a.next_review_date = datetime.fromisoformat(body["next_review_date"])

    db.commit()
    db.refresh(a)
    return a.to_dict()


@router.post("/{acceptance_id}/renew")
def renew_acceptance(
    acceptance_id: str,
    body: Dict[str, Any] = Body(default={}),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Renew an acceptance for another period."""
    a = _acc_or_404(db, acceptance_id, tenant_id)
    extension_days = body.get("extension_days", 365)
    base = max(a.expiry_date or datetime.utcnow(), datetime.utcnow())
    a.expiry_date = base + timedelta(days=extension_days)
    a.renewal_count = (a.renewal_count or 0) + 1
    a.last_renewed_at = datetime.utcnow()
    if body.get("renewed_by"):
        a.reviewed_by = body["renewed_by"]
        a.last_reviewed_at = datetime.utcnow()
    if body.get("rationale"):
        a.rationale = body["rationale"]
    db.commit()
    db.refresh(a)
    return a.to_dict()


@router.post("/{acceptance_id}/revoke")
def revoke_acceptance(
    acceptance_id: str,
    body: Dict[str, Any] = Body(default={}),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Revoke an active acceptance."""
    a = _acc_or_404(db, acceptance_id, tenant_id)
    a.decision = "rejected"
    a.expiry_date = datetime.utcnow()
    if body.get("revoked_by"):
        a.reviewed_by = body["revoked_by"]
    db.commit()
    db.refresh(a)

    # Reset risk status back to assessed
    risk = db.query(EnterpriseRisk).filter(
        EnterpriseRisk.risk_id == a.risk_id,
        EnterpriseRisk.tenant_id == tenant_id,
    ).first()
    if risk and getattr(risk.status, 'value', risk.status) == "accepted":
        risk.status = "assessed"
        db.commit()

    return {"message": "Acceptance revoked", "acceptance_id": acceptance_id}


@router.delete("/{acceptance_id}")
def delete_acceptance(
    acceptance_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    a = _acc_or_404(db, acceptance_id, tenant_id)
    a.is_active = False
    db.commit()
    return {"message": "Acceptance deleted"}
