"""
Custom Transaction Analyzer
Analyzes custom SAP transactions (Z*/Y* prefix) to detect behavior,
risk profile, and SoD implications.
"""

import logging
import re
from datetime import datetime
from typing import Optional, List, Dict, Any

from sqlalchemy import func

from db.database import db_manager
from db.models.operations import CustomTcodeRecord

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Seed data — inserted into the DB on first access if the table is empty
# ---------------------------------------------------------------------------

_SEED_TCODES: List[Dict[str, Any]] = [
    {
        "tcode": "Z_VENDOR_PAY",
        "description": "Custom vendor payment processing",
        "program": "Z_VENDOR_PAY",
        "risk_level": "critical",
        "risk_score": 95,
        "auth_objects": ["F_BKPF_BUK", "F_BKPF_BLA", "F_KNA1_BED"],
        "behavior_patterns": {
            "behaviors": ["creates", "modifies", "posts_financial"],
            "module": "FI-AP",
            "tables_accessed": ["BKPF", "BSEG", "LFA1", "PAYR"],
            "function_modules": ["FI_DOCUMENT_PARK", "POSTING_INTERFACE_DOCUMENT"],
            "standard_equivalent": "F110",
            "business_functions": ["AP_PAYMENT_PROCESSING", "VENDOR_MANAGEMENT"],
            "sod_risks": [
                "Can create AND approve payment in single transaction",
                "Bypasses standard payment proposal workflow",
            ],
            "risk_reasons": [
                "Posts financial documents without standard dual-control",
                "Accesses payment run tables",
            ],
        },
    },
    {
        "tcode": "ZFI_JOURNAL",
        "description": "Custom journal entry posting",
        "program": "ZFI_JOURNAL",
        "risk_level": "high",
        "risk_score": 80,
        "auth_objects": ["F_BKPF_BUK", "F_BKPF_BLA", "F_BKPF_KOA"],
        "behavior_patterns": {
            "behaviors": ["creates", "posts_financial", "modifies"],
            "module": "FI-GL",
            "tables_accessed": ["BKPF", "BSEG", "SKA1"],
            "function_modules": ["BAPI_ACC_DOCUMENT_POST"],
            "standard_equivalent": "FB50",
            "business_functions": ["GL_JOURNAL_ENTRY", "FINANCIAL_POSTING"],
            "sod_risks": [
                "Can post to all account types",
                "Potential for fraudulent reclassification entries",
            ],
            "risk_reasons": [
                "Unrestricted journal entry posting",
                "No document type restriction",
            ],
        },
    },
    {
        "tcode": "ZMM_PO_CREATE",
        "description": "Custom purchase order creation with auto-approval",
        "program": "ZMM_PO_CREATE",
        "risk_level": "high",
        "risk_score": 80,
        "auth_objects": ["M_BEST_BSA", "M_BEST_EKG", "M_BEST_EKO"],
        "behavior_patterns": {
            "behaviors": ["creates", "modifies", "approves"],
            "module": "MM-PUR",
            "tables_accessed": ["EKKO", "EKPO", "EKET", "LFA1"],
            "function_modules": ["BAPI_PO_CREATE1", "ME_DIRECT_INPUT_EKKO"],
            "standard_equivalent": "ME21N",
            "business_functions": ["PO_CREATION", "PURCHASING_APPROVAL"],
            "sod_risks": [
                "Create and auto-approve PO in same transaction",
                "Bypasses release strategy",
            ],
            "risk_reasons": [
                "Auto-approval flag bypasses standard release strategy",
                "Can set tolerance limits above threshold",
            ],
        },
    },
    {
        "tcode": "ZHR_PAYROLL",
        "description": "Custom payroll execution and posting",
        "program": "ZHR_PAYROLL",
        "risk_level": "critical",
        "risk_score": 95,
        "auth_objects": ["P_ORGIN", "P_PERNR", "HR_PAYR"],
        "behavior_patterns": {
            "behaviors": ["executes", "posts_financial", "reads"],
            "module": "HR-PY",
            "tables_accessed": ["PA0008", "PC2B5", "WPBP", "RT"],
            "function_modules": ["PYXX_PROCESS_PAYROLL_RESULT"],
            "standard_equivalent": "PC00_M99_CALC",
            "business_functions": ["PAYROLL_EXECUTION", "HR_MASTER_DATA"],
            "sod_risks": [
                "Modify salary AND execute payroll",
                "Full access to employee compensation data",
            ],
            "risk_reasons": [
                "Executes payroll without standard double-verification",
                "Access to salary master data",
            ],
        },
    },
    {
        "tcode": "Z_BANK_TRANSFER",
        "description": "Direct bank transfer initiation",
        "program": "Z_BANK_TRANSFER",
        "risk_level": "critical",
        "risk_score": 95,
        "auth_objects": ["F_BKPF_BUK", "F_FEBA_BUK", "T_FEBA"],
        "behavior_patterns": {
            "behaviors": ["creates", "posts_financial", "executes"],
            "module": "FI-TR",
            "tables_accessed": ["FEBEP", "FEBKO", "BKPF"],
            "function_modules": ["BANK_TRANSFER_CREATE", "FI_DOCUMENT_PARK"],
            "standard_equivalent": "F-53",
            "business_functions": ["BANK_TRANSFER", "TREASURY_MANAGEMENT"],
            "sod_risks": [
                "Initiate and confirm bank transfer",
                "No segregation from vendor setup",
            ],
            "risk_reasons": [
                "Direct bank transfer with no approval gate",
                "Can initiate external transfers",
            ],
        },
    },
    {
        "tcode": "ZUSER_ADMIN",
        "description": "Custom user administration bypass tool",
        "program": "ZUSER_ADMIN",
        "risk_level": "critical",
        "risk_score": 95,
        "auth_objects": ["S_USR_ADM", "S_TCODE", "S_USER_GRP"],
        "behavior_patterns": {
            "behaviors": ["creates", "modifies", "deletes", "admin"],
            "module": "BC-SEC",
            "tables_accessed": ["USR02", "USR04", "AGR_USERS"],
            "function_modules": ["SUSR_USER_CHANGE_PASSWORD_RFC"],
            "standard_equivalent": "SU01",
            "business_functions": ["USER_ADMINISTRATION", "PROFILE_MANAGEMENT"],
            "sod_risks": [
                "Create users AND assign roles",
                "Full authorization administration",
            ],
            "risk_reasons": [
                "Batch user modification without logging",
                "Can assign any profile including SAP_ALL",
            ],
        },
    },
    {
        "tcode": "ZFI_AR_CLEAR",
        "description": "Custom AR clearing with customer credit override",
        "program": "ZFI_AR_CLEAR",
        "risk_level": "high",
        "risk_score": 80,
        "auth_objects": ["F_BKPF_BUK", "F_KNA1_BED", "F_BKPF_BLA"],
        "behavior_patterns": {
            "behaviors": ["modifies", "clears", "posts_financial"],
            "module": "FI-AR",
            "tables_accessed": ["BKPF", "BSEG", "KNA1", "KNKA"],
            "function_modules": ["FI_DOCUMENT_CHANGE"],
            "standard_equivalent": "F-32",
            "business_functions": ["AR_CLEARING", "CUSTOMER_CREDIT"],
            "sod_risks": [
                "Extend credit AND clear open items",
                "Potential for fictitious customer payments",
            ],
            "risk_reasons": [
                "Override customer credit limits",
                "Clear AR items without standard checks",
            ],
        },
    },
    {
        "tcode": "ZMM_GR_POST",
        "description": "Goods receipt with price override",
        "program": "ZMM_GR_POST",
        "risk_level": "medium",
        "risk_score": 50,
        "auth_objects": ["M_MSEG_BWA", "M_MSEG_WMB", "M_MSEG_WOB"],
        "behavior_patterns": {
            "behaviors": ["creates", "posts_financial", "modifies"],
            "module": "MM-IM",
            "tables_accessed": ["MSEG", "MKPF", "EKKO"],
            "function_modules": ["BAPI_GOODSMVT_CREATE"],
            "standard_equivalent": "MIGO",
            "business_functions": ["GOODS_RECEIPT", "INVENTORY_MANAGEMENT"],
            "sod_risks": ["Create GR AND modify PO price"],
            "risk_reasons": ["Allows price deviation beyond tolerance"],
        },
    },
    {
        "tcode": "ZSD_BILL_CREAT",
        "description": "Custom billing document creation",
        "program": "ZSD_BILL_CREAT",
        "risk_level": "medium",
        "risk_score": 50,
        "auth_objects": ["V_VBRK_VKO", "V_VBRK_FKA"],
        "behavior_patterns": {
            "behaviors": ["creates", "posts_financial"],
            "module": "SD-BIL",
            "tables_accessed": ["VBRK", "VBRP", "VBAK"],
            "function_modules": ["BAPI_BILLINGDOC_CREATEMULTIPLE"],
            "standard_equivalent": "VF01",
            "business_functions": ["BILLING", "REVENUE_RECOGNITION"],
            "sod_risks": ["Create sales order AND bill without delivery"],
            "risk_reasons": ["Create billing without delivery verification"],
        },
    },
    {
        "tcode": "ZCO_BUDGET",
        "description": "Budget allocation and override",
        "program": "ZCO_BUDGET",
        "risk_level": "high",
        "risk_score": 80,
        "auth_objects": ["K_ORDER", "K_VRGNG"],
        "behavior_patterns": {
            "behaviors": ["modifies", "creates"],
            "module": "CO-OM",
            "tables_accessed": ["BPGE", "BPJA", "AUFK"],
            "function_modules": ["BAPI_COSTCENTER_CHANGE"],
            "standard_equivalent": "KO22",
            "business_functions": ["BUDGET_MANAGEMENT", "COST_CENTER_ACCOUNTING"],
            "sod_risks": ["Allocate budget AND execute spending"],
            "risk_reasons": [
                "Can set budget above approved amounts",
                "Override budget availability check",
            ],
        },
    },
    {
        "tcode": "ZBC_ROLE_ASSIGN",
        "description": "Batch role assignment tool",
        "program": "ZBC_ROLE_ASSIGN",
        "risk_level": "critical",
        "risk_score": 95,
        "auth_objects": ["S_USR_ADM", "S_USER_GRP", "S_TCODE"],
        "behavior_patterns": {
            "behaviors": ["creates", "modifies", "admin"],
            "module": "BC-SEC",
            "tables_accessed": ["AGR_USERS", "AGR_AGRS", "USR04"],
            "function_modules": ["SUSR_ROLE_ASSIGN_TO_USER"],
            "standard_equivalent": "SU01 / PFCG",
            "business_functions": ["ROLE_ADMINISTRATION", "USER_ADMINISTRATION"],
            "sod_risks": [
                "Assign roles AND create users",
                "Full bypass of access governance",
            ],
            "risk_reasons": [
                "Batch role assignment bypasses SoD controls",
                "No approval workflow integration",
            ],
        },
    },
    {
        "tcode": "ZFI_ACCRUAL",
        "description": "Manual accrual posting",
        "program": "ZFI_ACCRUAL",
        "risk_level": "medium",
        "risk_score": 50,
        "auth_objects": ["F_BKPF_BUK", "F_BKPF_BLA"],
        "behavior_patterns": {
            "behaviors": ["creates", "posts_financial"],
            "module": "FI-GL",
            "tables_accessed": ["BKPF", "BSEG"],
            "function_modules": ["BAPI_ACC_DOCUMENT_POST"],
            "standard_equivalent": "FBS1",
            "business_functions": ["ACCRUAL_MANAGEMENT", "GL_JOURNAL_ENTRY"],
            "sod_risks": ["Post accruals AND reverse entries"],
            "risk_reasons": ["Unrestricted period-end accrual posting"],
        },
    },
    {
        "tcode": "ZHR_MASTER",
        "description": "HR master data bulk update",
        "program": "ZHR_MASTER",
        "risk_level": "high",
        "risk_score": 80,
        "auth_objects": ["P_ORGIN", "P_PERNR", "P_ABAP"],
        "behavior_patterns": {
            "behaviors": ["modifies", "reads"],
            "module": "HR-PA",
            "tables_accessed": ["PA0001", "PA0002", "PA0008", "PA0009"],
            "function_modules": ["HR_INFOTYPE_OPERATION"],
            "standard_equivalent": "PA30",
            "business_functions": ["HR_MASTER_DATA", "PAYROLL_ADMINISTRATION"],
            "sod_risks": ["Modify employee bank details AND run payroll"],
            "risk_reasons": [
                "Bulk modification of sensitive HR infotypes",
                "Includes bank account infotype PA0009",
            ],
        },
    },
    {
        "tcode": "ZMM_VENDOR_NEW",
        "description": "Vendor master creation with payment terms",
        "program": "ZMM_VENDOR_NEW",
        "risk_level": "high",
        "risk_score": 80,
        "auth_objects": ["M_LFA1_BUK", "M_LFA1_EKO"],
        "behavior_patterns": {
            "behaviors": ["creates", "modifies"],
            "module": "MM-BP",
            "tables_accessed": ["LFA1", "LFB1", "LFBK"],
            "function_modules": ["BAPI_VENDOR_CREATEFROMDATA1"],
            "standard_equivalent": "MK01",
            "business_functions": ["VENDOR_MANAGEMENT", "MASTER_DATA"],
            "sod_risks": ["Create vendor AND initiate payment"],
            "risk_reasons": [
                "Creates vendor including banking details",
                "Sets payment terms without approval",
            ],
        },
    },
    {
        "tcode": "ZFI_CLEAR_OPEN",
        "description": "Open item clearing — all document types",
        "program": "ZFI_CLEAR_OPEN",
        "risk_level": "medium",
        "risk_score": 50,
        "auth_objects": ["F_BKPF_BUK", "F_BKPF_BLA"],
        "behavior_patterns": {
            "behaviors": ["modifies", "clears"],
            "module": "FI-GL",
            "tables_accessed": ["BKPF", "BSEG", "ACDOCA"],
            "function_modules": ["FI_DOCUMENT_CLEAR"],
            "standard_equivalent": "F-03",
            "business_functions": ["GL_CLEARING", "FINANCIAL_POSTING"],
            "sod_risks": [],
            "risk_reasons": [
                "Clears items across all GL accounts without restriction",
            ],
        },
    },
    {
        "tcode": "ZSD_PRICE_OVRD",
        "description": "Sales price override — customer specific",
        "program": "ZSD_PRICE_OVRD",
        "risk_level": "high",
        "risk_score": 80,
        "auth_objects": ["V_KONH_VKO", "V_KONP_VKO"],
        "behavior_patterns": {
            "behaviors": ["modifies"],
            "module": "SD-PRC",
            "tables_accessed": ["KONV", "KONH", "KONP"],
            "function_modules": ["PRICING_COMPLETE"],
            "standard_equivalent": "VK11",
            "business_functions": ["PRICING", "SALES_ORDER_MANAGEMENT"],
            "sod_risks": ["Set price AND create sales order"],
            "risk_reasons": ["Override approved price list without limit"],
        },
    },
    {
        "tcode": "ZBC_TRANSPORT",
        "description": "Custom transport release automation",
        "program": "ZBC_TRANSPORT",
        "risk_level": "medium",
        "risk_score": 50,
        "auth_objects": ["S_CTS_ADMI", "S_TRANSPRT"],
        "behavior_patterns": {
            "behaviors": ["executes", "admin"],
            "module": "BC-CTS",
            "tables_accessed": ["E070", "E071", "E07T"],
            "function_modules": ["TR_RELEASE_REQUEST"],
            "standard_equivalent": "SE10",
            "business_functions": ["TRANSPORT_MANAGEMENT", "CHANGE_MANAGEMENT"],
            "sod_risks": [],
            "risk_reasons": ["Automated release bypasses manual review"],
        },
    },
    {
        "tcode": "YMM_INV_ADJ",
        "description": "Inventory adjustment without goods movement",
        "program": "YMM_INV_ADJ",
        "risk_level": "high",
        "risk_score": 80,
        "auth_objects": ["M_MSEG_BWA", "M_RELA"],
        "behavior_patterns": {
            "behaviors": ["modifies", "creates"],
            "module": "MM-IM",
            "tables_accessed": ["MSEG", "MARD", "MCHB"],
            "function_modules": ["BAPI_GOODSMVT_CREATE"],
            "standard_equivalent": "MI10",
            "business_functions": ["INVENTORY_MANAGEMENT", "GOODS_MOVEMENT"],
            "sod_risks": ["Adjust inventory AND post goods receipt"],
            "risk_reasons": ["Adjust inventory values without physical count"],
        },
    },
    {
        "tcode": "ZPP_PROD_CONF",
        "description": "Production order confirmation with yield override",
        "program": "ZPP_PROD_CONF",
        "risk_level": "low",
        "risk_score": 20,
        "auth_objects": ["C_AFKO_AWA", "C_AFKO_AUF"],
        "behavior_patterns": {
            "behaviors": ["creates", "modifies"],
            "module": "PP-SFC",
            "tables_accessed": ["AFKO", "AFPO", "AFRU"],
            "function_modules": ["BAPI_PRODORDCONF_CREATE_TT"],
            "standard_equivalent": "CO11N",
            "business_functions": ["PRODUCTION_MANAGEMENT"],
            "sod_risks": [],
            "risk_reasons": [],
        },
    },
    {
        "tcode": "ZFI_TAX_POST",
        "description": "Manual tax adjustment posting",
        "program": "ZFI_TAX_POST",
        "risk_level": "high",
        "risk_score": 80,
        "auth_objects": ["F_BKPF_BUK", "F_BKPF_BLA", "F_BKPF_KOA"],
        "behavior_patterns": {
            "behaviors": ["creates", "posts_financial", "modifies"],
            "module": "FI-TX",
            "tables_accessed": ["BKPF", "BSEG", "T007A"],
            "function_modules": ["BAPI_ACC_DOCUMENT_POST"],
            "standard_equivalent": "FB41",
            "business_functions": ["TAX_MANAGEMENT", "FINANCIAL_POSTING"],
            "sod_risks": ["Post tax entries AND configure tax codes"],
            "risk_reasons": [
                "Adjust tax without approval workflow",
                "Can modify tax codes",
            ],
        },
    },
    {
        "tcode": "ZRFC_EXEC",
        "description": "RFC function module executor",
        "program": "ZRFC_EXEC",
        "risk_level": "critical",
        "risk_score": 95,
        "auth_objects": ["S_RFC", "S_RFCACL"],
        "behavior_patterns": {
            "behaviors": ["executes", "reads", "admin"],
            "module": "BC-RFC",
            "tables_accessed": [],
            "function_modules": ["RFC_FUNCTION_SEARCH", "RFC_READ_TABLE"],
            "standard_equivalent": "SE37",
            "business_functions": ["TECHNICAL_ADMINISTRATION"],
            "sod_risks": ["Execute RFC AND read any table"],
            "risk_reasons": [
                "Execute any RFC function module remotely",
                "Bypasses transaction-level access control",
            ],
        },
    },
]

