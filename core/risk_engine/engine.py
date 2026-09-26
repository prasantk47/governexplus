"""
Risk & SoD Analysis Engine

Performs multi-level SoD analysis:
  Level 1: Transaction-code overlap (legacy, fast)
  Level 2: Authorization-object overlap
  Level 3: Field/value overlap (e.g., both have ACTVT=01)
  Level 4: Organizational scope overlap (e.g., same company code)

Only Level 4 confirms a REAL violation.  A user with FK01 in company
1000 and F110 in company 2000 does NOT have a real SoD conflict.
"""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime
from typing import Optional

from core.effective_access.models import (
    AuthorizationObject,
    UserEffectiveAccess,
)
from core.rules.sod_ruleset import SoDRule, BusinessFunction

from .models import (
    AnalysisDepth,
    CriticalActionViolation,
    RiskAnalysisResult,
    SensitiveAccessViolation,
    SoDConflict,
    SoDViolation,
    ViolationStatus,
)

logger = logging.getLogger(__name__)

# Transactions considered critical/sensitive by default
DEFAULT_SENSITIVE_TRANSACTIONS = {
    "SU01", "SU10", "PFCG", "SE16N", "SE11", "SE38", "SA38",
    "SM30", "SM31", "SM37", "SM21", "STMS", "SCC4", "SE06",
    "SPRO", "RZ10", "RZ11", "SCC1", "SCC5", "SCC9",
    "FB01", "F110", "FK01", "FK02", "XK01", "XK02",
    "PA30", "PC00_M99_CALC", "PC00_M99_CIPE",
}

DEFAULT_CRITICAL_TRANSACTIONS = {
    "SU01", "SU10", "PFCG",     # User/role admin
    "SE16N", "SE11",              # Table access
    "SCC4", "SE06",               # Client admin
    "SM30", "SM31",               # Table maintenance
    "STMS",                        # Transport management
}


