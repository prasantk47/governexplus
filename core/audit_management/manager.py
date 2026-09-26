"""
Audit Management Manager

Full business logic for the Audit Management module (AM-01 through AM-31).

Covers:
  AM-01  Audit Universe (AuditableEntity CRUD + risk scoring)
  AM-02  Audit Planning (AuditPlan CRUD + approval workflow)
  AM-03  Auditor Resources (AuditorResource CRUD + availability)
  AM-04  Risk-Based Plan Generation
  AM-10  Engagement Management (AuditEngagement CRUD + status workflow)
  AM-11  Work Programs + Procedures
  AM-12  Workpapers (versioned)
  AM-13  Workpaper Review
  AM-14  Time Tracking
  AM-20  Findings with CCCE
  AM-21  Action Tracking
  AM-22  Management Response
  AM-30  Audit Reporting
  AM-31  Committee / Executive Reporting

Cross-module integrations:
  XI-03  Link findings to EnterpriseRisk, ProcessControl, RiskViolation
  XI-04  Entity risk score aggregation from RM + PC modules
"""

import logging
import uuid
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from db.models.audit_management import (
    ActionStatus,
    AuditEngagement,
    AuditFinding,
    AuditManagementAction,
    AuditPlan,
    AuditPlanStatus,
    AuditPlanType,
    AuditProcedure,
    AuditWorkpaper,
    AuditWorkProgram,
    AuditableEntity,
    AuditorResource,
    AuditorTimeEntry,
    EngagementStatus,
    FindingStatus,
    ProcedureStatus,
    WorkpaperReviewStatus,
    WorkpaperStatus,
)
from db.models.grc_foundation import OrgUnit
from db.models.process_control import ControlDeficiency, ProcessControl
from db.models.risk_management import EnterpriseRisk

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _gen_id(prefix: str) -> str:
    """Generate a short, readable unique ID with a given prefix."""
    return f"{prefix}-{uuid.uuid4().hex[:8].upper()}"


def _now() -> datetime:
    return datetime.utcnow()