# Standard business function to standard tcode mapping (for SoD suggestions)
_FUNCTION_SOD_RULES: Dict[str, List[str]] = {
    "AP_PAYMENT_PROCESSING": ["VENDOR_MANAGEMENT", "BANK_TRANSFER"],
    "VENDOR_MANAGEMENT": ["AP_PAYMENT_PROCESSING", "MASTER_DATA"],
    "GL_JOURNAL_ENTRY": ["FINANCIAL_POSTING", "ACCRUAL_MANAGEMENT"],
    "PAYROLL_EXECUTION": ["HR_MASTER_DATA", "PAYROLL_ADMINISTRATION"],
    "HR_MASTER_DATA": ["PAYROLL_EXECUTION"],
    "PO_CREATION": ["PURCHASING_APPROVAL", "GOODS_RECEIPT"],
    "PURCHASING_APPROVAL": ["PO_CREATION", "VENDOR_MANAGEMENT"],
    "USER_ADMINISTRATION": ["ROLE_ADMINISTRATION"],
    "ROLE_ADMINISTRATION": ["USER_ADMINISTRATION"],
    "BANK_TRANSFER": ["AP_PAYMENT_PROCESSING", "VENDOR_MANAGEMENT"],
    "BILLING": ["SALES_ORDER_MANAGEMENT", "PRICING"],
    "PRICING": ["BILLING", "SALES_ORDER_MANAGEMENT"],
    "BUDGET_MANAGEMENT": ["COST_CENTER_ACCOUNTING"],
}


