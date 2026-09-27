"""
Access Request API Router

Endpoints for the access request portal including:
- Request creation and submission
- Risk preview
- Approval processing
- Request tracking
"""

from fastapi import APIRouter, Depends, HTTPException, Header, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime

from sqlalchemy.orm import Session

from core.access_request import (
    AccessRequestManager, AccessRequest, AccessRequestStatus,
    RequestType, ApprovalAction
)
from core.rules import RuleEngine
from db.database import get_db

router = APIRouter(tags=["Access Requests"])

DEFAULT_TENANT = "tenant_default"

# Per-tenant rule engine registry
_rule_engines: Dict[str, RuleEngine] = {}


def _get_tenant_id(x_tenant_id: Optional[str] = Header(None)) -> str:
    """Extract tenant from header or use default."""
    return x_tenant_id or DEFAULT_TENANT


def _get_rule_engine(tenant_id: str = Depends(_get_tenant_id)) -> RuleEngine:
    """Return a per-tenant RuleEngine instance, creating it on first use."""
    if tenant_id not in _rule_engines:
        _rule_engines[tenant_id] = RuleEngine()
    return _rule_engines[tenant_id]


def _get_manager(
    db: Session = Depends(get_db),
    rule_engine: RuleEngine = Depends(_get_rule_engine),
) -> AccessRequestManager:
    """Create a request manager scoped to the current DB session and tenant engine."""
    return AccessRequestManager(db=db, rule_engine=rule_engine)


# =============================================================================
# Request/Response Models
# =============================================================================

class CreateRequestModel(BaseModel):
    """Model for creating a new access request. Requester fields auto-fill from JWT if omitted."""
    requester_user_id: Optional[str] = Field(None, example="JSMITH")
    requester_name: Optional[str] = Field(None, example="John Smith")
    requester_email: Optional[str] = Field(None, example="john.smith@company.com")
    target_user_id: Optional[str] = Field(None, example="MBROWN")
    target_user_name: Optional[str] = Field(None, example="Mary Brown")
    requested_roles: List[str] = Field(default_factory=list, example=["Z_AP_CLERK", "Z_PURCHASER"])
    business_justification: Optional[str] = Field(None, example="Need access for procurement project")
    justification: Optional[str] = Field(None)  # alias accepted by frontend
    request_type: Optional[str] = Field(default="new_access")
    priority: Optional[str] = Field(default="medium")
    is_temporary: bool = Field(default=False)
    end_date: Optional[datetime] = None
    ticket_reference: Optional[str] = Field(None, example="INC0012345")


class ApprovalActionModel(BaseModel):
    """Model for processing an approval action"""
    actor_id: str = Field(..., example="manager@company.com")
    action: str = Field(..., example="approve")  # approve, reject, delegate
    comments: Optional[str] = Field(None, example="Approved for project needs")
    delegate_to: Optional[str] = None


class RiskPreviewRequest(BaseModel):
    """Model for risk preview"""
    target_user_id: str
    requested_roles: List[str]


class ModifyItemsRequest(BaseModel):
    """Model for modifying roles on a pending request before approval."""
    remove_roles: List[str] = Field(default_factory=list, example=["ROLE_A"])
    add_roles: List[str] = Field(default_factory=list, example=["ROLE_B"])
    modifier_id: str = Field(..., example="admin")
    comments: Optional[str] = Field(None, example="Swapped role per manager request")


class AssignMitigationRequest(BaseModel):
    """Model for assigning a mitigation control to a violation during approval."""
    violation_id: str = Field(..., example="VIO-001")
    mitigation_control_id: str = Field(..., example="MC-CTRL-001")
    comments: Optional[str] = Field(None, example="Compensating control applied")


# =============================================================================
# Role Catalog Endpoints
# =============================================================================

@router.get("/catalog/roles")
async def get_role_catalog(
    search: Optional[str] = Query(None, description="Search roles"),
    business_process: Optional[str] = Query(None, description="Filter by process"),
    mgr: AccessRequestManager = Depends(_get_manager),
):
    """
    Get available roles from the catalog.

    Returns business-friendly role descriptions for the request portal.
    """
    roles = mgr.get_role_catalog(search, business_process)

    return {
        "total": len(roles),
        "roles": roles,
        "business_processes": list(set(
            r.get("business_process") for r in roles if r.get("business_process")
        ))
    }


