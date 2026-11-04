"""
IT Change Risk / ITGC API Router

Risk assessment and approval workflow for IT changes with
post-implementation review and rollback tracking.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from typing import Dict, List, Optional, Any
from datetime import datetime
from sqlalchemy.orm import Session
import uuid

from db.database import get_db
from db.models.governance_extended import ITChangeRisk

router = APIRouter(tags=["IT Change Risk / ITGC"])


def _get_tenant_id() -> str:
    from core.tenant import get_current_tenant
    ctx = get_current_tenant()
    return ctx.tenant_id if ctx else "default"


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def _change_or_404(db: Session, change_id: str, tenant_id: str) -> ITChangeRisk:
    c = db.query(ITChangeRisk).filter(
        ITChangeRisk.change_id == change_id,
        ITChangeRisk.tenant_id == tenant_id,
        ITChangeRisk.is_active.is_(True),
    ).first()
    if not c:
        raise HTTPException(status_code=404, detail=f"IT change risk '{change_id}' not found")
    return c


@router.get("")
def list_change_risks(
    approval_status: Optional[str] = Query(None),
    risk_level: Optional[str] = Query(None),
    change_type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    q = db.query(ITChangeRisk).filter(
        ITChangeRisk.tenant_id == tenant_id,
        ITChangeRisk.is_active.is_(True),
    )
    if approval_status:
        q = q.filter(ITChangeRisk.approval_status == approval_status)
    if risk_level:
        q = q.filter(ITChangeRisk.risk_level == risk_level)
    if change_type:
        q = q.filter(ITChangeRisk.change_type == change_type)
    changes = q.order_by(ITChangeRisk.planned_date.desc().nullsfirst(), ITChangeRisk.created_at.desc()).all()
    # Expose approval_status as status for frontend consistency
    result = []
    for c in changes:
        d = c.to_dict()
        d["status"] = d.get("approval_status", "pending")
        d["change_risk_id"] = d.get("change_id")
        d["requester"] = d.get("requested_by")
        result.append(d)
    return {"changes": result, "total": len(result)}


@router.post("", status_code=201)
def create_change_risk(
    body: Dict[str, Any] = Body(default={}),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    c = ITChangeRisk(
        change_id=_new_id("ITCHG"),
        tenant_id=tenant_id,
        title=body["title"],
        description=body.get("description"),
        change_type=body.get("change_type", "standard"),
        system_name=body.get("system_name"),
        systems_affected=body.get("affected_systems"),
        requested_by=body.get("requester") or body.get("requested_by"),
        assigned_to=body.get("assigned_reviewer"),
        planned_date=datetime.fromisoformat(body["planned_date"]) if body.get("planned_date") else None,
        risk_level=body.get("risk_level", "medium"),
        risk_description=body.get("risk_description"),
        rollback_plan=body.get("rollback_plan"),
        testing_evidence=body.get("testing_evidence"),
        approval_status="pending",
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    d = c.to_dict()
    d["status"] = d.get("approval_status", "pending")
    d["change_risk_id"] = d.get("change_id")
    return d


@router.get("/{change_id}")
def get_change_risk(
    change_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    c = _change_or_404(db, change_id, tenant_id)
    d = c.to_dict()
    d["status"] = d.get("approval_status", "pending")
    d["change_risk_id"] = d.get("change_id")
    return d


@router.put("/{change_id}/transition")
def transition_change_risk(
    change_id: str,
    body: Dict[str, Any] = Body(default={}),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Transition approval_status. Frontend passes 'status' field."""
    c = _change_or_404(db, change_id, tenant_id)
    new_status = body.get("status") or body.get("approval_status")
    allowed = {
        "pending": ["approved", "rejected"],
        "approved": ["implemented", "rejected"],
        "implemented": ["closed", "rolled_back"],
        "rejected": [],
        "closed": [],
        "rolled_back": [],
    }
    current = getattr(c.approval_status, "value", c.approval_status) or "pending"
    if new_status not in allowed.get(current, []):
        raise HTTPException(
            status_code=422,
            detail=f"Cannot transition from '{current}' to '{new_status}'. Allowed: {allowed.get(current, [])}",
        )
    c.approval_status = new_status
    now = datetime.utcnow()
    if new_status == "approved":
        c.approved_at = now
        c.approved_by = body.get("approved_by")
    if new_status == "rejected":
        c.rejection_reason = body.get("rejection_reason")
    if new_status == "implemented":
        c.actual_date = now
    if new_status in ("closed", "rolled_back"):
        c.post_change_status = "successful" if new_status == "closed" else "rolled_back"
        c.post_change_review = body.get("post_review_notes")
        c.reviewed_at = now
    db.commit()
    db.refresh(c)
    d = c.to_dict()
    d["status"] = d.get("approval_status", "pending")
    d["change_risk_id"] = d.get("change_id")
    return d


@router.put("/{change_id}")
def update_change_risk(
    change_id: str,
    body: Dict[str, Any] = Body(default={}),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    c = _change_or_404(db, change_id, tenant_id)
    updatable = [
        "title", "description", "change_type", "system_name",
        "risk_level", "risk_description", "rollback_plan", "testing_evidence",
    ]
    for k in updatable:
        if k in body:
            setattr(c, k, body[k])
    if "planned_date" in body and body["planned_date"]:
        c.planned_date = datetime.fromisoformat(body["planned_date"])
    if "requester" in body:
        c.requested_by = body["requester"]
    if "affected_systems" in body:
        c.systems_affected = body["affected_systems"]
    db.commit()
    db.refresh(c)
    d = c.to_dict()
    d["status"] = d.get("approval_status", "pending")
    d["change_risk_id"] = d.get("change_id")
    return d
