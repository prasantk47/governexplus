"""
JML — Joiner Mover Leaver API Router

Full lifecycle automation for HR-driven identity provisioning events:
  - Policy management: birthright role assignments per event type
  - HR event ingestion, processing, retry, and audit
  - Dashboard metrics and birthright role matrix reporting
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional
from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session
import uuid

from db.database import get_db
from db.models.extended_modules import JmlPolicy, JmlEvent

router = APIRouter(tags=["JML - Joiner Mover Leaver"])


# ---------------------------------------------------------------------------
# Tenant helper
# ---------------------------------------------------------------------------

def _get_tenant_id() -> str:
    from core.tenant import get_current_tenant
    ctx = get_current_tenant()
    return ctx.tenant_id if ctx else "default"


# ---------------------------------------------------------------------------
# ID factory
# ---------------------------------------------------------------------------

def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


# ---------------------------------------------------------------------------
# 404 helpers
# ---------------------------------------------------------------------------

def _policy_or_404(db: Session, policy_id: str, tenant_id: str) -> JmlPolicy:
    obj = db.query(JmlPolicy).filter(
        JmlPolicy.id == policy_id,
        JmlPolicy.tenant_id == tenant_id,
    ).first()
    if not obj:
        raise HTTPException(status_code=404, detail=f"JML Policy '{policy_id}' not found")
    return obj


def _event_or_404(db: Session, event_id: str, tenant_id: str) -> JmlEvent:
    obj = db.query(JmlEvent).filter(
        JmlEvent.id == event_id,
        JmlEvent.tenant_id == tenant_id,
    ).first()
    if not obj:
        raise HTTPException(status_code=404, detail=f"JML Event '{event_id}' not found")
    return obj


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class PolicyCreate(BaseModel):
    policy_name: str
    event_type: str = Field(..., description="joiner | mover | leaver | rehire")
    description: Optional[str] = None
    roles_to_grant: List[str] = Field(default_factory=list)
    roles_to_revoke: List[str] = Field(default_factory=list)
    org_unit_filter: Optional[str] = None
    job_function_filter: Optional[str] = None
    is_active: bool = True
    metadata: Optional[Dict[str, Any]] = None


class PolicyUpdate(BaseModel):
    policy_name: Optional[str] = None
    description: Optional[str] = None
    roles_to_grant: Optional[List[str]] = None
    roles_to_revoke: Optional[List[str]] = None
    org_unit_filter: Optional[str] = None
    job_function_filter: Optional[str] = None
    is_active: Optional[bool] = None
    metadata: Optional[Dict[str, Any]] = None


class EventCreate(BaseModel):
    event_type: str = Field(..., description="joiner | mover | leaver | rehire | transfer")
    employee_id: str
    employee_name: Optional[str] = None
    employee_email: Optional[str] = None
    effective_date: Optional[date] = None
    source_system: Optional[str] = "manual"
    previous_org_unit: Optional[str] = None
    new_org_unit: Optional[str] = None
    previous_job_function: Optional[str] = None
    new_job_function: Optional[str] = None
    previous_manager_id: Optional[str] = None
    new_manager_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


# ---------------------------------------------------------------------------
# Policies
# ---------------------------------------------------------------------------

@router.get("/policies")
def list_policies(
    event_type: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """List JML provisioning policies with optional filters."""
    q = db.query(JmlPolicy).filter(JmlPolicy.tenant_id == tenant_id)
    if event_type:
        q = q.filter(JmlPolicy.event_type == event_type)
    if is_active is not None:
        q = q.filter(JmlPolicy.is_active == is_active)
    policies = q.order_by(JmlPolicy.created_at.desc()).all()
    return {"total": len(policies), "policies": [p.to_dict() for p in policies]}


@router.get("/policies/{id}")
def get_policy(
    id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Get a single JML policy by ID."""
    return _policy_or_404(db, id, tenant_id).to_dict()


