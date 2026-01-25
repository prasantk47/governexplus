"""
Firefighter Live Monitoring Module

Provides real-time monitoring, alerting, and session tracking
for emergency access sessions.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from enum import Enum
from collections import defaultdict
import uuid
import asyncio


class AlertSeverity(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    HIGH = "high"
    CRITICAL = "critical"


class AlertType(Enum):
    """Types of monitoring alerts"""
    SESSION_STARTED = "session_started"
    SESSION_EXTENDED = "session_extended"
    SESSION_EXPIRING = "session_expiring"
    SESSION_EXPIRED = "session_expired"
    SENSITIVE_ACTION = "sensitive_action"
    RESTRICTED_TCODE = "restricted_tcode"
    HIGH_ACTIVITY = "high_activity"
    UNUSUAL_PATTERN = "unusual_pattern"
    POLICY_VIOLATION = "policy_violation"
    REVIEW_OVERDUE = "review_overdue"
    CONCURRENT_SESSIONS = "concurrent_sessions"


@dataclass
class MonitoringAlert:
    """A monitoring alert for firefighter activity"""
    alert_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    alert_type: AlertType = AlertType.SESSION_STARTED
    severity: AlertSeverity = AlertSeverity.INFO
    session_id: str = ""
    user_id: str = ""
    firefighter_id: str = ""
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    acknowledged: bool = False
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None

    def to_dict(self) -> Dict:
        return {
            "alert_id": self.alert_id,
            "alert_type": self.alert_type.value,
            "severity": self.severity.value,
            "session_id": self.session_id,
            "user_id": self.user_id,
            "firefighter_id": self.firefighter_id,
            "message": self.message,
            "details": self.details,
            "timestamp": self.timestamp.isoformat(),
            "acknowledged": self.acknowledged,
            "acknowledged_by": self.acknowledged_by,
            "acknowledged_at": self.acknowledged_at.isoformat() if self.acknowledged_at else None
        }


@dataclass
class SessionActivity:
    """Real-time activity within a firefighter session"""
    activity_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str = ""
    timestamp: datetime = field(default_factory=datetime.now)

    # Activity details
    action_type: str = ""  # tcode, function_module, table_access, etc.
    action_code: str = ""  # The actual tcode or function
    action_description: str = ""
    target_object: str = ""  # Table, document, etc.

    # Risk assessment
    is_sensitive: bool = False
    is_restricted: bool = False
    risk_level: str = "low"
    risk_reason: Optional[str] = None

    # Context
    client: str = ""
    ip_address: str = ""
    terminal: str = ""
    program: str = ""

    def to_dict(self) -> Dict:
        return {
            "activity_id": self.activity_id,
            "session_id": self.session_id,
            "timestamp": self.timestamp.isoformat(),
            "action_type": self.action_type,
            "action_code": self.action_code,
            "action_description": self.action_description,
            "target_object": self.target_object,
            "is_sensitive": self.is_sensitive,
            "is_restricted": self.is_restricted,
            "risk_level": self.risk_level,
            "risk_reason": self.risk_reason,
            "client": self.client,
            "ip_address": self.ip_address
        }


@dataclass
class SessionSnapshot:
    """Point-in-time snapshot of a session's state"""
    snapshot_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    session_id: str = ""
    captured_at: datetime = field(default_factory=datetime.now)

    # Session state
    user_id: str = ""
    firefighter_id: str = ""
    target_system: str = ""
    status: str = "active"

    # Timing
    started_at: datetime = None
    expires_at: datetime = None
    time_remaining_minutes: int = 0
    duration_minutes: int = 0

    # Activity summary
    total_actions: int = 0
    sensitive_actions: int = 0
    restricted_actions: int = 0
    last_activity: Optional[datetime] = None

    # Health indicators
    alert_count: int = 0
    unacknowledged_alerts: int = 0
    risk_score: float = 0.0

    def to_dict(self) -> Dict:
        return {
            "snapshot_id": self.snapshot_id,
            "session_id": self.session_id,
            "captured_at": self.captured_at.isoformat(),
            "user_id": self.user_id,
            "firefighter_id": self.firefighter_id,
            "target_system": self.target_system,
            "status": self.status,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "time_remaining_minutes": self.time_remaining_minutes,
            "duration_minutes": self.duration_minutes,
            "total_actions": self.total_actions,
            "sensitive_actions": self.sensitive_actions,
            "restricted_actions": self.restricted_actions,
            "last_activity": self.last_activity.isoformat() if self.last_activity else None,
            "alert_count": self.alert_count,
            "risk_score": self.risk_score
        }


