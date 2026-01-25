# Intelligent Notification Engine
# Context-aware, decision-ready emails

"""
Notification Engine for GOVERNEX+.

THIS IS A MASSIVE UPGRADE OVER SAP GRC:
- SAP GRC: Generic step-based emails
- GOVERNEX+: Context-aware, per-item, decision-ready notifications

Key Differences:
1. Event-based (not step-based)
2. Per-item notifications (not per-request)
3. Role-specific content (approver vs requester)
4. Decision-ready (includes why, what, risk)
5. SLA countdown integration
6. Zero-code template customization
7. Full audit trail

ONE-LINE POSITIONING:
SAP GRC emails tell you something happened.
GOVERNEX+ emails tell you what to do, why it matters, and what happens next.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from enum import Enum
import logging
import uuid
import re

logger = logging.getLogger(__name__)


# ============================================================
# NOTIFICATION EVENTS
# ============================================================

class NotificationEvent(Enum):
    """Events that trigger notifications (more granular than MSMP)."""

    # Request lifecycle
    REQUEST_SUBMITTED = "REQUEST_SUBMITTED"
    REQUEST_COMPLETED = "REQUEST_COMPLETED"
    REQUEST_CANCELLED = "REQUEST_CANCELLED"

    # Item-level events (THE DIFFERENCE)
    ITEM_ASSIGNED = "ITEM_ASSIGNED"
    ITEM_APPROVED = "ITEM_APPROVED"
    ITEM_REJECTED = "ITEM_REJECTED"
    ITEM_PENDING = "ITEM_PENDING"
    ITEM_PROVISIONED = "ITEM_PROVISIONED"
    ITEM_PARTIALLY_PROVISIONED = "ITEM_PARTIALLY_PROVISIONED"
    ITEM_PROVISION_FAILED = "ITEM_PROVISION_FAILED"
    ITEM_ON_HOLD = "ITEM_ON_HOLD"

    # SLA events
    SLA_WARNING = "SLA_WARNING"
    SLA_CRITICAL = "SLA_CRITICAL"
    SLA_BREACH = "SLA_BREACH"

    # Workflow events
    WORKFLOW_REASSEMBLED = "WORKFLOW_REASSEMBLED"
    APPROVAL_DELEGATED = "APPROVAL_DELEGATED"
    APPROVAL_ESCALATED = "APPROVAL_ESCALATED"
    APPROVER_CHANGED = "APPROVER_CHANGED"

    # Risk events
    RISK_INCREASED = "RISK_INCREASED"
    SOD_DETECTED = "SOD_DETECTED"

    # Review events
    POST_REVIEW_REQUIRED = "POST_REVIEW_REQUIRED"
    CERTIFICATION_DUE = "CERTIFICATION_DUE"

    # Firefighter events
    FIREFIGHTER_CHECKOUT = "FIREFIGHTER_CHECKOUT"
    FIREFIGHTER_CHECKIN = "FIREFIGHTER_CHECKIN"
    FIREFIGHTER_EXTENDED = "FIREFIGHTER_EXTENDED"


class RecipientType(Enum):
    """Who receives the notification."""
    REQUESTER = "REQUESTER"
    APPROVER = "APPROVER"
    TARGET_USER = "TARGET_USER"
    MANAGER = "MANAGER"
    SECURITY = "SECURITY"
    COMPLIANCE = "COMPLIANCE"
    ROLE_OWNER = "ROLE_OWNER"
    PROCESS_OWNER = "PROCESS_OWNER"
    AUDITOR = "AUDITOR"
    CUSTOM = "CUSTOM"


class NotificationChannel(Enum):
    """Delivery channel."""
    EMAIL = "EMAIL"
    SMS = "SMS"
    PUSH = "PUSH"
    IN_APP = "IN_APP"
    TEAMS = "TEAMS"
    SLACK = "SLACK"
    WEBHOOK = "WEBHOOK"


class NotificationPriority(Enum):
    """Notification priority."""
    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    URGENT = "URGENT"


# ============================================================
# NOTIFICATION CONTEXT
# ============================================================

@dataclass
class NotificationContext:
    """Complete context for notification rendering."""

    # Request info
    request_id: str = ""
    request_type: str = "ACCESS_REQUEST"

    # User info
    requester_id: str = ""
    requester_name: str = ""
    requester_email: str = ""
    requester_department: str = ""

    target_user_id: str = ""
    target_user_name: str = ""
    target_user_email: str = ""

    # Item info (THE KEY DIFFERENCE)
    item_id: str = ""
    item_name: str = ""
    item_type: str = ""  # ROLE, TCODE, etc.
    system_id: str = ""
    system_name: str = ""

    # Risk info
    risk_score: int = 0
    risk_level: str = "LOW"
    sod_conflicts: List[str] = field(default_factory=list)

    # Approval info
    approver_id: str = ""
    approver_name: str = ""
    approver_email: str = ""
    approver_reason: str = ""  # Why this approver was selected

    # SLA info
    sla_hours: int = 48
    sla_remaining_hours: float = 48
    sla_percentage: int = 0

    # Decision info
    decision: str = ""
    decision_comments: str = ""
    decision_timestamp: Optional[datetime] = None

    # Workflow info
    current_step: str = ""
    total_steps: int = 0
    completed_steps: int = 0

    # Business justification
    business_reason: str = ""

    # Links
    approve_link: str = ""
    reject_link: str = ""
    details_link: str = ""
    dashboard_link: str = ""

    # Metadata
    timestamp: datetime = field(default_factory=datetime.now)
    event_type: NotificationEvent = NotificationEvent.REQUEST_SUBMITTED

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "request_type": self.request_type,
            "requester": {
                "id": self.requester_id,
                "name": self.requester_name,
                "email": self.requester_email,
                "department": self.requester_department,
            },
            "target_user": {
                "id": self.target_user_id,
                "name": self.target_user_name,
            },
            "item": {
                "id": self.item_id,
                "name": self.item_name,
                "type": self.item_type,
                "system": self.system_name,
            },
            "risk": {
                "score": self.risk_score,
                "level": self.risk_level,
                "sod_conflicts": self.sod_conflicts,
            },
            "approver": {
                "id": self.approver_id,
                "name": self.approver_name,
                "reason": self.approver_reason,
            },
            "sla": {
                "hours": self.sla_hours,
                "remaining": self.sla_remaining_hours,
                "percentage": self.sla_percentage,
            },
            "decision": {
                "decision": self.decision,
                "comments": self.decision_comments,
            },
            "timestamp": self.timestamp.isoformat(),
            "event_type": self.event_type.value,
        }


# ============================================================
# NOTIFICATION TEMPLATES
# ============================================================

@dataclass
class NotificationTemplate:
    """Template for generating notifications."""
    template_id: str = ""
    name: str = ""
    event: NotificationEvent = NotificationEvent.REQUEST_SUBMITTED
    recipient_type: RecipientType = RecipientType.REQUESTER
    channel: NotificationChannel = NotificationChannel.EMAIL

    # Template content
    subject_template: str = ""
    body_template: str = ""
    html_template: Optional[str] = None

    # Conditions (when to use this template)
    conditions: Dict[str, Any] = field(default_factory=dict)

    # Settings
    priority: NotificationPriority = NotificationPriority.NORMAL
    enabled: bool = True

    # Metadata
    created_by: str = ""
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "template_id": self.template_id,
            "name": self.name,
            "event": self.event.value,
            "recipient_type": self.recipient_type.value,
            "channel": self.channel.value,
            "subject_template": self.subject_template,
            "body_template": self.body_template,
            "conditions": self.conditions,
            "priority": self.priority.value,
            "enabled": self.enabled,
        }


@dataclass
class RenderedNotification:
    """A notification ready to be sent."""
    notification_id: str = field(default_factory=lambda: f"NOTIF-{str(uuid.uuid4())[:8]}")

    # Recipient
    recipient_email: str = ""
    recipient_name: str = ""
    recipient_type: RecipientType = RecipientType.REQUESTER

    # Content
    subject: str = ""
    body: str = ""
    html_body: Optional[str] = None

    # Metadata
    event: NotificationEvent = NotificationEvent.REQUEST_SUBMITTED
    channel: NotificationChannel = NotificationChannel.EMAIL
    priority: NotificationPriority = NotificationPriority.NORMAL

    # Context for audit
    context: Dict[str, Any] = field(default_factory=dict)

    # Status
    sent: bool = False
    sent_at: Optional[datetime] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "notification_id": self.notification_id,
            "recipient": {
                "email": self.recipient_email,
                "name": self.recipient_name,
                "type": self.recipient_type.value,
            },
            "subject": self.subject,
            "body": self.body,
            "event": self.event.value,
            "channel": self.channel.value,
            "priority": self.priority.value,
            "sent": self.sent,
            "sent_at": self.sent_at.isoformat() if self.sent_at else None,
        }


# ============================================================
# TEMPLATE RENDERER
# ============================================================

class TemplateRenderer:
    """
    Renders notification templates with context.

    Supports:
    - {{variable}} substitution
    - Conditional sections
    - Localization (future)
    """

    def __init__(self):
        self._helpers: Dict[str, Callable] = {}
        self._register_default_helpers()

    def _register_default_helpers(self) -> None:
        """Register default template helpers."""
        self._helpers["risk_badge"] = self._risk_badge
        self._helpers["sla_status"] = self._sla_status
        self._helpers["item_status_icon"] = self._item_status_icon

    def _risk_badge(self, score: int) -> str:
        """Generate risk badge."""
        if score >= 80:
            return "🔴 Critical"
        elif score >= 60:
            return "🟠 High"
        elif score >= 40:
            return "🟡 Medium"
        else:
            return "🟢 Low"

    def _sla_status(self, percentage: int) -> str:
        """Generate SLA status."""
        if percentage >= 100:
            return "⛔ BREACHED"
        elif percentage >= 80:
            return "⚠️ CRITICAL"
        elif percentage >= 50:
            return "⏰ WARNING"
        else:
            return "✅ ON TRACK"

    def _item_status_icon(self, status: str) -> str:
        """Generate status icon."""
        icons = {
            "APPROVED": "✅",
            "REJECTED": "❌",
            "PENDING": "⏳",
            "PROVISIONED": "✓",
            "ON_HOLD": "⏸️",
        }
        return icons.get(status.upper(), "•")

    def render(self, template: NotificationTemplate, context: NotificationContext) -> RenderedNotification:
        """Render a template with context."""
        # Build variable dictionary
        variables = self._build_variables(context)

        # Render subject
        subject = self._substitute(template.subject_template, variables)

        # Render body
        body = self._substitute(template.body_template, variables)

        # Render HTML if available
        html_body = None
        if template.html_template:
            html_body = self._substitute(template.html_template, variables)

        # Determine recipient email
        recipient_email = self._get_recipient_email(template.recipient_type, context)
        recipient_name = self._get_recipient_name(template.recipient_type, context)

        return RenderedNotification(
            recipient_email=recipient_email,
            recipient_name=recipient_name,
            recipient_type=template.recipient_type,
            subject=subject,
            body=body,
            html_body=html_body,
            event=template.event,
            channel=template.channel,
            priority=template.priority,
            context=context.to_dict(),
        )

    def _build_variables(self, context: NotificationContext) -> Dict[str, Any]:
        """Build variable dictionary for substitution."""
        return {
            # Request
            "request_id": context.request_id,
            "request_type": context.request_type,

            # User
            "requester_name": context.requester_name,
            "requester_email": context.requester_email,
            "requester_department": context.requester_department,
            "target_user_name": context.target_user_name,

            # Item
            "item_id": context.item_id,
            "item_name": context.item_name,
            "item_type": context.item_type,
            "system_name": context.system_name,
            "role_name": context.item_name,  # Alias

            # Risk
            "risk_score": context.risk_score,
            "risk_level": context.risk_level,
            "risk_badge": self._risk_badge(context.risk_score),
            "sod_conflicts": ", ".join(context.sod_conflicts) if context.sod_conflicts else "None",

            # Approver
            "approver_name": context.approver_name,
            "approver_email": context.approver_email,
            "approver_reason": context.approver_reason,

            # SLA
            "sla_hours": context.sla_hours,
            "sla_remaining": f"{context.sla_remaining_hours:.1f}h",
            "sla_remaining_hours": context.sla_remaining_hours,
            "sla_percentage": context.sla_percentage,
            "sla_status": self._sla_status(context.sla_percentage),

            # Decision
            "decision": context.decision,
            "decision_comments": context.decision_comments,

            # Workflow
            "current_step": context.current_step,
            "total_steps": context.total_steps,
            "completed_steps": context.completed_steps,
            "progress": f"{context.completed_steps}/{context.total_steps}",

            # Business
            "business_reason": context.business_reason,

            # Links
            "approve_link": context.approve_link,
            "reject_link": context.reject_link,
            "details_link": context.details_link,
            "dashboard_link": context.dashboard_link,

            # Timestamp
            "timestamp": context.timestamp.strftime("%Y-%m-%d %H:%M"),
            "date": context.timestamp.strftime("%Y-%m-%d"),
            "time": context.timestamp.strftime("%H:%M"),
        }

    def _substitute(self, template: str, variables: Dict[str, Any]) -> str:
        """Substitute variables in template."""
        result = template

        # Replace {{variable}} patterns
        pattern = r"\{\{(\w+)\}\}"
        for match in re.finditer(pattern, template):
            var_name = match.group(1)
            value = variables.get(var_name, "")
            result = result.replace(match.group(0), str(value))

        return result

    def _get_recipient_email(self, recipient_type: RecipientType, context: NotificationContext) -> str:
        """Get recipient email based on type."""
        mapping = {
            RecipientType.REQUESTER: context.requester_email,
            RecipientType.APPROVER: context.approver_email,
            RecipientType.TARGET_USER: context.target_user_email,
        }
        return mapping.get(recipient_type, "")

    def _get_recipient_name(self, recipient_type: RecipientType, context: NotificationContext) -> str:
        """Get recipient name based on type."""
        mapping = {
            RecipientType.REQUESTER: context.requester_name,
            RecipientType.APPROVER: context.approver_name,
            RecipientType.TARGET_USER: context.target_user_name,
        }
        return mapping.get(recipient_type, "")


# ============================================================
# NOTIFICATION ENGINE
# ============================================================

class NotificationEngine:
    """
    Central notification engine.

    Handles:
    - Template management
    - Event routing
    - Notification rendering
    - Delivery
    - Audit logging
    """

    def __init__(self):
        self.renderer = TemplateRenderer()
        self._templates: Dict[str, NotificationTemplate] = {}
        self._rules: List[Dict[str, Any]] = []
        self._sent_log: List[RenderedNotification] = []
        self._delivery_handler: Optional[Callable] = None

        # Load default templates
        self._load_default_templates()

    def _load_default_templates(self) -> None:
        """Load default notification templates."""

        # Requester: Item Approved
        self.register_template(NotificationTemplate(
            template_id="REQUESTER_ITEM_APPROVED",
            name="Requester - Item Approved",
            event=NotificationEvent.ITEM_APPROVED,
            recipient_type=RecipientType.REQUESTER,
            subject_template="✅ {{item_name}} Approved | Request {{request_id}}",
            body_template="""Hi {{requester_name}},

