# GRC AI Assistant
# Conversational interface for zero-training experience

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
from datetime import datetime
import re


class QueryType(Enum):
    """Types of assistant queries"""
    RISK_CHECK = "risk_check"
    ACCESS_REQUEST = "access_request"
    APPROVAL_ACTION = "approval_action"
    REPORT_REQUEST = "report_request"
    HELP_QUESTION = "help_question"
    NAVIGATION = "navigation"
    STATUS_CHECK = "status_check"
    ANOMALY_ALERT = "anomaly_alert"
    REMEDIATION = "remediation"
    ROLE_DESIGN = "role_design"


class ConversationState(Enum):
    """State of the conversation"""
    IDLE = "idle"
    GATHERING_INFO = "gathering_info"
    CONFIRMING = "confirming"
    EXECUTING = "executing"
    COMPLETED = "completed"


@dataclass
class ConversationContext:
    """Context for ongoing conversation"""
    session_id: str
    user_id: str
    state: ConversationState = ConversationState.IDLE
    current_intent: Optional[QueryType] = None
    collected_data: Dict[str, Any] = field(default_factory=dict)
    history: List[Dict[str, str]] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_activity: datetime = field(default_factory=datetime.utcnow)


@dataclass
class AssistantResponse:
    """Response from the assistant"""
    message: str
    success: bool = True
    query_type: Optional[QueryType] = None

    # Actions the assistant can take
    actions: List[Dict[str, Any]] = field(default_factory=list)

    # Suggested follow-ups
    suggestions: List[str] = field(default_factory=list)

    # Data to display
    data: Optional[Any] = None
    visualization: Optional[str] = None  # "table", "chart", "form", etc.

    # State
    needs_confirmation: bool = False
    confirmation_question: str = ""


