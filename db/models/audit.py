"""
Database Models - Audit and Logging

Models for comprehensive audit trails and access request logging.
"""

from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Text,
    ForeignKey, JSON, Enum as SQLEnum
)
from datetime import datetime
import enum

from .base import Base


class AuditAction(enum.Enum):
    """Types of auditable actions"""
    # User actions
    USER_LOGIN = "user_login"
    USER_LOGOUT = "user_logout"
    USER_CREATED = "user_created"
    USER_MODIFIED = "user_modified"
    USER_DELETED = "user_deleted"
    USER_LOCKED = "user_locked"
    USER_UNLOCKED = "user_unlocked"

    # Role actions
    ROLE_ASSIGNED = "role_assigned"
    ROLE_REMOVED = "role_removed"
    ROLE_CREATED = "role_created"
    ROLE_MODIFIED = "role_modified"

    # Risk actions
    RISK_ANALYSIS_RUN = "risk_analysis_run"
    VIOLATION_DETECTED = "violation_detected"
    VIOLATION_MITIGATED = "violation_mitigated"
    VIOLATION_REMEDIATED = "violation_remediated"

    # Firefighter actions
    FF_REQUEST_SUBMITTED = "ff_request_submitted"
    FF_REQUEST_APPROVED = "ff_request_approved"
    FF_REQUEST_REJECTED = "ff_request_rejected"
    FF_SESSION_STARTED = "ff_session_started"
    FF_SESSION_ENDED = "ff_session_ended"
    FF_SESSION_REVOKED = "ff_session_revoked"
    FF_ACTIVITY_LOGGED = "ff_activity_logged"

    # Approver management actions
    APPROVER_CREATED = "approver_created"
    APPROVER_MODIFIED = "approver_modified"
    APPROVER_DELETED = "approver_deleted"
    APPROVER_OOO_SET = "approver_ooo_set"
    APPROVER_AVAILABILITY_TOGGLED = "approver_availability_toggled"

    # System actions
    SYSTEM_CONFIG_CHANGED = "system_config_changed"
    RULE_CREATED = "rule_created"
    RULE_MODIFIED = "rule_modified"
    REPORT_GENERATED = "report_generated"
    DATA_EXPORT = "data_export"
    DATA_IMPORT = "data_import"


class AuditLog(Base):
    """
    Comprehensive audit log for all GRC actions.

    Provides immutable audit trail for compliance and forensics.
    """
    __tablename__ = 'audit_logs'

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Timestamp (indexed for time-based queries)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Action classification
    action = Column(SQLEnum(AuditAction), nullable=False, index=True)
    action_category = Column(String(50), nullable=True)  # user, role, risk, firefighter, system

    # Actor (who performed the action)
    actor_user_id = Column(String(50), nullable=True, index=True)
    actor_username = Column(String(100), nullable=True)
    actor_type = Column(String(50), default='user')  # user, system, api

    # Target (what was affected)
    target_type = Column(String(50), nullable=True)  # user, role, violation, session
    target_id = Column(String(100), nullable=True, index=True)
    target_name = Column(String(255), nullable=True)

    # Context
    source_system = Column(String(50), nullable=True)  # SAP, GRC, API
    source_ip = Column(String(50), nullable=True)
    user_agent = Column(String(500), nullable=True)
    session_id = Column(String(100), nullable=True)

    # Action details (flexible JSON storage)
    details = Column(JSON, nullable=True)
    old_values = Column(JSON, nullable=True)  # For change tracking
    new_values = Column(JSON, nullable=True)

    # Result
    success = Column(Boolean, default=True)
    error_message = Column(Text, nullable=True)

    # Compliance tagging
    compliance_relevant = Column(Boolean, default=False)
    compliance_tags = Column(JSON, nullable=True)  # ['SOX', 'GDPR', etc.]

    # Retention
    retention_period_days = Column(Integer, default=2555)  # ~7 years default

    def __repr__(self):
        return f"<AuditLog(id={self.id}, action='{self.action.value}', actor='{self.actor_user_id}')>"

    def to_dict(self):
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat(),
            'action': self.action.value,
            'action_category': self.action_category,
            'actor_user_id': self.actor_user_id,
            'actor_username': self.actor_username,
            'actor_type': self.actor_type,
            'target_type': self.target_type,
            'target_id': self.target_id,
            'target_name': self.target_name,
            'success': self.success,
            'error_message': self.error_message,
            'details': self.details,
            'old_values': self.old_values,
            'new_values': self.new_values,
            'compliance_relevant': self.compliance_relevant,
            'compliance_tags': self.compliance_tags,
        }


