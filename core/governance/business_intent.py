"""
Business Intent Governance Layer

Captures, governs, and traces business purposes for access requests.
This is BEYOND SAP GRC - making "why" a first-class governed object.

Key Capabilities:
- Business intent taxonomy management
- Intent-to-access traceability
- Prior approval reuse
- Auditor-ready intent documentation
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Set
from datetime import datetime, timedelta
from enum import Enum
import uuid
import hashlib


class IntentCategory(Enum):
    """Standard business intent categories"""
    QUARTER_CLOSE = "quarter_close"
    YEAR_END_CLOSE = "year_end_close"
    AUDIT_SUPPORT = "audit_support"
    PRODUCTION_FIX = "production_fix"
    PROJECT_IMPLEMENTATION = "project_implementation"
    BUSINESS_CONTINUITY = "business_continuity"
    REGULATORY_COMPLIANCE = "regulatory_compliance"
    MERGER_ACQUISITION = "merger_acquisition"
    SYSTEM_MIGRATION = "system_migration"
    SECURITY_INCIDENT = "security_incident"
    TRAINING = "training"
    TESTING = "testing"
    DAILY_OPERATIONS = "daily_operations"
    CUSTOM = "custom"


class IntentRiskLevel(Enum):
    """Risk level of business intent"""
    ROUTINE = "routine"           # Normal business operations
    ELEVATED = "elevated"         # Time-sensitive, needs attention
    HIGH = "high"                 # Critical business need
    EMERGENCY = "emergency"       # Urgent, bypass normal controls


class IntentStatus(Enum):
    """Lifecycle status of a business intent"""
    DRAFT = "draft"
    SUBMITTED = "submitted"
    VALIDATED = "validated"
    APPROVED = "approved"
    ACTIVE = "active"
    COMPLETED = "completed"
    EXPIRED = "expired"
    REVOKED = "revoked"


@dataclass
class BusinessIntent:
    """
    A first-class business intent object.

    Captures the "why" behind access requests, making it auditable
    and reusable for similar future requests.
    """
    intent_id: str
    title: str
    description: str
    category: IntentCategory
    risk_level: IntentRiskLevel

    # Business context
    business_justification: str
    expected_outcome: str
    business_owner_id: str
    business_owner_name: str
    cost_center: Optional[str] = None
    project_code: Optional[str] = None

    # Timing
    valid_from: datetime = field(default_factory=datetime.utcnow)
    valid_until: Optional[datetime] = None
    actual_completion: Optional[datetime] = None

    # Regulatory context
    regulatory_drivers: List[str] = field(default_factory=list)
    compliance_requirements: List[str] = field(default_factory=list)

    # Traceability
    related_access_requests: List[str] = field(default_factory=list)
    related_firefighter_sessions: List[str] = field(default_factory=list)
    parent_intent_id: Optional[str] = None
    child_intents: List[str] = field(default_factory=list)

    # Approval
    status: IntentStatus = IntentStatus.DRAFT
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    approval_comments: str = ""

    # Audit trail
    created_at: datetime = field(default_factory=datetime.utcnow)
    created_by: str = ""
    modified_at: Optional[datetime] = None
    modification_history: List[Dict] = field(default_factory=list)

    # For reuse matching
    intent_fingerprint: str = ""
    reuse_count: int = 0
    similar_approved_intents: List[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.intent_id:
            self.intent_id = f"INT-{uuid.uuid4().hex[:8].upper()}"
        if not self.intent_fingerprint:
            self.intent_fingerprint = self._generate_fingerprint()

    def _generate_fingerprint(self) -> str:
        """Generate fingerprint for similarity matching"""
        components = [
            self.category.value,
            self.business_justification[:100] if self.business_justification else "",
            ",".join(sorted(self.regulatory_drivers)),
            self.cost_center or "",
        ]
        content = "|".join(components).lower()
        return hashlib.md5(content.encode()).hexdigest()[:12]

    def to_dict(self) -> Dict:
        return {
            "intent_id": self.intent_id,
            "title": self.title,
            "description": self.description,
            "category": self.category.value,
            "risk_level": self.risk_level.value,
            "business_justification": self.business_justification,
            "expected_outcome": self.expected_outcome,
            "business_owner_id": self.business_owner_id,
            "business_owner_name": self.business_owner_name,
            "cost_center": self.cost_center,
            "project_code": self.project_code,
            "valid_from": self.valid_from.isoformat() if self.valid_from else None,
            "valid_until": self.valid_until.isoformat() if self.valid_until else None,
            "regulatory_drivers": self.regulatory_drivers,
            "compliance_requirements": self.compliance_requirements,
            "related_access_requests": self.related_access_requests,
            "status": self.status.value,
            "approved_by": self.approved_by,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "created_at": self.created_at.isoformat(),
            "intent_fingerprint": self.intent_fingerprint,
            "reuse_count": self.reuse_count
        }

    def get_audit_narrative(self) -> str:
        """Generate auditor-friendly narrative"""
        return f"""