class FirefighterMonitor:
    """
    Real-time monitoring engine for firefighter sessions.

    Provides:
    - Live session tracking and activity logging
    - Alert generation for policy violations
    - Session health monitoring
    - Real-time dashboards data
    """

    # Restricted TCodes that trigger alerts
    RESTRICTED_TCODES = {
        "SE38": "ABAP Editor - Code execution",
        "SA38": "ABAP Reporting - Program execution",
        "SM59": "RFC Destinations - External connections",
        "STMS": "Transport Management - Production changes",
        "SCC4": "Client Administration - Client settings",
        "SE16": "Data Browser - Direct table access",
        "SE16N": "Data Browser - Direct table access",
        "SM21": "System Log - Log manipulation",
        "SM37": "Job Overview - Background jobs",
        "SU01": "User Maintenance - User administration",
        "PFCG": "Role Maintenance - Authorization changes",
        "SE11": "ABAP Dictionary - Database changes",
        "SE80": "Object Navigator - Development"
    }

    # Sensitive tables
    SENSITIVE_TABLES = {
        "USR02": "User master passwords",
        "BSEG": "Accounting document segment",
        "BKPF": "Accounting document header",
        "EKKO": "Purchasing document header",
        "EKPO": "Purchasing document item",
        "PA0008": "HR Basic Pay",
        "PA0001": "HR Organizational Assignment"
    }

    def __init__(self, policy_config: Dict = None):
        self.policy_config = policy_config or self._default_policy()

        self.alerts: Dict[str, MonitoringAlert] = {}
        self.activities: Dict[str, List[SessionActivity]] = defaultdict(list)
        self.session_snapshots: Dict[str, List[SessionSnapshot]] = defaultdict(list)

        # Alert subscribers
        self.alert_callbacks: List[Callable] = []

        # Session tracking
        self.active_sessions: Dict[str, Dict] = {}

    def _default_policy(self) -> Dict:
        """Default monitoring policy configuration"""
        return {
            "alert_on_session_start": True,
            "alert_before_expiry_minutes": 15,
            "max_session_duration_hours": 4,
            "max_concurrent_sessions_per_user": 1,
            "high_activity_threshold": 50,  # Actions per hour
            "restricted_tcode_alert_severity": "high",
            "sensitive_table_alert_severity": "warning",
            "auto_extend_allowed": True,
            "max_extensions": 2,
            "require_immediate_review": False,
            "snapshot_interval_minutes": 5
        }

    def subscribe_to_alerts(self, callback: Callable):
        """Subscribe to real-time alert notifications"""
        self.alert_callbacks.append(callback)

    def _notify_alert(self, alert: MonitoringAlert):
        """Notify all subscribers of a new alert"""
        for callback in self.alert_callbacks:
            try:
                callback(alert)
            except Exception:
                pass  # Don't let callback errors affect monitoring

    def register_session(
        self,
        session_id: str,
        user_id: str,
        firefighter_id: str,
        target_system: str,
        started_at: datetime,
        expires_at: datetime
    ):
        """Register a new session for monitoring"""
        self.active_sessions[session_id] = {
            "session_id": session_id,
            "user_id": user_id,
            "firefighter_id": firefighter_id,
            "target_system": target_system,
            "started_at": started_at,
            "expires_at": expires_at,
            "status": "active"
        }

        # Generate session start alert
        if self.policy_config.get("alert_on_session_start"):
            alert = MonitoringAlert(
                alert_type=AlertType.SESSION_STARTED,
                severity=AlertSeverity.INFO,
                session_id=session_id,
                user_id=user_id,
                firefighter_id=firefighter_id,
                message=f"Firefighter session started for {user_id} using {firefighter_id}",
                details={
                    "target_system": target_system,
                    "expires_at": expires_at.isoformat()
                }
            )
            self._add_alert(alert)

        # Check for concurrent sessions
        self._check_concurrent_sessions(user_id, session_id)

    def unregister_session(self, session_id: str, ended_reason: str = "normal"):
        """Unregister a session from monitoring"""
        if session_id in self.active_sessions:
            self.active_sessions[session_id]["status"] = "ended"
            self.active_sessions[session_id]["ended_at"] = datetime.now()
            self.active_sessions[session_id]["ended_reason"] = ended_reason

    def log_activity(
        self,
        session_id: str,
        action_type: str,
        action_code: str,
        action_description: str = "",
        target_object: str = "",
        **kwargs
    ) -> SessionActivity:
        """
        Log an activity within a firefighter session.

        Automatically assesses risk and generates alerts as needed.
        """
        # Determine sensitivity
        is_restricted = action_code.upper() in self.RESTRICTED_TCODES
        is_sensitive = (
            is_restricted or
            target_object.upper() in self.SENSITIVE_TABLES
        )

        # Determine risk level
        risk_level = "low"
        risk_reason = None

        if action_code.upper() in self.RESTRICTED_TCODES:
            risk_level = "high"
            risk_reason = self.RESTRICTED_TCODES[action_code.upper()]
        elif target_object.upper() in self.SENSITIVE_TABLES:
            risk_level = "medium"
            risk_reason = self.SENSITIVE_TABLES[target_object.upper()]

        activity = SessionActivity(
            session_id=session_id,
            action_type=action_type,
            action_code=action_code,
            action_description=action_description,
            target_object=target_object,
            is_sensitive=is_sensitive,
            is_restricted=is_restricted,
            risk_level=risk_level,
            risk_reason=risk_reason,
            **kwargs
        )

        self.activities[session_id].append(activity)

        # Generate alerts for restricted actions
        if is_restricted:
            session = self.active_sessions.get(session_id, {})
            alert = MonitoringAlert(
                alert_type=AlertType.RESTRICTED_TCODE,
                severity=AlertSeverity(self.policy_config.get("restricted_tcode_alert_severity", "high")),
                session_id=session_id,
                user_id=session.get("user_id", ""),
                firefighter_id=session.get("firefighter_id", ""),
                message=f"Restricted transaction {action_code} executed",
                details={
                    "action_code": action_code,
                    "risk_reason": risk_reason,
                    "target_object": target_object
                }
            )
            self._add_alert(alert)

        # Check for high activity
        self._check_activity_rate(session_id)

        return activity

    def _add_alert(self, alert: MonitoringAlert):
        """Add an alert and notify subscribers"""
        self.alerts[alert.alert_id] = alert
        self._notify_alert(alert)

    def _check_concurrent_sessions(self, user_id: str, current_session_id: str):
        """Check for concurrent sessions by the same user"""
        max_concurrent = self.policy_config.get("max_concurrent_sessions_per_user", 1)

        concurrent = [
            s for s in self.active_sessions.values()
            if s["user_id"] == user_id
            and s["status"] == "active"
            and s["session_id"] != current_session_id
        ]

        if len(concurrent) >= max_concurrent:
            alert = MonitoringAlert(
                alert_type=AlertType.CONCURRENT_SESSIONS,
                severity=AlertSeverity.WARNING,
                session_id=current_session_id,
                user_id=user_id,
                message=f"User {user_id} has multiple concurrent firefighter sessions",
                details={
                    "session_count": len(concurrent) + 1,
                    "session_ids": [s["session_id"] for s in concurrent] + [current_session_id]
                }
            )
            self._add_alert(alert)

    def _check_activity_rate(self, session_id: str):
        """Check if activity rate exceeds threshold"""
        threshold = self.policy_config.get("high_activity_threshold", 50)

        # Count activities in last hour
        one_hour_ago = datetime.now() - timedelta(hours=1)
        recent_activities = [
            a for a in self.activities.get(session_id, [])
            if a.timestamp >= one_hour_ago
        ]

        if len(recent_activities) >= threshold:
            session = self.active_sessions.get(session_id, {})

            # Don't alert repeatedly
            existing_alerts = [
                a for a in self.alerts.values()
                if a.session_id == session_id
                and a.alert_type == AlertType.HIGH_ACTIVITY
                and (datetime.now() - a.timestamp).total_seconds() < 3600
            ]

            if not existing_alerts:
                alert = MonitoringAlert(
                    alert_type=AlertType.HIGH_ACTIVITY,
                    severity=AlertSeverity.WARNING,
                    session_id=session_id,
                    user_id=session.get("user_id", ""),
                    firefighter_id=session.get("firefighter_id", ""),
                    message=f"High activity detected: {len(recent_activities)} actions in the last hour",
                    details={
                        "action_count": len(recent_activities),
                        "threshold": threshold
                    }
                )
                self._add_alert(alert)

    def check_expiring_sessions(self) -> List[MonitoringAlert]:
        """Check for sessions about to expire and generate alerts"""
        alerts = []
        warning_minutes = self.policy_config.get("alert_before_expiry_minutes", 15)

        for session in self.active_sessions.values():
            if session["status"] != "active":
                continue

            time_remaining = (session["expires_at"] - datetime.now()).total_seconds() / 60

            if 0 < time_remaining <= warning_minutes:
                # Check if we already alerted
                existing = [
                    a for a in self.alerts.values()
                    if a.session_id == session["session_id"]
                    and a.alert_type == AlertType.SESSION_EXPIRING
                ]

                if not existing:
                    alert = MonitoringAlert(
                        alert_type=AlertType.SESSION_EXPIRING,
                        severity=AlertSeverity.WARNING,
                        session_id=session["session_id"],
                        user_id=session["user_id"],
                        firefighter_id=session["firefighter_id"],
                        message=f"Session expiring in {int(time_remaining)} minutes",
                        details={"minutes_remaining": int(time_remaining)}
                    )
                    self._add_alert(alert)
                    alerts.append(alert)

            elif time_remaining <= 0:
                # Session expired
                alert = MonitoringAlert(
                    alert_type=AlertType.SESSION_EXPIRED,
                    severity=AlertSeverity.HIGH,
                    session_id=session["session_id"],
                    user_id=session["user_id"],
                    firefighter_id=session["firefighter_id"],
                    message="Session has expired",
                    details={"expired_at": session["expires_at"].isoformat()}
                )
                self._add_alert(alert)
                alerts.append(alert)
                session["status"] = "expired"

        return alerts

    def capture_snapshot(self, session_id: str) -> SessionSnapshot:
        """Capture a point-in-time snapshot of session state"""
        session = self.active_sessions.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        activities = self.activities.get(session_id, [])
        session_alerts = [a for a in self.alerts.values() if a.session_id == session_id]

        now = datetime.now()
        time_remaining = max(0, (session["expires_at"] - now).total_seconds() / 60)
        duration = (now - session["started_at"]).total_seconds() / 60

        snapshot = SessionSnapshot(
            session_id=session_id,
            user_id=session["user_id"],
            firefighter_id=session["firefighter_id"],
            target_system=session["target_system"],
            status=session["status"],
            started_at=session["started_at"],
            expires_at=session["expires_at"],
            time_remaining_minutes=int(time_remaining),
            duration_minutes=int(duration),
            total_actions=len(activities),
            sensitive_actions=len([a for a in activities if a.is_sensitive]),
            restricted_actions=len([a for a in activities if a.is_restricted]),
            last_activity=activities[-1].timestamp if activities else None,
            alert_count=len(session_alerts),
            unacknowledged_alerts=len([a for a in session_alerts if not a.acknowledged]),
            risk_score=self._calculate_session_risk(session_id)
        )

        self.session_snapshots[session_id].append(snapshot)
        return snapshot

    def _calculate_session_risk(self, session_id: str) -> float:
        """Calculate overall risk score for a session"""
        activities = self.activities.get(session_id, [])
        if not activities:
            return 0.0

        base_score = 0.0

        # Add points for restricted actions
        restricted_count = len([a for a in activities if a.is_restricted])
        base_score += restricted_count * 20

        # Add points for sensitive actions
        sensitive_count = len([a for a in activities if a.is_sensitive and not a.is_restricted])
        base_score += sensitive_count * 10

        # Add points for high activity
        if len(activities) > self.policy_config.get("high_activity_threshold", 50):
            base_score += 15

        # Add points for unacknowledged alerts
        unacked = len([
            a for a in self.alerts.values()
            if a.session_id == session_id and not a.acknowledged
        ])
        base_score += unacked * 5

        # Normalize to 0-100
        return min(100.0, base_score)

    def acknowledge_alert(self, alert_id: str, acknowledged_by: str) -> MonitoringAlert:
        """Acknowledge an alert"""
        alert = self.alerts.get(alert_id)
        if not alert:
            raise ValueError(f"Alert {alert_id} not found")

        alert.acknowledged = True
        alert.acknowledged_by = acknowledged_by
        alert.acknowledged_at = datetime.now()

        return alert

    def get_active_sessions_dashboard(self) -> Dict:
        """Get real-time dashboard data for active sessions"""
        active = [s for s in self.active_sessions.values() if s["status"] == "active"]

        sessions_data = []
        for session in active:
            activities = self.activities.get(session["session_id"], [])
            session_alerts = [
                a for a in self.alerts.values()
                if a.session_id == session["session_id"]
            ]

            now = datetime.now()
            time_remaining = max(0, (session["expires_at"] - now).total_seconds() / 60)

            sessions_data.append({
                "session_id": session["session_id"],
                "user_id": session["user_id"],
                "firefighter_id": session["firefighter_id"],
                "target_system": session["target_system"],
                "started_at": session["started_at"].isoformat(),
                "time_remaining_minutes": int(time_remaining),
                "activity_count": len(activities),
                "restricted_actions": len([a for a in activities if a.is_restricted]),
                "alert_count": len(session_alerts),
                "unacked_alerts": len([a for a in session_alerts if not a.acknowledged]),
                "risk_score": self._calculate_session_risk(session["session_id"])
            })

        # Sort by risk score descending
        sessions_data.sort(key=lambda x: x["risk_score"], reverse=True)

        return {
            "active_session_count": len(active),
            "total_activities": sum(len(self.activities.get(s["session_id"], [])) for s in active),
            "total_alerts": len([a for a in self.alerts.values() if not a.acknowledged]),
            "sessions": sessions_data,
            "timestamp": datetime.now().isoformat()
        }

    def get_alerts(
        self,
        session_id: str = None,
        severity: AlertSeverity = None,
        acknowledged: bool = None,
        limit: int = 100
    ) -> List[MonitoringAlert]:
        """Get alerts with filters"""
        results = []

        for alert in sorted(self.alerts.values(), key=lambda a: a.timestamp, reverse=True):
            if session_id and alert.session_id != session_id:
                continue
            if severity and alert.severity != severity:
                continue
            if acknowledged is not None and alert.acknowledged != acknowledged:
                continue

            results.append(alert)
            if len(results) >= limit:
                break

        return results

    def get_session_activities(
        self,
        session_id: str,
        start_time: datetime = None,
        risk_level: str = None,
        limit: int = 500
    ) -> List[SessionActivity]:
        """Get activities for a session with filters"""
        activities = self.activities.get(session_id, [])

        if start_time:
            activities = [a for a in activities if a.timestamp >= start_time]

        if risk_level:
            activities = [a for a in activities if a.risk_level == risk_level]

        return sorted(activities, key=lambda a: a.timestamp, reverse=True)[:limit]

    def get_session_timeline(self, session_id: str) -> List[Dict]:
        """Get chronological timeline of session events"""
        timeline = []

        # Add activities
        for activity in self.activities.get(session_id, []):
            timeline.append({
                "type": "activity",
                "timestamp": activity.timestamp,
                "data": activity.to_dict()
            })

        # Add alerts
        for alert in self.alerts.values():
            if alert.session_id == session_id:
                timeline.append({
                    "type": "alert",
                    "timestamp": alert.timestamp,
                    "data": alert.to_dict()
                })

        # Add snapshots
        for snapshot in self.session_snapshots.get(session_id, []):
            timeline.append({
                "type": "snapshot",
                "timestamp": snapshot.captured_at,
                "data": snapshot.to_dict()
            })

        # Sort by timestamp
        timeline.sort(key=lambda x: x["timestamp"])

        return timeline

    def get_monitoring_statistics(self) -> Dict:
        """Get overall monitoring statistics"""
        all_activities = []
        for activities in self.activities.values():
            all_activities.extend(activities)

        return {
            "active_sessions": len([s for s in self.active_sessions.values() if s["status"] == "active"]),
            "total_sessions_monitored": len(self.active_sessions),
            "total_activities_logged": len(all_activities),
            "restricted_actions": len([a for a in all_activities if a.is_restricted]),
            "sensitive_actions": len([a for a in all_activities if a.is_sensitive]),
            "total_alerts": len(self.alerts),
            "unacknowledged_alerts": len([a for a in self.alerts.values() if not a.acknowledged]),
            "alerts_by_severity": {
                "critical": len([a for a in self.alerts.values() if a.severity == AlertSeverity.CRITICAL]),
                "high": len([a for a in self.alerts.values() if a.severity == AlertSeverity.HIGH]),
                "warning": len([a for a in self.alerts.values() if a.severity == AlertSeverity.WARNING]),
                "info": len([a for a in self.alerts.values() if a.severity == AlertSeverity.INFO])
            },
            "alerts_by_type": {
                t.value: len([a for a in self.alerts.values() if a.alert_type == t])
                for t in AlertType
            }
        }
