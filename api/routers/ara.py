"""
Access Risk Analysis (ARA) API Router

GOVERNEX+ Advanced Risk Intelligence endpoints.

Provides comprehensive access risk analysis capabilities:
- SoD conflict detection and analysis
- Sensitive access identification
- Pre-provisioning risk simulation
- Real-time context-aware scoring
- Behavioral anomaly detection
- Mitigation control management
- Risk analytics and trends

SAP GRC: "Is there a risk?"
GOVERNEX+: "How risky is it, why, right now, and what should we do?"
"""

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from enum import Enum

from core.ara import (
    # Models
    Risk,
    RiskSeverity,
    RiskCategory,
    RiskStatus,
    RiskType,
    SoDRule,
    SoDConflict,
    RiskContext,
    UserContext,
    RiskAnalysisResult,
    SimulationResult,
    RemediationSuggestion,
    # Engine
    AccessRiskEngine,
    SoDAnalyzer,
    SensitiveAccessAnalyzer,
    RiskScorer,
    # Rules
    RuleEngine,
    RuleDefinition,
    # Mitigation
    MitigationControl,
    MitigationManager,
    # Analytics
    RiskAnalytics,
    RiskTrendAnalyzer,
)

from core.ara.behavioral import (
    BehavioralAnalyzer,
    UsageMetrics,
)

from core.ara.analytics import (
    TimeGranularity,
    EconomicRiskMetrics,
    ControlEffectivenessMetrics,
)

router = APIRouter(prefix="/ara", tags=["Access Risk Analysis"])

# =============================================================================
# Initialize ARA Components (Singleton pattern)
# =============================================================================

_ara_engine: Optional[AccessRiskEngine] = None
_mitigation_manager: Optional[MitigationManager] = None
_analytics: Optional[RiskAnalytics] = None
_behavioral_analyzer: Optional[BehavioralAnalyzer] = None


def get_ara_engine() -> AccessRiskEngine:
    """Get or create ARA engine singleton."""
    global _ara_engine
    if _ara_engine is None:
        _ara_engine = AccessRiskEngine()
    return _ara_engine


def get_mitigation_manager() -> MitigationManager:
    """Get or create mitigation manager singleton."""
    global _mitigation_manager
    if _mitigation_manager is None:
        _mitigation_manager = MitigationManager()
    return _mitigation_manager


def get_analytics() -> RiskAnalytics:
    """Get or create analytics singleton."""
    global _analytics
    if _analytics is None:
        _analytics = RiskAnalytics()
    return _analytics


def get_behavioral_analyzer() -> BehavioralAnalyzer:
    """Get or create behavioral analyzer singleton."""
    global _behavioral_analyzer
    if _behavioral_analyzer is None:
        _behavioral_analyzer = BehavioralAnalyzer()
    return _behavioral_analyzer


# =============================================================================
# Request/Response Models
# =============================================================================

class UserAccessData(BaseModel):
    """User access data for analysis."""
    user_id: str = Field(..., example="JSMITH")
    roles: List[str] = Field(default_factory=list, example=["Z_FI_CLERK", "Z_AP_USER"])
    tcodes: List[str] = Field(default_factory=list, example=["FK01", "FK02", "FB60"])
    auth_objects: List[Dict[str, Any]] = Field(default_factory=list)


class UserContextRequest(BaseModel):
    """Optional context for analysis."""
    employment_type: str = Field(default="employee", example="employee")
    department: str = Field(default="", example="Finance")
    is_privileged_user: bool = False
    is_emergency_access: bool = False
    access_level: str = Field(default="standard", example="standard")
    current_location: str = Field(default="internal", example="internal")
    previous_violations: int = 0


class AnalyzeUserRequest(BaseModel):
    """Request for user risk analysis."""
    access_data: UserAccessData
    context: Optional[UserContextRequest] = None
    include_behavioral: bool = Field(default=False, description="Include behavioral analysis")
    include_remediation: bool = Field(default=True, description="Include remediation suggestions")


class SimulateAccessRequest(BaseModel):
    """Request for access simulation."""
    user_id: str = Field(..., example="JSMITH")
    current_roles: List[str] = Field(default_factory=list)
    current_tcodes: List[str] = Field(default_factory=list)
    requested_roles: List[str] = Field(default_factory=list, example=["Z_FI_MANAGER"])
    requested_tcodes: List[str] = Field(default_factory=list)
    request_reason: Optional[str] = None


