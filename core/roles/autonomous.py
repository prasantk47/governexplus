# Autonomous Role Management
# Self-healing access model with automatic cleanup

"""
Autonomous Role Management for GOVERNEX+.

Features:
- Risk-based role assignment
- Autonomous role revocation
- Just-Enough-Access (JEA) policies
- Self-healing access model
"""

from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional, Any, Callable
from datetime import datetime, timedelta
from enum import Enum
import logging

from .models import Role, RoleType

logger = logging.getLogger(__name__)


class CleanupActionType(Enum):
    """Types of cleanup actions."""
    REVOKE_ROLE = "REVOKE_ROLE"
    REVOKE_PERMISSION = "REVOKE_PERMISSION"
    DEPRECATE_ROLE = "DEPRECATE_ROLE"
    EXPIRE_ASSIGNMENT = "EXPIRE_ASSIGNMENT"
    REDUCE_PRIVILEGES = "REDUCE_PRIVILEGES"


class AssignmentBasis(Enum):
    """Basis for role assignment recommendation."""
    JOB_FUNCTION = "JOB_FUNCTION"
    PEER_COMPARISON = "PEER_COMPARISON"
    USAGE_PATTERN = "USAGE_PATTERN"
    RISK_OPTIMIZATION = "RISK_OPTIMIZATION"


@dataclass
class JEAPolicy:
    """
    Just-Enough-Access policy definition.

    Defines context-based access rules that adapt to:
    - Time
    - Location
    - Device
    - Risk level
    """
    policy_id: str
    name: str
    description: str

    # Context conditions
    allowed_hours: Optional[tuple[int, int]] = None  # (start, end) hours
    allowed_days: Optional[List[int]] = None  # 0=Monday, 6=Sunday
    allowed_locations: Optional[List[str]] = None
    require_trusted_device: bool = False

    # Risk conditions
    max_user_risk_score: int = 80
    max_role_risk_score: int = 70

    # Access limits
    max_concurrent_sessions: int = 1
    session_timeout_minutes: int = 480  # 8 hours

    # Auto-expiry
    auto_expire_days: Optional[int] = None
    require_revalidation_days: Optional[int] = 30

    def to_dict(self) -> Dict[str, Any]:
        return {
            "policy_id": self.policy_id,
            "name": self.name,
            "description": self.description,
            "allowed_hours": self.allowed_hours,
            "allowed_days": self.allowed_days,
            "allowed_locations": self.allowed_locations,
            "require_trusted_device": self.require_trusted_device,
            "max_user_risk_score": self.max_user_risk_score,
            "max_role_risk_score": self.max_role_risk_score,
            "session_timeout_minutes": self.session_timeout_minutes,
            "auto_expire_days": self.auto_expire_days,
        }


@dataclass
class RevocationCandidate:
    """
    A role/user combination flagged for revocation.

    Includes evidence and rollback capability.
    """
    candidate_id: str
    user_id: str
    role_id: str
    role_name: str

    # Reason
    revocation_reason: str
    evidence: List[str] = field(default_factory=list)
    risk_score: float = 0.0

    # Classification
    urgency: str = "MEDIUM"  # LOW, MEDIUM, HIGH, CRITICAL
    auto_revoke: bool = False

    # Rollback
    allow_rollback: bool = True
    rollback_window_days: int = 7

    # Status
    status: str = "PENDING"  # PENDING, APPROVED, EXECUTED, ROLLED_BACK
    approved_by: Optional[str] = None
    executed_at: Optional[datetime] = None

    # Timestamps
    identified_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "user_id": self.user_id,
            "role_id": self.role_id,
            "role_name": self.role_name,
            "revocation_reason": self.revocation_reason,
            "evidence": self.evidence,
            "risk_score": round(self.risk_score, 2),
            "urgency": self.urgency,
            "auto_revoke": self.auto_revoke,
            "status": self.status,
            "identified_at": self.identified_at.isoformat(),
        }


