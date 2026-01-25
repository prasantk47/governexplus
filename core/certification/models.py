"""
Access Certification Models

Data models for access review/certification campaigns.
Supports periodic, continuous, and risk-triggered certifications.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from enum import Enum
import uuid


class CampaignStatus(Enum):
    """Campaign lifecycle status"""
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    ACTIVE = "active"
    IN_REVIEW = "in_review"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class CertificationAction(Enum):
    """Actions reviewers can take"""
    CERTIFY = "certify"         # Approve/maintain access
    REVOKE = "revoke"           # Remove access
    MODIFY = "modify"           # Request modification
    DELEGATE = "delegate"       # Delegate to another reviewer
    SKIP = "skip"               # Skip (with justification)


class CampaignType(Enum):
    """Types of certification campaigns"""
    USER_ACCESS = "user_access"       # Review all access for users
    ROLE_MEMBERSHIP = "role_membership"  # Review who has a role
    SENSITIVE_ACCESS = "sensitive_access"  # High-risk access only
    SOD_VIOLATIONS = "sod_violations"    # Review SoD conflicts
    MANAGER_CERTIFICATION = "manager"    # Manager reviews their team
    CONTINUOUS = "continuous"           # Always-on reviews


@dataclass
class CertificationItem:
    """
    A single item to be certified in a campaign.

    Represents one user-role or user-entitlement combination.
    """
    item_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    # What is being certified
    user_id: str = ""
    user_name: str = ""
    user_email: str = ""
    user_department: str = ""

    access_type: str = "role"  # role, entitlement, profile
    access_id: str = ""
    access_name: str = ""
    access_description: str = ""
    system: str = "SAP"

    # Context
    granted_date: Optional[datetime] = None
    last_used: Optional[datetime] = None
    usage_count: int = 0

    # Risk info
    risk_score: float = 0.0
    risk_flags: List[str] = field(default_factory=list)
    has_sod_violation: bool = False
    sod_details: Optional[Dict] = None

    # Reviewer
    reviewer_id: str = ""
    reviewer_name: str = ""
    reviewer_email: str = ""

    # Decision
    decision: Optional[CertificationAction] = None
    decision_date: Optional[datetime] = None
    decision_comments: str = ""
    delegated_to: Optional[str] = None

    # Status
    is_completed: bool = False
    is_overdue: bool = False
    reminder_sent: bool = False

    def to_dict(self) -> Dict:
        return {
            "item_id": self.item_id,
            "user_id": self.user_id,
            "user_name": self.user_name,
            "user_department": self.user_department,
            "access_type": self.access_type,
            "access_id": self.access_id,
            "access_name": self.access_name,
            "risk_score": self.risk_score,
            "risk_flags": self.risk_flags,
            "has_sod_violation": self.has_sod_violation,
            "reviewer_id": self.reviewer_id,
            "reviewer_name": self.reviewer_name,
            "decision": self.decision.value if self.decision else None,
            "decision_date": self.decision_date.isoformat() if self.decision_date else None,
            "decision_comments": self.decision_comments,
            "is_completed": self.is_completed,
            "last_used": self.last_used.isoformat() if self.last_used else None
        }


@dataclass
class CertificationDecision:
    """Record of a certification decision"""
    decision_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    item_id: str = ""
    campaign_id: str = ""

    # Decision details
    action: CertificationAction = CertificationAction.CERTIFY
    reviewer_id: str = ""
    reviewer_name: str = ""
    decision_date: datetime = field(default_factory=datetime.now)
    comments: str = ""

    # For delegation
    delegated_from: Optional[str] = None

    # For revocation
    revocation_reason: Optional[str] = None
    revocation_effective_date: Optional[datetime] = None

    def to_dict(self) -> Dict:
        return {
            "decision_id": self.decision_id,
            "item_id": self.item_id,
            "campaign_id": self.campaign_id,
            "action": self.action.value,
            "reviewer_id": self.reviewer_id,
            "decision_date": self.decision_date.isoformat(),
            "comments": self.comments
        }


@dataclass
class CertificationCampaign:
    """
    A certification campaign containing multiple items to review.
    """
    campaign_id: str = field(default_factory=lambda: f"CERT-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}")

    # Campaign details
    name: str = ""
    description: str = ""
    campaign_type: CampaignType = CampaignType.USER_ACCESS

    # Timing
    start_date: datetime = field(default_factory=datetime.now)
    end_date: datetime = field(default_factory=lambda: datetime.now() + timedelta(days=14))
    created_at: datetime = field(default_factory=datetime.now)

    # Status
    status: CampaignStatus = CampaignStatus.DRAFT

    # Scope
    scope_description: str = ""
    included_systems: List[str] = field(default_factory=lambda: ["SAP"])
    included_departments: List[str] = field(default_factory=list)  # Empty = all
    risk_threshold: Optional[float] = None  # Only items above this risk
    include_sod_only: bool = False

    # Items
    items: List[CertificationItem] = field(default_factory=list)

    # Configuration
    allow_delegation: bool = True
    require_comments_for_revoke: bool = True
    auto_revoke_on_timeout: bool = False
    reminder_days: List[int] = field(default_factory=lambda: [7, 3, 1])

    # Owner
    owner_id: str = ""
    owner_name: str = ""

    # Statistics (computed)
    total_items: int = 0
    completed_items: int = 0
    certified_count: int = 0
    revoked_count: int = 0

    def calculate_progress(self) -> Dict:
        """Calculate campaign progress statistics"""
        if not self.items:
            return {"progress": 0, "completed": 0, "total": 0}

        total = len(self.items)
        completed = sum(1 for i in self.items if i.is_completed)
        certified = sum(1 for i in self.items if i.decision == CertificationAction.CERTIFY)
        revoked = sum(1 for i in self.items if i.decision == CertificationAction.REVOKE)
        overdue = sum(1 for i in self.items if not i.is_completed and datetime.now() > self.end_date)

        return {
            "progress_percent": round((completed / total) * 100, 1),
            "total_items": total,
            "completed_items": completed,
            "pending_items": total - completed,
            "certified_count": certified,
            "revoked_count": revoked,
            "overdue_items": overdue
        }

    def get_reviewer_summary(self) -> Dict[str, Dict]:
        """Get summary by reviewer"""
        summary = {}

        for item in self.items:
            reviewer = item.reviewer_id
            if reviewer not in summary:
                summary[reviewer] = {
                    "reviewer_name": item.reviewer_name,
                    "total": 0,
                    "completed": 0,
                    "pending": 0
                }

            summary[reviewer]["total"] += 1
            if item.is_completed:
                summary[reviewer]["completed"] += 1
            else:
                summary[reviewer]["pending"] += 1

        return summary

    def is_overdue(self) -> bool:
        """Check if campaign is past end date"""
        return datetime.now() > self.end_date

    def days_remaining(self) -> int:
        """Days until campaign ends"""
        delta = self.end_date - datetime.now()
        return max(0, delta.days)

    def to_dict(self) -> Dict:
        progress = self.calculate_progress()

        return {
            "campaign_id": self.campaign_id,
            "name": self.name,
            "description": self.description,
            "campaign_type": self.campaign_type.value,
            "status": self.status.value,
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
            "days_remaining": self.days_remaining(),
            "is_overdue": self.is_overdue(),
            "owner_id": self.owner_id,
            "owner_name": self.owner_name,
            **progress
        }

    def to_summary(self) -> Dict:
        """Brief summary for list views"""
        progress = self.calculate_progress()

        return {
            "campaign_id": self.campaign_id,
            "name": self.name,
            "campaign_type": self.campaign_type.value,
            "status": self.status.value,
            "progress_percent": progress["progress_percent"],
            "days_remaining": self.days_remaining(),
            "total_items": progress["total_items"],
            "pending_items": progress["pending_items"]
        }