Good news! Your access request has been approved.

APPROVED:
• {{item_name}} ({{item_type}})
• System: {{system_name}}
• Risk: {{risk_badge}}

Approved by: {{approver_name}}
{{decision_comments}}

Next Steps:
The access will be provisioned automatically based on our policy.
You will receive another notification when provisioning is complete.

View details: {{details_link}}

Need help? Contact your IT support team.
""",
        ))

        # Requester: Partial Provisioning
        self.register_template(NotificationTemplate(
            template_id="REQUESTER_PARTIAL_PROVISIONED",
            name="Requester - Partial Provisioning",
            event=NotificationEvent.ITEM_PARTIALLY_PROVISIONED,
            recipient_type=RecipientType.REQUESTER,
            subject_template="⏳ Partial Access Granted | {{item_name}} Provisioned",
            body_template="""Hi {{requester_name}},

Your request has been PARTIALLY approved.

GRANTED:
• {{item_name}} ✅ (Provisioned)

PENDING:
Other items in your request are still awaiting approval.

No action required from you. You'll be notified when remaining items are decided.

View full request: {{details_link}}
""",
        ))

        # Approver: Item Assigned (Decision-Ready)
        self.register_template(NotificationTemplate(
            template_id="APPROVER_ITEM_ASSIGNED",
            name="Approver - Item Assigned",
            event=NotificationEvent.ITEM_ASSIGNED,
            recipient_type=RecipientType.APPROVER,
            priority=NotificationPriority.HIGH,
            subject_template="🔔 Approval Required: {{item_name}} | Risk {{risk_score}} | SLA {{sla_remaining}}",
            body_template="""Hi {{approver_name}},

