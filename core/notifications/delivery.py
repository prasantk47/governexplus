"""
Notification Delivery Engine

Real delivery of notifications via SMTP email and Slack (webhook or Bot API).
When environment variables are not configured, falls back to mock mode that
logs the notification payload instead of transmitting it.

Environment variables:
    SMTP_HOST          SMTP server hostname
    SMTP_PORT          SMTP server port (default: 587)
    SMTP_USER          SMTP authentication username
    SMTP_PASSWORD      SMTP authentication password
    SMTP_FROM          Sender address (default: noreply@governexplus.com)
    SMTP_USE_TLS       Use STARTTLS (default: true)
    SLACK_WEBHOOK_URL  Incoming webhook URL (simple posting)
    SLACK_BOT_TOKEN    Bot token for channel-based API posting
    SLACK_DEFAULT_CHANNEL  Fallback channel (default: #grc-alerts)
"""

from __future__ import annotations

import os
import smtplib
import ssl
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from urllib.request import Request as HTTPRequest
from urllib.request import urlopen
from urllib.error import URLError, HTTPError

from db.database import db_manager
from db.models.operations import NotificationRecord as NotificationRecordModel
from db.models.operations import NotificationPreference as NotificationPreferenceModel
from core.tenant import get_current_tenant
from core.logging import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class DeliveryStatus(str, Enum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    RETRYING = "retrying"
    MOCK = "mock"


class DeliveryChannel(str, Enum):
    EMAIL = "email"
    SLACK = "slack"


class NotificationType(str, Enum):
    ACCESS_REQUEST_SUBMITTED = "access_request_submitted"
    APPROVAL_NEEDED = "approval_needed"
    REQUEST_APPROVED = "request_approved"
    REQUEST_REJECTED = "request_rejected"
    MITIGATION_EXPIRING = "mitigation_expiring"
    CERTIFICATION_DUE = "certification_due"
    FIREFIGHTER_USAGE = "firefighter_usage"
    RISK_VIOLATION_DETECTED = "risk_violation_detected"
    PASSWORD_EXPIRING = "password_expiring"
    SYNC_FAILED = "sync_failed"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class EmailPayload:
    """All fields needed to send one email."""
    to: List[str]
    subject: str
    body: str
    html_body: Optional[str] = None
    cc: Optional[List[str]] = None
    reply_to: Optional[str] = None


@dataclass
class SlackPayload:
    """All fields needed to post one Slack message."""
    channel: str
    message: str
    blocks: Optional[List[Dict[str, Any]]] = None
    username: str = "GovernexPlus"
    icon_emoji: str = ":shield:"


@dataclass
class Notification:
    """A single notification to be delivered."""
    notification_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    notification_type: NotificationType = NotificationType.ACCESS_REQUEST_SUBMITTED
    recipient_id: str = ""
    recipient_email: Optional[str] = None
    recipient_slack_channel: Optional[str] = None
    channels: List[DeliveryChannel] = field(default_factory=lambda: [DeliveryChannel.EMAIL])
    subject: str = ""
    body: str = ""
    html_body: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class DeliveryRecord:
    """Persisted record for one delivery attempt."""
    record_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    notification_id: str = ""
    notification_type: str = ""
    recipient_id: str = ""
    recipient_email: Optional[str] = None
    recipient_slack_channel: Optional[str] = None
    channel: str = ""
    status: DeliveryStatus = DeliveryStatus.PENDING
    attempts: int = 0
    last_attempt_at: Optional[datetime] = None
    sent_at: Optional[datetime] = None
    error_message: Optional[str] = None
    payload_summary: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "record_id": self.record_id,
            "notification_id": self.notification_id,
            "notification_type": self.notification_type,
            "recipient_id": self.recipient_id,
            "recipient_email": self.recipient_email,
            "recipient_slack_channel": self.recipient_slack_channel,
            "channel": self.channel,
            "status": self.status.value if isinstance(self.status, DeliveryStatus) else self.status,
            "attempts": self.attempts,
            "last_attempt_at": self.last_attempt_at.isoformat() if self.last_attempt_at else None,
            "sent_at": self.sent_at.isoformat() if self.sent_at else None,
            "error_message": self.error_message,
            "payload_summary": self.payload_summary,
            "created_at": self.created_at.isoformat(),
        }


# ---------------------------------------------------------------------------
# Notification templates
# ---------------------------------------------------------------------------

