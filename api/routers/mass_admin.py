"""
API Router — Mass Administration

Exposes endpoints for bulk user and role operations with async job tracking.
"""

from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from core.mass_admin.engine import MassAdminEngine

router = APIRouter(tags=["Mass Administration"])

# Per-tenant engine registry
_engines: Dict[str, MassAdminEngine] = {}


def _get_tenant_id() -> str:
    from core.tenant import get_current_tenant
    ctx = get_current_tenant()
    return ctx.tenant_id if ctx else "default"


def _get_engine(tenant_id: str = Depends(_get_tenant_id)) -> MassAdminEngine:
    if tenant_id not in _engines:
        _engines[tenant_id] = MassAdminEngine()
    return _engines[tenant_id]


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class BulkUserImportRequest(BaseModel):
    users: list[dict[str, Any]] = Field(..., description="List of user records to import")
    submitted_by: str = Field(default="system", description="Who initiated the import")


class BulkRoleAssignRequest(BaseModel):
    user_ids: list[str] = Field(..., description="User IDs to receive the roles")
    role_ids: list[str] = Field(..., description="Role IDs to assign")
    submitted_by: str = Field(default="system")


class BulkRoleRemoveRequest(BaseModel):
    user_ids: list[str] = Field(..., description="User IDs to have roles removed")
    role_ids: list[str] = Field(..., description="Role IDs to remove")
    submitted_by: str = Field(default="system")


class MassRoleChangeRequest(BaseModel):
    role_id: str = Field(..., description="The role to modify")
    changes: dict[str, Any] = Field(
        ...,
        description="Dict describing changes: add_auth, remove_auth, rename, description",
    )
    submitted_by: str = Field(default="system")


class MassOwnerUpdateRequest(BaseModel):
    role_ids: list[str] = Field(..., description="Roles whose ownership will be updated")
    new_owner: str = Field(..., description="User ID of the new role owner")
    submitted_by: str = Field(default="system")


class BulkUserLockRequest(BaseModel):
    user_ids: list[str] = Field(..., description="User IDs to lock")
    reason: str = Field(..., description="Audit reason for the lock")
    submitted_by: str = Field(default="system")


class BulkUserUnlockRequest(BaseModel):
    user_ids: list[str] = Field(..., description="User IDs to unlock")
    submitted_by: str = Field(default="system")


class PreviewImpactRequest(BaseModel):
    operation: str = Field(
        ...,
        description=(
            "Operation name: bulk_role_assign | bulk_role_remove | mass_role_change "
            "| bulk_user_import | bulk_user_lock | mass_owner_update"
        ),
    )
    params: dict[str, Any] = Field(..., description="Parameters for the operation")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/mass-admin/jobs", summary="List bulk job history")
def list_job_history(
    operation: str | None = Query(default=None, description="Filter by operation type"),
    status: str | None = Query(default=None, description="Filter by status"),
    limit: int = Query(default=50, ge=1, le=500, description="Maximum jobs to return"),
    engine: MassAdminEngine = Depends(_get_engine),
) -> dict[str, Any]:
    """Return past and in-progress bulk administration jobs."""
    return engine.get_job_history(operation=operation, status=status, limit=limit)


@router.get("/mass-admin/jobs/{job_id}", summary="Get bulk job status")
def get_job_status(
    job_id: str,
    engine: MassAdminEngine = Depends(_get_engine),
) -> dict[str, Any]:
    """Poll the status and progress of a specific bulk job."""
    result = engine.get_job_status(job_id)
    if not result:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")
    return result


@router.post("/mass-admin/preview", summary="Preview impact of a bulk operation")
def preview_impact(
    body: PreviewImpactRequest,
    engine: MassAdminEngine = Depends(_get_engine),
) -> dict[str, Any]:
    """
    Estimate the impact of a bulk operation without executing it.

    Returns projected counts and warnings. Safe to call — no data is modified.
    """
    return engine.preview_impact(operation=body.operation, params=body.params)


@router.post("/mass-admin/users/import", summary="Bulk import users", status_code=202)
def bulk_user_import(
    body: BulkUserImportRequest,
    engine: MassAdminEngine = Depends(_get_engine),
) -> dict[str, Any]:
    """
    Import a batch of user records.

    Each record must include: username, email, full_name, department.
    Optional: user_type, manager_id.

    Returns a job tracking object. Poll `/mass-admin/jobs/{job_id}` for results.
    """
    if not body.users:
        raise HTTPException(status_code=400, detail="No user records provided")
    return engine.bulk_user_import(users_data=body.users, submitted_by=body.submitted_by)


@router.post("/mass-admin/roles/assign", summary="Bulk assign roles to users", status_code=202)
def bulk_role_assign(
    body: BulkRoleAssignRequest,
    engine: MassAdminEngine = Depends(_get_engine),
) -> dict[str, Any]:
    """
    Assign one or more roles to multiple users in a single operation.

    Creates assignments for every combination of user_id x role_id provided.
    Returns a job tracking object.
    """
    if not body.user_ids:
        raise HTTPException(status_code=400, detail="No user IDs provided")
    if not body.role_ids:
        raise HTTPException(status_code=400, detail="No role IDs provided")
    return engine.bulk_role_assign(
        user_ids=body.user_ids,
        role_ids=body.role_ids,
        submitted_by=body.submitted_by,
    )


