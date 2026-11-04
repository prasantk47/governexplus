"""
Issue Tracker — Common GRC Issue & Remediation Engine

One shared issue lifecycle across all GRC modules:
risk, controls, audit, fraud, access violations, vendor, compliance.
"""

import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from api.dependencies import get_current_user
from db.database import get_db
from db.models.issue_tracker import (
    GRCIssue, GRCIssueAction,
    IssueSeverity, IssueStatus, IssueSource, IssueType, ActionType
)

router = APIRouter(tags=["Issue Tracker"])


def _get_tenant_id(user: dict = Depends(get_current_user)) -> str:
    return user.get("tenant_id", "default")


def _new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12].upper()}"


def _issue_or_404(db: Session, issue_id: str, tenant_id: str) -> GRCIssue:
    issue = db.query(GRCIssue).filter_by(issue_id=issue_id, tenant_id=tenant_id).first()
    if not issue:
        raise HTTPException(status_code=404, detail=f"Issue {issue_id} not found")
    return issue


# ─── Request/Response models ──────────────────────────────────────────────────

class IssueCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=500)
    description: Optional[str] = None
    issue_type: str = "operational"
    source_module: str = "manual"
    severity: str = "medium"
    source_record_id: Optional[str] = None
    source_record_type: Optional[str] = None
    owner_id: Optional[str] = None
    owner_name: Optional[str] = None
    due_date: Optional[str] = None
    target_remediation_date: Optional[str] = None
    root_cause: Optional[str] = None
    root_cause_category: Optional[str] = None
    financial_impact: Optional[int] = None
    regulatory_impact: bool = False
    reputational_impact: bool = False
    remediation_plan: Optional[str] = None
    tags: List[str] = []
    extra: Dict[str, Any] = {}


class IssueUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    severity: Optional[str] = None
    owner_id: Optional[str] = None
    owner_name: Optional[str] = None
    due_date: Optional[str] = None
    target_remediation_date: Optional[str] = None
    root_cause: Optional[str] = None
    root_cause_category: Optional[str] = None
    financial_impact: Optional[int] = None
    regulatory_impact: Optional[bool] = None
    reputational_impact: Optional[bool] = None
    remediation_plan: Optional[str] = None
    remediation_progress: Optional[int] = None
    tags: Optional[List[str]] = None


class ActionCreate(BaseModel):
    action_type: str = "note"
    notes: Optional[str] = None
    evidence_url: Optional[str] = None
    evidence_description: Optional[str] = None
    performed_by_name: Optional[str] = None


class StatusTransition(BaseModel):
    new_status: str
    notes: Optional[str] = None
    performed_by_name: Optional[str] = None


class ValidationDecision(BaseModel):
    passed: bool
    notes: Optional[str] = None
    performed_by_name: Optional[str] = None


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/issues", status_code=201)
def create_issue(
    body: IssueCreate,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
    user: dict = Depends(get_current_user),
):
    """Create a new GRC issue from any module."""
    due = datetime.fromisoformat(body.due_date) if body.due_date else None
    target = datetime.fromisoformat(body.target_remediation_date) if body.target_remediation_date else None

    issue = GRCIssue(
        issue_id=_new_id("ISS"),
        tenant_id=tenant_id,
        title=body.title,
        description=body.description,
        issue_type=body.issue_type,
        source_module=body.source_module,
        severity=body.severity,
        status="open",
        source_record_id=body.source_record_id,
        source_record_type=body.source_record_type,
        owner_id=body.owner_id,
        owner_name=body.owner_name,
        due_date=due,
        target_remediation_date=target,
        root_cause=body.root_cause,
        root_cause_category=body.root_cause_category,
        financial_impact=body.financial_impact,
        regulatory_impact=body.regulatory_impact,
        reputational_impact=body.reputational_impact,
        remediation_plan=body.remediation_plan,
        tags=body.tags,
        extra=body.extra,
        created_by=user.get("user_id"),
        identified_date=datetime.utcnow(),
    )
    db.add(issue)

    # Initial action log
    action = GRCIssueAction(
        action_id=_new_id("ACT"),
        issue_id=issue.issue_id,
        tenant_id=tenant_id,
        action_type="note",
        performed_by=user.get("user_id", "system"),
        performed_by_name=user.get("full_name", ""),
        notes=f"Issue created from {body.source_module}",
        new_status="open",
    )
    db.add(action)
    db.commit()
    db.refresh(issue)
    return issue.to_dict()


