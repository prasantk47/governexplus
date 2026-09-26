"""
core.troubleshooter — Access Troubleshooter Module

Exports the engine and all public data types needed by the API layer and
any other GovernexPlus modules that need to invoke a diagnosis.
"""

from core.troubleshooter.engine import (
    # Input / output data classes
    TroubleshootRequest,
    DiagnosisStep,
    DiagnosisResult,
    # Enumerations
    CheckStatus,
    DiagnosisStatus,
    # Main engine
    AccessTroubleshooter,
    # Knowledge base accessors
    get_transaction_list,
    get_transaction_requirements,
    get_common_issues,
    get_diagnosis_history,
    # Raw knowledge bases (for advanced use)
    TRANSACTION_KB,
    FIORI_KB,
    COMMON_ISSUES,
)

__all__ = [
    "TroubleshootRequest",
    "DiagnosisStep",
    "DiagnosisResult",
    "CheckStatus",
    "DiagnosisStatus",
    "AccessTroubleshooter",
    "get_transaction_list",
    "get_transaction_requirements",
    "get_common_issues",
    "get_diagnosis_history",
    "TRANSACTION_KB",
    "FIORI_KB",
    "COMMON_ISSUES",
]
