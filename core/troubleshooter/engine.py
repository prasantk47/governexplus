"""
Access Troubleshooter Engine

AI-powered diagnostic engine that answers the single most important question in
legacy GRC: "Why can't user X execute transaction Y in system Z?"

The engine performs a deterministic, ordered diagnostic chain across all known
failure modes — from basic user status through transport gaps and Fiori catalog
misconfigurations — and returns a structured diagnosis with a root cause,
confidence score, recommended fix, and SoD risk impact of applying that fix.

Architecture
------------
- ``TroubleshootRequest``  — input value object
- ``DiagnosisStep``        — one check in the diagnostic chain
- ``DiagnosisResult``      — full structured output
- ``AccessTroubleshooter`` — orchestrates all checks; designed to be sub-classed
                             or replaced with a connector-backed implementation
- ``TRANSACTION_KB``       — knowledge base: 30+ tcodes with auth requirements
- ``FIORI_KB``             — Fiori app → catalog / OData / backend-auth mappings
- ``COMMON_ISSUES``        — curated list of top recurring failures
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class CheckStatus(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    WARNING = "warning"
    SKIPPED = "skipped"
    INFO = "info"


class DiagnosisStatus(str, Enum):
    ACCESS_GRANTED = "access_granted"
    ACCESS_DENIED = "access_denied"
    PARTIAL_ACCESS = "partial_access"


# ---------------------------------------------------------------------------
# Data transfer objects
# ---------------------------------------------------------------------------

@dataclass
class TroubleshootRequest:
    """Input to the troubleshooter engine.

    Attributes
    ----------
    user_id:
        SAP user logon name (case-insensitive; stored in uppercase internally).
    transaction:
        Transaction code or Fiori application ID (e.g. ``FB01``, ``F0018``).
    system:
        Target system SID or friendly name (e.g. ``PRD``, ``S4H_PROD``).
    tenant_id:
        GovernexPlus tenant performing the diagnosis.  Defaults to the platform
        default.
    requested_by:
        User ID of the analyst triggering the diagnosis — recorded in history.
    context:
        Optional free-form context that the caller wants attached (e.g. ticket
        reference, business justification being evaluated).
    """

    user_id: str
    transaction: str
    system: str
    tenant_id: str = "tenant_default"
    requested_by: str = "system"
    context: Optional[str] = None

    def __post_init__(self) -> None:
        self.user_id = self.user_id.upper().strip()
        self.transaction = self.transaction.upper().strip()
        self.system = self.system.upper().strip()


@dataclass
class DiagnosisStep:
    """Result of a single diagnostic check.

    Attributes
    ----------
    check_name:
        Short machine-readable identifier for the check.
    display_name:
        Human-readable label shown in UI cards.
    status:
        ``pass`` | ``fail`` | ``warning`` | ``skipped`` | ``info``.
    detail:
        Detailed findings for this step (what was found or not found).
    recommendation:
        Specific action to take if status is ``fail`` or ``warning``.
    technical_detail:
        Raw technical data (auth object values, role names, etc.) for
        advanced users.  May be ``None``.
    """

    check_name: str
    display_name: str
    status: CheckStatus
    detail: str
    recommendation: str = ""
    technical_detail: Optional[str] = None


@dataclass
class DiagnosisResult:
    """Full structured output from the troubleshooter engine.

    Attributes
    ----------
    diagnosis_id:
        Unique identifier for this diagnosis run — used in history lookups.
    request:
        The original request that produced this result.
    status:
        Top-level verdict: ``access_granted`` | ``access_denied`` |
        ``partial_access``.
    root_cause:
        One-sentence summary of the primary blocking reason (or confirmation
        of access when granted).
    diagnosis_steps:
        Ordered list of every check performed, including passed checks so the
        full chain is auditable.
    recommended_fix:
        Concrete action an administrator should take to resolve the issue.
    estimated_fix_time:
        Rough estimate of elapsed calendar time to implement the fix.
    risk_impact:
        SoD or sensitive-access conflicts that would arise if the recommended
        fix is applied.  Empty list means no new risk.
    confidence_score:
        Engine's confidence in the root cause (0.0 – 1.0).  Lower when
        multiple plausible failure modes coexist.
    diagnosed_at:
        ISO-8601 timestamp of when the diagnosis was performed.
    """

    diagnosis_id: str
    request: TroubleshootRequest
    status: DiagnosisStatus
    root_cause: str
    diagnosis_steps: List[DiagnosisStep]
    recommended_fix: str
    estimated_fix_time: str
    risk_impact: List[str]
    confidence_score: float
    diagnosed_at: str = field(
        default_factory=lambda: datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to a JSON-safe dictionary."""
        return {
            "diagnosis_id": self.diagnosis_id,
            "status": self.status.value,
            "root_cause": self.root_cause,
            "recommended_fix": self.recommended_fix,
            "estimated_fix_time": self.estimated_fix_time,
            "confidence_score": round(self.confidence_score, 3),
            "risk_impact": self.risk_impact,
            "diagnosed_at": self.diagnosed_at,
            "request": {
                "user_id": self.request.user_id,
                "transaction": self.request.transaction,
                "system": self.request.system,
                "tenant_id": self.request.tenant_id,
                "requested_by": self.request.requested_by,
                "context": self.request.context,
            },
            "diagnosis_steps": [
                {
                    "check_name": s.check_name,
                    "display_name": s.display_name,
                    "status": s.status.value,
                    "detail": s.detail,
                    "recommendation": s.recommendation,
                    "technical_detail": s.technical_detail,
                }
                for s in self.diagnosis_steps
            ],
        }


# ---------------------------------------------------------------------------
# Transaction knowledge base
# ---------------------------------------------------------------------------

@dataclass
class AuthObjectRequirement:
    """A single authorization object requirement for a transaction."""

    auth_object: str
    field_name: str
    required_values: List[str]
    description: str
    is_critical: bool = True


@dataclass
class TransactionProfile:
    """Full auth profile for one SAP transaction code."""

    tcode: str
    description: str
    module: str
    auth_requirements: List[AuthObjectRequirement]
    sensitive: bool = False
    fiori_app_id: Optional[str] = None
    notes: str = ""


