# Approval Rules
# YAML-based rule engine (BRF+ replacement)

"""
Approval Rules for GOVERNEX+.

Rules are defined in YAML, not ABAP:
- Human-readable
- Git-versionable
- Testable
- No transports

Rule types:
- Layer 1: Mandatory (Hard governance)
- Layer 2: Risk-Adaptive (Dynamic)
- Layer 3: Optimization (AI-assisted)
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
from enum import Enum
import logging
import re
import operator

from .models import (
    ApprovalContext, ApproverType, Approver,
    ApprovalPriority
)

logger = logging.getLogger(__name__)


class RuleLayer(Enum):
    """Rule evaluation layers."""
    MANDATORY = "MANDATORY"  # Cannot be skipped
    RISK_ADAPTIVE = "RISK_ADAPTIVE"  # Based on risk score
    OPTIMIZATION = "OPTIMIZATION"  # AI-assisted


class RuleStatus(Enum):
    """Rule lifecycle status."""
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    DEPRECATED = "DEPRECATED"
    DISABLED = "DISABLED"


class ConditionOperator(Enum):
    """Operators for conditions."""
    EQUALS = "="
    NOT_EQUALS = "!="
    GREATER_THAN = ">"
    LESS_THAN = "<"
    GREATER_EQUAL = ">="
    LESS_EQUAL = "<="
    IN = "IN"
    NOT_IN = "NOT_IN"
    CONTAINS = "CONTAINS"
    MATCHES = "MATCHES"


@dataclass
class RuleCondition:
    """
    A single condition in a rule.

    Supports:
    - Simple equality: system = SAP_PRD
    - Comparison: risk_score > 70
    - List membership: process IN [P2P, O2C]
    """
    field: str
    operator: ConditionOperator
    value: Any

    def evaluate(self, context: Dict[str, Any]) -> bool:
        """Evaluate condition against context."""
        # Get field value from context (supports nested fields)
        actual_value = self._get_nested_value(context, self.field)

        if actual_value is None:
            return False

        # Evaluate based on operator
        if self.operator == ConditionOperator.EQUALS:
            return str(actual_value) == str(self.value)

        elif self.operator == ConditionOperator.NOT_EQUALS:
            return str(actual_value) != str(self.value)

        elif self.operator == ConditionOperator.GREATER_THAN:
            return float(actual_value) > float(self.value)

        elif self.operator == ConditionOperator.LESS_THAN:
            return float(actual_value) < float(self.value)

        elif self.operator == ConditionOperator.GREATER_EQUAL:
            return float(actual_value) >= float(self.value)

        elif self.operator == ConditionOperator.LESS_EQUAL:
            return float(actual_value) <= float(self.value)

        elif self.operator == ConditionOperator.IN:
            return actual_value in self.value

        elif self.operator == ConditionOperator.NOT_IN:
            return actual_value not in self.value

        elif self.operator == ConditionOperator.CONTAINS:
            return self.value in str(actual_value)

        elif self.operator == ConditionOperator.MATCHES:
            return bool(re.match(self.value, str(actual_value)))

        return False

    def _get_nested_value(self, data: Dict[str, Any], field: str) -> Any:
        """Get value from nested dict using dot notation."""
        keys = field.split(".")
        value = data
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
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
    def from_dict(cls, data: Dict[str, Any]) -> "RuleCondition":
        return cls(
            field=data["field"],
            operator=ConditionOperator(data["operator"]),
            value=data["value"],
        )

    @classmethod
    def parse(cls, condition_str: str) -> "RuleCondition":
        """
        Parse condition from string.

        Examples:
        - "system = SAP_PRD"
        - "risk_score > 70"
        - "process IN [P2P, O2C]"
        """
        # Pattern for parsing conditions
        patterns = [
            (r"(\S+)\s*>=\s*(.+)", ConditionOperator.GREATER_EQUAL),
            (r"(\S+)\s*<=\s*(.+)", ConditionOperator.LESS_EQUAL),
            (r"(\S+)\s*!=\s*(.+)", ConditionOperator.NOT_EQUALS),
            (r"(\S+)\s*>\s*(.+)", ConditionOperator.GREATER_THAN),
            (r"(\S+)\s*<\s*(.+)", ConditionOperator.LESS_THAN),
            (r"(\S+)\s*=\s*(.+)", ConditionOperator.EQUALS),
            (r"(\S+)\s+IN\s+\[(.+)\]", ConditionOperator.IN),
            (r"(\S+)\s+NOT_IN\s+\[(.+)\]", ConditionOperator.NOT_IN),
        ]

        for pattern, op in patterns:
            match = re.match(pattern, condition_str.strip(), re.IGNORECASE)
            if match:
                field = match.group(1)
                value = match.group(2).strip()

                # Parse list values
                if op in [ConditionOperator.IN, ConditionOperator.NOT_IN]:
                    value = [v.strip() for v in value.split(",")]

                # Try to parse numeric values
                elif value.replace(".", "").replace("-", "").isdigit():
                    value = float(value)

                return cls(field=field, operator=op, value=value)

        raise ValueError(f"Cannot parse condition: {condition_str}")


@dataclass
class ApproverSpec:
    """Specification for an approver in a rule."""
    approver_type: ApproverType
    process: Optional[str] = None
    system: Optional[str] = None
    specific_id: Optional[str] = None
    required: bool = True
    can_be_delegated: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.approver_type.value,
            "process": self.process,
            "system": self.system,
            "specific_id": self.specific_id,
            "required": self.required,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ApproverSpec":
        return cls(
            approver_type=ApproverType(data["type"]),
            process=data.get("process"),
            system=data.get("system"),
            specific_id=data.get("specific_id"),
            required=data.get("required", True),
        )


@dataclass
class ApprovalRule:
    """
    A single approval rule.

    YAML representation:
    ```yaml
    rule_id: APPROVER-P2P-HIGH
    order: 10
    layer: RISK_ADAPTIVE

    conditions:
      system: SAP_PRD
      business_process: P2P
      risk_score: ">70"

    approvers:
      - type: PROCESS_OWNER
        process: P2P
      - type: SECURITY

    sla_hours: 8

    explain:
      why: "High-risk financial access in production system"
    ```
    """
    rule_id: str
    name: str
    description: str

    # Evaluation
    order: int = 100  # Lower = higher priority
    layer: RuleLayer = RuleLayer.RISK_ADAPTIVE

    # Conditions (all must match)
    conditions: List[RuleCondition] = field(default_factory=list)

    # Approvers required
    approvers: List[ApproverSpec] = field(default_factory=list)

    # SLA
    sla_hours: float = 24.0
    priority: ApprovalPriority = ApprovalPriority.NORMAL

    # Explainability
    explanation: str = ""
    business_rationale: str = ""

    # Lifecycle
    status: RuleStatus = RuleStatus.ACTIVE
    created_at: datetime = field(default_factory=datetime.now)
    created_by: str = ""
    version: str = "1.0"

    # Actions
    auto_approve_if_low_risk: bool = False
    notify_observers: List[str] = field(default_factory=list)

    def evaluate(self, context: ApprovalContext) -> bool:
        """
        Evaluate if rule applies to context.

        All conditions must match.
        """
        if self.status != RuleStatus.ACTIVE:
            return False

        context_dict = context.to_dict()

        for condition in self.conditions:
            if not condition.evaluate(context_dict):
                return False

        return True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "name": self.name,
            "description": self.description,
            "order": self.order,
            "layer": self.layer.value,
            "conditions": [c.to_dict() for c in self.conditions],
            "approvers": [a.to_dict() for a in self.approvers],
            "sla_hours": self.sla_hours,
            "priority": self.priority.value,
            "explanation": self.explanation,
            "status": self.status.value,
            "version": self.version,
        }

    def to_yaml(self) -> str:
        """Export rule to YAML format."""
        lines = [
            f"rule_id: {self.rule_id}",
            f"name: {self.name}",
            f"order: {self.order}",
            f"layer: {self.layer.value}",
            "",
            "conditions:",
        ]

        for cond in self.conditions:
            lines.append(f"  {cond.field}: \"{cond.operator.value}{cond.value}\"")

        lines.append("")
        lines.append("approvers:")
        for approver in self.approvers:
            lines.append(f"  - type: {approver.approver_type.value}")
            if approver.process:
                lines.append(f"    process: {approver.process}")
            if approver.system:
                lines.append(f"    system: {approver.system}")

        lines.append("")
        lines.append(f"sla_hours: {self.sla_hours}")
        lines.append("")
        lines.append("explain:")
        lines.append(f"  why: \"{self.explanation}\"")

        lines.append("")
        lines.append("lifecycle:")
        lines.append(f"  status: {self.status.value}")
        lines.append(f"  version: {self.version}")

        return "\n".join(lines)

    @classmethod
    def from_yaml_dict(cls, data: Dict[str, Any]) -> "ApprovalRule":
        """Create rule from parsed YAML dictionary."""
        conditions = []
        if "conditions" in data:
            for field, value in data["conditions"].items():
                if isinstance(value, str):
                    # Parse operator from value string
                    condition = RuleCondition.parse(f"{field} {value}")
                    conditions.append(condition)
                else:
                    conditions.append(RuleCondition(
                        field=field,
                        operator=ConditionOperator.EQUALS,
                        value=value
                    ))

        approvers = []
        if "approvers" in data:
            for approver_data in data["approvers"]:
                approvers.append(ApproverSpec.from_dict(approver_data))

        return cls(
            rule_id=data.get("rule_id", ""),
            name=data.get("name", ""),
            description=data.get("description", ""),
            order=data.get("order", 100),
            layer=RuleLayer(data.get("layer", "RISK_ADAPTIVE")),
            conditions=conditions,
            approvers=approvers,
            sla_hours=data.get("sla_hours", 24.0),
            priority=ApprovalPriority(data.get("priority", "NORMAL")),
            explanation=data.get("explain", {}).get("why", ""),
            status=RuleStatus(data.get("lifecycle", {}).get("status", "ACTIVE")),
            version=data.get("lifecycle", {}).get("version", "1.0"),
        )


@dataclass
class RuleEvaluationResult:
    """Result of evaluating a rule."""
    rule_id: str
    matched: bool
    conditions_evaluated: int = 0
    conditions_matched: int = 0
    approvers: List[ApproverSpec] = field(default_factory=list)
    sla_hours: float = 0.0
    explanation: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "matched": self.matched,
            "conditions_evaluated": self.conditions_evaluated,
            "conditions_matched": self.conditions_matched,
            "approvers": [a.to_dict() for a in self.approvers],
            "sla_hours": self.sla_hours,
            "explanation": self.explanation,
        }


@dataclass
class RuleSet:
    """Collection of approval rules."""
    ruleset_id: str
    name: str
    description: str

    rules: List[ApprovalRule] = field(default_factory=list)

    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    version: str = "1.0"

    def add_rule(self, rule: ApprovalRule) -> None:
        """Add rule to set."""
        self.rules.append(rule)
        # Keep sorted by order
        self.rules.sort(key=lambda r: r.order)

    def get_rule(self, rule_id: str) -> Optional[ApprovalRule]:
        """Get rule by ID."""
        for rule in self.rules:
            if rule.rule_id == rule_id:
                return rule
        return None

    def get_rules_by_layer(self, layer: RuleLayer) -> List[ApprovalRule]:
        """Get all rules in a layer."""
        return [r for r in self.rules if r.layer == layer]


class RuleEngine:
    """
    Rule engine for approval determination.

    Evaluates rules in order:
    1. Mandatory rules (Layer 1)
    2. Risk-adaptive rules (Layer 2)
    3. Optimization rules (Layer 3)
    """

    def __init__(self, ruleset: Optional[RuleSet] = None):
        """Initialize rule engine."""
        self.ruleset = ruleset or RuleSet(
            ruleset_id="DEFAULT",
            name="Default Ruleset",
            description="Default approval rules",
        )

    def evaluate(
        self,
        context: ApprovalContext
    ) -> List[RuleEvaluationResult]:
        """
        Evaluate all rules against context.

        Returns all matching rules.
        """
        results = []

        for rule in self.ruleset.rules:
            if rule.status != RuleStatus.ACTIVE:
                continue

            conditions_evaluated = len(rule.conditions)
            conditions_matched = 0

            context_dict = context.to_dict()

            for condition in rule.conditions:
                if condition.evaluate(context_dict):
                    conditions_matched += 1

            matched = conditions_matched == conditions_evaluated

            results.append(RuleEvaluationResult(
                rule_id=rule.rule_id,
                matched=matched,
                conditions_evaluated=conditions_evaluated,
                conditions_matched=conditions_matched,
                approvers=rule.approvers if matched else [],
                sla_hours=rule.sla_hours if matched else 0.0,
                explanation=rule.explanation if matched else "",
            ))

        return results

    def get_applicable_rules(
        self,
        context: ApprovalContext
    ) -> List[ApprovalRule]:
        """Get all rules that apply to this context."""
        return [
            rule for rule in self.ruleset.rules
            if rule.status == RuleStatus.ACTIVE and rule.evaluate(context)
        ]

    def get_required_approvers(
        self,
        context: ApprovalContext
    ) -> List[ApproverSpec]:
        """
        Get all required approvers based on rules.

        Combines approvers from all matching rules,
        removing duplicates.
        """
        approvers_by_type: Dict[str, ApproverSpec] = {}

        for rule in self.get_applicable_rules(context):
            for approver in rule.approvers:
                key = f"{approver.approver_type.value}_{approver.process or ''}_{approver.system or ''}"
                if key not in approvers_by_type:
                    approvers_by_type[key] = approver

        return list(approvers_by_type.values())

    def simulate(
        self,
        context: ApprovalContext,
        what_if: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Simulate rule evaluation with what-if analysis.

        Args:
            context: Base context
            what_if: Changes to simulate (e.g., {"risk.risk_score": 50})

        Returns:
            Simulation results
        """
        # Create modified context for what-if
        if what_if:
            import copy
            modified_context = copy.deepcopy(context)
            context_dict = modified_context.to_dict()

            for field, value in what_if.items():
                self._set_nested_value(context_dict, field, value)

            # Rebuild context from dict (simplified)
            if "risk" in context_dict and "risk_score" in what_if.get("risk", {}):
                modified_context.risk.risk_score = what_if["risk"]["risk_score"]
        else:
            modified_context = context

        # Evaluate
        matching_rules = self.get_applicable_rules(modified_context)
        required_approvers = self.get_required_approvers(modified_context)

        return {
            "context": modified_context.to_dict(),
            "matching_rules": [r.rule_id for r in matching_rules],
            "required_approvers": [a.to_dict() for a in required_approvers],
            "total_sla_hours": sum(r.sla_hours for r in matching_rules),
            "what_if_applied": what_if or {},
        }

    def _set_nested_value(self, data: Dict, field: str, value: Any) -> None:
        """Set value in nested dict using dot notation."""
        keys = field.split(".")
        current = data
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        current[keys[-1]] = value

    def load_rules_from_yaml(self, yaml_content: str) -> None:
        """Load rules from YAML content."""
        try:
            import yaml
            data = yaml.safe_load(yaml_content)

            if isinstance(data, list):
                for rule_data in data:
                    rule = ApprovalRule.from_yaml_dict(rule_data)
                    self.ruleset.add_rule(rule)
            elif isinstance(data, dict):
                rule = ApprovalRule.from_yaml_dict(data)
                self.ruleset.add_rule(rule)

        except ImportError:
            raise ImportError("PyYAML required for YAML parsing")


