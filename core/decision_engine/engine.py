"""
Decision Engine

Policy-based approval routing that considers:
- Request type (new access, modify, remove, emergency, SoD exception)
- Target system (SAP, Azure AD, etc.)
- Role risk classification
- Organizational scope
- SoD impact (from Risk Engine simulation)
- User classification (employee, contractor, vendor)

Replaces: "if risk == high → 2 approvers, else 1 approver"
"""

from __future__ import annotations

import copy
import hashlib
import logging
from datetime import datetime
from typing import Optional

from .models import (
    ApprovalPolicy,
    ApprovalStep,
    ApprovalStepType,
    ApprovalWorkflow,
    PolicyCondition,
    PolicyConditionOperator,
    RequestType,
    StepStatus,
)

logger = logging.getLogger(__name__)


class DecisionEngine:
    """Routes approval workflows based on configurable policies.

    Policies are evaluated in priority order (lowest number = highest
    priority).  The first matching policy determines the workflow.
    If no policy matches, a default policy applies.
    """

    def __init__(self):
        self._policies: list[ApprovalPolicy] = []
        self._workflows: dict[str, ApprovalWorkflow] = {}
        self._load_default_policies()

    def add_policy(self, policy: ApprovalPolicy) -> None:
        self._policies.append(policy)
        self._policies.sort(key=lambda p: p.priority)

    def set_policies(self, policies: list[ApprovalPolicy]) -> None:
        self._policies = sorted(policies, key=lambda p: p.priority)

    # ------------------------------------------------------------------
    # Workflow creation
    # ------------------------------------------------------------------

    def create_workflow(
        self,
        request_id: str,
        request_type: RequestType,
        user_id: str,
        tenant_id: str,
        context: dict,
    ) -> ApprovalWorkflow:
        """Create an approval workflow for a request.

        context should include:
            risk_level, system, role_type, role_id, department,
            user_type (employee/contractor), sod_violations_count,
            new_violations_count, risk_score, org_scope, ...
        """
        # Find matching policy
        policy = self._find_matching_policy(request_type, context)

        # Build workflow
        wf_id = _make_id(request_id, user_id)
        steps = [copy.deepcopy(s) for s in policy.steps]

        # Resolve dynamic approvers
        for step in steps:
            self._resolve_approver(step, context)

        workflow = ApprovalWorkflow(
            workflow_id=wf_id,
            request_id=request_id,
            request_type=request_type,
            policy_id=policy.policy_id,
            user_id=user_id,
            tenant_id=tenant_id,
            context=context,
            steps=steps,
            risk_score=context.get("risk_score", 0),
            sod_violations_count=context.get("sod_violations_count", 0),
            new_violations_count=context.get("new_violations_count", 0),
        )

        # Handle auto-approve/auto-reject
        if steps and steps[0].step_type == ApprovalStepType.AUTO_APPROVE:
            workflow.is_complete = True
            workflow.final_decision = "approved"
            workflow.completed_at = datetime.utcnow()
            steps[0].status = StepStatus.APPROVED
        elif steps and steps[0].step_type == ApprovalStepType.AUTO_REJECT:
            workflow.is_complete = True
            workflow.final_decision = "rejected"
            workflow.completed_at = datetime.utcnow()
            steps[0].status = StepStatus.REJECTED

        self._workflows[wf_id] = workflow
        self._persist_workflow(workflow)
        return workflow

    # ------------------------------------------------------------------
    # Step processing
    # ------------------------------------------------------------------

    def process_decision(
        self,
        workflow_id: str,
        step_number: int,
        decision: str,  # "approved" | "rejected"
        decided_by: str,
        comments: str = "",
    ) -> ApprovalWorkflow:
        """Process an approval/rejection decision for a workflow step."""
        wf = self._workflows.get(workflow_id)
        if not wf:
            raise ValueError(f"Workflow {workflow_id} not found")

        if wf.is_complete:
            raise ValueError(f"Workflow {workflow_id} is already complete")

        # Find the step
        step = None
        for s in wf.steps:
            if s.step_number == step_number and s.status == StepStatus.PENDING:
                step = s
                break

        if not step:
            raise ValueError(f"Step {step_number} not found or already decided")

        # Record the decision
        step.status = StepStatus.APPROVED if decision == "approved" else StepStatus.REJECTED
        step.decided_by = decided_by
        step.decided_at = datetime.utcnow()
        step.comments = comments

        # If rejected at any step, the whole workflow is rejected
        if decision == "rejected":
            wf.is_complete = True
            wf.final_decision = "rejected"
            wf.completed_at = datetime.utcnow()
            return wf

        # Check if all steps at the current level are approved
        current_level_steps = [s for s in wf.steps if s.step_number == step_number]
        all_approved = all(s.status == StepStatus.APPROVED for s in current_level_steps)

        if all_approved:
            # Move to next step
            next_steps = [s for s in wf.steps
                          if s.step_number > step_number and s.status == StepStatus.PENDING]
            if next_steps:
                wf.current_step = next_steps[0].step_number
            else:
                # All steps complete
                wf.is_complete = True
                wf.final_decision = "approved"
                wf.completed_at = datetime.utcnow()

        return wf

    def escalate_step(
        self,
        workflow_id: str,
        step_number: int,
        escalate_to: str,
        reason: str = "SLA timeout",
    ) -> ApprovalWorkflow:
        """Escalate a pending step to a different approver."""
        wf = self._workflows.get(workflow_id)
        if not wf:
            raise ValueError(f"Workflow {workflow_id} not found")

        for s in wf.steps:
            if s.step_number == step_number and s.status == StepStatus.PENDING:
                s.status = StepStatus.ESCALATED
                s.comments = reason
                # Add new step with escalated approver
                new_step = ApprovalStep(
                    step_number=step_number,
                    step_type=ApprovalStepType.CUSTOM,
                    approver_user_id=escalate_to,
                    sla_hours=24,
                )
                wf.steps.append(new_step)
                break

        return wf

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def get_workflow(self, workflow_id: str) -> Optional[ApprovalWorkflow]:
        return self._workflows.get(workflow_id)

    def get_pending_for_approver(self, approver_id: str) -> list[ApprovalWorkflow]:
        """Get all workflows with a pending step for this approver."""
        result = []
        for wf in self._workflows.values():
            if wf.is_complete:
                continue
            for s in wf.steps:
                if (s.status == StepStatus.PENDING and
                        s.approver_user_id == approver_id):
                    result.append(wf)
                    break
        return result

    def get_overdue_workflows(self) -> list[ApprovalWorkflow]:
        """Get workflows with steps past their SLA."""
        now = datetime.utcnow()
        overdue = []
        for wf in self._workflows.values():
            if wf.is_complete:
                continue
            for s in wf.steps:
                if s.status == StepStatus.PENDING:
                    elapsed = (now - wf.created_at).total_seconds() / 3600
                    if elapsed > s.sla_hours:
                        overdue.append(wf)
                        break
        return overdue

    # ------------------------------------------------------------------
    # Policy matching
    # ------------------------------------------------------------------

    def _find_matching_policy(
        self, request_type: RequestType, context: dict,
    ) -> ApprovalPolicy:
        """Find the first matching policy (sorted by priority)."""
        for policy in self._policies:
            if policy.matches(request_type, context):
                logger.info(f"Policy matched: {policy.policy_id} ({policy.name})")
                return policy

        logger.warning("No policy matched — using fallback default")
        return self._default_policy()

    def _resolve_approver(self, step: ApprovalStep, context: dict) -> None:
        """Resolve dynamic approver references."""
        if step.step_type == ApprovalStepType.MANAGER:
            step.approver_user_id = context.get("manager_user_id")
        elif step.step_type == ApprovalStepType.ROLE_OWNER:
            step.approver_user_id = context.get("role_owner_user_id")
        elif step.step_type == ApprovalStepType.DATA_OWNER:
            step.approver_user_id = context.get("data_owner_user_id")
        # SECURITY_ADMIN and COMPLIANCE are resolved by role, not specific user

    # ------------------------------------------------------------------
    # Default policies
    # ------------------------------------------------------------------

    def _load_default_policies(self) -> None:
        """Load built-in default policies."""
        self._policies = [
            # P1: Emergency access — auto-approve with post-audit
            ApprovalPolicy(
                policy_id="POL-EMERGENCY",
                name="Emergency Access Auto-Approve",
                description="Emergency/firefighter access auto-approved with mandatory post-audit",
                priority=10,
                request_types=[RequestType.EMERGENCY_ACCESS],
                conditions=[],
                steps=[
                    ApprovalStep(step_number=1, step_type=ApprovalStepType.AUTO_APPROVE),
                ],
                require_risk_analysis=False,
            ),

            # P2: Critical risk with SoD violations — requires compliance
            ApprovalPolicy(
                policy_id="POL-CRITICAL-SOD",
                name="Critical Risk with SoD",
                description="Requests that introduce new SoD violations at critical level",
                priority=20,
                request_types=[RequestType.NEW_ACCESS, RequestType.MODIFY_ACCESS],
                conditions=[
                    PolicyCondition("risk_level", PolicyConditionOperator.EQUALS, "critical"),
                    PolicyCondition("new_violations_count", PolicyConditionOperator.GREATER_THAN, 0),
                ],
                steps=[
                    ApprovalStep(step_number=1, step_type=ApprovalStepType.MANAGER, sla_hours=24),
                    ApprovalStep(step_number=2, step_type=ApprovalStepType.ROLE_OWNER, sla_hours=24),
                    ApprovalStep(step_number=3, step_type=ApprovalStepType.SECURITY_ADMIN, sla_hours=24),
                    ApprovalStep(step_number=4, step_type=ApprovalStepType.COMPLIANCE, sla_hours=48),
                ],
                auto_reject_on_critical_sod=False,
                require_justification=True,
            ),

            # P3: High risk — manager + role owner + security
            ApprovalPolicy(
                policy_id="POL-HIGH-RISK",
                name="High Risk Access",
                description="High risk roles or sensitive transactions",
                priority=30,
                request_types=[RequestType.NEW_ACCESS, RequestType.MODIFY_ACCESS],
                conditions=[
                    PolicyCondition("risk_level", PolicyConditionOperator.IN, ["high", "critical"]),
                ],
                steps=[
                    ApprovalStep(step_number=1, step_type=ApprovalStepType.MANAGER, sla_hours=48),
                    ApprovalStep(step_number=2, step_type=ApprovalStepType.ROLE_OWNER, sla_hours=48),
                    ApprovalStep(step_number=3, step_type=ApprovalStepType.SECURITY_ADMIN, sla_hours=48),
                ],
            ),

            # P4: Medium risk — manager + role owner
            ApprovalPolicy(
                policy_id="POL-MEDIUM-RISK",
                name="Medium Risk Access",
                description="Standard access request with moderate risk",
                priority=40,
                request_types=[RequestType.NEW_ACCESS, RequestType.MODIFY_ACCESS],
                conditions=[
                    PolicyCondition("risk_level", PolicyConditionOperator.EQUALS, "medium"),
                ],
                steps=[
                    ApprovalStep(step_number=1, step_type=ApprovalStepType.MANAGER, sla_hours=72),
                    ApprovalStep(step_number=2, step_type=ApprovalStepType.ROLE_OWNER, sla_hours=72),
                ],
            ),

            # P5: Low risk — manager only
            ApprovalPolicy(
                policy_id="POL-LOW-RISK",
                name="Low Risk Access",
                description="Low risk, standard approval",
                priority=50,
                request_types=[RequestType.NEW_ACCESS, RequestType.MODIFY_ACCESS],
                conditions=[
                    PolicyCondition("risk_level", PolicyConditionOperator.EQUALS, "low"),
                ],
                steps=[
                    ApprovalStep(step_number=1, step_type=ApprovalStepType.MANAGER, sla_hours=72),
                ],
            ),

            # P6: Remove access — auto-approve
            ApprovalPolicy(
                policy_id="POL-REMOVE",
                name="Remove Access Auto-Approve",
                description="Removing access is always safe",
                priority=60,
                request_types=[RequestType.REMOVE_ACCESS],
                conditions=[],
                steps=[
                    ApprovalStep(step_number=1, step_type=ApprovalStepType.AUTO_APPROVE),
                ],
                require_risk_analysis=False,
            ),

            # P7: SoD exception — requires security + compliance
            ApprovalPolicy(
                policy_id="POL-SOD-EXCEPTION",
                name="SoD Exception Request",
                description="Requesting an exception to an SoD rule",
                priority=15,
                request_types=[RequestType.SOD_EXCEPTION],
                conditions=[],
                steps=[
                    ApprovalStep(step_number=1, step_type=ApprovalStepType.MANAGER, sla_hours=24),
                    ApprovalStep(step_number=2, step_type=ApprovalStepType.SECURITY_ADMIN, sla_hours=48),
                    ApprovalStep(step_number=3, step_type=ApprovalStepType.COMPLIANCE, sla_hours=48),
                ],
                require_justification=True,
            ),
        ]

    @staticmethod
    def _default_policy() -> ApprovalPolicy:
        """Fallback policy if nothing matches."""
        return ApprovalPolicy(
            policy_id="POL-DEFAULT",
            name="Default Policy",
            description="Fallback: manager approval",
            priority=999,
            steps=[
                ApprovalStep(step_number=1, step_type=ApprovalStepType.MANAGER, sla_hours=72),
            ],
        )


    def _persist_workflow(self, wf: ApprovalWorkflow) -> None:
        """Write-through: persist workflow to database."""
        try:
            from db.database import db_manager
            from db.models.engines import DecisionWorkflowRecord

            with db_manager.session_scope() as session:
                row = DecisionWorkflowRecord(
                    workflow_id=wf.workflow_id,
                    request_id=wf.request_id,
                    request_type=wf.request_type.value if hasattr(wf.request_type, 'value') else str(wf.request_type),
                    policy_id=wf.policy_id,
                    user_id=wf.user_id,
                    tenant_id=wf.tenant_id,
                    current_step=wf.current_step,
                    is_complete=wf.is_complete,
                    final_decision=wf.final_decision,
                    risk_score=wf.risk_score,
                    sod_violations_count=wf.sod_violations_count,
                    new_violations_count=wf.new_violations_count,
                    context=wf.context,
                    steps=[
                        {"step_number": s.step_number, "step_type": s.step_type.value,
                         "approver_user_id": s.approver_user_id,
                         "status": s.status.value, "sla_hours": s.sla_hours}
                        for s in wf.steps
                    ],
                    completed_at=wf.completed_at,
                )
                session.add(row)
        except Exception as exc:
            logger.warning(f"DecisionWorkflow DB persist failed: {exc}")


def _make_id(request_id: str, user_id: str) -> str:
    raw = f"WF:{request_id}:{user_id}"
    return f"WF-{hashlib.sha256(raw.encode()).hexdigest()[:12]}"
