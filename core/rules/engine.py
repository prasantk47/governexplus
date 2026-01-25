"""
GRC Rules Engine - Core Rule Processing

This module provides the main rule engine for evaluating Segregation of Duties (SoD)
and other access control rules. Similar to SAP GRC Access Control's Risk Analysis
and Remediation (RAR) component.
"""

import uuid
import yaml
import json
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any, Set, Tuple
from datetime import datetime, timedelta
import logging

try:
    import networkx as nx
    HAS_NETWORKX = True
except ImportError:
    HAS_NETWORKX = False

from .models import (
    Entitlement, Permission, ConflictSet, UserAccess,
    RiskViolation, RiskSeverity, RuleType, RiskCategory
)

logger = logging.getLogger(__name__)


@dataclass
class RiskRule:
    """
    Represents a complete risk rule definition.

    Equivalent to SAP GRC rule IDs like P001-P200 for financial risks.
    """
    rule_id: str
    name: str
    description: str
    rule_type: RuleType
    severity: RiskSeverity
    risk_category: RiskCategory

    # Conflicting permissions/entitlements
    conflicts: List[ConflictSet] = field(default_factory=list)

    # For sensitive access rules (single function)
    sensitive_entitlements: List[Entitlement] = field(default_factory=list)

    # Business justification and remediation
    business_justification: str = ""
    mitigation_controls: List[str] = field(default_factory=list)
    recommended_actions: List[str] = field(default_factory=list)

    # Applicability filters
    applies_to_systems: List[str] = field(default_factory=lambda: ["*"])
    applies_to_departments: List[str] = field(default_factory=lambda: ["*"])
    applies_to_user_types: List[str] = field(default_factory=lambda: ["*"])

    # Exceptions
    exception_users: List[str] = field(default_factory=list)
    exception_roles: List[str] = field(default_factory=list)

    # Lifecycle
    effective_date: Optional[datetime] = None
    expiry_date: Optional[datetime] = None
    enabled: bool = True

    # Versioning
    version: str = "1.0"
    created_by: str = ""
    created_at: datetime = field(default_factory=datetime.now)

    def is_applicable(self, user_context: UserAccess) -> bool:
        """Check if this rule applies to the given user context"""
        if not self.enabled:
            return False

        # Check date validity
        now = datetime.now()
        if self.effective_date and now < self.effective_date:
            return False
        if self.expiry_date and now > self.expiry_date:
            return False

        # Check department filter
        if "*" not in self.applies_to_departments:
            if user_context.department not in self.applies_to_departments:
                return False

        # Check user type filter
        if "*" not in self.applies_to_user_types:
            if user_context.employment_type not in self.applies_to_user_types:
                return False

        # Check exceptions
        if user_context.user_id in self.exception_users:
            return False
        if any(role in self.exception_roles for role in user_context.roles):
            return False

        return True


