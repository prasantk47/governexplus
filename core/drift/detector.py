"""
Role Drift Detection Engine

Compares role definitions across system landscapes (DEV, QA, PROD) to
identify unauthorized changes, missing transports, version mismatches,
and configuration drift that introduce compliance or security risk.

Drift is quantified via a SHA-256-based "drift hash" computed from the
canonical role definition per system.  When hashes differ between
systems the engine decomposes the delta into structured findings.

Data is persisted in the ``drift_snapshots`` table (``DriftSnapshot`` model).
On first run the table is empty and the engine seeds it with the full
25-role hardcoded landscape so that the application is usable immediately
without a real SAP connection.  Subsequent calls load from the DB.
"""

import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Tuple

from db.models.intelligence import DriftSnapshot
from db.database import db_manager

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class DriftSeverity(str, Enum):
    """Severity classification for a drift finding."""

    CRITICAL = "critical"   # Role missing in PROD or wildcard values added
    HIGH = "high"           # Auth object values differ or org levels removed
    MEDIUM = "medium"       # Version mismatch or description change
    LOW = "low"             # Minor metadata difference
    INFO = "info"           # Role exists in all systems, fully aligned


class DriftType(str, Enum):
    """Category of drift observed."""

    MISSING_IN_SYSTEM = "missing_in_system"        # Role absent from one or more systems
    EXTRA_AUTH_VALUE = "extra_auth_value"           # Additional authorization value in one system
    REMOVED_AUTH_VALUE = "removed_auth_value"       # Authorization value removed in one system
    ORG_LEVEL_MISMATCH = "org_level_mismatch"       # Org-level field differs across systems
    VERSION_MISMATCH = "version_mismatch"           # Transport/version counter differs
    DESCRIPTION_CHANGED = "description_changed"     # Role description text differs
    MENU_CHANGED = "menu_changed"                   # Role menu structure changed
    PROFILE_MISMATCH = "profile_mismatch"           # Generated profile name differs
    AUTH_OBJECT_ADDED = "auth_object_added"         # Entire auth object added in one system
    AUTH_OBJECT_REMOVED = "auth_object_removed"     # Entire auth object removed in one system


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class AuthObjectDefinition:
    """Authorization object with field values as they appear in a role."""

    object_name: str                        # e.g. "F_BKPF_BUK"
    fields: Dict[str, List[str]]            # field_name -> list of permitted values
    activity_codes: List[str] = field(default_factory=list)


@dataclass
class OrgLevelDefinition:
    """Organizational level assignment within a role."""

    field_name: str     # e.g. "BUKRS", "WERKS"
    values: List[str]   # e.g. ["1000", "2000"]


@dataclass
class RoleSystemSnapshot:
    """
    A point-in-time snapshot of a role's definition in one system.

    All values are taken directly from the SAP role master (AGR_DEFINE,
    AGR_1251, AGR_ORGLEVELS) or their mock equivalents.
    """

    system_id: str                                          # "DEV", "QA", "PROD"
    role_name: str
    description: str
    version: str                                            # Transport counter / version tag
    profile_name: str                                       # Generated profile, e.g. T-AG100001
    auth_objects: List[AuthObjectDefinition] = field(default_factory=list)
    org_levels: List[OrgLevelDefinition] = field(default_factory=list)
    menu_nodes: List[str] = field(default_factory=list)     # T-codes in role menu
    last_changed_by: str = ""
    last_changed_at: Optional[datetime] = None
    is_composite: bool = False
    child_roles: List[str] = field(default_factory=list)


@dataclass
class DriftFinding:
    """A single, atomic drift observation between two systems."""

    finding_id: str
    drift_type: DriftType
    severity: DriftSeverity
    system_a: str
    system_b: str
    field_path: str          # Human-readable path: e.g. "auth_objects[F_BKPF_BUK].ACTVT"
    value_in_a: str
    value_in_b: str
    description: str
    remediation: str


@dataclass
class DriftReport:
    """
    Full drift analysis for a single role across all configured systems.

    The ``drift_hash`` dict maps system_id -> hash string.  Identical
    hashes mean the role definition is byte-for-byte equivalent on those
    systems.
    """

    role_name: str
    role_description: str
    scan_timestamp: datetime
    systems_present: List[str]
    systems_missing: List[str]
    drift_hash: Dict[str, str]          # system_id -> hash
    is_drifted: bool
    overall_severity: DriftSeverity
    findings: List[DriftFinding] = field(default_factory=list)
    finding_count: int = 0

    def __post_init__(self) -> None:
        self.finding_count = len(self.findings)


@dataclass
class DriftSummary:
    """Aggregated drift statistics across the full role estate."""

    scan_timestamp: datetime
    total_roles_scanned: int
    roles_in_sync: int
    roles_drifted: int
    by_severity: Dict[str, int]         # severity label -> count of roles at that severity
    by_drift_type: Dict[str, int]       # drift_type label -> total occurrences
    most_drifted_roles: List[str]       # Top 10 role names by finding count
    systems_compared: List[str]
    drift_percentage: float


# ---------------------------------------------------------------------------
# Serialisation helpers — convert between RoleSystemSnapshot and DB row
# ---------------------------------------------------------------------------

def _snapshot_to_db_fields(snap: RoleSystemSnapshot) -> dict:
    """
    Serialise a ``RoleSystemSnapshot`` into the JSON columns stored in
    ``DriftSnapshot``.

    Column mapping
    ~~~~~~~~~~~~~~
    * ``transactions``  — snapshot metadata dict (description, version,
                          profile_name, is_composite, child_roles,
                          last_changed_by, last_changed_at).
    * ``auth_objects``  — list of auth object dicts.
    * ``org_levels``    — list of org level dicts.
    * ``menu_nodes``    — list of tcode strings.
    """
    return {
        "transactions": {
            "description": snap.description,
            "version": snap.version,
            "profile_name": snap.profile_name,
            "is_composite": snap.is_composite,
            "child_roles": snap.child_roles,
            "last_changed_by": snap.last_changed_by,
            "last_changed_at": snap.last_changed_at.isoformat() if snap.last_changed_at else None,
        },
        "auth_objects": [
            {
                "object_name": ao.object_name,
                "fields": ao.fields,
                "activity_codes": ao.activity_codes,
            }
            for ao in snap.auth_objects
        ],
        "org_levels": [
            {"field_name": ol.field_name, "values": ol.values}
            for ol in snap.org_levels
        ],
        "menu_nodes": snap.menu_nodes,
    }


