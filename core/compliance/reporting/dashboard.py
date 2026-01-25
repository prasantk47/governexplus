# Auditor Dashboard
# Unified compliance dashboard for GOVERNEX+

"""
Auditor Dashboard - The single pane of glass for compliance monitoring.

This dashboard provides:
- Real-time compliance metrics
- Risk heat maps
- Trend analytics
- Executive summaries
- Drill-down capabilities

Designed to answer the auditor's first question:
"Show me the overall compliance posture."
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, date, timedelta
from enum import Enum
import uuid

from .models import (
    User, Role, RoleAssignment, SoDViolation, FirefighterUsage,
    ChangeLogEntry, LoginEvent, SecurityEvent,
    UserStatus, RiskLevel, ReportResult, ReportFormat
)


# ============================================================
# DASHBOARD ENUMS
# ============================================================

class DashboardTimeRange(Enum):
    """Time ranges for dashboard views."""
    TODAY = "TODAY"
    LAST_7_DAYS = "LAST_7_DAYS"
    LAST_30_DAYS = "LAST_30_DAYS"
    LAST_90_DAYS = "LAST_90_DAYS"
    LAST_YEAR = "LAST_YEAR"
    CUSTOM = "CUSTOM"


class ComplianceStatus(Enum):
    """Overall compliance status."""
    COMPLIANT = "COMPLIANT"
    AT_RISK = "AT_RISK"
    NON_COMPLIANT = "NON_COMPLIANT"
    UNDER_REVIEW = "UNDER_REVIEW"


class MetricTrend(Enum):
    """Trend direction for metrics."""
    IMPROVING = "IMPROVING"
    STABLE = "STABLE"
    DECLINING = "DECLINING"
    CRITICAL = "CRITICAL"


# ============================================================
# COMPLIANCE METRICS
# ============================================================

@dataclass
class MetricValue:
    """Single metric with trend information."""
    name: str = ""
    value: float = 0
    previous_value: float = 0
    unit: str = ""  # "count", "percent", "score"

    # Trend
    trend: MetricTrend = MetricTrend.STABLE
    change_percent: float = 0

    # Thresholds
    warning_threshold: float = 0
    critical_threshold: float = 0
    is_warning: bool = False
    is_critical: bool = False

    def calculate_trend(self) -> None:
        """Calculate trend based on previous value."""
        if self.previous_value == 0:
            self.change_percent = 0
            self.trend = MetricTrend.STABLE
            return

        self.change_percent = ((self.value - self.previous_value) / self.previous_value) * 100

        # For metrics where lower is better (violations, risks)
        if self.change_percent < -5:
            self.trend = MetricTrend.IMPROVING
        elif self.change_percent > 10:
            self.trend = MetricTrend.DECLINING
        elif self.change_percent > 25:
            self.trend = MetricTrend.CRITICAL
        else:
            self.trend = MetricTrend.STABLE

    def check_thresholds(self) -> None:
        """Check if value exceeds thresholds."""
        self.is_warning = self.value >= self.warning_threshold if self.warning_threshold > 0 else False
        self.is_critical = self.value >= self.critical_threshold if self.critical_threshold > 0 else False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "value": self.value,
            "previous_value": self.previous_value,
            "unit": self.unit,
            "trend": self.trend.value,
            "change_percent": round(self.change_percent, 2),
            "is_warning": self.is_warning,
            "is_critical": self.is_critical,
        }


@dataclass
class ComplianceMetrics:
    """
    Compliance metrics aggregator.

    Provides key metrics auditors care about:
    - User compliance (terminated users, generic accounts)
    - Access compliance (SoD violations, critical access)
    - Operational compliance (firefighter usage, change frequency)
    - Security compliance (failed logins, anomalies)
    """

    metrics_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    generated_at: datetime = field(default_factory=datetime.now)
    time_range: DashboardTimeRange = DashboardTimeRange.LAST_30_DAYS

    # Overall status
    compliance_status: ComplianceStatus = ComplianceStatus.COMPLIANT
    compliance_score: int = 100  # 0-100
    previous_score: int = 100

    # User Metrics
    total_users: int = 0
    active_users: int = 0
    terminated_with_access: int = 0
    generic_accounts: int = 0
    users_never_logged_in: int = 0
    users_inactive_90_days: int = 0

    # Access Metrics
    total_sod_violations: int = 0
    unmitigated_sod_violations: int = 0
    critical_sod_violations: int = 0
    users_with_critical_access: int = 0
    users_with_sap_all: int = 0

    # Role Metrics
    total_roles: int = 0
    orphaned_roles: int = 0
    roles_not_reviewed: int = 0
    overprivileged_users: int = 0

    # Firefighter Metrics
    firefighter_sessions: int = 0
    unreviewed_ff_sessions: int = 0
    ff_policy_violations: int = 0
    avg_ff_duration_minutes: float = 0

    # Change Metrics
    user_changes: int = 0
    role_changes: int = 0
    emergency_changes: int = 0
    unauthorized_changes: int = 0

    # Security Metrics
    failed_login_attempts: int = 0
    brute_force_attempts: int = 0
    anomalous_logins: int = 0
    security_events: int = 0

    # Individual metric objects with trends
    metric_details: Dict[str, MetricValue] = field(default_factory=dict)

    def calculate_compliance_score(self) -> int:
        """
        Calculate overall compliance score (0-100).

        Scoring weights:
        - SoD violations: 30%
        - User compliance: 25%
        - Firefighter compliance: 20%
        - Security: 15%
        - Change management: 10%
        """
        score = 100

        # SoD deductions (30 points max)
        if self.unmitigated_sod_violations > 0:
            sod_deduction = min(30, self.unmitigated_sod_violations * 2)
            score -= sod_deduction

        # User compliance deductions (25 points max)
        if self.terminated_with_access > 0:
            score -= min(15, self.terminated_with_access * 5)
        if self.generic_accounts > 5:
            score -= min(10, (self.generic_accounts - 5))

        # Firefighter deductions (20 points max)
        if self.unreviewed_ff_sessions > 0:
            score -= min(10, self.unreviewed_ff_sessions * 2)
        if self.ff_policy_violations > 0:
            score -= min(10, self.ff_policy_violations * 5)

        # Security deductions (15 points max)
        if self.brute_force_attempts > 0:
            score -= min(10, self.brute_force_attempts)
        if self.anomalous_logins > 0:
            score -= min(5, self.anomalous_logins)

        # Change management deductions (10 points max)
        if self.unauthorized_changes > 0:
            score -= min(10, self.unauthorized_changes * 5)

        self.compliance_score = max(0, score)
        self._determine_status()
        return self.compliance_score

    def _determine_status(self) -> None:
        """Determine overall compliance status based on score."""
        if self.compliance_score >= 90:
            self.compliance_status = ComplianceStatus.COMPLIANT
        elif self.compliance_score >= 70:
            self.compliance_status = ComplianceStatus.AT_RISK
        else:
            self.compliance_status = ComplianceStatus.NON_COMPLIANT

    def generate_metric_details(self) -> None:
        """Generate detailed metric objects with trends."""
        self.metric_details = {
            "sod_violations": MetricValue(
                name="Unmitigated SoD Violations",
                value=self.unmitigated_sod_violations,
                unit="count",
                warning_threshold=5,
                critical_threshold=10,
            ),
            "terminated_users": MetricValue(
                name="Terminated Users with Access",
                value=self.terminated_with_access,
                unit="count",
                warning_threshold=1,
                critical_threshold=5,
            ),
            "firefighter_unreviewed": MetricValue(
                name="Unreviewed FF Sessions",
                value=self.unreviewed_ff_sessions,
                unit="count",
                warning_threshold=3,
                critical_threshold=10,
            ),
            "failed_logins": MetricValue(
                name="Failed Login Attempts",
                value=self.failed_login_attempts,
                unit="count",
                warning_threshold=100,
                critical_threshold=500,
            ),
            "compliance_score": MetricValue(
                name="Compliance Score",
                value=self.compliance_score,
                previous_value=self.previous_score,
                unit="score",
            ),
        }

        for metric in self.metric_details.values():
            metric.calculate_trend()
            metric.check_thresholds()

    def get_critical_findings(self) -> List[Dict[str, Any]]:
        """Get list of critical findings requiring immediate attention."""
        findings = []

        if self.terminated_with_access > 0:
            findings.append({
                "type": "TERMINATED_USER_ACCESS",
                "severity": "CRITICAL",
                "count": self.terminated_with_access,
                "message": f"{self.terminated_with_access} terminated user(s) still have active access",
                "action": "Immediately revoke all access for terminated employees",
            })

        if self.users_with_sap_all > 0:
            findings.append({
                "type": "SAP_ALL_ACCESS",
                "severity": "CRITICAL",
                "count": self.users_with_sap_all,
                "message": f"{self.users_with_sap_all} user(s) have SAP_ALL or equivalent",
                "action": "Review and remediate full authorization assignments",
            })

        if self.critical_sod_violations > 0:
            findings.append({
                "type": "CRITICAL_SOD",
                "severity": "HIGH",
                "count": self.critical_sod_violations,
                "message": f"{self.critical_sod_violations} critical SoD violation(s) detected",
                "action": "Implement mitigating controls or remediate access",
            })

        if self.ff_policy_violations > 0:
            findings.append({
                "type": "FF_POLICY_VIOLATION",
                "severity": "HIGH",
                "count": self.ff_policy_violations,
                "message": f"{self.ff_policy_violations} firefighter policy violation(s)",
                "action": "Review and escalate emergency access violations",
            })

        if self.brute_force_attempts > 0:
            findings.append({
                "type": "BRUTE_FORCE",
                "severity": "HIGH",
                "count": self.brute_force_attempts,
                "message": f"{self.brute_force_attempts} potential brute force attack(s)",
                "action": "Investigate source IPs and consider blocking",
            })

        return findings

    def to_dict(self) -> Dict[str, Any]:
        return {
            "metrics_id": self.metrics_id,
            "generated_at": self.generated_at.isoformat(),
            "compliance_status": self.compliance_status.value,
            "compliance_score": self.compliance_score,
            "score_trend": "UP" if self.compliance_score > self.previous_score else "DOWN" if self.compliance_score < self.previous_score else "STABLE",
            "user_metrics": {
                "total_users": self.total_users,
                "active_users": self.active_users,
                "terminated_with_access": self.terminated_with_access,
                "generic_accounts": self.generic_accounts,
                "inactive_90_days": self.users_inactive_90_days,
            },
            "access_metrics": {
                "total_sod_violations": self.total_sod_violations,
                "unmitigated_sod_violations": self.unmitigated_sod_violations,
                "critical_sod_violations": self.critical_sod_violations,
                "users_with_critical_access": self.users_with_critical_access,
            },
            "firefighter_metrics": {
                "total_sessions": self.firefighter_sessions,
                "unreviewed_sessions": self.unreviewed_ff_sessions,
                "policy_violations": self.ff_policy_violations,
            },
            "security_metrics": {
                "failed_logins": self.failed_login_attempts,
                "brute_force_attempts": self.brute_force_attempts,
                "anomalous_logins": self.anomalous_logins,
            },
            "critical_findings": self.get_critical_findings(),
            "metric_details": {k: v.to_dict() for k, v in self.metric_details.items()},
        }


# ============================================================
# RISK HEAT MAP
# ============================================================

@dataclass
class HeatMapCell:
    """Single cell in a heat map."""
    row_label: str = ""
    column_label: str = ""
    value: int = 0
    risk_level: RiskLevel = RiskLevel.LOW
    tooltip: str = ""
    drill_down_filter: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "row": self.row_label,
            "column": self.column_label,
            "value": self.value,
            "risk_level": self.risk_level.value,
            "tooltip": self.tooltip,
            "drill_down": self.drill_down_filter,
        }


@dataclass
class RiskHeatmap:
    """
    Risk heat map visualization.

    Supports multiple heat map types:
    - SoD by Department vs Business Function
    - Critical Access by Department vs Transaction Category
    - Firefighter Usage by Department vs Week
    - Risk Score by User vs Application
    """

    heatmap_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    heatmap_type: str = ""  # SOD, CRITICAL_ACCESS, FIREFIGHTER, RISK_SCORE
    title: str = ""

    # Dimensions
    row_dimension: str = ""  # e.g., "department"
    column_dimension: str = ""  # e.g., "business_function"
    row_labels: List[str] = field(default_factory=list)
    column_labels: List[str] = field(default_factory=list)

    # Data
    cells: List[HeatMapCell] = field(default_factory=list)

    # Aggregations
    row_totals: Dict[str, int] = field(default_factory=dict)
    column_totals: Dict[str, int] = field(default_factory=dict)
    grand_total: int = 0

    # Thresholds for coloring
    low_threshold: int = 1
    medium_threshold: int = 3
    high_threshold: int = 5
    critical_threshold: int = 10

    def add_cell(self, row: str, column: str, value: int, details: str = "") -> None:
        """Add a cell to the heat map."""
        # Determine risk level based on value
        if value >= self.critical_threshold:
            risk_level = RiskLevel.CRITICAL
        elif value >= self.high_threshold:
            risk_level = RiskLevel.HIGH
        elif value >= self.medium_threshold:
            risk_level = RiskLevel.MEDIUM
        else:
            risk_level = RiskLevel.LOW

        cell = HeatMapCell(
            row_label=row,
            column_label=column,
            value=value,
            risk_level=risk_level,
            tooltip=f"{row} / {column}: {value} {details}",
            drill_down_filter={
                self.row_dimension: row,
                self.column_dimension: column,
            }
        )
        self.cells.append(cell)

        # Track labels
        if row not in self.row_labels:
            self.row_labels.append(row)
        if column not in self.column_labels:
            self.column_labels.append(column)

        # Update totals
        self.row_totals[row] = self.row_totals.get(row, 0) + value
        self.column_totals[column] = self.column_totals.get(column, 0) + value
        self.grand_total += value

    def get_cell(self, row: str, column: str) -> Optional[HeatMapCell]:
        """Get a specific cell."""
        for cell in self.cells:
            if cell.row_label == row and cell.column_label == column:
                return cell
        return None

    def get_top_risk_areas(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get top risk areas by value."""
        sorted_cells = sorted(self.cells, key=lambda x: x.value, reverse=True)
        return [
            {
                "row": cell.row_label,
                "column": cell.column_label,
                "value": cell.value,
                "risk_level": cell.risk_level.value,
            }
            for cell in sorted_cells[:limit]
        ]

    def to_dict(self) -> Dict[str, Any]:
        # Create matrix format for easy rendering
        matrix = {}
        for cell in self.cells:
            if cell.row_label not in matrix:
                matrix[cell.row_label] = {}
            matrix[cell.row_label][cell.column_label] = {
                "value": cell.value,
                "risk_level": cell.risk_level.value,
            }

        return {
            "heatmap_id": self.heatmap_id,
            "heatmap_type": self.heatmap_type,
            "title": self.title,
            "row_dimension": self.row_dimension,
            "column_dimension": self.column_dimension,
            "row_labels": self.row_labels,
            "column_labels": self.column_labels,
            "matrix": matrix,
            "row_totals": self.row_totals,
            "column_totals": self.column_totals,
            "grand_total": self.grand_total,
            "top_risk_areas": self.get_top_risk_areas(),
        }

    @classmethod
    def create_sod_heatmap(cls, violations: List[SoDViolation]) -> "RiskHeatmap":
        """Create SoD heat map from violations."""
        heatmap = cls(
            heatmap_type="SOD",
            title="SoD Violations by Department and Business Function",
            row_dimension="department",
            column_dimension="business_function",
        )

        # Aggregate by department and function
        aggregated: Dict[str, Dict[str, int]] = {}
        for v in violations:
            dept = v.user_department or "Unknown"
            # Extract function from rule name
            func = v.rule_name.split("-")[0] if "-" in v.rule_name else "General"

            if dept not in aggregated:
                aggregated[dept] = {}
            aggregated[dept][func] = aggregated[dept].get(func, 0) + 1

        # Add cells
        for dept, funcs in aggregated.items():
            for func, count in funcs.items():
                heatmap.add_cell(dept, func, count, "violations")

        return heatmap

    @classmethod
    def create_ff_heatmap(cls, usages: List[FirefighterUsage], weeks: int = 8) -> "RiskHeatmap":
        """Create firefighter usage heat map over time."""
        heatmap = cls(
            heatmap_type="FIREFIGHTER",
            title=f"Firefighter Usage by Department (Last {weeks} Weeks)",
            row_dimension="department",
            column_dimension="week",
            low_threshold=2,
            medium_threshold=5,
            high_threshold=10,
            critical_threshold=20,
        )

        # Group by department and week
        now = datetime.now()
        aggregated: Dict[str, Dict[str, int]] = {}

        for usage in usages:
            dept = usage.user_department or "Unknown"
            week_num = ((now - usage.checkout_time).days // 7) + 1
            week_label = f"Week {week_num}"

            if week_num > weeks:
                continue

            if dept not in aggregated:
                aggregated[dept] = {}
            aggregated[dept][week_label] = aggregated[dept].get(week_label, 0) + 1

        # Generate week labels
        week_labels = [f"Week {i}" for i in range(1, weeks + 1)]

        # Add cells
        for dept, weeks_data in aggregated.items():
            for week_label in week_labels:
                count = weeks_data.get(week_label, 0)
                if count > 0:
                    heatmap.add_cell(dept, week_label, count, "sessions")

        return heatmap


# ============================================================
# TREND ANALYTICS
# ============================================================

@dataclass
class TrendDataPoint:
    """Single data point in a trend."""
    date: date = field(default_factory=date.today)
    value: float = 0
    label: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "date": self.date.isoformat(),
            "value": self.value,
            "label": self.label,
        }


