# Role Portfolio Management
# Strategic view of role health and benchmarking

"""
Role Portfolio for GOVERNEX+.

Provides executive-grade visibility into role health:
- Portfolio health metrics
- Industry benchmarking
- Risk concentration analysis
- Sprawl detection
- Maturity scoring
"""

from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional, Any, Tuple
from datetime import datetime, timedelta
from enum import Enum
import logging
from collections import defaultdict

from .models import Role, RoleStatus, RoleLifecycleState

logger = logging.getLogger(__name__)


class HealthLevel(Enum):
    """Overall health level."""
    CRITICAL = "CRITICAL"
    POOR = "POOR"
    FAIR = "FAIR"
    GOOD = "GOOD"
    EXCELLENT = "EXCELLENT"


class MaturityLevel(Enum):
    """Role governance maturity level."""
    INITIAL = "INITIAL"  # Ad-hoc, no process
    DEVELOPING = "DEVELOPING"  # Some processes
    DEFINED = "DEFINED"  # Documented processes
    MANAGED = "MANAGED"  # Measured and controlled
    OPTIMIZING = "OPTIMIZING"  # Continuous improvement


@dataclass
class PortfolioMetrics:
    """Core metrics for the role portfolio."""
    total_roles: int = 0
    active_roles: int = 0
    deprecated_roles: int = 0
    draft_roles: int = 0

    # Risk metrics
    high_risk_roles: int = 0
    toxic_roles: int = 0
    roles_with_sod: int = 0

    # Usage metrics
    unused_roles: int = 0
    underutilized_roles: int = 0
    heavily_used_roles: int = 0

    # Governance metrics
    certified_roles: int = 0
    overdue_review_roles: int = 0
    roles_with_owners: int = 0

    # Permission metrics
    total_permissions: int = 0
    avg_permissions_per_role: float = 0.0
    sensitive_permissions_total: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_roles": self.total_roles,
            "active_roles": self.active_roles,
            "deprecated_roles": self.deprecated_roles,
            "draft_roles": self.draft_roles,
            "high_risk_roles": self.high_risk_roles,
            "toxic_roles": self.toxic_roles,
            "roles_with_sod": self.roles_with_sod,
            "unused_roles": self.unused_roles,
            "underutilized_roles": self.underutilized_roles,
            "heavily_used_roles": self.heavily_used_roles,
            "certified_roles": self.certified_roles,
            "overdue_review_roles": self.overdue_review_roles,
            "roles_with_owners": self.roles_with_owners,
            "total_permissions": self.total_permissions,
            "avg_permissions_per_role": round(self.avg_permissions_per_role, 2),
            "sensitive_permissions_total": self.sensitive_permissions_total,
        }


@dataclass
class PortfolioHealth:
    """
    Health assessment of the role portfolio.

    Provides executive-grade health metrics.
    """
    assessment_date: datetime = field(default_factory=datetime.now)

    # Overall health
    overall_level: HealthLevel = HealthLevel.FAIR
    overall_score: float = 50.0  # 0-100

    # Component scores
    risk_health_score: float = 50.0
    usage_health_score: float = 50.0
    governance_health_score: float = 50.0
    design_health_score: float = 50.0

    # Key percentages
    toxic_role_percentage: float = 0.0
    unused_role_percentage: float = 0.0
    high_risk_percentage: float = 0.0
    uncertified_percentage: float = 0.0
    ownerless_percentage: float = 0.0

    # Risk concentration
    risk_by_process: Dict[str, float] = field(default_factory=dict)
    risk_by_department: Dict[str, float] = field(default_factory=dict)

    # Trends
    score_trend: str = "stable"  # improving, stable, declining
    previous_score: Optional[float] = None

    # Key findings
    critical_findings: List[str] = field(default_factory=list)
    improvement_areas: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "assessment_date": self.assessment_date.isoformat(),
            "overall_level": self.overall_level.value,
            "overall_score": round(self.overall_score, 2),
            "component_scores": {
                "risk_health": round(self.risk_health_score, 2),
                "usage_health": round(self.usage_health_score, 2),
                "governance_health": round(self.governance_health_score, 2),
                "design_health": round(self.design_health_score, 2),
            },
            "key_percentages": {
                "toxic_roles": round(self.toxic_role_percentage, 2),
                "unused_roles": round(self.unused_role_percentage, 2),
                "high_risk": round(self.high_risk_percentage, 2),
                "uncertified": round(self.uncertified_percentage, 2),
                "ownerless": round(self.ownerless_percentage, 2),
            },
            "risk_by_process": self.risk_by_process,
            "risk_by_department": self.risk_by_department,
            "score_trend": self.score_trend,
            "critical_findings": self.critical_findings,
            "improvement_areas": self.improvement_areas,
        }


