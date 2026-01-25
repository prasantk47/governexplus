# ARA Rule Engine
# Policy-as-Code risk rule definitions and evaluation

"""
Rule Engine for Access Risk Analysis.

Provides:
- Versioned risk rule definitions
- Rule testing and simulation
- Change impact analysis
- Dynamic rule evaluation
"""

from typing import List, Optional, Dict, Any, Callable, Set
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import logging
import json
import re

from .models import (
    RiskSeverity,
    RiskCategory,
    SoDRule,
    SoDFunction,
    SoDRuleSet,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Rule Condition Types
# =============================================================================

class ConditionOperator(Enum):
    """Operators for rule conditions."""
    EQUALS = "eq"
    NOT_EQUALS = "ne"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    CONTAINS_ANY = "contains_any"  # List contains any of the values
    IN = "in"
    NOT_IN = "not_in"
    GREATER_THAN = "gt"
    LESS_THAN = "lt"
    GREATER_EQUAL = "gte"
    LESS_EQUAL = "lte"
    MATCHES = "matches"  # Regex
    EXISTS = "exists"
    NOT_EXISTS = "not_exists"
    ALL = "all"  # All values in list
    ANY = "any"  # Any value in list


@dataclass
class RuleCondition:
    """
    Single condition in a rule.

    Evaluates a field against a value using an operator.
    """
    field: str  # e.g., "tcodes", "auth_objects.S_TCODE.TCD"
    operator: ConditionOperator = ConditionOperator.EQUALS
    value: Any = None  # Expected value
    case_sensitive: bool = False

    def evaluate(self, context: Dict[str, Any]) -> bool:
        """
        Evaluate condition against context.

        Args:
            context: Dictionary of field values

        Returns:
            True if condition is met
        """
        # Get field value from context (supports nested paths)
        field_value = self._get_field_value(context, self.field)

        # Handle None field value
        if self.operator == ConditionOperator.EXISTS:
            return field_value is not None
        if self.operator == ConditionOperator.NOT_EXISTS:
            return field_value is None

        if field_value is None:
            return False

        # Normalize case if needed
        if not self.case_sensitive:
            if isinstance(field_value, str):
                field_value = field_value.upper()
            if isinstance(self.value, str):
                compare_value = self.value.upper()
            elif isinstance(self.value, list):
                compare_value = [v.upper() if isinstance(v, str) else v for v in self.value]
            else:
                compare_value = self.value
        else:
            compare_value = self.value

        # Evaluate based on operator
        return self._evaluate_operator(field_value, compare_value)

    def _get_field_value(self, context: Dict[str, Any], field_path: str) -> Any:
        """Get nested field value using dot notation."""
        parts = field_path.split(".")
        value = context

        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            elif isinstance(value, list) and part.isdigit():
                idx = int(part)
                value = value[idx] if idx < len(value) else None
            else:
                return None

            if value is None:
                return None

        return value

    def _evaluate_operator(self, field_value: Any, compare_value: Any) -> bool:
        """Evaluate operator against values."""
        op = self.operator

        if op == ConditionOperator.EQUALS:
            return field_value == compare_value

        elif op == ConditionOperator.NOT_EQUALS:
            return field_value != compare_value

        elif op == ConditionOperator.CONTAINS:
            if isinstance(field_value, (list, set)):
                return compare_value in field_value
            elif isinstance(field_value, str):
                return compare_value in field_value
            return False

        elif op == ConditionOperator.NOT_CONTAINS:
            if isinstance(field_value, (list, set)):
                return compare_value not in field_value
            elif isinstance(field_value, str):
                return compare_value not in field_value
            return True

        elif op == ConditionOperator.CONTAINS_ANY:
            # Field is a list, check if any of compare_values are in it
            if isinstance(field_value, (list, set)):
                if isinstance(compare_value, (list, set)):
                    return bool(set(field_value) & set(compare_value))
                return compare_value in field_value
            return False

        elif op == ConditionOperator.IN:
            return field_value in compare_value

        elif op == ConditionOperator.NOT_IN:
            return field_value not in compare_value

        elif op == ConditionOperator.GREATER_THAN:
            return field_value > compare_value

        elif op == ConditionOperator.LESS_THAN:
            return field_value < compare_value

        elif op == ConditionOperator.GREATER_EQUAL:
            return field_value >= compare_value

        elif op == ConditionOperator.LESS_EQUAL:
            return field_value <= compare_value

        elif op == ConditionOperator.MATCHES:
            if isinstance(field_value, str):
                return bool(re.match(compare_value, field_value))
            return False

        elif op == ConditionOperator.ALL:
            if isinstance(field_value, (list, set)):
                return all(v in field_value for v in compare_value)
            return False

        elif op == ConditionOperator.ANY:
            if isinstance(field_value, (list, set)):
                return any(v in field_value for v in compare_value)
            return False

        return False


# =============================================================================
# Rule Definition
# =============================================================================

@dataclass
class RuleDefinition:
    """
    Complete rule definition with conditions and actions.

    Supports policy-as-code approach with versioning.
    """
    rule_id: str
    name: str
    description: str = ""

    # Rule type
    rule_type: str = "sod"  # sod, sensitive, critical, behavioral

    # Conditions (AND logic by default)
    conditions: List[RuleCondition] = field(default_factory=list)
    condition_logic: str = "AND"  # AND, OR

    # SoD-specific: two function definitions
    function_1_conditions: List[RuleCondition] = field(default_factory=list)
    function_2_conditions: List[RuleCondition] = field(default_factory=list)

    # Risk attributes
    severity: RiskSeverity = RiskSeverity.HIGH
    category: RiskCategory = RiskCategory.FINANCIAL
    business_impact: str = ""

    # Rule metadata
    enabled: bool = True
    version: int = 1
    effective_date: Optional[datetime] = None
    expiry_date: Optional[datetime] = None

    # Organizational scope
    org_scope: Dict[str, List[str]] = field(default_factory=dict)

    # Tags for filtering
    tags: List[str] = field(default_factory=list)

    # Audit
    created_at: datetime = field(default_factory=datetime.now)
    created_by: str = ""
    modified_at: Optional[datetime] = None
    modified_by: Optional[str] = None

    def is_active(self) -> bool:
        """Check if rule is currently active."""
        if not self.enabled:
            return False

        now = datetime.now()

        if self.effective_date and now < self.effective_date:
            return False

        if self.expiry_date and now > self.expiry_date:
            return False

        return True

    def evaluate(self, context: Dict[str, Any]) -> bool:
        """
        Evaluate rule against context.

        Args:
            context: Access context to evaluate

        Returns:
            True if rule conditions are met (risk exists)
        """
        if not self.is_active():
            return False

        # Check organizational scope
        if not self._check_org_scope(context):
            return False

        # Evaluate conditions based on rule type
        if self.rule_type == "sod":
            return self._evaluate_sod(context)
        else:
            return self._evaluate_conditions(context, self.conditions)

    def _evaluate_sod(self, context: Dict[str, Any]) -> bool:
        """Evaluate SoD rule (both functions must be present)."""
        has_function_1 = self._evaluate_conditions(context, self.function_1_conditions)
        has_function_2 = self._evaluate_conditions(context, self.function_2_conditions)

        return has_function_1 and has_function_2

    def _evaluate_conditions(
        self,
        context: Dict[str, Any],
        conditions: List[RuleCondition]
    ) -> bool:
        """Evaluate a list of conditions."""
        if not conditions:
            return False

        results = [cond.evaluate(context) for cond in conditions]

        if self.condition_logic == "AND":
            return all(results)
        else:  # OR
            return any(results)

    def _check_org_scope(self, context: Dict[str, Any]) -> bool:
        """Check if context is within rule's organizational scope."""
        if not self.org_scope:
            return True  # No scope restriction

        for field, allowed_values in self.org_scope.items():
            context_value = context.get(field)
            if context_value and context_value not in allowed_values:
                return False

        return True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "rule_id": self.rule_id,
            "name": self.name,
            "description": self.description,
            "rule_type": self.rule_type,
            "severity": self.severity.value,
            "category": self.category.value,
            "business_impact": self.business_impact,
            "enabled": self.enabled,
            "version": self.version,
            "tags": self.tags,
            "created_at": self.created_at.isoformat(),
        }

    def to_sod_rule(self) -> SoDRule:
        """Convert to SoDRule for compatibility."""
        # Extract tcodes from conditions
        func1_tcodes = self._extract_tcodes(self.function_1_conditions)
        func2_tcodes = self._extract_tcodes(self.function_2_conditions)

        return SoDRule(
            rule_id=self.rule_id,
            name=self.name,
            description=self.description,
            function_1_tcodes=func1_tcodes,
            function_2_tcodes=func2_tcodes,
            severity=self.severity,
            category=self.category,
            business_impact=self.business_impact,
            enabled=self.enabled,
            version=self.version,
        )

    def _extract_tcodes(self, conditions: List[RuleCondition]) -> List[str]:
        """Extract tcode values from conditions."""
        tcodes = []
        for cond in conditions:
            if "tcode" in cond.field.lower():
                if isinstance(cond.value, list):
                    tcodes.extend(cond.value)
                elif cond.value:
                    tcodes.append(cond.value)
        return tcodes