# Key: tcode (uppercase).  Values cover the most commonly troubleshot SAP tcodes.
TRANSACTION_KB: Dict[str, TransactionProfile] = {
    # -------------------------------------------------------------------------
    # Finance / Accounts Payable
    # -------------------------------------------------------------------------
    "FB01": TransactionProfile(
        tcode="FB01",
        description="Post Document (General Ledger)",
        module="FI",
        auth_requirements=[
            AuthObjectRequirement("F_BKPF_BUK", "ACTVT", ["01"], "Post FI documents"),
            AuthObjectRequirement("F_BKPF_BUK", "BUKRS", ["*", "1000", "2000"], "Company code authorization"),
            AuthObjectRequirement("F_BKPF_KOA", "KOART", ["D", "K", "S"], "Account type authorization"),
            AuthObjectRequirement("F_BKPF_GSB", "GSBER", ["*"], "Business area authorization"),
        ],
        sensitive=True,
        fiori_app_id="F0718",
        notes="Requires both posting authorization and company code access.",
    ),
    "FB60": TransactionProfile(
        tcode="FB60",
        description="Enter Incoming Invoices",
        module="FI-AP",
        auth_requirements=[
            AuthObjectRequirement("F_BKPF_BUK", "ACTVT", ["01"], "Enter AP invoices"),
            AuthObjectRequirement("F_BKPF_BUK", "BUKRS", ["*", "1000"], "Company code"),
            AuthObjectRequirement("F_BKPF_KOA", "KOART", ["K"], "Vendor account type"),
        ],
        sensitive=False,
        fiori_app_id="F0859",
    ),
    "FK01": TransactionProfile(
        tcode="FK01",
        description="Create Vendor (Accounting)",
        module="FI-AP",
        auth_requirements=[
            AuthObjectRequirement("F_LFA1_BUK", "ACTVT", ["01"], "Create vendor master"),
            AuthObjectRequirement("F_LFA1_BUK", "BUKRS", ["*", "1000"], "Company code"),
            AuthObjectRequirement("F_LFA1_GRP", "KTOKK", ["*"], "Vendor account group"),
        ],
        sensitive=True,
        notes="Vendor master creation — high risk for payment fraud if combined with payment posting.",
    ),
    "FK02": TransactionProfile(
        tcode="FK02",
        description="Change Vendor (Accounting)",
        module="FI-AP",
        auth_requirements=[
            AuthObjectRequirement("F_LFA1_BUK", "ACTVT", ["02"], "Change vendor master"),
            AuthObjectRequirement("F_LFA1_BUK", "BUKRS", ["*", "1000"], "Company code"),
        ],
        sensitive=True,
    ),
    "F110": TransactionProfile(
        tcode="F110",
        description="Automatic Payment Program",
        module="FI-AP",
        auth_requirements=[
            AuthObjectRequirement("F_REGU_BUK", "ACTVT", ["01", "02", "08"], "Run payment program"),
            AuthObjectRequirement("F_REGU_BUK", "BUKRS", ["*", "1000"], "Company code"),
            AuthObjectRequirement("F_REGU_KOA", "KOART", ["K"], "Vendor payment"),
        ],
        sensitive=True,
        notes="Extremely sensitive — can initiate bulk vendor payments.",
    ),
    "XK01": TransactionProfile(
        tcode="XK01",
        description="Create Vendor (Centrally)",
        module="MM",
        auth_requirements=[
            AuthObjectRequirement("F_LFA1_BUK", "ACTVT", ["01"], "Create vendor master FI view"),
            AuthObjectRequirement("M_LFA1_EKO", "ACTVT", ["01"], "Create vendor master MM view"),
            AuthObjectRequirement("F_LFA1_GRP", "KTOKK", ["*"], "Vendor account group"),
        ],
        sensitive=True,
        notes="Central vendor creation — requires both FI and MM authorization.",
    ),
    # -------------------------------------------------------------------------
    # Finance / General
    # -------------------------------------------------------------------------
    "FB50": TransactionProfile(
        tcode="FB50",
        description="Enter G/L Account Document",
        module="FI",
        auth_requirements=[
            AuthObjectRequirement("F_BKPF_BUK", "ACTVT", ["01"], "Post G/L document"),
            AuthObjectRequirement("F_BKPF_BUK", "BUKRS", ["*"], "Company code"),
            AuthObjectRequirement("F_BKPF_KOA", "KOART", ["S"], "G/L account type"),
        ],
        fiori_app_id="F1643",
    ),
    "FS00": TransactionProfile(
        tcode="FS00",
        description="G/L Account Master Data",
        module="FI",
        auth_requirements=[
            AuthObjectRequirement("F_SKA1_BUK", "ACTVT", ["01", "02", "03"], "Manage G/L master"),
            AuthObjectRequirement("F_SKA1_BUK", "BUKRS", ["*"], "Company code"),
        ],
        sensitive=True,
    ),
    # -------------------------------------------------------------------------
    # Materials Management / Procurement
    # -------------------------------------------------------------------------
    "MIRO": TransactionProfile(
        tcode="MIRO",
        description="Enter Incoming Invoice (LIV)",
        module="MM-IV",
        auth_requirements=[
            AuthObjectRequirement("M_RECH_BUK", "ACTVT", ["01"], "Enter logistics invoice"),
            AuthObjectRequirement("M_RECH_BUK", "BUKRS", ["*", "1000"], "Company code"),
            AuthObjectRequirement("M_RECH_WRK", "WERKS", ["*", "1000"], "Plant authorization"),
        ],
        sensitive=False,
        fiori_app_id="F0859",
    ),
    "ME21N": TransactionProfile(
        tcode="ME21N",
        description="Create Purchase Order",
        module="MM-PUR",
        auth_requirements=[
            AuthObjectRequirement("M_BEST_BSA", "BSART", ["NB", "*"], "PO document type"),
            AuthObjectRequirement("M_BEST_EKG", "EKGRP", ["*"], "Purchasing group"),
            AuthObjectRequirement("M_BEST_EKO", "EKORG", ["*", "1000"], "Purchasing organization"),
            AuthObjectRequirement("M_BEST_WRK", "WERKS", ["*", "1000"], "Plant"),
        ],
        sensitive=False,
        fiori_app_id="F0842A",
        notes="Check purchasing group and organization field values carefully.",
    ),
    "ME22N": TransactionProfile(
        tcode="ME22N",
        description="Change Purchase Order",
        module="MM-PUR",
        auth_requirements=[
            AuthObjectRequirement("M_BEST_BSA", "BSART", ["NB", "*"], "PO document type"),
            AuthObjectRequirement("M_BEST_EKG", "EKGRP", ["*"], "Purchasing group"),
            AuthObjectRequirement("M_BEST_EKO", "EKORG", ["*"], "Purchasing organization"),
        ],
    ),
    "MM01": TransactionProfile(
        tcode="MM01",
        description="Create Material",
        module="MM",
        auth_requirements=[
            AuthObjectRequirement("M_MATE_STA", "STATM", ["*"], "Material type authorization"),
            AuthObjectRequirement("M_MATE_WRK", "WERKS", ["*"], "Plant"),
            AuthObjectRequirement("M_MATE_MAR", "ACTVT", ["01"], "Create material master"),
        ],
        sensitive=False,
        fiori_app_id="F1604",
    ),
    "MIGO": TransactionProfile(
        tcode="MIGO",
        description="Goods Movement",
        module="MM-IM",
        auth_requirements=[
            AuthObjectRequirement("M_MSEG_BWA", "BWART", ["*", "101", "102", "261"], "Movement type"),
            AuthObjectRequirement("M_MSEG_WMB", "WERKS", ["*"], "Plant"),
            AuthObjectRequirement("M_MSEG_WMB", "LGORT", ["*"], "Storage location"),
        ],
        fiori_app_id="F0842",
    ),
    # -------------------------------------------------------------------------
    # Sales / Order to Cash
    # -------------------------------------------------------------------------
    "VA01": TransactionProfile(
        tcode="VA01",
        description="Create Sales Order",
        module="SD",
        auth_requirements=[
            AuthObjectRequirement("V_VBAK_AAT", "AUART", ["TA", "*"], "Sales document type"),
            AuthObjectRequirement("V_VBAK_VKO", "VKORG", ["*", "1000"], "Sales organization"),
            AuthObjectRequirement("V_VBAK_VKO", "VTWEG", ["*", "10"], "Distribution channel"),
            AuthObjectRequirement("V_VBAK_VKO", "SPART", ["*", "00"], "Division"),
        ],
        fiori_app_id="F0798",
        notes="All three organizational levels in V_VBAK_VKO must match the sales area.",
    ),
    "VF01": TransactionProfile(
        tcode="VF01",
        description="Create Billing Document",
        module="SD",
        auth_requirements=[
            AuthObjectRequirement("V_VBRK_FKA", "FKART", ["F2", "*"], "Billing document type"),
            AuthObjectRequirement("V_VBRK_VKO", "VKORG", ["*"], "Sales organization"),
        ],
        sensitive=True,
    ),
    # -------------------------------------------------------------------------
    # Basis / Security Administration
    # -------------------------------------------------------------------------
    "SU01": TransactionProfile(
        tcode="SU01",
        description="User Maintenance",
        module="BASIS",
        auth_requirements=[
            AuthObjectRequirement("S_USR_ADM", "ACTVT", ["01", "02", "05", "06"], "User admin activity"),
            AuthObjectRequirement("S_USR_GRP", "CLASS", ["*"], "User group"),
            AuthObjectRequirement("S_USR_GRP", "ACTVT", ["01", "02", "05"], "User group activity"),
        ],
        sensitive=True,
        fiori_app_id="F2142",
        notes="SU01 is extremely sensitive — often conflicts with role assignment (SU10, PFCG).",
    ),
    "SU10": TransactionProfile(
        tcode="SU10",
        description="Mass User Maintenance",
        module="BASIS",
        auth_requirements=[
            AuthObjectRequirement("S_USR_ADM", "ACTVT", ["01", "02", "05"], "Mass user admin"),
            AuthObjectRequirement("S_USR_GRP", "CLASS", ["*"], "User group"),
        ],
        sensitive=True,
    ),
    "PFCG": TransactionProfile(
        tcode="PFCG",
        description="Role Maintenance",
        module="BASIS",
        auth_requirements=[
            AuthObjectRequirement("S_USER_AGR", "ACTVT", ["01", "02", "22"], "Maintain authorization roles"),
            AuthObjectRequirement("S_USER_AGR", "ACT_GROUP", ["*"], "Role name pattern"),
        ],
        sensitive=True,
        notes="PFCG combined with SU01 creates the super-user SoD conflict.",
    ),
    "SE38": TransactionProfile(
        tcode="SE38",
        description="ABAP Editor",
        module="BASIS",
        auth_requirements=[
            AuthObjectRequirement("S_DEVELOP", "ACTVT", ["01", "02", "03", "16"], "ABAP development"),
            AuthObjectRequirement("S_DEVELOP", "DEVCLASS", ["*"], "Development package"),
            AuthObjectRequirement("S_DEVELOP", "OBJTYPE", ["PROG"], "Object type: Program"),
        ],
        sensitive=True,
        notes="Development access is highly sensitive in production systems.",
    ),
    "SM30": TransactionProfile(
        tcode="SM30",
        description="Table Maintenance",
        module="BASIS",
        auth_requirements=[
            AuthObjectRequirement("S_TABU_DIS", "ACTVT", ["02"], "Table maintenance change"),
            AuthObjectRequirement("S_TABU_DIS", "DICBERCLS", ["*"], "Table authorization group"),
            AuthObjectRequirement("S_TABU_NAM", "TABLE", ["*"], "Specific table name"),
        ],
        sensitive=True,
    ),
    "SM36": TransactionProfile(
        tcode="SM36",
        description="Schedule Background Job",
        module="BASIS",
        auth_requirements=[
            AuthObjectRequirement("S_BTCH_JOB", "JOBACTION", ["RELE"], "Release background job"),
            AuthObjectRequirement("S_BTCH_ADM", "BTCADM", ["Y"], "Background administration"),
        ],
        sensitive=False,
    ),
    "STMS": TransactionProfile(
        tcode="STMS",
        description="Transport Management System",
        module="BASIS",
        auth_requirements=[
            AuthObjectRequirement("S_TRANSPRT", "ACTVT", ["01", "02", "43"], "Transport management"),
            AuthObjectRequirement("S_TRANSPRT", "TTYPE", ["K", "W", "T"], "Transport type"),
        ],
        sensitive=True,
        notes="Transport import to PROD is extremely sensitive.",
    ),
    # -------------------------------------------------------------------------
    # Human Resources
    # -------------------------------------------------------------------------
    "PA30": TransactionProfile(
        tcode="PA30",
        description="Maintain HR Master Data",
        module="HR",
        auth_requirements=[
            AuthObjectRequirement("P_ORGIN", "ACTVT", ["02"], "Change HR master data"),
            AuthObjectRequirement("P_ORGIN", "INFTY", ["0008", "0009", "0014", "0015"], "Infotype"),
            AuthObjectRequirement("P_ORGIN", "PERSA", ["*"], "Personnel area"),
        ],
        sensitive=True,
        notes="P_ORGIN must cover the correct personnel area and infotype range.",
    ),
    "PA61": TransactionProfile(
        tcode="PA61",
        description="Maintain Time Data",
        module="HR",
        auth_requirements=[
            AuthObjectRequirement("P_ORGIN", "ACTVT", ["02"], "Maintain time data"),
            AuthObjectRequirement("P_ORGIN", "INFTY", ["2001", "2002", "2006"], "Time infotypes"),
            AuthObjectRequirement("P_ORGIN", "PERSA", ["*"], "Personnel area"),
        ],
    ),
    # -------------------------------------------------------------------------
    # Asset Accounting
    # -------------------------------------------------------------------------
    "AS01": TransactionProfile(
        tcode="AS01",
        description="Create Asset",
        module="FI-AA",
        auth_requirements=[
            AuthObjectRequirement("A_D_ANLKL", "ACTVT", ["01"], "Create asset"),
            AuthObjectRequirement("A_D_ANLKL", "ANLKL", ["*"], "Asset class"),
            AuthObjectRequirement("A_D_BUKRS", "BUKRS", ["*"], "Company code"),
        ],
        sensitive=False,
    ),
    "AFAB": TransactionProfile(
        tcode="AFAB",
        description="Post Depreciation",
        module="FI-AA",
        auth_requirements=[
            AuthObjectRequirement("A_D_BUKRS", "ACTVT", ["01"], "Post depreciation"),
            AuthObjectRequirement("A_D_BUKRS", "BUKRS", ["*"], "Company code"),
            AuthObjectRequirement("F_BKPF_BUK", "ACTVT", ["01"], "Post FI document for depreciation"),
        ],
        sensitive=False,
    ),
    # -------------------------------------------------------------------------
    # Controlling
    # -------------------------------------------------------------------------
    "KS01": TransactionProfile(
        tcode="KS01",
        description="Create Cost Center",
        module="CO",
        auth_requirements=[
            AuthObjectRequirement("K_CSKS", "ACTVT", ["01"], "Create cost center"),
            AuthObjectRequirement("K_CSKS", "KOKRS", ["*"], "Controlling area"),
            AuthObjectRequirement("K_CSKS", "KOSTL", ["*"], "Cost center"),
        ],
        sensitive=False,
    ),
    "KB11N": TransactionProfile(
        tcode="KB11N",
        description="Enter Manual Cost Allocation",
        module="CO",
        auth_requirements=[
            AuthObjectRequirement("K_VRGNG", "ACTVT", ["01"], "Enter allocation"),
            AuthObjectRequirement("K_VRGNG", "VRGNG", ["RKIU"], "Allocation transaction"),
        ],
    ),
    # -------------------------------------------------------------------------
    # Reporting / Display only
    # -------------------------------------------------------------------------
    "FBL1N": TransactionProfile(
        tcode="FBL1N",
        description="Vendor Line Items",
        module="FI-AP",
        auth_requirements=[
            AuthObjectRequirement("F_BKPF_BUK", "ACTVT", ["03"], "Display FI documents"),
            AuthObjectRequirement("F_BKPF_BUK", "BUKRS", ["*"], "Company code"),
        ],
        sensitive=False,
        fiori_app_id="F1639",
    ),
    "FBL5N": TransactionProfile(
        tcode="FBL5N",
        description="Customer Line Items",
        module="FI-AR",
        auth_requirements=[
            AuthObjectRequirement("F_BKPF_BUK", "ACTVT", ["03"], "Display FI documents"),
            AuthObjectRequirement("F_BKPF_BUK", "BUKRS", ["*"], "Company code"),
        ],
        sensitive=False,
        fiori_app_id="F1640",
    ),
    "MB51": TransactionProfile(
        tcode="MB51",
        description="Material Document List",
        module="MM-IM",
        auth_requirements=[
            AuthObjectRequirement("M_MSEG_WMB", "WERKS", ["*"], "Plant display"),
            AuthObjectRequirement("M_MSEG_WMB", "ACTVT", ["03"], "Display goods movements"),
        ],
    ),
    # -------------------------------------------------------------------------
    # Plant Maintenance
    # -------------------------------------------------------------------------
    "IW31": TransactionProfile(
        tcode="IW31",
        description="Create Maintenance Order",
        module="PM",
        auth_requirements=[
            AuthObjectRequirement("I_AUFK", "ACTVT", ["01"], "Create PM order"),
            AuthObjectRequirement("I_AUFK", "AUTYP", ["30"], "Order type PM"),
            AuthObjectRequirement("I_WERK", "IWERK", ["*"], "Plant"),
        ],
    ),
    # -------------------------------------------------------------------------
    # Quality Management
    # -------------------------------------------------------------------------
    "QA01": TransactionProfile(
        tcode="QA01",
        description="Create Inspection Lot",
        module="QM",
        auth_requirements=[
            AuthObjectRequirement("Q_QMEL", "ACTVT", ["01"], "Create quality inspection"),
            AuthObjectRequirement("Q_QMEL", "WERKS", ["*"], "Plant"),
        ],
    ),
}


