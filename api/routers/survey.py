"""
Survey Engine API Router

Standalone survey platform for GRC use-cases:
  - Control owner attestations
  - Vendor due-diligence questionnaires
  - Employee compliance awareness
  - General-purpose surveys with scoring
  - Distribution management and anonymous response support
  - Analytics: completion rates, score distributions, per-question breakdowns
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
import uuid

from db.database import get_db
from db.models.extended_modules import StandaloneSurvey, SurveyDistribution, SurveyAnswer

router = APIRouter(tags=["Survey Engine"])


# ---------------------------------------------------------------------------
# Tenant helper
# ---------------------------------------------------------------------------

def _get_tenant_id() -> str:
    from core.tenant import get_current_tenant
    ctx = get_current_tenant()
    return ctx.tenant_id if ctx else "default"


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


# ---------------------------------------------------------------------------
# 404 helpers
# ---------------------------------------------------------------------------

def _survey_or_404(db: Session, survey_id: str, tenant_id: str) -> StandaloneSurvey:
    obj = db.query(StandaloneSurvey).filter(
        StandaloneSurvey.id == survey_id,
        StandaloneSurvey.tenant_id == tenant_id,
    ).first()
    if not obj:
        raise HTTPException(status_code=404, detail=f"Survey '{survey_id}' not found")
    return obj


def _distribution_or_404(db: Session, distribution_id: str, tenant_id: str) -> SurveyDistribution:
    obj = db.query(SurveyDistribution).filter(
        SurveyDistribution.id == distribution_id,
        SurveyDistribution.tenant_id == tenant_id,
    ).first()
    if not obj:
        raise HTTPException(status_code=404, detail=f"Distribution '{distribution_id}' not found")
    return obj


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class QuestionSchema(BaseModel):
    question_id: str
    question_text: str
    question_type: str = Field(
        ...,
        description="text | single_choice | multiple_choice | rating | yes_no | date | file_upload",
    )
    options: Optional[List[str]] = None
    is_required: bool = True
    score_weight: Optional[float] = 1.0
    help_text: Optional[str] = None
    order: int = 0


class SurveyCreate(BaseModel):
    title: str
    survey_type: str = Field(
        default="general",
        description="general | attestation | vendor_due_diligence | awareness | assessment",
    )
    description: Optional[str] = None
    status: str = Field(default="draft", description="draft | active | closed | archived")
    questions: List[QuestionSchema] = Field(default_factory=list)
    allow_anonymous: bool = False
    requires_completion: bool = True
    due_date: Optional[str] = None
    owner_id: Optional[str] = None
    owner_name: Optional[str] = None
    tags: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None


class SurveyUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    questions: Optional[List[QuestionSchema]] = None
    allow_anonymous: Optional[bool] = None
    requires_completion: Optional[bool] = None
    due_date: Optional[str] = None
    owner_id: Optional[str] = None
    tags: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None


class DistributeRequest(BaseModel):
    """Distribute a survey to a list of recipients."""
    recipients: List[Dict[str, Any]] = Field(
        ...,
        description="List of recipient objects: [{user_id, email, name}]",
    )
    due_date: Optional[str] = None
    send_reminder_days: Optional[int] = None
    message: Optional[str] = None


class AnswerSubmission(BaseModel):
    """Response payload from a survey recipient."""
    answers: List[Dict[str, Any]] = Field(
        ...,
        description="List of answers: [{question_id, value}]",
    )
    is_anonymous: bool = False
    respondent_name: Optional[str] = None
    respondent_email: Optional[str] = None
    completed_at: Optional[str] = None


# ---------------------------------------------------------------------------
# Surveys CRUD
# ---------------------------------------------------------------------------

@router.get("/")
def list_surveys(
    survey_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """List surveys with optional filters."""
    q = db.query(StandaloneSurvey).filter(StandaloneSurvey.tenant_id == tenant_id)
    if survey_type:
        q = q.filter(StandaloneSurvey.survey_type == survey_type)
    if status:
        q = q.filter(StandaloneSurvey.status == status)
    surveys = q.order_by(StandaloneSurvey.created_at.desc()).all()
    return {"total": len(surveys), "surveys": [s.to_dict() for s in surveys]}


@router.post("/", status_code=201)
def create_survey(
    body: SurveyCreate,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Create a new survey."""
    survey = StandaloneSurvey(
        id=_new_id("SRV"),
        tenant_id=tenant_id,
        title=body.title,
        survey_type=body.survey_type,
        description=body.description,
        status=body.status,
        questions=[q.dict() for q in body.questions],
        allow_anonymous=body.allow_anonymous,
        requires_completion=body.requires_completion,
        due_date=datetime.fromisoformat(body.due_date) if body.due_date else None,
        owner_id=body.owner_id,
        owner_name=body.owner_name,
        tags=body.tags or [],
        metadata_=body.metadata,
    )
    db.add(survey)
    db.commit()
    db.refresh(survey)
    return survey.to_dict()


