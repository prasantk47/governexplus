"""
Effective Access — Data Models

Defines the complete entitlement graph from role assignment
down to authorization field/value with organizational scope.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class AccessState(enum.Enum):
    """The 7 distinct access states."""
    REQUESTED = "requested"
    APPROVED = "approved"
    PROVISIONED = "provisioned"
    DETECTED = "detected"
    EFFECTIVE = "effective"
    USED = "used"
    CERTIFIED = "certified"


class ReconciliationStatus(enum.Enum):
    """Result of comparing approved vs detected access."""
    MATCHED = "matched"              # approved == detected
    OVER_PROVISIONED = "over"        # detected but never approved
    UNDER_PROVISIONED = "under"      # approved but not detected
    STALE = "stale"                  # approved, detected, but expired
    PROVISIONING_FAILED = "failed"   # approved, provisioning attempted, not detected
    PENDING = "pending"              # approved, provisioning not yet attempted


class RoleType(enum.Enum):
    SINGLE = "single"
    COMPOSITE = "composite"
    DERIVED = "derived"


class ActivityType(enum.Enum):
    """SAP activity types for authorization checks."""
    CREATE = "01"
    CHANGE = "02"
    DISPLAY = "03"
    DELETE = "06"
    PRINT = "08"
    EXECUTE = "16"
    RELEASE = "25"
    MAINTAIN = "70"


# ---------------------------------------------------------------------------
# Authorization models
# ---------------------------------------------------------------------------

@dataclass
class AuthFieldValue:
    """A single field-value pair within an authorization object."""
    field_name: str        # e.g., "TCD", "ACTVT", "BUKRS"
    value: str             # e.g., "FK01", "01", "1000"
    value_from: str = ""   # range start (if range)
    value_to: str = ""     # range end (if range)
    is_wildcard: bool = False  # "*" = all values

    def matches(self, other_value: str) -> bool:
        """Check if this field-value matches a given value."""
        if self.is_wildcard:
            return True
        if self.value_from and self.value_to:
            return self.value_from <= other_value <= self.value_to
        return self.value == other_value

    def overlaps(self, other: "AuthFieldValue") -> bool:
        """Check if two field values have overlapping scope."""
        if self.field_name != other.field_name:
            return False
        if self.is_wildcard or other.is_wildcard:
            return True
        if self.value_from and self.value_to and other.value_from and other.value_to:
            return self.value_from <= other.value_to and other.value_from <= self.value_to
        if self.value_from and self.value_to:
            return self.value_from <= other.value <= self.value_to
        if other.value_from and other.value_to:
            return other.value_from <= self.value <= other.value_to
        return self.value == other.value

    def to_dict(self) -> dict:
        d = {"field": self.field_name, "value": self.value}
        if self.value_from:
            d["from"] = self.value_from
        if self.value_to:
            d["to"] = self.value_to
        if self.is_wildcard:
            d["wildcard"] = True
        return d


@dataclass
class OrgRestriction:
    """Organizational scope restriction on a role assignment.

    In SAP, derived roles inherit the parent's menu/authorizations
    but get different org-level values (company code, plant, etc.).
    """
    org_field: str   # e.g., "BUKRS" (company code), "WERKS" (plant)
    values: list[str] = field(default_factory=list)
    is_wildcard: bool = False

    def contains(self, value: str) -> bool:
        if self.is_wildcard:
            return True
        return value in self.values

    def overlaps(self, other: "OrgRestriction") -> bool:
        if self.org_field != other.org_field:
            return False
        if self.is_wildcard or other.is_wildcard:
            return True
        return bool(set(self.values) & set(other.values))

    def intersection(self, other: "OrgRestriction") -> list[str]:
        """Return the overlapping org values."""
        if self.org_field != other.org_field:
            return []
        if self.is_wildcard:
            return list(other.values)
        if other.is_wildcard:
            return list(self.values)
        return list(set(self.values) & set(other.values))

    def to_dict(self) -> dict:
        return {
            "field": self.org_field,
            "values": self.values,
            "wildcard": self.is_wildcard,
        }


@dataclass
class AuthorizationObject:
    """An SAP authorization object with its field/value assignments.

    Example:
        object_name: "F_BKPF_BUK"
        fields: [
            AuthFieldValue("BUKRS", "1000"),  # company code
            AuthFieldValue("ACTVT", "01"),     # create
        ]
    """
    object_name: str                           # e.g., "F_BKPF_BUK"
    fields: list[AuthFieldValue] = field(default_factory=list)
    source_role: str = ""                      # which role grants this
    source_system: str = "SAP"

    @property
    def activity(self) -> Optional[str]:
        """Extract activity value if ACTVT field present."""
        for f in self.fields:
            if f.field_name == "ACTVT":
                return f.value
        return None

    @property
    def org_fields(self) -> list[AuthFieldValue]:
        """Return organizational-level fields (BUKRS, WERKS, EKORG, etc.)."""
        org_field_names = {
            "BUKRS", "WERKS", "EKORG", "VKORG", "GSBER",
            "KOKRS", "BWKEY", "LGNUM", "SWERK", "IWERK",
            "PERSA", "MOLGA", "PERSG", "PERSK",
        }
        return [f for f in self.fields if f.field_name in org_field_names]

    def get_field(self, name: str) -> Optional[AuthFieldValue]:
        for f in self.fields:
            if f.field_name == name:
                return f
        return None

    def has_change_access(self) -> bool:
        """Check if this grants create/change/delete (not just display)."""
        act = self.activity
        if not act:
            return True  # no activity field = unrestricted
        return act in ("01", "02", "06", "16", "25", "70")

    def overlaps_org_scope(self, other: "AuthorizationObject") -> dict:
        """Check organizational overlap between two auth objects.

        Returns dict of {org_field: [overlapping_values]} or empty if no overlap.
        """
        overlaps = {}
        for my_field in self.org_fields:
            for other_field in other.org_fields:
                if my_field.field_name == other_field.field_name:
                    if my_field.overlaps(other_field):
                        if my_field.is_wildcard:
                            vals = [other_field.value] if not other_field.is_wildcard else ["*"]
                        elif other_field.is_wildcard:
                            vals = [my_field.value]
                        else:
                            vals = [my_field.value] if my_field.value == other_field.value else []
                            # Handle ranges
                            if my_field.value_from and other_field.value_from:
                                start = max(my_field.value_from, other_field.value_from)
                                end = min(my_field.value_to, other_field.value_to)
                                vals = [f"{start}-{end}"]
                        if vals:
                            overlaps[my_field.field_name] = vals
        return overlaps

    def to_dict(self) -> dict:
        return {
            "object": self.object_name,
            "fields": [f.to_dict() for f in self.fields],
            "source_role": self.source_role,
            "source_system": self.source_system,
        }


@dataclass
class EntitlementScope:
    """Complete scope of an entitlement: transaction + auth objects + org level."""
    transaction: str                               # e.g., "FK01"
    auth_objects: list[AuthorizationObject] = field(default_factory=list)
    org_restrictions: list[OrgRestriction] = field(default_factory=list)
    source_role: str = ""
    source_system: str = "SAP"
    is_executable: bool = True      # vs merely assigned but not in menu
    is_fiori: bool = False
    fiori_app_id: str = ""

    @property
    def effective_org_scope(self) -> dict[str, list[str]]:
        """Combine org restrictions from auth objects and role-level restrictions."""
        scope: dict[str, set[str]] = {}
        # From auth objects
        for ao in self.auth_objects:
            for f in ao.org_fields:
                key = f.field_name
                if key not in scope:
                    scope[key] = set()
                if f.is_wildcard:
                    scope[key].add("*")
                elif f.value_from:
                    scope[key].add(f"{f.value_from}-{f.value_to}")
                else:
                    scope[key].add(f.value)
        # Apply role-level org restrictions (intersect)
        for org in self.org_restrictions:
            key = org.org_field
            if key in scope and "*" not in scope[key]:
                if not org.is_wildcard:
                    scope[key] &= set(org.values)
            elif key not in scope:
                scope[key] = set(org.values) if not org.is_wildcard else {"*"}
        return {k: sorted(v) for k, v in scope.items()}

    def to_dict(self) -> dict:
        return {
            "transaction": self.transaction,
            "auth_objects": [ao.to_dict() for ao in self.auth_objects],
            "org_scope": self.effective_org_scope,
            "source_role": self.source_role,
            "is_executable": self.is_executable,
            "is_fiori": self.is_fiori,
        }


@dataclass
class RoleExpansion:
    """Result of expanding a composite/derived role into its single roles."""
    original_role_id: str
    original_role_type: RoleType
    expanded_roles: list[str] = field(default_factory=list)  # single role IDs
    org_restrictions: list[OrgRestriction] = field(default_factory=list)
    is_active: bool = True
    valid_from: Optional[datetime] = None
    valid_to: Optional[datetime] = None

    @property
    def is_valid(self) -> bool:
        now = datetime.utcnow()
        if self.valid_from and now < self.valid_from:
            return False
        if self.valid_to and now > self.valid_to:
            return False
        return self.is_active


@dataclass
class EffectiveEntitlement:
    """A single effective entitlement for a user.

    This is the atomic unit of "what can this user actually do?"
    """
    user_id: str
    transaction: str
    auth_objects: list[AuthorizationObject]
    org_scope: dict[str, list[str]]      # {field: [values]}
    source_roles: list[str]              # which role(s) grant this
    source_system: str = "SAP"
    access_states: list[AccessState] = field(default_factory=list)
    has_change_access: bool = False
    has_display_only: bool = False
    is_executable: bool = True
    is_fiori: bool = False
    last_used: Optional[datetime] = None
    usage_count_90d: int = 0

    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "transaction": self.transaction,
            "auth_objects": [ao.to_dict() for ao in self.auth_objects],
            "org_scope": self.org_scope,
            "source_roles": self.source_roles,
            "access_states": [s.value for s in self.access_states],
            "has_change_access": self.has_change_access,
            "is_executable": self.is_executable,
            "last_used": self.last_used.isoformat() if self.last_used else None,
            "usage_count_90d": self.usage_count_90d,
        }


@dataclass
class UserEffectiveAccess:
    """Complete effective access picture for a user."""
    user_id: str
    tenant_id: str
    calculated_at: datetime = field(default_factory=datetime.utcnow)
    entitlements: list[EffectiveEntitlement] = field(default_factory=list)
    role_expansions: list[RoleExpansion] = field(default_factory=list)
    total_transactions: int = 0
    total_auth_objects: int = 0
    org_scope_summary: dict[str, list[str]] = field(default_factory=dict)

    # Reconciliation
    over_provisioned: list[str] = field(default_factory=list)  # detected but not approved
    under_provisioned: list[str] = field(default_factory=list) # approved but not detected
    stale_access: list[str] = field(default_factory=list)       # expired but still detected

    def get_transactions(self) -> set[str]:
        return {e.transaction for e in self.entitlements}

    def get_entitlements_for_transaction(self, txn: str) -> list[EffectiveEntitlement]:
        return [e for e in self.entitlements if e.transaction == txn]

    def get_org_scope_for_transaction(self, txn: str) -> dict[str, list[str]]:
        """Get combined org scope across all entitlements for a transaction."""
        combined: dict[str, set[str]] = {}
        for e in self.get_entitlements_for_transaction(txn):
            for field_name, values in e.org_scope.items():
                if field_name not in combined:
                    combined[field_name] = set()
                combined[field_name].update(values)
        return {k: sorted(v) for k, v in combined.items()}

    def has_executable_access(self, txn: str) -> bool:
        return any(
            e.transaction == txn and e.is_executable
            for e in self.entitlements
        )

    def has_change_access_to(self, txn: str) -> bool:
        return any(
            e.transaction == txn and e.has_change_access
            for e in self.entitlements
        )

    def to_summary(self) -> dict:
        return {
            "user_id": self.user_id,
            "calculated_at": self.calculated_at.isoformat(),
            "total_transactions": self.total_transactions,
            "total_auth_objects": self.total_auth_objects,
            "total_roles": len(self.role_expansions),
            "org_scope": self.org_scope_summary,
            "reconciliation": {
                "over_provisioned": len(self.over_provisioned),
                "under_provisioned": len(self.under_provisioned),
                "stale": len(self.stale_access),
            },
        }


@dataclass
class AccessReconciliation:
    """Result of comparing approved vs detected access for a user-role pair."""
    user_id: str
    role_id: str
    status: ReconciliationStatus
    approved_at: Optional[datetime] = None
    provisioned_at: Optional[datetime] = None
    detected_at: Optional[datetime] = None
    discrepancy_details: str = ""

    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "role_id": self.role_id,
            "status": self.status.value,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "provisioned_at": self.provisioned_at.isoformat() if self.provisioned_at else None,
            "detected_at": self.detected_at.isoformat() if self.detected_at else None,
            "discrepancy": self.discrepancy_details,
        }
