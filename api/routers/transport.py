"""
Role Transport Management Router
Exposes endpoints for tracking SAP transports across DEV/QA/PROD.
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from core.transport.manager import get_transport_manager

router = APIRouter(tags=["Role Transport Management"])


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class CreateTransportRequest(BaseModel):
    transport_id: str = Field(..., description="Unique transport identifier, e.g. DEV900020")
    description: str = Field(..., description="Human-readable description of the transport")
    roles: List[str] = Field(..., description="Role IDs carried by this transport")
    source_system: str = Field("DEV", description="Source landscape system")
    owner: str = Field("basis_admin", description="Transport owner / requestor")
    depends_on: List[str] = Field(
        default_factory=list,
        description="Transport IDs that must be in PROD before this one"
    )
    priority: str = Field("medium", description="Priority: low | medium | high | critical")


class TrackImportRequest(BaseModel):
    target_system: str = Field(..., description="Target system: QA or PROD")
    status: str = Field(..., description="Import status: success | failed | rolled_back")
    error: Optional[str] = Field(None, description="Error message if status is failed")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/dashboard", summary="Transport management dashboard statistics")
async def get_dashboard() -> Dict[str, Any]:
    """
    Return high-level statistics for the transport management dashboard:
    total count, state breakdown, pending count, failures, and critical items.
    """
    manager = get_transport_manager()
    return manager.get_dashboard()


@router.get("/transports", summary="List all transports with optional filters")
async def list_transports(
    role_id: Optional[str] = Query(None, description="Filter by role name substring"),
    system: Optional[str] = Query(None, description="Filter by source system"),
    state: Optional[str] = Query(None, description="Filter by state"),
    limit: int = Query(50, ge=1, le=200, description="Maximum results"),
) -> List[Dict[str, Any]]:
    """
    Return the full transport history list with optional filtering.

    Supported states: created, released, imported_qa, imported_prod, failed, rolled_back
    """
    manager = get_transport_manager()
    return manager.get_transport_history(role_id=role_id, system=system, state=state, limit=limit)


@router.get("/pending", summary="Transports not yet imported into PROD")
async def get_pending() -> List[Dict[str, Any]]:
    """
    Return all transports that have not reached PROD and are not in a terminal
    state (rolled_back).  Results are sorted by priority (critical first).
    """
    manager = get_transport_manager()
    return manager.get_pending_transports()


@router.get("/conflicts", summary="Detect all in-flight transport conflicts")
async def get_all_conflicts() -> List[Dict[str, Any]]:
    """
    Scan all pending transports and return any that conflict with other
    in-flight transports (i.e. multiple transports touching the same role
    at the same time).
    """
    manager = get_transport_manager()
    pending = manager.get_pending_transports()
    results = []
    for t in pending:
        conflict_info = manager.detect_conflicts(t["transport_id"])
        if conflict_info["conflicts_found"]:
            results.append(conflict_info)
    return results


@router.get(
    "/transports/{transport_id}",
    summary="Get a specific transport by ID"
)
async def get_transport(transport_id: str) -> Dict[str, Any]:
    """Return full details for a single transport."""
    manager = get_transport_manager()
    history = manager.get_transport_history(limit=500)
    for t in history:
        if t["transport_id"].upper() == transport_id.upper():
            return t
    raise HTTPException(status_code=404, detail=f"Transport {transport_id} not found")


@router.get(
    "/transports/{transport_id}/chain",
    summary="Full transport lifecycle chain"
)
async def get_transport_chain(transport_id: str) -> Dict[str, Any]:
    """
    Return the ordered lifecycle chain for a transport:
    created -> released -> imported_QA -> imported_PROD
    Each step includes timestamp, status, and details.
    """
    manager = get_transport_manager()
    try:
        return manager.get_transport_chain(transport_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get(
    "/transports/{transport_id}/dependencies",
    summary="Check transport dependencies"
)
async def check_dependencies(transport_id: str) -> Dict[str, Any]:
    """
    Verify whether all transports that this one depends on have been
    successfully imported into PROD.  Returns a list of satisfied and
    unsatisfied dependencies.
    """
    manager = get_transport_manager()
    try:
        return manager.check_dependencies(transport_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/transports", summary="Register a new transport", status_code=201)
async def create_transport(body: CreateTransportRequest) -> Dict[str, Any]:
    """
    Register a new transport in the system.  The transport starts in
    'created' state and must be explicitly released and tracked through
    subsequent import steps.
    """
    manager = get_transport_manager()
    try:
        return manager.create_transport(
            transport_id=body.transport_id.upper(),
            description=body.description,
            roles=body.roles,
            source_system=body.source_system.upper(),
            owner=body.owner,
            depends_on=[d.upper() for d in body.depends_on],
            priority=body.priority,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@router.put(
    "/transports/{transport_id}/import",
    summary="Record a transport import event"
)
async def track_import(transport_id: str, body: TrackImportRequest) -> Dict[str, Any]:
    """
    Record that a transport has been imported (or failed) on a target system.

    - target_system: QA or PROD
    - status: success | failed | rolled_back
    """
    valid_statuses = {"success", "failed", "rolled_back"}
    if body.status not in valid_statuses:
        raise HTTPException(
            status_code=422,
            detail=f"status must be one of: {', '.join(sorted(valid_statuses))}"
        )

    valid_systems = {"QA", "PROD"}
    if body.target_system.upper() not in valid_systems:
        raise HTTPException(
            status_code=422,
            detail=f"target_system must be one of: {', '.join(sorted(valid_systems))}"
        )

    manager = get_transport_manager()
    try:
        return manager.track_import(
            transport_id=transport_id.upper(),
            target_system=body.target_system,
            status=body.status,
            error=body.error,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
