"""
GRC Digital Twin API Router

Exposes the live GRC state model (GRCDigitalTwin) over HTTP.
All endpoints are authenticated via the shared get_current_user dependency
wired at include_router time in api/main.py.

Endpoints
---------
GET  /digital-twin/snapshot                  — Full point-in-time GRC snapshot
GET  /digital-twin/root-causes               — AI root-cause grouping of open findings
POST /digital-twin/what-if/user-move         — Simulate a user moving departments
GET  /digital-twin/predict-repeat-findings   — Predict controls likely to recur
"""

from fastapi import APIRouter, Depends, HTTPException, Body

from core.tenant import get_current_tenant
from db.database import db_manager

router = APIRouter(tags=["GRC Digital Twin"])


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
# GET /snapshot
# ===========================================================================

@router.get("/snapshot")
def get_snapshot(tenant_id: str = Depends(_get_tenant_id)):
    """
    Build and return a point-in-time snapshot of the full GRC state.

    Covers people, roles, risks, controls, findings, SoD violations, and
    cross-module graph connectivity statistics.
    """
    from core.intelligence.digital_twin import GRCDigitalTwin
    with db_manager.session_scope() as db:
        twin = GRCDigitalTwin(tenant_id, db)
        return twin.build_snapshot()


# ===========================================================================
# GET /root-causes
# ===========================================================================

@router.get("/root-causes")
def find_root_causes(tenant_id: str = Depends(_get_tenant_id)):
    """
    AI-powered root-cause analysis: group open findings by shared underlying risk.

    Returns distinct root-cause clusters, finding counts per cluster, and an
    insight narrative. Unlinked findings (no enterprise risk association) are
    counted separately so they can be triaged.
    """
    from core.intelligence.digital_twin import GRCDigitalTwin
    with db_manager.session_scope() as db:
        twin = GRCDigitalTwin(tenant_id, db)
        return twin.find_root_causes()


# ===========================================================================
# POST /what-if/user-move
# ===========================================================================

@router.post("/what-if/user-move")
def what_if_user_move(
    body: dict = Body(...),
    tenant_id: str = Depends(_get_tenant_id),
):
    """
    Simulate what happens to a user's access when they move departments.

    Body fields
    -----------
    user_id        : str  — The user_id of the User record
    new_department : str  — Target department name

    Returns current roles, roles to review (department-specific), roles to
    keep, recommended actions, and a risk assessment.
    """
    from core.intelligence.digital_twin import GRCDigitalTwin
    with db_manager.session_scope() as db:
        twin = GRCDigitalTwin(tenant_id, db)
        result = twin.what_if_user_move(
            body.get("user_id", ""),
            body.get("new_department", ""),
        )
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
        return result


# ===========================================================================
# GET /predict-repeat-findings
# ===========================================================================

@router.get("/predict-repeat-findings")
def predict_repeat_findings(tenant_id: str = Depends(_get_tenant_id)):
    """
    Predict which controls are likely to produce repeat audit findings.

    Controls with two or more historical findings are surfaced as medium risk;
    three or more as high risk. Results are sorted by finding count descending
    so the worst offenders appear first.
    """
    from core.intelligence.digital_twin import GRCDigitalTwin
    with db_manager.session_scope() as db:
        twin = GRCDigitalTwin(tenant_id, db)
        return twin.predict_repeat_findings()
