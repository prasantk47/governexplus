"""
Anomaly Detection Module

Detects unusual user behavior and access patterns
using statistical and ML-based methods.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from enum import Enum
from collections import defaultdict
import uuid
import math
import statistics


class AnomalyType(Enum):
    """Types of detected anomalies"""
    UNUSUAL_LOGIN_TIME = "unusual_login_time"
    UNUSUAL_LOCATION = "unusual_location"
    EXCESSIVE_ACTIVITY = "excessive_activity"
    UNUSUAL_TRANSACTION = "unusual_transaction"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    DATA_EXFILTRATION = "data_exfiltration"
    DORMANT_ACCOUNT_ACTIVITY = "dormant_account_activity"
    IMPOSSIBLE_TRAVEL = "impossible_travel"
    FAILED_LOGIN_SPIKE = "failed_login_spike"
    UNUSUAL_DATA_ACCESS = "unusual_data_access"


class AnomalySeverity(Enum):
    """Severity levels for anomalies"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class BehaviorBaseline:
    """Baseline behavior profile for a user"""
    user_id: str
    baseline_period_days: int = 30

    # Login patterns
    typical_login_hours: List[int] = field(default_factory=list)  # Hours of day
    typical_login_days: List[int] = field(default_factory=list)  # Days of week
    typical_locations: List[str] = field(default_factory=list)
    typical_ip_ranges: List[str] = field(default_factory=list)

    # Activity patterns
    avg_daily_transactions: float = 0.0
    std_daily_transactions: float = 0.0
    avg_session_duration_min: float = 0.0
    typical_transactions: List[str] = field(default_factory=list)

    # Data access patterns
    typical_tables_accessed: List[str] = field(default_factory=list)
    avg_records_accessed: float = 0.0
    typical_data_volume_mb: float = 0.0

    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    last_updated: datetime = field(default_factory=datetime.now)
    confidence_score: float = 0.0  # How confident in baseline

    def to_dict(self) -> Dict:
        return {
            "user_id": self.user_id,
            "baseline_period_days": self.baseline_period_days,
            "typical_login_hours": self.typical_login_hours,
            "typical_login_days": self.typical_login_days,
            "typical_locations": self.typical_locations,
            "avg_daily_transactions": round(self.avg_daily_transactions, 1),
            "typical_transactions": self.typical_transactions[:20],
            "confidence_score": round(self.confidence_score, 2),
            "last_updated": self.last_updated.isoformat()
        }


@dataclass
class AnomalyAlert:
    """A detected anomaly"""
    alert_id: str = field(default_factory=lambda: f"ANOM-{uuid.uuid4().hex[:8].upper()}")
    anomaly_type: AnomalyType = AnomalyType.UNUSUAL_LOGIN_TIME
    severity: AnomalySeverity = AnomalySeverity.MEDIUM

    # Target
    user_id: str = ""
    session_id: str = ""

    # Detection details
    description: str = ""
    detected_value: Any = None
    expected_value: Any = None
    deviation_score: float = 0.0  # How far from normal (z-score or similar)

    # Context
    timestamp: datetime = field(default_factory=datetime.now)
    location: str = ""
    ip_address: str = ""
    transaction: str = ""
    additional_context: Dict = field(default_factory=dict)

    # Status
    acknowledged: bool = False
    investigated: bool = False
    false_positive: bool = False
    resolution_notes: str = ""

    def to_dict(self) -> Dict:
        return {
            "alert_id": self.alert_id,
            "anomaly_type": self.anomaly_type.value,
            "severity": self.severity.value,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "description": self.description,
            "detected_value": str(self.detected_value),
            "expected_value": str(self.expected_value),
            "deviation_score": round(self.deviation_score, 2),
            "timestamp": self.timestamp.isoformat(),
            "location": self.location,
            "ip_address": self.ip_address,
            "transaction": self.transaction,
            "additional_context": self.additional_context,
            "acknowledged": self.acknowledged,
            "investigated": self.investigated,
            "false_positive": self.false_positive
        }


