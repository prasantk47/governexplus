"""
Mobile API Endpoints

Optimized API endpoints for mobile applications.
Supports approval workflows, notifications, and quick actions.
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

router = APIRouter()


# ==================== Models ====================

class ApprovalAction(str, Enum):
    APPROVE = "approve"
    REJECT = "reject"
    DELEGATE = "delegate"
    REQUEST_INFO = "request_info"


class ApprovalItemType(str, Enum):
    ACCESS_REQUEST = "access_request"
    CERTIFICATION = "certification"
    FIREFIGHTER = "firefighter"
    POLICY_EXCEPTION = "policy_exception"


class ApprovalItem(BaseModel):
    """Unified approval item for mobile inbox"""
    item_id: str
    item_type: ApprovalItemType
    title: str
    description: str
    requester_name: str
    requester_id: str
    target_user_name: Optional[str] = None
    target_user_id: Optional[str] = None
    risk_level: str = "low"
    risk_score: float = 0.0
    priority: str = "normal"
    due_date: Optional[datetime] = None
    created_at: datetime
    details: Dict[str, Any] = {}
    quick_actions: List[str] = ["approve", "reject"]


class ApprovalActionRequest(BaseModel):
    """Request to perform an approval action"""
    action: ApprovalAction
    comments: Optional[str] = None
    delegate_to: Optional[str] = None  # For delegation
    conditions: Optional[Dict[str, Any]] = None  # For conditional approval


class ApprovalActionResponse(BaseModel):
    """Response from an approval action"""
    success: bool
    message: str
    item_id: str
    action: str
    next_step: Optional[str] = None


class NotificationItem(BaseModel):
    """Mobile notification item"""
    notification_id: str
    title: str
    body: str
    notification_type: str
    priority: str
    read: bool = False
    action_url: Optional[str] = None
    created_at: datetime


class DashboardSummary(BaseModel):
    """Mobile dashboard summary"""
    pending_approvals: int
    pending_certifications: int
    active_firefighter_sessions: int
    open_violations: int
    unread_notifications: int
    risk_score: float
    last_updated: datetime


class QuickAction(BaseModel):
    """Quick action for mobile"""
    action_id: str
    title: str
    icon: str
    color: str
    count: Optional[int] = None
    action_type: str
    action_url: str


# ==================== Dashboard ====================

@router.get("/dashboard", response_model=DashboardSummary)
async def get_mobile_dashboard(
    user_id: str = Query(..., description="Current user ID")
):
    """
    Get mobile dashboard summary

    Returns key metrics and counts for the mobile home screen.
    """
    return DashboardSummary(
        pending_approvals=5,
        pending_certifications=12,
        active_firefighter_sessions=1,
        open_violations=3,
        unread_notifications=8,
        risk_score=42.5,
        last_updated=datetime.utcnow()
    )


@router.get("/quick-actions", response_model=List[QuickAction])
async def get_quick_actions(
    user_id: str = Query(..., description="Current user ID")
):
    """
    Get quick actions for mobile home screen

    Returns personalized quick action buttons based on user role.
    """
    return [
        QuickAction(
            action_id="approvals",
            title="Approvals",
            icon="check-circle",
            color="#4CAF50",
            count=5,
            action_type="navigate",
            action_url="/mobile/approvals"
        ),
        QuickAction(
            action_id="certifications",
            title="Certifications",
            icon="clipboard-check",
            color="#2196F3",
            count=12,
            action_type="navigate",
            action_url="/mobile/certifications"
        ),
        QuickAction(
            action_id="firefighter",
            title="Emergency Access",
            icon="fire",
            color="#FF5722",
            count=None,
            action_type="navigate",
            action_url="/mobile/firefighter"
        ),
        QuickAction(
            action_id="risks",
            title="My Risks",
            icon="alert-triangle",
            color="#FFC107",
            count=3,
            action_type="navigate",
            action_url="/mobile/risks"
        )
    ]


# ==================== Unified Approval Inbox ====================

@router.get("/approvals", response_model=List[ApprovalItem])
async def get_pending_approvals(
    user_id: str = Query(..., description="Current user ID"),
    item_type: Optional[ApprovalItemType] = None,
    priority: Optional[str] = None,
    limit: int = Query(20, le=100),
    offset: int = 0
):
    """
    Get unified approval inbox

    Returns all pending approvals across access requests,
    certifications, and firefighter requests.
    """
    # Simulated data
    items = [
        ApprovalItem(
            item_id="AR_001",
            item_type=ApprovalItemType.ACCESS_REQUEST,
            title="Role Request: Z_FI_AP_CLERK",
            description="John Smith requests AP Clerk role for Finance department work",
            requester_name="John Smith",
            requester_id="JSMITH",
            target_user_name="John Smith",
            target_user_id="JSMITH",
            risk_level="medium",
            risk_score=45.0,
            priority="normal",
            due_date=datetime(2026, 1, 20),
            created_at=datetime(2026, 1, 17, 10, 30),
            details={
                "roles": ["Z_FI_AP_CLERK"],
                "justification": "Need access for invoice processing",
                "sod_conflicts": 0
            },
            quick_actions=["approve", "reject", "delegate"]
        ),
        ApprovalItem(
            item_id="FF_001",
            item_type=ApprovalItemType.FIREFIGHTER,
            title="Emergency Access Request",
            description="Tom Davis requests emergency access for production incident",
            requester_name="Tom Davis",
            requester_id="TDAVIS",
            risk_level="critical",
            risk_score=85.0,
            priority="urgent",
            due_date=datetime(2026, 1, 17, 14, 0),
            created_at=datetime(2026, 1, 17, 12, 0),
            details={
                "firefighter_id": "FF_EMERGENCY_01",
                "reason": "Production order processing failure",
                "requested_hours": 4
            },
            quick_actions=["approve", "reject"]
        ),
        ApprovalItem(
            item_id="CERT_001",
            item_type=ApprovalItemType.CERTIFICATION,
            title="Certify Access: Mary Brown",
            description="Review and certify access for Mary Brown (Procurement Manager)",
            requester_name="System",
            requester_id="SYSTEM",
            target_user_name="Mary Brown",
            target_user_id="MBROWN",
            risk_level="high",
            risk_score=65.0,
            priority="normal",
            due_date=datetime(2026, 1, 25),
            created_at=datetime(2026, 1, 10),
            details={
                "campaign": "Q1 2026 Access Review",
                "roles_count": 5,
                "last_login": "2026-01-16"
            },
            quick_actions=["certify", "revoke", "modify"]
        )
    ]

    # Filter by type if specified
    if item_type:
        items = [i for i in items if i.item_type == item_type]

    # Filter by priority if specified
    if priority:
        items = [i for i in items if i.priority == priority]

    return items[offset:offset + limit]


@router.get("/approvals/{item_id}", response_model=ApprovalItem)
async def get_approval_detail(
    item_id: str,
    user_id: str = Query(..., description="Current user ID")
):
    """
    Get detailed approval item

    Returns full details for a specific approval item.
    """
    # Would fetch from database
    return ApprovalItem(
        item_id=item_id,
        item_type=ApprovalItemType.ACCESS_REQUEST,
        title="Role Request: Z_FI_AP_CLERK",
        description="John Smith requests AP Clerk role",
        requester_name="John Smith",
        requester_id="JSMITH",
        target_user_name="John Smith",
        target_user_id="JSMITH",
        risk_level="medium",
        risk_score=45.0,
        priority="normal",
        created_at=datetime.utcnow(),
        details={
            "roles": ["Z_FI_AP_CLERK"],
            "justification": "Need access for invoice processing",
            "current_roles": ["Z_FI_DISPLAY"],
            "risk_analysis": {
                "sod_conflicts": 0,
                "sensitive_access": False
            },
            "workflow_history": [
                {"step": "Submitted", "date": "2026-01-17", "actor": "JSMITH"},
                {"step": "Manager Approved", "date": "2026-01-17", "actor": "MANAGER1"}
            ]
        }
    )


@router.post("/approvals/{item_id}/action", response_model=ApprovalActionResponse)
async def perform_approval_action(
    item_id: str,
    action_request: ApprovalActionRequest,
    user_id: str = Query(..., description="Current user ID")
):
    """
    Perform approval action

    Execute approve, reject, delegate, or request-info on an approval item.
    """
    # Validate and process action
    if action_request.action == ApprovalAction.REJECT and not action_request.comments:
        raise HTTPException(
            status_code=400,
            detail="Comments are required when rejecting"
        )

    if action_request.action == ApprovalAction.DELEGATE and not action_request.delegate_to:
        raise HTTPException(
            status_code=400,
            detail="Delegate target is required for delegation"
        )

    # Process the action
    return ApprovalActionResponse(
        success=True,
        message=f"Successfully {action_request.action.value}d item {item_id}",
        item_id=item_id,
        action=action_request.action.value,
        next_step="Pending role owner approval" if action_request.action == ApprovalAction.APPROVE else None
    )


@router.post("/approvals/bulk-action", response_model=List[ApprovalActionResponse])
async def bulk_approval_action(
    item_ids: List[str],
    action_request: ApprovalActionRequest,
    user_id: str = Query(..., description="Current user ID")
):
    """
    Perform bulk approval action

    Execute the same action on multiple approval items at once.
    """
    results = []
    for item_id in item_ids:
        results.append(ApprovalActionResponse(
            success=True,
            message=f"Successfully {action_request.action.value}d",
            item_id=item_id,
            action=action_request.action.value
        ))

    return results


# ==================== Notifications ====================

@router.get("/notifications", response_model=List[NotificationItem])
async def get_notifications(
    user_id: str = Query(..., description="Current user ID"),
    unread_only: bool = False,
    limit: int = Query(50, le=100),
    offset: int = 0
):
    """
    Get user notifications

    Returns notifications for the mobile notification center.
    """
    notifications = [
        NotificationItem(
            notification_id="N001",
            title="Access Request Approved",
            body="Your request for Z_FI_AP_CLERK has been approved",
            notification_type="access_request",
            priority="normal",
            read=False,
            action_url="/access-requests/AR_001",
            created_at=datetime(2026, 1, 17, 11, 0)
        ),
        NotificationItem(
            notification_id="N002",
            title="Certification Due Soon",
            body="12 items due for certification by Jan 25",
            notification_type="certification",
            priority="high",
            read=False,
            action_url="/certification/pending",
            created_at=datetime(2026, 1, 17, 9, 0)
        ),
        NotificationItem(
            notification_id="N003",
            title="Firefighter Session Ended",
            body="Emergency session FF_SESSION_001 has ended. Please complete review.",
            notification_type="firefighter",
            priority="high",
            read=True,
            action_url="/firefighter/sessions/FF_SESSION_001/review",
            created_at=datetime(2026, 1, 16, 17, 0)
        )
    ]

    if unread_only:
        notifications = [n for n in notifications if not n.read]

    return notifications[offset:offset + limit]


@router.post("/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: str,
    user_id: str = Query(..., description="Current user ID")
):
    """Mark a notification as read"""
    return {"success": True, "notification_id": notification_id}


@router.post("/notifications/mark-all-read")
async def mark_all_notifications_read(
    user_id: str = Query(..., description="Current user ID")
):
    """Mark all notifications as read"""
    return {"success": True, "count": 5}


# ==================== Firefighter Quick Access ====================

@router.post("/firefighter/quick-request")
async def quick_firefighter_request(
    firefighter_id: str,
    reason: str,
    hours: int = 4,
    user_id: str = Query(..., description="Current user ID")
):
    """
    Quick firefighter access request

    Streamlined emergency access request for mobile.
    """
    return {
        "request_id": "FF_REQ_001",
        "status": "pending_approval",
        "firefighter_id": firefighter_id,
        "requested_hours": hours,
        "estimated_approval_time": "< 30 minutes",
        "message": "Request submitted. You will be notified when approved."
    }


@router.get("/firefighter/active-sessions")
async def get_active_firefighter_sessions(
    user_id: str = Query(..., description="Current user ID")
):
    """
    Get user's active firefighter sessions

    Returns currently active emergency access sessions.
    """
    return [
        {
            "session_id": "FF_SESSION_001",
            "firefighter_id": "FF_EMERGENCY_01",
            "started_at": datetime(2026, 1, 17, 12, 30).isoformat(),
            "expires_at": datetime(2026, 1, 17, 16, 30).isoformat(),
            "remaining_minutes": 120,
            "activity_count": 15,
            "status": "active"
        }
    ]


# ==================== User Profile ====================

@router.get("/profile")
async def get_mobile_profile(
    user_id: str = Query(..., description="Current user ID")
):
    """
    Get user profile for mobile

    Returns user information and access summary.
    """
    return {
        "user_id": user_id,
        "name": "John Smith",
        "email": "jsmith@company.com",
        "department": "Finance",
        "manager": "Jane Manager",
        "role_count": 5,
        "risk_score": 42.5,
        "risk_level": "medium",
        "pending_actions": 5,
        "last_login": datetime(2026, 1, 17, 8, 0).isoformat()
    }


@router.get("/profile/my-access")
async def get_my_access(
    user_id: str = Query(..., description="Current user ID")
):
    """
    Get user's current access

    Returns roles and entitlements for the current user.
    """
    return {
        "roles": [
            {
                "role_id": "Z_FI_DISPLAY",
                "role_name": "Finance Display",
                "valid_from": "2025-01-01",
                "valid_to": "2026-12-31",
                "risk_level": "low"
            },
            {
                "role_id": "Z_FI_AP_CLERK",
                "role_name": "AP Clerk",
                "valid_from": "2025-06-01",
                "valid_to": "2026-12-31",
                "risk_level": "medium"
            }
        ],
        "systems": ["SAP_ECC_PRD", "SAP_BW"],
        "total_transactions": 45,
        "sensitive_access": False
    }


# ==================== Offline Support ====================

@router.get("/sync/pending-items")
async def get_offline_sync_data(
    user_id: str = Query(..., description="Current user ID"),
    last_sync: Optional[datetime] = None
):
    """
    Get data for offline sync

    Returns approval items and notifications for offline caching.
    """
    return {
        "sync_timestamp": datetime.utcnow().isoformat(),
        "approvals": await get_pending_approvals(user_id),
        "notifications": await get_notifications(user_id),
        "dashboard": await get_mobile_dashboard(user_id)
    }


@router.post("/sync/offline-actions")
async def sync_offline_actions(
    actions: List[Dict[str, Any]],
    user_id: str = Query(..., description="Current user ID")
):
    """
    Sync offline actions

    Process actions that were taken while offline.
    """
    results = []
    for action in actions:
        # Process each offline action
        results.append({
            "action_id": action.get("action_id"),
            "status": "synced",
            "server_timestamp": datetime.utcnow().isoformat()
        })

    return {
        "synced_count": len(results),
        "results": results
    }
