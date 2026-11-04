"""
Regulatory Change Management API Router

Tracks regulatory developments, impact assessments, and action plans
to keep the organization's policies, controls and obligations current.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from typing import Dict, List, Optional, Any
from datetime import datetime
from sqlalchemy.orm import Session
import uuid

from db.database import get_db
from db.models.governance_extended import RegulatoryChange

router = APIRouter(tags=["Regulatory Change Management"])


def _get_tenant_id() -> str:
    from core.tenant import get_current_tenant
    ctx = get_current_tenant()
    return ctx.tenant_id if ctx else "default"


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def _change_or_404(db: Session, change_id: str, tenant_id: str) -> RegulatoryChange:
    c = db.query(RegulatoryChange).filter(
        RegulatoryChange.change_id == change_id,
        RegulatoryChange.tenant_id == tenant_id,
        RegulatoryChange.is_active.is_(True),
    ).first()
    if not c:
        raise HTTPException(status_code=404, detail=f"Regulatory change '{change_id}' not found")
    return c


@router.get("")
def list_changes(
    status: Optional[str] = Query(None),
    jurisdiction: Optional[str] = Query(None),
    impact_level: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    q = db.query(RegulatoryChange).filter(
        RegulatoryChange.tenant_id == tenant_id,
        RegulatoryChange.is_active.is_(True),
    )
    if status:
        q = q.filter(RegulatoryChange.status == status)
    if jurisdiction:
        q = q.filter(RegulatoryChange.jurisdiction.ilike(f"%{jurisdiction}%"))
    if impact_level:
        q = q.filter(RegulatoryChange.impact_level == impact_level)
    changes = q.order_by(RegulatoryChange.effective_date.desc().nullsfirst(), RegulatoryChange.created_at.desc()).all()
    return {"changes": [c.to_dict() for c in changes], "total": len(changes)}


@router.post("", status_code=201)
def create_change(
    body: Dict[str, Any] = Body(default={}),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    c = RegulatoryChange(
        change_id=_new_id("REGCHG"),
        tenant_id=tenant_id,
        title=body["title"],
        description=body.get("description"),
        regulation_name=body.get("regulation_name"),
        jurisdiction=body.get("jurisdiction"),
        regulator=body.get("issuing_body") or body.get("regulator"),
        change_type=body.get("change_type", "new_requirement"),
        impact_level=body.get("impact_level", "medium"),
        impact_description=body.get("impact_description"),
        effective_date=datetime.fromisoformat(body["effective_date"]) if body.get("effective_date") else None,
        action_due_date=datetime.fromisoformat(body["compliance_deadline"]) if body.get("compliance_deadline") else None,
        affected_obligations=body.get("affected_obligations"),
        affected_controls=body.get("affected_controls"),
        affected_policies=body.get("affected_policies"),
        assigned_to=body.get("assigned_owner") or body.get("assigned_to"),
        status="new",
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return c.to_dict()


@router.get("/{change_id}")
def get_change(
    change_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    return _change_or_404(db, change_id, tenant_id).to_dict()


@router.put("/{change_id}")
def update_change(
    change_id: str,
    body: Dict[str, Any] = Body(default={}),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    c = _change_or_404(db, change_id, tenant_id)
    updatable = [
        "title", "description", "regulation_name", "jurisdiction", "regulator",
        "change_type", "impact_level", "impact_description", "affected_obligations",
        "affected_controls", "affected_policies", "action_plan", "assigned_to", "status",
        "implementation_notes",
    ]
    for k in updatable:
        if k in body:
            setattr(c, k, body[k])
    if "issuing_body" in body:
        c.regulator = body["issuing_body"]
    if "assigned_owner" in body:
        c.assigned_to = body["assigned_owner"]
    if "effective_date" in body and body["effective_date"]:
        c.effective_date = datetime.fromisoformat(body["effective_date"])
    if "compliance_deadline" in body and body["compliance_deadline"]:
        c.action_due_date = datetime.fromisoformat(body["compliance_deadline"])
    if body.get("status") == "implemented" and not c.implemented_at:
        c.implemented_at = datetime.utcnow()
    db.commit()
    db.refresh(c)
    return c.to_dict()


@router.get("/summary/stats")
def reg_change_stats(
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    changes = db.query(RegulatoryChange).filter(
        RegulatoryChange.tenant_id == tenant_id,
        RegulatoryChange.is_active.is_(True),
    ).all()
    now = datetime.utcnow()
    overdue = [c for c in changes if c.action_due_date and c.action_due_date < now and c.status not in ("implemented", "closed")]
    by_status: Dict[str, int] = {}
    for c in changes:
        s = getattr(c.status, "value", c.status) or "unknown"
        by_status[s] = by_status.get(s, 0) + 1
    return {
        "total": len(changes),
        "overdue": len(overdue),
        "critical_impact": sum(1 for c in changes if c.impact_level == "critical"),
        "high_impact": sum(1 for c in changes if c.impact_level == "high"),
        "by_status": by_status,
    }