# =============================================================================
# Rule Engine
# =============================================================================

class RuleEngine:
    """
    Core rule engine for risk evaluation.

    Manages rule definitions and evaluates access against rules.
    """

    def __init__(self):
        self.rules: Dict[str, RuleDefinition] = {}
        self.rule_sets: Dict[str, SoDRuleSet] = {}
        self.functions: Dict[str, SoDFunction] = {}

        # Load default rules
        self._load_default_rules()

    def add_rule(self, rule: RuleDefinition) -> None:
        """Add a rule to the engine."""
        self.rules[rule.rule_id] = rule
        logger.info(f"Added rule: {rule.rule_id} - {rule.name}")

    def remove_rule(self, rule_id: str) -> bool:
        """Remove a rule from the engine."""
        if rule_id in self.rules:
            del self.rules[rule_id]
            return True
        return False

    def get_rule(self, rule_id: str) -> Optional[RuleDefinition]:
        """Get a rule by ID."""
        return self.rules.get(rule_id)

    def list_rules(
        self,
        rule_type: Optional[str] = None,
        category: Optional[RiskCategory] = None,
        tags: Optional[List[str]] = None,
        enabled_only: bool = True
    ) -> List[RuleDefinition]:
        """
        List rules with optional filtering.

        Args:
            rule_type: Filter by rule type
            category: Filter by category
            tags: Filter by tags (any match)
            enabled_only: Only return enabled rules
        """
        result = []

        for rule in self.rules.values():
            # Filter by enabled
            if enabled_only and not rule.is_active():
                continue

            # Filter by type
            if rule_type and rule.rule_type != rule_type:
                continue

            # Filter by category
            if category and rule.category != category:
                continue

            # Filter by tags
            if tags and not any(t in rule.tags for t in tags):
                continue

            result.append(rule)

        return result

    def evaluate_access(
        self,
        context: Dict[str, Any],
        rule_types: Optional[List[str]] = None
    ) -> List[tuple]:
        """
        Evaluate access context against all applicable rules.

        Args:
            context: Access context to evaluate
            rule_types: Optional filter for rule types

        Returns:
            List of (rule, result) tuples for triggered rules
        """
        triggered = []

        for rule in self.rules.values():
            # Filter by rule type
            if rule_types and rule.rule_type not in rule_types:
                continue

            # Skip inactive rules
            if not rule.is_active():
                continue

            # Evaluate
            if rule.evaluate(context):
                triggered.append((rule, True))
                logger.debug(f"Rule triggered: {rule.rule_id}")

        return triggered

    def simulate_access_change(
        self,
        current_access: Dict[str, Any],
        new_access: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Simulate impact of access change.

        Args:
            current_access: Current access context
            new_access: Access to be added

        Returns:
            Simulation result with risk delta
        """
        # Evaluate current risks
        current_triggered = self.evaluate_access(current_access)

        # Merge access
        combined_access = self._merge_access(current_access, new_access)

        # Evaluate combined risks
        combined_triggered = self.evaluate_access(combined_access)

        # Find new risks
        current_rule_ids = {r[0].rule_id for r in current_triggered}
        new_risks = [r for r in combined_triggered if r[0].rule_id not in current_rule_ids]

        return {
            "current_risk_count": len(current_triggered),
            "combined_risk_count": len(combined_triggered),
            "new_risks": new_risks,
            "risk_delta": len(combined_triggered) - len(current_triggered),
        }

    def _merge_access(
        self,
        current: Dict[str, Any],
        new: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Merge two access contexts."""
        merged = current.copy()

        for key, value in new.items():
            if key in merged:
                if isinstance(merged[key], list) and isinstance(value, list):
                    merged[key] = list(set(merged[key] + value))
                elif isinstance(merged[key], set) and isinstance(value, (set, list)):
                    merged[key] = merged[key] | set(value)
                else:
                    merged[key] = value
            else:
                merged[key] = value

        return merged

    def add_function(self, function: SoDFunction) -> None:
        """Add a business function definition."""
        self.functions[function.function_id] = function

    def add_ruleset(self, ruleset: SoDRuleSet) -> None:
        """Add a ruleset with functions and rules."""
        self.rule_sets[ruleset.ruleset_id] = ruleset

        # Add functions
        for func_id, func in ruleset.functions.items():
            self.functions[func_id] = func

        # Convert and add rules
        for sod_rule in ruleset.rules:
            rule_def = self._convert_sod_rule(sod_rule)
            self.add_rule(rule_def)

    def _convert_sod_rule(self, sod_rule: SoDRule) -> RuleDefinition:
        """Convert SoDRule to RuleDefinition."""
        # Build conditions from tcodes
        func1_conditions = []
        if sod_rule.function_1_tcodes:
            func1_conditions.append(RuleCondition(
                field="tcodes",
                operator=ConditionOperator.ANY,
                value=sod_rule.function_1_tcodes
            ))

        func2_conditions = []
        if sod_rule.function_2_tcodes:
            func2_conditions.append(RuleCondition(
                field="tcodes",
                operator=ConditionOperator.ANY,
                value=sod_rule.function_2_tcodes
            ))

        return RuleDefinition(
            rule_id=sod_rule.rule_id,
            name=sod_rule.name,
            description=sod_rule.description,
            rule_type="sod",
            function_1_conditions=func1_conditions,
            function_2_conditions=func2_conditions,
            severity=sod_rule.severity,
            category=sod_rule.category,
            business_impact=sod_rule.business_impact,
            enabled=sod_rule.enabled,
            version=sod_rule.version,
        )

    def _load_default_rules(self):
        """Load default SoD and sensitive access rules."""
        # Common SoD rules
        default_rules = [
            # Financial SoD
            RuleDefinition(
                rule_id="SOD_FIN_001",
                name="Create Vendor / Post Payment",
                description="User can create vendors and also post payments to vendors",
                rule_type="sod",
                function_1_conditions=[
                    RuleCondition("tcodes", ConditionOperator.ANY, ["XK01", "MK01", "FK01"])
                ],
                function_2_conditions=[
                    RuleCondition("tcodes", ConditionOperator.ANY, ["F-53", "F110", "FBZ1"])
                ],
                severity=RiskSeverity.CRITICAL,
                category=RiskCategory.FINANCIAL,
                business_impact="Risk of fraudulent payments to fictitious vendors",
                tags=["financial", "fraud", "payment"],
            ),
            RuleDefinition(
                rule_id="SOD_FIN_002",
                name="Create Purchase Order / Approve Purchase Order",
                description="User can create and approve purchase orders",
                rule_type="sod",
                function_1_conditions=[
                    RuleCondition("tcodes", ConditionOperator.ANY, ["ME21N", "ME21"])
                ],
                function_2_conditions=[
                    RuleCondition("tcodes", ConditionOperator.ANY, ["ME28", "ME29N"])
                ],
                severity=RiskSeverity.HIGH,
                category=RiskCategory.FINANCIAL,
                business_impact="Risk of unauthorized procurement",
                tags=["financial", "procurement"],
            ),
            RuleDefinition(
                rule_id="SOD_FIN_003",
                name="Maintain GL Accounts / Post Journal Entries",
                description="User can maintain GL accounts and post journal entries",
                rule_type="sod",
                function_1_conditions=[
                    RuleCondition("tcodes", ConditionOperator.ANY, ["FS00", "FSP0"])
                ],
                function_2_conditions=[
                    RuleCondition("tcodes", ConditionOperator.ANY, ["FB01", "FB50", "F-02"])
                ],
                severity=RiskSeverity.HIGH,
                category=RiskCategory.FINANCIAL,
                business_impact="Risk of fraudulent financial postings",
                tags=["financial", "accounting"],
            ),

            # HR SoD
            RuleDefinition(
                rule_id="SOD_HR_001",
                name="Maintain Employee / Approve Payroll",
                description="User can maintain employee records and approve payroll",
                rule_type="sod",
                function_1_conditions=[
                    RuleCondition("tcodes", ConditionOperator.ANY, ["PA30", "PA40"])
                ],
                function_2_conditions=[
                    RuleCondition("tcodes", ConditionOperator.ANY, ["PC00_M99_PAP", "PC00_M99_CEDT"])
                ],
                severity=RiskSeverity.HIGH,
                category=RiskCategory.HR,
                business_impact="Risk of ghost employees or payroll fraud",
                tags=["hr", "payroll", "fraud"],
            ),

            # IT SoD
            RuleDefinition(
                rule_id="SOD_IT_001",
                name="User Admin / Role Admin",
                description="User can create users and assign roles",
                rule_type="sod",
                function_1_conditions=[
                    RuleCondition("tcodes", ConditionOperator.ANY, ["SU01", "SU10"])
                ],
                function_2_conditions=[
                    RuleCondition("tcodes", ConditionOperator.ANY, ["PFCG", "SU01"])
                ],
                severity=RiskSeverity.CRITICAL,
                category=RiskCategory.IT,
                business_impact="Risk of unauthorized privilege escalation",
                tags=["it", "security", "access"],
            ),

            # Sensitive access rules
            RuleDefinition(
                rule_id="SENS_001",
                name="Debug Access",
                description="User has ABAP debugging capability",
                rule_type="sensitive",
                conditions=[
                    RuleCondition("tcodes", ConditionOperator.ANY, ["SE38", "SE80", "SE24"])
                ],
                severity=RiskSeverity.HIGH,
                category=RiskCategory.IT,
                business_impact="Can bypass authorization checks via debugging",
                tags=["it", "development", "debug"],
            ),
            RuleDefinition(
                rule_id="SENS_002",
                name="Direct Table Access",
                description="User has direct database table access",
                rule_type="sensitive",
                conditions=[
                    RuleCondition("tcodes", ConditionOperator.ANY, ["SE16", "SE16N", "SE17", "SM30"])
                ],
                severity=RiskSeverity.HIGH,
                category=RiskCategory.IT,
                business_impact="Can view/modify data bypassing application controls",
                tags=["it", "data", "table"],
            ),
            RuleDefinition(
                rule_id="SENS_003",
                name="Transport Management",
                description="User has transport management access",
                rule_type="sensitive",
                conditions=[
                    RuleCondition("tcodes", ConditionOperator.ANY, ["STMS", "SE09", "SE10"])
                ],
                severity=RiskSeverity.HIGH,
                category=RiskCategory.IT,
                business_impact="Can move changes to production system",
                tags=["it", "transport", "change"],
            ),
        ]

        for rule in default_rules:
            self.add_rule(rule)

        logger.info(f"Loaded {len(default_rules)} default rules")

    def export_rules(self, format: str = "json") -> str:
        """Export all rules to JSON."""
        rules_data = [rule.to_dict() for rule in self.rules.values()]
        return json.dumps(rules_data, indent=2, default=str)

    def import_rules(self, rules_json: str) -> int:
        """
        Import rules from JSON.

        Returns number of rules imported.
        """
        rules_data = json.loads(rules_json)
        imported = 0

        for rule_dict in rules_data:
            try:
                # Convert severity and category back to enums
                rule_dict["severity"] = RiskSeverity(rule_dict["severity"])
                rule_dict["category"] = RiskCategory(rule_dict["category"])

                # Remove datetime fields for now
                rule_dict.pop("created_at", None)

                rule = RuleDefinition(**rule_dict)
                self.add_rule(rule)
                imported += 1
            except Exception as e:
                logger.warning(f"Could not import rule: {e}")

        return imported