You have a pending approval that requires your attention.

─────────────────────────────
WHY YOU
─────────────────────────────
{{approver_reason}}

─────────────────────────────
ACCESS REQUESTED
─────────────────────────────
Role: {{item_name}}
Type: {{item_type}}
System: {{system_name}}
For User: {{target_user_name}}
Requested By: {{requester_name}} ({{requester_department}})

─────────────────────────────
RISK ASSESSMENT
─────────────────────────────
Risk Score: {{risk_score}} {{risk_badge}}
SoD Conflicts: {{sod_conflicts}}

─────────────────────────────
BUSINESS JUSTIFICATION
─────────────────────────────
{{business_reason}}

─────────────────────────────
SLA STATUS
─────────────────────────────
{{sla_status}} - {{sla_remaining}} remaining

─────────────────────────────
ACTIONS
─────────────────────────────
[APPROVE] {{approve_link}}
[REJECT] {{reject_link}}
[VIEW DETAILS] {{details_link}}

If you cannot make this decision, please delegate to an appropriate colleague.
""",
        ))

        # Approver: SLA Warning
        self.register_template(NotificationTemplate(
            template_id="APPROVER_SLA_WARNING",
            name="Approver - SLA Warning",
            event=NotificationEvent.SLA_WARNING,
            recipient_type=RecipientType.APPROVER,
            priority=NotificationPriority.HIGH,
            subject_template="⏰ SLA Warning: Approval due in {{sla_remaining}} | {{item_name}}",
            body_template="""Hi {{approver_name}},

