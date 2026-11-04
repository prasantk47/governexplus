"""
Regulatory Intelligence — Framework management, obligation tracking,
compliance mapping, and evidence linkage.
"""

import uuid
from datetime import datetime
from typing import List, Optional, Dict
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from api.dependencies import get_current_user
from db.database import get_db
from db.models.regulatory import (
    RegulatoryFramework, RegulatoryObligation, ObligationEvidence,
    ComplianceStatus
)

router = APIRouter(tags=["Regulatory Intelligence"])


def _get_tenant_id(user: dict = Depends(get_current_user)) -> str:
    return user.get("tenant_id", "default")


def _new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12].upper()}"


def _framework_or_404(db: Session, framework_id: str, tenant_id: str) -> RegulatoryFramework:
    f = db.query(RegulatoryFramework).filter_by(framework_id=framework_id, tenant_id=tenant_id).first()
    if not f:
        raise HTTPException(404, f"Framework {framework_id} not found")
    return f


def _obligation_or_404(db: Session, obligation_id: str, tenant_id: str) -> RegulatoryObligation:
    o = db.query(RegulatoryObligation).filter_by(obligation_id=obligation_id, tenant_id=tenant_id).first()
    if not o:
        raise HTTPException(404, f"Obligation {obligation_id} not found")
    return o


# ─── Models ───────────────────────────────────────────────────────────────────

class FrameworkCreate(BaseModel):
    name: str = Field(..., min_length=2)
    short_name: Optional[str] = None
    description: Optional[str] = None
    region: str = "global"
    effective_date: Optional[str] = None
    next_review_date: Optional[str] = None
    is_mandatory: bool = True
    external_reference: Optional[str] = None
    owner_id: Optional[str] = None
    owner_name: Optional[str] = None


class ObligationCreate(BaseModel):
    framework_id: str
    reference_code: Optional[str] = None
    title: str = Field(..., min_length=3)
    description: Optional[str] = None
    requirement_text: Optional[str] = None
    obligation_type: Optional[str] = None
    owner_id: Optional[str] = None
    owner_name: Optional[str] = None
    accountable_department: Optional[str] = None
    is_key_obligation: bool = False
    penalty_risk: str = "medium"
    linked_control_ids: List[str] = []
    linked_risk_ids: List[str] = []
    linked_policy_ids: List[str] = []


class ObligationAssess(BaseModel):
    compliance_status: str
    compliance_score: Optional[float] = None
    evidence_summary: Optional[str] = None
    gaps_identified: Optional[str] = None
    next_assessment_date: Optional[str] = None


class EvidenceAdd(BaseModel):
    title: str
    description: Optional[str] = None
    evidence_type: Optional[str] = None
    file_reference: Optional[str] = None
    valid_until: Optional[str] = None
    is_sufficient: Optional[bool] = None


# ─── Frameworks ───────────────────────────────────────────────────────────────

@router.post("/regulatory/frameworks", status_code=201)
def create_framework(
    body: FrameworkCreate,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
    user: dict = Depends(get_current_user),
):
    f = RegulatoryFramework(
        framework_id=_new_id("FW"),
        tenant_id=tenant_id,
        name=body.name,
        short_name=body.short_name,
        description=body.description,
        region=body.region,
        effective_date=datetime.fromisoformat(body.effective_date) if body.effective_date else None,
        next_review_date=datetime.fromisoformat(body.next_review_date) if body.next_review_date else None,
        is_mandatory=body.is_mandatory,
        external_reference=body.external_reference,
        owner_id=body.owner_id,
        owner_name=body.owner_name,
        status="active",
        created_by=user.get("user_id"),
    )
    db.add(f)
    db.commit()
    db.refresh(f)
    return f.to_dict()


@router.get("/regulatory/frameworks")
def list_frameworks(
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
    region: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
):
    q = db.query(RegulatoryFramework).filter(RegulatoryFramework.tenant_id == tenant_id)
    if region:
        q = q.filter(RegulatoryFramework.region == region)
    if status:
        q = q.filter(RegulatoryFramework.status == status)
    frameworks = q.order_by(RegulatoryFramework.name).all()

    result = []
    for f in frameworks:
        d = f.to_dict()
        obligations = db.query(RegulatoryObligation).filter_by(framework_id=f.framework_id, tenant_id=tenant_id).all()
        d["total_obligations"] = len(obligations)
        d["compliant_count"] = sum(1 for o in obligations if o.compliance_status == "compliant")
        d["non_compliant_count"] = sum(1 for o in obligations if o.compliance_status == "non_compliant")
        d["not_assessed_count"] = sum(1 for o in obligations if o.compliance_status == "not_assessed")
        result.append(d)
    return {"frameworks": result, "total": len(result)}