BUSINESS INTENT DOCUMENTATION
=============================
Intent ID: {self.intent_id}
Title: {self.title}
Category: {self.category.value.replace('_', ' ').title()}
Risk Level: {self.risk_level.value.title()}

BUSINESS JUSTIFICATION:
{self.business_justification}

EXPECTED OUTCOME:
{self.expected_outcome}

BUSINESS OWNER:
{self.business_owner_name} ({self.business_owner_id})

VALIDITY PERIOD:
From: {self.valid_from.strftime('%Y-%m-%d') if self.valid_from else 'N/A'}
Until: {self.valid_until.strftime('%Y-%m-%d') if self.valid_until else 'Ongoing'}

REGULATORY CONTEXT:
{chr(10).join(f'- {r}' for r in self.regulatory_drivers) if self.regulatory_drivers else 'None specified'}

APPROVAL STATUS:
Status: {self.status.value.title()}
Approved By: {self.approved_by or 'Pending'}
Approved At: {self.approved_at.strftime('%Y-%m-%d %H:%M') if self.approved_at else 'N/A'}

LINKED ACCESS:
- Access Requests: {len(self.related_access_requests)}
- Firefighter Sessions: {len(self.related_firefighter_sessions)}
"""


@dataclass
class IntentTemplate:
    """Pre-approved intent template for common scenarios"""
    template_id: str
    name: str
    category: IntentCategory
    description_template: str
    justification_template: str
    default_duration_days: int
    required_approvals: List[str]
    auto_approved: bool = False
    max_reuse_count: int = 10


class BusinessIntentEngine:
    """
    Manages business intent lifecycle.

    Features:
    - Intent creation and validation
    - Similar intent matching for reuse
    - Intent-to-access traceability
    - Audit documentation generation
    """

    def __init__(self):
        self.intents: Dict[str, BusinessIntent] = {}
        self.templates: Dict[str, IntentTemplate] = {}
        self.fingerprint_index: Dict[str, List[str]] = {}  # fingerprint -> intent_ids
        self._init_templates()

    def _init_templates(self):
        """Initialize standard intent templates"""
        templates = [
            IntentTemplate(
                template_id="TMPL-QC",
                name="Quarter Close Support",
                category=IntentCategory.QUARTER_CLOSE,
                description_template="Access required to support Q{quarter} {year} financial close activities",
                justification_template="Quarter-end close requires elevated access for financial reporting, reconciliation, and audit preparation. This is a recurring business requirement aligned with our reporting calendar.",
                default_duration_days=14,
                required_approvals=["controller", "cfo"],
                auto_approved=False
            ),
            IntentTemplate(
                template_id="TMPL-AUDIT",
                name="Internal/External Audit Support",
                category=IntentCategory.AUDIT_SUPPORT,
                description_template="Access to support {audit_type} audit for period {period}",
                justification_template="Audit teams require access to validate controls, review transactions, and verify compliance. Limited duration access aligned with audit timeline.",
                default_duration_days=30,
                required_approvals=["audit_manager"],
                auto_approved=False
            ),
            IntentTemplate(
                template_id="TMPL-PRODFIX",
                name="Production Issue Resolution",
                category=IntentCategory.PRODUCTION_FIX,
                description_template="Emergency access to resolve {incident_id}: {incident_summary}",
                justification_template="Production incident requires immediate resolution to prevent business disruption. Access limited to minimum necessary for fix.",
                default_duration_days=1,
                required_approvals=["it_manager"],
                auto_approved=False,
                max_reuse_count=1
            ),
            IntentTemplate(
                template_id="TMPL-DAILY",
                name="Daily Operations",
                category=IntentCategory.DAILY_OPERATIONS,
                description_template="Standard access for {role_name} daily operations",
                justification_template="Access required for standard job functions as defined in role description and approved by manager.",
                default_duration_days=365,
                required_approvals=["manager"],
                auto_approved=True
            ),
        ]

        for template in templates:
            self.templates[template.template_id] = template

    def create_intent(
        self,
        title: str,
        description: str,
        category: IntentCategory,
        business_justification: str,
        expected_outcome: str,
        business_owner_id: str,
        business_owner_name: str,
        created_by: str,
        risk_level: IntentRiskLevel = IntentRiskLevel.ROUTINE,
        valid_until: Optional[datetime] = None,
        regulatory_drivers: List[str] = None,
        cost_center: Optional[str] = None,
        project_code: Optional[str] = None
    ) -> BusinessIntent:
        """Create a new business intent"""

        intent = BusinessIntent(
            intent_id="",
            title=title,
            description=description,
            category=category,
            risk_level=risk_level,
            business_justification=business_justification,
            expected_outcome=expected_outcome,
            business_owner_id=business_owner_id,
            business_owner_name=business_owner_name,
            cost_center=cost_center,
            project_code=project_code,
            valid_until=valid_until,
            regulatory_drivers=regulatory_drivers or [],
            created_by=created_by
        )

        # Find similar approved intents
        intent.similar_approved_intents = self._find_similar_intents(intent)

        # Store intent
        self.intents[intent.intent_id] = intent

        # Index by fingerprint
        if intent.intent_fingerprint not in self.fingerprint_index:
            self.fingerprint_index[intent.intent_fingerprint] = []
        self.fingerprint_index[intent.intent_fingerprint].append(intent.intent_id)

        return intent

    def create_from_template(
        self,
        template_id: str,
        business_owner_id: str,
        business_owner_name: str,
        created_by: str,
        variables: Dict[str, str] = None,
        valid_until: Optional[datetime] = None
    ) -> BusinessIntent:
        """Create intent from pre-approved template"""

        if template_id not in self.templates:
            raise ValueError(f"Template not found: {template_id}")

        template = self.templates[template_id]
        variables = variables or {}

        # Fill in template variables
        description = template.description_template.format(**variables) if variables else template.description_template
        justification = template.justification_template.format(**variables) if variables else template.justification_template

        # Calculate validity
        if not valid_until:
            valid_until = datetime.utcnow() + timedelta(days=template.default_duration_days)

        intent = self.create_intent(
            title=f"{template.name} - {datetime.utcnow().strftime('%Y-%m-%d')}",
            description=description,
            category=template.category,
            business_justification=justification,
            expected_outcome=f"Successful completion of {template.name.lower()}",
            business_owner_id=business_owner_id,
            business_owner_name=business_owner_name,
            created_by=created_by,
            valid_until=valid_until
        )

        # Auto-approve if template allows
        if template.auto_approved:
            intent.status = IntentStatus.APPROVED
            intent.approved_by = "SYSTEM (Auto-approved Template)"
            intent.approved_at = datetime.utcnow()

        return intent

    def _find_similar_intents(self, intent: BusinessIntent) -> List[str]:
        """Find similar previously approved intents"""
        similar = []

        # Check fingerprint index
        if intent.intent_fingerprint in self.fingerprint_index:
            for intent_id in self.fingerprint_index[intent.intent_fingerprint]:
                existing = self.intents.get(intent_id)
                if existing and existing.status == IntentStatus.APPROVED:
                    similar.append(intent_id)

        return similar[:5]  # Return top 5

    def validate_intent(self, intent_id: str, validator_id: str) -> Dict:
        """Validate intent completeness and quality"""

        if intent_id not in self.intents:
            return {"valid": False, "error": "Intent not found"}

        intent = self.intents[intent_id]
        issues = []

        # Check required fields
        if len(intent.business_justification) < 50:
            issues.append("Business justification should be more detailed (min 50 characters)")

        if len(intent.expected_outcome) < 20:
            issues.append("Expected outcome should be more specific (min 20 characters)")

        if not intent.business_owner_id:
            issues.append("Business owner must be specified")

        if intent.risk_level in [IntentRiskLevel.HIGH, IntentRiskLevel.EMERGENCY]:
            if not intent.regulatory_drivers:
                issues.append("High-risk intents should specify regulatory drivers")

        # Update status
        if not issues:
            intent.status = IntentStatus.VALIDATED
            intent.modification_history.append({
                "action": "validated",
                "by": validator_id,
                "at": datetime.utcnow().isoformat()
            })

        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "intent_id": intent_id,
            "status": intent.status.value
        }

    def approve_intent(
        self,
        intent_id: str,
        approver_id: str,
        comments: str = ""
    ) -> Dict:
        """Approve a business intent"""

        if intent_id not in self.intents:
            return {"success": False, "error": "Intent not found"}

        intent = self.intents[intent_id]
        intent.status = IntentStatus.APPROVED
        intent.approved_by = approver_id
        intent.approved_at = datetime.utcnow()
        intent.approval_comments = comments
        intent.modification_history.append({
            "action": "approved",
            "by": approver_id,
            "at": datetime.utcnow().isoformat(),
            "comments": comments
        })

        return {
            "success": True,
            "intent_id": intent_id,
            "status": intent.status.value
        }

    def link_access_request(self, intent_id: str, request_id: str) -> Dict:
        """Link an access request to a business intent"""

        if intent_id not in self.intents:
            return {"success": False, "error": "Intent not found"}

        intent = self.intents[intent_id]
        if request_id not in intent.related_access_requests:
            intent.related_access_requests.append(request_id)

        return {
            "success": True,
            "intent_id": intent_id,
            "linked_requests": len(intent.related_access_requests)
        }

    def link_firefighter_session(self, intent_id: str, session_id: str) -> Dict:
        """Link a firefighter session to a business intent"""

        if intent_id not in self.intents:
            return {"success": False, "error": "Intent not found"}

        intent = self.intents[intent_id]
        if session_id not in intent.related_firefighter_sessions:
            intent.related_firefighter_sessions.append(session_id)

        return {
            "success": True,
            "intent_id": intent_id,
            "linked_sessions": len(intent.related_firefighter_sessions)
        }

    def reuse_intent(self, original_intent_id: str, created_by: str) -> BusinessIntent:
        """Reuse a previously approved intent for similar scenario"""

        if original_intent_id not in self.intents:
            raise ValueError("Original intent not found")

        original = self.intents[original_intent_id]
        if original.status != IntentStatus.APPROVED:
            raise ValueError("Can only reuse approved intents")

        # Create new intent based on original
        new_intent = self.create_intent(
            title=f"{original.title} (Reuse)",
            description=original.description,
            category=original.category,
            business_justification=original.business_justification,
            expected_outcome=original.expected_outcome,
            business_owner_id=original.business_owner_id,
            business_owner_name=original.business_owner_name,
            created_by=created_by,
            risk_level=original.risk_level,
            regulatory_drivers=original.regulatory_drivers.copy(),
            cost_center=original.cost_center,
            project_code=original.project_code
        )

        # Link to original
        new_intent.parent_intent_id = original_intent_id
        original.child_intents.append(new_intent.intent_id)
        original.reuse_count += 1

        # Auto-approve if original was approved
        new_intent.status = IntentStatus.APPROVED
        new_intent.approved_by = f"SYSTEM (Reuse of {original_intent_id})"
        new_intent.approved_at = datetime.utcnow()
        new_intent.approval_comments = f"Auto-approved based on prior approval of {original_intent_id}"

        return new_intent

    def get_intent_trail(self, intent_id: str) -> Dict:
        """Get full audit trail for an intent"""

        if intent_id not in self.intents:
            return {"error": "Intent not found"}

        intent = self.intents[intent_id]

        return {
            "intent": intent.to_dict(),
            "audit_narrative": intent.get_audit_narrative(),
            "modification_history": intent.modification_history,
            "linked_access_requests": intent.related_access_requests,
            "linked_firefighter_sessions": intent.related_firefighter_sessions,
            "parent_intent": intent.parent_intent_id,
            "child_intents": intent.child_intents,
            "similar_intents": intent.similar_approved_intents
        }

    def get_intents_by_category(self, category: IntentCategory) -> List[BusinessIntent]:
        """Get all intents by category"""
        return [i for i in self.intents.values() if i.category == category]

    def get_active_intents(self) -> List[BusinessIntent]:
        """Get all currently active intents"""
        now = datetime.utcnow()
        return [
            i for i in self.intents.values()
            if i.status == IntentStatus.APPROVED
            and i.valid_from <= now
            and (i.valid_until is None or i.valid_until > now)
        ]

    def get_statistics(self) -> Dict:
        """Get intent governance statistics"""
        intents = list(self.intents.values())

        return {
            "total_intents": len(intents),
            "by_status": {
                status.value: len([i for i in intents if i.status == status])
                for status in IntentStatus
            },
            "by_category": {
                cat.value: len([i for i in intents if i.category == cat])
                for cat in IntentCategory
            },
            "by_risk_level": {
                level.value: len([i for i in intents if i.risk_level == level])
                for level in IntentRiskLevel
            },
            "total_reuses": sum(i.reuse_count for i in intents),
            "linked_access_requests": sum(len(i.related_access_requests) for i in intents),
            "linked_firefighter_sessions": sum(len(i.related_firefighter_sessions) for i in intents)
        }
