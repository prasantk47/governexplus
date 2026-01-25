# Natural Language Policy Engine
# Query GRC data using natural language - no training required

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
from datetime import datetime
import re


class QueryType(Enum):
    """Types of natural language queries"""
    RISK_QUERY = "risk_query"           # "Show my risks"
    USER_QUERY = "user_query"           # "Who has SAP_ALL?"
    ACCESS_QUERY = "access_query"       # "What can John Smith access?"
    VIOLATION_QUERY = "violation_query" # "Show SoD violations in Finance"
    APPROVAL_QUERY = "approval_query"   # "What's pending my approval?"
    COMPARISON_QUERY = "comparison"     # "Compare Finance vs Sales risk"
    TREND_QUERY = "trend_query"         # "Show risk trend for last 30 days"
    ACTION_REQUEST = "action_request"   # "Create access request for..."
    HELP_QUERY = "help_query"           # "How do I..."
    REPORT_QUERY = "report_query"       # "Generate SOX report"


@dataclass
class PolicyIntent:
    """Parsed intent from natural language"""
    query_type: QueryType
    entities: Dict[str, Any]  # Extracted entities (user, role, dept, etc.)
    confidence: float
    original_query: str
    parsed_query: str  # Structured interpretation
    suggested_action: Optional[str] = None


@dataclass
class QueryResult:
    """Result of a natural language query"""
    success: bool
    intent: PolicyIntent
    data: Any
    summary: str  # Human-readable summary
    visualization_hint: Optional[str] = None  # "table", "chart", "list"
    follow_up_suggestions: List[str] = field(default_factory=list)
    executed_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class NaturalLanguageQuery:
    """Incoming natural language query"""
    text: str
    user_id: str  # Who is asking
    context: Dict[str, Any] = field(default_factory=dict)  # Conversation context


