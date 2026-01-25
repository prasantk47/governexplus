# Role Certification Intelligence
# Evidence-based certification with usage insights

"""
Role Certification for GOVERNEX+.

Features:
- Usage-evidence based certification
- Risk-aware certification decisions
- Auto-expire unused roles
- Intelligent certification campaigns
"""

from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional, Any
from datetime import datetime, timedelta
from enum import Enum
import logging

from .models import Role

logger = logging.getLogger(__name__)


class CertificationStatus(Enum):
    """Status of certification campaign."""
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class DecisionType(Enum):
    """Types of certification decisions."""
    CERTIFY = "CERTIFY"
    REVOKE = "REVOKE"
    MODIFY = "MODIFY"
    DELEGATE = "DELEGATE"
    DEFER = "DEFER"


@dataclass
class CertificationEvidence:
    """
    Evidence supporting certification decision.

    Provides data-driven insights for certifiers.
    """
    role_id: str
    user_id: Optional[str] = None

    # Usage evidence
    usage_last_90_days: int = 0
    usage_trend: str = "stable"  # increasing, stable, decreasing
    unused_permissions_count: int = 0
    most_used_permissions: List[str] = field(default_factory=list)
    least_used_permissions: List[str] = field(default_factory=list)

    # Risk evidence
    current_risk_score: float = 0.0
    risk_trend: str = "stable"
    sod_conflicts: int = 0
    sensitive_access_count: int = 0

    # Peer comparison
    peer_usage_percentile: float = 50.0
    peers_with_role: int = 0
    typical_for_job_function: bool = True

    # Recommendation
    ai_recommendation: DecisionType = DecisionType.CERTIFY
    ai_confidence: float = 0.0
    recommendation_rationale: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "role_id": self.role_id,
            "user_id": self.user_id,
            "usage_last_90_days": self.usage_last_90_days,
            "usage_trend": self.usage_trend,
            "unused_permissions_count": self.unused_permissions_count,
            "most_used_permissions": self.most_used_permissions[:5],
            "current_risk_score": round(self.current_risk_score, 2),
            "sod_conflicts": self.sod_conflicts,
            "peer_usage_percentile": round(self.peer_usage_percentile, 2),
            "typical_for_job_function": self.typical_for_job_function,
            "ai_recommendation": self.ai_recommendation.value,
            "ai_confidence": round(self.ai_confidence, 4),
            "recommendation_rationale": self.recommendation_rationale,
        }


@dataclass
class CertificationDecision:
    """
    A certification decision for a role/user.

    Records the decision and supporting information.
    """
    decision_id: str
    campaign_id: str
    role_id: str
    user_id: Optional[str] = None

    # Decision
    decision: DecisionType = DecisionType.CERTIFY
    comments: str = ""
    justification: str = ""

    # Evidence used
    evidence: Optional[CertificationEvidence] = None
    followed_recommendation: bool = True

    # Approver
    decided_by: str = ""
    decided_at: Optional[datetime] = None

    # Actions taken
    actions_required: List[str] = field(default_factory=list)
    actions_completed: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "campaign_id": self.campaign_id,
            "role_id": self.role_id,
            "user_id": self.user_id,
            "decision": self.decision.value,
            "comments": self.comments,
            "justification": self.justification,
            "evidence": self.evidence.to_dict() if self.evidence else None,
            "followed_recommendation": self.followed_recommendation,
            "decided_by": self.decided_by,
            "decided_at": self.decided_at.isoformat() if self.decided_at else None,
            "actions_required": self.actions_required,
            "actions_completed": self.actions_completed,
        }


