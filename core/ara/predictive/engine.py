# Predictive Risk Engine
# Forecasting access risk over time

"""
Predictive Risk Engine for GOVERNEX+.

Predicts likelihood of risk increase for:
- Users
- Roles
- Systems
- Business processes

Uses:
- Historical risk trends
- Access growth patterns
- Privilege creep indicators
- Peer comparison
- Review delays
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from enum import Enum
import logging
import math

logger = logging.getLogger(__name__)


class PredictionHorizon(Enum):
    """Prediction time horizons."""
    DAYS_30 = 30
    DAYS_60 = 60
    DAYS_90 = 90


class TrendDirection(Enum):
    """Direction of risk trend."""
    INCREASING = "INCREASING"
    STABLE = "STABLE"
    DECREASING = "DECREASING"


@dataclass
class PredictionConfig:
    """Configuration for risk prediction."""
    # Model settings
    use_ml_model: bool = False  # Use ML model if available
    confidence_threshold: float = 0.7

    # Feature weights
    trend_weight: float = 0.3
    access_growth_weight: float = 0.2
    privilege_creep_weight: float = 0.2
    peer_deviation_weight: float = 0.15
    review_delay_weight: float = 0.15

    # Alerting thresholds
    high_risk_threshold: int = 80
    warning_threshold: int = 60


@dataclass
class RiskPrediction:
    """
    Predicted risk for a user/entity.

    Contains:
    - Predictions for 30/60/90 days
    - Trend analysis
    - Contributing factors
    - Recommended actions
    """
    entity_id: str
    entity_type: str  # "USER", "ROLE", "SYSTEM"
    current_risk: float

    # Predictions
    prediction_30d: float
    prediction_60d: float
    prediction_90d: float

    # Trend
    trend: TrendDirection
    trend_slope: float  # Risk points per week

    # Confidence
    confidence: float  # 0-1
    data_quality: str  # "HIGH", "MEDIUM", "LOW"

    # Contributing factors
    factors: Dict[str, float] = field(default_factory=dict)
    primary_driver: str = ""

    # Alerts
    will_exceed_threshold: bool = False
    threshold_breach_days: Optional[int] = None

    # Recommendations
    recommended_actions: List[str] = field(default_factory=list)
    priority: str = "MEDIUM"

    # Metadata
    predicted_at: datetime = field(default_factory=datetime.now)
    model_version: str = "1.0"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entity_id": self.entity_id,
            "entity_type": self.entity_type,
            "current_risk": round(self.current_risk, 2),
            "predictions": {
                "30_days": round(self.prediction_30d, 2),
                "60_days": round(self.prediction_60d, 2),
                "90_days": round(self.prediction_90d, 2),
            },
            "trend": self.trend.value,
            "trend_slope": round(self.trend_slope, 4),
            "confidence": round(self.confidence, 4),
            "data_quality": self.data_quality,
            "factors": {k: round(v, 4) for k, v in self.factors.items()},
            "primary_driver": self.primary_driver,
            "will_exceed_threshold": self.will_exceed_threshold,
            "threshold_breach_days": self.threshold_breach_days,
            "recommended_actions": self.recommended_actions,
            "priority": self.priority,
            "predicted_at": self.predicted_at.isoformat(),
        }


class PredictiveRiskEngine:
    """
    Predicts future access risk based on historical patterns.

    Key capabilities:
    - Trend-based prediction
    - Feature-weighted forecasting
    - Early warning generation
    - Actionable recommendations
    """

    def __init__(self, config: Optional[PredictionConfig] = None):
        """
        Initialize predictive engine.

        Args:
            config: Prediction configuration
        """
        self.config = config or PredictionConfig()
        self._ml_model = None

        # Try to load ML model
        if self.config.use_ml_model:
            self._load_ml_model()

    def _load_ml_model(self):
        """Load ML model if available."""
        try:
            # In production, load a trained model
            # For now, we use statistical methods
            pass
        except Exception as e:
            logger.warning(f"ML model not available: {e}")

    def predict(
        self,
        entity_id: str,
        entity_type: str,
        risk_history: List[float],
        features: Optional[Dict[str, float]] = None
    ) -> RiskPrediction:
        """
        Predict future risk for an entity.

        Args:
            entity_id: Entity identifier
            entity_type: "USER", "ROLE", or "SYSTEM"
            risk_history: Historical risk scores (oldest first)
            features: Additional predictive features

        Returns:
            RiskPrediction with forecasts and recommendations
        """
        if not risk_history:
            return self._empty_prediction(entity_id, entity_type)

        # Ensure we have enough history
        if len(risk_history) < 3:
            # Pad with current value
            risk_history = [risk_history[0]] * 3 + risk_history

        current_risk = risk_history[-1]
        features = features or {}

        # Calculate trend using linear regression
        slope, confidence = self._calculate_trend(risk_history)

        # Determine trend direction
        if slope > 0.5:
            trend = TrendDirection.INCREASING
        elif slope < -0.5:
            trend = TrendDirection.DECREASING
        else:
            trend = TrendDirection.STABLE

        # Base predictions from trend
        pred_30d = self._project_risk(current_risk, slope, 30, features)
        pred_60d = self._project_risk(current_risk, slope, 60, features)
        pred_90d = self._project_risk(current_risk, slope, 90, features)

        # Calculate contributing factors
        factors = self._calculate_factors(risk_history, features)
        primary_driver = max(factors.items(), key=lambda x: abs(x[1]))[0] if factors else ""

        # Check threshold breach
        will_exceed = pred_90d > self.config.high_risk_threshold
        breach_days = None

        if will_exceed and current_risk < self.config.high_risk_threshold:
            breach_days = self._estimate_breach_days(
                current_risk, slope, self.config.high_risk_threshold
            )

        # Generate recommendations
        recommendations = self._generate_recommendations(
            current_risk, pred_90d, trend, factors
        )

        # Determine priority
        if will_exceed and (breach_days and breach_days < 30):
            priority = "HIGH"
        elif trend == TrendDirection.INCREASING:
            priority = "MEDIUM"
        else:
            priority = "LOW"

        # Assess data quality
        data_quality = self._assess_data_quality(risk_history)

        return RiskPrediction(
            entity_id=entity_id,
            entity_type=entity_type,
            current_risk=current_risk,
            prediction_30d=pred_30d,
            prediction_60d=pred_60d,
            prediction_90d=pred_90d,
            trend=trend,
            trend_slope=slope,
            confidence=confidence,
            data_quality=data_quality,
            factors=factors,
            primary_driver=primary_driver,
            will_exceed_threshold=will_exceed,
            threshold_breach_days=breach_days,
            recommended_actions=recommendations,
            priority=priority,
        )

    def _calculate_trend(
        self,
        risk_history: List[float]
    ) -> Tuple[float, float]:
        """Calculate trend using linear regression."""
        n = len(risk_history)
        x = list(range(n))
        y = risk_history

        # Calculate means
        x_mean = sum(x) / n
        y_mean = sum(y) / n

        # Calculate slope
        numerator = sum((x[i] - x_mean) * (y[i] - y_mean) for i in range(n))
        denominator = sum((x[i] - x_mean) ** 2 for i in range(n))

        if denominator == 0:
            return 0, 0.5

        slope = numerator / denominator

        # Calculate R-squared for confidence
        y_pred = [slope * x[i] + (y_mean - slope * x_mean) for i in range(n)]
        ss_res = sum((y[i] - y_pred[i]) ** 2 for i in range(n))
        ss_tot = sum((y[i] - y_mean) ** 2 for i in range(n))

        if ss_tot == 0:
            r_squared = 1.0
        else:
            r_squared = 1 - (ss_res / ss_tot)

        # Convert slope to weekly rate (assuming weekly data points)
        weekly_slope = slope

        return weekly_slope, max(0, min(1, r_squared))

    def _project_risk(
        self,
        current_risk: float,
        slope: float,
        days: int,
        features: Dict[str, float]
    ) -> float:
        """Project risk to future date."""
        weeks = days / 7

        # Base projection from trend
        base_projection = current_risk + slope * weeks

        # Adjust for features
        adjustment = 0

        # Access growth factor
        access_growth = features.get("access_growth_rate", 0)
        adjustment += access_growth * self.config.access_growth_weight * weeks

        # Privilege creep
        privilege_creep = features.get("privilege_creep", 0)
        adjustment += privilege_creep * self.config.privilege_creep_weight * weeks

        # Peer deviation
        peer_deviation = features.get("peer_deviation", 0)
        adjustment += peer_deviation * self.config.peer_deviation_weight

        # Review delays (increases risk)
        review_delay = features.get("review_delay_weeks", 0)
        adjustment += review_delay * self.config.review_delay_weight

        projected = base_projection + adjustment

        # Apply dampening for longer horizons (uncertainty)
        dampening = 1 - (days / 365) * 0.2
        projected = current_risk + (projected - current_risk) * dampening

        # Clamp to valid range
        return max(0, min(100, projected))

    def _calculate_factors(
        self,
        risk_history: List[float],
        features: Dict[str, float]
    ) -> Dict[str, float]:
        """Calculate contribution of each factor to risk change."""
        factors = {}

        # Trend contribution
        if len(risk_history) >= 2:
            recent_change = risk_history[-1] - risk_history[-2]
            factors["trend"] = recent_change * self.config.trend_weight

        # Access growth
        access_growth = features.get("access_growth_rate", 0)
        factors["access_growth"] = access_growth * self.config.access_growth_weight * 10

        # Privilege creep
        privilege_creep = features.get("privilege_creep", 0)
        factors["privilege_creep"] = privilege_creep * self.config.privilege_creep_weight * 10

        # Peer deviation
        peer_deviation = features.get("peer_deviation", 0)
        factors["peer_deviation"] = peer_deviation * self.config.peer_deviation_weight * 10

        # Review delays
        review_delay = features.get("review_delay_weeks", 0)
        factors["review_delay"] = review_delay * self.config.review_delay_weight

        return factors

    def _estimate_breach_days(
        self,
        current_risk: float,
        slope: float,
        threshold: float
    ) -> Optional[int]:
        """Estimate days until threshold breach."""
        if slope <= 0:
            return None

        risk_gap = threshold - current_risk
        weeks_to_breach = risk_gap / slope

        if weeks_to_breach < 0:
            return 0

        return int(weeks_to_breach * 7)

    def _generate_recommendations(
        self,
        current_risk: float,
        predicted_risk: float,
        trend: TrendDirection,
        factors: Dict[str, float]
    ) -> List[str]:
        """Generate actionable recommendations."""
        recommendations = []

        if trend == TrendDirection.INCREASING:
            recommendations.append("Schedule access review within 30 days")

        # Factor-specific recommendations
        if factors.get("access_growth", 0) > 5:
            recommendations.append("Review recent role assignments for necessity")

        if factors.get("privilege_creep", 0) > 5:
            recommendations.append("Remove unused privileges identified in usage analysis")

        if factors.get("peer_deviation", 0) > 5:
            recommendations.append("Compare access to peer group and justify deviations")

        if factors.get("review_delay", 0) > 2:
            recommendations.append("Complete overdue access certification")

        if predicted_risk > self.config.high_risk_threshold:
            recommendations.append("Prioritize for immediate risk remediation")

        if predicted_risk > current_risk + 20:
            recommendations.append("Implement additional monitoring controls")

        # Default recommendation
        if not recommendations:
            recommendations.append("Continue regular monitoring")

        return recommendations[:5]

    def _assess_data_quality(self, risk_history: List[float]) -> str:
        """Assess quality of historical data."""
        if len(risk_history) >= 12:
            return "HIGH"
        elif len(risk_history) >= 6:
            return "MEDIUM"
        else:
            return "LOW"

    def _empty_prediction(
        self,
        entity_id: str,
        entity_type: str
    ) -> RiskPrediction:
        """Return empty prediction when no data available."""
        return RiskPrediction(
            entity_id=entity_id,
            entity_type=entity_type,
            current_risk=0,
            prediction_30d=0,
            prediction_60d=0,
            prediction_90d=0,
            trend=TrendDirection.STABLE,
            trend_slope=0,
            confidence=0,
            data_quality="LOW",
            recommended_actions=["Collect more historical data for accurate predictions"],
        )

    def predict_batch(
        self,
        entities: List[Dict[str, Any]]
    ) -> List[RiskPrediction]:
        """
        Predict risk for multiple entities.

        Args:
            entities: List of dicts with entity_id, entity_type, risk_history, features

        Returns:
            List of RiskPrediction
        """
        return [
            self.predict(
                entity_id=e["entity_id"],
                entity_type=e.get("entity_type", "USER"),
                risk_history=e.get("risk_history", []),
                features=e.get("features", {}),
            )
            for e in entities
        ]

    def get_high_risk_forecasts(
        self,
        predictions: List[RiskPrediction],
        horizon: PredictionHorizon = PredictionHorizon.DAYS_90
    ) -> List[RiskPrediction]:
        """Get entities forecasted to exceed risk threshold."""
        threshold = self.config.high_risk_threshold

        high_risk = []
        for pred in predictions:
            if horizon == PredictionHorizon.DAYS_30:
                forecast = pred.prediction_30d
            elif horizon == PredictionHorizon.DAYS_60:
                forecast = pred.prediction_60d
            else:
                forecast = pred.prediction_90d

            if forecast > threshold:
                high_risk.append(pred)

        return sorted(high_risk, key=lambda p: p.prediction_90d, reverse=True)
