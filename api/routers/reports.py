"""
Simple Reports API Router for Frontend Demo

Handles basic report run and download operations.
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from datetime import datetime

router = APIRouter(tags=["Reports"])


# Mock report data
MOCK_REPORTS = {
    "RPT-001": {"id": "RPT-001", "name": "SoD Violations Summary", "format": "pdf", "status": "ready"},
    "RPT-002": {"id": "RPT-002", "name": "User Access Review", "format": "excel", "status": "ready"},
    "RPT-003": {"id": "RPT-003", "name": "Certification Campaign Status", "format": "pdf", "status": "ready"},
    "RPT-004": {"id": "RPT-004", "name": "Firefighter Session Audit", "format": "excel", "status": "ready"},
    "RPT-005": {"id": "RPT-005", "name": "High-Risk Users Report", "format": "pdf", "status": "ready"},
    "RPT-006": {"id": "RPT-006", "name": "Access Request History", "format": "csv", "status": "ready"},
    "RPT-007": {"id": "RPT-007", "name": "Role Assignment Matrix", "format": "excel", "status": "ready"},
    "RPT-008": {"id": "RPT-008", "name": "Compliance Summary Report", "format": "pdf", "status": "ready"},
}


@router.post("/{report_id}/run")
async def run_report(report_id: str):
    """Trigger report generation"""
    if report_id not in MOCK_REPORTS:
        raise HTTPException(status_code=404, detail=f"Report {report_id} not found")

    report = MOCK_REPORTS[report_id]
    return {
        "success": True,
        "report_id": report_id,
        "name": report["name"],
        "status": "generating",
        "message": f"Report '{report['name']}' generation started",
        "started_at": datetime.now().isoformat()
    }


@router.get("/{report_id}/download")
async def download_report(report_id: str):
    """Download a report (returns mock PDF content for demo)"""
    if report_id not in MOCK_REPORTS:
        raise HTTPException(status_code=404, detail=f"Report {report_id} not found")

    report = MOCK_REPORTS[report_id]

    # For demo, return a simple text file with report info
    content = f"""
GRC Zero Trust Platform
========================
Report: {report['name']}
ID: {report_id}
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

This is a demo report. In production, this would contain the actual report data.

Report Summary:
- Format: {report['format'].upper()}
- Status: {report['status']}
"""

    # Return as downloadable content
    return JSONResponse(
        content={
            "success": True,
            "report_id": report_id,
            "filename": f"report-{report_id}.{report['format']}",
            "content": content,
            "message": "Report ready for download"
        }
    )


@router.get("/{report_id}")
async def get_report(report_id: str):
    """Get report details"""
    if report_id not in MOCK_REPORTS:
        raise HTTPException(status_code=404, detail=f"Report {report_id} not found")

    return MOCK_REPORTS[report_id]
