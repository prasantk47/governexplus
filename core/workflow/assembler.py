# Workflow Assembler
# Dynamic workflow assembly from policy evaluation

"""
Workflow Assembler for GOVERNEX+.

This is the core innovation:
MSMP = static workflow selection
GOVERNEX+ = dynamic workflow assembly

The assembler:
1. Evaluates context against policies
2. Collects actions from matched rules
3. Resolves approvers for each action
4. Builds optimized step sequence
5. Returns fully assembled workflow

Key Principle:
Workflow is CONSTRUCTED, not SELECTED.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import logging

from .models import (
    Workflow, WorkflowStep, WorkflowContext, WorkflowStatus, StepStatus,
    ApproverTypeEnum, ProcessType, WorkflowConfig
)
from .policy import (
    PolicyEngine, PolicyAction, ActionType, RuleMatch
)

logger = logging.getLogger(__name__)


@dataclass
class AssemblyContext:
    """
    Context for workflow assembly.

    Contains everything needed to assemble the workflow.
    """
    workflow_context: WorkflowContext
    policy_id: Optional[str] = None

    # Results from policy evaluation
    matched_rules: List[RuleMatch] = field(default_factory=list)
    actions: List[PolicyAction] = field(default_factory=list)

    # Resolved approvers (populated during assembly)
    resolved_approvers: Dict[ApproverTypeEnum, Dict[str, Any]] = field(default_factory=dict)

    # Assembly decisions
    is_auto_approved: bool = False
    is_auto_rejected: bool = False
    auto_decision_reason: str = ""

    # Optimization hints
    priority_boost: bool = False
    expedite_sla: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "policy_id": self.policy_id,
            "matched_rules": len(self.matched_rules),
            "actions_count": len(self.actions),
            "is_auto_approved": self.is_auto_approved,
            "is_auto_rejected": self.is_auto_rejected,
        }


@dataclass
class AssemblyResult:
    """
    Result of workflow assembly.
    """
    success: bool = True
    workflow: Optional[Workflow] = None

    # Assembly metadata
    rules_evaluated: int = 0
    rules_matched: int = 0
    steps_created: int = 0

    # Decision path (for explainability)
    decision_path: List[str] = field(default_factory=list)

    # Warnings
    warnings: List[str] = field(default_factory=list)

    # Errors
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "workflow_id": self.workflow.workflow_id if self.workflow else None,
            "rules_evaluated": self.rules_evaluated,
            "rules_matched": self.rules_matched,
            "steps_created": self.steps_created,
            "decision_path": self.decision_path,
            "warnings": self.warnings,
            "errors": self.errors,
        }


class WorkflowAssembler:
    """
    Assembles workflows dynamically based on policy evaluation.

    This is the heart of GOVERNEX+ workflow engine.
    """

    def __init__(
        self,
        policy_engine: Optional[PolicyEngine] = None,
        config: Optional[WorkflowConfig] = None
    ):
        """Initialize assembler."""
        self.policy_engine = policy_engine or PolicyEngine()
        self.config = config or WorkflowConfig()

        # Approver resolvers (pluggable)
        self._resolvers: Dict[ApproverTypeEnum, callable] = {}
        self._init_default_resolvers()

    def _init_default_resolvers(self) -> None:
        """Initialize default approver resolvers."""
        # Default resolvers return placeholder IDs
        # In production, these would integrate with HR, IAM, etc.

        def resolve_line_manager(context: WorkflowContext) -> Dict[str, Any]:
            return {
                "id": context.target_user_manager_id or f"MGR_{context.target_user_id}",
                "name": f"Manager of {context.target_user_name}",
                "email": f"manager_{context.target_user_id}@company.com",
            }

        def resolve_role_owner(context: WorkflowContext) -> Dict[str, Any]:
            return {
                "id": f"ROLE_OWNER_{context.role_id}",
                "name": f"Owner of {context.role_name or context.role_id}",
                "email": f"role_owner_{context.role_id}@company.com",
            }

        def resolve_process_owner(context: WorkflowContext) -> Dict[str, Any]:
            return {
                "id": f"PROCESS_OWNER_{context.business_process}",
                "name": f"{context.business_process} Process Owner",
                "email": f"process_owner_{context.business_process.lower()}@company.com",
            }

        def resolve_data_owner(context: WorkflowContext) -> Dict[str, Any]:
            data_types = context.sensitive_data_access or ["GENERAL"]
            return {
                "id": f"DATA_OWNER_{data_types[0]}",
                "name": f"{data_types[0]} Data Owner",
                "email": f"data_owner_{data_types[0].lower()}@company.com",
            }

        def resolve_system_owner(context: WorkflowContext) -> Dict[str, Any]:
            return {
                "id": f"SYSTEM_OWNER_{context.system_id}",
                "name": f"{context.system_name or context.system_id} System Owner",
                "email": f"system_owner_{context.system_id.lower()}@company.com",
            }

        def resolve_security_officer(context: WorkflowContext) -> Dict[str, Any]:
            return {
                "id": "SECURITY_TEAM",
                "name": "Security Team",
                "email": "security@company.com",
            }

        def resolve_compliance_officer(context: WorkflowContext) -> Dict[str, Any]:
            return {
                "id": "COMPLIANCE_TEAM",
                "name": "Compliance Team",
                "email": "compliance@company.com",
            }

        def resolve_ciso(context: WorkflowContext) -> Dict[str, Any]:
            return {
                "id": "CISO",
                "name": "Chief Information Security Officer",
                "email": "ciso@company.com",
            }

        def resolve_firefighter_supervisor(context: WorkflowContext) -> Dict[str, Any]:
            return {
                "id": "FF_SUPERVISOR",
                "name": "Firefighter Supervisor",
                "email": "ff_supervisor@company.com",
            }

        def resolve_governance_desk(context: WorkflowContext) -> Dict[str, Any]:
            return {
                "id": "GOVERNANCE_DESK",
                "name": "Governance Desk",
                "email": "governance@company.com",
            }

        self._resolvers = {
            ApproverTypeEnum.LINE_MANAGER: resolve_line_manager,
            ApproverTypeEnum.ROLE_OWNER: resolve_role_owner,
            ApproverTypeEnum.PROCESS_OWNER: resolve_process_owner,
            ApproverTypeEnum.DATA_OWNER: resolve_data_owner,
            ApproverTypeEnum.SYSTEM_OWNER: resolve_system_owner,
            ApproverTypeEnum.SECURITY_OFFICER: resolve_security_officer,
            ApproverTypeEnum.COMPLIANCE_OFFICER: resolve_compliance_officer,
            ApproverTypeEnum.CISO: resolve_ciso,
            ApproverTypeEnum.FIREFIGHTER_SUPERVISOR: resolve_firefighter_supervisor,
            ApproverTypeEnum.GOVERNANCE_DESK: resolve_governance_desk,
        }

    def register_resolver(
        self,
        approver_type: ApproverTypeEnum,
        resolver: callable
    ) -> None:
        """
        Register a custom approver resolver.

        Resolver should accept WorkflowContext and return Dict with:
        - id: Approver ID
        - name: Approver name
        - email: Approver email
        """
        self._resolvers[approver_type] = resolver

    def assemble(
        self,
        context: WorkflowContext,
        policy_id: Optional[str] = None
    ) -> AssemblyResult:
        """
        Assemble a workflow for the given context.

        This is the main entry point.

        Args:
            context: Workflow context
            policy_id: Optional specific policy to use

        Returns:
            AssemblyResult with assembled workflow
        """
        result = AssemblyResult()
        decision_path = []

        try:
            # Step 1: Evaluate policy
            decision_path.append(f"1. Evaluating policy for request {context.request_id}")
            matched_rules, actions = self.policy_engine.evaluate(context, policy_id)

            result.rules_evaluated = len(matched_rules)
            result.rules_matched = len([r for r in matched_rules if r.matched])

            decision_path.append(f"   - Evaluated {result.rules_evaluated} rules")
            decision_path.append(f"   - {result.rules_matched} rules matched")

            # Create assembly context
            assembly_ctx = AssemblyContext(
                workflow_context=context,
                policy_id=policy_id,
                matched_rules=matched_rules,
                actions=actions,
            )

            # Step 2: Check for auto-decisions
            decision_path.append("2. Checking for auto-decisions")

            for action in actions:
                if action.action_type == ActionType.AUTO_APPROVE:
                    assembly_ctx.is_auto_approved = True
                    assembly_ctx.auto_decision_reason = action.reason
                    decision_path.append(f"   - AUTO_APPROVE: {action.reason}")
                    break
                elif action.action_type == ActionType.AUTO_REJECT:
                    assembly_ctx.is_auto_rejected = True
                    assembly_ctx.auto_decision_reason = action.reason
                    decision_path.append(f"   - AUTO_REJECT: {action.reason}")
                    break

            # Step 3: Create workflow
            decision_path.append("3. Creating workflow")

            workflow = Workflow(
                process_type=context.process_type,
                context=context,
                assembled_by_policy=policy_id or "CORE-GOVERNANCE",
                assembly_rules_matched=[r.rule.rule_id for r in matched_rules if r.matched],
            )

            # Handle auto-decisions
            if assembly_ctx.is_auto_approved:
                workflow.status = WorkflowStatus.AUTO_APPROVED
                workflow.final_decision = "APPROVED"
                workflow.final_decision_at = datetime.now()
                workflow.assembly_explanation = assembly_ctx.auto_decision_reason
                decision_path.append("   - Workflow auto-approved")

            elif assembly_ctx.is_auto_rejected:
                workflow.status = WorkflowStatus.AUTO_REJECTED
                workflow.final_decision = "REJECTED"
                workflow.final_decision_at = datetime.now()
                workflow.assembly_explanation = assembly_ctx.auto_decision_reason
                decision_path.append("   - Workflow auto-rejected")

            else:
                # Step 4: Build approval steps
                decision_path.append("4. Building approval steps")

                steps = self._build_steps(assembly_ctx, decision_path)
                workflow.steps = steps
                workflow.status = WorkflowStatus.PENDING

                result.steps_created = len(steps)
                decision_path.append(f"   - Created {len(steps)} approval step(s)")

                # Build explanation
                approver_types = [s.approver_type.value for s in steps]
                workflow.assembly_explanation = (
                    f"Workflow assembled with {len(steps)} step(s): {', '.join(approver_types)}"
                )

            # Step 5: Set post-workflow actions
            decision_path.append("5. Setting post-workflow actions")

            for action in actions:
                if action.action_type == ActionType.ADD_POST_REVIEW:
                    workflow.post_approval_actions.append("POST_ACCESS_REVIEW")
                    decision_path.append("   - Added post-access review")
                elif action.action_type == ActionType.NOTIFY:
                    workflow.post_approval_actions.append(
                        f"NOTIFY:{action.parameters.get('target', 'requester')}"
                    )

            # Add audit entry
            workflow.add_audit_entry("WORKFLOW_ASSEMBLED", {
                "policy_id": policy_id or "CORE-GOVERNANCE",
                "rules_matched": result.rules_matched,
                "steps_created": result.steps_created,
                "decision_path": decision_path,
            })

            result.workflow = workflow
            result.decision_path = decision_path
            result.success = True

        except Exception as e:
            logger.error(f"Workflow assembly failed: {e}")
            result.success = False
            result.errors.append(str(e))
            result.decision_path = decision_path

        return result

    def _build_steps(
        self,
        assembly_ctx: AssemblyContext,
        decision_path: List[str]
    ) -> List[WorkflowStep]:
        """Build workflow steps from actions."""
        steps = []
        step_number = 1

        # Collect ADD_APPROVER actions
        approver_actions = [
            a for a in assembly_ctx.actions
            if a.action_type == ActionType.ADD_APPROVER
        ]

        # Deduplicate by approver type
        seen_types = set()
        unique_actions = []
        for action in approver_actions:
            if action.approver_type and action.approver_type not in seen_types:
                seen_types.add(action.approver_type)
                unique_actions.append(action)

        # Create steps
        for action in unique_actions:
            if not action.approver_type:
                continue

            # Resolve approver
            approver_info = self._resolve_approver(
                action.approver_type,
                assembly_ctx.workflow_context
            )

            # Determine SLA
            sla_hours = action.sla_hours
            if not sla_hours:
                sla_hours = self._get_default_sla(assembly_ctx.workflow_context)

            # Apply SLA modifiers
            for mod_action in assembly_ctx.actions:
                if mod_action.action_type == ActionType.SET_SLA:
                    sla_hours = min(sla_hours, mod_action.sla_hours or sla_hours)

            # Create step
            step = WorkflowStep(
                step_number=step_number,
                name=f"{action.approver_type.value} Approval",
                description=action.reason,
                approver_type=action.approver_type,
                approver_id=approver_info.get("id"),
                approver_name=approver_info.get("name"),
                approver_email=approver_info.get("email"),
                sla_hours=sla_hours,
                reminder_hours=sla_hours / 2,
                escalation_hours=sla_hours * 1.5,
                reason=action.reason,
                policy_rule_id=self._find_rule_for_action(action, assembly_ctx),
                status=StepStatus.PENDING,
            )

            # Calculate due date
            step.due_at = datetime.now() + timedelta(hours=sla_hours)

            steps.append(step)
            step_number += 1

            decision_path.append(
                f"   - Step {step.step_number}: {action.approver_type.value} "
                f"({approver_info.get('name', 'Unknown')}) - SLA: {sla_hours}h"
            )

        # Check for REQUIRE_JUSTIFICATION action
        for action in assembly_ctx.actions:
            if action.action_type == ActionType.REQUIRE_JUSTIFICATION:
                for step in steps:
                    step.require_all = True  # Require comments

        return steps

    def _resolve_approver(
        self,
        approver_type: ApproverTypeEnum,
        context: WorkflowContext
    ) -> Dict[str, Any]:
        """Resolve approver using registered resolver."""
        resolver = self._resolvers.get(approver_type)
        if resolver:
            try:
                return resolver(context)
            except Exception as e:
                logger.warning(f"Resolver failed for {approver_type}: {e}")

        # Fallback
        return {
            "id": f"UNKNOWN_{approver_type.value}",
            "name": approver_type.value,
            "email": f"{approver_type.value.lower()}@company.com",
        }

    def _get_default_sla(self, context: WorkflowContext) -> float:
        """Get default SLA based on risk level."""
        return self.config.sla_by_risk.get(context.risk_level, 24.0)

    def _find_rule_for_action(
        self,
        action: PolicyAction,
        assembly_ctx: AssemblyContext
    ) -> str:
        """Find the rule that created this action."""
        for match in assembly_ctx.matched_rules:
            if match.matched and action in match.actions_to_execute:
                return match.rule.rule_id
        return "UNKNOWN"

    def simulate(
        self,
        context: WorkflowContext,
        policy_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Simulate workflow assembly without creating.

        Useful for what-if analysis and previews.
        """
        result = self.assemble(context, policy_id)

        return {
            "success": result.success,
            "would_create_workflow": result.workflow is not None,
            "status": result.workflow.status.value if result.workflow else None,
            "steps": [
                {
                    "number": s.step_number,
                    "approver_type": s.approver_type.value,
                    "approver_name": s.approver_name,
                    "sla_hours": s.sla_hours,
                    "reason": s.reason,
                }
                for s in (result.workflow.steps if result.workflow else [])
            ],
            "decision_path": result.decision_path,
            "auto_decision": (
                result.workflow.final_decision if result.workflow and result.workflow.final_decision
                else None
            ),
        }

    def explain(
        self,
        context: WorkflowContext,
        policy_id: Optional[str] = None
    ) -> str:
        """
        Generate human-readable explanation of workflow assembly.

        For requesters and auditors.
        """
        result = self.assemble(context, policy_id)
        lines = []

        lines.append("=" * 60)
        lines.append("WORKFLOW ASSEMBLY EXPLANATION")
        lines.append("=" * 60)
        lines.append("")

        lines.append(f"Request: {context.request_id}")
        lines.append(f"Process Type: {context.process_type.value}")
        lines.append(f"System: {context.system_name or context.system_id}")
        lines.append(f"Risk Score: {context.risk_score}/100 ({context.risk_level})")
        lines.append("")

        lines.append("-" * 40)
        lines.append("DECISION PATH")
        lines.append("-" * 40)
        for step in result.decision_path:
            lines.append(step)
        lines.append("")

        if result.workflow:
            lines.append("-" * 40)
            lines.append("RESULT")
            lines.append("-" * 40)
            lines.append(f"Status: {result.workflow.status.value}")

            if result.workflow.steps:
                lines.append(f"Approvers Required: {len(result.workflow.steps)}")
                for step in result.workflow.steps:
                    lines.append(f"  {step.step_number}. {step.approver_name} ({step.approver_type.value})")
                    lines.append(f"     Reason: {step.reason}")
                    lines.append(f"     SLA: {step.sla_hours} hours")
            else:
                lines.append(f"Decision: {result.workflow.final_decision}")
                lines.append(f"Reason: {result.workflow.assembly_explanation}")

        lines.append("")
        lines.append("=" * 60)

        return "\n".join(lines)
