"""
GovernEx+ Advanced Capabilities API

These endpoints represent the 5 differentiating features that make
this platform UNBEATABLE compared to SAP GRC:

1. Business Intent Governance
2. Control Effectiveness Scoring
3. Approval Behavior Analytics
4. Identity Risk Scoring
5. Explainable Risk Narratives
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from enum import Enum

# Import the core engines
from core.governance.business_intent import (
    BusinessIntentEngine, BusinessIntent, IntentCategory,
    IntentRiskLevel, IntentStatus
)
from core.assurance.control_effectiveness import (
    ControlEffectivenessEngine, ControlType, TestResult, ControlTest
)
from core.analytics.approval_behavior import (
    ApprovalBehaviorEngine, ApprovalAction, RiskBehaviorPattern
)
from core.identity.identity_risk import (
    IdentityRiskEngine, IdentityStatus, IdentityRiskLevel
)
from core.explainability.risk_narratives import (
    RiskNarrativeEngine, AudienceLevel, NarrativeType
)

router = APIRouter(prefix="/governex-plus", tags=["GovernEx+ Advanced"])

# Initialize engines
intent_engine = BusinessIntentEngine()
effectiveness_engine = ControlEffectivenessEngine()
behavior_engine = ApprovalBehaviorEngine()
identity_engine = IdentityRiskEngine()
narrative_engine = RiskNarrativeEngine()


# =============================================================================
# Request/Response Models
# =============================================================================

class CreateIntentRequest(BaseModel):
    title: str
    description: str
    category: str = "daily_operations"
    business_justification: str
    expected_outcome: str
    business_owner_id: str
    business_owner_name: str
    risk_level: str = "routine"
    valid_days: int = 30
    regulatory_drivers: List[str] = []
    cost_center: Optional[str] = None
    project_code: Optional[str] = None


class RecordApprovalRequest(BaseModel):
    approval_id: str
    approver_id: str
    approver_name: str
    approver_department: str
    manager_level: int = 1
    request_id: str
    request_type: str
    action: str  # approved, rejected, delegated
    risk_level: str
    decision_time_seconds: int
    requestor_id: str
    requestor_department: str
    comments: str = ""
    reviewed_details: bool = False
    accessed_risk_report: bool = False


class CreateIdentityRequest(BaseModel):
    identity_id: str
    employee_id: Optional[str] = None
    email: str
    full_name: str
    department: str
    job_title: str
    manager_id: Optional[str] = None
    manager_name: Optional[str] = None
    hr_status: str = "active"


class AddSystemAccessRequest(BaseModel):
    identity_id: str
    system_id: str
    system_name: str
    account_id: str
    account_type: str = "human"
    status: str = "active"
    roles: List[str] = []
    entitlements: List[str] = []
    last_login: Optional[str] = None
    login_count_30d: int = 0
    privilege_level: str = "standard"


class ExplainRiskRequest(BaseModel):
    user_id: str
    user_name: str
    department: str
    risk_score: float
    risk_level: str
    risk_factors: List[str]
    access_summary: Dict = {}
    peer_average: Optional[float] = None
    audience: str = "manager"


# =============================================================================
# 1. Business Intent Governance
# =============================================================================

@router.post("/intent/create")
async def create_business_intent(request: CreateIntentRequest):
    """
    Create a new business intent.

    Business intents capture the "WHY" behind access requests -
    making them auditable and reusable.
    """
    try:
        category = IntentCategory(request.category)
    except ValueError:
        category = IntentCategory.DAILY_OPERATIONS

    try:
        risk_level = IntentRiskLevel(request.risk_level)
    except ValueError:
        risk_level = IntentRiskLevel.ROUTINE

    valid_until = datetime.utcnow() + timedelta(days=request.valid_days)

    intent = intent_engine.create_intent(
        title=request.title,
        description=request.description,
        category=category,
        business_justification=request.business_justification,
        expected_outcome=request.expected_outcome,
        business_owner_id=request.business_owner_id,
        business_owner_name=request.business_owner_name,
        created_by=request.business_owner_id,
        risk_level=risk_level,
        valid_until=valid_until,
        regulatory_drivers=request.regulatory_drivers,
        cost_center=request.cost_center,
        project_code=request.project_code
    )

    return {
        "success": True,
        "intent": intent.to_dict(),
        "similar_approved_intents": intent.similar_approved_intents,
        "message": f"Business intent '{intent.intent_id}' created successfully"
    }


@router.get("/intent/{intent_id}")
async def get_business_intent(intent_id: str):
    """Get business intent details with full audit trail"""
    return intent_engine.get_intent_trail(intent_id)


@router.post("/intent/{intent_id}/approve")
async def approve_intent(intent_id: str, approver_id: str, comments: str = ""):
    """Approve a business intent"""
    return intent_engine.approve_intent(intent_id, approver_id, comments)


@router.post("/intent/{intent_id}/link-request")
async def link_access_request_to_intent(intent_id: str, request_id: str):
    """Link an access request to a business intent for traceability"""
    return intent_engine.link_access_request(intent_id, request_id)


@router.post("/intent/{original_id}/reuse")
async def reuse_approved_intent(original_id: str, created_by: str):
    """Reuse a previously approved intent for similar scenario"""
    try:
        new_intent = intent_engine.reuse_intent(original_id, created_by)
        return {
            "success": True,
            "new_intent": new_intent.to_dict(),
            "message": f"Intent reused from {original_id}. Auto-approved based on prior approval."
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/intent/templates")
async def list_intent_templates():
    """List available pre-approved intent templates"""
    return {
        "templates": [
            {
                "template_id": t.template_id,
                "name": t.name,
                "category": t.category.value,
                "default_duration_days": t.default_duration_days,
                "auto_approved": t.auto_approved
            }
            for t in intent_engine.templates.values()
        ]
    }


@router.get("/intent/stats")
async def get_intent_statistics():
    """Get business intent governance statistics"""
    return intent_engine.get_statistics()


# =============================================================================
# 2. Control Effectiveness Scoring
# =============================================================================

@router.get("/effectiveness/dashboard")
async def get_assurance_dashboard():
    """
    Get executive assurance dashboard.

    Shows PROOF that controls work, not just that they exist.
    """
    return effectiveness_engine.get_assurance_dashboard()


@router.get("/effectiveness/controls")
async def get_control_effectiveness_report():
    """Get detailed control effectiveness report"""
    return effectiveness_engine.get_control_effectiveness_report()


@router.get("/effectiveness/approval-quality")
async def get_approval_quality_report():
    """Get approval quality analysis report"""
    return effectiveness_engine.get_approval_quality_report()


@router.get("/effectiveness/mitigations")
async def get_mitigation_effectiveness_report():
    """Get mitigation effectiveness report"""
    return effectiveness_engine.get_mitigation_effectiveness_report()


@router.post("/effectiveness/record-approval")
async def record_approval_for_effectiveness(
    approver_id: str,
    approver_name: str,
    request_id: str,
    decision: str,
    risk_level: str,
    decision_time_minutes: int
):
    """Record an approval decision for effectiveness tracking"""
    effectiveness_engine.record_approval_decision(
        approver_id=approver_id,
        approver_name=approver_name,
        request_id=request_id,
        decision=decision,
        risk_level=risk_level,
        decision_time_minutes=decision_time_minutes
    )
    return {"success": True, "message": "Approval recorded for effectiveness analysis"}


# =============================================================================
# 3. Approval Behavior Analytics
# =============================================================================

@router.post("/behavior/record-approval")
async def record_approval_behavior(request: RecordApprovalRequest):
    """
    Record an approval for behavior analysis.

    Detects rubber-stamping, bias, and other governance concerns.
    """
    try:
        action = ApprovalAction(request.action)
    except ValueError:
        action = ApprovalAction.APPROVED

    behavior_engine.record_approval(
        approval_id=request.approval_id,
        approver_id=request.approver_id,
        approver_name=request.approver_name,
        approver_department=request.approver_department,
        manager_level=request.manager_level,
        request_id=request.request_id,
        request_type=request.request_type,
        action=action,
        risk_level=request.risk_level,
        decision_time_seconds=request.decision_time_seconds,
        requestor_id=request.requestor_id,
        requestor_department=request.requestor_department,
        comments=request.comments,
        reviewed_details=request.reviewed_details,
        accessed_risk_report=request.accessed_risk_report
    )

    return {"success": True, "message": "Approval recorded for behavior analysis"}


@router.get("/behavior/report")
async def get_behavior_analytics_report():
    """
    Get comprehensive approval behavior analytics.

    Identifies rubber-stampers, biased approvers, and governance risks.
    """
    return behavior_engine.get_behavior_analytics_report()


@router.get("/behavior/approver/{approver_id}")
async def get_approver_profile(approver_id: str):
    """Get detailed behavior profile for an approver"""
    profile = behavior_engine.get_approver_profile(approver_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Approver not found")

    return {
        "approver_id": profile.approver_id,
        "approver_name": profile.approver_name,
        "department": profile.department,
        "total_decisions": profile.total_decisions,
        "approval_rate": round((profile.approvals / profile.total_decisions * 100) if profile.total_decisions > 0 else 0, 1),
        "scores": {
            "rubber_stamp_score": round(profile.rubber_stamp_score, 1),
            "risk_awareness_score": round(profile.risk_awareness_score, 1),
            "consistency_score": round(profile.consistency_score, 1),
            "engagement_score": round(profile.engagement_score, 1)
        },
        "primary_pattern": profile.primary_pattern.value,
        "pattern_confidence": round(profile.pattern_confidence, 1),
        "recommendations": profile.recommendations,
        "bias_indicators": {
            "department_bias": profile.department_bias,
            "time_of_day_bias": profile.time_of_day_bias
        }
    }


# =============================================================================
# 4. Identity Risk Scoring
# =============================================================================

@router.post("/identity/create")
async def create_identity_profile(request: CreateIdentityRequest):
    """Create or update an identity profile"""
    profile = identity_engine.create_identity_profile(
        identity_id=request.identity_id,
        employee_id=request.employee_id,
        email=request.email,
        full_name=request.full_name,
        department=request.department,
        job_title=request.job_title,
        manager_id=request.manager_id,
        manager_name=request.manager_name,
        hr_status=request.hr_status
    )

    return {
        "success": True,
        "identity_id": profile.identity_id,
        "message": "Identity profile created"
    }


@router.post("/identity/add-access")
async def add_system_access_to_identity(request: AddSystemAccessRequest):
    """Add system access to an identity"""
    try:
        identity_engine.add_system_access(
            identity_id=request.identity_id,
            system_id=request.system_id,
            system_name=request.system_name,
            account_id=request.account_id,
            account_type=request.account_type,
            status=request.status,
            roles=request.roles,
            entitlements=request.entitlements,
            last_login=datetime.fromisoformat(request.last_login) if request.last_login else None,
            login_count_30d=request.login_count_30d,
            privilege_level=request.privilege_level
        )
        return {"success": True, "message": "System access added"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/identity/{identity_id}/risk")
async def get_identity_risk_assessment(identity_id: str):
    """
    Get comprehensive risk assessment for an identity.

    Auditors audit IDENTITIES - this gives them what they need.
    """
    return identity_engine.get_identity_risk_report(identity_id)


@router.get("/identity/hygiene-dashboard")
async def get_identity_hygiene_dashboard():
    """
    Get identity hygiene dashboard.

    Shows ghost identities, dormant accounts, orphaned users.
    """
    return identity_engine.get_identity_hygiene_dashboard()


@router.get("/identity/ghosts")
async def list_ghost_identities():
    """List all ghost identities (terminated but with active access)"""
    ghosts = identity_engine.detect_ghost_identities()
    return {
        "ghost_count": len(ghosts),
        "ghosts": [
            {
                "identity_id": g.identity_id,
                "name": g.full_name,
                "termination_date": g.termination_date.isoformat() if g.termination_date else "Unknown",
                "active_systems": [s.system_name for s in g.system_access.values() if s.status == "active"]
            }
            for g in ghosts
        ]
    }


@router.get("/identity/dormant")
async def list_dormant_identities(days: int = 90):
    """List identities with no activity"""
    dormant = identity_engine.detect_dormant_identities(days)
    return {
        "dormant_count": len(dormant),
        "threshold_days": days,
        "dormant": [
            {
                "identity_id": d.identity_id,
                "name": d.full_name,
                "days_inactive": d.days_since_last_activity
            }
            for d in dormant
        ]
    }


# =============================================================================
# 5. Explainable Risk Narratives
# =============================================================================

@router.post("/explain/user-risk")
async def explain_user_risk(request: ExplainRiskRequest):
    """
    Generate plain-English explanation for user risk.

    EXPLAINABILITY = TRUST, TRUST = ADOPTION
    """
    try:
        audience = AudienceLevel(request.audience)
    except ValueError:
        audience = AudienceLevel.MANAGER

    narrative = narrative_engine.explain_user_risk(
        user_id=request.user_id,
        user_name=request.user_name,
        department=request.department,
        risk_score=request.risk_score,
        risk_level=request.risk_level,
        risk_factors=request.risk_factors,
        access_summary=request.access_summary,
        peer_average=request.peer_average,
        audience=audience
    )

    return {
        "narrative_id": narrative.narrative_id,
        "headline": narrative.headline,
        "summary": narrative.summary,
        "detailed_explanation": narrative.detailed_explanation,
        "key_points": narrative.key_points,
        "evidence": narrative.evidence,
        "recommendations": narrative.recommendations,
        "confidence": narrative.confidence_score,
        "audience": audience.value
    }


@router.post("/explain/approval")
async def explain_approval_decision(
    request_id: str,
    request_type: str,
    decision: str,
    approver_name: str,
    risk_level: str,
    risk_score: float,
    decision_factors: List[str],
    mitigations: List[str] = [],
    audience: str = "auditor"
):
    """Generate explanation for why an approval decision was made"""
    try:
        aud = AudienceLevel(audience)
    except ValueError:
        aud = AudienceLevel.AUDITOR

    narrative = narrative_engine.explain_approval_decision(
        request_id=request_id,
        request_type=request_type,
        decision=decision,
        approver_name=approver_name,
        risk_level=risk_level,
        risk_score=risk_score,
        decision_factors=decision_factors,
        mitigations_applied=mitigations,
        audience=aud
    )

    return {
        "narrative_id": narrative.narrative_id,
        "headline": narrative.headline,
        "summary": narrative.summary,
        "detailed_explanation": narrative.detailed_explanation
    }


@router.post("/explain/violation")
async def explain_sod_violation(
    violation_id: str,
    rule_name: str,
    risk_level: str,
    function1: str,
    function2: str,
    business_impact: str,
    user_name: str,
    audience: str = "manager"
):
    """Generate plain-English explanation for an SoD violation"""
    try:
        aud = AudienceLevel(audience)
    except ValueError:
        aud = AudienceLevel.MANAGER

    narrative = narrative_engine.explain_violation(
        violation_id=violation_id,
        rule_name=rule_name,
        risk_level=risk_level,
        conflicting_functions=[function1, function2],
        business_impact=business_impact,
        user_name=user_name,
        audience=aud
    )

    return {
        "narrative_id": narrative.narrative_id,
        "headline": narrative.headline,
        "summary": narrative.summary,
        "detailed_explanation": narrative.detailed_explanation,
        "recommendations": narrative.recommendations
    }


@router.get("/explain/audit-package/{entity_type}/{entity_id}")
async def get_audit_documentation_package(entity_type: str, entity_id: str):
    """Generate complete audit documentation package for an entity"""
    return narrative_engine.generate_audit_package(entity_type, entity_id)


# =============================================================================
# Summary Dashboard
# =============================================================================

@router.get("/dashboard")
async def get_governex_plus_dashboard():
    """
    Get comprehensive GovernEx+ dashboard.

    Shows the power of the 5 differentiating capabilities.
    """
    return {
        "platform": "GovernEx+",
        "capabilities": {
            "business_intent_governance": {
                "status": "active",
                "description": "Captures and governs the 'WHY' behind access requests",
                "stats": intent_engine.get_statistics()
            },
            "control_effectiveness": {
                "status": "active",
                "description": "Proves controls WORK, not just exist",
                "dashboard": effectiveness_engine.get_assurance_dashboard()
            },
            "approval_behavior_analytics": {
                "status": "active",
                "description": "Ensures approvals are meaningful, not ceremonial",
                "report": behavior_engine.get_behavior_analytics_report()
            },
            "identity_risk_scoring": {
                "status": "active",
                "description": "Risk per identity - because auditors audit identities",
                "hygiene": identity_engine.get_identity_hygiene_dashboard()
            },
            "explainable_risk": {
                "status": "active",
                "description": "Plain-English explanations for all decisions",
                "narratives_generated": len(narrative_engine.generated_narratives)
            }
        },
        "competitive_advantage": [
            "Beyond SAP GRC: Intent-level governance",
            "Auditor-ready: Control effectiveness proof",
            "Governance quality: Approval behavior detection",
            "Identity-centric: Per-user risk scores",
            "Trust through transparency: Explainable AI"
        ]
    }
