"""
Policy Exception Register API Router

Manages time-bound policy deviations with approval workflow, compensating
controls, expiry, and renewal tracking.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import uuid

from db.database import get_db
from db.models.policy_exceptions import PolicyException

router = APIRouter(prefix="/policy-exceptions", tags=["Policy Exception Register"])


def _get_tenant_id() -> str:
    from core.tenant import get_current_tenant
    ctx = get_current_tenant()
    return ctx.tenant_id if ctx else "default"


def _new_id() -> str:
    return f"EXC_{uuid.uuid4().hex[:12].upper()}"


def _exc_or_404(db: Session, exception_id: str, tenant_id: str) -> PolicyException:
    e = db.query(PolicyException).filter(
        PolicyException.exception_id == exception_id,
        PolicyException.tenant_id == tenant_id,
        PolicyException.is_active.is_(True),
    ).first()
    if not e:
        raise HTTPException(status_code=404, detail=f"Exception '{exception_id}' not found")
    return e


# ===========================================================================
# CRUD
# ===========================================================================

@router.post("", status_code=201)
def create_exception(
    body: Dict[str, Any] = Body(default={}),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Submit a new policy exception request."""
    if not body.get("policy_id"):
        raise HTTPException(status_code=400, detail="policy_id is required")
    if not body.get("justification"):
        raise HTTPException(status_code=400, detail="justification is required")
    if not body.get("requested_by"):
        raise HTTPException(status_code=400, detail="requested_by is required")

    expiry_str = body.get("expiry_date")
    expiry_date = datetime.fromisoformat(expiry_str) if expiry_str else None

    effective_str = body.get("effective_date")
    effective_date = datetime.fromisoformat(effective_str) if effective_str else None

    # Compute duration_days if both dates provided
    duration_days = None
    if effective_date and expiry_date:
        duration_days = (expiry_date - effective_date).days

    e = PolicyException(
        exception_id=_new_id(),
        tenant_id=tenant_id,
        policy_id=body.get("policy_id"),
        policy_title=body.get("policy_title"),
        policy_section=body.get("policy_section"),
        title=body.get("title", f"Exception to {body.get('policy_id')}"),
        justification=body.get("justification"),
        scope_description=body.get("scope_description"),
        business_impact_if_denied=body.get("business_impact_if_denied"),
        exception_risk=body.get("exception_risk", "medium"),
        compensating_controls=body.get("compensating_controls"),
        residual_risk_description=body.get("residual_risk_description"),
        requested_by=body.get("requested_by"),
        requested_by_role=body.get("requested_by_role"),
        requested_at=datetime.utcnow(),
        org_unit=body.get("org_unit"),
        effective_date=effective_date,
        expiry_date=expiry_date,
        duration_days=duration_days,
        renewal_reminder_days=body.get("renewal_reminder_days", 30),
        status="pending_approval",
        is_active=True,
        extra=body.get("extra"),
    )

    db.add(e)
    db.commit()
    db.refresh(e)
    return e.to_dict()


