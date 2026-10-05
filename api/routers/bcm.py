"""
BCM — Business Continuity Management API Router

Full BCM lifecycle:
  - Business Impact Analysis (BIA) records: RTO/RPO, criticality, dependencies
  - BCM plans: BCP, DRP, crisis communication
  - Test exercises: tabletop, simulation, full drill
  - Incident activations: plan invocation, timeline events, resolution
  - Dashboard: critical processes, test coverage, active incidents
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import uuid

from db.database import get_db
from db.models.extended_modules import (
    BiaRecord, BcmPlan, BcmTestExercise, IncidentActivation,
    BcmCriticality, BcmPlanType, BcmPlanStatus, BcmActivationStatus,
)

router = APIRouter(tags=["Business Continuity Management"])


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

def _bia_or_404(db: Session, bia_id: str, tenant_id: str) -> BiaRecord:
    obj = db.query(BiaRecord).filter(
        BiaRecord.id == bia_id,
        BiaRecord.tenant_id == tenant_id,
    ).first()
    if not obj:
        raise HTTPException(status_code=404, detail=f"BIA record '{bia_id}' not found")
    return obj


def _plan_or_404(db: Session, plan_id: str, tenant_id: str) -> BcmPlan:
    obj = db.query(BcmPlan).filter(
        BcmPlan.id == plan_id,
        BcmPlan.tenant_id == tenant_id,
    ).first()
    if not obj:
        raise HTTPException(status_code=404, detail=f"BCM plan '{plan_id}' not found")
    return obj


def _exercise_or_404(db: Session, exercise_id: str, tenant_id: str) -> BcmTestExercise:
    obj = db.query(BcmTestExercise).filter(
        BcmTestExercise.id == exercise_id,
        BcmTestExercise.tenant_id == tenant_id,
    ).first()
    if not obj:
        raise HTTPException(status_code=404, detail=f"Exercise '{exercise_id}' not found")
    return obj


def _activation_or_404(db: Session, activation_id: str, tenant_id: str) -> IncidentActivation:
    obj = db.query(IncidentActivation).filter(
        IncidentActivation.id == activation_id,
        IncidentActivation.tenant_id == tenant_id,
    ).first()
    if not obj:
        raise HTTPException(status_code=404, detail=f"Activation '{activation_id}' not found")
    return obj


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class BiaCreate(BaseModel):
    process_name: str
    process_owner: Optional[str] = None
    org_unit_id: Optional[str] = None
    criticality: str = Field(default="medium", description="critical | high | medium | low")
    rto_hours: Optional[float] = Field(None, description="Recovery Time Objective in hours")
    rpo_hours: Optional[float] = Field(None, description="Recovery Point Objective in hours")
    mtpd_hours: Optional[float] = Field(None, description="Maximum Tolerable Period of Disruption")
    dependencies: Optional[List[str]] = None
    financial_impact_per_hour: Optional[float] = None
    currency: Optional[str] = "USD"
    recovery_strategy: Optional[str] = None
    minimum_staff_required: Optional[int] = None
    systems_required: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None


class BiaUpdate(BaseModel):
    process_name: Optional[str] = None
    process_owner: Optional[str] = None
    criticality: Optional[str] = None
    rto_hours: Optional[float] = None
    rpo_hours: Optional[float] = None
    mtpd_hours: Optional[float] = None
    dependencies: Optional[List[str]] = None
    financial_impact_per_hour: Optional[float] = None
    recovery_strategy: Optional[str] = None
    minimum_staff_required: Optional[int] = None
    systems_required: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None


class PlanCreate(BaseModel):
    plan_name: str
    plan_type: str = Field(..., description="bcp | drp | crisis_comms | pandemic | cyber_recovery")
    description: Optional[str] = None
    status: str = Field(default="draft", description="draft | active | under_review | retired")
    owner_id: Optional[str] = None
    owner_name: Optional[str] = None
    scope: Optional[str] = None
    linked_bia_ids: Optional[List[str]] = None
    version: Optional[str] = "1.0"
    approved_by: Optional[str] = None
    approved_at: Optional[str] = None
    next_review_date: Optional[str] = None
    test_frequency_months: Optional[int] = 12
    metadata: Optional[Dict[str, Any]] = None


class PlanUpdate(BaseModel):
    plan_name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    owner_id: Optional[str] = None
    scope: Optional[str] = None
    linked_bia_ids: Optional[List[str]] = None
    version: Optional[str] = None
    approved_by: Optional[str] = None
    approved_at: Optional[str] = None
    next_review_date: Optional[str] = None
    test_frequency_months: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None


class ExerciseCreate(BaseModel):
    plan_id: str
    exercise_name: str
    exercise_type: str = Field(
        default="tabletop",
        description="tabletop | simulation | full_drill | walkthrough | parallel_test",
    )
    scheduled_date: Optional[str] = None
    facilitator_id: Optional[str] = None
    participants: Optional[List[str]] = None
    scenario_description: Optional[str] = None
    objectives: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None


class ExerciseUpdate(BaseModel):
    outcome: Optional[str] = Field(None, description="pass | fail | partial | cancelled")
    actual_date: Optional[str] = None
    duration_minutes: Optional[int] = None
    findings: Optional[List[str]] = None
    action_items: Optional[List[Dict[str, Any]]] = None
    lessons_learned: Optional[str] = None
    next_exercise_date: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class ActivationCreate(BaseModel):
    plan_id: str
    activation_reason: str
    incident_type: Optional[str] = None
    severity: str = Field(default="high", description="critical | high | medium")
    activated_by: Optional[str] = None
    notification_list: Optional[List[str]] = None
    initial_notes: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class ActivationUpdate(BaseModel):
    status: Optional[str] = Field(None, description="active | resolved | stood_down")
    timeline_event: Optional[Dict[str, Any]] = Field(
        None, description="Single timeline event: {time, actor, action, notes}"
    )
    resolution_notes: Optional[str] = None
    lessons_learned: Optional[str] = None
    resolved_at: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


# ---------------------------------------------------------------------------
# BIA
# ---------------------------------------------------------------------------

@router.get("/bia")
def list_bia_records(
    criticality: Optional[str] = Query(None),
    process_owner: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """List all Business Impact Analysis records."""
    q = db.query(BiaRecord).filter(BiaRecord.tenant_id == tenant_id)
    if criticality:
        q = q.filter(BiaRecord.criticality == criticality)
    if process_owner:
        q = q.filter(BiaRecord.process_owner.ilike(f"%{process_owner}%"))
    records = q.order_by(BiaRecord.criticality, BiaRecord.process_name).all()
    return {"total": len(records), "bia_records": [r.to_dict() for r in records]}


@router.get("/bia/{id}")
def get_bia_record(
    id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Get a single BIA record by ID."""
    return _bia_or_404(db, id, tenant_id).to_dict()


