"""
Comprehensive SoD Ruleset

Pre-built Segregation of Duties rules based on industry best practices.
Covers all major SAP business processes:
- Finance (FI)
- Procurement (MM/P2P)
- Sales (SD/O2C)
- Human Resources (HR)
- Basis/Security
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum


class RiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class BusinessProcess(Enum):
    FINANCE = "FI"
    PROCUREMENT = "MM"
    SALES = "SD"
    HR = "HR"
    BASIS = "BASIS"
    TREASURY = "TR"
    ASSET = "AA"
    WAREHOUSE = "WM"
    QUALITY = "QM"
    PLANT_MAINT = "PM"
    PROJECT = "PS"
    GENERAL = "GEN"


@dataclass
class BusinessFunction:
    """A business function that can conflict with another"""
    function_id: str
    name: str
    description: str
    business_process: BusinessProcess
    transaction_codes: List[str] = field(default_factory=list)
    auth_objects: List[Dict] = field(default_factory=list)
    # Example auth_object: {"object": "F_BKPF_BUK", "field": "ACTVT", "values": ["01", "02"]}

    def to_dict(self) -> Dict:
        return {
            "function_id": self.function_id,
            "name": self.name,
            "description": self.description,
            "business_process": self.business_process.value,
            "transaction_codes": self.transaction_codes,
            "auth_objects": self.auth_objects
        }


@dataclass
class SoDRule:
    """A Segregation of Duties rule"""
    rule_id: str
    name: str
    description: str
    risk_level: RiskLevel
    business_process: BusinessProcess

    # Conflicting functions
    function1: BusinessFunction
    function2: BusinessFunction

    # Risk description
    risk_description: str = ""
    business_impact: str = ""
    recommendation: str = ""

    # Regulatory references
    sox_relevant: bool = False
    gdpr_relevant: bool = False
    regulatory_refs: List[str] = field(default_factory=list)

    is_active: bool = True
    is_cross_system: bool = False

    def to_dict(self) -> Dict:
        return {
            "rule_id": self.rule_id,
            "name": self.name,
            "description": self.description,
            "risk_level": self.risk_level.value,
            "business_process": self.business_process.value,
            "function1": self.function1.to_dict(),
            "function2": self.function2.to_dict(),
            "risk_description": self.risk_description,
            "business_impact": self.business_impact,
            "recommendation": self.recommendation,
            "sox_relevant": self.sox_relevant,
            "gdpr_relevant": self.gdpr_relevant,
            "is_active": self.is_active
        }


class SoDRulesetLibrary:
    """
    Comprehensive library of SoD rules.
    Zero-training: Pre-configured with industry best practices.
    """

    def __init__(self):
        self.functions: Dict[str, BusinessFunction] = {}
        self.rules: Dict[str, SoDRule] = {}
        self._init_functions()
        self._init_rules()

    def _init_functions(self):
        """Initialize business functions catalog"""

        # =================================================================
        # FINANCE FUNCTIONS
        # =================================================================
        fi_functions = [
            BusinessFunction(
                function_id="FI001",
                name="Vendor Master Maintenance",
                description="Create, change, delete vendor master records",
                business_process=BusinessProcess.FINANCE,
                transaction_codes=["FK01", "FK02", "FK03", "XK01", "XK02", "XK03"],
                auth_objects=[
                    {"object": "F_LFA1_BUK", "field": "ACTVT", "values": ["01", "02", "06"]},
                    {"object": "F_LFA1_GRP", "field": "ACTVT", "values": ["01", "02"]}
                ]
            ),
            BusinessFunction(
                function_id="FI002",
                name="AP Invoice Entry",
                description="Enter and post vendor invoices",
                business_process=BusinessProcess.FINANCE,
                transaction_codes=["FB60", "MIRO", "FV60"],
                auth_objects=[
                    {"object": "F_BKPF_BUK", "field": "ACTVT", "values": ["01", "02"]},
                    {"object": "F_BKPF_KOA", "field": "KOART", "values": ["K"]}
                ]
            ),
            BusinessFunction(
                function_id="FI003",
                name="AP Payment Processing",
                description="Execute vendor payment runs",
                business_process=BusinessProcess.FINANCE,
                transaction_codes=["F110", "F111", "FBZ1", "FBZ2"],
                auth_objects=[
                    {"object": "F_REGU_BUK", "field": "ACTVT", "values": ["01", "02"]},
                    {"object": "F_BKPF_BUK", "field": "ACTVT", "values": ["01"]}
                ]
            ),
            BusinessFunction(
                function_id="FI004",
                name="Customer Master Maintenance",
                description="Create, change, delete customer master records",
                business_process=BusinessProcess.FINANCE,
                transaction_codes=["FD01", "FD02", "FD03", "XD01", "XD02"],
                auth_objects=[
                    {"object": "F_KNA1_BUK", "field": "ACTVT", "values": ["01", "02", "06"]},
                    {"object": "F_KNA1_GRP", "field": "ACTVT", "values": ["01", "02"]}
                ]
            ),
            BusinessFunction(
                function_id="FI005",
                name="AR Invoice Entry",
                description="Enter and post customer invoices",
                business_process=BusinessProcess.FINANCE,
                transaction_codes=["FB70", "VF01", "FV70"],
                auth_objects=[
                    {"object": "F_BKPF_BUK", "field": "ACTVT", "values": ["01", "02"]},
                    {"object": "F_BKPF_KOA", "field": "KOART", "values": ["D"]}
                ]
            ),
            BusinessFunction(
                function_id="FI006",
                name="AR Cash Application",
                description="Apply incoming payments to customer invoices",
                business_process=BusinessProcess.FINANCE,
                transaction_codes=["F-28", "F-32", "FBZ3", "FBZ4"],
                auth_objects=[
                    {"object": "F_BKPF_BUK", "field": "ACTVT", "values": ["01", "02"]}
                ]
            ),
            BusinessFunction(
                function_id="FI007",
                name="GL Journal Entry",
                description="Post general ledger journal entries",
                business_process=BusinessProcess.FINANCE,
                transaction_codes=["FB50", "FB01", "FV50", "F-02"],
                auth_objects=[
                    {"object": "F_BKPF_BUK", "field": "ACTVT", "values": ["01", "02"]},
                    {"object": "F_BKPF_KOA", "field": "KOART", "values": ["S"]}
                ]
            ),
            BusinessFunction(
                function_id="FI008",
                name="GL Period Close",
                description="Execute period-end closing activities",
                business_process=BusinessProcess.FINANCE,
                transaction_codes=["MMPV", "F.05", "FAGLB03", "OB52"],
                auth_objects=[
                    {"object": "F_BKPF_BUK", "field": "ACTVT", "values": ["01", "02"]}
                ]
            ),
            BusinessFunction(
                function_id="FI009",
                name="Bank Master Maintenance",
                description="Maintain bank master data and house banks",
                business_process=BusinessProcess.FINANCE,
                transaction_codes=["FI12", "FI13", "FBZP"],
                auth_objects=[
                    {"object": "F_BNKA_MAN", "field": "ACTVT", "values": ["01", "02"]}
                ]
            ),
            BusinessFunction(
                function_id="FI010",
                name="Credit Memo Processing",
                description="Create and post credit memos",
                business_process=BusinessProcess.FINANCE,
                transaction_codes=["FB65", "FB75", "MIRA"],
                auth_objects=[
                    {"object": "F_BKPF_BUK", "field": "ACTVT", "values": ["01", "02"]}
                ]
            ),
        ]

        # =================================================================
        # PROCUREMENT FUNCTIONS (P2P)
        # =================================================================
        mm_functions = [
            BusinessFunction(
                function_id="MM001",
                name="Purchase Requisition",
                description="Create and release purchase requisitions",
                business_process=BusinessProcess.PROCUREMENT,
                transaction_codes=["ME51N", "ME52N", "ME54N", "ME55"],
                auth_objects=[
                    {"object": "M_BANF_WRK", "field": "ACTVT", "values": ["01", "02"]},
                    {"object": "M_BANF_BSA", "field": "ACTVT", "values": ["01"]}
                ]
            ),
            BusinessFunction(
                function_id="MM002",
                name="Purchase Order Creation",
                description="Create and change purchase orders",
                business_process=BusinessProcess.PROCUREMENT,
                transaction_codes=["ME21N", "ME22N", "ME23N", "ME28", "ME29N"],
                auth_objects=[
                    {"object": "M_BEST_WRK", "field": "ACTVT", "values": ["01", "02"]},
                    {"object": "M_BEST_BSA", "field": "ACTVT", "values": ["01"]}
                ]
            ),
            BusinessFunction(
                function_id="MM003",
                name="Goods Receipt",
                description="Post goods receipts for purchase orders",
                business_process=BusinessProcess.PROCUREMENT,
                transaction_codes=["MIGO", "MB01", "MB1A", "MB1C"],
                auth_objects=[
                    {"object": "M_MSEG_WMB", "field": "ACTVT", "values": ["01", "02"]},
                    {"object": "M_MSEG_BWA", "field": "BWART", "values": ["101", "102"]}
                ]
            ),
            BusinessFunction(
                function_id="MM004",
                name="Invoice Verification",
                description="Enter and post logistics invoices",
                business_process=BusinessProcess.PROCUREMENT,
                transaction_codes=["MIRO", "MIR7", "MIR4"],
                auth_objects=[
                    {"object": "M_RECH_WRK", "field": "ACTVT", "values": ["01", "02"]}
                ]
            ),
            BusinessFunction(
                function_id="MM005",
                name="Material Master Maintenance",
                description="Create and change material master records",
                business_process=BusinessProcess.PROCUREMENT,
                transaction_codes=["MM01", "MM02", "MM03", "MM06"],
                auth_objects=[
                    {"object": "M_MATE_WRK", "field": "ACTVT", "values": ["01", "02"]},
                    {"object": "M_MATE_MAR", "field": "ACTVT", "values": ["01", "02"]}
                ]
            ),
            BusinessFunction(
                function_id="MM006",
                name="Vendor Evaluation",
                description="Maintain vendor evaluation scores",
                business_process=BusinessProcess.PROCUREMENT,
                transaction_codes=["ME61", "ME62", "ME63"],
                auth_objects=[
                    {"object": "M_BEST_WRK", "field": "ACTVT", "values": ["02"]}
                ]
            ),
            BusinessFunction(
                function_id="MM007",
                name="Source List Maintenance",
                description="Maintain source lists and quota arrangements",
                business_process=BusinessProcess.PROCUREMENT,
                transaction_codes=["ME01", "ME03", "MEQ1", "MEQ3"],
                auth_objects=[
                    {"object": "M_RAHM_WRK", "field": "ACTVT", "values": ["01", "02"]}
                ]
            ),
        ]

        # =================================================================
        # SALES FUNCTIONS (O2C)
        # =================================================================
        sd_functions = [
            BusinessFunction(
                function_id="SD001",
                name="Sales Order Creation",
                description="Create and change sales orders",
                business_process=BusinessProcess.SALES,
                transaction_codes=["VA01", "VA02", "VA03"],
                auth_objects=[
                    {"object": "V_VBAK_VKO", "field": "ACTVT", "values": ["01", "02"]},
                    {"object": "V_VBAK_AAT", "field": "AUART", "values": ["*"]}
                ]
            ),
            BusinessFunction(
                function_id="SD002",
                name="Delivery Processing",
                description="Create and process outbound deliveries",
                business_process=BusinessProcess.SALES,
                transaction_codes=["VL01N", "VL02N", "VL03N", "VL06O"],
                auth_objects=[
                    {"object": "V_LIKP_VKO", "field": "ACTVT", "values": ["01", "02"]}
                ]
            ),
            BusinessFunction(
                function_id="SD003",
                name="Billing Document Creation",
                description="Create billing documents/invoices",
                business_process=BusinessProcess.SALES,
                transaction_codes=["VF01", "VF02", "VF03", "VF04"],
                auth_objects=[
                    {"object": "V_VBRK_VKO", "field": "ACTVT", "values": ["01", "02"]}
                ]
            ),
            BusinessFunction(
                function_id="SD004",
                name="Pricing Maintenance",
                description="Maintain pricing conditions and master data",
                business_process=BusinessProcess.SALES,
                transaction_codes=["VK11", "VK12", "VK13", "VK31", "VK32"],
                auth_objects=[
                    {"object": "V_KONH_VKO", "field": "ACTVT", "values": ["01", "02"]}
                ]
            ),
            BusinessFunction(
                function_id="SD005",
                name="Credit Management",
                description="Manage customer credit limits and blocks",
                business_process=BusinessProcess.SALES,
                transaction_codes=["FD32", "FD33", "VKM1", "VKM3"],
                auth_objects=[
                    {"object": "F_KNA1_BUK", "field": "ACTVT", "values": ["02"]}
                ]
            ),
            BusinessFunction(
                function_id="SD006",
                name="Returns Processing",
                description="Process sales returns and credits",
                business_process=BusinessProcess.SALES,
                transaction_codes=["VA01", "VL01N", "VF01"],  # with return doc types
                auth_objects=[
                    {"object": "V_VBAK_VKO", "field": "ACTVT", "values": ["01", "02"]}
                ]
            ),
        ]

        # =================================================================
        # HR FUNCTIONS
        # =================================================================
        hr_functions = [
            BusinessFunction(
                function_id="HR001",
                name="Personnel Master Maintenance",
                description="Create and change employee master data",
                business_process=BusinessProcess.HR,
                transaction_codes=["PA30", "PA40", "PA20"],
                auth_objects=[
                    {"object": "P_ORGIN", "field": "AUTHC", "values": ["*"]},
                    {"object": "P_PERNR", "field": "AUTHC", "values": ["*"]}
                ]
            ),
            BusinessFunction(
                function_id="HR002",
                name="Payroll Processing",
                description="Execute and release payroll runs",
                business_process=BusinessProcess.HR,
                transaction_codes=["PC00_M99_CALC", "PC00_M99_CDTA", "PA03"],
                auth_objects=[
                    {"object": "P_ABAP", "field": "REPID", "values": ["*"]}
                ]
            ),
            BusinessFunction(
                function_id="HR003",
                name="Time Management",
                description="Maintain time records and absences",
                business_process=BusinessProcess.HR,
                transaction_codes=["PA61", "PA62", "CAT2", "CATS"],
                auth_objects=[
                    {"object": "P_ORGIN", "field": "AUTHC", "values": ["*"]}
                ]
            ),
            BusinessFunction(
                function_id="HR004",
                name="Org Structure Maintenance",
                description="Maintain organizational structure",
                business_process=BusinessProcess.HR,
                transaction_codes=["PPOM_OLD", "PPOCE", "PO10"],
                auth_objects=[
                    {"object": "PLOG", "field": "PLESSION", "values": ["*"]}
                ]
            ),
            BusinessFunction(
                function_id="HR005",
                name="Bank Data Maintenance",
                description="Maintain employee bank details",
                business_process=BusinessProcess.HR,
                transaction_codes=["PA30"],  # Infotype 0009
                auth_objects=[
                    {"object": "P_ORGIN", "field": "INFTY", "values": ["0009"]}
                ]
            ),
        ]

        # =================================================================
        # BASIS/SECURITY FUNCTIONS
        # =================================================================
        basis_functions = [
            BusinessFunction(
                function_id="BA001",
                name="User Administration",
                description="Create, change, delete user accounts",
                business_process=BusinessProcess.BASIS,
                transaction_codes=["SU01", "SU01D", "SU10", "PFCG"],
                auth_objects=[
                    {"object": "S_USER_GRP", "field": "ACTVT", "values": ["01", "02", "05"]},
                    {"object": "S_USER_AGR", "field": "ACTVT", "values": ["01", "02"]}
                ]
            ),
            BusinessFunction(
                function_id="BA002",
                name="Role Administration",
                description="Create and modify authorization roles",
                business_process=BusinessProcess.BASIS,
                transaction_codes=["PFCG", "SU24", "SU25"],
                auth_objects=[
                    {"object": "S_USER_AGR", "field": "ACTVT", "values": ["01", "02"]}
                ]
            ),
            BusinessFunction(
                function_id="BA003",
                name="Table Maintenance",
                description="Direct table data maintenance",
                business_process=BusinessProcess.BASIS,
                transaction_codes=["SE16", "SE16N", "SM30", "SM31"],
                auth_objects=[
                    {"object": "S_TABU_DIS", "field": "ACTVT", "values": ["02", "03"]}
                ]
            ),
            BusinessFunction(
                function_id="BA004",
                name="Program Execution",
                description="Execute ABAP programs directly",
                business_process=BusinessProcess.BASIS,
                transaction_codes=["SA38", "SE38", "SE80"],
                auth_objects=[
                    {"object": "S_PROGRAM", "field": "P_ACTION", "values": ["SUBMIT"]}
                ]
            ),
            BusinessFunction(
                function_id="BA005",
                name="Transport Management",
                description="Release and import transports",
                business_process=BusinessProcess.BASIS,
                transaction_codes=["SE09", "SE10", "STMS"],
                auth_objects=[
                    {"object": "S_TRANSPRT", "field": "ACTVT", "values": ["01", "02", "43"]}
                ]
            ),
        ]

        # =================================================================
        # TREASURY FUNCTIONS
        # =================================================================
        tr_functions = [
            BusinessFunction("TR001", "Treasury Payment", "Execute treasury payments and wire transfers",
                BusinessProcess.TREASURY, ["FF67", "FF68", "F111", "FBZ1"],
                [{"object": "F_REGU_BUK", "field": "ACTVT", "values": ["01"]}]),
            BusinessFunction("TR002", "Bank Account Management", "Create and manage bank accounts",
                BusinessProcess.TREASURY, ["FI12", "FI13", "FBZP"],
                [{"object": "F_BNKA_MAN", "field": "ACTVT", "values": ["01", "02"]}]),
            BusinessFunction("TR003", "Investment Management", "Manage financial investments and securities",
                BusinessProcess.TREASURY, ["TBB1", "TBB2", "TB31"],
                [{"object": "F_T036", "field": "ACTVT", "values": ["01", "02"]}]),
            BusinessFunction("TR004", "Cash Position Management", "Monitor and manage cash positions",
                BusinessProcess.TREASURY, ["FF7A", "FF7B", "FF_5"],
                [{"object": "F_BNKA_MAN", "field": "ACTVT", "values": ["03"]}]),
        ]

        # =================================================================
        # ASSET ACCOUNTING FUNCTIONS
        # =================================================================
        aa_functions = [
            BusinessFunction("AA001", "Asset Master Maintenance", "Create and modify fixed asset records",
                BusinessProcess.ASSET, ["AS01", "AS02", "AS03", "AS05"],
                [{"object": "A_S_ANLKL", "field": "ACTVT", "values": ["01", "02"]}]),
            BusinessFunction("AA002", "Asset Acquisition", "Post asset acquisitions and capitalizations",
                BusinessProcess.ASSET, ["ABZON", "AB01", "ABNAN"],
                [{"object": "A_S_ANLKL", "field": "ACTVT", "values": ["01"]}]),
            BusinessFunction("AA003", "Asset Retirement", "Process asset retirements and disposals",
                BusinessProcess.ASSET, ["ABAVN", "ABT1N", "ABAON"],
                [{"object": "A_S_ANLKL", "field": "ACTVT", "values": ["06"]}]),
            BusinessFunction("AA004", "Asset Transfer", "Transfer assets between cost centers or companies",
                BusinessProcess.ASSET, ["ABUMN", "ABT1N"],
                [{"object": "A_S_ANLKL", "field": "ACTVT", "values": ["02"]}]),
            BusinessFunction("AA005", "Depreciation Run", "Execute periodic depreciation calculations",
                BusinessProcess.ASSET, ["AFAB", "AFAR", "AFBN"],
                [{"object": "A_S_ANLKL", "field": "ACTVT", "values": ["70"]}]),
        ]

        # =================================================================
        # WAREHOUSE MANAGEMENT FUNCTIONS
        # =================================================================
        wm_functions = [
            BusinessFunction("WM001", "Inventory Adjustment", "Post inventory adjustments and write-offs",
                BusinessProcess.WAREHOUSE, ["MB1A", "MB1B", "MB1C", "MI07"],
                [{"object": "M_MSEG_BWA", "field": "BWART", "values": ["201", "202", "561", "562"]}]),
            BusinessFunction("WM002", "Physical Inventory", "Execute and post physical inventory counts",
                BusinessProcess.WAREHOUSE, ["MI01", "MI04", "MI07", "MI20"],
                [{"object": "M_MSEG_WMB", "field": "ACTVT", "values": ["01", "02"]}]),
            BusinessFunction("WM003", "Stock Transfer", "Process stock transfers between plants and locations",
                BusinessProcess.WAREHOUSE, ["MB1B", "MIGO", "ME27"],
                [{"object": "M_MSEG_BWA", "field": "BWART", "values": ["301", "302", "311", "312"]}]),
        ]

        # =================================================================
        # QUALITY MANAGEMENT FUNCTIONS
        # =================================================================
        qm_functions = [
            BusinessFunction("QM001", "Quality Inspection", "Record quality inspection results",
                BusinessProcess.QUALITY, ["QA11", "QA12", "QA32"],
                [{"object": "Q_QMEL", "field": "ACTVT", "values": ["01", "02"]}]),
            BusinessFunction("QM002", "Usage Decision", "Make usage decisions for inspected lots",
                BusinessProcess.QUALITY, ["QA11", "QA12"],
                [{"object": "Q_QMEL", "field": "ACTVT", "values": ["02"]}]),
        ]

        # =================================================================
        # PLANT MAINTENANCE FUNCTIONS
        # =================================================================
        pm_functions = [
            BusinessFunction("PM001", "Maintenance Order", "Create and release maintenance work orders",
                BusinessProcess.PLANT_MAINT, ["IW31", "IW32", "IW33", "IW38"],
                [{"object": "I_AUFART", "field": "AUART", "values": ["*"]}]),
            BusinessFunction("PM002", "Service Entry", "Enter and accept service entry sheets",
                BusinessProcess.PLANT_MAINT, ["ML81N", "ML85"],
                [{"object": "M_BEST_WRK", "field": "ACTVT", "values": ["01", "02"]}]),
        ]

        # =================================================================
        # PROJECT SYSTEM FUNCTIONS
        # =================================================================
        ps_functions = [
            BusinessFunction("PS001", "Project Definition", "Create and modify project definitions",
                BusinessProcess.PROJECT, ["CJ01", "CJ02", "CJ03", "CJ20N"],
                [{"object": "C_PROJ_MAS", "field": "ACTVT", "values": ["01", "02"]}]),
            BusinessFunction("PS002", "Project Budget", "Set and release project budgets",
                BusinessProcess.PROJECT, ["CJ30", "CJ32", "CJ36"],
                [{"object": "C_PROJ_MAS", "field": "ACTVT", "values": ["77"]}]),
        ]

        # =================================================================
        # ADDITIONAL FINANCE FUNCTIONS
        # =================================================================
        fi_extra = [
            BusinessFunction("FI011", "Cost Center Maintenance", "Create and modify cost centers",
                BusinessProcess.FINANCE, ["KS01", "KS02", "KS03"],
                [{"object": "K_KOSTL", "field": "ACTVT", "values": ["01", "02"]}]),
            BusinessFunction("FI012", "Internal Order Maintenance", "Create and manage internal orders",
                BusinessProcess.FINANCE, ["KO01", "KO02", "KO03"],
                [{"object": "K_ORDER", "field": "ACTVT", "values": ["01", "02"]}]),
            BusinessFunction("FI013", "Profit Center Maintenance", "Create and modify profit centers",
                BusinessProcess.FINANCE, ["KE51", "KE52", "KE53"],
                [{"object": "K_PCA", "field": "ACTVT", "values": ["01", "02"]}]),
            BusinessFunction("FI014", "Financial Reporting", "Execute financial reports and extracts",
                BusinessProcess.FINANCE, ["S_ALR_87012284", "F.01", "FAGLB03"],
                [{"object": "F_BKPF_BUK", "field": "ACTVT", "values": ["03"]}]),
            BusinessFunction("FI015", "Tax Configuration", "Maintain tax codes and tax determination",
                BusinessProcess.FINANCE, ["FTXP", "OBCL", "OBCD"],
                [{"object": "F_BKPF_BUK", "field": "ACTVT", "values": ["01", "02"]}]),
            BusinessFunction("FI016", "Tolerance Group Maintenance", "Maintain payment and posting tolerances",
                BusinessProcess.FINANCE, ["OBA4", "OBAZ"],
                [{"object": "S_TABU_DIS", "field": "ACTVT", "values": ["02"]}]),
        ]

        # =================================================================
        # ADDITIONAL PROCUREMENT FUNCTIONS
        # =================================================================
        mm_extra = [
            BusinessFunction("MM008", "Contract Management", "Create and manage purchasing contracts",
                BusinessProcess.PROCUREMENT, ["ME31K", "ME32K", "ME33K", "ME35K"],
                [{"object": "M_RAHM_WRK", "field": "ACTVT", "values": ["01", "02"]}]),
            BusinessFunction("MM009", "Purchasing Info Record", "Maintain purchasing info records",
                BusinessProcess.PROCUREMENT, ["ME11", "ME12", "ME13"],
                [{"object": "M_BEST_WRK", "field": "ACTVT", "values": ["01", "02"]}]),
            BusinessFunction("MM010", "Release Strategy Config", "Configure PO release strategies",
                BusinessProcess.PROCUREMENT, ["SPRO", "ME28"],
                [{"object": "S_TABU_DIS", "field": "ACTVT", "values": ["02"]}]),
        ]

        # =================================================================
        # ADDITIONAL BASIS/SECURITY FUNCTIONS
        # =================================================================
        ba_extra = [
            BusinessFunction("BA006", "Audit Log Config", "Configure security audit log",
                BusinessProcess.BASIS, ["SM19", "SM20", "SM21"],
                [{"object": "S_C_FUNCT", "field": "ACTVT", "values": ["01", "16"]}]),
            BusinessFunction("BA007", "Background Job Admin", "Schedule and manage background jobs",
                BusinessProcess.BASIS, ["SM36", "SM37", "SM62"],
                [{"object": "S_BTCH_ADM", "field": "BTCADMIN", "values": ["Y"]}]),
            BusinessFunction("BA008", "System Configuration", "Maintain system parameters and profile",
                BusinessProcess.BASIS, ["RZ10", "RZ11", "TU02"],
                [{"object": "S_RZL_ADM", "field": "ACTVT", "values": ["01"]}]),
            BusinessFunction("BA009", "Debug/Replace", "Debug programs with replace capability",
                BusinessProcess.BASIS, ["SE38", "SE80"],
                [{"object": "S_DEVELOP", "field": "ACTVT", "values": ["02"]},
                 {"object": "S_PROGRAM", "field": "P_ACTION", "values": ["DEBUG"]}]),
            BusinessFunction("BA010", "RFC Destination Admin", "Maintain RFC connections",
                BusinessProcess.BASIS, ["SM59"],
                [{"object": "S_RFC_ADM", "field": "ACTVT", "values": ["01", "02"]}]),
        ]

        # Store all functions
        all_func_lists = [
            fi_functions, mm_functions, sd_functions, hr_functions, basis_functions,
            tr_functions, aa_functions, wm_functions, qm_functions,
            pm_functions, ps_functions,
            fi_extra, mm_extra, ba_extra,
        ]
        for func_list in all_func_lists:
            for func in func_list:
                self.functions[func.function_id] = func

    def _init_rules(self):
        """Initialize SoD rules based on best practices"""

        sod_rules = [
            # =================================================================
            # FINANCE SOD RULES
            # =================================================================
            SoDRule(
                rule_id="SOD-FI-001",
                name="Vendor Master vs AP Payment",
                description="Maintain vendor master AND process payments",
                risk_level=RiskLevel.CRITICAL,
                business_process=BusinessProcess.FINANCE,
                function1=self.functions["FI001"],
                function2=self.functions["FI003"],
                risk_description="User can create fictitious vendors and pay them",
                business_impact="Fraudulent payments to fake vendors",
                recommendation="Separate vendor maintenance from payment processing",
                sox_relevant=True
            ),
            SoDRule(
                rule_id="SOD-FI-002",
                name="Vendor Master vs AP Invoice",
                description="Maintain vendor master AND enter AP invoices",
                risk_level=RiskLevel.HIGH,
                business_process=BusinessProcess.FINANCE,
                function1=self.functions["FI001"],
                function2=self.functions["FI002"],
                risk_description="User can create vendors and post invoices to them",
                business_impact="Fictitious invoice fraud",
                recommendation="Separate vendor maintenance from invoice entry",
                sox_relevant=True
            ),
            SoDRule(
                rule_id="SOD-FI-003",
                name="AP Invoice vs AP Payment",
                description="Enter AP invoices AND process payments",
                risk_level=RiskLevel.HIGH,
                business_process=BusinessProcess.FINANCE,
                function1=self.functions["FI002"],
                function2=self.functions["FI003"],
                risk_description="User can enter invoices and immediately pay them",
                business_impact="Unauthorized or duplicate payments",
                recommendation="Separate invoice entry from payment execution",
                sox_relevant=True
            ),
            SoDRule(
                rule_id="SOD-FI-004",
                name="Customer Master vs AR Cash Application",
                description="Maintain customer master AND apply cash receipts",
                risk_level=RiskLevel.HIGH,
                business_process=BusinessProcess.FINANCE,
                function1=self.functions["FI004"],
                function2=self.functions["FI006"],
                risk_description="User can modify customer and misapply payments",
                business_impact="Lapping or theft of customer payments",
                recommendation="Separate customer maintenance from cash application",
                sox_relevant=True
            ),
            SoDRule(
                rule_id="SOD-FI-005",
                name="GL Journal Entry vs Period Close",
                description="Post journal entries AND execute period close",
                risk_level=RiskLevel.MEDIUM,
                business_process=BusinessProcess.FINANCE,
                function1=self.functions["FI007"],
                function2=self.functions["FI008"],
                risk_description="User can post entries after period close",
                business_impact="Post-close adjustments without review",
                recommendation="Separate JE posting from period close activities",
                sox_relevant=True
            ),
            SoDRule(
                rule_id="SOD-FI-006",
                name="Bank Master vs AP Payment",
                description="Maintain bank master AND process payments",
                risk_level=RiskLevel.CRITICAL,
                business_process=BusinessProcess.FINANCE,
                function1=self.functions["FI009"],
                function2=self.functions["FI003"],
                risk_description="User can redirect payments to different bank accounts",
                business_impact="Payment fraud via bank account manipulation",
                recommendation="Separate bank maintenance from payment processing",
                sox_relevant=True
            ),
            SoDRule(
                rule_id="SOD-FI-007",
                name="Credit Memo vs AR Cash",
                description="Create credit memos AND apply cash receipts",
                risk_level=RiskLevel.HIGH,
                business_process=BusinessProcess.FINANCE,
                function1=self.functions["FI010"],
                function2=self.functions["FI006"],
                risk_description="User can issue credit and misapply payments",
                business_impact="Revenue loss and potential theft",
                recommendation="Separate credit memo processing from cash application"
            ),

            # =================================================================
            # PROCUREMENT SOD RULES (P2P)
            # =================================================================
            SoDRule(
                rule_id="SOD-MM-001",
                name="PR Creation vs PO Creation",
                description="Create purchase requisitions AND create purchase orders",
                risk_level=RiskLevel.MEDIUM,
                business_process=BusinessProcess.PROCUREMENT,
                function1=self.functions["MM001"],
                function2=self.functions["MM002"],
                risk_description="User can request and approve their own purchases",
                business_impact="Circumvention of procurement approval process",
                recommendation="Separate requisition from PO creation"
            ),
            SoDRule(
                rule_id="SOD-MM-002",
                name="PO Creation vs Goods Receipt",
                description="Create purchase orders AND post goods receipts",
                risk_level=RiskLevel.HIGH,
                business_process=BusinessProcess.PROCUREMENT,
                function1=self.functions["MM002"],
                function2=self.functions["MM003"],
                risk_description="User can order goods and confirm receipt without verification",
                business_impact="Fictitious goods receipts for non-delivered items",
                recommendation="Separate PO creation from goods receipt posting",
                sox_relevant=True
            ),
            SoDRule(
                rule_id="SOD-MM-003",
                name="PO Creation vs Invoice Verification",
                description="Create purchase orders AND verify invoices",
                risk_level=RiskLevel.HIGH,
                business_process=BusinessProcess.PROCUREMENT,
                function1=self.functions["MM002"],
                function2=self.functions["MM004"],
                risk_description="User can create POs and approve invoices",
                business_impact="Self-approval of purchases",
                recommendation="Separate PO creation from invoice verification",
                sox_relevant=True
            ),
            SoDRule(
                rule_id="SOD-MM-004",
                name="Goods Receipt vs Invoice Verification",
                description="Post goods receipts AND verify invoices",
                risk_level=RiskLevel.HIGH,
                business_process=BusinessProcess.PROCUREMENT,
                function1=self.functions["MM003"],
                function2=self.functions["MM004"],
                risk_description="User can confirm receipt and approve payment",
                business_impact="Payment for non-received goods",
                recommendation="Separate GR posting from invoice verification",
                sox_relevant=True
            ),
            SoDRule(
                rule_id="SOD-MM-005",
                name="Vendor Master vs PO Creation",
                description="Maintain vendor master AND create purchase orders",
                risk_level=RiskLevel.CRITICAL,
                business_process=BusinessProcess.PROCUREMENT,
                function1=self.functions["FI001"],  # Cross-process
                function2=self.functions["MM002"],
                risk_description="User can create vendors and place orders with them",
                business_impact="Fictitious vendor fraud",
                recommendation="Separate vendor maintenance from purchasing",
                sox_relevant=True
            ),
            SoDRule(
                rule_id="SOD-MM-006",
                name="Material Master vs Goods Receipt",
                description="Maintain material master AND post goods receipts",
                risk_level=RiskLevel.MEDIUM,
                business_process=BusinessProcess.PROCUREMENT,
                function1=self.functions["MM005"],
                function2=self.functions["MM003"],
                risk_description="User can create materials and receive inventory",
                business_impact="Fictitious inventory creation",
                recommendation="Separate material master from inventory movements"
            ),
            SoDRule(
                rule_id="SOD-MM-007",
                name="Source List vs PO Creation",
                description="Maintain source lists AND create purchase orders",
                risk_level=RiskLevel.MEDIUM,
                business_process=BusinessProcess.PROCUREMENT,
                function1=self.functions["MM007"],
                function2=self.functions["MM002"],
                risk_description="User can prefer vendors and place orders",
                business_impact="Vendor favoritism and kickbacks",
                recommendation="Separate source list maintenance from purchasing"
            ),

            # =================================================================
            # SALES SOD RULES (O2C)
            # =================================================================
            SoDRule(
                rule_id="SOD-SD-001",
                name="Sales Order vs Delivery",
                description="Create sales orders AND create deliveries",
                risk_level=RiskLevel.MEDIUM,
                business_process=BusinessProcess.SALES,
                function1=self.functions["SD001"],
                function2=self.functions["SD002"],
                risk_description="User can create orders and ship without verification",
                business_impact="Unauthorized shipments",
                recommendation="Separate order entry from delivery processing"
            ),
            SoDRule(
                rule_id="SOD-SD-002",
                name="Sales Order vs Billing",
                description="Create sales orders AND create billing documents",
                risk_level=RiskLevel.HIGH,
                business_process=BusinessProcess.SALES,
                function1=self.functions["SD001"],
                function2=self.functions["SD003"],
                risk_description="User can enter orders and create invoices",
                business_impact="Fictitious sales and revenue manipulation",
                recommendation="Separate order entry from billing",
                sox_relevant=True
            ),
            SoDRule(
                rule_id="SOD-SD-003",
                name="Pricing vs Sales Order",
                description="Maintain pricing AND create sales orders",
                risk_level=RiskLevel.HIGH,
                business_process=BusinessProcess.SALES,
                function1=self.functions["SD004"],
                function2=self.functions["SD001"],
                risk_description="User can set prices and create orders at those prices",
                business_impact="Unauthorized discounts, revenue loss",
                recommendation="Separate pricing maintenance from order entry",
                sox_relevant=True
            ),
            SoDRule(
                rule_id="SOD-SD-004",
                name="Customer Master vs Sales Order",
                description="Maintain customer master AND create sales orders",
                risk_level=RiskLevel.MEDIUM,
                business_process=BusinessProcess.SALES,
                function1=self.functions["FI004"],  # Cross-process
                function2=self.functions["SD001"],
                risk_description="User can create customers and sell to them",
                business_impact="Fictitious customer fraud",
                recommendation="Separate customer maintenance from sales"
            ),
            SoDRule(
                rule_id="SOD-SD-005",
                name="Credit Management vs Sales Order",
                description="Manage credit limits AND create sales orders",
                risk_level=RiskLevel.HIGH,
                business_process=BusinessProcess.SALES,
                function1=self.functions["SD005"],
                function2=self.functions["SD001"],
                risk_description="User can release credit blocks on their own orders",
                business_impact="Shipments to credit-risk customers",
                recommendation="Separate credit management from order entry",
                sox_relevant=True
            ),
            SoDRule(
                rule_id="SOD-SD-006",
                name="Returns vs AR Cash Application",
                description="Process returns AND apply cash receipts",
                risk_level=RiskLevel.HIGH,
                business_process=BusinessProcess.SALES,
                function1=self.functions["SD006"],
                function2=self.functions["FI006"],  # Cross-process
                risk_description="User can process returns and manipulate payments",
                business_impact="Return fraud, revenue theft",
                recommendation="Separate returns from cash application"
            ),

            # =================================================================
            # HR SOD RULES
            # =================================================================
            SoDRule(
                rule_id="SOD-HR-001",
                name="Personnel Master vs Payroll",
                description="Maintain employee data AND process payroll",
                risk_level=RiskLevel.CRITICAL,
                business_process=BusinessProcess.HR,
                function1=self.functions["HR001"],
                function2=self.functions["HR002"],
                risk_description="User can add employees and pay them",
                business_impact="Ghost employee fraud",
                recommendation="Separate HR master data from payroll processing",
                gdpr_relevant=True,
                sox_relevant=True
            ),
            SoDRule(
                rule_id="SOD-HR-002",
                name="Bank Data vs Payroll",
                description="Maintain employee bank details AND process payroll",
                risk_level=RiskLevel.CRITICAL,
                business_process=BusinessProcess.HR,
                function1=self.functions["HR005"],
                function2=self.functions["HR002"],
                risk_description="User can redirect payroll to different accounts",
                business_impact="Payroll fraud via bank manipulation",
                recommendation="Separate bank data maintenance from payroll",
                gdpr_relevant=True,
                sox_relevant=True
            ),
            SoDRule(
                rule_id="SOD-HR-003",
                name="Time Management vs Payroll",
                description="Maintain time records AND process payroll",
                risk_level=RiskLevel.HIGH,
                business_process=BusinessProcess.HR,
                function1=self.functions["HR003"],
                function2=self.functions["HR002"],
                risk_description="User can inflate hours and process payment",
                business_impact="Time fraud",
                recommendation="Separate time entry from payroll processing"
            ),
            SoDRule(
                rule_id="SOD-HR-004",
                name="Org Structure vs Personnel Master",
                description="Maintain org structure AND employee master data",
                risk_level=RiskLevel.MEDIUM,
                business_process=BusinessProcess.HR,
                function1=self.functions["HR004"],
                function2=self.functions["HR001"],
                risk_description="User can manipulate reporting structures",
                business_impact="Unauthorized org changes affecting approvals",
                recommendation="Separate org maintenance from personnel administration"
            ),

            # =================================================================
            # BASIS/SECURITY SOD RULES
            # =================================================================
            SoDRule(
                rule_id="SOD-BA-001",
                name="User Admin vs Role Admin",
                description="Administer users AND administer roles",
                risk_level=RiskLevel.CRITICAL,
                business_process=BusinessProcess.BASIS,
                function1=self.functions["BA001"],
                function2=self.functions["BA002"],
                risk_description="User can create users and assign powerful roles",
                business_impact="Complete security bypass",
                recommendation="Separate user administration from role administration"
            ),
            SoDRule(
                rule_id="SOD-BA-002",
                name="User Admin vs Table Maintenance",
                description="Administer users AND maintain tables directly",
                risk_level=RiskLevel.CRITICAL,
                business_process=BusinessProcess.BASIS,
                function1=self.functions["BA001"],
                function2=self.functions["BA003"],
                risk_description="User can create accounts and manipulate data directly",
                business_impact="Complete system compromise",
                recommendation="Strictly limit table maintenance access"
            ),
            SoDRule(
                rule_id="SOD-BA-003",
                name="Role Admin vs Transport Management",
                description="Administer roles AND manage transports",
                risk_level=RiskLevel.HIGH,
                business_process=BusinessProcess.BASIS,
                function1=self.functions["BA002"],
                function2=self.functions["BA005"],
                risk_description="User can create roles and transport to production",
                business_impact="Unauthorized access escalation",
                recommendation="Separate role development from transport release"
            ),
            SoDRule(
                rule_id="SOD-BA-004",
                name="Program Execution vs Table Maintenance",
                description="Execute programs AND maintain tables",
                risk_level=RiskLevel.HIGH,
                business_process=BusinessProcess.BASIS,
                function1=self.functions["BA004"],
                function2=self.functions["BA003"],
                risk_description="User can run programs to manipulate data",
                business_impact="Data integrity compromise",
                recommendation="Limit direct data access capabilities"
            ),
        ]

        # =================================================================
        # EXPANDED FINANCE RULES
        # =================================================================
        sod_rules.extend([
            SoDRule("SOD-FI-008", "Vendor Master vs Credit Memo", "Maintain vendor AND create credit memos",
                RiskLevel.HIGH, BusinessProcess.FINANCE, self.functions["FI001"], self.functions["FI010"],
                "Can create vendor and issue credit memos", "Fictitious credit fraud",
                "Separate vendor maintenance from credit memo processing", sox_relevant=True),
            SoDRule("SOD-FI-009", "GL Journal Entry vs Bank Master", "Post JE AND maintain bank data",
                RiskLevel.HIGH, BusinessProcess.FINANCE, self.functions["FI007"], self.functions["FI009"],
                "Can post entries to manipulated bank accounts", "Misappropriation of funds",
                "Separate journal entry from bank maintenance", sox_relevant=True),
            SoDRule("SOD-FI-010", "AP Invoice vs Bank Master", "Enter invoices AND maintain bank data",
                RiskLevel.CRITICAL, BusinessProcess.FINANCE, self.functions["FI002"], self.functions["FI009"],
                "Can redirect invoice payments", "Payment redirection fraud",
                "Separate invoice entry from bank maintenance", sox_relevant=True),
            SoDRule("SOD-FI-011", "Vendor Master vs GL Journal", "Maintain vendor AND post journal entries",
                RiskLevel.HIGH, BusinessProcess.FINANCE, self.functions["FI001"], self.functions["FI007"],
                "Can create vendor and post offsetting entries", "Concealment of fraudulent vendor payments",
                "Separate vendor master from GL posting", sox_relevant=True),
            SoDRule("SOD-FI-012", "Customer Master vs Billing", "Maintain customer AND create billing docs",
                RiskLevel.HIGH, BusinessProcess.FINANCE, self.functions["FI004"], self.functions["SD003"],
                "Can create customer and bill them", "Revenue manipulation",
                "Separate customer maintenance from billing", sox_relevant=True),
            SoDRule("SOD-FI-013", "Cost Center vs GL Journal", "Maintain cost centers AND post journal entries",
                RiskLevel.MEDIUM, BusinessProcess.FINANCE, self.functions["FI011"], self.functions["FI007"],
                "Can create cost centers and post charges", "Misallocation of expenses",
                "Separate cost center maintenance from JE posting"),
            SoDRule("SOD-FI-014", "Profit Center vs Financial Report", "Maintain profit centers AND run reports",
                RiskLevel.MEDIUM, BusinessProcess.FINANCE, self.functions["FI013"], self.functions["FI014"],
                "Can manipulate reporting structure", "Misleading financial reports",
                "Separate profit center config from financial reporting"),
            SoDRule("SOD-FI-015", "Tax Config vs AP Invoice", "Maintain tax codes AND enter invoices",
                RiskLevel.HIGH, BusinessProcess.FINANCE, self.functions["FI015"], self.functions["FI002"],
                "Can manipulate tax calculations on invoices", "Tax evasion or overstatement",
                "Separate tax configuration from invoice processing", sox_relevant=True),
            SoDRule("SOD-FI-016", "Tolerance Group vs AP Payment", "Maintain tolerances AND process payments",
                RiskLevel.HIGH, BusinessProcess.FINANCE, self.functions["FI016"], self.functions["FI003"],
                "Can raise tolerance to approve large payments", "Bypass of payment approval thresholds",
                "Separate tolerance config from payment processing", sox_relevant=True),
            SoDRule("SOD-FI-017", "Internal Order vs GL Journal", "Maintain internal orders AND post JE",
                RiskLevel.MEDIUM, BusinessProcess.FINANCE, self.functions["FI012"], self.functions["FI007"],
                "Can create orders and charge expenses to them", "Hidden cost accumulation",
                "Separate internal order maintenance from posting"),
            SoDRule("SOD-FI-018", "Period Close vs Financial Report", "Execute period close AND run reports",
                RiskLevel.MEDIUM, BusinessProcess.FINANCE, self.functions["FI008"], self.functions["FI014"],
                "Can close period and generate final reports without review", "Unreviewed financial statements",
                "Require independent review of close and reports", sox_relevant=True),
            SoDRule("SOD-FI-019", "Credit Memo vs Customer Master", "Create credit memos AND maintain customers",
                RiskLevel.HIGH, BusinessProcess.FINANCE, self.functions["FI010"], self.functions["FI004"],
                "Can create customer and issue credits", "Revenue loss via fictitious credits",
                "Separate credit memo from customer maintenance", sox_relevant=True),
            SoDRule("SOD-FI-020", "Bank Master vs Credit Memo", "Maintain bank data AND create credit memos",
                RiskLevel.HIGH, BusinessProcess.FINANCE, self.functions["FI009"], self.functions["FI010"],
                "Can redirect credit refunds via bank changes", "Credit refund fraud",
                "Separate bank maintenance from credit processing", sox_relevant=True),
        ])

        # =================================================================
        # EXPANDED PROCUREMENT RULES
        # =================================================================
        sod_rules.extend([
            SoDRule("SOD-MM-008", "PR Creation vs Goods Receipt", "Create requisitions AND post GR",
                RiskLevel.HIGH, BusinessProcess.PROCUREMENT, self.functions["MM001"], self.functions["MM003"],
                "Can request and confirm receipt without PO", "Circumvention of purchasing process",
                "Ensure PR-to-PO-to-GR separation", sox_relevant=True),
            SoDRule("SOD-MM-009", "PR Creation vs Invoice Verification", "Create PR AND verify invoices",
                RiskLevel.MEDIUM, BusinessProcess.PROCUREMENT, self.functions["MM001"], self.functions["MM004"],
                "Can request and approve payment", "Self-approval of procurement",
                "Separate requisition from invoice verification"),
            SoDRule("SOD-MM-010", "Contract Mgmt vs PO Creation", "Manage contracts AND create POs",
                RiskLevel.MEDIUM, BusinessProcess.PROCUREMENT, self.functions["MM008"], self.functions["MM002"],
                "Can set contract terms and create call-offs", "Favorable contract exploitation",
                "Separate contract management from PO creation"),
            SoDRule("SOD-MM-011", "Contract Mgmt vs Invoice Verification", "Manage contracts AND verify invoices",
                RiskLevel.HIGH, BusinessProcess.PROCUREMENT, self.functions["MM008"], self.functions["MM004"],
                "Can set contract prices and approve invoices", "Price manipulation in contracts",
                "Separate contract management from invoice processing", sox_relevant=True),
            SoDRule("SOD-MM-012", "Info Record vs PO Creation", "Maintain info records AND create POs",
                RiskLevel.MEDIUM, BusinessProcess.PROCUREMENT, self.functions["MM009"], self.functions["MM002"],
                "Can set purchasing prices and place orders", "Price manipulation",
                "Separate info record maintenance from purchasing"),
            SoDRule("SOD-MM-013", "Release Strategy vs PO Creation", "Configure release AND create POs",
                RiskLevel.CRITICAL, BusinessProcess.PROCUREMENT, self.functions["MM010"], self.functions["MM002"],
                "Can change release requirements and approve own POs", "Complete bypass of approval controls",
                "Separate release strategy config from purchasing", sox_relevant=True),
            SoDRule("SOD-MM-014", "Vendor Master vs Goods Receipt", "Maintain vendor AND post GR",
                RiskLevel.HIGH, BusinessProcess.PROCUREMENT, self.functions["FI001"], self.functions["MM003"],
                "Can create vendor and confirm delivery", "Fictitious vendor and goods receipt",
                "Separate vendor maintenance from warehouse", sox_relevant=True),
            SoDRule("SOD-MM-015", "Vendor Master vs Invoice Verification", "Maintain vendor AND verify invoices",
                RiskLevel.CRITICAL, BusinessProcess.PROCUREMENT, self.functions["FI001"], self.functions["MM004"],
                "Can create vendor and approve their invoices", "Fictitious vendor invoice fraud",
                "Separate vendor maintenance from invoice verification", sox_relevant=True),
            SoDRule("SOD-MM-016", "Material Master vs PO Creation", "Maintain materials AND create POs",
                RiskLevel.MEDIUM, BusinessProcess.PROCUREMENT, self.functions["MM005"], self.functions["MM002"],
                "Can create material and purchase it", "Unauthorized procurement",
                "Separate material master from purchasing"),
            SoDRule("SOD-MM-017", "Material Master vs Invoice Verification", "Maintain materials AND verify invoices",
                RiskLevel.MEDIUM, BusinessProcess.PROCUREMENT, self.functions["MM005"], self.functions["MM004"],
                "Can manipulate material prices and approve invoices", "Price variance manipulation",
                "Separate material master from invoice processing"),
            SoDRule("SOD-MM-018", "Vendor Evaluation vs PO Creation", "Evaluate vendors AND create POs",
                RiskLevel.MEDIUM, BusinessProcess.PROCUREMENT, self.functions["MM006"], self.functions["MM002"],
                "Can score vendors favorably and award contracts", "Vendor favoritism",
                "Separate vendor evaluation from purchasing"),
            SoDRule("SOD-MM-019", "Source List vs Vendor Master", "Maintain source lists AND vendor master",
                RiskLevel.HIGH, BusinessProcess.PROCUREMENT, self.functions["MM007"], self.functions["FI001"],
                "Can create preferred vendor and lock out competition", "Anti-competitive procurement",
                "Separate source list from vendor maintenance"),
            SoDRule("SOD-MM-020", "PO Creation vs AP Payment", "Create POs AND process payments",
                RiskLevel.CRITICAL, BusinessProcess.PROCUREMENT, self.functions["MM002"], self.functions["FI003"],
                "Can create PO and pay without verification", "Complete P2P fraud cycle",
                "Separate purchasing from payment execution", sox_relevant=True),
        ])

        # =================================================================
        # EXPANDED SALES RULES (O2C)
        # =================================================================
        sod_rules.extend([
            SoDRule("SOD-SD-007", "Delivery vs Billing", "Process deliveries AND create billing",
                RiskLevel.MEDIUM, BusinessProcess.SALES, self.functions["SD002"], self.functions["SD003"],
                "Can ship and invoice without review", "Unauthorized billing",
                "Separate delivery from billing"),
            SoDRule("SOD-SD-008", "Pricing vs Billing", "Maintain pricing AND create billing",
                RiskLevel.HIGH, BusinessProcess.SALES, self.functions["SD004"], self.functions["SD003"],
                "Can set prices and generate invoices", "Revenue manipulation via pricing",
                "Separate pricing maintenance from billing", sox_relevant=True),
            SoDRule("SOD-SD-009", "Credit Mgmt vs Billing", "Manage credit AND create billing",
                RiskLevel.HIGH, BusinessProcess.SALES, self.functions["SD005"], self.functions["SD003"],
                "Can extend credit and generate invoices", "Bad debt exposure",
                "Separate credit management from billing"),
            SoDRule("SOD-SD-010", "Returns vs Billing", "Process returns AND create billing",
                RiskLevel.HIGH, BusinessProcess.SALES, self.functions["SD006"], self.functions["SD003"],
                "Can process return credits and new invoices", "Return-rebilling fraud",
                "Separate returns from billing"),
            SoDRule("SOD-SD-011", "Sales Order vs Credit Mgmt", "Create orders AND manage credit",
                RiskLevel.HIGH, BusinessProcess.SALES, self.functions["SD001"], self.functions["SD005"],
                "Can release own credit blocks", "Ship to blocked customers",
                "Separate order entry from credit management", sox_relevant=True),
            SoDRule("SOD-SD-012", "Pricing vs Credit Mgmt", "Maintain pricing AND manage credit",
                RiskLevel.MEDIUM, BusinessProcess.SALES, self.functions["SD004"], self.functions["SD005"],
                "Can inflate prices to stay within credit limit", "Credit limit circumvention",
                "Separate pricing from credit management"),
            SoDRule("SOD-SD-013", "Customer Master vs Billing", "Maintain customer AND create billing",
                RiskLevel.HIGH, BusinessProcess.SALES, self.functions["FI004"], self.functions["SD003"],
                "Can create customer and bill them", "Fictitious revenue",
                "Separate customer maintenance from billing", sox_relevant=True),
            SoDRule("SOD-SD-014", "Customer Master vs Delivery", "Maintain customer AND process deliveries",
                RiskLevel.MEDIUM, BusinessProcess.SALES, self.functions["FI004"], self.functions["SD002"],
                "Can create ship-to addresses and deliver", "Unauthorized shipment diversion",
                "Separate customer maintenance from delivery"),
            SoDRule("SOD-SD-015", "Returns vs Customer Master", "Process returns AND maintain customer",
                RiskLevel.MEDIUM, BusinessProcess.SALES, self.functions["SD006"], self.functions["FI004"],
                "Can process returns for fictitious customers", "Return fraud",
                "Separate returns from customer maintenance"),
        ])

        # =================================================================
        # EXPANDED HR RULES
        # =================================================================
        sod_rules.extend([
            SoDRule("SOD-HR-005", "Personnel Master vs Bank Data", "Maintain employee AND bank data",
                RiskLevel.CRITICAL, BusinessProcess.HR, self.functions["HR001"], self.functions["HR005"],
                "Can create employee and set bank details", "Ghost employee payroll fraud",
                "Separate personnel admin from bank data", gdpr_relevant=True, sox_relevant=True),
            SoDRule("SOD-HR-006", "Time Management vs Personnel Master", "Maintain time AND employee data",
                RiskLevel.MEDIUM, BusinessProcess.HR, self.functions["HR003"], self.functions["HR001"],
                "Can create employee and record time", "Fictitious time and attendance",
                "Separate time entry from personnel admin"),
            SoDRule("SOD-HR-007", "Org Structure vs Payroll", "Maintain org AND process payroll",
                RiskLevel.HIGH, BusinessProcess.HR, self.functions["HR004"], self.functions["HR002"],
                "Can change reporting lines to bypass approval", "Unauthorized payroll changes",
                "Separate org maintenance from payroll"),
            SoDRule("SOD-HR-008", "Personnel Master vs AP Payment", "Maintain employees AND process payments",
                RiskLevel.HIGH, BusinessProcess.HR, self.functions["HR001"], self.functions["FI003"],
                "Can create employee-vendor and pay them", "Employee-vendor collusion",
                "Separate HR from finance payments", sox_relevant=True),
            SoDRule("SOD-HR-009", "Bank Data vs AP Payment", "Maintain HR bank data AND process payments",
                RiskLevel.CRITICAL, BusinessProcess.HR, self.functions["HR005"], self.functions["FI003"],
                "Can redirect payments via bank changes", "Payment redirection fraud",
                "Separate HR bank data from AP payments", gdpr_relevant=True, sox_relevant=True),
            SoDRule("SOD-HR-010", "Personnel Master vs User Admin", "Maintain employees AND create users",
                RiskLevel.HIGH, BusinessProcess.HR, self.functions["HR001"], self.functions["BA001"],
                "Can create employee and system user simultaneously", "Unauthorized system access",
                "Separate HR from IT user provisioning"),
        ])

        # =================================================================
        # EXPANDED BASIS/SECURITY RULES
        # =================================================================
        sod_rules.extend([
            SoDRule("SOD-BA-005", "User Admin vs Transport", "Administer users AND manage transports",
                RiskLevel.CRITICAL, BusinessProcess.BASIS, self.functions["BA001"], self.functions["BA005"],
                "Can create users and transport changes to production", "Unauthorized production access",
                "Separate user admin from transport management"),
            SoDRule("SOD-BA-006", "Role Admin vs Table Maint", "Administer roles AND maintain tables",
                RiskLevel.CRITICAL, BusinessProcess.BASIS, self.functions["BA002"], self.functions["BA003"],
                "Can modify roles and directly change auth tables", "Complete security bypass",
                "Separate role admin from table maintenance"),
            SoDRule("SOD-BA-007", "User Admin vs Audit Log", "Administer users AND configure audit log",
                RiskLevel.CRITICAL, BusinessProcess.BASIS, self.functions["BA001"], self.functions["BA006"],
                "Can create users and disable their audit trail", "Forensic evidence tampering",
                "Separate user admin from audit log configuration"),
            SoDRule("SOD-BA-008", "Role Admin vs Audit Log", "Administer roles AND configure audit log",
                RiskLevel.HIGH, BusinessProcess.BASIS, self.functions["BA002"], self.functions["BA006"],
                "Can assign roles and suppress audit", "Undetectable privilege escalation",
                "Separate role admin from audit configuration"),
            SoDRule("SOD-BA-009", "User Admin vs Background Jobs", "Administer users AND manage batch jobs",
                RiskLevel.HIGH, BusinessProcess.BASIS, self.functions["BA001"], self.functions["BA007"],
                "Can create users and schedule privileged jobs", "Backdoor job execution",
                "Separate user admin from job scheduling"),
            SoDRule("SOD-BA-010", "Table Maint vs Transport", "Maintain tables AND manage transports",
                RiskLevel.CRITICAL, BusinessProcess.BASIS, self.functions["BA003"], self.functions["BA005"],
                "Can modify data and transport changes", "Uncontrolled data modifications in production",
                "Separate table maintenance from transport management"),
            SoDRule("SOD-BA-011", "Debug/Replace vs Transport", "Debug with replace AND manage transports",
                RiskLevel.CRITICAL, BusinessProcess.BASIS, self.functions["BA009"], self.functions["BA005"],
                "Can modify code in debug and transport", "Unauthorized code changes in production",
                "Separate development from transport management"),
            SoDRule("SOD-BA-012", "System Config vs User Admin", "Configure system AND administer users",
                RiskLevel.HIGH, BusinessProcess.BASIS, self.functions["BA008"], self.functions["BA001"],
                "Can change system params and create privileged users", "System-level compromise",
                "Separate system config from user admin"),
            SoDRule("SOD-BA-013", "RFC Admin vs User Admin", "Manage RFC AND administer users",
                RiskLevel.HIGH, BusinessProcess.BASIS, self.functions["BA010"], self.functions["BA001"],
                "Can create RFC destinations and users for remote access", "Unauthorized remote access",
                "Separate RFC admin from user admin"),
            SoDRule("SOD-BA-014", "Program Execution vs Transport", "Execute programs AND manage transports",
                RiskLevel.HIGH, BusinessProcess.BASIS, self.functions["BA004"], self.functions["BA005"],
                "Can run programs and transport results", "Unauthorized program execution in production",
                "Separate program execution from transport management"),
            SoDRule("SOD-BA-015", "Debug/Replace vs Table Maint", "Debug with replace AND maintain tables",
                RiskLevel.CRITICAL, BusinessProcess.BASIS, self.functions["BA009"], self.functions["BA003"],
                "Can modify code and data simultaneously", "Complete data integrity compromise",
                "Never combine debug replace with table maintenance"),
            SoDRule("SOD-BA-016", "Background Jobs vs Table Maint", "Manage jobs AND maintain tables",
                RiskLevel.HIGH, BusinessProcess.BASIS, self.functions["BA007"], self.functions["BA003"],
                "Can schedule jobs that modify tables directly", "Automated data manipulation",
                "Separate job scheduling from table maintenance"),
        ])

        # =================================================================
        # TREASURY SOD RULES
        # =================================================================
        sod_rules.extend([
            SoDRule("SOD-TR-001", "Treasury Payment vs Bank Account", "Execute payments AND manage bank accounts",
                RiskLevel.CRITICAL, BusinessProcess.TREASURY, self.functions["TR001"], self.functions["TR002"],
                "Can redirect treasury payments via bank changes", "Treasury payment fraud",
                "Separate payment execution from bank account management", sox_relevant=True),
            SoDRule("SOD-TR-002", "Investment Mgmt vs Treasury Payment", "Manage investments AND execute payments",
                RiskLevel.CRITICAL, BusinessProcess.TREASURY, self.functions["TR003"], self.functions["TR001"],
                "Can create investment positions and divert funds", "Investment fraud",
                "Separate investment management from payment execution", sox_relevant=True),
            SoDRule("SOD-TR-003", "Cash Position vs Treasury Payment", "Manage cash AND execute payments",
                RiskLevel.HIGH, BusinessProcess.TREASURY, self.functions["TR004"], self.functions["TR001"],
                "Can manipulate cash position and process payments", "Cash management fraud",
                "Separate cash monitoring from payment execution", sox_relevant=True),
            SoDRule("SOD-TR-004", "Bank Account vs Vendor Master", "Manage bank accounts AND vendor master",
                RiskLevel.CRITICAL, BusinessProcess.TREASURY, self.functions["TR002"], self.functions["FI001"],
                "Can create vendor bank details and modify house bank", "Payment routing fraud",
                "Separate bank account management from vendor maintenance", sox_relevant=True),
            SoDRule("SOD-TR-005", "Investment Mgmt vs Bank Account", "Manage investments AND bank accounts",
                RiskLevel.HIGH, BusinessProcess.TREASURY, self.functions["TR003"], self.functions["TR002"],
                "Can create investments and link to unauthorized banks", "Unauthorized investment placement",
                "Separate investment from bank account management", sox_relevant=True),
        ])

        # =================================================================
        # ASSET ACCOUNTING SOD RULES
        # =================================================================
        sod_rules.extend([
            SoDRule("SOD-AA-001", "Asset Master vs Acquisition", "Maintain assets AND post acquisitions",
                RiskLevel.HIGH, BusinessProcess.ASSET, self.functions["AA001"], self.functions["AA002"],
                "Can create fictitious assets and capitalize", "Asset overstatement",
                "Separate asset master from acquisition posting", sox_relevant=True),
            SoDRule("SOD-AA-002", "Asset Master vs Retirement", "Maintain assets AND process retirements",
                RiskLevel.HIGH, BusinessProcess.ASSET, self.functions["AA001"], self.functions["AA003"],
                "Can retire assets and manipulate records", "Asset theft concealment",
                "Separate asset master from retirement processing", sox_relevant=True),
            SoDRule("SOD-AA-003", "Asset Transfer vs Retirement", "Transfer assets AND retire assets",
                RiskLevel.MEDIUM, BusinessProcess.ASSET, self.functions["AA004"], self.functions["AA003"],
                "Can transfer and retire without oversight", "Asset misappropriation",
                "Separate asset transfers from retirements"),
            SoDRule("SOD-AA-004", "Depreciation vs Asset Master", "Run depreciation AND maintain assets",
                RiskLevel.MEDIUM, BusinessProcess.ASSET, self.functions["AA005"], self.functions["AA001"],
                "Can change useful life and run depreciation", "Depreciation manipulation",
                "Separate depreciation run from asset master maintenance", sox_relevant=True),
            SoDRule("SOD-AA-005", "Asset Acquisition vs AP Payment", "Post acquisitions AND process payments",
                RiskLevel.HIGH, BusinessProcess.ASSET, self.functions["AA002"], self.functions["FI003"],
                "Can capitalize and pay for fictitious assets", "Fictitious asset procurement",
                "Separate asset acquisition from payment", sox_relevant=True),
        ])

        # =================================================================
        # WAREHOUSE/INVENTORY SOD RULES
        # =================================================================
        sod_rules.extend([
            SoDRule("SOD-WM-001", "Inventory Adjustment vs Physical Inventory", "Adjust inventory AND count inventory",
                RiskLevel.HIGH, BusinessProcess.WAREHOUSE, self.functions["WM001"], self.functions["WM002"],
                "Can count and adjust without verification", "Inventory manipulation",
                "Separate counting from adjustment posting", sox_relevant=True),
            SoDRule("SOD-WM-002", "Inventory Adjustment vs Goods Receipt", "Adjust inventory AND post GR",
                RiskLevel.HIGH, BusinessProcess.WAREHOUSE, self.functions["WM001"], self.functions["MM003"],
                "Can receive goods and make adjustments", "Concealment of theft or shortages",
                "Separate inventory adjustments from goods receipt"),
            SoDRule("SOD-WM-003", "Stock Transfer vs Physical Inventory", "Transfer stock AND count inventory",
                RiskLevel.MEDIUM, BusinessProcess.WAREHOUSE, self.functions["WM003"], self.functions["WM002"],
                "Can transfer stock and manipulate counts", "Inter-location theft concealment",
                "Separate stock transfers from inventory counting"),
            SoDRule("SOD-WM-004", "Inventory Adjustment vs PO Creation", "Adjust inventory AND create POs",
                RiskLevel.HIGH, BusinessProcess.WAREHOUSE, self.functions["WM001"], self.functions["MM002"],
                "Can write off inventory and re-order", "Inventory write-off fraud",
                "Separate adjustments from purchasing"),
            SoDRule("SOD-WM-005", "Goods Receipt vs Physical Inventory", "Post GR AND count inventory",
                RiskLevel.MEDIUM, BusinessProcess.WAREHOUSE, self.functions["MM003"], self.functions["WM002"],
                "Can receive goods and manipulate counts", "Inventory discrepancy concealment",
                "Separate goods receipt from physical inventory"),
        ])

        # =================================================================
        # QUALITY MANAGEMENT SOD RULES
        # =================================================================
        sod_rules.extend([
            SoDRule("SOD-QM-001", "Quality Inspection vs Usage Decision", "Inspect AND make usage decision",
                RiskLevel.MEDIUM, BusinessProcess.QUALITY, self.functions["QM001"], self.functions["QM002"],
                "Can inspect and approve own inspection", "Quality control bypass",
                "Separate inspection from usage decision"),
            SoDRule("SOD-QM-002", "Quality Inspection vs Goods Receipt", "Inspect AND post goods receipt",
                RiskLevel.HIGH, BusinessProcess.QUALITY, self.functions["QM001"], self.functions["MM003"],
                "Can approve quality and confirm receipt", "Acceptance of substandard goods",
                "Separate quality inspection from GR posting"),
            SoDRule("SOD-QM-003", "Usage Decision vs Vendor Evaluation", "Make usage decisions AND evaluate vendors",
                RiskLevel.MEDIUM, BusinessProcess.QUALITY, self.functions["QM002"], self.functions["MM006"],
                "Can approve quality and rate vendor favorably", "Biased vendor evaluation",
                "Separate usage decisions from vendor evaluation"),
        ])

        # =================================================================
        # PLANT MAINTENANCE SOD RULES
        # =================================================================
        sod_rules.extend([
            SoDRule("SOD-PM-001", "Maintenance Order vs Service Entry", "Create MO AND accept services",
                RiskLevel.HIGH, BusinessProcess.PLANT_MAINT, self.functions["PM001"], self.functions["PM002"],
                "Can create work orders and accept own services", "Fictitious service acceptance",
                "Separate work order creation from service acceptance", sox_relevant=True),
            SoDRule("SOD-PM-002", "Maintenance Order vs PO Creation", "Create MO AND create POs",
                RiskLevel.MEDIUM, BusinessProcess.PLANT_MAINT, self.functions["PM001"], self.functions["MM002"],
                "Can create work and purchase without separation", "Self-procurement for maintenance",
                "Separate work order from procurement"),
            SoDRule("SOD-PM-003", "Service Entry vs Invoice Verification", "Accept services AND verify invoices",
                RiskLevel.HIGH, BusinessProcess.PLANT_MAINT, self.functions["PM002"], self.functions["MM004"],
                "Can accept services and approve payment", "Fictitious service billing",
                "Separate service acceptance from invoice verification", sox_relevant=True),
            SoDRule("SOD-PM-004", "Service Entry vs AP Payment", "Accept services AND process payments",
                RiskLevel.CRITICAL, BusinessProcess.PLANT_MAINT, self.functions["PM002"], self.functions["FI003"],
                "Can accept services and pay directly", "Service fraud",
                "Separate service entry from payment processing", sox_relevant=True),
        ])

        # =================================================================
        # PROJECT SYSTEM SOD RULES
        # =================================================================
        sod_rules.extend([
            SoDRule("SOD-PS-001", "Project Definition vs Project Budget", "Define projects AND set budgets",
                RiskLevel.HIGH, BusinessProcess.PROJECT, self.functions["PS001"], self.functions["PS002"],
                "Can create projects and fund them without approval", "Unauthorized project spending",
                "Separate project definition from budget allocation", sox_relevant=True),
            SoDRule("SOD-PS-002", "Project Budget vs PO Creation", "Set budgets AND create POs",
                RiskLevel.HIGH, BusinessProcess.PROJECT, self.functions["PS002"], self.functions["MM002"],
                "Can allocate budget and spend it", "Self-approval of project procurement",
                "Separate budget management from purchasing", sox_relevant=True),
            SoDRule("SOD-PS-003", "Project Definition vs PO Creation", "Define projects AND create POs",
                RiskLevel.MEDIUM, BusinessProcess.PROJECT, self.functions["PS001"], self.functions["MM002"],
                "Can create project and procure for it", "Uncontrolled project spending",
                "Separate project management from procurement"),
        ])

        # =================================================================
        # CROSS-PROCESS CRITICAL RULES
        # =================================================================
        sod_rules.extend([
            SoDRule("SOD-XP-001", "User Admin vs AP Payment", "Administer users AND process payments",
                RiskLevel.CRITICAL, BusinessProcess.GENERAL, self.functions["BA001"], self.functions["FI003"],
                "Can create user accounts and process payments", "Fraud via unauthorized accounts",
                "Never combine user admin with financial transactions", sox_relevant=True,
                is_cross_system=True),
            SoDRule("SOD-XP-002", "User Admin vs GL Journal", "Administer users AND post journal entries",
                RiskLevel.CRITICAL, BusinessProcess.GENERAL, self.functions["BA001"], self.functions["FI007"],
                "Can create users and post GL entries", "Complete financial fraud capability",
                "Separate user admin from financial posting", sox_relevant=True,
                is_cross_system=True),
            SoDRule("SOD-XP-003", "Table Maint vs AP Payment", "Maintain tables AND process payments",
                RiskLevel.CRITICAL, BusinessProcess.GENERAL, self.functions["BA003"], self.functions["FI003"],
                "Can modify payment tables and process payments", "Payment fraud via data manipulation",
                "Never combine table maintenance with payment processing", sox_relevant=True,
                is_cross_system=True),
            SoDRule("SOD-XP-004", "Role Admin vs AP Invoice", "Administer roles AND enter invoices",
                RiskLevel.HIGH, BusinessProcess.GENERAL, self.functions["BA002"], self.functions["FI002"],
                "Can assign invoice access and enter invoices", "Self-service privilege escalation",
                "Separate role admin from business transactions", is_cross_system=True),
            SoDRule("SOD-XP-005", "User Admin vs Vendor Master", "Administer users AND maintain vendors",
                RiskLevel.HIGH, BusinessProcess.GENERAL, self.functions["BA001"], self.functions["FI001"],
                "Can create user accounts for fictitious vendors", "Identity-vendor linkage fraud",
                "Separate user admin from vendor maintenance", is_cross_system=True),
            SoDRule("SOD-XP-006", "Table Maint vs HR Payroll", "Maintain tables AND process payroll",
                RiskLevel.CRITICAL, BusinessProcess.GENERAL, self.functions["BA003"], self.functions["HR002"],
                "Can modify payroll tables and run payroll", "Payroll data manipulation",
                "Never combine table maintenance with payroll", sox_relevant=True, gdpr_relevant=True,
                is_cross_system=True),
            SoDRule("SOD-XP-007", "Debug/Replace vs AP Payment", "Debug with replace AND process payments",
                RiskLevel.CRITICAL, BusinessProcess.GENERAL, self.functions["BA009"], self.functions["FI003"],
                "Can modify payment program logic in runtime", "Runtime payment manipulation",
                "Never combine debug/replace with financial transactions", sox_relevant=True,
                is_cross_system=True),
            SoDRule("SOD-XP-008", "Background Jobs vs AP Payment", "Schedule jobs AND process payments",
                RiskLevel.HIGH, BusinessProcess.GENERAL, self.functions["BA007"], self.functions["FI003"],
                "Can schedule automated payment runs", "Automated payment fraud",
                "Separate batch administration from payment processing", is_cross_system=True),
            SoDRule("SOD-XP-009", "RFC Admin vs AP Payment", "Manage RFC AND process payments",
                RiskLevel.HIGH, BusinessProcess.GENERAL, self.functions["BA010"], self.functions["FI003"],
                "Can create RFC destinations for remote payment execution", "Remote payment fraud",
                "Separate RFC admin from financial transactions", is_cross_system=True),
            SoDRule("SOD-XP-010", "Vendor Master vs Treasury Payment", "Maintain vendors AND execute treasury payments",
                RiskLevel.CRITICAL, BusinessProcess.GENERAL, self.functions["FI001"], self.functions["TR001"],
                "Can create vendor and execute wire transfers", "Wire transfer fraud",
                "Separate vendor maintenance from treasury operations", sox_relevant=True,
                is_cross_system=True),
            SoDRule("SOD-XP-011", "HR Personnel vs Vendor Master", "Maintain employees AND vendors",
                RiskLevel.HIGH, BusinessProcess.GENERAL, self.functions["HR001"], self.functions["FI001"],
                "Can create employee-vendor relationships", "Employee-vendor collusion",
                "Separate HR from vendor management", is_cross_system=True),
            SoDRule("SOD-XP-012", "Asset Master vs Vendor Master", "Maintain assets AND vendors",
                RiskLevel.MEDIUM, BusinessProcess.GENERAL, self.functions["AA001"], self.functions["FI001"],
                "Can link fictitious assets to fictitious vendors", "Asset-vendor fraud",
                "Separate asset management from vendor maintenance", is_cross_system=True),
            SoDRule("SOD-XP-013", "Inventory Adjust vs AP Payment", "Adjust inventory AND process payments",
                RiskLevel.HIGH, BusinessProcess.GENERAL, self.functions["WM001"], self.functions["FI003"],
                "Can write off inventory and process payment for same", "Inventory-payment fraud",
                "Separate inventory adjustments from payment processing", is_cross_system=True),
            SoDRule("SOD-XP-014", "User Admin vs Treasury Payment", "Administer users AND execute treasury payments",
                RiskLevel.CRITICAL, BusinessProcess.GENERAL, self.functions["BA001"], self.functions["TR001"],
                "Can create accounts and execute wire transfers", "Maximum fraud risk",
                "Never combine user admin with treasury", sox_relevant=True, is_cross_system=True),
            SoDRule("SOD-XP-015", "System Config vs AP Payment", "Configure system AND process payments",
                RiskLevel.CRITICAL, BusinessProcess.GENERAL, self.functions["BA008"], self.functions["FI003"],
                "Can change system behavior and process payments", "System-level payment fraud",
                "Separate system config from financial transactions", sox_relevant=True,
                is_cross_system=True),
        ])

        # Store all rules
        for rule in sod_rules:
            self.rules[rule.rule_id] = rule

    # =========================================================================
    # Query Methods
    # =========================================================================

    def get_all_rules(self, active_only: bool = True) -> List[SoDRule]:
        """Get all SoD rules"""
        rules = list(self.rules.values())
        if active_only:
            rules = [r for r in rules if r.is_active]
        return rules

    def get_rule(self, rule_id: str) -> Optional[SoDRule]:
        """Get a rule by ID"""
        return self.rules.get(rule_id)

    def get_rules_by_process(self, process: BusinessProcess) -> List[SoDRule]:
        """Get rules for a business process"""
        return [r for r in self.rules.values() if r.business_process == process and r.is_active]

    def get_rules_by_risk_level(self, level: RiskLevel) -> List[SoDRule]:
        """Get rules by risk level"""
        return [r for r in self.rules.values() if r.risk_level == level and r.is_active]

    def get_sox_relevant_rules(self) -> List[SoDRule]:
        """Get SOX-relevant rules"""
        return [r for r in self.rules.values() if r.sox_relevant and r.is_active]

    def get_gdpr_relevant_rules(self) -> List[SoDRule]:
        """Get GDPR-relevant rules"""
        return [r for r in self.rules.values() if r.gdpr_relevant and r.is_active]

    def get_function(self, function_id: str) -> Optional[BusinessFunction]:
        """Get a business function by ID"""
        return self.functions.get(function_id)

    def get_all_functions(self) -> List[BusinessFunction]:
        """Get all business functions"""
        return list(self.functions.values())

    def get_functions_by_process(self, process: BusinessProcess) -> List[BusinessFunction]:
        """Get functions for a business process"""
        return [f for f in self.functions.values() if f.business_process == process]

    # =========================================================================
    # Statistics
    # =========================================================================

    def get_statistics(self) -> Dict:
        """Get ruleset statistics"""
        rules = list(self.rules.values())
        return {
            "total_rules": len(rules),
            "active_rules": len([r for r in rules if r.is_active]),
            "total_functions": len(self.functions),
            "by_risk_level": {
                level.value: len([r for r in rules if r.risk_level == level])
                for level in RiskLevel
            },
            "by_process": {
                process.value: len([r for r in rules if r.business_process == process])
                for process in BusinessProcess
            },
            "sox_relevant": len([r for r in rules if r.sox_relevant]),
            "gdpr_relevant": len([r for r in rules if r.gdpr_relevant])
        }
