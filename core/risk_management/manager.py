"""
Risk Management Manager

Full business logic for the Risk Management module (RM-01 through RM-31).

Uses the per-tenant factory pattern: constructor takes tenant_id + db_session;
all DB queries are filtered by tenant_id.  No in-memory caching — every call
hits the database directly so data is always current.

Covered feature areas:
  RM-01  Risk Register        (create_risk, update_risk, get_risk, list_risks, delete_risk)
  RM-03  Risk Appetite        (set_appetite, get_appetite, check_appetite_breach)
  RM-10  Risk Assessment      (create_assessment, submit_assessment, review_assessment,
                               get_risk_assessments, run_assessment_campaign)
  RM-11  Assessment workflow  (submit_assessment, review_assessment)
  RM-12  Heat Map             (get_risk_heatmap)
  RM-13  KRI Management       (create_kri, record_kri_measurement, get_kri_dashboard,
                               get_kri_history)
  RM-20  Risk Response        (create_response, update_response_status, get_risk_responses)
  RM-22  Incident Management  (report_incident, update_incident, link_incident_to_risk,
                               get_incidents)
  RM-23  Review Cycles        (get_overdue_reviews, record_review_attestation)
  RM-30  Trends               (get_risk_trends)
  RM-31  Control Coverage     (get_risk_control_coverage)
  Extra  Top Risks            (get_top_risks)
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import uuid4

from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_

from db.models.risk_management import (
    EnterpriseRisk,
    RiskAssessment,
    RiskAppetite,
    KeyRiskIndicator,
    KRIMeasurement,
    RiskResponse,
    RiskIncident,
    RiskCategory,
    RiskStatus,
    AssessmentType,
    AssessmentStatus,
    KRIStatus,
    RiskResponseType,
    ResponseStatus,
    IncidentSeverity,
    IncidentStatus,
)
from db.models.grc_foundation import OrgUnit

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# ID generators
# ---------------------------------------------------------------------------

def _make_risk_id() -> str:
    return f"RSK-{uuid4().hex[:8].upper()}"

def _make_assessment_id() -> str:
    return f"ASS-{uuid4().hex[:8].upper()}"

def _make_kri_id() -> str:
    return f"KRI-{uuid4().hex[:8].upper()}"

def _make_response_id() -> str:
    return f"RSP-{uuid4().hex[:8].upper()}"

def _make_incident_id() -> str:
    return f"INC-{uuid4().hex[:8].upper()}"

def _make_campaign_id() -> str:
    return f"CAM-{uuid4().hex[:8].upper()}"


# ---------------------------------------------------------------------------
# Helper: safe enum coercion
# ---------------------------------------------------------------------------

def _coerce_enum(enum_cls, value, default=None):
    """Return enum member for *value* string, or *default* on failure."""
    if value is None:
        return default
    if isinstance(value, enum_cls):
        return value
    try:
        return enum_cls(value)
    except (ValueError, KeyError):
        return default


# ---------------------------------------------------------------------------
# Manager
# ---------------------------------------------------------------------------

class RiskManagementManager:
    """
    Per-tenant Risk Management business logic manager.

    Instantiate once per request / per tenant via the per-tenant factory
    pattern used elsewhere in this codebase:

        manager = RiskManagementManager(tenant_id=tenant_id, db=db_session)

    All methods raise ValueError for bad IDs, PermissionError where access is
    denied, and propagate SQLAlchemy exceptions on DB failures.
    """

    def __init__(self, tenant_id: str, db: Session) -> None:
        if not tenant_id:
            raise ValueError("tenant_id is required")
        if db is None:
            raise ValueError("db session is required")
        self._tenant_id = tenant_id
        self._db = db

    # =========================================================================
    # Internal query helpers (always tenant-scoped)
    # =========================================================================

    def _risk_q(self):
        """Base query for EnterpriseRisk scoped to this tenant."""
        return self._db.query(EnterpriseRisk).filter(
            EnterpriseRisk.tenant_id == self._tenant_id,
            EnterpriseRisk.is_active == True,
        )

    def _assessment_q(self):
        return self._db.query(RiskAssessment).filter(
            RiskAssessment.tenant_id == self._tenant_id
        )

    def _appetite_q(self):
        return self._db.query(RiskAppetite).filter(
            RiskAppetite.tenant_id == self._tenant_id
        )

    def _kri_q(self):
        return self._db.query(KeyRiskIndicator).filter(
            KeyRiskIndicator.tenant_id == self._tenant_id,
            KeyRiskIndicator.is_active == True,
        )

    def _measurement_q(self):
        return self._db.query(KRIMeasurement).filter(
            KRIMeasurement.tenant_id == self._tenant_id
        )

    def _response_q(self):
        return self._db.query(RiskResponse).filter(
            RiskResponse.tenant_id == self._tenant_id
        )

    def _incident_q(self):
        return self._db.query(RiskIncident).filter(
            RiskIncident.tenant_id == self._tenant_id
        )

    def _get_risk_by_risk_id(self, risk_id: str) -> EnterpriseRisk:
        """Fetch an active EnterpriseRisk by its business risk_id or raise."""
        row = self._risk_q().filter(EnterpriseRisk.risk_id == risk_id).first()
        if not row:
            raise ValueError(f"Risk '{risk_id}' not found for this tenant")
        return row

    def _get_assessment_by_id(self, assessment_id: str) -> RiskAssessment:
        row = self._assessment_q().filter(
            RiskAssessment.assessment_id == assessment_id
        ).first()
        if not row:
            raise ValueError(f"Assessment '{assessment_id}' not found")
        return row

    def _get_kri_by_kri_id(self, kri_id: str) -> KeyRiskIndicator:
        row = self._kri_q().filter(KeyRiskIndicator.kri_id == kri_id).first()
        if not row:
            raise ValueError(f"KRI '{kri_id}' not found")
        return row

    def _get_response_by_id(self, response_id: str) -> RiskResponse:
        row = self._response_q().filter(
            RiskResponse.response_id == response_id
        ).first()
        if not row:
            raise ValueError(f"Response '{response_id}' not found")
        return row

    def _get_incident_by_id(self, incident_id: str) -> RiskIncident:
        row = self._incident_q().filter(
            RiskIncident.incident_id == incident_id
        ).first()
        if not row:
            raise ValueError(f"Incident '{incident_id}' not found")
        return row

    # =========================================================================
    # RM-01  Risk Register
    # =========================================================================

    def create_risk(self, data: dict) -> dict:
        """
        Create a new enterprise risk in the risk register (RM-01).

        Required keys in *data*:
          title (str), category (str — RiskCategory value)

        Optional keys:
          description, description_ar, org_unit_id, risk_owner_id,
          risk_owner_name, inherent_likelihood (1-5), inherent_impact (1-5),
          residual_likelihood (1-5), residual_impact (1-5),
          risk_appetite, risk_tolerance, status, review_frequency,
          next_review_date (ISO str), related_control_ids (list),
          related_finding_ids (list), metadata
        """
        title = data.get("title", "").strip()
        if not title:
            raise ValueError("'title' is required to create a risk")

        category = _coerce_enum(RiskCategory, data.get("category"), RiskCategory.OPERATIONAL)

        inherent_likelihood = data.get("inherent_likelihood")
        inherent_impact = data.get("inherent_impact")
        inherent_score = None
        if inherent_likelihood is not None and inherent_impact is not None:
            inherent_score = float(inherent_likelihood) * float(inherent_impact)

        residual_likelihood = data.get("residual_likelihood")
        residual_impact = data.get("residual_impact")
        residual_score = None
        if residual_likelihood is not None and residual_impact is not None:
            residual_score = float(residual_likelihood) * float(residual_impact)

        next_review_raw = data.get("next_review_date")
        next_review_date = None
        if next_review_raw:
            try:
                next_review_date = datetime.fromisoformat(str(next_review_raw))
            except (ValueError, TypeError):
                pass

        risk = EnterpriseRisk(
            tenant_id=self._tenant_id,
            risk_id=_make_risk_id(),
            title=title,
            description=data.get("description"),
            description_ar=data.get("description_ar"),
            category=category,
            org_unit_id=data.get("org_unit_id"),
            risk_owner_id=data.get("risk_owner_id"),
            risk_owner_name=data.get("risk_owner_name"),
            inherent_likelihood=inherent_likelihood,
            inherent_impact=inherent_impact,
            inherent_score=inherent_score,
            residual_likelihood=residual_likelihood,
            residual_impact=residual_impact,
            residual_score=residual_score,
            risk_appetite=data.get("risk_appetite"),
            risk_tolerance=data.get("risk_tolerance"),
            status=_coerce_enum(RiskStatus, data.get("status"), RiskStatus.IDENTIFIED),
            review_frequency=data.get("review_frequency"),
            next_review_date=next_review_date,
            related_control_ids=data.get("related_control_ids") or [],
            related_finding_ids=data.get("related_finding_ids") or [],
            metadata_=data.get("metadata") or data.get("metadata_"),
            is_active=True,
        )

        self._db.add(risk)
        self._db.flush()

        logger.info(
            "Risk created: %s | tenant=%s | title=%s",
            risk.risk_id, self._tenant_id, title,
        )
        return risk.to_dict()

    def update_risk(self, risk_id: str, data: dict) -> dict:
        """
        Update mutable fields of an existing enterprise risk.

        Only keys present in *data* are updated; omitted keys are left unchanged.
        Scores are recalculated when their component fields are updated.
        """
        risk = self._get_risk_by_risk_id(risk_id)

        if "title" in data:
            risk.title = data["title"]
        if "description" in data:
            risk.description = data["description"]
        if "description_ar" in data:
            risk.description_ar = data["description_ar"]
        if "category" in data:
            risk.category = _coerce_enum(RiskCategory, data["category"], risk.category)
        if "org_unit_id" in data:
            risk.org_unit_id = data["org_unit_id"]
        if "risk_owner_id" in data:
            risk.risk_owner_id = data["risk_owner_id"]
        if "risk_owner_name" in data:
            risk.risk_owner_name = data["risk_owner_name"]
        if "status" in data:
            risk.status = _coerce_enum(RiskStatus, data["status"], risk.status)
        if "review_frequency" in data:
            risk.review_frequency = data["review_frequency"]
        if "next_review_date" in data:
            try:
                risk.next_review_date = datetime.fromisoformat(str(data["next_review_date"]))
            except (ValueError, TypeError):
                pass
        if "related_control_ids" in data:
            risk.related_control_ids = data["related_control_ids"]
        if "related_finding_ids" in data:
            risk.related_finding_ids = data["related_finding_ids"]
        if "risk_appetite" in data:
            risk.risk_appetite = data["risk_appetite"]
        if "risk_tolerance" in data:
            risk.risk_tolerance = data["risk_tolerance"]
        if "metadata" in data:
            risk.metadata_ = data["metadata"]

        # Recompute inherent score if components touched
        for field in ("inherent_likelihood", "inherent_impact"):
            if field in data:
                setattr(risk, field, data[field])
        if risk.inherent_likelihood is not None and risk.inherent_impact is not None:
            risk.inherent_score = float(risk.inherent_likelihood) * float(risk.inherent_impact)

        # Recompute residual score if components touched
        for field in ("residual_likelihood", "residual_impact"):
            if field in data:
                setattr(risk, field, data[field])
        if risk.residual_likelihood is not None and risk.residual_impact is not None:
            risk.residual_score = float(risk.residual_likelihood) * float(risk.residual_impact)

        self._db.flush()

        logger.info("Risk updated: %s | tenant=%s", risk_id, self._tenant_id)
        return risk.to_dict()

    def get_risk(self, risk_id: str) -> dict:
        """Return a single enterprise risk by its business risk_id."""
        return self._get_risk_by_risk_id(risk_id).to_dict()

    def list_risks(self, filters: Optional[dict] = None) -> list:
        """
        List enterprise risks with optional filtering.

        Supported filter keys:
          category (str), org_unit_id (int), status (str),
          owner (str — matched against risk_owner_id),
          search (str — partial match on title/description),
          limit (int, default 200), offset (int, default 0)
        """
        q = self._risk_q()
        f = filters or {}

        if "category" in f:
            cat = _coerce_enum(RiskCategory, f["category"])
            if cat:
                q = q.filter(EnterpriseRisk.category == cat)

        if "org_unit_id" in f and f["org_unit_id"] is not None:
            q = q.filter(EnterpriseRisk.org_unit_id == int(f["org_unit_id"]))

        if "status" in f:
            st = _coerce_enum(RiskStatus, f["status"])
            if st:
                q = q.filter(EnterpriseRisk.status == st)

        if "owner" in f and f["owner"]:
            q = q.filter(EnterpriseRisk.risk_owner_id == f["owner"])

        if "search" in f and f["search"]:
            term = f"%{f['search']}%"
            q = q.filter(
                or_(
                    EnterpriseRisk.title.ilike(term),
                    EnterpriseRisk.description.ilike(term),
                )
            )

        limit = int(f.get("limit", 200))
        offset = int(f.get("offset", 0))
        q = q.order_by(EnterpriseRisk.created_at.desc()).offset(offset).limit(limit)

        return [r.to_dict() for r in q.all()]

    def delete_risk(self, risk_id: str) -> bool:
        """
        Soft-delete an enterprise risk (sets is_active=False).

        Returns True if the risk was found and deactivated.
        """
        risk = self._get_risk_by_risk_id(risk_id)
        risk.is_active = False
        self._db.flush()
        logger.info("Risk soft-deleted: %s | tenant=%s", risk_id, self._tenant_id)
        return True

    # =========================================================================
    # RM-10, RM-11  Risk Assessment
    # =========================================================================

    def create_assessment(self, risk_id: str, data: dict) -> dict:
        """
        Create a new risk assessment for an existing enterprise risk (RM-10).

        Inherent/residual scores are calculated as likelihood * impact.

        Required keys in *data*:
          likelihood_score (int 1-5), impact_score (int 1-5)

        Optional keys:
          assessor_id, assessor_name, assessment_type (periodic/adhoc/consensus),
          likelihood_rationale, impact_rationale, monetary_impact, currency,
          comments
        """
        risk = self._get_risk_by_risk_id(risk_id)

        likelihood = int(data.get("likelihood_score", 3))
        impact = int(data.get("impact_score", 3))
        if not (1 <= likelihood <= 5):
            raise ValueError("likelihood_score must be between 1 and 5")
        if not (1 <= impact <= 5):
            raise ValueError("impact_score must be between 1 and 5")

        overall_score = float(likelihood * impact)

        assessment = RiskAssessment(
            tenant_id=self._tenant_id,
            assessment_id=_make_assessment_id(),
            risk_id=risk.id,
            assessor_id=data.get("assessor_id"),
            assessor_name=data.get("assessor_name"),
            likelihood_score=likelihood,
            impact_score=impact,
            overall_score=overall_score,
            assessment_type=_coerce_enum(
                AssessmentType, data.get("assessment_type"), AssessmentType.PERIODIC
            ),
            likelihood_rationale=data.get("likelihood_rationale"),
            impact_rationale=data.get("impact_rationale"),
            monetary_impact=data.get("monetary_impact"),
            currency=data.get("currency", "USD"),
            status=AssessmentStatus.DRAFT,
            comments=data.get("comments"),
        )

        self._db.add(assessment)

        # Update parent risk last_assessed timestamp and scores
        risk.last_assessed_at = datetime.utcnow()
        risk.inherent_likelihood = likelihood
        risk.inherent_impact = impact
        risk.inherent_score = overall_score
        risk.status = RiskStatus.ASSESSED

        self._db.flush()

        logger.info(
            "Assessment created: %s for risk %s | tenant=%s",
            assessment.assessment_id, risk_id, self._tenant_id,
        )
        return assessment.to_dict()

    def submit_assessment(self, assessment_id: str) -> dict:
        """
        Transition an assessment from DRAFT to SUBMITTED (RM-11).

        Only DRAFT assessments can be submitted.
        """
        assessment = self._get_assessment_by_id(assessment_id)
        if assessment.status != AssessmentStatus.DRAFT:
            raise ValueError(
                f"Assessment '{assessment_id}' is in status "
                f"'{assessment.status.value}' — only DRAFT assessments can be submitted"
            )
        assessment.status = AssessmentStatus.SUBMITTED
        self._db.flush()
        logger.info("Assessment submitted: %s | tenant=%s", assessment_id, self._tenant_id)
        return assessment.to_dict()

    def review_assessment(
        self, assessment_id: str, reviewer_id: str, data: dict
    ) -> dict:
        """
        Record a reviewer's decision on a submitted assessment (RM-11).

        Transitions assessment to REVIEWED or APPROVED based on *data['action']*.

        Required keys in *data*:
          action (str — 'review' | 'approve')

        Optional keys:
          comments (str), residual_likelihood (int 1-5), residual_impact (int 1-5)
        """
        assessment = self._get_assessment_by_id(assessment_id)
        if assessment.status not in (AssessmentStatus.SUBMITTED, AssessmentStatus.REVIEWED):
            raise ValueError(
                f"Assessment '{assessment_id}' must be SUBMITTED or REVIEWED to be reviewed/approved"
            )

        action = str(data.get("action", "review")).lower()
        if action not in ("review", "approve"):
            raise ValueError("'action' must be 'review' or 'approve'")

        assessment.reviewed_by = reviewer_id
        assessment.reviewed_at = datetime.utcnow()
        assessment.comments = data.get("comments", assessment.comments)
        assessment.status = (
            AssessmentStatus.APPROVED if action == "approve" else AssessmentStatus.REVIEWED
        )

        # Optionally update residual scores on the parent risk
        if action == "approve":
            risk = self._db.query(EnterpriseRisk).filter(
                EnterpriseRisk.id == assessment.risk_id,
                EnterpriseRisk.tenant_id == self._tenant_id,
            ).first()
            if risk:
                rl = data.get("residual_likelihood")
                ri = data.get("residual_impact")
                if rl is not None:
                    risk.residual_likelihood = int(rl)
                if ri is not None:
                    risk.residual_impact = int(ri)
                if risk.residual_likelihood and risk.residual_impact:
                    risk.residual_score = float(
                        risk.residual_likelihood * risk.residual_impact
                    )

        self._db.flush()
        logger.info(
            "Assessment %s %s by %s | tenant=%s",
            assessment_id, assessment.status.value, reviewer_id, self._tenant_id,
        )
        return assessment.to_dict()

    def get_risk_assessments(self, risk_id: str) -> list:
        """Return all assessments for a given risk, ordered newest first."""
        risk = self._get_risk_by_risk_id(risk_id)
        rows = (
            self._assessment_q()
            .filter(RiskAssessment.risk_id == risk.id)
            .order_by(RiskAssessment.created_at.desc())
            .all()
        )
        return [r.to_dict() for r in rows]

    def run_assessment_campaign(self, campaign_config: dict) -> dict:
        """
        Batch-create assessments for multiple risks in one campaign (RM-10).

        *campaign_config* keys:
          risk_ids (list[str])          — specific risk_ids to assess; if omitted,
                                          all active risks for the tenant are used
          filters (dict)                — list_risks-compatible filters applied when
                                          risk_ids is not provided
          assessor_id (str)
          assessor_name (str)
          assessment_type (str)         — default 'periodic'
          default_likelihood (int 1-5)  — applied when a risk has no prior score
          default_impact (int 1-5)
          comments (str)

        Returns a campaign summary dict with created assessment IDs and any errors.
        """
        campaign_id = _make_campaign_id()
        assessor_id = campaign_config.get("assessor_id", "system")
        assessor_name = campaign_config.get("assessor_name", "Campaign System")
        assessment_type = campaign_config.get("assessment_type", "periodic")
        default_likelihood = int(campaign_config.get("default_likelihood", 3))
        default_impact = int(campaign_config.get("default_impact", 3))
        comments = campaign_config.get("comments", f"Campaign {campaign_id}")

        # Resolve which risks to assess
        explicit_ids: List[str] = campaign_config.get("risk_ids") or []
        if explicit_ids:
            risks = (
                self._risk_q()
                .filter(EnterpriseRisk.risk_id.in_(explicit_ids))
                .all()
            )
        else:
            filters = campaign_config.get("filters") or {}
            risks_dicts = self.list_risks(filters)
            risk_ids_resolved = [r["risk_id"] for r in risks_dicts]
            risks = (
                self._risk_q()
                .filter(EnterpriseRisk.risk_id.in_(risk_ids_resolved))
                .all()
            )

        created: List[str] = []
        errors: List[dict] = []

        for risk in risks:
            try:
                likelihood = int(risk.inherent_likelihood or default_likelihood)
                impact = int(risk.inherent_impact or default_impact)
                likelihood = max(1, min(5, likelihood))
                impact = max(1, min(5, impact))

                assessment = RiskAssessment(
                    tenant_id=self._tenant_id,
                    assessment_id=_make_assessment_id(),
                    risk_id=risk.id,
                    assessor_id=assessor_id,
                    assessor_name=assessor_name,
                    likelihood_score=likelihood,
                    impact_score=impact,
                    overall_score=float(likelihood * impact),
                    assessment_type=_coerce_enum(
                        AssessmentType, assessment_type, AssessmentType.PERIODIC
                    ),
                    status=AssessmentStatus.DRAFT,
                    comments=comments,
                    currency="USD",
                )
                self._db.add(assessment)
                risk.last_assessed_at = datetime.utcnow()
                created.append(assessment.assessment_id)
            except Exception as exc:
                errors.append({"risk_id": risk.risk_id, "error": str(exc)})

        self._db.flush()

        logger.info(
            "Assessment campaign %s: %d created, %d errors | tenant=%s",
            campaign_id, len(created), len(errors), self._tenant_id,
        )
        return {
            "campaign_id": campaign_id,
            "total_risks": len(risks),
            "created_count": len(created),
            "error_count": len(errors),
            "assessment_ids": created,
            "errors": errors,
            "created_at": datetime.utcnow().isoformat(),
        }

    # =========================================================================
    # RM-03  Risk Appetite
    # =========================================================================

    def set_appetite(self, data: dict) -> dict:
        """
        Create or update the risk appetite for a category/org-unit pair (RM-03).

        Required keys:
          category (str), appetite_score (float), tolerance_score (float)

        Optional keys:
          org_unit_id (int), description (str),
          approved_by (str), effective_from (ISO str), effective_to (ISO str)

        If a matching record already exists (same tenant + category + org_unit_id)
        it is updated in-place; otherwise a new record is created.
        """
        category = data.get("category", "").strip()
        if not category:
            raise ValueError("'category' is required")

        appetite_score = data.get("appetite_score")
        tolerance_score = data.get("tolerance_score")
        if appetite_score is None or tolerance_score is None:
            raise ValueError("'appetite_score' and 'tolerance_score' are required")

        org_unit_id = data.get("org_unit_id")

        q = self._appetite_q().filter(RiskAppetite.category == category)
        if org_unit_id is not None:
            q = q.filter(RiskAppetite.org_unit_id == int(org_unit_id))
        else:
            q = q.filter(RiskAppetite.org_unit_id == None)  # noqa: E711

        existing = q.first()

        def _parse_dt(val):
            if val is None:
                return None
            try:
                return datetime.fromisoformat(str(val))
            except (ValueError, TypeError):
                return None

        if existing:
            existing.appetite_score = float(appetite_score)
            existing.tolerance_score = float(tolerance_score)
            if "description" in data:
                existing.description = data["description"]
            if "approved_by" in data:
                existing.approved_by = data["approved_by"]
                existing.approved_at = datetime.utcnow()
            if "effective_from" in data:
                existing.effective_from = _parse_dt(data["effective_from"])
            if "effective_to" in data:
                existing.effective_to = _parse_dt(data["effective_to"])
            self._db.flush()
            logger.info(
                "Risk appetite updated: category=%s | tenant=%s", category, self._tenant_id
            )
            return existing.to_dict()

        appetite = RiskAppetite(
            tenant_id=self._tenant_id,
            category=category,
            org_unit_id=int(org_unit_id) if org_unit_id is not None else None,
            appetite_score=float(appetite_score),
            tolerance_score=float(tolerance_score),
            description=data.get("description"),
            approved_by=data.get("approved_by"),
            approved_at=datetime.utcnow() if data.get("approved_by") else None,
            effective_from=_parse_dt(data.get("effective_from")),
            effective_to=_parse_dt(data.get("effective_to")),
        )
        self._db.add(appetite)
        self._db.flush()
        logger.info(
            "Risk appetite created: category=%s | tenant=%s", category, self._tenant_id
        )
        return appetite.to_dict()

    def get_appetite(
        self, category: str, org_unit_id: Optional[int] = None
    ) -> dict:
        """
        Return the risk appetite record for a category/org-unit combination (RM-03).

        Lookup precedence:
          1. Exact match on category + org_unit_id
          2. Fallback to category-level record (org_unit_id IS NULL)
          3. Fallback to 'all' category record if no category-specific one found

        Raises ValueError if no appetite record exists.
        """
        def _fetch(cat, ou_id):
            q = self._appetite_q().filter(RiskAppetite.category == cat)
            if ou_id is not None:
                q = q.filter(RiskAppetite.org_unit_id == int(ou_id))
            else:
                q = q.filter(RiskAppetite.org_unit_id == None)  # noqa: E711
            return q.first()

        # 1. Exact match
        row = _fetch(category, org_unit_id)
        if row:
            return row.to_dict()

        # 2. Category-level fallback (no org_unit)
        if org_unit_id is not None:
            row = _fetch(category, None)
            if row:
                return row.to_dict()

        # 3. Global 'all' fallback
        row = _fetch("all", None)
        if row:
            return row.to_dict()

        raise ValueError(
            f"No risk appetite defined for category='{category}' "
            f"(org_unit_id={org_unit_id}) in this tenant"
        )

    def check_appetite_breach(self, risk_id: str) -> dict:
        """
        Compare the risk's current residual score against the appetite threshold (RM-03).

        XL-A enhancement: also evaluates system_indicated_residual (the control-coverage-
        adjusted score computed by recompute_control_coverage) against the same thresholds.
        The indicated_* fields surface an early-warning signal when control failures are
        eroding the assumed risk position without the assessor having yet updated residual_score.

        Returns a summary dict with:
          risk_id, residual_score, appetite_score, tolerance_score,
          within_appetite (bool), within_tolerance (bool), breach_level (str),
          control_coverage (str), system_indicated_residual (float|None),
          coverage_computed_at (str|None),
          indicated_within_appetite (bool|None), indicated_within_tolerance (bool|None),
          indicated_breach_level (str)
        """
        risk = self._get_risk_by_risk_id(risk_id)

        try:
            appetite = self.get_appetite(
                risk.category.value if risk.category else "all",
                risk.org_unit_id,
            )
        except ValueError:
            # No appetite defined — report as unknown
            return {
                "risk_id": risk_id,
                "residual_score": risk.residual_score,
                "appetite_score": None,
                "tolerance_score": None,
                "within_appetite": None,
                "within_tolerance": None,
                "breach_level": "unknown",
                "message": "No risk appetite defined for this category",
                # XL-A coverage fields still surfaced even with no appetite
                "control_coverage": risk.control_coverage,
                "system_indicated_residual": risk.system_indicated_residual,
                "coverage_computed_at": (
                    risk.coverage_computed_at.isoformat()
                    if risk.coverage_computed_at else None
                ),
                "indicated_within_appetite": None,
                "indicated_within_tolerance": None,
                "indicated_breach_level": "unknown",
            }

        residual = risk.residual_score or risk.inherent_score or 0.0
        appetite_score = appetite["appetite_score"]
        tolerance_score = appetite["tolerance_score"]

        within_appetite = residual <= appetite_score
        within_tolerance = residual <= tolerance_score

        if within_appetite:
            breach_level = "none"
        elif within_tolerance:
            breach_level = "appetite"  # above appetite but within tolerance
        else:
            breach_level = "tolerance"  # above tolerance — escalation required

        # XL-A: evaluate system_indicated_residual against the same thresholds
        indicated = risk.system_indicated_residual
        if indicated is not None:
            indicated_within_appetite = indicated <= appetite_score
            indicated_within_tolerance = indicated <= tolerance_score
            if indicated_within_appetite:
                indicated_breach_level = "none"
            elif indicated_within_tolerance:
                indicated_breach_level = "appetite"
            else:
                indicated_breach_level = "tolerance"
        else:
            indicated_within_appetite = None
            indicated_within_tolerance = None
            indicated_breach_level = "unknown"  # coverage not yet computed

        return {
            "risk_id": risk_id,
            "risk_title": risk.title,
            "category": risk.category.value if risk.category else None,
            "residual_score": residual,
            "appetite_score": appetite_score,
            "tolerance_score": tolerance_score,
            "within_appetite": within_appetite,
            "within_tolerance": within_tolerance,
            "breach_level": breach_level,
            # XL-A: control coverage feedback
            "control_coverage": risk.control_coverage,
            "system_indicated_residual": indicated,
            "coverage_computed_at": (
                risk.coverage_computed_at.isoformat()
                if risk.coverage_computed_at else None
            ),
            "indicated_within_appetite": indicated_within_appetite,
            "indicated_within_tolerance": indicated_within_tolerance,
            "indicated_breach_level": indicated_breach_level,
        }

    # =========================================================================
    # RM-13  KRI Management
    # =========================================================================

    def create_kri(self, data: dict) -> dict:
        """
        Create a new Key Risk Indicator definition (RM-13).

        Required keys:
          name (str)

        Optional keys:
          description (str), risk_id (str — EnterpriseRisk.risk_id),
          data_source (str), unit_of_measure (str), frequency (str),
          threshold_green (float), threshold_amber (float), threshold_red (float),
          owner_id (str)
        """
        name = data.get("name", "").strip()
        if not name:
            raise ValueError("'name' is required to create a KRI")

        # Resolve parent risk if provided
        parent_risk_pk = None
        if data.get("risk_id"):
            try:
                parent_risk = self._get_risk_by_risk_id(str(data["risk_id"]))
                parent_risk_pk = parent_risk.id
            except ValueError:
                pass  # KRI without a linked risk is valid

        kri = KeyRiskIndicator(
            tenant_id=self._tenant_id,
            kri_id=_make_kri_id(),
            name=name,
            description=data.get("description"),
            risk_id=parent_risk_pk,
            data_source=data.get("data_source"),
            unit_of_measure=data.get("unit_of_measure"),
            frequency=data.get("frequency"),
            threshold_green=data.get("threshold_green"),
            threshold_amber=data.get("threshold_amber"),
            threshold_red=data.get("threshold_red"),
            owner_id=data.get("owner_id"),
            status=KRIStatus.NORMAL,
            is_active=True,
        )

        self._db.add(kri)
        self._db.flush()

        logger.info(
            "KRI created: %s | tenant=%s | name=%s",
            kri.kri_id, self._tenant_id, name,
        )
        return kri.to_dict()

    def record_kri_measurement(
        self, kri_id: str, value: float, measured_by: str
    ) -> dict:
        """
        Record a new KRI measurement and auto-update the KRI's traffic-light
        status based on its configured thresholds (RM-13).

        Returns the updated KRI dict (not the raw measurement row).
        """
        kri = self._get_kri_by_kri_id(kri_id)

        measurement = KRIMeasurement(
            tenant_id=self._tenant_id,
            kri_id=kri.id,
            value=value,
            measured_at=datetime.utcnow(),
            measured_by=measured_by,
            source="manual",
        )
        self._db.add(measurement)

        # Update current value on KRI
        kri.current_value = value
        kri.last_measured_at = datetime.utcnow()

        # Auto-calculate traffic-light status based on thresholds
        # Convention: lower values are better (e.g. incident count, % overdue)
        # Thresholds: green < amber < red
        new_status = KRIStatus.NORMAL
        if kri.threshold_red is not None and value > kri.threshold_red:
            new_status = KRIStatus.BREACH
        elif kri.threshold_amber is not None and value > kri.threshold_amber:
            new_status = KRIStatus.WARNING
        elif kri.threshold_green is not None and value > kri.threshold_green:
            new_status = KRIStatus.WARNING
        else:
            new_status = KRIStatus.NORMAL

        # Also handle inverted metrics (higher is better) — if all thresholds
        # are in ascending order and value is below threshold_red, check whether
        # the user configured reversed thresholds (green > amber > red).
        # Detect reversed by checking green > red when both are set.
        if (
            kri.threshold_green is not None
            and kri.threshold_red is not None
            and kri.threshold_green > kri.threshold_red
        ):
            # Inverted metric (e.g. compliance %)
            if value < kri.threshold_red:
                new_status = KRIStatus.BREACH
            elif value < kri.threshold_amber:
                new_status = KRIStatus.WARNING
            else:
                new_status = KRIStatus.NORMAL

        previous_status = kri.status
        kri.status = new_status
        self._db.flush()

        # Alert on status transition to WARNING or BREACH
        if new_status in (KRIStatus.WARNING, KRIStatus.BREACH) and new_status != previous_status:
            alert_msg = (
                f"KRI '{kri.name}' (ID: {kri_id}) status changed to "
                f"{new_status.value.upper()} (value={value})"
            )
            logger.warning("KRI ALERT [tenant=%s]: %s", self._tenant_id, alert_msg)
            if new_status == KRIStatus.BREACH and kri.linked_risk_id:
                # Flag the linked risk for attention
                try:
                    linked_risk = (
                        self._risk_q()
                        .filter(EnterpriseRisk.id == kri.linked_risk_id)
                        .first()
                    )
                    if linked_risk and hasattr(linked_risk, 'flags'):
                        flags = list(linked_risk.flags or [])
                        flags.append({
                            "flag": "kri_breach",
                            "kri_id": kri_id,
                            "value": value,
                            "flagged_at": datetime.utcnow().isoformat(),
                        })
                        linked_risk.flags = flags
                        self._db.flush()
                except Exception as exc:
                    logger.warning("KRI BREACH flag on risk failed: %s", exc)

        logger.info(
            "KRI measurement recorded: kri=%s value=%s status=%s | tenant=%s",
            kri_id, value, new_status.value, self._tenant_id,
        )
        return {
            **kri.to_dict(),
            "measurement": measurement.to_dict(),
            "status_changed_to": new_status.value,
            "alert_triggered": new_status in (KRIStatus.WARNING, KRIStatus.BREACH) and new_status != previous_status,
        }

    def get_kri_dashboard(self) -> dict:
        """
        Return a summary dashboard of all active KRIs with their current
        status, grouped by traffic-light colour (RM-13).

        Dashboard shape:
          summary: {normal, warning, breach, total}
          by_status: {normal: [...], warning: [...], breach: [...]}
          stale_kris: [...] — KRIs not measured in the last 30 days
        """
        kris = self._kri_q().order_by(KeyRiskIndicator.name).all()

        summary = {"normal": 0, "warning": 0, "breach": 0, "total": len(kris)}
        by_status: Dict[str, list] = {"normal": [], "warning": [], "breach": []}
        stale: list = []
        stale_cutoff = datetime.utcnow() - timedelta(days=30)

        for kri in kris:
            status_key = kri.status.value if kri.status else "normal"
            summary[status_key] = summary.get(status_key, 0) + 1
            by_status.setdefault(status_key, []).append(kri.to_dict())

            if kri.last_measured_at is None or kri.last_measured_at < stale_cutoff:
                stale.append(kri.to_dict())

        return {
            "summary": summary,
            "by_status": by_status,
            "stale_kris": stale,
            "generated_at": datetime.utcnow().isoformat(),
        }

    def get_kri_history(self, kri_id: str) -> list:
        """
        Return all historical measurements for a KRI, ordered oldest to newest.
        """
        kri = self._get_kri_by_kri_id(kri_id)
        rows = (
            self._measurement_q()
            .filter(KRIMeasurement.kri_id == kri.id)
            .order_by(KRIMeasurement.measured_at.asc())
            .all()
        )
        return [r.to_dict() for r in rows]

    # =========================================================================
    # RM-20  Risk Response
    # =========================================================================

    def create_response(self, risk_id: str, data: dict) -> dict:
        """
        Create a risk response plan linked to an enterprise risk (RM-20).

        Required keys:
          response_type (str — accept/mitigate/transfer/avoid)

        Optional keys:
          description (str), owner_id (str), owner_name (str),
          due_date (ISO str), actions (list of action-item dicts)
        """
        risk = self._get_risk_by_risk_id(risk_id)

        response_type = _coerce_enum(
            RiskResponseType, data.get("response_type"), RiskResponseType.ACCEPT
        )

        due_date = None
        if data.get("due_date"):
            try:
                due_date = datetime.fromisoformat(str(data["due_date"]))
            except (ValueError, TypeError):
                pass

        response = RiskResponse(
            tenant_id=self._tenant_id,
            response_id=_make_response_id(),
            risk_id=risk.id,
            response_type=response_type,
            description=data.get("description"),
            owner_id=data.get("owner_id"),
            owner_name=data.get("owner_name"),
            actions=data.get("actions") or [],
            status=ResponseStatus.PLANNED,
            due_date=due_date,
        )

        self._db.add(response)
        self._db.flush()

        logger.info(
            "Risk response created: %s for risk %s | tenant=%s",
            response.response_id, risk_id, self._tenant_id,
        )
        return response.to_dict()

    def update_response_status(
        self, response_id: str, status: str, data: Optional[dict] = None
    ) -> dict:
        """
        Update the execution status of a risk response plan (RM-20).

        *status* must be a valid ResponseStatus value:
          planned, in_progress, completed, overdue

        Optional keys in *data*:
          actions (list), effectiveness_rating (int 1-5),
          completed_at (ISO str)
        """
        response = self._get_response_by_id(response_id)
        new_status = _coerce_enum(ResponseStatus, status)
        if new_status is None:
            raise ValueError(
                f"Invalid response status '{status}'. "
                f"Valid values: {[s.value for s in ResponseStatus]}"
            )
        response.status = new_status
        data = data or {}

        if "actions" in data:
            response.actions = data["actions"]
        if "effectiveness_rating" in data:
            rating = int(data["effectiveness_rating"])
            if not (1 <= rating <= 5):
                raise ValueError("effectiveness_rating must be between 1 and 5")
            response.effectiveness_rating = rating
        if new_status == ResponseStatus.COMPLETED:
            if data.get("completed_at"):
                try:
                    response.completed_at = datetime.fromisoformat(str(data["completed_at"]))
                except (ValueError, TypeError):
                    response.completed_at = datetime.utcnow()
            else:
                response.completed_at = datetime.utcnow()

        self._db.flush()
        logger.info(
            "Risk response %s status -> %s | tenant=%s",
            response_id, new_status.value, self._tenant_id,
        )
        return response.to_dict()

    def get_risk_responses(self, risk_id: str) -> list:
        """Return all response plans for a given risk, ordered newest first."""
        risk = self._get_risk_by_risk_id(risk_id)
        rows = (
            self._response_q()
            .filter(RiskResponse.risk_id == risk.id)
            .order_by(RiskResponse.created_at.desc())
            .all()
        )
        return [r.to_dict() for r in rows]

    # =========================================================================
    # RM-22  Incident Management
    # =========================================================================

    def report_incident(self, data: dict) -> dict:
        """
        Report a new risk incident / loss event (RM-22).

        Required keys:
          title (str), severity (str — low/medium/high/critical)

        Optional keys:
          description (str), risk_id (str — EnterpriseRisk.risk_id),
          financial_impact (float), currency (str),
          occurred_at (ISO str), detected_at (ISO str),
          root_cause (str), corrective_actions (list),
          reported_by (str)
        """
        title = data.get("title", "").strip()
        if not title:
            raise ValueError("'title' is required to report an incident")

        severity = _coerce_enum(IncidentSeverity, data.get("severity"), IncidentSeverity.MEDIUM)

        # Optionally link to a risk
        parent_risk_pk = None
        if data.get("risk_id"):
            try:
                parent_risk = self._get_risk_by_risk_id(str(data["risk_id"]))
                parent_risk_pk = parent_risk.id
            except ValueError:
                pass

        def _parse_dt(val):
            if val is None:
                return None
            try:
                return datetime.fromisoformat(str(val))
            except (ValueError, TypeError):
                return None

        incident = RiskIncident(
            tenant_id=self._tenant_id,
            incident_id=_make_incident_id(),
            title=title,
            description=data.get("description"),
            risk_id=parent_risk_pk,
            severity=severity,
            financial_impact=data.get("financial_impact"),
            currency=data.get("currency"),
            occurred_at=_parse_dt(data.get("occurred_at")),
            detected_at=_parse_dt(data.get("detected_at")) or datetime.utcnow(),
            root_cause=data.get("root_cause"),
            corrective_actions=data.get("corrective_actions") or [],
            reported_by=data.get("reported_by"),
            status=IncidentStatus.REPORTED,
        )

        self._db.add(incident)
        self._db.flush()

        logger.info(
            "Incident reported: %s | tenant=%s | severity=%s",
            incident.incident_id, self._tenant_id, severity.value,
        )
        return incident.to_dict()

    def update_incident(self, incident_id: str, data: dict) -> dict:
        """
        Update mutable fields of an existing incident (RM-22).

        Updatable keys:
          title, description, severity, status, financial_impact, currency,
          occurred_at, detected_at, resolved_at, root_cause,
          corrective_actions, reported_by
        """
        incident = self._get_incident_by_id(incident_id)

        def _parse_dt(val):
            if val is None:
                return None
            try:
                return datetime.fromisoformat(str(val))
            except (ValueError, TypeError):
                return None

        if "title" in data:
            incident.title = data["title"]
        if "description" in data:
            incident.description = data["description"]
        if "severity" in data:
            incident.severity = _coerce_enum(IncidentSeverity, data["severity"], incident.severity)
        if "status" in data:
            new_status = _coerce_enum(IncidentStatus, data["status"], incident.status)
            incident.status = new_status
            if new_status == IncidentStatus.RESOLVED and not incident.resolved_at:
                incident.resolved_at = datetime.utcnow()
        if "financial_impact" in data:
            incident.financial_impact = data["financial_impact"]
        if "currency" in data:
            incident.currency = data["currency"]
        if "occurred_at" in data:
            incident.occurred_at = _parse_dt(data["occurred_at"])
        if "detected_at" in data:
            incident.detected_at = _parse_dt(data["detected_at"])
        if "resolved_at" in data:
            incident.resolved_at = _parse_dt(data["resolved_at"])
        if "root_cause" in data:
            incident.root_cause = data["root_cause"]
        if "corrective_actions" in data:
            incident.corrective_actions = data["corrective_actions"]
        if "reported_by" in data:
            incident.reported_by = data["reported_by"]

        self._db.flush()
        logger.info("Incident updated: %s | tenant=%s", incident_id, self._tenant_id)
        return incident.to_dict()

    def link_incident_to_risk(self, incident_id: str, risk_id: str) -> dict:
        """
        Associate an existing incident with an enterprise risk (RM-22).

        Returns the updated incident dict.
        """
        incident = self._get_incident_by_id(incident_id)
        risk = self._get_risk_by_risk_id(risk_id)
        incident.risk_id = risk.id

        # Recalibrate inherent_likelihood upward due to incident occurrence (capped at 5)
        old_likelihood = risk.inherent_likelihood or 1
        new_likelihood = min(5, old_likelihood + 1)
        risk.inherent_likelihood = new_likelihood
        if risk.inherent_impact:
            risk.inherent_score = float(new_likelihood * risk.inherent_impact)

        self._db.flush()

        logger.info(
            "Incident %s linked to risk %s; inherent_likelihood recalibrated %d→%d | tenant=%s",
            incident_id, risk_id, old_likelihood, new_likelihood, self._tenant_id,
        )
        return {
            **incident.to_dict(),
            "recalibration": {
                "reason": "Incident occurrence",
                "field": "inherent_likelihood",
                "previous_value": old_likelihood,
                "new_value": new_likelihood,
                "new_inherent_score": risk.inherent_score,
            },
        }

    def get_incidents(self, filters: Optional[dict] = None) -> list:
        """
        List incidents with optional filtering.

        Filter keys:
          risk_id (str), severity (str), status (str),
          reported_by (str), limit (int), offset (int)
        """
        q = self._incident_q()
        f = filters or {}

        if "risk_id" in f and f["risk_id"]:
            try:
                risk = self._get_risk_by_risk_id(str(f["risk_id"]))
                q = q.filter(RiskIncident.risk_id == risk.id)
            except ValueError:
                return []  # risk not found → no incidents

        if "severity" in f:
            sev = _coerce_enum(IncidentSeverity, f["severity"])
            if sev:
                q = q.filter(RiskIncident.severity == sev)

        if "status" in f:
            st = _coerce_enum(IncidentStatus, f["status"])
            if st:
                q = q.filter(RiskIncident.status == st)

        if "reported_by" in f and f["reported_by"]:
            q = q.filter(RiskIncident.reported_by == f["reported_by"])

        limit = int(f.get("limit", 200))
        offset = int(f.get("offset", 0))
        q = q.order_by(RiskIncident.detected_at.desc()).offset(offset).limit(limit)

        return [r.to_dict() for r in q.all()]

    # =========================================================================
    # RM-12  Heat Map
    # =========================================================================

    def get_risk_heatmap(self, matrix_size: int = 5) -> dict:
        """
        Build a configurable NxN likelihood/impact heat-map matrix (RM-12).

        Parameters
        ----------
        matrix_size : int
            Grid size — 3, 4, or 5 (default 5). Zone thresholds scale proportionally.

        Returns:
          matrix: NxN list-of-lists; each cell contains risk dicts
          summary: {total, high_risk_count, critical_risk_count}
          axes: {x: [labels], y: [labels]}
        """
        # Validate and clamp matrix size
        if matrix_size not in (3, 4, 5):
            matrix_size = 5

        risks = self._risk_q().all()
        max_val = matrix_size  # scale 1..max_val

        # Zone thresholds scale with matrix size
        # In a 5x5: critical >= 15 (3x5), high >= 9 (3x3)
        # Scale proportionally: critical >= 60% of max_score, high >= 36%
        max_score = float(matrix_size * matrix_size)
        critical_threshold = max_score * 0.60
        high_threshold = max_score * 0.36

        matrix: List[List[list]] = [[[] for _ in range(max_val)] for _ in range(max_val)]
        high_count = 0
        critical_count = 0

        for risk in risks:
            likelihood = risk.residual_likelihood or risk.inherent_likelihood
            impact = risk.residual_impact or risk.inherent_impact

            if likelihood is None or impact is None:
                continue

            # Normalise to the target matrix size (original scores are 1-5)
            l_norm = max(1, min(max_val, round(float(likelihood) / 5.0 * max_val)))
            i_norm = max(1, min(max_val, round(float(impact) / 5.0 * max_val)))

            l_idx = l_norm - 1
            i_idx = i_norm - 1
            score = float(l_norm) * float(i_norm)

            cell_entry = {
                "risk_id": risk.risk_id,
                "title": risk.title,
                "score": score,
                "status": risk.status.value if risk.status else None,
                "category": risk.category.value if risk.category else None,
            }
            matrix[l_idx][i_idx].append(cell_entry)

            if score >= critical_threshold:
                critical_count += 1
            elif score >= high_threshold:
                high_count += 1

        axis_labels = [str(i + 1) for i in range(max_val)]
        return {
            "matrix": matrix,
            "matrix_size": matrix_size,
            "summary": {
                "total": len(risks),
                "high_risk_count": high_count,
                "critical_risk_count": critical_count,
            },
            "axes": {
                "x": axis_labels,  # impact (columns)
                "y": axis_labels,  # likelihood (rows)
            },
            "generated_at": datetime.utcnow().isoformat(),
        }

    # =========================================================================
    # RM-30  Risk Trends
    # =========================================================================

    def get_risk_trends(self, period_months: int = 12) -> dict:
        """
        Return risk score trends over the last *period_months* months (RM-30).

        Queries RiskAssessment records grouped by calendar month and computes:
          - average overall_score per month
          - count of assessments per month
          - average per category

        Returns:
          period_months (int)
          monthly_trend: list of {month, avg_score, assessment_count}
          by_category: dict of category → [monthly data points]
          generated_at (ISO str)
        """
        cutoff = datetime.utcnow() - timedelta(days=30 * period_months)

        assessments = (
            self._assessment_q()
            .filter(RiskAssessment.created_at >= cutoff)
            .order_by(RiskAssessment.created_at.asc())
            .all()
        )

        # Build monthly buckets: {YYYY-MM: {scores: [], by_category: {cat: []}}}
        monthly: Dict[str, Dict[str, Any]] = {}

        for assessment in assessments:
            month_key = assessment.created_at.strftime("%Y-%m")
            if month_key not in monthly:
                monthly[month_key] = {"scores": [], "by_category": {}}
            monthly[month_key]["scores"].append(assessment.overall_score)

            # Join to parent risk for category
            risk_row = self._db.query(EnterpriseRisk).filter(
                EnterpriseRisk.id == assessment.risk_id,
                EnterpriseRisk.tenant_id == self._tenant_id,
            ).first()
            if risk_row and risk_row.category:
                cat = risk_row.category.value
                monthly[month_key]["by_category"].setdefault(cat, []).append(
                    assessment.overall_score
                )

        monthly_trend = []
        by_category: Dict[str, list] = {}

        for month_key in sorted(monthly.keys()):
            bucket = monthly[month_key]
            scores = bucket["scores"]
            avg_score = sum(scores) / len(scores) if scores else 0.0
            monthly_trend.append(
                {
                    "month": month_key,
                    "avg_score": round(avg_score, 2),
                    "assessment_count": len(scores),
                }
            )
            for cat, cat_scores in bucket["by_category"].items():
                by_category.setdefault(cat, []).append(
                    {
                        "month": month_key,
                        "avg_score": round(
                            sum(cat_scores) / len(cat_scores), 2
                        ),
                        "count": len(cat_scores),
                    }
                )

        return {
            "period_months": period_months,
            "monthly_trend": monthly_trend,
            "by_category": by_category,
            "generated_at": datetime.utcnow().isoformat(),
        }

    # =========================================================================
    # Top Risks
    # =========================================================================

    def get_committee_report(self, fiscal_year: int = None) -> dict:
        """
        Return executive-formatted data for board/committee risk presentation (RM-13+).

        Includes:
          - Top 10 risks by residual score
          - Appetite breaches count
          - Risk movement (improved/deteriorated/unchanged)
          - KRI status summary (green/amber/red counts)
          - Open incidents count + total financial impact
          - Response plan progress

        Parameters
        ----------
        fiscal_year : int, optional
            If provided, filter assessments/incidents to that fiscal year.
        """
        now = datetime.utcnow()
        fy = fiscal_year or now.year
        fy_start = datetime(fy, 1, 1)
        fy_end = datetime(fy, 12, 31, 23, 59, 59)

        # Top 10 risks by residual score
        all_risks = (
            self._risk_q()
            .filter(EnterpriseRisk.status != RiskStatus.CLOSED)
            .all()
        )
        top_10 = sorted(
            all_risks,
            key=lambda r: float(r.residual_score or r.inherent_score or 0),
            reverse=True,
        )[:10]

        # Appetite breaches
        appetite_breach_count = 0
        try:
            from db.models.risk_management import RiskAppetite
            appetites = (
                self._db.query(RiskAppetite)
                .filter(RiskAppetite.tenant_id == self._tenant_id)
                .all()
            )
            for risk in all_risks:
                score = risk.residual_score or risk.inherent_score or 0
                for appetite in appetites:
                    cat = appetite.risk_category.value if hasattr(appetite.risk_category, 'value') else str(appetite.risk_category)
                    risk_cat = risk.category.value if hasattr(risk.category, 'value') else str(risk.category)
                    if cat == risk_cat and score > (appetite.max_score or 100):
                        appetite_breach_count += 1
                        break
        except Exception:
            pass

        # Risk movement: compare latest vs prior assessment overall_score
        improved = deteriorated = unchanged = 0
        for risk in all_risks:
            assessments = (
                self._db.query(RiskAssessment)
                .filter(
                    RiskAssessment.risk_id == risk.id,
                    RiskAssessment.tenant_id == self._tenant_id,
                )
                .order_by(RiskAssessment.created_at.desc())
                .limit(2)
                .all()
            )
            if len(assessments) >= 2:
                latest_score = assessments[0].overall_score or 0
                prior_score = assessments[1].overall_score or 0
                if latest_score < prior_score:
                    improved += 1
                elif latest_score > prior_score:
                    deteriorated += 1
                else:
                    unchanged += 1
            else:
                unchanged += 1

        # KRI status summary
        kri_green = kri_amber = kri_red = 0
        try:
            kris = self._kri_q().all()
            for kri in kris:
                status_val = kri.status.value if kri.status else "normal"
                if status_val == "normal":
                    kri_green += 1
                elif status_val == "warning":
                    kri_amber += 1
                elif status_val == "breach":
                    kri_red += 1
        except Exception:
            pass

        # Open incidents + financial impact
        open_incidents = (
            self._incident_q()
            .filter(
                RiskIncident.status != IncidentStatus.CLOSED,
                RiskIncident.detected_at >= fy_start,
                RiskIncident.detected_at <= fy_end,
            )
            .all()
        )
        total_financial_impact = sum(
            float(inc.financial_impact or 0) for inc in open_incidents
        )

        # Response plan progress
        all_responses = self._response_q().all()
        rsp_planned = sum(1 for r in all_responses if r.status == ResponseStatus.PLANNED)
        rsp_in_progress = sum(1 for r in all_responses if r.status == ResponseStatus.IN_PROGRESS)
        rsp_completed = sum(1 for r in all_responses if r.status == ResponseStatus.COMPLETED)

        return {
            "fiscal_year": fy,
            "generated_at": now.isoformat(),
            "top_10_risks": [
                {
                    "risk_id": r.risk_id,
                    "title": r.title,
                    "category": r.category.value if r.category else None,
                    "residual_score": r.residual_score,
                    "status": r.status.value if r.status else None,
                }
                for r in top_10
            ],
            "appetite_breaches": appetite_breach_count,
            "risk_movement": {
                "improved": improved,
                "deteriorated": deteriorated,
                "unchanged": unchanged,
            },
            "kri_summary": {
                "green": kri_green,
                "amber": kri_amber,
                "red": kri_red,
                "total": kri_green + kri_amber + kri_red,
            },
            "incidents": {
                "open_count": len(open_incidents),
                "total_financial_impact": total_financial_impact,
            },
            "response_plan_progress": {
                "planned": rsp_planned,
                "in_progress": rsp_in_progress,
                "completed": rsp_completed,
                "total": rsp_planned + rsp_in_progress + rsp_completed,
            },
        }

    def get_top_risks(self, limit: int = 10) -> list:
        """
        Return the top *limit* risks ranked by residual score (falling back to
        inherent score), filtered to active, non-closed risks.
        """
        risks = (
            self._risk_q()
            .filter(EnterpriseRisk.status != RiskStatus.CLOSED)
            .all()
        )

        def _score(r: EnterpriseRisk) -> float:
            return float(r.residual_score or r.inherent_score or 0)

        ranked = sorted(risks, key=_score, reverse=True)[:limit]
        return [r.to_dict() for r in ranked]

    # =========================================================================
    # XL-A  Control Coverage Feedback (Loop A)
    # =========================================================================

    def recompute_control_coverage(self, risk_id: str) -> dict:
        """
        XL-A: Compute control coverage signal from linked PC controls.

        Walks every control_id in risk.related_control_ids and examines:
          - Open ControlDeficiency records (material weakness → 'failed',
            significant deficiency / control gap → 'degraded')
          - Latest ControlTest result (ineffective → 'failed',
            partially_effective → 'degraded')

        Populates three fields on EnterpriseRisk WITHOUT touching the
        assessor-owned residual_score:
          control_coverage          : effective / degraded / failed / uncontrolled
          system_indicated_residual : residual_score amplified by a degradation
                                      factor, capped at inherent_score
          coverage_computed_at      : timestamp of this computation

        Returns the updated risk dict.
        """
        from db.models.process_control import (
            ProcessControl,
            ControlDeficiency,
            ControlTest,
            DeficiencyStatus,
            DeficiencySeverity,
            TestResult,
        )

        risk = self._get_risk_by_risk_id(risk_id)

        control_ids = risk.related_control_ids or []
        if not control_ids:
            risk.control_coverage = 'uncontrolled'
            risk.system_indicated_residual = risk.inherent_score  # no controls = inherent
            risk.coverage_computed_at = datetime.utcnow()
            self._db.commit()
            logger.info(
                "XL-A coverage: risk=%s → uncontrolled (no linked controls) | tenant=%s",
                risk_id, self._tenant_id,
            )
            return risk.to_dict()

        has_material_weakness = False
        has_significant = False

        for cid in control_ids:
            control = self._db.query(ProcessControl).filter(
                ProcessControl.tenant_id == self._tenant_id,
                ProcessControl.control_id == cid,
                ProcessControl.is_active == True,  # noqa: E712
            ).first()
            if not control:
                continue

            # Check open deficiencies on this control
            open_defs = self._db.query(ControlDeficiency).filter(
                ControlDeficiency.tenant_id == self._tenant_id,
                ControlDeficiency.control_id == control.id,
                ControlDeficiency.status.in_([
                    DeficiencyStatus.OPEN,
                    DeficiencyStatus.IN_REMEDIATION,
                ]),
            ).all()

            for d in open_defs:
                if d.severity == DeficiencySeverity.MATERIAL_WEAKNESS:
                    has_material_weakness = True
                elif d.severity in (
                    DeficiencySeverity.SIGNIFICANT_DEFICIENCY,
                    DeficiencySeverity.CONTROL_GAP,
                ):
                    has_significant = True

            # Check the most recent test result for this control
            latest_test = (
                self._db.query(ControlTest)
                .filter(
                    ControlTest.tenant_id == self._tenant_id,
                    ControlTest.control_id == control.id,
                )
                .order_by(ControlTest.created_at.desc())
                .first()
            )

            if latest_test and latest_test.result == TestResult.INEFFECTIVE:
                has_material_weakness = True
            elif latest_test and latest_test.result == TestResult.PARTIALLY_EFFECTIVE:
                has_significant = True

        # Determine coverage tier and amplification factor
        if has_material_weakness:
            coverage = 'failed'
            factor = 1.5
        elif has_significant:
            coverage = 'degraded'
            factor = 1.25
        else:
            coverage = 'effective'
            factor = 1.0

        base_residual = risk.residual_score or risk.inherent_score or 0.0
        inherent_cap = risk.inherent_score or 25.0
        risk.control_coverage = coverage
        risk.system_indicated_residual = min(base_residual * factor, inherent_cap)
        risk.coverage_computed_at = datetime.utcnow()
        self._db.commit()

        logger.info(
            "XL-A coverage: risk=%s → %s (factor=%.2f) system_indicated_residual=%.2f | tenant=%s",
            risk_id, coverage, factor, risk.system_indicated_residual, self._tenant_id,
        )
        return risk.to_dict()

    # =========================================================================
    # RM-31  Risk Control Coverage
    # =========================================================================

    def get_risk_control_coverage(self) -> dict:
        """
        Return a control coverage gap report (RM-31).

        Computes:
          risks_without_controls: risks with no entries in related_control_ids
          risks_without_responses: risks with no response plans
          orphaned_responses: response plans whose parent risk is closed/deleted
          coverage_pct: % of active risks that have at least one linked control
        """
        risks = self._risk_q().filter(
            EnterpriseRisk.status != RiskStatus.CLOSED
        ).all()

        risks_without_controls = []
        risks_without_responses = []

        for risk in risks:
            has_controls = bool(risk.related_control_ids)
            if not has_controls:
                risks_without_controls.append(risk.to_dict())

            # Check responses
            response_count = (
                self._response_q()
                .filter(
                    RiskResponse.risk_id == risk.id,
                    RiskResponse.status != ResponseStatus.COMPLETED,
                )
                .count()
            )
            if response_count == 0:
                risks_without_responses.append(risk.to_dict())

        total = len(risks)
        covered = total - len(risks_without_controls)
        coverage_pct = round((covered / total * 100) if total > 0 else 0.0, 1)

        # Orphaned responses: responses whose risk is inactive/closed
        all_responses = self._response_q().all()
        orphaned = []
        for resp in all_responses:
            risk_row = self._db.query(EnterpriseRisk).filter(
                EnterpriseRisk.id == resp.risk_id,
                EnterpriseRisk.tenant_id == self._tenant_id,
            ).first()
            if risk_row is None or not risk_row.is_active or risk_row.status == RiskStatus.CLOSED:
                orphaned.append(resp.to_dict())

        return {
            "total_active_risks": total,
            "risks_with_controls": covered,
            "coverage_pct": coverage_pct,
            "risks_without_controls": risks_without_controls,
            "risks_without_responses": risks_without_responses,
            "orphaned_responses": orphaned,
            "generated_at": datetime.utcnow().isoformat(),
        }

    # =========================================================================
    # RM-23  Review Cycles
    # =========================================================================

    def get_overdue_reviews(self) -> list:
        """
        Return all active risks whose next_review_date is in the past (RM-23).

        Results are ordered by how overdue they are (most overdue first).
        Each dict includes an 'overdue_days' field.
        """
        now = datetime.utcnow()
        overdue_rows = (
            self._risk_q()
            .filter(
                EnterpriseRisk.next_review_date != None,  # noqa: E711
                EnterpriseRisk.next_review_date < now,
                EnterpriseRisk.status != RiskStatus.CLOSED,
            )
            .order_by(EnterpriseRisk.next_review_date.asc())
            .all()
        )

        result = []
        for risk in overdue_rows:
            d = risk.to_dict()
            overdue_days = (now - risk.next_review_date).days
            d["overdue_days"] = overdue_days
            result.append(d)

        return result

    def record_review_attestation(
        self, risk_id: str, reviewer_id: str, data: dict
    ) -> dict:
        """
        Record that a risk has been reviewed and reschedule the next review (RM-23).

        Updates the risk's last_assessed_at, status, and next_review_date.
        Optionally updates inherent/residual scores if the reviewer provides
        fresh assessments.

        Required keys in *data*:
          (none — all keys are optional)

        Optional keys:
          comments (str), confirm_no_change (bool),
          inherent_likelihood (int 1-5), inherent_impact (int 1-5),
          residual_likelihood (int 1-5), residual_impact (int 1-5),
          new_status (str — RiskStatus value),
          next_review_date (ISO str)  — override automatic scheduling
        """
        risk = self._get_risk_by_risk_id(risk_id)

        risk.last_assessed_at = datetime.utcnow()

        # Update status if supplied
        if data.get("new_status"):
            risk.status = _coerce_enum(RiskStatus, data["new_status"], risk.status)

        # Refresh scoring if provided
        for field in ("inherent_likelihood", "inherent_impact", "residual_likelihood", "residual_impact"):
            if field in data and data[field] is not None:
                setattr(risk, field, int(data[field]))

        if risk.inherent_likelihood and risk.inherent_impact:
            risk.inherent_score = float(risk.inherent_likelihood * risk.inherent_impact)
        if risk.residual_likelihood and risk.residual_impact:
            risk.residual_score = float(risk.residual_likelihood * risk.residual_impact)

        # Reschedule next review
        if data.get("next_review_date"):
            try:
                risk.next_review_date = datetime.fromisoformat(
                    str(data["next_review_date"])
                )
            except (ValueError, TypeError):
                pass
        else:
            # Auto-advance based on review_frequency
            freq = (risk.review_frequency or "annual").lower()
            advance_days = {
                "daily": 1,
                "weekly": 7,
                "monthly": 30,
                "quarterly": 91,
                "semi-annual": 182,
                "annual": 365,
            }.get(freq, 365)
            risk.next_review_date = datetime.utcnow() + timedelta(days=advance_days)

        # Create a lightweight assessment record to capture the attestation
        attestation_assessment = RiskAssessment(
            tenant_id=self._tenant_id,
            assessment_id=_make_assessment_id(),
            risk_id=risk.id,
            assessor_id=reviewer_id,
            assessor_name=data.get("reviewer_name"),
            likelihood_score=risk.residual_likelihood or risk.inherent_likelihood or 3,
            impact_score=risk.residual_impact or risk.inherent_impact or 3,
            overall_score=float(
                (risk.residual_score or risk.inherent_score or 9)
            ),
            assessment_type=AssessmentType.PERIODIC,
            status=AssessmentStatus.APPROVED,
            reviewed_by=reviewer_id,
            reviewed_at=datetime.utcnow(),
            comments=data.get("comments", "Periodic review attestation"),
            currency="USD",
        )
        self._db.add(attestation_assessment)
        self._db.flush()

        logger.info(
            "Review attestation recorded: risk=%s reviewer=%s next_review=%s | tenant=%s",
            risk_id,
            reviewer_id,
            risk.next_review_date.isoformat() if risk.next_review_date else "N/A",
            self._tenant_id,
        )
        return {
            **risk.to_dict(),
            "attestation_assessment_id": attestation_assessment.assessment_id,
            "reviewed_by": reviewer_id,
            "reviewed_at": attestation_assessment.reviewed_at.isoformat(),
            "comments": attestation_assessment.comments,
        }
