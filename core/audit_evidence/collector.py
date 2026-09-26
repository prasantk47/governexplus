"""
Audit Evidence Center — Evidence Collector

Collects structured audit evidence across all GRC modules for a specified
date range and set of evidence categories.  Evidence is assembled into
versioned EvidencePackages suitable for export to auditors (SOX, ISO 27001,
GDPR, etc.).

Each evidence item records: timestamp, actor, action, target, detail, and
evidence_type, matching the fields required by common audit frameworks.
"""

import hashlib
import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

from db.database import db_manager
from db.models.intelligence import AuditEvidenceItem as DBAuditEvidenceItem

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class EvidenceCategoryType(str, Enum):
    """GRC module categories from which evidence can be drawn."""

    USER_ACCESS = "user_access"
    ROLE_CHANGES = "role_changes"
    APPROVALS = "approvals"
    SOD_VIOLATIONS = "sod_violations"
    MITIGATIONS = "mitigations"
    FIREFIGHTER = "firefighter"
    CERTIFICATIONS = "certifications"
    PROVISIONING = "provisioning"


class EvidenceItemType(str, Enum):
    """Granular classification of an individual evidence item."""

    ACCESS_GRANTED = "access_granted"
    ACCESS_REVOKED = "access_revoked"
    ACCESS_REVIEWED = "access_reviewed"
    ROLE_CREATED = "role_created"
    ROLE_MODIFIED = "role_modified"
    ROLE_DELETED = "role_deleted"
    APPROVAL_SUBMITTED = "approval_submitted"
    APPROVAL_APPROVED = "approval_approved"
    APPROVAL_REJECTED = "approval_rejected"
    SOD_VIOLATION_DETECTED = "sod_violation_detected"
    SOD_VIOLATION_RESOLVED = "sod_violation_resolved"
    MITIGATION_CREATED = "mitigation_created"
    MITIGATION_REVIEWED = "mitigation_reviewed"
    MITIGATION_EXPIRED = "mitigation_expired"
    FIREFIGHTER_SESSION_OPENED = "firefighter_session_opened"
    FIREFIGHTER_SESSION_CLOSED = "firefighter_session_closed"
    FIREFIGHTER_ACTIVITY_LOGGED = "firefighter_activity_logged"
    CERTIFICATION_CAMPAIGN_STARTED = "certification_campaign_started"
    CERTIFICATION_DECISION_MADE = "certification_decision_made"
    CERTIFICATION_CAMPAIGN_COMPLETED = "certification_campaign_completed"
    PROVISIONING_REQUEST_RAISED = "provisioning_request_raised"
    PROVISIONING_COMPLETED = "provisioning_completed"
    PROVISIONING_FAILED = "provisioning_failed"


class PackageStatus(str, Enum):
    """Lifecycle status of an evidence package."""

    DRAFT = "draft"
    FINALIZED = "finalized"
    EXPORTED = "exported"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class EvidenceCategory:
    """Metadata describing an available evidence category."""

    category_id: EvidenceCategoryType
    display_name: str
    description: str
    regulatory_mapping: List[str]   # e.g. ["SOX 404", "ISO 27001 A.9.2"]
    item_count_available: int       # Approximate items available (mock)


@dataclass
class EvidenceItem:
    """
    A single, atomic piece of audit evidence.

    All fields are required for an item to be considered complete.  The
    ``detail`` dict allows category-specific metadata without breaking the
    common schema.
    """

    item_id: str
    timestamp: datetime
    actor: str              # Who performed the action (user ID or system name)
    action: str             # Human-readable action description
    target: str             # The object acted upon (user, role, session ID, etc.)
    detail: Dict[str, Any]  # Category-specific additional context
    evidence_type: EvidenceItemType
    category: EvidenceCategoryType
    risk_level: str         # "critical", "high", "medium", "low", "info"
    system_source: str      # Source system: "GRC", "SAP_ECC", "S4HANA", etc.
    is_exception: bool = False  # True when the item represents an anomaly


@dataclass
class EvidencePackage:
    """
    A versioned, tamper-evident collection of evidence items.

    The ``package_hash`` is a SHA-256 digest of the serialised item list,
    allowing auditors to verify completeness.
    """

    package_id: str
    created_at: datetime
    created_by: str
    start_date: datetime
    end_date: datetime
    categories_requested: List[EvidenceCategoryType]
    items: List[EvidenceItem]
    item_count: int
    package_hash: str
    status: PackageStatus
    title: str
    notes: str = ""

    def __post_init__(self) -> None:
        self.item_count = len(self.items)


@dataclass
class AuditSummary:
    """High-level compliance summary derived from an evidence package."""

    package_id: str
    period_start: datetime
    period_end: datetime
    total_evidence_items: int
    by_category: Dict[str, int]             # category -> item count
    by_risk_level: Dict[str, int]           # risk level -> item count
    exception_count: int
    sod_violations_detected: int
    sod_violations_resolved: int
    open_firefighter_sessions: int
    certifications_completed: int
    provisioning_requests: int
    compliance_score: float                 # 0-100 derived metric
    key_findings: List[str]
    generated_at: datetime


# ---------------------------------------------------------------------------
# Available categories metadata
# ---------------------------------------------------------------------------

