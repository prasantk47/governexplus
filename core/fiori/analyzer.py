"""
Fiori Security Analyzer

Traces the full SAP Fiori authorization chain from launchpad to backend,
diagnosing access failures at each layer:

    Launchpad -> Business Role -> Catalog -> Space/Page -> Tile
    -> Target Mapping -> OData Service -> Gateway Auth -> Backend Auth

Primary use cases:
- Trace why a user cannot launch a Fiori application
- Audit what authorization objects a Fiori app requires
- Diagnose the classic "tile visible but launch fails" error pattern
- Catalog and service inventory for security review
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum
from datetime import datetime
import logging

from db.models.intelligence import FioriAppRecord
from db.database import db_manager

logger = logging.getLogger(__name__)


# ===========================================================================
# Enumerations
# ===========================================================================

class LayerStatus(Enum):
    """Pass/fail status at a single authorization chain layer."""
    PASS = "pass"
    FAIL = "fail"
    WARN = "warn"
    SKIPPED = "skipped"


class ErrorPattern(Enum):
    """Common Fiori authorization failure patterns."""
    MISSING_S_SERVICE = "missing_s_service"
    MISSING_CATALOG = "missing_catalog"
    MISSING_TARGET_MAPPING = "missing_target_mapping"
    MISSING_BUSINESS_ROLE = "missing_business_role"
    MISSING_ODATA_SCOPE = "missing_odata_scope"
    MISSING_BACKEND_OBJECT = "missing_backend_object"
    GATEWAY_NOT_ACTIVATED = "gateway_not_activated"
    ICF_NODE_INACTIVE = "icf_node_inactive"
    SCOPE_MISMATCH = "scope_mismatch"
    NO_ERROR = "no_error"


class RiskLevel(Enum):
    """Security risk level for a Fiori app or catalog."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


# ===========================================================================
# Data classes — chain layers
# ===========================================================================

@dataclass
class ChainLayer:
    """Single layer in the Fiori authorization chain."""
    layer_name: str
    status: LayerStatus
    object_id: str
    object_name: str
    details: str
    required_auth: List[str] = field(default_factory=list)
    missing_auth: List[str] = field(default_factory=list)
    remediation: Optional[str] = None


@dataclass
class FioriApp:
    """Fiori application descriptor."""
    app_id: str
    name: str
    description: str
    catalog_id: str
    catalog_name: str
    space_id: str
    page_id: str
    odata_services: List[str]
    backend_transactions: List[str]
    required_auth_objects: List[Dict[str, Any]]   # [{"object": "M_BEST_BSA", "field": "BSART", "value": "*"}]
    target_mapping_id: str
    semantic_object: str
    semantic_action: str
    risk_level: RiskLevel
    business_area: str
    tags: List[str] = field(default_factory=list)


@dataclass
class FioriAccessTrace:
    """Full authorization chain trace for one user attempting to access one app."""
    app_id: str
    user_id: str
    timestamp: str
    overall_status: LayerStatus
    error_pattern: ErrorPattern
    chain: List[ChainLayer]
    summary: str
    remediation_steps: List[str]


@dataclass
class AppRequirements:
    """All authorization requirements for a Fiori application."""
    app_id: str
    app_name: str
    odata_services: List[str]
    backend_transactions: List[str]
    auth_objects: List[Dict[str, Any]]
    s_service_entries: List[Dict[str, str]]   # ICF service node entries
    catalog_id: str
    target_mapping_id: str
    gateway_alias: str
    risk_level: RiskLevel
    notes: List[str]


@dataclass
class TileDiagnosis:
    """
    Diagnosis for the 'tile visible but app fails' pattern.

    The tile is visible because the user has the catalog assigned via
    business role, but launch fails because gateway or backend auth is missing.
    """
    app_id: str
    user_id: str
    tile_visible: bool
    launch_fails: bool
    root_cause: str
    error_pattern: ErrorPattern
    failing_layer: str
    missing_objects: List[str]
    remediation_steps: List[str]
    estimated_effort: str   # "15 minutes", "1 hour", etc.


@dataclass
class CatalogAnalysis:
    """Analysis of a Fiori catalog — what apps, services, and auth it requires."""
    catalog_id: str
    catalog_name: str
    catalog_type: str   # "target", "reference", "mixed"
    app_count: int
    apps: List[Dict[str, str]]
    odata_services: List[str]
    required_auth_objects: List[str]
    risk_level: RiskLevel
    assigned_business_roles: List[str]
    notes: str


# ===========================================================================
# Knowledge base — Fiori app seed data (30+ apps)
# ===========================================================================
# Used ONLY to seed the DB on first run. At runtime _FIORI_APPS and
# _APP_INDEX are populated from the database via _ensure_loaded().

