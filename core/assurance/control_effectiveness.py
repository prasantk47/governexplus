"""
Control Effectiveness Scoring Engine

Proves that controls actually work - not just that they exist.
This transforms the platform from compliance reporting to an ASSURANCE platform.

Key Capabilities:
- Control effectiveness scoring
- Approval quality metrics
- Exception trend analysis
- Mitigation success tracking
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from enum import Enum
import statistics
import math


class ControlType(Enum):
    """Types of controls"""
    PREVENTIVE = "preventive"      # Stops risk before it happens
    DETECTIVE = "detective"        # Identifies risk after it occurs
    CORRECTIVE = "corrective"      # Fixes issues after detection
    COMPENSATING = "compensating"  # Offsets when primary control is weak


class EffectivenessRating(Enum):
    """Control effectiveness ratings"""
    HIGHLY_EFFECTIVE = "highly_effective"      # 90-100%
    EFFECTIVE = "effective"                    # 70-89%
    PARTIALLY_EFFECTIVE = "partially_effective"  # 50-69%
    INEFFECTIVE = "ineffective"                # 30-49%
    FAILED = "failed"                          # 0-29%


class TestResult(Enum):
    """Control test outcomes"""
    PASS = "pass"
    FAIL = "fail"
    EXCEPTION = "exception"
    NOT_TESTED = "not_tested"


@dataclass
class ControlTest:
    """A single control test instance"""
    test_id: str
    control_id: str
    test_date: datetime
    tested_by: str
    result: TestResult
    sample_size: int
    exceptions_found: int
    details: str = ""
    evidence_references: List[str] = field(default_factory=list)


@dataclass
class ControlMetrics:
    """Effectiveness metrics for a control"""
    control_id: str
    control_name: str
    control_type: ControlType

    # Effectiveness scores (0-100)
    design_effectiveness: float = 0.0
    operating_effectiveness: float = 0.0
    overall_effectiveness: float = 0.0
    effectiveness_rating: EffectivenessRating = EffectivenessRating.INEFFECTIVE

    # Test history
    total_tests: int = 0
    tests_passed: int = 0
    tests_failed: int = 0
    last_test_date: Optional[datetime] = None
    next_test_due: Optional[datetime] = None

    # Exception metrics
    total_exceptions: int = 0
    exceptions_remediated: int = 0
    avg_remediation_days: float = 0.0
    open_exceptions: int = 0

    # Trend data
    effectiveness_trend: str = "stable"  # improving, declining, stable
    trend_percentage: float = 0.0

    # Risk coverage
    risks_covered: List[str] = field(default_factory=list)
    sod_rules_mitigated: List[str] = field(default_factory=list)

    def calculate_effectiveness_rating(self) -> EffectivenessRating:
        """Calculate effectiveness rating from score"""
        score = self.overall_effectiveness
        if score >= 90:
            return EffectivenessRating.HIGHLY_EFFECTIVE
        elif score >= 70:
            return EffectivenessRating.EFFECTIVE
        elif score >= 50:
            return EffectivenessRating.PARTIALLY_EFFECTIVE
        elif score >= 30:
            return EffectivenessRating.INEFFECTIVE
        else:
            return EffectivenessRating.FAILED


@dataclass
class ApprovalQualityMetrics:
    """Metrics for approval quality analysis"""
    approver_id: str
    approver_name: str

    # Volume metrics
    total_approvals: int = 0
    total_rejections: int = 0
    total_delegations: int = 0

    # Timing metrics
    avg_decision_time_hours: float = 0.0
    fastest_decision_minutes: int = 0
    slowest_decision_hours: int = 0

    # Quality indicators
    rubber_stamp_score: float = 0.0  # 0-100, higher = more rubber stamping
    approval_rate: float = 0.0       # Percentage approved
    exception_rate: float = 0.0      # Items later revoked or flagged

    # Risk awareness
    high_risk_approved: int = 0
    high_risk_rejected: int = 0
    risk_awareness_score: float = 0.0

    # Bias indicators
    bias_detected: bool = False
    bias_type: Optional[str] = None
    bias_evidence: List[str] = field(default_factory=list)


@dataclass
class MitigationEffectiveness:
    """Effectiveness of mitigation controls"""
    mitigation_id: str
    mitigation_name: str
    associated_sod_rule: str

    # Coverage
    violations_covered: int = 0
    violations_successfully_mitigated: int = 0
    mitigation_success_rate: float = 0.0

    # Incidents
    incidents_despite_mitigation: int = 0
    incident_descriptions: List[str] = field(default_factory=list)

    # Review quality
    reviews_performed: int = 0
    issues_found_in_review: int = 0
    review_effectiveness: float = 0.0


class ControlEffectivenessEngine:
    """
    Engine for measuring and reporting control effectiveness.

    This is what auditors want to see - PROOF that controls work,
    not just documentation that they exist.
    """

    def __init__(self):
        self.control_metrics: Dict[str, ControlMetrics] = {}
        self.control_tests: Dict[str, List[ControlTest]] = {}
        self.approver_metrics: Dict[str, ApprovalQualityMetrics] = {}
        self.mitigation_effectiveness: Dict[str, MitigationEffectiveness] = {}
        self.approval_history: List[Dict] = []

    # =========================================================================
    # Control Effectiveness Scoring
    # =========================================================================

    def calculate_control_effectiveness(
        self,
        control_id: str,
        control_name: str,
        control_type: ControlType,
        test_history: List[ControlTest],
        design_score: float = 80.0
    ) -> ControlMetrics:
        """Calculate comprehensive control effectiveness"""

        metrics = ControlMetrics(
            control_id=control_id,
            control_name=control_name,
            control_type=control_type,
            design_effectiveness=design_score
        )

        if not test_history:
            metrics.overall_effectiveness = design_score * 0.5  # Untested = risky
            metrics.effectiveness_rating = metrics.calculate_effectiveness_rating()
            return metrics

        # Calculate operating effectiveness from tests
        metrics.total_tests = len(test_history)
        metrics.tests_passed = len([t for t in test_history if t.result == TestResult.PASS])
        metrics.tests_failed = len([t for t in test_history if t.result == TestResult.FAIL])

        # Pass rate
        if metrics.total_tests > 0:
            pass_rate = metrics.tests_passed / metrics.total_tests

            # Weight recent tests more heavily
            recent_tests = sorted(test_history, key=lambda t: t.test_date, reverse=True)[:5]
            recent_pass_rate = len([t for t in recent_tests if t.result == TestResult.PASS]) / len(recent_tests)

            # Operating effectiveness = weighted average
            metrics.operating_effectiveness = (pass_rate * 0.4 + recent_pass_rate * 0.6) * 100

        # Calculate exception metrics
        metrics.total_exceptions = sum(t.exceptions_found for t in test_history)
        metrics.last_test_date = max(t.test_date for t in test_history)

        # Calculate trend
        if len(test_history) >= 3:
            recent = test_history[-3:]
            older = test_history[:-3] if len(test_history) > 3 else []

            recent_rate = sum(1 for t in recent if t.result == TestResult.PASS) / len(recent)
            if older:
                older_rate = sum(1 for t in older if t.result == TestResult.PASS) / len(older)
                diff = recent_rate - older_rate
                if diff > 0.1:
                    metrics.effectiveness_trend = "improving"
                    metrics.trend_percentage = diff * 100
                elif diff < -0.1:
                    metrics.effectiveness_trend = "declining"
                    metrics.trend_percentage = diff * 100

        # Overall effectiveness = design * operating weight
        metrics.overall_effectiveness = (
            metrics.design_effectiveness * 0.3 +
            metrics.operating_effectiveness * 0.7
        )

        metrics.effectiveness_rating = metrics.calculate_effectiveness_rating()

        # Store metrics
        self.control_metrics[control_id] = metrics
        self.control_tests[control_id] = test_history

        return metrics

    def get_control_effectiveness_report(self) -> Dict:
        """Generate executive control effectiveness report"""

        metrics_list = list(self.control_metrics.values())

        if not metrics_list:
            return {"error": "No control metrics available"}

        # Calculate averages
        avg_effectiveness = statistics.mean([m.overall_effectiveness for m in metrics_list])

        # Distribution by rating
        rating_distribution = {}
        for rating in EffectivenessRating:
            count = len([m for m in metrics_list if m.effectiveness_rating == rating])
            rating_distribution[rating.value] = count

        # Controls needing attention
        attention_needed = [
            m for m in metrics_list
            if m.effectiveness_rating in [EffectivenessRating.INEFFECTIVE, EffectivenessRating.FAILED]
        ]

        # Declining controls
        declining = [m for m in metrics_list if m.effectiveness_trend == "declining"]

        return {
            "summary": {
                "total_controls": len(metrics_list),
                "average_effectiveness": round(avg_effectiveness, 1),
                "controls_highly_effective": rating_distribution.get("highly_effective", 0),
                "controls_needing_attention": len(attention_needed),
                "controls_declining": len(declining)
            },
            "distribution": rating_distribution,
            "attention_needed": [
                {
                    "control_id": m.control_id,
                    "control_name": m.control_name,
                    "effectiveness": round(m.overall_effectiveness, 1),
                    "rating": m.effectiveness_rating.value,
                    "issue": "Requires immediate remediation"
                }
                for m in attention_needed
            ],
            "declining_controls": [
                {
                    "control_id": m.control_id,
                    "control_name": m.control_name,
                    "trend_percentage": round(m.trend_percentage, 1),
                    "recommendation": "Review control design and execution"
                }
                for m in declining
            ],
            "assurance_statement": self._generate_assurance_statement(avg_effectiveness, metrics_list)
        }

    def _generate_assurance_statement(
        self,
        avg_effectiveness: float,
        metrics_list: List[ControlMetrics]
    ) -> str:
        """Generate auditor-friendly assurance statement"""

        ineffective_count = len([
            m for m in metrics_list
            if m.effectiveness_rating in [EffectivenessRating.INEFFECTIVE, EffectivenessRating.FAILED]
        ])

        if avg_effectiveness >= 85 and ineffective_count == 0:
            return (
                "Based on comprehensive testing, the control environment demonstrates "
                "STRONG effectiveness. All controls are operating as designed with "
                "no significant exceptions noted."
            )
        elif avg_effectiveness >= 70:
            return (
                f"The control environment demonstrates ADEQUATE effectiveness with an "
                f"average score of {avg_effectiveness:.0f}%. {ineffective_count} control(s) "
                f"require remediation attention."
            )
        else:
            return (
                f"MATERIAL WEAKNESSES identified in the control environment. Average "
                f"effectiveness of {avg_effectiveness:.0f}% falls below acceptable thresholds. "
                f"Immediate management attention required for {ineffective_count} controls."
            )

    # =========================================================================
    # Approval Quality Metrics
    # =========================================================================

    def record_approval_decision(
        self,
        approver_id: str,
        approver_name: str,
        request_id: str,
        decision: str,  # approved, rejected, delegated
        risk_level: str,
        decision_time_minutes: int,
        details: Dict = None
    ):
        """Record an approval decision for quality analysis"""

        self.approval_history.append({
            "approver_id": approver_id,
            "request_id": request_id,
            "decision": decision,
            "risk_level": risk_level,
            "decision_time_minutes": decision_time_minutes,
            "timestamp": datetime.utcnow().isoformat(),
            "details": details or {}
        })

        # Update approver metrics
        self._update_approver_metrics(approver_id, approver_name)

    def _update_approver_metrics(self, approver_id: str, approver_name: str):
        """Update metrics for an approver"""

        approver_history = [
            a for a in self.approval_history
            if a["approver_id"] == approver_id
        ]

        if not approver_history:
            return

        metrics = ApprovalQualityMetrics(
            approver_id=approver_id,
            approver_name=approver_name
        )

        # Volume metrics
        metrics.total_approvals = len([a for a in approver_history if a["decision"] == "approved"])
        metrics.total_rejections = len([a for a in approver_history if a["decision"] == "rejected"])
        metrics.total_delegations = len([a for a in approver_history if a["decision"] == "delegated"])

        total_decisions = len(approver_history)

        # Timing metrics
        decision_times = [a["decision_time_minutes"] for a in approver_history]
        metrics.avg_decision_time_hours = statistics.mean(decision_times) / 60
        metrics.fastest_decision_minutes = min(decision_times)
        metrics.slowest_decision_hours = max(decision_times) // 60

        # Approval rate
        if total_decisions > 0:
            metrics.approval_rate = (metrics.total_approvals / total_decisions) * 100

        # Rubber stamp detection
        metrics.rubber_stamp_score = self._calculate_rubber_stamp_score(approver_history)

        # Risk awareness
        high_risk = [a for a in approver_history if a["risk_level"] in ["high", "critical"]]
        if high_risk:
            metrics.high_risk_approved = len([a for a in high_risk if a["decision"] == "approved"])
            metrics.high_risk_rejected = len([a for a in high_risk if a["decision"] == "rejected"])
            metrics.risk_awareness_score = (metrics.high_risk_rejected / len(high_risk)) * 100

        # Bias detection
        self._detect_approval_bias(metrics, approver_history)

        self.approver_metrics[approver_id] = metrics

    def _calculate_rubber_stamp_score(self, approver_history: List[Dict]) -> float:
        """
        Calculate rubber stamp score (0-100).

        Indicators of rubber stamping:
        - Very fast decisions (< 1 minute)
        - Very high approval rate (> 95%)
        - No rejections of high-risk items
        - Consistent approval times (no variation)
        """
        score = 0.0

        if not approver_history:
            return 0.0

        decisions = len(approver_history)
        approvals = len([a for a in approver_history if a["decision"] == "approved"])
        decision_times = [a["decision_time_minutes"] for a in approver_history]

        # Very fast decisions
        very_fast = len([t for t in decision_times if t < 1])
        if very_fast / decisions > 0.5:
            score += 30

        # High approval rate
        approval_rate = approvals / decisions
        if approval_rate > 0.98:
            score += 30
        elif approval_rate > 0.95:
            score += 20

        # No variation in decision time
        if len(set(decision_times)) < 3 and decisions > 10:
            score += 20

        # High-risk items always approved
        high_risk = [a for a in approver_history if a["risk_level"] in ["high", "critical"]]
        if high_risk:
            hr_approval_rate = len([a for a in high_risk if a["decision"] == "approved"]) / len(high_risk)
            if hr_approval_rate > 0.95:
                score += 20

        return min(score, 100)

    def _detect_approval_bias(self, metrics: ApprovalQualityMetrics, history: List[Dict]):
        """Detect potential bias in approvals"""

        # Check for requestor bias
        requestors = {}
        for h in history:
            details = h.get("details", {})
            requestor = details.get("requestor_id", "unknown")
            if requestor not in requestors:
                requestors[requestor] = {"approved": 0, "rejected": 0}
            if h["decision"] == "approved":
                requestors[requestor]["approved"] += 1
            else:
                requestors[requestor]["rejected"] += 1

        # Check for significant variance
        for requestor, counts in requestors.items():
            total = counts["approved"] + counts["rejected"]
            if total >= 5:
                rate = counts["approved"] / total
                if rate > 0.95:
                    metrics.bias_detected = True
                    metrics.bias_type = "requestor_favoritism"
                    metrics.bias_evidence.append(
                        f"Requestor {requestor} has {rate*100:.0f}% approval rate"
                    )

    def get_approval_quality_report(self) -> Dict:
        """Generate approval quality report"""

        metrics_list = list(self.approver_metrics.values())

        if not metrics_list:
            return {"error": "No approval data available"}

        # Identify rubber stampers
        rubber_stampers = [
            m for m in metrics_list
            if m.rubber_stamp_score > 60
        ]

        # Low risk awareness
        low_awareness = [
            m for m in metrics_list
            if m.risk_awareness_score < 30 and m.total_approvals > 10
        ]

        # Biased approvers
        biased = [m for m in metrics_list if m.bias_detected]

        return {
            "summary": {
                "total_approvers_analyzed": len(metrics_list),
                "rubber_stamp_alerts": len(rubber_stampers),
                "low_risk_awareness_alerts": len(low_awareness),
                "bias_alerts": len(biased)
            },
            "rubber_stamp_concerns": [
                {
                    "approver_id": m.approver_id,
                    "approver_name": m.approver_name,
                    "rubber_stamp_score": round(m.rubber_stamp_score, 1),
                    "approval_rate": round(m.approval_rate, 1),
                    "avg_decision_time": f"{m.avg_decision_time_hours:.1f} hours",
                    "recommendation": "Requires coaching on approval responsibilities"
                }
                for m in rubber_stampers
            ],
            "risk_awareness_concerns": [
                {
                    "approver_id": m.approver_id,
                    "risk_awareness_score": round(m.risk_awareness_score, 1),
                    "high_risk_approved": m.high_risk_approved,
                    "high_risk_rejected": m.high_risk_rejected,
                    "recommendation": "Training on risk assessment required"
                }
                for m in low_awareness
            ],
            "bias_concerns": [
                {
                    "approver_id": m.approver_id,
                    "bias_type": m.bias_type,
                    "evidence": m.bias_evidence,
                    "recommendation": "Review approval patterns with compliance"
                }
                for m in biased
            ],
            "audit_opinion": self._generate_approval_quality_opinion(
                len(rubber_stampers), len(low_awareness), len(biased), len(metrics_list)
            )
        }

    def _generate_approval_quality_opinion(
        self,
        rubber_stampers: int,
        low_awareness: int,
        biased: int,
        total: int
    ) -> str:
        """Generate opinion on approval quality"""

        if total == 0:
            return "Insufficient data for assessment."

        concern_ratio = (rubber_stampers + low_awareness + biased) / total

        if concern_ratio < 0.1:
            return (
                "Approval processes demonstrate STRONG governance. Approvers are "
                "exercising appropriate judgment and risk awareness."
            )
        elif concern_ratio < 0.25:
            return (
                "Approval processes are ADEQUATE with some areas requiring attention. "
                f"{rubber_stampers + low_awareness + biased} approver(s) should receive "
                "additional guidance on approval responsibilities."
            )
        else:
            return (
                "SIGNIFICANT CONCERNS identified in approval quality. A high proportion "
                "of approvers show signs of rubber-stamping or inadequate risk assessment. "
                "Recommend immediate review of approval delegation and training programs."
            )

    # =========================================================================
    # Mitigation Effectiveness
    # =========================================================================

    def measure_mitigation_effectiveness(
        self,
        mitigation_id: str,
        mitigation_name: str,
        sod_rule: str,
        violations_covered: int,
        incidents_occurred: int,
        reviews_performed: int,
        issues_in_review: int
    ) -> MitigationEffectiveness:
        """Measure effectiveness of a mitigation control"""

        eff = MitigationEffectiveness(
            mitigation_id=mitigation_id,
            mitigation_name=mitigation_name,
            associated_sod_rule=sod_rule,
            violations_covered=violations_covered,
            incidents_despite_mitigation=incidents_occurred,
            reviews_performed=reviews_performed,
            issues_found_in_review=issues_in_review
        )

        # Calculate success rate
        if violations_covered > 0:
            eff.violations_successfully_mitigated = violations_covered - incidents_occurred
            eff.mitigation_success_rate = (eff.violations_successfully_mitigated / violations_covered) * 100

        # Calculate review effectiveness
        if reviews_performed > 0:
            # Higher issues found = more effective review (catching problems)
            # But balance with success rate
            eff.review_effectiveness = min(
                (issues_in_review / reviews_performed * 50) + (eff.mitigation_success_rate / 2),
                100
            )

        self.mitigation_effectiveness[mitigation_id] = eff
        return eff

    def get_mitigation_effectiveness_report(self) -> Dict:
        """Generate mitigation effectiveness report"""

        mitigations = list(self.mitigation_effectiveness.values())

        if not mitigations:
            return {"error": "No mitigation data available"}

        avg_success_rate = statistics.mean([m.mitigation_success_rate for m in mitigations])

        ineffective = [m for m in mitigations if m.mitigation_success_rate < 70]
        failed_mitigations = [m for m in mitigations if m.incidents_despite_mitigation > 0]

        return {
            "summary": {
                "total_mitigations": len(mitigations),
                "average_success_rate": round(avg_success_rate, 1),
                "ineffective_mitigations": len(ineffective),
                "mitigations_with_incidents": len(failed_mitigations)
            },
            "ineffective_mitigations": [
                {
                    "mitigation_id": m.mitigation_id,
                    "mitigation_name": m.mitigation_name,
                    "sod_rule": m.associated_sod_rule,
                    "success_rate": round(m.mitigation_success_rate, 1),
                    "incidents": m.incidents_despite_mitigation,
                    "recommendation": "Redesign or strengthen mitigation control"
                }
                for m in ineffective
            ],
            "incidents_despite_mitigation": [
                {
                    "mitigation_id": m.mitigation_id,
                    "incidents": m.incidents_despite_mitigation,
                    "descriptions": m.incident_descriptions
                }
                for m in failed_mitigations
            ]
        }

    # =========================================================================
    # Executive Dashboard
    # =========================================================================

    def get_assurance_dashboard(self) -> Dict:
        """Get executive assurance dashboard"""

        control_report = self.get_control_effectiveness_report()
        approval_report = self.get_approval_quality_report()
        mitigation_report = self.get_mitigation_effectiveness_report()

        # Calculate overall assurance score
        scores = []
        if "summary" in control_report and "average_effectiveness" in control_report["summary"]:
            scores.append(control_report["summary"]["average_effectiveness"])
        if "summary" in mitigation_report and "average_success_rate" in mitigation_report["summary"]:
            scores.append(mitigation_report["summary"]["average_success_rate"])

        overall_assurance = statistics.mean(scores) if scores else 0

        return {
            "overall_assurance_score": round(overall_assurance, 1),
            "overall_rating": self._get_assurance_rating(overall_assurance),
            "control_effectiveness": control_report.get("summary", {}),
            "approval_quality": approval_report.get("summary", {}),
            "mitigation_effectiveness": mitigation_report.get("summary", {}),
            "key_risks": self._identify_key_risks(control_report, approval_report, mitigation_report),
            "recommendations": self._generate_recommendations(control_report, approval_report, mitigation_report),
            "generated_at": datetime.utcnow().isoformat()
        }

    def _get_assurance_rating(self, score: float) -> str:
        """Get assurance rating from score"""
        if score >= 90:
            return "STRONG"
        elif score >= 70:
            return "ADEQUATE"
        elif score >= 50:
            return "NEEDS IMPROVEMENT"
        else:
            return "MATERIAL WEAKNESS"

    def _identify_key_risks(self, control_report: Dict, approval_report: Dict, mitigation_report: Dict) -> List[str]:
        """Identify key risks from reports"""
        risks = []

        if control_report.get("summary", {}).get("controls_needing_attention", 0) > 0:
            risks.append("Controls with low effectiveness require immediate attention")

        if approval_report.get("summary", {}).get("rubber_stamp_alerts", 0) > 0:
            risks.append("Approval rubber-stamping detected - governance may be ineffective")

        if mitigation_report.get("summary", {}).get("mitigations_with_incidents", 0) > 0:
            risks.append("SoD mitigations have failed to prevent incidents")

        return risks

    def _generate_recommendations(self, control_report: Dict, approval_report: Dict, mitigation_report: Dict) -> List[str]:
        """Generate prioritized recommendations"""
        recommendations = []

        # Control recommendations
        if control_report.get("attention_needed"):
            recommendations.append(
                f"PRIORITY 1: Remediate {len(control_report['attention_needed'])} ineffective controls"
            )

        # Approval recommendations
        if approval_report.get("rubber_stamp_concerns"):
            recommendations.append(
                f"PRIORITY 2: Address approval quality concerns for {len(approval_report['rubber_stamp_concerns'])} approvers"
            )

        # Mitigation recommendations
        if mitigation_report.get("ineffective_mitigations"):
            recommendations.append(
                f"PRIORITY 3: Strengthen {len(mitigation_report['ineffective_mitigations'])} ineffective mitigations"
            )

        return recommendations