_CATEGORIES: List[EvidenceCategory] = [
    EvidenceCategory(EvidenceCategoryType.USER_ACCESS, "User Access Changes",
                     "All access granted, revoked, and reviewed events for user accounts.",
                     ["SOX 404", "ISO 27001 A.9.2", "GDPR Art.25"], 10),
    EvidenceCategory(EvidenceCategoryType.ROLE_CHANGES, "Role Definition Changes",
                     "Modifications to role auth objects, org levels, and menus.",
                     ["SOX 404", "ISO 27001 A.9.4", "SAP GRC"], 8),
    EvidenceCategory(EvidenceCategoryType.APPROVALS, "Access Approvals",
                     "Submitted, approved, and rejected access requests with SLA tracking.",
                     ["SOX 302", "ISO 27001 A.9.2.3"], 8),
    EvidenceCategory(EvidenceCategoryType.SOD_VIOLATIONS, "SoD Violations",
                     "Detected and resolved Separation of Duties conflicts.",
                     ["SOX 404", "COSO 2013", "ISO 27001 A.6.1"], 8),
    EvidenceCategory(EvidenceCategoryType.MITIGATIONS, "SoD Mitigations",
                     "Created, reviewed, and expired mitigation controls for SoD violations.",
                     ["SOX 404", "COSO 2013"], 6),
    EvidenceCategory(EvidenceCategoryType.FIREFIGHTER, "Firefighter Sessions",
                     "Emergency access sessions including activity logs and manager reviews.",
                     ["SOX 404", "ISO 27001 A.9.4.2", "SAP EAM"], 6),
    EvidenceCategory(EvidenceCategoryType.CERTIFICATIONS, "Access Certifications",
                     "Periodic access review campaigns, decisions, and completion statistics.",
                     ["SOX 302", "ISO 27001 A.9.2.5"], 7),
    EvidenceCategory(EvidenceCategoryType.PROVISIONING, "Provisioning Events",
                     "Role provisioning requests, completions, and failures across systems.",
                     ["ISO 27001 A.9.2.1", "SOX 404"], 8),
]


# ---------------------------------------------------------------------------
# In-memory package store (mock persistence)
# ---------------------------------------------------------------------------

_PACKAGE_STORE: Dict[str, EvidencePackage] = {}


# ---------------------------------------------------------------------------
# DB seed helpers
# ---------------------------------------------------------------------------