@dataclass
class AssignmentRecommendation:
    """
    Recommendation for role assignment.

    Context-aware and risk-optimized.
    """
    recommendation_id: str
    user_id: str
    role_id: str
    role_name: str

    # Recommendation basis
    basis: AssignmentBasis = AssignmentBasis.JOB_FUNCTION
    confidence: float = 0.0  # 0-1
    rationale: str = ""

    # Context
    job_function_match: bool = False
    peer_similarity: float = 0.0
    usage_alignment: float = 0.0

    # Risk assessment
    predicted_risk_increase: float = 0.0
    sod_conflicts_introduced: int = 0

    # JEA policy
    recommended_jea_policy: Optional[str] = None
    recommended_duration_days: Optional[int] = None

    # Timestamps
    generated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "recommendation_id": self.recommendation_id,
            "user_id": self.user_id,
            "role_id": self.role_id,
            "role_name": self.role_name,
            "basis": self.basis.value,
            "confidence": round(self.confidence, 4),
            "rationale": self.rationale,
            "predicted_risk_increase": round(self.predicted_risk_increase, 2),
            "sod_conflicts_introduced": self.sod_conflicts_introduced,
            "recommended_jea_policy": self.recommended_jea_policy,
            "recommended_duration_days": self.recommended_duration_days,
            "generated_at": self.generated_at.isoformat(),
        }


@dataclass
class CleanupAction:
    """
    An automated cleanup action.

    Represents an action taken by the autonomous manager.
    """
    action_id: str
    action_type: CleanupActionType
    target_role_id: str
    target_user_id: Optional[str] = None

    # Details
    description: str = ""
    reason: str = ""
    evidence: List[str] = field(default_factory=list)

    # Impact
    risk_reduction: float = 0.0
    users_affected: int = 0

    # Status
    status: str = "PROPOSED"  # PROPOSED, APPROVED, EXECUTED, FAILED, REVERTED
    executed_at: Optional[datetime] = None
    executed_by: Optional[str] = None

    # Audit
    created_at: datetime = field(default_factory=datetime.now)
    approval_required: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action_id": self.action_id,
            "action_type": self.action_type.value,
            "target_role_id": self.target_role_id,
            "target_user_id": self.target_user_id,
            "description": self.description,
            "reason": self.reason,
            "evidence": self.evidence,
            "risk_reduction": round(self.risk_reduction, 2),
            "users_affected": self.users_affected,
            "status": self.status,
            "approval_required": self.approval_required,
            "created_at": self.created_at.isoformat(),
        }


