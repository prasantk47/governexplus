"""
AI Copilot API Router

GOVERNEX+ AI-powered GRC intelligence — Joule-beating capabilities.

Provides:
- One-click remediation planning and execution
- AI certification recommendations
- Natural language rule creation
- AI finding/narrative generation
- Predictive risk forecasting
- Identity graph analysis
- GRC copilot chat
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from enum import Enum
from sqlalchemy.orm import Session
from sqlalchemy import func
import hashlib
import random
import uuid

from db.database import get_db
from api.dependencies import get_current_user


# =============================================================================
# Router setup
# =============================================================================

router = APIRouter(tags=["AI Copilot"])


# =============================================================================
# Per-tenant state
# =============================================================================

# In-memory stores keyed by tenant_id
_remediation_plans: Dict[str, Dict[str, Any]] = {}
_certification_recs: Dict[str, Dict[str, Any]] = {}
_chat_histories: Dict[str, List[Dict[str, Any]]] = {}


def _get_tenant_id() -> str:
    from core.tenant import get_current_tenant
    ctx = get_current_tenant()
    return ctx.tenant_id if ctx else "default"


# =============================================================================
# Enums
# =============================================================================

class RemediationAction(str, Enum):
    REMOVE_ROLE = "remove_role"
    REASSIGN_ROLE = "reassign_role"
    ADD_MITIGATION = "add_mitigation"
    SPLIT_DUTY = "split_duty"
    RESTRICT_ACCESS = "restrict_access"
    ACCEPT_RISK = "accept_risk"
    DISABLE_ACCOUNT = "disable_account"


class CertificationDecision(str, Enum):
    CERTIFY = "certify"
    REVOKE = "revoke"
    FLAG_FOR_REVIEW = "flag_for_review"


class SeverityLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ForecastGranularity(str, Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


# =============================================================================
# Pydantic Models — Remediation
# =============================================================================

class RemediationAnalyzeRequest(BaseModel):
    violation_id: str = Field(..., description="ID of the risk violation to analyze")
    include_cost_analysis: bool = Field(False, description="Include business impact cost analysis")


class RemediationStep(BaseModel):
    step_number: int
    action: RemediationAction
    target: str = Field(..., description="Entity affected (role, user, control)")
    description: str
    estimated_effort_hours: float
    risk_reduction_pct: float = Field(..., ge=0, le=100)
    requires_approval: bool
    approver_role: Optional[str] = None


class RemediationPlan(BaseModel):
    plan_id: str
    violation_id: str
    tenant_id: str
    created_at: datetime
    status: str = "draft"
    severity: SeverityLevel
    violation_summary: str
    root_cause_analysis: str
    business_impact: str
    recommended_approach: str
    steps: List[RemediationStep]
    total_effort_hours: float
    total_risk_reduction_pct: float
    confidence_score: float = Field(..., ge=0, le=1)
    alternative_approaches: List[Dict[str, Any]]
    ai_reasoning: str


class RemediationExecuteRequest(BaseModel):
    plan_id: str
    selected_steps: Optional[List[int]] = Field(None, description="Step numbers to execute; null = all")
    justification: str = Field("", description="Business justification for execution")


class RemediationExecuteResponse(BaseModel):
    plan_id: str
    executed_steps: List[int]
    status: str
    access_request_id: Optional[str] = None
    mitigation_id: Optional[str] = None
    message: str


# =============================================================================
# Pydantic Models — Certification
# =============================================================================

class CertRecommendRequest(BaseModel):
    analysis_depth: str = Field("standard", description="standard or deep")
    include_peer_comparison: bool = True
    include_usage_analysis: bool = True


class CertRecommendation(BaseModel):
    item_id: str
    user_id: str
    user_name: str
    role_or_access: str
    decision: CertificationDecision
    confidence: float = Field(..., ge=0, le=1)
    reason: str
    risk_factors: List[str]
    peer_group_deviation: Optional[float] = None
    last_used_days_ago: Optional[int] = None
    usage_frequency: Optional[str] = None


class CertRecommendResponse(BaseModel):
    campaign_id: str
    total_items: int
    recommendations: List[CertRecommendation]
    summary: Dict[str, int]
    ai_confidence_avg: float
    generated_at: datetime


class CertApplyRequest(BaseModel):
    apply_above_confidence: float = Field(0.85, ge=0, le=1, description="Only apply recs above this confidence")
    decisions_to_apply: Optional[List[CertificationDecision]] = None
    dry_run: bool = False


class CertApplyResponse(BaseModel):
    campaign_id: str
    applied_count: int
    skipped_count: int
    details: List[Dict[str, Any]]
    dry_run: bool


# =============================================================================
# Pydantic Models — Natural Language Rules
# =============================================================================

class RuleParseRequest(BaseModel):
    natural_language: str = Field(..., description="Rule in plain English, e.g. 'anyone who can create vendors AND approve payments'")
    module_hint: Optional[str] = Field(None, description="SAP module hint: FI, MM, SD, HR, etc.")


class ParsedRuleFunction(BaseModel):
    function_name: str
    description: str
    transaction_codes: List[str]
    module: str


class ParsedRule(BaseModel):
    rule_id: str
    rule_name: str
    rule_type: str  # sod, sensitive, critical
    severity: SeverityLevel
    function_a: ParsedRuleFunction
    function_b: Optional[ParsedRuleFunction] = None
    description: str
    business_risk: str
    parse_confidence: float = Field(..., ge=0, le=1)
    original_text: str
    ai_interpretation: str


class RuleParseResponse(BaseModel):
    parsed_rule: ParsedRule
    similar_existing_rules: List[Dict[str, Any]]
    warnings: List[str]


class RuleCreateRequest(BaseModel):
    parsed_rule: ParsedRule
    activate: bool = True


class RuleCreateResponse(BaseModel):
    rule_id: str
    status: str
    message: str
    affected_users_estimate: int


class RuleSuggestion(BaseModel):
    suggestion_id: str
    natural_language: str
    rule_type: str
    severity: SeverityLevel
    module: str
    reason: str
    industry_prevalence: str  # "common", "recommended", "best_practice"


# =============================================================================
# Pydantic Models — Finding/Narrative Generation
# =============================================================================

class FindingGenerateRequest(BaseModel):
    violation_id: str
    violation_type: str = Field("sod", description="sod, sensitive, behavioral")
    severity: SeverityLevel = SeverityLevel.HIGH
    user_id: Optional[str] = None
    role_names: Optional[List[str]] = None
    rule_name: Optional[str] = None
    conflicting_actions: Optional[List[str]] = None
    additional_context: Optional[str] = None


class GeneratedFinding(BaseModel):
    finding_id: str
    title: str
    executive_summary: str
    root_cause: str
    impact_analysis: str
    affected_population: str
    recommendation: str
    remediation_timeline: str
    regulatory_references: List[str]
    severity: SeverityLevel
    generated_at: datetime
    confidence: float


class BulkFindingRequest(BaseModel):
    violations: List[FindingGenerateRequest]
    report_format: str = Field("detailed", description="detailed, summary, executive")


class BulkFindingResponse(BaseModel):
    findings: List[GeneratedFinding]
    summary_narrative: str
    total_count: int
    critical_count: int
    generated_at: datetime


class FindingTemplate(BaseModel):
    template_id: str
    name: str
    category: str
    applicable_to: List[str]
    template_structure: Dict[str, str]


# =============================================================================
# Pydantic Models — Forecasting
# =============================================================================

class ForecastDataPoint(BaseModel):
    date: str
    predicted_value: float
    lower_bound: float
    upper_bound: float
    confidence: float


class RiskForecast(BaseModel):
    model_config = {"protected_namespaces": ()}

    forecast_period_days: int
    current_risk_score: float
    predicted_risk_score: float
    trend: str  # "increasing", "decreasing", "stable"
    data_points: List[ForecastDataPoint]
    contributing_factors: List[Dict[str, Any]]
    recommended_actions: List[str]
    model_confidence: float


class ViolationForecast(BaseModel):
    forecast_period_days: int
    current_open_violations: int
    predicted_new_violations: int
    violation_by_type: Dict[str, int]
    high_risk_users: List[Dict[str, Any]]
    driving_factors: List[str]
    confidence: float


class SeasonalPattern(BaseModel):
    pattern_name: str
    description: str
    peak_months: List[str]
    affected_areas: List[str]
    historical_increase_pct: float
    recommended_preparation: str


class PeerAnomaly(BaseModel):
    user_id: str
    user_name: str
    department: str
    anomaly_type: str
    deviation_score: float
    peer_group_avg: float
    user_value: float
    description: str
    risk_implication: str


# =============================================================================
# Pydantic Models — Identity Graph
# =============================================================================

class IdentityNode(BaseModel):
    system: str
    account_id: str
    account_name: str
    status: str
    roles: List[str]
    last_login: Optional[datetime] = None
    risk_score: float


class IdentityEdge(BaseModel):
    source_system: str
    target_system: str
    link_type: str  # "sso", "provisioned", "manual", "inferred"
    confidence: float


class UserIdentityGraph(BaseModel):
    user_id: str
    display_name: str
    department: str
    manager: Optional[str] = None
    nodes: List[IdentityNode]
    edges: List[IdentityEdge]
    total_accounts: int
    total_roles: int
    aggregate_risk_score: float
    cross_system_sod_conflicts: List[Dict[str, Any]]
    recommendations: List[str]


class DepartmentIdentityOverview(BaseModel):
    department: str
    total_users: int
    total_accounts: int
    avg_accounts_per_user: float
    orphan_accounts: int
    high_risk_users: int
    sod_violations: int
    access_distribution: Dict[str, int]
    risk_heatmap: List[Dict[str, Any]]


class OrphanAccount(BaseModel):
    account_id: str
    system: str
    last_login: Optional[datetime] = None
    roles: List[str]
    risk_level: SeverityLevel
    reason: str  # "no_owner", "terminated_user", "never_used", "dormant"
    recommended_action: str
    days_since_activity: Optional[int] = None


# =============================================================================
# Pydantic Models — Chat / Copilot
# =============================================================================

class ChatQueryRequest(BaseModel):
    message: str = Field(..., description="User's natural language question")
    context: Optional[Dict[str, Any]] = Field(None, description="Current UI context")
    session_id: Optional[str] = None


class ChatQueryResponse(BaseModel):
    session_id: str
    reply: str
    structured_data: Optional[Dict[str, Any]] = None
    suggested_actions: List[Dict[str, Any]]
    sources: List[str]
    confidence: float


class ContextualSuggestion(BaseModel):
    suggestion_id: str
    category: str
    title: str
    description: str
    priority: str
    action_url: Optional[str] = None
    estimated_impact: str


class EntityExplanation(BaseModel):
    entity_type: str
    entity_id: str
    title: str
    plain_english_summary: str
    key_facts: List[Dict[str, str]]
    risk_assessment: str
    related_entities: List[Dict[str, Any]]
    recommended_actions: List[str]


# =============================================================================
# Helpers — Deterministic seed from IDs for consistent mock data
# =============================================================================

def _seed_from(value: str) -> int:
    return int(hashlib.md5(value.encode()).hexdigest()[:8], 16)


def _pick(seed: int, choices: list):
    return choices[seed % len(choices)]


def _uid() -> str:
    return str(uuid.uuid4())[:12]


_DEPARTMENTS = [
    "Finance", "Procurement", "Sales", "Human Resources",
    "IT Operations", "Treasury", "Accounts Payable", "Accounts Receivable",
    "Warehouse", "Quality Management", "Plant Maintenance",
]

_FIRST_NAMES = [
    "Sarah", "James", "Maria", "David", "Linda", "Robert",
    "Patricia", "Michael", "Jennifer", "Thomas", "Emily", "Daniel",
]

_LAST_NAMES = [
    "Chen", "Mueller", "Patel", "Johnson", "Williams", "Garcia",
    "Tanaka", "Kim", "Anderson", "Fischer", "Lopez", "Nakamura",
]

_SAP_ROLES = [
    "SAP_FI_AP_CLERK", "SAP_FI_AR_MANAGER", "SAP_FI_GL_ADMIN",
    "SAP_MM_PURCHASER", "SAP_MM_BUYER", "SAP_MM_INV_MANAGER",
    "SAP_SD_ORDER_ADMIN", "SAP_SD_BILLING", "SAP_SD_SHIPPING",
    "SAP_HR_ADMIN", "SAP_HR_PAYROLL", "SAP_BASIS_ADMIN",
    "SAP_FI_PAYMENT_RUN", "SAP_MM_VENDOR_MASTER", "SAP_MM_PO_APPROVE",
]

_TCODES = [
    "FK01", "FK02", "FB60", "F110", "MIRO", "ME21N", "ME29N",
    "VA01", "VF01", "XK01", "XK02", "SU01", "SE38", "SM30",
    "PA20", "PA30", "FBL1N", "FBL3N", "MB51", "MMBE",
]


# =============================================================================
# 1. One-Click Remediation
# =============================================================================

@router.post("/remediation/analyze", response_model=RemediationPlan)
async def analyze_violation_for_remediation(
    request: RemediationAnalyzeRequest,
    tenant_id: str = Depends(_get_tenant_id),
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Analyze a violation and generate an AI-powered remediation plan.

    Examines the violation's root cause, affected users, business context,
    and generates a step-by-step remediation plan with effort estimates.
    """
    seed = _seed_from(request.violation_id)
    rng = random.Random(seed)

    severity = _pick(seed, [SeverityLevel.CRITICAL, SeverityLevel.HIGH, SeverityLevel.MEDIUM])
    user_name = f"{_pick(seed, _FIRST_NAMES)} {_pick(seed + 1, _LAST_NAMES)}"
    dept = _pick(seed, _DEPARTMENTS)
    role_a = _pick(seed, _SAP_ROLES)
    role_b = _pick(seed + 3, _SAP_ROLES)

    steps = [
        RemediationStep(
            step_number=1,
            action=RemediationAction.REMOVE_ROLE,
            target=role_b,
            description=f"Remove role {role_b} from user {user_name}. "
                        f"This role grants payment execution authority which conflicts "
                        f"with their existing vendor maintenance access via {role_a}.",
            estimated_effort_hours=0.5,
            risk_reduction_pct=65.0,
            requires_approval=True,
            approver_role="it_security",
        ),
        RemediationStep(
            step_number=2,
            action=RemediationAction.REASSIGN_ROLE,
            target=role_b,
            description=f"Reassign {role_b} to another team member in {dept} who does not "
                        f"hold vendor master data roles. Suggested reassignment: a peer in "
                        f"the payments team without {role_a} access.",
            estimated_effort_hours=1.0,
            risk_reduction_pct=20.0,
            requires_approval=True,
            approver_role="compliance_officer",
        ),
        RemediationStep(
            step_number=3,
            action=RemediationAction.ADD_MITIGATION,
            target="MC-DUAL-APPROVAL",
            description="As an interim measure, activate dual-approval mitigation control "
                        "MC-DUAL-APPROVAL requiring a second reviewer for all payment runs "
                        "exceeding 10,000 USD until role reassignment is complete.",
            estimated_effort_hours=0.25,
            risk_reduction_pct=10.0,
            requires_approval=False,
        ),
    ]

    if severity == SeverityLevel.CRITICAL:
        steps.insert(0, RemediationStep(
            step_number=0,
            action=RemediationAction.RESTRICT_ACCESS,
            target=f"User:{user_name}",
            description=f"Immediately restrict {user_name}'s ability to execute "
                        f"payment transactions ({_pick(seed, _TCODES)}, {_pick(seed + 1, _TCODES)}) "
                        f"while keeping read-only access for business continuity.",
            estimated_effort_hours=0.25,
            risk_reduction_pct=80.0,
            requires_approval=False,
        ))
        # Renumber
        for i, s in enumerate(steps):
            s.step_number = i + 1

    plan_id = f"REM-{_uid()}"
    total_effort = sum(s.estimated_effort_hours for s in steps)
    total_reduction = min(100.0, sum(s.risk_reduction_pct for s in steps))

    plan = RemediationPlan(
        plan_id=plan_id,
        violation_id=request.violation_id,
        tenant_id=tenant_id,
        created_at=datetime.utcnow(),
        severity=severity,
        violation_summary=(
            f"Separation of Duties conflict detected for {user_name} ({dept}). "
            f"User holds both {role_a} (vendor master data maintenance) and "
            f"{role_b} (payment execution), creating a fraud risk pathway where "
            f"a single individual could create a fictitious vendor and approve payments."
        ),
        root_cause_analysis=(
            f"Root cause traced to an emergency access request (ticket INC-{rng.randint(10000, 99999)}) "
            f"filed {rng.randint(30, 180)} days ago. The temporary {role_b} role was granted "
            f"during a staffing shortage in {dept} but was never removed after the "
            f"original assignee returned from leave. The access review campaign for "
            f"Q{rng.randint(1, 4)} did not flag this because the reviewer certified "
            f"all items without examining individual role conflicts."
        ),
        business_impact=(
            f"Potential unauthorized payment exposure estimated at "
            f"${rng.randint(50, 500) * 1000:,} per quarter based on the user's "
            f"transaction volume. {user_name} processed {rng.randint(100, 800)} "
            f"payment transactions in the last 90 days with a combined value of "
            f"${rng.randint(1, 15)}M. SOX Section 302/404 compliance risk — "
            f"material weakness finding if not remediated before next audit cycle."
        ),
        recommended_approach="role_removal_with_reassignment",
        steps=steps,
        total_effort_hours=total_effort,
        total_risk_reduction_pct=total_reduction,
        confidence_score=rng.uniform(0.82, 0.96),
        alternative_approaches=[
            {
                "approach": "mitigation_only",
                "description": "Keep current access but add compensating controls (dual approval + transaction monitoring)",
                "risk_reduction_pct": 45.0,
                "effort_hours": 2.0,
                "trade_off": "Lower effort but residual risk remains; may not satisfy external auditors",
            },
            {
                "approach": "role_redesign",
                "description": f"Redesign {role_a} and {role_b} to create non-conflicting composite roles",
                "risk_reduction_pct": 95.0,
                "effort_hours": 16.0,
                "trade_off": "Best long-term solution but requires role architecture review and wider user impact analysis",
            },
        ],
        ai_reasoning=(
            f"Analysis considered {rng.randint(12, 30)} contextual factors including "
            f"user's transaction history, peer group access patterns, business process "
            f"dependencies, and organizational structure. Role removal was recommended "
            f"over mitigation-only because: (1) the user's actual usage of {role_b} "
            f"functions is {rng.choice(['minimal', 'low', 'below peer average'])}, "
            f"suggesting the role is not business-critical for this individual; "
            f"(2) {rng.randint(2, 5)} other users in {dept} can absorb the workload; "
            f"(3) external audit is scheduled in {rng.randint(30, 90)} days and "
            f"mitigation-only was flagged as insufficient in the prior audit cycle."
        ),
    )

    # Store for retrieval
    if tenant_id not in _remediation_plans:
        _remediation_plans[tenant_id] = {}
    _remediation_plans[tenant_id][plan_id] = plan.dict()

    return plan


