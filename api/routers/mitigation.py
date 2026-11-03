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
    # Organizational scope
    applicable_countries: List[str] = Field(default_factory=list, description="ISO country codes: IN, SG, DE, US, AE")
    applicable_company_codes: List[str] = Field(default_factory=list, description="SAP company codes: 1000, 2000")
    applicable_plants: List[str] = Field(default_factory=list)
    applicable_org_units: List[str] = Field(default_factory=list)
    scope_model: str = Field(default="global", description="global, country, company_code, local")


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
    # Organizational scope for this assignment
    company_codes: List[str] = Field(default_factory=list, description="Company codes this assignment covers")
    country: str = Field(default="", description="ISO country code")
    plant: str = ""
    org_unit: str = ""
    scope_description: str = Field(default="", description="e.g. India Manufacturing Finance Team")


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
        control_type = request.control_type
    except ValueError:
        control_type = "detective"

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
        compliance_frameworks=request.compliance_frameworks,
        applicable_countries=request.applicable_countries,
        applicable_company_codes=request.applicable_company_codes,
        applicable_plants=request.applicable_plants,
        applicable_org_units=request.applicable_org_units,
        scope_model=request.scope_model
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
            type_enum = control_type
        except ValueError:
            pass

    status_enum = None
    if status:
        try:
            status_enum = status
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
        "detective": "Detects issues after they occur",
        "preventive": "Prevents issues from occurring",
        "corrective": "Corrects issues after detection",
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
            requires_approval=request.requires_approval,
            company_codes=request.company_codes,
            country=request.country,
            plant=request.plant,
            org_unit=request.org_unit,
            scope_description=request.scope_description
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


# =============================================================================
# Monitor Inbox — alerts for assigned Control Monitors
# =============================================================================

@router.get("/monitor-inbox")
async def get_monitor_inbox(
    monitor_id: str = Query(..., description="User ID of the control monitor"),
    acknowledged: Optional[bool] = Query(None),
    alert_type: Optional[str] = Query(None),
    severity: Optional[str] = Query(None)
):
    """Get alerts for a specific control monitor (Monitor Inbox).

    A Control Monitor is the person assigned to review evidence when a user
    executes a transaction that is part of a mitigated SoD conflict.
    """
    return mitigation_manager.get_monitor_inbox(
        monitor_id=monitor_id,
        acknowledged=acknowledged,
        alert_type=alert_type,
        severity=severity
    )


@router.post("/monitor-inbox/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: str,
    acknowledged_by: str = Query(...),
    resolution_action: str = Query("reviewed", description="reviewed, escalated, false_positive"),
    resolution_notes: str = Query("")
):
    """Acknowledge an alert in the monitor inbox."""
    return mitigation_manager.acknowledge_alert(
        alert_id=alert_id,
        acknowledged_by=acknowledged_by,
        resolution_action=resolution_action,
        resolution_notes=resolution_notes
    )


@router.get("/monitor-inbox/summary")
async def get_monitor_inbox_summary(
    monitor_id: str = Query(..., description="User ID of the control monitor")
):
    """Get summary counts for a monitor's inbox."""
    return mitigation_manager.get_monitor_inbox_summary(monitor_id)


@router.post("/alerts/trigger-risk-execution")
async def trigger_risk_execution_alert(
    user_id: str = Query(..., description="User who executed the risky transaction"),
    user_name: str = Query(""),
    risk_id: str = Query(..., description="SoD risk ID that was triggered"),
    transaction_code: str = Query("", description="Transaction executed"),
    company_code: str = Query(""),
    system_id: str = Query("")
):
    """Called when a user executes a transaction covered by a mitigated SoD conflict.

    Finds the assigned Control Monitor for the user+risk combination and
    generates an alert in their Monitor Inbox.
    """
    return mitigation_manager.create_risk_execution_alert(
        user_id=user_id,
        user_name=user_name,
        risk_id=risk_id,
        transaction_code=transaction_code,
        company_code=company_code,
        system_id=system_id
    )