⏰ REMINDER: You have a pending approval approaching its deadline.

Role: {{item_name}}
Time Remaining: {{sla_remaining}}
SLA Status: {{sla_status}}

If not actioned soon, this will be escalated automatically.

[APPROVE] {{approve_link}}
[REJECT] {{reject_link}}
""",
        ))

        # Approver: SLA Breach
        self.register_template(NotificationTemplate(
            template_id="APPROVER_SLA_BREACH",
            name="Approver - SLA Breach",
            event=NotificationEvent.SLA_BREACH,
            recipient_type=RecipientType.APPROVER,
            priority=NotificationPriority.URGENT,
            subject_template="⛔ SLA BREACHED: {{item_name}} | Escalation Triggered",
            body_template="""Hi {{approver_name}},

⛔ SLA BREACH NOTIFICATION

The following approval has exceeded its SLA:

Role: {{item_name}}
Original SLA: {{sla_hours}}h
Time Elapsed: {{sla_remaining}} overdue

This request has been escalated to your manager.
Please action immediately or provide a reason for the delay.

[APPROVE NOW] {{approve_link}}
[REJECT NOW] {{reject_link}}
""",
        ))

        # Security: Audit Trail
        self.register_template(NotificationTemplate(
            template_id="SECURITY_PARTIAL_PROVISIONED",
            name="Security - Partial Provisioning Alert",
            event=NotificationEvent.ITEM_PARTIALLY_PROVISIONED,
            recipient_type=RecipientType.SECURITY,
            subject_template="📋 Audit: Partial Provisioning Executed | {{request_id}}",
            body_template="""Security Team,

