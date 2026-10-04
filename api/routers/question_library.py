"""
Question Library and Questionnaire API Router

Covers:
  PC-SAP-GAP-08 : Reusable assessment question library
  PC-SAP-GAP-09 : Assembled questionnaires from library
  PC-SAP-GAP-10 : Questionnaire responses with reviewer sign-off
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Dict, List, Optional, Any
from datetime import datetime
from sqlalchemy.orm import Session
import uuid

from db.database import get_db
from db.models.process_control import (
    QuestionLibrary, QuestionType,
    Questionnaire, QuestionnaireType,
    QuestionnaireResponse, ResponseStatus,
)

router = APIRouter(tags=["Question Library & Questionnaires"])


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


def _question_or_404(db: Session, question_id: str, tenant_id: str) -> QuestionLibrary:
    q = db.query(QuestionLibrary).filter(
        QuestionLibrary.question_id == question_id,
        QuestionLibrary.tenant_id == tenant_id,
        QuestionLibrary.is_active.is_(True),
    ).first()
    if not q:
        raise HTTPException(status_code=404, detail=f"Question '{question_id}' not found")
    return q


def _questionnaire_or_404(db: Session, questionnaire_id: str, tenant_id: str) -> Questionnaire:
    qnr = db.query(Questionnaire).filter(
        Questionnaire.questionnaire_id == questionnaire_id,
        Questionnaire.tenant_id == tenant_id,
        Questionnaire.is_active.is_(True),
    ).first()
    if not qnr:
        raise HTTPException(status_code=404, detail=f"Questionnaire '{questionnaire_id}' not found")
    return qnr


def _response_or_404(db: Session, response_id: str, tenant_id: str) -> QuestionnaireResponse:
    r = db.query(QuestionnaireResponse).filter(
        QuestionnaireResponse.response_id == response_id,
        QuestionnaireResponse.tenant_id == tenant_id,
    ).first()
    if not r:
        raise HTTPException(status_code=404, detail=f"Response '{response_id}' not found")
    return r


def _compute_score(questions: List[Dict], responses: Dict[str, Any]) -> Optional[float]:
    """
    Compute a weighted average score for rating-scale questionnaires.
    Returns None if no ratable answers are present.
    """
    total, count = 0.0, 0
    for q in (questions or []):
        qid = q.get("question_id")
        if q.get("question_type") == QuestionType.RATING_SCALE.value and qid in (responses or {}):
            try:
                val = float(responses[qid])
                scale_max = float(q.get("scale_max") or 5)
                total += val / scale_max * 100
                count += 1
            except (TypeError, ValueError):
                pass
    return round(total / count, 2) if count else None


# ===========================================================================
# Question Library  (PC-SAP-GAP-08)
# ===========================================================================

@router.post("/questions", status_code=201)
def create_question(
    body: Dict[str, Any] = Body(default={}),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Add a reusable question to the library."""
    try:
        q_type = QuestionType(body.get("question_type", "yes_no"))
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid question_type")

    q = QuestionLibrary(
        tenant_id=tenant_id,
        question_id=body.get("question_id") or _new_id("Q"),
        question_text=body["question_text"],
        description=body.get("description"),
        question_type=q_type,
        category=body.get("category", "general"),
        options=body.get("options"),
        scale_min=body.get("scale_min"),
        scale_max=body.get("scale_max"),
        required=body.get("required", True),
        applicable_modules=body.get("applicable_modules", []),
        tags=body.get("tags", []),
        is_active=True,
        usage_count=0,
    )
    db.add(q)
    db.commit()
    db.refresh(q)
    return q.to_dict()


