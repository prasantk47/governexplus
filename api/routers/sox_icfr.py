"""
SOX / ICFR API Router

Internal Controls over Financial Reporting (SOX 302/404):
  - ICFR control matrix with financial statement assertions
  - Design and operating effectiveness assessment
  - Deficiency classification (deficiency/significant_deficiency/material_weakness)
  - CEO/CFO/controller management sign-off
  - Financial close checklist management
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from typing import Dict, List, Optional, Any
from datetime import datetime
from sqlalchemy.orm import Session
import uuid

from db.database import get_db
from db.models.sox_icfr import ICFRControl, SOXSignoff, FinancialCloseTask

router = APIRouter(tags=["SOX / ICFR"])


def _get_tenant_id() -> str:
    from core.tenant import get_current_tenant
    ctx = get_current_tenant()
    return ctx.tenant_id if ctx else "default"


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def _control_or_404(db: Session, control_id: str, tenant_id: str) -> ICFRControl:
    c = db.query(ICFRControl).filter(
        ICFRControl.control_id == control_id,
        ICFRControl.tenant_id == tenant_id,
        ICFRControl.is_active.is_(True),
    ).first()
    if not c:
        raise HTTPException(status_code=404, detail=f"ICFR control '{control_id}' not found")
    return c


# ===========================================================================
# ICFR Controls
# ===========================================================================

@router.get("/controls")
def list_controls(
    sox_section: Optional[str] = Query(None),
    effectiveness: Optional[str] = Query(None),
    is_key_control: Optional[bool] = Query(None),
    process_name: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    q = db.query(ICFRControl).filter(
        ICFRControl.tenant_id == tenant_id,
        ICFRControl.is_active.is_(True),
    )
    if sox_section:
        q = q.filter(ICFRControl.sox_section == sox_section)
    if effectiveness:
        q = q.filter(ICFRControl.overall_effectiveness == effectiveness)
    if is_key_control is not None:
        q = q.filter(ICFRControl.is_key_control == is_key_control)
    if process_name:
        q = q.filter(ICFRControl.process_name.ilike(f"%{process_name}%"))
    controls = q.order_by(ICFRControl.financial_statement_area, ICFRControl.control_id).all()
    return {"controls": [c.to_dict() for c in controls], "total": len(controls)}


@router.post("/controls", status_code=201)
def create_control(
    body: Dict[str, Any] = Body(default={}),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    c = ICFRControl(
        control_id=body.get("control_id") or _new_id("ICFR"),
        tenant_id=tenant_id,
        title=body["title"],
        description=body.get("description"),
        control_type=body.get("control_type", "process_level"),
        frequency=body.get("frequency", "monthly"),
        financial_statement_area=body.get("financial_statement_area"),
        assertions=body.get("assertions"),
        account_codes=body.get("account_codes"),
        process_name=body.get("process_name"),
        sub_process=body.get("sub_process"),
        control_owner=body.get("control_owner"),
        control_performer=body.get("control_performer"),
        reviewer=body.get("reviewer"),
        overall_effectiveness=body.get("overall_effectiveness", "not_tested"),
        sox_section=body.get("sox_section", "404"),
        is_key_control=bool(body.get("is_key_control", False)),
        is_automated=bool(body.get("is_automated", False)),
        evidence_requirements=body.get("evidence_requirements"),
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return c.to_dict()


@router.get("/controls/{control_id}")
def get_control(
    control_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    return _control_or_404(db, control_id, tenant_id).to_dict()


@router.put("/controls/{control_id}")
def update_control(
    control_id: str,
    body: Dict[str, Any] = Body(default={}),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    c = _control_or_404(db, control_id, tenant_id)
    updatable = [
        "title", "description", "control_type", "frequency",
        "financial_statement_area", "assertions", "account_codes",
        "process_name", "sub_process", "control_owner", "control_performer",
        "reviewer", "design_effectiveness", "operating_effectiveness",
        "overall_effectiveness", "deficiency_type", "deficiency_description",
        "remediation_plan", "remediation_status", "sox_section",
        "is_key_control", "is_automated", "evidence_requirements", "evidence_links",
    ]
    for k in updatable:
        if k in body:
            setattr(c, k, body[k])
    if "remediation_due_date" in body and body["remediation_due_date"]:
        c.remediation_due_date = datetime.fromisoformat(body["remediation_due_date"])
    db.commit()
    db.refresh(c)
    return c.to_dict()


@router.post("/controls/{control_id}/test")
def record_test(
    control_id: str,
    body: Dict[str, Any] = Body(default={}),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    c = _control_or_404(db, control_id, tenant_id)
    c.last_tested_at = datetime.utcnow()
    c.last_tested_by = body.get("tested_by", "system")
    if "design_effectiveness" in body:
        c.design_effectiveness = body["design_effectiveness"]
    if "operating_effectiveness" in body:
        c.operating_effectiveness = body["operating_effectiveness"]
    if "overall_effectiveness" in body:
        c.overall_effectiveness = body["overall_effectiveness"]
    # Auto-classify deficiency
    eff = c.overall_effectiveness
    if eff == "material_weakness":
        c.deficiency_type = "material_weakness"
    elif eff == "significant_deficiency":
        c.deficiency_type = "significant_deficiency"
    elif eff == "deficiency":
        c.deficiency_type = "deficiency"
    if "next_test_date" in body and body["next_test_date"]:
        c.next_test_date = datetime.fromisoformat(body["next_test_date"])
    if "deficiency_description" in body:
        c.deficiency_description = body["deficiency_description"]
    db.commit()
    db.refresh(c)
    return c.to_dict()


@router.get("/summary")
def icfr_summary(
    sox_section: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    q = db.query(ICFRControl).filter(
        ICFRControl.tenant_id == tenant_id,
        ICFRControl.is_active.is_(True),
    )
    if sox_section:
        q = q.filter(ICFRControl.sox_section == sox_section)
    controls = q.all()

    total = len(controls)
    key_controls = [c for c in controls if c.is_key_control]
    effective = [c for c in key_controls if c.overall_effectiveness == "effective"]
    deficiencies = [c for c in controls if c.deficiency_type == "deficiency"]
    sig_defs = [c for c in controls if c.deficiency_type == "significant_deficiency"]
    mat_wks = [c for c in controls if c.deficiency_type == "material_weakness"]
    not_tested = [c for c in controls if c.overall_effectiveness == "not_tested"]

    return {
        "total_controls": total,
        "key_controls": len(key_controls),
        "effective_key_controls": len(effective),
        "deficiencies": len(deficiencies),
        "significant_deficiencies": len(sig_defs),
        "material_weaknesses": len(mat_wks),
        "not_tested": len(not_tested),
        "effectiveness_rate": round(len(effective) / len(key_controls) * 100, 1) if key_controls else 0,
    }


# ===========================================================================
# SOX Sign-offs
# ===========================================================================

@router.get("/signoffs")
def list_signoffs(
    period: Optional[str] = Query(None),
    sox_section: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    q = db.query(SOXSignoff).filter(
        SOXSignoff.tenant_id == tenant_id,
        SOXSignoff.is_active.is_(True),
    )
    if period:
        q = q.filter(SOXSignoff.period == period)
    if sox_section:
        q = q.filter(SOXSignoff.sox_section == sox_section)
    if status:
        q = q.filter(SOXSignoff.status == status)
    signoffs = q.order_by(SOXSignoff.created_at.desc()).all()
    return {"signoffs": [s.to_dict() for s in signoffs], "total": len(signoffs)}


@router.post("/signoffs", status_code=201)
def create_signoff(
    body: Dict[str, Any] = Body(default={}),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    # Auto-populate summary from ICFR controls
    q = db.query(ICFRControl).filter(
        ICFRControl.tenant_id == tenant_id,
        ICFRControl.is_active.is_(True),
        ICFRControl.is_key_control.is_(True),
    )
    if body.get("sox_section"):
        q = q.filter(ICFRControl.sox_section == body["sox_section"])
    controls = q.all()

    s = SOXSignoff(
        signoff_id=_new_id("SOXSIGN"),
        tenant_id=tenant_id,
        period=body["period"],
        sox_section=body.get("sox_section", "404"),
        signoff_type=body.get("signoff_type", "cfo"),
        signer_name=body["signer_name"],
        signer_title=body.get("signer_title"),
        signer_email=body.get("signer_email"),
        status="pending",
        total_key_controls=len(controls),
        effective_controls=sum(1 for c in controls if c.overall_effectiveness == "effective"),
        deficiencies=sum(1 for c in controls if c.deficiency_type == "deficiency"),
        significant_deficiencies=sum(1 for c in controls if c.deficiency_type == "significant_deficiency"),
        material_weaknesses=sum(1 for c in controls if c.deficiency_type == "material_weakness"),
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    return s.to_dict()


@router.post("/signoffs/{signoff_id}/sign")
def sign_signoff(
    signoff_id: str,
    body: Dict[str, Any] = Body(default={}),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    s = db.query(SOXSignoff).filter(
        SOXSignoff.signoff_id == signoff_id,
        SOXSignoff.tenant_id == tenant_id,
    ).first()
    if not s:
        raise HTTPException(status_code=404, detail="Sign-off not found")
    if s.status == "signed":
        raise HTTPException(status_code=409, detail="Already signed")
    s.status = "signed"
    s.signed_at = datetime.utcnow()
    s.conclusion = body.get("conclusion", "effective")
    s.conclusion_notes = body.get("conclusion_notes")
    s.exceptions_noted = body.get("exceptions_noted")
    db.commit()
    db.refresh(s)
    return s.to_dict()


# ===========================================================================
# Financial Close Tasks
# ===========================================================================

@router.get("/close-tasks")
def list_close_tasks(
    period: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    assigned_to: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    q = db.query(FinancialCloseTask).filter(
        FinancialCloseTask.tenant_id == tenant_id,
        FinancialCloseTask.is_active.is_(True),
    )
    if period:
        q = q.filter(FinancialCloseTask.period == period)
    if status:
        q = q.filter(FinancialCloseTask.status == status)
    if assigned_to:
        q = q.filter(FinancialCloseTask.assigned_to == assigned_to)
    tasks = q.order_by(FinancialCloseTask.sequence_order, FinancialCloseTask.due_date).all()
    return {"tasks": [t.to_dict() for t in tasks], "total": len(tasks)}


@router.post("/close-tasks", status_code=201)
def create_close_task(
    body: Dict[str, Any] = Body(default={}),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    t = FinancialCloseTask(
        task_id=_new_id("CLTASK"),
        tenant_id=tenant_id,
        period=body["period"],
        title=body["title"],
        description=body.get("description"),
        task_type=body.get("task_type"),
        sequence_order=body.get("sequence_order"),
        assigned_to=body.get("assigned_to"),
        due_date=datetime.fromisoformat(body["due_date"]) if body.get("due_date") else None,
        status="open",
        is_critical_path=bool(body.get("is_critical_path", False)),
        linked_control_id=body.get("linked_control_id"),
        notes=body.get("notes"),
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    return t.to_dict()


@router.put("/close-tasks/{task_id}/complete")
def complete_close_task(
    task_id: str,
    body: Dict[str, Any] = Body(default={}),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    t = db.query(FinancialCloseTask).filter(
        FinancialCloseTask.task_id == task_id,
        FinancialCloseTask.tenant_id == tenant_id,
    ).first()
    if not t:
        raise HTTPException(status_code=404, detail="Task not found")
    t.status = "completed"
    t.completed_at = datetime.utcnow()
    t.completed_by = body.get("completed_by", "system")
    if "notes" in body:
        t.notes = body["notes"]
    db.commit()
    db.refresh(t)
    return t.to_dict()
