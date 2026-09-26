"""
Fiori Security Analyzer API Router

Exposes endpoints for tracing and diagnosing the SAP Fiori authorization chain.

All endpoints are read-only. No database access is required — the analyzer
operates on an in-memory knowledge base of 30+ Fiori apps.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Any, Dict

from core.fiori.analyzer import (
    FioriSecurityAnalyzer,
    FioriApp,
    FioriAccessTrace,
    AppRequirements,
    TileDiagnosis,
    CatalogAnalysis,
    LayerStatus,
    ErrorPattern,
    RiskLevel,
)

router = APIRouter(tags=["Fiori Security Analyzer"])

# Single shared engine instance — stateless, safe to share
_analyzer = FioriSecurityAnalyzer()


# ===========================================================================
# Request / Response models
# ===========================================================================

class TraceRequest(BaseModel):
    """Request body for tracing Fiori app access for a specific user."""
    app_id: str
    user_id: str


class DiagnoseRequest(BaseModel):
    """Request body for diagnosing a tile error for a specific user."""
    app_id: str
    user_id: str


class FioriAppResponse(BaseModel):
    """Serializable summary of a Fiori app."""
    app_id: str
    name: str
    description: str
    catalog_id: str
    catalog_name: str
    space_id: str
    page_id: str
    odata_services: List[str]
    backend_transactions: List[str]
    required_auth_objects: List[Dict[str, Any]]
    target_mapping_id: str
    semantic_object: str
    semantic_action: str
    risk_level: str
    business_area: str
    tags: List[str]


class ChainLayerResponse(BaseModel):
    """Serializable Fiori authorization chain layer."""
    layer_name: str
    status: str
    object_id: str
    object_name: str
    details: str
    required_auth: List[str]
    missing_auth: List[str]
    remediation: Optional[str]


class TraceResponse(BaseModel):
    """Full authorization chain trace result."""
    app_id: str
    user_id: str
    timestamp: str
    overall_status: str
    error_pattern: str
    chain: List[ChainLayerResponse]
    summary: str
    remediation_steps: List[str]


class DiagnoseResponse(BaseModel):
    """Tile error diagnosis result."""
    app_id: str
    user_id: str
    tile_visible: bool
    launch_fails: bool
    root_cause: str
    error_pattern: str
    failing_layer: str
    missing_objects: List[str]
    remediation_steps: List[str]
    estimated_effort: str


class AppRequirementsResponse(BaseModel):
    """All authorization requirements for an app."""
    app_id: str
    app_name: str
    odata_services: List[str]
    backend_transactions: List[str]
    auth_objects: List[Dict[str, Any]]
    s_service_entries: List[Dict[str, str]]
    catalog_id: str
    target_mapping_id: str
    gateway_alias: str
    risk_level: str
    notes: List[str]


class CatalogResponse(BaseModel):
    """Catalog analysis result."""
    catalog_id: str
    catalog_name: str
    catalog_type: str
    app_count: int
    apps: List[Dict[str, str]]
    odata_services: List[str]
    required_auth_objects: List[str]
    risk_level: str
    assigned_business_roles: List[str]
    notes: str


# ===========================================================================
# Serialization helpers
# ===========================================================================

def _serialize_app(app: FioriApp) -> FioriAppResponse:
    return FioriAppResponse(
        app_id=app.app_id,
        name=app.name,
        description=app.description,
        catalog_id=app.catalog_id,
        catalog_name=app.catalog_name,
        space_id=app.space_id,
        page_id=app.page_id,
        odata_services=app.odata_services,
        backend_transactions=app.backend_transactions,
        required_auth_objects=app.required_auth_objects,
        target_mapping_id=app.target_mapping_id,
        semantic_object=app.semantic_object,
        semantic_action=app.semantic_action,
        risk_level=app.risk_level.value,
        business_area=app.business_area,
        tags=app.tags,
    )


def _serialize_trace(trace: FioriAccessTrace) -> TraceResponse:
    return TraceResponse(
        app_id=trace.app_id,
        user_id=trace.user_id,
        timestamp=trace.timestamp,
        overall_status=trace.overall_status.value,
        error_pattern=trace.error_pattern.value,
        chain=[
            ChainLayerResponse(
                layer_name=layer.layer_name,
                status=layer.status.value,
                object_id=layer.object_id,
                object_name=layer.object_name,
                details=layer.details,
                required_auth=layer.required_auth,
                missing_auth=layer.missing_auth,
                remediation=layer.remediation,
            )
            for layer in trace.chain
        ],
        summary=trace.summary,
        remediation_steps=trace.remediation_steps,
    )


def _serialize_diagnosis(diag: TileDiagnosis) -> DiagnoseResponse:
    return DiagnoseResponse(
        app_id=diag.app_id,
        user_id=diag.user_id,
        tile_visible=diag.tile_visible,
        launch_fails=diag.launch_fails,
        root_cause=diag.root_cause,
        error_pattern=diag.error_pattern.value,
        failing_layer=diag.failing_layer,
        missing_objects=diag.missing_objects,
        remediation_steps=diag.remediation_steps,
        estimated_effort=diag.estimated_effort,
    )


def _serialize_requirements(req: AppRequirements) -> AppRequirementsResponse:
    return AppRequirementsResponse(
        app_id=req.app_id,
        app_name=req.app_name,
        odata_services=req.odata_services,
        backend_transactions=req.backend_transactions,
        auth_objects=req.auth_objects,
        s_service_entries=req.s_service_entries,
        catalog_id=req.catalog_id,
        target_mapping_id=req.target_mapping_id,
        gateway_alias=req.gateway_alias,
        risk_level=req.risk_level.value,
        notes=req.notes,
    )


def _serialize_catalog(cat: CatalogAnalysis) -> CatalogResponse:
    return CatalogResponse(
        catalog_id=cat.catalog_id,
        catalog_name=cat.catalog_name,
        catalog_type=cat.catalog_type,
        app_count=cat.app_count,
        apps=cat.apps,
        odata_services=cat.odata_services,
        required_auth_objects=cat.required_auth_objects,
        risk_level=cat.risk_level.value,
        assigned_business_roles=cat.assigned_business_roles,
        notes=cat.notes,
    )


# ===========================================================================
# Endpoints
# ===========================================================================

@router.get(
    "/apps",
    response_model=List[FioriAppResponse],
    summary="List all Fiori apps",
    description=(
        "Returns the full Fiori application catalog with authorization metadata, "
        "OData service requirements, and risk levels."
    ),
)
def list_apps():
    apps = _analyzer.list_apps()
    return [_serialize_app(app) for app in apps]


@router.get(
    "/apps/{app_id}",
    response_model=AppRequirementsResponse,
    summary="Get app authorization requirements",
    description=(
        "Returns all authorization requirements for a specific Fiori app: "
        "OData services, S_SERVICE entries, backend transactions, and auth objects."
    ),
)
def get_app(app_id: str):
    try:
        req = _analyzer.get_app_requirements(app_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return _serialize_requirements(req)


@router.post(
    "/trace",
    response_model=TraceResponse,
    summary="Trace Fiori authorization chain",
    description=(
        "Traces the full Fiori authorization chain (8 layers) for a user/app pair. "
        "Returns pass/fail at each layer with remediation guidance."
    ),
)
def trace_access(request: TraceRequest):
    try:
        trace = _analyzer.trace_app(request.app_id, request.user_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return _serialize_trace(trace)


@router.post(
    "/diagnose",
    response_model=DiagnoseResponse,
    summary="Diagnose tile error",
    description=(
        "Diagnoses the 'tile visible but app launch fails' pattern. "
        "Identifies whether the failure is at catalog, S_SERVICE, gateway, "
        "or backend authorization layer."
    ),
)
def diagnose_tile_error(request: DiagnoseRequest):
    try:
        diagnosis = _analyzer.diagnose_tile_error(request.app_id, request.user_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return _serialize_diagnosis(diagnosis)


@router.get(
    "/catalogs",
    summary="List Fiori catalogs",
    description="Returns a summary list of all known Fiori catalogs with app counts and risk levels.",
)
def list_catalogs():
    return _analyzer.list_catalogs()


@router.get(
    "/catalogs/{catalog_id}",
    response_model=CatalogResponse,
    summary="Get catalog detail",
    description=(
        "Returns detailed analysis of a catalog including all apps, "
        "required OData services, authorization objects, and assigned business roles."
    ),
)
def get_catalog(catalog_id: str):
    try:
        cat = _analyzer.analyze_catalog(catalog_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return _serialize_catalog(cat)


@router.get(
    "/services",
    summary="List OData services",
    description=(
        "Returns a deduplicated list of all OData services referenced by Fiori apps "
        "in the knowledge base, including ICF paths and the primary app that uses them."
    ),
)
def list_odata_services():
    return _analyzer.list_odata_services()
