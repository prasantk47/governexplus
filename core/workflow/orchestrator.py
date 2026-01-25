# Workflow Orchestrator
# Ties together all workflow components

"""
Unified Workflow Orchestrator for GOVERNEX+.

This orchestrator brings together:
- Policy Engine (dynamic workflow assembly)
- Approver Resolver (pluggable resolution)
- Workflow Executor (state machine)
- Provisioning Engine (item-level partial provisioning)
- Event-Driven Re-Evaluation (continuous adaptation)
- SLA Manager (tracking and escalation)
- Audit Engine (complete audit trail)

ONE ORCHESTRATOR TO RULE THEM ALL:
Instead of separate flows for each process type (like SAP GRC),
GOVERNEX+ uses ONE unified orchestrator that adapts to ANY process.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
import logging

from .models import (
    WorkflowContext, Workflow, WorkflowStep, WorkflowStatus, StepStatus,
    ProcessType, ApproverTypeEnum, WorkflowDecision
)
from .policy import PolicyEngine, PolicySet
from .assembler import WorkflowAssembler, AssemblyResult
from .resolver import ResolverRegistry, ResolutionResult
from .executor import WorkflowExecutor, ExecutionResult
from .sla import SLAManager, SLAConfig, SLACheck
from .audit import WorkflowAuditEngine
from .provisioning import (
    ProvisioningEngine, ProvisioningPolicy, AccessRequest, AccessItem,
    ProvisioningResult, ItemStatus
)
from .events import (
    ReEvaluationEngine, WorkflowEvent, EventType, EventPriority, EventSource,
    ReEvaluationAction, ReEvaluationResult
)

logger = logging.getLogger(__name__)


# ============================================================
# ORCHESTRATION CONTEXT
# ============================================================

@dataclass
class OrchestrationContext:
    """Complete context for workflow orchestration."""

    # Request info
    request_id: str = ""
    process_type: ProcessType = ProcessType.ACCESS_REQUEST

    # Workflow context
    workflow_context: Optional[WorkflowContext] = None

    # Access request (for provisioning)
    access_request: Optional[AccessRequest] = None

    # Assembled workflow
    workflow: Optional[Workflow] = None
    assembly_result: Optional[AssemblyResult] = None

    # Current state
    current_step: Optional[WorkflowStep] = None
    pending_approvals: List[str] = field(default_factory=list)

    # Events
    pending_events: List[WorkflowEvent] = field(default_factory=list)

    # Audit
    audit_entries: List[Dict[str, Any]] = field(default_factory=list)

    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)


@dataclass
class OrchestrationResult:
    """Result of an orchestration operation."""
    success: bool = True
    operation: str = ""

    # Results from sub-components
    assembly_result: Optional[AssemblyResult] = None
    execution_result: Optional[ExecutionResult] = None
    provisioning_result: Optional[ProvisioningResult] = None
    reevaluation_results: List[ReEvaluationResult] = field(default_factory=list)
    sla_checks: List[SLACheck] = field(default_factory=list)

    # Messages
    message: str = ""
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    # Actions taken
    actions: List[str] = field(default_factory=list)

    # Audit trail
    audit_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "operation": self.operation,
            "message": self.message,
            "warnings": self.warnings,
            "errors": self.errors,
            "actions": self.actions,
            "assembly": self.assembly_result.to_dict() if self.assembly_result else None,
            "execution": self.execution_result.to_dict() if self.execution_result else None,
            "provisioning": self.provisioning_result.to_dict() if self.provisioning_result else None,
            "reevaluation": [r.to_dict() for r in self.reevaluation_results],
            "sla_checks": [s.to_dict() for s in self.sla_checks],
        }


# ============================================================
# UNIFIED ORCHESTRATOR
# ============================================================

class WorkflowOrchestrator:
    """
    Unified workflow orchestrator for GOVERNEX+.

    This is the main entry point for all workflow operations.
    It coordinates all sub-components to provide a seamless experience.
    """

    def __init__(
        self,
        policy_engine: Optional[PolicyEngine] = None,
        resolver_registry: Optional[ResolverRegistry] = None,
        provisioning_policy: Optional[ProvisioningPolicy] = None,
        sla_config: Optional[SLAConfig] = None,
    ):
        """
        Initialize orchestrator with optional custom components.

        Default components are created if not provided.
        """
        # Core components
        self.policy_engine = policy_engine or PolicyEngine()
        self.assembler = WorkflowAssembler(self.policy_engine)
        self.resolver = resolver_registry or ResolverRegistry()
        self.executor = WorkflowExecutor()
        self.sla_manager = SLAManager(sla_config)
        self.audit_engine = WorkflowAuditEngine()

        # Provisioning
        self.provisioning_policy = provisioning_policy or ProvisioningPolicy()
        self.provisioning_engine = ProvisioningEngine(self.provisioning_policy)

        # Event-driven re-evaluation
        self.reevaluation_engine = ReEvaluationEngine()
        self._setup_reevaluation_actions()

        # Active contexts (in-memory for now, should be persisted)
        self._contexts: Dict[str, OrchestrationContext] = {}

        # Callbacks
        self._on_workflow_complete: Optional[Callable] = None
        self._on_item_provisioned: Optional[Callable] = None
        self._on_sla_breach: Optional[Callable] = None

    def _setup_reevaluation_actions(self) -> None:
        """Configure re-evaluation action executors."""

        def hold_workflow(result: ReEvaluationResult, ctx: Dict[str, Any]):
            workflow_id = ctx.get("workflow_id")
            if workflow_id and workflow_id in self._contexts:
                context = self._contexts[workflow_id]
                if context.workflow:
                    context.workflow.status = WorkflowStatus.ON_HOLD
                    logger.info(f"Workflow {workflow_id} held due to event {result.event_id}")

        def add_approval_step(result: ReEvaluationResult, ctx: Dict[str, Any]):
            workflow_id = ctx.get("workflow_id")
            if workflow_id and workflow_id in self._contexts:
                context = self._contexts[workflow_id]
                if context.workflow:
                    # Add security review step
                    for detail in result.action_details:
                        if detail.get("step_type") == "SECURITY_REVIEW":
                            new_step = WorkflowStep(
                                step_id=f"SECURITY-{datetime.now().strftime('%H%M%S')}",
                                name="Security Review (Dynamic)",
                                approver_type=ApproverTypeEnum.ROLE,
                                approver_id="SECURITY_OFFICER",
                                is_mandatory=True,
                            )
                            context.workflow.steps.append(new_step)
                            logger.info(f"Added security review step to workflow {workflow_id}")

        def trigger_provisioning(result: ReEvaluationResult, ctx: Dict[str, Any]):
            request_id = ctx.get("request_id")
            if request_id and request_id in self._contexts:
                context = self._contexts[request_id]
                if context.access_request:
                    self.provisioning_engine.evaluate_request(context.access_request)

        self.reevaluation_engine.register_action_executor(
            ReEvaluationAction.HOLD_WORKFLOW, hold_workflow
        )
        self.reevaluation_engine.register_action_executor(
            ReEvaluationAction.ADD_APPROVAL_STEP, add_approval_step
        )
        self.reevaluation_engine.register_action_executor(
            ReEvaluationAction.TRIGGER_PROVISIONING_EVAL, trigger_provisioning
        )

    # ============================================================
    # WORKFLOW LIFECYCLE
    # ============================================================

    def submit_request(
        self,
        workflow_context: WorkflowContext,
        access_request: Optional[AccessRequest] = None,
        submitted_by: str = ""
    ) -> OrchestrationResult:
        """
        Submit a new request for workflow processing.

        This is the main entry point for new requests.

        Steps:
        1. Assemble workflow dynamically
        2. Resolve approvers
        3. Initialize workflow execution
        4. Start SLA tracking
        5. Create audit trail
        """
        result = OrchestrationResult(operation="SUBMIT_REQUEST")

        try:
            # Create orchestration context
            context = OrchestrationContext(
                request_id=workflow_context.request_id,
                process_type=workflow_context.process_type,
                workflow_context=workflow_context,
                access_request=access_request,
            )

            # Step 1: Assemble workflow
            assembly_result = self.assembler.assemble(workflow_context)
            result.assembly_result = assembly_result
            context.assembly_result = assembly_result

            if not assembly_result.workflow:
                result.success = False
                result.errors.append("Workflow assembly failed")
                return result

            context.workflow = assembly_result.workflow
            result.actions.append("WORKFLOW_ASSEMBLED")

            # Check for auto-decision
            if assembly_result.auto_decision:
                result.message = f"Request auto-{assembly_result.auto_decision}"
                result.actions.append(f"AUTO_{assembly_result.auto_decision}")

                # If auto-approved and we have access request, provision immediately
                if assembly_result.auto_decision == "APPROVED" and access_request:
                    for item in access_request.items:
                        item.mark_approved()
                    prov_result = self.provisioning_engine.evaluate_request(access_request)
                    result.provisioning_result = prov_result
                    result.actions.append("AUTO_PROVISIONED")

                return result

            # Step 2: Resolve approvers for each step
            for step in context.workflow.steps:
                resolution = self.resolver.resolve(step.approver_type, workflow_context)
                if resolution.resolved_approvers:
                    step.approver_id = resolution.resolved_approvers[0].approver_id
                    step.approver_name = resolution.resolved_approvers[0].approver_name

            result.actions.append("APPROVERS_RESOLVED")

            # Step 3: Submit workflow for execution
            exec_result = self.executor.submit(context.workflow, submitted_by)
            result.execution_result = exec_result
            result.actions.append("WORKFLOW_SUBMITTED")

            # Step 4: Start SLA tracking
            for step in context.workflow.steps:
                if step.status == StepStatus.PENDING:
                    self.sla_manager.start_tracking(context.workflow, step)

            result.actions.append("SLA_TRACKING_STARTED")

            # Step 5: Create audit trail
            self.audit_engine.log_submission(context.workflow, submitted_by)
            result.audit_id = context.workflow.workflow_id
            result.actions.append("AUDIT_CREATED")

            # Store context
            self._contexts[context.request_id] = context

            result.success = True
            result.message = f"Request {context.request_id} submitted successfully"

        except Exception as e:
            logger.error(f"Submit request failed: {e}")
            result.success = False
            result.errors.append(str(e))

        return result

    def record_decision(
        self,
        request_id: str,
        step_id: str,
        decision: str,  # APPROVED, REJECTED
        decided_by: str,
        comments: str = "",
        item_ids: Optional[List[str]] = None  # For item-level decisions
    ) -> OrchestrationResult:
        """
        Record an approval/rejection decision.

        This triggers:
        1. Workflow state update
        2. Provisioning evaluation (for partial provisioning)
        3. Event emission for re-evaluation
        4. SLA update
        5. Audit logging
        """
        result = OrchestrationResult(operation="RECORD_DECISION")

        context = self._contexts.get(request_id)
        if not context:
            result.success = False
            result.errors.append(f"Request {request_id} not found")
            return result

        try:
            # Step 1: Record decision in workflow executor
            if context.workflow:
                exec_result = self.executor.record_decision(
                    context.workflow, step_id, decision, decided_by, comments
                )
                result.execution_result = exec_result
                result.actions.append("DECISION_RECORDED")

            # Step 2: Record item-level decisions (for provisioning)
            if context.access_request and item_ids:
                for item_id in item_ids:
                    if decision == "APPROVED":
                        prov_result = self.provisioning_engine.record_approval(
                            context.access_request, item_id, decided_by, decided_by, comments
                        )
                    else:
                        prov_result = self.provisioning_engine.record_rejection(
                            context.access_request, item_id, decided_by, decided_by, comments
                        )
                    result.provisioning_result = prov_result

                result.actions.append("ITEM_DECISIONS_RECORDED")

                # Check for provisioned items
                provisioned = context.access_request.get_provisioned_items()
                if provisioned:
                    result.actions.append(f"PROVISIONED_{len(provisioned)}_ITEMS")
                    if self._on_item_provisioned:
                        for item in provisioned:
                            self._on_item_provisioned(item)

            # Step 3: Emit event for re-evaluation
            event = WorkflowEvent(
                event_type=EventType.APPROVAL_RECEIVED if decision == "APPROVED" else EventType.REJECTION_RECEIVED,
                priority=EventPriority.NORMAL,
                source=EventSource.USER_ACTION,
                request_id=request_id,
                workflow_id=context.workflow.workflow_id if context.workflow else None,
                step_id=step_id,
                payload={
                    "decision": decision,
                    "decided_by": decided_by,
                    "comments": comments,
                    "item_ids": item_ids,
                }
            )
            self.reevaluation_engine.emit_event(event)
            reeval_results = self.reevaluation_engine.process_pending_events({
                "request_id": request_id,
                "workflow_id": context.workflow.workflow_id if context.workflow else None,
            })
            result.reevaluation_results = reeval_results
            result.actions.append("REEVALUATION_TRIGGERED")

            # Step 4: Update SLA
            if context.workflow:
                step = next((s for s in context.workflow.steps if s.step_id == step_id), None)
                if step:
                    self.sla_manager.stop_tracking(step)
                    result.actions.append("SLA_STOPPED")

            # Step 5: Audit logging
            if context.workflow:
                step = next((s for s in context.workflow.steps if s.step_id == step_id), None)
                if step:
                    self.audit_engine.log_decision(context.workflow, step, decided_by, decision, comments)
                    result.actions.append("AUDIT_LOGGED")

            # Check if workflow is complete
            if context.workflow and context.workflow.status in [WorkflowStatus.APPROVED, WorkflowStatus.REJECTED]:
                result.actions.append(f"WORKFLOW_{context.workflow.status.value}")
                if self._on_workflow_complete:
                    self._on_workflow_complete(context.workflow)

            result.success = True
            result.message = f"Decision {decision} recorded for step {step_id}"

        except Exception as e:
            logger.error(f"Record decision failed: {e}")
            result.success = False
            result.errors.append(str(e))

        return result

    def check_sla_status(self, request_id: str) -> OrchestrationResult:
        """
        Check SLA status for all pending steps.

        Returns warnings and triggers escalations if needed.
        """
        result = OrchestrationResult(operation="CHECK_SLA")

        context = self._contexts.get(request_id)
        if not context or not context.workflow:
            result.success = False
            result.errors.append(f"Request {request_id} not found")
            return result

        try:
            for step in context.workflow.steps:
                if step.status == StepStatus.PENDING:
                    sla_check = self.sla_manager.check_step_sla(step)
                    result.sla_checks.append(sla_check)

                    if sla_check.is_breached:
                        # Emit SLA breach event
                        event = WorkflowEvent.sla_breach(
                            context.workflow.workflow_id,
                            step.step_id,
                            sla_check.elapsed_hours - sla_check.sla_hours,
                            sla_check.escalation_targets
                        )
                        self.reevaluation_engine.emit_event(event)
                        result.actions.append(f"SLA_BREACH_{step.step_id}")

                        if self._on_sla_breach:
                            self._on_sla_breach(context.workflow, step, sla_check)

                    elif sla_check.is_warning:
                        result.warnings.append(
                            f"Step {step.step_id} approaching SLA: {sla_check.remaining_hours:.1f}h remaining"
                        )

            # Process any triggered events
            reeval_results = self.reevaluation_engine.process_pending_events({
                "request_id": request_id,
                "workflow_id": context.workflow.workflow_id,
            })
            result.reevaluation_results = reeval_results

            result.success = True
            result.message = f"SLA check complete: {len(result.sla_checks)} steps checked"

        except Exception as e:
            logger.error(f"SLA check failed: {e}")
            result.success = False
            result.errors.append(str(e))

        return result

    def on_risk_change(
        self,
        request_id: str,
        item_id: Optional[str],
        old_score: int,
        new_score: int,
        reason: str
    ) -> OrchestrationResult:
        """
        Handle risk score change event.

        This may trigger:
        - Workflow modification (add/remove steps)
        - Provisioning hold/release
        - Notifications
        """
        result = OrchestrationResult(operation="RISK_CHANGE")

        context = self._contexts.get(request_id)
        if not context:
            result.success = False
            result.errors.append(f"Request {request_id} not found")
            return result

        try:
            # Update risk in context
            if context.workflow_context:
                context.workflow_context.risk_score = new_score

            if context.access_request and item_id:
                item = next((i for i in context.access_request.items if i.item_id == item_id), None)
                if item:
                    item.risk_score = new_score
                    item.risk_level = "HIGH" if new_score >= 70 else "MEDIUM" if new_score >= 40 else "LOW"

            # Trigger re-evaluation
            reeval_results = self.reevaluation_engine.on_risk_change(
                request_id, item_id, old_score, new_score, reason
            )
            result.reevaluation_results = reeval_results

            # Check what actions were taken
            for rr in reeval_results:
                for action in rr.actions_taken:
                    result.actions.append(action.value)

            # Re-evaluate provisioning
            if context.access_request:
                prov_result = self.provisioning_engine.evaluate_request(context.access_request)
                result.provisioning_result = prov_result

            result.success = True
            result.message = f"Risk change processed: {old_score} -> {new_score}"

        except Exception as e:
            logger.error(f"Risk change handling failed: {e}")
            result.success = False
            result.errors.append(str(e))

        return result

    def on_external_event(
        self,
        event_type: EventType,
        payload: Dict[str, Any]
    ) -> OrchestrationResult:
        """
        Handle external events (fraud alerts, control failures, etc.)

        These events may affect multiple requests.
        """
        result = OrchestrationResult(operation="EXTERNAL_EVENT")

        try:
            event = WorkflowEvent(
                event_type=event_type,
                priority=EventPriority.HIGH if event_type in [
                    EventType.FRAUD_ALERT, EventType.SECURITY_INCIDENT
                ] else EventPriority.NORMAL,
                source=EventSource.EXTERNAL_SYSTEM,
                request_id=payload.get("request_id"),
                user_id=payload.get("user_id"),
                payload=payload,
            )

            self.reevaluation_engine.emit_event(event)

            # If user-related, find all their requests
            affected_requests = []
            if payload.get("user_id"):
                user_id = payload["user_id"]
                for ctx in self._contexts.values():
                    if ctx.workflow_context and ctx.workflow_context.requester_id == user_id:
                        affected_requests.append(ctx.request_id)

            # Process events with affected request contexts
            for request_id in affected_requests:
                context = self._contexts.get(request_id)
                if context:
                    reeval_results = self.reevaluation_engine.process_pending_events({
                        "request_id": request_id,
                        "workflow_id": context.workflow.workflow_id if context.workflow else None,
                    })
                    result.reevaluation_results.extend(reeval_results)

            # If no specific requests, process globally
            if not affected_requests:
                reeval_results = self.reevaluation_engine.process_pending_events({})
                result.reevaluation_results = reeval_results

            result.success = True
            result.message = f"External event {event_type.value} processed"
            result.actions.append(f"EVENT_{event_type.value}")

        except Exception as e:
            logger.error(f"External event handling failed: {e}")
            result.success = False
            result.errors.append(str(e))

        return result

    # ============================================================
    # STATUS AND REPORTING
    # ============================================================

    def get_request_status(self, request_id: str) -> Dict[str, Any]:
        """Get complete status of a request."""
        context = self._contexts.get(request_id)
        if not context:
            return {"error": f"Request {request_id} not found"}

        status = {
            "request_id": request_id,
            "process_type": context.process_type.value,
            "created_at": context.created_at.isoformat(),
            "last_activity": context.last_activity.isoformat(),
        }

        if context.workflow:
            status["workflow"] = {
                "id": context.workflow.workflow_id,
                "status": context.workflow.status.value,
                "steps": [
                    {
                        "id": s.step_id,
                        "name": s.name,
                        "status": s.status.value,
                        "approver": s.approver_name,
                    }
                    for s in context.workflow.steps
                ]
            }

        if context.access_request:
            status["access_request"] = context.access_request.to_dict()
            status["provisioning"] = {
                "strategy": self.provisioning_policy.strategy.value,
                "status": self.provisioning_engine.explain_provisioning(context.access_request),
            }

        return status

    def get_audit_report(self, request_id: str) -> str:
        """Get audit report for a request."""
        context = self._contexts.get(request_id)
        if not context or not context.workflow:
            return f"Request {request_id} not found"

        return self.audit_engine.generate_audit_report(context.workflow)

    def get_explainability_report(self, request_id: str) -> str:
        """Get human-readable explanation of workflow decisions."""
        context = self._contexts.get(request_id)
        if not context or not context.workflow:
            return f"Request {request_id} not found"

        return self.audit_engine.explain_for_requester(context.workflow)

    # ============================================================
    # CALLBACKS
    # ============================================================

    def on_workflow_complete(self, callback: Callable[[Workflow], None]) -> None:
        """Register callback for workflow completion."""
        self._on_workflow_complete = callback

    def on_item_provisioned(self, callback: Callable[[AccessItem], None]) -> None:
        """Register callback for item provisioning."""
        self._on_item_provisioned = callback

    def on_sla_breach(self, callback: Callable[[Workflow, WorkflowStep, SLACheck], None]) -> None:
        """Register callback for SLA breach."""
        self._on_sla_breach = callback

    # ============================================================
    # POLICY MANAGEMENT
    # ============================================================

    def load_policy(self, policy_set: PolicySet) -> None:
        """Load a policy set into the policy engine."""
        self.policy_engine.load_policy_set(policy_set)

    def set_provisioning_policy(self, policy: ProvisioningPolicy) -> None:
        """Set the provisioning policy."""
        self.provisioning_policy = policy
        self.provisioning_engine = ProvisioningEngine(policy)


# ============================================================
# FACTORY FUNCTIONS
# ============================================================

def create_default_orchestrator() -> WorkflowOrchestrator:
    """Create orchestrator with default configuration."""
    return WorkflowOrchestrator()


def create_msmp_compatible_orchestrator() -> WorkflowOrchestrator:
    """Create orchestrator with MSMP-compatible behavior."""
    from .provisioning import MSMP_COMPATIBLE_POLICY
    return WorkflowOrchestrator(provisioning_policy=MSMP_COMPATIBLE_POLICY)


def create_governex_orchestrator() -> WorkflowOrchestrator:
    """Create orchestrator with full GOVERNEX+ features."""
    from .provisioning import GOVERNEX_DEFAULT_POLICY
    return WorkflowOrchestrator(provisioning_policy=GOVERNEX_DEFAULT_POLICY)