# ---------------------------------------------------------------------------
# Fiori knowledge base
# ---------------------------------------------------------------------------

@dataclass
class FioriAppProfile:
    """Fiori-specific authorization requirements on top of the backend tcode."""

    app_id: str
    app_name: str
    catalog_id: str
    target_mapping: str
    odata_service: str
    backend_tcode: str
    required_roles: List[str]
    launchpad_space: str
    notes: str = ""


FIORI_KB: Dict[str, FioriAppProfile] = {
    "F0718": FioriAppProfile(
        app_id="F0718",
        app_name="Post General Journal Entries",
        catalog_id="SAP_FIN_BC_ACC_JOUR_PC",
        target_mapping="FIN-F0718",
        odata_service="FIN_ACDOC_SRV",
        backend_tcode="FB01",
        required_roles=["SAP_FIN_BC_ACC_JOUR_PC"],
        launchpad_space="Finance",
    ),
    "F0842A": FioriAppProfile(
        app_id="F0842A",
        app_name="Create Purchase Order",
        catalog_id="SAP_MM_BC_PO_MANAGE_PC",
        target_mapping="MM-F0842A",
        odata_service="MM_PUR_PO_MAINT_V2_SRV",
        backend_tcode="ME21N",
        required_roles=["SAP_MM_BC_PO_MANAGE_PC"],
        launchpad_space="Procurement",
    ),
    "F0859": FioriAppProfile(
        app_id="F0859",
        app_name="Create Supplier Invoice",
        catalog_id="SAP_MM_BC_IV_PROCESS_PC",
        target_mapping="MM-F0859",
        odata_service="MM_IV_PROCESS_SRV",
        backend_tcode="MIRO",
        required_roles=["SAP_MM_BC_IV_PROCESS_PC"],
        launchpad_space="Finance",
    ),
    "F0798": FioriAppProfile(
        app_id="F0798",
        app_name="Create Sales Order",
        catalog_id="SAP_SD_BC_SO_MANAGE_PC",
        target_mapping="SD-F0798",
        odata_service="SD_ORDER_SRV_0001",
        backend_tcode="VA01",
        required_roles=["SAP_SD_BC_SO_MANAGE_PC"],
        launchpad_space="Sales",
    ),
    "F2142": FioriAppProfile(
        app_id="F2142",
        app_name="Maintain Users",
        catalog_id="SAP_BASIS_BC_USR_MAINT_PC",
        target_mapping="BASIS-F2142",
        odata_service="USR_USER_MAINT_SRV",
        backend_tcode="SU01",
        required_roles=["SAP_BASIS_BC_USR_MAINT_PC"],
        launchpad_space="Administration",
        notes="Admin-only app — verify Launchpad admin role is assigned.",
    ),
    "F1639": FioriAppProfile(
        app_id="F1639",
        app_name="Supplier Balances",
        catalog_id="SAP_FIN_BC_AP_VEND_BALA_PC",
        target_mapping="FIN-F1639",
        odata_service="FIN_GL_ITEMS_SRV",
        backend_tcode="FBL1N",
        required_roles=["SAP_FIN_BC_AP_VEND_BALA_PC"],
        launchpad_space="Finance",
    ),
}


# ---------------------------------------------------------------------------
# Common issues knowledge base
# ---------------------------------------------------------------------------

@dataclass
class CommonIssue:
    """A curated description of a frequently occurring access failure pattern."""

    issue_id: str
    title: str
    frequency: str          # "very_high" | "high" | "medium" | "low"
    symptom: str
    root_cause: str
    fix: str
    prevention: str
    affected_modules: List[str]


