# Feature Extraction for ML-based Anomaly Detection
# Auditor-explainable behavioral features

"""
Feature extraction for ARA ML models.

All features are:
- Auditor-explainable (no opaque embeddings)
- Derived from observable behavior
- Normalized for model consumption
- Documented with business meaning
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict
import logging
import statistics

logger = logging.getLogger(__name__)


@dataclass
class BehaviorFeatureVector:
    """
    Feature vector for ML anomaly detection.

    All features are explainable metrics that auditors can understand.
    """
    user_id: str

    # Transaction volume features
    tcode_exec_count: float = 0.0
    unique_tcodes_used: float = 0.0
    sensitive_tcode_count: float = 0.0
    sensitive_tcode_ratio: float = 0.0

    # Time-based features
    after_hours_ratio: float = 0.0
    weekend_ratio: float = 0.0
    avg_session_duration_minutes: float = 0.0

    # Access features
    role_count: float = 0.0
    entitlement_count: float = 0.0
    unused_privilege_ratio: float = 0.0

    # Peer comparison features
    peer_deviation_score: float = 0.0
    volume_vs_peer_ratio: float = 0.0

    # Risk-related features
    sod_conflict_count: float = 0.0
    sensitive_access_count: float = 0.0
    failed_auth_count: float = 0.0

    # Metadata
    extracted_at: datetime = field(default_factory=datetime.now)
    period_days: int = 30

    def to_vector(self) -> List[float]:
        """Convert to numeric vector for ML models."""
        return [
            self.tcode_exec_count,
            self.unique_tcodes_used,
            self.sensitive_tcode_count,
            self.sensitive_tcode_ratio,
            self.after_hours_ratio,
            self.weekend_ratio,
            self.avg_session_duration_minutes,
            self.role_count,
            self.entitlement_count,
            self.unused_privilege_ratio,
            self.peer_deviation_score,
            self.volume_vs_peer_ratio,
            self.sod_conflict_count,
            self.sensitive_access_count,
            self.failed_auth_count,
        ]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with feature names."""
        return {
            "user_id": self.user_id,
            "features": {
                "tcode_exec_count": self.tcode_exec_count,
                "unique_tcodes_used": self.unique_tcodes_used,
                "sensitive_tcode_count": self.sensitive_tcode_count,
                "sensitive_tcode_ratio": self.sensitive_tcode_ratio,
                "after_hours_ratio": self.after_hours_ratio,
                "weekend_ratio": self.weekend_ratio,
                "avg_session_duration_minutes": self.avg_session_duration_minutes,
                "role_count": self.role_count,
                "entitlement_count": self.entitlement_count,
                "unused_privilege_ratio": self.unused_privilege_ratio,
                "peer_deviation_score": self.peer_deviation_score,
                "volume_vs_peer_ratio": self.volume_vs_peer_ratio,
                "sod_conflict_count": self.sod_conflict_count,
                "sensitive_access_count": self.sensitive_access_count,
                "failed_auth_count": self.failed_auth_count,
            },
            "extracted_at": self.extracted_at.isoformat(),
            "period_days": self.period_days,
        }

    @classmethod
    def feature_names(cls) -> List[str]:
        """Get ordered list of feature names."""
        return [
            "tcode_exec_count",
            "unique_tcodes_used",
            "sensitive_tcode_count",
            "sensitive_tcode_ratio",
            "after_hours_ratio",
            "weekend_ratio",
            "avg_session_duration_minutes",
            "role_count",
            "entitlement_count",
            "unused_privilege_ratio",
            "peer_deviation_score",
            "volume_vs_peer_ratio",
            "sod_conflict_count",
            "sensitive_access_count",
            "failed_auth_count",
        ]