def _build_default_db_items(now: datetime) -> List[DBAuditEvidenceItem]:
    """Build the full list of default AuditEvidenceItem DB rows."""

    span_days = 30
    start = now - timedelta(days=span_days)

    def ts(days_from_start: float, hours: int = 0) -> datetime:
        offset = max(0.0, min(days_from_start, span_days - 0.01))
        return start + timedelta(days=offset, hours=hours)

    def item(
        eid: str, t: datetime, actor: str, action: str, target: str,
        detail: Dict[str, Any], evidence_type: str, category: str,
        risk_level: str = "info", source_system: str = "GRC",
        is_exception: bool = False,
        compliance_framework: str = "SOX 404",
    ) -> DBAuditEvidenceItem:
        data = dict(detail)
        data["_actor"] = actor
        data["_action"] = action
        data["_target"] = target
        data["_evidence_type"] = evidence_type
        data["_risk_level"] = risk_level
        data["_system_source"] = source_system
        data["_is_exception"] = is_exception
        return DBAuditEvidenceItem(
            evidence_id=eid,
            category=category,
            title=action[:255],
            description=action,
            source_system=source_system,
            compliance_framework=compliance_framework,
            evidence_data=data,
            collected_at=t,
            valid_until=now + timedelta(days=365),
            status="current",
        )

    rows: List[DBAuditEvidenceItem] = []

    # --- USER_ACCESS (10 items) ---
    rows += [
        item("UA-001", ts(0, 9), "ADMIN01", "Granted role Z_FI_AP_CLERK to user JOHN.SMITH",
             "JOHN.SMITH", {"role": "Z_FI_AP_CLERK", "ticket": "INC0001234", "justification": "New joiner"},
             "access_granted", "user_access", "medium", "GRC"),
        item("UA-002", ts(1, 10), "ADMIN01", "Revoked role Z_FI_AP_CLERK from user JANE.DOE",
             "JANE.DOE", {"role": "Z_FI_AP_CLERK", "ticket": "INC0001235", "reason": "Role transfer"},
             "access_revoked", "user_access", "medium", "GRC"),
        item("UA-003", ts(2, 8), "HR_SYSTEM", "Auto-provisioned onboarding roles for new hire MIKE.CHEN",
             "MIKE.CHEN", {"roles": ["Z_HR_TIME_ENTRY", "Z_CO_READ"], "source": "Workday"},
             "access_granted", "user_access", "low", "WORKDAY"),
        item("UA-004", ts(3, 14), "ADMIN02", "Granted SAP_SUPER profile to TEMP.CONTRACTOR01",
             "TEMP.CONTRACTOR01", {"profile": "SAP_SUPER", "ticket": "CHG0009871", "expiry": "30 days"},
             "access_granted", "user_access", "critical", "SAP_ECC", True),
        item("UA-005", ts(5, 11), "ADMIN01", "Revoked emergency access from TEMP.CONTRACTOR01",
             "TEMP.CONTRACTOR01", {"profile": "SAP_SUPER", "ticket": "CHG0009871", "reason": "Access expired"},
             "access_revoked", "user_access", "high", "GRC"),
        item("UA-006", ts(7, 9), "HR_SYSTEM", "Terminated user PETER.LEAVER — all access revoked",
             "PETER.LEAVER", {"roles_removed": 12, "systems": ["SAP_ECC", "FIORI"], "source": "Workday"},
             "access_revoked", "user_access", "high", "WORKDAY"),
        item("UA-007", ts(10, 13), "ADMIN02", "Granted role Z_MM_PURCHASE_ORDER to ALICE.WANG",
             "ALICE.WANG", {"role": "Z_MM_PURCHASE_ORDER", "ticket": "INC0001290"},
             "access_granted", "user_access", "medium", "GRC"),
        item("UA-008", ts(14, 16), "MANAGER01", "Reviewed and confirmed access for BOB.MARTIN",
             "BOB.MARTIN", {"roles_reviewed": 5, "outcome": "all_confirmed"},
             "access_reviewed", "user_access", "info", "GRC"),
        item("UA-009", ts(20, 10), "ADMIN01", "Transferred roles from SARAH.OLD to SARAH.NEW (account rename)",
             "SARAH.NEW", {"roles_transferred": 8, "old_account": "SARAH.OLD"},
             "access_granted", "user_access", "medium", "GRC"),
        item("UA-010", ts(25, 15), "ADMIN03", "Locked user account DAN.SUSPECT after security alert",
             "DAN.SUSPECT", {"reason": "Anomalous login pattern", "ticket": "SEC0000045"},
             "access_revoked", "user_access", "critical", "GRC", True),
    ]

    # --- ROLE_CHANGES (8 items) ---
    rows += [
        item("RC-001", ts(0, 11), "BASIS01", "Created new role Z_FI_BANK_MASTER",
             "Z_FI_BANK_MASTER", {"auth_objects_added": 3, "transport": "DEVK900123"},
             "role_created", "role_changes", "medium", "SAP_ECC"),
        item("RC-002", ts(2, 9), "BASIS01", "Modified role Z_FI_GL_POSTING — added activity 06",
             "Z_FI_GL_POSTING", {"field": "ACTVT", "old_value": "01,02,03", "new_value": "01,02,03,06",
                                  "transport": "DEVK900124", "justified_by": "MANAGER02"},
             "role_modified", "role_changes", "high", "SAP_ECC", True),
        item("RC-003", ts(5, 14), "BASIS02", "Deleted obsolete role Z_OLD_DISPLAY",
             "Z_OLD_DISPLAY", {"reason": "Role consolidation", "transport": "DEVK900125",
                                "users_affected": 3},
             "role_deleted", "role_changes", "medium", "SAP_ECC"),
        item("RC-004", ts(8, 10), "BASIS01", "Modified composite role Z_HR_TIME_MGMT — added child role",
             "Z_HR_TIME_MGMT", {"child_added": "Z_HR_LEAVE_ADMIN", "transport": "DEVK900126"},
             "role_modified", "role_changes", "medium", "SAP_ECC"),
        item("RC-005", ts(12, 8), "EMERGENCY_CHANGE", "Emergency role modification Z_BC_USER_ADMIN in PROD",
             "Z_BC_USER_ADMIN", {"reason": "System outage recovery", "authorized_by": "CIO",
                                  "change_ref": "EMRG-2024-0047"},
             "role_modified", "role_changes", "critical", "SAP_ECC", True),
        item("RC-006", ts(15, 11), "BASIS02", "Added org-level BUKRS 3000 to Z_FI_AP_CLERK",
             "Z_FI_AP_CLERK", {"org_field": "BUKRS", "value_added": "3000", "transport": "DEVK900130"},
             "role_modified", "role_changes", "medium", "SAP_ECC"),
        item("RC-007", ts(18, 13), "BASIS01", "Created cloned role Z_FI_AP_CLERK_READ from Z_FI_AP_CLERK",
             "Z_FI_AP_CLERK_READ", {"cloned_from": "Z_FI_AP_CLERK", "activities_restricted_to": ["03"],
                                      "transport": "DEVK900131"},
             "role_created", "role_changes", "low", "SAP_ECC"),
        item("RC-008", ts(22, 9), "BASIS02", "Removed wildcard value from Z_FI_BANK_MASTER.BUKRS",
             "Z_FI_BANK_MASTER", {"field": "BUKRS", "old_value": "*", "new_value": "1000,2000",
                                   "transport": "DEVK900135", "reason": "Audit finding"},
             "role_modified", "role_changes", "high", "SAP_ECC"),
    ]

    # --- APPROVALS (8 items) ---
    rows += [
        item("AP-001", ts(1, 8), "JOHN.SMITH", "Submitted access request for Z_MM_PURCHASE_ORDER",
             "REQ-20240801-001", {"role_requested": "Z_MM_PURCHASE_ORDER", "business_reason": "New project"},
             "approval_submitted", "approvals", "medium", "GRC"),
        item("AP-002", ts(1, 16), "MANAGER01", "Approved access request REQ-20240801-001",
             "REQ-20240801-001", {"approved_role": "Z_MM_PURCHASE_ORDER", "sla_met": True, "response_hours": 8},
             "approval_approved", "approvals", "medium", "GRC"),
        item("AP-003", ts(3, 9), "ALICE.WANG", "Submitted high-risk access request for Z_BASIS_TRANSPORT",
             "REQ-20240803-007", {"role_requested": "Z_BASIS_TRANSPORT", "risk_level": "high"},
             "approval_submitted", "approvals", "high", "GRC", True),
        item("AP-004", ts(3, 17), "MANAGER02", "Rejected high-risk access request REQ-20240803-007",
             "REQ-20240803-007", {"reason": "Insufficient business justification", "response_hours": 8},
             "approval_rejected", "approvals", "high", "GRC"),
        item("AP-005", ts(6, 10), "BOB.MARTIN", "Submitted bulk access request (3 roles)",
             "REQ-20240806-012", {"roles": ["Z_FI_AP_CLERK", "Z_CO_COST_CENTER", "Z_SD_READ"],
                                   "sod_pre_check": "2 conflicts detected"},
             "approval_submitted", "approvals", "high", "GRC", True),
        item("AP-006", ts(7, 11), "MANAGER01", "Approved partial request REQ-20240806-012 (2 of 3 roles)",
             "REQ-20240806-012", {"approved_roles": ["Z_FI_AP_CLERK", "Z_SD_READ"],
                                   "rejected_roles": ["Z_CO_COST_CENTER"], "reason": "SoD conflict"},
             "approval_approved", "approvals", "high", "GRC"),
        item("AP-007", ts(11, 14), "CAROL.NEW", "Submitted access request for standard onboarding roles",
             "REQ-20240811-020", {"roles": ["Z_HR_TIME_ENTRY", "Z_FI_REPORT_VIEWER"], "auto_approved": True},
             "approval_approved", "approvals", "low", "GRC"),
        item("AP-008", ts(19, 9), "TEMP.CONTRACTOR01", "Submitted request for SAP_SUPER (critical)",
             "REQ-20240819-031", {"role": "SAP_SUPER", "risk_score": 98, "escalated_to": "CISO"},
             "approval_submitted", "approvals", "critical", "GRC", True),
    ]

    # --- SOD_VIOLATIONS (8 items) ---
    rows += [
        item("SV-001", ts(0, 6), "RISK_ENGINE", "SoD violation detected: BOB.MARTIN holds AP Clerk + AP Approver",
             "BOB.MARTIN", {"rule": "FI-001", "functions": ["AP_PROCESSING", "AP_APPROVAL"], "risk_level": "critical"},
             "sod_violation_detected", "sod_violations", "critical", "GRC", True),
        item("SV-002", ts(5, 7), "RISK_ENGINE", "SoD violation detected: ALICE.WANG holds PO Create + PO Approve",
             "ALICE.WANG", {"rule": "MM-003", "functions": ["PO_CREATION", "PO_APPROVAL"]},
             "sod_violation_detected", "sod_violations", "high", "GRC", True),
        item("SV-003", ts(8, 7), "RISK_ENGINE", "SoD violation resolved: BOB.MARTIN — AP_APPROVAL role removed",
             "BOB.MARTIN", {"rule": "FI-001", "resolution": "role_revoked", "resolved_by": "ADMIN01"},
             "sod_violation_resolved", "sod_violations", "critical", "GRC"),
        item("SV-004", ts(10, 7), "RISK_ENGINE", "SoD violation detected: DAN.SUSPECT holds GL Post + GL Approve",
             "DAN.SUSPECT", {"rule": "FI-004", "functions": ["GL_POSTING", "GL_APPROVAL"]},
             "sod_violation_detected", "sod_violations", "critical", "GRC", True),
        item("SV-005", ts(12, 7), "RISK_ENGINE", "SoD violation detected: CAROL.NEW holds Vendor Create + Pay",
             "CAROL.NEW", {"rule": "FI-007", "functions": ["VENDOR_MASTER", "PAYMENT_RUN"]},
             "sod_violation_detected", "sod_violations", "high", "GRC", True),
        item("SV-006", ts(15, 7), "RISK_ENGINE", "SoD violation mitigated: ALICE.WANG — PO_APPROVAL mitigation active",
             "ALICE.WANG", {"rule": "MM-003", "mitigation_id": "MIT-2024-042"},
             "sod_violation_resolved", "sod_violations", "high", "GRC"),
        item("SV-007", ts(20, 7), "RISK_ENGINE", "SoD violation detected: MIKE.CHEN holds HR Pay + HR Config",
             "MIKE.CHEN", {"rule": "HR-002", "functions": ["PAYROLL_PROC", "HR_SYSTEM_CONFIG"]},
             "sod_violation_detected", "sod_violations", "critical", "GRC", True),
        item("SV-008", ts(22, 7), "RISK_ENGINE", "SoD violation resolved: CAROL.NEW — Vendor Create role removed",
             "CAROL.NEW", {"rule": "FI-007", "resolution": "role_revoked", "resolved_by": "ADMIN02"},
             "sod_violation_resolved", "sod_violations", "high", "GRC"),
    ]

    # --- MITIGATIONS (6 items) ---
    rows += [
        item("MT-001", ts(2, 10), "RISK_MGR01", "Created mitigation MIT-2024-041 for MIKE.CHEN (HR-002)",
             "MIT-2024-041", {"user": "MIKE.CHEN", "rule": "HR-002", "control": "Monthly supervisory review",
                               "valid_until": (now + timedelta(days=90)).strftime("%Y-%m-%d")},
             "mitigation_created", "mitigations", "high", "GRC"),
        item("MT-002", ts(4, 11), "RISK_MGR01", "Created mitigation MIT-2024-042 for ALICE.WANG (MM-003)",
             "MIT-2024-042", {"user": "ALICE.WANG", "rule": "MM-003",
                               "control": "Transaction log review bi-weekly",
                               "valid_until": (now + timedelta(days=60)).strftime("%Y-%m-%d")},
             "mitigation_created", "mitigations", "high", "GRC"),
        item("MT-003", ts(10, 14), "RISK_MGR02", "Reviewed mitigation MIT-2024-041 — control effective",
             "MIT-2024-041", {"review_outcome": "effective", "evidence": "No anomalous transactions",
                               "reviewed_by": "RISK_MGR02"},
             "mitigation_reviewed", "mitigations", "medium", "GRC"),
        item("MT-004", ts(16, 9), "SYSTEM", "Mitigation MIT-2024-035 expired — no renewal submitted",
             "MIT-2024-035", {"user": "OLD.USER", "rule": "SD-001", "action_required": "revoke_role"},
             "mitigation_expired", "mitigations", "high", "GRC", True),
        item("MT-005", ts(20, 10), "RISK_MGR01", "Reviewed mitigation MIT-2024-042 — extended 30 days",
             "MIT-2024-042", {"review_outcome": "extended", "reason": "Project not yet complete"},
             "mitigation_reviewed", "mitigations", "medium", "GRC"),
        item("MT-006", ts(24, 11), "RISK_MGR02", "Created mitigation MIT-2024-051 for DAN.SUSPECT (FI-004)",
             "MIT-2024-051", {"user": "DAN.SUSPECT", "rule": "FI-004",
                               "control": "CAAT monitoring — all GL postings reviewed",
                               "valid_until": (now + timedelta(days=30)).strftime("%Y-%m-%d")},
             "mitigation_created", "mitigations", "critical", "GRC", True),
    ]

    # --- FIREFIGHTER (6 items) ---
    rows += [
        item("FF-001", ts(3, 21), "BASIS01", "Opened firefighter session FS-20240803-001 (month-end close)",
             "FS-20240803-001", {"ff_id": "FF_BASIS01", "reason": "Month-end posting block removal",
                                  "approver": "CFO", "system": "PRD"},
             "firefighter_session_opened", "firefighter", "high", "SAP_ECC"),
        item("FF-002", ts(3.1, 22), "BASIS01", "Firefighter activity: executed F.07 in session FS-20240803-001",
             "FS-20240803-001", {"tcode": "F.07", "description": "Recurring entries", "records_affected": 142},
             "firefighter_activity_logged", "firefighter", "high", "SAP_ECC"),
        item("FF-003", ts(4, 1), "BASIS01", "Closed firefighter session FS-20240803-001",
             "FS-20240803-001", {"duration_minutes": 245, "tcodes_used": ["F.07", "FB50"],
                                  "log_reviewed_by": "MANAGER01"},
             "firefighter_session_closed", "firefighter", "high", "SAP_ECC"),
        item("FF-004", ts(12, 14), "ADMIN_EMRG", "Opened emergency firefighter session FS-20240812-002",
             "FS-20240812-002", {"ff_id": "FF_EMRG", "reason": "Critical system patch",
                                  "approver": "CIO", "system": "PRD"},
             "firefighter_session_opened", "firefighter", "critical", "SAP_ECC", True),
        item("FF-005", ts(12, 18), "ADMIN_EMRG",
             "Firefighter activity: modified system parameters in FS-20240812-002",
             "FS-20240812-002", {"tcode": "RZ10", "description": "Profile parameter change",
                                  "param": "login/min_password_length"},
             "firefighter_activity_logged", "firefighter", "critical", "SAP_ECC", True),
        item("FF-006", ts(12, 21), "ADMIN_EMRG", "Closed firefighter session FS-20240812-002",
             "FS-20240812-002", {"duration_minutes": 420, "tcodes_used": ["RZ10", "SM50", "SM04"],
                                  "log_reviewed_by": "CISO"},
             "firefighter_session_closed", "firefighter", "critical", "SAP_ECC"),
    ]

    # --- CERTIFICATIONS (7 items) ---
    rows += [
        item("CE-001", ts(0, 8), "SYSTEM", "Certification campaign Q3-2024 started — 142 users in scope",
             "CAMP-Q3-2024", {"users_in_scope": 142, "certifiers": 18,
                               "deadline": (now - timedelta(days=5)).strftime("%Y-%m-%d")},
             "certification_campaign_started", "certifications", "info", "GRC"),
        item("CE-002", ts(2, 9), "MANAGER01", "Certification decision: confirmed JOHN.SMITH access (all 4 roles)",
             "CAMP-Q3-2024", {"user": "JOHN.SMITH", "roles_confirmed": 4, "roles_removed": 0},
             "certification_decision_made", "certifications", "low", "GRC"),
        item("CE-003", ts(4, 10), "MANAGER02", "Certification decision: revoked 2 roles for PETER.LEAVER",
             "CAMP-Q3-2024", {"user": "PETER.LEAVER", "roles_confirmed": 1, "roles_removed": 2,
                               "removed": ["Z_FI_GL_POSTING", "Z_CO_COST_CENTER"]},
             "certification_decision_made", "certifications", "high", "GRC"),
        item("CE-004", ts(6, 11), "MANAGER01",
             "Certification decision: escalated DAN.SUSPECT for security review",
             "CAMP-Q3-2024", {"user": "DAN.SUSPECT", "escalated_to": "CISO",
                               "reason": "Anomalous access pattern"},
             "certification_decision_made", "certifications", "critical", "GRC", True),
        item("CE-005", ts(10, 14), "MANAGER03",
             "Certification decision: revoked Z_BASIS_TRANSPORT from ALICE.WANG",
             "CAMP-Q3-2024", {"user": "ALICE.WANG", "roles_removed": 1,
                               "removed": ["Z_BASIS_TRANSPORT"]},
             "certification_decision_made", "certifications", "high", "GRC"),
        item("CE-006", ts(20, 9), "MANAGER04", "Certification decision: confirmed all access for CAROL.NEW",
             "CAMP-Q3-2024", {"user": "CAROL.NEW", "roles_confirmed": 3, "roles_removed": 0},
             "certification_decision_made", "certifications", "low", "GRC"),
        item("CE-007", ts(span_days - 1, 17), "SYSTEM",
             "Certification campaign Q3-2024 completed — 97.2% review rate",
             "CAMP-Q3-2024", {"users_reviewed": 138, "users_total": 142, "roles_revoked": 23,
                               "exceptions_escalated": 4},
             "certification_campaign_completed", "certifications", "info", "GRC"),
    ]

    # --- PROVISIONING (8 items) ---
    rows += [
        item("PR-001", ts(1, 12), "PROV_ENGINE", "Provisioning request raised: JOHN.SMITH / Z_FI_AP_CLERK",
             "PROV-20240801-001", {"user": "JOHN.SMITH", "role": "Z_FI_AP_CLERK", "target_system": "PRD"},
             "provisioning_request_raised", "provisioning", "medium", "GRC"),
        item("PR-002", ts(1, 14), "PROV_ENGINE", "Provisioning completed: JOHN.SMITH / Z_FI_AP_CLERK in PRD",
             "PROV-20240801-001", {"user": "JOHN.SMITH", "role": "Z_FI_AP_CLERK", "system": "PRD",
                                    "duration_minutes": 2},
             "provisioning_completed", "provisioning", "medium", "GRC"),
        item("PR-003", ts(2, 11), "PROV_ENGINE",
             "Provisioning request raised: ALICE.WANG / Z_MM_PURCHASE_ORDER",
             "PROV-20240802-003", {"user": "ALICE.WANG", "role": "Z_MM_PURCHASE_ORDER",
                                    "target_system": "PRD"},
             "provisioning_request_raised", "provisioning", "medium", "GRC"),
        item("PR-004", ts(2, 13), "PROV_ENGINE",
             "Provisioning failed: ALICE.WANG / Z_MM_PURCHASE_ORDER (RFC error)",
             "PROV-20240802-003", {"user": "ALICE.WANG", "role": "Z_MM_PURCHASE_ORDER",
                                    "error": "RFC_CALL_EXCEPTION", "retry_scheduled": True},
             "provisioning_failed", "provisioning", "high", "GRC", True),
        item("PR-005", ts(2, 15), "PROV_ENGINE",
             "Provisioning completed (retry): ALICE.WANG / Z_MM_PURCHASE_ORDER",
             "PROV-20240802-003", {"user": "ALICE.WANG", "role": "Z_MM_PURCHASE_ORDER",
                                    "retry_attempt": 2},
             "provisioning_completed", "provisioning", "medium", "GRC"),
        item("PR-006", ts(7, 10), "PROV_ENGINE",
             "De-provisioning completed: PETER.LEAVER — 12 roles removed",
             "PROV-20240807-018", {"user": "PETER.LEAVER", "roles_removed": 12,
                                    "systems": ["PRD", "QA"]},
             "provisioning_completed", "provisioning", "high", "GRC"),
        item("PR-007", ts(14, 11), "PROV_ENGINE",
             "Provisioning request raised: MIKE.CHEN / Z_HR_PAYROLL_PROC",
             "PROV-20240814-022", {"user": "MIKE.CHEN", "role": "Z_HR_PAYROLL_PROC",
                                    "sod_pre_check": "PASS", "target_system": "PRD"},
             "provisioning_request_raised", "provisioning", "high", "GRC"),
        item("PR-008", ts(14, 12), "PROV_ENGINE",
             "Provisioning completed: MIKE.CHEN / Z_HR_PAYROLL_PROC",
             "PROV-20240814-022", {"user": "MIKE.CHEN", "role": "Z_HR_PAYROLL_PROC",
                                    "system": "PRD", "duration_minutes": 1},
             "provisioning_completed", "provisioning", "high", "GRC"),
    ]

    return rows


