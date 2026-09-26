"""
Model User & Templates API Router

Endpoints for "give me same access as Sarah" workflows and reusable
access template management.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from core.access_request.model_user import get_model_user_engine
from core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(tags=["Model User & Templates"])
_engine = get_model_user_engine()


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------

class CompareUsersRequest(BaseModel):
    source_user_id: str = Field(..., description="Model user (the one to copy from)")
    target_user_id: str = Field(..., description="User to be provisioned")


class GenerateRequestBody(BaseModel):
    source_user_id: str = Field(..., description="Model user")
    target_user_id: str = Field(..., description="Target user for provisioning")
    unused_days_threshold: int = Field(
        default=90,
        ge=1,
        le=365,
        description="Roles unused for this many days will be skipped",
    )


class CreateTemplateRequest(BaseModel):
    name: str = Field(..., min_length=3, description="Human-readable template name")
    description: str = Field(default="", description="What this template is for")
    role_ids: List[str] = Field(..., min_length=1, description="Role IDs to include")
    tags: List[str] = Field(default_factory=list, description="Optional category tags")
    created_by: str = Field(default="api")


class ApplyTemplateRequest(BaseModel):
    target_user_id: str = Field(..., description="User to apply the template to")
    requested_by: str = Field(default="api", description="Who is initiating the request")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/model/{user_id}")
async def get_model_user(user_id: str) -> Dict[str, Any]:
    """
    Return the full role inventory for a model (reference) user.

    Use this to preview what access a user holds before deciding to
    clone it for another user.
    """
    try:
        return _engine.get_model_user_access(user_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/compare")
async def compare_users(req: CompareUsersRequest) -> Dict[str, Any]:
    """
    Compare role assignments between a source (model) user and a target user.

    Returns three lists: roles only the source has, roles only the target has,
    and roles shared by both.
    """
    try:
        return _engine.compare_users(req.source_user_id, req.target_user_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/generate-request")
async def generate_request(req: GenerateRequestBody) -> Dict[str, Any]:
    """
    Generate a smart, filtered access request based on a model user.

    Each role from the model user is evaluated and tagged as:
    - COPY: safe to request as-is
    - REVIEW: high-risk or sensitive — requires approver attention
    - SKIP: temporary, unused, or department-specific — excluded automatically

    The result can be submitted directly or edited before submission.
    """
    try:
        return _engine.generate_smart_request(
            source_user_id=req.source_user_id,
            target_user_id=req.target_user_id,
            unused_days_threshold=req.unused_days_threshold,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/templates")
async def list_templates(
    active_only: bool = Query(default=True, description="Return only active templates"),
) -> Dict[str, Any]:
    """
    List all reusable access templates.

    Templates are pre-defined bundles of roles for common job functions
    (e.g. New Finance Employee, New IT Admin).
    """
    templates = _engine.list_templates(active_only=active_only)
    return {
        "total": len(templates),
        "templates": templates,
    }


@router.get("/templates/{template_id}")
async def get_template(template_id: str) -> Dict[str, Any]:
    """Return a single template with full role details."""
    try:
        tmpl = _engine.get_template(template_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    from core.access_request.model_user import _MOCK_ROLES  # noqa: PLC0415
    entry = tmpl.to_dict()
    entry["roles"] = [
        _MOCK_ROLES[rid].to_dict()
        for rid in tmpl.role_ids
        if rid in _MOCK_ROLES
    ]
    return entry


@router.post("/templates")
async def create_template(req: CreateTemplateRequest) -> Dict[str, Any]:
    """
    Create a new reusable access template.

    Provide a name, list of role IDs, and optional description/tags.
    The template can then be applied to any user.
    """
    template = _engine.create_template(
        name=req.name,
        role_ids=req.role_ids,
        description=req.description,
        created_by=req.created_by,
        tags=req.tags,
    )
    logger.info("api.template_created", template_id=template.template_id)
    return {
        "message": "Template created",
        "template": template.to_dict(),
    }


@router.post("/templates/{template_id}/apply")
async def apply_template(template_id: str, req: ApplyTemplateRequest) -> Dict[str, Any]:
    """
    Apply a template to a user.

    Generates a pre-populated access request containing the template's roles.
    Roles already held by the target user are excluded automatically.
    High-risk roles are flagged REVIEW for approver attention.
    """
    try:
        return _engine.apply_template(
            template_id=template_id,
            target_user_id=req.target_user_id,
            requested_by=req.requested_by,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.delete("/templates/{template_id}")
async def delete_template(
    template_id: str,
    deleted_by: str = Query(default="api"),
) -> Dict[str, Any]:
    """
    Soft-delete a template by marking it inactive.
    Deleted templates no longer appear in list results (unless active_only=false).
    """
    try:
        _engine.delete_template(template_id, deleted_by=deleted_by)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    logger.info("api.template_deleted", template_id=template_id)
    return {"message": f"Template '{template_id}' deleted", "template_id": template_id}
