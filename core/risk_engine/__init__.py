"""
Risk & SoD Analysis Engine

Proper SoD analysis that goes beyond transaction-code matching:

1. Auth-object level analysis (not just T-codes)
2. Organizational scope overlap detection
3. Activity-level conflict detection (create vs display is NOT a conflict)
4. Mitigation-aware violation scoring
5. Consumes UserEffectiveAccess from the Effective Access Engine

This replaces the demo-grade ConflictSet.check_conflict() which only
did set intersection on entitlement keys.
"""

from .engine import RiskEngine
from .models import (
    SoDConflict,
    SoDViolation,
    SensitiveAccessViolation,
    CriticalActionViolation,
    RiskAnalysisResult,
    ViolationStatus,
    AnalysisDepth,
)

__all__ = [
    "RiskEngine",
    "SoDConflict",
    "SoDViolation",
    "SensitiveAccessViolation",
    "CriticalActionViolation",
    "RiskAnalysisResult",
    "ViolationStatus",
    "AnalysisDepth",
]
