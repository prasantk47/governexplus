"""
Database Models - Audit Management Module

Full Audit Management module covering AM-01 through AM-32:
  - AuditableEntity     : audit universe (AM-01)
  - AuditPlan           : annual / multi-year plans (AM-02)
  - AuditEngagement     : individual audit engagements (AM-10)
  - AuditWorkProgram    : reusable procedure templates (AM-11)
  - AuditProcedure      : individual procedure execution (AM-11)
  - AuditWorkpaper      : document management (AM-12)
  - AuditFinding        : formal findings with CCCE (AM-20)
  - AuditAction         : management action items from findings (AM-21)
  - AuditorTimeEntry    : time tracking (AM-14)
  - AuditorResource     : skills and availability (AM-03)
  - AuditDimension      : multi-perspective audit dimensions (AM-SAP-GAP-11)
  - AuditAnnouncement   : formal auditee notification (AM-SAP-GAP-12)

Note: AuditAction here is the audit-management action-item model.
The audit-log AuditAction enum lives in db/models/audit.py.
"""

from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Text,
    ForeignKey, JSON, Float, Enum as SQLEnum
)
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from .base import Base, TimestampMixin


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class AuditableEntityType(enum.Enum):
    """Classification of an auditable entity"""
    ORG_UNIT = "org_unit"
    PROCESS = "process"
    SYSTEM = "system"
    PROJECT = "project"
    VENDOR = "vendor"


class AuditPlanType(enum.Enum):
    """Type of audit plan"""
    ANNUAL = "annual"
    MULTI_YEAR = "multi_year"
    SPECIAL = "special"


class AuditPlanStatus(enum.Enum):
    """Workflow status of an audit plan"""
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class EngagementType(enum.Enum):
    """Type of audit engagement"""
    FINANCIAL = "financial"
    OPERATIONAL = "operational"
    IT = "it"
    COMPLIANCE = "compliance"
    SPECIAL = "special"
    FOLLOW_UP = "follow_up"


class EngagementStatus(enum.Enum):
    """Lifecycle status of an audit engagement"""
    PLANNED = "planned"
    ANNOUNCED = "announced"
    FIELDWORK = "fieldwork"
    DRAFT_REPORT = "draft_report"
    FINAL_REPORT = "final_report"
    CLOSED = "closed"


class ProcedureStatus(enum.Enum):
    """Status of an individual audit procedure"""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    REVIEWED = "reviewed"


class WorkpaperReviewStatus(enum.Enum):
    """Review workflow status of a workpaper"""
    PENDING_REVIEW = "pending_review"
    REVIEWED = "reviewed"
    REVISION_NEEDED = "revision_needed"


class WorkpaperStatus(enum.Enum):
    """Publication status of a workpaper"""
    DRAFT = "draft"
    FINAL = "final"
    SUPERSEDED = "superseded"


