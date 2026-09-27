"""
Database Models - Process Control Module

Full Process Control module covering PC-01 through PC-32:
  - ProcessControl          : central control library (PC-01)
  - ControlTest             : operating effectiveness tests (PC-11)
  - ControlDeficiency       : issues surfaced from failed tests (PC-13)
  - ControlSelfAssessment   : owner sign-off campaigns (PC-12)
  - CCMRule                 : continuous control monitoring rules (PC-20, PC-22)
  - CCMExecution            : monitoring execution results (PC-22)
  - GRCEvidence             : evidence repository (PC-15)
  - SignOffCertification    : SOX-style cascading sign-offs (PC-14)
  - ControlObjective        : formal control objective entity (PC-SAP-GAP-05)
  - SubProcess              : formal subprocess hierarchy (PC-SAP-GAP-06)
  - PolicyDocument          : full policy lifecycle (PC-SAP-GAP-07)
  - QuestionLibrary         : reusable assessment questions (PC-SAP-GAP-08)
  - Questionnaire           : assembled questionnaire from library (PC-SAP-GAP-09)
  - QuestionnaireResponse   : filled questionnaire (PC-SAP-GAP-10)
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

class ControlType(enum.Enum):
    """Nature of the control's purpose"""
    PREVENTIVE = "preventive"
    DETECTIVE = "detective"
    CORRECTIVE = "corrective"


class ControlNature(enum.Enum):
    """How the control operates"""
    MANUAL = "manual"
    AUTOMATED = "automated"
    IT_DEPENDENT = "it_dependent"


class ControlFrequency(enum.Enum):
    """Execution cadence of the control"""
    CONTINUOUS = "continuous"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUAL = "annual"
    ADHOC = "adhoc"


class ControlStatus(enum.Enum):
    """Lifecycle status of a control definition"""
    DRAFT = "draft"
    ACTIVE = "active"
    UNDER_REVIEW = "under_review"
    RETIRED = "retired"


class TestType(enum.Enum):
    """Type of control test performed"""
    DESIGN = "design"
    OPERATING_EFFECTIVENESS = "operating_effectiveness"
    WALKTHROUGH = "walkthrough"


class TestResult(enum.Enum):
    """Overall result of a control test"""
    EFFECTIVE = "effective"
    INEFFECTIVE = "ineffective"
    PARTIALLY_EFFECTIVE = "partially_effective"
    NOT_TESTED = "not_tested"


class TestStatus(enum.Enum):
    """Workflow status of a control test"""
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    REVIEWED = "reviewed"


class DeficiencySeverity(enum.Enum):
    """Severity classification of a control deficiency"""
    SIGNIFICANT_DEFICIENCY = "significant_deficiency"
    MATERIAL_WEAKNESS = "material_weakness"
    CONTROL_GAP = "control_gap"
    OBSERVATION = "observation"


class DeficiencyStatus(enum.Enum):
    """Lifecycle status of a control deficiency"""
    OPEN = "open"
    IN_REMEDIATION = "in_remediation"
    REMEDIATED = "remediated"
    VERIFIED_CLOSED = "verified_closed"
    ACCEPTED = "accepted"


class CSAStatus(enum.Enum):
    """Status of a control self-assessment"""
    PENDING = "pending"
    COMPLETED = "completed"
    OVERDUE = "overdue"


class CCMRuleType(enum.Enum):
    """Category of a CCM monitoring rule"""
    CONFIG_CHECK = "config_check"
    DATA_PATTERN = "data_pattern"
    THRESHOLD = "threshold"
    SOD_BRIDGE = "sod_bridge"


class CCMResult(enum.Enum):
    """Result of a CCM execution run"""
    PASS = "pass"
    FAIL = "fail"
    ERROR = "error"
    SKIPPED = "skipped"


class EvidenceStatus(enum.Enum):
    """Lifecycle status of an evidence record"""
    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"


class SignOffStatus(enum.Enum):
    """Status of a sign-off certification"""
    PENDING = "pending"
    CERTIFIED = "certified"
    CERTIFIED_WITH_EXCEPTIONS = "certified_with_exceptions"
    REFUSED = "refused"


class ObjectiveStatus(enum.Enum):
    """Lifecycle status of a control objective"""
    ACTIVE = "active"
    UNDER_REVIEW = "under_review"
    RETIRED = "retired"


class PolicyType(enum.Enum):
    """Type / category of a policy document"""
    CORPORATE = "corporate"
    REGULATORY = "regulatory"
    OPERATIONAL = "operational"
    IT = "it"
    COMPLIANCE = "compliance"


class PolicyStatus(enum.Enum):
    """Lifecycle status of a policy document"""
    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    PUBLISHED = "published"
    ARCHIVED = "archived"
    RETIRED = "retired"


class QuestionType(enum.Enum):
    """Type of question in the question library"""
    YES_NO = "yes_no"
    RATING_SCALE = "rating_scale"
    MULTIPLE_CHOICE = "multiple_choice"
    TEXT = "text"
    NUMERIC = "numeric"


class QuestionnaireType(enum.Enum):
    """Type of questionnaire"""
    CONTROL_ASSESSMENT = "control_assessment"
    RISK_ASSESSMENT = "risk_assessment"
    AUDIT_INTERVIEW = "audit_interview"
    COMPLIANCE_SURVEY = "compliance_survey"
    SELF_ASSESSMENT = "self_assessment"


