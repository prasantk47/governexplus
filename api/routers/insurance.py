"""
Insurance / Risk Transfer API Router

Tracks insurance policies mapped to enterprise risks with premium
management, coverage adequacy analysis, and renewal alerts.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import uuid

from db.database import get_db
from db.models.governance_extended import InsurancePolicy

router = APIRouter(tags=["Insurance / Risk Transfer"])


def _get_tenant_id() -> str:
    from core.tenant import get_current_tenant
    ctx = get_current_tenant()
    return ctx.tenant_id if ctx else "default"


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def _policy_or_404(db: Session, policy_id: str, tenant_id: str) -> InsurancePolicy:
    p = db.query(InsurancePolicy).filter(
        InsurancePolicy.policy_id == policy_id,
        InsurancePolicy.tenant_id == tenant_id,
        InsurancePolicy.is_active.is_(True),
    ).first()
    if not p:
        raise HTTPException(status_code=404, detail=f"Insurance policy '{policy_id}' not found")
    return p


@router.get("")
def list_policies(
    policy_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    expiring_within_days: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    q = db.query(InsurancePolicy).filter(
        InsurancePolicy.tenant_id == tenant_id,
        InsurancePolicy.is_active.is_(True),
    )
    if policy_type:
        q = q.filter(InsurancePolicy.policy_type == policy_type)
    if status:
        q = q.filter(InsurancePolicy.status == status)
    policies = q.order_by(InsurancePolicy.expiry_date).all()
    result = [p.to_dict() for p in policies]
    if expiring_within_days is not None:
        cutoff = (datetime.utcnow() + timedelta(days=expiring_within_days)).isoformat()
        result = [p for p in result if p.get("expiry_date") and p["expiry_date"] <= cutoff]
    return {"policies": result, "total": len(result)}


@router.post("", status_code=201)
def create_policy(
    body: Dict[str, Any] = Body(default={}),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    p = InsurancePolicy(
        policy_id=_new_id("INSP"),
        tenant_id=tenant_id,
        policy_number=body.get("policy_number") or _new_id("POL"),
        policy_type=body.get("policy_type", "general_liability"),
        insurer_name=body["insurer_name"],
        description=body.get("coverage_description"),
        coverage_amount=body.get("coverage_amount"),
        deductible=body.get("deductible"),
        annual_premium=body.get("annual_premium"),
        currency=body.get("currency", "USD"),
        effective_date=datetime.fromisoformat(body["effective_date"]) if body.get("effective_date") else None,
        expiry_date=datetime.fromisoformat(body["expiry_date"]) if body.get("expiry_date") else None,
        linked_risk_ids=body.get("covered_risk_ids") or body.get("linked_risk_ids"),
        exclusions=body.get("exclusions"),
        policy_owner=body.get("policy_owner"),
        broker_name=body.get("broker_name"),
        broker_contact=body.get("broker_contact"),
        status="active",
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return p.to_dict()


@router.get("/{policy_id}")
def get_policy(
    policy_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    return _policy_or_404(db, policy_id, tenant_id).to_dict()


@router.put("/{policy_id}")
def update_policy(
    policy_id: str,
    body: Dict[str, Any] = Body(default={}),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    p = _policy_or_404(db, policy_id, tenant_id)
    updatable = [
        "policy_number", "policy_type", "insurer_name", "description",
        "coverage_amount", "deductible", "annual_premium", "currency",
        "linked_risk_ids", "exclusions", "policy_owner", "broker_name",
        "broker_contact", "status",
    ]
    for k in updatable:
        if k in body:
            setattr(p, k, body[k])
    for d in ["effective_date", "expiry_date"]:
        if d in body and body[d]:
            setattr(p, d, datetime.fromisoformat(body[d]))
    db.commit()
    db.refresh(p)
    return p.to_dict()


@router.get("/summary/coverage")
def coverage_summary(
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    policies = db.query(InsurancePolicy).filter(
        InsurancePolicy.tenant_id == tenant_id,
        InsurancePolicy.is_active.is_(True),
        InsurancePolicy.status == "active",
    ).all()
    now = datetime.utcnow()
    expiring_soon = [p for p in policies if p.expiry_date and (p.expiry_date - now).days <= 90]
    total_premium = sum(float(p.annual_premium or 0) for p in policies)
    total_coverage = sum(float(p.coverage_amount or 0) for p in policies)
    by_type: Dict[str, int] = {}
    for p in policies:
        pt = p.policy_type or "unknown"
        by_type[pt] = by_type.get(pt, 0) + 1
    return {
        "active_policies": len(policies),
        "expiring_within_90_days": len(expiring_soon),
        "total_annual_premium": round(total_premium, 2),
        "total_coverage_amount": round(total_coverage, 2),
        "by_type": by_type,
    }
