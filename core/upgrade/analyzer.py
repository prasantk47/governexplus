"""
Upgrade Impact Analyzer

Assesses the security impact of SAP version upgrades, covering:
- ECC 6.0 EHP7/EHP8 to S/4HANA 1909 / 2020 / 2021 / 2022 / 2023
- Deprecated authorization objects and transactions
- New authorization requirements introduced per release
- Simplification items affecting security roles
- Fiori authorization requirements replacing GUI transactions
- Affected roles and recommended remediation plan
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum
from datetime import datetime


# ===========================================================================
# Enumerations
# ===========================================================================

class ImpactSeverity(Enum):
    """Severity of an upgrade impact item."""
    CRITICAL = "critical"   # Role will break or major security gap
    HIGH = "high"           # Significant rework required
    MEDIUM = "medium"       # Adjustment required but manageable
    LOW = "low"             # Minor cleanup recommended
    INFO = "info"           # Informational only


class ChangeType(Enum):
    """Type of security change introduced by an upgrade."""
    DEPRECATED_OBJECT = "deprecated_object"
    DEPRECATED_TRANSACTION = "deprecated_transaction"
    NEW_OBJECT = "new_object"
    NEW_TRANSACTION = "new_transaction"
    CHANGED_BEHAVIOR = "changed_behavior"
    SIMPLIFICATION = "simplification"
    FIORI_REQUIREMENT = "fiori_requirement"
    RENAMED_OBJECT = "renamed_object"


class RemediationAction(Enum):
    """Type of remediation action required."""
    REMOVE = "remove"
    ADD = "add"
    REPLACE = "replace"
    REVIEW = "review"
    TEST = "test"


# ===========================================================================
# Data classes
# ===========================================================================

@dataclass
class DeprecatedObject:
    """An authorization object or transaction deprecated in a given version."""
    object_name: str
    object_type: str        # "auth_object", "transaction", "report"
    deprecated_in: str      # version string, e.g. "S/4HANA 1909"
    removed_in: Optional[str]   # version where it was fully removed
    replacement: Optional[str]  # replacement object/transaction if any
    impact: ImpactSeverity
    change_type: ChangeType
    description: str
    affected_business_areas: List[str] = field(default_factory=list)


@dataclass
class NewRequirement:
    """A new authorization object or requirement introduced in a version."""
    object_name: str
    object_type: str
    introduced_in: str
    mandatory: bool
    description: str
    example_value: str
    related_fiori_apps: List[str] = field(default_factory=list)
    affected_business_areas: List[str] = field(default_factory=list)
    impact: ImpactSeverity = ImpactSeverity.MEDIUM


@dataclass
class SimplificationItem:
    """SAP Simplification Item affecting security roles."""
    item_id: str
    title: str
    description: str
    affected_version: str
    change_type: ChangeType
    impact: ImpactSeverity
    action_required: str
    affected_objects: List[str] = field(default_factory=list)


@dataclass
class AffectedRole:
    """A business role expected to be impacted by an upgrade."""
    role_id: str
    role_name: str
    role_type: str          # "single", "composite", "reference"
    business_area: str
    deprecated_objects_count: int
    new_objects_count: int
    simplification_items_count: int
    overall_impact: ImpactSeverity
    requires_redesign: bool
    notes: str


@dataclass
class UpgradeImpact:
    """Full impact analysis for an upgrade path."""
    from_version: str
    to_version: str
    analysis_timestamp: str
    total_deprecated_objects: int
    total_new_requirements: int
    total_simplification_items: int
    total_affected_roles: int
    critical_items: int
    deprecated_objects: List[DeprecatedObject]
    new_requirements: List[NewRequirement]
    simplification_items: List[SimplificationItem]
    affected_roles: List[AffectedRole]
    executive_summary: str
    estimated_remediation_effort: str


@dataclass
class RoleSimulationResult:
    """Result of simulating an upgrade for a specific role."""
    role_id: str
    role_name: str
    current_objects: List[str]
    deprecated_in_role: List[str]
    new_required: List[str]
    net_change: int         # new_required - deprecated
    impact: ImpactSeverity
    action_items: List[str]


@dataclass
class UpgradeSimulation:
    """Simulation of upgrade impact across selected roles."""
    from_version: str
    to_version: str
    simulation_timestamp: str
    role_results: List[RoleSimulationResult]
    total_deprecated: int
    total_new: int
    roles_requiring_redesign: int
    estimated_effort_hours: float


@dataclass
class RemediationTask:
    """A single remediation task in the upgrade plan."""
    task_id: str
    title: str
    description: str
    action: RemediationAction
    priority: ImpactSeverity
    estimated_hours: float
    affected_roles: List[str]
    objects_involved: List[str]
    prerequisite_tasks: List[str] = field(default_factory=list)


@dataclass
class RemediationPlan:
    """Full remediation plan for an upgrade."""
    from_version: str
    to_version: str
    generated_at: str
    total_tasks: int
    total_estimated_hours: float
    phases: Dict[str, List[RemediationTask]]
    critical_path: List[str]    # task IDs on critical path
    notes: List[str]


# ===========================================================================
# Version knowledge base
# ===========================================================================

SUPPORTED_VERSION_PAIRS: List[Dict[str, str]] = [
    {"from": "ECC 6.0 EHP7", "to": "S/4HANA 1909",
     "type": "Greenfield/Brownfield", "notes": "First mainstream S/4HANA release"},
    {"from": "ECC 6.0 EHP7", "to": "S/4HANA 2020",
     "type": "Greenfield/Brownfield", "notes": "Enhanced Universal Journal"},
    {"from": "ECC 6.0 EHP7", "to": "S/4HANA 2021",
     "type": "Greenfield/Brownfield", "notes": "Embedded analytics enhancements"},
    {"from": "ECC 6.0 EHP7", "to": "S/4HANA 2022",
     "type": "Greenfield/Brownfield", "notes": "Procurement/logistics simplification"},
    {"from": "ECC 6.0 EHP7", "to": "S/4HANA 2023",
     "type": "Greenfield/Brownfield", "notes": "Latest release with GROW offering"},
    {"from": "ECC 6.0 EHP8", "to": "S/4HANA 1909",
     "type": "System Conversion", "notes": "Direct conversion path from EHP8"},
    {"from": "ECC 6.0 EHP8", "to": "S/4HANA 2020",
     "type": "System Conversion", "notes": "Most common conversion path"},
    {"from": "ECC 6.0 EHP8", "to": "S/4HANA 2021",
     "type": "System Conversion", "notes": "Recommended for new projects"},
    {"from": "ECC 6.0 EHP8", "to": "S/4HANA 2022",
     "type": "System Conversion", "notes": "Includes HANA 2.0 SPS 06+"},
    {"from": "ECC 6.0 EHP8", "to": "S/4HANA 2023",
     "type": "System Conversion", "notes": "Latest with AI-embedded features"},
    {"from": "S/4HANA 1909", "to": "S/4HANA 2020",
     "type": "Release Upgrade", "notes": "SPS-based upgrade path"},
    {"from": "S/4HANA 1909", "to": "S/4HANA 2021",
     "type": "Release Upgrade", "notes": "Skip upgrade supported"},
    {"from": "S/4HANA 1909", "to": "S/4HANA 2022",
     "type": "Release Upgrade", "notes": "Multiple SPS delta"},
    {"from": "S/4HANA 2020", "to": "S/4HANA 2021",
     "type": "Release Upgrade", "notes": "Annual release cycle"},
    {"from": "S/4HANA 2020", "to": "S/4HANA 2022",
     "type": "Release Upgrade", "notes": "Annual release skip"},
    {"from": "S/4HANA 2021", "to": "S/4HANA 2022",
     "type": "Release Upgrade", "notes": "Annual release cycle"},
    {"from": "S/4HANA 2021", "to": "S/4HANA 2023",
     "type": "Release Upgrade", "notes": "Two-year skip upgrade"},
    {"from": "S/4HANA 2022", "to": "S/4HANA 2023",
     "type": "Release Upgrade", "notes": "Annual release cycle"},
]


# ---------------------------------------------------------------------------
# Deprecated objects knowledge base
# ---------------------------------------------------------------------------

_DEPRECATED_OBJECTS: List[DeprecatedObject] = [
    DeprecatedObject(
        object_name="F_BKPF_GSB",
        object_type="auth_object",
        deprecated_in="S/4HANA 1909",
        removed_in="S/4HANA 2020",
        replacement="F_BKPF_BUK (extended)",
        impact=ImpactSeverity.HIGH,
        change_type=ChangeType.DEPRECATED_OBJECT,
        description=(
            "Business Area authorization (F_BKPF_GSB) is deprecated with the "
            "Universal Journal. Segment reporting replaces business area logic."
        ),
        affected_business_areas=["Finance", "Controlling"],
    ),
    DeprecatedObject(
        object_name="FBL1N (old Dynpro)",
        object_type="transaction",
        deprecated_in="S/4HANA 1909",
        removed_in=None,
        replacement="Manage Supplier Line Items (Fiori F3786)",
        impact=ImpactSeverity.MEDIUM,
        change_type=ChangeType.DEPRECATED_TRANSACTION,
        description=(
            "Classic FBL1N Dynpro transaction is deprecated in favor of the "
            "Fiori app. The ABAP transaction still exists but SAP recommends migration."
        ),
        affected_business_areas=["Finance"],
    ),
    DeprecatedObject(
        object_name="MR21 / MR22",
        object_type="transaction",
        deprecated_in="S/4HANA 2020",
        removed_in="S/4HANA 2023",
        replacement="Manage Material Price (Fiori F4471)",
        impact=ImpactSeverity.HIGH,
        change_type=ChangeType.DEPRECATED_TRANSACTION,
        description=(
            "Material price change transactions MR21/MR22 replaced by the "
            "Material Ledger-based price change in S/4HANA. Authorization "
            "objects for valuation area change."
        ),
        affected_business_areas=["Materials Management", "Finance"],
    ),
    DeprecatedObject(
        object_name="S_TCODE (blanket)",
        object_type="auth_object",
        deprecated_in="S/4HANA 1909",
        removed_in=None,
        replacement="Fiori catalog-based access control",
        impact=ImpactSeverity.CRITICAL,
        change_type=ChangeType.CHANGED_BEHAVIOR,
        description=(
            "S_TCODE-based authorization is deprecated for Fiori app access. "
            "Tile visibility is now controlled by catalog/page/space assignment "
            "rather than S_TCODE. Existing roles with S_TCODE only will fail "
            "to display tiles correctly."
        ),
        affected_business_areas=["All"],
    ),
    DeprecatedObject(
        object_name="PA_RPTIME",
        object_type="auth_object",
        deprecated_in="S/4HANA 2020",
        removed_in="S/4HANA 2022",
        replacement="HR_PT_WRK (new time management object)",
        impact=ImpactSeverity.HIGH,
        change_type=ChangeType.DEPRECATED_OBJECT,
        description=(
            "Legacy time management authorization object PA_RPTIME is replaced "
            "by the new HR time management framework in S/4HANA."
        ),
        affected_business_areas=["Human Resources"],
    ),
    DeprecatedObject(
        object_name="IS-H authorization objects (N_)",
        object_type="auth_object",
        deprecated_in="S/4HANA 1909",
        removed_in=None,
        replacement="S/4HANA for Healthcare objects",
        impact=ImpactSeverity.MEDIUM,
        change_type=ChangeType.DEPRECATED_OBJECT,
        description=(
            "IS-H (Healthcare) legacy authorization objects prefixed N_ are "
            "replaced by S/4HANA Healthcare module objects."
        ),
        affected_business_areas=["Healthcare"],
    ),
    DeprecatedObject(
        object_name="MM60 / ME2M (old reports)",
        object_type="transaction",
        deprecated_in="S/4HANA 2021",
        removed_in=None,
        replacement="Analytical apps via Embedded Analytics",
        impact=ImpactSeverity.LOW,
        change_type=ChangeType.DEPRECATED_TRANSACTION,
        description=(
            "Classic purchasing analysis reports MM60 and ME2M are superseded "
            "by Embedded Analytics purchasing overview apps."
        ),
        affected_business_areas=["Materials Management"],
    ),
    DeprecatedObject(
        object_name="FI_TCODES (F-01 to F-99 classic postings)",
        object_type="transaction",
        deprecated_in="S/4HANA 2020",
        removed_in=None,
        replacement="SAP Fiori apps (F0859, F1861, F3789)",
        impact=ImpactSeverity.MEDIUM,
        change_type=ChangeType.DEPRECATED_TRANSACTION,
        description=(
            "Classic F- series FI posting transactions (F-01, F-02, F-28, "
            "F-32, F-53) are deprecated in favor of Fiori posting apps."
        ),
        affected_business_areas=["Finance"],
    ),
    DeprecatedObject(
        object_name="CO_TCODE_KE* (EC-PCA classic)",
        object_type="transaction",
        deprecated_in="S/4HANA 1909",
        removed_in="S/4HANA 2022",
        replacement="Universal Journal profit center reporting",
        impact=ImpactSeverity.HIGH,
        change_type=ChangeType.SIMPLIFICATION,
        description=(
            "EC-PCA (classic Profit Center Accounting) is removed in S/4HANA. "
            "Profit center reporting now uses the Universal Journal (ACDOCA). "
            "Roles with KE* transactions must be redesigned."
        ),
        affected_business_areas=["Finance", "Controlling"],
    ),
    DeprecatedObject(
        object_name="RMAC_AUSP (batch classification in MM)",
        object_type="auth_object",
        deprecated_in="S/4HANA 2021",
        removed_in=None,
        replacement="CT_CLSFD (cross-application classification)",
        impact=ImpactSeverity.LOW,
        change_type=ChangeType.RENAMED_OBJECT,
        description=(
            "MM-specific batch classification authorization is consolidated "
            "into the cross-application classification object CT_CLSFD."
        ),
        affected_business_areas=["Materials Management"],
    ),
    DeprecatedObject(
        object_name="R_WLBSTNR (SD old route auth)",
        object_type="auth_object",
        deprecated_in="S/4HANA 1909",
        removed_in="S/4HANA 2021",
        replacement="WM/EWM authorization objects",
        impact=ImpactSeverity.MEDIUM,
        change_type=ChangeType.DEPRECATED_OBJECT,
        description=(
            "Legacy SD transportation routing authorization object replaced "
            "by EWM/WM transportation management objects."
        ),
        affected_business_areas=["Sales", "Logistics"],
    ),
    DeprecatedObject(
        object_name="SU01D (Display User — old Dynpro)",
        object_type="transaction",
        deprecated_in="S/4HANA 2022",
        removed_in=None,
        replacement="Manage Users (Fiori F0998)",
        impact=ImpactSeverity.LOW,
        change_type=ChangeType.DEPRECATED_TRANSACTION,
        description=(
            "SU01D display-only transaction is deprecated in favor of the "
            "Fiori user management app which provides display and change capability."
        ),
        affected_business_areas=["Basis"],
    ),
    DeprecatedObject(
        object_name="CK11N / CK24 (classic cost estimate)",
        object_type="transaction",
        deprecated_in="S/4HANA 2020",
        removed_in=None,
        replacement="Manage Standard Cost Estimates (Fiori F3873)",
        impact=ImpactSeverity.MEDIUM,
        change_type=ChangeType.DEPRECATED_TRANSACTION,
        description=(
            "Classic product cost planning transactions CK11N and CK24 are "
            "being replaced by the Fiori-based standard cost estimate app."
        ),
        affected_business_areas=["Controlling", "Production"],
    ),
    DeprecatedObject(
        object_name="FBCJ (cash journal old)",
        object_type="transaction",
        deprecated_in="S/4HANA 2021",
        removed_in=None,
        replacement="Manage Cash Journal (Fiori F3956)",
        impact=ImpactSeverity.LOW,
        change_type=ChangeType.DEPRECATED_TRANSACTION,
        description=(
            "Classic cash journal transaction FBCJ deprecated in favor of "
            "the Fiori cash journal app."
        ),
        affected_business_areas=["Finance"],
    ),
    DeprecatedObject(
        object_name="VL01N / VL02N (old Dynpro)",
        object_type="transaction",
        deprecated_in="S/4HANA 2022",
        removed_in=None,
        replacement="Manage Outbound Deliveries (Fiori F2189)",
        impact=ImpactSeverity.MEDIUM,
        change_type=ChangeType.DEPRECATED_TRANSACTION,
        description=(
            "Classic outbound delivery transactions recommended to be replaced "
            "by the Fiori delivery management app."
        ),
        affected_business_areas=["Sales", "Logistics"],
    ),
    DeprecatedObject(
        object_name="F_BKPF_BUP (old payment run auth)",
        object_type="auth_object",
        deprecated_in="S/4HANA 2021",
        removed_in=None,
        replacement="F_BKPF_BUK extended with payment activity",
        impact=ImpactSeverity.HIGH,
        change_type=ChangeType.CHANGED_BEHAVIOR,
        description=(
            "Payment run authorization granularity changed in S/4HANA 2021. "
            "New authorization check uses extended F_BKPF_BUK with payment-specific "
            "activity codes rather than the legacy F_BKPF_BUP object."
        ),
        affected_business_areas=["Finance"],
    ),
    DeprecatedObject(
        object_name="IW31 / IW32 (classic PM Dynpro)",
        object_type="transaction",
        deprecated_in="S/4HANA 2022",
        removed_in=None,
        replacement="Manage Work Orders (Fiori F1350)",
        impact=ImpactSeverity.MEDIUM,
        change_type=ChangeType.DEPRECATED_TRANSACTION,
        description=(
            "Classic Plant Maintenance work order transactions recommended "
            "for migration to the Fiori work order management app."
        ),
        affected_business_areas=["Plant Maintenance"],
    ),
    DeprecatedObject(
        object_name="S_DEVELOP (unrestricted — old pattern)",
        object_type="auth_object",
        deprecated_in="S/4HANA 1909",
        removed_in=None,
        replacement="S_DEVELOP with strict activity restriction",
        impact=ImpactSeverity.CRITICAL,
        change_type=ChangeType.CHANGED_BEHAVIOR,
        description=(
            "Unrestricted S_DEVELOP (*) authorization is a critical security risk "
            "in S/4HANA. SAP recommends restricting to specific activity codes "
            "(01=create, 02=change) and object types per developer."
        ),
        affected_business_areas=["Basis", "Development"],
    ),
    DeprecatedObject(
        object_name="RSUSR002 (User Info System — classic)",
        object_type="transaction",
        deprecated_in="S/4HANA 2020",
        removed_in=None,
        replacement="Identity Access Governance or Fiori User Management",
        impact=ImpactSeverity.MEDIUM,
        change_type=ChangeType.DEPRECATED_TRANSACTION,
        description=(
            "Classic user information system transaction RSUSR002 is being "
            "superseded by Fiori-based user analytics and reporting apps."
        ),
        affected_business_areas=["Basis", "Security"],
    ),
    DeprecatedObject(
        object_name="B_USERST_T (old user status)",
        object_type="auth_object",
        deprecated_in="S/4HANA 2021",
        removed_in="S/4HANA 2023",
        replacement="S_USER_STA (new user status object)",
        impact=ImpactSeverity.MEDIUM,
        change_type=ChangeType.RENAMED_OBJECT,
        description=(
            "User status authorization object B_USERST_T is renamed and "
            "restructured as S_USER_STA in S/4HANA 2021+."
        ),
        affected_business_areas=["Basis"],
    ),
    DeprecatedObject(
        object_name="PP/PI transaction codes (C201-C299)",
        object_type="transaction",
        deprecated_in="S/4HANA 2020",
        removed_in="S/4HANA 2023",
        replacement="Manage Process Orders (Fiori F4905)",
        impact=ImpactSeverity.HIGH,
        change_type=ChangeType.DEPRECATED_TRANSACTION,
        description=(
            "Classic PP/PI process order transactions in the C200 range are "
            "being phased out in favor of Fiori process order management apps."
        ),
        affected_business_areas=["Production Planning", "Manufacturing"],
    ),
]


# ---------------------------------------------------------------------------
# New requirements knowledge base
# ---------------------------------------------------------------------------

_NEW_REQUIREMENTS: List[NewRequirement] = [
    NewRequirement(
        object_name="S_SERVICE",
        object_type="auth_object",
        introduced_in="S/4HANA 1909",
        mandatory=True,
        description=(
            "S_SERVICE must be granted for every OData service a user needs "
            "to call via Fiori. Without this, tile is visible but app fails to launch. "
            "Most critical new requirement for Fiori authorization."
        ),
        example_value="SRV_NAME = MM_PUR_PO_MAINT_V2_SRV",
        related_fiori_apps=["F0842A", "F0859", "F2229", "F3702", "F1861", "F2358"],
        affected_business_areas=["All"],
        impact=ImpactSeverity.CRITICAL,
    ),
    NewRequirement(
        object_name="UI_LAUNCHPAD",
        object_type="auth_object",
        introduced_in="S/4HANA 1909",
        mandatory=True,
        description=(
            "Authorization object for accessing the SAP Fiori Launchpad shell. "
            "Users without this object cannot open the launchpad at all."
        ),
        example_value="ACTVT = 16 (Execute)",
        related_fiori_apps=["F1603", "F0150"],
        affected_business_areas=["All"],
        impact=ImpactSeverity.CRITICAL,
    ),
    NewRequirement(
        object_name="S_START (Fiori tile start)",
        object_type="auth_object",
        introduced_in="S/4HANA 1909",
        mandatory=True,
        description=(
            "Controls which Fiori apps a user can start from the launchpad. "
            "Replaces the S_TCODE check for Fiori apps. Must be included in "
            "all roles that grant Fiori app access."
        ),
        example_value="AUTH = <semantic object hash>",
        related_fiori_apps=["F0842A", "F0859", "F3702"],
        affected_business_areas=["All"],
        impact=ImpactSeverity.HIGH,
    ),
    NewRequirement(
        object_name="F_FAGL_LEG (Universal Journal)",
        object_type="auth_object",
        introduced_in="S/4HANA 1909",
        mandatory=True,
        description=(
            "New authorization object for accessing Universal Journal (ACDOCA) "
            "entries. Required for all FI/CO reporting and posting apps."
        ),
        example_value="RLDNR = 0L (leading ledger)",
        related_fiori_apps=["F0859", "F1691", "F2906"],
        affected_business_areas=["Finance", "Controlling"],
        impact=ImpactSeverity.HIGH,
    ),
    NewRequirement(
        object_name="FI_ML (Material Ledger auth)",
        object_type="auth_object",
        introduced_in="S/4HANA 2020",
        mandatory=False,
        description=(
            "Material Ledger authorization object required when Material Ledger "
            "is activated (mandatory in S/4HANA). Controls access to actual costing "
            "data and price changes."
        ),
        example_value="ACTVT = 01, 02, 03",
        related_fiori_apps=["F4218", "F4720"],
        affected_business_areas=["Finance", "Materials Management", "Controlling"],
        impact=ImpactSeverity.MEDIUM,
    ),
    NewRequirement(
        object_name="S_BTCH_JOB (enhanced)",
        object_type="auth_object",
        introduced_in="S/4HANA 2021",
        mandatory=False,
        description=(
            "Enhanced background job authorization now includes Application Server "
            "and job class restrictions. Existing blanket S_BTCH_JOB assignments "
            "must be reviewed and tightened."
        ),
        example_value="JOBACTION = RELE, AUTH = RELE",
        related_fiori_apps=[],
        affected_business_areas=["Basis", "All"],
        impact=ImpactSeverity.MEDIUM,
    ),
    NewRequirement(
        object_name="SRT_BO_QUERY (BOA framework)",
        object_type="auth_object",
        introduced_in="S/4HANA 2020",
        mandatory=False,
        description=(
            "New authorization object for Business Object Access (BOA) framework "
            "queries. Required by several S/4HANA Fiori apps that use the BOA "
            "query service layer."
        ),
        example_value="ACTVT = 03",
        related_fiori_apps=["F2229", "F3600", "F2340"],
        affected_business_areas=["Master Data", "Finance"],
        impact=ImpactSeverity.MEDIUM,
    ),
    NewRequirement(
        object_name="FI_FIPAY (Payment Approval)",
        object_type="auth_object",
        introduced_in="S/4HANA 2021",
        mandatory=False,
        description=(
            "Dedicated payment approval authorization object introduced for "
            "digital payment approval workflows. Separate from payment posting "
            "authorization (F_BKPF_BUK)."
        ),
        example_value="ACTVT = 07 (approve)",
        related_fiori_apps=["F1861", "F2483"],
        affected_business_areas=["Finance"],
        impact=ImpactSeverity.HIGH,
    ),
    NewRequirement(
        object_name="C_AFRU_BGR (confirmation auth)",
        object_type="auth_object",
        introduced_in="S/4HANA 2020",
        mandatory=False,
        description=(
            "New PP order confirmation authorization introducing business group "
            "restriction. Replaces blanket IW41/CO11N authorization patterns."
        ),
        example_value="PERSA = *, BGR = *",
        related_fiori_apps=["F4720"],
        affected_business_areas=["Production Planning"],
        impact=ImpactSeverity.MEDIUM,
    ),
    NewRequirement(
        object_name="MDG_BS_MROLE (MDG role auth)",
        object_type="auth_object",
        introduced_in="S/4HANA 2022",
        mandatory=False,
        description=(
            "Master Data Governance role-based authorization object. Required when "
            "MDG is used for centralized master data governance workflows."
        ),
        example_value="ROLE = BP_CREATOR, ACTVT = 16",
        related_fiori_apps=["F2229", "F3600", "F2340"],
        affected_business_areas=["Master Data"],
        impact=ImpactSeverity.MEDIUM,
    ),
    NewRequirement(
        object_name="HR_PTIM_V (time recording)",
        object_type="auth_object",
        introduced_in="S/4HANA 2021",
        mandatory=False,
        description=(
            "New HR time management authorization object replacing the legacy "
            "PA_RPTIME object. Required for all time recording and approval scenarios."
        ),
        example_value="PERSA = *, ACTVT = 01, 02, 03",
        related_fiori_apps=["F1924"],
        affected_business_areas=["Human Resources"],
        impact=ImpactSeverity.HIGH,
    ),
    NewRequirement(
        object_name="S_EPM_APPL (Embedded Analytics)",
        object_type="auth_object",
        introduced_in="S/4HANA 1909",
        mandatory=False,
        description=(
            "Authorization for Embedded Analytics (SAC / CDS analytical views). "
            "Required for users accessing real-time S/4HANA analytical apps."
        ),
        example_value="APPL = FIN_GL_*, ACTVT = 03",
        related_fiori_apps=["F1691", "F2906"],
        affected_business_areas=["Finance", "Controlling", "All Reporting"],
        impact=ImpactSeverity.MEDIUM,
    ),
    NewRequirement(
        object_name="SYST_BC_WF (new workflow auth)",
        object_type="auth_object",
        introduced_in="S/4HANA 2022",
        mandatory=False,
        description=(
            "New SAP Business Technology Platform (BTP) workflow authorization "
            "object. Required when using BTP-based approval flows integrated with "
            "S/4HANA."
        ),
        example_value="WF_APPL = SAP_FIN_AP_APPROVAL",
        related_fiori_apps=["F1603", "F1366"],
        affected_business_areas=["Workflow", "All"],
        impact=ImpactSeverity.MEDIUM,
    ),
    NewRequirement(
        object_name="S_TABU_NAM (table authorization)",
        object_type="auth_object",
        introduced_in="S/4HANA 2020",
        mandatory=False,
        description=(
            "Table-level authorization object replacing generic S_TABU_DIS for "
            "specific table access control. Allows tighter restriction on which "
            "specific tables users can access."
        ),
        example_value="TABLE = T001, ACTVT = 03",
        related_fiori_apps=["F4109", "F5502"],
        affected_business_areas=["Finance", "Basis", "Configuration"],
        impact=ImpactSeverity.MEDIUM,
    ),
    NewRequirement(
        object_name="FI_APAR_ANC (AP/AR netting)",
        object_type="auth_object",
        introduced_in="S/4HANA 2023",
        mandatory=False,
        description=(
            "New authorization object for AP/AR netting and payment netting "
            "scenarios introduced in S/4HANA 2023."
        ),
        example_value="BUKRS = *, ACTVT = 16",
        related_fiori_apps=["F1861", "F3789", "F2483"],
        affected_business_areas=["Finance"],
        impact=ImpactSeverity.LOW,
    ),
]


# ---------------------------------------------------------------------------
# Simplification items
# ---------------------------------------------------------------------------

_SIMPLIFICATION_ITEMS: List[SimplificationItem] = [
    SimplificationItem(
        item_id="SIM-001",
        title="Removal of EC-PCA (Classic Profit Center Accounting)",
        description=(
            "Classic EC-PCA is removed in S/4HANA. Profit center accounting "
            "is now fully integrated into the Universal Journal (ACDOCA). "
            "All KE* roles and authorizations must be redesigned."
        ),
        affected_version="S/4HANA 1909",
        change_type=ChangeType.SIMPLIFICATION,
        impact=ImpactSeverity.CRITICAL,
        action_required=(
            "Review all roles containing KE* transactions. Redesign CO reporting "
            "roles to use the Universal Journal profit center dimension. "
            "Test all profit center reports in sandbox."
        ),
        affected_objects=["K_PCA", "KE51", "KE52", "KE1Y", "KE30"],
    ),
    SimplificationItem(
        item_id="SIM-002",
        title="Material Ledger Mandatory Activation",
        description=(
            "Material Ledger (ML) is mandatory in S/4HANA. All material valuation "
            "goes through ML. This affects authorization objects for price changes "
            "and actual costing."
        ),
        affected_version="S/4HANA 1909",
        change_type=ChangeType.NEW_OBJECT,
        impact=ImpactSeverity.HIGH,
        action_required=(
            "Add FI_ML authorization object to all roles that perform material "
            "price changes (MR21, MR22). Adjust valuation area-based authorization."
        ),
        affected_objects=["FI_ML", "MR21", "MR22", "CKM3N"],
    ),
    SimplificationItem(
        item_id="SIM-003",
        title="Business Partner as Single Source — Customer/Vendor Integration",
        description=(
            "Customer and Vendor master data is unified under Business Partner (BP) "
            "in S/4HANA. Separate customer (KNA1) and vendor (LFA1) maintenance "
            "transactions are deprecated."
        ),
        affected_version="S/4HANA 1909",
        change_type=ChangeType.SIMPLIFICATION,
        impact=ImpactSeverity.HIGH,
        action_required=(
            "Replace XD01/XD02 (customer) and XK01/XK02 (vendor) authorizations "
            "with Business Partner authorization (B_BUPA_*). Map old object values "
            "to new BP role types."
        ),
        affected_objects=["B_BUPA_BZT", "B_BUPA_GRP", "B_BUPA_RLT", "XD01", "XK01", "FD01"],
    ),
    SimplificationItem(
        item_id="SIM-004",
        title="Removal of Asset Accounting with Parallel Depreciation Areas (Old APC)",
        description=(
            "Classic Asset Accounting with parallel depreciation areas is replaced "
            "by the New Asset Accounting in S/4HANA. Authorization objects for "
            "depreciation area management change significantly."
        ),
        affected_version="S/4HANA 1909",
        change_type=ChangeType.SIMPLIFICATION,
        impact=ImpactSeverity.HIGH,
        action_required=(
            "Migrate asset accounting authorization from classic A_ANLAGE_A "
            "to the new A_T001A object structure. Test all asset posting "
            "and reporting scenarios."
        ),
        affected_objects=["A_T001A", "A_ANLAGE_A", "AS01", "AS02", "AFAB"],
    ),
    SimplificationItem(
        item_id="SIM-005",
        title="Fiori Launchpad as Primary UX — GUI Phaseout",
        description=(
            "SAP GUI access is being phased out as the primary UX. S/4HANA roles "
            "must include Fiori catalog/space/page assignments alongside or instead "
            "of SAP GUI transaction codes."
        ),
        affected_version="S/4HANA 1909",
        change_type=ChangeType.FIORI_REQUIREMENT,
        impact=ImpactSeverity.CRITICAL,
        action_required=(
            "For each SAP GUI role, identify the equivalent Fiori app(s). Add "
            "S_SERVICE for each OData service. Assign catalogs via business role. "
            "Run Fiori app checker (transaction /UI2/FLP) to validate."
        ),
        affected_objects=["S_SERVICE", "UI_LAUNCHPAD", "S_START"],
    ),
    SimplificationItem(
        item_id="SIM-006",
        title="HR Renewal and Time Management Restructuring",
        description=(
            "HR Renewal in S/4HANA restructures time management authorization. "
            "PA30/PA20 (classic infotype maintenance) authorization model changes "
            "with the adoption of the new HR admin cockpit."
        ),
        affected_version="S/4HANA 2021",
        change_type=ChangeType.CHANGED_BEHAVIOR,
        impact=ImpactSeverity.HIGH,
        action_required=(
            "Review P_ORGIN and P_ORGINCON authorization for all HR roles. "
            "Map personnel area/subarea restrictions to new structural authorization. "
            "Test HR self-service Fiori scenarios."
        ),
        affected_objects=["P_ORGIN", "P_PERNR", "HR_PTIM_V", "PA_RPTIME"],
    ),
    SimplificationItem(
        item_id="SIM-007",
        title="Table Authorization Tightening (S_TABU_DIS to S_TABU_NAM)",
        description=(
            "S/4HANA 2020 introduces table-name level authorization via S_TABU_NAM "
            "to replace the broader table class authorization S_TABU_DIS. "
            "This allows more granular control over which specific tables users access."
        ),
        affected_version="S/4HANA 2020",
        change_type=ChangeType.NEW_OBJECT,
        impact=ImpactSeverity.MEDIUM,
        action_required=(
            "Review roles containing S_TABU_DIS with broad class authorizations. "
            "Replace with S_TABU_NAM for specific table names where possible. "
            "Audit developers and support users for excessive table access."
        ),
        affected_objects=["S_TABU_DIS", "S_TABU_NAM", "SE16", "SE16N", "SM30"],
    ),
    SimplificationItem(
        item_id="SIM-008",
        title="Integration of SD and MM Procurement via Unified Purchasing",
        description=(
            "Procurement processes in S/4HANA unify SD (scheduling agreements via "
            "customer) and MM (purchasing) authorization models. STO authorization "
            "changes significantly."
        ),
        affected_version="S/4HANA 2022",
        change_type=ChangeType.CHANGED_BEHAVIOR,
        impact=ImpactSeverity.MEDIUM,
        action_required=(
            "Review stock transfer order roles. Adjust M_BEST_BSA document type "
            "settings for cross-company and cross-plant STOs. Test in integration "
            "sandbox before production upgrade."
        ),
        affected_objects=["M_BEST_BSA", "M_BEST_EKO", "V_VBAK_AAT", "ME27"],
    ),
]


# ---------------------------------------------------------------------------
# Mock affected roles
# ---------------------------------------------------------------------------

_AFFECTED_ROLES: List[AffectedRole] = [
    AffectedRole(
        role_id="Z_FI_AP_ACCOUNTANT",
        role_name="FI Accounts Payable Accountant",
        role_type="single",
        business_area="Finance",
        deprecated_objects_count=4,
        new_objects_count=3,
        simplification_items_count=1,
        overall_impact=ImpactSeverity.HIGH,
        requires_redesign=False,
        notes=(
            "AP posting and payment transactions need Fiori S_SERVICE additions. "
            "F-53/F-28 references should migrate to Fiori apps F1861/F3789."
        ),
    ),
    AffectedRole(
        role_id="Z_CO_PROFIT_CENTER_MGR",
        role_name="CO Profit Center Manager",
        role_type="single",
        business_area="Controlling",
        deprecated_objects_count=8,
        new_objects_count=2,
        simplification_items_count=2,
        overall_impact=ImpactSeverity.CRITICAL,
        requires_redesign=True,
        notes=(
            "EC-PCA removal (SIM-001) requires complete role redesign. "
            "KE* transactions removed — must migrate to Universal Journal "
            "profit center reporting apps."
        ),
    ),
    AffectedRole(
        role_id="Z_MM_PURCHASER",
        role_name="MM Purchasing Specialist",
        role_type="single",
        business_area="Materials Management",
        deprecated_objects_count=2,
        new_objects_count=4,
        simplification_items_count=1,
        overall_impact=ImpactSeverity.HIGH,
        requires_redesign=False,
        notes=(
            "Must add S_SERVICE for MM_PUR_PO_MAINT_V2_SRV and related services. "
            "Business partner authorization adjustment needed for vendor master."
        ),
    ),
    AffectedRole(
        role_id="Z_HR_PAYROLL_ADMIN",
        role_name="HR Payroll Administrator",
        role_type="single",
        business_area="Human Resources",
        deprecated_objects_count=3,
        new_objects_count=3,
        simplification_items_count=1,
        overall_impact=ImpactSeverity.HIGH,
        requires_redesign=False,
        notes=(
            "PA_RPTIME deprecation requires migration to HR_PTIM_V. "
            "Payroll run Fiori app S_SERVICE for HR_PAYROLL_RUN_SRV needed."
        ),
    ),
    AffectedRole(
        role_id="Z_BASIS_USER_ADMIN",
        role_name="Basis User Administrator",
        role_type="single",
        business_area="Basis",
        deprecated_objects_count=1,
        new_objects_count=2,
        simplification_items_count=0,
        overall_impact=ImpactSeverity.MEDIUM,
        requires_redesign=False,
        notes=(
            "SU01D deprecation means user admin Fiori app F0998 should be added. "
            "S_SERVICE for USER_MANAGEMENT_SRV must be included."
        ),
    ),
    AffectedRole(
        role_id="Z_FI_GL_ACCOUNTANT",
        role_name="FI General Ledger Accountant",
        role_type="single",
        business_area="Finance",
        deprecated_objects_count=3,
        new_objects_count=4,
        simplification_items_count=2,
        overall_impact=ImpactSeverity.HIGH,
        requires_redesign=False,
        notes=(
            "F_BKPF_GSB deprecation. New F_FAGL_LEG Universal Journal "
            "authorization required. S_SERVICE for FIN_GL_ITEMS_SRV."
        ),
    ),
    AffectedRole(
        role_id="Z_SD_SALES_REP",
        role_name="SD Sales Representative",
        role_type="single",
        business_area="Sales",
        deprecated_objects_count=2,
        new_objects_count=3,
        simplification_items_count=1,
        overall_impact=ImpactSeverity.MEDIUM,
        requires_redesign=False,
        notes=(
            "Customer master migration from XD01 to Business Partner. "
            "S_SERVICE for SD_SALES_ORDER_MANAGE_V2 and API_BUSINESS_PARTNER."
        ),
    ),
    AffectedRole(
        role_id="Z_DEVELOPER",
        role_name="ABAP Developer",
        role_type="single",
        business_area="Basis",
        deprecated_objects_count=0,
        new_objects_count=2,
        simplification_items_count=1,
        overall_impact=ImpactSeverity.CRITICAL,
        requires_redesign=True,
        notes=(
            "Unrestricted S_DEVELOP must be restricted in S/4HANA. "
            "Security audit required before upgrade. Development role must "
            "be split by developer type and object scope."
        ),
    ),
    AffectedRole(
        role_id="Z_COMPOSITE_FINANCE_USER",
        role_name="Finance User (Composite)",
        role_type="composite",
        business_area="Finance",
        deprecated_objects_count=6,
        new_objects_count=8,
        simplification_items_count=3,
        overall_impact=ImpactSeverity.HIGH,
        requires_redesign=False,
        notes=(
            "Composite role containing multiple FI sub-roles. Each sub-role "
            "requires individual S_SERVICE additions and Universal Journal "
            "authorization updates."
        ),
    ),
    AffectedRole(
        role_id="Z_PP_PRODUCTION_OPERATOR",
        role_name="PP Production Operator",
        role_type="single",
        business_area="Production Planning",
        deprecated_objects_count=2,
        new_objects_count=2,
        simplification_items_count=0,
        overall_impact=ImpactSeverity.MEDIUM,
        requires_redesign=False,
        notes=(
            "New C_AFRU_BGR authorization required for order confirmations. "
            "PP/PI C2xx transactions migration to Fiori Process Order app."
        ),
    ),
]


# ===========================================================================
# Analyzer engine
# ===========================================================================

class UpgradeImpactAnalyzer:
    """
    Assesses the security and authorization impact of SAP version upgrades.

    Provides:
    - Full impact analysis per upgrade path
    - Per-role impact simulation
    - Deprecated object inventory per version
    - New authorization requirements per version
    - Actionable remediation plan
    """

    def get_supported_versions(self) -> List[Dict[str, str]]:
        """Return all supported version upgrade pairs."""
        return SUPPORTED_VERSION_PAIRS

    def analyze_upgrade(self, from_version: str, to_version: str) -> UpgradeImpact:
        """
        Perform a full security impact analysis for an upgrade path.

        The from_version and to_version must appear in the supported version list.
        Returns comprehensive impact data including deprecated objects, new requirements,
        simplification items, and affected roles.
        """
        pair_found = any(
            p["from"] == from_version and p["to"] == to_version
            for p in SUPPORTED_VERSION_PAIRS
        )
        if not pair_found:
            raise ValueError(
                f"Unsupported upgrade path: {from_version} -> {to_version}. "
                "Call get_supported_versions() for valid pairs."
            )

        deprecated = self.get_deprecated_objects(to_version)
        new_reqs = self.get_new_requirements(to_version)
        simp_items = self._get_simplification_items(to_version)
        affected = self.get_affected_roles()
        critical_count = sum(
            1 for d in deprecated if d.impact == ImpactSeverity.CRITICAL
        ) + sum(
            1 for n in new_reqs if n.impact == ImpactSeverity.CRITICAL
        )

        is_ecc_to_s4 = from_version.startswith("ECC")
        effort = "6-12 months" if is_ecc_to_s4 else "4-8 weeks"

        return UpgradeImpact(
            from_version=from_version,
            to_version=to_version,
            analysis_timestamp=datetime.utcnow().isoformat() + "Z",
            total_deprecated_objects=len(deprecated),
            total_new_requirements=len(new_reqs),
            total_simplification_items=len(simp_items),
            total_affected_roles=len(affected),
            critical_items=critical_count,
            deprecated_objects=deprecated,
            new_requirements=new_reqs,
            simplification_items=simp_items,
            affected_roles=affected,
            executive_summary=(
                f"Upgrade from {from_version} to {to_version} affects "
                f"{len(affected)} roles with {len(deprecated)} deprecated objects "
                f"and {len(new_reqs)} new authorization requirements. "
                f"{critical_count} critical items require immediate attention. "
                f"Estimated remediation effort: {effort}."
            ),
            estimated_remediation_effort=effort,
        )

    def get_affected_roles(self) -> List[AffectedRole]:
        """Return all roles expected to be impacted by a standard ECC -> S/4HANA upgrade."""
        return list(_AFFECTED_ROLES)

    def get_deprecated_objects(self, version: str) -> List[DeprecatedObject]:
        """
        Return deprecated authorization objects and transactions up to and
        including the given target version.
        """
        _version_order = [
            "S/4HANA 1909", "S/4HANA 2020", "S/4HANA 2021",
            "S/4HANA 2022", "S/4HANA 2023",
        ]
        if version not in _version_order:
            # Return all if version is not in the ordered list
            return list(_DEPRECATED_OBJECTS)

        target_idx = _version_order.index(version)
        return [
            obj for obj in _DEPRECATED_OBJECTS
            if obj.deprecated_in in _version_order
            and _version_order.index(obj.deprecated_in) <= target_idx
        ]

    def get_new_requirements(self, version: str) -> List[NewRequirement]:
        """
        Return new authorization requirements introduced up to and including
        the given target version.
        """
        _version_order = [
            "S/4HANA 1909", "S/4HANA 2020", "S/4HANA 2021",
            "S/4HANA 2022", "S/4HANA 2023",
        ]
        if version not in _version_order:
            return list(_NEW_REQUIREMENTS)

        target_idx = _version_order.index(version)
        return [
            req for req in _NEW_REQUIREMENTS
            if req.introduced_in in _version_order
            and _version_order.index(req.introduced_in) <= target_idx
        ]

    def simulate_upgrade(
        self, role_ids: List[str], from_version: str, to_version: str
    ) -> UpgradeSimulation:
        """
        Simulate the upgrade impact for a specific set of role IDs.

        Matches role_ids against the known affected role catalog. Unknown
        role IDs are reported with a generic medium-impact assessment.
        """
        deprecated = self.get_deprecated_objects(to_version)
        new_reqs = self.get_new_requirements(to_version)
        role_catalog: Dict[str, AffectedRole] = {r.role_id: r for r in _AFFECTED_ROLES}

        results: List[RoleSimulationResult] = []
        redesign_count = 0

        for role_id in role_ids:
            known = role_catalog.get(role_id)
            if known:
                dep_count = known.deprecated_objects_count
                new_count = known.new_objects_count
                impact = known.overall_impact
                requires_redesign = known.requires_redesign
                action_items = [
                    f"Remove {dep_count} deprecated authorization object(s).",
                    f"Add {new_count} new authorization object(s).",
                    "Add S_SERVICE entries for all required OData services.",
                    "Assign business role catalog for Fiori app access.",
                ]
                if requires_redesign:
                    action_items.insert(0, "REDESIGN REQUIRED — see simplification items.")
            else:
                dep_count = 2
                new_count = 3
                impact = ImpactSeverity.MEDIUM
                requires_redesign = False
                action_items = [
                    "Review role for deprecated objects (estimated 2 objects).",
                    "Add S_SERVICE entries for Fiori apps in this role.",
                    "Add UI_LAUNCHPAD and S_START authorization.",
                ]

            if requires_redesign:
                redesign_count += 1

            results.append(RoleSimulationResult(
                role_id=role_id,
                role_name=known.role_name if known else f"Role: {role_id}",
                current_objects=[d.object_name for d in deprecated[:dep_count]],
                deprecated_in_role=[d.object_name for d in deprecated[:dep_count]],
                new_required=[n.object_name for n in new_reqs[:new_count]],
                net_change=new_count - dep_count,
                impact=impact,
                action_items=action_items,
            ))

        total_dep = sum(r.deprecated_objects_count if (r2 := role_catalog.get(r.role_id)) else 2
                        for r in results
                        for r in [type('obj', (object,), {"role_id": r.role_id,
                                  "deprecated_objects_count": 2})()]
                        ) if False else sum(
            (role_catalog[rid].deprecated_objects_count if rid in role_catalog else 2)
            for rid in role_ids
        )
        total_new = sum(
            (role_catalog[rid].new_objects_count if rid in role_catalog else 3)
            for rid in role_ids
        )

        return UpgradeSimulation(
            from_version=from_version,
            to_version=to_version,
            simulation_timestamp=datetime.utcnow().isoformat() + "Z",
            role_results=results,
            total_deprecated=total_dep,
            total_new=total_new,
            roles_requiring_redesign=redesign_count,
            estimated_effort_hours=float(len(role_ids) * 8 + redesign_count * 24),
        )

    def generate_remediation_plan(
        self, from_version: str = "ECC 6.0 EHP8", to_version: str = "S/4HANA 2022"
    ) -> RemediationPlan:
        """
        Generate a phased remediation plan for the upgrade.

        Phases:
        - Phase 1 - Assessment: inventory and gap analysis
        - Phase 2 - Design: role redesign and new object mapping
        - Phase 3 - Build: PFCG changes and profile generation
        - Phase 4 - Test: sandbox and integration testing
        - Phase 5 - Cutover: production migration and hypercare
        """
        tasks_p1 = [
            RemediationTask(
                task_id="T001",
                title="Inventory existing roles and authorization objects",
                description=(
                    "Export all custom roles (Z_* and Y_*) from current system. "
                    "Document all authorization objects and values per role."
                ),
                action=RemediationAction.REVIEW,
                priority=ImpactSeverity.CRITICAL,
                estimated_hours=16.0,
                affected_roles=["All"],
                objects_involved=["All authorization objects"],
            ),
            RemediationTask(
                task_id="T002",
                title="Map deprecated objects to replacements",
                description=(
                    "For each deprecated object/transaction, identify the replacement "
                    "and map existing roles to the new object structure."
                ),
                action=RemediationAction.REPLACE,
                priority=ImpactSeverity.HIGH,
                estimated_hours=24.0,
                affected_roles=["All"],
                objects_involved=[d.object_name for d in _DEPRECATED_OBJECTS[:10]],
                prerequisite_tasks=["T001"],
            ),
            RemediationTask(
                task_id="T003",
                title="Identify Fiori app requirements per business role",
                description=(
                    "For each business area, identify which Fiori apps replace "
                    "existing GUI transactions and document required S_SERVICE entries."
                ),
                action=RemediationAction.REVIEW,
                priority=ImpactSeverity.HIGH,
                estimated_hours=20.0,
                affected_roles=["All"],
                objects_involved=["S_SERVICE", "UI_LAUNCHPAD", "S_START"],
                prerequisite_tasks=["T001"],
            ),
        ]
        tasks_p2 = [
            RemediationTask(
                task_id="T004",
                title="Redesign EC-PCA dependent roles",
                description=(
                    "Roles using EC-PCA (KE* transactions) must be completely "
                    "redesigned for Universal Journal profit center reporting."
                ),
                action=RemediationAction.REPLACE,
                priority=ImpactSeverity.CRITICAL,
                estimated_hours=40.0,
                affected_roles=["Z_CO_PROFIT_CENTER_MGR"],
                objects_involved=["K_PCA", "KE51", "F_FAGL_LEG"],
                prerequisite_tasks=["T002"],
            ),
            RemediationTask(
                task_id="T005",
                title="Design Business Partner authorization for customer/vendor roles",
                description=(
                    "Map XD01/XK01 authorization patterns to B_BUPA_* authorization "
                    "objects for the customer-vendor integration in S/4HANA."
                ),
                action=RemediationAction.REPLACE,
                priority=ImpactSeverity.HIGH,
                estimated_hours=16.0,
                affected_roles=["Z_MM_PURCHASER", "Z_SD_SALES_REP"],
                objects_involved=["B_BUPA_BZT", "B_BUPA_GRP", "B_BUPA_RLT"],
                prerequisite_tasks=["T002"],
            ),
            RemediationTask(
                task_id="T006",
                title="Restrict unrestricted S_DEVELOP authorizations",
                description=(
                    "Audit and restrict all S_DEVELOP (*) authorizations. "
                    "Create developer-type specific roles with scoped object access."
                ),
                action=RemediationAction.REPLACE,
                priority=ImpactSeverity.CRITICAL,
                estimated_hours=24.0,
                affected_roles=["Z_DEVELOPER"],
                objects_involved=["S_DEVELOP"],
                prerequisite_tasks=["T001"],
            ),
        ]
        tasks_p3 = [
            RemediationTask(
                task_id="T007",
                title="Add S_SERVICE authorization to all Fiori-enabled roles",
                description=(
                    "For every role that will access Fiori apps, add S_SERVICE "
                    "entries for all OData services required by those apps."
                ),
                action=RemediationAction.ADD,
                priority=ImpactSeverity.CRITICAL,
                estimated_hours=32.0,
                affected_roles=["All Fiori-enabled roles"],
                objects_involved=["S_SERVICE"],
                prerequisite_tasks=["T003", "T004"],
            ),
            RemediationTask(
                task_id="T008",
                title="Add Universal Journal authorization (F_FAGL_LEG) to FI/CO roles",
                description=(
                    "Add F_FAGL_LEG authorization to all Financial Accounting "
                    "and Controlling roles for Universal Journal access."
                ),
                action=RemediationAction.ADD,
                priority=ImpactSeverity.HIGH,
                estimated_hours=8.0,
                affected_roles=["Z_FI_AP_ACCOUNTANT", "Z_FI_GL_ACCOUNTANT", "Z_COMPOSITE_FINANCE_USER"],
                objects_involved=["F_FAGL_LEG"],
                prerequisite_tasks=["T005"],
            ),
            RemediationTask(
                task_id="T009",
                title="Remove deprecated authorization objects from all roles",
                description=(
                    "Remove all deprecated objects identified in the gap analysis "
                    "from affected roles. Regenerate authorization profiles."
                ),
                action=RemediationAction.REMOVE,
                priority=ImpactSeverity.HIGH,
                estimated_hours=20.0,
                affected_roles=["All"],
                objects_involved=[d.object_name for d in _DEPRECATED_OBJECTS if
                                  d.impact in (ImpactSeverity.HIGH, ImpactSeverity.CRITICAL)],
                prerequisite_tasks=["T002"],
            ),
        ]
        tasks_p4 = [
            RemediationTask(
                task_id="T010",
                title="Test all redesigned roles in S/4HANA sandbox",
                description=(
                    "Perform end-to-end testing of all modified roles in the "
                    "S/4HANA sandbox system. Use transaction SU53 to check "
                    "authorization failures."
                ),
                action=RemediationAction.TEST,
                priority=ImpactSeverity.HIGH,
                estimated_hours=40.0,
                affected_roles=["All"],
                objects_involved=["All"],
                prerequisite_tasks=["T007", "T008", "T009"],
            ),
            RemediationTask(
                task_id="T011",
                title="Fiori authorization end-to-end test",
                description=(
                    "Test each Fiori app tile visibility and launch for all "
                    "business user personas. Verify S_SERVICE allows OData calls."
                ),
                action=RemediationAction.TEST,
                priority=ImpactSeverity.HIGH,
                estimated_hours=24.0,
                affected_roles=["All Fiori-enabled roles"],
                objects_involved=["S_SERVICE", "UI_LAUNCHPAD"],
                prerequisite_tasks=["T010"],
            ),
        ]
        tasks_p5 = [
            RemediationTask(
                task_id="T012",
                title="Production role transport and user re-assignment",
                description=(
                    "Transport redesigned roles to production system. "
                    "Re-assign roles to users and verify access profiles are generated."
                ),
                action=RemediationAction.ADD,
                priority=ImpactSeverity.CRITICAL,
                estimated_hours=8.0,
                affected_roles=["All"],
                objects_involved=["All"],
                prerequisite_tasks=["T011"],
            ),
        ]

        total_hours = sum(
            t.estimated_hours
            for phase in [tasks_p1, tasks_p2, tasks_p3, tasks_p4, tasks_p5]
            for t in phase
        )

        return RemediationPlan(
            from_version=from_version,
            to_version=to_version,
            generated_at=datetime.utcnow().isoformat() + "Z",
            total_tasks=12,
            total_estimated_hours=total_hours,
            phases={
                "Phase 1 - Assessment": tasks_p1,
                "Phase 2 - Design": tasks_p2,
                "Phase 3 - Build": tasks_p3,
                "Phase 4 - Test": tasks_p4,
                "Phase 5 - Cutover": tasks_p5,
            },
            critical_path=["T001", "T002", "T007", "T010", "T012"],
            notes=[
                "All estimates assume a team of 2 security consultants.",
                "Testing phase assumes access to a functional S/4HANA sandbox.",
                "EC-PCA redesign (T004) is the longest lead-time item.",
                "S_DEVELOP restriction (T006) requires developer sign-off.",
            ],
        )

    def _get_simplification_items(self, version: str) -> List[SimplificationItem]:
        """Return simplification items relevant to the given target version."""
        _version_order = [
            "S/4HANA 1909", "S/4HANA 2020", "S/4HANA 2021",
            "S/4HANA 2022", "S/4HANA 2023",
        ]
        if version not in _version_order:
            return list(_SIMPLIFICATION_ITEMS)
        target_idx = _version_order.index(version)
        return [
            item for item in _SIMPLIFICATION_ITEMS
            if item.affected_version in _version_order
            and _version_order.index(item.affected_version) <= target_idx
        ]
