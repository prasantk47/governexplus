# Control Monitoring Dashboard
# Real-time visibility into control effectiveness

"""
Control Monitoring for CCM.

Provides:
- Real-time control status
- Health scores
- Trend analysis
- Audit-ready dashboards
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from collections import defaultdict
import logging

from .controls import Control, ControlStatus, ControlType
from .engine import ControlEvaluationResult, ControlViolation

logger = logging.getLogger(__name__)


@dataclass
class ControlHealthScore:
    """Health score for a control."""
    control_id: str
    score: float  # 0-100
    status: str  # "HEALTHY", "WARNING", "CRITICAL"

    # Components
    pass_rate: float  # % of evaluations that passed
    mttr_hours: float  # Mean time to resolve violations
    violation_trend: str  # "improving", "stable", "deteriorating"

    # Recent history
    evaluations_30d: int = 0
    failures_30d: int = 0
    open_violations: int = 0

    calculated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "control_id": self.control_id,
            "score": round(self.score, 2),
            "status": self.status,
            "pass_rate": round(self.pass_rate, 4),
            "mttr_hours": round(self.mttr_hours, 2),
            "violation_trend": self.violation_trend,
            "evaluations_30d": self.evaluations_30d,
            "failures_30d": self.failures_30d,
            "open_violations": self.open_violations,
            "calculated_at": self.calculated_at.isoformat(),
        }


@dataclass
class ControlMetrics:
    """Aggregate metrics for all controls."""
    # Overall
    total_controls: int = 0
    active_controls: int = 0
    healthy_controls: int = 0
    warning_controls: int = 0
    critical_controls: int = 0

    # Performance
    overall_pass_rate: float = 0.0
    avg_mttr_hours: float = 0.0
    evaluations_today: int = 0
    violations_today: int = 0

    # By type
    by_type: Dict[str, Dict[str, int]] = field(default_factory=dict)

    # Trend
    pass_rate_trend: str = "stable"  # "improving", "stable", "deteriorating"
    violations_trend: str = "stable"

    # Calculated
    calculated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_controls": self.total_controls,
            "active_controls": self.active_controls,
            "healthy_controls": self.healthy_controls,
            "warning_controls": self.warning_controls,
            "critical_controls": self.critical_controls,
            "overall_pass_rate": round(self.overall_pass_rate, 4),
            "avg_mttr_hours": round(self.avg_mttr_hours, 2),
            "evaluations_today": self.evaluations_today,
            "violations_today": self.violations_today,
            "by_type": self.by_type,
            "pass_rate_trend": self.pass_rate_trend,
            "violations_trend": self.violations_trend,
            "calculated_at": self.calculated_at.isoformat(),
        }


@dataclass
class MonitoringDashboard:
    """Complete monitoring dashboard data."""
    # Summary
    metrics: ControlMetrics = field(default_factory=ControlMetrics)

    # Health scores by control
    health_scores: List[ControlHealthScore] = field(default_factory=list)

    # Top issues
    critical_controls: List[Dict[str, Any]] = field(default_factory=list)
    recent_violations: List[Dict[str, Any]] = field(default_factory=list)

    # Trends
    daily_pass_rates: List[Dict[str, Any]] = field(default_factory=list)
    daily_violations: List[Dict[str, Any]] = field(default_factory=list)

    # Generated
    generated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "metrics": self.metrics.to_dict(),
            "health_scores": [h.to_dict() for h in self.health_scores],
            "critical_controls": self.critical_controls,
            "recent_violations": self.recent_violations,
            "daily_pass_rates": self.daily_pass_rates,
            "daily_violations": self.daily_violations,
            "generated_at": self.generated_at.isoformat(),
        }


class ControlMonitor:
    """
    Monitors control effectiveness continuously.

    Key capabilities:
    - Calculate health scores
    - Track trends
    - Generate dashboards
    - Identify at-risk controls
    """

    # Health thresholds
    HEALTHY_THRESHOLD = 90
    WARNING_THRESHOLD = 70

    def __init__(self):
        """Initialize monitor."""
        # Evaluation history
        self._evaluations: List[ControlEvaluationResult] = []
        self._violations: List[ControlViolation] = []
        self._max_history = 10000

    def record_evaluation(self, result: ControlEvaluationResult):
        """Record an evaluation result."""
        self._evaluations.append(result)

        # Record violations
        self._violations.extend(result.violations)

        # Trim history
        if len(self._evaluations) > self._max_history:
            self._evaluations = self._evaluations[-self._max_history:]

        if len(self._violations) > self._max_history * 10:
            self._violations = self._violations[-self._max_history * 10:]

    def calculate_health_score(
        self,
        control_id: str,
        days: int = 30
    ) -> ControlHealthScore:
        """Calculate health score for a control."""
        cutoff = datetime.now() - timedelta(days=days)

        # Get recent evaluations for this control
        recent = [
            e for e in self._evaluations
            if e.control_id == control_id and e.evaluation_started >= cutoff
        ]

        if not recent:
            return ControlHealthScore(
                control_id=control_id,
                score=100,
                status="HEALTHY",
                pass_rate=1.0,
                mttr_hours=0,
                violation_trend="stable",
            )

        # Calculate pass rate
        passed = sum(1 for e in recent if e.passed)
        pass_rate = passed / len(recent)

        # Count failures
        failures = len(recent) - passed

        # Get open violations
        open_violations = sum(
            1 for v in self._violations
            if v.control_id == control_id and not v.resolved
        )

        # Calculate MTTR (simplified)
        resolved = [
            v for v in self._violations
            if v.control_id == control_id and v.resolved and v.resolved_at
        ]
        if resolved:
            total_hours = sum(
                (v.resolved_at - v.detected_at).total_seconds() / 3600
                for v in resolved
            )
            mttr = total_hours / len(resolved)
        else:
            mttr = 0

        # Determine trend
        if len(recent) >= 10:
            first_half = recent[:len(recent)//2]
            second_half = recent[len(recent)//2:]

            first_pass_rate = sum(1 for e in first_half if e.passed) / len(first_half)
            second_pass_rate = sum(1 for e in second_half if e.passed) / len(second_half)

            if second_pass_rate > first_pass_rate + 0.05:
                trend = "improving"
            elif second_pass_rate < first_pass_rate - 0.05:
                trend = "deteriorating"
            else:
                trend = "stable"
        else:
            trend = "stable"

        # Calculate score
        score = pass_rate * 100

        # Adjust for open violations
        if open_violations > 0:
            score = max(0, score - open_violations * 5)

        # Adjust for MTTR
        if mttr > 48:  # More than 48 hours MTTR
            score = max(0, score - 10)

        # Determine status
        if score >= self.HEALTHY_THRESHOLD:
            status = "HEALTHY"
        elif score >= self.WARNING_THRESHOLD:
            status = "WARNING"
        else:
            status = "CRITICAL"

        return ControlHealthScore(
            control_id=control_id,
            score=score,
            status=status,
            pass_rate=pass_rate,
            mttr_hours=mttr,
            violation_trend=trend,
            evaluations_30d=len(recent),
            failures_30d=failures,
            open_violations=open_violations,
        )

    def calculate_metrics(
        self,
        controls: List[Control]
    ) -> ControlMetrics:
        """Calculate aggregate metrics for all controls."""
        metrics = ControlMetrics()
        metrics.total_controls = len(controls)
        metrics.active_controls = sum(
            1 for c in controls if c.status == ControlStatus.ACTIVE
        )

        # Calculate health scores
        health_scores = []
        for control in controls:
            score = self.calculate_health_score(control.control_id)
            health_scores.append(score)

        # Aggregate by status
        metrics.healthy_controls = sum(1 for h in health_scores if h.status == "HEALTHY")
        metrics.warning_controls = sum(1 for h in health_scores if h.status == "WARNING")
        metrics.critical_controls = sum(1 for h in health_scores if h.status == "CRITICAL")

        # Overall pass rate
        if health_scores:
            metrics.overall_pass_rate = sum(h.pass_rate for h in health_scores) / len(health_scores)
            metrics.avg_mttr_hours = sum(h.mttr_hours for h in health_scores) / len(health_scores)

        # Today's stats
        today = datetime.now().date()
        today_evals = [
            e for e in self._evaluations
            if e.evaluation_started.date() == today
        ]
        metrics.evaluations_today = len(today_evals)
        metrics.violations_today = sum(e.violations_found for e in today_evals)

        # By type
        for control_type in ControlType:
            type_controls = [c for c in controls if c.control_type == control_type]
            type_health = [
                h for h in health_scores
                if any(c.control_id == h.control_id for c in type_controls)
            ]
            metrics.by_type[control_type.value] = {
                "total": len(type_controls),
                "healthy": sum(1 for h in type_health if h.status == "HEALTHY"),
            }

        return metrics

    def generate_dashboard(
        self,
        controls: List[Control],
        days: int = 30
    ) -> MonitoringDashboard:
        """Generate complete monitoring dashboard."""
        dashboard = MonitoringDashboard()

        # Calculate metrics
        dashboard.metrics = self.calculate_metrics(controls)

        # Calculate health scores for each control
        for control in controls:
            score = self.calculate_health_score(control.control_id, days)
            dashboard.health_scores.append(score)

        # Sort health scores by score (worst first)
        dashboard.health_scores.sort(key=lambda h: h.score)

        # Critical controls
        dashboard.critical_controls = [
            {"control_id": h.control_id, "score": h.score, "open_violations": h.open_violations}
            for h in dashboard.health_scores
            if h.status == "CRITICAL"
        ][:10]

        # Recent violations
        recent_violations = sorted(
            self._violations,
            key=lambda v: v.detected_at,
            reverse=True
        )[:20]
        dashboard.recent_violations = [v.to_dict() for v in recent_violations]

        # Daily trends
        cutoff = datetime.now() - timedelta(days=days)
        daily_evals = defaultdict(list)

        for e in self._evaluations:
            if e.evaluation_started >= cutoff:
                date_str = e.evaluation_started.date().isoformat()
                daily_evals[date_str].append(e)

        for date_str in sorted(daily_evals.keys()):
            evals = daily_evals[date_str]
            passed = sum(1 for e in evals if e.passed)
            pass_rate = passed / len(evals) if evals else 1.0
            violations = sum(e.violations_found for e in evals)

            dashboard.daily_pass_rates.append({
                "date": date_str,
                "pass_rate": round(pass_rate, 4),
                "evaluations": len(evals),
            })
            dashboard.daily_violations.append({
                "date": date_str,
                "violations": violations,
            })

        return dashboard

    def get_at_risk_controls(
        self,
        controls: List[Control],
        threshold: float = 70
    ) -> List[ControlHealthScore]:
        """Get controls that are at risk (below threshold)."""
        at_risk = []

        for control in controls:
            score = self.calculate_health_score(control.control_id)
            if score.score < threshold:
                at_risk.append(score)

        return sorted(at_risk, key=lambda h: h.score)

    def get_open_violations(
        self,
        control_id: Optional[str] = None
    ) -> List[ControlViolation]:
        """Get open (unresolved) violations."""
        violations = [v for v in self._violations if not v.resolved]

        if control_id:
            violations = [v for v in violations if v.control_id == control_id]

        return sorted(violations, key=lambda v: v.detected_at, reverse=True)

    def resolve_violation(
        self,
        violation_id: str,
        resolved_by: str,
        notes: str = ""
    ):
        """Mark a violation as resolved."""
        for violation in self._violations:
            if violation.violation_id == violation_id:
                violation.resolved = True
                violation.resolved_at = datetime.now()
                violation.resolved_by = resolved_by
                violation.resolution_notes = notes
                break