Partial provisioning was executed for request {{request_id}}.

PROVISIONED:
• {{item_name}} (Risk: {{risk_score}})
• System: {{system_name}}
• User: {{target_user_name}}

POLICY APPLIED:
• Provisioning Mode: PER_ITEM
• Risk at Decision: {{risk_score}}
• Approved By: {{approver_name}}

AUDIT DETAILS:
• Timestamp: {{timestamp}}
• Request ID: {{request_id}}
• Item ID: {{item_id}}

Full audit trail available at: {{details_link}}
""",
        ))

        # Requester: Item Rejected
        self.register_template(NotificationTemplate(
            template_id="REQUESTER_ITEM_REJECTED",
            name="Requester - Item Rejected",
            event=NotificationEvent.ITEM_REJECTED,
            recipient_type=RecipientType.REQUESTER,
            subject_template="❌ {{item_name}} Rejected | Request {{request_id}}",
            body_template="""Hi {{requester_name}},

Unfortunately, part of your access request has been rejected.

REJECTED:
• {{item_name}} ({{item_type}})
• System: {{system_name}}

REASON:
{{decision_comments}}

Rejected by: {{approver_name}}

NEXT STEPS:
You may modify your request and resubmit, or contact {{approver_name}} for clarification.

View details: {{details_link}}
""",
        ))

    def register_template(self, template: NotificationTemplate) -> None:
        """Register a notification template."""
        self._templates[template.template_id] = template
        logger.info(f"Registered template: {template.template_id}")

    def set_delivery_handler(self, handler: Callable[[RenderedNotification], bool]) -> None:
        """Set the delivery handler (actual email sending)."""
        self._delivery_handler = handler

    def on_event(
        self,
        event: NotificationEvent,
        context: NotificationContext
    ) -> List[RenderedNotification]:
        """
        Handle a notification event.

        Finds matching templates and sends notifications.
        """
        context.event_type = event
        notifications = []

        # Find matching templates
        matching_templates = [
            t for t in self._templates.values()
            if t.event == event and t.enabled and self._check_conditions(t, context)
        ]

        # Render and send each
        for template in matching_templates:
            try:
                notification = self.renderer.render(template, context)
                notifications.append(notification)

                # Attempt delivery
                if self._delivery_handler:
                    success = self._delivery_handler(notification)
                    notification.sent = success
                    notification.sent_at = datetime.now() if success else None
                else:
                    # Mock delivery
                    notification.sent = True
                    notification.sent_at = datetime.now()

                # Log for audit
                self._sent_log.append(notification)
                logger.info(f"Notification sent: {notification.notification_id} to {notification.recipient_email}")

            except Exception as e:
                logger.error(f"Failed to send notification: {e}")
                notification = RenderedNotification(
                    event=event,
                    error=str(e),
                )
                notifications.append(notification)

        return notifications

    def _check_conditions(self, template: NotificationTemplate, context: NotificationContext) -> bool:
        """Check if template conditions are met."""
        if not template.conditions:
            return True

        for key, expected in template.conditions.items():
            actual = getattr(context, key, None)
            if actual != expected:
                return False

        return True

    def get_sent_log(
        self,
        request_id: Optional[str] = None,
        event: Optional[NotificationEvent] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get sent notification log (for audit)."""
        log = self._sent_log

        if request_id:
            log = [n for n in log if n.context.get("request_id") == request_id]
        if event:
            log = [n for n in log if n.event == event]

        return [n.to_dict() for n in log[-limit:]]

    def get_templates(self) -> List[Dict[str, Any]]:
        """Get all templates (for UI management)."""
        return [t.to_dict() for t in self._templates.values()]

    def preview_notification(
        self,
        template_id: str,
        context: NotificationContext
    ) -> Optional[RenderedNotification]:
        """Preview a notification without sending."""
        template = self._templates.get(template_id)
        if not template:
            return None

        return self.renderer.render(template, context)