@dataclass
class ActivityEvent:
    """A user activity event for analysis"""
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = ""
    timestamp: datetime = field(default_factory=datetime.now)

    # Event details
    event_type: str = ""  # login, transaction, data_access, etc.
    transaction_code: str = ""
    action: str = ""

    # Context
    ip_address: str = ""
    location: str = ""
    device_id: str = ""
    session_id: str = ""

    # Data access
    table_accessed: str = ""
    records_count: int = 0
    data_volume_kb: float = 0.0

    # Outcome
    success: bool = True
    error_code: str = ""


class AnomalyDetector:
    """
    Behavioral Anomaly Detection Engine.

    Detects unusual patterns in user activity using:
    - Statistical analysis (z-scores, IQR)
    - Time-series analysis
    - Peer group comparison
    - Rule-based detection
    """

    # Detection thresholds
    THRESHOLDS = {
        "z_score_threshold": 2.5,  # Standard deviations from mean
        "login_hour_deviation": 3,  # Hours outside normal
        "activity_multiplier": 3.0,  # Times normal activity
        "failed_login_threshold": 5,  # Failed logins in 10 min
        "dormant_days_threshold": 30,  # Days of inactivity
        "impossible_travel_speed_kmh": 1000,  # km/h (faster than commercial flight)
    }

    # Location coordinates (simplified for demo)
    LOCATION_COORDS = {
        "New York": (40.7128, -74.0060),
        "Los Angeles": (34.0522, -118.2437),
        "London": (51.5074, -0.1278),
        "Tokyo": (35.6762, 139.6503),
        "Singapore": (1.3521, 103.8198),
        "Sydney": (-33.8688, 151.2093),
        "Frankfurt": (50.1109, 8.6821)
    }

    def __init__(self):
        self.baselines: Dict[str, BehaviorBaseline] = {}
        self.alerts: Dict[str, AnomalyAlert] = {}
        self.activity_buffer: Dict[str, List[ActivityEvent]] = defaultdict(list)

        # Peer groups for comparison
        self.peer_groups: Dict[str, List[str]] = defaultdict(list)

        # Statistics cache
        self.user_stats: Dict[str, Dict] = {}

    def build_baseline(
        self,
        user_id: str,
        historical_events: List[Dict],
        period_days: int = 30
    ) -> BehaviorBaseline:
        """
        Build a behavioral baseline from historical activity.
        """
        baseline = BehaviorBaseline(
            user_id=user_id,
            baseline_period_days=period_days
        )

        if not historical_events:
            baseline.confidence_score = 0.0
            self.baselines[user_id] = baseline
            return baseline

        # Parse events
        events = [self._parse_event(e) for e in historical_events]

        # Login time analysis
        login_events = [e for e in events if e.event_type == "login"]
        if login_events:
            hours = [e.timestamp.hour for e in login_events]
            days = [e.timestamp.weekday() for e in login_events]

            # Find typical hours (most common)
            hour_counts = defaultdict(int)
            for h in hours:
                hour_counts[h] += 1

            # Top hours covering 80% of logins
            sorted_hours = sorted(hour_counts.items(), key=lambda x: x[1], reverse=True)
            total = len(hours)
            cumulative = 0
            for hour, count in sorted_hours:
                baseline.typical_login_hours.append(hour)
                cumulative += count
                if cumulative / total >= 0.8:
                    break

            baseline.typical_login_days = list(set(days))

        # Location analysis
        locations = [e.location for e in events if e.location]
        if locations:
            loc_counts = defaultdict(int)
            for loc in locations:
                loc_counts[loc] += 1
            baseline.typical_locations = [
                loc for loc, count in sorted(loc_counts.items(), key=lambda x: x[1], reverse=True)[:5]
            ]

        # IP analysis
        ips = [e.ip_address for e in events if e.ip_address]
        baseline.typical_ip_ranges = list(set(ip.rsplit('.', 1)[0] + '.*' for ip in ips[:50]))

        # Transaction analysis
        transactions = [e for e in events if e.transaction_code]
        if transactions:
            # Daily transaction counts
            daily_counts = defaultdict(int)
            for e in transactions:
                day_key = e.timestamp.date()
                daily_counts[day_key] += 1

            if daily_counts:
                counts = list(daily_counts.values())
                baseline.avg_daily_transactions = statistics.mean(counts)
                baseline.std_daily_transactions = statistics.stdev(counts) if len(counts) > 1 else 0

            # Typical transactions
            tcode_counts = defaultdict(int)
            for e in transactions:
                tcode_counts[e.transaction_code] += 1

            baseline.typical_transactions = [
                t for t, c in sorted(tcode_counts.items(), key=lambda x: x[1], reverse=True)[:50]
            ]

        # Data access patterns
        data_events = [e for e in events if e.table_accessed]
        if data_events:
            baseline.typical_tables_accessed = list(set(e.table_accessed for e in data_events))[:30]
            baseline.avg_records_accessed = statistics.mean([e.records_count for e in data_events])
            baseline.typical_data_volume_mb = statistics.mean([e.data_volume_kb / 1024 for e in data_events])

        # Calculate confidence based on data volume
        baseline.confidence_score = min(1.0, len(events) / 100)  # More events = higher confidence
        baseline.last_updated = datetime.now()

        self.baselines[user_id] = baseline
        return baseline

    def analyze_event(self, event_data: Dict) -> List[AnomalyAlert]:
        """
        Analyze a single event for anomalies.

        Returns list of any detected anomalies.
        """
        event = self._parse_event(event_data)

        # Add to buffer for time-series analysis
        self.activity_buffer[event.user_id].append(event)

        # Keep buffer limited
        if len(self.activity_buffer[event.user_id]) > 1000:
            self.activity_buffer[event.user_id] = self.activity_buffer[event.user_id][-500:]

        # Get user baseline
        baseline = self.baselines.get(event.user_id)

        alerts = []

        # Run detection checks
        if event.event_type == "login":
            alerts.extend(self._check_login_anomalies(event, baseline))

        if event.transaction_code:
            alerts.extend(self._check_transaction_anomalies(event, baseline))

        if event.table_accessed:
            alerts.extend(self._check_data_access_anomalies(event, baseline))

        # Always check for activity volume anomalies
        alerts.extend(self._check_activity_volume(event, baseline))

        # Store alerts
        for alert in alerts:
            self.alerts[alert.alert_id] = alert

        return alerts

    def analyze_batch(self, events: List[Dict]) -> List[AnomalyAlert]:
        """Analyze a batch of events"""
        all_alerts = []
        for event_data in events:
            alerts = self.analyze_event(event_data)
            all_alerts.extend(alerts)
        return all_alerts

    def _parse_event(self, event_data: Dict) -> ActivityEvent:
        """Parse event data into ActivityEvent"""
        timestamp = event_data.get("timestamp")
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        elif not isinstance(timestamp, datetime):
            timestamp = datetime.now()

        return ActivityEvent(
            event_id=event_data.get("event_id", str(uuid.uuid4())),
            user_id=event_data.get("user_id", ""),
            timestamp=timestamp,
            event_type=event_data.get("event_type", "unknown"),
            transaction_code=event_data.get("transaction_code", ""),
            action=event_data.get("action", ""),
            ip_address=event_data.get("ip_address", ""),
            location=event_data.get("location", ""),
            device_id=event_data.get("device_id", ""),
            session_id=event_data.get("session_id", ""),
            table_accessed=event_data.get("table_accessed", ""),
            records_count=event_data.get("records_count", 0),
            data_volume_kb=event_data.get("data_volume_kb", 0),
            success=event_data.get("success", True),
            error_code=event_data.get("error_code", "")
        )

    def _check_login_anomalies(
        self,
        event: ActivityEvent,
        baseline: Optional[BehaviorBaseline]
    ) -> List[AnomalyAlert]:
        """Check for login-related anomalies"""
        alerts = []

        # Unusual login time
        if baseline and baseline.typical_login_hours:
            hour = event.timestamp.hour
            if hour not in baseline.typical_login_hours:
                # Calculate how far outside normal hours
                min_distance = min(
                    min(abs(hour - h), 24 - abs(hour - h))
                    for h in baseline.typical_login_hours
                )

                if min_distance >= self.THRESHOLDS["login_hour_deviation"]:
                    alerts.append(AnomalyAlert(
                        anomaly_type=AnomalyType.UNUSUAL_LOGIN_TIME,
                        severity=AnomalySeverity.MEDIUM if min_distance < 6 else AnomalySeverity.HIGH,
                        user_id=event.user_id,
                        session_id=event.session_id,
                        description=f"Login at unusual hour ({hour}:00)",
                        detected_value=hour,
                        expected_value=baseline.typical_login_hours,
                        deviation_score=min_distance,
                        timestamp=event.timestamp,
                        ip_address=event.ip_address,
                        location=event.location
                    ))

        # Unusual location
        if baseline and baseline.typical_locations and event.location:
            if event.location not in baseline.typical_locations:
                alerts.append(AnomalyAlert(
                    anomaly_type=AnomalyType.UNUSUAL_LOCATION,
                    severity=AnomalySeverity.HIGH,
                    user_id=event.user_id,
                    session_id=event.session_id,
                    description=f"Login from unusual location: {event.location}",
                    detected_value=event.location,
                    expected_value=baseline.typical_locations,
                    deviation_score=1.0,
                    timestamp=event.timestamp,
                    ip_address=event.ip_address,
                    location=event.location
                ))

                # Check for impossible travel
                travel_alert = self._check_impossible_travel(event, baseline)
                if travel_alert:
                    alerts.append(travel_alert)

        # Failed login spike
        failed_alert = self._check_failed_logins(event)
        if failed_alert:
            alerts.append(failed_alert)

        # Dormant account
        if baseline and not event.success:
            pass  # Would check last activity date

        return alerts

    def _check_impossible_travel(
        self,
        event: ActivityEvent,
        baseline: BehaviorBaseline
    ) -> Optional[AnomalyAlert]:
        """Check for impossible travel (login from distant locations in short time)"""
        # Get recent logins for user
        recent_events = [
            e for e in self.activity_buffer.get(event.user_id, [])
            if e.event_type == "login"
            and e.location
            and (event.timestamp - e.timestamp).total_seconds() < 3600 * 6  # Within 6 hours
            and e.event_id != event.event_id
        ]

        if not recent_events or not event.location:
            return None

        for prev_event in recent_events:
            # Calculate distance
            if prev_event.location in self.LOCATION_COORDS and event.location in self.LOCATION_COORDS:
                coord1 = self.LOCATION_COORDS[prev_event.location]
                coord2 = self.LOCATION_COORDS[event.location]
                distance = self._haversine_distance(coord1, coord2)

                # Calculate time difference
                time_diff_hours = abs((event.timestamp - prev_event.timestamp).total_seconds()) / 3600

                if time_diff_hours > 0:
                    speed = distance / time_diff_hours

                    if speed > self.THRESHOLDS["impossible_travel_speed_kmh"]:
                        return AnomalyAlert(
                            anomaly_type=AnomalyType.IMPOSSIBLE_TRAVEL,
                            severity=AnomalySeverity.CRITICAL,
                            user_id=event.user_id,
                            session_id=event.session_id,
                            description=f"Impossible travel: {prev_event.location} to {event.location} in {time_diff_hours:.1f} hours",
                            detected_value=f"{speed:.0f} km/h",
                            expected_value=f"< {self.THRESHOLDS['impossible_travel_speed_kmh']} km/h",
                            deviation_score=speed / self.THRESHOLDS["impossible_travel_speed_kmh"],
                            timestamp=event.timestamp,
                            ip_address=event.ip_address,
                            location=event.location,
                            additional_context={
                                "previous_location": prev_event.location,
                                "distance_km": round(distance, 0),
                                "time_hours": round(time_diff_hours, 2)
                            }
                        )

        return None

    def _haversine_distance(self, coord1: Tuple[float, float], coord2: Tuple[float, float]) -> float:
        """Calculate distance between two coordinates in km"""
        R = 6371  # Earth's radius in km

        lat1, lon1 = math.radians(coord1[0]), math.radians(coord1[1])
        lat2, lon2 = math.radians(coord2[0]), math.radians(coord2[1])

        dlat = lat2 - lat1
        dlon = lon2 - lon1

        a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
        c = 2 * math.asin(math.sqrt(a))

        return R * c

    def _check_failed_logins(self, event: ActivityEvent) -> Optional[AnomalyAlert]:
        """Check for spike in failed logins"""
        if event.success:
            return None

        # Count recent failed logins
        ten_min_ago = event.timestamp - timedelta(minutes=10)
        recent_failed = [
            e for e in self.activity_buffer.get(event.user_id, [])
            if e.event_type == "login"
            and not e.success
            and e.timestamp >= ten_min_ago
        ]

        if len(recent_failed) >= self.THRESHOLDS["failed_login_threshold"]:
            return AnomalyAlert(
                anomaly_type=AnomalyType.FAILED_LOGIN_SPIKE,
                severity=AnomalySeverity.HIGH,
                user_id=event.user_id,
                session_id=event.session_id,
                description=f"{len(recent_failed)} failed login attempts in 10 minutes",
                detected_value=len(recent_failed),
                expected_value=f"< {self.THRESHOLDS['failed_login_threshold']}",
                deviation_score=len(recent_failed) / self.THRESHOLDS["failed_login_threshold"],
                timestamp=event.timestamp,
                ip_address=event.ip_address,
                additional_context={
                    "failed_count": len(recent_failed),
                    "unique_ips": len(set(e.ip_address for e in recent_failed))
                }
            )

        return None

    def _check_transaction_anomalies(
        self,
        event: ActivityEvent,
        baseline: Optional[BehaviorBaseline]
    ) -> List[AnomalyAlert]:
        """Check for unusual transaction patterns"""
        alerts = []

        # Unusual transaction type
        if baseline and baseline.typical_transactions:
            if event.transaction_code and event.transaction_code not in baseline.typical_transactions:
                # Check if it's a sensitive transaction
                sensitive_tcodes = ["SE38", "SA38", "SM59", "SU01", "PFCG", "SE16N", "SE11"]
                is_sensitive = event.transaction_code.upper() in sensitive_tcodes

                alerts.append(AnomalyAlert(
                    anomaly_type=AnomalyType.UNUSUAL_TRANSACTION,
                    severity=AnomalySeverity.HIGH if is_sensitive else AnomalySeverity.MEDIUM,
                    user_id=event.user_id,
                    session_id=event.session_id,
                    description=f"Unusual transaction: {event.transaction_code}",
                    detected_value=event.transaction_code,
                    expected_value=f"One of {len(baseline.typical_transactions)} typical transactions",
                    deviation_score=1.0 if is_sensitive else 0.5,
                    timestamp=event.timestamp,
                    transaction=event.transaction_code,
                    additional_context={"is_sensitive": is_sensitive}
                ))

        return alerts

    def _check_data_access_anomalies(
        self,
        event: ActivityEvent,
        baseline: Optional[BehaviorBaseline]
    ) -> List[AnomalyAlert]:
        """Check for unusual data access patterns"""
        alerts = []

        # Unusual table access
        if baseline and baseline.typical_tables_accessed:
            if event.table_accessed and event.table_accessed not in baseline.typical_tables_accessed:
                sensitive_tables = ["USR02", "PA0008", "BSEG", "BKPF"]
                is_sensitive = event.table_accessed.upper() in sensitive_tables

                alerts.append(AnomalyAlert(
                    anomaly_type=AnomalyType.UNUSUAL_DATA_ACCESS,
                    severity=AnomalySeverity.HIGH if is_sensitive else AnomalySeverity.MEDIUM,
                    user_id=event.user_id,
                    session_id=event.session_id,
                    description=f"Access to unusual table: {event.table_accessed}",
                    detected_value=event.table_accessed,
                    expected_value=baseline.typical_tables_accessed[:10],
                    deviation_score=1.0,
                    timestamp=event.timestamp,
                    transaction=event.transaction_code,
                    additional_context={
                        "records_accessed": event.records_count,
                        "is_sensitive_table": is_sensitive
                    }
                ))

        # Excessive data volume
        if baseline and baseline.avg_records_accessed > 0:
            if event.records_count > baseline.avg_records_accessed * 10:
                alerts.append(AnomalyAlert(
                    anomaly_type=AnomalyType.DATA_EXFILTRATION,
                    severity=AnomalySeverity.CRITICAL,
                    user_id=event.user_id,
                    session_id=event.session_id,
                    description=f"Excessive data access: {event.records_count} records",
                    detected_value=event.records_count,
                    expected_value=f"~{baseline.avg_records_accessed:.0f} records (avg)",
                    deviation_score=event.records_count / baseline.avg_records_accessed,
                    timestamp=event.timestamp,
                    transaction=event.transaction_code,
                    additional_context={
                        "table": event.table_accessed,
                        "multiple_of_normal": round(event.records_count / baseline.avg_records_accessed, 1)
                    }
                ))

        return alerts

    def _check_activity_volume(
        self,
        event: ActivityEvent,
        baseline: Optional[BehaviorBaseline]
    ) -> List[AnomalyAlert]:
        """Check for unusual activity volume"""
        alerts = []

        if not baseline or baseline.avg_daily_transactions == 0:
            return alerts

        # Count today's transactions
        today = event.timestamp.date()
        today_events = [
            e for e in self.activity_buffer.get(event.user_id, [])
            if e.timestamp.date() == today and e.transaction_code
        ]

        if len(today_events) > baseline.avg_daily_transactions * self.THRESHOLDS["activity_multiplier"]:
            # Calculate z-score
            if baseline.std_daily_transactions > 0:
                z_score = (len(today_events) - baseline.avg_daily_transactions) / baseline.std_daily_transactions
            else:
                z_score = self.THRESHOLDS["activity_multiplier"]

            if z_score >= self.THRESHOLDS["z_score_threshold"]:
                alerts.append(AnomalyAlert(
                    anomaly_type=AnomalyType.EXCESSIVE_ACTIVITY,
                    severity=AnomalySeverity.HIGH if z_score > 4 else AnomalySeverity.MEDIUM,
                    user_id=event.user_id,
                    session_id=event.session_id,
                    description=f"Excessive activity: {len(today_events)} transactions today",
                    detected_value=len(today_events),
                    expected_value=f"{baseline.avg_daily_transactions:.0f} ± {baseline.std_daily_transactions:.0f}",
                    deviation_score=z_score,
                    timestamp=event.timestamp,
                    additional_context={
                        "z_score": round(z_score, 2),
                        "normal_avg": round(baseline.avg_daily_transactions, 1)
                    }
                ))

        return alerts

    def get_alerts(
        self,
        user_id: str = None,
        anomaly_type: AnomalyType = None,
        severity: AnomalySeverity = None,
        acknowledged: bool = None,
        start_time: datetime = None,
        limit: int = 100
    ) -> List[AnomalyAlert]:
        """Get alerts with filters"""
        results = []

        for alert in sorted(self.alerts.values(), key=lambda a: a.timestamp, reverse=True):
            if user_id and alert.user_id != user_id:
                continue
            if anomaly_type and alert.anomaly_type != anomaly_type:
                continue
            if severity and alert.severity != severity:
                continue
            if acknowledged is not None and alert.acknowledged != acknowledged:
                continue
            if start_time and alert.timestamp < start_time:
                continue

            results.append(alert)
            if len(results) >= limit:
                break

        return results

    def acknowledge_alert(self, alert_id: str, notes: str = "") -> AnomalyAlert:
        """Acknowledge an alert"""
        alert = self.alerts.get(alert_id)
        if not alert:
            raise ValueError(f"Alert {alert_id} not found")

        alert.acknowledged = True
        alert.resolution_notes = notes
        return alert

    def mark_false_positive(self, alert_id: str, notes: str = "") -> AnomalyAlert:
        """Mark an alert as false positive"""
        alert = self.alerts.get(alert_id)
        if not alert:
            raise ValueError(f"Alert {alert_id} not found")

        alert.false_positive = True
        alert.investigated = True
        alert.resolution_notes = notes
        return alert

    def get_user_risk_summary(self, user_id: str) -> Dict:
        """Get anomaly risk summary for a user"""
        user_alerts = self.get_alerts(user_id=user_id)
        baseline = self.baselines.get(user_id)

        by_type = defaultdict(int)
        by_severity = defaultdict(int)

        for alert in user_alerts:
            if not alert.false_positive:
                by_type[alert.anomaly_type.value] += 1
                by_severity[alert.severity.value] += 1

        return {
            "user_id": user_id,
            "has_baseline": baseline is not None,
            "baseline_confidence": baseline.confidence_score if baseline else 0,
            "total_alerts": len(user_alerts),
            "unacknowledged": len([a for a in user_alerts if not a.acknowledged]),
            "false_positives": len([a for a in user_alerts if a.false_positive]),
            "by_type": dict(by_type),
            "by_severity": dict(by_severity),
            "anomaly_risk_score": self._calculate_anomaly_risk(user_alerts)
        }

    def _calculate_anomaly_risk(self, alerts: List[AnomalyAlert]) -> float:
        """Calculate anomaly-based risk score"""
        if not alerts:
            return 0.0

        severity_weights = {
            AnomalySeverity.LOW: 5,
            AnomalySeverity.MEDIUM: 15,
            AnomalySeverity.HIGH: 30,
            AnomalySeverity.CRITICAL: 50
        }

        # Only count recent non-false-positive alerts
        recent_alerts = [
            a for a in alerts
            if not a.false_positive
            and (datetime.now() - a.timestamp).days < 30
        ]

        score = sum(severity_weights.get(a.severity, 10) for a in recent_alerts)
        return min(100.0, score)

    def get_statistics(self) -> Dict:
        """Get overall anomaly detection statistics"""
        all_alerts = list(self.alerts.values())
        recent = [a for a in all_alerts if (datetime.now() - a.timestamp).days < 7]

        by_type = defaultdict(int)
        by_severity = defaultdict(int)

        for alert in recent:
            by_type[alert.anomaly_type.value] += 1
            by_severity[alert.severity.value] += 1

        return {
            "total_alerts": len(all_alerts),
            "alerts_last_7_days": len(recent),
            "unacknowledged": len([a for a in all_alerts if not a.acknowledged]),
            "false_positive_rate": len([a for a in all_alerts if a.false_positive]) / len(all_alerts) if all_alerts else 0,
            "users_with_baselines": len(self.baselines),
            "by_type": dict(by_type),
            "by_severity": dict(by_severity)
        }