COMMON_ISSUES: List[CommonIssue] = [
    CommonIssue(
        issue_id="CI-001",
        title="Missing Company Code in Auth Object",
        frequency="very_high",
        symptom="User can open the transaction but gets 'No authorization' on company-code-specific data.",
        root_cause="The role contains the correct activity (ACTVT) but the company code field (BUKRS) "
                   "is restricted to a value that does not include the user's operating company.",
        fix="In PFCG, expand the authorization object (e.g. F_BKPF_BUK), add the required company "
            "code to the BUKRS field, regenerate the profile, and run SU25 to update user buffers.",
        prevention="Use org-level variable substitution ($BUKRS) in role templates to avoid manual "
                   "maintenance per company code.",
        affected_modules=["FI", "MM", "SD"],
    ),
    CommonIssue(
        issue_id="CI-002",
        title="User Buffer Not Refreshed After Role Assignment",
        frequency="very_high",
        symptom="Role was assigned but user still receives 'No authorization' until they re-log.",
        root_cause="SAP loads the authorization profile into an in-memory user buffer at logon. "
                   "Changes to role assignments or profiles are not reflected until the buffer is "
                   "rebuilt (at next logon or via SU56).",
        fix="Ask the user to log off and log back in.  Alternatively, execute SU56 > 'Rebuild "
            "Authorization Buffer' for the affected user without forcing a re-logon.",
        prevention="Document this behavior in the access request process so approvers set correct "
                   "expectations with end users.",
        affected_modules=["BASIS", "FI", "MM", "SD", "HR"],
    ),
    CommonIssue(
        issue_id="CI-003",
        title="Role Not Transported to Target System",
        frequency="high",
        symptom="User has correct roles in DEV/QAS but access fails in PRD.",
        root_cause="The role or its authorization profile was created or modified in DEV but the "
                   "transport was not released, imported, or was rejected at a quality gate.",
        fix="Check STMS in PRD for the transport request.  If missing, create a new transport in "
            "DEV (PFCG > Utilities > Create Transport Request), release it, and import via STMS.",
        prevention="Enforce a change management process requiring transport sign-off before access "
                   "requests are marked 'fulfilled'.",
        affected_modules=["BASIS"],
    ),
    CommonIssue(
        issue_id="CI-004",
        title="Role Validity Period Expired",
        frequency="high",
        symptom="User had access previously but lost it without any explicit revocation action.",
        root_cause="The role assignment on the user record (SU01 > Roles tab) has a 'Valid To' "
                   "date that has passed, causing the role to be excluded from the authorization "
                   "check even though the role still appears assigned.",
        fix="In SU01, open the Roles tab, locate the expired assignment, and update the 'Valid To' "
            "date to an appropriate future date (following the change management process).",
        prevention="Configure automated alerts in the access governance workflow to notify role "
                   "owners 30 days before assignments expire.",
        affected_modules=["BASIS", "FI", "MM", "SD"],
    ),
    CommonIssue(
        issue_id="CI-005",
        title="Fiori Tile Visible But App Throws Error",
        frequency="high",
        symptom="The Fiori tile renders on the Launchpad but clicking it produces 'Service Not "
                "Authorized' or 'Access Denied'.",
        root_cause="The catalog role providing the tile was assigned but the OData service "
                   "authorization or the backend ABAP authorization was not included. Catalog "
                   "access and backend access are governed by separate authorization objects.",
        fix="Assign the corresponding backend role (e.g. SAP_FIN_BC_ACC_JOUR_PC) in addition to "
            "the catalog role.  Verify OData scope using /sap/opu/odata/sap/<SRV>/metadata.",
        prevention="Always assign role pairs: (1) Fiori catalog role and (2) backend authorization "
                   "role.  Document this pairing in the role catalog.",
        affected_modules=["BASIS", "FI", "MM", "SD"],
    ),
    CommonIssue(
        issue_id="CI-006",
        title="Plant or Org Level Not Covered",
        frequency="high",
        symptom="User can post/create for some plants or company codes but not others.",
        root_cause="The authorization object restricts access to specific organizational values "
                   "(plant WERKS, purchasing org EKORG, etc.) and the new plant or org unit was "
                   "not added after an organizational change.",
        fix="Identify the restricting auth object and field in SU53 trace output, then add the "
            "missing organizational value in PFCG and re-transport if required.",
        prevention="Maintain an org-level matrix that is reviewed whenever SAP organizational "
                   "structures change (new plants, company codes, sales orgs).",
        affected_modules=["MM", "SD", "FI"],
    ),
    CommonIssue(
        issue_id="CI-007",
        title="User Account Locked",
        frequency="medium",
        symptom="User cannot log on at all, or can log on but actions fail with 'User locked'.",
        root_cause="Account locked by administrator (SU01), by failed logon attempts (max wrong "
                   "password tries per profile parameter login/fails_to_user_lock), or by "
                   "system-wide lock during maintenance.",
        fix="In SU01 > Logon Data tab, click 'Unlock User'.  If locked by failed logons, also "
            "reset the password.  Investigate why the account was locked before unlocking.",
        prevention="Implement account lockout monitoring alerts and a formal unlock request "
                   "process to prevent social-engineering exploitation.",
        affected_modules=["BASIS"],
    ),
    CommonIssue(
        issue_id="CI-008",
        title="Authorization Object Present But ACTVT Value Missing",
        frequency="medium",
        symptom="SU53 shows the auth object but the activity value (e.g. '01' for Create) is "
                "not in the maintained values list.",
        root_cause="When building the role in PFCG, the administrator added the auth object but "
                   "only included certain activity codes (e.g. '03' Display) and omitted the "
                   "required activity (e.g. '01' Create or '02' Change).",
        fix="In PFCG, expand the affected auth object, add the required ACTVT value, save, "
            "regenerate the profile, and distribute to users.",
        prevention="Use the 'Check Authorization' function in PFCG after every role change and "
                   "validate against the transaction's required authorization objects using SU24.",
        affected_modules=["FI", "MM", "SD", "HR", "BASIS"],
    ),
    CommonIssue(
        issue_id="CI-009",
        title="User Validity Dates Expired",
        frequency="medium",
        symptom="User cannot log on at all — system shows 'User not authorized to log on'.",
        root_cause="The user master record has a 'Valid To' date in the past (SU01 > Logon Data).",
        fix="In SU01, update the 'Valid To' field to an appropriate future date.  This is separate "
            "from role validity and controls whether the user account itself is active.",
        prevention="Integrate user validity management with the HR joiner/mover/leaver process "
                   "to automatically extend or expire accounts based on employment status.",
        affected_modules=["BASIS"],
    ),
    CommonIssue(
        issue_id="CI-010",
        title="Profile Parameter Restricts Access",
        frequency="low",
        symptom="Access works in some system clients but not others for the same user and role.",
        root_cause="Client-specific profile parameters (e.g. auth/no_check_in_some_cases) or "
                   "system-level parameter auth/authorization_trace may alter how checks behave "
                   "across clients.",
        fix="Use RZ10 to compare the profile parameter values between the working client and the "
            "failing client.  Align parameter values following the SAP security hardening guide.",
        prevention="Standardize profile parameters across landscape tiers and document deviations.",
        affected_modules=["BASIS"],
    ),
]


# ---------------------------------------------------------------------------
# Mock user and role store
# ---------------------------------------------------------------------------

class _UserStatus(str, Enum):
    ACTIVE = "active"
    LOCKED = "locked"
    EXPIRED = "expired"
    INACTIVE = "inactive"


@dataclass
class _MockUser:
    user_id: str
    display_name: str
    status: _UserStatus
    valid_from: date
    valid_to: date
    user_group: str
    roles: List[str]
    department: str
    lock_reason: Optional[str] = None


@dataclass
class _MockRole:
    role_name: str
    description: str
    transactions: List[str]
    auth_objects: Dict[str, Dict[str, List[str]]]  # obj -> field -> values
    valid_from: date
    valid_to: date
    transported_to: List[str]  # list of system SIDs where this role exists


# NOTE: _MOCK_USERS and _MOCK_ROLES have been replaced by the DB-backed cache
# system (_KB_USERS_CACHE / _KB_ROLES_CACHE).  KB data is loaded exclusively
# from TroubleshooterKBUser / TroubleshooterKBRole DB tables.  No hardcoded
# fallback data is inserted — empty tables yield empty caches.

# Known SoD conflict pairs (role-level, for risk impact reporting)
_SOD_CONFLICTS: List[Tuple[str, str, str]] = [
    ("Z_FI_AP_CLERK", "Z_FI_AP_PAYMENT", "AP Clerk + Payment Posting — payment fraud risk"),
    ("Z_SECURITY_ADMIN", "Z_BASIS_ADMIN", "Security Admin + Basis Admin — unrestricted system access"),
    ("Z_MM_BUYER", "Z_FI_AP_CLERK", "PO Create + Invoice Post — procure-to-pay SoD conflict"),
]


# ---------------------------------------------------------------------------
# DB-backed knowledge-base cache
# ---------------------------------------------------------------------------
# Module-level caches keyed by tenant_id.  Populated lazily on first use via
# _ensure_kb_loaded().  Format matches the _MockUser / _MockRole dataclasses so
# that all downstream diagnostic logic is unchanged.

_KB_USERS_CACHE: Dict[str, Dict[str, _MockUser]] = {}   # tenant_id -> {user_id -> _MockUser}
_KB_ROLES_CACHE: Dict[str, Dict[str, _MockRole]] = {}   # tenant_id -> {role_name -> _MockRole}
_KB_LOADED_TENANTS: set = set()


# _hardcoded_users() and _hardcoded_roles() have been removed.
# The troubleshooter KB is loaded exclusively from the DB tables
# TroubleshooterKBUser and TroubleshooterKBRole.
# If those tables are empty, the engine reports "user not found" / "role not found"
# for any lookup — no fabricated data is ever returned.


def _db_user_to_mock(row: "TroubleshooterKBUser") -> _MockUser:  # type: ignore[name-defined]
    """Convert a DB row to the internal _MockUser dataclass used by the engine."""
    try:
        status = _UserStatus(row.status.lower())
    except ValueError:
        status = _UserStatus.INACTIVE

    valid_from: date
    valid_to: date
    _today = date.today()

    if isinstance(row.valid_from, datetime):
        valid_from = row.valid_from.date()
    elif isinstance(row.valid_from, date):
        valid_from = row.valid_from
    else:
        valid_from = _today - timedelta(days=1)

    if isinstance(row.valid_to, datetime):
        valid_to = row.valid_to.date()
    elif isinstance(row.valid_to, date):
        valid_to = row.valid_to
    else:
        valid_to = _today - timedelta(days=1)

    return _MockUser(
        user_id=row.user_ext_id.upper(),
        display_name=row.full_name,
        status=status,
        valid_from=valid_from,
        valid_to=valid_to,
        user_group=row.department or "",
        roles=list(row.roles) if row.roles else [],
        department=row.department or "",
        lock_reason=getattr(row, "lock_reason", None),
    )


def _db_role_to_mock(row: "TroubleshooterKBRole") -> _MockRole:  # type: ignore[name-defined]
    """Convert a DB row to the internal _MockRole dataclass used by the engine."""
    _today = date.today()

    # Roles in the DB have no valid_from / valid_to columns; default to active.
    valid_from = _today - timedelta(days=1)
    valid_to = _today + timedelta(days=365)

    # auth_objects stored as dict {obj: {field: [values]}} — same shape as _MockRole expects.
    raw_auth = row.auth_objects
    if isinstance(raw_auth, dict):
        auth_objects: Dict[str, Dict[str, List[str]]] = raw_auth
    else:
        auth_objects = {}

    return _MockRole(
        role_name=row.role_name,
        description=row.description or "",
        transactions=list(row.transactions) if row.transactions else [],
        auth_objects=auth_objects,
        valid_from=valid_from,
        valid_to=valid_to,
        transported_to=list(row.systems_deployed) if row.systems_deployed else [],
    )


