# AI Intelligence API Router
# Exposes all AI/ML capabilities

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
from datetime import datetime

from core.ai import (
    RiskIntelligenceEngine, ContextualRiskScore,
    NLPPolicyEngine, NaturalLanguageQuery,
    BehavioralAnomalyDetector, AnomalyAlert, RiskIndicator,
    AIRoleOptimizer, RoleMiningResult,
    RemediationAdvisor, RemediationPlan,
    GRCAssistant, AssistantResponse
)

router = APIRouter(prefix="/ai", tags=["AI Intelligence"])

# Initialize AI engines
risk_engine = RiskIntelligenceEngine()
nlp_engine = NLPPolicyEngine()
anomaly_detector = BehavioralAnomalyDetector()
role_optimizer = AIRoleOptimizer()
remediation_advisor = RemediationAdvisor()
grc_assistant = GRCAssistant()


# ==================== Request/Response Models ====================

class RiskAnalysisRequest(BaseModel):
    user_id: str
    violations: List[Dict[str, Any]] = []
    current_access: List[str] = []
    recent_activity: List[Dict[str, Any]] = []


class NLPQueryRequest(BaseModel):
    query: str
    user_id: str = "CURRENT_USER"
    context: Dict[str, Any] = {}


class ActivityRequest(BaseModel):
    user_id: str
    transaction: str = ""
    timestamp: Optional[str] = None
    records_accessed: int = 0
    location: str = ""
    session_id: str = ""
    transactions_per_minute: float = 0


class AlertStatusRequest(BaseModel):
    status: str
    updated_by: str
    notes: str = ""


class RemediationRequest(BaseModel):
    risk_id: str
    risk_type: str
    risk_description: str
    affected_users: List[str] = []
    affected_roles: List[str] = []
    context: Dict[str, Any] = {}


class ChatRequest(BaseModel):
    message: str
    user_id: str
    session_id: Optional[str] = None


class RoleDesignRequest(BaseModel):
    business_function: str
    required_transactions: List[str] = []
    department: str = ""


class FeedbackRequest(BaseModel):
    user_id: str
    risk_factor_id: str
    reason: str


# ==================== Risk Intelligence ====================

@router.post("/risk/analyze")
async def analyze_contextual_risk(request: RiskAnalysisRequest):
    """
    AI-Powered Contextual Risk Analysis

    Goes beyond traditional SoD detection to provide:
    - Context-aware risk scoring
    - Behavioral analysis
    - Peer comparison
    - Future risk prediction
    """
    result = risk_engine.calculate_contextual_risk(
        user_id=request.user_id,
        traditional_violations=request.violations,
        current_access=request.current_access,
        recent_activity=request.recent_activity
    )

    return {
        "user_id": result.user_id,
        "scores": {
            "base_score": result.base_score,
            "contextual_score": result.contextual_score,
            "confidence": result.confidence
        },
        "components": {
            "access_risk": result.access_risk,
            "behavioral_risk": result.behavioral_risk,
            "contextual_risk": result.contextual_risk,
            "historical_risk": result.historical_risk
        },
        "risk_factors": [
            {
                "id": f.id,
                "name": f.name,
                "category": f.category,
                "weight": f.weight,
                "explanation": f.explanation,
                "evidence": f.evidence
            }
            for f in result.risk_factors
        ],
        "mitigating_factors": result.mitigating_factors,
        "peer_comparison": {
            "percentile": result.peer_percentile,
            "department_percentile": result.department_percentile
        },
        "prediction": {
            "predicted_score": result.prediction.predicted_score,
            "confidence": result.prediction.confidence,
            "time_horizon": result.prediction.time_horizon,
            "trend": result.prediction.trend.value,
            "key_drivers": result.prediction.key_drivers,
            "recommended_actions": result.prediction.recommended_actions
        } if result.prediction else None
    }


@router.get("/risk/compare/{user_id}")
async def compare_to_peers(user_id: str):
    """Compare user's risk to their peers"""
    return risk_engine.compare_to_peers(user_id)


@router.get("/risk/department/{department}")
async def analyze_department(department: str):
    """Analyze risk across a department"""
    return risk_engine.analyze_department(department)


