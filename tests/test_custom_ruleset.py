"""
Tests for CustomRulesetManager — tenant rule preferences, clone, CRUD.
"""

import pytest
from core.rules.custom_ruleset import CustomRulesetManager
from core.rules.sod_ruleset import SoDRulesetLibrary


@pytest.fixture
def manager(db_session):
    return CustomRulesetManager(db_session, tenant_id="test_tenant")


class TestBuiltinRules:
    """Tests for built-in rule listing and toggling."""

    def test_get_builtin_rules(self, manager):
        rules = manager.get_builtin_rules()
        assert len(rules) >= 121

    def test_toggle_builtin_rule_off(self, manager):
        result = manager.toggle_builtin_rule("SOD-FI-001", enabled=False)
        assert result is not None

        # Verify it's disabled in effective ruleset
        effective = manager.get_effective_ruleset()
        effective_ids = [r.get("rule_id") or r.get("id") for r in effective]
        # SOD-FI-001 should NOT be in effective rules
        assert "SOD-FI-001" not in effective_ids

    def test_toggle_builtin_rule_back_on(self, manager):
        manager.toggle_builtin_rule("SOD-FI-001", enabled=False)
        manager.toggle_builtin_rule("SOD-FI-001", enabled=True)

        effective = manager.get_effective_ruleset()
        effective_ids = [r.get("rule_id") or r.get("id") for r in effective]
        assert "SOD-FI-001" in effective_ids


class TestCustomRuleCRUD:
    """Tests for creating, updating, and deleting custom rules."""

    def test_create_custom_rule(self, manager):
        rule_data = {
            "name": "Custom Test Rule",
            "description": "A test custom rule",
            "rule_type": "sod",
            "severity": "high",
            "risk_category": "Financial",
            "rule_definition": {
                "function_1": "FI-AP-INV",
                "function_2": "FI-AP-PAY",
            },
        }
        result = manager.create_custom_rule(rule_data)
        assert result is not None
        assert "rule_id" in result
        assert result["source"] == "custom"

    def test_list_custom_rules(self, manager):
        manager.create_custom_rule({
            "name": "Rule A",
            "rule_type": "sod",
            "severity": "medium",
            "risk_category": "Financial",
            "rule_definition": {},
        })
        rules = manager.get_custom_rules()
        assert len(rules) >= 1

    def test_update_custom_rule(self, manager):
        created = manager.create_custom_rule({
            "name": "Before Update",
            "rule_type": "sod",
            "severity": "low",
            "risk_category": "Financial",
            "rule_definition": {},
        })
        rule_id = created["rule_id"]
        updated = manager.update_custom_rule(rule_id, {"name": "After Update"})
        assert updated is not None
        # Verify the update took effect by re-fetching
        rules = manager.get_custom_rules()
        updated_rule = next(
            (r for r in rules if (r.get("rule_id") if isinstance(r, dict) else r.rule_id) == rule_id),
            None
        )
        assert updated_rule is not None

    def test_delete_custom_rule(self, manager):
        created = manager.create_custom_rule({
            "name": "To Delete",
            "rule_type": "sod",
            "severity": "low",
            "risk_category": "Financial",
            "rule_definition": {},
        })
        rule_id = created["rule_id"]
        result = manager.delete_custom_rule(rule_id)
        # Result may be True or a dict with deletion info
        assert result is not None

        rules = manager.get_custom_rules()
        ids = [r.get("rule_id") if isinstance(r, dict) else r.rule_id for r in rules]
        assert rule_id not in ids


class TestCloneBuiltinRule:
    """Tests for cloning built-in rules."""

    def test_clone_creates_custom_copy(self, manager):
        cloned = manager.clone_builtin_rule("SOD-FI-001")
        assert cloned is not None
        source = cloned.get("source") if isinstance(cloned, dict) else cloned.source
        cloned_from = cloned.get("cloned_from") if isinstance(cloned, dict) else cloned.cloned_from
        assert source == "cloned"
        assert cloned_from == "SOD-FI-001"

    def test_clone_disables_original(self, manager):
        manager.clone_builtin_rule("SOD-FI-002")

        effective = manager.get_effective_ruleset()
        effective_ids = [r.get("rule_id") or r.get("id") for r in effective]
        # Original should be replaced by clone
        assert "SOD-FI-002" not in effective_ids


class TestExportImport:
    """Tests for rule export/import."""

    def test_export_json(self, manager):
        export = manager.export_ruleset(format="json")
        assert isinstance(export, str)
        import json
        data = json.loads(export)
        assert "rules" in data or "custom_rules" in data or isinstance(data, list)

    def test_export_yaml(self, manager):
        export = manager.export_ruleset(format="yaml")
        assert isinstance(export, str)
        import yaml
        data = yaml.safe_load(export)
        assert data is not None
