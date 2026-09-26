"""
Evidence & Audit Provenance Engine — Data Models

Immutable audit evidence that links every action to its provenance:
who, what, when, why, how, and proof.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Any


class EvidenceType(enum.Enum):
    ACCESS_REQUEST = "access_request"
    APPROVAL_DECISION = "approval_decision"
    PROVISIONING_ACTION = "provisioning_action"
    PROVISIONING_VERIFICATION = "provisioning_verification"
    SOD_ANALYSIS = "sod_analysis"
    RISK_ASSESSMENT = "risk_assessment"
    CERTIFICATION_DECISION = "certification_decision"
    CERTIFICATION_REVOCATION = "certification_revocation"
    FIREFIGHTER_SESSION = "firefighter_session"
    FIREFIGHTER_ACTIVITY = "firefighter_activity"
    ROLE_CHANGE = "role_change"
    POLICY_CHANGE = "policy_change"
    EXCEPTION_GRANT = "exception_grant"
    MITIGATION_ASSIGNMENT = "mitigation_assignment"
    IDENTITY_CHANGE = "identity_change"
    CONNECTOR_SYNC = "connector_sync"
    MANUAL_OVERRIDE = "manual_override"


class EvidenceIntegrity(enum.Enum):
    VERIFIED = "verified"
    UNVERIFIED = "unverified"
    TAMPERED = "tampered"


@dataclass
class EvidenceRecord:
    """An immutable audit evidence record.

    Evidence is append-only.  Once created, it cannot be modified.
    Each record has a hash chain linking it to the previous record
    for tamper detection.
    """
    evidence_id: str
    evidence_type: EvidenceType
    tenant_id: str

    # Who performed the action
    actor_user_id: str
    actor_role: str = ""         # their role at the time
    actor_ip: str = ""

    # What happened
    action: str = ""             # human-readable action description
    action_details: dict[str, Any] = field(default_factory=dict)

    # On what
    target_user_id: Optional[str] = None
    target_object_type: str = ""  # "role", "request", "violation", etc.
    target_object_id: str = ""

    # Why (justification/reason)
    justification: str = ""
    policy_id: Optional[str] = None

    # Links to other objects
    request_id: Optional[str] = None
    workflow_id: Optional[str] = None
    finding_id: Optional[str] = None
    plan_id: Optional[str] = None
    campaign_id: Optional[str] = None
    session_id: Optional[str] = None

    # Proof
    before_state: Optional[dict] = None
    after_state: Optional[dict] = None
    system_response: Optional[str] = None

    # Integrity
    timestamp: datetime = field(default_factory=datetime.utcnow)
    previous_hash: str = ""
    record_hash: str = ""
    integrity: EvidenceIntegrity = EvidenceIntegrity.VERIFIED

    def to_dict(self) -> dict:
        return {
            "evidence_id": self.evidence_id,
            "type": self.evidence_type.value,
            "tenant_id": self.tenant_id,
            "actor": self.actor_user_id,
            "action": self.action,
            "target_type": self.target_object_type,
            "target_id": self.target_object_id,
            "target_user": self.target_user_id,
            "justification": self.justification,
            "request_id": self.request_id,
            "finding_id": self.finding_id,
            "timestamp": self.timestamp.isoformat(),
            "integrity": self.integrity.value,
            "record_hash": self.record_hash,
        }

    def to_audit_line(self) -> str:
        """One-line audit trail format."""
        target = self.target_user_id or self.target_object_id
        return (
            f"[{self.timestamp.isoformat()}] "
            f"{self.actor_user_id} {self.action} "
            f"on {self.target_object_type}:{target} "
            f"({self.evidence_type.value})"
        )