class SoDRuleRequest(BaseModel):
    """Request for creating SoD rule."""
    rule_id: str = Field(..., example="SOD_FIN_001")
    name: str = Field(..., example="Create Vendor / Post Payment")
    description: str = Field(default="")
    function_1_tcodes: List[str] = Field(..., example=["FK01", "XK01"])
    function_2_tcodes: List[str] = Field(..., example=["F110", "FBZ1"])
    severity: str = Field(default="high", example="high")
    category: str = Field(default="financial", example="financial")
    business_impact: str = Field(default="")


class MitigationControlRequest(BaseModel):
    """Request for creating mitigation control."""
    control_id: str = Field(..., example="MIT_DUAL_APPROVAL")
    name: str = Field(..., example="Dual Approval Required")
    description: str = Field(default="")
    control_type: str = Field(default="preventive", example="preventive")
    risk_reduction_pct: float = Field(default=50.0, ge=0, le=100)
    applicable_risk_types: List[str] = Field(default_factory=list)
    requires_approval: bool = True
    approvers: List[str] = Field(default_factory=list)


class AssignControlRequest(BaseModel):
    """Request for assigning control to risk."""
    risk_id: str
    control_id: str
    assigned_by: str
    justification: str = ""
    expires_at: Optional[datetime] = None


class ExceptionRequest(BaseModel):
    """Request for risk exception."""
    risk_id: str
    requested_by: str
    justification: str
    expires_at: datetime
    approvers: List[str] = Field(default_factory=list)


class ApproveExceptionRequest(BaseModel):
    """Request for approving exception."""
    exception_id: str
    approved_by: str
    comments: str = ""


class TrendQueryRequest(BaseModel):
    """Request for trend query."""
    from_date: datetime
    to_date: datetime
    granularity: str = Field(default="daily", example="daily")


class UsageDataRequest(BaseModel):
    """Usage data for behavioral analysis."""
    user_id: str
    total_transactions: int = 0
    unique_tcodes_used: int = 0
    sensitive_transactions: int = 0
    off_hours_transactions: int = 0
    weekend_transactions: int = 0
    tcode_counts: Dict[str, int] = Field(default_factory=dict)


# =============================================================================
# Risk Analysis Endpoints
# =============================================================================

