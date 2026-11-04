"""
Database Models - GDPR / Privacy Management Module

Covers Data Processing Inventory, DSAR, DPIA, consent records,
data breach notifications, and data retention schedules.
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, JSON, Float
from datetime import datetime
import enum

from .base import Base, TimestampMixin


class DSARStatus(enum.Enum):
    RECEIVED = "received"
    VERIFIED = "verified"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    REJECTED = "rejected"
    EXTENDED = "extended"


class DSARType(enum.Enum):
    ACCESS = "access"
    ERASURE = "erasure"
    RECTIFICATION = "rectification"
    PORTABILITY = "portability"
    RESTRICTION = "restriction"
    OBJECTION = "objection"


class DPIAStatus(enum.Enum):
    DRAFT = "draft"
    IN_PROGRESS = "in_progress"
    AWAITING_DPO = "awaiting_dpo"
    APPROVED = "approved"
    REJECTED = "rejected"


class BreachSeverity(enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class BreachStatus(enum.Enum):
    DETECTED = "detected"
    INVESTIGATING = "investigating"
    CONTAINED = "contained"
    NOTIFIED_REGULATOR = "notified_regulator"
    NOTIFIED_SUBJECTS = "notified_subjects"
    CLOSED = "closed"


class DataProcessingActivity(Base, TimestampMixin):
    """Data Processing Inventory (Article 30 GDPR record of processing activities)."""
    __tablename__ = 'data_processing_activities'

    id = Column(Integer, primary_key=True, autoincrement=True)
    activity_id = Column(String(100), nullable=False, index=True)
    tenant_id = Column(String(100), nullable=False, index=True)

    name = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    purpose = Column(Text, nullable=False)
    legal_basis = Column(String(100), nullable=True)                 # consent, contract, legal_obligation, vital_interest, public_task, legitimate_interest
    legitimate_interest_assessment = Column(Text, nullable=True)

    # Data categories
    personal_data_categories = Column(JSON, nullable=True)           # list of data types
    special_categories = Column(JSON, nullable=True)                 # health, biometric, etc.
    data_subjects = Column(JSON, nullable=True)                      # employees, customers, etc.

    # Parties
    controller_name = Column(String(255), nullable=True)
    processor_name = Column(String(255), nullable=True)
    third_party_recipients = Column(JSON, nullable=True)

    # Transfers
    transfers_outside_eea = Column(Boolean, default=False)
    transfer_safeguards = Column(String(500), nullable=True)         # adequacy decision, SCCs, BCRs

    # Retention
    retention_period = Column(String(255), nullable=True)
    retention_justification = Column(Text, nullable=True)

    # Security
    security_measures = Column(Text, nullable=True)
    dpia_required = Column(Boolean, default=False)
    dpia_id = Column(String(100), nullable=True)

    # Ownership
    business_owner = Column(String(255), nullable=True)
    system_name = Column(String(255), nullable=True)

    status = Column(String(50), nullable=False, default="active")
    is_active = Column(Boolean, default=True, nullable=False)
    extra = Column(JSON, nullable=True)

    def to_dict(self):
        return {
            'id': self.id, 'activity_id': self.activity_id, 'tenant_id': self.tenant_id,
            'name': self.name, 'description': self.description, 'purpose': self.purpose,
            'legal_basis': self.legal_basis, 'legitimate_interest_assessment': self.legitimate_interest_assessment,
            'personal_data_categories': self.personal_data_categories, 'special_categories': self.special_categories,
            'data_subjects': self.data_subjects, 'controller_name': self.controller_name,
            'processor_name': self.processor_name, 'third_party_recipients': self.third_party_recipients,
            'transfers_outside_eea': self.transfers_outside_eea, 'transfer_safeguards': self.transfer_safeguards,
            'retention_period': self.retention_period, 'retention_justification': self.retention_justification,
            'security_measures': self.security_measures, 'dpia_required': self.dpia_required,
            'dpia_id': self.dpia_id, 'business_owner': self.business_owner, 'system_name': self.system_name,
            'status': getattr(self.status, 'value', self.status), 'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class DSARRequest(Base, TimestampMixin):
    """Data Subject Access Request."""
    __tablename__ = 'dsar_requests'

    id = Column(Integer, primary_key=True, autoincrement=True)
    dsar_id = Column(String(100), nullable=False, index=True)
    tenant_id = Column(String(100), nullable=False, index=True)

    request_type = Column(String(50), nullable=False)
    subject_name = Column(String(255), nullable=False)
    subject_email = Column(String(255), nullable=False)
    subject_id_verified = Column(Boolean, default=False)
    verification_method = Column(String(100), nullable=True)

    description = Column(Text, nullable=True)
    received_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    deadline = Column(DateTime, nullable=True)                       # 30 days from receipt (or 72h for breach)
    extended_deadline = Column(DateTime, nullable=True)

    assigned_to = Column(String(255), nullable=True)
    status = Column(String(50), nullable=False, default="received")

    response_summary = Column(Text, nullable=True)
    rejection_reason = Column(Text, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    completed_by = Column(String(255), nullable=True)

    is_active = Column(Boolean, default=True, nullable=False)
    extra = Column(JSON, nullable=True)

    def to_dict(self):
        return {
            'id': self.id, 'dsar_id': self.dsar_id, 'tenant_id': self.tenant_id,
            'request_type': getattr(self.request_type, 'value', self.request_type),
            'subject_name': self.subject_name, 'subject_email': self.subject_email,
            'subject_id_verified': self.subject_id_verified, 'verification_method': self.verification_method,
            'description': self.description,
            'received_at': self.received_at.isoformat() if self.received_at else None,
            'deadline': self.deadline.isoformat() if self.deadline else None,
            'extended_deadline': self.extended_deadline.isoformat() if self.extended_deadline else None,
            'assigned_to': self.assigned_to, 'status': getattr(self.status, 'value', self.status),
            'response_summary': self.response_summary, 'rejection_reason': self.rejection_reason,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'completed_by': self.completed_by, 'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class DPIAAssessment(Base, TimestampMixin):
    """Data Protection Impact Assessment."""
    __tablename__ = 'dpia_assessments'

    id = Column(Integer, primary_key=True, autoincrement=True)
    dpia_id = Column(String(100), nullable=False, index=True)
    tenant_id = Column(String(100), nullable=False, index=True)

    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    processing_activity_id = Column(String(100), nullable=True, index=True)
    project_name = Column(String(255), nullable=True)

    # Assessment
    necessity_assessment = Column(Text, nullable=True)
    proportionality_assessment = Column(Text, nullable=True)
    risk_assessment = Column(JSON, nullable=True)                    # list of identified risks
    risk_measures = Column(JSON, nullable=True)                      # mitigations per risk

    # Consultation
    dpo_consulted = Column(Boolean, default=False)
    dpo_opinion = Column(Text, nullable=True)
    dpo_consulted_at = Column(DateTime, nullable=True)
    regulator_consulted = Column(Boolean, default=False)
    regulator_response = Column(Text, nullable=True)

    overall_risk_level = Column(String(50), nullable=True)
    conclusion = Column(String(50), nullable=True)                   # proceed / proceed_with_measures / do_not_proceed
    conclusion_notes = Column(Text, nullable=True)

    conducted_by = Column(String(255), nullable=True)
    approved_by = Column(String(255), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    review_date = Column(DateTime, nullable=True)

    status = Column(String(50), nullable=False, default="draft")
    is_active = Column(Boolean, default=True, nullable=False)

    def to_dict(self):
        return {
            'id': self.id, 'dpia_id': self.dpia_id, 'tenant_id': self.tenant_id,
            'title': self.title, 'description': self.description,
            'processing_activity_id': self.processing_activity_id, 'project_name': self.project_name,
            'necessity_assessment': self.necessity_assessment, 'proportionality_assessment': self.proportionality_assessment,
            'risk_assessment': self.risk_assessment, 'risk_measures': self.risk_measures,
            'dpo_consulted': self.dpo_consulted, 'dpo_opinion': self.dpo_opinion,
            'dpo_consulted_at': self.dpo_consulted_at.isoformat() if self.dpo_consulted_at else None,
            'regulator_consulted': self.regulator_consulted, 'regulator_response': self.regulator_response,
            'overall_risk_level': self.overall_risk_level, 'conclusion': self.conclusion,
            'conclusion_notes': self.conclusion_notes, 'conducted_by': self.conducted_by,
            'approved_by': self.approved_by,
            'approved_at': self.approved_at.isoformat() if self.approved_at else None,
            'review_date': self.review_date.isoformat() if self.review_date else None,
            'status': getattr(self.status, 'value', self.status), 'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class DataBreachIncident(Base, TimestampMixin):
    """Data breach notification and management."""
    __tablename__ = 'data_breach_incidents'

    id = Column(Integer, primary_key=True, autoincrement=True)
    breach_id = Column(String(100), nullable=False, index=True)
    tenant_id = Column(String(100), nullable=False, index=True)

    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=False)
    severity = Column(String(50), nullable=False, default="medium")

    detected_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    occurred_at = Column(DateTime, nullable=True)
    contained_at = Column(DateTime, nullable=True)

    breach_type = Column(String(100), nullable=True)                 # unauthorized_access, accidental_disclosure, etc.
    data_categories_affected = Column(JSON, nullable=True)
    subjects_affected_count = Column(Integer, nullable=True)
    systems_affected = Column(JSON, nullable=True)

    # Regulator notification (72-hour rule)
    regulator_notification_required = Column(Boolean, default=False)
    regulator_notified_at = Column(DateTime, nullable=True)
    regulator_reference = Column(String(255), nullable=True)
    regulator_deadline = Column(DateTime, nullable=True)

    # Subject notification
    subjects_notification_required = Column(Boolean, default=False)
    subjects_notified_at = Column(DateTime, nullable=True)

    # Response
    lead_investigator = Column(String(255), nullable=True)
    root_cause = Column(Text, nullable=True)
    remediation_actions = Column(Text, nullable=True)
    lessons_learned = Column(Text, nullable=True)

    status = Column(String(50), nullable=False, default="detected")
    is_active = Column(Boolean, default=True, nullable=False)
    extra = Column(JSON, nullable=True)

    def to_dict(self):
        return {
            'id': self.id, 'breach_id': self.breach_id, 'tenant_id': self.tenant_id,
            'title': self.title, 'description': self.description,
            'severity': getattr(self.severity, 'value', self.severity),
            'detected_at': self.detected_at.isoformat() if self.detected_at else None,
            'occurred_at': self.occurred_at.isoformat() if self.occurred_at else None,
            'contained_at': self.contained_at.isoformat() if self.contained_at else None,
            'breach_type': self.breach_type,
            'data_categories_affected': self.data_categories_affected,
            'subjects_affected_count': self.subjects_affected_count,
            'systems_affected': self.systems_affected,
            'regulator_notification_required': self.regulator_notification_required,
            'regulator_notified_at': self.regulator_notified_at.isoformat() if self.regulator_notified_at else None,
            'regulator_reference': self.regulator_reference,
            'regulator_deadline': self.regulator_deadline.isoformat() if self.regulator_deadline else None,
            'subjects_notification_required': self.subjects_notification_required,
            'subjects_notified_at': self.subjects_notified_at.isoformat() if self.subjects_notified_at else None,
            'lead_investigator': self.lead_investigator,
            'root_cause': self.root_cause, 'remediation_actions': self.remediation_actions,
            'lessons_learned': self.lessons_learned,
            'status': getattr(self.status, 'value', self.status), 'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