@dataclass
class TrendSeries:
    """Time series data for trending."""
    series_id: str = ""
    name: str = ""
    data_points: List[TrendDataPoint] = field(default_factory=list)

    # Statistics
    current_value: float = 0
    average: float = 0
    min_value: float = 0
    max_value: float = 0
    trend_direction: str = "STABLE"  # UP, DOWN, STABLE

    def calculate_stats(self) -> None:
        """Calculate trend statistics."""
        if not self.data_points:
            return

        values = [dp.value for dp in self.data_points]
        self.current_value = values[-1] if values else 0
        self.average = sum(values) / len(values)
        self.min_value = min(values)
        self.max_value = max(values)

        # Determine trend direction (compare last 3 to first 3)
        if len(values) >= 6:
            first_avg = sum(values[:3]) / 3
            last_avg = sum(values[-3:]) / 3
            if last_avg > first_avg * 1.1:
                self.trend_direction = "UP"
            elif last_avg < first_avg * 0.9:
                self.trend_direction = "DOWN"
            else:
                self.trend_direction = "STABLE"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "series_id": self.series_id,
            "name": self.name,
            "data": [dp.to_dict() for dp in self.data_points],
            "stats": {
                "current": self.current_value,
                "average": round(self.average, 2),
                "min": self.min_value,
                "max": self.max_value,
                "trend": self.trend_direction,
            }
        }


