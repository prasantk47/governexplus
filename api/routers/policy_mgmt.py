"""
Policy Lifecycle Management API Router

Covers PC-SAP-GAP-07: Full policy document lifecycle from draft → retire,
including versioning, acknowledgment tracking, and review scheduling.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Dict, List, Optional, Any
from datetime import datetime
from sqlalchemy.orm import Session
import uuid

from db.database import get_db
from db.models.process_control import (
    PolicyDocument, PolicyType, PolicyStatus,
)

router = APIRouter(tags=["Policy Management"])


# ---------------------------------------------------------------------------
# Tenant helpers
# ---------------------------------------------------------------------------

def _get_tenant_id() -> str:
    from core.tenant import get_current_tenant
    ctx = get_current_tenant()
    return ctx.tenant_id if ctx else "default"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def _policy_or_404(db: Session, policy_id: str, tenant_id: str) -> PolicyDocument:
    p = db.query(PolicyDocument).filter(
        PolicyDocument.policy_id == policy_id,
        PolicyDocument.tenant_id == tenant_id,
    ).first()
    if not p:
        raise HTTPException(status_code=404, detail=f"Policy '{policy_id}' not found")
    return p


def _append_version_history(policy: PolicyDocument, changed_by: str, summary: str) -> None:
    """Append an entry to the policy's version_history JSON log."""
    history = list(policy.version_history or [])
    history.append({
        "version": policy.version,
        "changed_by": changed_by,
        "changed_at": datetime.utcnow().isoformat(),
        "summary": summary,
    })
    policy.version_history = history


# ===========================================================================
# Policy CRUD
# ===========================================================================

