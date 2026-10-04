"""
Role Redesign Copilot — API Router

Exposes the SAP Role Redesign Copilot engine that analyzes an organization's
entire role landscape and recommends consolidation, cleanup, and SoD-clean redesign.
"""

from fastapi import APIRouter, Depends, HTTPException, Body
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional

from api.dependencies import get_current_user
from core.tenant import get_current_tenant
from db.database import db_manager

router = APIRouter()


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class RoleRiskCheckRequest(BaseModel):
    permissions: List[str] = Field(default_factory=list, description="List of permission/T-code strings to check")
    system: str = Field(default="SAP", description="Source system identifier")
    role_name: Optional[str] = Field(default=None, description="Proposed role name (optional)")


class RoleMiningRequest(BaseModel):
    department: Optional[str] = Field(default=None, description="Department to mine roles for")
    threshold: float = Field(default=0.70, ge=0.0, le=1.0, description="Similarity threshold for clustering")
    min_users: int = Field(default=2, ge=1, description="Minimum users sharing permissions to form a cluster")
    system: str = Field(default="SAP", description="Source system identifier")


def _get_tenant_id() -> str:
    ctx = get_current_tenant()
    return ctx.tenant_id if ctx else "default"


@router.get("/analyze")
def analyze_landscape(tenant_id: str = Depends(_get_tenant_id)):
    """Full role landscape analysis.

    Scans all active roles, user assignments, and risk data to produce a
    comprehensive intelligence report including unused roles, duplicates,
    similar roles, high-risk roles, overprovisioned users, and consolidation
    proposals.
    """
    from core.role_intelligence.copilot import RoleRedesignCopilot
    with db_manager.session_scope() as db:
        copilot = RoleRedesignCopilot(tenant_id, db)
        return copilot.analyze_landscape()


@router.get("/executive-summary")
def executive_summary(tenant_id: str = Depends(_get_tenant_id)):
    """Executive summary of role landscape.

    Returns a health score, key metrics, and a prioritised action plan
    suitable for presenting to senior stakeholders.
    """
    from core.role_intelligence.copilot import RoleRedesignCopilot
    with db_manager.session_scope() as db:
        copilot = RoleRedesignCopilot(tenant_id, db)
        analysis = copilot.analyze_landscape()
        return copilot.generate_executive_summary(analysis)


@router.post("/propose-split")
def propose_split(
    body: dict = Body(...),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Propose splitting a role with SoD conflicts into clean sub-roles.

    Body: ``{"role_id": "<business role id>"}``

    Analyses the T-code entitlements granted through the target role,
    categorises them by business function, and returns a set of proposed
    replacement roles along with a step-by-step migration and test plan.
    """
    from core.role_intelligence.copilot import RoleRedesignCopilot
    role_id = body.get("role_id")
    if not role_id:
        raise HTTPException(status_code=400, detail="role_id required")
    with db_manager.session_scope() as db:
        copilot = RoleRedesignCopilot(tenant_id, db)
        result = copilot.propose_role_split(role_id)
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
        return result


@router.post("/roles/risk-check", summary="Design-time SoD risk check for a proposed role")
def roles_risk_check(
    body: RoleRiskCheckRequest,
    tenant_id: str = Depends(_get_tenant_id),
    _: Dict[str, Any] = Depends(get_current_user),
):
    """
    Check a proposed set of permissions/T-codes for SoD conflicts before the role is created.

    Runs the full SoD rule engine against the supplied permission list and returns
    any violations, risk level, and remediation suggestions.
    """
    from core.rules import RuleEngine
    from core.rules.models import Entitlement, UserAccess

    engine = RuleEngine()

    # Build synthetic entitlements from the permission list
    entitlements = []
    for perm in body.permissions:
        parts = perm.split(":")
        if len(parts) >= 3:
            # format: system:auth_object:field:value
            entitlements.append(
                Entitlement(system=parts[0], auth_object=parts[1], field=parts[2], value=parts[3] if len(parts) > 3 else "*")
            )
        elif len(parts) == 2:
            # format: auth_object:value
            entitlements.append(
                Entitlement(system=body.system, auth_object=parts[0], field="TCD", value=parts[1])
            )
        else:
            # bare T-code
            entitlements.append(
                Entitlement(system=body.system, auth_object="S_TCODE", field="TCD", value=perm)
            )

    if not entitlements:
        return {
            "proposed_role": body.role_name,
            "system": body.system,
            "permissions_checked": 0,
            "violations": [],
            "violation_count": 0,
            "risk_level": "low",
            "is_clean": True,
            "recommendations": [],
        }

    proposed_user = UserAccess(
        user_id=f"__proposed__{body.role_name or 'role'}",
        username="__proposed__",
        full_name="Proposed Role Check",
        department="",
        entitlements=entitlements,
    )

    violations_objs = engine.evaluate_user(proposed_user)
    violations = [
        {
            "violation_id": v.violation_id,
            "rule_id": v.rule_id,
            "rule_name": v.rule_name,
            "severity": v.severity.name.lower() if hasattr(v.severity, "name") else str(v.severity),
            "description": v.description,
        }
        for v in violations_objs
    ]

    risk_level = "critical" if any(v["severity"] == "critical" for v in violations) else \
                 "high" if any(v["severity"] == "high" for v in violations) else \
                 "medium" if violations else "low"

    return {
        "proposed_role": body.role_name,
        "system": body.system,
        "permissions_checked": len(body.permissions),
        "violations": violations,
        "violation_count": len(violations),
        "risk_level": risk_level,
        "is_clean": len(violations) == 0,
        "recommendations": [
            f"Remove conflicting permission group: {v['rule_name']}"
            for v in violations[:5]
        ],
    }


@router.post("/roles/mining", summary="Mine role patterns from user access data")
def roles_mining(
    body: RoleMiningRequest,
    tenant_id: str = Depends(_get_tenant_id),
    _: Dict[str, Any] = Depends(get_current_user),
):
    """
    Analyse existing user-permission assignments to discover natural role clusters.

    Uses the RoleIntelligenceEngine to identify groups of users with similar
    access patterns and propose consolidated role definitions.
    """
    from core.role_intelligence import RoleIntelligenceEngine

    engine = RoleIntelligenceEngine(tenant_id=tenant_id)
    overview = engine.get_overview()

    # Build mining result from intelligence engine data
    clusters = []
    try:
        consolidation_data = engine.get_consolidation_candidates(threshold=body.threshold)
        groups = consolidation_data.get("consolidation_groups", [])
        for i, group in enumerate(groups):
            roles_in_group = group.get("roles", [])
            if len(roles_in_group) < body.min_users:
                continue
            # Derive a proposed role name from department or group pattern
            dept_suffix = f"_{body.department.replace(' ', '_').upper()}" if body.department else ""
            clusters.append({
                "cluster_id": f"MINED-{i + 1:03d}",
                "proposed_role_name": f"Z_MINED{dept_suffix}_{i + 1:03d}",
                "user_count": group.get("total_users", len(roles_in_group)),
                "source_roles": [r.get("role_id", r) if isinstance(r, dict) else r for r in roles_in_group[:10]],
                "similarity_score": group.get("similarity_score", body.threshold),
                "department": body.department,
                "system": body.system,
            })
    except Exception:
        pass

    return {
        "department": body.department,
        "system": body.system,
        "threshold": body.threshold,
        "min_users": body.min_users,
        "clusters_found": len(clusters),
        "proposed_roles": clusters,
        "total_roles_analyzed": overview.get("total_roles", 0),
        "mining_status": "completed",
    }
