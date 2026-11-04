"""
Issue Tracker — Common GRC Issue & Remediation Lifecycle

Shared issue engine across all modules: risk, controls, audit, fraud,
access violations, vendor issues. One lifecycle, one view.
"""

import enum
from sqlalchemy import Column, String, Text, Integer, DateTime, Boolean, JSON, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from .base import Base, TimestampMixin


class IssueSeverity(str, enum.Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFORMATIONAL = "informational"


class IssueStatus(str, enum.Enum):
    OPEN = "open"
    ASSIGNED = "assigned"
    IN_REMEDIATION = "in_remediation"
    PENDING_VALIDATION = "pending_validation"
    CLOSED = "closed"
    ACCEPTED = "accepted"
    OVERDUE = "overdue"


class IssueSource(str, enum.Enum):
    RISK = "risk"
    CONTROL = "control"
    AUDIT = "audit"
    FRAUD = "fraud"
    ACCESS = "access"
    VENDOR = "vendor"
    MANUAL = "manual"
    CCM = "ccm"
    COMPLIANCE = "compliance"


class IssueType(str, enum.Enum):
    CONTROL_DEFICIENCY = "control_deficiency"
    RISK_EXPOSURE = "risk_exposure"
    AUDIT_FINDING = "audit_finding"
    ACCESS_VIOLATION = "access_violation"
    FRAUD_CASE = "fraud_case"
    VENDOR_ISSUE = "vendor_issue"
    POLICY_BREACH = "policy_breach"
    COMPLIANCE_GAP = "compliance_gap"
    OPERATIONAL = "operational"


class ActionType(str, enum.Enum):
    REMEDIATION = "remediation"
    INVESTIGATION = "investigation"
    ESCALATION = "escalation"
    NOTE = "note"
    STATUS_CHANGE = "status_change"
    EVIDENCE = "evidence"
    VALIDATION = "validation"
    ACCEPTANCE = "acceptance"


class GRCIssue(Base, TimestampMixin):
    """Central issue record shared across all GRC modules."""
    __tablename__ = "grc_issues"

    issue_id = Column(String(50), primary_key=True)
    tenant_id = Column(String(100), nullable=False, index=True)

    # Classification
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    issue_type = Column(String(50), nullable=False, default="operational")
    source_module = Column(String(50), nullable=False, default="manual")
    severity = Column(String(50), nullable=False, default="medium")
    status = Column(String(50), nullable=False, default="open")

    # Source linkage (points back to originating record)
    source_record_id = Column(String(100), nullable=True)   # e.g. risk_id, finding_id
    source_record_type = Column(String(100), nullable=True) # e.g. EnterpriseRisk, AuditFinding

    # Ownership
    owner_id = Column(String(100), nullable=True)
    owner_name = Column(String(200), nullable=True)
    assigned_by = Column(String(100), nullable=True)
    assigned_at = Column(DateTime, nullable=True)

    # Timeline
    identified_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    due_date = Column(DateTime, nullable=True)
    closed_date = Column(DateTime, nullable=True)
    target_remediation_date = Column(DateTime, nullable=True)

    # Root cause
    root_cause = Column(Text, nullable=True)
    root_cause_category = Column(String(100), nullable=True)  # people/process/technology/policy/external

    # Risk impact
    financial_impact = Column(Integer, nullable=True)         # USD
    regulatory_impact = Column(Boolean, default=False)
    reputational_impact = Column(Boolean, default=False)

    # Remediation
    remediation_plan = Column(Text, nullable=True)
    remediation_progress = Column(Integer, default=0)         # 0-100 %
    validation_required = Column(Boolean, default=True)
    validated_by = Column(String(100), nullable=True)
    validated_at = Column(DateTime, nullable=True)

    # Recurrence
    is_repeat = Column(Boolean, default=False)
    repeat_count = Column(Integer, default=0)
    previous_issue_id = Column(String(50), nullable=True)

    # Metadata
    tags = Column(JSON, default=list)
    extra = Column(JSON, default=dict)

    # Audit
    created_by = Column(String(100), nullable=True)
    last_updated_by = Column(String(100), nullable=True)

    actions = relationship("GRCIssueAction", back_populates="issue",
                           cascade="all, delete-orphan", lazy="select")

    def to_dict(self):
        return {
            "issue_id": self.issue_id,
            "tenant_id": self.tenant_id,
            "title": self.title,
            "description": self.description,
            "issue_type": self.issue_type,
            "source_module": self.source_module,
            "severity": self.severity,
            "status": self.status,
            "source_record_id": self.source_record_id,
            "source_record_type": self.source_record_type,
            "owner_id": self.owner_id,
            "owner_name": self.owner_name,
            "assigned_by": self.assigned_by,
            "assigned_at": self.assigned_at.isoformat() if self.assigned_at else None,
            "identified_date": self.identified_date.isoformat() if self.identified_date else None,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "closed_date": self.closed_date.isoformat() if self.closed_date else None,
            "target_remediation_date": self.target_remediation_date.isoformat() if self.target_remediation_date else None,
            "root_cause": self.root_cause,
            "root_cause_category": self.root_cause_category,
            "financial_impact": self.financial_impact,
            "regulatory_impact": self.regulatory_impact,
            "reputational_impact": self.reputational_impact,
            "remediation_plan": self.remediation_plan,
            "remediation_progress": self.remediation_progress,
            "validation_required": self.validation_required,
            "validated_by": self.validated_by,
            "validated_at": self.validated_at.isoformat() if self.validated_at else None,
            "is_repeat": self.is_repeat,
            "repeat_count": self.repeat_count,
            "previous_issue_id": self.previous_issue_id,
            "tags": self.tags or [],
            "extra": self.extra or {},
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class GRCIssueAction(Base):
    """Action/comment log entry for an issue."""
    __tablename__ = "grc_issue_actions"

    action_id = Column(String(50), primary_key=True)
    issue_id = Column(String(50), ForeignKey("grc_issues.issue_id"), nullable=False, index=True)
    tenant_id = Column(String(100), nullable=False, index=True)

    action_type = Column(String(50), nullable=False, default="note")
    performed_by = Column(String(100), nullable=False)
    performed_by_name = Column(String(200), nullable=True)
    performed_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Content
    notes = Column(Text, nullable=True)
    old_status = Column(String(50), nullable=True)
    new_status = Column(String(50), nullable=True)
    evidence_url = Column(String(500), nullable=True)
    evidence_description = Column(Text, nullable=True)

    issue = relationship("GRCIssue", back_populates="actions")

    def to_dict(self):
        return {
            "action_id": self.action_id,
            "issue_id": self.issue_id,
            "action_type": self.action_type,
            "performed_by": self.performed_by,
            "performed_by_name": self.performed_by_name,
            "performed_at": self.performed_at.isoformat() if self.performed_at else None,
            "notes": self.notes,
            "old_status": self.old_status,
            "new_status": self.new_status,
            "evidence_url": self.evidence_url,
            "evidence_description": self.evidence_description,
        }
