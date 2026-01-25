# Auto-Approval Engine
# Risk-based decision making for access requests

"""
Auto-Approval Engine for GOVERNEX+.

Provides risk-adaptive approval decisions:
- Auto-approve low-risk requests
- Route moderate requests to appropriate approvers
- Deny and escalate high-risk requests

All decisions are auditable and policy-driven.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class ApprovalDecision(Enum):
    """Possible approval decisions."""
    AUTO_APPROVE = "AUTO_APPROVE"
    MANAGER_APPROVAL = "MANAGER_APPROVAL"
    SECURITY_APPROVAL = "SECURITY_APPROVAL"
    DUAL_APPROVAL = "DUAL_APPROVAL"  # Manager + Security
    DENY = "DENY"
    ESCALATE = "ESCALATE"


class ApprovalLevel(Enum):
    """Approval workflow levels."""
    NONE = "NONE"  # Auto-approved
    L1_MANAGER = "L1_MANAGER"
    L2_SECURITY = "L2_SECURITY"
    L3_EXECUTIVE = "L3_EXECUTIVE"
    MULTI_LEVEL = "MULTI_LEVEL"


@dataclass
class ApprovalConfig:
    """Configuration for approval thresholds."""
    # Risk score thresholds
    auto_approve_max: int = 20
    manager_approval_max: int = 50
    security_approval_max: int = 80
    # Above security_approval_max -> DENY

    # Override settings
    allow_override: bool = True
    override_requires_justification: bool = True
    override_requires_dual_approval: bool = True

    # Special handling
    sensitive_roles_require_security: bool = True
    firefighter_auto_approve: bool = False

    # SLA settings (hours)
    auto_approval_sla: int = 0
    manager_approval_sla: int = 24
    security_approval_sla: int = 48

    # Expiry settings
    temp_access_max_days: int = 30
    require_expiry_for_high_risk: bool = True


@dataclass
class ApprovalRequest:
    """An access request requiring approval decision."""
    request_id: str
    user_id: str
    requested_access: List[str]  # Roles, tcodes, or entitlements

    # Risk analysis results
    risk_score: int = 0
    risk_category: str = ""
    sod_conflicts: List[str] = field(default_factory=list)
    sensitive_access: bool = False

    # Context
    justification: str = ""
    requested_by: str = ""
    target_system: str = ""
    requested_duration: Optional[int] = None  # Days, None = permanent

    # Additional flags
    is_emergency: bool = False
    is_temporary: bool = False
    is_firefighter: bool = False

    # Timestamps
    requested_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "user_id": self.user_id,
            "requested_access": self.requested_access,
            "risk_score": self.risk_score,
            "risk_category": self.risk_category,
            "sod_conflicts": self.sod_conflicts,
            "sensitive_access": self.sensitive_access,
            "justification": self.justification,
            "requested_by": self.requested_by,
            "target_system": self.target_system,
            "requested_duration": self.requested_duration,
            "is_emergency": self.is_emergency,
            "is_temporary": self.is_temporary,
            "is_firefighter": self.is_firefighter,
            "requested_at": self.requested_at.isoformat(),
        }


@dataclass
class ApprovalResult:
    """Result of an approval decision."""
    request_id: str
    decision: ApprovalDecision
    approval_level: ApprovalLevel
    risk_score: int

    # Decision details
    reason: str
    conditions: List[str] = field(default_factory=list)  # Conditions for approval

    # Routing
    approvers: List[str] = field(default_factory=list)
    escalation_path: List[str] = field(default_factory=list)

    # SLA
    sla_hours: int = 0
    due_by: Optional[datetime] = None

    # Audit
    decided_at: datetime = field(default_factory=datetime.now)
    policy_applied: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "decision": self.decision.value,
            "approval_level": self.approval_level.value,
            "risk_score": self.risk_score,
            "reason": self.reason,
            "conditions": self.conditions,
            "approvers": self.approvers,
            "escalation_path": self.escalation_path,
            "sla_hours": self.sla_hours,
            "due_by": self.due_by.isoformat() if self.due_by else None,
            "decided_at": self.decided_at.isoformat(),
            "policy_applied": self.policy_applied,
        }


class AutoApprovalEngine:
    """
    Risk-based auto-approval engine.

    Makes approval decisions based on:
    - Risk score
    - SoD conflicts
    - Sensitive access flags
    - Request context
    - Policy rules

    All decisions are auditable and configurable.
    """

    def __init__(self, config: Optional[ApprovalConfig] = None):
        """
        Initialize approval engine.

        Args:
            config: Approval configuration
        """
        self.config = config or ApprovalConfig()

        # Custom decision hooks
        self._pre_decision_hooks: List[Callable[[ApprovalRequest], Optional[ApprovalResult]]] = []
        self._post_decision_hooks: List[Callable[[ApprovalRequest, ApprovalResult], None]] = []

    def decide(self, request: ApprovalRequest) -> ApprovalResult:
        """
        Make approval decision for a request.

        Args:
            request: Access request to evaluate

        Returns:
            ApprovalResult with decision and routing
        """
        # Run pre-decision hooks (can override decision)
        for hook in self._pre_decision_hooks:
            result = hook(request)
            if result:
                self._run_post_hooks(request, result)
                return result

        # Core decision logic
        result = self._evaluate_request(request)

        # Run post-decision hooks
        self._run_post_hooks(request, result)

        return result

    def _evaluate_request(self, request: ApprovalRequest) -> ApprovalResult:
        """Core decision logic."""
        risk_score = request.risk_score

        # Check for immediate denial conditions
        if self._should_deny(request):
            return self._create_denial(request)

        # Check for auto-approval
        if self._can_auto_approve(request):
            return self._create_auto_approval(request)

        # Determine approval level based on risk
        if risk_score <= self.config.manager_approval_max:
            return self._create_manager_approval(request)

        if risk_score <= self.config.security_approval_max:
            return self._create_security_approval(request)

        # High risk - deny by default
        return self._create_denial(request)

    def _should_deny(self, request: ApprovalRequest) -> bool:
        """Check if request should be denied outright."""
        # Critical SoD conflicts
        if len(request.sod_conflicts) > 3:
            return True

        # Extremely high risk
        if request.risk_score > 95:
            return True

        return False

    def _can_auto_approve(self, request: ApprovalRequest) -> bool:
        """Check if request qualifies for auto-approval."""
        # Risk score check
        if request.risk_score > self.config.auto_approve_max:
            return False

        # No SoD conflicts
        if request.sod_conflicts:
            return False

        # No sensitive access
        if request.sensitive_access and self.config.sensitive_roles_require_security:
            return False

        # Firefighter access check
        if request.is_firefighter and not self.config.firefighter_auto_approve:
            return False

        return True

    def _create_auto_approval(self, request: ApprovalRequest) -> ApprovalResult:
        """Create auto-approval result."""
        return ApprovalResult(
            request_id=request.request_id,
            decision=ApprovalDecision.AUTO_APPROVE,
            approval_level=ApprovalLevel.NONE,
            risk_score=request.risk_score,
            reason="Low risk access request automatically approved",
            sla_hours=self.config.auto_approval_sla,
            policy_applied="AUTO_APPROVE_LOW_RISK",
        )

    def _create_manager_approval(self, request: ApprovalRequest) -> ApprovalResult:
        """Create manager approval result."""
        conditions = []

        if request.is_temporary or self.config.require_expiry_for_high_risk:
            conditions.append(
                f"Access expires in {request.requested_duration or 30} days"
            )

        if request.sod_conflicts:
            conditions.append("Mitigating control required for SoD conflicts")

        from datetime import timedelta
        due_by = datetime.now() + timedelta(hours=self.config.manager_approval_sla)

        return ApprovalResult(
            request_id=request.request_id,
            decision=ApprovalDecision.MANAGER_APPROVAL,
            approval_level=ApprovalLevel.L1_MANAGER,
            risk_score=request.risk_score,
            reason="Moderate risk - manager approval required",
            conditions=conditions,
            approvers=[f"manager_of_{request.user_id}"],
            sla_hours=self.config.manager_approval_sla,
            due_by=due_by,
            policy_applied="MANAGER_APPROVAL_MODERATE_RISK",
        )

    def _create_security_approval(self, request: ApprovalRequest) -> ApprovalResult:
        """Create security approval result."""
        conditions = [
            "Security review required",
            "Business justification must be documented",
        ]

        if request.sod_conflicts:
            conditions.append(
                f"Mitigating control required for {len(request.sod_conflicts)} SoD conflicts"
            )

        if request.sensitive_access:
            conditions.append("Sensitive access logging will be enabled")

        from datetime import timedelta
        due_by = datetime.now() + timedelta(hours=self.config.security_approval_sla)

        # Determine if dual approval needed
        if request.risk_score > 70 or len(request.sod_conflicts) > 1:
            decision = ApprovalDecision.DUAL_APPROVAL
            approval_level = ApprovalLevel.MULTI_LEVEL
            approvers = [
                f"manager_of_{request.user_id}",
                "security_team",
            ]
            reason = "High risk - dual approval required (manager + security)"
        else:
            decision = ApprovalDecision.SECURITY_APPROVAL
            approval_level = ApprovalLevel.L2_SECURITY
            approvers = ["security_team"]
            reason = "Elevated risk - security approval required"

        return ApprovalResult(
            request_id=request.request_id,
            decision=decision,
            approval_level=approval_level,
            risk_score=request.risk_score,
            reason=reason,
            conditions=conditions,
            approvers=approvers,
            escalation_path=["security_manager", "ciso"],
            sla_hours=self.config.security_approval_sla,
            due_by=due_by,
            policy_applied="SECURITY_APPROVAL_HIGH_RISK",
        )

    def _create_denial(self, request: ApprovalRequest) -> ApprovalResult:
        """Create denial result."""
        reasons = ["Risk exceeds acceptable threshold"]

        if len(request.sod_conflicts) > 3:
            reasons.append(f"Too many SoD conflicts ({len(request.sod_conflicts)})")

        if request.risk_score > 95:
            reasons.append("Critical risk level detected")

        return ApprovalResult(
            request_id=request.request_id,
            decision=ApprovalDecision.DENY,
            approval_level=ApprovalLevel.NONE,
            risk_score=request.risk_score,
            reason="; ".join(reasons),
            conditions=[
                "Request denied - escalation required for override",
                "Contact security team for alternatives",
            ],
            escalation_path=["security_manager", "ciso"],
            policy_applied="DENY_CRITICAL_RISK",
        )

    def _run_post_hooks(
        self,
        request: ApprovalRequest,
        result: ApprovalResult
    ):
        """Run post-decision hooks."""
        for hook in self._post_decision_hooks:
            try:
                hook(request, result)
            except Exception as e:
                logger.error(f"Post-decision hook failed: {e}")

    def add_pre_decision_hook(
        self,
        hook: Callable[[ApprovalRequest], Optional[ApprovalResult]]
    ):
        """Add a pre-decision hook (can override decision)."""
        self._pre_decision_hooks.append(hook)

    def add_post_decision_hook(
        self,
        hook: Callable[[ApprovalRequest, ApprovalResult], None]
    ):
        """Add a post-decision hook (for logging, notifications, etc.)."""
        self._post_decision_hooks.append(hook)

    def simulate_decision(
        self,
        user_id: str,
        requested_access: List[str],
        risk_score: int,
        sod_conflicts: Optional[List[str]] = None,
        sensitive_access: bool = False
    ) -> ApprovalResult:
        """
        Simulate an approval decision without creating a real request.

        Useful for pre-provisioning checks.
        """
        request = ApprovalRequest(
            request_id=f"SIM-{user_id}-{datetime.now().timestamp()}",
            user_id=user_id,
            requested_access=requested_access,
            risk_score=risk_score,
            sod_conflicts=sod_conflicts or [],
            sensitive_access=sensitive_access,
        )
        return self.decide(request)

    def get_decision_summary(self) -> Dict[str, Any]:
        """Get summary of decision thresholds."""
        return {
            "thresholds": {
                "auto_approve_max": self.config.auto_approve_max,
                "manager_approval_max": self.config.manager_approval_max,
                "security_approval_max": self.config.security_approval_max,
            },
            "sla_hours": {
                "auto_approval": self.config.auto_approval_sla,
                "manager_approval": self.config.manager_approval_sla,
                "security_approval": self.config.security_approval_sla,
            },
            "special_handling": {
                "sensitive_roles_require_security": self.config.sensitive_roles_require_security,
                "firefighter_auto_approve": self.config.firefighter_auto_approve,
            },
        }
