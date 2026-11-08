"""
GAP-1: Change Governance Management Router
"""
import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from db.database import get_db
from db.models.change_governance import ChangeRequest

router = APIRouter()

VALID_TRANSITIONS = {
    "draft": ["submitted"],
    "submitted": ["risk_assessed", "rejected"],
    "risk_assessed": ["pending_approval"],
    "pending_approval": ["approved", "rejected"],
    "approved": ["implementing"],
    "implementing": ["implemented", "rolled_back"],
    "implemented": ["verifying"],
    "verifying": ["verified", "rolled_back"],
    "verified": ["closed"],
    "rejected": [],
    "closed": [],
    "rolled_back": ["draft"],
}


def _tenant(request):
    return getattr(request.state, "tenant_id", "default")


@router.get("/")
def list_changes(
    request: None = None,
    domain: str = None,
    category: str = None,
    status: str = None,
    db: Session = Depends(get_db),
):
    from starlette.requests import Request
    # Get tenant from first arg
    q = db.query(ChangeRequest)
    if domain:
        q = q.filter(ChangeRequest.domain == domain)
    if category:
        q = q.filter(ChangeRequest.category == category)
    if status:
        q = q.filter(ChangeRequest.status == status)
    return [r.to_dict() for r in q.order_by(ChangeRequest.created_at.desc()).limit(200).all()]


@router.post("/")
def create_change_request(body: dict, db: Session = Depends(get_db)):
    rec = ChangeRequest(
        id=str(uuid.uuid4()),
        tenant_id=body.get("tenant_id", "default"),
        change_id=body.get("change_id", f"CHG-{uuid.uuid4().hex[:8].upper()}"),
        title=body["title"],
        description=body.get("description"),
        domain=body.get("domain", "master_data"),
        category=body.get("category", "normal"),
        status="draft",
        risk_level=body.get("risk_level", "medium"),
        target_system=body.get("target_system"),
        object_type=body.get("object_type"),
        object_key=body.get("object_key"),
        field_name=body.get("field_name"),
        before_value=body.get("before_value"),
        after_value=body.get("after_value"),
        change_payload=body.get("change_payload"),
        requester=body.get("requester", "system"),
        justification=body.get("justification"),
        effective_date=body.get("effective_date"),
        rollback_plan=body.get("rollback_plan"),
        related_ticket=body.get("related_ticket"),
        impact_assessment=body.get("impact_assessment"),
        linked_risk_ids=body.get("linked_risk_ids"),
        linked_control_ids=body.get("linked_control_ids"),
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)
    return rec.to_dict()


@router.get("/{change_id}")
def get_change(change_id: str, db: Session = Depends(get_db)):
    rec = db.query(ChangeRequest).filter(
        (ChangeRequest.id == change_id) | (ChangeRequest.change_id == change_id)
    ).first()
    if not rec:
        raise HTTPException(404, "Change request not found")
    return rec.to_dict()


@router.put("/{change_id}")
def update_change(change_id: str, body: dict, db: Session = Depends(get_db)):
    rec = db.query(ChangeRequest).filter(
        (ChangeRequest.id == change_id) | (ChangeRequest.change_id == change_id)
    ).first()
    if not rec:
        raise HTTPException(404, "Change request not found")
    for k, v in body.items():
        if hasattr(rec, k) and k not in ("id", "tenant_id", "change_id"):
            setattr(rec, k, v)
    db.commit()
    db.refresh(rec)
    return rec.to_dict()


@router.put("/{change_id}/transition")
def transition_change(change_id: str, body: dict, db: Session = Depends(get_db)):
    rec = db.query(ChangeRequest).filter(
        (ChangeRequest.id == change_id) | (ChangeRequest.change_id == change_id)
    ).first()
    if not rec:
        raise HTTPException(404, "Change request not found")
    new_status = body["new_status"]
    allowed = VALID_TRANSITIONS.get(rec.status, [])
    if new_status not in allowed:
        raise HTTPException(400, f"Cannot transition from {rec.status} to {new_status}. Allowed: {allowed}")
    now = datetime.utcnow()
    rec.status = new_status
    if new_status == "approved":
        rec.approved_at = now
        rec.approved_by = body.get("actor", "system")
    elif new_status == "rejected":
        rec.rejected_at = now
        rec.rejected_by = body.get("actor", "system")
        rec.rejection_reason = body.get("reason")
    elif new_status == "implemented":
        rec.implemented_at = now
        rec.implemented_by = body.get("actor", "system")
        rec.implementation_notes = body.get("notes")
    elif new_status == "verified":
        rec.verified_at = now
        rec.verified_by = body.get("actor", "system")
        rec.verification_result = body.get("result", "pass")
        rec.verification_notes = body.get("notes")
        rec.discrepancy_found = body.get("discrepancy", False)
    elif new_status == "closed":
        rec.closed_at = now
        rec.closed_by = body.get("actor", "system")
    db.commit()
    db.refresh(rec)
    return rec.to_dict()


@router.get("/summary/stats")
def change_summary(db: Session = Depends(get_db)):
    from sqlalchemy import func
    rows = db.query(ChangeRequest.status, func.count()).group_by(ChangeRequest.status).all()
    by_status = {s: c for s, c in rows}
    domain_rows = db.query(ChangeRequest.domain, func.count()).group_by(ChangeRequest.domain).all()
    by_domain = {d: c for d, c in domain_rows}
    return {"by_status": by_status, "by_domain": by_domain, "total": sum(by_status.values())}