# Built-in rules
BUILTIN_RULES = [
    # Layer 1: Mandatory Rules
    ApprovalRule(
        rule_id="MANDATORY-PROD-SYSTEM-OWNER",
        name="Production System Owner Required",
        description="System owner required for all production access",
        order=10,
        layer=RuleLayer.MANDATORY,
        conditions=[
            RuleCondition("request.system_criticality", ConditionOperator.EQUALS, "PROD"),
        ],
        approvers=[
            ApproverSpec(ApproverType.SYSTEM_OWNER, required=True),
        ],
        sla_hours=8,
        explanation="Production access requires system owner approval",
    ),
    ApprovalRule(
        rule_id="MANDATORY-FINANCIAL-PROCESS-OWNER",
        name="Financial Process Owner Required",
        description="Process owner required for financial access",
        order=11,
        layer=RuleLayer.MANDATORY,
        conditions=[
            RuleCondition("risk.affects_financial", ConditionOperator.EQUALS, True),
        ],
        approvers=[
            ApproverSpec(ApproverType.PROCESS_OWNER, required=True),
        ],
        sla_hours=8,
        explanation="Financial access requires process owner approval",
    ),

    # Layer 2: Risk-Adaptive Rules
    ApprovalRule(
        rule_id="RISK-AUTO-APPROVE-LOW",
        name="Auto-Approve Low Risk",
        description="Auto-approve requests with risk score <= 20",
        order=50,
        layer=RuleLayer.RISK_ADAPTIVE,
        conditions=[
            RuleCondition("risk.risk_score", ConditionOperator.LESS_EQUAL, 20),
            RuleCondition("risk.sod_conflict_count", ConditionOperator.EQUALS, 0),
        ],
        approvers=[],  # No approvers = auto-approve
        sla_hours=0,
        explanation="Low-risk request qualifies for auto-approval",
        auto_approve_if_low_risk=True,
    ),
    ApprovalRule(
        rule_id="RISK-MANAGER-MEDIUM",
        name="Manager Approval for Medium Risk",
        description="Line manager required for risk 21-50",
        order=51,
        layer=RuleLayer.RISK_ADAPTIVE,
        conditions=[
            RuleCondition("risk.risk_score", ConditionOperator.GREATER_THAN, 20),
            RuleCondition("risk.risk_score", ConditionOperator.LESS_EQUAL, 50),
        ],
        approvers=[
            ApproverSpec(ApproverType.LINE_MANAGER, required=True),
        ],
        sla_hours=24,
        explanation="Medium-risk request requires manager approval",
    ),
    ApprovalRule(
        rule_id="RISK-SECURITY-HIGH",
        name="Security Approval for High Risk",
        description="Security + Process Owner for risk 51-80",
        order=52,
        layer=RuleLayer.RISK_ADAPTIVE,
        conditions=[
            RuleCondition("risk.risk_score", ConditionOperator.GREATER_THAN, 50),
            RuleCondition("risk.risk_score", ConditionOperator.LESS_EQUAL, 80),
        ],
        approvers=[
            ApproverSpec(ApproverType.SECURITY_OFFICER, required=True),
            ApproverSpec(ApproverType.PROCESS_OWNER, required=True),
        ],
        sla_hours=16,
        explanation="High-risk request requires security and process owner approval",
    ),
    ApprovalRule(
        rule_id="RISK-CISO-CRITICAL",
        name="CISO Approval for Critical Risk",
        description="CISO + Compliance for risk > 80",
        order=53,
        layer=RuleLayer.RISK_ADAPTIVE,
        conditions=[
            RuleCondition("risk.risk_score", ConditionOperator.GREATER_THAN, 80),
        ],
        approvers=[
            ApproverSpec(ApproverType.SECURITY_OFFICER, required=True),
            ApproverSpec(ApproverType.COMPLIANCE_OFFICER, required=True),
            ApproverSpec(ApproverType.CISO, required=True),
        ],
        sla_hours=8,
        explanation="Critical-risk request requires CISO and compliance approval",
        priority=ApprovalPriority.CRITICAL,
    ),
]