def _ensure_kb_loaded(tenant_id: str = "tenant_default") -> None:
    """
    Ensure the in-memory KB caches are populated for *tenant_id*.

    Strategy
    --------
    1. If the cache already contains data for this tenant, return immediately.
    2. Query ``TroubleshooterKBUser`` and ``TroubleshooterKBRole`` for the
       tenant from the database.
    3. If the tables are empty, the caches remain empty — no fabricated data
       is inserted.  The engine will report "user not found" / "role not found"
       for any lookup until real data is loaded via the admin import API.
    4. Convert DB rows to ``_MockUser`` / ``_MockRole`` adapter objects and
       store them in the module-level caches.

    The function is intentionally safe to call multiple times — it is a no-op
    after the first successful load.
    """
    if tenant_id in _KB_LOADED_TENANTS:
        return

    try:
        from db.models.intelligence import (  # local import to avoid circular deps
            TroubleshooterKBUser,
            TroubleshooterKBRole,
        )
        from db.database import db_manager

        if not db_manager._initialized:
            db_manager.init()

        with db_manager.session_scope() as session:
            user_rows = (
                session.query(TroubleshooterKBUser)
                .filter(TroubleshooterKBUser.tenant_id == tenant_id)
                .all()
            )

            role_rows = (
                session.query(TroubleshooterKBRole)
                .filter(TroubleshooterKBRole.tenant_id == tenant_id)
                .all()
            )

            # Build caches from DB rows (empty if no rows present)
            users_cache: Dict[str, _MockUser] = {}
            for r in user_rows:
                try:
                    mu = _db_user_to_mock(r)
                    users_cache[mu.user_id] = mu
                except Exception as exc:
                    logger.warning("Failed to convert KB user row id=%s: %s", r.id, exc)

            roles_cache: Dict[str, _MockRole] = {}
            for r in role_rows:
                try:
                    mr = _db_role_to_mock(r)
                    roles_cache[mr.role_name] = mr
                except Exception as exc:
                    logger.warning("Failed to convert KB role row id=%s: %s", r.id, exc)

        _KB_USERS_CACHE[tenant_id] = users_cache
        _KB_ROLES_CACHE[tenant_id] = roles_cache
        _KB_LOADED_TENANTS.add(tenant_id)
        logger.info(
            "Troubleshooter KB loaded from DB for tenant '%s': %d users, %d roles",
            tenant_id, len(users_cache), len(roles_cache),
        )

    except Exception as exc:
        logger.warning(
            "Troubleshooter KB DB load failed for tenant '%s' (%s); "
            "starting with empty KB caches.",
            tenant_id, exc,
        )
        # Return empty caches on DB failure — never fabricate data.
        # The engine will report "user not found" for any lookup until the DB
        # is available and the cache is reloaded.
        if tenant_id not in _KB_USERS_CACHE:
            _KB_USERS_CACHE[tenant_id] = {}
        if tenant_id not in _KB_ROLES_CACHE:
            _KB_ROLES_CACHE[tenant_id] = {}
        _KB_LOADED_TENANTS.add(tenant_id)


# ---------------------------------------------------------------------------
# Diagnosis history store (in-memory; session-scoped)
# ---------------------------------------------------------------------------

_DIAGNOSIS_HISTORY: List[DiagnosisResult] = []
_MAX_HISTORY = 200


def _record_history(result: DiagnosisResult) -> None:
    _DIAGNOSIS_HISTORY.append(result)
    if len(_DIAGNOSIS_HISTORY) > _MAX_HISTORY:
        _DIAGNOSIS_HISTORY.pop(0)


# ---------------------------------------------------------------------------
# Main engine
# ---------------------------------------------------------------------------