@router.post("/policies", status_code=201)
def create_policy(
    body: PolicyCreate,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Create a new JML provisioning policy."""
    policy = JmlPolicy(
        id=_new_id("JMLP"),
        tenant_id=tenant_id,
        policy_name=body.policy_name,
        event_type=body.event_type,
        description=body.description,
        birthright_roles=body.roles_to_grant or [],
        org_unit=body.org_unit_filter,
        position_criteria={"job_function": body.job_function_filter} if body.job_function_filter else None,
        is_active=body.is_active if body.is_active is not None else True,
    )
    db.add(policy)
    db.commit()
    db.refresh(policy)
    return policy.to_dict()


@router.put("/policies/{id}")
def update_policy(
    id: str,
    body: PolicyUpdate,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Update an existing JML policy."""
    policy = _policy_or_404(db, id, tenant_id)
    updatable = [
        "policy_name", "description", "roles_to_grant", "roles_to_revoke",
        "org_unit_filter", "job_function_filter", "is_active",
    ]
    for field in updatable:
        val = getattr(body, field)
        if val is not None:
            setattr(policy, field, val)
    if body.metadata is not None:
        policy.metadata_ = body.metadata
    db.commit()
    db.refresh(policy)
    return policy.to_dict()


@router.delete("/policies/{id}", status_code=204)
def delete_policy(
    id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Soft-delete a JML policy by marking it inactive."""
    policy = _policy_or_404(db, id, tenant_id)
    policy.is_active = False
    db.commit()


# ---------------------------------------------------------------------------
# Events
# ---------------------------------------------------------------------------

@router.get("/events")
def list_events(
    event_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    employee_id: Optional[str] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """List HR events with rich filtering."""
    q = db.query(JmlEvent).filter(JmlEvent.tenant_id == tenant_id)
    if event_type:
        q = q.filter(JmlEvent.event_type == event_type)
    if status:
        q = q.filter(JmlEvent.status == status)
    if employee_id:
        q = q.filter(JmlEvent.employee_id == employee_id)
    if date_from:
        q = q.filter(JmlEvent.effective_date >= datetime.combine(date_from, datetime.min.time()))
    if date_to:
        q = q.filter(JmlEvent.effective_date <= datetime.combine(date_to, datetime.max.time()))
    total = q.count()
    events = q.order_by(JmlEvent.created_at.desc()).offset(offset).limit(limit).all()
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "events": [e.to_dict() for e in events],
    }


@router.get("/events/{id}")
def get_event(
    id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Get full detail of a single JML event including processing log."""
    return _event_or_404(db, id, tenant_id).to_dict()


@router.post("/events", status_code=201)
def create_event(
    body: EventCreate,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Manually create / log an HR identity event."""
    event = JmlEvent(
        id=_new_id("JMLE"),
        tenant_id=tenant_id,
        event_type=body.event_type,
        employee_id=body.employee_id,
        employee_name=body.employee_name,
        employee_email=body.employee_email,
        effective_date=body.effective_date,
        source_system=body.source_system or "manual",
        previous_org_unit=body.previous_org_unit,
        new_org_unit=body.new_org_unit,
        previous_job_function=body.previous_job_function,
        new_job_function=body.new_job_function,
        previous_manager_id=body.previous_manager_id,
        new_manager_id=body.new_manager_id,
        status="pending",
        metadata_=body.metadata,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event.to_dict()


@router.post("/events/{id}/process")
def process_event(
    id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Trigger processing of a pending JML event (applies matching policies)."""
    event = _event_or_404(db, id, tenant_id)
    if event.status not in ("pending", "pending_retry"):
        raise HTTPException(
            status_code=400,
            detail=f"Event is in '{event.status}' state and cannot be processed",
        )

    # Find matching policies
    policies = db.query(JmlPolicy).filter(
        JmlPolicy.tenant_id == tenant_id,
        JmlPolicy.event_type == event.event_type,
        JmlPolicy.is_active == True,
    ).all()

    actions_taken = []
    for policy in policies:
        # Apply org/job filters if set
        if policy.org_unit_filter and event.new_org_unit != policy.org_unit_filter:
            continue
        if policy.job_function_filter and event.new_job_function != policy.job_function_filter:
            continue
        for role in (policy.roles_to_grant or []):
            actions_taken.append({"action": "grant", "role": role, "policy_id": policy.id})
        for role in (policy.roles_to_revoke or []):
            actions_taken.append({"action": "revoke", "role": role, "policy_id": policy.id})

    event.status = "completed"
    event.processed_at = datetime.utcnow()
    event.processing_log = actions_taken
    db.commit()
    db.refresh(event)
    return {
        "event_id": id,
        "status": "completed",
        "policies_matched": len(set(a["policy_id"] for a in actions_taken)),
        "actions_taken": actions_taken,
        "processed_at": event.processed_at.isoformat(),
    }


@router.post("/events/{id}/retry")
def retry_event(
    id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Retry a failed JML event."""
    event = _event_or_404(db, id, tenant_id)
    if event.status != "failed":
        raise HTTPException(
            status_code=400,
            detail=f"Only 'failed' events can be retried; current status: '{event.status}'",
        )
    event.status = "pending_retry"
    event.retry_count = (getattr(event, "retry_count", 0) or 0) + 1
    event.retry_requested_at = datetime.utcnow()
    db.commit()
    db.refresh(event)
    return {"event_id": id, "status": "pending_retry", "retry_count": event.retry_count}


# ---------------------------------------------------------------------------
# Dashboard & matrix
# ---------------------------------------------------------------------------

@router.get("/dashboard")
def get_jml_dashboard(
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """JML operational dashboard: today's events, pending/failed counts, type breakdown."""
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

    all_events = db.query(JmlEvent).filter(JmlEvent.tenant_id == tenant_id).all()

    events_today = sum(1 for e in all_events if e.created_at and e.created_at >= today_start)
    pending_count = sum(1 for e in all_events if e.status in ("pending", "pending_retry"))
    failed_count = sum(1 for e in all_events if e.status == "failed")
    completed_today = sum(
        1 for e in all_events
        if e.status == "completed"
        and e.processed_at
        and e.processed_at >= today_start
    )

    type_breakdown: Dict[str, int] = {}
    for e in all_events:
        type_breakdown[e.event_type] = type_breakdown.get(e.event_type, 0) + 1

    return {
        "events_today": events_today,
        "pending_count": pending_count,
        "failed_count": failed_count,
        "completed_today": completed_today,
        "total_events": len(all_events),
        "events_by_type": type_breakdown,
    }


@router.get("/birthright-matrix")
def get_birthright_matrix(
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Return all active policies as a structured birthright role matrix."""
    policies = db.query(JmlPolicy).filter(
        JmlPolicy.tenant_id == tenant_id,
        JmlPolicy.is_active == True,
    ).order_by(JmlPolicy.event_type, JmlPolicy.policy_name).all()

    matrix: Dict[str, List[Dict[str, Any]]] = {}
    for p in policies:
        entry = {
            "policy_id": p.id,
            "policy_name": p.policy_name,
            "org_unit_filter": p.org_unit_filter,
            "job_function_filter": p.job_function_filter,
            "roles_granted": p.roles_to_grant or [],
            "roles_revoked": p.roles_to_revoke or [],
        }
        matrix.setdefault(p.event_type, []).append(entry)

    return {
        "total_policies": len(policies),
        "matrix": matrix,
        "event_types": sorted(matrix.keys()),
    }
