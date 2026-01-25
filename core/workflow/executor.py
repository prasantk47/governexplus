# Workflow Executor
# State machine for workflow execution

"""
Workflow Executor for GOVERNEX+.

Manages workflow state transitions:
- Step activation/completion
- Decision recording
- Status management
- Audit trail
- Provisioning triggers

Key Principle:
Deterministic state machine with full auditability.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
from enum import Enum
import logging

from .models import (
    Workflow, WorkflowStep, WorkflowStatus, StepStatus,
    StepDecision, WorkflowDecision, WorkflowContext
)
from .sla import SLAManager, EscalationTrigger

logger = logging.getLogger(__name__)


class EventType(Enum):
    """Types of workflow events."""
    WORKFLOW_CREATED = "WORKFLOW_CREATED"
    WORKFLOW_SUBMITTED = "WORKFLOW_SUBMITTED"
    WORKFLOW_APPROVED = "WORKFLOW_APPROVED"
    WORKFLOW_REJECTED = "WORKFLOW_REJECTED"
    WORKFLOW_CANCELLED = "WORKFLOW_CANCELLED"
    WORKFLOW_COMPLETED = "WORKFLOW_COMPLETED"
    STEP_ACTIVATED = "STEP_ACTIVATED"
    STEP_APPROVED = "STEP_APPROVED"
    STEP_REJECTED = "STEP_REJECTED"
    STEP_DELEGATED = "STEP_DELEGATED"
    STEP_ESCALATED = "STEP_ESCALATED"
    STEP_SKIPPED = "STEP_SKIPPED"
    STEP_TIMED_OUT = "STEP_TIMED_OUT"
    DECISION_RECORDED = "DECISION_RECORDED"
    PROVISIONING_STARTED = "PROVISIONING_STARTED"
    PROVISIONING_COMPLETED = "PROVISIONING_COMPLETED"
    PROVISIONING_FAILED = "PROVISIONING_FAILED"


@dataclass
class ExecutionEvent:
    """An event during workflow execution."""
    event_id: str = ""
    event_type: EventType = EventType.WORKFLOW_CREATED
    workflow_id: str = ""
    step_id: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    actor: str = ""
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "workflow_id": self.workflow_id,
            "step_id": self.step_id,
            "timestamp": self.timestamp.isoformat(),
            "actor": self.actor,
            "details": self.details,
        }


@dataclass
class ExecutionResult:
    """Result of an execution action."""
    success: bool = True
    event: Optional[ExecutionEvent] = None
    new_status: Optional[str] = None
    message: str = ""
    errors: List[str] = field(default_factory=list)
    next_actions: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "event": self.event.to_dict() if self.event else None,
            "new_status": self.new_status,
            "message": self.message,
            "errors": self.errors,
            "next_actions": self.next_actions,
        }


class WorkflowExecutor:
    """
    Executes workflow state transitions.

    Manages the complete lifecycle of a workflow.
    """

    def __init__(self, sla_manager: Optional[SLAManager] = None):
        """Initialize executor."""
        self.sla_manager = sla_manager or SLAManager()

        # Event history
        self._events: List[ExecutionEvent] = []

        # Callbacks
        self._on_workflow_complete: Optional[Callable[[Workflow], None]] = None
        self._on_step_complete: Optional[Callable[[Workflow, WorkflowStep], None]] = None
        self._on_provision: Optional[Callable[[Workflow], bool]] = None

        # Event counter for IDs
        self._event_counter = 0

    def _create_event(
        self,
        event_type: EventType,
        workflow: Workflow,
        step: Optional[WorkflowStep] = None,
        actor: str = "",
        details: Optional[Dict[str, Any]] = None
    ) -> ExecutionEvent:
        """Create an execution event."""
        self._event_counter += 1
        event = ExecutionEvent(
            event_id=f"EVT-{datetime.now().strftime('%Y%m%d%H%M%S')}-{self._event_counter:04d}",
            event_type=event_type,
            workflow_id=workflow.workflow_id,
            step_id=step.step_id if step else None,
            actor=actor,
            details=details or {},
        )
        self._events.append(event)

        # Add to workflow audit log
        workflow.add_audit_entry(event_type.value, event.to_dict())

        return event

    def submit(self, workflow: Workflow, submitted_by: str = "") -> ExecutionResult:
        """
        Submit a workflow for processing.

        Activates the first step(s).
        """
        if workflow.status not in [WorkflowStatus.DRAFT, WorkflowStatus.PENDING]:
            return ExecutionResult(
                success=False,
                message=f"Cannot submit workflow in status {workflow.status.value}",
                errors=[f"Invalid status: {workflow.status.value}"],
            )

        # Handle auto-approved workflows
        if workflow.status == WorkflowStatus.AUTO_APPROVED:
            workflow.submitted_at = datetime.now()
            workflow.completed_at = datetime.now()

            event = self._create_event(
                EventType.WORKFLOW_APPROVED,
                workflow,
                actor=submitted_by,
                details={"auto_approved": True, "reason": workflow.assembly_explanation},
            )

            return ExecutionResult(
                success=True,
                event=event,
                new_status=WorkflowStatus.AUTO_APPROVED.value,
                message="Workflow auto-approved",
                next_actions=["PROVISION"],
            )

        # Handle auto-rejected workflows
        if workflow.status == WorkflowStatus.AUTO_REJECTED:
            workflow.submitted_at = datetime.now()
            workflow.completed_at = datetime.now()

            event = self._create_event(
                EventType.WORKFLOW_REJECTED,
                workflow,
                actor=submitted_by,
                details={"auto_rejected": True, "reason": workflow.assembly_explanation},
            )

            return ExecutionResult(
                success=True,
                event=event,
                new_status=WorkflowStatus.AUTO_REJECTED.value,
                message="Workflow auto-rejected",
            )

        # Normal submission
        workflow.status = WorkflowStatus.IN_PROGRESS
        workflow.submitted_at = datetime.now()

        event = self._create_event(
            EventType.WORKFLOW_SUBMITTED,
            workflow,
            actor=submitted_by,
        )

        # Activate first step
        if workflow.steps:
            self._activate_step(workflow, workflow.steps[0], submitted_by)

        return ExecutionResult(
            success=True,
            event=event,
            new_status=WorkflowStatus.IN_PROGRESS.value,
            message=f"Workflow submitted with {len(workflow.steps)} step(s)",
            next_actions=["AWAIT_APPROVAL"],
        )

    def _activate_step(
        self,
        workflow: Workflow,
        step: WorkflowStep,
        actor: str = ""
    ) -> None:
        """Activate a workflow step."""
        step.status = StepStatus.ACTIVE
        step.activated_at = datetime.now()
        workflow.status = WorkflowStatus.WAITING_APPROVAL

        self._create_event(
            EventType.STEP_ACTIVATED,
            workflow,
            step,
            actor=actor,
            details={
                "approver_id": step.approver_id,
                "approver_type": step.approver_type.value,
                "sla_hours": step.sla_hours,
            },
        )

    def record_decision(
        self,
        workflow: Workflow,
        step_id: str,
        decision: str,  # APPROVED, REJECTED
        decided_by: str,
        comments: str = ""
    ) -> ExecutionResult:
        """
        Record an approval decision on a step.

        Args:
            workflow: The workflow
            step_id: Step to record decision for
            decision: APPROVED or REJECTED
            decided_by: Who made the decision
            comments: Optional comments

        Returns:
            ExecutionResult
        """
        # Find the step
        step = next((s for s in workflow.steps if s.step_id == step_id), None)
        if not step:
            return ExecutionResult(
                success=False,
                message=f"Step {step_id} not found",
                errors=["Step not found"],
            )

        # Validate step is active
        if step.status != StepStatus.ACTIVE:
            return ExecutionResult(
                success=False,
                message=f"Step is not active (status: {step.status.value})",
                errors=["Step not active"],
            )

        # Validate decision
        decision = decision.upper()
        if decision not in ["APPROVED", "REJECTED"]:
            return ExecutionResult(
                success=False,
                message=f"Invalid decision: {decision}",
                errors=["Invalid decision"],
            )

        # Record decision
        step.status = StepStatus.APPROVED if decision == "APPROVED" else StepStatus.REJECTED
        step.decision = decision
        step.decision_comments = comments
        step.decided_by = decided_by
        step.decided_at = datetime.now()

        event_type = EventType.STEP_APPROVED if decision == "APPROVED" else EventType.STEP_REJECTED

        event = self._create_event(
            event_type,
            workflow,
            step,
            actor=decided_by,
            details={
                "decision": decision,
                "comments": comments,
            },
        )

        # Determine next action
        if decision == "REJECTED":
            return self._handle_rejection(workflow, step, decided_by)
        else:
            return self._handle_approval(workflow, step, decided_by)

    def _handle_approval(
        self,
        workflow: Workflow,
        step: WorkflowStep,
        actor: str
    ) -> ExecutionResult:
        """Handle step approval - advance workflow."""
        # Call step complete callback
        if self._on_step_complete:
            try:
                self._on_step_complete(workflow, step)
            except Exception as e:
                logger.error(f"Step complete callback failed: {e}")

        # Check if there are more steps
        current_index = workflow.steps.index(step)

        if current_index < len(workflow.steps) - 1:
            # Activate next step
            next_step = workflow.steps[current_index + 1]
            self._activate_step(workflow, next_step, actor)
            workflow.current_step_index = current_index + 1

            return ExecutionResult(
                success=True,
                new_status=WorkflowStatus.WAITING_APPROVAL.value,
                message=f"Step approved. Awaiting {next_step.approver_type.value} approval.",
                next_actions=["AWAIT_APPROVAL"],
            )
        else:
            # All steps complete - workflow approved
            return self._complete_workflow(workflow, "APPROVED", actor)

    def _handle_rejection(
        self,
        workflow: Workflow,
        step: WorkflowStep,
        actor: str
    ) -> ExecutionResult:
        """Handle step rejection - workflow rejected."""
        return self._complete_workflow(workflow, "REJECTED", actor)

    def _complete_workflow(
        self,
        workflow: Workflow,
        decision: str,
        actor: str
    ) -> ExecutionResult:
        """Complete the workflow."""
        workflow.final_decision = decision
        workflow.final_decision_at = datetime.now()
        workflow.completed_at = datetime.now()

        if decision == "APPROVED":
            workflow.status = WorkflowStatus.APPROVED
            event_type = EventType.WORKFLOW_APPROVED
        else:
            workflow.status = WorkflowStatus.REJECTED
            event_type = EventType.WORKFLOW_REJECTED

        event = self._create_event(
            event_type,
            workflow,
            actor=actor,
            details={"final_decision": decision},
        )

        # Call workflow complete callback
        if self._on_workflow_complete:
            try:
                self._on_workflow_complete(workflow)
            except Exception as e:
                logger.error(f"Workflow complete callback failed: {e}")

        next_actions = []
        if decision == "APPROVED":
            next_actions = ["PROVISION"]

        return ExecutionResult(
            success=True,
            event=event,
            new_status=workflow.status.value,
            message=f"Workflow {decision.lower()}",
            next_actions=next_actions,
        )

    def delegate(
        self,
        workflow: Workflow,
        step_id: str,
        delegated_by: str,
        delegate_to_id: str,
        delegate_to_name: str,
        reason: str = ""
    ) -> ExecutionResult:
        """
        Delegate a step to another approver.
        """
        step = next((s for s in workflow.steps if s.step_id == step_id), None)
        if not step:
            return ExecutionResult(
                success=False,
                message=f"Step {step_id} not found",
                errors=["Step not found"],
            )

        if not step.allow_delegation:
            return ExecutionResult(
                success=False,
                message="Delegation not allowed for this step",
                errors=["Delegation not allowed"],
            )

        # Record delegation
        original_approver = step.approver_id
        step.delegation_history.append({
            "from": original_approver,
            "to": delegate_to_id,
            "delegated_by": delegated_by,
            "delegated_at": datetime.now().isoformat(),
            "reason": reason,
        })

        step.approver_id = delegate_to_id
        step.approver_name = delegate_to_name
        step.status = StepStatus.DELEGATED

        event = self._create_event(
            EventType.STEP_DELEGATED,
            workflow,
            step,
            actor=delegated_by,
            details={
                "from": original_approver,
                "to": delegate_to_id,
                "reason": reason,
            },
        )

        # Reactivate step
        step.status = StepStatus.ACTIVE

        return ExecutionResult(
            success=True,
            event=event,
            new_status=StepStatus.ACTIVE.value,
            message=f"Delegated to {delegate_to_name}",
            next_actions=["AWAIT_APPROVAL"],
        )

    def escalate(
        self,
        workflow: Workflow,
        step_id: str,
        escalated_by: str,
        escalate_to_id: str,
        escalate_to_name: str,
        trigger: EscalationTrigger = EscalationTrigger.MANUAL,
        reason: str = ""
    ) -> ExecutionResult:
        """
        Escalate a step to a higher authority.
        """
        step = next((s for s in workflow.steps if s.step_id == step_id), None)
        if not step:
            return ExecutionResult(
                success=False,
                message=f"Step {step_id} not found",
                errors=["Step not found"],
            )

        # Record escalation
        original_approver = step.approver_id
        step.escalation_history.append({
            "from": original_approver,
            "to": escalate_to_id,
            "escalated_by": escalated_by,
            "escalated_at": datetime.now().isoformat(),
            "trigger": trigger.value,
            "reason": reason,
        })

        step.approver_id = escalate_to_id
        step.approver_name = escalate_to_name
        step.status = StepStatus.ESCALATED

        # Create SLA escalation action
        escalation_action = self.sla_manager.create_escalation(
            step, workflow, trigger,
            to_approver_id=escalate_to_id,
            reason=reason
        )

        event = self._create_event(
            EventType.STEP_ESCALATED,
            workflow,
            step,
            actor=escalated_by,
            details={
                "from": original_approver,
                "to": escalate_to_id,
                "trigger": trigger.value,
                "reason": reason,
                "escalation_id": escalation_action.action_id,
            },
        )

        # Reactivate step
        step.status = StepStatus.ACTIVE
        step.activated_at = datetime.now()  # Reset SLA

        return ExecutionResult(
            success=True,
            event=event,
            new_status=StepStatus.ACTIVE.value,
            message=f"Escalated to {escalate_to_name}",
            next_actions=["AWAIT_APPROVAL"],
        )

    def cancel(
        self,
        workflow: Workflow,
        cancelled_by: str,
        reason: str = ""
    ) -> ExecutionResult:
        """
        Cancel a workflow.
        """
        if workflow.is_complete():
            return ExecutionResult(
                success=False,
                message="Cannot cancel a completed workflow",
                errors=["Workflow already complete"],
            )

        workflow.status = WorkflowStatus.CANCELLED
        workflow.completed_at = datetime.now()

        # Mark all pending steps as cancelled
        for step in workflow.steps:
            if step.is_pending():
                step.status = StepStatus.CANCELLED

        event = self._create_event(
            EventType.WORKFLOW_CANCELLED,
            workflow,
            actor=cancelled_by,
            details={"reason": reason},
        )

        return ExecutionResult(
            success=True,
            event=event,
            new_status=WorkflowStatus.CANCELLED.value,
            message="Workflow cancelled",
        )

    def provision(
        self,
        workflow: Workflow,
        provisioned_by: str = "SYSTEM"
    ) -> ExecutionResult:
        """
        Trigger provisioning for an approved workflow.
        """
        if workflow.final_decision != "APPROVED":
            return ExecutionResult(
                success=False,
                message="Can only provision approved workflows",
                errors=["Workflow not approved"],
            )

        workflow.status = WorkflowStatus.PROVISIONING

        event = self._create_event(
            EventType.PROVISIONING_STARTED,
            workflow,
            actor=provisioned_by,
        )

        # Call provisioning callback
        provision_success = True
        if self._on_provision:
            try:
                provision_success = self._on_provision(workflow)
            except Exception as e:
                logger.error(f"Provisioning failed: {e}")
                provision_success = False

        if provision_success:
            workflow.status = WorkflowStatus.COMPLETED

            self._create_event(
                EventType.PROVISIONING_COMPLETED,
                workflow,
                actor=provisioned_by,
            )

            return ExecutionResult(
                success=True,
                new_status=WorkflowStatus.COMPLETED.value,
                message="Provisioning completed",
            )
        else:
            workflow.status = WorkflowStatus.FAILED

            self._create_event(
                EventType.PROVISIONING_FAILED,
                workflow,
                actor=provisioned_by,
            )

            return ExecutionResult(
                success=False,
                new_status=WorkflowStatus.FAILED.value,
                message="Provisioning failed",
                errors=["Provisioning callback returned failure"],
            )

    def register_callbacks(
        self,
        on_workflow_complete: Optional[Callable[[Workflow], None]] = None,
        on_step_complete: Optional[Callable[[Workflow, WorkflowStep], None]] = None,
        on_provision: Optional[Callable[[Workflow], bool]] = None
    ) -> None:
        """Register callback functions."""
        self._on_workflow_complete = on_workflow_complete
        self._on_step_complete = on_step_complete
        self._on_provision = on_provision

    def get_events(
        self,
        workflow_id: Optional[str] = None,
        event_types: Optional[List[EventType]] = None,
        since: Optional[datetime] = None
    ) -> List[ExecutionEvent]:
        """Get execution events with optional filtering."""
        events = self._events

        if workflow_id:
            events = [e for e in events if e.workflow_id == workflow_id]

        if event_types:
            events = [e for e in events if e.event_type in event_types]

        if since:
            events = [e for e in events if e.timestamp >= since]

        return sorted(events, key=lambda e: e.timestamp, reverse=True)

    def get_workflow_status(self, workflow: Workflow) -> Dict[str, Any]:
        """Get comprehensive workflow status."""
        sla_status = self.sla_manager.check_workflow_sla(workflow)

        current_step = workflow.get_current_step()

        return {
            "workflow_id": workflow.workflow_id,
            "status": workflow.status.value,
            "progress": {
                "total_steps": len(workflow.steps),
                "completed_steps": len(workflow.get_completed_steps()),
                "current_step_index": workflow.current_step_index,
            },
            "current_step": {
                "step_id": current_step.step_id if current_step else None,
                "approver": current_step.approver_name if current_step else None,
                "status": current_step.status.value if current_step else None,
            } if current_step else None,
            "sla": sla_status,
            "final_decision": workflow.final_decision,
            "timing": {
                "created_at": workflow.created_at.isoformat(),
                "submitted_at": workflow.submitted_at.isoformat() if workflow.submitted_at else None,
                "completed_at": workflow.completed_at.isoformat() if workflow.completed_at else None,
                "elapsed_hours": round(workflow.get_elapsed_hours(), 2),
            },
        }
