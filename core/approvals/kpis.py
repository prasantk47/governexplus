# Approval KPIs and SLA Tracking
# Performance metrics for approval workflows

"""
Approval KPIs for GOVERNEX+.

Tracks:
- SLA compliance
- Approval velocity
- Bottleneck detection
- Risk vs speed trade-offs
- Approver performance
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from enum import Enum
import logging
from collections import defaultdict

from .models import ApprovalStatus, ApproverType

logger = logging.getLogger(__name__)


class KPICategory(Enum):
    """Categories of approval KPIs."""
    EFFICIENCY = "EFFICIENCY"       # Speed and throughput
    COMPLIANCE = "COMPLIANCE"       # SLA adherence
    QUALITY = "QUALITY"             # Decision quality
    RISK = "RISK"                   # Risk management
    EXPERIENCE = "EXPERIENCE"       # User experience


class TrendDirection(Enum):
    """Direction of KPI trend."""
    IMPROVING = "IMPROVING"
    STABLE = "STABLE"
    DECLINING = "DECLINING"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


@dataclass
class KPIDefinition:
    """Definition of a KPI metric."""
    kpi_id: str
    name: str
    description: str
    category: KPICategory
    unit: str
    target: float
    warning_threshold: float
    critical_threshold: float
    higher_is_better: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "kpi_id": self.kpi_id,
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
            "unit": self.unit,
            "target": self.target,
            "warning_threshold": self.warning_threshold,
            "critical_threshold": self.critical_threshold,
            "higher_is_better": self.higher_is_better,
        }


@dataclass
class KPIValue:
    """Current value of a KPI."""
    kpi_id: str
    value: float
    target: float
    status: str  # ON_TARGET, WARNING, CRITICAL
    trend: TrendDirection
    trend_value: float  # % change
    measured_at: datetime = field(default_factory=datetime.now)
    sample_size: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "kpi_id": self.kpi_id,
            "value": round(self.value, 2),
            "target": self.target,
            "status": self.status,
            "trend": self.trend.value,
            "trend_value": round(self.trend_value, 1),
            "measured_at": self.measured_at.isoformat(),
            "sample_size": self.sample_size,
        }


@dataclass
class SLABreach:
    """Record of an SLA breach."""
    request_id: str
    approver_id: str
    expected_hours: float
    actual_hours: float
    breach_hours: float  # How much over SLA
    breach_severity: str  # MINOR (<1h), MODERATE (1-4h), SEVERE (>4h)
    root_cause: str
    occurred_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "approver_id": self.approver_id,
            "expected_hours": self.expected_hours,
            "actual_hours": round(self.actual_hours, 1),
            "breach_hours": round(self.breach_hours, 1),
            "breach_severity": self.breach_severity,
            "root_cause": self.root_cause,
            "occurred_at": self.occurred_at.isoformat(),
        }


@dataclass
class BottleneckReport:
    """Report on approval bottlenecks."""
    approver_id: str
    approver_name: str
    approver_type: ApproverType
    avg_queue_size: float
    avg_wait_hours: float
    breach_rate: float
    is_bottleneck: bool
    recommendations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "approver_id": self.approver_id,
            "approver_name": self.approver_name,
            "approver_type": self.approver_type.value,
            "avg_queue_size": round(self.avg_queue_size, 1),
            "avg_wait_hours": round(self.avg_wait_hours, 1),
            "breach_rate": round(self.breach_rate, 1),
            "is_bottleneck": self.is_bottleneck,
            "recommendations": self.recommendations,
        }


# ============================================================
# KPI DEFINITIONS
# ============================================================

APPROVAL_KPIS = [
    # Efficiency KPIs
    KPIDefinition(
        kpi_id="APR-EFF-001",
        name="Average Approval Time",
        description="Average time from submission to final approval",
        category=KPICategory.EFFICIENCY,
        unit="hours",
        target=8.0,
        warning_threshold=16.0,
        critical_threshold=24.0,
        higher_is_better=False,
    ),
    KPIDefinition(
        kpi_id="APR-EFF-002",
        name="Same-Day Approval Rate",
        description="Percentage of requests approved within same business day",
        category=KPICategory.EFFICIENCY,
        unit="%",
        target=70.0,
        warning_threshold=50.0,
        critical_threshold=30.0,
        higher_is_better=True,
    ),
    KPIDefinition(
        kpi_id="APR-EFF-003",
        name="Auto-Approval Rate",
        description="Percentage of low-risk requests auto-approved",
        category=KPICategory.EFFICIENCY,
        unit="%",
        target=25.0,
        warning_threshold=15.0,
        critical_threshold=5.0,
        higher_is_better=True,
    ),
    KPIDefinition(
        kpi_id="APR-EFF-004",
        name="Approvals per Day",
        description="Average number of approvals processed per day",
        category=KPICategory.EFFICIENCY,
        unit="count",
        target=50.0,
        warning_threshold=30.0,
        critical_threshold=15.0,
        higher_is_better=True,
    ),

    # Compliance KPIs
    KPIDefinition(
        kpi_id="APR-CMP-001",
        name="SLA Compliance Rate",
        description="Percentage of requests completed within SLA",
        category=KPICategory.COMPLIANCE,
        unit="%",
        target=95.0,
        warning_threshold=90.0,
        critical_threshold=85.0,
        higher_is_better=True,
    ),
    KPIDefinition(
        kpi_id="APR-CMP-002",
        name="Severe SLA Breaches",
        description="Number of severe SLA breaches (>4h over SLA) this month",
        category=KPICategory.COMPLIANCE,
        unit="count",
        target=0.0,
        warning_threshold=5.0,
        critical_threshold=10.0,
        higher_is_better=False,
    ),
    KPIDefinition(
        kpi_id="APR-CMP-003",
        name="Delegation Coverage",
        description="Percentage of approvers with active delegation configured",
        category=KPICategory.COMPLIANCE,
        unit="%",
        target=90.0,
        warning_threshold=75.0,
        critical_threshold=60.0,
        higher_is_better=True,
    ),

    # Quality KPIs
    KPIDefinition(
        kpi_id="APR-QTY-001",
        name="Approval with Justification Rate",
        description="Percentage of approvals with documented justification",
        category=KPICategory.QUALITY,
        unit="%",
        target=100.0,
        warning_threshold=90.0,
        critical_threshold=80.0,
        higher_is_better=True,
    ),
    KPIDefinition(
        kpi_id="APR-QTY-002",
        name="Rejection Rate",
        description="Percentage of requests rejected",
        category=KPICategory.QUALITY,
        unit="%",
        target=15.0,  # Some rejections expected
        warning_threshold=5.0,  # Too few = rubber stamping
        critical_threshold=2.0,
        higher_is_better=False,  # Neither too high nor too low
    ),
    KPIDefinition(
        kpi_id="APR-QTY-003",
        name="High-Risk Rejection Rate",
        description="Percentage of high-risk requests rejected",
        category=KPICategory.QUALITY,
        unit="%",
        target=30.0,  # Higher scrutiny for high risk
        warning_threshold=15.0,
        critical_threshold=5.0,
        higher_is_better=True,
    ),

    # Risk KPIs
    KPIDefinition(
        kpi_id="APR-RSK-001",
        name="Risk-Adjusted Approval Time",
        description="Correlation between risk score and approval time",
        category=KPICategory.RISK,
        unit="correlation",
        target=0.7,  # Higher risk should take longer
        warning_threshold=0.5,
        critical_threshold=0.3,
        higher_is_better=True,
    ),
    KPIDefinition(
        kpi_id="APR-RSK-002",
        name="Critical Risk CISO Review Rate",
        description="Percentage of critical-risk requests reviewed by CISO",
        category=KPICategory.RISK,
        unit="%",
        target=100.0,
        warning_threshold=95.0,
        critical_threshold=90.0,
        higher_is_better=True,
    ),

    # Experience KPIs
    KPIDefinition(
        kpi_id="APR-EXP-001",
        name="Requester Satisfaction",
        description="Average satisfaction score from requesters (1-5)",
        category=KPICategory.EXPERIENCE,
        unit="score",
        target=4.0,
        warning_threshold=3.5,
        critical_threshold=3.0,
        higher_is_better=True,
    ),
    KPIDefinition(
        kpi_id="APR-EXP-002",
        name="First-Time Approval Rate",
        description="Percentage of requests approved without resubmission",
        category=KPICategory.EXPERIENCE,
        unit="%",
        target=85.0,
        warning_threshold=75.0,
        critical_threshold=65.0,
        higher_is_better=True,
    ),
]


class ApprovalKPIEngine:
    """
    Engine for calculating and tracking approval KPIs.

    Provides:
    - Real-time KPI calculation
    - Trend analysis
    - Bottleneck detection
    - SLA tracking
    """

    def __init__(self):
        """Initialize KPI engine."""
        self._kpi_definitions = {kpi.kpi_id: kpi for kpi in APPROVAL_KPIS}
        self._historical_values: Dict[str, List[Tuple[datetime, float]]] = defaultdict(list)
        self._sla_breaches: List[SLABreach] = []
        self._approval_records: List[Dict[str, Any]] = []

    def record_approval(self, record: Dict[str, Any]) -> None:
        """
        Record an approval for KPI tracking.

        Expected fields:
        - request_id
        - submitted_at
        - completed_at
        - status (APPROVED/REJECTED)
        - risk_score
        - approvers
        - sla_hours
        - has_justification
        """
        self._approval_records.append(record)

        # Check for SLA breach
        if record.get("submitted_at") and record.get("completed_at"):
            submitted = record["submitted_at"]
            completed = record["completed_at"]
            if isinstance(submitted, str):
                submitted = datetime.fromisoformat(submitted)
            if isinstance(completed, str):
                completed = datetime.fromisoformat(completed)

            actual_hours = (completed - submitted).total_seconds() / 3600
            sla_hours = record.get("sla_hours", 24.0)

            if actual_hours > sla_hours:
                breach_hours = actual_hours - sla_hours
                severity = "MINOR" if breach_hours < 1 else ("MODERATE" if breach_hours < 4 else "SEVERE")

                breach = SLABreach(
                    request_id=record.get("request_id", ""),
                    approver_id=record.get("final_approver_id", ""),
                    expected_hours=sla_hours,
                    actual_hours=actual_hours,
                    breach_hours=breach_hours,
                    breach_severity=severity,
                    root_cause=self._determine_breach_cause(record),
                )
                self._sla_breaches.append(breach)

    def _determine_breach_cause(self, record: Dict[str, Any]) -> str:
        """Determine likely cause of SLA breach."""
        approvers = record.get("approvers", [])

        # Check for OOO approvers
        for approver in approvers:
            if approver.get("was_ooo"):
                return "Approver out of office"

        # Check for high queue
        for approver in approvers:
            if approver.get("queue_size", 0) > 10:
                return "Approver overloaded"

        # Check for multiple approvers
        if len(approvers) > 3:
            return "Multiple approval levels"

        return "Unknown"

    def calculate_kpi(
        self,
        kpi_id: str,
        period_days: int = 30
    ) -> Optional[KPIValue]:
        """Calculate current value for a KPI."""
        if kpi_id not in self._kpi_definitions:
            return None

        definition = self._kpi_definitions[kpi_id]
        cutoff = datetime.now() - timedelta(days=period_days)

        # Filter records to period
        records = [
            r for r in self._approval_records
            if r.get("completed_at") and
            (r["completed_at"] if isinstance(r["completed_at"], datetime)
             else datetime.fromisoformat(r["completed_at"])) >= cutoff
        ]

        if not records:
            return KPIValue(
                kpi_id=kpi_id,
                value=0.0,
                target=definition.target,
                status="INSUFFICIENT_DATA",
                trend=TrendDirection.INSUFFICIENT_DATA,
                trend_value=0.0,
                sample_size=0,
            )

        # Calculate value based on KPI type
        value = self._calculate_kpi_value(kpi_id, records)

        # Determine status
        status = self._determine_status(value, definition)

        # Calculate trend
        trend, trend_value = self._calculate_trend(kpi_id, value)

        # Store historical value
        self._historical_values[kpi_id].append((datetime.now(), value))

        return KPIValue(
            kpi_id=kpi_id,
            value=value,
            target=definition.target,
            status=status,
            trend=trend,
            trend_value=trend_value,
            sample_size=len(records),
        )

    def _calculate_kpi_value(self, kpi_id: str, records: List[Dict[str, Any]]) -> float:
        """Calculate specific KPI value."""
        if kpi_id == "APR-EFF-001":  # Average Approval Time
            times = []
            for r in records:
                if r.get("submitted_at") and r.get("completed_at"):
                    submitted = r["submitted_at"]
                    completed = r["completed_at"]
                    if isinstance(submitted, str):
                        submitted = datetime.fromisoformat(submitted)
                    if isinstance(completed, str):
                        completed = datetime.fromisoformat(completed)
                    times.append((completed - submitted).total_seconds() / 3600)
            return sum(times) / len(times) if times else 0.0

        elif kpi_id == "APR-EFF-002":  # Same-Day Approval Rate
            same_day = 0
            for r in records:
                if r.get("submitted_at") and r.get("completed_at"):
                    submitted = r["submitted_at"]
                    completed = r["completed_at"]
                    if isinstance(submitted, str):
                        submitted = datetime.fromisoformat(submitted)
                    if isinstance(completed, str):
                        completed = datetime.fromisoformat(completed)
                    if (completed - submitted).total_seconds() / 3600 <= 8:
                        same_day += 1
            return (same_day / len(records)) * 100 if records else 0.0

        elif kpi_id == "APR-EFF-003":  # Auto-Approval Rate
            auto_approved = sum(1 for r in records if r.get("auto_approved", False))
            return (auto_approved / len(records)) * 100 if records else 0.0

        elif kpi_id == "APR-EFF-004":  # Approvals per Day
            if not records:
                return 0.0
            dates = set()
            for r in records:
                completed = r.get("completed_at")
                if completed:
                    if isinstance(completed, str):
                        completed = datetime.fromisoformat(completed)
                    dates.add(completed.date())
            return len(records) / len(dates) if dates else 0.0

        elif kpi_id == "APR-CMP-001":  # SLA Compliance Rate
            within_sla = 0
            for r in records:
                if r.get("submitted_at") and r.get("completed_at"):
                    submitted = r["submitted_at"]
                    completed = r["completed_at"]
                    if isinstance(submitted, str):
                        submitted = datetime.fromisoformat(submitted)
                    if isinstance(completed, str):
                        completed = datetime.fromisoformat(completed)
                    actual = (completed - submitted).total_seconds() / 3600
                    sla = r.get("sla_hours", 24.0)
                    if actual <= sla:
                        within_sla += 1
            return (within_sla / len(records)) * 100 if records else 0.0

        elif kpi_id == "APR-CMP-002":  # Severe SLA Breaches
            cutoff = datetime.now() - timedelta(days=30)
            severe = [
                b for b in self._sla_breaches
                if b.breach_severity == "SEVERE" and b.occurred_at >= cutoff
            ]
            return float(len(severe))

        elif kpi_id == "APR-QTY-001":  # Approval with Justification Rate
            with_justification = sum(1 for r in records if r.get("has_justification", False))
            return (with_justification / len(records)) * 100 if records else 0.0

        elif kpi_id == "APR-QTY-002":  # Rejection Rate
            rejected = sum(1 for r in records if r.get("status") == "REJECTED")
            return (rejected / len(records)) * 100 if records else 0.0

        elif kpi_id == "APR-QTY-003":  # High-Risk Rejection Rate
            high_risk = [r for r in records if r.get("risk_score", 0) > 50]
            if not high_risk:
                return 0.0
            rejected = sum(1 for r in high_risk if r.get("status") == "REJECTED")
            return (rejected / len(high_risk)) * 100

        elif kpi_id == "APR-RSK-002":  # Critical Risk CISO Review Rate
            critical = [r for r in records if r.get("risk_score", 0) > 80]
            if not critical:
                return 100.0
            ciso_reviewed = sum(1 for r in critical if "CISO" in str(r.get("approvers", [])))
            return (ciso_reviewed / len(critical)) * 100

        elif kpi_id == "APR-EXP-001":  # Requester Satisfaction
            scores = [r.get("satisfaction_score") for r in records if r.get("satisfaction_score")]
            return sum(scores) / len(scores) if scores else 0.0

        elif kpi_id == "APR-EXP-002":  # First-Time Approval Rate
            first_time = sum(1 for r in records if not r.get("was_resubmission", False))
            return (first_time / len(records)) * 100 if records else 0.0

        return 0.0

    def _determine_status(self, value: float, definition: KPIDefinition) -> str:
        """Determine KPI status (ON_TARGET, WARNING, CRITICAL)."""
        if definition.higher_is_better:
            if value >= definition.target:
                return "ON_TARGET"
            elif value >= definition.warning_threshold:
                return "WARNING"
            else:
                return "CRITICAL"
        else:
            if value <= definition.target:
                return "ON_TARGET"
            elif value <= definition.warning_threshold:
                return "WARNING"
            else:
                return "CRITICAL"

    def _calculate_trend(self, kpi_id: str, current_value: float) -> Tuple[TrendDirection, float]:
        """Calculate trend for a KPI."""
        history = self._historical_values.get(kpi_id, [])

        if len(history) < 2:
            return TrendDirection.INSUFFICIENT_DATA, 0.0

        # Compare to value from ~7 days ago
        week_ago = datetime.now() - timedelta(days=7)
        past_values = [(t, v) for t, v in history if t <= week_ago]

        if not past_values:
            return TrendDirection.INSUFFICIENT_DATA, 0.0

        past_value = past_values[-1][1]

        if past_value == 0:
            return TrendDirection.INSUFFICIENT_DATA, 0.0

        change = ((current_value - past_value) / past_value) * 100

        definition = self._kpi_definitions.get(kpi_id)
        if definition:
            if definition.higher_is_better:
                if change > 5:
                    return TrendDirection.IMPROVING, change
                elif change < -5:
                    return TrendDirection.DECLINING, change
            else:
                if change < -5:
                    return TrendDirection.IMPROVING, change
                elif change > 5:
                    return TrendDirection.DECLINING, change

        return TrendDirection.STABLE, change

    def calculate_all_kpis(self, period_days: int = 30) -> Dict[str, KPIValue]:
        """Calculate all KPIs."""
        return {
            kpi_id: self.calculate_kpi(kpi_id, period_days)
            for kpi_id in self._kpi_definitions
        }

    def get_kpis_by_category(
        self,
        category: KPICategory,
        period_days: int = 30
    ) -> List[KPIValue]:
        """Get KPIs for a specific category."""
        kpi_ids = [
            kpi.kpi_id for kpi in APPROVAL_KPIS
            if kpi.category == category
        ]
        return [
            self.calculate_kpi(kpi_id, period_days)
            for kpi_id in kpi_ids
        ]

    def detect_bottlenecks(
        self,
        approver_stats: List[Dict[str, Any]]
    ) -> List[BottleneckReport]:
        """
        Detect approval bottlenecks.

        Args:
            approver_stats: Statistics per approver

        Returns:
            List of bottleneck reports
        """
        bottlenecks = []

        for stats in approver_stats:
            is_bottleneck = False
            recommendations = []

            avg_queue = stats.get("avg_queue_size", 0)
            avg_wait = stats.get("avg_wait_hours", 0)
            breach_rate = stats.get("breach_rate", 0)

            # Check bottleneck indicators
            if avg_queue > 10:
                is_bottleneck = True
                recommendations.append("Consider adding delegate to handle overflow")

            if avg_wait > 16:
                is_bottleneck = True
                recommendations.append("Review workload distribution")

            if breach_rate > 10:
                is_bottleneck = True
                recommendations.append("Configure automatic escalation")

            bottlenecks.append(BottleneckReport(
                approver_id=stats.get("approver_id", ""),
                approver_name=stats.get("approver_name", ""),
                approver_type=stats.get("approver_type", ApproverType.LINE_MANAGER),
                avg_queue_size=avg_queue,
                avg_wait_hours=avg_wait,
                breach_rate=breach_rate,
                is_bottleneck=is_bottleneck,
                recommendations=recommendations,
            ))

        # Sort by severity
        bottlenecks.sort(key=lambda b: (not b.is_bottleneck, -b.breach_rate))

        return bottlenecks

    def get_sla_breaches(
        self,
        since: Optional[datetime] = None,
        severity: Optional[str] = None
    ) -> List[SLABreach]:
        """Get SLA breaches with optional filtering."""
        breaches = self._sla_breaches

        if since:
            breaches = [b for b in breaches if b.occurred_at >= since]

        if severity:
            breaches = [b for b in breaches if b.breach_severity == severity]

        return sorted(breaches, key=lambda b: b.occurred_at, reverse=True)

    def generate_dashboard(self, period_days: int = 30) -> Dict[str, Any]:
        """Generate KPI dashboard data."""
        all_kpis = self.calculate_all_kpis(period_days)

        # Categorize by status
        on_target = [k for k in all_kpis.values() if k and k.status == "ON_TARGET"]
        warning = [k for k in all_kpis.values() if k and k.status == "WARNING"]
        critical = [k for k in all_kpis.values() if k and k.status == "CRITICAL"]

        # Get recent breaches
        recent_breaches = self.get_sla_breaches(
            since=datetime.now() - timedelta(days=7)
        )

        return {
            "generated_at": datetime.now().isoformat(),
            "period_days": period_days,
            "summary": {
                "total_kpis": len(all_kpis),
                "on_target": len(on_target),
                "warning": len(warning),
                "critical": len(critical),
                "health_score": (len(on_target) / len(all_kpis) * 100) if all_kpis else 0,
            },
            "kpis_by_category": {
                category.value: [
                    kpi.to_dict() for kpi in self.get_kpis_by_category(category, period_days)
                    if kpi
                ]
                for category in KPICategory
            },
            "critical_alerts": [k.to_dict() for k in critical],
            "recent_breaches": [b.to_dict() for b in recent_breaches[:5]],
            "trends": {
                "improving": len([k for k in all_kpis.values() if k and k.trend == TrendDirection.IMPROVING]),
                "stable": len([k for k in all_kpis.values() if k and k.trend == TrendDirection.STABLE]),
                "declining": len([k for k in all_kpis.values() if k and k.trend == TrendDirection.DECLINING]),
            },
        }

    def generate_executive_summary(self, period_days: int = 30) -> str:
        """Generate executive summary of approval performance."""
        dashboard = self.generate_dashboard(period_days)
        summary = dashboard["summary"]

        lines = []
        lines.append("=" * 50)
        lines.append("APPROVAL WORKFLOW PERFORMANCE SUMMARY")
        lines.append("=" * 50)
        lines.append("")

        # Overall health
        health = summary["health_score"]
        if health >= 80:
            status = "HEALTHY"
        elif health >= 60:
            status = "NEEDS ATTENTION"
        else:
            status = "REQUIRES INTERVENTION"

        lines.append(f"Overall Status: {status}")
        lines.append(f"Health Score: {health:.0f}%")
        lines.append(f"KPIs On Target: {summary['on_target']}/{summary['total_kpis']}")
        lines.append("")

        # Critical issues
        if dashboard["critical_alerts"]:
            lines.append("CRITICAL ISSUES:")
            for alert in dashboard["critical_alerts"][:3]:
                kpi_def = self._kpi_definitions.get(alert["kpi_id"])
                if kpi_def:
                    lines.append(f"  - {kpi_def.name}: {alert['value']} (target: {alert['target']})")
            lines.append("")

        # Trends
        trends = dashboard["trends"]
        lines.append(f"Trends: {trends['improving']} improving, {trends['stable']} stable, {trends['declining']} declining")

        # Recent breaches
        if dashboard["recent_breaches"]:
            lines.append("")
            lines.append(f"SLA Breaches (last 7 days): {len(dashboard['recent_breaches'])}")

        lines.append("")
        lines.append("=" * 50)

        return "\n".join(lines)