# ============================================================
# NOTIFICATION RULES (CUSTOMER-CONFIGURABLE)
# ============================================================

@dataclass
class NotificationRule:
    """Customer-defined notification rule."""
    rule_id: str = ""
    name: str = ""
    enabled: bool = True

    # Trigger
    event: NotificationEvent = NotificationEvent.ITEM_ASSIGNED
    conditions: Dict[str, Any] = field(default_factory=dict)

    # Recipients
    send_to: List[RecipientType] = field(default_factory=list)
    custom_emails: List[str] = field(default_factory=list)

    # Template
    template_id: str = ""  # Use existing template
    custom_subject: Optional[str] = None  # Override subject
    custom_body: Optional[str] = None  # Override body

    # Channel
    channel: NotificationChannel = NotificationChannel.EMAIL

    # Settings
    include_risk: bool = True
    include_sla: bool = True
    include_business_reason: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "name": self.name,
            "enabled": self.enabled,
            "event": self.event.value,
            "conditions": self.conditions,
            "send_to": [r.value for r in self.send_to],
            "template_id": self.template_id,
            "channel": self.channel.value,
        }


class NotificationRuleEngine:
    """
    Customer-configurable notification rules.

    Allows customers to define:
    - Who gets mail
    - When
    - For which events
    - Per workflow
    - Per risk level
    """

    def __init__(self, notification_engine: NotificationEngine):
        self.notification_engine = notification_engine
        self._rules: List[NotificationRule] = []

    def add_rule(self, rule: NotificationRule) -> None:
        """Add a notification rule."""
        self._rules.append(rule)

    def process_event(
        self,
        event: NotificationEvent,
        context: NotificationContext
    ) -> List[RenderedNotification]:
        """Process event through rules."""
        notifications = []

        # Check custom rules first
        matching_rules = [
            r for r in self._rules
            if r.event == event and r.enabled and self._check_rule_conditions(r, context)
        ]

        if matching_rules:
            for rule in matching_rules:
                for recipient_type in rule.send_to:
                    # Create template from rule
                    template = NotificationTemplate(
                        template_id=f"RULE_{rule.rule_id}",
                        event=event,
                        recipient_type=recipient_type,
                        subject_template=rule.custom_subject or "",
                        body_template=rule.custom_body or "",
                        channel=rule.channel,
                    )

                    # If using existing template
                    if rule.template_id and rule.template_id in self.notification_engine._templates:
                        base_template = self.notification_engine._templates[rule.template_id]
                        template.subject_template = rule.custom_subject or base_template.subject_template
                        template.body_template = rule.custom_body or base_template.body_template

                    notification = self.notification_engine.renderer.render(template, context)
                    notifications.append(notification)

        # Fall back to default templates
        else:
            notifications = self.notification_engine.on_event(event, context)

        return notifications

    def _check_rule_conditions(self, rule: NotificationRule, context: NotificationContext) -> bool:
        """Check if rule conditions match context."""
        for key, expected in rule.conditions.items():
            actual = getattr(context, key, None)

            if isinstance(expected, dict):
                # Complex condition
                operator = expected.get("operator", "eq")
                value = expected.get("value")

                if operator == "gt" and actual <= value:
                    return False
                elif operator == "lt" and actual >= value:
                    return False
                elif operator == "eq" and actual != value:
                    return False
                elif operator == "in" and actual not in value:
                    return False
            else:
                if actual != expected:
                    return False

        return True

    def get_rules(self) -> List[Dict[str, Any]]:
        """Get all rules."""
        return [r.to_dict() for r in self._rules]


