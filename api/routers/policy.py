"""
Policy Management API Router

Endpoints for policy lifecycle management with versioning and approvals.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

from core.policy import PolicyManager, Policy, PolicyType, PolicyStatus

router = APIRouter(tags=["Policy"])

# Initialize manager
policy_manager = PolicyManager()


# =============================================================================
# Request/Response Models
# =============================================================================

class CreatePolicyRequest(BaseModel):
    """Request to create a new policy"""
    name: str = Field(..., example="Vendor Creation SoD Rule")
    description: str = Field(..., example="Segregation rule for vendor management")
    policy_type: str = Field(..., example="risk_rule")
    category: str = Field(default="", example="Financial Controls")
    tags: List[str] = Field(default_factory=list)
    scope: Dict[str, Any] = Field(default_factory=dict)
    initial_content: Dict[str, Any] = Field(..., example={"rule_id": "SOD-001"})
    owner_id: str = Field(..., example="security.admin@company.com")
    owner_name: str = Field(..., example="Security Admin")
    requires_approval: bool = Field(default=True)
    required_approver_count: int = Field(default=1, ge=1, le=5)
    allowed_approvers: List[str] = Field(default_factory=list)
    compliance_frameworks: List[str] = Field(default_factory=list)


class CreateVersionRequest(BaseModel):
    """Request to create a new policy version"""
    new_content: Dict[str, Any] = Field(...)
    change_summary: str = Field(..., example="Updated risk scoring threshold")
    reason: str = Field(default="", example="Based on audit findings")
    effective_from: Optional[datetime] = None


class ApprovalRequest(BaseModel):
    """Request to approve/reject a policy version"""
    approver_id: str = Field(..., example="ciso@company.com")
    approver_name: str = Field(..., example="Chief Information Security Officer")
    comments: str = Field(default="", example="Approved as per review meeting")


class RejectionRequest(BaseModel):
    """Request to reject a policy version"""
    rejector_id: str = Field(..., example="ciso@company.com")
    rejector_name: str = Field(..., example="Chief Information Security Officer")
    reason: str = Field(..., example="Needs additional risk assessment")


class ActivationRequest(BaseModel):
    """Request to activate a policy version"""
    activated_by: str = Field(...)
    effective_from: Optional[datetime] = None


class RollbackRequest(BaseModel):
    """Request to rollback to a previous version"""
    rolled_back_by: str = Field(...)
    reason: str = Field(..., example="Reverting due to production issue")


class CreateFromTemplateRequest(BaseModel):
    """Request to create policy from template"""
    template_id: str = Field(...)
    name: str = Field(...)
    owner_id: str = Field(...)
    owner_name: str = Field(...)
    content_overrides: Dict[str, Any] = Field(default_factory=dict)
    description: str = Field(default="")
    category: str = Field(default="")
    tags: List[str] = Field(default_factory=list)


# =============================================================================
# Policy CRUD Endpoints
# =============================================================================

@router.post("/", status_code=201)
async def create_policy(request: CreatePolicyRequest):
    """
    Create a new policy with initial version.

    The policy is created in DRAFT status unless requires_approval is False.
    """
    try:
        # Map policy type
        type_map = {
            "risk_rule": PolicyType.RISK_RULE,
            "access_policy": PolicyType.ACCESS_POLICY,
            "approval_policy": PolicyType.APPROVAL_POLICY,
            "certification_policy": PolicyType.CERTIFICATION_POLICY,
            "firefighter_policy": PolicyType.FIREFIGHTER_POLICY,
            "compliance_policy": PolicyType.COMPLIANCE_POLICY,
            "password_policy": PolicyType.PASSWORD_POLICY,
            "retention_policy": PolicyType.RETENTION_POLICY
        }
        policy_type = type_map.get(request.policy_type, PolicyType.RISK_RULE)

        policy = policy_manager.create_policy(
            name=request.name,
            description=request.description,
            policy_type=policy_type,
            owner_id=request.owner_id,
            owner_name=request.owner_name,
            initial_content=request.initial_content,
            category=request.category,
            tags=request.tags,
            scope=request.scope,
            requires_approval=request.requires_approval,
            required_approver_count=request.required_approver_count,
            allowed_approvers=request.allowed_approvers,
            compliance_frameworks=request.compliance_frameworks
        )

        current = policy.get_current_version()

        return {
            "message": "Policy created successfully",
            "policy_id": policy.policy_id,
            "version_id": current.version_id if current else None,
            "status": current.status.value if current else "no_version"
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/")
async def list_policies(
    policy_type: Optional[str] = Query(None, description="Filter by policy type"),
    owner_id: Optional[str] = Query(None, description="Filter by owner"),
    framework: Optional[str] = Query(None, description="Filter by compliance framework"),
    status: Optional[str] = Query(None, description="Filter by status"),
    include_deprecated: bool = Query(False, description="Include deprecated policies")
):
    """
    List all policies with optional filters.
    """
    type_enum = None
    if policy_type:
        try:
            type_enum = PolicyType(policy_type)
        except ValueError:
            pass

    status_enum = None
    if status:
        try:
            status_enum = PolicyStatus(status)
        except ValueError:
            pass

    policies = policy_manager.get_policies(
        policy_type=type_enum,
        owner_id=owner_id,
        framework=framework,
        status=status_enum,
        include_deprecated=include_deprecated
    )

    return {
        "total": len(policies),
        "policies": [p.to_summary() for p in policies]
    }


@router.get("/types")
async def list_policy_types():
    """List all available policy types"""
    return {
        "types": [
            {"value": t.value, "name": t.name}
            for t in PolicyType
        ]
    }


@router.get("/statistics")
async def get_policy_statistics():
    """Get policy management statistics"""
    return policy_manager.get_statistics()


@router.get("/{policy_id}")
async def get_policy(policy_id: str):
    """Get detailed information about a policy"""
    policy = policy_manager.get_policy(policy_id)
    if not policy:
        raise HTTPException(status_code=404, detail=f"Policy {policy_id} not found")

    return policy.to_dict()


@router.get("/{policy_id}/versions")
async def get_policy_versions(policy_id: str):
    """Get all versions of a policy"""
    policy = policy_manager.get_policy(policy_id)
    if not policy:
        raise HTTPException(status_code=404, detail=f"Policy {policy_id} not found")

    return {
        "policy_id": policy_id,
        "current_version_id": policy.current_version_id,
        "version_count": len(policy.versions),
        "versions": policy.get_version_history()
    }


@router.get("/{policy_id}/versions/{version_id}")
async def get_policy_version(policy_id: str, version_id: str):
    """Get a specific version of a policy"""
    policy = policy_manager.get_policy(policy_id)
    if not policy:
        raise HTTPException(status_code=404, detail=f"Policy {policy_id} not found")

    version = policy.get_version(version_id)
    if not version:
        raise HTTPException(status_code=404, detail=f"Version {version_id} not found")

    return version.to_dict()


# =============================================================================
# Version Management Endpoints
# =============================================================================

@router.post("/{policy_id}/versions", status_code=201)
async def create_policy_version(policy_id: str, request: CreateVersionRequest):
    """
    Create a new version of a policy.

    The new version is created in DRAFT status.
    """
    try:
        version = policy_manager.create_new_version(
            policy_id=policy_id,
            new_content=request.new_content,
            created_by=request.reason or "system",  # Should come from auth
            change_summary=request.change_summary,
            reason=request.reason,
            effective_from=request.effective_from
        )

        return {
            "message": "New version created",
            "version_id": version.version_id,
            "version_label": version.version_label,
            "status": version.status.value
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{policy_id}/versions/{version_id}/submit")
async def submit_for_approval(
    policy_id: str,
    version_id: str,
    submitter_id: str = Query(..., description="User submitting for approval")
):
    """
    Submit a policy version for approval.
    """
    try:
        version = policy_manager.submit_for_approval(policy_id, version_id, submitter_id)

        return {
            "message": "Submitted for approval",
            "version_id": version.version_id,
            "status": version.status.value,
            "required_approvers": version.required_approvers
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{policy_id}/versions/{version_id}/approve")
async def approve_version(policy_id: str, version_id: str, request: ApprovalRequest):
    """
    Approve a policy version.

    Multiple approvals may be required based on policy configuration.
    """
    try:
        version = policy_manager.approve_version(
            policy_id=policy_id,
            version_id=version_id,
            approver_id=request.approver_id,
            approver_name=request.approver_name,
            comments=request.comments
        )

        return {
            "message": "Approval recorded",
            "version_id": version.version_id,
            "status": version.status.value,
            "is_fully_approved": version.is_fully_approved(),
            "approvals_received": len([a for a in version.approvals if a.action == "approve"]),
            "approvals_required": len(version.required_approvers)
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.post("/{policy_id}/versions/{version_id}/reject")
async def reject_version(policy_id: str, version_id: str, request: RejectionRequest):
    """
    Reject a policy version.

    The version will be returned to DRAFT status.
    """
    try:
        version = policy_manager.reject_version(
            policy_id=policy_id,
            version_id=version_id,
            rejector_id=request.rejector_id,
            rejector_name=request.rejector_name,
            reason=request.reason
        )

        return {
            "message": "Version rejected",
            "version_id": version.version_id,
            "status": version.status.value
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{policy_id}/versions/{version_id}/activate")
async def activate_version(policy_id: str, version_id: str, request: ActivationRequest):
    """
    Activate an approved policy version.

    This makes the version the current active version.
    """
    try:
        version = policy_manager.activate_version(
            policy_id=policy_id,
            version_id=version_id,
            activated_by=request.activated_by,
            effective_from=request.effective_from
        )

        return {
            "message": "Version activated",
            "version_id": version.version_id,
            "status": version.status.value,
            "effective_from": version.effective_from.isoformat() if version.effective_from else None
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{policy_id}/rollback")
async def rollback_to_version(
    policy_id: str,
    target_version_id: str = Query(..., description="Version to rollback to"),
    request: RollbackRequest = None
):
    """
    Rollback to a previous version.

    Creates a new version with the content from the target version.
    """
    try:
        version = policy_manager.rollback_to_version(
            policy_id=policy_id,
            target_version_id=target_version_id,
            rolled_back_by=request.rolled_back_by,
            reason=request.reason
        )

        return {
            "message": "Rollback completed - new version created",
            "new_version_id": version.version_id,
            "new_version_label": version.version_label,
            "status": version.status.value
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{policy_id}/compare")
async def compare_versions(
    policy_id: str,
    version_1: str = Query(..., description="First version ID"),
    version_2: str = Query(..., description="Second version ID")
):
    """
    Compare two versions of a policy.

    Returns a diff of the changes between versions.
    """
    try:
        comparison = policy_manager.compare_versions(policy_id, version_1, version_2)
        return comparison

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# =============================================================================
# Approval Workflow Endpoints
# =============================================================================

@router.get("/approvals/pending")
async def get_pending_approvals(
    approver_id: Optional[str] = Query(None, description="Filter by approver")
):
    """
    Get policy versions pending approval.
    """
    pending = policy_manager.get_pending_approvals(approver_id)

    return {
        "total": len(pending),
        "pending_approvals": pending
    }


# =============================================================================
# Change History Endpoints
# =============================================================================

@router.get("/{policy_id}/history")
async def get_policy_history(
    policy_id: str,
    limit: int = Query(50, le=200)
):
    """
    Get change history for a specific policy.
    """
    history = policy_manager.get_change_history(policy_id=policy_id, limit=limit)

    return {
        "policy_id": policy_id,
        "total": len(history),
        "changes": [c.to_dict() for c in history]
    }


@router.get("/history/all")
async def get_all_change_history(
    changed_by: Optional[str] = Query(None, description="Filter by user"),
    start_date: Optional[datetime] = Query(None, description="Start date"),
    end_date: Optional[datetime] = Query(None, description="End date"),
    limit: int = Query(100, le=500)
):
    """
    Get change history across all policies.
    """
    history = policy_manager.get_change_history(
        changed_by=changed_by,
        start_date=start_date,
        end_date=end_date,
        limit=limit
    )

    return {
        "total": len(history),
        "changes": [c.to_dict() for c in history]
    }


# =============================================================================
# Template Endpoints
# =============================================================================

@router.get("/templates/")
async def list_templates(
    policy_type: Optional[str] = Query(None, description="Filter by policy type")
):
    """
    List available policy templates.
    """
    type_enum = None
    if policy_type:
        try:
            type_enum = PolicyType(policy_type)
        except ValueError:
            pass

    templates = policy_manager.get_templates(type_enum)

    return {
        "total": len(templates),
        "templates": [t.to_dict() for t in templates]
    }


@router.get("/templates/{template_id}")
async def get_template(template_id: str):
    """
    Get a specific template.
    """
    template = policy_manager.get_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail=f"Template {template_id} not found")

    return template.to_dict()


@router.post("/templates/{template_id}/create-policy", status_code=201)
async def create_policy_from_template(template_id: str, request: CreateFromTemplateRequest):
    """
    Create a policy from a template.
    """
    try:
        policy = policy_manager.create_policy_from_template(
            template_id=template_id,
            name=request.name,
            owner_id=request.owner_id,
            owner_name=request.owner_name,
            content_overrides=request.content_overrides,
            description=request.description,
            category=request.category,
            tags=request.tags
        )

        return {
            "message": "Policy created from template",
            "policy_id": policy.policy_id,
            "template_used": template_id
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
