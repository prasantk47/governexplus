"""
Database Models - Risk Management Module

Full Risk Management module covering RM-01 through RM-31:
  - EnterpriseRisk          : the risk register (RM-01)
  - RiskAssessment          : periodic / ad-hoc assessment records (RM-10, RM-11)
  - RiskAppetite            : per category / org-unit appetite & tolerance (RM-03)
  - KeyRiskIndicator        : KRI definitions and thresholds (RM-13)
  - KRIMeasurement          : historical KRI readings
  - RiskResponse            : response plans (RM-20)
  - RiskIncident            : loss / incident events (RM-22)
  - BusinessObjective       : link risks to business objectives (RM-SAP-GAP-01)
  - RiskScenario            : multi-driver cascading scenarios (RM-SAP-GAP-02)
  - MonteCarloSimulation    : Monte Carlo simulation run results (RM-SAP-GAP-03)
  - RiskOpportunity         : positive risk / opportunity tracking (RM-SAP-GAP-04)
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

class RiskCategory(enum.Enum):
    """Enterprise risk categories"""
    STRATEGIC = "strategic"
    OPERATIONAL = "operational"
    FINANCIAL = "financial"
    COMPLIANCE = "compliance"
    IT_CYBER = "it_cyber"
    REPUTATIONAL = "reputational"


class RiskStatus(enum.Enum):
    """Lifecycle status of an enterprise risk"""
    IDENTIFIED = "identified"
    ASSESSED = "assessed"
    MITIGATED = "mitigated"
    ACCEPTED = "accepted"
    CLOSED = "closed"


class AssessmentType(enum.Enum):
    """Type of risk assessment"""
    PERIODIC = "periodic"
    ADHOC = "adhoc"
    CONSENSUS = "consensus"


class AssessmentStatus(enum.Enum):
    """Workflow status of a risk assessment"""
    DRAFT = "draft"
    SUBMITTED = "submitted"
    REVIEWED = "reviewed"
    APPROVED = "approved"


class KRIStatus(enum.Enum):
    """Traffic-light status of a KRI"""
    NORMAL = "normal"
    WARNING = "warning"
    BREACH = "breach"


class RiskResponseType(enum.Enum):
    """How the organisation will respond to a risk"""
    ACCEPT = "accept"
    MITIGATE = "mitigate"
    TRANSFER = "transfer"
    AVOID = "avoid"


class ResponseStatus(enum.Enum):
    """Execution status of a risk response plan"""
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    OVERDUE = "overdue"


class IncidentSeverity(enum.Enum):
    """Severity classification of a risk incident"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class IncidentStatus(enum.Enum):
    """Lifecycle status of an incident"""
    REPORTED = "reported"
    INVESTIGATING = "investigating"
    RESOLVED = "resolved"
    CLOSED = "closed"


class ObjectiveCategory(enum.Enum):
    """Categories for business objectives"""
    STRATEGIC = "strategic"
    FINANCIAL = "financial"
    OPERATIONAL = "operational"
    COMPLIANCE = "compliance"
    GROWTH = "growth"


class ObjectiveStatus(enum.Enum):
    """Lifecycle status of a business objective"""
    ACTIVE = "active"
    ACHIEVED = "achieved"
    AT_RISK = "at_risk"
    FAILED = "failed"


class ScenarioType(enum.Enum):
    """Type of risk scenario"""
    SINGLE_EVENT = "single_event"
    CASCADING = "cascading"
    COMPOUND = "compound"
    STRESS_TEST = "stress_test"


class ScenarioVelocity(enum.Enum):
    """Speed at which a risk scenario would materialise"""
    SUDDEN = "sudden"
    RAPID = "rapid"
    MODERATE = "moderate"
    GRADUAL = "gradual"


class ScenarioStatus(enum.Enum):
    """Lifecycle status of a risk scenario"""
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"


class DistributionType(enum.Enum):
    """Statistical distribution type for Monte Carlo inputs"""
    NORMAL = "normal"
    LOGNORMAL = "lognormal"
    TRIANGULAR = "triangular"
    UNIFORM = "uniform"
    PERT = "pert"


class OpportunityCategory(enum.Enum):
    """Category of a risk opportunity"""
    STRATEGIC = "strategic"
    FINANCIAL = "financial"
    OPERATIONAL = "operational"
    INNOVATION = "innovation"
    MARKET = "market"