def _ensure_loaded(tenant_id: str = "tenant_default") -> None:
    """Seed the audit_evidence table with default data if it is empty."""
    with db_manager.session_scope() as session:
        count = session.query(DBAuditEvidenceItem).filter_by(tenant_id=tenant_id).count()
        if count == 0:
            now = datetime.utcnow()
            defaults = _build_default_db_items(now)
            for row in defaults:
                row.tenant_id = tenant_id
            session.add_all(defaults)
            logger.info("audit_evidence_collector: seeded %d default items", len(defaults))


# ---------------------------------------------------------------------------
# Conversion helper: DB row → EvidenceItem dataclass
# ---------------------------------------------------------------------------

def _row_to_evidence_item(row: DBAuditEvidenceItem) -> EvidenceItem:
    """Convert a DBAuditEvidenceItem ORM row to an EvidenceItem dataclass."""
    data: Dict[str, Any] = row.evidence_data or {}
    actor = data.pop("_actor", "SYSTEM")
    action = data.pop("_action", row.title or "")
    target = data.pop("_target", "")
    evidence_type_str = data.pop("_evidence_type", "access_granted")
    risk_level = data.pop("_risk_level", "info")
    system_source = data.pop("_system_source", row.source_system or "GRC")
    is_exception = data.pop("_is_exception", False)

    try:
        evidence_type = EvidenceItemType(evidence_type_str)
    except ValueError:
        evidence_type = EvidenceItemType.ACCESS_GRANTED

    try:
        category = EvidenceCategoryType(row.category)
    except ValueError:
        category = EvidenceCategoryType.USER_ACCESS

    return EvidenceItem(
        item_id=row.evidence_id,
        timestamp=row.collected_at,
        actor=actor,
        action=action,
        target=target,
        detail=data,
        evidence_type=evidence_type,
        category=category,
        risk_level=risk_level,
        system_source=system_source,
        is_exception=bool(is_exception),
    )