# ============================================================
# CONVENIENCE FUNCTIONS
# ============================================================

def create_default_notification_engine() -> NotificationEngine:
    """Create engine with default templates."""
    return NotificationEngine()


def sample_context_for_testing() -> NotificationContext:
    """Create sample context for testing."""
    return NotificationContext(
        request_id="REQ-2026-001234",
        request_type="ACCESS_REQUEST",
        requester_id="U12345",
        requester_name="John Smith",
        requester_email="john.smith@company.com",
        requester_department="Finance",
        target_user_id="U12345",
        target_user_name="John Smith",
        target_user_email="john.smith@company.com",
        item_id="ITEM-001",
        item_name="FI_VENDOR_CREATE",
        item_type="ROLE",
        system_id="PRD",
        system_name="SAP ERP Production",
        risk_score=72,
        risk_level="HIGH",
        sod_conflicts=["FI_PAYMENT_EXECUTE"],
        approver_id="A54321",
        approver_name="Jane Doe",
        approver_email="jane.doe@company.com",
        approver_reason="You own the FI_VENDOR_CREATE role and are responsible for approving vendor-related access.",
        sla_hours=48,
        sla_remaining_hours=36.5,
        sla_percentage=24,
        business_reason="Need to create vendors for new supplier onboarding project starting Q1 2026.",
        approve_link="https://governex.company.com/approve/REQ-2026-001234/ITEM-001",
        reject_link="https://governex.company.com/reject/REQ-2026-001234/ITEM-001",
        details_link="https://governex.company.com/request/REQ-2026-001234",
    )
