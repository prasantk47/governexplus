"""
Role Drift Detection API Router

Exposes endpoints for comparing role definitions across system landscapes
(DEV, QA, PROD) and surfacing drift findings for remediation.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Dict, List, Optional
from datetime import datetime

from core.drift.detector import (
    DriftDetector,
    DriftReport,
    DriftSummary,
    DriftFinding,
    DriftSeverity,
    DriftType,
)

router = APIRouter(tags=["Role Drift Detection"])

# Single shared detector instance (mock data is stateless)
_detector = DriftDetector()


# =============================================================================
# Request / Response Models
# =============================================================================


class DriftFindingResponse(BaseModel):
    """Serialised representation of a single drift finding."""

    finding_id: str
    drift_type: str
    severity: str
    system_a: str
    system_b: str
    field_path: str
    value_in_a: str
    value_in_b: str
    description: str
    remediation: str


class DriftReportResponse(BaseModel):
    """Serialised drift report for a single role."""

    role_name: str
    role_description: str
    scan_timestamp: str
    systems_present: List[str]
    systems_missing: List[str]
    drift_hash: Dict[str, str]
    is_drifted: bool
    overall_severity: str
    finding_count: int
    findings: List[DriftFindingResponse]


class DriftSummaryResponse(BaseModel):
    """Aggregated drift statistics across the estate."""

    scan_timestamp: str
    total_roles_scanned: int
    roles_in_sync: int
    roles_drifted: int
    drift_percentage: float
    by_severity: Dict[str, int]
    by_drift_type: Dict[str, int]
    most_drifted_roles: List[str]
    systems_compared: List[str]


class CompareSystemsRequest(BaseModel):
    """Request body for a two-system comparison."""

    system_a: str = Field(..., description="First system identifier, e.g. 'DEV'")
    system_b: str = Field(..., description="Second system identifier, e.g. 'PROD'")
    roles_filter: Optional[List[str]] = Field(
        None,
        description="Optional list of role names to restrict comparison.  If omitted, all roles are compared.",
    )


# =============================================================================
# Serialisation helpers
# =============================================================================


def _serialise_finding(f: DriftFinding) -> DriftFindingResponse:
    return DriftFindingResponse(
        finding_id=f.finding_id,
        drift_type=f.drift_type.value,
        severity=f.severity.value,
        system_a=f.system_a,
        system_b=f.system_b,
        field_path=f.field_path,
        value_in_a=f.value_in_a,
        value_in_b=f.value_in_b,
        description=f.description,
        remediation=f.remediation,
    )


def _serialise_report(r: DriftReport) -> DriftReportResponse:
    return DriftReportResponse(
        role_name=r.role_name,
        role_description=r.role_description,
        scan_timestamp=r.scan_timestamp.isoformat(),
        systems_present=r.systems_present,
        systems_missing=r.systems_missing,
        drift_hash=r.drift_hash,
        is_drifted=r.is_drifted,
        overall_severity=r.overall_severity.value,
        finding_count=r.finding_count,
        findings=[_serialise_finding(f) for f in r.findings],
    )


def _serialise_summary(s: DriftSummary) -> DriftSummaryResponse:
    return DriftSummaryResponse(
        scan_timestamp=s.scan_timestamp.isoformat(),
        total_roles_scanned=s.total_roles_scanned,
        roles_in_sync=s.roles_in_sync,
        roles_drifted=s.roles_drifted,
        drift_percentage=s.drift_percentage,
        by_severity=s.by_severity,
        by_drift_type=s.by_drift_type,
        most_drifted_roles=s.most_drifted_roles,
        systems_compared=s.systems_compared,
    )


# =============================================================================
# Endpoints
# =============================================================================


@router.get(
    "/summary",
    response_model=DriftSummaryResponse,
    summary="Drift overview statistics",
    description=(
        "Returns aggregated drift statistics across the full role estate including "
        "counts by severity, counts by drift type, and the most drifted roles."
    ),
)
def get_drift_summary() -> DriftSummaryResponse:
    """
    Return a high-level summary of role drift across all systems.

    The summary counts how many roles are in sync versus drifted, breaks
    down findings by severity and drift type, and lists the top 10 most
    drifted roles by finding count.
    """
    summary = _detector.get_drift_summary()
    return _serialise_summary(summary)


@router.get(
    "/scan",
    response_model=List[DriftReportResponse],
    summary="Full estate drift scan",
    description=(
        "Runs drift detection across all roles in the landscape and returns "
        "one DriftReport per role, ordered by severity (critical first)."
    ),
)
def scan_all_drift(
    drifted_only: bool = Query(False, description="When true, return only roles that have at least one drift finding."),
    severity: Optional[str] = Query(None, description="Filter by minimum severity: critical, high, medium, low."),
) -> List[DriftReportResponse]:
    """
    Scan all roles across DEV, QA, and PROD for definition drift.

    Parameters
    ----------
    drifted_only:
        If true, suppress fully-aligned roles from the response.
    severity:
        Minimum severity level to include.  Roles with lower overall severity
        are excluded.
    """
    reports = _detector.scan_all_drift()

    if drifted_only:
        reports = [r for r in reports if r.is_drifted]

    if severity:
        sev_order = {
            "critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4,
        }
        requested = sev_order.get(severity.lower())
        if requested is None:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid severity '{severity}'.  Valid values: critical, high, medium, low, info.",
            )
        reports = [r for r in reports if sev_order[r.overall_severity.value] <= requested]

    return [_serialise_report(r) for r in reports]


@router.get(
    "/roles/{role_id}",
    response_model=DriftReportResponse,
    summary="Drift detail for a specific role",
    description=(
        "Returns the full drift report for the named role, including every "
        "finding across all system pairs."
    ),
)
def get_role_drift(role_id: str) -> DriftReportResponse:
    """
    Analyse drift for a single role identified by ``role_id``.

    The ``role_id`` is case-insensitive.  Use the ``/scan`` endpoint or
    ``GET /roles`` from another router to discover role names.

    Raises 404 if the role is not found in the landscape.
    """
    try:
        report = _detector.detect_drift(role_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return _serialise_report(report)


@router.get(
    "/systems",
    summary="List systems being compared",
    description="Returns the identifiers of all systems included in the drift comparison.",
)
def get_systems() -> Dict:
    """
    Return the list of system identifiers used in landscape comparisons.

    The reference system (typically PROD) is also indicated.
    """
    return {
        "systems": _detector.get_systems(),
        "reference_system": _detector.REFERENCE_SYSTEM,
        "roles_in_landscape": len(_detector.list_roles()),
    }


@router.post(
    "/compare",
    response_model=List[DriftReportResponse],
    summary="Compare two specific systems",
    description=(
        "Compares role definitions between two named systems and returns drift "
        "reports restricted to findings between those systems only.  Optionally "
        "filtered to a subset of role names."
    ),
)
def compare_systems(body: CompareSystemsRequest) -> List[DriftReportResponse]:
    """
    Run a targeted comparison between two systems.

    Use this when you want to check specifically what is different between
    DEV and QA before promoting a transport, without the noise of the full
    three-way scan.

    The response is ordered by finding count descending.
    """
    try:
        reports = _detector.compare_systems(body.system_a, body.system_b)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    if body.roles_filter:
        upper_filter = {r.upper() for r in body.roles_filter}
        reports = [r for r in reports if r.role_name in upper_filter]

    return [_serialise_report(r) for r in reports]
