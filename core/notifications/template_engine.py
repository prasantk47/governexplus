"""
Notification Template Engine

Advanced notification templates with localization, personalization,
and multi-channel support (email, Slack, Teams, webhooks).
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum
from datetime import datetime
import re
import json


class NotificationChannel(Enum):
    """Notification delivery channels"""
    EMAIL = "email"
    SLACK = "slack"
    TEAMS = "teams"
    WEBHOOK = "webhook"
    SMS = "sms"
    IN_APP = "in_app"
    PUSH = "push"


class NotificationPriority(Enum):
    """Notification priority levels"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class EventType(Enum):
    """Notification event types"""
    # Access Request Events
    ACCESS_REQUEST_SUBMITTED = "access_request_submitted"
    ACCESS_REQUEST_APPROVED = "access_request_approved"
    ACCESS_REQUEST_REJECTED = "access_request_rejected"
    ACCESS_REQUEST_PENDING_APPROVAL = "access_request_pending_approval"
    ACCESS_REQUEST_ESCALATED = "access_request_escalated"
    ACCESS_REQUEST_EXPIRED = "access_request_expired"

    # Certification Events
    CERTIFICATION_CAMPAIGN_STARTED = "certification_campaign_started"
    CERTIFICATION_REVIEW_ASSIGNED = "certification_review_assigned"
    CERTIFICATION_REMINDER = "certification_reminder"
    CERTIFICATION_OVERDUE = "certification_overdue"
    CERTIFICATION_COMPLETED = "certification_completed"

    # Firefighter Events
    FIREFIGHTER_REQUEST_SUBMITTED = "firefighter_request_submitted"
    FIREFIGHTER_REQUEST_APPROVED = "firefighter_request_approved"
    FIREFIGHTER_SESSION_STARTED = "firefighter_session_started"
    FIREFIGHTER_SESSION_ENDING = "firefighter_session_ending"
    FIREFIGHTER_SESSION_ENDED = "firefighter_session_ended"
    FIREFIGHTER_SENSITIVE_ACTION = "firefighter_sensitive_action"
    FIREFIGHTER_REVIEW_PENDING = "firefighter_review_pending"

    # Risk Events
    RISK_VIOLATION_DETECTED = "risk_violation_detected"
    RISK_VIOLATION_CRITICAL = "risk_violation_critical"
    RISK_MITIGATION_EXPIRING = "risk_mitigation_expiring"

    # User Events
    USER_CREATED = "user_created"
    USER_DEACTIVATED = "user_deactivated"
    USER_ROLE_ASSIGNED = "user_role_assigned"
    USER_ROLE_REMOVED = "user_role_removed"

    # System Events
    SYSTEM_SYNC_COMPLETED = "system_sync_completed"
    SYSTEM_SYNC_FAILED = "system_sync_failed"
    SYSTEM_ALERT = "system_alert"


@dataclass
class NotificationTemplate:
    """Notification template definition"""
    template_id: str
    tenant_id: str
    name: str
    event_type: EventType
    channel: NotificationChannel

    # Content
    subject: str  # For email
    body: str
    body_html: Optional[str] = None  # HTML version for email

    # Localization
    locale: str = "en"
    translations: Dict[str, Dict[str, str]] = field(default_factory=dict)

    # Channel-specific settings
    channel_config: Dict[str, Any] = field(default_factory=dict)

    # Variables
    variables: List[str] = field(default_factory=list)
    default_values: Dict[str, Any] = field(default_factory=dict)

    # Settings
    is_active: bool = True
    priority: NotificationPriority = NotificationPriority.NORMAL

    # Metadata
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    created_by: str = ""


@dataclass
class NotificationMessage:
    """Rendered notification message"""
    message_id: str
    template_id: str
    channel: NotificationChannel
    recipient: str
    subject: str
    body: str
    body_html: Optional[str] = None
    priority: NotificationPriority = NotificationPriority.NORMAL
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)


