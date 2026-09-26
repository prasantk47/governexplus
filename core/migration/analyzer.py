"""
Migration Analyzer — SAP ECC to S/4HANA Security Impact Analysis

Helps SAP security consultants understand and plan the security impact
of migrating from ECC 6.0 to S/4HANA. Provides:

- Transaction code mapping (ECC -> S/4HANA equivalents and Fiori apps)
- Authorization object delta analysis
- Role-level migration readiness scoring
- User impact assessment
- Prioritized migration plan with effort estimates

Knowledge base covers 50+ transaction mappings, 20+ obsolete transactions,
15+ new S/4HANA auth objects, and a curated Fiori app catalog.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum
import re
import logging

from db.models.intelligence import MigrationMapping
from db.database import db_manager

logger = logging.getLogger(__name__)


# =============================================================================
# Enumerations
# =============================================================================

class MigrationStatus(str, Enum):
    COMPATIBLE      = "compatible"       # Works as-is in S/4HANA
    REPLACED        = "replaced"         # Replaced by a different tcode or Fiori app
    FIORI_ONLY      = "fiori_only"       # No tcode equivalent; Fiori only
    OBSOLETE        = "obsolete"         # Removed; no equivalent
    CHANGED         = "changed"          # Same tcode but behavior/auth changed
    NEW             = "new"              # New in S/4HANA, did not exist in ECC


class MigrationRisk(str, Enum):
    LOW      = "low"
    MEDIUM   = "medium"
    HIGH     = "high"
    CRITICAL = "critical"


class MigrationTaskPriority(str, Enum):
    P1 = "P1 - Critical"
    P2 = "P2 - High"
    P3 = "P3 - Medium"
    P4 = "P4 - Low"


class AuthChangeType(str, Enum):
    NEW        = "new"         # Introduced in S/4HANA
    DEPRECATED = "deprecated"  # Removed or superseded in S/4HANA
    CHANGED    = "changed"     # Exists in both but field values changed
    RENAMED    = "renamed"     # Object renamed


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class FioriApp:
    app_id: str            # e.g. "F0842"
    name: str
    description: str
    catalog: str           # Fiori catalog / launchpad group
    semantic_object: str
    action: str
    replaces_tcodes: List[str] = field(default_factory=list)
    required_auth_objects: List[str] = field(default_factory=list)
    business_process: str = ""

    def to_dict(self) -> dict:
        return {
            "app_id": self.app_id,
            "name": self.name,
            "description": self.description,
            "catalog": self.catalog,
            "semantic_object": self.semantic_object,
            "action": self.action,
            "replaces_tcodes": self.replaces_tcodes,
            "required_auth_objects": self.required_auth_objects,
            "business_process": self.business_process,
        }


@dataclass
class TransactionMapping:
    ecc_tcode: str
    s4_tcode: Optional[str]           # None if Fiori-only or obsolete
    status: MigrationStatus
    fiori_app_ids: List[str] = field(default_factory=list)
    notes: str = ""
    business_process: str = ""
    risk: MigrationRisk = MigrationRisk.LOW

    def to_dict(self) -> dict:
        return {
            "ecc_tcode": self.ecc_tcode,
            "s4_tcode": self.s4_tcode,
            "status": self.status.value,
            "fiori_app_ids": self.fiori_app_ids,
            "notes": self.notes,
            "business_process": self.business_process,
            "risk": self.risk.value,
        }


@dataclass
class AuthObjectChange:
    object_name: str
    change_type: AuthChangeType
    ecc_description: Optional[str]
    s4_description: Optional[str]
    affected_fields: List[str] = field(default_factory=list)
    replaced_by: Optional[str] = None
    notes: str = ""
    business_process: str = ""

    def to_dict(self) -> dict:
        return {
            "object_name": self.object_name,
            "change_type": self.change_type.value,
            "ecc_description": self.ecc_description,
            "s4_description": self.s4_description,
            "affected_fields": self.affected_fields,
            "replaced_by": self.replaced_by,
            "notes": self.notes,
            "business_process": self.business_process,
        }


@dataclass
class TransactionImpact:
    role_id: str
    ecc_tcodes: List[str]
    compatible: List[TransactionMapping]
    replaced: List[TransactionMapping]
    fiori_only: List[TransactionMapping]
    obsolete: List[TransactionMapping]
    changed: List[TransactionMapping]
    unknown: List[str]                 # Tcodes not in knowledge base
    compatibility_pct: float
    required_fiori_apps: List[str]
    summary: str

    def to_dict(self) -> dict:
        return {
            "role_id": self.role_id,
            "ecc_tcodes": self.ecc_tcodes,
            "counts": {
                "total": len(self.ecc_tcodes),
                "compatible": len(self.compatible),
                "replaced": len(self.replaced),
                "fiori_only": len(self.fiori_only),
                "obsolete": len(self.obsolete),
                "changed": len(self.changed),
                "unknown": len(self.unknown),
            },
            "compatible": [m.to_dict() for m in self.compatible],
            "replaced": [m.to_dict() for m in self.replaced],
            "fiori_only": [m.to_dict() for m in self.fiori_only],
            "obsolete": [m.to_dict() for m in self.obsolete],
            "changed": [m.to_dict() for m in self.changed],
            "unknown_tcodes": self.unknown,
            "compatibility_pct": round(self.compatibility_pct, 1),
            "required_fiori_apps": self.required_fiori_apps,
            "summary": self.summary,
        }


@dataclass
class AuthChangeImpact:
    role_id: str
    ecc_auth_objects: List[str]
    new_objects_needed: List[AuthObjectChange]
    deprecated_objects: List[AuthObjectChange]
    changed_objects: List[AuthObjectChange]
    unaffected_objects: List[str]
    migration_effort: str              # "low" | "medium" | "high"
    notes: List[str]

    def to_dict(self) -> dict:
        return {
            "role_id": self.role_id,
            "ecc_auth_objects": self.ecc_auth_objects,
            "new_objects_needed": [o.to_dict() for o in self.new_objects_needed],
            "deprecated_objects": [o.to_dict() for o in self.deprecated_objects],
            "changed_objects": [o.to_dict() for o in self.changed_objects],
            "unaffected_objects": self.unaffected_objects,
            "counts": {
                "ecc_total": len(self.ecc_auth_objects),
                "new_needed": len(self.new_objects_needed),
                "deprecated": len(self.deprecated_objects),
                "changed": len(self.changed_objects),
                "unaffected": len(self.unaffected_objects),
            },
            "migration_effort": self.migration_effort,
            "notes": self.notes,
        }


@dataclass
class RoleMigrationAssessment:
    role_id: str
    role_name: str
    readiness_score: float             # 0–100
    risk: MigrationRisk
    transaction_impact: TransactionImpact
    auth_change_impact: AuthChangeImpact
    recommended_actions: List[str]
    estimated_effort_days: float
    simplification_items: List[str]    # SAP simplification list references
    new_roles_suggested: List[str]
    can_auto_migrate: bool

    def to_dict(self) -> dict:
        return {
            "role_id": self.role_id,
            "role_name": self.role_name,
            "readiness_score": round(self.readiness_score, 1),
            "risk": self.risk.value,
            "transaction_impact": self.transaction_impact.to_dict(),
            "auth_change_impact": self.auth_change_impact.to_dict(),
            "recommended_actions": self.recommended_actions,
            "estimated_effort_days": self.estimated_effort_days,
            "simplification_items": self.simplification_items,
            "new_roles_suggested": self.new_roles_suggested,
            "can_auto_migrate": self.can_auto_migrate,
        }


@dataclass
class UserImpactRecord:
    user_id: str
    user_name: str
    affected_roles: List[str]
    will_lose_access: List[str]        # Tcodes / objects lost
    needs_new_roles: List[str]
    needs_fiori_training: bool
    impact_level: MigrationRisk

    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "user_name": self.user_name,
            "affected_roles": self.affected_roles,
            "will_lose_access": self.will_lose_access,
            "needs_new_roles": self.needs_new_roles,
            "needs_fiori_training": self.needs_fiori_training,
            "impact_level": self.impact_level.value,
        }


@dataclass
class UserImpactReport:
    total_users: int
    affected_users: int
    users_losing_access: int
    users_needing_new_roles: int
    users_needing_fiori_training: int
    high_impact_users: List[UserImpactRecord]
    impact_by_department: Dict[str, int]
    summary: str

    def to_dict(self) -> dict:
        return {
            "total_users": self.total_users,
            "affected_users": self.affected_users,
            "users_losing_access": self.users_losing_access,
            "users_needing_new_roles": self.users_needing_new_roles,
            "users_needing_fiori_training": self.users_needing_fiori_training,
            "high_impact_users": [u.to_dict() for u in self.high_impact_users],
            "impact_by_department": self.impact_by_department,
            "summary": self.summary,
        }


@dataclass
class MigrationTask:
    task_id: str
    title: str
    description: str
    priority: MigrationTaskPriority
    phase: int                         # 1=Preparation, 2=Design, 3=Build, 4=Test, 5=Go-live
    phase_name: str
    effort_days: float
    depends_on: List[str]              # task_ids
    risk: MigrationRisk
    category: str                      # "roles" | "auth" | "fiori" | "testing" | "training"
    affected_roles: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "title": self.title,
            "description": self.description,
            "priority": self.priority.value,
            "phase": self.phase,
            "phase_name": self.phase_name,
            "effort_days": self.effort_days,
            "depends_on": self.depends_on,
            "risk": self.risk.value,
            "category": self.category,
            "affected_roles": self.affected_roles,
        }


@dataclass
class MigrationPlan:
    total_roles: int
    total_effort_days: float
    estimated_duration_weeks: float
    overall_risk: MigrationRisk
    readiness_score: float             # 0–100 across all roles
    phases: Dict[int, List[MigrationTask]]
    critical_path_tasks: List[str]     # task_ids on critical path
    risks: List[Dict]
    assumptions: List[str]
    summary: str

    def to_dict(self) -> dict:
        return {
            "total_roles": self.total_roles,
            "total_effort_days": self.total_effort_days,
            "estimated_duration_weeks": round(self.estimated_duration_weeks, 1),
            "overall_risk": self.overall_risk.value,
            "readiness_score": round(self.readiness_score, 1),
            "phases": {
                str(phase): [t.to_dict() for t in tasks]
                for phase, tasks in self.phases.items()
            },
            "critical_path_tasks": self.critical_path_tasks,
            "risks": self.risks,
            "assumptions": self.assumptions,
            "summary": self.summary,
        }


# =============================================================================
# Knowledge Base
# =============================================================================

# ---------------------------------------------------------------------------
# Fiori App Catalog
# ---------------------------------------------------------------------------

FIORI_APP_CATALOG: Dict[str, FioriApp] = {
    "F0842": FioriApp(
        app_id="F0842",
        name="Post General Journal Entries",
        description="Create general ledger journal entries in S/4HANA",
        catalog="SAP_FIN_BC_GL_POSTING",
        semantic_object="FinancialDocument",
        action="create",
        replaces_tcodes=["FB01", "FB50"],
        required_auth_objects=["F_BKPF_BUK", "F_BKPF_KOA", "F_BKPF_GSB"],
        business_process="Finance",
    ),
    "F0859": FioriApp(
        app_id="F0859",
        name="Manage Supplier Invoices",
        description="Process and manage supplier invoices",
        catalog="SAP_MM_BC_PO_INVOICE",
        semantic_object="SupplierInvoice",
        action="manage",
        replaces_tcodes=["MIRO", "MIR7"],
        required_auth_objects=["F_BKPF_BUK", "M_RECH_BWA", "M_RECH_WRK"],
        business_process="Procurement",
    ),
    "F2229": FioriApp(
        app_id="F2229",
        name="Create Purchase Orders",
        description="Create and manage purchase orders",
        catalog="SAP_MM_BC_PO_CREATE",
        semantic_object="PurchaseOrder",
        action="create",
        replaces_tcodes=["ME21N"],
        required_auth_objects=["M_BEST_BSA", "M_BEST_EKG", "M_BEST_EKO", "M_BEST_WRK"],
        business_process="Procurement",
    ),
    "F0797": FioriApp(
        app_id="F0797",
        name="Manage Business Partners",
        description="Create and maintain business partners (replaces FK01/XK01/VD01)",
        catalog="SAP_MM_BC_BP_MANAGE",
        semantic_object="BusinessPartner",
        action="manage",
        replaces_tcodes=["FK01", "FK02", "XK01", "XK02", "VD01", "VD02"],
        required_auth_objects=["B_BUPA_RLT", "B_BUPA_GRP", "V_KNA1_VKO"],
        business_process="Master Data",
    ),
    "F1366": FioriApp(
        app_id="F1366",
        name="Manage Sales Orders",
        description="Create and manage customer sales orders",
        catalog="SAP_SD_BC_SO_MANAGE",
        semantic_object="SalesOrder",
        action="manage",
        replaces_tcodes=["VA01", "VA02", "VA03"],
        required_auth_objects=["V_VBAK_AAT", "V_VBAK_VKO"],
        business_process="Sales",
    ),
    "F0971": FioriApp(
        app_id="F0971",
        name="Post Goods Movement",
        description="Post goods receipts, issues and transfers",
        catalog="SAP_MM_BC_GR_POST",
        semantic_object="GoodsMovement",
        action="create",
        replaces_tcodes=["MB01", "MIGO", "MB1A", "MB1C"],
        required_auth_objects=["M_MSEG_BWA", "M_MSEG_WMB", "M_MSEG_WRK"],
        business_process="Inventory",
    ),
    "F0560": FioriApp(
        app_id="F0560",
        name="Approve Purchase Orders",
        description="Approve pending purchase orders",
        catalog="SAP_MM_BC_PO_APPROVE",
        semantic_object="PurchaseOrder",
        action="approve",
        replaces_tcodes=["ME28"],
        required_auth_objects=["M_BEST_BSA", "M_BEST_EKG"],
        business_process="Procurement",
    ),
    "F1534": FioriApp(
        app_id="F1534",
        name="Create Supplier",
        description="Create new supplier via Business Partner framework",
        catalog="SAP_MM_BC_BP_SUPPLIER",
        semantic_object="Supplier",
        action="create",
        replaces_tcodes=["MK01", "XK01"],
        required_auth_objects=["B_BUPA_RLT", "LFM1"],
        business_process="Master Data",
    ),
    "F2680": FioriApp(
        app_id="F2680",
        name="Manage Credit Accounts",
        description="View and manage customer credit limits",
        catalog="SAP_SD_BC_CREDIT_MANAGE",
        semantic_object="CreditAccount",
        action="manage",
        replaces_tcodes=["FD32", "FD33"],
        required_auth_objects=["F_KNKK_BUK", "F_KNKK_KKB"],
        business_process="Finance",
    ),
    "F3009": FioriApp(
        app_id="F3009",
        name="Manage Fixed Assets",
        description="Create, change and retire fixed assets",
        catalog="SAP_FIN_BC_AA_MANAGE",
        semantic_object="FixedAsset",
        action="manage",
        replaces_tcodes=["AS01", "AS02", "AS03", "ABAVN"],
        required_auth_objects=["A_ANLKL", "A_KOSTL"],
        business_process="Asset Accounting",
    ),
    "F0718": FioriApp(
        app_id="F0718",
        name="My Inbox",
        description="Unified approval inbox for workflow items",
        catalog="SAP_BASIS_BC_WF_INBOX",
        semantic_object="WorkflowTask",
        action="DisplayMyInbox",
        replaces_tcodes=["SWIA", "SBWP"],
        required_auth_objects=["S_TCODE", "W_WI_OBJ"],
        business_process="Workflow",
    ),
    "F1465": FioriApp(
        app_id="F1465",
        name="Manage Journal Entries",
        description="Review, post and reverse general ledger postings",
        catalog="SAP_FIN_BC_GL_MANAGE",
        semantic_object="JournalEntry",
        action="manage",
        replaces_tcodes=["FB03", "FBL3N", "FBRA"],
        required_auth_objects=["F_BKPF_BUK", "F_BKPF_KOA"],
        business_process="Finance",
    ),
    "F2336": FioriApp(
        app_id="F2336",
        name="Run Depreciation",
        description="Execute planned depreciation runs",
        catalog="SAP_FIN_BC_AA_DEPR",
        semantic_object="Depreciation",
        action="run",
        replaces_tcodes=["AFAB"],
        required_auth_objects=["A_ANLKL", "F_BKPF_BUK"],
        business_process="Asset Accounting",
    ),
    "F0735": FioriApp(
        app_id="F0735",
        name="Manage Bank Statements",
        description="Import and process electronic bank statements",
        catalog="SAP_FIN_BC_BANK_STMT",
        semantic_object="BankStatement",
        action="manage",
        replaces_tcodes=["FF_5", "FEBAN"],
        required_auth_objects=["F_T012_BUK", "F_BKPF_BUK"],
        business_process="Treasury",
    ),
    "F2302": FioriApp(
        app_id="F2302",
        name="Display Financial Statements",
        description="View balance sheet, P&L and trial balance",
        catalog="SAP_FIN_BC_FS_DISPLAY",
        semantic_object="FinancialStatement",
        action="display",
        replaces_tcodes=["F.01", "S_ALR_87012284"],
        required_auth_objects=["F_BKPF_BUK", "F_FAGLFLEXT"],
        business_process="Finance",
    ),
}


# ---------------------------------------------------------------------------
# Transaction Mapping Knowledge Base — hardcoded seed data (50+ mappings)
# ---------------------------------------------------------------------------
# These definitions are used ONLY to seed the DB on first run.
# At runtime TRANSACTION_MAPPING is populated from the database via
# _ensure_loaded(), so edits here take effect only on a fresh/empty DB.

_TRANSACTION_MAPPING_SEED: Dict[str, TransactionMapping] = {

    # --- Finance (FI) ---
    "FB01": TransactionMapping("FB01", None, MigrationStatus.FIORI_ONLY,
        fiori_app_ids=["F0842"],
        notes="Replaced by Fiori app F0842 'Post General Journal Entries'",
        business_process="Finance", risk=MigrationRisk.MEDIUM),
    "FB50": TransactionMapping("FB50", None, MigrationStatus.FIORI_ONLY,
        fiori_app_ids=["F0842"],
        notes="G/L account document entry replaced by F0842",
        business_process="Finance", risk=MigrationRisk.MEDIUM),
    "FB03": TransactionMapping("FB03", None, MigrationStatus.FIORI_ONLY,
        fiori_app_ids=["F1465"],
        notes="Document display replaced by F1465 'Manage Journal Entries'",
        business_process="Finance", risk=MigrationRisk.LOW),
    "FBL3N": TransactionMapping("FBL3N", "FAGLB03", MigrationStatus.REPLACED,
        fiori_app_ids=["F1465"],
        notes="Use FAGLB03 or Fiori F1465. New Universal Journal (ACDOCA) changes line item reporting.",
        business_process="Finance", risk=MigrationRisk.HIGH),
    "FBL1N": TransactionMapping("FBL1N", "FBL1N", MigrationStatus.COMPATIBLE,
        notes="Compatible. Some field behavior changes with new data model.",
        business_process="Finance", risk=MigrationRisk.LOW),
    "FBL5N": TransactionMapping("FBL5N", "FBL5N", MigrationStatus.COMPATIBLE,
        notes="Compatible. Customer line items.",
        business_process="Finance", risk=MigrationRisk.LOW),
    "FBRA": TransactionMapping("FBRA", None, MigrationStatus.FIORI_ONLY,
        fiori_app_ids=["F1465"],
        notes="Document reversal via F1465",
        business_process="Finance", risk=MigrationRisk.MEDIUM),
    "F.01": TransactionMapping("F.01", None, MigrationStatus.FIORI_ONLY,
        fiori_app_ids=["F2302"],
        notes="Financial statements via Fiori F2302",
        business_process="Finance", risk=MigrationRisk.MEDIUM),
    "FD32": TransactionMapping("FD32", None, MigrationStatus.FIORI_ONLY,
        fiori_app_ids=["F2680"],
        notes="Credit master replaced by Fiori F2680 'Manage Credit Accounts'",
        business_process="Finance", risk=MigrationRisk.MEDIUM),
    "FD33": TransactionMapping("FD33", None, MigrationStatus.FIORI_ONLY,
        fiori_app_ids=["F2680"],
        notes="Credit display replaced by Fiori F2680",
        business_process="Finance", risk=MigrationRisk.LOW),
    "FF_5": TransactionMapping("FF_5", None, MigrationStatus.FIORI_ONLY,
        fiori_app_ids=["F0735"],
        notes="Bank statement import via Fiori F0735",
        business_process="Treasury", risk=MigrationRisk.MEDIUM),
    "FEBAN": TransactionMapping("FEBAN", None, MigrationStatus.FIORI_ONLY,
        fiori_app_ids=["F0735"],
        notes="Bank statement processing via Fiori F0735",
        business_process="Treasury", risk=MigrationRisk.MEDIUM),
    "F110": TransactionMapping("F110", "F110", MigrationStatus.COMPATIBLE,
        notes="Payment run compatible. SEPA mandate handling changed.",
        business_process="Finance", risk=MigrationRisk.LOW),
    "MIRO": TransactionMapping("MIRO", None, MigrationStatus.FIORI_ONLY,
        fiori_app_ids=["F0859"],
        notes="Supplier invoice posting replaced by Fiori F0859",
        business_process="Procurement", risk=MigrationRisk.HIGH),
    "MIR7": TransactionMapping("MIR7", None, MigrationStatus.FIORI_ONLY,
        fiori_app_ids=["F0859"],
        notes="Park invoice replaced by Fiori F0859",
        business_process="Procurement", risk=MigrationRisk.MEDIUM),

    # --- Procurement (MM/P2P) ---
    "ME21N": TransactionMapping("ME21N", "ME21N", MigrationStatus.COMPATIBLE,
        fiori_app_ids=["F2229"],
        notes="Compatible. Fiori F2229 is the preferred UX. Auth objects unchanged.",
        business_process="Procurement", risk=MigrationRisk.LOW),
    "ME22N": TransactionMapping("ME22N", "ME22N", MigrationStatus.COMPATIBLE,
        notes="Purchase order change. Compatible.",
        business_process="Procurement", risk=MigrationRisk.LOW),
    "ME23N": TransactionMapping("ME23N", "ME23N", MigrationStatus.COMPATIBLE,
        notes="Purchase order display. Compatible.",
        business_process="Procurement", risk=MigrationRisk.LOW),
    "ME28": TransactionMapping("ME28", None, MigrationStatus.FIORI_ONLY,
        fiori_app_ids=["F0560"],
        notes="PO approval replaced by Fiori F0560 'Approve Purchase Orders'",
        business_process="Procurement", risk=MigrationRisk.MEDIUM),
    "ME51N": TransactionMapping("ME51N", "ME51N", MigrationStatus.COMPATIBLE,
        notes="Purchase requisition. Compatible.",
        business_process="Procurement", risk=MigrationRisk.LOW),
    "ME52N": TransactionMapping("ME52N", "ME52N", MigrationStatus.COMPATIBLE,
        notes="PR change. Compatible.",
        business_process="Procurement", risk=MigrationRisk.LOW),
    "MK01": TransactionMapping("MK01", "BP", MigrationStatus.REPLACED,
        fiori_app_ids=["F1534"],
        notes="Vendor master replaced by Business Partner (BP transaction / Fiori F1534). "
              "Full BP data model migration required.",
        business_process="Master Data", risk=MigrationRisk.CRITICAL),
    "MK02": TransactionMapping("MK02", "BP", MigrationStatus.REPLACED,
        fiori_app_ids=["F1534"],
        notes="Vendor change replaced by BP",
        business_process="Master Data", risk=MigrationRisk.HIGH),
    "XK01": TransactionMapping("XK01", "BP", MigrationStatus.REPLACED,
        fiori_app_ids=["F1534", "F0797"],
        notes="Central vendor create replaced by Business Partner (BP)",
        business_process="Master Data", risk=MigrationRisk.CRITICAL),
    "XK02": TransactionMapping("XK02", "BP", MigrationStatus.REPLACED,
        fiori_app_ids=["F0797"],
        notes="Central vendor change replaced by BP",
        business_process="Master Data", risk=MigrationRisk.HIGH),

    # --- Sales (SD/O2C) ---
    "VA01": TransactionMapping("VA01", "VA01", MigrationStatus.COMPATIBLE,
        fiori_app_ids=["F1366"],
        notes="Sales order creation. Tcode compatible; Fiori F1366 preferred.",
        business_process="Sales", risk=MigrationRisk.LOW),
    "VA02": TransactionMapping("VA02", "VA02", MigrationStatus.COMPATIBLE,
        fiori_app_ids=["F1366"],
        notes="Sales order change. Compatible.",
        business_process="Sales", risk=MigrationRisk.LOW),
    "VA03": TransactionMapping("VA03", "VA03", MigrationStatus.COMPATIBLE,
        fiori_app_ids=["F1366"],
        notes="Sales order display. Compatible.",
        business_process="Sales", risk=MigrationRisk.LOW),
    "VF01": TransactionMapping("VF01", "VF01", MigrationStatus.COMPATIBLE,
        notes="Billing document creation. Compatible.",
        business_process="Sales", risk=MigrationRisk.LOW),
    "VF02": TransactionMapping("VF02", "VF02", MigrationStatus.COMPATIBLE,
        notes="Billing document change. Compatible.",
        business_process="Sales", risk=MigrationRisk.LOW),
    "VD01": TransactionMapping("VD01", "BP", MigrationStatus.REPLACED,
        fiori_app_ids=["F0797"],
        notes="Customer master (sales area) replaced by Business Partner",
        business_process="Master Data", risk=MigrationRisk.CRITICAL),
    "VD02": TransactionMapping("VD02", "BP", MigrationStatus.REPLACED,
        fiori_app_ids=["F0797"],
        notes="Customer change replaced by BP",
        business_process="Master Data", risk=MigrationRisk.HIGH),
    "XD01": TransactionMapping("XD01", "BP", MigrationStatus.REPLACED,
        fiori_app_ids=["F0797"],
        notes="Central customer create replaced by Business Partner",
        business_process="Master Data", risk=MigrationRisk.CRITICAL),

    # --- Inventory Management ---
    "MB01": TransactionMapping("MB01", "MIGO", MigrationStatus.REPLACED,
        fiori_app_ids=["F0971"],
        notes="Goods receipt replaced by MIGO or Fiori F0971",
        business_process="Inventory", risk=MigrationRisk.MEDIUM),
    "MIGO": TransactionMapping("MIGO", "MIGO", MigrationStatus.COMPATIBLE,
        fiori_app_ids=["F0971"],
        notes="Goods movements. Compatible. Fiori F0971 is preferred UX.",
        business_process="Inventory", risk=MigrationRisk.LOW),
    "MB1A": TransactionMapping("MB1A", "MIGO", MigrationStatus.REPLACED,
        fiori_app_ids=["F0971"],
        notes="Goods issue replaced by MIGO/F0971",
        business_process="Inventory", risk=MigrationRisk.MEDIUM),
    "MB1C": TransactionMapping("MB1C", "MIGO", MigrationStatus.REPLACED,
        fiori_app_ids=["F0971"],
        notes="Other goods receipt replaced by MIGO/F0971",
        business_process="Inventory", risk=MigrationRisk.MEDIUM),
    "MB52": TransactionMapping("MB52", "MB52", MigrationStatus.COMPATIBLE,
        notes="Warehouse stocks. Compatible.",
        business_process="Inventory", risk=MigrationRisk.LOW),

    # --- Asset Accounting ---
    "AS01": TransactionMapping("AS01", None, MigrationStatus.FIORI_ONLY,
        fiori_app_ids=["F3009"],
        notes="Asset creation via Fiori F3009 'Manage Fixed Assets'. "
              "New Asset Accounting (FI-AA) is mandatory in S/4HANA.",
        business_process="Asset Accounting", risk=MigrationRisk.HIGH),
    "AS02": TransactionMapping("AS02", None, MigrationStatus.FIORI_ONLY,
        fiori_app_ids=["F3009"],
        notes="Asset change via Fiori F3009",
        business_process="Asset Accounting", risk=MigrationRisk.MEDIUM),
    "AS03": TransactionMapping("AS03", None, MigrationStatus.FIORI_ONLY,
        fiori_app_ids=["F3009"],
        notes="Asset display via Fiori F3009",
        business_process="Asset Accounting", risk=MigrationRisk.LOW),
    "AFAB": TransactionMapping("AFAB", None, MigrationStatus.FIORI_ONLY,
        fiori_app_ids=["F2336"],
        notes="Depreciation run via Fiori F2336. New AA posting logic applies.",
        business_process="Asset Accounting", risk=MigrationRisk.HIGH),
    "ABAVN": TransactionMapping("ABAVN", None, MigrationStatus.FIORI_ONLY,
        fiori_app_ids=["F3009"],
        notes="Asset retirement via Fiori F3009",
        business_process="Asset Accounting", risk=MigrationRisk.MEDIUM),

    # --- Master Data ---
    "FK01": TransactionMapping("FK01", "BP", MigrationStatus.REPLACED,
        fiori_app_ids=["F0797"],
        notes="FI vendor create replaced by Business Partner (BP). "
              "Simplification item SI-FIN-M-00001.",
        business_process="Master Data", risk=MigrationRisk.CRITICAL),
    "FK02": TransactionMapping("FK02", "BP", MigrationStatus.REPLACED,
        fiori_app_ids=["F0797"],
        notes="FI vendor change replaced by BP",
        business_process="Master Data", risk=MigrationRisk.HIGH),
    "FD01": TransactionMapping("FD01", "BP", MigrationStatus.REPLACED,
        fiori_app_ids=["F0797"],
        notes="FI customer create replaced by Business Partner (BP). "
              "Simplification item SI-FIN-M-00001.",
        business_process="Master Data", risk=MigrationRisk.CRITICAL),
    "FD02": TransactionMapping("FD02", "BP", MigrationStatus.REPLACED,
        fiori_app_ids=["F0797"],
        notes="FI customer change replaced by BP",
        business_process="Master Data", risk=MigrationRisk.HIGH),
    "BP": TransactionMapping("BP", "BP", MigrationStatus.NEW,
        fiori_app_ids=["F0797"],
        notes="Business Partner: new master data concept in S/4HANA combining "
              "customer and vendor. Requires new auth object B_BUPA_RLT.",
        business_process="Master Data", risk=MigrationRisk.MEDIUM),

    # --- Basis / Security ---
    "SU01": TransactionMapping("SU01", "SU01", MigrationStatus.COMPATIBLE,
        notes="User maintenance. Compatible. Identity Governance integration recommended.",
        business_process="Basis", risk=MigrationRisk.LOW),
    "SU10": TransactionMapping("SU10", "SU10", MigrationStatus.COMPATIBLE,
        notes="Mass user changes. Compatible.",
        business_process="Basis", risk=MigrationRisk.LOW),
    "PFCG": TransactionMapping("PFCG", "PFCG", MigrationStatus.COMPATIBLE,
        notes="Role maintenance. Compatible. New auth objects for S/4HANA features needed.",
        business_process="Basis", risk=MigrationRisk.LOW),
    "SE16N": TransactionMapping("SE16N", "SE16N", MigrationStatus.COMPATIBLE,
        notes="Table browser. Compatible. New tables (ACDOCA, etc.) available.",
        business_process="Basis", risk=MigrationRisk.LOW),
    "SM30": TransactionMapping("SM30", "SM30", MigrationStatus.COMPATIBLE,
        notes="Table maintenance. Compatible.",
        business_process="Basis", risk=MigrationRisk.LOW),

    # --- Workflow ---
    "SWIA": TransactionMapping("SWIA", None, MigrationStatus.FIORI_ONLY,
        fiori_app_ids=["F0718"],
        notes="Workflow inbox replaced by Fiori F0718 'My Inbox'",
        business_process="Workflow", risk=MigrationRisk.MEDIUM),
    "SBWP": TransactionMapping("SBWP", None, MigrationStatus.FIORI_ONLY,
        fiori_app_ids=["F0718"],
        notes="Business Workplace replaced by Fiori F0718",
        business_process="Workflow", risk=MigrationRisk.MEDIUM),

    # --- HR (if HCM on-prem) ---
    "PA30": TransactionMapping("PA30", "PA30", MigrationStatus.COMPATIBLE,
        notes="HR master data. Compatible if HCM on-prem. SuccessFactors integration changes scope.",
        business_process="HR", risk=MigrationRisk.LOW),
    "PA40": TransactionMapping("PA40", "PA40", MigrationStatus.COMPATIBLE,
        notes="Personnel actions. Compatible with HCM on-prem.",
        business_process="HR", risk=MigrationRisk.LOW),
}

# ---------------------------------------------------------------------------
# Runtime cache — populated from DB by _ensure_loaded()
# ---------------------------------------------------------------------------

TRANSACTION_MAPPING: Dict[str, TransactionMapping] = {}
_mapping_loaded: bool = False


def _ensure_loaded() -> None:
    """
    Populate TRANSACTION_MAPPING from the database on first access.

    If the migration_mappings table is empty, seeds it from the hardcoded
    _TRANSACTION_MAPPING_SEED dict so the engine works out of the box on a
    fresh deployment.  Subsequent calls are no-ops (flag guard).
    """
    global _mapping_loaded
    if _mapping_loaded:
        return

    try:
        if not db_manager._initialized:
            db_manager.init()

        with db_manager.session_scope() as session:
            count = session.query(MigrationMapping).count()

            if count == 0:
                # Seed DB from hardcoded definitions
                logger.info(
                    "migration_mappings table is empty — seeding %d records from built-in knowledge base",
                    len(_TRANSACTION_MAPPING_SEED),
                )
                for tcode, mapping in _TRANSACTION_MAPPING_SEED.items():
                    record = MigrationMapping(
                        tenant_id="tenant_default",
                        ecc_tcode=mapping.ecc_tcode,
                        s4_tcode=mapping.s4_tcode,
                        status=mapping.status.value,
                        fiori_app_ids=mapping.fiori_app_ids,
                        notes=mapping.notes,
                        business_process=mapping.business_process,
                        risk_level=mapping.risk.value,
                    )
                    session.add(record)
                # session_scope auto-commits on exit

            # Re-query (covers both the seed path and an already-populated DB)
            rows = session.query(MigrationMapping).all()

        for row in rows:
            try:
                status = MigrationStatus(row.status)
            except ValueError:
                status = MigrationStatus.COMPATIBLE

            try:
                risk = MigrationRisk(row.risk_level or "low")
            except ValueError:
                risk = MigrationRisk.LOW

            TRANSACTION_MAPPING[row.ecc_tcode.upper()] = TransactionMapping(
                ecc_tcode=row.ecc_tcode,
                s4_tcode=row.s4_tcode,
                status=status,
                fiori_app_ids=row.fiori_app_ids or [],
                notes=row.notes or "",
                business_process=row.business_process or "",
                risk=risk,
            )

        _mapping_loaded = True
        logger.debug("TRANSACTION_MAPPING loaded: %d entries from DB", len(TRANSACTION_MAPPING))

    except Exception as exc:
        logger.warning(
            "Could not load TRANSACTION_MAPPING from DB (%s); falling back to seed data.",
            exc,
        )
        # Fallback: use the hardcoded seed so the engine stays functional
        TRANSACTION_MAPPING.update(_TRANSACTION_MAPPING_SEED)
        _mapping_loaded = True


# ---------------------------------------------------------------------------
# Obsolete Transactions (20+)
# ---------------------------------------------------------------------------

OBSOLETE_TRANSACTIONS: Dict[str, Dict] = {
    "FBN1": {
        "tcode": "FBN1",
        "description": "Number ranges for accounting documents",
        "reason": "Managed automatically in S/4HANA via customizing. Manual number range assignment obsolete.",
        "business_process": "Finance",
        "simplification_item": "SI-FIN-GL-00003",
    },
    "FK10N": {
        "tcode": "FK10N",
        "description": "Vendor balance display",
        "reason": "Replaced by Universal Journal reports and Fiori analytics.",
        "business_process": "Finance",
        "simplification_item": "SI-FIN-M-00002",
    },
    "FD10N": {
        "tcode": "FD10N",
        "description": "Customer balance display",
        "reason": "Replaced by Universal Journal reports.",
        "business_process": "Finance",
        "simplification_item": "SI-FIN-M-00002",
    },
    "FAGLL03": {
        "tcode": "FAGLL03",
        "description": "G/L account line item display (new GL)",
        "reason": "Merged into FAGLB03 and Universal Journal (ACDOCA) reporting.",
        "business_process": "Finance",
        "simplification_item": "SI-FIN-GL-00001",
    },
    "FAGL_FC_VAL": {
        "tcode": "FAGL_FC_VAL",
        "description": "Foreign currency valuation (old program)",
        "reason": "Replaced by new valuation program FAGL_FC_TRANS in S/4HANA.",
        "business_process": "Finance",
        "simplification_item": "SI-FIN-GL-00007",
    },
    "MB31": {
        "tcode": "MB31",
        "description": "Goods receipt for production order (separate tcode)",
        "reason": "Merged into MIGO. MB31 no longer available as separate transaction.",
        "business_process": "Inventory",
        "simplification_item": "SI-MM-IM-00004",
    },
    "MBGR": {
        "tcode": "MBGR",
        "description": "Display goods movements by reason",
        "reason": "Obsolete. Use Material Documents List (MB51).",
        "business_process": "Inventory",
        "simplification_item": "SI-MM-IM-00005",
    },
    "OMB1": {
        "tcode": "OMB1",
        "description": "Inventory management parameters (old)",
        "reason": "Configuration moved to new Customizing path in S/4HANA.",
        "business_process": "Inventory",
        "simplification_item": "SI-MM-IM-00001",
    },
    "CKMVFM": {
        "tcode": "CKMVFM",
        "description": "Material ledger — valuated material flow (old)",
        "reason": "Material ledger is now mandatory in S/4HANA. Different reporting path.",
        "business_process": "Controlling",
        "simplification_item": "SI-CO-ML-00001",
    },
    "CO43": {
        "tcode": "CO43",
        "description": "Actual overhead calculation (separate)",
        "reason": "Overhead calculation integrated into universal journal postings.",
        "business_process": "Controlling",
        "simplification_item": "SI-CO-OC-00001",
    },
    "F-22": {
        "tcode": "F-22",
        "description": "Enter customer invoice (enjoy obsolete form)",
        "reason": "Obsolete Enjoy transaction. Use FB70 or Fiori F0842.",
        "business_process": "Finance",
        "simplification_item": "SI-FIN-AR-00001",
    },
    "F-43": {
        "tcode": "F-43",
        "description": "Enter vendor invoice (classic)",
        "reason": "Obsolete. Use FB60 or Fiori F0859.",
        "business_process": "Finance",
        "simplification_item": "SI-FIN-AP-00001",
    },
    "LSMW": {
        "tcode": "LSMW",
        "description": "Legacy System Migration Workbench",
        "reason": "Replaced by SAP Migration Cockpit for S/4HANA data migration.",
        "business_process": "Basis",
        "simplification_item": "SI-BC-DM-00001",
    },
    "SM35": {
        "tcode": "SM35",
        "description": "Batch Input Monitoring",
        "reason": "Reduced relevance; many programs replaced by direct APIs/IDocs.",
        "business_process": "Basis",
        "simplification_item": "SI-BC-BI-00001",
    },
    "OAAQ": {
        "tcode": "OAAQ",
        "description": "Asset Accounting — fiscal year closed",
        "reason": "New Asset Accounting uses different year-close procedure.",
        "business_process": "Asset Accounting",
        "simplification_item": "SI-FIN-AA-00002",
    },
    "OABZ": {
        "tcode": "OABZ",
        "description": "Transfer old asset data",
        "reason": "Old asset transfer obsolete. Use migration tools for S/4HANA AA.",
        "business_process": "Asset Accounting",
        "simplification_item": "SI-FIN-AA-00003",
    },
    "VKM1": {
        "tcode": "VKM1",
        "description": "Blocked SD documents — old credit management",
        "reason": "Replaced by SAP Credit Management (FSCM) which is the default in S/4HANA.",
        "business_process": "Sales",
        "simplification_item": "SI-SD-CM-00001",
    },
    "F.28": {
        "tcode": "F.28",
        "description": "Customers: Reset credit limit",
        "reason": "Old credit management program. Use FSCM Credit Management.",
        "business_process": "Finance",
        "simplification_item": "SI-SD-CM-00002",
    },
    "MM60": {
        "tcode": "MM60",
        "description": "Goods movements: statistics (old report)",
        "reason": "Replaced by Embedded Analytics / CDS view-based reports.",
        "business_process": "Inventory",
        "simplification_item": "SI-MM-IM-00006",
    },
    "MCBE": {
        "tcode": "MCBE",
        "description": "Plant analysis — LIS report",
        "reason": "Logistics Information System (LIS) is obsolete. Use Embedded Analytics.",
        "business_process": "Inventory",
        "simplification_item": "SI-MM-LIS-00001",
    },
    "MC.9": {
        "tcode": "MC.9",
        "description": "SIS: Customer analysis — LIS",
        "reason": "LIS Sales Information System replaced by Embedded Analytics / SAP Analytics Cloud.",
        "business_process": "Sales",
        "simplification_item": "SI-SD-LIS-00001",
    },
}


# ---------------------------------------------------------------------------
# Authorization Object Changes Knowledge Base (15+ entries)
# ---------------------------------------------------------------------------

AUTH_OBJECT_CHANGES: Dict[str, AuthObjectChange] = {

    # New objects introduced in S/4HANA
    "B_BUPA_RLT": AuthObjectChange(
        object_name="B_BUPA_RLT",
        change_type=AuthChangeType.NEW,
        ecc_description=None,
        s4_description="Business Partner: BP Roles",
        affected_fields=["BPROL", "ACTVT"],
        notes="Mandatory for Business Partner access. Required because vendor/customer "
              "master moved to BP framework. All roles using FK01/XK01/VD01/FD01 need this.",
        business_process="Master Data",
    ),
    "B_BUPA_GRP": AuthObjectChange(
        object_name="B_BUPA_GRP",
        change_type=AuthChangeType.NEW,
        ecc_description=None,
        s4_description="Business Partner: BP Grouping",
        affected_fields=["BPGRP", "ACTVT"],
        notes="Controls which BP groups a user can maintain. New in S/4HANA BP framework.",
        business_process="Master Data",
    ),
    "B_BUPA_ATT": AuthObjectChange(
        object_name="B_BUPA_ATT",
        change_type=AuthChangeType.NEW,
        ecc_description=None,
        s4_description="Business Partner: Authorization Type",
        affected_fields=["BPKIND", "ACTVT"],
        notes="Controls BP authorization categories (natural person, organization, group).",
        business_process="Master Data",
    ),
    "F_FAGLFLEXT": AuthObjectChange(
        object_name="F_FAGLFLEXT",
        change_type=AuthChangeType.NEW,
        ecc_description=None,
        s4_description="G/L Accounting: Authorization for Totals Tables",
        affected_fields=["RRCTY", "RVERS", "RBUKRS", "RYEAR", "ACTVT"],
        notes="New in S/4HANA New General Ledger. Required for financial statement and "
              "balance display reports using Universal Journal.",
        business_process="Finance",
    ),
    "F_ACDOCA": AuthObjectChange(
        object_name="F_ACDOCA",
        change_type=AuthChangeType.NEW,
        ecc_description=None,
        s4_description="Universal Journal: Authorization for ACDOCA Table",
        affected_fields=["RBUKRS", "RACCT", "ACTVT"],
        notes="Controls access to the Universal Journal (ACDOCA) which replaces multiple "
              "legacy tables. Critical for all financial reporting authorizations.",
        business_process="Finance",
    ),
    "S_FIORI_APP": AuthObjectChange(
        object_name="S_FIORI_APP",
        change_type=AuthChangeType.NEW,
        ecc_description=None,
        s4_description="Fiori Application Authorization",
        affected_fields=["APPID", "ACTVT"],
        notes="Controls which Fiori apps a user can launch. Required for all users "
              "accessing the Fiori launchpad. One of the most impactful new objects.",
        business_process="Basis",
    ),
    "S_START": AuthObjectChange(
        object_name="S_START",
        change_type=AuthChangeType.NEW,
        ecc_description=None,
        s4_description="Starting Objects of an ABAP Application Server Service",
        affected_fields=["OBJECT", "PROGRAM"],
        notes="Controls service and OData endpoint access. Required for Fiori app backends.",
        business_process="Basis",
    ),
    "S_ODP_READ": AuthObjectChange(
        object_name="S_ODP_READ",
        change_type=AuthChangeType.NEW,
        ecc_description=None,
        s4_description="Operational Data Provisioning: Authorization for ODP",
        affected_fields=["ODPNAME", "ODPTYPE", "ACTVT"],
        notes="Required for Embedded Analytics and CDS-based reporting. New in S/4HANA.",
        business_process="Analytics",
    ),
    "C_AFVC_CMF": AuthObjectChange(
        object_name="C_AFVC_CMF",
        change_type=AuthChangeType.NEW,
        ecc_description=None,
        s4_description="PM/PP: Confirmation of Operation in Order",
        affected_fields=["ACTVT", "WERKS"],
        notes="New authorization concept for production/maintenance confirmations in S/4HANA.",
        business_process="Manufacturing",
    ),
    "P_NNNNN": AuthObjectChange(
        object_name="P_TRAVL",
        change_type=AuthChangeType.NEW,
        ecc_description=None,
        s4_description="Travel Management: Personnel Area for Travel",
        affected_fields=["PERSA", "ACTVT"],
        notes="New auth object for S/4HANA Travel Management if travel module is active.",
        business_process="HR",
    ),

    # Deprecated objects
    "F_BSEG_VAR": AuthObjectChange(
        object_name="F_BSEG_VAR",
        change_type=AuthChangeType.DEPRECATED,
        ecc_description="FI: Document Field Variants Authorization",
        s4_description=None,
        affected_fields=["F_BSEG_VAR"],
        notes="BSEG table is no longer the primary FI table. Replaced by ACDOCA-based "
              "controls. Remove from roles after migration.",
        business_process="Finance",
    ),
    "K_CSKS_KOS": AuthObjectChange(
        object_name="K_CSKS_KOS",
        change_type=AuthChangeType.DEPRECATED,
        ecc_description="CO: Cost Center — Actual Line Item Display (KOLS)",
        s4_description=None,
        affected_fields=["KOSTL", "KOKRS", "ACTVT"],
        notes="Old cost center line item report authorization. Replaced by Universal "
              "Journal reporting auth objects.",
        business_process="Controlling",
    ),
    "V_LIKP_VST": AuthObjectChange(
        object_name="V_LIKP_VST",
        change_type=AuthChangeType.DEPRECATED,
        ecc_description="SD: Delivery — Shipping Point",
        s4_description=None,
        affected_fields=["VSTEL", "ACTVT"],
        notes="Partially deprecated. Extended Transportation Management (eTM) uses "
              "different authorization concept. Validate before removing.",
        business_process="Sales",
    ),
    "S_BDS_DS": AuthObjectChange(
        object_name="S_BDS_DS",
        change_type=AuthChangeType.DEPRECATED,
        ecc_description="Business Document Service: Document Set",
        s4_description=None,
        affected_fields=["ACTVT"],
        notes="BDS replaced by S/4HANA Document Management. Object no longer evaluated.",
        business_process="Basis",
    ),

    # Changed objects
    "F_BKPF_BUK": AuthObjectChange(
        object_name="F_BKPF_BUK",
        change_type=AuthChangeType.CHANGED,
        ecc_description="FI: Accounting Document — Company Code",
        s4_description="FI: Accounting Document — Company Code (extended for Universal Journal)",
        affected_fields=["BUKRS", "ACTVT"],
        notes="Object remains but now gates access to Universal Journal (ACDOCA) postings. "
              "Activity values 'display' now covers ACDOCA read. Verify authorizations are correct.",
        business_process="Finance",
    ),
    "M_MSEG_BWA": AuthObjectChange(
        object_name="M_MSEG_BWA",
        change_type=AuthChangeType.CHANGED,
        ecc_description="MM: Goods Movement — Movement Type",
        s4_description="MM: Goods Movement — Movement Type (extended movement type catalog)",
        affected_fields=["BWART", "ACTVT"],
        notes="New movement types added in S/4HANA for inbound/outbound deliveries. "
              "Verify that allowed BWART values include S/4HANA-specific ones.",
        business_process="Inventory",
    ),
    "S_TCODE": AuthObjectChange(
        object_name="S_TCODE",
        change_type=AuthChangeType.CHANGED,
        ecc_description="Transaction Code Check at Transaction Start",
        s4_description="Transaction Code Check at Transaction Start (Fiori-aware)",
        affected_fields=["TCD"],
        notes="S_TCODE still evaluated for classic Dynpro tcodes. For Fiori apps, "
              "S_FIORI_APP is now the primary control. Roles mixing Fiori and classic "
              "access must include both objects.",
        business_process="Basis",
    ),
}


# ---------------------------------------------------------------------------
# Simplification Items Reference
# ---------------------------------------------------------------------------

SIMPLIFICATION_ITEMS: Dict[str, Dict] = {
    "SI-FIN-M-00001": {
        "id": "SI-FIN-M-00001",
        "title": "Business Partner as Successor for Customer/Vendor Integration",
        "description": "In S/4HANA, the Business Partner (BP) is the single master object "
                       "for customer and vendor. Transactions FK01, XK01, FD01, XD01, VD01 "
                       "are replaced by BP or deactivated.",
        "impact": "critical",
        "affected_tcodes": ["FK01", "FK02", "XK01", "XK02", "FD01", "FD02", "VD01", "VD02"],
    },
    "SI-FIN-GL-00001": {
        "id": "SI-FIN-GL-00001",
        "title": "Universal Journal (ACDOCA) Replaces Multiple Ledger Tables",
        "description": "BSEG, BSAD, BSAK, BSAS, BSID, BSIK, BSIS, FAGLFLEXA tables are "
                       "compatibility views in S/4HANA. ACDOCA is the single source of truth.",
        "impact": "high",
        "affected_tcodes": ["FBL3N", "FAGLL03", "FBL1N", "FBL5N"],
    },
    "SI-FIN-AA-00001": {
        "id": "SI-FIN-AA-00001",
        "title": "New Asset Accounting (FI-AA) is Mandatory",
        "description": "Classic Asset Accounting (based on ANLC/ANLA) is replaced. "
                       "New AA posts in real-time to Universal Journal. Migration of AA "
                       "data required before go-live.",
        "impact": "high",
        "affected_tcodes": ["AS01", "AS02", "AFAB", "OAAQ", "OABZ"],
    },
    "SI-MM-LIS-00001": {
        "id": "SI-MM-LIS-00001",
        "title": "Logistics Information System (LIS) Obsolete",
        "description": "LIS update tables (MCxx) are no longer updated. Reporting must "
                       "migrate to Embedded Analytics / CDS view-based solutions.",
        "impact": "medium",
        "affected_tcodes": ["MCBE", "MC.9", "MM60"],
    },
    "SI-SD-CM-00001": {
        "id": "SI-SD-CM-00001",
        "title": "Credit Management — FSCM is Default",
        "description": "SAP Credit Management (FSCM-CR) is now the default. Old SD credit "
                       "management (FI-AR-CR) is still available but deprecated.",
        "impact": "medium",
        "affected_tcodes": ["VKM1", "F.28"],
    },
    "SI-CO-ML-00001": {
        "id": "SI-CO-ML-00001",
        "title": "Material Ledger Mandatory",
        "description": "Material Ledger is mandatory in S/4HANA. Actual costing is available "
                       "but optional. All inventory postings go through ML.",
        "impact": "high",
        "affected_tcodes": ["CKMVFM"],
    },
}


# =============================================================================
# MigrationAnalyzer Engine
# =============================================================================

class MigrationAnalyzer:
    """
    SAP ECC to S/4HANA Migration Security Analyzer.

    Analyzes the security impact of migrating SAP roles and users from
    ECC 6.0 to S/4HANA using a comprehensive knowledge base of transaction
    mappings, authorization object changes, and Fiori app requirements.

    All role and user data is accepted as plain dicts so this engine can be
    driven from any source (DB query results, mock data, API payloads).
    """

    def __init__(self) -> None:
        _ensure_loaded()
        self.transaction_map = TRANSACTION_MAPPING
        self.obsolete = OBSOLETE_TRANSACTIONS
        self.auth_changes = AUTH_OBJECT_CHANGES
        self.fiori_catalog = FIORI_APP_CATALOG
        self.simplification_items = SIMPLIFICATION_ITEMS

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    def analyze_transactions(
        self,
        role_id: str,
        ecc_tcodes: List[str],
    ) -> TransactionImpact:
        """
        Map a set of ECC transaction codes to their S/4HANA status.

        Parameters
        ----------
        role_id:    Identifier for the role being analyzed.
        ecc_tcodes: List of ECC transaction codes assigned to the role.

        Returns
        -------
        TransactionImpact dataclass with categorized mappings and a
        compatibility percentage.
        """
        compatible: List[TransactionMapping] = []
        replaced: List[TransactionMapping] = []
        fiori_only: List[TransactionMapping] = []
        obsolete_list: List[TransactionMapping] = []
        changed: List[TransactionMapping] = []
        unknown: List[str] = []
        required_fiori_ids: set = set()

        for tcode in ecc_tcodes:
            mapping = self.transaction_map.get(tcode.upper())
            if mapping is None:
                # Not in knowledge base — flag for manual review
                unknown.append(tcode)
                continue

            for app_id in mapping.fiori_app_ids:
                required_fiori_ids.add(app_id)

            if mapping.status == MigrationStatus.COMPATIBLE:
                compatible.append(mapping)
            elif mapping.status == MigrationStatus.REPLACED:
                replaced.append(mapping)
            elif mapping.status == MigrationStatus.FIORI_ONLY:
                fiori_only.append(mapping)
            elif mapping.status == MigrationStatus.OBSOLETE:
                obsolete_list.append(mapping)
            elif mapping.status == MigrationStatus.CHANGED:
                changed.append(mapping)
            else:
                # NEW or unhandled
                compatible.append(mapping)

        total = len(ecc_tcodes)
        if total == 0:
            compat_pct = 100.0
        else:
            # compatible + changed (with review) count toward compatibility
            compat_pct = ((len(compatible) + len(changed)) / total) * 100.0

        problem_count = len(replaced) + len(fiori_only) + len(obsolete_list)
        if problem_count == 0:
            summary = f"All {total} transactions are compatible with S/4HANA."
        else:
            summary = (
                f"{len(compatible)} of {total} transactions are directly compatible. "
                f"{len(replaced)} require replacement, {len(fiori_only)} move to Fiori-only, "
                f"{len(obsolete_list)} are obsolete, {len(unknown)} are unrecognised."
            )

        return TransactionImpact(
            role_id=role_id,
            ecc_tcodes=ecc_tcodes,
            compatible=compatible,
            replaced=replaced,
            fiori_only=fiori_only,
            obsolete=obsolete_list,
            changed=changed,
            unknown=unknown,
            compatibility_pct=compat_pct,
            required_fiori_apps=sorted(required_fiori_ids),
            summary=summary,
        )

    def analyze_auth_changes(
        self,
        role_id: str,
        ecc_auth_objects: List[str],
    ) -> AuthChangeImpact:
        """
        Determine which authorization objects in a role are affected by the
        ECC -> S/4HANA migration.

        Parameters
        ----------
        role_id:           Role identifier.
        ecc_auth_objects:  Auth object names currently in the ECC role.

        Returns
        -------
        AuthChangeImpact with categorized changes and effort estimate.
        """
        new_needed: List[AuthObjectChange] = []
        deprecated: List[AuthObjectChange] = []
        changed_list: List[AuthObjectChange] = []
        unaffected: List[str] = []
        notes: List[str] = []

        # Check which existing objects are deprecated or changed
        for obj_name in ecc_auth_objects:
            change = self.auth_changes.get(obj_name)
            if change is None:
                unaffected.append(obj_name)
            elif change.change_type == AuthChangeType.DEPRECATED:
                deprecated.append(change)
                notes.append(
                    f"{obj_name} is deprecated in S/4HANA and should be removed."
                )
            elif change.change_type in (AuthChangeType.CHANGED, AuthChangeType.RENAMED):
                changed_list.append(change)
                notes.append(
                    f"{obj_name} has changed behavior in S/4HANA: {change.notes}"
                )

        # Identify new objects that S/4HANA requires
        # (based on whether the role has BP-related or Fiori-related usage)
        new_candidates = [
            c for c in self.auth_changes.values()
            if c.change_type == AuthChangeType.NEW
        ]

        # Heuristics: add Fiori auth objects if role has any Fiori-facing tcodes
        bp_objects = {"B_BUPA_RLT", "B_BUPA_GRP", "B_BUPA_ATT"}
        fiori_objects = {"S_FIORI_APP", "S_START"}
        analytics_objects = {"S_ODP_READ", "F_FAGLFLEXT", "F_ACDOCA"}

        existing_set = set(ecc_auth_objects)

        # All roles migrating to Fiori need S_FIORI_APP and S_START
        for obj_name in fiori_objects:
            if obj_name not in existing_set:
                change = self.auth_changes.get(obj_name)
                if change:
                    new_needed.append(change)

        # Roles with FI objects need ACDOCA and FAGLFLEXT
        has_fi = any(o.startswith("F_BKPF") or o.startswith("F_BSEG") for o in ecc_auth_objects)
        if has_fi:
            for obj_name in analytics_objects:
                if obj_name not in existing_set:
                    change = self.auth_changes.get(obj_name)
                    if change:
                        new_needed.append(change)

        # Roles with vendor/customer objects need BP objects
        has_vendor_customer = any(
            o in ("LFM1", "KNA1", "LFA1", "V_KNA1_VKO", "V_LFA1_BUK")
            for o in ecc_auth_objects
        )
        if has_vendor_customer:
            for obj_name in bp_objects:
                if obj_name not in existing_set:
                    change = self.auth_changes.get(obj_name)
                    if change:
                        new_needed.append(change)

        # Deduplicate
        seen = set()
        deduped_new = []
        for c in new_needed:
            if c.object_name not in seen:
                seen.add(c.object_name)
                deduped_new.append(c)
        new_needed = deduped_new

        # Effort scoring
        effort_score = len(deprecated) * 1 + len(changed_list) * 2 + len(new_needed) * 3
        if effort_score <= 3:
            effort = "low"
        elif effort_score <= 10:
            effort = "medium"
        else:
            effort = "high"

        return AuthChangeImpact(
            role_id=role_id,
            ecc_auth_objects=ecc_auth_objects,
            new_objects_needed=new_needed,
            deprecated_objects=deprecated,
            changed_objects=changed_list,
            unaffected_objects=unaffected,
            migration_effort=effort,
            notes=notes,
        )

    def assess_role(
        self,
        role_id: str,
        role_name: str,
        ecc_tcodes: List[str],
        ecc_auth_objects: List[str],
    ) -> RoleMigrationAssessment:
        """
        Produce a complete migration readiness assessment for one role.

        Parameters
        ----------
        role_id:          Role technical name.
        role_name:        Human-readable role description.
        ecc_tcodes:       Transaction codes in the role.
        ecc_auth_objects: Authorization objects in the role.

        Returns
        -------
        RoleMigrationAssessment with score, risk, effort and action plan.
        """
        tx_impact = self.analyze_transactions(role_id, ecc_tcodes)
        auth_impact = self.analyze_auth_changes(role_id, ecc_auth_objects)

        # --- Readiness Score ---
        # Transaction score (60% weight)
        tx_score = tx_impact.compatibility_pct * 0.60

        # Auth score (40% weight)
        total_auth = len(ecc_auth_objects)
        if total_auth == 0:
            auth_compat_pct = 100.0
        else:
            auth_problem = len(auth_impact.deprecated_objects)
            auth_compat_pct = max(0.0, ((total_auth - auth_problem) / total_auth) * 100.0)
        auth_score = auth_compat_pct * 0.40

        readiness_score = tx_score + auth_score

        # --- Risk Level ---
        critical_tcodes = [m for m in tx_impact.replaced + tx_impact.fiori_only
                           if m.risk == MigrationRisk.CRITICAL]
        obsolete_count = len(tx_impact.obsolete)
        new_auth_count = len(auth_impact.new_objects_needed)
        deprecated_auth_count = len(auth_impact.deprecated_objects)

        if critical_tcodes or readiness_score < 40:
            risk = MigrationRisk.CRITICAL
        elif readiness_score < 65 or (new_auth_count + deprecated_auth_count) > 5:
            risk = MigrationRisk.HIGH
        elif readiness_score < 80 or obsolete_count > 3:
            risk = MigrationRisk.MEDIUM
        else:
            risk = MigrationRisk.LOW

        # --- Recommended Actions ---
        actions = []
        if tx_impact.fiori_only:
            actions.append(
                f"Provision Fiori launchpad access for apps: "
                f"{', '.join(tx_impact.required_fiori_apps)}. "
                f"Add S_FIORI_APP authorization object with relevant app IDs."
            )
        if tx_impact.replaced:
            replaced_pairs = [
                f"{m.ecc_tcode} -> {m.s4_tcode or 'BP/Fiori'}"
                for m in tx_impact.replaced
            ]
            actions.append(
                f"Update S_TCODE entries: {'; '.join(replaced_pairs)}"
            )
        if tx_impact.obsolete:
            actions.append(
                f"Remove obsolete tcodes from role: "
                f"{', '.join(m.ecc_tcode for m in tx_impact.obsolete)}"
            )
        if auth_impact.deprecated_objects:
            actions.append(
                f"Remove deprecated auth objects: "
                f"{', '.join(o.object_name for o in auth_impact.deprecated_objects)}"
            )
        if auth_impact.new_objects_needed:
            actions.append(
                f"Add new S/4HANA auth objects: "
                f"{', '.join(o.object_name for o in auth_impact.new_objects_needed)}"
            )
        if not actions:
            actions.append("Role is largely compatible. Perform regression test after migration.")

        # --- Effort Estimation ---
        base_days = 0.5
        effort_per_tcode_change = 0.1
        effort_per_auth_change = 0.25
        effort_days = (
            base_days
            + len(tx_impact.replaced) * effort_per_tcode_change
            + len(tx_impact.fiori_only) * effort_per_tcode_change
            + len(tx_impact.obsolete) * effort_per_tcode_change
            + len(auth_impact.new_objects_needed) * effort_per_auth_change
            + len(auth_impact.deprecated_objects) * effort_per_auth_change
        )

        # --- Simplification Items ---
        sim_items = []
        all_tcodes_upper = {t.upper() for t in ecc_tcodes}
        for si_id, si_data in self.simplification_items.items():
            if any(t in all_tcodes_upper for t in si_data["affected_tcodes"]):
                sim_items.append(si_id)

        # --- New Role Suggestions ---
        suggested_roles: List[str] = []
        if any(m.ecc_tcode in ("FK01", "XK01", "MK01", "FD01", "XD01", "VD01")
               for m in tx_impact.replaced):
            suggested_roles.append("Z_S4_BUSINESS_PARTNER_ADMIN")
        if tx_impact.fiori_only:
            suggested_roles.append("Z_S4_FIORI_BASIC_USER")

        can_auto_migrate = (
            readiness_score >= 85
            and len(critical_tcodes) == 0
            and len(auth_impact.deprecated_objects) == 0
            and len(auth_impact.new_objects_needed) <= 2
        )

        return RoleMigrationAssessment(
            role_id=role_id,
            role_name=role_name,
            readiness_score=readiness_score,
            risk=risk,
            transaction_impact=tx_impact,
            auth_change_impact=auth_impact,
            recommended_actions=actions,
            estimated_effort_days=round(effort_days, 2),
            simplification_items=sim_items,
            new_roles_suggested=suggested_roles,
            can_auto_migrate=can_auto_migrate,
        )

    def analyze_user_impact(
        self,
        users: List[Dict],
        role_assessments: Optional[Dict[str, RoleMigrationAssessment]] = None,
    ) -> UserImpactReport:
        """
        Determine how many users are affected by the migration and in what way.

        Parameters
        ----------
        users:            List of user dicts with keys:
                          user_id, user_name, roles (list), department (str).
        role_assessments: Optional pre-computed role assessments keyed by role_id.
                          If omitted, a simplified heuristic is used.

        Returns
        -------
        UserImpactReport summarising user-level migration impact.
        """
        total_users = len(users)
        affected_count = 0
        losing_access_count = 0
        needing_new_roles_count = 0
        needing_fiori_count = 0
        high_impact_records: List[UserImpactRecord] = []
        dept_impact: Dict[str, int] = {}

        for user in users:
            user_id = user.get("user_id", "")
            user_name = user.get("user_name", user_id)
            roles = user.get("roles", [])
            department = user.get("department", "Unknown")

            will_lose: List[str] = []
            needs_new: List[str] = []
            needs_fiori = False
            user_risk = MigrationRisk.LOW
            user_affected = False

            for role_id in roles:
                if role_assessments and role_id in role_assessments:
                    assessment = role_assessments[role_id]
                    tx = assessment.transaction_impact

                    if tx.obsolete:
                        will_lose.extend(m.ecc_tcode for m in tx.obsolete)
                    if tx.fiori_only or tx.replaced:
                        needs_fiori = True
                        user_affected = True
                    if assessment.new_roles_suggested:
                        needs_new.extend(assessment.new_roles_suggested)
                    if assessment.risk in (MigrationRisk.HIGH, MigrationRisk.CRITICAL):
                        user_risk = assessment.risk
                        user_affected = True
                else:
                    # Heuristic: any role with a name suggesting finance/vendor is affected
                    role_lower = role_id.lower()
                    if any(k in role_lower for k in ("vendor", "customer", "fi_", "ap_", "ar_", "gl_")):
                        user_affected = True
                        needs_new.append("Z_S4_BUSINESS_PARTNER_USER")
                        user_risk = MigrationRisk.MEDIUM

            if user_affected:
                affected_count += 1
            if will_lose:
                losing_access_count += 1
            if needs_new:
                needing_new_roles_count += 1
            if needs_fiori:
                needing_fiori_count += 1

            dept_impact[department] = dept_impact.get(department, 0) + (1 if user_affected else 0)

            if user_risk in (MigrationRisk.HIGH, MigrationRisk.CRITICAL):
                high_impact_records.append(UserImpactRecord(
                    user_id=user_id,
                    user_name=user_name,
                    affected_roles=[r for r in roles
                                    if role_assessments and r in role_assessments
                                    and role_assessments[r].risk in
                                    (MigrationRisk.HIGH, MigrationRisk.CRITICAL)],
                    will_lose_access=list(set(will_lose)),
                    needs_new_roles=list(set(needs_new)),
                    needs_fiori_training=needs_fiori,
                    impact_level=user_risk,
                ))

        summary = (
            f"{affected_count} of {total_users} users are impacted by the migration. "
            f"{losing_access_count} will lose access to specific transactions. "
            f"{needing_new_roles_count} require new role assignments. "
            f"{needing_fiori_count} need Fiori launchpad provisioning."
        )

        return UserImpactReport(
            total_users=total_users,
            affected_users=affected_count,
            users_losing_access=losing_access_count,
            users_needing_new_roles=needing_new_roles_count,
            users_needing_fiori_training=needing_fiori_count,
            high_impact_users=high_impact_records,
            impact_by_department=dept_impact,
            summary=summary,
        )

    def generate_plan(
        self,
        role_assessments: List[RoleMigrationAssessment],
        total_users: int = 0,
    ) -> MigrationPlan:
        """
        Generate a phased, prioritized migration plan from a list of role assessments.

        Phases:
          1 — Preparation  (landscape analysis, project setup)
          2 — Design       (role redesign, BP framework design)
          3 — Build        (role recreation, Fiori setup)
          4 — Test         (regression, SoD validation)
          5 — Go-live      (cutover, post-go-live support)

        Parameters
        ----------
        role_assessments: Results from assess_role() for all in-scope roles.
        total_users:      Number of users for effort scaling.

        Returns
        -------
        MigrationPlan with phased task list, effort totals and risk summary.
        """
        tasks: List[MigrationTask] = []
        task_counter = 0

        def _task_id() -> str:
            nonlocal task_counter
            task_counter += 1
            return f"TASK-{task_counter:03d}"

        # --- Phase 1: Preparation ---
        t1 = _task_id()
        tasks.append(MigrationTask(
            task_id=t1,
            title="Landscape and Role Inventory",
            description="Extract full role and user inventory from ECC. Document current "
                        "SoD conflicts and sensitive access assignments as baseline.",
            priority=MigrationTaskPriority.P1,
            phase=1,
            phase_name="Preparation",
            effort_days=3.0,
            depends_on=[],
            risk=MigrationRisk.LOW,
            category="roles",
        ))

        t2 = _task_id()
        tasks.append(MigrationTask(
            task_id=t2,
            title="Business Partner Migration Assessment",
            description="Identify all vendor and customer master data. Plan BP migration "
                        "(FK01/XK01/FD01/XD01/VD01 transactions). Simplification item SI-FIN-M-00001.",
            priority=MigrationTaskPriority.P1,
            phase=1,
            phase_name="Preparation",
            effort_days=2.0,
            depends_on=[t1],
            risk=MigrationRisk.CRITICAL,
            category="roles",
        ))

        t3 = _task_id()
        tasks.append(MigrationTask(
            task_id=t3,
            title="Fiori Launchpad Architecture Design",
            description="Design Fiori launchpad groups, catalogs and tile assignments. "
                        "Map roles to required Fiori app IDs. Define S_FIORI_APP values per role.",
            priority=MigrationTaskPriority.P1,
            phase=1,
            phase_name="Preparation",
            effort_days=5.0,
            depends_on=[t1],
            risk=MigrationRisk.HIGH,
            category="fiori",
        ))

        t4 = _task_id()
        tasks.append(MigrationTask(
            task_id=t4,
            title="SoD Rule Refresh for S/4HANA",
            description="Update SoD ruleset to include S/4HANA-specific transaction codes "
                        "and authorization objects. Validate existing rules remain valid.",
            priority=MigrationTaskPriority.P2,
            phase=1,
            phase_name="Preparation",
            effort_days=3.0,
            depends_on=[t1],
            risk=MigrationRisk.HIGH,
            category="roles",
        ))

        # --- Phase 2: Design ---
        t5 = _task_id()
        tasks.append(MigrationTask(
            task_id=t5,
            title="Role Redesign for Obsolete and Replaced Transactions",
            description="For each role with replaced/obsolete tcodes, design the updated "
                        "S/4HANA role structure including new Fiori-based authorizations.",
            priority=MigrationTaskPriority.P1,
            phase=2,
            phase_name="Design",
            effort_days=_sum_effort(role_assessments, statuses=[MigrationStatus.REPLACED,
                                                                  MigrationStatus.FIORI_ONLY,
                                                                  MigrationStatus.OBSOLETE]),
            depends_on=[t3, t4],
            risk=MigrationRisk.HIGH,
            category="roles",
            affected_roles=[a.role_id for a in role_assessments
                            if a.risk in (MigrationRisk.HIGH, MigrationRisk.CRITICAL)],
        ))

        t6 = _task_id()
        tasks.append(MigrationTask(
            task_id=t6,
            title="Business Partner Authorization Design",
            description="Design new authorization concept for Business Partner (B_BUPA_RLT, "
                        "B_BUPA_GRP, B_BUPA_ATT). Map to existing vendor/customer role structure.",
            priority=MigrationTaskPriority.P1,
            phase=2,
            phase_name="Design",
            effort_days=3.0,
            depends_on=[t2, t5],
            risk=MigrationRisk.CRITICAL,
            category="auth",
        ))

        t7 = _task_id()
        tasks.append(MigrationTask(
            task_id=t7,
            title="Universal Journal Auth Object Design",
            description="Design F_ACDOCA and F_FAGLFLEXT authorization values for all "
                        "finance roles. Remove deprecated BSEG-based controls.",
            priority=MigrationTaskPriority.P2,
            phase=2,
            phase_name="Design",
            effort_days=2.0,
            depends_on=[t5],
            risk=MigrationRisk.HIGH,
            category="auth",
        ))

        # --- Phase 3: Build ---
        t8 = _task_id()
        tasks.append(MigrationTask(
            task_id=t8,
            title="Role Build in S/4HANA Development System",
            description="Recreate all in-scope roles in the S/4HANA development system "
                        "using PFCG. Include updated tcodes, new auth objects and Fiori settings.",
            priority=MigrationTaskPriority.P1,
            phase=3,
            phase_name="Build",
            effort_days=sum(a.estimated_effort_days for a in role_assessments),
            depends_on=[t5, t6, t7],
            risk=MigrationRisk.HIGH,
            category="roles",
            affected_roles=[a.role_id for a in role_assessments],
        ))

        t9 = _task_id()
        tasks.append(MigrationTask(
            task_id=t9,
            title="Fiori Launchpad Configuration",
            description="Configure Fiori launchpad catalogs and groups in S/4HANA. "
                        "Assign roles to catalogs. Configure backend system aliases.",
            priority=MigrationTaskPriority.P1,
            phase=3,
            phase_name="Build",
            effort_days=5.0,
            depends_on=[t3, t8],
            risk=MigrationRisk.MEDIUM,
            category="fiori",
        ))

        user_training_days = max(1.0, total_users * 0.02)
        t10 = _task_id()
        tasks.append(MigrationTask(
            task_id=t10,
            title="Business Partner Data Migration",
            description="Run customer/vendor to Business Partner conversion. "
                        "Validate BP data completeness and role assignments.",
            priority=MigrationTaskPriority.P1,
            phase=3,
            phase_name="Build",
            effort_days=4.0,
            depends_on=[t6],
            risk=MigrationRisk.CRITICAL,
            category="roles",
        ))

        # --- Phase 4: Test ---
        t11 = _task_id()
        tasks.append(MigrationTask(
            task_id=t11,
            title="Authorization Regression Testing",
            description="Perform role-based user acceptance testing. Verify each role "
                        "grants correct access in S/4HANA. Use Productive Test Simulation (PTS).",
            priority=MigrationTaskPriority.P1,
            phase=4,
            phase_name="Test",
            effort_days=max(3.0, len(role_assessments) * 0.5),
            depends_on=[t8, t9],
            risk=MigrationRisk.HIGH,
            category="testing",
        ))

        t12 = _task_id()
        tasks.append(MigrationTask(
            task_id=t12,
            title="SoD Conflict Re-Validation",
            description="Run full SoD analysis on all S/4HANA roles. Compare results "
                        "to ECC baseline. Resolve any new conflicts introduced by migration.",
            priority=MigrationTaskPriority.P1,
            phase=4,
            phase_name="Test",
            effort_days=2.0,
            depends_on=[t11],
            risk=MigrationRisk.HIGH,
            category="testing",
        ))

        t13 = _task_id()
        tasks.append(MigrationTask(
            task_id=t13,
            title="Fiori App Access Testing",
            description="Verify all Fiori apps are accessible to the correct user groups. "
                        "Test S_FIORI_APP values and launchpad tile visibility.",
            priority=MigrationTaskPriority.P2,
            phase=4,
            phase_name="Test",
            effort_days=2.0,
            depends_on=[t9, t11],
            risk=MigrationRisk.MEDIUM,
            category="testing",
        ))

        # --- Phase 5: Go-live ---
        t14 = _task_id()
        tasks.append(MigrationTask(
            task_id=t14,
            title="User Training — Fiori UX",
            description=f"Train {total_users or 'all'} end users on Fiori launchpad. "
                        "Focus on replaced transactions and new Fiori apps.",
            priority=MigrationTaskPriority.P2,
            phase=5,
            phase_name="Go-live",
            effort_days=user_training_days,
            depends_on=[t13],
            risk=MigrationRisk.MEDIUM,
            category="training",
        ))

        t15 = _task_id()
        tasks.append(MigrationTask(
            task_id=t15,
            title="Production Role Transport and Cutover",
            description="Transport all roles from QA to Production. Execute user role "
                        "reassignments. Deactivate obsolete ECC roles.",
            priority=MigrationTaskPriority.P1,
            phase=5,
            phase_name="Go-live",
            effort_days=2.0,
            depends_on=[t12, t14],
            risk=MigrationRisk.CRITICAL,
            category="roles",
        ))

        t16 = _task_id()
        tasks.append(MigrationTask(
            task_id=t16,
            title="Post-Go-Live Access Review",
            description="Run access certification campaign within 30 days of go-live. "
                        "Validate no unintended access was granted during migration.",
            priority=MigrationTaskPriority.P2,
            phase=5,
            phase_name="Go-live",
            effort_days=3.0,
            depends_on=[t15],
            risk=MigrationRisk.HIGH,
            category="testing",
        ))

        # Organize by phase
        phases: Dict[int, List[MigrationTask]] = {1: [], 2: [], 3: [], 4: [], 5: []}
        for task in tasks:
            phases[task.phase].append(task)

        total_effort = sum(t.effort_days for t in tasks)
        # Assume parallel work with 3 consultants at 70% utilization
        duration_weeks = (total_effort / (3 * 5 * 0.70))

        overall_risk = _aggregate_risk(role_assessments)

        readiness_scores = [a.readiness_score for a in role_assessments]
        avg_readiness = sum(readiness_scores) / len(readiness_scores) if readiness_scores else 0.0

        critical_path = [t1, t2, t3, t5, t6, t8, t10, t11, t12, t15]

        risks = [
            {
                "risk_id": "R001",
                "description": "Business Partner migration data quality issues cause delays",
                "likelihood": "medium",
                "impact": "critical",
                "mitigation": "Run BP data quality checks 8 weeks before go-live",
            },
            {
                "risk_id": "R002",
                "description": "SoD conflicts multiply when Fiori apps grant broader access than ECC tcodes",
                "likelihood": "high",
                "impact": "high",
                "mitigation": "Run SoD simulation in QA before transporting to Production",
            },
            {
                "risk_id": "R003",
                "description": "Users lose productive access due to missing Fiori authorizations",
                "likelihood": "medium",
                "impact": "high",
                "mitigation": "Complete Fiori authorization testing with key user group before go-live",
            },
            {
                "risk_id": "R004",
                "description": "Asset Accounting migration requires parallel ledger realignment",
                "likelihood": "low",
                "impact": "high",
                "mitigation": "Engage FI-AA consultant for new Asset Accounting setup",
            },
            {
                "risk_id": "R005",
                "description": "Custom ABAP programs bypass new S/4HANA authorization checks",
                "likelihood": "medium",
                "impact": "medium",
                "mitigation": "Run SCI (SAP Code Inspector) security checks on all Z-programs",
            },
        ]

        assumptions = [
            "S/4HANA system is on release 2023 or later.",
            "SAP Fiori launchpad is the primary UX for end users.",
            "Business Partner (BP) framework migration is in scope.",
            "New Asset Accounting (FI-AA) will be activated.",
            "Material Ledger will be activated (mandatory in S/4HANA).",
            "Logistics Information System (LIS) reports are out of scope.",
            "SuccessFactors integration is out of scope (HCM on-prem assumed).",
            "Effort estimates assume experienced SAP security consultants.",
        ]

        summary = (
            f"Migration plan covers {len(role_assessments)} roles across 5 phases. "
            f"Total estimated effort: {round(total_effort, 1)} person-days over "
            f"{round(duration_weeks, 1)} weeks with 3 consultants. "
            f"Overall migration risk: {overall_risk.value.upper()}. "
            f"Average role readiness: {round(avg_readiness, 1)}%."
        )

        return MigrationPlan(
            total_roles=len(role_assessments),
            total_effort_days=round(total_effort, 2),
            estimated_duration_weeks=duration_weeks,
            overall_risk=overall_risk,
            readiness_score=avg_readiness,
            phases=phases,
            critical_path_tasks=critical_path,
            risks=risks,
            assumptions=assumptions,
            summary=summary,
        )

    # -------------------------------------------------------------------------
    # Helper / Convenience Methods
    # -------------------------------------------------------------------------

    def get_all_transaction_mappings(self) -> List[Dict]:
        """Return the full ECC to S/4HANA transaction mapping as a list of dicts."""
        return [m.to_dict() for m in self.transaction_map.values()]

    def get_obsolete_transactions(self) -> List[Dict]:
        """Return all known obsolete ECC transactions."""
        return list(self.obsolete.values())

    def get_fiori_apps(self) -> List[Dict]:
        """Return the full Fiori app catalog."""
        return [app.to_dict() for app in self.fiori_catalog.values()]

    def get_auth_object_changes(self) -> List[Dict]:
        """Return all authorization object changes between ECC and S/4HANA."""
        return [c.to_dict() for c in self.auth_changes.values()]

    def get_simplification_items(self) -> List[Dict]:
        """Return all relevant SAP simplification list items."""
        return list(self.simplification_items.values())

    def get_overview_stats(self) -> Dict:
        """Return aggregate statistics for the migration analyzer knowledge base."""
        return {
            "transaction_mappings": len(self.transaction_map),
            "obsolete_transactions": len(self.obsolete),
            "fiori_apps_cataloged": len(self.fiori_catalog),
            "auth_object_changes": len(self.auth_changes),
            "new_auth_objects": sum(
                1 for c in self.auth_changes.values()
                if c.change_type == AuthChangeType.NEW
            ),
            "deprecated_auth_objects": sum(
                1 for c in self.auth_changes.values()
                if c.change_type == AuthChangeType.DEPRECATED
            ),
            "changed_auth_objects": sum(
                1 for c in self.auth_changes.values()
                if c.change_type == AuthChangeType.CHANGED
            ),
            "simplification_items": len(self.simplification_items),
            "business_processes_covered": sorted({
                m.business_process for m in self.transaction_map.values()
                if m.business_process
            }),
        }


# =============================================================================
# Private Helpers
# =============================================================================

def _sum_effort(
    assessments: List[RoleMigrationAssessment],
    statuses: Optional[List[MigrationStatus]] = None,
) -> float:
    """Sum estimated effort for roles that have transactions in the given statuses."""
    total = 0.0
    for a in assessments:
        tx = a.transaction_impact
        counts_in_status = sum([
            len([m for m in tx.replaced if statuses is None or m.status in statuses]),
            len([m for m in tx.fiori_only if statuses is None or m.status in statuses]),
            len([m for m in tx.obsolete if statuses is None or m.status in statuses]),
        ])
        if counts_in_status > 0:
            total += a.estimated_effort_days
    return max(1.0, total)


def _aggregate_risk(assessments: List[RoleMigrationAssessment]) -> MigrationRisk:
    """Return the highest risk level across all assessments."""
    if not assessments:
        return MigrationRisk.LOW
    order = [MigrationRisk.LOW, MigrationRisk.MEDIUM, MigrationRisk.HIGH, MigrationRisk.CRITICAL]
    highest = MigrationRisk.LOW
    for a in assessments:
        if order.index(a.risk) > order.index(highest):
            highest = a.risk
    return highest
