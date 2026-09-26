"""
Identity Correlation API Router

Exposes endpoints for mapping and correlating identities across
SAP ECC, S/4HANA, SuccessFactors, and Azure Active Directory.

Covers orphan detection, cross-system SoD risk, anomaly detection,
and manual cluster merge operations.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

from core.identity_correlation.engine import (
    IdentityCorrelationEngine,
    IdentityCluster,
    SystemAccount,
    CorrelationLink,
    CorrelationResult,
    OrphanAccount,
    CrossSystemRisk,
    IdentityAnomaly,
    CorrelationStats,
    SystemType,
    CorrelationMethod,
    AccountStatus,
    AnomalyType,
    RiskLevel,
)

router = APIRouter(tags=["Identity Correlation"])

# Per-tenant engine registry
_engines: Dict[str, IdentityCorrelationEngine] = {}


def _get_tenant_id() -> str:
    from core.tenant import get_current_tenant
    ctx = get_current_tenant()
    return ctx.tenant_id if ctx else "default"


def _get_engine(tenant_id: str = Depends(_get_tenant_id)) -> IdentityCorrelationEngine:
    if tenant_id not in _engines:
        _engines[tenant_id] = IdentityCorrelationEngine()
    return _engines[tenant_id]


# ===========================================================================
# Request / Response models
# ===========================================================================

class CorrelateUserRequest(BaseModel):
    """Request body for correlating a specific user across systems."""
    user_id: str
    system: str     # SystemType value, e.g. "sap_ecc"


class MergeRequest(BaseModel):
    """Request body for manually merging two identity clusters."""
    cluster_id_a: str
    cluster_id_b: str
    merged_by: str = "admin"


class SystemAccountResponse(BaseModel):
    account_id: str
    system: str
    username: str
    display_name: str
    email: Optional[str]
    employee_id: Optional[str]
    department: Optional[str]
    location: Optional[str]
    manager_id: Optional[str]
    job_title: Optional[str]
    status: str
    last_login: Optional[str]
    roles: List[str]
    groups: List[str]
    created_at: Optional[str]


class CorrelationLinkResponse(BaseModel):
    account_a_id: str
    account_b_id: str
    system_a: str
    system_b: str
    method: str
    confidence: float
    evidence: List[str]
    created_at: str
    created_by: str


class IdentityClusterResponse(BaseModel):
    cluster_id: str
    canonical_name: str
    canonical_email: Optional[str]
    employee_id: Optional[str]
    department: Optional[str]
    location: Optional[str]
    job_title: Optional[str]
    accounts: List[SystemAccountResponse]
    correlation_links: List[CorrelationLinkResponse]
    overall_confidence: float
    risk_level: str
    anomalies: List[str]
    last_correlated: str


class OrphanAccountResponse(BaseModel):
    account: SystemAccountResponse
    reason: str
    risk_level: str
    last_login: Optional[str]
    days_since_login: Optional[int]
    recommended_action: str


class CrossSystemRiskResponse(BaseModel):
    cluster_id: str
    canonical_name: str
    risk_id: str
    risk_name: str
    risk_level: str
    contributing_accounts: List[Dict[str, str]]
    description: str
    sod_rule: Optional[str]
    remediation: str


class IdentityAnomalyResponse(BaseModel):
    anomaly_id: str
    anomaly_type: str
    cluster_id: Optional[str]
    affected_accounts: List[Dict[str, str]]
    description: str
    risk_level: str
    detected_at: str
    recommended_action: str
    evidence: List[str]


class CorrelationResultResponse(BaseModel):
    source_account: SystemAccountResponse
    matched_accounts: List[SystemAccountResponse]
    correlation_links: List[CorrelationLinkResponse]
    cluster_id: Optional[str]
    overall_confidence: float
    unmatched_systems: List[str]
    summary: str


class CorrelationStatsResponse(BaseModel):
    total_accounts: int
    total_clusters: int
    fully_correlated: int
    partially_correlated: int
    orphan_accounts: int
    anomaly_count: int
    cross_system_risks: int
    average_confidence: float
    by_system: Dict[str, int]
    last_run: str


# ===========================================================================
# Serialization helpers
# ===========================================================================

def _serialize_account(acc: SystemAccount) -> SystemAccountResponse:
    return SystemAccountResponse(
        account_id=acc.account_id,
        system=acc.system.value,
        username=acc.username,
        display_name=acc.display_name,
        email=acc.email,
        employee_id=acc.employee_id,
        department=acc.department,
        location=acc.location,
        manager_id=acc.manager_id,
        job_title=acc.job_title,
        status=acc.status.value,
        last_login=acc.last_login,
        roles=acc.roles,
        groups=acc.groups,
        created_at=acc.created_at,
    )


def _serialize_link(lnk: CorrelationLink) -> CorrelationLinkResponse:
    return CorrelationLinkResponse(
        account_a_id=lnk.account_a_id,
        account_b_id=lnk.account_b_id,
        system_a=lnk.system_a.value,
        system_b=lnk.system_b.value,
        method=lnk.method.value,
        confidence=lnk.confidence,
        evidence=lnk.evidence,
        created_at=lnk.created_at,
        created_by=lnk.created_by,
    )


def _serialize_cluster(cluster: IdentityCluster) -> IdentityClusterResponse:
    return IdentityClusterResponse(
        cluster_id=cluster.cluster_id,
        canonical_name=cluster.canonical_name,
        canonical_email=cluster.canonical_email,
        employee_id=cluster.employee_id,
        department=cluster.department,
        location=cluster.location,
        job_title=cluster.job_title,
        accounts=[_serialize_account(a) for a in cluster.accounts],
        correlation_links=[_serialize_link(lnk) for lnk in cluster.correlation_links],
        overall_confidence=cluster.overall_confidence,
        risk_level=cluster.risk_level.value,
        anomalies=cluster.anomalies,
        last_correlated=cluster.last_correlated,
    )


def _serialize_orphan(orphan: OrphanAccount) -> OrphanAccountResponse:
    return OrphanAccountResponse(
        account=_serialize_account(orphan.account),
        reason=orphan.reason,
        risk_level=orphan.risk_level.value,
        last_login=orphan.last_login,
        days_since_login=orphan.days_since_login,
        recommended_action=orphan.recommended_action,
    )


def _serialize_risk(risk: CrossSystemRisk) -> CrossSystemRiskResponse:
    return CrossSystemRiskResponse(
        cluster_id=risk.cluster_id,
        canonical_name=risk.canonical_name,
        risk_id=risk.risk_id,
        risk_name=risk.risk_name,
        risk_level=risk.risk_level.value,
        contributing_accounts=risk.contributing_accounts,
        description=risk.description,
        sod_rule=risk.sod_rule,
        remediation=risk.remediation,
    )


def _serialize_anomaly(anomaly: IdentityAnomaly) -> IdentityAnomalyResponse:
    return IdentityAnomalyResponse(
        anomaly_id=anomaly.anomaly_id,
        anomaly_type=anomaly.anomaly_type.value,
        cluster_id=anomaly.cluster_id,
        affected_accounts=anomaly.affected_accounts,
        description=anomaly.description,
        risk_level=anomaly.risk_level.value,
        detected_at=anomaly.detected_at,
        recommended_action=anomaly.recommended_action,
        evidence=anomaly.evidence,
    )


def _serialize_correlation_result(result: CorrelationResult) -> CorrelationResultResponse:
    return CorrelationResultResponse(
        source_account=_serialize_account(result.source_account),
        matched_accounts=[_serialize_account(a) for a in result.matched_accounts],
        correlation_links=[_serialize_link(lnk) for lnk in result.correlation_links],
        cluster_id=result.cluster_id,
        overall_confidence=result.overall_confidence,
        unmatched_systems=[s.value for s in result.unmatched_systems],
        summary=result.summary,
    )


# ===========================================================================
# Endpoints
# ===========================================================================

@router.get(
    "/overview",
    response_model=CorrelationStatsResponse,
    summary="Identity correlation overview",
    description=(
        "Returns high-level statistics: total accounts, cluster counts, "
        "orphan count, anomaly count, cross-system risks, and average "
        "correlation confidence."
    ),
)
def get_overview(engine: IdentityCorrelationEngine = Depends(_get_engine)):
    stats = engine.get_overview()
    return CorrelationStatsResponse(
        total_accounts=stats.total_accounts,
        total_clusters=stats.total_clusters,
        fully_correlated=stats.fully_correlated,
        partially_correlated=stats.partially_correlated,
        orphan_accounts=stats.orphan_accounts,
        anomaly_count=stats.anomaly_count,
        cross_system_risks=stats.cross_system_risks,
        average_confidence=stats.average_confidence,
        by_system=stats.by_system,
        last_run=stats.last_run,
    )


@router.get(
    "/clusters",
    response_model=List[IdentityClusterResponse],
    summary="List all identity clusters",
    description=(
        "Returns all identity clusters. Each cluster groups accounts across "
        "systems that are believed to belong to the same person. "
        "Use the risk_level filter to narrow results."
    ),
)
def list_clusters(
    risk_level: Optional[str] = Query(
        default=None,
        description="Filter by risk level: critical, high, medium, low",
    ),
    engine: IdentityCorrelationEngine = Depends(_get_engine),
):
    clusters = engine.correlate_all()
    if risk_level:
        try:
            rl = RiskLevel(risk_level.lower())
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid risk_level '{risk_level}'. "
                       f"Valid values: {[r.value for r in RiskLevel]}",
            )
        clusters = [c for c in clusters if c.risk_level == rl]
    return [_serialize_cluster(c) for c in clusters]


@router.get(
    "/clusters/{cluster_id}",
    response_model=IdentityClusterResponse,
    summary="Get cluster detail",
    description=(
        "Returns full detail for a specific identity cluster including all accounts, "
        "correlation links, confidence scores, and detected anomalies."
    ),
)
def get_cluster(
    cluster_id: str,
    engine: IdentityCorrelationEngine = Depends(_get_engine),
):
    try:
        cluster = engine.get_cluster(cluster_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return _serialize_cluster(cluster)


@router.get(
    "/orphans",
    response_model=List[OrphanAccountResponse],
    summary="List orphaned accounts",
    description=(
        "Returns accounts with no confirmed correlation to any other system. "
        "These are accounts that cannot be verified against an HR record and "
        "may represent terminated employees, service accounts, or unauthorized access."
    ),
)
def list_orphans(engine: IdentityCorrelationEngine = Depends(_get_engine)):
    orphans = engine.find_orphans()
    return [_serialize_orphan(o) for o in orphans]


@router.get(
    "/cross-system-risk",
    response_model=List[CrossSystemRiskResponse],
    summary="Get cross-system SoD risks",
    description=(
        "Returns SoD risks that are only visible when combining access across "
        "multiple systems (e.g. PO creation in SAP + PO approval in Azure AD). "
        "Optionally filter by cluster_id."
    ),
)
def get_cross_system_risks(
    cluster_id: Optional[str] = Query(
        default=None,
        description="Filter risks to a specific identity cluster",
    ),
    engine: IdentityCorrelationEngine = Depends(_get_engine),
):
    if cluster_id:
        try:
            risks = engine.get_cross_system_risk(cluster_id)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc))
    else:
        risks = engine.get_all_cross_system_risks()
    return [_serialize_risk(r) for r in risks]


@router.post(
    "/correlate/{user_id}",
    response_model=CorrelationResultResponse,
    summary="Correlate a specific user",
    description=(
        "Finds the identity cluster for the specified account and returns "
        "all correlated accounts in other systems, correlation methods, "
        "confidence scores, and any unmatched systems."
    ),
)
def correlate_user(
    user_id: str,
    request: CorrelateUserRequest,
    engine: IdentityCorrelationEngine = Depends(_get_engine),
):
    try:
        result = engine.correlate_user(user_id, request.system)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return _serialize_correlation_result(result)


@router.get(
    "/anomalies",
    response_model=List[IdentityAnomalyResponse],
    summary="Detect identity anomalies",
    description=(
        "Returns all detected identity anomalies: ghost accounts, orphans, "
        "name/department mismatches, duplicate accounts, stale accounts, "
        "and cross-system SoD risks visible in cluster data."
    ),
)
def list_anomalies(
    anomaly_type: Optional[str] = Query(
        default=None,
        description=(
            "Filter by anomaly type: ghost_account, orphan_account, name_mismatch, "
            "department_mismatch, duplicate_account, excessive_accounts, "
            "cross_system_sod, stale_account"
        ),
    ),
    engine: IdentityCorrelationEngine = Depends(_get_engine),
):
    anomalies = engine.detect_anomalies()
    if anomaly_type:
        try:
            at = AnomalyType(anomaly_type.lower())
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid anomaly_type '{anomaly_type}'. "
                       f"Valid values: {[a.value for a in AnomalyType]}",
            )
        anomalies = [a for a in anomalies if a.anomaly_type == at]
    return [_serialize_anomaly(a) for a in anomalies]


@router.post(
    "/merge",
    response_model=IdentityClusterResponse,
    summary="Manually merge two identity clusters",
    description=(
        "Merges two identity clusters into one. Use this when the correlation "
        "engine has not automatically linked two accounts that belong to the "
        "same person (e.g. contractor with different last name in one system). "
        "The merged cluster inherits cluster_id and canonical attributes from cluster_a."
    ),
)
def merge_clusters(
    request: MergeRequest,
    engine: IdentityCorrelationEngine = Depends(_get_engine),
):
    try:
        merged = engine.merge_clusters(
            request.cluster_id_a,
            request.cluster_id_b,
            request.merged_by,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return _serialize_cluster(merged)
