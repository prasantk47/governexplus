"""
Upgrade Impact Analyzer Module

Assesses the security and authorization impact of SAP version upgrades.
"""

from .analyzer import (
    UpgradeImpactAnalyzer,
    UpgradeImpact,
    AffectedRole,
    DeprecatedObject,
    NewRequirement,
    SimplificationItem,
    UpgradeSimulation,
    RoleSimulationResult,
    RemediationPlan,
    RemediationTask,
    ImpactSeverity,
    ChangeType,
    RemediationAction,
    SUPPORTED_VERSION_PAIRS,
)

__all__ = [
    "UpgradeImpactAnalyzer",
    "UpgradeImpact",
    "AffectedRole",
    "DeprecatedObject",
    "NewRequirement",
    "SimplificationItem",
    "UpgradeSimulation",
    "RoleSimulationResult",
    "RemediationPlan",
    "RemediationTask",
    "ImpactSeverity",
    "ChangeType",
    "RemediationAction",
    "SUPPORTED_VERSION_PAIRS",
]