@router.post("/analyze/user", response_model=Dict[str, Any])
async def analyze_user_access(
    request: AnalyzeUserRequest,
    background_tasks: BackgroundTasks
):
    """
    Perform comprehensive risk analysis for a user.

    This endpoint evaluates:
    - SoD conflicts between user's functions
    - Sensitive access (high-risk authorizations)
    - Critical actions capability
    - Context-aware risk scoring
    - Optionally: behavioral anomalies

    Returns detailed risk analysis with remediation suggestions.
    """
    engine = get_ara_engine()
    analytics = get_analytics()

    try:
        # Build access map
        access_map = {
            "roles": request.access_data.roles,
            "tcodes": request.access_data.tcodes,
            "auth_objects": request.access_data.auth_objects,
        }

        # Build context
        context = None
        if request.context:
            user_ctx = UserContext(
                user_id=request.access_data.user_id,
                employment_type=request.context.employment_type,
                department=request.context.department,
                is_privileged_user=request.context.is_privileged_user,
                is_emergency_access=request.context.is_emergency_access,
                access_level=request.context.access_level,
                current_location=request.context.current_location,
                previous_violations=request.context.previous_violations,
            )
            context = RiskContext(user_context=user_ctx)

        # Run analysis
        result = engine.analyze_user(
            user_id=request.access_data.user_id,
            access=access_map,
            context=context
        )

        # Index for analytics (background)
        background_tasks.add_task(analytics.index_analysis_result, result)

        # Build response
        response = {
            "analysis_id": result.analysis_id,
            "user_id": result.user_id,
            "analyzed_at": result.analyzed_at.isoformat(),
            "duration_ms": result.duration_ms,
            "summary": {
                "total_risks": result.total_risks,
                "critical_count": result.critical_count,
                "high_count": result.high_count,
                "medium_count": result.medium_count,
                "low_count": result.low_count,
                "aggregate_risk_score": result.aggregate_risk_score,
                "max_risk_score": result.max_risk_score,
            },
            "risks": [r.to_dict() for r in result.risks],
            "sod_conflicts": [c.to_dict() for c in result.sod_conflicts],
        }

        # Add remediation suggestions
        if request.include_remediation and result.risks:
            suggestions = engine.get_remediation_suggestions(result.risks)
            response["remediation_suggestions"] = [s.to_dict() for s in suggestions]

        # Add behavioral analysis
        if request.include_behavioral:
            behavioral = get_behavioral_analyzer()
            identity_score = behavioral.calculate_identity_risk_score(
                request.access_data.user_id
            )
            response["behavioral_analysis"] = {
                "identity_risk_score": identity_score,
                "anomalies_detected": [],  # Would require usage history
            }

        return response

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@router.post("/analyze/batch", response_model=Dict[str, Any])
async def analyze_batch_users(
    users: List[UserAccessData],
    background_tasks: BackgroundTasks
):
    """
    Analyze multiple users in batch.

    Returns aggregated results sorted by risk score.
    """
    engine = get_ara_engine()
    results = []
    errors = []

    for user_data in users:
        try:
            access_map = {
                "roles": user_data.roles,
                "tcodes": user_data.tcodes,
                "auth_objects": user_data.auth_objects,
            }

            result = engine.analyze_user(
                user_id=user_data.user_id,
                access_map=access_map
            )

            results.append({
                "user_id": user_data.user_id,
                "total_risks": result.total_risks,
                "critical_count": result.critical_count,
                "high_count": result.high_count,
                "aggregate_score": result.aggregate_risk_score,
                "status": "analyzed",
            })

        except Exception as e:
            errors.append({
                "user_id": user_data.user_id,
                "error": str(e),
                "status": "failed",
            })

    # Sort by risk
    results.sort(key=lambda x: (x["critical_count"], x["aggregate_score"]), reverse=True)

    return {
        "total_users": len(users),
        "analyzed": len(results),
        "failed": len(errors),
        "results": results,
        "errors": errors,
        "analysis_timestamp": datetime.now().isoformat(),
    }


@router.post("/analyze/role/{role_id}", response_model=Dict[str, Any])
async def analyze_role(role_id: str, tcodes: List[str] = Query(default=[])):
    """
    Analyze a role for inherent risks.

    Evaluates what risks exist within a role's access.
    """
    engine = get_ara_engine()

    access_map = {
        "roles": [role_id],
        "tcodes": tcodes,
        "auth_objects": [],
    }

    result = engine.analyze_user(
        user_id=f"ROLE_ANALYSIS_{role_id}",
        access_map=access_map
    )

    return {
        "role_id": role_id,
        "analyzed_at": result.analyzed_at.isoformat(),
        "risk_summary": {
            "total_risks": result.total_risks,
            "critical_count": result.critical_count,
            "high_count": result.high_count,
            "aggregate_score": result.aggregate_risk_score,
        },
        "sod_conflicts": [c.to_dict() for c in result.sod_conflicts],
        "sensitive_access": [
            r.to_dict() for r in result.risks
            if r.risk_type == RiskType.SENSITIVE_ACCESS
        ],
        "recommendation": "review_required" if result.critical_count > 0 else "acceptable",
    }


# =============================================================================
# Risk Simulation Endpoints
# =============================================================================

