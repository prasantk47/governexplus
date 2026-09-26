"""
Access Timeline Tracker

Records and retrieves the complete history of access changes for users and
roles, covering: role assignments, removals, modifications, transport imports,
org value changes, account lock/unlock events, and password resets.

The tracker supports forensic investigation of access loss events, answering
questions such as: "Why did JOHN.SMITH lose access to transaction FB60 on
2024-08-15?"
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional

from db.database import db_manager
from db.models.intelligence import TimelineEvent as DBTimelineEvent

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class TimelineEventType(str, Enum):
    """Classification of an access timeline event."""

    ROLE_ASSIGNED = "role_assigned"
    ROLE_REMOVED = "role_removed"
    ROLE_MODIFIED = "role_modified"
    TRANSPORT_IMPORTED = "transport_imported"
    USER_COMPARISON = "user_comparison"
    ORG_VALUE_CHANGED = "org_value_changed"
    USER_LOCKED = "user_locked"
    USER_UNLOCKED = "user_unlocked"
    PASSWORD_CHANGED = "password_changed"
    PROFILE_REGENERATED = "profile_regenerated"
    ACCESS_GRANTED_INDIRECT = "access_granted_indirect"    # via composite role
    ACCESS_REVOKED_INDIRECT = "access_revoked_indirect"    # via composite role child removal
    MITIGATION_APPLIED = "mitigation_applied"
    CERTIFICATION_REVOKED = "certification_revoked"         # removed during cert campaign


class ChangeImpact(str, Enum):
    """Business impact classification for a timeline event."""

    ACCESS_GAINED = "access_gained"
    ACCESS_LOST = "access_lost"
    ACCESS_MODIFIED = "access_modified"
    NO_ACCESS_CHANGE = "no_access_change"


class LossCauseCategory(str, Enum):
    """Root cause category for an access loss event."""

    ROLE_REMOVED = "role_removed"
    TRANSPORT_OVERWROTE = "transport_overwrote"
    USER_LOCKED = "user_locked"
    ORG_LEVEL_RESTRICTED = "org_level_restricted"
    AUTH_VALUE_REMOVED = "auth_value_removed"
    CERTIFICATION_REVOKED = "certification_revoked"
    PROFILE_NOT_REGENERATED = "profile_not_regenerated"
    COMPOSITE_CHILD_REMOVED = "composite_child_removed"
    UNKNOWN = "unknown"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class TimelineEvent:
    """
    A single access-related event in a user or role timeline.

    All events carry the six W-fields (who, what, when, where, which, why)
    needed by auditors and access investigators.
    """

    event_id: str
    event_type: TimelineEventType
    timestamp: datetime
    actor: str                          # Who made the change (user / system / transport)
    subject: str                        # The user or role affected
    description: str                    # Human-readable summary
    system: str                         # SAP system: "PRD", "QA", "DEV"
    detail: Dict                        # Type-specific structured metadata
    impact: ChangeImpact
    affected_tcodes: List[str] = field(default_factory=list)
    transport_request: Optional[str] = None
    ticket_reference: Optional[str] = None
    is_reversible: bool = True
    reversal_event_id: Optional[str] = None


@dataclass
class Timeline:
    """
    The ordered sequence of access events for a user or role.

    ``subject_type`` is either ``"user"`` or ``"role"``.
    """

    subject_id: str
    subject_type: str
    subject_display_name: str
    period_start: datetime
    period_end: datetime
    events: List[TimelineEvent]
    event_count: int = 0
    access_gained_count: int = 0
    access_lost_count: int = 0
    access_modified_count: int = 0

    def __post_init__(self) -> None:
        self.event_count = len(self.events)
        self.access_gained_count = sum(1 for e in self.events if e.impact == ChangeImpact.ACCESS_GAINED)
        self.access_lost_count = sum(1 for e in self.events if e.impact == ChangeImpact.ACCESS_LOST)
        self.access_modified_count = sum(1 for e in self.events if e.impact == ChangeImpact.ACCESS_MODIFIED)


@dataclass
class ChangeSummary:
    """Recent change digest for a specific user."""

    user_id: str
    period_days: int
    roles_added: List[str]
    roles_removed: List[str]
    roles_modified: List[str]
    org_level_changes: List[Dict]
    account_status_changes: List[Dict]
    net_access_change: str          # "expanded", "reduced", "unchanged", "mixed"
    highest_impact_event: Optional[str]
    change_count: int
    last_change_timestamp: Optional[datetime]


@dataclass
class LossCauseAnalysis:
    """
    Forensic analysis of why a user lost access to a specific transaction.

    The ``causal_chain`` lists events in reverse-chronological order that
    led to the access loss, with the most proximate cause first.
    """

    user_id: str
    transaction: str
    reported_loss_date: datetime
    cause_category: LossCauseCategory
    confidence: float               # 0.0-1.0
    root_cause_summary: str
    causal_chain: List[TimelineEvent]
    remediation_steps: List[str]
    related_tickets: List[str]
    similar_users_affected: List[str]


# ---------------------------------------------------------------------------
# DB seed helpers
# ---------------------------------------------------------------------------

def _make_db_events(now: datetime) -> List[DBTimelineEvent]:
    """Build the full list of default TimelineEvent DB rows."""

    def _e(
        eid: str, etype: str, days_ago: float, performed_by: str,
        user_ext_id: str, username: str, description: str, system: str,
        detail: Dict, impact: str, tcodes: Optional[List[str]] = None,
        transport: Optional[str] = None, ticket: Optional[str] = None,
    ) -> DBTimelineEvent:
        detail_copy = dict(detail)
        if tcodes:
            detail_copy["_affected_tcodes"] = tcodes
        if transport:
            detail_copy["_transport_request"] = transport
        if ticket:
            detail_copy["_ticket_reference"] = ticket
        detail_copy["_impact"] = impact
        detail_copy["_subject_type"] = "user"
        return DBTimelineEvent(
            event_id=eid,
            event_type=etype,
            user_ext_id=user_ext_id,
            username=username,
            target_object=description[:255],
            detail=json.dumps(detail_copy),
            performed_by=performed_by,
            system=system,
            event_timestamp=now - timedelta(days=days_ago),
        )

    def _re(
        eid: str, etype: str, days_ago: float, performed_by: str,
        role_id: str, description: str, detail: Dict, impact: str,
        transport: Optional[str] = None, ticket: Optional[str] = None,
    ) -> DBTimelineEvent:
        detail_copy = dict(detail)
        if transport:
            detail_copy["_transport_request"] = transport
        if ticket:
            detail_copy["_ticket_reference"] = ticket
        detail_copy["_impact"] = impact
        detail_copy["_subject_type"] = "role"
        return DBTimelineEvent(
            event_id=eid,
            event_type=etype,
            user_ext_id=role_id,
            username=role_id,
            target_object=description[:255],
            detail=json.dumps(detail_copy),
            performed_by=performed_by,
            system="PRD",
            event_timestamp=now - timedelta(days=days_ago),
        )

    rows: List[DBTimelineEvent] = []

    # JOHN.SMITH user events
    rows += [
        _e("EVT-JS-001", "role_assigned", 85, "ADMIN01", "JOHN.SMITH", "JOHN.SMITH",
           "Assigned role Z_FI_AP_CLERK on joining", "PRD",
           {"role": "Z_FI_AP_CLERK", "reason": "New hire onboarding", "approval": "MANAGER01"},
           "access_gained", ["FB60", "FB65", "FBL1N", "F110"], ticket="INC0001000"),
        _e("EVT-JS-002", "transport_imported", 60, "DEVK900090", "JOHN.SMITH", "JOHN.SMITH",
           "Transport DEVK900090 imported — Z_FI_AP_CLERK updated (ACTVT 06 removed)", "PRD",
           {"transport": "DEVK900090", "role_affected": "Z_FI_AP_CLERK",
            "field_changed": "ACTVT", "old_value": "01,02,03,06", "new_value": "01,02,03"},
           "access_modified", ["FB60", "FB65"], transport="DEVK900090"),
        _e("EVT-JS-003", "password_changed", 45, "JOHN.SMITH", "JOHN.SMITH", "JOHN.SMITH",
           "User self-service password reset", "PRD",
           {"method": "self_service", "system": "PRD"}, "no_access_change"),
        _e("EVT-JS-004", "role_assigned", 30, "ADMIN01", "JOHN.SMITH", "JOHN.SMITH",
           "Assigned additional role Z_FI_REPORT_VIEWER", "PRD",
           {"role": "Z_FI_REPORT_VIEWER", "reason": "Project requirement", "approval": "MANAGER01"},
           "access_gained", ["S_ALR_87012082"], ticket="INC0001200"),
        _e("EVT-JS-005", "org_value_changed", 20, "BASIS01", "JOHN.SMITH", "JOHN.SMITH",
           "Org-level BUKRS extended to include company code 3000", "PRD",
           {"field": "BUKRS", "old_values": ["1000", "2000"], "new_values": ["1000", "2000", "3000"],
            "transport": "DEVK900130"},
           "access_gained", transport="DEVK900130"),
        _e("EVT-JS-006", "certification_revoked", 15, "MANAGER01", "JOHN.SMITH", "JOHN.SMITH",
           "Role Z_FI_REPORT_VIEWER revoked during Q3 access certification", "PRD",
           {"campaign": "CAMP-Q3-2024", "reason": "No longer required per manager review"},
           "access_lost", ["S_ALR_87012082"], ticket="CERT-Q3-2024"),
        _e("EVT-JS-007", "user_locked", 5, "SEC_SYSTEM", "JOHN.SMITH", "JOHN.SMITH",
           "Account locked after 5 consecutive failed login attempts", "PRD",
           {"failed_attempts": 5, "source_ip": "192.168.1.44", "auto_lock": True},
           "access_lost"),
        _e("EVT-JS-008", "user_unlocked", 4, "ADMIN01", "JOHN.SMITH", "JOHN.SMITH",
           "Account unlocked after identity verification", "PRD",
           {"unlocked_by": "ADMIN01", "ticket": "INC0001380"},
           "access_gained", ticket="INC0001380"),
    ]

    # ALICE.WANG user events
    rows += [
        _e("EVT-AW-001", "role_assigned", 80, "ADMIN02", "ALICE.WANG", "ALICE.WANG",
           "Assigned Z_MM_PURCHASE_ORDER at project start", "PRD",
           {"role": "Z_MM_PURCHASE_ORDER", "approval": "MANAGER02"},
           "access_gained", ["ME21N", "ME22N", "ME23N"], ticket="INC0001050"),
        _e("EVT-AW-002", "role_assigned", 75, "ADMIN02", "ALICE.WANG", "ALICE.WANG",
           "Assigned Z_MM_GOODS_RECEIPT for warehouse support", "PRD",
           {"role": "Z_MM_GOODS_RECEIPT", "approval": "MANAGER02"},
           "access_gained", ["MIGO"], ticket="INC0001055"),
        _e("EVT-AW-003", "org_value_changed", 50, "BASIS01", "ALICE.WANG", "ALICE.WANG",
           "Org-level WERKS restricted from [1000, 2000] to [1000] in Z_MM_PURCHASE_ORDER", "PRD",
           {"role": "Z_MM_PURCHASE_ORDER", "field": "WERKS",
            "old_values": ["1000", "2000"], "new_values": ["1000"], "transport": "DEVK900101"},
           "access_modified", transport="DEVK900101"),
        _e("EVT-AW-004", "role_removed", 15, "ADMIN02", "ALICE.WANG", "ALICE.WANG",
           "Role Z_BASIS_TRANSPORT removed — rejected during Q3 certification", "PRD",
           {"role": "Z_BASIS_TRANSPORT", "campaign": "CAMP-Q3-2024", "reason": "Scope creep"},
           "access_lost", ["SE09", "SE10", "STMS"], ticket="CERT-Q3-2024"),
        _e("EVT-AW-005", "mitigation_applied", 10, "RISK_MGR01", "ALICE.WANG", "ALICE.WANG",
           "Mitigation MIT-2024-042 applied for SoD rule MM-003", "PRD",
           {"mitigation_id": "MIT-2024-042", "rule": "MM-003", "control": "Bi-weekly log review"},
           "no_access_change", ticket="SOD-2024-042"),
    ]

    # BOB.MARTIN user events
    rows += [
        _e("EVT-BM-001", "role_assigned", 90, "ADMIN01", "BOB.MARTIN", "BOB.MARTIN",
           "Assigned Z_FI_AP_CLERK and Z_FI_AP_APPROVE on hire", "PRD",
           {"roles": ["Z_FI_AP_CLERK", "Z_FI_AP_APPROVE"], "approval": "MANAGER01"},
           "access_gained", ["FB60", "FB65", "MIR7", "MIRO"], ticket="INC0000800"),
        _e("EVT-BM-002", "role_removed", 82, "ADMIN01", "BOB.MARTIN", "BOB.MARTIN",
           "Role Z_FI_AP_APPROVE removed — SoD violation FI-001 detected", "PRD",
           {"role": "Z_FI_AP_APPROVE", "sod_rule": "FI-001", "ticket": "INC0000820"},
           "access_lost", ["MIRO"], ticket="INC0000820"),
        _e("EVT-BM-003", "transport_imported", 40, "DEVK900095", "BOB.MARTIN", "BOB.MARTIN",
           "Transport DEVK900095 updated Z_FI_AP_CLERK — menu node FB65 removed", "PRD",
           {"transport": "DEVK900095", "menu_removed": ["FB65"]},
           "access_modified", transport="DEVK900095"),
        _e("EVT-BM-004", "user_comparison", 20, "ADMIN03", "BOB.MARTIN", "BOB.MARTIN",
           "User comparison: BOB.MARTIN vs JANE.TEMPLATE — 3 role differences found", "PRD",
           {"reference_user": "JANE.TEMPLATE", "extra_roles": ["Z_CO_READ"],
            "missing_roles": ["Z_FI_REPORT_VIEWER", "Z_SD_READ"]},
           "no_access_change"),
        _e("EVT-BM-005", "role_assigned", 5, "ADMIN01", "BOB.MARTIN", "BOB.MARTIN",
           "Assigned Z_FI_REPORT_VIEWER to align with role template", "PRD",
           {"role": "Z_FI_REPORT_VIEWER", "reason": "Template alignment", "approval": "MANAGER01"},
           "access_gained", ["S_ALR_87012082", "S_ALR_87012083"], ticket="INC0001400"),
    ]

    # MIKE.CHEN user events
    rows += [
        _e("EVT-MC-001", "role_assigned", 88, "HR_SYSTEM", "MIKE.CHEN", "MIKE.CHEN",
           "Auto-provisioned onboarding roles via Workday integration", "PRD",
           {"roles": ["Z_HR_TIME_ENTRY", "Z_CO_READ"], "source": "Workday",
            "hire_date": (now - timedelta(days=88)).strftime("%Y-%m-%d")},
           "access_gained", ["CAT2", "KSB1"], ticket="INC0000900"),
        _e("EVT-MC-002", "role_assigned", 60, "ADMIN02", "MIKE.CHEN", "MIKE.CHEN",
           "Assigned Z_HR_PAYROLL_PROC for expanded responsibilities", "PRD",
           {"role": "Z_HR_PAYROLL_PROC", "approval": "MANAGER03"},
           "access_gained", ["PC00_M01_CALC", "PC00_M01_CDOC"], ticket="INC0001100"),
        _e("EVT-MC-003", "org_value_changed", 45, "BASIS02", "MIKE.CHEN", "MIKE.CHEN",
           "Org-level MOLGA expanded to include country group 08 (Switzerland)", "PRD",
           {"role": "Z_HR_PAYROLL_PROC", "field": "MOLGA",
            "old_values": ["01"], "new_values": ["01", "08"], "transport": "DEVK900110"},
           "access_gained", transport="DEVK900110"),
        _e("EVT-MC-004", "transport_imported", 10, "DEVK900140", "MIKE.CHEN", "MIKE.CHEN",
           "Transport DEVK900140 reimported Z_HR_PAYROLL_PROC without MOLGA 08", "PRD",
           {"transport": "DEVK900140", "regression": True,
            "field_regressed": "MOLGA", "value_lost": "08"},
           "access_lost", transport="DEVK900140"),
    ]

    # PETER.LEAVER user events
    rows += [
        _e("EVT-PL-001", "role_assigned", 365, "ADMIN01", "PETER.LEAVER", "PETER.LEAVER",
           "Assigned standard finance roles on hire", "PRD",
           {"roles": ["Z_FI_AP_CLERK", "Z_FI_GL_POSTING", "Z_CO_COST_CENTER"], "approval": "MANAGER01"},
           "access_gained", ["FB60", "FB50", "KSB1"], ticket="INC0000100"),
        _e("EVT-PL-002", "certification_revoked", 90, "MANAGER02", "PETER.LEAVER", "PETER.LEAVER",
           "Z_FI_GL_POSTING and Z_CO_COST_CENTER removed — cert campaign review", "PRD",
           {"roles_removed": ["Z_FI_GL_POSTING", "Z_CO_COST_CENTER"], "campaign": "CAMP-Q2-2024"},
           "access_lost", ["FB50", "KSB1"], ticket="CERT-Q2-2024"),
        _e("EVT-PL-003", "user_locked", 30, "HR_SYSTEM", "PETER.LEAVER", "PETER.LEAVER",
           "Account locked — termination event received from Workday", "PRD",
           {"reason": "Employment terminated", "source": "Workday",
            "effective_date": (now - timedelta(days=30)).strftime("%Y-%m-%d")},
           "access_lost"),
        _e("EVT-PL-004", "role_removed", 30, "HR_SYSTEM", "PETER.LEAVER", "PETER.LEAVER",
           "All 12 roles revoked on termination", "PRD",
           {"roles_removed": 12, "source": "Workday", "systems": ["PRD", "QA"]},
           "access_lost"),
    ]

    # DAN.SUSPECT user events
    rows += [
        _e("EVT-DS-001", "role_assigned", 70, "ADMIN03", "DAN.SUSPECT", "DAN.SUSPECT",
           "Assigned Z_FI_GL_POSTING", "PRD",
           {"role": "Z_FI_GL_POSTING", "approval": "MANAGER04"},
           "access_gained", ["FB50", "FB03"], ticket="INC0001020"),
        _e("EVT-DS-002", "role_assigned", 65, "ADMIN03", "DAN.SUSPECT", "DAN.SUSPECT",
           "Assigned Z_FI_GL_APPROVE — creates SoD conflict FI-004", "PRD",
           {"role": "Z_FI_GL_APPROVE", "sod_detected_at_assign": True, "rule": "FI-004"},
           "access_gained", ["F-02", "FB05"], ticket="INC0001025"),
        _e("EVT-DS-003", "user_locked", 25, "SEC_SYSTEM", "DAN.SUSPECT", "DAN.SUSPECT",
           "Account locked following anomalous login pattern alert", "PRD",
           {"reason": "Anomalous login pattern", "siem_alert": "SIEM-2024-0045", "source_ip": "203.0.113.99"},
           "access_lost"),
        _e("EVT-DS-004", "profile_regenerated", 25, "ADMIN01", "DAN.SUSPECT", "DAN.SUSPECT",
           "Profile regenerated for Z_FI_GL_POSTING after audit finding", "PRD",
           {"role": "Z_FI_GL_POSTING", "reason": "Profile out of sync with role definition"},
           "no_access_change"),
    ]

    # CAROL.NEW user events
    rows += [
        _e("EVT-CN-001", "role_assigned", 50, "HR_SYSTEM", "CAROL.NEW", "CAROL.NEW",
           "Auto-provisioned standard roles on hire via Workday", "PRD",
           {"roles": ["Z_FI_AP_CLERK", "Z_SD_READ", "Z_CO_READ"], "source": "Workday"},
           "access_gained", ["FB60", "VA03", "KSB1"], ticket="INC0001150"),
        _e("EVT-CN-002", "role_assigned", 30, "ADMIN01", "CAROL.NEW", "CAROL.NEW",
           "Assigned Z_MM_VENDOR_MASTER — creates SoD risk with AP_CLERK", "PRD",
           {"role": "Z_MM_VENDOR_MASTER", "sod_warning": "FI-007 detected", "approval": "MANAGER01"},
           "access_gained", ["XK01", "XK02"], ticket="INC0001200"),
        _e("EVT-CN-003", "role_removed", 10, "ADMIN01", "CAROL.NEW", "CAROL.NEW",
           "Role Z_MM_VENDOR_MASTER removed — SoD violation FI-007 resolved", "PRD",
           {"role": "Z_MM_VENDOR_MASTER", "sod_rule": "FI-007", "reason": "Access not justified"},
           "access_lost", ["XK01", "XK02"], ticket="SOD-2024-039"),
    ]

    # Role events — Z_FI_AP_CLERK
    rows += [
        _re("EVT-R-AP-001", "role_assigned", 180, "BASIS01", "Z_FI_AP_CLERK",
            "Role Z_FI_AP_CLERK created and transported to PRD",
            {"transport": "DEVK900010", "auth_objects": 3, "users_assigned": 0},
            "no_access_change", transport="DEVK900010"),
        _re("EVT-R-AP-002", "transport_imported", 60, "DEVK900090", "Z_FI_AP_CLERK",
            "Transport DEVK900090 — removed ACTVT 06 (delete) from F_BKPF_BUK",
            {"transport": "DEVK900090", "object": "F_BKPF_BUK", "field": "ACTVT",
             "old": "01,02,03,06", "new": "01,02,03", "reason": "Audit finding"},
            "access_modified", transport="DEVK900090"),
        _re("EVT-R-AP-003", "org_value_changed", 20, "BASIS01", "Z_FI_AP_CLERK",
            "Org-level BUKRS extended to include company code 3000",
            {"field": "BUKRS", "old": ["1000", "2000"], "new": ["1000", "2000", "3000"],
             "transport": "DEVK900130"},
            "access_gained", transport="DEVK900130"),
        _re("EVT-R-AP-004", "profile_regenerated", 10, "BASIS01", "Z_FI_AP_CLERK",
            "Profile T-AG100001 regenerated after org-level change",
            {"profile": "T-AG100001", "users_affected": 14},
            "no_access_change"),
    ]

    # Role events — Z_FI_GL_POSTING
    rows += [
        _re("EVT-R-GL-001", "role_assigned", 200, "BASIS01", "Z_FI_GL_POSTING",
            "Role Z_FI_GL_POSTING created",
            {"transport": "DEVK900005", "auth_objects": 2},
            "no_access_change", transport="DEVK900005"),
        _re("EVT-R-GL-002", "role_modified", 30, "BASIS01", "Z_FI_GL_POSTING",
            "Activity 06 added to F_BKPF_BUK in DEV — pending transport to PROD",
            {"environment": "DEV", "field": "ACTVT", "added": "06", "transport": "DEVK900124"},
            "access_modified", transport="DEVK900124"),
    ]

    # Role events — Z_MM_PURCHASE_ORDER
    rows += [
        _re("EVT-R-MM-001", "role_assigned", 120, "BASIS02", "Z_MM_PURCHASE_ORDER",
            "Role Z_MM_PURCHASE_ORDER created in DEV and QA — transport to PROD pending",
            {"transport": "DEVK900060", "systems_reached": ["DEV", "QA"]},
            "no_access_change", transport="DEVK900060"),
    ]

    # Role events — Z_BC_USER_ADMIN
    rows += [
        _re("EVT-R-UA-001", "role_assigned", 5, "BASIS_EMERGENCY", "Z_BC_USER_ADMIN",
            "Emergency role Z_BC_USER_ADMIN created directly in PROD (no transport)",
            {"reason": "System outage", "auth_ref": "EMRG-2024-0047",
             "emergency_change": True, "approved_by": "CIO"},
            "access_gained", ticket="EMRG-2024-0047"),
    ]

    return rows


def _ensure_loaded(tenant_id: str = "tenant_default") -> None:
    """Seed the timeline_events table with default data if it is empty."""
    with db_manager.session_scope() as session:
        count = session.query(DBTimelineEvent).filter_by(tenant_id=tenant_id).count()
        if count == 0:
            now = datetime.utcnow()
            defaults = _make_db_events(now)
            for row in defaults:
                row.tenant_id = tenant_id
            session.add_all(defaults)
            logger.info("timeline_tracker: seeded %d default events", len(defaults))


# ---------------------------------------------------------------------------
# Conversion helper: DB row → TimelineEvent dataclass
# ---------------------------------------------------------------------------

def _row_to_event(row: DBTimelineEvent) -> TimelineEvent:
    """Convert a DBTimelineEvent ORM row to a TimelineEvent dataclass."""
    try:
        detail_dict: Dict = json.loads(row.detail) if row.detail else {}
    except (json.JSONDecodeError, TypeError):
        detail_dict = {}

    impact_str = detail_dict.pop("_impact", "no_access_change")
    try:
        impact = ChangeImpact(impact_str)
    except ValueError:
        impact = ChangeImpact.NO_ACCESS_CHANGE

    affected_tcodes: List[str] = detail_dict.pop("_affected_tcodes", [])
    transport_request: Optional[str] = detail_dict.pop("_transport_request", None)
    ticket_reference: Optional[str] = detail_dict.pop("_ticket_reference", None)
    detail_dict.pop("_subject_type", None)

    try:
        event_type = TimelineEventType(row.event_type)
    except ValueError:
        event_type = TimelineEventType.ROLE_MODIFIED

    return TimelineEvent(
        event_id=row.event_id,
        event_type=event_type,
        timestamp=row.event_timestamp,
        actor=row.performed_by or "SYSTEM",
        subject=row.user_ext_id,
        description=row.target_object or "",
        system=row.system or "PRD",
        detail=detail_dict,
        impact=impact,
        affected_tcodes=affected_tcodes,
        transport_request=transport_request,
        ticket_reference=ticket_reference,
    )


# ---------------------------------------------------------------------------
# DB query helpers (replace in-memory _build_* functions)
# ---------------------------------------------------------------------------

def _build_user_events(user_id: str, now: datetime) -> List[TimelineEvent]:
    """Query DB for timeline events for the given user (subject_type=user)."""
    _ensure_loaded()
    with db_manager.session_scope() as session:
        rows = (
            session.query(DBTimelineEvent)
            .filter(
                DBTimelineEvent.user_ext_id == user_id.upper(),
                DBTimelineEvent.detail.like('%"_subject_type": "user"%'),
            )
            .order_by(DBTimelineEvent.event_timestamp)
            .all()
        )
        return [_row_to_event(r) for r in rows]


def _build_role_events(role_id: str, now: datetime) -> List[TimelineEvent]:
    """Query DB for timeline events for the given role (subject_type=role)."""
    _ensure_loaded()
    with db_manager.session_scope() as session:
        rows = (
            session.query(DBTimelineEvent)
            .filter(
                DBTimelineEvent.user_ext_id == role_id.upper(),
                DBTimelineEvent.detail.like('%"_subject_type": "role"%'),
            )
            .order_by(DBTimelineEvent.event_timestamp)
            .all()
        )
        return [_row_to_event(r) for r in rows]


def _all_recent_events(days: int, now: datetime) -> List[TimelineEvent]:
    """Query DB for cross-user events within the last `days` days."""
    _ensure_loaded()
    cutoff = now - timedelta(days=days)
    with db_manager.session_scope() as session:
        rows = (
            session.query(DBTimelineEvent)
            .filter(
                DBTimelineEvent.event_timestamp >= cutoff,
                DBTimelineEvent.detail.like('%"_subject_type": "user"%'),
            )
            .order_by(DBTimelineEvent.event_timestamp.desc())
            .all()
        )
        return [_row_to_event(r) for r in rows]


# ---------------------------------------------------------------------------
# AccessTimelineTracker — public engine
# ---------------------------------------------------------------------------


class AccessTimelineTracker:
    """
    Tracks and investigates access changes for users and roles over time.

    Usage::

        tracker  = AccessTimelineTracker()
        timeline = tracker.get_user_timeline("JOHN.SMITH", days=90)
        summary  = tracker.get_change_summary("JOHN.SMITH")
        analysis = tracker.find_access_loss_cause("MIKE.CHEN", "PC00_M01_CALC")
    """

    def __init__(self) -> None:
        self._now: datetime = datetime.utcnow()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_user_timeline(self, user_id: str, days: int = 90) -> Timeline:
        """
        Return the complete access timeline for a user over the given period.

        Parameters
        ----------
        user_id:
            SAP user ID, e.g. ``"JOHN.SMITH"``.
        days:
            How many days back to include.

        Returns
        -------
        Timeline
            Ordered list of access events from oldest to newest.
        """
        cutoff = self._now - timedelta(days=days)
        all_events = _build_user_events(user_id, self._now)
        filtered = sorted(
            [e for e in all_events if e.timestamp >= cutoff],
            key=lambda e: e.timestamp,
        )

        display_name = user_id.replace(".", " ").title()
        return Timeline(
            subject_id=user_id.upper(),
            subject_type="user",
            subject_display_name=display_name,
            period_start=cutoff,
            period_end=self._now,
            events=filtered,
        )

    def get_role_timeline(self, role_id: str, days: int = 90) -> Timeline:
        """
        Return the change history for a role over the given period.

        Parameters
        ----------
        role_id:
            SAP role name, e.g. ``"Z_FI_AP_CLERK"``.
        days:
            How many days back to include.

        Returns
        -------
        Timeline
            Ordered list of role-related events from oldest to newest.
        """
        cutoff = self._now - timedelta(days=days)
        all_events = _build_role_events(role_id, self._now)
        filtered = sorted(
            [e for e in all_events if e.timestamp >= cutoff],
            key=lambda e: e.timestamp,
        )
        return Timeline(
            subject_id=role_id.upper(),
            subject_type="role",
            subject_display_name=role_id.upper(),
            period_start=cutoff,
            period_end=self._now,
            events=filtered,
        )

    def get_change_summary(self, user_id: str, days: int = 30) -> ChangeSummary:
        """
        Return a digest of recent access changes for a user.

        Parameters
        ----------
        user_id:
            SAP user ID.
        days:
            Look-back window in days (default 30).

        Returns
        -------
        ChangeSummary
            Roles added/removed, org changes, and net direction of change.
        """
        timeline = self.get_user_timeline(user_id, days=days)
        events = timeline.events

        roles_added: List[str] = []
        roles_removed: List[str] = []
        roles_modified: List[str] = []
        org_changes: List[Dict] = []
        status_changes: List[Dict] = []
        last_ts: Optional[datetime] = None

        for e in sorted(events, key=lambda x: x.timestamp):
            last_ts = e.timestamp
            if e.event_type == TimelineEventType.ROLE_ASSIGNED:
                r = e.detail.get("role") or e.detail.get("roles", "")
                if isinstance(r, list):
                    roles_added.extend(r)
                else:
                    roles_added.append(str(r))
            elif e.event_type in (TimelineEventType.ROLE_REMOVED, TimelineEventType.CERTIFICATION_REVOKED):
                r = e.detail.get("role") or e.detail.get("roles_removed", "")
                if isinstance(r, list):
                    roles_removed.extend(r)
                else:
                    roles_removed.append(str(r))
            elif e.event_type == TimelineEventType.TRANSPORT_IMPORTED:
                role = e.detail.get("role_affected")
                if role:
                    roles_modified.append(role)
            elif e.event_type == TimelineEventType.ORG_VALUE_CHANGED:
                org_changes.append({
                    "field": e.detail.get("field"),
                    "old": e.detail.get("old_values"),
                    "new": e.detail.get("new_values"),
                    "timestamp": e.timestamp.isoformat(),
                })
            elif e.event_type in (TimelineEventType.USER_LOCKED, TimelineEventType.USER_UNLOCKED):
                status_changes.append({
                    "event": e.event_type.value,
                    "timestamp": e.timestamp.isoformat(),
                    "reason": e.detail.get("reason", ""),
                })

        if roles_added and not roles_removed:
            net = "expanded"
        elif roles_removed and not roles_added:
            net = "reduced"
        elif roles_added and roles_removed:
            net = "mixed"
        else:
            net = "unchanged"

        # Highest impact: prefer critical-level events
        critical = [e for e in events if e.impact == ChangeImpact.ACCESS_LOST]
        highest = critical[0].description if critical else (events[-1].description if events else None)

        return ChangeSummary(
            user_id=user_id.upper(),
            period_days=days,
            roles_added=roles_added,
            roles_removed=roles_removed,
            roles_modified=roles_modified,
            org_level_changes=org_changes,
            account_status_changes=status_changes,
            net_access_change=net,
            highest_impact_event=highest,
            change_count=len(events),
            last_change_timestamp=last_ts,
        )

    def find_access_loss_cause(
        self,
        user_id: str,
        transaction: str,
        reported_loss_date: Optional[datetime] = None,
    ) -> LossCauseAnalysis:
        """
        Investigate why a user lost access to a specific transaction.

        Parameters
        ----------
        user_id:
            The affected user.
        transaction:
            The transaction code the user can no longer execute, e.g. ``"FB60"``.
        reported_loss_date:
            When the user noticed the access loss.  Defaults to now.

        Returns
        -------
        LossCauseAnalysis
            Root cause with causal chain and remediation steps.
        """
        loss_date = reported_loss_date or self._now
        all_events = _build_user_events(user_id, self._now)
        tcode_upper = transaction.upper()

        # Find events that mention the tcode and represent a loss
        loss_events = [
            e for e in all_events
            if (
                tcode_upper in [t.upper() for t in e.affected_tcodes]
                and e.impact in (ChangeImpact.ACCESS_LOST, ChangeImpact.ACCESS_MODIFIED)
                and e.timestamp <= loss_date
            )
        ]

        # Sort most recent first
        loss_events.sort(key=lambda e: e.timestamp, reverse=True)

        if not loss_events:
            # Generic fallback — look for any access-loss event
            loss_events = [
                e for e in all_events
                if e.impact == ChangeImpact.ACCESS_LOST and e.timestamp <= loss_date
            ]
            loss_events.sort(key=lambda e: e.timestamp, reverse=True)

        if not loss_events:
            return LossCauseAnalysis(
                user_id=user_id.upper(),
                transaction=tcode_upper,
                reported_loss_date=loss_date,
                cause_category=LossCauseCategory.UNKNOWN,
                confidence=0.1,
                root_cause_summary=(
                    f"No access-loss events found for {user_id} related to {tcode_upper}. "
                    "Manual investigation required."
                ),
                causal_chain=[],
                remediation_steps=[
                    "Check current role assignments via SU01/SU56.",
                    "Review transport logs for recent imports to PRD.",
                    "Verify user account status (locked/expired).",
                    "Compare against reference user with same job function.",
                ],
                related_tickets=[],
                similar_users_affected=[],
            )

        proximate = loss_events[0]

        # Determine cause category
        cause_map = {
            TimelineEventType.ROLE_REMOVED: LossCauseCategory.ROLE_REMOVED,
            TimelineEventType.CERTIFICATION_REVOKED: LossCauseCategory.CERTIFICATION_REVOKED,
            TimelineEventType.TRANSPORT_IMPORTED: LossCauseCategory.TRANSPORT_OVERWROTE,
            TimelineEventType.USER_LOCKED: LossCauseCategory.USER_LOCKED,
            TimelineEventType.ORG_VALUE_CHANGED: LossCauseCategory.ORG_LEVEL_RESTRICTED,
            TimelineEventType.PROFILE_REGENERATED: LossCauseCategory.PROFILE_NOT_REGENERATED,
            TimelineEventType.ACCESS_REVOKED_INDIRECT: LossCauseCategory.COMPOSITE_CHILD_REMOVED,
        }
        cause_cat = cause_map.get(proximate.event_type, LossCauseCategory.UNKNOWN)
        confidence = 0.92 if tcode_upper in [t.upper() for t in proximate.affected_tcodes] else 0.65

        # Build remediation
        remediation: List[str] = {
            LossCauseCategory.ROLE_REMOVED: [
                f"Raise an access request to re-assign the role that provided {tcode_upper}.",
                "Obtain manager approval and SoD pre-check before provisioning.",
                f"Verify the removal was intentional by reviewing ticket {proximate.ticket_reference or 'N/A'}.",
            ],
            LossCauseCategory.TRANSPORT_OVERWROTE: [
                f"Review transport {proximate.transport_request} to confirm whether the change was intended.",
                f"If unintentional, create a correction transport restoring {tcode_upper} access.",
                "Raise a change request for the correction transport.",
            ],
            LossCauseCategory.USER_LOCKED: [
                f"Contact the helpdesk to unlock account {user_id}.",
                "Verify identity before unlock via INC ticket.",
                "Investigate the reason for the lock to prevent recurrence.",
            ],
            LossCauseCategory.CERTIFICATION_REVOKED: [
                f"Review the certification decision in campaign {proximate.detail.get('campaign', 'N/A')}.",
                "If the access is still required, raise a new access request with updated business justification.",
                "Obtain manager re-approval.",
            ],
            LossCauseCategory.ORG_LEVEL_RESTRICTED: [
                f"Check whether org-level restriction in transport {proximate.transport_request} was intentional.",
                "If not, create a correction transport re-adding the required org-level values.",
            ],
        }.get(cause_cat, [
            f"Investigate manually via SU53 and SUIM for {user_id}.",
            f"Check authorization trace for {tcode_upper} in ST01.",
        ])

        tickets = [e.ticket_reference for e in loss_events if e.ticket_reference]
        summary = (
            f"Access to {tcode_upper} was lost by {user_id} on "
            f"{proximate.timestamp.strftime('%Y-%m-%d %H:%M')} UTC.  "
            f"Root cause: {cause_cat.value.replace('_', ' ')}.  "
            f"Event: {proximate.description}"
        )

        return LossCauseAnalysis(
            user_id=user_id.upper(),
            transaction=tcode_upper,
            reported_loss_date=loss_date,
            cause_category=cause_cat,
            confidence=confidence,
            root_cause_summary=summary,
            causal_chain=loss_events[:5],
            remediation_steps=remediation,
            related_tickets=tickets,
            similar_users_affected=self._find_similar_users_affected(tcode_upper, proximate),
        )

    def get_recent_changes(self, days: int = 7) -> List[TimelineEvent]:
        """
        Return recent access changes across all users.

        Parameters
        ----------
        days:
            Look-back window.

        Returns
        -------
        List[TimelineEvent]
            Events sorted most-recent first.
        """
        return _all_recent_events(days, self._now)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _find_similar_users_affected(
        self, tcode: str, proximate_event: TimelineEvent
    ) -> List[str]:
        """
        Heuristic: find other users affected by the same transport or role change.
        """
        transport = proximate_event.transport_request
        if not transport:
            return []
        # In a real implementation this would query the DB.  Return plausible mock users.
        transport_impact: Dict[str, List[str]] = {
            "DEVK900090": ["JANE.DOE", "CAROL.NEW"],
            "DEVK900095": ["CAROL.NEW"],
            "DEVK900140": ["SARAH.NEW"],
        }
        return transport_impact.get(transport, [])
