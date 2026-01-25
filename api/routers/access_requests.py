"""
Access Request API Router

Endpoints for the access request portal including:
- Request creation and submission
- Risk preview
- Approval processing
- Request tracking
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime

from core.access_request import (
    AccessRequestManager, AccessRequest, AccessRequestStatus,
    RequestType, ApprovalAction
)
from core.rules import RuleEngine

router = APIRouter(tags=["Access Requests"])

# Initialize managers
rule_engine = RuleEngine()
request_manager = AccessRequestManager(rule_engine=rule_engine)


# =============================================================================
# Request/Response Models
# =============================================================================

class CreateRequestModel(BaseModel):
    """Model for creating a new access request"""
    requester_user_id: str = Field(..., example="JSMITH")
    requester_name: str = Field(..., example="John Smith")
    requester_email: str = Field(..., example="john.smith@company.com")
    target_user_id: str = Field(..., example="MBROWN")
    target_user_name: str = Field(..., example="Mary Brown")
    requested_roles: List[str] = Field(..., example=["Z_AP_CLERK", "Z_PURCHASER"])
    business_justification: str = Field(..., min_length=20,
        example="Need access to process vendor invoices for the new procurement project")
    request_type: Optional[str] = Field(default="new_access")
    is_temporary: bool = Field(default=False)
    end_date: Optional[datetime] = None
    ticket_reference: Optional[str] = Field(None, example="INC0012345")


class ApprovalActionModel(BaseModel):
    """Model for processing an approval action"""
    actor_id: str = Field(..., example="manager@company.com")
    action: str = Field(..., example="approve")  # approve, reject, delegate
    comments: Optional[str] = Field(None, example="Approved for project needs")
    delegate_to: Optional[str] = None


class RiskPreviewRequest(BaseModel):
    """Model for risk preview"""
    target_user_id: str
    requested_roles: List[str]


# =============================================================================
# Role Catalog Endpoints
# =============================================================================

@router.get("/catalog/roles")
async def get_role_catalog(
    search: Optional[str] = Query(None, description="Search roles"),
    business_process: Optional[str] = Query(None, description="Filter by process")
):
    """
    Get available roles from the catalog.

    Returns business-friendly role descriptions for the request portal.
    """
    roles = request_manager.get_role_catalog(search, business_process)

    return {
        "total": len(roles),
        "roles": roles,
        "business_processes": list(set(
            r.get("business_process") for r in roles if r.get("business_process")
        ))
    }


@router.get("/catalog/roles/{role_id}")
async def get_role_details(role_id: str):
    """Get detailed information about a specific role"""
    roles = request_manager.get_role_catalog()
    role = next((r for r in roles if r["role_id"] == role_id), None)

    if not role:
        raise HTTPException(status_code=404, detail=f"Role {role_id} not found")

    return role


# =============================================================================
# Risk Preview Endpoints
# =============================================================================

@router.post("/preview-risk")
async def preview_risk(request: RiskPreviewRequest):
    """
    Preview risk analysis before submitting a request.

    Shows what SoD violations and sensitive access would be introduced.
    """
    # Create a temporary request for analysis
    temp_request = AccessRequest(
        target_user_id=request.target_user_id,
        target_user_name=request.target_user_id
    )

    # Add requested items
    from core.access_request.models import RequestedAccess
    for role_id in request.requested_roles:
        temp_request.requested_items.append(RequestedAccess(
            access_type="role",
            access_name=role_id
        ))

    preview = await request_manager.preview_risk(temp_request)

    return preview


# =============================================================================
# Request Lifecycle Endpoints
# =============================================================================

@router.post("/", status_code=201)
async def create_access_request(request: CreateRequestModel):
    """
    Create a new access request (draft).

    The request is created in DRAFT status. Use /submit to submit for approval.
    """
    try:
        # Map request type
        type_map = {
            "new_access": RequestType.NEW_ACCESS,
            "modify_access": RequestType.MODIFY_ACCESS,
            "remove_access": RequestType.REMOVE_ACCESS,
            "temporary": RequestType.TEMPORARY_ACCESS,
            "extension": RequestType.ROLE_EXTENSION
        }
        req_type = type_map.get(request.request_type, RequestType.NEW_ACCESS)

        access_request = await request_manager.create_request(
            requester_user_id=request.requester_user_id,
            requester_name=request.requester_name,
            requester_email=request.requester_email,
            target_user_id=request.target_user_id,
            target_user_name=request.target_user_name,
            requested_roles=request.requested_roles,
            business_justification=request.business_justification,
            request_type=req_type,
            is_temporary=request.is_temporary,
            end_date=request.end_date,
            ticket_reference=request.ticket_reference
        )

        return {
            "request_id": access_request.request_id,
            "status": access_request.status.value,
            "message": "Request created in draft. Use /submit to submit for approval.",
            "request": access_request.to_summary()
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{request_id}/submit")
async def submit_request(request_id: str):
    """
    Submit a draft request for approval.

    This triggers risk analysis and workflow generation.
    """
    try:
        access_request = await request_manager.submit_request(request_id)

        return {
            "request_id": access_request.request_id,
            "status": access_request.status.value,
            "risk_level": access_request.risk_level,
            "risk_score": access_request.overall_risk_score,
            "sod_violations": len(access_request.sod_violations),
            "approval_steps": len(access_request.approval_steps),
            "current_approvers": access_request.get_current_approvers(),
            "message": "Request submitted for approval"
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{request_id}")
async def get_request(request_id: str):
    """Get full details of an access request"""
    access_request = request_manager.get_request(request_id)

    if not access_request:
        raise HTTPException(status_code=404, detail=f"Request {request_id} not found")

    return access_request.to_dict()


@router.get("/")
async def list_requests(
    status: Optional[str] = Query(None, description="Filter by status"),
    requester: Optional[str] = Query(None, description="Filter by requester"),
    target: Optional[str] = Query(None, description="Filter by target user"),
    limit: int = Query(50, le=200)
):
    """List access requests with optional filters"""
    requests = list(request_manager.requests.values())

    # Apply filters
    if status:
        requests = [r for r in requests if r.status.value == status]
    if requester:
        requests = [r for r in requests if r.requester_user_id == requester]
    if target:
        requests = [r for r in requests if r.target_user_id == target]

    # Sort by created date
    requests.sort(key=lambda r: r.created_at, reverse=True)

    return {
        "total": len(requests),
        "requests": [r.to_summary() for r in requests[:limit]]
    }


@router.post("/{request_id}/cancel")
async def cancel_request(request_id: str, user_id: str = Query(...)):
    """Cancel a pending request"""
    access_request = request_manager.get_request(request_id)

    if not access_request:
        raise HTTPException(status_code=404, detail=f"Request {request_id} not found")

    if access_request.requester_user_id != user_id:
        raise HTTPException(status_code=403, detail="Only requester can cancel")

    if access_request.status not in [AccessRequestStatus.DRAFT, AccessRequestStatus.PENDING_APPROVAL]:
        raise HTTPException(status_code=400, detail="Cannot cancel request in current status")

    access_request.status = AccessRequestStatus.CANCELLED
    access_request.last_updated_at = datetime.now()

    return {
        "request_id": request_id,
        "status": "cancelled",
        "message": "Request has been cancelled"
    }


# =============================================================================
# Approval Endpoints
# =============================================================================

@router.get("/approvals/pending")
async def get_pending_approvals(approver_id: str = Query(..., description="Approver user ID")):
    """
    Get all pending approvals for an approver.

    This is the unified approval inbox.
    """
    pending = request_manager.get_pending_approvals(approver_id)

    return {
        "approver_id": approver_id,
        "pending_count": len(pending),
        "approvals": pending
    }


@router.post("/{request_id}/approve/{step_id}")
async def process_approval(
    request_id: str,
    step_id: str,
    approval: ApprovalActionModel
):
    """
    Process an approval action on a request.

    Actions: approve, reject, delegate, request_info, escalate
    """
    try:
        # Map action string to enum
        action_map = {
            "approve": ApprovalAction.APPROVE,
            "reject": ApprovalAction.REJECT,
            "delegate": ApprovalAction.DELEGATE,
            "request_info": ApprovalAction.REQUEST_INFO,
            "escalate": ApprovalAction.ESCALATE
        }
        action = action_map.get(approval.action.lower())

        if not action:
            raise ValueError(f"Invalid action: {approval.action}")

        access_request = await request_manager.process_approval(
            request_id=request_id,
            step_id=step_id,
            action=action,
            actor_id=approval.actor_id,
            comments=approval.comments or "",
            delegate_to=approval.delegate_to
        )

        return {
            "request_id": request_id,
            "action_taken": approval.action,
            "status": access_request.status.value,
            "current_step": access_request.current_step,
            "is_fully_approved": access_request.is_fully_approved(),
            "message": f"Action '{approval.action}' processed successfully"
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.post("/{request_id}/bulk-approve")
async def bulk_approve(
    request_id: str,
    actor_id: str = Query(...),
    comments: str = Query(default="Bulk approved")
):
    """
    Approve all pending steps (for authorized super-approvers).
    """
    access_request = request_manager.get_request(request_id)

    if not access_request:
        raise HTTPException(status_code=404, detail=f"Request {request_id} not found")

    approved_steps = []
    for step in access_request.approval_steps:
        if step.status.value == "pending":
            try:
                await request_manager.process_approval(
                    request_id=request_id,
                    step_id=step.step_id,
                    action=ApprovalAction.APPROVE,
                    actor_id=actor_id,
                    comments=comments
                )
                approved_steps.append(step.step_id)
            except Exception:
                pass

    return {
        "request_id": request_id,
        "steps_approved": len(approved_steps),
        "status": access_request.status.value
    }


# =============================================================================
# User-Specific Endpoints
# =============================================================================

@router.get("/my-requests")
async def get_my_requests(user_id: str = Query(...)):
    """Get all requests created by the current user"""
    requests = request_manager.get_requests_for_user(user_id)

    return {
        "user_id": user_id,
        "total": len(requests),
        "requests": [r.to_summary() for r in requests]
    }


@router.get("/my-access")
async def get_my_access(user_id: str = Query(...)):
    """Get all access granted to a user through requests"""
    requests = request_manager.get_requests_for_target(user_id)

    # Filter to provisioned/active access
    active = [
        r for r in requests
        if r.status == AccessRequestStatus.PROVISIONED
    ]

    return {
        "user_id": user_id,
        "active_access": [
            {
                "request_id": r.request_id,
                "roles": [i.access_name for i in r.requested_items],
                "granted_at": r.provisioned_at.isoformat() if r.provisioned_at else None,
                "expires_at": r.access_expires_at.isoformat() if r.access_expires_at else "Never",
                "is_temporary": r.is_temporary
            }
            for r in active
        ]
    }


# =============================================================================
# Statistics Endpoints
# =============================================================================

@router.get("/statistics")
async def get_request_statistics():
    """Get overall request statistics"""
    return request_manager.get_statistics()


@router.get("/statistics/sla")
async def get_sla_statistics():
    """Get SLA compliance statistics"""
    requests = list(request_manager.requests.values())

    total_pending = sum(1 for r in requests
                       if r.status == AccessRequestStatus.PENDING_APPROVAL)

    overdue = sum(1 for r in requests
                 if r.status == AccessRequestStatus.PENDING_APPROVAL
                 and any(s.is_overdue() for s in r.approval_steps))

    # Calculate average approval time for completed requests
    completed = [r for r in requests if r.completed_at and r.submitted_at]
    avg_hours = 0
    if completed:
        total_hours = sum(
            (r.completed_at - r.submitted_at).total_seconds() / 3600
            for r in completed
        )
        avg_hours = total_hours / len(completed)

    return {
        "total_pending": total_pending,
        "overdue_count": overdue,
        "sla_compliance_rate": ((total_pending - overdue) / total_pending * 100) if total_pending > 0 else 100,
        "average_approval_hours": round(avg_hours, 1),
        "requests_completed_today": sum(1 for r in completed
                                        if r.completed_at and r.completed_at.date() == datetime.now().date())
    }
