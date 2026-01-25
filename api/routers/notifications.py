# Notifications API Router
# Email and In-App Notification Management

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum

from core.notifications import (
    NotificationService, Notification, NotificationType,
    NotificationChannel, NotificationPriority
)

router = APIRouter(prefix="/notifications", tags=["Notifications"])

# Global service instance
notification_service = NotificationService()


# ==================== Request/Response Models ====================

class SendNotificationRequest(BaseModel):
    recipient_id: str
    notification_type: str
    context: Dict[str, Any] = {}
    channels: List[str] = ["in_app"]
    priority: str = "normal"


class MarkReadRequest(BaseModel):
    notification_ids: List[str]


class NotificationPreferencesRequest(BaseModel):
    email_enabled: bool = True
    in_app_enabled: bool = True
    digest_enabled: bool = False
    digest_frequency: str = "daily"
    quiet_hours_start: Optional[str] = None
    quiet_hours_end: Optional[str] = None
    disabled_types: List[str] = []


# ==================== User Notifications ====================

@router.get("/")
async def list_notifications(
    user_id: str,
    unread_only: bool = False,
    notification_type: Optional[str] = None,
    limit: int = Query(default=50, le=200),
    offset: int = 0
):
    """
    List notifications for a user

    Filter by read/unread status and notification type.
    """
    notifications = notification_service.get_user_notifications(
        user_id=user_id,
        unread_only=unread_only
    )

    # Apply type filter
    if notification_type:
        try:
            n_type = NotificationType(notification_type)
            notifications = [n for n in notifications if n.notification_type == n_type]
        except ValueError:
            pass

    # Apply pagination
    total = len(notifications)
    notifications = notifications[offset:offset + limit]

    return {
        "notifications": [
            {
                "id": n.id,
                "type": n.notification_type.value,
                "title": n.title,
                "message": n.message,
                "priority": n.priority.value,
                "read": n.read,
                "created_at": n.created_at.isoformat(),
                "read_at": n.read_at.isoformat() if n.read_at else None,
                "action_url": n.action_url,
                "context": n.context
            }
            for n in notifications
        ],
        "total": total,
        "unread_count": len([n for n in notifications if not n.read])
    }


@router.get("/unread-count")
async def get_unread_count(user_id: str):
    """Get count of unread notifications for a user"""
    notifications = notification_service.get_user_notifications(
        user_id=user_id,
        unread_only=True
    )
    return {"unread_count": len(notifications)}


@router.get("/{notification_id}")
async def get_notification(notification_id: str):
    """Get a specific notification"""
    for notifications in notification_service.notifications.values():
        for n in notifications:
            if n.id == notification_id:
                return {
                    "id": n.id,
                    "type": n.notification_type.value,
                    "title": n.title,
                    "message": n.message,
                    "priority": n.priority.value,
                    "read": n.read,
                    "created_at": n.created_at.isoformat(),
                    "read_at": n.read_at.isoformat() if n.read_at else None,
                    "action_url": n.action_url,
                    "context": n.context
                }

    raise HTTPException(status_code=404, detail="Notification not found")


@router.post("/{notification_id}/read")
async def mark_notification_read(notification_id: str):
    """Mark a notification as read"""
    result = notification_service.mark_as_read(notification_id)
    if not result["success"]:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.post("/mark-read")
async def mark_multiple_read(request: MarkReadRequest):
    """Mark multiple notifications as read"""
    results = []
    for nid in request.notification_ids:
        result = notification_service.mark_as_read(nid)
        results.append({"id": nid, "success": result["success"]})

    return {
        "results": results,
        "total_marked": len([r for r in results if r["success"]])
    }


@router.post("/mark-all-read")
async def mark_all_read(user_id: str):
    """Mark all notifications as read for a user"""
    result = notification_service.mark_all_as_read(user_id)
    return result


# ==================== Send Notifications ====================

@router.post("/send")
async def send_notification(request: SendNotificationRequest):
    """
    Send a notification to a user

    Supports multiple channels (email, in_app, teams, slack).
    """
    try:
        n_type = NotificationType(request.notification_type)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid notification type: {request.notification_type}"
        )

    try:
        priority = NotificationPriority(request.priority)
    except ValueError:
        priority = NotificationPriority.NORMAL

    channels = []
    for ch in request.channels:
        try:
            channels.append(NotificationChannel(ch))
        except ValueError:
            pass

    if not channels:
        channels = [NotificationChannel.IN_APP]

    result = notification_service.send_notification(
        recipient_id=request.recipient_id,
        notification_type=n_type,
        context=request.context,
        channels=channels,
        priority=priority
    )

    return result


# ==================== Convenience Endpoints ====================

@router.post("/approval-required")
async def notify_approval_required(
    approver_id: str,
    request_id: str,
    requester_name: str,
    request_type: str
):
    """Send approval required notification"""
    result = notification_service.notify_approval_required(
        approver_id=approver_id,
        request_id=request_id,
        requester_name=requester_name,
        request_type=request_type
    )
    return result


@router.post("/request-approved")
async def notify_request_approved(
    requester_id: str,
    request_id: str,
    request_type: str,
    approver_name: str
):
    """Send request approved notification"""
    result = notification_service.notify_request_approved(
        requester_id=requester_id,
        request_id=request_id,
        request_type=request_type,
        approver_name=approver_name
    )
    return result


