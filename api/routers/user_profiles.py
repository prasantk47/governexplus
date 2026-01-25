"""
User Profile API Router

Endpoints for unified user profile management.
Aggregates data from HR, Identity Provider, SAP, and GRC systems.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime, date

from core.identity import (
    UserProfileService, UnifiedUserProfile, UserSource,
    ManagerInfo, OrganizationInfo, RiskProfile, AccessSummary
)

router = APIRouter(tags=["User Profiles"])

profile_service = UserProfileService()


# =============================================================================
# Request/Response Models
# =============================================================================

class OrganizationModel(BaseModel):
    company_code: str = ""
    company_name: str = ""
    cost_center: str = ""
    cost_center_name: str = ""
    department: str = ""
    department_name: str = ""
    org_unit: str = ""
    org_unit_name: str = ""
    location: str = ""
    location_name: str = ""
    country: str = ""
    region: str = ""
    business_unit: str = ""
    division: str = ""


class ManagerModel(BaseModel):
    user_id: str
    employee_id: Optional[str] = None
    name: str = ""
    email: str = ""
    title: str = ""
    department: str = ""


class SyncHRDataRequest(BaseModel):
    """Request model for syncing HR data"""
    employee_id: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    full_name: Optional[str] = None
    email: Optional[str] = None
    job_title: Optional[str] = None
    job_code: Optional[str] = None
    hire_date: Optional[date] = None
    termination_date: Optional[date] = None
    organization: Optional[OrganizationModel] = None
    manager: Optional[ManagerModel] = None


class SyncSAPDataRequest(BaseModel):
    """Request model for syncing SAP data"""
    user_type: Optional[str] = None
    license_type: Optional[str] = None
    password_status: Optional[str] = None
    valid_from: Optional[date] = None
    valid_to: Optional[date] = None
    last_login: Optional[datetime] = None
    lock_status: int = 0
    roles: Optional[List[Dict]] = None
    profiles: Optional[List[Dict]] = None


class UpdateRiskRequest(BaseModel):
    """Request model for updating risk profile"""
    risk_level: Optional[str] = None
    risk_score: Optional[float] = None
    sod_violations: Optional[int] = None
    sensitive_access: Optional[int] = None
    high_risk_roles: Optional[List[str]] = None
    mitigations: Optional[int] = None
    anomaly_score: Optional[float] = None


# =============================================================================
# Profile Retrieval Endpoints
# =============================================================================

@router.get("/")
async def list_profiles(
    search: Optional[str] = Query(None, description="Search by user ID, name, email"),
    department: Optional[str] = Query(None, description="Filter by department"),
    status: Optional[str] = Query(None, description="Filter by status"),
    risk_level: Optional[str] = Query(None, description="Filter by risk level"),
    employment_type: Optional[str] = Query(None, description="Filter by employment type"),
    has_sod_violations: Optional[bool] = Query(None, description="Filter by SoD violations"),
    requires_certification: Optional[bool] = Query(None, description="Filter by certification requirement"),
    limit: int = Query(100, le=1000)
):
    """
    List user profiles with filters.

    Returns unified profiles aggregated from all data sources.
    """
    from core.identity.user_profile import UserStatus, EmploymentType

    status_enum = UserStatus(status) if status else None
    emp_type_enum = EmploymentType(employment_type) if employment_type else None

    profiles = profile_service.search_profiles(
        search=search,
        department=department,
        status=status_enum,
        risk_level=risk_level,
        employment_type=emp_type_enum,
        has_sod_violations=has_sod_violations,
        requires_certification=requires_certification,
        limit=limit
    )

    return {
        "total": len(profiles),
        "profiles": [p.to_summary() for p in profiles]
    }


@router.get("/statistics")
async def get_profile_statistics():
    """Get user profile statistics"""
    return profile_service.get_statistics()


@router.get("/{user_id}")
async def get_profile(user_id: str):
    """
    Get complete unified profile for a user.

    Returns comprehensive user data aggregated from HR, Identity Provider,
    SAP, and GRC systems.
    """
    profile = profile_service.get_profile(user_id)
    if not profile:
        raise HTTPException(status_code=404, detail=f"User profile not found: {user_id}")
    return profile.to_dict()


@router.get("/{user_id}/summary")
async def get_profile_summary(user_id: str):
    """Get brief profile summary for lists and dropdowns"""
    profile = profile_service.get_profile(user_id)
    if not profile:
        raise HTTPException(status_code=404, detail=f"User profile not found: {user_id}")
    return profile.to_summary()


@router.get("/{user_id}/request-context")
async def get_request_context(user_id: str):
    """
    Get user context optimized for access requests.

    Includes manager info for routing, risk profile, and current access summary.
    """
    profile = profile_service.get_profile(user_id)
    if not profile:
        raise HTTPException(status_code=404, detail=f"User profile not found: {user_id}")
    return profile.to_request_context()


# =============================================================================
# Lookup by Different Identifiers
# =============================================================================

@router.get("/by-employee-id/{employee_id}")
async def get_profile_by_employee_id(employee_id: str):
    """Get user profile by HR employee ID"""
    profile = profile_service.get_profile_by_employee_id(employee_id)
    if not profile:
        raise HTTPException(status_code=404, detail=f"User not found with employee ID: {employee_id}")
    return profile.to_dict()


@router.get("/by-email/{email}")
async def get_profile_by_email(email: str):
    """Get user profile by email address"""
    profile = profile_service.get_profile_by_email(email)
    if not profile:
        raise HTTPException(status_code=404, detail=f"User not found with email: {email}")
    return profile.to_dict()


# =============================================================================
# Manager & Organization Endpoints
# =============================================================================

@router.get("/{user_id}/direct-reports")
async def get_direct_reports(user_id: str):
    """Get all direct reports for a manager"""
    direct_reports = profile_service.get_manager_direct_reports(user_id)
    return {
        "manager_user_id": user_id,
        "total": len(direct_reports),
        "direct_reports": [p.to_summary() for p in direct_reports]
    }


@router.get("/{user_id}/manager-chain")
async def get_manager_chain(user_id: str):
    """Get the management chain for a user"""
    profile = profile_service.get_profile(user_id)
    if not profile:
        raise HTTPException(status_code=404, detail=f"User profile not found: {user_id}")

    chain = []
    current = profile
    visited = set()  # Prevent infinite loops

    while current and current.manager and current.manager.user_id not in visited:
        visited.add(current.user_id)
        manager_profile = profile_service.get_profile(current.manager.user_id)
        if manager_profile:
            chain.append({
                "user_id": manager_profile.user_id,
                "name": manager_profile.full_name,
                "title": manager_profile.job_title,
                "email": manager_profile.email,
                "level": len(chain) + 1
            })
            current = manager_profile
        else:
            # Manager exists but no profile
            chain.append({
                "user_id": current.manager.user_id,
                "name": current.manager.name,
                "title": current.manager.title,
                "email": current.manager.email,
                "level": len(chain) + 1
            })
            break

    return {
        "user_id": user_id,
        "manager_chain": chain
    }


# =============================================================================
# Risk & Access Endpoints
# =============================================================================

@router.get("/{user_id}/risk-profile")
async def get_risk_profile(user_id: str):
    """Get detailed risk profile for a user"""
    profile = profile_service.get_profile(user_id)
    if not profile:
        raise HTTPException(status_code=404, detail=f"User profile not found: {user_id}")

    return {
        "user_id": user_id,
        "full_name": profile.full_name,
        "risk_profile": profile.risk_profile.to_dict(),
        "requires_sod_review": profile.requires_sod_review,
        "requires_certification": profile.requires_certification,
        "compliance_flags": profile.compliance_flags
    }


@router.get("/{user_id}/access-summary")
async def get_access_summary(user_id: str):
    """Get current access summary for a user"""
    profile = profile_service.get_profile(user_id)
    if not profile:
        raise HTTPException(status_code=404, detail=f"User profile not found: {user_id}")

    return {
        "user_id": user_id,
        "full_name": profile.full_name,
        "access_summary": profile.access_summary.to_dict(),
        "sap_user_type": profile.sap_user_type,
        "sap_license_type": profile.sap_license_type,
        "sap_last_login": profile.sap_last_login.isoformat() if profile.sap_last_login else None
    }


# =============================================================================
# Data Synchronization Endpoints
# =============================================================================

@router.post("/{user_id}/sync/hr")
async def sync_from_hr(user_id: str, request: SyncHRDataRequest):
    """
    Sync user profile with HR system data.

    Updates HR-sourced fields: employee info, organization, manager.
    """
    hr_data = request.dict(exclude_none=True)

    # Convert nested models to dicts
    if request.organization:
        hr_data["organization"] = request.organization.dict()
    if request.manager:
        hr_data["manager"] = request.manager.dict()

    profile = profile_service.sync_from_hr(user_id, hr_data)
    return {
        "status": "synced",
        "user_id": user_id,
        "source": "hr_system",
        "synced_at": profile.source_timestamps.get("hr_system", datetime.now()).isoformat(),
        "profile": profile.to_summary()
    }


@router.post("/{user_id}/sync/sap")
async def sync_from_sap(user_id: str, request: SyncSAPDataRequest):
    """
    Sync user profile with SAP system data.

    Updates SAP-sourced fields: user type, validity, roles, profiles.
    """
    sap_data = request.dict(exclude_none=True)
    profile = profile_service.sync_from_sap(user_id, sap_data)
    return {
        "status": "synced",
        "user_id": user_id,
        "source": "sap_system",
        "synced_at": profile.source_timestamps.get("sap_system", datetime.now()).isoformat(),
        "profile": profile.to_summary()
    }


@router.post("/{user_id}/risk/update")
async def update_risk_profile(user_id: str, request: UpdateRiskRequest):
    """
    Update user's risk profile from GRC analysis.

    Typically called after risk analysis runs.
    """
    risk_data = request.dict(exclude_none=True)
    profile = profile_service.update_risk_profile(user_id, risk_data)

    if not profile:
        raise HTTPException(status_code=404, detail=f"User profile not found: {user_id}")

    return {
        "status": "updated",
        "user_id": user_id,
        "risk_profile": profile.risk_profile.to_dict(),
        "requires_sod_review": profile.requires_sod_review,
        "requires_certification": profile.requires_certification
    }


# =============================================================================
# Bulk Operations
# =============================================================================

@router.post("/bulk/lookup")
async def bulk_lookup(user_ids: List[str]):
    """
    Bulk lookup multiple user profiles.

    Returns summaries for all requested users.
    """
    results = []
    not_found = []

    for user_id in user_ids:
        profile = profile_service.get_profile(user_id)
        if profile:
            results.append(profile.to_summary())
        else:
            not_found.append(user_id)

    return {
        "found": len(results),
        "not_found_count": len(not_found),
        "profiles": results,
        "not_found_ids": not_found
    }


@router.get("/high-risk")
async def get_high_risk_users(
    risk_level: str = Query(default="high", description="Minimum risk level"),
    limit: int = Query(default=50, le=200)
):
    """Get users with high or critical risk profiles"""
    profiles = profile_service.search_profiles(
        risk_level=risk_level,
        limit=limit
    )

    # Also include critical if searching for high
    if risk_level == "high":
        critical = profile_service.search_profiles(
            risk_level="critical",
            limit=limit
        )
        profiles.extend(critical)

    # Sort by risk score descending
    profiles.sort(key=lambda p: p.risk_profile.risk_score, reverse=True)

    return {
        "total": len(profiles[:limit]),
        "profiles": [
            {
                **p.to_summary(),
                "risk_score": p.risk_profile.risk_score,
                "sod_violations": p.risk_profile.sod_violation_count,
                "compliance_flags": p.compliance_flags
            }
            for p in profiles[:limit]
        ]
    }


@router.get("/requiring-certification")
async def get_users_requiring_certification(
    limit: int = Query(default=50, le=200)
):
    """Get users who require access certification"""
    profiles = profile_service.search_profiles(
        requires_certification=True,
        limit=limit
    )

    return {
        "total": len(profiles),
        "profiles": [
            {
                **p.to_summary(),
                "last_certification": p.risk_profile.last_certification_date.isoformat() if p.risk_profile.last_certification_date else None,
                "certification_status": p.risk_profile.certification_status,
                "compliance_flags": p.compliance_flags
            }
            for p in profiles
        ]
    }


@router.get("/external-users")
async def get_external_users(
    limit: int = Query(default=50, le=200)
):
    """Get all external users (contractors, vendors)"""
    from core.identity.user_profile import EmploymentType

    contractors = profile_service.search_profiles(
        employment_type=EmploymentType.CONTRACTOR,
        limit=limit
    )
    vendors = profile_service.search_profiles(
        employment_type=EmploymentType.VENDOR,
        limit=limit
    )

    profiles = contractors + vendors

    return {
        "total": len(profiles),
        "contractors": len(contractors),
        "vendors": len(vendors),
        "profiles": [
            {
                **p.to_summary(),
                "employment_type": p.employment_type.value,
                "hire_date": p.hire_date.isoformat() if p.hire_date else None,
                "termination_date": p.termination_date.isoformat() if p.termination_date else None,
                "sap_valid_to": p.sap_valid_to.isoformat() if p.sap_valid_to else None
            }
            for p in profiles
        ]
    }


@router.get("/inactive-users")
async def get_inactive_users(
    days: int = Query(default=90, ge=1, le=365, description="Days since last login"),
    include_never_logged_in: bool = Query(default=True, description="Include users who never logged in"),
    status: Optional[str] = Query(default="active", description="Filter by user status"),
    limit: int = Query(default=100, le=500)
):
    """
    Get users who haven't logged in for specified number of days.

    This is critical for:
    - Security compliance (identifying dormant accounts)
    - License optimization (identifying unused accounts)
    - Access recertification (prioritizing stale accounts)
    - SOX/ISO 27001 audit requirements
    """
    from datetime import timedelta
    from core.identity.user_profile import UserStatus

    cutoff_date = datetime.now() - timedelta(days=days)
    status_enum = UserStatus(status) if status else None

    # Get all profiles with the specified status
    all_profiles = profile_service.search_profiles(
        status=status_enum,
        limit=limit * 2  # Get more to filter
    )

    inactive_users = []
    never_logged_in = []

    for profile in all_profiles:
        last_login = profile.sap_last_login

        if last_login is None:
            if include_never_logged_in:
                never_logged_in.append({
                    **profile.to_summary(),
                    "last_login": None,
                    "days_inactive": None,
                    "never_logged_in": True,
                    "risk_level": profile.risk_profile.risk_level if profile.risk_profile else "unknown",
                    "sap_user_type": profile.sap_user_type,
                    "created_at": profile.hire_date.isoformat() if profile.hire_date else None,
                    "recommendation": "Review account necessity - never used"
                })
        elif last_login < cutoff_date:
            days_inactive = (datetime.now() - last_login).days
            inactive_users.append({
                **profile.to_summary(),
                "last_login": last_login.isoformat(),
                "days_inactive": days_inactive,
                "never_logged_in": False,
                "risk_level": profile.risk_profile.risk_level if profile.risk_profile else "unknown",
                "sap_user_type": profile.sap_user_type,
                "sap_valid_to": profile.sap_valid_to.isoformat() if profile.sap_valid_to else None,
                "recommendation": _get_inactivity_recommendation(days_inactive)
            })

    # Sort by days inactive (most inactive first)
    inactive_users.sort(key=lambda x: x["days_inactive"] or 0, reverse=True)

    # Combine results
    all_inactive = inactive_users + never_logged_in

    return {
        "threshold_days": days,
        "cutoff_date": cutoff_date.isoformat(),
        "total_inactive": len(all_inactive),
        "inactive_with_login_history": len(inactive_users),
        "never_logged_in": len(never_logged_in),
        "summary": {
            "30_to_60_days": len([u for u in inactive_users if u["days_inactive"] and 30 <= u["days_inactive"] < 60]),
            "60_to_90_days": len([u for u in inactive_users if u["days_inactive"] and 60 <= u["days_inactive"] < 90]),
            "90_to_180_days": len([u for u in inactive_users if u["days_inactive"] and 90 <= u["days_inactive"] < 180]),
            "over_180_days": len([u for u in inactive_users if u["days_inactive"] and u["days_inactive"] >= 180]),
        },
        "recommendations": {
            "disable_accounts": len([u for u in all_inactive if u.get("days_inactive", 999) >= 180 or u.get("never_logged_in")]),
            "require_review": len([u for u in all_inactive if u.get("days_inactive") and 90 <= u["days_inactive"] < 180]),
            "monitor": len([u for u in all_inactive if u.get("days_inactive") and u["days_inactive"] < 90])
        },
        "users": all_inactive[:limit]
    }


def _get_inactivity_recommendation(days_inactive: int) -> str:
    """Get recommendation based on inactivity duration"""
    if days_inactive >= 365:
        return "Immediate action required - Consider disabling or removing account"
    elif days_inactive >= 180:
        return "High priority - Disable account and review with manager"
    elif days_inactive >= 90:
        return "Medium priority - Require justification for continued access"
    elif days_inactive >= 60:
        return "Low priority - Flag for next access review"
    else:
        return "Monitor - Include in regular access certification"


@router.get("/inactive-users/summary")
async def get_inactive_users_summary():
    """
    Get summary statistics for inactive users across the platform.

    Useful for dashboards and executive reporting.
    """
    from datetime import timedelta
    from core.identity.user_profile import UserStatus

    # Get all active users
    all_profiles = profile_service.search_profiles(
        status=UserStatus.ACTIVE,
        limit=10000
    )

    now = datetime.now()

    stats = {
        "total_active_users": len(all_profiles),
        "never_logged_in": 0,
        "inactive_30_days": 0,
        "inactive_60_days": 0,
        "inactive_90_days": 0,
        "inactive_180_days": 0,
        "inactive_365_days": 0,
        "active_last_30_days": 0,
    }

    for profile in all_profiles:
        last_login = profile.sap_last_login

        if last_login is None:
            stats["never_logged_in"] += 1
        else:
            days_since = (now - last_login).days

            if days_since < 30:
                stats["active_last_30_days"] += 1
            if days_since >= 30:
                stats["inactive_30_days"] += 1
            if days_since >= 60:
                stats["inactive_60_days"] += 1
            if days_since >= 90:
                stats["inactive_90_days"] += 1
            if days_since >= 180:
                stats["inactive_180_days"] += 1
            if days_since >= 365:
                stats["inactive_365_days"] += 1

    # Calculate percentages
    total = stats["total_active_users"]
    if total > 0:
        stats["percentages"] = {
            "never_logged_in": round(stats["never_logged_in"] / total * 100, 1),
            "inactive_90_days": round(stats["inactive_90_days"] / total * 100, 1),
            "active_last_30_days": round(stats["active_last_30_days"] / total * 100, 1),
        }

    # Risk assessment
    dormant_accounts = stats["inactive_90_days"] + stats["never_logged_in"]
    if dormant_accounts > total * 0.2:
        stats["risk_assessment"] = "HIGH - More than 20% of accounts are dormant"
    elif dormant_accounts > total * 0.1:
        stats["risk_assessment"] = "MEDIUM - More than 10% of accounts are dormant"
    else:
        stats["risk_assessment"] = "LOW - Dormant accounts under control"

    stats["compliance_note"] = "SOX, ISO 27001, and NIST require regular review of inactive accounts"

    return stats


# =============================================================================
# Data Source Status
# =============================================================================

@router.get("/{user_id}/data-sources")
async def get_data_source_status(user_id: str):
    """Get data source sync status for a user profile"""
    profile = profile_service.get_profile(user_id)
    if not profile:
        raise HTTPException(status_code=404, detail=f"User profile not found: {user_id}")

    return {
        "user_id": user_id,
        "data_sources": [s.value for s in profile.data_sources],
        "source_timestamps": {
            k: v.isoformat() for k, v in profile.source_timestamps.items()
        },
        "last_sync": profile.last_sync.isoformat() if profile.last_sync else None,
        "available_sources": [s.value for s in UserSource]
    }
