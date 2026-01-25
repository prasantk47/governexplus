# Approver Determination Engine
# Dynamic, context-driven approver selection

"""
Approver Determination Engine for GOVERNEX+.

Multi-layer determination:
- Layer 1: Mandatory approvers (hard rules)
- Layer 2: Risk-based dynamic approvers
- Layer 3: Contextual overrides
- Layer 4: AI optimization (optional)
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from enum import Enum
import logging

from .models import (
    ApprovalContext, ApprovalRequest, Approver, ApprovalRoute,
    ApproverType, ApprovalStatus, ApprovalPriority, AccessType
)
from .rules import RuleEngine, ApproverSpec, RuleLayer, BUILTIN_RULES

logger = logging.getLogger(__name__)


@dataclass
class ApproverSelection:
    """
    A selected approver with explanation.

    Why was this approver chosen?
    """
    approver: Approver
    rule_id: str
    layer: RuleLayer
    reason: str
    is_required: bool = True
    can_delegate: bool = True
    sla_hours: float = 24.0

    # Optimization data
    ai_confidence: float = 0.0
    ai_recommendation_reason: str = ""
    alternatives: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "approver": self.approver.to_dict(),
            "rule_id": self.rule_id,
            "layer": self.layer.value,
            "reason": self.reason,
            "is_required": self.is_required,
            "sla_hours": self.sla_hours,
            "ai_confidence": round(self.ai_confidence, 2) if self.ai_confidence else None,
            "alternatives": self.alternatives,
        }


@dataclass
class DeterminationResult:
    """
    Complete result of approver determination.

    Includes all approvers, explanations, and routing.
    """
    request_id: str
    determined_at: datetime = field(default_factory=datetime.now)

    # Selections by layer
    mandatory_approvers: List[ApproverSelection] = field(default_factory=list)
    risk_based_approvers: List[ApproverSelection] = field(default_factory=list)
    contextual_approvers: List[ApproverSelection] = field(default_factory=list)

    # All approvers in order
    all_approvers: List[ApproverSelection] = field(default_factory=list)

    # Routing
    stages: List[List[ApproverSelection]] = field(default_factory=list)
    total_sla_hours: float = 0.0

    # Special cases
    is_auto_approved: bool = False
    auto_approval_reason: str = ""

    # Rules matched
    rules_matched: List[str] = field(default_factory=list)
    rules_evaluated: int = 0

    # Explanation
    summary: str = ""
    detailed_explanation: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "determined_at": self.determined_at.isoformat(),
            "mandatory_approvers": [a.to_dict() for a in self.mandatory_approvers],
            "risk_based_approvers": [a.to_dict() for a in self.risk_based_approvers],
            "contextual_approvers": [a.to_dict() for a in self.contextual_approvers],
            "total_approvers": len(self.all_approvers),
            "stages": [
                [a.to_dict() for a in stage]
                for stage in self.stages
            ],
            "total_sla_hours": self.total_sla_hours,
            "is_auto_approved": self.is_auto_approved,
            "auto_approval_reason": self.auto_approval_reason,
            "rules_matched": self.rules_matched,
            "summary": self.summary,
        }


class ApproverDeterminationEngine:
    """
    Determines approvers based on context.

    Key capabilities:
    - Layer-based evaluation
    - Risk-adaptive routing
    - Contextual overrides
    - AI optimization (optional)
    - Full explainability
    """

    def __init__(self, rule_engine: Optional[RuleEngine] = None):
        """Initialize engine."""
        self.rule_engine = rule_engine or RuleEngine()

        # Load built-in rules if no rules provided
        if not self.rule_engine.ruleset.rules:
            for rule in BUILTIN_RULES:
                self.rule_engine.ruleset.add_rule(rule)

        # Approver registry (maps types to actual approvers)
        self._approver_registry: Dict[str, Approver] = {}

        # Configuration
        self._config = {
            "enable_auto_approval": True,
            "auto_approval_max_risk": 20,
            "enable_ai_optimization": True,
            "default_sla_hours": 24,
        }

    def register_approver(
        self,
        approver_id: str,
        approver_name: str,
        approver_type: ApproverType,
        process_scope: Optional[List[str]] = None,
        system_scope: Optional[List[str]] = None,
        email: str = ""
    ) -> Approver:
        """Register an approver in the system."""
        approver = Approver(
            approver_id=approver_id,
            approver_name=approver_name,
            approver_type=approver_type,
            process_scope=process_scope or [],
            system_scope=system_scope or [],
            email=email,
        )
        self._approver_registry[approver_id] = approver
        return approver

    def determine(
        self,
        request: ApprovalRequest
    ) -> DeterminationResult:
        """
        Determine approvers for a request.

        Main entry point for approver determination.
        """
        result = DeterminationResult(
            request_id=request.request_id,
        )

        context = request.context

        # Step 1: Evaluate all rules
        applicable_rules = self.rule_engine.get_applicable_rules(context)
        result.rules_evaluated = len(self.rule_engine.ruleset.rules)
        result.rules_matched = [r.rule_id for r in applicable_rules]

        # Step 2: Check for auto-approval
        if self._check_auto_approval(context, applicable_rules):
            result.is_auto_approved = True
            result.auto_approval_reason = self._get_auto_approval_reason(context)
            result.summary = f"Request auto-approved: {result.auto_approval_reason}"
            return result

        # Step 3: Collect approvers by layer
        # Layer 1: Mandatory
        mandatory_rules = [r for r in applicable_rules if r.layer == RuleLayer.MANDATORY]
        for rule in mandatory_rules:
            for spec in rule.approvers:
                approver = self._resolve_approver(spec, context)
                if approver:
                    result.mandatory_approvers.append(ApproverSelection(
                        approver=approver,
                        rule_id=rule.rule_id,
                        layer=RuleLayer.MANDATORY,
                        reason=rule.explanation,
                        is_required=spec.required,
                        sla_hours=rule.sla_hours,
                    ))

        # Layer 2: Risk-based
        risk_rules = [r for r in applicable_rules if r.layer == RuleLayer.RISK_ADAPTIVE]
        for rule in risk_rules:
            if rule.auto_approve_if_low_risk:
                continue  # Handled in auto-approval check

            for spec in rule.approvers:
                approver = self._resolve_approver(spec, context)
                if approver:
                    result.risk_based_approvers.append(ApproverSelection(
                        approver=approver,
                        rule_id=rule.rule_id,
                        layer=RuleLayer.RISK_ADAPTIVE,
                        reason=rule.explanation,
                        is_required=spec.required,
                        sla_hours=rule.sla_hours,
                    ))

        # Layer 3: Contextual overrides
        contextual_approvers = self._apply_contextual_overrides(context)
        result.contextual_approvers = contextual_approvers

        # Step 4: Combine all approvers
        result.all_approvers = (
            result.mandatory_approvers +
            result.risk_based_approvers +
            result.contextual_approvers
        )

        # Step 5: Organize into stages
        result.stages = self._organize_stages(result.all_approvers)

        # Step 6: Calculate total SLA
        result.total_sla_hours = sum(
            a.sla_hours for a in result.all_approvers
        )

        # Step 7: Generate summary
        result.summary = self._generate_summary(result, context)
        result.detailed_explanation = self._generate_detailed_explanation(result, context)

        return result

    def _check_auto_approval(
        self,
        context: ApprovalContext,
        applicable_rules: List
    ) -> bool:
        """Check if request qualifies for auto-approval."""
        if not self._config["enable_auto_approval"]:
            return False

        # Check risk score threshold
        if context.risk.risk_score > self._config["auto_approval_max_risk"]:
            return False

        # Check for SoD conflicts
        if context.risk.sod_conflict_count > 0:
            return False

        # Check for toxic role
        if context.risk.toxic_role_involved:
            return False

        # Check for auto-approval rules
        for rule in applicable_rules:
            if rule.auto_approve_if_low_risk and rule.evaluate(context):
                return True

        # Check if any mandatory rules require approvers
        mandatory_rules = [r for r in applicable_rules if r.layer == RuleLayer.MANDATORY]
        if mandatory_rules:
            return False

        return context.risk.risk_score <= self._config["auto_approval_max_risk"]

    def _get_auto_approval_reason(self, context: ApprovalContext) -> str:
        """Get reason for auto-approval."""
        reasons = []

        if context.risk.risk_score <= 20:
            reasons.append(f"Low risk score ({context.risk.risk_score:.0f})")

        if context.risk.sod_conflict_count == 0:
            reasons.append("No SoD conflicts")

        if context.request.is_temporary:
            reasons.append("Temporary access")

        return "; ".join(reasons) if reasons else "Meets auto-approval criteria"

    def _resolve_approver(
        self,
        spec: ApproverSpec,
        context: ApprovalContext
    ) -> Optional[Approver]:
        """
        Resolve approver specification to actual approver.

        Finds the right person based on type, process, system.
        """
        # If specific ID provided, use it
        if spec.specific_id and spec.specific_id in self._approver_registry:
            return self._approver_registry[spec.specific_id]

        # Find by type and scope
        for approver in self._approver_registry.values():
            if approver.approver_type != spec.approver_type:
                continue

            # Check process scope
            if spec.process and approver.process_scope:
                if spec.process not in approver.process_scope:
                    continue

            # Check system scope
            if spec.system and approver.system_scope:
                if spec.system not in approver.system_scope:
                    continue

            # Check availability
            if not approver.is_available:
                continue

            return approver

        # Create placeholder if not found
        return Approver(
            approver_id=f"PENDING_{spec.approver_type.value}",
            approver_name=f"Pending {spec.approver_type.value}",
            approver_type=spec.approver_type,
        )

    def _apply_contextual_overrides(
        self,
        context: ApprovalContext
    ) -> List[ApproverSelection]:
        """
        Apply contextual overrides based on special conditions.

        Examples:
        - After-hours request → Add Security as observer
        - Temporary access → May skip Role Owner
        - Firefighter → Mandatory Supervisor + Post-review
        """
        overrides = []

        # After-hours access
        if not context.request.is_business_hours:
            security = self._find_approver_by_type(ApproverType.SECURITY_OFFICER)
            if security:
                overrides.append(ApproverSelection(
                    approver=security,
                    rule_id="CONTEXTUAL-AFTER-HOURS",
                    layer=RuleLayer.OPTIMIZATION,
                    reason="After-hours request requires security awareness",
                    is_required=False,  # Observer, not blocker
                    sla_hours=4,
                ))

        # Firefighter access
        if context.request.access_type == AccessType.FIREFIGHTER:
            # Add manager as mandatory reviewer
            manager = self._find_approver_by_type(ApproverType.LINE_MANAGER)
            if manager:
                overrides.append(ApproverSelection(
                    approver=manager,
                    rule_id="CONTEXTUAL-FIREFIGHTER",
                    layer=RuleLayer.MANDATORY,
                    reason="Firefighter access requires supervisor approval",
                    is_required=True,
                    sla_hours=2,
                ))

        # Emergency access
        if context.request.access_type == AccessType.EMERGENCY:
            # Compressed SLA, but still need approval
            security = self._find_approver_by_type(ApproverType.SECURITY_OFFICER)
            if security:
                overrides.append(ApproverSelection(
                    approver=security,
                    rule_id="CONTEXTUAL-EMERGENCY",
                    layer=RuleLayer.MANDATORY,
                    reason="Emergency access with compressed SLA",
                    is_required=True,
                    sla_hours=1,  # 1 hour SLA for emergency
                ))

        # Vendor/contractor access
        if context.user.employment_type in ["CONTRACTOR", "VENDOR"]:
            # Additional oversight required
            compliance = self._find_approver_by_type(ApproverType.COMPLIANCE_OFFICER)
            if compliance:
                overrides.append(ApproverSelection(
                    approver=compliance,
                    rule_id="CONTEXTUAL-CONTRACTOR",
                    layer=RuleLayer.RISK_ADAPTIVE,
                    reason="External party access requires compliance review",
                    is_required=True,
                    sla_hours=24,
                ))

        return overrides

    def _find_approver_by_type(
        self,
        approver_type: ApproverType
    ) -> Optional[Approver]:
        """Find an available approver by type."""
        for approver in self._approver_registry.values():
            if approver.approver_type == approver_type and approver.is_available:
                return approver
        return None

    def _organize_stages(
        self,
        approvers: List[ApproverSelection]
    ) -> List[List[ApproverSelection]]:
        """
        Organize approvers into stages.

        Mandatory first, then parallel risk-based, then contextual.
        """
        stages = []

        # Stage 1: All mandatory approvers (can be parallel)
        mandatory = [a for a in approvers if a.layer == RuleLayer.MANDATORY]
        if mandatory:
            stages.append(mandatory)

        # Stage 2: Risk-based approvers (parallel)
        risk_based = [a for a in approvers if a.layer == RuleLayer.RISK_ADAPTIVE]
        if risk_based:
            stages.append(risk_based)

        # Stage 3: Optimization/contextual (parallel)
        contextual = [a for a in approvers if a.layer == RuleLayer.OPTIMIZATION]
        if contextual:
            stages.append(contextual)

        return stages

    def _generate_summary(
        self,
        result: DeterminationResult,
        context: ApprovalContext
    ) -> str:
        """Generate human-readable summary."""
        if result.is_auto_approved:
            return f"Auto-approved: {result.auto_approval_reason}"

        approver_count = len(result.all_approvers)
        stage_count = len(result.stages)

        parts = [
            f"{approver_count} approver(s) required",
            f"in {stage_count} stage(s)",
        ]

        if result.total_sla_hours:
            parts.append(f"Total SLA: {result.total_sla_hours:.0f} hours")

        if context.risk.risk_score >= 70:
            parts.append("High-risk request")

        return " | ".join(parts)

    def _generate_detailed_explanation(
        self,
        result: DeterminationResult,
        context: ApprovalContext
    ) -> List[str]:
        """Generate detailed explanation for auditors."""
        explanations = []

        explanations.append(f"Risk score: {context.risk.risk_score:.0f}")
        explanations.append(f"System: {context.request.system_criticality.value}")

        if context.risk.sod_conflict_count > 0:
            explanations.append(f"SoD conflicts: {context.risk.sod_conflict_count}")

        for approver in result.mandatory_approvers:
            explanations.append(
                f"[MANDATORY] {approver.approver.approver_name}: {approver.reason}"
            )

        for approver in result.risk_based_approvers:
            explanations.append(
                f"[RISK-BASED] {approver.approver.approver_name}: {approver.reason}"
            )

        for approver in result.contextual_approvers:
            explanations.append(
                f"[CONTEXTUAL] {approver.approver.approver_name}: {approver.reason}"
            )

        return explanations

    def create_route(
        self,
        request: ApprovalRequest,
        result: DeterminationResult
    ) -> ApprovalRoute:
        """Create approval route from determination result."""
        route = ApprovalRoute(
            route_id=f"ROUTE-{request.request_id}",
            request_id=request.request_id,
            total_sla_hours=result.total_sla_hours,
            determination_rule_id=",".join(result.rules_matched),
            determination_reason=result.summary,
        )

        # Convert selections to approvers
        for stage in result.stages:
            stage_approvers = [s.approver for s in stage]
            route.stages.append(stage_approvers)

        if result.is_auto_approved:
            route.is_auto_approved = True
            route.auto_approval_reason = result.auto_approval_reason
            route.overall_status = ApprovalStatus.AUTO_APPROVED

        # Calculate due date
        if route.total_sla_hours > 0:
            route.due_at = datetime.now() + timedelta(hours=route.total_sla_hours)

        return route

    def simulate(
        self,
        context: ApprovalContext,
        what_if: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Simulate determination with what-if analysis.

        Examples:
        - What if risk was lower?
        - What if this was temporary?
        - What if in DEV instead of PROD?
        """
        # Create mock request
        request = ApprovalRequest(
            request_id="SIMULATION",
            context=context,
        )

        # Apply what-if changes
        if what_if:
            if "risk_score" in what_if:
                context.risk.risk_score = what_if["risk_score"]
            if "system_criticality" in what_if:
                from .models import SystemCriticality
                context.request.system_criticality = SystemCriticality(what_if["system_criticality"])
            if "is_temporary" in what_if:
                context.request.is_temporary = what_if["is_temporary"]

        # Run determination
        result = self.determine(request)

        return {
            "what_if": what_if or {},
            "result": result.to_dict(),
            "is_auto_approved": result.is_auto_approved,
            "approver_count": len(result.all_approvers),
            "total_sla_hours": result.total_sla_hours,
        }
