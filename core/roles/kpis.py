# Role Design KPIs
# Executive metrics for CIO and CISO

"""
Role Design KPIs for GOVERNEX+.

CIO-Level KPIs (Efficiency & Cost):
- Avg roles per user
- % unused permissions
- Role reuse ratio
- Time to provision
- Role count trend

CISO-Level KPIs (Risk & Control):
- % toxic roles
- SoD violations per 100 users
- Privilege creep rate
- High-risk dormant access
- Fraud likelihood index

Joint CIO/CISO KPIs (Strategic):
- Risk reduction vs baseline
- Controls passing continuously
- Auto-approved vs manual ratio
- Audit issues avoided
- Benchmark percentile
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class KPICategory(Enum):
    """KPI categories."""
    CIO = "CIO"
    CISO = "CISO"
    JOINT = "JOINT"


class KPITrend(Enum):
    """KPI trend direction."""
    IMPROVING = "IMPROVING"
    STABLE = "STABLE"
    DECLINING = "DECLINING"


class KPIStatus(Enum):
    """KPI health status."""
    GREEN = "GREEN"
    YELLOW = "YELLOW"
    RED = "RED"


@dataclass
class KPIDefinition:
    """Definition of a KPI."""
    kpi_id: str
    name: str
    description: str
    category: KPICategory
    unit: str = ""
    higher_is_better: bool = True

    # Thresholds
    green_threshold: float = 0.0
    yellow_threshold: float = 0.0
    red_threshold: float = 0.0

    # Target
    target_value: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "kpi_id": self.kpi_id,
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
            "unit": self.unit,
            "higher_is_better": self.higher_is_better,
            "thresholds": {
                "green": self.green_threshold,
                "yellow": self.yellow_threshold,
                "red": self.red_threshold,
            },
            "target": self.target_value,
        }


@dataclass
class KPIValue:
    """A computed KPI value."""
    kpi_id: str
    name: str
    value: float
    unit: str = ""
    timestamp: datetime = field(default_factory=datetime.now)

    # Status
    status: KPIStatus = KPIStatus.GREEN
    trend: KPITrend = KPITrend.STABLE

    # Comparison
    previous_value: Optional[float] = None
    target_value: Optional[float] = None
    baseline_value: Optional[float] = None

    # Deltas
    delta_vs_previous: float = 0.0
    delta_vs_target: float = 0.0
    delta_vs_baseline: float = 0.0

    # Context
    category: KPICategory = KPICategory.CIO
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "kpi_id": self.kpi_id,
            "name": self.name,
            "value": round(self.value, 2),
            "unit": self.unit,
            "status": self.status.value,
            "trend": self.trend.value,
            "timestamp": self.timestamp.isoformat(),
            "previous_value": round(self.previous_value, 2) if self.previous_value else None,
            "target_value": round(self.target_value, 2) if self.target_value else None,
            "delta_vs_previous": round(self.delta_vs_previous, 2),
            "delta_vs_target": round(self.delta_vs_target, 2),
            "delta_vs_baseline": round(self.delta_vs_baseline, 2),
            "category": self.category.value,
        }


@dataclass
class KPIDashboard:
    """Complete KPI dashboard."""
    generated_at: datetime = field(default_factory=datetime.now)
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None

    # KPIs by category
    cio_kpis: List[KPIValue] = field(default_factory=list)
    ciso_kpis: List[KPIValue] = field(default_factory=list)
    joint_kpis: List[KPIValue] = field(default_factory=list)

    # Summary
    overall_health: KPIStatus = KPIStatus.GREEN
    kpis_on_target: int = 0
    kpis_at_risk: int = 0
    kpis_critical: int = 0

    # Executive summary
    executive_summary: str = ""
    key_improvements: List[str] = field(default_factory=list)
    action_items: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "generated_at": self.generated_at.isoformat(),
            "period": {
                "start": self.period_start.isoformat() if self.period_start else None,
                "end": self.period_end.isoformat() if self.period_end else None,
            },
            "cio_kpis": [k.to_dict() for k in self.cio_kpis],
            "ciso_kpis": [k.to_dict() for k in self.ciso_kpis],
            "joint_kpis": [k.to_dict() for k in self.joint_kpis],
            "summary": {
                "overall_health": self.overall_health.value,
                "on_target": self.kpis_on_target,
                "at_risk": self.kpis_at_risk,
                "critical": self.kpis_critical,
            },
            "executive_summary": self.executive_summary,
            "key_improvements": self.key_improvements,
            "action_items": self.action_items,
        }


# Standard KPI definitions
CIO_KPIS = [
    KPIDefinition(
        kpi_id="CIO-001",
        name="Avg Roles per User",
        description="Average number of roles assigned per user",
        category=KPICategory.CIO,
        unit="roles",
        higher_is_better=False,
        green_threshold=3.0,
        yellow_threshold=5.0,
        red_threshold=8.0,
        target_value=3.0,
    ),
    KPIDefinition(
        kpi_id="CIO-002",
        name="Unused Permission Rate",
        description="Percentage of assigned permissions never used",
        category=KPICategory.CIO,
        unit="%",
        higher_is_better=False,
        green_threshold=15.0,
        yellow_threshold=30.0,
        red_threshold=50.0,
        target_value=10.0,
    ),
    KPIDefinition(
        kpi_id="CIO-003",
        name="Role Reuse Ratio",
        description="Average users per role (higher = better reuse)",
        category=KPICategory.CIO,
        unit="users/role",
        higher_is_better=True,
        green_threshold=8.0,
        yellow_threshold=4.0,
        red_threshold=2.0,
        target_value=10.0,
    ),
    KPIDefinition(
        kpi_id="CIO-004",
        name="Time to Provision",
        description="Average hours to complete role assignment",
        category=KPICategory.CIO,
        unit="hours",
        higher_is_better=False,
        green_threshold=4.0,
        yellow_threshold=24.0,
        red_threshold=72.0,
        target_value=2.0,
    ),
    KPIDefinition(
        kpi_id="CIO-005",
        name="Role Count Trend",
        description="Monthly change in total role count",
        category=KPICategory.CIO,
        unit="%",
        higher_is_better=False,
        green_threshold=2.0,
        yellow_threshold=5.0,
        red_threshold=10.0,
        target_value=0.0,
    ),
]

CISO_KPIS = [
    KPIDefinition(
        kpi_id="CISO-001",
        name="Toxic Role Rate",
        description="Percentage of roles enabling fraud paths",
        category=KPICategory.CISO,
        unit="%",
        higher_is_better=False,
        green_threshold=2.0,
        yellow_threshold=5.0,
        red_threshold=10.0,
        target_value=0.0,
    ),
    KPIDefinition(
        kpi_id="CISO-002",
        name="SoD Violations per 100 Users",
        description="Rate of segregation of duties violations",
        category=KPICategory.CISO,
        unit="per 100",
        higher_is_better=False,
        green_threshold=3.0,
        yellow_threshold=8.0,
        red_threshold=15.0,
        target_value=2.0,
    ),
    KPIDefinition(
        kpi_id="CISO-003",
        name="Privilege Creep Rate",
        description="Monthly increase in average permissions per user",
        category=KPICategory.CISO,
        unit="%",
        higher_is_better=False,
        green_threshold=1.0,
        yellow_threshold=3.0,
        red_threshold=5.0,
        target_value=0.0,
    ),
    KPIDefinition(
        kpi_id="CISO-004",
        name="High-Risk Dormant Access",
        description="Percentage of high-risk access unused for 90+ days",
        category=KPICategory.CISO,
        unit="%",
        higher_is_better=False,
        green_threshold=5.0,
        yellow_threshold=15.0,
        red_threshold=25.0,
        target_value=0.0,
    ),
    KPIDefinition(
        kpi_id="CISO-005",
        name="Fraud Likelihood Index",
        description="Composite fraud risk score (0-100)",
        category=KPICategory.CISO,
        unit="score",
        higher_is_better=False,
        green_threshold=20.0,
        yellow_threshold=40.0,
        red_threshold=60.0,
        target_value=15.0,
    ),
]

JOINT_KPIS = [
    KPIDefinition(
        kpi_id="JOINT-001",
        name="Risk Reduction vs Baseline",
        description="Percentage risk reduction since baseline",
        category=KPICategory.JOINT,
        unit="%",
        higher_is_better=True,
        green_threshold=40.0,
        yellow_threshold=20.0,
        red_threshold=0.0,
        target_value=50.0,
    ),
    KPIDefinition(
        kpi_id="JOINT-002",
        name="Controls Passing Rate",
        description="Percentage of continuous controls passing",
        category=KPICategory.JOINT,
        unit="%",
        higher_is_better=True,
        green_threshold=95.0,
        yellow_threshold=85.0,
        red_threshold=75.0,
        target_value=98.0,
    ),
    KPIDefinition(
        kpi_id="JOINT-003",
        name="Auto-Approval Rate",
        description="Percentage of low-risk requests auto-approved",
        category=KPICategory.JOINT,
        unit="%",
        higher_is_better=True,
        green_threshold=60.0,
        yellow_threshold=40.0,
        red_threshold=20.0,
        target_value=70.0,
    ),
    KPIDefinition(
        kpi_id="JOINT-004",
        name="Audit Issues Avoided",
        description="Estimated audit issues prevented by controls",
        category=KPICategory.JOINT,
        unit="count",
        higher_is_better=True,
        green_threshold=20.0,
        yellow_threshold=10.0,
        red_threshold=5.0,
    ),
    KPIDefinition(
        kpi_id="JOINT-005",
        name="Industry Benchmark Percentile",
        description="Position vs industry peers",
        category=KPICategory.JOINT,
        unit="percentile",
        higher_is_better=True,
        green_threshold=70.0,
        yellow_threshold=50.0,
        red_threshold=30.0,
        target_value=75.0,
    ),
]


class RoleDesignKPIEngine:
    """
    Calculates and tracks role design KPIs.

    Provides metrics for CIO, CISO, and joint executive view.
    """

    def __init__(self):
        """Initialize KPI engine."""
        self._history: Dict[str, List[KPIValue]] = {}
        self._baselines: Dict[str, float] = {}
        self._targets: Dict[str, float] = {}

        # Initialize from definitions
        for kpi in CIO_KPIS + CISO_KPIS + JOINT_KPIS:
            if kpi.target_value:
                self._targets[kpi.kpi_id] = kpi.target_value

    def set_baseline(self, kpi_id: str, value: float) -> None:
        """Set baseline value for a KPI."""
        self._baselines[kpi_id] = value

    def set_target(self, kpi_id: str, value: float) -> None:
        """Set target value for a KPI."""
        self._targets[kpi_id] = value

    def calculate_kpis(
        self,
        metrics: Dict[str, Any]
    ) -> KPIDashboard:
        """
        Calculate all KPIs from input metrics.

        Args:
            metrics: Raw metrics data with:
                - total_users
                - total_roles
                - role_assignments
                - unused_permissions
                - sod_violations
                - toxic_roles
                - high_risk_dormant
                - controls_passing
                - auto_approvals
                - manual_approvals
                - baseline_risk_score
                - current_risk_score
                - benchmark_percentile

        Returns:
            KPIDashboard with all calculated KPIs
        """
        dashboard = KPIDashboard(
            period_end=datetime.now(),
        )

        # Calculate CIO KPIs
        dashboard.cio_kpis = self._calculate_cio_kpis(metrics)

        # Calculate CISO KPIs
        dashboard.ciso_kpis = self._calculate_ciso_kpis(metrics)

        # Calculate Joint KPIs
        dashboard.joint_kpis = self._calculate_joint_kpis(metrics)

        # Calculate summary
        all_kpis = dashboard.cio_kpis + dashboard.ciso_kpis + dashboard.joint_kpis
        dashboard.kpis_on_target = sum(1 for k in all_kpis if k.status == KPIStatus.GREEN)
        dashboard.kpis_at_risk = sum(1 for k in all_kpis if k.status == KPIStatus.YELLOW)
        dashboard.kpis_critical = sum(1 for k in all_kpis if k.status == KPIStatus.RED)

        # Determine overall health
        if dashboard.kpis_critical > 2:
            dashboard.overall_health = KPIStatus.RED
        elif dashboard.kpis_critical > 0 or dashboard.kpis_at_risk > 3:
            dashboard.overall_health = KPIStatus.YELLOW
        else:
            dashboard.overall_health = KPIStatus.GREEN

        # Generate executive summary
        dashboard.executive_summary = self._generate_executive_summary(dashboard)
        dashboard.key_improvements = self._identify_improvements(all_kpis)
        dashboard.action_items = self._generate_action_items(all_kpis)

        return dashboard

    def _calculate_cio_kpis(self, metrics: Dict[str, Any]) -> List[KPIValue]:
        """Calculate CIO-level KPIs."""
        kpis = []

        # Avg Roles per User
        total_users = metrics.get("total_users", 1)
        role_assignments = metrics.get("role_assignments", 0)
        avg_roles = role_assignments / max(total_users, 1)

        kpis.append(self._create_kpi_value(
            CIO_KPIS[0], avg_roles
        ))

        # Unused Permission Rate
        total_permissions = metrics.get("total_permissions", 1)
        unused_permissions = metrics.get("unused_permissions", 0)
        unused_rate = unused_permissions / max(total_permissions, 1) * 100

        kpis.append(self._create_kpi_value(
            CIO_KPIS[1], unused_rate
        ))

        # Role Reuse Ratio
        total_roles = metrics.get("total_roles", 1)
        reuse_ratio = role_assignments / max(total_roles, 1)

        kpis.append(self._create_kpi_value(
            CIO_KPIS[2], reuse_ratio
        ))

        # Time to Provision
        avg_provision_hours = metrics.get("avg_provision_hours", 4.0)

        kpis.append(self._create_kpi_value(
            CIO_KPIS[3], avg_provision_hours
        ))

        # Role Count Trend
        previous_roles = metrics.get("previous_total_roles", total_roles)
        if previous_roles > 0:
            role_trend = (total_roles - previous_roles) / previous_roles * 100
        else:
            role_trend = 0

        kpis.append(self._create_kpi_value(
            CIO_KPIS[4], role_trend
        ))

        return kpis

    def _calculate_ciso_kpis(self, metrics: Dict[str, Any]) -> List[KPIValue]:
        """Calculate CISO-level KPIs."""
        kpis = []

        # Toxic Role Rate
        total_roles = metrics.get("total_roles", 1)
        toxic_roles = metrics.get("toxic_roles", 0)
        toxic_rate = toxic_roles / max(total_roles, 1) * 100

        kpis.append(self._create_kpi_value(
            CISO_KPIS[0], toxic_rate
        ))

        # SoD Violations per 100 Users
        total_users = metrics.get("total_users", 100)
        sod_violations = metrics.get("sod_violations", 0)
        sod_rate = sod_violations / max(total_users, 1) * 100

        kpis.append(self._create_kpi_value(
            CISO_KPIS[1], sod_rate
        ))

        # Privilege Creep Rate
        creep_rate = metrics.get("privilege_creep_rate", 0)

        kpis.append(self._create_kpi_value(
            CISO_KPIS[2], creep_rate
        ))

        # High-Risk Dormant Access
        dormant_rate = metrics.get("high_risk_dormant_rate", 0)

        kpis.append(self._create_kpi_value(
            CISO_KPIS[3], dormant_rate
        ))

        # Fraud Likelihood Index
        fraud_index = metrics.get("fraud_likelihood_index", 0)

        kpis.append(self._create_kpi_value(
            CISO_KPIS[4], fraud_index
        ))

        return kpis

    def _calculate_joint_kpis(self, metrics: Dict[str, Any]) -> List[KPIValue]:
        """Calculate joint CIO/CISO KPIs."""
        kpis = []

        # Risk Reduction vs Baseline
        baseline_risk = metrics.get("baseline_risk_score", 100)
        current_risk = metrics.get("current_risk_score", baseline_risk)
        if baseline_risk > 0:
            risk_reduction = (baseline_risk - current_risk) / baseline_risk * 100
        else:
            risk_reduction = 0

        kpis.append(self._create_kpi_value(
            JOINT_KPIS[0], risk_reduction
        ))

        # Controls Passing Rate
        total_controls = metrics.get("total_controls", 1)
        passing_controls = metrics.get("controls_passing", 0)
        passing_rate = passing_controls / max(total_controls, 1) * 100

        kpis.append(self._create_kpi_value(
            JOINT_KPIS[1], passing_rate
        ))

        # Auto-Approval Rate
        total_approvals = metrics.get("total_approvals", 1)
        auto_approvals = metrics.get("auto_approvals", 0)
        auto_rate = auto_approvals / max(total_approvals, 1) * 100

        kpis.append(self._create_kpi_value(
            JOINT_KPIS[2], auto_rate
        ))

        # Audit Issues Avoided
        issues_avoided = metrics.get("audit_issues_avoided", 0)

        kpis.append(self._create_kpi_value(
            JOINT_KPIS[3], issues_avoided
        ))

        # Benchmark Percentile
        percentile = metrics.get("benchmark_percentile", 50)

        kpis.append(self._create_kpi_value(
            JOINT_KPIS[4], percentile
        ))

        return kpis

    def _create_kpi_value(
        self,
        definition: KPIDefinition,
        value: float
    ) -> KPIValue:
        """Create a KPI value with status and trend."""
        kpi = KPIValue(
            kpi_id=definition.kpi_id,
            name=definition.name,
            value=value,
            unit=definition.unit,
            category=definition.category,
            description=definition.description,
            target_value=self._targets.get(definition.kpi_id, definition.target_value),
        )

        # Determine status
        if definition.higher_is_better:
            if value >= definition.green_threshold:
                kpi.status = KPIStatus.GREEN
            elif value >= definition.yellow_threshold:
                kpi.status = KPIStatus.YELLOW
            else:
                kpi.status = KPIStatus.RED
        else:
            if value <= definition.green_threshold:
                kpi.status = KPIStatus.GREEN
            elif value <= definition.yellow_threshold:
                kpi.status = KPIStatus.YELLOW
            else:
                kpi.status = KPIStatus.RED

        # Get previous value and calculate trend
        history = self._history.get(definition.kpi_id, [])
        if history:
            kpi.previous_value = history[-1].value
            kpi.delta_vs_previous = value - kpi.previous_value

            # Determine trend
            if definition.higher_is_better:
                if kpi.delta_vs_previous > 0.05 * abs(kpi.previous_value):
                    kpi.trend = KPITrend.IMPROVING
                elif kpi.delta_vs_previous < -0.05 * abs(kpi.previous_value):
                    kpi.trend = KPITrend.DECLINING
            else:
                if kpi.delta_vs_previous < -0.05 * abs(kpi.previous_value):
                    kpi.trend = KPITrend.IMPROVING
                elif kpi.delta_vs_previous > 0.05 * abs(kpi.previous_value):
                    kpi.trend = KPITrend.DECLINING

        # Calculate delta vs target
        if kpi.target_value is not None:
            kpi.delta_vs_target = value - kpi.target_value

        # Calculate delta vs baseline
        baseline = self._baselines.get(definition.kpi_id)
        if baseline is not None:
            kpi.baseline_value = baseline
            kpi.delta_vs_baseline = value - baseline

        # Store in history
        if definition.kpi_id not in self._history:
            self._history[definition.kpi_id] = []
        self._history[definition.kpi_id].append(kpi)

        return kpi

    def _generate_executive_summary(self, dashboard: KPIDashboard) -> str:
        """Generate executive summary text."""
        total_kpis = len(dashboard.cio_kpis) + len(dashboard.ciso_kpis) + len(dashboard.joint_kpis)

        summary_parts = []

        # Overall status
        if dashboard.overall_health == KPIStatus.GREEN:
            summary_parts.append(
                f"Role governance health is strong with {dashboard.kpis_on_target}/{total_kpis} KPIs on target."
            )
        elif dashboard.overall_health == KPIStatus.YELLOW:
            summary_parts.append(
                f"Role governance requires attention: {dashboard.kpis_at_risk} KPIs at risk, "
                f"{dashboard.kpis_critical} critical."
            )
        else:
            summary_parts.append(
                f"Role governance health is critical: {dashboard.kpis_critical} KPIs require immediate action."
            )

        # Highlight key metrics
        all_kpis = dashboard.cio_kpis + dashboard.ciso_kpis + dashboard.joint_kpis

        # Best performing
        improving = [k for k in all_kpis if k.trend == KPITrend.IMPROVING]
        if improving:
            best = max(improving, key=lambda k: abs(k.delta_vs_previous) if k.delta_vs_previous else 0)
            summary_parts.append(f"Strongest improvement: {best.name}.")

        # Most critical
        critical = [k for k in all_kpis if k.status == KPIStatus.RED]
        if critical:
            worst = critical[0]
            summary_parts.append(f"Priority focus: {worst.name} at {worst.value:.1f}{worst.unit}.")

        return " ".join(summary_parts)

    def _identify_improvements(self, all_kpis: List[KPIValue]) -> List[str]:
        """Identify key improvements."""
        improvements = []

        for kpi in all_kpis:
            if kpi.trend == KPITrend.IMPROVING and kpi.delta_vs_previous:
                if kpi.delta_vs_previous > 0:
                    improvements.append(
                        f"{kpi.name}: improved by {abs(kpi.delta_vs_previous):.1f}{kpi.unit}"
                    )
                else:
                    improvements.append(
                        f"{kpi.name}: reduced by {abs(kpi.delta_vs_previous):.1f}{kpi.unit}"
                    )

        return improvements[:5]  # Top 5

    def _generate_action_items(self, all_kpis: List[KPIValue]) -> List[str]:
        """Generate action items for underperforming KPIs."""
        actions = []

        for kpi in all_kpis:
            if kpi.status == KPIStatus.RED:
                actions.append(f"CRITICAL: Address {kpi.name} ({kpi.value:.1f}{kpi.unit})")
            elif kpi.status == KPIStatus.YELLOW and kpi.trend == KPITrend.DECLINING:
                actions.append(f"WATCH: {kpi.name} declining - review preventive measures")

        return actions[:5]  # Top 5

    def get_trend_report(
        self,
        kpi_id: str,
        periods: int = 12
    ) -> Dict[str, Any]:
        """Get trend report for a specific KPI."""
        history = self._history.get(kpi_id, [])[-periods:]

        if not history:
            return {"error": "No history available"}

        return {
            "kpi_id": kpi_id,
            "name": history[0].name if history else "",
            "periods": len(history),
            "current_value": history[-1].value if history else 0,
            "current_status": history[-1].status.value if history else None,
            "trend": history[-1].trend.value if history else None,
            "history": [
                {
                    "timestamp": h.timestamp.isoformat(),
                    "value": round(h.value, 2),
                    "status": h.status.value,
                }
                for h in history
            ],
            "min_value": min(h.value for h in history),
            "max_value": max(h.value for h in history),
            "avg_value": sum(h.value for h in history) / len(history),
        }

    def compare_periods(
        self,
        current_metrics: Dict[str, Any],
        previous_metrics: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Compare KPIs between two periods."""
        current = self.calculate_kpis(current_metrics)
        previous = self.calculate_kpis(previous_metrics)

        comparisons = []

        for curr in (current.cio_kpis + current.ciso_kpis + current.joint_kpis):
            prev_kpi = next(
                (p for p in (previous.cio_kpis + previous.ciso_kpis + previous.joint_kpis)
                 if p.kpi_id == curr.kpi_id),
                None
            )

            if prev_kpi:
                delta = curr.value - prev_kpi.value
                pct_change = (delta / prev_kpi.value * 100) if prev_kpi.value != 0 else 0

                comparisons.append({
                    "kpi_id": curr.kpi_id,
                    "name": curr.name,
                    "current": round(curr.value, 2),
                    "previous": round(prev_kpi.value, 2),
                    "delta": round(delta, 2),
                    "pct_change": round(pct_change, 1),
                    "status_change": f"{prev_kpi.status.value} → {curr.status.value}",
                })

        return {
            "current_overall_health": current.overall_health.value,
            "previous_overall_health": previous.overall_health.value,
            "comparisons": comparisons,
            "improved_count": sum(
                1 for c in comparisons
                if c["delta"] > 0 and any(
                    d.higher_is_better for d in (CIO_KPIS + CISO_KPIS + JOINT_KPIS)
                    if d.kpi_id == c["kpi_id"]
                )
            ),
        }
