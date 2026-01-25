"""
Explainable Risk Narratives Engine

Provides plain-English explanations for all risk decisions.
EXPLAINABILITY = TRUST, TRUST = ADOPTION

Key Capabilities:
- "Why was this risky?" explanations
- "Why was it approved?" narratives
- "Why is this user different from peers?" analysis
- "Why is this mitigation sufficient?" rationale
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from enum import Enum
import statistics


class NarrativeType(Enum):
    """Types of narratives"""
    RISK_EXPLANATION = "risk_explanation"
    APPROVAL_RATIONALE = "approval_rationale"
    PEER_COMPARISON = "peer_comparison"
    MITIGATION_RATIONALE = "mitigation_rationale"
    VIOLATION_EXPLANATION = "violation_explanation"
    RECOMMENDATION = "recommendation"


class AudienceLevel(Enum):
    """Target audience for narrative"""
    EXECUTIVE = "executive"     # Board/C-level - high-level, business impact
    MANAGER = "manager"         # Managers - actionable, context
    TECHNICAL = "technical"     # IT/GRC team - detailed, technical
    AUDITOR = "auditor"         # Auditors - evidence-based, control-focused
    END_USER = "end_user"       # Self-service - simple, clear


@dataclass
class NarrativeContext:
    """Context for generating a narrative"""
    entity_type: str  # user, role, request, violation, control
    entity_id: str
    risk_score: float
    risk_level: str
    risk_factors: List[str]
    peer_group: Optional[str] = None
    peer_average: Optional[float] = None
    historical_data: Dict = field(default_factory=dict)
    related_controls: List[str] = field(default_factory=list)
    related_mitigations: List[str] = field(default_factory=list)


@dataclass
class RiskNarrative:
    """A generated risk narrative"""
    narrative_id: str
    narrative_type: NarrativeType
    audience_level: AudienceLevel
    entity_type: str
    entity_id: str

    # The narrative content
    headline: str
    summary: str
    detailed_explanation: str
    key_points: List[str]
    evidence: List[str]
    recommendations: List[str]

    # Supporting data
    risk_score: float
    risk_level: str
    confidence_score: float  # How confident we are in this explanation

    # Metadata
    generated_at: datetime = field(default_factory=datetime.utcnow)
    valid_until: Optional[datetime] = None


class RiskNarrativeEngine:
    """
    Engine for generating explainable risk narratives.

    Makes complex GRC decisions understandable to any audience.
    """

    def __init__(self):
        self.narrative_templates: Dict[str, Dict] = {}
        self.generated_narratives: Dict[str, RiskNarrative] = {}
        self._init_templates()

    def _init_templates(self):
        """Initialize narrative templates"""

        # Risk level descriptions
        self.risk_level_descriptions = {
            "critical": {
                "executive": "presents an immediate threat to business operations",
                "manager": "requires urgent attention and immediate action",
                "technical": "exceeds all risk thresholds and triggers immediate review",
                "auditor": "represents a material control weakness",
                "end_user": "is very high and needs to be addressed right away"
            },
            "high": {
                "executive": "poses significant business risk",
                "manager": "should be addressed within this review cycle",
                "technical": "exceeds standard risk thresholds",
                "auditor": "requires documented mitigation or remediation plan",
                "end_user": "is higher than normal and should be reviewed"
            },
            "medium": {
                "executive": "requires monitoring and planned remediation",
                "manager": "should be included in regular review processes",
                "technical": "falls within elevated risk parameters",
                "auditor": "should be tracked and periodically reassessed",
                "end_user": "is moderate - no immediate action needed"
            },
            "low": {
                "executive": "is within acceptable business parameters",
                "manager": "can be managed through standard processes",
                "technical": "falls within normal operating thresholds",
                "auditor": "is adequately controlled",
                "end_user": "is low - you're in good shape"
            }
        }

    def explain_user_risk(
        self,
        user_id: str,
        user_name: str,
        department: str,
        risk_score: float,
        risk_level: str,
        risk_factors: List[str],
        access_summary: Dict,
        peer_average: Optional[float] = None,
        audience: AudienceLevel = AudienceLevel.MANAGER
    ) -> RiskNarrative:
        """Generate explanation for user risk score"""

        # Build context
        context = NarrativeContext(
            entity_type="user",
            entity_id=user_id,
            risk_score=risk_score,
            risk_level=risk_level,
            risk_factors=risk_factors,
            peer_average=peer_average
        )

        # Generate headline based on audience
        if audience == AudienceLevel.EXECUTIVE:
            headline = f"{user_name} in {department} {self.risk_level_descriptions[risk_level]['executive']}"
        elif audience == AudienceLevel.END_USER:
            headline = f"Your access risk score is {risk_score:.0f} out of 100"
        else:
            headline = f"Risk Assessment: {user_name} ({user_id}) - {risk_level.upper()} risk ({risk_score:.0f}/100)"

        # Generate summary
        summary = self._generate_user_risk_summary(
            user_name, department, risk_score, risk_level, risk_factors, peer_average, audience
        )

        # Generate detailed explanation
        detailed = self._generate_user_risk_detail(
            user_name, risk_factors, access_summary, peer_average, audience
        )

        # Key points
        key_points = self._extract_key_points(risk_factors, audience)

        # Evidence
        evidence = self._generate_evidence(risk_factors, access_summary)

        # Recommendations
        recommendations = self._generate_user_recommendations(risk_level, risk_factors, audience)

        narrative = RiskNarrative(
            narrative_id=f"NAR-{user_id}-{int(datetime.utcnow().timestamp())}",
            narrative_type=NarrativeType.RISK_EXPLANATION,
            audience_level=audience,
            entity_type="user",
            entity_id=user_id,
            headline=headline,
            summary=summary,
            detailed_explanation=detailed,
            key_points=key_points,
            evidence=evidence,
            recommendations=recommendations,
            risk_score=risk_score,
            risk_level=risk_level,
            confidence_score=self._calculate_confidence(len(risk_factors), len(evidence))
        )

        self.generated_narratives[narrative.narrative_id] = narrative
        return narrative

    def _generate_user_risk_summary(
        self,
        user_name: str,
        department: str,
        risk_score: float,
        risk_level: str,
        risk_factors: List[str],
        peer_average: Optional[float],
        audience: AudienceLevel
    ) -> str:
        """Generate user risk summary"""

        if audience == AudienceLevel.EXECUTIVE:
            peer_comp = ""
            if peer_average:
                if risk_score > peer_average * 1.2:
                    peer_comp = f" This is {((risk_score/peer_average)-1)*100:.0f}% higher than peers in the same role."
                elif risk_score < peer_average * 0.8:
                    peer_comp = f" This is well below the peer average of {peer_average:.0f}."

            return (
                f"{user_name} has a risk score of {risk_score:.0f}, which {self.risk_level_descriptions[risk_level]['executive']}.{peer_comp} "
                f"The primary concern is {risk_factors[0].lower() if risk_factors else 'elevated access levels'}."
            )

        elif audience == AudienceLevel.END_USER:
            if risk_level in ["low", "minimal"]:
                return (
                    f"Good news! Your access permissions are well-managed. Your risk score of {risk_score:.0f} "
                    f"indicates your access is appropriate for your role."
                )
            else:
                main_reason = risk_factors[0] if risk_factors else "your current access levels"
                return (
                    f"Your risk score is {risk_score:.0f} out of 100. The main reason is: {main_reason.lower()}. "
                    f"This doesn't mean you did anything wrong - it just means your access should be reviewed."
                )

        elif audience == AudienceLevel.AUDITOR:
            return (
                f"Identity {user_name} ({department}) assessed at {risk_level.upper()} risk "
                f"(score: {risk_score:.1f}/100). Assessment based on {len(risk_factors)} risk factors. "
                f"Peer comparison: {'Above average' if peer_average and risk_score > peer_average else 'Within normal range'}."
            )

        else:  # Manager/Technical
            return (
                f"{user_name}'s risk score of {risk_score:.0f} places them at {risk_level.upper()} risk level. "
                f"This assessment is based on {len(risk_factors)} contributing factors including "
                f"{', '.join(risk_factors[:2]) if len(risk_factors) >= 2 else risk_factors[0] if risk_factors else 'access patterns'}."
            )

    def _generate_user_risk_detail(
        self,
        user_name: str,
        risk_factors: List[str],
        access_summary: Dict,
        peer_average: Optional[float],
        audience: AudienceLevel
    ) -> str:
        """Generate detailed risk explanation"""

        sections = []

        # Factor analysis
        if risk_factors:
            if audience == AudienceLevel.END_USER:
                sections.append("**What's contributing to your score:**")
                for i, factor in enumerate(risk_factors[:3], 1):
                    sections.append(f"{i}. {factor}")
            else:
                sections.append("**Risk Factor Analysis:**")
                for factor in risk_factors:
                    sections.append(f"• {factor}")

        # Access analysis
        if access_summary:
            systems = access_summary.get("total_systems", 0)
            roles = access_summary.get("total_roles", 0)

            if audience in [AudienceLevel.TECHNICAL, AudienceLevel.AUDITOR]:
                sections.append(f"\n**Access Footprint:**")
                sections.append(f"• Systems with access: {systems}")
                sections.append(f"• Total roles assigned: {roles}")
                sections.append(f"• Entitlements: {access_summary.get('total_entitlements', 0)}")
            else:
                sections.append(f"\n**Access Summary:** Access across {systems} systems with {roles} roles.")

        # Peer comparison
        if peer_average:
            if audience == AudienceLevel.AUDITOR:
                sections.append(f"\n**Peer Comparison:** Peer group average: {peer_average:.1f}. "
                              f"Subject is {'above' if access_summary.get('risk_score', 0) > peer_average else 'at or below'} average.")

        return "\n".join(sections)

    def _extract_key_points(self, risk_factors: List[str], audience: AudienceLevel) -> List[str]:
        """Extract key points from risk factors"""

        if audience == AudienceLevel.EXECUTIVE:
            # Simplify for executives
            return [f.split('-')[0].strip() if '-' in f else f[:50] for f in risk_factors[:3]]
        elif audience == AudienceLevel.END_USER:
            # Make it actionable for users
            key_points = []
            for factor in risk_factors[:3]:
                if "admin" in factor.lower():
                    key_points.append("You have administrator-level access that should be reviewed")
                elif "dormant" in factor.lower():
                    key_points.append("Some of your access hasn't been used recently")
                elif "role" in factor.lower() and "count" in factor.lower():
                    key_points.append("You have many roles - some might not be needed anymore")
                else:
                    key_points.append(factor)
            return key_points
        else:
            return risk_factors[:5]

    def _generate_evidence(self, risk_factors: List[str], access_summary: Dict) -> List[str]:
        """Generate evidence supporting the assessment"""

        evidence = []

        for factor in risk_factors:
            if "system" in factor.lower():
                evidence.append(f"System access data: {factor}")
            elif "role" in factor.lower():
                evidence.append(f"Role analysis: {factor}")
            else:
                evidence.append(f"Assessment factor: {factor}")

        if access_summary:
            evidence.append(f"Total access footprint: {access_summary.get('total_systems', 0)} systems, "
                          f"{access_summary.get('total_roles', 0)} roles")

        return evidence

    def _generate_user_recommendations(
        self,
        risk_level: str,
        risk_factors: List[str],
        audience: AudienceLevel
    ) -> List[str]:
        """Generate recommendations"""

        recommendations = []

        if risk_level == "critical":
            if audience == AudienceLevel.END_USER:
                recommendations.append("Please contact your manager or IT security to review your access")
            else:
                recommendations.append("Immediate review required - consider temporary access restriction")
                recommendations.append("Escalate to security team for investigation")

        elif risk_level == "high":
            if audience == AudienceLevel.END_USER:
                recommendations.append("Consider whether you still need all your current access")
            else:
                recommendations.append("Schedule access review within 30 days")
                recommendations.append("Verify all access is still business-justified")

        # Factor-specific recommendations
        for factor in risk_factors:
            if "admin" in factor.lower():
                recommendations.append("Review necessity of administrative privileges")
            if "dormant" in factor.lower():
                recommendations.append("Consider revoking unused access")
            if "ghost" in factor.lower():
                recommendations.append("URGENT: Immediately revoke all access for terminated identity")

        return recommendations[:5]

    def _calculate_confidence(self, factor_count: int, evidence_count: int) -> float:
        """Calculate confidence score for the narrative"""

        base = 50.0
        base += min(factor_count * 10, 30)  # Up to 30 points for factors
        base += min(evidence_count * 5, 20)  # Up to 20 points for evidence
        return min(base, 100)

    def explain_approval_decision(
        self,
        request_id: str,
        request_type: str,
        decision: str,
        approver_name: str,
        risk_level: str,
        risk_score: float,
        decision_factors: List[str],
        mitigations_applied: List[str],
        audience: AudienceLevel = AudienceLevel.AUDITOR
    ) -> RiskNarrative:
        """Generate explanation for approval decision"""

        if decision == "approved":
            headline = f"Access Request {request_id} APPROVED with {risk_level} risk"
            summary = self._generate_approval_summary(
                request_id, approver_name, risk_level, risk_score,
                decision_factors, mitigations_applied, audience
            )
        else:
            headline = f"Access Request {request_id} REJECTED due to {risk_level} risk"
            summary = self._generate_rejection_summary(
                request_id, approver_name, risk_level, decision_factors, audience
            )

        detailed = self._generate_approval_detail(
            decision, risk_level, decision_factors, mitigations_applied
        )

        narrative = RiskNarrative(
            narrative_id=f"NAR-APR-{request_id}-{int(datetime.utcnow().timestamp())}",
            narrative_type=NarrativeType.APPROVAL_RATIONALE,
            audience_level=audience,
            entity_type="request",
            entity_id=request_id,
            headline=headline,
            summary=summary,
            detailed_explanation=detailed,
            key_points=decision_factors[:3],
            evidence=[f"Risk score at decision time: {risk_score}", f"Approver: {approver_name}"],
            recommendations=[],
            risk_score=risk_score,
            risk_level=risk_level,
            confidence_score=90.0
        )

        self.generated_narratives[narrative.narrative_id] = narrative
        return narrative

    def _generate_approval_summary(
        self,
        request_id: str,
        approver_name: str,
        risk_level: str,
        risk_score: float,
        factors: List[str],
        mitigations: List[str],
        audience: AudienceLevel
    ) -> str:
        """Generate approval summary"""

        if audience == AudienceLevel.AUDITOR:
            mitigation_text = f"with {len(mitigations)} mitigating controls" if mitigations else "without additional mitigations"
            return (
                f"Request {request_id} was approved by {approver_name} at {risk_level} risk level "
                f"(score: {risk_score:.1f}) {mitigation_text}. "
                f"Decision factors: {', '.join(factors[:2])}."
            )
        else:
            if risk_level in ["high", "critical"]:
                return (
                    f"This request was approved despite {risk_level} risk because "
                    f"appropriate mitigating controls are in place: {', '.join(mitigations[:2]) if mitigations else 'business justification reviewed'}."
                )
            else:
                return f"This request was approved at {risk_level} risk level following standard review."

    def _generate_rejection_summary(
        self,
        request_id: str,
        approver_name: str,
        risk_level: str,
        factors: List[str],
        audience: AudienceLevel
    ) -> str:
        """Generate rejection summary"""

        main_reason = factors[0] if factors else "unacceptable risk level"

        if audience == AudienceLevel.END_USER:
            return (
                f"Your access request was not approved. The main reason: {main_reason.lower()}. "
                f"Please contact your manager if you believe this access is necessary for your job."
            )
        else:
            return (
                f"Request {request_id} was rejected by {approver_name} due to {risk_level} risk. "
                f"Primary rejection reason: {main_reason}."
            )

    def _generate_approval_detail(
        self,
        decision: str,
        risk_level: str,
        factors: List[str],
        mitigations: List[str]
    ) -> str:
        """Generate detailed approval explanation"""

        sections = []

        sections.append(f"**Decision:** {decision.upper()}")
        sections.append(f"**Risk Level:** {risk_level.upper()}")

        if factors:
            sections.append("\n**Factors Considered:**")
            for factor in factors:
                sections.append(f"• {factor}")

        if mitigations and decision == "approved":
            sections.append("\n**Mitigating Controls:**")
            for mit in mitigations:
                sections.append(f"• {mit}")

        return "\n".join(sections)

    def explain_violation(
        self,
        violation_id: str,
        rule_name: str,
        risk_level: str,
        conflicting_functions: List[str],
        business_impact: str,
        user_name: str,
        audience: AudienceLevel = AudienceLevel.MANAGER
    ) -> RiskNarrative:
        """Generate explanation for an SoD violation"""

        if audience == AudienceLevel.END_USER:
            headline = f"You have a Segregation of Duties concern"
            summary = (
                f"Our analysis found that your access includes conflicting responsibilities: "
                f"{' and '.join(conflicting_functions)}. This is a {risk_level} risk item. "
                f"Why it matters: {business_impact}"
            )
        elif audience == AudienceLevel.EXECUTIVE:
            headline = f"{risk_level.upper()} SoD Violation: {rule_name}"
            summary = (
                f"A segregation of duties conflict has been detected. "
                f"Business impact: {business_impact}. "
                f"This violation should be addressed to maintain proper internal controls."
            )
        else:
            headline = f"SoD Violation {violation_id}: {rule_name}"
            summary = (
                f"User {user_name} has access to conflicting functions: {' vs '.join(conflicting_functions)}. "
                f"Risk level: {risk_level.upper()}. {business_impact}"
            )

        narrative = RiskNarrative(
            narrative_id=f"NAR-VIO-{violation_id}",
            narrative_type=NarrativeType.VIOLATION_EXPLANATION,
            audience_level=audience,
            entity_type="violation",
            entity_id=violation_id,
            headline=headline,
            summary=summary,
            detailed_explanation=self._generate_violation_detail(
                rule_name, conflicting_functions, business_impact, audience
            ),
            key_points=[
                f"Rule: {rule_name}",
                f"Functions: {' vs '.join(conflicting_functions)}",
                f"Impact: {business_impact[:50]}..."
            ],
            evidence=[f"Functions in conflict: {', '.join(conflicting_functions)}"],
            recommendations=self._generate_violation_recommendations(risk_level, audience),
            risk_score=85.0 if risk_level == "critical" else 70.0 if risk_level == "high" else 50.0,
            risk_level=risk_level,
            confidence_score=95.0
        )

        self.generated_narratives[narrative.narrative_id] = narrative
        return narrative

    def _generate_violation_detail(
        self,
        rule_name: str,
        functions: List[str],
        impact: str,
        audience: AudienceLevel
    ) -> str:
        """Generate detailed violation explanation"""

        if audience == AudienceLevel.END_USER:
            return (
                f"**What is Segregation of Duties?**\n"
                f"It's a basic principle that certain tasks should be done by different people "
                f"to prevent errors and fraud.\n\n"
                f"**Your situation:**\n"
                f"You have access to both {functions[0]} AND {functions[1]}. "
                f"Having both could allow: {impact}\n\n"
                f"**What happens now:**\n"
                f"This will be reviewed. You may not need to do anything if the access is necessary for your job."
            )
        else:
            return (
                f"**Rule:** {rule_name}\n\n"
                f"**Conflicting Functions:**\n"
                f"• Function 1: {functions[0]}\n"
                f"• Function 2: {functions[1]}\n\n"
                f"**Business Risk:**\n{impact}\n\n"
                f"**Control Requirement:**\n"
                f"These functions should be performed by different individuals to maintain "
                f"proper segregation of duties."
            )

    def _generate_violation_recommendations(self, risk_level: str, audience: AudienceLevel) -> List[str]:
        """Generate violation recommendations"""

        if audience == AudienceLevel.END_USER:
            return [
                "Wait for your manager to review this",
                "If you receive a request to justify this access, please respond promptly"
            ]
        else:
            recs = []
            if risk_level in ["critical", "high"]:
                recs.append("Immediately assess if both accesses are required")
                recs.append("If both required, implement mitigating control with documented approval")
            recs.append("Review if access can be split between two individuals")
            recs.append("Document business justification if exception is needed")
            return recs

    def explain_mitigation_sufficiency(
        self,
        mitigation_id: str,
        mitigation_name: str,
        covered_violation: str,
        effectiveness_score: float,
        control_activities: List[str],
        audience: AudienceLevel = AudienceLevel.AUDITOR
    ) -> RiskNarrative:
        """Generate explanation for why a mitigation is sufficient"""

        is_sufficient = effectiveness_score >= 70

        if is_sufficient:
            headline = f"Mitigation '{mitigation_name}' is SUFFICIENT for {covered_violation}"
            summary = (
                f"The mitigating control demonstrates {effectiveness_score:.0f}% effectiveness "
                f"in addressing the risk from {covered_violation}. "
                f"This is based on {len(control_activities)} control activities."
            )
        else:
            headline = f"Mitigation '{mitigation_name}' has GAPS for {covered_violation}"
            summary = (
                f"The mitigating control shows only {effectiveness_score:.0f}% effectiveness. "
                f"Additional controls or remediation may be required."
            )

        narrative = RiskNarrative(
            narrative_id=f"NAR-MIT-{mitigation_id}",
            narrative_type=NarrativeType.MITIGATION_RATIONALE,
            audience_level=audience,
            entity_type="mitigation",
            entity_id=mitigation_id,
            headline=headline,
            summary=summary,
            detailed_explanation=self._generate_mitigation_detail(
                mitigation_name, effectiveness_score, control_activities
            ),
            key_points=[
                f"Effectiveness: {effectiveness_score:.0f}%",
                f"Control activities: {len(control_activities)}",
                f"Verdict: {'Sufficient' if is_sufficient else 'Needs improvement'}"
            ],
            evidence=[f"Activity: {act}" for act in control_activities[:3]],
            recommendations=[] if is_sufficient else [
                "Increase review frequency",
                "Add automated monitoring",
                "Consider additional detective controls"
            ],
            risk_score=100 - effectiveness_score,
            risk_level="low" if is_sufficient else "medium",
            confidence_score=effectiveness_score
        )

        self.generated_narratives[narrative.narrative_id] = narrative
        return narrative

    def _generate_mitigation_detail(
        self,
        name: str,
        effectiveness: float,
        activities: List[str]
    ) -> str:
        """Generate mitigation detail"""

        sections = [
            f"**Mitigation Control:** {name}",
            f"**Effectiveness Score:** {effectiveness:.1f}%",
            f"\n**Control Activities:**"
        ]

        for act in activities:
            sections.append(f"• {act}")

        if effectiveness >= 80:
            sections.append(f"\n**Assessment:** This mitigation provides STRONG coverage.")
        elif effectiveness >= 60:
            sections.append(f"\n**Assessment:** This mitigation provides ADEQUATE coverage "
                          f"but could be strengthened.")
        else:
            sections.append(f"\n**Assessment:** This mitigation has GAPS that should be addressed.")

        return "\n".join(sections)

    def get_narrative_for_audience(
        self,
        narrative_id: str,
        target_audience: AudienceLevel
    ) -> Optional[RiskNarrative]:
        """Adapt an existing narrative for a different audience"""

        original = self.generated_narratives.get(narrative_id)
        if not original:
            return None

        # For now, return original - in production would regenerate
        # with appropriate templates for target audience
        return original

    def generate_audit_package(
        self,
        entity_type: str,
        entity_id: str,
        include_history: bool = True
    ) -> Dict:
        """Generate complete audit documentation package"""

        relevant_narratives = [
            n for n in self.generated_narratives.values()
            if n.entity_type == entity_type and n.entity_id == entity_id
        ]

        return {
            "entity": {
                "type": entity_type,
                "id": entity_id
            },
            "narratives": [
                {
                    "narrative_id": n.narrative_id,
                    "type": n.narrative_type.value,
                    "headline": n.headline,
                    "summary": n.summary,
                    "detailed_explanation": n.detailed_explanation,
                    "evidence": n.evidence,
                    "recommendations": n.recommendations,
                    "confidence": n.confidence_score,
                    "generated_at": n.generated_at.isoformat()
                }
                for n in relevant_narratives
            ],
            "generated_at": datetime.utcnow().isoformat(),
            "package_purpose": "Audit documentation and evidence package"
        }
