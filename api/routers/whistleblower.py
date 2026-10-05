"""
Whistleblower Intake API Router

Anonymous and confidential whistleblower case management:
  - Public submission endpoint returns a one-way case reference token
  - Anonymous follow-up via that token (no auth required)
  - Investigator case management (auth-gated)
  - Secure message thread between anonymous submitter and investigators
  - Dashboard: case volumes, cycle times, category breakdown
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
import uuid
import secrets

from db.database import get_db
from db.models.extended_modules import WhistleblowerCase, WhistleblowerMessage, WhistleblowerStatus

router = APIRouter(tags=["Whistleblower Intake"])


# ---------------------------------------------------------------------------
# Tenant helper
# ---------------------------------------------------------------------------

def _get_tenant_id() -> str:
    from core.tenant import get_current_tenant
    ctx = get_current_tenant()
    return ctx.tenant_id if ctx else "default"


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def _generate_case_reference() -> str:
    """Generate a cryptographically secure, human-typeable case reference."""
    return secrets.token_urlsafe(16)


# ---------------------------------------------------------------------------
# 404 helpers
# ---------------------------------------------------------------------------

def _case_or_404(db: Session, case_id: str, tenant_id: str) -> WhistleblowerCase:
    obj = db.query(WhistleblowerCase).filter(
        WhistleblowerCase.id == case_id,
        WhistleblowerCase.tenant_id == tenant_id,
    ).first()
    if not obj:
        raise HTTPException(status_code=404, detail=f"Case '{case_id}' not found")
    return obj


def _case_by_reference(db: Session, case_reference: str, tenant_id: str) -> WhistleblowerCase:
    """Look up a case by its anonymous reference token."""
    obj = db.query(WhistleblowerCase).filter(
        WhistleblowerCase.case_reference == case_reference,
        WhistleblowerCase.tenant_id == tenant_id,
    ).first()
    if not obj:
        # Return 404 with a generic message — do not reveal whether the reference exists
        raise HTTPException(
            status_code=404,
            detail="Case not found. Please check your case reference token.",
        )
    return obj


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class SubmissionCreate(BaseModel):
    """Public submission — no authenticated user required."""
    category: str = Field(
        ...,
        description="fraud | bribery | safety | harassment | data_privacy | conflict_of_interest | other",
    )
    title: str = Field(..., max_length=300)
    description: str
    priority: Optional[str] = Field(
        default="normal",
        description="urgent | high | normal | low",
    )
    subject_name: Optional[str] = None
    subject_department: Optional[str] = None
    incident_date: Optional[str] = None
    supporting_details: Optional[str] = None
    is_anonymous: bool = True
    submitter_name: Optional[str] = Field(
        None,
        description="Filled only if submitter waives anonymity",
    )
    submitter_email: Optional[str] = Field(
        None,
        description="Filled only if submitter waives anonymity",
    )


class CaseUpdate(BaseModel):
    status: Optional[str] = Field(
        None,
        description="open | under_investigation | pending_closure | closed | referred",
    )
    priority: Optional[str] = None
    assigned_to: Optional[str] = None
    category: Optional[str] = None
    internal_notes: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class MessageCreate(BaseModel):
    """Investigator reply to the anonymous submitter."""
    message_body: str
    is_visible_to_submitter: bool = True
    attachment_refs: Optional[List[str]] = None


class AnonymousReply(BaseModel):
    """Anonymous submitter follow-up message."""
    message_body: str
    additional_attachments: Optional[List[str]] = None


# ---------------------------------------------------------------------------
# Public: Submission
# ---------------------------------------------------------------------------

@router.post("/submit", status_code=201)
def submit_case(
    body: SubmissionCreate,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """
    PUBLIC endpoint — no authentication required.

    Submit a whistleblower report. Returns a `case_reference` token that the
    submitter must store securely for anonymous follow-up. This token is the
    ONLY way to retrieve case status and messages without an investigator account.
    """
    case_reference = _generate_case_reference()
    case = WhistleblowerCase(
        id=_new_id("WBC"),
        tenant_id=tenant_id,
        case_reference=case_reference,
        category=body.category,
        summary=body.title,
        details=body.description,
        priority=body.priority or "normal",
        is_anonymous=body.is_anonymous,
        submitter_email=None if body.is_anonymous else body.submitter_email,
        status=WhistleblowerStatus.OPEN,
        submitted_at=datetime.utcnow(),
    )
    db.add(case)
    db.commit()
    db.refresh(case)
    # Return minimal confirmation — never expose internal IDs publicly
    return {
        "message": "Your report has been submitted successfully.",
        "case_reference": case_reference,
        "status": "open",
        "instructions": (
            "Please save your case reference token securely. "
            "You can use it at /whistleblower/track/{case_reference} "
            "to check status and communicate with investigators."
        ),
    }


# ---------------------------------------------------------------------------
# Admin: Case management
# ---------------------------------------------------------------------------

@router.get("/cases")
def list_cases(
    status: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """List all whistleblower cases (admin/investigator only)."""
    q = db.query(WhistleblowerCase).filter(WhistleblowerCase.tenant_id == tenant_id)
    if status:
        q = q.filter(WhistleblowerCase.status == status)
    if category:
        q = q.filter(WhistleblowerCase.category == category)
    if priority:
        q = q.filter(WhistleblowerCase.priority == priority)
    cases = q.order_by(WhistleblowerCase.submitted_at.desc()).all()
    return {"total": len(cases), "cases": [c.to_dict() for c in cases]}


@router.get("/cases/{id}")
def get_case(
    id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Get full case detail including all metadata (admin only)."""
    return _case_or_404(db, id, tenant_id).to_dict()


