"""
Notification Delivery API Router

Endpoints for sending, tracking, and configuring real email and Slack
notifications. Backed by NotificationDeliveryEngine in
core/notifications/delivery.py.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field, EmailStr

from core.notifications.delivery import (
    DeliveryChannel,
    Notification,
    NotificationType,
    get_delivery_engine,
)
from core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(tags=["Notification Delivery"])
_engine = get_delivery_engine()


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------

class SendEmailRequest(BaseModel):
    to: List[str] = Field(..., min_length=1, description="Recipient email addresses")
    subject: str = Field(..., min_length=1)
    body: str = Field(..., min_length=1)
    html_body: Optional[str] = None
    cc: Optional[List[str]] = None


class SendSlackRequest(BaseModel):
    channel: str = Field(..., min_length=1, description="Slack channel e.g. #grc-alerts")
    message: str = Field(..., min_length=1)
    blocks: Optional[List[Dict[str, Any]]] = None


class SendNotificationRequest(BaseModel):
    notification_type: str = Field(
        ...,
        description="One of the NotificationType values",
    )
    recipient_id: str = Field(..., description="Internal user ID")
    recipient_email: Optional[str] = Field(None, description="Destination email address")
    recipient_slack_channel: Optional[str] = Field(None, description="Destination Slack channel")
    channels: List[str] = Field(
        default=["email"],
        description="Delivery channels: email, slack",
    )
    context: Dict[str, Any] = Field(
        default_factory=dict,
        description="Template variable substitutions",
    )


class BulkSendRequest(BaseModel):
    notifications: List[SendNotificationRequest] = Field(..., min_length=1)


class UserPreferencesRequest(BaseModel):
    email_enabled: bool = True
    slack_enabled: bool = False
    slack_channel: Optional[str] = None
    disabled_types: List[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_notification_type(value: str) -> NotificationType:
    try:
        return NotificationType(value)
    except ValueError:
        valid = [t.value for t in NotificationType]
        raise HTTPException(
            status_code=422,
            detail=f"Unknown notification_type '{value}'. Valid values: {valid}",
        )


def _parse_channel(value: str) -> DeliveryChannel:
    try:
        return DeliveryChannel(value)
    except ValueError:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown channel '{value}'. Valid: email, slack",
        )


def _build_notification(req: SendNotificationRequest) -> Notification:
    ntype = _parse_notification_type(req.notification_type)
    channels = [_parse_channel(c) for c in req.channels]
    return Notification(
        notification_type=ntype,
        recipient_id=req.recipient_id,
        recipient_email=req.recipient_email,
        recipient_slack_channel=req.recipient_slack_channel,
        channels=channels,
        context=req.context,
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/send")
async def send_notification(req: SendNotificationRequest) -> Dict[str, Any]:
    """
    Send a single notification via one or more channels.

    The body of the notification is rendered from the built-in template for the
    given notification_type. Supply context keys to fill template placeholders.
    """
    notification = _build_notification(req)
    records = _engine.send_notification(notification)
    if not records:
        raise HTTPException(
            status_code=400,
            detail="No delivery records created. Check that recipient_email or "
                   "recipient_slack_channel is provided for the requested channels.",
        )
    logger.info(
        "api.notification_sent",
        notification_id=notification.notification_id,
        channels=req.channels,
    )
    return {
        "notification_id": notification.notification_id,
        "records": [r.to_dict() for r in records],
        "sent_at": datetime.utcnow().isoformat(),
    }


@router.post("/send-bulk")
async def send_bulk(req: BulkSendRequest) -> Dict[str, Any]:
    """
    Send multiple notifications in a single request.

    Returns a mapping of notification_id -> list of delivery records.
    """
    notifications = [_build_notification(n) for n in req.notifications]
    results = _engine.send_bulk(notifications)
    flattened = {
        nid: [r.to_dict() for r in recs]
        for nid, recs in results.items()
    }
    logger.info("api.bulk_sent", count=len(notifications))
    return {
        "total": len(notifications),
        "results": flattened,
        "sent_at": datetime.utcnow().isoformat(),
    }


@router.get("/history")
async def get_history(
    user_id: Optional[str] = Query(None, description="Filter by recipient user ID"),
    limit: int = Query(100, ge=1, le=500),
) -> Dict[str, Any]:
    """
    Retrieve delivery history, optionally filtered by user.
    Returns most recent records first.
    """
    records = _engine.get_delivery_history(user_id=user_id, limit=limit)
    return {
        "total": len(records),
        "user_id": user_id,
        "records": records,
    }


@router.get("/status/{notification_id}")
async def get_status(notification_id: str) -> Dict[str, Any]:
    """
    Get the delivery status of a specific notification by ID.
    Returns one record per channel that was attempted.
    """
    status = _engine.get_delivery_status(notification_id)
    if status is None:
        raise HTTPException(
            status_code=404,
            detail=f"No delivery records found for notification_id '{notification_id}'",
        )
    return status


@router.post("/retry")
async def retry_failed() -> Dict[str, Any]:
    """
    Retry all failed deliveries that have not yet reached the maximum
    attempt threshold. Returns a summary of the retry run.
    """
    summary = _engine.retry_failed()
    logger.info("api.retry_run", **summary)
    return {
        **summary,
        "run_at": datetime.utcnow().isoformat(),
    }


@router.get("/templates")
async def list_templates() -> Dict[str, Any]:
    """
    Return metadata for all built-in notification templates, including
    the subject/body template strings and available placeholders.
    """
    templates = _engine.get_templates()
    return {
        "total": len(templates),
        "templates": templates,
    }


@router.get("/preferences/{user_id}")
async def get_preferences(user_id: str) -> Dict[str, Any]:
    """
    Retrieve notification channel preferences for a user.
    Returns defaults when the user has not yet set preferences.
    """
    return _engine.get_preferences(user_id)


@router.put("/preferences/{user_id}")
async def update_preferences(
    user_id: str,
    req: UserPreferencesRequest,
) -> Dict[str, Any]:
    """
    Update notification delivery preferences for a user.
    Controls which channels are active and which notification types are muted.
    """
    prefs = _engine.set_preferences(user_id, req.model_dump())
    logger.info("api.preferences_updated", user_id=user_id)
    return {
        "message": "Preferences updated",
        "preferences": prefs,
    }
