"""
Firefighter API Router

Endpoints for emergency access management (Firefighter/EAM functionality).
Implements the complete Firefighter workflow:
- Request with Reason Codes
- Multi-level Approval with SLAs
- Session Management with Extensions
- Controller Review with SLA tracking
- Audit Evidence Export
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime, timedelta
import io

from core.firefighter import (
    FirefighterManager,
    FirefighterRequest,
    FirefighterSession,
    ReasonCode,
    REASON_CODE_CATALOG,
    RequestPriority,
    SessionStatus,
    ReviewStatus
)
from connectors.sap.mock_connector import SAPMockConnector
from connectors.base import ConnectionConfig, ConnectionType

router = APIRouter(tags=["Firefighter"])

# Initialize mock SAP connector
mock_config = ConnectionConfig(
    name="SAP_DEV",
    connection_type=ConnectionType.RFC,
    host="mock.sap.local",
    sap_client="100"
)
sap_connector = SAPMockConnector(mock_config)
sap_connector.connect()

# Initialize firefighter manager
ff_manager = FirefighterManager(sap_connector=sap_connector)


# =============================================================================
# Request/Response Models
# =============================================================================

class FirefighterRequestCreate(BaseModel):
    """Request to create a new firefighter access request with structured reason code"""
    requester_user_id: str = Field(..., example="JSMITH")
    requester_name: str = Field(..., example="John Smith")
    requester_email: str = Field(..., example="john.smith@company.com")
    target_system: str = Field(..., example="SAP_PROD")
    firefighter_id: str = Field(..., example="FF_EMERGENCY_01")

    # Reason Code (structured)
    reason_code: str = Field(..., example="prod_incident",
                            description="Reason code from catalog: prod_incident, change_management, audit_request, etc.")
    reason: Optional[str] = Field("", example="Critical production issue - payroll calculation error",
                                  description="Additional description")
    planned_actions: Optional[List[str]] = Field(default_factory=list,
                                                  example=["Run PA30 for employee updates", "Check BTCI logs"],
                                                  description="List of planned actions during session")
    business_justification: Optional[str] = Field("", example="Month-end payroll run failed, need to investigate and fix")

    # Timing and priority
    duration_hours: Optional[float] = Field(default=2, ge=0.5, le=8)
    priority: Optional[str] = Field(default=None, example="high",
                                   description="Override priority (defaults from reason code)")
    ticket_reference: Optional[str] = Field(None, example="INC0012345")


class FirefighterApproval(BaseModel):
    """Approval action for a firefighter request"""
    approver_id: str = Field(..., example="security.admin")
    comments: Optional[str] = Field(None, example="Approved for emergency fix")


class FirefighterRejection(BaseModel):
    """Rejection action for a firefighter request"""
    approver_id: str = Field(..., example="security.admin")
    reason: str = Field(..., example="Insufficient justification")


class ActivityLogEntry(BaseModel):
    """Log an activity during firefighter session"""
    action_type: str = Field(..., example="TCODE_EXECUTE")
    transaction_code: Optional[str] = Field(None, example="PA30")
    details: Optional[Dict] = Field(default_factory=dict)
    client_ip: Optional[str] = None


class SessionReview(BaseModel):
    """Review submission for completed session"""
    reviewer_id: str
    approved: bool
    comments: str


class SessionExtensionRequest(BaseModel):
    """Request to extend an active session"""
    requested_by: str = Field(..., example="JSMITH")
    extension_minutes: int = Field(..., ge=15, le=120, example=60)
    reason: str = Field(..., example="Need additional time to complete debugging")
    approved_by: Optional[str] = Field(None, example="security.admin")


class ControllerReviewStart(BaseModel):
    """Start controller review"""
    controller_id: str = Field(..., example="controller1")


class ControllerReviewComplete(BaseModel):
    """Complete controller review"""
    controller_id: str = Field(..., example="controller1")
    approved: bool = Field(..., example=True)
    findings: List[str] = Field(default_factory=list, example=["No anomalies detected"])
    comments: str = Field(..., example="All activities reviewed and approved")
    flagged_activities: Optional[List[str]] = Field(default_factory=list)


# =============================================================================
# Reason Code Endpoints
# =============================================================================

@router.get("/reason-codes")
async def get_reason_codes():
    """
    Get all available reason codes with their configurations.

    Returns the complete reason code catalog including:
    - Required fields for each code
    - Default priority and max duration
    - Approval chain requirements
    - SLA information
    """
    return {
        'reason_codes': FirefighterManager.get_reason_codes()
    }


@router.get("/reason-codes/{code}")
async def get_reason_code(code: str):
    """
    Get configuration for a specific reason code.
    """
    try:
        reason_code = ReasonCode(code)
        config = REASON_CODE_CATALOG.get(reason_code)
        if not config:
            raise HTTPException(status_code=404, detail=f"Reason code '{code}' not found")
        return config.to_dict()
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid reason code: {code}")


# =============================================================================
# Request Management Endpoints
# =============================================================================

@router.post("/requests", status_code=201)
async def create_firefighter_request(request: FirefighterRequestCreate):
    """
    Submit a new firefighter access request with structured reason code.

    The request will be routed through the approval workflow based on:
    - Reason code configuration (approval chain, SLAs)
    - Target system
    - Risk assessment

    Reason codes determine required fields, default priority, and approval routing.
    """
    try:
        # Map reason code string to enum
        try:
            reason_code = ReasonCode(request.reason_code)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid reason code: {request.reason_code}. "
                       f"Valid codes: {[rc.value for rc in ReasonCode]}"
            )

        # Map priority string to enum if provided
        priority = None
        if request.priority:
            priority_map = {
                'low': RequestPriority.LOW,
                'medium': RequestPriority.MEDIUM,
                'high': RequestPriority.HIGH,
                'critical': RequestPriority.CRITICAL
            }
            priority = priority_map.get(request.priority.lower())

        ff_request = await ff_manager.submit_request(
            requester_user_id=request.requester_user_id,
            requester_name=request.requester_name,
            requester_email=request.requester_email,
            target_system=request.target_system,
            firefighter_id=request.firefighter_id,
            reason_code=reason_code,
            reason=request.reason or "",
            business_justification=request.business_justification or "",
            planned_actions=request.planned_actions or [],
            duration=timedelta(hours=request.duration_hours),
            priority=priority,
            ticket_reference=request.ticket_reference
        )

        return {
            'request_id': ff_request.request_id,
            'status': ff_request.status.value,
            'reason_code': ff_request.reason_code.value,
            'reason_code_label': REASON_CODE_CATALOG[ff_request.reason_code].label,
            'risk_score': ff_request.risk_score,
            'requires_dual_approval': ff_request.requires_dual_approval,
            'approval_chain': ff_request.approval_chain,
            'approvers': ff_request.approvers,
            'approval_sla': ff_request.approval_sla.isoformat() if ff_request.approval_sla else None,
            'message': 'Request submitted successfully. Awaiting approval.'
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to submit request: {str(e)}")


@router.get("/requests")
async def list_requests(
    status: Optional[str] = Query(None, description="Filter by status"),
    requester: Optional[str] = Query(None, description="Filter by requester")
):
    """
    List firefighter requests.
    """
    requests = []

    for req in ff_manager.requests.values():
        if status and req.status.value != status:
            continue
        if requester and req.requester_user_id != requester:
            continue
        requests.append(req.to_dict())

    return {
        'total': len(requests),
        'requests': requests
    }


@router.get("/requests/pending")
async def get_pending_requests():
    """
    Get all requests pending approval.
    """
    return {
        'pending_requests': ff_manager.get_pending_requests()
    }


@router.get("/requests/{request_id}")
async def get_request(request_id: str):
    """
    Get details of a specific firefighter request.
    """
    request = ff_manager.get_request(request_id)
    if not request:
        raise HTTPException(status_code=404, detail=f"Request {request_id} not found")

    return request.to_dict()


@router.post("/requests/{request_id}/approve")
async def approve_request(request_id: str, approval: FirefighterApproval):
    """
    Approve a firefighter request.

    Upon approval, a firefighter session is created and the requester
    can retrieve credentials.
    """
    try:
        session = await ff_manager.approve_request(
            request_id=request_id,
            approver_id=approval.approver_id,
            comments=approval.comments
        )

        return {
            'message': 'Request approved',
            'session_id': session.session_id,
            'firefighter_id': session.firefighter_id,
            'valid_until': session.end_time.isoformat(),
            'status': session.status.value
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.post("/requests/{request_id}/reject")
async def reject_request(request_id: str, rejection: FirefighterRejection):
    """
    Reject a firefighter request.
    """
    try:
        request = await ff_manager.reject_request(
            request_id=request_id,
            approver_id=rejection.approver_id,
            reason=rejection.reason
        )

        return {
            'message': 'Request rejected',
            'request_id': request.request_id,
            'status': request.status.value,
            'rejection_reason': request.rejection_reason
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


# =============================================================================
# Session Management Endpoints
# =============================================================================

@router.get("/sessions")
async def list_sessions(
    status: Optional[str] = Query(None, description="Filter by status"),
    user_id: Optional[str] = Query(None, description="Filter by user")
):
    """
    List firefighter sessions.
    """
    sessions = []

    for session in ff_manager.sessions.values():
        if status and session.status.value != status:
            continue
        if user_id and session.requester_user_id != user_id:
            continue
        sessions.append(session.to_dict())

    return {
        'total': len(sessions),
        'sessions': sessions
    }


@router.get("/sessions/active")
async def get_active_sessions():
    """
    Get all currently active firefighter sessions.
    """
    return {
        'active_sessions': ff_manager.get_active_sessions()
    }


@router.get("/sessions/{session_id}")
async def get_session(session_id: str):
    """
    Get details of a specific firefighter session.
    """
    session = ff_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    return session.to_dict()


@router.get("/sessions/{session_id}/credentials")
async def get_session_credentials(
    session_id: str,
    user_id: str = Query(..., description="Requester user ID for verification")
):
    """
    Get credentials for an active firefighter session.

    Only the original requester can retrieve the credentials.
    """
    try:
        credentials = await ff_manager.get_session_credentials(session_id, user_id)
        return credentials

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.post("/sessions/{session_id}/activity")
async def log_session_activity(session_id: str, activity: ActivityLogEntry):
    """
    Log an activity performed during a firefighter session.

    This should be called for each significant action performed.
    """
    try:
        log = await ff_manager.log_activity(
            session_id=session_id,
            action_type=activity.action_type,
            action_details={
                'tcode': activity.transaction_code,
                **activity.details
            },
            client_ip=activity.client_ip
        )

        return {
            'logged': True,
            'activity_id': log.log_id,
            'is_sensitive': log.is_sensitive,
            'requires_review': log.requires_review
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/sessions/{session_id}/activities")
async def get_session_activities(session_id: str):
    """
    Get all logged activities for a firefighter session.
    """
    try:
        activities = await ff_manager.get_session_activities(session_id)
        return {
            'session_id': session_id,
            'activity_count': len(activities),
            'activities': activities
        }

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/sessions/{session_id}/end")
async def end_session(
    session_id: str,
    user_id: str = Query(..., description="User ending the session")
):
    """
    End an active firefighter session.

    This will lock the firefighter ID and trigger the review workflow.
    """
    try:
        session = await ff_manager.end_session(
            session_id=session_id,
            ended_by=user_id,
            reason="Normal completion"
        )

        return {
            'message': 'Session ended successfully',
            'session_id': session.session_id,
            'status': session.status.value,
            'activity_count': session.activity_count,
            'requires_review': session.requires_review
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/sessions/{session_id}/revoke")
async def revoke_session(
    session_id: str,
    revoked_by: str = Query(..., description="User revoking the session"),
    reason: str = Query(..., description="Reason for revocation")
):
    """
    Forcefully revoke/terminate a firefighter session.

    This is used for emergency situations or policy violations.
    """
    try:
        session = await ff_manager.revoke_session(
            session_id=session_id,
            revoked_by=revoked_by,
            reason=reason
        )

        return {
            'message': 'Session revoked',
            'session_id': session.session_id,
            'status': session.status.value,
            'revocation_reason': reason
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# =============================================================================
# Review Endpoints
# =============================================================================

@router.get("/reviews/pending")
async def get_pending_reviews(
    reviewer_id: str = Query(..., description="Reviewer user ID")
):
    """
    Get sessions pending review for a reviewer.
    """
    reviews = await ff_manager.get_pending_reviews(reviewer_id)
    return {
        'pending_count': len(reviews),
        'sessions': reviews
    }


@router.post("/sessions/{session_id}/review")
async def submit_review(session_id: str, review: SessionReview):
    """
    Submit a review for a completed firefighter session.
    """
    try:
        session = await ff_manager.submit_review(
            session_id=session_id,
            reviewer_id=review.reviewer_id,
            approved=review.approved,
            comments=review.comments
        )

        return {
            'message': 'Review submitted',
            'session_id': session.session_id,
            'review_status': 'approved' if review.approved else 'flagged'
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# =============================================================================
# Firefighter ID Management
# =============================================================================

@router.get("/firefighters")
async def list_firefighter_ids():
    """
    List available firefighter IDs and their status.
    """
    # In production, this would come from configuration
    firefighter_ids = ['FF_EMERGENCY_01', 'FF_EMERGENCY_02', 'FF_BASIS_01']

    results = []
    for ff_id in firefighter_ids:
        status = sap_connector.check_firefighter_availability(ff_id)
        results.append({
            'firefighter_id': ff_id,
            **status
        })

    return {
        'firefighter_ids': results
    }


@router.get("/firefighters/{firefighter_id}/status")
async def check_firefighter_status(firefighter_id: str):
    """
    Check the availability status of a firefighter ID.
    """
    status = sap_connector.check_firefighter_availability(firefighter_id)
    return status


# =============================================================================
# Session Extension
# =============================================================================

@router.post("/sessions/{session_id}/extend")
async def extend_session(session_id: str, extension: SessionExtensionRequest):
    """
    Extend an active firefighter session.

    Sessions can be extended up to a maximum number of times (default: 2).
    Each extension is logged and tracked for audit purposes.
    """
    try:
        session = await ff_manager.extend_session(
            session_id=session_id,
            requested_by=extension.requested_by,
            extension_minutes=extension.extension_minutes,
            reason=extension.reason,
            approved_by=extension.approved_by
        )

        return {
            'message': f'Session extended by {extension.extension_minutes} minutes',
            'session_id': session.session_id,
            'new_end_time': session.end_time.isoformat(),
            'extension_count': session.extension_count,
            'can_extend_again': session.can_extend(),
            'remaining_extensions': session.max_extensions - session.extension_count
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# =============================================================================
# Controller Review Management
# =============================================================================

@router.post("/sessions/{session_id}/controller-review/start")
async def start_controller_review(session_id: str, data: ControllerReviewStart):
    """
    Mark a controller review as in progress.

    Called when the controller begins reviewing the session activities.
    """
    try:
        review = await ff_manager.start_controller_review(
            session_id=session_id,
            controller_id=data.controller_id
        )

        return {
            'message': 'Controller review started',
            'session_id': session_id,
            'review_status': review.status.value,
            'started_at': review.started_at.isoformat() if review.started_at else None,
            'sla_deadline': review.sla_deadline.isoformat() if review.sla_deadline else None
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.post("/sessions/{session_id}/controller-review/complete")
async def complete_controller_review(session_id: str, data: ControllerReviewComplete):
    """
    Complete controller review for a session.

    The controller submits their findings, approval status, and any flagged activities.
    Flagged sessions are escalated to security.
    """
    try:
        review = await ff_manager.complete_controller_review(
            session_id=session_id,
            controller_id=data.controller_id,
            approved=data.approved,
            findings=data.findings,
            comments=data.comments,
            flagged_activities=data.flagged_activities
        )

        return {
            'message': 'Controller review completed',
            'session_id': session_id,
            'review_status': review.status.value,
            'approved': review.approved,
            'completed_at': review.completed_at.isoformat() if review.completed_at else None,
            'findings_count': len(review.findings),
            'flagged_activities_count': len(review.flagged_activities)
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.get("/sessions/{session_id}/controller-review")
async def get_controller_review(session_id: str):
    """
    Get controller review status and details for a session.
    """
    session = ff_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    if not session.controller_review:
        return {
            'session_id': session_id,
            'review_assigned': False,
            'message': 'No controller review assigned yet'
        }

    return {
        'session_id': session_id,
        'review_assigned': True,
        **session.controller_review.to_dict()
    }


# =============================================================================
# Audit Evidence Export
# =============================================================================

@router.get("/sessions/{session_id}/audit-evidence")
async def get_audit_evidence(session_id: str):
    """
    Generate comprehensive audit evidence package for a session.

    Returns complete audit trail including:
    - Request and approval details
    - Session timeline
    - All activities with timestamps
    - Controller review results
    - Integrity hash for evidence verification
    """
    try:
        evidence = await ff_manager.generate_audit_evidence(session_id)
        return evidence

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/sessions/{session_id}/audit-evidence/export")
async def export_audit_evidence(
    session_id: str,
    format: str = Query(default="json", description="Export format: json, csv, pdf_data")
):
    """
    Export audit evidence in specified format.

    Formats:
    - json: Complete evidence package as JSON
    - csv: Activity log as CSV file
    - pdf_data: Structured data for PDF generation
    """
    try:
        export = await ff_manager.export_audit_evidence(session_id, format)

        if format == 'csv':
            # Return as downloadable CSV
            return StreamingResponse(
                io.StringIO(export['content']),
                media_type='text/csv',
                headers={
                    'Content-Disposition': f'attachment; filename="{export["filename"]}"'
                }
            )
        elif format == 'json':
            # Return as downloadable JSON
            return StreamingResponse(
                io.StringIO(export['content']),
                media_type='application/json',
                headers={
                    'Content-Disposition': f'attachment; filename="{export["filename"]}"'
                }
            )
        else:
            return export

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/audit/sessions")
async def get_sessions_for_audit(
    start_date: Optional[str] = Query(None, description="Filter by start date (ISO format)"),
    end_date: Optional[str] = Query(None, description="Filter by end date (ISO format)"),
    status: Optional[str] = Query(None, description="Filter by status"),
    firefighter_id: Optional[str] = Query(None, description="Filter by firefighter ID")
):
    """
    Get sessions matching audit criteria.

    Used for compliance reporting and audit preparation.
    """
    try:
        # Parse dates
        start = datetime.fromisoformat(start_date) if start_date else None
        end = datetime.fromisoformat(end_date) if end_date else None

        # Parse status
        session_status = None
        if status:
            session_status = SessionStatus(status)

        sessions = await ff_manager.get_sessions_for_audit(
            start_date=start,
            end_date=end,
            status=session_status,
            firefighter_id=firefighter_id
        )

        return {
            'total': len(sessions),
            'filters': {
                'start_date': start_date,
                'end_date': end_date,
                'status': status,
                'firefighter_id': firefighter_id
            },
            'sessions': sessions
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# =============================================================================
# Statistics
# =============================================================================

@router.get("/statistics")
async def get_firefighter_statistics():
    """
    Get firefighter system statistics.
    """
    return ff_manager.get_statistics()
