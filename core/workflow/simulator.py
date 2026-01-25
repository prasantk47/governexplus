# Workflow Simulator
# Real-time preview of workflow behavior

"""
Workflow Simulator for GOVERNEX+.

This powers the "What happens if..." panel in the UI.
Customers can:
1. See how their workflow will behave
2. Test edge cases before going live
3. Understand the impact of their choices

Key Features:
- Scenario simulation
- Outcome prediction
- Audit preview
- Risk impact analysis
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from enum import Enum
import random

from .builder import (
    WorkflowCanvas, BlockType, TriggerBlock, ConditionBlock,
    ApprovalBlock, ApprovalGroupBlock, ProvisioningGateBlock,
    ActionBlock, SplitBlock, ProvisioningMode
)


# ============================================================
# SIMULATION SCENARIOS
# ============================================================

@dataclass
class SimulationScenario:
    """A test scenario for simulation."""
    scenario_id: str = ""
    name: str = ""
    description: str = ""

    # Request data
    num_items: int = 1
    items: List[Dict[str, Any]] = field(default_factory=list)

    # Context overrides
    risk_scores: List[int] = field(default_factory=list)
    systems: List[str] = field(default_factory=list)
    user_type: str = "EMPLOYEE"
    is_emergency: bool = False
    is_temporary: bool = False

    # Approval simulation
    approval_outcomes: Dict[str, str] = field(default_factory=dict)  # step_id -> APPROVED/REJECTED
    approval_delays_hours: Dict[str, int] = field(default_factory=dict)  # step_id -> hours

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "name": self.name,
            "description": self.description,
            "items": self.items or [{"risk": r} for r in self.risk_scores],
            "context": {
                "user_type": self.user_type,
                "is_emergency": self.is_emergency,
                "is_temporary": self.is_temporary,
            },
            "approvals": self.approval_outcomes,
        }


@dataclass
class SimulationOutcome:
    """Predicted outcome of a scenario."""
    scenario_id: str = ""

    # Timeline
    events: List[Dict[str, Any]] = field(default_factory=list)
    total_duration_hours: float = 0

    # Final state
    request_status: str = ""  # APPROVED, REJECTED, PARTIAL
    items_provisioned: int = 0
    items_rejected: int = 0
    items_pending: int = 0

    # Actions taken
    notifications_sent: List[str] = field(default_factory=list)
    escalations_triggered: List[str] = field(default_factory=list)

    # Audit preview
    audit_trail: List[str] = field(default_factory=list)

    # Impact analysis
    risk_impact: Dict[str, Any] = field(default_factory=dict)
    sla_impact: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "timeline": self.events,
            "duration_hours": self.total_duration_hours,
            "outcome": {
                "status": self.request_status,
                "provisioned": self.items_provisioned,
                "rejected": self.items_rejected,
                "pending": self.items_pending,
            },
            "notifications": self.notifications_sent,
            "escalations": self.escalations_triggered,
            "audit_trail": self.audit_trail,
            "impact": {
                "risk": self.risk_impact,
                "sla": self.sla_impact,
            }
        }

    def to_human_readable(self) -> str:
        """Generate human-readable summary."""
        lines = []
        lines.append("=" * 50)
        lines.append("📋 SIMULATION RESULT")
        lines.append("=" * 50)
        lines.append("")

        # Timeline
        lines.append("⏱️ TIMELINE:")
        for event in self.events:
            time_str = event.get("time", "T+0h")
            action = event.get("action", "")
            detail = event.get("detail", "")
            lines.append(f"   {time_str}: {action} - {detail}")
        lines.append("")

        # Outcome
        lines.append("📊 OUTCOME:")
        lines.append(f"   Status: {self.request_status}")
        lines.append(f"   Items Provisioned: {self.items_provisioned}")
        lines.append(f"   Items Rejected: {self.items_rejected}")
        lines.append(f"   Items Pending: {self.items_pending}")
        lines.append(f"   Total Duration: {self.total_duration_hours:.1f} hours")
        lines.append("")

        # Audit preview
        if self.audit_trail:
            lines.append("📝 AUDIT TRAIL PREVIEW:")
            for entry in self.audit_trail[:5]:
                lines.append(f"   • {entry}")
        lines.append("")

        # Impact
        if self.risk_impact:
            lines.append("⚠️ RISK IMPACT:")
            for key, value in self.risk_impact.items():
                lines.append(f"   • {key}: {value}")

        lines.append("=" * 50)
        return "\n".join(lines)


# ============================================================
# WORKFLOW SIMULATOR
# ============================================================

class WorkflowSimulator:
    """
    Simulates workflow execution without actually running it.

    This is the engine behind the preview panel.
    """

    def __init__(self):
        self._predefined_scenarios = self._create_predefined_scenarios()

    def _create_predefined_scenarios(self) -> List[SimulationScenario]:
        """Create predefined test scenarios."""
        return [
            SimulationScenario(
                scenario_id="SINGLE_LOW_RISK",
                name="Single Low-Risk Request",
                description="One role, risk score 25, all approvers approve",
                num_items=1,
                risk_scores=[25],
                approval_outcomes={"*": "APPROVED"},
            ),
            SimulationScenario(
                scenario_id="SINGLE_HIGH_RISK",
                name="Single High-Risk Request",
                description="One role, risk score 85, security reviews",
                num_items=1,
                risk_scores=[85],
                approval_outcomes={"*": "APPROVED"},
            ),
            SimulationScenario(
                scenario_id="MULTI_MIXED_APPROVED",
                name="Multiple Roles - All Approved",
                description="3 roles with different risks, all approved",
                num_items=3,
                risk_scores=[25, 55, 80],
                approval_outcomes={"*": "APPROVED"},
            ),
            SimulationScenario(
                scenario_id="MULTI_MIXED_PARTIAL",
                name="Multiple Roles - Partial Approval",
                description="3 roles, 2 approved, 1 rejected",
                num_items=3,
                risk_scores=[25, 55, 80],
                approval_outcomes={"ITEM_1": "APPROVED", "ITEM_2": "APPROVED", "ITEM_3": "REJECTED"},
            ),
            SimulationScenario(
                scenario_id="SLA_BREACH",
                name="SLA Breach Scenario",
                description="Approval takes too long, escalation triggered",
                num_items=1,
                risk_scores=[50],
                approval_delays_hours={"MANAGER": 72},
                approval_outcomes={"*": "APPROVED"},
            ),
            SimulationScenario(
                scenario_id="EMERGENCY",
                name="Emergency Access",
                description="Emergency request with expedited approval",
                num_items=1,
                risk_scores=[60],
                is_emergency=True,
                approval_outcomes={"*": "APPROVED"},
            ),
            SimulationScenario(
                scenario_id="VENDOR_ACCESS",
                name="Vendor Access Request",
                description="External vendor requesting access",
                num_items=2,
                risk_scores=[40, 70],
                user_type="VENDOR",
                approval_outcomes={"*": "APPROVED"},
            ),
        ]

    def get_predefined_scenarios(self) -> List[Dict[str, Any]]:
        """Get list of predefined scenarios for UI."""
        return [s.to_dict() for s in self._predefined_scenarios]

    def simulate(
        self,
        canvas: WorkflowCanvas,
        scenario: SimulationScenario
    ) -> SimulationOutcome:
        """
        Simulate workflow execution for a given scenario.

        Returns predicted outcome.
        """
        outcome = SimulationOutcome(scenario_id=scenario.scenario_id)
        current_time = 0  # hours from start

        # Step 1: Log submission
        outcome.events.append({
            "time": "T+0h",
            "action": "REQUEST_SUBMITTED",
            "detail": f"{scenario.num_items} item(s) submitted for approval",
        })
        outcome.audit_trail.append(f"Request submitted with {scenario.num_items} access item(s)")

        # Step 2: Evaluate conditions
        conditions = [b for b in canvas.blocks if b.block_type == BlockType.CONDITION]
        for i, risk in enumerate(scenario.risk_scores):
            for cond in conditions:
                if isinstance(cond, ConditionBlock):
                    passed = self._evaluate_condition(cond, risk, scenario)
                    outcome.events.append({
                        "time": f"T+{current_time}h",
                        "action": "CONDITION_EVALUATED",
                        "detail": f"Item {i+1}: {cond.to_human_readable()} → {'PASS' if passed else 'FAIL'}",
                    })

        # Step 3: Process approvals
        approvals = [b for b in canvas.blocks if b.block_type in [BlockType.APPROVAL, BlockType.APPROVAL_GROUP]]

        for approval in approvals:
            if isinstance(approval, ApprovalBlock):
                delay = scenario.approval_delays_hours.get(approval.approver_type.value, approval.sla_hours // 2)
                current_time += delay

                # Check SLA
                if delay > approval.sla_hours:
                    outcome.events.append({
                        "time": f"T+{current_time}h",
                        "action": "SLA_BREACH",
                        "detail": f"{approval.name} exceeded SLA of {approval.sla_hours}h",
                    })
                    outcome.escalations_triggered.append(f"Escalation to {approval.escalate_to.value if approval.escalate_to else 'manager'}")
                    outcome.audit_trail.append(f"SLA breach detected for {approval.name}")

                # Determine outcome
                decision = scenario.approval_outcomes.get("*", scenario.approval_outcomes.get(approval.block_id, "APPROVED"))
                outcome.events.append({
                    "time": f"T+{current_time}h",
                    "action": f"APPROVAL_{decision}",
                    "detail": f"{approval.name} {decision.lower()}d the request",
                })
                outcome.audit_trail.append(f"{approval.approver_type.value} {decision.lower()}d")

            elif isinstance(approval, ApprovalGroupBlock):
                for sub_approval in approval.approvals:
                    delay = scenario.approval_delays_hours.get(sub_approval.approver_type.value, sub_approval.sla_hours // 2)
                    if approval.mode == "PARALLEL":
                        # Parallel: max delay
                        pass
                    else:
                        # Sequential: sum delays
                        current_time += delay

        # Step 4: Provisioning gate
        gates = [b for b in canvas.blocks if b.block_type == BlockType.PROVISIONING_GATE]

        for gate in gates:
            if isinstance(gate, ProvisioningGateBlock):
                outcome.events.append({
                    "time": f"T+{current_time}h",
                    "action": "PROVISIONING_GATE",
                    "detail": f"Evaluating: {gate.to_human_readable()}",
                })

                # Simulate provisioning based on mode
                if gate.mode == ProvisioningMode.PER_ITEM:
                    # Each approved item provisioned immediately
                    for i in range(scenario.num_items):
                        item_decision = scenario.approval_outcomes.get(f"ITEM_{i+1}", scenario.approval_outcomes.get("*", "APPROVED"))
                        if item_decision == "APPROVED":
                            outcome.items_provisioned += 1
                            outcome.events.append({
                                "time": f"T+{current_time}h",
                                "action": "ITEM_PROVISIONED",
                                "detail": f"Item {i+1} (risk {scenario.risk_scores[i] if i < len(scenario.risk_scores) else 'N/A'}) provisioned",
                            })
                        else:
                            outcome.items_rejected += 1

                elif gate.mode == ProvisioningMode.ALL_OR_NOTHING:
                    # Check if all approved
                    all_approved = all(
                        scenario.approval_outcomes.get(f"ITEM_{i+1}", scenario.approval_outcomes.get("*", "APPROVED")) == "APPROVED"
                        for i in range(scenario.num_items)
                    )
                    if all_approved:
                        outcome.items_provisioned = scenario.num_items
                        outcome.events.append({
                            "time": f"T+{current_time}h",
                            "action": "ALL_PROVISIONED",
                            "detail": f"All {scenario.num_items} items provisioned together",
                        })
                    else:
                        outcome.events.append({
                            "time": f"T+{current_time}h",
                            "action": "PROVISIONING_BLOCKED",
                            "detail": "Not all items approved, no provisioning (ALL_OR_NOTHING)",
                        })

                elif gate.mode == ProvisioningMode.RISK_BASED:
                    # Provision low-risk first
                    for i, risk in enumerate(scenario.risk_scores):
                        item_decision = scenario.approval_outcomes.get(f"ITEM_{i+1}", scenario.approval_outcomes.get("*", "APPROVED"))
                        if item_decision == "APPROVED":
                            if risk <= gate.risk_threshold:
                                outcome.items_provisioned += 1
                                outcome.events.append({
                                    "time": f"T+{current_time}h",
                                    "action": "LOW_RISK_PROVISIONED",
                                    "detail": f"Item {i+1} (risk {risk} ≤ {gate.risk_threshold}) provisioned immediately",
                                })
                            else:
                                outcome.events.append({
                                    "time": f"T+{current_time}h",
                                    "action": "HIGH_RISK_HELD",
                                    "detail": f"Item {i+1} (risk {risk} > {gate.risk_threshold}) held for additional review",
                                })
                                outcome.items_pending += 1

        # Step 5: Actions
        actions = [b for b in canvas.blocks if b.block_type == BlockType.ACTION]
        for action in actions:
            if isinstance(action, ActionBlock):
                outcome.notifications_sent.append(action.to_human_readable())
                outcome.events.append({
                    "time": f"T+{current_time}h",
                    "action": action.action_type.value,
                    "detail": action.to_human_readable(),
                })

        # Final status
        outcome.total_duration_hours = current_time
        if outcome.items_rejected == scenario.num_items:
            outcome.request_status = "REJECTED"
        elif outcome.items_provisioned == scenario.num_items:
            outcome.request_status = "APPROVED"
        elif outcome.items_provisioned > 0:
            outcome.request_status = "PARTIAL"
        else:
            outcome.request_status = "PENDING"

        # Risk impact
        outcome.risk_impact = {
            "total_risk_score": sum(scenario.risk_scores),
            "average_risk": sum(scenario.risk_scores) / len(scenario.risk_scores) if scenario.risk_scores else 0,
            "high_risk_items": len([r for r in scenario.risk_scores if r > 70]),
        }

        # SLA impact
        outcome.sla_impact = {
            "expected_duration_hours": current_time,
            "breaches_predicted": len(outcome.escalations_triggered),
        }

        return outcome

    def _evaluate_condition(
        self,
        condition: ConditionBlock,
        risk_score: int,
        scenario: SimulationScenario
    ) -> bool:
        """Evaluate a condition against scenario data."""
        from .builder import ConditionAttribute, ConditionOperator

        value = None
        if condition.attribute == ConditionAttribute.RISK_SCORE:
            value = risk_score
        elif condition.attribute == ConditionAttribute.USER_TYPE:
            value = scenario.user_type
        elif condition.attribute == ConditionAttribute.IS_EMERGENCY:
            value = scenario.is_emergency
        elif condition.attribute == ConditionAttribute.IS_TEMPORARY:
            value = scenario.is_temporary

        if value is None:
            return True  # Default pass if can't evaluate

        if condition.operator == ConditionOperator.GREATER_THAN:
            return value > condition.value
        elif condition.operator == ConditionOperator.LESS_THAN:
            return value < condition.value
        elif condition.operator == ConditionOperator.EQUALS:
            return value == condition.value
        elif condition.operator == ConditionOperator.GREATER_OR_EQUAL:
            return value >= condition.value
        elif condition.operator == ConditionOperator.LESS_OR_EQUAL:
            return value <= condition.value
        elif condition.operator == ConditionOperator.IS_TRUE:
            return bool(value)
        elif condition.operator == ConditionOperator.IS_FALSE:
            return not bool(value)

        return True

    def compare_scenarios(
        self,
        canvas: WorkflowCanvas,
        scenarios: List[SimulationScenario]
    ) -> Dict[str, Any]:
        """
        Compare outcomes across multiple scenarios.

        Useful for impact analysis.
        """
        results = []
        for scenario in scenarios:
            outcome = self.simulate(canvas, scenario)
            results.append({
                "scenario": scenario.name,
                "outcome": outcome.request_status,
                "provisioned": outcome.items_provisioned,
                "duration": outcome.total_duration_hours,
                "escalations": len(outcome.escalations_triggered),
            })

        return {
            "comparison": results,
            "summary": {
                "scenarios_tested": len(scenarios),
                "success_rate": len([r for r in results if r["outcome"] != "REJECTED"]) / len(results) if results else 0,
                "avg_duration": sum(r["duration"] for r in results) / len(results) if results else 0,
            }
        }

    def generate_what_if_analysis(
        self,
        canvas: WorkflowCanvas,
        base_scenario: SimulationScenario
    ) -> Dict[str, Any]:
        """
        Generate "what if" analysis showing different outcomes.

        Shows customer how different inputs affect results.
        """
        analyses = []

        # What if: All approved
        scenario_all_approved = SimulationScenario(
            scenario_id="WHAT_IF_ALL_APPROVED",
            name="What if all items are approved?",
            num_items=base_scenario.num_items,
            risk_scores=base_scenario.risk_scores,
            approval_outcomes={"*": "APPROVED"},
        )
        outcome_all = self.simulate(canvas, scenario_all_approved)
        analyses.append({
            "question": "What if all items are approved?",
            "answer": f"{outcome_all.items_provisioned} items provisioned in {outcome_all.total_duration_hours:.0f}h",
            "outcome": outcome_all.to_dict(),
        })

        # What if: One rejected
        if base_scenario.num_items > 1:
            scenario_one_rejected = SimulationScenario(
                scenario_id="WHAT_IF_ONE_REJECTED",
                name="What if one item is rejected?",
                num_items=base_scenario.num_items,
                risk_scores=base_scenario.risk_scores,
                approval_outcomes={"ITEM_1": "APPROVED", "ITEM_2": "REJECTED", "*": "APPROVED"},
            )
            outcome_partial = self.simulate(canvas, scenario_one_rejected)
            analyses.append({
                "question": "What if one item is rejected?",
                "answer": f"{outcome_partial.items_provisioned} items provisioned, {outcome_partial.items_rejected} rejected",
                "outcome": outcome_partial.to_dict(),
            })

        # What if: SLA breach
        scenario_sla = SimulationScenario(
            scenario_id="WHAT_IF_SLA_BREACH",
            name="What if approver doesn't respond in time?",
            num_items=base_scenario.num_items,
            risk_scores=base_scenario.risk_scores,
            approval_delays_hours={"LINE_MANAGER": 96, "SECURITY_OFFICER": 96},
            approval_outcomes={"*": "APPROVED"},
        )
        outcome_sla = self.simulate(canvas, scenario_sla)
        analyses.append({
            "question": "What if approver doesn't respond in time?",
            "answer": f"{len(outcome_sla.escalations_triggered)} escalation(s) triggered",
            "outcome": outcome_sla.to_dict(),
        })

        # What if: Higher risk
        if base_scenario.risk_scores:
            high_risk_scores = [min(r + 30, 100) for r in base_scenario.risk_scores]
            scenario_high_risk = SimulationScenario(
                scenario_id="WHAT_IF_HIGH_RISK",
                name="What if risk scores are higher?",
                num_items=base_scenario.num_items,
                risk_scores=high_risk_scores,
                approval_outcomes={"*": "APPROVED"},
            )
            outcome_high = self.simulate(canvas, scenario_high_risk)
            analyses.append({
                "question": f"What if risk scores increase to {high_risk_scores}?",
                "answer": f"{outcome_high.items_provisioned} items provisioned, {outcome_high.items_pending} held for review",
                "outcome": outcome_high.to_dict(),
            })

        return {
            "base_scenario": base_scenario.to_dict(),
            "what_if_analyses": analyses,
        }


# ============================================================
# QUICK SIMULATION HELPERS
# ============================================================

def quick_simulate(canvas: WorkflowCanvas, num_items: int = 1, risk: int = 50) -> str:
    """Quick simulation with default scenario."""
    simulator = WorkflowSimulator()
    scenario = SimulationScenario(
        scenario_id="QUICK",
        name="Quick Test",
        num_items=num_items,
        risk_scores=[risk] * num_items,
        approval_outcomes={"*": "APPROVED"},
    )
    outcome = simulator.simulate(canvas, scenario)
    return outcome.to_human_readable()


def test_partial_provisioning(canvas: WorkflowCanvas) -> str:
    """
    Test the exact scenario:
    2 roles → 2 approvers → 1 approved, 1 pending
    """
    simulator = WorkflowSimulator()
    scenario = SimulationScenario(
        scenario_id="PARTIAL_TEST",
        name="Partial Provisioning Test",
        description="2 roles, 2 approvers, 1 approved immediately",
        num_items=2,
        risk_scores=[30, 70],
        approval_outcomes={"ITEM_1": "APPROVED", "ITEM_2": "PENDING"},
    )
    outcome = simulator.simulate(canvas, scenario)
    return outcome.to_human_readable()
