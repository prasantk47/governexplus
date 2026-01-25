# Workflow Policy Engine
# YAML-based policy-driven workflow assembly

"""
Policy Engine for GOVERNEX+ Universal Workflow.

Replaces MSMP's static workflow configuration with:
- YAML-based policy definitions
- Human-readable rules
- Git-versioned policies
- Safe expression evaluation
- Runtime policy composition

Key Principle:
MSMP = "Follow the configured path"
GOVERNEX+ = "Assemble the safest path for THIS request"
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable, Tuple
from datetime import datetime
from enum import Enum
import re
import logging
import operator

from .models import ApproverTypeEnum, WorkflowContext

logger = logging.getLogger(__name__)


# ============================================================
# POLICY CONDITION DSL
# ============================================================

class ConditionOperator(Enum):
    """Supported condition operators."""
    EQUALS = "=="
    NOT_EQUALS = "!="
    GREATER = ">"
    GREATER_EQUAL = ">="
    LESS = "<"
    LESS_EQUAL = "<="
    IN = "in"
    NOT_IN = "not_in"
    CONTAINS = "contains"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"
    MATCHES = "matches"  # Regex
    EXISTS = "exists"
    NOT_EXISTS = "not_exists"
    IS_TRUE = "is_true"
    IS_FALSE = "is_false"


@dataclass
class PolicyCondition:
    """
    A single condition in a policy rule.

    Supports safe expression evaluation without eval().
    """
    field: str
    operator: ConditionOperator
    value: Any = None

    def evaluate(self, context: Dict[str, Any]) -> bool:
        """
        Safely evaluate this condition against context.

        No eval() - uses explicit operator mapping.
        """
        # Get field value from context (supports nested paths)
        actual = self._get_nested_value(context, self.field)

        # Apply operator
        if self.operator == ConditionOperator.EQUALS:
            return actual == self.value

        elif self.operator == ConditionOperator.NOT_EQUALS:
            return actual != self.value

        elif self.operator == ConditionOperator.GREATER:
            return actual is not None and actual > self.value

        elif self.operator == ConditionOperator.GREATER_EQUAL:
            return actual is not None and actual >= self.value

        elif self.operator == ConditionOperator.LESS:
            return actual is not None and actual < self.value

        elif self.operator == ConditionOperator.LESS_EQUAL:
            return actual is not None and actual <= self.value

        elif self.operator == ConditionOperator.IN:
            return actual in self.value if isinstance(self.value, (list, set, tuple)) else False

        elif self.operator == ConditionOperator.NOT_IN:
            return actual not in self.value if isinstance(self.value, (list, set, tuple)) else True

        elif self.operator == ConditionOperator.CONTAINS:
            return self.value in actual if isinstance(actual, (str, list)) else False

        elif self.operator == ConditionOperator.STARTS_WITH:
            return actual.startswith(self.value) if isinstance(actual, str) else False

        elif self.operator == ConditionOperator.ENDS_WITH:
            return actual.endswith(self.value) if isinstance(actual, str) else False

        elif self.operator == ConditionOperator.MATCHES:
            return bool(re.match(self.value, str(actual))) if actual else False

        elif self.operator == ConditionOperator.EXISTS:
            return actual is not None

        elif self.operator == ConditionOperator.NOT_EXISTS:
            return actual is None

        elif self.operator == ConditionOperator.IS_TRUE:
            return bool(actual) is True

        elif self.operator == ConditionOperator.IS_FALSE:
            return bool(actual) is False

        return False

    def _get_nested_value(self, obj: Dict, path: str) -> Any:
        """Get value from nested dict using dot notation."""
        keys = path.split(".")
        value = obj
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            else:
                return None
            if value is None:
                return None
        return value

    @classmethod
    def from_string(cls, expression: str) -> "PolicyCondition":
        """
        Parse condition from string expression.

        Examples:
            "risk_score > 50"
            "system == 'PROD'"
            "risk_level in ['HIGH', 'CRITICAL']"
            "is_production is_true"
        """
        expression = expression.strip()

        # Handle special operators
        if " is_true" in expression:
            field = expression.replace(" is_true", "").strip()
            return cls(field=field, operator=ConditionOperator.IS_TRUE)

        if " is_false" in expression:
            field = expression.replace(" is_false", "").strip()
            return cls(field=field, operator=ConditionOperator.IS_FALSE)

        if " exists" in expression:
            field = expression.replace(" exists", "").strip()
            return cls(field=field, operator=ConditionOperator.EXISTS)

        if " not_exists" in expression:
            field = expression.replace(" not_exists", "").strip()
            return cls(field=field, operator=ConditionOperator.NOT_EXISTS)

        # Parse comparison operators
        operators = [
            (">=", ConditionOperator.GREATER_EQUAL),
            ("<=", ConditionOperator.LESS_EQUAL),
            ("!=", ConditionOperator.NOT_EQUALS),
            ("==", ConditionOperator.EQUALS),
            (">", ConditionOperator.GREATER),
            ("<", ConditionOperator.LESS),
            (" not_in ", ConditionOperator.NOT_IN),
            (" in ", ConditionOperator.IN),
            (" contains ", ConditionOperator.CONTAINS),
            (" starts_with ", ConditionOperator.STARTS_WITH),
            (" ends_with ", ConditionOperator.ENDS_WITH),
            (" matches ", ConditionOperator.MATCHES),
        ]

        for op_str, op_enum in operators:
            if op_str in expression:
                parts = expression.split(op_str, 1)
                if len(parts) == 2:
                    field = parts[0].strip()
                    value_str = parts[1].strip()
                    value = cls._parse_value(value_str)
                    return cls(field=field, operator=op_enum, value=value)

        raise ValueError(f"Cannot parse condition: {expression}")

    @staticmethod
    def _parse_value(value_str: str) -> Any:
        """Parse string value to appropriate type."""
        value_str = value_str.strip()

        # Boolean
        if value_str.lower() == "true":
            return True
        if value_str.lower() == "false":
            return False

        # None
        if value_str.lower() == "none" or value_str.lower() == "null":
            return None

        # Number
        if value_str.isdigit():
            return int(value_str)
        try:
            return float(value_str)
        except ValueError:
            pass

        # List
        if value_str.startswith("[") and value_str.endswith("]"):
            inner = value_str[1:-1]
            items = [PolicyCondition._parse_value(i.strip()) for i in inner.split(",")]
            return items

        # String (remove quotes)
        if (value_str.startswith("'") and value_str.endswith("'")) or \
           (value_str.startswith('"') and value_str.endswith('"')):
            return value_str[1:-1]

        return value_str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "field": self.field,
            "operator": self.operator.value,
            "value": self.value,
        }


# ============================================================
# POLICY ACTION
# ============================================================

class ActionType(Enum):
    """Types of policy actions."""
    ADD_APPROVER = "ADD_APPROVER"
    REMOVE_APPROVER = "REMOVE_APPROVER"
    SET_SLA = "SET_SLA"
    AUTO_APPROVE = "AUTO_APPROVE"
    AUTO_REJECT = "AUTO_REJECT"
    REQUIRE_JUSTIFICATION = "REQUIRE_JUSTIFICATION"
    ADD_POST_REVIEW = "ADD_POST_REVIEW"
    NOTIFY = "NOTIFY"
    ESCALATE = "ESCALATE"
    SET_PRIORITY = "SET_PRIORITY"


@dataclass
class PolicyAction:
    """
    An action to take when policy rule matches.
    """
    action_type: ActionType
    approver_type: Optional[ApproverTypeEnum] = None
    approver_id: Optional[str] = None
    sla_hours: Optional[float] = None
    reason: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action_type": self.action_type.value,
            "approver_type": self.approver_type.value if self.approver_type else None,
            "approver_id": self.approver_id,
            "sla_hours": self.sla_hours,
            "reason": self.reason,
            "parameters": self.parameters,
        }


# ============================================================
# POLICY RULE
# ============================================================

@dataclass
class PolicyRule:
    """
    A single rule in the workflow policy.

    Rules are evaluated in priority order.
    Multiple rules can match and contribute steps.
    """
    rule_id: str
    name: str
    description: str = ""
    priority: int = 100  # Lower = evaluated first

    # Layer
    layer: str = "STANDARD"  # MANDATORY, RISK_ADAPTIVE, CONTEXTUAL, OPTIMIZATION

    # Conditions (all must match)
    conditions: List[PolicyCondition] = field(default_factory=list)

    # Actions (all are executed if conditions match)
    actions: List[PolicyAction] = field(default_factory=list)

    # Metadata
    is_active: bool = True
    effective_from: Optional[datetime] = None
    effective_until: Optional[datetime] = None
    tags: List[str] = field(default_factory=list)

    def matches(self, context: Dict[str, Any]) -> bool:
        """Check if all conditions match."""
        if not self.is_active:
            return False

        # Check effective dates
        now = datetime.now()
        if self.effective_from and now < self.effective_from:
            return False
        if self.effective_until and now > self.effective_until:
            return False

        # All conditions must match
        return all(cond.evaluate(context) for cond in self.conditions)

    def get_matched_conditions(self, context: Dict[str, Any]) -> List[str]:
        """Get list of conditions that matched (for explainability)."""
        return [
            f"{cond.field} {cond.operator.value} {cond.value}"
            for cond in self.conditions
            if cond.evaluate(context)
        ]

    @classmethod
    def from_yaml_dict(cls, data: Dict[str, Any]) -> "PolicyRule":
        """Create rule from YAML dictionary."""
        conditions = []
        for cond_str in data.get("when", []):
            if isinstance(cond_str, str):
                conditions.append(PolicyCondition.from_string(cond_str))
            elif isinstance(cond_str, dict):
                conditions.append(PolicyCondition(
                    field=cond_str.get("field", ""),
                    operator=ConditionOperator(cond_str.get("operator", "==")),
                    value=cond_str.get("value"),
                ))

        actions = []
        for action_data in data.get("then", []):
            if isinstance(action_data, dict):
                action_type = ActionType(action_data.get("action", "ADD_APPROVER"))
                approver_type = None
                if "approver" in action_data:
                    try:
                        approver_type = ApproverTypeEnum(action_data["approver"])
                    except ValueError:
                        approver_type = ApproverTypeEnum.CUSTOM

                actions.append(PolicyAction(
                    action_type=action_type,
                    approver_type=approver_type,
                    approver_id=action_data.get("approver_id"),
                    sla_hours=action_data.get("sla"),
                    reason=action_data.get("reason", ""),
                    parameters=action_data.get("parameters", {}),
                ))
            elif isinstance(action_data, str):
                # Simple string like "AUTO_APPROVE"
                actions.append(PolicyAction(
                    action_type=ActionType(action_data),
                    reason=data.get("reason", ""),
                ))

        return cls(
            rule_id=data.get("id", f"rule_{datetime.now().timestamp()}"),
            name=data.get("name", ""),
            description=data.get("description", ""),
            priority=data.get("priority", 100),
            layer=data.get("layer", "STANDARD"),
            conditions=conditions,
            actions=actions,
            is_active=data.get("active", True),
            tags=data.get("tags", []),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "name": self.name,
            "description": self.description,
            "priority": self.priority,
            "layer": self.layer,
            "conditions": [c.to_dict() for c in self.conditions],
            "actions": [a.to_dict() for a in self.actions],
            "is_active": self.is_active,
            "tags": self.tags,
        }

    def to_yaml(self) -> str:
        """Convert rule to YAML string."""
        lines = []
        lines.append(f"- id: {self.rule_id}")
        lines.append(f"  name: {self.name}")
        if self.description:
            lines.append(f"  description: {self.description}")
        lines.append(f"  priority: {self.priority}")
        lines.append(f"  layer: {self.layer}")

        lines.append("  when:")
        for cond in self.conditions:
            lines.append(f"    - \"{cond.field} {cond.operator.value} {cond.value}\"")

        lines.append("  then:")
        for action in self.actions:
            if action.action_type == ActionType.ADD_APPROVER:
                lines.append(f"    - action: ADD_APPROVER")
                if action.approver_type:
                    lines.append(f"      approver: {action.approver_type.value}")
                if action.sla_hours:
                    lines.append(f"      sla: {action.sla_hours}")
                if action.reason:
                    lines.append(f"      reason: \"{action.reason}\"")
            else:
                lines.append(f"    - action: {action.action_type.value}")

        return "\n".join(lines)


@dataclass
class RuleMatch:
    """Result of a rule evaluation."""
    rule: PolicyRule
    matched: bool
    matched_conditions: List[str] = field(default_factory=list)
    actions_to_execute: List[PolicyAction] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id": self.rule.rule_id,
            "rule_name": self.rule.name,
            "matched": self.matched,
            "matched_conditions": self.matched_conditions,
            "actions": [a.to_dict() for a in self.actions_to_execute],
        }


# ============================================================
# POLICY SET
# ============================================================

@dataclass
class PolicySet:
    """
    A collection of policies.

    Can be loaded from YAML files or defined programmatically.
    """
    policy_id: str
    name: str
    description: str = ""
    version: str = "1.0"

    # Rules organized by layer
    mandatory_rules: List[PolicyRule] = field(default_factory=list)
    risk_adaptive_rules: List[PolicyRule] = field(default_factory=list)
    contextual_rules: List[PolicyRule] = field(default_factory=list)
    optimization_rules: List[PolicyRule] = field(default_factory=list)

    # Metadata
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def add_rule(self, rule: PolicyRule) -> None:
        """Add a rule to the appropriate layer."""
        if rule.layer == "MANDATORY":
            self.mandatory_rules.append(rule)
        elif rule.layer == "RISK_ADAPTIVE":
            self.risk_adaptive_rules.append(rule)
        elif rule.layer == "CONTEXTUAL":
            self.contextual_rules.append(rule)
        elif rule.layer == "OPTIMIZATION":
            self.optimization_rules.append(rule)
        else:
            self.contextual_rules.append(rule)

        # Sort by priority
        self._sort_rules()

    def _sort_rules(self) -> None:
        """Sort all rules by priority."""
        self.mandatory_rules.sort(key=lambda r: r.priority)
        self.risk_adaptive_rules.sort(key=lambda r: r.priority)
        self.contextual_rules.sort(key=lambda r: r.priority)
        self.optimization_rules.sort(key=lambda r: r.priority)

    def get_all_rules(self) -> List[PolicyRule]:
        """Get all rules in evaluation order."""
        return (
            self.mandatory_rules +
            self.risk_adaptive_rules +
            self.contextual_rules +
            self.optimization_rules
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "policy_id": self.policy_id,
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "rules": {
                "mandatory": [r.to_dict() for r in self.mandatory_rules],
                "risk_adaptive": [r.to_dict() for r in self.risk_adaptive_rules],
                "contextual": [r.to_dict() for r in self.contextual_rules],
                "optimization": [r.to_dict() for r in self.optimization_rules],
            },
            "is_active": self.is_active,
        }


# ============================================================
# POLICY ENGINE
# ============================================================

class PolicyEngine:
    """
    The core policy evaluation engine.

    Evaluates context against policies and determines workflow steps.
    """

    def __init__(self):
        """Initialize policy engine."""
        self._policy_sets: Dict[str, PolicySet] = {}
        self._default_policy_id: Optional[str] = None
        self._init_default_policies()

    def _init_default_policies(self) -> None:
        """Initialize default governance policies."""
        default_policy = PolicySet(
            policy_id="CORE-GOVERNANCE",
            name="Core Governance Policy",
            description="Default policy for all workflow types",
            version="1.0",
        )

        # ========================================
        # MANDATORY RULES (Always apply)
        # ========================================

        # Production system requires system owner
        default_policy.add_rule(PolicyRule(
            rule_id="MANDATORY-PROD-SYSTEM-OWNER",
            name="Production System Owner",
            description="Production systems require system owner approval",
            layer="MANDATORY",
            priority=10,
            conditions=[
                PolicyCondition.from_string("is_production == true"),
            ],
            actions=[
                PolicyAction(
                    action_type=ActionType.ADD_APPROVER,
                    approver_type=ApproverTypeEnum.SYSTEM_OWNER,
                    sla_hours=8.0,
                    reason="Production system access requires system owner approval",
                ),
            ],
        ))

        # Financial process requires process owner
        default_policy.add_rule(PolicyRule(
            rule_id="MANDATORY-FINANCIAL-PROCESS-OWNER",
            name="Financial Process Owner",
            description="Financial processes require process owner approval",
            layer="MANDATORY",
            priority=20,
            conditions=[
                PolicyCondition(
                    field="business_process",
                    operator=ConditionOperator.IN,
                    value=["P2P", "O2C", "RTR", "FINANCIAL_CLOSE", "AP", "AR", "GL"],
                ),
            ],
            actions=[
                PolicyAction(
                    action_type=ActionType.ADD_APPROVER,
                    approver_type=ApproverTypeEnum.PROCESS_OWNER,
                    sla_hours=6.0,
                    reason="Financial process access requires process owner approval",
                ),
            ],
        ))

        # Sensitive data requires data owner
        default_policy.add_rule(PolicyRule(
            rule_id="MANDATORY-SENSITIVE-DATA-OWNER",
            name="Sensitive Data Owner",
            description="Access to sensitive data requires data owner approval",
            layer="MANDATORY",
            priority=30,
            conditions=[
                PolicyCondition.from_string("has_sensitive_data == true"),
            ],
            actions=[
                PolicyAction(
                    action_type=ActionType.ADD_APPROVER,
                    approver_type=ApproverTypeEnum.DATA_OWNER,
                    sla_hours=8.0,
                    reason="Sensitive data access requires data owner approval",
                ),
            ],
        ))

        # ========================================
        # RISK-ADAPTIVE RULES
        # ========================================

        # Auto-approve low risk
        default_policy.add_rule(PolicyRule(
            rule_id="RISK-AUTO-APPROVE-LOW",
            name="Auto-Approve Low Risk",
            description="Auto-approve low-risk requests",
            layer="RISK_ADAPTIVE",
            priority=10,
            conditions=[
                PolicyCondition.from_string("risk_score <= 20"),
                PolicyCondition.from_string("is_production == false"),
                PolicyCondition.from_string("has_sod_conflicts == false"),
            ],
            actions=[
                PolicyAction(
                    action_type=ActionType.AUTO_APPROVE,
                    reason="Low risk request auto-approved",
                ),
            ],
        ))

        # Medium risk requires manager
        default_policy.add_rule(PolicyRule(
            rule_id="RISK-MANAGER-MEDIUM",
            name="Manager Approval - Medium Risk",
            description="Medium risk requests require manager approval",
            layer="RISK_ADAPTIVE",
            priority=20,
            conditions=[
                PolicyCondition.from_string("risk_score > 20"),
                PolicyCondition.from_string("risk_score <= 50"),
            ],
            actions=[
                PolicyAction(
                    action_type=ActionType.ADD_APPROVER,
                    approver_type=ApproverTypeEnum.LINE_MANAGER,
                    sla_hours=24.0,
                    reason="Medium risk requires manager review",
                ),
            ],
        ))

        # High risk requires security
        default_policy.add_rule(PolicyRule(
            rule_id="RISK-SECURITY-HIGH",
            name="Security Approval - High Risk",
            description="High risk requests require security team approval",
            layer="RISK_ADAPTIVE",
            priority=30,
            conditions=[
                PolicyCondition.from_string("risk_score > 50"),
                PolicyCondition.from_string("risk_score <= 80"),
            ],
            actions=[
                PolicyAction(
                    action_type=ActionType.ADD_APPROVER,
                    approver_type=ApproverTypeEnum.LINE_MANAGER,
                    sla_hours=12.0,
                    reason="High risk requires manager review",
                ),
                PolicyAction(
                    action_type=ActionType.ADD_APPROVER,
                    approver_type=ApproverTypeEnum.SECURITY_OFFICER,
                    sla_hours=8.0,
                    reason="High risk requires security team review",
                ),
            ],
        ))

        # Critical risk requires CISO
        default_policy.add_rule(PolicyRule(
            rule_id="RISK-CISO-CRITICAL",
            name="CISO Approval - Critical Risk",
            description="Critical risk requests require CISO approval",
            layer="RISK_ADAPTIVE",
            priority=40,
            conditions=[
                PolicyCondition.from_string("risk_score > 80"),
            ],
            actions=[
                PolicyAction(
                    action_type=ActionType.ADD_APPROVER,
                    approver_type=ApproverTypeEnum.LINE_MANAGER,
                    sla_hours=8.0,
                    reason="Critical risk requires manager review",
                ),
                PolicyAction(
                    action_type=ActionType.ADD_APPROVER,
                    approver_type=ApproverTypeEnum.SECURITY_OFFICER,
                    sla_hours=4.0,
                    reason="Critical risk requires security team review",
                ),
                PolicyAction(
                    action_type=ActionType.ADD_APPROVER,
                    approver_type=ApproverTypeEnum.COMPLIANCE_OFFICER,
                    sla_hours=4.0,
                    reason="Critical risk requires compliance review",
                ),
                PolicyAction(
                    action_type=ActionType.ADD_APPROVER,
                    approver_type=ApproverTypeEnum.CISO,
                    sla_hours=8.0,
                    reason="Critical risk requires CISO sign-off",
                ),
            ],
        ))

        # SoD conflicts require compliance
        default_policy.add_rule(PolicyRule(
            rule_id="RISK-SOD-COMPLIANCE",
            name="SoD Conflict - Compliance Review",
            description="SoD conflicts require compliance review",
            layer="RISK_ADAPTIVE",
            priority=50,
            conditions=[
                PolicyCondition.from_string("has_sod_conflicts == true"),
            ],
            actions=[
                PolicyAction(
                    action_type=ActionType.ADD_APPROVER,
                    approver_type=ApproverTypeEnum.COMPLIANCE_OFFICER,
                    sla_hours=8.0,
                    reason="SoD conflict requires compliance review",
                ),
                PolicyAction(
                    action_type=ActionType.REQUIRE_JUSTIFICATION,
                    reason="SoD conflict requires documented justification",
                ),
            ],
        ))

        # ========================================
        # CONTEXTUAL RULES
        # ========================================

        # Firefighter access requires supervisor
        default_policy.add_rule(PolicyRule(
            rule_id="CONTEXT-FIREFIGHTER",
            name="Firefighter Supervisor",
            description="Firefighter access requires supervisor approval",
            layer="CONTEXTUAL",
            priority=10,
            conditions=[
                PolicyCondition(
                    field="process_type",
                    operator=ConditionOperator.IN,
                    value=["FIREFIGHTER", "EMERGENCY_ACCESS"],
                ),
            ],
            actions=[
                PolicyAction(
                    action_type=ActionType.ADD_APPROVER,
                    approver_type=ApproverTypeEnum.FIREFIGHTER_SUPERVISOR,
                    sla_hours=2.0,
                    reason="Emergency access requires supervisor approval",
                ),
                PolicyAction(
                    action_type=ActionType.ADD_POST_REVIEW,
                    reason="Emergency access requires post-use review",
                ),
            ],
        ))

        # Temporary access has shorter SLA
        default_policy.add_rule(PolicyRule(
            rule_id="CONTEXT-TEMPORARY",
            name="Temporary Access SLA",
            description="Temporary access has expedited processing",
            layer="CONTEXTUAL",
            priority=20,
            conditions=[
                PolicyCondition.from_string("is_temporary == true"),
            ],
            actions=[
                PolicyAction(
                    action_type=ActionType.SET_SLA,
                    sla_hours=4.0,
                    reason="Temporary access expedited",
                ),
            ],
        ))

        # Role creation requires security review
        default_policy.add_rule(PolicyRule(
            rule_id="CONTEXT-ROLE-CREATION",
            name="Role Creation Review",
            description="Role creation requires security review",
            layer="CONTEXTUAL",
            priority=30,
            conditions=[
                PolicyCondition(
                    field="process_type",
                    operator=ConditionOperator.IN,
                    value=["ROLE_CREATION", "ROLE_MODIFICATION"],
                ),
            ],
            actions=[
                PolicyAction(
                    action_type=ActionType.ADD_APPROVER,
                    approver_type=ApproverTypeEnum.SECURITY_OFFICER,
                    sla_hours=24.0,
                    reason="Role changes require security review",
                ),
                PolicyAction(
                    action_type=ActionType.ADD_APPROVER,
                    approver_type=ApproverTypeEnum.ROLE_OWNER,
                    sla_hours=24.0,
                    reason="Role changes require role owner approval",
                ),
            ],
        ))

        # Store default policy
        self._policy_sets[default_policy.policy_id] = default_policy
        self._default_policy_id = default_policy.policy_id

        logger.info(f"Initialized default policy with {len(default_policy.get_all_rules())} rules")

    def load_policy_from_yaml(self, yaml_content: str) -> PolicySet:
        """Load a policy set from YAML content."""
        import yaml as yaml_parser

        data = yaml_parser.safe_load(yaml_content)

        policy = PolicySet(
            policy_id=data.get("id", f"policy_{datetime.now().timestamp()}"),
            name=data.get("name", "Custom Policy"),
            description=data.get("description", ""),
            version=data.get("version", "1.0"),
        )

        for rule_data in data.get("rules", []):
            rule = PolicyRule.from_yaml_dict(rule_data)
            policy.add_rule(rule)

        self._policy_sets[policy.policy_id] = policy
        return policy

    def evaluate(
        self,
        context: WorkflowContext,
        policy_id: Optional[str] = None
    ) -> Tuple[List[RuleMatch], List[PolicyAction]]:
        """
        Evaluate context against policy and return matched rules and actions.

        Args:
            context: Workflow context to evaluate
            policy_id: Optional specific policy to use

        Returns:
            Tuple of (matched rules, actions to execute)
        """
        policy_id = policy_id or self._default_policy_id
        if not policy_id or policy_id not in self._policy_sets:
            raise ValueError(f"Policy not found: {policy_id}")

        policy = self._policy_sets[policy_id]
        context_dict = context.to_eval_dict()

        matched_rules: List[RuleMatch] = []
        all_actions: List[PolicyAction] = []
        auto_approved = False

        # Evaluate rules by layer (order matters)
        for rule in policy.get_all_rules():
            if not rule.is_active:
                continue

            matched = rule.matches(context_dict)
            match_result = RuleMatch(
                rule=rule,
                matched=matched,
                matched_conditions=rule.get_matched_conditions(context_dict) if matched else [],
                actions_to_execute=rule.actions if matched else [],
            )
            matched_rules.append(match_result)

            if matched:
                logger.debug(f"Rule matched: {rule.rule_id}")

                # Check for auto-approve action
                for action in rule.actions:
                    if action.action_type == ActionType.AUTO_APPROVE:
                        auto_approved = True
                        all_actions.append(action)
                    elif action.action_type == ActionType.AUTO_REJECT:
                        # Auto-reject takes precedence
                        return matched_rules, [action]
                    else:
                        all_actions.append(action)

        # If auto-approved, only return that action (no approvers needed)
        if auto_approved:
            # But still include mandatory approvers
            mandatory_actions = [
                a for a in all_actions
                if a.action_type == ActionType.ADD_APPROVER
                and any(
                    r.rule.layer == "MANDATORY" and r.matched
                    for r in matched_rules
                    if a in r.actions_to_execute
                )
            ]
            if mandatory_actions:
                # Can't auto-approve with mandatory rules
                auto_actions = [a for a in all_actions if a.action_type != ActionType.AUTO_APPROVE]
                return matched_rules, auto_actions
            else:
                auto_action = [a for a in all_actions if a.action_type == ActionType.AUTO_APPROVE]
                return matched_rules, auto_action

        return matched_rules, all_actions

    def get_policy(self, policy_id: str) -> Optional[PolicySet]:
        """Get a policy by ID."""
        return self._policy_sets.get(policy_id)

    def list_policies(self) -> List[PolicySet]:
        """List all policies."""
        return list(self._policy_sets.values())

    def add_policy(self, policy: PolicySet) -> None:
        """Add a policy set."""
        self._policy_sets[policy.policy_id] = policy

    def remove_policy(self, policy_id: str) -> bool:
        """Remove a policy set."""
        if policy_id in self._policy_sets:
            del self._policy_sets[policy_id]
            return True
        return False

    def set_default_policy(self, policy_id: str) -> None:
        """Set the default policy."""
        if policy_id not in self._policy_sets:
            raise ValueError(f"Policy not found: {policy_id}")
        self._default_policy_id = policy_id

    def explain_evaluation(
        self,
        context: WorkflowContext,
        policy_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Explain the policy evaluation for a context.

        Useful for debugging and audit.
        """
        matched_rules, actions = self.evaluate(context, policy_id)

        return {
            "context_summary": {
                "system": context.system_id,
                "risk_score": context.risk_score,
                "risk_level": context.risk_level,
                "is_production": context.is_production,
                "process_type": context.process_type.value,
            },
            "rules_evaluated": len(matched_rules),
            "rules_matched": len([r for r in matched_rules if r.matched]),
            "matched_rules": [
                {
                    "rule_id": r.rule.rule_id,
                    "rule_name": r.rule.name,
                    "layer": r.rule.layer,
                    "conditions_matched": r.matched_conditions,
                }
                for r in matched_rules if r.matched
            ],
            "actions": [a.to_dict() for a in actions],
            "outcome": (
                "AUTO_APPROVE" if any(a.action_type == ActionType.AUTO_APPROVE for a in actions)
                else "AUTO_REJECT" if any(a.action_type == ActionType.AUTO_REJECT for a in actions)
                else f"{len([a for a in actions if a.action_type == ActionType.ADD_APPROVER])} approver(s) required"
            ),
        }