class OpportunityStatus(enum.Enum):
    """Lifecycle status of a risk opportunity"""
    IDENTIFIED = "identified"
    EVALUATING = "evaluating"
    PURSUING = "pursuing"
    REALIZED = "realized"
    DECLINED = "declined"


# ---------------------------------------------------------------------------
# EnterpriseRisk  (RM-01)
# ---------------------------------------------------------------------------

class EnterpriseRisk(Base, TimestampMixin):
    """
    Enterprise Risk Register entry.

    Each record represents one identified organisational risk with full
    inherent / residual scoring, ownership, review scheduling, and links
    to controls and findings.  Supports Arabic descriptions for bilingual
    tenants (RM-01).
    """
    __tablename__ = 'enterprise_risks'

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Multi-tenant support
    tenant_id = Column(String(100), nullable=False, index=True, default='tenant_default')

    # Identity
    risk_id = Column(String(100), nullable=False, index=True)   # unique within tenant
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    description_ar = Column(Text, nullable=True)                # Arabic translation

    # Classification
    category = Column(SQLEnum(RiskCategory), nullable=False)
    org_unit_id = Column(Integer, ForeignKey('org_units.id'), nullable=True, index=True)

    # Ownership
    risk_owner_id = Column(String(100), nullable=True)
    risk_owner_name = Column(String(255), nullable=True)

    # Inherent risk scoring (before controls)
    inherent_likelihood = Column(Integer, nullable=True)   # 1-5
    inherent_impact = Column(Integer, nullable=True)       # 1-5
    inherent_score = Column(Float, nullable=True)          # computed: likelihood × impact

    # Residual risk scoring (after controls)
    residual_likelihood = Column(Integer, nullable=True)   # 1-5
    residual_impact = Column(Integer, nullable=True)       # 1-5
    residual_score = Column(Float, nullable=True)          # computed: likelihood × impact

    # Appetite / tolerance
    risk_appetite = Column(Float, nullable=True)
    risk_tolerance = Column(Float, nullable=True)

    # Lifecycle
    status = Column(SQLEnum(RiskStatus), nullable=False, default=RiskStatus.IDENTIFIED)

    # Review scheduling
    last_assessed_at = Column(DateTime, nullable=True)
    next_review_date = Column(DateTime, nullable=True)
    review_frequency = Column(String(50), nullable=True)   # e.g. "quarterly", "annual"

    # Linked objects (stored as JSON arrays of IDs)
    related_control_ids = Column(JSON, nullable=True)
    related_finding_ids = Column(JSON, nullable=True)

    # Extension bag
    metadata_ = Column('metadata', JSON, nullable=True)

    # XL-A: Control coverage feedback (Loop A)
    # Reflects degraded coverage when linked PC controls fail — never silently
    # overwrites the assessor's residual_score; uses system_indicated_residual instead.
    control_coverage = Column(String(20), default='effective')  # effective/degraded/failed/uncontrolled
    system_indicated_residual = Column(Float, nullable=True)
    coverage_computed_at = Column(DateTime, nullable=True)

    # GovernexPlus gap: velocity and business objective linkage
    velocity = Column(String(50), nullable=True)            # sudden/rapid/moderate/gradual
    business_objective_id = Column(String(100), nullable=True)  # links to business_objectives.objective_id

    # Status
    is_active = Column(Boolean, default=True, nullable=False)

    # Relationships
    assessments = relationship('RiskAssessment', back_populates='risk')
    responses = relationship('RiskResponse', back_populates='risk')
    incidents = relationship('RiskIncident', back_populates='risk')
    kris = relationship('KeyRiskIndicator', back_populates='risk')

    def __repr__(self):
        return (
            f"<EnterpriseRisk(risk_id='{self.risk_id}', "
            f"title='{self.title[:50]}', status='{self.status}')>"
        )

    def to_dict(self):
        return {
            'id': self.id,
            'tenant_id': self.tenant_id,
            'risk_id': self.risk_id,
            'title': self.title,
            'description': self.description,
            'description_ar': self.description_ar,
            'category': self.category.value if self.category else None,
            'org_unit_id': self.org_unit_id,
            'risk_owner_id': self.risk_owner_id,
            'risk_owner_name': self.risk_owner_name,
            'inherent_likelihood': self.inherent_likelihood,
            'inherent_impact': self.inherent_impact,
            'inherent_score': self.inherent_score,
            'residual_likelihood': self.residual_likelihood,
            'residual_impact': self.residual_impact,
            'residual_score': self.residual_score,
            'risk_appetite': self.risk_appetite,
            'risk_tolerance': self.risk_tolerance,
            'status': self.status.value if self.status else None,
            'last_assessed_at': self.last_assessed_at.isoformat() if self.last_assessed_at else None,
            'next_review_date': self.next_review_date.isoformat() if self.next_review_date else None,
            'review_frequency': self.review_frequency,
            'related_control_ids': self.related_control_ids,
            'related_finding_ids': self.related_finding_ids,
            'metadata': self.metadata_,
            'is_active': self.is_active,
            # XL-A: control coverage feedback fields
            'control_coverage': self.control_coverage,
            'system_indicated_residual': self.system_indicated_residual,
            'coverage_computed_at': self.coverage_computed_at.isoformat() if self.coverage_computed_at else None,
            # GovernexPlus gap fields
            'velocity': self.velocity,
            'business_objective_id': self.business_objective_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


# ---------------------------------------------------------------------------
# RiskAssessment  (RM-10, RM-11)
# ---------------------------------------------------------------------------

class RiskAssessment(Base, TimestampMixin):
    """
    Periodic or ad-hoc risk assessment record.

    Captures the assessor's scoring rationale, optional monetary impact
    estimate, and workflow status for each assessment event (RM-10, RM-11).
    """
    __tablename__ = 'risk_assessments'

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Multi-tenant support
    tenant_id = Column(String(100), nullable=False, index=True, default='tenant_default')

    # Identity
    assessment_id = Column(String(100), nullable=False, index=True)

    # Parent risk
    risk_id = Column(Integer, ForeignKey('enterprise_risks.id'), nullable=False, index=True)

    # Assessor
    assessor_id = Column(String(100), nullable=True)
    assessor_name = Column(String(255), nullable=True)

    # Scoring
    likelihood_score = Column(Integer, nullable=False)    # 1-5
    impact_score = Column(Integer, nullable=False)        # 1-5
    overall_score = Column(Float, nullable=False)         # computed

    # Assessment type
    assessment_type = Column(SQLEnum(AssessmentType), nullable=False, default=AssessmentType.PERIODIC)

    # Rationale
    likelihood_rationale = Column(Text, nullable=True)
    impact_rationale = Column(Text, nullable=True)

    # Financial impact
    monetary_impact = Column(Float, nullable=True)
    currency = Column(String(3), default='USD', nullable=False)

    # Workflow
    status = Column(SQLEnum(AssessmentStatus), nullable=False, default=AssessmentStatus.DRAFT)
    reviewed_by = Column(String(100), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    comments = Column(Text, nullable=True)

    # Relationships
    risk = relationship('EnterpriseRisk', back_populates='assessments')

    def __repr__(self):
        return (
            f"<RiskAssessment(assessment_id='{self.assessment_id}', "
            f"risk_id={self.risk_id}, score={self.overall_score})>"
        )

    def to_dict(self):
        return {
            'id': self.id,
            'tenant_id': self.tenant_id,
            'assessment_id': self.assessment_id,
            'risk_id': self.risk_id,
            'assessor_id': self.assessor_id,
            'assessor_name': self.assessor_name,
            'likelihood_score': self.likelihood_score,
            'impact_score': self.impact_score,
            'overall_score': self.overall_score,
            'assessment_type': self.assessment_type.value if self.assessment_type else None,
            'likelihood_rationale': self.likelihood_rationale,
            'impact_rationale': self.impact_rationale,
            'monetary_impact': self.monetary_impact,
            'currency': self.currency,
            'status': self.status.value if self.status else None,
            'reviewed_by': self.reviewed_by,
            'reviewed_at': self.reviewed_at.isoformat() if self.reviewed_at else None,
            'comments': self.comments,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


# ---------------------------------------------------------------------------
# RiskAppetite  (RM-03)
# ---------------------------------------------------------------------------

class RiskAppetite(Base, TimestampMixin):
    """
    Risk appetite and tolerance thresholds per category / org unit (RM-03).

    Allows the board / risk committee to define acceptable risk levels at
    category granularity, with optional scoping to a specific org unit.
    """
    __tablename__ = 'risk_appetites'

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Multi-tenant support
    tenant_id = Column(String(100), nullable=False, index=True, default='tenant_default')

    # Scope
    category = Column(String(100), nullable=False)     # maps to RiskCategory values or 'all'
    org_unit_id = Column(Integer, ForeignKey('org_units.id'), nullable=True, index=True)

    # Thresholds
    appetite_score = Column(Float, nullable=False)
    tolerance_score = Column(Float, nullable=False)

    # Documentation
    description = Column(Text, nullable=True)

    # Approval
    approved_by = Column(String(100), nullable=True)
    approved_at = Column(DateTime, nullable=True)

    # Validity window
    effective_from = Column(DateTime, nullable=True)
    effective_to = Column(DateTime, nullable=True)

    def __repr__(self):
        return (
            f"<RiskAppetite(category='{self.category}', "
            f"appetite={self.appetite_score}, tolerance={self.tolerance_score})>"
        )

    def to_dict(self):
        return {
            'id': self.id,
            'tenant_id': self.tenant_id,
            'category': self.category,
            'org_unit_id': self.org_unit_id,
            'appetite_score': self.appetite_score,
            'tolerance_score': self.tolerance_score,
            'description': self.description,
            'approved_by': self.approved_by,
            'approved_at': self.approved_at.isoformat() if self.approved_at else None,
            'effective_from': self.effective_from.isoformat() if self.effective_from else None,
            'effective_to': self.effective_to.isoformat() if self.effective_to else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


# ---------------------------------------------------------------------------
# KeyRiskIndicator  (RM-13)
# ---------------------------------------------------------------------------

class KeyRiskIndicator(Base, TimestampMixin):
    """
    KRI definition, data-source configuration, and threshold settings (RM-13).

    Thresholds follow a traffic-light model: values below threshold_green are
    normal, between green and amber trigger a warning, above amber (or above
    threshold_red) trigger a breach alert.
    """
    __tablename__ = 'key_risk_indicators'

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Multi-tenant support
    tenant_id = Column(String(100), nullable=False, index=True, default='tenant_default')

    # Identity
    kri_id = Column(String(100), nullable=False, index=True)   # unique within tenant
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # Parent risk (optional — KRIs may be standalone)
    risk_id = Column(Integer, ForeignKey('enterprise_risks.id'), nullable=True, index=True)

    # Data collection
    data_source = Column(String(100), nullable=True)       # manual, api, connector
    unit_of_measure = Column(String(100), nullable=True)   # e.g. "count", "%", "USD"
    frequency = Column(String(50), nullable=True)          # daily, weekly, monthly

    # Thresholds
    threshold_green = Column(Float, nullable=True)
    threshold_amber = Column(Float, nullable=True)
    threshold_red = Column(Float, nullable=True)

    # Current reading
    current_value = Column(Float, nullable=True)
    last_measured_at = Column(DateTime, nullable=True)

    # Traffic-light status
    status = Column(SQLEnum(KRIStatus), nullable=False, default=KRIStatus.NORMAL)

    # Ownership
    owner_id = Column(String(100), nullable=True)

    # Status
    is_active = Column(Boolean, default=True, nullable=False)

    # Relationships
    risk = relationship('EnterpriseRisk', back_populates='kris')
    measurements = relationship('KRIMeasurement', back_populates='kri')

    def __repr__(self):
        return (
            f"<KeyRiskIndicator(kri_id='{self.kri_id}', "
            f"name='{self.name}', status='{self.status}')>"
        )

    def to_dict(self):
        return {
            'id': self.id,
            'tenant_id': self.tenant_id,
            'kri_id': self.kri_id,
            'name': self.name,
            'description': self.description,
            'risk_id': self.risk_id,
            'data_source': self.data_source,
            'unit_of_measure': self.unit_of_measure,
            'frequency': self.frequency,
            'threshold_green': self.threshold_green,
            'threshold_amber': self.threshold_amber,
            'threshold_red': self.threshold_red,
            'current_value': self.current_value,
            'last_measured_at': self.last_measured_at.isoformat() if self.last_measured_at else None,
            'status': self.status.value if self.status else None,
            'owner_id': self.owner_id,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


# ---------------------------------------------------------------------------
# KRIMeasurement
# ---------------------------------------------------------------------------

class KRIMeasurement(Base, TimestampMixin):
    """
    Historical reading of a Key Risk Indicator.

    Each row is an immutable point-in-time measurement that drives trending
    reports and retrospective threshold-breach analysis.
    """
    __tablename__ = 'kri_measurements'

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Multi-tenant support
    tenant_id = Column(String(100), nullable=False, index=True, default='tenant_default')

    # Parent KRI
    kri_id = Column(Integer, ForeignKey('key_risk_indicators.id'), nullable=False, index=True)

    # Reading
    value = Column(Float, nullable=False)
    measured_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    measured_by = Column(String(100), nullable=True)    # user ID or 'system'
    source = Column(String(100), nullable=True)         # manual, api, connector name
    notes = Column(Text, nullable=True)

    # Relationships
    kri = relationship('KeyRiskIndicator', back_populates='measurements')

    def __repr__(self):
        return (
            f"<KRIMeasurement(kri_id={self.kri_id}, "
            f"value={self.value}, measured_at='{self.measured_at}')>"
        )

    def to_dict(self):
        return {
            'id': self.id,
            'tenant_id': self.tenant_id,
            'kri_id': self.kri_id,
            'value': self.value,
            'measured_at': self.measured_at.isoformat() if self.measured_at else None,
            'measured_by': self.measured_by,
            'source': self.source,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


# ---------------------------------------------------------------------------
# RiskResponse  (RM-20)
# ---------------------------------------------------------------------------

class RiskResponse(Base, TimestampMixin):
    """
    Risk response plan for an identified enterprise risk (RM-20).

    Captures the chosen response strategy (accept / mitigate / transfer /
    avoid), a structured action-item list, and tracks completion.
    """
    __tablename__ = 'risk_responses'

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Multi-tenant support
    tenant_id = Column(String(100), nullable=False, index=True, default='tenant_default')

    # Identity
    response_id = Column(String(100), nullable=False, index=True)

    # Parent risk
    risk_id = Column(Integer, ForeignKey('enterprise_risks.id'), nullable=False, index=True)

    # Strategy
    response_type = Column(SQLEnum(RiskResponseType), nullable=False)
    description = Column(Text, nullable=True)

    # Ownership
    owner_id = Column(String(100), nullable=True)
    owner_name = Column(String(255), nullable=True)

    # Action items  — JSON list of {description, due_date, owner, status}
    actions = Column(JSON, nullable=True)

    # Lifecycle
    status = Column(SQLEnum(ResponseStatus), nullable=False, default=ResponseStatus.PLANNED)
    due_date = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # Effectiveness (1-5 rating post-completion)
    effectiveness_rating = Column(Integer, nullable=True)

    # Relationships
    risk = relationship('EnterpriseRisk', back_populates='responses')

    def __repr__(self):
        return (
            f"<RiskResponse(response_id='{self.response_id}', "
            f"type='{self.response_type}', status='{self.status}')>"
        )

    def to_dict(self):
        return {
            'id': self.id,
            'tenant_id': self.tenant_id,
            'response_id': self.response_id,
            'risk_id': self.risk_id,
            'response_type': self.response_type.value if self.response_type else None,
            'description': self.description,
            'owner_id': self.owner_id,
            'owner_name': self.owner_name,
            'actions': self.actions,
            'status': self.status.value if self.status else None,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'effectiveness_rating': self.effectiveness_rating,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


# ---------------------------------------------------------------------------
# RiskIncident  (RM-22)
# ---------------------------------------------------------------------------

class RiskIncident(Base, TimestampMixin):
    """
    Loss event / operational risk incident record (RM-22).

    Captures incidents that materialise a risk, including financial impact,
    timeline (occurred → detected → resolved), root-cause analysis, and
    corrective action tracking.
    """
    __tablename__ = 'risk_incidents'

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Multi-tenant support
    tenant_id = Column(String(100), nullable=False, index=True, default='tenant_default')

    # Identity
    incident_id = Column(String(100), nullable=False, index=True)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)

    # Link to risk register (optional — incidents may be standalone)
    risk_id = Column(Integer, ForeignKey('enterprise_risks.id'), nullable=True, index=True)

    # Classification
    severity = Column(SQLEnum(IncidentSeverity), nullable=False)

    # Financial impact
    financial_impact = Column(Float, nullable=True)
    currency = Column(String(3), nullable=True)

    # Loss management — insurance recovery tracking
    recovery_amount = Column(Float, nullable=True)      # total amount recovered
    insurance_claim = Column(Float, nullable=True)      # gross insurance claim filed
    insurance_recovery = Column(Float, nullable=True)   # amount actually received from insurer

    # Timeline
    occurred_at = Column(DateTime, nullable=True)
    detected_at = Column(DateTime, nullable=True)
    resolved_at = Column(DateTime, nullable=True)

    # Analysis
    root_cause = Column(Text, nullable=True)
    corrective_actions = Column(JSON, nullable=True)   # list of {action, owner, due_date, status}

    # Reporting
    reported_by = Column(String(100), nullable=True)

    # Lifecycle
    status = Column(SQLEnum(IncidentStatus), nullable=False, default=IncidentStatus.REPORTED)

    # Relationships
    risk = relationship('EnterpriseRisk', back_populates='incidents')

    def __repr__(self):
        return (
            f"<RiskIncident(incident_id='{self.incident_id}', "
            f"severity='{self.severity}', status='{self.status}')>"
        )

    def to_dict(self):
        return {
            'id': self.id,
            'tenant_id': self.tenant_id,
            'incident_id': self.incident_id,
            'title': self.title,
            'description': self.description,
            'risk_id': self.risk_id,
            'severity': self.severity.value if self.severity else None,
            'financial_impact': self.financial_impact,
            'currency': self.currency,
            'recovery_amount': self.recovery_amount,
            'insurance_claim': self.insurance_claim,
            'insurance_recovery': self.insurance_recovery,
            'occurred_at': self.occurred_at.isoformat() if self.occurred_at else None,
            'detected_at': self.detected_at.isoformat() if self.detected_at else None,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None,
            'root_cause': self.root_cause,
            'corrective_actions': self.corrective_actions,
            'reported_by': self.reported_by,
            'status': self.status.value if self.status else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


# ---------------------------------------------------------------------------
# BusinessObjective  (RM-SAP-GAP-01)
# ---------------------------------------------------------------------------

class BusinessObjective(Base, TimestampMixin):
    """
    Business objective entity linking risks to strategic/operational goals.

    Enables risk-to-objective traceability so the board can see which
    objectives are threatened by which risks, closing the RM GovernexPlus gap
    for objective-based risk mapping (RM-SAP-GAP-01).
    """
    __tablename__ = 'business_objectives'

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Multi-tenant support
    tenant_id = Column(String(100), nullable=False, index=True, default='tenant_default')

    # Identity — auto-generated as RSK-OBJ-{seq}
    objective_id = Column(String(100), nullable=False, index=True)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)

    # Classification
    category = Column(SQLEnum(ObjectiveCategory), nullable=False)

    # Organisational scope
    org_unit_id = Column(Integer, ForeignKey('org_units.id'), nullable=True, index=True)

    # Ownership
    owner_id = Column(String(100), nullable=True)
    owner_name = Column(String(255), nullable=True)

    # Timeline
    target_date = Column(DateTime, nullable=True)

    # Lifecycle
    status = Column(SQLEnum(ObjectiveStatus), nullable=False, default=ObjectiveStatus.ACTIVE)

    # Linked risk IDs (JSON array of EnterpriseRisk.risk_id values)
    linked_risk_ids = Column(JSON, nullable=True)

    # Status flag
    is_active = Column(Boolean, default=True, nullable=False)

    # Extension bag
    metadata_ = Column('metadata', JSON, nullable=True)

    def __repr__(self):
        return (
            f"<BusinessObjective(objective_id='{self.objective_id}', "
            f"title='{self.title[:50]}', status='{self.status}')>"
        )

    def to_dict(self):
        return {
            'id': self.id,
            'tenant_id': self.tenant_id,
            'objective_id': self.objective_id,
            'title': self.title,
            'description': self.description,
            'category': self.category.value if self.category else None,
            'org_unit_id': self.org_unit_id,
            'owner_id': self.owner_id,
            'owner_name': self.owner_name,
            'target_date': self.target_date.isoformat() if self.target_date else None,
            'status': self.status.value if self.status else None,
            'linked_risk_ids': self.linked_risk_ids,
            'is_active': self.is_active,
            'metadata': self.metadata_,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


# ---------------------------------------------------------------------------
# RiskScenario  (RM-SAP-GAP-02)
# ---------------------------------------------------------------------------

class RiskScenario(Base, TimestampMixin):
    """
    Multi-driver cascading risk scenario definition.

    Captures compound events, trigger chains, and cascading effects for
    scenario-based risk analysis.  Supports Monte Carlo linkage via the
    simulation_results JSON field (RM-SAP-GAP-02).
    """
    __tablename__ = 'risk_scenarios'

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Multi-tenant support
    tenant_id = Column(String(100), nullable=False, index=True, default='tenant_default')

    # Identity — auto-generated as SCN-{seq}
    scenario_id = Column(String(100), nullable=False, index=True)
    name = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)

    # Classification
    scenario_type = Column(SQLEnum(ScenarioType), nullable=False)

    # Linked risk IDs (JSON array of EnterpriseRisk.risk_id values)
    risk_ids = Column(JSON, nullable=True)

    # Scenario structure
    trigger_events = Column(JSON, nullable=True)       # list of trigger descriptions
    cascading_effects = Column(JSON, nullable=True)    # ordered list of cascading effects

    # Probability and impact range
    probability = Column(Float, nullable=True)         # 0.0 – 1.0
    impact_low = Column(Float, nullable=False, default=0.0)
    impact_mid = Column(Float, nullable=False, default=0.0)
    impact_high = Column(Float, nullable=False, default=0.0)

    # Time horizon
    time_horizon = Column(String(50), nullable=True)   # immediate/short_term/medium_term/long_term

    # Velocity at which the scenario would unfold
    velocity = Column(SQLEnum(ScenarioVelocity), nullable=True)

    # Lifecycle
    status = Column(SQLEnum(ScenarioStatus), nullable=False, default=ScenarioStatus.DRAFT)

    # Authorship and simulation tracking
    created_by = Column(String(100), nullable=True)
    last_simulated_at = Column(DateTime, nullable=True)

    # Monte Carlo output cache (p5/p25/p50/p75/p95/mean/std_dev/var/cvar/max_loss)
    simulation_results = Column(JSON, nullable=True)

    # Relationships
    simulations = relationship('MonteCarloSimulation', back_populates='scenario')

    def __repr__(self):
        return (
            f"<RiskScenario(scenario_id='{self.scenario_id}', "
            f"name='{self.name[:50]}', type='{self.scenario_type}')>"
        )

    def to_dict(self):
        return {
            'id': self.id,
            'tenant_id': self.tenant_id,
            'scenario_id': self.scenario_id,
            'name': self.name,
            'description': self.description,
            'scenario_type': self.scenario_type.value if self.scenario_type else None,
            'risk_ids': self.risk_ids,
            'trigger_events': self.trigger_events,
            'cascading_effects': self.cascading_effects,
            'probability': self.probability,
            'impact_low': self.impact_low,
            'impact_mid': self.impact_mid,
            'impact_high': self.impact_high,
            'time_horizon': self.time_horizon,
            'velocity': self.velocity.value if self.velocity else None,
            'status': self.status.value if self.status else None,
            'created_by': self.created_by,
            'last_simulated_at': self.last_simulated_at.isoformat() if self.last_simulated_at else None,
            'simulation_results': self.simulation_results,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


# ---------------------------------------------------------------------------
# MonteCarloSimulation  (RM-SAP-GAP-03)
# ---------------------------------------------------------------------------

class MonteCarloSimulation(Base, TimestampMixin):
    """
    Monte Carlo simulation run result.

    Stores full distributional output (percentiles, VaR, CVaR) for a single
    execution run.  Can be linked to a scenario or a standalone enterprise
    risk.  Execution metadata allows reproducibility (RM-SAP-GAP-03).
    """
    __tablename__ = 'monte_carlo_simulations'

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Multi-tenant support
    tenant_id = Column(String(100), nullable=False, index=True, default='tenant_default')

    # Identity — auto-generated as MCS-{seq}
    simulation_id = Column(String(100), nullable=False, index=True)

    # Parent links (one of these will be populated)
    scenario_id = Column(Integer, ForeignKey('risk_scenarios.id'), nullable=True, index=True)
    risk_id = Column(Integer, ForeignKey('enterprise_risks.id'), nullable=True, index=True)

    # Distribution configuration
    distribution_type = Column(SQLEnum(DistributionType), nullable=False)
    iterations = Column(Integer, nullable=False, default=10000)

    # Input parameters (distribution-specific: mean/std_dev, low/mid/high, min/max, etc.)
    input_parameters = Column(JSON, nullable=False)

    # Distributional results
    # Expected keys: p5, p25, p50, p75, p95, mean, std_dev, var, cvar, max_loss
    results = Column(JSON, nullable=True)

    # Execution metadata
    executed_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    executed_by = Column(String(100), nullable=True)
    execution_time_ms = Column(Integer, nullable=True)

    # Relationships
    scenario = relationship('RiskScenario', back_populates='simulations')

    def __repr__(self):
        return (
            f"<MonteCarloSimulation(simulation_id='{self.simulation_id}', "
            f"iterations={self.iterations}, dist='{self.distribution_type}')>"
        )

    def to_dict(self):
        return {
            'id': self.id,
            'tenant_id': self.tenant_id,
            'simulation_id': self.simulation_id,
            'scenario_id': self.scenario_id,
            'risk_id': self.risk_id,
            'distribution_type': self.distribution_type.value if self.distribution_type else None,
            'iterations': self.iterations,
            'input_parameters': self.input_parameters,
            'results': self.results,
            'executed_at': self.executed_at.isoformat() if self.executed_at else None,
            'executed_by': self.executed_by,
            'execution_time_ms': self.execution_time_ms,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


# ---------------------------------------------------------------------------
# RiskOpportunity  (RM-SAP-GAP-04)
# ---------------------------------------------------------------------------

class RiskOpportunity(Base, TimestampMixin):
    """
    Positive risk / opportunity tracking.

    Represents an upside risk or strategic opportunity, including probability,
    potential upside, investment required, and realised value tracking.
    Linked risks indicate which threats this opportunity could offset
    (RM-SAP-GAP-04).
    """
    __tablename__ = 'risk_opportunities'

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Multi-tenant support
    tenant_id = Column(String(100), nullable=False, index=True, default='tenant_default')

    # Identity — auto-generated as OPP-{seq}
    opportunity_id = Column(String(100), nullable=False, index=True)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)

    # Classification
    category = Column(SQLEnum(OpportunityCategory), nullable=False)

    # Organisational scope
    org_unit_id = Column(Integer, ForeignKey('org_units.id'), nullable=True, index=True)

    # Ownership
    owner_id = Column(String(100), nullable=True)
    owner_name = Column(String(255), nullable=True)

    # Financial parameters
    probability = Column(Float, nullable=True)             # 0.0 – 1.0
    potential_upside = Column(Float, nullable=True)
    investment_required = Column(Float, nullable=True)
    currency = Column(String(3), nullable=False, default='USD')

    # Time horizon
    time_horizon = Column(String(50), nullable=True)       # immediate/short_term/medium_term/long_term

    # Lifecycle
    status = Column(SQLEnum(OpportunityStatus), nullable=False, default=OpportunityStatus.IDENTIFIED)

    # Links to risks this opportunity could offset (JSON array of risk_id values)
    linked_risk_ids = Column(JSON, nullable=True)

    # Action items — list of {description, owner, due_date, status}
    actions = Column(JSON, nullable=True)

    # Realisation tracking
    realized_value = Column(Float, nullable=True)
    realized_at = Column(DateTime, nullable=True)

    def __repr__(self):
        return (
            f"<RiskOpportunity(opportunity_id='{self.opportunity_id}', "
            f"title='{self.title[:50]}', status='{self.status}')>"
        )

    def to_dict(self):
        return {
            'id': self.id,
            'tenant_id': self.tenant_id,
            'opportunity_id': self.opportunity_id,
            'title': self.title,
            'description': self.description,
            'category': self.category.value if self.category else None,
            'org_unit_id': self.org_unit_id,
            'owner_id': self.owner_id,
            'owner_name': self.owner_name,
            'probability': self.probability,
            'potential_upside': self.potential_upside,
            'investment_required': self.investment_required,
            'currency': self.currency,
            'time_horizon': self.time_horizon,
            'status': self.status.value if self.status else None,
            'linked_risk_ids': self.linked_risk_ids,
            'actions': self.actions,
            'realized_value': self.realized_value,
            'realized_at': self.realized_at.isoformat() if self.realized_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
