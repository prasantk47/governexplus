"""
TPRM — Third-Party Risk Management API Router

Full vendor risk lifecycle:
  - Vendor register with tiering and risk scoring
  - Periodic assessments (questionnaire-based or automated)
  - Issue tracking and remediation
  - Contract management with expiry alerting
  - Executive dashboard
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import uuid

from db.database import get_db
from db.models.extended_modules import Vendor, VendorAssessment, VendorIssue, VendorContract

router = APIRouter(tags=["Third-Party Risk Management"])


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

def _vendor_or_404(db: Session, vendor_id: str, tenant_id: str) -> Vendor:
    obj = db.query(Vendor).filter(
        Vendor.id == vendor_id,
        Vendor.tenant_id == tenant_id,
    ).first()
    if not obj:
        raise HTTPException(status_code=404, detail=f"Vendor '{vendor_id}' not found")
    return obj


def _assessment_or_404(db: Session, assessment_id: str, tenant_id: str) -> VendorAssessment:
    obj = db.query(VendorAssessment).filter(
        VendorAssessment.id == assessment_id,
        VendorAssessment.tenant_id == tenant_id,
    ).first()
    if not obj:
        raise HTTPException(status_code=404, detail=f"Assessment '{assessment_id}' not found")
    return obj


def _issue_or_404(db: Session, issue_id: str, tenant_id: str) -> VendorIssue:
    obj = db.query(VendorIssue).filter(
        VendorIssue.id == issue_id,
        VendorIssue.tenant_id == tenant_id,
    ).first()
    if not obj:
        raise HTTPException(status_code=404, detail=f"Issue '{issue_id}' not found")
    return obj


def _contract_or_404(db: Session, contract_id: str, tenant_id: str) -> VendorContract:
    obj = db.query(VendorContract).filter(
        VendorContract.id == contract_id,
        VendorContract.tenant_id == tenant_id,
    ).first()
    if not obj:
        raise HTTPException(status_code=404, detail=f"Contract '{contract_id}' not found")
    return obj


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class VendorCreate(BaseModel):
    vendor_name: str
    vendor_code: Optional[str] = None
    tier: str = Field(default="tier3", description="tier1 | tier2 | tier3 | tier4")
    status: str = Field(default="active", description="active | inactive | under_review | terminated")
    category: Optional[str] = None
    website: Optional[str] = None
    country: Optional[str] = None
    primary_contact_name: Optional[str] = None
    primary_contact_email: Optional[str] = None
    owner_id: Optional[str] = None
    owner_name: Optional[str] = None
    inherent_risk_score: Optional[float] = None
    services_provided: Optional[List[str]] = None
    data_classification: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class VendorUpdate(BaseModel):
    vendor_name: Optional[str] = None
    tier: Optional[str] = None
    status: Optional[str] = None
    category: Optional[str] = None
    website: Optional[str] = None
    country: Optional[str] = None
    primary_contact_name: Optional[str] = None
    primary_contact_email: Optional[str] = None
    owner_id: Optional[str] = None
    owner_name: Optional[str] = None
    inherent_risk_score: Optional[float] = None
    services_provided: Optional[List[str]] = None
    data_classification: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class AssessmentCreate(BaseModel):
    vendor_id: str
    assessment_type: str = Field(default="annual", description="annual | triggered | onboarding | exit")
    assessor_id: Optional[str] = None
    assessor_name: Optional[str] = None
    due_date: Optional[str] = None
    questionnaire_id: Optional[str] = None
    scope_notes: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class AssessmentUpdate(BaseModel):
    status: Optional[str] = None
    risk_score: Optional[float] = None
    findings_summary: Optional[str] = None
    recommendations: Optional[str] = None
    completed_at: Optional[str] = None
    next_assessment_date: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class IssueCreate(BaseModel):
    vendor_id: str
    assessment_id: Optional[str] = None
    title: str
    description: Optional[str] = None
    severity: str = Field(default="medium", description="critical | high | medium | low")
    category: Optional[str] = None
    remediation_plan: Optional[str] = None
    due_date: Optional[str] = None
    owner_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class IssueUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    severity: Optional[str] = None
    status: Optional[str] = None
    remediation_plan: Optional[str] = None
    due_date: Optional[str] = None
    resolved_at: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class ContractCreate(BaseModel):
    vendor_id: str
    contract_reference: Optional[str] = None
    contract_type: Optional[str] = None
    title: str
    status: str = Field(default="active", description="active | expired | terminated | draft")
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    contract_value: Optional[float] = None
    currency: Optional[str] = "USD"
    auto_renews: bool = False
    renewal_notice_days: Optional[int] = 30
    owner_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


# ---------------------------------------------------------------------------
# Vendors
# ---------------------------------------------------------------------------

@router.get("/vendors")
def list_vendors(
    tier: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """List vendors with optional filters."""
    q = db.query(Vendor).filter(Vendor.tenant_id == tenant_id)
    if tier:
        q = q.filter(Vendor.tier == tier)
    if status:
        q = q.filter(Vendor.status == status)
    if search:
        q = q.filter(Vendor.vendor_name.ilike(f"%{search}%"))
    total = q.count()
    vendors = q.order_by(Vendor.vendor_name).offset(offset).limit(limit).all()
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "vendors": [v.to_dict() for v in vendors],
    }


@router.post("/vendors", status_code=201)
def create_vendor(
    body: VendorCreate,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Register a new third-party vendor."""
    vendor = Vendor(
        id=_new_id("VND"),
        tenant_id=tenant_id,
        vendor_name=body.vendor_name,
        vendor_code=body.vendor_code,
        tier=body.tier,
        status=body.status,
        category=body.category,
        website=body.website,
        country=body.country,
        primary_contact_name=body.primary_contact_name,
        primary_contact_email=body.primary_contact_email,
        owner_id=body.owner_id,
        owner_name=body.owner_name,
        inherent_risk_score=body.inherent_risk_score,
        services_provided=body.services_provided or [],
        data_classification=body.data_classification,
        metadata_=body.metadata,
    )
    db.add(vendor)
    db.commit()
    db.refresh(vendor)
    return vendor.to_dict()