def _db_row_to_snapshot(row: DriftSnapshot) -> RoleSystemSnapshot:
    """Reconstruct a ``RoleSystemSnapshot`` from a ``DriftSnapshot`` DB row."""
    meta: dict = row.transactions or {}
    last_changed_at: Optional[datetime] = None
    if meta.get("last_changed_at"):
        try:
            last_changed_at = datetime.fromisoformat(meta["last_changed_at"])
        except (ValueError, TypeError):
            last_changed_at = None

    auth_objects: List[AuthObjectDefinition] = [
        AuthObjectDefinition(
            object_name=ao["object_name"],
            fields=ao.get("fields", {}),
            activity_codes=ao.get("activity_codes", []),
        )
        for ao in (row.auth_objects or [])
    ]
    org_levels: List[OrgLevelDefinition] = [
        OrgLevelDefinition(field_name=ol["field_name"], values=ol.get("values", []))
        for ol in (row.org_levels or [])
    ]

    return RoleSystemSnapshot(
        system_id=row.system,
        role_name=row.role_name,
        description=meta.get("description", ""),
        version=meta.get("version", "0000"),
        profile_name=meta.get("profile_name", ""),
        auth_objects=auth_objects,
        org_levels=org_levels,
        menu_nodes=list(row.menu_nodes or []),
        last_changed_by=meta.get("last_changed_by", ""),
        last_changed_at=last_changed_at,
        is_composite=meta.get("is_composite", False),
        child_roles=list(meta.get("child_roles", [])),
    )


# ---------------------------------------------------------------------------
# Hardcoded seed landscape — 25 roles across DEV/QA/PROD
# ---------------------------------------------------------------------------