class FindingSeverity(enum.Enum):
    """Severity rating of an audit finding"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    OBSERVATION = "observation"


class FindingStatus(enum.Enum):
    """Lifecycle status of an audit finding"""
    DRAFT = "draft"
    DISCUSSED = "discussed"
    FINAL = "final"
    MANAGEMENT_RESPONSE_RECEIVED = "management_response_received"
    CLOSED = "closed"


class ActionStatus(enum.Enum):
    """Status of a management action item"""
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    OVERDUE = "overdue"
    CLOSED_VERIFIED = "closed_verified"


class DimensionType(enum.Enum):
    """Type of audit dimension for multi-perspective coverage"""
    BUSINESS_PROCESS = "business_process"
    LEGAL_ENTITY = "legal_entity"
    IT_SYSTEM = "it_system"
    GEOGRAPHY = "geography"
    REGULATION = "regulation"
    PRODUCT = "product"


class AnnouncementStatus(enum.Enum):
    """Status of an audit announcement"""
    DRAFT = "draft"
    SENT = "sent"
    ACKNOWLEDGED = "acknowledged"


# ---------------------------------------------------------------------------
# AuditableEntity  (AM-01)
# ---------------------------------------------------------------------------

class AuditableEntity(Base, TimestampMixin):
    """
    Audit universe entry — any entity subject to internal audit (AM-01).

    Risk scores are computed from RM, AC, and PC data and drive the annual
    risk-based audit plan.  Entities can represent org units, processes,
    IT systems, projects, or vendors.
    """
    __tablename__ = 'auditable_entities'

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Multi-tenant support
    tenant_id = Column(String(100), nullable=False, index=True, default='tenant_default')

    # Identity
    entity_id = Column(String(100), nullable=False, index=True)   # unique within tenant
    name = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    entity_type = Column(SQLEnum(AuditableEntityType), nullable=False)

    # Organisational link
    org_unit_id = Column(Integer, ForeignKey('org_units.id'), nullable=True, index=True)

    # Risk-based scoring (computed externally, stored here for plan prioritisation)
    risk_score = Column(Float, nullable=True)

    # Audit history
    last_audited_at = Column(DateTime, nullable=True)
    audit_frequency = Column(String(50), nullable=True)       # annual, bi-annual, 3-year
    primary_auditor_id = Column(String(100), nullable=True)

    # Status
    is_active = Column(Boolean, default=True, nullable=False)

    # Extension bag
    metadata_ = Column('metadata', JSON, nullable=True)

    # Relationships
    engagements = relationship('AuditEngagement', back_populates='entity')

    def __repr__(self):
        return (
            f"<AuditableEntity(entity_id='{self.entity_id}', "
            f"name='{self.name[:50]}', type='{self.entity_type}')>"
        )

    def to_dict(self):
        return {
            'id': self.id,
            'tenant_id': self.tenant_id,
            'entity_id': self.entity_id,
            'name': self.name,
            'description': self.description,
            'entity_type': self.entity_type.value if self.entity_type else None,
            'org_unit_id': self.org_unit_id,
            'risk_score': self.risk_score,
            'last_audited_at': self.last_audited_at.isoformat() if self.last_audited_at else None,
            'audit_frequency': self.audit_frequency,
            'primary_auditor_id': self.primary_auditor_id,
            'is_active': self.is_active,
            'metadata': self.metadata_,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


# ---------------------------------------------------------------------------
# AuditPlan  (AM-02)
# ---------------------------------------------------------------------------

class AuditPlan(Base, TimestampMixin):
    """
    Annual or multi-year internal audit plan (AM-02).

    Captures board/AC-approved scope, budget, and risk methodology used to
    prioritise engagements.  Approved plans become the source of truth for
    engagement scheduling.
    """
    __tablename__ = 'audit_plans'

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Multi-tenant support
    tenant_id = Column(String(100), nullable=False, index=True, default='tenant_default')

    # Identity
    plan_id = Column(String(100), nullable=False, index=True)
    name = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)

    # Classification
    plan_type = Column(SQLEnum(AuditPlanType), nullable=False)
    fiscal_year = Column(Integer, nullable=False)
    period_start = Column(DateTime, nullable=True)
    period_end = Column(DateTime, nullable=True)

    # Resources
    total_audit_hours = Column(Integer, nullable=True)
    allocated_budget = Column(Float, nullable=True)

    # Workflow
    status = Column(SQLEnum(AuditPlanStatus), nullable=False, default=AuditPlanStatus.DRAFT)
    prepared_by = Column(String(100), nullable=True)
    approved_by = Column(String(100), nullable=True)
    approved_at = Column(DateTime, nullable=True)

    # Risk methodology description
    risk_methodology = Column(Text, nullable=True)

    # Rolling plan support (AM-SAP-GAP)
    is_rolling = Column(Boolean, default=False, nullable=False)
    predecessor_plan_id = Column(Integer, ForeignKey('audit_plans.id'), nullable=True, index=True)

    # Extension bag
    metadata_ = Column('metadata', JSON, nullable=True)

    # Relationships
    engagements = relationship('AuditEngagement', back_populates='plan')
    predecessor = relationship('AuditPlan', remote_side='AuditPlan.id', back_populates='successors')
    successors = relationship('AuditPlan', back_populates='predecessor')

    def __repr__(self):
        return (
            f"<AuditPlan(plan_id='{self.plan_id}', "
            f"fiscal_year={self.fiscal_year}, status='{self.status}')>"
        )

    def to_dict(self):
        return {
            'id': self.id,
            'tenant_id': self.tenant_id,
            'plan_id': self.plan_id,
            'name': self.name,
            'description': self.description,
            'plan_type': self.plan_type.value if self.plan_type else None,
            'fiscal_year': self.fiscal_year,
            'period_start': self.period_start.isoformat() if self.period_start else None,
            'period_end': self.period_end.isoformat() if self.period_end else None,
            'total_audit_hours': self.total_audit_hours,
            'allocated_budget': self.allocated_budget,
            'status': self.status.value if self.status else None,
            'prepared_by': self.prepared_by,
            'approved_by': self.approved_by,
            'approved_at': self.approved_at.isoformat() if self.approved_at else None,
            'risk_methodology': self.risk_methodology,
            'is_rolling': self.is_rolling,
            'predecessor_plan_id': self.predecessor_plan_id,
            'metadata': self.metadata_,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


# ---------------------------------------------------------------------------
# AuditEngagement  (AM-10)
# ---------------------------------------------------------------------------

class AuditEngagement(Base, TimestampMixin):
    """
    Individual audit engagement (AM-10).

    Represents a single audit project from planning through report issuance.
    Team members are stored as a JSON list to avoid a separate join table while
    still supporting multi-member engagements.
    """
    __tablename__ = 'audit_engagements'

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Multi-tenant support
    tenant_id = Column(String(100), nullable=False, index=True, default='tenant_default')

    # Identity
    engagement_id = Column(String(100), nullable=False, index=True)

    # Parent plan and auditable entity (both optional for special/ad-hoc engagements)
    plan_id = Column(Integer, ForeignKey('audit_plans.id'), nullable=True, index=True)
    entity_id = Column(Integer, ForeignKey('auditable_entities.id'), nullable=True, index=True)

    # Description
    title = Column(String(500), nullable=False)
    objective = Column(Text, nullable=True)
    scope = Column(Text, nullable=True)

    # Classification
    engagement_type = Column(SQLEnum(EngagementType), nullable=False)

    # Lifecycle
    status = Column(SQLEnum(EngagementStatus), nullable=False, default=EngagementStatus.PLANNED)

    # Team
    lead_auditor_id = Column(String(100), nullable=True)
    lead_auditor_name = Column(String(255), nullable=True)
    team_members = Column(JSON, nullable=True)    # [{id, name, role}]

    # Scheduling
    planned_start = Column(DateTime, nullable=True)
    planned_end = Column(DateTime, nullable=True)
    actual_start = Column(DateTime, nullable=True)
    actual_end = Column(DateTime, nullable=True)

    # Budget
    budget_hours = Column(Float, nullable=True)
    actual_hours = Column(Float, nullable=True)

    # Risk
    risk_rating = Column(String(20), nullable=True)    # high, medium, low

    # Methodology notes
    methodology = Column(Text, nullable=True)

    # Audit opinion (AM-SAP-GAP)
    opinion = Column(String(100), nullable=True)            # satisfactory/needs_improvement/unsatisfactory
    opinion_rationale = Column(Text, nullable=True)

    # Relationships
    plan = relationship('AuditPlan', back_populates='engagements')
    entity = relationship('AuditableEntity', back_populates='engagements')
    procedures = relationship('AuditProcedure', back_populates='engagement')
    workpapers = relationship('AuditWorkpaper', back_populates='engagement')
    findings = relationship('AuditFinding', back_populates='engagement')
    time_entries = relationship('AuditorTimeEntry', back_populates='engagement')

    def __repr__(self):
        return (
            f"<AuditEngagement(engagement_id='{self.engagement_id}', "
            f"title='{self.title[:50]}', status='{self.status}')>"
        )

    def to_dict(self):
        return {
            'id': self.id,
            'tenant_id': self.tenant_id,
            'engagement_id': self.engagement_id,
            'plan_id': self.plan_id,
            'entity_id': self.entity_id,
            'title': self.title,
            'objective': self.objective,
            'scope': self.scope,
            'engagement_type': self.engagement_type.value if self.engagement_type else None,
            'status': self.status.value if self.status else None,
            'lead_auditor_id': self.lead_auditor_id,
            'lead_auditor_name': self.lead_auditor_name,
            'team_members': self.team_members,
            'planned_start': self.planned_start.isoformat() if self.planned_start else None,
            'planned_end': self.planned_end.isoformat() if self.planned_end else None,
            'actual_start': self.actual_start.isoformat() if self.actual_start else None,
            'actual_end': self.actual_end.isoformat() if self.actual_end else None,
            'budget_hours': self.budget_hours,
            'actual_hours': self.actual_hours,
            'risk_rating': self.risk_rating,
            'methodology': self.methodology,
            'opinion': self.opinion,
            'opinion_rationale': self.opinion_rationale,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


# ---------------------------------------------------------------------------
# AuditWorkProgram  (AM-11)
# ---------------------------------------------------------------------------

class AuditWorkProgram(Base, TimestampMixin):
    """
    Reusable audit work program / procedure template (AM-11).

    Templates are authored once and instantiated as AuditProcedure rows when
    an engagement begins.  The procedures JSON holds the ordered checklist of
    steps with reference numbers, descriptions, and expected evidence.
    """
    __tablename__ = 'audit_work_programs'

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Multi-tenant support
    tenant_id = Column(String(100), nullable=False, index=True, default='tenant_default')

    # Identity
    program_id = Column(String(100), nullable=False, index=True)
    name = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)

    # Classification
    audit_type = Column(String(50), nullable=True)    # financial, it, operational, compliance

    # Procedure steps — [{ref, title, description, expected_evidence}]
    procedures = Column(JSON, nullable=True)

    # Template flag — if True this is a reusable master; if False it's engagement-specific
    is_template = Column(Boolean, default=False, nullable=False)

    # Source engagement (when saved from an actual engagement for future re-use)
    source_engagement_id = Column(
        Integer, ForeignKey('audit_engagements.id'), nullable=True, index=True
    )

    # Versioning
    version = Column(Integer, nullable=False, default=1)

    def __repr__(self):
        return (
            f"<AuditWorkProgram(program_id='{self.program_id}', "
            f"name='{self.name[:50]}', is_template={self.is_template})>"
        )

    def to_dict(self):
        return {
            'id': self.id,
            'tenant_id': self.tenant_id,
            'program_id': self.program_id,
            'name': self.name,
            'description': self.description,
            'audit_type': self.audit_type,
            'procedures': self.procedures,
            'is_template': self.is_template,
            'source_engagement_id': self.source_engagement_id,
            'version': self.version,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


# ---------------------------------------------------------------------------
# AuditProcedure
# ---------------------------------------------------------------------------

class AuditProcedure(Base, TimestampMixin):
    """
    Individual audit procedure execution record within an engagement.

    Each procedure corresponds to one step in the work program.  Preparer /
    reviewer sign-off fields mirror a traditional e-workpaper sign-off model.
    """
    __tablename__ = 'audit_procedures'

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Multi-tenant support
    tenant_id = Column(String(100), nullable=False, index=True, default='tenant_default')

    # Identity
    procedure_id = Column(String(100), nullable=False, index=True)

    # Parent engagement and optional work program
    engagement_id = Column(Integer, ForeignKey('audit_engagements.id'), nullable=False, index=True)
    work_program_id = Column(Integer, ForeignKey('audit_work_programs.id'), nullable=True, index=True)

    # Reference number within the engagement (e.g. "AP-001")
    ref_number = Column(String(50), nullable=True)

    # Description
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)

    # Assignment
    assigned_to_id = Column(String(100), nullable=True)
    assigned_to_name = Column(String(255), nullable=True)

    # Workflow
    status = Column(SQLEnum(ProcedureStatus), nullable=False, default=ProcedureStatus.NOT_STARTED)
    conclusion = Column(Text, nullable=True)

    # Time tracking
    hours_spent = Column(Float, nullable=False, default=0.0)

    # Preparer sign-off
    preparer_id = Column(String(100), nullable=True)
    prepared_at = Column(DateTime, nullable=True)

    # Reviewer sign-off
    reviewer_id = Column(String(100), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    review_notes = Column(Text, nullable=True)

    # Evidence and cross-references
    evidence_ids = Column(JSON, nullable=True)        # list of grc_evidence IDs
    cross_references = Column(JSON, nullable=True)    # references to other procedures

    # Relationships
    engagement = relationship('AuditEngagement', back_populates='procedures')
    work_program = relationship('AuditWorkProgram')
    workpapers = relationship('AuditWorkpaper', back_populates='procedure')

    def __repr__(self):
        return (
            f"<AuditProcedure(procedure_id='{self.procedure_id}', "
            f"ref='{self.ref_number}', status='{self.status}')>"
        )

    def to_dict(self):
        return {
            'id': self.id,
            'tenant_id': self.tenant_id,
            'procedure_id': self.procedure_id,
            'engagement_id': self.engagement_id,
            'work_program_id': self.work_program_id,
            'ref_number': self.ref_number,
            'title': self.title,
            'description': self.description,
            'assigned_to_id': self.assigned_to_id,
            'assigned_to_name': self.assigned_to_name,
            'status': self.status.value if self.status else None,
            'conclusion': self.conclusion,
            'hours_spent': self.hours_spent,
            'preparer_id': self.preparer_id,
            'prepared_at': self.prepared_at.isoformat() if self.prepared_at else None,
            'reviewer_id': self.reviewer_id,
            'reviewed_at': self.reviewed_at.isoformat() if self.reviewed_at else None,
            'review_notes': self.review_notes,
            'evidence_ids': self.evidence_ids,
            'cross_references': self.cross_references,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


# ---------------------------------------------------------------------------
# AuditWorkpaper  (AM-12)
# ---------------------------------------------------------------------------

class AuditWorkpaper(Base, TimestampMixin):
    """
    Electronic workpaper document (AM-12).

    Supports file-based documents (stored path + hash) and text-based
    narratives (inline content).  Full version lineage is tracked via
    previous_version_id chain.
    """
    __tablename__ = 'audit_workpapers'

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Multi-tenant support
    tenant_id = Column(String(100), nullable=False, index=True, default='tenant_default')

    # Identity
    workpaper_id = Column(String(100), nullable=False, index=True)

    # Parent engagement and optional procedure
    engagement_id = Column(Integer, ForeignKey('audit_engagements.id'), nullable=False, index=True)
    procedure_id = Column(Integer, ForeignKey('audit_procedures.id'), nullable=True, index=True)

    # Description
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)

    # Document classification
    document_type = Column(String(100), nullable=True)   # narrative, schedule, confirmation, extract, screenshot

    # File metadata (null for inline text workpapers)
    file_name = Column(String(500), nullable=True)
    file_path = Column(String(2000), nullable=True)
    file_size = Column(Integer, nullable=True)

    # Inline text content (for narrative workpapers)
    content = Column(Text, nullable=True)

    # Versioning
    version = Column(Integer, nullable=False, default=1)
    previous_version_id = Column(Integer, ForeignKey('audit_workpapers.id'), nullable=True)

    # Preparer sign-off
    preparer_id = Column(String(100), nullable=True)
    prepared_at = Column(DateTime, nullable=True)

    # Reviewer sign-off
    reviewer_id = Column(String(100), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    review_status = Column(
        SQLEnum(WorkpaperReviewStatus), nullable=False, default=WorkpaperReviewStatus.PENDING_REVIEW
    )
    review_notes = Column(JSON, nullable=True)       # [{reviewer_id, note, timestamp}]

    # Cross-references and status
    cross_references = Column(JSON, nullable=True)
    status = Column(SQLEnum(WorkpaperStatus), nullable=False, default=WorkpaperStatus.DRAFT)

    # Relationships
    engagement = relationship('AuditEngagement', back_populates='workpapers')
    procedure = relationship('AuditProcedure', back_populates='workpapers')
    previous_version = relationship('AuditWorkpaper', remote_side='AuditWorkpaper.id')

    def __repr__(self):
        return (
            f"<AuditWorkpaper(workpaper_id='{self.workpaper_id}', "
            f"title='{self.title[:50]}', status='{self.status}')>"
        )

    def to_dict(self):
        return {
            'id': self.id,
            'tenant_id': self.tenant_id,
            'workpaper_id': self.workpaper_id,
            'engagement_id': self.engagement_id,
            'procedure_id': self.procedure_id,
            'title': self.title,
            'description': self.description,
            'document_type': self.document_type,
            'file_name': self.file_name,
            'file_path': self.file_path,
            'file_size': self.file_size,
            'content': self.content,
            'version': self.version,
            'previous_version_id': self.previous_version_id,
            'preparer_id': self.preparer_id,
            'prepared_at': self.prepared_at.isoformat() if self.prepared_at else None,
            'reviewer_id': self.reviewer_id,
            'reviewed_at': self.reviewed_at.isoformat() if self.reviewed_at else None,
            'review_status': self.review_status.value if self.review_status else None,
            'review_notes': self.review_notes,
            'cross_references': self.cross_references,
            'status': self.status.value if self.status else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


# ---------------------------------------------------------------------------
# AuditFinding  (AM-20)
# ---------------------------------------------------------------------------

class AuditFinding(Base, TimestampMixin):
    """
    Formal audit finding using the CCCE structure (AM-20).

    Condition / Criteria / Cause / Effect maps to standard IIA finding
    documentation.  Cross-module links connect findings to risk register
    entries, process controls, and access-control violations.
    """
    __tablename__ = 'audit_findings'

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Multi-tenant support
    tenant_id = Column(String(100), nullable=False, index=True, default='tenant_default')

    # Identity
    finding_id = Column(String(100), nullable=False, index=True)

    # Parent engagement and optional procedure
    engagement_id = Column(Integer, ForeignKey('audit_engagements.id'), nullable=False, index=True)
    procedure_id = Column(Integer, ForeignKey('audit_procedures.id'), nullable=True, index=True)

    # Reference number within the engagement (e.g. "F-001")
    ref_number = Column(String(50), nullable=True)

    # CCCE structure
    title = Column(String(500), nullable=False)
    condition = Column(Text, nullable=True)      # what was found
    criteria = Column(Text, nullable=True)       # what should be
    cause = Column(Text, nullable=True)          # why it happened
    effect = Column(Text, nullable=True)         # risk / impact

    # Recommendation
    recommendation = Column(Text, nullable=True)

    # Classification
    severity = Column(SQLEnum(FindingSeverity), nullable=False)
    category = Column(String(100), nullable=True)    # financial, operational, compliance, it

    # Cross-module links (all optional)
    risk_id = Column(Integer, ForeignKey('enterprise_risks.id'), nullable=True, index=True)
    control_id = Column(Integer, ForeignKey('process_controls.id'), nullable=True, index=True)
    violation_id = Column(Integer, nullable=True)     # links to risk_violations.id (no FK to avoid circular dep)

    # Management response
    management_response = Column(Text, nullable=True)
    management_action_owner = Column(String(100), nullable=True)
    management_target_date = Column(DateTime, nullable=True)

    # Lifecycle
    status = Column(SQLEnum(FindingStatus), nullable=False, default=FindingStatus.DRAFT)

    # Repeat finding tracking
    repeat_finding = Column(Boolean, default=False, nullable=False)
    prior_finding_id = Column(Integer, ForeignKey('audit_findings.id'), nullable=True)

    # Relationships
    engagement = relationship('AuditEngagement', back_populates='findings')
    procedure = relationship('AuditProcedure')
    prior_finding = relationship('AuditFinding', remote_side='AuditFinding.id')
    actions = relationship('AuditManagementAction', back_populates='finding')

    def __repr__(self):
        return (
            f"<AuditFinding(finding_id='{self.finding_id}', "
            f"severity='{self.severity}', status='{self.status}')>"
        )

    def to_dict(self):
        return {
            'id': self.id,
            'tenant_id': self.tenant_id,
            'finding_id': self.finding_id,
            'engagement_id': self.engagement_id,
            'procedure_id': self.procedure_id,
            'ref_number': self.ref_number,
            'title': self.title,
            'condition': self.condition,
            'criteria': self.criteria,
            'cause': self.cause,
            'effect': self.effect,
            'recommendation': self.recommendation,
            'severity': self.severity.value if self.severity else None,
            'category': self.category,
            'risk_id': self.risk_id,
            'control_id': self.control_id,
            'violation_id': self.violation_id,
            'management_response': self.management_response,
            'management_action_owner': self.management_action_owner,
            'management_target_date': self.management_target_date.isoformat() if self.management_target_date else None,
            'status': self.status.value if self.status else None,
            'repeat_finding': self.repeat_finding,
            'prior_finding_id': self.prior_finding_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


# ---------------------------------------------------------------------------
# AuditManagementAction  (AM-21)
# ---------------------------------------------------------------------------

class AuditManagementAction(Base, TimestampMixin):
    """
    Management action item raised from an audit finding (AM-21).

    Tracks completion, evidence of closure, and escalation level.  Named
    AuditManagementAction (not AuditAction) to avoid collision with the
    AuditAction enum in db/models/audit.py.
    """
    __tablename__ = 'audit_actions'

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Multi-tenant support
    tenant_id = Column(String(100), nullable=False, index=True, default='tenant_default')

    # Identity
    action_id = Column(String(100), nullable=False, index=True)

    # Parent finding
    finding_id = Column(Integer, ForeignKey('audit_findings.id'), nullable=False, index=True)

    # Description and ownership
    description = Column(Text, nullable=False)
    owner_id = Column(String(100), nullable=True)
    owner_name = Column(String(255), nullable=True)

    # Due dates
    due_date = Column(DateTime, nullable=True)
    extended_due_date = Column(DateTime, nullable=True)

    # Completion
    completed_at = Column(DateTime, nullable=True)
    evidence_of_closure = Column(Text, nullable=True)
    evidence_ids = Column(JSON, nullable=True)    # list of grc_evidence IDs

    # Lifecycle
    status = Column(SQLEnum(ActionStatus), nullable=False, default=ActionStatus.OPEN)

    # Verification
    verified_by = Column(String(100), nullable=True)
    verified_at = Column(DateTime, nullable=True)

    # Escalation tracking
    escalation_level = Column(Integer, nullable=False, default=0)
    last_escalated_at = Column(DateTime, nullable=True)

    # Relationships
    finding = relationship('AuditFinding', back_populates='actions')

    def __repr__(self):
        return (
            f"<AuditManagementAction(action_id='{self.action_id}', "
            f"status='{self.status}', escalation_level={self.escalation_level})>"
        )

    def to_dict(self):
        return {
            'id': self.id,
            'tenant_id': self.tenant_id,
            'action_id': self.action_id,
            'finding_id': self.finding_id,
            'description': self.description,
            'owner_id': self.owner_id,
            'owner_name': self.owner_name,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'extended_due_date': self.extended_due_date.isoformat() if self.extended_due_date else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'evidence_of_closure': self.evidence_of_closure,
            'evidence_ids': self.evidence_ids,
            'status': self.status.value if self.status else None,
            'verified_by': self.verified_by,
            'verified_at': self.verified_at.isoformat() if self.verified_at else None,
            'escalation_level': self.escalation_level,
            'last_escalated_at': self.last_escalated_at.isoformat() if self.last_escalated_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


# ---------------------------------------------------------------------------
# AuditorTimeEntry  (AM-14)
# ---------------------------------------------------------------------------

class AuditorTimeEntry(Base, TimestampMixin):
    """
    Auditor time entry for engagement charge-back and productivity tracking (AM-14).

    Entries are linked to both an engagement and optionally the specific
    procedure that consumed the time.
    """
    __tablename__ = 'auditor_time_entries'

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Multi-tenant support
    tenant_id = Column(String(100), nullable=False, index=True, default='tenant_default')

    # Parent engagement and optional procedure
    engagement_id = Column(Integer, ForeignKey('audit_engagements.id'), nullable=False, index=True)
    procedure_id = Column(Integer, ForeignKey('audit_procedures.id'), nullable=True, index=True)

    # Auditor
    auditor_id = Column(String(100), nullable=False, index=True)
    auditor_name = Column(String(255), nullable=True)

    # Time record
    date = Column(DateTime, nullable=False)
    hours = Column(Float, nullable=False)
    activity_type = Column(String(50), nullable=True)   # planning, fieldwork, reporting, review, admin
    description = Column(Text, nullable=True)

    # Relationships
    engagement = relationship('AuditEngagement', back_populates='time_entries')

    def __repr__(self):
        return (
            f"<AuditorTimeEntry(auditor_id='{self.auditor_id}', "
            f"engagement_id={self.engagement_id}, hours={self.hours})>"
        )

    def to_dict(self):
        return {
            'id': self.id,
            'tenant_id': self.tenant_id,
            'engagement_id': self.engagement_id,
            'procedure_id': self.procedure_id,
            'auditor_id': self.auditor_id,
            'auditor_name': self.auditor_name,
            'date': self.date.isoformat() if self.date else None,
            'hours': self.hours,
            'activity_type': self.activity_type,
            'description': self.description,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


# ---------------------------------------------------------------------------
# AuditorResource  (AM-03)
# ---------------------------------------------------------------------------

class AuditorResource(Base, TimestampMixin):
    """
    Auditor resource record — skills, certifications, and availability (AM-03).

    Used by the audit planning module to match engagements to auditors with
    the right expertise and available capacity.
    """
    __tablename__ = 'auditor_resources'

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Multi-tenant support
    tenant_id = Column(String(100), nullable=False, index=True, default='tenant_default')

    # Identity (unique within tenant)
    auditor_id = Column(String(100), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=True)
    title = Column(String(255), nullable=True)

    # Competencies
    skills = Column(JSON, nullable=True)           # ["GovernexPlus", "IFRS", "IT Audit", ...]
    certifications = Column(JSON, nullable=True)   # ["CIA", "CISA", "CPA", "CISM", ...]

    # Capacity
    available_hours_per_month = Column(Float, nullable=False, default=160.0)

    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    is_external = Column(Boolean, default=False, nullable=False)   # co-sourced / guest auditor

    def __repr__(self):
        return (
            f"<AuditorResource(auditor_id='{self.auditor_id}', "
            f"name='{self.name}', is_external={self.is_external})>"
        )

    def to_dict(self):
        return {
            'id': self.id,
            'tenant_id': self.tenant_id,
            'auditor_id': self.auditor_id,
            'name': self.name,
            'email': self.email,
            'title': self.title,
            'skills': self.skills,
            'certifications': self.certifications,
            'available_hours_per_month': self.available_hours_per_month,
            'is_active': self.is_active,
            'is_external': self.is_external,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


# ---------------------------------------------------------------------------
# AuditDimension  (AM-SAP-GAP-11)
# ---------------------------------------------------------------------------

class AuditDimension(Base, TimestampMixin):
    """
    Multi-perspective audit dimension for coverage analysis.

    Dimensions allow audit plans and engagements to be viewed through
    multiple lenses simultaneously (e.g. by legal entity AND by process AND
    by IT system).  The hierarchy JSON stores the dimension's tree structure
    (AM-SAP-GAP-11).
    """
    __tablename__ = 'audit_dimensions'

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Multi-tenant support
    tenant_id = Column(String(100), nullable=False, index=True, default='tenant_default')

    # Identity — auto-generated as DIM-{seq}
    dimension_id = Column(String(100), nullable=False, index=True)
    name = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)

    # Classification
    dimension_type = Column(SQLEnum(DimensionType), nullable=False)

    # Tree structure — [{id, name, parent_id, children: [...]}]
    hierarchy = Column(JSON, nullable=True)

    is_active = Column(Boolean, default=True, nullable=False)

    def __repr__(self):
        return (
            f"<AuditDimension(dimension_id='{self.dimension_id}', "
            f"name='{self.name[:50]}', type='{self.dimension_type}')>"
        )

    def to_dict(self):
        return {
            'id': self.id,
            'tenant_id': self.tenant_id,
            'dimension_id': self.dimension_id,
            'name': self.name,
            'description': self.description,
            'dimension_type': self.dimension_type.value if self.dimension_type else None,
            'hierarchy': self.hierarchy,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


# ---------------------------------------------------------------------------
# AuditAnnouncement  (AM-SAP-GAP-12)
# ---------------------------------------------------------------------------

class AuditAnnouncement(Base, TimestampMixin):
    """
    Formal audit announcement sent to auditees.

    Records the announcement communication (subject + body), the recipient
    list with acknowledgment timestamps, and the sending auditor.  This
    closes the GovernexPlus AM gap for formal engagement kick-off notifications
    (AM-SAP-GAP-12).
    """
    __tablename__ = 'audit_announcements'

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Multi-tenant support
    tenant_id = Column(String(100), nullable=False, index=True, default='tenant_default')

    # Identity — auto-generated as ANN-{seq}
    announcement_id = Column(String(100), nullable=False, index=True)

    # Parent engagement
    engagement_id = Column(Integer, ForeignKey('audit_engagements.id'), nullable=False, index=True)

    # Recipients — [{id, name, email}]
    recipients = Column(JSON, nullable=True)

    # Communication content
    subject = Column(String(500), nullable=False)
    body = Column(Text, nullable=False)

    # Sending metadata
    sent_at = Column(DateTime, nullable=True)
    sent_by = Column(String(100), nullable=True)

    # Acknowledgment tracking — [{id, acknowledged_at}]
    acknowledgments = Column(JSON, nullable=True)

    # Lifecycle
    status = Column(SQLEnum(AnnouncementStatus), nullable=False, default=AnnouncementStatus.DRAFT)

    # Relationships
    engagement = relationship('AuditEngagement')

    def __repr__(self):
        return (
            f"<AuditAnnouncement(announcement_id='{self.announcement_id}', "
            f"engagement_id={self.engagement_id}, status='{self.status}')>"
        )

    def to_dict(self):
        return {
            'id': self.id,
            'tenant_id': self.tenant_id,
            'announcement_id': self.announcement_id,
            'engagement_id': self.engagement_id,
            'recipients': self.recipients,
            'subject': self.subject,
            'body': self.body,
            'sent_at': self.sent_at.isoformat() if self.sent_at else None,
            'sent_by': self.sent_by,
            'acknowledgments': self.acknowledgments,
            'status': self.status.value if self.status else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