class AccessRequestLog(Base):
    """
    Log for access requests (role assignments, permission changes).

    Tracks the full lifecycle of access provisioning requests.
    """
    __tablename__ = 'access_request_logs'

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Tenant isolation
    tenant_id = Column(String(100), nullable=False, index=True, default="tenant_default")

    # Request identity
    request_id = Column(String(100), unique=True, nullable=False, index=True)
    request_type = Column(String(50), nullable=False)  # new_access, modify, remove, review

    # Timestamps
    submitted_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)

    # Requester
    requester_user_id = Column(String(50), nullable=False, index=True)
    requester_name = Column(String(255), nullable=True)
    requester_email = Column(String(255), nullable=True)
    requester_department = Column(String(100), nullable=True)
    requester_manager = Column(String(50), nullable=True)

    # Target user (who access is being requested for)
    target_user_id = Column(String(50), nullable=False, index=True)
    target_user_name = Column(String(255), nullable=True)

    # Requested access
    requested_roles = Column(JSON, nullable=True)  # List of role IDs
    requested_permissions = Column(JSON, nullable=True)  # Specific permissions

    # Business justification
    business_justification = Column(Text, nullable=True)
    ticket_reference = Column(String(100), nullable=True)
    valid_from = Column(DateTime, nullable=True)
    valid_to = Column(DateTime, nullable=True)

    # Risk analysis
    risk_score = Column(Integer, default=0)
    violations_detected = Column(JSON, nullable=True)  # Pre-request SoD check
    risk_accepted = Column(Boolean, default=False)

    # Approval workflow
    approval_workflow = Column(String(100), nullable=True)
    current_approval_step = Column(Integer, default=1)
    total_approval_steps = Column(Integer, default=1)

    # Approvals (stored as JSON array)
    approvals = Column(JSON, nullable=True)
    # Format: [{"approver": "user", "action": "approved", "timestamp": "...", "comments": "..."}]

    # Final status
    status = Column(String(50), default='pending')  # pending, approved, rejected, cancelled
    final_approver = Column(String(50), nullable=True)
    final_decision_at = Column(DateTime, nullable=True)
    rejection_reason = Column(Text, nullable=True)

    # Provisioning
    provisioned = Column(Boolean, default=False)
    provisioned_at = Column(DateTime, nullable=True)
    provisioned_by = Column(String(50), nullable=True)  # system or manual
    provisioning_errors = Column(JSON, nullable=True)

    def __repr__(self):
        return f"<AccessRequestLog(id='{self.request_id}', status='{self.status}')>"

    def to_dict(self):
        return {
            'request_id': self.request_id,
            'request_type': self.request_type,
            'requester_user_id': self.requester_user_id,
            'target_user_id': self.target_user_id,
            'requested_roles': self.requested_roles,
            'status': self.status,
            'risk_score': self.risk_score,
            'submitted_at': self.submitted_at.isoformat() if self.submitted_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
        }


class CertificationCampaignLog(Base):
    """
    Persistent certification campaign — replaces in-memory self.campaigns dict.
    """
    __tablename__ = 'certification_campaigns'

    id = Column(Integer, primary_key=True, autoincrement=True)
    campaign_id = Column(String(100), unique=True, nullable=False, index=True)
    tenant_id = Column(String(100), nullable=False, index=True, default="tenant_default")

    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    campaign_type = Column(String(50), nullable=False, default="user_access")
    status = Column(String(50), nullable=False, default="draft")

    owner_id = Column(String(50), nullable=False)
    owner_name = Column(String(255), nullable=True)

    start_date = Column(DateTime, nullable=True)
    end_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Scope
    included_systems = Column(JSON, nullable=True)
    included_departments = Column(JSON, nullable=True)
    risk_threshold = Column(Integer, nullable=True)

    # Stats
    total_items = Column(Integer, default=0)
    completed_items = Column(Integer, default=0)
    certified_count = Column(Integer, default=0)
    revoked_count = Column(Integer, default=0)

    # Config overrides (JSON bag)
    config = Column(JSON, nullable=True)

    # Template Library traceability (Phase 1)
    source_template_item_id = Column(String(36), nullable=True, index=True)
    template_version = Column(String(20), nullable=True)
    is_customized = Column(Boolean, nullable=False, default=False)

    def to_dict(self):
        return {
            'campaign_id': self.campaign_id,
            'tenant_id': self.tenant_id,
            'name': self.name,
            'description': self.description,
            'campaign_type': self.campaign_type,
            'status': self.status,
            'owner_id': self.owner_id,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'total_items': self.total_items,
            'completed_items': self.completed_items,
            'certified_count': self.certified_count,
            'revoked_count': self.revoked_count,
        }


class CertificationItemLog(Base):
    """
    Persistent certification item — replaces in-memory campaign.items list.
    """
    __tablename__ = 'certification_items'

    id = Column(Integer, primary_key=True, autoincrement=True)
    item_id = Column(String(100), unique=True, nullable=False, index=True)
    campaign_id = Column(String(100), nullable=False, index=True)
    tenant_id = Column(String(100), nullable=False, index=True, default="tenant_default")

    # What is being reviewed
    user_id = Column(String(50), nullable=False, index=True)
    user_name = Column(String(255), nullable=True)
    user_department = Column(String(100), nullable=True)
    access_type = Column(String(50), default="role")
    access_id = Column(String(100), nullable=False)
    access_name = Column(String(255), nullable=True)
    system = Column(String(50), default="SAP")
    granted_date = Column(DateTime, nullable=True)

    # Risk
    risk_score = Column(Integer, default=0)
    has_sod_violation = Column(Boolean, default=False)
    risk_flags = Column(JSON, nullable=True)

    # Review
    reviewer_id = Column(String(50), nullable=False)
    reviewer_name = Column(String(255), nullable=True)
    decision = Column(String(50), nullable=True)  # certify, revoke, delegate
    decision_date = Column(DateTime, nullable=True)
    decision_comments = Column(Text, nullable=True)
    is_completed = Column(Boolean, default=False)

    # Escalation
    escalation_level = Column(Integer, default=0)
    is_overdue = Column(Boolean, default=False)

    def to_dict(self):
        return {
            'item_id': self.item_id,
            'campaign_id': self.campaign_id,
            'user_id': self.user_id,
            'user_name': self.user_name,
            'access_id': self.access_id,
            'access_name': self.access_name,
            'risk_score': self.risk_score,
            'decision': self.decision,
            'is_completed': self.is_completed,
        }
