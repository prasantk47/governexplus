"""
Policy Management Models

Data models for policy definitions, versions, and approvals.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from enum import Enum
import uuid
import hashlib
import json


class PolicyType(Enum):
    """Types of policies"""
    RISK_RULE = "risk_rule"               # SoD/sensitive access rule
    ACCESS_POLICY = "access_policy"       # Access provisioning policy
    APPROVAL_POLICY = "approval_policy"   # Workflow approval rules
    CERTIFICATION_POLICY = "certification_policy"  # Certification requirements
    FIREFIGHTER_POLICY = "firefighter_policy"     # Emergency access policies
    COMPLIANCE_POLICY = "compliance_policy"       # Regulatory compliance rules
    PASSWORD_POLICY = "password_policy"   # Authentication policies
    RETENTION_POLICY = "retention_policy" # Data retention rules


class PolicyStatus(Enum):
    """Policy lifecycle status"""
    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    RETIRED = "retired"


class ChangeType(Enum):
    """Types of policy changes"""
    CREATE = "create"
    UPDATE = "update"
    ACTIVATE = "activate"
    DEPRECATE = "deprecate"
    RETIRE = "retire"
    ROLLBACK = "rollback"


@dataclass
class PolicyApproval:
    """Record of a policy approval"""
    approval_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    approver_id: str = ""
    approver_name: str = ""
    action: str = "approve"  # approve, reject, comment
    comments: str = ""
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict:
        return {
            "approval_id": self.approval_id,
            "approver_id": self.approver_id,
            "approver_name": self.approver_name,
            "action": self.action,
            "comments": self.comments,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class PolicyVersion:
    """A specific version of a policy"""
    version_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    policy_id: str = ""
    version_number: int = 1
    version_label: str = ""  # e.g., "1.0", "1.1-draft"

    # Content
    content: Dict[str, Any] = field(default_factory=dict)
    content_hash: str = ""  # Hash of content for integrity

    # Metadata
    status: PolicyStatus = PolicyStatus.DRAFT
    created_by: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    change_summary: str = ""
    change_type: ChangeType = ChangeType.CREATE

    # Approvals
    required_approvers: List[str] = field(default_factory=list)
    approvals: List[PolicyApproval] = field(default_factory=list)

    # Effectiveness dates
    effective_from: Optional[datetime] = None
    effective_to: Optional[datetime] = None

    def __post_init__(self):
        if not self.content_hash and self.content:
            self.content_hash = self._compute_hash()
        if not self.version_label:
            self.version_label = f"{self.version_number}.0"

    def _compute_hash(self) -> str:
        """Compute hash of policy content for integrity verification"""
        content_str = json.dumps(self.content, sort_keys=True, default=str)
        return hashlib.sha256(content_str.encode()).hexdigest()[:16]

    def verify_integrity(self) -> bool:
        """Verify content hasn't been tampered with"""
        return self.content_hash == self._compute_hash()

    def is_fully_approved(self) -> bool:
        """Check if all required approvals are obtained"""
        if not self.required_approvers:
            return True

        approved_by = {a.approver_id for a in self.approvals if a.action == "approve"}
        return all(req in approved_by for req in self.required_approvers)

    def is_effective(self) -> bool:
        """Check if policy version is currently effective"""
        now = datetime.now()
        if self.status != PolicyStatus.ACTIVE:
            return False
        if self.effective_from and now < self.effective_from:
            return False
        if self.effective_to and now > self.effective_to:
            return False
        return True

    def to_dict(self) -> Dict:
        return {
            "version_id": self.version_id,
            "policy_id": self.policy_id,
            "version_number": self.version_number,
            "version_label": self.version_label,
            "content": self.content,
            "content_hash": self.content_hash,
            "status": self.status.value,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat(),
            "change_summary": self.change_summary,
            "change_type": self.change_type.value,
            "required_approvers": self.required_approvers,
            "approvals": [a.to_dict() for a in self.approvals],
            "effective_from": self.effective_from.isoformat() if self.effective_from else None,
            "effective_to": self.effective_to.isoformat() if self.effective_to else None,
            "is_fully_approved": self.is_fully_approved(),
            "is_effective": self.is_effective()
        }


