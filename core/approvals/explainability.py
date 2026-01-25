# Approval Explainability Layer
# Clear explanations for requesters, approvers, and auditors

"""
Explainability Engine for GOVERNEX+.

Provides human-readable explanations for:
- Why these approvers? (for requesters)
- Why is this risky? (for approvers)
- How was decision made? (for auditors)
- What-if analysis (for all)
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from enum import Enum
import logging

from .models import (
    ApprovalRequest, ApprovalContext, Approver, ApproverType,
    RiskContext, RequestContext
)
from .rules import ApprovalRule, RuleLayer, RuleCondition, ApprovalRuleEngine

logger = logging.getLogger(__name__)


class Audience(Enum):
    """Target audience for explanation."""
    REQUESTER = "REQUESTER"       # Business user requesting access
    APPROVER = "APPROVER"         # Person approving
    AUDITOR = "AUDITOR"           # Compliance/audit review
    EXECUTIVE = "EXECUTIVE"       # Summary for leadership
    SYSTEM = "SYSTEM"             # Technical/machine-readable


class ExplanationDepth(Enum):
    """Depth of explanation detail."""
    BRIEF = "BRIEF"           # One-liner
    STANDARD = "STANDARD"     # Normal detail
    DETAILED = "DETAILED"     # Full audit trail
    TECHNICAL = "TECHNICAL"   # Rule-level detail


@dataclass
class RuleMatch:
    """A rule that matched during determination."""
    rule_id: str
    rule_name: str
    layer: RuleLayer
    priority: int
    conditions_matched: List[str]
    approvers_added: List[str]
    sla_hours: float
    explanation: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "rule_name": self.rule_name,
            "layer": self.layer.value,
            "priority": self.priority,
            "conditions_matched": self.conditions_matched,
            "approvers_added": self.approvers_added,
            "sla_hours": self.sla_hours,
            "explanation": self.explanation,
        }


@dataclass
class RiskFactor:
    """A factor contributing to risk score."""
    factor_name: str
    contribution: float
    description: str
    value: Any = None
    threshold: Any = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "factor_name": self.factor_name,
            "contribution": round(self.contribution, 1),
            "description": self.description,
            "value": self.value,
            "threshold": self.threshold,
        }


@dataclass
class ApprovalExplanation:
    """
    Complete explanation of approval determination.

    Answers:
    - Why these approvers?
    - Why this risk level?
    - How long will it take?
    - What rules applied?
    """
    request_id: str
    generated_at: datetime = field(default_factory=datetime.now)
    audience: Audience = Audience.STANDARD

    # Summary
    headline: str = ""
    summary: str = ""

    # Approvers
    approver_explanations: List[Dict[str, str]] = field(default_factory=list)

    # Risk
    risk_score: int = 0
    risk_level: str = ""
    risk_factors: List[RiskFactor] = field(default_factory=list)
    risk_summary: str = ""

    # Rules
    rules_matched: List[RuleMatch] = field(default_factory=list)

    # Timeline
    expected_sla_hours: float = 0.0
    timeline_explanation: str = ""

    # What-if
    alternatives: List[Dict[str, Any]] = field(default_factory=list)

    # Audit
    determination_path: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "generated_at": self.generated_at.isoformat(),
            "audience": self.audience.value,
            "headline": self.headline,
            "summary": self.summary,
            "approvers": self.approver_explanations,
            "risk": {
                "score": self.risk_score,
                "level": self.risk_level,
                "factors": [f.to_dict() for f in self.risk_factors],
                "summary": self.risk_summary,
            },
            "rules_matched": [r.to_dict() for r in self.rules_matched],
            "timeline": {
                "expected_hours": self.expected_sla_hours,
                "explanation": self.timeline_explanation,
            },
            "alternatives": self.alternatives,
            "determination_path": self.determination_path,
        }


@dataclass
class WhatIfResult:
    """Result of what-if analysis."""
    scenario: str
    original_approvers: List[str]
    new_approvers: List[str]
    risk_change: int
    sla_change: float
    explanation: str
    recommendation: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scenario": self.scenario,
            "original_approvers": self.original_approvers,
            "new_approvers": self.new_approvers,
            "risk_change": self.risk_change,
            "sla_change": self.sla_change,
            "explanation": self.explanation,
            "recommendation": self.recommendation,
        }


class ExplainabilityEngine:
    """
    Generates human-readable explanations for approval decisions.

    Key principles:
    - Explain in terms users understand
    - Adapt to audience (requester vs auditor)
    - Show counterfactuals (what-if)
    - Full audit trail
    """

    def __init__(self, rule_engine: Optional[ApprovalRuleEngine] = None):
        """Initialize explainability engine."""
        self.rule_engine = rule_engine or ApprovalRuleEngine()

        # Risk level descriptions
        self._risk_levels = {
            (0, 20): ("LOW", "Standard access with minimal oversight needed"),
            (21, 50): ("MEDIUM", "Moderate access requiring management review"),
            (51, 80): ("HIGH", "Sensitive access requiring security approval"),
            (81, 100): ("CRITICAL", "Highly privileged access requiring CISO sign-off"),
        }

        # Approver type descriptions
        self._approver_descriptions = {
            ApproverType.LINE_MANAGER: "your direct manager",
            ApproverType.ROLE_OWNER: "the role owner",
            ApproverType.PROCESS_OWNER: "the business process owner",
            ApproverType.DATA_OWNER: "the data owner",
            ApproverType.SECURITY_OFFICER: "the security team",
            ApproverType.COMPLIANCE_OFFICER: "the compliance team",
            ApproverType.SYSTEM_OWNER: "the system owner",
            ApproverType.CISO: "the Chief Information Security Officer",
            ApproverType.DELEGATE: "the designated delegate",
        }

    def explain(
        self,
        request: ApprovalRequest,
        context: ApprovalContext,
        matched_rules: List[ApprovalRule],
        selected_approvers: List[Approver],
        audience: Audience = Audience.REQUESTER,
        depth: ExplanationDepth = ExplanationDepth.STANDARD
    ) -> ApprovalExplanation:
        """
        Generate explanation for approval determination.

        Args:
            request: The approval request
            context: Full context used for determination
            matched_rules: Rules that matched
            selected_approvers: Approvers selected
            audience: Target audience
            depth: Level of detail

        Returns:
            ApprovalExplanation
        """
        explanation = ApprovalExplanation(
            request_id=request.request_id,
            audience=audience,
            risk_score=context.risk.risk_score if context.risk else 0,
        )

        # Generate headline
        explanation.headline = self._generate_headline(
            request, selected_approvers, context.risk
        )

        # Generate summary based on audience
        explanation.summary = self._generate_summary(
            request, context, selected_approvers, audience
        )

        # Explain each approver
        explanation.approver_explanations = self._explain_approvers(
            selected_approvers, matched_rules, audience
        )

        # Explain risk
        if context.risk:
            explanation.risk_level = self._get_risk_level(context.risk.risk_score)
            explanation.risk_factors = self._explain_risk_factors(context.risk)
            explanation.risk_summary = self._summarize_risk(context.risk, audience)

        # Explain rules (for auditors)
        if depth in [ExplanationDepth.DETAILED, ExplanationDepth.TECHNICAL]:
            explanation.rules_matched = self._explain_rules(matched_rules)

        # Timeline
        explanation.expected_sla_hours = max(
            (r.sla_hours for r in matched_rules),
            default=24.0
        )
        explanation.timeline_explanation = self._explain_timeline(
            explanation.expected_sla_hours, selected_approvers
        )

        # Determination path (for audit)
        explanation.determination_path = self._trace_determination_path(
            context, matched_rules, selected_approvers
        )

        return explanation

    def _generate_headline(
        self,
        request: ApprovalRequest,
        approvers: List[Approver],
        risk: Optional[RiskContext]
    ) -> str:
        """Generate one-line headline."""
        risk_level = self._get_risk_level(risk.risk_score if risk else 0)

        if len(approvers) == 1:
            return f"{risk_level} risk request - requires 1 approval"
        else:
            return f"{risk_level} risk request - requires {len(approvers)} approvals"

    def _generate_summary(
        self,
        request: ApprovalRequest,
        context: ApprovalContext,
        approvers: List[Approver],
        audience: Audience
    ) -> str:
        """Generate summary appropriate for audience."""
        risk_score = context.risk.risk_score if context.risk else 0
        risk_level = self._get_risk_level(risk_score)

        if audience == Audience.REQUESTER:
            # Business-friendly language
            approver_list = ", ".join([
                self._approver_descriptions.get(a.approver_type, a.approver_type.value)
                for a in approvers[:3]
            ])
            if len(approvers) > 3:
                approver_list += f", and {len(approvers) - 3} more"

            return (
                f"Your request for {request.request_type} access to {request.system_id} "
                f"has been classified as {risk_level.lower()} risk (score: {risk_score}/100). "
                f"It needs approval from {approver_list}."
            )

        elif audience == Audience.APPROVER:
            # Focus on what they need to evaluate
            highlights = []
            if risk_score > 50:
                highlights.append(f"elevated risk score ({risk_score})")
            if context.risk and context.risk.sod_conflicts:
                highlights.append(f"{len(context.risk.sod_conflicts)} potential SoD conflicts")
            if context.request and context.request.is_production:
                highlights.append("production system access")

            highlight_text = ", ".join(highlights) if highlights else "standard access request"
            return (
                f"This {risk_level.lower()} risk request involves {highlight_text}. "
                f"Please review the risk factors below before making your decision."
            )

        elif audience == Audience.AUDITOR:
            # Full technical detail
            rule_count = len([r for r in context.request.matched_rules] if context.request else 0)
            return (
                f"Request {request.request_id} determined as {risk_level} risk "
                f"(score: {risk_score}/100). {len(approvers)} approver(s) required. "
                f"Determination based on {rule_count} matched rules across "
                f"{self._count_layers([]) } determination layers."
            )

        else:  # EXECUTIVE
            return (
                f"{risk_level} risk access request requiring {len(approvers)} approval(s). "
                f"Risk score: {risk_score}/100."
            )

    def _explain_approvers(
        self,
        approvers: List[Approver],
        rules: List[ApprovalRule],
        audience: Audience
    ) -> List[Dict[str, str]]:
        """Explain why each approver is needed."""
        explanations = []

        for approver in approvers:
            # Find the rule that added this approver
            adding_rule = None
            for rule in rules:
                for spec in rule.approvers:
                    if spec.approver_type == approver.approver_type:
                        adding_rule = rule
                        break

            if audience == Audience.REQUESTER:
                # Simple explanation
                reason = self._approver_descriptions.get(
                    approver.approver_type,
                    approver.approver_type.value.lower()
                )
                explanations.append({
                    "approver": approver.approver_name,
                    "role": approver.approver_type.value,
                    "reason": f"Required because they are {reason}",
                })
            else:
                # More detail for approvers/auditors
                rule_ref = f" (Rule: {adding_rule.rule_id})" if adding_rule else ""
                explanations.append({
                    "approver": approver.approver_name,
                    "approver_id": approver.approver_id,
                    "role": approver.approver_type.value,
                    "layer": adding_rule.layer.value if adding_rule else "UNKNOWN",
                    "reason": adding_rule.explanation if adding_rule else "Required by policy",
                    "rule_reference": rule_ref,
                })

        return explanations

    def _explain_risk_factors(self, risk: RiskContext) -> List[RiskFactor]:
        """Break down risk score into contributing factors."""
        factors = []

        # Base risk from request type
        base_risk = risk.base_risk_score if hasattr(risk, 'base_risk_score') else 20
        factors.append(RiskFactor(
            factor_name="Base Request Risk",
            contribution=base_risk,
            description="Baseline risk for this type of access request",
            value=base_risk,
        ))

        # SoD conflicts
        if risk.sod_conflicts:
            sod_contribution = min(len(risk.sod_conflicts) * 10, 30)
            factors.append(RiskFactor(
                factor_name="SoD Conflicts",
                contribution=sod_contribution,
                description=f"Found {len(risk.sod_conflicts)} potential separation of duty conflicts",
                value=len(risk.sod_conflicts),
                threshold=0,
            ))

        # Sensitive data
        if risk.sensitive_data_access:
            for data_type in risk.sensitive_data_access[:3]:
                factors.append(RiskFactor(
                    factor_name=f"Sensitive Data: {data_type}",
                    contribution=15,
                    description=f"Access to {data_type} data increases risk",
                    value=data_type,
                ))

        # Toxic combinations
        if risk.toxic_combinations:
            for combo in risk.toxic_combinations[:2]:
                factors.append(RiskFactor(
                    factor_name="Toxic Combination",
                    contribution=20,
                    description=f"Toxic permission combination detected: {combo.get('name', 'unknown')}",
                    value=combo,
                ))

        # High-privilege indicators
        if risk.high_privilege_indicators:
            for indicator in risk.high_privilege_indicators[:3]:
                factors.append(RiskFactor(
                    factor_name="High Privilege",
                    contribution=10,
                    description=f"High privilege indicator: {indicator}",
                    value=indicator,
                ))

        return factors

    def _summarize_risk(self, risk: RiskContext, audience: Audience) -> str:
        """Generate risk summary for audience."""
        score = risk.risk_score
        level = self._get_risk_level(score)

        if audience == Audience.REQUESTER:
            if score <= 20:
                return "This is a low-risk request and should be processed quickly."
            elif score <= 50:
                return (
                    "This request has moderate risk factors. Your manager will need to confirm "
                    "this access is appropriate for your role."
                )
            elif score <= 80:
                return (
                    "This is a high-risk request that will require careful review by the "
                    "security team. Please ensure you have a valid business justification."
                )
            else:
                return (
                    "This is a critical-risk request requiring CISO approval. Access of this "
                    "nature is typically reserved for specific job functions."
                )

        elif audience == Audience.APPROVER:
            factors = []
            if risk.sod_conflicts:
                factors.append(f"{len(risk.sod_conflicts)} SoD conflicts")
            if risk.toxic_combinations:
                factors.append(f"{len(risk.toxic_combinations)} toxic combinations")
            if risk.sensitive_data_access:
                factors.append(f"access to {len(risk.sensitive_data_access)} sensitive data types")

            factor_text = ", ".join(factors) if factors else "standard risk factors"
            return f"Risk score of {score}/100 ({level}) driven by {factor_text}."

        else:  # AUDITOR/EXECUTIVE
            return f"Computed risk score: {score}/100. Classification: {level}."

    def _explain_rules(self, rules: List[ApprovalRule]) -> List[RuleMatch]:
        """Explain which rules matched and why."""
        matches = []

        for rule in rules:
            conditions_matched = []
            for cond in rule.conditions:
                conditions_matched.append(
                    f"{cond.field} {cond.operator} {cond.value}"
                )

            approvers_added = [
                spec.approver_type.value for spec in rule.approvers
            ]

            matches.append(RuleMatch(
                rule_id=rule.rule_id,
                rule_name=rule.name,
                layer=rule.layer,
                priority=rule.priority,
                conditions_matched=conditions_matched,
                approvers_added=approvers_added,
                sla_hours=rule.sla_hours,
                explanation=rule.explanation,
            ))

        return matches

    def _explain_timeline(self, sla_hours: float, approvers: List[Approver]) -> str:
        """Explain expected timeline."""
        if sla_hours <= 4:
            return f"Target completion within {sla_hours:.0f} hours (same business day)."
        elif sla_hours <= 24:
            return f"Target completion within {sla_hours:.0f} hours (1 business day)."
        elif sla_hours <= 72:
            days = sla_hours / 24
            return f"Target completion within {days:.0f} business days due to multiple approvers."
        else:
            days = sla_hours / 24
            return f"Extended timeline of {days:.0f} days due to elevated risk requiring careful review."

    def _trace_determination_path(
        self,
        context: ApprovalContext,
        rules: List[ApprovalRule],
        approvers: List[Approver]
    ) -> List[str]:
        """Trace the determination path for audit."""
        path = []

        path.append(f"1. Received request {context.request.request_id if context.request else 'N/A'}")
        path.append(f"2. Calculated risk score: {context.risk.risk_score if context.risk else 0}")
        path.append(f"3. Risk classification: {self._get_risk_level(context.risk.risk_score if context.risk else 0)}")

        # Rules by layer
        mandatory = [r for r in rules if r.layer == RuleLayer.MANDATORY]
        risk_based = [r for r in rules if r.layer == RuleLayer.RISK_ADAPTIVE]
        contextual = [r for r in rules if r.layer == RuleLayer.CONTEXTUAL]

        path.append(f"4. Layer 1 (Mandatory): {len(mandatory)} rules matched")
        for r in mandatory:
            path.append(f"   - {r.rule_id}: {r.explanation}")

        path.append(f"5. Layer 2 (Risk-Adaptive): {len(risk_based)} rules matched")
        for r in risk_based:
            path.append(f"   - {r.rule_id}: {r.explanation}")

        path.append(f"6. Layer 3 (Contextual): {len(contextual)} rules matched")
        for r in contextual:
            path.append(f"   - {r.rule_id}: {r.explanation}")

        path.append(f"7. Final approvers determined: {len(approvers)}")
        for a in approvers:
            path.append(f"   - {a.approver_name} ({a.approver_type.value})")

        max_sla = max((r.sla_hours for r in rules), default=24.0)
        path.append(f"8. SLA set: {max_sla} hours")

        return path

    def _get_risk_level(self, score: int) -> str:
        """Get risk level name from score."""
        for (low, high), (level, _) in self._risk_levels.items():
            if low <= score <= high:
                return level
        return "UNKNOWN"

    def _count_layers(self, rules: List[ApprovalRule]) -> int:
        """Count distinct layers in rules."""
        return len(set(r.layer for r in rules))

    def what_if_analysis(
        self,
        request: ApprovalRequest,
        context: ApprovalContext,
        scenarios: List[Dict[str, Any]]
    ) -> List[WhatIfResult]:
        """
        Run what-if analysis for different scenarios.

        Example scenarios:
        - "What if risk score was lower?"
        - "What if this was non-production?"
        - "What if requester had existing access?"
        """
        results = []

        # Get current state
        current_result = self.rule_engine.evaluate(context)
        current_approvers = [a.approver_id for a in current_result.approvers]

        for scenario in scenarios:
            # Clone context and modify
            modified_context = self._apply_scenario(context, scenario)

            # Re-evaluate
            new_result = self.rule_engine.evaluate(modified_context)
            new_approvers = [a.approver_id for a in new_result.approvers]

            # Calculate changes
            risk_change = (
                (modified_context.risk.risk_score if modified_context.risk else 0) -
                (context.risk.risk_score if context.risk else 0)
            )
            sla_change = new_result.sla_hours - current_result.sla_hours

            # Generate explanation
            if set(new_approvers) == set(current_approvers):
                explanation = "No change in required approvers"
                recommendation = "Current routing is appropriate"
            elif len(new_approvers) < len(current_approvers):
                removed = set(current_approvers) - set(new_approvers)
                explanation = f"Would remove {len(removed)} approver(s)"
                recommendation = "Consider if scenario conditions can be met"
            else:
                added = set(new_approvers) - set(current_approvers)
                explanation = f"Would add {len(added)} approver(s)"
                recommendation = "Current routing is more efficient"

            results.append(WhatIfResult(
                scenario=scenario.get("description", "Modified scenario"),
                original_approvers=current_approvers,
                new_approvers=new_approvers,
                risk_change=risk_change,
                sla_change=sla_change,
                explanation=explanation,
                recommendation=recommendation,
            ))

        return results

    def _apply_scenario(
        self,
        context: ApprovalContext,
        scenario: Dict[str, Any]
    ) -> ApprovalContext:
        """Apply what-if scenario to context."""
        # Create modified copies
        modified_risk = RiskContext(
            risk_score=scenario.get("risk_score", context.risk.risk_score if context.risk else 0),
            sod_conflicts=scenario.get("sod_conflicts", context.risk.sod_conflicts if context.risk else []),
            sensitive_data_access=scenario.get("sensitive_data", context.risk.sensitive_data_access if context.risk else []),
            toxic_combinations=context.risk.toxic_combinations if context.risk else [],
            high_privilege_indicators=context.risk.high_privilege_indicators if context.risk else [],
        )

        modified_request = RequestContext(
            request_id=context.request.request_id if context.request else "",
            request_type=context.request.request_type if context.request else "",
            system_id=scenario.get("system_id", context.request.system_id if context.request else ""),
            is_production=scenario.get("is_production", context.request.is_production if context.request else False),
            business_process=context.request.business_process if context.request else "",
        )

        return ApprovalContext(
            request=modified_request,
            risk=modified_risk,
            user=context.user,
        )

    def generate_audit_narrative(
        self,
        request: ApprovalRequest,
        context: ApprovalContext,
        rules: List[ApprovalRule],
        approvers: List[Approver],
        decisions: List[Dict[str, Any]]
    ) -> str:
        """
        Generate complete audit narrative for a completed request.

        Suitable for compliance documentation.
        """
        lines = []

        lines.append("=" * 60)
        lines.append("APPROVAL DETERMINATION AUDIT REPORT")
        lines.append("=" * 60)
        lines.append("")

        lines.append(f"Request ID: {request.request_id}")
        lines.append(f"Request Type: {request.request_type}")
        lines.append(f"System: {request.system_id}")
        lines.append(f"Requester: {request.requester_id}")
        lines.append(f"Submitted: {request.submitted_at.isoformat() if request.submitted_at else 'N/A'}")
        lines.append("")

        lines.append("-" * 40)
        lines.append("RISK ASSESSMENT")
        lines.append("-" * 40)
        risk_score = context.risk.risk_score if context.risk else 0
        lines.append(f"Risk Score: {risk_score}/100")
        lines.append(f"Risk Level: {self._get_risk_level(risk_score)}")

        if context.risk:
            if context.risk.sod_conflicts:
                lines.append(f"SoD Conflicts: {len(context.risk.sod_conflicts)}")
            if context.risk.toxic_combinations:
                lines.append(f"Toxic Combinations: {len(context.risk.toxic_combinations)}")
            if context.risk.sensitive_data_access:
                lines.append(f"Sensitive Data Types: {', '.join(context.risk.sensitive_data_access)}")
        lines.append("")

        lines.append("-" * 40)
        lines.append("RULES APPLIED")
        lines.append("-" * 40)
        for rule in rules:
            lines.append(f"  [{rule.layer.value}] {rule.rule_id}")
            lines.append(f"    Explanation: {rule.explanation}")
            lines.append(f"    Approvers Added: {[s.approver_type.value for s in rule.approvers]}")
        lines.append("")

        lines.append("-" * 40)
        lines.append("APPROVERS REQUIRED")
        lines.append("-" * 40)
        for approver in approvers:
            lines.append(f"  - {approver.approver_name} ({approver.approver_type.value})")
        lines.append("")

        lines.append("-" * 40)
        lines.append("DECISIONS RECORDED")
        lines.append("-" * 40)
        for decision in decisions:
            lines.append(f"  Approver: {decision.get('approver_id', 'N/A')}")
            lines.append(f"  Decision: {decision.get('status', 'N/A')}")
            lines.append(f"  Timestamp: {decision.get('decided_at', 'N/A')}")
            if decision.get('comments'):
                lines.append(f"  Comments: {decision.get('comments')}")
            lines.append("")

        lines.append("=" * 60)
        lines.append(f"Report Generated: {datetime.now().isoformat()}")
        lines.append("=" * 60)

        return "\n".join(lines)

    def generate_comparison_report(
        self,
        brfplus_route: Dict[str, Any],
        governex_route: Dict[str, Any]
    ) -> str:
        """
        Generate side-by-side comparison of BRF+ vs GOVERNEX+ routing.

        For migration validation.
        """
        lines = []

        lines.append("=" * 70)
        lines.append("BRF+ vs GOVERNEX+ APPROVAL ROUTING COMPARISON")
        lines.append("=" * 70)
        lines.append("")

        lines.append(f"{'Attribute':<25} {'BRF+':<20} {'GOVERNEX+':<20}")
        lines.append("-" * 70)

        # Compare approvers
        brfplus_approvers = brfplus_route.get("approvers", [])
        governex_approvers = governex_route.get("approvers", [])

        lines.append(f"{'Approver Count':<25} {len(brfplus_approvers):<20} {len(governex_approvers):<20}")

        lines.append("")
        lines.append("Approvers (BRF+):")
        for a in brfplus_approvers:
            lines.append(f"  - {a}")

        lines.append("")
        lines.append("Approvers (GOVERNEX+):")
        for a in governex_approvers:
            lines.append(f"  - {a}")

        # Compare SLA
        brfplus_sla = brfplus_route.get("sla_hours", "N/A")
        governex_sla = governex_route.get("sla_hours", "N/A")
        lines.append("")
        lines.append(f"{'SLA (hours)':<25} {brfplus_sla:<20} {governex_sla:<20}")

        # GOVERNEX+ advantages
        lines.append("")
        lines.append("-" * 70)
        lines.append("GOVERNEX+ ADVANTAGES")
        lines.append("-" * 70)

        advantages = []
        if governex_route.get("risk_score"):
            advantages.append(f"  - Risk score calculated: {governex_route['risk_score']}/100")
        if governex_route.get("explanation"):
            advantages.append(f"  - Full explainability provided")
        if governex_route.get("what_if_available"):
            advantages.append(f"  - What-if analysis available")
        if governex_route.get("delegation_supported"):
            advantages.append(f"  - Automatic delegation on OOO")
        if governex_route.get("ai_optimization"):
            advantages.append(f"  - AI-optimized approver selection")

        for adv in advantages:
            lines.append(adv)

        lines.append("")
        lines.append("=" * 70)

        return "\n".join(lines)