@router.post("/request-rejected")
async def notify_request_rejected(
    requester_id: str,
    request_id: str,
    request_type: str,
    rejector_name: str,
    reason: str = ""
):
    """Send request rejected notification"""
    result = notification_service.notify_request_rejected(
        requester_id=requester_id,
        request_id=request_id,
        request_type=request_type,
        rejector_name=rejector_name,
        reason=reason
    )
    return result


@router.post("/firefighter-started")
async def notify_firefighter_started(
    controller_id: str,
    session_id: str,
    user_name: str,
    firefighter_id: str,
    reason: str
):
    """Send firefighter session started notification"""
    result = notification_service.notify_ff_session_started(
        controller_id=controller_id,
        session_id=session_id,
        user_name=user_name,
        firefighter_id=firefighter_id,
        reason=reason
    )
    return result


@router.post("/certification-due")
async def notify_certification_due(
    reviewer_id: str,
    campaign_name: str,
    due_date: str,
    items_count: int
):
    """Send certification review reminder"""
    result = notification_service.notify_certification_due(
        reviewer_id=reviewer_id,
        campaign_name=campaign_name,
        due_date=due_date,
        items_count=items_count
    )
    return result


@router.post("/risk-violation")
async def notify_risk_violation(
    user_id: str,
    risk_id: str,
    risk_name: str,
    risk_level: str
):
    """Send risk violation alert"""
    result = notification_service.notify_risk_violation(
        user_id=user_id,
        risk_id=risk_id,
        risk_name=risk_name,
        risk_level=risk_level
    )
    return result


# ==================== Templates ====================

@router.get("/templates")
async def list_templates():
    """List all notification templates"""
    return {
        "templates": [
            {
                "id": t.id,
                "name": t.name,
                "notification_type": t.notification_type.value,
                "subject_template": t.subject_template,
                "body_template": t.body_template[:200] + "..." if len(t.body_template) > 200 else t.body_template,
                "channels": [c.value for c in t.channels]
            }
            for t in notification_service.templates.values()
        ]
    }


@router.get("/templates/{template_id}")
async def get_template(template_id: str):
    """Get a specific notification template"""
    if template_id not in notification_service.templates:
        raise HTTPException(status_code=404, detail="Template not found")

    t = notification_service.templates[template_id]
    return {
        "id": t.id,
        "name": t.name,
        "notification_type": t.notification_type.value,
        "subject_template": t.subject_template,
        "body_template": t.body_template,
        "channels": [c.value for c in t.channels]
    }


# ==================== Notification Types ====================

@router.get("/types")
async def list_notification_types():
    """List all available notification types"""
    return {
        "types": [
            {"value": nt.value, "name": nt.name}
            for nt in NotificationType
        ]
    }


@router.get("/channels")
async def list_channels():
    """List available notification channels"""
    return {
        "channels": [
            {"value": ch.value, "name": ch.name}
            for ch in NotificationChannel
        ]
    }


# ==================== User Preferences ====================

@router.get("/preferences/{user_id}")
async def get_preferences(user_id: str):
    """Get notification preferences for a user"""
    prefs = notification_service.user_preferences.get(user_id, {})
    return {
        "user_id": user_id,
        "preferences": {
            "email_enabled": prefs.get("email_enabled", True),
            "in_app_enabled": prefs.get("in_app_enabled", True),
            "digest_enabled": prefs.get("digest_enabled", False),
            "digest_frequency": prefs.get("digest_frequency", "daily"),
            "quiet_hours_start": prefs.get("quiet_hours_start"),
            "quiet_hours_end": prefs.get("quiet_hours_end"),
            "disabled_types": prefs.get("disabled_types", [])
        }
    }


@router.put("/preferences/{user_id}")
async def update_preferences(user_id: str, request: NotificationPreferencesRequest):
    """Update notification preferences for a user"""
    notification_service.user_preferences[user_id] = {
        "email_enabled": request.email_enabled,
        "in_app_enabled": request.in_app_enabled,
        "digest_enabled": request.digest_enabled,
        "digest_frequency": request.digest_frequency,
        "quiet_hours_start": request.quiet_hours_start,
        "quiet_hours_end": request.quiet_hours_end,
        "disabled_types": request.disabled_types
    }

    return {
        "success": True,
        "message": "Preferences updated successfully"
    }


# ==================== Statistics ====================

@router.get("/stats")
async def get_notification_stats():
    """Get notification statistics"""
    total_notifications = sum(
        len(notifications)
        for notifications in notification_service.notifications.values()
    )

    unread_count = sum(
        len([n for n in notifications if not n.read])
        for notifications in notification_service.notifications.values()
    )

    by_type = {}
    for notifications in notification_service.notifications.values():
        for n in notifications:
            type_key = n.notification_type.value
            if type_key not in by_type:
                by_type[type_key] = 0
            by_type[type_key] += 1

    return {
        "total_notifications": total_notifications,
        "unread_count": unread_count,
        "by_type": by_type,
        "templates_count": len(notification_service.templates)
    }
