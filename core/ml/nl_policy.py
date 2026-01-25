"""
Natural Language Policy Builder

Converts natural language descriptions into structured GRC policies
using pattern matching, entity extraction, and rule templates.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any, Set
from datetime import datetime
from enum import Enum
import re
import uuid


class PolicyIntent(Enum):
    """Detected policy intents from natural language"""
    CREATE_SOD_RULE = "create_sod_rule"
    CREATE_SENSITIVE_RULE = "create_sensitive_rule"
    CREATE_APPROVAL_WORKFLOW = "create_approval_workflow"
    CREATE_CERTIFICATION_POLICY = "create_certification_policy"
    CREATE_ACCESS_POLICY = "create_access_policy"
    CREATE_FIREFIGHTER_POLICY = "create_firefighter_policy"
    MODIFY_POLICY = "modify_policy"
    QUERY_POLICY = "query_policy"
    UNKNOWN = "unknown"


class EntityType(Enum):
    """Types of entities extracted from text"""
    TRANSACTION = "transaction"
    ROLE = "role"
    PERMISSION = "permission"
    DEPARTMENT = "department"
    JOB_TITLE = "job_title"
    USER = "user"
    SYSTEM = "system"
    RISK_LEVEL = "risk_level"
    TIME_PERIOD = "time_period"
    APPROVAL_LEVEL = "approval_level"
    ACTION = "action"
    CONDITION = "condition"


@dataclass
class ExtractedEntity:
    """An entity extracted from natural language"""
    entity_type: EntityType
    value: str
    original_text: str
    confidence: float = 0.0
    position: Tuple[int, int] = (0, 0)  # Start, end position in text

    def to_dict(self) -> Dict:
        return {
            "type": self.entity_type.value,
            "value": self.value,
            "original_text": self.original_text,
            "confidence": round(self.confidence, 2)
        }


@dataclass
class ParsedPolicy:
    """A policy parsed from natural language"""
    parse_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    original_text: str = ""
    intent: PolicyIntent = PolicyIntent.UNKNOWN

    # Extracted components
    entities: List[ExtractedEntity] = field(default_factory=list)
    policy_name: str = ""
    policy_description: str = ""

    # Structured output
    structured_policy: Dict[str, Any] = field(default_factory=dict)

    # Confidence and quality
    overall_confidence: float = 0.0
    ambiguities: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)

    # Status
    is_complete: bool = False
    missing_elements: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "parse_id": self.parse_id,
            "original_text": self.original_text,
            "intent": self.intent.value,
            "entities": [e.to_dict() for e in self.entities],
            "policy_name": self.policy_name,
            "policy_description": self.policy_description,
            "structured_policy": self.structured_policy,
            "overall_confidence": round(self.overall_confidence, 2),
            "ambiguities": self.ambiguities,
            "suggestions": self.suggestions,
            "is_complete": self.is_complete,
            "missing_elements": self.missing_elements
        }


@dataclass
class PolicyTemplate:
    """Template for generating policies from NL"""
    template_id: str
    name: str
    intent: PolicyIntent
    required_entities: List[EntityType]
    optional_entities: List[EntityType]
    output_schema: Dict[str, Any]
    examples: List[str] = field(default_factory=list)


class NLPolicyBuilder:
    """
    Natural Language Policy Builder.

    Converts natural language descriptions into structured GRC policies.
    Uses pattern matching, keyword extraction, and templates.
    """

    # Transaction code patterns
    TCODE_PATTERN = re.compile(r'\b([A-Z]{2,4}\d{2,3}[A-Z]?|[A-Z]+_[A-Z0-9_]+)\b')

    # Common SAP transactions
    SAP_TCODES = {
        # Finance
        "FB01": "Post Document", "FB02": "Change Document", "FB03": "Display Document",
        "F110": "Payment Run", "FK01": "Create Vendor", "FK02": "Change Vendor",
        "XK01": "Create Vendor Central", "XK02": "Change Vendor Central",
        "FBL1N": "Vendor Line Items", "FBL3N": "G/L Line Items", "FBL5N": "Customer Line Items",
        # Procurement
        "ME21N": "Create PO", "ME22N": "Change PO", "ME23N": "Display PO",
        "ME51N": "Create PR", "ME52N": "Change PR", "ME53N": "Display PR",
        "MIGO": "Goods Movement", "MB01": "Goods Receipt",
        # HR
        "PA20": "Display HR Master", "PA30": "Maintain HR Master", "PA40": "Personnel Actions",
        # Basis
        "SU01": "User Maintenance", "PFCG": "Role Maintenance",
        "SE38": "ABAP Editor", "SE16": "Data Browser", "SM59": "RFC Destinations",
    }

    # Risk level keywords
    RISK_KEYWORDS = {
        "critical": ["critical", "highest", "severe", "emergency", "urgent"],
        "high": ["high", "major", "significant", "important"],
        "medium": ["medium", "moderate", "standard", "normal"],
        "low": ["low", "minor", "minimal", "basic"]
    }

    # Department keywords
    DEPARTMENT_KEYWORDS = {
        "finance": ["finance", "financial", "accounting", "treasury", "fp&a"],
        "procurement": ["procurement", "purchasing", "buying", "supply chain", "sourcing"],
        "hr": ["hr", "human resources", "personnel", "payroll", "talent"],
        "it": ["it", "information technology", "technical", "systems", "infrastructure"],
        "sales": ["sales", "commercial", "revenue", "business development"],
        "operations": ["operations", "manufacturing", "production", "logistics"]
    }

    # Action keywords for SoD
    SOD_ACTION_KEYWORDS = {
        "create": ["create", "add", "new", "insert", "post", "book"],
        "approve": ["approve", "release", "authorize", "sign off", "confirm"],
        "modify": ["modify", "change", "edit", "update", "alter"],
        "delete": ["delete", "remove", "cancel", "void"],
        "display": ["display", "view", "read", "show", "list"],
        "execute": ["execute", "run", "process", "perform"]
    }

    # Intent detection patterns
    INTENT_PATTERNS = {
        PolicyIntent.CREATE_SOD_RULE: [
            r"segregat\w*\s+of\s+dut\w*",
            r"sod\s+rule",
            r"cannot\s+both",
            r"should\s+not\s+be\s+able\s+to\s+.*\s+and\s+",
            r"separate\s+.*\s+from\s+",
            r"conflict\s+between",
            r"incompatible\s+functions?"
        ],
        PolicyIntent.CREATE_SENSITIVE_RULE: [
            r"sensitive\s+access",
            r"restrict\w*\s+access",
            r"privileged\s+access",
            r"critical\s+transaction",
            r"high\s+risk\s+access"
        ],
        PolicyIntent.CREATE_APPROVAL_WORKFLOW: [
            r"approval\s+workflow",
            r"require\s+.*\s+approval",
            r"needs?\s+.*\s+sign[\s-]?off",
            r"must\s+be\s+approved",
            r"escalat\w*\s+to"
        ],
        PolicyIntent.CREATE_CERTIFICATION_POLICY: [
            r"certif\w*\s+campaign",
            r"access\s+review",
            r"periodic\s+review",
            r"attestation",
            r"recertif\w*"
        ],
        PolicyIntent.CREATE_ACCESS_POLICY: [
            r"access\s+policy",
            r"grant\w*\s+access",
            r"provision\w*\s+access",
            r"role\s+assignment"
        ],
        PolicyIntent.CREATE_FIREFIGHTER_POLICY: [
            r"firefighter",
            r"emergency\s+access",
            r"break[\s-]?glass",
            r"privileged\s+session"
        ]
    }

    def __init__(self):
        self.templates = self._create_templates()
        self.parse_history: List[ParsedPolicy] = []

    def _create_templates(self) -> Dict[str, PolicyTemplate]:
        """Create policy templates"""
        templates = {}

        # SoD Rule Template
        templates["sod_rule"] = PolicyTemplate(
            template_id="sod_rule",
            name="Segregation of Duties Rule",
            intent=PolicyIntent.CREATE_SOD_RULE,
            required_entities=[EntityType.TRANSACTION, EntityType.ACTION],
            optional_entities=[EntityType.RISK_LEVEL, EntityType.DEPARTMENT],
            output_schema={
                "rule_type": "sod",
                "function_1": {"name": "", "permissions": []},
                "function_2": {"name": "", "permissions": []},
                "severity": "high",
                "business_process": "",
                "remediation": ""
            },
            examples=[
                "Users who can create vendors should not be able to process payments",
                "Separate purchase order creation from goods receipt",
                "No user should have both ME21N and MIGO access"
            ]
        )

        # Sensitive Access Template
        templates["sensitive_rule"] = PolicyTemplate(
            template_id="sensitive_rule",
            name="Sensitive Access Rule",
            intent=PolicyIntent.CREATE_SENSITIVE_RULE,
            required_entities=[EntityType.TRANSACTION],
            optional_entities=[EntityType.RISK_LEVEL, EntityType.APPROVAL_LEVEL],
            output_schema={
                "rule_type": "sensitive",
                "permissions": [],
                "severity": "high",
                "requires_approval": True,
                "review_frequency": "quarterly"
            },
            examples=[
                "SE38 access is critical and should be restricted",
                "SM59 RFC maintenance requires special approval"
            ]
        )

        # Approval Workflow Template
        templates["approval_workflow"] = PolicyTemplate(
            template_id="approval_workflow",
            name="Approval Workflow",
            intent=PolicyIntent.CREATE_APPROVAL_WORKFLOW,
            required_entities=[EntityType.APPROVAL_LEVEL],
            optional_entities=[EntityType.RISK_LEVEL, EntityType.DEPARTMENT, EntityType.ROLE],
            output_schema={
                "workflow_type": "approval",
                "trigger_conditions": [],
                "approval_levels": [],
                "sla_hours": 48,
                "escalation_rules": []
            },
            examples=[
                "High risk access requests require manager and security approval",
                "All firefighter requests need dual approval"
            ]
        )

        return templates

    def parse(self, text: str) -> ParsedPolicy:
        """
        Parse natural language text into a structured policy.

        Args:
            text: Natural language policy description

        Returns:
            ParsedPolicy with extracted entities and structured output
        """
        parsed = ParsedPolicy(original_text=text)

        # Normalize text
        normalized = text.lower().strip()

        # Detect intent
        parsed.intent = self._detect_intent(normalized)

        # Extract entities
        parsed.entities = self._extract_entities(text, normalized)

        # Generate policy name
        parsed.policy_name = self._generate_policy_name(parsed)

        # Build structured policy based on intent
        if parsed.intent == PolicyIntent.CREATE_SOD_RULE:
            self._build_sod_rule(parsed)
        elif parsed.intent == PolicyIntent.CREATE_SENSITIVE_RULE:
            self._build_sensitive_rule(parsed)
        elif parsed.intent == PolicyIntent.CREATE_APPROVAL_WORKFLOW:
            self._build_approval_workflow(parsed)
        elif parsed.intent == PolicyIntent.CREATE_CERTIFICATION_POLICY:
            self._build_certification_policy(parsed)
        elif parsed.intent == PolicyIntent.CREATE_FIREFIGHTER_POLICY:
            self._build_firefighter_policy(parsed)
        else:
            self._build_generic_policy(parsed)

        # Validate completeness
        self._validate_completeness(parsed)

        # Calculate confidence
        parsed.overall_confidence = self._calculate_confidence(parsed)

        # Generate suggestions
        self._generate_suggestions(parsed)

        self.parse_history.append(parsed)
        return parsed

    def _detect_intent(self, text: str) -> PolicyIntent:
        """Detect the intent from the text"""
        scores = {}

        for intent, patterns in self.INTENT_PATTERNS.items():
            score = 0
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    score += 1
            scores[intent] = score

        if max(scores.values()) > 0:
            return max(scores, key=scores.get)

        return PolicyIntent.UNKNOWN

    def _extract_entities(self, original: str, normalized: str) -> List[ExtractedEntity]:
        """Extract all entities from text"""
        entities = []

        # Extract transaction codes
        entities.extend(self._extract_transactions(original))

        # Extract risk levels
        entities.extend(self._extract_risk_levels(normalized))

        # Extract departments
        entities.extend(self._extract_departments(normalized))

        # Extract actions
        entities.extend(self._extract_actions(normalized))

        # Extract time periods
        entities.extend(self._extract_time_periods(normalized))

        # Extract approval levels
        entities.extend(self._extract_approval_levels(normalized))

        # Extract roles
        entities.extend(self._extract_roles(original))

        return entities

    def _extract_transactions(self, text: str) -> List[ExtractedEntity]:
        """Extract SAP transaction codes"""
        entities = []

        # Pattern match
        for match in self.TCODE_PATTERN.finditer(text):
            tcode = match.group(1).upper()
            if tcode in self.SAP_TCODES or re.match(r'^[A-Z]{2,4}\d{2,3}[A-Z]?$', tcode):
                entities.append(ExtractedEntity(
                    entity_type=EntityType.TRANSACTION,
                    value=tcode,
                    original_text=match.group(0),
                    confidence=0.95 if tcode in self.SAP_TCODES else 0.7,
                    position=(match.start(), match.end())
                ))

        # Look for transaction descriptions
        tcode_descriptions = {
            "create vendor": ["XK01", "FK01"],
            "change vendor": ["XK02", "FK02"],
            "payment run": ["F110"],
            "post document": ["FB01"],
            "create purchase order": ["ME21N"],
            "create po": ["ME21N"],
            "change purchase order": ["ME22N"],
            "change po": ["ME22N"],
            "goods receipt": ["MIGO", "MB01"],
            "user maintenance": ["SU01"],
            "role maintenance": ["PFCG"],
            "abap editor": ["SE38"],
            "data browser": ["SE16", "SE16N"]
        }

        lower_text = text.lower()
        for desc, tcodes in tcode_descriptions.items():
            if desc in lower_text:
                for tcode in tcodes:
                    # Check if already extracted
                    if not any(e.value == tcode for e in entities):
                        entities.append(ExtractedEntity(
                            entity_type=EntityType.TRANSACTION,
                            value=tcode,
                            original_text=desc,
                            confidence=0.85
                        ))

        return entities

    def _extract_risk_levels(self, text: str) -> List[ExtractedEntity]:
        """Extract risk level mentions"""
        entities = []

        for level, keywords in self.RISK_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text:
                    entities.append(ExtractedEntity(
                        entity_type=EntityType.RISK_LEVEL,
                        value=level,
                        original_text=keyword,
                        confidence=0.9
                    ))
                    break  # One per level

        return entities

    def _extract_departments(self, text: str) -> List[ExtractedEntity]:
        """Extract department mentions"""
        entities = []

        for dept, keywords in self.DEPARTMENT_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text:
                    entities.append(ExtractedEntity(
                        entity_type=EntityType.DEPARTMENT,
                        value=dept,
                        original_text=keyword,
                        confidence=0.85
                    ))
                    break

        return entities

    def _extract_actions(self, text: str) -> List[ExtractedEntity]:
        """Extract action mentions (create, approve, etc.)"""
        entities = []

        for action, keywords in self.SOD_ACTION_KEYWORDS.items():
            for keyword in keywords:
                pattern = rf'\b{keyword}\b'
                if re.search(pattern, text):
                    entities.append(ExtractedEntity(
                        entity_type=EntityType.ACTION,
                        value=action,
                        original_text=keyword,
                        confidence=0.8
                    ))
                    break

        return entities

    def _extract_time_periods(self, text: str) -> List[ExtractedEntity]:
        """Extract time period mentions"""
        entities = []

        patterns = {
            "daily": r'\bdaily\b',
            "weekly": r'\bweekly\b',
            "monthly": r'\bmonthly\b',
            "quarterly": r'\bquarterly\b',
            "annually": r'\b(annually|yearly|annual)\b',
            "24_hours": r'\b24\s*hours?\b',
            "48_hours": r'\b48\s*hours?\b',
            "7_days": r'\b7\s*days?\b',
            "30_days": r'\b30\s*days?\b',
            "90_days": r'\b90\s*days?\b'
        }

        for period, pattern in patterns.items():
            if re.search(pattern, text, re.IGNORECASE):
                entities.append(ExtractedEntity(
                    entity_type=EntityType.TIME_PERIOD,
                    value=period,
                    original_text=re.search(pattern, text, re.IGNORECASE).group(0),
                    confidence=0.9
                ))

        return entities

    def _extract_approval_levels(self, text: str) -> List[ExtractedEntity]:
        """Extract approval level mentions"""
        entities = []

        approval_patterns = {
            "manager": r'\bmanager\b',
            "director": r'\bdirector\b',
            "vp": r'\b(vp|vice\s*president)\b',
            "ciso": r'\bciso\b',
            "security": r'\bsecurity\s*(team|admin|officer)?\b',
            "hr": r'\bhr\s*(team|admin)?\b',
            "dual": r'\bdual\s*approval\b',
            "it": r'\bit\s*(team|admin)?\b'
        }

        for level, pattern in approval_patterns.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                entities.append(ExtractedEntity(
                    entity_type=EntityType.APPROVAL_LEVEL,
                    value=level,
                    original_text=match.group(0),
                    confidence=0.85
                ))

        return entities

    def _extract_roles(self, text: str) -> List[ExtractedEntity]:
        """Extract role mentions"""
        entities = []

        # Pattern for SAP role names (Z_*, Y_*)
        role_pattern = re.compile(r'\b([ZY]_[A-Z0-9_]+)\b')

        for match in role_pattern.finditer(text):
            entities.append(ExtractedEntity(
                entity_type=EntityType.ROLE,
                value=match.group(1),
                original_text=match.group(0),
                confidence=0.9,
                position=(match.start(), match.end())
            ))

        return entities

    def _generate_policy_name(self, parsed: ParsedPolicy) -> str:
        """Generate a policy name from extracted entities"""
        parts = []

        # Get key entities
        transactions = [e.value for e in parsed.entities if e.entity_type == EntityType.TRANSACTION]
        departments = [e.value for e in parsed.entities if e.entity_type == EntityType.DEPARTMENT]
        actions = [e.value for e in parsed.entities if e.entity_type == EntityType.ACTION]

        if parsed.intent == PolicyIntent.CREATE_SOD_RULE:
            if actions and len(actions) >= 2:
                parts.append(f"SoD-{actions[0].title()}-vs-{actions[1].title()}")
            elif transactions and len(transactions) >= 2:
                parts.append(f"SoD-{transactions[0]}-{transactions[1]}")
            else:
                parts.append("SoD-Rule")

        elif parsed.intent == PolicyIntent.CREATE_SENSITIVE_RULE:
            if transactions:
                parts.append(f"Sensitive-{transactions[0]}")
            else:
                parts.append("Sensitive-Access")

        elif parsed.intent == PolicyIntent.CREATE_APPROVAL_WORKFLOW:
            if departments:
                parts.append(f"Approval-{departments[0].title()}")
            else:
                parts.append("Approval-Workflow")

        else:
            parts.append("Policy")

        # Add department if available
        if departments and "Approval" not in parts[0]:
            parts.append(departments[0].upper())

        return "-".join(parts)

    def _build_sod_rule(self, parsed: ParsedPolicy):
        """Build a structured SoD rule"""
        transactions = [e for e in parsed.entities if e.entity_type == EntityType.TRANSACTION]
        actions = [e for e in parsed.entities if e.entity_type == EntityType.ACTION]
        risk_levels = [e for e in parsed.entities if e.entity_type == EntityType.RISK_LEVEL]
        departments = [e for e in parsed.entities if e.entity_type == EntityType.DEPARTMENT]

        # Build functions from transactions and actions
        function_1 = {"name": "", "permissions": [], "actions": []}
        function_2 = {"name": "", "permissions": [], "actions": []}

        # Try to split transactions between functions
        if len(transactions) >= 2:
            mid = len(transactions) // 2
            function_1["permissions"] = [t.value for t in transactions[:mid]]
            function_2["permissions"] = [t.value for t in transactions[mid:]]

            # Name functions based on transactions
            function_1["name"] = self._get_function_name(function_1["permissions"])
            function_2["name"] = self._get_function_name(function_2["permissions"])

        elif len(transactions) == 1 and len(actions) >= 2:
            # Split by actions
            function_1["permissions"] = [transactions[0].value]
            function_1["actions"] = [actions[0].value]
            function_1["name"] = f"{actions[0].value.title()} Function"

            function_2["permissions"] = [transactions[0].value]
            function_2["actions"] = [actions[1].value]
            function_2["name"] = f"{actions[1].value.title()} Function"

        elif len(actions) >= 2:
            function_1["actions"] = [actions[0].value]
            function_1["name"] = f"{actions[0].value.title()} Function"

            function_2["actions"] = [actions[1].value]
            function_2["name"] = f"{actions[1].value.title()} Function"

        parsed.structured_policy = {
            "rule_type": "sod",
            "rule_id": f"SOD-{parsed.parse_id.upper()}",
            "name": parsed.policy_name,
            "description": parsed.original_text,
            "function_1": function_1,
            "function_2": function_2,
            "severity": risk_levels[0].value if risk_levels else "high",
            "business_process": departments[0].value.title() if departments else "",
            "is_active": True,
            "remediation": "Segregate responsibilities between different users"
        }

        parsed.policy_description = f"Segregation of Duties rule preventing {function_1['name']} and {function_2['name']} from being combined"

    def _build_sensitive_rule(self, parsed: ParsedPolicy):
        """Build a structured sensitive access rule"""
        transactions = [e for e in parsed.entities if e.entity_type == EntityType.TRANSACTION]
        risk_levels = [e for e in parsed.entities if e.entity_type == EntityType.RISK_LEVEL]
        approvals = [e for e in parsed.entities if e.entity_type == EntityType.APPROVAL_LEVEL]

        parsed.structured_policy = {
            "rule_type": "sensitive",
            "rule_id": f"SENS-{parsed.parse_id.upper()}",
            "name": parsed.policy_name,
            "description": parsed.original_text,
            "permissions": [
                {
                    "auth_object": "S_TCODE",
                    "field": "TCD",
                    "values": [t.value for t in transactions]
                }
            ] if transactions else [],
            "severity": risk_levels[0].value if risk_levels else "high",
            "requires_approval": len(approvals) > 0,
            "approval_levels": [a.value for a in approvals],
            "review_frequency": "quarterly",
            "is_active": True
        }

        parsed.policy_description = f"Sensitive access rule for transactions: {', '.join(t.value for t in transactions)}"

    def _build_approval_workflow(self, parsed: ParsedPolicy):
        """Build a structured approval workflow"""
        approvals = [e for e in parsed.entities if e.entity_type == EntityType.APPROVAL_LEVEL]
        risk_levels = [e for e in parsed.entities if e.entity_type == EntityType.RISK_LEVEL]
        departments = [e for e in parsed.entities if e.entity_type == EntityType.DEPARTMENT]
        time_periods = [e for e in parsed.entities if e.entity_type == EntityType.TIME_PERIOD]

        # Build approval levels
        levels = []
        for i, approval in enumerate(approvals):
            levels.append({
                "level": i + 1,
                "type": approval.value,
                "required": True,
                "auto_approve_after_hours": None
            })

        # Determine SLA
        sla_hours = 48
        for tp in time_periods:
            if tp.value == "24_hours":
                sla_hours = 24
            elif tp.value == "48_hours":
                sla_hours = 48
            elif tp.value == "7_days":
                sla_hours = 168

        parsed.structured_policy = {
            "workflow_type": "approval",
            "workflow_id": f"WF-{parsed.parse_id.upper()}",
            "name": parsed.policy_name,
            "description": parsed.original_text,
            "trigger_conditions": {
                "risk_level": risk_levels[0].value if risk_levels else "high",
                "departments": [d.value for d in departments]
            },
            "approval_levels": levels if levels else [
                {"level": 1, "type": "manager", "required": True}
            ],
            "sla_hours": sla_hours,
            "escalation_rules": [
                {
                    "after_hours": sla_hours // 2,
                    "escalate_to": "next_level"
                }
            ],
            "is_active": True
        }

        parsed.policy_description = f"Approval workflow requiring {len(levels)} level(s) of approval"

    def _build_certification_policy(self, parsed: ParsedPolicy):
        """Build a structured certification policy"""
        time_periods = [e for e in parsed.entities if e.entity_type == EntityType.TIME_PERIOD]
        departments = [e for e in parsed.entities if e.entity_type == EntityType.DEPARTMENT]
        approvals = [e for e in parsed.entities if e.entity_type == EntityType.APPROVAL_LEVEL]

        # Determine frequency
        frequency = "quarterly"
        for tp in time_periods:
            if tp.value in ["monthly", "quarterly", "annually"]:
                frequency = tp.value

        parsed.structured_policy = {
            "policy_type": "certification",
            "policy_id": f"CERT-{parsed.parse_id.upper()}",
            "name": parsed.policy_name,
            "description": parsed.original_text,
            "certification_type": "user_access",
            "frequency": frequency,
            "scope": {
                "departments": [d.value for d in departments],
                "include_all_users": len(departments) == 0
            },
            "reviewer": approvals[0].value if approvals else "manager",
            "reminder_days_before": 7,
            "escalation_days": 3,
            "is_active": True
        }

        parsed.policy_description = f"Certification policy requiring {frequency} access review"

    def _build_firefighter_policy(self, parsed: ParsedPolicy):
        """Build a structured firefighter policy"""
        time_periods = [e for e in parsed.entities if e.entity_type == EntityType.TIME_PERIOD]
        approvals = [e for e in parsed.entities if e.entity_type == EntityType.APPROVAL_LEVEL]
        transactions = [e for e in parsed.entities if e.entity_type == EntityType.TRANSACTION]

        # Determine max duration
        max_hours = 4
        for tp in time_periods:
            if tp.value == "24_hours":
                max_hours = 24
            elif tp.value == "48_hours":
                max_hours = 48

        parsed.structured_policy = {
            "policy_type": "firefighter",
            "policy_id": f"FF-{parsed.parse_id.upper()}",
            "name": parsed.policy_name,
            "description": parsed.original_text,
            "max_duration_hours": max_hours,
            "max_extensions": 2,
            "requires_approval": True,
            "requires_dual_approval": any(a.value == "dual" for a in approvals),
            "approvers": [a.value for a in approvals if a.value != "dual"] or ["manager", "security"],
            "mandatory_post_review": True,
            "review_sla_hours": 48,
            "restricted_transactions": [t.value for t in transactions],
            "activity_logging": "comprehensive",
            "is_active": True
        }

        parsed.policy_description = f"Firefighter policy with {max_hours} hour maximum duration"

    def _build_generic_policy(self, parsed: ParsedPolicy):
        """Build a generic policy when intent is unclear"""
        parsed.structured_policy = {
            "policy_type": "custom",
            "policy_id": f"POL-{parsed.parse_id.upper()}",
            "name": parsed.policy_name or "Custom Policy",
            "description": parsed.original_text,
            "entities": [e.to_dict() for e in parsed.entities],
            "requires_manual_review": True
        }

        parsed.ambiguities.append("Policy type could not be determined automatically")

    def _get_function_name(self, transactions: List[str]) -> str:
        """Get a human-readable function name from transactions"""
        if not transactions:
            return "Unknown Function"

        # Map common transaction groups to names
        function_names = {
            frozenset(["XK01", "FK01", "XK02", "FK02"]): "Vendor Management",
            frozenset(["F110", "FB10", "F-53"]): "Payment Processing",
            frozenset(["ME21N", "ME22N"]): "Purchase Order Creation",
            frozenset(["MIGO", "MB01"]): "Goods Receipt",
            frozenset(["PA30", "PA40"]): "HR Maintenance",
            frozenset(["SU01", "PFCG"]): "User Administration"
        }

        tcode_set = frozenset(transactions)
        for key, name in function_names.items():
            if tcode_set & key:
                return name

        # Use transaction description
        if transactions[0] in self.SAP_TCODES:
            return self.SAP_TCODES[transactions[0]]

        return f"Function ({', '.join(transactions)})"

    def _validate_completeness(self, parsed: ParsedPolicy):
        """Validate if the parsed policy is complete"""
        parsed.missing_elements = []

        template = self.templates.get(parsed.intent.value.replace("create_", ""))
        if not template:
            parsed.is_complete = len(parsed.entities) > 0
            return

        # Check required entities
        entity_types = {e.entity_type for e in parsed.entities}
        for required in template.required_entities:
            if required not in entity_types:
                parsed.missing_elements.append(required.value)

        parsed.is_complete = len(parsed.missing_elements) == 0

    def _calculate_confidence(self, parsed: ParsedPolicy) -> float:
        """Calculate overall confidence score"""
        if not parsed.entities:
            return 0.1

        # Base confidence from entity confidences
        entity_conf = sum(e.confidence for e in parsed.entities) / len(parsed.entities)

        # Adjust for intent detection
        intent_conf = 0.9 if parsed.intent != PolicyIntent.UNKNOWN else 0.3

        # Adjust for completeness
        complete_conf = 1.0 if parsed.is_complete else 0.7

        # Weighted average
        return entity_conf * 0.5 + intent_conf * 0.3 + complete_conf * 0.2

    def _generate_suggestions(self, parsed: ParsedPolicy):
        """Generate suggestions for improving the policy"""

        if not parsed.is_complete:
            for missing in parsed.missing_elements:
                if missing == EntityType.TRANSACTION.value:
                    parsed.suggestions.append(
                        "Add specific transaction codes (e.g., ME21N, FB01) for more precise policy"
                    )
                elif missing == EntityType.ACTION.value:
                    parsed.suggestions.append(
                        "Specify the actions to segregate (e.g., create, approve, modify)"
                    )

        if parsed.overall_confidence < 0.7:
            parsed.suggestions.append(
                "Consider rephrasing with more specific terms for better accuracy"
            )

        if parsed.intent == PolicyIntent.CREATE_SOD_RULE:
            transactions = [e for e in parsed.entities if e.entity_type == EntityType.TRANSACTION]
            if len(transactions) < 2:
                parsed.suggestions.append(
                    "SoD rules typically need at least 2 conflicting transactions or functions"
                )

        if not any(e.entity_type == EntityType.RISK_LEVEL for e in parsed.entities):
            parsed.suggestions.append(
                "Consider specifying a risk level (critical, high, medium, low)"
            )

    def refine_policy(self, parse_id: str, refinements: Dict) -> ParsedPolicy:
        """Refine a parsed policy with additional information"""
        # Find the original parse
        original = next((p for p in self.parse_history if p.parse_id == parse_id), None)
        if not original:
            raise ValueError(f"Parse {parse_id} not found")

        # Apply refinements
        if "additional_transactions" in refinements:
            for tcode in refinements["additional_transactions"]:
                original.entities.append(ExtractedEntity(
                    entity_type=EntityType.TRANSACTION,
                    value=tcode.upper(),
                    original_text=tcode,
                    confidence=0.95
                ))

        if "risk_level" in refinements:
            original.entities.append(ExtractedEntity(
                entity_type=EntityType.RISK_LEVEL,
                value=refinements["risk_level"],
                original_text=refinements["risk_level"],
                confidence=1.0
            ))

        if "policy_name" in refinements:
            original.policy_name = refinements["policy_name"]

        # Rebuild structured policy
        if original.intent == PolicyIntent.CREATE_SOD_RULE:
            self._build_sod_rule(original)
        elif original.intent == PolicyIntent.CREATE_SENSITIVE_RULE:
            self._build_sensitive_rule(original)

        # Revalidate
        self._validate_completeness(original)
        original.overall_confidence = self._calculate_confidence(original)
        original.suggestions = []
        self._generate_suggestions(original)

        return original

    def get_examples(self, intent: PolicyIntent = None) -> List[Dict]:
        """Get example natural language inputs"""
        examples = [
            {
                "text": "Users who can create vendors should not be able to process payments",
                "intent": "create_sod_rule",
                "description": "Classic P2P segregation of duties"
            },
            {
                "text": "No one should have both ME21N and MIGO access",
                "intent": "create_sod_rule",
                "description": "PO and GR separation using transaction codes"
            },
            {
                "text": "SE38 ABAP editor access is critical and requires security approval",
                "intent": "create_sensitive_rule",
                "description": "Sensitive access for development"
            },
            {
                "text": "High risk access requests require manager and security team approval within 48 hours",
                "intent": "create_approval_workflow",
                "description": "Multi-level approval workflow"
            },
            {
                "text": "All user access should be reviewed quarterly by managers",
                "intent": "create_certification_policy",
                "description": "Periodic access review"
            },
            {
                "text": "Firefighter access should be limited to 4 hours and require dual approval",
                "intent": "create_firefighter_policy",
                "description": "Emergency access policy"
            }
        ]

        if intent:
            return [e for e in examples if e["intent"] == intent.value]
        return examples

    def get_statistics(self) -> Dict:
        """Get NL policy builder statistics"""
        by_intent = {}
        for parsed in self.parse_history:
            intent = parsed.intent.value
            by_intent[intent] = by_intent.get(intent, 0) + 1

        avg_confidence = sum(p.overall_confidence for p in self.parse_history) / len(self.parse_history) if self.parse_history else 0
        complete_count = sum(1 for p in self.parse_history if p.is_complete)

        return {
            "total_parsed": len(self.parse_history),
            "by_intent": by_intent,
            "average_confidence": round(avg_confidence, 2),
            "completion_rate": round(complete_count / len(self.parse_history), 2) if self.parse_history else 0,
            "supported_intents": [i.value for i in PolicyIntent if i != PolicyIntent.UNKNOWN]
        }
