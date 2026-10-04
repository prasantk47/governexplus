"""
SAP Security Controls API Router

Endpoints for managing SAP security controls, evaluations, and exceptions.
"""

from fastapi import APIRouter, HTTPException, Query, Depends, UploadFile, File
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
import io

from db.database import get_db
from sqlalchemy.orm import Session
from core.security_controls import SecurityControlManager, ControlEvaluator, ControlImporter

router = APIRouter(tags=["SAP Security Controls"])


# =============================================================================
# Request/Response Models
# =============================================================================

class CreateControlRequest(BaseModel):
    control_id: Optional[str] = None
    control_name: str = Field(..., min_length=3)
    business_area: str
    control_type: str
    category: str
    description: str
    purpose: Optional[str] = None
    procedure: Optional[str] = None
    profile_parameter: Optional[str] = None
    expected_value: Optional[str] = None
    default_risk_rating: str = "YELLOW"
    recommendation: Optional[str] = None
    comment: Optional[str] = None
    is_automated: bool = False
    compliance_frameworks: List[str] = Field(default_factory=list)
    value_mappings: Optional[List[Dict[str, Any]]] = None


class UpdateControlRequest(BaseModel):
    control_name: Optional[str] = None
    business_area: Optional[str] = None
    control_type: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    purpose: Optional[str] = None
    procedure: Optional[str] = None
    profile_parameter: Optional[str] = None
    expected_value: Optional[str] = None
    default_risk_rating: Optional[str] = None
    recommendation: Optional[str] = None
    comment: Optional[str] = None
    status: Optional[str] = None
    is_automated: Optional[bool] = None
    compliance_frameworks: Optional[List[str]] = None


class ValueMappingRequest(BaseModel):
    value_condition: str
    value_pattern: Optional[str] = None
    risk_rating: str
    recommendation: Optional[str] = None
    comment: Optional[str] = None
    evaluation_order: int = 0


class EvaluateControlRequest(BaseModel):
    system_id: str
    actual_value: Optional[str] = None
    client: Optional[str] = None
    evaluated_by: Optional[str] = None
    additional_data: Optional[Dict[str, Any]] = None


class BatchEvaluateRequest(BaseModel):
    system_id: str
    client: Optional[str] = None
    evaluated_by: Optional[str] = None
    evaluations: List[Dict[str, Any]]


class ParameterEvaluateRequest(BaseModel):
    system_id: str
    client: Optional[str] = None
    evaluated_by: Optional[str] = None
    parameter_values: Dict[str, Any]


class CreateExceptionRequest(BaseModel):
    control_id: str
    system_id: Optional[str] = None
    requested_by: str
    business_justification: str
    risk_acceptance: Optional[str] = None
    compensating_controls: Optional[List[str]] = None
    valid_from: Optional[datetime] = None
    valid_to: Optional[datetime] = None
    is_permanent: bool = False
    review_frequency_days: int = 90


class ApproveExceptionRequest(BaseModel):
    approved_by: str
    approved: bool = True
    rejection_reason: Optional[str] = None


class ImportControlsRequest(BaseModel):
    content: str
    format: str = "csv"
    delimiter: str = "\t"
    update_existing: bool = False


# =============================================================================
# Control CRUD Endpoints
# =============================================================================

