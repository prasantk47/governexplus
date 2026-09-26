"""
Evidence & Audit Provenance Engine

Append-only, hash-chained evidence store that all modules use
to produce verifiable audit trails.
"""

from .engine import EvidenceEngine
from .models import (
    EvidenceIntegrity,
    EvidenceRecord,
    EvidenceType,
)

__all__ = [
    "EvidenceEngine",
    "EvidenceIntegrity",
    "EvidenceRecord",
    "EvidenceType",
]
