# Approval Models
# Core data structures for approval system

"""
Approval Models for GOVERNEX+.

Modern approver types beyond "Manager / Security / IT":
- Line Manager (People authority)
- Role Owner (Design accountability)
- Process Owner (Business risk owner)
- Data Owner (Data protection)
- Security Officer (Control & risk)
- Compliance Officer (Regulation)
- System Owner (Technical)
- Delegate (Temporary substitute)
- AI-Recommended (Suggested, not enforced)
"""

from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional, Any
from datetime import datetime, timedelta
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class ApproverType(Enum):
    """Types of approvers (personas, not roles)."""
    LINE_MANAGER = "LINE_MANAGER"
    ROLE_OWNER = "ROLE_OWNER"
    PROCESS_OWNER = "PROCESS_OWNER"
    DATA_OWNER = "DATA_OWNER"
    SECURITY_OFFICER = "SECURITY_OFFICER"
    COMPLIANCE_OFFICER = "COMPLIANCE_OFFICER"
    SYSTEM_OWNER = "SYSTEM_OWNER"
    DELEGATE = "DELEGATE"
    AI_RECOMMENDED = "AI_RECOMMENDED"
    GOVERNANCE_DESK = "GOVERNANCE_DESK"
    CISO = "CISO"


class ApprovalStatus(Enum):
    """Status of an approval request."""
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    ESCALATED = "ESCALATED"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"
    AUTO_APPROVED = "AUTO_APPROVED"


class ApprovalPriority(Enum):
    """Priority of approval request."""
    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"
    EMERGENCY = "EMERGENCY"


class AccessType(Enum):
    """Type of access being requested."""
    ROLE = "ROLE"
    TRANSACTION = "TRANSACTION"
    FIREFIGHTER = "FIREFIGHTER"
    EMERGENCY = "EMERGENCY"
    TEMPORARY = "TEMPORARY"
    PERMANENT = "PERMANENT"


class SystemCriticality(Enum):
    """Criticality of the target system."""
    DEV = "DEV"
    QA = "QA"
    PRE_PROD = "PRE_PROD"
    PROD = "PROD"


@dataclass
class RequestContext:
    """
    Context about the access request itself.

    What is being requested?
    """
    access_type: AccessType = AccessType.ROLE
    system_criticality: SystemCriticality = SystemCriticality.PROD

    # What's requested
    role_ids: List[str] = field(default_factory=list)
    transaction_codes: List[str] = field(default_factory=list)

    # Duration
    is_temporary: bool = False
    duration_days: Optional[int] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

    # Justification
    business_justification: str = ""
    ticket_reference: str = ""

    # Timing
    request_time: datetime = field(default_factory=datetime.now)
    is_business_hours: bool = True

    # Target system
    system_id: str = ""
    system_name: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "access_type": self.access_type.value,
            "system_criticality": self.system_criticality.value,
            "role_ids": self.role_ids,
            "transaction_codes": self.transaction_codes,
            "is_temporary": self.is_temporary,
            "duration_days": self.duration_days,
            "system_id": self.system_id,
            "is_business_hours": self.is_business_hours,
        }


@dataclass
class RiskContext:
    """
    Risk information about the request.

    How risky is this?
    """
    # ARA scores
    risk_score: float = 0.0
    sod_severity: str = ""  # NONE, LOW, MEDIUM, HIGH, CRITICAL
    sod_conflict_count: int = 0

    # Advanced risk
    toxic_role_involved: bool = False
    fraud_likelihood: float = 0.0
    privilege_escalation_risk: bool = False

    # Predictive risk
    predictive_risk_30d: float = 0.0
    predictive_risk_60d: float = 0.0
    predictive_risk_90d: float = 0.0

    # Business process
    business_process: str = ""
    affects_financial: bool = False
    affects_hr: bool = False
    affects_sensitive_data: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "risk_score": round(self.risk_score, 2),
            "sod_severity": self.sod_severity,
            "sod_conflict_count": self.sod_conflict_count,
            "toxic_role_involved": self.toxic_role_involved,
            "fraud_likelihood": round(self.fraud_likelihood, 2),
            "affects_financial": self.affects_financial,
            "business_process": self.business_process,
        }


@dataclass
class UserContext:
    """
    Context about the requester.

    Who is asking?
    """
    user_id: str = ""
    user_name: str = ""

    # Organizational
    department: str = ""
    job_function: str = ""
    manager_id: str = ""
    cost_center: str = ""

    # Employment
    employment_type: str = "FTE"  # FTE, CONTRACTOR, VENDOR
    tenure_days: int = 0
    is_privileged_user: bool = False

    # History
    past_requests: int = 0
    past_rejections: int = 0
    approval_rate: float = 100.0

    # Current access
    current_roles: List[str] = field(default_factory=list)
    current_risk_score: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "user_name": self.user_name,
            "department": self.department,
            "employment_type": self.employment_type,
            "tenure_days": self.tenure_days,
            "is_privileged_user": self.is_privileged_user,
            "past_approval_rate": round(self.approval_rate, 2),
        }