@dataclass
class TrendAnalytics:
    """
    Trend analytics for compliance metrics over time.

    Tracks:
    - SoD violations over time
    - Compliance score history
    - Firefighter usage trends
    - Security incident trends
    - Change velocity
    """

    analytics_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    generated_at: datetime = field(default_factory=datetime.now)
    time_range: DashboardTimeRange = DashboardTimeRange.LAST_90_DAYS

    # Trend series
    series: Dict[str, TrendSeries] = field(default_factory=dict)

    # Forecasts
    forecasts: Dict[str, float] = field(default_factory=dict)

    # Annotations (events that affected trends)
    annotations: List[Dict[str, Any]] = field(default_factory=list)

    def add_series(self, series: TrendSeries) -> None:
        """Add a trend series."""
        series.calculate_stats()
        self.series[series.series_id] = series

    def add_annotation(self, date: date, label: str, description: str) -> None:
        """Add an annotation to the trend (e.g., policy change, audit)."""
        self.annotations.append({
            "date": date.isoformat(),
            "label": label,
            "description": description,
        })

    def generate_sod_trend(self, violations: List[SoDViolation], days: int = 90) -> TrendSeries:
        """Generate SoD violation trend."""
        series = TrendSeries(
            series_id="sod_violations",
            name="SoD Violations",
        )

        # Group by date
        today = date.today()
        daily_counts: Dict[date, int] = {}

        for v in violations:
            v_date = v.detected_date.date() if isinstance(v.detected_date, datetime) else v.detected_date
            if (today - v_date).days <= days:
                daily_counts[v_date] = daily_counts.get(v_date, 0) + 1

        # Create weekly aggregates
        for i in range(0, days, 7):
            week_start = today - timedelta(days=i + 7)
            week_end = today - timedelta(days=i)
            week_count = sum(
                count for d, count in daily_counts.items()
                if week_start <= d < week_end
            )
            series.data_points.append(TrendDataPoint(
                date=week_end,
                value=week_count,
                label=f"Week ending {week_end.isoformat()}",
            ))

        series.data_points.reverse()  # Chronological order
        series.calculate_stats()
        return series

    def generate_compliance_score_trend(self, historical_scores: List[Dict[str, Any]]) -> TrendSeries:
        """Generate compliance score trend."""
        series = TrendSeries(
            series_id="compliance_score",
            name="Compliance Score",
        )

        for entry in historical_scores:
            series.data_points.append(TrendDataPoint(
                date=entry.get("date", date.today()),
                value=entry.get("score", 0),
            ))

        series.calculate_stats()
        return series

    def generate_ff_usage_trend(self, usages: List[FirefighterUsage], days: int = 90) -> TrendSeries:
        """Generate firefighter usage trend."""
        series = TrendSeries(
            series_id="ff_usage",
            name="Firefighter Sessions",
        )

        today = date.today()
        weekly_counts: Dict[date, int] = {}

        for usage in usages:
            usage_date = usage.checkout_time.date()
            week_start = usage_date - timedelta(days=usage_date.weekday())
            if (today - usage_date).days <= days:
                weekly_counts[week_start] = weekly_counts.get(week_start, 0) + 1

        for week_start, count in sorted(weekly_counts.items()):
            series.data_points.append(TrendDataPoint(
                date=week_start,
                value=count,
            ))

        series.calculate_stats()
        return series

    def get_insights(self) -> List[Dict[str, Any]]:
        """Generate insights from trend data."""
        insights = []

        for series_id, series in self.series.items():
            if series.trend_direction == "UP" and series_id in ["sod_violations", "ff_usage"]:
                insights.append({
                    "type": "WARNING",
                    "metric": series.name,
                    "message": f"{series.name} is trending upward - increased {int((series.current_value / series.average - 1) * 100)}% from average",
                    "recommendation": "Investigate root cause and consider preventive measures",
                })
            elif series.trend_direction == "DOWN" and series_id == "compliance_score":
                insights.append({
                    "type": "CRITICAL",
                    "metric": series.name,
                    "message": f"Compliance score is declining - current: {series.current_value:.0f}, average: {series.average:.0f}",
                    "recommendation": "Review recent changes and address compliance gaps",
                })
            elif series.trend_direction == "DOWN" and series_id in ["sod_violations", "ff_usage"]:
                insights.append({
                    "type": "POSITIVE",
                    "metric": series.name,
                    "message": f"{series.name} is trending downward - decreased {int((1 - series.current_value / series.average) * 100)}% from average",
                    "recommendation": "Continue current controls and monitoring",
                })

        return insights

    def to_dict(self) -> Dict[str, Any]:
        return {
            "analytics_id": self.analytics_id,
            "generated_at": self.generated_at.isoformat(),
            "time_range": self.time_range.value,
            "series": {k: v.to_dict() for k, v in self.series.items()},
            "insights": self.get_insights(),
            "annotations": self.annotations,
        }


