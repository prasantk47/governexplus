"""
Organizational Rules for Risk Analysis

Filters false positives from SoD analysis by considering organizational context.
SAP GRC equivalent: Organizational Rules that filter risks by company code, plant, etc.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum
import uuid


class OrgRuleType(Enum):
    """Types of organizational rules"""
    EXCLUSION = "exclusion"         # Exclude risk if org values don't overlap
    INCLUSION = "inclusion"         # Only flag risk if org values match
    SUPPLEMENTARY = "supplementary" # Additional conditions on top of base rule


class OrgFieldType(Enum):
    """Organizational field types"""
    COMPANY_CODE = "company_code"     # BUKRS
    PLANT = "plant"                   # WERKS
    SALES_ORG = "sales_org"           # VKORG
    PURCHASING_ORG = "purchasing_org" # EKORG
    COST_CENTER = "cost_center"       # KOSTL
    PROFIT_CENTER = "profit_center"   # PRCTR
    BUSINESS_AREA = "business_area"   # GSBER
    CONTROLLING_AREA = "controlling_area"  # KOKRS
    COUNTRY = "country"
    REGION = "region"
    DEPARTMENT = "department"
    CUSTOM = "custom"


@dataclass
class OrgFieldValue:
    """A specific organizational field and its values"""
    field_type: OrgFieldType
    field_name: str = ""  # For custom fields
    values: List[str] = field(default_factory=list)
    include_all: bool = False  # True = match any value

    def matches(self, user_values: List[str]) -> bool:
        """Check if user's org values match this rule"""
        if self.include_all:
            return True
        if not self.values or not user_values:
            return False
        # Check for overlap
        return bool(set(self.values) & set(user_values))

    def to_dict(self) -> Dict:
        return {
            "field_type": self.field_type.value,
            "field_name": self.field_name,
            "values": self.values,
            "include_all": self.include_all
        }


@dataclass
class OrganizationalRule:
    """
    Organizational rule for filtering risk analysis.

    Example: A user with AP posting in Company Code 1000 and vendor maintenance
    in Company Code 2000 should NOT trigger an SoD - the access is separated
    by organization.
    """
    rule_id: str = field(default_factory=lambda: f"ORG-{uuid.uuid4().hex[:8].upper()}")
    name: str = ""
    description: str = ""
    rule_type: OrgRuleType = OrgRuleType.EXCLUSION

    # Which risk rules this applies to
    risk_ids: List[str] = field(default_factory=list)  # Empty = all risks
    risk_categories: List[str] = field(default_factory=list)

    # Organizational fields to check
    org_fields: List[OrgFieldValue] = field(default_factory=list)

    # How to evaluate multiple fields
    require_all_fields: bool = True  # True = AND, False = OR

    # Scope
    systems: List[str] = field(default_factory=list)  # Empty = all systems
    is_cross_system: bool = False

    # Status
    is_active: bool = True
    valid_from: Optional[datetime] = None
    valid_to: Optional[datetime] = None

    # Audit
    created_by: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def applies_to_risk(self, risk_id: str, risk_category: str = "") -> bool:
        """Check if this rule applies to a specific risk"""
        if self.risk_ids and risk_id not in self.risk_ids:
            return False
        if self.risk_categories and risk_category not in self.risk_categories:
            return False
        return True

    def evaluate(self, function1_org: Dict, function2_org: Dict) -> bool:
        """
        Evaluate if the organizational rule filters out this risk.

        Args:
            function1_org: Org values for first function (e.g., {"company_code": ["1000", "2000"]})
            function2_org: Org values for second function

        Returns:
            True if risk should be FILTERED OUT (no real conflict)
            False if risk is VALID (real conflict exists)
        """
        if self.rule_type == OrgRuleType.EXCLUSION:
            return self._evaluate_exclusion(function1_org, function2_org)
        elif self.rule_type == OrgRuleType.INCLUSION:
            return not self._evaluate_inclusion(function1_org, function2_org)
        return False

    def _evaluate_exclusion(self, func1_org: Dict, func2_org: Dict) -> bool:
        """
        Exclusion rule: Filter risk if org values DON'T overlap.
        Example: User has AP in CC 1000 and vendor maint in CC 2000 = no real conflict
        """
        for org_field in self.org_fields:
            field_key = org_field.field_type.value
            if org_field.field_name:
                field_key = org_field.field_name

            func1_values = func1_org.get(field_key, [])
            func2_values = func2_org.get(field_key, [])

            if isinstance(func1_values, str):
                func1_values = [func1_values]
            if isinstance(func2_values, str):
                func2_values = [func2_values]

            # Check for overlap
            overlap = set(func1_values) & set(func2_values)

            if self.require_all_fields:
                # AND logic: all fields must have no overlap to filter
                if overlap:
                    return False  # Found overlap, risk is valid
            else:
                # OR logic: any field with no overlap filters the risk
                if not overlap:
                    return True  # No overlap found, filter the risk

        # For AND logic: no overlaps found in any field = filter
        # For OR logic: all fields had overlap = risk is valid
        return self.require_all_fields

    def _evaluate_inclusion(self, func1_org: Dict, func2_org: Dict) -> bool:
        """
        Inclusion rule: Only flag risk if org values DO overlap.
        Inverse of exclusion.
        """
        for org_field in self.org_fields:
            field_key = org_field.field_type.value
            func1_values = func1_org.get(field_key, [])
            func2_values = func2_org.get(field_key, [])

            if isinstance(func1_values, str):
                func1_values = [func1_values]
            if isinstance(func2_values, str):
                func2_values = [func2_values]

            overlap = set(func1_values) & set(func2_values)

            if self.require_all_fields:
                if not overlap:
                    return False
            else:
                if overlap:
                    return True

        return self.require_all_fields

    def to_dict(self) -> Dict:
        return {
            "rule_id": self.rule_id,
            "name": self.name,
            "description": self.description,
            "rule_type": self.rule_type.value,
            "risk_ids": self.risk_ids,
            "risk_categories": self.risk_categories,
            "org_fields": [f.to_dict() for f in self.org_fields],
            "require_all_fields": self.require_all_fields,
            "systems": self.systems,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat()
        }