class NLPPolicyEngine:
    """
    Natural Language Policy Engine

    Allows users to interact with GRC using plain English:
    - "Show my SoD violations"
    - "Who in Finance has vendor master access?"
    - "What would happen if I gave John the AP_CLERK role?"
    - "Show me high-risk users trending up"

    Key advantages over traditional SAP GRC:
    1. Zero training required - just type naturally
    2. Context-aware - understands "my", "my team", etc.
    3. Actionable results - directly links to remediation
    4. Conversational - supports follow-up questions
    """

    def __init__(self):
        # Pattern matchers for intent detection
        self.intent_patterns: Dict[QueryType, List[re.Pattern]] = {}
        self.entity_extractors: Dict[str, Callable] = {}

        # Demo data for query responses
        self.demo_data = self._initialize_demo_data()

        # Conversation memory for follow-ups
        self.conversation_history: Dict[str, List[Dict]] = {}

        self._initialize_patterns()

    def _initialize_patterns(self):
        """Initialize regex patterns for intent matching"""
        self.intent_patterns = {
            QueryType.RISK_QUERY: [
                re.compile(r"(show|display|what are|list).*(risk|violation|conflict)", re.I),
                re.compile(r"my (risk|sod|access).*(score|level|status)", re.I),
                re.compile(r"(am i|do i have).*(risk|violation|conflict)", re.I),
            ],
            QueryType.USER_QUERY: [
                re.compile(r"who (has|have|can|is|are).*(access|role|permission)", re.I),
                re.compile(r"(users|people|employees).*(with|having|who have)", re.I),
                re.compile(r"(find|show|list).*(users|people).*(with|having)", re.I),
            ],
            QueryType.ACCESS_QUERY: [
                re.compile(r"what (can|does|access|permissions).*(have|access)", re.I),
                re.compile(r"(show|list|display).*access.*(for|of)", re.I),
                re.compile(r"what roles.*(does|has)", re.I),
            ],
            QueryType.VIOLATION_QUERY: [
                re.compile(r"(show|list|display).*(sod|violation|conflict)", re.I),
                re.compile(r"(sod|separation of duties).*(in|for|by)", re.I),
                re.compile(r"(conflicts|violations).*(department|team|user)", re.I),
            ],
            QueryType.APPROVAL_QUERY: [
                re.compile(r"(what|show|list).*(pending|waiting|need).*(approv|review)", re.I),
                re.compile(r"my (pending|approval|inbox)", re.I),
                re.compile(r"(requests|items).*(pending|waiting)", re.I),
            ],
            QueryType.COMPARISON_QUERY: [
                re.compile(r"compare.*(vs|versus|to|with|and)", re.I),
                re.compile(r"(difference|comparison).*(between|of)", re.I),
                re.compile(r"how does.*compare", re.I),
            ],
            QueryType.TREND_QUERY: [
                re.compile(r"(trend|trending|over time|history)", re.I),
                re.compile(r"(last|past|previous).*(days|weeks|months)", re.I),
                re.compile(r"(show|display).*over.*(time|period)", re.I),
            ],
            QueryType.ACTION_REQUEST: [
                re.compile(r"(create|submit|request|add).*(access|role|permission)", re.I),
                re.compile(r"(give|grant|assign).*(access|role|permission)", re.I),
                re.compile(r"(remove|revoke|delete).*(access|role|permission)", re.I),
            ],
            QueryType.REPORT_QUERY: [
                re.compile(r"(generate|create|run).*(report|audit)", re.I),
                re.compile(r"(sox|gdpr|compliance).*(report|audit)", re.I),
                re.compile(r"(export|download).*report", re.I),
            ],
            QueryType.HELP_QUERY: [
                re.compile(r"(how do i|how can i|help me|what is)", re.I),
                re.compile(r"(explain|tell me about|what does)", re.I),
            ],
        }

    def _initialize_demo_data(self) -> Dict[str, Any]:
        """Initialize demo data for query responses"""
        return {
            "users": {
                "JSMITH": {
                    "name": "John Smith",
                    "department": "Finance",
                    "risk_score": 65,
                    "violations": 3,
                    "roles": ["FI_AP_CLERK", "FI_AR_CLERK", "FI_GL_DISPLAY"]
                },
                "MBROWN": {
                    "name": "Mary Brown",
                    "department": "Procurement",
                    "risk_score": 42,
                    "violations": 1,
                    "roles": ["MM_BUYER", "MM_REQUISITIONER"]
                },
                "TDAVIS": {
                    "name": "Tom Davis",
                    "department": "IT",
                    "risk_score": 78,
                    "violations": 5,
                    "roles": ["BASIS_ADMIN", "SECURITY_ADMIN"]
                }
            },
            "pending_approvals": [
                {"id": "REQ001", "requester": "Alice Wilson", "type": "Role Request", "role": "FI_AP_MANAGER"},
                {"id": "REQ002", "requester": "Bob Johnson", "type": "Emergency Access", "system": "PRD"},
                {"id": "REQ003", "requester": "Carol White", "type": "Role Request", "role": "MM_BUYER"}
            ],
            "departments": {
                "Finance": {"avg_risk": 52, "users": 45, "high_risk": 8},
                "Procurement": {"avg_risk": 38, "users": 32, "high_risk": 4},
                "IT": {"avg_risk": 65, "users": 28, "high_risk": 12},
                "Sales": {"avg_risk": 28, "users": 120, "high_risk": 5}
            }
        }

    # ==================== Query Processing ====================

    def process_query(self, query: NaturalLanguageQuery) -> QueryResult:
        """
        Main entry point - process a natural language query

        1. Parse intent
        2. Extract entities
        3. Execute query
        4. Format response
        """
        # Store in conversation history
        if query.user_id not in self.conversation_history:
            self.conversation_history[query.user_id] = []
        self.conversation_history[query.user_id].append({
            "query": query.text,
            "timestamp": datetime.utcnow()
        })

        # Parse intent
        intent = self._parse_intent(query)

        # Handle context references (it, them, etc.)
        intent = self._resolve_context(intent, query)

        # Execute based on intent type
        result = self._execute_query(intent, query)

        return result

    def _parse_intent(self, query: NaturalLanguageQuery) -> PolicyIntent:
        """Parse intent from natural language query"""
        text = query.text.lower().strip()

        # Match against patterns
        best_match = QueryType.HELP_QUERY
        best_confidence = 0.3

        for query_type, patterns in self.intent_patterns.items():
            for pattern in patterns:
                if pattern.search(text):
                    confidence = 0.8  # Pattern match confidence
                    if confidence > best_confidence:
                        best_match = query_type
                        best_confidence = confidence
                    break

        # Extract entities
        entities = self._extract_entities(text, best_match)

        return PolicyIntent(
            query_type=best_match,
            entities=entities,
            confidence=best_confidence,
            original_query=query.text,
            parsed_query=self._generate_parsed_query(best_match, entities)
        )

    def _extract_entities(self, text: str, query_type: QueryType) -> Dict[str, Any]:
        """Extract entities from query text"""
        entities = {}

        # Extract user mentions
        user_pattern = re.compile(r"\b([A-Z][a-z]+ [A-Z][a-z]+)\b")
        user_matches = user_pattern.findall(text.title())
        if user_matches:
            entities["mentioned_users"] = user_matches

        # Extract departments
        dept_keywords = ["finance", "procurement", "it", "sales", "hr", "operations"]
        for dept in dept_keywords:
            if dept in text.lower():
                entities["department"] = dept.title()
                break

        # Extract roles
        role_pattern = re.compile(r"\b([A-Z_]+(?:_[A-Z]+)+)\b")
        role_matches = role_pattern.findall(text.upper())
        if role_matches:
            entities["roles"] = role_matches

        # Extract time references
        time_pattern = re.compile(r"(last|past)\s+(\d+)\s+(day|week|month)s?", re.I)
        time_match = time_pattern.search(text)
        if time_match:
            entities["time_range"] = {
                "value": int(time_match.group(2)),
                "unit": time_match.group(3)
            }

        # Detect self-reference
        if any(word in text.lower() for word in ["my", "me", "i ", "i'm"]):
            entities["self_reference"] = True

        # Detect team reference
        if any(word in text.lower() for word in ["my team", "my department", "my reports"]):
            entities["team_reference"] = True

        return entities

    def _generate_parsed_query(self, query_type: QueryType, entities: Dict) -> str:
        """Generate structured interpretation of query"""
        if query_type == QueryType.RISK_QUERY:
            if entities.get("self_reference"):
                return "SELECT risk_profile WHERE user = CURRENT_USER"
            elif entities.get("department"):
                return f"SELECT risk_profile WHERE department = '{entities['department']}'"
            return "SELECT risk_profile"

        elif query_type == QueryType.USER_QUERY:
            if entities.get("roles"):
                return f"SELECT users WHERE role IN {entities['roles']}"
            return "SELECT users"

        elif query_type == QueryType.APPROVAL_QUERY:
            return "SELECT pending_approvals WHERE approver = CURRENT_USER"

        return f"EXECUTE {query_type.value}"

    def _resolve_context(self, intent: PolicyIntent, query: NaturalLanguageQuery) -> PolicyIntent:
        """Resolve context references like 'it', 'them', etc."""
        history = self.conversation_history.get(query.user_id, [])

        # If query has pronouns and we have history, try to resolve
        pronouns = ["it", "them", "they", "that", "those"]
        if any(p in intent.original_query.lower() for p in pronouns):
            if len(history) > 1:
                # Look at previous query for context
                prev = history[-2]
                # In production, we'd do more sophisticated context resolution
                intent.entities["context_resolved"] = True

        return intent

    # ==================== Query Execution ====================

    def _execute_query(self, intent: PolicyIntent, query: NaturalLanguageQuery) -> QueryResult:
        """Execute query based on intent type"""
        handlers = {
            QueryType.RISK_QUERY: self._handle_risk_query,
            QueryType.USER_QUERY: self._handle_user_query,
            QueryType.ACCESS_QUERY: self._handle_access_query,
            QueryType.VIOLATION_QUERY: self._handle_violation_query,
            QueryType.APPROVAL_QUERY: self._handle_approval_query,
            QueryType.COMPARISON_QUERY: self._handle_comparison_query,
            QueryType.TREND_QUERY: self._handle_trend_query,
            QueryType.ACTION_REQUEST: self._handle_action_request,
            QueryType.REPORT_QUERY: self._handle_report_query,
            QueryType.HELP_QUERY: self._handle_help_query,
        }

        handler = handlers.get(intent.query_type, self._handle_help_query)
        return handler(intent, query)

    def _handle_risk_query(self, intent: PolicyIntent, query: NaturalLanguageQuery) -> QueryResult:
        """Handle risk-related queries"""
        entities = intent.entities

        if entities.get("self_reference"):
            # User asking about their own risk
            user_data = self.demo_data["users"].get("JSMITH")  # Demo: assume current user
            return QueryResult(
                success=True,
                intent=intent,
                data={
                    "risk_score": user_data["risk_score"],
                    "violations": user_data["violations"],
                    "trend": "increasing"
                },
                summary=f"Your current risk score is {user_data['risk_score']} "
                       f"with {user_data['violations']} active SoD violations. "
                       f"This is above the department average of 52.",
                visualization_hint="gauge",
                follow_up_suggestions=[
                    "Show me the details of my violations",
                    "How can I reduce my risk score?",
                    "Compare my risk to my peers"
                ]
            )

        elif entities.get("department"):
            dept = entities["department"]
            dept_data = self.demo_data["departments"].get(dept, {})
            return QueryResult(
                success=True,
                intent=intent,
                data=dept_data,
                summary=f"{dept} department has an average risk score of "
                       f"{dept_data.get('avg_risk', 'N/A')} across "
                       f"{dept_data.get('users', 'N/A')} users. "
                       f"{dept_data.get('high_risk', 0)} users are in high-risk status.",
                visualization_hint="bar_chart",
                follow_up_suggestions=[
                    f"Who are the high-risk users in {dept}?",
                    f"Show SoD violations in {dept}",
                    f"Compare {dept} to other departments"
                ]
            )

        # General risk query
        return QueryResult(
            success=True,
            intent=intent,
            data=self.demo_data["departments"],
            summary="Organization-wide risk summary: IT has the highest average risk (65), "
                   "followed by Finance (52), Procurement (38), and Sales (28).",
            visualization_hint="dashboard",
            follow_up_suggestions=[
                "Show me the IT department details",
                "Who are the top 10 highest risk users?",
                "Show risk trends over time"
            ]
        )

    def _handle_user_query(self, intent: PolicyIntent, query: NaturalLanguageQuery) -> QueryResult:
        """Handle user-related queries"""
        entities = intent.entities

        if entities.get("roles"):
            role = entities["roles"][0]
            # Find users with this role
            matching_users = [
                {"user": uid, "name": data["name"], "department": data["department"]}
                for uid, data in self.demo_data["users"].items()
                if role in data.get("roles", [])
            ]
            return QueryResult(
                success=True,
                intent=intent,
                data=matching_users,
                summary=f"Found {len(matching_users)} user(s) with role {role}.",
                visualization_hint="table",
                follow_up_suggestions=[
                    f"Show risks for users with {role}",
                    f"What permissions does {role} grant?",
                    f"Are there SoD conflicts with {role}?"
                ]
            )

        return QueryResult(
            success=True,
            intent=intent,
            data=list(self.demo_data["users"].values()),
            summary=f"Found {len(self.demo_data['users'])} users in the system.",
            visualization_hint="table",
            follow_up_suggestions=[
                "Show only high-risk users",
                "Filter by department",
                "Show users with SoD violations"
            ]
        )

    def _handle_access_query(self, intent: PolicyIntent, query: NaturalLanguageQuery) -> QueryResult:
        """Handle access-related queries"""
        mentioned_users = intent.entities.get("mentioned_users", [])

        if mentioned_users:
            name = mentioned_users[0]
            # Find user by name
            for uid, data in self.demo_data["users"].items():
                if data["name"].lower() == name.lower():
                    return QueryResult(
                        success=True,
                        intent=intent,
                        data={
                            "user": data["name"],
                            "roles": data["roles"],
                            "department": data["department"]
                        },
                        summary=f"{data['name']} has {len(data['roles'])} roles: "
                               f"{', '.join(data['roles'])}",
                        visualization_hint="list",
                        follow_up_suggestions=[
                            f"Show risks for {data['name']}",
                            f"What transactions can {data['name']} execute?",
                            f"Compare {data['name']} to peers"
                        ]
                    )

        return QueryResult(
            success=True,
            intent=intent,
            data={},
            summary="Please specify a user. For example: 'What access does John Smith have?'",
            visualization_hint=None,
            follow_up_suggestions=[
                "Show my access",
                "Show access for [user name]",
                "List all users with role [role name]"
            ]
        )

    def _handle_approval_query(self, intent: PolicyIntent, query: NaturalLanguageQuery) -> QueryResult:
        """Handle approval-related queries"""
        pending = self.demo_data["pending_approvals"]

        return QueryResult(
            success=True,
            intent=intent,
            data=pending,
            summary=f"You have {len(pending)} items pending your approval:\n" +
                   "\n".join([f"• {p['type']} from {p['requester']}" for p in pending]),
            visualization_hint="action_list",
            follow_up_suggestions=[
                "Show details for REQ001",
                "Approve all low-risk requests",
                "What's the risk for these requests?"
            ]
        )

    def _handle_comparison_query(self, intent: PolicyIntent, query: NaturalLanguageQuery) -> QueryResult:
        """Handle comparison queries"""
        text = intent.original_query.lower()

        # Extract departments to compare
        depts = []
        for dept in self.demo_data["departments"].keys():
            if dept.lower() in text:
                depts.append(dept)

        if len(depts) >= 2:
            d1, d2 = depts[0], depts[1]
            data1 = self.demo_data["departments"][d1]
            data2 = self.demo_data["departments"][d2]

            return QueryResult(
                success=True,
                intent=intent,
                data={d1: data1, d2: data2},
                summary=f"Comparison:\n"
                       f"• {d1}: Avg Risk {data1['avg_risk']}, {data1['high_risk']} high-risk users\n"
                       f"• {d2}: Avg Risk {data2['avg_risk']}, {data2['high_risk']} high-risk users",
                visualization_hint="comparison_chart",
                follow_up_suggestions=[
                    f"Why is {d1 if data1['avg_risk'] > data2['avg_risk'] else d2} riskier?",
                    f"Show high-risk users in {d1}",
                    "Compare all departments"
                ]
            )

        return QueryResult(
            success=True,
            intent=intent,
            data=self.demo_data["departments"],
            summary="All departments comparison:\n" +
                   "\n".join([f"• {d}: Risk {v['avg_risk']}"
                             for d, v in self.demo_data["departments"].items()]),
            visualization_hint="comparison_chart",
            follow_up_suggestions=[
                "Compare Finance vs IT",
                "Show trends for all departments",
                "Which department improved most?"
            ]
        )

    def _handle_trend_query(self, intent: PolicyIntent, query: NaturalLanguageQuery) -> QueryResult:
        """Handle trend queries"""
        time_range = intent.entities.get("time_range", {"value": 30, "unit": "day"})

        # Demo trend data
        trend_data = {
            "period": f"Last {time_range['value']} {time_range['unit']}s",
            "data_points": [
                {"date": "Week 1", "risk": 52},
                {"date": "Week 2", "risk": 55},
                {"date": "Week 3", "risk": 53},
                {"date": "Week 4", "risk": 58}
            ],
            "trend": "slightly_increasing",
            "change": "+6 points"
        }

        return QueryResult(
            success=True,
            intent=intent,
            data=trend_data,
            summary=f"Risk trend over {trend_data['period']}:\n"
                   f"Overall risk has increased by 6 points, primarily driven by "
                   f"new role assignments in IT department.",
            visualization_hint="line_chart",
            follow_up_suggestions=[
                "What caused the increase?",
                "Show IT department trend",
                "Who contributed most to the increase?"
            ]
        )

    def _handle_action_request(self, intent: PolicyIntent, query: NaturalLanguageQuery) -> QueryResult:
        """Handle action requests (create, submit, etc.)"""
        text = intent.original_query.lower()

        if "request" in text or "create" in text:
            return QueryResult(
                success=True,
                intent=intent,
                data={"action": "create_request"},
                summary="I can help you create an access request. What role or access do you need?\n\n"
                       "You can say things like:\n"
                       "• 'I need access to create purchase orders'\n"
                       "• 'Request the FI_AP_CLERK role'\n"
                       "• 'I need the same access as John Smith'",
                visualization_hint="form",
                follow_up_suggestions=[
                    "Show available roles",
                    "What access does my team have?",
                    "Show my pending requests"
                ]
            )

        return QueryResult(
            success=True,
            intent=intent,
            data={},
            summary="What action would you like to take? I can help you:\n"
                   "• Create an access request\n"
                   "• Submit for approval\n"
                   "• Revoke access",
            visualization_hint=None,
            follow_up_suggestions=[
                "Create access request",
                "Review and approve requests",
                "Revoke role for user"
            ]
        )

    def _handle_report_query(self, intent: PolicyIntent, query: NaturalLanguageQuery) -> QueryResult:
        """Handle report generation queries"""
        text = intent.original_query.lower()

        if "sox" in text:
            report_type = "SOX Compliance"
        elif "gdpr" in text:
            report_type = "GDPR Compliance"
        else:
            report_type = "Risk Summary"

        return QueryResult(
            success=True,
            intent=intent,
            data={
                "report_type": report_type,
                "status": "ready",
                "download_link": f"/reports/{report_type.lower().replace(' ', '_')}_report.pdf"
            },
            summary=f"Generating {report_type} Report...\n\n"
                   f"Report Contents:\n"
                   f"• Executive Summary\n"
                   f"• Risk Analysis by Department\n"
                   f"• SoD Violations (125 total)\n"
                   f"• Remediation Status\n"
                   f"• Audit Trail",
            visualization_hint="download",
            follow_up_suggestions=[
                "Schedule this report weekly",
                "Email report to compliance team",
                "Show violations that need attention"
            ]
        )

    def _handle_help_query(self, intent: PolicyIntent, query: NaturalLanguageQuery) -> QueryResult:
        """Handle help queries"""
        return QueryResult(
            success=True,
            intent=intent,
            data={"type": "help"},
            summary="I can help you with:\n\n"
                   "**Risk & Compliance:**\n"
                   "• 'Show my risk score'\n"
                   "• 'Who has SoD violations in Finance?'\n"
                   "• 'Compare departments'\n\n"
                   "**Access Management:**\n"
                   "• 'What access does John Smith have?'\n"
                   "• 'Create access request'\n"
                   "• 'Show my pending approvals'\n\n"
                   "**Reports:**\n"
                   "• 'Generate SOX report'\n"
                   "• 'Show risk trends'\n\n"
                   "Just type naturally - I'll understand!",
            visualization_hint="help",
            follow_up_suggestions=[
                "Show my risks",
                "What's pending my approval?",
                "Show organization risk summary"
            ]
        )

    # ==================== Convenience Methods ====================

    def quick_query(self, text: str, user_id: str = "CURRENT_USER") -> Dict[str, Any]:
        """Convenience method for quick queries"""
        query = NaturalLanguageQuery(text=text, user_id=user_id)
        result = self.process_query(query)

        return {
            "query": text,
            "understood_as": result.intent.query_type.value,
            "confidence": result.intent.confidence,
            "summary": result.summary,
            "data": result.data,
            "suggestions": result.follow_up_suggestions
        }

    def get_suggestions_for_context(self, user_id: str) -> List[str]:
        """Get contextual suggestions based on user's situation"""
        # In production, this would analyze user's current state
        return [
            "Show my pending approvals",
            "What's my risk score?",
            "Show SoD violations in my team",
            "Generate weekly compliance report"
        ]