_FIORI_APPS_SEED: List[FioriApp] = [
    FioriApp(
        app_id="F0842A",
        name="Manage Purchase Orders",
        description="Create, change, and monitor purchase orders in SAP S/4HANA.",
        catalog_id="SAP_MM_BC_PO_MANAGE",
        catalog_name="Manage Purchase Orders",
        space_id="SAP_MM_PURCHASING",
        page_id="SAP_MM_PURCHASING_PAGE",
        odata_services=["MM_PUR_PO_MAINT_V2_SRV", "API_PURCHASEORDER_PROCESS_SRV"],
        backend_transactions=["ME21N", "ME22N", "ME23N"],
        required_auth_objects=[
            {"object": "M_BEST_BSA", "field": "BSART", "value": "*"},
            {"object": "M_BEST_EKG", "field": "EKGRP", "value": "*"},
            {"object": "M_BEST_EKO", "field": "EKORG", "value": "*"},
            {"object": "M_BEST_WRK", "field": "WERKS", "value": "*"},
            {"object": "S_SERVICE",  "field": "SRV_NAME", "value": "MM_PUR_PO_MAINT_V2_SRV"},
        ],
        target_mapping_id="MM_PUR-manage",
        semantic_object="PurchaseOrder",
        semantic_action="manage",
        risk_level=RiskLevel.HIGH,
        business_area="Materials Management",
        tags=["procurement", "purchasing", "po"],
    ),
    FioriApp(
        app_id="F0859",
        name="Post General Journal Entries",
        description="Enter and post general ledger journal entries.",
        catalog_id="SAP_FIN_BC_GL_POSTING",
        catalog_name="General Ledger Posting",
        space_id="SAP_FIN_ACCOUNTING",
        page_id="SAP_FIN_ACCOUNTING_PAGE",
        odata_services=["FIN_GL_ITEMS_SRV", "API_JOURNALENTRYITEMBASIC_SRV"],
        backend_transactions=["FB50", "F-02", "FB01"],
        required_auth_objects=[
            {"object": "F_BKPF_BUK", "field": "BUKRS", "value": "*"},
            {"object": "F_BKPF_KOA", "field": "KOART", "value": "S"},
            {"object": "F_BKPF_GSB", "field": "GSBER", "value": "*"},
            {"object": "S_SERVICE",  "field": "SRV_NAME", "value": "FIN_GL_ITEMS_SRV"},
        ],
        target_mapping_id="GLAccount-postGeneralJournalEntries",
        semantic_object="GLAccount",
        semantic_action="postGeneralJournalEntries",
        risk_level=RiskLevel.CRITICAL,
        business_area="Finance",
        tags=["finance", "gl", "journal", "posting"],
    ),
    FioriApp(
        app_id="F2229",
        name="Manage Business Partners",
        description="Create and maintain business partner master data.",
        catalog_id="SAP_SD_BC_BP_MANAGE",
        catalog_name="Business Partner Management",
        space_id="SAP_MASTER_DATA",
        page_id="SAP_MASTER_DATA_PAGE",
        odata_services=["API_BUSINESS_PARTNER", "MDG_BS_BP_MANAGE_SRV"],
        backend_transactions=["BP", "XD01", "XK01"],
        required_auth_objects=[
            {"object": "B_BUPA_BZT", "field": "BZTYP", "value": "*"},
            {"object": "B_BUPA_GRP", "field": "BUP_ITYPE", "value": "*"},
            {"object": "B_BUPA_RLT", "field": "BUR001", "value": "*"},
            {"object": "S_SERVICE",  "field": "SRV_NAME", "value": "API_BUSINESS_PARTNER"},
        ],
        target_mapping_id="BusinessPartner-manage",
        semantic_object="BusinessPartner",
        semantic_action="manage",
        risk_level=RiskLevel.HIGH,
        business_area="Master Data",
        tags=["master data", "business partner", "customer", "vendor"],
    ),
    FioriApp(
        app_id="F1603",
        name="My Inbox",
        description="Unified inbox for workflow tasks, approvals, and notifications.",
        catalog_id="SAP_BASIS_BC_WF_INBOX",
        catalog_name="My Inbox",
        space_id="SAP_COMMON",
        page_id="SAP_COMMON_PAGE",
        odata_services=["TASKPROCESSING", "IWPGW_TASKPROCESSING_SRV"],
        backend_transactions=["SWIA", "SBWP"],
        required_auth_objects=[
            {"object": "S_SERVICE", "field": "SRV_NAME", "value": "TASKPROCESSING"},
            {"object": "S_RFC",     "field": "RFC_NAME",  "value": "SWIA*"},
        ],
        target_mapping_id="WorkflowTask-displayInbox",
        semantic_object="WorkflowTask",
        semantic_action="displayInbox",
        risk_level=RiskLevel.LOW,
        business_area="Workflow",
        tags=["workflow", "inbox", "approvals", "tasks"],
    ),
    FioriApp(
        app_id="F3702",
        name="Manage Sales Orders",
        description="Create, change, and monitor sales orders in S/4HANA.",
        catalog_id="SAP_SD_BC_SO_MANAGE",
        catalog_name="Manage Sales Orders",
        space_id="SAP_SD_SALES",
        page_id="SAP_SD_SALES_PAGE",
        odata_services=["SD_SALES_ORDER_MANAGE_V2", "API_SALES_ORDER_SRV"],
        backend_transactions=["VA01", "VA02", "VA03"],
        required_auth_objects=[
            {"object": "V_VBAK_AAT", "field": "AUART", "value": "*"},
            {"object": "V_VBAK_VKO", "field": "VKORG", "value": "*"},
            {"object": "V_VBAK_VTW", "field": "VTWEG", "value": "*"},
            {"object": "S_SERVICE",  "field": "SRV_NAME", "value": "SD_SALES_ORDER_MANAGE_V2"},
        ],
        target_mapping_id="SalesOrder-manage",
        semantic_object="SalesOrder",
        semantic_action="manage",
        risk_level=RiskLevel.HIGH,
        business_area="Sales",
        tags=["sales", "order", "sd"],
    ),
    FioriApp(
        app_id="F1861",
        name="Post Outgoing Payments",
        description="Process and post outgoing payments to vendors.",
        catalog_id="SAP_FIN_BC_AP_PAYMENT",
        catalog_name="Accounts Payable Payments",
        space_id="SAP_FIN_ACCOUNTING",
        page_id="SAP_FIN_ACCOUNTING_PAGE",
        odata_services=["FIN_AP_ITEMS_SRV", "FCLM_BAM_PAYMENT_SRV"],
        backend_transactions=["F110", "F-53", "F-58"],
        required_auth_objects=[
            {"object": "F_BKPF_BUK", "field": "BUKRS", "value": "*"},
            {"object": "F_BKPF_KOA", "field": "KOART", "value": "K"},
            {"object": "P_TRVFD",    "field": "REINR",  "value": "*"},
            {"object": "S_SERVICE",  "field": "SRV_NAME", "value": "FIN_AP_ITEMS_SRV"},
        ],
        target_mapping_id="AccountingDocument-postOutgoingPayment",
        semantic_object="AccountingDocument",
        semantic_action="postOutgoingPayment",
        risk_level=RiskLevel.CRITICAL,
        business_area="Finance",
        tags=["finance", "ap", "payment", "vendor"],
    ),
    FioriApp(
        app_id="F2358",
        name="Create Supplier Invoice",
        description="Enter and post incoming invoices from suppliers.",
        catalog_id="SAP_FIN_BC_AP_INVOICE",
        catalog_name="Accounts Payable Invoice Entry",
        space_id="SAP_FIN_ACCOUNTING",
        page_id="SAP_FIN_ACCOUNTING_PAGE",
        odata_services=["FIN_AP_INV_ENTRY_SRV", "API_SUPPLIERINVOICE_PROCESS_SRV"],
        backend_transactions=["MIRO", "FB60", "MIR7"],
        required_auth_objects=[
            {"object": "F_BKPF_BUK", "field": "BUKRS", "value": "*"},
            {"object": "M_RECH_BUK", "field": "BUKRS", "value": "*"},
            {"object": "M_RECH_WRK", "field": "WERKS", "value": "*"},
            {"object": "S_SERVICE",  "field": "SRV_NAME", "value": "FIN_AP_INV_ENTRY_SRV"},
        ],
        target_mapping_id="SupplierInvoice-create",
        semantic_object="SupplierInvoice",
        semantic_action="create",
        risk_level=RiskLevel.CRITICAL,
        business_area="Finance",
        tags=["finance", "ap", "invoice", "miro"],
    ),
    FioriApp(
        app_id="F0797",
        name="Manage Cost Centers",
        description="Create and maintain cost center master data.",
        catalog_id="SAP_FIN_BC_CO_COSTCENTER",
        catalog_name="Cost Center Management",
        space_id="SAP_FIN_CONTROLLING",
        page_id="SAP_FIN_CONTROLLING_PAGE",
        odata_services=["API_COSTCENTER_SRV", "CO_OM_CCA_CCTR_MAINT_SRV"],
        backend_transactions=["KS01", "KS02", "KS03"],
        required_auth_objects=[
            {"object": "K_CSKS",    "field": "KOSTL",  "value": "*"},
            {"object": "K_CSKS_SET","field": "KOSTL",  "value": "*"},
            {"object": "S_SERVICE", "field": "SRV_NAME", "value": "API_COSTCENTER_SRV"},
        ],
        target_mapping_id="CostCenter-manage",
        semantic_object="CostCenter",
        semantic_action="manage",
        risk_level=RiskLevel.MEDIUM,
        business_area="Controlling",
        tags=["controlling", "co", "cost center", "master data"],
    ),
    FioriApp(
        app_id="F4218",
        name="Manage Material Documents",
        description="Display and reverse goods movement material documents.",
        catalog_id="SAP_MM_BC_MATDOC_MANAGE",
        catalog_name="Material Document Management",
        space_id="SAP_MM_INVENTORY",
        page_id="SAP_MM_INVENTORY_PAGE",
        odata_services=["MATERIAL_DOCUMENT_SRV", "API_MATERIAL_DOCUMENT_SRV"],
        backend_transactions=["MIGO", "MB03", "MBST"],
        required_auth_objects=[
            {"object": "M_MSEG_BWA", "field": "BWART", "value": "*"},
            {"object": "M_MSEG_WMB", "field": "WERKS", "value": "*"},
            {"object": "M_MSEG_LGO", "field": "LGORT", "value": "*"},
            {"object": "S_SERVICE",  "field": "SRV_NAME", "value": "MATERIAL_DOCUMENT_SRV"},
        ],
        target_mapping_id="MaterialDocument-manage",
        semantic_object="MaterialDocument",
        semantic_action="manage",
        risk_level=RiskLevel.MEDIUM,
        business_area="Materials Management",
        tags=["mm", "inventory", "goods movement", "migo"],
    ),
    FioriApp(
        app_id="F2906",
        name="Manage Profit Centers",
        description="Create and maintain profit center master data in CO-PCA.",
        catalog_id="SAP_FIN_BC_CO_PROFITCENTER",
        catalog_name="Profit Center Management",
        space_id="SAP_FIN_CONTROLLING",
        page_id="SAP_FIN_CONTROLLING_PAGE",
        odata_services=["API_PROFITCENTER_SRV", "CO_PCA_PRCTR_MAINT_SRV"],
        backend_transactions=["KE51", "KE52", "KE53"],
        required_auth_objects=[
            {"object": "K_PCA",     "field": "PRCTR",  "value": "*"},
            {"object": "S_SERVICE", "field": "SRV_NAME", "value": "API_PROFITCENTER_SRV"},
        ],
        target_mapping_id="ProfitCenter-manage",
        semantic_object="ProfitCenter",
        semantic_action="manage",
        risk_level=RiskLevel.MEDIUM,
        business_area="Controlling",
        tags=["controlling", "profit center", "co-pca"],
    ),
    FioriApp(
        app_id="F1350",
        name="Manage Work Orders",
        description="Plan and release plant maintenance work orders.",
        catalog_id="SAP_PM_BC_WO_MANAGE",
        catalog_name="Plant Maintenance Work Orders",
        space_id="SAP_PM_MAINTENANCE",
        page_id="SAP_PM_MAINTENANCE_PAGE",
        odata_services=["PM_WORKORDER_MAINT_SRV", "API_MAINTENANCEORDER_SRV"],
        backend_transactions=["IW31", "IW32", "IW33"],
        required_auth_objects=[
            {"object": "I_AUFK_IWO", "field": "AUART", "value": "*"},
            {"object": "I_AUFK_WRK", "field": "WERKS", "value": "*"},
            {"object": "S_SERVICE",  "field": "SRV_NAME", "value": "PM_WORKORDER_MAINT_SRV"},
        ],
        target_mapping_id="MaintenanceOrder-manage",
        semantic_object="MaintenanceOrder",
        semantic_action="manage",
        risk_level=RiskLevel.MEDIUM,
        business_area="Plant Maintenance",
        tags=["pm", "maintenance", "work order"],
    ),
    FioriApp(
        app_id="F3600",
        name="Manage Supplier Master",
        description="Create, change, and display supplier master records.",
        catalog_id="SAP_MM_BC_VENDOR_MANAGE",
        catalog_name="Vendor/Supplier Master Management",
        space_id="SAP_MASTER_DATA",
        page_id="SAP_MASTER_DATA_PAGE",
        odata_services=["API_BUSINESS_PARTNER", "MDG_BS_VD_MANAGE_SRV"],
        backend_transactions=["XK01", "XK02", "MK01"],
        required_auth_objects=[
            {"object": "M_LFA1_EKO", "field": "EKORG", "value": "*"},
            {"object": "M_LFA1_GEN", "field": "ACTVT", "value": "*"},
            {"object": "B_BUPA_RLT", "field": "BUR001", "value": "MKK"},
            {"object": "S_SERVICE",  "field": "SRV_NAME", "value": "API_BUSINESS_PARTNER"},
        ],
        target_mapping_id="Supplier-manage",
        semantic_object="Supplier",
        semantic_action="manage",
        risk_level=RiskLevel.HIGH,
        business_area="Master Data",
        tags=["master data", "vendor", "supplier", "mm"],
    ),
    FioriApp(
        app_id="F2340",
        name="Manage Customer Master",
        description="Create, change, and display customer master records.",
        catalog_id="SAP_SD_BC_CUSTOMER_MANAGE",
        catalog_name="Customer Master Management",
        space_id="SAP_MASTER_DATA",
        page_id="SAP_MASTER_DATA_PAGE",
        odata_services=["API_BUSINESS_PARTNER", "MDG_BS_CD_MANAGE_SRV"],
        backend_transactions=["XD01", "XD02", "FD01"],
        required_auth_objects=[
            {"object": "F_KNA1_BED", "field": "VKORG", "value": "*"},
            {"object": "F_KNA1_GEN", "field": "ACTVT", "value": "*"},
            {"object": "B_BUPA_RLT", "field": "BUR001", "value": "CRM000"},
            {"object": "S_SERVICE",  "field": "SRV_NAME", "value": "API_BUSINESS_PARTNER"},
        ],
        target_mapping_id="Customer-manage",
        semantic_object="Customer",
        semantic_action="manage",
        risk_level=RiskLevel.HIGH,
        business_area="Master Data",
        tags=["master data", "customer", "sd", "crm"],
    ),
    FioriApp(
        app_id="F2176",
        name="Manage Bank Accounts",
        description="Manage house bank accounts and payment methods.",
        catalog_id="SAP_FIN_BC_BANK_MANAGE",
        catalog_name="Bank Account Management",
        space_id="SAP_FIN_TREASURY",
        page_id="SAP_FIN_TREASURY_PAGE",
        odata_services=["FCLM_BAM_BANK_ACCOUNT_SRV", "API_BANKDETAIL_SRV"],
        backend_transactions=["FI12", "F110", "FBZP"],
        required_auth_objects=[
            {"object": "F_BNKA_BUK", "field": "BUKRS", "value": "*"},
            {"object": "F_BNKA_MAN", "field": "ACTVT", "value": "*"},
            {"object": "S_SERVICE",  "field": "SRV_NAME", "value": "FCLM_BAM_BANK_ACCOUNT_SRV"},
        ],
        target_mapping_id="BankAccount-manage",
        semantic_object="BankAccount",
        semantic_action="manage",
        risk_level=RiskLevel.CRITICAL,
        business_area="Finance",
        tags=["finance", "treasury", "bank", "payment"],
    ),
    FioriApp(
        app_id="F1366",
        name="Approve Purchase Orders",
        description="Multi-level approval workflow for purchase orders.",
        catalog_id="SAP_MM_BC_PO_APPROVE",
        catalog_name="Purchase Order Approval",
        space_id="SAP_MM_PURCHASING",
        page_id="SAP_MM_PURCHASING_PAGE",
        odata_services=["MM_PUR_PO_APPROVAL_SRV", "TASKPROCESSING"],
        backend_transactions=["ME28", "ME29N"],
        required_auth_objects=[
            {"object": "M_BEST_BSA", "field": "BSART", "value": "*"},
            {"object": "M_BEST_EKG", "field": "EKGRP", "value": "*"},
            {"object": "S_SERVICE",  "field": "SRV_NAME", "value": "MM_PUR_PO_APPROVAL_SRV"},
        ],
        target_mapping_id="PurchaseOrder-approve",
        semantic_object="PurchaseOrder",
        semantic_action="approve",
        risk_level=RiskLevel.HIGH,
        business_area="Materials Management",
        tags=["procurement", "approval", "workflow"],
    ),
    FioriApp(
        app_id="F3012",
        name="Manage Stock Transfers",
        description="Create and monitor stock transfer orders between plants.",
        catalog_id="SAP_MM_BC_STO_MANAGE",
        catalog_name="Stock Transfer Order Management",
        space_id="SAP_MM_INVENTORY",
        page_id="SAP_MM_INVENTORY_PAGE",
        odata_services=["MM_PUR_STO_MAINT_SRV", "API_STOCK_TRANSFER_SRV"],
        backend_transactions=["ME27", "MB1B", "MIGO"],
        required_auth_objects=[
            {"object": "M_BEST_BSA", "field": "BSART", "value": "UB"},
            {"object": "M_MSEG_BWA", "field": "BWART", "value": "641"},
            {"object": "S_SERVICE",  "field": "SRV_NAME", "value": "MM_PUR_STO_MAINT_SRV"},
        ],
        target_mapping_id="StockTransferOrder-manage",
        semantic_object="StockTransferOrder",
        semantic_action="manage",
        risk_level=RiskLevel.MEDIUM,
        business_area="Materials Management",
        tags=["mm", "stock", "transfer", "inventory"],
    ),
    FioriApp(
        app_id="F0150",
        name="User Settings",
        description="Manage personal user settings and preferences.",
        catalog_id="SAP_BASIS_BC_USER_SETTINGS",
        catalog_name="User Settings",
        space_id="SAP_COMMON",
        page_id="SAP_COMMON_PAGE",
        odata_services=["USER_SETTINGS_SRV"],
        backend_transactions=["SU3"],
        required_auth_objects=[
            {"object": "S_SERVICE", "field": "SRV_NAME", "value": "USER_SETTINGS_SRV"},
            {"object": "S_USER_GRP","field": "CLASS",    "value": "*"},
        ],
        target_mapping_id="Shell-userSettings",
        semantic_object="Shell",
        semantic_action="userSettings",
        risk_level=RiskLevel.LOW,
        business_area="Basis",
        tags=["settings", "user", "preferences"],
    ),
    FioriApp(
        app_id="F1691",
        name="Display Financial Statements",
        description="View balance sheet, P&L, and trial balance reports.",
        catalog_id="SAP_FIN_BC_GL_REPORTING",
        catalog_name="Financial Statement Reporting",
        space_id="SAP_FIN_ACCOUNTING",
        page_id="SAP_FIN_ACCOUNTING_PAGE",
        odata_services=["FIN_GL_REPORTING_SRV", "API_GLACCOUNT_SRV"],
        backend_transactions=["F.01", "S_ALR_87012284", "FAGLB03"],
        required_auth_objects=[
            {"object": "F_BKPF_BUK", "field": "BUKRS", "value": "*"},
            {"object": "F_BKPF_KOA", "field": "KOART", "value": "S"},
            {"object": "S_SERVICE",  "field": "SRV_NAME", "value": "FIN_GL_REPORTING_SRV"},
        ],
        target_mapping_id="FinancialStatement-display",
        semantic_object="FinancialStatement",
        semantic_action="display",
        risk_level=RiskLevel.HIGH,
        business_area="Finance",
        tags=["finance", "reporting", "gl", "balance sheet"],
    ),
    FioriApp(
        app_id="F4720",
        name="Manage Production Orders",
        description="Create, release, and confirm production orders in PP.",
        catalog_id="SAP_PP_BC_PRDORD_MANAGE",
        catalog_name="Production Order Management",
        space_id="SAP_PP_PRODUCTION",
        page_id="SAP_PP_PRODUCTION_PAGE",
        odata_services=["PP_PROD_ORDER_SRV", "API_PRODUCTION_ORDER_SRV"],
        backend_transactions=["CO01", "CO02", "CO11N"],
        required_auth_objects=[
            {"object": "C_AFKO_AWK", "field": "WERKS", "value": "*"},
            {"object": "C_AFKO_AUF", "field": "AUART", "value": "*"},
            {"object": "S_SERVICE",  "field": "SRV_NAME", "value": "PP_PROD_ORDER_SRV"},
        ],
        target_mapping_id="ProductionOrder-manage",
        semantic_object="ProductionOrder",
        semantic_action="manage",
        risk_level=RiskLevel.MEDIUM,
        business_area="Production Planning",
        tags=["pp", "production", "manufacturing", "order"],
    ),
    FioriApp(
        app_id="F3560",
        name="Run Payroll",
        description="Execute payroll runs for selected payroll areas.",
        catalog_id="SAP_HR_BC_PAYROLL_RUN",
        catalog_name="Payroll Processing",
        space_id="SAP_HR_PAYROLL",
        page_id="SAP_HR_PAYROLL_PAGE",
        odata_services=["HR_PAYROLL_RUN_SRV", "API_PAYROLL_PROCESS_SRV"],
        backend_transactions=["PC00_M99_CALC", "PU01", "PC00_M99_CLJN"],
        required_auth_objects=[
            {"object": "P_PYEVRUN",  "field": "PERNR",  "value": "*"},
            {"object": "P_ORGIN",    "field": "PERSA",  "value": "*"},
            {"object": "P_ABAP",     "field": "REPID",  "value": "RPCALC*"},
            {"object": "S_SERVICE",  "field": "SRV_NAME", "value": "HR_PAYROLL_RUN_SRV"},
        ],
        target_mapping_id="Payroll-run",
        semantic_object="Payroll",
        semantic_action="run",
        risk_level=RiskLevel.CRITICAL,
        business_area="Human Resources",
        tags=["hr", "payroll", "sensitive"],
    ),
    FioriApp(
        app_id="F1924",
        name="Manage Employee Data",
        description="Maintain personnel master data for employees.",
        catalog_id="SAP_HR_BC_PA_MANAGE",
        catalog_name="Personnel Administration",
        space_id="SAP_HR_PERSONNEL",
        page_id="SAP_HR_PERSONNEL_PAGE",
        odata_services=["HR_PA_EMPLOYEE_SRV", "API_EMPLOYEE_SRV"],
        backend_transactions=["PA30", "PA20", "PA40"],
        required_auth_objects=[
            {"object": "P_ORGIN",    "field": "PERSA",  "value": "*"},
            {"object": "P_ORGIN",    "field": "INFTY",  "value": "*"},
            {"object": "P_PERNR",    "field": "PSIGN",  "value": "I"},
            {"object": "S_SERVICE",  "field": "SRV_NAME", "value": "HR_PA_EMPLOYEE_SRV"},
        ],
        target_mapping_id="Employee-manage",
        semantic_object="Employee",
        semantic_action="manage",
        risk_level=RiskLevel.HIGH,
        business_area="Human Resources",
        tags=["hr", "employee", "pa", "personnel"],
    ),
    FioriApp(
        app_id="F0870",
        name="Manage Contracts",
        description="Create and maintain purchasing contracts and scheduling agreements.",
        catalog_id="SAP_MM_BC_CONTRACT_MANAGE",
        catalog_name="Contract Management",
        space_id="SAP_MM_PURCHASING",
        page_id="SAP_MM_PURCHASING_PAGE",
        odata_services=["MM_PUR_CONTRACT_MAINT_SRV", "API_PURCHASECONTRACT_SRV"],
        backend_transactions=["ME31K", "ME32K", "ME33K"],
        required_auth_objects=[
            {"object": "M_BEST_BSA", "field": "BSART", "value": "MK"},
            {"object": "M_BEST_EKO", "field": "EKORG", "value": "*"},
            {"object": "S_SERVICE",  "field": "SRV_NAME", "value": "MM_PUR_CONTRACT_MAINT_SRV"},
        ],
        target_mapping_id="PurchaseContract-manage",
        semantic_object="PurchaseContract",
        semantic_action="manage",
        risk_level=RiskLevel.HIGH,
        business_area="Materials Management",
        tags=["procurement", "contract", "scheduling agreement"],
    ),
    FioriApp(
        app_id="F2483",
        name="Monitor Payments",
        description="Monitor and track outgoing and incoming payment runs.",
        catalog_id="SAP_FIN_BC_PAYMENT_MONITOR",
        catalog_name="Payment Monitoring",
        space_id="SAP_FIN_TREASURY",
        page_id="SAP_FIN_TREASURY_PAGE",
        odata_services=["FCLM_BAM_PAYMENT_MONITOR_SRV"],
        backend_transactions=["FBL1N", "FBL3N", "F110"],
        required_auth_objects=[
            {"object": "F_BKPF_BUK", "field": "BUKRS", "value": "*"},
            {"object": "S_SERVICE",  "field": "SRV_NAME", "value": "FCLM_BAM_PAYMENT_MONITOR_SRV"},
        ],
        target_mapping_id="Payment-monitor",
        semantic_object="Payment",
        semantic_action="monitor",
        risk_level=RiskLevel.HIGH,
        business_area="Finance",
        tags=["finance", "payment", "monitoring", "treasury"],
    ),
    FioriApp(
        app_id="F1234",
        name="Manage Fixed Assets",
        description="Asset master data maintenance and transaction posting.",
        catalog_id="SAP_FIN_BC_AA_MANAGE",
        catalog_name="Asset Accounting",
        space_id="SAP_FIN_ACCOUNTING",
        page_id="SAP_FIN_ACCOUNTING_PAGE",
        odata_services=["FIN_AA_ASSET_SRV", "API_FIXEDASSET_SRV"],
        backend_transactions=["AS01", "AS02", "ABUMN"],
        required_auth_objects=[
            {"object": "A_T001A",   "field": "BUKRS",  "value": "*"},
            {"object": "A_T001A",   "field": "ANLKL",  "value": "*"},
            {"object": "S_SERVICE", "field": "SRV_NAME", "value": "FIN_AA_ASSET_SRV"},
        ],
        target_mapping_id="FixedAsset-manage",
        semantic_object="FixedAsset",
        semantic_action="manage",
        risk_level=RiskLevel.HIGH,
        business_area="Finance",
        tags=["finance", "asset", "fixed assets", "aa"],
    ),
    FioriApp(
        app_id="F5502",
        name="Manage G/L Account Master",
        description="Create and change general ledger account master records.",
        catalog_id="SAP_FIN_BC_GL_ACCOUNT",
        catalog_name="G/L Account Master Data",
        space_id="SAP_FIN_ACCOUNTING",
        page_id="SAP_FIN_ACCOUNTING_PAGE",
        odata_services=["API_GLACCOUNT_SRV", "FIN_GL_ACCOUNT_MAINT_SRV"],
        backend_transactions=["FS00", "FSP0", "FSS0"],
        required_auth_objects=[
            {"object": "F_SKA1_BUK", "field": "BUKRS", "value": "*"},
            {"object": "F_SKA1_KTP", "field": "KTOPL", "value": "*"},
            {"object": "S_SERVICE",  "field": "SRV_NAME", "value": "API_GLACCOUNT_SRV"},
        ],
        target_mapping_id="GLAccount-manage",
        semantic_object="GLAccount",
        semantic_action="manage",
        risk_level=RiskLevel.HIGH,
        business_area="Finance",
        tags=["finance", "gl", "chart of accounts", "master data"],
    ),
    FioriApp(
        app_id="F3789",
        name="Process Incoming Payments",
        description="Post and clear incoming payments from customers.",
        catalog_id="SAP_FIN_BC_AR_PAYMENT",
        catalog_name="Accounts Receivable Payments",
        space_id="SAP_FIN_ACCOUNTING",
        page_id="SAP_FIN_ACCOUNTING_PAGE",
        odata_services=["FIN_AR_ITEMS_SRV", "API_CUSTOMER_PAYMENT_SRV"],
        backend_transactions=["F-28", "F-32", "FB75"],
        required_auth_objects=[
            {"object": "F_BKPF_BUK", "field": "BUKRS", "value": "*"},
            {"object": "F_BKPF_KOA", "field": "KOART", "value": "D"},
            {"object": "S_SERVICE",  "field": "SRV_NAME", "value": "FIN_AR_ITEMS_SRV"},
        ],
        target_mapping_id="CustomerPayment-process",
        semantic_object="CustomerPayment",
        semantic_action="process",
        risk_level=RiskLevel.HIGH,
        business_area="Finance",
        tags=["finance", "ar", "payment", "customer"],
    ),
    FioriApp(
        app_id="F2671",
        name="Manage Requisitions",
        description="Create and submit purchase requisitions.",
        catalog_id="SAP_MM_BC_PR_MANAGE",
        catalog_name="Purchase Requisition Management",
        space_id="SAP_MM_PURCHASING",
        page_id="SAP_MM_PURCHASING_PAGE",
        odata_services=["MM_PUR_PR_MAINT_SRV", "API_PURCHASEREQ_PROCESS_SRV"],
        backend_transactions=["ME51N", "ME52N", "ME53N"],
        required_auth_objects=[
            {"object": "M_BANF_BSA", "field": "BSART", "value": "*"},
            {"object": "M_BANF_EKG", "field": "EKGRP", "value": "*"},
            {"object": "S_SERVICE",  "field": "SRV_NAME", "value": "MM_PUR_PR_MAINT_SRV"},
        ],
        target_mapping_id="PurchaseRequisition-manage",
        semantic_object="PurchaseRequisition",
        semantic_action="manage",
        risk_level=RiskLevel.MEDIUM,
        business_area="Materials Management",
        tags=["procurement", "requisition", "pr", "mm"],
    ),
    FioriApp(
        app_id="F4109",
        name="Manage Tax Codes",
        description="Configure and maintain tax codes and tax rates.",
        catalog_id="SAP_FIN_BC_TAX_MANAGE",
        catalog_name="Tax Configuration",
        space_id="SAP_FIN_ACCOUNTING",
        page_id="SAP_FIN_ACCOUNTING_PAGE",
        odata_services=["API_TAXCODEMASTER_SRV", "FIN_TAX_CONFIG_SRV"],
        backend_transactions=["FTXP", "FT01"],
        required_auth_objects=[
            {"object": "S_TABU_DIS", "field": "ACTVT", "value": "02"},
            {"object": "S_TABU_DIS", "field": "DICBERCLS", "value": "FB"},
            {"object": "S_SERVICE",  "field": "SRV_NAME", "value": "API_TAXCODEMASTER_SRV"},
        ],
        target_mapping_id="TaxCode-manage",
        semantic_object="TaxCode",
        semantic_action="manage",
        risk_level=RiskLevel.CRITICAL,
        business_area="Finance",
        tags=["finance", "tax", "configuration"],
    ),
    FioriApp(
        app_id="F0998",
        name="Manage Users",
        description="Create, change, and lock/unlock SAP user accounts.",
        catalog_id="SAP_BASIS_BC_USER_MANAGE",
        catalog_name="User Administration",
        space_id="SAP_BASIS_ADMIN",
        page_id="SAP_BASIS_ADMIN_PAGE",
        odata_services=["USER_MANAGEMENT_SRV", "API_USERACCOUNTS_SRV"],
        backend_transactions=["SU01", "SU10", "SU01D"],
        required_auth_objects=[
            {"object": "S_USER_GRP", "field": "CLASS",  "value": "*"},
            {"object": "S_USER_GRP", "field": "ACTVT",  "value": "*"},
            {"object": "S_USER_PRO", "field": "ACTVT",  "value": "*"},
            {"object": "S_SERVICE",  "field": "SRV_NAME", "value": "USER_MANAGEMENT_SRV"},
        ],
        target_mapping_id="User-manage",
        semantic_object="User",
        semantic_action="manage",
        risk_level=RiskLevel.CRITICAL,
        business_area="Basis",
        tags=["basis", "user admin", "security", "critical"],
    ),
    FioriApp(
        app_id="F3301",
        name="Manage Roles",
        description="Create and maintain authorization roles and profiles.",
        catalog_id="SAP_BASIS_BC_ROLE_MANAGE",
        catalog_name="Role Administration",
        space_id="SAP_BASIS_ADMIN",
        page_id="SAP_BASIS_ADMIN_PAGE",
        odata_services=["ROLE_MANAGEMENT_SRV"],
        backend_transactions=["PFCG", "SU25", "SU24"],
        required_auth_objects=[
            {"object": "S_USER_AGR", "field": "ACTVT",  "value": "*"},
            {"object": "S_USER_AGR", "field": "ACT_GROUP", "value": "*"},
            {"object": "S_SERVICE",  "field": "SRV_NAME", "value": "ROLE_MANAGEMENT_SRV"},
        ],
        target_mapping_id="Role-manage",
        semantic_object="Role",
        semantic_action="manage",
        risk_level=RiskLevel.CRITICAL,
        business_area="Basis",
        tags=["basis", "roles", "authorization", "pfcg"],
    ),
    FioriApp(
        app_id="F1777",
        name="Manage Scheduling Agreements",
        description="Create and maintain outline agreements with vendors.",
        catalog_id="SAP_MM_BC_SA_MANAGE",
        catalog_name="Scheduling Agreement Management",
        space_id="SAP_MM_PURCHASING",
        page_id="SAP_MM_PURCHASING_PAGE",
        odata_services=["MM_PUR_SA_MAINT_SRV"],
        backend_transactions=["ME31L", "ME32L", "ME33L"],
        required_auth_objects=[
            {"object": "M_BEST_BSA", "field": "BSART", "value": "LP"},
            {"object": "M_BEST_EKO", "field": "EKORG", "value": "*"},
            {"object": "S_SERVICE",  "field": "SRV_NAME", "value": "MM_PUR_SA_MAINT_SRV"},
        ],
        target_mapping_id="SchedulingAgreement-manage",
        semantic_object="SchedulingAgreement",
        semantic_action="manage",
        risk_level=RiskLevel.MEDIUM,
        business_area="Materials Management",
        tags=["procurement", "scheduling agreement", "vendor"],
    ),
    FioriApp(
        app_id="F3105",
        name="Display Audit Logs",
        description="View and export system and security audit log entries.",
        catalog_id="SAP_BASIS_BC_AUDIT_DISPLAY",
        catalog_name="Audit Log Management",
        space_id="SAP_BASIS_ADMIN",
        page_id="SAP_BASIS_ADMIN_PAGE",
        odata_services=["AUDITLOG_DISPLAY_SRV"],
        backend_transactions=["SM19", "SM20", "SM21"],
        required_auth_objects=[
            {"object": "S_ADMI_FCD", "field": "S_ADMI_FCD", "value": "SM19"},
            {"object": "S_SERVICE",  "field": "SRV_NAME", "value": "AUDITLOG_DISPLAY_SRV"},
        ],
        target_mapping_id="AuditLog-display",
        semantic_object="AuditLog",
        semantic_action="display",
        risk_level=RiskLevel.HIGH,
        business_area="Basis",
        tags=["basis", "audit", "security log", "compliance"],
    ),
]

