# core/ara/ruleset_bridge.py
# Loads the full delivered SoD library (core/rules/sod_ruleset.py, 121 rules)
# into ARA's runtime RuleEngine, converting library SoDRule -> RuleDefinition.
# Idempotent; existing rule_ids (defaults, tenant customs) are not overwritten.

import logging
from typing import TYPE_CHECKING

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from core.ara.rules import RuleEngine


def load_full_ruleset(engine: "RuleEngine") -> int:
    from core.ara.rules import RuleDefinition, RuleCondition, ConditionOperator
    from core.ara.models import RiskSeverity, RiskCategory
    from core.rules.sod_ruleset import SoDRulesetLibrary, RiskLevel, BusinessProcess

    ANY = getattr(ConditionOperator, "ANY", ConditionOperator.CONTAINS_ANY)

    severity_map = {
        RiskLevel.LOW: getattr(RiskSeverity, "LOW", None),
        RiskLevel.MEDIUM: getattr(RiskSeverity, "MEDIUM", None),
        RiskLevel.HIGH: getattr(RiskSeverity, "HIGH", None),
        RiskLevel.CRITICAL: getattr(RiskSeverity, "CRITICAL", None),
    }
    category_map = {
        BusinessProcess.FINANCE: getattr(RiskCategory, "FINANCIAL", None),
        BusinessProcess.TREASURY: getattr(RiskCategory, "FINANCIAL", None),
        BusinessProcess.ASSET: getattr(RiskCategory, "FINANCIAL", None),
        BusinessProcess.PROCUREMENT: getattr(RiskCategory, "PROCUREMENT",
                                             getattr(RiskCategory, "FINANCIAL", None)),
        BusinessProcess.HR: getattr(RiskCategory, "HR_PAYROLL",
                                    getattr(RiskCategory, "HR", None)),
        BusinessProcess.BASIS: getattr(RiskCategory, "BASIS",
                                       getattr(RiskCategory, "IT_SECURITY", None)),
    }
    default_severity = getattr(RiskSeverity, "HIGH")
    default_category = getattr(RiskCategory, "FINANCIAL")

    def conditions_for(fn) -> list:
        conds = []
        if fn.transaction_codes:
            conds.append(RuleCondition("tcodes", ANY, list(fn.transaction_codes)))
        for ao in fn.auth_objects:
            obj, fld = ao.get("object"), ao.get("field")
            values = ao.get("values") or ([ao["value"]] if ao.get("value") else [])
            if obj and fld and values:
                conds.append(RuleCondition(
                    f"auth_objects.{obj}.{fld}", ANY, [str(v) for v in values]
                ))
        return conds

    library = SoDRulesetLibrary()
    added = 0
    for r in library.get_all_rules(active_only=False):
        if r.rule_id in engine.rules:
            continue
        f1 = conditions_for(r.function1)
        f2 = conditions_for(r.function2)
        if not f1 or not f2:
            continue  # a SoD rule needs both sides to be evaluable
        engine.add_rule(RuleDefinition(
            rule_id=r.rule_id,
            name=r.name,
            description=r.description,
            rule_type="sod",
            function_1_conditions=f1,
            function_2_conditions=f2,
            severity=severity_map.get(r.risk_level) or default_severity,
            category=category_map.get(r.business_process) or default_category,
            business_impact=r.business_impact or r.risk_description,
        ))
        added += 1
    logger.info("ara.ruleset_bridge: %d library rules loaded (engine total: %d)",
                added, len(engine.rules))
    return added
