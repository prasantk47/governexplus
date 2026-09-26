"""
Risk Management API Router

Full enterprise risk management lifecycle (RM-01 through RM-31):
  - Risk register CRUD
  - Periodic / ad-hoc assessments with workflow
  - Risk appetite and KRI management
  - Risk responses and incident management
  - Heatmap, trend, and coverage reporting
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import uuid

from db.database import get_db
from db.models.risk_management import (
    EnterpriseRisk, RiskCategory, RiskStatus,
    RiskAssessment, AssessmentType, AssessmentStatus,
    RiskAppetite,
    KeyRiskIndicator, KRIStatus, KRIMeasurement,
    RiskResponse, RiskResponseType, ResponseStatus,
    RiskIncident, IncidentSeverity, IncidentStatus,
)

router = APIRouter(tags=["Risk Management"])

_VALID_CATEGORIES = {e.value for e in RiskCategory}
_VALID_STATUSES   = {e.value for e in RiskStatus}


# ---------------------------------------------------------------------------
# Tenant helpers
# ---------------------------------------------------------------------------

def _get_tenant_id() -> str:
    from core.tenant import get_current_tenant
    ctx = get_current_tenant()
    return ctx.tenant_id if ctx else "default"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _risk_or_404(db: Session, risk_id: str, tenant_id: str) -> EnterpriseRisk:
    r = db.query(EnterpriseRisk).filter(
        EnterpriseRisk.risk_id == risk_id,
        EnterpriseRisk.tenant_id == tenant_id,
        EnterpriseRisk.is_active.is_(True),
    ).first()
    if not r:
        raise HTTPException(status_code=404, detail=f"Risk '{risk_id}' not found")
    return r


def _assessment_or_404(db: Session, assessment_id: str, tenant_id: str) -> RiskAssessment:
    a = db.query(RiskAssessment).filter(
        RiskAssessment.assessment_id == assessment_id,
        RiskAssessment.tenant_id == tenant_id,
    ).first()
    if not a:
        raise HTTPException(status_code=404, detail=f"Assessment '{assessment_id}' not found")
    return a


def _kri_or_404(db: Session, kri_id: str, tenant_id: str) -> KeyRiskIndicator:
    k = db.query(KeyRiskIndicator).filter(
        KeyRiskIndicator.kri_id == kri_id,
        KeyRiskIndicator.tenant_id == tenant_id,
    ).first()
    if not k:
        raise HTTPException(status_code=404, detail=f"KRI '{kri_id}' not found")
    return k


def _response_or_404(db: Session, response_id: str, tenant_id: str) -> RiskResponse:
    r = db.query(RiskResponse).filter(
        RiskResponse.response_id == response_id,
        RiskResponse.tenant_id == tenant_id,
    ).first()
    if not r:
        raise HTTPException(status_code=404, detail=f"Response '{response_id}' not found")
    return r


def _incident_or_404(db: Session, incident_id: str, tenant_id: str) -> RiskIncident:
    i = db.query(RiskIncident).filter(
        RiskIncident.incident_id == incident_id,
        RiskIncident.tenant_id == tenant_id,
    ).first()
    if not i:
        raise HTTPException(status_code=404, detail=f"Incident '{incident_id}' not found")
    return i


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def _get_manager(
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """DI factory: returns a per-request RiskManagementManager."""
    from core.risk_management.manager import RiskManagementManager
    return RiskManagementManager(tenant_id=tenant_id, db=db)


def _kri_status(kri: KeyRiskIndicator) -> str:
    if kri.current_value is None:
        return KRIStatus.NORMAL.value
    if kri.threshold_red is not None and kri.current_value >= kri.threshold_red:
        return KRIStatus.BREACH.value
    if kri.threshold_amber is not None and kri.current_value >= kri.threshold_amber:
        return KRIStatus.WARNING.value
    return KRIStatus.NORMAL.value


# ===========================================================================
# Risk Register  (RM-01)
# ===========================================================================

@router.post("/risks", status_code=201)
def create_risk(
    body: Dict[str, Any],
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Create a new enterprise risk register entry."""
    category_val = body.get("category", "operational")
    try:
        category = RiskCategory(category_val)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid category: {category_val}")

    inherent_likelihood = body.get("inherent_likelihood")
    inherent_impact = body.get("inherent_impact")
    inherent_score = (
        inherent_likelihood * inherent_impact
        if inherent_likelihood and inherent_impact else None
    )

    risk = EnterpriseRisk(
        tenant_id=tenant_id,
        risk_id=body.get("risk_id") or _new_id("RISK"),
        title=body.get("title", ""),
        description=body.get("description"),
        description_ar=body.get("description_ar"),
        category=category,
        org_unit_id=body.get("org_unit_id"),
        risk_owner_id=body.get("risk_owner_id"),
        risk_owner_name=body.get("risk_owner_name"),
        inherent_likelihood=inherent_likelihood,
        inherent_impact=inherent_impact,
        inherent_score=inherent_score,
        residual_likelihood=body.get("residual_likelihood"),
        residual_impact=body.get("residual_impact"),
        residual_score=body.get("residual_score"),
        risk_appetite=body.get("risk_appetite"),
        risk_tolerance=body.get("risk_tolerance"),
        status=RiskStatus.IDENTIFIED,
        next_review_date=(
            datetime.fromisoformat(body["next_review_date"])
            if body.get("next_review_date") else None
        ),
        review_frequency=body.get("review_frequency"),
        related_control_ids=body.get("related_control_ids", []),
        related_finding_ids=body.get("related_finding_ids", []),
        metadata_=body.get("metadata"),
        is_active=True,
    )
    db.add(risk)
    db.commit()
    db.refresh(risk)
    return risk.to_dict()


