# AI/ML Intelligence Module
# Advanced AI capabilities beyond traditional GRC

from .risk_intelligence import (
    RiskIntelligenceEngine, RiskPrediction, RiskFactor,
    ContextualRiskScore, RiskTrend
)
from .nlp_engine import (
    NLPPolicyEngine, PolicyIntent, QueryResult,
    NaturalLanguageQuery
)
from .anomaly_detector import (
    BehavioralAnomalyDetector, AnomalyAlert, UserBehaviorProfile,
    AnomalyType, RiskIndicator
)
from .role_optimizer import (
    AIRoleOptimizer, RoleRecommendation, RoleMiningResult,
    AccessPattern, OptimizationSuggestion
)
from .remediation_advisor import (
    RemediationAdvisor, RemediationPlan, RemediationAction,
    ActionType, ImpactAssessment
)
from .assistant import (
    GRCAssistant, ConversationContext, AssistantResponse,
    QueryType
)

__all__ = [
    # Risk Intelligence
    "RiskIntelligenceEngine",
    "RiskPrediction",
    "RiskFactor",
    "ContextualRiskScore",
    "RiskTrend",
    # NLP Engine
    "NLPPolicyEngine",
    "PolicyIntent",
    "QueryResult",
    "NaturalLanguageQuery",
    # Anomaly Detection
    "BehavioralAnomalyDetector",
    "AnomalyAlert",
    "UserBehaviorProfile",
    "AnomalyType",
    "RiskIndicator",
    # Role Optimization
    "AIRoleOptimizer",
    "RoleRecommendation",
    "RoleMiningResult",
    "AccessPattern",
    "OptimizationSuggestion",
    # Remediation
    "RemediationAdvisor",
    "RemediationPlan",
    "RemediationAction",
    "ActionType",
    "ImpactAssessment",
    # Assistant
    "GRCAssistant",
    "ConversationContext",
    "AssistantResponse",
    "QueryType"
]