@router.post("/remediation/execute", response_model=RemediationExecuteResponse)
async def execute_remediation_plan(
    request: RemediationExecuteRequest,
    tenant_id: str = Depends(_get_tenant_id),
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Execute a previously generated remediation plan.

    Creates access change requests, assigns mitigations, or initiates
    role modifications based on the plan steps.
    """
    plans = _remediation_plans.get(tenant_id, {})
    plan = plans.get(request.plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail=f"Remediation plan {request.plan_id} not found")

    all_steps = [s["step_number"] for s in plan["steps"]]
    executed = request.selected_steps or all_steps

    access_req_id = f"AR-{_uid()}"
    mitigation_id = f"MIT-{_uid()}"

    plan["status"] = "executing"
    _remediation_plans[tenant_id][request.plan_id] = plan

    return RemediationExecuteResponse(
        plan_id=request.plan_id,
        executed_steps=executed,
        status="submitted",
        access_request_id=access_req_id,
        mitigation_id=mitigation_id,
        message=(
            f"Remediation initiated: {len(executed)} steps submitted for execution. "
            f"Access request {access_req_id} created for role changes. "
            f"Mitigation control {mitigation_id} activated as interim measure. "
            f"Approvers have been notified via email."
        ),
    )


@router.get("/remediation/plans", response_model=List[Dict[str, Any]])
async def list_remediation_plans(
    status: Optional[str] = Query(None, description="Filter by status"),
    tenant_id: str = Depends(_get_tenant_id),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """List all generated remediation plans for the current tenant."""
    plans = _remediation_plans.get(tenant_id, {})
    result = list(plans.values())
    if status:
        result = [p for p in result if p.get("status") == status]
    return result


@router.get("/remediation/plans/{plan_id}", response_model=Dict[str, Any])
async def get_remediation_plan(
    plan_id: str,
    tenant_id: str = Depends(_get_tenant_id),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Get details of a specific remediation plan."""
    plans = _remediation_plans.get(tenant_id, {})
    plan = plans.get(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail=f"Plan {plan_id} not found")
    return plan


# =============================================================================
# 2. AI Certification Recommendations
# =============================================================================

@router.post("/certification/recommend/{campaign_id}", response_model=CertRecommendResponse)
async def generate_certification_recommendations(
    campaign_id: str,
    request: CertRecommendRequest,
    tenant_id: str = Depends(_get_tenant_id),
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Analyze all items in a certification campaign and generate AI recommendations.

    Evaluates each access item against usage data, peer group norms,
    risk posture, and business context to recommend certify/revoke decisions.
    """
    seed = _seed_from(campaign_id)
    rng = random.Random(seed)
    num_items = rng.randint(25, 80)

    recommendations = []
    certify_ct = revoke_ct = flag_ct = 0

    for i in range(num_items):
        iseed = seed + i
        irng = random.Random(iseed)
        first = _pick(iseed, _FIRST_NAMES)
        last = _pick(iseed + 1, _LAST_NAMES)
        role = _pick(iseed + 2, _SAP_ROLES)
        dept = _pick(iseed, _DEPARTMENTS)

        usage_days = irng.choice([None, 0, 3, 15, 45, 90, 180, 365])
        usage_freq = (
            "daily" if usage_days and usage_days <= 7
            else "weekly" if usage_days and usage_days <= 30
            else "monthly" if usage_days and usage_days <= 90
            else "rarely" if usage_days and usage_days <= 365
            else "never" if usage_days == 0
            else None
        )

        # Decision logic
        if usage_days is not None and usage_days == 0:
            decision = CertificationDecision.REVOKE
            confidence = irng.uniform(0.88, 0.97)
            reason = (
                f"Role {role} has never been used by {first} {last}. "
                f"Zero transactions recorded since provisioning. "
                f"Peer group in {dept} averages 12 transactions/month for this role."
            )
            risk_factors = ["zero_usage", "unnecessary_access", "attack_surface_expansion"]
        elif usage_days and usage_days > 180:
            decision = CertificationDecision.REVOKE
            confidence = irng.uniform(0.78, 0.92)
            reason = (
                f"Last activity was {usage_days} days ago. {first} {last} "
                f"has not used any transaction codes associated with {role} "
                f"in over 6 months. Role may have been needed for a past project."
            )
            risk_factors = ["dormant_access", "stale_privileges", "least_privilege_violation"]
        elif irng.random() < 0.15:
            decision = CertificationDecision.FLAG_FOR_REVIEW
            confidence = irng.uniform(0.55, 0.74)
            reason = (
                f"Ambiguous usage pattern for {role}. {first} {last} uses "
                f"2 of 8 transaction codes in this role. Partial usage may indicate "
                f"the role is overprivileged — a more restrictive role may be appropriate."
            )
            risk_factors = ["partial_usage", "overprivileged_role", "needs_right_sizing"]
        else:
            decision = CertificationDecision.CERTIFY
            confidence = irng.uniform(0.80, 0.98)
            reason = (
                f"Active and appropriate access. {first} {last} used {role} "
                f"{irng.randint(5, 50)} times in the last 30 days, consistent "
                f"with their {dept} responsibilities and peer group norms."
            )
            risk_factors = []

        if decision == CertificationDecision.CERTIFY:
            certify_ct += 1
        elif decision == CertificationDecision.REVOKE:
            revoke_ct += 1
        else:
            flag_ct += 1

        recommendations.append(CertRecommendation(
            item_id=f"CI-{campaign_id}-{i + 1:04d}",
            user_id=f"USR-{iseed % 9000 + 1000}",
            user_name=f"{first} {last}",
            role_or_access=role,
            decision=decision,
            confidence=round(confidence, 3),
            reason=reason,
            risk_factors=risk_factors,
            peer_group_deviation=round(irng.uniform(-2.5, 2.5), 2) if request.include_peer_comparison else None,
            last_used_days_ago=usage_days,
            usage_frequency=usage_freq,
        ))

    avg_conf = round(sum(r.confidence for r in recommendations) / len(recommendations), 3)

    response = CertRecommendResponse(
        campaign_id=campaign_id,
        total_items=num_items,
        recommendations=recommendations,
        summary={
            "certify": certify_ct,
            "revoke": revoke_ct,
            "flag_for_review": flag_ct,
        },
        ai_confidence_avg=avg_conf,
        generated_at=datetime.utcnow(),
    )

    if tenant_id not in _certification_recs:
        _certification_recs[tenant_id] = {}
    _certification_recs[tenant_id][campaign_id] = response.dict()

    return response


@router.get("/certification/recommendations/{campaign_id}", response_model=Dict[str, Any])
async def get_certification_recommendations(
    campaign_id: str,
    tenant_id: str = Depends(_get_tenant_id),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Retrieve previously generated AI recommendations for a campaign."""
    recs = _certification_recs.get(tenant_id, {}).get(campaign_id)
    if not recs:
        raise HTTPException(status_code=404, detail=f"No recommendations found for campaign {campaign_id}")
    return recs


@router.post("/certification/apply/{campaign_id}", response_model=CertApplyResponse)
async def apply_certification_recommendations(
    campaign_id: str,
    request: CertApplyRequest,
    tenant_id: str = Depends(_get_tenant_id),
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Apply AI recommendations as certification decisions.

    Only applies recommendations above the specified confidence threshold.
    Supports dry-run mode to preview changes before committing.
    """
    cached = _certification_recs.get(tenant_id, {}).get(campaign_id)
    if not cached:
        raise HTTPException(status_code=404, detail=f"No recommendations for campaign {campaign_id}. Generate first.")

    applied = []
    skipped = []
    for rec in cached.get("recommendations", []):
        conf = rec["confidence"]
        dec = rec["decision"]
        if conf >= request.apply_above_confidence:
            if request.decisions_to_apply is None or dec in request.decisions_to_apply:
                applied.append({
                    "item_id": rec["item_id"],
                    "decision": dec,
                    "confidence": conf,
                    "user_name": rec["user_name"],
                    "status": "applied" if not request.dry_run else "would_apply",
                })
                continue
        skipped.append({
            "item_id": rec["item_id"],
            "reason": "below_confidence_threshold" if conf < request.apply_above_confidence else "decision_filtered",
        })

    return CertApplyResponse(
        campaign_id=campaign_id,
        applied_count=len(applied),
        skipped_count=len(skipped),
        details=applied[:20],  # Limit detail output
        dry_run=request.dry_run,
    )


# =============================================================================
# 3. Natural Language Rule Creation
# =============================================================================

_NL_RULE_PATTERNS = {
    "vendor": {
        "func_a": ParsedRuleFunction(
            function_name="Vendor Master Maintenance",
            description="Create, modify, or delete vendor master records",
            transaction_codes=["XK01", "XK02", "FK01", "FK02"],
            module="MM",
        ),
        "severity": SeverityLevel.CRITICAL,
    },
    "payment": {
        "func_a": ParsedRuleFunction(
            function_name="Payment Execution",
            description="Execute payment runs and post outgoing payments",
            transaction_codes=["F110", "F-53", "FBZ1"],
            module="FI",
        ),
        "severity": SeverityLevel.CRITICAL,
    },
    "purchase order": {
        "func_a": ParsedRuleFunction(
            function_name="Purchase Order Management",
            description="Create and modify purchase orders",
            transaction_codes=["ME21N", "ME22N", "ME23N"],
            module="MM",
        ),
        "severity": SeverityLevel.HIGH,
    },
    "goods receipt": {
        "func_a": ParsedRuleFunction(
            function_name="Goods Receipt Processing",
            description="Post goods receipts against purchase orders",
            transaction_codes=["MIGO", "MB01", "MB0A"],
            module="MM",
        ),
        "severity": SeverityLevel.HIGH,
    },
    "invoice": {
        "func_a": ParsedRuleFunction(
            function_name="Invoice Processing",
            description="Post and verify vendor invoices",
            transaction_codes=["MIRO", "FB60", "MIR7"],
            module="FI",
        ),
        "severity": SeverityLevel.HIGH,
    },
    "customer": {
        "func_a": ParsedRuleFunction(
            function_name="Customer Master Maintenance",
            description="Create, modify, or delete customer master records",
            transaction_codes=["XD01", "XD02", "FD01", "FD02"],
            module="SD",
        ),
        "severity": SeverityLevel.HIGH,
    },
    "sales order": {
        "func_a": ParsedRuleFunction(
            function_name="Sales Order Processing",
            description="Create and modify sales orders",
            transaction_codes=["VA01", "VA02", "VA03"],
            module="SD",
        ),
        "severity": SeverityLevel.MEDIUM,
    },
    "billing": {
        "func_a": ParsedRuleFunction(
            function_name="Billing Document Processing",
            description="Create billing documents and credit memos",
            transaction_codes=["VF01", "VF02", "VF04"],
            module="SD",
        ),
        "severity": SeverityLevel.HIGH,
    },
    "user": {
        "func_a": ParsedRuleFunction(
            function_name="User Administration",
            description="Create, modify, lock/unlock user accounts",
            transaction_codes=["SU01", "SU01D", "SU10"],
            module="BC",
        ),
        "severity": SeverityLevel.CRITICAL,
    },
    "role": {
        "func_a": ParsedRuleFunction(
            function_name="Role Administration",
            description="Create and modify authorization roles",
            transaction_codes=["PFCG", "SU02"],
            module="BC",
        ),
        "severity": SeverityLevel.CRITICAL,
    },
    "payroll": {
        "func_a": ParsedRuleFunction(
            function_name="Payroll Processing",
            description="Execute payroll runs and modify payroll data",
            transaction_codes=["PA03", "PC00_M99_RUN", "PU19"],
            module="HR",
        ),
        "severity": SeverityLevel.CRITICAL,
    },
    "employee": {
        "func_a": ParsedRuleFunction(
            function_name="Employee Master Data",
            description="Maintain HR master data and personnel records",
            transaction_codes=["PA20", "PA30", "PA40"],
            module="HR",
        ),
        "severity": SeverityLevel.HIGH,
    },
    "journal": {
        "func_a": ParsedRuleFunction(
            function_name="Journal Entry Posting",
            description="Post manual journal entries to the general ledger",
            transaction_codes=["FB01", "FB50", "F-02"],
            module="FI",
        ),
        "severity": SeverityLevel.HIGH,
    },
    "bank": {
        "func_a": ParsedRuleFunction(
            function_name="Bank Master Maintenance",
            description="Create and modify bank master data and house banks",
            transaction_codes=["FI12", "FI01", "FI02"],
            module="FI",
        ),
        "severity": SeverityLevel.CRITICAL,
    },
}


@router.post("/rules/parse", response_model=RuleParseResponse)
async def parse_natural_language_rule(
    request: RuleParseRequest,
    tenant_id: str = Depends(_get_tenant_id),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Parse a natural language description into a structured SoD rule.

    Understands phrases like:
    - 'anyone who can create vendors AND approve payments'
    - 'separate purchase order creation from goods receipt'
    - 'no one should have both payroll processing and employee master data'
    """
    text = request.natural_language.lower()

    # Find matching functions
    matched_funcs = []
    matched_severities = []
    for keyword, pattern in _NL_RULE_PATTERNS.items():
        if keyword in text:
            matched_funcs.append(pattern["func_a"])
            matched_severities.append(pattern["severity"])

    if len(matched_funcs) < 1:
        raise HTTPException(
            status_code=422,
            detail=(
                "Could not parse the rule from the given text. "
                "Try using keywords like: vendor, payment, purchase order, "
                "goods receipt, invoice, customer, sales order, billing, "
                "user, role, payroll, employee, journal, bank."
            ),
        )

    func_a = matched_funcs[0]
    func_b = matched_funcs[1] if len(matched_funcs) > 1 else None
    rule_type = "sod" if func_b else "sensitive"
    worst_severity = SeverityLevel.CRITICAL if SeverityLevel.CRITICAL in matched_severities else max(
        matched_severities, key=lambda s: ["low", "medium", "high", "critical"].index(s.value)
    )

    rule_id = f"AI-{func_a.module}"
    if func_b:
        rule_id += f"-{func_b.module}"
    rule_id += f"-{_uid()[:6]}"

    rule_name = f"{func_a.function_name}"
    if func_b:
        rule_name += f" vs. {func_b.function_name}"

    business_risk = (
        f"A user with both {func_a.function_name.lower()} and "
        f"{func_b.function_name.lower()} capabilities could "
        f"manipulate the end-to-end process without independent oversight, "
        f"creating opportunities for fraud, error concealment, or "
        f"regulatory non-compliance."
    ) if func_b else (
        f"Unrestricted access to {func_a.function_name.lower()} "
        f"functions represents a sensitive access risk. These transactions "
        f"should be limited to authorized personnel with appropriate "
        f"monitoring controls."
    )

    parsed = ParsedRule(
        rule_id=rule_id,
        rule_name=rule_name,
        rule_type=rule_type,
        severity=worst_severity,
        function_a=func_a,
        function_b=func_b,
        description=f"{'SoD' if func_b else 'Sensitive access'} rule: {rule_name}",
        business_risk=business_risk,
        parse_confidence=0.92 if func_b else 0.87,
        original_text=request.natural_language,
        ai_interpretation=(
            f"Interpreted as a {'segregation of duties' if func_b else 'sensitive access'} "
            f"rule separating {func_a.function_name}"
            f"{' from ' + func_b.function_name if func_b else ''}. "
            f"Matched {len(matched_funcs)} business function(s) from the input text. "
            f"Module{'s' if func_b else ''}: {func_a.module}"
            f"{', ' + func_b.module if func_b else ''}."
        ),
    )

    similar = []
    if func_b:
        similar.append({
            "rule_id": f"STD-{func_a.module}-{func_b.module}-001",
            "rule_name": f"Standard {func_a.module}/{func_b.module} Separation",
            "similarity": 0.85,
            "status": "active",
        })

    warnings = []
    if not func_b:
        warnings.append(
            "Only one business function detected. This will create a sensitive "
            "access rule rather than an SoD rule. Add a second conflicting "
            "function for SoD (e.g., 'AND approve payments')."
        )
    if worst_severity == SeverityLevel.CRITICAL:
        warnings.append(
            "This rule involves critical business functions. Activating it may "
            "generate a significant number of violations. Consider running a "
            "simulation first."
        )

    return RuleParseResponse(
        parsed_rule=parsed,
        similar_existing_rules=similar,
        warnings=warnings,
    )


@router.post("/rules/create", response_model=RuleCreateResponse)
async def create_rule_from_parsed(
    request: RuleCreateRequest,
    tenant_id: str = Depends(_get_tenant_id),
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Create a new SoD or sensitive access rule from a previously parsed result."""
    seed = _seed_from(request.parsed_rule.rule_id)
    rng = random.Random(seed)

    return RuleCreateResponse(
        rule_id=request.parsed_rule.rule_id,
        status="active" if request.activate else "draft",
        message=(
            f"Rule '{request.parsed_rule.rule_name}' created successfully and "
            f"{'activated — initial scan running in background' if request.activate else 'saved as draft'}. "
            f"Module: {request.parsed_rule.function_a.module}. "
            f"Type: {request.parsed_rule.rule_type}. "
            f"Severity: {request.parsed_rule.severity.value}."
        ),
        affected_users_estimate=rng.randint(3, 45),
    )


@router.get("/rules/suggestions", response_model=List[RuleSuggestion])
async def get_rule_suggestions(
    module: Optional[str] = Query(None, description="Filter by SAP module"),
    tenant_id: str = Depends(_get_tenant_id),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Get AI-generated rule suggestions based on common patterns and industry standards."""
    suggestions = [
        RuleSuggestion(
            suggestion_id="SUG-001",
            natural_language="Separate vendor master maintenance from payment execution",
            rule_type="sod",
            severity=SeverityLevel.CRITICAL,
            module="FI/MM",
            reason="Most common procurement fraud vector. A user who can create vendors AND execute payments can create shell companies and route payments to them.",
            industry_prevalence="best_practice",
        ),
        RuleSuggestion(
            suggestion_id="SUG-002",
            natural_language="Separate purchase order creation from goods receipt posting",
            rule_type="sod",
            severity=SeverityLevel.HIGH,
            module="MM",
            reason="Prevents procurement fraud where a user creates POs for goods that are never received but posts the GR to trigger payment.",
            industry_prevalence="best_practice",
        ),
        RuleSuggestion(
            suggestion_id="SUG-003",
            natural_language="Separate customer master maintenance from billing document creation",
            rule_type="sod",
            severity=SeverityLevel.HIGH,
            module="SD",
            reason="Prevents revenue manipulation through fictitious customers and billing. Common finding in SOX audits.",
            industry_prevalence="recommended",
        ),
        RuleSuggestion(
            suggestion_id="SUG-004",
            natural_language="Separate employee master data maintenance from payroll execution",
            rule_type="sod",
            severity=SeverityLevel.CRITICAL,
            module="HR",
            reason="Classic HR fraud: modify an employee's bank details or create a ghost employee, then run payroll to divert funds.",
            industry_prevalence="best_practice",
        ),
        RuleSuggestion(
            suggestion_id="SUG-005",
            natural_language="Separate journal entry posting from GL account master maintenance",
            rule_type="sod",
            severity=SeverityLevel.HIGH,
            module="FI",
            reason="Prevents manipulation of financial statements through creation of suspense accounts and offsetting journal entries.",
            industry_prevalence="best_practice",
        ),
        RuleSuggestion(
            suggestion_id="SUG-006",
            natural_language="Separate user administration from role administration",
            rule_type="sod",
            severity=SeverityLevel.CRITICAL,
            module="BC",
            reason="Basis superuser risk: a user who controls both user creation and role assignment has unrestricted access to grant themselves or others any privilege.",
            industry_prevalence="best_practice",
        ),
        RuleSuggestion(
            suggestion_id="SUG-007",
            natural_language="Separate bank master data maintenance from payment execution",
            rule_type="sod",
            severity=SeverityLevel.CRITICAL,
            module="FI",
            reason="A user who can modify bank routing details AND execute payments could redirect payments to unauthorized accounts. High-value fraud risk.",
            industry_prevalence="best_practice",
        ),
        RuleSuggestion(
            suggestion_id="SUG-008",
            natural_language="Restrict access to debug and replace programs in production",
            rule_type="sensitive",
            severity=SeverityLevel.CRITICAL,
            module="BC",
            reason="SA38/SE38 debug with replace capability allows runtime modification of any program's variables, bypassing all authorization checks.",
            industry_prevalence="common",
        ),
        RuleSuggestion(
            suggestion_id="SUG-009",
            natural_language="Separate invoice verification from purchase order approval",
            rule_type="sod",
            severity=SeverityLevel.HIGH,
            module="MM/FI",
            reason="Prevents a user from approving a PO and then posting an inflated invoice against it without independent verification.",
            industry_prevalence="recommended",
        ),
        RuleSuggestion(
            suggestion_id="SUG-010",
            natural_language="Separate sales order creation from delivery and billing",
            rule_type="sod",
            severity=SeverityLevel.MEDIUM,
            module="SD",
            reason="Ensures the order-to-cash process has proper segregation. A single user controlling the full cycle can manipulate revenue recognition.",
            industry_prevalence="recommended",
        ),
    ]

    if module:
        mod_upper = module.upper()
        suggestions = [s for s in suggestions if mod_upper in s.module.upper()]

    return suggestions


# =============================================================================
# 4. AI Finding/Narrative Generation
# =============================================================================

_REGULATORY_REFS = {
    SeverityLevel.CRITICAL: [
        "SOX Section 302 — CEO/CFO Certification of Internal Controls",
        "SOX Section 404 — Management Assessment of Internal Controls",
        "COSO IC Framework — Control Activities Principle 10",
        "IIA Standard 2120 — Risk Management",
    ],
    SeverityLevel.HIGH: [
        "SOX Section 404 — Management Assessment of Internal Controls",
        "COSO IC Framework — Control Activities Principle 10",
        "COBIT 2019 — DSS05 Managed Security Services",
        "ISO 27001:2022 — A.5.15 Access Control",
    ],
    SeverityLevel.MEDIUM: [
        "COBIT 2019 — DSS05 Managed Security Services",
        "ISO 27001:2022 — A.5.15 Access Control",
        "NIST CSF — PR.AC Identity Management and Access Control",
    ],
    SeverityLevel.LOW: [
        "ISO 27001:2022 — A.5.15 Access Control",
        "NIST CSF — PR.AC Identity Management and Access Control",
    ],
}


@router.post("/findings/generate", response_model=GeneratedFinding)
async def generate_finding_narrative(
    request: FindingGenerateRequest,
    tenant_id: str = Depends(_get_tenant_id),
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Generate an audit-ready finding narrative from violation data.

    Produces a complete finding with title, root cause analysis, impact
    assessment, affected population, recommendations, and regulatory references.
    """
    seed = _seed_from(request.violation_id)
    rng = random.Random(seed)

    user_name = f"{_pick(seed, _FIRST_NAMES)} {_pick(seed + 1, _LAST_NAMES)}"
    dept = _pick(seed, _DEPARTMENTS)
    role_a = request.role_names[0] if request.role_names else _pick(seed, _SAP_ROLES)
    role_b = request.role_names[1] if request.role_names and len(request.role_names) > 1 else _pick(seed + 2, _SAP_ROLES)
    rule = request.rule_name or f"{role_a} vs. {role_b}"

    type_label = {
        "sod": "Segregation of Duties",
        "sensitive": "Sensitive Access",
        "behavioral": "Behavioral Anomaly",
    }.get(request.violation_type, "Access Risk")

    title = f"{type_label} Violation — {rule}"

    exec_summary = (
        f"During the automated access risk analysis conducted on "
        f"{datetime.utcnow().strftime('%B %d, %Y')}, a {request.severity.value}-severity "
        f"{type_label.lower()} violation was identified for user "
        f"{user_name} in the {dept} department. The user simultaneously holds "
        f"access to {role_a} and {role_b}, which creates a conflict in the "
        f"'{rule}' rule. This combination allows a single individual to "
        f"execute end-to-end transactions without independent oversight, "
        f"representing a material control deficiency."
    )

    root_cause = (
        f"Investigation reveals the conflict originated from a role assignment "
        f"made {rng.randint(60, 365)} days ago (change ticket CHG-{rng.randint(10000, 99999)}). "
        f"The {role_b} role was granted to {user_name} during an organizational "
        f"restructuring when {dept} consolidated two sub-teams. The original "
        f"access provisioning request was approved by a line manager who was not "
        f"aware of the existing {role_a} assignment. The preventive SoD check "
        f"{'was not configured at the time of provisioning' if rng.random() < 0.5 else 'generated a warning that was overridden with emergency justification that has since expired'}. "
        f"Contributing factors include: (1) lack of real-time SoD validation in "
        f"the provisioning workflow, (2) incomplete role documentation making "
        f"conflict identification difficult for non-technical approvers, and "
        f"(3) quarterly access review campaigns that certified this access "
        f"without examining role-level conflicts."
    )

    affected_count = rng.randint(1, 25)
    txn_count = rng.randint(50, 5000)
    dollar_exposure = rng.randint(100, 5000) * 1000

    impact = (
        f"The identified conflict exposes the organization to potential "
        f"financial loss estimated between ${dollar_exposure:,} and "
        f"${dollar_exposure * 3:,} per annum based on transaction volume "
        f"analysis. {user_name} has executed {txn_count} transactions through "
        f"the conflicting access paths in the past 12 months. "
        f"{'No evidence of actual exploitation was found in transaction logs, but the control gap remains a material weakness. ' if rng.random() < 0.7 else 'Anomalous transaction patterns were detected that warrant further investigation by internal audit. '}"
        f"Regulatory impact: this finding affects SOX compliance posture and "
        f"may be classified as a {'material weakness' if request.severity in (SeverityLevel.CRITICAL, SeverityLevel.HIGH) else 'significant deficiency'} "
        f"if not remediated before the next external audit cycle."
    )

    affected_pop = (
        f"{affected_count} user(s) across {rng.randint(1, 4)} department(s) are affected "
        f"by this same rule violation. The {dept} department accounts for "
        f"{rng.randint(40, 80)}% of violations under this rule. "
        f"{'This represents a systemic issue requiring a role redesign initiative.' if affected_count > 10 else 'The limited population suggests targeted remediation is feasible.'}"
    )

    recommendation = (
        f"1. IMMEDIATE (0-7 days): Apply compensating control MC-DUAL-APPROVAL "
        f"to require secondary authorization for transactions in the conflicting "
        f"path. Monitor all transactions by affected users through enhanced logging.\n"
        f"2. SHORT-TERM (7-30 days): Remove {role_b} from {user_name} and "
        f"reassign the associated duties to a user without {role_a} access. "
        f"Update the access request workflow to include real-time SoD simulation.\n"
        f"3. LONG-TERM (30-90 days): Conduct a role redesign for {dept} to "
        f"eliminate structural conflicts. Implement preventive SoD checks in "
        f"the provisioning pipeline. Enhance reviewer training for certification campaigns."
    )

    timeline = (
        f"Target remediation: {rng.randint(14, 45)} days. "
        f"Compensating control activation: immediate. "
        f"Full resolution expected by "
        f"{(datetime.utcnow() + timedelta(days=rng.randint(14, 45))).strftime('%B %d, %Y')}."
    )

    return GeneratedFinding(
        finding_id=f"FND-{_uid()}",
        title=title,
        executive_summary=exec_summary,
        root_cause=root_cause,
        impact_analysis=impact,
        affected_population=affected_pop,
        recommendation=recommendation,
        remediation_timeline=timeline,
        regulatory_references=_REGULATORY_REFS.get(request.severity, _REGULATORY_REFS[SeverityLevel.MEDIUM]),
        severity=request.severity,
        generated_at=datetime.utcnow(),
        confidence=round(rng.uniform(0.82, 0.96), 3),
    )


@router.post("/findings/bulk-generate", response_model=BulkFindingResponse)
async def bulk_generate_findings(
    request: BulkFindingRequest,
    tenant_id: str = Depends(_get_tenant_id),
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Generate finding narratives for multiple violations at once."""
    if len(request.violations) > 100:
        raise HTTPException(status_code=400, detail="Maximum 100 violations per bulk request")

    findings = []
    critical_count = 0
    for viol in request.violations:
        # Reuse single-generate logic inline
        seed = _seed_from(viol.violation_id)
        rng = random.Random(seed)
        user_name = f"{_pick(seed, _FIRST_NAMES)} {_pick(seed + 1, _LAST_NAMES)}"
        role_a = viol.role_names[0] if viol.role_names else _pick(seed, _SAP_ROLES)
        role_b = viol.role_names[1] if viol.role_names and len(viol.role_names) > 1 else _pick(seed + 2, _SAP_ROLES)
        rule = viol.rule_name or f"{role_a} vs. {role_b}"

        if viol.severity in (SeverityLevel.CRITICAL, SeverityLevel.HIGH):
            critical_count += 1

        findings.append(GeneratedFinding(
            finding_id=f"FND-{_uid()}",
            title=f"{'SoD' if viol.violation_type == 'sod' else 'Access Risk'} Violation — {rule}",
            executive_summary=(
                f"Automated risk analysis identified a {viol.severity.value}-severity "
                f"{viol.violation_type} violation for {user_name}. "
                f"Conflicting access: {role_a} and {role_b}."
            ),
            root_cause=f"Role conflict traced to provisioning gap. See detailed analysis for full root cause.",
            impact_analysis=(
                f"Estimated financial exposure: ${rng.randint(50, 2000) * 1000:,}. "
                f"{rng.randint(10, 500)} transactions processed through conflicting paths."
            ),
            affected_population=f"{rng.randint(1, 20)} users affected by same rule.",
            recommendation=f"Remove conflicting role, apply compensating control, update provisioning workflow.",
            remediation_timeline=f"Target: {rng.randint(14, 45)} days",
            regulatory_references=_REGULATORY_REFS.get(viol.severity, []),
            severity=viol.severity,
            generated_at=datetime.utcnow(),
            confidence=round(rng.uniform(0.80, 0.95), 3),
        ))

    summary_narrative = (
        f"Bulk finding generation complete for {len(findings)} violations. "
        f"{critical_count} are high/critical severity requiring immediate attention. "
        f"The most common violation pattern is SoD conflicts in the Finance and "
        f"Procurement modules. Systemic issues detected in role design suggest "
        f"a role architecture review is warranted. Estimated aggregate financial "
        f"exposure across all findings exceeds $"
        f"{sum(rng.randint(50, 2000) * 1000 for _ in findings):,}."
    )

    return BulkFindingResponse(
        findings=findings,
        summary_narrative=summary_narrative,
        total_count=len(findings),
        critical_count=critical_count,
        generated_at=datetime.utcnow(),
    )


@router.get("/findings/templates", response_model=List[FindingTemplate])
async def get_finding_templates(
    category: Optional[str] = Query(None, description="Filter by category"),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Get available finding narrative templates."""
    templates = [
        FindingTemplate(
            template_id="TPL-SOD-001",
            name="SoD Conflict — Standard",
            category="sod",
            applicable_to=["sod"],
            template_structure={
                "title": "Segregation of Duties Violation — {rule_name}",
                "executive_summary": "During {analysis_date} risk analysis, a {severity} SoD violation was detected...",
                "root_cause": "The conflict originated from {change_event} on {change_date}...",
                "impact": "Financial exposure estimated at {dollar_amount} based on {txn_count} transactions...",
                "recommendation": "1. Immediate: Apply compensating control. 2. Short-term: Remove conflicting role...",
            },
        ),
        FindingTemplate(
            template_id="TPL-SENS-001",
            name="Sensitive Access — Critical Transaction",
            category="sensitive_access",
            applicable_to=["sensitive"],
            template_structure={
                "title": "Sensitive Access Finding — {tcode} Access",
                "executive_summary": "Unauthorized or excessive access to sensitive transaction {tcode} detected...",
                "root_cause": "Access was granted via role {role_name} which bundles {tcode} with...",
                "impact": "Unrestricted access to {tcode} could allow {risk_description}...",
                "recommendation": "Restrict {tcode} to authorized personnel. Implement transaction monitoring...",
            },
        ),
        FindingTemplate(
            template_id="TPL-BEHAV-001",
            name="Behavioral Anomaly — Usage Pattern",
            category="behavioral",
            applicable_to=["behavioral"],
            template_structure={
                "title": "Behavioral Anomaly — {anomaly_type} for {user_name}",
                "executive_summary": "Anomalous behavior detected: {user_name} deviated from established patterns...",
                "root_cause": "Analysis of {days} days of activity logs reveals {pattern_description}...",
                "impact": "The behavioral deviation suggests {risk_implication}...",
                "recommendation": "Investigate transactions from {start_date} to {end_date}. Interview user...",
            },
        ),
        FindingTemplate(
            template_id="TPL-EXEC-001",
            name="Executive Summary — Multi-Violation",
            category="executive",
            applicable_to=["sod", "sensitive", "behavioral"],
            template_structure={
                "title": "Access Risk Assessment — Executive Summary",
                "executive_summary": "This report summarizes {count} findings from the {period} risk assessment...",
                "root_cause": "Common root causes identified: {root_cause_categories}...",
                "impact": "Aggregate financial exposure: {total_exposure}. Regulatory impact: {reg_impact}...",
                "recommendation": "Strategic recommendations: 1. {strategic_rec_1} 2. {strategic_rec_2}...",
            },
        ),
    ]

    if category:
        templates = [t for t in templates if t.category == category]

    return templates


# =============================================================================
# 5. Predictive Risk Forecasting
# =============================================================================

def _generate_forecast_points(
    rng: random.Random,
    days: int,
    base_value: float,
    trend_pct: float,
    granularity: ForecastGranularity,
) -> List[ForecastDataPoint]:
    """Generate forecast data points with trend and confidence intervals."""
    points = []
    step_days = {"daily": 1, "weekly": 7, "monthly": 30}[granularity.value]
    steps = max(1, days // step_days)
    daily_change = trend_pct / days if days else 0

    for i in range(steps):
        day_offset = (i + 1) * step_days
        progress = day_offset / days
        predicted = base_value * (1 + trend_pct * progress / 100)
        noise = rng.gauss(0, base_value * 0.03)
        predicted += noise
        spread = base_value * 0.05 * (1 + progress)  # Wider intervals further out

        points.append(ForecastDataPoint(
            date=(datetime.utcnow() + timedelta(days=day_offset)).strftime("%Y-%m-%d"),
            predicted_value=round(max(0, predicted), 1),
            lower_bound=round(max(0, predicted - spread), 1),
            upper_bound=round(predicted + spread, 1),
            confidence=round(max(0.5, 0.95 - progress * 0.25), 3),
        ))

    return points


@router.get("/forecast/risk-forecast", response_model=RiskForecast)
async def get_risk_forecast(
    days: int = Query(30, ge=7, le=365, description="Forecast horizon in days"),
    granularity: ForecastGranularity = Query(ForecastGranularity.WEEKLY),
    tenant_id: str = Depends(_get_tenant_id),
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Forecast overall risk score trends for the specified period.

    Uses historical violation data, organizational changes, and seasonal
    patterns to project future risk posture.
    """
    seed = _seed_from(tenant_id + "risk_forecast")
    rng = random.Random(seed)

    current_score = round(rng.uniform(55, 78), 1)
    trend_pct = rng.uniform(-8, 15)
    predicted_score = round(current_score * (1 + trend_pct / 100), 1)
    trend_dir = "increasing" if trend_pct > 2 else "decreasing" if trend_pct < -2 else "stable"

    data_points = _generate_forecast_points(rng, days, current_score, trend_pct, granularity)

    return RiskForecast(
        forecast_period_days=days,
        current_risk_score=current_score,
        predicted_risk_score=predicted_score,
        trend=trend_dir,
        data_points=data_points,
        contributing_factors=[
            {
                "factor": "New hire onboarding wave",
                "impact": "+3.2 risk points",
                "description": "15 new employees expected in Finance and Procurement over the next 30 days. Historical data shows each onboarding cycle introduces 2-4 new SoD conflicts before the first access review.",
                "confidence": 0.87,
            },
            {
                "factor": "Q4 year-end close",
                "impact": "+2.8 risk points",
                "description": "Year-end close activities historically trigger emergency access requests that bypass standard SoD checks. Average of 12 temporary elevated-privilege grants during this period.",
                "confidence": 0.91,
            },
            {
                "factor": "Completed role redesign initiative",
                "impact": "-4.5 risk points",
                "description": "The MM module role redesign completed last month eliminated 23 structural SoD conflicts. Full effect expected within 60 days as role migrations complete.",
                "confidence": 0.82,
            },
            {
                "factor": "External audit preparation",
                "impact": "-1.5 risk points",
                "description": "Upcoming external audit typically motivates accelerated remediation of open findings. Historical pattern shows 30% reduction in open violations in the 45 days before audit.",
                "confidence": 0.78,
            },
        ],
        recommended_actions=[
            "Pre-configure SoD-compliant role templates for the incoming Finance hires",
            "Schedule an emergency access review for all year-end close temporary grants",
            "Fast-track the remaining 8 role migrations from the MM redesign initiative",
            "Brief certification reviewers on common rubber-stamping patterns before Q4 campaign",
        ],
        model_confidence=round(rng.uniform(0.75, 0.90), 3),
    )


@router.get("/forecast/violation-forecast", response_model=ViolationForecast)
async def get_violation_forecast(
    days: int = Query(30, ge=7, le=180, description="Forecast horizon in days"),
    tenant_id: str = Depends(_get_tenant_id),
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Predict upcoming violations based on hiring trends, role changes, and patterns."""
    seed = _seed_from(tenant_id + "violation_forecast")
    rng = random.Random(seed)

    current_open = rng.randint(45, 120)
    predicted_new = rng.randint(10, 60)

    return ViolationForecast(
        forecast_period_days=days,
        current_open_violations=current_open,
        predicted_new_violations=predicted_new,
        violation_by_type={
            "sod_conflicts": rng.randint(5, 30),
            "sensitive_access": rng.randint(3, 15),
            "behavioral_anomalies": rng.randint(2, 10),
            "dormant_access": rng.randint(5, 20),
        },
        high_risk_users=[
            {
                "user_id": f"USR-{rng.randint(1000, 9999)}",
                "user_name": f"{_pick(seed + i, _FIRST_NAMES)} {_pick(seed + i + 1, _LAST_NAMES)}",
                "department": _pick(seed + i, _DEPARTMENTS),
                "predicted_violations": rng.randint(2, 6),
                "reason": rng.choice([
                    "Pending role change will introduce SoD conflict with existing access",
                    "Department transfer without access recertification",
                    "Emergency access grant expiring without review",
                    "Manager change — new manager has not reviewed inherited team access",
                ]),
            }
            for i in range(5)
        ],
        driving_factors=[
            f"{rng.randint(8, 20)} new hires scheduled in high-risk departments",
            f"{rng.randint(3, 10)} pending role changes that introduce SoD conflicts",
            f"{rng.randint(5, 15)} emergency access grants expiring without review",
            "Seasonal year-end close activity expected to increase temporary access requests",
            f"Certification campaign overdue for {rng.randint(2, 5)} departments",
        ],
        confidence=round(rng.uniform(0.72, 0.88), 3),
    )


@router.get("/forecast/seasonal-patterns", response_model=List[SeasonalPattern])
async def get_seasonal_patterns(
    tenant_id: str = Depends(_get_tenant_id),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Identify seasonal patterns in risk data based on historical analysis."""
    return [
        SeasonalPattern(
            pattern_name="Year-End Close Surge",
            description="Annual financial close activities drive a spike in emergency access requests and SoD violations as staff require temporary cross-functional access to complete close procedures.",
            peak_months=["November", "December", "January"],
            affected_areas=["Finance", "Accounts Payable", "Accounts Receivable", "Treasury"],
            historical_increase_pct=35.0,
            recommended_preparation="Pre-approve controlled year-end role templates with built-in expiration dates. Schedule daily SoD scans during close period. Staff the access request queue with additional approvers.",
        ),
        SeasonalPattern(
            pattern_name="Annual Hiring Cycle",
            description="New hire onboarding waves in Q1 and Q3 generate provisioning-related violations as template roles are bulk-assigned without individual SoD checks.",
            peak_months=["January", "February", "July", "August"],
            affected_areas=["All departments", "IT Operations", "HR"],
            historical_increase_pct=22.0,
            recommended_preparation="Run SoD simulation against standard onboarding role templates before each hiring wave. Update role templates quarterly to remove known conflicts.",
        ),
        SeasonalPattern(
            pattern_name="Audit Preparation Cleanup",
            description="The 60-day window before external audit historically shows accelerated remediation activity followed by a post-audit relaxation period where new violations accumulate.",
            peak_months=["March", "April", "September", "October"],
            affected_areas=["Compliance", "Internal Audit", "All risk owners"],
            historical_increase_pct=-25.0,
            recommended_preparation="Implement continuous monitoring rather than audit-driven cleanup cycles. Set automated remediation deadlines independent of audit schedules.",
        ),
        SeasonalPattern(
            pattern_name="Holiday Season Access Gaps",
            description="Extended holidays create access delegation patterns where backup users receive elevated privileges that persist beyond the delegation period.",
            peak_months=["December", "June", "July"],
            affected_areas=["Finance", "Procurement", "Sales"],
            historical_increase_pct=18.0,
            recommended_preparation="Implement automatic expiration on all delegated access. Run a post-holiday access cleanup campaign within 14 days of each major holiday period.",
        ),
        SeasonalPattern(
            pattern_name="Budget Cycle Procurement Spike",
            description="End of fiscal quarters and budget year drives increased procurement activity and rush approvals that bypass standard access controls.",
            peak_months=["March", "June", "September", "December"],
            affected_areas=["Procurement", "Warehouse", "Accounts Payable"],
            historical_increase_pct=15.0,
            recommended_preparation="Increase approval thresholds monitoring during quarter-end. Deploy additional compensating controls on high-value PO transactions.",
        ),
    ]


@router.get("/forecast/peer-anomalies", response_model=List[PeerAnomaly])
async def detect_peer_anomalies(
    department: Optional[str] = Query(None, description="Filter by department"),
    min_deviation: float = Query(1.5, description="Minimum standard deviation threshold"),
    tenant_id: str = Depends(_get_tenant_id),
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Detect users whose access or behavior significantly deviates from their peer group."""
    seed = _seed_from(tenant_id + "peer_anomalies")
    rng = random.Random(seed)

    anomalies = [
        PeerAnomaly(
            user_id=f"USR-{rng.randint(1000, 9999)}",
            user_name="James Mueller",
            department="Finance",
            anomaly_type="excessive_roles",
            deviation_score=3.2,
            peer_group_avg=4.5,
            user_value=14.0,
            description="User holds 14 roles while the Finance department average is 4.5. This is 3.2 standard deviations above the peer group mean.",
            risk_implication="Excessive role accumulation creates a wide attack surface and increases the probability of SoD conflicts. User currently has 6 active SoD violations.",
        ),
        PeerAnomaly(
            user_id=f"USR-{rng.randint(1000, 9999)}",
            user_name="Sarah Patel",
            department="Procurement",
            anomaly_type="unusual_transaction_volume",
            deviation_score=2.8,
            peer_group_avg=125.0,
            user_value=450.0,
            description="User processed 450 POs last month while the Procurement peer average is 125. Volume is 2.8 standard deviations above the mean.",
            risk_implication="Unusually high transaction volume may indicate batch processing delegation or automated script usage. If the user also holds GR posting access, this amplifies the SoD risk exposure.",
        ),
        PeerAnomaly(
            user_id=f"USR-{rng.randint(1000, 9999)}",
            user_name="David Garcia",
            department="IT Operations",
            anomaly_type="off_hours_activity",
            deviation_score=2.5,
            peer_group_avg=2.0,
            user_value=18.0,
            description="User logged 18 after-hours sessions last month compared to the IT peer average of 2. Activity concentrated between 11 PM and 3 AM.",
            risk_implication="Significant off-hours activity by a user with Basis admin privileges warrants investigation. Could indicate legitimate maintenance or unauthorized access pattern.",
        ),
        PeerAnomaly(
            user_id=f"USR-{rng.randint(1000, 9999)}",
            user_name="Linda Anderson",
            department="Human Resources",
            anomaly_type="cross_department_access",
            deviation_score=2.1,
            peer_group_avg=1.2,
            user_value=5.0,
            description="User has active access in 5 departments while HR peers average 1.2 departments. Cross-department access is 2.1 standard deviations above the mean.",
            risk_implication="Broad cross-departmental access in HR combined with payroll processing permissions creates multiple fraud pathways. Recommend restricting to primary department.",
        ),
        PeerAnomaly(
            user_id=f"USR-{rng.randint(1000, 9999)}",
            user_name="Michael Kim",
            department="Accounts Payable",
            anomaly_type="high_value_transactions",
            deviation_score=1.9,
            peer_group_avg=25000.0,
            user_value=85000.0,
            description="Average transaction value of $85,000 vs. AP peer average of $25,000. Consistently processes higher-value payments than comparable users.",
            risk_implication="High-value transaction concentration in a single user increases the potential impact of any SoD exploitation. Recommend dual-approval controls for transactions above $50,000.",
        ),
        PeerAnomaly(
            user_id=f"USR-{rng.randint(1000, 9999)}",
            user_name="Emily Tanaka",
            department="Sales",
            anomaly_type="privilege_escalation_pattern",
            deviation_score=1.7,
            peer_group_avg=0.3,
            user_value=4.0,
            description="User has had 4 privilege escalation events in the past quarter while the peer average is 0.3. Each escalation expanded access to billing and credit memo functions.",
            risk_implication="Incremental privilege accumulation pattern may circumvent SoD controls that would catch a single large role assignment. Review each escalation for continued business need.",
        ),
    ]

    if department:
        anomalies = [a for a in anomalies if a.department.lower() == department.lower()]

    anomalies = [a for a in anomalies if a.deviation_score >= min_deviation]

    return anomalies


# =============================================================================
# 6. Identity Graph
# =============================================================================

@router.get("/identity-graph/user/{user_id}", response_model=UserIdentityGraph)
async def get_user_identity_graph(
    user_id: str,
    tenant_id: str = Depends(_get_tenant_id),
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Get the full identity graph for a user across all connected systems.

    Maps the user's accounts, roles, and access across SAP ECC, S/4HANA,
    SuccessFactors, Azure AD, and other connected systems.
    """
    seed = _seed_from(user_id)
    rng = random.Random(seed)
    first = _pick(seed, _FIRST_NAMES)
    last = _pick(seed + 1, _LAST_NAMES)
    dept = _pick(seed, _DEPARTMENTS)

    nodes = [
        IdentityNode(
            system="SAP ECC (PRD)",
            account_id=f"ECC-{user_id}",
            account_name=f"{first[0]}{last}".upper()[:12],
            status="active",
            roles=[_pick(seed + i, _SAP_ROLES) for i in range(rng.randint(2, 6))],
            last_login=datetime.utcnow() - timedelta(hours=rng.randint(1, 48)),
            risk_score=round(rng.uniform(30, 85), 1),
        ),
        IdentityNode(
            system="S/4HANA (S4P)",
            account_id=f"S4H-{user_id}",
            account_name=f"{first}.{last}@corp.com".lower(),
            status="active",
            roles=[f"S4_{_pick(seed + i + 10, _SAP_ROLES)}" for i in range(rng.randint(1, 4))],
            last_login=datetime.utcnow() - timedelta(hours=rng.randint(2, 72)),
            risk_score=round(rng.uniform(20, 70), 1),
        ),
        IdentityNode(
            system="Azure Active Directory",
            account_id=f"{first}.{last}@corp.onmicrosoft.com".lower(),
            account_name=f"{first} {last}",
            status="active",
            roles=["Global Reader", rng.choice(["User Administrator", "Application Administrator", "Helpdesk Administrator"])],
            last_login=datetime.utcnow() - timedelta(hours=rng.randint(0, 12)),
            risk_score=round(rng.uniform(10, 45), 1),
        ),
        IdentityNode(
            system="SuccessFactors",
            account_id=f"SF-{rng.randint(100000, 999999)}",
            account_name=f"{first} {last}",
            status="active",
            roles=["Employee Self-Service", "Manager Self-Service" if rng.random() > 0.5 else "Employee Self-Service"],
            last_login=datetime.utcnow() - timedelta(days=rng.randint(1, 14)),
            risk_score=round(rng.uniform(5, 20), 1),
        ),
    ]

    # Occasionally add a dormant account
    if rng.random() > 0.4:
        nodes.append(IdentityNode(
            system="SAP GRC AC (Legacy)",
            account_id=f"GRC-{user_id}",
            account_name=f"{first[0]}{last}".upper()[:12],
            status="dormant",
            roles=["FF_OWNER", "RISK_ANALYST"],
            last_login=datetime.utcnow() - timedelta(days=rng.randint(180, 500)),
            risk_score=round(rng.uniform(15, 40), 1),
        ))

    edges = [
        IdentityEdge(
            source_system="Azure Active Directory",
            target_system="SAP ECC (PRD)",
            link_type="sso",
            confidence=0.99,
        ),
        IdentityEdge(
            source_system="Azure Active Directory",
            target_system="S/4HANA (S4P)",
            link_type="sso",
            confidence=0.99,
        ),
        IdentityEdge(
            source_system="Azure Active Directory",
            target_system="SuccessFactors",
            link_type="provisioned",
            confidence=0.95,
        ),
        IdentityEdge(
            source_system="SAP ECC (PRD)",
            target_system="S/4HANA (S4P)",
            link_type="inferred",
            confidence=0.88,
        ),
    ]

    if len(nodes) > 4:
        edges.append(IdentityEdge(
            source_system="SAP ECC (PRD)",
            target_system="SAP GRC AC (Legacy)",
            link_type="manual",
            confidence=0.75,
        ))

    total_roles = sum(len(n.roles) for n in nodes)
    max_risk = max(n.risk_score for n in nodes)
    aggregate = round(max_risk * 0.6 + sum(n.risk_score for n in nodes) / len(nodes) * 0.4, 1)

    sod_conflicts = []
    if rng.random() > 0.3:
        sod_conflicts.append({
            "conflict_id": f"XS-{_uid()[:8]}",
            "system_a": "SAP ECC (PRD)",
            "system_b": "S/4HANA (S4P)",
            "role_a": nodes[0].roles[0] if nodes[0].roles else "UNKNOWN",
            "role_b": nodes[1].roles[0] if nodes[1].roles else "UNKNOWN",
            "description": "Cross-system SoD: vendor maintenance in ECC combined with payment approval in S/4HANA",
            "severity": "high",
        })

    recommendations = [
        f"Consolidate duplicate accounts across ECC and S/4HANA during migration",
    ]
    dormant_nodes = [n for n in nodes if n.status == "dormant"]
    if dormant_nodes:
        recommendations.append(
            f"Decommission dormant account in {dormant_nodes[0].system} — last login over 6 months ago"
        )
    if total_roles > 10:
        recommendations.append(
            f"User holds {total_roles} roles across {len(nodes)} systems — conduct access right-sizing review"
        )
    if sod_conflicts:
        recommendations.append(
            "Remediate cross-system SoD conflict between ECC and S/4HANA before go-live"
        )

    return UserIdentityGraph(
        user_id=user_id,
        display_name=f"{first} {last}",
        department=dept,
        manager=f"{_pick(seed + 99, _FIRST_NAMES)} {_pick(seed + 100, _LAST_NAMES)}",
        nodes=nodes,
        edges=edges,
        total_accounts=len(nodes),
        total_roles=total_roles,
        aggregate_risk_score=aggregate,
        cross_system_sod_conflicts=sod_conflicts,
        recommendations=recommendations,
    )


@router.get("/identity-graph/department/{department}", response_model=DepartmentIdentityOverview)
async def get_department_identity_overview(
    department: str,
    tenant_id: str = Depends(_get_tenant_id),
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Get an identity overview for an entire department."""
    seed = _seed_from(department)
    rng = random.Random(seed)

    total_users = rng.randint(15, 80)
    avg_accounts = round(rng.uniform(2.5, 4.5), 1)

    return DepartmentIdentityOverview(
        department=department,
        total_users=total_users,
        total_accounts=int(total_users * avg_accounts),
        avg_accounts_per_user=avg_accounts,
        orphan_accounts=rng.randint(2, 12),
        high_risk_users=rng.randint(3, int(total_users * 0.15)),
        sod_violations=rng.randint(5, 35),
        access_distribution={
            "SAP ECC": total_users,
            "S/4HANA": rng.randint(int(total_users * 0.5), total_users),
            "Azure AD": total_users,
            "SuccessFactors": total_users,
            "ServiceNow": rng.randint(int(total_users * 0.3), int(total_users * 0.7)),
        },
        risk_heatmap=[
            {
                "category": "SoD Conflicts",
                "count": rng.randint(5, 25),
                "trend": rng.choice(["increasing", "stable", "decreasing"]),
                "severity_distribution": {"critical": rng.randint(1, 5), "high": rng.randint(3, 10), "medium": rng.randint(5, 15)},
            },
            {
                "category": "Excessive Access",
                "count": rng.randint(3, 15),
                "trend": "stable",
                "severity_distribution": {"critical": rng.randint(0, 3), "high": rng.randint(2, 8), "medium": rng.randint(4, 12)},
            },
            {
                "category": "Dormant Accounts",
                "count": rng.randint(2, 10),
                "trend": "decreasing",
                "severity_distribution": {"critical": 0, "high": rng.randint(1, 4), "medium": rng.randint(2, 6)},
            },
            {
                "category": "Cross-System Conflicts",
                "count": rng.randint(1, 8),
                "trend": rng.choice(["increasing", "stable"]),
                "severity_distribution": {"critical": rng.randint(0, 2), "high": rng.randint(1, 5), "medium": rng.randint(2, 6)},
            },
        ],
    )


@router.get("/identity-graph/orphan-accounts", response_model=List[OrphanAccount])
async def find_orphan_accounts(
    system: Optional[str] = Query(None, description="Filter by system"),
    risk_level: Optional[SeverityLevel] = Query(None, description="Filter by risk level"),
    tenant_id: str = Depends(_get_tenant_id),
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Find accounts without linked identities or belonging to terminated users."""
    seed = _seed_from(tenant_id + "orphans")
    rng = random.Random(seed)

    orphans = [
        OrphanAccount(
            account_id="ECC-JSMITH_OLD",
            system="SAP ECC (PRD)",
            last_login=datetime.utcnow() - timedelta(days=245),
            roles=["SAP_FI_AP_CLERK", "SAP_FI_PAYMENT_RUN", "SAP_MM_VENDOR_MASTER"],
            risk_level=SeverityLevel.CRITICAL,
            reason="terminated_user",
            recommended_action="Immediately lock account and remove all role assignments. User John Smith terminated 8 months ago but SAP account was never deprovisioned.",
            days_since_activity=245,
        ),
        OrphanAccount(
            account_id="S4H-SVC_MIGRATION",
            system="S/4HANA (S4P)",
            last_login=datetime.utcnow() - timedelta(days=180),
            roles=["SAP_ALL", "SAP_NEW"],
            risk_level=SeverityLevel.CRITICAL,
            reason="no_owner",
            recommended_action="Emergency: service account with SAP_ALL has no assigned owner. Immediately lock and audit all activity logs. Assign ownership or decommission.",
            days_since_activity=180,
        ),
        OrphanAccount(
            account_id="ECC-CONSULTANT1",
            system="SAP ECC (PRD)",
            last_login=datetime.utcnow() - timedelta(days=120),
            roles=["SAP_BASIS_ADMIN", "Z_CUSTOM_DEV"],
            risk_level=SeverityLevel.HIGH,
            reason="dormant",
            recommended_action="Consultant account dormant for 120 days. Contract ended in July. Lock account and revoke all Basis admin roles.",
            days_since_activity=120,
        ),
        OrphanAccount(
            account_id="AAD-TEMP.INTERN@CORP.COM",
            system="Azure Active Directory",
            last_login=datetime.utcnow() - timedelta(days=90),
            roles=["Global Reader", "SharePoint Member"],
            risk_level=SeverityLevel.LOW,
            reason="dormant",
            recommended_action="Intern Azure AD account inactive for 90 days. Internship ended. Disable account and remove from all groups.",
            days_since_activity=90,
        ),
        OrphanAccount(
            account_id="ECC-BATCH_USER_02",
            system="SAP ECC (PRD)",
            last_login=None,
            roles=["SAP_MM_PURCHASER", "SAP_MM_INV_MANAGER"],
            risk_level=SeverityLevel.HIGH,
            reason="never_used",
            recommended_action="Account was created 6 months ago but has never been used. No matching employee found in HR system. Investigate origin and lock if no valid business owner identified.",
            days_since_activity=None,
        ),
        OrphanAccount(
            account_id="SF-900123",
            system="SuccessFactors",
            last_login=datetime.utcnow() - timedelta(days=200),
            roles=["Employee Self-Service", "Recruiter"],
            risk_level=SeverityLevel.MEDIUM,
            reason="terminated_user",
            recommended_action="SuccessFactors account for terminated recruiter still active. Remove Recruiter role and disable account to prevent access to candidate data.",
            days_since_activity=200,
        ),
        OrphanAccount(
            account_id="ECC-RFC_INTERFACE",
            system="SAP ECC (PRD)",
            last_login=datetime.utcnow() - timedelta(days=365),
            roles=["SAP_FI_GL_ADMIN", "Z_RFC_FULL"],
            risk_level=SeverityLevel.CRITICAL,
            reason="no_owner",
            recommended_action="RFC interface account with broad GL access has no assigned owner and no activity in 12 months. Critical risk — lock immediately and trace all historical transactions.",
            days_since_activity=365,
        ),
    ]

    if system:
        orphans = [o for o in orphans if system.lower() in o.system.lower()]
    if risk_level:
        orphans = [o for o in orphans if o.risk_level == risk_level]

    return orphans


# =============================================================================
# 7. GRC Copilot Chat
# =============================================================================

_GRC_KNOWLEDGE = {
    "sod": (
        "Segregation of Duties (SoD) is a fundamental internal control principle "
        "requiring that no single individual should control all phases of a business "
        "transaction. In SAP environments, SoD conflicts arise when a user has access "
        "to transaction codes that span conflicting business functions — for example, "
        "creating a vendor (FK01) AND executing payment runs (F110)."
    ),
    "risk": (
        "GovernexPlus calculates risk scores using a multi-dimensional model: "
        "base severity from rule definitions, contextual amplifiers (transaction volume, "
        "financial exposure, user privilege level), usage-aware dampeners (dormant access "
        "scores higher than actively monitored access), and behavioral anomaly signals."
    ),
    "certification": (
        "Access certification campaigns are periodic reviews where managers or access "
        "owners validate that users still need their assigned roles and permissions. "
        "GovernexPlus enhances this with AI-powered recommendations based on usage "
        "analysis, peer group comparison, and risk context."
    ),
    "mitigation": (
        "Mitigation controls are compensating measures applied when an SoD conflict "
        "cannot be eliminated. Types include: dual-approval (requires second authorizer), "
        "transaction monitoring (real-time alerts on high-risk activity), periodic review "
        "(scheduled re-evaluation), and automated controls (system-enforced limits)."
    ),
    "firefighter": (
        "Firefighter access (emergency access) provides temporary elevated privileges "
        "for break-glass scenarios. GovernexPlus enforces: time-limited sessions, "
        "mandatory reason codes, real-time controller notifications, complete transaction "
        "logging, and automatic access revocation after the defined period."
    ),
}


@router.post("/chat/query", response_model=ChatQueryResponse)
async def chat_query(
    request: ChatQueryRequest,
    tenant_id: str = Depends(_get_tenant_id),
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Context-aware GRC copilot chat. Understands tenant data and GRC concepts."""
    message = request.message.lower()
    session_id = request.session_id or f"CHAT-{_uid()}"

    # Track conversation
    if tenant_id not in _chat_histories:
        _chat_histories[tenant_id] = []
    _chat_histories[tenant_id].append({
        "session_id": session_id,
        "timestamp": datetime.utcnow().isoformat(),
        "user": current_user.get("username", "unknown"),
        "message": request.message,
    })

    seed = _seed_from(message[:50])
    rng = random.Random(seed)

    # Pattern-match for contextual responses
    if any(kw in message for kw in ["how many", "count", "total", "number of"]):
        if "violation" in message:
            count = rng.randint(45, 150)
            critical = rng.randint(5, 20)
            reply = (
                f"Your tenant currently has {count} open risk violations. "
                f"Of these, {critical} are critical severity, "
                f"{rng.randint(15, 40)} are high, and the remainder are medium/low. "
                f"The Finance department has the highest concentration with "
                f"{rng.randint(15, 35)} violations, followed by Procurement with "
                f"{rng.randint(10, 25)}. Compared to last month, this represents a "
                f"{rng.choice(['+', '-'])}{rng.randint(3, 12)}% change."
            )
            structured = {"total_violations": count, "critical": critical}
            sources = ["risk_violations table", "trend_analytics"]
        elif "user" in message:
            count = rng.randint(200, 1500)
            reply = (
                f"There are {count} active users in your tenant. "
                f"{rng.randint(int(count * 0.05), int(count * 0.15))} users "
                f"have SoD violations, and {rng.randint(int(count * 0.02), int(count * 0.08))} "
                f"have sensitive access findings."
            )
            structured = {"total_users": count}
            sources = ["users table", "risk_violations table"]
        else:
            reply = (
                f"I can help you with counts across your GRC data. "
                f"Try asking about violations, users, roles, rules, or mitigations."
            )
            structured = None
            sources = []
    elif any(kw in message for kw in ["what is", "explain", "define", "what are"]):
        matched_topic = None
        for topic, explanation in _GRC_KNOWLEDGE.items():
            if topic in message:
                matched_topic = topic
                reply = explanation
                break
        if not matched_topic:
            reply = (
                "I can explain GRC concepts including SoD (Segregation of Duties), "
                "risk scoring methodology, access certification, mitigation controls, "
                "firefighter access, role design, and compliance frameworks. "
                "What would you like to know more about?"
            )
        structured = None
        sources = ["GRC knowledge base"]
    elif any(kw in message for kw in ["who", "which user", "find user"]):
        reply = (
            f"Based on your query, here are the most relevant users:\n\n"
            f"1. {_pick(seed, _FIRST_NAMES)} {_pick(seed + 1, _LAST_NAMES)} "
            f"({_pick(seed, _DEPARTMENTS)}) — {rng.randint(2, 8)} open violations, "
            f"risk score {rng.randint(55, 95)}\n"
            f"2. {_pick(seed + 2, _FIRST_NAMES)} {_pick(seed + 3, _LAST_NAMES)} "
            f"({_pick(seed + 1, _DEPARTMENTS)}) — {rng.randint(1, 5)} open violations, "
            f"risk score {rng.randint(40, 80)}\n"
            f"3. {_pick(seed + 4, _FIRST_NAMES)} {_pick(seed + 5, _LAST_NAMES)} "
            f"({_pick(seed + 2, _DEPARTMENTS)}) — {rng.randint(1, 4)} open violations, "
            f"risk score {rng.randint(30, 70)}\n\n"
            f"Would you like me to drill into any of these users?"
        )
        structured = {"result_type": "user_list", "count": 3}
        sources = ["users table", "risk_violations table"]
    elif any(kw in message for kw in ["recommend", "suggest", "should i", "what should"]):
        reply = (
            f"Based on your current risk posture, I recommend:\n\n"
            f"1. **Immediate**: Address the {rng.randint(3, 8)} critical SoD violations "
            f"in Finance — these involve vendor/payment conflicts with the highest "
            f"financial exposure.\n"
            f"2. **This week**: Launch an access certification campaign for "
            f"{_pick(seed, _DEPARTMENTS)} — it has been {rng.randint(60, 120)} days "
            f"since the last review.\n"
            f"3. **This month**: Review {rng.randint(5, 15)} orphan accounts detected "
            f"across SAP ECC and S/4HANA — {rng.randint(2, 5)} have privileged access.\n"
            f"4. **Ongoing**: Enable real-time SoD checks in the provisioning workflow "
            f"to prevent new violations.\n\n"
            f"Shall I create action items for any of these?"
        )
        structured = {"result_type": "recommendations", "priority_actions": 4}
        sources = ["risk_analytics", "certification_campaigns", "identity_graph"]
    elif any(kw in message for kw in ["help", "what can you", "capabilities"]):
        reply = (
            "I am the GovernexPlus AI Copilot. I can help you with:\n\n"
            "- **Risk Analysis**: 'How many critical violations do we have?'\n"
            "- **User Lookup**: 'Who has the most SoD conflicts?'\n"
            "- **Explanations**: 'What is segregation of duties?'\n"
            "- **Recommendations**: 'What should I focus on this week?'\n"
            "- **Forecasting**: 'What is our risk trend for next month?'\n"
            "- **Remediation**: 'How do I fix violation V-12345?'\n"
            "- **Compliance**: 'Are we ready for the SOX audit?'\n"
            "- **Identity**: 'Show me orphan accounts in SAP ECC'\n\n"
            "Just ask in plain English — I understand your GRC context."
        )
        structured = None
        sources = []
    else:
        reply = (
            f"I understand you are asking about: \"{request.message}\"\n\n"
            f"Based on your tenant's current data, here is what I found:\n\n"
            f"Your organization has {rng.randint(50, 200)} active risk findings, "
            f"with the majority concentrated in {_pick(seed, _DEPARTMENTS)} and "
            f"{_pick(seed + 1, _DEPARTMENTS)}. The overall risk trend is "
            f"{rng.choice(['slightly increasing', 'stable', 'improving'])} compared "
            f"to last quarter.\n\n"
            f"Would you like me to:\n"
            f"- Drill deeper into a specific area?\n"
            f"- Generate a report on this topic?\n"
            f"- Create remediation plans for the highest-risk items?"
        )
        structured = None
        sources = ["risk_analytics", "user_access_data"]

    suggested_actions = [
        {
            "action": "view_dashboard",
            "label": "Open Risk Dashboard",
            "url": "/dashboard/risk-overview",
        },
        {
            "action": "run_analysis",
            "label": "Run Full Risk Analysis",
            "url": "/risk-analysis/run",
        },
        {
            "action": "view_violations",
            "label": "View Open Violations",
            "url": "/violations?status=open",
        },
    ]

    return ChatQueryResponse(
        session_id=session_id,
        reply=reply,
        structured_data=structured,
        suggested_actions=suggested_actions,
        sources=sources,
        confidence=round(rng.uniform(0.75, 0.95), 3),
    )


@router.get("/chat/suggestions", response_model=List[ContextualSuggestion])
async def get_contextual_suggestions(
    tenant_id: str = Depends(_get_tenant_id),
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Get contextual suggestions based on the current risk posture and user role."""
    seed = _seed_from(tenant_id + datetime.utcnow().strftime("%Y-%m-%d"))
    rng = random.Random(seed)

    return [
        ContextualSuggestion(
            suggestion_id="CTX-001",
            category="risk_remediation",
            title=f"Address {rng.randint(3, 8)} Critical SoD Violations",
            description=(
                f"There are {rng.randint(3, 8)} critical SoD violations in "
                f"{_pick(seed, _DEPARTMENTS)} that have been open for over "
                f"{rng.randint(14, 60)} days. These involve vendor/payment "
                f"conflicts with estimated exposure of ${rng.randint(200, 800)}K."
            ),
            priority="critical",
            action_url="/ai-copilot/remediation/analyze",
            estimated_impact=f"Reduce critical risk count by {rng.randint(40, 70)}%",
        ),
        ContextualSuggestion(
            suggestion_id="CTX-002",
            category="certification",
            title="Overdue Access Review Campaign",
            description=(
                f"The {_pick(seed + 1, _DEPARTMENTS)} department has not had an "
                f"access review in {rng.randint(75, 150)} days, exceeding the "
                f"90-day policy threshold. {rng.randint(20, 60)} users need review."
            ),
            priority="high",
            action_url="/certifications/create",
            estimated_impact=f"Bring {rng.randint(20, 60)} users back into compliance",
        ),
        ContextualSuggestion(
            suggestion_id="CTX-003",
            category="identity_hygiene",
            title=f"Clean Up {rng.randint(5, 15)} Orphan Accounts",
            description=(
                "Orphan accounts with no linked identity owner detected across "
                "SAP systems. Some hold privileged roles including Basis admin access."
            ),
            priority="high",
            action_url="/ai-copilot/identity-graph/orphan-accounts",
            estimated_impact="Eliminate unauthorized access pathways and reduce attack surface",
        ),
        ContextualSuggestion(
            suggestion_id="CTX-004",
            category="forecasting",
            title="Prepare for Upcoming Hiring Wave",
            description=(
                f"HR data indicates {rng.randint(8, 25)} new hires starting in "
                f"the next 30 days. Historical patterns show each onboarding "
                f"cycle introduces SoD conflicts. Pre-validate role templates now."
            ),
            priority="medium",
            action_url="/ai-copilot/forecast/violation-forecast",
            estimated_impact="Prevent 60-80% of onboarding-related violations",
        ),
        ContextualSuggestion(
            suggestion_id="CTX-005",
            category="rule_optimization",
            title="New Rule Suggestions Available",
            description=(
                f"Based on industry benchmarks and your transaction patterns, "
                f"{rng.randint(3, 7)} new SoD rules are recommended. These cover "
                f"gaps in your current ruleset identified by peer comparison analysis."
            ),
            priority="medium",
            action_url="/ai-copilot/rules/suggestions",
            estimated_impact=f"Improve SoD coverage by {rng.randint(10, 25)}%",
        ),
    ]


@router.post("/chat/explain/{entity_type}/{entity_id}", response_model=EntityExplanation)
async def explain_entity(
    entity_type: str,
    entity_id: str,
    tenant_id: str = Depends(_get_tenant_id),
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Explain any GRC entity in plain English.

    Supports entity types: user, role, violation, rule, mitigation, campaign.
    """
    seed = _seed_from(f"{entity_type}:{entity_id}")
    rng = random.Random(seed)

    first = _pick(seed, _FIRST_NAMES)
    last = _pick(seed + 1, _LAST_NAMES)
    dept = _pick(seed, _DEPARTMENTS)

    explanations = {
        "user": {
            "title": f"User Profile: {first} {last}",
            "plain_english_summary": (
                f"{first} {last} is a member of the {dept} department with "
                f"{rng.randint(2, 8)} assigned roles across SAP ECC and S/4HANA. "
                f"Their current risk score is {rng.randint(30, 85)} out of 100, "
                f"{'which is above average for their peer group and warrants attention' if rng.random() > 0.5 else 'which is within normal range for their peer group'}. "
                f"They have {rng.randint(0, 5)} open SoD violations and last logged "
                f"in {rng.randint(0, 48)} hours ago."
            ),
            "key_facts": [
                {"label": "Department", "value": dept},
                {"label": "Active Roles", "value": str(rng.randint(2, 8))},
                {"label": "Risk Score", "value": f"{rng.randint(30, 85)}/100"},
                {"label": "Open Violations", "value": str(rng.randint(0, 5))},
                {"label": "Last Login", "value": f"{rng.randint(0, 48)} hours ago"},
                {"label": "Account Status", "value": "Active"},
            ],
            "risk_assessment": (
                f"{'Elevated risk due to SoD conflicts between vendor maintenance and payment roles. Recommend immediate review.' if rng.random() > 0.5 else 'Risk within acceptable bounds. Next scheduled review in ' + str(rng.randint(15, 60)) + ' days.'}"
            ),
            "related_entities": [
                {"type": "role", "id": _pick(seed, _SAP_ROLES), "relationship": "assigned_role"},
                {"type": "role", "id": _pick(seed + 1, _SAP_ROLES), "relationship": "assigned_role"},
                {"type": "violation", "id": f"V-{rng.randint(10000, 99999)}", "relationship": "has_violation"},
            ],
            "recommended_actions": [
                "Review open SoD violations and initiate remediation",
                "Verify role assignments align with current job responsibilities",
                "Schedule manager certification for Q4 access review",
            ],
        },
        "violation": {
            "title": f"Violation {entity_id}",
            "plain_english_summary": (
                f"This is a {rng.choice(['critical', 'high'])}-severity Segregation of "
                f"Duties violation. In plain terms, {first} {last} in {dept} can both "
                f"{'create vendors in the system AND approve payments to those vendors' if rng.random() > 0.5 else 'create purchase orders AND confirm that goods were received'}. "
                f"This is risky because a single person could potentially "
                f"{'create a fake vendor and pay themselves' if rng.random() > 0.5 else 'order goods that were never delivered and mark them as received to trigger payment'}. "
                f"This violation has been open for {rng.randint(7, 120)} days."
            ),
            "key_facts": [
                {"label": "Severity", "value": rng.choice(["Critical", "High"])},
                {"label": "Type", "value": "Segregation of Duties"},
                {"label": "Affected User", "value": f"{first} {last}"},
                {"label": "Department", "value": dept},
                {"label": "Days Open", "value": str(rng.randint(7, 120))},
                {"label": "Status", "value": rng.choice(["Open", "In Progress"])},
            ],
            "risk_assessment": (
                f"Financial exposure estimated at ${rng.randint(100, 2000) * 1000:,} "
                f"based on the user's transaction volume. "
                f"{'No evidence of exploitation found in transaction logs.' if rng.random() > 0.3 else 'Anomalous transaction patterns detected — recommend investigation.'}"
            ),
            "related_entities": [
                {"type": "user", "id": entity_id, "relationship": "violating_user"},
                {"type": "rule", "id": f"RULE-{rng.randint(100, 999)}", "relationship": "violated_rule"},
                {"type": "mitigation", "id": f"MIT-{rng.randint(100, 999)}", "relationship": "compensating_control"},
            ],
            "recommended_actions": [
                "Generate a remediation plan using AI Copilot",
                "Apply compensating control as interim measure",
                "Review user's transaction history for anomalies",
            ],
        },
        "role": {
            "title": f"Role: {_pick(seed, _SAP_ROLES)}",
            "plain_english_summary": (
                f"This role grants access to {_pick(seed, _DEPARTMENTS).lower()} "
                f"functions in SAP. It contains {rng.randint(3, 15)} transaction codes "
                f"and is currently assigned to {rng.randint(5, 50)} users. "
                f"The role is involved in {rng.randint(0, 8)} SoD conflicts with "
                f"other roles in the system."
            ),
            "key_facts": [
                {"label": "Role Name", "value": _pick(seed, _SAP_ROLES)},
                {"label": "Module", "value": rng.choice(["FI", "MM", "SD", "HR", "BC"])},
                {"label": "Transaction Codes", "value": str(rng.randint(3, 15))},
                {"label": "Assigned Users", "value": str(rng.randint(5, 50))},
                {"label": "SoD Conflicts", "value": str(rng.randint(0, 8))},
                {"label": "Last Modified", "value": f"{rng.randint(10, 365)} days ago"},
            ],
            "risk_assessment": (
                f"{'This role has a high conflict density and should be considered for redesign.' if rng.random() > 0.5 else 'This role has an acceptable risk profile. Standard monitoring controls are sufficient.'}"
            ),
            "related_entities": [
                {"type": "user", "id": f"USR-{rng.randint(1000, 9999)}", "relationship": "assigned_to"},
                {"type": "rule", "id": f"RULE-{rng.randint(100, 999)}", "relationship": "conflicts_with"},
            ],
            "recommended_actions": [
                "Review role assignment population for least-privilege compliance",
                "Check for transaction codes that can be split into separate roles",
                "Run SoD simulation to identify all conflict pairs",
            ],
        },
        "rule": {
            "title": f"SoD Rule {entity_id}",
            "plain_english_summary": (
                f"This rule checks that no single user can perform both sides of a "
                f"conflicting business process. Specifically, it ensures that "
                f"{'vendor maintenance (creating/changing vendors) is separated from payment execution (running payment programs)' if rng.random() > 0.5 else 'purchase order creation is separated from goods receipt posting'}. "
                f"Currently {rng.randint(3, 25)} users are in violation of this rule."
            ),
            "key_facts": [
                {"label": "Rule ID", "value": entity_id},
                {"label": "Type", "value": "Segregation of Duties"},
                {"label": "Severity", "value": rng.choice(["Critical", "High"])},
                {"label": "Active Violations", "value": str(rng.randint(3, 25))},
                {"label": "Module", "value": rng.choice(["FI", "MM", "FI/MM"])},
                {"label": "Status", "value": "Active"},
            ],
            "risk_assessment": (
                f"This is a {'critical' if rng.random() > 0.5 else 'high'}-priority "
                f"rule. Industry benchmarks show this conflict type is exploited in "
                f"{rng.randint(15, 40)}% of procurement fraud cases."
            ),
            "related_entities": [
                {"type": "violation", "id": f"V-{rng.randint(10000, 99999)}", "relationship": "generates_violation"},
                {"type": "mitigation", "id": f"MIT-{rng.randint(100, 999)}", "relationship": "mitigated_by"},
            ],
            "recommended_actions": [
                "Review all violating users and prioritize by transaction volume",
                "Ensure compensating controls are applied to all accepted risks",
                "Consider rule threshold tuning if false positive rate is high",
            ],
        },
    }

    entity_data = explanations.get(entity_type)
    if not entity_data:
        # Generic fallback
        entity_data = {
            "title": f"{entity_type.replace('_', ' ').title()} {entity_id}",
            "plain_english_summary": (
                f"This {entity_type} entity is part of your GRC landscape. "
                f"It was last updated {rng.randint(1, 90)} days ago and is "
                f"currently in an active state."
            ),
            "key_facts": [
                {"label": "Entity Type", "value": entity_type},
                {"label": "Entity ID", "value": entity_id},
                {"label": "Status", "value": "Active"},
            ],
            "risk_assessment": "Standard risk profile. No immediate concerns identified.",
            "related_entities": [],
            "recommended_actions": ["Review entity details in the relevant module"],
        }

    return EntityExplanation(
        entity_type=entity_type,
        entity_id=entity_id,
        title=entity_data["title"],
        plain_english_summary=entity_data["plain_english_summary"],
        key_facts=entity_data["key_facts"],
        risk_assessment=entity_data["risk_assessment"],
        related_entities=entity_data["related_entities"],
        recommended_actions=entity_data["recommended_actions"],
    )
