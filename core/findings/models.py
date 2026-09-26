"""
Findings Engine — Data Models

Normalized finding and recommendation models that every module
produces and the central findings center consumes.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Any


class FindingType(enum.Enum):
    SOD_VIOLATION = "sod_violation"
    SENSITIVE_ACCESS = "sensitive_access"
    CRITICAL_ACTION = "critical_action"
    OVER_PROVISIONED = "over_provisioned"
    UNDER_PROVISIONED = "under_provisioned"
    STALE_ACCESS = "stale_access"
    UNUSED_ACCESS = "unused_access"
    ROLE_DRIFT = "role_drift"
    CERTIFICATION_OVERDUE = "certification_overdue"
    CERTIFICATION_REVOKED = "certification_revoked"
    FIREFIGHTER_ANOMALY = "firefighter_anomaly"
    POLICY_VIOLATION = "policy_violation"
    IDENTITY_MISMATCH = "identity_mismatch"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    ORPHAN_ACCOUNT = "orphan_account"


class FindingSeverity(enum.Enum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class FindingStatus(enum.Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    MITIGATED = "mitigated"
    REMEDIATED = "remediated"
    ACCEPTED = "accepted"
    FALSE_POSITIVE = "false_positive"
    EXPIRED = "expired"


class FindingSource(enum.Enum):
    RISK_ENGINE = "risk_engine"
    EFFECTIVE_ACCESS = "effective_access"
    CERTIFICATION = "certification"
    FIREFIGHTER = "firefighter"
    DRIFT_DETECTION = "drift_detection"
    IDENTITY_CORRELATION = "identity_correlation"
    ROLE_INTELLIGENCE = "role_intelligence"
    PROVISIONING = "provisioning"
    USAGE_ANALYTICS = "usage_analytics"
    POLICY_ENGINE = "policy_engine"
    MANUAL = "manual"


class RecommendationType(enum.Enum):
    REMOVE_ROLE = "remove_role"
    REMOVE_TRANSACTION = "remove_transaction"
    ADD_MITIGATION = "add_mitigation"
    SPLIT_ROLE = "split_role"
    REASSIGN_TO_ROLE = "reassign_to_role"
    LOCK_ACCOUNT = "lock_account"
    REVIEW_ACCESS = "review_access"
    CERTIFY_ACCESS = "certify_access"
    RESTRICT_ORG_SCOPE = "restrict_org_scope"
    CREATE_DERIVED_ROLE = "create_derived_role"
    ESCALATE = "escalate"
    NO_ACTION = "no_action"


class RecommendationStatus(enum.Enum):
    PROPOSED = "proposed"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Recommendation:
    """A specific recommended action for a finding."""
    recommendation_id: str
    finding_id: str
    recommendation_type: RecommendationType
    description: str
    priority: int = 1  # 1=highest

    # What to do
    target_user_id: Optional[str] = None
    target_role_id: Optional[str] = None
    target_transaction: Optional[str] = None
    target_system: str = "SAP"
    action_params: dict[str, Any] = field(default_factory=dict)

    # Status tracking
    status: RecommendationStatus = RecommendationStatus.PROPOSED
    proposed_at: datetime = field(default_factory=datetime.utcnow)
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    execution_result: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "recommendation_id": self.recommendation_id,
            "finding_id": self.finding_id,
            "type": self.recommendation_type.value,
            "description": self.description,
            "priority": self.priority,
            "target_user_id": self.target_user_id,
            "target_role_id": self.target_role_id,
            "target_transaction": self.target_transaction,
            "status": self.status.value,
            "proposed_at": self.proposed_at.isoformat(),
        }


@dataclass
class Finding:
    """A normalized finding from any module.

    This is the single object that feeds the Findings Center,
    dashboards, reports, and audit trails.
    """
    finding_id: str
    finding_type: FindingType
    severity: FindingSeverity
    source: FindingSource

    # Who/what is affected
    user_id: str
    tenant_id: str
    system_id: str = "SAP"

    # What was found
    title: str = ""
    description: str = ""
    details: dict[str, Any] = field(default_factory=dict)

    # Context: roles, transactions, auth objects involved
    related_roles: list[str] = field(default_factory=list)
    related_transactions: list[str] = field(default_factory=list)
    related_auth_objects: list[str] = field(default_factory=list)
    org_scope: dict[str, list[str]] = field(default_factory=dict)

    # Risk
    risk_score: float = 0.0
    business_impact: str = ""

    # Regulatory
    sox_relevant: bool = False
    regulatory_refs: list[str] = field(default_factory=list)

    # Linked objects
    rule_id: Optional[str] = None
    violation_id: Optional[str] = None
    campaign_id: Optional[str] = None
    request_id: Optional[str] = None

    # Status tracking
    status: FindingStatus = FindingStatus.OPEN
    detected_at: datetime = field(default_factory=datetime.utcnow)
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None

    # Recommendations
    recommendations: list[Recommendation] = field(default_factory=list)

    # Evidence/audit trail
    evidence_ids: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "finding_id": self.finding_id,
            "type": self.finding_type.value,
            "severity": self.severity.value,
            "source": self.source.value,
            "user_id": self.user_id,
            "tenant_id": self.tenant_id,
            "title": self.title,
            "description": self.description,
            "details": self.details,
            "related_roles": self.related_roles,
            "related_transactions": self.related_transactions,
            "org_scope": self.org_scope,
            "risk_score": self.risk_score,
            "business_impact": self.business_impact,
            "sox_relevant": self.sox_relevant,
            "rule_id": self.rule_id,
            "status": self.status.value,
            "detected_at": self.detected_at.isoformat(),
            "recommendations": [r.to_dict() for r in self.recommendations],
        }

    def to_summary(self) -> dict:
        return {
            "finding_id": self.finding_id,
            "type": self.finding_type.value,
            "severity": self.severity.value,
            "title": self.title,
            "user_id": self.user_id,
            "status": self.status.value,
            "risk_score": self.risk_score,
            "recommendation_count": len(self.recommendations),
        }