@dataclass
class CertificationCampaign:
    """
    A certification campaign.

    Organizes bulk certification of roles/assignments.
    """
    campaign_id: str
    name: str
    description: str

    # Scope
    target_roles: List[str] = field(default_factory=list)
    target_users: List[str] = field(default_factory=list)
    scope_type: str = "ROLE"  # ROLE, USER, COMBINED

    # Timing
    start_date: datetime = field(default_factory=datetime.now)
    due_date: Optional[datetime] = None
    completed_date: Optional[datetime] = None

    # Status
    status: CertificationStatus = CertificationStatus.DRAFT

    # Progress
    total_items: int = 0
    certified_count: int = 0
    revoked_count: int = 0
    pending_count: int = 0

    # Decisions
    decisions: List[CertificationDecision] = field(default_factory=list)

    # Settings
    require_justification: bool = True
    allow_bulk_decisions: bool = False
    auto_revoke_on_expiry: bool = True
    reminder_days: List[int] = field(default_factory=lambda: [7, 3, 1])

    # Owner
    owner_id: str = ""
    certifiers: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "campaign_id": self.campaign_id,
            "name": self.name,
            "description": self.description,
            "target_roles": self.target_roles,
            "target_users": self.target_users,
            "scope_type": self.scope_type,
            "start_date": self.start_date.isoformat(),
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "status": self.status.value,
            "total_items": self.total_items,
            "certified_count": self.certified_count,
            "revoked_count": self.revoked_count,
            "pending_count": self.pending_count,
            "progress_percent": round(
                (self.certified_count + self.revoked_count) / max(self.total_items, 1) * 100, 2
            ),
            "owner_id": self.owner_id,
        }


