"""
Identity Correlation Engine Module

Maps and correlates identities across SAP ECC, S/4HANA, SuccessFactors, and Azure AD.
"""

from .engine import (
    IdentityCorrelationEngine,
    IdentityCluster,
    SystemAccount,
    CorrelationLink,
    CorrelationResult,
    OrphanAccount,
    CrossSystemRisk,
    IdentityAnomaly,
    CorrelationStats,
    SystemType,
    CorrelationMethod,
    AccountStatus,
    AnomalyType,
    RiskLevel,
)

__all__ = [
    "IdentityCorrelationEngine",
    "IdentityCluster",
    "SystemAccount",
    "CorrelationLink",
    "CorrelationResult",
    "OrphanAccount",
    "CrossSystemRisk",
    "IdentityAnomaly",
    "CorrelationStats",
    "SystemType",
    "CorrelationMethod",
    "AccountStatus",
    "AnomalyType",
    "RiskLevel",
]
