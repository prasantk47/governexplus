"""
GAP-5: Evidence Management Service Router
"""
import hashlib
import uuid
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from db.database import get_db
from db.models.evidence_management import EvidenceItem, EvidencePackage

router = APIRouter()


@router.get("/items")
def list_evidence(
    category: str = None,
    evidence_type: str = None,
    status: str = None,
    db: Session = Depends(get_db),
):
    q = db.query(EvidenceItem)
    if category:
        q = q.filter(EvidenceItem.category == category)
    if evidence_type:
        q = q.filter(EvidenceItem.evidence_type == evidence_type)
    if status:
        q = q.filter(EvidenceItem.status == status)
    return [r.to_dict() for r in q.order_by(EvidenceItem.created_at.desc()).limit(200).all()]


@router.post("/items")
def create_evidence(body: dict, db: Session = Depends(get_db)):
    content = body.get("content_text", "")
    checksum = hashlib.sha256(content.encode()).hexdigest() if content else None
    retention_days = body.get("retention_period_days", 2555)
    rec = EvidenceItem(
        id=str(uuid.uuid4()),
        tenant_id=body.get("tenant_id", "default"),
        evidence_id=body.get("evidence_id", f"EVD-{uuid.uuid4().hex[:8].upper()}"),
        title=body["title"],
        description=body.get("description"),
        evidence_type=body.get("evidence_type", "document"),
        category=body.get("category", "control_test"),
        sensitivity=body.get("sensitivity", "internal"),
        source_system=body.get("source_system"),
        source_module=body.get("source_module"),
        source_record_id=body.get("source_record_id"),
        source_record_type=body.get("source_record_type"),
        collected_by=body.get("collected_by", "system"),
        collected_at=datetime.utcnow(),
        file_name=body.get("file_name"),
        file_type=body.get("file_type"),
        file_size_bytes=body.get("file_size_bytes"),
        storage_path=body.get("storage_path"),
        content_text=content,
        checksum_sha256=checksum,
        is_tamper_evident=bool(checksum),
        retention_class=body.get("retention_class", "standard"),
        retention_period_days=retention_days,
        retention_expiry_date=datetime.utcnow() + timedelta(days=retention_days),
        custody_chain=[{"actor": body.get("collected_by", "system"), "action": "collected", "timestamp": datetime.utcnow().isoformat()}],
        linked_control_ids=body.get("linked_control_ids"),
        linked_risk_ids=body.get("linked_risk_ids"),
        linked_issue_ids=body.get("linked_issue_ids"),
        linked_finding_ids=body.get("linked_finding_ids"),
        linked_audit_ids=body.get("linked_audit_ids"),
        linked_obligation_ids=body.get("linked_obligation_ids"),
        status="active",
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)
    return rec.to_dict()


@router.get("/items/{evidence_id}")
def get_evidence(evidence_id: str, db: Session = Depends(get_db)):
    rec = db.query(EvidenceItem).filter(
        (EvidenceItem.id == evidence_id) | (EvidenceItem.evidence_id == evidence_id)
    ).first()
    if not rec:
        raise HTTPException(404, "Evidence not found")
    chain = rec.custody_chain or []
    chain.append({"actor": "viewer", "action": "accessed", "timestamp": datetime.utcnow().isoformat()})
    rec.custody_chain = chain
    db.commit()
    return rec.to_dict()


@router.put("/items/{evidence_id}/legal-hold")
def set_legal_hold(evidence_id: str, body: dict, db: Session = Depends(get_db)):
    rec = db.query(EvidenceItem).filter(
        (EvidenceItem.id == evidence_id) | (EvidenceItem.evidence_id == evidence_id)
    ).first()
    if not rec:
        raise HTTPException(404, "Evidence not found")
    rec.legal_hold = body.get("hold", True)
    rec.legal_hold_reason = body.get("reason")
    rec.legal_hold_set_by = body.get("set_by", "system")
    rec.legal_hold_set_at = datetime.utcnow()
    rec.disposal_eligible = False
    db.commit()
    db.refresh(rec)
    return rec.to_dict()


@router.get("/packages")
def list_packages(status: str = None, db: Session = Depends(get_db)):
    q = db.query(EvidencePackage)
    if status:
        q = q.filter(EvidencePackage.status == status)
    return [r.to_dict() for r in q.order_by(EvidencePackage.created_at.desc()).limit(100).all()]


@router.post("/packages")
def create_package(body: dict, db: Session = Depends(get_db)):
    items = body.get("evidence_item_ids", [])
    rec = EvidencePackage(
        id=str(uuid.uuid4()),
        tenant_id=body.get("tenant_id", "default"),
        package_id=body.get("package_id", f"PKG-{uuid.uuid4().hex[:8].upper()}"),
        title=body["title"],
        description=body.get("description"),
        package_type=body.get("package_type", "audit_engagement"),
        purpose=body.get("purpose"),
        evidence_item_ids=items,
        item_count=len(items),
        compiled_by=body.get("compiled_by", "system"),
        compiled_at=datetime.utcnow(),
        linked_engagement_id=body.get("linked_engagement_id"),
        linked_assessment_id=body.get("linked_assessment_id"),
        linked_change_request_id=body.get("linked_change_request_id"),
        access_restricted_to=body.get("access_restricted_to"),
        status="draft",
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)
    return rec.to_dict()


@router.get("/packages/{package_id}")
def get_package(package_id: str, db: Session = Depends(get_db)):
    rec = db.query(EvidencePackage).filter(
        (EvidencePackage.id == package_id) | (EvidencePackage.package_id == package_id)
    ).first()
    if not rec:
        raise HTTPException(404, "Package not found")
    return rec.to_dict()


@router.put("/packages/{package_id}/seal")
def seal_package(package_id: str, body: dict, db: Session = Depends(get_db)):
    rec = db.query(EvidencePackage).filter(
        (EvidencePackage.id == package_id) | (EvidencePackage.package_id == package_id)
    ).first()
    if not rec:
        raise HTTPException(404, "Package not found")
    rec.status = "sealed"
    rec.approved_by = body.get("approved_by", "system")
    rec.approved_at = datetime.utcnow()
    db.commit()
    db.refresh(rec)
    return rec.to_dict()


@router.get("/summary")
def evidence_summary(db: Session = Depends(get_db)):
    from sqlalchemy import func
    total = db.query(func.count(EvidenceItem.id)).scalar()
    by_type = db.query(EvidenceItem.evidence_type, func.count()).group_by(EvidenceItem.evidence_type).all()
    legal_holds = db.query(func.count()).filter(EvidenceItem.legal_hold == True).scalar()
    packages = db.query(func.count(EvidencePackage.id)).scalar()
    return {
        "total_items": total,
        "by_type": {t: c for t, c in by_type},
        "legal_holds": legal_holds,
        "total_packages": packages,
    }
