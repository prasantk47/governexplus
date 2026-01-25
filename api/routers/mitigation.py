"""
Mitigation Controls API Router

Endpoints for managing compensating controls and risk mitigation.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime

from core.mitigation import (
    MitigationManager, ControlType, ControlStatus
)

router = APIRouter(tags=["Mitigation Controls"])

# Initialize manager
mitigation_manager = MitigationManager()


# =============================================================================
# Request Models
# =============================================================================

class CreateControlRequest(BaseModel):
    name: str = Field(..., min_length=3)
    description: str
    control_type: str = Field(default="detective")
    control_objective: str = ""
    control_activity: str = ""
    frequency: str = "quarterly"
    responsible_role: str = ""
    owner_id: str = ""
    owner_name: str = ""
    risk_reduction_percentage: float = Field(default=50.0, ge=0, le=100)
    automation_level: str = "manual"
    evidence_requirements: List[str] = Field(default_factory=list)
    compliance_frameworks: List[str] = Field(default_factory=list)


class AssignControlRequest(BaseModel):
    control_id: str
    risk_id: str
    target_type: str = Field(..., description="user, role, or org_unit")
    target_id: str
    target_name: str
    justification: str
    valid_from: Optional[datetime] = None
    valid_to: Optional[datetime] = None
    monitor_id: str = ""
    monitor_name: str = ""
    requires_approval: bool = True


class RecordEffectivenessRequest(BaseModel):
    score: float = Field(..., ge=0, le=100)
    test_method: str
    findings: List[str] = Field(default_factory=list)
    evidence_references: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)


class CreateAttestationRequest(BaseModel):
    attester_id: str
    attester_name: str
    status: str = "attested"
    comments: str = ""
    evidence_attached: bool = False
    evidence_description: str = ""


class RecordMonitoringRequest(BaseModel):
    is_effective: bool
    notes: str = ""


# =============================================================================
# Control CRUD Endpoints
# =============================================================================

@router.post("/controls")
async def create_control(
    request: CreateControlRequest,
    created_by: str = Query(...)
):
    """Create a new mitigation control"""
    try:
        control_type = ControlType(request.control_type)
    except ValueError:
        control_type = ControlType.DETECTIVE

    control = mitigation_manager.create_control(
        name=request.name,
        description=request.description,
        control_type=control_type,
        created_by=created_by,
        control_objective=request.control_objective,
        control_activity=request.control_activity,
        frequency=request.frequency,
        responsible_role=request.responsible_role,
        owner_id=request.owner_id,
        owner_name=request.owner_name,
        risk_reduction_percentage=request.risk_reduction_percentage,
        automation_level=request.automation_level,
        evidence_requirements=request.evidence_requirements,
        compliance_frameworks=request.compliance_frameworks
    )

    return control.to_dict()


@router.get("/controls")
async def list_controls(
    control_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    risk_id: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    search: Optional[str] = Query(None)
):
    """List controls with filters"""
    type_enum = None
    if control_type:
        try:
            type_enum = ControlType(control_type)
        except ValueError:
            pass

    status_enum = None
    if status:
        try:
            status_enum = ControlStatus(status)
        except ValueError:
            pass

    controls = mitigation_manager.list_controls(
        control_type=type_enum,
        status=status_enum,
        risk_id=risk_id,
        category=category,
        search=search
    )

    return {
        "total": len(controls),
        "controls": [c.to_dict() for c in controls]
    }


@router.get("/controls/{control_id}")
async def get_control(control_id: str):
    """Get a control by ID"""
    control = mitigation_manager.get_control(control_id)
    if not control:
        raise HTTPException(status_code=404, detail=f"Control {control_id} not found")
    return control.to_dict()


@router.put("/controls/{control_id}")
async def update_control(
    control_id: str,
    modified_by: str = Query(...),
    name: Optional[str] = None,
    description: Optional[str] = None,
    control_objective: Optional[str] = None,
    frequency: Optional[str] = None,
    risk_reduction_percentage: Optional[float] = None
):
    """Update a control"""
    updates = {}
    if name:
        updates["name"] = name
    if description:
        updates["description"] = description
    if control_objective:
        updates["control_objective"] = control_objective
    if frequency:
        updates["frequency"] = frequency
    if risk_reduction_percentage is not None:
        updates["risk_reduction_percentage"] = risk_reduction_percentage

    try:
        control = mitigation_manager.update_control(control_id, modified_by, **updates)
        return control.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/controls/{control_id}/approve")
async def approve_control(
    control_id: str,
    approved_by: str = Query(...)
):
    """Approve a control"""
    try:
        control = mitigation_manager.approve_control(control_id, approved_by)
        return control.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/controls/{control_id}/deprecate")
async def deprecate_control(
    control_id: str,
    deprecated_by: str = Query(...),
    reason: str = Query(default="")
):
    """Deprecate a control"""
    try:
        control = mitigation_manager.deprecate_control(control_id, deprecated_by, reason)
        return control.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/controls/types")
async def list_control_types():
    """List available control types"""
    return {
        "types": [
            {"value": t.value, "name": t.name, "description": _get_type_description(t)}
            for t in ControlType
        ]
    }


def _get_type_description(t: ControlType) -> str:
    descriptions = {
        ControlType.DETECTIVE: "Detects issues after they occur",
        ControlType.PREVENTIVE: "Prevents issues from occurring",
        ControlType.CORRECTIVE: "Corrects issues after detection",
        ControlType.MONITORING: "Continuous monitoring",
        ControlType.REVIEW: "Periodic review",
        ControlType.APPROVAL: "Approval-based control",
        ControlType.AUTOMATED: "System-enforced control"
    }
    return descriptions.get(t, "")


# =============================================================================
# Control Assignment Endpoints
# =============================================================================

@router.post("/assignments")
async def assign_control(
    request: AssignControlRequest,
    assigned_by: str = Query(...)
):
    """Assign a control to mitigate a risk"""
    try:
        assignment = mitigation_manager.assign_control(
            control_id=request.control_id,
            risk_id=request.risk_id,
            target_type=request.target_type,
            target_id=request.target_id,
            target_name=request.target_name,
            assigned_by=assigned_by,
            justification=request.justification,
            valid_from=request.valid_from,
            valid_to=request.valid_to,
            monitor_id=request.monitor_id,
            monitor_name=request.monitor_name,
            requires_approval=request.requires_approval
        )
        return assignment.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/assignments/{assignment_id}/approve")
async def approve_assignment(
    assignment_id: str,
    approved_by: str = Query(...),
    comments: str = Query(default="")
):
    """Approve a control assignment"""
    try:
        assignment = mitigation_manager.approve_assignment(assignment_id, approved_by, comments)
        return assignment.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/assignments/{assignment_id}/revoke")
async def revoke_assignment(
    assignment_id: str,
    revoked_by: str = Query(...),
    reason: str = Query(default="")
):
    """Revoke a control assignment"""
    try:
        assignment = mitigation_manager.revoke_assignment(assignment_id, revoked_by, reason)
        return assignment.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/assignments/user/{user_id}")
async def get_user_assignments(
    user_id: str,
    include_expired: bool = Query(default=False)
):
    """Get control assignments for a user"""
    assignments = mitigation_manager.get_user_assignments(user_id, include_expired)
    return {
        "user_id": user_id,
        "total": len(assignments),
        "assignments": [a.to_dict() for a in assignments]
    }


@router.get("/assignments/risk/{risk_id}")
async def get_risk_mitigations(
    risk_id: str,
    include_expired: bool = Query(default=False)
):
    """Get mitigation controls for a specific risk"""
    mitigations = mitigation_manager.get_risk_mitigations(risk_id, include_expired)
    return {
        "risk_id": risk_id,
        "total": len(mitigations),
        "mitigations": mitigations
    }


@router.get("/assignments/check-mitigation")
async def check_risk_mitigation(
    risk_id: str = Query(...),
    target_id: str = Query(...),
    target_type: str = Query(default="user")
):
    """Check if a risk is mitigated for a target"""
    result = mitigation_manager.is_risk_mitigated(risk_id, target_id, target_type)
    return result


# =============================================================================
# Effectiveness Testing Endpoints
# =============================================================================

@router.post("/controls/{control_id}/effectiveness")
async def record_effectiveness_test(
    control_id: str,
    request: RecordEffectivenessRequest,
    tested_by: str = Query(...)
):
    """Record an effectiveness test for a control"""
    try:
        effectiveness = mitigation_manager.record_effectiveness_test(
            control_id=control_id,
            tested_by=tested_by,
            score=request.score,
            test_method=request.test_method,
            findings=request.findings,
            evidence_references=request.evidence_references,
            recommendations=request.recommendations
        )
        return effectiveness.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/controls/{control_id}/effectiveness/trend")
async def get_effectiveness_trend(control_id: str):
    """Get effectiveness trend for a control"""
    try:
        return mitigation_manager.get_effectiveness_trend(control_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# =============================================================================
# Attestation Endpoints
# =============================================================================

@router.post("/assignments/{assignment_id}/attest")
async def create_attestation(
    assignment_id: str,
    request: CreateAttestationRequest
):
    """Create an attestation for an assignment"""
    try:
        attestation = mitigation_manager.create_attestation(
            assignment_id=assignment_id,
            attester_id=request.attester_id,
            attester_name=request.attester_name,
            status=request.status,
            comments=request.comments,
            evidence_attached=request.evidence_attached,
            evidence_description=request.evidence_description
        )
        return attestation.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/attestations/pending")
async def get_pending_attestations(
    attester_id: Optional[str] = Query(None)
):
    """Get pending attestations"""
    pending = mitigation_manager.get_pending_attestations(attester_id)
    return {
        "total": len(pending),
        "pending": pending
    }


@router.get("/attestations/summary")
async def get_attestation_summary():
    """Get attestation summary"""
    return mitigation_manager.get_attestation_summary()


# =============================================================================
# Monitoring Endpoints
# =============================================================================

@router.post("/assignments/{assignment_id}/monitor")
async def record_monitoring(
    assignment_id: str,
    request: RecordMonitoringRequest,
    monitored_by: str = Query(...)
):
    """Record monitoring activity"""
    try:
        assignment = mitigation_manager.record_monitoring(
            assignment_id=assignment_id,
            monitored_by=monitored_by,
            is_effective=request.is_effective,
            notes=request.notes
        )
        return assignment.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/monitoring/schedule")
async def get_monitoring_schedule():
    """Get upcoming monitoring schedule"""
    return mitigation_manager.get_monitoring_schedule()


# =============================================================================
# Recommendations & Reports
# =============================================================================

@router.get("/recommend/{risk_id}")
async def recommend_controls(risk_id: str):
    """Get recommended controls for a risk"""
    recommendations = mitigation_manager.recommend_controls(risk_id)
    return {
        "risk_id": risk_id,
        "recommendations": recommendations
    }


@router.get("/coverage")
async def get_control_coverage():
    """Get control coverage report"""
    return mitigation_manager.get_control_coverage_report()


@router.get("/statistics")
async def get_mitigation_statistics():
    """Get mitigation control statistics"""
    return mitigation_manager.get_statistics()
