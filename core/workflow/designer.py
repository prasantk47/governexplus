"""
Visual Workflow Designer

SAP GRC-equivalent workflow designer with drag-and-drop visual builder,
conditional logic, parallel paths, and escalation rules.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
from datetime import datetime, timedelta
import uuid
import json


class StepType(Enum):
    """Workflow step types"""
    START = "start"
    END = "end"
    APPROVAL = "approval"
    NOTIFICATION = "notification"
    CONDITION = "condition"
    PARALLEL_SPLIT = "parallel_split"
    PARALLEL_JOIN = "parallel_join"
    ASSIGNMENT = "assignment"
    SCRIPT = "script"
    WAIT = "wait"
    SUBPROCESS = "subprocess"


class ApprovalStrategy(Enum):
    """Approval strategies for multi-approver steps"""
    ANY = "any"              # Any one approver can approve
    ALL = "all"              # All approvers must approve
    MAJORITY = "majority"    # Majority must approve
    FIRST_RESPONSE = "first_response"  # First responder decides


class EscalationType(Enum):
    """Escalation types"""
    NONE = "none"
    MANAGER = "manager"          # Escalate to approver's manager
    ROLE = "role"                # Escalate to specific role
    USER = "user"                # Escalate to specific user
    AUTO_APPROVE = "auto_approve"  # Auto-approve after timeout
    AUTO_REJECT = "auto_reject"    # Auto-reject after timeout


@dataclass
class Position:
    """Position for visual designer"""
    x: int = 0
    y: int = 0


@dataclass
class WorkflowStep:
    """Workflow step definition"""
    step_id: str
    step_type: StepType
    name: str
    description: str = ""

    # Visual position
    position: Position = field(default_factory=Position)

    # Connections
    next_steps: List[str] = field(default_factory=list)  # Step IDs
    previous_steps: List[str] = field(default_factory=list)

    # Approval configuration
    approvers: List[str] = field(default_factory=list)  # User IDs or role names
    approver_type: str = "user"  # user, role, manager, dynamic
    approval_strategy: ApprovalStrategy = ApprovalStrategy.ANY
    allow_delegation: bool = True
    allow_reassignment: bool = True

    # Condition configuration
    condition_expression: str = ""  # e.g., "risk_level == 'critical'"
    true_branch: Optional[str] = None  # Step ID
    false_branch: Optional[str] = None  # Step ID

    # Timing
    due_hours: int = 48
    reminder_hours: int = 24
    escalation_hours: int = 72

    # Escalation
    escalation_type: EscalationType = EscalationType.MANAGER
    escalation_target: str = ""
    escalation_levels: int = 2

    # Notification
    notification_template: str = ""
    notification_recipients: List[str] = field(default_factory=list)

    # Script/custom logic
    script_code: str = ""
    script_language: str = "python"

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkflowDefinition:
    """Complete workflow definition"""
    workflow_id: str
    tenant_id: str
    name: str
    description: str
    workflow_type: str  # access_request, certification, firefighter, custom

    # Version control
    version: int = 1
    is_active: bool = True
    is_draft: bool = True

    # Steps
    steps: Dict[str, WorkflowStep] = field(default_factory=dict)
    start_step_id: Optional[str] = None
    end_step_ids: List[str] = field(default_factory=list)

    # Trigger conditions
    trigger_conditions: Dict[str, Any] = field(default_factory=dict)

    # Global settings
    sla_hours: int = 48
    auto_complete_on_timeout: bool = False
    allow_withdrawal: bool = True
    require_comments_on_reject: bool = True

    # Visual layout
    canvas_width: int = 1200
    canvas_height: int = 800

    # Metadata
    created_by: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    published_at: Optional[datetime] = None


@dataclass
class WorkflowInstance:
    """Running workflow instance"""
    instance_id: str
    workflow_id: str
    tenant_id: str

    # Context
    context_type: str  # access_request, certification_item, etc.
    context_id: str
    context_data: Dict[str, Any] = field(default_factory=dict)

    # Execution state
    status: str = "running"  # running, completed, cancelled, error
    current_step_id: Optional[str] = None
    completed_steps: List[str] = field(default_factory=list)

    # History
    history: List[Dict[str, Any]] = field(default_factory=list)

    # Timing
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    due_at: Optional[datetime] = None

    # Result
    outcome: Optional[str] = None  # approved, rejected, cancelled


class WorkflowDesigner:
    """
    Visual Workflow Designer

    Provides:
    1. Drag-and-drop workflow creation
    2. Conditional branching
    3. Parallel approval paths
    4. Automatic escalation
    5. Custom scripts and integrations
    """

    def __init__(self):
        self.definitions: Dict[str, WorkflowDefinition] = {}
        self.instances: Dict[str, WorkflowInstance] = {}

        # Initialize standard workflows
        self._initialize_standard_workflows()

    def _initialize_standard_workflows(self):
        """Initialize standard workflow templates"""

        # Access Request Workflow
        self.create_standard_access_request_workflow("__system__")

        # Certification Review Workflow
        self.create_standard_certification_workflow("__system__")

        # Firefighter Approval Workflow
        self.create_standard_firefighter_workflow("__system__")

    # ==================== Workflow Design ====================

    def create_workflow(
        self,
        tenant_id: str,
        name: str,
        description: str,
        workflow_type: str,
        created_by: str = ""
    ) -> WorkflowDefinition:
        """Create a new workflow definition"""
        workflow_id = f"WF_{tenant_id}_{workflow_type}_{uuid.uuid4().hex[:8]}"

        # Create start and end steps
        start_step = WorkflowStep(
            step_id="start",
            step_type=StepType.START,
            name="Start",
            position=Position(100, 400)
        )

        end_step = WorkflowStep(
            step_id="end",
            step_type=StepType.END,
            name="End",
            position=Position(1100, 400)
        )

        workflow = WorkflowDefinition(
            workflow_id=workflow_id,
            tenant_id=tenant_id,
            name=name,
            description=description,
            workflow_type=workflow_type,
            steps={"start": start_step, "end": end_step},
            start_step_id="start",
            end_step_ids=["end"],
            created_by=created_by
        )

        self.definitions[workflow_id] = workflow
        return workflow

    def add_step(
        self,
        workflow_id: str,
        step_type: StepType,
        name: str,
        position: Position = None,
        **kwargs
    ) -> WorkflowStep:
        """Add a step to a workflow"""
        workflow = self.definitions.get(workflow_id)
        if not workflow:
            raise ValueError(f"Workflow not found: {workflow_id}")

        step_id = f"step_{uuid.uuid4().hex[:8]}"

        step = WorkflowStep(
            step_id=step_id,
            step_type=step_type,
            name=name,
            position=position or Position(500, 400),
            **kwargs
        )

        workflow.steps[step_id] = step
        workflow.updated_at = datetime.utcnow()

        return step

    def connect_steps(
        self,
        workflow_id: str,
        from_step_id: str,
        to_step_id: str,
        branch: str = None  # 'true' or 'false' for condition steps
    ) -> bool:
        """Connect two steps"""
        workflow = self.definitions.get(workflow_id)
        if not workflow:
            return False

        from_step = workflow.steps.get(from_step_id)
        to_step = workflow.steps.get(to_step_id)

        if not from_step or not to_step:
            return False

        # Handle condition branching
        if from_step.step_type == StepType.CONDITION:
            if branch == "true":
                from_step.true_branch = to_step_id
            elif branch == "false":
                from_step.false_branch = to_step_id
        else:
            if to_step_id not in from_step.next_steps:
                from_step.next_steps.append(to_step_id)

        if from_step_id not in to_step.previous_steps:
            to_step.previous_steps.append(from_step_id)

        workflow.updated_at = datetime.utcnow()
        return True

    def delete_step(self, workflow_id: str, step_id: str) -> bool:
        """Delete a step from a workflow"""
        workflow = self.definitions.get(workflow_id)
        if not workflow or step_id not in workflow.steps:
            return False

        if step_id in ["start", "end"]:
            return False  # Cannot delete start/end

        step = workflow.steps[step_id]

        # Remove connections
        for prev_id in step.previous_steps:
            prev_step = workflow.steps.get(prev_id)
            if prev_step:
                if step_id in prev_step.next_steps:
                    prev_step.next_steps.remove(step_id)
                if prev_step.true_branch == step_id:
                    prev_step.true_branch = None
                if prev_step.false_branch == step_id:
                    prev_step.false_branch = None

        for next_id in step.next_steps:
            next_step = workflow.steps.get(next_id)
            if next_step and step_id in next_step.previous_steps:
                next_step.previous_steps.remove(step_id)

        del workflow.steps[step_id]
        workflow.updated_at = datetime.utcnow()
        return True

    def update_step(
        self,
        workflow_id: str,
        step_id: str,
        **updates
    ) -> Optional[WorkflowStep]:
        """Update step properties"""
        workflow = self.definitions.get(workflow_id)
        if not workflow or step_id not in workflow.steps:
            return None

        step = workflow.steps[step_id]
        for key, value in updates.items():
            if hasattr(step, key):
                setattr(step, key, value)

        workflow.updated_at = datetime.utcnow()
        return step

    # ==================== Workflow Validation ====================

    def validate_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """Validate workflow structure"""
        workflow = self.definitions.get(workflow_id)
        if not workflow:
            return {"valid": False, "errors": ["Workflow not found"]}

        errors = []
        warnings = []

        # Check start step exists
        if not workflow.start_step_id:
            errors.append("No start step defined")

        # Check end steps exist
        if not workflow.end_step_ids:
            errors.append("No end steps defined")

        # Check all steps are reachable
        reachable = self._find_reachable_steps(workflow, workflow.start_step_id)
        for step_id, step in workflow.steps.items():
            if step_id not in reachable and step.step_type != StepType.START:
                warnings.append(f"Step '{step.name}' ({step_id}) is not reachable")

        # Check all paths lead to end
        for step_id, step in workflow.steps.items():
            if step.step_type not in [StepType.END, StepType.PARALLEL_SPLIT]:
                if not step.next_steps and step.step_type != StepType.CONDITION:
                    if step_id not in workflow.end_step_ids:
                        errors.append(f"Step '{step.name}' has no outgoing connections")

                if step.step_type == StepType.CONDITION:
                    if not step.true_branch:
                        errors.append(f"Condition '{step.name}' has no true branch")
                    if not step.false_branch:
                        errors.append(f"Condition '{step.name}' has no false branch")

        # Check approval steps have approvers
        for step_id, step in workflow.steps.items():
            if step.step_type == StepType.APPROVAL:
                if not step.approvers and step.approver_type not in ["manager", "dynamic"]:
                    warnings.append(f"Approval step '{step.name}' has no approvers defined")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }

    def _find_reachable_steps(
        self,
        workflow: WorkflowDefinition,
        start_id: str,
        visited: set = None
    ) -> set:
        """Find all steps reachable from a starting step"""
        if visited is None:
            visited = set()

        if start_id in visited:
            return visited

        visited.add(start_id)
        step = workflow.steps.get(start_id)

        if step:
            for next_id in step.next_steps:
                self._find_reachable_steps(workflow, next_id, visited)
            if step.true_branch:
                self._find_reachable_steps(workflow, step.true_branch, visited)
            if step.false_branch:
                self._find_reachable_steps(workflow, step.false_branch, visited)

        return visited

    # ==================== Workflow Publishing ====================

    def publish_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """Publish a workflow for use"""
        validation = self.validate_workflow(workflow_id)
        if not validation["valid"]:
            return {"success": False, "errors": validation["errors"]}

        workflow = self.definitions[workflow_id]
        workflow.is_draft = False
        workflow.is_active = True
        workflow.version += 1
        workflow.published_at = datetime.utcnow()
        workflow.updated_at = datetime.utcnow()

        return {
            "success": True,
            "version": workflow.version,
            "published_at": workflow.published_at.isoformat()
        }

    def unpublish_workflow(self, workflow_id: str) -> bool:
        """Unpublish a workflow"""
        workflow = self.definitions.get(workflow_id)
        if workflow:
            workflow.is_active = False
            workflow.updated_at = datetime.utcnow()
            return True
        return False

    # ==================== Standard Workflows ====================

    def create_standard_access_request_workflow(
        self,
        tenant_id: str
    ) -> WorkflowDefinition:
        """Create standard access request workflow"""
        workflow = self.create_workflow(
            tenant_id=tenant_id,
            name="Access Request Approval",
            description="Standard multi-level access request approval workflow",
            workflow_type="access_request"
        )

        # Add steps
        risk_check = self.add_step(
            workflow.workflow_id,
            StepType.CONDITION,
            "Risk Level Check",
            Position(250, 400),
            condition_expression="risk_level in ['high', 'critical']"
        )

        manager_approval = self.add_step(
            workflow.workflow_id,
            StepType.APPROVAL,
            "Manager Approval",
            Position(400, 250),
            approver_type="manager",
            approval_strategy=ApprovalStrategy.ANY,
            due_hours=24
        )

        role_owner_approval = self.add_step(
            workflow.workflow_id,
            StepType.APPROVAL,
            "Role Owner Approval",
            Position(600, 250),
            approver_type="role",
            approvers=["ROLE_OWNER"],
            due_hours=48
        )

        risk_owner_approval = self.add_step(
            workflow.workflow_id,
            StepType.APPROVAL,
            "Risk Owner Approval",
            Position(400, 550),
            approver_type="role",
            approvers=["RISK_OWNER"],
            due_hours=24
        )

        security_approval = self.add_step(
            workflow.workflow_id,
            StepType.APPROVAL,
            "Security Approval",
            Position(600, 550),
            approver_type="role",
            approvers=["SECURITY_ADMIN"],
            due_hours=48
        )

        provision = self.add_step(
            workflow.workflow_id,
            StepType.SCRIPT,
            "Provision Access",
            Position(850, 400),
            script_code="provision_access(context)"
        )

        notify = self.add_step(
            workflow.workflow_id,
            StepType.NOTIFICATION,
            "Notify Requester",
            Position(1000, 400),
            notification_template="access_request_completed"
        )

        # Connect steps
        self.connect_steps(workflow.workflow_id, "start", risk_check.step_id)

        # Low risk path
        self.connect_steps(workflow.workflow_id, risk_check.step_id, manager_approval.step_id, "false")
        self.connect_steps(workflow.workflow_id, manager_approval.step_id, role_owner_approval.step_id)
        self.connect_steps(workflow.workflow_id, role_owner_approval.step_id, provision.step_id)

        # High risk path
        self.connect_steps(workflow.workflow_id, risk_check.step_id, risk_owner_approval.step_id, "true")
        self.connect_steps(workflow.workflow_id, risk_owner_approval.step_id, security_approval.step_id)
        self.connect_steps(workflow.workflow_id, security_approval.step_id, provision.step_id)

        # Final steps
        self.connect_steps(workflow.workflow_id, provision.step_id, notify.step_id)
        self.connect_steps(workflow.workflow_id, notify.step_id, "end")

        return workflow

    def create_standard_certification_workflow(
        self,
        tenant_id: str
    ) -> WorkflowDefinition:
        """Create standard certification review workflow"""
        workflow = self.create_workflow(
            tenant_id=tenant_id,
            name="Certification Review",
            description="Access certification review workflow",
            workflow_type="certification"
        )

        review = self.add_step(
            workflow.workflow_id,
            StepType.APPROVAL,
            "Manager Review",
            Position(350, 400),
            approver_type="manager",
            approval_strategy=ApprovalStrategy.ANY,
            due_hours=168  # 7 days
        )

        self.connect_steps(workflow.workflow_id, "start", review.step_id)
        self.connect_steps(workflow.workflow_id, review.step_id, "end")

        return workflow

    def create_standard_firefighter_workflow(
        self,
        tenant_id: str
    ) -> WorkflowDefinition:
        """Create standard firefighter approval workflow"""
        workflow = self.create_workflow(
            tenant_id=tenant_id,
            name="Firefighter Approval",
            description="Emergency access approval workflow",
            workflow_type="firefighter"
        )

        controller_approval = self.add_step(
            workflow.workflow_id,
            StepType.APPROVAL,
            "Controller Approval",
            Position(350, 400),
            approver_type="role",
            approvers=["FF_CONTROLLER"],
            due_hours=2,
            escalation_type=EscalationType.AUTO_APPROVE,
            escalation_hours=4
        )

        self.connect_steps(workflow.workflow_id, "start", controller_approval.step_id)
        self.connect_steps(workflow.workflow_id, controller_approval.step_id, "end")

        return workflow

    # ==================== Export/Import ====================

    def export_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """Export workflow to JSON"""
        workflow = self.definitions.get(workflow_id)
        if not workflow:
            return {"error": "Workflow not found"}

        return {
            "version": "1.0",
            "exported_at": datetime.utcnow().isoformat(),
            "workflow": {
                "name": workflow.name,
                "description": workflow.description,
                "workflow_type": workflow.workflow_type,
                "steps": {
                    step_id: {
                        "step_type": step.step_type.value,
                        "name": step.name,
                        "description": step.description,
                        "position": {"x": step.position.x, "y": step.position.y},
                        "next_steps": step.next_steps,
                        "approvers": step.approvers,
                        "approver_type": step.approver_type,
                        "approval_strategy": step.approval_strategy.value,
                        "condition_expression": step.condition_expression,
                        "true_branch": step.true_branch,
                        "false_branch": step.false_branch,
                        "due_hours": step.due_hours,
                        "escalation_type": step.escalation_type.value
                    }
                    for step_id, step in workflow.steps.items()
                },
                "start_step_id": workflow.start_step_id,
                "end_step_ids": workflow.end_step_ids,
                "sla_hours": workflow.sla_hours
            }
        }

    def import_workflow(
        self,
        data: Dict[str, Any],
        tenant_id: str,
        created_by: str = ""
    ) -> WorkflowDefinition:
        """Import workflow from JSON"""
        wf_data = data["workflow"]

        workflow = self.create_workflow(
            tenant_id=tenant_id,
            name=wf_data["name"],
            description=wf_data["description"],
            workflow_type=wf_data["workflow_type"],
            created_by=created_by
        )

        # Clear default steps
        workflow.steps.clear()

        # Import steps
        for step_id, step_data in wf_data["steps"].items():
            step = WorkflowStep(
                step_id=step_id,
                step_type=StepType(step_data["step_type"]),
                name=step_data["name"],
                description=step_data.get("description", ""),
                position=Position(step_data["position"]["x"], step_data["position"]["y"]),
                next_steps=step_data.get("next_steps", []),
                approvers=step_data.get("approvers", []),
                approver_type=step_data.get("approver_type", "user"),
                approval_strategy=ApprovalStrategy(step_data.get("approval_strategy", "any")),
                condition_expression=step_data.get("condition_expression", ""),
                true_branch=step_data.get("true_branch"),
                false_branch=step_data.get("false_branch"),
                due_hours=step_data.get("due_hours", 48),
                escalation_type=EscalationType(step_data.get("escalation_type", "manager"))
            )
            workflow.steps[step_id] = step

        workflow.start_step_id = wf_data["start_step_id"]
        workflow.end_step_ids = wf_data["end_step_ids"]
        workflow.sla_hours = wf_data.get("sla_hours", 48)

        return workflow


# Singleton instance
workflow_designer = WorkflowDesigner()
