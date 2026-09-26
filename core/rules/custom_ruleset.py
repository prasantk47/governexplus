"""
Custom Ruleset Manager

Allows tenants to:
1. Use built-in rules (121+ pre-configured SoD rules)
2. Toggle built-in rules on/off per tenant
3. Clone a built-in rule and customize it
4. Create entirely new custom rules
5. Import/export rulesets as YAML or JSON
6. Merge built-in + custom rules for risk analysis
"""

import yaml
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from sqlalchemy.orm import Session

from db.models.risk import RiskRuleModel, TenantRulePreference, RiskSeverityLevel
from core.rules.sod_ruleset import SoDRulesetLibrary, SoDRule, BusinessFunction, RiskLevel

logger = logging.getLogger(__name__)


class CustomRulesetManager:
    """
    Manages the combination of built-in + tenant-specific custom rules.

    Design:
    - Built-in rules live in code (SoDRulesetLibrary) — always available
    - Tenant preferences stored in DB (enable/disable built-ins)
    - Custom rules stored in DB (RiskRuleModel with source='custom'|'cloned')
    - At runtime: merge built-in (filtered by prefs) + custom rules
    """

    def __init__(self, db: Session, tenant_id: str = "tenant_default"):
        self.db = db
        self.tenant_id = tenant_id
        self._builtin = SoDRulesetLibrary()

    # ========================================================================
    # Built-in Rule Management
    # ========================================================================

    def get_builtin_rules(self, include_disabled: bool = False) -> List[Dict]:
        """Get all built-in rules with tenant-specific enable/disable status."""
        prefs = self._get_tenant_preferences()
        disabled_ids = {p.builtin_rule_id for p in prefs if not p.is_enabled}

        result = []
        for rule in self._builtin.get_all_rules(active_only=False):
            rule_dict = rule.to_dict()
            rule_dict["source"] = "builtin"
            rule_dict["is_enabled"] = rule.rule_id not in disabled_ids

            # Check if there's a custom override (clone)
            pref = next((p for p in prefs if p.builtin_rule_id == rule.rule_id), None)
            if pref and pref.custom_override_id:
                rule_dict["has_custom_override"] = True
                rule_dict["custom_override_id"] = pref.custom_override_id

            if include_disabled or rule_dict["is_enabled"]:
                result.append(rule_dict)

        return result

    def toggle_builtin_rule(
        self, rule_id: str, enabled: bool, user_id: str = "", reason: str = ""
    ) -> Dict:
        """Enable or disable a built-in rule for this tenant."""
        # Verify rule exists
        rule = self._builtin.get_rule(rule_id)
        if not rule:
            raise ValueError(f"Built-in rule not found: {rule_id}")

        pref = self.db.query(TenantRulePreference).filter_by(
            tenant_id=self.tenant_id, builtin_rule_id=rule_id
        ).first()

        if pref:
            pref.is_enabled = enabled
            pref.disabled_by = user_id if not enabled else None
            pref.disabled_reason = reason if not enabled else None
        else:
            pref = TenantRulePreference(
                tenant_id=self.tenant_id,
                builtin_rule_id=rule_id,
                is_enabled=enabled,
                disabled_by=user_id if not enabled else None,
                disabled_reason=reason if not enabled else None,
            )
            self.db.add(pref)

        self.db.commit()
        return {"rule_id": rule_id, "is_enabled": enabled, "source": "builtin"}

    def bulk_toggle_rules(
        self, rule_ids: List[str], enabled: bool, user_id: str = ""
    ) -> Dict:
        """Enable or disable multiple built-in rules at once."""
        results = []
        for rule_id in rule_ids:
            try:
                r = self.toggle_builtin_rule(rule_id, enabled, user_id)
                results.append(r)
            except ValueError:
                results.append({"rule_id": rule_id, "error": "not found"})
        return {"updated": len([r for r in results if "error" not in r]), "results": results}

    # ========================================================================
    # Clone Built-in Rule
    # ========================================================================

    def clone_builtin_rule(
        self, rule_id: str, user_id: str = "", modifications: Dict = None
    ) -> Dict:
        """
        Clone a built-in rule to create a tenant-customizable copy.

        - The original built-in rule is disabled for this tenant
        - A new custom rule is created with the same definition
        - The tenant can then modify the cloned rule freely
        """
        rule = self._builtin.get_rule(rule_id)
        if not rule:
            raise ValueError(f"Built-in rule not found: {rule_id}")

        # Create the custom clone
        rule_dict = rule.to_dict()
        mods = modifications or {}

        custom_rule = RiskRuleModel(
            tenant_id=self.tenant_id,
            rule_id=f"CUST-{rule_id}",
            name=mods.get("name", f"[Custom] {rule.name}"),
            description=mods.get("description", rule.description),
            rule_type="sod",
            severity=self._map_risk_level(mods.get("risk_level", rule.risk_level.value)),
            risk_category=rule.business_process.value,
            rule_definition={
                "function1": rule_dict["function1"],
                "function2": rule_dict["function2"],
                **{k: v for k, v in mods.items()
                   if k not in ("name", "description", "risk_level")},
            },
            business_justification=mods.get("risk_description", rule.risk_description),
            mitigation_controls=[rule.recommendation] if rule.recommendation else [],
            recommended_actions=[rule.recommendation] if rule.recommendation else [],
            is_enabled=True,
            version="1.0",
            created_by=user_id,
            source="cloned",
            cloned_from=rule_id,
        )
        self.db.add(custom_rule)
        self.db.flush()  # Get the ID

        # Disable the original built-in and link to clone
        self.toggle_builtin_rule(rule_id, enabled=False, user_id=user_id,
                                 reason=f"Cloned to custom rule CUST-{rule_id}")
        pref = self.db.query(TenantRulePreference).filter_by(
            tenant_id=self.tenant_id, builtin_rule_id=rule_id
        ).first()
        if pref:
            pref.custom_override_id = custom_rule.id

        self.db.commit()
        return {
            "custom_rule_id": custom_rule.rule_id,
            "db_id": custom_rule.id,
            "cloned_from": rule_id,
            "source": "cloned",
            "message": f"Built-in rule {rule_id} cloned and disabled. Edit CUST-{rule_id} freely."
        }

    # ========================================================================
    # Custom Rule CRUD
    # ========================================================================

    def create_custom_rule(self, rule_data: Dict, user_id: str = "") -> Dict:
        """Create a brand-new custom rule for this tenant."""
        rule_id = rule_data.get("rule_id")
        if not rule_id:
            # Auto-generate
            count = self.db.query(RiskRuleModel).filter_by(
                tenant_id=self.tenant_id
            ).count()
            rule_id = f"CUST-{self.tenant_id[:8].upper()}-{count + 1:03d}"

        custom_rule = RiskRuleModel(
            tenant_id=self.tenant_id,
            rule_id=rule_id,
            name=rule_data["name"],
            description=rule_data.get("description", ""),
            rule_type=rule_data.get("rule_type", "sod"),
            severity=self._map_risk_level(rule_data.get("severity", "high")),
            risk_category=rule_data.get("risk_category", "GEN"),
            rule_definition=rule_data.get("rule_definition", {}),
            business_justification=rule_data.get("business_justification", ""),
            mitigation_controls=rule_data.get("mitigation_controls", []),
            recommended_actions=rule_data.get("recommended_actions", []),
            applies_to_systems=rule_data.get("applies_to_systems", ["*"]),
            applies_to_departments=rule_data.get("applies_to_departments", ["*"]),
            exception_users=rule_data.get("exception_users", []),
            exception_roles=rule_data.get("exception_roles", []),
            is_enabled=rule_data.get("is_enabled", True),
            effective_date=rule_data.get("effective_date"),
            expiry_date=rule_data.get("expiry_date"),
            version="1.0",
            created_by=user_id,
            source="custom",
        )
        self.db.add(custom_rule)
        self.db.commit()

        return {"rule_id": custom_rule.rule_id, "db_id": custom_rule.id, "source": "custom"}

    def update_custom_rule(self, rule_id: str, updates: Dict, user_id: str = "") -> Dict:
        """Update an existing custom rule."""
        rule = self.db.query(RiskRuleModel).filter_by(
            tenant_id=self.tenant_id, rule_id=rule_id
        ).first()
        if not rule:
            raise ValueError(f"Custom rule not found: {rule_id}")
        if rule.source == "builtin":
            raise ValueError("Cannot edit built-in rules directly. Clone it first.")

        for key, value in updates.items():
            if key == "severity":
                rule.severity = self._map_risk_level(value)
            elif key == "rule_definition":
                rule.rule_definition = value
            elif hasattr(rule, key) and key not in ("id", "tenant_id", "source", "cloned_from"):
                setattr(rule, key, value)

        rule.last_modified_by = user_id
        rule.version = self._increment_version(rule.version)
        self.db.commit()
        return {"rule_id": rule_id, "version": rule.version, "updated": True}

    def delete_custom_rule(self, rule_id: str) -> Dict:
        """Delete a custom rule. If it was cloned, re-enable the original."""
        rule = self.db.query(RiskRuleModel).filter_by(
            tenant_id=self.tenant_id, rule_id=rule_id
        ).first()
        if not rule:
            raise ValueError(f"Custom rule not found: {rule_id}")
        if rule.source == "builtin":
            raise ValueError("Cannot delete built-in rules. Disable them instead.")

        # If cloned, re-enable the original built-in
        if rule.cloned_from:
            pref = self.db.query(TenantRulePreference).filter_by(
                tenant_id=self.tenant_id, builtin_rule_id=rule.cloned_from
            ).first()
            if pref:
                pref.is_enabled = True
                pref.custom_override_id = None
                pref.disabled_reason = None

        self.db.delete(rule)
        self.db.commit()
        return {"rule_id": rule_id, "deleted": True, "restored_builtin": rule.cloned_from}

    def get_custom_rules(self, include_disabled: bool = False) -> List[Dict]:
        """Get all custom rules for this tenant."""
        query = self.db.query(RiskRuleModel).filter_by(tenant_id=self.tenant_id)
        if not include_disabled:
            query = query.filter_by(is_enabled=True)

        return [self._rule_model_to_dict(r) for r in query.all()]

    # ========================================================================
    # Merged Ruleset — What the risk engine actually uses
    # ========================================================================

    def get_effective_ruleset(self) -> List[Dict]:
        """
        Get the complete effective ruleset for this tenant.
        Merges: enabled built-in rules + enabled custom rules.
        This is what the risk analysis engine uses.
        """
        rules = []

        # Built-in rules (filtered by tenant preferences)
        rules.extend(self.get_builtin_rules(include_disabled=False))

        # Custom rules
        rules.extend(self.get_custom_rules(include_disabled=False))

        return rules

    def get_ruleset_stats(self) -> Dict:
        """Get statistics about the tenant's ruleset."""
        builtin_all = self._builtin.get_all_rules(active_only=False)
        prefs = self._get_tenant_preferences()
        disabled_ids = {p.builtin_rule_id for p in prefs if not p.is_enabled}
        custom_count = self.db.query(RiskRuleModel).filter_by(
            tenant_id=self.tenant_id, is_enabled=True
        ).count()
        cloned_count = self.db.query(RiskRuleModel).filter_by(
            tenant_id=self.tenant_id, source="cloned"
        ).count()

        return {
            "builtin_total": len(builtin_all),
            "builtin_enabled": len(builtin_all) - len(disabled_ids),
            "builtin_disabled": len(disabled_ids),
            "custom_rules": custom_count,
            "cloned_rules": cloned_count,
            "total_effective": len(builtin_all) - len(disabled_ids) + custom_count,
        }

    # ========================================================================
    # Import / Export
    # ========================================================================

    def export_ruleset(self, format: str = "yaml", include_builtins: bool = False) -> str:
        """
        Export the tenant's custom rules as YAML or JSON.
        Optionally include built-in rule preferences.
        """
        export_data = {
            "tenant_id": self.tenant_id,
            "exported_at": datetime.utcnow().isoformat(),
            "format_version": "1.0",
            "custom_rules": self.get_custom_rules(include_disabled=True),
        }

        if include_builtins:
            prefs = self._get_tenant_preferences()
            export_data["builtin_preferences"] = [
                {
                    "rule_id": p.builtin_rule_id,
                    "is_enabled": p.is_enabled,
                    "reason": p.disabled_reason,
                }
                for p in prefs
            ]

        if format == "yaml":
            return yaml.dump(export_data, default_flow_style=False, sort_keys=False)
        return json.dumps(export_data, indent=2, default=str)

    def import_ruleset(
        self, content: str, format: str = "yaml",
        mode: str = "merge", user_id: str = ""
    ) -> Dict:
        """
        Import rules from YAML or JSON.

        Modes:
        - merge: Add imported rules, skip duplicates
        - replace: Delete all existing custom rules, import fresh
        - append: Add all imported rules with new IDs (no duplicate check)
        """
        if format == "yaml":
            data = yaml.safe_load(content)
        else:
            data = json.loads(content)

        rules = data.get("custom_rules", data.get("rules", []))
        prefs = data.get("builtin_preferences", [])

        if mode == "replace":
            self.db.query(RiskRuleModel).filter_by(tenant_id=self.tenant_id).delete()
            self.db.commit()

        imported = 0
        skipped = 0

        for rule_data in rules:
            rule_id = rule_data.get("rule_id", "")

            if mode == "merge":
                exists = self.db.query(RiskRuleModel).filter_by(
                    tenant_id=self.tenant_id, rule_id=rule_id
                ).first()
                if exists:
                    skipped += 1
                    continue

            if mode == "append":
                count = self.db.query(RiskRuleModel).filter_by(
                    tenant_id=self.tenant_id
                ).count()
                rule_data["rule_id"] = f"IMP-{count + imported + 1:03d}"

            self.create_custom_rule(rule_data, user_id=user_id)
            imported += 1

        # Apply built-in preferences if provided
        prefs_applied = 0
        for pref_data in prefs:
            try:
                self.toggle_builtin_rule(
                    pref_data["rule_id"],
                    pref_data.get("is_enabled", True),
                    user_id=user_id,
                    reason=pref_data.get("reason", "Imported")
                )
                prefs_applied += 1
            except ValueError:
                pass

        self.db.commit()
        return {
            "imported": imported,
            "skipped": skipped,
            "preferences_applied": prefs_applied,
            "mode": mode,
        }

    # ========================================================================
    # Private Helpers
    # ========================================================================

    def _get_tenant_preferences(self) -> List[TenantRulePreference]:
        return self.db.query(TenantRulePreference).filter_by(
            tenant_id=self.tenant_id
        ).all()

    def _rule_model_to_dict(self, rule: RiskRuleModel) -> Dict:
        return {
            "rule_id": rule.rule_id,
            "name": rule.name,
            "description": rule.description,
            "rule_type": rule.rule_type,
            "risk_level": rule.severity.value if rule.severity else "medium",
            "risk_category": rule.risk_category,
            "rule_definition": rule.rule_definition,
            "business_justification": rule.business_justification,
            "mitigation_controls": rule.mitigation_controls,
            "recommended_actions": rule.recommended_actions,
            "applies_to_systems": rule.applies_to_systems,
            "exception_users": rule.exception_users,
            "exception_roles": rule.exception_roles,
            "is_enabled": rule.is_enabled,
            "source": rule.source,
            "cloned_from": rule.cloned_from,
            "version": rule.version,
            "created_by": rule.created_by,
            "created_at": rule.created_at.isoformat() if rule.created_at else None,
        }

    @staticmethod
    def _map_risk_level(level: str) -> RiskSeverityLevel:
        mapping = {
            "low": RiskSeverityLevel.LOW,
            "medium": RiskSeverityLevel.MEDIUM,
            "high": RiskSeverityLevel.HIGH,
            "critical": RiskSeverityLevel.CRITICAL,
        }
        return mapping.get(level.lower(), RiskSeverityLevel.MEDIUM)

    @staticmethod
    def _increment_version(version: str) -> str:
        try:
            parts = version.split(".")
            parts[-1] = str(int(parts[-1]) + 1)
            return ".".join(parts)
        except (ValueError, IndexError):
            return "1.1"
