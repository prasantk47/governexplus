"""
GDPR / Privacy Management API Router

Covers Article 30 processing inventory, DSAR, DPIA, data breach notification:
  - Data Processing Activities (RoPA)
  - Data Subject Access Requests (30-day deadline)
  - Data Protection Impact Assessments
  - Data Breach Incidents (72h regulator notification rule)
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import uuid

from db.database import get_db
from db.models.privacy import (
    DataProcessingActivity, DSARRequest, DPIAAssessment, DataBreachIncident,
)

router = APIRouter(tags=["Privacy / GDPR"])


def _get_tenant_id() -> str:
    from core.tenant import get_current_tenant
    ctx = get_current_tenant()
    return ctx.tenant_id if ctx else "default"


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


# ===========================================================================
# Data Processing Activities (Article 30 RoPA)
# ===========================================================================

@router.get("/processing-activities")
def list_processing_activities(
    legal_basis: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    transfers_outside_eea: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    q = db.query(DataProcessingActivity).filter(
        DataProcessingActivity.tenant_id == tenant_id,
        DataProcessingActivity.is_active.is_(True),
    )
    if legal_basis:
        q = q.filter(DataProcessingActivity.legal_basis == legal_basis)
    if status:
        q = q.filter(DataProcessingActivity.status == status)
    if transfers_outside_eea is not None:
        q = q.filter(DataProcessingActivity.transfers_outside_eea == transfers_outside_eea)
    activities = q.order_by(DataProcessingActivity.name).all()
    return {"activities": [a.to_dict() for a in activities], "total": len(activities)}


@router.post("/processing-activities", status_code=201)
def create_processing_activity(
    body: Dict[str, Any] = Body(default={}),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    a = DataProcessingActivity(
        activity_id=_new_id("DPA"),
        tenant_id=tenant_id,
        name=body["name"],
        description=body.get("description"),
        purpose=body["purpose"],
        legal_basis=body.get("legal_basis"),
        legitimate_interest_assessment=body.get("legitimate_interest_assessment"),
        personal_data_categories=body.get("personal_data_categories"),
        special_categories=body.get("special_categories"),
        data_subjects=body.get("data_subjects"),
        controller_name=body.get("controller_name"),
        processor_name=body.get("processor_name"),
        third_party_recipients=body.get("third_party_recipients"),
        transfers_outside_eea=bool(body.get("transfers_outside_eea", False)),
        transfer_safeguards=body.get("transfer_safeguards"),
        retention_period=body.get("retention_period"),
        retention_justification=body.get("retention_justification"),
        security_measures=body.get("security_measures"),
        dpia_required=bool(body.get("dpia_required", False)),
        business_owner=body.get("business_owner"),
        system_name=body.get("system_name"),
        status=body.get("status", "active"),
    )
    db.add(a)
    db.commit()
    db.refresh(a)
    return a.to_dict()


@router.put("/processing-activities/{activity_id}")
def update_processing_activity(
    activity_id: str,
    body: Dict[str, Any] = Body(default={}),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    a = db.query(DataProcessingActivity).filter(
        DataProcessingActivity.activity_id == activity_id,
        DataProcessingActivity.tenant_id == tenant_id,
    ).first()
    if not a:
        raise HTTPException(status_code=404, detail="Processing activity not found")
    updatable = [
        "name", "description", "purpose", "legal_basis", "personal_data_categories",
        "special_categories", "data_subjects", "controller_name", "processor_name",
        "third_party_recipients", "transfers_outside_eea", "transfer_safeguards",
        "retention_period", "retention_justification", "security_measures",
        "dpia_required", "business_owner", "system_name", "status",
    ]
    for k in updatable:
        if k in body:
            setattr(a, k, body[k])
    db.commit()
    db.refresh(a)
    return a.to_dict()


# ===========================================================================
# DSAR (Data Subject Access Requests)
# ===========================================================================

@router.get("/dsar")
def list_dsar(
    status: Optional[str] = Query(None),
    request_type: Optional[str] = Query(None),
    overdue_only: bool = Query(False),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    q = db.query(DSARRequest).filter(
        DSARRequest.tenant_id == tenant_id,
        DSARRequest.is_active.is_(True),
    )
    if status:
        q = q.filter(DSARRequest.status == status)
    if request_type:
        q = q.filter(DSARRequest.request_type == request_type)
    requests = q.order_by(DSARRequest.received_at.desc()).all()
    result = [r.to_dict() for r in requests]
    if overdue_only:
        now = datetime.utcnow()
        result = [r for r in result if r.get("deadline") and datetime.fromisoformat(r["deadline"]) < now and r["status"] not in ("completed", "rejected")]
    return {"requests": result, "total": len(result)}


@router.post("/dsar", status_code=201)
def create_dsar(
    body: Dict[str, Any] = Body(default={}),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    received = datetime.utcnow()
    # GDPR Article 12: 30 days from receipt
    deadline = received + timedelta(days=30)
    r = DSARRequest(
        dsar_id=_new_id("DSAR"),
        tenant_id=tenant_id,
        request_type=body.get("request_type", "access"),
        subject_name=body["subject_name"],
        subject_email=body["subject_email"],
        subject_id_verified=bool(body.get("subject_id_verified", False)),
        verification_method=body.get("verification_method"),
        description=body.get("description"),
        received_at=received,
        deadline=deadline,
        assigned_to=body.get("assigned_to"),
        status="received",
    )
    db.add(r)
    db.commit()
    db.refresh(r)
    return r.to_dict()


@router.put("/dsar/{dsar_id}/status")
def update_dsar_status(
    dsar_id: str,
    body: Dict[str, Any] = Body(default={}),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    r = db.query(DSARRequest).filter(
        DSARRequest.dsar_id == dsar_id,
        DSARRequest.tenant_id == tenant_id,
    ).first()
    if not r:
        raise HTTPException(status_code=404, detail="DSAR not found")
    new_status = body.get("status")
    allowed = {"received", "verified", "in_progress", "completed", "rejected", "extended"}
    if new_status not in allowed:
        raise HTTPException(status_code=422, detail=f"Invalid status. Must be one of: {allowed}")
    r.status = new_status
    if new_status == "completed":
        r.completed_at = datetime.utcnow()
        r.completed_by = body.get("completed_by")
        r.response_summary = body.get("response_summary")
    if new_status == "rejected":
        r.rejection_reason = body.get("rejection_reason")
    if new_status == "extended":
        # GDPR allows 2-month extension for complex requests
        r.extended_deadline = r.deadline + timedelta(days=60) if r.deadline else None
    if "assigned_to" in body:
        r.assigned_to = body["assigned_to"]
    db.commit()
    db.refresh(r)
    return r.to_dict()


# ===========================================================================
# DPIA (Data Protection Impact Assessment)
# ===========================================================================

@router.get("/dpia")
def list_dpia(
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    q = db.query(DPIAAssessment).filter(
        DPIAAssessment.tenant_id == tenant_id,
        DPIAAssessment.is_active.is_(True),
    )
    if status:
        q = q.filter(DPIAAssessment.status == status)
    assessments = q.order_by(DPIAAssessment.created_at.desc()).all()
    return {"assessments": [a.to_dict() for a in assessments], "total": len(assessments)}


@router.post("/dpia", status_code=201)
def create_dpia(
    body: Dict[str, Any] = Body(default={}),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    a = DPIAAssessment(
        dpia_id=_new_id("DPIA"),
        tenant_id=tenant_id,
        title=body["title"],
        description=body.get("description"),
        processing_activity_id=body.get("processing_activity_id"),
        project_name=body.get("project_name"),
        conducted_by=body.get("conducted_by"),
        status="draft",
    )
    db.add(a)
    db.commit()
    db.refresh(a)
    return a.to_dict()


@router.put("/dpia/{dpia_id}")
def update_dpia(
    dpia_id: str,
    body: Dict[str, Any] = Body(default={}),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    a = db.query(DPIAAssessment).filter(
        DPIAAssessment.dpia_id == dpia_id,
        DPIAAssessment.tenant_id == tenant_id,
    ).first()
    if not a:
        raise HTTPException(status_code=404, detail="DPIA not found")
    updatable = [
        "title", "description", "necessity_assessment", "proportionality_assessment",
        "risk_assessment", "risk_measures", "dpo_consulted", "dpo_opinion",
        "regulator_consulted", "regulator_response", "overall_risk_level",
        "conclusion", "conclusion_notes", "conducted_by", "approved_by", "status",
    ]
    for k in updatable:
        if k in body:
            setattr(a, k, body[k])
    if body.get("dpo_consulted"):
        a.dpo_consulted_at = datetime.utcnow()
    if body.get("status") == "approved" and not a.approved_at:
        a.approved_at = datetime.utcnow()
    db.commit()
    db.refresh(a)
    return a.to_dict()


# ===========================================================================
# Data Breach Incidents
# ===========================================================================

@router.get("/breaches")
def list_breaches(
    status: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    q = db.query(DataBreachIncident).filter(
        DataBreachIncident.tenant_id == tenant_id,
        DataBreachIncident.is_active.is_(True),
    )
    if status:
        q = q.filter(DataBreachIncident.status == status)
    if severity:
        q = q.filter(DataBreachIncident.severity == severity)
    breaches = q.order_by(DataBreachIncident.detected_at.desc()).all()
    return {"breaches": [b.to_dict() for b in breaches], "total": len(breaches)}


@router.post("/breaches", status_code=201)
def create_breach(
    body: Dict[str, Any] = Body(default={}),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    detected = datetime.utcnow()
    # GDPR Article 33: 72h notification to regulator for reportable breaches
    regulator_deadline = detected + timedelta(hours=72)
    b = DataBreachIncident(
        breach_id=_new_id("BREACH"),
        tenant_id=tenant_id,
        title=body["title"],
        description=body["description"],
        severity=body.get("severity", "medium"),
        detected_at=detected,
        occurred_at=datetime.fromisoformat(body["occurred_at"]) if body.get("occurred_at") else None,
        breach_type=body.get("breach_type"),
        data_categories_affected=body.get("data_categories_affected"),
        subjects_affected_count=body.get("subjects_affected_count"),
        systems_affected=body.get("systems_affected"),
        regulator_notification_required=bool(body.get("regulator_notification_required", False)),
        regulator_deadline=regulator_deadline,
        subjects_notification_required=bool(body.get("subjects_notification_required", False)),
        lead_investigator=body.get("lead_investigator"),
        status="detected",
    )
    db.add(b)
    db.commit()
    db.refresh(b)
    return b.to_dict()


@router.put("/breaches/{breach_id}/status")
def update_breach_status(
    breach_id: str,
    body: Dict[str, Any] = Body(default={}),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    b = db.query(DataBreachIncident).filter(
        DataBreachIncident.breach_id == breach_id,
        DataBreachIncident.tenant_id == tenant_id,
    ).first()
    if not b:
        raise HTTPException(status_code=404, detail="Breach not found")
    new_status = body.get("status")
    b.status = new_status
    now = datetime.utcnow()
    if new_status == "contained":
        b.contained_at = now
    if new_status == "notified_regulator":
        b.regulator_notified_at = now
        b.regulator_reference = body.get("regulator_reference")
    if new_status == "notified_subjects":
        b.subjects_notified_at = now
    if "root_cause" in body:
        b.root_cause = body["root_cause"]
    if "remediation_actions" in body:
        b.remediation_actions = body["remediation_actions"]
    if "lessons_learned" in body:
        b.lessons_learned = body["lessons_learned"]
    db.commit()
    db.refresh(b)
    return b.to_dict()


@router.get("/dashboard")
def privacy_dashboard(
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    activities = db.query(DataProcessingActivity).filter(
        DataProcessingActivity.tenant_id == tenant_id,
        DataProcessingActivity.is_active.is_(True),
    ).all()
    dsars = db.query(DSARRequest).filter(
        DSARRequest.tenant_id == tenant_id,
        DSARRequest.is_active.is_(True),
    ).all()
    dpias = db.query(DPIAAssessment).filter(
        DPIAAssessment.tenant_id == tenant_id,
        DPIAAssessment.is_active.is_(True),
    ).all()
    breaches = db.query(DataBreachIncident).filter(
        DataBreachIncident.tenant_id == tenant_id,
        DataBreachIncident.is_active.is_(True),
    ).all()

    now = datetime.utcnow()
    overdue_dsars = [r for r in dsars if r.deadline and r.deadline < now and r.status not in ("completed", "rejected")]
    open_breaches = [b for b in breaches if b.status not in ("closed",)]
    unnotified = [b for b in breaches if b.regulator_notification_required and not b.regulator_notified_at]

    return {
        "processing_activities": len(activities),
        "eea_transfers": sum(1 for a in activities if a.transfers_outside_eea),
        "dpia_required": sum(1 for a in activities if a.dpia_required),
        "open_dsars": sum(1 for r in dsars if r.status not in ("completed", "rejected")),
        "overdue_dsars": len(overdue_dsars),
        "open_dpias": sum(1 for d in dpias if d.status not in ("approved", "rejected")),
        "open_breaches": len(open_breaches),
        "unnotified_regulator": len(unnotified),
    }
