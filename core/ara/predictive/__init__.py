# Predictive Access Risk Engine
# Forecasting risk 30/60/90 days ahead

"""
Predictive Risk Engine for GOVERNEX+.

SAP GRC answers: "Is there a risk today?"
GOVERNEX+ answers: "Who will become risky, when, and why?"

This enables pre-emptive governance, not reactive cleanup.

Prediction horizons:
- 30 days (operational)
- 60 days (managerial)
- 90 days (strategic)
"""

from .engine import (
    PredictiveRiskEngine,
    PredictionConfig,
    RiskPrediction,
    PredictionHorizon,
    TrendDirection,
)

from .features import (
    PredictiveFeatureSet,
    FeatureImportance,
    build_prediction_features,
)

from .refactor import (
    RoleRefactorEngine,
    RefactorSuggestion,
    RoleSplitRecommendation,
    PrivilegeAnalysis,
)

__all__ = [
    # Engine
    "PredictiveRiskEngine",
    "PredictionConfig",
    "RiskPrediction",
    "PredictionHorizon",
    "TrendDirection",
    # Features
    "PredictiveFeatureSet",
    "FeatureImportance",
    "build_prediction_features",
    # Refactoring
    "RoleRefactorEngine",
    "RefactorSuggestion",
    "RoleSplitRecommendation",
    "PrivilegeAnalysis",
]