@router.get("/risks")
def list_risks(
    category: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    org_unit_id: Optional[int] = Query(None),
    owner_id: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """List risks with optional filters."""
    q = db.query(EnterpriseRisk).filter(
        EnterpriseRisk.tenant_id == tenant_id,
        EnterpriseRisk.is_active.is_(True),
    )
    if category:
        q = q.filter(EnterpriseRisk.category == RiskCategory(category))
    if status:
        q = q.filter(EnterpriseRisk.status == RiskStatus(status))
    if org_unit_id is not None:
        q = q.filter(EnterpriseRisk.org_unit_id == org_unit_id)
    if owner_id:
        q = q.filter(EnterpriseRisk.risk_owner_id == owner_id)
    if search:
        like = f"%{search}%"
        q = q.filter(EnterpriseRisk.title.ilike(like))
    risks = q.order_by(EnterpriseRisk.created_at.desc()).all()
    return {"total": len(risks), "risks": [r.to_dict() for r in risks]}


@router.get("/risks/{risk_id}")
def get_risk(
    risk_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """
    Return a single enterprise risk.

    Response always includes the XL-A coverage fields:
      control_coverage, system_indicated_residual, coverage_computed_at.
    These are populated by POST /risks/{risk_id}/recompute-coverage and are
    null until that endpoint has been called at least once.
    """
    return _risk_or_404(db, risk_id, tenant_id).to_dict()


@router.post("/risks/{risk_id}/recompute-coverage")
def recompute_control_coverage(
    risk_id: str,
    manager=Depends(_get_manager),
):
    """
    XL-A — Control-Failure → Residual Risk Feedback (Loop A).

    Inspects every ProcessControl linked via risk.related_control_ids and
    evaluates open ControlDeficiency records plus the latest ControlTest result
    for each control.

    Populates three read-only audit fields on the risk WITHOUT touching the
    assessor-owned residual_score (auditors hate silent rewrites):
      control_coverage          : 'effective' | 'degraded' | 'failed' | 'uncontrolled'
      system_indicated_residual : risk-adjusted residual score (amplified by a
                                  degradation factor, capped at inherent_score)
      coverage_computed_at      : UTC timestamp of this computation

    Degradation factors applied to residual_score:
      material weakness / ineffective test  → × 1.5  (coverage = 'failed')
      significant deficiency / partial test → × 1.25 (coverage = 'degraded')
      all controls effective                → × 1.0  (coverage = 'effective')
    """
    try:
        return manager.recompute_control_coverage(risk_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.put("/risks/{risk_id}")
def update_risk(
    risk_id: str,
    body: Dict[str, Any],
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    risk = _risk_or_404(db, risk_id, tenant_id)
    updatable = [
        "title", "description", "description_ar", "risk_owner_id", "risk_owner_name",
        "inherent_likelihood", "inherent_impact", "inherent_score",
        "residual_likelihood", "residual_impact", "residual_score",
        "risk_appetite", "risk_tolerance", "review_frequency",
        "related_control_ids", "related_finding_ids", "metadata_",
    ]
    for field in updatable:
        if field in body:
            setattr(risk, field, body[field])
    if "category" in body:
        risk.category = RiskCategory(body["category"])
    if "status" in body:
        risk.status = RiskStatus(body["status"])
    if "next_review_date" in body and body["next_review_date"]:
        risk.next_review_date = datetime.fromisoformat(body["next_review_date"])
    db.commit()
    db.refresh(risk)
    return risk.to_dict()


@router.delete("/risks/{risk_id}", status_code=204)
def delete_risk(
    risk_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    risk = _risk_or_404(db, risk_id, tenant_id)
    risk.is_active = False
    db.commit()


# ===========================================================================
# Risk Assessments  (RM-10, RM-11)
# ===========================================================================

@router.post("/risks/{risk_id}/assessments", status_code=201)
def create_assessment(
    risk_id: str,
    body: Dict[str, Any],
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Create a new risk assessment for a risk."""
    risk = _risk_or_404(db, risk_id, tenant_id)
    likelihood = body.get("likelihood_score", 3)
    impact = body.get("impact_score", 3)
    assessment_type_val = body.get("assessment_type", "periodic")
    try:
        assessment_type = AssessmentType(assessment_type_val)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid assessment type: {assessment_type_val}")

    a = RiskAssessment(
        tenant_id=tenant_id,
        assessment_id=_new_id("ASMT"),
        risk_id=risk.id,
        assessor_id=body.get("assessor_id"),
        assessor_name=body.get("assessor_name"),
        likelihood_score=likelihood,
        impact_score=impact,
        overall_score=likelihood * impact,
        assessment_type=assessment_type,
        likelihood_rationale=body.get("likelihood_rationale"),
        impact_rationale=body.get("impact_rationale"),
        monetary_impact=body.get("monetary_impact"),
        currency=body.get("currency", "USD"),
        status=AssessmentStatus.DRAFT,
        comments=body.get("comments"),
    )
    db.add(a)
    # Update risk last_assessed
    risk.last_assessed_at = datetime.utcnow()
    risk.status = RiskStatus.ASSESSED
    db.commit()
    db.refresh(a)
    return a.to_dict()


@router.get("/risks/{risk_id}/assessments")
def get_risk_assessments(
    risk_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    risk = _risk_or_404(db, risk_id, tenant_id)
    assessments = db.query(RiskAssessment).filter(
        RiskAssessment.risk_id == risk.id,
        RiskAssessment.tenant_id == tenant_id,
    ).order_by(RiskAssessment.created_at.desc()).all()
    return {"total": len(assessments), "assessments": [a.to_dict() for a in assessments]}


@router.put("/assessments/{assessment_id}/submit")
def submit_assessment(
    assessment_id: str,
    body: Dict[str, Any],
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    a = _assessment_or_404(db, assessment_id, tenant_id)
    if a.status != AssessmentStatus.DRAFT:
        raise HTTPException(status_code=400, detail="Only DRAFT assessments can be submitted")
    a.status = AssessmentStatus.SUBMITTED
    db.commit()
    db.refresh(a)
    return a.to_dict()


@router.put("/assessments/{assessment_id}/review")
def review_assessment(
    assessment_id: str,
    body: Dict[str, Any],
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    a = _assessment_or_404(db, assessment_id, tenant_id)
    a.status = AssessmentStatus.REVIEWED
    a.reviewed_by = body.get("reviewed_by")
    a.reviewed_at = datetime.utcnow()
    a.comments = body.get("comments", a.comments)
    db.commit()
    db.refresh(a)
    return a.to_dict()


@router.post("/assessment-campaigns")
def run_assessment_campaign(
    body: Dict[str, Any],
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Trigger a batch assessment campaign for a set of risks or category."""
    category = body.get("category")
    assessor_id = body.get("assessor_id", "system")
    assessor_name = body.get("assessor_name", "System")
    campaign_id = _new_id("CAMP")
    created = []

    q = db.query(EnterpriseRisk).filter(
        EnterpriseRisk.tenant_id == tenant_id,
        EnterpriseRisk.is_active.is_(True),
    )
    if category:
        try:
            q = q.filter(EnterpriseRisk.category == RiskCategory(category))
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid category: {category}")
    risks = q.all()

    for risk in risks:
        a = RiskAssessment(
            tenant_id=tenant_id,
            assessment_id=_new_id("ASMT"),
            risk_id=risk.id,
            assessor_id=assessor_id,
            assessor_name=assessor_name,
            likelihood_score=risk.residual_likelihood or risk.inherent_likelihood or 3,
            impact_score=risk.residual_impact or risk.inherent_impact or 3,
            overall_score=(risk.residual_likelihood or 3) * (risk.residual_impact or 3),
            assessment_type=AssessmentType.PERIODIC,
            status=AssessmentStatus.DRAFT,
            comments=f"Campaign: {campaign_id}",
        )
        db.add(a)
        risk.last_assessed_at = datetime.utcnow()
        created.append(a.assessment_id)

    db.commit()
    return {
        "campaign_id": campaign_id,
        "assessments_created": len(created),
        "assessment_ids": created,
    }


# ===========================================================================
# Risk Appetite  (RM-03)
# ===========================================================================

@router.post("/appetites", status_code=201)
def set_appetite(
    body: Dict[str, Any],
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Set or replace the risk appetite for a category / org unit."""
    category = body.get("category", "all")
    org_unit_id = body.get("org_unit_id")

    # Upsert: deactivate old record if exists by removing (simple replace strategy)
    existing = db.query(RiskAppetite).filter(
        RiskAppetite.tenant_id == tenant_id,
        RiskAppetite.category == category,
        RiskAppetite.org_unit_id == org_unit_id,
    ).first()

    if existing:
        existing.appetite_score = body["appetite_score"]
        existing.tolerance_score = body["tolerance_score"]
        existing.description = body.get("description", existing.description)
        existing.approved_by = body.get("approved_by", existing.approved_by)
        existing.approved_at = datetime.utcnow() if body.get("approved_by") else existing.approved_at
        if body.get("effective_from"):
            existing.effective_from = datetime.fromisoformat(body["effective_from"])
        if body.get("effective_to"):
            existing.effective_to = datetime.fromisoformat(body["effective_to"])
        db.commit()
        db.refresh(existing)
        return existing.to_dict()

    appetite = RiskAppetite(
        tenant_id=tenant_id,
        category=category,
        org_unit_id=org_unit_id,
        appetite_score=body["appetite_score"],
        tolerance_score=body["tolerance_score"],
        description=body.get("description"),
        approved_by=body.get("approved_by"),
        approved_at=datetime.utcnow() if body.get("approved_by") else None,
        effective_from=datetime.fromisoformat(body["effective_from"]) if body.get("effective_from") else None,
        effective_to=datetime.fromisoformat(body["effective_to"]) if body.get("effective_to") else None,
    )
    db.add(appetite)
    db.commit()
    db.refresh(appetite)
    return appetite.to_dict()


@router.get("/appetites")
def get_appetite(
    category: Optional[str] = Query(None),
    org_unit_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    q = db.query(RiskAppetite).filter(RiskAppetite.tenant_id == tenant_id)
    if category:
        q = q.filter(RiskAppetite.category == category)
    if org_unit_id is not None:
        q = q.filter(RiskAppetite.org_unit_id == org_unit_id)
    appetites = q.all()
    return {"total": len(appetites), "appetites": [a.to_dict() for a in appetites]}


@router.get("/risks/{risk_id}/appetite-check")
def check_appetite_breach(
    risk_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """
    Check whether a risk's residual score breaches its appetite / tolerance thresholds.

    XL-A enhancement: also checks system_indicated_residual (the control-coverage-adjusted
    score computed by recompute-coverage) against the same appetite thresholds.
    The 'indicated_status' field shows whether the coverage-adjusted score would breach
    appetite even when the assessor's residual_score does not — an early-warning signal
    for when control failures are eroding the assumed risk position.
    """
    risk = _risk_or_404(db, risk_id, tenant_id)
    appetite = db.query(RiskAppetite).filter(
        RiskAppetite.tenant_id == tenant_id,
        RiskAppetite.category == risk.category.value,
    ).first()
    if not appetite:
        appetite = db.query(RiskAppetite).filter(
            RiskAppetite.tenant_id == tenant_id,
            RiskAppetite.category == "all",
        ).first()

    residual = risk.residual_score or 0.0
    result = {
        "risk_id": risk_id,
        "risk_title": risk.title,
        "residual_score": residual,
        "appetite_score": appetite.appetite_score if appetite else None,
        "tolerance_score": appetite.tolerance_score if appetite else None,
        "appetite_breach": False,
        "tolerance_breach": False,
        "status": "within_appetite",
        # XL-A: coverage-adjusted fields
        "control_coverage": risk.control_coverage,
        "system_indicated_residual": risk.system_indicated_residual,
        "coverage_computed_at": risk.coverage_computed_at.isoformat() if risk.coverage_computed_at else None,
        "indicated_appetite_breach": False,
        "indicated_tolerance_breach": False,
        "indicated_status": "unknown" if risk.system_indicated_residual is None else "within_appetite",
    }
    if appetite:
        if residual > appetite.tolerance_score:
            result["tolerance_breach"] = True
            result["appetite_breach"] = True
            result["status"] = "tolerance_breach"
        elif residual > appetite.appetite_score:
            result["appetite_breach"] = True
            result["status"] = "appetite_breach"

        # XL-A: evaluate system_indicated_residual against same thresholds
        if risk.system_indicated_residual is not None:
            indicated = risk.system_indicated_residual
            if indicated > appetite.tolerance_score:
                result["indicated_tolerance_breach"] = True
                result["indicated_appetite_breach"] = True
                result["indicated_status"] = "tolerance_breach"
            elif indicated > appetite.appetite_score:
                result["indicated_appetite_breach"] = True
                result["indicated_status"] = "appetite_breach"
            else:
                result["indicated_status"] = "within_appetite"

    return result


# ===========================================================================
# KRIs  (RM-13)
# ===========================================================================

@router.post("/kris", status_code=201)
def create_kri(
    body: Dict[str, Any],
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    kri = KeyRiskIndicator(
        tenant_id=tenant_id,
        kri_id=body.get("kri_id") or _new_id("KRI"),
        name=body["name"],
        description=body.get("description"),
        risk_id=body.get("risk_id"),
        data_source=body.get("data_source", "manual"),
        unit_of_measure=body.get("unit_of_measure"),
        frequency=body.get("frequency", "monthly"),
        threshold_green=body.get("threshold_green"),
        threshold_amber=body.get("threshold_amber"),
        threshold_red=body.get("threshold_red"),
        owner_id=body.get("owner_id"),
        is_active=True,
        status=KRIStatus.NORMAL,
    )
    db.add(kri)
    db.commit()
    db.refresh(kri)
    return kri.to_dict()


@router.get("/kris/dashboard")
def get_kri_dashboard(
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """KRI traffic-light dashboard."""
    kris = db.query(KeyRiskIndicator).filter(
        KeyRiskIndicator.tenant_id == tenant_id,
        KeyRiskIndicator.is_active.is_(True),
    ).all()

    normal = warning = breach = 0
    items = []
    for k in kris:
        current_status = _kri_status(k)
        if current_status == KRIStatus.NORMAL.value:
            normal += 1
        elif current_status == KRIStatus.WARNING.value:
            warning += 1
        else:
            breach += 1
        d = k.to_dict()
        d["current_status"] = current_status
        items.append(d)

    return {
        "total_kris": len(kris),
        "normal": normal,
        "warning": warning,
        "breach": breach,
        "kris": items,
    }


@router.post("/kris/{kri_id}/measurements", status_code=201)
def record_kri_measurement(
    kri_id: str,
    body: Dict[str, Any],
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    kri = _kri_or_404(db, kri_id, tenant_id)
    value = body["value"]
    m = KRIMeasurement(
        tenant_id=tenant_id,
        kri_id=kri.id,
        value=value,
        measured_at=datetime.utcnow(),
        measured_by=body.get("measured_by", "manual"),
        source=body.get("source", "manual"),
        notes=body.get("notes"),
    )
    db.add(m)
    # Update current value and status
    kri.current_value = value
    kri.last_measured_at = datetime.utcnow()
    kri.status = KRIStatus(_kri_status(kri))
    db.commit()
    db.refresh(m)
    return {
        "measurement": m.to_dict(),
        "kri_status": kri.status.value,
    }


@router.get("/kris/{kri_id}/history")
def get_kri_history(
    kri_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    kri = _kri_or_404(db, kri_id, tenant_id)
    measurements = db.query(KRIMeasurement).filter(
        KRIMeasurement.kri_id == kri.id,
        KRIMeasurement.tenant_id == tenant_id,
    ).order_by(KRIMeasurement.measured_at.desc()).all()
    return {
        "kri_id": kri_id,
        "kri_name": kri.name,
        "total_measurements": len(measurements),
        "measurements": [m.to_dict() for m in measurements],
    }


# ===========================================================================
# Risk Responses  (RM-20)
# ===========================================================================

@router.post("/risks/{risk_id}/responses", status_code=201)
def create_response(
    risk_id: str,
    body: Dict[str, Any],
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    risk = _risk_or_404(db, risk_id, tenant_id)
    try:
        response_type = RiskResponseType(body.get("response_type", "mitigate"))
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid response_type")
    resp = RiskResponse(
        tenant_id=tenant_id,
        response_id=_new_id("RESP"),
        risk_id=risk.id,
        response_type=response_type,
        description=body.get("description"),
        owner_id=body.get("owner_id"),
        owner_name=body.get("owner_name"),
        actions=body.get("actions", []),
        status=ResponseStatus.PLANNED,
        due_date=datetime.fromisoformat(body["due_date"]) if body.get("due_date") else None,
    )
    db.add(resp)
    db.commit()
    db.refresh(resp)
    return resp.to_dict()


@router.get("/risks/{risk_id}/responses")
def get_risk_responses(
    risk_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    risk = _risk_or_404(db, risk_id, tenant_id)
    responses = db.query(RiskResponse).filter(
        RiskResponse.risk_id == risk.id,
        RiskResponse.tenant_id == tenant_id,
    ).all()
    return {"total": len(responses), "responses": [r.to_dict() for r in responses]}


@router.put("/responses/{response_id}/status")
def update_response_status(
    response_id: str,
    body: Dict[str, Any],
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    resp = _response_or_404(db, response_id, tenant_id)
    try:
        resp.status = ResponseStatus(body["status"])
    except (KeyError, ValueError):
        raise HTTPException(status_code=400, detail="Missing or invalid 'status'")
    if resp.status == ResponseStatus.COMPLETED:
        resp.completed_at = datetime.utcnow()
    if "effectiveness_rating" in body:
        resp.effectiveness_rating = body["effectiveness_rating"]
    db.commit()
    db.refresh(resp)
    return resp.to_dict()


# ===========================================================================
# Incidents  (RM-22)
# ===========================================================================

@router.post("/incidents", status_code=201)
def report_incident(
    body: Dict[str, Any],
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    try:
        severity = IncidentSeverity(body.get("severity", "medium"))
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid severity")
    inc = RiskIncident(
        tenant_id=tenant_id,
        incident_id=_new_id("INC"),
        title=body["title"],
        description=body.get("description"),
        severity=severity,
        financial_impact=body.get("financial_impact"),
        currency=body.get("currency", "USD"),
        occurred_at=datetime.fromisoformat(body["occurred_at"]) if body.get("occurred_at") else None,
        detected_at=datetime.utcnow(),
        reported_by=body.get("reported_by"),
        root_cause=body.get("root_cause"),
        corrective_actions=body.get("corrective_actions", []),
        status=IncidentStatus.REPORTED,
    )
    db.add(inc)
    db.commit()
    db.refresh(inc)
    return inc.to_dict()


@router.put("/incidents/{incident_id}")
def update_incident(
    incident_id: str,
    body: Dict[str, Any],
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    inc = _incident_or_404(db, incident_id, tenant_id)
    for field in ["title", "description", "root_cause", "corrective_actions", "financial_impact"]:
        if field in body:
            setattr(inc, field, body[field])
    if "status" in body:
        inc.status = IncidentStatus(body["status"])
        if inc.status == IncidentStatus.RESOLVED:
            inc.resolved_at = datetime.utcnow()
    if "severity" in body:
        inc.severity = IncidentSeverity(body["severity"])
    db.commit()
    db.refresh(inc)
    return inc.to_dict()


@router.get("/incidents")
def get_incidents(
    status: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    q = db.query(RiskIncident).filter(RiskIncident.tenant_id == tenant_id)
    if status:
        q = q.filter(RiskIncident.status == IncidentStatus(status))
    if severity:
        q = q.filter(RiskIncident.severity == IncidentSeverity(severity))
    incidents = q.order_by(RiskIncident.created_at.desc()).all()
    return {"total": len(incidents), "incidents": [i.to_dict() for i in incidents]}


@router.post("/incidents/{incident_id}/link-risk")
def link_incident_to_risk(
    incident_id: str,
    body: Dict[str, Any],
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    inc = _incident_or_404(db, incident_id, tenant_id)
    risk = _risk_or_404(db, body["risk_id"], tenant_id)
    inc.risk_id = risk.id
    db.commit()
    return {"incident_id": incident_id, "linked_risk_id": body["risk_id"], "success": True}


# ===========================================================================
# Reporting  (RM-25..RM-31)
# ===========================================================================

@router.get("/heatmap")
def get_risk_heatmap(
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """5x5 risk heatmap — counts of risks per (likelihood, impact) cell."""
    risks = db.query(EnterpriseRisk).filter(
        EnterpriseRisk.tenant_id == tenant_id,
        EnterpriseRisk.is_active.is_(True),
    ).all()

    cells: Dict[str, int] = {}
    unscored = 0
    for r in risks:
        l_val = r.residual_likelihood or r.inherent_likelihood
        i_val = r.residual_impact or r.inherent_impact
        if l_val and i_val:
            key = f"{l_val}_{i_val}"
            cells[key] = cells.get(key, 0) + 1
        else:
            unscored += 1

    heatmap = []
    for likelihood in range(1, 6):
        for impact in range(1, 6):
            heatmap.append({
                "likelihood": likelihood,
                "impact": impact,
                "score": likelihood * impact,
                "count": cells.get(f"{likelihood}_{impact}", 0),
                "zone": (
                    "critical" if likelihood * impact >= 20
                    else "high" if likelihood * impact >= 12
                    else "medium" if likelihood * impact >= 6
                    else "low"
                ),
            })

    return {
        "total_risks": len(risks),
        "unscored": unscored,
        "heatmap": heatmap,
    }


@router.get("/trends")
def get_risk_trends(
    period_months: int = Query(default=12),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Risk score trends by month over the requested period."""
    cutoff = datetime.utcnow() - timedelta(days=period_months * 30)
    assessments = db.query(RiskAssessment).filter(
        RiskAssessment.tenant_id == tenant_id,
        RiskAssessment.created_at >= cutoff,
    ).order_by(RiskAssessment.created_at).all()

    # Bucket by year-month
    buckets: Dict[str, List[float]] = {}
    for a in assessments:
        if a.created_at:
            key = a.created_at.strftime("%Y-%m")
            buckets.setdefault(key, []).append(a.overall_score)

    trend = [
        {"month": month, "avg_score": round(sum(scores) / len(scores), 2), "count": len(scores)}
        for month, scores in sorted(buckets.items())
    ]
    return {"period_months": period_months, "trend": trend}


@router.get("/top-risks")
def get_top_risks(
    limit: int = Query(default=10),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Top risks by residual score."""
    risks = db.query(EnterpriseRisk).filter(
        EnterpriseRisk.tenant_id == tenant_id,
        EnterpriseRisk.is_active.is_(True),
    ).order_by(EnterpriseRisk.residual_score.desc().nullslast()).limit(limit).all()
    return {"top_risks": [r.to_dict() for r in risks]}


@router.get("/risk-control-coverage")
def get_risk_control_coverage(
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Percentage of risks that have at least one linked control."""
    risks = db.query(EnterpriseRisk).filter(
        EnterpriseRisk.tenant_id == tenant_id,
        EnterpriseRisk.is_active.is_(True),
    ).all()
    total = len(risks)
    covered = sum(1 for r in risks if r.related_control_ids)
    return {
        "total_risks": total,
        "covered": covered,
        "uncovered": total - covered,
        "coverage_pct": round(covered / total * 100, 1) if total else 0,
    }


@router.get("/overdue-reviews")
def get_overdue_reviews(
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Risks whose next_review_date has passed."""
    now = datetime.utcnow()
    overdue = db.query(EnterpriseRisk).filter(
        EnterpriseRisk.tenant_id == tenant_id,
        EnterpriseRisk.is_active.is_(True),
        EnterpriseRisk.next_review_date < now,
    ).all()
    return {"total_overdue": len(overdue), "risks": [r.to_dict() for r in overdue]}


@router.post("/risks/{risk_id}/review-attestation")
def record_review_attestation(
    risk_id: str,
    body: Dict[str, Any],
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Record that a risk has been reviewed and advance its next_review_date."""
    risk = _risk_or_404(db, risk_id, tenant_id)
    risk.last_assessed_at = datetime.utcnow()
    freq = risk.review_frequency or "quarterly"
    delta_map = {"monthly": 30, "quarterly": 90, "semi_annual": 180, "annual": 365}
    days = delta_map.get(freq, 90)
    risk.next_review_date = datetime.utcnow() + timedelta(days=days)
    risk.risk_owner_id = body.get("attested_by", risk.risk_owner_id)
    db.commit()
    return {
        "risk_id": risk_id,
        "attested_by": body.get("attested_by"),
        "attested_at": datetime.utcnow().isoformat(),
        "next_review_date": risk.next_review_date.isoformat(),
    }
