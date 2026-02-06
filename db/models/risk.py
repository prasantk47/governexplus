"""
Database Models - Risk and Violation Management

Models for storing risk analysis results, violations, and mitigation controls.
"""

from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Text,
    ForeignKey, JSON, Float, Enum as SQLEnum
)
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from .base import Base, TimestampMixin


class ViolationStatus(enum.Enum):
    """Risk violation status"""
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    MITIGATED = "mitigated"
    REMEDIATED = "remediated"
    ACCEPTED = "accepted"
    FALSE_POSITIVE = "false_positive"
    CLOSED = "closed"


class RiskSeverityLevel(enum.Enum):
    """Risk severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RiskViolation(Base, TimestampMixin):
    """
    Model for storing detected risk violations.

    Each violation represents a user having conflicting access
    or sensitive permissions that violate defined risk rules.
    """
    __tablename__ = 'risk_violations'

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Multi-tenant support
    tenant_id = Column(String(100), nullable=False, index=True, default='tenant_default')

    # Violation identity
    violation_id = Column(String(100), nullable=False, index=True)

    # Rule reference
    rule_id = Column(String(50), nullable=False, index=True)
    rule_name = Column(String(255), nullable=False)
    rule_type = Column(String(50), nullable=False)  # sod, sensitive, behavioral

    # User reference
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    user_external_id = Column(String(50), nullable=False, index=True)
    username = Column(String(100), nullable=True)

    # Risk details
    severity = Column(SQLEnum(RiskSeverityLevel), nullable=False)
    severity_score = Column(Integer, default=0)  # 0-100
    risk_category = Column(String(50), nullable=False)  # Financial, HR, IT, etc.

    # Conflicting items
    conflicting_functions = Column(JSON, nullable=True)  # List of function names
    conflicting_entitlements = Column(JSON, nullable=True)  # List of auth objects

    # Business context
    business_impact = Column(Text, nullable=True)
    affected_systems = Column(JSON, nullable=True)

    # Status tracking
    status = Column(SQLEnum(ViolationStatus), default=ViolationStatus.OPEN)

    # Detection
    detected_at = Column(DateTime, default=datetime.utcnow)
    detected_by = Column(String(100), default='system')  # system, manual, audit

    # Resolution
    resolved_at = Column(DateTime, nullable=True)
    resolved_by = Column(String(50), nullable=True)
    resolution_notes = Column(Text, nullable=True)

    # Mitigation
    mitigation_id = Column(Integer, ForeignKey('mitigation_controls.id'), nullable=True)
    is_mitigated = Column(Boolean, default=False)

    # Review
    reviewed_by = Column(String(50), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    review_notes = Column(Text, nullable=True)

    # Audit fields
    last_analysis_at = Column(DateTime, nullable=True)
    occurrence_count = Column(Integer, default=1)  # How many times detected

    # Relationships
    user = relationship("User", back_populates="violations")
    mitigation = relationship("MitigationControl", back_populates="violations")

    def __repr__(self):
        return f"<RiskViolation(id='{self.violation_id}', rule='{self.rule_id}', user='{self.user_external_id}')>"

    def to_dict(self):
        return {
            'violation_id': self.violation_id,
            'rule_id': self.rule_id,
            'rule_name': self.rule_name,
            'rule_type': self.rule_type,
            'user_id': self.user_external_id,
            'username': self.username,
            'severity': self.severity.value,
            'severity_score': self.severity_score,
            'risk_category': self.risk_category,
            'conflicting_functions': self.conflicting_functions,
            'status': self.status.value,
            'is_mitigated': self.is_mitigated,
            'detected_at': self.detected_at.isoformat() if self.detected_at else None
        }


class MitigationControl(Base, TimestampMixin):
    """
    Model for mitigation controls that can be applied to violations.

    A mitigation control is a compensating control that reduces risk
    when an SoD conflict cannot be eliminated.
    """
    __tablename__ = 'mitigation_controls'

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Multi-tenant support
    tenant_id = Column(String(100), nullable=False, index=True, default='tenant_default')

    # Control identity
    control_id = Column(String(50), nullable=False, index=True)
    control_name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # Control details
    control_type = Column(String(50), nullable=False)  # preventive, detective, manual
    monitoring_frequency = Column(String(50), default='monthly')  # daily, weekly, monthly

    # Applicable rules
    applicable_rule_ids = Column(JSON, nullable=True)  # List of rule IDs this control mitigates

    # Ownership
    owner_user_id = Column(String(50), nullable=True)
    owner_name = Column(String(255), nullable=True)
    owner_email = Column(String(255), nullable=True)

    # Approval
    approved_by = Column(String(50), nullable=True)
    approved_at = Column(DateTime, nullable=True)

    # Validity
    valid_from = Column(DateTime, default=datetime.utcnow)
    valid_to = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)

    # Effectiveness
    last_tested_at = Column(DateTime, nullable=True)
    test_result = Column(String(50), nullable=True)  # passed, failed, partial

    # Relationships
    violations = relationship("RiskViolation", back_populates="mitigation")

    def __repr__(self):
        return f"<MitigationControl(id='{self.control_id}', name='{self.control_name}')>"


class RiskRuleModel(Base, TimestampMixin):
    """
    Database model for storing risk rules.

    Complements the in-memory rules with database persistence.
    """
    __tablename__ = 'risk_rules'

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Multi-tenant support
    tenant_id = Column(String(100), nullable=False, index=True, default='tenant_default')

    # Rule identity
    rule_id = Column(String(50), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # Rule type and severity
    rule_type = Column(String(50), nullable=False)  # sod, sensitive, critical_action
    severity = Column(SQLEnum(RiskSeverityLevel), nullable=False)
    risk_category = Column(String(50), nullable=False)

    # Rule definition (stored as JSON)
    rule_definition = Column(JSON, nullable=False)  # Full rule config

    # Business context
    business_justification = Column(Text, nullable=True)
    mitigation_controls = Column(JSON, nullable=True)  # List of control descriptions
    recommended_actions = Column(JSON, nullable=True)

    # Applicability
    applies_to_systems = Column(JSON, default=['*'])
    applies_to_departments = Column(JSON, default=['*'])
    exception_users = Column(JSON, default=[])
    exception_roles = Column(JSON, default=[])

    # Status
    is_enabled = Column(Boolean, default=True)
    effective_date = Column(DateTime, nullable=True)
    expiry_date = Column(DateTime, nullable=True)

    # Versioning
    version = Column(String(20), default='1.0')
    created_by = Column(String(50), nullable=True)
    last_modified_by = Column(String(50), nullable=True)

    # Statistics
    violation_count = Column(Integer, default=0)
    last_triggered_at = Column(DateTime, nullable=True)

    def __repr__(self):
        return f"<RiskRuleModel(id='{self.rule_id}', name='{self.name}')>"
