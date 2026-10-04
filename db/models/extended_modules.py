"""
Database Models - Extended Modules

Covers 6 additional GRC modules:
  JML (Joiner-Mover-Leaver):
    - JmlPolicy             : lifecycle policy definitions per event type
    - JmlEvent              : individual provisioning / de-provisioning events

  TPRM (Third-Party Risk Management):
    - Vendor                : vendor registry with risk tiering
    - VendorAssessment      : questionnaire-based vendor risk assessments
    - VendorIssue           : issues / findings raised against a vendor
    - VendorContract        : contract lifecycle tracking

  Fraud Detection:
    - FraudRule             : detection rules (velocity / threshold / pattern / anomaly)
    - FraudAlert            : alerts triggered by rules
    - FraudCase             : investigation cases linking multiple alerts

  BCM (Business Continuity Management):
    - BiaRecord             : Business Impact Analysis records
    - BcmPlan               : BCP / DRP / crisis plans
    - BcmTestExercise       : plan testing and exercise records
    - IncidentActivation    : plan activations during real incidents

  Whistleblower:
    - WhistleblowerCase     : anonymous / named disclosures
    - WhistleblowerMessage  : threaded communications on a case

  Survey (standalone):
    - StandaloneSurvey      : survey definitions
    - SurveyDistribution    : per-recipient distribution records
    - SurveyAnswer          : submitted responses
"""

from sqlalchemy import (
    Column, String, Boolean, DateTime, Text,
    JSON, Float, Integer, Enum as SQLEnum
)
from datetime import datetime
import enum
import uuid

from .base import Base, TimestampMixin


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _uuid() -> str:
    return str(uuid.uuid4())


# ===========================================================================
# JML — Joiner / Mover / Leaver
# ===========================================================================

class JmlEventType(enum.Enum):
    JOINER = "joiner"
    MOVER = "mover"
    LEAVER = "leaver"
    CONTRACTOR_START = "contractor_start"
    CONTRACTOR_END = "contractor_end"


