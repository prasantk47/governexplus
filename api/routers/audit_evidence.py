"""
Audit Evidence Center API Router

Provides endpoints for collecting, packaging, and exporting structured audit
evidence across all GRC modules to support SOX, ISO 27001, and GDPR reviews.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta

from core.audit_evidence.collector import (
    AuditEvidenceCollector,
    EvidenceCategory,
    EvidenceCategoryType,
    EvidenceItem,
    EvidencePackage,
    AuditSummary,
    PackageStatus,
)

router = APIRouter(tags=["Audit Evidence Center"])

# Shared collector — package store lives in module-level dict inside collector
_collector = AuditEvidenceCollector()


# =============================================================================
# Request / Response Models
# =============================================================================


class CollectEvidenceRequest(BaseModel):
    """Request body for triggering an evidence collection run."""

    start_date: datetime = Field(
        ...,
        description="Inclusive start of the evidence collection window (ISO 8601).",
    )
    end_date: datetime = Field(
        ...,
        description="Inclusive end of the evidence collection window (ISO 8601).",
    )
    categories: Optional[List[str]] = Field(
        None,
        description=(
            "List of evidence category identifiers to collect.  "
            "If omitted, all categories are included.  "
            "Valid values: user_access, role_changes, approvals, sod_violations, "
            "mitigations, firefighter, certifications, provisioning."
        ),
    )
    title: Optional[str] = Field(None, description="Optional title for the evidence package.")
    notes: Optional[str] = Field(None, description="Optional notes to attach to the package.")
    created_by: str = Field("api_user", description="User or system initiating the collection.")


class ExportPackageRequest(BaseModel):
    """Request body for exporting a specific evidence package."""

    package_id: str = Field(..., description="The package identifier returned from /collect.")
    format: str = Field("json", description="Export format.  Currently only 'json' is supported.")


class EvidenceCategoryResponse(BaseModel):
    """Metadata for an available evidence category."""

    category_id: str
    display_name: str
    description: str
    regulatory_mapping: List[str]
    item_count_available: int


class EvidenceItemResponse(BaseModel):
    """A single evidence item."""

    item_id: str
    timestamp: str
    actor: str
    action: str
    target: str
    detail: Dict[str, Any]
    evidence_type: str
    category: str
    risk_level: str
    system_source: str
    is_exception: bool


class EvidencePackageSummaryResponse(BaseModel):
    """Lightweight package entry for list views (no item payload)."""

    package_id: str
    title: str
    created_at: str
    created_by: str
    start_date: str
    end_date: str
    categories_requested: List[str]
    item_count: int
    package_hash: str
    status: str
    notes: str


class EvidencePackageDetailResponse(EvidencePackageSummaryResponse):
    """Full package response including all evidence items."""

    items: List[EvidenceItemResponse]


class AuditSummaryResponse(BaseModel):
    """Compliance summary derived from an evidence package."""

    package_id: str
    period_start: str
    period_end: str
    total_evidence_items: int
    by_category: Dict[str, int]
    by_risk_level: Dict[str, int]
    exception_count: int
    sod_violations_detected: int
    sod_violations_resolved: int
    open_firefighter_sessions: int
    certifications_completed: int
    provisioning_requests: int
    compliance_score: float
    key_findings: List[str]
    generated_at: str


# =============================================================================
# Serialisation helpers
# =============================================================================


def _serialise_category(cat: EvidenceCategory) -> EvidenceCategoryResponse:
    return EvidenceCategoryResponse(
        category_id=cat.category_id.value,
        display_name=cat.display_name,
        description=cat.description,
        regulatory_mapping=cat.regulatory_mapping,
        item_count_available=cat.item_count_available,
    )


def _serialise_item(item: EvidenceItem) -> EvidenceItemResponse:
    return EvidenceItemResponse(
        item_id=item.item_id,
        timestamp=item.timestamp.isoformat(),
        actor=item.actor,
        action=item.action,
        target=item.target,
        detail=item.detail,
        evidence_type=item.evidence_type.value,
        category=item.category.value,
        risk_level=item.risk_level,
        system_source=item.system_source,
        is_exception=item.is_exception,
    )


def _serialise_package_summary(pkg: EvidencePackage) -> EvidencePackageSummaryResponse:
    return EvidencePackageSummaryResponse(
        package_id=pkg.package_id,
        title=pkg.title,
        created_at=pkg.created_at.isoformat(),
        created_by=pkg.created_by,
        start_date=pkg.start_date.isoformat(),
        end_date=pkg.end_date.isoformat(),
        categories_requested=[c.value for c in pkg.categories_requested],
        item_count=pkg.item_count,
        package_hash=pkg.package_hash,
        status=pkg.status.value,
        notes=pkg.notes,
    )


def _serialise_package_detail(pkg: EvidencePackage) -> EvidencePackageDetailResponse:
    return EvidencePackageDetailResponse(
        package_id=pkg.package_id,
        title=pkg.title,
        created_at=pkg.created_at.isoformat(),
        created_by=pkg.created_by,
        start_date=pkg.start_date.isoformat(),
        end_date=pkg.end_date.isoformat(),
        categories_requested=[c.value for c in pkg.categories_requested],
        item_count=pkg.item_count,
        package_hash=pkg.package_hash,
        status=pkg.status.value,
        notes=pkg.notes,
        items=[_serialise_item(i) for i in pkg.items],
    )


def _serialise_audit_summary(s: AuditSummary) -> AuditSummaryResponse:
    return AuditSummaryResponse(
        package_id=s.package_id,
        period_start=s.period_start.isoformat(),
        period_end=s.period_end.isoformat(),
        total_evidence_items=s.total_evidence_items,
        by_category=s.by_category,
        by_risk_level=s.by_risk_level,
        exception_count=s.exception_count,
        sod_violations_detected=s.sod_violations_detected,
        sod_violations_resolved=s.sod_violations_resolved,
        open_firefighter_sessions=s.open_firefighter_sessions,
        certifications_completed=s.certifications_completed,
        provisioning_requests=s.provisioning_requests,
        compliance_score=s.compliance_score,
        key_findings=s.key_findings,
        generated_at=s.generated_at.isoformat(),
    )


def _parse_categories(raw: Optional[List[str]]) -> Optional[List[EvidenceCategoryType]]:
    """Parse and validate category strings, raising HTTP 400 on invalid values."""
    if not raw:
        return None
    valid = {e.value: e for e in EvidenceCategoryType}
    parsed: List[EvidenceCategoryType] = []
    for cat in raw:
        if cat not in valid:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Invalid category '{cat}'.  "
                    f"Valid values: {sorted(valid.keys())}."
                ),
            )
        parsed.append(valid[cat])
    return parsed


# =============================================================================
# Endpoints
# =============================================================================


@router.get(
    "/categories",
    response_model=List[EvidenceCategoryResponse],
    summary="List available evidence categories",
    description=(
        "Returns all GRC module categories from which evidence can be collected, "
        "including regulatory mapping references (SOX, ISO 27001, GDPR)."
    ),
)
def get_categories() -> List[EvidenceCategoryResponse]:
    """
    Return metadata for all available audit evidence categories.

    Use the ``category_id`` values in the ``/collect`` endpoint to select
    which modules to draw evidence from.
    """
    categories = _collector.get_available_categories()
    return [_serialise_category(c) for c in categories]


@router.post(
    "/collect",
    response_model=EvidencePackageSummaryResponse,
    summary="Collect evidence for a date range",
    description=(
        "Triggers an evidence collection run for the specified date range and "
        "categories.  Returns a package summary including the package_id needed "
        "to retrieve or export the full package."
    ),
    status_code=201,
)
def collect_evidence(body: CollectEvidenceRequest) -> EvidencePackageSummaryResponse:
    """
    Collect GRC audit evidence for the given date range and categories.

    The resulting ``EvidencePackage`` is stored in memory and retrievable via
    ``GET /packages/{package_id}``.  A SHA-256 hash of the item list is
    computed for tamper-evidence purposes.

    Returns 400 if the date range is invalid or a category identifier is
    unrecognised.
    """
    if body.start_date > body.end_date:
        raise HTTPException(
            status_code=400,
            detail="start_date must be before end_date.",
        )

    max_days = 366
    if (body.end_date - body.start_date).days > max_days:
        raise HTTPException(
            status_code=400,
            detail=f"Date range must not exceed {max_days} days.",
        )

    parsed_categories = _parse_categories(body.categories)

    try:
        package = _collector.collect_evidence(
            start_date=body.start_date,
            end_date=body.end_date,
            categories=parsed_categories,
            created_by=body.created_by,
            title=body.title or "",
            notes=body.notes or "",
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return _serialise_package_summary(package)


@router.get(
    "/packages",
    response_model=List[EvidencePackageSummaryResponse],
    summary="List previously generated packages",
    description=(
        "Returns all evidence packages generated in this session, ordered by "
        "creation date descending.  Item payloads are omitted for performance; "
        "use GET /packages/{package_id} to retrieve the full package."
    ),
)
def list_packages(
    status: Optional[str] = Query(None, description="Filter by package status: draft, finalized, exported."),
) -> List[EvidencePackageSummaryResponse]:
    """
    List all previously generated evidence packages.

    Optionally filter by lifecycle status.
    """
    packages = _collector.get_packages()
    if status:
        valid_statuses = {s.value for s in PackageStatus}
        if status not in valid_statuses:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status '{status}'.  Valid values: {sorted(valid_statuses)}.",
            )
        packages = [p for p in packages if p.status.value == status]
    return [_serialise_package_summary(p) for p in packages]


@router.get(
    "/packages/{package_id}",
    response_model=EvidencePackageDetailResponse,
    summary="Retrieve a specific evidence package",
    description=(
        "Returns the full evidence package including all collected items.  "
        "Use the package_id returned by POST /collect."
    ),
)
def get_package(package_id: str) -> EvidencePackageDetailResponse:
    """
    Retrieve a specific evidence package by its ID.

    Returns 404 if the package does not exist or has not been generated in
    the current session.
    """
    package = _collector.get_package(package_id)
    if not package:
        raise HTTPException(
            status_code=404,
            detail=f"Evidence package '{package_id}' not found.",
        )
    return _serialise_package_detail(package)


@router.post(
    "/export",
    summary="Export an evidence package",
    description=(
        "Exports a previously collected evidence package as a structured JSON "
        "document suitable for submission to auditors.  Marks the package as "
        "'exported' in the lifecycle."
    ),
)
def export_package(body: ExportPackageRequest) -> Dict:
    """
    Export an evidence package as structured JSON.

    The exported document includes the package metadata, a SHA-256 hash for
    tamper verification, and the full ordered list of evidence items.

    Returns 400 for unsupported formats and 404 for unknown package IDs.
    """
    if body.format.lower() != "json":
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported export format '{body.format}'.  Only 'json' is currently supported.",
        )

    try:
        exported = _collector.export_package(body.package_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    return exported


@router.get(
    "/summary",
    response_model=AuditSummaryResponse,
    summary="Quick compliance summary",
    description=(
        "Generates an evidence collection for the last 30 days across all "
        "categories and returns the compliance summary without persisting a "
        "named package.  Useful for dashboard widgets."
    ),
)
def get_quick_summary(
    days: int = Query(30, ge=1, le=365, description="Number of days to look back."),
) -> AuditSummaryResponse:
    """
    Return a quick compliance summary for the last N days.

    This endpoint is designed for dashboard use.  It collects all evidence
    for the requested window, derives summary metrics, and returns them
    without requiring a prior ``/collect`` call.
    """
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)

    package = _collector.collect_evidence(
        start_date=start_date,
        end_date=end_date,
        categories=None,
        created_by="dashboard",
        title=f"Quick summary — last {days} days",
    )
    summary = _collector.generate_summary(package)
    return _serialise_audit_summary(summary)
