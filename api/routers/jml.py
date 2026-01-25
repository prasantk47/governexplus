"""
JML (Joiner/Mover/Leaver) API Router

Endpoints for HR lifecycle automation and provisioning.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

from core.jml import JMLManager, JMLEventType, ProvisioningStatus

router = APIRouter(tags=["JML"])

# Initialize manager
jml_manager = JMLManager()


# =============================================================================
# Request/Response Models
# =============================================================================

class JMLEventRequest(BaseModel):
    """Request to create a JML event"""
    event_type: str = Field(..., example="joiner")
    employee_id: str = Field(..., example="EMP001")
    employee_name: str = Field(..., example="John Smith")
    employee_email: str = Field(default="", example="john.smith@company.com")
    job_title: str = Field(..., example="Finance Analyst")
    department: str = Field(..., example="Finance")
    manager_id: str = Field(default="", example="MGR001")
    manager_name: str = Field(default="", example="Jane Doe")
    location: str = Field(default="", example="New York")
    cost_center: str = Field(default="", example="CC1001")
    employee_type: str = Field(default="FTE", example="FTE")
    company_code: str = Field(default="", example="1000")
    effective_date: Optional[datetime] = None
    termination_date: Optional[datetime] = None
    contract_end_date: Optional[datetime] = None

    # For movers
    previous_job_title: Optional[str] = None
    previous_department: Optional[str] = None
    previous_manager_id: Optional[str] = None
    previous_location: Optional[str] = None
    previous_cost_center: Optional[str] = None

    source_system: str = Field(default="HR")
    source_event_id: Optional[str] = None
    notes: str = Field(default="")


class ApprovalRequest(BaseModel):
    """Request to approve/reject a JML event"""
    approver_id: str = Field(..., example="security.admin@company.com")
    comments: str = Field(default="")


class RejectionRequest(BaseModel):
    """Request to reject a JML event"""
    rejector_id: str = Field(..., example="security.admin@company.com")
    reason: str = Field(..., example="Missing required documentation")


class CreateProfileRequest(BaseModel):
    """Request to create an access profile"""
    name: str = Field(..., example="Finance Analyst")
    description: str = Field(..., example="Standard access for Finance Analysts")
    job_titles: List[str] = Field(default_factory=list)
    departments: List[str] = Field(default_factory=list)
    locations: List[str] = Field(default_factory=list)
    employee_types: List[str] = Field(default_factory=list)
    roles: List[Dict] = Field(default_factory=list, example=[{"system": "SAP", "role_name": "Z_FIN_ANALYST"}])
    groups: List[Dict] = Field(default_factory=list, example=[{"system": "AD", "group_name": "Finance_Users"}])
    priority: int = Field(default=100)
    requires_approval: bool = Field(default=False)
    auto_expire_days: Optional[int] = None
    owner_id: str = Field(default="")


class ProfileMatchPreviewRequest(BaseModel):
    """Request to preview profile matches"""
    job_title: str = Field(default="")
    department: str = Field(default="")
    location: str = Field(default="")
    cost_center: str = Field(default="")
    employee_type: str = Field(default="FTE")


# =============================================================================
# JML Event Endpoints
# =============================================================================

@router.post("/events", status_code=201)
async def create_jml_event(request: JMLEventRequest):
    """
    Create and process a JML event from HR.

    This endpoint receives HR lifecycle events (joiners, movers, leavers)
    and generates the appropriate provisioning actions.
    """
    try:
        event_data = {
            "event_type": request.event_type,
            "employee_id": request.employee_id,
            "employee_name": request.employee_name,
            "employee_email": request.employee_email,
            "job_title": request.job_title,
            "department": request.department,
            "manager_id": request.manager_id,
            "manager_name": request.manager_name,
            "location": request.location,
            "cost_center": request.cost_center,
            "employee_type": request.employee_type,
            "company_code": request.company_code,
            "effective_date": request.effective_date or datetime.now(),
            "termination_date": request.termination_date,
            "contract_end_date": request.contract_end_date,
            "previous_job_title": request.previous_job_title,
            "previous_department": request.previous_department,
            "previous_manager_id": request.previous_manager_id,
            "previous_location": request.previous_location,
            "previous_cost_center": request.previous_cost_center,
            "source_system": request.source_system,
            "source_event_id": request.source_event_id,
            "notes": request.notes
        }

        event = await jml_manager.process_hr_event(event_data)

        return {
            "message": "JML event created successfully",
            "event_id": event.event_id,
            "event_type": event.event_type.value,
            "status": event.status.value,
            "requires_approval": event.requires_approval,
            "matched_profiles": event.matched_profiles,
            "action_count": len(event.actions),
            "actions_summary": [
                {
                    "action_type": a.action_type.value,
                    "target_system": a.target_system,
                    "role_name": a.role_name,
                    "status": a.status.value
                }
                for a in event.actions[:10]  # First 10 actions
            ]
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/events")
async def list_jml_events(
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    status: Optional[str] = Query(None, description="Filter by status"),
    employee_id: Optional[str] = Query(None, description="Filter by employee"),
    start_date: Optional[datetime] = Query(None, description="Filter by start date"),
    end_date: Optional[datetime] = Query(None, description="Filter by end date"),
    limit: int = Query(50, le=200)
):
    """
    List JML events with optional filters.
    """
    event_type_enum = None
    if event_type:
        try:
            event_type_enum = JMLEventType(event_type)
        except ValueError:
            pass

    status_enum = None
    if status:
        try:
            status_enum = ProvisioningStatus(status)
        except ValueError:
            pass

    events = jml_manager.get_events(
        event_type=event_type_enum,
        status=status_enum,
        employee_id=employee_id,
        start_date=start_date,
        end_date=end_date
    )[:limit]

    return {
        "total": len(events),
        "events": [e.to_summary() for e in events]
    }


@router.get("/events/types")
async def list_event_types():
    """List all JML event types"""
    return {
        "types": [
            {"value": t.value, "name": t.name}
            for t in JMLEventType
        ]
    }


@router.get("/events/pending-approval")
async def get_pending_approvals():
    """Get JML events pending approval"""
    pending = jml_manager.get_pending_approvals()

    return {
        "total": len(pending),
        "events": [e.to_dict() for e in pending]
    }


@router.get("/events/{event_id}")
async def get_jml_event(event_id: str):
    """Get detailed information about a JML event"""
    event = jml_manager.get_event(event_id)
    if not event:
        raise HTTPException(status_code=404, detail=f"Event {event_id} not found")

    return event.to_dict()


@router.get("/events/{event_id}/actions")
async def get_event_actions(event_id: str):
    """Get all provisioning actions for an event"""
    event = jml_manager.get_event(event_id)
    if not event:
        raise HTTPException(status_code=404, detail=f"Event {event_id} not found")

    return {
        "event_id": event_id,
        "total_actions": len(event.actions),
        "progress": event.calculate_progress(),
        "actions": [a.to_dict() for a in event.actions]
    }


@router.post("/events/{event_id}/approve")
async def approve_event(event_id: str, request: ApprovalRequest):
    """
    Approve a JML event for execution.
    """
    try:
        event = await jml_manager.approve_event(
            event_id=event_id,
            approver_id=request.approver_id,
            comments=request.comments
        )

        return {
            "message": "Event approved",
            "event_id": event.event_id,
            "approval_status": event.approval_status,
            "approved_by": event.approved_by
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/events/{event_id}/reject")
async def reject_event(event_id: str, request: RejectionRequest):
    """
    Reject a JML event.
    """
    try:
        event = await jml_manager.reject_event(
            event_id=event_id,
            rejector_id=request.rejector_id,
            reason=request.reason
        )

        return {
            "message": "Event rejected",
            "event_id": event.event_id,
            "status": event.status.value
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/events/{event_id}/execute")
async def execute_event(event_id: str):
    """
    Execute all pending provisioning actions for an event.

    The event must be approved (if approval required) before execution.
    """
    try:
        event = await jml_manager.execute_event(event_id)

        progress = event.calculate_progress()

        return {
            "message": "Event execution completed",
            "event_id": event.event_id,
            "status": event.status.value,
            "progress": progress,
            "actions": [
                {
                    "action_type": a.action_type.value,
                    "status": a.status.value,
                    "success": a.success,
                    "error": a.error_message
                }
                for a in event.actions
            ]
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# =============================================================================
# Employee History Endpoints
# =============================================================================

@router.get("/employees/{employee_id}/history")
async def get_employee_history(employee_id: str):
    """Get JML history for an employee"""
    events = jml_manager.get_employee_history(employee_id)

    return {
        "employee_id": employee_id,
        "total_events": len(events),
        "events": [e.to_dict() for e in events]
    }


# =============================================================================
# Access Profile Endpoints
# =============================================================================

@router.get("/profiles")
async def list_profiles(
    active_only: bool = Query(True, description="Only show active profiles")
):
    """List all access profiles"""
    profiles = jml_manager.get_profiles(active_only=active_only)

    return {
        "total": len(profiles),
        "profiles": [p.to_dict() for p in profiles]
    }


@router.post("/profiles", status_code=201)
async def create_profile(request: CreateProfileRequest):
    """
    Create a new access profile.

    Profiles define standard access for job roles/positions.
    """
    profile = jml_manager.create_profile(
        name=request.name,
        description=request.description,
        job_titles=request.job_titles,
        departments=request.departments,
        locations=request.locations,
        employee_types=request.employee_types,
        roles=request.roles,
        groups=request.groups,
        priority=request.priority,
        requires_approval=request.requires_approval,
        auto_expire_days=request.auto_expire_days,
        owner_id=request.owner_id
    )

    return {
        "message": "Profile created",
        "profile_id": profile.profile_id
    }


@router.get("/profiles/{profile_id}")
async def get_profile(profile_id: str):
    """Get a specific access profile"""
    profile = jml_manager.get_profile(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail=f"Profile {profile_id} not found")

    return profile.to_dict()


@router.post("/profiles/preview-match")
async def preview_profile_match(request: ProfileMatchPreviewRequest):
    """
    Preview which profiles would match given employee attributes.

    Useful for testing profile configurations.
    """
    attrs = {
        "job_title": request.job_title,
        "department": request.department,
        "location": request.location,
        "cost_center": request.cost_center,
        "employee_type": request.employee_type
    }

    matches = jml_manager.preview_profile_matches(attrs)

    return {
        "input_attributes": attrs,
        "matched_profiles": len(matches),
        "profiles": matches
    }


# =============================================================================
# Statistics Endpoints
# =============================================================================

@router.get("/statistics")
async def get_jml_statistics():
    """Get JML processing statistics"""
    return jml_manager.get_statistics()


# =============================================================================
# Bulk Operations
# =============================================================================

@router.post("/events/bulk", status_code=201)
async def create_bulk_events(events: List[JMLEventRequest]):
    """
    Create multiple JML events in bulk.

    Useful for batch processing from HR systems.
    """
    results = []

    for request in events:
        try:
            event_data = {
                "event_type": request.event_type,
                "employee_id": request.employee_id,
                "employee_name": request.employee_name,
                "employee_email": request.employee_email,
                "job_title": request.job_title,
                "department": request.department,
                "manager_id": request.manager_id,
                "manager_name": request.manager_name,
                "location": request.location,
                "cost_center": request.cost_center,
                "employee_type": request.employee_type,
                "effective_date": request.effective_date or datetime.now(),
                "source_system": request.source_system
            }

            event = await jml_manager.process_hr_event(event_data)

            results.append({
                "employee_id": request.employee_id,
                "event_id": event.event_id,
                "status": "success"
            })

        except Exception as e:
            results.append({
                "employee_id": request.employee_id,
                "status": "failed",
                "error": str(e)
            })

    success_count = len([r for r in results if r["status"] == "success"])

    return {
        "message": f"Processed {len(events)} events",
        "success_count": success_count,
        "failed_count": len(events) - success_count,
        "results": results
    }


@router.post("/events/bulk-execute")
async def bulk_execute_events(event_ids: List[str]):
    """
    Execute multiple JML events.
    """
    results = []

    for event_id in event_ids:
        try:
            event = await jml_manager.execute_event(event_id)
            results.append({
                "event_id": event_id,
                "status": event.status.value,
                "success": True
            })
        except Exception as e:
            results.append({
                "event_id": event_id,
                "status": "failed",
                "success": False,
                "error": str(e)
            })

    return {
        "processed": len(results),
        "results": results
    }
