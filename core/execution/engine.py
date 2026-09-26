"""
Execution & Verification Engine

Manages the provisioning lifecycle:
    1. Plan  — build list of actions from an approved workflow
    2. Simulate — dry-run against target system (if supported)
    3. Execute — send actions to target system via connector
    4. Verify — read back from target system to confirm
    5. Recalculate — re-run effective access + risk analysis
    6. Close — mark complete or flag discrepancies

This engine does NOT call connectors directly.  It produces
ExecutionPlan/ExecutionAction objects and provides hooks for
callers to implement the actual system calls.
"""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime
from typing import Optional, Callable, Any

from .models import (
    ActionType,
    ExecutionAction,
    ExecutionPhase,
    ExecutionPlan,
    VerificationResult,
)

logger = logging.getLogger(__name__)


# Type for connector callbacks
SimulateCallback = Callable[[ExecutionAction], tuple[bool, str, list[str]]]
ExecuteCallback = Callable[[ExecutionAction], tuple[bool, str, Optional[str]]]
VerifyCallback = Callable[[ExecutionAction], tuple[VerificationResult, str]]


class ExecutionEngine:
    """Orchestrates the provisioning lifecycle."""

    def __init__(self):
        self._plans: dict[str, ExecutionPlan] = {}

    # ------------------------------------------------------------------
    # Plan creation
    # ------------------------------------------------------------------

    def create_plan(
        self,
        request_id: str,
        workflow_id: str,
        user_id: str,
        tenant_id: str,
        actions: list[dict],
        pre_risk_score: float = 0.0,
        pre_violation_count: int = 0,
    ) -> ExecutionPlan:
        """Create an execution plan from an approved workflow.

        Each action dict:
            action_type, target_system, user_id, role_id, parameters
        """
        plan_id = _make_id("PLAN", request_id)

        parsed_actions = []
        for i, a in enumerate(actions):
            action = ExecutionAction(
                action_id=_make_id("ACT", request_id, str(i)),
                action_type=ActionType(a["action_type"]),
                target_system=a.get("target_system", "SAP"),
                target_client=a.get("target_client", ""),
                user_id=a.get("user_id", user_id),
                role_id=a.get("role_id", ""),
                parameters=a.get("parameters", {}),
            )
            parsed_actions.append(action)

        plan = ExecutionPlan(
            plan_id=plan_id,
            request_id=request_id,
            workflow_id=workflow_id,
            user_id=user_id,
            tenant_id=tenant_id,
            actions=parsed_actions,
            pre_risk_score=pre_risk_score,
            pre_violation_count=pre_violation_count,
        )

        self._plans[plan_id] = plan
        self._persist_plan(plan)
        return plan

    # ------------------------------------------------------------------
    # Simulation
    # ------------------------------------------------------------------

    def simulate(
        self,
        plan_id: str,
        simulate_fn: SimulateCallback,
    ) -> ExecutionPlan:
        """Dry-run all actions in the plan.

        simulate_fn(action) should return:
            (success: bool, result_message: str, warnings: list[str])
        """
        plan = self._get_plan(plan_id)
        all_ok = True

        for action in plan.actions:
            success, message, warnings = simulate_fn(action)
            action.simulation_result = message
            action.simulation_warnings = warnings
            action.phase = ExecutionPhase.SIMULATED
            if not success:
                all_ok = False

        plan.phase = ExecutionPhase.SIMULATED if all_ok else ExecutionPhase.FAILED
        plan.simulated_at = datetime.utcnow()
        return plan

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def execute(
        self,
        plan_id: str,
        execute_fn: ExecuteCallback,
        executed_by: str = "",
    ) -> ExecutionPlan:
        """Execute all actions via the connector.

        execute_fn(action) should return:
            (success: bool, response_message: str, target_id: Optional[str])
        """
        plan = self._get_plan(plan_id)
        plan.phase = ExecutionPhase.EXECUTING
        plan.executed_by = executed_by

        all_ok = True
        for action in plan.actions:
            action.phase = ExecutionPhase.EXECUTING
            try:
                success, response, target_id = execute_fn(action)
                action.executed_at = datetime.utcnow()
                action.target_response = response
                action.target_message_id = target_id
                action.phase = ExecutionPhase.EXECUTED if success else ExecutionPhase.FAILED
                if not success:
                    all_ok = False
            except Exception as e:
                logger.error(f"Action {action.action_id} failed: {e}")
                action.phase = ExecutionPhase.FAILED
                action.target_response = str(e)
                all_ok = False

        plan.phase = ExecutionPhase.EXECUTED if all_ok else ExecutionPhase.FAILED
        plan.executed_at = datetime.utcnow()
        return plan

    # ------------------------------------------------------------------
    # Verification
    # ------------------------------------------------------------------

    def verify(
        self,
        plan_id: str,
        verify_fn: VerifyCallback,
    ) -> ExecutionPlan:
        """Verify executed actions by reading back from target system.

        verify_fn(action) should return:
            (VerificationResult, details_message: str)
        """
        plan = self._get_plan(plan_id)
        plan.phase = ExecutionPhase.VERIFYING

        all_confirmed = True
        for action in plan.actions:
            if action.phase != ExecutionPhase.EXECUTED:
                continue

            action.phase = ExecutionPhase.VERIFYING
            result, details = verify_fn(action)
            action.verification_result = result
            action.verification_details = details
            action.verified_at = datetime.utcnow()

            if result == VerificationResult.CONFIRMED:
                action.phase = ExecutionPhase.VERIFIED
            else:
                action.phase = ExecutionPhase.FAILED
                all_confirmed = False
                logger.warning(
                    f"Verification failed for {action.action_id}: {result.value} — {details}"
                )

        plan.phase = ExecutionPhase.VERIFIED if all_confirmed else ExecutionPhase.FAILED
        plan.verified_at = datetime.utcnow()
        return plan

    # ------------------------------------------------------------------
    # Post-execution risk update
    # ------------------------------------------------------------------

    def update_post_risk(
        self,
        plan_id: str,
        post_risk_score: float,
        post_violation_count: int,
    ) -> ExecutionPlan:
        """Update the plan with post-execution risk metrics."""
        plan = self._get_plan(plan_id)
        plan.post_risk_score = post_risk_score
        plan.post_violation_count = post_violation_count
        return plan

    def close(self, plan_id: str) -> ExecutionPlan:
        """Mark plan as closed/complete."""
        plan = self._get_plan(plan_id)
        plan.closed_at = datetime.utcnow()
        self._update_plan_in_db(plan)
        return plan

    # ------------------------------------------------------------------
    # Rollback
    # ------------------------------------------------------------------

    def create_rollback_plan(self, plan_id: str) -> ExecutionPlan:
        """Create a new plan that reverses all executed actions."""
        original = self._get_plan(plan_id)

        rollback_actions = []
        for action in reversed(original.actions):
            if action.phase not in (ExecutionPhase.EXECUTED, ExecutionPhase.VERIFIED):
                continue

            reverse_type = {
                ActionType.ASSIGN_ROLE: ActionType.REMOVE_ROLE,
                ActionType.REMOVE_ROLE: ActionType.ASSIGN_ROLE,
                ActionType.LOCK_USER: ActionType.UNLOCK_USER,
                ActionType.UNLOCK_USER: ActionType.LOCK_USER,
            }.get(action.action_type)

            if not reverse_type:
                logger.warning(f"Cannot auto-rollback action type {action.action_type}")
                continue

            rollback = ExecutionAction(
                action_id=_make_id("RB", action.action_id),
                action_type=reverse_type,
                target_system=action.target_system,
                target_client=action.target_client,
                user_id=action.user_id,
                role_id=action.role_id,
                parameters=action.parameters,
                rollback_action_id=action.action_id,
            )
            rollback_actions.append(rollback)

        rb_plan_id = _make_id("RBPLAN", plan_id)
        rollback_plan = ExecutionPlan(
            plan_id=rb_plan_id,
            request_id=f"RB-{original.request_id}",
            workflow_id=original.workflow_id,
            user_id=original.user_id,
            tenant_id=original.tenant_id,
            actions=rollback_actions,
            execution_mode="rollback",
        )

        self._plans[rb_plan_id] = rollback_plan
        return rollback_plan

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def get_plan(self, plan_id: str) -> Optional[ExecutionPlan]:
        return self._plans.get(plan_id)

    def get_plans_for_user(self, user_id: str) -> list[ExecutionPlan]:
        return [p for p in self._plans.values() if p.user_id == user_id]

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _get_plan(self, plan_id: str) -> ExecutionPlan:
        plan = self._plans.get(plan_id)
        if not plan:
            raise ValueError(f"Execution plan {plan_id} not found")
        return plan


    def _persist_plan(self, plan: ExecutionPlan) -> None:
        """Write-through: persist execution plan to database."""
        try:
            from db.database import db_manager
            from db.models.engines import ExecutionPlanRecord

            with db_manager.session_scope() as session:
                row = ExecutionPlanRecord(
                    plan_id=plan.plan_id,
                    request_id=plan.request_id,
                    workflow_id=plan.workflow_id,
                    user_id=plan.user_id,
                    tenant_id=plan.tenant_id,
                    phase=plan.phase.value,
                    execution_mode=plan.execution_mode,
                    pre_risk_score=plan.pre_risk_score,
                    pre_violation_count=plan.pre_violation_count,
                    actions=[
                        {"action_id": a.action_id, "action_type": a.action_type.value,
                         "target_system": a.target_system, "user_id": a.user_id,
                         "role_id": a.role_id, "phase": a.phase.value}
                        for a in plan.actions
                    ],
                )
                session.add(row)
        except Exception as exc:
            logger.warning(f"ExecutionPlan DB persist failed: {exc}")

    def _update_plan_in_db(self, plan: ExecutionPlan) -> None:
        """Update existing plan record in database."""
        try:
            from db.database import db_manager
            from db.models.engines import ExecutionPlanRecord

            with db_manager.session_scope() as session:
                row = session.query(ExecutionPlanRecord).filter_by(
                    plan_id=plan.plan_id
                ).first()
                if row:
                    row.phase = plan.phase.value if hasattr(plan.phase, 'value') else str(plan.phase)
                    row.executed_by = plan.executed_by
                    row.executed_at = plan.executed_at
                    row.verified_at = plan.verified_at
                    row.closed_at = plan.closed_at
                    row.post_risk_score = plan.post_risk_score
                    row.post_violation_count = plan.post_violation_count
        except Exception as exc:
            logger.warning(f"ExecutionPlan DB update failed: {exc}")


def _make_id(*parts: str) -> str:
    raw = ":".join(parts)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]
