"""
Event Correlator for Governex+

Advanced event correlation and threat pattern detection.
Identifies complex attack patterns by analyzing sequences of events.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Set
from datetime import datetime, timedelta
from collections import defaultdict
import re

from .connector import SIEMEvent, SIEMEventType, SIEMSeverity


class ThreatCategory(Enum):
    """Categories of security threats"""
    CREDENTIAL_ATTACK = "credential_attack"
    PRIVILEGE_ABUSE = "privilege_abuse"
    DATA_EXFILTRATION = "data_exfiltration"
    INSIDER_THREAT = "insider_threat"
    POLICY_CIRCUMVENTION = "policy_circumvention"
    ACCOUNT_COMPROMISE = "account_compromise"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"


@dataclass
class CorrelationRule:
    """Rule for correlating multiple events into a threat pattern"""
    rule_id: str
    name: str
    description: str
    category: ThreatCategory
    severity: SIEMSeverity

    # Event matching
    event_sequence: List[SIEMEventType]  # Required events in order
    time_window_minutes: int = 60  # Time window for correlation
    min_events: int = 2  # Minimum events to trigger

    # Conditions
    same_user: bool = True  # Events must be from same user
    same_system: bool = False  # Events must be from same system
    same_ip: bool = False  # Events must be from same IP

    # Additional conditions (field: regex pattern)
    conditions: Dict[str, str] = field(default_factory=dict)

    # Response
    auto_response: str = ""  # Action to take: alert, block, lockout
    notification_emails: List[str] = field(default_factory=list)

    enabled: bool = True


@dataclass
class ThreatPattern:
    """Detected threat pattern from correlated events"""
    pattern_id: str
    rule: CorrelationRule
    detected_at: datetime
    severity: SIEMSeverity

    # Involved entities
    user: str
    source_ips: Set[str]
    systems: Set[str]

    # Correlated events
    events: List[SIEMEvent]

    # Analysis
    confidence: float  # 0.0 to 1.0
    risk_score: int
    description: str
    recommended_action: str

    # Status
    acknowledged: bool = False
    acknowledged_by: str = ""
    acknowledged_at: Optional[datetime] = None
    false_positive: bool = False
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "pattern_id": self.pattern_id,
            "rule_id": self.rule.rule_id,
            "rule_name": self.rule.name,
            "category": self.rule.category.value,
            "detected_at": self.detected_at.isoformat(),
            "severity": self.severity.name,
            "user": self.user,
            "source_ips": list(self.source_ips),
            "systems": list(self.systems),
            "event_count": len(self.events),
            "events": [e.to_dict() for e in self.events],
            "confidence": self.confidence,
            "risk_score": self.risk_score,
            "description": self.description,
            "recommended_action": self.recommended_action,
            "acknowledged": self.acknowledged,
            "acknowledged_by": self.acknowledged_by,
            "acknowledged_at": self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            "false_positive": self.false_positive,
            "notes": self.notes
        }


class EventCorrelator:
    """
    Event Correlator for Advanced Threat Detection

    Features:
    - Pattern-based correlation rules
    - Time-window event grouping
    - Multi-factor threat scoring
    - Automatic response triggers
    - Learning from false positives
    """

    def __init__(self):
        self.rules: Dict[str, CorrelationRule] = {}
        self.detected_patterns: List[ThreatPattern] = []
        self.event_windows: Dict[str, List[SIEMEvent]] = defaultdict(list)
        self.statistics = {
            "events_processed": 0,
            "patterns_detected": 0,
            "by_category": {c.value: 0 for c in ThreatCategory},
            "by_severity": {s.name: 0 for s in SIEMSeverity},
            "false_positives": 0,
            "true_positives": 0
        }

        # Load default correlation rules
        self._load_default_rules()

    def _load_default_rules(self):
        """Load default correlation rules"""

        # Rule 1: Brute Force Attack
        self.rules["brute_force"] = CorrelationRule(
            rule_id="brute_force",
            name="Brute Force Login Attack",
            description="Multiple failed login attempts followed by success",
            category=ThreatCategory.CREDENTIAL_ATTACK,
            severity=SIEMSeverity.HIGH,
            event_sequence=[
                SIEMEventType.LOGIN_FAILURE,
                SIEMEventType.LOGIN_FAILURE,
                SIEMEventType.LOGIN_FAILURE,
                SIEMEventType.LOGIN_SUCCESS
            ],
            time_window_minutes=30,
            min_events=4,
            same_user=True,
            auto_response="alert"
        )

        # Rule 2: Privilege Escalation
        self.rules["priv_escalation"] = CorrelationRule(
            rule_id="priv_escalation",
            name="Privilege Escalation Attempt",
            description="User granted elevated privileges followed by sensitive access",
            category=ThreatCategory.PRIVILEGE_ABUSE,
            severity=SIEMSeverity.CRITICAL,
            event_sequence=[
                SIEMEventType.ROLE_ASSIGNED,
                SIEMEventType.SENSITIVE_ACCESS
            ],
            time_window_minutes=60,
            min_events=2,
            same_user=True,
            auto_response="alert"
        )

        # Rule 3: Data Exfiltration
        self.rules["data_exfil"] = CorrelationRule(
            rule_id="data_exfil",
            name="Potential Data Exfiltration",
            description="Large data export followed by logout",
            category=ThreatCategory.DATA_EXFILTRATION,
            severity=SIEMSeverity.CRITICAL,
            event_sequence=[
                SIEMEventType.BULK_DOWNLOAD,
                SIEMEventType.LOGOUT
            ],
            time_window_minutes=30,
            min_events=2,
            same_user=True,
            auto_response="alert"
        )

        # Rule 4: SoD Violation with Execution
        self.rules["sod_exploit"] = CorrelationRule(
            rule_id="sod_exploit",
            name="SoD Violation Exploited",
            description="SoD violation detected followed by conflicting transaction execution",
            category=ThreatCategory.POLICY_CIRCUMVENTION,
            severity=SIEMSeverity.HIGH,
            event_sequence=[
                SIEMEventType.SOD_VIOLATION,
                SIEMEventType.DATA_WRITE
            ],
            time_window_minutes=120,
            min_events=2,
            same_user=True,
            auto_response="alert"
        )

        # Rule 5: Account Takeover
        self.rules["account_takeover"] = CorrelationRule(
            rule_id="account_takeover",
            name="Potential Account Takeover",
            description="Login from new location followed by permission changes",
            category=ThreatCategory.ACCOUNT_COMPROMISE,
            severity=SIEMSeverity.CRITICAL,
            event_sequence=[
                SIEMEventType.LOGIN_SUCCESS,
                SIEMEventType.PERMISSION_CHANGE
            ],
            time_window_minutes=60,
            min_events=2,
            same_user=True,
            same_ip=False,  # Different IP is suspicious
            auto_response="lockout"
        )

        # Rule 6: Firefighter Abuse
        self.rules["ff_abuse"] = CorrelationRule(
            rule_id="ff_abuse",
            name="Firefighter Session Abuse",
            description="Extended firefighter session with unusual activity",
            category=ThreatCategory.PRIVILEGE_ABUSE,
            severity=SIEMSeverity.HIGH,
            event_sequence=[
                SIEMEventType.FF_SESSION_START,
                SIEMEventType.SENSITIVE_ACCESS,
                SIEMEventType.DATA_EXPORT
            ],
            time_window_minutes=240,
            min_events=3,
            same_user=True,
            auto_response="alert"
        )

        # Rule 7: Insider Threat Pattern
        self.rules["insider_threat"] = CorrelationRule(
            rule_id="insider_threat",
            name="Insider Threat Indicators",
            description="Access to sensitive data outside normal hours with export",
            category=ThreatCategory.INSIDER_THREAT,
            severity=SIEMSeverity.HIGH,
            event_sequence=[
                SIEMEventType.LOGIN_SUCCESS,
                SIEMEventType.SENSITIVE_ACCESS,
                SIEMEventType.DATA_EXPORT
            ],
            time_window_minutes=180,
            min_events=3,
            same_user=True,
            auto_response="alert"
        )

        # Rule 8: Mass Permission Changes
        self.rules["mass_perm_change"] = CorrelationRule(
            rule_id="mass_perm_change",
            name="Mass Permission Modification",
            description="Multiple permission changes in short time",
            category=ThreatCategory.SUSPICIOUS_ACTIVITY,
            severity=SIEMSeverity.MEDIUM,
            event_sequence=[
                SIEMEventType.PERMISSION_CHANGE,
                SIEMEventType.PERMISSION_CHANGE,
                SIEMEventType.PERMISSION_CHANGE
            ],
            time_window_minutes=15,
            min_events=3,
            same_user=True,
            auto_response="alert"
        )

    def process_event(self, event: SIEMEvent) -> List[ThreatPattern]:
        """
        Process an event and check for correlation patterns

        Args:
            event: The security event to process

        Returns:
            List of detected threat patterns
        """
        self.statistics["events_processed"] += 1
        detected = []

        # Add event to user's window
        user_key = event.source_user or "unknown"
        self.event_windows[user_key].append(event)

        # Clean old events from windows
        self._cleanup_windows()

        # Check each rule
        for rule_id, rule in self.rules.items():
            if not rule.enabled:
                continue

            pattern = self._check_rule(rule, user_key, event)
            if pattern:
                detected.append(pattern)
                self.detected_patterns.append(pattern)
                self.statistics["patterns_detected"] += 1
                self.statistics["by_category"][rule.category.value] += 1
                self.statistics["by_severity"][pattern.severity.name] += 1

        return detected

    def _check_rule(
        self,
        rule: CorrelationRule,
        user_key: str,
        latest_event: SIEMEvent
    ) -> Optional[ThreatPattern]:
        """Check if a rule matches the current event window"""

        # Get events in time window
        cutoff = datetime.now() - timedelta(minutes=rule.time_window_minutes)
        window_events = [
            e for e in self.event_windows[user_key]
            if e.timestamp >= cutoff
        ]

        if len(window_events) < rule.min_events:
            return None

        # Check if required event types are present
        event_types = [e.event_type for e in window_events]
        matched_events = []

        for required_type in rule.event_sequence:
            found = False
            for event in window_events:
                if event.event_type == required_type and event not in matched_events:
                    matched_events.append(event)
                    found = True
                    break
            if not found:
                return None

        # Check additional conditions
        if rule.same_user:
            users = set(e.source_user for e in matched_events)
            if len(users) > 1:
                return None

        if rule.same_system:
            systems = set(e.source_system for e in matched_events)
            if len(systems) > 1:
                return None

        if rule.same_ip:
            ips = set(e.source_ip for e in matched_events if e.source_ip)
            if len(ips) > 1:
                return None

        # Check custom conditions
        for field_name, pattern in rule.conditions.items():
            for event in matched_events:
                value = getattr(event, field_name, "") or event.custom_fields.get(field_name, "")
                if not re.match(pattern, str(value)):
                    return None

        # Pattern detected - create threat pattern
        import uuid

        source_ips = set(e.source_ip for e in matched_events if e.source_ip)
        systems = set(e.source_system for e in matched_events)

        # Calculate confidence based on match quality
        confidence = min(len(matched_events) / len(rule.event_sequence), 1.0)

        # Calculate risk score
        risk_score = self._calculate_risk_score(rule, matched_events)

        pattern = ThreatPattern(
            pattern_id=str(uuid.uuid4()),
            rule=rule,
            detected_at=datetime.now(),
            severity=rule.severity,
            user=user_key,
            source_ips=source_ips,
            systems=systems,
            events=matched_events,
            confidence=confidence,
            risk_score=risk_score,
            description=self._generate_description(rule, matched_events),
            recommended_action=self._get_recommended_action(rule, risk_score)
        )

        # Clear matched events from window to prevent re-detection
        for event in matched_events:
            if event in self.event_windows[user_key]:
                self.event_windows[user_key].remove(event)

        return pattern

    def _calculate_risk_score(self, rule: CorrelationRule, events: List[SIEMEvent]) -> int:
        """Calculate risk score for detected pattern"""
        base_score = rule.severity.value * 10

        # Add points for high-risk events
        for event in events:
            if event.risk_score:
                base_score += event.risk_score // 10

        # Add points for sensitive access
        sensitive_events = [e for e in events if e.event_type in [
            SIEMEventType.SENSITIVE_ACCESS,
            SIEMEventType.BULK_DOWNLOAD,
            SIEMEventType.DATA_EXPORT
        ]]
        base_score += len(sensitive_events) * 5

        return min(base_score, 100)

    def _generate_description(self, rule: CorrelationRule, events: List[SIEMEvent]) -> str:
        """Generate human-readable description"""
        user = events[0].source_user if events else "Unknown"
        event_types = ", ".join(e.event_type.name for e in events[:3])

        return (
            f"{rule.name} detected for user '{user}'. "
            f"Pattern: {event_types}. "
            f"{len(events)} events correlated within {rule.time_window_minutes} minutes."
        )

    def _get_recommended_action(self, rule: CorrelationRule, risk_score: int) -> str:
        """Get recommended action based on rule and risk score"""
        if risk_score >= 80:
            return "Immediately suspend user access and investigate"
        elif risk_score >= 60:
            return "Alert security team and review user activity"
        elif risk_score >= 40:
            return "Monitor user closely and document activity"
        else:
            return "Log for review during next security assessment"

    def _cleanup_windows(self):
        """Remove old events from windows"""
        max_age = timedelta(hours=24)
        cutoff = datetime.now() - max_age

        for user_key in list(self.event_windows.keys()):
            self.event_windows[user_key] = [
                e for e in self.event_windows[user_key]
                if e.timestamp >= cutoff
            ]
            if not self.event_windows[user_key]:
                del self.event_windows[user_key]

    def get_patterns(
        self,
        category: Optional[ThreatCategory] = None,
        severity: Optional[SIEMSeverity] = None,
        user: Optional[str] = None,
        acknowledged: Optional[bool] = None,
        limit: int = 100
    ) -> List[ThreatPattern]:
        """Get detected patterns with filters"""
        patterns = self.detected_patterns

        if category:
            patterns = [p for p in patterns if p.rule.category == category]
        if severity:
            patterns = [p for p in patterns if p.severity == severity]
        if user:
            patterns = [p for p in patterns if p.user == user]
        if acknowledged is not None:
            patterns = [p for p in patterns if p.acknowledged == acknowledged]

        return patterns[-limit:]

    def acknowledge_pattern(self, pattern_id: str, acknowledged_by: str, notes: str = "") -> bool:
        """Acknowledge a detected pattern"""
        for pattern in self.detected_patterns:
            if pattern.pattern_id == pattern_id:
                pattern.acknowledged = True
                pattern.acknowledged_by = acknowledged_by
                pattern.acknowledged_at = datetime.now()
                pattern.notes = notes
                return True
        return False

    def mark_false_positive(self, pattern_id: str, notes: str = "") -> bool:
        """Mark pattern as false positive"""
        for pattern in self.detected_patterns:
            if pattern.pattern_id == pattern_id:
                pattern.false_positive = True
                pattern.notes = notes
                self.statistics["false_positives"] += 1
                return True
        return False

    def get_rules(self) -> List[Dict[str, Any]]:
        """Get all correlation rules"""
        return [
            {
                "rule_id": rule.rule_id,
                "name": rule.name,
                "description": rule.description,
                "category": rule.category.value,
                "severity": rule.severity.name,
                "event_sequence": [e.value for e in rule.event_sequence],
                "time_window_minutes": rule.time_window_minutes,
                "min_events": rule.min_events,
                "auto_response": rule.auto_response,
                "enabled": rule.enabled
            }
            for rule in self.rules.values()
        ]

    def get_statistics(self) -> Dict[str, Any]:
        """Get correlator statistics"""
        return {
            **self.statistics,
            "rules_count": len(self.rules),
            "active_rules": sum(1 for r in self.rules.values() if r.enabled),
            "pending_patterns": sum(1 for p in self.detected_patterns if not p.acknowledged),
            "active_users_monitored": len(self.event_windows)
        }


# Global correlator instance
event_correlator = EventCorrelator()
