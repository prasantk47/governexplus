"""
Cross-System Correlation API Router

Endpoints for multi-system identity correlation and unified access views.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime

from core.cross_system import (
    CrossSystemManager, SystemType, CorrelationStatus, ConflictSeverity
)

router = APIRouter(tags=["Cross-System"])

# Initialize manager
cross_system_manager = CrossSystemManager()


# =============================================================================
# Request Models
# =============================================================================

class CreateIdentityRequest(BaseModel):
    display_name: str = Field(..., min_length=2)
    email: str
    employee_id: str = ""
    department: str = ""
    job_title: str = ""
    manager_id: str = ""
    location: str = ""


class LinkAccountRequest(BaseModel):
    system_id: str
    system_type: str
    username: str
    display_name: str = ""
    email: str = ""
    status: str = "active"


class AddAccessRequest(BaseModel):
    system_id: str
    roles: List[str] = Field(default_factory=list)
    groups: List[str] = Field(default_factory=list)
    permissions: List[str] = Field(default_factory=list)
    is_privileged: bool = False


class CorrelateAccountsRequest(BaseModel):
    source_account: Dict
    target_accounts: List[Dict]


class MitigateConflictRequest(BaseModel):
    control_id: str


class AcceptConflictRequest(BaseModel):
    justification: str


# =============================================================================
# Identity Management Endpoints
# =============================================================================

@router.post("/identities")
async def create_identity(request: CreateIdentityRequest):
    """Create a new identity"""
    identity = cross_system_manager.create_identity(
        display_name=request.display_name,
        email=request.email,
        employee_id=request.employee_id,
        department=request.department,
        job_title=request.job_title,
        manager_id=request.manager_id,
        location=request.location
    )
    return identity.to_dict()


@router.get("/identities")
async def list_identities(
    correlation_status: Optional[str] = Query(None),
    department: Optional[str] = Query(None),
    has_conflicts: Optional[bool] = Query(None),
    search: Optional[str] = Query(None)
):
    """List identities with filters"""
    status_enum = None
    if correlation_status:
        try:
            status_enum = CorrelationStatus(correlation_status)
        except ValueError:
            pass

    identities = cross_system_manager.list_identities(
        correlation_status=status_enum,
        department=department,
        has_conflicts=has_conflicts,
        search=search
    )

    return {
        "total": len(identities),
        "identities": [i.to_dict() for i in identities]
    }


@router.get("/identities/{identity_id}")
async def get_identity(identity_id: str):
    """Get an identity by ID"""
    identity = cross_system_manager.get_identity(identity_id)
    if not identity:
        raise HTTPException(status_code=404, detail=f"Identity {identity_id} not found")
    return identity.to_dict()


@router.get("/identities/by-email/{email}")
async def find_identity_by_email(email: str):
    """Find an identity by email"""
    identity = cross_system_manager.find_identity_by_email(email)
    if not identity:
        raise HTTPException(status_code=404, detail=f"Identity with email {email} not found")
    return identity.to_dict()


@router.post("/identities/{identity_id}/accounts")
async def link_account(
    identity_id: str,
    request: LinkAccountRequest
):
    """Link a system account to an identity"""
    try:
        system_type = SystemType(request.system_type)
    except ValueError:
        system_type = SystemType.CUSTOM

    try:
        identity = cross_system_manager.link_account(
            identity_id=identity_id,
            system_id=request.system_id,
            system_type=system_type,
            username=request.username,
            display_name=request.display_name,
            email=request.email,
            status=request.status
        )
        return identity.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/identities/{identity_id}/access")
async def add_system_access(
    identity_id: str,
    request: AddAccessRequest
):
    """Add system access to an identity"""
    try:
        identity = cross_system_manager.add_system_access(
            identity_id=identity_id,
            system_id=request.system_id,
            roles=request.roles,
            groups=request.groups,
            permissions=request.permissions,
            is_privileged=request.is_privileged
        )
        return identity.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# =============================================================================
# Unified Access View Endpoints
# =============================================================================

@router.get("/identities/{identity_id}/unified-access")
async def get_unified_access_view(identity_id: str):
    """Get unified access view for an identity"""
    try:
        view = cross_system_manager.get_unified_access_view(identity_id)
        return view.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# =============================================================================
# Correlation Endpoints
# =============================================================================

@router.post("/correlate")
async def correlate_accounts(request: CorrelateAccountsRequest):
    """Find matching accounts using correlation rules"""
    matches = cross_system_manager.correlate_accounts(
        source_account=request.source_account,
        target_accounts=request.target_accounts
    )
    return {
        "matches_found": len(matches),
        "matches": matches
    }


@router.post("/correlate/auto")
async def run_auto_correlation():
    """Run automatic correlation across all systems"""
    result = cross_system_manager.auto_correlate()
    return result


@router.get("/correlation-rules")
async def list_correlation_rules():
    """List correlation rules"""
    rules = cross_system_manager.correlation_rules
    return {
        "total": len(rules),
        "rules": [r.to_dict() for r in rules]
    }


# =============================================================================
# Cross-System SoD Analysis Endpoints
# =============================================================================

@router.post("/identities/{identity_id}/analyze-sod")
async def analyze_cross_system_sod(identity_id: str):
    """Analyze an identity for cross-system SoD conflicts"""
    try:
        conflicts = cross_system_manager.analyze_cross_system_sod(identity_id)
        return {
            "identity_id": identity_id,
            "conflicts_found": len(conflicts),
            "conflicts": [c.to_dict() for c in conflicts]
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/analyze-all")
async def analyze_all_identities():
    """Analyze all identities for cross-system conflicts"""
    results = cross_system_manager.analyze_all_identities()
    return results


# =============================================================================
# Conflict Management Endpoints
# =============================================================================

@router.get("/conflicts")
async def list_conflicts(
    identity_id: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    status: Optional[str] = Query(None)
):
    """List conflicts with filters"""
    severity_enum = None
    if severity:
        try:
            severity_enum = ConflictSeverity(severity)
        except ValueError:
            pass

    conflicts = cross_system_manager.list_conflicts(
        identity_id=identity_id,
        severity=severity_enum,
        status=status
    )

    return {
        "total": len(conflicts),
        "conflicts": [c.to_dict() for c in conflicts]
    }


@router.post("/conflicts/{conflict_id}/mitigate")
async def mitigate_conflict(
    conflict_id: str,
    request: MitigateConflictRequest,
    mitigated_by: str = Query(...)
):
    """Mark a conflict as mitigated"""
    try:
        conflict = cross_system_manager.mitigate_conflict(
            conflict_id=conflict_id,
            control_id=request.control_id,
            mitigated_by=mitigated_by
        )
        return conflict.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/conflicts/{conflict_id}/accept")
async def accept_conflict(
    conflict_id: str,
    request: AcceptConflictRequest,
    accepted_by: str = Query(...)
):
    """Accept a conflict (risk acceptance)"""
    try:
        conflict = cross_system_manager.accept_conflict(
            conflict_id=conflict_id,
            accepted_by=accepted_by,
            justification=request.justification
        )
        return conflict.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/conflicts/{conflict_id}/resolve")
async def resolve_conflict(
    conflict_id: str,
    resolved_by: str = Query(...)
):
    """Mark a conflict as resolved"""
    try:
        conflict = cross_system_manager.resolve_conflict(conflict_id, resolved_by)
        return conflict.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# =============================================================================
# System Management Endpoints
# =============================================================================

@router.get("/systems")
async def list_connected_systems():
    """List all connected systems"""
    systems = cross_system_manager.list_connected_systems()
    return {
        "total": len(systems),
        "systems": systems
    }


@router.get("/systems/statistics")
async def get_system_statistics():
    """Get statistics by system"""
    return cross_system_manager.get_system_statistics()


@router.get("/system-types")
async def list_system_types():
    """List available system types"""
    return {
        "types": [
            {"value": t.value, "name": t.name}
            for t in SystemType
        ]
    }


# =============================================================================
# Statistics
# =============================================================================

@router.get("/statistics")
async def get_cross_system_statistics():
    """Get cross-system correlation statistics"""
    return cross_system_manager.get_statistics()