@dataclass
class IndustryBenchmark:
    """Industry benchmark data for comparison."""
    industry: str
    benchmark_date: datetime = field(default_factory=datetime.now)

    # Role counts
    avg_roles_per_1000_users: float = 0.0
    median_permissions_per_role: float = 0.0

    # Risk benchmarks
    avg_high_risk_percentage: float = 0.0
    avg_toxic_percentage: float = 0.0
    avg_sod_conflict_rate: float = 0.0

    # Governance benchmarks
    avg_certification_rate: float = 0.0
    avg_ownership_rate: float = 0.0
    avg_review_compliance: float = 0.0

    # Usage benchmarks
    avg_unused_percentage: float = 0.0
    avg_utilization_rate: float = 0.0


@dataclass
class RoleBenchmark:
    """
    Benchmark comparison results.

    Compares organization's role portfolio to industry peers.
    """
    benchmark_date: datetime = field(default_factory=datetime.now)
    industry: str = "General"
    peer_count: int = 0

    # Comparison results
    roles_per_user_percentile: float = 50.0
    risk_percentile: float = 50.0
    governance_percentile: float = 50.0
    usage_percentile: float = 50.0

    # Specific comparisons
    comparisons: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    # Maturity assessment
    maturity_level: MaturityLevel = MaturityLevel.DEFINED
    maturity_score: float = 50.0

    # Gap analysis
    gaps: List[Dict[str, Any]] = field(default_factory=list)
    strengths: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "benchmark_date": self.benchmark_date.isoformat(),
            "industry": self.industry,
            "peer_count": self.peer_count,
            "percentiles": {
                "roles_per_user": round(self.roles_per_user_percentile, 2),
                "risk": round(self.risk_percentile, 2),
                "governance": round(self.governance_percentile, 2),
                "usage": round(self.usage_percentile, 2),
            },
            "comparisons": self.comparisons,
            "maturity_level": self.maturity_level.value,
            "maturity_score": round(self.maturity_score, 2),
            "gaps": self.gaps,
            "strengths": self.strengths,
        }


@dataclass
class RoleSprawlAnalysis:
    """Analysis of role sprawl issues."""
    total_roles: int = 0
    optimal_role_count: int = 0
    sprawl_ratio: float = 1.0  # actual/optimal

    # Duplication
    potential_duplicates: List[Tuple[str, str, float]] = field(default_factory=list)
    consolidation_opportunities: int = 0

    # Fragmentation
    overly_granular_roles: int = 0
    roles_with_single_permission: int = 0

    # Bloat
    oversized_roles: int = 0
    avg_excess_permissions: float = 0.0

    # Recommendations
    sprawl_reduction_potential: float = 0.0  # % reduction possible
    priority_actions: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_roles": self.total_roles,
            "optimal_role_count": self.optimal_role_count,
            "sprawl_ratio": round(self.sprawl_ratio, 2),
            "potential_duplicates": len(self.potential_duplicates),
            "consolidation_opportunities": self.consolidation_opportunities,
            "overly_granular_roles": self.overly_granular_roles,
            "oversized_roles": self.oversized_roles,
            "sprawl_reduction_potential": round(self.sprawl_reduction_potential, 2),
            "priority_actions": self.priority_actions,
        }


