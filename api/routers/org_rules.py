"""
API Router — Organizational Rules

Exposes endpoints for managing SAP organizational-scoping rules and
evaluating whether user org assignments satisfy role restrictions.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from core.org_rules.engine import OrgRulesEngine

router = APIRouter(tags=["Organizational Rules"])

_engine = OrgRulesEngine()


# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------

class DefineRuleRequest(BaseModel):
    name: str = Field(..., description="Human-readable name for the rule")
    org_field: str = Field(..., description="SAP org field: BUKRS, WERKS, EKORG, VKORG, KOSTL, KOKRS")
    values: list[str] = Field(..., description="List of field values to allow or deny")
    scope: str = Field(..., description="'inclusive' or 'exclusive'")
    description: str = Field(default="", description="Optional description")


class UpdateRuleRequest(BaseModel):
    name: str | None = None
    values: list[str] | None = None
    scope: str | None = None
    description: str | None = None
    active: bool | None = None


class EvaluateAccessRequest(BaseModel):
    user_id: str = Field(..., description="User identifier")
    role_id: str = Field(..., description="Role identifier")
    org_context: dict[str, list[str]] | None = Field(
        default=None,
        description="Explicit org values to test. Omit to use stored user assignments.",
    )


class SetRoleRestrictionsRequest(BaseModel):
    rule_ids: list[str] = Field(..., description="Rule IDs to attach to the role")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/org-rules", summary="List all organizational rules")
def list_org_rules(
    active_only: bool = Query(default=False, description="Return only active rules"),
    org_field: str | None = Query(default=None, description="Filter by SAP org field"),
) -> dict[str, Any]:
    """Return all defined organizational scoping rules with optional filters."""
    rules = _engine.list_rules()
    if active_only:
        rules = [r for r in rules if r["active"]]
    if org_field:
        rules = [r for r in rules if r["org_field"] == org_field.upper()]
    return {"rules": rules, "total": len(rules)}


@router.get("/org-rules/hierarchy", summary="Get organizational hierarchy tree")
def get_org_hierarchy() -> dict[str, Any]:
    """
    Return the full organizational hierarchy tree showing relationships
    between controlling areas, company codes, plants, purchasing orgs,
    sales orgs, and cost centers.
    """
    return _engine.get_org_hierarchy()


@router.get("/org-rules/{rule_id}", summary="Get a specific organizational rule")
def get_org_rule(rule_id: str) -> dict[str, Any]:
    """Return a single org rule by its ID."""
    rule = _engine.get_rule(rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail=f"Rule '{rule_id}' not found")
    return rule


@router.post("/org-rules", summary="Create a new organizational rule", status_code=201)
def create_org_rule(body: DefineRuleRequest) -> dict[str, Any]:
    """
    Define a new organizational scoping rule.

    - **name**: A descriptive label.
    - **org_field**: One of BUKRS, WERKS, EKORG, VKORG, KOSTL, KOKRS.
    - **values**: The field values to allow or deny.
    - **scope**: `inclusive` — only listed values permitted; `exclusive` — listed values denied.
    """
    try:
        rule = _engine.define_rule(
            name=body.name,
            org_field=body.org_field.upper(),
            values=body.values,
            scope=body.scope,
            description=body.description,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return _engine.get_rule(rule.rule_id)


@router.put("/org-rules/{rule_id}", summary="Update an existing organizational rule")
def update_org_rule(rule_id: str, body: UpdateRuleRequest) -> dict[str, Any]:
    """Update one or more fields of an existing org rule."""
    try:
        updated = _engine.update_rule(
            rule_id=rule_id,
            name=body.name,
            values=body.values,
            scope=body.scope,
            description=body.description,
            active=body.active,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if not updated:
        raise HTTPException(status_code=404, detail=f"Rule '{rule_id}' not found")
    return updated


@router.delete("/org-rules/{rule_id}", summary="Delete an organizational rule")
def delete_org_rule(rule_id: str) -> dict[str, Any]:
    """Permanently remove an org rule by ID."""
    deleted = _engine.delete_rule(rule_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Rule '{rule_id}' not found")
    return {"deleted": True, "rule_id": rule_id}


@router.post("/org-rules/evaluate", summary="Evaluate org access for a user and role")
def evaluate_access(body: EvaluateAccessRequest) -> dict[str, Any]:
    """
    Evaluate whether a user's organizational assignments satisfy the
    restrictions attached to a requested role.

    Returns an `allowed` flag plus details of any violations.
    """
    result = _engine.evaluate_access(
        user_id=body.user_id,
        role_id=body.role_id,
        org_context=body.org_context,
    )
    return {
        "allowed": result.allowed,
        "user_id": result.user_id,
        "role_id": result.role_id,
        "violations": result.violations,
        "violation_count": len(result.violations),
        "evaluated_at": result.evaluated_at,
    }


@router.get("/org-rules/users/{user_id}/context", summary="Get user org context")
def get_user_org_context(user_id: str) -> dict[str, Any]:
    """Return all organizational field assignments for a specific user."""
    return _engine.get_user_org_context(user_id)


@router.get("/org-rules/roles/{role_id}/restrictions", summary="Get role org restrictions")
def get_role_restrictions(role_id: str) -> dict[str, Any]:
    """Return the organizational scoping rules attached to a role."""
    return _engine.get_role_org_restrictions(role_id)


@router.put("/org-rules/roles/{role_id}/restrictions", summary="Set role org restrictions")
def set_role_restrictions(role_id: str, body: SetRoleRestrictionsRequest) -> dict[str, Any]:
    """
    Attach a set of org rules to a role.  Replaces any previously attached rules.
    """
    try:
        return _engine.set_role_org_restrictions(role_id, body.rule_ids)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/org-rules/validate-assignment", summary="Validate user-role org assignment")
def validate_assignment(
    user_id: str = Query(..., description="User identifier"),
    role_id: str = Query(..., description="Role identifier"),
) -> dict[str, Any]:
    """
    Quick validation check: does the user's current org assignment satisfy
    all restrictions for the given role?  Returns valid flag and violations.
    """
    return _engine.validate_org_assignment(user_id, role_id)
