"""
Notification Service

Handles all notifications across the GRC platform including:
- Email notifications
- In-app notifications
- Workflow alerts
- Escalation reminders
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Callable
from datetime import datetime, timedelta
from enum import Enum
import uuid


class NotificationType(Enum):
    """Types of notifications"""
    # Access Requests
    REQUEST_SUBMITTED = "request_submitted"
    REQUEST_APPROVED = "request_approved"
    REQUEST_REJECTED = "request_rejected"
    REQUEST_PENDING_APPROVAL = "request_pending_approval"
    REQUEST_PROVISIONED = "request_provisioned"
    REQUEST_REMINDER = "request_reminder"
    REQUEST_ESCALATED = "request_escalated"

    # Firefighter/EAM
    FF_SESSION_STARTED = "ff_session_started"
    FF_SESSION_ENDING = "ff_session_ending"
    FF_SESSION_ENDED = "ff_session_ended"
    FF_REVIEW_REQUIRED = "ff_review_required"
    FF_SENSITIVE_ACTION = "ff_sensitive_action"

    # Certification
    CERT_CAMPAIGN_STARTED = "cert_campaign_started"
    CERT_REVIEW_ASSIGNED = "cert_review_assigned"
    CERT_REMINDER = "cert_reminder"
    CERT_OVERDUE = "cert_overdue"
    CERT_COMPLETED = "cert_completed"

    # Risk Alerts
    RISK_VIOLATION_DETECTED = "risk_violation_detected"
    RISK_CRITICAL_ACCESS = "risk_critical_access"
    RISK_MITIGATION_EXPIRING = "risk_mitigation_expiring"

    # System
    SYSTEM_ALERT = "system_alert"
    SYNC_COMPLETED = "sync_completed"
    SYNC_FAILED = "sync_failed"


class NotificationChannel(Enum):
    """Notification delivery channels"""
    EMAIL = "email"
    IN_APP = "in_app"
    SMS = "sms"
    TEAMS = "teams"
    SLACK = "slack"
    WEBHOOK = "webhook"


class NotificationPriority(Enum):
    """Notification priority levels"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


@dataclass
class NotificationTemplate:
    """Template for generating notifications"""
    template_id: str
    notification_type: NotificationType
    name: str
    subject_template: str
    body_template: str
    channels: List[NotificationChannel] = field(default_factory=list)
    is_active: bool = True

    def render(self, context: Dict) -> Dict:
        """Render template with context variables"""
        subject = self.subject_template
        body = self.body_template

        for key, value in context.items():
            placeholder = f"{{{{{key}}}}}"
            subject = subject.replace(placeholder, str(value))
            body = body.replace(placeholder, str(value))

        return {
            "subject": subject,
            "body": body
        }


@dataclass
class Notification:
    """Individual notification instance"""
    notification_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    notification_type: NotificationType = NotificationType.SYSTEM_ALERT

    # Recipients
    recipient_user_id: str = ""
    recipient_email: str = ""
    recipient_name: str = ""

    # Content
    subject: str = ""
    body: str = ""
    body_html: Optional[str] = None

    # Context
    context: Dict = field(default_factory=dict)
    reference_type: str = ""  # request, session, campaign, etc.
    reference_id: str = ""

    # Delivery
    channels: List[NotificationChannel] = field(default_factory=lambda: [NotificationChannel.IN_APP])
    priority: NotificationPriority = NotificationPriority.NORMAL

    # Status
    is_read: bool = False
    read_at: Optional[datetime] = None
    is_sent: bool = False
    sent_at: Optional[datetime] = None
    delivery_status: Dict[str, str] = field(default_factory=dict)  # channel -> status

    # Timing
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None

    # Actions
    action_url: Optional[str] = None
    action_label: Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            "notification_id": self.notification_id,
            "notification_type": self.notification_type.value,
            "recipient_user_id": self.recipient_user_id,
            "recipient_email": self.recipient_email,
            "subject": self.subject,
            "body": self.body,
            "reference_type": self.reference_type,
            "reference_id": self.reference_id,
            "channels": [c.value for c in self.channels],
            "priority": self.priority.value,
            "is_read": self.is_read,
            "read_at": self.read_at.isoformat() if self.read_at else None,
            "is_sent": self.is_sent,
            "sent_at": self.sent_at.isoformat() if self.sent_at else None,
            "created_at": self.created_at.isoformat(),
            "action_url": self.action_url,
            "action_label": self.action_label
        }