class RolePortfolio:
    """
    Manages the overall role portfolio.

    Key capabilities:
    - Track all roles in the organization
    - Calculate portfolio metrics
    - Identify trends
    - Support executive reporting
    """

    def __init__(self):
        """Initialize portfolio."""
        self._roles: Dict[str, Role] = {}
        self._role_scores: Dict[str, float] = {}
        self._role_usage: Dict[str, Dict[str, Any]] = {}
        self._history: List[PortfolioMetrics] = []

    def add_role(self, role: Role) -> None:
        """Add a role to the portfolio."""
        self._roles[role.role_id] = role

    def remove_role(self, role_id: str) -> Optional[Role]:
        """Remove a role from the portfolio."""
        return self._roles.pop(role_id, None)

    def get_role(self, role_id: str) -> Optional[Role]:
        """Get a role by ID."""
        return self._roles.get(role_id)

    def set_role_score(self, role_id: str, score: float) -> None:
        """Set a role's risk score."""
        self._role_scores[role_id] = score

    def set_role_usage(self, role_id: str, usage: Dict[str, Any]) -> None:
        """Set role usage data."""
        self._role_usage[role_id] = usage

    def calculate_metrics(self) -> PortfolioMetrics:
        """Calculate current portfolio metrics."""
        metrics = PortfolioMetrics()
        metrics.total_roles = len(self._roles)

        if metrics.total_roles == 0:
            return metrics

        for role in self._roles.values():
            # Status counts
            if role.lifecycle_state == RoleLifecycleState.ACTIVE:
                metrics.active_roles += 1
            elif role.lifecycle_state == RoleLifecycleState.DEPRECATED:
                metrics.deprecated_roles += 1
            elif role.lifecycle_state == RoleLifecycleState.DRAFT:
                metrics.draft_roles += 1

            # Risk counts
            score = self._role_scores.get(role.role_id, 0)
            if score >= 70:
                metrics.high_risk_roles += 1
            if score >= 85:
                metrics.toxic_roles += 1

            # Usage counts
            usage = self._role_usage.get(role.role_id, {})
            usage_level = usage.get("usage_level", "")
            if usage_level == "NEVER_USED":
                metrics.unused_roles += 1
            elif usage_level == "RARELY_USED":
                metrics.underutilized_roles += 1
            elif usage_level == "HEAVILY_USED":
                metrics.heavily_used_roles += 1

            # Governance counts
            if role.metadata and role.metadata.owner_id:
                metrics.roles_with_owners += 1
            if role.metadata and role.metadata.is_certified:
                metrics.certified_roles += 1
            if role.metadata and role.metadata.next_review_date:
                if role.metadata.next_review_date < datetime.now():
                    metrics.overdue_review_roles += 1

            # Permission counts
            metrics.total_permissions += role.permission_count
            metrics.sensitive_permissions_total += role.sensitive_permission_count

        metrics.avg_permissions_per_role = (
            metrics.total_permissions / metrics.total_roles
        )

        # Store in history
        self._history.append(metrics)

        return metrics

    def get_roles_by_process(self) -> Dict[str, List[Role]]:
        """Group roles by business process."""
        by_process: Dict[str, List[Role]] = defaultdict(list)
        for role in self._roles.values():
            process = role.metadata.business_process if role.metadata else "Unassigned"
            by_process[process].append(role)
        return dict(by_process)

    def get_roles_by_department(self) -> Dict[str, List[Role]]:
        """Group roles by department."""
        by_dept: Dict[str, List[Role]] = defaultdict(list)
        for role in self._roles.values():
            dept = role.metadata.department if role.metadata else "Unassigned"
            by_dept[dept].append(role)
        return dict(by_dept)

    def get_high_risk_roles(self, threshold: float = 70.0) -> List[Tuple[Role, float]]:
        """Get roles above risk threshold."""
        results = []
        for role_id, score in self._role_scores.items():
            if score >= threshold:
                role = self._roles.get(role_id)
                if role:
                    results.append((role, score))
        return sorted(results, key=lambda x: x[1], reverse=True)

    def get_unused_roles(self, days: int = 90) -> List[Role]:
        """Get roles not used in specified days."""
        results = []
        for role_id, usage in self._role_usage.items():
            last_used = usage.get("last_used")
            if not last_used:
                role = self._roles.get(role_id)
                if role:
                    results.append(role)
            elif isinstance(last_used, datetime):
                if (datetime.now() - last_used).days > days:
                    role = self._roles.get(role_id)
                    if role:
                        results.append(role)
        return results