class AutonomousRoleManager:
    """
    Autonomous role management engine.

    Key capabilities:
    - Identify unused/high-risk role assignments
    - Recommend revocations
    - Execute approved cleanups
    - Provide rollback capability
    """

    # Thresholds
    UNUSED_DAYS_THRESHOLD = 90
    HIGH_RISK_THRESHOLD = 80
    AUTO_REVOKE_RISK_THRESHOLD = 95

    def __init__(self):
        """Initialize autonomous manager."""
        self._action_counter = 0
        self._revocation_candidates: List[RevocationCandidate] = []
        self._cleanup_actions: List[CleanupAction] = []
        self._jea_policies: Dict[str, JEAPolicy] = {}

        # Callbacks
        self._on_revocation: Optional[Callable] = None
        self._on_cleanup: Optional[Callable] = None

    def register_jea_policy(self, policy: JEAPolicy):
        """Register a JEA policy."""
        self._jea_policies[policy.policy_id] = policy

    def analyze_for_revocation(
        self,
        user_id: str,
        role: Role,
        usage_data: Dict[str, Any],
        user_risk_score: float = 0
    ) -> Optional[RevocationCandidate]:
        """
        Analyze if a role assignment should be revoked.

        Args:
            user_id: User identifier
            role: Assigned role
            usage_data: Role usage data for this user
            user_risk_score: User's current risk score

        Returns:
            RevocationCandidate if revocation recommended
        """
        reasons = []
        evidence = []
        risk_score = 0

        # Check unused
        days_since_use = usage_data.get("days_since_last_use", 0)
        if days_since_use > self.UNUSED_DAYS_THRESHOLD:
            reasons.append("unused_access")
            evidence.append(f"Role not used in {days_since_use} days")
            risk_score += 20

        # Check role risk
        role_risk = usage_data.get("role_risk_score", 0)
        if role_risk > self.HIGH_RISK_THRESHOLD:
            reasons.append("high_risk_role")
            evidence.append(f"Role risk score: {role_risk}")
            risk_score += role_risk * 0.3

        # Check user risk
        if user_risk_score > self.HIGH_RISK_THRESHOLD:
            reasons.append("high_risk_user")
            evidence.append(f"User risk score: {user_risk_score}")
            risk_score += user_risk_score * 0.2

        # Check usage anomalies
        anomaly_score = usage_data.get("anomaly_score", 0)
        if anomaly_score > 0.7:
            reasons.append("anomalous_usage")
            evidence.append(f"Usage anomaly detected (score: {anomaly_score:.2f})")
            risk_score += 30

        if not reasons:
            return None

        self._action_counter += 1
        candidate = RevocationCandidate(
            candidate_id=f"REV-{user_id}-{role.role_id}-{self._action_counter}",
            user_id=user_id,
            role_id=role.role_id,
            role_name=role.role_name,
            revocation_reason=", ".join(reasons),
            evidence=evidence,
            risk_score=min(100, risk_score),
        )

        # Determine urgency
        if risk_score > self.AUTO_REVOKE_RISK_THRESHOLD:
            candidate.urgency = "CRITICAL"
            candidate.auto_revoke = True
        elif risk_score > self.HIGH_RISK_THRESHOLD:
            candidate.urgency = "HIGH"
        elif risk_score > 50:
            candidate.urgency = "MEDIUM"
        else:
            candidate.urgency = "LOW"

        self._revocation_candidates.append(candidate)
        return candidate

    def recommend_assignments(
        self,
        user_id: str,
        job_function: str,
        current_roles: List[Role],
        available_roles: List[Role],
        peer_roles: Optional[Dict[str, Set[str]]] = None
    ) -> List[AssignmentRecommendation]:
        """
        Recommend role assignments for a user.

        Args:
            user_id: User identifier
            job_function: User's job function
            current_roles: User's current roles
            available_roles: Roles available for assignment
            peer_roles: Roles assigned to similar users

        Returns:
            List of assignment recommendations
        """
        recommendations = []
        current_role_ids = {r.role_id for r in current_roles}
        peer_roles = peer_roles or {}

        for role in available_roles:
            if role.role_id in current_role_ids:
                continue

            # Calculate match scores
            job_match = self._check_job_match(role, job_function)
            peer_sim = self._calculate_peer_similarity(role.role_id, peer_roles)

            # Skip if no match
            if not job_match and peer_sim < 0.3:
                continue

            self._action_counter += 1
            rec = AssignmentRecommendation(
                recommendation_id=f"ASSIGN-{user_id}-{role.role_id}-{self._action_counter}",
                user_id=user_id,
                role_id=role.role_id,
                role_name=role.role_name,
                job_function_match=job_match,
                peer_similarity=peer_sim,
            )

            # Determine basis and confidence
            if job_match and peer_sim > 0.5:
                rec.basis = AssignmentBasis.JOB_FUNCTION
                rec.confidence = 0.9
                rec.rationale = "Matches job function and peer assignments"
            elif job_match:
                rec.basis = AssignmentBasis.JOB_FUNCTION
                rec.confidence = 0.7
                rec.rationale = "Matches job function"
            elif peer_sim > 0.5:
                rec.basis = AssignmentBasis.PEER_COMPARISON
                rec.confidence = peer_sim
                rec.rationale = f"{peer_sim:.0%} of similar users have this role"

            # Get appropriate JEA policy
            rec.recommended_jea_policy = self._get_recommended_jea(role)

            recommendations.append(rec)

        # Sort by confidence
        recommendations.sort(key=lambda r: r.confidence, reverse=True)

        return recommendations[:10]  # Top 10

    def _check_job_match(self, role: Role, job_function: str) -> bool:
        """Check if role matches job function."""
        if not role.metadata:
            return False

        role_function = role.metadata.job_function.lower()
        job_function = job_function.lower()

        return (
            job_function in role_function or
            role_function in job_function or
            role.metadata.business_process.lower() in job_function
        )

    def _calculate_peer_similarity(
        self,
        role_id: str,
        peer_roles: Dict[str, Set[str]]
    ) -> float:
        """Calculate what percentage of peers have this role."""
        if not peer_roles:
            return 0

        peers_with_role = sum(
            1 for roles in peer_roles.values()
            if role_id in roles
        )

        return peers_with_role / len(peer_roles)

    def _get_recommended_jea(self, role: Role) -> Optional[str]:
        """Get recommended JEA policy for a role."""
        # High-risk roles get restricted policies
        if role.metadata and role.metadata.risk_rating in ["HIGH", "CRITICAL"]:
            for policy_id, policy in self._jea_policies.items():
                if policy.require_trusted_device or policy.allowed_hours:
                    return policy_id

        return None

    def generate_cleanup_actions(
        self,
        roles: List[Role],
        usage_data: Dict[str, Dict[str, Any]]
    ) -> List[CleanupAction]:
        """
        Generate cleanup actions for the role portfolio.

        Args:
            roles: List of roles to analyze
            usage_data: Usage data per role

        Returns:
            List of proposed cleanup actions
        """
        actions = []

        for role in roles:
            role_usage = usage_data.get(role.role_id, {})

            # Check for deprecation candidates
            if role.assignment_count == 0:
                self._action_counter += 1
                actions.append(CleanupAction(
                    action_id=f"CLEANUP-{self._action_counter}",
                    action_type=CleanupActionType.DEPRECATE_ROLE,
                    target_role_id=role.role_id,
                    description=f"Deprecate unused role '{role.role_name}'",
                    reason="No users assigned",
                    evidence=["Assignment count: 0"],
                    users_affected=0,
                ))

            # Check for privilege reduction
            unused_ratio = role_usage.get("unused_permissions_ratio", 0)
            if unused_ratio > 0.5:
                self._action_counter += 1
                actions.append(CleanupAction(
                    action_id=f"CLEANUP-{self._action_counter}",
                    action_type=CleanupActionType.REDUCE_PRIVILEGES,
                    target_role_id=role.role_id,
                    description=f"Remove unused permissions from '{role.role_name}'",
                    reason=f"{unused_ratio:.0%} of permissions never used",
                    evidence=[f"Unused permission ratio: {unused_ratio:.0%}"],
                    users_affected=role.assignment_count,
                    risk_reduction=unused_ratio * 20,
                ))

        self._cleanup_actions.extend(actions)
        return actions

    def execute_revocation(
        self,
        candidate: RevocationCandidate,
        executed_by: str
    ) -> bool:
        """
        Execute a role revocation.

        Args:
            candidate: Revocation candidate to execute
            executed_by: User executing the revocation

        Returns:
            True if successful
        """
        candidate.status = "EXECUTED"
        candidate.executed_at = datetime.now()

        logger.info(
            f"Revoked role {candidate.role_id} from user {candidate.user_id} "
            f"by {executed_by}: {candidate.revocation_reason}"
        )

        if self._on_revocation:
            self._on_revocation(candidate)

        return True

    def rollback_revocation(
        self,
        candidate_id: str,
        reason: str
    ) -> bool:
        """
        Rollback a revocation within the rollback window.

        Args:
            candidate_id: ID of revocation to rollback
            reason: Reason for rollback

        Returns:
            True if successful
        """
        for candidate in self._revocation_candidates:
            if candidate.candidate_id == candidate_id:
                if candidate.status != "EXECUTED":
                    return False

                if not candidate.allow_rollback:
                    return False

                # Check rollback window
                if candidate.executed_at:
                    days_since = (datetime.now() - candidate.executed_at).days
                    if days_since > candidate.rollback_window_days:
                        return False

                candidate.status = "ROLLED_BACK"
                logger.info(f"Rolled back revocation {candidate_id}: {reason}")
                return True

        return False

    def get_pending_candidates(self) -> List[RevocationCandidate]:
        """Get pending revocation candidates."""
        return [c for c in self._revocation_candidates if c.status == "PENDING"]

    def get_pending_actions(self) -> List[CleanupAction]:
        """Get pending cleanup actions."""
        return [a for a in self._cleanup_actions if a.status == "PROPOSED"]

    def set_revocation_callback(self, callback: Callable):
        """Set callback for revocation events."""
        self._on_revocation = callback

    def set_cleanup_callback(self, callback: Callable):
        """Set callback for cleanup events."""
        self._on_cleanup = callback
