"""
Database Models - Approver Management

Models for managing approver personas (who holds each approver role)
and custom approval rules.
"""

from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Text,
    Float, JSON, UniqueConstraint
)
from datetime import datetime

from .base import Base, TimestampMixin


class ApproverModel(Base, TimestampMixin):
    """
    Approver persona assignment.

    Maps real people to approver types (LINE_MANAGER, SECURITY_OFFICER, etc.)
    Used by the approval determination engine to resolve abstract approver
    specs to concrete approvers.
    """
    __tablename__ = 'approvers'
    __table_args__ = (
        UniqueConstraint('tenant_id', 'approver_id', name='uq_tenant_approver_id'),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(String(100), nullable=False, index=True, default='tenant_default')

    # Identity
    approver_id = Column(String(100), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=True)

    # Type (stored as VARCHAR for flexibility)
    # Values: LINE_MANAGER, ROLE_OWNER, PROCESS_OWNER, DATA_OWNER,
    #         SECURITY_OFFICER, COMPLIANCE_OFFICER, SYSTEM_OWNER,
    #         DELEGATE, AI_RECOMMENDED, GOVERNANCE_DESK, CISO
    approver_type = Column(String(50), nullable=False, index=True)

    # Scope (JSON arrays)
    process_scope = Column(JSON, default=[])   # e.g., ["P2P", "O2C"]
    system_scope = Column(JSON, default=[])    # e.g., ["SAP_PRD", "SAP_QAS"]

    # Availability
    is_active = Column(Boolean, default=True)
    is_available = Column(Boolean, default=True)
    is_ooo = Column(Boolean, default=False)
    ooo_until = Column(DateTime, nullable=True)
    delegate_id = Column(String(100), nullable=True)
    ooo_reason = Column(String(500), nullable=True)
    ooo_approved_by = Column(String(100), nullable=True)

    # Organization
    department = Column(String(100), nullable=True)
    job_title = Column(String(255), nullable=True)

    # Performance metrics
    avg_response_hours = Column(Float, default=0.0)
    approval_rate = Column(Float, default=0.0)
    current_queue_size = Column(Integer, default=0)

    # Status: active, inactive, suspended
    status = Column(String(20), default='active')

    def __repr__(self):
        return f"<Approver(id={self.approver_id}, type={self.approver_type}, name={self.name})>"

    def to_dict(self):
        return {
            'id': self.id,
            'approver_id': self.approver_id,
            'name': self.name,
            'email': self.email,
            'approver_type': self.approver_type,
            'department': self.department,
            'status': self.status,
            'is_available': self.is_available,
            'is_ooo': self.is_ooo,
        }


class ApprovalRuleModel(Base, TimestampMixin):
    """
    Persisted approval rule.

    Allows custom rules beyond the built-in rules defined in
    core/approvals/rules.py. Admins can create tenant-specific
    approval routing rules.
    """
    __tablename__ = 'approval_rules'
    __table_args__ = (
        UniqueConstraint('tenant_id', 'rule_id', name='uq_tenant_approval_rule_id'),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(String(100), nullable=False, index=True, default='tenant_default')

    # Rule identity
    rule_id = Column(String(100), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # Classification
    layer = Column(String(30), nullable=False, default='RISK_ADAPTIVE')
    conditions = Column(JSON, default=[])
    approver_specs = Column(JSON, default=[])

    # Configuration
    sla_hours = Column(Float, default=24.0)
    priority = Column(String(20), default='NORMAL')
    order = Column(Integer, default=100)

    # Status
    is_active = Column(Boolean, default=True)
    is_builtin = Column(Boolean, default=False)

    # Metadata
    created_by = Column(String(50), nullable=True)
    version = Column(String(20), default='1.0')

    def __repr__(self):
        return f"<ApprovalRule(id={self.rule_id}, name={self.name}, layer={self.layer})>"