@router.post("/risk/feedback/false-positive")
async def record_false_positive(request: FeedbackRequest):
    """Record a false positive to improve AI accuracy"""
    return risk_engine.record_false_positive(
        user_id=request.user_id,
        risk_factor_id=request.risk_factor_id,
        reason=request.reason
    )


# ==================== Natural Language Interface ====================

@router.post("/query")
async def natural_language_query(request: NLPQueryRequest):
    """
    Natural Language Query Interface

    Ask questions in plain English:
    - "Show my risks"
    - "Who has SAP_ALL?"
    - "Compare Finance vs IT risk"
    """
    query = NaturalLanguageQuery(
        text=request.query,
        user_id=request.user_id,
        context=request.context
    )

    result = nlp_engine.process_query(query)

    return {
        "query": request.query,
        "understood_as": result.intent.query_type.value,
        "confidence": result.intent.confidence,
        "parsed_query": result.intent.parsed_query,
        "summary": result.summary,
        "data": result.data,
        "visualization": result.visualization_hint,
        "follow_up_suggestions": result.follow_up_suggestions
    }


@router.get("/query/suggestions/{user_id}")
async def get_query_suggestions(user_id: str):
    """Get contextual query suggestions for a user"""
    return {
        "suggestions": nlp_engine.get_suggestions_for_context(user_id)
    }


# ==================== Behavioral Anomaly Detection ====================

@router.post("/anomaly/analyze")
async def analyze_activity(request: ActivityRequest):
    """
    Real-time Behavioral Anomaly Detection

    Analyzes user activity for unusual patterns:
    - Off-hours access
    - Unusual data volume
    - Unfamiliar transactions
    - Location changes
    """
    activity = {
        "transaction": request.transaction,
        "timestamp": datetime.fromisoformat(request.timestamp) if request.timestamp else datetime.utcnow(),
        "records_accessed": request.records_accessed,
        "location": request.location,
        "session_id": request.session_id,
        "transactions_per_minute": request.transactions_per_minute
    }

    alerts = anomaly_detector.analyze_activity(request.user_id, activity)

    return {
        "user_id": request.user_id,
        "alerts_generated": len(alerts),
        "alerts": [
            {
                "id": a.id,
                "type": a.anomaly_type.value,
                "risk_level": a.risk_indicator.value,
                "description": a.description,
                "expected": a.expected_value,
                "actual": a.actual_value,
                "deviation_score": a.deviation_score,
                "timestamp": a.timestamp.isoformat()
            }
            for a in alerts
        ]
    }


@router.get("/anomaly/alerts")
async def get_active_alerts(
    user_id: Optional[str] = None,
    risk_level: Optional[str] = None,
    limit: int = Query(default=50, le=200)
):
    """Get active anomaly alerts"""
    risk_indicator = None
    if risk_level:
        try:
            risk_indicator = RiskIndicator(risk_level)
        except ValueError:
            pass

    alerts = anomaly_detector.get_active_alerts(
        user_id=user_id,
        risk_level=risk_indicator,
        limit=limit
    )

    return {
        "alerts": [
            {
                "id": a.id,
                "user_id": a.user_id,
                "type": a.anomaly_type.value,
                "risk_level": a.risk_indicator.value,
                "status": a.status.value,
                "description": a.description,
                "timestamp": a.timestamp.isoformat()
            }
            for a in alerts
        ],
        "total": len(alerts)
    }


@router.put("/anomaly/alerts/{alert_id}")
async def update_alert(alert_id: str, request: AlertStatusRequest):
    """Update alert status (investigate, confirm, resolve)"""
    from core.ai.anomaly_detector import AlertStatus

    try:
        status = AlertStatus(request.status)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid status: {request.status}")

    result = anomaly_detector.update_alert_status(
        alert_id=alert_id,
        new_status=status,
        updated_by=request.updated_by,
        notes=request.notes
    )

    if not result["success"]:
        raise HTTPException(status_code=404, detail=result["error"])

    return result


@router.get("/anomaly/user/{user_id}/score")
async def get_user_behavioral_risk(user_id: str):
    """Get behavioral risk score for a user"""
    return anomaly_detector.get_user_risk_score(user_id)


@router.get("/anomaly/summary")
async def get_anomaly_summary():
    """Get summary of anomaly detection status"""
    return anomaly_detector.get_risk_summary()


