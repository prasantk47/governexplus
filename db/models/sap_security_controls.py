"""
Database Models - SAP Security Controls

Models for SAP security controls including control definitions,
evaluation results, and compliance tracking.
"""

from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Text,
    ForeignKey, JSON, Float, Enum as SQLEnum, Index
)
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from .base import Base, TimestampMixin


class RiskRating(enum.Enum):
    """Risk rating levels for security controls"""
    GREEN = "GREEN"
    YELLOW = "YELLOW"
    RED = "RED"


class ControlCategory(enum.Enum):
    """Categories of SAP security controls"""
    GENERAL_AUTHENTICATION = "General Authentication"
    SSO_MANAGEMENT = "Single Sign-On (SSO) Management"
    BASIS_SECURITY_ADMIN = "Basis & Security Administration"
    BACKGROUND_JOB_ADMIN = "Background job Administration"
    OS_COMMANDS_MANAGEMENT = "OS Commands Management"
    CHANGE_MANAGEMENT = "Change Management"
    USER_ADMINISTRATION = "User Administration"
    AUDIT_LOGGING = "Audit Logging"
    RFC_SECURITY = "RFC Security"
    CODE_SECURITY = "Code Security"
    GATEWAY_SECURITY = "Gateway Security"
    TABLE_MAINTENANCE = "Table Maintenance"
    DATA_PRIVACY = "Data Privacy"