@router.post("/", status_code=201)
def create_policy(
    body: Dict[str, Any] = Body(default={}),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Create a new policy document in draft status."""
    try:
        policy_type = PolicyType(body.get("policy_type", "corporate"))
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid policy_type")

    p = PolicyDocument(
        tenant_id=tenant_id,
        policy_id=body.get("policy_id") or _new_id("POL"),
        title=body["title"],
        description=body.get("description"),
        policy_type=policy_type,
        regulation_id=body.get("regulation_id"),
        content=body.get("content"),
        version=1,
        version_history=[],
        status=PolicyStatus.DRAFT,
        author_id=body.get("author_id"),
        author_name=body.get("author_name"),
        review_frequency=body.get("review_frequency"),
        next_review_date=(
            datetime.fromisoformat(body["next_review_date"])
            if body.get("next_review_date") else None
        ),
        effective_date=(
            datetime.fromisoformat(body["effective_date"])
            if body.get("effective_date") else None
        ),
        expiry_date=(
            datetime.fromisoformat(body["expiry_date"])
            if body.get("expiry_date") else None
        ),
        acknowledgment_required=body.get("acknowledgment_required", False),
        acknowledgment_count=0,
        total_recipients=body.get("total_recipients", 0),
        tags=body.get("tags", []),
        attachments=body.get("attachments", []),
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return p.to_dict()


@router.get("/")
def list_policies(
    policy_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    regulation_id: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    q = db.query(PolicyDocument).filter(PolicyDocument.tenant_id == tenant_id)
    if policy_type:
        try:
            q = q.filter(PolicyDocument.policy_type == PolicyType(policy_type))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid policy_type")
    if status:
        try:
            q = q.filter(PolicyDocument.status == PolicyStatus(status))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid status")
    if regulation_id:
        q = q.filter(PolicyDocument.regulation_id == regulation_id)
    if search:
        q = q.filter(PolicyDocument.title.ilike(f"%{search}%"))
    policies = q.order_by(PolicyDocument.created_at.desc()).all()
    return {"total": len(policies), "policies": [p.to_dict() for p in policies]}


@router.get("/due-review")
def list_policies_due_review(
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Return policies whose next_review_date is in the past and are still active."""
    now = datetime.utcnow()
    overdue = db.query(PolicyDocument).filter(
        PolicyDocument.tenant_id == tenant_id,
        PolicyDocument.next_review_date <= now,
        PolicyDocument.status.in_([
            PolicyStatus.PUBLISHED,
            PolicyStatus.APPROVED,
        ]),
    ).order_by(PolicyDocument.next_review_date.asc()).all()
    return {"total": len(overdue), "policies": [p.to_dict() for p in overdue]}


@router.get("/{policy_id}")
def get_policy(
    policy_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Get policy detail including full version history."""
    return _policy_or_404(db, policy_id, tenant_id).to_dict()


@router.put("/{policy_id}")
def update_policy(
    policy_id: str,
    body: Dict[str, Any] = Body(default={}),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """
    Update a policy document.  Content edits auto-increment the version number
    and append a version_history entry.
    """
    p = _policy_or_404(db, policy_id, tenant_id)

    # Content changes → version bump
    content_changed = "content" in body and body["content"] != p.content
    if content_changed:
        _append_version_history(
            p,
            changed_by=body.get("changed_by", "unknown"),
            summary=body.get("change_summary", "Content updated"),
        )
        p.version += 1
        p.content = body["content"]

    scalar_fields = [
        "title", "description", "regulation_id", "review_frequency",
        "acknowledgment_required", "total_recipients", "tags",
    ]
    for field in scalar_fields:
        if field in body:
            setattr(p, field, body[field])

    date_fields = ["next_review_date", "effective_date", "expiry_date"]
    for field in date_fields:
        if field in body and body[field]:
            setattr(p, field, datetime.fromisoformat(body[field]))

    db.commit()
    db.refresh(p)
    return p.to_dict()


# ===========================================================================
# Lifecycle transitions
# ===========================================================================

@router.put("/{policy_id}/submit")
def submit_policy(
    policy_id: str,
    body: Dict[str, Any] = Body(default={}),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Advance policy from draft to pending_review."""
    p = _policy_or_404(db, policy_id, tenant_id)
    if p.status != PolicyStatus.DRAFT:
        raise HTTPException(status_code=400, detail="Only draft policies can be submitted")
    _append_version_history(p, changed_by=body.get("submitted_by", "unknown"), summary="Submitted for review")
    p.status = PolicyStatus.PENDING_REVIEW
    db.commit()
    db.refresh(p)
    return p.to_dict()


@router.put("/{policy_id}/approve")
def approve_policy(
    policy_id: str,
    body: Dict[str, Any] = Body(default={}),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Approve a policy under review."""
    p = _policy_or_404(db, policy_id, tenant_id)
    if p.status != PolicyStatus.PENDING_REVIEW:
        raise HTTPException(status_code=400, detail="Policy must be in pending_review to approve")
    if not body.get("approved_by"):
        raise HTTPException(status_code=400, detail="approved_by is required")
    p.approved_by = body["approved_by"]
    p.approved_at = datetime.utcnow()
    p.status = PolicyStatus.APPROVED
    _append_version_history(p, changed_by=body["approved_by"], summary="Approved")
    db.commit()
    db.refresh(p)
    return p.to_dict()


@router.put("/{policy_id}/publish")
def publish_policy(
    policy_id: str,
    body: Dict[str, Any] = Body(default={}),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Publish an approved policy."""
    p = _policy_or_404(db, policy_id, tenant_id)
    if p.status != PolicyStatus.APPROVED:
        raise HTTPException(status_code=400, detail="Policy must be approved before publishing")
    p.published_at = datetime.utcnow()
    p.status = PolicyStatus.PUBLISHED
    _append_version_history(
        p,
        changed_by=body.get("published_by", "unknown"),
        summary="Published",
    )
    # If effective_date not set, default to now
    if not p.effective_date:
        p.effective_date = datetime.utcnow()
    db.commit()
    db.refresh(p)
    return p.to_dict()


@router.put("/{policy_id}/archive")
def archive_policy(
    policy_id: str,
    body: Dict[str, Any] = Body(default={}),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    p = _policy_or_404(db, policy_id, tenant_id)
    _append_version_history(p, changed_by=body.get("archived_by", "unknown"), summary="Archived")
    p.status = PolicyStatus.ARCHIVED
    db.commit()
    db.refresh(p)
    return p.to_dict()


@router.put("/{policy_id}/retire")
def retire_policy(
    policy_id: str,
    body: Dict[str, Any] = Body(default={}),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    p = _policy_or_404(db, policy_id, tenant_id)
    _append_version_history(p, changed_by=body.get("retired_by", "unknown"), summary="Retired")
    p.status = PolicyStatus.RETIRED
    db.commit()
    db.refresh(p)
    return p.to_dict()


# ===========================================================================
# Acknowledgments
# ===========================================================================

@router.post("/{policy_id}/acknowledge")
def acknowledge_policy(
    policy_id: str,
    body: Dict[str, Any] = Body(default={}),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """
    Record a user's acknowledgment of a published policy.

    Body: { "user_id": "...", "user_name": "...", "user_email": "..." }

    Acknowledgments are stored in the policy's attachments JSON as a separate
    key-type record.  The acknowledgment_count is incremented.
    """
    p = _policy_or_404(db, policy_id, tenant_id)
    if p.status != PolicyStatus.PUBLISHED:
        raise HTTPException(status_code=400, detail="Acknowledgments can only be recorded for published policies")
    if not body.get("user_id"):
        raise HTTPException(status_code=400, detail="user_id is required")

    # Store acknowledgments in a JSON column attached to the policy.
    # We repurpose attachments with a type discriminator to keep the model lean.
    acks = [a for a in (p.attachments or []) if a.get("type") != "acknowledgment"]
    existing_ack_ids = {
        a["user_id"] for a in (p.attachments or []) if a.get("type") == "acknowledgment"
    }

    if body["user_id"] in existing_ack_ids:
        raise HTTPException(status_code=409, detail="User has already acknowledged this policy")

    new_ack = {
        "type": "acknowledgment",
        "user_id": body["user_id"],
        "user_name": body.get("user_name"),
        "user_email": body.get("user_email"),
        "acknowledged_at": datetime.utcnow().isoformat(),
    }
    p.attachments = (acks + [a for a in (p.attachments or []) if a.get("type") == "acknowledgment"]) + [new_ack]
    p.acknowledgment_count = p.acknowledgment_count + 1

    db.commit()
    return {
        "policy_id": policy_id,
        "user_id": body["user_id"],
        "acknowledged_at": new_ack["acknowledged_at"],
        "total_acknowledgments": p.acknowledgment_count,
        "total_recipients": p.total_recipients,
        "completion_pct": (
            round(p.acknowledgment_count / p.total_recipients * 100, 1)
            if p.total_recipients else None
        ),
    }


@router.get("/{policy_id}/acknowledgments")
def list_acknowledgments(
    policy_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Return the acknowledgment status for a policy."""
    p = _policy_or_404(db, policy_id, tenant_id)
    acks = [a for a in (p.attachments or []) if a.get("type") == "acknowledgment"]
    return {
        "policy_id": policy_id,
        "title": p.title,
        "status": p.status.value if p.status else None,
        "acknowledgment_required": p.acknowledgment_required,
        "total_recipients": p.total_recipients,
        "acknowledgment_count": p.acknowledgment_count,
        "completion_pct": (
            round(p.acknowledgment_count / p.total_recipients * 100, 1)
            if p.total_recipients else None
        ),
        "acknowledgments": acks,
    }