def _parse_dt(value: Any) -> Optional[datetime]:
    """Coerce a string / datetime / None to datetime."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value))
    except (ValueError, TypeError):
        return None


# ---------------------------------------------------------------------------
# Engagement status workflow
# ---------------------------------------------------------------------------

_ENGAGEMENT_WORKFLOW = [
    EngagementStatus.PLANNED,
    EngagementStatus.ANNOUNCED,
    EngagementStatus.FIELDWORK,
    EngagementStatus.DRAFT_REPORT,
    EngagementStatus.FINAL_REPORT,
    EngagementStatus.CLOSED,
]


def _next_engagement_status(current: EngagementStatus) -> Optional[EngagementStatus]:
    try:
        idx = _ENGAGEMENT_WORKFLOW.index(current)
        return _ENGAGEMENT_WORKFLOW[idx + 1]
    except (ValueError, IndexError):
        return None


# ---------------------------------------------------------------------------
# Private utility
# ---------------------------------------------------------------------------

def _apply_fields(obj: Any, data: Dict, fields: List[str]) -> None:
    """
    Apply keys present in ``data`` to the corresponding attributes on ``obj``.

    Only writes a field if its key is present in data (does not overwrite
    with None if a key is absent).
    """
    for field in fields:
        if field in data:
            setattr(obj, field, data[field])


# ---------------------------------------------------------------------------
# Manager
# ---------------------------------------------------------------------------

class AuditManagementManager:
    """
    Central manager for internal audit business logic.

    Instantiated per-tenant; the tenant_id is stamped on every record
    created through this manager and used to scope every query.

    Parameters
    ----------
    tenant_id : str
        Tenant identifier used for row-level isolation.
    db : Session
        Active SQLAlchemy session.  All writes are flushed but the caller
        is responsible for committing / rolling back the transaction.
    """

    def __init__(self, tenant_id: str, db: Session) -> None:
        self.tenant_id = tenant_id
        self.db = db

    # =========================================================================
    # Internal query helpers
    # =========================================================================

    def _q(self, model):
        """Return a tenant-scoped base query for a model."""
        return self.db.query(model).filter(model.tenant_id == self.tenant_id)

    def _get_or_404(self, model, id_col_name: str, id_val: str):
        """
        Fetch a single row by its string identifier column or raise ValueError.
        """
        row = (
            self._q(model)
            .filter(getattr(model, id_col_name) == id_val)
            .first()
        )
        if row is None:
            raise ValueError(
                f"{model.__name__} '{id_val}' not found for tenant '{self.tenant_id}'"
            )
        return row

    # =========================================================================
    # 1. Audit Universe (AM-01)
    # =========================================================================

    def create_entity(self, data: Dict) -> Dict:
        """
        Create an AuditableEntity in the audit universe.

        Auto-generates entity_id in the format AE-XXXXXXXX.
        """
        entity = AuditableEntity(
            tenant_id=self.tenant_id,
            entity_id=_gen_id("AE"),
            name=data["name"],
            description=data.get("description"),
            entity_type=data["entity_type"],
            org_unit_id=data.get("org_unit_id"),
            risk_score=data.get("risk_score"),
            last_audited_at=_parse_dt(data.get("last_audited_at")),
            audit_frequency=data.get("audit_frequency"),
            primary_auditor_id=data.get("primary_auditor_id"),
            is_active=data.get("is_active", True),
            metadata_=data.get("metadata"),
        )
        self.db.add(entity)
        self.db.flush()
        logger.info(
            "Tenant %s: created AuditableEntity %s (%s)",
            self.tenant_id,
            entity.entity_id,
            entity.name,
        )
        return entity.to_dict()

    def update_entity(self, entity_id: str, data: Dict) -> Dict:
        """Update mutable fields on an AuditableEntity."""
        entity = self._get_or_404(AuditableEntity, "entity_id", entity_id)
        _apply_fields(
            entity,
            data,
            [
                "name",
                "description",
                "entity_type",
                "org_unit_id",
                "risk_score",
                "audit_frequency",
                "primary_auditor_id",
                "is_active",
            ],
        )
        if "last_audited_at" in data:
            entity.last_audited_at = _parse_dt(data["last_audited_at"])
        if "metadata" in data:
            entity.metadata_ = data["metadata"]
        self.db.flush()
        return entity.to_dict()

    def list_entities(self, filters: Optional[Dict] = None) -> List[Dict]:
        """
        Return all auditable entities for this tenant.

        Supported filter keys: ``is_active``, ``entity_type``, ``org_unit_id``.
        """
        q = self._q(AuditableEntity)
        filters = filters or {}
        if "is_active" in filters:
            q = q.filter(AuditableEntity.is_active == filters["is_active"])
        if "entity_type" in filters:
            q = q.filter(AuditableEntity.entity_type == filters["entity_type"])
        if "org_unit_id" in filters:
            q = q.filter(AuditableEntity.org_unit_id == filters["org_unit_id"])
        return [e.to_dict() for e in q.order_by(AuditableEntity.name).all()]

    def compute_entity_risk(self, entity_id: str) -> Dict:
        """
        Compute and persist a composite risk score for an auditable entity (XI-04).

        Aggregates:
        - Average residual_score from EnterpriseRisk rows for the entity's org_unit
        - Count of open ControlDeficiency rows for controls in the same org_unit
        - Count of open AuditFinding rows from prior engagements on this entity

        Returns a dict with component scores and the newly stored composite score.
        """
        entity = self._get_or_404(AuditableEntity, "entity_id", entity_id)
        org_unit_id = entity.org_unit_id

        # --- RM component: average residual risk score ---
        rm_avg = 0.0
        if org_unit_id:
            result = (
                self.db.query(func.avg(EnterpriseRisk.residual_score))
                .filter(
                    EnterpriseRisk.tenant_id == self.tenant_id,
                    EnterpriseRisk.org_unit_id == org_unit_id,
                    EnterpriseRisk.is_active == True,
                )
                .scalar()
            )
            rm_avg = float(result or 0.0)

        # --- PC component: count open control deficiencies for this org unit ---
        pc_deficiencies = 0
        if org_unit_id:
            pc_deficiencies = (
                self.db.query(func.count(ControlDeficiency.id))
                .join(
                    ProcessControl,
                    ControlDeficiency.control_id == ProcessControl.id,
                )
                .filter(
                    ProcessControl.tenant_id == self.tenant_id,
                    ProcessControl.org_unit_id == org_unit_id,
                    ControlDeficiency.tenant_id == self.tenant_id,
                    ControlDeficiency.status.in_(["open", "in_remediation"]),
                )
                .scalar()
                or 0
            )

        # --- AM component: open findings from prior engagements on this entity ---
        am_findings = (
            self.db.query(func.count(AuditFinding.id))
            .join(
                AuditEngagement,
                AuditFinding.engagement_id == AuditEngagement.id,
            )
            .filter(
                AuditEngagement.tenant_id == self.tenant_id,
                AuditEngagement.entity_id == entity.id,
                AuditFinding.tenant_id == self.tenant_id,
                AuditFinding.status != FindingStatus.CLOSED,
            )
            .scalar()
            or 0
        )

        # Composite: RM carries 60 %, PC deficiency density 25 %, open findings 15 %
        # Normalise deficiency / findings counts into a 0–25 score (cap at 10 items each)
        pc_score = min(pc_deficiencies, 10) * 2.5     # max 25
        am_score = min(am_findings, 10) * 1.5         # max 15
        composite = round((rm_avg * 0.6 * 25) + pc_score + am_score, 2)

        entity.risk_score = composite
        self.db.flush()

        return {
            "entity_id": entity_id,
            "rm_avg_residual_score": round(rm_avg, 3),
            "pc_open_deficiencies": pc_deficiencies,
            "am_open_findings": am_findings,
            "composite_risk_score": composite,
        }

    # Keep legacy name as an alias for backward compatibility
    def compute_entity_risk_score(self, entity_id: str) -> Dict:
        """Alias for compute_entity_risk — retained for backward compatibility."""
        return self.compute_entity_risk(entity_id)

    # =========================================================================
    # 2. Audit Planning (AM-02, AM-04)
    # =========================================================================

    def create_plan(self, data: Dict) -> Dict:
        """Create an AuditPlan in DRAFT status. Auto-generates plan_id."""
        plan = AuditPlan(
            tenant_id=self.tenant_id,
            plan_id=_gen_id("AP"),
            name=data["name"],
            description=data.get("description"),
            plan_type=data.get("plan_type", AuditPlanType.ANNUAL),
            fiscal_year=data["fiscal_year"],
            period_start=_parse_dt(data.get("period_start")),
            period_end=_parse_dt(data.get("period_end")),
            total_audit_hours=data.get("total_audit_hours"),
            allocated_budget=data.get("allocated_budget"),
            status=AuditPlanStatus.DRAFT,
            prepared_by=data.get("prepared_by"),
            risk_methodology=data.get("risk_methodology"),
            metadata_=data.get("metadata"),
        )
        self.db.add(plan)
        self.db.flush()
        logger.info(
            "Tenant %s: created AuditPlan %s (FY%s)",
            self.tenant_id,
            plan.plan_id,
            plan.fiscal_year,
        )
        return plan.to_dict()

    def get_plan(self, plan_id: str) -> Dict:
        """Fetch a single plan by its plan_id, with engagement count."""
        plan = self._get_or_404(AuditPlan, "plan_id", plan_id)
        result = plan.to_dict()
        result["engagement_count"] = (
            self._q(AuditEngagement)
            .filter(AuditEngagement.plan_id == plan.id)
            .count()
        )
        return result

    def list_plans(self, filters: Optional[Dict] = None) -> List[Dict]:
        """
        Return all audit plans for this tenant.

        Supported filter keys: ``status``, ``fiscal_year``, ``plan_type``.
        """
        q = self._q(AuditPlan)
        filters = filters or {}
        if "status" in filters:
            q = q.filter(AuditPlan.status == filters["status"])
        if "fiscal_year" in filters:
            q = q.filter(AuditPlan.fiscal_year == int(filters["fiscal_year"]))
        if "plan_type" in filters:
            q = q.filter(AuditPlan.plan_type == filters["plan_type"])
        plans = q.order_by(AuditPlan.fiscal_year.desc(), AuditPlan.name).all()
        results = []
        for p in plans:
            d = p.to_dict()
            d["engagement_count"] = (
                self._q(AuditEngagement)
                .filter(AuditEngagement.plan_id == p.id)
                .count()
            )
            results.append(d)
        return results

    def update_plan(self, plan_id: str, data: Dict) -> Dict:
        """Update a plan's mutable fields (only allowed while DRAFT or PENDING_APPROVAL)."""
        plan = self._get_or_404(AuditPlan, "plan_id", plan_id)
        if plan.status == AuditPlanStatus.APPROVED:
            raise ValueError(
                f"Plan '{plan_id}' is already approved and cannot be modified."
            )
        _apply_fields(
            plan,
            data,
            [
                "name",
                "description",
                "plan_type",
                "fiscal_year",
                "total_audit_hours",
                "allocated_budget",
                "prepared_by",
                "risk_methodology",
            ],
        )
        for dt_field in ("period_start", "period_end"):
            if dt_field in data:
                setattr(plan, dt_field, _parse_dt(data[dt_field]))
        if "metadata" in data:
            plan.metadata_ = data["metadata"]
        self.db.flush()
        return plan.to_dict()

    def submit_plan(self, plan_id: str) -> Dict:
        """Transition plan from DRAFT → PENDING_APPROVAL."""
        plan = self._get_or_404(AuditPlan, "plan_id", plan_id)
        if plan.status != AuditPlanStatus.DRAFT:
            raise ValueError(
                f"Plan '{plan_id}' must be in DRAFT status to submit for approval "
                f"(current: {plan.status.value})."
            )
        plan.status = AuditPlanStatus.PENDING_APPROVAL
        self.db.flush()
        logger.info("Tenant %s: plan %s submitted for approval.", self.tenant_id, plan_id)
        return plan.to_dict()

    # Backward-compat alias
    def submit_plan_for_approval(self, plan_id: str) -> Dict:
        """Alias for submit_plan — retained for backward compatibility."""
        return self.submit_plan(plan_id)

    def approve_plan(self, plan_id: str, approver_id: str) -> Dict:
        """Transition plan from PENDING_APPROVAL → APPROVED and record approver."""
        plan = self._get_or_404(AuditPlan, "plan_id", plan_id)
        if plan.status != AuditPlanStatus.PENDING_APPROVAL:
            raise ValueError(
                f"Plan '{plan_id}' must be in PENDING_APPROVAL to be approved "
                f"(current: {plan.status.value})."
            )
        plan.status = AuditPlanStatus.APPROVED
        plan.approved_by = approver_id
        plan.approved_at = _now()
        self.db.flush()
        logger.info(
            "Tenant %s: plan %s approved by %s.", self.tenant_id, plan_id, approver_id
        )
        return plan.to_dict()

    def generate_risk_based_plan(self, data: Dict) -> Dict:
        """
        Auto-generate an AuditPlan for the fiscal year given in ``data`` (AM-04).

        Selects the top-N auditable entities by risk_score, creates the plan,
        and creates one PLANNED AuditEngagement for each selected entity.

        Required key in ``data``:
            fiscal_year     (int)   Fiscal year for the plan

        Optional keys:
            name            (str)   Plan name (defaults to auto-generated)
            top_n           (int)   Number of entities to select (default 10)
            plan_type       (str)   AuditPlanType value (default 'annual')
            period_start    (str)   ISO date string
            period_end      (str)   ISO date string
            total_audit_hours (int)
            allocated_budget  (float)
            prepared_by     (str)
            risk_methodology (str)
            description     (str)
        """
        fiscal_year = int(data["fiscal_year"])
        top_n = int(data.get("top_n", 10))

        entities = (
            self._q(AuditableEntity)
            .filter(
                AuditableEntity.is_active == True,
                AuditableEntity.risk_score.isnot(None),
            )
            .order_by(AuditableEntity.risk_score.desc())
            .limit(top_n)
            .all()
        )

        plan_data = {
            "name": data.get(
                "name", f"Risk-Based Audit Plan FY{fiscal_year}"
            ),
            "description": data.get("description"),
            "plan_type": data.get("plan_type", AuditPlanType.ANNUAL),
            "fiscal_year": fiscal_year,
            "period_start": data.get("period_start"),
            "period_end": data.get("period_end"),
            "total_audit_hours": data.get("total_audit_hours"),
            "allocated_budget": data.get("allocated_budget"),
            "prepared_by": data.get("prepared_by"),
            "risk_methodology": data.get(
                "risk_methodology",
                "Risk-based selection: top entities by composite risk score (RM + PC + AM).",
            ),
        }
        plan_dict = self.create_plan(plan_data)
        plan = self._get_or_404(AuditPlan, "plan_id", plan_dict["plan_id"])

        engagements_created = []
        for entity in entities:
            eng = AuditEngagement(
                tenant_id=self.tenant_id,
                engagement_id=_gen_id("ENG"),
                plan_id=plan.id,
                entity_id=entity.id,
                title=f"Audit of {entity.name} – FY{fiscal_year}",
                objective=f"Review of {entity.name} driven by risk score {entity.risk_score}.",
                engagement_type="operational",
                status=EngagementStatus.PLANNED,
                risk_rating=(
                    "high"
                    if (entity.risk_score or 0) >= 15
                    else "medium"
                    if (entity.risk_score or 0) >= 8
                    else "low"
                ),
            )
            self.db.add(eng)
            engagements_created.append(entity.entity_id)

        self.db.flush()
        result = plan.to_dict()
        result["engagements_created_for_entities"] = engagements_created
        logger.info(
            "Tenant %s: generated risk-based plan %s with %d engagements.",
            self.tenant_id,
            plan.plan_id,
            len(engagements_created),
        )
        return result

    # =========================================================================
    # 3. Engagement Management (AM-10)
    # =========================================================================

    def create_engagement(self, data: Dict) -> Dict:
        """Create an AuditEngagement in PLANNED status. Auto-generates engagement_id."""
        # Resolve plan FK (optional)
        plan_pk = None
        if data.get("plan_id"):
            plan_row = (
                self._q(AuditPlan)
                .filter(AuditPlan.plan_id == data["plan_id"])
                .first()
            )
            if plan_row:
                plan_pk = plan_row.id

        # Resolve entity FK (optional)
        entity_pk = None
        if data.get("entity_id"):
            entity_row = (
                self._q(AuditableEntity)
                .filter(AuditableEntity.entity_id == data["entity_id"])
                .first()
            )
            if entity_row:
                entity_pk = entity_row.id

        eng = AuditEngagement(
            tenant_id=self.tenant_id,
            engagement_id=_gen_id("ENG"),
            plan_id=plan_pk,
            entity_id=entity_pk,
            title=data["title"],
            objective=data.get("objective"),
            scope=data.get("scope"),
            engagement_type=data["engagement_type"],
            status=EngagementStatus.PLANNED,
            lead_auditor_id=data.get("lead_auditor_id"),
            lead_auditor_name=data.get("lead_auditor_name"),
            team_members=data.get("team_members"),
            planned_start=_parse_dt(data.get("planned_start")),
            planned_end=_parse_dt(data.get("planned_end")),
            budget_hours=data.get("budget_hours"),
            risk_rating=data.get("risk_rating"),
            methodology=data.get("methodology"),
        )
        self.db.add(eng)
        self.db.flush()
        logger.info(
            "Tenant %s: created AuditEngagement %s ('%s').",
            self.tenant_id,
            eng.engagement_id,
            eng.title,
        )
        return eng.to_dict()

    def get_engagement(self, engagement_id: str) -> Dict:
        """
        Fetch an engagement with child counts (procedures, findings, workpapers).
        """
        eng = self._get_or_404(AuditEngagement, "engagement_id", engagement_id)
        result = eng.to_dict()
        result["procedure_count"] = (
            self._q(AuditProcedure)
            .filter(AuditProcedure.engagement_id == eng.id)
            .count()
        )
        result["finding_count"] = (
            self._q(AuditFinding)
            .filter(AuditFinding.engagement_id == eng.id)
            .count()
        )
        result["workpaper_count"] = (
            self._q(AuditWorkpaper)
            .filter(AuditWorkpaper.engagement_id == eng.id)
            .count()
        )
        return result

    def list_engagements(self, filters: Optional[Dict] = None) -> List[Dict]:
        """
        List engagements for this tenant.

        Supported filter keys: ``status``, ``plan_id`` (string plan_id),
        ``engagement_type``, ``lead_auditor_id``.
        """
        q = self._q(AuditEngagement)
        filters = filters or {}
        if "status" in filters:
            q = q.filter(AuditEngagement.status == filters["status"])
        if "engagement_type" in filters:
            q = q.filter(AuditEngagement.engagement_type == filters["engagement_type"])
        if "lead_auditor_id" in filters:
            q = q.filter(AuditEngagement.lead_auditor_id == filters["lead_auditor_id"])
        if "plan_id" in filters:
            plan_row = (
                self._q(AuditPlan)
                .filter(AuditPlan.plan_id == filters["plan_id"])
                .first()
            )
            if plan_row:
                q = q.filter(AuditEngagement.plan_id == plan_row.id)
        return [e.to_dict() for e in q.order_by(AuditEngagement.planned_start).all()]

    def update_engagement(self, engagement_id: str, data: Dict) -> Dict:
        """Update mutable fields on an engagement."""
        eng = self._get_or_404(AuditEngagement, "engagement_id", engagement_id)
        _apply_fields(
            eng,
            data,
            [
                "title",
                "objective",
                "scope",
                "engagement_type",
                "lead_auditor_id",
                "lead_auditor_name",
                "team_members",
                "budget_hours",
                "actual_hours",
                "risk_rating",
                "methodology",
            ],
        )
        for dt_field in ("planned_start", "planned_end", "actual_start", "actual_end"):
            if dt_field in data:
                setattr(eng, dt_field, _parse_dt(data[dt_field]))
        self.db.flush()
        return eng.to_dict()

    def advance_engagement(self, engagement_id: str) -> Dict:
        """
        Move an engagement to the next status in the lifecycle workflow:
        PLANNED → ANNOUNCED → FIELDWORK → DRAFT_REPORT → FINAL_REPORT → CLOSED.

        Sets actual_start when transitioning into FIELDWORK, actual_end when CLOSED.
        """
        eng = self._get_or_404(AuditEngagement, "engagement_id", engagement_id)
        next_status = _next_engagement_status(eng.status)
        if next_status is None:
            raise ValueError(
                f"Engagement '{engagement_id}' is already in terminal status "
                f"'{eng.status.value}'."
            )
        prev_status = eng.status
        eng.status = next_status

        if next_status == EngagementStatus.FIELDWORK and eng.actual_start is None:
            eng.actual_start = _now()
        if next_status == EngagementStatus.CLOSED and eng.actual_end is None:
            eng.actual_end = _now()

        self.db.flush()
        logger.info(
            "Tenant %s: engagement %s advanced %s → %s.",
            self.tenant_id,
            engagement_id,
            prev_status.value,
            next_status.value,
        )
        return eng.to_dict()

    # Backward-compat alias
    def advance_engagement_status(self, engagement_id: str) -> Dict:
        """Alias for advance_engagement — retained for backward compatibility."""
        return self.advance_engagement(engagement_id)

    # =========================================================================
    # 4. Work Programs (AM-11)
    # =========================================================================

    def create_work_program(self, data: Dict) -> Dict:
        """
        Create an AuditWorkProgram.

        Set ``is_template=True`` for reusable master templates; omit or set
        ``False`` for engagement-specific programs.
        """
        wp = AuditWorkProgram(
            tenant_id=self.tenant_id,
            program_id=_gen_id("WP"),
            name=data["name"],
            description=data.get("description"),
            audit_type=data.get("audit_type"),
            procedures=data.get("procedures"),
            is_template=data.get("is_template", False),
            version=data.get("version", 1),
        )
        self.db.add(wp)
        self.db.flush()
        logger.info(
            "Tenant %s: created AuditWorkProgram %s (template=%s).",
            self.tenant_id,
            wp.program_id,
            wp.is_template,
        )
        return wp.to_dict()

    def list_templates(self) -> List[Dict]:
        """Return all work program templates for this tenant."""
        return [
            wp.to_dict()
            for wp in self._q(AuditWorkProgram)
            .filter(AuditWorkProgram.is_template == True)
            .order_by(AuditWorkProgram.name)
            .all()
        ]

    def clone_work_program(self, program_id: str, engagement_id: str) -> Dict:
        """
        Clone a template work program into an engagement-specific copy (AM-11).

        The clone's is_template is set to False and its source_engagement_id
        is set to the resolved AuditEngagement PK.
        """
        template = self._get_or_404(AuditWorkProgram, "program_id", program_id)
        eng = self._get_or_404(AuditEngagement, "engagement_id", engagement_id)

        clone = AuditWorkProgram(
            tenant_id=self.tenant_id,
            program_id=_gen_id("WP"),
            name=f"{template.name} (copy)",
            description=template.description,
            audit_type=template.audit_type,
            procedures=template.procedures,
            is_template=False,
            source_engagement_id=eng.id,
            version=1,
        )
        self.db.add(clone)
        self.db.flush()
        logger.info(
            "Tenant %s: cloned work program %s → %s for engagement %s.",
            self.tenant_id,
            program_id,
            clone.program_id,
            engagement_id,
        )
        return clone.to_dict()

    # =========================================================================
    # 5. Procedures (AM-11 execution / AM-12)
    # =========================================================================

    def create_procedure(self, engagement_id: str, data: Dict) -> Dict:
        """Create an AuditProcedure within an engagement."""
        eng = self._get_or_404(AuditEngagement, "engagement_id", engagement_id)

        # Resolve optional work program FK
        wp_pk = None
        if data.get("work_program_id"):
            wp_row = (
                self._q(AuditWorkProgram)
                .filter(AuditWorkProgram.program_id == data["work_program_id"])
                .first()
            )
            if wp_row:
                wp_pk = wp_row.id

        proc = AuditProcedure(
            tenant_id=self.tenant_id,
            procedure_id=_gen_id("PROC"),
            engagement_id=eng.id,
            work_program_id=wp_pk,
            ref_number=data.get("ref_number"),
            title=data["title"],
            description=data.get("description"),
            assigned_to_id=data.get("assigned_to_id"),
            assigned_to_name=data.get("assigned_to_name"),
            status=ProcedureStatus.NOT_STARTED,
            hours_spent=data.get("hours_spent", 0.0),
            evidence_ids=data.get("evidence_ids"),
            cross_references=data.get("cross_references"),
        )
        self.db.add(proc)
        self.db.flush()
        return proc.to_dict()

    def list_procedures(self, engagement_id: str) -> List[Dict]:
        """List all procedures for an engagement."""
        eng = self._get_or_404(AuditEngagement, "engagement_id", engagement_id)
        return [
            p.to_dict()
            for p in self._q(AuditProcedure)
            .filter(AuditProcedure.engagement_id == eng.id)
            .order_by(AuditProcedure.ref_number)
            .all()
        ]

    def update_procedure(self, procedure_id: str, data: Dict) -> Dict:
        """Update mutable fields on a procedure."""
        proc = self._get_or_404(AuditProcedure, "procedure_id", procedure_id)
        _apply_fields(
            proc,
            data,
            [
                "ref_number",
                "title",
                "description",
                "assigned_to_id",
                "assigned_to_name",
                "hours_spent",
                "evidence_ids",
                "cross_references",
            ],
        )
        self.db.flush()
        return proc.to_dict()

    def complete_procedure(self, procedure_id: str, data: Dict) -> Dict:
        """
        Mark a procedure as COMPLETED with a preparer sign-off (AM-12).

        Required data keys: ``conclusion``, ``preparer_id``.
        Sets status → COMPLETED, records conclusion, preparer_id, and prepared_at.
        """
        proc = self._get_or_404(AuditProcedure, "procedure_id", procedure_id)
        proc.status = ProcedureStatus.COMPLETED
        proc.conclusion = data.get("conclusion", proc.conclusion)
        proc.preparer_id = data.get("preparer_id", proc.preparer_id)
        proc.prepared_at = _now()
        if "hours_spent" in data:
            proc.hours_spent = float(data["hours_spent"])
        self.db.flush()
        logger.info(
            "Tenant %s: procedure %s completed by %s.",
            self.tenant_id,
            procedure_id,
            proc.preparer_id,
        )
        return proc.to_dict()

    def review_procedure(self, procedure_id: str, reviewer_id: str, data: Dict) -> Dict:
        """
        Record a reviewer sign-off on a COMPLETED procedure (AM-12).

        Transitions status → REVIEWED. Accepts ``review_notes`` in data.
        """
        proc = self._get_or_404(AuditProcedure, "procedure_id", procedure_id)
        if proc.status not in (ProcedureStatus.COMPLETED, ProcedureStatus.REVIEWED):
            raise ValueError(
                f"Procedure '{procedure_id}' must be COMPLETED before it can be reviewed "
                f"(current: {proc.status.value})."
            )
        proc.status = ProcedureStatus.REVIEWED
        proc.reviewer_id = reviewer_id
        proc.reviewed_at = _now()
        proc.review_notes = data.get("review_notes", proc.review_notes)
        self.db.flush()
        return proc.to_dict()

    # =========================================================================
    # 6. Workpapers (AM-12, AM-13)
    # =========================================================================

    def create_workpaper(self, engagement_id: str, data: Dict) -> Dict:
        """Create an AuditWorkpaper in DRAFT status."""
        eng = self._get_or_404(AuditEngagement, "engagement_id", engagement_id)

        # Resolve optional procedure FK
        proc_pk = None
        if data.get("procedure_id"):
            proc_row = (
                self._q(AuditProcedure)
                .filter(AuditProcedure.procedure_id == data["procedure_id"])
                .first()
            )
            if proc_row:
                proc_pk = proc_row.id

        wp = AuditWorkpaper(
            tenant_id=self.tenant_id,
            workpaper_id=_gen_id("WPR"),
            engagement_id=eng.id,
            procedure_id=proc_pk,
            title=data["title"],
            description=data.get("description"),
            document_type=data.get("document_type"),
            file_name=data.get("file_name"),
            file_path=data.get("file_path"),
            file_size=data.get("file_size"),
            content=data.get("content"),
            version=1,
            preparer_id=data.get("preparer_id"),
            prepared_at=_parse_dt(data.get("prepared_at")),
            review_status=WorkpaperReviewStatus.PENDING_REVIEW,
            status=WorkpaperStatus.DRAFT,
            cross_references=data.get("cross_references"),
        )
        self.db.add(wp)
        self.db.flush()
        return wp.to_dict()

    def list_workpapers(self, engagement_id: str) -> List[Dict]:
        """List non-superseded workpapers for an engagement."""
        eng = self._get_or_404(AuditEngagement, "engagement_id", engagement_id)
        return [
            w.to_dict()
            for w in self._q(AuditWorkpaper)
            .filter(
                AuditWorkpaper.engagement_id == eng.id,
                AuditWorkpaper.status != WorkpaperStatus.SUPERSEDED,
            )
            .order_by(AuditWorkpaper.title)
            .all()
        ]

    def update_workpaper(self, workpaper_id: str, data: Dict) -> Dict:
        """
        Update a workpaper, creating a new version (AM-12).

        The current record is superseded; a new row is created with
        version N+1 and previous_version_id pointing to the old row.
        """
        old = self._get_or_404(AuditWorkpaper, "workpaper_id", workpaper_id)

        # Supersede the old version
        old.status = WorkpaperStatus.SUPERSEDED
        self.db.flush()

        new_wp = AuditWorkpaper(
            tenant_id=self.tenant_id,
            workpaper_id=_gen_id("WPR"),
            engagement_id=old.engagement_id,
            procedure_id=old.procedure_id,
            title=data.get("title", old.title),
            description=data.get("description", old.description),
            document_type=data.get("document_type", old.document_type),
            file_name=data.get("file_name", old.file_name),
            file_path=data.get("file_path", old.file_path),
            file_size=data.get("file_size", old.file_size),
            content=data.get("content", old.content),
            version=old.version + 1,
            previous_version_id=old.id,
            preparer_id=data.get("preparer_id", old.preparer_id),
            prepared_at=_parse_dt(data.get("prepared_at")) or old.prepared_at,
            review_status=WorkpaperReviewStatus.PENDING_REVIEW,
            status=WorkpaperStatus.DRAFT,
            cross_references=data.get("cross_references", old.cross_references),
        )
        self.db.add(new_wp)
        self.db.flush()
        logger.info(
            "Tenant %s: workpaper %s superseded; new version %s (v%d).",
            self.tenant_id,
            workpaper_id,
            new_wp.workpaper_id,
            new_wp.version,
        )
        return new_wp.to_dict()

    def submit_for_review(self, workpaper_id: str) -> Dict:
        """
        Set the workpaper's review_status to PENDING_REVIEW (AM-13).

        Idempotent — safe to call if already pending.
        """
        wp = self._get_or_404(AuditWorkpaper, "workpaper_id", workpaper_id)
        wp.review_status = WorkpaperReviewStatus.PENDING_REVIEW
        self.db.flush()
        return wp.to_dict()

    def review_workpaper(self, workpaper_id: str, reviewer_id: str, data: Dict) -> Dict:
        """
        Record a reviewer decision on a workpaper (AM-13).

        ``data`` should contain:
            decision  (str)  'approved' | 'revision_needed'
            note      (str)  Optional review note
        """
        wp = self._get_or_404(AuditWorkpaper, "workpaper_id", workpaper_id)
        decision = data.get("decision", "approved").lower()

        if decision == "revision_needed":
            wp.review_status = WorkpaperReviewStatus.REVISION_NEEDED
        else:
            wp.review_status = WorkpaperReviewStatus.REVIEWED
            wp.status = WorkpaperStatus.FINAL
            wp.reviewer_id = reviewer_id
            wp.reviewed_at = _now()

        # Append note to review_notes JSON list
        note_entry = {
            "reviewer_id": reviewer_id,
            "decision": decision,
            "note": data.get("note"),
            "timestamp": _now().isoformat(),
        }
        wp.review_notes = (wp.review_notes or []) + [note_entry]
        self.db.flush()
        return wp.to_dict()

    # =========================================================================
    # 7. Findings with CCCE (AM-20, AM-22, AM-23)
    # =========================================================================

    def create_finding(self, engagement_id: str, data: Dict) -> Dict:
        """
        Create a formal AuditFinding with CCCE structure (AM-20).

        Required data keys: ``title``, ``severity``.
        CCCE keys: ``condition``, ``criteria``, ``cause``, ``effect``.
        """
        eng = self._get_or_404(AuditEngagement, "engagement_id", engagement_id)

        proc_pk = None
        if data.get("procedure_id"):
            proc_row = (
                self._q(AuditProcedure)
                .filter(AuditProcedure.procedure_id == data["procedure_id"])
                .first()
            )
            if proc_row:
                proc_pk = proc_row.id

        finding = AuditFinding(
            tenant_id=self.tenant_id,
            finding_id=_gen_id("FND"),
            engagement_id=eng.id,
            procedure_id=proc_pk,
            ref_number=data.get("ref_number"),
            title=data["title"],
            condition=data.get("condition"),
            criteria=data.get("criteria"),
            cause=data.get("cause"),
            effect=data.get("effect"),
            recommendation=data.get("recommendation"),
            severity=data["severity"],
            category=data.get("category"),
            status=FindingStatus.DRAFT,
            repeat_finding=data.get("repeat_finding", False),
        )
        self.db.add(finding)
        self.db.flush()
        logger.info(
            "Tenant %s: created AuditFinding %s (%s) in engagement %s.",
            self.tenant_id,
            finding.finding_id,
            finding.severity,
            engagement_id,
        )
        return finding.to_dict()

    def update_finding(self, finding_id: str, data: Dict) -> Dict:
        """Update mutable fields on a finding."""
        finding = self._get_or_404(AuditFinding, "finding_id", finding_id)
        _apply_fields(
            finding,
            data,
            [
                "title",
                "condition",
                "criteria",
                "cause",
                "effect",
                "recommendation",
                "severity",
                "category",
                "status",
                "repeat_finding",
            ],
        )
        self.db.flush()
        return finding.to_dict()

    def list_findings(self, filters: Optional[Dict] = None) -> List[Dict]:
        """
        List findings for this tenant.

        Supported filter keys: ``engagement_id`` (string engagement_id),
        ``severity``, ``status``, ``category``.
        """
        q = self._q(AuditFinding)
        filters = filters or {}

        if "engagement_id" in filters:
            eng_row = (
                self._q(AuditEngagement)
                .filter(AuditEngagement.engagement_id == filters["engagement_id"])
                .first()
            )
            if eng_row:
                q = q.filter(AuditFinding.engagement_id == eng_row.id)
            else:
                return []
        if "severity" in filters:
            q = q.filter(AuditFinding.severity == filters["severity"])
        if "status" in filters:
            q = q.filter(AuditFinding.status == filters["status"])
        if "category" in filters:
            q = q.filter(AuditFinding.category == filters["category"])

        return [f.to_dict() for f in q.order_by(AuditFinding.created_at.desc()).all()]

    def record_management_response(self, finding_id: str, data: Dict) -> Dict:
        """
        Record management's response to a finding (AM-22).

        Transitions status → MANAGEMENT_RESPONSE_RECEIVED.
        data keys: ``management_response``, ``management_action_owner``,
                   ``management_target_date``.
        """
        finding = self._get_or_404(AuditFinding, "finding_id", finding_id)
        finding.management_response = data.get(
            "management_response", finding.management_response
        )
        finding.management_action_owner = data.get(
            "management_action_owner", finding.management_action_owner
        )
        finding.management_target_date = _parse_dt(
            data.get("management_target_date")
        ) or finding.management_target_date
        finding.status = FindingStatus.MANAGEMENT_RESPONSE_RECEIVED
        self.db.flush()
        return finding.to_dict()

    def link_finding_to_risk(self, finding_id: str, risk_id: int) -> Dict:
        """
        Link a finding to an EnterpriseRisk record (XI-03).

        Also appends this finding's string ID to the risk's related_finding_ids list.
        """
        finding = self._get_or_404(AuditFinding, "finding_id", finding_id)
        risk = (
            self.db.query(EnterpriseRisk)
            .filter(
                EnterpriseRisk.tenant_id == self.tenant_id,
                EnterpriseRisk.id == risk_id,
            )
            .first()
        )
        if risk is None:
            raise ValueError(f"EnterpriseRisk id={risk_id} not found.")
        finding.risk_id = risk_id

        # Keep the risk's back-reference list in sync
        existing_ids = list(risk.related_finding_ids or [])
        if finding.finding_id not in existing_ids:
            existing_ids.append(finding.finding_id)
            risk.related_finding_ids = existing_ids

        self.db.flush()
        return finding.to_dict()

    def link_finding_to_control(self, finding_id: str, control_id: int) -> Dict:
        """
        Link a finding to a ProcessControl record (XI-03).

        Also appends this finding's string ID to the control's related_finding_ids list.
        """
        finding = self._get_or_404(AuditFinding, "finding_id", finding_id)
        control = (
            self.db.query(ProcessControl)
            .filter(
                ProcessControl.tenant_id == self.tenant_id,
                ProcessControl.id == control_id,
            )
            .first()
        )
        if control is None:
            raise ValueError(f"ProcessControl id={control_id} not found.")
        finding.control_id = control_id

        # Keep control's back-reference list in sync
        existing_ids = list(control.related_finding_ids or [])
        if finding.finding_id not in existing_ids:
            existing_ids.append(finding.finding_id)
            control.related_finding_ids = existing_ids

        self.db.flush()
        return finding.to_dict()

    def link_finding_to_violation(self, finding_id: str, violation_id: int) -> Dict:
        """
        Link a finding to a RiskViolation by ID (XI-03).

        The violation_id is stored directly without a FK (avoids circular deps).
        """
        finding = self._get_or_404(AuditFinding, "finding_id", finding_id)
        finding.violation_id = violation_id
        self.db.flush()
        return finding.to_dict()

    def check_repeat_finding(self, finding_id: str) -> Dict:
        """
        Check whether a similar finding exists from prior engagements (AM-20 / AM-23).

        Performs a case-insensitive substring match on the first 40 characters
        of the title across all findings for this tenant (excluding the current one).

        Returns a dict with:
            finding_id        — the queried finding
            is_repeat         — True if similar priors found
            match_count       — number of similar prior findings
            prior_findings    — list of matching prior finding dicts
        """
        finding = self._get_or_404(AuditFinding, "finding_id", finding_id)
        title_key = finding.title[:40].lower()

        candidates = (
            self._q(AuditFinding)
            .filter(AuditFinding.finding_id != finding_id)
            .all()
        )
        matches = [
            c.to_dict()
            for c in candidates
            if title_key in c.title.lower()
        ]

        # If any matches found, flag the finding as a repeat
        if matches and not finding.repeat_finding:
            finding.repeat_finding = True
            # Link to the most recent prior finding by DB primary key (highest id)
            prior_ids = [m["id"] for m in matches if m.get("id")]
            if prior_ids:
                finding.prior_finding_id = max(prior_ids)
            self.db.flush()

        return {
            "finding_id": finding_id,
            "is_repeat": bool(matches),
            "match_count": len(matches),
            "prior_findings": matches,
        }

    # Backward-compat alias (returns list as before)
    def check_repeat_findings(self, finding_id: str) -> List[Dict]:
        """Alias that returns only the prior_findings list — retained for backward compatibility."""
        result = self.check_repeat_finding(finding_id)
        return result["prior_findings"]

    # =========================================================================
    # 8. Actions (AM-21)
    # =========================================================================

    def create_action(self, finding_id: str, data: Dict) -> Dict:
        """Create a management action item for a finding (AM-21)."""
        finding = self._get_or_404(AuditFinding, "finding_id", finding_id)
        action = AuditManagementAction(
            tenant_id=self.tenant_id,
            action_id=_gen_id("ACT"),
            finding_id=finding.id,
            description=data["description"],
            owner_id=data.get("owner_id"),
            owner_name=data.get("owner_name"),
            due_date=_parse_dt(data.get("due_date")),
            extended_due_date=_parse_dt(data.get("extended_due_date")),
            status=ActionStatus.OPEN,
            escalation_level=0,
            evidence_ids=data.get("evidence_ids"),
        )
        self.db.add(action)
        self.db.flush()
        return action.to_dict()

    def update_action(self, action_id: str, data: Dict) -> Dict:
        """Update mutable fields on an action item."""
        action = self._get_or_404(AuditManagementAction, "action_id", action_id)
        _apply_fields(
            action,
            data,
            [
                "description",
                "owner_id",
                "owner_name",
                "status",
                "evidence_of_closure",
                "evidence_ids",
            ],
        )
        for dt_field in ("due_date", "extended_due_date"):
            if dt_field in data:
                setattr(action, dt_field, _parse_dt(data[dt_field]))
        self.db.flush()
        return action.to_dict()

    def close_action(self, action_id: str, data: Dict) -> Dict:
        """
        Close a management action item with evidence (AM-21).

        data keys:
            evidence_of_closure (str)  Description of closure evidence
            evidence_ids        (list) Optional list of evidence record IDs
            completed_by        (str)  User ID of the person marking complete

        Sets status → COMPLETED (awaiting verifier sign-off).
        Use verify_action_closure() for the final CLOSED_VERIFIED transition.
        """
        action = self._get_or_404(AuditManagementAction, "action_id", action_id)
        action.status = ActionStatus.COMPLETED
        action.evidence_of_closure = data.get(
            "evidence_of_closure", action.evidence_of_closure
        )
        if "evidence_ids" in data:
            action.evidence_ids = data["evidence_ids"]
        action.completed_at = _now()
        self.db.flush()
        logger.info(
            "Tenant %s: action %s marked completed.", self.tenant_id, action_id
        )
        return action.to_dict()

    def verify_action_closure(self, action_id: str, verifier_id: str) -> Dict:
        """
        Verify and formally close a completed action item (AM-21).

        The action must already be in COMPLETED status.
        Transitions status → CLOSED_VERIFIED and records verifier sign-off.
        """
        action = self._get_or_404(AuditManagementAction, "action_id", action_id)
        if action.status != ActionStatus.COMPLETED:
            raise ValueError(
                f"Action '{action_id}' must be in COMPLETED status before verification "
                f"(current: {action.status.value})."
            )
        action.status = ActionStatus.CLOSED_VERIFIED
        action.verified_by = verifier_id
        action.verified_at = _now()
        self.db.flush()
        logger.info(
            "Tenant %s: action %s closed and verified by %s.",
            self.tenant_id,
            action_id,
            verifier_id,
        )
        return action.to_dict()

    def get_overdue_actions(self) -> List[Dict]:
        """
        Return all actions past their due date that are not yet closed (AM-21).

        Also stamps their status to OVERDUE in the database.
        """
        now = _now()
        overdue = (
            self._q(AuditManagementAction)
            .filter(
                AuditManagementAction.due_date < now,
                AuditManagementAction.status.in_(
                    [ActionStatus.OPEN, ActionStatus.IN_PROGRESS]
                ),
            )
            .all()
        )
        for action in overdue:
            action.status = ActionStatus.OVERDUE
        if overdue:
            self.db.flush()
        return [a.to_dict() for a in overdue]

    def escalate_overdue_actions(self) -> Dict:
        """
        Bump escalation_level by 1 on all OVERDUE actions (AM-21).

        Records last_escalated_at timestamp.

        Returns a summary dict:
            escalated_count   — number of actions escalated
            actions           — list of escalated action dicts
        """
        now = _now()
        overdue = (
            self._q(AuditManagementAction)
            .filter(AuditManagementAction.status == ActionStatus.OVERDUE)
            .all()
        )
        escalated = []
        for action in overdue:
            action.escalation_level += 1
            action.last_escalated_at = now
            escalated.append(action)
        if escalated:
            self.db.flush()
            logger.info(
                "Tenant %s: escalated %d overdue actions.",
                self.tenant_id,
                len(escalated),
            )
        return {
            "escalated_count": len(escalated),
            "actions": [a.to_dict() for a in escalated],
        }

    # =========================================================================
    # 9. Time Tracking (AM-14)
    # =========================================================================

    def record_time(self, engagement_id: str, data: Dict) -> Dict:
        """
        Log auditor time against an engagement (AM-14).

        Required data keys: ``auditor_id``, ``date``, ``hours``.
        Optional: ``activity_type``, ``description``, ``auditor_name``,
                  ``procedure_id`` (string procedure_id).
        """
        eng = self._get_or_404(AuditEngagement, "engagement_id", engagement_id)

        proc_pk = None
        if data.get("procedure_id"):
            proc_row = (
                self._q(AuditProcedure)
                .filter(AuditProcedure.procedure_id == data["procedure_id"])
                .first()
            )
            if proc_row:
                proc_pk = proc_row.id

        entry = AuditorTimeEntry(
            tenant_id=self.tenant_id,
            engagement_id=eng.id,
            procedure_id=proc_pk,
            auditor_id=data["auditor_id"],
            auditor_name=data.get("auditor_name"),
            date=_parse_dt(data["date"]) or _now(),
            hours=float(data["hours"]),
            activity_type=data.get("activity_type"),
            description=data.get("description"),
        )
        self.db.add(entry)
        self.db.flush()
        return entry.to_dict()

    # Backward-compat alias
    def log_time(self, engagement_id: str, data: Dict) -> Dict:
        """Alias for record_time — retained for backward compatibility."""
        return self.record_time(engagement_id, data)

    def get_time_summary(self, engagement_id: str) -> Dict:
        """
        Return total hours by auditor and by activity type for an engagement (AM-14).
        """
        eng = self._get_or_404(AuditEngagement, "engagement_id", engagement_id)

        entries = (
            self._q(AuditorTimeEntry)
            .filter(AuditorTimeEntry.engagement_id == eng.id)
            .all()
        )

        by_auditor: Dict[str, float] = defaultdict(float)
        by_activity: Dict[str, float] = defaultdict(float)
        total = 0.0

        for e in entries:
            by_auditor[e.auditor_id] += e.hours
            by_activity[e.activity_type or "unclassified"] += e.hours
            total += e.hours

        return {
            "engagement_id": engagement_id,
            "total_hours": round(total, 2),
            "by_auditor": dict(by_auditor),
            "by_activity_type": dict(by_activity),
            "entry_count": len(entries),
        }

    def get_auditor_utilization(
        self,
        auditor_id: str,
        period_start: Any = None,
        period_end: Any = None,
    ) -> Dict:
        """
        Return total logged hours for an auditor within an optional date window (AM-14).

        Breaks down by engagement and activity type.
        """
        start = _parse_dt(period_start)
        end = _parse_dt(period_end)

        q = self._q(AuditorTimeEntry).filter(
            AuditorTimeEntry.auditor_id == auditor_id
        )
        if start:
            q = q.filter(AuditorTimeEntry.date >= start)
        if end:
            q = q.filter(AuditorTimeEntry.date <= end)

        entries = q.all()

        by_engagement: Dict[int, float] = defaultdict(float)
        by_activity: Dict[str, float] = defaultdict(float)
        total = 0.0

        for e in entries:
            by_engagement[e.engagement_id] += e.hours
            by_activity[e.activity_type or "unclassified"] += e.hours
            total += e.hours

        return {
            "auditor_id": auditor_id,
            "period_start": start.isoformat() if start else None,
            "period_end": end.isoformat() if end else None,
            "total_hours": round(total, 2),
            "by_engagement_id": dict(by_engagement),
            "by_activity_type": dict(by_activity),
            "entry_count": len(entries),
        }

    # =========================================================================
    # 10. Resources (AM-03)
    # =========================================================================

    def create_resource(self, data: Dict) -> Dict:
        """Create an AuditorResource record (AM-03). auditor_id must be unique per tenant."""
        resource = AuditorResource(
            tenant_id=self.tenant_id,
            auditor_id=data.get("auditor_id") or _gen_id("AUD"),
            name=data["name"],
            email=data.get("email"),
            title=data.get("title"),
            skills=data.get("skills"),
            certifications=data.get("certifications"),
            available_hours_per_month=data.get("available_hours_per_month", 160.0),
            is_active=data.get("is_active", True),
            is_external=data.get("is_external", False),
        )
        self.db.add(resource)
        self.db.flush()
        return resource.to_dict()

    def update_resource(self, auditor_id: str, data: Dict) -> Dict:
        """Update mutable fields on an AuditorResource."""
        resource = self._get_or_404(AuditorResource, "auditor_id", auditor_id)
        _apply_fields(
            resource,
            data,
            [
                "name",
                "email",
                "title",
                "skills",
                "certifications",
                "available_hours_per_month",
                "is_active",
                "is_external",
            ],
        )
        self.db.flush()
        return resource.to_dict()

    def list_resources(self, filters: Optional[Dict] = None) -> List[Dict]:
        """
        List auditor resources for this tenant.

        Supported filter keys: ``is_active``, ``is_external``.
        """
        q = self._q(AuditorResource)
        filters = filters or {}
        if "is_active" in filters:
            q = q.filter(AuditorResource.is_active == filters["is_active"])
        if "is_external" in filters:
            q = q.filter(AuditorResource.is_external == filters["is_external"])
        return [r.to_dict() for r in q.order_by(AuditorResource.name).all()]

    def get_available_resources(
        self,
        start_date: Any,
        end_date: Any,
        skills: Optional[List[str]] = None,
    ) -> List[Dict]:
        """
        Return active auditors available in the date window, optionally filtered
        by required skills (AM-03).

        Date range parameters ``start_date`` / ``end_date`` are accepted for
        interface completeness; full capacity-calendar integration is a Phase 2
        enhancement.  Currently returns all active auditors whose hours logged
        in the period leave remaining capacity (based on available_hours_per_month).

        Skill matching is performed in Python against the JSON skills array.
        """
        start = _parse_dt(start_date)
        end = _parse_dt(end_date)

        resources = (
            self._q(AuditorResource)
            .filter(AuditorResource.is_active == True)
            .order_by(AuditorResource.name)
            .all()
        )

        # Filter by required skills if specified
        if skills:
            required = {s.lower() for s in skills}
            resources = [
                r
                for r in resources
                if required.issubset({s.lower() for s in (r.skills or [])})
            ]

        result = []
        for r in resources:
            # Compute hours already logged in the period
            q = self._q(AuditorTimeEntry).filter(
                AuditorTimeEntry.auditor_id == r.auditor_id
            )
            if start:
                q = q.filter(AuditorTimeEntry.date >= start)
            if end:
                q = q.filter(AuditorTimeEntry.date <= end)

            logged_hours = sum(e.hours for e in q.all())

            # Estimate available capacity for the period
            # For periods shorter than a month, scale proportionally (30-day month)
            if start and end:
                period_days = max((end - start).days, 1)
                period_months = period_days / 30.0
            else:
                period_months = 1.0

            capacity = r.available_hours_per_month * period_months
            remaining = max(capacity - logged_hours, 0.0)

            r_dict = r.to_dict()
            r_dict["logged_hours_in_period"] = round(logged_hours, 2)
            r_dict["capacity_hours_in_period"] = round(capacity, 2)
            r_dict["remaining_hours_in_period"] = round(remaining, 2)
            result.append(r_dict)

        return result

    # Backward-compat alias
    def get_available_auditors(
        self,
        skills: Optional[List[str]] = None,
        start_date: Any = None,
        end_date: Any = None,
    ) -> List[Dict]:
        """Alias for get_available_resources — retained for backward compatibility."""
        return self.get_available_resources(
            start_date=start_date, end_date=end_date, skills=skills
        )

    # =========================================================================
    # 11. Reporting (AM-30, AM-31)
    # =========================================================================

    def generate_engagement_report(self, engagement_id: str) -> Dict:
        """
        Generate a structured audit report from an engagement's findings (AM-30).

        Compiles the engagement header, team, scope, methodology, findings
        (grouped by severity), management responses, and action items.
        """
        eng = self._get_or_404(AuditEngagement, "engagement_id", engagement_id)

        findings = (
            self._q(AuditFinding)
            .filter(AuditFinding.engagement_id == eng.id)
            .order_by(AuditFinding.severity)
            .all()
        )

        findings_by_severity: Dict[str, List[Dict]] = defaultdict(list)
        for f in findings:
            severity_key = f.severity.value if f.severity else "unknown"
            finding_dict = f.to_dict()

            # Attach action items
            actions = (
                self._q(AuditManagementAction)
                .filter(AuditManagementAction.finding_id == f.id)
                .all()
            )
            finding_dict["actions"] = [a.to_dict() for a in actions]
            findings_by_severity[severity_key].append(finding_dict)

        # Severity order for the report
        severity_order = ["critical", "high", "medium", "low", "observation"]
        ordered_findings = {
            sev: findings_by_severity[sev]
            for sev in severity_order
            if sev in findings_by_severity
        }

        open_actions_count = (
            self._q(AuditManagementAction)
            .join(AuditFinding, AuditManagementAction.finding_id == AuditFinding.id)
            .filter(
                AuditFinding.engagement_id == eng.id,
                AuditManagementAction.status.in_(
                    [ActionStatus.OPEN, ActionStatus.IN_PROGRESS, ActionStatus.OVERDUE]
                ),
            )
            .count()
        )

        # Attach workpapers index
        workpapers = (
            self._q(AuditWorkpaper)
            .filter(
                AuditWorkpaper.engagement_id == eng.id,
                AuditWorkpaper.status != WorkpaperStatus.SUPERSEDED,
            )
            .all()
        )

        return {
            "report_type": "audit_engagement_report",
            "generated_at": _now().isoformat(),
            "engagement": eng.to_dict(),
            "executive_summary": {
                "title": eng.title,
                "objective": eng.objective,
                "scope": eng.scope,
                "methodology": eng.methodology,
                "status": eng.status.value if eng.status else None,
                "lead_auditor": eng.lead_auditor_name,
                "planned_start": eng.planned_start.isoformat() if eng.planned_start else None,
                "planned_end": eng.planned_end.isoformat() if eng.planned_end else None,
                "actual_start": eng.actual_start.isoformat() if eng.actual_start else None,
                "actual_end": eng.actual_end.isoformat() if eng.actual_end else None,
            },
            "findings_summary": {
                "total": len(findings),
                "by_severity": {
                    sev: len(lst) for sev, lst in findings_by_severity.items()
                },
                "open_actions": open_actions_count,
            },
            "findings": ordered_findings,
            "workpapers": [w.to_dict() for w in workpapers],
            "recommendations": [
                {
                    "finding_id": f.to_dict()["finding_id"],
                    "recommendation": f.recommendation,
                    "severity": f.severity.value if f.severity else None,
                }
                for f in findings
                if f.recommendation
            ],
        }

    # Backward-compat alias
    def generate_audit_report(self, engagement_id: str) -> Dict:
        """Alias for generate_engagement_report — retained for backward compatibility."""
        return self.generate_engagement_report(engagement_id)

    def get_audit_dashboard(self) -> Dict:
        """
        Return a consolidated audit dashboard for this tenant (AM-30).

        Includes:
        - Plan progress (engagements by status across all plans)
        - Findings breakdown by severity and status
        - Overdue actions count and actions due within 30 days
        - Top 5 entities by risk score
        """
        # Engagement counts by status
        eng_by_status: Dict[str, int] = defaultdict(int)
        for eng in self._q(AuditEngagement).all():
            eng_by_status[eng.status.value if eng.status else "unknown"] += 1

        # Finding counts by severity and status
        finding_by_severity: Dict[str, int] = defaultdict(int)
        finding_by_status: Dict[str, int] = defaultdict(int)
        for f in self._q(AuditFinding).all():
            finding_by_severity[f.severity.value if f.severity else "unknown"] += 1
            finding_by_status[f.status.value if f.status else "unknown"] += 1

        # Overdue actions
        overdue_count = (
            self._q(AuditManagementAction)
            .filter(AuditManagementAction.status == ActionStatus.OVERDUE)
            .count()
        )

        # Actions due within 30 days
        due_soon_cutoff = _now() + timedelta(days=30)
        actions_due_soon = (
            self._q(AuditManagementAction)
            .filter(
                AuditManagementAction.due_date <= due_soon_cutoff,
                AuditManagementAction.status.in_(
                    [ActionStatus.OPEN, ActionStatus.IN_PROGRESS]
                ),
            )
            .count()
        )

        # Plans summary
        total_plans = self._q(AuditPlan).count()
        approved_plans = (
            self._q(AuditPlan)
            .filter(AuditPlan.status == AuditPlanStatus.APPROVED)
            .count()
        )

        # Top 5 riskiest entities
        top_entities = (
            self._q(AuditableEntity)
            .filter(
                AuditableEntity.is_active == True,
                AuditableEntity.risk_score.isnot(None),
            )
            .order_by(AuditableEntity.risk_score.desc())
            .limit(5)
            .all()
        )

        return {
            "dashboard_type": "audit_management",
            "generated_at": _now().isoformat(),
            "tenant_id": self.tenant_id,
            "plans": {
                "total": total_plans,
                "approved": approved_plans,
            },
            "engagements_by_status": dict(eng_by_status),
            "findings_by_severity": dict(finding_by_severity),
            "findings_by_status": dict(finding_by_status),
            "overdue_actions": overdue_count,
            "actions_due_within_30_days": actions_due_soon,
            "top_risk_entities": [e.to_dict() for e in top_entities],
        }

    # =========================================================================
    # XL-D  Evidence Pull from AC/PC/RM
    # =========================================================================

    def pull_evidence(self, engagement_id: str, data: dict) -> dict:
        """
        XL-D: Pull system-generated evidence from AC/PC/RM into an audit engagement.

        Validates the engagement exists for this tenant, then delegates to
        EvidencePullService which queries the requested source table, serialises
        a point-in-time snapshot, hashes it for integrity, and persists a
        GRCEvidence record linked to the engagement.

        Required keys in *data*:
          source (str) — 'sod_violations' | 'ccm_executions' |
                         'firefighter_sessions' | 'risk_baseline'

        Optional keys:
          filters   (dict) — source-specific filter params (rule_ids, from, to, …)
          title     (str)  — human-readable evidence title
          pulled_by (str)  — user ID performing the pull (default 'system')

        Returns a summary dict:
          evidence_id, source, row_count, sha256, generated_at, linked_to
        """
        from core.audit_management.evidence_pull import EvidencePullService

        # Validate engagement belongs to this tenant
        engagement = self._get_or_404(AuditEngagement, "engagement_id", engagement_id)  # noqa: F841 — validates ownership

        source = data.get("source")
        if not source:
            raise ValueError("'source' is required")

        service = EvidencePullService(tenant_id=self.tenant_id, db=self.db)
        return service.pull_evidence(
            engagement_id=engagement_id,
            source=source,
            filters=data.get("filters", {}),
            title=data.get("title"),
            pulled_by=data.get("pulled_by", "system"),
        )

    def get_committee_report(self, fiscal_year: Optional[int] = None) -> Dict:
        """
        Generate an executive / audit-committee summary (AM-31).

        Parameters
        ----------
        fiscal_year : int, optional
            If given, filters plans and engagements to that fiscal year.
            If None, reports across all years.

        Returns a board-level summary covering plan status, engagement
        completion rate, critical/high findings, repeat findings, and
        overdue high-priority actions.
        """
        # Plans
        plans_q = self._q(AuditPlan)
        if fiscal_year is not None:
            plans_q = plans_q.filter(AuditPlan.fiscal_year == int(fiscal_year))
        plans = plans_q.all()

        plans_summary = []
        for p in plans:
            eng_count = (
                self._q(AuditEngagement)
                .filter(AuditEngagement.plan_id == p.id)
                .count()
            )
            closed_count = (
                self._q(AuditEngagement)
                .filter(
                    AuditEngagement.plan_id == p.id,
                    AuditEngagement.status == EngagementStatus.CLOSED,
                )
                .count()
            )
            plans_summary.append(
                {
                    "plan_id": p.plan_id,
                    "name": p.name,
                    "fiscal_year": p.fiscal_year,
                    "status": p.status.value if p.status else None,
                    "engagement_count": eng_count,
                    "closed_engagement_count": closed_count,
                    "completion_rate_pct": (
                        round(closed_count / eng_count * 100, 1)
                        if eng_count
                        else 0.0
                    ),
                }
            )

        # Overall engagement completion rate
        eng_q = self._q(AuditEngagement)
        if fiscal_year is not None:
            # Scope to engagements under the filtered plans
            plan_pks = [p.id for p in plans]
            if plan_pks:
                eng_q = eng_q.filter(AuditEngagement.plan_id.in_(plan_pks))
            else:
                eng_q = eng_q.filter(False)  # no plans = no engagements

        total_engs = eng_q.count()
        closed_engs = (
            eng_q.filter(AuditEngagement.status == EngagementStatus.CLOSED).count()
            if total_engs
            else 0
        )
        completion_rate = (
            round(closed_engs / total_engs * 100, 1) if total_engs else 0.0
        )

        # Critical and high open findings
        findings_q = self._q(AuditFinding).filter(
            AuditFinding.severity.in_(["critical", "high"]),
            AuditFinding.status != FindingStatus.CLOSED,
        )
        critical_high = findings_q.all()

        # Repeat findings
        repeat_findings_count = (
            self._q(AuditFinding)
            .filter(AuditFinding.repeat_finding == True)
            .count()
        )

        # Overdue high-priority actions
        overdue_high = (
            self._q(AuditManagementAction)
            .join(AuditFinding, AuditManagementAction.finding_id == AuditFinding.id)
            .filter(
                AuditManagementAction.status == ActionStatus.OVERDUE,
                AuditFinding.severity.in_(["critical", "high"]),
            )
            .count()
        )

        # Actions without a due date set (governance gap indicator)
        actions_no_due_date = (
            self._q(AuditManagementAction)
            .filter(
                AuditManagementAction.due_date.is_(None),
                AuditManagementAction.status.in_(
                    [ActionStatus.OPEN, ActionStatus.IN_PROGRESS]
                ),
            )
            .count()
        )

        return {
            "report_type": "audit_committee_report",
            "fiscal_year": fiscal_year,
            "generated_at": _now().isoformat(),
            "tenant_id": self.tenant_id,
            "plans_summary": plans_summary,
            "engagement_completion_rate_pct": completion_rate,
            "total_engagements": total_engs,
            "closed_engagements": closed_engs,
            "open_critical_high_findings": len(critical_high),
            "critical_high_findings": [f.to_dict() for f in critical_high],
            "repeat_finding_count": repeat_findings_count,
            "overdue_high_priority_actions": overdue_high,
            "actions_without_due_date": actions_no_due_date,
        }
