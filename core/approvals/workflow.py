# Approval Workflow Manager
# Multi-stage approval orchestration

"""
Approval Workflow Manager for GOVERNEX+.

Manages the complete approval lifecycle:
- Multi-stage routing
- Parallel and sequential approvals
- Escalation handling
- SLA management
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from enum import Enum
import logging

from .models import (
    ApprovalRequest, ApprovalRoute, ApprovalDecision,
    Approver, ApprovalStatus, ApproverType, ApprovalPriority
)

logger = logging.getLogger(__name__)


class WorkflowStatus(Enum):
    """Status of a workflow instance."""
    CREATED = "CREATED"
    ACTIVE = "ACTIVE"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    ESCALATED = "ESCALATED"
    COMPLETED = "COMPLETED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"


class StageType(Enum):
    """Type of workflow stage."""
    PARALLEL = "PARALLEL"  # All approvers must approve
    ANY = "ANY"  # Any one approver can approve
    SEQUENTIAL = "SEQUENTIAL"  # Approvers in order


@dataclass
class WorkflowStage:
    """
    A stage in the approval workflow.

    Contains approvers and completion logic.
    """
    stage_id: str
    stage_number: int
    name: str

    # Approvers
    approvers: List[Approver] = field(default_factory=list)

    # Type
    stage_type: StageType = StageType.PARALLEL

    # Status
    status: WorkflowStatus = WorkflowStatus.CREATED
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Decisions
    decisions: List[ApprovalDecision] = field(default_factory=list)

    # SLA
    sla_hours: float = 24.0
    due_at: Optional[datetime] = None

    # Requirements
    required_approvals: int = 0  # 0 = all, N = specific count

    def start(self) -> None:
        """Start the stage."""
        self.status = WorkflowStatus.PENDING_APPROVAL
        self.started_at = datetime.now()
        if self.sla_hours > 0:
            self.due_at = self.started_at + timedelta(hours=self.sla_hours)

    def add_decision(self, decision: ApprovalDecision) -> None:
        """Add a decision to the stage."""
        self.decisions.append(decision)
        self._check_completion()

    def _check_completion(self) -> None:
        """Check if stage is complete."""
        if self.stage_type == StageType.ANY:
            # Any approval completes the stage
            approved = [d for d in self.decisions if d.status == ApprovalStatus.APPROVED]
            rejected = [d for d in self.decisions if d.status == ApprovalStatus.REJECTED]

            if approved:
                self.status = WorkflowStatus.COMPLETED
                self.completed_at = datetime.now()
            elif rejected:
                self.status = WorkflowStatus.REJECTED
                self.completed_at = datetime.now()

        elif self.stage_type == StageType.PARALLEL:
            # All must approve
            total = len(self.approvers)
            approved = len([d for d in self.decisions if d.status == ApprovalStatus.APPROVED])
            rejected = [d for d in self.decisions if d.status == ApprovalStatus.REJECTED]

            if rejected:
                self.status = WorkflowStatus.REJECTED
                self.completed_at = datetime.now()
            elif approved >= total:
                self.status = WorkflowStatus.COMPLETED
                self.completed_at = datetime.now()

    def is_complete(self) -> bool:
        """Check if stage is complete."""
        return self.status in [WorkflowStatus.COMPLETED, WorkflowStatus.REJECTED]

    def is_approved(self) -> bool:
        """Check if stage was approved."""
        return self.status == WorkflowStatus.COMPLETED

    def is_overdue(self) -> bool:
        """Check if stage is overdue."""
        if not self.due_at:
            return False
        return datetime.now() > self.due_at and not self.is_complete()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "stage_id": self.stage_id,
            "stage_number": self.stage_number,
            "name": self.name,
            "stage_type": self.stage_type.value,
            "status": self.status.value,
            "approver_count": len(self.approvers),
            "decision_count": len(self.decisions),
            "sla_hours": self.sla_hours,
            "due_at": self.due_at.isoformat() if self.due_at else None,
            "is_overdue": self.is_overdue(),
        }


@dataclass
class ApprovalWorkflow:
    """
    Complete approval workflow instance.

    Orchestrates multi-stage approvals.
    """
    workflow_id: str
    request_id: str
    created_at: datetime = field(default_factory=datetime.now)

    # Stages
    stages: List[WorkflowStage] = field(default_factory=list)
    current_stage: int = 0

    # Status
    status: WorkflowStatus = WorkflowStatus.CREATED
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Final outcome
    final_status: Optional[ApprovalStatus] = None

    # Tracking
    audit_log: List[Dict[str, Any]] = field(default_factory=list)

    def start(self) -> None:
        """Start the workflow."""
        self.status = WorkflowStatus.ACTIVE
        self.started_at = datetime.now()

        if self.stages:
            self.stages[0].start()
            self.status = WorkflowStatus.PENDING_APPROVAL

        self._log("WORKFLOW_STARTED", {"stage": 0})

    def get_current_stage(self) -> Optional[WorkflowStage]:
        """Get the current stage."""
        if 0 <= self.current_stage < len(self.stages):
            return self.stages[self.current_stage]
        return None

    def get_pending_approvers(self) -> List[Approver]:
        """Get approvers who haven't decided yet."""
        stage = self.get_current_stage()
        if not stage:
            return []

        decided_ids = {d.approver_id for d in stage.decisions}
        return [a for a in stage.approvers if a.approver_id not in decided_ids]

    def record_decision(
        self,
        approver_id: str,
        status: ApprovalStatus,
        comments: str = "",
        conditions: Optional[List[str]] = None
    ) -> bool:
        """
        Record an approver's decision.

        Returns True if decision was recorded.
        """
        stage = self.get_current_stage()
        if not stage:
            return False

        # Find the approver
        approver = next(
            (a for a in stage.approvers if a.approver_id == approver_id),
            None
        )
        if not approver:
            return False

        # Create decision
        decision = ApprovalDecision(
            decision_id=f"DEC-{self.workflow_id}-{len(stage.decisions)+1}",
            request_id=self.request_id,
            approver_id=approver_id,
            approver_type=approver.approver_type,
            status=status,
            decision_time=datetime.now(),
            comments=comments,
            conditions=conditions or [],
        )

        # Calculate SLA compliance
        if stage.started_at:
            elapsed = (datetime.now() - stage.started_at).total_seconds() / 3600
            decision.response_time_hours = elapsed
            decision.within_sla = elapsed <= stage.sla_hours

        stage.add_decision(decision)

        self._log("DECISION_RECORDED", {
            "stage": self.current_stage,
            "approver_id": approver_id,
            "status": status.value,
        })

        # Check if stage complete
        if stage.is_complete():
            self._handle_stage_completion(stage)

        return True

    def _handle_stage_completion(self, stage: WorkflowStage) -> None:
        """Handle stage completion."""
        if stage.status == WorkflowStatus.REJECTED:
            self.status = WorkflowStatus.REJECTED
            self.final_status = ApprovalStatus.REJECTED
            self.completed_at = datetime.now()
            self._log("WORKFLOW_REJECTED", {"stage": self.current_stage})

        elif stage.status == WorkflowStatus.COMPLETED:
            # Move to next stage
            if self.current_stage < len(self.stages) - 1:
                self.current_stage += 1
                self.stages[self.current_stage].start()
                self._log("STAGE_ADVANCED", {"stage": self.current_stage})
            else:
                # All stages complete
                self.status = WorkflowStatus.COMPLETED
                self.final_status = ApprovalStatus.APPROVED
                self.completed_at = datetime.now()
                self._log("WORKFLOW_COMPLETED", {})

    def escalate(self, reason: str) -> None:
        """Escalate the workflow."""
        self.status = WorkflowStatus.ESCALATED
        self._log("WORKFLOW_ESCALATED", {"reason": reason})

    def cancel(self, reason: str) -> None:
        """Cancel the workflow."""
        self.status = WorkflowStatus.CANCELLED
        self.final_status = ApprovalStatus.CANCELLED
        self.completed_at = datetime.now()
        self._log("WORKFLOW_CANCELLED", {"reason": reason})

    def check_expiry(self) -> bool:
        """Check if workflow has expired."""
        stage = self.get_current_stage()
        if stage and stage.is_overdue():
            self.status = WorkflowStatus.EXPIRED
            self.final_status = ApprovalStatus.EXPIRED
            self.completed_at = datetime.now()
            self._log("WORKFLOW_EXPIRED", {"stage": self.current_stage})
            return True
        return False

    def _log(self, event: str, details: Dict[str, Any]) -> None:
        """Add to audit log."""
        self.audit_log.append({
            "timestamp": datetime.now().isoformat(),
            "event": event,
            "details": details,
        })

    def get_progress(self) -> Dict[str, Any]:
        """Get workflow progress summary."""
        total_stages = len(self.stages)
        completed_stages = sum(1 for s in self.stages if s.is_complete())

        total_decisions = sum(len(s.decisions) for s in self.stages)
        total_approvers = sum(len(s.approvers) for s in self.stages)

        return {
            "status": self.status.value,
            "current_stage": self.current_stage,
            "total_stages": total_stages,
            "completed_stages": completed_stages,
            "progress_percent": (completed_stages / total_stages * 100) if total_stages else 0,
            "total_decisions": total_decisions,
            "total_approvers": total_approvers,
            "pending_approvers": len(self.get_pending_approvers()),
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "workflow_id": self.workflow_id,
            "request_id": self.request_id,
            "status": self.status.value,
            "current_stage": self.current_stage,
            "stages": [s.to_dict() for s in self.stages],
            "progress": self.get_progress(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "final_status": self.final_status.value if self.final_status else None,
        }


class WorkflowManager:
    """
    Manages approval workflows.

    Responsibilities:
    - Create workflows from routes
    - Track active workflows
    - Handle SLA monitoring
    - Manage escalations
    """

    def __init__(self):
        """Initialize manager."""
        self._workflows: Dict[str, ApprovalWorkflow] = {}
        self._workflow_counter = 0

        # Callbacks
        self._on_approval: Optional[Callable] = None
        self._on_rejection: Optional[Callable] = None
        self._on_escalation: Optional[Callable] = None

    def create_workflow(
        self,
        request: ApprovalRequest,
        route: ApprovalRoute
    ) -> ApprovalWorkflow:
        """
        Create a workflow from an approval route.

        Args:
            request: The approval request
            route: The determined approval route

        Returns:
            Created workflow
        """
        self._workflow_counter += 1
        workflow_id = f"WF-{datetime.now().strftime('%Y%m%d%H%M%S')}-{self._workflow_counter}"

        workflow = ApprovalWorkflow(
            workflow_id=workflow_id,
            request_id=request.request_id,
        )

        # Create stages from route
        for i, stage_approvers in enumerate(route.stages):
            stage = WorkflowStage(
                stage_id=f"{workflow_id}-S{i+1}",
                stage_number=i + 1,
                name=f"Stage {i + 1}",
                approvers=stage_approvers,
                stage_type=StageType.PARALLEL,  # Default to parallel
                sla_hours=route.total_sla_hours / len(route.stages) if route.stages else 24,
            )
            workflow.stages.append(stage)

        self._workflows[workflow_id] = workflow

        # Handle auto-approval
        if route.is_auto_approved:
            workflow.status = WorkflowStatus.COMPLETED
            workflow.final_status = ApprovalStatus.AUTO_APPROVED
            workflow.completed_at = datetime.now()
            workflow._log("AUTO_APPROVED", {"reason": route.auto_approval_reason})
        else:
            # Start the workflow
            workflow.start()

        return workflow

    def get_workflow(self, workflow_id: str) -> Optional[ApprovalWorkflow]:
        """Get a workflow by ID."""
        return self._workflows.get(workflow_id)

    def get_workflow_by_request(self, request_id: str) -> Optional[ApprovalWorkflow]:
        """Get workflow for a request."""
        for workflow in self._workflows.values():
            if workflow.request_id == request_id:
                return workflow
        return None

    def record_decision(
        self,
        workflow_id: str,
        approver_id: str,
        status: ApprovalStatus,
        comments: str = ""
    ) -> bool:
        """Record a decision on a workflow."""
        workflow = self.get_workflow(workflow_id)
        if not workflow:
            return False

        result = workflow.record_decision(approver_id, status, comments)

        # Trigger callbacks
        if workflow.final_status == ApprovalStatus.APPROVED and self._on_approval:
            self._on_approval(workflow)
        elif workflow.final_status == ApprovalStatus.REJECTED and self._on_rejection:
            self._on_rejection(workflow)

        return result

    def check_sla_breaches(self) -> List[ApprovalWorkflow]:
        """Check for SLA breaches across all workflows."""
        breached = []

        for workflow in self._workflows.values():
            if workflow.status == WorkflowStatus.PENDING_APPROVAL:
                if workflow.check_expiry():
                    breached.append(workflow)

        return breached

    def escalate_overdue(self) -> List[ApprovalWorkflow]:
        """Escalate overdue workflows."""
        escalated = []

        for workflow in self._workflows.values():
            if workflow.status == WorkflowStatus.PENDING_APPROVAL:
                stage = workflow.get_current_stage()
                if stage and stage.is_overdue():
                    workflow.escalate("SLA breach")
                    escalated.append(workflow)
                    if self._on_escalation:
                        self._on_escalation(workflow)

        return escalated

    def get_active_workflows(self) -> List[ApprovalWorkflow]:
        """Get all active workflows."""
        return [
            w for w in self._workflows.values()
            if w.status in [WorkflowStatus.ACTIVE, WorkflowStatus.PENDING_APPROVAL]
        ]

    def get_pending_by_approver(self, approver_id: str) -> List[ApprovalWorkflow]:
        """Get workflows pending for a specific approver."""
        pending = []

        for workflow in self.get_active_workflows():
            approvers = workflow.get_pending_approvers()
            if any(a.approver_id == approver_id for a in approvers):
                pending.append(workflow)

        return pending

    def get_statistics(self) -> Dict[str, Any]:
        """Get workflow statistics."""
        workflows = list(self._workflows.values())

        return {
            "total": len(workflows),
            "active": sum(1 for w in workflows if w.status == WorkflowStatus.ACTIVE),
            "pending": sum(1 for w in workflows if w.status == WorkflowStatus.PENDING_APPROVAL),
            "completed": sum(1 for w in workflows if w.status == WorkflowStatus.COMPLETED),
            "rejected": sum(1 for w in workflows if w.status == WorkflowStatus.REJECTED),
            "escalated": sum(1 for w in workflows if w.status == WorkflowStatus.ESCALATED),
            "expired": sum(1 for w in workflows if w.status == WorkflowStatus.EXPIRED),
        }

    def on_approval(self, callback: Callable) -> None:
        """Register approval callback."""
        self._on_approval = callback

    def on_rejection(self, callback: Callable) -> None:
        """Register rejection callback."""
        self._on_rejection = callback

    def on_escalation(self, callback: Callable) -> None:
        """Register escalation callback."""
        self._on_escalation = callback