@router.post("/mass-admin/roles/remove", summary="Bulk remove roles from users", status_code=202)
def bulk_role_remove(
    body: BulkRoleRemoveRequest,
    engine: MassAdminEngine = Depends(_get_engine),
) -> dict[str, Any]:
    """
    Remove one or more roles from multiple users in a single operation.

    Returns a job tracking object.
    """
    if not body.user_ids:
        raise HTTPException(status_code=400, detail="No user IDs provided")
    if not body.role_ids:
        raise HTTPException(status_code=400, detail="No role IDs provided")
    return engine.bulk_role_remove(
        user_ids=body.user_ids,
        role_ids=body.role_ids,
        submitted_by=body.submitted_by,
    )


@router.post("/mass-admin/roles/mass-change", summary="Apply mass role change", status_code=202)
def mass_role_change(
    body: MassRoleChangeRequest,
    engine: MassAdminEngine = Depends(_get_engine),
) -> dict[str, Any]:
    """
    Apply a set of changes to a role definition and propagate those changes
    to all users currently assigned the role.

    Supported changes:
    - `add_auth`: list of authorization objects to add
    - `remove_auth`: list of authorization objects to remove
    - `rename`: new role name string
    - `description`: updated description string

    Returns a job tracking object.
    """
    if not body.changes:
        raise HTTPException(status_code=400, detail="No changes specified")
    return engine.mass_role_change(
        role_id=body.role_id,
        changes=body.changes,
        submitted_by=body.submitted_by,
    )


@router.post("/mass-admin/roles/owner", summary="Mass update role ownership", status_code=202)
def mass_owner_update(
    body: MassOwnerUpdateRequest,
    engine: MassAdminEngine = Depends(_get_engine),
) -> dict[str, Any]:
    """
    Reassign ownership of multiple roles to a new owner in one operation.

    Returns a job tracking object.
    """
    if not body.role_ids:
        raise HTTPException(status_code=400, detail="No role IDs provided")
    return engine.mass_owner_update(
        role_ids=body.role_ids,
        new_owner=body.new_owner,
        submitted_by=body.submitted_by,
    )


@router.post("/mass-admin/users/lock", summary="Bulk lock user accounts", status_code=202)
def bulk_user_lock(
    body: BulkUserLockRequest,
    engine: MassAdminEngine = Depends(_get_engine),
) -> dict[str, Any]:
    """
    Lock multiple user accounts simultaneously.

    All active sessions for the affected users will be terminated.
    The reason is written to the audit log.

    Returns a job tracking object.
    """
    if not body.user_ids:
        raise HTTPException(status_code=400, detail="No user IDs provided")
    if not body.reason.strip():
        raise HTTPException(status_code=400, detail="A reason must be provided for account locks")
    return engine.bulk_user_lock(
        user_ids=body.user_ids,
        reason=body.reason,
        submitted_by=body.submitted_by,
    )


@router.post("/mass-admin/users/unlock", summary="Bulk unlock user accounts", status_code=202)
def bulk_user_unlock(
    body: BulkUserUnlockRequest,
    engine: MassAdminEngine = Depends(_get_engine),
) -> dict[str, Any]:
    """
    Unlock multiple previously locked user accounts simultaneously.

    Returns a job tracking object.
    """
    if not body.user_ids:
        raise HTTPException(status_code=400, detail="No user IDs provided")
    return engine.bulk_user_unlock(
        user_ids=body.user_ids,
        submitted_by=body.submitted_by,
    )


@router.get("/mass-admin/operations", summary="List supported bulk operations")
def list_operations() -> dict[str, Any]:
    """Return the list of supported bulk operations and their descriptions."""
    return {
        "operations": [
            {
                "name": "bulk_user_import",
                "endpoint": "POST /mass-admin/users/import",
                "description": "Import users from a structured list",
                "required_params": ["users"],
            },
            {
                "name": "bulk_role_assign",
                "endpoint": "POST /mass-admin/roles/assign",
                "description": "Assign roles to multiple users",
                "required_params": ["user_ids", "role_ids"],
            },
            {
                "name": "bulk_role_remove",
                "endpoint": "POST /mass-admin/roles/remove",
                "description": "Remove roles from multiple users",
                "required_params": ["user_ids", "role_ids"],
            },
            {
                "name": "mass_role_change",
                "endpoint": "POST /mass-admin/roles/mass-change",
                "description": "Modify a role and propagate changes to all holders",
                "required_params": ["role_id", "changes"],
            },
            {
                "name": "mass_owner_update",
                "endpoint": "POST /mass-admin/roles/owner",
                "description": "Reassign ownership across multiple roles",
                "required_params": ["role_ids", "new_owner"],
            },
            {
                "name": "bulk_user_lock",
                "endpoint": "POST /mass-admin/users/lock",
                "description": "Lock multiple user accounts",
                "required_params": ["user_ids", "reason"],
            },
            {
                "name": "bulk_user_unlock",
                "endpoint": "POST /mass-admin/users/unlock",
                "description": "Unlock multiple user accounts",
                "required_params": ["user_ids"],
            },
        ]
    }
