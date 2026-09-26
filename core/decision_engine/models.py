"""
Decision Engine — Data Models

Policy-based approval routing and decision models.
Replaces the demo-grade "if risk=high → 2 approvers" logic.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Any


class ApprovalStepType(enum.Enum):
    MANAGER = "manager"
    ROLE_OWNER = "role_owner"
    SECURITY_ADMIN = "security_admin"
    DATA_OWNER = "data_owner"
    COMPLIANCE = "compliance"
    CUSTOM = "custom"
    AUTO_APPROVE = "auto_approve"
    AUTO_REJECT = "auto_reject"


class StepStatus(enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    ESCALATED = "escalated"
    SKIPPED = "skipped"
    TIMED_OUT = "timed_out"


class RequestType(enum.Enum):
    NEW_ACCESS = "new_access"
    MODIFY_ACCESS = "modify_access"
    REMOVE_ACCESS = "remove_access"
    EMERGENCY_ACCESS = "emergency_access"
    ROLE_CHANGE = "role_change"
    SOD_EXCEPTION = "sod_exception"
    MITIGATION_APPROVAL = "mitigation_approval"


class PolicyConditionOperator(enum.Enum):
    EQUALS = "eq"
    NOT_EQUALS = "ne"
    IN = "in"
    NOT_IN = "not_in"
    GREATER_THAN = "gt"
    LESS_THAN = "lt"
    CONTAINS = "contains"
    MATCHES = "matches"  # regex


@dataclass
class PolicyCondition:
    """A single condition in a policy rule."""
    field: str                         # e.g., "risk_level", "system", "role_type"
    operator: PolicyConditionOperator
    value: Any                         # e.g., "critical", ["SAP", "Azure"], 50

    def evaluate(self, context: dict) -> bool:
        """Evaluate this condition against a request context."""
        actual = context.get(self.field)
        if actual is None:
            return False

        if self.operator == PolicyConditionOperator.EQUALS:
            return actual == self.value
        elif self.operator == PolicyConditionOperator.NOT_EQUALS:
            return actual != self.value
        elif self.operator == PolicyConditionOperator.IN:
            return actual in self.value
        elif self.operator == PolicyConditionOperator.NOT_IN:
            return actual not in self.value
        elif self.operator == PolicyConditionOperator.GREATER_THAN:
            return actual > self.value
        elif self.operator == PolicyConditionOperator.LESS_THAN:
            return actual < self.value
        elif self.operator == PolicyConditionOperator.CONTAINS:
            return self.value in str(actual)
        return False

    def to_dict(self) -> dict:
        return {
            "field": self.field,
            "operator": self.operator.value,
            "value": self.value,
        }


@dataclass
class ApprovalStep:
    """A single step in an approval workflow."""
    step_number: int
    step_type: ApprovalStepType
    approver_user_id: Optional[str] = None  # specific approver
    approver_role: Optional[str] = None     # role-based resolution
    sla_hours: int = 48                      # auto-escalate after
    is_parallel: bool = False                # parallel with other steps at same number
    can_delegate: bool = True

    # Runtime state
    status: StepStatus = StepStatus.PENDING
    decided_by: Optional[str] = None
    decided_at: Optional[datetime] = None
    comments: str = ""
    delegated_to: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "step_number": self.step_number,
            "step_type": self.step_type.value,
            "approver_user_id": self.approver_user_id,
            "approver_role": self.approver_role,
            "sla_hours": self.sla_hours,
            "status": self.status.value,
            "decided_by": self.decided_by,
            "decided_at": self.decided_at.isoformat() if self.decided_at else None,
            "comments": self.comments,
        }


@dataclass
class ApprovalPolicy:
    """A policy that defines when and how to route approvals.

    Example:
        name: "High-risk SAP access"
        conditions: [risk_level == "high", system == "SAP"]
        steps: [manager → role_owner → security_admin]
    """
    policy_id: str
    name: str
    description: str
    priority: int = 100  # lower = higher priority, first match wins

    # When this policy applies
    request_types: list[RequestType] = field(default_factory=list)
    conditions: list[PolicyCondition] = field(default_factory=list)

    # What approval steps to follow
    steps: list[ApprovalStep] = field(default_factory=list)

    # Settings
    is_active: bool = True
    require_risk_analysis: bool = True
    auto_reject_on_critical_sod: bool = False
    require_justification: bool = True

    def matches(self, request_type: RequestType, context: dict) -> bool:
        """Check if this policy applies to a given request."""
        if not self.is_active:
            return False
        if self.request_types and request_type not in self.request_types:
            return False
        return all(c.evaluate(context) for c in self.conditions)

    def to_dict(self) -> dict:
        return {
            "policy_id": self.policy_id,
            "name": self.name,
            "description": self.description,
            "priority": self.priority,
            "request_types": [rt.value for rt in self.request_types],
            "conditions": [c.to_dict() for c in self.conditions],
            "steps": [s.to_dict() for s in self.steps],
            "is_active": self.is_active,
        }


@dataclass
class ApprovalWorkflow:
    """A running approval workflow instance for a specific request."""
    workflow_id: str
    request_id: str
    request_type: RequestType
    policy_id: str
    user_id: str        # requestor
    tenant_id: str

    # Request context used for policy matching
    context: dict = field(default_factory=dict)

    # Steps (copied from policy, with runtime state)
    steps: list[ApprovalStep] = field(default_factory=list)

    # Overall status
    current_step: int = 1
    is_complete: bool = False
    final_decision: Optional[str] = None  # "approved" | "rejected"
    completed_at: Optional[datetime] = None

    # Risk analysis result (attached)
    risk_score: float = 0.0
    sod_violations_count: int = 0
    new_violations_count: int = 0

    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "workflow_id": self.workflow_id,
            "request_id": self.request_id,
            "request_type": self.request_type.value,
            "policy_id": self.policy_id,
            "user_id": self.user_id,
            "current_step": self.current_step,
            "is_complete": self.is_complete,
            "final_decision": self.final_decision,
            "risk_score": self.risk_score,
            "sod_violations_count": self.sod_violations_count,
            "steps": [s.to_dict() for s in self.steps],
            "created_at": self.created_at.isoformat(),
        }