@dataclass
class NotificationPreference:
    """User notification preferences"""
    user_id: str
    preferences: Dict[str, Dict] = field(default_factory=dict)  # type -> {channels, enabled}

    def get_channels(self, notification_type: NotificationType) -> List[NotificationChannel]:
        """Get enabled channels for a notification type"""
        type_key = notification_type.value
        if type_key in self.preferences:
            pref = self.preferences[type_key]
            if pref.get("enabled", True):
                return [NotificationChannel(c) for c in pref.get("channels", ["in_app"])]
        return [NotificationChannel.IN_APP]  # Default

    def is_enabled(self, notification_type: NotificationType) -> bool:
        """Check if notification type is enabled"""
        type_key = notification_type.value
        if type_key in self.preferences:
            return self.preferences[type_key].get("enabled", True)
        return True


class NotificationService:
    """
    Central notification service for the GRC platform.
    Provides zero-training experience with smart defaults.
    """

    def __init__(self):
        self.notifications: Dict[str, Notification] = {}
        self.templates: Dict[str, NotificationTemplate] = {}
        self.preferences: Dict[str, NotificationPreference] = {}
        self.user_notifications: Dict[str, List[str]] = {}  # user_id -> notification_ids

        # Email configuration (would be loaded from settings)
        self.email_config = {
            "smtp_host": "smtp.company.com",
            "smtp_port": 587,
            "from_address": "grc-notifications@company.com",
            "from_name": "GRC Platform"
        }

        self._init_templates()

    def _init_templates(self):
        """Initialize default notification templates"""
        templates = [
            # Access Request Templates
            NotificationTemplate(
                template_id="req_pending",
                notification_type=NotificationType.REQUEST_PENDING_APPROVAL,
                name="Access Request Pending Approval",
                subject_template="Action Required: Access Request {{request_id}} needs your approval",
                body_template="""
Hello {{approver_name}},

A new access request requires your approval:

Request ID: {{request_id}}
Requester: {{requester_name}}
For User: {{target_user_name}}
Roles Requested: {{roles}}
Risk Level: {{risk_level}}
Business Justification: {{justification}}

Please review and take action.

[Approve] [Reject] [View Details]
                """.strip(),
                channels=[NotificationChannel.EMAIL, NotificationChannel.IN_APP]
            ),
            NotificationTemplate(
                template_id="req_approved",
                notification_type=NotificationType.REQUEST_APPROVED,
                name="Access Request Approved",
                subject_template="Your Access Request {{request_id}} has been approved",
                body_template="""
Hello {{requester_name}},

Great news! Your access request has been approved.

Request ID: {{request_id}}
For User: {{target_user_name}}
Roles Granted: {{roles}}
Approved By: {{approver_name}}

Access will be provisioned shortly.
                """.strip(),
                channels=[NotificationChannel.EMAIL, NotificationChannel.IN_APP]
            ),
            NotificationTemplate(
                template_id="req_rejected",
                notification_type=NotificationType.REQUEST_REJECTED,
                name="Access Request Rejected",
                subject_template="Your Access Request {{request_id}} has been rejected",
                body_template="""
Hello {{requester_name}},

Unfortunately, your access request has been rejected.

Request ID: {{request_id}}
For User: {{target_user_name}}
Rejected By: {{approver_name}}
Reason: {{rejection_reason}}

If you have questions, please contact your manager or the security team.
                """.strip(),
                channels=[NotificationChannel.EMAIL, NotificationChannel.IN_APP]
            ),
            NotificationTemplate(
                template_id="req_reminder",
                notification_type=NotificationType.REQUEST_REMINDER,
                name="Access Request Reminder",
                subject_template="Reminder: Access Request {{request_id}} awaiting your approval",
                body_template="""
Hello {{approver_name}},

This is a reminder that the following access request is still awaiting your approval:

Request ID: {{request_id}}
Requester: {{requester_name}}
Submitted: {{submitted_date}}
Days Pending: {{days_pending}}

Please review and take action to avoid SLA breach.
                """.strip(),
                channels=[NotificationChannel.EMAIL, NotificationChannel.IN_APP]
            ),

            # Firefighter Templates
            NotificationTemplate(
                template_id="ff_started",
                notification_type=NotificationType.FF_SESSION_STARTED,
                name="Firefighter Session Started",
                subject_template="Alert: Firefighter Session Started - {{session_id}}",
                body_template="""
A firefighter session has been started:

Session ID: {{session_id}}
User: {{user_name}} ({{user_id}})
Firefighter ID: {{firefighter_id}}
System: {{system}}
Reason: {{reason}}
Duration: {{duration}} minutes
Started At: {{start_time}}

All activities will be logged for review.
                """.strip(),
                channels=[NotificationChannel.EMAIL, NotificationChannel.IN_APP]
            ),
            NotificationTemplate(
                template_id="ff_ending",
                notification_type=NotificationType.FF_SESSION_ENDING,
                name="Firefighter Session Ending Soon",
                subject_template="Warning: Firefighter Session {{session_id}} ending in {{minutes}} minutes",
                body_template="""
Your firefighter session is ending soon:

Session ID: {{session_id}}
Time Remaining: {{minutes}} minutes
End Time: {{end_time}}

Please complete your work and log out. Session will auto-terminate at the scheduled time.
                """.strip(),
                channels=[NotificationChannel.EMAIL, NotificationChannel.IN_APP]
            ),
            NotificationTemplate(
                template_id="ff_review",
                notification_type=NotificationType.FF_REVIEW_REQUIRED,
                name="Firefighter Log Review Required",
                subject_template="Action Required: Review Firefighter Session {{session_id}}",
                body_template="""
Hello {{controller_name}},

A firefighter session has ended and requires your review:

Session ID: {{session_id}}
User: {{user_name}}
System: {{system}}
Duration: {{duration}} minutes
Activities Logged: {{activity_count}}
Sensitive Actions: {{sensitive_count}}

Please review the activity log and mark as reviewed.

[Review Now]
                """.strip(),
                channels=[NotificationChannel.EMAIL, NotificationChannel.IN_APP]
            ),

            # Certification Templates
            NotificationTemplate(
                template_id="cert_assigned",
                notification_type=NotificationType.CERT_REVIEW_ASSIGNED,
                name="Certification Review Assigned",
                subject_template="Action Required: Access Certification Review - {{campaign_name}}",
                body_template="""
Hello {{reviewer_name}},

You have been assigned access certification reviews:

Campaign: {{campaign_name}}
Items to Review: {{item_count}}
Due Date: {{due_date}}

Please review each user's access and certify or revoke as appropriate.

[Start Review]
                """.strip(),
                channels=[NotificationChannel.EMAIL, NotificationChannel.IN_APP]
            ),
            NotificationTemplate(
                template_id="cert_reminder",
                notification_type=NotificationType.CERT_REMINDER,
                name="Certification Review Reminder",
                subject_template="Reminder: {{remaining}} certification reviews due by {{due_date}}",
                body_template="""
Hello {{reviewer_name}},

You have outstanding certification reviews:

Campaign: {{campaign_name}}
Remaining Items: {{remaining}}
Due Date: {{due_date}}
Days Remaining: {{days_remaining}}

Please complete your reviews before the deadline.

[Continue Review]
                """.strip(),
                channels=[NotificationChannel.EMAIL, NotificationChannel.IN_APP]
            ),

            # Risk Alert Templates
            NotificationTemplate(
                template_id="risk_violation",
                notification_type=NotificationType.RISK_VIOLATION_DETECTED,
                name="SoD Violation Detected",
                subject_template="Risk Alert: SoD Violation Detected for {{user_name}}",
                body_template="""
A Segregation of Duties violation has been detected:

User: {{user_name}} ({{user_id}})
Risk ID: {{risk_id}}
Risk Level: {{risk_level}}
Conflicting Functions:
- {{function_1}}
- {{function_2}}

Description: {{description}}

Recommendation: {{recommendation}}

[View Details] [Assign Mitigation]
                """.strip(),
                channels=[NotificationChannel.EMAIL, NotificationChannel.IN_APP]
            ),
            NotificationTemplate(
                template_id="risk_mitigation_expiring",
                notification_type=NotificationType.RISK_MITIGATION_EXPIRING,
                name="Mitigation Control Expiring",
                subject_template="Alert: Mitigation Control Expiring - {{control_name}}",
                body_template="""
A mitigation control is expiring soon:

Control: {{control_name}}
Control ID: {{control_id}}
Assigned To: {{user_name}}
Risk: {{risk_name}}
Expires: {{expiry_date}}

Please review and renew the mitigation or remediate the underlying risk.

[Renew Control] [View Risk]
                """.strip(),
                channels=[NotificationChannel.EMAIL, NotificationChannel.IN_APP]
            ),
        ]

        for template in templates:
            self.templates[template.template_id] = template

    # =========================================================================
    # Core Notification Methods
    # =========================================================================

    def send(
        self,
        notification_type: NotificationType,
        recipient_user_id: str,
        recipient_email: str,
        recipient_name: str,
        context: Dict,
        reference_type: str = "",
        reference_id: str = "",
        priority: NotificationPriority = NotificationPriority.NORMAL,
        channels: Optional[List[NotificationChannel]] = None
    ) -> Notification:
        """Send a notification using the appropriate template"""

        # Find template for this notification type
        template = self._get_template_for_type(notification_type)

        # Get user preferences
        user_channels = channels
        if not user_channels:
            pref = self.preferences.get(recipient_user_id)
            if pref:
                user_channels = pref.get_channels(notification_type)
            else:
                user_channels = template.channels if template else [NotificationChannel.IN_APP]

        # Render content
        if template:
            rendered = template.render(context)
            subject = rendered["subject"]
            body = rendered["body"]
        else:
            subject = context.get("subject", "Notification")
            body = context.get("body", "")

        # Create notification
        notification = Notification(
            notification_type=notification_type,
            recipient_user_id=recipient_user_id,
            recipient_email=recipient_email,
            recipient_name=recipient_name,
            subject=subject,
            body=body,
            context=context,
            reference_type=reference_type,
            reference_id=reference_id,
            channels=user_channels,
            priority=priority,
            action_url=context.get("action_url"),
            action_label=context.get("action_label")
        )

        # Store notification
        self.notifications[notification.notification_id] = notification

        # Index by user
        if recipient_user_id not in self.user_notifications:
            self.user_notifications[recipient_user_id] = []
        self.user_notifications[recipient_user_id].append(notification.notification_id)

        # Deliver through channels
        self._deliver(notification)

        return notification

    def _get_template_for_type(self, notification_type: NotificationType) -> Optional[NotificationTemplate]:
        """Get template for notification type"""
        for template in self.templates.values():
            if template.notification_type == notification_type and template.is_active:
                return template
        return None

    def _deliver(self, notification: Notification):
        """Deliver notification through configured channels"""
        for channel in notification.channels:
            try:
                if channel == NotificationChannel.EMAIL:
                    self._send_email(notification)
                elif channel == NotificationChannel.IN_APP:
                    # Already stored, just mark as sent
                    pass
                elif channel == NotificationChannel.TEAMS:
                    self._send_teams(notification)
                elif channel == NotificationChannel.SLACK:
                    self._send_slack(notification)
                elif channel == NotificationChannel.WEBHOOK:
                    self._send_webhook(notification)

                notification.delivery_status[channel.value] = "sent"
            except Exception as e:
                notification.delivery_status[channel.value] = f"failed: {str(e)}"

        notification.is_sent = True
        notification.sent_at = datetime.now()

    def _send_email(self, notification: Notification):
        """Send email notification (stub - would use SMTP/SendGrid/etc.)"""
        # In production, this would send actual email
        # For now, just log the intent
        print(f"[EMAIL] To: {notification.recipient_email}")
        print(f"[EMAIL] Subject: {notification.subject}")

    def _send_teams(self, notification: Notification):
        """Send Microsoft Teams notification"""
        # Would integrate with Teams webhook
        pass

    def _send_slack(self, notification: Notification):
        """Send Slack notification"""
        # Would integrate with Slack API
        pass

    def _send_webhook(self, notification: Notification):
        """Send webhook notification"""
        # Would POST to configured webhook URL
        pass

    # =========================================================================
    # User Notification Methods
    # =========================================================================

    def get_user_notifications(
        self,
        user_id: str,
        unread_only: bool = False,
        notification_type: Optional[NotificationType] = None,
        limit: int = 50
    ) -> List[Notification]:
        """Get notifications for a user"""
        notification_ids = self.user_notifications.get(user_id, [])
        notifications = []

        for nid in reversed(notification_ids):  # Most recent first
            n = self.notifications.get(nid)
            if not n:
                continue
            if unread_only and n.is_read:
                continue
            if notification_type and n.notification_type != notification_type:
                continue
            notifications.append(n)
            if len(notifications) >= limit:
                break

        return notifications

    def get_unread_count(self, user_id: str) -> int:
        """Get count of unread notifications"""
        notification_ids = self.user_notifications.get(user_id, [])
        return sum(1 for nid in notification_ids
                   if nid in self.notifications and not self.notifications[nid].is_read)

    def mark_as_read(self, notification_id: str) -> bool:
        """Mark notification as read"""
        if notification_id in self.notifications:
            self.notifications[notification_id].is_read = True
            self.notifications[notification_id].read_at = datetime.now()
            return True
        return False

    def mark_all_as_read(self, user_id: str) -> int:
        """Mark all notifications as read for a user"""
        count = 0
        notification_ids = self.user_notifications.get(user_id, [])
        for nid in notification_ids:
            if nid in self.notifications and not self.notifications[nid].is_read:
                self.notifications[nid].is_read = True
                self.notifications[nid].read_at = datetime.now()
                count += 1
        return count

    # =========================================================================
    # Preference Management
    # =========================================================================

    def get_preferences(self, user_id: str) -> NotificationPreference:
        """Get user notification preferences"""
        if user_id not in self.preferences:
            self.preferences[user_id] = NotificationPreference(user_id=user_id)
        return self.preferences[user_id]

    def update_preferences(self, user_id: str, preferences: Dict) -> NotificationPreference:
        """Update user notification preferences"""
        pref = self.get_preferences(user_id)
        pref.preferences.update(preferences)
        return pref

    # =========================================================================
    # Template Management
    # =========================================================================

    def get_templates(self) -> List[NotificationTemplate]:
        """Get all notification templates"""
        return list(self.templates.values())

    def update_template(
        self,
        template_id: str,
        subject_template: Optional[str] = None,
        body_template: Optional[str] = None,
        channels: Optional[List[NotificationChannel]] = None,
        is_active: Optional[bool] = None
    ) -> Optional[NotificationTemplate]:
        """Update a notification template"""
        if template_id not in self.templates:
            return None

        template = self.templates[template_id]
        if subject_template:
            template.subject_template = subject_template
        if body_template:
            template.body_template = body_template
        if channels:
            template.channels = channels
        if is_active is not None:
            template.is_active = is_active

        return template

    # =========================================================================
    # Convenience Methods for Common Notifications
    # =========================================================================

    def notify_approval_required(
        self,
        approver_id: str,
        approver_email: str,
        approver_name: str,
        request_id: str,
        requester_name: str,
        target_user_name: str,
        roles: List[str],
        risk_level: str,
        justification: str
    ):
        """Send approval required notification"""
        return self.send(
            notification_type=NotificationType.REQUEST_PENDING_APPROVAL,
            recipient_user_id=approver_id,
            recipient_email=approver_email,
            recipient_name=approver_name,
            context={
                "request_id": request_id,
                "approver_name": approver_name,
                "requester_name": requester_name,
                "target_user_name": target_user_name,
                "roles": ", ".join(roles),
                "risk_level": risk_level,
                "justification": justification,
                "action_url": f"/access-requests/{request_id}",
                "action_label": "Review Request"
            },
            reference_type="access_request",
            reference_id=request_id,
            priority=NotificationPriority.HIGH if risk_level in ["high", "critical"] else NotificationPriority.NORMAL
        )

    def notify_request_approved(
        self,
        requester_id: str,
        requester_email: str,
        requester_name: str,
        request_id: str,
        target_user_name: str,
        roles: List[str],
        approver_name: str
    ):
        """Send request approved notification"""
        return self.send(
            notification_type=NotificationType.REQUEST_APPROVED,
            recipient_user_id=requester_id,
            recipient_email=requester_email,
            recipient_name=requester_name,
            context={
                "request_id": request_id,
                "requester_name": requester_name,
                "target_user_name": target_user_name,
                "roles": ", ".join(roles),
                "approver_name": approver_name
            },
            reference_type="access_request",
            reference_id=request_id
        )

    def notify_ff_session_started(
        self,
        controller_id: str,
        controller_email: str,
        controller_name: str,
        session_id: str,
        user_id: str,
        user_name: str,
        firefighter_id: str,
        system: str,
        reason: str,
        duration: int
    ):
        """Send firefighter session started notification"""
        return self.send(
            notification_type=NotificationType.FF_SESSION_STARTED,
            recipient_user_id=controller_id,
            recipient_email=controller_email,
            recipient_name=controller_name,
            context={
                "session_id": session_id,
                "user_id": user_id,
                "user_name": user_name,
                "firefighter_id": firefighter_id,
                "system": system,
                "reason": reason,
                "duration": duration,
                "start_time": datetime.now().strftime("%Y-%m-%d %H:%M")
            },
            reference_type="ff_session",
            reference_id=session_id,
            priority=NotificationPriority.HIGH
        )

    def notify_certification_assigned(
        self,
        reviewer_id: str,
        reviewer_email: str,
        reviewer_name: str,
        campaign_id: str,
        campaign_name: str,
        item_count: int,
        due_date: str
    ):
        """Send certification review assigned notification"""
        return self.send(
            notification_type=NotificationType.CERT_REVIEW_ASSIGNED,
            recipient_user_id=reviewer_id,
            recipient_email=reviewer_email,
            recipient_name=reviewer_name,
            context={
                "campaign_id": campaign_id,
                "campaign_name": campaign_name,
                "reviewer_name": reviewer_name,
                "item_count": item_count,
                "due_date": due_date,
                "action_url": f"/certification/campaigns/{campaign_id}",
                "action_label": "Start Review"
            },
            reference_type="certification",
            reference_id=campaign_id,
            priority=NotificationPriority.HIGH
        )

    def notify_risk_violation(
        self,
        user_id: str,
        user_email: str,
        user_name: str,
        risk_id: str,
        risk_level: str,
        function_1: str,
        function_2: str,
        description: str,
        recommendation: str
    ):
        """Send risk violation notification"""
        return self.send(
            notification_type=NotificationType.RISK_VIOLATION_DETECTED,
            recipient_user_id=user_id,
            recipient_email=user_email,
            recipient_name=user_name,
            context={
                "user_name": user_name,
                "user_id": user_id,
                "risk_id": risk_id,
                "risk_level": risk_level,
                "function_1": function_1,
                "function_2": function_2,
                "description": description,
                "recommendation": recommendation,
                "action_url": f"/risk/violations/{risk_id}",
                "action_label": "View Details"
            },
            reference_type="risk_violation",
            reference_id=risk_id,
            priority=NotificationPriority.URGENT if risk_level == "critical" else NotificationPriority.HIGH
        )
