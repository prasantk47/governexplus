"""
Reporting & Analytics API Router

Endpoints for report generation, templates, and scheduling.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime

from core.reporting import (
    ReportingEngine, ReportFormat, ReportType
)

router = APIRouter(tags=["Reporting"])

reporting_engine = ReportingEngine()


# Request Models
class GenerateReportRequest(BaseModel):
    template_id: str
    parameters: Dict = Field(default_factory=dict)
    format: str = "pdf"


class CreateTemplateRequest(BaseModel):
    name: str
    description: str
    report_type: str
    sections: List[Dict] = Field(default_factory=list)
    parameters: List[Dict] = Field(default_factory=list)
    default_format: str = "pdf"


class CreateScheduleRequest(BaseModel):
    template_id: str
    name: str
    cron_expression: str
    parameters: Dict = Field(default_factory=dict)
    format: str = "pdf"
    recipients: List[str] = Field(default_factory=list)


# Report Generation Endpoints
@router.post("/generate")
async def generate_report(
    request: GenerateReportRequest,
    generated_by: str = Query(...)
):
    """Generate a report from a template"""
    try:
        format_enum = ReportFormat(request.format)
        report = reporting_engine.generate_report(
            template_id=request.template_id,
            parameters=request.parameters,
            format=format_enum,
            generated_by=generated_by
        )
        return report.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/reports")
async def list_reports(
    report_type: Optional[str] = Query(None),
    generated_by: Optional[str] = Query(None),
    from_date: Optional[datetime] = Query(None),
    to_date: Optional[datetime] = Query(None)
):
    """List generated reports"""
    type_enum = ReportType(report_type) if report_type else None
    reports = reporting_engine.list_reports(type_enum, generated_by, from_date, to_date)
    return {"total": len(reports), "reports": [r.to_dict() for r in reports]}


@router.get("/reports/{report_id}")
async def get_report(report_id: str):
    """Get report details"""
    report = reporting_engine.get_report(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report.to_dict()


@router.get("/reports/{report_id}/download")
async def download_report(report_id: str):
    """Download report content"""
    report = reporting_engine.get_report(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    # In production, this would return the actual file
    return {
        "report_id": report_id,
        "filename": f"{report.name}.{report.format.value}",
        "content_type": _get_content_type(report.format),
        "download_url": f"/api/reports/{report_id}/content"
    }


def _get_content_type(format: ReportFormat) -> str:
    """Get MIME content type for report format"""
    content_types = {
        ReportFormat.PDF: "application/pdf",
        ReportFormat.EXCEL: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ReportFormat.CSV: "text/csv",
        ReportFormat.JSON: "application/json",
        ReportFormat.HTML: "text/html"
    }
    return content_types.get(format, "application/octet-stream")


# Template Endpoints
@router.get("/templates")
async def list_templates(
    report_type: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None)
):
    """List report templates"""
    type_enum = ReportType(report_type) if report_type else None
    templates = reporting_engine.list_templates(type_enum, is_active)
    return {"total": len(templates), "templates": [t.to_dict() for t in templates]}


@router.get("/templates/{template_id}")
async def get_template(template_id: str):
    """Get template details"""
    template = reporting_engine.get_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return template.to_dict()


@router.post("/templates")
async def create_template(
    request: CreateTemplateRequest,
    created_by: str = Query(...)
):
    """Create a new report template"""
    try:
        report_type = ReportType(request.report_type)
        default_format = ReportFormat(request.default_format)
        template = reporting_engine.create_template(
            name=request.name,
            description=request.description,
            report_type=report_type,
            sections=request.sections,
            parameters=request.parameters,
            default_format=default_format,
            created_by=created_by
        )
        return template.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/templates/{template_id}")
async def update_template(
    template_id: str,
    request: CreateTemplateRequest
):
    """Update a report template"""
    try:
        report_type = ReportType(request.report_type)
        default_format = ReportFormat(request.default_format)
        template = reporting_engine.update_template(
            template_id=template_id,
            name=request.name,
            description=request.description,
            report_type=report_type,
            sections=request.sections,
            parameters=request.parameters,
            default_format=default_format
        )
        return template.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/templates/{template_id}")
async def delete_template(template_id: str):
    """Delete a report template"""
    try:
        reporting_engine.delete_template(template_id)
        return {"status": "deleted", "template_id": template_id}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# Schedule Endpoints
@router.get("/schedules")
async def list_schedules(
    is_active: Optional[bool] = Query(None)
):
    """List report schedules"""
    schedules = reporting_engine.list_schedules(is_active)
    return {"total": len(schedules), "schedules": [s.to_dict() for s in schedules]}


@router.get("/schedules/{schedule_id}")
async def get_schedule(schedule_id: str):
    """Get schedule details"""
    schedule = reporting_engine.get_schedule(schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return schedule.to_dict()


@router.post("/schedules")
async def create_schedule(
    request: CreateScheduleRequest,
    created_by: str = Query(...)
):
    """Create a new report schedule"""
    try:
        format_enum = ReportFormat(request.format)
        schedule = reporting_engine.create_schedule(
            template_id=request.template_id,
            name=request.name,
            cron_expression=request.cron_expression,
            parameters=request.parameters,
            format=format_enum,
            recipients=request.recipients,
            created_by=created_by
        )
        return schedule.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/schedules/{schedule_id}/toggle")
async def toggle_schedule(schedule_id: str):
    """Enable or disable a schedule"""
    try:
        schedule = reporting_engine.toggle_schedule(schedule_id)
        return schedule.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/schedules/{schedule_id}/run")
async def run_scheduled_report(
    schedule_id: str,
    generated_by: str = Query(...)
):
    """Manually run a scheduled report"""
    try:
        report = reporting_engine.run_scheduled_report(schedule_id, generated_by)
        return report.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/schedules/{schedule_id}")
async def delete_schedule(schedule_id: str):
    """Delete a report schedule"""
    try:
        reporting_engine.delete_schedule(schedule_id)
        return {"status": "deleted", "schedule_id": schedule_id}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# Analytics Endpoints
@router.get("/analytics/summary")
async def get_analytics_summary():
    """Get reporting analytics summary"""
    return reporting_engine.get_analytics_summary()


@router.get("/analytics/usage")
async def get_report_usage(
    from_date: Optional[datetime] = Query(None),
    to_date: Optional[datetime] = Query(None)
):
    """Get report usage statistics"""
    return reporting_engine.get_report_usage(from_date, to_date)


# Quick Reports (Pre-defined report generation)
@router.post("/quick/executive-summary")
async def generate_executive_summary(
    generated_by: str = Query(...),
    format: str = Query(default="pdf")
):
    """Generate executive summary report"""
    try:
        format_enum = ReportFormat(format)
        report = reporting_engine.generate_quick_report(
            "executive_summary",
            format_enum,
            generated_by
        )
        return report.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/quick/sod-violations")
async def generate_sod_report(
    generated_by: str = Query(...),
    format: str = Query(default="pdf"),
    include_mitigated: bool = Query(default=False)
):
    """Generate SoD violations report"""
    try:
        format_enum = ReportFormat(format)
        report = reporting_engine.generate_quick_report(
            "sod_violations",
            format_enum,
            generated_by,
            {"include_mitigated": include_mitigated}
        )
        return report.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/quick/user-access")
async def generate_user_access_report(
    generated_by: str = Query(...),
    user_id: Optional[str] = Query(None),
    format: str = Query(default="excel")
):
    """Generate user access report"""
    try:
        format_enum = ReportFormat(format)
        params = {}
        if user_id:
            params["user_id"] = user_id
        report = reporting_engine.generate_quick_report(
            "user_access",
            format_enum,
            generated_by,
            params
        )
        return report.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/quick/compliance")
async def generate_compliance_report(
    generated_by: str = Query(...),
    framework_id: Optional[str] = Query(None),
    format: str = Query(default="pdf")
):
    """Generate compliance report"""
    try:
        format_enum = ReportFormat(format)
        params = {}
        if framework_id:
            params["framework_id"] = framework_id
        report = reporting_engine.generate_quick_report(
            "compliance",
            format_enum,
            generated_by,
            params
        )
        return report.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