@router.post("/bia", status_code=201)
def create_bia_record(
    body: BiaCreate,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Create a new BIA record."""
    record = BiaRecord(
        id=_new_id("BIA"),
        tenant_id=tenant_id,
        process_name=body.process_name,
        process_owner=body.process_owner,
        criticality=BcmCriticality(body.criticality) if body.criticality else BcmCriticality.MEDIUM,
        rto_hours=body.rto_hours,
        rpo_hours=body.rpo_hours,
        mtpd_hours=body.mtpd_hours,
        dependencies=body.dependencies or [],
        recovery_strategy=body.recovery_strategy,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record.to_dict()


@router.put("/bia/{id}")
def update_bia_record(
    id: str,
    body: BiaUpdate,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Update a BIA record."""
    record = _bia_or_404(db, id, tenant_id)
    updatable = [
        "process_name", "process_owner", "criticality", "rto_hours", "rpo_hours",
        "mtpd_hours", "dependencies", "financial_impact_per_hour", "recovery_strategy",
        "minimum_staff_required", "systems_required",
    ]
    for field in updatable:
        val = getattr(body, field)
        if val is not None:
            setattr(record, field, val)
    if body.metadata is not None:
        record.metadata_ = body.metadata
    db.commit()
    db.refresh(record)
    return record.to_dict()


# ---------------------------------------------------------------------------
# Plans
# ---------------------------------------------------------------------------

@router.get("/plans")
def list_plans(
    plan_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """List BCM plans."""
    q = db.query(BcmPlan).filter(BcmPlan.tenant_id == tenant_id)
    if plan_type:
        q = q.filter(BcmPlan.plan_type == plan_type)
    if status:
        q = q.filter(BcmPlan.status == status)
    plans = q.order_by(BcmPlan.plan_name).all()
    return {"total": len(plans), "plans": [p.to_dict() for p in plans]}


@router.post("/plans", status_code=201)
def create_plan(
    body: PlanCreate,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Create a new BCM plan."""
    plan = BcmPlan(
        id=_new_id("BCMP"),
        tenant_id=tenant_id,
        plan_name=body.plan_name,
        plan_type=BcmPlanType(body.plan_type) if body.plan_type else BcmPlanType.BCP,
        scope=body.scope,
        owner=body.owner_name,
        version=body.version or "1.0",
        status=BcmPlanStatus(body.status) if body.status else BcmPlanStatus.DRAFT,
        approved_by=body.approved_by,
        next_test_date=datetime.fromisoformat(body.next_review_date) if body.next_review_date else None,
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan.to_dict()


@router.get("/plans/{id}")
def get_plan(
    id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Get full BCM plan detail."""
    return _plan_or_404(db, id, tenant_id).to_dict()


@router.put("/plans/{id}")
def update_plan(
    id: str,
    body: PlanUpdate,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Update a BCM plan."""
    plan = _plan_or_404(db, id, tenant_id)
    updatable = [
        "plan_name", "description", "status", "owner_id", "scope",
        "linked_bia_ids", "version", "approved_by", "test_frequency_months",
    ]
    for field in updatable:
        val = getattr(body, field)
        if val is not None:
            setattr(plan, field, val)
    if body.approved_at:
        plan.approved_at = datetime.fromisoformat(body.approved_at)
    if body.next_review_date:
        plan.next_test_date = datetime.fromisoformat(body.next_review_date)
    if body.metadata is not None:
        plan.metadata_ = body.metadata
    db.commit()
    db.refresh(plan)
    return plan.to_dict()


# ---------------------------------------------------------------------------
# Exercises
# ---------------------------------------------------------------------------

@router.get("/exercises")
def list_exercises(
    plan_id: Optional[str] = Query(None),
    outcome: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """List BCM test exercises."""
    q = db.query(BcmTestExercise).filter(BcmTestExercise.tenant_id == tenant_id)
    if plan_id:
        q = q.filter(BcmTestExercise.plan_id == plan_id)
    if outcome:
        q = q.filter(BcmTestExercise.outcome == outcome)
    exercises = q.order_by(BcmTestExercise.scheduled_date.desc().nullslast()).all()
    return {"total": len(exercises), "exercises": [e.to_dict() for e in exercises]}


@router.post("/exercises", status_code=201)
def create_exercise(
    body: ExerciseCreate,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Schedule a new BCM test exercise."""
    _plan_or_404(db, body.plan_id, tenant_id)
    exercise = BcmTestExercise(
        id=_new_id("BCME"),
        tenant_id=tenant_id,
        plan_id=body.plan_id,
        exercise_name=body.exercise_name,
        exercise_type=body.exercise_type,
        scheduled_date=datetime.fromisoformat(body.scheduled_date) if body.scheduled_date else None,
        facilitator_id=body.facilitator_id,
        participants=body.participants or [],
        scenario_description=body.scenario_description,
        objectives=body.objectives or [],
        status="scheduled",
        metadata_=body.metadata,
    )
    db.add(exercise)
    db.commit()
    db.refresh(exercise)
    return exercise.to_dict()


@router.put("/exercises/{id}")
def update_exercise(
    id: str,
    body: ExerciseUpdate,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Record results for a completed BCM exercise."""
    exercise = _exercise_or_404(db, id, tenant_id)
    if body.outcome is not None:
        exercise.outcome = body.outcome
        exercise.status = "completed"
    if body.actual_date:
        exercise.actual_date = datetime.fromisoformat(body.actual_date)
    if body.duration_minutes is not None:
        exercise.duration_minutes = body.duration_minutes
    if body.findings is not None:
        exercise.findings = body.findings
    if body.action_items is not None:
        exercise.action_items = body.action_items
    if body.lessons_learned is not None:
        exercise.lessons_learned = body.lessons_learned
    if body.next_exercise_date:
        exercise.next_exercise_date = datetime.fromisoformat(body.next_exercise_date)
        # Update parent plan's next_review_date
        plan = db.query(BcmPlan).filter(
            BcmPlan.id == exercise.plan_id,
            BcmPlan.tenant_id == tenant_id,
        ).first()
        if plan:
            plan.last_tested = exercise.actual_date or datetime.utcnow()
            plan.next_test_date = datetime.fromisoformat(body.next_exercise_date)
    if body.metadata is not None:
        exercise.metadata_ = body.metadata
    db.commit()
    db.refresh(exercise)
    return exercise.to_dict()


# ---------------------------------------------------------------------------
# Activations
# ---------------------------------------------------------------------------

@router.get("/activations")
def list_activations(
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """List BCM incident activations."""
    q = db.query(IncidentActivation).filter(IncidentActivation.tenant_id == tenant_id)
    if status:
        q = q.filter(IncidentActivation.status == status)
    activations = q.order_by(IncidentActivation.created_at.desc()).all()
    return {"total": len(activations), "activations": [a.to_dict() for a in activations]}


@router.post("/activations", status_code=201)
def activate_plan(
    body: ActivationCreate,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Activate a BCM plan for a live incident."""
    plan = _plan_or_404(db, body.plan_id, tenant_id)
    if plan.status != "active":
        raise HTTPException(
            status_code=400,
            detail=f"Plan '{body.plan_id}' must be in 'active' status to be activated",
        )
    activation = IncidentActivation(
        id=_new_id("BCMA"),
        tenant_id=tenant_id,
        plan_id=body.plan_id,
        activation_reason=body.activation_reason,
        incident_type=body.incident_type,
        severity=body.severity,
        activated_by=body.activated_by,
        notification_list=body.notification_list or [],
        initial_notes=body.initial_notes,
        status="active",
        activated_at=datetime.utcnow(),
        timeline=[{
            "time": datetime.utcnow().isoformat(),
            "actor": body.activated_by or "system",
            "action": "Plan activated",
            "notes": body.initial_notes,
        }],
        metadata_=body.metadata,
    )
    db.add(activation)
    db.commit()
    db.refresh(activation)
    return activation.to_dict()


@router.put("/activations/{id}")
def update_activation(
    id: str,
    body: ActivationUpdate,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Update an activation — add timeline events or resolve the incident."""
    activation = _activation_or_404(db, id, tenant_id)
    if body.status:
        activation.status = body.status
    if body.timeline_event:
        timeline = list(activation.timeline or [])
        event = body.timeline_event.copy()
        if "time" not in event:
            event["time"] = datetime.utcnow().isoformat()
        timeline.append(event)
        activation.timeline = timeline
    if body.resolution_notes:
        activation.resolution_notes = body.resolution_notes
    if body.lessons_learned:
        activation.lessons_learned = body.lessons_learned
    if body.resolved_at:
        activation.resolved_at = datetime.fromisoformat(body.resolved_at)
        activation.status = "resolved"
    elif body.status in ("resolved", "stood_down"):
        activation.resolved_at = datetime.utcnow()
    if body.metadata is not None:
        activation.metadata_ = body.metadata
    db.commit()
    db.refresh(activation)
    return activation.to_dict()


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@router.get("/dashboard")
def get_bcm_dashboard(
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """BCM executive dashboard metrics."""
    year_start = datetime.utcnow().replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)

    critical_processes = db.query(BiaRecord).filter(
        BiaRecord.tenant_id == tenant_id,
        BiaRecord.criticality == BcmCriticality.CRITICAL,
    ).count()

    plans_tested_this_year = db.query(BcmPlan).filter(
        BcmPlan.tenant_id == tenant_id,
        BcmPlan.last_tested >= year_start,
    ).count()

    active_incidents = db.query(IncidentActivation).filter(
        IncidentActivation.tenant_id == tenant_id,
        IncidentActivation.status == BcmActivationStatus.ACTIVE,
    ).count()

    plans_due_test = db.query(BcmPlan).filter(
        BcmPlan.tenant_id == tenant_id,
        BcmPlan.status == BcmPlanStatus.ACTIVE,
        BcmPlan.next_test_date <= datetime.utcnow(),
    ).count()

    total_plans = db.query(BcmPlan).filter(
        BcmPlan.tenant_id == tenant_id,
        BcmPlan.status == BcmPlanStatus.ACTIVE,
    ).count()

    total_bia = db.query(BiaRecord).filter(BiaRecord.tenant_id == tenant_id).count()

    return {
        "critical_processes": critical_processes,
        "plans_tested_this_year": plans_tested_this_year,
        "active_incidents": active_incidents,
        "plans_due_test": plans_due_test,
        "total_active_plans": total_plans,
        "total_bia_records": total_bia,
    }
