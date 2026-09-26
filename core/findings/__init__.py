"""
Unified Findings Engine

All modules (SoD, certification, firefighter, drift, reconciliation)
produce normalized Finding objects that flow into a central Findings
& Recommendations Center.

A Finding is the atomic unit of "something needs attention."
"""

from .models import (
    Finding,
    FindingType,
    FindingSeverity,
    FindingStatus,
    FindingSource,
    Recommendation,
    RecommendationType,
    RecommendationStatus,
)
from .engine import FindingsEngine

__all__ = [
    "Finding",
    "FindingType",
    "FindingSeverity",
    "FindingStatus",
    "FindingSource",
    "Recommendation",
    "RecommendationType",
    "RecommendationStatus",
    "FindingsEngine",
]
