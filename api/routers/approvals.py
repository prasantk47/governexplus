"""
Approvals API Router

Simplified approval endpoints for the frontend approval inbox.
Maps to the more detailed access_requests approval flow.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

router = APIRouter(tags=["Approvals"])


class QuickApprovalModel(BaseModel):
    """Model for quick approval/rejection"""
    quickApproval: Optional[bool] = False
    quickReject: Optional[bool] = False
    comments: Optional[str] = None
    actor_id: Optional[str] = "current_user"


# Mock pending approvals data
MOCK_APPROVALS = {
    "REQ-2024-001": {
        "id": "REQ-2024-001",
        "type": "access_request",
        "requester": "John Smith",
        "requesterDept": "Finance",
        "summary": "SAP_FI_AP_CLERK, SAP_FI_GL_ACCOUNTANT",
        "riskLevel": "high",
        "submittedDate": "2024-01-15",
        "dueDate": "2024-01-18",
        "priority": "urgent",
        "sodConflicts": True,
        "status": "pending"
    },
    "REQ-2024-002": {
        "id": "REQ-2024-002",
        "type": "access_request",
        "requester": "Emily Davis",
        "requesterDept": "Sales",
        "summary": "SALESFORCE_ADMIN",
        "riskLevel": "high",
        "submittedDate": "2024-01-16",
        "dueDate": "2024-01-19",
        "priority": "high",
        "sodConflicts": False,
        "status": "pending"
    },
    "REQ-2024-003": {
        "id": "REQ-2024-003",
        "type": "access_request",
        "requester": "Lisa Chen",
        "requesterDept": "HR",
        "summary": "WORKDAY_HR_ADMIN",
        "riskLevel": "medium",
        "submittedDate": "2024-01-14",
        "dueDate": "2024-01-21",
        "priority": "normal",
        "sodConflicts": False,
        "status": "pending"
    },
}


@router.get("/")
async def list_pending_approvals():
    """Get all pending approvals"""
    pending = [a for a in MOCK_APPROVALS.values() if a.get("status") == "pending"]
    return {
        "total": len(pending),
        "approvals": pending
    }


@router.get("/{approval_id}")
async def get_approval(approval_id: str):
    """Get a specific approval item"""
    if approval_id not in MOCK_APPROVALS:
        raise HTTPException(status_code=404, detail=f"Approval {approval_id} not found")

    return MOCK_APPROVALS[approval_id]


@router.post("/{approval_id}/approve")
async def approve_request(approval_id: str, body: QuickApprovalModel = None):
    """
    Approve a pending request.

    This is a simplified endpoint for quick approvals from the approval inbox.
    """
    if approval_id not in MOCK_APPROVALS:
        raise HTTPException(status_code=404, detail=f"Request {approval_id} not found")

    approval = MOCK_APPROVALS[approval_id]

    # Update status (allow re-approving for demo)
    approval["status"] = "approved"
    approval["approvedAt"] = datetime.now().isoformat()
    approval["approvedBy"] = body.actor_id if body else "current_user"

    return {
        "success": True,
        "request_id": approval_id,
        "status": "approved",
        "message": f"Request {approval_id} has been approved"
    }


@router.post("/{approval_id}/reject")
async def reject_request(approval_id: str, body: QuickApprovalModel = None):
    """
    Reject a pending request.

    This is a simplified endpoint for quick rejections from the approval inbox.
    """
    if approval_id not in MOCK_APPROVALS:
        raise HTTPException(status_code=404, detail=f"Request {approval_id} not found")

    approval = MOCK_APPROVALS[approval_id]

    # Update status (allow re-rejecting for demo)
    approval["status"] = "rejected"
    approval["rejectedAt"] = datetime.now().isoformat()
    approval["rejectedBy"] = body.actor_id if body else "current_user"
    approval["rejectionReason"] = body.comments if body and body.comments else "Request rejected"

    return {
        "success": True,
        "request_id": approval_id,
        "status": "rejected",
        "message": f"Request {approval_id} has been rejected"
    }


@router.post("/{approval_id}/forward")
async def forward_request(approval_id: str, forward_to: str):
    """Forward a request to another approver"""
    if approval_id not in MOCK_APPROVALS:
        raise HTTPException(status_code=404, detail=f"Request {approval_id} not found")

    return {
        "success": True,
        "request_id": approval_id,
        "forwarded_to": forward_to,
        "message": f"Request {approval_id} has been forwarded to {forward_to}"
    }