class AccessTroubleshooter:
    """
    AI-powered diagnostic engine for SAP access failures.

    The engine runs an ordered diagnostic chain.  Each step is independent;
    the chain short-circuits at the first definitive blocking failure and
    continues past non-blocking warnings.  Confidence is reduced when the
    root cause is ambiguous (e.g. multiple partial failures).

    Usage
    -----
    ::

        engine = AccessTroubleshooter()
        result = engine.diagnose(
            TroubleshootRequest(
                user_id="<SAP_USER_ID>",
                transaction="FB01",
                system="PRD",
            )
        )
        print(result.root_cause)

    Sub-classing
    ------------
    Override ``_fetch_user``, ``_fetch_roles``, and ``_fetch_role_detail`` to
    plug in live SAP RFC calls or a database-backed connector instead of the
    built-in DB-backed KB cache.
    """

    def __init__(self) -> None:
        self._transaction_kb: Dict[str, TransactionProfile] = TRANSACTION_KB
        self._fiori_kb: Dict[str, FioriAppProfile] = FIORI_KB

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def diagnose(self, request: TroubleshootRequest) -> DiagnosisResult:
        """
        Run the full diagnostic chain and return a ``DiagnosisResult``.

        Parameters
        ----------
        request:
            A fully-populated ``TroubleshootRequest``.

        Returns
        -------
        DiagnosisResult
            Structured result including root cause, all diagnostic steps,
            recommended fix, and risk impact of applying the fix.
        """
        steps: List[DiagnosisStep] = []
        blocking_step: Optional[DiagnosisStep] = None

        # Ensure KB data is loaded from DB for this tenant (cached after first call)
        _ensure_kb_loaded(request.tenant_id)

        # Determine whether input is a Fiori app ID or a classic tcode
        is_fiori = self._is_fiori_app(request.transaction)
        tcode = self._resolve_tcode(request.transaction)
        tcode_profile = self._transaction_kb.get(tcode)

        # Retrieve user and role data from DB-backed cache
        user = self._fetch_user(request.user_id, request.tenant_id)
        user_roles = self._fetch_user_roles(request.user_id, request.tenant_id)

        # ---- Chain -------------------------------------------------------

        # Step 1: User existence
        step = self._check_user_exists(request.user_id, user)
        steps.append(step)
        if step.status == CheckStatus.FAIL:
            blocking_step = step

        if blocking_step is None:
            # Step 2: User active / not locked
            step = self._check_user_active(user)
            steps.append(step)
            if step.status == CheckStatus.FAIL:
                blocking_step = step

        if blocking_step is None:
            # Step 3: User validity dates
            step = self._check_user_validity(user)
            steps.append(step)
            if step.status == CheckStatus.FAIL:
                blocking_step = step

        if blocking_step is None:
            # Step 4: Any roles assigned
            step = self._check_roles_assigned(user, user_roles)
            steps.append(step)
            if step.status == CheckStatus.FAIL:
                blocking_step = step

        if blocking_step is None:
            # Step 5: Transaction known in KB
            step = self._check_transaction_known(request.transaction, tcode_profile)
            steps.append(step)
            # Not blocking — we continue even if the tcode is unknown

            # Step 6: Does any role include the transaction?
            step6, covering_roles = self._check_tcode_in_roles(tcode, user_roles)
            steps.append(step6)
            if step6.status == CheckStatus.FAIL:
                blocking_step = step6

        if blocking_step is None and tcode_profile:
            # Step 7: Authorization objects present and correct
            step7, auth_gaps = self._check_auth_objects(tcode, tcode_profile, user_roles, request.system)
            steps.append(step7)
            if step7.status == CheckStatus.FAIL:
                blocking_step = step7
            elif step7.status == CheckStatus.WARNING and auth_gaps:
                # Do not block, but record partial
                pass

            # Step 8: Org-level values
            step = self._check_org_level_values(tcode_profile, user_roles)
            steps.append(step)
            if step.status == CheckStatus.FAIL and blocking_step is None:
                blocking_step = step

        if blocking_step is None:
            # Step 9: Role validity dates
            step, expired_roles = self._check_role_validity(user_roles)
            steps.append(step)
            if step.status == CheckStatus.FAIL:
                blocking_step = step

        if blocking_step is None:
            # Step 10: User buffer / comparison
            step = self._check_user_buffer(request.user_id, user)
            steps.append(step)

        if blocking_step is None:
            # Step 11: Transport consistency (role in DEV but not in system)
            step = self._check_transport_consistency(user_roles, request.system)
            steps.append(step)
            if step.status == CheckStatus.FAIL:
                blocking_step = step

        if blocking_step is None and is_fiori:
            # Step 12: Fiori-specific checks (catalog, OData, target mapping)
            fiori_steps = self._check_fiori_stack(request.transaction, user_roles)
            steps.extend(fiori_steps)
            for fs in fiori_steps:
                if fs.status == CheckStatus.FAIL and blocking_step is None:
                    blocking_step = fs

        # ------------------------------------------------------------------
        # Determine overall status and build result
        # ------------------------------------------------------------------

        status, root_cause, confidence = self._derive_verdict(
            blocking_step=blocking_step,
            steps=steps,
            request=request,
            tcode_profile=tcode_profile,
        )

        recommended_fix, fix_time = self._recommend_fix(blocking_step, tcode_profile, is_fiori)
        risk_impact = self._assess_risk_impact(
            recommended_fix=recommended_fix,
            user_roles=user_roles,
            tcode=tcode,
        )

        result = DiagnosisResult(
            diagnosis_id=str(uuid.uuid4()),
            request=request,
            status=status,
            root_cause=root_cause,
            diagnosis_steps=steps,
            recommended_fix=recommended_fix,
            estimated_fix_time=fix_time,
            risk_impact=risk_impact,
            confidence_score=confidence,
        )

        _record_history(result)
        return result

    def batch_diagnose(
        self,
        user_ids: List[str],
        transaction: str,
        system: str,
        tenant_id: str = "tenant_default",
        requested_by: str = "system",
    ) -> List[DiagnosisResult]:
        """
        Diagnose multiple users for the same transaction and system.

        Parameters
        ----------
        user_ids:
            List of SAP user logon names.
        transaction:
            Transaction code or Fiori app ID.
        system:
            Target system SID.
        tenant_id:
            GovernexPlus tenant identifier.
        requested_by:
            User ID of the analyst initiating the batch.

        Returns
        -------
        list of DiagnosisResult
            One result per user, in the same order as ``user_ids``.
        """
        results = []
        for uid in user_ids:
            req = TroubleshootRequest(
                user_id=uid,
                transaction=transaction,
                system=system,
                tenant_id=tenant_id,
                requested_by=requested_by,
            )
            results.append(self.diagnose(req))
        return results

    # ------------------------------------------------------------------
    # Data-access layer (overridable for live connector integration)
    # ------------------------------------------------------------------

    def _fetch_user(
        self, user_id: str, tenant_id: str = "tenant_default"
    ) -> Optional[_MockUser]:
        """
        Return a user record for *user_id* from the DB-backed KB cache.

        The cache is populated from the DB by ``_ensure_kb_loaded`` which is
        called in ``diagnose`` before this method is reached.  Returns None
        if the user is not found in the DB-backed cache.
        """
        cache = _KB_USERS_CACHE.get(tenant_id, {})
        return cache.get(user_id.upper())

    def _fetch_user_roles(
        self, user_id: str, tenant_id: str = "tenant_default"
    ) -> List[_MockRole]:
        """
        Return a list of role detail objects assigned to *user_id* from the
        DB-backed KB cache.

        Role names are read from the user's ``roles`` JSON list, then resolved
        to ``_MockRole`` objects from the roles cache.  Unknown role names are
        silently skipped (they are not in the troubleshooter KB).
        """
        user_cache = _KB_USERS_CACHE.get(tenant_id, {})
        user = user_cache.get(user_id.upper())
        if not user:
            return []
        role_cache = _KB_ROLES_CACHE.get(tenant_id, {})
        return [role_cache[rn] for rn in user.roles if rn in role_cache]

    # ------------------------------------------------------------------
    # Diagnostic step implementations
    # ------------------------------------------------------------------

    def _check_user_exists(
        self, user_id: str, user: Optional[_MockUser]
    ) -> DiagnosisStep:
        if user and user.status != _UserStatus.INACTIVE:
            return DiagnosisStep(
                check_name="user_exists",
                display_name="User Account Exists",
                status=CheckStatus.PASS,
                detail=f"User '{user_id}' found: {user.display_name} ({user.department}).",
            )
        return DiagnosisStep(
            check_name="user_exists",
            display_name="User Account Exists",
            status=CheckStatus.FAIL,
            detail=f"User '{user_id}' does not exist in the target system.",
            recommendation=(
                "Verify the user ID is correct.  If the user needs to be created, "
                "submit a new-user provisioning request through the access request portal."
            ),
            technical_detail="SU01 lookup returned no result for this user ID.",
        )

    def _check_user_active(self, user: _MockUser) -> DiagnosisStep:
        if user.status == _UserStatus.ACTIVE:
            return DiagnosisStep(
                check_name="user_active",
                display_name="User Account Status",
                status=CheckStatus.PASS,
                detail=f"Account status is ACTIVE.",
            )
        if user.status == _UserStatus.LOCKED:
            return DiagnosisStep(
                check_name="user_active",
                display_name="User Account Status",
                status=CheckStatus.FAIL,
                detail=(
                    f"User account is LOCKED.  "
                    f"Reason: {user.lock_reason or 'Not specified'}."
                ),
                recommendation=(
                    "Navigate to SU01 > Logon Data tab and click 'Unlock User'. "
                    "Investigate the lock reason before unlocking — if caused by "
                    "repeated failed logons, also reset the password and notify the user."
                ),
                technical_detail=f"SU01 lock indicator set.  Lock reason: {user.lock_reason}",
            )
        return DiagnosisStep(
            check_name="user_active",
            display_name="User Account Status",
            status=CheckStatus.FAIL,
            detail=f"Account status is {user.status.value.upper()}.",
            recommendation=(
                "Review the user account status in SU01 and reactivate if the account "
                "should remain active.  Ensure the reactivation is authorised via a "
                "formal change request."
            ),
        )

    def _check_user_validity(self, user: _MockUser) -> DiagnosisStep:
        today = date.today()
        if user.valid_to < today:
            return DiagnosisStep(
                check_name="user_validity",
                display_name="User Validity Dates",
                status=CheckStatus.FAIL,
                detail=(
                    f"User validity period expired on {user.valid_to.isoformat()}.  "
                    f"The account has been expired for {(today - user.valid_to).days} day(s)."
                ),
                recommendation=(
                    "In SU01 > Logon Data, update the 'Valid To' field to an appropriate "
                    "future date.  This must follow the organisation's joiner/mover/leaver "
                    "process and requires manager approval."
                ),
                technical_detail=(
                    f"Valid From: {user.valid_from.isoformat()}  "
                    f"Valid To: {user.valid_to.isoformat()}  "
                    f"Today: {today.isoformat()}"
                ),
            )
        days_remaining = (user.valid_to - today).days
        status = CheckStatus.PASS if days_remaining > 30 else CheckStatus.WARNING
        detail = (
            f"User validity is current.  Valid from {user.valid_from.isoformat()} "
            f"to {user.valid_to.isoformat()} ({days_remaining} day(s) remaining)."
        )
        recommendation = (
            f"Account expires in {days_remaining} day(s).  "
            "Initiate an extension request before expiry to avoid access disruption."
            if days_remaining <= 30
            else ""
        )
        return DiagnosisStep(
            check_name="user_validity",
            display_name="User Validity Dates",
            status=status,
            detail=detail,
            recommendation=recommendation,
        )

    def _check_roles_assigned(
        self, user: _MockUser, roles: List[_MockRole]
    ) -> DiagnosisStep:
        if roles:
            role_list = ", ".join(r.role_name for r in roles)
            return DiagnosisStep(
                check_name="roles_assigned",
                display_name="Roles Assigned to User",
                status=CheckStatus.PASS,
                detail=f"{len(roles)} role(s) assigned: {role_list}.",
                technical_detail=f"Role names: {role_list}",
            )
        return DiagnosisStep(
            check_name="roles_assigned",
            display_name="Roles Assigned to User",
            status=CheckStatus.FAIL,
            detail="No roles are assigned to this user.",
            recommendation=(
                "Submit an access request for the appropriate role(s) in the access "
                "request portal.  The approver and security administrator must assign "
                "and activate the role via SU01 > Roles tab."
            ),
            technical_detail="SU01 > Roles tab is empty for this user.",
        )

    def _check_transaction_known(
        self, transaction: str, profile: Optional[TransactionProfile]
    ) -> DiagnosisStep:
        if profile:
            return DiagnosisStep(
                check_name="transaction_known",
                display_name="Transaction in Knowledge Base",
                status=CheckStatus.INFO,
                detail=(
                    f"Transaction '{transaction}' is known: {profile.description} "
                    f"(Module: {profile.module}).  "
                    f"Auth objects to check: "
                    f"{', '.join(r.auth_object for r in profile.auth_requirements)}."
                ),
                technical_detail=f"Module: {profile.module}  Sensitive: {profile.sensitive}",
            )
        return DiagnosisStep(
            check_name="transaction_known",
            display_name="Transaction in Knowledge Base",
            status=CheckStatus.WARNING,
            detail=(
                f"Transaction '{transaction}' is not in the GovernexPlus knowledge base.  "
                "Authorization analysis will be limited to role and tcode coverage checks."
            ),
            recommendation=(
                "Use transaction SU24 in SAP to view the authorization objects maintained "
                "for this transaction code.  Then validate those objects in PFCG."
            ),
        )

    def _check_tcode_in_roles(
        self, tcode: str, roles: List[_MockRole]
    ) -> Tuple[DiagnosisStep, List[str]]:
        covering = [r.role_name for r in roles if tcode in r.transactions]
        if covering:
            return (
                DiagnosisStep(
                    check_name="tcode_in_roles",
                    display_name="Transaction Covered by Role",
                    status=CheckStatus.PASS,
                    detail=(
                        f"Transaction '{tcode}' is included in {len(covering)} role(s): "
                        f"{', '.join(covering)}."
                    ),
                    technical_detail=f"Covering roles: {', '.join(covering)}",
                ),
                covering,
            )
        return (
            DiagnosisStep(
                check_name="tcode_in_roles",
                display_name="Transaction Covered by Role",
                status=CheckStatus.FAIL,
                detail=(
                    f"Transaction '{tcode}' is not present in any of the user's "
                    f"{len(roles)} assigned role(s).  The role menu check will fail at logon."
                ),
                recommendation=(
                    f"Identify which role should grant '{tcode}' access (use PFCG to search "
                    f"by transaction code), then submit an access request for that role. "
                    f"Alternatively, if using a custom role, add '{tcode}' to the role menu "
                    f"in PFCG and regenerate the authorization profile."
                ),
                technical_detail=(
                    f"User roles checked: {', '.join(r.role_name for r in roles)}.  "
                    f"None contain tcode '{tcode}'."
                ),
            ),
            [],
        )

    def _check_auth_objects(
        self,
        tcode: str,
        profile: TransactionProfile,
        roles: List[_MockRole],
        system: str,
    ) -> Tuple[DiagnosisStep, List[str]]:
        """
        Check whether the required auth objects are present with sufficient values.

        Returns the step and a list of gap descriptions for downstream use.
        """
        gaps: List[str] = []
        all_role_objects: Dict[str, Dict[str, List[str]]] = {}
        for role in roles:
            for obj, fields in role.auth_objects.items():
                if obj not in all_role_objects:
                    all_role_objects[obj] = {}
                for fld, vals in fields.items():
                    existing = all_role_objects[obj].get(fld, [])
                    all_role_objects[obj][fld] = list(set(existing + vals))

        for req in profile.auth_requirements:
            if req.auth_object not in all_role_objects:
                if req.is_critical:
                    gaps.append(
                        f"MISSING critical auth object '{req.auth_object}' "
                        f"(required for: {req.description})"
                    )
                continue
            obj_data = all_role_objects[req.auth_object]
            field_data = obj_data.get(req.field_name, [])
            if not field_data:
                gaps.append(
                    f"Auth object '{req.auth_object}' present but field "
                    f"'{req.field_name}' has no values maintained."
                )
                continue
            if "*" in field_data:
                continue  # Wildcard — fully authorized
            # Check if any required value is covered
            missing = [v for v in req.required_values if v not in field_data and "*" not in field_data]
            if missing and req.is_critical:
                gaps.append(
                    f"Auth object '{req.auth_object}' field '{req.field_name}': "
                    f"required value(s) {missing} not found in maintained values {field_data}."
                )

        if not gaps:
            return (
                DiagnosisStep(
                    check_name="auth_objects",
                    display_name="Authorization Objects",
                    status=CheckStatus.PASS,
                    detail=(
                        f"All {len(profile.auth_requirements)} required authorization "
                        f"object(s) for '{tcode}' are present with appropriate values."
                    ),
                    technical_detail=(
                        f"Objects checked: "
                        f"{', '.join(r.auth_object for r in profile.auth_requirements)}"
                    ),
                ),
                [],
            )

        # Partial gaps — could be warning or fail depending on criticality
        critical_gaps = [g for g in gaps if "MISSING critical" in g or "required value(s)" in g]
        if critical_gaps:
            return (
                DiagnosisStep(
                    check_name="auth_objects",
                    display_name="Authorization Objects",
                    status=CheckStatus.FAIL,
                    detail=(
                        f"{len(gaps)} authorization gap(s) found for transaction '{tcode}': "
                        f"{gaps[0]}"
                        + (f" (and {len(gaps)-1} more)" if len(gaps) > 1 else "")
                        + "."
                    ),
                    recommendation=(
                        "Open the role in PFCG, navigate to the Authorizations tab, and add "
                        "the missing authorization object(s) or extend the field values as "
                        "identified above.  After saving, regenerate the profile (Generate icon) "
                        "and ask the user to re-log for the buffer to refresh."
                    ),
                    technical_detail="\n".join(gaps),
                ),
                gaps,
            )

        return (
            DiagnosisStep(
                check_name="auth_objects",
                display_name="Authorization Objects",
                status=CheckStatus.WARNING,
                detail=(
                    f"{len(gaps)} minor authorization gap(s) for '{tcode}'.  "
                    "Access may be partial."
                ),
                recommendation=(
                    "Review the auth object field values in PFCG and extend where needed."
                ),
                technical_detail="\n".join(gaps),
            ),
            gaps,
        )

    def _check_org_level_values(
        self, profile: TransactionProfile, roles: List[_MockRole]
    ) -> DiagnosisStep:
        """
        Check that organizational-level fields are populated and non-restrictive.
        """
        org_fields = {
            "BUKRS": "Company Code",
            "WERKS": "Plant",
            "EKORG": "Purchasing Organization",
            "VKORG": "Sales Organization",
            "PERSA": "Personnel Area",
            "KOKRS": "Controlling Area",
            "GSBER": "Business Area",
        }
        issues: List[str] = []
        for role in roles:
            for obj_name, fields in role.auth_objects.items():
                for fld, vals in fields.items():
                    if fld in org_fields and vals and vals != ["*"]:
                        # Has restrictive values — flag for informational purposes
                        pass  # handled by auth_objects check

        # Check if any role has empty org-level fields
        for role in roles:
            for req in profile.auth_requirements:
                obj_data = role.auth_objects.get(req.auth_object, {})
                fld_vals = obj_data.get(req.field_name, [])
                if req.field_name in org_fields and not fld_vals:
                    issues.append(
                        f"Role '{role.role_name}': org field '{req.field_name}' "
                        f"({org_fields[req.field_name]}) is empty in auth object "
                        f"'{req.auth_object}'."
                    )

        if not issues:
            return DiagnosisStep(
                check_name="org_level_values",
                display_name="Organizational Level Values",
                status=CheckStatus.PASS,
                detail=(
                    "All organizational level field values (company code, plant, etc.) "
                    "appear consistent with the transaction requirements."
                ),
            )
        return DiagnosisStep(
            check_name="org_level_values",
            display_name="Organizational Level Values",
            status=CheckStatus.FAIL,
            detail=(
                f"{len(issues)} organizational field gap(s) found: {issues[0]}"
                + (f" (and {len(issues)-1} more)" if len(issues) > 1 else "")
                + "."
            ),
            recommendation=(
                "Open the affected role in PFCG > Authorizations tab.  Locate the "
                "organizational-level field (shown with a globe icon) and enter the "
                "required value(s).  After saving, regenerate the profile."
            ),
            technical_detail="\n".join(issues),
        )

    def _check_role_validity(
        self, roles: List[_MockRole]
    ) -> Tuple[DiagnosisStep, List[str]]:
        today = date.today()
        expired = [
            r.role_name
            for r in roles
            if r.valid_to < today
        ]
        expiring_soon = [
            r.role_name
            for r in roles
            if today <= r.valid_to <= today + timedelta(days=30)
        ]

        if expired:
            return (
                DiagnosisStep(
                    check_name="role_validity",
                    display_name="Role Assignment Validity",
                    status=CheckStatus.FAIL,
                    detail=(
                        f"The following role assignment(s) have expired and will not be "
                        f"included in the authorization check: {', '.join(expired)}."
                    ),
                    recommendation=(
                        "In SU01 > Roles tab, locate the expired role assignment(s) and "
                        "extend the 'Valid To' date.  This requires an authorised access "
                        "request and manager approval."
                    ),
                    technical_detail=f"Expired roles: {', '.join(expired)}",
                ),
                expired,
            )

        if expiring_soon:
            return (
                DiagnosisStep(
                    check_name="role_validity",
                    display_name="Role Assignment Validity",
                    status=CheckStatus.WARNING,
                    detail=(
                        f"The following role(s) expire within 30 days: "
                        f"{', '.join(expiring_soon)}.  Access will be lost without renewal."
                    ),
                    recommendation=(
                        "Initiate a role assignment renewal request immediately to prevent "
                        "unexpected access loss."
                    ),
                ),
                expiring_soon,
            )

        return (
            DiagnosisStep(
                check_name="role_validity",
                display_name="Role Assignment Validity",
                status=CheckStatus.PASS,
                detail="All role assignments have current validity dates.",
            ),
            [],
        )

    def _check_user_buffer(
        self, user_id: str, user: Optional[_MockUser]
    ) -> DiagnosisStep:
        """
        Heuristic check for user buffer staleness.

        In a live connector this would compare SU01 role list with UST10S/UST12
        profile data and flag mismatches.  In the mock we simulate a small
        probability of a stale buffer for active users.
        """
        if user is None or user.status != _UserStatus.ACTIVE:
            return DiagnosisStep(
                check_name="user_buffer",
                display_name="User Authorization Buffer",
                status=CheckStatus.SKIPPED,
                detail="Buffer check skipped — user is not active.",
            )

        # Deterministic simulation: buffer considered stale if user_id ends in 'I'
        stale = user_id.upper().endswith("I")
        if stale:
            return DiagnosisStep(
                check_name="user_buffer",
                display_name="User Authorization Buffer",
                status=CheckStatus.WARNING,
                detail=(
                    "The user's authorization buffer may be out of sync with the current "
                    "role assignments.  This can occur after recent role changes without "
                    "a re-logon."
                ),
                recommendation=(
                    "Ask the user to log off and log back in, which rebuilds the buffer.  "
                    "Alternatively, run SU56 for the user and click 'Rebuild Authorization "
                    "Buffer' without forcing a re-logon."
                ),
                technical_detail=(
                    "Comparison of UST10S (current roles) vs authorization buffer "
                    "shows potential discrepancy."
                ),
            )

        return DiagnosisStep(
            check_name="user_buffer",
            display_name="User Authorization Buffer",
            status=CheckStatus.PASS,
            detail=(
                "User authorization buffer appears current.  No recent role changes "
                "detected that would require a buffer rebuild."
            ),
        )

    def _check_transport_consistency(
        self, roles: List[_MockRole], system: str
    ) -> DiagnosisStep:
        """
        Check that all assigned roles have been transported to the target system.
        """
        missing_in_system: List[str] = [
            r.role_name
            for r in roles
            if system.upper() not in [s.upper() for s in r.transported_to]
        ]

        if missing_in_system:
            return DiagnosisStep(
                check_name="transport_consistency",
                display_name="Transport Consistency (Role in Target System)",
                status=CheckStatus.FAIL,
                detail=(
                    f"The following role(s) exist in the source system but have NOT been "
                    f"transported to '{system}': {', '.join(missing_in_system)}."
                ),
                recommendation=(
                    "In the source system (typically DEV or QAS), create a transport "
                    "request for the missing role(s) via PFCG > Utilities > Create Transport "
                    "Request.  Release the request and import it into the target system via "
                    "STMS.  Follow the change management process and obtain required approvals."
                ),
                technical_detail=(
                    f"Roles not found in system '{system}': {', '.join(missing_in_system)}.  "
                    f"Check STMS import queue in '{system}' for pending transports."
                ),
            )

        return DiagnosisStep(
            check_name="transport_consistency",
            display_name="Transport Consistency (Role in Target System)",
            status=CheckStatus.PASS,
            detail=(
                f"All {len(roles)} assigned role(s) have been transported to "
                f"system '{system}'."
            ),
        )

    def _check_fiori_stack(
        self, app_id: str, roles: List[_MockRole]
    ) -> List[DiagnosisStep]:
        """
        Run Fiori-specific checks: catalog availability, target mapping,
        OData service authorization, and backend auth.
        """
        steps: List[DiagnosisStep] = []
        fiori_profile = self._fiori_kb.get(app_id.upper())

        # Step A: Catalog
        if not fiori_profile:
            steps.append(
                DiagnosisStep(
                    check_name="fiori_catalog",
                    display_name="Fiori: Catalog Assignment",
                    status=CheckStatus.WARNING,
                    detail=(
                        f"Fiori app '{app_id}' not found in the GovernexPlus Fiori KB.  "
                        "Cannot validate catalog or OData service automatically."
                    ),
                    recommendation=(
                        "Manually verify in the Fiori Launchpad Designer that the app is "
                        "included in a catalog assigned to the user's roles."
                    ),
                )
            )
            return steps

        catalog_covered = any(
            fiori_profile.catalog_id in r.role_name or
            any(fiori_profile.backend_tcode in r.transactions for r in [r])
            for r in roles
        )
        steps.append(
            DiagnosisStep(
                check_name="fiori_catalog",
                display_name="Fiori: Catalog Assignment",
                status=CheckStatus.PASS if catalog_covered else CheckStatus.FAIL,
                detail=(
                    f"Catalog '{fiori_profile.catalog_id}' "
                    + (
                        "is accessible via the user's roles."
                        if catalog_covered
                        else "is NOT accessible via the user's roles.  "
                             "The Fiori tile will not appear on the Launchpad."
                    )
                ),
                recommendation=(
                    ""
                    if catalog_covered
                    else (
                        f"Assign the catalog role '{fiori_profile.catalog_id}' to the user.  "
                        "This is separate from the backend authorization role."
                    )
                ),
                technical_detail=(
                    f"App ID: {fiori_profile.app_id}  "
                    f"Catalog: {fiori_profile.catalog_id}  "
                    f"Space: {fiori_profile.launchpad_space}"
                ),
            )
        )

        # Step B: Target Mapping
        steps.append(
            DiagnosisStep(
                check_name="fiori_target_mapping",
                display_name="Fiori: Target Mapping",
                status=CheckStatus.INFO,
                detail=(
                    f"Target mapping '{fiori_profile.target_mapping}' should route "
                    f"app '{app_id}' to backend transaction '{fiori_profile.backend_tcode}'."
                ),
                recommendation=(
                    "If the app launches but immediately errors, verify the target mapping "
                    "in Launchpad Designer (Settings > Target Mappings) points to the "
                    f"correct semantic object and action for {fiori_profile.backend_tcode}."
                ),
            )
        )

        # Step C: OData Service
        steps.append(
            DiagnosisStep(
                check_name="fiori_odata",
                display_name="Fiori: OData Service Authorization",
                status=CheckStatus.INFO,
                detail=(
                    f"OData service '{fiori_profile.odata_service}' must be activated "
                    "in /IWFND/MAINT_SERVICE and the user must have S_SERVICE authorization."
                ),
                recommendation=(
                    f"Check /IWFND/ERROR_LOG for '{fiori_profile.odata_service}' errors.  "
                    "Ensure the service is activated in /IWFND/MAINT_SERVICE and that the "
                    "Fiori backend role includes S_SERVICE with the correct service name."
                ),
                technical_detail=(
                    f"OData service: {fiori_profile.odata_service}  "
                    f"Endpoint: /sap/opu/odata/sap/{fiori_profile.odata_service}/"
                ),
            )
        )

        # Step D: Backend auth note
        steps.append(
            DiagnosisStep(
                check_name="fiori_backend_auth",
                display_name="Fiori: Backend Authorization",
                status=CheckStatus.INFO,
                detail=(
                    f"Fiori app '{app_id}' executes backend transaction "
                    f"'{fiori_profile.backend_tcode}'.  Backend auth objects must also be "
                    f"authorized (checked separately in Authorization Objects step)."
                ),
                recommendation=(
                    "Assign both the Fiori catalog role "
                    f"({fiori_profile.catalog_id}) AND the backend authorization role "
                    f"({', '.join(fiori_profile.required_roles)}).  "
                    "These are two distinct role assignments."
                ),
            )
        )

        return steps

    # ------------------------------------------------------------------
    # Verdict and fix derivation
    # ------------------------------------------------------------------

    def _derive_verdict(
        self,
        blocking_step: Optional[DiagnosisStep],
        steps: List[DiagnosisStep],
        request: TroubleshootRequest,
        tcode_profile: Optional[TransactionProfile],
    ) -> Tuple[DiagnosisStatus, str, float]:
        """
        Determine overall status, root cause string, and confidence score.
        """
        warning_count = sum(1 for s in steps if s.status == CheckStatus.WARNING)
        fail_count = sum(1 for s in steps if s.status == CheckStatus.FAIL)

        if fail_count == 0:
            confidence = max(0.70, 0.95 - (warning_count * 0.05))
            if warning_count == 0:
                return (
                    DiagnosisStatus.ACCESS_GRANTED,
                    (
                        f"All diagnostic checks passed.  User '{request.user_id}' appears "
                        f"to have valid access to '{request.transaction}' on system "
                        f"'{request.system}'.  If the user still reports an issue, request "
                        "a live SU53 trace from the user during the failed attempt."
                    ),
                    confidence,
                )
            return (
                DiagnosisStatus.PARTIAL_ACCESS,
                (
                    f"No critical failures detected, but {warning_count} warning(s) suggest "
                    f"access may be partial or at risk.  Check warning steps for details."
                ),
                confidence,
            )

        if blocking_step is None:
            # Should not happen, but be defensive
            blocking_step = next((s for s in steps if s.status == CheckStatus.FAIL), None)

        root_cause = blocking_step.detail if blocking_step else "Unknown failure."
        # Reduce confidence if multiple failures coexist (ambiguous root cause)
        confidence = max(0.50, 0.92 - ((fail_count - 1) * 0.12) - (warning_count * 0.04))

        return DiagnosisStatus.ACCESS_DENIED, root_cause, confidence

    def _recommend_fix(
        self,
        blocking_step: Optional[DiagnosisStep],
        tcode_profile: Optional[TransactionProfile],
        is_fiori: bool,
    ) -> Tuple[str, str]:
        """
        Return (recommended_fix, estimated_fix_time) based on the blocking step.
        """
        if blocking_step is None:
            return (
                "No fix required.  Access appears to be in order.  "
                "If the issue persists, collect a SU53 trace for deeper analysis.",
                "N/A",
            )

        fix_map: Dict[str, Tuple[str, str]] = {
            "user_exists": (
                "Create the user account via SU01 or the provisioning workflow, or verify the "
                "correct user ID with the helpdesk.",
                "1-2 business days",
            ),
            "user_active": (
                "Unlock the user in SU01 > Logon Data.  Reset the password if locked due to "
                "failed attempts.  Document the unlock in the incident management system.",
                "15-30 minutes",
            ),
            "user_validity": (
                "Extend the user validity date in SU01 > Logon Data.  Obtain manager approval "
                "and submit a change request following the access governance process.",
                "1-4 hours (including approval)",
            ),
            "roles_assigned": (
                "Submit an access request for the appropriate role(s) through the GovernexPlus "
                "access request portal.  The request will route to the role owner and manager "
                "for approval before the security team assigns it in SU01.",
                "1-3 business days (including approval)",
            ),
            "tcode_in_roles": (
                "Submit an access request for the role that grants the required transaction.  "
                "Alternatively, if this is a custom role, add the tcode to the role menu in "
                "PFCG and regenerate the authorization profile.",
                "1-3 business days",
            ),
            "auth_objects": (
                "Open the covering role in PFCG > Authorizations tab.  Add the missing "
                "authorization object or extend the field values.  Save, regenerate the "
                "profile, and request the user to re-log.",
                "2-4 hours (including testing and transport)",
            ),
            "org_level_values": (
                "Extend the organizational field values in the covering role in PFCG.  "
                "If the role is org-level separated, assign the correct org-level variant "
                "of the role.",
                "2-4 hours",
            ),
            "role_validity": (
                "Submit a role assignment renewal request.  In SU01 > Roles tab, extend the "
                "'Valid To' date for the expired assignment after obtaining approval.",
                "1-2 business days",
            ),
            "transport_consistency": (
                "Create a transport request for the role in the source system via PFCG > "
                "Utilities > Create Transport Request.  Release and import via STMS.  Obtain "
                "CAB / change management approval for the import window.",
                "1-5 business days (depending on transport schedule)",
            ),
            "fiori_catalog": (
                "Assign the Fiori catalog role to the user.  In Launchpad Designer, verify "
                "the app is in the catalog, then assign the catalog role in SU01 > Roles tab.",
                "1-2 hours",
            ),
        }

        default_fix = (
            "Review the specific diagnostic step details and apply the recommended action.  "
            "Consult the SAP authorization trace (SU53) for live confirmation.",
            "2-8 hours",
        )

        return fix_map.get(blocking_step.check_name, default_fix)

    def _assess_risk_impact(
        self,
        recommended_fix: str,
        user_roles: List[_MockRole],
        tcode: str,
    ) -> List[str]:
        """
        Identify SoD or sensitive-access risks that would result from applying
        the recommended fix (i.e. assigning the transaction or role).
        """
        impacts: List[str] = []
        current_role_names = {r.role_name for r in user_roles}

        # Check known SoD conflicts if a new role would be added
        for role_a, role_b, description in _SOD_CONFLICTS:
            if role_a in current_role_names or role_b in current_role_names:
                impacts.append(
                    f"Potential SoD conflict: {description}"
                )

        # Flag sensitive transactions
        profile = self._transaction_kb.get(tcode)
        if profile and profile.sensitive:
            impacts.append(
                f"Transaction '{tcode}' is classified as sensitive "
                f"({profile.description}).  Assignment requires additional scrutiny and "
                "may require a mitigating control."
            )

        return impacts

    # ------------------------------------------------------------------
    # Utility helpers
    # ------------------------------------------------------------------

    def _is_fiori_app(self, transaction: str) -> bool:
        """Return True if the input looks like a Fiori app ID (e.g. F0718)."""
        cleaned = transaction.upper().strip()
        return cleaned in self._fiori_kb or (
            cleaned.startswith("F") and cleaned[1:].isdigit()
        )

    def _resolve_tcode(self, transaction: str) -> str:
        """Map a Fiori app ID to its backend tcode, or return the input unchanged."""
        fiori = self._fiori_kb.get(transaction.upper())
        if fiori:
            return fiori.backend_tcode
        return transaction.upper()