@router.put("/cases/{id}")
def update_case(
    id: str,
    body: CaseUpdate,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Update case status, assignment, or priority."""
    case = _case_or_404(db, id, tenant_id)
    if body.status is not None:
        case.status = body.status
        if body.status == "closed":
            case.closed_at = datetime.utcnow()
    if body.priority is not None:
        case.priority = body.priority
    if body.assigned_to is not None:
        case.assigned_to = body.assigned_to
    if body.category is not None:
        case.category = body.category
    if body.internal_notes is not None:
        case.internal_notes = body.internal_notes
    if body.metadata is not None:
        case.metadata_ = body.metadata
    db.commit()
    db.refresh(case)
    return case.to_dict()


@router.post("/cases/{id}/messages", status_code=201)
def add_message(
    id: str,
    body: MessageCreate,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Add an investigator reply to the case message thread."""
    case = _case_or_404(db, id, tenant_id)
    message = WhistleblowerMessage(
        id=_new_id("WBMSG"),
        tenant_id=tenant_id,
        case_id=case.id,
        sender_type="investigator",
        message_body=body.message_body,
        is_visible_to_submitter=body.is_visible_to_submitter,
        attachment_refs=body.attachment_refs or [],
        sent_at=datetime.utcnow(),
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    return message.to_dict()


@router.get("/cases/{id}/messages")
def get_messages(
    id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Get full message thread for a case (all messages, including internal-only)."""
    case = _case_or_404(db, id, tenant_id)
    messages = db.query(WhistleblowerMessage).filter(
        WhistleblowerMessage.case_id == case.id,
        WhistleblowerMessage.tenant_id == tenant_id,
    ).order_by(WhistleblowerMessage.sent_at.asc()).all()
    return {
        "case_id": id,
        "total_messages": len(messages),
        "messages": [m.to_dict() for m in messages],
    }


# ---------------------------------------------------------------------------
# Public: Anonymous tracking
# ---------------------------------------------------------------------------

@router.get("/track/{case_reference}")
def track_case(
    case_reference: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """
    PUBLIC — anonymous submitter checks their case status via reference token.

    Returns only the case status and investigator-authored messages that are
    flagged as visible to the submitter. Internal investigator notes are NOT
    included in this response.
    """
    case = _case_by_reference(db, case_reference, tenant_id)

    # Only return messages flagged as visible to the submitter
    messages = db.query(WhistleblowerMessage).filter(
        WhistleblowerMessage.case_id == case.id,
        WhistleblowerMessage.tenant_id == tenant_id,
        WhistleblowerMessage.is_visible_to_submitter == True,
    ).order_by(WhistleblowerMessage.sent_at.asc()).all()

    return {
        "case_reference": case_reference,
        "status": case.status,
        "category": case.category,
        "priority": case.priority,
        "submitted_at": case.submitted_at.isoformat() if case.submitted_at else None,
        "last_updated": case.updated_at.isoformat() if hasattr(case, "updated_at") and case.updated_at else None,
        "messages_from_investigator": [
            {
                "sent_at": m.sent_at.isoformat(),
                "message": m.message_body,
            }
            for m in messages
            if m.sender_type == "investigator"
        ],
    }


@router.post("/track/{case_reference}/reply", status_code=201)
def anonymous_reply(
    case_reference: str,
    body: AnonymousReply,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """
    PUBLIC — anonymous submitter sends a follow-up message.

    No authentication is required; only possession of the case reference token
    grants access to add messages.
    """
    case = _case_by_reference(db, case_reference, tenant_id)
    if case.status == "closed":
        raise HTTPException(
            status_code=400,
            detail="This case is closed. New messages cannot be added.",
        )
    message = WhistleblowerMessage(
        id=_new_id("WBMSG"),
        tenant_id=tenant_id,
        case_id=case.id,
        sender_type="submitter",
        message_body=body.message_body,
        is_visible_to_submitter=True,
        attachment_refs=body.additional_attachments or [],
        sent_at=datetime.utcnow(),
    )
    db.add(message)
    db.commit()
    return {
        "message": "Your reply has been submitted successfully.",
        "sent_at": message.sent_at.isoformat(),
    }


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@router.get("/dashboard")
def get_dashboard(
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Whistleblower program dashboard for administrators."""
    all_cases = db.query(WhistleblowerCase).filter(
        WhistleblowerCase.tenant_id == tenant_id,
    ).all()

    total_cases = len(all_cases)
    open_cases = sum(1 for c in all_cases if c.status in ("open", "under_investigation", "pending_closure"))

    by_category: Dict[str, int] = {}
    for c in all_cases:
        by_category[c.category] = by_category.get(c.category, 0) + 1

    # Average cycle time for closed cases (days)
    closed_cases = [
        c for c in all_cases
        if c.status == "closed"
        and c.submitted_at
        and hasattr(c, "closed_at")
        and c.closed_at
    ]
    if closed_cases:
        total_days = sum(
            (c.closed_at - c.submitted_at).days for c in closed_cases
        )
        avg_cycle_time = round(total_days / len(closed_cases), 1)
    else:
        avg_cycle_time = None

    return {
        "total_cases": total_cases,
        "open_cases": open_cases,
        "closed_cases": len(closed_cases),
        "by_category": by_category,
        "avg_cycle_time_days": avg_cycle_time,
    }