class JmlEventStatus(enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    MANUAL_REVIEW = "manual_review"


class JmlPolicy(Base, TimestampMixin):
    """
    JML lifecycle policy definition.

    Specifies which birthright roles and automated actions should be applied
    when an HR event of a given type fires for employees matching the
    org_unit / position_criteria filter.
    """
    __tablename__ = 'jml_policies'

    id = Column(String(36), primary_key=True, default=_uuid)

    # Multi-tenant
    tenant_id = Column(String(100), nullable=False, index=True)

    # Identity
    policy_name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # Scope
    event_type = Column(SQLEnum(JmlEventType), nullable=False, index=True)
    org_unit = Column(String(255), nullable=True)
    position_criteria = Column(JSON, nullable=True)   # {field: value, ...} filter bag

    # Provisioning spec
    birthright_roles = Column(JSON, nullable=True)    # list of role IDs / names
    actions = Column(JSON, nullable=True)             # [{type, target, params}]

    # Status
    is_active = Column(Boolean, nullable=False, default=True)
    created_by = Column(String(100), nullable=True)

    # Template Library traceability (Phase 1)
    source_template_item_id = Column(String(36), nullable=True, index=True)
    template_version = Column(String(20), nullable=True)
    is_customized = Column(Boolean, nullable=False, default=False)

    def __repr__(self):
        return (
            f"<JmlPolicy(id='{self.id}', policy_name='{self.policy_name}', "
            f"event_type='{self.event_type}')>"
        )

    def to_dict(self):
        return {
            'id': self.id,
            'tenant_id': self.tenant_id,
            'policy_name': self.policy_name,
            'description': self.description,
            'event_type': self.event_type.value if self.event_type else None,
            'org_unit': self.org_unit,
            'position_criteria': self.position_criteria,
            'birthright_roles': self.birthright_roles,
            'actions': self.actions,
            'is_active': self.is_active,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class JmlEvent(Base, TimestampMixin):
    """
    Individual JML provisioning / de-provisioning event.

    Created whenever an HR system emits a lifecycle signal.  The matched
    policy drives automated role assignments / revocations; unmatched events
    can be flagged for manual review.
    """
    __tablename__ = 'jml_events'

    id = Column(String(36), primary_key=True, default=_uuid)

    # Multi-tenant
    tenant_id = Column(String(100), nullable=False, index=True)

    # Event classification
    event_type = Column(SQLEnum(JmlEventType), nullable=False, index=True)

    # Subject
    employee_id = Column(String(100), nullable=False, index=True)
    employee_name = Column(String(255), nullable=True)

    # Position change
    old_position = Column(String(255), nullable=True)
    new_position = Column(String(255), nullable=True)
    old_org_unit = Column(String(255), nullable=True)
    new_org_unit = Column(String(255), nullable=True)

    # Timing
    effective_date = Column(DateTime, nullable=True)

    # Source
    hr_system = Column(String(100), nullable=True)
    raw_payload = Column(JSON, nullable=True)

    # Processing
    status = Column(SQLEnum(JmlEventStatus), nullable=False, default=JmlEventStatus.PENDING, index=True)
    matched_policy_id = Column(String(36), nullable=True, index=True)
    actions_taken = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    processed_at = Column(DateTime, nullable=True)

    def __repr__(self):
        return (
            f"<JmlEvent(id='{self.id}', employee_id='{self.employee_id}', "
            f"event_type='{self.event_type}', status='{self.status}')>"
        )

    def to_dict(self):
        return {
            'id': self.id,
            'tenant_id': self.tenant_id,
            'event_type': self.event_type.value if self.event_type else None,
            'employee_id': self.employee_id,
            'employee_name': self.employee_name,
            'old_position': self.old_position,
            'new_position': self.new_position,
            'old_org_unit': self.old_org_unit,
            'new_org_unit': self.new_org_unit,
            'effective_date': self.effective_date.isoformat() if self.effective_date else None,
            'hr_system': self.hr_system,
            'raw_payload': self.raw_payload,
            'status': self.status.value if self.status else None,
            'matched_policy_id': self.matched_policy_id,
            'actions_taken': self.actions_taken,
            'error_message': self.error_message,
            'processed_at': self.processed_at.isoformat() if self.processed_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


# ===========================================================================
# TPRM — Third-Party Risk Management
# ===========================================================================

class VendorStatus(enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING_REVIEW = "pending_review"
    BLACKLISTED = "blacklisted"


class VendorAssessmentStatus(enum.Enum):
    DRAFT = "draft"
    SENT = "sent"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    OVERDUE = "overdue"


class VendorRiskRating(enum.Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class VendorIssueSeverity(enum.Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class VendorIssueStatus(enum.Enum):
    OPEN = "open"
    IN_REMEDIATION = "in_remediation"
    CLOSED = "closed"
    ACCEPTED = "accepted"


class VendorContractStatus(enum.Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    TERMINATED = "terminated"
    DRAFT = "draft"


class Vendor(Base, TimestampMixin):
    """
    Vendor registry entry with risk tiering and assessment scheduling.
    """
    __tablename__ = 'vendors'

    id = Column(String(36), primary_key=True, default=_uuid)

    # Multi-tenant
    tenant_id = Column(String(100), nullable=False, index=True)

    # Identity
    vendor_name = Column(String(255), nullable=False)
    vendor_code = Column(String(100), nullable=True, index=True)

    # Risk classification
    tier = Column(Integer, nullable=True)          # 1 = critical, 2 = important, 3 = standard
    status = Column(SQLEnum(VendorStatus), nullable=False, default=VendorStatus.ACTIVE, index=True)

    # Contact
    primary_contact = Column(String(255), nullable=True)
    contact_email = Column(String(255), nullable=True)
    country = Column(String(100), nullable=True)

    # Services
    services_provided = Column(JSON, nullable=True)   # list of service descriptions

    # Risk scoring
    risk_score = Column(Float, nullable=True)
    last_assessment_date = Column(DateTime, nullable=True)
    next_assessment_date = Column(DateTime, nullable=True)

    # Contract lifecycle
    contract_expiry = Column(DateTime, nullable=True)

    def __repr__(self):
        return (
            f"<Vendor(id='{self.id}', vendor_name='{self.vendor_name}', "
            f"tier={self.tier}, status='{self.status}')>"
        )

    def to_dict(self):
        return {
            'id': self.id,
            'tenant_id': self.tenant_id,
            'vendor_name': self.vendor_name,
            'vendor_code': self.vendor_code,
            'tier': self.tier,
            'status': self.status.value if self.status else None,
            'primary_contact': self.primary_contact,
            'contact_email': self.contact_email,
            'country': self.country,
            'services_provided': self.services_provided,
            'risk_score': self.risk_score,
            'last_assessment_date': self.last_assessment_date.isoformat() if self.last_assessment_date else None,
            'next_assessment_date': self.next_assessment_date.isoformat() if self.next_assessment_date else None,
            'contract_expiry': self.contract_expiry.isoformat() if self.contract_expiry else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class VendorAssessment(Base, TimestampMixin):
    """
    Questionnaire-based vendor risk assessment.
    """
    __tablename__ = 'vendor_assessments'

    id = Column(String(36), primary_key=True, default=_uuid)

    # Multi-tenant
    tenant_id = Column(String(100), nullable=False, index=True)

    # Parent
    vendor_id = Column(String(36), nullable=False, index=True)

    # Identity
    assessment_name = Column(String(255), nullable=False)
    questionnaire_id = Column(String(36), nullable=True, index=True)

    # Workflow
    status = Column(SQLEnum(VendorAssessmentStatus), nullable=False, default=VendorAssessmentStatus.DRAFT, index=True)
    sent_date = Column(DateTime, nullable=True)
    due_date = Column(DateTime, nullable=True)
    completed_date = Column(DateTime, nullable=True)

    # Results
    overall_score = Column(Float, nullable=True)
    risk_rating = Column(SQLEnum(VendorRiskRating), nullable=True)
    responses = Column(JSON, nullable=True)   # {question_id: answer}

    # Assessor
    assessor = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)

    def __repr__(self):
        return (
            f"<VendorAssessment(id='{self.id}', vendor_id='{self.vendor_id}', "
            f"status='{self.status}')>"
        )

    def to_dict(self):
        return {
            'id': self.id,
            'tenant_id': self.tenant_id,
            'vendor_id': self.vendor_id,
            'assessment_name': self.assessment_name,
            'questionnaire_id': self.questionnaire_id,
            'status': self.status.value if self.status else None,
            'sent_date': self.sent_date.isoformat() if self.sent_date else None,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'completed_date': self.completed_date.isoformat() if self.completed_date else None,
            'overall_score': self.overall_score,
            'risk_rating': self.risk_rating.value if self.risk_rating else None,
            'responses': self.responses,
            'assessor': self.assessor,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class VendorIssue(Base, TimestampMixin):
    """
    Issue or finding raised against a vendor.
    """
    __tablename__ = 'vendor_issues'

    id = Column(String(36), primary_key=True, default=_uuid)

    # Multi-tenant
    tenant_id = Column(String(100), nullable=False, index=True)

    # Parent
    vendor_id = Column(String(36), nullable=False, index=True)

    # Description
    issue_title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)

    # Classification
    severity = Column(SQLEnum(VendorIssueSeverity), nullable=False, index=True)
    status = Column(SQLEnum(VendorIssueStatus), nullable=False, default=VendorIssueStatus.OPEN, index=True)

    # Remediation
    due_date = Column(DateTime, nullable=True)
    owner = Column(String(100), nullable=True)
    resolution_notes = Column(Text, nullable=True)
    closed_date = Column(DateTime, nullable=True)

    def __repr__(self):
        return (
            f"<VendorIssue(id='{self.id}', vendor_id='{self.vendor_id}', "
            f"severity='{self.severity}', status='{self.status}')>"
        )

    def to_dict(self):
        return {
            'id': self.id,
            'tenant_id': self.tenant_id,
            'vendor_id': self.vendor_id,
            'issue_title': self.issue_title,
            'description': self.description,
            'severity': self.severity.value if self.severity else None,
            'status': self.status.value if self.status else None,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'owner': self.owner,
            'resolution_notes': self.resolution_notes,
            'closed_date': self.closed_date.isoformat() if self.closed_date else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class VendorContract(Base, TimestampMixin):
    """
    Vendor contract lifecycle record.
    """
    __tablename__ = 'vendor_contracts'

    id = Column(String(36), primary_key=True, default=_uuid)

    # Multi-tenant
    tenant_id = Column(String(100), nullable=False, index=True)

    # Parent
    vendor_id = Column(String(36), nullable=False, index=True)

    # Identity
    contract_name = Column(String(255), nullable=False)
    contract_type = Column(String(100), nullable=True)

    # Dates
    start_date = Column(DateTime, nullable=True)
    end_date = Column(DateTime, nullable=True)

    # Financials
    value = Column(Float, nullable=True)
    currency = Column(String(3), nullable=False, default='USD')

    # Renewal
    auto_renew = Column(Boolean, nullable=False, default=False)
    notice_period_days = Column(Integer, nullable=True)

    # SLAs
    key_slas = Column(JSON, nullable=True)   # [{metric, target, measure_frequency}]

    # Status
    status = Column(SQLEnum(VendorContractStatus), nullable=False, default=VendorContractStatus.DRAFT, index=True)

    def __repr__(self):
        return (
            f"<VendorContract(id='{self.id}', vendor_id='{self.vendor_id}', "
            f"contract_name='{self.contract_name}', status='{self.status}')>"
        )

    def to_dict(self):
        return {
            'id': self.id,
            'tenant_id': self.tenant_id,
            'vendor_id': self.vendor_id,
            'contract_name': self.contract_name,
            'contract_type': self.contract_type,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'value': self.value,
            'currency': self.currency,
            'auto_renew': self.auto_renew,
            'notice_period_days': self.notice_period_days,
            'key_slas': self.key_slas,
            'status': self.status.value if self.status else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


# ===========================================================================
# Fraud Detection
# ===========================================================================

class FraudRuleType(enum.Enum):
    VELOCITY = "velocity"
    THRESHOLD = "threshold"
    PATTERN = "pattern"
    ANOMALY = "anomaly"


class FraudAlertStatus(enum.Enum):
    OPEN = "open"
    INVESTIGATING = "investigating"
    CONFIRMED_FRAUD = "confirmed_fraud"
    FALSE_POSITIVE = "false_positive"
    DISMISSED = "dismissed"


class FraudCaseSeverity(enum.Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class FraudCaseStatus(enum.Enum):
    OPEN = "open"
    INVESTIGATING = "investigating"
    CLOSED = "closed"
    ESCALATED = "escalated"


class FraudRule(Base, TimestampMixin):
    """
    Fraud detection rule definition.
    """
    __tablename__ = 'fraud_rules'

    id = Column(String(36), primary_key=True, default=_uuid)

    # Multi-tenant
    tenant_id = Column(String(100), nullable=False, index=True)

    # Identity
    rule_name = Column(String(255), nullable=False)
    rule_type = Column(SQLEnum(FraudRuleType), nullable=False, index=True)
    description = Column(Text, nullable=True)

    # Logic
    conditions = Column(JSON, nullable=False)   # rule condition tree

    # Scoring
    risk_score = Column(Float, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    alert_on_breach = Column(Boolean, nullable=False, default=True)

    # Authorship
    created_by = Column(String(100), nullable=True)

    # Execution stats
    last_triggered_at = Column(DateTime, nullable=True)
    trigger_count = Column(Integer, nullable=False, default=0)

    # Template Library traceability (Phase 1)
    source_template_item_id = Column(String(36), nullable=True, index=True)
    template_version = Column(String(20), nullable=True)
    is_customized = Column(Boolean, nullable=False, default=False)

    def __repr__(self):
        return (
            f"<FraudRule(id='{self.id}', rule_name='{self.rule_name}', "
            f"rule_type='{self.rule_type}')>"
        )

    def to_dict(self):
        return {
            'id': self.id,
            'tenant_id': self.tenant_id,
            'rule_name': self.rule_name,
            'rule_type': self.rule_type.value if self.rule_type else None,
            'description': self.description,
            'conditions': self.conditions,
            'risk_score': self.risk_score,
            'is_active': self.is_active,
            'alert_on_breach': self.alert_on_breach,
            'created_by': self.created_by,
            'last_triggered_at': self.last_triggered_at.isoformat() if self.last_triggered_at else None,
            'trigger_count': self.trigger_count,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class FraudAlert(Base, TimestampMixin):
    """
    Alert triggered by a fraud detection rule.
    """
    __tablename__ = 'fraud_alerts'

    id = Column(String(36), primary_key=True, default=_uuid)

    # Multi-tenant
    tenant_id = Column(String(100), nullable=False, index=True)

    # Parent rule
    rule_id = Column(String(36), nullable=False, index=True)

    # Subject
    user_id = Column(String(100), nullable=True, index=True)
    system_id = Column(String(100), nullable=True)

    # Alert detail
    alert_type = Column(String(100), nullable=True)
    description = Column(Text, nullable=True)
    risk_score = Column(Float, nullable=True)

    # Workflow
    status = Column(SQLEnum(FraudAlertStatus), nullable=False, default=FraudAlertStatus.OPEN, index=True)
    triggered_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    reviewed_by = Column(String(100), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)

    # Case linkage
    case_id = Column(String(36), nullable=True, index=True)

    # Evidence
    evidence = Column(JSON, nullable=True)

    def __repr__(self):
        return (
            f"<FraudAlert(id='{self.id}', rule_id='{self.rule_id}', "
            f"status='{self.status}')>"
        )

    def to_dict(self):
        return {
            'id': self.id,
            'tenant_id': self.tenant_id,
            'rule_id': self.rule_id,
            'user_id': self.user_id,
            'system_id': self.system_id,
            'alert_type': self.alert_type,
            'description': self.description,
            'risk_score': self.risk_score,
            'status': self.status.value if self.status else None,
            'triggered_at': self.triggered_at.isoformat() if self.triggered_at else None,
            'reviewed_by': self.reviewed_by,
            'reviewed_at': self.reviewed_at.isoformat() if self.reviewed_at else None,
            'case_id': self.case_id,
            'evidence': self.evidence,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class FraudCase(Base, TimestampMixin):
    """
    Fraud investigation case — aggregates multiple alerts into a single
    investigation workflow with outcome tracking.
    """
    __tablename__ = 'fraud_cases'

    id = Column(String(36), primary_key=True, default=_uuid)

    # Multi-tenant
    tenant_id = Column(String(100), nullable=False, index=True)

    # Identity
    case_reference = Column(String(100), nullable=False, index=True)   # human-readable ref
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)

    # Classification
    severity = Column(SQLEnum(FraudCaseSeverity), nullable=False, index=True)
    status = Column(SQLEnum(FraudCaseStatus), nullable=False, default=FraudCaseStatus.OPEN, index=True)

    # Ownership
    assigned_to = Column(String(100), nullable=True)

    # Linked alerts / findings
    linked_alert_ids = Column(JSON, nullable=True)   # list of FraudAlert IDs
    linked_finding_id = Column(String(100), nullable=True)

    # Timeline
    opened_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    closed_at = Column(DateTime, nullable=True)

    # Outcome
    outcome = Column(Text, nullable=True)
    loss_amount = Column(Float, nullable=True)

    def __repr__(self):
        return (
            f"<FraudCase(id='{self.id}', case_reference='{self.case_reference}', "
            f"severity='{self.severity}', status='{self.status}')>"
        )

    def to_dict(self):
        return {
            'id': self.id,
            'tenant_id': self.tenant_id,
            'case_reference': self.case_reference,
            'title': self.title,
            'description': self.description,
            'severity': self.severity.value if self.severity else None,
            'status': self.status.value if self.status else None,
            'assigned_to': self.assigned_to,
            'linked_alert_ids': self.linked_alert_ids,
            'linked_finding_id': self.linked_finding_id,
            'opened_at': self.opened_at.isoformat() if self.opened_at else None,
            'closed_at': self.closed_at.isoformat() if self.closed_at else None,
            'outcome': self.outcome,
            'loss_amount': self.loss_amount,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


# ===========================================================================
# BCM — Business Continuity Management
# ===========================================================================

class BcmCriticality(enum.Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class BcmPlanType(enum.Enum):
    BCP = "bcp"
    DRP = "drp"
    CRISIS = "crisis"
    COMMUNICATION = "communication"


class BcmPlanStatus(enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    RETIRED = "retired"


class BcmExerciseType(enum.Enum):
    TABLETOP = "tabletop"
    WALKTHROUGH = "walkthrough"
    SIMULATION = "simulation"
    FULL_TEST = "full_test"


class BcmExerciseOutcome(enum.Enum):
    PASS = "pass"
    FAIL = "fail"
    PARTIAL = "partial"


class BcmActivationSeverity(enum.Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class BcmActivationStatus(enum.Enum):
    ACTIVE = "active"
    RESOLVED = "resolved"
    CLOSED = "closed"


class BiaRecord(Base, TimestampMixin):
    """
    Business Impact Analysis record for a business process.
    """
    __tablename__ = 'bia_records'

    id = Column(String(36), primary_key=True, default=_uuid)

    # Multi-tenant
    tenant_id = Column(String(100), nullable=False, index=True)

    # Process identity
    process_name = Column(String(500), nullable=False)
    process_owner = Column(String(255), nullable=True)

    # Impact classification
    criticality = Column(SQLEnum(BcmCriticality), nullable=False, index=True)

    # Recovery objectives (hours)
    rto_hours = Column(Float, nullable=True)    # Recovery Time Objective
    rpo_hours = Column(Float, nullable=True)    # Recovery Point Objective
    mtpd_hours = Column(Float, nullable=True)   # Maximum Tolerable Period of Disruption

    # Context
    dependencies = Column(JSON, nullable=True)      # [{type, name, description}]
    recovery_strategy = Column(Text, nullable=True)
    impact_description = Column(Text, nullable=True)
    last_reviewed = Column(DateTime, nullable=True)

    def __repr__(self):
        return (
            f"<BiaRecord(id='{self.id}', process_name='{self.process_name}', "
            f"criticality='{self.criticality}')>"
        )

    def to_dict(self):
        return {
            'id': self.id,
            'tenant_id': self.tenant_id,
            'process_name': self.process_name,
            'process_owner': self.process_owner,
            'criticality': self.criticality.value if self.criticality else None,
            'rto_hours': self.rto_hours,
            'rpo_hours': self.rpo_hours,
            'mtpd_hours': self.mtpd_hours,
            'dependencies': self.dependencies,
            'recovery_strategy': self.recovery_strategy,
            'impact_description': self.impact_description,
            'last_reviewed': self.last_reviewed.isoformat() if self.last_reviewed else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class BcmPlan(Base, TimestampMixin):
    """
    Business Continuity / Disaster Recovery / Crisis plan.
    """
    __tablename__ = 'bcm_plans'

    id = Column(String(36), primary_key=True, default=_uuid)

    # Multi-tenant
    tenant_id = Column(String(100), nullable=False, index=True)

    # Identity
    plan_name = Column(String(255), nullable=False)
    plan_type = Column(SQLEnum(BcmPlanType), nullable=False, index=True)
    scope = Column(Text, nullable=True)

    # Ownership
    owner = Column(String(100), nullable=True)

    # Versioning
    version = Column(String(50), nullable=True, default='1.0')
    status = Column(SQLEnum(BcmPlanStatus), nullable=False, default=BcmPlanStatus.DRAFT, index=True)

    # Testing schedule
    last_tested = Column(DateTime, nullable=True)
    next_test_date = Column(DateTime, nullable=True)

    # Plan content
    call_tree = Column(JSON, nullable=True)         # [{name, role, phone, email, order}]
    recovery_steps = Column(JSON, nullable=True)    # [{step, description, owner, duration_mins}]

    # Approval
    approved_by = Column(String(100), nullable=True)
    approved_date = Column(DateTime, nullable=True)

    def __repr__(self):
        return (
            f"<BcmPlan(id='{self.id}', plan_name='{self.plan_name}', "
            f"plan_type='{self.plan_type}', status='{self.status}')>"
        )

    def to_dict(self):
        return {
            'id': self.id,
            'tenant_id': self.tenant_id,
            'plan_name': self.plan_name,
            'plan_type': self.plan_type.value if self.plan_type else None,
            'scope': self.scope,
            'owner': self.owner,
            'version': self.version,
            'status': self.status.value if self.status else None,
            'last_tested': self.last_tested.isoformat() if self.last_tested else None,
            'next_test_date': self.next_test_date.isoformat() if self.next_test_date else None,
            'call_tree': self.call_tree,
            'recovery_steps': self.recovery_steps,
            'approved_by': self.approved_by,
            'approved_date': self.approved_date.isoformat() if self.approved_date else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class BcmTestExercise(Base, TimestampMixin):
    """
    BCM plan test / exercise record.
    """
    __tablename__ = 'bcm_test_exercises'

    id = Column(String(36), primary_key=True, default=_uuid)

    # Multi-tenant
    tenant_id = Column(String(100), nullable=False, index=True)

    # Parent plan
    plan_id = Column(String(36), nullable=False, index=True)

    # Exercise identity
    exercise_name = Column(String(255), nullable=False)
    exercise_type = Column(SQLEnum(BcmExerciseType), nullable=False)

    # Dates
    scheduled_date = Column(DateTime, nullable=True)
    completed_date = Column(DateTime, nullable=True)

    # Participants
    facilitator = Column(String(100), nullable=True)
    participants = Column(JSON, nullable=True)   # [{name, role, org_unit}]

    # Results
    outcome = Column(SQLEnum(BcmExerciseOutcome), nullable=True)
    findings = Column(Text, nullable=True)
    lessons_learned = Column(Text, nullable=True)

    def __repr__(self):
        return (
            f"<BcmTestExercise(id='{self.id}', plan_id='{self.plan_id}', "
            f"exercise_name='{self.exercise_name}', outcome='{self.outcome}')>"
        )

    def to_dict(self):
        return {
            'id': self.id,
            'tenant_id': self.tenant_id,
            'plan_id': self.plan_id,
            'exercise_name': self.exercise_name,
            'exercise_type': self.exercise_type.value if self.exercise_type else None,
            'scheduled_date': self.scheduled_date.isoformat() if self.scheduled_date else None,
            'completed_date': self.completed_date.isoformat() if self.completed_date else None,
            'facilitator': self.facilitator,
            'participants': self.participants,
            'outcome': self.outcome.value if self.outcome else None,
            'findings': self.findings,
            'lessons_learned': self.lessons_learned,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class IncidentActivation(Base, TimestampMixin):
    """
    BCM plan activation record for a real business disruption event.
    """
    __tablename__ = 'incident_activations'

    id = Column(String(36), primary_key=True, default=_uuid)

    # Multi-tenant
    tenant_id = Column(String(100), nullable=False, index=True)

    # Identity
    activation_name = Column(String(255), nullable=False)

    # Activated plan
    plan_id = Column(String(36), nullable=False, index=True)

    # Activation metadata
    activated_by = Column(String(100), nullable=False)
    activation_reason = Column(Text, nullable=True)
    severity = Column(SQLEnum(BcmActivationSeverity), nullable=False, index=True)
    status = Column(SQLEnum(BcmActivationStatus), nullable=False, default=BcmActivationStatus.ACTIVE, index=True)

    # Timeline
    activated_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)

    # Impact tracking
    impacted_processes = Column(JSON, nullable=True)    # list of process names / IDs
    timeline_events = Column(JSON, nullable=True)       # [{timestamp, event_type, description, actor}]
    communications_log = Column(JSON, nullable=True)    # [{sent_at, channel, recipients, message}]

    def __repr__(self):
        return (
            f"<IncidentActivation(id='{self.id}', plan_id='{self.plan_id}', "
            f"severity='{self.severity}', status='{self.status}')>"
        )

    def to_dict(self):
        return {
            'id': self.id,
            'tenant_id': self.tenant_id,
            'activation_name': self.activation_name,
            'plan_id': self.plan_id,
            'activated_by': self.activated_by,
            'activation_reason': self.activation_reason,
            'severity': self.severity.value if self.severity else None,
            'status': self.status.value if self.status else None,
            'activated_at': self.activated_at.isoformat() if self.activated_at else None,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None,
            'impacted_processes': self.impacted_processes,
            'timeline_events': self.timeline_events,
            'communications_log': self.communications_log,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


# ===========================================================================
# Whistleblower
# ===========================================================================

class WhistleblowerCategory(enum.Enum):
    FRAUD = "fraud"
    CORRUPTION = "corruption"
    SAFETY = "safety"
    HARASSMENT = "harassment"
    OTHER = "other"


class WhistleblowerStatus(enum.Enum):
    OPEN = "open"
    TRIAGING = "triaging"
    INVESTIGATING = "investigating"
    CLOSED = "closed"
    ESCALATED = "escalated"


class WhistleblowerPriority(enum.Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class WhistleblowerSender(enum.Enum):
    SUBMITTER = "submitter"
    INVESTIGATOR = "investigator"
    SYSTEM = "system"


class WhistleblowerCase(Base, TimestampMixin):
    """
    Whistleblower disclosure — supports fully anonymous submissions via
    a unique case_reference token for follow-up without revealing identity.
    """
    __tablename__ = 'whistleblower_cases'

    id = Column(String(36), primary_key=True, default=_uuid)

    # Multi-tenant
    tenant_id = Column(String(100), nullable=False, index=True)

    # Anonymous follow-up token (unique per case)
    case_reference = Column(String(100), nullable=False, unique=True, index=True)

    # Classification
    category = Column(SQLEnum(WhistleblowerCategory), nullable=False, index=True)
    submission_channel = Column(String(50), nullable=True)   # web / email / phone

    # Content
    summary = Column(String(1000), nullable=False)
    details = Column(Text, nullable=True)

    # Submission
    submitted_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    is_anonymous = Column(Boolean, nullable=False, default=True)
    submitter_email = Column(String(255), nullable=True)

    # Workflow
    status = Column(SQLEnum(WhistleblowerStatus), nullable=False, default=WhistleblowerStatus.OPEN, index=True)
    assigned_to = Column(String(100), nullable=True)
    priority = Column(SQLEnum(WhistleblowerPriority), nullable=True)

    # Resolution
    resolution = Column(Text, nullable=True)
    closed_at = Column(DateTime, nullable=True)

    def __repr__(self):
        return (
            f"<WhistleblowerCase(id='{self.id}', "
            f"case_reference='{self.case_reference}', status='{self.status}')>"
        )

    def to_dict(self):
        return {
            'id': self.id,
            'tenant_id': self.tenant_id,
            'case_reference': self.case_reference,
            'category': self.category.value if self.category else None,
            'submission_channel': self.submission_channel,
            'summary': self.summary,
            'details': self.details,
            'submitted_at': self.submitted_at.isoformat() if self.submitted_at else None,
            'is_anonymous': self.is_anonymous,
            'submitter_email': self.submitter_email,
            'status': self.status.value if self.status else None,
            'assigned_to': self.assigned_to,
            'priority': self.priority.value if self.priority else None,
            'resolution': self.resolution,
            'closed_at': self.closed_at.isoformat() if self.closed_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class WhistleblowerMessage(Base, TimestampMixin):
    """
    Threaded message on a whistleblower case.

    Allows the submitter (using only their case_reference token) and the
    investigator to exchange messages without exposing identity.
    """
    __tablename__ = 'whistleblower_messages'

    id = Column(String(36), primary_key=True, default=_uuid)

    # Multi-tenant
    tenant_id = Column(String(100), nullable=False, index=True)

    # Parent case
    case_id = Column(String(36), nullable=False, index=True)

    # Message
    sender = Column(SQLEnum(WhistleblowerSender), nullable=False)
    message_text = Column(Text, nullable=False)
    sent_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    is_read = Column(Boolean, nullable=False, default=False)

    def __repr__(self):
        return (
            f"<WhistleblowerMessage(id='{self.id}', case_id='{self.case_id}', "
            f"sender='{self.sender}')>"
        )

    def to_dict(self):
        return {
            'id': self.id,
            'tenant_id': self.tenant_id,
            'case_id': self.case_id,
            'sender': self.sender.value if self.sender else None,
            'message_text': self.message_text,
            'sent_at': self.sent_at.isoformat() if self.sent_at else None,
            'is_read': self.is_read,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


# ===========================================================================
# Survey (standalone — broader than process_control questionnaires)
# ===========================================================================

class SurveyType(enum.Enum):
    RISK_ASSESSMENT = "risk_assessment"
    POLICY_ATTESTATION = "policy_attestation"
    VENDOR_QUESTIONNAIRE = "vendor_questionnaire"
    GENERAL = "general"


class SurveyStatus(enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    CLOSED = "closed"


class SurveyDistributionStatus(enum.Enum):
    PENDING = "pending"
    SENT = "sent"
    COMPLETED = "completed"
    OVERDUE = "overdue"


class StandaloneSurvey(Base, TimestampMixin):
    """
    Standalone survey definition — independent of the PC questionnaire library,
    supporting risk assessments, policy attestations, vendor questionnaires,
    and general-purpose surveys.
    """
    __tablename__ = 'standalone_surveys'

    id = Column(String(36), primary_key=True, default=_uuid)

    # Multi-tenant
    tenant_id = Column(String(100), nullable=False, index=True)

    # Identity
    survey_name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    survey_type = Column(SQLEnum(SurveyType), nullable=False, index=True)

    # Questions — [{id, text, type, required, options, ...}]
    questions = Column(JSON, nullable=True)

    # Lifecycle
    status = Column(SQLEnum(SurveyStatus), nullable=False, default=SurveyStatus.DRAFT, index=True)
    created_by = Column(String(100), nullable=True)
    created_at_override = Column('survey_created_at', DateTime, nullable=True)   # alias to avoid clash with TimestampMixin
    due_date = Column(DateTime, nullable=True)
    allow_anonymous = Column(Boolean, nullable=False, default=False)

    # Template Library traceability (Phase 1)
    source_template_item_id = Column(String(36), nullable=True, index=True)
    template_version = Column(String(20), nullable=True)
    is_customized = Column(Boolean, nullable=False, default=False)

    def __repr__(self):
        return (
            f"<StandaloneSurvey(id='{self.id}', survey_name='{self.survey_name}', "
            f"survey_type='{self.survey_type}', status='{self.status}')>"
        )

    def to_dict(self):
        return {
            'id': self.id,
            'tenant_id': self.tenant_id,
            'survey_name': self.survey_name,
            'description': self.description,
            'survey_type': self.survey_type.value if self.survey_type else None,
            'questions': self.questions,
            'status': self.status.value if self.status else None,
            'created_by': self.created_by,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'allow_anonymous': self.allow_anonymous,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class SurveyDistribution(Base, TimestampMixin):
    """
    Per-recipient survey distribution record — tracks send / reminder / completion state.
    """
    __tablename__ = 'survey_distributions'

    id = Column(String(36), primary_key=True, default=_uuid)

    # Multi-tenant
    tenant_id = Column(String(100), nullable=False, index=True)

    # Parent survey
    survey_id = Column(String(36), nullable=False, index=True)

    # Recipient
    recipient_id = Column(String(100), nullable=True, index=True)
    recipient_email = Column(String(255), nullable=True)
    recipient_name = Column(String(255), nullable=True)

    # Lifecycle
    sent_at = Column(DateTime, nullable=True)
    due_date = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    status = Column(SQLEnum(SurveyDistributionStatus), nullable=False, default=SurveyDistributionStatus.PENDING, index=True)

    # Reminders
    reminder_count = Column(Integer, nullable=False, default=0)
    last_reminder_at = Column(DateTime, nullable=True)

    def __repr__(self):
        return (
            f"<SurveyDistribution(id='{self.id}', survey_id='{self.survey_id}', "
            f"recipient_email='{self.recipient_email}', status='{self.status}')>"
        )

    def to_dict(self):
        return {
            'id': self.id,
            'tenant_id': self.tenant_id,
            'survey_id': self.survey_id,
            'recipient_id': self.recipient_id,
            'recipient_email': self.recipient_email,
            'recipient_name': self.recipient_name,
            'sent_at': self.sent_at.isoformat() if self.sent_at else None,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'status': self.status.value if self.status else None,
            'reminder_count': self.reminder_count,
            'last_reminder_at': self.last_reminder_at.isoformat() if self.last_reminder_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class SurveyAnswer(Base, TimestampMixin):
    """
    Submitted responses to a standalone survey distribution.
    """
    __tablename__ = 'survey_answers'

    id = Column(String(36), primary_key=True, default=_uuid)

    # Multi-tenant
    tenant_id = Column(String(100), nullable=False, index=True)

    # Parent distribution and survey
    distribution_id = Column(String(36), nullable=False, index=True)
    survey_id = Column(String(36), nullable=False, index=True)

    # Respondent
    respondent_id = Column(String(100), nullable=True, index=True)
    respondent_email = Column(String(255), nullable=True)

    # Answers — {question_id: answer_value}
    responses = Column(JSON, nullable=True)

    # Computed score
    score = Column(Float, nullable=True)

    # Submission
    submitted_at = Column(DateTime, nullable=True)
    is_anonymous = Column(Boolean, nullable=False, default=False)

    def __repr__(self):
        return (
            f"<SurveyAnswer(id='{self.id}', survey_id='{self.survey_id}', "
            f"respondent_email='{self.respondent_email}')>"
        )

    def to_dict(self):
        return {
            'id': self.id,
            'tenant_id': self.tenant_id,
            'distribution_id': self.distribution_id,
            'survey_id': self.survey_id,
            'respondent_id': self.respondent_id,
            'respondent_email': self.respondent_email,
            'responses': self.responses,
            'score': self.score,
            'submitted_at': self.submitted_at.isoformat() if self.submitted_at else None,
            'is_anonymous': self.is_anonymous,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
