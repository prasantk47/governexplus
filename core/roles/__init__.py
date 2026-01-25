# Role Design Module
# GOVERNEX+ Intelligent Role Engineering

"""
Role Design for GOVERNEX+

SAP GRC: "Here is a role. Please manage it."
GOVERNEX+: "Here is the safest role design, why it works,
            and how it stays clean automatically."

Capabilities:

1. Role Foundation:
   - Business-aligned role modeling
   - Least-privilege enforcement
   - Role lifecycle management

2. Intelligent Analysis:
   - Usage analytics
   - Risk scoring (0-100)
   - Toxic role detection

3. Role Engineering:
   - Auto decomposition
   - Consolidation
   - Permission clustering

4. Preventive Governance:
   - Pre-build risk simulation
   - Auto-generated SoD rules
   - Certification intelligence

5. Continuous Governance:
   - Real-time control monitoring
   - Drift detection
   - Autonomous cleanup

6. Zero-Trust Features:
   - Risk-based assignment
   - Autonomous revocation
   - Just-Enough-Access (JEA)
"""

from .models import (
    Role,
    RoleType,
    RoleStatus,
    RoleLifecycleState,
    Permission,
    PermissionType,
    AuthorizationObject,
    RoleMetadata,
    RoleVersion,
)

from .analytics import (
    RoleUsageAnalyzer,
    UsageMetrics,
    PermissionUsage,
    UsagePattern,
    UsageTrend,
)

from .scoring import (
    RoleRiskScorer,
    RoleRiskScore,
    RiskFactor,
    RiskTrend,
)

from .engineering import (
    RoleEngineer,
    DecompositionSuggestion,
    ConsolidationSuggestion,
    PermissionCluster,
    RoleDesignRecommendation,
)

from .simulation import (
    RoleSimulator,
    SimulationResult,
    SimulatedRisk,
    SimulationConfig,
    SimulationStatus,
)

from .governance import (
    RoleGovernanceEngine,
    DriftDetector,
    DriftReport,
    ComplianceStatus,
    GovernancePolicy,
)

from .autonomous import (
    AutonomousRoleManager,
    RevocationCandidate,
    AssignmentRecommendation,
    CleanupAction,
    JEAPolicy,
)

from .certification import (
    RoleCertificationEngine,
    CertificationCampaign,
    CertificationDecision,
    CertificationEvidence,
    CertificationStatus,
    DecisionType,
)

from .portfolio import (
    RolePortfolio,
    PortfolioHealth,
    PortfolioMetrics,
    RoleBenchmark,
    RoleSprawlAnalysis,
    PortfolioDashboard,
    HealthLevel,
    MaturityLevel,
    IndustryBenchmark,
)

from .kpis import (
    RoleDesignKPIEngine,
    KPIDashboard,
    KPIValue,
    KPIDefinition,
    KPICategory,
    KPIStatus,
    KPITrend,
)

from .narratives import (
    RoleNarrativeGenerator,
    ExecutiveNarrative,
    NarrativeSection,
    NarrativeType,
    AudienceType,
)

from .rollout import (
    RolloutTimelineTracker,
    RolloutTimeline,
    PhaseDefinition,
    PhaseTask,
    AICheckpoint,
    Phase,
    TaskStatus,
    AICheckpointType,
)

# ML submodule
from .ml import (
    RoleFeatureExtractor,
    UserRoleFeatures,
    FeatureSet,
    FeatureImportance,
    BehaviorClusterer,
    ClusterResult,
    ClusterProfile,
    ClusteringConfig,
    RoleBlueprintGenerator,
    RoleBlueprint,
    BlueprintSuggestion,
    BlueprintValidation,
    ModelRegistry,
    RegisteredModel,
    ModelVersion,
    ModelMetrics,
    ModelStatus,
    TrainingPipeline,
    TrainingConfig,
    TrainingResult,
    DataSplit,
)

__all__ = [
    # Models
    "Role",
    "RoleType",
    "RoleStatus",
    "RoleLifecycleState",
    "Permission",
    "PermissionType",
    "AuthorizationObject",
    "RoleMetadata",
    "RoleVersion",
    # Analytics
    "RoleUsageAnalyzer",
    "UsageMetrics",
    "PermissionUsage",
    "UsagePattern",
    "UsageTrend",
    # Scoring
    "RoleRiskScorer",
    "RoleRiskScore",
    "RiskFactor",
    "RiskTrend",
    # Engineering
    "RoleEngineer",
    "DecompositionSuggestion",
    "ConsolidationSuggestion",
    "PermissionCluster",
    "RoleDesignRecommendation",
    # Simulation
    "RoleSimulator",
    "SimulationResult",
    "SimulatedRisk",
    "SimulationConfig",
    "SimulationStatus",
    # Governance
    "RoleGovernanceEngine",
    "DriftDetector",
    "DriftReport",
    "ComplianceStatus",
    "GovernancePolicy",
    # Autonomous
    "AutonomousRoleManager",
    "RevocationCandidate",
    "AssignmentRecommendation",
    "CleanupAction",
    "JEAPolicy",
    # Certification
    "RoleCertificationEngine",
    "CertificationCampaign",
    "CertificationDecision",
    "CertificationEvidence",
    "CertificationStatus",
    "DecisionType",
    # Portfolio
    "RolePortfolio",
    "PortfolioHealth",
    "PortfolioMetrics",
    "RoleBenchmark",
    "RoleSprawlAnalysis",
    "PortfolioDashboard",
    "HealthLevel",
    "MaturityLevel",
    "IndustryBenchmark",
    # KPIs
    "RoleDesignKPIEngine",
    "KPIDashboard",
    "KPIValue",
    "KPIDefinition",
    "KPICategory",
    "KPIStatus",
    "KPITrend",
    # Narratives
    "RoleNarrativeGenerator",
    "ExecutiveNarrative",
    "NarrativeSection",
    "NarrativeType",
    "AudienceType",
    # Rollout
    "RolloutTimelineTracker",
    "RolloutTimeline",
    "PhaseDefinition",
    "PhaseTask",
    "AICheckpoint",
    "Phase",
    "TaskStatus",
    "AICheckpointType",
    # ML
    "RoleFeatureExtractor",
    "UserRoleFeatures",
    "FeatureSet",
    "FeatureImportance",
    "BehaviorClusterer",
    "ClusterResult",
    "ClusterProfile",
    "ClusteringConfig",
    "RoleBlueprintGenerator",
    "RoleBlueprint",
    "BlueprintSuggestion",
    "BlueprintValidation",
    "ModelRegistry",
    "RegisteredModel",
    "ModelVersion",
    "ModelMetrics",
    "ModelStatus",
    "TrainingPipeline",
    "TrainingConfig",
    "TrainingResult",
    "DataSplit",
]
