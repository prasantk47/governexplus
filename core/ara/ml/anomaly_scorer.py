# ML-based Anomaly Scorer for ARA
# Unsupervised, Explainable, Audit-Safe

"""
Anomaly Scoring for Access Risk Analysis.

Provides multiple detection methods:
- Isolation Forest (primary)
- Z-Score deviation (fallback)
- EWMA trend detection (optional)

Design Principles:
- ML is assistive, not authoritative
- All scores are explainable
- Deterministic fallback available
- Auditor-safe and compliant
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import logging
import statistics
import math

# Optional: sklearn for Isolation Forest
try:
    from sklearn.ensemble import IsolationForest
    from sklearn.preprocessing import StandardScaler
    import numpy as np
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False

from .features import BehaviorFeatureVector

logger = logging.getLogger(__name__)


@dataclass
class AnomalyResult:
    """
    Result of anomaly scoring.

    Designed to be explainable and auditor-friendly.
    """
    user_id: str
    is_anomaly: bool = False
    anomaly_score: float = 0.0  # -1 to 1 (negative = more anomalous)
    risk_adjustment: int = 0  # Points to add to risk score (0-30)

    # Explainability
    explanation: str = ""
    contributing_features: List[str] = field(default_factory=list)
    feature_deviations: Dict[str, float] = field(default_factory=dict)

    # Metadata
    method_used: str = "isolation_forest"
    confidence: float = 0.0
    scored_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "is_anomaly": self.is_anomaly,
            "anomaly_score": round(self.anomaly_score, 4),
            "risk_adjustment": self.risk_adjustment,
            "explanation": self.explanation,
            "contributing_features": self.contributing_features,
            "feature_deviations": {k: round(v, 4) for k, v in self.feature_deviations.items()},
            "method_used": self.method_used,
            "confidence": round(self.confidence, 4),
            "scored_at": self.scored_at.isoformat(),
        }


class AnomalyScorer:
    """
    ML-based anomaly scorer using Isolation Forest.

    Key features:
    - Unsupervised (no labels required)
    - Explainable (feature contribution analysis)
    - Audit-safe (deterministic fallback)
    """

    # Risk adjustment thresholds
    HIGH_ANOMALY_ADJUSTMENT = 25
    MEDIUM_ANOMALY_ADJUSTMENT = 15
    LOW_ANOMALY_ADJUSTMENT = 5

    def __init__(
        self,
        contamination: float = 0.05,
        n_estimators: int = 100,
        random_state: int = 42
    ):
        """
        Initialize anomaly scorer.

        Args:
            contamination: Expected proportion of anomalies (0.01-0.1)
            n_estimators: Number of trees in Isolation Forest
            random_state: For reproducibility
        """
        self.contamination = contamination
        self.n_estimators = n_estimators
        self.random_state = random_state

        self.model = None
        self.scaler = None
        self.is_trained = False
        self.training_stats: Dict[str, Dict[str, float]] = {}
        self.feature_names: List[str] = []

        if HAS_SKLEARN:
            self._init_model()
        else:
            logger.warning("sklearn not available, using Z-score fallback")

    def _init_model(self):
        """Initialize sklearn models."""
        self.model = IsolationForest(
            n_estimators=self.n_estimators,
            contamination=self.contamination,
            random_state=self.random_state,
            n_jobs=-1
        )
        self.scaler = StandardScaler()

    def train(
        self,
        historical_vectors: List[BehaviorFeatureVector],
        feature_names: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Train anomaly detection model on historical data.

        Args:
            historical_vectors: List of feature vectors from normal behavior
            feature_names: Optional list of feature names

        Returns:
            Training statistics
        """
        if not historical_vectors:
            logger.warning("No training data provided")
            return {"status": "error", "message": "No training data"}

        self.feature_names = feature_names or BehaviorFeatureVector.feature_names()

        # Convert to numpy array
        X_raw = [v.to_vector() for v in historical_vectors]

        if HAS_SKLEARN:
            X = np.array(X_raw)

            # Fit scaler
            self.scaler.fit(X)
            X_scaled = self.scaler.transform(X)

            # Fit Isolation Forest
            self.model.fit(X_scaled)

            # Calculate training statistics for explainability
            for i, name in enumerate(self.feature_names):
                col = X[:, i]
                self.training_stats[name] = {
                    "mean": float(np.mean(col)),
                    "std": float(np.std(col)),
                    "min": float(np.min(col)),
                    "max": float(np.max(col)),
                    "median": float(np.median(col)),
                }

            self.is_trained = True
            logger.info(f"Trained anomaly scorer on {len(historical_vectors)} samples")

            return {
                "status": "trained",
                "samples": len(historical_vectors),
                "features": len(self.feature_names),
                "contamination": self.contamination,
            }
        else:
            # Fallback: calculate statistics for Z-score
            for i, name in enumerate(self.feature_names):
                col = [v[i] for v in X_raw]
                self.training_stats[name] = {
                    "mean": statistics.mean(col) if col else 0,
                    "std": statistics.stdev(col) if len(col) > 1 else 1,
                    "min": min(col) if col else 0,
                    "max": max(col) if col else 0,
                }

            self.is_trained = True
            return {
                "status": "trained_zscore",
                "samples": len(historical_vectors),
                "features": len(self.feature_names),
            }

    def score(
        self,
        feature_vector: BehaviorFeatureVector
    ) -> AnomalyResult:
        """
        Score a feature vector for anomalies.

        Args:
            feature_vector: User behavior features

        Returns:
            AnomalyResult with score and explanation
        """
        result = AnomalyResult(user_id=feature_vector.user_id)

        if not self.is_trained:
            result.explanation = "ML model not trained - using default scoring"
            result.method_used = "untrained"
            return result

        X_raw = feature_vector.to_vector()

        if HAS_SKLEARN and self.model is not None:
            result = self._score_isolation_forest(feature_vector, X_raw)
        else:
            result = self._score_zscore(feature_vector, X_raw)

        return result

    def _score_isolation_forest(
        self,
        feature_vector: BehaviorFeatureVector,
        X_raw: List[float]
    ) -> AnomalyResult:
        """Score using Isolation Forest."""
        result = AnomalyResult(
            user_id=feature_vector.user_id,
            method_used="isolation_forest"
        )

        X = np.array([X_raw])
        X_scaled = self.scaler.transform(X)

        # Get anomaly score (-1 = anomaly, 1 = normal)
        raw_score = self.model.decision_function(X_scaled)[0]
        prediction = self.model.predict(X_scaled)[0]

        result.anomaly_score = float(raw_score)
        result.is_anomaly = prediction == -1

        # Calculate risk adjustment based on score severity
        if result.is_anomaly:
            if raw_score < -0.3:
                result.risk_adjustment = self.HIGH_ANOMALY_ADJUSTMENT
            elif raw_score < -0.15:
                result.risk_adjustment = self.MEDIUM_ANOMALY_ADJUSTMENT
            else:
                result.risk_adjustment = self.LOW_ANOMALY_ADJUSTMENT

        # Feature contribution analysis
        deviations = self._calculate_feature_deviations(X_raw)
        result.feature_deviations = deviations
        result.contributing_features = self._identify_contributing_features(deviations)

        # Generate explanation
        result.explanation = self._generate_explanation(result)
        result.confidence = self._calculate_confidence(raw_score)

        return result

    def _score_zscore(
        self,
        feature_vector: BehaviorFeatureVector,
        X_raw: List[float]
    ) -> AnomalyResult:
        """Score using Z-score method (fallback)."""
        result = AnomalyResult(
            user_id=feature_vector.user_id,
            method_used="zscore"
        )

        # Calculate Z-scores for each feature
        z_scores = {}
        total_z = 0

        for i, name in enumerate(self.feature_names):
            stats = self.training_stats.get(name, {})
            mean = stats.get("mean", 0)
            std = stats.get("std", 1)

            if std > 0:
                z = (X_raw[i] - mean) / std
            else:
                z = 0

            z_scores[name] = z
            total_z += abs(z)

        # Average absolute Z-score
        avg_z = total_z / len(self.feature_names) if self.feature_names else 0

        # Determine if anomaly (threshold: 2 standard deviations on average)
        result.is_anomaly = avg_z > 2.0
        result.anomaly_score = -avg_z / 3  # Normalize to -1 to 0 range

        if result.is_anomaly:
            if avg_z > 3:
                result.risk_adjustment = self.HIGH_ANOMALY_ADJUSTMENT
            elif avg_z > 2.5:
                result.risk_adjustment = self.MEDIUM_ANOMALY_ADJUSTMENT
            else:
                result.risk_adjustment = self.LOW_ANOMALY_ADJUSTMENT

        result.feature_deviations = z_scores
        result.contributing_features = [
            name for name, z in z_scores.items() if abs(z) > 2
        ]

        result.explanation = self._generate_explanation(result)
        result.confidence = min(0.9, avg_z / 5) if result.is_anomaly else 0.5

        return result

    def _calculate_feature_deviations(
        self,
        X_raw: List[float]
    ) -> Dict[str, float]:
        """Calculate how much each feature deviates from training data."""
        deviations = {}

        for i, name in enumerate(self.feature_names):
            stats = self.training_stats.get(name, {})
            mean = stats.get("mean", 0)
            std = stats.get("std", 1)

            if std > 0:
                z = (X_raw[i] - mean) / std
            else:
                z = 0

            deviations[name] = z

        return deviations

    def _identify_contributing_features(
        self,
        deviations: Dict[str, float],
        threshold: float = 1.5
    ) -> List[str]:
        """Identify features that contribute most to anomaly."""
        contributing = [
            name for name, z in deviations.items()
            if abs(z) > threshold
        ]
        # Sort by deviation magnitude
        contributing.sort(key=lambda x: abs(deviations[x]), reverse=True)
        return contributing[:5]  # Top 5

    def _generate_explanation(self, result: AnomalyResult) -> str:
        """Generate human-readable explanation."""
        if not result.is_anomaly:
            return "Behavior within normal range"

        explanations = []

        # Map features to human-readable descriptions
        feature_descriptions = {
            "tcode_exec_count": "transaction volume",
            "sensitive_tcode_ratio": "sensitive transaction usage",
            "after_hours_ratio": "off-hours activity",
            "weekend_ratio": "weekend activity",
            "unused_privilege_ratio": "unused privileges",
            "peer_deviation_score": "deviation from peers",
            "volume_vs_peer_ratio": "activity compared to peers",
            "sod_conflict_count": "segregation of duties conflicts",
            "failed_auth_count": "failed authentication attempts",
        }

        for feature in result.contributing_features[:3]:
            deviation = result.feature_deviations.get(feature, 0)
            desc = feature_descriptions.get(feature, feature.replace("_", " "))

            if deviation > 0:
                explanations.append(f"unusually high {desc}")
            else:
                explanations.append(f"unusually low {desc}")

        if explanations:
            return "Behavior deviates significantly: " + ", ".join(explanations)
        else:
            return "Behavior deviates from historical patterns"

    def _calculate_confidence(self, raw_score: float) -> float:
        """Calculate confidence in the anomaly score."""
        # Higher absolute score = higher confidence
        return min(0.95, 0.5 + abs(raw_score) * 0.5)

    def save_model(self, path: str):
        """Save trained model to disk."""
        if not HAS_SKLEARN:
            logger.warning("sklearn not available, saving statistics only")

        import json
        with open(path, 'w') as f:
            json.dump({
                "training_stats": self.training_stats,
                "feature_names": self.feature_names,
                "contamination": self.contamination,
                "is_trained": self.is_trained,
            }, f, indent=2)

    def load_model(self, path: str):
        """Load trained model from disk."""
        import json
        with open(path) as f:
            data = json.load(f)

        self.training_stats = data.get("training_stats", {})
        self.feature_names = data.get("feature_names", [])
        self.contamination = data.get("contamination", 0.05)
        self.is_trained = data.get("is_trained", False)


