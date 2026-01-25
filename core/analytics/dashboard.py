"""
Dashboard Manager Module

Provides real-time dashboard data aggregation and management.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from enum import Enum
import uuid

from .metrics import MetricsCollector, MetricCategory


class WidgetType(Enum):
    """Dashboard widget types"""
    METRIC_CARD = "metric_card"           # Single metric display
    CHART_LINE = "chart_line"             # Line chart
    CHART_BAR = "chart_bar"               # Bar chart
    CHART_PIE = "chart_pie"               # Pie chart
    TABLE = "table"                        # Data table
    ALERT_LIST = "alert_list"             # List of alerts
    HEATMAP = "heatmap"                   # Risk heatmap
    TREND = "trend"                       # Trend indicator
    COUNTER = "counter"                   # Animated counter
    PROGRESS = "progress"                 # Progress bar
    STATUS_GRID = "status_grid"           # Grid of status indicators


@dataclass
class DashboardWidget:
    """A widget on a dashboard"""
    widget_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    widget_type: WidgetType = WidgetType.METRIC_CARD
    title: str = ""
    metric_ids: List[str] = field(default_factory=list)
    config: Dict[str, Any] = field(default_factory=dict)
    position: Dict[str, int] = field(default_factory=lambda: {"x": 0, "y": 0, "w": 1, "h": 1})

    def to_dict(self) -> Dict:
        return {
            "widget_id": self.widget_id,
            "widget_type": self.widget_type.value,
            "title": self.title,
            "metric_ids": self.metric_ids,
            "config": self.config,
            "position": self.position
        }


@dataclass
class Dashboard:
    """A dashboard configuration"""
    dashboard_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    description: str = ""
    owner_id: str = ""
    is_default: bool = False
    category: str = "general"
    widgets: List[DashboardWidget] = field(default_factory=list)
    refresh_interval_seconds: int = 30
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict:
        return {
            "dashboard_id": self.dashboard_id,
            "name": self.name,
            "description": self.description,
            "owner_id": self.owner_id,
            "is_default": self.is_default,
            "category": self.category,
            "widgets": [w.to_dict() for w in self.widgets],
            "refresh_interval_seconds": self.refresh_interval_seconds,
            "created_at": self.created_at.isoformat()
        }


class DashboardManager:
    """
    Manages dashboards and provides data for dashboard widgets.

    Aggregates data from all GRC modules to provide real-time
    monitoring and analytics.
    """

    def __init__(self, metrics_collector: MetricsCollector = None):
        self.metrics = metrics_collector or MetricsCollector()
        self.dashboards: Dict[str, Dashboard] = {}

        # Create default dashboards
        self._create_default_dashboards()

    def _create_default_dashboards(self):
        """Create standard default dashboards"""

        # Executive Summary Dashboard
        exec_dashboard = Dashboard(
            dashboard_id="exec-summary",
            name="Executive Summary",
            description="High-level GRC overview for executives",
            is_default=True,
            category="executive",
            widgets=[
                DashboardWidget(
                    widget_id="health-score",
                    widget_type=WidgetType.METRIC_CARD,
                    title="GRC Health Score",
                    config={"color_coded": True, "show_trend": True}
                ),
                DashboardWidget(
                    widget_id="critical-alerts",
                    widget_type=WidgetType.COUNTER,
                    title="Critical Alerts",
                    metric_ids=["risk.violations.critical"],
                    config={"color": "red", "animate": True}
                ),
                DashboardWidget(
                    widget_id="compliance-rate",
                    widget_type=WidgetType.PROGRESS,
                    title="Overall Compliance",
                    metric_ids=["compliance.controls.effective"],
                    config={"target": 95}
                ),
                DashboardWidget(
                    widget_id="risk-trend",
                    widget_type=WidgetType.CHART_LINE,
                    title="Risk Trend (30 Days)",
                    metric_ids=["risk.violations.total", "risk.violations.critical"],
                    config={"period_days": 30}
                ),
                DashboardWidget(
                    widget_id="sla-compliance",
                    widget_type=WidgetType.METRIC_CARD,
                    title="SLA Compliance",
                    metric_ids=["access.sla.compliance"],
                    config={"format": "percentage"}
                )
            ],
            refresh_interval_seconds=60
        )
        self.dashboards["exec-summary"] = exec_dashboard

        # Risk Management Dashboard
        risk_dashboard = Dashboard(
            dashboard_id="risk-management",
            name="Risk Management",
            description="Detailed risk analysis and SoD monitoring",
            category="risk",
            widgets=[
                DashboardWidget(
                    widget_id="risk-summary",
                    widget_type=WidgetType.STATUS_GRID,
                    title="Risk Overview",
                    metric_ids=[
                        "risk.violations.total",
                        "risk.violations.critical",
                        "risk.violations.unmitigated",
                        "risk.score.average"
                    ]
                ),
                DashboardWidget(
                    widget_id="risk-by-severity",
                    widget_type=WidgetType.CHART_PIE,
                    title="Violations by Severity",
                    config={"group_by": "severity"}
                ),
                DashboardWidget(
                    widget_id="risk-by-category",
                    widget_type=WidgetType.CHART_BAR,
                    title="Violations by Category",
                    config={"group_by": "category", "orientation": "horizontal"}
                ),
                DashboardWidget(
                    widget_id="top-risky-users",
                    widget_type=WidgetType.TABLE,
                    title="Top 10 Risky Users",
                    config={"limit": 10, "sort_by": "risk_score", "order": "desc"}
                ),
                DashboardWidget(
                    widget_id="risk-heatmap",
                    widget_type=WidgetType.HEATMAP,
                    title="Department Risk Heatmap",
                    config={"dimensions": ["department", "risk_category"]}
                ),
                DashboardWidget(
                    widget_id="unmitigated-violations",
                    widget_type=WidgetType.TABLE,
                    title="Unmitigated Critical Violations",
                    config={"filter": {"severity": "critical", "mitigated": False}}
                )
            ],
            refresh_interval_seconds=30
        )
        self.dashboards["risk-management"] = risk_dashboard

        # Access Request Dashboard
        access_dashboard = Dashboard(
            dashboard_id="access-requests",
            name="Access Request Management",
            description="Access request workflow monitoring",
            category="access",
            widgets=[
                DashboardWidget(
                    widget_id="request-summary",
                    widget_type=WidgetType.STATUS_GRID,
                    title="Request Overview",
                    metric_ids=[
                        "access.requests.pending",
                        "access.requests.daily",
                        "access.approval.rate",
                        "access.sla.compliance"
                    ]
                ),
                DashboardWidget(
                    widget_id="request-volume",
                    widget_type=WidgetType.CHART_LINE,
                    title="Request Volume (7 Days)",
                    metric_ids=["access.requests.daily"],
                    config={"period_days": 7}
                ),
                DashboardWidget(
                    widget_id="pending-by-approver",
                    widget_type=WidgetType.CHART_BAR,
                    title="Pending by Approver",
                    config={"group_by": "approver"}
                ),
                DashboardWidget(
                    widget_id="sla-breaches",
                    widget_type=WidgetType.ALERT_LIST,
                    title="SLA Breaches",
                    config={"filter": {"sla_status": "breached"}}
                ),
                DashboardWidget(
                    widget_id="approval-trend",
                    widget_type=WidgetType.CHART_LINE,
                    title="Approval/Rejection Trend",
                    config={"metrics": ["approved", "rejected"], "period_days": 30}
                )
            ],
            refresh_interval_seconds=30
        )
        self.dashboards["access-requests"] = access_dashboard

        # Firefighter Dashboard
        ff_dashboard = Dashboard(
            dashboard_id="firefighter",
            name="Firefighter Monitoring",
            description="Emergency access monitoring and compliance",
            category="firefighter",
            widgets=[
                DashboardWidget(
                    widget_id="ff-active",
                    widget_type=WidgetType.COUNTER,
                    title="Active Sessions",
                    metric_ids=["firefighter.sessions.active"],
                    config={"color_threshold": {"warning": 3, "critical": 5}}
                ),
                DashboardWidget(
                    widget_id="ff-pending-requests",
                    widget_type=WidgetType.COUNTER,
                    title="Pending Requests",
                    metric_ids=["firefighter.requests.pending"]
                ),
                DashboardWidget(
                    widget_id="ff-pending-reviews",
                    widget_type=WidgetType.COUNTER,
                    title="Pending Reviews",
                    metric_ids=["firefighter.reviews.pending"],
                    config={"color": "orange"}
                ),
                DashboardWidget(
                    widget_id="ff-active-sessions",
                    widget_type=WidgetType.TABLE,
                    title="Active Sessions",
                    config={"columns": ["user", "firefighter_id", "system", "start_time", "remaining"]}
                ),
                DashboardWidget(
                    widget_id="ff-usage-trend",
                    widget_type=WidgetType.CHART_LINE,
                    title="Usage Trend (30 Days)",
                    metric_ids=["firefighter.usage.daily"],
                    config={"period_days": 30}
                ),
                DashboardWidget(
                    widget_id="ff-by-system",
                    widget_type=WidgetType.CHART_PIE,
                    title="Sessions by System",
                    config={"group_by": "system"}
                )
            ],
            refresh_interval_seconds=15  # More frequent refresh for monitoring
        )
        self.dashboards["firefighter"] = ff_dashboard

        # Certification Dashboard
        cert_dashboard = Dashboard(
            dashboard_id="certification",
            name="Certification Campaigns",
            description="Access certification progress monitoring",
            category="certification",
            widgets=[
                DashboardWidget(
                    widget_id="cert-active-campaigns",
                    widget_type=WidgetType.COUNTER,
                    title="Active Campaigns",
                    metric_ids=["certification.campaigns.active"]
                ),
                DashboardWidget(
                    widget_id="cert-pending",
                    widget_type=WidgetType.COUNTER,
                    title="Pending Items",
                    metric_ids=["certification.items.pending"],
                    config={"color": "orange"}
                ),
                DashboardWidget(
                    widget_id="cert-completion",
                    widget_type=WidgetType.PROGRESS,
                    title="Overall Completion",
                    metric_ids=["certification.completion.rate"],
                    config={"target": 100}
                ),
                DashboardWidget(
                    widget_id="cert-campaigns-table",
                    widget_type=WidgetType.TABLE,
                    title="Campaign Status",
                    config={"columns": ["name", "type", "progress", "pending", "days_remaining"]}
                ),
                DashboardWidget(
                    widget_id="cert-reviewer-workload",
                    widget_type=WidgetType.CHART_BAR,
                    title="Reviewer Workload",
                    config={"group_by": "reviewer", "orientation": "horizontal"}
                ),
                DashboardWidget(
                    widget_id="cert-decisions",
                    widget_type=WidgetType.CHART_PIE,
                    title="Decision Breakdown",
                    config={"metrics": ["certified", "revoked", "modified", "pending"]}
                )
            ],
            refresh_interval_seconds=60
        )
        self.dashboards["certification"] = cert_dashboard

    def get_dashboard(self, dashboard_id: str) -> Optional[Dashboard]:
        """Get a dashboard by ID"""
        return self.dashboards.get(dashboard_id)

    def list_dashboards(self, category: str = None) -> List[Dict]:
        """List available dashboards"""
        dashboards = []

        for dashboard in self.dashboards.values():
            if category and dashboard.category != category:
                continue
            dashboards.append({
                "dashboard_id": dashboard.dashboard_id,
                "name": dashboard.name,
                "description": dashboard.description,
                "category": dashboard.category,
                "is_default": dashboard.is_default,
                "widget_count": len(dashboard.widgets)
            })

        return dashboards

    def get_dashboard_data(self, dashboard_id: str) -> Dict:
        """Get all data for a dashboard"""
        dashboard = self.dashboards.get(dashboard_id)
        if not dashboard:
            return {"error": f"Dashboard {dashboard_id} not found"}

        widget_data = []
        for widget in dashboard.widgets:
            data = self._get_widget_data(widget)
            widget_data.append({
                **widget.to_dict(),
                "data": data
            })

        return {
            **dashboard.to_dict(),
            "widgets": widget_data,
            "generated_at": datetime.now().isoformat()
        }

    def _get_widget_data(self, widget: DashboardWidget) -> Dict:
        """Get data for a specific widget"""
        data = {}

        if widget.widget_type == WidgetType.METRIC_CARD:
            if widget.metric_ids:
                data = self.metrics.get_with_status(widget.metric_ids[0])

        elif widget.widget_type == WidgetType.COUNTER:
            if widget.metric_ids:
                current = self.metrics.get_current(widget.metric_ids[0])
                data = {"value": current or 0}

        elif widget.widget_type == WidgetType.STATUS_GRID:
            data = {"metrics": [
                self.metrics.get_with_status(m) for m in widget.metric_ids
            ]}

        elif widget.widget_type == WidgetType.PROGRESS:
            if widget.metric_ids:
                current = self.metrics.get_current(widget.metric_ids[0])
                target = widget.config.get("target", 100)
                data = {
                    "value": current or 0,
                    "target": target,
                    "percentage": round((current / target) * 100, 1) if current and target else 0
                }

        elif widget.widget_type in [WidgetType.CHART_LINE, WidgetType.CHART_BAR]:
            period_days = widget.config.get("period_days", 7)
            start_time = datetime.now() - timedelta(days=period_days)

            series_data = {}
            for metric_id in widget.metric_ids:
                series_data[metric_id] = self.metrics.get_time_series(
                    metric_id,
                    start_time=start_time,
                    interval_minutes=60 if period_days <= 1 else 1440
                )

            data = {"series": series_data}

        elif widget.widget_type == WidgetType.ALERT_LIST:
            data = {"alerts": self.metrics.get_alerts()}

        elif widget.widget_type == WidgetType.TABLE:
            # Table data would come from appropriate service
            # Placeholder for now
            data = {"rows": [], "columns": widget.config.get("columns", [])}

        elif widget.widget_type == WidgetType.CHART_PIE:
            # Pie chart data would need aggregation
            data = {"segments": []}

        return data

    def get_executive_summary(self) -> Dict:
        """Get executive summary data"""
        summary = self.metrics.calculate_summary_stats()

        # Get key metrics
        key_metrics = {
            "risk": self.metrics.get_category_metrics(MetricCategory.RISK),
            "compliance": self.metrics.get_category_metrics(MetricCategory.COMPLIANCE),
            "access": self.metrics.get_category_metrics(MetricCategory.ACCESS)
        }

        # Get critical alerts
        alerts = self.metrics.get_alerts()
        critical_alerts = [a for a in alerts if a.get("severity") == "critical"]

        return {
            "health_score": summary["health_score"],
            "overall_status": summary["status"],
            "summary_stats": summary,
            "key_metrics": key_metrics,
            "critical_alerts": critical_alerts[:5],  # Top 5
            "generated_at": datetime.now().isoformat()
        }

    def get_risk_summary(self) -> Dict:
        """Get risk management summary"""
        risk_metrics = self.metrics.get_category_metrics(MetricCategory.RISK)

        return {
            "metrics": risk_metrics,
            "violations_by_severity": {
                "critical": self.metrics.get_current("risk.violations.critical") or 0,
                "high": 0,  # Would need additional metrics
                "medium": 0,
                "low": 0
            },
            "total_violations": self.metrics.get_current("risk.violations.total") or 0,
            "unmitigated": self.metrics.get_current("risk.violations.unmitigated") or 0,
            "average_risk_score": self.metrics.get_current("risk.score.average") or 0
        }

    def get_workflow_summary(self) -> Dict:
        """Get workflow/access request summary"""
        return {
            "pending_requests": self.metrics.get_current("access.requests.pending") or 0,
            "daily_volume": self.metrics.get_current("access.requests.daily") or 0,
            "approval_rate": self.metrics.get_current("access.approval.rate") or 0,
            "sla_compliance": self.metrics.get_current("access.sla.compliance") or 0,
            "metrics": self.metrics.get_category_metrics(MetricCategory.ACCESS)
        }

    def get_certification_summary(self) -> Dict:
        """Get certification campaign summary"""
        return {
            "active_campaigns": self.metrics.get_current("certification.campaigns.active") or 0,
            "pending_items": self.metrics.get_current("certification.items.pending") or 0,
            "completion_rate": self.metrics.get_current("certification.completion.rate") or 0,
            "revocation_rate": self.metrics.get_current("certification.revocation.rate") or 0,
            "metrics": self.metrics.get_category_metrics(MetricCategory.CERTIFICATION)
        }

    def get_firefighter_summary(self) -> Dict:
        """Get firefighter/EAM summary"""
        return {
            "active_sessions": self.metrics.get_current("firefighter.sessions.active") or 0,
            "pending_requests": self.metrics.get_current("firefighter.requests.pending") or 0,
            "pending_reviews": self.metrics.get_current("firefighter.reviews.pending") or 0,
            "daily_usage": self.metrics.get_current("firefighter.usage.daily") or 0,
            "metrics": self.metrics.get_category_metrics(MetricCategory.FIREFIGHTER)
        }

    def create_custom_dashboard(
        self,
        name: str,
        description: str,
        owner_id: str,
        widgets: List[Dict]
    ) -> Dashboard:
        """Create a custom dashboard"""
        dashboard = Dashboard(
            name=name,
            description=description,
            owner_id=owner_id,
            category="custom"
        )

        for w in widgets:
            widget = DashboardWidget(
                widget_type=WidgetType(w.get("widget_type", "metric_card")),
                title=w.get("title", ""),
                metric_ids=w.get("metric_ids", []),
                config=w.get("config", {}),
                position=w.get("position", {"x": 0, "y": 0, "w": 1, "h": 1})
            )
            dashboard.widgets.append(widget)

        self.dashboards[dashboard.dashboard_id] = dashboard
        return dashboard

    def update_metrics_from_sources(
        self,
        risk_engine=None,
        access_manager=None,
        cert_manager=None,
        ff_manager=None
    ):
        """
        Update metrics from source modules.

        This would be called periodically to refresh dashboard data.
        """
        # Risk metrics
        if risk_engine:
            # In production, these would query actual data
            pass

        # Access request metrics
        if access_manager:
            pending = len([r for r in access_manager.requests.values()
                          if r.status.value in ["pending_approval", "submitted"]])
            self.metrics.record("access.requests.pending", pending)

        # Certification metrics
        if cert_manager:
            active = len([c for c in cert_manager.campaigns.values()
                         if c.status.value == "active"])
            self.metrics.record("certification.campaigns.active", active)

            total_pending = sum(
                len([i for i in c.items if not i.is_completed])
                for c in cert_manager.campaigns.values()
                if c.status.value == "active"
            )
            self.metrics.record("certification.items.pending", total_pending)

        # Firefighter metrics
        if ff_manager:
            active_sessions = len([s for s in ff_manager.sessions.values()
                                  if s.status.value == "active"])
            self.metrics.record("firefighter.sessions.active", active_sessions)

            pending_requests = len([r for r in ff_manager.requests.values()
                                   if r.status.value == "pending_approval"])
            self.metrics.record("firefighter.requests.pending", pending_requests)
