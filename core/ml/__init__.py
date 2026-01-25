"""
Machine Learning Module for GRC Platform

Provides AI/ML capabilities including:
- Role Mining and Optimization
- Predictive Risk Scoring
- Anomaly Detection
- Intelligent Access Recommendations
- Natural Language Policy Processing
"""

from .role_mining import RoleMiner, RoleCluster, MiningResult, ClusteringAlgorithm
from .risk_predictor import RiskPredictor, RiskPrediction
from .anomaly_detector import AnomalyDetector, AnomalyAlert, AnomalyType, AnomalySeverity
from .recommender import AccessRecommender, Recommendation, RecommendationType
from .nl_policy import NLPolicyBuilder, ParsedPolicy, PolicyIntent, ExtractedEntity, EntityType

__all__ = [
    'RoleMiner',
    'RoleCluster',
    'MiningResult',
    'ClusteringAlgorithm',
    'RiskPredictor',
    'RiskPrediction',
    'AnomalyDetector',
    'AnomalyAlert',
    'AnomalyType',
    'AnomalySeverity',
    'AccessRecommender',
    'Recommendation',
    'RecommendationType',
    'NLPolicyBuilder',
    'ParsedPolicy',
    'PolicyIntent',
    'ExtractedEntity',
    'EntityType'
]
