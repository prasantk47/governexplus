"""
Approvals API Router

Simplified approval endpoints for the frontend approval inbox.
Uses real DB-backed AccessRequestManager instead of mock data.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session

from db.database import get_db
from core.access_request.manager import AccessRequestManager
from core.access_request.models import ApprovalAction

router = APIRouter(tags=["Approvals"])


class QuickApprovalModel(BaseModel):
    """Model for quick approval/rejection"""
    quickApproval: Optional[bool] = False
    quickReject: Optional[bool] = False
    comments: Optional[str] = None
    actor_id: Optional[str] = "current_user"


def _get_manager(db: Session = Depends(get_db)):
    return AccessRequestManager(db=db)


@router.get("/")
async def list_pending_approvals(
    approver_id: Optional[str] = None,
    mgr: AccessRequestManager = Depends(_get_manager),
):
    """Get all pending approvals"""
    if approver_id:
        pending = mgr.get_pending_approvals(approver_id)
    else:
        # Return all requests with pending_approval status
        pending_requests = mgr.get_all_requests(status="pending_approval")
        pending = []
        for req in pending_requests:
            pending.append({
                "id": req.request_id,
                "type": "access_request",
                "requester": req.requester_user_id,
                "summary": ", ".join(
                    [item.role_id or item.entitlement_id or "" for item in req.requested_items]
                ) if req.requested_items else "",
                "riskLevel": req.risk_level or "medium",
                "submittedDate": req.submitted_at.isoformat() if req.submitted_at else None,
                "priority": req.priority or "normal",
                "status": req.status.value if hasattr(req.status, "value") else str(req.status),
            })
    return {
        "total": len(pending),
        "approvals": pending,
    }


@router.get("/{approval_id}")
async def get_approval(
    approval_id: str,
    mgr: AccessRequestManager = Depends(_get_manager),
):
    """Get a specific approval item"""
    request = mgr.get_request(approval_id)
    if not request:
        raise HTTPException(status_code=404, detail=f"Approval {approval_id} not found")

    return {
        "id": request.request_id,
        "type": "access_request",
        "requester": request.requester_user_id,
        "summary": ", ".join(
            [item.role_id or item.entitlement_id or "" for item in request.requested_items]
        ) if request.requested_items else "",
        "riskLevel": request.risk_level or "medium",
        "submittedDate": request.submitted_at.isoformat() if request.submitted_at else None,
        "priority": request.priority or "normal",
        "status": request.status.value if hasattr(request.status, "value") else str(request.status),
        "approval_steps": [
            {
                "step_id": step.step_id,
                "step_name": step.step_name,
                "status": step.status.value if hasattr(step.status, "value") else str(step.status),
                "approver_ids": step.approver_ids,
            }
            for step in request.approval_steps
        ] if request.approval_steps else [],
    }


@router.post("/{approval_id}/approve")
async def approve_request(
    approval_id: str,
    body: QuickApprovalModel = None,
    mgr: AccessRequestManager = Depends(_get_manager),
):
    """
    Approve a pending request.

    Finds the first pending approval step and approves it.
    """
    request = mgr.get_request(approval_id)
    if not request:
        raise HTTPException(status_code=404, detail=f"Request {approval_id} not found")

    # Find the first pending step
    step_id = None
    for step in request.approval_steps:
        step_status = step.status.value if hasattr(step.status, "value") else str(step.status)
        if step_status == "pending":
            step_id = step.step_id
            break

    if not step_id:
        raise HTTPException(status_code=400, detail="No pending approval steps found")

    actor_id = body.actor_id if body and body.actor_id else "current_user"
    comments = body.comments if body and body.comments else ""

    try:
        await mgr.process_approval(
            request_id=approval_id,
            step_id=step_id,
            action=ApprovalAction.APPROVE,
            actor_id=actor_id,
            comments=comments,
        )
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))

    return {
        "success": True,
        "request_id": approval_id,
        "status": "approved",
        "message": f"Request {approval_id} has been approved",
    }


@router.post("/{approval_id}/reject")
async def reject_request(
    approval_id: str,
    body: QuickApprovalModel = None,
    mgr: AccessRequestManager = Depends(_get_manager),
):
    """
    Reject a pending request.

    Finds the first pending approval step and rejects it.
    """
    request = mgr.get_request(approval_id)
    if not request:
        raise HTTPException(status_code=404, detail=f"Request {approval_id} not found")

    # Find the first pending step
    step_id = None
    for step in request.approval_steps:
        step_status = step.status.value if hasattr(step.status, "value") else str(step.status)
        if step_status == "pending":
            step_id = step.step_id
            break

    if not step_id:
        raise HTTPException(status_code=400, detail="No pending approval steps found")

    actor_id = body.actor_id if body and body.actor_id else "current_user"
    comments = body.comments if body and body.comments else "Request rejected"

    try:
        await mgr.process_approval(
            request_id=approval_id,
            step_id=step_id,
            action=ApprovalAction.REJECT,
            actor_id=actor_id,
            comments=comments,
        )
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))

    return {
        "success": True,
        "request_id": approval_id,
        "status": "rejected",
        "message": f"Request {approval_id} has been rejected",
    }


@router.post("/{approval_id}/forward")
async def forward_request(
    approval_id: str,
    forward_to: str,
    mgr: AccessRequestManager = Depends(_get_manager),
):
    """Forward a request to another approver"""
    request = mgr.get_request(approval_id)
    if not request:
        raise HTTPException(status_code=404, detail=f"Request {approval_id} not found")

    # Find the first pending step
    step_id = None
    for step in request.approval_steps:
        step_status = step.status.value if hasattr(step.status, "value") else str(step.status)
        if step_status == "pending":
            step_id = step.step_id
            break

    if not step_id:
        raise HTTPException(status_code=400, detail="No pending approval steps found")

    try:
        await mgr.process_approval(
            request_id=approval_id,
            step_id=step_id,
            action=ApprovalAction.DELEGATE,
            actor_id="current_user",
            delegate_to=forward_to,
        )
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))

    return {
        "success": True,
        "request_id": approval_id,
        "forwarded_to": forward_to,
        "message": f"Request {approval_id} has been forwarded to {forward_to}",
    }