class RuleEngine:
    """
    Main rule engine for GRC risk analysis.

    Features:
    - Load rules from YAML/JSON files
    - Evaluate users against rules
    - Support for SoD and sensitive access rules
    - Rule dependency tracking (with networkx)
    - Batch analysis capabilities
    """

    def __init__(self, rules_path: Optional[str] = None):
        self.rules: Dict[str, RiskRule] = {}
        self.rule_index_by_category: Dict[RiskCategory, List[str]] = {}
        self.rule_index_by_type: Dict[RuleType, List[str]] = {}

        # Rule dependency graph
        if HAS_NETWORKX:
            self.rule_graph = nx.DiGraph()

        # Statistics
        self.stats = {
            "rules_loaded": 0,
            "evaluations_performed": 0,
            "violations_found": 0
        }

        # Load default rules
        self._load_default_sap_rules()

        # Load from file if provided
        if rules_path:
            self.load_rules_from_file(rules_path)

    def _load_default_sap_rules(self):
        """Load standard SAP GRC-like rules"""

        # Financial SoD Rules
        self.add_rule(RiskRule(
            rule_id="FI_P2P_001",
            name="Purchase to Pay - Vendor Creation & Payment",
            description="User can create vendors AND execute payments, creating fraud risk",
            rule_type=RuleType.SOD,
            severity=RiskSeverity.CRITICAL,
            risk_category=RiskCategory.FINANCIAL,
            conflicts=[
                ConflictSet(
                    name="Vendor Creation vs Payment Execution",
                    description="Segregation between vendor master maintenance and payment processing",
                    function_a_name="Vendor Creation",
                    function_a_entitlements=[
                        Entitlement(auth_object="S_TCODE", field="TCD", value="XK01"),
                        Entitlement(auth_object="S_TCODE", field="TCD", value="FK01"),
                    ],
                    function_b_name="Payment Execution",
                    function_b_entitlements=[
                        Entitlement(auth_object="S_TCODE", field="TCD", value="F110"),
                        Entitlement(auth_object="S_TCODE", field="TCD", value="F-53"),
                    ]
                )
            ],
            business_justification="Prevents ghost vendor fraud where same person creates fictitious vendors and pays them",
            mitigation_controls=[
                "Dual approval for payments > $10,000",
                "Monthly vendor audit review",
                "Automated duplicate vendor detection"
            ],
            recommended_actions=[
                "Remove payment execution from user",
                "Implement payment approval workflow",
                "Assign to different cost centers"
            ]
        ))

        self.add_rule(RiskRule(
            rule_id="FI_P2P_002",
            name="Purchase to Pay - PO Creation & Goods Receipt",
            description="User can create purchase orders AND post goods receipts",
            rule_type=RuleType.SOD,
            severity=RiskSeverity.HIGH,
            risk_category=RiskCategory.PROCUREMENT,
            conflicts=[
                ConflictSet(
                    name="PO Creation vs Goods Receipt",
                    description="Segregation between purchasing and warehouse receipt",
                    function_a_name="Purchase Order Creation",
                    function_a_entitlements=[
                        Entitlement(auth_object="S_TCODE", field="TCD", value="ME21N"),
                        Entitlement(auth_object="S_TCODE", field="TCD", value="ME22N"),
                    ],
                    function_b_name="Goods Receipt Posting",
                    function_b_entitlements=[
                        Entitlement(auth_object="S_TCODE", field="TCD", value="MIGO"),
                        Entitlement(auth_object="S_TCODE", field="TCD", value="MB01"),
                    ]
                )
            ],
            business_justification="Prevents fraudulent goods receipt against fictitious or inflated POs",
            mitigation_controls=[
                "Three-way match enforcement",
                "Receipt confirmation workflow",
                "Inventory count reconciliation"
            ]
        ))

        self.add_rule(RiskRule(
            rule_id="FI_GL_001",
            name="General Ledger - Post & Park Journal Entries",
            description="User can both post and park journal entries",
            rule_type=RuleType.SOD,
            severity=RiskSeverity.HIGH,
            risk_category=RiskCategory.FINANCIAL,
            conflicts=[
                ConflictSet(
                    name="Journal Entry Posting vs Parking",
                    description="Segregation between parking and final posting of journals",
                    function_a_name="Park Journal Entry",
                    function_a_entitlements=[
                        Entitlement(auth_object="S_TCODE", field="TCD", value="FBV1"),
                        Entitlement(auth_object="S_TCODE", field="TCD", value="F-65"),
                    ],
                    function_b_name="Post Journal Entry",
                    function_b_entitlements=[
                        Entitlement(auth_object="S_TCODE", field="TCD", value="F-02"),
                        Entitlement(auth_object="S_TCODE", field="TCD", value="FB01"),
                        Entitlement(auth_object="S_TCODE", field="TCD", value="FBV2"),
                    ]
                )
            ],
            business_justification="Dual control over journal entries prevents unauthorized postings"
        ))

        # HR/Payroll Rules
        self.add_rule(RiskRule(
            rule_id="HR_PAY_001",
            name="Payroll - Change Employee Bank & Run Payroll",
            description="User can modify employee bank details AND execute payroll runs",
            rule_type=RuleType.SOD,
            severity=RiskSeverity.CRITICAL,
            risk_category=RiskCategory.HR_PAYROLL,
            conflicts=[
                ConflictSet(
                    name="Bank Maintenance vs Payroll Execution",
                    description="Segregation between HR master data and payroll processing",
                    function_a_name="Employee Bank Details Maintenance",
                    function_a_entitlements=[
                        Entitlement(auth_object="S_TCODE", field="TCD", value="PA30"),
                        Entitlement(auth_object="P_ORGIN", field="INFTY", value="0009"),
                    ],
                    function_b_name="Payroll Execution",
                    function_b_entitlements=[
                        Entitlement(auth_object="S_TCODE", field="TCD", value="PC00_M99_CALC"),
                        Entitlement(auth_object="S_TCODE", field="TCD", value="PC00_M99_CIPE"),
                    ]
                )
            ],
            business_justification="Prevents payroll fraud through unauthorized bank detail changes",
            mitigation_controls=[
                "Bank change audit trail review",
                "Employee self-service for bank changes",
                "Pre-payroll audit report"
            ]
        ))

        # IT Security/Basis Rules
        self.add_rule(RiskRule(
            rule_id="IT_SEC_001",
            name="Security - User Administration & Role Assignment",
            description="User can create users AND assign roles",
            rule_type=RuleType.SOD,
            severity=RiskSeverity.CRITICAL,
            risk_category=RiskCategory.IT_SECURITY,
            conflicts=[
                ConflictSet(
                    name="User Creation vs Role Assignment",
                    description="Segregation between user provisioning and authorization",
                    function_a_name="User Creation/Maintenance",
                    function_a_entitlements=[
                        Entitlement(auth_object="S_TCODE", field="TCD", value="SU01"),
                        Entitlement(auth_object="S_USER_GRP", field="ACTVT", value="01"),
                    ],
                    function_b_name="Role Assignment",
                    function_b_entitlements=[
                        Entitlement(auth_object="S_TCODE", field="TCD", value="SU01"),
                        Entitlement(auth_object="S_USER_AGR", field="ACTVT", value="22"),
                    ]
                )
            ],
            business_justification="Prevents unauthorized elevation of privileges through user/role manipulation"
        ))

        # Sensitive Access Rules
        self.add_rule(RiskRule(
            rule_id="IT_SENS_001",
            name="Sensitive - Debug/Replace in Production",
            description="User has debug and replace capability in production",
            rule_type=RuleType.SENSITIVE,
            severity=RiskSeverity.CRITICAL,
            risk_category=RiskCategory.IT_SECURITY,
            sensitive_entitlements=[
                Entitlement(auth_object="S_DEVELOP", field="ACTVT", value="02"),
                Entitlement(auth_object="S_DEVELOP", field="OBJTYPE", value="DEBUG"),
            ],
            business_justification="Debug with replace allows runtime code modification, bypassing all controls",
            mitigation_controls=[
                "Emergency access only via firefighter",
                "Full session recording",
                "Management notification"
            ]
        ))

        self.add_rule(RiskRule(
            rule_id="IT_SENS_002",
            name="Sensitive - Direct Table Modification",
            description="User can directly modify database tables",
            rule_type=RuleType.SENSITIVE,
            severity=RiskSeverity.CRITICAL,
            risk_category=RiskCategory.IT_SECURITY,
            sensitive_entitlements=[
                Entitlement(auth_object="S_TCODE", field="TCD", value="SE16N"),
                Entitlement(auth_object="S_TABU_DIS", field="ACTVT", value="02"),
            ],
            business_justification="Direct table access bypasses all application-level controls and audit trails"
        ))

        logger.info(f"Loaded {len(self.rules)} default SAP GRC rules")

    def add_rule(self, rule: RiskRule):
        """Add a rule to the engine with indexing"""
        self.rules[rule.rule_id] = rule

        # Index by category
        if rule.risk_category not in self.rule_index_by_category:
            self.rule_index_by_category[rule.risk_category] = []
        self.rule_index_by_category[rule.risk_category].append(rule.rule_id)

        # Index by type
        if rule.rule_type not in self.rule_index_by_type:
            self.rule_index_by_type[rule.rule_type] = []
        self.rule_index_by_type[rule.rule_type].append(rule.rule_id)

        # Add to graph
        if HAS_NETWORKX:
            self.rule_graph.add_node(rule.rule_id, **{
                "name": rule.name,
                "severity": rule.severity.value,
                "category": rule.risk_category.value
            })

        self.stats["rules_loaded"] += 1

    def load_rules_from_file(self, filepath: str):
        """Load rules from YAML or JSON file"""
        path = Path(filepath)

        if not path.exists():
            raise FileNotFoundError(f"Rules file not found: {filepath}")

        with open(path, 'r', encoding='utf-8') as f:
            if path.suffix in ['.yaml', '.yml']:
                data = yaml.safe_load(f)
            else:
                data = json.load(f)

        for rule_data in data.get('rules', []):
            rule = self._parse_rule_from_dict(rule_data)
            self.add_rule(rule)

        logger.info(f"Loaded {len(data.get('rules', []))} rules from {filepath}")

    def _parse_rule_from_dict(self, data: Dict) -> RiskRule:
        """Parse a rule from dictionary format"""
        # Parse conflicts
        conflicts = []
        for conflict_data in data.get('conflicts', []):
            func_a_entitlements = [
                Entitlement(**e) for e in conflict_data.get('function_a_entitlements', [])
            ]
            func_b_entitlements = [
                Entitlement(**e) for e in conflict_data.get('function_b_entitlements', [])
            ]

            # Also support nested entitlements format from YAML
            for func_data in conflict_data.get('functions', []):
                if func_data.get('side') == 'A':
                    func_a_entitlements = [
                        Entitlement(**e) for e in func_data.get('entitlements', [])
                    ]
                elif func_data.get('side') == 'B':
                    func_b_entitlements = [
                        Entitlement(**e) for e in func_data.get('entitlements', [])
                    ]

            conflicts.append(ConflictSet(
                name=conflict_data.get('name', ''),
                description=conflict_data.get('description', ''),
                function_a_name=conflict_data.get('function_a_name', ''),
                function_a_entitlements=func_a_entitlements,
                function_b_name=conflict_data.get('function_b_name', ''),
                function_b_entitlements=func_b_entitlements
            ))

        # Parse sensitive entitlements
        sensitive_entitlements = [
            Entitlement(**e) for e in data.get('sensitive_entitlements', [])
        ]

        return RiskRule(
            rule_id=data['rule_id'],
            name=data['name'],
            description=data.get('description', ''),
            rule_type=RuleType(data.get('rule_type', 'segregation_of_duties')),
            severity=RiskSeverity[data.get('severity', 'MEDIUM')],
            risk_category=RiskCategory(data.get('risk_category', 'Custom')),
            conflicts=conflicts,
            sensitive_entitlements=sensitive_entitlements,
            business_justification=data.get('business_justification', ''),
            mitigation_controls=data.get('mitigation_controls', []),
            recommended_actions=data.get('recommended_actions', []),
            applies_to_systems=data.get('applies_to_systems', ['*']),
            applies_to_departments=data.get('applies_to_departments', ['*']),
            exception_users=data.get('exception_users', []),
            exception_roles=data.get('exception_roles', []),
            enabled=data.get('enabled', True),
            version=data.get('version', '1.0')
        )

    def evaluate_user(self,
                      user: UserAccess,
                      rule_ids: Optional[List[str]] = None,
                      include_mitigated: bool = False) -> List[RiskViolation]:
        """
        Evaluate a user's access against all applicable rules.

        Args:
            user: UserAccess object with entitlements
            rule_ids: Optional list of specific rules to check (default: all)
            include_mitigated: Whether to include violations with active mitigations

        Returns:
            List of RiskViolation objects
        """
        violations = []
        rules_to_check = rule_ids or list(self.rules.keys())

        for rule_id in rules_to_check:
            rule = self.rules.get(rule_id)
            if not rule:
                continue

            if not rule.is_applicable(user):
                continue

            # Check based on rule type
            if rule.rule_type == RuleType.SOD:
                rule_violations = self._check_sod_rule(rule, user)
            elif rule.rule_type == RuleType.SENSITIVE:
                rule_violations = self._check_sensitive_rule(rule, user)
            else:
                continue  # Other rule types not yet implemented

            violations.extend(rule_violations)

        self.stats["evaluations_performed"] += 1
        self.stats["violations_found"] += len(violations)

        return violations

    def _check_sod_rule(self, rule: RiskRule, user: UserAccess) -> List[RiskViolation]:
        """Check SoD conflicts for a rule"""
        violations = []

        for conflict in rule.conflicts:
            result = conflict.check_conflict(user.entitlements)

            if result.get("has_conflict"):
                violation = RiskViolation(
                    violation_id=str(uuid.uuid4()),
                    rule_id=rule.rule_id,
                    rule_name=rule.name,
                    rule_type=rule.rule_type,
                    severity=rule.severity,
                    user_id=user.user_id,
                    username=user.username,
                    conflicting_entitlements=[
                        result["function_a"],
                        result["function_b"]
                    ],
                    risk_category=rule.risk_category,
                    business_impact=rule.business_justification,
                    recommended_actions=rule.recommended_actions,
                    mitigation_controls=rule.mitigation_controls
                )
                violations.append(violation)

        return violations

    def _check_sensitive_rule(self, rule: RiskRule, user: UserAccess) -> List[RiskViolation]:
        """Check sensitive access for a rule"""
        violations = []

        user_keys = {e.to_key() for e in user.entitlements}
        sensitive_keys = {e.to_key() for e in rule.sensitive_entitlements}

        if sensitive_keys.issubset(user_keys):
            violation = RiskViolation(
                violation_id=str(uuid.uuid4()),
                rule_id=rule.rule_id,
                rule_name=rule.name,
                rule_type=rule.rule_type,
                severity=rule.severity,
                user_id=user.user_id,
                username=user.username,
                conflicting_entitlements=[{
                    "type": "sensitive_access",
                    "entitlements": list(sensitive_keys)
                }],
                risk_category=rule.risk_category,
                business_impact=rule.business_justification,
                recommended_actions=rule.recommended_actions,
                mitigation_controls=rule.mitigation_controls
            )
            violations.append(violation)

        return violations

    def evaluate_batch(self,
                       users: List[UserAccess],
                       rule_ids: Optional[List[str]] = None) -> Dict[str, List[RiskViolation]]:
        """
        Evaluate multiple users in batch.

        Returns dict mapping user_id to list of violations.
        """
        results = {}

        for user in users:
            violations = self.evaluate_user(user, rule_ids)
            if violations:
                results[user.user_id] = violations

        return results

    def get_risk_summary(self,
                        violations: List[RiskViolation]) -> Dict[str, Any]:
        """Generate summary statistics for violations"""
        if not violations:
            return {
                "total_violations": 0,
                "by_severity": {},
                "by_category": {},
                "aggregate_risk_score": 0
            }

        by_severity = {}
        by_category = {}

        for v in violations:
            sev_name = v.severity.name
            by_severity[sev_name] = by_severity.get(sev_name, 0) + 1

            cat_name = v.risk_category.value
            by_category[cat_name] = by_category.get(cat_name, 0) + 1

        # Calculate aggregate risk score (weighted by severity)
        total_score = sum(v.severity.value for v in violations)
        max_possible = len(violations) * 100

        return {
            "total_violations": len(violations),
            "by_severity": by_severity,
            "by_category": by_category,
            "aggregate_risk_score": round((total_score / max_possible) * 100, 2) if max_possible > 0 else 0,
            "highest_severity": max(v.severity.value for v in violations),
            "unique_rules_triggered": len(set(v.rule_id for v in violations))
        }

    def export_rules(self, filepath: str, format: str = "yaml"):
        """Export all rules to file"""
        rules_data = []

        for rule in self.rules.values():
            rule_dict = {
                "rule_id": rule.rule_id,
                "name": rule.name,
                "description": rule.description,
                "rule_type": rule.rule_type.value,
                "severity": rule.severity.name,
                "risk_category": rule.risk_category.value,
                "business_justification": rule.business_justification,
                "mitigation_controls": rule.mitigation_controls,
                "enabled": rule.enabled,
                "version": rule.version
            }

            # Add conflicts for SoD rules
            if rule.conflicts:
                rule_dict["conflicts"] = []
                for conflict in rule.conflicts:
                    rule_dict["conflicts"].append({
                        "name": conflict.name,
                        "function_a_name": conflict.function_a_name,
                        "function_a_entitlements": [
                            {"auth_object": e.auth_object, "field": e.field, "value": e.value}
                            for e in conflict.function_a_entitlements
                        ],
                        "function_b_name": conflict.function_b_name,
                        "function_b_entitlements": [
                            {"auth_object": e.auth_object, "field": e.field, "value": e.value}
                            for e in conflict.function_b_entitlements
                        ]
                    })

            rules_data.append(rule_dict)

        with open(filepath, 'w', encoding='utf-8') as f:
            if format == "yaml":
                yaml.dump({"rules": rules_data}, f, default_flow_style=False, sort_keys=False)
            else:
                json.dump({"rules": rules_data}, f, indent=2)

        logger.info(f"Exported {len(rules_data)} rules to {filepath}")

    def get_statistics(self) -> Dict[str, Any]:
        """Get engine statistics"""
        return {
            **self.stats,
            "rules_by_category": {
                cat.value: len(ids) for cat, ids in self.rule_index_by_category.items()
            },
            "rules_by_type": {
                typ.value: len(ids) for typ, ids in self.rule_index_by_type.items()
            }
        }
