"""
Audit Evidence Agent API Router

Exposes the AI-driven evidence collection agent over HTTP.
All endpoints are authenticated via the shared get_current_user dependency
wired at include_router time in api/main.py.

Endpoints
---------
GET  /evidence-agent/requirements          — List all collectable requirement types
POST /evidence-agent/collect               — Auto-collect evidence for a requirement
POST /evidence-agent/assess-control        — Assess evidence coverage for a PC control
"""

from fastapi import APIRouter, Depends, HTTPException, Body

from core.tenant import get_current_tenant
from db.database import db_manager

router = APIRouter(tags=["Audit Evidence Agent"])


# ---------------------------------------------------------------------------
# Tenant resolution — consistent with the existing per-tenant engine pattern
# ---------------------------------------------------------------------------

def _get_tenant_id() -> str:
    """Resolve current tenant from middleware context."""
    try:
        ctx = get_current_tenant()
        return ctx.tenant_id if ctx else "default"
    except Exception:
        return "default"


# ===========================================================================
# GET /requirements
# ===========================================================================

@router.get("/requirements")
def list_requirements(tenant_id: str = Depends(_get_tenant_id)):
    """
    List all control requirement types the evidence agent can collect evidence for.

    Returns each type with its description and the data sources it queries.
    """
    from core.audit_management.evidence_agent import AuditEvidenceAgent
    with db_manager.session_scope() as db:
        agent = AuditEvidenceAgent(tenant_id, db)
        return agent.list_available_requirements()


# ===========================================================================
# POST /collect
# ===========================================================================

@router.post("/collect")
def collect_evidence(
    body: dict = Body(...),
    tenant_id: str = Depends(_get_tenant_id),
):
    """
    Auto-collect and assemble an evidence package for a control requirement.

    Body fields
    -----------
    requirement_type : str  — One of the types returned by /requirements
    period_start     : str  — ISO-8601 date (optional, defaults to 90 days ago)
    period_end       : str  — ISO-8601 date (optional, defaults to now)

    Returns a signed evidence package with completeness score, per-source
    record counts, gaps, and an AI assessment narrative.
    """
    from core.audit_management.evidence_agent import AuditEvidenceAgent
    with db_manager.session_scope() as db:
        agent = AuditEvidenceAgent(tenant_id, db)
        result = agent.collect_evidence(
            body.get("requirement_type", ""),
            body.get("period_start"),
            body.get("period_end"),
        )
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        return result


# ===========================================================================
# POST /assess-control
# ===========================================================================

@router.post("/assess-control")
def assess_control(
    body: dict = Body(...),
    tenant_id: str = Depends(_get_tenant_id),
):
    """
    Assess evidence coverage for a specific Process Control.

    Body fields
    -----------
    control_id : str  — The control_id of the ProcessControl record

    Returns test count, evidence document count, missing items, coverage
    percentage, and a recommended next action.
    """
    from core.audit_management.evidence_agent import AuditEvidenceAgent
    with db_manager.session_scope() as db:
        agent = AuditEvidenceAgent(tenant_id, db)
        result = agent.assess_control_evidence(body.get("control_id", ""))
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
        return result
