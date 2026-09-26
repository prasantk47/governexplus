"""
Users API Router

Endpoints for user management, role assignments, and entitlement queries.
Enterprise-grade implementation with PostgreSQL persistence.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Header
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from sqlalchemy.orm import Session
from sqlalchemy import func
from db.database import get_db
from api.dependencies import get_current_user as _get_jwt_user

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


def get_current_user(user: dict = Depends(_get_jwt_user)) -> str:
    """Extract user_id from verified JWT payload."""
    return user.get("sub", "system")


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


# =============================================================================
# AC-18: Dormant / Inactive Account Detection
# =============================================================================

# Roles that carry elevated SAP privileges — used to flag critical-access dormancy
_SENSITIVE_ROLE_PATTERNS = {
    "SAP_ALL", "SAP_NEW", "SUPER_USER", "FIREFIGHTER", "EMERGENCY",
    "BASIS_ADMIN", "SECURITY_ADMIN", "HR_SENSITIVE", "FI_POSTING",
    "S_TCODE", "S_DEVELOP", "S_RFC",
}


def _is_sensitive_role(role_name: str) -> bool:
    """Return True if the role name contains any sensitive keyword."""
    upper = role_name.upper()
    return any(pat in upper for pat in _SENSITIVE_ROLE_PATTERNS)


@router.get("/dormant", summary="Detect dormant/inactive accounts with risk context (AC-18)")
async def get_dormant_users(
    days: int = Query(90, ge=1, le=3650, description="Inactivity threshold in days (default 90)"),
    include_locked: bool = Query(False, description="Include already-locked accounts"),
    critical_only: bool = Query(False, description="Only return users with sensitive/critical access"),
    limit: int = Query(200, ge=1, le=1000, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
) -> Dict[str, Any]:
    """
    Detect user accounts that have been inactive for at least N days (AC-18).

    **Dormancy criteria**: last_login < now - days threshold (NULL last_login = never logged in).

    Each result includes:
    - **user_id**, **full_name**, **email**, **department**, **user_type**
    - **last_login**: Last recorded login timestamp (null = never)
    - **days_inactive**: Days since last login (or since account creation if never logged in)
    - **role_count**: Number of roles currently assigned
    - **has_sensitive_roles**: True if any assigned role carries elevated privileges
    - **sensitive_roles**: List of sensitive role names
    - **risk_score**: Current risk score from the User record
    - **is_locked**: Whether the account is already locked
    - **account_age_days**: Days since user record was created
    - **risk_flag**: 'CRITICAL' if dormant + has sensitive roles, 'HIGH' if dormant only

    Results are sorted by risk_flag desc, then days_inactive desc.
    """
    from db.models.user import User, UserRole, Role

    cutoff_date = datetime.utcnow() - timedelta(days=days)
    now = datetime.utcnow()

    try:
        # Base query — filter by tenant
        query = db.query(User).filter(User.tenant_id == tenant_id)

        # Apply inactivity filter:
        # last_login < cutoff (dormant) OR last_login IS NULL (never logged in)
        query = query.filter(
            (User.last_login < cutoff_date) | (User.last_login.is_(None))
        )

        # Optionally exclude already-locked accounts
        if not include_locked:
            query = query.filter(User.status != "locked")

        total_count = query.count()

        # Paginate
        users = query.order_by(
            User.last_login.asc().nullsfirst(),
        ).offset(offset).limit(limit).all()

        results: List[Dict[str, Any]] = []

        for user in users:
            # Compute days_inactive
            if user.last_login:
                days_inactive = (now - user.last_login).days
            else:
                # Never logged in — use account age as proxy
                created = getattr(user, 'created_at', None)
                days_inactive = (now - created).days if created else days

            # Account age
            created_at = getattr(user, 'created_at', None)
            account_age_days = (now - created_at).days if created_at else 0

            # Get assigned roles (join UserRole -> Role)
            user_roles = (
                db.query(UserRole, Role)
                .join(Role, UserRole.role_id == Role.id)
                .filter(UserRole.user_id == user.id)
                .all()
            )
            role_count = len(user_roles)

            # Check for sensitive roles
            sensitive_roles: List[str] = []
            for ur, role in user_roles:
                role_name = getattr(role, 'role_name', None) or getattr(role, 'name', None) or str(role.role_id)
                if _is_sensitive_role(role_name):
                    sensitive_roles.append(role_name)

            has_sensitive_roles = len(sensitive_roles) > 0

            # Apply critical_only filter
            if critical_only and not has_sensitive_roles:
                continue

            # Risk flag
            risk_flag: str
            if has_sensitive_roles and days_inactive >= days:
                risk_flag = "CRITICAL"
            elif days_inactive >= days * 2:
                risk_flag = "HIGH"
            elif has_sensitive_roles:
                risk_flag = "ELEVATED"
            else:
                risk_flag = "STANDARD"

            results.append({
                "user_id": user.user_id,
                "username": user.username,
                "full_name": user.full_name or user.username,
                "email": user.email,
                "department": user.department,
                "company_code": getattr(user, 'company_code', None),
                "user_type": user.user_type,
                "status": user.status,
                "last_login": user.last_login.isoformat() if user.last_login else None,
                "days_inactive": days_inactive,
                "account_age_days": account_age_days,
                "role_count": role_count,
                "has_sensitive_roles": has_sensitive_roles,
                "sensitive_roles": sensitive_roles,
                "risk_score": float(user.risk_score or 0),
                "is_locked": user.status == "locked",
                "risk_flag": risk_flag,
            })

        # Sort: CRITICAL > HIGH > ELEVATED > STANDARD, then days_inactive desc
        _flag_order = {"CRITICAL": 0, "HIGH": 1, "ELEVATED": 2, "STANDARD": 3}
        results.sort(key=lambda x: (_flag_order.get(x["risk_flag"], 9), -x["days_inactive"]))

        critical_count = sum(1 for r in results if r["risk_flag"] == "CRITICAL")
        high_count = sum(1 for r in results if r["risk_flag"] == "HIGH")
        sensitive_dormant = sum(1 for r in results if r["has_sensitive_roles"])

        return {
            "threshold_days": days,
            "cutoff_date": cutoff_date.isoformat(),
            "generated_at": now.isoformat(),
            "total_dormant": total_count,
            "returned": len(results),
            "offset": offset,
            "summary": {
                "critical_risk_users": critical_count,
                "high_risk_users": high_count,
                "with_sensitive_access": sensitive_dormant,
                "recommendation": (
                    f"Immediate action required: {critical_count} dormant users with sensitive/critical access."
                    if critical_count > 0
                    else "No critical-risk dormant accounts detected."
                ),
            },
            "users": results,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Dormant account detection failed: {str(e)}")


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
