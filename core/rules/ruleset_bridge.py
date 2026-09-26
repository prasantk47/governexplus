# core/rules/ruleset_bridge.py
# Loads the full SoDRulesetLibrary (121 delivered rules) into the runtime
# RuleEngine, converting SoDRule -> RiskRule.
#
# Integration (one line in RuleEngine.__init__, after _load_default_sap_rules):
#
#     from core.rules.ruleset_bridge import load_full_ruleset
#     load_full_ruleset(self)
#
# Idempotent: existing rule_ids are not overwritten, so custom/tenant rules win.

import logging
from typing import TYPE_CHECKING

from core.rules.models import (
    RiskSeverity, RiskCategory, RuleType, Entitlement, ConflictSet,
)
from core.rules.sod_ruleset import (
    SoDRulesetLibrary, SoDRule, RiskLevel, BusinessProcess, BusinessFunction,
)

if TYPE_CHECKING:
    from core.rules.engine import RuleEngine

logger = logging.getLogger(__name__)

_SEVERITY = {
    RiskLevel.LOW: RiskSeverity.LOW,
    RiskLevel.MEDIUM: RiskSeverity.MEDIUM,
    RiskLevel.HIGH: RiskSeverity.HIGH,
    RiskLevel.CRITICAL: RiskSeverity.CRITICAL,
}

_CATEGORY = {
    BusinessProcess.FINANCE: RiskCategory.FINANCIAL,
    BusinessProcess.TREASURY: RiskCategory.FINANCIAL,
    BusinessProcess.ASSET: RiskCategory.FINANCIAL,
    BusinessProcess.PROCUREMENT: RiskCategory.PROCUREMENT,
    BusinessProcess.HR: RiskCategory.HR_PAYROLL,
    BusinessProcess.BASIS: RiskCategory.BASIS,
    BusinessProcess.WAREHOUSE: RiskCategory.INVENTORY,
}


def _function_entitlements(fn: BusinessFunction) -> list[Entitlement]:
    """Convert a business function into concrete entitlements."""
    ents: list[Entitlement] = [
        Entitlement(auth_object="S_TCODE", field="TCD", value=tcode)
        for tcode in fn.transaction_codes
    ]
    for ao in fn.auth_objects:
        values = ao.get("values") or [ao.get("value", "*")]
        for v in values:
            ents.append(Entitlement(
                auth_object=ao.get("object", ""),
                field=ao.get("field", ""),
                value=str(v),
            ))
    return ents


def _convert(rule: SoDRule):
    from core.rules.engine import RiskRule  # local import avoids cycle
    conflict = ConflictSet(
        name=rule.name,
        description=rule.description,
        function_a_name=rule.function1.name,
        function_a_entitlements=_function_entitlements(rule.function1),
        function_b_name=rule.function2.name,
        function_b_entitlements=_function_entitlements(rule.function2),
    )
    return RiskRule(
        rule_id=rule.rule_id,
        name=rule.name,
        description=rule.description,
        rule_type=RuleType.SOD,
        severity=_SEVERITY.get(rule.risk_level, RiskSeverity.MEDIUM),
        risk_category=_CATEGORY.get(rule.business_process, RiskCategory.IT_SECURITY),
        conflicts=[conflict],
        business_justification=rule.business_impact or rule.risk_description,
        recommended_actions=[rule.recommendation] if rule.recommendation else [],
        enabled=rule.is_active,
        created_by="sod_ruleset_library",
    )


def load_full_ruleset(engine: "RuleEngine") -> int:
    """Load every library rule the engine doesn't already know. Returns count added."""
    library = SoDRulesetLibrary()
    added = 0
    for sod_rule in library.get_all_rules(active_only=False):
        if sod_rule.rule_id in engine.rules:
            continue  # custom/tenant overrides win
        risk_rule = _convert(sod_rule)
        engine.rules[risk_rule.rule_id] = risk_rule
        engine.rule_index_by_category.setdefault(risk_rule.risk_category, []).append(risk_rule.rule_id)
        engine.rule_index_by_type.setdefault(risk_rule.rule_type, []).append(risk_rule.rule_id)
        added += 1
    engine.stats["rules_loaded"] = len(engine.rules)
    logger.info("ruleset_bridge: %d library rules loaded (engine total: %d)",
                added, len(engine.rules))
    return added
