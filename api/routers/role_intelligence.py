"""
Role Intelligence API Router

Endpoints for analysing the SAP role estate: duplication detection, usage
analytics, consolidation planning, health scoring, and naming convention
enforcement.

All endpoints are read-only analysis operations except POST /analyze, which
runs the full analysis pipeline in a single call.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional

from core.role_intelligence import RoleIntelligenceEngine

router = APIRouter(tags=["Role Intelligence"])

# Per-tenant engine registry
_engines: Dict[str, RoleIntelligenceEngine] = {}


def _get_tenant_id() -> str:
    from core.tenant import get_current_tenant
    ctx = get_current_tenant()
    return ctx.tenant_id if ctx else "default"


def _get_engine(tenant_id: str = Depends(_get_tenant_id)) -> RoleIntelligenceEngine:
    if tenant_id not in _engines:
        _engines[tenant_id] = RoleIntelligenceEngine(tenant_id=tenant_id)
    return _engines[tenant_id]


# =============================================================================
# Request / Response models
# =============================================================================

class AnalyzeRequest(BaseModel):
    duplicate_threshold: float = Field(
        default=0.80,
        ge=0.0,
        le=1.0,
        description="Similarity threshold (0.0-1.0) for duplicate detection.",
    )
    consolidation_threshold: float = Field(
        default=0.70,
        ge=0.0,
        le=1.0,
        description="Similarity threshold (0.0-1.0) for consolidation grouping.",
    )
    stale_days: int = Field(
        default=90,
        ge=1,
        description="Number of days without use before a role is considered stale.",
    )


# =============================================================================
# Endpoints
# =============================================================================

@router.get("/overview")
async def get_overview(engine: RoleIntelligenceEngine = Depends(_get_engine)) -> Dict[str, Any]:
    """
    Return a high-level summary of the role estate.

    Includes total role count, average health score, grade distribution,
    roles by business process and type, unused role count, ownership rate,
    and SoD conflict count. This endpoint is fast — it does not run the
    full duplicate or consolidation analysis.
    """
    return engine.get_overview()


@router.get("/duplicates")
async def get_duplicates(
    threshold: float = Query(
        default=0.80,
        ge=0.0,
        le=1.0,
        description="Minimum similarity score (0.0-1.0) to flag two roles as duplicates.",
    ),
    engine: RoleIntelligenceEngine = Depends(_get_engine),
) -> Dict[str, Any]:
    """
    Find duplicate and near-duplicate roles in the estate.

    Groups roles where pairwise similarity exceeds the threshold. Each
    group identifies the recommended canonical role to retain and lists
    the retirement candidates. Uses a weighted Jaccard similarity across
    transactions (50%), auth objects (35%), and org values (15%).
    """
    groups = engine.find_duplicates(threshold=threshold)
    return {
        "threshold_pct": round(threshold * 100, 1),
        "duplicate_group_count": len(groups),
        "total_retirement_candidates": sum(len(g.retirement_candidates) for g in groups),
        "groups": [g.to_dict() for g in groups],
    }


@router.get("/unused")
async def get_unused_roles(
    stale_days: int = Query(
        default=90,
        ge=1,
        description="Roles last used more than this many days ago are flagged as stale.",
    ),
    engine: RoleIntelligenceEngine = Depends(_get_engine),
) -> Dict[str, Any]:
    """
    List roles that are unused or stale, with retirement recommendations.

    Unused roles have zero assigned users. Stale roles have not been used
    within the configured stale_days window. Low-usage roles (1-2 users)
    are surfaced separately as consolidation candidates.
    """
    report = engine.get_usage_stats(stale_days=stale_days)
    return report.to_dict()


@router.get("/similarity/{role_a}/{role_b}")
async def get_similarity(
    role_a: str,
    role_b: str,
    engine: RoleIntelligenceEngine = Depends(_get_engine),
) -> Dict[str, Any]:
    """
    Compare two specific roles and return a detailed similarity breakdown.

    Scores are returned as percentages (0-100). The response includes the
    shared and unique transaction codes, shared auth objects, and a plain-
    English recommendation on whether consolidation is warranted.

    Path parameters are role IDs (e.g. R001, R002).
    """
    try:
        result = engine.analyze_similarity(role_a, role_b)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return result.to_dict()


@router.get("/consolidation")
async def get_consolidation_plan(
    threshold: float = Query(
        default=0.70,
        ge=0.0,
        le=1.0,
        description="Minimum similarity score (0.0-1.0) to include a role pair in consolidation planning.",
    ),
    engine: RoleIntelligenceEngine = Depends(_get_engine),
) -> Dict[str, Any]:
    """
    Generate a consolidation plan for the role estate.

    Groups similar roles, proposes a canonical merged name, estimates the
    effort in person-days, scores the risk (low / medium / high), and
    provides step-by-step merge instructions. High-priority groups are
    surfaced separately — these are low-risk groups where immediate action
    is recommended.
    """
    plan = engine.recommend_consolidation(threshold=threshold)
    return plan.to_dict()


@router.get("/health")
async def get_all_health_scores(
    min_score: Optional[int] = Query(
        default=None,
        ge=0,
        le=100,
        description="Filter to roles with health score at or above this value.",
    ),
    max_score: Optional[int] = Query(
        default=None,
        ge=0,
        le=100,
        description="Filter to roles with health score at or below this value.",
    ),
    grade: Optional[str] = Query(
        default=None,
        description="Filter by health grade: A, B, C, D, or F.",
    ),
    engine: RoleIntelligenceEngine = Depends(_get_engine),
) -> Dict[str, Any]:
    """
    Return health scores for all roles in the estate.

    Roles are sorted by overall score ascending (worst first) to prioritise
    remediation effort. Scores are calculated across six dimensions: owner
    presence (20 pts), description quality (15 pts), SoD conflicts (25 pts),
    user count (10 pts), recent usage (20 pts), and naming convention (10 pts).

    Optional filters: min_score, max_score, grade (A/B/C/D/F).
    """
    scores = engine.calculate_health_all()

    if min_score is not None:
        scores = [s for s in scores if s.overall_score >= min_score]
    if max_score is not None:
        scores = [s for s in scores if s.overall_score <= max_score]
    if grade is not None:
        grade_upper = grade.upper()
        if grade_upper not in ("A", "B", "C", "D", "F"):
            raise HTTPException(status_code=400, detail="Grade must be one of A, B, C, D, F.")
        scores = [s for s in scores if s.grade == grade_upper]

    avg = sum(s.overall_score for s in scores) / len(scores) if scores else 0
    grade_dist: Dict[str, int] = {"A": 0, "B": 0, "C": 0, "D": 0, "F": 0}
    for s in scores:
        grade_dist[s.grade] = grade_dist.get(s.grade, 0) + 1

    return {
        "total_returned": len(scores),
        "average_score": round(avg, 1),
        "grade_distribution": grade_dist,
        "roles": [s.to_dict() for s in scores],
    }


@router.get("/health/{role_id}")
async def get_role_health(
    role_id: str,
    engine: RoleIntelligenceEngine = Depends(_get_engine),
) -> Dict[str, Any]:
    """
    Return the health score for a single role.

    Provides a per-dimension breakdown, a list of specific issues found,
    and actionable recommendations for each issue. Role IDs follow the
    format used by the role catalogue (e.g. R001, R042).
    """
    try:
        score = engine.calculate_health(role_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return score.to_dict()


@router.get("/naming-issues")
async def get_naming_issues(
    issue_type: Optional[str] = Query(
        default=None,
        description="Filter by issue type: 'pattern_mismatch' or 'antipattern'.",
    ),
    engine: RoleIntelligenceEngine = Depends(_get_engine),
) -> Dict[str, Any]:
    """
    Return all roles that violate the SAP role naming convention.

    The standard convention requires:
    - Single roles:    Z_<PROCESS>_<FUNCTION>[_<DETAIL>] (all uppercase)
    - Composite roles: ZC_<PROCESS>_<FUNCTION>[_<DETAIL>] (all uppercase)

    Anti-pattern tokens that are always flagged include: TEMP, OLD, COPY,
    TEST, BACKUP, FINAL, NEW, and trailing digits (e.g. V2, FINAL2).

    Each issue includes a suggested corrected name.
    """
    report = engine.analyze_naming()
    result = report.to_dict()

    if issue_type:
        result["issues"] = [
            i for i in result["issues"] if i["issue_type"] == issue_type
        ]
        result["non_compliant_count"] = len(result["issues"])

    return result


@router.post("/analyze")
async def run_full_analysis(
    request: AnalyzeRequest,
    engine: RoleIntelligenceEngine = Depends(_get_engine),
) -> Dict[str, Any]:
    """
    Run the complete Role Intelligence analysis pipeline.

    Executes all six analysis modules in a single call:
    1. Usage analytics (unused, stale, low-usage roles)
    2. Duplicate detection at the specified threshold
    3. Consolidation planning at the specified threshold
    4. Health scoring for all roles
    5. Naming convention analysis
    6. Estate overview summary

    Returns a unified result object with a top-level summary and the full
    output of each module. Use this endpoint to power a full role estate
    review report.
    """
    # Run the full analysis pipeline for this tenant's engine
    result = engine.run_full_analysis()

    # Re-run usage with caller-supplied stale_days
    usage = engine.get_usage_stats(stale_days=request.stale_days)
    result["usage"] = usage.to_dict()

    # Re-run duplicates with caller-supplied threshold
    duplicates = engine.find_duplicates(threshold=request.duplicate_threshold)
    result["duplicates"] = [d.to_dict() for d in duplicates]

    # Re-run consolidation with caller-supplied threshold
    consolidation = engine.recommend_consolidation(threshold=request.consolidation_threshold)
    result["consolidation"] = consolidation.to_dict()

    # Update summary to reflect caller parameters
    result["summary"]["duplicate_groups"] = len(duplicates)
    result["summary"]["unused_roles"] = len(usage.unused_roles)
    result["summary"]["stale_roles"] = len(usage.stale_roles)
    result["summary"]["roles_saveable_via_consolidation"] = consolidation.total_roles_saveable
    result["parameters_used"] = {
        "duplicate_threshold_pct": round(request.duplicate_threshold * 100, 1),
        "consolidation_threshold_pct": round(request.consolidation_threshold * 100, 1),
        "stale_days": request.stale_days,
    }

    return result
