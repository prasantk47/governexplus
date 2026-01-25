"""
Dashboard API Router

Endpoints for real-time dashboards and analytics.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime, timedelta

from core.analytics import DashboardManager, MetricsCollector
from core.analytics.metrics import MetricCategory

router = APIRouter(tags=["Dashboard"])

# Initialize managers
metrics_collector = MetricsCollector()
dashboard_manager = DashboardManager(metrics_collector)


# =============================================================================
# Main Stats Endpoint (used by frontend dashboard)
# =============================================================================

@router.get("/stats")
async def get_dashboard_stats():
    """
    Get main dashboard statistics for the frontend.

    Returns stats in the format expected by the Dashboard component.
    """
    _seed_sample_metrics()

    return {
        "totalUsers": 1250,
        "activeViolations": int(metrics_collector.get_current("risk.violations.total") or 45),
        "pendingApprovals": int(metrics_collector.get_current("access.requests.pending") or 12),
        "certificationProgress": int(metrics_collector.get_current("certification.completion.rate") or 78),
        "activeFirefighterSessions": int(metrics_collector.get_current("firefighter.sessions.active") or 2),
        "riskScore": int(metrics_collector.get_current("risk.score.average") or 42),
        "riskTrend": "down" if (metrics_collector.get_current("risk.score.average") or 50) < 50 else "up"
    }

# Seed some sample metrics for demonstration
def _seed_sample_metrics():
    """Seed sample metrics for demo purposes"""
    import random

    metrics_collector.record("risk.violations.total", random.randint(45, 75))
    metrics_collector.record("risk.violations.critical", random.randint(3, 12))
    metrics_collector.record("risk.violations.unmitigated", random.randint(15, 35))
    metrics_collector.record("risk.score.average", random.uniform(35, 55))

    metrics_collector.record("access.requests.pending", random.randint(20, 60))
    metrics_collector.record("access.requests.daily", random.randint(15, 45))
    metrics_collector.record("access.approval.rate", random.uniform(75, 92))
    metrics_collector.record("access.sla.compliance", random.uniform(85, 98))

    metrics_collector.record("certification.campaigns.active", random.randint(2, 5))
    metrics_collector.record("certification.items.pending", random.randint(200, 800))
    metrics_collector.record("certification.completion.rate", random.uniform(40, 85))
    metrics_collector.record("certification.revocation.rate", random.uniform(5, 15))

    metrics_collector.record("firefighter.sessions.active", random.randint(0, 4))
    metrics_collector.record("firefighter.requests.pending", random.randint(0, 6))
    metrics_collector.record("firefighter.usage.daily", random.randint(2, 10))
    metrics_collector.record("firefighter.reviews.pending", random.randint(3, 15))

    metrics_collector.record("compliance.controls.effective", random.uniform(88, 97))
    metrics_collector.record("compliance.audit.findings", random.randint(5, 20))

    metrics_collector.record("performance.api.latency", random.uniform(50, 200))

_seed_sample_metrics()


# =============================================================================
# Request/Response Models
# =============================================================================

class CreateDashboardRequest(BaseModel):
    """Request to create a custom dashboard"""
    name: str = Field(..., example="My Custom Dashboard")
    description: str = Field(..., example="Custom monitoring dashboard")
    widgets: List[Dict] = Field(default_factory=list)


class MetricRecordRequest(BaseModel):
    """Request to record a metric value"""
    metric_id: str = Field(..., example="risk.violations.total")
    value: float = Field(..., example=42.0)
    dimensions: Optional[Dict[str, str]] = None
    metadata: Optional[Dict] = None


# =============================================================================
# Dashboard Endpoints
# =============================================================================

@router.get("/dashboards")
async def list_dashboards(
    category: Optional[str] = Query(None, description="Filter by category")
):
    """
    List all available dashboards.
    """
    return {
        "dashboards": dashboard_manager.list_dashboards(category)
    }


@router.get("/dashboards/{dashboard_id}")
async def get_dashboard(dashboard_id: str):
    """
    Get a dashboard configuration and layout.
    """
    dashboard = dashboard_manager.get_dashboard(dashboard_id)
    if not dashboard:
        raise HTTPException(status_code=404, detail=f"Dashboard {dashboard_id} not found")

    return dashboard.to_dict()


@router.get("/dashboards/{dashboard_id}/data")
async def get_dashboard_data(dashboard_id: str):
    """
    Get full dashboard data including all widget data.

    Use this endpoint to render a complete dashboard.
    """
    data = dashboard_manager.get_dashboard_data(dashboard_id)
    if "error" in data:
        raise HTTPException(status_code=404, detail=data["error"])

    return data


@router.post("/dashboards", status_code=201)
async def create_dashboard(
    request: CreateDashboardRequest,
    owner_id: str = Query(..., description="Owner user ID")
):
    """
    Create a custom dashboard.
    """
    dashboard = dashboard_manager.create_custom_dashboard(
        name=request.name,
        description=request.description,
        owner_id=owner_id,
        widgets=request.widgets
    )

    return {
        "message": "Dashboard created",
        "dashboard_id": dashboard.dashboard_id
    }


# =============================================================================
# Summary Endpoints
# =============================================================================

@router.get("/summary/executive")
async def get_executive_summary():
    """
    Get executive summary dashboard data.

    Provides high-level KPIs and status for executive reporting.
    """
    _seed_sample_metrics()  # Refresh sample data
    return dashboard_manager.get_executive_summary()


@router.get("/summary/risk")
async def get_risk_summary():
    """
    Get risk management summary.
    """
    _seed_sample_metrics()
    return dashboard_manager.get_risk_summary()


@router.get("/summary/access")
async def get_access_summary():
    """
    Get access request workflow summary.
    """
    _seed_sample_metrics()
    return dashboard_manager.get_workflow_summary()


@router.get("/summary/certification")
async def get_certification_summary():
    """
    Get certification campaign summary.
    """
    _seed_sample_metrics()
    return dashboard_manager.get_certification_summary()


@router.get("/summary/firefighter")
async def get_firefighter_summary():
    """
    Get firefighter/emergency access summary.
    """
    _seed_sample_metrics()
    return dashboard_manager.get_firefighter_summary()


# =============================================================================
# Metrics Endpoints
# =============================================================================

@router.get("/metrics")
async def list_all_metrics():
    """
    Get all metrics grouped by category.
    """
    _seed_sample_metrics()
    return dashboard_manager.metrics.get_all_metrics()


@router.get("/metrics/category/{category}")
async def get_category_metrics(category: str):
    """
    Get all metrics for a specific category.
    """
    try:
        cat = MetricCategory(category)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid category. Valid categories: {[c.value for c in MetricCategory]}"
        )

    _seed_sample_metrics()
    return {
        "category": category,
        "metrics": dashboard_manager.metrics.get_category_metrics(cat)
    }


@router.get("/metrics/{metric_id}")
async def get_metric(metric_id: str):
    """
    Get a specific metric with current value and status.
    """
    _seed_sample_metrics()
    result = dashboard_manager.metrics.get_with_status(metric_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])

    return result


@router.get("/metrics/{metric_id}/timeseries")
async def get_metric_timeseries(
    metric_id: str,
    hours: int = Query(24, description="Hours of history"),
    interval_minutes: int = Query(60, description="Aggregation interval")
):
    """
    Get time series data for a metric.

    Useful for charting historical trends.
    """
    start_time = datetime.now() - timedelta(hours=hours)

    series = dashboard_manager.metrics.get_time_series(
        metric_id,
        start_time=start_time,
        interval_minutes=interval_minutes
    )

    return {
        "metric_id": metric_id,
        "period_hours": hours,
        "interval_minutes": interval_minutes,
        "data_points": len(series),
        "series": series
    }


@router.post("/metrics/record")
async def record_metric(request: MetricRecordRequest):
    """
    Record a metric value.

    Used by other modules to report metrics.
    """
    dashboard_manager.metrics.record(
        metric_id=request.metric_id,
        value=request.value,
        dimensions=request.dimensions,
        metadata=request.metadata
    )

    return {
        "recorded": True,
        "metric_id": request.metric_id,
        "value": request.value
    }


# =============================================================================
# Alerts Endpoints
# =============================================================================

@router.get("/alerts")
async def get_alerts():
    """
    Get all current alerts (metrics in warning/critical state).
    """
    _seed_sample_metrics()
    alerts = dashboard_manager.metrics.get_alerts()

    return {
        "total": len(alerts),
        "critical": len([a for a in alerts if a.get("severity") == "critical"]),
        "warning": len([a for a in alerts if a.get("severity") == "warning"]),
        "alerts": alerts
    }


@router.get("/health")
async def get_system_health():
    """
    Get overall system health status.
    """
    _seed_sample_metrics()
    summary = dashboard_manager.metrics.calculate_summary_stats()
    alerts = dashboard_manager.metrics.get_alerts()

    return {
        "health_score": summary["health_score"],
        "status": summary["status"],
        "metrics_summary": {
            "total": summary["total_metrics"],
            "critical": summary["critical_count"],
            "warning": summary["warning_count"],
            "healthy": summary["normal_count"]
        },
        "active_alerts": len(alerts),
        "timestamp": datetime.now().isoformat()
    }


# =============================================================================
# Report Endpoints
# =============================================================================

@router.get("/reports/kpi")
async def get_kpi_report(
    period_days: int = Query(30, description="Report period in days")
):
    """
    Generate a KPI summary report.
    """
    _seed_sample_metrics()

    return {
        "report_type": "kpi_summary",
        "period_days": period_days,
        "generated_at": datetime.now().isoformat(),
        "kpis": {
            "risk_management": {
                "total_violations": metrics_collector.get_current("risk.violations.total"),
                "critical_violations": metrics_collector.get_current("risk.violations.critical"),
                "unmitigated_violations": metrics_collector.get_current("risk.violations.unmitigated"),
                "average_risk_score": metrics_collector.get_current("risk.score.average")
            },
            "access_management": {
                "pending_requests": metrics_collector.get_current("access.requests.pending"),
                "approval_rate": metrics_collector.get_current("access.approval.rate"),
                "sla_compliance": metrics_collector.get_current("access.sla.compliance")
            },
            "certification": {
                "active_campaigns": metrics_collector.get_current("certification.campaigns.active"),
                "pending_items": metrics_collector.get_current("certification.items.pending"),
                "completion_rate": metrics_collector.get_current("certification.completion.rate"),
                "revocation_rate": metrics_collector.get_current("certification.revocation.rate")
            },
            "emergency_access": {
                "active_sessions": metrics_collector.get_current("firefighter.sessions.active"),
                "pending_reviews": metrics_collector.get_current("firefighter.reviews.pending")
            },
            "compliance": {
                "controls_effectiveness": metrics_collector.get_current("compliance.controls.effective"),
                "open_findings": metrics_collector.get_current("compliance.audit.findings")
            }
        }
    }


@router.get("/reports/trends")
async def get_trend_report(
    metrics: List[str] = Query(
        default=["risk.violations.total", "access.requests.daily"],
        description="Metrics to include"
    ),
    period_days: int = Query(30, description="Report period in days")
):
    """
    Generate a trends report for specified metrics.
    """
    start_time = datetime.now() - timedelta(days=period_days)

    trends = {}
    for metric_id in metrics:
        series = metrics_collector.get_time_series(
            metric_id,
            start_time=start_time,
            interval_minutes=1440  # Daily
        )
        if metric_id in metrics_collector.series:
            trends[metric_id] = {
                "trend": metrics_collector.series[metric_id].get_trend(),
                "current": metrics_collector.get_current(metric_id),
                "average": metrics_collector.series[metric_id].get_average(period_days * 24 * 60),
                "data_points": series
            }

    return {
        "report_type": "trends",
        "period_days": period_days,
        "generated_at": datetime.now().isoformat(),
        "trends": trends
    }
