"""
Approval Workflow Engine

Manages approval routing, escalation, and SLA tracking for access requests.
Supports dynamic workflow generation based on risk levels and business rules.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime, timedelta
from enum import Enum
import logging

from .models import (
    AccessRequest, AccessRequestStatus, ApprovalStep,
    ApprovalStatus, ApprovalAction, RequestedAccess
)

logger = logging.getLogger(__name__)


class ApproverType(Enum):
    """Types of approvers"""
    DIRECT_MANAGER = "direct_manager"
    DATA_OWNER = "data_owner"
    ROLE_OWNER = "role_owner"
    SECURITY_TEAM = "security_team"
    RISK_TEAM = "risk_team"
    COMPLIANCE_TEAM = "compliance_team"
    IT_ADMIN = "it_admin"
    SPECIFIC_USER = "specific_user"
    COST_CENTER_OWNER = "cost_center_owner"


@dataclass
class ApprovalRule:
    """
    Defines a rule for when/how approvals are required.

    Rules are evaluated in order and can add approval steps dynamically.
    """
    rule_id: str
    rule_name: str
    description: str

    # Conditions (all must be true for rule to apply)
    conditions: Dict[str, Any] = field(default_factory=dict)
    # Example conditions:
    # - risk_level: ["high", "critical"]
    # - has_sod_violations: True
    # - request_type: ["new_access"]
    # - target_system: ["SAP_PROD"]
    # - role_patterns: ["*_ADMIN", "Z_*"]

    # Approval configuration
    approver_type: ApproverType = ApproverType.DIRECT_MANAGER
    specific_approvers: List[str] = field(default_factory=list)
    step_name: str = ""
    sla_hours: int = 48
    require_all: bool = False  # All approvers must approve

    # Options
    can_skip_if_self: bool = False  # Skip if approver is requester
    auto_approve_if_low_risk: bool = False
    priority: int = 100  # Lower = evaluated first

    enabled: bool = True

    def evaluate(self, request: AccessRequest) -> bool:
        """Check if this rule applies to the request"""
        if not self.enabled:
            return False

        for condition_key, condition_value in self.conditions.items():
            if not self._check_condition(request, condition_key, condition_value):
                return False

        return True

    def _check_condition(self, request: AccessRequest, key: str, value: Any) -> bool:
        """Evaluate a single condition"""

        if key == "risk_level":
            return request.risk_level in value

        elif key == "has_sod_violations":
            has_violations = len(request.sod_violations) > 0
            return has_violations == value

        elif key == "request_type":
            return request.request_type.value in value

        elif key == "min_risk_score":
            return request.overall_risk_score >= value

        elif key == "max_risk_score":
            return request.overall_risk_score <= value

        elif key == "target_system":
            systems = [item.system for item in request.requested_items]
            return any(s in value for s in systems)

        elif key == "role_patterns":
            # Check if any requested role matches patterns
            import fnmatch
            role_names = [item.access_name for item in request.requested_items]
            for pattern in value:
                for role in role_names:
                    if fnmatch.fnmatch(role, pattern):
                        return True
            return False

        elif key == "is_temporary":
            return request.is_temporary == value

        elif key == "department":
            return request.target_user_department in value

        return True  # Unknown conditions pass by default


class WorkflowEngine:
    """
    Manages approval workflows for access requests.

    Features:
    - Dynamic workflow generation based on risk
    - Multi-level approval routing
    - SLA tracking and escalation
    - Delegation support
    """

    def __init__(self,
                 user_resolver: Optional[Callable] = None,
                 notification_handler: Optional[Callable] = None):
        """
        Initialize workflow engine.

        Args:
            user_resolver: Function to resolve user details (manager, etc.)
            notification_handler: Function to send notifications
        """
        self.user_resolver = user_resolver or self._default_user_resolver
        self.notification_handler = notification_handler

        # Approval rules (loaded from config or database)
        self.rules: List[ApprovalRule] = []
        self._load_default_rules()

        # Configuration
        self.config = {
            "default_sla_hours": 48,
            "escalation_after_hours": 72,
            "max_approval_levels": 5,
            "auto_approve_low_risk": False,
            "require_manager_approval": True
        }

    def _load_default_rules(self):
        """Load default approval rules"""

        # Rule 1: Manager approval always required
        self.rules.append(ApprovalRule(
            rule_id="RULE_MGR_001",
            rule_name="Manager Approval",
            description="Direct manager must approve all access requests",
            conditions={},  # Applies to all
            approver_type=ApproverType.DIRECT_MANAGER,
            step_name="Manager Approval",
            sla_hours=48,
            priority=10
        ))

        # Rule 2: Security team for high/critical risk
        self.rules.append(ApprovalRule(
            rule_id="RULE_SEC_001",
            rule_name="Security Review - High Risk",
            description="Security team review for high/critical risk requests",
            conditions={
                "risk_level": ["high", "critical"]
            },
            approver_type=ApproverType.SECURITY_TEAM,
            specific_approvers=["security.team@company.com"],
            step_name="Security Review",
            sla_hours=24,
            priority=20
        ))

        # Rule 3: Role owner approval
        self.rules.append(ApprovalRule(
            rule_id="RULE_OWNER_001",
            rule_name="Role Owner Approval",
            description="Role owner must approve sensitive role assignments",
            conditions={
                "role_patterns": ["*_ADMIN", "Z_SENSITIVE_*", "SAP_*"]
            },
            approver_type=ApproverType.ROLE_OWNER,
            step_name="Role Owner Approval",
            sla_hours=48,
            priority=30
        ))

        # Rule 4: Compliance team for SoD violations
        self.rules.append(ApprovalRule(
            rule_id="RULE_COMP_001",
            rule_name="Compliance Review - SoD",
            description="Compliance team must review requests with SoD violations",
            conditions={
                "has_sod_violations": True
            },
            approver_type=ApproverType.COMPLIANCE_TEAM,
            specific_approvers=["compliance.team@company.com"],
            step_name="Compliance Review",
            sla_hours=72,
            priority=25
        ))

        # Rule 5: IT Admin for production systems
        self.rules.append(ApprovalRule(
            rule_id="RULE_IT_001",
            rule_name="IT Admin - Production",
            description="IT Admin approval for production system access",
            conditions={
                "target_system": ["SAP_PROD", "PROD", "PRD"]
            },
            approver_type=ApproverType.IT_ADMIN,
            specific_approvers=["it.admin@company.com"],
            step_name="IT Admin Approval",
            sla_hours=24,
            priority=40
        ))

        # Sort by priority
        self.rules.sort(key=lambda r: r.priority)

    def _default_user_resolver(self, user_id: str, info_type: str) -> Optional[str]:
        """Default user resolver - should be overridden"""
        # Returns mock data for testing
        mock_managers = {
            "JSMITH": "manager1@company.com",
            "MBROWN": "manager2@company.com",
            "default": "default.manager@company.com"
        }

        if info_type == "manager":
            return mock_managers.get(user_id, mock_managers["default"])
        elif info_type == "email":
            return f"{user_id.lower()}@company.com"
        elif info_type == "name":
            return user_id

        return None

    def generate_workflow(self, request: AccessRequest) -> List[ApprovalStep]:
        """
        Generate approval workflow based on request characteristics.

        Evaluates all rules and builds the approval chain.
        """
        steps = []
        step_number = 1

        for rule in self.rules:
            if rule.evaluate(request):
                step = self._create_approval_step(request, rule, step_number)
                if step:
                    steps.append(step)
                    step_number += 1

                    # Check max levels
                    if step_number > self.config["max_approval_levels"]:
                        logger.warning(f"Max approval levels reached for request {request.request_id}")
                        break

        # If no steps generated, add default manager approval
        if not steps and self.config["require_manager_approval"]:
            steps.append(self._create_manager_step(request, 1))

        # Set due dates
        for step in steps:
            step.due_date = datetime.now() + timedelta(hours=step.sla_hours)

        return steps

    def _create_approval_step(self, request: AccessRequest,
                             rule: ApprovalRule, step_number: int) -> Optional[ApprovalStep]:
        """Create an approval step from a rule"""

        approvers = self._resolve_approvers(request, rule)

        if not approvers:
            logger.warning(f"No approvers found for rule {rule.rule_id}")
            return None

        # Check if we should skip (e.g., approver is requester)
        if rule.can_skip_if_self:
            if request.requester_user_id in approvers:
                return None

        return ApprovalStep(
            step_number=step_number,
            step_name=rule.step_name,
            step_type="approval",
            approver_type=rule.approver_type.value,
            approver_ids=approvers,
            approver_names=[self.user_resolver(a, "name") or a for a in approvers],
            require_all=rule.require_all,
            status=ApprovalStatus.PENDING,
            sla_hours=rule.sla_hours
        )

    def _create_manager_step(self, request: AccessRequest, step_number: int) -> ApprovalStep:
        """Create default manager approval step"""
        manager_id = self.user_resolver(request.target_user_id, "manager")

        return ApprovalStep(
            step_number=step_number,
            step_name="Manager Approval",
            step_type="approval",
            approver_type="manager",
            approver_ids=[manager_id] if manager_id else ["default.manager@company.com"],
            require_all=False,
            status=ApprovalStatus.PENDING,
            sla_hours=self.config["default_sla_hours"]
        )

    def _resolve_approvers(self, request: AccessRequest,
                          rule: ApprovalRule) -> List[str]:
        """Resolve actual approver IDs based on rule type"""

        if rule.specific_approvers:
            return rule.specific_approvers

        approver_type = rule.approver_type

        if approver_type == ApproverType.DIRECT_MANAGER:
            manager = self.user_resolver(request.target_user_id, "manager")
            return [manager] if manager else []

        elif approver_type == ApproverType.SECURITY_TEAM:
            return ["security.team@company.com"]

        elif approver_type == ApproverType.COMPLIANCE_TEAM:
            return ["compliance.team@company.com"]

        elif approver_type == ApproverType.IT_ADMIN:
            return ["it.admin@company.com"]

        elif approver_type == ApproverType.ROLE_OWNER:
            # Would look up role owner from role catalog
            return ["role.owner@company.com"]

        elif approver_type == ApproverType.DATA_OWNER:
            return ["data.owner@company.com"]

        return []

    async def process_approval_action(self,
                                     request: AccessRequest,
                                     step_id: str,
                                     action: ApprovalAction,
                                     actor_id: str,
                                     comments: str = "",
                                     delegate_to: Optional[str] = None) -> AccessRequest:
        """
        Process an approval action on a request.

        Args:
            request: The access request
            step_id: ID of the approval step
            action: Action being taken
            actor_id: User taking the action
            comments: Optional comments
            delegate_to: For delegation, the new approver

        Returns:
            Updated AccessRequest
        """

        # Find the step
        step = None
        step_index = -1
        for i, s in enumerate(request.approval_steps):
            if s.step_id == step_id:
                step = s
                step_index = i
                break

        if not step:
            raise ValueError(f"Approval step {step_id} not found")

        if step.status != ApprovalStatus.PENDING:
            raise ValueError(f"Step is not pending (status: {step.status.value})")

        # Verify actor is authorized
        if actor_id not in step.approver_ids:
            # Check if delegated
            if step.delegated_to != actor_id:
                raise PermissionError(f"User {actor_id} is not authorized to approve this step")

        # Process the action
        step.actioned_by = actor_id
        step.actioned_by_name = self.user_resolver(actor_id, "name")
        step.actioned_at = datetime.now()
        step.action = action
        step.comments = comments

        if action == ApprovalAction.APPROVE:
            step.status = ApprovalStatus.APPROVED
            # Move to next step
            request.current_step = step_index + 1

            # Check if fully approved
            if request.is_fully_approved():
                request.status = AccessRequestStatus.APPROVED
                request.final_decision = "approved"
                request.final_decision_by = actor_id
                request.final_decision_at = datetime.now()

        elif action == ApprovalAction.REJECT:
            step.status = ApprovalStatus.REJECTED
            request.status = AccessRequestStatus.REJECTED
            request.final_decision = "rejected"
            request.final_decision_by = actor_id
            request.final_decision_at = datetime.now()
            request.rejection_reason = comments

        elif action == ApprovalAction.DELEGATE:
            if not delegate_to:
                raise ValueError("Delegation requires delegate_to parameter")
            step.status = ApprovalStatus.DELEGATED
            step.delegated_to = delegate_to
            step.delegated_by = actor_id
            # Reset status to pending for new approver
            step.status = ApprovalStatus.PENDING
            step.approver_ids = [delegate_to]

        elif action == ApprovalAction.ESCALATE:
            step.status = ApprovalStatus.ESCALATED
            step.escalation_triggered = True
            # Would trigger escalation workflow

        elif action == ApprovalAction.REQUEST_INFO:
            # Keep pending but record the request
            step.comments = f"[INFO REQUESTED] {comments}"
            # Would notify requester

        request.last_updated_at = datetime.now()

        # Send notifications
        if self.notification_handler:
            await self._send_notifications(request, step, action)

        return request

    async def _send_notifications(self, request: AccessRequest,
                                 step: ApprovalStep, action: ApprovalAction):
        """Send appropriate notifications"""
        if not self.notification_handler:
            return

        if action == ApprovalAction.APPROVE:
            # Notify requester of progress
            await self.notification_handler(
                recipient=request.requester_email,
                subject=f"Access Request {request.request_id} - Step Approved",
                message=f"Step '{step.step_name}' has been approved."
            )

            # If fully approved, notify for provisioning
            if request.status == AccessRequestStatus.APPROVED:
                await self.notification_handler(
                    recipient=request.requester_email,
                    subject=f"Access Request {request.request_id} - Fully Approved",
                    message="Your access request has been fully approved and will be provisioned."
                )

        elif action == ApprovalAction.REJECT:
            await self.notification_handler(
                recipient=request.requester_email,
                subject=f"Access Request {request.request_id} - Rejected",
                message=f"Your request was rejected. Reason: {step.comments}"
            )

    async def check_sla_and_escalate(self, requests: List[AccessRequest]):
        """
        Check SLA status and trigger escalations for overdue requests.

        Should be called periodically (e.g., every hour).
        """
        for request in requests:
            if request.status != AccessRequestStatus.PENDING_APPROVAL:
                continue

            for step in request.approval_steps:
                if step.status != ApprovalStatus.PENDING:
                    continue

                if step.is_overdue() and not step.escalation_triggered:
                    # Trigger escalation
                    await self._escalate_step(request, step)

    async def _escalate_step(self, request: AccessRequest, step: ApprovalStep):
        """Escalate an overdue approval step"""
        step.escalation_triggered = True

        # Get escalation target (e.g., approver's manager)
        escalation_target = None
        if step.approver_ids:
            escalation_target = self.user_resolver(step.approver_ids[0], "manager")

        if escalation_target:
            step.approver_ids.append(escalation_target)

        # Send notifications
        if self.notification_handler:
            # Notify original approvers
            for approver in step.approver_ids:
                await self.notification_handler(
                    recipient=self.user_resolver(approver, "email") or approver,
                    subject=f"[ESCALATION] Access Request {request.request_id} Overdue",
                    message=f"Request is overdue for approval. Please take action immediately."
                )

        logger.warning(f"Escalated step {step.step_id} for request {request.request_id}")

    def get_pending_approvals_for_user(self, user_id: str,
                                      requests: List[AccessRequest]) -> List[Dict]:
        """Get all pending approvals for a specific user"""
        pending = []

        for request in requests:
            if request.status != AccessRequestStatus.PENDING_APPROVAL:
                continue

            for step in request.approval_steps:
                if step.status != ApprovalStatus.PENDING:
                    continue

                if user_id in step.approver_ids or step.delegated_to == user_id:
                    pending.append({
                        "request_id": request.request_id,
                        "request_summary": request.to_summary(),
                        "step": step.to_dict(),
                        "is_overdue": step.is_overdue(),
                        "days_pending": (datetime.now() - request.submitted_at).days if request.submitted_at else 0
                    })

        return pending

    def add_rule(self, rule: ApprovalRule):
        """Add a new approval rule"""
        self.rules.append(rule)
        self.rules.sort(key=lambda r: r.priority)

    def remove_rule(self, rule_id: str):
        """Remove an approval rule"""
        self.rules = [r for r in self.rules if r.rule_id != rule_id]
