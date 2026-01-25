"""
Database Models - Firefighter/Emergency Access Management

Models for persisting firefighter requests, sessions, and activity logs.
"""

from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Text,
    ForeignKey, JSON, Float, Enum as SQLEnum, Interval
)
from sqlalchemy.orm import relationship
from datetime import datetime, timedelta
import enum

from .base import Base, TimestampMixin


class FFRequestStatus(enum.Enum):
    """Firefighter request status"""
    REQUESTED = "requested"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class FFSessionStatus(enum.Enum):
    """Firefighter session status"""
    ACTIVE = "active"
    COMPLETED = "completed"
    EXPIRED = "expired"
    REVOKED = "revoked"


class FFPriority(enum.Enum):
    """Request priority"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class FirefighterRequest(Base, TimestampMixin):
    """
    Model for firefighter access requests.
    """
    __tablename__ = 'firefighter_requests'

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Request identity
    request_id = Column(String(50), unique=True, nullable=False, index=True)

    # Requester info
    requester_user_id = Column(String(50), nullable=False, index=True)
    requester_name = Column(String(255), nullable=True)
    requester_email = Column(String(255), nullable=True)
    requester_department = Column(String(100), nullable=True)

    # Target access
    target_system = Column(String(50), nullable=False)
    firefighter_id = Column(String(50), nullable=False, index=True)

    # Request details
    reason = Column(Text, nullable=False)
    business_justification = Column(Text, nullable=True)
    ticket_reference = Column(String(100), nullable=True)  # Incident/change ticket

    # Timing
    requested_duration_minutes = Column(Integer, default=120)  # Default 2 hours
    needed_by = Column(DateTime, nullable=True)

    # Priority and category
    priority = Column(SQLEnum(FFPriority), default=FFPriority.MEDIUM)
    category = Column(String(50), default='general')  # incident, change, audit

    # Status
    status = Column(SQLEnum(FFRequestStatus), default=FFRequestStatus.REQUESTED)

    # Risk assessment
    risk_score = Column(Float, default=0.0)
    requires_dual_approval = Column(Boolean, default=False)

    # Approval workflow
    approvers = Column(JSON, nullable=True)  # List of approver emails
    approved_by = Column(String(50), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    approval_comments = Column(Text, nullable=True)

    # Rejection
    rejected_by = Column(String(50), nullable=True)
    rejected_at = Column(DateTime, nullable=True)
    rejection_reason = Column(Text, nullable=True)

    # Relationships
    session = relationship("FirefighterSession", back_populates="request", uselist=False)

    def __repr__(self):
        return f"<FirefighterRequest(id='{self.request_id}', requester='{self.requester_user_id}')>"

    def to_dict(self):
        return {
            'request_id': self.request_id,
            'requester_user_id': self.requester_user_id,
            'requester_name': self.requester_name,
            'target_system': self.target_system,
            'firefighter_id': self.firefighter_id,
            'reason': self.reason,
            'priority': self.priority.value,
            'status': self.status.value,
            'risk_score': self.risk_score,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'approved_by': self.approved_by,
            'approved_at': self.approved_at.isoformat() if self.approved_at else None
        }


class FirefighterSession(Base, TimestampMixin):
    """
    Model for active and completed firefighter sessions.
    """
    __tablename__ = 'firefighter_sessions'

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Session identity
    session_id = Column(String(50), unique=True, nullable=False, index=True)

    # Request reference
    request_id = Column(String(50), ForeignKey('firefighter_requests.request_id'), nullable=False)

    # Users
    requester_user_id = Column(String(50), nullable=False, index=True)
    firefighter_id = Column(String(50), nullable=False, index=True)

    # Target
    target_system = Column(String(50), nullable=False)

    # Timing
    start_time = Column(DateTime, nullable=False)
    scheduled_end_time = Column(DateTime, nullable=False)
    actual_end_time = Column(DateTime, nullable=True)

    # Status
    status = Column(SQLEnum(FFSessionStatus), default=FFSessionStatus.ACTIVE)

    # Security
    session_token_hash = Column(String(255), nullable=True)  # Hash of session token
    mfa_verified = Column(Boolean, default=False)
    mfa_verified_at = Column(DateTime, nullable=True)

    # Session info
    reason = Column(Text, nullable=True)
    approver = Column(String(50), nullable=True)

    # Activity tracking
    activity_count = Column(Integer, default=0)
    sensitive_action_count = Column(Integer, default=0)

    # Termination
    terminated_by = Column(String(50), nullable=True)
    termination_reason = Column(Text, nullable=True)

    # Review
    requires_review = Column(Boolean, default=True)
    reviewed_by = Column(String(50), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    review_status = Column(String(50), nullable=True)  # approved, flagged
    review_comments = Column(Text, nullable=True)

    # Client info
    client_ip = Column(String(50), nullable=True)
    user_agent = Column(String(500), nullable=True)

    # Relationships
    request = relationship("FirefighterRequest", back_populates="session")
    activities = relationship("FirefighterActivity", back_populates="session",
                            cascade="all, delete-orphan")

    def __repr__(self):
        return f"<FirefighterSession(id='{self.session_id}', ff='{self.firefighter_id}')>"

    def is_active(self) -> bool:
        """Check if session is currently active"""
        if self.status != FFSessionStatus.ACTIVE:
            return False
        return datetime.utcnow() < self.scheduled_end_time

    def remaining_minutes(self) -> int:
        """Get remaining session time in minutes"""
        if not self.is_active():
            return 0
        delta = self.scheduled_end_time - datetime.utcnow()
        return max(0, int(delta.total_seconds() / 60))

    def to_dict(self):
        return {
            'session_id': self.session_id,
            'request_id': self.request_id,
            'requester_user_id': self.requester_user_id,
            'firefighter_id': self.firefighter_id,
            'target_system': self.target_system,
            'start_time': self.start_time.isoformat(),
            'scheduled_end_time': self.scheduled_end_time.isoformat(),
            'actual_end_time': self.actual_end_time.isoformat() if self.actual_end_time else None,
            'status': self.status.value,
            'activity_count': self.activity_count,
            'sensitive_action_count': self.sensitive_action_count,
            'requires_review': self.requires_review,
            'remaining_minutes': self.remaining_minutes()
        }


class FirefighterActivity(Base):
    """
    Model for logging activities during firefighter sessions.
    """
    __tablename__ = 'firefighter_activities'

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Activity identity
    activity_id = Column(String(100), unique=True, nullable=False, index=True)

    # Session reference
    session_id = Column(String(50), ForeignKey('firefighter_sessions.session_id'), nullable=False)

    # Timing
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Activity details
    action_type = Column(String(50), nullable=False)  # TCODE_EXECUTE, DATA_CHANGE, etc.
    action_details = Column(JSON, nullable=True)

    # SAP-specific
    transaction_code = Column(String(50), nullable=True, index=True)
    program_name = Column(String(100), nullable=True)
    table_name = Column(String(100), nullable=True)

    # Client context
    client_ip = Column(String(50), nullable=True)
    user_agent = Column(String(500), nullable=True)
    sap_gui_version = Column(String(50), nullable=True)

    # Risk indicators
    is_sensitive = Column(Boolean, default=False)
    requires_review = Column(Boolean, default=False)
    risk_flag = Column(String(50), nullable=True)

    # Review
    reviewed = Column(Boolean, default=False)
    reviewer_comments = Column(Text, nullable=True)

    # Relationships
    session = relationship("FirefighterSession", back_populates="activities")

    def __repr__(self):
        return f"<FirefighterActivity(id='{self.activity_id}', action='{self.action_type}')>"

    def to_dict(self):
        return {
            'activity_id': self.activity_id,
            'session_id': self.session_id,
            'timestamp': self.timestamp.isoformat(),
            'action_type': self.action_type,
            'transaction_code': self.transaction_code,
            'is_sensitive': self.is_sensitive,
            'requires_review': self.requires_review,
            'action_details': self.action_details
        }
