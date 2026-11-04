"""
Database Models - Policy Exception Register

Tracks time-bound policy exceptions with approval, conditions, expiry,
and renewal workflow.
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, JSON, Float
from datetime import datetime
import enum

from .base import Base, TimestampMixin


class ExceptionStatus(enum.Enum):
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"
    RENEWAL_PENDING = "renewal_pending"


class ExceptionRisk(enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class PolicyException(Base, TimestampMixin):
    """
    Time-bound policy exception record.

    Tracks requests to deviate from a published policy with formal approval,
    compensating controls, expiry date, and renewal workflow.
    """
    __tablename__ = 'policy_exceptions'

    id = Column(Integer, primary_key=True, autoincrement=True)
    exception_id = Column(String(100), nullable=False, index=True)
    tenant_id = Column(String(100), nullable=False, index=True)

    # Linked policy
    policy_id = Column(String(100), nullable=False, index=True)
    policy_title = Column(String(500), nullable=True)
    policy_section = Column(String(500), nullable=True)   # specific clause/section

    # Request details
    title = Column(String(500), nullable=False)
    justification = Column(Text, nullable=False)
    scope_description = Column(Text, nullable=True)       # affected systems/users/processes
    business_impact_if_denied = Column(Text, nullable=True)

    # Risk assessment
    exception_risk = Column(String(50), nullable=False, default="medium")
    compensating_controls = Column(Text, nullable=True)
    residual_risk_description = Column(Text, nullable=True)

    # Requestor
    requested_by = Column(String(255), nullable=False)
    requested_by_role = Column(String(255), nullable=True)
    requested_at = Column(DateTime, nullable=True, default=datetime.utcnow)
    org_unit = Column(String(255), nullable=True)

    # Approval chain
    approved_by = Column(String(255), nullable=True)
    approved_by_role = Column(String(255), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    second_approver = Column(String(255), nullable=True)
    second_approved_at = Column(DateTime, nullable=True)
    rejection_reason = Column(Text, nullable=True)

    # Validity period
    effective_date = Column(DateTime, nullable=True)
    expiry_date = Column(DateTime, nullable=True)
    duration_days = Column(Integer, nullable=True)

    # Renewal
    renewal_reminder_days = Column(Integer, default=30)
    renewal_count = Column(Integer, default=0)
    last_renewed_at = Column(DateTime, nullable=True)

    # Review
    next_review_date = Column(DateTime, nullable=True)
    reviewed_by = Column(String(255), nullable=True)
    last_reviewed_at = Column(DateTime, nullable=True)

    # Status
    status = Column(String(50), nullable=False, default="pending_approval")
    is_active = Column(Boolean, default=True, nullable=False)
    extra = Column(JSON, nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'exception_id': self.exception_id,
            'tenant_id': self.tenant_id,
            'policy_id': self.policy_id,
            'policy_title': self.policy_title,
            'policy_section': self.policy_section,
            'title': self.title,
            'justification': self.justification,
            'scope_description': self.scope_description,
            'business_impact_if_denied': self.business_impact_if_denied,
            'exception_risk': getattr(self.exception_risk, 'value', self.exception_risk),
            'compensating_controls': self.compensating_controls,
            'residual_risk_description': self.residual_risk_description,
            'requested_by': self.requested_by,
            'requested_by_role': self.requested_by_role,
            'requested_at': self.requested_at.isoformat() if self.requested_at else None,
            'org_unit': self.org_unit,
            'approved_by': self.approved_by,
            'approved_by_role': self.approved_by_role,
            'approved_at': self.approved_at.isoformat() if self.approved_at else None,
            'second_approver': self.second_approver,
            'second_approved_at': self.second_approved_at.isoformat() if self.second_approved_at else None,
            'rejection_reason': self.rejection_reason,
            'effective_date': self.effective_date.isoformat() if self.effective_date else None,
            'expiry_date': self.expiry_date.isoformat() if self.expiry_date else None,
            'duration_days': self.duration_days,
            'renewal_reminder_days': self.renewal_reminder_days,
            'renewal_count': self.renewal_count,
            'last_renewed_at': self.last_renewed_at.isoformat() if self.last_renewed_at else None,
            'next_review_date': self.next_review_date.isoformat() if self.next_review_date else None,
            'reviewed_by': self.reviewed_by,
            'last_reviewed_at': self.last_reviewed_at.isoformat() if self.last_reviewed_at else None,
            'status': getattr(self.status, 'value', self.status),
            'is_active': self.is_active,
            'extra': self.extra,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