def _build_seed_landscape() -> Dict[str, Dict[str, RoleSystemSnapshot]]:
    """
    Returns: { role_name: { system_id: RoleSystemSnapshot } }

    Covers the following drift scenarios:
    - Role present in DEV+QA but missing from PROD
    - Auth object added in PROD but not in DEV
    - Org-level values differ between QA and PROD
    - Version counter ahead in DEV (transport not yet moved)
    - Description changed between systems
    - Activity codes widened (e.g. display-only -> display+change)
    - Profile name mismatch after emergency change
    - Auth object removed in PROD (security hardening applied only there)
    - Composite role with different child role membership
    - Fully aligned role (no drift)
    """

    now = datetime.utcnow()
    d = now - timedelta(days=5)
    q = now - timedelta(days=3)
    p = now - timedelta(days=10)

    landscape: Dict[str, Dict[str, RoleSystemSnapshot]] = {}

    # ------------------------------------------------------------------
    # 1. Z_FI_AP_CLERK — fully aligned, no drift
    # ------------------------------------------------------------------
    for sys_id, ts in [("DEV", d), ("QA", q), ("PROD", p)]:
        landscape.setdefault("Z_FI_AP_CLERK", {})[sys_id] = RoleSystemSnapshot(
            system_id=sys_id,
            role_name="Z_FI_AP_CLERK",
            description="Accounts Payable Clerk",
            version="0042",
            profile_name="T-AG100001",
            auth_objects=[
                AuthObjectDefinition("F_BKPF_BUK", {"BUKRS": ["1000", "2000"], "ACTVT": ["01", "02", "03"]}),
                AuthObjectDefinition("F_BKPF_KOA", {"KOART": ["K"], "ACTVT": ["01", "02", "03"]}),
            ],
            org_levels=[OrgLevelDefinition("BUKRS", ["1000", "2000"])],
            menu_nodes=["FB60", "FB65", "FBL1N", "F110"],
            last_changed_by="TRANSPORT",
            last_changed_at=ts,
        )

    # ------------------------------------------------------------------
    # 2. Z_FI_GL_POSTING — DEV has extra ACTVT "06" (delete) not in PROD
    # ------------------------------------------------------------------
    for sys_id, actvt, ts in [("DEV", ["01", "02", "03", "06"], d), ("QA", ["01", "02", "03"], q), ("PROD", ["01", "02", "03"], p)]:
        landscape.setdefault("Z_FI_GL_POSTING", {})[sys_id] = RoleSystemSnapshot(
            system_id=sys_id,
            role_name="Z_FI_GL_POSTING",
            description="General Ledger Posting",
            version="0018",
            profile_name="T-AG100002",
            auth_objects=[
                AuthObjectDefinition("F_BKPF_BUK", {"BUKRS": ["1000"], "ACTVT": actvt}),
            ],
            org_levels=[OrgLevelDefinition("BUKRS", ["1000"])],
            menu_nodes=["FB50", "FB03"],
            last_changed_by="DEVUSER01" if sys_id == "DEV" else "TRANSPORT",
            last_changed_at=ts,
        )

    # ------------------------------------------------------------------
    # 3. Z_MM_PURCHASE_ORDER — missing from PROD (transport pending)
    # ------------------------------------------------------------------
    for sys_id, ts in [("DEV", d), ("QA", q)]:
        landscape.setdefault("Z_MM_PURCHASE_ORDER", {})[sys_id] = RoleSystemSnapshot(
            system_id=sys_id,
            role_name="Z_MM_PURCHASE_ORDER",
            description="Purchase Order Creator",
            version="0007",
            profile_name="T-AG100003",
            auth_objects=[
                AuthObjectDefinition("M_EINF_BSA", {"BSART": ["NB", "ZNB"], "ACTVT": ["01", "02"]}),
            ],
            org_levels=[OrgLevelDefinition("WERKS", ["1000", "2000"])],
            menu_nodes=["ME21N", "ME22N", "ME23N"],
            last_changed_by="TRANSPORT",
            last_changed_at=ts,
        )

    # ------------------------------------------------------------------
    # 4. Z_HR_PAYROLL_PROC — org level MOLGA differs between QA and PROD
    # ------------------------------------------------------------------
    for sys_id, molga_vals, ts in [("DEV", ["01"], d), ("QA", ["01", "08"], q), ("PROD", ["01"], p)]:
        landscape.setdefault("Z_HR_PAYROLL_PROC", {})[sys_id] = RoleSystemSnapshot(
            system_id=sys_id,
            role_name="Z_HR_PAYROLL_PROC",
            description="Payroll Processing",
            version="0031",
            profile_name="T-AG100004",
            auth_objects=[
                AuthObjectDefinition("P_ORGIN", {"INFTY": ["0008", "0014"], "ACTVT": ["01", "02", "03"]}),
            ],
            org_levels=[OrgLevelDefinition("MOLGA", molga_vals)],
            menu_nodes=["PC00_M01_CALC", "PC00_M01_CDOC"],
            last_changed_by="TRANSPORT",
            last_changed_at=ts,
        )

    # ------------------------------------------------------------------
    # 5. Z_SD_SALES_ORDER — version mismatch, DEV is 2 transports ahead
    # ------------------------------------------------------------------
    for sys_id, ver, ts in [("DEV", "0055", d), ("QA", "0053", q), ("PROD", "0053", p)]:
        landscape.setdefault("Z_SD_SALES_ORDER", {})[sys_id] = RoleSystemSnapshot(
            system_id=sys_id,
            role_name="Z_SD_SALES_ORDER",
            description="Sales Order Management",
            version=ver,
            profile_name="T-AG100005",
            auth_objects=[
                AuthObjectDefinition("V_VBAK_AAT", {"AUART": ["TA", "KR"], "ACTVT": ["01", "02", "03"]}),
            ],
            org_levels=[OrgLevelDefinition("VKORG", ["1000"])],
            menu_nodes=["VA01", "VA02", "VA03"],
            last_changed_by="DEVUSER02" if sys_id == "DEV" else "TRANSPORT",
            last_changed_at=ts,
        )

    # ------------------------------------------------------------------
    # 6. Z_BASIS_TRANSPORT — auth object S_TRANSPRT added in DEV only
    # ------------------------------------------------------------------
    for sys_id, extra_obj, ts in [("DEV", True, d), ("QA", False, q), ("PROD", False, p)]:
        auth_objs = [AuthObjectDefinition("S_TCODE", {"TCD": ["SE09", "SE10"]}, activity_codes=["01", "02", "03"])]
        if extra_obj:
            auth_objs.append(AuthObjectDefinition("S_TRANSPRT", {"TTYPE": ["CUST", "TASK"], "ACTVT": ["01"]}, activity_codes=["01"]))
        landscape.setdefault("Z_BASIS_TRANSPORT", {})[sys_id] = RoleSystemSnapshot(
            system_id=sys_id,
            role_name="Z_BASIS_TRANSPORT",
            description="Transport Management",
            version="0012",
            profile_name="T-AG100006",
            auth_objects=auth_objs,
            org_levels=[],
            menu_nodes=["SE09", "SE10", "STMS"],
            last_changed_by="BASIS01" if sys_id == "DEV" else "TRANSPORT",
            last_changed_at=ts,
        )

    # ------------------------------------------------------------------
    # 7. Z_FI_ASSET_MGMT — description changed in PROD after emergency patch
    # ------------------------------------------------------------------
    for sys_id, desc, ts in [("DEV", "Asset Management", d), ("QA", "Asset Management", q), ("PROD", "Asset Management (Restricted)", p)]:
        landscape.setdefault("Z_FI_ASSET_MGMT", {})[sys_id] = RoleSystemSnapshot(
            system_id=sys_id,
            role_name="Z_FI_ASSET_MGMT",
            description=desc,
            version="0022",
            profile_name="T-AG100007",
            auth_objects=[
                AuthObjectDefinition("A_ANLKL", {"ANLKL": ["*"], "ACTVT": ["01", "02", "03", "06"]}),
            ],
            org_levels=[OrgLevelDefinition("BUKRS", ["1000"])],
            menu_nodes=["AS01", "AS02", "AS03", "AW01N"],
            last_changed_by="TRANSPORT",
            last_changed_at=ts,
        )

    # ------------------------------------------------------------------
    # 8. Z_CO_COST_CENTER — menu node removed in PROD (KP06 removed)
    # ------------------------------------------------------------------
    for sys_id, menu, ts in [("DEV", ["KP06", "KSB1", "KS01"], d), ("QA", ["KP06", "KSB1", "KS01"], q), ("PROD", ["KSB1", "KS01"], p)]:
        landscape.setdefault("Z_CO_COST_CENTER", {})[sys_id] = RoleSystemSnapshot(
            system_id=sys_id,
            role_name="Z_CO_COST_CENTER",
            description="Cost Center Accountant",
            version="0019",
            profile_name="T-AG100008",
            auth_objects=[
                AuthObjectDefinition("K_CSKS", {"KOSTL": ["100000", "200000"], "ACTVT": ["01", "02", "03"]}),
            ],
            org_levels=[OrgLevelDefinition("KOKRS", ["CO01"])],
            menu_nodes=menu,
            last_changed_by="TRANSPORT",
            last_changed_at=ts,
        )

    # ------------------------------------------------------------------
    # 9. Z_PM_MAINTENANCE — org levels completely absent in QA
    # ------------------------------------------------------------------
    for sys_id, org_lvls, ts in [("DEV", [OrgLevelDefinition("WERKS", ["1000"])], d), ("QA", [], q), ("PROD", [OrgLevelDefinition("WERKS", ["1000"])], p)]:
        landscape.setdefault("Z_PM_MAINTENANCE", {})[sys_id] = RoleSystemSnapshot(
            system_id=sys_id,
            role_name="Z_PM_MAINTENANCE",
            description="Plant Maintenance Technician",
            version="0008",
            profile_name="T-AG100009",
            auth_objects=[
                AuthObjectDefinition("I_QMEL", {"QMART": ["M1", "M2"], "ACTVT": ["01", "02"]}),
            ],
            org_levels=org_lvls,
            menu_nodes=["IW21", "IW22", "IW31"],
            last_changed_by="TRANSPORT",
            last_changed_at=ts,
        )

    # ------------------------------------------------------------------
    # 10. Z_SD_BILLING — profile name differs (emergency regen in PROD)
    # ------------------------------------------------------------------
    for sys_id, profile, ts in [("DEV", "T-AG100010", d), ("QA", "T-AG100010", q), ("PROD", "T-AG100010X", p)]:
        landscape.setdefault("Z_SD_BILLING", {})[sys_id] = RoleSystemSnapshot(
            system_id=sys_id,
            role_name="Z_SD_BILLING",
            description="Billing Clerk",
            version="0029",
            profile_name=profile,
            auth_objects=[
                AuthObjectDefinition("V_VBRK_FKA", {"FKART": ["F2", "G2"], "ACTVT": ["01", "02", "03"]}),
            ],
            org_levels=[OrgLevelDefinition("VKORG", ["1000", "2000"])],
            menu_nodes=["VF01", "VF02", "VF03"],
            last_changed_by="TRANSPORT",
            last_changed_at=ts,
        )

    # ------------------------------------------------------------------
    # 11. Z_MM_GOODS_RECEIPT — activity 06 (delete) removed in PROD
    # ------------------------------------------------------------------
    for sys_id, actvt, ts in [("DEV", ["01", "02", "06"], d), ("QA", ["01", "02", "06"], q), ("PROD", ["01", "02"], p)]:
        landscape.setdefault("Z_MM_GOODS_RECEIPT", {})[sys_id] = RoleSystemSnapshot(
            system_id=sys_id,
            role_name="Z_MM_GOODS_RECEIPT",
            description="Goods Receipt Processor",
            version="0014",
            profile_name="T-AG100011",
            auth_objects=[
                AuthObjectDefinition("M_MSEG_BWA", {"BWART": ["101", "102"], "ACTVT": actvt}),
            ],
            org_levels=[OrgLevelDefinition("WERKS", ["1000"])],
            menu_nodes=["MIGO"],
            last_changed_by="TRANSPORT",
            last_changed_at=ts,
        )

    # ------------------------------------------------------------------
    # 12. Z_BC_USER_ADMIN — missing from both QA and DEV (PROD-only emergency)
    # ------------------------------------------------------------------
    landscape.setdefault("Z_BC_USER_ADMIN", {})["PROD"] = RoleSystemSnapshot(
        system_id="PROD",
        role_name="Z_BC_USER_ADMIN",
        description="User Administration (Emergency)",
        version="0001",
        profile_name="T-AG100012",
        auth_objects=[
            AuthObjectDefinition("S_USR_ADM", {"USRACT_02": ["02", "03", "05"], "ACTVT": ["01", "02", "08"]}),
        ],
        org_levels=[],
        menu_nodes=["SU01", "SU10"],
        last_changed_by="BASIS_EMERGENCY",
        last_changed_at=p,
    )

    # ------------------------------------------------------------------
    # 13. Z_FI_BANK_MASTER — wildcard BUKRS in DEV, restricted in PROD
    # ------------------------------------------------------------------
    for sys_id, bukrs, ts in [("DEV", ["*"], d), ("QA", ["1000", "2000", "3000"], q), ("PROD", ["1000", "2000"], p)]:
        landscape.setdefault("Z_FI_BANK_MASTER", {})[sys_id] = RoleSystemSnapshot(
            system_id=sys_id,
            role_name="Z_FI_BANK_MASTER",
            description="Bank Master Data Maintainer",
            version="0033",
            profile_name="T-AG100013",
            auth_objects=[
                AuthObjectDefinition("F_BNKA_MAN", {"BUKRS": bukrs, "ACTVT": ["01", "02", "03"]}),
            ],
            org_levels=[OrgLevelDefinition("BUKRS", bukrs)],
            menu_nodes=["FI01", "FI02", "FI03"],
            last_changed_by="TRANSPORT",
            last_changed_at=ts,
        )

    # ------------------------------------------------------------------
    # 14. Z_HR_TIME_MGMT — composite role, child list differs
    # ------------------------------------------------------------------
    for sys_id, children, ts in [
        ("DEV", ["Z_HR_TIME_ENTRY", "Z_HR_TIME_APPROVE", "Z_HR_LEAVE_ADMIN"], d),
        ("QA",  ["Z_HR_TIME_ENTRY", "Z_HR_TIME_APPROVE"], q),
        ("PROD",["Z_HR_TIME_ENTRY", "Z_HR_TIME_APPROVE"], p),
    ]:
        landscape.setdefault("Z_HR_TIME_MGMT", {})[sys_id] = RoleSystemSnapshot(
            system_id=sys_id,
            role_name="Z_HR_TIME_MGMT",
            description="Time Management Composite",
            version="0005",
            profile_name="",
            auth_objects=[],
            org_levels=[],
            menu_nodes=[],
            last_changed_by="TRANSPORT",
            last_changed_at=ts,
            is_composite=True,
            child_roles=children,
        )

    # ------------------------------------------------------------------
    # 15. Z_QM_QUALITY_INSP — auth object added in QA for testing, not removed
    # ------------------------------------------------------------------
    for sys_id, extra, ts in [("DEV", False, d), ("QA", True, q), ("PROD", False, p)]:
        auth_objs = [AuthObjectDefinition("Q_QST00", {"QSYSTYP": ["R"], "ACTVT": ["01", "02", "03"]})]
        if extra:
            auth_objs.append(AuthObjectDefinition("Q_TCODE_ALL", {"TCD": ["*"]}, activity_codes=["01"]))
        landscape.setdefault("Z_QM_QUALITY_INSP", {})[sys_id] = RoleSystemSnapshot(
            system_id=sys_id,
            role_name="Z_QM_QUALITY_INSP",
            description="Quality Inspection Clerk",
            version="0017",
            profile_name="T-AG100015",
            auth_objects=auth_objs,
            org_levels=[OrgLevelDefinition("WERKS", ["1000"])],
            menu_nodes=["QA01", "QA02", "QA11"],
            last_changed_by="TRANSPORT",
            last_changed_at=ts,
        )

    # ------------------------------------------------------------------
    # 16-25. Additional roles with smaller drift scenarios
    # ------------------------------------------------------------------
    _add_additional_roles(landscape, now)

    return landscape