class FeatureExtractor:
    """
    Extracts ML features from user behavior data.

    Designed for:
    - Explainability (auditors can understand each feature)
    - Consistency (same inputs produce same outputs)
    - Scalability (efficient extraction)
    """

    # Sensitive tcodes (configurable)
    SENSITIVE_TCODES = {
        "SE38", "SE80", "SE16", "SE16N", "SU01", "PFCG",
        "SM59", "STMS", "SM30", "FB01", "F110", "XK01",
        "FK01", "F-53", "PA30", "SE09", "SE10",
    }

    # Business hours (configurable)
    BUSINESS_HOURS_START = 6
    BUSINESS_HOURS_END = 20

    def __init__(
        self,
        sensitive_tcodes: Optional[set] = None,
        business_hours: Optional[Tuple[int, int]] = None
    ):
        """
        Initialize feature extractor.

        Args:
            sensitive_tcodes: Override default sensitive tcodes
            business_hours: Tuple of (start_hour, end_hour)
        """
        if sensitive_tcodes:
            self.SENSITIVE_TCODES = sensitive_tcodes
        if business_hours:
            self.BUSINESS_HOURS_START, self.BUSINESS_HOURS_END = business_hours

    def extract(
        self,
        user_id: str,
        transactions: List[Dict[str, Any]],
        assigned_access: Dict[str, Any],
        used_access: Dict[str, int],
        peer_metrics: Optional[Dict[str, float]] = None,
        risk_data: Optional[Dict[str, int]] = None,
        period_days: int = 30
    ) -> BehaviorFeatureVector:
        """
        Extract feature vector for a user.

        Args:
            user_id: User identifier
            transactions: List of transaction records
            assigned_access: User's assigned access (roles, tcodes)
            used_access: Mapping of tcode -> usage count
            peer_metrics: Optional peer comparison data
            risk_data: Optional risk-related counts
            period_days: Analysis period

        Returns:
            BehaviorFeatureVector for ML scoring
        """
        features = BehaviorFeatureVector(
            user_id=user_id,
            period_days=period_days
        )

        # Transaction volume features
        features.tcode_exec_count = float(len(transactions))
        features.unique_tcodes_used = float(len(used_access))

        # Sensitive tcode analysis
        sensitive_count = sum(
            1 for t in transactions
            if t.get("tcode", "") in self.SENSITIVE_TCODES
        )
        features.sensitive_tcode_count = float(sensitive_count)
        features.sensitive_tcode_ratio = (
            sensitive_count / len(transactions) if transactions else 0.0
        )

        # Time-based features
        after_hours = 0
        weekend = 0
        session_durations = []

        for txn in transactions:
            txn_time = self._parse_time(txn)
            if txn_time:
                hour = txn_time.hour
                if hour < self.BUSINESS_HOURS_START or hour >= self.BUSINESS_HOURS_END:
                    after_hours += 1
                if txn_time.weekday() >= 5:
                    weekend += 1

            duration = txn.get("duration_ms", 0)
            if duration > 0:
                session_durations.append(duration / 60000)  # Convert to minutes

        features.after_hours_ratio = (
            after_hours / len(transactions) if transactions else 0.0
        )
        features.weekend_ratio = (
            weekend / len(transactions) if transactions else 0.0
        )
        features.avg_session_duration_minutes = (
            statistics.mean(session_durations) if session_durations else 0.0
        )

        # Access features
        features.role_count = float(len(assigned_access.get("roles", [])))
        features.entitlement_count = float(len(assigned_access.get("tcodes", [])))

        # Unused privilege ratio
        assigned_tcodes = set(assigned_access.get("tcodes", []))
        used_tcodes = set(used_access.keys())
        unused = assigned_tcodes - used_tcodes
        features.unused_privilege_ratio = (
            len(unused) / len(assigned_tcodes) if assigned_tcodes else 0.0
        )

        # Peer comparison features
        if peer_metrics:
            peer_avg_volume = peer_metrics.get("avg_volume", 0)
            if peer_avg_volume > 0:
                features.volume_vs_peer_ratio = (
                    features.tcode_exec_count / peer_avg_volume
                )
            features.peer_deviation_score = peer_metrics.get("deviation_score", 0)

        # Risk-related features
        if risk_data:
            features.sod_conflict_count = float(risk_data.get("sod_conflicts", 0))
            features.sensitive_access_count = float(risk_data.get("sensitive_access", 0))
            features.failed_auth_count = float(risk_data.get("failed_auths", 0))

        return features

    def _parse_time(self, txn: Dict[str, Any]) -> Optional[datetime]:
        """Parse transaction timestamp."""
        time_val = txn.get("datetime") or txn.get("timestamp")
        if not time_val:
            return None

        if isinstance(time_val, datetime):
            return time_val

        try:
            if "T" in str(time_val):
                return datetime.fromisoformat(str(time_val))
        except (ValueError, TypeError):
            pass

        return None


def extract_user_features(
    user_id: str,
    transactions: List[Dict[str, Any]],
    assigned_access: Dict[str, Any],
    period_days: int = 30
) -> BehaviorFeatureVector:
    """
    Convenience function to extract features for a user.

    Args:
        user_id: User identifier
        transactions: List of transaction records
        assigned_access: User's assigned access
        period_days: Analysis period

    Returns:
        Feature vector for ML scoring
    """
    extractor = FeatureExtractor()

    # Build used_access from transactions
    used_access = defaultdict(int)
    for txn in transactions:
        tcode = txn.get("tcode", "")
        if tcode:
            used_access[tcode] += 1

    return extractor.extract(
        user_id=user_id,
        transactions=transactions,
        assigned_access=assigned_access,
        used_access=dict(used_access),
        period_days=period_days
    )


def extract_session_features(
    user_id: str,
    session_events: List[Dict[str, Any]],
    context: Dict[str, Any]
) -> BehaviorFeatureVector:
    """
    Extract features from a single session (real-time use).

    Args:
        user_id: User identifier
        session_events: Events in the current session
        context: Session context (location, device, etc.)

    Returns:
        Feature vector for real-time ML scoring
    """
    extractor = FeatureExtractor()

    # Build minimal access map from session
    used_access = defaultdict(int)
    for event in session_events:
        tcode = event.get("tcode", "")
        if tcode:
            used_access[tcode] += 1

    features = extractor.extract(
        user_id=user_id,
        transactions=session_events,
        assigned_access=context.get("assigned_access", {}),
        used_access=dict(used_access),
        period_days=1
    )

    return features
