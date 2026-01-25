# Behavioral Anomaly Detection
# Real-time detection of unusual access patterns

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from datetime import datetime, timedelta
from collections import defaultdict
import math


class AnomalyType(Enum):
    """Types of detected anomalies"""
    TIME_ANOMALY = "time_anomaly"           # Access at unusual time
    VOLUME_ANOMALY = "volume_anomaly"       # Unusual data volume
    FREQUENCY_ANOMALY = "frequency_anomaly" # Unusual access frequency
    LOCATION_ANOMALY = "location_anomaly"   # Unusual location
    PATTERN_ANOMALY = "pattern_anomaly"     # Unusual sequence
    SCOPE_ANOMALY = "scope_anomaly"         # Accessing unusual data
    VELOCITY_ANOMALY = "velocity_anomaly"   # Too fast to be human
    DORMANT_ANOMALY = "dormant_anomaly"     # Long inactive, suddenly active


class RiskIndicator(Enum):
    """Risk indicator levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertStatus(Enum):
    """Alert status"""
    NEW = "new"
    INVESTIGATING = "investigating"
    CONFIRMED = "confirmed"
    FALSE_POSITIVE = "false_positive"
    RESOLVED = "resolved"


@dataclass
class UserBehaviorProfile:
    """Learned behavioral profile for a user"""
    user_id: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_updated: datetime = field(default_factory=datetime.utcnow)

    # Time patterns
    typical_hours: Tuple[int, int] = (9, 17)  # Start, end hour
    typical_days: List[int] = field(default_factory=lambda: [0,1,2,3,4])  # Mon-Fri
    avg_sessions_per_day: float = 2.0

    # Transaction patterns
    typical_transactions: List[str] = field(default_factory=list)
    transaction_frequency: Dict[str, float] = field(default_factory=dict)
    avg_transactions_per_session: float = 50.0

    # Volume patterns
    avg_records_accessed: float = 100.0
    max_normal_records: float = 500.0

    # Location patterns
    typical_ip_ranges: List[str] = field(default_factory=list)
    typical_locations: List[str] = field(default_factory=list)

    # Activity patterns
    last_active: Optional[datetime] = None
    avg_days_between_activity: float = 1.0

    # Learning metrics
    observation_days: int = 0
    confidence: float = 0.5  # How confident we are in this profile


@dataclass
class AnomalyAlert:
    """Detected anomaly alert"""
    id: str
    user_id: str
    anomaly_type: AnomalyType
    risk_indicator: RiskIndicator
    status: AlertStatus = AlertStatus.NEW

    # What happened
    description: str = ""
    details: Dict[str, Any] = field(default_factory=dict)

    # Comparison to normal
    expected_value: Any = None
    actual_value: Any = None
    deviation_score: float = 0.0  # How far from normal (0-1)

    # Context
    session_id: Optional[str] = None
    transaction: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)

    # Investigation
    investigated_by: Optional[str] = None
    investigation_notes: str = ""
    resolution: str = ""

    # Related alerts
    related_alerts: List[str] = field(default_factory=list)


class BehavioralAnomalyDetector:
    """
    Real-Time Behavioral Anomaly Detection

    Key advantages over traditional SAP GRC:

    1. LEARNS NORMAL BEHAVIOR: Builds profile of each user
       - What transactions they typically run
       - When they typically work
       - How much data they typically access

    2. DETECTS DEVIATIONS: Flags unusual patterns
       - Access at 3 AM from someone who always works 9-5
       - Downloading 10,000 records when normal is 100
       - Using transactions never used before

    3. RISK-BASED ALERTING: Prioritizes what matters
       - Not all anomalies are equal
       - Considers sensitivity of data/action
       - Reduces alert fatigue

    4. CONTINUOUS MONITORING: Real-time, not just periodic
       - Catches issues as they happen
       - Enables quick response

    5. ADAPTS OVER TIME: Gets smarter
       - Learns from false positives
       - Adjusts to changing work patterns
    """

    def __init__(self):
        # User behavior profiles
        self.profiles: Dict[str, UserBehaviorProfile] = {}

        # Active alerts
        self.alerts: Dict[str, AnomalyAlert] = {}

        # Alert history
        self.alert_history: List[AnomalyAlert] = []

        # Configuration
        self.config = {
            "time_deviation_threshold": 2,      # Hours outside normal
            "volume_deviation_multiplier": 3,   # X times normal volume
            "frequency_deviation_multiplier": 5, # X times normal frequency
            "dormancy_threshold_days": 30,      # Days without activity
            "min_observation_days": 7,          # Days before baseline valid
            "alert_cooldown_minutes": 60        # Min time between same alerts
        }

        # Sensitivity weights for different data/transactions
        self.sensitivity_weights = {
            "SU01": 1.5,    # User maintenance
            "PFCG": 1.5,    # Role maintenance
            "SE16": 1.3,    # Table display
            "SM21": 1.3,    # System log
            "FB01": 1.2,    # Financial posting
            "F110": 1.4,    # Payment run
            "PA30": 1.3,    # HR master data
            "default": 1.0
        }

        self._initialize_demo_profiles()

    def _initialize_demo_profiles(self):
        """Initialize demo user profiles"""
        self.profiles = {
            "JSMITH": UserBehaviorProfile(
                user_id="JSMITH",
                typical_hours=(8, 18),
                typical_days=[0, 1, 2, 3, 4],
                typical_transactions=["FB01", "FB02", "FB03", "F-02", "FBL1N"],
                transaction_frequency={"FB01": 20, "FB02": 15, "FB03": 50, "F-02": 5},
                avg_transactions_per_session=45,
                avg_records_accessed=150,
                max_normal_records=500,
                typical_locations=["Office-NYC", "VPN-US"],
                observation_days=180,
                confidence=0.9
            ),
            "MBROWN": UserBehaviorProfile(
                user_id="MBROWN",
                typical_hours=(9, 17),
                typical_days=[0, 1, 2, 3, 4],
                typical_transactions=["ME21N", "ME22N", "ME23N", "MIGO", "MB51"],
                transaction_frequency={"ME21N": 10, "ME22N": 5, "ME23N": 20, "MIGO": 8},
                avg_transactions_per_session=30,
                avg_records_accessed=80,
                max_normal_records=300,
                typical_locations=["Office-Chicago"],
                observation_days=90,
                confidence=0.85
            ),
            "TDAVIS": UserBehaviorProfile(
                user_id="TDAVIS",
                typical_hours=(7, 22),  # IT works varied hours
                typical_days=[0, 1, 2, 3, 4, 5, 6],  # Including weekends
                typical_transactions=["SU01", "PFCG", "SM21", "SM37", "ST22"],
                transaction_frequency={"SU01": 30, "PFCG": 25, "SM21": 50, "SM37": 40},
                avg_transactions_per_session=80,
                avg_records_accessed=500,
                max_normal_records=2000,
                typical_locations=["Office-IT", "VPN-Admin", "DataCenter"],
                observation_days=365,
                confidence=0.95
            )
        }

    # ==================== Real-Time Detection ====================

    def analyze_activity(
        self,
        user_id: str,
        activity: Dict[str, Any]
    ) -> List[AnomalyAlert]:
        """
        Analyze a user activity for anomalies

        Called in real-time as activities occur.

        activity dict should contain:
        - transaction: Transaction code
        - timestamp: When it occurred
        - records_accessed: Number of records
        - location: IP or location identifier
        - session_id: Session identifier
        """
        alerts = []

        # Get or create profile
        profile = self.profiles.get(user_id)
        if not profile:
            profile = UserBehaviorProfile(user_id=user_id)
            self.profiles[user_id] = profile

        # Skip detection if not enough baseline data
        if profile.observation_days < self.config["min_observation_days"]:
            self._update_profile(profile, activity)
            return []

        # Run detection checks
        alerts.extend(self._check_time_anomaly(profile, activity))
        alerts.extend(self._check_volume_anomaly(profile, activity))
        alerts.extend(self._check_transaction_anomaly(profile, activity))
        alerts.extend(self._check_location_anomaly(profile, activity))
        alerts.extend(self._check_dormancy_anomaly(profile, activity))
        alerts.extend(self._check_velocity_anomaly(profile, activity))

        # Update profile with new activity
        self._update_profile(profile, activity)

        # Store and deduplicate alerts
        for alert in alerts:
            if not self._is_duplicate_alert(alert):
                self.alerts[alert.id] = alert
                self.alert_history.append(alert)

        return alerts

    def _check_time_anomaly(
        self,
        profile: UserBehaviorProfile,
        activity: Dict
    ) -> List[AnomalyAlert]:
        """Check for time-based anomalies"""
        alerts = []
        timestamp = activity.get("timestamp", datetime.utcnow())

        hour = timestamp.hour
        day_of_week = timestamp.weekday()

        # Check if outside typical hours
        start_hour, end_hour = profile.typical_hours
        if hour < start_hour - self.config["time_deviation_threshold"] or \
           hour > end_hour + self.config["time_deviation_threshold"]:

            # Calculate deviation score
            if hour < start_hour:
                deviation = (start_hour - hour) / 12
            else:
                deviation = (hour - end_hour) / 12

            risk = RiskIndicator.MEDIUM
            if hour < 6 or hour > 22:
                risk = RiskIndicator.HIGH

            alerts.append(AnomalyAlert(
                id=f"anomaly_{profile.user_id}_{timestamp.strftime('%Y%m%d%H%M%S')}_time",
                user_id=profile.user_id,
                anomaly_type=AnomalyType.TIME_ANOMALY,
                risk_indicator=risk,
                description=f"Activity at unusual time ({hour}:00)",
                details={"hour": hour, "typical_hours": profile.typical_hours},
                expected_value=f"{start_hour}:00 - {end_hour}:00",
                actual_value=f"{hour}:00",
                deviation_score=min(deviation, 1.0),
                session_id=activity.get("session_id"),
                transaction=activity.get("transaction"),
                timestamp=timestamp
            ))

        # Check if unusual day
        if day_of_week not in profile.typical_days:
            day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
            alerts.append(AnomalyAlert(
                id=f"anomaly_{profile.user_id}_{timestamp.strftime('%Y%m%d%H%M%S')}_day",
                user_id=profile.user_id,
                anomaly_type=AnomalyType.TIME_ANOMALY,
                risk_indicator=RiskIndicator.LOW,
                description=f"Activity on unusual day ({day_names[day_of_week]})",
                details={"day": day_of_week, "typical_days": profile.typical_days},
                expected_value=[day_names[d] for d in profile.typical_days],
                actual_value=day_names[day_of_week],
                deviation_score=0.3,
                timestamp=timestamp
            ))

        return alerts

    def _check_volume_anomaly(
        self,
        profile: UserBehaviorProfile,
        activity: Dict
    ) -> List[AnomalyAlert]:
        """Check for volume-based anomalies"""
        alerts = []
        records = activity.get("records_accessed", 0)

        if records > profile.max_normal_records:
            multiplier = records / profile.avg_records_accessed
            deviation = min((records - profile.avg_records_accessed) / profile.avg_records_accessed, 1.0)

            risk = RiskIndicator.MEDIUM
            if multiplier > self.config["volume_deviation_multiplier"]:
                risk = RiskIndicator.HIGH
            if multiplier > self.config["volume_deviation_multiplier"] * 2:
                risk = RiskIndicator.CRITICAL

            alerts.append(AnomalyAlert(
                id=f"anomaly_{profile.user_id}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_volume",
                user_id=profile.user_id,
                anomaly_type=AnomalyType.VOLUME_ANOMALY,
                risk_indicator=risk,
                description=f"Unusually high data access ({records:,} records)",
                details={
                    "records_accessed": records,
                    "normal_average": profile.avg_records_accessed,
                    "multiplier": round(multiplier, 1)
                },
                expected_value=f"< {profile.max_normal_records:,} records",
                actual_value=f"{records:,} records",
                deviation_score=deviation,
                session_id=activity.get("session_id"),
                transaction=activity.get("transaction")
            ))

        return alerts

    def _check_transaction_anomaly(
        self,
        profile: UserBehaviorProfile,
        activity: Dict
    ) -> List[AnomalyAlert]:
        """Check for unusual transaction access"""
        alerts = []
        transaction = activity.get("transaction", "")

        if transaction and transaction not in profile.typical_transactions:
            # Check sensitivity of transaction
            sensitivity = self.sensitivity_weights.get(
                transaction,
                self.sensitivity_weights["default"]
            )

            risk = RiskIndicator.LOW
            if sensitivity > 1.2:
                risk = RiskIndicator.MEDIUM
            if sensitivity > 1.4:
                risk = RiskIndicator.HIGH

            alerts.append(AnomalyAlert(
                id=f"anomaly_{profile.user_id}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_tcode",
                user_id=profile.user_id,
                anomaly_type=AnomalyType.PATTERN_ANOMALY,
                risk_indicator=risk,
                description=f"Access to unusual transaction ({transaction})",
                details={
                    "transaction": transaction,
                    "typical_transactions": profile.typical_transactions[:10],
                    "sensitivity": sensitivity
                },
                expected_value=profile.typical_transactions[:5],
                actual_value=transaction,
                deviation_score=0.5 * sensitivity,
                transaction=transaction
            ))

        return alerts

    def _check_location_anomaly(
        self,
        profile: UserBehaviorProfile,
        activity: Dict
    ) -> List[AnomalyAlert]:
        """Check for unusual location access"""
        alerts = []
        location = activity.get("location", "")

        if location and profile.typical_locations and location not in profile.typical_locations:
            alerts.append(AnomalyAlert(
                id=f"anomaly_{profile.user_id}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_loc",
                user_id=profile.user_id,
                anomaly_type=AnomalyType.LOCATION_ANOMALY,
                risk_indicator=RiskIndicator.HIGH,
                description=f"Access from unusual location ({location})",
                details={
                    "location": location,
                    "typical_locations": profile.typical_locations
                },
                expected_value=profile.typical_locations,
                actual_value=location,
                deviation_score=0.7,
                session_id=activity.get("session_id")
            ))

        return alerts

    def _check_dormancy_anomaly(
        self,
        profile: UserBehaviorProfile,
        activity: Dict
    ) -> List[AnomalyAlert]:
        """Check for activity after long dormancy"""
        alerts = []

        if profile.last_active:
            days_inactive = (datetime.utcnow() - profile.last_active).days

            if days_inactive > self.config["dormancy_threshold_days"]:
                risk = RiskIndicator.HIGH
                if days_inactive > self.config["dormancy_threshold_days"] * 2:
                    risk = RiskIndicator.CRITICAL

                alerts.append(AnomalyAlert(
                    id=f"anomaly_{profile.user_id}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_dormant",
                    user_id=profile.user_id,
                    anomaly_type=AnomalyType.DORMANT_ANOMALY,
                    risk_indicator=risk,
                    description=f"Activity after {days_inactive} days of inactivity",
                    details={
                        "days_inactive": days_inactive,
                        "last_active": profile.last_active.isoformat(),
                        "threshold": self.config["dormancy_threshold_days"]
                    },
                    expected_value=f"< {self.config['dormancy_threshold_days']} days",
                    actual_value=f"{days_inactive} days",
                    deviation_score=min(days_inactive / 90, 1.0)
                ))

        return alerts

    def _check_velocity_anomaly(
        self,
        profile: UserBehaviorProfile,
        activity: Dict
    ) -> List[AnomalyAlert]:
        """Check for impossible velocity (too fast for human)"""
        alerts = []
        transactions_per_minute = activity.get("transactions_per_minute", 0)

        # Humans typically can't do more than 10-15 transactions per minute
        if transactions_per_minute > 20:
            risk = RiskIndicator.CRITICAL

            alerts.append(AnomalyAlert(
                id=f"anomaly_{profile.user_id}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_velocity",
                user_id=profile.user_id,
                anomaly_type=AnomalyType.VELOCITY_ANOMALY,
                risk_indicator=risk,
                description=f"Impossible transaction velocity ({transactions_per_minute}/min)",
                details={
                    "transactions_per_minute": transactions_per_minute,
                    "max_human_possible": 15
                },
                expected_value="< 15 transactions/minute",
                actual_value=f"{transactions_per_minute} transactions/minute",
                deviation_score=1.0
            ))

        return alerts

    def _is_duplicate_alert(self, alert: AnomalyAlert) -> bool:
        """Check if similar alert was raised recently"""
        cooldown = timedelta(minutes=self.config["alert_cooldown_minutes"])

        for existing in self.alerts.values():
            if (existing.user_id == alert.user_id and
                existing.anomaly_type == alert.anomaly_type and
                (alert.timestamp - existing.timestamp) < cooldown):
                return True

        return False

    def _update_profile(self, profile: UserBehaviorProfile, activity: Dict):
        """Update user profile with new activity (continuous learning)"""
        profile.last_active = datetime.utcnow()
        profile.last_updated = datetime.utcnow()

        # Update transaction patterns
        transaction = activity.get("transaction", "")
        if transaction:
            if transaction not in profile.typical_transactions:
                # Only add after seeing it multiple times
                freq = profile.transaction_frequency.get(transaction, 0) + 1
                profile.transaction_frequency[transaction] = freq
                if freq >= 5:  # Threshold to be considered "typical"
                    profile.typical_transactions.append(transaction)

        # Update volume averages (exponential moving average)
        records = activity.get("records_accessed", 0)
        if records > 0:
            alpha = 0.1  # Smoothing factor
            profile.avg_records_accessed = (
                alpha * records + (1 - alpha) * profile.avg_records_accessed
            )

        profile.observation_days += 1

    # ==================== Alert Management ====================

    def get_active_alerts(
        self,
        user_id: Optional[str] = None,
        risk_level: Optional[RiskIndicator] = None,
        limit: int = 100
    ) -> List[AnomalyAlert]:
        """Get active alerts with optional filters"""
        alerts = list(self.alerts.values())

        # Filter by user
        if user_id:
            alerts = [a for a in alerts if a.user_id == user_id]

        # Filter by risk level
        if risk_level:
            alerts = [a for a in alerts if a.risk_indicator == risk_level]

        # Filter out resolved
        alerts = [a for a in alerts if a.status not in [
            AlertStatus.FALSE_POSITIVE, AlertStatus.RESOLVED
        ]]

        # Sort by risk level and time
        risk_order = {
            RiskIndicator.CRITICAL: 0,
            RiskIndicator.HIGH: 1,
            RiskIndicator.MEDIUM: 2,
            RiskIndicator.LOW: 3
        }
        alerts.sort(key=lambda a: (risk_order[a.risk_indicator], a.timestamp), reverse=True)

        return alerts[:limit]

    def update_alert_status(
        self,
        alert_id: str,
        new_status: AlertStatus,
        updated_by: str,
        notes: str = ""
    ) -> Dict[str, Any]:
        """Update alert status"""
        if alert_id not in self.alerts:
            return {"success": False, "error": "Alert not found"}

        alert = self.alerts[alert_id]
        alert.status = new_status
        alert.investigated_by = updated_by
        alert.investigation_notes = notes

        # If marked as false positive, learn from it
        if new_status == AlertStatus.FALSE_POSITIVE:
            self._learn_from_false_positive(alert)

        return {
            "success": True,
            "alert_id": alert_id,
            "new_status": new_status.value
        }

    def _learn_from_false_positive(self, alert: AnomalyAlert):
        """Adjust detection to reduce similar false positives"""
        profile = self.profiles.get(alert.user_id)
        if not profile:
            return

        # Adjust based on anomaly type
        if alert.anomaly_type == AnomalyType.TIME_ANOMALY:
            # Expand typical hours
            hour = alert.details.get("hour", 12)
            start, end = profile.typical_hours
            if hour < start:
                profile.typical_hours = (hour, end)
            elif hour > end:
                profile.typical_hours = (start, hour)

        elif alert.anomaly_type == AnomalyType.PATTERN_ANOMALY:
            # Add transaction to typical list
            tcode = alert.transaction
            if tcode and tcode not in profile.typical_transactions:
                profile.typical_transactions.append(tcode)

        elif alert.anomaly_type == AnomalyType.LOCATION_ANOMALY:
            # Add location to typical list
            location = alert.details.get("location")
            if location and location not in profile.typical_locations:
                profile.typical_locations.append(location)

    # ==================== Analytics ====================

    def get_risk_summary(self) -> Dict[str, Any]:
        """Get summary of current anomaly detection state"""
        alerts = list(self.alerts.values())
        active_alerts = [a for a in alerts if a.status not in [
            AlertStatus.FALSE_POSITIVE, AlertStatus.RESOLVED
        ]]

        by_type = defaultdict(int)
        by_risk = defaultdict(int)
        by_user = defaultdict(int)

        for alert in active_alerts:
            by_type[alert.anomaly_type.value] += 1
            by_risk[alert.risk_indicator.value] += 1
            by_user[alert.user_id] += 1

        return {
            "total_active_alerts": len(active_alerts),
            "by_anomaly_type": dict(by_type),
            "by_risk_level": dict(by_risk),
            "top_users": sorted(by_user.items(), key=lambda x: x[1], reverse=True)[:10],
            "profiles_monitored": len(self.profiles),
            "alerts_today": len([
                a for a in active_alerts
                if a.timestamp.date() == datetime.utcnow().date()
            ])
        }

    def get_user_risk_score(self, user_id: str) -> Dict[str, Any]:
        """Calculate current risk score for a user based on anomalies"""
        user_alerts = [
            a for a in self.alerts.values()
            if a.user_id == user_id and a.status not in [
                AlertStatus.FALSE_POSITIVE, AlertStatus.RESOLVED
            ]
        ]

        if not user_alerts:
            return {
                "user_id": user_id,
                "behavioral_risk_score": 0,
                "active_alerts": 0,
                "risk_level": "low"
            }

        # Calculate weighted score
        risk_weights = {
            RiskIndicator.CRITICAL: 40,
            RiskIndicator.HIGH: 25,
            RiskIndicator.MEDIUM: 10,
            RiskIndicator.LOW: 5
        }

        score = sum(risk_weights[a.risk_indicator] for a in user_alerts)
        score = min(score, 100)

        level = "low"
        if score > 30:
            level = "medium"
        if score > 60:
            level = "high"
        if score > 80:
            level = "critical"

        return {
            "user_id": user_id,
            "behavioral_risk_score": score,
            "active_alerts": len(user_alerts),
            "critical_alerts": len([a for a in user_alerts if a.risk_indicator == RiskIndicator.CRITICAL]),
            "risk_level": level,
            "top_concerns": [
                {"type": a.anomaly_type.value, "description": a.description}
                for a in sorted(
                    user_alerts,
                    key=lambda x: list(RiskIndicator).index(x.risk_indicator)
                )[:3]
            ]
        }
