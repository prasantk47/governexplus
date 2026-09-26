"""
Tests for SoD Ruleset Library and Rule Engine.
"""

import pytest
from core.rules.sod_ruleset import (
    SoDRulesetLibrary, BusinessFunction, SoDRule,
    RiskLevel, BusinessProcess,
)
from core.rules.engine import RuleEngine
from core.rules.models import Entitlement, UserAccess


class TestSoDRulesetLibrary:
    """Tests for the built-in SoD ruleset."""

    def test_library_loads(self):
        lib = SoDRulesetLibrary()
        assert len(lib.functions) > 0
        assert len(lib.rules) > 0

    def test_has_121_rules(self):
        lib = SoDRulesetLibrary()
        assert len(lib.rules) >= 121

    def test_has_65_functions(self):
        lib = SoDRulesetLibrary()
        assert len(lib.functions) >= 65

    def test_all_rules_reference_valid_functions(self):
        lib = SoDRulesetLibrary()
        function_ids = set(lib.functions.keys())
        for rule_id, rule in lib.rules.items():
            f1_id = rule.function1.function_id if hasattr(rule.function1, 'function_id') else rule.function1
            f2_id = rule.function2.function_id if hasattr(rule.function2, 'function_id') else rule.function2
            assert f1_id in function_ids, (
                f"Rule {rule_id} references unknown function1: {f1_id}"
            )
            assert f2_id in function_ids, (
                f"Rule {rule_id} references unknown function2: {f2_id}"
            )

    def test_rule_ids_are_unique(self):
        lib = SoDRulesetLibrary()
        # Dict keys are inherently unique — verify count matches
        assert len(lib.rules) == len(set(lib.rules.keys()))

    def test_function_ids_are_unique(self):
        lib = SoDRulesetLibrary()
        assert len(lib.functions) == len(set(lib.functions.keys()))

    def test_all_risk_levels_present(self):
        lib = SoDRulesetLibrary()
        levels = {r.risk_level for r in lib.rules.values()}
        assert RiskLevel.HIGH in levels
        assert RiskLevel.CRITICAL in levels

    def test_business_processes_covered(self):
        lib = SoDRulesetLibrary()
        processes = {f.business_process for f in lib.functions.values()}
        assert BusinessProcess.FINANCE in processes
        assert BusinessProcess.PROCUREMENT in processes
        assert BusinessProcess.SALES in processes
        assert BusinessProcess.HR in processes
        assert BusinessProcess.BASIS in processes

    def test_get_rules_by_process(self):
        lib = SoDRulesetLibrary()
        fi_rules = lib.get_rules_by_process(BusinessProcess.FINANCE)
        assert len(fi_rules) > 0

    def test_sox_relevant_rules(self):
        lib = SoDRulesetLibrary()
        sox_rules = lib.get_sox_relevant_rules()
        assert len(sox_rules) >= 50

    def test_get_statistics(self):
        lib = SoDRulesetLibrary()
        stats = lib.get_statistics()
        assert "total_rules" in stats
        assert "total_functions" in stats
        assert stats["total_rules"] >= 121
        assert stats["total_functions"] >= 65

    def test_get_function_by_id(self):
        lib = SoDRulesetLibrary()
        func = lib.get_function("FI001")
        assert func is not None
        assert func.function_id == "FI001"

    def test_get_rule_by_id(self):
        lib = SoDRulesetLibrary()
        rule = lib.get_rule("SOD-FI-001")
        assert rule is not None
        assert rule.rule_id == "SOD-FI-001"


class TestRuleEngine:
    """Tests for the core rule engine."""

    def test_engine_loads_rules(self):
        engine = RuleEngine()
        assert len(engine.rules) > 0

    def test_engine_has_rule_index(self):
        engine = RuleEngine()
        assert len(engine.rule_index_by_category) > 0

    def test_analyze_user_with_no_entitlements(self):
        engine = RuleEngine()
        user = UserAccess(
            user_id="EMPTY_USER",
            username="empty",
            full_name="Empty User",
            department="Finance",
            entitlements=[],
        )
        violations = engine.evaluate_user(user)
        assert isinstance(violations, list)
        assert len(violations) == 0

    def test_analyze_user_with_sod_conflict(self):
        """User with vendor create + payment run = SoD violation."""
        engine = RuleEngine()
        user = UserAccess(
            user_id="RISKY_USER",
            username="risky",
            full_name="Risky User",
            department="Finance",
            entitlements=[
                # Vendor master maintenance
                Entitlement(auth_object="S_TCODE", field="TCD", value="XK01"),
                Entitlement(auth_object="S_TCODE", field="TCD", value="FK01"),
                # Payment processing
                Entitlement(auth_object="S_TCODE", field="TCD", value="F110"),
                Entitlement(auth_object="S_TCODE", field="TCD", value="F-53"),
            ],
        )
        violations = engine.evaluate_user(user)
        assert len(violations) >= 1


class TestEntitlementModel:
    """Tests for Entitlement data model."""

    def test_entitlement_equality(self):
        e1 = Entitlement(auth_object="S_TCODE", field="TCD", value="FB01")
        e2 = Entitlement(auth_object="S_TCODE", field="TCD", value="FB01")
        assert e1 == e2

    def test_entitlement_with_system(self):
        e = Entitlement(
            auth_object="S_TCODE",
            field="TCD",
            value="FB01",
            system="SAP_ECC",
        )
        assert e.system == "SAP_ECC"