_TEMPLATES: Dict[NotificationType, Dict[str, str]] = {
    NotificationType.ACCESS_REQUEST_SUBMITTED: {
        "subject": "Access Request Submitted: {request_id}",
        "body": (
            "Your access request {request_id} has been submitted successfully.\n"
            "Requested roles: {roles}\n"
            "Estimated review time: {eta}\n\n"
            "You will be notified when a decision is made."
        ),
        "html_body": (
            "<p>Your access request <strong>{request_id}</strong> has been submitted.</p>"
            "<p>Requested roles: {roles}</p>"
            "<p>Estimated review time: {eta}</p>"
            "<p>You will be notified when a decision is made.</p>"
        ),
        "slack_message": (
            "*Access Request Submitted*\nRequest ID: `{request_id}`\n"
            "Roles: {roles}\nETA: {eta}"
        ),
    },
    NotificationType.APPROVAL_NEEDED: {
        "subject": "Action Required: Access Request {request_id} Awaits Your Approval",
        "body": (
            "An access request requires your approval.\n"
            "Request ID: {request_id}\n"
            "Requester: {requester_name}\n"
            "Roles requested: {roles}\n"
            "Risk level: {risk_level}\n\n"
            "Please review and approve or reject this request in GovernexPlus."
        ),
        "html_body": (
            "<p><strong>Action Required:</strong> An access request awaits your approval.</p>"
            "<ul>"
            "<li>Request ID: {request_id}</li>"
            "<li>Requester: {requester_name}</li>"
            "<li>Roles: {roles}</li>"
            "<li>Risk level: <strong>{risk_level}</strong></li>"
            "</ul>"
        ),
        "slack_message": (
            "*Approval Required*\nRequest `{request_id}` from {requester_name} "
            "needs your review.\nRisk: {risk_level}"
        ),
    },
    NotificationType.REQUEST_APPROVED: {
        "subject": "Access Request Approved: {request_id}",
        "body": (
            "Your access request {request_id} has been approved.\n"
            "Approved by: {approver_name}\n"
            "Provisioning will begin shortly."
        ),
        "html_body": (
            "<p>Your access request <strong>{request_id}</strong> has been "
            "<span style='color:green'>approved</span>.</p>"
            "<p>Approved by: {approver_name}</p>"
            "<p>Provisioning will begin shortly.</p>"
        ),
        "slack_message": (
            "*Request Approved* :white_check_mark:\n"
            "Request `{request_id}` approved by {approver_name}."
        ),
    },
    NotificationType.REQUEST_REJECTED: {
        "subject": "Access Request Rejected: {request_id}",
        "body": (
            "Your access request {request_id} has been rejected.\n"
            "Rejected by: {approver_name}\n"
            "Reason: {reason}\n\n"
            "Please contact your manager if you believe this is an error."
        ),
        "html_body": (
            "<p>Your access request <strong>{request_id}</strong> has been "
            "<span style='color:red'>rejected</span>.</p>"
            "<p>Rejected by: {approver_name}</p>"
            "<p>Reason: {reason}</p>"
        ),
        "slack_message": (
            "*Request Rejected* :x:\n"
            "Request `{request_id}` rejected by {approver_name}.\nReason: {reason}"
        ),
    },
    NotificationType.MITIGATION_EXPIRING: {
        "subject": "Mitigation Control Expiring: {control_name}",
        "body": (
            "Mitigation control '{control_name}' is expiring on {expiry_date}.\n"
            "Days remaining: {days_remaining}\n"
            "Violations covered: {violation_count}\n\n"
            "Please review and renew this control to maintain compliance."
        ),
        "html_body": (
            "<p>Mitigation control <strong>{control_name}</strong> expires on "
            "<strong>{expiry_date}</strong>.</p>"
            "<p>Days remaining: {days_remaining}</p>"
            "<p>Violations covered: {violation_count}</p>"
            "<p>Please renew this control to maintain compliance.</p>"
        ),
        "slack_message": (
            "*Mitigation Expiring* :warning:\n"
            "Control `{control_name}` expires on {expiry_date} ({days_remaining} days remaining)."
        ),
    },
    NotificationType.CERTIFICATION_DUE: {
        "subject": "Certification Review Due: {campaign_name}",
        "body": (
            "A certification review is due.\n"
            "Campaign: {campaign_name}\n"
            "Due date: {due_date}\n"
            "Items to review: {item_count}\n\n"
            "Please complete your review in GovernexPlus."
        ),
        "html_body": (
            "<p>Certification review due for campaign <strong>{campaign_name}</strong>.</p>"
            "<p>Due date: <strong>{due_date}</strong></p>"
            "<p>Items to review: {item_count}</p>"
        ),
        "slack_message": (
            "*Certification Due* :calendar:\n"
            "Campaign `{campaign_name}` due on {due_date}. {item_count} items to review."
        ),
    },
    NotificationType.FIREFIGHTER_USAGE: {
        "subject": "Firefighter Access Used: {ff_user} on {system}",
        "body": (
            "Firefighter (emergency) access was used.\n"
            "User: {ff_user}\n"
            "System: {system}\n"
            "Ticket: {ticket_id}\n"
            "Started: {start_time}\n\n"
            "This event has been logged for audit."
        ),
        "html_body": (
            "<p>Firefighter access activated.</p>"
            "<ul>"
            "<li>User: {ff_user}</li>"
            "<li>System: {system}</li>"
            "<li>Ticket: {ticket_id}</li>"
            "<li>Started: {start_time}</li>"
            "</ul>"
        ),
        "slack_message": (
            "*Firefighter Access* :fire:\n"
            "User `{ff_user}` activated emergency access on {system}. Ticket: {ticket_id}"
        ),
    },
    NotificationType.RISK_VIOLATION_DETECTED: {
        "subject": "Risk Violation Detected: {rule_name} for {user_id}",
        "body": (
            "A risk violation has been detected.\n"
            "Rule: {rule_name}\n"
            "User: {user_id}\n"
            "Risk level: {risk_level}\n"
            "Functions in conflict: {functions}\n\n"
            "Please review this violation in the Risk Dashboard."
        ),
        "html_body": (
            "<p><strong>Risk Violation Detected</strong></p>"
            "<ul>"
            "<li>Rule: {rule_name}</li>"
            "<li>User: {user_id}</li>"
            "<li>Risk level: <strong>{risk_level}</strong></li>"
            "<li>Functions in conflict: {functions}</li>"
            "</ul>"
        ),
        "slack_message": (
            "*Risk Violation* :rotating_light:\n"
            "Rule `{rule_name}` violated by {user_id}. Risk level: {risk_level}"
        ),
    },
    NotificationType.PASSWORD_EXPIRING: {
        "subject": "Password Expiring in {days_remaining} Days",
        "body": (
            "Your password will expire in {days_remaining} days ({expiry_date}).\n"
            "Systems affected: {systems}\n\n"
            "Please reset your password before the expiry date."
        ),
        "html_body": (
            "<p>Your password expires in <strong>{days_remaining} days</strong> "
            "({expiry_date}).</p>"
            "<p>Systems affected: {systems}</p>"
            "<p>Please reset before the expiry date.</p>"
        ),
        "slack_message": (
            "*Password Expiring* :key:\n"
            "Password expires in {days_remaining} days ({expiry_date}). Systems: {systems}"
        ),
    },
    NotificationType.SYNC_FAILED: {
        "subject": "System Sync Failed: {system_name}",
        "body": (
            "Synchronization with {system_name} failed.\n"
            "Error: {error_message}\n"
            "Failed at: {failed_at}\n"
            "Retry attempts: {retry_count}\n\n"
            "Please check the integration configuration."
        ),
        "html_body": (
            "<p>Sync with <strong>{system_name}</strong> failed.</p>"
            "<p>Error: {error_message}</p>"
            "<p>Failed at: {failed_at}</p>"
            "<p>Retry attempts: {retry_count}</p>"
        ),
        "slack_message": (
            "*Sync Failed* :x:\n"
            "Sync with `{system_name}` failed: {error_message}. Attempts: {retry_count}"
        ),
    },
}