# ==================== Role Mining & Optimization ====================

@router.post("/roles/mine")
async def mine_roles(
    min_pattern_frequency: float = Query(default=0.3, ge=0.0, le=1.0),
    min_users: int = Query(default=2, ge=1)
):
    """
    AI Role Mining

    Discovers optimal role structures from actual usage patterns:
    - Identifies common access patterns
    - Suggests role consolidations
    - Recommends splits for SoD compliance
    - Identifies unused authorizations
    """
    result = role_optimizer.mine_roles(
        min_pattern_frequency=min_pattern_frequency,
        min_users=min_users
    )

    return {
        "id": result.id,
        "analyzed_at": result.analyzed_at.isoformat(),
        "current_roles": result.current_role_count,
        "recommended_roles": result.recommended_role_count,
        "potential_reduction": f"{result.potential_reduction:.1f}%",
        "issues_found": {
            "unused_authorizations": result.unused_authorizations,
            "over_privileged_users": result.over_privileged_users,
            "sod_conflicts": result.sod_conflicts_found
        },
        "patterns_discovered": len(result.access_patterns),
        "recommendations": [
            {
                "id": r.id,
                "name": r.name,
                "description": r.description,
                "type": r.optimization_type.value,
                "risk_reduction": r.risk_reduction,
                "efficiency_gain": r.efficiency_gain,
                "users_affected": r.users_affected,
                "confidence": r.confidence,
                "reasoning": r.reasoning
            }
            for r in result.recommendations
        ],
        "summary": result.summary
    }


@router.get("/roles/suggestions")
async def get_role_suggestions(focus: Optional[str] = None):
    """Get role optimization suggestions"""
    suggestions = role_optimizer.get_optimization_suggestions(focus=focus)

    return {
        "suggestions": [
            {
                "id": s.id,
                "title": s.title,
                "description": s.description,
                "type": s.optimization_type.value,
                "priority": s.priority,
                "target_roles": s.target_roles,
                "action_items": s.action_items,
                "risk_impact": s.risk_impact,
                "efficiency_impact": s.efficiency_impact,
                "effort": s.effort_level,
                "time_estimate": s.implementation_time
            }
            for s in suggestions
        ]
    }


@router.post("/roles/design")
async def design_role(request: RoleDesignRequest):
    """AI-assisted role design"""
    result = role_optimizer.design_role(
        business_function=request.business_function,
        required_transactions=request.required_transactions,
        department=request.department
    )

    return {
        "id": result.id,
        "name": result.name,
        "description": result.description,
        "transactions": result.transactions,
        "sod_conflicts": result.sod_conflicts,
        "least_privilege_score": result.least_privilege_score,
        "reasoning": result.reasoning,
        "confidence": result.confidence
    }


# ==================== Remediation Advisor ====================

@router.post("/remediation/plan")
async def generate_remediation_plan(request: RemediationRequest):
    """
    AI Remediation Planning

    Generates intelligent remediation plans:
    - Multiple options with trade-offs
    - Impact assessment
    - Step-by-step implementation
    - Auto-executable actions
    """
    plan = remediation_advisor.generate_remediation_plan(
        risk_id=request.risk_id,
        risk_type=request.risk_type,
        risk_description=request.risk_description,
        affected_users=request.affected_users,
        affected_roles=request.affected_roles,
        context=request.context
    )

    return {
        "id": plan.id,
        "risk_id": plan.risk_id,
        "risk_description": plan.risk_description,
        "recommended_approach": plan.recommended_approach,
        "total_risk_reduction": f"{plan.total_risk_reduction:.0f}%",
        "estimated_effort": plan.estimated_effort,
        "confidence": plan.confidence,
        "reasoning": plan.reasoning,
        "recommended_actions": [
            {
                "id": a.id,
                "type": a.action_type.value,
                "title": a.title,
                "description": a.description,
                "complexity": a.complexity.value,
                "priority": a.priority,
                "impact": {
                    "risk_reduction": a.impact.risk_reduction,
                    "users_affected": a.impact.users_affected,
                    "business_impact": a.impact.business_impact,
                    "reversibility": a.impact.reversibility
                } if a.impact else None,
                "steps": a.steps,
                "warnings": a.warnings,
                "can_auto_execute": a.can_auto_execute
            }
            for a in plan.recommended_actions
        ],
        "alternatives": [
            {
                "id": a.id,
                "type": a.action_type.value,
                "title": a.title,
                "description": a.description,
                "complexity": a.complexity.value
            }
            for a in plan.alternatives
        ]
    }


