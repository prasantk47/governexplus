"""
Effective Access Calculation Engine

The authoritative engine for determining what a user can actually do.
Resolves the full chain:

    USER
     ↓
    ROLE ASSIGNMENTS (with validity, org restrictions)
     ↓
    COMPOSITE / DERIVED ROLE EXPANSION
     ↓
    AUTHORIZATION OBJECTS
     ↓
    FIELD / VALUE PAIRS
     ↓
    ORGANIZATIONAL SCOPE
     ↓
    EFFECTIVE ENTITLEMENTS

Distinguishes 7 access states:
    1. Requested Access  — in an open access request
    2. Approved Access   — approved but not yet provisioned
    3. Provisioned Access — sent to target system
    4. Detected Access   — read from target system via connector
    5. Effective Access   — computed from detected + org restrictions
    6. Used Access        — actually exercised (from usage logs)
    7. Certified Access   — confirmed in last certification campaign

These are NOT the same thing. Approval ≠ actual access.
"""

from .engine import EffectiveAccessEngine
from .models import (
    AccessState,
    AuthorizationObject,
    AuthFieldValue,
    OrgRestriction,
    EffectiveEntitlement,
    EntitlementScope,
    RoleExpansion,
    UserEffectiveAccess,
    AccessReconciliation,
    ReconciliationStatus,
)

__all__ = [
    "EffectiveAccessEngine",
    "AccessState",
    "AuthorizationObject",
    "AuthFieldValue",
    "OrgRestriction",
    "EffectiveEntitlement",
    "EntitlementScope",
    "RoleExpansion",
    "UserEffectiveAccess",
    "AccessReconciliation",
    "ReconciliationStatus",
]