class ResponseStatus(enum.Enum):
    """Status of a questionnaire response"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUBMITTED = "submitted"
    REVIEWED = "reviewed"


# ---------------------------------------------------------------------------
# ProcessControl  (PC-01)
# ---------------------------------------------------------------------------

class ProcessControl(Base, TimestampMixin):
    """
    Central control library entry (PC-01).

    A ProcessControl record defines a single internal control, its execution
    parameters, framework mappings, risk linkages, and full change history.
    Versioning is tracked via the version counter and change_history JSON log.
    """
    __tablename__ = 'process_controls'

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Multi-tenant support
    tenant_id = Column(String(100), nullable=False, index=True, default='tenant_default')

    # Identity
    control_id = Column(String(100), nullable=False, index=True)   # unique within tenant
    name = Column(String(500), nullable=False)
    objective = Column(Text, nullable=True)
    description = Column(Text, nullable=True)

    # Classification
    control_type = Column(SQLEnum(ControlType), nullable=False)
    control_nature = Column(SQLEnum(ControlNature), nullable=False)
    frequency = Column(SQLEnum(ControlFrequency), nullable=False)

    # Organisational scope
    org_unit_id = Column(Integer, ForeignKey('org_units.id'), nullable=True, index=True)
    process_name = Column(String(255), nullable=True)
    subprocess_name = Column(String(255), nullable=True)

    # Ownership
    owner_id = Column(String(100), nullable=True)
    owner_name = Column(String(255), nullable=True)
    owner_email = Column(String(255), nullable=True)

    # Framework mappings — [{"framework_id": "...", "requirement_id": "..."}]
    framework_mappings = Column(JSON, nullable=True)

    # Linked objects (JSON arrays of IDs)
    risk_ids = Column(JSON, nullable=True)           # linked EnterpriseRisk IDs
    regulation_ids = Column(JSON, nullable=True)     # linked regulation / standard IDs

    # Versioning
    version = Column(Integer, nullable=False, default=1)
    effective_date = Column(DateTime, nullable=True)
    review_date = Column(DateTime, nullable=True)
    next_review_date = Column(DateTime, nullable=True)

    # Status
    status = Column(SQLEnum(ControlStatus), nullable=False, default=ControlStatus.DRAFT)

    # Key / material control flag (relevant for SOX scoping)
    key_control = Column(Boolean, default=False, nullable=False)

    is_active = Column(Boolean, default=True, nullable=False)

    # Audit trail for version changes
    change_history = Column(JSON, nullable=True)   # list of {version, changed_by, changed_at, summary}

    # Relationships
    tests = relationship('ControlTest', back_populates='control')
    deficiencies = relationship('ControlDeficiency', back_populates='control')
    self_assessments = relationship('ControlSelfAssessment', back_populates='control')
    ccm_rules = relationship('CCMRule', back_populates='control')

    def __repr__(self):
        return (
            f"<ProcessControl(control_id='{self.control_id}', "
            f"name='{self.name[:50]}', status='{self.status}')>"
        )

    def to_dict(self):
        return {
            'id': self.id,
            'tenant_id': self.tenant_id,
            'control_id': self.control_id,
            'name': self.name,
            'objective': self.objective,
            'description': self.description,
            'control_type': self.control_type.value if self.control_type else None,
            'control_nature': self.control_nature.value if self.control_nature else None,
            'frequency': self.frequency.value if self.frequency else None,
            'org_unit_id': self.org_unit_id,
            'process_name': self.process_name,
            'subprocess_name': self.subprocess_name,
            'owner_id': self.owner_id,
            'owner_name': self.owner_name,
            'owner_email': self.owner_email,
            'framework_mappings': self.framework_mappings,
            'risk_ids': self.risk_ids,
            'regulation_ids': self.regulation_ids,
            'version': self.version,
            'effective_date': self.effective_date.isoformat() if self.effective_date else None,
            'review_date': self.review_date.isoformat() if self.review_date else None,
            'next_review_date': self.next_review_date.isoformat() if self.next_review_date else None,
            'status': self.status.value if self.status else None,
            'key_control': self.key_control,
            'is_active': self.is_active,
            'change_history': self.change_history,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


# ---------------------------------------------------------------------------
# ControlTest  (PC-11)
# ---------------------------------------------------------------------------

class ControlTest(Base, TimestampMixin):
    """
    Operating effectiveness test for a control (PC-11).

    Records the test approach, sampling parameters, step-by-step procedures,
    exceptions found, and reviewer sign-off for a defined testing period.
    """
    __tablename__ = 'control_tests'

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Multi-tenant support
    tenant_id = Column(String(100), nullable=False, index=True, default='tenant_default')

    # Identity
    test_id = Column(String(100), nullable=False, index=True)

    # Parent control
    control_id = Column(Integer, ForeignKey('process_controls.id'), nullable=False, index=True)

    # Test parameters
    test_type = Column(SQLEnum(TestType), nullable=False)
    testing_period_start = Column(DateTime, nullable=True)
    testing_period_end = Column(DateTime, nullable=True)
    sample_size = Column(Integer, nullable=True)
    population_size = Column(Integer, nullable=True)

    # Tester
    tester_id = Column(String(100), nullable=True)
    tester_name = Column(String(255), nullable=True)

    # Procedure — ordered list of {ref, step, description}
    test_steps = Column(JSON, nullable=True)

    # Result
    result = Column(SQLEnum(TestResult), nullable=True)
    exceptions_found = Column(Integer, nullable=False, default=0)
    exception_details = Column(JSON, nullable=True)  # list of exception descriptions
    conclusion = Column(Text, nullable=True)

    # Evidence links
    evidence_ids = Column(JSON, nullable=True)    # list of grc_evidence IDs

    # Review
    reviewed_by = Column(String(100), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)

    # Workflow
    status = Column(SQLEnum(TestStatus), nullable=False, default=TestStatus.PLANNED)

    # Relationships
    control = relationship('ProcessControl', back_populates='tests')
    deficiencies = relationship('ControlDeficiency', back_populates='test')

    def __repr__(self):
        return (
            f"<ControlTest(test_id='{self.test_id}', "
            f"control_id={self.control_id}, result='{self.result}')>"
        )

    def to_dict(self):
        return {
            'id': self.id,
            'tenant_id': self.tenant_id,
            'test_id': self.test_id,
            'control_id': self.control_id,
            'test_type': self.test_type.value if self.test_type else None,
            'testing_period_start': self.testing_period_start.isoformat() if self.testing_period_start else None,
            'testing_period_end': self.testing_period_end.isoformat() if self.testing_period_end else None,
            'sample_size': self.sample_size,
            'population_size': self.population_size,
            'tester_id': self.tester_id,
            'tester_name': self.tester_name,
            'test_steps': self.test_steps,
            'result': self.result.value if self.result else None,
            'exceptions_found': self.exceptions_found,
            'exception_details': self.exception_details,
            'conclusion': self.conclusion,
            'evidence_ids': self.evidence_ids,
            'reviewed_by': self.reviewed_by,
            'reviewed_at': self.reviewed_at.isoformat() if self.reviewed_at else None,
            'status': self.status.value if self.status else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


# ---------------------------------------------------------------------------
# ControlDeficiency  (PC-13)
# ---------------------------------------------------------------------------

class ControlDeficiency(Base, TimestampMixin):
    """
    Control deficiency record surfaced from a test, monitoring run, or
    SoD violation bridge (PC-13).

    Tracks remediation ownership, due dates, verification, and links back to
    the risk register and audit findings.
    """
    __tablename__ = 'control_deficiencies'

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Multi-tenant support
    tenant_id = Column(String(100), nullable=False, index=True, default='tenant_default')

    # Identity
    deficiency_id = Column(String(100), nullable=False, index=True)

    # Parent control
    control_id = Column(Integer, ForeignKey('process_controls.id'), nullable=False, index=True)

    # Source — test, monitoring, sod_bridge, self_assessment
    test_id = Column(Integer, ForeignKey('control_tests.id'), nullable=True, index=True)
    source = Column(String(50), nullable=False, default='test')

    # Description
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)

    # Severity
    severity = Column(SQLEnum(DeficiencySeverity), nullable=False)
    root_cause = Column(Text, nullable=True)

    # Remediation
    remediation_plan = Column(Text, nullable=True)
    remediation_owner_id = Column(String(100), nullable=True)
    remediation_owner_name = Column(String(255), nullable=True)
    due_date = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # Lifecycle
    status = Column(SQLEnum(DeficiencyStatus), nullable=False, default=DeficiencyStatus.OPEN)

    # Verification
    verified_by = Column(String(100), nullable=True)
    verified_at = Column(DateTime, nullable=True)

    # Linked objects
    related_risk_ids = Column(JSON, nullable=True)
    related_finding_ids = Column(JSON, nullable=True)

    # Relationships
    control = relationship('ProcessControl', back_populates='deficiencies')
    test = relationship('ControlTest', back_populates='deficiencies')

    def __repr__(self):
        return (
            f"<ControlDeficiency(deficiency_id='{self.deficiency_id}', "
            f"severity='{self.severity}', status='{self.status}')>"
        )

    def to_dict(self):
        return {
            'id': self.id,
            'tenant_id': self.tenant_id,
            'deficiency_id': self.deficiency_id,
            'control_id': self.control_id,
            'test_id': self.test_id,
            'source': self.source,
            'title': self.title,
            'description': self.description,
            'severity': self.severity.value if self.severity else None,
            'root_cause': self.root_cause,
            'remediation_plan': self.remediation_plan,
            'remediation_owner_id': self.remediation_owner_id,
            'remediation_owner_name': self.remediation_owner_name,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'status': self.status.value if self.status else None,
            'verified_by': self.verified_by,
            'verified_at': self.verified_at.isoformat() if self.verified_at else None,
            'related_risk_ids': self.related_risk_ids,
            'related_finding_ids': self.related_finding_ids,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


# ---------------------------------------------------------------------------
# ControlSelfAssessment  (PC-12)
# ---------------------------------------------------------------------------

class ControlSelfAssessment(Base, TimestampMixin):
    """
    Control Self-Assessment (CSA) — owner-driven attestation campaign (PC-12).

    Control owners complete a questionnaire confirming design adequacy and
    operating effectiveness, then formally attest.  Supports quarterly,
    annual, and ad-hoc campaign types.
    """
    __tablename__ = 'control_self_assessments'

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Multi-tenant support
    tenant_id = Column(String(100), nullable=False, index=True, default='tenant_default')

    # Identity
    assessment_id = Column(String(100), nullable=False, index=True)

    # Campaign metadata
    campaign_name = Column(String(255), nullable=False)
    campaign_type = Column(String(50), nullable=True)   # quarterly, annual, adhoc

    # Parent control
    control_id = Column(Integer, ForeignKey('process_controls.id'), nullable=False, index=True)

    # Assessor (control owner or delegate)
    assessor_id = Column(String(100), nullable=True)
    assessor_name = Column(String(255), nullable=True)

    # Assessment responses
    design_adequate = Column(Boolean, nullable=True)
    operating_effectively = Column(Boolean, nullable=True)
    questionnaire_responses = Column(JSON, nullable=True)  # {question_id: answer}

    # Formal attestation
    attestation = Column(Text, nullable=True)
    attested_at = Column(DateTime, nullable=True)

    # Workflow
    status = Column(SQLEnum(CSAStatus), nullable=False, default=CSAStatus.PENDING)
    due_date = Column(DateTime, nullable=True)

    # Reviewer
    reviewer_id = Column(String(100), nullable=True)
    reviewer_comments = Column(Text, nullable=True)
    reviewed_at = Column(DateTime, nullable=True)

    # Relationships
    control = relationship('ProcessControl', back_populates='self_assessments')

    def __repr__(self):
        return (
            f"<ControlSelfAssessment(assessment_id='{self.assessment_id}', "
            f"control_id={self.control_id}, status='{self.status}')>"
        )

    def to_dict(self):
        return {
            'id': self.id,
            'tenant_id': self.tenant_id,
            'assessment_id': self.assessment_id,
            'campaign_name': self.campaign_name,
            'campaign_type': self.campaign_type,
            'control_id': self.control_id,
            'assessor_id': self.assessor_id,
            'assessor_name': self.assessor_name,
            'design_adequate': self.design_adequate,
            'operating_effectively': self.operating_effectively,
            'questionnaire_responses': self.questionnaire_responses,
            'attestation': self.attestation,
            'attested_at': self.attested_at.isoformat() if self.attested_at else None,
            'status': self.status.value if self.status else None,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'reviewer_id': self.reviewer_id,
            'reviewer_comments': self.reviewer_comments,
            'reviewed_at': self.reviewed_at.isoformat() if self.reviewed_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


# ---------------------------------------------------------------------------
# CCMRule  (PC-20, PC-22)
# ---------------------------------------------------------------------------

class CCMRule(Base, TimestampMixin):
    """
    Continuous Control Monitoring rule definition (PC-20, PC-22).

    Defines an automated check that is periodically executed against a source
    system.  The rule_definition JSON holds the actual check parameters
    (queries, expected values, threshold bounds, etc.).  Breaches can
    auto-create deficiency records.
    """
    __tablename__ = 'ccm_rules'

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Multi-tenant support
    tenant_id = Column(String(100), nullable=False, index=True, default='tenant_default')

    # Identity
    rule_id = Column(String(100), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # Parent control (optional — some CCM rules are standalone monitors)
    control_id = Column(Integer, ForeignKey('process_controls.id'), nullable=True, index=True)

    # Source system
    source_system = Column(String(100), nullable=True)   # SAP, AzureAD, ServiceNow

    # Rule logic
    rule_type = Column(SQLEnum(CCMRuleType), nullable=False)
    rule_definition = Column(JSON, nullable=False)        # check logic / params

    # Threshold evaluation
    threshold_operator = Column(String(20), nullable=True)   # gt, lt, eq, ne, between
    threshold_value = Column(String(255), nullable=True)

    # Scheduling
    frequency = Column(String(50), nullable=True)            # realtime, hourly, daily, weekly

    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    last_run_at = Column(DateTime, nullable=True)
    last_result = Column(String(50), nullable=True)          # pass, fail, error

    # Auto-deficiency creation on breach
    auto_create_deficiency = Column(Boolean, default=True, nullable=False)
    severity_on_breach = Column(String(50), nullable=False, default='observation')

    # False-positive / exclusion management (PC-SAP-GAP: CCM exclusion rules)
    exclusion_rules = Column(JSON, nullable=True)   # [{"field": "company_code", "operator": "eq", "value": "1000"}]
    exclusion_count = Column(Integer, default=0, nullable=False)

    # Relationships
    control = relationship('ProcessControl', back_populates='ccm_rules')
    executions = relationship('CCMExecution', back_populates='rule')

    def __repr__(self):
        return (
            f"<CCMRule(rule_id='{self.rule_id}', "
            f"name='{self.name}', source='{self.source_system}')>"
        )

    def to_dict(self):
        return {
            'id': self.id,
            'tenant_id': self.tenant_id,
            'rule_id': self.rule_id,
            'name': self.name,
            'description': self.description,
            'control_id': self.control_id,
            'source_system': self.source_system,
            'rule_type': self.rule_type.value if self.rule_type else None,
            'rule_definition': self.rule_definition,
            'threshold_operator': self.threshold_operator,
            'threshold_value': self.threshold_value,
            'frequency': self.frequency,
            'is_active': self.is_active,
            'last_run_at': self.last_run_at.isoformat() if self.last_run_at else None,
            'last_result': self.last_result,
            'auto_create_deficiency': self.auto_create_deficiency,
            'severity_on_breach': self.severity_on_breach,
            'exclusion_rules': self.exclusion_rules,
            'exclusion_count': self.exclusion_count,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


# ---------------------------------------------------------------------------
# CCMExecution  (PC-22)
# ---------------------------------------------------------------------------

class CCMExecution(Base, TimestampMixin):
    """
    Result of a single CCM rule execution run (PC-22).

    Each run produces an immutable result row.  If the rule breaches its
    threshold and auto_create_deficiency is enabled, deficiency_id is
    populated with the auto-created ControlDeficiency record.
    """
    __tablename__ = 'ccm_executions'

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Multi-tenant support
    tenant_id = Column(String(100), nullable=False, index=True, default='tenant_default')

    # Parent rule
    rule_id = Column(Integer, ForeignKey('ccm_rules.id'), nullable=False, index=True)

    # Execution details
    executed_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    execution_duration_ms = Column(Integer, nullable=True)

    # Result
    result = Column(SQLEnum(CCMResult), nullable=False)
    findings_count = Column(Integer, nullable=False, default=0)
    findings_detail = Column(JSON, nullable=True)   # list of finding summaries

    # Auto-created deficiency (if threshold breached)
    deficiency_id = Column(Integer, ForeignKey('control_deficiencies.id'), nullable=True, index=True)

    # Relationships
    rule = relationship('CCMRule', back_populates='executions')

    def __repr__(self):
        return (
            f"<CCMExecution(rule_id={self.rule_id}, "
            f"result='{self.result}', findings={self.findings_count})>"
        )

    def to_dict(self):
        return {
            'id': self.id,
            'tenant_id': self.tenant_id,
            'rule_id': self.rule_id,
            'executed_at': self.executed_at.isoformat() if self.executed_at else None,
            'execution_duration_ms': self.execution_duration_ms,
            'result': self.result.value if self.result else None,
            'findings_count': self.findings_count,
            'findings_detail': self.findings_detail,
            'deficiency_id': self.deficiency_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


# ---------------------------------------------------------------------------
# GRCEvidence  (PC-15)
# ---------------------------------------------------------------------------

class GRCEvidence(Base, TimestampMixin):
    """
    Centralised evidence repository for all GRC modules (PC-15).

    Stores metadata and optional content for documents, screenshots, system
    extracts, and attestations linked to control tests, deficiencies,
    findings, and audit workpapers.  Content hashing (SHA-256) provides
    integrity verification.
    """
    __tablename__ = 'grc_evidence'

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Multi-tenant support
    tenant_id = Column(String(100), nullable=False, index=True, default='tenant_default')

    # Identity
    evidence_id = Column(String(100), nullable=False, index=True)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)

    # File metadata
    evidence_type = Column(String(100), nullable=True)      # document, screenshot, export, system_extract, attestation
    file_name = Column(String(500), nullable=True)
    file_path = Column(String(2000), nullable=True)
    file_size = Column(Integer, nullable=True)               # bytes
    mime_type = Column(String(100), nullable=True)

    # Integrity
    content_hash = Column(String(64), nullable=True)         # SHA-256 hex digest

    # Source linkage
    source_module = Column(String(20), nullable=True)               # pc, rm, am, ac
    linked_object_type = Column(String(100), nullable=True)         # control_test, deficiency, finding, audit_workpaper
    linked_object_id = Column(String(100), nullable=True, index=True)

    # Upload
    uploaded_by = Column(String(100), nullable=True)
    upload_date = Column(DateTime, nullable=True, default=datetime.utcnow)

    # Retention & legal hold
    retention_until = Column(DateTime, nullable=True)
    legal_hold = Column(Boolean, default=False, nullable=False)

    # Versioning
    version = Column(Integer, nullable=False, default=1)
    previous_version_id = Column(Integer, ForeignKey('grc_evidence.id'), nullable=True)

    # Status
    status = Column(SQLEnum(EvidenceStatus), nullable=False, default=EvidenceStatus.ACTIVE)

    # Evidence pull metadata (XL-D): source, filters, row_count, generated_at, generated_by, data snapshot
    extract_metadata = Column(JSON, nullable=True)

    # Relationships
    previous_version = relationship('GRCEvidence', remote_side='GRCEvidence.id')

    def __repr__(self):
        return (
            f"<GRCEvidence(evidence_id='{self.evidence_id}', "
            f"title='{self.title[:50]}', status='{self.status}')>"
        )

    def to_dict(self):
        return {
            'id': self.id,
            'tenant_id': self.tenant_id,
            'evidence_id': self.evidence_id,
            'title': self.title,
            'description': self.description,
            'evidence_type': self.evidence_type,
            'file_name': self.file_name,
            'file_path': self.file_path,
            'file_size': self.file_size,
            'mime_type': self.mime_type,
            'content_hash': self.content_hash,
            'source_module': self.source_module,
            'linked_object_type': self.linked_object_type,
            'linked_object_id': self.linked_object_id,
            'uploaded_by': self.uploaded_by,
            'upload_date': self.upload_date.isoformat() if self.upload_date else None,
            'retention_until': self.retention_until.isoformat() if self.retention_until else None,
            'legal_hold': self.legal_hold,
            'version': self.version,
            'previous_version_id': self.previous_version_id,
            'status': self.status.value if self.status else None,
            'extract_metadata': self.extract_metadata,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


# ---------------------------------------------------------------------------
# SignOffCertification  (PC-14)
# ---------------------------------------------------------------------------

class SignOffCertification(Base, TimestampMixin):
    """
    SOX-style cascading management sign-off / certification (PC-14).

    Control owners, process owners, CFOs, and CEOs certify the effectiveness
    of controls within their scope for a defined period.  The self-referential
    parent_certification_id enables roll-up from control owner → CFO → CEO.
    """
    __tablename__ = 'signoff_certifications'

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Multi-tenant support
    tenant_id = Column(String(100), nullable=False, index=True, default='tenant_default')

    # Identity
    certification_id = Column(String(100), nullable=False, index=True)

    # Scope
    period = Column(String(50), nullable=False)          # e.g. "Q2-2026", "FY-2026"
    org_unit_id = Column(Integer, ForeignKey('org_units.id'), nullable=True, index=True)

    # Certifier
    certifier_id = Column(String(100), nullable=False)
    certifier_name = Column(String(255), nullable=True)
    certifier_role = Column(String(100), nullable=True)  # control_owner, process_owner, cfo, ceo

    # Roll-up hierarchy (child → parent)
    parent_certification_id = Column(
        Integer, ForeignKey('signoff_certifications.id'), nullable=True, index=True
    )

    # Certification summary
    scope_summary = Column(Text, nullable=True)
    controls_in_scope = Column(Integer, nullable=False, default=0)
    controls_effective = Column(Integer, nullable=False, default=0)
    deficiencies_open = Column(Integer, nullable=False, default=0)

    # Formal certification statement
    statement = Column(Text, nullable=True)
    certified_at = Column(DateTime, nullable=True)

    # Status
    status = Column(SQLEnum(SignOffStatus), nullable=False, default=SignOffStatus.PENDING)

    # Exceptions and notes
    exceptions = Column(JSON, nullable=True)         # list of exception descriptions
    comments = Column(Text, nullable=True)

    # Relationships
    parent = relationship(
        'SignOffCertification',
        remote_side='SignOffCertification.id',
        back_populates='children',
    )
    children = relationship('SignOffCertification', back_populates='parent')

    def __repr__(self):
        return (
            f"<SignOffCertification(certification_id='{self.certification_id}', "
            f"period='{self.period}', status='{self.status}')>"
        )

    def to_dict(self):
        return {
            'id': self.id,
            'tenant_id': self.tenant_id,
            'certification_id': self.certification_id,
            'period': self.period,
            'org_unit_id': self.org_unit_id,
            'certifier_id': self.certifier_id,
            'certifier_name': self.certifier_name,
            'certifier_role': self.certifier_role,
            'parent_certification_id': self.parent_certification_id,
            'scope_summary': self.scope_summary,
            'controls_in_scope': self.controls_in_scope,
            'controls_effective': self.controls_effective,
            'deficiencies_open': self.deficiencies_open,
            'statement': self.statement,
            'certified_at': self.certified_at.isoformat() if self.certified_at else None,
            'status': self.status.value if self.status else None,
            'exceptions': self.exceptions,
            'comments': self.comments,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


# ---------------------------------------------------------------------------
# ControlObjective  (PC-SAP-GAP-05)
# ---------------------------------------------------------------------------

class ControlObjective(Base, TimestampMixin):
    """
    Formal control objective entity linking controls to specific objectives.

    Provides the objective-based control mapping layer required by GovernexPlus AC
    and COSO/COBIT frameworks.  Linked risks and controls are stored as JSON
    arrays of business-key strings (PC-SAP-GAP-05).
    """
    __tablename__ = 'control_objectives'

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Multi-tenant support
    tenant_id = Column(String(100), nullable=False, index=True, default='tenant_default')

    # Identity — auto-generated as COBJ-{seq}
    objective_id = Column(String(100), nullable=False, index=True)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)

    # Process scope
    process_name = Column(String(255), nullable=True)
    subprocess_name = Column(String(255), nullable=True)

    # Optional framework requirement linkage
    framework_requirement_id = Column(Integer, ForeignKey('framework_requirements.id'), nullable=True, index=True)

    # Linked objects (JSON arrays of business-key strings)
    risk_ids = Column(JSON, nullable=True)     # linked EnterpriseRisk.risk_id values
    control_ids = Column(JSON, nullable=True)  # linked ProcessControl.control_id values

    # Ownership
    owner_id = Column(String(100), nullable=True)
    owner_name = Column(String(255), nullable=True)

    # Lifecycle
    status = Column(SQLEnum(ObjectiveStatus), nullable=False, default=ObjectiveStatus.ACTIVE)
    is_active = Column(Boolean, default=True, nullable=False)

    def __repr__(self):
        return (
            f"<ControlObjective(objective_id='{self.objective_id}', "
            f"title='{self.title[:50]}', status='{self.status}')>"
        )

    def to_dict(self):
        return {
            'id': self.id,
            'tenant_id': self.tenant_id,
            'objective_id': self.objective_id,
            'title': self.title,
            'description': self.description,
            'process_name': self.process_name,
            'subprocess_name': self.subprocess_name,
            'framework_requirement_id': self.framework_requirement_id,
            'risk_ids': self.risk_ids,
            'control_ids': self.control_ids,
            'owner_id': self.owner_id,
            'owner_name': self.owner_name,
            'status': self.status.value if self.status else None,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


# ---------------------------------------------------------------------------
# SubProcess  (PC-SAP-GAP-06)
# ---------------------------------------------------------------------------

class SubProcess(Base, TimestampMixin):
    """
    Formal subprocess hierarchy record.

    Enables multi-level process decomposition (Process → SubProcess → …).
    Self-referential parent_subprocess_id supports unlimited nesting.
    sort_order drives the display sequence within a parent (PC-SAP-GAP-06).
    """
    __tablename__ = 'subprocesses'

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Multi-tenant support
    tenant_id = Column(String(100), nullable=False, index=True, default='tenant_default')

    # Identity — auto-generated as SUB-{seq}
    subprocess_id = Column(String(100), nullable=False, index=True)
    name = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)

    # Parent process (top-level process name)
    process_name = Column(String(255), nullable=False)

    # Self-referential parent for nested hierarchy
    parent_subprocess_id = Column(Integer, ForeignKey('subprocesses.id'), nullable=True, index=True)

    # Organisational scope
    org_unit_id = Column(Integer, ForeignKey('org_units.id'), nullable=True, index=True)

    # Ownership
    owner_id = Column(String(100), nullable=True)
    owner_name = Column(String(255), nullable=True)

    # Hierarchy metadata
    level = Column(Integer, nullable=False, default=1)
    sort_order = Column(Integer, nullable=False, default=0)

    # Linked objects (JSON arrays of business-key strings)
    risk_ids = Column(JSON, nullable=True)
    control_ids = Column(JSON, nullable=True)

    is_active = Column(Boolean, default=True, nullable=False)

    # Relationships
    parent = relationship('SubProcess', remote_side='SubProcess.id', back_populates='children')
    children = relationship('SubProcess', back_populates='parent')

    def __repr__(self):
        return (
            f"<SubProcess(subprocess_id='{self.subprocess_id}', "
            f"name='{self.name[:50]}', level={self.level})>"
        )

    def to_dict(self):
        return {
            'id': self.id,
            'tenant_id': self.tenant_id,
            'subprocess_id': self.subprocess_id,
            'name': self.name,
            'description': self.description,
            'process_name': self.process_name,
            'parent_subprocess_id': self.parent_subprocess_id,
            'org_unit_id': self.org_unit_id,
            'owner_id': self.owner_id,
            'owner_name': self.owner_name,
            'level': self.level,
            'sort_order': self.sort_order,
            'risk_ids': self.risk_ids,
            'control_ids': self.control_ids,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


# ---------------------------------------------------------------------------
# PolicyDocument  (PC-SAP-GAP-07)
# ---------------------------------------------------------------------------

class PolicyDocument(Base, TimestampMixin):
    """
    Full policy lifecycle management.

    Tracks the full lifecycle from draft authoring through board approval,
    publication, periodic review, and retirement.  Version history is
    maintained in version_history JSON.  Supports acknowledgment tracking
    for mandatory policy sign-offs (PC-SAP-GAP-07).
    """
    __tablename__ = 'policy_documents'

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Multi-tenant support
    tenant_id = Column(String(100), nullable=False, index=True, default='tenant_default')

    # Identity — auto-generated as POL-{seq}
    policy_id = Column(String(100), nullable=False, index=True)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)

    # Classification
    policy_type = Column(SQLEnum(PolicyType), nullable=False)

    # Optional framework / regulation linkage
    regulation_id = Column(String(100), nullable=True)

    # Full policy text
    content = Column(Text, nullable=True)

    # Versioning
    version = Column(Integer, nullable=False, default=1)
    version_history = Column(JSON, nullable=True)   # [{version, changed_by, changed_at, summary}]

    # Lifecycle
    status = Column(SQLEnum(PolicyStatus), nullable=False, default=PolicyStatus.DRAFT)

    # Authorship
    author_id = Column(String(100), nullable=True)
    author_name = Column(String(255), nullable=True)

    # Approval
    approved_by = Column(String(100), nullable=True)
    approved_at = Column(DateTime, nullable=True)

    # Publication
    published_at = Column(DateTime, nullable=True)
    effective_date = Column(DateTime, nullable=True)
    expiry_date = Column(DateTime, nullable=True)

    # Review scheduling
    review_frequency = Column(String(50), nullable=True)   # annual, semi_annual, quarterly
    next_review_date = Column(DateTime, nullable=True)
    last_reviewed_at = Column(DateTime, nullable=True)

    # Acknowledgment tracking
    acknowledgment_required = Column(Boolean, default=False, nullable=False)
    acknowledgment_count = Column(Integer, nullable=False, default=0)
    total_recipients = Column(Integer, nullable=False, default=0)

    # Metadata
    tags = Column(JSON, nullable=True)
    attachments = Column(JSON, nullable=True)   # [{file_name, file_path, uploaded_at, uploaded_by}]

    def __repr__(self):
        return (
            f"<PolicyDocument(policy_id='{self.policy_id}', "
            f"title='{self.title[:50]}', version={self.version}, status='{self.status}')>"
        )

    def to_dict(self):
        return {
            'id': self.id,
            'tenant_id': self.tenant_id,
            'policy_id': self.policy_id,
            'title': self.title,
            'description': self.description,
            'policy_type': self.policy_type.value if self.policy_type else None,
            'regulation_id': self.regulation_id,
            'content': self.content,
            'version': self.version,
            'version_history': self.version_history,
            'status': self.status.value if self.status else None,
            'author_id': self.author_id,
            'author_name': self.author_name,
            'approved_by': self.approved_by,
            'approved_at': self.approved_at.isoformat() if self.approved_at else None,
            'published_at': self.published_at.isoformat() if self.published_at else None,
            'effective_date': self.effective_date.isoformat() if self.effective_date else None,
            'expiry_date': self.expiry_date.isoformat() if self.expiry_date else None,
            'review_frequency': self.review_frequency,
            'next_review_date': self.next_review_date.isoformat() if self.next_review_date else None,
            'last_reviewed_at': self.last_reviewed_at.isoformat() if self.last_reviewed_at else None,
            'acknowledgment_required': self.acknowledgment_required,
            'acknowledgment_count': self.acknowledgment_count,
            'total_recipients': self.total_recipients,
            'tags': self.tags,
            'attachments': self.attachments,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


# ---------------------------------------------------------------------------
# QuestionLibrary  (PC-SAP-GAP-08)
# ---------------------------------------------------------------------------

class QuestionLibrary(Base, TimestampMixin):
    """
    Reusable assessment question library.

    Central repository of questions that can be assembled into questionnaires
    for control assessments, risk assessments, audit interviews, and
    compliance surveys.  Questions are tagged by module and category to
    support smart filtering (PC-SAP-GAP-08).
    """
    __tablename__ = 'question_library'

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Multi-tenant support
    tenant_id = Column(String(100), nullable=False, index=True, default='tenant_default')

    # Identity — auto-generated as Q-{seq}
    question_id = Column(String(100), nullable=False, index=True)

    # Question content
    question_text = Column(Text, nullable=False)
    description = Column(Text, nullable=True)

    # Question parameters
    question_type = Column(SQLEnum(QuestionType), nullable=False)
    category = Column(String(100), nullable=False)   # control, risk, compliance, audit, general

    # Options for multiple_choice; null for other types
    options = Column(JSON, nullable=True)

    # Scale bounds for rating_scale questions
    scale_min = Column(Integer, nullable=True)
    scale_max = Column(Integer, nullable=True)

    # Configuration
    required = Column(Boolean, default=True, nullable=False)

    # Which GRC modules this question applies to
    applicable_modules = Column(JSON, nullable=True)   # ['pc', 'rm', 'am']

    # Discovery
    tags = Column(JSON, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    usage_count = Column(Integer, nullable=False, default=0)

    def __repr__(self):
        return (
            f"<QuestionLibrary(question_id='{self.question_id}', "
            f"type='{self.question_type}', category='{self.category}')>"
        )

    def to_dict(self):
        return {
            'id': self.id,
            'tenant_id': self.tenant_id,
            'question_id': self.question_id,
            'question_text': self.question_text,
            'description': self.description,
            'question_type': self.question_type.value if self.question_type else None,
            'category': self.category,
            'options': self.options,
            'scale_min': self.scale_min,
            'scale_max': self.scale_max,
            'required': self.required,
            'applicable_modules': self.applicable_modules,
            'tags': self.tags,
            'is_active': self.is_active,
            'usage_count': self.usage_count,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


# ---------------------------------------------------------------------------
# Questionnaire  (PC-SAP-GAP-09)
# ---------------------------------------------------------------------------

class Questionnaire(Base, TimestampMixin):
    """
    Assembled questionnaire from the question library.

    A questionnaire is an ordered collection of question library entries,
    optionally overriding question parameters for the specific assessment
    context.  Templates can be re-instantiated for recurring campaigns
    (PC-SAP-GAP-09).
    """
    __tablename__ = 'questionnaires'

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Multi-tenant support
    tenant_id = Column(String(100), nullable=False, index=True, default='tenant_default')

    # Identity — auto-generated as QNR-{seq}
    questionnaire_id = Column(String(100), nullable=False, index=True)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)

    # Classification
    questionnaire_type = Column(SQLEnum(QuestionnaireType), nullable=False)

    # Ordered question list — [{question_id, sort_order, required_override, ...}]
    questions = Column(JSON, nullable=True)

    # Module and object linkage
    target_module = Column(String(10), nullable=True)         # pc, rm, am
    linked_object_type = Column(String(100), nullable=True)   # control, risk, engagement
    linked_object_id = Column(String(100), nullable=True)

    # Authorship
    created_by = Column(String(100), nullable=True)

    # Template flag — reusable master vs one-off instance
    is_template = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    # Relationships
    responses = relationship('QuestionnaireResponse', back_populates='questionnaire')

    def __repr__(self):
        return (
            f"<Questionnaire(questionnaire_id='{self.questionnaire_id}', "
            f"title='{self.title[:50]}', type='{self.questionnaire_type}')>"
        )

    def to_dict(self):
        return {
            'id': self.id,
            'tenant_id': self.tenant_id,
            'questionnaire_id': self.questionnaire_id,
            'title': self.title,
            'description': self.description,
            'questionnaire_type': self.questionnaire_type.value if self.questionnaire_type else None,
            'questions': self.questions,
            'target_module': self.target_module,
            'linked_object_type': self.linked_object_type,
            'linked_object_id': self.linked_object_id,
            'created_by': self.created_by,
            'is_template': self.is_template,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


# ---------------------------------------------------------------------------
# QuestionnaireResponse  (PC-SAP-GAP-10)
# ---------------------------------------------------------------------------

class QuestionnaireResponse(Base, TimestampMixin):
    """
    Filled-in questionnaire response from a respondent.

    Stores each answer keyed by question_id in the responses JSON map.
    An optional score is computed from numeric / rating answers.
    Supports multi-round review with reviewer comments (PC-SAP-GAP-10).
    """
    __tablename__ = 'questionnaire_responses'

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Multi-tenant support
    tenant_id = Column(String(100), nullable=False, index=True, default='tenant_default')

    # Identity — auto-generated as QR-{seq}
    response_id = Column(String(100), nullable=False, index=True)

    # Parent questionnaire
    questionnaire_id = Column(Integer, ForeignKey('questionnaires.id'), nullable=False, index=True)

    # Respondent
    respondent_id = Column(String(100), nullable=False)
    respondent_name = Column(String(255), nullable=True)
    respondent_email = Column(String(255), nullable=True)

    # Answers — {question_id: answer_value}
    responses = Column(JSON, nullable=True)

    # Computed score (for rating-based questionnaires)
    score = Column(Float, nullable=True)

    # Workflow
    status = Column(SQLEnum(ResponseStatus), nullable=False, default=ResponseStatus.PENDING)
    submitted_at = Column(DateTime, nullable=True)

    # Review
    reviewed_by = Column(String(100), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    review_comments = Column(Text, nullable=True)

    # Relationships
    questionnaire = relationship('Questionnaire', back_populates='responses')

    def __repr__(self):
        return (
            f"<QuestionnaireResponse(response_id='{self.response_id}', "
            f"respondent_id='{self.respondent_id}', status='{self.status}')>"
        )

    def to_dict(self):
        return {
            'id': self.id,
            'tenant_id': self.tenant_id,
            'response_id': self.response_id,
            'questionnaire_id': self.questionnaire_id,
            'respondent_id': self.respondent_id,
            'respondent_name': self.respondent_name,
            'respondent_email': self.respondent_email,
            'responses': self.responses,
            'score': self.score,
            'status': self.status.value if self.status else None,
            'submitted_at': self.submitted_at.isoformat() if self.submitted_at else None,
            'reviewed_by': self.reviewed_by,
            'reviewed_at': self.reviewed_at.isoformat() if self.reviewed_at else None,
            'review_comments': self.review_comments,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