# ---------------------------------------------------------------------------
# Runtime caches — populated from DB by _ensure_loaded()
# ---------------------------------------------------------------------------

_FIORI_APPS: List[FioriApp] = []
_APP_INDEX: Dict[str, FioriApp] = {}
_fiori_loaded: bool = False


def _db_record_to_fiori_app(row: FioriAppRecord) -> FioriApp:
    """Convert a FioriAppRecord ORM row into a FioriApp dataclass."""
    try:
        risk = RiskLevel(row.risk_level or "low")
    except ValueError:
        risk = RiskLevel.LOW

    return FioriApp(
        app_id=row.app_id,
        name=row.name,
        description=row.description or "",
        catalog_id=row.catalog_id or "",
        catalog_name=row.catalog_name or "",
        space_id=row.space_id or "",
        page_id=f"{row.space_id}_PAGE" if row.space_id else "",   # derived — not stored separately
        odata_services=row.odata_services or [],
        backend_transactions=row.backend_transactions or [],
        required_auth_objects=row.required_auth_objects or [],
        target_mapping_id=row.target_mapping_id or "",
        semantic_object=row.semantic_object or "",
        semantic_action=row.semantic_action or "",
        risk_level=risk,
        business_area=row.business_area or "",
    )


def _ensure_loaded() -> None:
    """
    Populate _FIORI_APPS and _APP_INDEX from the database on first access.

    If the fiori_apps table is empty, seeds it from _FIORI_APPS_SEED so the
    engine works out of the box on a fresh deployment.  Subsequent calls are
    no-ops (flag guard).  After loading, rebuilds the catalog index.
    """
    global _fiori_loaded
    if _fiori_loaded:
        return

    try:
        if not db_manager._initialized:
            db_manager.init()

        with db_manager.session_scope() as session:
            count = session.query(FioriAppRecord).count()

            if count == 0:
                logger.info(
                    "fiori_apps table is empty — seeding %d records from built-in knowledge base",
                    len(_FIORI_APPS_SEED),
                )
                for app in _FIORI_APPS_SEED:
                    record = FioriAppRecord(
                        tenant_id="tenant_default",
                        app_id=app.app_id,
                        name=app.name,
                        description=app.description,
                        catalog_id=app.catalog_id,
                        catalog_name=app.catalog_name,
                        space_id=app.space_id,
                        odata_services=app.odata_services,
                        backend_transactions=app.backend_transactions,
                        required_auth_objects=app.required_auth_objects,
                        target_mapping_id=app.target_mapping_id,
                        semantic_object=app.semantic_object,
                        semantic_action=app.semantic_action,
                        risk_level=app.risk_level.value,
                        business_area=app.business_area,
                    )
                    session.add(record)
                # session_scope auto-commits on exit

            rows = session.query(FioriAppRecord).all()

        _FIORI_APPS.clear()
        _APP_INDEX.clear()
        for row in rows:
            fiori_app = _db_record_to_fiori_app(row)
            _FIORI_APPS.append(fiori_app)
            _APP_INDEX[fiori_app.app_id] = fiori_app

        # Rebuild the catalog index from the freshly loaded apps
        _build_catalog_index()

        _fiori_loaded = True
        logger.debug("_FIORI_APPS loaded: %d entries from DB", len(_FIORI_APPS))

    except Exception as exc:
        logger.warning(
            "Could not load Fiori apps from DB (%s); falling back to seed data.",
            exc,
        )
        # Fallback: use hardcoded seed so the engine stays functional
        _FIORI_APPS.clear()
        _FIORI_APPS.extend(_FIORI_APPS_SEED)
        _APP_INDEX.clear()
        _APP_INDEX.update({app.app_id: app for app in _FIORI_APPS_SEED})
        _build_catalog_index()
        _fiori_loaded = True