@router.get("/{id}")
def get_survey(
    id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Get full survey definition including all questions."""
    return _survey_or_404(db, id, tenant_id).to_dict()


@router.put("/{id}")
def update_survey(
    id: str,
    body: SurveyUpdate,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Update a survey. Active surveys: only status/due_date may be updated."""
    survey = _survey_or_404(db, id, tenant_id)
    if survey.status == "active" and body.questions is not None:
        raise HTTPException(
            status_code=400,
            detail="Questions cannot be modified on an active survey. Close it first.",
        )
    if body.title is not None:
        survey.title = body.title
    if body.description is not None:
        survey.description = body.description
    if body.status is not None:
        survey.status = body.status
    if body.questions is not None:
        survey.questions = [q.dict() for q in body.questions]
    if body.allow_anonymous is not None:
        survey.allow_anonymous = body.allow_anonymous
    if body.requires_completion is not None:
        survey.requires_completion = body.requires_completion
    if body.due_date:
        survey.due_date = datetime.fromisoformat(body.due_date)
    if body.owner_id is not None:
        survey.owner_id = body.owner_id
    if body.tags is not None:
        survey.tags = body.tags
    if body.metadata is not None:
        survey.metadata_ = body.metadata
    db.commit()
    db.refresh(survey)
    return survey.to_dict()


@router.delete("/{id}", status_code=204)
def delete_survey(
    id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Delete a draft survey (only drafts can be deleted)."""
    survey = _survey_or_404(db, id, tenant_id)
    if survey.status != "draft":
        raise HTTPException(
            status_code=400,
            detail=f"Only 'draft' surveys can be deleted; current status: '{survey.status}'",
        )
    db.delete(survey)
    db.commit()


# ---------------------------------------------------------------------------
# Distribution
# ---------------------------------------------------------------------------

@router.post("/{id}/distribute", status_code=201)
def distribute_survey(
    id: str,
    body: DistributeRequest,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """
    Distribute a survey to a list of recipients.

    Creates one SurveyDistribution record per recipient. Each distribution gets
    its own unique access token that can be sent to the recipient.
    """
    survey = _survey_or_404(db, id, tenant_id)
    if survey.status not in ("draft", "active"):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot distribute a survey in '{survey.status}' status",
        )
    if survey.status == "draft":
        survey.status = "active"

    created_distributions = []
    for recipient in body.recipients:
        dist = SurveyDistribution(
            id=_new_id("SDST"),
            tenant_id=tenant_id,
            survey_id=survey.id,
            recipient_user_id=recipient.get("user_id"),
            recipient_email=recipient.get("email"),
            recipient_name=recipient.get("name"),
            due_date=datetime.fromisoformat(body.due_date) if body.due_date else survey.due_date,
            send_reminder_days=body.send_reminder_days,
            distribution_message=body.message,
            status="sent",
            sent_at=datetime.utcnow(),
            access_token=_new_id("TOKEN"),
        )
        db.add(dist)
        created_distributions.append(dist)

    db.commit()
    for d in created_distributions:
        db.refresh(d)

    return {
        "survey_id": id,
        "recipients_count": len(created_distributions),
        "distributions": [d.to_dict() for d in created_distributions],
    }


@router.get("/{id}/distributions")
def list_distributions(
    id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """List all distributions for a survey with completion status."""
    _survey_or_404(db, id, tenant_id)
    distributions = db.query(SurveyDistribution).filter(
        SurveyDistribution.survey_id == id,
        SurveyDistribution.tenant_id == tenant_id,
    ).order_by(SurveyDistribution.sent_at.desc()).all()
    total = len(distributions)
    completed = sum(1 for d in distributions if d.status == "completed")
    return {
        "survey_id": id,
        "total": total,
        "completed": completed,
        "pending": total - completed,
        "completion_rate": round(completed / total * 100, 1) if total else 0.0,
        "distributions": [d.to_dict() for d in distributions],
    }


@router.get("/{id}/responses")
def list_responses(
    id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """List all submitted answers/responses for a survey."""
    _survey_or_404(db, id, tenant_id)
    # Get all distributions for this survey
    dist_ids = [
        d.id for d in db.query(SurveyDistribution).filter(
            SurveyDistribution.survey_id == id,
            SurveyDistribution.tenant_id == tenant_id,
        ).all()
    ]
    if not dist_ids:
        return {"survey_id": id, "total_responses": 0, "responses": []}
    answers = db.query(SurveyAnswer).filter(
        SurveyAnswer.distribution_id.in_(dist_ids),
        SurveyAnswer.tenant_id == tenant_id,
    ).order_by(SurveyAnswer.submitted_at.desc()).all()
    return {
        "survey_id": id,
        "total_responses": len(answers),
        "responses": [a.to_dict() for a in answers],
    }


@router.get("/{id}/analytics")
def get_survey_analytics(
    id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """
    Survey response analytics:
    - Completion rate
    - Score distribution (if questions have weights)
    - Per-question answer breakdown
    """
    survey = _survey_or_404(db, id, tenant_id)

    distributions = db.query(SurveyDistribution).filter(
        SurveyDistribution.survey_id == id,
        SurveyDistribution.tenant_id == tenant_id,
    ).all()

    total_distributed = len(distributions)
    completed = sum(1 for d in distributions if d.status == "completed")
    completion_rate = round(completed / total_distributed * 100, 1) if total_distributed else 0.0

    dist_ids = [d.id for d in distributions]
    answers = db.query(SurveyAnswer).filter(
        SurveyAnswer.distribution_id.in_(dist_ids),
        SurveyAnswer.tenant_id == tenant_id,
    ).all() if dist_ids else []

    # Per-question breakdown
    questions = survey.questions or []
    per_question: Dict[str, Any] = {}
    for q in questions:
        qid = q.get("question_id") or q.get("id")
        if not qid:
            continue
        q_answers = []
        for ans_record in answers:
            ans_data = ans_record.answers or []
            for ans in ans_data:
                if ans.get("question_id") == qid:
                    q_answers.append(ans.get("value"))
        value_counts: Dict[str, int] = {}
        for val in q_answers:
            key = str(val) if val is not None else "no_answer"
            value_counts[key] = value_counts.get(key, 0) + 1
        per_question[qid] = {
            "question_text": q.get("question_text"),
            "question_type": q.get("question_type"),
            "response_count": len(q_answers),
            "value_distribution": value_counts,
        }

    # Score distribution: sum weighted answers
    score_distribution: List[float] = []
    for ans_record in answers:
        total_score = 0.0
        ans_data = ans_record.answers or []
        for ans in ans_data:
            qid = ans.get("question_id")
            # Find question weight
            weight = 1.0
            for q in questions:
                if (q.get("question_id") or q.get("id")) == qid:
                    weight = float(q.get("score_weight", 1.0) or 1.0)
                    break
            val = ans.get("value")
            if isinstance(val, (int, float)):
                total_score += float(val) * weight
        score_distribution.append(round(total_score, 2))

    avg_score = round(sum(score_distribution) / len(score_distribution), 2) if score_distribution else None

    return {
        "survey_id": id,
        "total_distributed": total_distributed,
        "total_responses": len(answers),
        "completion_rate": completion_rate,
        "avg_score": avg_score,
        "score_distribution": score_distribution,
        "per_question": per_question,
    }


# ---------------------------------------------------------------------------
# Public-friendly: Respond to a distribution
# ---------------------------------------------------------------------------

@router.get("/respond/{distribution_id}")
def get_survey_form(
    distribution_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """
    Public-friendly endpoint — recipient retrieves the survey form.
    Returns survey questions without any sensitive administrative data.
    """
    dist = _distribution_or_404(db, distribution_id, tenant_id)
    if dist.status == "completed":
        raise HTTPException(status_code=400, detail="This survey has already been completed.")
    survey = db.query(StandaloneSurvey).filter(
        StandaloneSurvey.id == dist.survey_id,
        StandaloneSurvey.tenant_id == tenant_id,
    ).first()
    if not survey:
        raise HTTPException(status_code=404, detail="Survey not found.")
    if survey.status != "active":
        raise HTTPException(
            status_code=400,
            detail=f"This survey is currently '{survey.status}' and is not accepting responses.",
        )
    # Check due date
    if survey.due_date and datetime.utcnow() > survey.due_date:
        raise HTTPException(status_code=400, detail="The deadline for this survey has passed.")
    return {
        "distribution_id": distribution_id,
        "survey_title": survey.title,
        "survey_description": survey.description,
        "due_date": survey.due_date.isoformat() if survey.due_date else None,
        "allow_anonymous": survey.allow_anonymous,
        "questions": survey.questions or [],
    }


@router.post("/respond/{distribution_id}", status_code=201)
def submit_response(
    distribution_id: str,
    body: AnswerSubmission,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """
    Submit a survey response.
    Supports anonymous responses when the survey allows it.
    """
    dist = _distribution_or_404(db, distribution_id, tenant_id)
    if dist.status == "completed":
        raise HTTPException(status_code=409, detail="A response has already been submitted for this distribution.")

    survey = db.query(StandaloneSurvey).filter(
        StandaloneSurvey.id == dist.survey_id,
        StandaloneSurvey.tenant_id == tenant_id,
    ).first()
    if not survey:
        raise HTTPException(status_code=404, detail="Survey not found.")
    if survey.status != "active":
        raise HTTPException(
            status_code=400,
            detail=f"Survey is '{survey.status}' and not accepting responses.",
        )
    if body.is_anonymous and not survey.allow_anonymous:
        raise HTTPException(
            status_code=400,
            detail="This survey does not allow anonymous responses.",
        )

    # Validate required questions are answered
    required_question_ids = {
        q.get("question_id") or q.get("id")
        for q in (survey.questions or [])
        if q.get("is_required", True)
    }
    submitted_question_ids = {a.get("question_id") for a in body.answers}
    missing = required_question_ids - submitted_question_ids
    if missing:
        raise HTTPException(
            status_code=422,
            detail=f"Missing required question answers: {sorted(missing)}",
        )

    answer_record = SurveyAnswer(
        id=_new_id("SANS"),
        tenant_id=tenant_id,
        distribution_id=distribution_id,
        survey_id=dist.survey_id,
        is_anonymous=body.is_anonymous,
        respondent_name=None if body.is_anonymous else body.respondent_name,
        respondent_email=None if body.is_anonymous else body.respondent_email,
        answers=body.answers,
        submitted_at=datetime.fromisoformat(body.completed_at) if body.completed_at else datetime.utcnow(),
    )
    db.add(answer_record)
    dist.status = "completed"
    dist.completed_at = answer_record.submitted_at
    db.commit()
    db.refresh(answer_record)
    return {
        "message": "Thank you. Your response has been recorded.",
        "response_id": answer_record.id,
        "submitted_at": answer_record.submitted_at.isoformat(),
    }


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@router.get("/dashboard")
def get_survey_dashboard(
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Survey engine dashboard: active surveys, pending responses, overall completion rate."""
    surveys = db.query(StandaloneSurvey).filter(
        StandaloneSurvey.tenant_id == tenant_id,
    ).all()

    active_surveys = sum(1 for s in surveys if s.status == "active")

    all_distributions = db.query(SurveyDistribution).filter(
        SurveyDistribution.tenant_id == tenant_id,
    ).all()
    total_distributed = len(all_distributions)
    total_completed = sum(1 for d in all_distributions if d.status == "completed")
    pending_responses = total_distributed - total_completed
    completion_rate = round(total_completed / total_distributed * 100, 1) if total_distributed else 0.0

    # Per-survey breakdown for active surveys
    active_breakdown = []
    for s in surveys:
        if s.status != "active":
            continue
        s_dists = [d for d in all_distributions if d.survey_id == s.id]
        s_total = len(s_dists)
        s_done = sum(1 for d in s_dists if d.status == "completed")
        active_breakdown.append({
            "survey_id": s.id,
            "title": s.title,
            "survey_type": s.survey_type,
            "distributed": s_total,
            "completed": s_done,
            "completion_rate": round(s_done / s_total * 100, 1) if s_total else 0.0,
            "due_date": s.due_date.isoformat() if s.due_date else None,
        })

    return {
        "active_surveys": active_surveys,
        "pending_responses": pending_responses,
        "total_distributed": total_distributed,
        "total_completed": total_completed,
        "completion_rate": completion_rate,
        "active_surveys_breakdown": active_breakdown,
    }
