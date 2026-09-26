"""
GRC AI Assistant API Router

Prefix: /ai/grc

Exposes all GRCAssistant capabilities as REST endpoints with:
  - Per-tenant engine registry (Dict[tenant_id, GRCAssistant])
  - JWT authentication via shared get_current_user dependency
  - Graceful error handling — always returns a response (template fallback
    if the LLM call fails)
  - Pydantic request/response models for clean OpenAPI documentation

Modules covered:
  RM  — Risk Management (risk description, assessment, KRI thresholds, executive summary)
  PC  — Policy & Controls (control suggestion)
  AM  — Audit Management (finding write-up, audit focus areas, management response)
  AC  — Access Control (SoD remediation)
  NL  — Natural Language GRC Query (cross-module)
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from api.dependencies import get_current_user
from core.ai.grc_assistant import GRCAssistant
from db.database import get_db
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/ai/grc",
    tags=["GRC AI Assistant"],
)

# ---------------------------------------------------------------------------
# Per-tenant assistant registry
# ---------------------------------------------------------------------------

_assistants: Dict[str, GRCAssistant] = {}


def _get_tenant_id() -> str:
    from core.tenant import get_current_tenant
    ctx = get_current_tenant()
    return ctx.tenant_id if ctx else "default"


def _get_assistant(
    tenant_id: str = Depends(_get_tenant_id),
    db: Session = Depends(get_db),
) -> GRCAssistant:
    """Return (or lazily create) the GRCAssistant for this tenant."""
    if tenant_id not in _assistants:
        _assistants[tenant_id] = GRCAssistant(tenant_id=tenant_id, db_session=db)
    return _assistants[tenant_id]


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

# ---- RM: Risk Description ----

class DraftRiskDescriptionRequest(BaseModel):
    title: str = Field(..., description="Short risk title as it would appear in the risk register.")
    category: str = Field(..., description="Risk category (e.g. Financial, Operational, Access, Compliance).")
    context: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional extra context: department, system, regulatory driver, etc.",
    )


class DraftRiskDescriptionResponse(BaseModel):
    description: str
    description_ar: str
    suggested_likelihood: int = Field(..., ge=1, le=5)
    suggested_impact: int = Field(..., ge=1, le=5)
    suggested_category: str


# ---- PC: Control Suggestion ----

class SuggestControlsRequest(BaseModel):
    risk_description: str = Field(..., description="Full description of the risk to be controlled.")
    risk_category: str = Field(..., description="Risk category to guide control selection.")


class ControlItem(BaseModel):
    control_name: str
    objective: str
    control_type: str = Field(..., description="preventive | detective | corrective")
    control_nature: str = Field(..., description="manual | automated | hybrid")
    frequency: str
    rationale: str


# ---- AM: Finding Write-Up ----

class DraftFindingRequest(BaseModel):
    condition_notes: str = Field(
        ...,
        description="Raw field notes describing the condition observed during audit work.",
    )
    audit_area: str = Field(..., description="Audit area or process being reviewed (e.g. 'Accounts Payable').")
    context: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional extra context: entity name, audit period, materiality threshold, etc.",
    )


class DraftFindingResponse(BaseModel):
    title: str
    condition: str
    criteria: str
    cause: str
    effect: str
    recommendation: str
    severity: str = Field(..., description="high | medium | low")


# ---- AC: SoD Remediation ----

class RecommendRemediationRequest(BaseModel):
    violation: Dict[str, Any] = Field(
        ...,
        description=(
            "SoD violation dict. Expected keys: rule_name, user_id, conflicting_roles, "
            "conflicting_functions, severity, business_justification."
        ),
    )


class RemediationResponse(BaseModel):
    recommendations: List[str]
    risk_reduction_estimate: str
    implementation_effort: str = Field(..., description="low | medium | high")
    mitigation_control_suggestion: str


# ---- RM: Risk Assessment Assistance ----

class AssistAssessmentRequest(BaseModel):
    risk: Dict[str, Any] = Field(
        ...,
        description="Risk record dict. Expected keys: title, category, likelihood, impact.",
    )
    historical_data: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional historical data: occurrences_last_2_years, etc.",
    )


class AssistAssessmentResponse(BaseModel):
    suggested_likelihood: int = Field(..., ge=1, le=5)
    suggested_impact: int = Field(..., ge=1, le=5)
    rationale: str
    comparable_risks: List[str]
    industry_benchmarks: str


# ---- AM: Audit Focus Areas ----

class SuggestAuditFocusRequest(BaseModel):
    entity: Dict[str, Any] = Field(
        ...,
        description="Entity being audited. Expected keys: name, type, industry.",
    )
    risk_data: Dict[str, Any] = Field(
        ...,
        description="Current risk profile: high_risk_areas, violation_counts, etc.",
    )
    control_data: Dict[str, Any] = Field(
        ...,
        description="Current control environment: weak_controls, maturity_level, etc.",
    )


class AuditFocusArea(BaseModel):
    area: str
    risk_rationale: str
    suggested_procedures: List[str]
    estimated_hours: int


# ---- AM: Management Response ----

class DraftManagementResponseRequest(BaseModel):
    finding: Dict[str, Any] = Field(
        ...,
        description="Audit finding dict. Expected keys: title, condition, recommendation, severity.",
    )


class ManagementResponseResult(BaseModel):
    response: str
    proposed_actions: List[str]
    suggested_timeline: str


# ---- RM: KRI Thresholds ----

class SuggestKRIThresholdsRequest(BaseModel):
    kri_name: str = Field(..., description="Name of the Key Risk Indicator.")
    historical_values: List[float] = Field(
        ...,
        min_items=1,
        description="Historical KRI measurements (ordered oldest to newest).",
    )


class KRIThresholdsResponse(BaseModel):
    threshold_green: float
    threshold_amber: float
    threshold_red: float
    methodology: str


# ---- RM/PC/AM/AC: Executive Summary ----

class GenerateSummaryRequest(BaseModel):
    module: str = Field(
        ...,
        description="GRC module abbreviation: rm | pc | am | ac (or descriptive names).",
    )
    data: Dict[str, Any] = Field(
        ...,
        description=(
            "Module-specific data dict containing KPIs, counts, and status information "
            "to be reflected in the summary."
        ),
    )


class ExecutiveSummaryResponse(BaseModel):
    summary: str
    summary_ar: str
    key_findings: List[str]
    recommendations: List[str]


# ---- NL: GRC Data Query ----

class GRCQueryRequest(BaseModel):
    question: str = Field(..., description="Natural language question about GRC data.")
    context: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional GRC data context to ground the answer.",
    )


class GRCQueryResponse(BaseModel):
    answer: str
    data_sources: List[str]
    confidence: float = Field(..., ge=0.0, le=1.0)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/draft-risk-description",
    response_model=DraftRiskDescriptionResponse,
    summary="Draft Risk Description (RM)",
    description=(
        "Generate a professional risk register description for a given risk title and category. "
        "Includes an Arabic translation and suggested likelihood / impact scores."
    ),
)
async def draft_risk_description(
    body: DraftRiskDescriptionRequest,
    assistant: GRCAssistant = Depends(_get_assistant),
    _current_user: Dict = Depends(get_current_user),
) -> DraftRiskDescriptionResponse:
    try:
        result = assistant.draft_risk_description(
            risk_title=body.title,
            category=body.category,
            context=body.context,
        )
        return DraftRiskDescriptionResponse(**result)
    except Exception as exc:
        logger.exception("draft_risk_description failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to draft risk description.")


@router.post(
    "/suggest-controls",
    response_model=List[ControlItem],
    summary="Suggest Controls for Risk (PC)",
    description=(
        "Suggest appropriate internal controls (preventive, detective, corrective) "
        "for a given risk description and category."
    ),
)
async def suggest_controls(
    body: SuggestControlsRequest,
    assistant: GRCAssistant = Depends(_get_assistant),
    _current_user: Dict = Depends(get_current_user),
) -> List[ControlItem]:
    try:
        controls = assistant.suggest_controls_for_risk(
            risk_description=body.risk_description,
            risk_category=body.risk_category,
        )
        return [ControlItem(**c) for c in controls]
    except Exception as exc:
        logger.exception("suggest_controls failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to suggest controls.")


@router.post(
    "/draft-finding",
    response_model=DraftFindingResponse,
    summary="Draft Audit Finding — CCCE Structure (AM)",
    description=(
        "Transform rough field notes into a professionally structured audit finding "
        "using the Condition / Criteria / Cause / Effect (CCCE) framework."
    ),
)
async def draft_finding(
    body: DraftFindingRequest,
    assistant: GRCAssistant = Depends(_get_assistant),
    _current_user: Dict = Depends(get_current_user),
) -> DraftFindingResponse:
    try:
        result = assistant.draft_finding(
            condition_notes=body.condition_notes,
            audit_area=body.audit_area,
            context=body.context,
        )
        return DraftFindingResponse(**result)
    except Exception as exc:
        logger.exception("draft_finding failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to draft finding.")


@router.post(
    "/recommend-remediation",
    response_model=RemediationResponse,
    summary="Recommend SoD Remediation (AC)",
    description=(
        "Provide prioritised, actionable remediation recommendations for a Segregation "
        "of Duties violation, including risk reduction estimates and mitigation control guidance."
    ),
)
async def recommend_remediation(
    body: RecommendRemediationRequest,
    assistant: GRCAssistant = Depends(_get_assistant),
    _current_user: Dict = Depends(get_current_user),
) -> RemediationResponse:
    try:
        result = assistant.recommend_sod_remediation(violation=body.violation)
        return RemediationResponse(**result)
    except Exception as exc:
        logger.exception("recommend_remediation failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to recommend remediation.")


@router.post(
    "/assist-assessment",
    response_model=AssistAssessmentResponse,
    summary="Assist Risk Assessment (RM)",
    description=(
        "Suggest calibrated likelihood and impact scores for a risk record, "
        "with rationale, comparable risks, and industry benchmarks."
    ),
)
async def assist_assessment(
    body: AssistAssessmentRequest,
    assistant: GRCAssistant = Depends(_get_assistant),
    _current_user: Dict = Depends(get_current_user),
) -> AssistAssessmentResponse:
    try:
        result = assistant.assist_risk_assessment(
            risk=body.risk,
            historical_data=body.historical_data,
        )
        return AssistAssessmentResponse(**result)
    except Exception as exc:
        logger.exception("assist_assessment failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to assist risk assessment.")


@router.post(
    "/suggest-audit-focus",
    response_model=List[AuditFocusArea],
    summary="Suggest Audit Focus Areas (AM)",
    description=(
        "Generate risk-based audit focus areas for planning purposes, "
        "with suggested procedures and estimated hours for each area."
    ),
)
async def suggest_audit_focus(
    body: SuggestAuditFocusRequest,
    assistant: GRCAssistant = Depends(_get_assistant),
    _current_user: Dict = Depends(get_current_user),
) -> List[AuditFocusArea]:
    try:
        areas = assistant.suggest_audit_focus_areas(
            entity=body.entity,
            risk_data=body.risk_data,
            control_data=body.control_data,
        )
        return [AuditFocusArea(**a) for a in areas]
    except Exception as exc:
        logger.exception("suggest_audit_focus failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to suggest audit focus areas.")


@router.post(
    "/draft-management-response",
    response_model=ManagementResponseResult,
    summary="Draft Management Response (AM)",
    description=(
        "Generate a formal, constructive management response to an audit finding, "
        "including proposed remediation actions and a suggested timeline."
    ),
)
async def draft_management_response(
    body: DraftManagementResponseRequest,
    assistant: GRCAssistant = Depends(_get_assistant),
    _current_user: Dict = Depends(get_current_user),
) -> ManagementResponseResult:
    try:
        result = assistant.draft_management_response(finding=body.finding)
        return ManagementResponseResult(**result)
    except Exception as exc:
        logger.exception("draft_management_response failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to draft management response.")


@router.post(
    "/suggest-kri-thresholds",
    response_model=KRIThresholdsResponse,
    summary="Suggest KRI Thresholds (RM)",
    description=(
        "Derive statistically calibrated green / amber / red thresholds for a Key Risk "
        "Indicator from its historical time series, with full methodology explanation."
    ),
)
async def suggest_kri_thresholds(
    body: SuggestKRIThresholdsRequest,
    assistant: GRCAssistant = Depends(_get_assistant),
    _current_user: Dict = Depends(get_current_user),
) -> KRIThresholdsResponse:
    try:
        result = assistant.suggest_kri_thresholds(
            kri_name=body.kri_name,
            historical_values=body.historical_values,
        )
        return KRIThresholdsResponse(**result)
    except Exception as exc:
        logger.exception("suggest_kri_thresholds failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to suggest KRI thresholds.")


@router.post(
    "/generate-summary",
    response_model=ExecutiveSummaryResponse,
    summary="Generate Executive Summary (RM / PC / AM / AC)",
    description=(
        "Produce a board-level executive summary for any GRC module, "
        "including an Arabic translation, key findings, and strategic recommendations."
    ),
)
async def generate_summary(
    body: GenerateSummaryRequest,
    assistant: GRCAssistant = Depends(_get_assistant),
    _current_user: Dict = Depends(get_current_user),
) -> ExecutiveSummaryResponse:
    try:
        result = assistant.generate_executive_summary(
            module=body.module,
            data=body.data,
        )
        return ExecutiveSummaryResponse(**result)
    except Exception as exc:
        logger.exception("generate_summary failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to generate executive summary.")


@router.post(
    "/query",
    response_model=GRCQueryResponse,
    summary="Natural Language GRC Data Query",
    description=(
        "Answer natural language questions about GRC data. "
        "Provide optional context to ground the answer in actual platform data. "
        "Returns a confidence score — lower scores indicate the LLM or template "
        "had limited context to work from."
    ),
)
async def query_grc_data(
    body: GRCQueryRequest,
    assistant: GRCAssistant = Depends(_get_assistant),
    _current_user: Dict = Depends(get_current_user),
) -> GRCQueryResponse:
    try:
        result = assistant.query_grc_data(
            question=body.question,
            context=body.context,
        )
        return GRCQueryResponse(**result)
    except Exception as exc:
        logger.exception("query_grc_data failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to process GRC data query.")