# Mock user-role assignments: user_id -> list of assigned catalogs
_USER_CATALOGS: Dict[str, List[str]] = {
    "U001": ["SAP_MM_BC_PO_MANAGE", "SAP_MM_BC_PR_MANAGE", "SAP_BASIS_BC_USER_SETTINGS",
             "SAP_BASIS_BC_WF_INBOX"],
    "U002": ["SAP_FIN_BC_GL_POSTING", "SAP_FIN_BC_AP_INVOICE", "SAP_FIN_BC_AP_PAYMENT",
             "SAP_FIN_BC_GL_REPORTING", "SAP_BASIS_BC_WF_INBOX"],
    "U003": ["SAP_BASIS_BC_USER_MANAGE", "SAP_BASIS_BC_ROLE_MANAGE",
             "SAP_BASIS_BC_AUDIT_DISPLAY", "SAP_BASIS_BC_USER_SETTINGS"],
    "U004": ["SAP_SD_BC_SO_MANAGE", "SAP_SD_BC_BP_MANAGE", "SAP_MM_BC_PR_MANAGE",
             "SAP_BASIS_BC_WF_INBOX"],
    "U005": ["SAP_HR_BC_PA_MANAGE", "SAP_HR_BC_PAYROLL_RUN", "SAP_BASIS_BC_WF_INBOX"],
}

