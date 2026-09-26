"""
Effective Access Calculation Engine

The authoritative engine for resolving what a user can ACTUALLY do.
All other modules (SoD, certification, risk, firefighter) consume this.

Resolution chain:
    USER → ROLE ASSIGNMENTS → COMPOSITE/DERIVED EXPANSION →
    AUTHORIZATION OBJECTS → FIELD/VALUE PAIRS →
    ORGANIZATIONAL SCOPE → EFFECTIVE ENTITLEMENTS

Data sources:
    1. DB: UserRole assignments (approved/provisioned state)
    2. Connector: Detected roles/authorizations from target system
    3. Access Requests: Pending/approved requests (requested/approved state)
    4. Usage Logs: Actual transaction execution (used state)
    5. Certification: Last certification decisions (certified state)
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from .models import (
    AccessState,
    AccessReconciliation,
    AuthFieldValue,
    AuthorizationObject,
    EffectiveEntitlement,
    EntitlementScope,
    OrgRestriction,
    ReconciliationStatus,
    RoleExpansion,
    RoleType,
    UserEffectiveAccess,
)

logger = logging.getLogger(__name__)


class EffectiveAccessEngine:
    """Calculates the complete effective access picture for a user.

    This is a *pure logic* engine.  It does NOT touch the database or
    connectors directly.  Callers feed it data, and it returns the
    resolved result.  This keeps the engine testable and decoupled.

    Typical usage::

        engine = EffectiveAccessEngine()

        # 1. Feed role assignments from DB
        engine.add_role_assignments(user_id, role_records)

        # 2. Feed role definitions (from connector or cache)
        engine.add_role_definitions(role_defs)

        # 3. Feed detected access from target system
        engine.add_detected_access(user_id, detected_roles)

        # 4. Feed usage data
        engine.add_usage_data(user_id, usage_records)

        # 5. Calculate
        result: UserEffectiveAccess = engine.calculate(user_id, tenant_id)
    """

    def __init__(self):
        # Keyed by user_id
        self._role_assignments: dict[str, list[_RoleAssignment]] = {}
        # Keyed by role_id
        self._role_definitions: dict[str, _RoleDefinition] = {}
        # Composite role → child roles
        self._composite_children: dict[str, list[str]] = {}
        # Derived role → parent + org restrictions
        self._derived_roles: dict[str, _DerivedRoleInfo] = {}
        # Detected access per user: {user_id: [role_ids]}
        self._detected_roles: dict[str, set[str]] = {}
        # Usage data per user: {user_id: {transaction: (last_used, count_90d)}}
        self._usage_data: dict[str, dict[str, tuple[Optional[datetime], int]]] = {}
        # Certified access: {user_id: {role_id: certified_at}}
        self._certified_access: dict[str, dict[str, datetime]] = {}

    # ------------------------------------------------------------------
    # Data ingestion
    # ------------------------------------------------------------------

    def add_role_assignments(
        self,
        user_id: str,
        assignments: list[dict],
    ) -> None:
        """Feed role assignments from the database.

        Each dict should have:
            role_id, assigned_at, valid_from, valid_to, is_active, request_id
        """
        parsed = []
        for a in assignments:
            parsed.append(_RoleAssignment(
                role_id=a["role_id"],
                assigned_at=a.get("assigned_at"),
                valid_from=a.get("valid_from"),
                valid_to=a.get("valid_to"),
                is_active=a.get("is_active", True),
                request_id=a.get("request_id"),
            ))
        self._role_assignments[user_id] = parsed

    def add_role_definitions(self, role_defs: list[dict]) -> None:
        """Feed role definitions from connector or cache.

        Each dict should have:
            role_id, role_type ("single"|"composite"|"derived"),
            description,
            transactions: [{tcode, text}],
            authorizations: [{auth_object, field, values: [...]}],
            parent_role_id (for derived),
            child_roles: [role_ids] (for composite),
            org_restrictions: [{org_field, values: [...]}] (for derived)
        """
        for rd in role_defs:
            role_id = rd["role_id"]
            role_type_str = rd.get("role_type", "single")

            # Parse authorizations → grouped by auth_object
            auth_objects = _parse_authorizations(role_id, rd.get("authorizations", []))

            # Parse transactions
            transactions = [t["tcode"] for t in rd.get("transactions", [])]

            self._role_definitions[role_id] = _RoleDefinition(
                role_id=role_id,
                role_type=role_type_str,
                description=rd.get("description", ""),
                transactions=transactions,
                auth_objects=auth_objects,
            )

            # Track composite children
            if role_type_str == "composite":
                self._composite_children[role_id] = rd.get("child_roles", [])

            # Track derived role info
            if role_type_str == "derived":
                org_restrictions = []
                for org in rd.get("org_restrictions", []):
                    org_restrictions.append(OrgRestriction(
                        org_field=org["org_field"],
                        values=org.get("values", []),
                        is_wildcard=org.get("is_wildcard", False),
                    ))
                self._derived_roles[role_id] = _DerivedRoleInfo(
                    parent_role_id=rd.get("parent_role_id", ""),
                    org_restrictions=org_restrictions,
                )

    def add_detected_access(self, user_id: str, detected_role_ids: list[str]) -> None:
        """Feed roles detected on the target system via connector read-back."""
        self._detected_roles[user_id] = set(detected_role_ids)

    def add_usage_data(
        self,
        user_id: str,
        usage_records: list[dict],
    ) -> None:
        """Feed usage/activity log data.

        Each dict: {transaction, last_used: datetime|None, count_90d: int}
        """
        data: dict[str, tuple[Optional[datetime], int]] = {}
        for u in usage_records:
            data[u["transaction"]] = (u.get("last_used"), u.get("count_90d", 0))
        self._usage_data[user_id] = data

    def add_certified_access(
        self,
        user_id: str,
        certified: dict[str, datetime],
    ) -> None:
        """Feed last certification decisions.

        certified: {role_id: certified_at}
        """
        self._certified_access[user_id] = certified

    # ------------------------------------------------------------------
    # Core calculation
    # ------------------------------------------------------------------

    def calculate(self, user_id: str, tenant_id: str) -> UserEffectiveAccess:
        """Calculate the complete effective access for a user.

        Returns a fully resolved UserEffectiveAccess with:
        - Expanded roles (composite → single, derived → parent + org)
        - All entitlements at the auth-object/field-value level
        - Organizational scope for each entitlement
        - Access state tracking (requested/approved/provisioned/detected/used/certified)
        - Reconciliation of approved vs detected access
        """
        result = UserEffectiveAccess(
            user_id=user_id,
            tenant_id=tenant_id,
            calculated_at=datetime.utcnow(),
        )

        # Step 1: Get the user's assigned roles
        assignments = self._role_assignments.get(user_id, [])

        # Step 2: Expand all roles to single roles
        expanded = self._expand_roles(assignments)
        result.role_expansions = [e for e in expanded.values()]

        # Step 3: For each expanded single role, resolve entitlements
        entitlements_by_txn: dict[str, EffectiveEntitlement] = {}

        for role_id, expansion in expanded.items():
            if not expansion.is_valid:
                continue

            role_def = self._role_definitions.get(role_id)
            if not role_def:
                # Role definition not loaded — skip
                logger.warning(f"Role definition not found for {role_id}")
                continue

            # Build entitlement scopes for this role
            scopes = self._build_entitlement_scopes(role_def, expansion)

            for scope in scopes:
                txn = scope.transaction
                if txn in entitlements_by_txn:
                    # Merge: add auth objects and source roles
                    existing = entitlements_by_txn[txn]
                    existing.auth_objects.extend(scope.auth_objects)
                    if scope.source_role not in existing.source_roles:
                        existing.source_roles.append(scope.source_role)
                    # Merge org scope
                    for field_name, values in scope.effective_org_scope.items():
                        if field_name in existing.org_scope:
                            merged = set(existing.org_scope[field_name]) | set(values)
                            existing.org_scope[field_name] = sorted(merged)
                        else:
                            existing.org_scope[field_name] = values
                else:
                    # New entitlement
                    ent = EffectiveEntitlement(
                        user_id=user_id,
                        transaction=txn,
                        auth_objects=list(scope.auth_objects),
                        org_scope=dict(scope.effective_org_scope),
                        source_roles=[scope.source_role],
                        source_system=scope.source_system,
                        is_executable=scope.is_executable,
                        is_fiori=scope.is_fiori,
                    )
                    entitlements_by_txn[txn] = ent

        # Step 4: Enrich with access states, usage, and change/display classification
        detected_roles = self._detected_roles.get(user_id, set())
        usage_data = self._usage_data.get(user_id, {})
        certified = self._certified_access.get(user_id, {})

        for txn, ent in entitlements_by_txn.items():
            # Determine access states
            states = self._determine_access_states(
                user_id, ent.source_roles, detected_roles, certified,
            )
            ent.access_states = states

            # Classify change vs display
            ent.has_change_access = any(ao.has_change_access() for ao in ent.auth_objects)
            ent.has_display_only = not ent.has_change_access

            # Usage enrichment
            if txn in usage_data:
                ent.last_used, ent.usage_count_90d = usage_data[txn]

        result.entitlements = list(entitlements_by_txn.values())

        # Step 5: Compute summary metrics
        result.total_transactions = len(entitlements_by_txn)
        seen_auth_objects: set[str] = set()
        for ent in result.entitlements:
            for ao in ent.auth_objects:
                seen_auth_objects.add(ao.object_name)
        result.total_auth_objects = len(seen_auth_objects)

        # Org scope summary
        org_summary: dict[str, set[str]] = {}
        for ent in result.entitlements:
            for field_name, values in ent.org_scope.items():
                if field_name not in org_summary:
                    org_summary[field_name] = set()
                org_summary[field_name].update(values)
        result.org_scope_summary = {k: sorted(v) for k, v in org_summary.items()}

        # Step 6: Reconciliation
        result.over_provisioned, result.under_provisioned, result.stale_access = \
            self._reconcile(user_id, assignments, detected_roles)

        return result

    # ------------------------------------------------------------------
    # Role expansion
    # ------------------------------------------------------------------

    def _expand_roles(
        self, assignments: list[_RoleAssignment],
    ) -> dict[str, RoleExpansion]:
        """Expand composite and derived roles into single roles.

        Returns a dict of single_role_id → RoleExpansion.
        """
        expansions: dict[str, RoleExpansion] = {}

        for assignment in assignments:
            role_id = assignment.role_id
            role_def = self._role_definitions.get(role_id)

            if not role_def:
                # No definition — treat as single role
                expansions[role_id] = RoleExpansion(
                    original_role_id=role_id,
                    original_role_type=RoleType.SINGLE,
                    expanded_roles=[role_id],
                    is_active=assignment.is_active,
                    valid_from=assignment.valid_from,
                    valid_to=assignment.valid_to,
                )
                continue

            if role_def.role_type == "composite":
                children = self._expand_composite(role_id, set())
                expansions[role_id] = RoleExpansion(
                    original_role_id=role_id,
                    original_role_type=RoleType.COMPOSITE,
                    expanded_roles=children,
                    is_active=assignment.is_active,
                    valid_from=assignment.valid_from,
                    valid_to=assignment.valid_to,
                )
                # Also register each child so we process its entitlements
                for child_id in children:
                    if child_id not in expansions:
                        expansions[child_id] = RoleExpansion(
                            original_role_id=child_id,
                            original_role_type=RoleType.SINGLE,
                            expanded_roles=[child_id],
                            is_active=assignment.is_active,
                            valid_from=assignment.valid_from,
                            valid_to=assignment.valid_to,
                        )

            elif role_def.role_type == "derived":
                derived_info = self._derived_roles.get(role_id)
                parent_id = derived_info.parent_role_id if derived_info else role_id
                org_restrictions = derived_info.org_restrictions if derived_info else []
                expansions[role_id] = RoleExpansion(
                    original_role_id=role_id,
                    original_role_type=RoleType.DERIVED,
                    expanded_roles=[parent_id],
                    org_restrictions=org_restrictions,
                    is_active=assignment.is_active,
                    valid_from=assignment.valid_from,
                    valid_to=assignment.valid_to,
                )

            else:
                # Single role
                expansions[role_id] = RoleExpansion(
                    original_role_id=role_id,
                    original_role_type=RoleType.SINGLE,
                    expanded_roles=[role_id],
                    is_active=assignment.is_active,
                    valid_from=assignment.valid_from,
                    valid_to=assignment.valid_to,
                )

        return expansions

    def _expand_composite(self, role_id: str, visited: set[str]) -> list[str]:
        """Recursively expand composite role to leaf single roles."""
        if role_id in visited:
            logger.warning(f"Circular composite role reference: {role_id}")
            return []
        visited.add(role_id)

        children = self._composite_children.get(role_id, [])
        if not children:
            return [role_id]

        result = []
        for child_id in children:
            child_def = self._role_definitions.get(child_id)
            if child_def and child_def.role_type == "composite":
                result.extend(self._expand_composite(child_id, visited))
            else:
                result.append(child_id)
        return result

    # ------------------------------------------------------------------
    # Entitlement scope building
    # ------------------------------------------------------------------

    def _build_entitlement_scopes(
        self,
        role_def: _RoleDefinition,
        expansion: RoleExpansion,
    ) -> list[EntitlementScope]:
        """Build EntitlementScope for each transaction in a role."""
        scopes = []
        for txn in role_def.transactions:
            scope = EntitlementScope(
                transaction=txn,
                auth_objects=list(role_def.auth_objects),
                org_restrictions=list(expansion.org_restrictions),
                source_role=role_def.role_id,
            )
            scopes.append(scope)
        return scopes

    # ------------------------------------------------------------------
    # Access state determination
    # ------------------------------------------------------------------

    def _determine_access_states(
        self,
        user_id: str,
        source_roles: list[str],
        detected_roles: set[str],
        certified: dict[str, datetime],
    ) -> list[AccessState]:
        """Determine which access states apply to an entitlement."""
        states = []

        # Approved (it's in our DB assignments)
        states.append(AccessState.APPROVED)

        # Provisioned (we track this via the assignment existing)
        states.append(AccessState.PROVISIONED)

        # Detected (any source role is detected on target system)
        if any(r in detected_roles for r in source_roles):
            states.append(AccessState.DETECTED)
            states.append(AccessState.EFFECTIVE)

        # Certified (any source role was certified)
        if any(r in certified for r in source_roles):
            states.append(AccessState.CERTIFIED)

        # Used state is set separately via usage data enrichment

        return states

    # ------------------------------------------------------------------
    # Reconciliation
    # ------------------------------------------------------------------

    def _reconcile(
        self,
        user_id: str,
        assignments: list[_RoleAssignment],
        detected_roles: set[str],
    ) -> tuple[list[str], list[str], list[str]]:
        """Compare approved (DB) vs detected (connector) access.

        Returns (over_provisioned, under_provisioned, stale).
        """
        approved_role_ids = {
            a.role_id for a in assignments if a.is_active
        }
        now = datetime.utcnow()

        # Over-provisioned: detected but never approved
        over = sorted(detected_roles - approved_role_ids)

        # Under-provisioned: approved but not detected
        under = sorted(approved_role_ids - detected_roles)

        # Stale: approved with expired validity but still detected
        stale = []
        for a in assignments:
            if a.valid_to and a.valid_to < now and a.role_id in detected_roles:
                stale.append(a.role_id)

        return over, under, stale

    def reconcile_detailed(
        self,
        user_id: str,
    ) -> list[AccessReconciliation]:
        """Produce detailed per-role reconciliation records."""
        assignments = self._role_assignments.get(user_id, [])
        detected = self._detected_roles.get(user_id, set())
        now = datetime.utcnow()

        results = []
        approved_ids = set()

        for a in assignments:
            approved_ids.add(a.role_id)
            if not a.is_active:
                continue

            if a.role_id in detected:
                if a.valid_to and a.valid_to < now:
                    status = ReconciliationStatus.STALE
                else:
                    status = ReconciliationStatus.MATCHED
            else:
                status = ReconciliationStatus.UNDER_PROVISIONED

            results.append(AccessReconciliation(
                user_id=user_id,
                role_id=a.role_id,
                status=status,
                approved_at=a.assigned_at,
                detected_at=now if a.role_id in detected else None,
            ))

        # Over-provisioned: detected but not in assignments
        for role_id in sorted(detected - approved_ids):
            results.append(AccessReconciliation(
                user_id=user_id,
                role_id=role_id,
                status=ReconciliationStatus.OVER_PROVISIONED,
                detected_at=now,
                discrepancy_details="Role detected on target system but no matching approval found",
            ))

        return results

    # ------------------------------------------------------------------
    # Query helpers (post-calculation)
    # ------------------------------------------------------------------

    def get_entitlements_with_org_overlap(
        self,
        access: UserEffectiveAccess,
        txn_a: str,
        txn_b: str,
    ) -> dict[str, list[str]]:
        """Check if two transactions share organizational scope.

        This is critical for SoD: if FK01 is in company 1000 and F110
        is in company 2000, there is NO real SoD conflict even though
        both transactions are assigned.

        Returns {org_field: [overlapping_values]} or empty if no overlap.
        """
        scope_a = access.get_org_scope_for_transaction(txn_a)
        scope_b = access.get_org_scope_for_transaction(txn_b)

        overlaps: dict[str, list[str]] = {}
        for field_name in set(scope_a.keys()) & set(scope_b.keys()):
            vals_a = set(scope_a[field_name])
            vals_b = set(scope_b[field_name])

            # Wildcard handling
            if "*" in vals_a or "*" in vals_b:
                overlaps[field_name] = sorted(vals_a | vals_b)
                continue

            common = vals_a & vals_b
            if common:
                overlaps[field_name] = sorted(common)

        return overlaps

    def get_auth_object_overlap(
        self,
        access: UserEffectiveAccess,
        txn_a: str,
        txn_b: str,
        auth_object_name: str,
    ) -> dict:
        """Check if two transactions overlap on a specific auth object.

        Returns overlap details at the field/value level, not just
        "both transactions are assigned."
        """
        ents_a = access.get_entitlements_for_transaction(txn_a)
        ents_b = access.get_entitlements_for_transaction(txn_b)

        # Gather auth objects matching the name
        aos_a = [ao for e in ents_a for ao in e.auth_objects
                 if ao.object_name == auth_object_name]
        aos_b = [ao for e in ents_b for ao in e.auth_objects
                 if ao.object_name == auth_object_name]

        if not aos_a or not aos_b:
            return {}

        # Check field-level overlap
        overlap_result = {}
        for ao_a in aos_a:
            for ao_b in aos_b:
                org_overlap = ao_a.overlaps_org_scope(ao_b)
                if org_overlap:
                    overlap_result["org_overlap"] = org_overlap

                # Check activity overlap
                act_a = ao_a.activity
                act_b = ao_b.activity
                if act_a and act_b:
                    overlap_result["activities"] = {
                        "txn_a": act_a,
                        "txn_b": act_b,
                    }

        return overlap_result


# ---------------------------------------------------------------------------
# Internal data classes (not exported)
# ---------------------------------------------------------------------------

class _RoleAssignment:
    __slots__ = ("role_id", "assigned_at", "valid_from", "valid_to",
                 "is_active", "request_id")

    def __init__(
        self,
        role_id: str,
        assigned_at: Optional[datetime] = None,
        valid_from: Optional[datetime] = None,
        valid_to: Optional[datetime] = None,
        is_active: bool = True,
        request_id: Optional[str] = None,
    ):
        self.role_id = role_id
        self.assigned_at = assigned_at
        self.valid_from = valid_from
        self.valid_to = valid_to
        self.is_active = is_active
        self.request_id = request_id


class _RoleDefinition:
    __slots__ = ("role_id", "role_type", "description",
                 "transactions", "auth_objects")

    def __init__(
        self,
        role_id: str,
        role_type: str,
        description: str,
        transactions: list[str],
        auth_objects: list[AuthorizationObject],
    ):
        self.role_id = role_id
        self.role_type = role_type
        self.description = description
        self.transactions = transactions
        self.auth_objects = auth_objects


class _DerivedRoleInfo:
    __slots__ = ("parent_role_id", "org_restrictions")

    def __init__(self, parent_role_id: str, org_restrictions: list[OrgRestriction]):
        self.parent_role_id = parent_role_id
        self.org_restrictions = org_restrictions


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_authorizations(
    role_id: str,
    raw_auths: list[dict],
) -> list[AuthorizationObject]:
    """Parse raw authorization dicts into AuthorizationObject instances.

    Groups fields by auth_object name, since SAP stores them flat:
        [
            {"auth_object": "F_BKPF_BUK", "field": "BUKRS", "values": ["1000"]},
            {"auth_object": "F_BKPF_BUK", "field": "ACTVT", "values": ["01","02"]},
        ]
    becomes one AuthorizationObject with two AuthFieldValue entries.
    """
    grouped: dict[str, list[AuthFieldValue]] = {}

    for auth in raw_auths:
        obj_name = auth["auth_object"]
        field_name = auth.get("field", "")
        values = auth.get("values", [])

        if obj_name not in grouped:
            grouped[obj_name] = []

        for val in values:
            is_wildcard = val == "*"
            grouped[obj_name].append(AuthFieldValue(
                field_name=field_name,
                value=val,
                is_wildcard=is_wildcard,
            ))

    result = []
    for obj_name, fields in grouped.items():
        result.append(AuthorizationObject(
            object_name=obj_name,
            fields=fields,
            source_role=role_id,
        ))
    return result
