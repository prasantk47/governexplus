# ARA Machine Learning Module
# Intelligent anomaly detection for GOVERNEX+

"""
ML-based Anomaly Detection for Access Risk Analysis.

Provides:
- Unsupervised anomaly scoring (Isolation Forest)
- Feature-level explainability
- Z-Score deviation detection
- Peer comparison scoring
- Trend analysis (EWMA)

Design Principles:
- ML is assistive, not authoritative
- All decisions are explainable
- Fallback to rules if ML unavailable
- Auditor-safe and compliant
"""

from .anomaly_scorer import (
    AnomalyScorer,
    ZScoreDetector,
    EWMATrendDetector,
)
from .features import (
    FeatureExtractor,
    BehaviorFeatureVector,
    extract_user_features,
    extract_session_features,
)
from .peer_analysis import (
    PeerGroupAnalyzer,
    PeerDeviationResult,
)

__all__ = [
    # Anomaly scoring
    "AnomalyScorer",
    "ZScoreDetector",
    "EWMATrendDetector",
    # Features
    "FeatureExtractor",
    "BehaviorFeatureVector",
    "extract_user_features",
    "extract_session_features",
    # Peer analysis
    "PeerGroupAnalyzer",
    "PeerDeviationResult",
]
