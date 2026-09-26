"""
Organizational Rules Engine

Enforces SAP organizational-level access scoping. In SAP, authorization
objects carry organizational field values (BUKRS, WERKS, EKORG, VKORG,
KOSTL, KOKRS) that restrict which company codes, plants, purchasing
organizations, sales organizations, cost centers, and controlling areas a
user may act within.

This engine allows administrators to define named rules that express those
constraints, then evaluate whether a given user's current org assignments
satisfy the constraints attached to a role.

Data is persisted in the relational database via the OrgRule,
OrgUserAssignment, and OrgRoleRestriction models in db.models.operations.
On first access per tenant, default seed data is inserted automatically
(lazy initialisation) so the system works out-of-the-box without a
separate seed script.
"""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from db.database import db_manager
from db.models.operations import (
    OrgRule as OrgRuleModel,
    OrgUserAssignment as OrgUserAssignmentModel,
    OrgRoleRestriction as OrgRoleRestrictionModel,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# SAP field registry
# ---------------------------------------------------------------------------

SAP_ORG_FIELDS = {
    "BUKRS": "Company Code",
    "WERKS": "Plant",
    "EKORG": "Purchasing Organization",
    "VKORG": "Sales Organization",
    "KOSTL": "Cost Center",
    "KOKRS": "Controlling Area",
}

# ---------------------------------------------------------------------------
# In-process value objects (returned by the engine; never stored directly)
# ---------------------------------------------------------------------------

@dataclass
class OrgRule:
    """A single organizational scoping rule (in-memory value object)."""

    rule_id: str
    name: str
    org_field: str          # SAP field name, e.g. "BUKRS"
    allowed_values: list[str]
    scope: str              # "inclusive" | "exclusive"
    description: str = ""
    active: bool = True
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class OrgAssignment:
    """One org-field assignment for a user."""

    user_id: str
    org_field: str
    values: list[str]
    assigned_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class RoleOrgRestriction:
    """Org restrictions attached to a role."""

    role_id: str
    rules: list[str]        # rule_ids that apply to this role


@dataclass
class EvaluationResult:
    """Result of an org-context access evaluation."""

    allowed: bool
    user_id: str
    role_id: str
    violations: list[dict[str, Any]]
    evaluated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


# ---------------------------------------------------------------------------
# Default seed data (inserted on first access if the DB table is empty)
# ---------------------------------------------------------------------------

_DEFAULT_RULES = [
    # Company Code rules
    ("ORG-001", "CC-US-Only",           "BUKRS", ["1000", "1100"],
     "inclusive",  "Restrict access to US company codes only"),
    ("ORG-002", "CC-EU-Only",           "BUKRS", ["2000", "2100", "2200"],
     "inclusive",  "Restrict access to European company codes"),
    ("ORG-003", "CC-APAC-Only",         "BUKRS", ["3000", "3100"],
     "inclusive",  "Restrict access to APAC company codes"),
    ("ORG-004", "CC-Exclude-Test",      "BUKRS", ["9000", "9999"],
     "exclusive",  "Exclude test/sandbox company codes"),
    ("ORG-005", "CC-Global",            "BUKRS",
     ["1000", "1100", "2000", "2100", "2200", "3000", "3100"],
     "inclusive",  "Allow all production company codes"),
    # Plant rules
    ("ORG-006", "Plant-Manufacturing",  "WERKS", ["P001", "P002", "P003"],
     "inclusive",  "Manufacturing plants only"),
    ("ORG-007", "Plant-Distribution",   "WERKS", ["D001", "D002"],
     "inclusive",  "Distribution center plants only"),
    ("ORG-008", "Plant-All-Prod",       "WERKS",
     ["P001", "P002", "P003", "D001", "D002", "S001"],
     "inclusive",  "All production plants"),
    ("ORG-009", "Plant-Exclude-Service","WERKS", ["SVC1", "SVC2"],
     "exclusive",  "Exclude service-only plants"),
    ("ORG-010", "Plant-EU",             "WERKS", ["EU01", "EU02", "EU03"],
     "inclusive",  "European plants only"),
    # Purchasing Org rules
    ("ORG-011", "POrg-Central",         "EKORG", ["P001"],
     "inclusive",  "Central purchasing organization only"),
    ("ORG-012", "POrg-Local",           "EKORG", ["PL01", "PL02", "PL03"],
     "inclusive",  "Local purchasing organizations"),
    # Sales Org rules
    ("ORG-013", "SOrg-Domestic",        "VKORG", ["S001", "S002"],
     "inclusive",  "Domestic sales organizations"),
    # Cost Center rules
    ("ORG-014", "CC-Finance-Only",      "KOSTL", ["FIN01", "FIN02", "FIN03"],
     "inclusive",  "Finance department cost centers only"),
    # Controlling Area rules
    ("ORG-015", "CoArea-Corp",          "KOKRS", ["CORP"],
     "inclusive",  "Corporate controlling area only"),
]

_DEFAULT_USER_ASSIGNMENTS = {
    "U001": [
        ("BUKRS", ["1000", "1100"]),
        ("WERKS", ["P001", "P002"]),
        ("EKORG", ["P001"]),
        ("KOSTL", ["FIN01"]),
        ("KOKRS", ["CORP"]),
    ],
    "U002": [
        ("BUKRS", ["2000", "2100", "2200"]),
        ("WERKS", ["EU01", "EU02"]),
        ("VKORG", ["S001"]),
    ],
    "U003": [
        ("BUKRS", ["1000", "1100", "2000", "2100", "2200", "3000", "3100"]),
        ("WERKS", ["P001", "P002", "P003", "D001", "D002", "S001"]),
        ("EKORG", ["P001", "PL01", "PL02", "PL03"]),
        ("VKORG", ["S001", "S002"]),
        ("KOSTL", ["FIN01", "FIN02", "FIN03"]),
        ("KOKRS", ["CORP"]),
    ],
    "U004": [
        ("BUKRS", ["3000", "3100"]),
        ("WERKS", ["P003", "D002"]),
    ],
    "U005": [
        ("BUKRS", ["1000"]),
        ("WERKS", ["P001"]),
        ("KOSTL", ["FIN01", "FIN02"]),
        ("KOKRS", ["CORP"]),
    ],
}

_DEFAULT_ROLE_RESTRICTIONS = {
    "ROLE_FI_AP_CLERK":      ["ORG-001", "ORG-014", "ORG-015"],
    "ROLE_MM_BUYER":         ["ORG-011", "ORG-006"],
    "ROLE_SD_ORDER_ENTRY":   ["ORG-013"],
    "ROLE_FI_CONTROLLER":    ["ORG-005", "ORG-015"],
    "ROLE_MM_PURCHASING_MGR":["ORG-012", "ORG-008"],
    "ROLE_GLOBAL_AUDITOR":   ["ORG-005", "ORG-008"],
}


# ---------------------------------------------------------------------------
# DB helper: condition_value is stored as JSON string in a VARCHAR(500) column
# ---------------------------------------------------------------------------

def _encode_values(values: list[str]) -> str:
    """Serialize a list of strings to a compact JSON string for DB storage."""
    return json.dumps(values, separators=(",", ":"))


def _decode_values(raw: str | list | None) -> list[str]:
    """Deserialise the condition_value column back to a Python list."""
    if raw is None:
        return []
    if isinstance(raw, list):
        return raw
    try:
        result = json.loads(raw)
        return result if isinstance(result, list) else []
    except (json.JSONDecodeError, TypeError):
        return []


def _db_row_to_value_object(row: OrgRuleModel) -> OrgRule:
    """Convert a DB OrgRuleModel row into the engine's OrgRule value object."""
    return OrgRule(
        rule_id=row.rule_id,
        name=row.name,
        org_field=row.org_field,
        allowed_values=_decode_values(row.condition_value),
        scope=row.condition_type,
        description=row.description or "",
        active=row.is_active,
        created_at=row.created_at.isoformat() if row.created_at else datetime.utcnow().isoformat(),
        updated_at=row.updated_at.isoformat() if row.updated_at else datetime.utcnow().isoformat(),
    )


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

class OrgRulesEngine:
    """
    Core engine for organizational access-scoping rules.

    Reads and writes all data through SQLAlchemy sessions obtained from
    db_manager.  On the first call per tenant the engine lazily seeds the
    database with 15 built-in rules, 5 sample user org-field assignments,
    and 6 role-restriction mappings so the system works without a separate
    seed step.
    """

    def __init__(self, tenant_id: str = "tenant_default") -> None:
        self._tenant_id = tenant_id
        self._seeded: bool = False          # guards against repeated seed checks

    # ------------------------------------------------------------------
    # Lazy seeding
    # ------------------------------------------------------------------

    def _ensure_seeded(self) -> None:
        """Insert default data if the org_rules table is empty for this tenant."""
        if self._seeded:
            return

        try:
            db_manager.init()
            db_manager.create_tables()

            with db_manager.session_scope() as session:
                existing = (
                    session.query(OrgRuleModel)
                    .filter(OrgRuleModel.tenant_id == self._tenant_id)
                    .first()
                )
                if existing:
                    self._seeded = True
                    return

                # --- seed rules ---
                for rule_id, name, org_field, values, ctype, desc in _DEFAULT_RULES:
                    session.add(OrgRuleModel(
                        tenant_id=self._tenant_id,
                        rule_id=rule_id,
                        name=name,
                        description=desc,
                        org_field=org_field,
                        condition_type=ctype,
                        condition_value=_encode_values(values),
                        is_active=True,
                        priority=100,
                        created_by="system",
                    ))

                # --- seed user org assignments ---
                for user_id, field_assignments in _DEFAULT_USER_ASSIGNMENTS.items():
                    for org_field, values in field_assignments:
                        session.add(OrgUserAssignmentModel(
                            tenant_id=self._tenant_id,
                            user_id=user_id,
                            org_field=org_field,
                            values=values,
                        ))

                # --- seed role restrictions ---
                for role_id, rule_ids in _DEFAULT_ROLE_RESTRICTIONS.items():
                    session.add(OrgRoleRestrictionModel(
                        tenant_id=self._tenant_id,
                        role_id=role_id,
                        rule_ids=rule_ids,
                    ))

            self._seeded = True
            logger.info(
                "OrgRulesEngine: seeded default data for tenant '%s'",
                self._tenant_id,
            )
        except Exception as exc:  # pragma: no cover
            logger.warning(
                "OrgRulesEngine: could not seed DB (%s); engine will operate without defaults.",
                exc,
            )

    # ------------------------------------------------------------------
    # Rule CRUD
    # ------------------------------------------------------------------

    def define_rule(
        self,
        name: str,
        org_field: str,
        values: list[str],
        scope: str,
        description: str = "",
    ) -> OrgRule:
        """
        Create and persist a new organizational scoping rule.

        Parameters
        ----------
        name:        Human-readable rule name.
        org_field:   SAP organizational field (BUKRS, WERKS, EKORG, VKORG, KOSTL, KOKRS).
        values:      Allowed (or excluded) values for the field.
        scope:       "inclusive" — only listed values are permitted;
                     "exclusive" — listed values are explicitly denied.
        description: Optional description.

        Returns
        -------
        The newly created OrgRule value object.
        """
        if org_field not in SAP_ORG_FIELDS:
            raise ValueError(
                f"Unknown org field '{org_field}'. "
                f"Valid fields: {', '.join(SAP_ORG_FIELDS.keys())}"
            )
        if scope not in ("inclusive", "exclusive"):
            raise ValueError("scope must be 'inclusive' or 'exclusive'")

        self._ensure_seeded()

        rule_id = f"ORG-{uuid.uuid4().hex[:6].upper()}"
        with db_manager.session_scope() as session:
            row = OrgRuleModel(
                tenant_id=self._tenant_id,
                rule_id=rule_id,
                name=name,
                description=description,
                org_field=org_field,
                condition_type=scope,
                condition_value=_encode_values(values),
                is_active=True,
                priority=100,
                created_by="api",
            )
            session.add(row)

        return OrgRule(
            rule_id=rule_id,
            name=name,
            org_field=org_field,
            allowed_values=values,
            scope=scope,
            description=description,
        )

    def list_rules(self) -> list[dict[str, Any]]:
        """Return all defined organizational rules for this tenant."""
        self._ensure_seeded()
        with db_manager.session_scope() as session:
            rows = (
                session.query(OrgRuleModel)
                .filter(OrgRuleModel.tenant_id == self._tenant_id)
                .order_by(OrgRuleModel.rule_id)
                .all()
            )
            return [self._rule_to_dict(_db_row_to_value_object(r)) for r in rows]

    def get_rule(self, rule_id: str) -> dict[str, Any] | None:
        """Return a single rule by ID, or None if not found."""
        self._ensure_seeded()
        with db_manager.session_scope() as session:
            row = (
                session.query(OrgRuleModel)
                .filter(
                    OrgRuleModel.tenant_id == self._tenant_id,
                    OrgRuleModel.rule_id == rule_id,
                )
                .first()
            )
            if not row:
                return None
            return self._rule_to_dict(_db_row_to_value_object(row))

    def update_rule(
        self,
        rule_id: str,
        name: str | None = None,
        values: list[str] | None = None,
        scope: str | None = None,
        description: str | None = None,
        active: bool | None = None,
    ) -> dict[str, Any] | None:
        """Update an existing rule. Returns updated rule dict or None if not found."""
        self._ensure_seeded()

        if scope is not None and scope not in ("inclusive", "exclusive"):
            raise ValueError("scope must be 'inclusive' or 'exclusive'")

        with db_manager.session_scope() as session:
            row = (
                session.query(OrgRuleModel)
                .filter(
                    OrgRuleModel.tenant_id == self._tenant_id,
                    OrgRuleModel.rule_id == rule_id,
                )
                .first()
            )
            if not row:
                return None

            if name is not None:
                row.name = name
            if values is not None:
                row.condition_value = _encode_values(values)
            if scope is not None:
                row.condition_type = scope
            if description is not None:
                row.description = description
            if active is not None:
                row.is_active = active
            row.updated_at = datetime.utcnow()

            result = self._rule_to_dict(_db_row_to_value_object(row))

        return result

    def delete_rule(self, rule_id: str) -> bool:
        """Remove a rule by ID. Returns True if deleted, False if not found."""
        self._ensure_seeded()
        with db_manager.session_scope() as session:
            row = (
                session.query(OrgRuleModel)
                .filter(
                    OrgRuleModel.tenant_id == self._tenant_id,
                    OrgRuleModel.rule_id == rule_id,
                )
                .first()
            )
            if not row:
                return False
            session.delete(row)
        return True

    # ------------------------------------------------------------------
    # Evaluation
    # ------------------------------------------------------------------

    def evaluate_access(
        self,
        user_id: str,
        role_id: str,
        org_context: dict[str, list[str]] | None = None,
    ) -> EvaluationResult:
        """
        Evaluate whether a user's org assignments permit the requested role.

        Parameters
        ----------
        user_id:     The user being evaluated.
        role_id:     The role being requested.
        org_context: Optional explicit org values to check against.
                     Falls back to stored user assignments from the DB.

        Returns
        -------
        EvaluationResult with allowed flag and any violations found.
        """
        self._ensure_seeded()

        with db_manager.session_scope() as session:
            # Resolve org context from DB if not provided explicitly
            if org_context is None:
                assignment_rows = (
                    session.query(OrgUserAssignmentModel)
                    .filter(
                        OrgUserAssignmentModel.tenant_id == self._tenant_id,
                        OrgUserAssignmentModel.user_id == user_id,
                    )
                    .all()
                )
                org_context = {a.org_field: list(a.values or []) for a in assignment_rows}

            # Load role restriction
            restriction_row = (
                session.query(OrgRoleRestrictionModel)
                .filter(
                    OrgRoleRestrictionModel.tenant_id == self._tenant_id,
                    OrgRoleRestrictionModel.role_id == role_id,
                )
                .first()
            )

            if not restriction_row:
                return EvaluationResult(
                    allowed=True,
                    user_id=user_id,
                    role_id=role_id,
                    violations=[],
                )

            rule_ids = list(restriction_row.rule_ids or [])

            # Load relevant rules in one query
            rule_rows = (
                session.query(OrgRuleModel)
                .filter(
                    OrgRuleModel.tenant_id == self._tenant_id,
                    OrgRuleModel.rule_id.in_(rule_ids),
                )
                .all()
            )
            rules_by_id = {r.rule_id: _db_row_to_value_object(r) for r in rule_rows}

        violations: list[dict[str, Any]] = []
        for rid in rule_ids:
            rule = rules_by_id.get(rid)
            if not rule or not rule.active:
                continue

            user_values = set(org_context.get(rule.org_field, []))
            allowed_set = set(rule.allowed_values)

            if rule.scope == "inclusive":
                disallowed = user_values - allowed_set
                if disallowed or not user_values:
                    violations.append({
                        "rule_id": rid,
                        "rule_name": rule.name,
                        "org_field": rule.org_field,
                        "field_label": SAP_ORG_FIELDS.get(rule.org_field, rule.org_field),
                        "scope": "inclusive",
                        "disallowed_values": sorted(disallowed),
                        "allowed_values": sorted(allowed_set),
                        "message": (
                            f"User has no valid {SAP_ORG_FIELDS.get(rule.org_field)} assignment "
                            f"matching rule '{rule.name}'"
                        ) if not user_values else (
                            f"Values {sorted(disallowed)} are outside the permitted set "
                            f"for rule '{rule.name}'"
                        ),
                    })
            elif rule.scope == "exclusive":
                denied_present = user_values & allowed_set
                if denied_present:
                    violations.append({
                        "rule_id": rid,
                        "rule_name": rule.name,
                        "org_field": rule.org_field,
                        "field_label": SAP_ORG_FIELDS.get(rule.org_field, rule.org_field),
                        "scope": "exclusive",
                        "denied_values_present": sorted(denied_present),
                        "message": (
                            f"User holds excluded {SAP_ORG_FIELDS.get(rule.org_field)} values "
                            f"{sorted(denied_present)} which are forbidden by rule '{rule.name}'"
                        ),
                    })

        return EvaluationResult(
            allowed=len(violations) == 0,
            user_id=user_id,
            role_id=role_id,
            violations=violations,
        )

    def validate_org_assignment(self, user_id: str, role_id: str) -> dict[str, Any]:
        """
        Validate whether a user's stored org assignments satisfy a role's
        org restrictions.  Thin wrapper around evaluate_access.
        """
        result = self.evaluate_access(user_id, role_id)
        return {
            "valid": result.allowed,
            "user_id": result.user_id,
            "role_id": result.role_id,
            "violations": result.violations,
            "evaluated_at": result.evaluated_at,
        }

    # ------------------------------------------------------------------
    # User / Role context queries
    # ------------------------------------------------------------------

    def get_user_org_context(self, user_id: str) -> dict[str, Any]:
        """
        Return all organizational field assignments for a user from the DB.

        Returns a dict keyed by SAP field name, with values list and
        human-readable label.
        """
        self._ensure_seeded()
        with db_manager.session_scope() as session:
            rows = (
                session.query(OrgUserAssignmentModel)
                .filter(
                    OrgUserAssignmentModel.tenant_id == self._tenant_id,
                    OrgUserAssignmentModel.user_id == user_id,
                )
                .all()
            )
            context: dict[str, Any] = {}
            for a in rows:
                context[a.org_field] = {
                    "field_label": SAP_ORG_FIELDS.get(a.org_field, a.org_field),
                    "values": list(a.values or []),
                    "assigned_at": a.assigned_at.isoformat() if a.assigned_at else None,
                }

        return {
            "user_id": user_id,
            "org_assignments": context,
            "total_fields_assigned": len(context),
        }

    def get_role_org_restrictions(self, role_id: str) -> dict[str, Any]:
        """
        Return the org-level restrictions registered for a role,
        including full rule detail fetched from the DB.
        """
        self._ensure_seeded()
        with db_manager.session_scope() as session:
            restriction_row = (
                session.query(OrgRoleRestrictionModel)
                .filter(
                    OrgRoleRestrictionModel.tenant_id == self._tenant_id,
                    OrgRoleRestrictionModel.role_id == role_id,
                )
                .first()
            )

            if not restriction_row:
                return {
                    "role_id": role_id,
                    "restrictions": [],
                    "message": "No organizational restrictions defined for this role",
                }

            rule_ids = list(restriction_row.rule_ids or [])
            rule_rows = (
                session.query(OrgRuleModel)
                .filter(
                    OrgRuleModel.tenant_id == self._tenant_id,
                    OrgRuleModel.rule_id.in_(rule_ids),
                )
                .all()
            )
            rules_detail = [self._rule_to_dict(_db_row_to_value_object(r)) for r in rule_rows]

        return {
            "role_id": role_id,
            "restrictions": rules_detail,
            "total_rules": len(rules_detail),
        }

    def set_role_org_restrictions(self, role_id: str, rule_ids: list[str]) -> dict[str, Any]:
        """
        Attach a set of org rules to a role, replacing any existing restrictions.
        Validates that every supplied rule_id exists in the DB first.
        """
        self._ensure_seeded()
        with db_manager.session_scope() as session:
            # Validate all rule IDs exist for this tenant
            existing_ids = {
                r.rule_id
                for r in session.query(OrgRuleModel.rule_id)
                .filter(
                    OrgRuleModel.tenant_id == self._tenant_id,
                    OrgRuleModel.rule_id.in_(rule_ids),
                )
                .all()
            }
            missing = [rid for rid in rule_ids if rid not in existing_ids]
            if missing:
                raise ValueError(f"Unknown rule IDs: {missing}")

            # Upsert the role restriction row
            restriction_row = (
                session.query(OrgRoleRestrictionModel)
                .filter(
                    OrgRoleRestrictionModel.tenant_id == self._tenant_id,
                    OrgRoleRestrictionModel.role_id == role_id,
                )
                .first()
            )
            if restriction_row:
                restriction_row.rule_ids = rule_ids
            else:
                session.add(OrgRoleRestrictionModel(
                    tenant_id=self._tenant_id,
                    role_id=role_id,
                    rule_ids=rule_ids,
                ))

        return self.get_role_org_restrictions(role_id)

    # ------------------------------------------------------------------
    # Org hierarchy  (static reference data — no DB involvement)
    # ------------------------------------------------------------------

    def get_org_hierarchy(self) -> dict[str, Any]:
        """
        Return the organizational hierarchy tree representing the
        relationships between controlling areas, company codes, plants,
        purchasing orgs, sales orgs, and cost centers.
        """
        return {
            "hierarchy": {
                "CORP": {
                    "label": "Corporate Controlling Area",
                    "org_field": "KOKRS",
                    "company_codes": {
                        "1000": {
                            "label": "US HQ",
                            "org_field": "BUKRS",
                            "plants": {
                                "P001": {"label": "US Manufacturing Plant 1", "org_field": "WERKS"},
                                "P002": {"label": "US Manufacturing Plant 2", "org_field": "WERKS"},
                                "D001": {"label": "US Distribution Center 1", "org_field": "WERKS"},
                            },
                            "cost_centers": {
                                "FIN01": {"label": "US Finance", "org_field": "KOSTL"},
                                "FIN02": {"label": "US Controlling", "org_field": "KOSTL"},
                            },
                        },
                        "1100": {
                            "label": "US Subsidiary",
                            "org_field": "BUKRS",
                            "plants": {
                                "S001": {"label": "US Service Depot", "org_field": "WERKS"},
                            },
                            "cost_centers": {
                                "FIN03": {"label": "US Sub Finance", "org_field": "KOSTL"},
                            },
                        },
                        "2000": {
                            "label": "Germany HQ",
                            "org_field": "BUKRS",
                            "plants": {
                                "EU01": {"label": "DE Manufacturing", "org_field": "WERKS"},
                                "EU02": {"label": "DE Distribution", "org_field": "WERKS"},
                            },
                        },
                        "2100": {
                            "label": "France Subsidiary",
                            "org_field": "BUKRS",
                            "plants": {
                                "EU03": {"label": "FR Plant", "org_field": "WERKS"},
                            },
                        },
                        "2200": {
                            "label": "UK Subsidiary",
                            "org_field": "BUKRS",
                            "plants": {},
                        },
                        "3000": {
                            "label": "Japan HQ",
                            "org_field": "BUKRS",
                            "plants": {
                                "P003": {"label": "JP Manufacturing", "org_field": "WERKS"},
                            },
                        },
                        "3100": {
                            "label": "Australia Subsidiary",
                            "org_field": "BUKRS",
                            "plants": {
                                "D002": {"label": "AU Distribution", "org_field": "WERKS"},
                            },
                        },
                    },
                    "purchasing_orgs": {
                        "P001": {"label": "Central Purchasing", "org_field": "EKORG"},
                        "PL01": {"label": "US Local Purchasing", "org_field": "EKORG"},
                        "PL02": {"label": "EU Local Purchasing", "org_field": "EKORG"},
                        "PL03": {"label": "APAC Local Purchasing", "org_field": "EKORG"},
                    },
                    "sales_orgs": {
                        "S001": {"label": "Domestic Sales", "org_field": "VKORG"},
                        "S002": {"label": "Government Sales", "org_field": "VKORG"},
                    },
                },
            },
            "sap_org_fields": SAP_ORG_FIELDS,
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _rule_to_dict(self, rule: OrgRule) -> dict[str, Any]:
        return {
            "rule_id": rule.rule_id,
            "name": rule.name,
            "org_field": rule.org_field,
            "field_label": SAP_ORG_FIELDS.get(rule.org_field, rule.org_field),
            "allowed_values": rule.allowed_values,
            "scope": rule.scope,
            "description": rule.description,
            "active": rule.active,
            "created_at": rule.created_at,
            "updated_at": rule.updated_at,
        }