class RoleCertificationEngine:
    """
    Intelligent role certification engine.

    Key capabilities:
    - Generate evidence for certification decisions
    - AI-powered recommendations
    - Campaign management
    - Auto-expiry for uncertified roles
    """

    # Thresholds for recommendations
    UNUSED_DAYS_REVOKE_THRESHOLD = 90
    LOW_USAGE_REVOKE_THRESHOLD = 5
    HIGH_RISK_REVIEW_THRESHOLD = 70

    def __init__(self):
        """Initialize certification engine."""
        self._campaigns: Dict[str, CertificationCampaign] = {}
        self._decision_counter = 0

    def generate_evidence(
        self,
        role: Role,
        user_id: Optional[str] = None,
        usage_data: Optional[Dict[str, Any]] = None,
        risk_data: Optional[Dict[str, Any]] = None,
        peer_data: Optional[Dict[str, Any]] = None
    ) -> CertificationEvidence:
        """
        Generate evidence for certification.

        Args:
            role: Role being certified
            user_id: User if user-role certification
            usage_data: Role usage analytics
            risk_data: Role risk data
            peer_data: Peer comparison data

        Returns:
            CertificationEvidence with insights and recommendation
        """
        usage_data = usage_data or {}
        risk_data = risk_data or {}
        peer_data = peer_data or {}

        evidence = CertificationEvidence(
            role_id=role.role_id,
            user_id=user_id,
        )

        # Usage evidence
        evidence.usage_last_90_days = usage_data.get("total_executions", 0)
        evidence.usage_trend = usage_data.get("trend", "stable")
        evidence.unused_permissions_count = usage_data.get("unused_permissions", 0)
        evidence.most_used_permissions = usage_data.get("most_used", [])[:5]
        evidence.least_used_permissions = usage_data.get("least_used", [])[:5]

        # Risk evidence
        evidence.current_risk_score = risk_data.get("risk_score", 0)
        evidence.risk_trend = risk_data.get("trend", "stable")
        evidence.sod_conflicts = risk_data.get("sod_conflicts", 0)
        evidence.sensitive_access_count = role.sensitive_permission_count

        # Peer comparison
        evidence.peer_usage_percentile = peer_data.get("usage_percentile", 50)
        evidence.peers_with_role = peer_data.get("peers_with_role", 0)
        evidence.typical_for_job_function = peer_data.get("typical", True)

        # Generate AI recommendation
        evidence.ai_recommendation, evidence.ai_confidence, evidence.recommendation_rationale = \
            self._generate_recommendation(evidence)

        return evidence

    def _generate_recommendation(
        self,
        evidence: CertificationEvidence
    ) -> tuple[DecisionType, float, str]:
        """Generate AI-powered certification recommendation."""
        # Decision logic
        revoke_signals = []
        certify_signals = []

        # Usage-based signals
        if evidence.usage_last_90_days == 0:
            revoke_signals.append("No usage in 90 days")
        elif evidence.usage_last_90_days < self.LOW_USAGE_REVOKE_THRESHOLD:
            revoke_signals.append(f"Very low usage ({evidence.usage_last_90_days} in 90 days)")
        else:
            certify_signals.append("Active usage")

        # Risk-based signals
        if evidence.current_risk_score > self.HIGH_RISK_REVIEW_THRESHOLD:
            revoke_signals.append(f"High risk score ({evidence.current_risk_score:.0f})")
        elif evidence.current_risk_score < 40:
            certify_signals.append("Low risk")

        if evidence.sod_conflicts > 0:
            revoke_signals.append(f"{evidence.sod_conflicts} SoD conflicts")

        # Peer comparison
        if not evidence.typical_for_job_function:
            revoke_signals.append("Atypical for job function")
        else:
            certify_signals.append("Typical for job function")

        if evidence.peer_usage_percentile < 10:
            revoke_signals.append(f"Usage below {evidence.peer_usage_percentile:.0f}% of peers")

        # Calculate recommendation
        if len(revoke_signals) >= 3:
            return (
                DecisionType.REVOKE,
                0.9,
                f"Recommend revocation: {'; '.join(revoke_signals)}"
            )
        elif len(revoke_signals) >= 2:
            return (
                DecisionType.MODIFY,
                0.7,
                f"Recommend review: {'; '.join(revoke_signals)}"
            )
        elif len(certify_signals) >= 2:
            return (
                DecisionType.CERTIFY,
                0.85,
                f"Recommend certification: {'; '.join(certify_signals)}"
            )
        else:
            return (
                DecisionType.DEFER,
                0.5,
                "Insufficient evidence for clear recommendation"
            )

    def create_campaign(
        self,
        name: str,
        description: str,
        roles: List[Role],
        due_days: int = 30,
        owner_id: str = "",
        certifiers: Optional[List[str]] = None
    ) -> CertificationCampaign:
        """
        Create a certification campaign.

        Args:
            name: Campaign name
            description: Campaign description
            roles: Roles to certify
            due_days: Days until due
            owner_id: Campaign owner
            certifiers: List of certifier IDs

        Returns:
            Created campaign
        """
        campaign_id = f"CERT-{datetime.now().strftime('%Y%m%d%H%M%S')}"

        campaign = CertificationCampaign(
            campaign_id=campaign_id,
            name=name,
            description=description,
            target_roles=[r.role_id for r in roles],
            scope_type="ROLE",
            due_date=datetime.now() + timedelta(days=due_days),
            total_items=len(roles),
            pending_count=len(roles),
            owner_id=owner_id,
            certifiers=certifiers or [],
        )

        self._campaigns[campaign_id] = campaign
        return campaign

    def record_decision(
        self,
        campaign_id: str,
        role_id: str,
        decision: DecisionType,
        decided_by: str,
        comments: str = "",
        justification: str = "",
        user_id: Optional[str] = None,
        evidence: Optional[CertificationEvidence] = None
    ) -> CertificationDecision:
        """
        Record a certification decision.

        Args:
            campaign_id: Campaign ID
            role_id: Role being certified
            decision: The decision
            decided_by: Certifier ID
            comments: Optional comments
            justification: Required justification (for non-certify)
            user_id: User if user-role certification
            evidence: Evidence used

        Returns:
            Recorded decision
        """
        campaign = self._campaigns.get(campaign_id)
        if not campaign:
            raise ValueError(f"Campaign {campaign_id} not found")

        self._decision_counter += 1
        decision_record = CertificationDecision(
            decision_id=f"DEC-{self._decision_counter}",
            campaign_id=campaign_id,
            role_id=role_id,
            user_id=user_id,
            decision=decision,
            comments=comments,
            justification=justification,
            evidence=evidence,
            decided_by=decided_by,
            decided_at=datetime.now(),
        )

        # Check if followed recommendation
        if evidence:
            decision_record.followed_recommendation = (
                decision == evidence.ai_recommendation
            )

        # Determine required actions
        if decision == DecisionType.REVOKE:
            decision_record.actions_required = ["Remove role from user/system"]
        elif decision == DecisionType.MODIFY:
            decision_record.actions_required = ["Review and remove unused permissions"]

        campaign.decisions.append(decision_record)

        # Update counts
        campaign.pending_count -= 1
        if decision == DecisionType.CERTIFY:
            campaign.certified_count += 1
        elif decision == DecisionType.REVOKE:
            campaign.revoked_count += 1

        # Check completion
        if campaign.pending_count == 0:
            campaign.status = CertificationStatus.COMPLETED
            campaign.completed_date = datetime.now()

        return decision_record

    def get_campaign(self, campaign_id: str) -> Optional[CertificationCampaign]:
        """Get a campaign by ID."""
        return self._campaigns.get(campaign_id)

    def get_active_campaigns(self) -> List[CertificationCampaign]:
        """Get all active campaigns."""
        return [
            c for c in self._campaigns.values()
            if c.status == CertificationStatus.ACTIVE
        ]

    def get_overdue_items(
        self,
        campaign_id: str
    ) -> List[str]:
        """Get items overdue for certification."""
        campaign = self._campaigns.get(campaign_id)
        if not campaign or not campaign.due_date:
            return []

        if datetime.now() < campaign.due_date:
            return []

        # Find uncertified roles
        certified_roles = {d.role_id for d in campaign.decisions}
        return [r for r in campaign.target_roles if r not in certified_roles]

    def auto_revoke_expired(
        self,
        campaign_id: str
    ) -> List[CertificationDecision]:
        """
        Auto-revoke uncertified items after campaign expiry.

        Args:
            campaign_id: Campaign ID

        Returns:
            List of auto-revocation decisions
        """
        campaign = self._campaigns.get(campaign_id)
        if not campaign or not campaign.auto_revoke_on_expiry:
            return []

        if not campaign.due_date or datetime.now() < campaign.due_date:
            return []

        overdue = self.get_overdue_items(campaign_id)
        decisions = []

        for role_id in overdue:
            self._decision_counter += 1
            decision = CertificationDecision(
                decision_id=f"DEC-AUTO-{self._decision_counter}",
                campaign_id=campaign_id,
                role_id=role_id,
                decision=DecisionType.REVOKE,
                comments="Auto-revoked: certification not completed by due date",
                justification="Campaign expiry auto-revocation policy",
                decided_by="SYSTEM",
                decided_at=datetime.now(),
                actions_required=["Remove role - certification expired"],
            )
            campaign.decisions.append(decision)
            campaign.revoked_count += 1
            campaign.pending_count -= 1
            decisions.append(decision)

        return decisions

    def get_certification_summary(
        self,
        campaign_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get certification summary statistics."""
        if campaign_id:
            campaigns = [self._campaigns.get(campaign_id)]
            campaigns = [c for c in campaigns if c]
        else:
            campaigns = list(self._campaigns.values())

        total_items = sum(c.total_items for c in campaigns)
        certified = sum(c.certified_count for c in campaigns)
        revoked = sum(c.revoked_count for c in campaigns)
        pending = sum(c.pending_count for c in campaigns)

        # Recommendation follow rate
        all_decisions = []
        for c in campaigns:
            all_decisions.extend(c.decisions)

        followed = sum(1 for d in all_decisions if d.followed_recommendation)
        follow_rate = followed / len(all_decisions) if all_decisions else 0

        return {
            "total_campaigns": len(campaigns),
            "total_items": total_items,
            "certified": certified,
            "revoked": revoked,
            "pending": pending,
            "completion_rate": (certified + revoked) / max(total_items, 1) * 100,
            "certification_rate": certified / max(certified + revoked, 1) * 100,
            "recommendation_follow_rate": follow_rate * 100,
        }