class GRCAssistant:
    """
    GRC AI Assistant

    Provides a conversational interface for all GRC operations.
    Users can interact naturally without training.

    Key capabilities:
    1. Natural language understanding
    2. Multi-turn conversations
    3. Proactive alerts and suggestions
    4. One-click actions
    5. Contextual help

    Example interactions:
    - "Show my risks"
    - "I need access to create purchase orders"
    - "Approve John's request"
    - "What's the status of my access request?"
    - "Help me understand this SoD violation"
    """

    def __init__(self):
        # Active conversation contexts
        self.contexts: Dict[str, ConversationContext] = {}

        # Command handlers
        self.handlers: Dict[QueryType, Callable] = {
            QueryType.RISK_CHECK: self._handle_risk_check,
            QueryType.ACCESS_REQUEST: self._handle_access_request,
            QueryType.APPROVAL_ACTION: self._handle_approval,
            QueryType.REPORT_REQUEST: self._handle_report,
            QueryType.HELP_QUESTION: self._handle_help,
            QueryType.STATUS_CHECK: self._handle_status,
            QueryType.ANOMALY_ALERT: self._handle_anomaly,
            QueryType.REMEDIATION: self._handle_remediation,
            QueryType.ROLE_DESIGN: self._handle_role_design,
            QueryType.NAVIGATION: self._handle_navigation,
        }

        # Quick action patterns
        self.quick_actions = {
            "approve": self._quick_approve,
            "reject": self._quick_reject,
            "show risks": self._quick_show_risks,
            "my approvals": self._quick_my_approvals,
        }

        # Demo data
        self._demo_data = self._initialize_demo_data()

    def _initialize_demo_data(self) -> Dict[str, Any]:
        """Initialize demo data for responses"""
        return {
            "current_user": {
                "id": "JSMITH",
                "name": "John Smith",
                "department": "Finance",
                "manager": "Mary Williams",
                "risk_score": 65,
                "violations": 3
            },
            "pending_approvals": [
                {
                    "id": "REQ-2024-001",
                    "requester": "Alice Wilson",
                    "type": "Role Request",
                    "role": "FI_AP_MANAGER",
                    "risk": "medium",
                    "submitted": "2 hours ago"
                },
                {
                    "id": "REQ-2024-002",
                    "requester": "Bob Johnson",
                    "type": "Emergency Access",
                    "system": "PRD",
                    "risk": "high",
                    "submitted": "30 minutes ago"
                }
            ],
            "my_requests": [
                {
                    "id": "REQ-2024-005",
                    "type": "Role Request",
                    "role": "FI_GL_MANAGER",
                    "status": "Pending Manager Approval",
                    "submitted": "Yesterday"
                }
            ],
            "violations": [
                {
                    "id": "SOD-001",
                    "rule": "AP Invoice vs Payment",
                    "risk": "high",
                    "status": "Open"
                },
                {
                    "id": "SOD-002",
                    "rule": "Vendor Master vs AP Payment",
                    "risk": "critical",
                    "status": "Open"
                }
            ]
        }

    # ==================== Main Entry Point ====================

    def chat(
        self,
        user_id: str,
        message: str,
        session_id: Optional[str] = None
    ) -> AssistantResponse:
        """
        Main entry point for chat interaction

        Handles:
        - New conversations
        - Continuing multi-turn dialogs
        - Quick actions
        """
        # Get or create context
        if session_id and session_id in self.contexts:
            context = self.contexts[session_id]
        else:
            session_id = f"session_{user_id}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
            context = ConversationContext(session_id=session_id, user_id=user_id)
            self.contexts[session_id] = context

        # Update context
        context.last_activity = datetime.utcnow()
        context.history.append({"role": "user", "content": message})

        # Check for quick actions first
        lower_msg = message.lower().strip()
        for pattern, handler in self.quick_actions.items():
            if lower_msg.startswith(pattern) or lower_msg == pattern:
                response = handler(context, message)
                context.history.append({"role": "assistant", "content": response.message})
                return response

        # Handle ongoing conversation
        if context.state == ConversationState.GATHERING_INFO:
            response = self._continue_gathering(context, message)
        elif context.state == ConversationState.CONFIRMING:
            response = self._handle_confirmation(context, message)
        else:
            # New query - detect intent and handle
            intent = self._detect_intent(message)
            context.current_intent = intent
            handler = self.handlers.get(intent, self._handle_unknown)
            response = handler(context, message)

        context.history.append({"role": "assistant", "content": response.message})
        return response

    def _detect_intent(self, message: str) -> QueryType:
        """Detect user intent from message"""
        lower = message.lower()

        # Risk-related
        if any(word in lower for word in ["risk", "violation", "sod", "conflict"]):
            return QueryType.RISK_CHECK

        # Access request
        if any(word in lower for word in ["need access", "request access", "give me", "i need"]):
            return QueryType.ACCESS_REQUEST

        # Approvals
        if any(word in lower for word in ["approve", "reject", "pending approval", "my approvals"]):
            return QueryType.APPROVAL_ACTION

        # Reports
        if any(word in lower for word in ["report", "generate", "export", "download"]):
            return QueryType.REPORT_REQUEST

        # Status
        if any(word in lower for word in ["status", "where is", "what happened", "track"]):
            return QueryType.STATUS_CHECK

        # Anomaly
        if any(word in lower for word in ["unusual", "anomaly", "strange", "suspicious"]):
            return QueryType.ANOMALY_ALERT

        # Remediation
        if any(word in lower for word in ["fix", "remediate", "resolve", "remove"]):
            return QueryType.REMEDIATION

        # Role design
        if any(word in lower for word in ["create role", "design role", "new role"]):
            return QueryType.ROLE_DESIGN

        # Navigation
        if any(word in lower for word in ["go to", "show me", "open", "navigate"]):
            return QueryType.NAVIGATION

        # Default to help
        return QueryType.HELP_QUESTION

    # ==================== Quick Actions ====================

    def _quick_show_risks(self, context: ConversationContext, message: str) -> AssistantResponse:
        """Quick action: show user's risks"""
        user_data = self._demo_data["current_user"]
        violations = self._demo_data["violations"]

        response_text = f"""Here's your risk summary:

**Risk Score:** {user_data['risk_score']}/100 (Above department average)

**Active Violations ({len(violations)}):**
"""
        for v in violations:
            response_text += f"• {v['rule']} - {v['risk'].upper()} risk\n"

        response_text += "\nWould you like me to suggest remediation options?"

        return AssistantResponse(
            message=response_text,
            query_type=QueryType.RISK_CHECK,
            data={"risk_score": user_data["risk_score"], "violations": violations},
            visualization="risk_gauge",
            suggestions=[
                "Show remediation options",
                "Compare to my peers",
                "View violation details"
            ]
        )

    def _quick_my_approvals(self, context: ConversationContext, message: str) -> AssistantResponse:
        """Quick action: show pending approvals"""
        approvals = self._demo_data["pending_approvals"]

        if not approvals:
            return AssistantResponse(
                message="You have no pending approvals. Nice work keeping your inbox clear!",
                query_type=QueryType.APPROVAL_ACTION,
                suggestions=["Show my requests", "Check team status"]
            )

        response_text = f"You have **{len(approvals)} items** pending your approval:\n\n"

        for i, approval in enumerate(approvals, 1):
            response_text += f"{i}. **{approval['type']}** from {approval['requester']}\n"
            response_text += f"   Risk: {approval['risk'].upper()} | Submitted: {approval['submitted']}\n\n"

        response_text += "Say 'approve 1' or 'reject 2' to take action."

        return AssistantResponse(
            message=response_text,
            query_type=QueryType.APPROVAL_ACTION,
            data=approvals,
            visualization="action_list",
            actions=[
                {"type": "approve", "label": "Approve All Low-Risk"},
                {"type": "view", "label": "View Details"}
            ],
            suggestions=[
                "Approve 1",
                "Show risk analysis for request 2",
                "Delegate to someone else"
            ]
        )

    def _quick_approve(self, context: ConversationContext, message: str) -> AssistantResponse:
        """Quick action: approve a request"""
        # Extract request number or ID
        numbers = re.findall(r'\d+', message)
        approvals = self._demo_data["pending_approvals"]

        if numbers:
            idx = int(numbers[0]) - 1
            if 0 <= idx < len(approvals):
                approval = approvals[idx]
                return AssistantResponse(
                    message=f"Ready to approve **{approval['type']}** from {approval['requester']}.\n\n"
                           f"Risk Level: {approval['risk'].upper()}\n\n"
                           f"Do you want to proceed?",
                    query_type=QueryType.APPROVAL_ACTION,
                    needs_confirmation=True,
                    confirmation_question="Confirm approval?",
                    suggestions=["Yes, approve", "Show more details", "No, cancel"]
                )

        return AssistantResponse(
            message="Which request would you like to approve? Please specify the request number.",
            query_type=QueryType.APPROVAL_ACTION,
            suggestions=["Show my approvals", "Approve all"]
        )

    def _quick_reject(self, context: ConversationContext, message: str) -> AssistantResponse:
        """Quick action: reject a request"""
        numbers = re.findall(r'\d+', message)

        if numbers:
            return AssistantResponse(
                message=f"To reject request #{numbers[0]}, please provide a reason:\n\n"
                       f"This will be shared with the requester.",
                query_type=QueryType.APPROVAL_ACTION,
                actions=[{"type": "input", "label": "Rejection reason"}],
                suggestions=[
                    "Missing justification",
                    "SoD conflict - need mitigation first",
                    "Request different role"
                ]
            )

        return AssistantResponse(
            message="Which request would you like to reject?",
            suggestions=["Show my approvals"]
        )

    # ==================== Intent Handlers ====================

    def _handle_risk_check(self, context: ConversationContext, message: str) -> AssistantResponse:
        """Handle risk-related queries"""
        lower = message.lower()

        # Check if asking about self
        if any(word in lower for word in ["my", "me", "i have"]):
            return self._quick_show_risks(context, message)

        # Check if asking about team/department
        if any(word in lower for word in ["team", "department", "finance", "it"]):
            return AssistantResponse(
                message="Finance department risk summary:\n\n"
                       "**Average Risk Score:** 52/100\n"
                       "**High-Risk Users:** 3 of 45\n"
                       "**Open Violations:** 12\n\n"
                       "Your score of 65 is above the department average.",
                query_type=QueryType.RISK_CHECK,
                visualization="bar_chart",
                suggestions=[
                    "Who are the high-risk users?",
                    "Show violation breakdown",
                    "Compare to other departments"
                ]
            )

        # Generic risk query
        return AssistantResponse(
            message="I can help with risk analysis. What would you like to know?\n\n"
                   "• Your personal risk score\n"
                   "• Your team's risk profile\n"
                   "• Organization-wide risk summary",
            query_type=QueryType.RISK_CHECK,
            suggestions=[
                "Show my risks",
                "Show team risks",
                "Show organization summary"
            ]
        )

    def _handle_access_request(self, context: ConversationContext, message: str) -> AssistantResponse:
        """Handle access request creation"""
        lower = message.lower()

        # Check what access they need
        if "purchase order" in lower or "po" in lower:
            context.state = ConversationState.GATHERING_INFO
            context.collected_data["requested_function"] = "Purchase Order Creation"

            return AssistantResponse(
                message="I can help you request access to create Purchase Orders.\n\n"
                       "**Recommended Role:** MM_BUYER\n"
                       "**Risk Preview:** LOW (no SoD conflicts with your current access)\n\n"
                       "Would you like me to create this request?",
                query_type=QueryType.ACCESS_REQUEST,
                needs_confirmation=True,
                confirmation_question="Create access request for MM_BUYER role?",
                suggestions=[
                    "Yes, create request",
                    "Show what this role includes",
                    "I need different access"
                ]
            )

        # Generic access request
        context.state = ConversationState.GATHERING_INFO

        return AssistantResponse(
            message="I can help you request access. What do you need to do?\n\n"
                   "For example:\n"
                   "• 'I need to create purchase orders'\n"
                   "• 'I need the same access as John Smith'\n"
                   "• 'I need the FI_AP_CLERK role'",
            query_type=QueryType.ACCESS_REQUEST,
            suggestions=[
                "Create purchase orders",
                "View financial reports",
                "Manage user accounts"
            ]
        )

    def _handle_approval(self, context: ConversationContext, message: str) -> AssistantResponse:
        """Handle approval-related queries"""
        return self._quick_my_approvals(context, message)

    def _handle_report(self, context: ConversationContext, message: str) -> AssistantResponse:
        """Handle report requests"""
        lower = message.lower()

        if "sox" in lower:
            report_type = "SOX Compliance"
        elif "risk" in lower:
            report_type = "Risk Summary"
        elif "audit" in lower:
            report_type = "Audit Trail"
        else:
            report_type = "General"

        return AssistantResponse(
            message=f"I can generate a **{report_type} Report** for you.\n\n"
                   f"**What period?**\n"
                   f"• Last 30 days\n"
                   f"• Last quarter\n"
                   f"• Year to date\n"
                   f"• Custom range",
            query_type=QueryType.REPORT_REQUEST,
            actions=[
                {"type": "generate", "label": f"Generate {report_type} Report"}
            ],
            suggestions=[
                "Last 30 days",
                "Last quarter",
                "Custom date range"
            ]
        )

    def _handle_status(self, context: ConversationContext, message: str) -> AssistantResponse:
        """Handle status check queries"""
        requests = self._demo_data["my_requests"]

        if requests:
            req = requests[0]
            return AssistantResponse(
                message=f"Here's the status of your most recent request:\n\n"
                       f"**Request ID:** {req['id']}\n"
                       f"**Type:** {req['type']} for {req['role']}\n"
                       f"**Status:** {req['status']}\n"
                       f"**Submitted:** {req['submitted']}\n\n"
                       f"Your manager needs to approve this request.",
                query_type=QueryType.STATUS_CHECK,
                data=requests,
                suggestions=[
                    "Send reminder to manager",
                    "Cancel this request",
                    "Show all my requests"
                ]
            )

        return AssistantResponse(
            message="You don't have any pending requests. Would you like to create one?",
            suggestions=["Request access", "Show my current access"]
        )

    def _handle_anomaly(self, context: ConversationContext, message: str) -> AssistantResponse:
        """Handle anomaly-related queries"""
        return AssistantResponse(
            message="I've been monitoring for unusual activity.\n\n"
                   "**No anomalies detected** for your account in the last 24 hours.\n\n"
                   "Your activity patterns are consistent with your normal behavior.",
            query_type=QueryType.ANOMALY_ALERT,
            suggestions=[
                "Show my activity log",
                "What counts as unusual?",
                "Check my team's anomalies"
            ]
        )

    def _handle_remediation(self, context: ConversationContext, message: str) -> AssistantResponse:
        """Handle remediation requests"""
        violations = self._demo_data["violations"]

        if violations:
            v = violations[0]
            return AssistantResponse(
                message=f"Let me help you resolve the **{v['rule']}** violation.\n\n"
                       f"**Recommended Action:** Add mitigating control\n\n"
                       f"This allows you to keep the access with additional oversight. "
                       f"A report will be generated monthly for your manager to review.\n\n"
                       f"Do you want me to set this up?",
                query_type=QueryType.REMEDIATION,
                needs_confirmation=True,
                confirmation_question="Add mitigating control?",
                actions=[
                    {"type": "mitigate", "label": "Add Mitigating Control"},
                    {"type": "remove", "label": "Remove Conflicting Access"}
                ],
                suggestions=[
                    "Yes, add mitigation",
                    "Show other options",
                    "I'll handle this later"
                ]
            )

        return AssistantResponse(
            message="You don't have any open violations to remediate!",
            suggestions=["Show my risk score", "View all remediations"]
        )

    def _handle_role_design(self, context: ConversationContext, message: str) -> AssistantResponse:
        """Handle role design assistance"""
        context.state = ConversationState.GATHERING_INFO

        return AssistantResponse(
            message="I can help you design a new role. Let's start with the basics:\n\n"
                   "**What business function is this role for?**\n\n"
                   "For example:\n"
                   "• Accounts Payable processing\n"
                   "• Purchase order creation\n"
                   "• User administration",
            query_type=QueryType.ROLE_DESIGN,
            suggestions=[
                "Accounts Payable",
                "Procurement",
                "Financial Reporting"
            ]
        )

    def _handle_navigation(self, context: ConversationContext, message: str) -> AssistantResponse:
        """Handle navigation requests"""
        lower = message.lower()

        pages = {
            "dashboard": "/dashboard",
            "risk": "/risk-analysis",
            "requests": "/access-requests",
            "approvals": "/approvals",
            "reports": "/reports",
            "settings": "/settings"
        }

        for keyword, path in pages.items():
            if keyword in lower:
                return AssistantResponse(
                    message=f"Opening **{keyword.title()}**...",
                    query_type=QueryType.NAVIGATION,
                    actions=[{"type": "navigate", "path": path}]
                )

        return AssistantResponse(
            message="Where would you like to go?\n\n"
                   "• Dashboard\n"
                   "• Risk Analysis\n"
                   "• Access Requests\n"
                   "• Reports\n"
                   "• Settings",
            query_type=QueryType.NAVIGATION,
            suggestions=["Dashboard", "Risk Analysis", "Reports"]
        )

    def _handle_help(self, context: ConversationContext, message: str) -> AssistantResponse:
        """Handle help queries"""
        return AssistantResponse(
            message="Hi! I'm your GRC Assistant. Here's what I can help with:\n\n"
                   "**Quick Actions:**\n"
                   "• 'Show my risks' - View your risk score and violations\n"
                   "• 'My approvals' - See what needs your attention\n"
                   "• 'Request access' - Start an access request\n\n"
                   "**Reports:**\n"
                   "• 'Generate SOX report'\n"
                   "• 'Show risk trends'\n\n"
                   "**Help:**\n"
                   "• 'What is SoD?'\n"
                   "• 'How do I reduce my risk score?'\n\n"
                   "Just type naturally - I'll understand!",
            query_type=QueryType.HELP_QUESTION,
            suggestions=[
                "Show my risks",
                "My approvals",
                "Request access"
            ]
        )

    def _handle_unknown(self, context: ConversationContext, message: str) -> AssistantResponse:
        """Handle unknown queries"""
        return AssistantResponse(
            message="I'm not sure I understood that. Could you rephrase?\n\n"
                   "Here are some things I can help with:\n"
                   "• Check your risk score\n"
                   "• Request access\n"
                   "• Approve requests\n"
                   "• Generate reports",
            suggestions=[
                "Show my risks",
                "My approvals",
                "Help"
            ]
        )

    # ==================== Multi-Turn Handling ====================

    def _continue_gathering(self, context: ConversationContext, message: str) -> AssistantResponse:
        """Continue gathering information for multi-turn dialog"""
        intent = context.current_intent

        if intent == QueryType.ACCESS_REQUEST:
            # Add to collected data
            context.collected_data["additional_info"] = message
            context.state = ConversationState.CONFIRMING

            return AssistantResponse(
                message=f"Got it. Here's what I'll request:\n\n"
                       f"**Function:** {context.collected_data.get('requested_function', message)}\n"
                       f"**Notes:** {message}\n\n"
                       f"Shall I submit this request?",
                needs_confirmation=True,
                confirmation_question="Submit this access request?",
                suggestions=["Yes, submit", "Add more details", "Cancel"]
            )

        if intent == QueryType.ROLE_DESIGN:
            context.collected_data["business_function"] = message
            context.state = ConversationState.IDLE

            return AssistantResponse(
                message=f"Based on the **{message}** function, here's my recommended role design:\n\n"
                       f"**Suggested Name:** {message.replace(' ', '_').upper()}_ROLE\n"
                       f"**Transactions:** Based on similar roles in your organization\n"
                       f"**SoD Status:** No conflicts detected\n\n"
                       f"Would you like me to create this role template?",
                query_type=QueryType.ROLE_DESIGN,
                needs_confirmation=True,
                suggestions=["Create template", "Modify design", "Start over"]
            )

        # Default
        context.state = ConversationState.IDLE
        return self._handle_unknown(context, message)

    def _handle_confirmation(self, context: ConversationContext, message: str) -> AssistantResponse:
        """Handle confirmation responses"""
        lower = message.lower()

        if any(word in lower for word in ["yes", "confirm", "approve", "submit", "create", "proceed"]):
            context.state = ConversationState.COMPLETED

            if context.current_intent == QueryType.ACCESS_REQUEST:
                return AssistantResponse(
                    message="**Access request submitted!**\n\n"
                           "Request ID: REQ-2024-099\n"
                           "Status: Pending Manager Approval\n\n"
                           "I'll notify you when there's an update.",
                    query_type=QueryType.ACCESS_REQUEST,
                    actions=[{"type": "track", "label": "Track Request"}],
                    suggestions=["Track this request", "Submit another", "Go to dashboard"]
                )

            if context.current_intent == QueryType.APPROVAL_ACTION:
                return AssistantResponse(
                    message="**Request approved!**\n\n"
                           "The requester has been notified and access will be provisioned shortly.",
                    suggestions=["Show remaining approvals", "Go to dashboard"]
                )

            return AssistantResponse(
                message="Done! Is there anything else I can help with?",
                suggestions=["Show my risks", "My approvals", "No, thanks"]
            )

        elif any(word in lower for word in ["no", "cancel", "stop", "never mind"]):
            context.state = ConversationState.IDLE
            return AssistantResponse(
                message="No problem, I've cancelled that action. What else can I help with?",
                suggestions=["Show my risks", "Request access", "Help"]
            )

        else:
            # Didn't understand the response
            return AssistantResponse(
                message="Sorry, I didn't catch that. Did you want to proceed?\n\n"
                       "Say 'yes' to confirm or 'no' to cancel.",
                needs_confirmation=True,
                suggestions=["Yes", "No"]
            )

    # ==================== Proactive Suggestions ====================

    def get_proactive_suggestions(self, user_id: str) -> List[Dict[str, Any]]:
        """Get proactive suggestions for a user based on their context"""
        suggestions = []

        # Check for pending approvals
        approvals = self._demo_data["pending_approvals"]
        if approvals:
            suggestions.append({
                "type": "action",
                "title": f"You have {len(approvals)} pending approvals",
                "action": "Show approvals",
                "priority": "high"
            })

        # Check for overdue reviews
        suggestions.append({
            "type": "reminder",
            "title": "Access review due in 5 days",
            "action": "Start review",
            "priority": "medium"
        })

        # Risk score increase
        suggestions.append({
            "type": "alert",
            "title": "Your risk score increased by 5 points this week",
            "action": "See why",
            "priority": "low"
        })

        return suggestions

    def get_quick_stats(self, user_id: str) -> Dict[str, Any]:
        """Get quick stats for dashboard widget"""
        return {
            "risk_score": 65,
            "pending_approvals": 2,
            "open_violations": 3,
            "requests_in_progress": 1,
            "greeting": "Good morning, John! Here's your GRC summary."
        }