@router.get("/vendors/{id}")
def get_vendor(
    id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Get full vendor detail."""
    return _vendor_or_404(db, id, tenant_id).to_dict()


@router.put("/vendors/{id}")
def update_vendor(
    id: str,
    body: VendorUpdate,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Update a vendor record."""
    vendor = _vendor_or_404(db, id, tenant_id)
    updatable = [
        "vendor_name", "tier", "status", "category", "website", "country",
        "primary_contact_name", "primary_contact_email", "owner_id", "owner_name",
        "inherent_risk_score", "services_provided", "data_classification",
    ]
    for field in updatable:
        val = getattr(body, field)
        if val is not None:
            setattr(vendor, field, val)
    if body.metadata is not None:
        vendor.metadata_ = body.metadata
    db.commit()
    db.refresh(vendor)
    return vendor.to_dict()


@router.get("/vendors/{id}/assessments")
def list_vendor_assessments(
    id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """List all assessments for a specific vendor."""
    _vendor_or_404(db, id, tenant_id)
    assessments = db.query(VendorAssessment).filter(
        VendorAssessment.vendor_id == id,
        VendorAssessment.tenant_id == tenant_id,
    ).order_by(VendorAssessment.created_at.desc()).all()
    return {"total": len(assessments), "assessments": [a.to_dict() for a in assessments]}


@router.get("/vendors/{id}/issues")
def list_vendor_issues(
    id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """List all open and historical issues for a vendor."""
    _vendor_or_404(db, id, tenant_id)
    issues = db.query(VendorIssue).filter(
        VendorIssue.vendor_id == id,
        VendorIssue.tenant_id == tenant_id,
    ).order_by(VendorIssue.created_at.desc()).all()
    return {"total": len(issues), "issues": [i.to_dict() for i in issues]}


@router.get("/vendors/{id}/contracts")
def list_vendor_contracts(
    id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """List all contracts associated with a vendor."""
    _vendor_or_404(db, id, tenant_id)
    contracts = db.query(VendorContract).filter(
        VendorContract.vendor_id == id,
        VendorContract.tenant_id == tenant_id,
    ).order_by(VendorContract.created_at.desc()).all()
    return {"total": len(contracts), "contracts": [c.to_dict() for c in contracts]}


# ---------------------------------------------------------------------------
# Assessments
# ---------------------------------------------------------------------------

@router.post("/assessments", status_code=201)
def create_assessment(
    body: AssessmentCreate,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Create a new vendor assessment."""
    _vendor_or_404(db, body.vendor_id, tenant_id)
    assessment = VendorAssessment(
        id=_new_id("VAST"),
        tenant_id=tenant_id,
        vendor_id=body.vendor_id,
        assessment_type=body.assessment_type,
        assessor_id=body.assessor_id,
        assessor_name=body.assessor_name,
        due_date=datetime.fromisoformat(body.due_date) if body.due_date else None,
        questionnaire_id=body.questionnaire_id,
        scope_notes=body.scope_notes,
        status="draft",
        metadata_=body.metadata,
    )
    db.add(assessment)
    db.commit()
    db.refresh(assessment)
    return assessment.to_dict()


@router.put("/assessments/{id}")
def update_assessment(
    id: str,
    body: AssessmentUpdate,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Update an assessment — record score, status, findings."""
    assessment = _assessment_or_404(db, id, tenant_id)
    if body.status is not None:
        assessment.status = body.status
    if body.risk_score is not None:
        assessment.risk_score = body.risk_score
    if body.findings_summary is not None:
        assessment.findings_summary = body.findings_summary
    if body.recommendations is not None:
        assessment.recommendations = body.recommendations
    if body.completed_at:
        assessment.completed_at = datetime.fromisoformat(body.completed_at)
    if body.next_assessment_date:
        assessment.next_assessment_date = datetime.fromisoformat(body.next_assessment_date)
    if body.metadata is not None:
        assessment.metadata_ = body.metadata
    # Cascade risk score to vendor
    if body.risk_score is not None:
        vendor = db.query(Vendor).filter(
            Vendor.id == assessment.vendor_id,
            Vendor.tenant_id == tenant_id,
        ).first()
        if vendor:
            vendor.residual_risk_score = body.risk_score
            vendor.last_assessed_at = datetime.utcnow()
    db.commit()
    db.refresh(assessment)
    return assessment.to_dict()


# ---------------------------------------------------------------------------
# Issues
# ---------------------------------------------------------------------------

@router.post("/issues", status_code=201)
def create_issue(
    body: IssueCreate,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Create a vendor risk issue."""
    _vendor_or_404(db, body.vendor_id, tenant_id)
    issue = VendorIssue(
        id=_new_id("VISS"),
        tenant_id=tenant_id,
        vendor_id=body.vendor_id,
        assessment_id=body.assessment_id,
        title=body.title,
        description=body.description,
        severity=body.severity,
        category=body.category,
        remediation_plan=body.remediation_plan,
        due_date=datetime.fromisoformat(body.due_date) if body.due_date else None,
        owner_id=body.owner_id,
        status="open",
        metadata_=body.metadata,
    )
    db.add(issue)
    db.commit()
    db.refresh(issue)
    return issue.to_dict()


@router.put("/issues/{id}")
def update_issue(
    id: str,
    body: IssueUpdate,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Update a vendor issue status or remediation details."""
    issue = _issue_or_404(db, id, tenant_id)
    updatable = ["title", "description", "severity", "status", "remediation_plan", "owner_id"]
    for field in updatable:
        val = getattr(body, field, None)
        if val is not None:
            setattr(issue, field, val)
    if body.due_date:
        issue.due_date = datetime.fromisoformat(body.due_date)
    if body.resolved_at:
        issue.resolved_at = datetime.fromisoformat(body.resolved_at)
        issue.status = "resolved"
    if body.metadata is not None:
        issue.metadata_ = body.metadata
    db.commit()
    db.refresh(issue)
    return issue.to_dict()


# ---------------------------------------------------------------------------
# Contracts
# ---------------------------------------------------------------------------

@router.get("/contracts")
def list_contracts(
    status: Optional[str] = Query(None),
    expiring_soon: Optional[bool] = Query(None, description="Filter to contracts expiring within 30 days"),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """List all vendor contracts with optional filters."""
    q = db.query(VendorContract).filter(VendorContract.tenant_id == tenant_id)
    if status:
        q = q.filter(VendorContract.status == status)
    if expiring_soon:
        threshold = datetime.utcnow() + timedelta(days=30)
        q = q.filter(
            VendorContract.end_date != None,
            VendorContract.end_date <= threshold,
            VendorContract.status == "active",
        )
    contracts = q.order_by(VendorContract.end_date.asc().nullslast()).all()
    return {"total": len(contracts), "contracts": [c.to_dict() for c in contracts]}


@router.post("/contracts", status_code=201)
def create_contract(
    body: ContractCreate,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Create a new vendor contract record."""
    _vendor_or_404(db, body.vendor_id, tenant_id)
    contract = VendorContract(
        id=_new_id("VCNT"),
        tenant_id=tenant_id,
        vendor_id=body.vendor_id,
        contract_reference=body.contract_reference,
        contract_type=body.contract_type,
        title=body.title,
        status=body.status,
        start_date=datetime.fromisoformat(body.start_date) if body.start_date else None,
        end_date=datetime.fromisoformat(body.end_date) if body.end_date else None,
        contract_value=body.contract_value,
        currency=body.currency,
        auto_renews=body.auto_renews,
        renewal_notice_days=body.renewal_notice_days,
        owner_id=body.owner_id,
        metadata_=body.metadata,
    )
    db.add(contract)
    db.commit()
    db.refresh(contract)
    return contract.to_dict()


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@router.get("/dashboard")
def get_tprm_dashboard(
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """TPRM executive dashboard metrics."""
    now = datetime.utcnow()
    threshold_30d = now + timedelta(days=30)

    total_vendors = db.query(Vendor).filter(
        Vendor.tenant_id == tenant_id,
        Vendor.status == "active",
    ).count()

    high_risk_count = db.query(Vendor).filter(
        Vendor.tenant_id == tenant_id,
        Vendor.tier == "tier1",
        Vendor.status == "active",
    ).count()

    assessments_overdue = db.query(VendorAssessment).filter(
        VendorAssessment.tenant_id == tenant_id,
        VendorAssessment.status.in_(["draft", "in_progress"]),
        VendorAssessment.due_date < now,
    ).count()

    contracts_expiring_30d = db.query(VendorContract).filter(
        VendorContract.tenant_id == tenant_id,
        VendorContract.status == "active",
        VendorContract.end_date != None,
        VendorContract.end_date <= threshold_30d,
        VendorContract.end_date >= now,
    ).count()

    open_issues = db.query(VendorIssue).filter(
        VendorIssue.tenant_id == tenant_id,
        VendorIssue.status == "open",
    ).count()

    critical_issues = db.query(VendorIssue).filter(
        VendorIssue.tenant_id == tenant_id,
        VendorIssue.severity.in_(["critical", "high"]),
        VendorIssue.status == "open",
    ).count()

    return {
        "total_vendors": total_vendors,
        "high_risk_count": high_risk_count,
        "assessments_overdue": assessments_overdue,
        "contracts_expiring_30d": contracts_expiring_30d,
        "open_issues": open_issues,
        "critical_open_issues": critical_issues,
    }