class PortfolioDashboard:
    """
    Executive dashboard for role portfolio.

    Provides:
    - Health assessment
    - Benchmarking
    - Sprawl analysis
    - Trend reporting
    - Action recommendations
    """

    # Health score thresholds
    HEALTH_THRESHOLDS = {
        HealthLevel.CRITICAL: 30,
        HealthLevel.POOR: 50,
        HealthLevel.FAIR: 70,
        HealthLevel.GOOD: 85,
        HealthLevel.EXCELLENT: 100,
    }

    # Industry benchmarks (simplified - production would load from external source)
    INDUSTRY_BENCHMARKS = {
        "Financial Services": IndustryBenchmark(
            industry="Financial Services",
            avg_roles_per_1000_users=150,
            median_permissions_per_role=25,
            avg_high_risk_percentage=8.0,
            avg_toxic_percentage=2.0,
            avg_sod_conflict_rate=5.0,
            avg_certification_rate=92.0,
            avg_ownership_rate=95.0,
            avg_review_compliance=88.0,
            avg_unused_percentage=12.0,
            avg_utilization_rate=75.0,
        ),
        "Healthcare": IndustryBenchmark(
            industry="Healthcare",
            avg_roles_per_1000_users=180,
            median_permissions_per_role=30,
            avg_high_risk_percentage=10.0,
            avg_toxic_percentage=3.0,
            avg_sod_conflict_rate=7.0,
            avg_certification_rate=88.0,
            avg_ownership_rate=90.0,
            avg_review_compliance=82.0,
            avg_unused_percentage=15.0,
            avg_utilization_rate=70.0,
        ),
        "Manufacturing": IndustryBenchmark(
            industry="Manufacturing",
            avg_roles_per_1000_users=120,
            median_permissions_per_role=20,
            avg_high_risk_percentage=12.0,
            avg_toxic_percentage=4.0,
            avg_sod_conflict_rate=8.0,
            avg_certification_rate=80.0,
            avg_ownership_rate=85.0,
            avg_review_compliance=75.0,
            avg_unused_percentage=20.0,
            avg_utilization_rate=65.0,
        ),
        "Technology": IndustryBenchmark(
            industry="Technology",
            avg_roles_per_1000_users=200,
            median_permissions_per_role=35,
            avg_high_risk_percentage=6.0,
            avg_toxic_percentage=1.5,
            avg_sod_conflict_rate=4.0,
            avg_certification_rate=85.0,
            avg_ownership_rate=92.0,
            avg_review_compliance=80.0,
            avg_unused_percentage=18.0,
            avg_utilization_rate=72.0,
        ),
        "General": IndustryBenchmark(
            industry="General",
            avg_roles_per_1000_users=160,
            median_permissions_per_role=28,
            avg_high_risk_percentage=10.0,
            avg_toxic_percentage=3.0,
            avg_sod_conflict_rate=6.0,
            avg_certification_rate=85.0,
            avg_ownership_rate=88.0,
            avg_review_compliance=80.0,
            avg_unused_percentage=15.0,
            avg_utilization_rate=70.0,
        ),
    }

    def __init__(self, portfolio: RolePortfolio):
        """Initialize dashboard."""
        self.portfolio = portfolio
        self._health_history: List[PortfolioHealth] = []

    def assess_health(self) -> PortfolioHealth:
        """
        Perform comprehensive health assessment.

        Returns:
            PortfolioHealth with scores and findings
        """
        metrics = self.portfolio.calculate_metrics()
        health = PortfolioHealth()

        if metrics.total_roles == 0:
            health.overall_level = HealthLevel.FAIR
            health.overall_score = 50.0
            health.critical_findings.append("No roles in portfolio")
            return health

        # Calculate percentages
        health.toxic_role_percentage = (
            metrics.toxic_roles / metrics.total_roles * 100
        )
        health.unused_role_percentage = (
            metrics.unused_roles / metrics.total_roles * 100
        )
        health.high_risk_percentage = (
            metrics.high_risk_roles / metrics.total_roles * 100
        )
        health.uncertified_percentage = (
            (metrics.total_roles - metrics.certified_roles) / metrics.total_roles * 100
        )
        health.ownerless_percentage = (
            (metrics.total_roles - metrics.roles_with_owners) / metrics.total_roles * 100
        )

        # Risk health score (0-100)
        # Lower is worse: toxic roles, high risk, SoD conflicts
        risk_deductions = 0
        risk_deductions += health.toxic_role_percentage * 10  # Heavy penalty for toxic
        risk_deductions += health.high_risk_percentage * 2
        health.risk_health_score = max(0, 100 - risk_deductions)

        # Usage health score
        # Unused roles and underutilization hurt score
        usage_deductions = 0
        usage_deductions += health.unused_role_percentage * 3
        usage_deductions += (metrics.underutilized_roles / max(metrics.total_roles, 1)) * 100
        health.usage_health_score = max(0, 100 - usage_deductions)

        # Governance health score
        # Certification, ownership, review compliance
        governance_score = 0
        governance_score += (metrics.certified_roles / metrics.total_roles) * 40
        governance_score += (metrics.roles_with_owners / metrics.total_roles) * 30
        governance_score += max(0, 30 - (metrics.overdue_review_roles / metrics.total_roles * 100))
        health.governance_health_score = min(100, governance_score)

        # Design health score
        # Permission counts, distribution
        design_score = 100
        if metrics.avg_permissions_per_role > 50:
            design_score -= 20
        elif metrics.avg_permissions_per_role > 30:
            design_score -= 10

        sensitive_ratio = (
            metrics.sensitive_permissions_total / max(metrics.total_permissions, 1)
        )
        if sensitive_ratio > 0.3:
            design_score -= 15

        health.design_health_score = max(0, design_score)

        # Overall score (weighted average)
        health.overall_score = (
            health.risk_health_score * 0.35 +
            health.usage_health_score * 0.20 +
            health.governance_health_score * 0.30 +
            health.design_health_score * 0.15
        )

        # Determine level
        if health.overall_score < self.HEALTH_THRESHOLDS[HealthLevel.CRITICAL]:
            health.overall_level = HealthLevel.CRITICAL
        elif health.overall_score < self.HEALTH_THRESHOLDS[HealthLevel.POOR]:
            health.overall_level = HealthLevel.POOR
        elif health.overall_score < self.HEALTH_THRESHOLDS[HealthLevel.FAIR]:
            health.overall_level = HealthLevel.FAIR
        elif health.overall_score < self.HEALTH_THRESHOLDS[HealthLevel.GOOD]:
            health.overall_level = HealthLevel.GOOD
        else:
            health.overall_level = HealthLevel.EXCELLENT

        # Calculate risk by process
        by_process = self.portfolio.get_roles_by_process()
        for process, roles in by_process.items():
            process_risk = 0
            for role in roles:
                score = self.portfolio._role_scores.get(role.role_id, 0)
                process_risk += score
            health.risk_by_process[process] = (
                process_risk / len(roles) if roles else 0
            )

        # Calculate risk by department
        by_dept = self.portfolio.get_roles_by_department()
        for dept, roles in by_dept.items():
            dept_risk = 0
            for role in roles:
                score = self.portfolio._role_scores.get(role.role_id, 0)
                dept_risk += score
            health.risk_by_department[dept] = (
                dept_risk / len(roles) if roles else 0
            )

        # Trend calculation
        if self._health_history:
            previous = self._health_history[-1]
            health.previous_score = previous.overall_score
            diff = health.overall_score - previous.overall_score
            if diff > 5:
                health.score_trend = "improving"
            elif diff < -5:
                health.score_trend = "declining"
            else:
                health.score_trend = "stable"

        # Generate findings
        if health.toxic_role_percentage > 5:
            health.critical_findings.append(
                f"High toxic role rate: {health.toxic_role_percentage:.1f}%"
            )
        if health.unused_role_percentage > 20:
            health.critical_findings.append(
                f"High unused role rate: {health.unused_role_percentage:.1f}%"
            )
        if health.uncertified_percentage > 30:
            health.critical_findings.append(
                f"Low certification rate: {100 - health.uncertified_percentage:.1f}%"
            )
        if health.ownerless_percentage > 20:
            health.critical_findings.append(
                f"Many roles without owners: {health.ownerless_percentage:.1f}%"
            )

        # Improvement areas
        if health.risk_health_score < 70:
            health.improvement_areas.append("Risk reduction needed")
        if health.usage_health_score < 70:
            health.improvement_areas.append("Role cleanup recommended")
        if health.governance_health_score < 70:
            health.improvement_areas.append("Governance practices need improvement")
        if health.design_health_score < 70:
            health.improvement_areas.append("Role design optimization needed")

        # Store in history
        self._health_history.append(health)

        return health

    def benchmark(
        self,
        industry: str = "General",
        user_count: int = 1000
    ) -> RoleBenchmark:
        """
        Benchmark portfolio against industry peers.

        Args:
            industry: Industry to benchmark against
            user_count: Organization user count for normalization

        Returns:
            RoleBenchmark with comparison results
        """
        benchmark_data = self.INDUSTRY_BENCHMARKS.get(
            industry,
            self.INDUSTRY_BENCHMARKS["General"]
        )

        metrics = self.portfolio.calculate_metrics()
        result = RoleBenchmark(
            industry=industry,
            peer_count=100,  # Simulated peer count
        )

        if metrics.total_roles == 0:
            return result

        # Calculate our rates
        our_roles_per_1000 = metrics.total_roles / (user_count / 1000)
        our_high_risk_pct = metrics.high_risk_roles / metrics.total_roles * 100
        our_toxic_pct = metrics.toxic_roles / metrics.total_roles * 100
        our_unused_pct = metrics.unused_roles / metrics.total_roles * 100
        our_certified_pct = metrics.certified_roles / metrics.total_roles * 100
        our_ownership_pct = metrics.roles_with_owners / metrics.total_roles * 100

        # Roles per user percentile (lower is better)
        ratio = our_roles_per_1000 / benchmark_data.avg_roles_per_1000_users
        result.roles_per_user_percentile = max(0, min(100, 100 - (ratio - 1) * 50))

        # Risk percentile (lower high-risk is better)
        risk_ratio = our_high_risk_pct / max(benchmark_data.avg_high_risk_percentage, 0.1)
        result.risk_percentile = max(0, min(100, 100 - (risk_ratio - 1) * 50))

        # Governance percentile (higher certification is better)
        gov_ratio = our_certified_pct / max(benchmark_data.avg_certification_rate, 0.1)
        result.governance_percentile = max(0, min(100, gov_ratio * 50 + 25))

        # Usage percentile (lower unused is better)
        usage_ratio = our_unused_pct / max(benchmark_data.avg_unused_percentage, 0.1)
        result.usage_percentile = max(0, min(100, 100 - (usage_ratio - 1) * 50))

        # Detailed comparisons
        result.comparisons = {
            "roles_per_1000_users": {
                "our_value": round(our_roles_per_1000, 1),
                "benchmark": benchmark_data.avg_roles_per_1000_users,
                "delta": round(our_roles_per_1000 - benchmark_data.avg_roles_per_1000_users, 1),
            },
            "high_risk_percentage": {
                "our_value": round(our_high_risk_pct, 1),
                "benchmark": benchmark_data.avg_high_risk_percentage,
                "delta": round(our_high_risk_pct - benchmark_data.avg_high_risk_percentage, 1),
            },
            "toxic_percentage": {
                "our_value": round(our_toxic_pct, 1),
                "benchmark": benchmark_data.avg_toxic_percentage,
                "delta": round(our_toxic_pct - benchmark_data.avg_toxic_percentage, 1),
            },
            "certification_rate": {
                "our_value": round(our_certified_pct, 1),
                "benchmark": benchmark_data.avg_certification_rate,
                "delta": round(our_certified_pct - benchmark_data.avg_certification_rate, 1),
            },
            "ownership_rate": {
                "our_value": round(our_ownership_pct, 1),
                "benchmark": benchmark_data.avg_ownership_rate,
                "delta": round(our_ownership_pct - benchmark_data.avg_ownership_rate, 1),
            },
            "unused_percentage": {
                "our_value": round(our_unused_pct, 1),
                "benchmark": benchmark_data.avg_unused_percentage,
                "delta": round(our_unused_pct - benchmark_data.avg_unused_percentage, 1),
            },
        }

        # Maturity assessment
        maturity_score = (
            result.risk_percentile * 0.3 +
            result.governance_percentile * 0.4 +
            result.usage_percentile * 0.3
        )
        result.maturity_score = maturity_score

        if maturity_score < 30:
            result.maturity_level = MaturityLevel.INITIAL
        elif maturity_score < 50:
            result.maturity_level = MaturityLevel.DEVELOPING
        elif maturity_score < 70:
            result.maturity_level = MaturityLevel.DEFINED
        elif maturity_score < 85:
            result.maturity_level = MaturityLevel.MANAGED
        else:
            result.maturity_level = MaturityLevel.OPTIMIZING

        # Gap analysis
        for metric, comparison in result.comparisons.items():
            delta = comparison["delta"]
            if metric in ["certification_rate", "ownership_rate"]:
                # Higher is better
                if delta < -10:
                    result.gaps.append({
                        "metric": metric,
                        "gap": abs(delta),
                        "priority": "HIGH" if delta < -20 else "MEDIUM",
                    })
                elif delta > 10:
                    result.strengths.append(f"Strong {metric}: {delta:+.1f}% above benchmark")
            else:
                # Lower is better
                if delta > 10:
                    result.gaps.append({
                        "metric": metric,
                        "gap": delta,
                        "priority": "HIGH" if delta > 20 else "MEDIUM",
                    })
                elif delta < -10:
                    result.strengths.append(f"Strong {metric}: {abs(delta):.1f}% below benchmark")

        return result

    def analyze_sprawl(
        self,
        optimal_roles_per_1000_users: float = 100
    ) -> RoleSprawlAnalysis:
        """
        Analyze role sprawl issues.

        Args:
            optimal_roles_per_1000_users: Target role count

        Returns:
            RoleSprawlAnalysis with sprawl metrics
        """
        analysis = RoleSprawlAnalysis()
        analysis.total_roles = len(self.portfolio._roles)

        if analysis.total_roles == 0:
            return analysis

        # Estimate optimal (simplified)
        analysis.optimal_role_count = max(
            10,
            int(analysis.total_roles * 0.7)  # 30% reduction target
        )
        analysis.sprawl_ratio = analysis.total_roles / analysis.optimal_role_count

        # Find potential duplicates (simplified - check permission overlap)
        roles = list(self.portfolio._roles.values())
        for i, role1 in enumerate(roles):
            for role2 in roles[i+1:]:
                perm_set1 = {p.permission_id for p in role1.permissions}
                perm_set2 = {p.permission_id for p in role2.permissions}

                if perm_set1 and perm_set2:
                    overlap = len(perm_set1 & perm_set2)
                    union = len(perm_set1 | perm_set2)
                    similarity = overlap / union if union > 0 else 0

                    if similarity > 0.8:
                        analysis.potential_duplicates.append(
                            (role1.role_id, role2.role_id, similarity)
                        )
                        analysis.consolidation_opportunities += 1

        # Analyze role sizes
        for role in roles:
            perm_count = role.permission_count

            if perm_count <= 1:
                analysis.roles_with_single_permission += 1
                analysis.overly_granular_roles += 1
            elif perm_count > 50:
                analysis.oversized_roles += 1

        # Calculate reduction potential
        reduction_from_duplicates = len(analysis.potential_duplicates)
        reduction_from_granular = analysis.overly_granular_roles * 0.5
        total_reduction = reduction_from_duplicates + reduction_from_granular
        analysis.sprawl_reduction_potential = min(
            50,
            (total_reduction / analysis.total_roles) * 100
        )

        # Priority actions
        if analysis.potential_duplicates:
            analysis.priority_actions.append(
                f"Consolidate {len(analysis.potential_duplicates)} duplicate role pairs"
            )
        if analysis.overly_granular_roles > 5:
            analysis.priority_actions.append(
                f"Merge {analysis.overly_granular_roles} overly granular roles"
            )
        if analysis.oversized_roles > 0:
            analysis.priority_actions.append(
                f"Decompose {analysis.oversized_roles} oversized roles"
            )
        if not analysis.priority_actions:
            analysis.priority_actions.append("Role portfolio is well-optimized")

        return analysis

    def get_executive_summary(self) -> Dict[str, Any]:
        """
        Generate executive summary for the portfolio.

        Returns:
            Dict with key metrics and insights
        """
        health = self.assess_health()
        metrics = self.portfolio.calculate_metrics()

        return {
            "summary": {
                "total_roles": metrics.total_roles,
                "overall_health": health.overall_level.value,
                "health_score": round(health.overall_score, 1),
                "score_trend": health.score_trend,
            },
            "risk_summary": {
                "high_risk_roles": metrics.high_risk_roles,
                "toxic_roles": metrics.toxic_roles,
                "roles_with_sod": metrics.roles_with_sod,
                "risk_health_score": round(health.risk_health_score, 1),
            },
            "governance_summary": {
                "certified_roles": metrics.certified_roles,
                "certification_rate": round(
                    metrics.certified_roles / max(metrics.total_roles, 1) * 100, 1
                ),
                "overdue_reviews": metrics.overdue_review_roles,
                "governance_score": round(health.governance_health_score, 1),
            },
            "usage_summary": {
                "unused_roles": metrics.unused_roles,
                "underutilized_roles": metrics.underutilized_roles,
                "heavily_used_roles": metrics.heavily_used_roles,
                "usage_score": round(health.usage_health_score, 1),
            },
            "critical_findings": health.critical_findings[:5],
            "improvement_areas": health.improvement_areas[:3],
            "generated_at": datetime.now().isoformat(),
        }

    def get_trend_report(
        self,
        periods: int = 6
    ) -> Dict[str, Any]:
        """
        Generate trend report from historical data.

        Args:
            periods: Number of historical periods to include

        Returns:
            Dict with trend data
        """
        history = self._health_history[-periods:] if self._health_history else []

        if not history:
            return {"error": "No historical data available"}

        scores = [h.overall_score for h in history]
        risk_scores = [h.risk_health_score for h in history]
        gov_scores = [h.governance_health_score for h in history]

        return {
            "periods": len(history),
            "overall_trend": {
                "current": scores[-1] if scores else 0,
                "previous": scores[-2] if len(scores) > 1 else None,
                "change": scores[-1] - scores[0] if len(scores) > 1 else 0,
                "direction": "improving" if scores[-1] > scores[0] else "declining",
            },
            "risk_trend": {
                "current": risk_scores[-1] if risk_scores else 0,
                "change": risk_scores[-1] - risk_scores[0] if len(risk_scores) > 1 else 0,
            },
            "governance_trend": {
                "current": gov_scores[-1] if gov_scores else 0,
                "change": gov_scores[-1] - gov_scores[0] if len(gov_scores) > 1 else 0,
            },
            "history": [
                {
                    "date": h.assessment_date.isoformat(),
                    "score": round(h.overall_score, 1),
                    "level": h.overall_level.value,
                }
                for h in history
            ],
        }