class ZScoreDetector:
    """
    Simple Z-score based anomaly detector.

    Use when:
    - sklearn is not available
    - Quick baseline detection needed
    - Explainability is paramount
    """

    def __init__(self, threshold: float = 2.0):
        """
        Initialize Z-score detector.

        Args:
            threshold: Z-score threshold for anomaly (default 2.0)
        """
        self.threshold = threshold
        self.baselines: Dict[str, Dict[str, float]] = {}

    def update_baseline(
        self,
        feature_name: str,
        values: List[float]
    ):
        """Update baseline statistics for a feature."""
        if not values:
            return

        self.baselines[feature_name] = {
            "mean": statistics.mean(values),
            "std": statistics.stdev(values) if len(values) > 1 else 1,
            "count": len(values),
        }

    def detect(
        self,
        feature_name: str,
        value: float
    ) -> Tuple[bool, float, str]:
        """
        Detect if value is anomalous.

        Returns:
            Tuple of (is_anomaly, z_score, explanation)
        """
        baseline = self.baselines.get(feature_name)
        if not baseline:
            return False, 0.0, "No baseline available"

        mean = baseline["mean"]
        std = baseline["std"]

        if std == 0:
            return False, 0.0, "Insufficient variance in baseline"

        z_score = (value - mean) / std
        is_anomaly = abs(z_score) > self.threshold

        if is_anomaly:
            direction = "higher" if z_score > 0 else "lower"
            explanation = f"{feature_name} is {abs(z_score):.1f} std dev {direction} than normal"
        else:
            explanation = f"{feature_name} within normal range"

        return is_anomaly, z_score, explanation


