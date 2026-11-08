"""
GAP-1: Change Governance Management
====================================
Governs changes to master data, configuration, security, GRC rules, workflows.
Risk-based routing, maker-checker, before/after capture, verification.
"""
import enum
from sqlalchemy import Column, String, Text, JSON, DateTime, Integer, Float, Boolean, ForeignKey, func
from .base import Base, TimestampMixin


class ChangeCategory(enum.Enum):
    standard = "standard"
    normal = "normal"
    high_risk = "high_risk"
    emergency = "emergency"
    prohibited = "prohibited"


class ChangeDomain(enum.Enum):
    master_data = "master_data"
    financial_config = "financial_config"
    procurement_config = "procurement_config"
    security_access = "security_access"
    grc_config = "grc_config"
    it_platform = "it_platform"
    org_reference = "org_reference"
    policy_control = "policy_control"


class ChangeStatus(enum.Enum):
    draft = "draft"
    submitted = "submitted"
    risk_assessed = "risk_assessed"
    pending_approval = "pending_approval"
    approved = "approved"
    rejected = "rejected"
    implementing = "implementing"
    implemented = "implemented"
    verifying = "verifying"
    verified = "verified"
    closed = "closed"
    rolled_back = "rolled_back"


class ChangeRequest(Base, TimestampMixin):
    __tablename__ = "change_requests"

    id = Column(String(50), primary_key=True)
    tenant_id = Column(String(50), nullable=False, index=True)
    change_id = Column(String(50), nullable=False, unique=True)
    title = Column(String(300), nullable=False)
    description = Column(Text)
    domain = Column(String(50), nullable=False, default="master_data")
    category = Column(String(50), nullable=False, default="normal")
    status = Column(String(50), nullable=False, default="draft")
    risk_level = Column(String(20), default="medium")

    # Object being changed
    target_system = Column(String(100))
    object_type = Column(String(100))
    object_key = Column(String(200))
    field_name = Column(String(200))
    before_value = Column(Text)
    after_value = Column(Text)
    change_payload = Column(JSON)

    # Actors
    requester = Column(String(100), nullable=False)
    approver = Column(String(100))
    implementer = Column(String(100))
    verifier = Column(String(100))

    # Business context
    justification = Column(Text)
    effective_date = Column(DateTime)
    rollback_plan = Column(Text)
    related_ticket = Column(String(100))
    impact_assessment = Column(Text)

    # Approval
    approved_at = Column(DateTime)
    approved_by = Column(String(100))
    approval_comments = Column(Text)
    rejected_at = Column(DateTime)
    rejected_by = Column(String(100))
    rejection_reason = Column(Text)

    # Implementation
    implemented_at = Column(DateTime)
    implemented_by = Column(String(100))
    implementation_notes = Column(Text)

    # Verification
    verified_at = Column(DateTime)
    verified_by = Column(String(100))
    verification_result = Column(String(50))
    verification_notes = Column(Text)
    discrepancy_found = Column(Boolean, default=False)

    # Monitoring
    post_change_review = Column(Text)
    closed_at = Column(DateTime)
    closed_by = Column(String(100))

    # Linked GRC records
    linked_risk_ids = Column(JSON)
    linked_control_ids = Column(JSON)
    linked_issue_ids = Column(JSON)

    def to_dict(self):
        return {c.name: getattr(self, c.name, None) for c in self.__table__.columns}
