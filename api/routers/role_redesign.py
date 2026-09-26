"""
Role Redesign Copilot — API Router

Exposes the SAP Role Redesign Copilot engine that analyzes an organization's
entire role landscape and recommends consolidation, cleanup, and SoD-clean redesign.
"""

from fastapi import APIRouter, Depends, HTTPException, Body

from api.dependencies import get_current_user
from core.tenant import get_current_tenant
from db.database import db_manager

router = APIRouter()


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
