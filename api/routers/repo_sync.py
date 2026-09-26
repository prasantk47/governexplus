"""
API Router — Repository Sync

Exposes endpoints for managing and monitoring synchronization of identity
and authorization data from connected external systems.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from core.repo_sync.engine import RepoSyncEngine

router = APIRouter(tags=["Repository Sync"])

_engine = RepoSyncEngine()


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class ScheduleSyncRequest(BaseModel):
    interval_minutes: int = Field(
        ...,
        ge=0,
        description="Sync interval in minutes. Use 0 to disable scheduling (manual only).",
    )
    enabled: bool = Field(default=True, description="Whether the system sync is active")


class CancelSyncRequest(BaseModel):
    job_id: str = Field(..., description="Job ID of the running sync to cancel")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/repo-sync/dashboard", summary="Sync status dashboard for all systems")
def get_sync_dashboard() -> dict[str, Any]:
    """
    Return an overview of sync health across all connected systems,
    including last sync time, status, scheduled next run, and record totals.
    """
    return _engine.get_sync_dashboard()


@router.get("/repo-sync/systems", summary="List all connected systems")
def list_systems() -> dict[str, Any]:
    """Return summary information for all registered connected systems."""
    systems = _engine.list_systems()
    return {"systems": systems, "total": len(systems)}


@router.get("/repo-sync/systems/{system_id}/status", summary="Get sync status for a system")
def get_sync_status(system_id: str) -> dict[str, Any]:
    """Return the current sync status and latest job summary for a specific system."""
    try:
        return _engine.get_sync_status(system_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/repo-sync/systems/{system_id}/history", summary="Get sync history for a system")
def get_sync_history(
    system_id: str,
    sync_type: str | None = Query(
        default=None,
        description="Filter by sync type: users | roles | authorizations | usage | full",
    ),
    limit: int = Query(default=20, ge=1, le=200),
) -> dict[str, Any]:
    """
    Return the sync run history for a specific system.

    Filter by sync_type (users, roles, authorizations, usage, full) and
    control the number of results with limit.
    """
    try:
        return _engine.get_sync_history(system_id, sync_type=sync_type, limit=limit)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/repo-sync/systems/{system_id}/sync/users", summary="Sync users from a system", status_code=202)
def sync_users(
    system_id: str,
    triggered_by: str = Query(default="api"),
) -> dict[str, Any]:
    """
    Synchronize user master data from the specified system into the repository.

    Reads all user records from the source, compares with the local repository,
    and applies add/update/delete deltas. Returns a sync job record.
    """
    try:
        return _engine.sync_users(system_id, triggered_by=triggered_by)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/repo-sync/systems/{system_id}/sync/roles", summary="Sync roles from a system", status_code=202)
def sync_roles(
    system_id: str,
    triggered_by: str = Query(default="api"),
) -> dict[str, Any]:
    """
    Synchronize role definitions and composite role memberships from a system.
    """
    try:
        return _engine.sync_roles(system_id, triggered_by=triggered_by)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/repo-sync/systems/{system_id}/sync/authorizations", summary="Sync authorization data", status_code=202)
def sync_authorizations(
    system_id: str,
    triggered_by: str = Query(default="api"),
) -> dict[str, Any]:
    """
    Synchronize authorization object values assigned to users and roles
    from the specified system.
    """
    try:
        return _engine.sync_authorizations(system_id, triggered_by=triggered_by)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/repo-sync/systems/{system_id}/sync/usage", summary="Sync transaction usage logs", status_code=202)
def sync_usage(
    system_id: str,
    triggered_by: str = Query(default="api"),
) -> dict[str, Any]:
    """
    Synchronize transaction usage logs from the specified system.

    Equivalent to extracting SAP SM20 / STAD data for usage analysis
    and risk scoring.
    """
    try:
        return _engine.sync_usage(system_id, triggered_by=triggered_by)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/repo-sync/systems/{system_id}/sync/full", summary="Run full sync for a system", status_code=202)
def full_sync(
    system_id: str,
    triggered_by: str = Query(default="api"),
) -> dict[str, Any]:
    """
    Execute a full synchronization of all data types (users, roles, authorizations,
    usage) from the specified system sequentially.

    This is the most comprehensive sync operation and may take several minutes
    for large systems.
    """
    try:
        return _engine.full_sync(system_id, triggered_by=triggered_by)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.put("/repo-sync/systems/{system_id}/schedule", summary="Set sync schedule for a system")
def schedule_sync(system_id: str, body: ScheduleSyncRequest) -> dict[str, Any]:
    """
    Set or update the automatic sync schedule for a connected system.

    - Set `interval_minutes` to a positive integer to enable scheduled syncs.
    - Set `interval_minutes` to 0 to switch to manual-only mode.
    - Set `enabled` to false to completely disable syncing for the system.
    """
    try:
        return _engine.schedule_sync(
            system_id=system_id,
            interval_minutes=body.interval_minutes,
            enabled=body.enabled,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/repo-sync/cancel", summary="Cancel a running sync job")
def cancel_sync(body: CancelSyncRequest) -> dict[str, Any]:
    """
    Cancel a running sync job by its job ID.

    Only jobs in `running` state can be cancelled.  Completed or failed jobs
    will return a descriptive error.
    """
    try:
        return _engine.cancel_sync(body.job_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/repo-sync/sync-types", summary="List supported sync types")
def list_sync_types() -> dict[str, Any]:
    """Return the list of supported data sync types and their descriptions."""
    return {
        "sync_types": [
            {
                "type": "users",
                "description": "User master data (SU01 equivalent)",
                "typical_volume": "1,000 – 100,000 records",
                "typical_duration_seconds": "30 – 300",
            },
            {
                "type": "roles",
                "description": "Role and composite role definitions",
                "typical_volume": "100 – 5,000 records",
                "typical_duration_seconds": "15 – 120",
            },
            {
                "type": "authorizations",
                "description": "Authorization object values assigned to users and roles",
                "typical_volume": "10,000 – 500,000 records",
                "typical_duration_seconds": "120 – 1800",
            },
            {
                "type": "usage",
                "description": "Transaction usage logs (SM20 / STAD equivalent)",
                "typical_volume": "50,000 – 5,000,000 records",
                "typical_duration_seconds": "120 – 3600",
            },
            {
                "type": "full",
                "description": "All sync types executed sequentially",
                "typical_volume": "Depends on all types combined",
                "typical_duration_seconds": "300 – 7200",
            },
        ]
    }