@dataclass
class SupplementaryRule:
    """
    Supplementary rule for additional risk conditions.
    SAP GRC equivalent: Supplementary rules that add conditions to base risks.
    """
    rule_id: str = field(default_factory=lambda: f"SUP-{uuid.uuid4().hex[:8].upper()}")
    name: str = ""
    description: str = ""

    # Base risk this supplements
    base_risk_id: str = ""

    # Additional conditions
    conditions: List[Dict] = field(default_factory=list)
    # Example: [{"field": "amount_limit", "operator": "gt", "value": 10000}]

    # What happens if conditions match
    action: str = "elevate"  # elevate, reduce, exclude
    new_risk_level: str = ""  # For elevate/reduce

    is_active: bool = True

    def evaluate(self, context: Dict) -> Optional[str]:
        """
        Evaluate supplementary conditions.

        Returns:
            New risk level if conditions match, None otherwise
        """
        all_match = True
        for condition in self.conditions:
            field_name = condition.get("field")
            operator = condition.get("operator")
            expected = condition.get("value")

            actual = context.get(field_name)
            if actual is None:
                all_match = False
                break

            if not self._compare(actual, operator, expected):
                all_match = False
                break

        if all_match:
            if self.action == "exclude":
                return "excluded"
            return self.new_risk_level

        return None

    def _compare(self, actual: Any, operator: str, expected: Any) -> bool:
        """Compare values based on operator"""
        ops = {
            "eq": lambda a, e: a == e,
            "ne": lambda a, e: a != e,
            "gt": lambda a, e: a > e,
            "gte": lambda a, e: a >= e,
            "lt": lambda a, e: a < e,
            "lte": lambda a, e: a <= e,
            "in": lambda a, e: a in e,
            "not_in": lambda a, e: a not in e,
            "contains": lambda a, e: e in str(a),
            "starts_with": lambda a, e: str(a).startswith(e),
        }
        return ops.get(operator, lambda a, e: False)(actual, expected)

    def to_dict(self) -> Dict:
        return {
            "rule_id": self.rule_id,
            "name": self.name,
            "description": self.description,
            "base_risk_id": self.base_risk_id,
            "conditions": self.conditions,
            "action": self.action,
            "new_risk_level": self.new_risk_level,
            "is_active": self.is_active
        }