def render_template(template: str, context: Dict[str, Any]) -> str:
    """Safely render a template string with context, leaving missing keys as-is."""
    try:
        return template.format_map({k: v for k, v in context.items()})
    except (KeyError, ValueError):
        return template


# ---------------------------------------------------------------------------
# SMTP client
# ---------------------------------------------------------------------------

class SMTPClient:
    """Thin wrapper around smtplib for sending emails."""

    def __init__(self) -> None:
        self.host = os.getenv("SMTP_HOST", "")
        self.port = int(os.getenv("SMTP_PORT", "587"))
        self.user = os.getenv("SMTP_USER", "")
        self.password = os.getenv("SMTP_PASSWORD", "")
        self.from_addr = os.getenv("SMTP_FROM", "noreply@governexplus.com")
        use_tls_raw = os.getenv("SMTP_USE_TLS", "true").lower()
        self.use_tls = use_tls_raw not in ("false", "0", "no")
        self.is_configured = bool(self.host and self.user and self.password)

    def send(self, payload: EmailPayload) -> Tuple[bool, Optional[str]]:
        """
        Send an email. Returns (success, error_message).
        If not configured, falls back to mock mode.
        """
        if not self.is_configured:
            logger.info(
                "smtp.mock_send",
                to=payload.to,
                subject=payload.subject,
                mock=True,
            )
            return True, None

        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = payload.subject
            msg["From"] = self.from_addr
            msg["To"] = ", ".join(payload.to)
            if payload.cc:
                msg["Cc"] = ", ".join(payload.cc)
            if payload.reply_to:
                msg["Reply-To"] = payload.reply_to

            msg.attach(MIMEText(payload.body, "plain", "utf-8"))
            if payload.html_body:
                msg.attach(MIMEText(payload.html_body, "html", "utf-8"))

            all_recipients = list(payload.to)
            if payload.cc:
                all_recipients.extend(payload.cc)

            context = ssl.create_default_context()
            with smtplib.SMTP(self.host, self.port, timeout=15) as server:
                if self.use_tls:
                    server.starttls(context=context)
                server.login(self.user, self.password)
                server.sendmail(self.from_addr, all_recipients, msg.as_string())

            logger.info("smtp.sent", to=payload.to, subject=payload.subject)
            return True, None

        except smtplib.SMTPAuthenticationError as exc:
            error = f"SMTP authentication failed: {exc}"
            logger.error("smtp.auth_error", error=error)
            return False, error
        except smtplib.SMTPException as exc:
            error = f"SMTP error: {exc}"
            logger.error("smtp.error", error=error)
            return False, error
        except OSError as exc:
            error = f"Network error sending email: {exc}"
            logger.error("smtp.network_error", error=error)
            return False, error


