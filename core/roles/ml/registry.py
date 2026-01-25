# Model Registry
# Governance and versioning for ML models

"""
Model Registry for GOVERNEX+.

Model Governance Rules:
- ML never blocks alone
- ML only adjusts risk
- Deterministic fallback always
- Models versioned
- Training data logged
- Feature importance exposed
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum
import logging
import hashlib
import json

logger = logging.getLogger(__name__)


class ModelStatus(Enum):
    """Model lifecycle status."""
    DRAFT = "DRAFT"
    TRAINING = "TRAINING"
    VALIDATING = "VALIDATING"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    DEPLOYED = "DEPLOYED"
    DEPRECATED = "DEPRECATED"
    RETIRED = "RETIRED"


class ModelType(Enum):
    """Types of models in the registry."""
    CLUSTERING = "CLUSTERING"  # Role design clustering
    ANOMALY = "ANOMALY"  # Anomaly detection
    PREDICTION = "PREDICTION"  # Risk prediction
    CLASSIFICATION = "CLASSIFICATION"  # Role classification


@dataclass
class ModelMetrics:
    """Performance metrics for a model."""
    # Clustering metrics
    silhouette_score: Optional[float] = None
    inertia: Optional[float] = None
    cluster_count: Optional[int] = None

    # Classification metrics
    accuracy: Optional[float] = None
    precision: Optional[float] = None
    recall: Optional[float] = None
    f1_score: Optional[float] = None

    # Anomaly metrics
    false_positive_rate: Optional[float] = None
    detection_rate: Optional[float] = None

    # General metrics
    training_samples: int = 0
    validation_samples: int = 0
    inference_time_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        metrics = {}
        for key, value in self.__dict__.items():
            if value is not None:
                if isinstance(value, float):
                    metrics[key] = round(value, 4)
                else:
                    metrics[key] = value
        return metrics


@dataclass
class TrainingMetadata:
    """Metadata about model training."""
    training_start: datetime = field(default_factory=datetime.now)
    training_end: Optional[datetime] = None
    training_duration_seconds: float = 0.0

    # Data info
    data_source: str = ""
    data_period_start: Optional[datetime] = None
    data_period_end: Optional[datetime] = None
    sample_count: int = 0

    # Feature info
    features_used: List[str] = field(default_factory=list)
    feature_count: int = 0

    # Hyperparameters
    hyperparameters: Dict[str, Any] = field(default_factory=dict)

    # Data hash for reproducibility
    data_hash: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "training_start": self.training_start.isoformat(),
            "training_end": self.training_end.isoformat() if self.training_end else None,
            "training_duration_seconds": round(self.training_duration_seconds, 2),
            "data_source": self.data_source,
            "data_period_start": self.data_period_start.isoformat() if self.data_period_start else None,
            "data_period_end": self.data_period_end.isoformat() if self.data_period_end else None,
            "sample_count": self.sample_count,
            "features_used": self.features_used,
            "feature_count": self.feature_count,
            "hyperparameters": self.hyperparameters,
            "data_hash": self.data_hash,
        }


@dataclass
class ModelVersion:
    """A specific version of a model."""
    version: str
    created_at: datetime = field(default_factory=datetime.now)
    created_by: str = ""

    # Status
    status: ModelStatus = ModelStatus.DRAFT

    # Metrics
    metrics: Optional[ModelMetrics] = None

    # Training info
    training_metadata: Optional[TrainingMetadata] = None

    # Approval
    approved_by: str = ""
    approved_at: Optional[datetime] = None
    approval_notes: str = ""

    # Deployment
    deployed_at: Optional[datetime] = None
    deployment_environment: str = ""

    # Feature importance
    feature_importance: Dict[str, float] = field(default_factory=dict)

    # Rollback info
    can_rollback: bool = True
    previous_version: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": self.version,
            "created_at": self.created_at.isoformat(),
            "created_by": self.created_by,
            "status": self.status.value,
            "metrics": self.metrics.to_dict() if self.metrics else None,
            "training_metadata": self.training_metadata.to_dict() if self.training_metadata else None,
            "approved_by": self.approved_by,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "deployed_at": self.deployed_at.isoformat() if self.deployed_at else None,
            "feature_importance": {
                k: round(v, 4) for k, v in self.feature_importance.items()
            },
        }


@dataclass
class RegisteredModel:
    """A registered model with version history."""
    model_id: str
    name: str
    description: str
    model_type: ModelType

    # Ownership
    owner: str = ""
    team: str = ""

    # Versions
    versions: List[ModelVersion] = field(default_factory=list)
    current_version: str = ""

    # Configuration
    deterministic_fallback: str = ""  # What to use if model fails
    max_inference_time_ms: float = 100.0
    auto_rollback_on_degradation: bool = True

    # Usage constraints
    can_block_alone: bool = False  # ML never blocks alone
    requires_human_review: bool = True
    risk_adjustment_only: bool = True  # ML only adjusts risk

    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    # Tags
    tags: List[str] = field(default_factory=list)

    def get_version(self, version: str) -> Optional[ModelVersion]:
        """Get specific version."""
        for v in self.versions:
            if v.version == version:
                return v
        return None

    def get_current_version(self) -> Optional[ModelVersion]:
        """Get current deployed version."""
        return self.get_version(self.current_version)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "model_id": self.model_id,
            "name": self.name,
            "description": self.description,
            "model_type": self.model_type.value,
            "owner": self.owner,
            "team": self.team,
            "current_version": self.current_version,
            "version_count": len(self.versions),
            "constraints": {
                "can_block_alone": self.can_block_alone,
                "requires_human_review": self.requires_human_review,
                "risk_adjustment_only": self.risk_adjustment_only,
            },
            "deterministic_fallback": self.deterministic_fallback,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "tags": self.tags,
        }


class ModelRegistry:
    """
    Registry for ML models with governance.

    Key governance rules enforced:
    - ML never blocks alone
    - ML only adjusts risk
    - Deterministic fallback always
    - Models versioned
    - Training data logged
    - Feature importance exposed
    """

    def __init__(self):
        """Initialize registry."""
        self._models: Dict[str, RegisteredModel] = {}
        self._version_counter: Dict[str, int] = {}

    def register_model(
        self,
        name: str,
        description: str,
        model_type: ModelType,
        owner: str = "",
        deterministic_fallback: str = "",
        tags: Optional[List[str]] = None
    ) -> RegisteredModel:
        """
        Register a new model.

        Args:
            name: Model name
            description: Model description
            model_type: Type of model
            owner: Model owner
            deterministic_fallback: Fallback when model unavailable
            tags: Optional tags

        Returns:
            Registered model
        """
        model_id = f"MODEL-{name.upper().replace(' ', '_')}-{datetime.now().strftime('%Y%m%d%H%M%S')}"

        model = RegisteredModel(
            model_id=model_id,
            name=name,
            description=description,
            model_type=model_type,
            owner=owner,
            deterministic_fallback=deterministic_fallback,
            tags=tags or [],
        )

        # Enforce governance rules
        model.can_block_alone = False  # Never
        model.risk_adjustment_only = True  # Always

        if not deterministic_fallback:
            model.deterministic_fallback = "USE_DEFAULT_RISK_SCORE"

        self._models[model_id] = model
        self._version_counter[model_id] = 0

        logger.info(f"Registered model: {model_id}")
        return model

    def add_version(
        self,
        model_id: str,
        metrics: ModelMetrics,
        training_metadata: TrainingMetadata,
        feature_importance: Optional[Dict[str, float]] = None,
        created_by: str = ""
    ) -> ModelVersion:
        """
        Add a new version to a model.

        Args:
            model_id: Model ID
            metrics: Performance metrics
            training_metadata: Training details
            feature_importance: Feature importance scores
            created_by: Creator

        Returns:
            Created version
        """
        model = self._models.get(model_id)
        if not model:
            raise ValueError(f"Model {model_id} not found")

        self._version_counter[model_id] += 1
        version_num = self._version_counter[model_id]
        version_str = f"v{version_num}.0.0"

        # Determine previous version
        previous = model.current_version if model.current_version else ""

        version = ModelVersion(
            version=version_str,
            created_by=created_by,
            status=ModelStatus.PENDING_APPROVAL,
            metrics=metrics,
            training_metadata=training_metadata,
            feature_importance=feature_importance or {},
            previous_version=previous,
        )

        model.versions.append(version)
        model.updated_at = datetime.now()

        logger.info(f"Added version {version_str} to model {model_id}")
        return version

    def approve_version(
        self,
        model_id: str,
        version: str,
        approved_by: str,
        notes: str = ""
    ) -> bool:
        """
        Approve a model version for deployment.

        Args:
            model_id: Model ID
            version: Version to approve
            approved_by: Approver
            notes: Approval notes

        Returns:
            True if approved
        """
        model = self._models.get(model_id)
        if not model:
            return False

        version_obj = model.get_version(version)
        if not version_obj:
            return False

        if version_obj.status != ModelStatus.PENDING_APPROVAL:
            logger.warning(f"Version {version} not pending approval")
            return False

        version_obj.status = ModelStatus.APPROVED
        version_obj.approved_by = approved_by
        version_obj.approved_at = datetime.now()
        version_obj.approval_notes = notes

        logger.info(f"Approved version {version} of model {model_id}")
        return True

    def deploy_version(
        self,
        model_id: str,
        version: str,
        environment: str = "production"
    ) -> bool:
        """
        Deploy a model version.

        Args:
            model_id: Model ID
            version: Version to deploy
            environment: Deployment environment

        Returns:
            True if deployed
        """
        model = self._models.get(model_id)
        if not model:
            return False

        version_obj = model.get_version(version)
        if not version_obj:
            return False

        if version_obj.status != ModelStatus.APPROVED:
            logger.warning(f"Version {version} not approved for deployment")
            return False

        # Deprecate current version
        current = model.get_current_version()
        if current and current.version != version:
            current.status = ModelStatus.DEPRECATED

        # Deploy new version
        version_obj.status = ModelStatus.DEPLOYED
        version_obj.deployed_at = datetime.now()
        version_obj.deployment_environment = environment
        model.current_version = version
        model.updated_at = datetime.now()

        logger.info(f"Deployed version {version} of model {model_id} to {environment}")
        return True

    def rollback(
        self,
        model_id: str,
        reason: str = ""
    ) -> bool:
        """
        Rollback to previous version.

        Args:
            model_id: Model ID
            reason: Rollback reason

        Returns:
            True if rolled back
        """
        model = self._models.get(model_id)
        if not model:
            return False

        current = model.get_current_version()
        if not current or not current.previous_version:
            logger.warning(f"No previous version to rollback to for {model_id}")
            return False

        previous = model.get_version(current.previous_version)
        if not previous:
            return False

        # Rollback
        current.status = ModelStatus.DEPRECATED
        previous.status = ModelStatus.DEPLOYED
        previous.deployed_at = datetime.now()
        model.current_version = previous.version
        model.updated_at = datetime.now()

        logger.info(f"Rolled back model {model_id} to version {previous.version}: {reason}")
        return True

    def get_model(self, model_id: str) -> Optional[RegisteredModel]:
        """Get a model by ID."""
        return self._models.get(model_id)

    def list_models(
        self,
        model_type: Optional[ModelType] = None,
        status: Optional[ModelStatus] = None
    ) -> List[RegisteredModel]:
        """List models with optional filters."""
        models = list(self._models.values())

        if model_type:
            models = [m for m in models if m.model_type == model_type]

        if status:
            models = [
                m for m in models
                if m.get_current_version() and
                m.get_current_version().status == status
            ]

        return models

    def get_feature_importance(
        self,
        model_id: str,
        version: Optional[str] = None
    ) -> Dict[str, float]:
        """
        Get feature importance for a model.

        Exposes feature importance for auditability.
        """
        model = self._models.get(model_id)
        if not model:
            return {}

        if version:
            version_obj = model.get_version(version)
        else:
            version_obj = model.get_current_version()

        if not version_obj:
            return {}

        return version_obj.feature_importance

    def validate_governance(
        self,
        model_id: str
    ) -> Dict[str, Any]:
        """
        Validate model governance compliance.

        Checks:
        - Has deterministic fallback
        - Cannot block alone
        - Risk adjustment only
        - Feature importance available
        """
        model = self._models.get(model_id)
        if not model:
            return {"error": "Model not found"}

        issues = []
        passed = []

        # Check rules
        if model.can_block_alone:
            issues.append("Model configured to block alone - VIOLATION")
        else:
            passed.append("Model cannot block alone")

        if not model.risk_adjustment_only:
            issues.append("Model not risk-adjustment-only - VIOLATION")
        else:
            passed.append("Model is risk-adjustment-only")

        if not model.deterministic_fallback:
            issues.append("No deterministic fallback configured")
        else:
            passed.append(f"Deterministic fallback: {model.deterministic_fallback}")

        current = model.get_current_version()
        if current:
            if not current.feature_importance:
                issues.append("Feature importance not exposed")
            else:
                passed.append(f"Feature importance available ({len(current.feature_importance)} features)")

            if not current.training_metadata:
                issues.append("Training metadata not logged")
            else:
                passed.append("Training metadata logged")

        return {
            "model_id": model_id,
            "compliant": len(issues) == 0,
            "issues": issues,
            "passed": passed,
            "score": len(passed) / (len(passed) + len(issues)) * 100 if (passed or issues) else 0,
        }

    def generate_data_hash(self, data: Any) -> str:
        """Generate hash for training data reproducibility."""
        data_str = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(data_str.encode()).hexdigest()[:16]

    def get_audit_trail(
        self,
        model_id: str
    ) -> List[Dict[str, Any]]:
        """Get complete audit trail for a model."""
        model = self._models.get(model_id)
        if not model:
            return []

        trail = []

        # Registration event
        trail.append({
            "event": "REGISTERED",
            "timestamp": model.created_at.isoformat(),
            "details": {
                "name": model.name,
                "type": model.model_type.value,
                "owner": model.owner,
            },
        })

        # Version events
        for version in model.versions:
            trail.append({
                "event": "VERSION_CREATED",
                "timestamp": version.created_at.isoformat(),
                "version": version.version,
                "details": {
                    "created_by": version.created_by,
                    "metrics": version.metrics.to_dict() if version.metrics else None,
                },
            })

            if version.approved_at:
                trail.append({
                    "event": "VERSION_APPROVED",
                    "timestamp": version.approved_at.isoformat(),
                    "version": version.version,
                    "details": {
                        "approved_by": version.approved_by,
                        "notes": version.approval_notes,
                    },
                })

            if version.deployed_at:
                trail.append({
                    "event": "VERSION_DEPLOYED",
                    "timestamp": version.deployed_at.isoformat(),
                    "version": version.version,
                    "details": {
                        "environment": version.deployment_environment,
                    },
                })

        return sorted(trail, key=lambda x: x["timestamp"])