class ControlStatus(enum.Enum):
    """Status of a security control"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    DRAFT = "draft"
    DEPRECATED = "deprecated"


class EvaluationStatus(enum.Enum):
    """Status of a control evaluation"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class SAPSecurityControl(Base, TimestampMixin):
    """
    SAP Security Control Definition.

    Defines a security control with its expected values,
    risk ratings, and remediation guidance.
    """
    __tablename__ = 'sap_security_controls'

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Control identification
    control_id = Column(String(50), unique=True, nullable=False, index=True)
    control_name = Column(String(500), nullable=False)

    # Classification
    business_area = Column(String(255), nullable=False)
    control_type = Column(String(255), nullable=False)
    category = Column(String(255), nullable=False)

    # Control details
    description = Column(Text, nullable=False)
    purpose = Column(Text, nullable=True)
    procedure = Column(Text, nullable=True)

    # Technical parameters
    profile_parameter = Column(String(255), nullable=True)
    expected_value = Column(Text, nullable=True)

    # Risk and compliance
    default_risk_rating = Column(SQLEnum(RiskRating), default=RiskRating.YELLOW)
    recommendation = Column(Text, nullable=True)
    comment = Column(Text, nullable=True)

    # Status
    status = Column(SQLEnum(ControlStatus), default=ControlStatus.ACTIVE)
    is_automated = Column(Boolean, default=False)

    # Compliance frameworks
    compliance_frameworks = Column(JSON, nullable=True)  # ['SOX', 'ISO27001', etc.]

    # Relationships
    value_mappings = relationship("ControlValueMapping", back_populates="control", cascade="all, delete-orphan")
    evaluations = relationship("ControlEvaluation", back_populates="control", cascade="all, delete-orphan")

    __table_args__ = (
        Index('ix_sap_controls_category', 'category'),
        Index('ix_sap_controls_business_area', 'business_area'),
        Index('ix_sap_controls_status', 'status'),
    )

    def __repr__(self):
        return f"<SAPSecurityControl(id='{self.control_id}', name='{self.control_name[:50]}...')>"

    def to_dict(self):
        return {
            'id': self.id,
            'control_id': self.control_id,
            'control_name': self.control_name,
            'business_area': self.business_area,
            'control_type': self.control_type,
            'category': self.category,
            'description': self.description,
            'purpose': self.purpose,
            'procedure': self.procedure,
            'profile_parameter': self.profile_parameter,
            'expected_value': self.expected_value,
            'default_risk_rating': self.default_risk_rating.value if self.default_risk_rating else None,
            'recommendation': self.recommendation,
            'comment': self.comment,
            'status': self.status.value if self.status else None,
            'is_automated': self.is_automated,
            'compliance_frameworks': self.compliance_frameworks,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class ControlValueMapping(Base, TimestampMixin):
    """
    Maps specific values to risk ratings for a control.

    Allows defining multiple value conditions that result in
    different risk ratings (GREEN/YELLOW/RED).
    """
    __tablename__ = 'control_value_mappings'

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Parent control
    control_id = Column(Integer, ForeignKey('sap_security_controls.id', ondelete='CASCADE'), nullable=False, index=True)

    # Value condition
    value_condition = Column(Text, nullable=False)  # e.g., "Value is between 1 and 3600"
    value_pattern = Column(String(500), nullable=True)  # Regex or comparison pattern

    # Risk rating for this value
    risk_rating = Column(SQLEnum(RiskRating), nullable=False)

    # Guidance
    recommendation = Column(Text, nullable=True)
    comment = Column(Text, nullable=True)

    # Order for evaluation
    evaluation_order = Column(Integer, default=0)

    # Relationship
    control = relationship("SAPSecurityControl", back_populates="value_mappings")

    def __repr__(self):
        return f"<ControlValueMapping(control_id={self.control_id}, rating='{self.risk_rating.value}')>"

    def to_dict(self):
        return {
            'id': self.id,
            'control_id': self.control_id,
            'value_condition': self.value_condition,
            'value_pattern': self.value_pattern,
            'risk_rating': self.risk_rating.value if self.risk_rating else None,
            'recommendation': self.recommendation,
            'comment': self.comment,
            'evaluation_order': self.evaluation_order
        }


class ControlEvaluation(Base, TimestampMixin):
    """
    Records the evaluation/test result of a security control.

    Captures the actual system value, resulting risk rating,
    and any findings.
    """
    __tablename__ = 'control_evaluations'

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Control reference
    control_id = Column(Integer, ForeignKey('sap_security_controls.id', ondelete='CASCADE'), nullable=False, index=True)

    # System context
    system_id = Column(String(100), nullable=False, index=True)  # SAP System ID
    client = Column(String(10), nullable=True)  # SAP Client

    # Evaluation metadata
    evaluation_id = Column(String(100), unique=True, nullable=False)
    evaluation_date = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    evaluated_by = Column(String(100), nullable=True)

    # Actual values
    actual_value = Column(Text, nullable=True)
    actual_value_details = Column(JSON, nullable=True)  # For complex results

    # Result
    risk_rating = Column(SQLEnum(RiskRating), nullable=False)
    status = Column(SQLEnum(EvaluationStatus), default=EvaluationStatus.COMPLETED)

    # Findings
    finding_description = Column(Text, nullable=True)
    affected_users = Column(JSON, nullable=True)  # List of affected users/roles
    affected_count = Column(Integer, default=0)

    # Evidence
    evidence = Column(JSON, nullable=True)  # Screenshots, logs, etc.
    evidence_path = Column(String(500), nullable=True)

    # Recommendations
    remediation_steps = Column(JSON, nullable=True)
    remediation_deadline = Column(DateTime, nullable=True)
    remediation_owner = Column(String(100), nullable=True)

    # Follow-up
    is_exception_requested = Column(Boolean, default=False)
    exception_id = Column(Integer, ForeignKey('control_exceptions.id', ondelete='SET NULL'), nullable=True)

    # Relationship
    control = relationship("SAPSecurityControl", back_populates="evaluations")
    exception = relationship("ControlException", back_populates="evaluations")

    __table_args__ = (
        Index('ix_evaluations_system', 'system_id', 'evaluation_date'),
        Index('ix_evaluations_rating', 'risk_rating'),
    )

    def __repr__(self):
        return f"<ControlEvaluation(id='{self.evaluation_id}', rating='{self.risk_rating.value}')>"

    def to_dict(self):
        return {
            'id': self.id,
            'control_id': self.control_id,
            'system_id': self.system_id,
            'client': self.client,
            'evaluation_id': self.evaluation_id,
            'evaluation_date': self.evaluation_date.isoformat() if self.evaluation_date else None,
            'evaluated_by': self.evaluated_by,
            'actual_value': self.actual_value,
            'actual_value_details': self.actual_value_details,
            'risk_rating': self.risk_rating.value if self.risk_rating else None,
            'status': self.status.value if self.status else None,
            'finding_description': self.finding_description,
            'affected_users': self.affected_users,
            'affected_count': self.affected_count,
            'remediation_steps': self.remediation_steps,
            'remediation_deadline': self.remediation_deadline.isoformat() if self.remediation_deadline else None,
            'remediation_owner': self.remediation_owner,
            'is_exception_requested': self.is_exception_requested,
            'exception_id': self.exception_id
        }


class ControlException(Base, TimestampMixin):
    """
    Exception/waiver for a control finding.

    Tracks approved exceptions with justification,
    validity period, and compensating controls.
    """
    __tablename__ = 'control_exceptions'

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Exception identification
    exception_id = Column(String(100), unique=True, nullable=False, index=True)

    # Scope
    control_id = Column(Integer, ForeignKey('sap_security_controls.id', ondelete='CASCADE'), nullable=False)
    system_id = Column(String(100), nullable=True)  # Null = all systems

    # Requester
    requested_by = Column(String(100), nullable=False)
    requested_date = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Justification
    business_justification = Column(Text, nullable=False)
    risk_acceptance = Column(Text, nullable=True)
    compensating_controls = Column(JSON, nullable=True)

    # Approval
    approval_status = Column(String(50), default='pending')  # pending, approved, rejected
    approved_by = Column(String(100), nullable=True)
    approved_date = Column(DateTime, nullable=True)
    rejection_reason = Column(Text, nullable=True)

    # Validity
    valid_from = Column(DateTime, nullable=True)
    valid_to = Column(DateTime, nullable=True)
    is_permanent = Column(Boolean, default=False)

    # Review
    review_frequency_days = Column(Integer, default=90)
    next_review_date = Column(DateTime, nullable=True)
    last_review_date = Column(DateTime, nullable=True)

    # Relationships
    control = relationship("SAPSecurityControl")
    evaluations = relationship("ControlEvaluation", back_populates="exception")

    __table_args__ = (
        Index('ix_exceptions_status', 'approval_status'),
        Index('ix_exceptions_validity', 'valid_from', 'valid_to'),
    )

    def __repr__(self):
        return f"<ControlException(id='{self.exception_id}', status='{self.approval_status}')>"

    def to_dict(self):
        return {
            'id': self.id,
            'exception_id': self.exception_id,
            'control_id': self.control_id,
            'system_id': self.system_id,
            'requested_by': self.requested_by,
            'requested_date': self.requested_date.isoformat() if self.requested_date else None,
            'business_justification': self.business_justification,
            'risk_acceptance': self.risk_acceptance,
            'compensating_controls': self.compensating_controls,
            'approval_status': self.approval_status,
            'approved_by': self.approved_by,
            'approved_date': self.approved_date.isoformat() if self.approved_date else None,
            'valid_from': self.valid_from.isoformat() if self.valid_from else None,
            'valid_to': self.valid_to.isoformat() if self.valid_to else None,
            'is_permanent': self.is_permanent,
            'review_frequency_days': self.review_frequency_days,
            'next_review_date': self.next_review_date.isoformat() if self.next_review_date else None
        }


class SystemSecurityProfile(Base, TimestampMixin):
    """
    Security profile for an SAP system.

    Aggregates overall security posture based on control evaluations.
    """
    __tablename__ = 'system_security_profiles'

    id = Column(Integer, primary_key=True, autoincrement=True)

    # System identification
    system_id = Column(String(100), unique=True, nullable=False, index=True)
    system_name = Column(String(255), nullable=True)
    system_type = Column(String(50), nullable=True)  # ECC, S/4HANA, BW, etc.

    # Latest evaluation summary
    last_evaluation_date = Column(DateTime, nullable=True)
    total_controls = Column(Integer, default=0)
    controls_evaluated = Column(Integer, default=0)

    # Risk summary
    green_count = Column(Integer, default=0)
    yellow_count = Column(Integer, default=0)
    red_count = Column(Integer, default=0)

    # Overall score (0-100)
    security_score = Column(Float, default=0.0)

    # Category breakdown
    category_scores = Column(JSON, nullable=True)

    # Compliance status
    compliance_status = Column(JSON, nullable=True)  # Per framework compliance %

    def __repr__(self):
        return f"<SystemSecurityProfile(system='{self.system_id}', score={self.security_score})>"

    def to_dict(self):
        return {
            'id': self.id,
            'system_id': self.system_id,
            'system_name': self.system_name,
            'system_type': self.system_type,
            'last_evaluation_date': self.last_evaluation_date.isoformat() if self.last_evaluation_date else None,
            'total_controls': self.total_controls,
            'controls_evaluated': self.controls_evaluated,
            'green_count': self.green_count,
            'yellow_count': self.yellow_count,
            'red_count': self.red_count,
            'security_score': self.security_score,
            'category_scores': self.category_scores,
            'compliance_status': self.compliance_status
        }
