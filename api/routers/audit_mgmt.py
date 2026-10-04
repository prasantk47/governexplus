"""
Audit Management API Router

Full internal audit lifecycle (AM-01 through AM-32):
  - Audit universe (auditable entities)
  - Annual audit planning with risk-based prioritisation
  - Engagement management with lifecycle advancement
  - Work programs (reusable procedure templates)
  - Procedure and workpaper management with e-sign-off
  - Formal findings (CCCE) with cross-module linking
  - Management action tracking with escalation
  - Time tracking and auditor resource management
  - Committee-ready reporting
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import uuid

from db.database import get_db
from db.models.audit_management import (
    AuditableEntity, AuditableEntityType,
    AuditPlan, AuditPlanType, AuditPlanStatus,
    AuditEngagement, EngagementType, EngagementStatus,
    AuditWorkProgram,
    AuditProcedure, ProcedureStatus,
    AuditWorkpaper, WorkpaperStatus, WorkpaperReviewStatus,
    AuditFinding, FindingSeverity, FindingStatus,
    AuditManagementAction, ActionStatus,
    AuditorTimeEntry,
    AuditorResource,
    AuditDimension, DimensionType,
    AuditAnnouncement, AnnouncementStatus,
)

router = APIRouter(tags=["Audit Management"])


# ---------------------------------------------------------------------------
# Tenant helpers
# ---------------------------------------------------------------------------

def _get_tenant_id() -> str:
    from core.tenant import get_current_tenant
    ctx = get_current_tenant()
    return ctx.tenant_id if ctx else "default"


def _get_manager(
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """DI factory: returns a per-request AuditManagementManager."""
    from core.audit_management.manager import AuditManagementManager
    return AuditManagementManager(tenant_id=tenant_id, db=db)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def _entity_or_404(db: Session, entity_id: str, tenant_id: str) -> AuditableEntity:
    e = db.query(AuditableEntity).filter(
        AuditableEntity.entity_id == entity_id,
        AuditableEntity.tenant_id == tenant_id,
        AuditableEntity.is_active.is_(True),
    ).first()
    if not e:
        raise HTTPException(status_code=404, detail=f"Auditable entity '{entity_id}' not found")
    return e


def _plan_or_404(db: Session, plan_id: str, tenant_id: str) -> AuditPlan:
    p = db.query(AuditPlan).filter(
        AuditPlan.plan_id == plan_id,
        AuditPlan.tenant_id == tenant_id,
    ).first()
    if not p:
        raise HTTPException(status_code=404, detail=f"Audit plan '{plan_id}' not found")
    return p


def _engagement_or_404(db: Session, engagement_id: str, tenant_id: str) -> AuditEngagement:
    e = db.query(AuditEngagement).filter(
        AuditEngagement.engagement_id == engagement_id,
        AuditEngagement.tenant_id == tenant_id,
    ).first()
    if not e:
        raise HTTPException(status_code=404, detail=f"Engagement '{engagement_id}' not found")
    return e


def _procedure_or_404(db: Session, procedure_id: str, tenant_id: str) -> AuditProcedure:
    p = db.query(AuditProcedure).filter(
        AuditProcedure.procedure_id == procedure_id,
        AuditProcedure.tenant_id == tenant_id,
    ).first()
    if not p:
        raise HTTPException(status_code=404, detail=f"Procedure '{procedure_id}' not found")
    return p


def _workpaper_or_404(db: Session, workpaper_id: str, tenant_id: str) -> AuditWorkpaper:
    w = db.query(AuditWorkpaper).filter(
        AuditWorkpaper.workpaper_id == workpaper_id,
        AuditWorkpaper.tenant_id == tenant_id,
    ).first()
    if not w:
        raise HTTPException(status_code=404, detail=f"Workpaper '{workpaper_id}' not found")
    return w


def _finding_or_404(db: Session, finding_id: str, tenant_id: str) -> AuditFinding:
    f = db.query(AuditFinding).filter(
        AuditFinding.finding_id == finding_id,
        AuditFinding.tenant_id == tenant_id,
    ).first()
    if not f:
        raise HTTPException(status_code=404, detail=f"Finding '{finding_id}' not found")
    return f


def _action_or_404(db: Session, action_id: str, tenant_id: str) -> AuditManagementAction:
    a = db.query(AuditManagementAction).filter(
        AuditManagementAction.action_id == action_id,
        AuditManagementAction.tenant_id == tenant_id,
    ).first()
    if not a:
        raise HTTPException(status_code=404, detail=f"Action '{action_id}' not found")
    return a


# Engagement status order for advancement
_ENGAGEMENT_STATUS_ORDER = [
    EngagementStatus.PLANNED,
    EngagementStatus.ANNOUNCED,
    EngagementStatus.FIELDWORK,
    EngagementStatus.DRAFT_REPORT,
    EngagementStatus.FINAL_REPORT,
    EngagementStatus.CLOSED,
]


# ===========================================================================
# Audit Universe  (AM-01)
# ===========================================================================

@router.post("/entities", status_code=201)
def create_entity(
    body: Dict[str, Any] = Body(default={}),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Add an entity to the audit universe."""
    try:
        entity_type = AuditableEntityType(body.get("entity_type", "org_unit"))
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid entity_type")

    e = AuditableEntity(
        tenant_id=tenant_id,
        entity_id=body.get("entity_id") or _new_id("ENT"),
        name=body["name"],
        description=body.get("description"),
        entity_type=entity_type,
        org_unit_id=body.get("org_unit_id"),
        risk_score=body.get("risk_score"),
        last_audited_at=datetime.fromisoformat(body["last_audited_at"]) if body.get("last_audited_at") else None,
        audit_frequency=body.get("audit_frequency", "annual"),
        primary_auditor_id=body.get("primary_auditor_id"),
        is_active=True,
        metadata_=body.get("metadata"),
    )
    db.add(e)
    db.commit()
    db.refresh(e)
    return e.to_dict()