@dataclass
class Policy:
    """
    A managed policy with version history.

    Policies define rules and configurations for the GRC platform.
    Each change creates a new version, maintaining full history.
    """
    policy_id: str = field(default_factory=lambda: f"POL-{uuid.uuid4().hex[:8].upper()}")

    # Identity
    name: str = ""
    description: str = ""
    policy_type: PolicyType = PolicyType.RISK_RULE

    # Classification
    category: str = ""
    tags: List[str] = field(default_factory=list)
    scope: Dict[str, Any] = field(default_factory=dict)  # What this policy applies to

    # Ownership
    owner_id: str = ""
    owner_name: str = ""
    owner_department: str = ""
    steward_ids: List[str] = field(default_factory=list)  # Additional responsible parties

    # Versions
    versions: List[PolicyVersion] = field(default_factory=list)
    current_version_id: Optional[str] = None

    # Configuration
    requires_approval: bool = True
    required_approver_count: int = 1
    allowed_approvers: List[str] = field(default_factory=list)
    auto_deprecate_days: Optional[int] = None  # Auto-deprecate after N days

    # Status tracking
    created_at: datetime = field(default_factory=datetime.now)
    last_modified: datetime = field(default_factory=datetime.now)
    last_reviewed: Optional[datetime] = None
    next_review_date: Optional[datetime] = None

    # Compliance
    compliance_frameworks: List[str] = field(default_factory=list)  # SOX, GDPR, etc.
    control_ids: List[str] = field(default_factory=list)  # Related control IDs

    def get_current_version(self) -> Optional[PolicyVersion]:
        """Get the current active version"""
        if self.current_version_id:
            for v in self.versions:
                if v.version_id == self.current_version_id:
                    return v
        return None

    def get_version(self, version_id: str) -> Optional[PolicyVersion]:
        """Get a specific version"""
        for v in self.versions:
            if v.version_id == version_id:
                return v
        return None

    def get_effective_version(self) -> Optional[PolicyVersion]:
        """Get the currently effective version"""
        for v in self.versions:
            if v.is_effective():
                return v
        return None

    def get_version_history(self) -> List[Dict]:
        """Get version history summary"""
        return [
            {
                "version_id": v.version_id,
                "version_label": v.version_label,
                "status": v.status.value,
                "created_by": v.created_by,
                "created_at": v.created_at.isoformat(),
                "change_type": v.change_type.value,
                "change_summary": v.change_summary
            }
            for v in sorted(self.versions, key=lambda x: x.version_number, reverse=True)
        ]

    def get_next_version_number(self) -> int:
        """Get the next version number"""
        if not self.versions:
            return 1
        return max(v.version_number for v in self.versions) + 1

    def is_review_overdue(self) -> bool:
        """Check if policy review is overdue"""
        if not self.next_review_date:
            return False
        return datetime.now() > self.next_review_date

    def to_dict(self) -> Dict:
        current = self.get_current_version()

        return {
            "policy_id": self.policy_id,
            "name": self.name,
            "description": self.description,
            "policy_type": self.policy_type.value,
            "category": self.category,
            "tags": self.tags,
            "scope": self.scope,
            "owner_id": self.owner_id,
            "owner_name": self.owner_name,
            "requires_approval": self.requires_approval,
            "version_count": len(self.versions),
            "current_version": current.to_dict() if current else None,
            "created_at": self.created_at.isoformat(),
            "last_modified": self.last_modified.isoformat(),
            "last_reviewed": self.last_reviewed.isoformat() if self.last_reviewed else None,
            "next_review_date": self.next_review_date.isoformat() if self.next_review_date else None,
            "is_review_overdue": self.is_review_overdue(),
            "compliance_frameworks": self.compliance_frameworks,
            "control_ids": self.control_ids
        }

    def to_summary(self) -> Dict:
        """Brief summary for list views"""
        current = self.get_current_version()

        return {
            "policy_id": self.policy_id,
            "name": self.name,
            "policy_type": self.policy_type.value,
            "category": self.category,
            "owner_name": self.owner_name,
            "current_status": current.status.value if current else "no_version",
            "current_version_label": current.version_label if current else None,
            "version_count": len(self.versions),
            "is_review_overdue": self.is_review_overdue()
        }


@dataclass
class PolicyChange:
    """Record of a policy change for audit trail"""
    change_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    policy_id: str = ""
    version_id: str = ""
    change_type: ChangeType = ChangeType.UPDATE
    changed_by: str = ""
    changed_at: datetime = field(default_factory=datetime.now)
    previous_content: Optional[Dict] = None
    new_content: Optional[Dict] = None
    change_summary: str = ""
    reason: str = ""

    def to_dict(self) -> Dict:
        return {
            "change_id": self.change_id,
            "policy_id": self.policy_id,
            "version_id": self.version_id,
            "change_type": self.change_type.value,
            "changed_by": self.changed_by,
            "changed_at": self.changed_at.isoformat(),
            "change_summary": self.change_summary,
            "reason": self.reason
        }


@dataclass
class PolicyTemplate:
    """Template for creating standardized policies"""
    template_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    description: str = ""
    policy_type: PolicyType = PolicyType.RISK_RULE
    content_schema: Dict[str, Any] = field(default_factory=dict)
    default_content: Dict[str, Any] = field(default_factory=dict)
    required_fields: List[str] = field(default_factory=list)
    example_content: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "template_id": self.template_id,
            "name": self.name,
            "description": self.description,
            "policy_type": self.policy_type.value,
            "content_schema": self.content_schema,
            "default_content": self.default_content,
            "required_fields": self.required_fields,
            "example_content": self.example_content
        }
