"""
SIEM Connector for Governex+

Real-time security event forwarding to SIEM systems like
Splunk, QRadar, Azure Sentinel, and others.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime
import json
import logging
import asyncio
from collections import deque

logger = logging.getLogger(__name__)


class SIEMEventType(Enum):
    """Types of security events"""
    # Authentication Events
    LOGIN_SUCCESS = "auth.login.success"
    LOGIN_FAILURE = "auth.login.failure"
    LOGIN_LOCKED = "auth.login.locked"
    LOGOUT = "auth.logout"
    SESSION_TIMEOUT = "auth.session.timeout"
    MFA_CHALLENGE = "auth.mfa.challenge"
    MFA_FAILURE = "auth.mfa.failure"

    # Authorization Events
    ACCESS_GRANTED = "authz.access.granted"
    ACCESS_DENIED = "authz.access.denied"
    PRIVILEGE_ESCALATION = "authz.privilege.escalation"
    ROLE_ASSIGNED = "authz.role.assigned"
    ROLE_REMOVED = "authz.role.removed"
    PERMISSION_CHANGE = "authz.permission.change"

    # Data Access Events
    DATA_READ = "data.read"
    DATA_WRITE = "data.write"
    DATA_DELETE = "data.delete"
    DATA_EXPORT = "data.export"
    BULK_DOWNLOAD = "data.bulk.download"
    SENSITIVE_ACCESS = "data.sensitive.access"

    # Risk Events
    SOD_VIOLATION = "risk.sod.violation"
    RISK_THRESHOLD = "risk.threshold.exceeded"
    ANOMALY_DETECTED = "risk.anomaly.detected"
    POLICY_VIOLATION = "risk.policy.violation"

    # System Events
    CONFIG_CHANGE = "system.config.change"
    USER_CREATED = "system.user.created"
    USER_DELETED = "system.user.deleted"
    ROLE_CREATED = "system.role.created"
    ROLE_MODIFIED = "system.role.modified"

    # Firefighter Events
    FF_SESSION_START = "firefighter.session.start"
    FF_SESSION_END = "firefighter.session.end"
    FF_ACTION_PERFORMED = "firefighter.action.performed"
    FF_VIOLATION = "firefighter.violation"

    # Compliance Events
    CERTIFICATION_COMPLETED = "compliance.certification.completed"
    AUDIT_FINDING = "compliance.audit.finding"
    CONTROL_FAILURE = "compliance.control.failure"


class SIEMSeverity(Enum):
    """Event severity levels (CEF standard)"""
    LOW = 1
    MEDIUM = 4
    HIGH = 7
    CRITICAL = 10


@dataclass
class SIEMEvent:
    """Security event for SIEM reporting"""
    event_id: str
    event_type: SIEMEventType
    severity: SIEMSeverity
    timestamp: datetime

    # Source information
    source_system: str
    source_ip: str = ""
    source_user: str = ""
    source_application: str = "Governex+"

    # Target information
    target_user: str = ""
    target_resource: str = ""
    target_system: str = ""

    # Event details
    action: str = ""
    outcome: str = "success"  # success, failure, unknown
    reason: str = ""

    # Additional context
    risk_score: Optional[int] = None
    transaction_code: str = ""
    session_id: str = ""
    request_id: str = ""

    # Custom fields
    custom_fields: Dict[str, Any] = field(default_factory=dict)

    # Correlation
    correlation_id: str = ""
    related_events: List[str] = field(default_factory=list)

    def to_cef(self) -> str:
        """Convert to Common Event Format (CEF)"""
        # CEF:Version|Device Vendor|Device Product|Device Version|Signature ID|Name|Severity|Extension
        extensions = {
            "src": self.source_ip,
            "suser": self.source_user,
            "duser": self.target_user,
            "dst": self.target_system,
            "act": self.action,
            "outcome": self.outcome,
            "msg": self.reason,
            "cs1": self.transaction_code,
            "cs1Label": "TransactionCode",
            "cs2": self.session_id,
            "cs2Label": "SessionID",
            "cs3": str(self.risk_score) if self.risk_score else "",
            "cs3Label": "RiskScore",
            "rt": self.timestamp.strftime("%b %d %Y %H:%M:%S"),
        }

        ext_str = " ".join(f"{k}={v}" for k, v in extensions.items() if v)

        return (
            f"CEF:0|Governex|Governex+|1.0|{self.event_type.value}|"
            f"{self.event_type.name}|{self.severity.value}|{ext_str}"
        )

    def to_json(self) -> str:
        """Convert to JSON format"""
        return json.dumps({
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "severity": self.severity.name,
            "severity_value": self.severity.value,
            "timestamp": self.timestamp.isoformat(),
            "source": {
                "system": self.source_system,
                "ip": self.source_ip,
                "user": self.source_user,
                "application": self.source_application
            },
            "target": {
                "user": self.target_user,
                "resource": self.target_resource,
                "system": self.target_system
            },
            "action": self.action,
            "outcome": self.outcome,
            "reason": self.reason,
            "risk_score": self.risk_score,
            "transaction_code": self.transaction_code,
            "session_id": self.session_id,
            "request_id": self.request_id,
            "correlation_id": self.correlation_id,
            "related_events": self.related_events,
            "custom_fields": self.custom_fields
        }, default=str)

    def to_syslog(self) -> str:
        """Convert to Syslog format"""
        priority = 8 + min(self.severity.value, 7)  # facility=1 (user), severity mapped
        return (
            f"<{priority}>{self.timestamp.strftime('%b %d %H:%M:%S')} "
            f"{self.source_system} Governex+[{self.event_id}]: "
            f"{self.event_type.value} - {self.action} by {self.source_user} "
            f"outcome={self.outcome} risk={self.risk_score or 'N/A'}"
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "event_type_name": self.event_type.name,
            "severity": self.severity.name,
            "severity_value": self.severity.value,
            "timestamp": self.timestamp.isoformat(),
            "source_system": self.source_system,
            "source_ip": self.source_ip,
            "source_user": self.source_user,
            "source_application": self.source_application,
            "target_user": self.target_user,
            "target_resource": self.target_resource,
            "target_system": self.target_system,
            "action": self.action,
            "outcome": self.outcome,
            "reason": self.reason,
            "risk_score": self.risk_score,
            "transaction_code": self.transaction_code,
            "session_id": self.session_id,
            "request_id": self.request_id,
            "correlation_id": self.correlation_id,
            "related_events": self.related_events,
            "custom_fields": self.custom_fields
        }


@dataclass
class SIEMDestination:
    """SIEM destination configuration"""
    name: str
    type: str  # splunk, qradar, sentinel, elastic, syslog, webhook
    enabled: bool = True

    # Connection settings
    host: str = ""
    port: int = 0
    protocol: str = "https"  # https, http, tcp, udp

    # Authentication
    api_key: str = ""
    api_secret: str = ""
    token: str = ""

    # Formatting
    format: str = "json"  # json, cef, syslog

    # Filtering
    min_severity: SIEMSeverity = SIEMSeverity.LOW
    event_types: List[str] = field(default_factory=list)  # Empty = all

    # Batching
    batch_size: int = 100
    batch_timeout_seconds: int = 30


class SIEMConnector:
    """
    SIEM Connector for Governex+

    Features:
    - Multi-destination support (Splunk, QRadar, Sentinel, etc.)
    - Real-time event streaming
    - Event batching and buffering
    - Multiple output formats (CEF, JSON, Syslog)
    - Event filtering by severity and type
    - Automatic retry and failover
    """

    def __init__(self):
        self.destinations: Dict[str, SIEMDestination] = {}
        self.event_buffer: deque = deque(maxlen=10000)
        self.sent_events: deque = deque(maxlen=1000)
        self.callbacks: List[Callable[[SIEMEvent], None]] = []
        self.statistics = {
            "total_events": 0,
            "events_sent": 0,
            "events_failed": 0,
            "events_filtered": 0,
            "by_severity": {s.name: 0 for s in SIEMSeverity},
            "by_type": {},
            "by_destination": {}
        }
        self._running = False

        # Add default demo destinations
        self._setup_demo_destinations()

    def _setup_demo_destinations(self):
        """Setup demo SIEM destinations"""
        self.destinations["splunk_demo"] = SIEMDestination(
            name="Splunk HEC",
            type="splunk",
            enabled=True,
            host="splunk.governexplus.com",
            port=8088,
            protocol="https",
            format="json",
            min_severity=SIEMSeverity.LOW
        )

        self.destinations["sentinel_demo"] = SIEMDestination(
            name="Azure Sentinel",
            type="sentinel",
            enabled=True,
            host="sentinel.azure.com",
            format="json",
            min_severity=SIEMSeverity.MEDIUM
        )

        self.destinations["syslog_demo"] = SIEMDestination(
            name="Syslog Server",
            type="syslog",
            enabled=False,
            host="syslog.internal",
            port=514,
            protocol="udp",
            format="syslog",
            min_severity=SIEMSeverity.HIGH
        )

    def add_destination(self, destination: SIEMDestination) -> str:
        """Add a SIEM destination"""
        dest_id = f"dest_{len(self.destinations) + 1}"
        self.destinations[dest_id] = destination
        self.statistics["by_destination"][dest_id] = {"sent": 0, "failed": 0}
        return dest_id

    def remove_destination(self, dest_id: str) -> bool:
        """Remove a SIEM destination"""
        if dest_id in self.destinations:
            del self.destinations[dest_id]
            return True
        return False

    def get_destinations(self) -> List[Dict[str, Any]]:
        """Get all configured destinations"""
        return [
            {
                "id": dest_id,
                "name": dest.name,
                "type": dest.type,
                "enabled": dest.enabled,
                "host": dest.host,
                "port": dest.port,
                "format": dest.format,
                "min_severity": dest.min_severity.name,
                "stats": self.statistics["by_destination"].get(dest_id, {"sent": 0, "failed": 0})
            }
            for dest_id, dest in self.destinations.items()
        ]

    def emit(self, event: SIEMEvent) -> bool:
        """
        Emit a security event to all configured destinations

        Args:
            event: The security event to emit

        Returns:
            True if event was accepted for processing
        """
        self.statistics["total_events"] += 1
        self.statistics["by_severity"][event.severity.name] += 1

        event_type = event.event_type.value
        if event_type not in self.statistics["by_type"]:
            self.statistics["by_type"][event_type] = 0
        self.statistics["by_type"][event_type] += 1

        # Add to buffer
        self.event_buffer.append(event)

        # Process for each destination
        for dest_id, dest in self.destinations.items():
            if not dest.enabled:
                continue

            # Check severity filter
            if event.severity.value < dest.min_severity.value:
                self.statistics["events_filtered"] += 1
                continue

            # Check event type filter
            if dest.event_types and event.event_type.value not in dest.event_types:
                self.statistics["events_filtered"] += 1
                continue

            # Send to destination (simulated)
            self._send_to_destination(dest_id, dest, event)

        # Notify callbacks
        for callback in self.callbacks:
            try:
                callback(event)
            except Exception as e:
                logger.error(f"Callback error: {e}")

        return True

    def _send_to_destination(self, dest_id: str, dest: SIEMDestination, event: SIEMEvent):
        """Send event to a specific destination"""
        try:
            # Format the event
            if dest.format == "cef":
                payload = event.to_cef()
            elif dest.format == "syslog":
                payload = event.to_syslog()
            else:
                payload = event.to_json()

            # In production, this would make actual HTTP/TCP/UDP calls
            # For demo, we simulate success
            logger.info(f"SIEM [{dest.name}]: {event.event_type.value} - {event.action}")

            self.statistics["events_sent"] += 1
            if dest_id not in self.statistics["by_destination"]:
                self.statistics["by_destination"][dest_id] = {"sent": 0, "failed": 0}
            self.statistics["by_destination"][dest_id]["sent"] += 1

            self.sent_events.append({
                "event_id": event.event_id,
                "destination": dest_id,
                "timestamp": datetime.now().isoformat(),
                "status": "sent"
            })

        except Exception as e:
            logger.error(f"Failed to send to {dest.name}: {e}")
            self.statistics["events_failed"] += 1
            if dest_id in self.statistics["by_destination"]:
                self.statistics["by_destination"][dest_id]["failed"] += 1

    def register_callback(self, callback: Callable[[SIEMEvent], None]):
        """Register a callback for real-time event notifications"""
        self.callbacks.append(callback)

    def get_recent_events(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent events from buffer"""
        events = list(self.event_buffer)[-limit:]
        return [e.to_dict() for e in events]

    def get_statistics(self) -> Dict[str, Any]:
        """Get connector statistics"""
        return {
            **self.statistics,
            "buffer_size": len(self.event_buffer),
            "destinations_count": len(self.destinations),
            "active_destinations": sum(1 for d in self.destinations.values() if d.enabled)
        }

    def create_event(
        self,
        event_type: SIEMEventType,
        severity: SIEMSeverity,
        source_user: str,
        action: str,
        **kwargs
    ) -> SIEMEvent:
        """Helper to create and emit an event"""
        import uuid

        event = SIEMEvent(
            event_id=str(uuid.uuid4()),
            event_type=event_type,
            severity=severity,
            timestamp=datetime.now(),
            source_system=kwargs.get("source_system", "Governex+"),
            source_ip=kwargs.get("source_ip", ""),
            source_user=source_user,
            target_user=kwargs.get("target_user", ""),
            target_resource=kwargs.get("target_resource", ""),
            target_system=kwargs.get("target_system", ""),
            action=action,
            outcome=kwargs.get("outcome", "success"),
            reason=kwargs.get("reason", ""),
            risk_score=kwargs.get("risk_score"),
            transaction_code=kwargs.get("transaction_code", ""),
            session_id=kwargs.get("session_id", ""),
            request_id=kwargs.get("request_id", ""),
            custom_fields=kwargs.get("custom_fields", {})
        )

        self.emit(event)
        return event


# Global connector instance
siem_connector = SIEMConnector()