class EWMATrendDetector:
    """
    Exponentially Weighted Moving Average trend detector.

    Detects sudden changes in behavior over time.
    """

    def __init__(self, alpha: float = 0.3, threshold_factor: float = 2.0):
        """
        Initialize EWMA detector.

        Args:
            alpha: Smoothing factor (0-1, higher = more weight on recent)
            threshold_factor: Multiplier for threshold
        """
        self.alpha = alpha
        self.threshold_factor = threshold_factor
        self.ewma: Dict[str, float] = {}
        self.ewma_var: Dict[str, float] = {}
        self.initialized: Dict[str, bool] = {}

    def update(
        self,
        metric_name: str,
        value: float
    ) -> Tuple[bool, float, str]:
        """
        Update EWMA and detect anomaly.

        Args:
            metric_name: Name of metric
            value: Current value

        Returns:
            Tuple of (is_anomaly, deviation, explanation)
        """
        if metric_name not in self.initialized:
            # Initialize with first value
            self.ewma[metric_name] = value
            self.ewma_var[metric_name] = 0
            self.initialized[metric_name] = True
            return False, 0.0, "First observation, no baseline"

        # Current EWMA
        prev_ewma = self.ewma[metric_name]
        prev_var = self.ewma_var[metric_name]

        # Update EWMA
        new_ewma = self.alpha * value + (1 - self.alpha) * prev_ewma

        # Update variance estimate
        error = value - prev_ewma
        new_var = self.alpha * (error ** 2) + (1 - self.alpha) * prev_var

        self.ewma[metric_name] = new_ewma
        self.ewma_var[metric_name] = new_var

        # Calculate threshold
        std_dev = math.sqrt(new_var) if new_var > 0 else 0
        threshold = self.threshold_factor * std_dev

        # Detect anomaly
        deviation = abs(value - prev_ewma)
        is_anomaly = deviation > threshold and std_dev > 0

        if is_anomaly:
            direction = "spike" if value > prev_ewma else "drop"
            explanation = f"Sudden {direction} in {metric_name}: {deviation:.2f} (threshold: {threshold:.2f})"
        else:
            explanation = f"{metric_name} following normal trend"

        return is_anomaly, deviation, explanation

    def reset(self, metric_name: Optional[str] = None):
        """Reset detector state."""
        if metric_name:
            self.ewma.pop(metric_name, None)
            self.ewma_var.pop(metric_name, None)
            self.initialized.pop(metric_name, None)
        else:
            self.ewma.clear()
            self.ewma_var.clear()
            self.initialized.clear()
