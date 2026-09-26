"""
Approver Management API Router

Endpoints for managing approver personas — who holds each
approver role (LINE_MANAGER, SECURITY_OFFICER, CISO, etc.).
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Header
from typing import Optional, List
from sqlalchemy.orm import Session

from db.database import get_db
from api.dependencies import get_current_user as _get_jwt_user
from services.approver_service import ApproverService
from api.schemas.approver import (
    ApproverCreate, ApproverUpdate,
    ApproverSummary, ApproverDetailResponse,
    PaginatedApproversResponse, ApproverStatsResponse,
    ApproverTypeInfo,
    SetOOORequest, ToggleAvailabilityRequest,
)

router = APIRouter(tags=["Approver Management"])

DEFAULT_TENANT = "tenant_default"


def get_tenant_id(x_tenant_id: Optional[str] = Header(None)) -> str:
    """Get tenant ID from header or use default"""
    return x_tenant_id or DEFAULT_TENANT


def get_current_user(user: dict = Depends(_get_jwt_user)) -> str:
    """Extract user_id from verified JWT payload."""
    return user.get("sub", "system")


# =============================================================================
# List & Stats
# =============================================================================

@router.get("/", response_model=PaginatedApproversResponse)
async def list_approvers(
    search: Optional[str] = Query(None, description="Search by name, ID, email, or department"),
    approver_type: Optional[str] = Query(None, description="Filter by approver type"),
    status: Optional[str] = Query(None, description="Filter by status (active, inactive, suspended)"),
    is_available: Optional[bool] = Query(None, description="Filter by availability"),
    limit: int = Query(100, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id)
):
    """List all approvers with pagination and filters."""
    service = ApproverService(db)
    return service.list_approvers(
        tenant_id=tenant_id,
        search=search,
        approver_type=approver_type,
        status=status,
        is_available=is_available,
        limit=limit,
        offset=offset
    )


@router.get("/stats", response_model=ApproverStatsResponse)
async def get_approver_stats(
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id)
):
    """Get approver statistics (total, active, available, OOO, by type)."""
    service = ApproverService(db)
    return service.get_stats(tenant_id)


@router.get("/types", response_model=List[ApproverTypeInfo])
async def get_approver_types():
    """Get all approver types with labels and descriptions."""
    return ApproverService.get_approver_types()


# =============================================================================
# CRUD
# =============================================================================

@router.get("/{approver_id}", response_model=ApproverDetailResponse)
async def get_approver(
    approver_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id)
):
    """Get a single approver by ID."""
    service = ApproverService(db)
    approver = service.get_approver(tenant_id, approver_id)
    if not approver:
        raise HTTPException(status_code=404, detail=f"Approver '{approver_id}' not found")
    return approver


@router.post("/", response_model=ApproverSummary, status_code=201)
async def create_approver(
    data: ApproverCreate,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
    current_user: str = Depends(get_current_user)
):
    """Create a new approver."""
    service = ApproverService(db)
    try:
        return service.create_approver(tenant_id, data, current_user)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{approver_id}", response_model=ApproverSummary)
async def update_approver(
    approver_id: str,
    data: ApproverUpdate,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
    current_user: str = Depends(get_current_user)
):
    """Update an existing approver."""
    service = ApproverService(db)
    result = service.update_approver(tenant_id, approver_id, data, current_user)
    if not result:
        raise HTTPException(status_code=404, detail=f"Approver '{approver_id}' not found")
    return result


@router.delete("/{approver_id}")
async def delete_approver(
    approver_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
    current_user: str = Depends(get_current_user)
):
    """Soft-delete an approver."""
    service = ApproverService(db)
    success = service.delete_approver(tenant_id, approver_id, current_user)
    if not success:
        raise HTTPException(status_code=404, detail=f"Approver '{approver_id}' not found")
    return {"success": True, "message": f"Approver '{approver_id}' deleted"}


# =============================================================================
# Availability & OOO
# =============================================================================

@router.post("/{approver_id}/toggle-availability", response_model=ApproverSummary)
async def toggle_availability(
    approver_id: str,
    data: ToggleAvailabilityRequest,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
    current_user: str = Depends(get_current_user)
):
    """Toggle approver availability on/off."""
    service = ApproverService(db)
    result = service.toggle_availability(tenant_id, approver_id, data.is_available, current_user)
    if not result:
        raise HTTPException(status_code=404, detail=f"Approver '{approver_id}' not found")
    return result


@router.post("/{approver_id}/set-ooo", response_model=ApproverSummary)
async def set_ooo(
    approver_id: str,
    data: SetOOORequest,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
    current_user: str = Depends(get_current_user)
):
    """Set approver as out-of-office with optional delegate and reason."""
    service = ApproverService(db)
    result = service.set_ooo(
        tenant_id, approver_id, data.ooo_until, data.delegate_id, current_user,
        reason=data.reason
    )
    if not result:
        raise HTTPException(status_code=404, detail=f"Approver '{approver_id}' not found")
    return result


@router.post("/{approver_id}/clear-ooo", response_model=ApproverSummary)
async def clear_ooo(
    approver_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
    current_user: str = Depends(get_current_user)
):
    """Clear out-of-office status."""
    service = ApproverService(db)
    result = service.clear_ooo(tenant_id, approver_id, current_user)
    if not result:
        raise HTTPException(status_code=404, detail=f"Approver '{approver_id}' not found")
    return result