def _add_additional_roles(landscape: Dict, now: datetime) -> None:
    """Add roles 16-25 with assorted drift conditions."""

    d = now - timedelta(days=5)
    q = now - timedelta(days=3)
    p = now - timedelta(days=10)

    simple_aligned = [
        ("Z_FI_PAYMENT_RUN",    "Payment Run Processor",      "T-AG100016", ["F110", "FBZ2"]),
        ("Z_CO_PROFIT_CENTER",  "Profit Center Accountant",   "T-AG100017", ["KE51", "KE52"]),
        ("Z_SD_PRICING",        "Pricing Condition Maintainer","T-AG100018", ["VK11", "VK12"]),
        ("Z_MM_VENDOR_MASTER",  "Vendor Master Maintainer",   "T-AG100019", ["XK01", "XK02", "XK03"]),
        ("Z_HR_ORG_MGMT",       "Org Management Viewer",      "T-AG100020", ["PPOSE", "PPOMW"]),
    ]
    for role_name, desc, profile, menu in simple_aligned:
        for sys_id, ts in [("DEV", d), ("QA", q), ("PROD", p)]:
            landscape.setdefault(role_name, {})[sys_id] = RoleSystemSnapshot(
                system_id=sys_id, role_name=role_name, description=desc,
                version="0010", profile_name=profile,
                auth_objects=[AuthObjectDefinition("S_TCODE", {"TCD": menu})],
                org_levels=[], menu_nodes=menu,
                last_changed_by="TRANSPORT", last_changed_at=ts,
            )

    # Role 21 — version mismatch QA vs PROD
    for sys_id, ver, ts in [("DEV", "0020", d), ("QA", "0021", q), ("PROD", "0020", p)]:
        landscape.setdefault("Z_FI_TRAVEL_MGMT", {})[sys_id] = RoleSystemSnapshot(
            system_id=sys_id, role_name="Z_FI_TRAVEL_MGMT",
            description="Travel Expense Manager",
            version=ver, profile_name="T-AG100021",
            auth_objects=[AuthObjectDefinition("PR_PFACH", {"ACTVT": ["01", "02", "03"]})],
            org_levels=[], menu_nodes=["TRIP", "PR05"],
            last_changed_by="TRANSPORT", last_changed_at=ts,
        )

    # Role 22 — missing from DEV only
    for sys_id, ts in [("QA", q), ("PROD", p)]:
        landscape.setdefault("Z_LEGACY_INTERFACE", {})[sys_id] = RoleSystemSnapshot(
            system_id=sys_id, role_name="Z_LEGACY_INTERFACE",
            description="Legacy RFC Interface Role",
            version="0003", profile_name="T-AG100022",
            auth_objects=[AuthObjectDefinition("S_RFC", {"RFC_TYPE": ["FUGR"], "RFC_NAME": ["ZBAPI_*"], "ACTVT": ["16"]})],
            org_levels=[], menu_nodes=[],
            last_changed_by="TRANSPORT", last_changed_at=ts,
        )

    # Role 23 — auth activity broadened in QA (02 added)
    for sys_id, actvt, ts in [("DEV", ["03"], d), ("QA", ["02", "03"], q), ("PROD", ["03"], p)]:
        landscape.setdefault("Z_FI_REPORT_VIEWER", {})[sys_id] = RoleSystemSnapshot(
            system_id=sys_id, role_name="Z_FI_REPORT_VIEWER",
            description="Finance Report Viewer",
            version="0009", profile_name="T-AG100023",
            auth_objects=[AuthObjectDefinition("S_TABU_DIS", {"ACTVT": actvt, "DICBERCLS": ["FC"]})],
            org_levels=[], menu_nodes=["S_ALR_87012082", "S_ALR_87012083"],
            last_changed_by="TRANSPORT", last_changed_at=ts,
        )

    # Role 24 — description and version both differ
    for sys_id, desc, ver, ts in [
        ("DEV",  "WM Stock Controller",          "0011", d),
        ("QA",   "WM Stock Controller",          "0011", q),
        ("PROD", "WM Stock Controller (Audited)", "0012", p),
    ]:
        landscape.setdefault("Z_WM_STOCK_CTRL", {})[sys_id] = RoleSystemSnapshot(
            system_id=sys_id, role_name="Z_WM_STOCK_CTRL",
            description=desc, version=ver, profile_name="T-AG100024",
            auth_objects=[AuthObjectDefinition("L_TAGT_ALL", {"LGNUM": ["001"], "ACTVT": ["01", "02", "03"]})],
            org_levels=[OrgLevelDefinition("LGNUM", ["001"])],
            menu_nodes=["LT01", "LT0A", "LI01"],
            last_changed_by="TRANSPORT", last_changed_at=ts,
        )

    # Role 25 — fully aligned, serves as a clean control case
    for sys_id, ts in [("DEV", d), ("QA", q), ("PROD", p)]:
        landscape.setdefault("Z_BC_READ_ONLY", {})[sys_id] = RoleSystemSnapshot(
            system_id=sys_id, role_name="Z_BC_READ_ONLY",
            description="Basis Read Only",
            version="0004", profile_name="T-AG100025",
            auth_objects=[AuthObjectDefinition("S_TCODE", {"TCD": ["SM50", "SM66", "ST05"]})],
            org_levels=[], menu_nodes=["SM50", "SM66", "ST05"],
            last_changed_by="TRANSPORT", last_changed_at=ts,
        )