@router.get("/issues")
def list_issues(
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
    status: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    source_module: Optional[str] = Query(None),
    issue_type: Optional[str] = Query(None),
    owner_id: Optional[str] = Query(None),
    overdue_only: bool = Query(False),
    limit: int = Query(100, le=500),
    offset: int = Query(0),
):
    """List issues with filters."""
    q = db.query(GRCIssue).filter(GRCIssue.tenant_id == tenant_id)
    if status:
        q = q.filter(GRCIssue.status == status)
    if severity:
        q = q.filter(GRCIssue.severity == severity)
    if source_module:
        q = q.filter(GRCIssue.source_module == source_module)
    if issue_type:
        q = q.filter(GRCIssue.issue_type == issue_type)
    if owner_id:
        q = q.filter(GRCIssue.owner_id == owner_id)
    if overdue_only:
        q = q.filter(GRCIssue.due_date < datetime.utcnow(), GRCIssue.status.notin_(["closed", "accepted"]))

    total = q.count()
    issues = q.order_by(GRCIssue.created_at.desc()).offset(offset).limit(limit).all()
    return {
        "total": total,
        "issues": [i.to_dict() for i in issues],
        "offset": offset,
        "limit": limit,
    }


@router.get("/issues/summary")
def get_issues_summary(
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Dashboard KPIs: counts by status, severity, module."""
    all_issues = db.query(GRCIssue).filter(GRCIssue.tenant_id == tenant_id).all()
    now = datetime.utcnow()

    by_status: Dict[str, int] = {}
    by_severity: Dict[str, int] = {}
    by_module: Dict[str, int] = {}
    overdue = 0

    for i in all_issues:
        by_status[i.status] = by_status.get(i.status, 0) + 1
        by_severity[i.severity] = by_severity.get(i.severity, 0) + 1
        by_module[i.source_module] = by_module.get(i.source_module, 0) + 1
        if i.due_date and i.due_date < now and i.status not in ("closed", "accepted"):
            overdue += 1

    open_count = sum(v for k, v in by_status.items() if k not in ("closed", "accepted"))
    return {
        "total": len(all_issues),
        "open": open_count,
        "overdue": overdue,
        "by_status": by_status,
        "by_severity": by_severity,
        "by_module": by_module,
        "critical_open": sum(1 for i in all_issues if i.severity == "critical" and i.status not in ("closed", "accepted")),
        "high_open": sum(1 for i in all_issues if i.severity == "high" and i.status not in ("closed", "accepted")),
    }


@router.get("/issues/{issue_id}")
def get_issue(
    issue_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    issue = _issue_or_404(db, issue_id, tenant_id)
    result = issue.to_dict()
    result["actions"] = [a.to_dict() for a in sorted(issue.actions, key=lambda x: x.performed_at)]
    return result


@router.put("/issues/{issue_id}")
def update_issue(
    issue_id: str,
    body: IssueUpdate,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
    user: dict = Depends(get_current_user),
):
    issue = _issue_or_404(db, issue_id, tenant_id)
    updates = body.model_dump(exclude_none=True)

    for field in ("due_date", "target_remediation_date"):
        if field in updates and updates[field]:
            updates[field] = datetime.fromisoformat(updates[field])

    for k, v in updates.items():
        setattr(issue, k, v)

    issue.last_updated_by = user.get("user_id")
    db.commit()
    db.refresh(issue)
    return issue.to_dict()


@router.post("/issues/{issue_id}/status")
def transition_status(
    issue_id: str,
    body: StatusTransition,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
    user: dict = Depends(get_current_user),
):
    """Move an issue through its lifecycle."""
    issue = _issue_or_404(db, issue_id, tenant_id)
    old_status = issue.status

    valid_transitions = {
        "open": ["assigned", "in_remediation", "accepted", "closed"],
        "assigned": ["in_remediation", "open", "accepted"],
        "in_remediation": ["pending_validation", "open", "closed"],
        "pending_validation": ["closed", "in_remediation"],
        "closed": ["open"],
        "accepted": ["open"],
        "overdue": ["in_remediation", "assigned"],
    }
    allowed = valid_transitions.get(old_status, [])
    if body.new_status not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot transition from '{old_status}' to '{body.new_status}'. Allowed: {allowed}"
        )

    issue.status = body.new_status
    issue.last_updated_by = user.get("user_id")

    if body.new_status == "closed":
        issue.closed_date = datetime.utcnow()
    if body.new_status == "assigned" and issue.assigned_at is None:
        issue.assigned_at = datetime.utcnow()
        issue.assigned_by = user.get("user_id")

    action = GRCIssueAction(
        action_id=_new_id("ACT"),
        issue_id=issue_id,
        tenant_id=tenant_id,
        action_type="status_change",
        performed_by=user.get("user_id", "system"),
        performed_by_name=body.performed_by_name or user.get("full_name", ""),
        notes=body.notes,
        old_status=old_status,
        new_status=body.new_status,
    )
    db.add(action)
    db.commit()
    db.refresh(issue)
    return issue.to_dict()


@router.post("/issues/{issue_id}/assign")
def assign_issue(
    issue_id: str,
    owner_id: str = Query(...),
    owner_name: str = Query(""),
    notes: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
    user: dict = Depends(get_current_user),
):
    """Assign ownership of an issue."""
    issue = _issue_or_404(db, issue_id, tenant_id)
    old_owner = issue.owner_id
    issue.owner_id = owner_id
    issue.owner_name = owner_name
    issue.assigned_at = datetime.utcnow()
    issue.assigned_by = user.get("user_id")
    if issue.status == "open":
        issue.status = "assigned"

    action = GRCIssueAction(
        action_id=_new_id("ACT"),
        issue_id=issue_id,
        tenant_id=tenant_id,
        action_type="note",
        performed_by=user.get("user_id", "system"),
        notes=f"Assigned to {owner_name or owner_id} (was: {old_owner or 'unassigned'}). {notes or ''}",
        new_status=issue.status,
    )
    db.add(action)
    db.commit()
    return {"message": "Issue assigned", "owner_id": owner_id}


@router.post("/issues/{issue_id}/actions")
def add_action(
    issue_id: str,
    body: ActionCreate,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
    user: dict = Depends(get_current_user),
):
    """Add a remediation note, evidence, or escalation log."""
    _issue_or_404(db, issue_id, tenant_id)
    action = GRCIssueAction(
        action_id=_new_id("ACT"),
        issue_id=issue_id,
        tenant_id=tenant_id,
        action_type=body.action_type,
        performed_by=user.get("user_id", "system"),
        performed_by_name=body.performed_by_name or user.get("full_name", ""),
        notes=body.notes,
        evidence_url=body.evidence_url,
        evidence_description=body.evidence_description,
    )
    db.add(action)
    db.commit()
    return action.to_dict()


@router.post("/issues/{issue_id}/validate")
def validate_issue(
    issue_id: str,
    body: ValidationDecision,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
    user: dict = Depends(get_current_user),
):
    """Validator independently confirms remediation is complete."""
    issue = _issue_or_404(db, issue_id, tenant_id)
    if issue.status != "pending_validation":
        raise HTTPException(400, "Issue must be in pending_validation status to validate")

    issue.validated_by = user.get("user_id")
    issue.validated_at = datetime.utcnow()

    if body.passed:
        issue.status = "closed"
        issue.closed_date = datetime.utcnow()
        new_status = "closed"
        note = f"Validation PASSED — {body.notes or 'remediation confirmed effective'}"
    else:
        issue.status = "in_remediation"
        new_status = "in_remediation"
        note = f"Validation FAILED — {body.notes or 'remediation insufficient, returned for rework'}"

    action = GRCIssueAction(
        action_id=_new_id("ACT"),
        issue_id=issue_id,
        tenant_id=tenant_id,
        action_type="validation",
        performed_by=user.get("user_id", "system"),
        performed_by_name=body.performed_by_name or user.get("full_name", ""),
        notes=note,
        old_status="pending_validation",
        new_status=new_status,
    )
    db.add(action)
    db.commit()
    db.refresh(issue)
    return issue.to_dict()


@router.post("/issues/{issue_id}/accept")
def accept_risk(
    issue_id: str,
    rationale: str = Query(..., description="Justification for accepting without remediation"),
    accepted_by_name: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
    user: dict = Depends(get_current_user),
):
    """Accept an issue without remediation (risk acceptance)."""
    issue = _issue_or_404(db, issue_id, tenant_id)
    issue.status = "accepted"
    issue.extra = {**(issue.extra or {}), "acceptance_rationale": rationale, "accepted_by": user.get("user_id")}

    action = GRCIssueAction(
        action_id=_new_id("ACT"),
        issue_id=issue_id,
        tenant_id=tenant_id,
        action_type="acceptance",
        performed_by=user.get("user_id", "system"),
        performed_by_name=accepted_by_name or user.get("full_name", ""),
        notes=f"Issue accepted without remediation: {rationale}",
        old_status=issue.status,
        new_status="accepted",
    )
    db.add(action)
    db.commit()
    return {"message": "Issue accepted", "issue_id": issue_id}


@router.get("/issues/{issue_id}/actions")
def get_actions(
    issue_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    _issue_or_404(db, issue_id, tenant_id)
    actions = (db.query(GRCIssueAction)
               .filter_by(issue_id=issue_id, tenant_id=tenant_id)
               .order_by(GRCIssueAction.performed_at.asc())
               .all())
    return [a.to_dict() for a in actions]


@router.delete("/issues/{issue_id}")
def delete_issue(
    issue_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
    user: dict = Depends(get_current_user),
):
    issue = _issue_or_404(db, issue_id, tenant_id)
    db.delete(issue)
    db.commit()
    return {"message": f"Issue {issue_id} deleted"}
