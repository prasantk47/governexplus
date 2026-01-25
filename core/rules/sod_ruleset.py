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

        # Store all functions
        for func_list in [fi_functions, mm_functions, sd_functions, hr_functions, basis_functions]:
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
