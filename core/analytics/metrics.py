"""
Metrics Collection Module

Collects and aggregates metrics from all GRC modules for dashboards.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from enum import Enum
from collections import defaultdict
import statistics


class MetricType(Enum):
    """Types of metrics"""
    COUNTER = "counter"          # Cumulative count
    GAUGE = "gauge"              # Current value
    HISTOGRAM = "histogram"      # Distribution
    RATE = "rate"                # Per-time-period rate
    PERCENTAGE = "percentage"    # Ratio as percentage


class MetricCategory(Enum):
    """Metric categories"""
    RISK = "risk"
    ACCESS = "access"
    COMPLIANCE = "compliance"
    FIREFIGHTER = "firefighter"
    CERTIFICATION = "certification"
    PERFORMANCE = "performance"
    WORKFLOW = "workflow"


@dataclass
class MetricDefinition:
    """Definition of a metric"""
    metric_id: str
    name: str
    description: str
    metric_type: MetricType
    category: MetricCategory
    unit: str = ""
    thresholds: Dict[str, float] = field(default_factory=dict)  # warning, critical


@dataclass
class MetricValue:
    """A recorded metric value"""
    metric_id: str
    value: float
    timestamp: datetime = field(default_factory=datetime.now)
    dimensions: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MetricSeries:
    """Time series of metric values"""
    metric_id: str
    values: List[MetricValue] = field(default_factory=list)

    def add(self, value: float, dimensions: Dict = None, metadata: Dict = None):
        self.values.append(MetricValue(
            metric_id=self.metric_id,
            value=value,
            dimensions=dimensions or {},
            metadata=metadata or {}
        ))

    def get_latest(self) -> Optional[MetricValue]:
        return self.values[-1] if self.values else None

    def get_average(self, window_minutes: int = 60) -> float:
        cutoff = datetime.now() - timedelta(minutes=window_minutes)
        recent = [v.value for v in self.values if v.timestamp >= cutoff]
        return statistics.mean(recent) if recent else 0.0

    def get_trend(self, periods: int = 10) -> str:
        """Determine trend direction"""
        if len(self.values) < periods:
            return "insufficient_data"

        recent = [v.value for v in self.values[-periods:]]
        first_half = statistics.mean(recent[:periods//2])
        second_half = statistics.mean(recent[periods//2:])

        diff_pct = ((second_half - first_half) / first_half * 100) if first_half else 0

        if diff_pct > 10:
            return "increasing"
        elif diff_pct < -10:
            return "decreasing"
        else:
            return "stable"


class MetricsCollector:
    """
    Centralized metrics collection and aggregation.

    Collects metrics from all GRC modules and provides
    aggregated views for dashboards.
    """

    # Standard metric definitions
    METRICS = {
        # Risk metrics
        "risk.violations.total": MetricDefinition(
            metric_id="risk.violations.total",
            name="Total Risk Violations",
            description="Total number of active risk violations",
            metric_type=MetricType.GAUGE,
            category=MetricCategory.RISK,
            thresholds={"warning": 50, "critical": 100}
        ),
        "risk.violations.critical": MetricDefinition(
            metric_id="risk.violations.critical",
            name="Critical Risk Violations",
            description="Number of critical severity violations",
            metric_type=MetricType.GAUGE,
            category=MetricCategory.RISK,
            thresholds={"warning": 5, "critical": 10}
        ),
        "risk.violations.unmitigated": MetricDefinition(
            metric_id="risk.violations.unmitigated",
            name="Unmitigated Violations",
            description="Violations without mitigation controls",
            metric_type=MetricType.GAUGE,
            category=MetricCategory.RISK,
            thresholds={"warning": 20, "critical": 50}
        ),
        "risk.score.average": MetricDefinition(
            metric_id="risk.score.average",
            name="Average Risk Score",
            description="Average risk score across all users",
            metric_type=MetricType.GAUGE,
            category=MetricCategory.RISK,
            unit="score",
            thresholds={"warning": 40, "critical": 60}
        ),

        # Access request metrics
        "access.requests.pending": MetricDefinition(
            metric_id="access.requests.pending",
            name="Pending Access Requests",
            description="Access requests awaiting approval",
            metric_type=MetricType.GAUGE,
            category=MetricCategory.ACCESS,
            thresholds={"warning": 50, "critical": 100}
        ),
        "access.requests.daily": MetricDefinition(
            metric_id="access.requests.daily",
            name="Daily Request Volume",
            description="Access requests submitted today",
            metric_type=MetricType.COUNTER,
            category=MetricCategory.ACCESS
        ),
        "access.approval.rate": MetricDefinition(
            metric_id="access.approval.rate",
            name="Approval Rate",
            description="Percentage of requests approved",
            metric_type=MetricType.PERCENTAGE,
            category=MetricCategory.ACCESS,
            unit="%"
        ),
        "access.sla.compliance": MetricDefinition(
            metric_id="access.sla.compliance",
            name="SLA Compliance Rate",
            description="Requests completed within SLA",
            metric_type=MetricType.PERCENTAGE,
            category=MetricCategory.ACCESS,
            unit="%",
            thresholds={"warning": 90, "critical": 80}
        ),

        # Certification metrics
        "certification.campaigns.active": MetricDefinition(
            metric_id="certification.campaigns.active",
            name="Active Campaigns",
            description="Currently running certification campaigns",
            metric_type=MetricType.GAUGE,
            category=MetricCategory.CERTIFICATION
        ),
        "certification.items.pending": MetricDefinition(
            metric_id="certification.items.pending",
            name="Pending Certifications",
            description="Items awaiting certification decision",
            metric_type=MetricType.GAUGE,
            category=MetricCategory.CERTIFICATION,
            thresholds={"warning": 500, "critical": 1000}
        ),
        "certification.completion.rate": MetricDefinition(
            metric_id="certification.completion.rate",
            name="Certification Completion Rate",
            description="Percentage of items certified",
            metric_type=MetricType.PERCENTAGE,
            category=MetricCategory.CERTIFICATION,
            unit="%"
        ),
        "certification.revocation.rate": MetricDefinition(
            metric_id="certification.revocation.rate",
            name="Revocation Rate",
            description="Percentage of access revoked during certification",
            metric_type=MetricType.PERCENTAGE,
            category=MetricCategory.CERTIFICATION,
            unit="%"
        ),

        # Firefighter metrics
        "firefighter.sessions.active": MetricDefinition(
            metric_id="firefighter.sessions.active",
            name="Active FF Sessions",
            description="Currently active firefighter sessions",
            metric_type=MetricType.GAUGE,
            category=MetricCategory.FIREFIGHTER,
            thresholds={"warning": 5, "critical": 10}
        ),
        "firefighter.requests.pending": MetricDefinition(
            metric_id="firefighter.requests.pending",
            name="Pending FF Requests",
            description="Firefighter requests awaiting approval",
            metric_type=MetricType.GAUGE,
            category=MetricCategory.FIREFIGHTER,
            thresholds={"warning": 5, "critical": 10}
        ),
        "firefighter.usage.daily": MetricDefinition(
            metric_id="firefighter.usage.daily",
            name="Daily FF Usage",
            description="Firefighter sessions started today",
            metric_type=MetricType.COUNTER,
            category=MetricCategory.FIREFIGHTER
        ),
        "firefighter.reviews.pending": MetricDefinition(
            metric_id="firefighter.reviews.pending",
            name="Pending FF Reviews",
            description="Completed sessions awaiting review",
            metric_type=MetricType.GAUGE,
            category=MetricCategory.FIREFIGHTER,
            thresholds={"warning": 10, "critical": 25}
        ),

        # Compliance metrics
        "compliance.controls.effective": MetricDefinition(
            metric_id="compliance.controls.effective",
            name="Effective Controls",
            description="Percentage of controls rated effective",
            metric_type=MetricType.PERCENTAGE,
            category=MetricCategory.COMPLIANCE,
            unit="%",
            thresholds={"warning": 90, "critical": 80}
        ),
        "compliance.audit.findings": MetricDefinition(
            metric_id="compliance.audit.findings",
            name="Open Audit Findings",
            description="Unresolved audit findings",
            metric_type=MetricType.GAUGE,
            category=MetricCategory.COMPLIANCE,
            thresholds={"warning": 10, "critical": 25}
        ),

        # Performance metrics
        "performance.api.latency": MetricDefinition(
            metric_id="performance.api.latency",
            name="API Latency",
            description="Average API response time",
            metric_type=MetricType.GAUGE,
            category=MetricCategory.PERFORMANCE,
            unit="ms",
            thresholds={"warning": 500, "critical": 1000}
        ),
        "performance.analysis.time": MetricDefinition(
            metric_id="performance.analysis.time",
            name="Risk Analysis Time",
            description="Average time to complete risk analysis",
            metric_type=MetricType.GAUGE,
            category=MetricCategory.PERFORMANCE,
            unit="ms"
        ),
    }

    def __init__(self):
        self.series: Dict[str, MetricSeries] = {}
        self.dimension_values: Dict[str, set] = defaultdict(set)

        # Initialize series for all defined metrics
        for metric_id in self.METRICS:
            self.series[metric_id] = MetricSeries(metric_id=metric_id)

    def record(
        self,
        metric_id: str,
        value: float,
        dimensions: Dict[str, str] = None,
        metadata: Dict[str, Any] = None
    ):
        """Record a metric value"""
        if metric_id not in self.series:
            self.series[metric_id] = MetricSeries(metric_id=metric_id)

        self.series[metric_id].add(value, dimensions, metadata)

        # Track dimension values
        if dimensions:
            for dim_name, dim_value in dimensions.items():
                self.dimension_values[dim_name].add(dim_value)

    def get_current(self, metric_id: str) -> Optional[float]:
        """Get current value of a metric"""
        if metric_id not in self.series:
            return None

        latest = self.series[metric_id].get_latest()
        return latest.value if latest else None

    def get_with_status(self, metric_id: str) -> Dict:
        """Get metric value with threshold status"""
        if metric_id not in self.METRICS:
            return {"error": f"Unknown metric: {metric_id}"}

        definition = self.METRICS[metric_id]
        current = self.get_current(metric_id)

        status = "normal"
        if current is not None and definition.thresholds:
            critical = definition.thresholds.get("critical")
            warning = definition.thresholds.get("warning")

            # For metrics where lower is worse (like compliance rates)
            if definition.metric_type == MetricType.PERCENTAGE and "compliance" in metric_id:
                if critical and current < critical:
                    status = "critical"
                elif warning and current < warning:
                    status = "warning"
            else:
                # For metrics where higher is worse
                if critical and current >= critical:
                    status = "critical"
                elif warning and current >= warning:
                    status = "warning"

        return {
            "metric_id": metric_id,
            "name": definition.name,
            "value": current,
            "unit": definition.unit,
            "status": status,
            "trend": self.series[metric_id].get_trend() if metric_id in self.series else "unknown",
            "thresholds": definition.thresholds
        }

    def get_category_metrics(self, category: MetricCategory) -> List[Dict]:
        """Get all metrics for a category"""
        results = []

        for metric_id, definition in self.METRICS.items():
            if definition.category == category:
                results.append(self.get_with_status(metric_id))

        return results

    def get_all_metrics(self) -> Dict[str, List[Dict]]:
        """Get all metrics grouped by category"""
        by_category = {}

        for category in MetricCategory:
            metrics = self.get_category_metrics(category)
            if metrics:
                by_category[category.value] = metrics

        return by_category

    def get_alerts(self) -> List[Dict]:
        """Get all metrics in warning or critical state"""
        alerts = []

        for metric_id in self.METRICS:
            status = self.get_with_status(metric_id)
            if status.get("status") in ["warning", "critical"]:
                alerts.append({
                    **status,
                    "severity": status["status"],
                    "timestamp": datetime.now().isoformat()
                })

        return sorted(alerts, key=lambda x: 0 if x["severity"] == "critical" else 1)

    def get_time_series(
        self,
        metric_id: str,
        start_time: datetime = None,
        end_time: datetime = None,
        interval_minutes: int = 60
    ) -> List[Dict]:
        """Get time series data for charting"""
        if metric_id not in self.series:
            return []

        start_time = start_time or (datetime.now() - timedelta(days=1))
        end_time = end_time or datetime.now()

        # Filter values in range
        values = [
            v for v in self.series[metric_id].values
            if start_time <= v.timestamp <= end_time
        ]

        # Aggregate by interval
        buckets = defaultdict(list)
        for v in values:
            bucket_time = v.timestamp.replace(
                minute=(v.timestamp.minute // interval_minutes) * interval_minutes,
                second=0,
                microsecond=0
            )
            buckets[bucket_time].append(v.value)

        # Calculate aggregates
        result = []
        for timestamp, vals in sorted(buckets.items()):
            result.append({
                "timestamp": timestamp.isoformat(),
                "value": statistics.mean(vals),
                "min": min(vals),
                "max": max(vals),
                "count": len(vals)
            })

        return result

    def calculate_summary_stats(self) -> Dict:
        """Calculate summary statistics across all metrics"""
        total_critical = 0
        total_warning = 0
        total_normal = 0

        for metric_id in self.METRICS:
            status = self.get_with_status(metric_id)
            if status.get("status") == "critical":
                total_critical += 1
            elif status.get("status") == "warning":
                total_warning += 1
            else:
                total_normal += 1

        total = total_critical + total_warning + total_normal

        return {
            "total_metrics": total,
            "critical_count": total_critical,
            "warning_count": total_warning,
            "normal_count": total_normal,
            "health_score": round((total_normal / total) * 100, 1) if total else 100,
            "status": "critical" if total_critical > 0 else ("warning" if total_warning > 0 else "healthy")
        }