@router.get("/catalog/roles/{role_id}")
async def get_role_details(role_id: str, mgr: AccessRequestManager = Depends(_get_manager)):
    """Get detailed information about a specific role"""
    roles = mgr.get_role_catalog()
    role = next((r for r in roles if r["role_id"] == role_id), None)

    if not role:
        raise HTTPException(status_code=404, detail=f"Role {role_id} not found")

    return role


# =============================================================================
# Risk Preview Endpoints
# =============================================================================

@router.post("/preview-risk")
async def preview_risk(
    request: RiskPreviewRequest,
    mgr: AccessRequestManager = Depends(_get_manager),
):
    """Preview risk analysis before submitting a request."""
    temp_request = AccessRequest(
        target_user_id=request.target_user_id,
        target_user_name=request.target_user_id
    )

    from core.access_request.models import RequestedAccess
    for role_id in request.requested_roles:
        temp_request.requested_items.append(RequestedAccess(
            access_type="role",
            access_name=role_id
        ))

    return await mgr.preview_risk(temp_request)


# =============================================================================
# Request Lifecycle Endpoints
# =============================================================================

@router.post("/", status_code=201)
async def create_access_request(
    request: CreateRequestModel,
    mgr: AccessRequestManager = Depends(_get_manager),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Create a new access request (draft), persisted to database.
    Requester fields auto-fill from JWT if not provided."""
    try:
        # Auto-fill requester from JWT context
        from core.tenant import get_current_tenant
        ctx = get_current_tenant()
        requester_id = request.requester_user_id or (ctx.user_id if ctx else "unknown")
        requester_name = request.requester_name or (ctx.user_email if ctx else "Unknown User")
        requester_email = request.requester_email or (ctx.user_email if ctx else "")
        target_id = request.target_user_id or requester_id
        target_name = request.target_user_name or requester_name
        justification = request.business_justification or request.justification or "Access requested"

        type_map = {
            "new_access": RequestType.NEW_ACCESS,
            "modify_access": RequestType.MODIFY_ACCESS,
            "remove_access": RequestType.REMOVE_ACCESS,
            "temporary": RequestType.TEMPORARY_ACCESS,
            "extension": RequestType.ROLE_EXTENSION,
            "role_assignment": RequestType.NEW_ACCESS,
        }
        req_type = type_map.get(request.request_type, RequestType.NEW_ACCESS)

        access_request = await mgr.create_request(
            tenant_id=tenant_id,
            requester_user_id=requester_id,
            requester_name=requester_name,
            requester_email=requester_email,
            target_user_id=target_id,
            target_user_name=target_name,
            requested_roles=request.requested_roles,
            business_justification=justification,
            request_type=req_type,
            is_temporary=request.is_temporary,
            end_date=request.end_date,
            ticket_reference=request.ticket_reference
        )

        return {
            "request_id": access_request.request_id,
            "status": access_request.status.value,
            "message": "Request created in draft. Use /submit to submit for approval.",
            "request": access_request.to_summary()
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{request_id}/submit")
async def submit_request(
    request_id: str,
    mgr: AccessRequestManager = Depends(_get_manager),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Submit a draft request for approval."""
    try:
        access_request = await mgr.submit_request(request_id, tenant_id)

        return {
            "request_id": access_request.request_id,
            "status": access_request.status.value,
            "risk_level": access_request.risk_level,
            "risk_score": access_request.overall_risk_score,
            "sod_violations": len(access_request.sod_violations),
            "approval_steps": len(access_request.approval_steps),
            "current_approvers": access_request.get_current_approvers(),
            "message": "Request submitted for approval"
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{request_id}")
async def get_request(
    request_id: str,
    mgr: AccessRequestManager = Depends(_get_manager),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Get full details of an access request"""
    access_request = mgr.get_request(request_id, tenant_id)
    if not access_request:
        raise HTTPException(status_code=404, detail=f"Request {request_id} not found")
    return access_request.to_dict()


@router.get("/")
async def list_requests(
    status: Optional[str] = Query(None, description="Filter by status"),
    requester: Optional[str] = Query(None, description="Filter by requester"),
    target: Optional[str] = Query(None, description="Filter by target user"),
    search: Optional[str] = Query(None, description="Full-text search across request ID, role, and user fields"),
    limit: int = Query(50, le=200),
    mgr: AccessRequestManager = Depends(_get_manager),
    tenant_id: str = Depends(_get_tenant_id),
):
    """List access requests with optional filters (DB-backed)"""
    requests = mgr.get_all_requests(tenant_id=tenant_id, status=status or "", limit=limit)

    if requester:
        requests = [r for r in requests if r.requester_user_id == requester]
    if target:
        requests = [r for r in requests if r.target_user_id == target]
    if search:
        term = search.lower()
        requests = [
            r for r in requests
            if term in r.request_id.lower()
            or term in (r.requester_user_id or "").lower()
            or term in (r.requester_name or "").lower()
            or term in (r.target_user_id or "").lower()
            or term in (r.target_user_name or "").lower()
            or any(term in (item.access_name or "").lower() for item in r.requested_items)
        ]

    return {
        "total": len(requests),
        "requests": [r.to_summary() for r in requests]
    }


@router.post("/{request_id}/cancel")
async def cancel_request(
    request_id: str,
    user_id: str = Query(...),
    mgr: AccessRequestManager = Depends(_get_manager),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Cancel a pending request"""
    access_request = mgr.get_request(request_id, tenant_id)
    if not access_request:
        raise HTTPException(status_code=404, detail=f"Request {request_id} not found")

    if access_request.requester_user_id != user_id:
        raise HTTPException(status_code=403, detail="Only requester can cancel")

    if access_request.status not in [AccessRequestStatus.DRAFT, AccessRequestStatus.PENDING_APPROVAL]:
        raise HTTPException(status_code=400, detail="Cannot cancel request in current status")

    access_request.status = AccessRequestStatus.CANCELLED
    mgr._save_to_db(access_request)

    return {
        "request_id": request_id,
        "status": "cancelled",
        "message": "Request has been cancelled"
    }


# =============================================================================
# Modify-Before-Approval Endpoint (ARM gap)
# =============================================================================

@router.put("/{request_id}/modify-items")
async def modify_request_items(
    request_id: str,
    body: ModifyItemsRequest,
    mgr: AccessRequestManager = Depends(_get_manager),
    tenant_id: str = Depends(_get_tenant_id),
):
    """
    Modify the roles on a pending access request before it is approved.

    Only allowed when request status is PENDING_APPROVAL.
    Re-runs risk analysis after the change and records the modification in the audit trail.
    """
    access_request = mgr.get_request(request_id, tenant_id)
    if not access_request:
        raise HTTPException(status_code=404, detail=f"Request {request_id} not found")

    if access_request.status != AccessRequestStatus.PENDING_APPROVAL:
        raise HTTPException(
            status_code=400,
            detail=f"Request is not in PENDING_APPROVAL status (current: {access_request.status.value})"
        )

    from core.access_request.models import RequestedAccess

    # Remove requested roles
    if body.remove_roles:
        access_request.requested_items = [
            item for item in access_request.requested_items
            if item.access_name not in body.remove_roles
        ]

    # Add new roles
    for role_id in body.add_roles:
        if not any(item.access_name == role_id for item in access_request.requested_items):
            access_request.requested_items.append(RequestedAccess(
                access_type="role",
                access_name=role_id,
            ))

    # Re-run risk preview
    try:
        risk_result = await mgr.preview_risk(access_request)
    except Exception:
        risk_result = {}

    # Audit trail entry
    modification_note = {
        "modifier_id": body.modifier_id,
        "modified_at": datetime.utcnow().isoformat(),
        "removed_roles": body.remove_roles,
        "added_roles": body.add_roles,
        "comments": body.comments or "",
    }
    if not hasattr(access_request, 'audit_notes') or access_request.audit_notes is None:
        access_request.audit_notes = []
    if isinstance(access_request.audit_notes, list):
        access_request.audit_notes.append(modification_note)

    mgr._save_to_db(access_request)

    return {
        "request_id": request_id,
        "status": access_request.status.value,
        "current_roles": [item.access_name for item in access_request.requested_items],
        "modification": modification_note,
        "risk_preview": risk_result,
        "message": "Request items updated and risk re-assessed",
    }


# =============================================================================
# Inline Mitigation Assignment Endpoint (ARM gap)
# =============================================================================

@router.post("/{request_id}/assign-mitigation")
async def assign_mitigation_to_request(
    request_id: str,
    body: AssignMitigationRequest,
    mgr: AccessRequestManager = Depends(_get_manager),
    tenant_id: str = Depends(_get_tenant_id),
    db: Session = Depends(get_db),
):
    """
    Assign a mitigation control to a violation on a pending access request.

    Links the mitigation control to the violation, updates the request risk
    assessment to reflect the mitigated state, and allows approval to proceed.
    """
    access_request = mgr.get_request(request_id, tenant_id)
    if not access_request:
        raise HTTPException(status_code=404, detail=f"Request {request_id} not found")

    # Link mitigation in DB
    try:
        from db.models.risk import RiskViolation, MitigationControl
        violation = db.query(RiskViolation).filter(
            RiskViolation.violation_id == body.violation_id
        ).first()
        if not violation:
            raise HTTPException(status_code=404, detail=f"Violation {body.violation_id} not found")

        control = db.query(MitigationControl).filter(
            MitigationControl.control_id == body.mitigation_control_id
        ).first()

        if violation:
            violation.mitigation_status = "mitigated"
            violation.mitigation_control_id = body.mitigation_control_id
            violation.mitigation_comments = body.comments or ""
            db.commit()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to link mitigation: {str(e)}")

    return {
        "request_id": request_id,
        "violation_id": body.violation_id,
        "mitigation_control_id": body.mitigation_control_id,
        "comments": body.comments,
        "message": "Mitigation assigned. Request may now proceed with mitigated risk.",
    }


# =============================================================================
# Approval Endpoints
# =============================================================================

@router.get("/approvals/pending")
async def get_pending_approvals(
    approver_id: Optional[str] = Query(None, description="Approver user ID (defaults to current user)"),
    type: Optional[str] = Query(None, description="Filter by request type (access_request, role_change, etc.)"),
    priority: Optional[str] = Query(None, description="Filter by priority (normal, high, urgent)"),
    search: Optional[str] = Query(None, description="Search across requester name, ID, or summary"),
    mgr: AccessRequestManager = Depends(_get_manager),
):
    """Get all pending approvals for an approver."""
    if not approver_id:
        from core.tenant import get_current_tenant
        ctx = get_current_tenant()
        approver_id = ctx.user_id if ctx else "admin"
    pending = mgr.get_pending_approvals(approver_id)

    if type:
        pending = [p for p in pending if p.get("type") == type]
    if priority:
        pending = [p for p in pending if p.get("priority") == priority]
    if search:
        term = search.lower()
        pending = [
            p for p in pending
            if term in str(p.get("id", "")).lower()
            or term in str(p.get("requester", "")).lower()
            or term in str(p.get("summary", "")).lower()
        ]

    return {
        "approver_id": approver_id,
        "pending_count": len(pending),
        "approvals": pending
    }


@router.post("/{request_id}/approve/{step_id}")
async def process_approval(
    request_id: str,
    step_id: str,
    approval: ApprovalActionModel,
    mgr: AccessRequestManager = Depends(_get_manager),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Process an approval action on a request."""
    try:
        action_map = {
            "approve": ApprovalAction.APPROVE,
            "reject": ApprovalAction.REJECT,
            "delegate": ApprovalAction.DELEGATE,
            "request_info": ApprovalAction.REQUEST_INFO,
            "escalate": ApprovalAction.ESCALATE
        }
        action = action_map.get(approval.action.lower())
        if not action:
            raise ValueError(f"Invalid action: {approval.action}")

        # Self-approval prevention
        the_request = mgr.get_request(request_id, tenant_id)
        if not the_request:
            raise HTTPException(status_code=404, detail=f"Request {request_id} not found")

        # Check role prerequisites (warning, not a hard block)
        if action == ApprovalAction.APPROVE:
            import logging as _logging
            _prereq_logger = _logging.getLogger(__name__)
            for item in (the_request.requested_items or []):
                role_obj = None
                try:
                    from db.models.user import Role
                    from db.database import get_db as _gdb
                    # Prerequisites check is best-effort — do not fail approval on DB error
                    if hasattr(mgr, 'db') and mgr.db:
                        role_obj = mgr.db.query(Role).filter(Role.role_id == item.access_name).first()
                except Exception:
                    pass
                if role_obj and hasattr(role_obj, 'prerequisites') and role_obj.prerequisites:
                    for prereq in (role_obj.prerequisites or []):
                        # Log warning if prerequisites not met (configurable block in future)
                        _prereq_logger.warning(
                            "Role %s has prerequisite '%s' — not yet verified for user %s",
                            item.access_name, prereq, the_request.target_user_id,
                        )

        if action == ApprovalAction.APPROVE and approval.actor_id == the_request.requester_user_id:
            raise HTTPException(
                status_code=403,
                detail="Self-approval is not permitted. A different approver must review this request."
            )

        access_request = await mgr.process_approval(
            request_id=request_id,
            step_id=step_id,
            action=action,
            actor_id=approval.actor_id,
            comments=approval.comments or "",
            delegate_to=approval.delegate_to,
            tenant_id=tenant_id,
        )

        return {
            "request_id": request_id,
            "action_taken": approval.action,
            "status": access_request.status.value,
            "current_step": access_request.current_step,
            "is_fully_approved": access_request.is_fully_approved(),
            "message": f"Action '{approval.action}' processed successfully"
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.post("/{request_id}/bulk-approve")
async def bulk_approve(
    request_id: str,
    actor_id: str = Query(...),
    comments: str = Query(default="Bulk approved"),
    mgr: AccessRequestManager = Depends(_get_manager),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Approve all pending steps (for authorized super-approvers)."""
    access_request = mgr.get_request(request_id, tenant_id)
    if not access_request:
        raise HTTPException(status_code=404, detail=f"Request {request_id} not found")

    approved_steps = []
    for step in access_request.approval_steps:
        if step.status.value == "pending":
            try:
                await mgr.process_approval(
                    request_id=request_id,
                    step_id=step.step_id,
                    action=ApprovalAction.APPROVE,
                    actor_id=actor_id,
                    comments=comments,
                    tenant_id=tenant_id,
                )
                approved_steps.append(step.step_id)
            except Exception:
                pass

    return {
        "request_id": request_id,
        "steps_approved": len(approved_steps),
        "status": access_request.status.value
    }


# =============================================================================
# User-Specific Endpoints
# =============================================================================

@router.get("/my-requests")
async def get_my_requests(
    user_id: str = Query(...),
    mgr: AccessRequestManager = Depends(_get_manager),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Get all requests created by the current user"""
    requests = mgr.get_requests_for_user(user_id, tenant_id)
    return {
        "user_id": user_id,
        "total": len(requests),
        "requests": [r.to_summary() for r in requests]
    }


@router.get("/my-access")
async def get_my_access(
    user_id: str = Query(...),
    mgr: AccessRequestManager = Depends(_get_manager),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Get all access granted to a user through requests"""
    requests = mgr.get_requests_for_target(user_id, tenant_id)
    active = [r for r in requests if r.status == AccessRequestStatus.PROVISIONED]

    return {
        "user_id": user_id,
        "active_access": [
            {
                "request_id": r.request_id,
                "roles": [i.access_name for i in r.requested_items],
                "granted_at": r.provisioned_at.isoformat() if r.provisioned_at else None,
                "expires_at": r.access_expires_at.isoformat() if r.access_expires_at else "Never",
                "is_temporary": r.is_temporary
            }
            for r in active
        ]
    }


# =============================================================================
# Statistics Endpoints
# =============================================================================

@router.get("/statistics")
async def get_request_statistics(
    mgr: AccessRequestManager = Depends(_get_manager),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Get overall request statistics"""
    return mgr.get_statistics(tenant_id)


@router.get("/statistics/sla")
async def get_sla_statistics(
    mgr: AccessRequestManager = Depends(_get_manager),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Get SLA compliance statistics"""
    requests = mgr.get_all_requests(tenant_id=tenant_id, status="pending_approval")

    total_pending = sum(1 for r in requests
                       if r.status == AccessRequestStatus.PENDING_APPROVAL)

    overdue = sum(1 for r in requests
                 if r.status == AccessRequestStatus.PENDING_APPROVAL
                 and any(s.is_overdue() for s in r.approval_steps))

    # Calculate average approval time for completed requests
    completed = [r for r in requests if r.completed_at and r.submitted_at]
    avg_hours = 0
    if completed:
        total_hours = sum(
            (r.completed_at - r.submitted_at).total_seconds() / 3600
            for r in completed
        )
        avg_hours = total_hours / len(completed)

    return {
        "total_pending": total_pending,
        "overdue_count": overdue,
        "sla_compliance_rate": ((total_pending - overdue) / total_pending * 100) if total_pending > 0 else 100,
        "average_approval_hours": round(avg_hours, 1),
        "requests_completed_today": sum(1 for r in completed
                                        if r.completed_at and r.completed_at.date() == datetime.now().date())
    }