@router.get("/remediation/quick/{risk_type}")
async def get_quick_recommendations(risk_type: str, user_count: int = 1):
    """Get quick remediation recommendations"""
    recommendations = remediation_advisor.get_quick_recommendations(
        risk_type=risk_type,
        user_count=user_count
    )
    return {"recommendations": recommendations}


# ==================== Conversational Assistant ====================

@router.post("/chat")
async def chat_with_assistant(request: ChatRequest):
    """
    Conversational AI Assistant

    Natural language interface for all GRC operations:
    - "Show my risks"
    - "Approve John's request"
    - "I need access to create POs"
    """
    response = grc_assistant.chat(
        user_id=request.user_id,
        message=request.message,
        session_id=request.session_id
    )

    return {
        "message": response.message,
        "success": response.success,
        "query_type": response.query_type.value if response.query_type else None,
        "actions": response.actions,
        "suggestions": response.suggestions,
        "data": response.data,
        "visualization": response.visualization,
        "needs_confirmation": response.needs_confirmation,
        "confirmation_question": response.confirmation_question
    }


@router.get("/chat/suggestions/{user_id}")
async def get_proactive_suggestions(user_id: str):
    """Get proactive suggestions for a user"""
    return {
        "suggestions": grc_assistant.get_proactive_suggestions(user_id)
    }


@router.get("/chat/stats/{user_id}")
async def get_quick_stats(user_id: str):
    """Get quick stats for dashboard widget"""
    return grc_assistant.get_quick_stats(user_id)


# ==================== AI Capabilities Overview ====================

@router.get("/capabilities")
async def get_ai_capabilities():
    """Get overview of AI capabilities"""
    return {
        "capabilities": [
            {
                "name": "Contextual Risk Intelligence",
                "description": "AI-powered risk scoring that considers context, behavior, and predictions",
                "endpoint": "/ai/risk/analyze",
                "features": [
                    "Context-aware scoring",
                    "Behavioral analysis",
                    "Peer comparison",
                    "Future risk prediction"
                ]
            },
            {
                "name": "Natural Language Interface",
                "description": "Query GRC data using plain English",
                "endpoint": "/ai/query",
                "features": [
                    "Intent detection",
                    "Entity extraction",
                    "Conversational context",
                    "Follow-up suggestions"
                ]
            },
            {
                "name": "Behavioral Anomaly Detection",
                "description": "Real-time detection of unusual access patterns",
                "endpoint": "/ai/anomaly/analyze",
                "features": [
                    "Time anomaly detection",
                    "Volume anomaly detection",
                    "Pattern learning",
                    "Continuous adaptation"
                ]
            },
            {
                "name": "Role Mining & Optimization",
                "description": "AI-powered role design and optimization",
                "endpoint": "/ai/roles/mine",
                "features": [
                    "Pattern discovery",
                    "Role consolidation",
                    "SoD conflict prevention",
                    "Least privilege optimization"
                ]
            },
            {
                "name": "Remediation Advisor",
                "description": "Intelligent remediation recommendations",
                "endpoint": "/ai/remediation/plan",
                "features": [
                    "Multiple options with trade-offs",
                    "Impact assessment",
                    "Step-by-step guidance",
                    "Auto-executable actions"
                ]
            },
            {
                "name": "Conversational Assistant",
                "description": "Chat interface for all GRC operations",
                "endpoint": "/ai/chat",
                "features": [
                    "Natural conversations",
                    "Multi-turn dialogs",
                    "Quick actions",
                    "Proactive suggestions"
                ]
            }
        ],
        "advantages_over_traditional_grc": [
            "Context-aware scoring vs binary detection",
            "Predictive analytics vs reactive alerts",
            "Natural language vs complex menus",
            "Continuous learning vs static rules",
            "Behavioral analysis vs access-only checks",
            "Auto-remediation vs manual resolution"
        ]
    }
