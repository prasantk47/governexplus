# Workflow Engine Models
# Universal workflow data structures for GOVERNEX+

"""
Core Data Models for GOVERNEX+ Universal Workflow Engine.

These models support:
- Process-agnostic workflow definition
- Dynamic workflow assembly
- Risk-adaptive routing
- Complete auditability
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
from enum import Enum
import uuid


# ============================================================
# ENUMERATIONS
# ============================================================

class ProcessType(Enum):
    """
    All GRC process types supported by the workflow engine.

    GOVERNEX+ supports ALL process types with ONE engine.
    """
    # Access & Identity
    ACCESS_REQUEST = "ACCESS_REQUEST"
    ROLE_ASSIGNMENT = "ROLE_ASSIGNMENT"
    TEMPORARY_ACCESS = "TEMPORARY_ACCESS"
    BULK_ACCESS = "BULK_ACCESS"
    USER_ONBOARDING = "USER_ONBOARDING"
    USER_OFFBOARDING = "USER_OFFBOARDING"
    USER_TRANSFER = "USER_TRANSFER"

    # Privileged Access
    FIREFIGHTER = "FIREFIGHTER"
    EMERGENCY_ACCESS = "EMERGENCY_ACCESS"
    JIT_PRIVILEGED = "JIT_PRIVILEGED"
    POST_ACCESS_REVIEW = "POST_ACCESS_REVIEW"

    # Risk & Compliance
    RISK_ACCEPTANCE = "RISK_ACCEPTANCE"
    MITIGATION_ASSIGNMENT = "MITIGATION_ASSIGNMENT"
    CONTROL_EXCEPTION = "CONTROL_EXCEPTION"
    POLICY_OVERRIDE = "POLICY_OVERRIDE"
    SOD_WAIVER = "SOD_WAIVER"

    # Role Governance
    ROLE_CREATION = "ROLE_CREATION"
    ROLE_MODIFICATION = "ROLE_MODIFICATION"
    ROLE_RETIREMENT = "ROLE_RETIREMENT"
    ROLE_REFACTOR = "ROLE_REFACTOR"

    # Audit & Review
    ACCESS_REVIEW = "ACCESS_REVIEW"
    ROLE_CERTIFICATION = "ROLE_CERTIFICATION"
    CONTROL_TESTING = "CONTROL_TESTING"
    AUDIT_EVIDENCE = "AUDIT_EVIDENCE"

    # Autonomous
    AUTO_APPROVAL = "AUTO_APPROVAL"
    AUTO_REVOCATION = "AUTO_REVOCATION"
    PREDICTIVE_ESCALATION = "PREDICTIVE_ESCALATION"

    # Generic
    GENERIC = "GENERIC"


class AccessType(Enum):
    """Type of access being requested."""
    ROLE = "ROLE"
    TCODE = "TCODE"
    PROFILE = "PROFILE"
    AUTH_OBJECT = "AUTH_OBJECT"
    COMPOSITE_ROLE = "COMPOSITE_ROLE"
    DERIVED_ROLE = "DERIVED_ROLE"
    APPLICATION = "APPLICATION"
    ENTITLEMENT = "ENTITLEMENT"


class TriggerType(Enum):
    """What triggered the workflow."""
    USER_REQUEST = "USER_REQUEST"
    MANAGER_REQUEST = "MANAGER_REQUEST"
    SCHEDULED = "SCHEDULED"
    RISK_DETECTION = "RISK_DETECTION"
    POLICY_VIOLATION = "POLICY_VIOLATION"
    EXPIRATION = "EXPIRATION"
    SYSTEM_EVENT = "SYSTEM_EVENT"
    AI_PREDICTION = "AI_PREDICTION"
    EXTERNAL_INTEGRATION = "EXTERNAL_INTEGRATION"


class WorkflowStatus(Enum):
    """Status of a workflow instance."""
    DRAFT = "DRAFT"
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    WAITING_APPROVAL = "WAITING_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"
    ESCALATED = "ESCALATED"
    AUTO_APPROVED = "AUTO_APPROVED"
    AUTO_REJECTED = "AUTO_REJECTED"
    PROVISIONING = "PROVISIONING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    SUSPENDED = "SUSPENDED"


class StepStatus(Enum):
    """Status of a workflow step."""
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    DELEGATED = "DELEGATED"
    ESCALATED = "ESCALATED"
    AUTO_APPROVED = "AUTO_APPROVED"
    SKIPPED = "SKIPPED"
    TIMED_OUT = "TIMED_OUT"
    CANCELLED = "CANCELLED"


class ApproverTypeEnum(Enum):
    """Types of approvers in the workflow."""
    LINE_MANAGER = "LINE_MANAGER"
    ROLE_OWNER = "ROLE_OWNER"
    PROCESS_OWNER = "PROCESS_OWNER"
    DATA_OWNER = "DATA_OWNER"
    SYSTEM_OWNER = "SYSTEM_OWNER"
    SECURITY_OFFICER = "SECURITY_OFFICER"
    COMPLIANCE_OFFICER = "COMPLIANCE_OFFICER"
    RISK_OFFICER = "RISK_OFFICER"
    CISO = "CISO"
    FIREFIGHTER_SUPERVISOR = "FIREFIGHTER_SUPERVISOR"
    GOVERNANCE_DESK = "GOVERNANCE_DESK"
    CUSTOM = "CUSTOM"


# ============================================================
# CONTEXT MODELS
# ============================================================

@dataclass
class WorkflowContext:
    """
    Complete context for workflow assembly.

    This is the "input" to the workflow engine.
    Everything needed to assemble the right workflow.
    """
    # Request identity
    request_id: str = ""
    process_type: ProcessType = ProcessType.GENERIC
    trigger_type: TriggerType = TriggerType.USER_REQUEST

    # What is being requested
    system_id: str = ""
    system_name: str = ""
    is_production: bool = False
    business_process: str = ""
    access_type: AccessType = AccessType.ROLE
    role_id: str = ""
    role_name: str = ""
    access_items: List[Dict[str, Any]] = field(default_factory=list)

    # Who is requesting
    requester_id: str = ""
    requester_name: str = ""
    requester_department: str = ""
    requester_manager_id: str = ""
    requester_cost_center: str = ""

    # For whom (may differ from requester)
    target_user_id: str = ""
    target_user_name: str = ""
    target_user_department: str = ""
    target_user_manager_id: str = ""

    # Risk assessment
    risk_score: int = 0
    risk_level: str = "LOW"  # LOW, MEDIUM, HIGH, CRITICAL
    sod_conflicts: List[str] = field(default_factory=list)
    toxic_combinations: List[str] = field(default_factory=list)
    sensitive_data_access: List[str] = field(default_factory=list)
    fraud_likelihood: float = 0.0

    # Duration
    is_temporary: bool = False
    duration_days: Optional[int] = None
    access_start: Optional[datetime] = None
    access_end: Optional[datetime] = None

    # Business justification
    justification: str = ""
    business_case: str = ""
    ticket_reference: str = ""

    # Additional context
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)

    def to_eval_dict(self) -> Dict[str, Any]:
        """Convert to dict for policy evaluation."""
        return {
            "request_id": self.request_id,
            "process_type": self.process_type.value,
            "trigger_type": self.trigger_type.value,
            "system": self.system_id,
            "system_name": self.system_name,
            "is_production": self.is_production,
            "business_process": self.business_process,
            "access_type": self.access_type.value,
            "role_id": self.role_id,
            "requester": self.requester_id,
            "requester_department": self.requester_department,
            "target_user": self.target_user_id,
            "target_user_department": self.target_user_department,
            "risk_score": self.risk_score,
            "risk_level": self.risk_level,
            "sod_conflict_count": len(self.sod_conflicts),
            "has_sod_conflicts": len(self.sod_conflicts) > 0,
            "has_toxic_combinations": len(self.toxic_combinations) > 0,
            "has_sensitive_data": len(self.sensitive_data_access) > 0,
            "fraud_likelihood": self.fraud_likelihood,
            "is_temporary": self.is_temporary,
            "duration_days": self.duration_days,
            **self.metadata,
        }

    def to_dict(self) -> Dict[str, Any]:
        """Full serialization."""
        return {
            "request_id": self.request_id,
            "process_type": self.process_type.value,
            "trigger_type": self.trigger_type.value,
            "system": {
                "id": self.system_id,
                "name": self.system_name,
                "is_production": self.is_production,
            },
            "business_process": self.business_process,
            "access": {
                "type": self.access_type.value,
                "role_id": self.role_id,
                "role_name": self.role_name,
                "items": self.access_items,
            },
            "requester": {
                "id": self.requester_id,
                "name": self.requester_name,
                "department": self.requester_department,
                "manager_id": self.requester_manager_id,
            },
            "target_user": {
                "id": self.target_user_id,
                "name": self.target_user_name,
                "department": self.target_user_department,
                "manager_id": self.target_user_manager_id,
            },
            "risk": {
                "score": self.risk_score,
                "level": self.risk_level,
                "sod_conflicts": self.sod_conflicts,
                "toxic_combinations": self.toxic_combinations,
                "sensitive_data": self.sensitive_data_access,
                "fraud_likelihood": self.fraud_likelihood,
            },
            "duration": {
                "is_temporary": self.is_temporary,
                "days": self.duration_days,
                "start": self.access_start.isoformat() if self.access_start else None,
                "end": self.access_end.isoformat() if self.access_end else None,
            },
            "justification": self.justification,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
        }


# ============================================================
# STEP MODELS
# ============================================================

@dataclass
class WorkflowStep:
    """
    A single step in the assembled workflow.

    Steps are created dynamically by the assembler.
    """
    step_id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    step_number: int = 1
    name: str = ""
    description: str = ""

    # Approver
    approver_type: ApproverTypeEnum = ApproverTypeEnum.LINE_MANAGER
    approver_id: Optional[str] = None
    approver_name: Optional[str] = None
    approver_email: Optional[str] = None

    # Behavior
    require_all: bool = False  # If multiple approvers, require all
    allow_delegation: bool = True
    allow_rejection: bool = True

    # SLA
    sla_hours: float = 24.0
    reminder_hours: float = 12.0
    escalation_hours: float = 48.0
    escalation_approver_id: Optional[str] = None

    # Status
    status: StepStatus = StepStatus.PENDING
    decision: Optional[str] = None  # APPROVED, REJECTED
    decision_comments: str = ""
    decided_by: Optional[str] = None
    decided_at: Optional[datetime] = None

    # Reason (from policy)
    reason: str = ""
    policy_rule_id: str = ""

    # Timing
    created_at: datetime = field(default_factory=datetime.now)
    activated_at: Optional[datetime] = None
    due_at: Optional[datetime] = None

    # Audit
    delegation_history: List[Dict[str, Any]] = field(default_factory=list)
    escalation_history: List[Dict[str, Any]] = field(default_factory=list)

    def is_complete(self) -> bool:
        """Check if step is complete."""
        return self.status in [
            StepStatus.APPROVED,
            StepStatus.REJECTED,
            StepStatus.SKIPPED,
            StepStatus.AUTO_APPROVED,
            StepStatus.CANCELLED,
        ]

    def is_pending(self) -> bool:
        """Check if step is waiting for action."""
        return self.status in [StepStatus.PENDING, StepStatus.ACTIVE]

    def is_overdue(self) -> bool:
        """Check if step is past SLA."""
        if self.due_at and self.is_pending():
            return datetime.now() > self.due_at
        return False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_id": self.step_id,
            "step_number": self.step_number,
            "name": self.name,
            "description": self.description,
            "approver": {
                "type": self.approver_type.value,
                "id": self.approver_id,
                "name": self.approver_name,
            },
            "behavior": {
                "require_all": self.require_all,
                "allow_delegation": self.allow_delegation,
                "allow_rejection": self.allow_rejection,
            },
            "sla": {
                "hours": self.sla_hours,
                "reminder_hours": self.reminder_hours,
                "escalation_hours": self.escalation_hours,
            },
            "status": self.status.value,
            "decision": self.decision,
            "decision_comments": self.decision_comments,
            "decided_by": self.decided_by,
            "decided_at": self.decided_at.isoformat() if self.decided_at else None,
            "reason": self.reason,
            "policy_rule_id": self.policy_rule_id,
            "due_at": self.due_at.isoformat() if self.due_at else None,
            "is_overdue": self.is_overdue(),
        }


# ============================================================
# WORKFLOW MODELS
# ============================================================

@dataclass
class Workflow:
    """
    A complete workflow instance.

    This is the assembled workflow ready for execution.
    """
    workflow_id: str = field(default_factory=lambda: f"WF-{datetime.now().strftime('%Y%m%d%H%M%S')}-{str(uuid.uuid4())[:8]}")
    process_type: ProcessType = ProcessType.GENERIC

    # Context (what triggered this)
    context: Optional[WorkflowContext] = None

    # Steps (dynamically assembled)
    steps: List[WorkflowStep] = field(default_factory=list)

    # Status
    status: WorkflowStatus = WorkflowStatus.DRAFT
    current_step_index: int = 0

    # Decisions
    final_decision: Optional[str] = None  # APPROVED, REJECTED
    final_decision_at: Optional[datetime] = None

    # Assembly metadata
    assembled_by_policy: str = ""
    assembly_rules_matched: List[str] = field(default_factory=list)
    assembly_explanation: str = ""

    # Timing
    created_at: datetime = field(default_factory=datetime.now)
    submitted_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Post-workflow actions
    post_approval_actions: List[str] = field(default_factory=list)
    post_rejection_actions: List[str] = field(default_factory=list)

    # Audit trail
    audit_log: List[Dict[str, Any]] = field(default_factory=list)

    def get_current_step(self) -> Optional[WorkflowStep]:
        """Get the current active step."""
        if 0 <= self.current_step_index < len(self.steps):
            return self.steps[self.current_step_index]
        return None

    def get_pending_steps(self) -> List[WorkflowStep]:
        """Get all pending steps."""
        return [s for s in self.steps if s.is_pending()]

    def get_completed_steps(self) -> List[WorkflowStep]:
        """Get all completed steps."""
        return [s for s in self.steps if s.is_complete()]

    def is_complete(self) -> bool:
        """Check if workflow is complete."""
        return self.status in [
            WorkflowStatus.APPROVED,
            WorkflowStatus.REJECTED,
            WorkflowStatus.CANCELLED,
            WorkflowStatus.COMPLETED,
            WorkflowStatus.AUTO_APPROVED,
            WorkflowStatus.AUTO_REJECTED,
        ]

    def get_total_sla_hours(self) -> float:
        """Get total SLA for all steps."""
        return sum(s.sla_hours for s in self.steps)

    def get_elapsed_hours(self) -> float:
        """Get elapsed time since submission."""
        if self.submitted_at:
            return (datetime.now() - self.submitted_at).total_seconds() / 3600
        return 0.0

    def add_audit_entry(self, event: str, details: Dict[str, Any]) -> None:
        """Add an audit log entry."""
        self.audit_log.append({
            "timestamp": datetime.now().isoformat(),
            "event": event,
            "details": details,
        })

    def to_dict(self) -> Dict[str, Any]:
        return {
            "workflow_id": self.workflow_id,
            "process_type": self.process_type.value,
            "context": self.context.to_dict() if self.context else None,
            "steps": [s.to_dict() for s in self.steps],
            "status": self.status.value,
            "current_step_index": self.current_step_index,
            "final_decision": self.final_decision,
            "assembly": {
                "policy": self.assembled_by_policy,
                "rules_matched": self.assembly_rules_matched,
                "explanation": self.assembly_explanation,
            },
            "timing": {
                "created_at": self.created_at.isoformat(),
                "submitted_at": self.submitted_at.isoformat() if self.submitted_at else None,
                "completed_at": self.completed_at.isoformat() if self.completed_at else None,
                "total_sla_hours": self.get_total_sla_hours(),
                "elapsed_hours": round(self.get_elapsed_hours(), 2),
            },
            "is_complete": self.is_complete(),
        }


# ============================================================
# DECISION MODELS
# ============================================================

@dataclass
class StepDecision:
    """A decision made on a workflow step."""
    step_id: str
    decision: str  # APPROVED, REJECTED, DELEGATED
    decided_by: str
    decided_at: datetime = field(default_factory=datetime.now)
    comments: str = ""
    delegation_to: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_id": self.step_id,
            "decision": self.decision,
            "decided_by": self.decided_by,
            "decided_at": self.decided_at.isoformat(),
            "comments": self.comments,
            "delegation_to": self.delegation_to,
        }


@dataclass
class WorkflowDecision:
    """Final decision on a workflow."""
    workflow_id: str
    decision: str  # APPROVED, REJECTED
    decided_at: datetime = field(default_factory=datetime.now)
    step_decisions: List[StepDecision] = field(default_factory=list)
    override_by: Optional[str] = None
    override_reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "workflow_id": self.workflow_id,
            "decision": self.decision,
            "decided_at": self.decided_at.isoformat(),
            "step_decisions": [s.to_dict() for s in self.step_decisions],
            "override": {
                "by": self.override_by,
                "reason": self.override_reason,
            } if self.override_by else None,
        }


# ============================================================
# CONFIGURATION MODELS
# ============================================================

@dataclass
class StepConfig:
    """Configuration for a workflow step."""
    approver_type: ApproverTypeEnum
    sla_hours: float = 24.0
    require_all: bool = False
    allow_delegation: bool = True
    allow_rejection: bool = True
    reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "approver_type": self.approver_type.value,
            "sla_hours": self.sla_hours,
            "require_all": self.require_all,
            "allow_delegation": self.allow_delegation,
            "allow_rejection": self.allow_rejection,
            "reason": self.reason,
        }


@dataclass
class EscalationConfig:
    """Configuration for escalation behavior."""
    enabled: bool = True
    hours_before_escalation: float = 24.0
    escalation_chain: List[ApproverTypeEnum] = field(default_factory=list)
    notify_on_escalation: bool = True
    max_escalations: int = 3

    def to_dict(self) -> Dict[str, Any]:
        return {
            "enabled": self.enabled,
            "hours_before_escalation": self.hours_before_escalation,
            "escalation_chain": [a.value for a in self.escalation_chain],
            "notify_on_escalation": self.notify_on_escalation,
            "max_escalations": self.max_escalations,
        }


@dataclass
class WorkflowConfig:
    """
    Global workflow configuration.

    Customizable per tenant/organization.
    """
    # Default SLAs by risk level
    sla_by_risk: Dict[str, float] = field(default_factory=lambda: {
        "LOW": 72.0,
        "MEDIUM": 48.0,
        "HIGH": 24.0,
        "CRITICAL": 8.0,
    })

    # Auto-approval settings
    auto_approve_enabled: bool = True
    auto_approve_max_risk_score: int = 20
    auto_approve_excluded_systems: List[str] = field(default_factory=list)

    # Escalation
    escalation_config: EscalationConfig = field(default_factory=EscalationConfig)

    # Delegation
    delegation_enabled: bool = True
    max_delegation_depth: int = 2

    # Notifications
    notify_requester_on_each_step: bool = True
    notify_on_sla_warning: bool = True
    sla_warning_threshold_hours: float = 4.0

    # Audit
    require_comments_on_rejection: bool = True
    require_comments_on_high_risk_approval: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sla_by_risk": self.sla_by_risk,
            "auto_approve": {
                "enabled": self.auto_approve_enabled,
                "max_risk_score": self.auto_approve_max_risk_score,
                "excluded_systems": self.auto_approve_excluded_systems,
            },
            "escalation": self.escalation_config.to_dict(),
            "delegation": {
                "enabled": self.delegation_enabled,
                "max_depth": self.max_delegation_depth,
            },
            "notifications": {
                "notify_requester_on_each_step": self.notify_requester_on_each_step,
                "notify_on_sla_warning": self.notify_on_sla_warning,
                "sla_warning_threshold_hours": self.sla_warning_threshold_hours,
            },
            "audit": {
                "require_comments_on_rejection": self.require_comments_on_rejection,
                "require_comments_on_high_risk_approval": self.require_comments_on_high_risk_approval,
            },
        }