class OrgRuleEngine:
    """
    Engine for managing and applying organizational rules.
    Provides zero-training experience with sensible defaults.
    """

    def __init__(self):
        self.org_rules: Dict[str, OrganizationalRule] = {}
        self.supplementary_rules: Dict[str, SupplementaryRule] = {}
        self._init_default_rules()

    def _init_default_rules(self):
        """Initialize default organizational rules for common scenarios"""

        # Company Code Separation Rule
        cc_rule = OrganizationalRule(
            rule_id="ORG-CC-SEP",
            name="Company Code Separation",
            description="Filter SoD if functions are in different company codes",
            rule_type=OrgRuleType.EXCLUSION,
            org_fields=[
                OrgFieldValue(
                    field_type=OrgFieldType.COMPANY_CODE,
                    include_all=False
                )
            ],
            risk_categories=["SOD"]
        )

        # Plant Separation Rule
        plant_rule = OrganizationalRule(
            rule_id="ORG-PLANT-SEP",
            name="Plant Separation",
            description="Filter SoD if functions are in different plants",
            rule_type=OrgRuleType.EXCLUSION,
            org_fields=[
                OrgFieldValue(
                    field_type=OrgFieldType.PLANT,
                    include_all=False
                )
            ],
            risk_categories=["SOD"],
            is_active=False  # Disabled by default
        )

        # Purchasing Org Separation
        purch_rule = OrganizationalRule(
            rule_id="ORG-EKORG-SEP",
            name="Purchasing Organization Separation",
            description="Filter procurement SoD if in different purchasing orgs",
            rule_type=OrgRuleType.EXCLUSION,
            org_fields=[
                OrgFieldValue(
                    field_type=OrgFieldType.PURCHASING_ORG,
                    include_all=False
                )
            ],
            risk_categories=["SOD-P2P", "SOD-PROCUREMENT"]
        )

        # Sales Org Separation
        sales_rule = OrganizationalRule(
            rule_id="ORG-VKORG-SEP",
            name="Sales Organization Separation",
            description="Filter sales SoD if in different sales orgs",
            rule_type=OrgRuleType.EXCLUSION,
            org_fields=[
                OrgFieldValue(
                    field_type=OrgFieldType.SALES_ORG,
                    include_all=False
                )
            ],
            risk_categories=["SOD-O2C", "SOD-SALES"]
        )

        # Critical Company Code Rule (Inclusion)
        critical_cc_rule = OrganizationalRule(
            rule_id="ORG-CC-CRITICAL",
            name="Critical Company Code Focus",
            description="Only flag risks in critical company codes",
            rule_type=OrgRuleType.INCLUSION,
            org_fields=[
                OrgFieldValue(
                    field_type=OrgFieldType.COMPANY_CODE,
                    values=["1000", "2000"],  # Main operating companies
                    include_all=False
                )
            ],
            is_active=False  # Disabled by default
        )

        for rule in [cc_rule, plant_rule, purch_rule, sales_rule, critical_cc_rule]:
            self.org_rules[rule.rule_id] = rule

        # Default Supplementary Rules
        high_amount_rule = SupplementaryRule(
            rule_id="SUP-HIGH-AMOUNT",
            name="High Amount Transactions",
            description="Elevate risk for high-value transactions",
            conditions=[
                {"field": "transaction_limit", "operator": "gt", "value": 100000}
            ],
            action="elevate",
            new_risk_level="critical"
        )

        test_user_rule = SupplementaryRule(
            rule_id="SUP-TEST-USER",
            name="Test User Exclusion",
            description="Exclude test users from risk analysis",
            conditions=[
                {"field": "user_id", "operator": "starts_with", "value": "TEST"}
            ],
            action="exclude"
        )

        for rule in [high_amount_rule, test_user_rule]:
            self.supplementary_rules[rule.rule_id] = rule

    def filter_risk(
        self,
        risk_id: str,
        risk_category: str,
        func1_org: Dict,
        func2_org: Dict,
        context: Optional[Dict] = None
    ) -> Dict:
        """
        Apply organizational rules to determine if a risk should be filtered.

        Returns:
            {
                "filtered": bool,
                "reason": str,
                "applied_rules": List[str],
                "adjusted_risk_level": Optional[str]
            }
        """
        applied_rules = []
        filtered = False
        reason = ""
        adjusted_level = None

        # Apply organizational rules
        for rule in self.org_rules.values():
            if not rule.is_active:
                continue
            if not rule.applies_to_risk(risk_id, risk_category):
                continue

            if rule.evaluate(func1_org, func2_org):
                filtered = True
                applied_rules.append(rule.rule_id)
                reason = f"Filtered by {rule.name}: Organizational separation detected"
                break

        # Apply supplementary rules if not filtered and context provided
        if not filtered and context:
            for sup_rule in self.supplementary_rules.values():
                if not sup_rule.is_active:
                    continue
                if sup_rule.base_risk_id and sup_rule.base_risk_id != risk_id:
                    continue

                result = sup_rule.evaluate(context)
                if result:
                    applied_rules.append(sup_rule.rule_id)
                    if result == "excluded":
                        filtered = True
                        reason = f"Excluded by {sup_rule.name}"
                    else:
                        adjusted_level = result
                        reason = f"Risk level adjusted by {sup_rule.name}"

        return {
            "filtered": filtered,
            "reason": reason,
            "applied_rules": applied_rules,
            "adjusted_risk_level": adjusted_level
        }

    # =========================================================================
    # Rule Management
    # =========================================================================

    def list_org_rules(self, active_only: bool = False) -> List[OrganizationalRule]:
        """List all organizational rules"""
        rules = list(self.org_rules.values())
        if active_only:
            rules = [r for r in rules if r.is_active]
        return rules

    def get_org_rule(self, rule_id: str) -> Optional[OrganizationalRule]:
        """Get an organizational rule by ID"""
        return self.org_rules.get(rule_id)

    def create_org_rule(self, rule: OrganizationalRule) -> OrganizationalRule:
        """Create a new organizational rule"""
        self.org_rules[rule.rule_id] = rule
        return rule

    def update_org_rule(self, rule_id: str, updates: Dict) -> Optional[OrganizationalRule]:
        """Update an organizational rule"""
        if rule_id not in self.org_rules:
            return None
        rule = self.org_rules[rule_id]
        for key, value in updates.items():
            if hasattr(rule, key):
                setattr(rule, key, value)
        rule.updated_at = datetime.now()
        return rule

    def delete_org_rule(self, rule_id: str) -> bool:
        """Delete an organizational rule"""
        if rule_id in self.org_rules:
            del self.org_rules[rule_id]
            return True
        return False

    def toggle_org_rule(self, rule_id: str) -> Optional[OrganizationalRule]:
        """Toggle rule active status"""
        if rule_id in self.org_rules:
            self.org_rules[rule_id].is_active = not self.org_rules[rule_id].is_active
            return self.org_rules[rule_id]
        return None

    # =========================================================================
    # Supplementary Rule Management
    # =========================================================================

    def list_supplementary_rules(self) -> List[SupplementaryRule]:
        """List all supplementary rules"""
        return list(self.supplementary_rules.values())

    def create_supplementary_rule(self, rule: SupplementaryRule) -> SupplementaryRule:
        """Create a new supplementary rule"""
        self.supplementary_rules[rule.rule_id] = rule
        return rule

    # =========================================================================
    # Statistics
    # =========================================================================

    def get_statistics(self) -> Dict:
        """Get organizational rule statistics"""
        return {
            "total_org_rules": len(self.org_rules),
            "active_org_rules": len([r for r in self.org_rules.values() if r.is_active]),
            "total_supplementary_rules": len(self.supplementary_rules),
            "rules_by_type": {
                "exclusion": len([r for r in self.org_rules.values()
                                 if r.rule_type == OrgRuleType.EXCLUSION]),
                "inclusion": len([r for r in self.org_rules.values()
                                 if r.rule_type == OrgRuleType.INCLUSION])
            },
            "rules_by_field": {
                field.value: len([r for r in self.org_rules.values()
                                 if any(f.field_type == field for f in r.org_fields)])
                for field in OrgFieldType
            }
        }
