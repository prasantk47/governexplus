"""
Risk Engine — Data Models

Violation and analysis result models that capture the FULL context
of a risk finding, not just "these two transactions conflict."
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


class ViolationStatus(enum.Enum):
    OPEN = "open"
    MITIGATED = "mitigated"
    REMEDIATED = "remediated"
    ACCEPTED = "accepted"
    FALSE_POSITIVE = "false_positive"
    EXCEPTION = "exception"


class AnalysisDepth(enum.Enum):
    """How deep the analysis went."""
    TRANSACTION_ONLY = "transaction"    # legacy: just T-code overlap
    AUTH_OBJECT = "auth_object"         # checked auth objects
    FIELD_VALUE = "field_value"         # checked field/value pairs
    ORG_SCOPE = "org_scope"             # checked organizational overlap


@dataclass
class SoDConflict:
    """A specific SoD conflict between two business functions.

    Unlike the old ConflictSet, this captures:
    - Which auth objects actually conflict (not just T-codes)
    - Which org scope overlaps (company code, plant, etc.)
    - Whether the conflict is change-vs-change or change-vs-display
    - The analysis depth that confirmed the conflict
    """
    rule_id: str
    rule_name: str

    # Function A
    function_a_id: str
    function_a_name: str
    function_a_transactions: list[str]

    # Function B
    function_b_id: str
    function_b_name: str
    function_b_transactions: list[str]

    # The actual conflicting transactions found on the user
    conflicting_txn_a: list[str] = field(default_factory=list)
    conflicting_txn_b: list[str] = field(default_factory=list)

    # Auth object overlap details
    auth_object_overlaps: list[dict] = field(default_factory=list)
    # Each: {"auth_object": str, "fields": {field: overlap_values}, "source_roles": []}

    # Org scope overlap
    org_overlap: dict[str, list[str]] = field(default_factory=dict)
    # {org_field: [overlapping_values]}

    # Analysis depth that found this conflict
    analysis_depth: AnalysisDepth = AnalysisDepth.TRANSACTION_ONLY

    # Is this a real change-vs-change conflict or just display?
    both_have_change_access: bool = False

    def to_dict(self) -> dict:
        return {
            "rule_id": self.rule_id,
            "rule_name": self.rule_name,
            "function_a": {
                "id": self.function_a_id,
                "name": self.function_a_name,
                "transactions": self.conflicting_txn_a,
            },
            "function_b": {
                "id": self.function_b_id,
                "name": self.function_b_name,
                "transactions": self.conflicting_txn_b,
            },
            "auth_object_overlaps": self.auth_object_overlaps,
            "org_overlap": self.org_overlap,
            "analysis_depth": self.analysis_depth.value,
            "both_have_change_access": self.both_have_change_access,
        }


@dataclass
class SoDViolation:
    """A confirmed SoD violation for a specific user."""
    violation_id: str
    user_id: str
    conflict: SoDConflict

    # Risk classification
    risk_level: str = "high"   # low, medium, high, critical
    business_process: str = ""
    risk_description: str = ""
    business_impact: str = ""

    # Source roles granting the conflicting access
    source_roles_a: list[str] = field(default_factory=list)
    source_roles_b: list[str] = field(default_factory=list)

    # Mitigation
    mitigation_id: Optional[str] = None
    mitigation_description: str = ""
    is_mitigated: bool = False

    # Status
    status: ViolationStatus = ViolationStatus.OPEN
    detected_at: datetime = field(default_factory=datetime.utcnow)
    resolved_at: Optional[datetime] = None

    # Regulatory
    sox_relevant: bool = False
    regulatory_refs: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "violation_id": self.violation_id,
            "user_id": self.user_id,
            "conflict": self.conflict.to_dict(),
            "risk_level": self.risk_level,
            "business_process": self.business_process,
            "risk_description": self.risk_description,
            "business_impact": self.business_impact,
            "source_roles_a": self.source_roles_a,
            "source_roles_b": self.source_roles_b,
            "is_mitigated": self.is_mitigated,
            "mitigation_id": self.mitigation_id,
            "status": self.status.value,
            "detected_at": self.detected_at.isoformat(),
            "sox_relevant": self.sox_relevant,
        }


@dataclass
class SensitiveAccessViolation:
    """A user has access to a sensitive transaction/function."""
    violation_id: str
    user_id: str
    transaction: str
    auth_objects: list[str]
    source_roles: list[str]
    org_scope: dict[str, list[str]]
    risk_level: str = "high"
    has_change_access: bool = False
    last_used: Optional[datetime] = None
    usage_count_90d: int = 0
    status: ViolationStatus = ViolationStatus.OPEN
    detected_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "violation_id": self.violation_id,
            "user_id": self.user_id,
            "transaction": self.transaction,
            "auth_objects": self.auth_objects,
            "source_roles": self.source_roles,
            "org_scope": self.org_scope,
            "risk_level": self.risk_level,
            "has_change_access": self.has_change_access,
            "status": self.status.value,
        }


@dataclass
class CriticalActionViolation:
    """A user executed (or has access to) a critical action."""
    violation_id: str
    user_id: str
    transaction: str
    action_description: str
    source_roles: list[str]
    risk_level: str = "critical"
    was_executed: bool = False
    executed_at: Optional[datetime] = None
    status: ViolationStatus = ViolationStatus.OPEN
    detected_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "violation_id": self.violation_id,
            "user_id": self.user_id,
            "transaction": self.transaction,
            "action_description": self.action_description,
            "risk_level": self.risk_level,
            "was_executed": self.was_executed,
            "status": self.status.value,
        }


@dataclass
class RiskAnalysisResult:
    """Complete risk analysis result for a user."""
    user_id: str
    tenant_id: str
    analyzed_at: datetime = field(default_factory=datetime.utcnow)
    analysis_depth: AnalysisDepth = AnalysisDepth.ORG_SCOPE

    # Violations
    sod_violations: list[SoDViolation] = field(default_factory=list)
    sensitive_access: list[SensitiveAccessViolation] = field(default_factory=list)
    critical_actions: list[CriticalActionViolation] = field(default_factory=list)

    # Summary
    total_violations: int = 0
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    mitigated_count: int = 0

    # Computed risk score (0-100)
    risk_score: float = 0.0

    def compute_summary(self) -> None:
        """Recompute summary counts and risk score."""
        all_violations = []
        for v in self.sod_violations:
            all_violations.append(v.risk_level)
        for v in self.sensitive_access:
            all_violations.append(v.risk_level)
        for v in self.critical_actions:
            all_violations.append(v.risk_level)

        self.total_violations = len(all_violations)
        self.critical_count = sum(1 for r in all_violations if r == "critical")
        self.high_count = sum(1 for r in all_violations if r == "high")
        self.medium_count = sum(1 for r in all_violations if r == "medium")
        self.low_count = sum(1 for r in all_violations if r == "low")
        self.mitigated_count = sum(
            1 for v in self.sod_violations if v.is_mitigated
        )

        # Weighted score: critical=100, high=60, medium=30, low=10
        weights = {"critical": 100, "high": 60, "medium": 30, "low": 10}
        raw = sum(weights.get(r, 0) for r in all_violations)
        # Normalize to 0-100 (cap at 100)
        self.risk_score = min(100.0, raw)

    def to_dict(self) -> dict:
        self.compute_summary()
        return {
            "user_id": self.user_id,
            "analyzed_at": self.analyzed_at.isoformat(),
            "analysis_depth": self.analysis_depth.value,
            "risk_score": self.risk_score,
            "total_violations": self.total_violations,
            "by_severity": {
                "critical": self.critical_count,
                "high": self.high_count,
                "medium": self.medium_count,
                "low": self.low_count,
            },
            "mitigated_count": self.mitigated_count,
            "sod_violations": [v.to_dict() for v in self.sod_violations],
            "sensitive_access": [v.to_dict() for v in self.sensitive_access],
            "critical_actions": [v.to_dict() for v in self.critical_actions],
        }