# ---------------------------------------------------------------------------
# Slack client
# ---------------------------------------------------------------------------

class SlackClient:
    """Posts messages via Slack Incoming Webhook or Web API."""

    def __init__(self) -> None:
        self.webhook_url = os.getenv("SLACK_WEBHOOK_URL", "")
        self.bot_token = os.getenv("SLACK_BOT_TOKEN", "")
        self.default_channel = os.getenv("SLACK_DEFAULT_CHANNEL", "#grc-alerts")
        self.is_configured = bool(self.webhook_url or self.bot_token)

    def send(self, payload: SlackPayload) -> Tuple[bool, Optional[str]]:
        """
        Send a Slack message. Prefers webhook over Bot API if both are set.
        Returns (success, error_message).
        """
        if not self.is_configured:
            logger.info(
                "slack.mock_send",
                channel=payload.channel,
                message=payload.message[:120],
                mock=True,
            )
            return True, None

        if self.webhook_url:
            return self._send_webhook(payload)
        return self._send_api(payload)

    def _build_body(self, payload: SlackPayload) -> Dict[str, Any]:
        body: Dict[str, Any] = {
            "text": payload.message,
            "username": payload.username,
            "icon_emoji": payload.icon_emoji,
        }
        if payload.blocks:
            body["blocks"] = payload.blocks
        return body

    def _send_webhook(self, payload: SlackPayload) -> Tuple[bool, Optional[str]]:
        body = self._build_body(payload)
        try:
            data = json.dumps(body).encode("utf-8")
            req = HTTPRequest(
                self.webhook_url,
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urlopen(req, timeout=10) as resp:
                if resp.status == 200:
                    logger.info("slack.webhook_sent", channel=payload.channel)
                    return True, None
                error = f"Slack webhook returned HTTP {resp.status}"
                logger.error("slack.webhook_error", error=error)
                return False, error
        except (URLError, HTTPError) as exc:
            error = f"Slack webhook request failed: {exc}"
            logger.error("slack.webhook_error", error=error)
            return False, error

    def _send_api(self, payload: SlackPayload) -> Tuple[bool, Optional[str]]:
        body = self._build_body(payload)
        body["channel"] = payload.channel or self.default_channel
        try:
            data = json.dumps(body).encode("utf-8")
            req = HTTPRequest(
                "https://slack.com/api/chat.postMessage",
                data=data,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.bot_token}",
                },
                method="POST",
            )
            with urlopen(req, timeout=10) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                if result.get("ok"):
                    logger.info("slack.api_sent", channel=payload.channel)
                    return True, None
                error = f"Slack API error: {result.get('error', 'unknown')}"
                logger.error("slack.api_error", error=error)
                return False, error
        except (URLError, HTTPError, json.JSONDecodeError) as exc:
            error = f"Slack API request failed: {exc}"
            logger.error("slack.api_error", error=error)
            return False, error


