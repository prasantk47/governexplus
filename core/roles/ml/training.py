# Training Pipeline
# End-to-end ML training with governance

"""
Training Pipeline for GOVERNEX+.

Production-grade training with:
- Data validation
- Feature engineering
- Model training
- Evaluation
- Registry integration
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from enum import Enum
import logging

from .features import RoleFeatureExtractor, FeatureSet, UserRoleFeatures
from .clustering import BehaviorClusterer, ClusterResult, ClusteringConfig
from .registry import (
    ModelRegistry, ModelMetrics, TrainingMetadata,
    ModelType, ModelStatus
)

logger = logging.getLogger(__name__)


class TrainingStage(Enum):
    """Stages of training pipeline."""
    DATA_LOADING = "DATA_LOADING"
    DATA_VALIDATION = "DATA_VALIDATION"
    FEATURE_ENGINEERING = "FEATURE_ENGINEERING"
    MODEL_TRAINING = "MODEL_TRAINING"
    EVALUATION = "EVALUATION"
    REGISTRATION = "REGISTRATION"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


@dataclass
class DataSplit:
    """Train/validation/test data split."""
    train_features: FeatureSet
    validation_features: FeatureSet
    test_features: Optional[FeatureSet] = None

    train_ratio: float = 0.7
    validation_ratio: float = 0.15
    test_ratio: float = 0.15

    def to_dict(self) -> Dict[str, Any]:
        return {
            "train_size": len(self.train_features.features),
            "validation_size": len(self.validation_features.features),
            "test_size": len(self.test_features.features) if self.test_features else 0,
            "ratios": {
                "train": self.train_ratio,
                "validation": self.validation_ratio,
                "test": self.test_ratio,
            },
        }


@dataclass
class TrainingConfig:
    """Configuration for training pipeline."""
    # Model settings
    model_name: str = "role_clustering"
    model_type: ModelType = ModelType.CLUSTERING

    # Clustering settings
    clustering_config: Optional[ClusteringConfig] = None
    auto_optimize_k: bool = True
    min_k: int = 2
    max_k: int = 15

    # Data settings
    min_samples: int = 50
    train_ratio: float = 0.7
    validation_ratio: float = 0.15

    # Features
    feature_selection: List[str] = field(default_factory=list)
    normalize_features: bool = True

    # Quality thresholds
    min_silhouette_score: float = 0.3
    max_noise_ratio: float = 0.15

    # Registry
    auto_register: bool = True
    require_approval: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "model_name": self.model_name,
            "model_type": self.model_type.value,
            "auto_optimize_k": self.auto_optimize_k,
            "min_samples": self.min_samples,
            "train_ratio": self.train_ratio,
            "quality_thresholds": {
                "min_silhouette_score": self.min_silhouette_score,
                "max_noise_ratio": self.max_noise_ratio,
            },
        }


@dataclass
class TrainingResult:
    """Result of training pipeline."""
    success: bool = True
    stage: TrainingStage = TrainingStage.COMPLETED

    # Model info
    model_id: Optional[str] = None
    version: Optional[str] = None

    # Results
    cluster_result: Optional[ClusterResult] = None
    metrics: Optional[ModelMetrics] = None

    # Quality
    quality_passed: bool = True
    quality_issues: List[str] = field(default_factory=list)

    # Timing
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    duration_seconds: float = 0.0

    # Errors
    error_message: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "stage": self.stage.value,
            "model_id": self.model_id,
            "version": self.version,
            "metrics": self.metrics.to_dict() if self.metrics else None,
            "quality_passed": self.quality_passed,
            "quality_issues": self.quality_issues,
            "duration_seconds": round(self.duration_seconds, 2),
            "error_message": self.error_message,
        }


class TrainingPipeline:
    """
    End-to-end training pipeline.

    Stages:
    1. Data loading
    2. Data validation
    3. Feature engineering
    4. Model training
    5. Evaluation
    6. Registry integration
    """

    def __init__(
        self,
        registry: Optional[ModelRegistry] = None,
        config: Optional[TrainingConfig] = None
    ):
        """Initialize pipeline."""
        self.registry = registry or ModelRegistry()
        self.config = config or TrainingConfig()
        self.feature_extractor = RoleFeatureExtractor()

    def train(
        self,
        raw_data: List[Dict[str, Any]],
        tcode_data: Optional[Dict[str, List[str]]] = None
    ) -> TrainingResult:
        """
        Run complete training pipeline.

        Args:
            raw_data: Raw user-role data
            tcode_data: Optional tcode usage per user

        Returns:
            TrainingResult with model and metrics
        """
        result = TrainingResult()
        result.started_at = datetime.now()

        try:
            # Stage 1: Data Loading
            result.stage = TrainingStage.DATA_LOADING
            logger.info("Stage 1: Loading data")

            if not raw_data:
                raise ValueError("No data provided")

            # Stage 2: Data Validation
            result.stage = TrainingStage.DATA_VALIDATION
            logger.info("Stage 2: Validating data")

            validation_errors = self._validate_data(raw_data)
            if validation_errors:
                result.quality_issues.extend(validation_errors)
                if len(raw_data) < self.config.min_samples:
                    raise ValueError(f"Insufficient samples: {len(raw_data)} < {self.config.min_samples}")

            # Stage 3: Feature Engineering
            result.stage = TrainingStage.FEATURE_ENGINEERING
            logger.info("Stage 3: Engineering features")

            feature_set = self.feature_extractor.extract_batch(raw_data)
            logger.info(f"Extracted {len(feature_set.features)} feature vectors")

            # Split data
            data_split = self._split_data(feature_set)

            # Stage 4: Model Training
            result.stage = TrainingStage.MODEL_TRAINING
            logger.info("Stage 4: Training model")

            # Configure clustering
            clustering_config = self.config.clustering_config or ClusteringConfig()

            if self.config.auto_optimize_k:
                clusterer = BehaviorClusterer(clustering_config)
                optimal = clusterer.find_optimal_k(
                    data_split.train_features,
                    self.config.min_k,
                    self.config.max_k
                )
                clustering_config.n_clusters = optimal["optimal_k"]
                logger.info(f"Optimal k={clustering_config.n_clusters}")

            # Train
            clusterer = BehaviorClusterer(clustering_config)
            cluster_result = clusterer.cluster(
                data_split.train_features,
                tcode_data
            )
            result.cluster_result = cluster_result

            # Stage 5: Evaluation
            result.stage = TrainingStage.EVALUATION
            logger.info("Stage 5: Evaluating model")

            # Validate on validation set
            validation_result = clusterer.cluster(
                data_split.validation_features,
                tcode_data
            )

            metrics = ModelMetrics(
                silhouette_score=cluster_result.silhouette_score,
                inertia=cluster_result.inertia,
                cluster_count=cluster_result.n_clusters,
                training_samples=len(data_split.train_features.features),
                validation_samples=len(data_split.validation_features.features),
            )
            result.metrics = metrics

            # Quality checks
            quality_passed, quality_issues = self._check_quality(
                cluster_result, validation_result
            )
            result.quality_passed = quality_passed
            result.quality_issues.extend(quality_issues)

            # Stage 6: Registration
            result.stage = TrainingStage.REGISTRATION
            logger.info("Stage 6: Registering model")

            if self.config.auto_register:
                model, version = self._register_model(
                    cluster_result, metrics, data_split, raw_data
                )
                result.model_id = model.model_id
                result.version = version.version

            # Complete
            result.stage = TrainingStage.COMPLETED
            result.success = True
            result.completed_at = datetime.now()
            result.duration_seconds = (
                result.completed_at - result.started_at
            ).total_seconds()

            logger.info(f"Training completed successfully in {result.duration_seconds:.2f}s")

        except Exception as e:
            result.success = False
            result.stage = TrainingStage.FAILED
            result.error_message = str(e)
            result.completed_at = datetime.now()
            result.duration_seconds = (
                result.completed_at - result.started_at
            ).total_seconds()
            logger.error(f"Training failed: {e}")

        return result

    def _validate_data(self, raw_data: List[Dict[str, Any]]) -> List[str]:
        """Validate input data."""
        issues = []

        if len(raw_data) < self.config.min_samples:
            issues.append(
                f"Sample count ({len(raw_data)}) below minimum ({self.config.min_samples})"
            )

        # Check required fields
        required = ["user_id", "role_id"]
        for i, record in enumerate(raw_data[:10]):  # Check first 10
            for field in required:
                if field not in record:
                    issues.append(f"Record {i} missing required field: {field}")
                    break

        # Check for duplicates
        user_role_pairs = set()
        duplicates = 0
        for record in raw_data:
            key = (record.get("user_id"), record.get("role_id"))
            if key in user_role_pairs:
                duplicates += 1
            user_role_pairs.add(key)

        if duplicates > 0:
            issues.append(f"Found {duplicates} duplicate user-role pairs")

        return issues

    def _split_data(self, feature_set: FeatureSet) -> DataSplit:
        """Split data into train/validation/test."""
        features = feature_set.features
        n = len(features)

        train_end = int(n * self.config.train_ratio)
        val_end = int(n * (self.config.train_ratio + self.config.validation_ratio))

        train_features = FeatureSet(
            name=f"{feature_set.name}_train",
            description="Training split",
            features=features[:train_end],
        )

        validation_features = FeatureSet(
            name=f"{feature_set.name}_validation",
            description="Validation split",
            features=features[train_end:val_end],
        )

        test_features = FeatureSet(
            name=f"{feature_set.name}_test",
            description="Test split",
            features=features[val_end:],
        ) if val_end < n else None

        return DataSplit(
            train_features=train_features,
            validation_features=validation_features,
            test_features=test_features,
            train_ratio=self.config.train_ratio,
            validation_ratio=self.config.validation_ratio,
        )

    def _check_quality(
        self,
        train_result: ClusterResult,
        validation_result: ClusterResult
    ) -> Tuple[bool, List[str]]:
        """Check model quality."""
        issues = []
        passed = True

        # Check silhouette score
        if train_result.silhouette_score < self.config.min_silhouette_score:
            issues.append(
                f"Silhouette score ({train_result.silhouette_score:.3f}) "
                f"below threshold ({self.config.min_silhouette_score})"
            )
            passed = False

        # Check noise ratio
        total_points = len(train_result.user_assignments) + len(train_result.noise_points)
        if total_points > 0:
            noise_ratio = len(train_result.noise_points) / total_points
            if noise_ratio > self.config.max_noise_ratio:
                issues.append(
                    f"Noise ratio ({noise_ratio:.2%}) exceeds threshold ({self.config.max_noise_ratio:.2%})"
                )
                passed = False

        # Check cluster stability (compare train vs validation)
        if abs(train_result.n_clusters - validation_result.n_clusters) > 2:
            issues.append(
                f"Cluster count unstable: train={train_result.n_clusters}, "
                f"validation={validation_result.n_clusters}"
            )

        # Check for degenerate clusters
        for cluster in train_result.clusters:
            if cluster.member_count < 3:
                issues.append(f"Cluster {cluster.cluster_id} has only {cluster.member_count} members")

        return passed, issues

    def _register_model(
        self,
        cluster_result: ClusterResult,
        metrics: ModelMetrics,
        data_split: DataSplit,
        raw_data: List[Dict[str, Any]]
    ) -> Tuple[Any, Any]:
        """Register model with registry."""
        # Register model
        model = self.registry.register_model(
            name=self.config.model_name,
            description=f"Role clustering model with {cluster_result.n_clusters} clusters",
            model_type=self.config.model_type,
            deterministic_fallback="USE_DEFAULT_ROLE_ASSIGNMENT",
        )

        # Create training metadata
        training_metadata = TrainingMetadata(
            training_end=datetime.now(),
            data_source="batch_training",
            sample_count=len(raw_data),
            features_used=UserRoleFeatures.feature_names(),
            feature_count=len(UserRoleFeatures.feature_names()),
            hyperparameters=cluster_result.config.to_dict() if cluster_result.config else {},
            data_hash=self.registry.generate_data_hash(raw_data[:100]),  # Hash first 100
        )
        training_metadata.training_duration_seconds = (
            training_metadata.training_end - training_metadata.training_start
        ).total_seconds()

        # Calculate feature importance (based on cluster separation contribution)
        feature_importance = self._calculate_feature_importance(cluster_result)

        # Add version
        version = self.registry.add_version(
            model_id=model.model_id,
            metrics=metrics,
            training_metadata=training_metadata,
            feature_importance=feature_importance,
            created_by="TrainingPipeline",
        )

        return model, version

    def _calculate_feature_importance(
        self,
        cluster_result: ClusterResult
    ) -> Dict[str, float]:
        """Calculate feature importance from clustering."""
        feature_names = UserRoleFeatures.feature_names()

        if not cluster_result.clusters or len(cluster_result.clusters) < 2:
            return {name: 1.0 / len(feature_names) for name in feature_names}

        # Calculate variance of centroid values for each feature
        importance = {}
        used_features = cluster_result.config.use_features if cluster_result.config else feature_names

        for feature in used_features:
            values = []
            for cluster in cluster_result.clusters:
                if feature in cluster.centroid:
                    values.append(cluster.centroid[feature])

            if len(values) >= 2:
                mean = sum(values) / len(values)
                variance = sum((v - mean) ** 2 for v in values) / len(values)
                importance[feature] = variance
            else:
                importance[feature] = 0.0

        # Normalize
        total = sum(importance.values())
        if total > 0:
            importance = {k: v / total for k, v in importance.items()}

        return importance

    def retrain(
        self,
        model_id: str,
        raw_data: List[Dict[str, Any]],
        tcode_data: Optional[Dict[str, List[str]]] = None
    ) -> TrainingResult:
        """
        Retrain an existing model with new data.

        Args:
            model_id: Model to retrain
            raw_data: New training data
            tcode_data: Optional tcode data

        Returns:
            TrainingResult with new version
        """
        model = self.registry.get_model(model_id)
        if not model:
            result = TrainingResult(success=False)
            result.error_message = f"Model {model_id} not found"
            return result

        # Get current config
        current = model.get_current_version()
        if current and current.training_metadata:
            # Use similar hyperparameters
            self.config.clustering_config = ClusteringConfig()
            if current.training_metadata.hyperparameters:
                n_clusters = current.training_metadata.hyperparameters.get("n_clusters")
                if n_clusters:
                    self.config.clustering_config.n_clusters = n_clusters
                    self.config.auto_optimize_k = False

        # Run training
        result = self.train(raw_data, tcode_data)

        if result.success:
            # Update model reference
            result.model_id = model_id

        return result