# ---------------------------------------------------------------------------
# DB query replacing _build_mock_items
# ---------------------------------------------------------------------------

def _build_items_from_db(
    start_date: datetime,
    end_date: datetime,
    tenant_id: str = "tenant_default",
) -> List[EvidenceItem]:
    """Query DB for evidence items within the date range."""
    _ensure_loaded(tenant_id)
    with db_manager.session_scope() as session:
        rows = (
            session.query(DBAuditEvidenceItem)
            .filter(
                DBAuditEvidenceItem.tenant_id == tenant_id,
                DBAuditEvidenceItem.collected_at >= start_date,
                DBAuditEvidenceItem.collected_at <= end_date,
            )
            .order_by(DBAuditEvidenceItem.collected_at)
            .all()
        )
        return [_row_to_evidence_item(r) for r in rows]


# ---------------------------------------------------------------------------
# AuditEvidenceCollector — public engine
# ---------------------------------------------------------------------------


class AuditEvidenceCollector:
    """
    Collects and packages audit evidence across all GRC modules.

    Usage::

        collector = AuditEvidenceCollector()
        package   = collector.collect_evidence(start, end, categories)
        summary   = collector.generate_summary(package)
    """

    def get_available_categories(self) -> List[EvidenceCategory]:
        """
        Return all available evidence categories with metadata.

        Returns
        -------
        List[EvidenceCategory]
            One entry per GRC evidence domain.
        """
        return list(_CATEGORIES)

    def collect_evidence(
        self,
        start_date: datetime,
        end_date: datetime,
        categories: Optional[List[EvidenceCategoryType]] = None,
        created_by: str = "system",
        title: str = "",
        notes: str = "",
        tenant_id: str = "tenant_default",
    ) -> EvidencePackage:
        """
        Collect evidence for the specified date range and categories.

        Parameters
        ----------
        start_date:
            Inclusive start of the evidence window.
        end_date:
            Inclusive end of the evidence window.
        categories:
            Subset of EvidenceCategoryType values to collect.  If None,
            all categories are included.
        created_by:
            User or system initiating the collection.
        title:
            Optional human-readable title for the package.
        notes:
            Optional notes to attach to the package.
        tenant_id:
            Tenant to query evidence for.

        Returns
        -------
        EvidencePackage
            Assembled, hashed evidence package stored in memory.
        """
        if start_date > end_date:
            raise ValueError("start_date must be before end_date.")

        requested_categories = list(categories) if categories else list(EvidenceCategoryType)

        all_items = _build_items_from_db(start_date, end_date, tenant_id)
        filtered_items = [i for i in all_items if i.category in requested_categories]
        filtered_items.sort(key=lambda x: x.timestamp)

        package_id = f"PKG-{uuid.uuid4().hex[:12].upper()}"
        package_hash = self._compute_package_hash(filtered_items)
        package_title = title or (
            f"Audit Evidence {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
        )

        package = EvidencePackage(
            package_id=package_id,
            created_at=datetime.utcnow(),
            created_by=created_by,
            start_date=start_date,
            end_date=end_date,
            categories_requested=requested_categories,
            items=filtered_items,
            item_count=len(filtered_items),
            package_hash=package_hash,
            status=PackageStatus.DRAFT,
            title=package_title,
            notes=notes,
        )

        _PACKAGE_STORE[package_id] = package
        logger.info("evidence_package_created", extra={"package_id": package_id, "item_count": len(filtered_items)})
        return package

    def generate_summary(self, package: EvidencePackage) -> AuditSummary:
        """
        Generate a compliance summary from an evidence package.

        Parameters
        ----------
        package:
            The EvidencePackage to summarise.

        Returns
        -------
        AuditSummary
            High-level metrics and key findings.
        """
        by_category: Dict[str, int] = {cat.value: 0 for cat in EvidenceCategoryType}
        by_risk: Dict[str, int] = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
        exceptions = 0
        sod_detected = 0
        sod_resolved = 0
        open_ff = 0
        ff_opened = 0
        ff_closed = 0
        certs_completed = 0
        prov_requests = 0

        for item in package.items:
            by_category[item.category.value] += 1
            by_risk[item.risk_level] = by_risk.get(item.risk_level, 0) + 1
            if item.is_exception:
                exceptions += 1
            if item.evidence_type == EvidenceItemType.SOD_VIOLATION_DETECTED:
                sod_detected += 1
            if item.evidence_type == EvidenceItemType.SOD_VIOLATION_RESOLVED:
                sod_resolved += 1
            if item.evidence_type == EvidenceItemType.FIREFIGHTER_SESSION_OPENED:
                ff_opened += 1
            if item.evidence_type == EvidenceItemType.FIREFIGHTER_SESSION_CLOSED:
                ff_closed += 1
            if item.evidence_type == EvidenceItemType.CERTIFICATION_CAMPAIGN_COMPLETED:
                certs_completed += 1
            if item.evidence_type == EvidenceItemType.PROVISIONING_REQUEST_RAISED:
                prov_requests += 1

        open_ff = max(0, ff_opened - ff_closed)

        key_findings: List[str] = []
        if by_risk["critical"] > 0:
            key_findings.append(f"{by_risk['critical']} critical-risk events require immediate review.")
        if sod_detected > sod_resolved:
            key_findings.append(f"{sod_detected - sod_resolved} SoD violations remain open.")
        if open_ff > 0:
            key_findings.append(f"{open_ff} firefighter session(s) without a matching close event.")
        if exceptions > 0:
            key_findings.append(f"{exceptions} exception items flagged for auditor attention.")
        if not key_findings:
            key_findings.append("No critical findings in this evidence package.")

        total = len(package.items)
        exceptions_pct = exceptions / total if total > 0 else 0
        compliance_score = max(0.0, round(100.0 - (exceptions_pct * 100 * 0.6) - (by_risk["critical"] * 2.5), 1))

        return AuditSummary(
            package_id=package.package_id,
            period_start=package.start_date,
            period_end=package.end_date,
            total_evidence_items=total,
            by_category=by_category,
            by_risk_level=by_risk,
            exception_count=exceptions,
            sod_violations_detected=sod_detected,
            sod_violations_resolved=sod_resolved,
            open_firefighter_sessions=open_ff,
            certifications_completed=certs_completed,
            provisioning_requests=prov_requests,
            compliance_score=compliance_score,
            key_findings=key_findings,
            generated_at=datetime.utcnow(),
        )

    def get_packages(self) -> List[EvidencePackage]:
        """
        Return all previously generated packages (without item payloads).

        Returns
        -------
        List[EvidencePackage]
            Packages sorted by creation date descending.
        """
        packages = list(_PACKAGE_STORE.values())
        packages.sort(key=lambda p: p.created_at, reverse=True)
        # Strip items for list view to reduce payload size
        return [
            EvidencePackage(
                package_id=p.package_id,
                created_at=p.created_at,
                created_by=p.created_by,
                start_date=p.start_date,
                end_date=p.end_date,
                categories_requested=p.categories_requested,
                items=[],
                item_count=p.item_count,
                package_hash=p.package_hash,
                status=p.status,
                title=p.title,
                notes=p.notes,
            )
            for p in packages
        ]

    def get_package(self, package_id: str) -> Optional[EvidencePackage]:
        """
        Retrieve a specific package by ID.

        Parameters
        ----------
        package_id:
            The package identifier returned from ``collect_evidence``.

        Returns
        -------
        EvidencePackage or None
        """
        return _PACKAGE_STORE.get(package_id)

    def export_package(self, package_id: str) -> Dict[str, Any]:
        """
        Export a package as a structured JSON-serialisable dict.

        Parameters
        ----------
        package_id:
            The package to export.

        Returns
        -------
        dict
            Fully serialised package including all evidence items.

        Raises
        ------
        KeyError
            If the package_id does not exist.
        """
        package = _PACKAGE_STORE.get(package_id)
        if not package:
            raise KeyError(f"Package '{package_id}' not found.")

        # Mark as exported
        package.status = PackageStatus.EXPORTED

        return {
            "package_id": package.package_id,
            "title": package.title,
            "created_at": package.created_at.isoformat(),
            "created_by": package.created_by,
            "start_date": package.start_date.isoformat(),
            "end_date": package.end_date.isoformat(),
            "categories": [c.value for c in package.categories_requested],
            "item_count": package.item_count,
            "package_hash": package.package_hash,
            "status": package.status.value,
            "notes": package.notes,
            "items": [
                {
                    "item_id": item.item_id,
                    "timestamp": item.timestamp.isoformat(),
                    "actor": item.actor,
                    "action": item.action,
                    "target": item.target,
                    "detail": item.detail,
                    "evidence_type": item.evidence_type.value,
                    "category": item.category.value,
                    "risk_level": item.risk_level,
                    "system_source": item.system_source,
                    "is_exception": item.is_exception,
                }
                for item in package.items
            ],
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_package_hash(items: List[EvidenceItem]) -> str:
        """SHA-256 hash of the serialised item list for tamper detection."""
        payload = json.dumps(
            [
                {
                    "item_id": i.item_id,
                    "timestamp": i.timestamp.isoformat(),
                    "actor": i.actor,
                    "action": i.action,
                    "target": i.target,
                    "evidence_type": i.evidence_type.value,
                }
                for i in items
            ],
            sort_keys=True,
        )
        return hashlib.sha256(payload.encode()).hexdigest()
