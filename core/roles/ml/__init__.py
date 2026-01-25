# Role Design ML Module
# AI-Assisted Role Engineering

"""
ML-Powered Role Design for GOVERNEX+.

SAP GRC starts from roles.
GOVERNEX+ starts from behavior.

Capabilities:
- Behavior clustering (discover real job patterns)
- Role blueprint generation from clusters
- Auto role refactoring suggestions
- Predictive role risk
- Model governance & registry
"""

from .features import (
    RoleFeatureExtractor,
    UserRoleFeatures,
    FeatureSet,
    FeatureImportance,
)

from .clustering import (
    BehaviorClusterer,
    ClusterResult,
    ClusterProfile,
    ClusteringConfig,
)

from .blueprints import (
    RoleBlueprintGenerator,
    RoleBlueprint,
    BlueprintSuggestion,
    BlueprintValidation,
)

from .registry import (
    ModelRegistry,
    RegisteredModel,
    ModelVersion,
    ModelMetrics,
    ModelStatus,
)

from .training import (
    TrainingPipeline,
    TrainingConfig,
    TrainingResult,
    DataSplit,
)

__all__ = [
    # Features
    "RoleFeatureExtractor",
    "UserRoleFeatures",
    "FeatureSet",
    "FeatureImportance",
    # Clustering
    "BehaviorClusterer",
    "ClusterResult",
    "ClusterProfile",
    "ClusteringConfig",
    # Blueprints
    "RoleBlueprintGenerator",
    "RoleBlueprint",
    "BlueprintSuggestion",
    "BlueprintValidation",
    # Registry
    "ModelRegistry",
    "RegisteredModel",
    "ModelVersion",
    "ModelMetrics",
    "ModelStatus",
    # Training
    "TrainingPipeline",
    "TrainingConfig",
    "TrainingResult",
    "DataSplit",
]