# ---------------------------------------------------------------------------
# Module-level convenience helpers
# ---------------------------------------------------------------------------

def get_transaction_list() -> List[Dict[str, Any]]:
    """Return a serializable list of all known transactions."""
    return [
        {
            "tcode": tp.tcode,
            "description": tp.description,
            "module": tp.module,
            "sensitive": tp.sensitive,
            "fiori_app_id": tp.fiori_app_id,
        }
        for tp in TRANSACTION_KB.values()
    ]


def get_transaction_requirements(tcode: str) -> Optional[Dict[str, Any]]:
    """Return full auth requirements for a tcode, or None if unknown."""
    profile = TRANSACTION_KB.get(tcode.upper())
    if not profile:
        return None
    return {
        "tcode": profile.tcode,
        "description": profile.description,
        "module": profile.module,
        "sensitive": profile.sensitive,
        "fiori_app_id": profile.fiori_app_id,
        "notes": profile.notes,
        "auth_requirements": [
            {
                "auth_object": r.auth_object,
                "field_name": r.field_name,
                "required_values": r.required_values,
                "description": r.description,
                "is_critical": r.is_critical,
            }
            for r in profile.auth_requirements
        ],
    }


def get_common_issues() -> List[Dict[str, Any]]:
    """Return the curated list of common SAP access issues."""
    return [
        {
            "issue_id": ci.issue_id,
            "title": ci.title,
            "frequency": ci.frequency,
            "symptom": ci.symptom,
            "root_cause": ci.root_cause,
            "fix": ci.fix,
            "prevention": ci.prevention,
            "affected_modules": ci.affected_modules,
        }
        for ci in COMMON_ISSUES
    ]


def get_diagnosis_history(
    limit: int = 50,
    user_filter: Optional[str] = None,
    transaction_filter: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Return recent diagnosis history, newest first.

    Parameters
    ----------
    limit:
        Maximum number of records to return.
    user_filter:
        If provided, return only results for this user_id.
    transaction_filter:
        If provided, return only results for this transaction.
    """
    results = list(reversed(_DIAGNOSIS_HISTORY))
    if user_filter:
        results = [r for r in results if r.request.user_id == user_filter.upper()]
    if transaction_filter:
        results = [r for r in results if r.request.transaction == transaction_filter.upper()]
    return [r.to_dict() for r in results[:limit]]