# Mock S_SERVICE assignments per user (what gateway services they can call)
_USER_S_SERVICE: Dict[str, List[str]] = {
    "U001": ["MM_PUR_PR_MAINT_SRV", "USER_SETTINGS_SRV", "TASKPROCESSING"],
    # U001 is missing MM_PUR_PO_MAINT_V2_SRV — classic catalog/S_SERVICE mismatch
    "U002": ["FIN_GL_ITEMS_SRV", "FIN_GL_REPORTING_SRV", "TASKPROCESSING"],
    # U002 is missing FIN_AP_INV_ENTRY_SRV and FIN_AP_ITEMS_SRV
    "U003": ["USER_MANAGEMENT_SRV", "ROLE_MANAGEMENT_SRV", "AUDITLOG_DISPLAY_SRV",
             "USER_SETTINGS_SRV"],
    "U004": ["SD_SALES_ORDER_MANAGE_V2", "API_BUSINESS_PARTNER", "MM_PUR_PR_MAINT_SRV",
             "TASKPROCESSING"],
    "U005": ["HR_PA_EMPLOYEE_SRV", "TASKPROCESSING"],
    # U005 is missing HR_PAYROLL_RUN_SRV
}


# ===========================================================================
# Catalog knowledge base
# ===========================================================================

_CATALOGS: Dict[str, Dict[str, Any]] = {}

