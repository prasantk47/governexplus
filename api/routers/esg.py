"""
GAP-7: ESG Module Router
"""
import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from db.database import get_db
from db.models.esg import ESGCommitment, ESGMetric, ESGDisclosure

router = APIRouter()


# ── Commitments ───────────────────────────────────────────────────────────────

@router.get("/commitments")
def list_commitments(pillar: str = None, status: str = None, db: Session = Depends(get_db)):
    q = db.query(ESGCommitment)
    if pillar:
        q = q.filter(ESGCommitment.pillar == pillar)
    if status:
        q = q.filter(ESGCommitment.status == status)
    return [r.to_dict() for r in q.order_by(ESGCommitment.created_at.desc()).limit(200).all()]


@router.post("/commitments")
def create_commitment(body: dict, db: Session = Depends(get_db)):
    rec = ESGCommitment(
        id=str(uuid.uuid4()),
        tenant_id=body.get("tenant_id", "default"),
        commitment_id=body.get("commitment_id", f"ESG-{uuid.uuid4().hex[:8].upper()}"),
        title=body["title"],
        description=body.get("description"),
        pillar=body["pillar"],
        category=body.get("category"),
        framework=body.get("framework"),
        framework_reference=body.get("framework_reference"),
        target_description=body.get("target_description"),
        target_value=body.get("target_value"),
        target_unit=body.get("target_unit"),
        target_date=body.get("target_date"),
        baseline_value=body.get("baseline_value"),
        baseline_date=body.get("baseline_date"),
        current_value=body.get("current_value"),
        owner=body.get("owner"),
        responsible_team=body.get("responsible_team"),
        linked_risk_ids=body.get("linked_risk_ids"),
        linked_control_ids=body.get("linked_control_ids"),
        linked_obligation_ids=body.get("linked_obligation_ids"),
        status=body.get("status", "active"),
        review_frequency_days=body.get("review_frequency_days", 90),
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)
    return rec.to_dict()


@router.get("/commitments/{commitment_id}")
def get_commitment(commitment_id: str, db: Session = Depends(get_db)):
    rec = db.query(ESGCommitment).filter(
        (ESGCommitment.id == commitment_id) | (ESGCommitment.commitment_id == commitment_id)
    ).first()
    if not rec:
        raise HTTPException(404, "Commitment not found")
    return rec.to_dict()


@router.put("/commitments/{commitment_id}")
def update_commitment(commitment_id: str, body: dict, db: Session = Depends(get_db)):
    rec = db.query(ESGCommitment).filter(
        (ESGCommitment.id == commitment_id) | (ESGCommitment.commitment_id == commitment_id)
    ).first()
    if not rec:
        raise HTTPException(404, "Commitment not found")
    for k, v in body.items():
        if hasattr(rec, k) and k not in ("id", "tenant_id", "commitment_id"):
            setattr(rec, k, v)
    if rec.target_value and rec.current_value and rec.target_value > 0:
        rec.progress_pct = round(rec.current_value / rec.target_value * 100, 1)
    db.commit()
    db.refresh(rec)
    return rec.to_dict()


# ── Metrics ───────────────────────────────────────────────────────────────────

@router.get("/metrics")
def list_metrics(pillar: str = None, commitment_id: str = None, db: Session = Depends(get_db)):
    q = db.query(ESGMetric)
    if pillar:
        q = q.filter(ESGMetric.pillar == pillar)
    if commitment_id:
        q = q.filter(ESGMetric.commitment_id == commitment_id)
    return [r.to_dict() for r in q.order_by(ESGMetric.reporting_date.desc()).limit(200).all()]


@router.post("/metrics")
def record_metric(body: dict, db: Session = Depends(get_db)):
    rec = ESGMetric(
        id=str(uuid.uuid4()),
        tenant_id=body.get("tenant_id", "default"),
        metric_id=body.get("metric_id", f"MET-{uuid.uuid4().hex[:8].upper()}"),
        commitment_id=body.get("commitment_id"),
        name=body["name"],
        description=body.get("description"),
        pillar=body["pillar"],
        category=body.get("category"),
        unit=body.get("unit"),
        value=body["value"],
        period=body.get("period"),
        reporting_date=datetime.utcnow(),
        data_source=body.get("data_source"),
        verified=body.get("verified", False),
        evidence_ids=body.get("evidence_ids"),
        methodology_notes=body.get("methodology_notes"),
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)
    return rec.to_dict()


@router.put("/metrics/{metric_id}/verify")
def verify_metric(metric_id: str, body: dict, db: Session = Depends(get_db)):
    rec = db.query(ESGMetric).filter(
        (ESGMetric.id == metric_id) | (ESGMetric.metric_id == metric_id)
    ).first()
    if not rec:
        raise HTTPException(404, "Metric not found")
    rec.verified = True
    rec.verified_by = body.get("verified_by", "system")
    rec.verified_at = datetime.utcnow()
    db.commit()
    db.refresh(rec)
    return rec.to_dict()


# ── Disclosures ───────────────────────────────────────────────────────────────

@router.get("/disclosures")
def list_disclosures(db: Session = Depends(get_db)):
    return [r.to_dict() for r in db.query(ESGDisclosure).order_by(ESGDisclosure.created_at.desc()).limit(50).all()]


@router.post("/disclosures")
def create_disclosure(body: dict, db: Session = Depends(get_db)):
    rec = ESGDisclosure(
        id=str(uuid.uuid4()),
        tenant_id=body.get("tenant_id", "default"),
        title=body["title"],
        framework=body["framework"],
        reporting_period=body["reporting_period"],
        disclosure_data=body.get("disclosure_data"),
        commitment_ids=body.get("commitment_ids"),
        metric_ids=body.get("metric_ids"),
        prepared_by=body.get("prepared_by"),
        status="draft",
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)
    return rec.to_dict()


@router.put("/disclosures/{disclosure_id}/publish")
def publish_disclosure(disclosure_id: str, body: dict, db: Session = Depends(get_db)):
    rec = db.query(ESGDisclosure).filter(ESGDisclosure.id == disclosure_id).first()
    if not rec:
        raise HTTPException(404, "Disclosure not found")
    rec.status = "published"
    rec.approved_by = body.get("approved_by")
    rec.published_at = datetime.utcnow()
    db.commit()
    db.refresh(rec)
    return rec.to_dict()


# ── Dashboard ─────────────────────────────────────────────────────────────────

@router.get("/dashboard")
def esg_dashboard(db: Session = Depends(get_db)):
    from sqlalchemy import func
    commitments = db.query(ESGCommitment.pillar, func.count()).group_by(ESGCommitment.pillar).all()
    by_status = db.query(ESGCommitment.status, func.count()).group_by(ESGCommitment.status).all()
    metrics_count = db.query(func.count(ESGMetric.id)).scalar()
    verified = db.query(func.count()).filter(ESGMetric.verified == True).scalar()
    return {
        "commitments_by_pillar": {p: c for p, c in commitments},
        "commitments_by_status": {s: c for s, c in by_status},
        "total_metrics": metrics_count,
        "verified_metrics": verified,
        "verification_rate": round(verified / max(metrics_count, 1) * 100, 1),
    }