@router.get("")
def list_exceptions(
    status: Optional[str] = Query(None),
    policy_id: Optional[str] = Query(None),
    exception_risk: Optional[str] = Query(None),
    expiring_days: Optional[int] = Query(None),
    include_expired: bool = Query(False),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    q = db.query(PolicyException).filter(
        PolicyException.tenant_id == tenant_id,
        PolicyException.is_active.is_(True),
    )
    if status:
        q = q.filter(PolicyException.status == status)
    if policy_id:
        q = q.filter(PolicyException.policy_id == policy_id)
    if exception_risk:
        q = q.filter(PolicyException.exception_risk == exception_risk)
    if not include_expired:
        q = q.filter(
            (PolicyException.expiry_date == None) |
            (PolicyException.expiry_date > datetime.utcnow())
        )
    if expiring_days is not None:
        cutoff = datetime.utcnow() + timedelta(days=expiring_days)
        q = q.filter(
            PolicyException.expiry_date != None,
            PolicyException.expiry_date <= cutoff,
            PolicyException.expiry_date > datetime.utcnow(),
        )

    exceptions = q.order_by(PolicyException.created_at.desc()).all()

    now = datetime.utcnow()
    result = []
    for exc in exceptions:
        d = exc.to_dict()
        if exc.expiry_date:
            days_left = (exc.expiry_date - now).days
            d["days_until_expiry"] = days_left
            d["is_expired"] = days_left < 0
            d["expiring_soon"] = 0 <= days_left <= (exc.renewal_reminder_days or 30)
        else:
            d["days_until_expiry"] = None
            d["is_expired"] = False
            d["expiring_soon"] = False
        result.append(d)

    return {"total": len(result), "exceptions": result}


@router.get("/summary")
def exceptions_summary(
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Dashboard summary for policy exception register."""
    all_exc = db.query(PolicyException).filter(
        PolicyException.tenant_id == tenant_id,
        PolicyException.is_active.is_(True),
    ).all()

    now = datetime.utcnow()
    total = len(all_exc)
    pending = sum(1 for e in all_exc if getattr(e.status, 'value', e.status) == "pending_approval")
    active = sum(1 for e in all_exc if getattr(e.status, 'value', e.status) == "active")
    expired = sum(1 for e in all_exc if e.expiry_date and e.expiry_date < now)
    expiring_30d = sum(
        1 for e in all_exc
        if e.expiry_date and now < e.expiry_date <= now + timedelta(days=30)
    )
    by_risk = {}
    by_status = {}
    for e in all_exc:
        r = getattr(e.exception_risk, 'value', e.exception_risk) or "medium"
        by_risk[r] = by_risk.get(r, 0) + 1
        s = getattr(e.status, 'value', e.status) or "pending_approval"
        by_status[s] = by_status.get(s, 0) + 1

    return {
        "total": total,
        "pending_approval": pending,
        "active": active,
        "expired": expired,
        "expiring_30d": expiring_30d,
        "by_risk": by_risk,
        "by_status": by_status,
    }


@router.get("/{exception_id}")
def get_exception(
    exception_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    return _exc_or_404(db, exception_id, tenant_id).to_dict()


@router.put("/{exception_id}")
def update_exception(
    exception_id: str,
    body: Dict[str, Any] = Body(default={}),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    e = _exc_or_404(db, exception_id, tenant_id)
    for field in ["title", "justification", "scope_description", "business_impact_if_denied",
                  "exception_risk", "compensating_controls", "residual_risk_description",
                  "renewal_reminder_days", "org_unit", "extra"]:
        if field in body:
            setattr(e, field, body[field])
    if "expiry_date" in body:
        e.expiry_date = datetime.fromisoformat(body["expiry_date"])
    if "effective_date" in body:
        e.effective_date = datetime.fromisoformat(body["effective_date"])
    db.commit()
    db.refresh(e)
    return e.to_dict()


@router.post("/{exception_id}/approve")
def approve_exception(
    exception_id: str,
    body: Dict[str, Any] = Body(default={}),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Approve a policy exception request."""
    e = _exc_or_404(db, exception_id, tenant_id)
    if getattr(e.status, 'value', e.status) not in ("pending_approval", "renewal_pending"):
        raise HTTPException(status_code=400, detail="Exception is not pending approval")

    e.approved_by = body.get("approved_by", "")
    e.approved_by_role = body.get("approved_by_role")
    e.approved_at = datetime.utcnow()

    # Activate on approval
    e.status = "active"

    # Set effective/expiry if provided
    if body.get("expiry_date"):
        e.expiry_date = datetime.fromisoformat(body["expiry_date"])
    if not e.effective_date:
        e.effective_date = datetime.utcnow()

    if body.get("conditions"):
        e.extra = {**(e.extra or {}), "approval_conditions": body["conditions"]}

    db.commit()
    db.refresh(e)
    return e.to_dict()


@router.post("/{exception_id}/reject")
def reject_exception(
    exception_id: str,
    body: Dict[str, Any] = Body(default={}),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Reject a policy exception request."""
    e = _exc_or_404(db, exception_id, tenant_id)
    e.status = "rejected"
    e.rejection_reason = body.get("reason", "")
    e.approved_by = body.get("rejected_by")
    e.approved_at = datetime.utcnow()
    db.commit()
    db.refresh(e)
    return e.to_dict()


@router.post("/{exception_id}/renew")
def renew_exception(
    exception_id: str,
    body: Dict[str, Any] = Body(default={}),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Request renewal of an expiring exception."""
    e = _exc_or_404(db, exception_id, tenant_id)
    extension_days = body.get("extension_days", 365)
    base = max(e.expiry_date or datetime.utcnow(), datetime.utcnow())
    e.expiry_date = base + timedelta(days=extension_days)
    e.renewal_count = (e.renewal_count or 0) + 1
    e.last_renewed_at = datetime.utcnow()
    e.status = "active"
    if body.get("renewed_by"):
        e.reviewed_by = body["renewed_by"]
        e.last_reviewed_at = datetime.utcnow()
    db.commit()
    db.refresh(e)
    return e.to_dict()


@router.post("/{exception_id}/revoke")
def revoke_exception(
    exception_id: str,
    body: Dict[str, Any] = Body(default={}),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Revoke an active exception before its expiry."""
    e = _exc_or_404(db, exception_id, tenant_id)
    e.status = "revoked"
    e.expiry_date = datetime.utcnow()
    if body.get("revoked_by"):
        e.reviewed_by = body["revoked_by"]
        e.last_reviewed_at = datetime.utcnow()
    if body.get("reason"):
        e.rejection_reason = body["reason"]
    db.commit()
    db.refresh(e)
    return {"message": "Exception revoked", "exception_id": exception_id}


@router.delete("/{exception_id}")
def delete_exception(
    exception_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    e = _exc_or_404(db, exception_id, tenant_id)
    e.is_active = False
    db.commit()
    return {"message": "Exception deleted"}