@router.get("/entities")
def list_entities(
    entity_type: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    q = db.query(AuditableEntity).filter(AuditableEntity.tenant_id == tenant_id)
    if entity_type:
        q = q.filter(AuditableEntity.entity_type == AuditableEntityType(entity_type))
    if is_active is not None:
        q = q.filter(AuditableEntity.is_active == is_active)
    if search:
        q = q.filter(AuditableEntity.name.ilike(f"%{search}%"))
    entities = q.order_by(AuditableEntity.risk_score.desc().nullslast()).all()
    return {"total": len(entities), "entities": [e.to_dict() for e in entities]}


@router.put("/entities/{entity_id}")
def update_entity(
    entity_id: str,
    body: Dict[str, Any] = Body(default={}),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    e = _entity_or_404(db, entity_id, tenant_id)
    for field in ["name", "description", "risk_score", "audit_frequency", "primary_auditor_id", "metadata_"]:
        if field in body:
            setattr(e, field, body[field])
    db.commit()
    db.refresh(e)
    return e.to_dict()


@router.post("/entities/{entity_id}/compute-risk")
def compute_entity_risk(
    entity_id: str,
    body: Dict[str, Any] = Body(default={}),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Compute and store a risk score for an auditable entity."""
    e = _entity_or_404(db, entity_id, tenant_id)
    # Weighted scoring from supplied dimensions
    weights = body.get("weights", {"inherent_risk": 0.4, "control_effectiveness": 0.35, "last_audit_recency": 0.25})
    scores = body.get("scores", {})
    risk_score = sum(weights.get(k, 0) * v for k, v in scores.items())
    e.risk_score = round(risk_score, 2)
    db.commit()
    return {"entity_id": entity_id, "computed_risk_score": e.risk_score, "inputs": scores}


# ===========================================================================
# Audit Plans  (AM-02)
# ===========================================================================

@router.post("/plans", status_code=201)
def create_plan(
    body: Dict[str, Any] = Body(default={}),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    try:
        plan_type = AuditPlanType(body.get("plan_type", "annual"))
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid plan_type")

    p = AuditPlan(
        tenant_id=tenant_id,
        plan_id=body.get("plan_id") or _new_id("PLAN"),
        name=body["name"],
        description=body.get("description"),
        plan_type=plan_type,
        fiscal_year=body.get("fiscal_year", datetime.utcnow().year),
        period_start=datetime.fromisoformat(body["period_start"]) if body.get("period_start") else None,
        period_end=datetime.fromisoformat(body["period_end"]) if body.get("period_end") else None,
        total_audit_hours=body.get("total_audit_hours"),
        allocated_budget=body.get("allocated_budget"),
        status=AuditPlanStatus.DRAFT,
        prepared_by=body.get("prepared_by"),
        risk_methodology=body.get("risk_methodology"),
        metadata_=body.get("metadata"),
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return p.to_dict()


@router.get("/plans")
def list_plans(
    status: Optional[str] = Query(None),
    fiscal_year: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    q = db.query(AuditPlan).filter(AuditPlan.tenant_id == tenant_id)
    if status:
        q = q.filter(AuditPlan.status == AuditPlanStatus(status))
    if fiscal_year:
        q = q.filter(AuditPlan.fiscal_year == fiscal_year)
    plans = q.order_by(AuditPlan.fiscal_year.desc()).all()
    return {"total": len(plans), "plans": [p.to_dict() for p in plans]}


@router.get("/plans/{plan_id}")
def get_plan(
    plan_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    return _plan_or_404(db, plan_id, tenant_id).to_dict()


@router.put("/plans/{plan_id}")
def update_plan(
    plan_id: str,
    body: Dict[str, Any] = Body(default={}),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    p = _plan_or_404(db, plan_id, tenant_id)
    for field in ["name", "description", "total_audit_hours", "allocated_budget", "risk_methodology"]:
        if field in body:
            setattr(p, field, body[field])
    db.commit()
    db.refresh(p)
    return p.to_dict()


@router.put("/plans/{plan_id}/submit")
def submit_plan(
    plan_id: str,
    body: Dict[str, Any] = Body(default={}),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    p = _plan_or_404(db, plan_id, tenant_id)
    p.status = AuditPlanStatus.PENDING_APPROVAL
    db.commit()
    db.refresh(p)
    return p.to_dict()


@router.put("/plans/{plan_id}/approve")
def approve_plan(
    plan_id: str,
    body: Dict[str, Any] = Body(default={}),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    p = _plan_or_404(db, plan_id, tenant_id)
    p.status = AuditPlanStatus.APPROVED
    p.approved_by = body.get("approved_by")
    p.approved_at = datetime.utcnow()
    db.commit()
    db.refresh(p)
    return p.to_dict()


@router.post("/plans/generate-risk-based")
def generate_risk_based_plan(
    body: Dict[str, Any] = Body(default={}),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Auto-generate an audit plan from the top-risk auditable entities."""
    fiscal_year = body.get("fiscal_year", datetime.utcnow().year)
    top_n = body.get("top_n", 10)
    entities = db.query(AuditableEntity).filter(
        AuditableEntity.tenant_id == tenant_id,
        AuditableEntity.is_active.is_(True),
    ).order_by(AuditableEntity.risk_score.desc().nullslast()).limit(top_n).all()

    plan = AuditPlan(
        tenant_id=tenant_id,
        plan_id=_new_id("PLAN"),
        name=f"Risk-Based Audit Plan {fiscal_year}",
        description="Auto-generated based on entity risk scores",
        plan_type=AuditPlanType.ANNUAL,
        fiscal_year=fiscal_year,
        status=AuditPlanStatus.DRAFT,
        prepared_by=body.get("prepared_by", "system"),
        risk_methodology="Top-N risk score ranking from audit universe",
    )
    db.add(plan)
    db.flush()

    engagements_created = []
    for ent in entities:
        eng = AuditEngagement(
            tenant_id=tenant_id,
            engagement_id=_new_id("ENG"),
            plan_id=plan.id,
            entity_id=ent.id,
            title=f"Audit of {ent.name}",
            engagement_type=EngagementType.OPERATIONAL,
            status=EngagementStatus.PLANNED,
            risk_rating="high" if (ent.risk_score or 0) >= 15 else "medium",
        )
        db.add(eng)
        engagements_created.append(eng.engagement_id)

    db.commit()
    return {
        "plan_id": plan.plan_id,
        "fiscal_year": fiscal_year,
        "entities_included": len(entities),
        "engagements_created": engagements_created,
    }


# ===========================================================================
# Engagements  (AM-10)
# ===========================================================================

@router.post("/engagements", status_code=201)
def create_engagement(
    body: Dict[str, Any] = Body(default={}),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    try:
        engagement_type = EngagementType(body.get("engagement_type", "operational"))
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid engagement_type")

    # Resolve plan and entity PKs from string IDs
    plan_pk = None
    if body.get("plan_id"):
        p = db.query(AuditPlan).filter(
            AuditPlan.plan_id == body["plan_id"],
            AuditPlan.tenant_id == tenant_id,
        ).first()
        if p:
            plan_pk = p.id

    entity_pk = None
    if body.get("entity_id"):
        ent = db.query(AuditableEntity).filter(
            AuditableEntity.entity_id == body["entity_id"],
            AuditableEntity.tenant_id == tenant_id,
        ).first()
        if ent:
            entity_pk = ent.id

    eng = AuditEngagement(
        tenant_id=tenant_id,
        engagement_id=body.get("engagement_id") or _new_id("ENG"),
        plan_id=plan_pk,
        entity_id=entity_pk,
        title=body["title"],
        objective=body.get("objective"),
        scope=body.get("scope"),
        engagement_type=engagement_type,
        status=EngagementStatus.PLANNED,
        lead_auditor_id=body.get("lead_auditor_id"),
        lead_auditor_name=body.get("lead_auditor_name"),
        team_members=body.get("team_members", []),
        planned_start=datetime.fromisoformat(body["planned_start"]) if body.get("planned_start") else None,
        planned_end=datetime.fromisoformat(body["planned_end"]) if body.get("planned_end") else None,
        budget_hours=body.get("budget_hours"),
        risk_rating=body.get("risk_rating"),
        methodology=body.get("methodology"),
    )
    db.add(eng)
    db.commit()
    db.refresh(eng)
    return eng.to_dict()


@router.get("/engagements")
def list_engagements(
    status: Optional[str] = Query(None),
    engagement_type: Optional[str] = Query(None),
    lead_auditor_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    q = db.query(AuditEngagement).filter(AuditEngagement.tenant_id == tenant_id)
    if status:
        q = q.filter(AuditEngagement.status == EngagementStatus(status))
    if engagement_type:
        q = q.filter(AuditEngagement.engagement_type == EngagementType(engagement_type))
    if lead_auditor_id:
        q = q.filter(AuditEngagement.lead_auditor_id == lead_auditor_id)
    engagements = q.order_by(AuditEngagement.planned_start.desc().nullslast()).all()
    return {"total": len(engagements), "engagements": [e.to_dict() for e in engagements]}


@router.get("/engagements/{engagement_id}")
def get_engagement(
    engagement_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    return _engagement_or_404(db, engagement_id, tenant_id).to_dict()


@router.put("/engagements/{engagement_id}")
def update_engagement(
    engagement_id: str,
    body: Dict[str, Any] = Body(default={}),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    eng = _engagement_or_404(db, engagement_id, tenant_id)
    for field in ["title", "objective", "scope", "lead_auditor_id", "lead_auditor_name",
                  "team_members", "budget_hours", "risk_rating", "methodology"]:
        if field in body:
            setattr(eng, field, body[field])
    if "actual_start" in body:
        eng.actual_start = datetime.fromisoformat(body["actual_start"])
    if "actual_end" in body:
        eng.actual_end = datetime.fromisoformat(body["actual_end"])
    db.commit()
    db.refresh(eng)
    return eng.to_dict()


@router.put("/engagements/{engagement_id}/advance")
def advance_engagement(
    engagement_id: str,
    body: Dict[str, Any] = Body(default={}),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Advance the engagement to the next lifecycle status."""
    eng = _engagement_or_404(db, engagement_id, tenant_id)
    current_index = next(
        (i for i, s in enumerate(_ENGAGEMENT_STATUS_ORDER) if s == eng.status), None
    )
    if current_index is None or current_index >= len(_ENGAGEMENT_STATUS_ORDER) - 1:
        raise HTTPException(status_code=400, detail="Engagement cannot be advanced further")
    eng.status = _ENGAGEMENT_STATUS_ORDER[current_index + 1]
    if eng.status == EngagementStatus.FIELDWORK:
        eng.actual_start = datetime.utcnow()
    if eng.status == EngagementStatus.CLOSED:
        eng.actual_end = datetime.utcnow()
    db.commit()
    db.refresh(eng)
    return eng.to_dict()


# ===========================================================================
# Work Programs  (AM-11)
# ===========================================================================

@router.post("/work-programs", status_code=201)
def create_work_program(
    body: Dict[str, Any] = Body(default={}),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    wp = AuditWorkProgram(
        tenant_id=tenant_id,
        program_id=body.get("program_id") or _new_id("WP"),
        name=body["name"],
        description=body.get("description"),
        audit_type=body.get("audit_type"),
        procedures=body.get("procedures", []),
        is_template=body.get("is_template", True),
        version=1,
    )
    db.add(wp)
    db.commit()
    db.refresh(wp)
    return wp.to_dict()


@router.get("/work-programs/templates")
def list_work_program_templates(
    audit_type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    q = db.query(AuditWorkProgram).filter(
        AuditWorkProgram.tenant_id == tenant_id,
        AuditWorkProgram.is_template.is_(True),
    )
    if audit_type:
        q = q.filter(AuditWorkProgram.audit_type == audit_type)
    templates = q.all()
    return {"total": len(templates), "templates": [t.to_dict() for t in templates]}


@router.post("/work-programs/{program_id}/clone")
def clone_work_program(
    program_id: str,
    body: Dict[str, Any] = Body(default={}),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Clone a work program template for use in a specific engagement."""
    source = db.query(AuditWorkProgram).filter(
        AuditWorkProgram.program_id == program_id,
        AuditWorkProgram.tenant_id == tenant_id,
    ).first()
    if not source:
        raise HTTPException(status_code=404, detail=f"Work program '{program_id}' not found")

    clone = AuditWorkProgram(
        tenant_id=tenant_id,
        program_id=_new_id("WP"),
        name=body.get("name", f"Copy of {source.name}"),
        description=source.description,
        audit_type=source.audit_type,
        procedures=source.procedures,
        is_template=False,
        version=1,
    )
    db.add(clone)
    db.commit()
    db.refresh(clone)
    return clone.to_dict()


# ===========================================================================
# Procedures
# ===========================================================================

@router.post("/engagements/{engagement_id}/procedures", status_code=201)
def create_procedure(
    engagement_id: str,
    body: Dict[str, Any] = Body(default={}),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    eng = _engagement_or_404(db, engagement_id, tenant_id)
    p = AuditProcedure(
        tenant_id=tenant_id,
        procedure_id=_new_id("PROC"),
        engagement_id=eng.id,
        ref_number=body.get("ref_number"),
        title=body["title"],
        description=body.get("description"),
        assigned_to_id=body.get("assigned_to_id"),
        assigned_to_name=body.get("assigned_to_name"),
        status=ProcedureStatus.NOT_STARTED,
        hours_spent=0.0,
        evidence_ids=body.get("evidence_ids", []),
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return p.to_dict()


@router.get("/engagements/{engagement_id}/procedures")
def list_procedures(
    engagement_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    eng = _engagement_or_404(db, engagement_id, tenant_id)
    procedures = db.query(AuditProcedure).filter(
        AuditProcedure.engagement_id == eng.id,
        AuditProcedure.tenant_id == tenant_id,
    ).all()
    return {"total": len(procedures), "procedures": [p.to_dict() for p in procedures]}


@router.put("/procedures/{procedure_id}")
def update_procedure(
    procedure_id: str,
    body: Dict[str, Any] = Body(default={}),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    p = _procedure_or_404(db, procedure_id, tenant_id)
    for field in ["title", "description", "assigned_to_id", "assigned_to_name",
                  "conclusion", "hours_spent", "evidence_ids", "cross_references"]:
        if field in body:
            setattr(p, field, body[field])
    db.commit()
    db.refresh(p)
    return p.to_dict()


@router.put("/procedures/{procedure_id}/complete")
def complete_procedure(
    procedure_id: str,
    body: Dict[str, Any] = Body(default={}),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    p = _procedure_or_404(db, procedure_id, tenant_id)
    p.status = ProcedureStatus.COMPLETED
    p.conclusion = body.get("conclusion", p.conclusion)
    p.preparer_id = body.get("preparer_id", p.preparer_id)
    p.prepared_at = datetime.utcnow()
    if "hours_spent" in body:
        p.hours_spent = body["hours_spent"]
    db.commit()
    db.refresh(p)
    return p.to_dict()


@router.put("/procedures/{procedure_id}/review")
def review_procedure(
    procedure_id: str,
    body: Dict[str, Any] = Body(default={}),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    p = _procedure_or_404(db, procedure_id, tenant_id)
    p.status = ProcedureStatus.REVIEWED
    p.reviewer_id = body.get("reviewer_id")
    p.reviewed_at = datetime.utcnow()
    p.review_notes = body.get("review_notes")
    db.commit()
    db.refresh(p)
    return p.to_dict()


# ===========================================================================
# Workpapers  (AM-12)
# ===========================================================================

@router.post("/engagements/{engagement_id}/workpapers", status_code=201)
def create_workpaper(
    engagement_id: str,
    body: Dict[str, Any] = Body(default={}),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    eng = _engagement_or_404(db, engagement_id, tenant_id)
    w = AuditWorkpaper(
        tenant_id=tenant_id,
        workpaper_id=_new_id("WPR"),
        engagement_id=eng.id,
        procedure_id=body.get("procedure_id"),
        title=body["title"],
        description=body.get("description"),
        document_type=body.get("document_type", "narrative"),
        file_name=body.get("file_name"),
        file_path=body.get("file_path"),
        file_size=body.get("file_size"),
        content=body.get("content"),
        version=1,
        preparer_id=body.get("preparer_id"),
        prepared_at=datetime.utcnow() if body.get("preparer_id") else None,
        review_status=WorkpaperReviewStatus.PENDING_REVIEW,
        status=WorkpaperStatus.DRAFT,
        cross_references=body.get("cross_references", []),
    )
    db.add(w)
    db.commit()
    db.refresh(w)
    return w.to_dict()


@router.get("/engagements/{engagement_id}/workpapers")
def list_workpapers(
    engagement_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    eng = _engagement_or_404(db, engagement_id, tenant_id)
    workpapers = db.query(AuditWorkpaper).filter(
        AuditWorkpaper.engagement_id == eng.id,
        AuditWorkpaper.tenant_id == tenant_id,
    ).all()
    return {"total": len(workpapers), "workpapers": [w.to_dict() for w in workpapers]}


@router.put("/workpapers/{workpaper_id}")
def update_workpaper(
    workpaper_id: str,
    body: Dict[str, Any] = Body(default={}),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    w = _workpaper_or_404(db, workpaper_id, tenant_id)
    for field in ["title", "description", "content", "file_name", "file_path", "cross_references"]:
        if field in body:
            setattr(w, field, body[field])
    db.commit()
    db.refresh(w)
    return w.to_dict()


@router.put("/workpapers/{workpaper_id}/submit-review")
def submit_workpaper_for_review(
    workpaper_id: str,
    body: Dict[str, Any] = Body(default={}),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    w = _workpaper_or_404(db, workpaper_id, tenant_id)
    w.review_status = WorkpaperReviewStatus.PENDING_REVIEW
    db.commit()
    db.refresh(w)
    return w.to_dict()


@router.put("/workpapers/{workpaper_id}/review")
def review_workpaper(
    workpaper_id: str,
    body: Dict[str, Any] = Body(default={}),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    w = _workpaper_or_404(db, workpaper_id, tenant_id)
    approved = body.get("approved", True)
    w.reviewer_id = body.get("reviewer_id")
    w.reviewed_at = datetime.utcnow()
    notes = w.review_notes or []
    notes.append({
        "reviewer_id": body.get("reviewer_id"),
        "note": body.get("review_note", ""),
        "approved": approved,
        "timestamp": datetime.utcnow().isoformat(),
    })
    w.review_notes = notes
    w.review_status = (
        WorkpaperReviewStatus.REVIEWED if approved
        else WorkpaperReviewStatus.REVISION_NEEDED
    )
    if approved:
        w.status = WorkpaperStatus.FINAL
    db.commit()
    db.refresh(w)
    return w.to_dict()


# ===========================================================================
# Findings  (AM-20)
# ===========================================================================

@router.post("/engagements/{engagement_id}/findings", status_code=201)
def create_finding(
    engagement_id: str,
    body: Dict[str, Any] = Body(default={}),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    eng = _engagement_or_404(db, engagement_id, tenant_id)
    try:
        severity = FindingSeverity(body.get("severity", "medium"))
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid severity")

    f = AuditFinding(
        tenant_id=tenant_id,
        finding_id=_new_id("FND"),
        engagement_id=eng.id,
        ref_number=body.get("ref_number"),
        title=body["title"],
        condition=body.get("condition"),
        criteria=body.get("criteria"),
        cause=body.get("cause"),
        effect=body.get("effect"),
        recommendation=body.get("recommendation"),
        severity=severity,
        category=body.get("category"),
        status=FindingStatus.DRAFT,
        repeat_finding=body.get("repeat_finding", False),
    )
    db.add(f)
    db.commit()
    db.refresh(f)
    return f.to_dict()


@router.get("/findings")
def list_findings(
    status: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    engagement_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    q = db.query(AuditFinding).filter(AuditFinding.tenant_id == tenant_id)
    if status:
        q = q.filter(AuditFinding.status == FindingStatus(status))
    if severity:
        q = q.filter(AuditFinding.severity == FindingSeverity(severity))
    if engagement_id:
        eng = db.query(AuditEngagement).filter(
            AuditEngagement.engagement_id == engagement_id,
            AuditEngagement.tenant_id == tenant_id,
        ).first()
        if eng:
            q = q.filter(AuditFinding.engagement_id == eng.id)
    findings = q.order_by(AuditFinding.created_at.desc()).all()
    return {"total": len(findings), "findings": [f.to_dict() for f in findings]}


@router.put("/findings/{finding_id}")
def update_finding(
    finding_id: str,
    body: Dict[str, Any] = Body(default={}),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    f = _finding_or_404(db, finding_id, tenant_id)
    for field in ["title", "condition", "criteria", "cause", "effect", "recommendation", "category"]:
        if field in body:
            setattr(f, field, body[field])
    if "severity" in body:
        f.severity = FindingSeverity(body["severity"])
    if "status" in body:
        f.status = FindingStatus(body["status"])
    db.commit()
    db.refresh(f)
    return f.to_dict()


@router.put("/findings/{finding_id}/management-response")
def record_management_response(
    finding_id: str,
    body: Dict[str, Any] = Body(default={}),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    f = _finding_or_404(db, finding_id, tenant_id)
    f.management_response = body.get("management_response")
    f.management_action_owner = body.get("management_action_owner")
    f.management_target_date = (
        datetime.fromisoformat(body["management_target_date"])
        if body.get("management_target_date") else None
    )
    f.status = FindingStatus.MANAGEMENT_RESPONSE_RECEIVED
    db.commit()
    db.refresh(f)
    return f.to_dict()


@router.post("/findings/{finding_id}/link-risk")
def link_finding_to_risk(
    finding_id: str,
    body: Dict[str, Any] = Body(default={}),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    f = _finding_or_404(db, finding_id, tenant_id)
    from db.models.risk_management import EnterpriseRisk
    risk = db.query(EnterpriseRisk).filter(
        EnterpriseRisk.risk_id == body["risk_id"],
        EnterpriseRisk.tenant_id == tenant_id,
    ).first()
    if not risk:
        raise HTTPException(status_code=404, detail="Risk not found")
    f.risk_id = risk.id
    db.commit()
    return {"finding_id": finding_id, "linked_risk_id": body["risk_id"]}


@router.post("/findings/{finding_id}/link-control")
def link_finding_to_control(
    finding_id: str,
    body: Dict[str, Any] = Body(default={}),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    f = _finding_or_404(db, finding_id, tenant_id)
    from db.models.process_control import ProcessControl
    ctrl = db.query(ProcessControl).filter(
        ProcessControl.control_id == body["control_id"],
        ProcessControl.tenant_id == tenant_id,
    ).first()
    if not ctrl:
        raise HTTPException(status_code=404, detail="Control not found")
    f.control_id = ctrl.id
    db.commit()
    return {"finding_id": finding_id, "linked_control_id": body["control_id"]}


@router.post("/findings/{finding_id}/link-violation")
def link_finding_to_violation(
    finding_id: str,
    body: Dict[str, Any] = Body(default={}),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    f = _finding_or_404(db, finding_id, tenant_id)
    f.violation_id = body["violation_id"]
    db.commit()
    return {"finding_id": finding_id, "linked_violation_id": body["violation_id"]}


@router.get("/findings/{finding_id}/check-repeat")
def check_repeat_finding(
    finding_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    f = _finding_or_404(db, finding_id, tenant_id)
    # Look for prior findings with the same title in older engagements
    prior = db.query(AuditFinding).filter(
        AuditFinding.tenant_id == tenant_id,
        AuditFinding.title == f.title,
        AuditFinding.id != f.id,
    ).order_by(AuditFinding.created_at.desc()).all()
    if prior:
        f.repeat_finding = True
        f.prior_finding_id = prior[0].id
        db.commit()
    return {
        "finding_id": finding_id,
        "is_repeat": f.repeat_finding,
        "prior_findings": [p.finding_id for p in prior],
    }


# ===========================================================================
# Management Actions  (AM-21)
# ===========================================================================

@router.post("/findings/{finding_id}/actions", status_code=201)
def create_action(
    finding_id: str,
    body: Dict[str, Any] = Body(default={}),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    f = _finding_or_404(db, finding_id, tenant_id)
    a = AuditManagementAction(
        tenant_id=tenant_id,
        action_id=_new_id("ACT"),
        finding_id=f.id,
        description=body["description"],
        owner_id=body.get("owner_id"),
        owner_name=body.get("owner_name"),
        due_date=datetime.fromisoformat(body["due_date"]) if body.get("due_date") else None,
        status=ActionStatus.OPEN,
        escalation_level=0,
    )
    db.add(a)
    db.commit()
    db.refresh(a)
    return a.to_dict()


@router.put("/actions/{action_id}")
def update_action(
    action_id: str,
    body: Dict[str, Any] = Body(default={}),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    a = _action_or_404(db, action_id, tenant_id)
    for field in ["description", "owner_id", "owner_name", "evidence_of_closure", "evidence_ids"]:
        if field in body:
            setattr(a, field, body[field])
    if "due_date" in body and body["due_date"]:
        a.due_date = datetime.fromisoformat(body["due_date"])
    db.commit()
    db.refresh(a)
    return a.to_dict()


@router.put("/actions/{action_id}/close")
def close_action(
    action_id: str,
    body: Dict[str, Any] = Body(default={}),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    a = _action_or_404(db, action_id, tenant_id)
    a.status = ActionStatus.COMPLETED
    a.completed_at = datetime.utcnow()
    a.evidence_of_closure = body.get("evidence_of_closure")
    a.evidence_ids = body.get("evidence_ids", [])
    a.verified_by = body.get("verified_by")
    a.verified_at = datetime.utcnow() if body.get("verified_by") else None
    if body.get("verified_by"):
        a.status = ActionStatus.CLOSED_VERIFIED
    db.commit()
    db.refresh(a)
    return a.to_dict()


@router.get("/actions/overdue")
def get_overdue_actions(
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    now = datetime.utcnow()
    actions = db.query(AuditManagementAction).filter(
        AuditManagementAction.tenant_id == tenant_id,
        AuditManagementAction.due_date < now,
        AuditManagementAction.status.in_([ActionStatus.OPEN, ActionStatus.IN_PROGRESS]),
    ).all()
    # Mark as OVERDUE
    for a in actions:
        a.status = ActionStatus.OVERDUE
    db.commit()
    return {"total_overdue": len(actions), "actions": [a.to_dict() for a in actions]}


@router.post("/actions/escalate")
def escalate_actions(
    body: Dict[str, Any] = Body(default={}),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Escalate all overdue actions by incrementing their escalation level."""
    now = datetime.utcnow()
    actions = db.query(AuditManagementAction).filter(
        AuditManagementAction.tenant_id == tenant_id,
        AuditManagementAction.due_date < now,
        AuditManagementAction.status.in_([ActionStatus.OPEN, ActionStatus.IN_PROGRESS, ActionStatus.OVERDUE]),
    ).all()
    escalated = []
    for a in actions:
        a.escalation_level += 1
        a.last_escalated_at = datetime.utcnow()
        a.status = ActionStatus.OVERDUE
        escalated.append(a.action_id)
    db.commit()
    return {"escalated_count": len(escalated), "action_ids": escalated}


# ===========================================================================
# Time Tracking  (AM-14)
# ===========================================================================

@router.post("/engagements/{engagement_id}/time", status_code=201)
def log_time(
    engagement_id: str,
    body: Dict[str, Any] = Body(default={}),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    eng = _engagement_or_404(db, engagement_id, tenant_id)
    entry = AuditorTimeEntry(
        tenant_id=tenant_id,
        engagement_id=eng.id,
        procedure_id=body.get("procedure_id"),
        auditor_id=body["auditor_id"],
        auditor_name=body.get("auditor_name"),
        date=datetime.fromisoformat(body.get("date", datetime.utcnow().isoformat())),
        hours=body["hours"],
        activity_type=body.get("activity_type", "fieldwork"),
        description=body.get("description"),
    )
    db.add(entry)
    # Accumulate actual hours on engagement
    eng.actual_hours = (eng.actual_hours or 0) + body["hours"]
    db.commit()
    db.refresh(entry)
    return entry.to_dict()


@router.get("/engagements/{engagement_id}/time-summary")
def get_time_summary(
    engagement_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    eng = _engagement_or_404(db, engagement_id, tenant_id)
    entries = db.query(AuditorTimeEntry).filter(
        AuditorTimeEntry.engagement_id == eng.id,
        AuditorTimeEntry.tenant_id == tenant_id,
    ).all()
    by_auditor: Dict[str, float] = {}
    by_activity: Dict[str, float] = {}
    for e in entries:
        by_auditor[e.auditor_id] = by_auditor.get(e.auditor_id, 0) + e.hours
        act = e.activity_type or "other"
        by_activity[act] = by_activity.get(act, 0) + e.hours
    return {
        "engagement_id": engagement_id,
        "total_hours": eng.actual_hours or 0,
        "budget_hours": eng.budget_hours,
        "by_auditor": by_auditor,
        "by_activity": by_activity,
        "entries": [e.to_dict() for e in entries],
    }


@router.get("/auditors/{auditor_id}/utilization")
def get_auditor_utilization(
    auditor_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    entries = db.query(AuditorTimeEntry).filter(
        AuditorTimeEntry.tenant_id == tenant_id,
        AuditorTimeEntry.auditor_id == auditor_id,
    ).all()
    total_hours = sum(e.hours for e in entries)
    resource = db.query(AuditorResource).filter(
        AuditorResource.tenant_id == tenant_id,
        AuditorResource.auditor_id == auditor_id,
    ).first()
    available_monthly = resource.available_hours_per_month if resource else 160.0
    return {
        "auditor_id": auditor_id,
        "total_hours_logged": total_hours,
        "available_hours_per_month": available_monthly,
        "utilization_pct": round(total_hours / available_monthly * 100, 1) if available_monthly else None,
    }


# ===========================================================================
# Auditor Resources  (AM-03)
# ===========================================================================

@router.post("/resources", status_code=201)
def create_auditor_resource(
    body: Dict[str, Any] = Body(default={}),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    r = AuditorResource(
        tenant_id=tenant_id,
        auditor_id=body.get("auditor_id") or _new_id("AUD"),
        name=body["name"],
        email=body.get("email"),
        title=body.get("title"),
        skills=body.get("skills", []),
        certifications=body.get("certifications", []),
        available_hours_per_month=body.get("available_hours_per_month", 160.0),
        is_active=True,
        is_external=body.get("is_external", False),
    )
    db.add(r)
    db.commit()
    db.refresh(r)
    return r.to_dict()


@router.get("/resources")
def list_auditor_resources(
    is_external: Optional[bool] = Query(None),
    is_active: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    q = db.query(AuditorResource).filter(AuditorResource.tenant_id == tenant_id)
    if is_external is not None:
        q = q.filter(AuditorResource.is_external == is_external)
    if is_active is not None:
        q = q.filter(AuditorResource.is_active == is_active)
    resources = q.all()
    return {"total": len(resources), "resources": [r.to_dict() for r in resources]}


@router.put("/resources/{auditor_id}")
def update_auditor_resource(
    auditor_id: str,
    body: Dict[str, Any] = Body(default={}),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    r = db.query(AuditorResource).filter(
        AuditorResource.auditor_id == auditor_id,
        AuditorResource.tenant_id == tenant_id,
    ).first()
    if not r:
        raise HTTPException(status_code=404, detail=f"Auditor '{auditor_id}' not found")
    for field in ["name", "email", "title", "skills", "certifications", "available_hours_per_month", "is_active"]:
        if field in body:
            setattr(r, field, body[field])
    db.commit()
    db.refresh(r)
    return r.to_dict()


@router.get("/resources/available")
def get_available_auditors(
    min_hours: float = Query(default=0.0),
    skill: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    resources = db.query(AuditorResource).filter(
        AuditorResource.tenant_id == tenant_id,
        AuditorResource.is_active.is_(True),
        AuditorResource.available_hours_per_month >= min_hours,
    ).all()
    if skill:
        resources = [r for r in resources if skill in (r.skills or [])]
    return {"total": len(resources), "auditors": [r.to_dict() for r in resources]}


# ===========================================================================
# Reporting  (AM-31, AM-32)
# ===========================================================================

@router.get("/engagements/{engagement_id}/report")
def get_engagement_report(
    engagement_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Generate a complete engagement report package."""
    eng = _engagement_or_404(db, engagement_id, tenant_id)
    findings = db.query(AuditFinding).filter(
        AuditFinding.engagement_id == eng.id,
        AuditFinding.tenant_id == tenant_id,
    ).all()
    actions = db.query(AuditManagementAction).join(
        AuditFinding, AuditManagementAction.finding_id == AuditFinding.id
    ).filter(
        AuditFinding.engagement_id == eng.id,
        AuditManagementAction.tenant_id == tenant_id,
    ).all()

    severity_summary: Dict[str, int] = {}
    for f in findings:
        sev = f.severity.value if f.severity else "unknown"
        severity_summary[sev] = severity_summary.get(sev, 0) + 1

    return {
        "engagement": eng.to_dict(),
        "findings_count": len(findings),
        "severity_summary": severity_summary,
        "findings": [f.to_dict() for f in findings],
        "actions": [a.to_dict() for a in actions],
        "report_generated_at": datetime.utcnow().isoformat(),
    }


@router.get("/dashboard")
def get_audit_dashboard(
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Internal audit department dashboard."""
    total_entities = db.query(AuditableEntity).filter(
        AuditableEntity.tenant_id == tenant_id,
        AuditableEntity.is_active.is_(True),
    ).count()
    in_progress = db.query(AuditEngagement).filter(
        AuditEngagement.tenant_id == tenant_id,
        AuditEngagement.status.in_([
            EngagementStatus.ANNOUNCED,
            EngagementStatus.FIELDWORK,
            EngagementStatus.DRAFT_REPORT,
        ]),
    ).count()
    open_findings = db.query(AuditFinding).filter(
        AuditFinding.tenant_id == tenant_id,
        AuditFinding.status.notin_([FindingStatus.CLOSED]),
    ).count()
    overdue_actions = db.query(AuditManagementAction).filter(
        AuditManagementAction.tenant_id == tenant_id,
        AuditManagementAction.status == ActionStatus.OVERDUE,
    ).count()
    critical_findings = db.query(AuditFinding).filter(
        AuditFinding.tenant_id == tenant_id,
        AuditFinding.severity == FindingSeverity.CRITICAL,
        AuditFinding.status != FindingStatus.CLOSED,
    ).count()
    return {
        "total_auditable_entities": total_entities,
        "engagements_in_progress": in_progress,
        "open_findings": open_findings,
        "critical_open_findings": critical_findings,
        "overdue_actions": overdue_actions,
    }


@router.get("/committee-report")
def get_committee_report(
    fiscal_year: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Audit committee summary report for board-level presentation."""
    year = fiscal_year or datetime.utcnow().year
    plans = db.query(AuditPlan).filter(
        AuditPlan.tenant_id == tenant_id,
        AuditPlan.fiscal_year == year,
    ).all()
    engagements = db.query(AuditEngagement).filter(
        AuditEngagement.tenant_id == tenant_id,
    ).all()
    closed_engagements = [e for e in engagements if e.status == EngagementStatus.CLOSED]
    all_findings = db.query(AuditFinding).filter(
        AuditFinding.tenant_id == tenant_id,
    ).all()
    open_findings = [f for f in all_findings if f.status != FindingStatus.CLOSED]
    critical = [f for f in open_findings if f.severity == FindingSeverity.CRITICAL]
    high = [f for f in open_findings if f.severity == FindingSeverity.HIGH]

    overdue_actions = db.query(AuditManagementAction).filter(
        AuditManagementAction.tenant_id == tenant_id,
        AuditManagementAction.status == ActionStatus.OVERDUE,
    ).count()

    return {
        "fiscal_year": year,
        "audit_plans": len(plans),
        "total_engagements": len(engagements),
        "completed_engagements": len(closed_engagements),
        "completion_rate": round(len(closed_engagements) / len(engagements) * 100, 1) if engagements else 0,
        "open_findings": len(open_findings),
        "critical_findings": len(critical),
        "high_findings": len(high),
        "overdue_management_actions": overdue_actions,
        "generated_at": datetime.utcnow().isoformat(),
    }


# ===========================================================================
# Evidence Pull  (XL-D)
# ===========================================================================

@router.post("/engagements/{engagement_id}/pull-evidence", status_code=201)
def pull_evidence_for_engagement(
    engagement_id: str,
    body: Dict[str, Any] = Body(default={}),
    mgr=Depends(_get_manager),
):
    """
    XL-D: Pull a point-in-time immutable evidence snapshot from AC/PC/RM into an engagement.

    Supported sources:
      sod_violations      — RiskViolation records (filtered by rule_ids, from, to, user_ids)
      ccm_executions      — CCMExecution records (filtered by from, to, control_ids)
      firefighter_sessions — FirefighterSession records with embedded activities
      risk_baseline       — EnterpriseRisk records with latest assessment (filtered by risk_ids)

    The snapshot is serialised to canonical JSON, SHA-256 hashed for integrity, and
    stored as a GRCEvidence record (evidence_type='system_extract') linked to the engagement.
    """
    try:
        return mgr.pull_evidence(engagement_id, body)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/procedures/{procedure_id}/pull-evidence", status_code=201)
def pull_evidence_for_procedure(
    procedure_id: str,
    body: Dict[str, Any] = Body(default={}),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
    mgr=Depends(_get_manager),
):
    """XL-D: Pull a point-in-time immutable evidence snapshot and link it to a specific procedure."""
    from core.audit_management.evidence_pull import EvidencePullService
    proc = _procedure_or_404(db, procedure_id, tenant_id)
    source = body.get("source")
    if not source:
        raise HTTPException(status_code=400, detail="'source' is required")
    # Resolve engagement_id string from the procedure's FK
    engagement_id = body.get("engagement_id", "")
    if not engagement_id and proc.engagement_id:
        eng = db.query(AuditEngagement).filter(
            AuditEngagement.id == proc.engagement_id,
            AuditEngagement.tenant_id == tenant_id,
        ).first()
        if eng:
            engagement_id = eng.engagement_id
    try:
        service = EvidencePullService(tenant_id=tenant_id, db=db)
        return service.pull_evidence(
            engagement_id=engagement_id,
            source=source,
            filters=body.get("filters", {}),
            title=body.get("title"),
            pulled_by=body.get("pulled_by", "system"),
            procedure_id=procedure_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


# ===========================================================================
# Audit Opinion  (AM-SAP-GAP-09)
# ===========================================================================

@router.put("/engagements/{engagement_id}/opinion")
def set_audit_opinion(
    engagement_id: str,
    body: Dict[str, Any] = Body(default={}),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """
    Record the formal audit opinion on a completed engagement.

    Valid opinion values: unqualified | qualified | adverse | disclaimer |
    satisfactory | needs_improvement | unsatisfactory

    Body:
      opinion          : str (required)
      rationale        : str (required)
      opinion_date     : ISO date string (optional, defaults to now)
      opinion_issued_by: str (optional)
    """
    eng = _engagement_or_404(db, engagement_id, tenant_id)

    _VALID_OPINIONS = {
        "unqualified", "qualified", "adverse", "disclaimer",
        "satisfactory", "needs_improvement", "unsatisfactory",
    }
    opinion = body.get("opinion", "").lower()
    if not opinion:
        raise HTTPException(status_code=400, detail="opinion is required")
    if opinion not in _VALID_OPINIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid opinion '{opinion}'. Valid values: {sorted(_VALID_OPINIONS)}",
        )
    rationale = body.get("rationale")
    if not rationale:
        raise HTTPException(status_code=400, detail="rationale is required")

    # Store in engagement metadata-style JSON field; if the model has a
    # dedicated field it would be set here.  We persist via metadata_ convention.
    opinion_record = {
        "opinion": opinion,
        "rationale": rationale,
        "opinion_date": body.get("opinion_date") or datetime.utcnow().isoformat(),
        "issued_by": body.get("opinion_issued_by"),
        "recorded_at": datetime.utcnow().isoformat(),
    }

    # Persist as JSON on the engagement (stored in methodology field as
    # metadata extension, or dedicated DB column if present)
    if hasattr(eng, "audit_opinion"):
        eng.audit_opinion = opinion
        eng.audit_opinion_rationale = rationale
    else:
        # Fallback: embed in methodology JSON string
        existing_meta = {}
        try:
            import json
            if eng.methodology:
                existing_meta = json.loads(eng.methodology) if isinstance(eng.methodology, str) else {}
        except Exception:
            pass
        existing_meta["audit_opinion"] = opinion_record
        eng.methodology = existing_meta if not isinstance(existing_meta, str) else eng.methodology

    db.commit()
    db.refresh(eng)
    return {
        "engagement_id": engagement_id,
        "status": eng.status.value if eng.status else None,
        **opinion_record,
    }


# ===========================================================================
# Plan Roll-Forward  (AM-SAP-GAP-10)
# ===========================================================================

@router.post("/plans/{plan_id}/roll-forward")
def roll_forward_plan(
    plan_id: str,
    body: Dict[str, Any] = Body(default={}),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """
    Create a successor audit plan by rolling forward an existing plan.

    All engagements from the source plan that are NOT in a terminal status
    (closed) are carried forward to the new plan as PLANNED engagements.

    Body:
      new_fiscal_year  : int (required)
      new_plan_name    : str (optional, defaults to auto-generated name)
      prepared_by      : str (optional)
      carry_statuses   : list of statuses to carry forward
                         (default: all non-closed)
    """
    source = _plan_or_404(db, plan_id, tenant_id)

    new_year = body.get("new_fiscal_year")
    if not new_year:
        raise HTTPException(status_code=400, detail="new_fiscal_year is required")

    carry_statuses_raw = body.get("carry_statuses", [
        "planned", "announced", "fieldwork", "draft_report",
    ])
    carry_statuses = []
    for s in carry_statuses_raw:
        try:
            carry_statuses.append(EngagementStatus(s))
        except ValueError:
            pass

    # Create the new plan
    new_plan = AuditPlan(
        tenant_id=tenant_id,
        plan_id=_new_id("PLAN"),
        name=body.get("new_plan_name") or f"{source.name} (Roll-Forward {new_year})",
        description=f"Rolled forward from plan '{source.plan_id}' ({source.fiscal_year})",
        plan_type=source.plan_type,
        fiscal_year=int(new_year),
        total_audit_hours=source.total_audit_hours,
        allocated_budget=source.allocated_budget,
        status=AuditPlanStatus.DRAFT,
        prepared_by=body.get("prepared_by", source.prepared_by),
        risk_methodology=source.risk_methodology,
    )
    db.add(new_plan)
    db.flush()  # get new_plan.id

    # Pull unfinished engagements from source plan
    source_engs = db.query(AuditEngagement).filter(
        AuditEngagement.plan_id == source.id,
        AuditEngagement.tenant_id == tenant_id,
        AuditEngagement.status.in_(carry_statuses) if carry_statuses else True,
    ).all()

    carried_ids = []
    for eng in source_engs:
        new_eng = AuditEngagement(
            tenant_id=tenant_id,
            engagement_id=_new_id("ENG"),
            plan_id=new_plan.id,
            entity_id=eng.entity_id,
            title=eng.title,
            objective=eng.objective,
            scope=eng.scope,
            engagement_type=eng.engagement_type,
            status=EngagementStatus.PLANNED,
            lead_auditor_id=eng.lead_auditor_id,
            lead_auditor_name=eng.lead_auditor_name,
            team_members=eng.team_members,
            budget_hours=eng.budget_hours,
            risk_rating=eng.risk_rating,
            methodology=eng.methodology,
        )
        db.add(new_eng)
        carried_ids.append(new_eng.engagement_id)

    db.commit()
    db.refresh(new_plan)
    return {
        "source_plan_id": plan_id,
        "new_plan_id": new_plan.plan_id,
        "new_fiscal_year": new_year,
        "engagements_carried_forward": len(carried_ids),
        "carried_engagement_ids": carried_ids,
        "new_plan": new_plan.to_dict(),
    }


# ===========================================================================
# Audit Dimensions  (AM-SAP-GAP-11)
# ===========================================================================

@router.post("/dimensions", status_code=201)
def create_dimension(
    body: Dict[str, Any] = Body(default={}),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """
    Create a new multi-perspective audit dimension.

    Dimensions allow audit coverage to be viewed through multiple lenses
    simultaneously (e.g. by legal entity AND by IT system).

    Body:
      name, description, dimension_type (business_process | legal_entity |
      it_system | geography | regulation | product), hierarchy (optional JSON tree)
    """
    try:
        dim_type = DimensionType(body.get("dimension_type", "business_process"))
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid dimension_type")

    d = AuditDimension(
        tenant_id=tenant_id,
        dimension_id=body.get("dimension_id") or _new_id("DIM"),
        name=body["name"],
        description=body.get("description"),
        dimension_type=dim_type,
        hierarchy=body.get("hierarchy"),
        is_active=True,
    )
    db.add(d)
    db.commit()
    db.refresh(d)
    return d.to_dict()


@router.get("/dimensions")
def list_dimensions(
    dimension_type: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """List audit dimensions with optional type filter."""
    q = db.query(AuditDimension).filter(AuditDimension.tenant_id == tenant_id)
    if dimension_type:
        try:
            q = q.filter(AuditDimension.dimension_type == DimensionType(dimension_type))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid dimension_type")
    if is_active is not None:
        q = q.filter(AuditDimension.is_active == is_active)
    dims = q.order_by(AuditDimension.name.asc()).all()
    return {"total": len(dims), "dimensions": [d.to_dict() for d in dims]}


# ===========================================================================
# Audit Announcements  (AM-SAP-GAP-12)
# ===========================================================================

@router.post("/engagements/{engagement_id}/announce", status_code=201)
def create_announcement(
    engagement_id: str,
    body: Dict[str, Any] = Body(default={}),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """
    Create and immediately send a formal audit announcement to auditees.

    Body:
      subject       : str (required)
      body          : str (required) — announcement message content
      recipients    : list of {id, name, email}
      sent_by       : str — announcing auditor user_id
      send_now      : bool (default true) — if true, marks status=SENT and
                      sets sent_at; if false, creates as DRAFT
    """
    eng = _engagement_or_404(db, engagement_id, tenant_id)

    if not body.get("subject"):
        raise HTTPException(status_code=400, detail="subject is required")
    if not body.get("body"):
        raise HTTPException(status_code=400, detail="body is required")

    send_now = body.get("send_now", True)
    ann = AuditAnnouncement(
        tenant_id=tenant_id,
        announcement_id=_new_id("ANN"),
        engagement_id=eng.id,
        recipients=body.get("recipients", []),
        subject=body["subject"],
        body=body["body"],
        sent_by=body.get("sent_by"),
        sent_at=datetime.utcnow() if send_now else None,
        acknowledgments=[],
        status=AnnouncementStatus.SENT if send_now else AnnouncementStatus.DRAFT,
    )
    db.add(ann)

    # Advance engagement to ANNOUNCED status if still PLANNED
    if send_now and eng.status == EngagementStatus.PLANNED:
        eng.status = EngagementStatus.ANNOUNCED

    db.commit()
    db.refresh(ann)
    return ann.to_dict()


@router.get("/engagements/{engagement_id}/announcements")
def list_announcements(
    engagement_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """List all announcements for an engagement."""
    eng = _engagement_or_404(db, engagement_id, tenant_id)
    anns = db.query(AuditAnnouncement).filter(
        AuditAnnouncement.engagement_id == eng.id,
        AuditAnnouncement.tenant_id == tenant_id,
    ).order_by(AuditAnnouncement.created_at.desc()).all()
    return {"total": len(anns), "announcements": [a.to_dict() for a in anns]}