# ============================================================
# AUDITOR DASHBOARD
# ============================================================

@dataclass
class DashboardWidget:
    """Widget configuration for dashboard."""
    widget_id: str = ""
    widget_type: str = ""  # METRIC, HEATMAP, TREND, TABLE, FINDING
    title: str = ""
    position: Dict[str, int] = field(default_factory=dict)  # row, col, width, height
    data_source: str = ""
    refresh_interval_seconds: int = 300
    drill_down_report: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "widget_id": self.widget_id,
            "widget_type": self.widget_type,
            "title": self.title,
            "position": self.position,
            "data_source": self.data_source,
            "drill_down_report": self.drill_down_report,
        }


@dataclass
class AuditorDashboard:
    """
    The Auditor Dashboard - Single pane of glass for compliance.

    This is the main entry point for auditors. It provides:
    - Executive summary with compliance score
    - Critical findings requiring immediate attention
    - Risk heat maps for visual risk assessment
    - Trend charts for compliance over time
    - Quick links to detailed reports

    Designed to answer:
    1. "What is the overall compliance posture?" (Compliance Score)
    2. "What needs immediate attention?" (Critical Findings)
    3. "Where are the risk concentrations?" (Heat Maps)
    4. "Are we getting better or worse?" (Trends)
    5. "Show me the details" (Drill-down Reports)
    """

    dashboard_id: str = field(default_factory=lambda: f"DASH-{str(uuid.uuid4())[:8]}")
    name: str = "Auditor Compliance Dashboard"
    generated_at: datetime = field(default_factory=datetime.now)

    # Time range
    time_range: DashboardTimeRange = DashboardTimeRange.LAST_30_DAYS
    custom_start: Optional[date] = None
    custom_end: Optional[date] = None

    # Core components
    metrics: Optional[ComplianceMetrics] = None
    heatmaps: Dict[str, RiskHeatmap] = field(default_factory=dict)
    trends: Optional[TrendAnalytics] = None

    # Widgets
    widgets: List[DashboardWidget] = field(default_factory=list)

    # Quick access reports
    report_shortcuts: List[Dict[str, str]] = field(default_factory=list)

    # User preferences
    user_id: str = ""
    is_default: bool = True

    def initialize_default_layout(self) -> None:
        """Set up default dashboard layout."""
        self.widgets = [
            DashboardWidget(
                widget_id="compliance_score",
                widget_type="METRIC",
                title="Compliance Score",
                position={"row": 1, "col": 1, "width": 2, "height": 1},
                data_source="metrics.compliance_score",
                drill_down_report="ComplianceScorecard",
            ),
            DashboardWidget(
                widget_id="critical_findings",
                widget_type="FINDING",
                title="Critical Findings",
                position={"row": 1, "col": 3, "width": 2, "height": 2},
                data_source="metrics.critical_findings",
            ),
            DashboardWidget(
                widget_id="sod_heatmap",
                widget_type="HEATMAP",
                title="SoD Risk Heat Map",
                position={"row": 2, "col": 1, "width": 2, "height": 2},
                data_source="heatmaps.sod",
                drill_down_report="SoDConflictReport",
            ),
            DashboardWidget(
                widget_id="compliance_trend",
                widget_type="TREND",
                title="Compliance Score Trend",
                position={"row": 3, "col": 1, "width": 4, "height": 2},
                data_source="trends.compliance_score",
            ),
            DashboardWidget(
                widget_id="key_metrics",
                widget_type="METRIC",
                title="Key Metrics",
                position={"row": 4, "col": 1, "width": 4, "height": 1},
                data_source="metrics.metric_details",
            ),
        ]

        self.report_shortcuts = [
            {"name": "User Master Report", "report": "UserListReport", "icon": "users"},
            {"name": "SoD Conflicts", "report": "SoDConflictReport", "icon": "alert-triangle"},
            {"name": "Critical Access", "report": "CriticalTransactionReport", "icon": "shield"},
            {"name": "Firefighter Log", "report": "FirefighterUsageReport", "icon": "flame"},
            {"name": "Change History", "report": "UserChangeLog", "icon": "history"},
            {"name": "Login Audit", "report": "LoginAuditReport", "icon": "log-in"},
        ]

    def build_dashboard(
        self,
        users: List[User],
        violations: List[SoDViolation],
        ff_usages: List[FirefighterUsage],
        login_events: List[LoginEvent],
        changes: List[ChangeLogEntry],
        historical_scores: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        """Build dashboard from raw data."""

        # Build metrics
        self.metrics = ComplianceMetrics(
            time_range=self.time_range,
            total_users=len(users),
            active_users=len([u for u in users if u.status == UserStatus.ACTIVE]),
            terminated_with_access=len([u for u in users if u.is_terminated()]),
            generic_accounts=len([u for u in users if u.is_generic_account()]),
            users_never_logged_in=len([u for u in users if not u.last_login]),
            users_inactive_90_days=len([
                u for u in users
                if u.last_login and (datetime.now() - u.last_login).days > 90
            ]),
            total_sod_violations=len(violations),
            unmitigated_sod_violations=len([v for v in violations if not v.is_mitigated]),
            critical_sod_violations=len([v for v in violations if v.risk_level == RiskLevel.CRITICAL]),
            users_with_critical_access=len([u for u in users if u.critical_access_count > 0]),
            users_with_sap_all=len([u for u in users if "SAP_ALL" in u.roles]),
            firefighter_sessions=len(ff_usages),
            unreviewed_ff_sessions=len([f for f in ff_usages if not f.reviewed]),
            ff_policy_violations=len([f for f in ff_usages if f.critical_actions > 0 and not f.reviewed]),
            failed_login_attempts=len([e for e in login_events if not e.success]),
            brute_force_attempts=self._detect_brute_force(login_events),
            anomalous_logins=len([e for e in login_events if e.is_anomalous]),
            user_changes=len([c for c in changes if c.object_type == "USER"]),
            role_changes=len([c for c in changes if c.object_type == "ROLE"]),
        )

        self.metrics.calculate_compliance_score()
        self.metrics.generate_metric_details()

        # Build heat maps
        self.heatmaps["sod"] = RiskHeatmap.create_sod_heatmap(violations)
        self.heatmaps["firefighter"] = RiskHeatmap.create_ff_heatmap(ff_usages)

        # Build trends
        self.trends = TrendAnalytics(time_range=self.time_range)
        self.trends.add_series(self.trends.generate_sod_trend(violations))
        self.trends.add_series(self.trends.generate_ff_usage_trend(ff_usages))

        if historical_scores:
            self.trends.add_series(self.trends.generate_compliance_score_trend(historical_scores))

    def _detect_brute_force(self, events: List[LoginEvent], threshold: int = 5) -> int:
        """Detect brute force attempts (multiple failures from same IP)."""
        from collections import Counter

        failed_by_ip: Counter = Counter()
        for event in events:
            if not event.success:
                failed_by_ip[event.ip_address] += 1

        return sum(1 for ip, count in failed_by_ip.items() if count >= threshold)

    def get_executive_summary(self) -> Dict[str, Any]:
        """Generate executive summary for the dashboard."""
        if not self.metrics:
            return {}

        return {
            "compliance_score": self.metrics.compliance_score,
            "compliance_status": self.metrics.compliance_status.value,
            "headline": self._generate_headline(),
            "critical_finding_count": len(self.metrics.get_critical_findings()),
            "key_numbers": {
                "Users": self.metrics.total_users,
                "SoD Violations": self.metrics.unmitigated_sod_violations,
                "FF Sessions": self.metrics.firefighter_sessions,
                "Failed Logins": self.metrics.failed_login_attempts,
            },
            "recommendations": self._get_top_recommendations(),
        }

    def _generate_headline(self) -> str:
        """Generate dashboard headline based on status."""
        if not self.metrics:
            return "Dashboard data not loaded"

        if self.metrics.compliance_status == ComplianceStatus.COMPLIANT:
            return "Compliance posture is healthy"
        elif self.metrics.compliance_status == ComplianceStatus.AT_RISK:
            findings = len(self.metrics.get_critical_findings())
            return f"Attention needed: {findings} critical finding(s) identified"
        else:
            return "Immediate action required: Non-compliant status detected"

    def _get_top_recommendations(self, limit: int = 3) -> List[str]:
        """Get top recommendations based on findings."""
        recommendations = []

        if not self.metrics:
            return recommendations

        if self.metrics.terminated_with_access > 0:
            recommendations.append(f"Revoke access for {self.metrics.terminated_with_access} terminated user(s)")

        if self.metrics.unmitigated_sod_violations > 0:
            recommendations.append(f"Review and mitigate {self.metrics.unmitigated_sod_violations} SoD violation(s)")

        if self.metrics.unreviewed_ff_sessions > 0:
            recommendations.append(f"Review {self.metrics.unreviewed_ff_sessions} firefighter session(s)")

        if self.metrics.generic_accounts > 5:
            recommendations.append(f"Assess need for {self.metrics.generic_accounts} generic/shared accounts")

        return recommendations[:limit]

    def refresh(self) -> None:
        """Refresh dashboard data."""
        self.generated_at = datetime.now()
        # In real implementation, would re-fetch data and rebuild

    def export(self, format: ReportFormat = ReportFormat.PDF) -> Dict[str, Any]:
        """Export dashboard for reporting."""
        return {
            "dashboard_id": self.dashboard_id,
            "name": self.name,
            "generated_at": self.generated_at.isoformat(),
            "format": format.value,
            "executive_summary": self.get_executive_summary(),
            "metrics": self.metrics.to_dict() if self.metrics else {},
            "heatmaps": {k: v.to_dict() for k, v in self.heatmaps.items()},
            "trends": self.trends.to_dict() if self.trends else {},
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dashboard_id": self.dashboard_id,
            "name": self.name,
            "generated_at": self.generated_at.isoformat(),
            "time_range": self.time_range.value,
            "executive_summary": self.get_executive_summary(),
            "metrics": self.metrics.to_dict() if self.metrics else {},
            "heatmaps": {k: v.to_dict() for k, v in self.heatmaps.items()},
            "trends": self.trends.to_dict() if self.trends else {},
            "widgets": [w.to_dict() for w in self.widgets],
            "report_shortcuts": self.report_shortcuts,
        }


# ============================================================
# FACTORY FUNCTIONS
# ============================================================

def create_auditor_dashboard(
    users: List[User],
    violations: List[SoDViolation],
    ff_usages: List[FirefighterUsage],
    login_events: List[LoginEvent],
    changes: List[ChangeLogEntry],
    time_range: DashboardTimeRange = DashboardTimeRange.LAST_30_DAYS,
) -> AuditorDashboard:
    """Factory function to create a fully populated auditor dashboard."""
    dashboard = AuditorDashboard(time_range=time_range)
    dashboard.initialize_default_layout()
    dashboard.build_dashboard(
        users=users,
        violations=violations,
        ff_usages=ff_usages,
        login_events=login_events,
        changes=changes,
    )
    return dashboard


def create_executive_dashboard(
    metrics: ComplianceMetrics,
    historical_scores: List[Dict[str, Any]],
) -> AuditorDashboard:
    """Create a simplified executive dashboard."""
    dashboard = AuditorDashboard(name="Executive Compliance Summary")
    dashboard.metrics = metrics

    # Simpler widget set for executives
    dashboard.widgets = [
        DashboardWidget(
            widget_id="compliance_score",
            widget_type="METRIC",
            title="Compliance Score",
            position={"row": 1, "col": 1, "width": 4, "height": 1},
        ),
        DashboardWidget(
            widget_id="trend",
            widget_type="TREND",
            title="Score Trend",
            position={"row": 2, "col": 1, "width": 4, "height": 2},
        ),
        DashboardWidget(
            widget_id="findings",
            widget_type="FINDING",
            title="Critical Findings",
            position={"row": 3, "col": 1, "width": 4, "height": 1},
        ),
    ]

    dashboard.trends = TrendAnalytics()
    dashboard.trends.add_series(
        dashboard.trends.generate_compliance_score_trend(historical_scores)
    )

    return dashboard