@router.get("/questions")
def list_questions(
    category: Optional[str] = Query(None),
    question_type: Optional[str] = Query(None),
    applicable_modules: Optional[str] = Query(None, description="Comma-separated module codes, e.g. 'pc,rm'"),
    tags: Optional[str] = Query(None, description="Comma-separated tags"),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    q = db.query(QuestionLibrary).filter(
        QuestionLibrary.tenant_id == tenant_id,
        QuestionLibrary.is_active.is_(True),
    )
    if category:
        q = q.filter(QuestionLibrary.category == category)
    if question_type:
        try:
            q = q.filter(QuestionLibrary.question_type == QuestionType(question_type))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid question_type")
    questions = q.order_by(QuestionLibrary.usage_count.desc()).all()

    # Post-filter by applicable_modules / tags (JSON array columns)
    if applicable_modules:
        mods = [m.strip() for m in applicable_modules.split(",")]
        questions = [
            q for q in questions
            if any(m in (q.applicable_modules or []) for m in mods)
        ]
    if tags:
        tag_list = [t.strip() for t in tags.split(",")]
        questions = [
            q for q in questions
            if any(t in (q.tags or []) for t in tag_list)
        ]

    return {"total": len(questions), "questions": [q.to_dict() for q in questions]}


@router.put("/questions/{question_id}")
def update_question(
    question_id: str,
    body: Dict[str, Any] = Body(default={}),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    q = _question_or_404(db, question_id, tenant_id)
    scalar_fields = [
        "question_text", "description", "category", "options",
        "scale_min", "scale_max", "required", "applicable_modules", "tags",
    ]
    for field in scalar_fields:
        if field in body:
            setattr(q, field, body[field])
    if "question_type" in body:
        q.question_type = QuestionType(body["question_type"])
    if "is_active" in body:
        q.is_active = body["is_active"]
    db.commit()
    db.refresh(q)
    return q.to_dict()


# ===========================================================================
# Questionnaires  (PC-SAP-GAP-09)
# ===========================================================================

@router.post("/", status_code=201)
def create_questionnaire(
    body: Dict[str, Any] = Body(default={}),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """
    Assemble a questionnaire from question_ids.

    Body fields:
      title, description, questionnaire_type, question_ids (list of question_id strings),
      target_module, linked_object_type, linked_object_id, is_template, created_by
    """
    try:
        qnr_type = QuestionnaireType(body.get("questionnaire_type", "control_assessment"))
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid questionnaire_type")

    question_ids: List[str] = body.get("question_ids", [])
    assembled_questions: List[Dict] = []
    for idx, qid in enumerate(question_ids):
        q_obj = db.query(QuestionLibrary).filter(
            QuestionLibrary.question_id == qid,
            QuestionLibrary.tenant_id == tenant_id,
            QuestionLibrary.is_active.is_(True),
        ).first()
        if not q_obj:
            raise HTTPException(status_code=404, detail=f"Question '{qid}' not found in library")
        assembled_questions.append({
            "question_id": q_obj.question_id,
            "question_text": q_obj.question_text,
            "question_type": q_obj.question_type.value,
            "category": q_obj.category,
            "options": q_obj.options,
            "scale_min": q_obj.scale_min,
            "scale_max": q_obj.scale_max,
            "required": q_obj.required,
            "sort_order": idx,
        })
        # Increment usage counter
        q_obj.usage_count = (q_obj.usage_count or 0) + 1

    qnr = Questionnaire(
        tenant_id=tenant_id,
        questionnaire_id=body.get("questionnaire_id") or _new_id("QNR"),
        title=body["title"],
        description=body.get("description"),
        questionnaire_type=qnr_type,
        questions=assembled_questions,
        target_module=body.get("target_module"),
        linked_object_type=body.get("linked_object_type"),
        linked_object_id=body.get("linked_object_id"),
        created_by=body.get("created_by"),
        is_template=body.get("is_template", False),
        is_active=True,
    )
    db.add(qnr)
    db.commit()
    db.refresh(qnr)
    return qnr.to_dict()


@router.get("/")
def list_questionnaires(
    questionnaire_type: Optional[str] = Query(None),
    target_module: Optional[str] = Query(None),
    is_template: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    q = db.query(Questionnaire).filter(
        Questionnaire.tenant_id == tenant_id,
        Questionnaire.is_active.is_(True),
    )
    if questionnaire_type:
        try:
            q = q.filter(Questionnaire.questionnaire_type == QuestionnaireType(questionnaire_type))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid questionnaire_type")
    if target_module:
        q = q.filter(Questionnaire.target_module == target_module)
    if is_template is not None:
        q = q.filter(Questionnaire.is_template == is_template)
    questionnaires = q.order_by(Questionnaire.created_at.desc()).all()
    return {"total": len(questionnaires), "questionnaires": [qnr.to_dict() for qnr in questionnaires]}


@router.get("/{questionnaire_id}")
def get_questionnaire(
    questionnaire_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Get questionnaire with full embedded question details."""
    qnr = _questionnaire_or_404(db, questionnaire_id, tenant_id)
    data = qnr.to_dict()
    data["response_count"] = db.query(QuestionnaireResponse).filter(
        QuestionnaireResponse.questionnaire_id == qnr.id,
        QuestionnaireResponse.tenant_id == tenant_id,
    ).count()
    return data


@router.post("/{questionnaire_id}/clone")
def clone_questionnaire(
    questionnaire_id: str,
    body: Dict[str, Any] = Body(default={}),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """
    Clone a questionnaire template to create a new use-specific instance.
    The clone has is_template=False and can be linked to a specific object.
    """
    source = _questionnaire_or_404(db, questionnaire_id, tenant_id)

    clone = Questionnaire(
        tenant_id=tenant_id,
        questionnaire_id=_new_id("QNR"),
        title=body.get("title", f"Copy of {source.title}"),
        description=body.get("description", source.description),
        questionnaire_type=source.questionnaire_type,
        questions=source.questions,
        target_module=body.get("target_module", source.target_module),
        linked_object_type=body.get("linked_object_type", source.linked_object_type),
        linked_object_id=body.get("linked_object_id"),
        created_by=body.get("created_by"),
        is_template=False,
        is_active=True,
    )
    db.add(clone)
    db.commit()
    db.refresh(clone)
    return clone.to_dict()


# ===========================================================================
# Questionnaire Responses  (PC-SAP-GAP-10)
# ===========================================================================

@router.post("/{questionnaire_id}/responses", status_code=201)
def submit_response(
    questionnaire_id: str,
    body: Dict[str, Any] = Body(default={}),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """
    Start or submit a questionnaire response for a respondent.

    Body fields:
      respondent_id, respondent_name, respondent_email
      responses : {question_id: answer_value}
    """
    qnr = _questionnaire_or_404(db, questionnaire_id, tenant_id)

    if not body.get("respondent_id"):
        raise HTTPException(status_code=400, detail="respondent_id is required")

    # Prevent duplicate active responses from same respondent
    existing = db.query(QuestionnaireResponse).filter(
        QuestionnaireResponse.questionnaire_id == qnr.id,
        QuestionnaireResponse.respondent_id == body["respondent_id"],
        QuestionnaireResponse.tenant_id == tenant_id,
        QuestionnaireResponse.status.in_([
            ResponseStatus.PENDING,
            ResponseStatus.IN_PROGRESS,
        ]),
    ).first()
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Respondent already has an active response '{existing.response_id}'",
        )

    answers = body.get("responses", {})
    score = _compute_score(qnr.questions or [], answers)

    r = QuestionnaireResponse(
        tenant_id=tenant_id,
        response_id=_new_id("QR"),
        questionnaire_id=qnr.id,
        respondent_id=body["respondent_id"],
        respondent_name=body.get("respondent_name"),
        respondent_email=body.get("respondent_email"),
        responses=answers,
        score=score,
        status=ResponseStatus.IN_PROGRESS if answers else ResponseStatus.PENDING,
    )
    db.add(r)
    db.commit()
    db.refresh(r)
    return r.to_dict()


@router.get("/{questionnaire_id}/responses")
def list_responses(
    questionnaire_id: str,
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    qnr = _questionnaire_or_404(db, questionnaire_id, tenant_id)
    q = db.query(QuestionnaireResponse).filter(
        QuestionnaireResponse.questionnaire_id == qnr.id,
        QuestionnaireResponse.tenant_id == tenant_id,
    )
    if status:
        try:
            q = q.filter(QuestionnaireResponse.status == ResponseStatus(status))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid status")
    responses = q.order_by(QuestionnaireResponse.created_at.desc()).all()
    return {"total": len(responses), "responses": [r.to_dict() for r in responses]}


@router.put("/responses/{response_id}/submit")
def mark_response_submitted(
    response_id: str,
    body: Dict[str, Any] = Body(default={}),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Mark a response as submitted (finalise answers)."""
    r = _response_or_404(db, response_id, tenant_id)
    if r.status not in (ResponseStatus.PENDING, ResponseStatus.IN_PROGRESS):
        raise HTTPException(status_code=400, detail="Response is already submitted or reviewed")

    # Update answers if provided
    if "responses" in body:
        r.responses = body["responses"]
        # Re-compute score
        qnr = db.query(Questionnaire).filter(Questionnaire.id == r.questionnaire_id).first()
        if qnr:
            r.score = _compute_score(qnr.questions or [], r.responses)

    r.status = ResponseStatus.SUBMITTED
    r.submitted_at = datetime.utcnow()
    db.commit()
    db.refresh(r)
    return r.to_dict()


@router.put("/responses/{response_id}/review")
def review_response(
    response_id: str,
    body: Dict[str, Any] = Body(default={}),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Reviewer sign-off on a submitted response."""
    r = _response_or_404(db, response_id, tenant_id)
    if r.status != ResponseStatus.SUBMITTED:
        raise HTTPException(status_code=400, detail="Response must be submitted before review")
    if not body.get("reviewed_by"):
        raise HTTPException(status_code=400, detail="reviewed_by is required")
    r.reviewed_by = body["reviewed_by"]
    r.reviewed_at = datetime.utcnow()
    r.review_comments = body.get("review_comments")
    r.status = ResponseStatus.REVIEWED
    db.commit()
    db.refresh(r)
    return r.to_dict()


@router.get("/responses/pending")
def list_pending_responses(
    respondent_id: str = Query(...),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """List all pending/in-progress responses for a given respondent."""
    responses = db.query(QuestionnaireResponse).filter(
        QuestionnaireResponse.tenant_id == tenant_id,
        QuestionnaireResponse.respondent_id == respondent_id,
        QuestionnaireResponse.status.in_([
            ResponseStatus.PENDING,
            ResponseStatus.IN_PROGRESS,
        ]),
    ).order_by(QuestionnaireResponse.created_at.asc()).all()
    return {"total": len(responses), "responses": [r.to_dict() for r in responses]}