@dataclass
class ApprovalContext:
    """
    Complete context for approval determination.

    All inputs used to determine approvers.
    """
    request: RequestContext = field(default_factory=RequestContext)
    risk: RiskContext = field(default_factory=RiskContext)
    user: UserContext = field(default_factory=UserContext)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request": self.request.to_dict(),
            "risk": self.risk.to_dict(),
            "user": self.user.to_dict(),
        }


@dataclass
class Approver:
    """
    An individual approver.

    Not just a user ID, but context about why they approve.
    """
    approver_id: str
    approver_name: str
    approver_type: ApproverType

    # Contact
    email: str = ""

    # Scope
    process_scope: List[str] = field(default_factory=list)
    system_scope: List[str] = field(default_factory=list)

    # Status
    is_available: bool = True
    is_ooo: bool = False
    ooo_until: Optional[datetime] = None

    # Delegation
    delegate_id: Optional[str] = None
    delegate_name: Optional[str] = None

    # Performance
    avg_response_hours: float = 0.0
    approval_rate: float = 0.0
    current_queue_size: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "approver_id": self.approver_id,
            "approver_name": self.approver_name,
            "approver_type": self.approver_type.value,
            "is_available": self.is_available,
            "is_ooo": self.is_ooo,
            "delegate_id": self.delegate_id,
            "avg_response_hours": round(self.avg_response_hours, 1),
        }


@dataclass
class ApprovalDecision:
    """
    A decision made by an approver.

    Records the decision and reasoning.
    """
    decision_id: str
    request_id: str
    approver_id: str
    approver_type: ApproverType

    # Decision
    status: ApprovalStatus = ApprovalStatus.PENDING
    decision_time: Optional[datetime] = None

    # Details
    comments: str = ""
    conditions: List[str] = field(default_factory=list)

    # If rejected or modified
    rejection_reason: str = ""
    suggested_modification: str = ""

    # SLA
    sla_hours: float = 0.0
    response_time_hours: float = 0.0
    within_sla: bool = True

    # Override info
    overrode_ai_recommendation: bool = False
    override_reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "request_id": self.request_id,
            "approver_id": self.approver_id,
            "approver_type": self.approver_type.value,
            "status": self.status.value,
            "decision_time": self.decision_time.isoformat() if self.decision_time else None,
            "comments": self.comments,
            "within_sla": self.within_sla,
            "overrode_ai_recommendation": self.overrode_ai_recommendation,
        }


@dataclass
class ApprovalRoute:
    """
    The complete approval route for a request.

    Who needs to approve in what order?
    """
    route_id: str
    request_id: str

    # Approvers in order
    stages: List[List[Approver]] = field(default_factory=list)
    current_stage: int = 0

    # Status
    overall_status: ApprovalStatus = ApprovalStatus.PENDING
    decisions: List[ApprovalDecision] = field(default_factory=list)

    # SLA
    total_sla_hours: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)
    due_at: Optional[datetime] = None

    # Determination info
    determination_rule_id: str = ""
    determination_reason: str = ""

    # Auto-approval
    is_auto_approved: bool = False
    auto_approval_reason: str = ""

    def get_current_approvers(self) -> List[Approver]:
        """Get approvers for current stage."""
        if self.current_stage < len(self.stages):
            return self.stages[self.current_stage]
        return []

    def advance_stage(self) -> bool:
        """Move to next stage."""
        if self.current_stage < len(self.stages) - 1:
            self.current_stage += 1
            return True
        return False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "route_id": self.route_id,
            "request_id": self.request_id,
            "stages": [
                [a.to_dict() for a in stage]
                for stage in self.stages
            ],
            "current_stage": self.current_stage,
            "overall_status": self.overall_status.value,
            "total_sla_hours": self.total_sla_hours,
            "due_at": self.due_at.isoformat() if self.due_at else None,
            "is_auto_approved": self.is_auto_approved,
            "determination_reason": self.determination_reason,
        }


@dataclass
class ApprovalRequest:
    """
    A complete approval request.

    Ties together context, route, and decisions.
    """
    request_id: str
    created_at: datetime = field(default_factory=datetime.now)

    # Requester
    requester_id: str = ""
    requester_name: str = ""
    on_behalf_of: Optional[str] = None

    # Context
    context: ApprovalContext = field(default_factory=ApprovalContext)

    # Route
    route: Optional[ApprovalRoute] = None

    # Status
    status: ApprovalStatus = ApprovalStatus.PENDING
    priority: ApprovalPriority = ApprovalPriority.NORMAL

    # Completion
    completed_at: Optional[datetime] = None
    final_decision: Optional[ApprovalStatus] = None

    # Audit
    audit_trail: List[Dict[str, Any]] = field(default_factory=list)

    def add_audit_event(self, event_type: str, details: Dict[str, Any]) -> None:
        """Add an audit trail event."""
        self.audit_trail.append({
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "details": details,
        })

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "created_at": self.created_at.isoformat(),
            "requester_id": self.requester_id,
            "requester_name": self.requester_name,
            "context": self.context.to_dict(),
            "route": self.route.to_dict() if self.route else None,
            "status": self.status.value,
            "priority": self.priority.value,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }
