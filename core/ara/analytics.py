# Risk Analytics Module
# Advanced analytics for GOVERNEX+ ARA

"""
Risk Analytics for Access Risk Analysis.

Provides:
- Risk trend analysis over time
- Risk heatmaps by role/user/department
- Economic risk quantification
- Control effectiveness analysis
- High-risk entity leaderboards
- Risk concentration metrics

SAP GRC: Basic reporting
GOVERNEX+: Intelligent analytics with economic impact quantification
"""

from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from collections import defaultdict
from enum import Enum
import logging
import statistics

from .models import (
    Risk,
    RiskSeverity,
    RiskCategory,
    RiskStatus,
    RiskType,
    SoDConflict,
    RiskAnalysisResult,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Analytics Data Models
# =============================================================================

@dataclass
class RiskTrendPoint:
    """Single point in a risk trend series."""
    timestamp: datetime
    total_risks: int = 0
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    aggregate_score: float = 0.0
    new_risks: int = 0
    remediated_risks: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "total_risks": self.total_risks,
            "critical_count": self.critical_count,
            "high_count": self.high_count,
            "medium_count": self.medium_count,
            "low_count": self.low_count,
            "aggregate_score": self.aggregate_score,
            "new_risks": self.new_risks,
            "remediated_risks": self.remediated_risks,
        }


@dataclass
class RiskHeatmapCell:
    """Single cell in a risk heatmap."""
    row_id: str  # e.g., user_id, role_id
    row_name: str
    column_id: str  # e.g., category, rule_id
    column_name: str
    risk_count: int = 0
    severity_score: float = 0.0
    color_intensity: float = 0.0  # 0-1 for visualization

    def to_dict(self) -> Dict[str, Any]:
        return {
            "row_id": self.row_id,
            "row_name": self.row_name,
            "column_id": self.column_id,
            "column_name": self.column_name,
            "risk_count": self.risk_count,
            "severity_score": self.severity_score,
            "color_intensity": self.color_intensity,
        }


@dataclass
class RiskConcentration:
    """Risk concentration metrics for an entity."""
    entity_type: str  # user, role, department
    entity_id: str
    entity_name: str
    total_risks: int = 0
    critical_risks: int = 0
    risk_score: float = 0.0
    percentage_of_total: float = 0.0
    risk_density: float = 0.0  # risks per entitlement

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "entity_name": self.entity_name,
            "total_risks": self.total_risks,
            "critical_risks": self.critical_risks,
            "risk_score": self.risk_score,
            "percentage_of_total": self.percentage_of_total,
            "risk_density": self.risk_density,
        }


@dataclass
class EconomicRiskMetrics:
    """Economic quantification of risk exposure."""
    total_exposure: float = 0.0  # USD
    annual_loss_expectancy: float = 0.0
    regulatory_penalty_risk: float = 0.0
    fraud_exposure: float = 0.0
    operational_cost: float = 0.0

    # Breakdown by category
    exposure_by_category: Dict[str, float] = field(default_factory=dict)

    # Cost factors
    avg_incident_cost: float = 50000.0  # Default baseline
    regulatory_fine_factor: float = 100000.0
    fraud_multiplier: float = 2.5

    # Confidence
    confidence_level: float = 0.8  # 0-1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_exposure": self.total_exposure,
            "annual_loss_expectancy": self.annual_loss_expectancy,
            "regulatory_penalty_risk": self.regulatory_penalty_risk,
            "fraud_exposure": self.fraud_exposure,
            "operational_cost": self.operational_cost,
            "exposure_by_category": self.exposure_by_category,
            "confidence_level": self.confidence_level,
        }


@dataclass
class ControlEffectivenessMetrics:
    """Metrics for mitigation control effectiveness."""
    control_id: str
    control_name: str

    # Usage metrics
    times_applied: int = 0
    risks_covered: int = 0
    unique_users: int = 0

    # Effectiveness metrics
    prevented_incidents: int = 0
    risk_reduction_pct: float = 0.0
    avg_time_to_remediate: float = 0.0  # hours

    # Quality metrics
    approval_override_rate: float = 0.0
    exception_rate: float = 0.0
    recurrence_rate: float = 0.0  # risks that came back

    # Score
    effectiveness_score: float = 0.0  # 0-100

    def to_dict(self) -> Dict[str, Any]:
        return {
            "control_id": self.control_id,
            "control_name": self.control_name,
            "times_applied": self.times_applied,
            "risks_covered": self.risks_covered,
            "unique_users": self.unique_users,
            "prevented_incidents": self.prevented_incidents,
            "risk_reduction_pct": self.risk_reduction_pct,
            "avg_time_to_remediate": self.avg_time_to_remediate,
            "approval_override_rate": self.approval_override_rate,
            "exception_rate": self.exception_rate,
            "recurrence_rate": self.recurrence_rate,
            "effectiveness_score": self.effectiveness_score,
        }


class TimeGranularity(Enum):
    """Time granularity for trend analysis."""
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"


# =============================================================================
# Risk Trend Analyzer
# =============================================================================

class RiskTrendAnalyzer:
    """
    Analyzes risk trends over time.

    Provides historical analysis and forecasting capabilities.
    """

    def __init__(self, risk_history: Optional[List[RiskAnalysisResult]] = None):
        """
        Initialize trend analyzer.

        Args:
            risk_history: Historical analysis results
        """
        self.risk_history = risk_history or []
        self._risk_snapshots: List[Dict[str, Any]] = []

    def add_snapshot(
        self,
        timestamp: datetime,
        risks: List[Risk],
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Add a risk snapshot for trend tracking.

        Args:
            timestamp: Snapshot timestamp
            risks: List of risks at that point
            metadata: Optional additional data
        """
        snapshot = {
            "timestamp": timestamp,
            "risks": risks,
            "total": len(risks),
            "by_severity": self._count_by_severity(risks),
            "by_category": self._count_by_category(risks),
            "aggregate_score": self._calculate_aggregate(risks),
            "metadata": metadata or {},
        }
        self._risk_snapshots.append(snapshot)
        self._risk_snapshots.sort(key=lambda x: x["timestamp"])

    def get_trend(
        self,
        from_date: datetime,
        to_date: datetime,
        granularity: TimeGranularity = TimeGranularity.DAILY
    ) -> List[RiskTrendPoint]:
        """
        Get risk trend for a time period.

        Args:
            from_date: Start date
            to_date: End date
            granularity: Time granularity

        Returns:
            List of trend points
        """
        trend_points = []

        # Filter snapshots in range
        filtered = [
            s for s in self._risk_snapshots
            if from_date <= s["timestamp"] <= to_date
        ]

        if not filtered:
            return trend_points

        # Group by time bucket
        buckets = self._bucket_by_granularity(filtered, granularity)

        prev_risks = set()
        for bucket_time, snapshots in sorted(buckets.items()):
            # Use last snapshot in bucket
            snapshot = snapshots[-1]
            current_risk_ids = {r.risk_id for r in snapshot["risks"]}

            point = RiskTrendPoint(
                timestamp=bucket_time,
                total_risks=snapshot["total"],
                critical_count=snapshot["by_severity"].get(RiskSeverity.CRITICAL, 0),
                high_count=snapshot["by_severity"].get(RiskSeverity.HIGH, 0),
                medium_count=snapshot["by_severity"].get(RiskSeverity.MEDIUM, 0),
                low_count=snapshot["by_severity"].get(RiskSeverity.LOW, 0),
                aggregate_score=snapshot["aggregate_score"],
                new_risks=len(current_risk_ids - prev_risks),
                remediated_risks=len(prev_risks - current_risk_ids),
            )
            trend_points.append(point)
            prev_risks = current_risk_ids

        return trend_points

    def get_trend_summary(
        self,
        from_date: datetime,
        to_date: datetime
    ) -> Dict[str, Any]:
        """
        Get summary statistics for a trend period.

        Args:
            from_date: Start date
            to_date: End date

        Returns:
            Summary statistics
        """
        trend = self.get_trend(from_date, to_date, TimeGranularity.DAILY)

        if not trend:
            return {
                "period_start": from_date.isoformat(),
                "period_end": to_date.isoformat(),
                "data_points": 0,
                "error": "No data available",
            }

        scores = [p.aggregate_score for p in trend]
        totals = [p.total_risks for p in trend]

        return {
            "period_start": from_date.isoformat(),
            "period_end": to_date.isoformat(),
            "data_points": len(trend),
            "risk_score": {
                "start": scores[0] if scores else 0,
                "end": scores[-1] if scores else 0,
                "min": min(scores) if scores else 0,
                "max": max(scores) if scores else 0,
                "avg": statistics.mean(scores) if scores else 0,
                "trend": "increasing" if scores[-1] > scores[0] else "decreasing" if scores[-1] < scores[0] else "stable",
            },
            "risk_count": {
                "start": totals[0] if totals else 0,
                "end": totals[-1] if totals else 0,
                "total_new": sum(p.new_risks for p in trend),
                "total_remediated": sum(p.remediated_risks for p in trend),
                "net_change": totals[-1] - totals[0] if totals else 0,
            },
            "velocity": {
                "new_per_day": sum(p.new_risks for p in trend) / len(trend) if trend else 0,
                "remediated_per_day": sum(p.remediated_risks for p in trend) / len(trend) if trend else 0,
            },
        }

    def forecast_risk(
        self,
        days_ahead: int = 30,
        method: str = "linear"
    ) -> List[RiskTrendPoint]:
        """
        Forecast future risk trends.

        Args:
            days_ahead: Days to forecast
            method: Forecasting method (linear, exponential)

        Returns:
            Forecasted trend points
        """
        if len(self._risk_snapshots) < 7:
            logger.warning("Insufficient data for forecasting")
            return []

        # Use recent data for forecasting
        recent = self._risk_snapshots[-30:]
        scores = [s["aggregate_score"] for s in recent]

        forecast = []
        last_time = recent[-1]["timestamp"]

        # Simple linear regression
        if method == "linear":
            n = len(scores)
            x_mean = n / 2
            y_mean = statistics.mean(scores)

            numerator = sum((i - x_mean) * (scores[i] - y_mean) for i in range(n))
            denominator = sum((i - x_mean) ** 2 for i in range(n))

            slope = numerator / denominator if denominator != 0 else 0
            intercept = y_mean - slope * x_mean

            for day in range(1, days_ahead + 1):
                projected_score = max(0, min(100, intercept + slope * (n + day)))
                forecast.append(RiskTrendPoint(
                    timestamp=last_time + timedelta(days=day),
                    aggregate_score=projected_score,
                    total_risks=int(recent[-1]["total"] * (projected_score / scores[-1])) if scores[-1] > 0 else recent[-1]["total"],
                ))

        return forecast

    def _bucket_by_granularity(
        self,
        snapshots: List[Dict],
        granularity: TimeGranularity
    ) -> Dict[datetime, List[Dict]]:
        """Group snapshots by time bucket."""
        buckets = defaultdict(list)

        for snapshot in snapshots:
            ts = snapshot["timestamp"]

            if granularity == TimeGranularity.HOURLY:
                bucket = ts.replace(minute=0, second=0, microsecond=0)
            elif granularity == TimeGranularity.DAILY:
                bucket = ts.replace(hour=0, minute=0, second=0, microsecond=0)
            elif granularity == TimeGranularity.WEEKLY:
                bucket = ts - timedelta(days=ts.weekday())
                bucket = bucket.replace(hour=0, minute=0, second=0, microsecond=0)
            elif granularity == TimeGranularity.MONTHLY:
                bucket = ts.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            elif granularity == TimeGranularity.QUARTERLY:
                quarter_month = ((ts.month - 1) // 3) * 3 + 1
                bucket = ts.replace(month=quarter_month, day=1, hour=0, minute=0, second=0, microsecond=0)
            else:
                bucket = ts

            buckets[bucket].append(snapshot)

        return dict(buckets)

    def _count_by_severity(self, risks: List[Risk]) -> Dict[RiskSeverity, int]:
        """Count risks by severity."""
        counts = defaultdict(int)
        for risk in risks:
            counts[risk.severity] += 1
        return dict(counts)

    def _count_by_category(self, risks: List[Risk]) -> Dict[RiskCategory, int]:
        """Count risks by category."""
        counts = defaultdict(int)
        for risk in risks:
            counts[risk.category] += 1
        return dict(counts)

    def _calculate_aggregate(self, risks: List[Risk]) -> float:
        """Calculate aggregate risk score."""
        if not risks:
            return 0.0
        return sum(r.final_score for r in risks) / len(risks)


# =============================================================================
# Risk Analytics Engine
# =============================================================================

class RiskAnalytics:
    """
    Comprehensive risk analytics engine.

    Provides heatmaps, concentrations, economic quantification,
    and control effectiveness analysis.
    """

    # Economic impact factors by category
    CATEGORY_IMPACT_FACTORS = {
        RiskCategory.FRAUD: 500000,
        RiskCategory.FINANCIAL: 250000,
        RiskCategory.COMPLIANCE: 200000,
        RiskCategory.SECURITY: 150000,
        RiskCategory.DATA_PRIVACY: 300000,
        RiskCategory.OPERATIONAL: 75000,
        RiskCategory.IT: 100000,
        RiskCategory.HR: 50000,
    }

    # Severity multipliers
    SEVERITY_MULTIPLIERS = {
        RiskSeverity.CRITICAL: 4.0,
        RiskSeverity.HIGH: 2.0,
        RiskSeverity.MEDIUM: 1.0,
        RiskSeverity.LOW: 0.5,
    }

    def __init__(self):
        """Initialize analytics engine."""
        self.trend_analyzer = RiskTrendAnalyzer()
        self._user_risks: Dict[str, List[Risk]] = defaultdict(list)
        self._role_risks: Dict[str, List[Risk]] = defaultdict(list)
        self._department_risks: Dict[str, List[Risk]] = defaultdict(list)
        self._control_stats: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            "applied": 0,
            "risks_covered": 0,
            "users": set(),
            "prevented": 0,
            "overrides": 0,
            "exceptions": 0,
            "recurrences": 0,
            "remediation_times": [],
        })

    def index_risk(
        self,
        risk: Risk,
        user_id: Optional[str] = None,
        role_id: Optional[str] = None,
        department: Optional[str] = None
    ):
        """
        Index a risk for analytics.

        Args:
            risk: Risk to index
            user_id: User associated with risk
            role_id: Role associated with risk
            department: Department associated with risk
        """
        if user_id:
            self._user_risks[user_id].append(risk)
        if role_id:
            self._role_risks[role_id].append(risk)
        if department:
            self._department_risks[department].append(risk)

    def index_analysis_result(self, result: RiskAnalysisResult):
        """
        Index all risks from an analysis result.

        Args:
            result: Analysis result to index
        """
        for risk in result.risks:
            self.index_risk(
                risk,
                user_id=result.user_id,
                role_id=result.role_id,
            )

        # Add to trend analyzer
        self.trend_analyzer.add_snapshot(
            timestamp=result.analyzed_at,
            risks=result.risks,
            metadata={
                "analysis_id": result.analysis_id,
                "user_id": result.user_id,
            }
        )

    # =========================================================================
    # Risk Heatmaps
    # =========================================================================

    def get_user_category_heatmap(
        self,
        user_ids: Optional[List[str]] = None,
        top_n: int = 20
    ) -> List[RiskHeatmapCell]:
        """
        Generate user vs category risk heatmap.

        Args:
            user_ids: Specific users (None for all)
            top_n: Limit to top N users by risk

        Returns:
            Heatmap cells
        """
        cells = []

        # Filter users
        users = user_ids or list(self._user_risks.keys())

        # Calculate risk scores per user
        user_scores = []
        for user_id in users:
            risks = self._user_risks.get(user_id, [])
            total_score = sum(r.final_score for r in risks)
            user_scores.append((user_id, total_score, risks))

        # Sort by score and take top N
        user_scores.sort(key=lambda x: x[1], reverse=True)
        top_users = user_scores[:top_n]

        # Find max for normalization
        max_score = max((s[1] for s in top_users), default=1)

        for user_id, total_score, risks in top_users:
            # Count by category
            by_category = defaultdict(list)
            for risk in risks:
                by_category[risk.category].append(risk)

            for category in RiskCategory:
                cat_risks = by_category.get(category, [])
                cat_score = sum(r.final_score for r in cat_risks)

                cells.append(RiskHeatmapCell(
                    row_id=user_id,
                    row_name=user_id,
                    column_id=category.value,
                    column_name=category.value.replace("_", " ").title(),
                    risk_count=len(cat_risks),
                    severity_score=cat_score,
                    color_intensity=cat_score / max_score if max_score > 0 else 0,
                ))

        return cells

    def get_role_severity_heatmap(
        self,
        role_ids: Optional[List[str]] = None,
        top_n: int = 20
    ) -> List[RiskHeatmapCell]:
        """
        Generate role vs severity risk heatmap.

        Args:
            role_ids: Specific roles (None for all)
            top_n: Limit to top N roles

        Returns:
            Heatmap cells
        """
        cells = []

        roles = role_ids or list(self._role_risks.keys())

        # Calculate totals
        role_totals = []
        for role_id in roles:
            risks = self._role_risks.get(role_id, [])
            role_totals.append((role_id, len(risks), risks))

        role_totals.sort(key=lambda x: x[1], reverse=True)
        top_roles = role_totals[:top_n]

        max_count = max((r[1] for r in top_roles), default=1)

        for role_id, total, risks in top_roles:
            by_severity = defaultdict(list)
            for risk in risks:
                by_severity[risk.severity].append(risk)

            for severity in RiskSeverity:
                sev_risks = by_severity.get(severity, [])

                cells.append(RiskHeatmapCell(
                    row_id=role_id,
                    row_name=role_id,
                    column_id=severity.value,
                    column_name=severity.value.title(),
                    risk_count=len(sev_risks),
                    severity_score=len(sev_risks) * self.SEVERITY_MULTIPLIERS[severity],
                    color_intensity=len(sev_risks) / max_count if max_count > 0 else 0,
                ))

        return cells

    # =========================================================================
    # Risk Concentration / Leaderboards
    # =========================================================================

    def get_high_risk_users(
        self,
        top_n: int = 10,
        min_critical: int = 0
    ) -> List[RiskConcentration]:
        """
        Get leaderboard of high-risk users.

        Args:
            top_n: Number of users to return
            min_critical: Minimum critical risks to include

        Returns:
            Risk concentration metrics for top users
        """
        concentrations = []
        total_risks = sum(len(risks) for risks in self._user_risks.values())

        for user_id, risks in self._user_risks.items():
            critical_count = len([r for r in risks if r.severity == RiskSeverity.CRITICAL])

            if critical_count < min_critical:
                continue

            total_score = sum(r.final_score for r in risks)
            avg_score = total_score / len(risks) if risks else 0

            concentrations.append(RiskConcentration(
                entity_type="user",
                entity_id=user_id,
                entity_name=user_id,
                total_risks=len(risks),
                critical_risks=critical_count,
                risk_score=avg_score,
                percentage_of_total=(len(risks) / total_risks * 100) if total_risks > 0 else 0,
            ))

        concentrations.sort(key=lambda x: (x.critical_risks, x.risk_score), reverse=True)
        return concentrations[:top_n]

    def get_high_risk_roles(
        self,
        top_n: int = 10
    ) -> List[RiskConcentration]:
        """
        Get leaderboard of high-risk roles.

        Args:
            top_n: Number of roles to return

        Returns:
            Risk concentration metrics for top roles
        """
        concentrations = []
        total_risks = sum(len(risks) for risks in self._role_risks.values())

        for role_id, risks in self._role_risks.items():
            critical_count = len([r for r in risks if r.severity == RiskSeverity.CRITICAL])
            total_score = sum(r.final_score for r in risks)
            avg_score = total_score / len(risks) if risks else 0

            concentrations.append(RiskConcentration(
                entity_type="role",
                entity_id=role_id,
                entity_name=role_id,
                total_risks=len(risks),
                critical_risks=critical_count,
                risk_score=avg_score,
                percentage_of_total=(len(risks) / total_risks * 100) if total_risks > 0 else 0,
            ))

        concentrations.sort(key=lambda x: (x.critical_risks, x.risk_score), reverse=True)
        return concentrations[:top_n]

    def get_department_risk_summary(self) -> List[RiskConcentration]:
        """
        Get risk summary by department.

        Returns:
            Risk concentration metrics for each department
        """
        concentrations = []
        total_risks = sum(len(risks) for risks in self._department_risks.values())

        for dept, risks in self._department_risks.items():
            critical_count = len([r for r in risks if r.severity == RiskSeverity.CRITICAL])
            total_score = sum(r.final_score for r in risks)
            avg_score = total_score / len(risks) if risks else 0

            concentrations.append(RiskConcentration(
                entity_type="department",
                entity_id=dept,
                entity_name=dept,
                total_risks=len(risks),
                critical_risks=critical_count,
                risk_score=avg_score,
                percentage_of_total=(len(risks) / total_risks * 100) if total_risks > 0 else 0,
            ))

        concentrations.sort(key=lambda x: x.risk_score, reverse=True)
        return concentrations

    # =========================================================================
    # Economic Risk Quantification
    # =========================================================================

    def calculate_economic_exposure(
        self,
        risks: Optional[List[Risk]] = None,
        custom_impact_factors: Optional[Dict[RiskCategory, float]] = None
    ) -> EconomicRiskMetrics:
        """
        Calculate economic risk exposure.

        Args:
            risks: Risks to analyze (None for all indexed)
            custom_impact_factors: Override default impact factors

        Returns:
            Economic metrics
        """
        if risks is None:
            risks = []
            for user_risks in self._user_risks.values():
                risks.extend(user_risks)

        impact_factors = custom_impact_factors or self.CATEGORY_IMPACT_FACTORS

        metrics = EconomicRiskMetrics()
        exposure_by_category = defaultdict(float)

        for risk in risks:
            # Base exposure from category
            base_impact = impact_factors.get(risk.category, 50000)

            # Apply severity multiplier
            severity_mult = self.SEVERITY_MULTIPLIERS.get(risk.severity, 1.0)

            # Apply risk score factor (0-100 normalized)
            score_factor = risk.final_score / 100

            # Calculate exposure
            exposure = base_impact * severity_mult * score_factor

            exposure_by_category[risk.category.value] += exposure
            metrics.total_exposure += exposure

            # Track specific risk types
            if risk.category == RiskCategory.FRAUD:
                metrics.fraud_exposure += exposure
            elif risk.category in [RiskCategory.COMPLIANCE, RiskCategory.DATA_PRIVACY]:
                metrics.regulatory_penalty_risk += exposure

        # Calculate annual loss expectancy (ALE = SLE * ARO)
        # Assume annual rate of occurrence based on risk count
        aro = min(0.5, len(risks) * 0.01)  # Cap at 50%
        metrics.annual_loss_expectancy = metrics.total_exposure * aro

        # Operational cost (assume 10% of exposure for monitoring/controls)
        metrics.operational_cost = metrics.total_exposure * 0.10

        metrics.exposure_by_category = dict(exposure_by_category)

        # Confidence based on data quality
        metrics.confidence_level = min(0.95, 0.5 + (len(risks) * 0.005))

        return metrics

    def estimate_remediation_roi(
        self,
        risks: List[Risk],
        remediation_cost: float
    ) -> Dict[str, Any]:
        """
        Estimate ROI of remediating given risks.

        Args:
            risks: Risks to remediate
            remediation_cost: Estimated cost to remediate

        Returns:
            ROI analysis
        """
        current_exposure = self.calculate_economic_exposure(risks)

        # Assume 90% risk reduction after remediation
        residual_exposure = current_exposure.total_exposure * 0.10

        risk_reduction = current_exposure.total_exposure - residual_exposure
        roi = ((risk_reduction - remediation_cost) / remediation_cost * 100) if remediation_cost > 0 else 0

        return {
            "current_exposure": current_exposure.total_exposure,
            "remediation_cost": remediation_cost,
            "residual_exposure": residual_exposure,
            "risk_reduction": risk_reduction,
            "roi_percentage": roi,
            "payback_period_months": (remediation_cost / (risk_reduction / 12)) if risk_reduction > 0 else float("inf"),
            "recommendation": "proceed" if roi > 50 else "review" if roi > 0 else "reconsider",
        }

    # =========================================================================
    # Control Effectiveness
    # =========================================================================

    def record_control_application(
        self,
        control_id: str,
        control_name: str,
        user_id: str,
        risks_covered: int,
        prevented_incident: bool = False
    ):
        """
        Record a control application for effectiveness tracking.

        Args:
            control_id: Control identifier
            control_name: Control name
            user_id: User the control was applied to
            risks_covered: Number of risks covered
            prevented_incident: Whether an incident was prevented
        """
        stats = self._control_stats[control_id]
        stats["name"] = control_name
        stats["applied"] += 1
        stats["risks_covered"] += risks_covered
        stats["users"].add(user_id)
        if prevented_incident:
            stats["prevented"] += 1

    def record_control_override(self, control_id: str):
        """Record when a control approval was overridden."""
        self._control_stats[control_id]["overrides"] += 1

    def record_control_exception(self, control_id: str):
        """Record when an exception was granted."""
        self._control_stats[control_id]["exceptions"] += 1

    def record_risk_recurrence(self, control_id: str):
        """Record when a mitigated risk recurred."""
        self._control_stats[control_id]["recurrences"] += 1

    def record_remediation_time(self, control_id: str, hours: float):
        """Record time to remediate with this control."""
        self._control_stats[control_id]["remediation_times"].append(hours)

    def get_control_effectiveness(
        self,
        control_id: Optional[str] = None
    ) -> List[ControlEffectivenessMetrics]:
        """
        Get control effectiveness metrics.

        Args:
            control_id: Specific control (None for all)

        Returns:
            Effectiveness metrics for controls
        """
        results = []

        controls = [control_id] if control_id else list(self._control_stats.keys())

        for cid in controls:
            stats = self._control_stats.get(cid)
            if not stats:
                continue

            applied = stats["applied"]
            if applied == 0:
                continue

            remediation_times = stats.get("remediation_times", [])
            avg_remediation = statistics.mean(remediation_times) if remediation_times else 0

            # Calculate effectiveness score
            prevention_rate = stats["prevented"] / applied if applied > 0 else 0
            override_rate = stats["overrides"] / applied if applied > 0 else 0
            exception_rate = stats["exceptions"] / applied if applied > 0 else 0
            recurrence_rate = stats["recurrences"] / applied if applied > 0 else 0

            # Weighted effectiveness: high prevention, low overrides/exceptions/recurrence
            effectiveness = (
                (prevention_rate * 40) +
                ((1 - override_rate) * 20) +
                ((1 - exception_rate) * 20) +
                ((1 - recurrence_rate) * 20)
            )

            metrics = ControlEffectivenessMetrics(
                control_id=cid,
                control_name=stats.get("name", cid),
                times_applied=applied,
                risks_covered=stats["risks_covered"],
                unique_users=len(stats["users"]),
                prevented_incidents=stats["prevented"],
                risk_reduction_pct=prevention_rate * 100,
                avg_time_to_remediate=avg_remediation,
                approval_override_rate=override_rate,
                exception_rate=exception_rate,
                recurrence_rate=recurrence_rate,
                effectiveness_score=effectiveness,
            )
            results.append(metrics)

        results.sort(key=lambda x: x.effectiveness_score, reverse=True)
        return results

    # =========================================================================
    # Dashboard Summaries
    # =========================================================================

    def get_executive_summary(self) -> Dict[str, Any]:
        """
        Get executive-level risk summary.

        Returns:
            High-level metrics for executives
        """
        all_risks = []
        for user_risks in self._user_risks.values():
            all_risks.extend(user_risks)

        # Deduplicate by risk_id
        unique_risks = {r.risk_id: r for r in all_risks}
        risks = list(unique_risks.values())

        economic = self.calculate_economic_exposure(risks)

        by_severity = defaultdict(int)
        by_category = defaultdict(int)
        by_status = defaultdict(int)

        for risk in risks:
            by_severity[risk.severity.value] += 1
            by_category[risk.category.value] += 1
            by_status[risk.status.value] += 1

        return {
            "total_risks": len(risks),
            "unique_users_at_risk": len(self._user_risks),
            "unique_roles_at_risk": len(self._role_risks),
            "by_severity": dict(by_severity),
            "by_category": dict(by_category),
            "by_status": dict(by_status),
            "economic_exposure": {
                "total": economic.total_exposure,
                "annual_loss_expectancy": economic.annual_loss_expectancy,
                "fraud_exposure": economic.fraud_exposure,
                "regulatory_risk": economic.regulatory_penalty_risk,
            },
            "top_risk_users": [
                c.to_dict() for c in self.get_high_risk_users(top_n=5)
            ],
            "top_risk_roles": [
                c.to_dict() for c in self.get_high_risk_roles(top_n=5)
            ],
            "generated_at": datetime.now().isoformat(),
        }

    def get_risk_distribution(self) -> Dict[str, Any]:
        """
        Get risk distribution statistics.

        Returns:
            Distribution metrics
        """
        all_risks = []
        for user_risks in self._user_risks.values():
            all_risks.extend(user_risks)

        if not all_risks:
            return {"error": "No risks indexed"}

        scores = [r.final_score for r in all_risks]

        return {
            "total_risks": len(all_risks),
            "score_distribution": {
                "min": min(scores),
                "max": max(scores),
                "mean": statistics.mean(scores),
                "median": statistics.median(scores),
                "stdev": statistics.stdev(scores) if len(scores) > 1 else 0,
            },
            "percentiles": {
                "p25": sorted(scores)[len(scores) // 4] if scores else 0,
                "p50": statistics.median(scores),
                "p75": sorted(scores)[3 * len(scores) // 4] if scores else 0,
                "p90": sorted(scores)[int(len(scores) * 0.9)] if scores else 0,
            },
            "severity_distribution": {
                severity.value: len([r for r in all_risks if r.severity == severity])
                for severity in RiskSeverity
            },
        }
