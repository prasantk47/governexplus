"""
Compliance Management API Router

Endpoints for regulatory frameworks, control objectives, and assessments.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime

from core.compliance import (
    ComplianceManager, ComplianceStatus, EvidenceType
)

router = APIRouter(tags=["Compliance"])

compliance_manager = ComplianceManager()


# Request Models
class CreateFrameworkRequest(BaseModel):
    name: str
    short_name: str
    description: str
    version: str = ""
    categories: List[str] = Field(default_factory=list)


class AddObjectiveRequest(BaseModel):
    reference_id: str
    name: str
    description: str
    category: str
    control_requirements: List[str] = Field(default_factory=list)
    is_key_control: bool = False
    risk_level: str = "medium"


class CreateAssessmentRequest(BaseModel):
    status: str
    score: float = Field(..., ge=0, le=100)
    findings: List[str] = Field(default_factory=list)
    gaps: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)


class AddEvidenceRequest(BaseModel):
    evidence_type: str
    name: str
    description: str
    reference: str
    valid_until: Optional[datetime] = None


# Framework Endpoints
@router.get("/frameworks")
async def list_frameworks(
    is_active: Optional[bool] = Query(None),
    region: Optional[str] = Query(None)
):
    """List compliance frameworks"""
    frameworks = compliance_manager.list_frameworks(is_active, region)
    return {"total": len(frameworks), "frameworks": [f.to_dict() for f in frameworks]}


@router.get("/frameworks/{framework_id}")
async def get_framework(framework_id: str):
    """Get framework details"""
    framework = compliance_manager.get_framework(framework_id)
    if not framework:
        raise HTTPException(status_code=404, detail="Framework not found")
    return framework.to_dict()


@router.get("/frameworks/{framework_id}/status")
async def get_framework_status(framework_id: str):
    """Get detailed compliance status for a framework"""
    try:
        return compliance_manager.get_framework_status(framework_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/frameworks")
async def create_framework(request: CreateFrameworkRequest):
    """Create a new framework"""
    framework = compliance_manager.create_framework(
        name=request.name,
        short_name=request.short_name,
        description=request.description,
        version=request.version,
        categories=request.categories
    )
    return framework.to_dict()


# Objective Endpoints
@router.get("/objectives")
async def list_objectives(
    framework_id: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    key_controls_only: bool = Query(default=False)
):
    """List control objectives"""
    status_enum = ComplianceStatus(status) if status else None
    objectives = compliance_manager.list_objectives(
        framework_id, category, status_enum, key_controls_only
    )
    return {"total": len(objectives), "objectives": [o.to_dict() for o in objectives]}


@router.get("/objectives/{objective_id}")
async def get_objective(objective_id: str):
    """Get objective details"""
    objective = compliance_manager.get_objective(objective_id)
    if not objective:
        raise HTTPException(status_code=404, detail="Objective not found")
    return objective.to_dict()


@router.post("/frameworks/{framework_id}/objectives")
async def add_objective(framework_id: str, request: AddObjectiveRequest):
    """Add a control objective to a framework"""
    try:
        objective = compliance_manager.add_objective(
            framework_id=framework_id,
            reference_id=request.reference_id,
            name=request.name,
            description=request.description,
            category=request.category,
            control_requirements=request.control_requirements,
            is_key_control=request.is_key_control,
            risk_level=request.risk_level
        )
        return objective.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/objectives/{objective_id}/map-control")
async def map_control(objective_id: str, control_id: str = Query(...)):
    """Map a GRC control to an objective"""
    try:
        objective = compliance_manager.map_control_to_objective(objective_id, control_id)
        return objective.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# Assessment Endpoints
@router.post("/objectives/{objective_id}/assessments")
async def create_assessment(
    objective_id: str,
    request: CreateAssessmentRequest,
    assessed_by: str = Query(...)
):
    """Create a compliance assessment"""
    try:
        status_enum = ComplianceStatus(request.status)
        assessment = compliance_manager.create_assessment(
            objective_id=objective_id,
            assessed_by=assessed_by,
            status=status_enum,
            score=request.score,
            findings=request.findings,
            gaps=request.gaps,
            recommendations=request.recommendations
        )
        return assessment.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/assessments/{assessment_id}/evidence")
async def add_evidence(
    assessment_id: str,
    request: AddEvidenceRequest,
    collected_by: str = Query(...)
):
    """Add evidence to an assessment"""
    try:
        evidence_type = EvidenceType(request.evidence_type)
        evidence = compliance_manager.add_evidence(
            assessment_id=assessment_id,
            evidence_type=evidence_type,
            name=request.name,
            description=request.description,
            reference=request.reference,
            collected_by=collected_by,
            valid_until=request.valid_until
        )
        return evidence.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/assessments/{assessment_id}/review")
async def review_assessment(
    assessment_id: str,
    reviewed_by: str = Query(...),
    comments: str = Query(default="")
):
    """Review an assessment"""
    try:
        assessment = compliance_manager.review_assessment(assessment_id, reviewed_by, comments)
        return assessment.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# Dashboard & Reports
@router.get("/dashboard")
async def get_compliance_dashboard():
    """Get compliance dashboard"""
    return compliance_manager.get_compliance_dashboard()


@router.get("/pending-assessments")
async def get_pending_assessments():
    """Get objectives due for assessment"""
    return compliance_manager.get_pending_assessments()


@router.get("/statistics")
async def get_compliance_statistics():
    """Get compliance statistics"""
    return compliance_manager.get_statistics()
