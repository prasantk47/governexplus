"""
GAP-4: Obligation Management Router
"""
import uuid
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from db.database import get_db
from db.models.obligation_management import Obligation, ObligationAssessment

router = APIRouter()


@router.get("/")
def list_obligations(
    status: str = None,
    category: str = None,
    compliance_status: str = None,
    db: Session = Depends(get_db),
):
    q = db.query(Obligation)
    if status:
        q = q.filter(Obligation.status == status)
    if category:
        q = q.filter(Obligation.category == category)
    if compliance_status:
        q = q.filter(Obligation.compliance_status == compliance_status)
    return [r.to_dict() for r in q.order_by(Obligation.created_at.desc()).limit(200).all()]


@router.post("/")
def create_obligation(body: dict, db: Session = Depends(get_db)):
    review_days = body.get("review_frequency_days", 365)
    rec = Obligation(
        id=str(uuid.uuid4()),
        tenant_id=body.get("tenant_id", "default"),
        obligation_id=body.get("obligation_id", f"OBL-{uuid.uuid4().hex[:8].upper()}"),
        title=body["title"],
        description=body.get("description"),
        regulation_id=body.get("regulation_id"),
        regulation_name=body.get("regulation_name"),
        section_reference=body.get("section_reference"),
        jurisdiction=body.get("jurisdiction"),
        effective_date=body.get("effective_date"),
        category=body.get("category"),
        obligation_type=body.get("obligation_type", "mandatory"),
        applicability=body.get("applicability"),
        applicable_entities=body.get("applicable_entities"),
        owner=body.get("owner"),
        responsible_team=body.get("responsible_team"),
        linked_policy_ids=body.get("linked_policy_ids"),
        linked_control_ids=body.get("linked_control_ids"),
        linked_control_objective_ids=body.get("linked_control_objective_ids"),
        linked_risk_ids=body.get("linked_risk_ids"),
        compliance_status="not_assessed",
        status="active",
        review_frequency_days=review_days,
        next_review_date=datetime.utcnow() + timedelta(days=review_days),
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)
    return rec.to_dict()


@router.get("/{obligation_id}")
def get_obligation(obligation_id: str, db: Session = Depends(get_db)):
    rec = db.query(Obligation).filter(
        (Obligation.id == obligation_id) | (Obligation.obligation_id == obligation_id)
    ).first()
    if not rec:
        raise HTTPException(404, "Obligation not found")
    return rec.to_dict()


@router.put("/{obligation_id}")
def update_obligation(obligation_id: str, body: dict, db: Session = Depends(get_db)):
    rec = db.query(Obligation).filter(
        (Obligation.id == obligation_id) | (Obligation.obligation_id == obligation_id)
    ).first()
    if not rec:
        raise HTTPException(404, "Obligation not found")
    for k, v in body.items():
        if hasattr(rec, k) and k not in ("id", "tenant_id", "obligation_id"):
            setattr(rec, k, v)
    db.commit()
    db.refresh(rec)
    return rec.to_dict()


@router.post("/{obligation_id}/assess")
def assess_obligation(obligation_id: str, body: dict, db: Session = Depends(get_db)):
    obl = db.query(Obligation).filter(
        (Obligation.id == obligation_id) | (Obligation.obligation_id == obligation_id)
    ).first()
    if not obl:
        raise HTTPException(404, "Obligation not found")
    assessment = ObligationAssessment(
        id=str(uuid.uuid4()),
        tenant_id=obl.tenant_id,
        obligation_id=obl.id,
        assessment_period=body.get("assessment_period", "Q4-2026"),
        assessor=body.get("assessor", "system"),
        compliance_rating=body["compliance_rating"],
        evidence_summary=body.get("evidence_summary"),
        gaps_identified=body.get("gaps_identified"),
        exceptions=body.get("exceptions"),
        remediation_actions=body.get("remediation_actions"),
    )
    db.add(assessment)
    obl.compliance_status = body["compliance_rating"]
    obl.last_assessed_date = datetime.utcnow()
    obl.last_assessed_by = body.get("assessor", "system")
    if body.get("gap_description"):
        obl.gap_description = body["gap_description"]
    db.commit()
    db.refresh(assessment)
    return assessment.to_dict()


@router.get("/{obligation_id}/assessments")
def list_assessments(obligation_id: str, db: Session = Depends(get_db)):
    return [r.to_dict() for r in db.query(ObligationAssessment).filter(
        ObligationAssessment.obligation_id == obligation_id
    ).order_by(ObligationAssessment.created_at.desc()).all()]


@router.get("/summary/stats")
def obligation_summary(db: Session = Depends(get_db)):
    from sqlalchemy import func
    by_status = db.query(Obligation.compliance_status, func.count()).group_by(Obligation.compliance_status).all()
    by_cat = db.query(Obligation.category, func.count()).group_by(Obligation.category).all()
    overdue = db.query(func.count()).filter(
        Obligation.next_review_date < datetime.utcnow(),
        Obligation.status == "active",
    ).scalar()
    return {
        "by_compliance_status": {s: c for s, c in by_status},
        "by_category": {cat: c for cat, c in by_cat},
        "overdue_reviews": overdue,
        "total": sum(c for _, c in by_status),
    }
