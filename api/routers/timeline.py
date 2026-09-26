"""
Access Timeline API Router

Provides endpoints for retrieving the complete history of access changes
for users and roles, and for investigating access loss events forensically.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional
from datetime import datetime

from core.timeline.tracker import (
    AccessTimelineTracker,
    Timeline,
    ChangeSummary,
    LossCauseAnalysis,
    TimelineEvent,
    ChangeImpact,
    TimelineEventType,
)

router = APIRouter(tags=["Access Timeline"])

# Single shared tracker instance
_tracker = AccessTimelineTracker()


# =============================================================================
# Request / Response Models
# =============================================================================


class InvestigateRequest(BaseModel):
    """Request body for access loss investigation."""

    user_id: str = Field(..., description="SAP user ID of the affected user, e.g. 'JOHN.SMITH'.")
    transaction: str = Field(..., description="Transaction code the user can no longer access, e.g. 'FB60'.")
    reported_loss_date: Optional[datetime] = Field(
        None,
        description=(
            "When the user reported the access loss (ISO 8601).  "
            "If omitted, the current timestamp is used."
        ),
    )


class TimelineEventResponse(BaseModel):
    """Serialised timeline event."""

    event_id: str
    event_type: str
    timestamp: str
    actor: str
    subject: str
    description: str
    system: str
    detail: Dict[str, Any]
    impact: str
    affected_tcodes: List[str]
    transport_request: Optional[str]
    ticket_reference: Optional[str]
    is_reversible: bool
    reversal_event_id: Optional[str]


class TimelineResponse(BaseModel):
    """Full timeline for a user or role."""

    subject_id: str
    subject_type: str
    subject_display_name: str
    period_start: str
    period_end: str
    event_count: int
    access_gained_count: int
    access_lost_count: int
    access_modified_count: int
    events: List[TimelineEventResponse]


class ChangeSummaryResponse(BaseModel):
    """Recent change digest for a user."""

    user_id: str
    period_days: int
    roles_added: List[str]
    roles_removed: List[str]
    roles_modified: List[str]
    org_level_changes: List[Dict]
    account_status_changes: List[Dict]
    net_access_change: str
    highest_impact_event: Optional[str]
    change_count: int
    last_change_timestamp: Optional[str]


class LossCauseResponse(BaseModel):
    """Forensic access loss analysis result."""

    user_id: str
    transaction: str
    reported_loss_date: str
    cause_category: str
    confidence: float
    root_cause_summary: str
    causal_chain: List[TimelineEventResponse]
    remediation_steps: List[str]
    related_tickets: List[str]
    similar_users_affected: List[str]


# =============================================================================
# Serialisation helpers
# =============================================================================


def _serialise_event(e: TimelineEvent) -> TimelineEventResponse:
    return TimelineEventResponse(
        event_id=e.event_id,
        event_type=e.event_type.value,
        timestamp=e.timestamp.isoformat(),
        actor=e.actor,
        subject=e.subject,
        description=e.description,
        system=e.system,
        detail=e.detail,
        impact=e.impact.value,
        affected_tcodes=e.affected_tcodes,
        transport_request=e.transport_request,
        ticket_reference=e.ticket_reference,
        is_reversible=e.is_reversible,
        reversal_event_id=e.reversal_event_id,
    )


def _serialise_timeline(t: Timeline) -> TimelineResponse:
    return TimelineResponse(
        subject_id=t.subject_id,
        subject_type=t.subject_type,
        subject_display_name=t.subject_display_name,
        period_start=t.period_start.isoformat(),
        period_end=t.period_end.isoformat(),
        event_count=t.event_count,
        access_gained_count=t.access_gained_count,
        access_lost_count=t.access_lost_count,
        access_modified_count=t.access_modified_count,
        events=[_serialise_event(e) for e in t.events],
    )


def _serialise_change_summary(s: ChangeSummary) -> ChangeSummaryResponse:
    return ChangeSummaryResponse(
        user_id=s.user_id,
        period_days=s.period_days,
        roles_added=s.roles_added,
        roles_removed=s.roles_removed,
        roles_modified=s.roles_modified,
        org_level_changes=s.org_level_changes,
        account_status_changes=s.account_status_changes,
        net_access_change=s.net_access_change,
        highest_impact_event=s.highest_impact_event,
        change_count=s.change_count,
        last_change_timestamp=s.last_change_timestamp.isoformat() if s.last_change_timestamp else None,
    )


def _serialise_loss_cause(a: LossCauseAnalysis) -> LossCauseResponse:
    return LossCauseResponse(
        user_id=a.user_id,
        transaction=a.transaction,
        reported_loss_date=a.reported_loss_date.isoformat(),
        cause_category=a.cause_category.value,
        confidence=a.confidence,
        root_cause_summary=a.root_cause_summary,
        causal_chain=[_serialise_event(e) for e in a.causal_chain],
        remediation_steps=a.remediation_steps,
        related_tickets=a.related_tickets,
        similar_users_affected=a.similar_users_affected,
    )


# =============================================================================
# Endpoints
# =============================================================================


@router.get(
    "/user/{user_id}",
    response_model=TimelineResponse,
    summary="User access timeline",
    description=(
        "Returns the complete ordered access timeline for the specified user "
        "covering the requested number of days.  Events include role assignments, "
        "removals, transport imports, org-level changes, and account locks."
    ),
)
def get_user_timeline(
    user_id: str,
    days: int = Query(90, ge=1, le=730, description="Number of days of history to return."),
    impact_filter: Optional[str] = Query(
        None,
        description="Filter events by access impact: access_gained, access_lost, access_modified, no_access_change.",
    ),
) -> TimelineResponse:
    """
    Retrieve the access event timeline for a user.

    Use ``days`` to control the look-back window.  Use ``impact_filter`` to
    isolate access-gaining or access-losing events for targeted analysis.

    Returns an empty timeline (not 404) if the user has no recorded events.
    """
    timeline = _tracker.get_user_timeline(user_id, days=days)

    if impact_filter:
        valid_impacts = {i.value for i in ChangeImpact}
        if impact_filter not in valid_impacts:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid impact_filter '{impact_filter}'.  Valid values: {sorted(valid_impacts)}.",
            )
        timeline.events = [e for e in timeline.events if e.impact.value == impact_filter]
        timeline.event_count = len(timeline.events)
        timeline.access_gained_count = sum(1 for e in timeline.events if e.impact == ChangeImpact.ACCESS_GAINED)
        timeline.access_lost_count = sum(1 for e in timeline.events if e.impact == ChangeImpact.ACCESS_LOST)
        timeline.access_modified_count = sum(1 for e in timeline.events if e.impact == ChangeImpact.ACCESS_MODIFIED)

    return _serialise_timeline(timeline)


@router.get(
    "/role/{role_id}",
    response_model=TimelineResponse,
    summary="Role change timeline",
    description=(
        "Returns the change history for the specified role, covering transport "
        "imports, auth object modifications, org-level changes, and profile "
        "regenerations across the requested period."
    ),
)
def get_role_timeline(
    role_id: str,
    days: int = Query(90, ge=1, le=730, description="Number of days of history to return."),
) -> TimelineResponse:
    """
    Retrieve the change timeline for a role definition.

    Useful for understanding what transports or manual changes have affected
    a role and when, particularly before or after an audit finding.
    """
    timeline = _tracker.get_role_timeline(role_id, days=days)
    return _serialise_timeline(timeline)


@router.get(
    "/user/{user_id}/changes",
    response_model=ChangeSummaryResponse,
    summary="Recent access change summary for a user",
    description=(
        "Returns a digest of recent access changes for the specified user: "
        "roles added/removed, org-level changes, account status events, and "
        "the net direction of change (expanded, reduced, mixed, unchanged)."
    ),
)
def get_user_change_summary(
    user_id: str,
    days: int = Query(30, ge=1, le=365, description="Look-back window in days."),
) -> ChangeSummaryResponse:
    """
    Return a structured summary of recent access changes for a user.

    The ``net_access_change`` field gives a quick indication of whether the
    user's overall access has expanded, reduced, or stayed the same.
    """
    summary = _tracker.get_change_summary(user_id, days=days)
    return _serialise_change_summary(summary)


@router.post(
    "/investigate",
    response_model=LossCauseResponse,
    summary="Investigate access loss cause",
    description=(
        "Performs a forensic investigation into why a user lost access to a "
        "specific transaction.  Returns a root cause analysis with a causal "
        "event chain and step-by-step remediation instructions."
    ),
)
def investigate_access_loss(body: InvestigateRequest) -> LossCauseResponse:
    """
    Investigate why a user can no longer access a transaction.

    The engine traces timeline events backwards from the reported loss date to
    identify the proximate cause (role removal, transport overwrite, account
    lock, org-level restriction, certification revocation, or profile issue).

    The ``confidence`` field (0.0-1.0) indicates how certain the engine is
    that the identified event is the true cause.  A confidence below 0.5
    means manual investigation is strongly recommended.
    """
    if not body.user_id.strip():
        raise HTTPException(status_code=400, detail="user_id must not be empty.")
    if not body.transaction.strip():
        raise HTTPException(status_code=400, detail="transaction must not be empty.")

    analysis = _tracker.find_access_loss_cause(
        user_id=body.user_id.strip(),
        transaction=body.transaction.strip(),
        reported_loss_date=body.reported_loss_date,
    )
    return _serialise_loss_cause(analysis)


@router.get(
    "/recent",
    response_model=List[TimelineEventResponse],
    summary="Recent access changes across all users",
    description=(
        "Returns the most recent access change events across all monitored users, "
        "ordered most-recent first.  Useful for a live activity feed on the dashboard."
    ),
)
def get_recent_changes(
    days: int = Query(7, ge=1, le=90, description="Number of days to look back."),
    limit: int = Query(50, ge=1, le=200, description="Maximum number of events to return."),
    event_type: Optional[str] = Query(
        None,
        description=(
            "Filter by event type, e.g. 'role_assigned', 'role_removed', "
            "'transport_imported', 'user_locked'."
        ),
    ),
) -> List[TimelineEventResponse]:
    """
    Return recent access change events across all users.

    Use ``event_type`` to filter for specific kinds of changes, e.g. to see
    only transport imports or only role assignments in the last 7 days.
    """
    if event_type:
        valid_types = {e.value for e in TimelineEventType}
        if event_type not in valid_types:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid event_type '{event_type}'.  Valid values: {sorted(valid_types)}.",
            )

    events = _tracker.get_recent_changes(days=days)

    if event_type:
        events = [e for e in events if e.event_type.value == event_type]

    return [_serialise_event(e) for e in events[:limit]]