# ---------------------------------------------------------------------------
# Hash computation
# ---------------------------------------------------------------------------

def _compute_drift_hash(snapshot: RoleSystemSnapshot) -> str:
    """
    Compute a deterministic SHA-256 hash over the canonical role definition.

    Fields included: auth_objects (sorted), org_levels (sorted), menu_nodes
    (sorted), version, profile_name.  Description is intentionally excluded
    from the structural hash but compared separately as a LOW-severity drift.
    """
    canonical: Dict = {
        "version": snapshot.version,
        "profile_name": snapshot.profile_name,
        "is_composite": snapshot.is_composite,
        "child_roles": sorted(snapshot.child_roles),
        "auth_objects": sorted(
            [
                {
                    "object_name": ao.object_name,
                    "fields": {k: sorted(v) for k, v in sorted(ao.fields.items())},
                    "activity_codes": sorted(ao.activity_codes),
                }
                for ao in snapshot.auth_objects
            ],
            key=lambda x: x["object_name"],
        ),
        "org_levels": sorted(
            [{"field_name": ol.field_name, "values": sorted(ol.values)} for ol in snapshot.org_levels],
            key=lambda x: x["field_name"],
        ),
        "menu_nodes": sorted(snapshot.menu_nodes),
    }
    payload = json.dumps(canonical, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Finding generators
# ---------------------------------------------------------------------------

def _finding_id(role: str, idx: int) -> str:
    return f"DRIFT-{role[:8].upper().replace('_','')}-{idx:04d}"


def _compare_snapshots(
    role_name: str,
    snap_a: RoleSystemSnapshot,
    snap_b: RoleSystemSnapshot,
    finding_offset: int = 0,
) -> List[DriftFinding]:
    """Compare two system snapshots and return all findings."""

    findings: List[DriftFinding] = []
    idx = finding_offset

    def add(dtype: DriftType, sev: DriftSeverity, path: str, va: str, vb: str, desc: str, rem: str) -> None:
        nonlocal idx
        findings.append(DriftFinding(
            finding_id=_finding_id(role_name, idx),
            drift_type=dtype,
            severity=sev,
            system_a=snap_a.system_id,
            system_b=snap_b.system_id,
            field_path=path,
            value_in_a=va,
            value_in_b=vb,
            description=desc,
            remediation=rem,
        ))
        idx += 1

    # Version
    if snap_a.version != snap_b.version:
        add(
            DriftType.VERSION_MISMATCH, DriftSeverity.MEDIUM,
            "version", snap_a.version, snap_b.version,
            f"Version counter differs: {snap_a.system_id}={snap_a.version}, {snap_b.system_id}={snap_b.version}.",
            f"Move outstanding transports from {snap_a.system_id} to {snap_b.system_id} or verify transport log.",
        )

    # Profile name
    if snap_a.profile_name != snap_b.profile_name:
        add(
            DriftType.PROFILE_MISMATCH, DriftSeverity.HIGH,
            "profile_name", snap_a.profile_name, snap_b.profile_name,
            f"Generated profile name differs between {snap_a.system_id} and {snap_b.system_id}.",
            "Regenerate profile in the system with the non-standard name and re-transport.",
        )

    # Description
    if snap_a.description != snap_b.description:
        add(
            DriftType.DESCRIPTION_CHANGED, DriftSeverity.LOW,
            "description", snap_a.description, snap_b.description,
            f"Role description differs between {snap_a.system_id} and {snap_b.system_id}.",
            "Align role description via transport and review change history.",
        )

    # Child roles (composites)
    if snap_a.is_composite or snap_b.is_composite:
        set_a = set(snap_a.child_roles)
        set_b = set(snap_b.child_roles)
        for cr in sorted(set_a - set_b):
            add(DriftType.AUTH_OBJECT_ADDED, DriftSeverity.HIGH,
                f"child_roles[{cr}]", cr, "(absent)",
                f"Child role {cr} present in {snap_a.system_id} but missing from {snap_b.system_id}.",
                f"Transport child role {cr} to {snap_b.system_id} or remove from composite in {snap_a.system_id}.")
        for cr in sorted(set_b - set_a):
            add(DriftType.AUTH_OBJECT_REMOVED, DriftSeverity.HIGH,
                f"child_roles[{cr}]", "(absent)", cr,
                f"Child role {cr} present in {snap_b.system_id} but missing from {snap_a.system_id}.",
                f"Transport child role {cr} to {snap_a.system_id} or remove from composite in {snap_b.system_id}.")
        return findings  # Skip auth object comparison for composites

    # Auth objects
    objs_a: Dict[str, AuthObjectDefinition] = {ao.object_name: ao for ao in snap_a.auth_objects}
    objs_b: Dict[str, AuthObjectDefinition] = {ao.object_name: ao for ao in snap_b.auth_objects}

    for obj_name in sorted(set(objs_a) - set(objs_b)):
        sev = DriftSeverity.CRITICAL if "ADM" in obj_name or "USR" in obj_name else DriftSeverity.HIGH
        add(DriftType.AUTH_OBJECT_ADDED, sev,
            f"auth_objects[{obj_name}]", obj_name, "(absent)",
            f"Auth object {obj_name} present in {snap_a.system_id} but missing from {snap_b.system_id}.",
            f"Review whether {obj_name} is intentionally absent from {snap_b.system_id}. Transport if required.")

    for obj_name in sorted(set(objs_b) - set(objs_a)):
        sev = DriftSeverity.CRITICAL if "ADM" in obj_name or "USR" in obj_name else DriftSeverity.HIGH
        add(DriftType.AUTH_OBJECT_REMOVED, sev,
            f"auth_objects[{obj_name}]", "(absent)", obj_name,
            f"Auth object {obj_name} present in {snap_b.system_id} but missing from {snap_a.system_id}.",
            f"Review whether {obj_name} should be added to {snap_a.system_id}. Transport if required.")

    for obj_name in sorted(set(objs_a) & set(objs_b)):
        ao_a = objs_a[obj_name]
        ao_b = objs_b[obj_name]
        all_fields = set(ao_a.fields) | set(ao_b.fields)
        for field_name in sorted(all_fields):
            vals_a = set(ao_a.fields.get(field_name, []))
            vals_b = set(ao_b.fields.get(field_name, []))
            if vals_a == vals_b:
                continue
            extra_in_a = vals_a - vals_b
            extra_in_b = vals_b - vals_a
            if extra_in_a:
                # Wildcard is always CRITICAL
                sev = DriftSeverity.CRITICAL if "*" in extra_in_a else DriftSeverity.HIGH
                add(DriftType.EXTRA_AUTH_VALUE, sev,
                    f"auth_objects[{obj_name}].{field_name}",
                    str(sorted(extra_in_a)), "(absent)",
                    f"Field {field_name} of {obj_name} has extra values in {snap_a.system_id}: {sorted(extra_in_a)}.",
                    f"Remove or restrict the extra values in {snap_a.system_id} to match {snap_b.system_id}.")
            if extra_in_b:
                sev = DriftSeverity.CRITICAL if "*" in extra_in_b else DriftSeverity.HIGH
                add(DriftType.REMOVED_AUTH_VALUE, sev,
                    f"auth_objects[{obj_name}].{field_name}",
                    "(absent)", str(sorted(extra_in_b)),
                    f"Field {field_name} of {obj_name} has extra values in {snap_b.system_id}: {sorted(extra_in_b)}.",
                    f"Remove or restrict the extra values in {snap_b.system_id} to match {snap_a.system_id}.")

    # Org levels
    org_a: Dict[str, OrgLevelDefinition] = {ol.field_name: ol for ol in snap_a.org_levels}
    org_b: Dict[str, OrgLevelDefinition] = {ol.field_name: ol for ol in snap_b.org_levels}
    all_org_fields = set(org_a) | set(org_b)
    for field_name in sorted(all_org_fields):
        if field_name not in org_a:
            add(DriftType.ORG_LEVEL_MISMATCH, DriftSeverity.HIGH,
                f"org_levels[{field_name}]", "(absent)", str(sorted(org_b[field_name].values)),
                f"Org-level field {field_name} missing from {snap_a.system_id}.",
                f"Add org-level {field_name} to the role in {snap_a.system_id} via profile maintenance.")
        elif field_name not in org_b:
            add(DriftType.ORG_LEVEL_MISMATCH, DriftSeverity.HIGH,
                f"org_levels[{field_name}]", str(sorted(org_a[field_name].values)), "(absent)",
                f"Org-level field {field_name} missing from {snap_b.system_id}.",
                f"Add org-level {field_name} to the role in {snap_b.system_id} via profile maintenance.")
        else:
            va = sorted(org_a[field_name].values)
            vb = sorted(org_b[field_name].values)
            if va != vb:
                add(DriftType.ORG_LEVEL_MISMATCH, DriftSeverity.MEDIUM,
                    f"org_levels[{field_name}]", str(va), str(vb),
                    f"Org-level {field_name} values differ: {snap_a.system_id}={va}, {snap_b.system_id}={vb}.",
                    "Align org-level values across systems and transport the corrected role.")

    # Menu
    menu_a = set(snap_a.menu_nodes)
    menu_b = set(snap_b.menu_nodes)
    extra_menu_a = menu_a - menu_b
    extra_menu_b = menu_b - menu_a
    if extra_menu_a:
        add(DriftType.MENU_CHANGED, DriftSeverity.LOW,
            "menu_nodes", str(sorted(extra_menu_a)), "(absent)",
            f"Menu nodes {sorted(extra_menu_a)} present in {snap_a.system_id} but not {snap_b.system_id}.",
            "Transport the role menu from the reference system.")
    if extra_menu_b:
        add(DriftType.MENU_CHANGED, DriftSeverity.LOW,
            "menu_nodes", "(absent)", str(sorted(extra_menu_b)),
            f"Menu nodes {sorted(extra_menu_b)} present in {snap_b.system_id} but not {snap_a.system_id}.",
            "Transport the role menu from the reference system.")

    return findings


def _overall_severity(findings: List[DriftFinding]) -> DriftSeverity:
    """Derive the worst-case severity from the finding list."""
    if not findings:
        return DriftSeverity.INFO
    order = [DriftSeverity.CRITICAL, DriftSeverity.HIGH, DriftSeverity.MEDIUM, DriftSeverity.LOW, DriftSeverity.INFO]
    for sev in order:
        if any(f.severity == sev for f in findings):
            return sev
    return DriftSeverity.INFO


# ---------------------------------------------------------------------------
# DriftDetector — public engine
# ---------------------------------------------------------------------------


class DriftDetector:
    """
    Main drift detection engine.

    Landscape data is loaded from the ``drift_snapshots`` database table on
    first use.  If the table is empty the engine seeds it with the 25-role
    hardcoded snapshot so that the application works out-of-the-box.

    Usage::

        detector = DriftDetector()
        report   = detector.detect_drift("Z_FI_AP_CLERK")
        summary  = detector.get_drift_summary()
        all_rpts = detector.scan_all_drift()
    """

    SYSTEMS = ["DEV", "QA", "PROD"]
    REFERENCE_SYSTEM = "PROD"

    def __init__(self, tenant_id: str = "tenant_default") -> None:
        self._tenant_id = tenant_id
        self._landscape: Optional[Dict[str, Dict[str, RoleSystemSnapshot]]] = None

    # ------------------------------------------------------------------
    # DB helpers
    # ------------------------------------------------------------------

    def _ensure_loaded(self) -> None:
        """
        Guarantee ``self._landscape`` is populated.

        1. Open a DB session and query ``drift_snapshots`` for this tenant.
        2. If the table is empty, insert the full seed landscape and reload.
        3. Reconstruct the in-memory landscape dict from DB rows.
        """
        if self._landscape is not None:
            return

        if not db_manager._initialized:
            db_manager.init()

        with db_manager.session_scope() as session:
            rows = (
                session.query(DriftSnapshot)
                .filter(DriftSnapshot.tenant_id == self._tenant_id)
                .all()
            )

            if not rows:
                # Seed the DB with the hardcoded snapshot data
                rows = self._seed_db(session)

            # Build landscape from DB rows
            landscape: Dict[str, Dict[str, RoleSystemSnapshot]] = {}
            for row in rows:
                snap = _db_row_to_snapshot(row)
                landscape.setdefault(row.role_name, {})[row.system] = snap

        self._landscape = landscape

    def _seed_db(self, session) -> List[DriftSnapshot]:
        """
        Insert the full 25-role hardcoded landscape into the DB and return
        the newly created rows.

        Called inside an existing ``session_scope`` transaction — the caller
        commits on exit.
        """
        seed = _build_seed_landscape()
        new_rows: List[DriftSnapshot] = []

        for role_name, systems in seed.items():
            for system_id, snap in systems.items():
                db_fields = _snapshot_to_db_fields(snap)
                snapshot_hash = _compute_drift_hash(snap)
                snapshot_id = f"{self._tenant_id}_{role_name}_{system_id}"

                row = DriftSnapshot(
                    tenant_id=self._tenant_id,
                    snapshot_id=snapshot_id,
                    role_name=role_name,
                    system=system_id,
                    snapshot_hash=snapshot_hash,
                    transactions=db_fields["transactions"],
                    auth_objects=db_fields["auth_objects"],
                    org_levels=db_fields["org_levels"],
                    menu_nodes=db_fields["menu_nodes"],
                    captured_at=snap.last_changed_at or datetime.utcnow(),
                )
                session.add(row)
                new_rows.append(row)

        session.flush()  # Assign IDs without closing the transaction
        logger.info(
            "drift_snapshots_seeded",
            extra={"tenant_id": self._tenant_id, "row_count": len(new_rows)},
        )
        return new_rows

    def _invalidate_cache(self) -> None:
        """Force a reload from the DB on the next access."""
        self._landscape = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def detect_drift(self, role_id: str) -> DriftReport:
        """
        Analyse drift for a single role across all configured systems.

        Parameters
        ----------
        role_id:
            The role name, e.g. ``"Z_FI_AP_CLERK"``.

        Returns
        -------
        DriftReport
            Structured drift report including per-finding breakdowns.
        """
        self._ensure_loaded()
        role_name = role_id.upper()
        role_snapshots = self._landscape.get(role_name, {})

        if not role_snapshots:
            raise ValueError(f"Role '{role_name}' not found in landscape.  Available roles: {self.list_roles()}")

        scan_ts = datetime.utcnow()
        systems_present = [s for s in self.SYSTEMS if s in role_snapshots]
        systems_missing = [s for s in self.SYSTEMS if s not in role_snapshots]

        # Compute hashes
        drift_hash: Dict[str, str] = {
            sys_id: _compute_drift_hash(snap)
            for sys_id, snap in role_snapshots.items()
        }

        # Collect findings for all system pairs
        findings: List[DriftFinding] = []
        offset = 0
        pairs: List[Tuple[str, str]] = []
        for i, sys_a in enumerate(systems_present):
            for sys_b in systems_present[i + 1:]:
                pairs.append((sys_a, sys_b))

        for sys_a, sys_b in pairs:
            new_findings = _compare_snapshots(
                role_name,
                role_snapshots[sys_a],
                role_snapshots[sys_b],
                finding_offset=offset,
            )
            findings.extend(new_findings)
            offset += len(new_findings)

        # Missing-system findings
        for missing_sys in systems_missing:
            for present_sys in systems_present:
                findings.append(DriftFinding(
                    finding_id=_finding_id(role_name, offset),
                    drift_type=DriftType.MISSING_IN_SYSTEM,
                    severity=DriftSeverity.CRITICAL if missing_sys == "PROD" else DriftSeverity.HIGH,
                    system_a=present_sys,
                    system_b=missing_sys,
                    field_path="role",
                    value_in_a=role_name,
                    value_in_b="(not found)",
                    description=f"Role {role_name} is present in {present_sys} but absent from {missing_sys}.",
                    remediation=(
                        f"Transport role {role_name} from {present_sys} to {missing_sys}.  "
                        "Verify transport request and obtain appropriate approval before moving to PROD."
                    ),
                ))
                offset += 1

        role_description = next(iter(role_snapshots.values())).description
        overall_sev = _overall_severity(findings)
        unique_hashes = set(drift_hash.values())

        return DriftReport(
            role_name=role_name,
            role_description=role_description,
            scan_timestamp=scan_ts,
            systems_present=systems_present,
            systems_missing=systems_missing,
            drift_hash=drift_hash,
            is_drifted=len(unique_hashes) > 1 or bool(systems_missing),
            overall_severity=overall_sev,
            findings=findings,
        )

    def scan_all_drift(self) -> List[DriftReport]:
        """
        Run drift detection across the entire role estate.

        Returns
        -------
        List[DriftReport]
            One report per role, sorted by overall severity (critical first)
            then by finding count descending.
        """
        self._ensure_loaded()
        reports: List[DriftReport] = []
        for role_name in sorted(self._landscape.keys()):
            try:
                reports.append(self.detect_drift(role_name))
            except Exception as exc:  # pragma: no cover
                logger.warning("drift_scan_error", extra={"role": role_name, "error": str(exc)})

        severity_order = {
            DriftSeverity.CRITICAL: 0,
            DriftSeverity.HIGH: 1,
            DriftSeverity.MEDIUM: 2,
            DriftSeverity.LOW: 3,
            DriftSeverity.INFO: 4,
        }
        reports.sort(key=lambda r: (severity_order[r.overall_severity], -r.finding_count))
        return reports

    def get_drift_summary(self) -> DriftSummary:
        """
        Return aggregated statistics across the full role estate.

        Returns
        -------
        DriftSummary
            Counts by severity and drift type, plus top drifted roles.
        """
        reports = self.scan_all_drift()

        by_severity: Dict[str, int] = {sev.value: 0 for sev in DriftSeverity}
        by_drift_type: Dict[str, int] = {dt.value: 0 for dt in DriftType}
        finding_counts: List[Tuple[str, int]] = []

        for report in reports:
            by_severity[report.overall_severity.value] += 1
            for finding in report.findings:
                by_drift_type[finding.drift_type.value] += 1
            finding_counts.append((report.role_name, report.finding_count))

        finding_counts.sort(key=lambda x: -x[1])
        most_drifted = [role for role, _ in finding_counts[:10] if _ > 0]

        roles_drifted = sum(1 for r in reports if r.is_drifted)

        return DriftSummary(
            scan_timestamp=datetime.utcnow(),
            total_roles_scanned=len(reports),
            roles_in_sync=len(reports) - roles_drifted,
            roles_drifted=roles_drifted,
            by_severity=by_severity,
            by_drift_type=by_drift_type,
            most_drifted_roles=most_drifted,
            systems_compared=self.SYSTEMS,
            drift_percentage=round(roles_drifted / len(reports) * 100, 1) if reports else 0.0,
        )

    def get_systems(self) -> List[str]:
        """Return the list of systems being compared."""
        return list(self.SYSTEMS)

    def list_roles(self) -> List[str]:
        """Return all role names present in the landscape."""
        self._ensure_loaded()
        return sorted(self._landscape.keys())

    def compare_systems(self, system_a: str, system_b: str) -> List[DriftReport]:
        """
        Compare two specific systems across all roles that exist in both.

        Parameters
        ----------
        system_a, system_b:
            System identifiers, e.g. ``"DEV"`` and ``"PROD"``.

        Returns
        -------
        List[DriftReport]
            Reports restricted to findings between the two named systems.
        """
        self._ensure_loaded()
        system_a = system_a.upper()
        system_b = system_b.upper()
        if system_a not in self.SYSTEMS or system_b not in self.SYSTEMS:
            raise ValueError(
                f"Invalid system identifiers.  Allowed values: {self.SYSTEMS}"
            )

        results: List[DriftReport] = []
        for role_name in sorted(self._landscape.keys()):
            role_snapshots = self._landscape[role_name]
            if system_a not in role_snapshots and system_b not in role_snapshots:
                continue

            systems_present = [s for s in [system_a, system_b] if s in role_snapshots]
            systems_missing = [s for s in [system_a, system_b] if s not in role_snapshots]
            findings: List[DriftFinding] = []

            if system_a in role_snapshots and system_b in role_snapshots:
                findings = _compare_snapshots(
                    role_name, role_snapshots[system_a], role_snapshots[system_b]
                )

            for missing_sys in systems_missing:
                present_sys = systems_present[0] if systems_present else "unknown"
                findings.append(DriftFinding(
                    finding_id=_finding_id(role_name, len(findings)),
                    drift_type=DriftType.MISSING_IN_SYSTEM,
                    severity=DriftSeverity.CRITICAL if missing_sys == "PROD" else DriftSeverity.HIGH,
                    system_a=present_sys,
                    system_b=missing_sys,
                    field_path="role",
                    value_in_a=role_name,
                    value_in_b="(not found)",
                    description=f"Role {role_name} absent from {missing_sys}.",
                    remediation=f"Transport role {role_name} from {present_sys} to {missing_sys}.",
                ))

            drift_hash = {
                s: _compute_drift_hash(role_snapshots[s])
                for s in systems_present
            }
            role_description = next(iter(role_snapshots.values())).description
            results.append(DriftReport(
                role_name=role_name,
                role_description=role_description,
                scan_timestamp=datetime.utcnow(),
                systems_present=systems_present,
                systems_missing=systems_missing,
                drift_hash=drift_hash,
                is_drifted=bool(findings),
                overall_severity=_overall_severity(findings),
                findings=findings,
            ))

        results.sort(key=lambda r: -r.finding_count)
        return results
