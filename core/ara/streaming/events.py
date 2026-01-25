# Event Models for ARA Streaming
# Kafka event schemas for real-time risk evaluation

"""
Event models for the ARA streaming pipeline.

All events are:
- JSON serializable
- Schema versioned
- Timestamp aware
- Correlation enabled
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import datetime
from enum import Enum
from uuid import uuid4
import json


class EventType(Enum):
    """Types of events in the ARA pipeline."""
    # Inbound events
    ACCESS_REQUEST = "ACCESS_REQUEST"
    ACCESS_GRANTED = "ACCESS_GRANTED"
    ACCESS_REVOKED = "ACCESS_REVOKED"
    ACCESS_CHANGE = "ACCESS_CHANGE"
    LOGIN = "LOGIN"
    TRANSACTION_EXECUTED = "TRANSACTION_EXECUTED"

    # Firefighter events
    FF_SESSION_START = "FF_SESSION_START"
    FF_SESSION_END = "FF_SESSION_END"
    FF_TRANSACTION = "FF_TRANSACTION"

    # Risk events
    RISK_DETECTED = "RISK_DETECTED"
    RISK_MITIGATED = "RISK_MITIGATED"
    RISK_ACCEPTED = "RISK_ACCEPTED"

    # Audit events
    AUDIT_LOG = "AUDIT_LOG"


@dataclass
class BaseEvent:
    """Base class for all streaming events."""
    event_id: str = field(default_factory=lambda: str(uuid4()))
    event_type: EventType = EventType.AUDIT_LOG
    timestamp: datetime = field(default_factory=datetime.now)
    correlation_id: str = ""
    schema_version: str = "1.0"

    # Source information
    source_system: str = "GOVERNEX"
    source_component: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "timestamp": self.timestamp.isoformat(),
            "correlation_id": self.correlation_id,
            "schema_version": self.schema_version,
            "source_system": self.source_system,
            "source_component": self.source_component,
        }

    def to_json(self) -> str:
        """Serialize to JSON."""
        return json.dumps(self.to_dict(), default=str)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BaseEvent":
        """Create from dictionary."""
        data["event_type"] = EventType(data.get("event_type", "AUDIT_LOG"))
        if isinstance(data.get("timestamp"), str):
            data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class AccessEvent(BaseEvent):
    """
    Event representing an access-related action.

    Used for:
    - Access requests
    - Role assignments/removals
    - Entitlement changes
    - Login events
    """
    # User information
    user_id: str = ""
    username: str = ""
    department: str = ""

    # Access details
    system: str = "SAP"
    roles: List[str] = field(default_factory=list)
    entitlements: List[str] = field(default_factory=list)

    # Request context
    requested_roles: List[str] = field(default_factory=list)
    requested_entitlements: List[str] = field(default_factory=list)
    action: str = ""  # request, approve, provision, revoke

    # Runtime context
    context: Dict[str, Any] = field(default_factory=dict)

    # Usage snapshot for behavioral analysis
    usage_snapshot: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        self.event_type = EventType.ACCESS_REQUEST
        self.source_component = "access_management"

    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        base.update({
            "user_id": self.user_id,
            "username": self.username,
            "department": self.department,
            "system": self.system,
            "roles": self.roles,
            "entitlements": self.entitlements,
            "requested_roles": self.requested_roles,
            "requested_entitlements": self.requested_entitlements,
            "action": self.action,
            "context": self.context,
            "usage_snapshot": self.usage_snapshot,
        })
        return base

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AccessEvent":
        if isinstance(data.get("timestamp"), str):
            data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        data["event_type"] = EventType(data.get("event_type", "ACCESS_REQUEST"))
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class FirefighterEvent(BaseEvent):
    """
    Event for firefighter/emergency access activity.

    High-priority events requiring real-time monitoring.
    """
    # Session information
    session_id: str = ""
    ff_user_id: str = ""  # Firefighter account
    real_user_id: str = ""  # Actual user
    approver_id: str = ""

    # Activity
    system: str = "SAP"
    tcode: str = ""
    program: str = ""
    table_name: str = ""

    # Transaction details
    duration_ms: int = 0
    is_change: bool = False
    change_type: str = ""  # create, update, delete

    # Context
    justification: str = ""
    ticket_number: str = ""

    # Risk indicators
    is_restricted_tcode: bool = False
    is_table_access: bool = False

    def __post_init__(self):
        self.event_type = EventType.FF_TRANSACTION
        self.source_component = "firefighter"

    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        base.update({
            "session_id": self.session_id,
            "ff_user_id": self.ff_user_id,
            "real_user_id": self.real_user_id,
            "approver_id": self.approver_id,
            "system": self.system,
            "tcode": self.tcode,
            "program": self.program,
            "table_name": self.table_name,
            "duration_ms": self.duration_ms,
            "is_change": self.is_change,
            "change_type": self.change_type,
            "justification": self.justification,
            "ticket_number": self.ticket_number,
            "is_restricted_tcode": self.is_restricted_tcode,
            "is_table_access": self.is_table_access,
        })
        return base

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FirefighterEvent":
        if isinstance(data.get("timestamp"), str):
            data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        data["event_type"] = EventType(data.get("event_type", "FF_TRANSACTION"))
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class RiskResultEvent(BaseEvent):
    """
    Event containing risk evaluation results.

    Published after real-time risk analysis.
    """
    # Analysis reference
    analysis_id: str = ""
    original_event_id: str = ""

    # Entity
    user_id: str = ""
    system: str = "SAP"

    # Risk summary
    total_risks: int = 0
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0

    # Scores
    aggregate_risk_score: int = 0
    max_risk_score: int = 0
    ml_risk_adjustment: int = 0

    # Details
    risks: List[Dict[str, Any]] = field(default_factory=list)
    sod_conflicts: List[Dict[str, Any]] = field(default_factory=list)

    # ML insights
    anomaly_detected: bool = False
    anomaly_explanation: str = ""

    # Recommendation
    recommendation: str = ""  # approve, review, deny
    recommendation_reason: str = ""

    # Performance
    evaluation_duration_ms: int = 0

    def __post_init__(self):
        self.event_type = EventType.RISK_DETECTED
        self.source_component = "ara_engine"

    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        base.update({
            "analysis_id": self.analysis_id,
            "original_event_id": self.original_event_id,
            "user_id": self.user_id,
            "system": self.system,
            "total_risks": self.total_risks,
            "critical_count": self.critical_count,
            "high_count": self.high_count,
            "medium_count": self.medium_count,
            "low_count": self.low_count,
            "aggregate_risk_score": self.aggregate_risk_score,
            "max_risk_score": self.max_risk_score,
            "ml_risk_adjustment": self.ml_risk_adjustment,
            "risks": self.risks,
            "sod_conflicts": self.sod_conflicts,
            "anomaly_detected": self.anomaly_detected,
            "anomaly_explanation": self.anomaly_explanation,
            "recommendation": self.recommendation,
            "recommendation_reason": self.recommendation_reason,
            "evaluation_duration_ms": self.evaluation_duration_ms,
        })
        return base

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RiskResultEvent":
        if isinstance(data.get("timestamp"), str):
            data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        data["event_type"] = EventType(data.get("event_type", "RISK_DETECTED"))
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class AuditEvent(BaseEvent):
    """
    Immutable audit event for compliance trail.

    Every significant action generates an audit event.
    """
    # Action
    action: str = ""  # risk_evaluated, risk_mitigated, exception_granted, etc.
    action_category: str = ""  # access, risk, mitigation, exception

    # Subject
    subject_type: str = ""  # user, role, risk, control
    subject_id: str = ""
    subject_name: str = ""

    # Actor
    actor_id: str = ""
    actor_name: str = ""
    actor_type: str = ""  # user, system, automated

    # Details
    details: Dict[str, Any] = field(default_factory=dict)
    previous_state: Dict[str, Any] = field(default_factory=dict)
    new_state: Dict[str, Any] = field(default_factory=dict)

    # Compliance
    compliance_tags: List[str] = field(default_factory=list)
    regulatory_requirement: str = ""

    def __post_init__(self):
        self.event_type = EventType.AUDIT_LOG
        self.source_component = "audit_trail"

    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        base.update({
            "action": self.action,
            "action_category": self.action_category,
            "subject_type": self.subject_type,
            "subject_id": self.subject_id,
            "subject_name": self.subject_name,
            "actor_id": self.actor_id,
            "actor_name": self.actor_name,
            "actor_type": self.actor_type,
            "details": self.details,
            "previous_state": self.previous_state,
            "new_state": self.new_state,
            "compliance_tags": self.compliance_tags,
            "regulatory_requirement": self.regulatory_requirement,
        })
        return base

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AuditEvent":
        if isinstance(data.get("timestamp"), str):
            data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        data["event_type"] = EventType(data.get("event_type", "AUDIT_LOG"))
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


# Event serialization helpers

def serialize_event(event: BaseEvent) -> bytes:
    """Serialize event to bytes for Kafka."""
    return event.to_json().encode('utf-8')


def deserialize_event(data: bytes, event_class: type = BaseEvent) -> BaseEvent:
    """Deserialize event from bytes."""
    payload = json.loads(data.decode('utf-8'))
    return event_class.from_dict(payload)


def parse_event_type(data: bytes) -> EventType:
    """Parse event type from raw data without full deserialization."""
    payload = json.loads(data.decode('utf-8'))
    return EventType(payload.get("event_type", "AUDIT_LOG"))