# ---------------------------------------------------------------------------
# Delivery Engine
# ---------------------------------------------------------------------------

_MAX_RETRY_ATTEMPTS = 3


def _get_tenant_id() -> str:
    """Return the active tenant_id from the request context, or the default."""
    ctx = get_current_tenant()
    if ctx is not None:
        return ctx.tenant_id
    return os.getenv("DEFAULT_TENANT_ID", "tenant_default")


class NotificationDeliveryEngine:
    """
    Routes notifications to the correct channel (email / Slack) and
    tracks every delivery attempt.
    """

    def __init__(self) -> None:
        self._smtp = SMTPClient()
        self._slack = SlackClient()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def send_email(
        self,
        to: List[str],
        subject: str,
        body: str,
        html_body: Optional[str] = None,
        cc: Optional[List[str]] = None,
    ) -> DeliveryRecord:
        """Send an email immediately and return a delivery record."""
        payload = EmailPayload(to=to, subject=subject, body=body, html_body=html_body, cc=cc)
        record = DeliveryRecord(
            channel=DeliveryChannel.EMAIL.value,
            payload_summary=f"to={','.join(to)} subject={subject[:60]}",
        )
        success, error = self._smtp.send(payload)
        self._finalise_record(record, success, error)
        return record

    def send_slack(
        self,
        channel: str,
        message: str,
        blocks: Optional[List[Dict[str, Any]]] = None,
    ) -> DeliveryRecord:
        """Send a Slack message immediately and return a delivery record."""
        payload = SlackPayload(channel=channel, message=message, blocks=blocks)
        record = DeliveryRecord(
            channel=DeliveryChannel.SLACK.value,
            payload_summary=f"channel={channel} msg={message[:60]}",
        )
        success, error = self._slack.send(payload)
        self._finalise_record(record, success, error)
        return record

    def send_notification(self, notification: Notification) -> List[DeliveryRecord]:
        """
        Route a Notification to all of its configured delivery channels.
        Templates are applied automatically from _TEMPLATES.
        Returns one DeliveryRecord per channel attempt.
        """
        tmpl = _TEMPLATES.get(notification.notification_type, {})
        ctx = notification.context

        subject = render_template(tmpl.get("subject", notification.subject), ctx)
        body = render_template(tmpl.get("body", notification.body), ctx)
        html_body = render_template(tmpl.get("html_body", ""), ctx) or None
        slack_msg = render_template(tmpl.get("slack_message", notification.body), ctx)

        records: List[DeliveryRecord] = []

        for ch in notification.channels:
            if ch == DeliveryChannel.EMAIL:
                if not notification.recipient_email:
                    logger.warning(
                        "delivery.skip_email",
                        notification_id=notification.notification_id,
                        reason="no recipient_email",
                    )
                    continue
                record = self.send_email(
                    to=[notification.recipient_email],
                    subject=subject,
                    body=body,
                    html_body=html_body,
                )

            elif ch == DeliveryChannel.SLACK:
                channel = (
                    notification.recipient_slack_channel
                    or self._slack.default_channel
                )
                record = self.send_slack(channel=channel, message=slack_msg)

            else:
                logger.warning(
                    "delivery.unsupported_channel",
                    channel=ch,
                    notification_id=notification.notification_id,
                )
                continue

            record.notification_id = notification.notification_id
            record.notification_type = notification.notification_type.value
            record.recipient_id = notification.recipient_id
            record.recipient_email = notification.recipient_email
            record.recipient_slack_channel = notification.recipient_slack_channel
            self._store_record(record)
            records.append(record)

        return records

    def send_bulk(self, notifications: List[Notification]) -> Dict[str, List[DeliveryRecord]]:
        """
        Send multiple notifications. Returns a mapping of notification_id to
        the list of DeliveryRecords produced for that notification.
        """
        results: Dict[str, List[DeliveryRecord]] = {}
        for notification in notifications:
            records = self.send_notification(notification)
            results[notification.notification_id] = records
        logger.info("delivery.bulk_complete", count=len(notifications))
        return results

    def get_delivery_status(self, notification_id: str) -> Optional[Dict[str, Any]]:
        """Return all delivery records for a given notification_id, queried from DB."""
        tenant_id = _get_tenant_id()
        with db_manager.session_scope() as session:
            rows = (
                session.query(NotificationRecordModel)
                .filter(
                    NotificationRecordModel.tenant_id == tenant_id,
                    NotificationRecordModel.notification_id == notification_id,
                )
                .all()
            )
            if not rows:
                return None
            records_data = [row.to_dict() for row in rows]
            statuses = {row.status for row in rows}

        if all(s == DeliveryStatus.SENT.value for s in statuses):
            overall = "delivered"
        elif any(s == DeliveryStatus.FAILED.value for s in statuses):
            overall = "partial_failure"
        else:
            overall = "pending"

        return {
            "notification_id": notification_id,
            "records": records_data,
            "overall_status": overall,
        }

    def get_delivery_history(
        self,
        user_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Return delivery history from DB, optionally filtered by recipient_id.
        Most recent first.
        """
        tenant_id = _get_tenant_id()
        with db_manager.session_scope() as session:
            query = session.query(NotificationRecordModel).filter(
                NotificationRecordModel.tenant_id == tenant_id,
            )
            if user_id:
                query = query.filter(
                    NotificationRecordModel.recipient_id == user_id,
                )
            rows = (
                query
                .order_by(NotificationRecordModel.id.desc())
                .limit(limit)
                .all()
            )
            return [row.to_dict() for row in rows]

    def retry_failed(self) -> Dict[str, Any]:
        """
        Re-attempt delivery for all DB rows in FAILED status that have
        not exceeded the maximum retry limit. Updates each row in-place.
        Returns a summary.
        """
        tenant_id = _get_tenant_id()
        retried = 0
        still_failed = 0
        total_processed = 0

        with db_manager.session_scope() as session:
            failed_rows = (
                session.query(NotificationRecordModel)
                .filter(
                    NotificationRecordModel.tenant_id == tenant_id,
                    NotificationRecordModel.status == DeliveryStatus.FAILED.value,
                    NotificationRecordModel.retry_count < _MAX_RETRY_ATTEMPTS,
                )
                .all()
            )
            total_processed = len(failed_rows)

            for row in failed_rows:
                row.status = DeliveryStatus.RETRYING.value
                row.retry_count = (row.retry_count or 0) + 1

                # Re-send based on channel using stored recipient fields
                if row.channel == DeliveryChannel.EMAIL.value:
                    to_addr = row.recipient_email or "admin@governexplus.com"
                    success, error = self._smtp.send(
                        EmailPayload(
                            to=[to_addr],
                            subject=row.subject or f"Retry: notification {row.notification_id}",
                            body=row.body or (
                                f"Retry attempt {row.retry_count} for notification "
                                f"{row.notification_id}."
                            ),
                        )
                    )
                else:
                    channel = row.recipient_slack_channel or self._slack.default_channel
                    success, error = self._slack.send(
                        SlackPayload(
                            channel=channel,
                            message=(
                                f"Retry attempt {row.retry_count} for notification "
                                f"`{row.notification_id}`."
                            ),
                        )
                    )

                now = datetime.utcnow()
                if success:
                    row.status = DeliveryStatus.SENT.value
                    row.sent_at = now
                    row.error_message = None
                    retried += 1
                else:
                    row.status = DeliveryStatus.FAILED.value
                    row.error_message = error
                    still_failed += 1

            # session_scope auto-commits on exit

        logger.info("delivery.retry_run", retried=retried, still_failed=still_failed)
        return {
            "retried": retried,
            "still_failed": still_failed,
            "total_processed": total_processed,
        }

    # ------------------------------------------------------------------
    # Template helpers
    # ------------------------------------------------------------------

    def get_templates(self) -> List[Dict[str, Any]]:
        """Return metadata for all built-in notification templates."""
        result = []
        for ntype, tmpl in _TEMPLATES.items():
            result.append(
                {
                    "notification_type": ntype.value,
                    "subject_template": tmpl.get("subject", ""),
                    "body_template": tmpl.get("body", ""),
                    "has_html": bool(tmpl.get("html_body")),
                    "has_slack": bool(tmpl.get("slack_message")),
                }
            )
        return result

    # ------------------------------------------------------------------
    # User preferences (DB-backed)
    # ------------------------------------------------------------------

    def get_preferences(self, user_id: str) -> Dict[str, Any]:
        """Return channel/type preferences for a user from DB, or safe defaults."""
        tenant_id = _get_tenant_id()
        with db_manager.session_scope() as session:
            row = (
                session.query(NotificationPreferenceModel)
                .filter(
                    NotificationPreferenceModel.tenant_id == tenant_id,
                    NotificationPreferenceModel.user_id == user_id,
                )
                .first()
            )
            if row is not None:
                return row.to_dict()

        # No row found — return defaults (not persisted until set_preferences is called)
        return {
            "user_id": user_id,
            "email_enabled": True,
            "slack_enabled": False,
            "slack_channel": None,
            "disabled_types": [],
            "tenant_id": tenant_id,
        }

    def set_preferences(self, user_id: str, prefs: Dict[str, Any]) -> Dict[str, Any]:
        """Upsert channel/type preferences for a user into the DB."""
        tenant_id = _get_tenant_id()
        with db_manager.session_scope() as session:
            row = (
                session.query(NotificationPreferenceModel)
                .filter(
                    NotificationPreferenceModel.tenant_id == tenant_id,
                    NotificationPreferenceModel.user_id == user_id,
                )
                .first()
            )
            if row is None:
                row = NotificationPreferenceModel(
                    tenant_id=tenant_id,
                    user_id=user_id,
                )
                session.add(row)

            row.email_enabled = bool(prefs.get("email_enabled", True))
            row.slack_enabled = bool(prefs.get("slack_enabled", False))
            row.slack_channel = prefs.get("slack_channel")
            row.disabled_types = prefs.get("disabled_types", [])
            # session_scope auto-commits; capture dict before session closes
            result = {
                "user_id": user_id,
                "email_enabled": row.email_enabled,
                "slack_enabled": row.slack_enabled,
                "slack_channel": row.slack_channel,
                "disabled_types": row.disabled_types,
                "tenant_id": tenant_id,
            }

        logger.info("delivery.preferences_updated", user_id=user_id)
        return result

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _finalise_record(
        record: DeliveryRecord,
        success: bool,
        error: Optional[str],
    ) -> None:
        now = datetime.utcnow()
        record.last_attempt_at = now
        record.attempts += 1
        if success:
            record.status = DeliveryStatus.SENT
            record.sent_at = now
            record.error_message = None
        else:
            record.status = DeliveryStatus.FAILED
            record.error_message = error

    @staticmethod
    def _store_record(record: DeliveryRecord) -> None:
        """Persist a DeliveryRecord to the notification_records table."""
        tenant_id = _get_tenant_id()
        try:
            with db_manager.session_scope() as session:
                db_row = NotificationRecordModel(
                    tenant_id=tenant_id,
                    notification_id=record.notification_id or record.record_id,
                    notification_type=record.notification_type,
                    recipient_id=record.recipient_id,
                    recipient_email=record.recipient_email,
                    recipient_slack_channel=record.recipient_slack_channel,
                    channel=record.channel,
                    status=record.status.value if isinstance(record.status, DeliveryStatus) else record.status,
                    subject=record.payload_summary,
                    body=None,
                    context=None,
                    sent_at=record.sent_at,
                    delivered_at=record.sent_at,
                    retry_count=record.attempts,
                    error_message=record.error_message,
                )
                session.add(db_row)
        except Exception as exc:  # pragma: no cover
            logger.error("delivery.store_record_error", error=str(exc), record_id=record.record_id)

# Module-level singleton
_engine: Optional[NotificationDeliveryEngine] = None


def get_delivery_engine() -> NotificationDeliveryEngine:
    """Return the module-level delivery engine singleton."""
    global _engine
    if _engine is None:
        _engine = NotificationDeliveryEngine()
    return _engine
