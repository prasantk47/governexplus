# Approver Optimizer
# AI-assisted approver selection and optimization

"""
Approver Optimizer for GOVERNEX+.

AI does selection optimization, not decision-making:
- Who approves similar requests fastest?
- Who rejects risky requests appropriately?
- Who causes SLA delays?
- Who is currently overloaded?
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from enum import Enum
import logging
from collections import defaultdict

from .models import Approver, ApproverType, ApprovalDecision, ApprovalStatus

logger = logging.getLogger(__name__)


@dataclass
class ApproverMetrics:
    """Performance metrics for an approver."""
    approver_id: str
    approver_name: str
    approver_type: ApproverType

    # Volume
    total_decisions: int = 0
    decisions_last_30_days: int = 0
    current_queue_size: int = 0

    # Speed
    avg_response_hours: float = 0.0
    median_response_hours: float = 0.0
    sla_compliance_rate: float = 100.0

    # Quality
    approval_rate: float = 0.0
    rejection_rate: float = 0.0
    override_rate: float = 0.0  # How often they override AI recommendations

    # Risk awareness
    high_risk_approval_rate: float = 0.0
    appropriate_rejection_rate: float = 0.0  # Rejected and later confirmed risky

    # Availability
    avg_availability_hours: float = 40.0
    current_load: float = 0.0  # 0-100%

    def to_dict(self) -> Dict[str, Any]:
        return {
            "approver_id": self.approver_id,
            "approver_name": self.approver_name,
            "approver_type": self.approver_type.value,
            "total_decisions": self.total_decisions,
            "current_queue_size": self.current_queue_size,
            "avg_response_hours": round(self.avg_response_hours, 1),
            "sla_compliance_rate": round(self.sla_compliance_rate, 1),
            "approval_rate": round(self.approval_rate, 1),
            "current_load": round(self.current_load, 1),
        }


@dataclass
class ApproverScore:
    """
    Composite score for an approver.

    Used to rank approvers for selection.
    """
    approver_id: str
    approver_name: str

    # Component scores (0-100)
    speed_score: float = 50.0
    quality_score: float = 50.0
    availability_score: float = 50.0
    relevance_score: float = 50.0

    # Composite
    overall_score: float = 50.0
    confidence: float = 0.5

    # Explanation
    strengths: List[str] = field(default_factory=list)
    concerns: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "approver_id": self.approver_id,
            "approver_name": self.approver_name,
            "overall_score": round(self.overall_score, 1),
            "confidence": round(self.confidence, 2),
            "component_scores": {
                "speed": round(self.speed_score, 1),
                "quality": round(self.quality_score, 1),
                "availability": round(self.availability_score, 1),
                "relevance": round(self.relevance_score, 1),
            },
            "strengths": self.strengths,
            "concerns": self.concerns,
        }


@dataclass
class OptimizationResult:
    """
    Result of approver optimization.

    Includes recommendation and explanation.
    """
    recommended_approver: Approver
    confidence: float
    reason: List[str]

    # Alternatives
    alternatives: List[Tuple[Approver, ApproverScore]] = field(default_factory=list)

    # Comparison
    vs_default: str = ""  # Why this is better than default

    # Warning
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "recommended_approver": self.recommended_approver.to_dict(),
            "confidence": round(self.confidence, 2),
            "reason": self.reason,
            "alternatives": [
                {
                    "approver": a.to_dict(),
                    "score": s.to_dict(),
                }
                for a, s in self.alternatives
            ],
            "vs_default": self.vs_default,
            "warnings": self.warnings,
        }


class ApproverOptimizer:
    """
    Optimizes approver selection using historical data.

    Key signals:
    - Response time patterns
    - Decision quality
    - Workload distribution
    - Risk awareness
    """

    def __init__(self):
        """Initialize optimizer."""
        self._metrics: Dict[str, ApproverMetrics] = {}
        self._decision_history: List[ApprovalDecision] = []
        self._weights = {
            "speed": 0.25,
            "quality": 0.30,
            "availability": 0.25,
            "relevance": 0.20,
        }

    def record_decision(self, decision: ApprovalDecision) -> None:
        """Record a decision for learning."""
        self._decision_history.append(decision)
        self._update_metrics(decision)

    def _update_metrics(self, decision: ApprovalDecision) -> None:
        """Update approver metrics based on decision."""
        approver_id = decision.approver_id

        if approver_id not in self._metrics:
            self._metrics[approver_id] = ApproverMetrics(
                approver_id=approver_id,
                approver_name="",
                approver_type=decision.approver_type,
            )

        metrics = self._metrics[approver_id]
        metrics.total_decisions += 1

        # Update response time
        if decision.response_time_hours > 0:
            # Running average
            n = metrics.total_decisions
            metrics.avg_response_hours = (
                (metrics.avg_response_hours * (n - 1) + decision.response_time_hours) / n
            )

        # Update SLA compliance
        if decision.within_sla:
            compliant = int(metrics.sla_compliance_rate * (n - 1) / 100) + 1
            metrics.sla_compliance_rate = compliant / n * 100
        else:
            compliant = int(metrics.sla_compliance_rate * (n - 1) / 100)
            metrics.sla_compliance_rate = compliant / n * 100

        # Update approval/rejection rates
        if decision.status == ApprovalStatus.APPROVED:
            approved = int(metrics.approval_rate * (n - 1) / 100) + 1
            metrics.approval_rate = approved / n * 100
        elif decision.status == ApprovalStatus.REJECTED:
            rejected = int(metrics.rejection_rate * (n - 1) / 100) + 1
            metrics.rejection_rate = rejected / n * 100

    def get_metrics(self, approver_id: str) -> Optional[ApproverMetrics]:
        """Get metrics for an approver."""
        return self._metrics.get(approver_id)

    def score_approver(
        self,
        approver: Approver,
        request_context: Optional[Dict[str, Any]] = None
    ) -> ApproverScore:
        """
        Calculate composite score for an approver.

        Args:
            approver: The approver to score
            request_context: Optional context for relevance scoring

        Returns:
            ApproverScore with component and overall scores
        """
        score = ApproverScore(
            approver_id=approver.approver_id,
            approver_name=approver.approver_name,
        )

        metrics = self._metrics.get(approver.approver_id)

        # Speed score (faster = better)
        if metrics and metrics.avg_response_hours > 0:
            # Normalize: 4 hours = 100, 24 hours = 50, 72 hours = 0
            if metrics.avg_response_hours <= 4:
                score.speed_score = 100
            elif metrics.avg_response_hours <= 24:
                score.speed_score = 100 - (metrics.avg_response_hours - 4) * 2.5
            else:
                score.speed_score = max(0, 50 - (metrics.avg_response_hours - 24))

            if score.speed_score >= 80:
                score.strengths.append(f"Fast responder ({metrics.avg_response_hours:.1f}h avg)")
            elif score.speed_score < 40:
                score.concerns.append(f"Slow response time ({metrics.avg_response_hours:.1f}h avg)")
        else:
            score.speed_score = 50  # Default when no data

        # Quality score (SLA compliance + appropriate decisions)
        if metrics:
            score.quality_score = metrics.sla_compliance_rate * 0.7 + 30

            if metrics.sla_compliance_rate >= 95:
                score.strengths.append("Excellent SLA compliance")
            elif metrics.sla_compliance_rate < 80:
                score.concerns.append(f"SLA compliance issue ({metrics.sla_compliance_rate:.0f}%)")
        else:
            score.quality_score = 50

        # Availability score
        if approver.is_ooo:
            score.availability_score = 0
            score.concerns.append("Currently out of office")
        elif not approver.is_available:
            score.availability_score = 20
            score.concerns.append("Limited availability")
        else:
            # Consider queue size
            queue = approver.current_queue_size
            if queue <= 3:
                score.availability_score = 100
            elif queue <= 10:
                score.availability_score = 80 - (queue - 3) * 5
            else:
                score.availability_score = max(20, 50 - queue)

            if queue == 0:
                score.strengths.append("No pending queue")
            elif queue > 10:
                score.concerns.append(f"High queue ({queue} pending)")

        # Relevance score (process/system match)
        if request_context:
            process = request_context.get("business_process", "")
            system = request_context.get("system_id", "")

            relevance = 50
            if process and process in approver.process_scope:
                relevance += 25
                score.strengths.append(f"Owns {process} process")
            if system and system in approver.system_scope:
                relevance += 25

            score.relevance_score = relevance
        else:
            score.relevance_score = 50

        # Calculate overall score (weighted)
        score.overall_score = (
            score.speed_score * self._weights["speed"] +
            score.quality_score * self._weights["quality"] +
            score.availability_score * self._weights["availability"] +
            score.relevance_score * self._weights["relevance"]
        )

        # Calculate confidence based on data quality
        if metrics and metrics.total_decisions >= 50:
            score.confidence = 0.9
        elif metrics and metrics.total_decisions >= 20:
            score.confidence = 0.7
        elif metrics and metrics.total_decisions >= 5:
            score.confidence = 0.5
        else:
            score.confidence = 0.3

        return score

    def optimize(
        self,
        candidates: List[Approver],
        request_context: Optional[Dict[str, Any]] = None
    ) -> OptimizationResult:
        """
        Select optimal approver from candidates.

        Args:
            candidates: Potential approvers
            request_context: Request context for relevance

        Returns:
            OptimizationResult with recommendation
        """
        if not candidates:
            raise ValueError("No candidates provided")

        # Score all candidates
        scored = []
        for approver in candidates:
            score = self.score_approver(approver, request_context)
            scored.append((approver, score))

        # Sort by overall score
        scored.sort(key=lambda x: x[1].overall_score, reverse=True)

        best_approver, best_score = scored[0]

        # Build reasons
        reasons = []
        if best_score.strengths:
            reasons.extend(best_score.strengths)
        reasons.append(f"Overall score: {best_score.overall_score:.0f}/100")

        # Get alternatives
        alternatives = scored[1:4]  # Top 3 alternatives

        # Compare to default (first candidate)
        default = candidates[0]
        if best_approver.approver_id != default.approver_id:
            default_score = next(
                (s for a, s in scored if a.approver_id == default.approver_id),
                None
            )
            if default_score:
                improvement = best_score.overall_score - default_score.overall_score
                vs_default = f"Score {improvement:.0f} points higher than default approver"
            else:
                vs_default = "Better match based on performance history"
        else:
            vs_default = "Default approver is optimal choice"

        # Collect warnings
        warnings = []
        if best_score.concerns:
            warnings.extend(best_score.concerns)
        if best_score.confidence < 0.5:
            warnings.append("Limited historical data for confidence")

        return OptimizationResult(
            recommended_approver=best_approver,
            confidence=best_score.confidence,
            reason=reasons,
            alternatives=alternatives,
            vs_default=vs_default,
            warnings=warnings,
        )

    def predict_response_time(
        self,
        approver: Approver
    ) -> Dict[str, Any]:
        """Predict response time for an approver."""
        metrics = self._metrics.get(approver.approver_id)

        if not metrics:
            return {
                "predicted_hours": 24.0,
                "confidence": "LOW",
                "range": {"min": 4, "max": 72},
            }

        # Use historical average with adjustment for current load
        predicted = metrics.avg_response_hours
        if approver.current_queue_size > 5:
            predicted *= 1.5

        return {
            "predicted_hours": round(predicted, 1),
            "confidence": "HIGH" if metrics.total_decisions >= 20 else "MEDIUM",
            "range": {
                "min": max(1, predicted * 0.5),
                "max": predicted * 2,
            },
        }

    def get_workload_distribution(self) -> Dict[str, Any]:
        """Get workload distribution across approvers."""
        distribution = {}

        for approver_id, metrics in self._metrics.items():
            distribution[approver_id] = {
                "current_queue": metrics.current_queue_size,
                "decisions_30d": metrics.decisions_last_30_days,
                "avg_response": metrics.avg_response_hours,
                "load_percent": metrics.current_load,
            }

        return distribution

    def rebalance_suggestions(
        self,
        approvers: List[Approver]
    ) -> List[Dict[str, Any]]:
        """
        Suggest workload rebalancing.

        Returns suggestions for redistributing work.
        """
        suggestions = []

        # Find overloaded and underloaded
        overloaded = []
        underloaded = []

        for approver in approvers:
            metrics = self._metrics.get(approver.approver_id)
            if not metrics:
                continue

            if metrics.current_queue_size > 10:
                overloaded.append((approver, metrics))
            elif metrics.current_queue_size < 3 and approver.is_available:
                underloaded.append((approver, metrics))

        # Generate suggestions
        for over_approver, over_metrics in overloaded:
            for under_approver, under_metrics in underloaded:
                if over_approver.approver_type == under_approver.approver_type:
                    suggestions.append({
                        "action": "REDISTRIBUTE",
                        "from": over_approver.approver_id,
                        "to": under_approver.approver_id,
                        "reason": f"{over_approver.approver_name} has {over_metrics.current_queue_size} pending, {under_approver.approver_name} has capacity",
                    })

        return suggestions

    def generate_performance_report(self) -> Dict[str, Any]:
        """Generate performance report for all approvers."""
        report = {
            "generated_at": datetime.now().isoformat(),
            "total_approvers": len(self._metrics),
            "total_decisions": sum(m.total_decisions for m in self._metrics.values()),
            "approvers": [],
        }

        for approver_id, metrics in self._metrics.items():
            report["approvers"].append({
                "approver_id": approver_id,
                "type": metrics.approver_type.value,
                "total_decisions": metrics.total_decisions,
                "avg_response_hours": round(metrics.avg_response_hours, 1),
                "sla_compliance": round(metrics.sla_compliance_rate, 1),
                "approval_rate": round(metrics.approval_rate, 1),
            })

        # Sort by decisions
        report["approvers"].sort(key=lambda x: x["total_decisions"], reverse=True)

        # Top performers
        by_sla = sorted(report["approvers"], key=lambda x: x["sla_compliance"], reverse=True)
        report["top_sla_performers"] = [a["approver_id"] for a in by_sla[:5]]

        by_speed = sorted(report["approvers"], key=lambda x: x["avg_response_hours"])
        report["fastest_responders"] = [a["approver_id"] for a in by_speed[:5]]

        return report
