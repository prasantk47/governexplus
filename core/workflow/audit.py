# Workflow Audit and Explainability
# Complete audit trail and decision explanation

"""
Audit Engine for GOVERNEX+ Workflow.

Provides:
- Complete decision path tracking
- Human-readable explanations
- Audit-ready reports
- Compliance evidence

Key Principle:
Every decision must be explainable and auditable.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum
import logging

from .models import (
    Workflow, WorkflowStep, WorkflowContext, WorkflowStatus, StepStatus,
    ProcessType, ApproverTypeEnum
)
from .policy import PolicyRule, RuleMatch
from .executor import ExecutionEvent, EventType

logger = logging.getLogger(__name__)


class AuditEventType(Enum):
    """Types of audit events."""
    WORKFLOW_CREATED = "WORKFLOW_CREATED"
    WORKFLOW_ASSEMBLED = "WORKFLOW_ASSEMBLED"
    WORKFLOW_SUBMITTED = "WORKFLOW_SUBMITTED"
    STEP_ACTIVATED = "STEP_ACTIVATED"
    DECISION_MADE = "DECISION_MADE"
    DELEGATION_OCCURRED = "DELEGATION_OCCURRED"
    ESCALATION_OCCURRED = "ESCALATION_OCCURRED"
    SLA_WARNING = "SLA_WARNING"
    SLA_BREACH = "SLA_BREACH"
    WORKFLOW_COMPLETED = "WORKFLOW_COMPLETED"
    PROVISIONING_COMPLETED = "PROVISIONING_COMPLETED"
    POLICY_EVALUATED = "POLICY_EVALUATED"
    RULE_MATCHED = "RULE_MATCHED"


@dataclass
class AuditEvent:
    """A single audit event."""
    event_id: str = ""
    event_type: AuditEventType = AuditEventType.WORKFLOW_CREATED
    workflow_id: str = ""
    step_id: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)

    # Actor
    actor: str = ""
    actor_type: str = ""  # USER, SYSTEM, POLICY

    # Details
    description: str = ""
    details: Dict[str, Any] = field(default_factory=dict)

    # Evidence
    evidence: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "workflow_id": self.workflow_id,
            "step_id": self.step_id,
            "timestamp": self.timestamp.isoformat(),
            "actor": self.actor,
            "actor_type": self.actor_type,
            "description": self.description,
            "details": self.details,
            "evidence": self.evidence,
        }


@dataclass
class DecisionPath:
    """Complete decision path for a workflow."""
    workflow_id: str
    steps: List[Dict[str, Any]] = field(default_factory=list)

    def add_step(
        self,
        step_number: int,
        description: str,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """Add a step to the decision path."""
        self.steps.append({
            "step_number": step_number,
            "timestamp": datetime.now().isoformat(),
            "description": description,
            "details": details or {},
        })

    def to_dict(self) -> Dict[str, Any]:
        return {
            "workflow_id": self.workflow_id,
            "steps": self.steps,
        }

    def to_narrative(self) -> str:
        """Convert to human-readable narrative."""
        lines = []
        for step in self.steps:
            lines.append(f"{step['step_number']}. {step['description']}")
            if step.get('details'):
                for key, value in step['details'].items():
                    lines.append(f"   - {key}: {value}")
        return "\n".join(lines)


@dataclass
class AuditTrail:
    """Complete audit trail for a workflow."""
    workflow_id: str
    events: List[AuditEvent] = field(default_factory=list)
    decision_path: Optional[DecisionPath] = None

    # Summary
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    total_duration_hours: float = 0.0

    def add_event(self, event: AuditEvent) -> None:
        """Add an event to the trail."""
        self.events.append(event)
        if not self.start_time:
            self.start_time = event.timestamp

    def finalize(self) -> None:
        """Finalize the audit trail."""
        if self.events:
            self.end_time = self.events[-1].timestamp
            if self.start_time:
                self.total_duration_hours = (
                    (self.end_time - self.start_time).total_seconds() / 3600
                )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "workflow_id": self.workflow_id,
            "events": [e.to_dict() for e in self.events],
            "decision_path": self.decision_path.to_dict() if self.decision_path else None,
            "summary": {
                "start_time": self.start_time.isoformat() if self.start_time else None,
                "end_time": self.end_time.isoformat() if self.end_time else None,
                "total_duration_hours": round(self.total_duration_hours, 2),
                "total_events": len(self.events),
            },
        }


class WorkflowAuditEngine:
    """
    Manages audit trails and explainability.

    Provides:
    - Event tracking
    - Decision path documentation
    - Audit report generation
    - Compliance evidence
    """

    def __init__(self):
        """Initialize audit engine."""
        self._trails: Dict[str, AuditTrail] = {}
        self._event_counter = 0

    def create_trail(self, workflow_id: str) -> AuditTrail:
        """Create a new audit trail for a workflow."""
        trail = AuditTrail(
            workflow_id=workflow_id,
            decision_path=DecisionPath(workflow_id=workflow_id),
        )
        self._trails[workflow_id] = trail
        return trail

    def get_trail(self, workflow_id: str) -> Optional[AuditTrail]:
        """Get audit trail for a workflow."""
        return self._trails.get(workflow_id)

    def record_event(
        self,
        workflow_id: str,
        event_type: AuditEventType,
        description: str,
        actor: str = "",
        actor_type: str = "SYSTEM",
        step_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        evidence: Optional[Dict[str, Any]] = None
    ) -> AuditEvent:
        """Record an audit event."""
        self._event_counter += 1

        event = AuditEvent(
            event_id=f"AUD-{datetime.now().strftime('%Y%m%d%H%M%S')}-{self._event_counter:04d}",
            event_type=event_type,
            workflow_id=workflow_id,
            step_id=step_id,
            actor=actor,
            actor_type=actor_type,
            description=description,
            details=details or {},
            evidence=evidence or {},
        )

        # Add to trail
        trail = self._trails.get(workflow_id)
        if not trail:
            trail = self.create_trail(workflow_id)
        trail.add_event(event)

        return event

    def record_assembly(
        self,
        workflow: Workflow,
        matched_rules: List[RuleMatch],
        context: WorkflowContext
    ) -> None:
        """Record workflow assembly for audit."""
        trail = self.get_trail(workflow.workflow_id)
        if not trail:
            trail = self.create_trail(workflow.workflow_id)

        # Record policy evaluation
        self.record_event(
            workflow.workflow_id,
            AuditEventType.POLICY_EVALUATED,
            f"Policy evaluated for request {context.request_id}",
            actor="POLICY_ENGINE",
            actor_type="SYSTEM",
            details={
                "policy_id": workflow.assembled_by_policy,
                "rules_evaluated": len(matched_rules),
                "rules_matched": len([r for r in matched_rules if r.matched]),
            },
            evidence={
                "context": context.to_dict(),
            },
        )

        # Record each matched rule
        for rule_match in matched_rules:
            if rule_match.matched:
                self.record_event(
                    workflow.workflow_id,
                    AuditEventType.RULE_MATCHED,
                    f"Rule '{rule_match.rule.name}' matched",
                    actor="POLICY_ENGINE",
                    actor_type="SYSTEM",
                    details={
                        "rule_id": rule_match.rule.rule_id,
                        "rule_name": rule_match.rule.name,
                        "layer": rule_match.rule.layer,
                        "conditions_matched": rule_match.matched_conditions,
                        "actions": [a.action_type.value for a in rule_match.actions_to_execute],
                    },
                )

                # Add to decision path
                if trail.decision_path:
                    trail.decision_path.add_step(
                        len(trail.decision_path.steps) + 1,
                        f"Rule matched: {rule_match.rule.name}",
                        {
                            "conditions": rule_match.matched_conditions,
                            "result": [a.action_type.value for a in rule_match.actions_to_execute],
                        },
                    )

        # Record assembly complete
        self.record_event(
            workflow.workflow_id,
            AuditEventType.WORKFLOW_ASSEMBLED,
            f"Workflow assembled with {len(workflow.steps)} steps",
            actor="ASSEMBLER",
            actor_type="SYSTEM",
            details={
                "steps_created": len(workflow.steps),
                "approver_types": [s.approver_type.value for s in workflow.steps],
                "total_sla_hours": workflow.get_total_sla_hours(),
            },
        )

    def record_decision(
        self,
        workflow: Workflow,
        step: WorkflowStep,
        decision: str,
        decided_by: str,
        comments: str = ""
    ) -> None:
        """Record an approval decision."""
        self.record_event(
            workflow.workflow_id,
            AuditEventType.DECISION_MADE,
            f"{decided_by} {decision.lower()} step '{step.name}'",
            actor=decided_by,
            actor_type="USER",
            step_id=step.step_id,
            details={
                "decision": decision,
                "comments": comments,
                "approver_type": step.approver_type.value,
                "response_time_hours": self._calculate_response_time(step),
                "within_sla": not step.is_overdue(),
            },
            evidence={
                "step_details": step.to_dict(),
            },
        )

        # Add to decision path
        trail = self.get_trail(workflow.workflow_id)
        if trail and trail.decision_path:
            trail.decision_path.add_step(
                len(trail.decision_path.steps) + 1,
                f"{step.approver_type.value}: {decision}",
                {
                    "approver": decided_by,
                    "comments": comments,
                },
            )

    def _calculate_response_time(self, step: WorkflowStep) -> float:
        """Calculate response time for a step."""
        if step.activated_at and step.decided_at:
            return (step.decided_at - step.activated_at).total_seconds() / 3600
        return 0.0

    def generate_audit_report(
        self,
        workflow: Workflow,
        include_evidence: bool = True
    ) -> str:
        """
        Generate comprehensive audit report.

        Suitable for compliance and audit documentation.
        """
        trail = self.get_trail(workflow.workflow_id)
        if trail:
            trail.finalize()

        lines = []

        lines.append("=" * 70)
        lines.append("WORKFLOW AUDIT REPORT")
        lines.append("=" * 70)
        lines.append("")

        # Header
        lines.append("WORKFLOW DETAILS")
        lines.append("-" * 40)
        lines.append(f"Workflow ID: {workflow.workflow_id}")
        lines.append(f"Process Type: {workflow.process_type.value}")
        lines.append(f"Status: {workflow.status.value}")
        lines.append(f"Final Decision: {workflow.final_decision or 'Pending'}")
        lines.append("")

        # Context
        if workflow.context:
            lines.append("REQUEST CONTEXT")
            lines.append("-" * 40)
            lines.append(f"Request ID: {workflow.context.request_id}")
            lines.append(f"System: {workflow.context.system_name or workflow.context.system_id}")
            lines.append(f"Requester: {workflow.context.requester_name} ({workflow.context.requester_id})")
            lines.append(f"Target User: {workflow.context.target_user_name} ({workflow.context.target_user_id})")
            lines.append(f"Risk Score: {workflow.context.risk_score}/100 ({workflow.context.risk_level})")
            if workflow.context.sod_conflicts:
                lines.append(f"SoD Conflicts: {len(workflow.context.sod_conflicts)}")
            lines.append("")

        # Assembly
        lines.append("WORKFLOW ASSEMBLY")
        lines.append("-" * 40)
        lines.append(f"Policy Used: {workflow.assembled_by_policy}")
        lines.append(f"Rules Matched: {len(workflow.assembly_rules_matched)}")
        for rule_id in workflow.assembly_rules_matched:
            lines.append(f"  - {rule_id}")
        lines.append(f"Explanation: {workflow.assembly_explanation}")
        lines.append("")

        # Steps
        lines.append("APPROVAL STEPS")
        lines.append("-" * 40)
        for step in workflow.steps:
            lines.append(f"Step {step.step_number}: {step.name}")
            lines.append(f"  Approver: {step.approver_name} ({step.approver_type.value})")
            lines.append(f"  Status: {step.status.value}")
            if step.decision:
                lines.append(f"  Decision: {step.decision}")
                lines.append(f"  Decided By: {step.decided_by}")
                lines.append(f"  Decided At: {step.decided_at.isoformat() if step.decided_at else 'N/A'}")
                if step.decision_comments:
                    lines.append(f"  Comments: {step.decision_comments}")
            lines.append(f"  SLA: {step.sla_hours} hours")
            lines.append(f"  Reason: {step.reason}")
            lines.append("")

        # Decision Path
        if trail and trail.decision_path:
            lines.append("DECISION PATH")
            lines.append("-" * 40)
            lines.append(trail.decision_path.to_narrative())
            lines.append("")

        # Timeline
        lines.append("TIMELINE")
        lines.append("-" * 40)
        lines.append(f"Created: {workflow.created_at.isoformat()}")
        lines.append(f"Submitted: {workflow.submitted_at.isoformat() if workflow.submitted_at else 'N/A'}")
        lines.append(f"Completed: {workflow.completed_at.isoformat() if workflow.completed_at else 'N/A'}")
        if trail:
            lines.append(f"Duration: {trail.total_duration_hours:.2f} hours")
        lines.append("")

        # Events
        if trail and include_evidence:
            lines.append("AUDIT EVENTS")
            lines.append("-" * 40)
            for event in trail.events:
                lines.append(f"[{event.timestamp.isoformat()}] {event.event_type.value}")
                lines.append(f"  Actor: {event.actor} ({event.actor_type})")
                lines.append(f"  Description: {event.description}")
                if event.details:
                    for key, value in event.details.items():
                        lines.append(f"  {key}: {value}")
                lines.append("")

        lines.append("=" * 70)
        lines.append(f"Report Generated: {datetime.now().isoformat()}")
        lines.append("=" * 70)

        return "\n".join(lines)

    def generate_compliance_evidence(self, workflow: Workflow) -> Dict[str, Any]:
        """
        Generate compliance evidence package.

        Contains all information needed for audit.
        """
        trail = self.get_trail(workflow.workflow_id)
        if trail:
            trail.finalize()

        return {
            "workflow": workflow.to_dict(),
            "audit_trail": trail.to_dict() if trail else None,
            "compliance_assertions": {
                "all_approvals_recorded": all(
                    s.decided_by is not None for s in workflow.steps if s.decision
                ),
                "sla_compliance": all(
                    not s.is_overdue() for s in workflow.steps if s.is_complete()
                ),
                "policy_based_routing": workflow.assembled_by_policy is not None,
                "complete_audit_trail": trail is not None and len(trail.events) > 0,
            },
            "generated_at": datetime.now().isoformat(),
        }

    def explain_for_requester(self, workflow: Workflow) -> str:
        """
        Generate requester-friendly explanation.

        Simple language, no technical jargon.
        """
        lines = []

        lines.append("Your Request Status")
        lines.append("=" * 40)
        lines.append("")

        status_map = {
            WorkflowStatus.PENDING: "Your request is being processed.",
            WorkflowStatus.IN_PROGRESS: "Your request is being reviewed.",
            WorkflowStatus.WAITING_APPROVAL: "Your request is waiting for approval.",
            WorkflowStatus.APPROVED: "Your request has been approved!",
            WorkflowStatus.REJECTED: "Your request has been rejected.",
            WorkflowStatus.AUTO_APPROVED: "Your request was automatically approved.",
            WorkflowStatus.COMPLETED: "Your request has been completed.",
        }

        lines.append(status_map.get(workflow.status, "Processing..."))
        lines.append("")

        # Approvers
        if workflow.steps:
            lines.append("Who Needs to Approve")
            lines.append("-" * 40)
            for step in workflow.steps:
                icon = "✓" if step.status == StepStatus.APPROVED else "○"
                if step.status == StepStatus.REJECTED:
                    icon = "✗"
                elif step.status == StepStatus.ACTIVE:
                    icon = "→"
                lines.append(f"  {icon} {step.approver_name}")
            lines.append("")

        # Current status
        current = workflow.get_current_step()
        if current and current.status == StepStatus.ACTIVE:
            lines.append(f"Currently waiting for: {current.approver_name}")
            lines.append("")

        # Why these approvers
        lines.append("Why These Approvers?")
        lines.append("-" * 40)
        lines.append(workflow.assembly_explanation)
        lines.append("")

        return "\n".join(lines)

    def explain_for_approver(self, workflow: Workflow, step: WorkflowStep) -> str:
        """
        Generate approver-friendly explanation.

        Focus on what they need to evaluate.
        """
        lines = []

        lines.append("Approval Required")
        lines.append("=" * 40)
        lines.append("")

        lines.append(f"You are being asked to review this request because:")
        lines.append(f"  {step.reason}")
        lines.append("")

        if workflow.context:
            lines.append("Request Details")
            lines.append("-" * 40)
            lines.append(f"Requester: {workflow.context.requester_name}")
            lines.append(f"Target User: {workflow.context.target_user_name}")
            lines.append(f"System: {workflow.context.system_name or workflow.context.system_id}")
            if workflow.context.role_name:
                lines.append(f"Role: {workflow.context.role_name}")
            lines.append("")

            lines.append("Risk Assessment")
            lines.append("-" * 40)
            lines.append(f"Risk Score: {workflow.context.risk_score}/100")
            lines.append(f"Risk Level: {workflow.context.risk_level}")
            if workflow.context.sod_conflicts:
                lines.append(f"SoD Conflicts: {len(workflow.context.sod_conflicts)}")
                for conflict in workflow.context.sod_conflicts[:3]:
                    lines.append(f"  - {conflict}")
            lines.append("")

        lines.append("SLA Information")
        lines.append("-" * 40)
        lines.append(f"Response needed within: {step.sla_hours} hours")
        if step.due_at:
            lines.append(f"Due by: {step.due_at.isoformat()}")
        lines.append("")

        return "\n".join(lines)