class NotificationTemplateEngine:
    """
    Notification Template Engine

    Provides:
    1. Template management with variables
    2. Multi-channel rendering (email, Slack, Teams)
    3. Localization support
    4. Default templates for all GRC events
    5. Custom template creation
    """

    def __init__(self):
        self.templates: Dict[str, NotificationTemplate] = {}
        self._initialize_default_templates()

    def _initialize_default_templates(self):
        """Initialize default notification templates"""

        # Access Request Templates
        self._add_template(
            template_id="tpl_access_request_pending",
            name="Access Request Pending Approval",
            event_type=EventType.ACCESS_REQUEST_PENDING_APPROVAL,
            channel=NotificationChannel.EMAIL,
            subject="[Action Required] Access Request Pending Your Approval - {{request_id}}",
            body="""
Dear {{approver_name}},

An access request requires your approval:

Request Details:
- Request ID: {{request_id}}
- Requester: {{requester_name}} ({{requester_id}})
- Target User: {{target_user_name}} ({{target_user_id}})
- Requested Roles: {{requested_roles}}
- Justification: {{justification}}

Risk Assessment:
- Risk Level: {{risk_level}}
- SoD Violations: {{violation_count}}

Please review and take action:
{{action_url}}

This request will escalate if not addressed within {{sla_hours}} hours.

Best regards,
GRC Zero Trust Platform
            """,
            body_html="""
<html>
<body style="font-family: Arial, sans-serif;">
<h2>Access Request Pending Approval</h2>
<p>Dear {{approver_name}},</p>
<p>An access request requires your approval:</p>

<table style="border-collapse: collapse; width: 100%; max-width: 600px;">
<tr><td style="padding: 8px; border: 1px solid #ddd;"><strong>Request ID</strong></td><td style="padding: 8px; border: 1px solid #ddd;">{{request_id}}</td></tr>
<tr><td style="padding: 8px; border: 1px solid #ddd;"><strong>Requester</strong></td><td style="padding: 8px; border: 1px solid #ddd;">{{requester_name}} ({{requester_id}})</td></tr>
<tr><td style="padding: 8px; border: 1px solid #ddd;"><strong>Target User</strong></td><td style="padding: 8px; border: 1px solid #ddd;">{{target_user_name}} ({{target_user_id}})</td></tr>
<tr><td style="padding: 8px; border: 1px solid #ddd;"><strong>Requested Roles</strong></td><td style="padding: 8px; border: 1px solid #ddd;">{{requested_roles}}</td></tr>
<tr><td style="padding: 8px; border: 1px solid #ddd;"><strong>Risk Level</strong></td><td style="padding: 8px; border: 1px solid #ddd; color: {{risk_color}};">{{risk_level}}</td></tr>
</table>

<p style="margin-top: 20px;">
<a href="{{action_url}}" style="background-color: #4CAF50; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Review Request</a>
</p>

<p style="color: #666; font-size: 12px;">This request will escalate if not addressed within {{sla_hours}} hours.</p>
</body>
</html>
            """,
            variables=["request_id", "approver_name", "requester_name", "requester_id", "target_user_name", "target_user_id", "requested_roles", "justification", "risk_level", "risk_color", "violation_count", "action_url", "sla_hours"],
            priority=NotificationPriority.HIGH
        )

        # Slack version
        self._add_template(
            template_id="tpl_access_request_pending_slack",
            name="Access Request Pending (Slack)",
            event_type=EventType.ACCESS_REQUEST_PENDING_APPROVAL,
            channel=NotificationChannel.SLACK,
            subject="",
            body=json.dumps({
                "blocks": [
                    {
                        "type": "header",
                        "text": {"type": "plain_text", "text": ":key: Access Request Pending Approval"}
                    },
                    {
                        "type": "section",
                        "fields": [
                            {"type": "mrkdwn", "text": "*Request ID:*\n{{request_id}}"},
                            {"type": "mrkdwn", "text": "*Risk Level:*\n{{risk_level}}"},
                            {"type": "mrkdwn", "text": "*Requester:*\n{{requester_name}}"},
                            {"type": "mrkdwn", "text": "*Target User:*\n{{target_user_name}}"}
                        ]
                    },
                    {
                        "type": "section",
                        "text": {"type": "mrkdwn", "text": "*Requested Roles:* {{requested_roles}}"}
                    },
                    {
                        "type": "actions",
                        "elements": [
                            {"type": "button", "text": {"type": "plain_text", "text": "Approve"}, "style": "primary", "action_id": "approve_{{request_id}}"},
                            {"type": "button", "text": {"type": "plain_text", "text": "Reject"}, "style": "danger", "action_id": "reject_{{request_id}}"},
                            {"type": "button", "text": {"type": "plain_text", "text": "View Details"}, "url": "{{action_url}}"}
                        ]
                    }
                ]
            }),
            variables=["request_id", "requester_name", "target_user_name", "requested_roles", "risk_level", "action_url"],
            priority=NotificationPriority.HIGH
        )

        # Certification Reminder
        self._add_template(
            template_id="tpl_certification_reminder",
            name="Certification Review Reminder",
            event_type=EventType.CERTIFICATION_REMINDER,
            channel=NotificationChannel.EMAIL,
            subject="[Reminder] {{pending_count}} Access Reviews Pending - Due {{due_date}}",
            body="""
Dear {{reviewer_name}},

This is a reminder that you have {{pending_count}} access reviews pending for the certification campaign:

Campaign: {{campaign_name}}
Due Date: {{due_date}}
Days Remaining: {{days_remaining}}

Items to Review:
{{review_summary}}

Please complete your reviews before the due date:
{{action_url}}

Thank you for helping maintain access compliance.

Best regards,
GRC Zero Trust Platform
            """,
            variables=["reviewer_name", "pending_count", "campaign_name", "due_date", "days_remaining", "review_summary", "action_url"],
            priority=NotificationPriority.NORMAL
        )

        # Firefighter Sensitive Action Alert
        self._add_template(
            template_id="tpl_firefighter_sensitive_action",
            name="Firefighter Sensitive Action Alert",
            event_type=EventType.FIREFIGHTER_SENSITIVE_ACTION,
            channel=NotificationChannel.EMAIL,
            subject="[ALERT] Sensitive Action Detected - Firefighter Session {{session_id}}",
            body="""
SECURITY ALERT

A sensitive action has been detected during an active firefighter session:

Session Details:
- Session ID: {{session_id}}
- Firefighter ID: {{firefighter_id}}
- User: {{user_name}} ({{user_id}})
- Started: {{session_start}}

Sensitive Action:
- Transaction: {{transaction}}
- Action: {{action_description}}
- Timestamp: {{action_time}}
- Details: {{action_details}}

This action has been logged and may require post-session review.

View Session Details: {{session_url}}

This is an automated alert from the GRC Zero Trust Platform.
            """,
            variables=["session_id", "firefighter_id", "user_name", "user_id", "session_start", "transaction", "action_description", "action_time", "action_details", "session_url"],
            priority=NotificationPriority.URGENT
        )

        # Risk Violation Critical
        self._add_template(
            template_id="tpl_risk_violation_critical",
            name="Critical Risk Violation Alert",
            event_type=EventType.RISK_VIOLATION_CRITICAL,
            channel=NotificationChannel.EMAIL,
            subject="[CRITICAL] SoD Violation Detected - {{user_name}}",
            body="""
CRITICAL RISK ALERT

A critical Segregation of Duties violation has been detected:

User: {{user_name}} ({{user_id}})
Department: {{department}}

Violation Details:
- Rule: {{rule_name}}
- Risk Level: CRITICAL
- Function 1: {{function_1}}
- Function 2: {{function_2}}

Business Impact:
{{risk_description}}

Compliance Impact: {{compliance_frameworks}}

Recommended Actions:
1. Review user's current access
2. Implement compensating controls if access is required
3. Consider role redesign to eliminate conflict

Take Action: {{action_url}}

This violation was detected at {{detected_at}}.
            """,
            variables=["user_name", "user_id", "department", "rule_name", "function_1", "function_2", "risk_description", "compliance_frameworks", "action_url", "detected_at"],
            priority=NotificationPriority.URGENT
        )

        # Microsoft Teams version
        self._add_template(
            template_id="tpl_risk_violation_critical_teams",
            name="Critical Risk Violation (Teams)",
            event_type=EventType.RISK_VIOLATION_CRITICAL,
            channel=NotificationChannel.TEAMS,
            subject="",
            body=json.dumps({
                "@type": "MessageCard",
                "@context": "http://schema.org/extensions",
                "themeColor": "FF0000",
                "summary": "Critical SoD Violation Detected",
                "sections": [{
                    "activityTitle": "🚨 Critical SoD Violation",
                    "activitySubtitle": "{{user_name}} ({{user_id}})",
                    "facts": [
                        {"name": "Rule", "value": "{{rule_name}}"},
                        {"name": "Risk Level", "value": "CRITICAL"},
                        {"name": "Function 1", "value": "{{function_1}}"},
                        {"name": "Function 2", "value": "{{function_2}}"},
                        {"name": "Detected", "value": "{{detected_at}}"}
                    ],
                    "markdown": True
                }],
                "potentialAction": [{
                    "@type": "OpenUri",
                    "name": "View Details",
                    "targets": [{"os": "default", "uri": "{{action_url}}"}]
                }]
            }),
            variables=["user_name", "user_id", "rule_name", "function_1", "function_2", "detected_at", "action_url"],
            priority=NotificationPriority.URGENT
        )

    def _add_template(
        self,
        template_id: str,
        name: str,
        event_type: EventType,
        channel: NotificationChannel,
        subject: str,
        body: str,
        body_html: str = None,
        variables: List[str] = None,
        priority: NotificationPriority = NotificationPriority.NORMAL
    ):
        """Add a template to the engine"""
        template = NotificationTemplate(
            template_id=template_id,
            tenant_id="__system__",
            name=name,
            event_type=event_type,
            channel=channel,
            subject=subject,
            body=body.strip(),
            body_html=body_html.strip() if body_html else None,
            variables=variables or [],
            priority=priority
        )
        self.templates[template_id] = template

    # ==================== Template Management ====================

    def create_template(
        self,
        tenant_id: str,
        name: str,
        event_type: EventType,
        channel: NotificationChannel,
        subject: str,
        body: str,
        body_html: str = None,
        variables: List[str] = None,
        translations: Dict[str, Dict[str, str]] = None,
        priority: NotificationPriority = NotificationPriority.NORMAL,
        created_by: str = ""
    ) -> NotificationTemplate:
        """Create a custom notification template"""
        template_id = f"tpl_{tenant_id}_{event_type.value}_{channel.value}"

        template = NotificationTemplate(
            template_id=template_id,
            tenant_id=tenant_id,
            name=name,
            event_type=event_type,
            channel=channel,
            subject=subject,
            body=body,
            body_html=body_html,
            variables=variables or self._extract_variables(body),
            translations=translations or {},
            priority=priority,
            created_by=created_by
        )

        self.templates[template_id] = template
        return template

    def get_template(
        self,
        event_type: EventType,
        channel: NotificationChannel,
        tenant_id: str = None
    ) -> Optional[NotificationTemplate]:
        """Get template for event type and channel"""
        # First try tenant-specific template
        if tenant_id:
            tenant_template_id = f"tpl_{tenant_id}_{event_type.value}_{channel.value}"
            if tenant_template_id in self.templates:
                return self.templates[tenant_template_id]

        # Fall back to system template
        for template in self.templates.values():
            if (template.event_type == event_type and
                template.channel == channel and
                template.tenant_id == "__system__"):
                return template

        return None

    def _extract_variables(self, text: str) -> List[str]:
        """Extract variable names from template text"""
        pattern = r'\{\{(\w+)\}\}'
        return list(set(re.findall(pattern, text)))

    # ==================== Rendering ====================

    def render(
        self,
        template: NotificationTemplate,
        variables: Dict[str, Any],
        locale: str = "en"
    ) -> NotificationMessage:
        """Render a notification template with variables"""
        # Get localized content
        if locale != "en" and locale in template.translations:
            subject = template.translations[locale].get("subject", template.subject)
            body = template.translations[locale].get("body", template.body)
            body_html = template.translations[locale].get("body_html", template.body_html)
        else:
            subject = template.subject
            body = template.body
            body_html = template.body_html

        # Apply default values
        merged_vars = {**template.default_values, **variables}

        # Render
        rendered_subject = self._render_text(subject, merged_vars)
        rendered_body = self._render_text(body, merged_vars)
        rendered_html = self._render_text(body_html, merged_vars) if body_html else None

        return NotificationMessage(
            message_id=f"msg_{template.template_id}_{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}",
            template_id=template.template_id,
            channel=template.channel,
            recipient=variables.get("recipient", ""),
            subject=rendered_subject,
            body=rendered_body,
            body_html=rendered_html,
            priority=template.priority,
            metadata={"variables": merged_vars, "locale": locale}
        )

    def _render_text(self, text: str, variables: Dict[str, Any]) -> str:
        """Render text with variable substitution"""
        if not text:
            return ""

        result = text
        for key, value in variables.items():
            placeholder = f"{{{{{key}}}}}"
            result = result.replace(placeholder, str(value) if value is not None else "")

        return result

    # ==================== Multi-Channel Rendering ====================

    def render_for_all_channels(
        self,
        event_type: EventType,
        variables: Dict[str, Any],
        tenant_id: str = None,
        channels: List[NotificationChannel] = None
    ) -> List[NotificationMessage]:
        """Render notification for all configured channels"""
        if channels is None:
            channels = [NotificationChannel.EMAIL, NotificationChannel.SLACK, NotificationChannel.TEAMS]

        messages = []

        for channel in channels:
            template = self.get_template(event_type, channel, tenant_id)
            if template and template.is_active:
                message = self.render(template, variables)
                messages.append(message)

        return messages

    # ==================== Template Export/Import ====================

    def export_templates(self, tenant_id: str = None) -> Dict[str, Any]:
        """Export templates to JSON"""
        templates_to_export = []

        for template in self.templates.values():
            if tenant_id is None or template.tenant_id == tenant_id:
                templates_to_export.append({
                    "template_id": template.template_id,
                    "name": template.name,
                    "event_type": template.event_type.value,
                    "channel": template.channel.value,
                    "subject": template.subject,
                    "body": template.body,
                    "body_html": template.body_html,
                    "variables": template.variables,
                    "translations": template.translations,
                    "priority": template.priority.value
                })

        return {
            "version": "1.0",
            "exported_at": datetime.utcnow().isoformat(),
            "templates": templates_to_export
        }

    def import_templates(
        self,
        data: Dict[str, Any],
        tenant_id: str
    ) -> Dict[str, Any]:
        """Import templates from JSON"""
        imported = 0
        errors = []

        for tpl_data in data.get("templates", []):
            try:
                self.create_template(
                    tenant_id=tenant_id,
                    name=tpl_data["name"],
                    event_type=EventType(tpl_data["event_type"]),
                    channel=NotificationChannel(tpl_data["channel"]),
                    subject=tpl_data["subject"],
                    body=tpl_data["body"],
                    body_html=tpl_data.get("body_html"),
                    variables=tpl_data.get("variables", []),
                    translations=tpl_data.get("translations", {}),
                    priority=NotificationPriority(tpl_data.get("priority", "normal"))
                )
                imported += 1
            except Exception as e:
                errors.append({"template": tpl_data.get("name"), "error": str(e)})

        return {"imported": imported, "errors": errors}


# Singleton instance
template_engine = NotificationTemplateEngine()