@router.post("/simulate/access", response_model=Dict[str, Any])
async def simulate_access_request(request: SimulateAccessRequest):
    """
    Simulate risk impact of granting access.

    Pre-provisioning analysis that shows:
    - Current risk state
    - New risks that would be created
    - Risk score delta
    - Recommendation (approve/review/deny)

    Essential for access request workflows.
    """
    engine = get_ara_engine()

    try:
        result = engine.simulate_access(
            user_id=request.user_id,
            current_access={
                "roles": request.current_roles,
                "tcodes": request.current_tcodes,
            },
            requested_access={
                "roles": request.requested_roles,
                "tcodes": request.requested_tcodes,
            }
        )

        return {
            "simulation_id": result.simulation_id,
            "user_id": result.user_id,
            "simulated_at": result.simulated_at.isoformat(),
            "current_state": {
                "risk_score": result.current_risk_score,
                "risk_count": len(result.current_risks),
            },
            "simulated_state": {
                "risk_score": result.simulated_risk_score,
                "risk_count": len(result.current_risks) + len(result.new_risks),
            },
            "impact": {
                "risk_delta": result.risk_delta,
                "new_sod_conflicts": len(result.new_sod_conflicts),
                "new_sensitive_access": len(result.new_sensitive_access),
            },
            "new_risks": [r.to_dict() for r in result.new_risks],
            "new_sod_conflicts": [c.to_dict() for c in result.new_sod_conflicts],
            "recommendation": result.recommendation,
            "recommendation_reason": result.recommendation_reason,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Simulation failed: {str(e)}")


@router.post("/simulate/role-change", response_model=Dict[str, Any])
async def simulate_role_change(
    user_id: str = Query(...),
    add_roles: List[str] = Query(default=[]),
    remove_roles: List[str] = Query(default=[]),
    current_roles: List[str] = Query(default=[]),
    current_tcodes: List[str] = Query(default=[])
):
    """
    Simulate impact of role changes (add/remove).

    Useful for role re-engineering and access reviews.
    """
    engine = get_ara_engine()

    # Calculate new role set
    new_roles = set(current_roles) | set(add_roles)
    new_roles -= set(remove_roles)

    result = engine.simulate_access(
        user_id=user_id,
        current_access={
            "roles": current_roles,
            "tcodes": current_tcodes,
        },
        requested_access={
            "roles": list(new_roles),
            "tcodes": current_tcodes,
        }
    )

    return {
        "user_id": user_id,
        "role_changes": {
            "added": add_roles,
            "removed": remove_roles,
            "final_roles": list(new_roles),
        },
        "risk_impact": {
            "before": result.current_risk_score,
            "after": result.simulated_risk_score,
            "delta": result.risk_delta,
        },
        "new_conflicts": len(result.new_sod_conflicts),
        "recommendation": result.recommendation,
    }


# =============================================================================
# SoD Rules Management
# =============================================================================

@router.get("/sod/rules", response_model=List[Dict[str, Any]])
async def list_sod_rules(
    category: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    enabled_only: bool = Query(True)
):
    """
    List all SoD rules.

    Supports filtering by category, severity, and enabled status.
    """
    engine = get_ara_engine()
    rules = engine.get_sod_rules()

    result = []
    for rule in rules:
        if enabled_only and not rule.enabled:
            continue
        if category and rule.category.value != category:
            continue
        if severity and rule.severity.value != severity:
            continue
        result.append(rule.to_dict())

    return result


@router.get("/sod/rules/{rule_id}", response_model=Dict[str, Any])
async def get_sod_rule(rule_id: str):
    """Get detailed SoD rule information."""
    engine = get_ara_engine()
    rule = engine.get_sod_rule(rule_id)

    if not rule:
        raise HTTPException(status_code=404, detail=f"Rule {rule_id} not found")

    return rule.to_dict()


@router.post("/sod/rules", response_model=Dict[str, Any])
async def create_sod_rule(request: SoDRuleRequest):
    """
    Create a new SoD rule.

    Defines conflicting functions that should not be combined.
    """
    engine = get_ara_engine()

    try:
        severity = RiskSeverity(request.severity)
    except ValueError:
        severity = RiskSeverity.HIGH

    try:
        category = RiskCategory(request.category)
    except ValueError:
        category = RiskCategory.FINANCIAL

    rule = SoDRule(
        rule_id=request.rule_id,
        name=request.name,
        description=request.description,
        function_1_tcodes=request.function_1_tcodes,
        function_2_tcodes=request.function_2_tcodes,
        severity=severity,
        category=category,
        business_impact=request.business_impact,
    )

    engine.add_sod_rule(rule)

    return {
        "status": "created",
        "rule": rule.to_dict(),
    }


@router.delete("/sod/rules/{rule_id}")
async def delete_sod_rule(rule_id: str):
    """Delete a SoD rule."""
    engine = get_ara_engine()
    success = engine.remove_sod_rule(rule_id)

    if not success:
        raise HTTPException(status_code=404, detail=f"Rule {rule_id} not found")

    return {"status": "deleted", "rule_id": rule_id}


@router.put("/sod/rules/{rule_id}/toggle")
async def toggle_sod_rule(rule_id: str, enabled: bool = Query(...)):
    """Enable or disable a SoD rule."""
    engine = get_ara_engine()
    rule = engine.get_sod_rule(rule_id)

    if not rule:
        raise HTTPException(status_code=404, detail=f"Rule {rule_id} not found")

    rule.enabled = enabled
    return {"status": "updated", "rule_id": rule_id, "enabled": enabled}


# =============================================================================
# Mitigation Control Endpoints
# =============================================================================

@router.get("/mitigation/controls", response_model=List[Dict[str, Any]])
async def list_mitigation_controls(
    control_type: Optional[str] = Query(None),
    active_only: bool = Query(True)
):
    """List all mitigation controls."""
    manager = get_mitigation_manager()
    controls = manager.get_all_controls()

    result = []
    for control in controls:
        if control_type and control.control_type != control_type:
            continue
        if active_only and not control.is_active:
            continue
        result.append(control.to_dict())

    return result


@router.post("/mitigation/controls", response_model=Dict[str, Any])
async def create_mitigation_control(request: MitigationControlRequest):
    """Create a new mitigation control."""
    manager = get_mitigation_manager()

    control = MitigationControl(
        control_id=request.control_id,
        name=request.name,
        description=request.description,
        control_type=request.control_type,
        risk_reduction_pct=request.risk_reduction_pct,
        applicable_risk_types=[RiskType(rt) for rt in request.applicable_risk_types] if request.applicable_risk_types else [],
        requires_approval=request.requires_approval,
        approvers=request.approvers,
    )

    manager.register_control(control)

    return {
        "status": "created",
        "control": control.to_dict(),
    }


@router.post("/mitigation/assign", response_model=Dict[str, Any])
async def assign_mitigation_control(request: AssignControlRequest):
    """
    Assign a mitigation control to a risk.

    Creates a control assignment linking a risk to its mitigation.
    """
    manager = get_mitigation_manager()

    try:
        assignment = manager.assign_control(
            risk_id=request.risk_id,
            control_id=request.control_id,
            assigned_by=request.assigned_by,
            justification=request.justification,
            expires_at=request.expires_at,
        )

        return {
            "status": "assigned",
            "assignment": assignment.to_dict(),
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/mitigation/assignments/{risk_id}")
async def get_risk_mitigation(risk_id: str):
    """Get mitigation assignments for a risk."""
    manager = get_mitigation_manager()
    assignments = manager.get_assignments_for_risk(risk_id)

    return {
        "risk_id": risk_id,
        "assignments": [a.to_dict() for a in assignments],
        "is_mitigated": len(assignments) > 0,
    }


@router.post("/mitigation/exceptions/request", response_model=Dict[str, Any])
async def request_exception(request: ExceptionRequest):
    """
    Request a risk exception.

    Exceptions allow accepting a risk for a limited time with justification.
    """
    manager = get_mitigation_manager()

    try:
        exception = manager.request_exception(
            risk_id=request.risk_id,
            requested_by=request.requested_by,
            justification=request.justification,
            expires_at=request.expires_at,
            approvers=request.approvers,
        )

        return {
            "status": "pending",
            "exception": exception.to_dict(),
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/mitigation/exceptions/approve", response_model=Dict[str, Any])
async def approve_exception(request: ApproveExceptionRequest):
    """Approve a pending exception request."""
    manager = get_mitigation_manager()

    try:
        exception = manager.approve_exception(
            exception_id=request.exception_id,
            approved_by=request.approved_by,
            comments=request.comments,
        )

        return {
            "status": "approved",
            "exception": exception.to_dict(),
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/mitigation/exceptions", response_model=List[Dict[str, Any]])
async def list_exceptions(
    status: Optional[str] = Query(None),
    user_id: Optional[str] = Query(None)
):
    """List risk exceptions."""
    manager = get_mitigation_manager()
    exceptions = manager.get_all_exceptions()

    result = []
    for exc in exceptions:
        if status and exc.status != status:
            continue
        result.append(exc.to_dict())

    return result


# =============================================================================
# Behavioral Analysis Endpoints
# =============================================================================

@router.post("/behavioral/record-usage")
async def record_usage_metrics(request: UsageDataRequest):
    """
    Record usage metrics for behavioral analysis.

    Called periodically to update user activity patterns.
    """
    analyzer = get_behavioral_analyzer()

    metrics = UsageMetrics(
        user_id=request.user_id,
        period_start=datetime.now() - timedelta(days=30),
        period_end=datetime.now(),
        total_transactions=request.total_transactions,
        unique_tcodes=request.unique_tcodes_used,
        sensitive_transactions=request.sensitive_transactions,
        off_hours_transactions=request.off_hours_transactions,
        weekend_transactions=request.weekend_transactions,
        tcode_counts=request.tcode_counts,
    )

    analyzer.record_usage(metrics)

    return {"status": "recorded", "user_id": request.user_id}


@router.get("/behavioral/score/{user_id}")
async def get_behavioral_score(user_id: str):
    """
    Get behavioral/identity risk score for a user.

    Score based on usage patterns and anomalies.
    """
    analyzer = get_behavioral_analyzer()

    # Get usage metrics if available
    usage_metrics = analyzer.user_baselines.get(user_id)

    # Detect any anomalies
    anomalies = analyzer.detect_anomalies(user_id, usage_metrics)

    # Calculate identity risk score
    score_result = analyzer.calculate_identity_risk_score(
        user_id=user_id,
        behavioral_anomalies=anomalies,
        usage_metrics=usage_metrics
    )

    return {
        "user_id": user_id,
        "identity_risk_score": score_result.get("identity_risk_score", 0),
        "breakdown": score_result.get("breakdown", {}),
        "anomalies": [a.to_dict() for a in anomalies] if anomalies else [],
        "risk_level": score_result.get("risk_level", "low"),
    }


@router.get("/behavioral/anomalies")
async def get_all_anomalies(min_severity: str = Query(default="medium")):
    """Get all detected behavioral anomalies."""
    analyzer = get_behavioral_analyzer()

    # This would typically pull from stored anomalies
    # For now, return placeholder
    return {
        "anomalies": [],
        "total_count": 0,
        "min_severity_filter": min_severity,
    }


# =============================================================================
# Analytics Endpoints
# =============================================================================

@router.get("/analytics/summary")
async def get_analytics_summary():
    """
    Get executive-level risk analytics summary.

    Provides high-level metrics for dashboards.
    """
    analytics = get_analytics()
    return analytics.get_executive_summary()


@router.get("/analytics/distribution")
async def get_risk_distribution():
    """Get risk score distribution statistics."""
    analytics = get_analytics()
    return analytics.get_risk_distribution()


@router.post("/analytics/trend", response_model=Dict[str, Any])
async def get_risk_trend(request: TrendQueryRequest):
    """
    Get risk trend over time.

    Returns time-series data for visualization.
    """
    analytics = get_analytics()

    try:
        granularity = TimeGranularity(request.granularity)
    except ValueError:
        granularity = TimeGranularity.DAILY

    trend = analytics.trend_analyzer.get_trend(
        from_date=request.from_date,
        to_date=request.to_date,
        granularity=granularity
    )

    summary = analytics.trend_analyzer.get_trend_summary(
        from_date=request.from_date,
        to_date=request.to_date
    )

    return {
        "period": {
            "from": request.from_date.isoformat(),
            "to": request.to_date.isoformat(),
            "granularity": granularity.value,
        },
        "data_points": [p.to_dict() for p in trend],
        "summary": summary,
    }


@router.get("/analytics/forecast")
async def get_risk_forecast(days_ahead: int = Query(default=30, ge=7, le=90)):
    """
    Get risk forecast for future period.

    Uses historical trends to project future risk.
    """
    analytics = get_analytics()

    forecast = analytics.trend_analyzer.forecast_risk(days_ahead=days_ahead)

    return {
        "forecast_days": days_ahead,
        "data_points": [p.to_dict() for p in forecast],
        "confidence_note": "Forecast based on linear regression of recent trends",
    }


@router.get("/analytics/heatmap/user-category")
async def get_user_category_heatmap(top_n: int = Query(default=20, ge=5, le=100)):
    """Get user vs category risk heatmap data."""
    analytics = get_analytics()
    cells = analytics.get_user_category_heatmap(top_n=top_n)
    return {"cells": [c.to_dict() for c in cells]}


@router.get("/analytics/heatmap/role-severity")
async def get_role_severity_heatmap(top_n: int = Query(default=20, ge=5, le=100)):
    """Get role vs severity risk heatmap data."""
    analytics = get_analytics()
    cells = analytics.get_role_severity_heatmap(top_n=top_n)
    return {"cells": [c.to_dict() for c in cells]}


@router.get("/analytics/leaderboard/users")
async def get_high_risk_users(
    top_n: int = Query(default=10, ge=5, le=50),
    min_critical: int = Query(default=0, ge=0)
):
    """Get leaderboard of high-risk users."""
    analytics = get_analytics()
    users = analytics.get_high_risk_users(top_n=top_n, min_critical=min_critical)
    return {"users": [u.to_dict() for u in users]}


@router.get("/analytics/leaderboard/roles")
async def get_high_risk_roles(top_n: int = Query(default=10, ge=5, le=50)):
    """Get leaderboard of high-risk roles."""
    analytics = get_analytics()
    roles = analytics.get_high_risk_roles(top_n=top_n)
    return {"roles": [r.to_dict() for r in roles]}


@router.get("/analytics/departments")
async def get_department_summary():
    """Get risk summary by department."""
    analytics = get_analytics()
    depts = analytics.get_department_risk_summary()
    return {"departments": [d.to_dict() for d in depts]}


# =============================================================================
# Economic Quantification Endpoints
# =============================================================================

@router.get("/analytics/economic-exposure")
async def get_economic_exposure():
    """
    Get economic risk exposure quantification.

    Provides financial impact estimates for risk portfolio.
    """
    analytics = get_analytics()
    metrics = analytics.calculate_economic_exposure()
    return metrics.to_dict()


@router.post("/analytics/remediation-roi")
async def calculate_remediation_roi(
    risk_ids: List[str],
    remediation_cost: float = Query(..., gt=0)
):
    """
    Calculate ROI of remediating specified risks.

    Helps prioritize remediation investments.
    """
    analytics = get_analytics()

    # Collect risks (would typically fetch from database)
    risks = []  # Placeholder - would fetch by risk_ids

    roi_analysis = analytics.estimate_remediation_roi(
        risks=risks,
        remediation_cost=remediation_cost
    )

    return roi_analysis


# =============================================================================
# Control Effectiveness Endpoints
# =============================================================================

@router.get("/analytics/control-effectiveness")
async def get_control_effectiveness(control_id: Optional[str] = Query(None)):
    """
    Get mitigation control effectiveness metrics.

    Shows how well controls are performing.
    """
    analytics = get_analytics()
    metrics = analytics.get_control_effectiveness(control_id=control_id)
    return {"controls": [m.to_dict() for m in metrics]}


@router.post("/analytics/record-control-event")
async def record_control_event(
    control_id: str,
    event_type: str = Query(..., description="applied|override|exception|recurrence|prevented"),
    user_id: Optional[str] = None,
    risks_covered: int = 0
):
    """
    Record a control event for effectiveness tracking.

    Called by workflows when controls are applied/overridden.
    """
    analytics = get_analytics()

    if event_type == "applied":
        analytics.record_control_application(
            control_id=control_id,
            control_name=control_id,
            user_id=user_id or "unknown",
            risks_covered=risks_covered,
            prevented_incident=False
        )
    elif event_type == "prevented":
        analytics.record_control_application(
            control_id=control_id,
            control_name=control_id,
            user_id=user_id or "unknown",
            risks_covered=risks_covered,
            prevented_incident=True
        )
    elif event_type == "override":
        analytics.record_control_override(control_id)
    elif event_type == "exception":
        analytics.record_control_exception(control_id)
    elif event_type == "recurrence":
        analytics.record_risk_recurrence(control_id)
    else:
        raise HTTPException(status_code=400, detail=f"Unknown event type: {event_type}")

    return {"status": "recorded", "control_id": control_id, "event_type": event_type}