@router.get("/regulatory/frameworks/{framework_id}")
def get_framework(
    framework_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    f = _framework_or_404(db, framework_id, tenant_id)
    d = f.to_dict()
    obligations = db.query(RegulatoryObligation).filter_by(framework_id=framework_id, tenant_id=tenant_id).all()
    d["obligations"] = [o.to_dict() for o in obligations]
    d["total_obligations"] = len(obligations)
    statuses = {}
    for o in obligations:
        statuses[o.compliance_status] = statuses.get(o.compliance_status, 0) + 1
    d["compliance_breakdown"] = statuses
    return d


@router.put("/regulatory/frameworks/{framework_id}")
def update_framework(
    framework_id: str,
    body: FrameworkCreate,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
    user: dict = Depends(get_current_user),
):
    f = _framework_or_404(db, framework_id, tenant_id)
    for k, v in body.model_dump(exclude_none=True).items():
        if k in ("effective_date", "next_review_date") and v:
            v = datetime.fromisoformat(v)
        setattr(f, k, v)
    db.commit()
    db.refresh(f)
    return f.to_dict()


# ─── Obligations ──────────────────────────────────────────────────────────────

@router.post("/regulatory/obligations", status_code=201)
def create_obligation(
    body: ObligationCreate,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
    user: dict = Depends(get_current_user),
):
    _framework_or_404(db, body.framework_id, tenant_id)
    o = RegulatoryObligation(
        obligation_id=_new_id("OBL"),
        tenant_id=tenant_id,
        framework_id=body.framework_id,
        reference_code=body.reference_code,
        title=body.title,
        description=body.description,
        requirement_text=body.requirement_text,
        obligation_type=body.obligation_type,
        owner_id=body.owner_id,
        owner_name=body.owner_name,
        accountable_department=body.accountable_department,
        is_key_obligation=body.is_key_obligation,
        penalty_risk=body.penalty_risk,
        linked_control_ids=body.linked_control_ids,
        linked_risk_ids=body.linked_risk_ids,
        linked_policy_ids=body.linked_policy_ids,
        compliance_status="not_assessed",
        status="active",
        created_by=user.get("user_id"),
    )
    db.add(o)
    db.commit()
    db.refresh(o)
    return o.to_dict()


@router.get("/regulatory/obligations")
def list_obligations(
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
    framework_id: Optional[str] = Query(None),
    compliance_status: Optional[str] = Query(None),
    is_key: Optional[bool] = Query(None),
    penalty_risk: Optional[str] = Query(None),
):
    q = db.query(RegulatoryObligation).filter(RegulatoryObligation.tenant_id == tenant_id)
    if framework_id:
        q = q.filter(RegulatoryObligation.framework_id == framework_id)
    if compliance_status:
        q = q.filter(RegulatoryObligation.compliance_status == compliance_status)
    if is_key is not None:
        q = q.filter(RegulatoryObligation.is_key_obligation == is_key)
    if penalty_risk:
        q = q.filter(RegulatoryObligation.penalty_risk == penalty_risk)
    obligations = q.order_by(RegulatoryObligation.title).all()
    return {"obligations": [o.to_dict() for o in obligations], "total": len(obligations)}


@router.get("/regulatory/obligations/{obligation_id}")
def get_obligation(
    obligation_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    o = _obligation_or_404(db, obligation_id, tenant_id)
    d = o.to_dict()
    d["evidence"] = [e.to_dict() for e in o.evidence_records]
    return d


@router.post("/regulatory/obligations/{obligation_id}/assess")
def assess_obligation(
    obligation_id: str,
    body: ObligationAssess,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
    user: dict = Depends(get_current_user),
):
    """Record compliance assessment for an obligation."""
    o = _obligation_or_404(db, obligation_id, tenant_id)
    o.compliance_status = body.compliance_status
    if body.compliance_score is not None:
        o.compliance_score = body.compliance_score
    if body.evidence_summary:
        o.evidence_summary = body.evidence_summary
    if body.gaps_identified:
        o.gaps_identified = body.gaps_identified
    o.last_assessed_date = datetime.utcnow()
    o.assessed_by = user.get("user_id")
    if body.next_assessment_date:
        o.next_assessment_date = datetime.fromisoformat(body.next_assessment_date)
    db.commit()
    db.refresh(o)
    return o.to_dict()


@router.post("/regulatory/obligations/{obligation_id}/link")
def link_obligation(
    obligation_id: str,
    control_ids: List[str] = Query(default=[]),
    risk_ids: List[str] = Query(default=[]),
    policy_ids: List[str] = Query(default=[]),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
    user: dict = Depends(get_current_user),
):
    """Link controls, risks, and policies to an obligation."""
    o = _obligation_or_404(db, obligation_id, tenant_id)
    existing_controls = set(o.linked_control_ids or [])
    existing_risks = set(o.linked_risk_ids or [])
    existing_policies = set(o.linked_policy_ids or [])

    o.linked_control_ids = list(existing_controls | set(control_ids))
    o.linked_risk_ids = list(existing_risks | set(risk_ids))
    o.linked_policy_ids = list(existing_policies | set(policy_ids))
    db.commit()
    return {"message": "Links updated", "obligation_id": obligation_id}


@router.post("/regulatory/obligations/{obligation_id}/evidence", status_code=201)
def add_evidence(
    obligation_id: str,
    body: EvidenceAdd,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
    user: dict = Depends(get_current_user),
):
    _obligation_or_404(db, obligation_id, tenant_id)
    e = ObligationEvidence(
        evidence_id=_new_id("EV"),
        obligation_id=obligation_id,
        tenant_id=tenant_id,
        title=body.title,
        description=body.description,
        evidence_type=body.evidence_type,
        file_reference=body.file_reference,
        valid_until=datetime.fromisoformat(body.valid_until) if body.valid_until else None,
        is_sufficient=body.is_sufficient,
        collected_by=user.get("user_id"),
    )
    db.add(e)
    db.commit()
    db.refresh(e)
    return e.to_dict()


# ─── Summary / Dashboard ──────────────────────────────────────────────────────

@router.get("/regulatory/dashboard")
def regulatory_dashboard(
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Overall regulatory compliance posture dashboard."""
    frameworks = db.query(RegulatoryFramework).filter_by(tenant_id=tenant_id, status="active").all()
    all_obligations = db.query(RegulatoryObligation).filter_by(tenant_id=tenant_id, status="active").all()

    by_status: Dict[str, int] = {}
    by_framework: Dict[str, Dict] = {}
    critical_gaps = []

    for o in all_obligations:
        by_status[o.compliance_status] = by_status.get(o.compliance_status, 0) + 1
        if o.framework_id not in by_framework:
            fw = next((f for f in frameworks if f.framework_id == o.framework_id), None)
            by_framework[o.framework_id] = {
                "framework_name": fw.short_name or fw.name if fw else o.framework_id,
                "total": 0, "compliant": 0, "non_compliant": 0, "not_assessed": 0,
            }
        by_framework[o.framework_id]["total"] += 1
        if o.compliance_status == "compliant":
            by_framework[o.framework_id]["compliant"] += 1
        elif o.compliance_status == "non_compliant":
            by_framework[o.framework_id]["non_compliant"] += 1
            if o.is_key_obligation or o.penalty_risk in ("high", "critical"):
                critical_gaps.append({
                    "obligation_id": o.obligation_id,
                    "title": o.title,
                    "framework_id": o.framework_id,
                    "penalty_risk": o.penalty_risk,
                    "gaps_identified": o.gaps_identified,
                })
        else:
            by_framework[o.framework_id]["not_assessed"] += 1

    total = len(all_obligations)
    compliant = by_status.get("compliant", 0)
    score = round((compliant / total * 100), 1) if total > 0 else 0

    return {
        "overall_compliance_score": score,
        "total_frameworks": len(frameworks),
        "total_obligations": total,
        "by_status": by_status,
        "by_framework": list(by_framework.values()),
        "critical_gaps": critical_gaps,
        "non_compliant_count": by_status.get("non_compliant", 0),
        "not_assessed_count": by_status.get("not_assessed", 0),
    }