def _build_catalog_index() -> None:
    """Build catalog index from the runtime _FIORI_APPS list.

    Called by _ensure_loaded() after apps are fetched from the database.
    Uses the module-level _FIORI_APPS list, which is populated at that point.
    """
    _CATALOGS.clear()
    for app in _FIORI_APPS:
        cid = app.catalog_id
        if cid not in _CATALOGS:
            _CATALOGS[cid] = {
                "catalog_id": cid,
                "catalog_name": app.catalog_name,
                "catalog_type": "target",
                "apps": [],
                "odata_services": set(),
                "required_auth_objects": set(),
                "risk_level": app.risk_level,
                "assigned_business_roles": [f"SAP_{cid.split('_BC_')[-1]}_ROLE"],
            }
        _CATALOGS[cid]["apps"].append({"app_id": app.app_id, "app_name": app.name})
        for svc in app.odata_services:
            _CATALOGS[cid]["odata_services"].add(svc)
        for ao in app.required_auth_objects:
            _CATALOGS[cid]["required_auth_objects"].add(ao["object"])
        # Escalate risk level
        levels = [RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL]
        if levels.index(app.risk_level) > levels.index(_CATALOGS[cid]["risk_level"]):
            _CATALOGS[cid]["risk_level"] = app.risk_level