@router.get("/controls")
async def list_controls(
    category: Optional[str] = Query(None, description="Filter by category"),
    business_area: Optional[str] = Query(None, description="Filter by business area"),
    status: Optional[str] = Query(None, description="Filter by status (active, inactive, draft, deprecated)"),
    search: Optional[str] = Query(None, description="Search in name, description, ID"),
    limit: int = Query(100, le=1000, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    db: Session = Depends(get_db)
):
    """List all security controls with filtering and pagination"""
    manager = SecurityControlManager(db)
    return manager.list_controls(
        category=category,
        business_area=business_area,
        status=status,
        search=search,
        limit=limit,
        offset=offset
    )


@router.get("/controls/categories")
async def get_categories(db: Session = Depends(get_db)):
    """Get all unique control categories"""
    manager = SecurityControlManager(db)
    return {"categories": manager.get_categories()}


@router.get("/controls/business-areas")
async def get_business_areas(db: Session = Depends(get_db)):
    """Get all unique business areas"""
    manager = SecurityControlManager(db)
    return {"business_areas": manager.get_business_areas()}


@router.get("/controls/{control_id}")
async def get_control(control_id: str, db: Session = Depends(get_db)):
    """Get a specific control by ID"""
    manager = SecurityControlManager(db)
    control = manager.get_control(control_id)
    if not control:
        raise HTTPException(status_code=404, detail=f"Control not found: {control_id}")

    result = control.to_dict()
    result['value_mappings'] = manager.get_value_mappings(control_id)
    return result


@router.post("/controls")
async def create_control(request: CreateControlRequest, db: Session = Depends(get_db)):
    """Create a new security control"""
    manager = SecurityControlManager(db)

    try:
        control = manager.create_control(request.model_dump())
        return {
            "status": "success",
            "message": f"Control {control.control_id} created successfully",
            "control": control.to_dict()
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/controls/{control_id}")
async def update_control(
    control_id: str,
    request: UpdateControlRequest,
    db: Session = Depends(get_db)
):
    """Update an existing control"""
    manager = SecurityControlManager(db)

    update_data = {k: v for k, v in request.model_dump().items() if v is not None}
    control = manager.update_control(control_id, update_data)

    if not control:
        raise HTTPException(status_code=404, detail=f"Control not found: {control_id}")

    return {
        "status": "success",
        "message": f"Control {control_id} updated successfully",
        "control": control.to_dict()
    }


@router.delete("/controls/{control_id}")
async def delete_control(control_id: str, db: Session = Depends(get_db)):
    """Delete a control"""
    manager = SecurityControlManager(db)

    if not manager.delete_control(control_id):
        raise HTTPException(status_code=404, detail=f"Control not found: {control_id}")

    return {
        "status": "success",
        "message": f"Control {control_id} deleted successfully"
    }


# =============================================================================
# Value Mapping Endpoints
# =============================================================================

@router.get("/controls/{control_id}/mappings")
async def get_value_mappings(control_id: str, db: Session = Depends(get_db)):
    """Get value mappings for a control"""
    manager = SecurityControlManager(db)
    control = manager.get_control(control_id)
    if not control:
        raise HTTPException(status_code=404, detail=f"Control not found: {control_id}")

    return {"mappings": manager.get_value_mappings(control_id)}


@router.post("/controls/{control_id}/mappings")
async def add_value_mapping(
    control_id: str,
    request: ValueMappingRequest,
    db: Session = Depends(get_db)
):
    """Add a value mapping to a control"""
    manager = SecurityControlManager(db)

    try:
        mapping = manager.add_value_mapping(control_id, request.model_dump())
        return {
            "status": "success",
            "message": "Value mapping added successfully",
            "mapping": mapping.to_dict()
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# =============================================================================
# Evaluation Endpoints
# =============================================================================

@router.post("/controls/{control_id}/evaluate")
async def evaluate_control(
    control_id: str,
    request: EvaluateControlRequest,
    db: Session = Depends(get_db)
):
    """Evaluate a control against an actual value"""
    manager = SecurityControlManager(db)
    evaluator = ControlEvaluator(manager)

    try:
        evaluation = evaluator.evaluate_control(
            control_id=control_id,
            system_id=request.system_id,
            actual_value=request.actual_value,
            evaluated_by=request.evaluated_by,
            client=request.client,
            additional_data=request.additional_data
        )
        return {
            "status": "success",
            "evaluation": evaluation.to_dict()
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/evaluate/batch")
async def batch_evaluate(request: BatchEvaluateRequest, db: Session = Depends(get_db)):
    """Evaluate multiple controls in batch"""
    manager = SecurityControlManager(db)
    evaluator = ControlEvaluator(manager)

    result = evaluator.batch_evaluate(
        system_id=request.system_id,
        evaluations=request.evaluations,
        evaluated_by=request.evaluated_by,
        client=request.client
    )

    return result


@router.post("/evaluate/parameters")
async def evaluate_parameters(request: ParameterEvaluateRequest, db: Session = Depends(get_db)):
    """Evaluate all parameter-based controls against provided parameter values"""
    manager = SecurityControlManager(db)
    evaluator = ControlEvaluator(manager)

    result = evaluator.evaluate_parameter_controls(
        system_id=request.system_id,
        parameter_values=request.parameter_values,
        evaluated_by=request.evaluated_by,
        client=request.client
    )

    return result


@router.get("/evaluations")
async def get_evaluations(
    control_id: Optional[str] = Query(None),
    system_id: Optional[str] = Query(None),
    risk_rating: Optional[str] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    limit: int = Query(100, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """Get evaluation history with filtering"""
    manager = SecurityControlManager(db)
    return manager.get_evaluations(
        control_id=control_id,
        system_id=system_id,
        risk_rating=risk_rating,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        offset=offset
    )


@router.get("/evaluations/report/{system_id}")
async def get_evaluation_report(
    system_id: str,
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    db: Session = Depends(get_db)
):
    """Generate an evaluation report for a system"""
    manager = SecurityControlManager(db)
    evaluator = ControlEvaluator(manager)

    return evaluator.get_evaluation_report(
        system_id=system_id,
        start_date=start_date,
        end_date=end_date
    )


# =============================================================================
# Exception Endpoints
# =============================================================================

@router.post("/exceptions")
async def create_exception(request: CreateExceptionRequest, db: Session = Depends(get_db)):
    """Create an exception request"""
    manager = SecurityControlManager(db)

    try:
        exception = manager.create_exception(request.model_dump())
        return {
            "status": "success",
            "message": "Exception request created successfully",
            "exception": exception.to_dict()
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/exceptions")
async def get_exceptions(
    control_id: Optional[str] = Query(None),
    system_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(100, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """Get exceptions with filtering"""
    manager = SecurityControlManager(db)
    return manager.get_exceptions(
        control_id=control_id,
        system_id=system_id,
        status=status,
        limit=limit,
        offset=offset
    )


@router.post("/exceptions/{exception_id}/approve")
async def approve_exception(
    exception_id: str,
    request: ApproveExceptionRequest,
    db: Session = Depends(get_db)
):
    """Approve or reject an exception"""
    manager = SecurityControlManager(db)

    exception = manager.approve_exception(
        exception_id=exception_id,
        approved_by=request.approved_by,
        approved=request.approved,
        rejection_reason=request.rejection_reason
    )

    if not exception:
        raise HTTPException(status_code=404, detail=f"Exception not found: {exception_id}")

    return {
        "status": "success",
        "message": f"Exception {'approved' if request.approved else 'rejected'} successfully",
        "exception": exception.to_dict()
    }


# =============================================================================
# System Profile Endpoints
# =============================================================================

@router.get("/systems")
async def get_system_profiles(db: Session = Depends(get_db)):
    """Get security profiles for all systems"""
    manager = SecurityControlManager(db)
    return {"systems": manager.get_all_system_profiles()}


@router.get("/systems/{system_id}")
async def get_system_profile(system_id: str, db: Session = Depends(get_db)):
    """Get security profile for a specific system"""
    manager = SecurityControlManager(db)
    profile = manager.get_system_profile(system_id)

    if not profile:
        raise HTTPException(status_code=404, detail=f"System profile not found: {system_id}")

    return profile


# =============================================================================
# Dashboard & Statistics
# =============================================================================

@router.get("/dashboard")
async def get_dashboard(db: Session = Depends(get_db)):
    """Get dashboard statistics"""
    manager = SecurityControlManager(db)
    return manager.get_dashboard_stats()


# =============================================================================
# Import/Export Endpoints
# =============================================================================

@router.post("/import")
async def import_controls(request: ImportControlsRequest, db: Session = Depends(get_db)):
    """Import controls from CSV or JSON"""
    manager = SecurityControlManager(db)
    importer = ControlImporter(manager)

    try:
        if request.format.lower() == 'json':
            result = importer.import_from_json(
                request.content,
                update_existing=request.update_existing
            )
        else:
            result = importer.import_from_csv(
                request.content,
                delimiter=request.delimiter,
                update_existing=request.update_existing
            )

        return {
            "status": "success",
            "message": f"Import completed: {result['imported']} imported, {result['updated']} updated, {result['skipped']} skipped",
            "details": result
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Import failed: {str(e)}")


@router.post("/import/file")
async def import_controls_file(
    file: UploadFile = File(...),
    update_existing: bool = Query(False),
    db: Session = Depends(get_db)
):
    """Import controls from an uploaded file (supports CSV, TSV, JSON, and Excel)"""
    import traceback
    import logging

    logger = logging.getLogger(__name__)

    try:
        manager = SecurityControlManager(db)
        importer = ControlImporter(manager)

        content = await file.read()
        filename = file.filename or ""
        logger.info(f"Received file: {filename}, size: {len(content)} bytes")

        # Handle Excel files
        if filename.endswith('.xlsx') or filename.endswith('.xls'):
            try:
                import openpyxl
                from io import BytesIO

                wb = openpyxl.load_workbook(BytesIO(content), read_only=True, data_only=True)
                ws = wb.active

                # Convert Excel to CSV format
                rows = list(ws.iter_rows(values_only=True))
                if not rows:
                    raise HTTPException(status_code=400, detail="Excel file is empty")

                # Build CSV string from Excel data
                import csv
                output = io.StringIO()
                writer = csv.writer(output, delimiter='\t')
                for row in rows:
                    # Convert None to empty string
                    writer.writerow([str(cell) if cell is not None else '' for cell in row])
                content_str = output.getvalue()
                wb.close()

                logger.info(f"Converted Excel to CSV, {len(rows)} rows")
                result = importer.import_from_csv(content_str, delimiter='\t', update_existing=update_existing)

            except ImportError:
                raise HTTPException(
                    status_code=400,
                    detail="Excel file support requires openpyxl. Please install it with: pip install openpyxl. Alternatively, save your file as CSV or TSV."
                )

        elif filename.endswith('.json'):
            # Handle JSON files
            content_str = None
            for encoding in ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252']:
                try:
                    content_str = content.decode(encoding)
                    break
                except UnicodeDecodeError:
                    continue

            if content_str is None:
                raise HTTPException(status_code=400, detail="Could not decode JSON file.")

            result = importer.import_from_json(content_str, update_existing=update_existing)

        else:
            # Handle CSV/TSV files
            content_str = None
            used_encoding = None
            for encoding in ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252']:
                try:
                    content_str = content.decode(encoding)
                    used_encoding = encoding
                    break
                except UnicodeDecodeError:
                    continue

            if content_str is None:
                raise HTTPException(status_code=400, detail="Could not decode file. Please ensure it's a valid text file.")

            # Normalize line endings
            content_str = content_str.replace('\r\n', '\n').replace('\r', '\n')

            logger.info(f"Decoded file using {used_encoding}, content length: {len(content_str)} chars")

            delimiter = ',' if filename.endswith('.csv') else '\t'
            logger.info(f"Importing as CSV with delimiter: {repr(delimiter)}")
            result = importer.import_from_csv(content_str, delimiter=delimiter, update_existing=update_existing)

        logger.info(f"Import result: {result['imported']} imported, {result['updated']} updated, {result['skipped']} skipped, {len(result.get('errors', []))} errors")

        return {
            "status": "success",
            "message": f"Import completed: {result['imported']} imported, {result['updated']} updated, {result['skipped']} skipped",
            "details": result
        }
    except HTTPException:
        raise
    except Exception as e:
        error_msg = f"Import failed: {str(e)}"
        logger.error(f"{error_msg}\n{traceback.format_exc()}")
        raise HTTPException(status_code=400, detail=error_msg)


@router.get("/export")
async def export_controls(
    format: str = Query("json", description="Export format: json or csv"),
    control_ids: Optional[str] = Query(None, description="Comma-separated control IDs to export"),
    db: Session = Depends(get_db)
):
    """Export controls to JSON or CSV"""
    manager = SecurityControlManager(db)
    importer = ControlImporter(manager)

    ids = control_ids.split(',') if control_ids else None

    if format.lower() == 'csv':
        content = importer.export_to_csv(control_ids=ids)
        return StreamingResponse(
            io.StringIO(content),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=security_controls.csv"}
        )
    else:
        content = importer.export_to_json(control_ids=ids)
        return StreamingResponse(
            io.StringIO(content),
            media_type="application/json",
            headers={"Content-Disposition": "attachment; filename=security_controls.json"}
        )


@router.get("/import/template")
async def get_import_template(
    format: str = Query("json", description="Template format: json or csv"),
    db: Session = Depends(get_db)
):
    """Get an import template"""
    manager = SecurityControlManager(db)
    importer = ControlImporter(manager)

    template = importer.get_import_template(format=format)

    return {
        "format": format,
        "template": template
    }


# =============================================================================
# Template Library & Seed Endpoints
# =============================================================================

@router.get("/templates")
async def list_templates(
    category: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    compliance_framework: Optional[str] = Query(None),
):
    """
    List SAP security control templates from the built-in library.
    Templates are in-memory (SAP- prefix); customers adopt them into their environment.
    """
    from core.security_controls.sap_library import SAP_CONTROLS_LIBRARY

    results = SAP_CONTROLS_LIBRARY

    if category:
        results = [c for c in results if c.get("category", "").lower() == category.lower()]

    if compliance_framework:
        results = [
            c for c in results
            if compliance_framework.upper() in [f.upper() for f in c.get("compliance_frameworks", [])]
        ]

    if search:
        q = search.lower()
        results = [
            c for c in results
            if q in c.get("control_id", "").lower()
            or q in c.get("control_name", "").lower()
            or q in c.get("description", "").lower()
            or q in (c.get("profile_parameter") or "").lower()
        ]

    # Collect unique categories for filter UI
    all_categories = sorted({c.get("category", "") for c in SAP_CONTROLS_LIBRARY if c.get("category")})

    return {
        "templates": results,
        "total": len(results),
        "categories": all_categories,
    }


@router.post("/templates/{control_id}/adopt")
async def adopt_template(
    control_id: str,
    db: Session = Depends(get_db)
):
    """
    Adopt a SAP- template into the tenant's controls as a customizable CUST- copy.
    If a CUST- copy already exists it is returned as-is (idempotent).
    """
    from core.security_controls.sap_library import SAP_CONTROLS_LIBRARY

    template = next((c for c in SAP_CONTROLS_LIBRARY if c["control_id"] == control_id), None)
    if not template:
        raise HTTPException(status_code=404, detail=f"Template not found: {control_id}")

    # Derive CUST- id: SAP-AUTH-001 → CUST-AUTH-001
    cust_id = "CUST-" + control_id.removeprefix("SAP-")

    manager = SecurityControlManager(db)

    # Return existing if already adopted
    existing = manager.get_control(cust_id)
    if existing:
        return {
            "status": "existing",
            "message": f"Template already adopted as {cust_id}",
            "control": existing.to_dict(),
        }

    # Clone template with CUST- prefix
    adopted_data = {**template, "control_id": cust_id, "status": "active"}
    control = manager.create_control(adopted_data)

    return {
        "status": "adopted",
        "message": f"Template adopted as {cust_id} — you can now customize it",
        "control": control.to_dict(),
    }


@router.post("/seed-defaults")
async def seed_default_controls(db: Session = Depends(get_db)):
    """
    Seed the SAP security controls library into the database (idempotent).
    Existing controls (same control_id) are skipped — custom changes are preserved.
    """
    from core.security_controls.sap_library import SAP_CONTROLS_LIBRARY

    manager = SecurityControlManager(db)
    inserted = 0
    skipped = 0

    for ctrl in SAP_CONTROLS_LIBRARY:
        existing = manager.get_control(ctrl["control_id"])
        if existing:
            skipped += 1
            continue
        try:
            manager.create_control(ctrl)
            inserted += 1
        except Exception:
            skipped += 1

    return {
        "status": "success",
        "message": f"Seed complete: {inserted} inserted, {skipped} skipped (already exist)",
        "inserted": inserted,
        "skipped": skipped,
        "total_library": len(SAP_CONTROLS_LIBRARY),
    }
