# Predictive Features
# Feature engineering for risk prediction

"""
Predictive Features for GOVERNEX+.

Features used for risk prediction:
- Risk trend slope
- Access growth rate
- Privilege creep ratio
- Approval strictness
- Role toxicity index
- Review delays
- Peer deviation
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


@dataclass
class FeatureImportance:
    """Importance of a feature in prediction."""
    feature_name: str
    importance_score: float  # 0-1
    direction: str  # "positive" or "negative" effect on risk
    description: str


@dataclass
class PredictiveFeatureSet:
    """
    Complete feature set for risk prediction.

    All features are numerical and auditable.
    """
    entity_id: str
    entity_type: str

    # Trend features
    risk_trend_slope: float = 0.0  # Risk points change per week
    risk_volatility: float = 0.0  # Standard deviation of risk scores

    # Access features
    access_growth_rate: float = 0.0  # Roles added per month
    role_count: int = 0
    privilege_count: int = 0
    sensitive_privilege_count: int = 0

    # Privilege creep
    privilege_creep: float = 0.0  # Unused privilege ratio trend
    unused_privilege_ratio: float = 0.0

    # Approval behavior
    approval_strictness: float = 0.0  # Denial rate
    avg_approval_time_hours: float = 0.0

    # Role quality
    role_toxicity_index: float = 0.0  # Average toxicity of assigned roles
    role_overlap_score: float = 0.0  # Redundant privileges from multiple roles

    # Review status
    review_delay_weeks: float = 0.0  # Weeks since last review
    overdue_certifications: int = 0

    # Peer comparison
    peer_deviation: float = 0.0  # Z-score deviation from peers
    peer_percentile: float = 0.0  # Percentile in peer group

    # Activity features
    activity_anomaly_score: float = 0.0
    after_hours_ratio: float = 0.0

    # Timestamps
    calculated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entity_id": self.entity_id,
            "entity_type": self.entity_type,
            "risk_trend_slope": round(self.risk_trend_slope, 4),
            "risk_volatility": round(self.risk_volatility, 4),
            "access_growth_rate": round(self.access_growth_rate, 4),
            "role_count": self.role_count,
            "privilege_count": self.privilege_count,
            "sensitive_privilege_count": self.sensitive_privilege_count,
            "privilege_creep": round(self.privilege_creep, 4),
            "unused_privilege_ratio": round(self.unused_privilege_ratio, 4),
            "approval_strictness": round(self.approval_strictness, 4),
            "avg_approval_time_hours": round(self.avg_approval_time_hours, 2),
            "role_toxicity_index": round(self.role_toxicity_index, 4),
            "role_overlap_score": round(self.role_overlap_score, 4),
            "review_delay_weeks": round(self.review_delay_weeks, 2),
            "overdue_certifications": self.overdue_certifications,
            "peer_deviation": round(self.peer_deviation, 4),
            "peer_percentile": round(self.peer_percentile, 2),
            "activity_anomaly_score": round(self.activity_anomaly_score, 4),
            "after_hours_ratio": round(self.after_hours_ratio, 4),
            "calculated_at": self.calculated_at.isoformat(),
        }

    def to_vector(self) -> List[float]:
        """Convert to numerical vector for ML models."""
        return [
            self.risk_trend_slope,
            self.risk_volatility,
            self.access_growth_rate,
            self.role_count,
            self.privilege_count,
            self.sensitive_privilege_count,
            self.privilege_creep,
            self.unused_privilege_ratio,
            self.approval_strictness,
            self.avg_approval_time_hours,
            self.role_toxicity_index,
            self.role_overlap_score,
            self.review_delay_weeks,
            self.overdue_certifications,
            self.peer_deviation,
            self.peer_percentile,
            self.activity_anomaly_score,
            self.after_hours_ratio,
        ]

    @staticmethod
    def feature_names() -> List[str]:
        """Get ordered list of feature names."""
        return [
            "risk_trend_slope",
            "risk_volatility",
            "access_growth_rate",
            "role_count",
            "privilege_count",
            "sensitive_privilege_count",
            "privilege_creep",
            "unused_privilege_ratio",
            "approval_strictness",
            "avg_approval_time_hours",
            "role_toxicity_index",
            "role_overlap_score",
            "review_delay_weeks",
            "overdue_certifications",
            "peer_deviation",
            "peer_percentile",
            "activity_anomaly_score",
            "after_hours_ratio",
        ]

    def to_prediction_dict(self) -> Dict[str, float]:
        """Convert to dict format for prediction engine."""
        return {
            "access_growth_rate": self.access_growth_rate,
            "privilege_creep": self.privilege_creep,
            "peer_deviation": self.peer_deviation,
            "review_delay_weeks": self.review_delay_weeks,
            "role_toxicity_index": self.role_toxicity_index,
        }


# Default feature importances (based on domain knowledge)
DEFAULT_FEATURE_IMPORTANCES = [
    FeatureImportance(
        feature_name="risk_trend_slope",
        importance_score=0.25,
        direction="positive",
        description="Rate of risk increase over time",
    ),
    FeatureImportance(
        feature_name="privilege_creep",
        importance_score=0.20,
        direction="positive",
        description="Accumulation of unused privileges",
    ),
    FeatureImportance(
        feature_name="review_delay_weeks",
        importance_score=0.15,
        direction="positive",
        description="Weeks since last access review",
    ),
    FeatureImportance(
        feature_name="peer_deviation",
        importance_score=0.15,
        direction="positive",
        description="Deviation from peer group behavior",
    ),
    FeatureImportance(
        feature_name="role_toxicity_index",
        importance_score=0.10,
        direction="positive",
        description="Toxicity of assigned roles",
    ),
    FeatureImportance(
        feature_name="access_growth_rate",
        importance_score=0.10,
        direction="positive",
        description="Rate of access accumulation",
    ),
    FeatureImportance(
        feature_name="approval_strictness",
        importance_score=0.05,
        direction="negative",
        description="Strictness of approval process",
    ),
]


def build_prediction_features(
    entity_id: str,
    entity_type: str,
    risk_history: List[float],
    access_history: Optional[Dict[str, Any]] = None,
    usage_data: Optional[Dict[str, Any]] = None,
    peer_data: Optional[Dict[str, Any]] = None,
    review_data: Optional[Dict[str, Any]] = None,
) -> PredictiveFeatureSet:
    """
    Build feature set from available data.

    Args:
        entity_id: Entity identifier
        entity_type: "USER", "ROLE", or "SYSTEM"
        risk_history: Historical risk scores
        access_history: Role/privilege assignment history
        usage_data: Usage and activity data
        peer_data: Peer comparison data
        review_data: Review and certification data

    Returns:
        PredictiveFeatureSet with calculated features
    """
    features = PredictiveFeatureSet(
        entity_id=entity_id,
        entity_type=entity_type,
    )

    # Calculate trend features
    if risk_history and len(risk_history) >= 2:
        features.risk_trend_slope = _calculate_slope(risk_history)
        features.risk_volatility = _calculate_volatility(risk_history)

    # Access features
    if access_history:
        features.role_count = access_history.get("current_role_count", 0)
        features.privilege_count = access_history.get("current_privilege_count", 0)
        features.sensitive_privilege_count = access_history.get("sensitive_privilege_count", 0)

        # Access growth
        prev_roles = access_history.get("role_count_30d_ago", features.role_count)
        features.access_growth_rate = (features.role_count - prev_roles) / max(prev_roles, 1)

    # Usage features
    if usage_data:
        features.unused_privilege_ratio = usage_data.get("unused_ratio", 0)
        features.activity_anomaly_score = usage_data.get("anomaly_score", 0)
        features.after_hours_ratio = usage_data.get("after_hours_ratio", 0)

        # Privilege creep (unused ratio trend)
        prev_unused = usage_data.get("unused_ratio_30d_ago", features.unused_privilege_ratio)
        features.privilege_creep = features.unused_privilege_ratio - prev_unused

    # Peer features
    if peer_data:
        features.peer_deviation = peer_data.get("deviation_score", 0)
        features.peer_percentile = peer_data.get("percentile", 50)

    # Review features
    if review_data:
        last_review = review_data.get("last_review_date")
        if last_review:
            if isinstance(last_review, str):
                last_review = datetime.fromisoformat(last_review)
            days_since = (datetime.now() - last_review).days
            features.review_delay_weeks = days_since / 7

        features.overdue_certifications = review_data.get("overdue_count", 0)
        features.approval_strictness = review_data.get("denial_rate", 0)
        features.avg_approval_time_hours = review_data.get("avg_approval_hours", 0)

    return features


def _calculate_slope(values: List[float]) -> float:
    """Calculate linear regression slope."""
    n = len(values)
    if n < 2:
        return 0

    x = list(range(n))
    x_mean = sum(x) / n
    y_mean = sum(values) / n

    numerator = sum((x[i] - x_mean) * (values[i] - y_mean) for i in range(n))
    denominator = sum((x[i] - x_mean) ** 2 for i in range(n))

    if denominator == 0:
        return 0

    return numerator / denominator


def _calculate_volatility(values: List[float]) -> float:
    """Calculate standard deviation."""
    if len(values) < 2:
        return 0

    mean = sum(values) / len(values)
    variance = sum((v - mean) ** 2 for v in values) / len(values)

    return variance ** 0.5