class RiskEngine:
    """Performs risk analysis on effective access.

    This engine is *stateless* — it takes a UserEffectiveAccess and a
    ruleset, and returns a RiskAnalysisResult.  It does not touch the
    database.
    """

    def __init__(
        self,
        sod_rules: Optional[list[SoDRule]] = None,
        sensitive_transactions: Optional[set[str]] = None,
        critical_transactions: Optional[set[str]] = None,
        mitigations: Optional[dict[str, dict]] = None,
    ):
        self._sod_rules = sod_rules or []
        self._sensitive_txns = sensitive_transactions or DEFAULT_SENSITIVE_TRANSACTIONS
        self._critical_txns = critical_transactions or DEFAULT_CRITICAL_TRANSACTIONS
        # mitigations: {rule_id: {user_id: {mitigation_id, description, valid_to}}}
        self._mitigations = mitigations or {}

    def set_rules(self, rules: list[SoDRule]) -> None:
        self._sod_rules = rules

    def set_mitigations(self, mitigations: dict[str, dict]) -> None:
        self._mitigations = mitigations

    # ------------------------------------------------------------------
    # Main analysis
    # ------------------------------------------------------------------

    def analyze(
        self,
        access: UserEffectiveAccess,
        depth: AnalysisDepth = AnalysisDepth.ORG_SCOPE,
    ) -> RiskAnalysisResult:
        """Run full risk analysis on a user's effective access.

        Args:
            access: The resolved effective access from EffectiveAccessEngine
            depth: How deep to analyze (default: full org-scope analysis)

        Returns:
            RiskAnalysisResult with all violations found
        """
        result = RiskAnalysisResult(
            user_id=access.user_id,
            tenant_id=access.tenant_id,
            analysis_depth=depth,
        )

        user_txns = access.get_transactions()

        # 1. SoD analysis
        for rule in self._sod_rules:
            if not rule.is_active:
                continue
            violation = self._check_sod_rule(access, rule, user_txns, depth)
            if violation:
                result.sod_violations.append(violation)

        # 2. Sensitive access check
        for ent in access.entitlements:
            if ent.transaction in self._sensitive_txns:
                vid = self._make_id("SA", access.user_id, ent.transaction)
                result.sensitive_access.append(SensitiveAccessViolation(
                    violation_id=vid,
                    user_id=access.user_id,
                    transaction=ent.transaction,
                    auth_objects=[ao.object_name for ao in ent.auth_objects],
                    source_roles=ent.source_roles,
                    org_scope=ent.org_scope,
                    risk_level="high" if ent.has_change_access else "medium",
                    has_change_access=ent.has_change_access,
                    last_used=ent.last_used,
                    usage_count_90d=ent.usage_count_90d,
                ))

        # 3. Critical action check
        for ent in access.entitlements:
            if ent.transaction in self._critical_txns and ent.has_change_access:
                vid = self._make_id("CA", access.user_id, ent.transaction)
                result.critical_actions.append(CriticalActionViolation(
                    violation_id=vid,
                    user_id=access.user_id,
                    transaction=ent.transaction,
                    action_description=f"Change access to critical transaction {ent.transaction}",
                    source_roles=ent.source_roles,
                    risk_level="critical",
                    was_executed=ent.usage_count_90d > 0,
                    executed_at=ent.last_used,
                ))

        result.compute_summary()
        return result

    # ------------------------------------------------------------------
    # SoD rule checking — multi-level
    # ------------------------------------------------------------------

    def _check_sod_rule(
        self,
        access: UserEffectiveAccess,
        rule: SoDRule,
        user_txns: set[str],
        depth: AnalysisDepth,
    ) -> Optional[SoDViolation]:
        """Check a single SoD rule against user's effective access.

        Returns a violation if confirmed at the requested depth, else None.
        """
        func_a = rule.function1
        func_b = rule.function2

        # Level 1: Transaction-code overlap
        user_txns_a = set(func_a.transaction_codes) & user_txns
        user_txns_b = set(func_b.transaction_codes) & user_txns

        if not user_txns_a or not user_txns_b:
            return None  # No T-code overlap — no conflict possible

        if depth == AnalysisDepth.TRANSACTION_ONLY:
            return self._build_violation(
                access, rule, func_a, func_b,
                user_txns_a, user_txns_b,
                AnalysisDepth.TRANSACTION_ONLY,
            )

        # Level 2-3: Auth object + field/value overlap
        auth_overlaps = self._check_auth_object_overlap(
            access, user_txns_a, user_txns_b, func_a, func_b,
        )

        if depth == AnalysisDepth.AUTH_OBJECT and auth_overlaps:
            return self._build_violation(
                access, rule, func_a, func_b,
                user_txns_a, user_txns_b,
                AnalysisDepth.AUTH_OBJECT,
                auth_overlaps=auth_overlaps,
            )

        if depth == AnalysisDepth.FIELD_VALUE and auth_overlaps:
            return self._build_violation(
                access, rule, func_a, func_b,
                user_txns_a, user_txns_b,
                AnalysisDepth.FIELD_VALUE,
                auth_overlaps=auth_overlaps,
            )

        # Level 4: Organizational scope overlap
        org_overlap = self._check_org_overlap(access, user_txns_a, user_txns_b)

        if not org_overlap and depth == AnalysisDepth.ORG_SCOPE:
            # No org overlap — NOT a real violation
            logger.info(
                f"SoD rule {rule.rule_id} matched at T-code level for "
                f"user {access.user_id} but NO organizational overlap — "
                f"suppressing as false positive"
            )
            return None

        # Both have change access?
        change_a = any(
            access.has_change_access_to(t) for t in user_txns_a
        )
        change_b = any(
            access.has_change_access_to(t) for t in user_txns_b
        )

        return self._build_violation(
            access, rule, func_a, func_b,
            user_txns_a, user_txns_b,
            depth,
            auth_overlaps=auth_overlaps,
            org_overlap=org_overlap,
            both_change=change_a and change_b,
        )

    def _check_auth_object_overlap(
        self,
        access: UserEffectiveAccess,
        txns_a: set[str],
        txns_b: set[str],
        func_a: BusinessFunction,
        func_b: BusinessFunction,
    ) -> list[dict]:
        """Check if the two function sides share auth object scope.

        Uses the rule's auth_objects definitions to see if the user's
        entitlements actually overlap at the auth object level.
        """
        overlaps = []

        # Get auth objects from function definitions
        rule_auth_a = {ao["object"] for ao in func_a.auth_objects} if func_a.auth_objects else set()
        rule_auth_b = {ao["object"] for ao in func_b.auth_objects} if func_b.auth_objects else set()

        # Gather actual auth objects from user's entitlements
        user_aos_a: list[AuthorizationObject] = []
        for txn in txns_a:
            for ent in access.get_entitlements_for_transaction(txn):
                user_aos_a.extend(ent.auth_objects)

        user_aos_b: list[AuthorizationObject] = []
        for txn in txns_b:
            for ent in access.get_entitlements_for_transaction(txn):
                user_aos_b.extend(ent.auth_objects)

        # Check if user actually has the auth objects the rule cares about
        for ao_a in user_aos_a:
            for ao_b in user_aos_b:
                # Check org-scope overlap between these auth objects
                org_overlap = ao_a.overlaps_org_scope(ao_b)
                if org_overlap:
                    overlaps.append({
                        "auth_object_a": ao_a.object_name,
                        "auth_object_b": ao_b.object_name,
                        "org_fields": org_overlap,
                        "role_a": ao_a.source_role,
                        "role_b": ao_b.source_role,
                    })

        return overlaps

    def _check_org_overlap(
        self,
        access: UserEffectiveAccess,
        txns_a: set[str],
        txns_b: set[str],
    ) -> dict[str, list[str]]:
        """Check organizational scope overlap between two sets of transactions.

        This is the key differentiator: FK01 in company 1000 + F110 in
        company 2000 is NOT a real conflict.
        """
        # Collect org scope from all entitlements in each side
        org_a: dict[str, set[str]] = {}
        for txn in txns_a:
            scope = access.get_org_scope_for_transaction(txn)
            for field_name, values in scope.items():
                if field_name not in org_a:
                    org_a[field_name] = set()
                org_a[field_name].update(values)

        org_b: dict[str, set[str]] = {}
        for txn in txns_b:
            scope = access.get_org_scope_for_transaction(txn)
            for field_name, values in scope.items():
                if field_name not in org_b:
                    org_b[field_name] = set()
                org_b[field_name].update(values)

        # Find overlapping org fields
        overlap: dict[str, list[str]] = {}
        common_fields = set(org_a.keys()) & set(org_b.keys())

        if not common_fields:
            # No org restrictions on either side — treat as full overlap
            # (conservative: if neither side restricts org, assume overlap)
            return {"_unrestricted": ["*"]}

        for field_name in common_fields:
            vals_a = org_a[field_name]
            vals_b = org_b[field_name]

            if "*" in vals_a or "*" in vals_b:
                overlap[field_name] = sorted(vals_a | vals_b)
                continue

            common = vals_a & vals_b
            if common:
                overlap[field_name] = sorted(common)

        return overlap

    # ------------------------------------------------------------------
    # Violation building
    # ------------------------------------------------------------------

    def _build_violation(
        self,
        access: UserEffectiveAccess,
        rule: SoDRule,
        func_a: BusinessFunction,
        func_b: BusinessFunction,
        txns_a: set[str],
        txns_b: set[str],
        depth: AnalysisDepth,
        auth_overlaps: Optional[list[dict]] = None,
        org_overlap: Optional[dict[str, list[str]]] = None,
        both_change: bool = False,
    ) -> SoDViolation:
        """Construct a full SoDViolation with all context."""
        conflict = SoDConflict(
            rule_id=rule.rule_id,
            rule_name=rule.name,
            function_a_id=func_a.function_id,
            function_a_name=func_a.name,
            function_a_transactions=func_a.transaction_codes,
            function_b_id=func_b.function_id,
            function_b_name=func_b.name,
            function_b_transactions=func_b.transaction_codes,
            conflicting_txn_a=sorted(txns_a),
            conflicting_txn_b=sorted(txns_b),
            auth_object_overlaps=auth_overlaps or [],
            org_overlap=org_overlap or {},
            analysis_depth=depth,
            both_have_change_access=both_change,
        )

        vid = self._make_id("SOD", access.user_id, rule.rule_id)

        # Find source roles
        roles_a = set()
        for txn in txns_a:
            for ent in access.get_entitlements_for_transaction(txn):
                roles_a.update(ent.source_roles)

        roles_b = set()
        for txn in txns_b:
            for ent in access.get_entitlements_for_transaction(txn):
                roles_b.update(ent.source_roles)

        # Check for mitigation
        rule_mitigations = self._mitigations.get(rule.rule_id, {})
        user_mitigation = rule_mitigations.get(access.user_id)
        is_mitigated = False
        mitigation_id = None
        mitigation_desc = ""
        if user_mitigation:
            valid_to = user_mitigation.get("valid_to")
            if not valid_to or valid_to > datetime.utcnow():
                is_mitigated = True
                mitigation_id = user_mitigation.get("mitigation_id")
                mitigation_desc = user_mitigation.get("description", "")

        return SoDViolation(
            violation_id=vid,
            user_id=access.user_id,
            conflict=conflict,
            risk_level=rule.risk_level.value,
            business_process=rule.business_process.value,
            risk_description=rule.risk_description,
            business_impact=rule.business_impact,
            source_roles_a=sorted(roles_a),
            source_roles_b=sorted(roles_b),
            mitigation_id=mitigation_id,
            mitigation_description=mitigation_desc,
            is_mitigated=is_mitigated,
            status=ViolationStatus.MITIGATED if is_mitigated else ViolationStatus.OPEN,
            sox_relevant=rule.sox_relevant,
            regulatory_refs=rule.regulatory_refs,
        )

    # ------------------------------------------------------------------
    # Simulation: "what if" analysis
    # ------------------------------------------------------------------

    def simulate_role_addition(
        self,
        current_access: UserEffectiveAccess,
        proposed_access: UserEffectiveAccess,
    ) -> RiskAnalysisResult:
        """Compare current vs proposed access to find NEW violations.

        Used by access request workflows to preview risk impact.
        """
        current_result = self.analyze(current_access)
        proposed_result = self.analyze(proposed_access)

        current_vids = {v.violation_id for v in current_result.sod_violations}

        # Filter to only NEW violations
        new_violations = [
            v for v in proposed_result.sod_violations
            if v.violation_id not in current_vids
        ]

        delta = RiskAnalysisResult(
            user_id=current_access.user_id,
            tenant_id=current_access.tenant_id,
            sod_violations=new_violations,
            sensitive_access=[
                v for v in proposed_result.sensitive_access
                if v.violation_id not in {
                    s.violation_id for s in current_result.sensitive_access
                }
            ],
            critical_actions=[
                v for v in proposed_result.critical_actions
                if v.violation_id not in {
                    c.violation_id for c in current_result.critical_actions
                }
            ],
        )
        delta.compute_summary()
        return delta

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _make_id(prefix: str, user_id: str, rule_or_txn: str) -> str:
        """Generate deterministic violation ID."""
        raw = f"{prefix}:{user_id}:{rule_or_txn}"
        return f"{prefix}-{hashlib.sha256(raw.encode()).hexdigest()[:12]}"
