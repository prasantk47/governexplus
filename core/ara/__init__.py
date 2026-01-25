# Access Risk Analysis (ARA) Module
# GOVERNEX+ Advanced Risk Intelligence Engine

"""
Access Risk Analysis (ARA) for GOVERNEX+

This module provides comprehensive access risk analysis capabilities
that exceed SAP GRC functionality:

Core Capabilities:
- Segregation of Duties (SoD) analysis
- Sensitive access detection
- Critical action identification
- Risk simulation (pre-provisioning)

Advanced Features:
- Real-time risk evaluation
- Context-aware risk scoring
- Dynamic risk calculation
- Usage-based risk analysis
- Behavioral anomaly detection

ML Intelligence:
- Unsupervised anomaly detection (Isolation Forest)
- Peer group behavior comparison
- Trend-based risk prediction
- Explainable ML scores

Real-Time Streaming:
- Kafka-based event processing
- Sub-second risk evaluation
- Real-time alerts
- Audit trail generation

Graph-Based SoD:
- Indirect SoD violation detection
- Multi-step risk path analysis
- Toxic role discovery
- Auto-generated SoD rules

LLM Summarization:
- Human-readable risk explanations
- Executive-grade narratives
- Audit-safe summarization

Predictive Risk:
- 30/60/90 day risk forecasting
- Trend analysis
- Early warning system

Auto-Approval:
- Risk-based approval routing
- Policy-as-code workflows

Continuous Control Monitoring:
- Real-time control evaluation
- Control health scores
- Audit evidence generation

SAP GRC answers: "Is there a risk?"
GOVERNEX+ answers: "How risky is it, why, right now, and what should we do?"
"""

from .models import (
    # Risk Models
    Risk,
    RiskSeverity,
    RiskCategory,
    RiskStatus,
    RiskType,
    # SoD Models
    SoDRule,
    SoDConflict,
    SoDRuleSet,
    # Context Models
    RiskContext,
    UserContext,
    # Analysis Results
    RiskAnalysisResult,
    SimulationResult,
    RemediationSuggestion,
)

from .engine import (
    AccessRiskEngine,
    SoDAnalyzer,
    SensitiveAccessAnalyzer,
    RiskScorer,
)

from .rules import (
    RuleEngine,
    RuleDefinition,
    RuleCondition,
)

from .mitigation import (
    MitigationControl,
    MitigationManager,
)

from .analytics import (
    RiskAnalytics,
    RiskTrendAnalyzer,
)

# ML Components
from .ml import (
    AnomalyScorer,
    ZScoreDetector,
    EWMATrendDetector,
    FeatureExtractor,
    BehaviorFeatureVector,
    PeerGroupAnalyzer,
)

# Streaming Components
from .streaming import (
    ARARealTimePipeline,
    PipelineConfig,
    AccessEvent,
    FirefighterEvent,
    RiskResultEvent,
    AuditEvent,
)

# Graph-Based SoD Components
from .graph import (
    SoDGraph,
    NodeType,
    EdgeType,
    RiskPattern,
    RiskPatternLibrary,
    GraphSoDDetector,
    GraphSoDFinding,
    ToxicRoleDetector,
    ToxicRoleFinding,
    SoDRuleGenerator,
    GeneratedSoDRule,
)

# LLM Components
from .llm import (
    RiskSummarizer,
    SummaryConfig,
    RiskSummaryResult,
    ExecutiveNarrativeGenerator,
    ExecutiveNarrative,
)

# Auto-Approval Components
from .approval import (
    AutoApprovalEngine,
    ApprovalDecision,
    ApprovalLevel,
    ApprovalConfig,
    ApprovalRequest,
    ApprovalResult,
    PolicyEngine,
    ApprovalPolicy,
)

# Predictive Risk Components
from .predictive import (
    PredictiveRiskEngine,
    PredictionConfig,
    RiskPrediction,
    PredictiveFeatureSet,
    RoleRefactorEngine,
    RefactorSuggestion,
)

# Continuous Control Monitoring Components
from .ccm import (
    Control,
    ControlType,
    ControlFrequency,
    ControlEngine,
    ControlEvaluationResult,
    ControlViolation,
    ControlMonitor,
    ControlLibrary,
    BUILTIN_CONTROLS,
)

__all__ = [
    # Models
    "Risk",
    "RiskSeverity",
    "RiskCategory",
    "RiskStatus",
    "RiskType",
    "SoDRule",
    "SoDConflict",
    "SoDRuleSet",
    "RiskContext",
    "UserContext",
    "RiskAnalysisResult",
    "SimulationResult",
    "RemediationSuggestion",
    # Engine
    "AccessRiskEngine",
    "SoDAnalyzer",
    "SensitiveAccessAnalyzer",
    "RiskScorer",
    # Rules
    "RuleEngine",
    "RuleDefinition",
    "RuleCondition",
    # Mitigation
    "MitigationControl",
    "MitigationManager",
    # Analytics
    "RiskAnalytics",
    "RiskTrendAnalyzer",
    # ML
    "AnomalyScorer",
    "ZScoreDetector",
    "EWMATrendDetector",
    "FeatureExtractor",
    "BehaviorFeatureVector",
    "PeerGroupAnalyzer",
    # Streaming
    "ARARealTimePipeline",
    "PipelineConfig",
    "AccessEvent",
    "FirefighterEvent",
    "RiskResultEvent",
    "AuditEvent",
    # Graph-Based SoD
    "SoDGraph",
    "NodeType",
    "EdgeType",
    "RiskPattern",
    "RiskPatternLibrary",
    "GraphSoDDetector",
    "GraphSoDFinding",
    "ToxicRoleDetector",
    "ToxicRoleFinding",
    "SoDRuleGenerator",
    "GeneratedSoDRule",
    # LLM
    "RiskSummarizer",
    "SummaryConfig",
    "RiskSummaryResult",
    "ExecutiveNarrativeGenerator",
    "ExecutiveNarrative",
    # Auto-Approval
    "AutoApprovalEngine",
    "ApprovalDecision",
    "ApprovalLevel",
    "ApprovalConfig",
    "ApprovalRequest",
    "ApprovalResult",
    "PolicyEngine",
    "ApprovalPolicy",
    # Predictive Risk
    "PredictiveRiskEngine",
    "PredictionConfig",
    "RiskPrediction",
    "PredictiveFeatureSet",
    "RoleRefactorEngine",
    "RefactorSuggestion",
    # Continuous Control Monitoring
    "Control",
    "ControlType",
    "ControlFrequency",
    "ControlEngine",
    "ControlEvaluationResult",
    "ControlViolation",
    "ControlMonitor",
    "ControlLibrary",
    "BUILTIN_CONTROLS",
]
