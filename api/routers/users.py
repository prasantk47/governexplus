"""
Users API Router

Endpoints for user management, role assignments, and entitlement queries.
Enterprise-grade implementation with PostgreSQL persistence.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Header
from typing import List, Optional, Dict
from datetime import datetime

from sqlalchemy.orm import Session
from db.database import get_db

from services.user_service import UserService
from api.schemas.user import (
    UserCreate,
    UserUpdate,
    UserFilters,
    UserSummary,
    UserDetailResponse,
    UserResponse,
    PaginatedUsersResponse,
    UserStatsResponse,
    RoleAssignment,
    RoleInfo,
    UserStatus,
    RiskLevel,
    UserType,
)

router = APIRouter(tags=["Users"])

# Default tenant for demo (in production, get from auth context)
DEFAULT_TENANT = "tenant_default"


def get_tenant_id(x_tenant_id: Optional[str] = Header(None)) -> str:
    """Get tenant ID from header or use default"""
    return x_tenant_id or DEFAULT_TENANT


def get_current_user() -> str:
    """Get current user from auth context (simplified for demo)"""
    return "system"


# =============================================================================
# User CRUD Endpoints
# =============================================================================

@router.get("/", response_model=PaginatedUsersResponse)
async def list_users(
    search: Optional[str] = Query(None, description="Search by name, email, or ID"),
    status: Optional[str] = Query(None, description="Filter by status"),
    department: Optional[str] = Query(None, description="Filter by department"),
    risk_level: Optional[str] = Query(None, description="Filter by risk level"),
    user_type: Optional[str] = Query(None, description="Filter by user type"),
    has_violations: Optional[bool] = Query(None, description="Filter users with violations"),
    limit: int = Query(100, le=1000, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id)
):
    """
    List all users with pagination and filters.

    - **search**: Search across name, email, user_id, username
    - **status**: active, inactive, suspended, locked
    - **department**: Filter by department name
    - **risk_level**: low, medium, high, critical
    - **has_violations**: true/false to filter by violation status
    """
    service = UserService(db)

    filters = UserFilters(
        search=search,
        status=UserStatus(status) if status else None,
        department=department,
        risk_level=RiskLevel(risk_level) if risk_level else None,
        user_type=UserType(user_type) if user_type else None,
        has_violations=has_violations
    )

    return service.list_users(tenant_id, filters, limit, offset)


@router.get("/stats", response_model=UserStatsResponse)
async def get_user_statistics(
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id)
):
    """
    Get user statistics for dashboard.

    Returns counts by status, risk level, and department breakdown.
    """
    service = UserService(db)
    return service.get_user_stats(tenant_id)


@router.get("/departments", response_model=List[str])
async def list_departments(
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id)
):
    """
    Get list of unique departments.
    """
    service = UserService(db)
    return service.get_departments(tenant_id)


@router.get("/{user_id}", response_model=UserDetailResponse)
async def get_user(
    user_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id)
):
    """
    Get detailed information for a specific user.

    Includes roles, violations, entitlements, and risk metrics.
    """
    service = UserService(db)
    user = service.get_user(tenant_id, user_id)

    if not user:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")

    return user


@router.post("/", response_model=UserResponse, status_code=201)
async def create_user(
    user_data: UserCreate,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
    current_user: str = Depends(get_current_user)
):
    """
    Create a new user.

    Required fields: user_id, username, full_name
    """
    service = UserService(db)

    try:
        return service.create_user(tenant_id, user_data, current_user)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    user_data: UserUpdate,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
    current_user: str = Depends(get_current_user)
):
    """
    Update an existing user.

    Only provided fields will be updated.
    """
    service = UserService(db)
    user = service.update_user(tenant_id, user_id, user_data, current_user)

    if not user:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")

    return user


@router.delete("/{user_id}", status_code=204)
async def delete_user(
    user_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
    current_user: str = Depends(get_current_user)
):
    """
    Delete a user (soft delete).

    The user status is set to 'deleted' but the record is retained for audit.
    """
    service = UserService(db)
    result = service.delete_user(tenant_id, user_id, current_user)

    if not result:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")

    return None


# =============================================================================
# User Role Endpoints
# =============================================================================

@router.get("/{user_id}/roles", response_model=List[RoleInfo])
async def get_user_roles(
    user_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id)
):
    """
    Get all roles assigned to a user.
    """
    service = UserService(db)

    # Verify user exists
    user = service.get_user(tenant_id, user_id)
    if not user:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")

    return service.get_user_roles(tenant_id, user_id)


@router.post("/{user_id}/roles", response_model=RoleInfo, status_code=201)
async def assign_role_to_user(
    user_id: str,
    assignment: RoleAssignment,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
    current_user: str = Depends(get_current_user)
):
    """
    Assign a role to a user.

    Optionally specify validity period and justification.
    """
    service = UserService(db)

    result = service.assign_role(tenant_id, user_id, assignment, current_user)

    if not result:
        raise HTTPException(
            status_code=400,
            detail=f"Could not assign role. User {user_id} or role {assignment.role_id} not found."
        )

    return result


@router.delete("/{user_id}/roles/{role_id}", status_code=204)
async def revoke_role_from_user(
    user_id: str,
    role_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
    current_user: str = Depends(get_current_user)
):
    """
    Revoke a role from a user.
    """
    service = UserService(db)
    result = service.revoke_role(tenant_id, user_id, role_id, current_user)

    if not result:
        raise HTTPException(
            status_code=404,
            detail=f"Role assignment not found for user {user_id} and role {role_id}"
        )

    return None


# =============================================================================
# Risk & Violation Endpoints
# =============================================================================

@router.get("/{user_id}/risk-profile")
async def get_user_risk_profile(
    user_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id)
):
    """
    Get user's risk profile including score, violations, and sensitive access.
    """
    service = UserService(db)
    user = service.get_user(tenant_id, user_id)

    if not user:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")

    return {
        "user_id": user.user_id,
        "risk_score": user.risk_score,
        "risk_level": user.risk_level,
        "violation_count": user.violation_count,
        "active_violations": user.active_violations,
        "sensitive_access_count": user.sensitive_access_count,
        "violations": user.violations,
        "high_risk_roles": [r for r in user.roles if r.risk_level in ["high", "critical"]]
    }


@router.post("/{user_id}/recalculate-risk")
async def recalculate_user_risk(
    user_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id)
):
    """
    Recalculate user's risk score based on current violations.
    """
    service = UserService(db)
    new_score = service.recalculate_risk_score(tenant_id, user_id)

    if new_score is None:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")

    return {
        "user_id": user_id,
        "new_risk_score": new_score,
        "message": "Risk score recalculated successfully"
    }


# =============================================================================
# Entitlement Endpoints
# =============================================================================

@router.get("/{user_id}/entitlements")
async def get_user_entitlements(
    user_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id)
):
    """
    Get all entitlements (authorizations) for a user.

    Returns the expanded authorization values from all assigned roles.
    """
    service = UserService(db)
    user = service.get_user(tenant_id, user_id)

    if not user:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")

    return {
        "user_id": user_id,
        "entitlement_count": len(user.entitlements),
        "sensitive_count": user.sensitive_access_count,
        "entitlements": user.entitlements
    }


@router.get("/{user_id}/transactions")
async def get_user_transactions(
    user_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id)
):
    """
    Get all transaction codes accessible by a user.

    Filters entitlements to show only S_TCODE authorizations.
    """
    service = UserService(db)
    user = service.get_user(tenant_id, user_id)

    if not user:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")

    # Filter to S_TCODE authorizations
    tcodes = [
        {
            "tcode": e.auth_value,
            "source_role": e.source_role,
            "is_sensitive": e.is_sensitive
        }
        for e in user.entitlements
        if e.auth_object == "S_TCODE"
    ]

    # Remove duplicates
    unique_tcodes = {}
    for t in tcodes:
        if t["tcode"] not in unique_tcodes:
            unique_tcodes[t["tcode"]] = t

    return {
        "user_id": user_id,
        "transaction_count": len(unique_tcodes),
        "transactions": list(unique_tcodes.values())
    }
