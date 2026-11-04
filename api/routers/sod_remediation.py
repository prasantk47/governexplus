"""
SoD Remediation Workflow API Router

Dedicated lifecycle management for SoD violation remediation:
  open → in_remediation → pending_validation → validated → closed | accepted (exception)
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from typing import Dict, List, Optional, Any
from datetime import datetime
from sqlalchemy.orm import Session
import uuid

from db.database import get_db
from db.models.governance_extended import SoDRemediation

router = APIRouter(tags=["SoD Remediation"])


def _get_tenant_id() -> str:
    from core.tenant import get_current_tenant
    ctx = get_current_tenant()
    return ctx.tenant_id if ctx else "default"


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def _remediation_or_404(db: Session, remediation_id: str, tenant_id: str) -> SoDRemediation:
    r = db.query(SoDRemediation).filter(
        SoDRemediation.remediation_id == remediation_id,
        SoDRemediation.tenant_id == tenant_id,
        SoDRemediation.is_active.is_(True),
    ).first()
    if not r:
        raise HTTPException(status_code=404, detail=f"SoD remediation '{remediation_id}' not found")
    return r


VALID_TRANSITIONS = {
    "open": ["in_remediation", "accepted"],
    "in_remediation": ["pending_validation", "open"],
    "pending_validation": ["validated", "in_remediation"],
    "validated": ["closed"],
    "accepted": ["closed"],
    "closed": [],
}


@router.get("")
def list_remediations(
    status: Optional[str] = Query(None),
    violation_id: Optional[str] = Query(None),
    assigned_to: Optional[str] = Query(None),
    overdue_only: bool = Query(False),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    q = db.query(SoDRemediation).filter(
        SoDRemediation.tenant_id == tenant_id,
        SoDRemediation.is_active.is_(True),
    )
    if status:
        q = q.filter(SoDRemediation.status == status)
    if violation_id:
        q = q.filter(SoDRemediation.violation_id == violation_id)
    if assigned_to:
        q = q.filter(SoDRemediation.assigned_to == assigned_to)
    remediations = q.order_by(SoDRemediation.due_date, SoDRemediation.created_at.desc()).all()
    result = []
    for r in remediations:
        d = r.to_dict()
        d["priority"] = "high"  # Default; not stored in model
        result.append(d)
    if overdue_only:
        now = datetime.utcnow().isoformat()
        result = [r for r in result if r.get("due_date") and r["due_date"] < now and r["status"] not in ("closed",)]
    return {"remediations": result, "total": len(result)}


@router.post("", status_code=201)
def create_remediation(
    body: Dict[str, Any] = Body(default={}),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    r = SoDRemediation(
        remediation_id=_new_id("SODREM"),
        tenant_id=tenant_id,
        violation_id=body.get("violation_id") or _new_id("VIO"),
        user_id=body.get("user_id") or "unknown",
        rule_id=body.get("rule_id") or "unknown",
        rule_description=body.get("rule_description"),
        severity=body.get("severity"),
        remediation_type=body.get("remediation_type", "role_removal"),
        remediation_description=body.get("remediation_description"),
        assigned_to=body.get("assigned_to"),
        due_date=datetime.fromisoformat(body["due_date"]) if body.get("due_date") else None,
        status="open",
    )
    db.add(r)
    db.commit()
    db.refresh(r)
    d = r.to_dict()
    d["priority"] = body.get("priority", "medium")
    return d


@router.get("/{remediation_id}")
def get_remediation(
    remediation_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    r = _remediation_or_404(db, remediation_id, tenant_id)
    d = r.to_dict()
    d["priority"] = "medium"
    return d


@router.put("/{remediation_id}/transition")
def transition_remediation(
    remediation_id: str,
    body: Dict[str, Any] = Body(default={}),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    r = _remediation_or_404(db, remediation_id, tenant_id)
    current = getattr(r.status, "value", r.status)
    new_status = body.get("status")
    allowed = VALID_TRANSITIONS.get(current, [])
    if new_status not in allowed:
        raise HTTPException(
            status_code=422,
            detail=f"Cannot transition from '{current}' to '{new_status}'. Allowed: {allowed}",
        )
    r.status = new_status
    now = datetime.utcnow()
    if new_status == "in_remediation":
        if "assigned_to" in body:
            r.assigned_to = body["assigned_to"]
    if new_status == "pending_validation":
        if "actions_taken" in body:
            r.actions_taken = body["actions_taken"]
        r.validated_by = body.get("validator")
    if new_status == "validated":
        r.validated_at = now
        r.validated_by = body.get("validated_by") or r.validated_by
        r.validation_notes = body.get("validation_notes")
    if new_status == "accepted":
        r.exception_requested = True
        r.exception_rationale = body.get("risk_acceptance_justification")
        r.exception_approved_by = body.get("risk_accepted_by")
    if new_status == "closed":
        r.closed_at = now
    db.commit()
    db.refresh(r)
    d = r.to_dict()
    d["priority"] = "medium"
    return d


@router.put("/{remediation_id}")
def update_remediation(
    remediation_id: str,
    body: Dict[str, Any] = Body(default={}),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    r = _remediation_or_404(db, remediation_id, tenant_id)
    updatable = [
        "remediation_type", "remediation_description", "assigned_to", "severity",
    ]
    for k in updatable:
        if k in body:
            setattr(r, k, body[k])
    if "due_date" in body and body["due_date"]:
        r.due_date = datetime.fromisoformat(body["due_date"])
    db.commit()
    db.refresh(r)
    d = r.to_dict()
    d["priority"] = "medium"
    return d


@router.get("/summary/stats")
def remediation_stats(
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    remediations = db.query(SoDRemediation).filter(
        SoDRemediation.tenant_id == tenant_id,
        SoDRemediation.is_active.is_(True),
    ).all()
    now = datetime.utcnow()
    overdue = [r for r in remediations if r.due_date and r.due_date < now and getattr(r.status, 'value', r.status) not in ("closed",)]
    by_status: Dict[str, int] = {}
    for r in remediations:
        s = getattr(r.status, 'value', r.status) or "unknown"
        by_status[s] = by_status.get(s, 0) + 1
    return {
        "total": len(remediations),
        "open": by_status.get("open", 0),
        "in_remediation": by_status.get("in_remediation", 0),
        "pending_validation": by_status.get("pending_validation", 0),
        "overdue": len(overdue),
        "closed": by_status.get("closed", 0),
        "accepted_risk": by_status.get("accepted", 0),
        "by_status": by_status,
    }