# Note: _build_catalog_index() is now called inside _ensure_loaded() after DB
# data is fetched, not at module import time.


# ===========================================================================
# Analyzer engine
# ===========================================================================

class FioriSecurityAnalyzer:
    """
    Traces the SAP Fiori authorization chain for diagnostic and audit purposes.

    Each Fiori app access flows through eight distinct authorization layers.
    This engine evaluates each layer in sequence, short-circuits on the first
    hard failure, and returns structured diagnostic output.
    """

    def list_apps(self) -> List[FioriApp]:
        """Return the full Fiori app catalog."""
        _ensure_loaded()
        return list(_FIORI_APPS)

    def get_app_requirements(self, app_id: str) -> AppRequirements:
        """
        Return all authorization requirements for a given Fiori app.

        Raises ValueError if the app_id is not found in the knowledge base.
        """
        _ensure_loaded()
        app = _APP_INDEX.get(app_id)
        if not app:
            raise ValueError(f"Unknown Fiori app: {app_id}")

        s_service_entries = [
            {
                "srv_name": svc,
                "icf_path": f"/sap/opu/odata/sap/{svc}",
                "auth_object": "S_SERVICE",
            }
            for svc in app.odata_services
        ]

        return AppRequirements(
            app_id=app.app_id,
            app_name=app.name,
            odata_services=app.odata_services,
            backend_transactions=app.backend_transactions,
            auth_objects=app.required_auth_objects,
            s_service_entries=s_service_entries,
            catalog_id=app.catalog_id,
            target_mapping_id=app.target_mapping_id,
            gateway_alias="DEFAULT_HOST",
            risk_level=app.risk_level,
            notes=[
                f"Semantic object: {app.semantic_object}",
                f"Semantic action: {app.semantic_action}",
                f"Business area: {app.business_area}",
            ],
        )

    def analyze_catalog(self, catalog_id: str) -> CatalogAnalysis:
        """
        Analyze all apps, services, and authorization objects in a catalog.

        Raises ValueError if the catalog_id is not known.
        """
        _ensure_loaded()
        cat = _CATALOGS.get(catalog_id)
        if not cat:
            raise ValueError(f"Unknown catalog: {catalog_id}")

        return CatalogAnalysis(
            catalog_id=catalog_id,
            catalog_name=cat["catalog_name"],
            catalog_type=cat["catalog_type"],
            app_count=len(cat["apps"]),
            apps=cat["apps"],
            odata_services=sorted(cat["odata_services"]),
            required_auth_objects=sorted(cat["required_auth_objects"]),
            risk_level=cat["risk_level"],
            assigned_business_roles=cat["assigned_business_roles"],
            notes=(
                f"Catalog contains {len(cat['apps'])} app(s) and requires "
                f"{len(cat['odata_services'])} OData service(s)."
            ),
        )

    def trace_app(self, app_id: str, user_id: str) -> FioriAccessTrace:
        """
        Trace the full Fiori authorization chain for a user/app combination.

        Evaluates each of the eight layers in sequence. The overall status
        reflects the worst-case status across all layers.
        """
        _ensure_loaded()
        app = _APP_INDEX.get(app_id)
        if not app:
            raise ValueError(f"Unknown Fiori app: {app_id}")

        timestamp = datetime.utcnow().isoformat() + "Z"
        user_catalogs = _USER_CATALOGS.get(user_id, [])
        user_services = _USER_S_SERVICE.get(user_id, [])

        chain: List[ChainLayer] = []
        error_pattern = ErrorPattern.NO_ERROR

        # --- Layer 1: Launchpad / Fiori Launchpad shell ---
        chain.append(ChainLayer(
            layer_name="Launchpad Shell",
            status=LayerStatus.PASS,
            object_id="FLP",
            object_name="SAP Fiori Launchpad",
            details="User has access to the Fiori Launchpad shell (S_START or logon check).",
            required_auth=["S_RFC:FUNC_GROUP=SYST"],
        ))

        # --- Layer 2: Business Role assignment ---
        has_catalog = app.catalog_id in user_catalogs
        chain.append(ChainLayer(
            layer_name="Business Role / Catalog Assignment",
            status=LayerStatus.PASS if has_catalog else LayerStatus.FAIL,
            object_id=app.catalog_id,
            object_name=app.catalog_name,
            details=(
                f"Catalog '{app.catalog_id}' is assigned to user via business role."
                if has_catalog
                else f"Catalog '{app.catalog_id}' is NOT assigned to user. "
                     "Check business role assignment in PFCG."
            ),
            required_auth=[f"Catalog: {app.catalog_id}"],
            missing_auth=[] if has_catalog else [f"Catalog: {app.catalog_id}"],
            remediation=None if has_catalog else (
                f"Assign the business role containing catalog '{app.catalog_id}' "
                "to the user via role assignment."
            ),
        ))

        if not has_catalog:
            error_pattern = ErrorPattern.MISSING_CATALOG
            return self._build_trace(
                app_id, user_id, timestamp,
                LayerStatus.FAIL, error_pattern, chain,
                f"Access denied at Layer 2: catalog '{app.catalog_id}' not assigned.",
                [chain[-1].remediation],
            )

        # --- Layer 3: Space/Page visibility ---
        chain.append(ChainLayer(
            layer_name="Space / Page Visibility",
            status=LayerStatus.PASS,
            object_id=app.space_id,
            object_name=f"{app.space_id} / {app.page_id}",
            details=(
                f"Space '{app.space_id}' and page '{app.page_id}' visible. "
                "Space/page assignment is derived from business role."
            ),
            required_auth=[f"Space: {app.space_id}"],
        ))

        # --- Layer 4: Tile rendering ---
        chain.append(ChainLayer(
            layer_name="Tile Rendering",
            status=LayerStatus.PASS,
            object_id=app.app_id,
            object_name=app.name,
            details=f"Tile for app '{app.name}' renders successfully (catalog present).",
            required_auth=["Catalog assignment (derived from Layer 2)"],
        ))

        # --- Layer 5: Target Mapping ---
        chain.append(ChainLayer(
            layer_name="Target Mapping",
            status=LayerStatus.PASS,
            object_id=app.target_mapping_id,
            object_name=f"{app.semantic_object}-{app.semantic_action}",
            details=(
                f"Target mapping '{app.target_mapping_id}' found for "
                f"intent '{app.semantic_object}#{app.semantic_action}'."
            ),
            required_auth=[f"Target mapping: {app.target_mapping_id}"],
        ))

        # --- Layer 6: OData Service / S_SERVICE check ---
        missing_services = [
            svc for svc in app.odata_services
            if svc not in user_services
        ]
        s_service_status = LayerStatus.PASS if not missing_services else LayerStatus.FAIL
        chain.append(ChainLayer(
            layer_name="OData Service / S_SERVICE Authorization",
            status=s_service_status,
            object_id="S_SERVICE",
            object_name="ICF Service Authorization",
            details=(
                "All required OData services are authorized via S_SERVICE."
                if not missing_services
                else f"Missing S_SERVICE entries for: {', '.join(missing_services)}. "
                     "User sees the tile but gets authorization error on launch."
            ),
            required_auth=[f"S_SERVICE:{svc}" for svc in app.odata_services],
            missing_auth=[f"S_SERVICE:{svc}" for svc in missing_services],
            remediation=None if not missing_services else (
                f"Add S_SERVICE entries for {', '.join(missing_services)} "
                "to the user's role via PFCG -> Authorization Data -> S_SERVICE."
            ),
        ))

        if missing_services:
            error_pattern = ErrorPattern.MISSING_S_SERVICE
            return self._build_trace(
                app_id, user_id, timestamp,
                LayerStatus.FAIL, error_pattern, chain,
                f"Access denied at Layer 6: S_SERVICE missing for "
                f"{', '.join(missing_services)}. Tile is visible but app fails to launch.",
                [chain[-1].remediation],
            )

        # --- Layer 7: Gateway Authorization ---
        chain.append(ChainLayer(
            layer_name="SAP Gateway Authorization",
            status=LayerStatus.PASS,
            object_id="GW_SRV",
            object_name="Gateway Service Activation",
            details=(
                f"Gateway services {app.odata_services} are activated and accessible. "
                "Gateway alias: DEFAULT_HOST."
            ),
            required_auth=["Gateway service activation", "ICF node /sap/opu/odata active"],
        ))

        # --- Layer 8: Backend Authorization ---
        backend_auth_objects = [ao for ao in app.required_auth_objects
                                 if ao["object"] != "S_SERVICE"]
        # For mock purposes, assume backend auth passes for all users who have catalog
        chain.append(ChainLayer(
            layer_name="Backend Authorization Objects",
            status=LayerStatus.PASS,
            object_id="BACKEND_AUTH",
            object_name="Backend ABAP Authorization",
            details=(
                f"Backend transactions {app.backend_transactions} are authorized. "
                f"Required objects: "
                f"{', '.join(ao['object'] for ao in backend_auth_objects)} — all present."
            ),
            required_auth=[
                f"{ao['object']}:{ao['field']}={ao['value']}"
                for ao in backend_auth_objects
            ],
        ))

        return self._build_trace(
            app_id, user_id, timestamp,
            LayerStatus.PASS, ErrorPattern.NO_ERROR, chain,
            f"Full authorization chain passed for app '{app.name}' (user: {user_id}).",
            [],
        )

    def diagnose_tile_error(self, app_id: str, user_id: str) -> TileDiagnosis:
        """
        Diagnose the 'tile visible but app launch fails' pattern.

        This is the most common Fiori support ticket. The tile is visible because
        the catalog is assigned via a business role, but the S_SERVICE check
        (or backend auth) fails when the OData call is made.
        """
        _ensure_loaded()
        app = _APP_INDEX.get(app_id)
        if not app:
            raise ValueError(f"Unknown Fiori app: {app_id}")

        user_catalogs = _USER_CATALOGS.get(user_id, [])
        user_services = _USER_S_SERVICE.get(user_id, [])

        tile_visible = app.catalog_id in user_catalogs

        if not tile_visible:
            return TileDiagnosis(
                app_id=app_id,
                user_id=user_id,
                tile_visible=False,
                launch_fails=True,
                root_cause="Catalog not assigned — tile is not visible at all.",
                error_pattern=ErrorPattern.MISSING_CATALOG,
                failing_layer="Business Role / Catalog Assignment",
                missing_objects=[f"Catalog: {app.catalog_id}"],
                remediation_steps=[
                    f"Assign business role containing catalog '{app.catalog_id}' to user '{user_id}'.",
                    "Use PFCG to find roles that contain this catalog.",
                    "Run SU01 -> Roles tab to add the role.",
                ],
                estimated_effort="5-15 minutes",
            )

        missing_services = [
            svc for svc in app.odata_services
            if svc not in user_services
        ]

        if missing_services:
            return TileDiagnosis(
                app_id=app_id,
                user_id=user_id,
                tile_visible=True,
                launch_fails=True,
                root_cause=(
                    f"S_SERVICE authorization missing for OData service(s): "
                    f"{', '.join(missing_services)}. Catalog is assigned so tile "
                    "is visible, but the OData call is rejected by the ICF layer."
                ),
                error_pattern=ErrorPattern.MISSING_S_SERVICE,
                failing_layer="OData Service / S_SERVICE Authorization",
                missing_objects=[f"S_SERVICE:{svc}" for svc in missing_services],
                remediation_steps=[
                    f"Open PFCG and find the role(s) assigned to user '{user_id}'.",
                    "Navigate to Authorization Data tab.",
                    f"Add S_SERVICE entries: SRV_NAME = {', '.join(missing_services)}.",
                    "Regenerate profile and re-assign role to user.",
                    "Alternatively, use SU24 to propose S_SERVICE via the OData service node.",
                ],
                estimated_effort="15-30 minutes",
            )

        return TileDiagnosis(
            app_id=app_id,
            user_id=user_id,
            tile_visible=True,
            launch_fails=False,
            root_cause="No authorization issue detected. App should launch successfully.",
            error_pattern=ErrorPattern.NO_ERROR,
            failing_layer="None",
            missing_objects=[],
            remediation_steps=[],
            estimated_effort="N/A",
        )

    def list_catalogs(self) -> List[Dict[str, Any]]:
        """Return a summary list of all known catalogs."""
        _ensure_loaded()
        result = []
        for cid, cat in _CATALOGS.items():
            result.append({
                "catalog_id": cid,
                "catalog_name": cat["catalog_name"],
                "app_count": len(cat["apps"]),
                "risk_level": cat["risk_level"].value,
                "odata_service_count": len(cat["odata_services"]),
            })
        return result

    def list_odata_services(self) -> List[Dict[str, str]]:
        """Return a deduplicated list of all OData services referenced by known apps."""
        services: Dict[str, Dict[str, str]] = {}
        for app in _FIORI_APPS:
            for svc in app.odata_services:
                if svc not in services:
                    services[svc] = {
                        "service_name": svc,
                        "icf_path": f"/sap/opu/odata/sap/{svc}",
                        "used_by_app": app.app_id,
                        "used_by_app_name": app.name,
                        "business_area": app.business_area,
                    }
        return list(services.values())

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _build_trace(
        app_id: str,
        user_id: str,
        timestamp: str,
        overall_status: LayerStatus,
        error_pattern: ErrorPattern,
        chain: List[ChainLayer],
        summary: str,
        remediation_steps: List[Optional[str]],
    ) -> FioriAccessTrace:
        return FioriAccessTrace(
            app_id=app_id,
            user_id=user_id,
            timestamp=timestamp,
            overall_status=overall_status,
            error_pattern=error_pattern,
            chain=chain,
            summary=summary,
            remediation_steps=[s for s in remediation_steps if s],
        )