# ---------------------------------------------------------------------------
# Helper: convert a DB record to the flat dict format used by public methods
# ---------------------------------------------------------------------------

def _record_to_entry(record: CustomTcodeRecord) -> Dict[str, Any]:
    """
    Flatten a CustomTcodeRecord into the dict shape that the analyzer's
    public methods have always returned (backward-compatible with the old
    in-memory ``_CUSTOM_TCODES`` list).
    """
    bp = record.behavior_patterns or {}
    return {
        "tcode": record.tcode,
        "description": record.description,
        "module": bp.get("module", "Unknown"),
        "behaviors": bp.get("behaviors", []),
        "auth_objects": record.auth_objects or [],
        "tables_accessed": bp.get("tables_accessed", []),
        "function_modules": bp.get("function_modules", []),
        "standard_equivalent": bp.get("standard_equivalent"),
        "risk_level": record.risk_level,
        "risk_score": record.risk_score,
        "risk_reasons": bp.get("risk_reasons", []),
        "business_functions": bp.get("business_functions", []),
        "sod_risks": bp.get("sod_risks", []),
    }


def _is_custom_tcode(tcode: str) -> bool:
    return tcode.upper().startswith("Z") or tcode.upper().startswith("Y")


class CustomTcodeAnalyzer:
    """
    Analyzes custom SAP transactions (Z*/Y* naming convention) to detect
    behaviors, risks, and SoD implications.
    """

    def analyze_transaction(self, tcode: str) -> Dict[str, Any]:
        """
        Detect the behavior profile of a custom transaction.
        Returns detected operations, accessed objects, and risk indicators.
        """
        tcode_upper = tcode.upper()
        if not _is_custom_tcode(tcode_upper):
            return {
                "tcode": tcode_upper,
                "error": "Not a custom transaction code (must start with Z or Y)",
            }

        entry = _TCODE_INDEX.get(tcode_upper)
        if entry is None:
            return self._infer_from_name(tcode_upper)

        return {
            "tcode": tcode_upper,
            "description": entry["description"],
            "module": entry["module"],
            "behaviors": entry["behaviors"],
            "auth_objects": entry["auth_objects"],
            "tables_accessed": entry["tables_accessed"],
            "function_modules": entry["function_modules"],
            "standard_equivalent": entry["standard_equivalent"],
            "analysis_method": "catalog",
        }

    def detect_risk(self, tcode: str) -> Dict[str, Any]:
        """
        Identify risk classification and risk drivers for a custom transaction.
        """
        tcode_upper = tcode.upper()
        entry = _TCODE_INDEX.get(tcode_upper)

        if entry is None:
            return {
                "tcode": tcode_upper,
                "risk_level": "unknown",
                "risk_reasons": ["Transaction not in catalog — manual review required"],
                "sod_risks": [],
                "recommendation": "Perform manual authorization object review",
            }

        return {
            "tcode": tcode_upper,
            "risk_level": entry["risk_level"],
            "risk_reasons": entry["risk_reasons"],
            "sod_risks": entry["sod_risks"],
            "behaviors": entry["behaviors"],
            "module": entry["module"],
            "recommendation": self._build_recommendation(entry),
        }

    def map_to_functions(self, tcode: str) -> Dict[str, Any]:
        """
        Map a custom transaction to standard GRC business functions.
        """
        tcode_upper = tcode.upper()
        entry = _TCODE_INDEX.get(tcode_upper)

        if entry is None:
            return {
                "tcode": tcode_upper,
                "business_functions": [],
                "note": "Not in catalog — functions could not be determined",
            }

        return {
            "tcode": tcode_upper,
            "business_functions": entry["business_functions"],
            "standard_equivalent": entry["standard_equivalent"],
            "module": entry["module"],
        }

    def get_all_custom_tcodes(
        self,
        module: Optional[str] = None,
        risk_level: Optional[str] = None,
        behavior: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        List all known custom transactions with optional filters.

        module: e.g. FI-AP, MM-PUR
        risk_level: low | medium | high | critical
        behavior: creates | modifies | deletes | reads | executes | admin
        """
        results = list(_CUSTOM_TCODES)

        if module:
            mod_upper = module.upper()
            results = [t for t in results if t["module"].upper().startswith(mod_upper)]

        if risk_level:
            results = [t for t in results if t["risk_level"] == risk_level.lower()]

        if behavior:
            beh_lower = behavior.lower()
            results = [t for t in results if beh_lower in t["behaviors"]]

        return [
            {
                "tcode": t["tcode"],
                "description": t["description"],
                "module": t["module"],
                "risk_level": t["risk_level"],
                "behaviors": t["behaviors"],
                "standard_equivalent": t["standard_equivalent"],
            }
            for t in results
        ]

    def suggest_sod_rules(self, tcode: str) -> Dict[str, Any]:
        """
        Suggest SoD rules that should be created to govern this custom transaction,
        based on the business functions it maps to and known conflict patterns.
        """
        tcode_upper = tcode.upper()
        entry = _TCODE_INDEX.get(tcode_upper)

        if entry is None:
            return {
                "tcode": tcode_upper,
                "suggested_rules": [],
                "note": "Transaction not in catalog",
            }

        functions = entry["business_functions"]
        suggestions: List[Dict[str, str]] = []
        seen: set = set()

        for func in functions:
            conflicts = _FUNCTION_SOD_RULES.get(func, [])
            for conflict_func in conflicts:
                pair = tuple(sorted([func, conflict_func]))
                if pair not in seen:
                    seen.add(pair)
                    suggestions.append({
                        "rule_name": f"CUSTOM-{tcode_upper}-{conflict_func}",
                        "function_1": func,
                        "function_2": conflict_func,
                        "risk_level": entry["risk_level"],
                        "description": (
                            f"Segregate {func} from {conflict_func} — "
                            f"{tcode_upper} performs {func} operations"
                        ),
                        "tcode_in_scope": tcode_upper,
                    })

        # Also add direct sod_risks from catalog
        direct_risks = [
            {
                "rule_name": f"CUSTOM-{tcode_upper}-DIRECT-{i+1}",
                "description": risk,
                "risk_level": entry["risk_level"],
                "source": "direct_analysis",
            }
            for i, risk in enumerate(entry.get("sod_risks", []))
        ]

        return {
            "tcode": tcode_upper,
            "business_functions": functions,
            "suggested_rules": suggestions,
            "direct_risks": direct_risks,
            "total_suggestions": len(suggestions) + len(direct_risks),
        }

    def get_analysis_summary(self) -> Dict[str, Any]:
        """Return dashboard statistics across all known custom transactions."""
        risk_counts: Dict[str, int] = {}
        module_counts: Dict[str, int] = {}
        behavior_counts: Dict[str, int] = {}
        sod_risk_count = 0
        critical_list: List[str] = []

        for t in _CUSTOM_TCODES:
            rl = t["risk_level"]
            risk_counts[rl] = risk_counts.get(rl, 0) + 1

            mod = t["module"].split("-")[0]
            module_counts[mod] = module_counts.get(mod, 0) + 1

            for beh in t["behaviors"]:
                behavior_counts[beh] = behavior_counts.get(beh, 0) + 1

            if t.get("sod_risks"):
                sod_risk_count += 1

            if rl == "critical":
                critical_list.append(t["tcode"])

        return {
            "total_custom_tcodes": len(_CUSTOM_TCODES),
            "risk_breakdown": risk_counts,
            "module_breakdown": module_counts,
            "behavior_breakdown": behavior_counts,
            "with_sod_risks": sod_risk_count,
            "critical_transactions": critical_list,
            "coverage_note": (
                "Catalog covers transactions discovered via system analysis. "
                "Run Z_TCODE_SCAN to detect additional custom transactions."
            ),
        }

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _infer_from_name(self, tcode: str) -> Dict[str, Any]:
        """
        Heuristically infer behavior from the transaction name pattern
        when not found in the catalog.
        """
        name_lower = tcode.lower()
        behaviors: List[str] = []
        module_hint = "Unknown"

        # Behavior inference from naming conventions
        if any(k in name_lower for k in ["pay", "post", "bank", "trf"]):
            behaviors.append("posts_financial")
        if any(k in name_lower for k in ["create", "new", "add", "creat"]):
            behaviors.append("creates")
        if any(k in name_lower for k in ["change", "edit", "upd", "mod"]):
            behaviors.append("modifies")
        if any(k in name_lower for k in ["del", "remove", "cancel"]):
            behaviors.append("deletes")
        if any(k in name_lower for k in ["report", "list", "disp", "view", "read"]):
            behaviors.append("reads")
        if any(k in name_lower for k in ["admin", "conf", "set", "config"]):
            behaviors.append("admin")

        if not behaviors:
            behaviors.append("reads")

        # Module inference
        if any(k in name_lower for k in ["fi", "gl", "ap", "ar", "acct"]):
            module_hint = "FI"
        elif any(k in name_lower for k in ["mm", "po", "gr", "vendor"]):
            module_hint = "MM"
        elif any(k in name_lower for k in ["hr", "pay", "pernr"]):
            module_hint = "HR"
        elif any(k in name_lower for k in ["sd", "sales", "bill"]):
            module_hint = "SD"
        elif any(k in name_lower for k in ["pp", "prod", "mfg"]):
            module_hint = "PP"
        elif any(k in name_lower for k in ["bc", "user", "role", "auth"]):
            module_hint = "BC-SEC"

        risk_level = "medium"
        if any(b in behaviors for b in ["posts_financial", "admin"]):
            risk_level = "high"

        return {
            "tcode": tcode,
            "description": "Not in catalog — inferred from naming convention",
            "module": module_hint,
            "behaviors": behaviors,
            "auth_objects": [],
            "tables_accessed": [],
            "function_modules": [],
            "standard_equivalent": None,
            "risk_level": risk_level,
            "analysis_method": "inferred",
            "note": "Add to catalog for precise analysis",
        }

    @staticmethod
    def _build_recommendation(entry: Dict[str, Any]) -> str:
        rl = entry["risk_level"]
        if rl == "critical":
            return (
                "Immediate review required. Restrict access via role concept. "
                "Add compensating controls and monitor all usage."
            )
        if rl == "high":
            return (
                "Implement SoD rule. Limit assignment to named individuals. "
                "Enable audit logging for all executions."
            )
        if rl == "medium":
            return (
                "Review role assignment. Consider mitigating controls "
                "if broad access is required."
            )
        return "Monitor usage. No immediate action required."


# Module-level singleton
_analyzer: Optional[CustomTcodeAnalyzer] = None


def get_analyzer() -> CustomTcodeAnalyzer:
    global _analyzer
    if _analyzer is None:
        _analyzer = CustomTcodeAnalyzer()
    return _analyzer
