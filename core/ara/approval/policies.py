# Approval Policies
# Policy-as-code for approval workflows

"""
Policy Engine for Approval Workflows.

Allows defining complex approval policies as code/configuration.
Policies can be loaded from YAML or defined programmatically.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable, Union
from datetime import datetime
from enum import Enum
import logging
import operator

logger = logging.getLogger(__name__)


class PolicyOperator(Enum):
    """Operators for policy conditions."""
    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"
    GREATER_EQUAL = "greater_equal"
    LESS_EQUAL = "less_equal"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    IN = "in"
    NOT_IN = "not_in"
    MATCHES = "matches"  # Regex


class PolicyAction(Enum):
    """Actions a policy can take."""
    APPROVE = "APPROVE"
    DENY = "DENY"
    REQUIRE_MANAGER = "REQUIRE_MANAGER"
    REQUIRE_SECURITY = "REQUIRE_SECURITY"
    REQUIRE_DUAL = "REQUIRE_DUAL"
    ESCALATE = "ESCALATE"
    ADD_CONDITION = "ADD_CONDITION"
    SET_EXPIRY = "SET_EXPIRY"


@dataclass
class PolicyCondition:
    """A single condition in a policy."""
    field: str  # Field to evaluate (e.g., "risk_score", "user.department")
    operator: PolicyOperator
    value: Any

    def evaluate(self, context: Dict[str, Any]) -> bool:
        """Evaluate condition against context."""
        actual_value = self._get_field_value(context)

        op_map = {
            PolicyOperator.EQUALS: operator.eq,
            PolicyOperator.NOT_EQUALS: operator.ne,
            PolicyOperator.GREATER_THAN: operator.gt,
            PolicyOperator.LESS_THAN: operator.lt,
            PolicyOperator.GREATER_EQUAL: operator.ge,
            PolicyOperator.LESS_EQUAL: operator.le,
        }

        if self.operator in op_map:
            return op_map[self.operator](actual_value, self.value)

        if self.operator == PolicyOperator.CONTAINS:
            return self.value in actual_value if actual_value else False

        if self.operator == PolicyOperator.NOT_CONTAINS:
            return self.value not in actual_value if actual_value else True

        if self.operator == PolicyOperator.IN:
            return actual_value in self.value if self.value else False

        if self.operator == PolicyOperator.NOT_IN:
            return actual_value not in self.value if self.value else True

        if self.operator == PolicyOperator.MATCHES:
            import re
            return bool(re.match(self.value, str(actual_value)))

        return False

    def _get_field_value(self, context: Dict[str, Any]) -> Any:
        """Get field value from context, supporting dot notation."""
        parts = self.field.split(".")
        value = context

        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            elif hasattr(value, part):
                value = getattr(value, part)
            else:
                return None

        return value

    def to_dict(self) -> Dict[str, Any]:
        return {
            "field": self.field,
            "operator": self.operator.value,
            "value": self.value,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PolicyCondition":
        return cls(
            field=data["field"],
            operator=PolicyOperator(data["operator"]),
            value=data["value"],
        )


@dataclass
class ApprovalPolicy:
    """
    An approval policy definition.

    Policies are evaluated in priority order. First matching
    policy determines the action.
    """
    policy_id: str
    name: str
    description: str
    priority: int = 100  # Lower = higher priority

    # Conditions (all must match)
    conditions: List[PolicyCondition] = field(default_factory=list)

    # Action to take
    action: PolicyAction = PolicyAction.REQUIRE_MANAGER
    action_params: Dict[str, Any] = field(default_factory=dict)

    # Additional requirements
    required_approvers: List[str] = field(default_factory=list)
    approval_conditions: List[str] = field(default_factory=list)  # Text conditions

    # Metadata
    is_active: bool = True
    effective_from: Optional[datetime] = None
    effective_to: Optional[datetime] = None
    created_by: str = "SYSTEM"

    def matches(self, context: Dict[str, Any]) -> bool:
        """Check if all conditions match."""
        if not self.is_active:
            return False

        # Check effective dates
        now = datetime.now()
        if self.effective_from and now < self.effective_from:
            return False
        if self.effective_to and now > self.effective_to:
            return False

        # All conditions must match
        return all(c.evaluate(context) for c in self.conditions)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "policy_id": self.policy_id,
            "name": self.name,
            "description": self.description,
            "priority": self.priority,
            "conditions": [c.to_dict() for c in self.conditions],
            "action": self.action.value,
            "action_params": self.action_params,
            "required_approvers": self.required_approvers,
            "approval_conditions": self.approval_conditions,
            "is_active": self.is_active,
            "effective_from": self.effective_from.isoformat() if self.effective_from else None,
            "effective_to": self.effective_to.isoformat() if self.effective_to else None,
            "created_by": self.created_by,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ApprovalPolicy":
        conditions = [
            PolicyCondition.from_dict(c)
            for c in data.get("conditions", [])
        ]
        return cls(
            policy_id=data["policy_id"],
            name=data["name"],
            description=data.get("description", ""),
            priority=data.get("priority", 100),
            conditions=conditions,
            action=PolicyAction(data.get("action", "REQUIRE_MANAGER")),
            action_params=data.get("action_params", {}),
            required_approvers=data.get("required_approvers", []),
            approval_conditions=data.get("approval_conditions", []),
            is_active=data.get("is_active", True),
            effective_from=datetime.fromisoformat(data["effective_from"]) if data.get("effective_from") else None,
            effective_to=datetime.fromisoformat(data["effective_to"]) if data.get("effective_to") else None,
            created_by=data.get("created_by", "SYSTEM"),
        )


# Built-in policies
BUILTIN_POLICIES = [
    ApprovalPolicy(
        policy_id="POLICY-EMERGENCY-APPROVE",
        name="Emergency Access Auto-Approve",
        description="Auto-approve emergency access with logging",
        priority=10,
        conditions=[
            PolicyCondition("is_emergency", PolicyOperator.EQUALS, True),
            PolicyCondition("risk_score", PolicyOperator.LESS_EQUAL, 60),
        ],
        action=PolicyAction.APPROVE,
        action_params={"log_level": "HIGH", "notify": ["security_team"]},
        approval_conditions=["Access expires in 24 hours", "Enhanced logging enabled"],
    ),
    ApprovalPolicy(
        policy_id="POLICY-FIREFIGHTER-SECURITY",
        name="Firefighter Access Security Review",
        description="Firefighter access requires security approval",
        priority=20,
        conditions=[
            PolicyCondition("is_firefighter", PolicyOperator.EQUALS, True),
        ],
        action=PolicyAction.REQUIRE_SECURITY,
        required_approvers=["security_team"],
        approval_conditions=["Session recording enabled", "Maximum 8 hour duration"],
    ),
    ApprovalPolicy(
        policy_id="POLICY-HIGH-RISK-DENY",
        name="Critical Risk Denial",
        description="Deny requests with critical risk scores",
        priority=5,
        conditions=[
            PolicyCondition("risk_score", PolicyOperator.GREATER_THAN, 90),
        ],
        action=PolicyAction.DENY,
        action_params={"reason": "Risk score exceeds maximum threshold"},
    ),
    ApprovalPolicy(
        policy_id="POLICY-SOD-DUAL",
        name="SoD Conflict Dual Approval",
        description="SoD conflicts require dual approval",
        priority=30,
        conditions=[
            PolicyCondition("sod_conflict_count", PolicyOperator.GREATER_THAN, 0),
        ],
        action=PolicyAction.REQUIRE_DUAL,
        required_approvers=["manager", "security_team"],
        approval_conditions=["Mitigating control must be applied"],
    ),
    ApprovalPolicy(
        policy_id="POLICY-SENSITIVE-SECURITY",
        name="Sensitive Access Security Review",
        description="Sensitive access requires security approval",
        priority=40,
        conditions=[
            PolicyCondition("sensitive_access", PolicyOperator.EQUALS, True),
        ],
        action=PolicyAction.REQUIRE_SECURITY,
        required_approvers=["security_team"],
    ),
    ApprovalPolicy(
        policy_id="POLICY-LOW-RISK-APPROVE",
        name="Low Risk Auto-Approve",
        description="Auto-approve low risk standard access",
        priority=100,
        conditions=[
            PolicyCondition("risk_score", PolicyOperator.LESS_EQUAL, 20),
            PolicyCondition("sod_conflict_count", PolicyOperator.EQUALS, 0),
            PolicyCondition("sensitive_access", PolicyOperator.EQUALS, False),
        ],
        action=PolicyAction.APPROVE,
    ),
]


class PolicyEngine:
    """
    Policy evaluation engine.

    Evaluates approval policies against request context
    and returns the appropriate action.
    """

    def __init__(self):
        """Initialize with built-in policies."""
        self.policies: Dict[str, ApprovalPolicy] = {}
        self._load_builtin_policies()

    def _load_builtin_policies(self):
        """Load built-in policies."""
        for policy in BUILTIN_POLICIES:
            self.policies[policy.policy_id] = policy

    def add_policy(self, policy: ApprovalPolicy):
        """Add a custom policy."""
        self.policies[policy.policy_id] = policy
        logger.info(f"Added policy: {policy.policy_id}")

    def remove_policy(self, policy_id: str):
        """Remove a policy."""
        if policy_id in self.policies:
            del self.policies[policy_id]

    def evaluate(self, context: Dict[str, Any]) -> Optional[ApprovalPolicy]:
        """
        Evaluate policies against context.

        Returns the first matching policy (by priority order).
        """
        # Sort by priority (lower = higher priority)
        sorted_policies = sorted(
            self.policies.values(),
            key=lambda p: p.priority
        )

        for policy in sorted_policies:
            if policy.matches(context):
                logger.debug(f"Policy matched: {policy.policy_id}")
                return policy

        return None

    def evaluate_all(self, context: Dict[str, Any]) -> List[ApprovalPolicy]:
        """
        Evaluate all policies against context.

        Returns all matching policies.
        """
        return [
            policy for policy in self.policies.values()
            if policy.matches(context)
        ]

    def get_active_policies(self) -> List[ApprovalPolicy]:
        """Get all active policies."""
        return [p for p in self.policies.values() if p.is_active]

    def load_from_yaml(self, yaml_content: str):
        """Load policies from YAML content."""
        try:
            import yaml
            data = yaml.safe_load(yaml_content)
            for policy_data in data.get("policies", []):
                policy = ApprovalPolicy.from_dict(policy_data)
                self.policies[policy.policy_id] = policy
        except ImportError:
            logger.warning("PyYAML not available")
        except Exception as e:
            logger.error(f"Error loading policies: {e}")

    def export_to_yaml(self) -> str:
        """Export policies to YAML format."""
        try:
            import yaml
            data = {
                "policies": [p.to_dict() for p in self.policies.values()]
            }
            return yaml.dump(data, default_flow_style=False)
        except ImportError:
            logger.warning("PyYAML not available")
            return ""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize engine state."""
        return {
            "policies": [p.to_dict() for p in self.policies.values()],
            "policy_count": len(self.policies),
            "active_count": len(self.get_active_policies()),
        }
