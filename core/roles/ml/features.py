# Role Feature Engineering
# Explainable features for ML models

"""
Feature Engineering for Role ML.

Features are:
- Numerical (auditor-safe)
- Explainable (no opaque embeddings)
- Derived from actual usage
"""

from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional, Any, Tuple
from datetime import datetime, timedelta
from enum import Enum
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)


class FeatureCategory(Enum):
    """Categories of features."""
    USAGE = "USAGE"
    RISK = "RISK"
    BEHAVIOR = "BEHAVIOR"
    GOVERNANCE = "GOVERNANCE"
    CONTROLS = "CONTROLS"


@dataclass
class FeatureDefinition:
    """Definition of a single feature."""
    name: str
    category: FeatureCategory
    description: str
    data_type: str = "float"
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    higher_is_riskier: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "category": self.category.value,
            "description": self.description,
            "data_type": self.data_type,
            "min_value": self.min_value,
            "max_value": self.max_value,
            "higher_is_riskier": self.higher_is_riskier,
        }


# Standard feature definitions
STANDARD_FEATURES: List[FeatureDefinition] = [
    # Usage features
    FeatureDefinition(
        name="tcode_usage_frequency",
        category=FeatureCategory.USAGE,
        description="Total transaction executions in period",
        min_value=0,
    ),
    FeatureDefinition(
        name="unique_tcodes_used",
        category=FeatureCategory.USAGE,
        description="Count of distinct transactions used",
        min_value=0,
    ),
    FeatureDefinition(
        name="unused_tcode_ratio",
        category=FeatureCategory.USAGE,
        description="Ratio of assigned but unused transactions",
        min_value=0,
        max_value=1,
    ),
    FeatureDefinition(
        name="sensitive_tcode_ratio",
        category=FeatureCategory.USAGE,
        description="Ratio of sensitive transaction usage",
        min_value=0,
        max_value=1,
    ),
    FeatureDefinition(
        name="permission_utilization",
        category=FeatureCategory.USAGE,
        description="Percentage of permissions actually used",
        min_value=0,
        max_value=100,
        higher_is_riskier=False,
    ),

    # Behavior features
    FeatureDefinition(
        name="after_hours_ratio",
        category=FeatureCategory.BEHAVIOR,
        description="Ratio of access outside business hours",
        min_value=0,
        max_value=1,
    ),
    FeatureDefinition(
        name="weekend_access_ratio",
        category=FeatureCategory.BEHAVIOR,
        description="Ratio of access on weekends",
        min_value=0,
        max_value=1,
    ),
    FeatureDefinition(
        name="firefighter_dependency",
        category=FeatureCategory.BEHAVIOR,
        description="Frequency of emergency access usage",
        min_value=0,
    ),
    FeatureDefinition(
        name="peer_deviation_score",
        category=FeatureCategory.BEHAVIOR,
        description="How different from peer group",
        min_value=0,
        max_value=100,
    ),
    FeatureDefinition(
        name="access_pattern_variance",
        category=FeatureCategory.BEHAVIOR,
        description="Variance in daily access patterns",
        min_value=0,
    ),

    # Risk features
    FeatureDefinition(
        name="sod_violation_count",
        category=FeatureCategory.RISK,
        description="Number of SoD violations",
        min_value=0,
    ),
    FeatureDefinition(
        name="toxic_path_exposure",
        category=FeatureCategory.RISK,
        description="Exposure to toxic role combinations",
        min_value=0,
        max_value=100,
    ),
    FeatureDefinition(
        name="privilege_breadth",
        category=FeatureCategory.RISK,
        description="Breadth of access across systems",
        min_value=0,
    ),
    FeatureDefinition(
        name="sensitive_data_access",
        category=FeatureCategory.RISK,
        description="Count of sensitive data access points",
        min_value=0,
    ),
    FeatureDefinition(
        name="cross_process_access",
        category=FeatureCategory.RISK,
        description="Access spanning multiple business processes",
        min_value=0,
    ),

    # Governance features
    FeatureDefinition(
        name="approval_strictness",
        category=FeatureCategory.GOVERNANCE,
        description="Average approval level required",
        min_value=0,
        max_value=100,
        higher_is_riskier=False,
    ),
    FeatureDefinition(
        name="days_since_certification",
        category=FeatureCategory.GOVERNANCE,
        description="Days since last certification",
        min_value=0,
    ),
    FeatureDefinition(
        name="role_age_days",
        category=FeatureCategory.GOVERNANCE,
        description="Age of role assignment in days",
        min_value=0,
    ),
    FeatureDefinition(
        name="review_compliance_score",
        category=FeatureCategory.GOVERNANCE,
        description="Compliance with review schedules",
        min_value=0,
        max_value=100,
        higher_is_riskier=False,
    ),

    # Control features
    FeatureDefinition(
        name="control_failure_count",
        category=FeatureCategory.CONTROLS,
        description="Number of control failures",
        min_value=0,
    ),
    FeatureDefinition(
        name="mitigating_control_coverage",
        category=FeatureCategory.CONTROLS,
        description="Percentage of risks with mitigating controls",
        min_value=0,
        max_value=100,
        higher_is_riskier=False,
    ),
]


@dataclass
class UserRoleFeatures:
    """
    Feature vector for a user-role combination.

    This is what ML models see.
    """
    user_id: str
    role_id: str
    extraction_date: datetime = field(default_factory=datetime.now)

    # Usage features
    tcode_usage_frequency: float = 0.0
    unique_tcodes_used: float = 0.0
    unused_tcode_ratio: float = 0.0
    sensitive_tcode_ratio: float = 0.0
    permission_utilization: float = 0.0

    # Behavior features
    after_hours_ratio: float = 0.0
    weekend_access_ratio: float = 0.0
    firefighter_dependency: float = 0.0
    peer_deviation_score: float = 0.0
    access_pattern_variance: float = 0.0

    # Risk features
    sod_violation_count: float = 0.0
    toxic_path_exposure: float = 0.0
    privilege_breadth: float = 0.0
    sensitive_data_access: float = 0.0
    cross_process_access: float = 0.0

    # Governance features
    approval_strictness: float = 0.0
    days_since_certification: float = 0.0
    role_age_days: float = 0.0
    review_compliance_score: float = 0.0

    # Control features
    control_failure_count: float = 0.0
    mitigating_control_coverage: float = 0.0

    def to_vector(self) -> List[float]:
        """Convert to numerical vector for ML."""
        return [
            self.tcode_usage_frequency,
            self.unique_tcodes_used,
            self.unused_tcode_ratio,
            self.sensitive_tcode_ratio,
            self.permission_utilization,
            self.after_hours_ratio,
            self.weekend_access_ratio,
            self.firefighter_dependency,
            self.peer_deviation_score,
            self.access_pattern_variance,
            self.sod_violation_count,
            self.toxic_path_exposure,
            self.privilege_breadth,
            self.sensitive_data_access,
            self.cross_process_access,
            self.approval_strictness,
            self.days_since_certification,
            self.role_age_days,
            self.review_compliance_score,
            self.control_failure_count,
            self.mitigating_control_coverage,
        ]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "user_id": self.user_id,
            "role_id": self.role_id,
            "extraction_date": self.extraction_date.isoformat(),
            "features": {
                "usage": {
                    "tcode_usage_frequency": self.tcode_usage_frequency,
                    "unique_tcodes_used": self.unique_tcodes_used,
                    "unused_tcode_ratio": round(self.unused_tcode_ratio, 4),
                    "sensitive_tcode_ratio": round(self.sensitive_tcode_ratio, 4),
                    "permission_utilization": round(self.permission_utilization, 2),
                },
                "behavior": {
                    "after_hours_ratio": round(self.after_hours_ratio, 4),
                    "weekend_access_ratio": round(self.weekend_access_ratio, 4),
                    "firefighter_dependency": self.firefighter_dependency,
                    "peer_deviation_score": round(self.peer_deviation_score, 2),
                    "access_pattern_variance": round(self.access_pattern_variance, 4),
                },
                "risk": {
                    "sod_violation_count": self.sod_violation_count,
                    "toxic_path_exposure": round(self.toxic_path_exposure, 2),
                    "privilege_breadth": self.privilege_breadth,
                    "sensitive_data_access": self.sensitive_data_access,
                    "cross_process_access": self.cross_process_access,
                },
                "governance": {
                    "approval_strictness": round(self.approval_strictness, 2),
                    "days_since_certification": self.days_since_certification,
                    "role_age_days": self.role_age_days,
                    "review_compliance_score": round(self.review_compliance_score, 2),
                },
                "controls": {
                    "control_failure_count": self.control_failure_count,
                    "mitigating_control_coverage": round(self.mitigating_control_coverage, 2),
                },
            },
        }

    @classmethod
    def feature_names(cls) -> List[str]:
        """Get ordered feature names."""
        return [
            "tcode_usage_frequency",
            "unique_tcodes_used",
            "unused_tcode_ratio",
            "sensitive_tcode_ratio",
            "permission_utilization",
            "after_hours_ratio",
            "weekend_access_ratio",
            "firefighter_dependency",
            "peer_deviation_score",
            "access_pattern_variance",
            "sod_violation_count",
            "toxic_path_exposure",
            "privilege_breadth",
            "sensitive_data_access",
            "cross_process_access",
            "approval_strictness",
            "days_since_certification",
            "role_age_days",
            "review_compliance_score",
            "control_failure_count",
            "mitigating_control_coverage",
        ]


@dataclass
class FeatureSet:
    """Collection of feature vectors for analysis."""
    name: str
    description: str
    created_at: datetime = field(default_factory=datetime.now)
    features: List[UserRoleFeatures] = field(default_factory=list)

    # Metadata
    source_system: str = ""
    extraction_period_start: Optional[datetime] = None
    extraction_period_end: Optional[datetime] = None

    def add_features(self, features: UserRoleFeatures) -> None:
        """Add a feature vector."""
        self.features.append(features)

    def to_matrix(self) -> List[List[float]]:
        """Convert all features to matrix for ML."""
        return [f.to_vector() for f in self.features]

    def get_user_ids(self) -> List[str]:
        """Get all user IDs."""
        return [f.user_id for f in self.features]

    def get_statistics(self) -> Dict[str, Dict[str, float]]:
        """Get feature statistics."""
        if not self.features:
            return {}

        matrix = self.to_matrix()
        names = UserRoleFeatures.feature_names()
        stats = {}

        for i, name in enumerate(names):
            values = [row[i] for row in matrix]
            stats[name] = {
                "min": min(values),
                "max": max(values),
                "mean": sum(values) / len(values),
                "non_zero_count": sum(1 for v in values if v > 0),
            }

        return stats


@dataclass
class FeatureImportance:
    """Feature importance from a trained model."""
    model_id: str
    feature_importances: Dict[str, float] = field(default_factory=dict)
    computed_at: datetime = field(default_factory=datetime.now)

    def get_top_features(self, n: int = 10) -> List[Tuple[str, float]]:
        """Get top N most important features."""
        sorted_features = sorted(
            self.feature_importances.items(),
            key=lambda x: x[1],
            reverse=True
        )
        return sorted_features[:n]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "model_id": self.model_id,
            "computed_at": self.computed_at.isoformat(),
            "top_features": self.get_top_features(10),
            "all_features": self.feature_importances,
        }


class RoleFeatureExtractor:
    """
    Extracts ML features from SAP data.

    Transforms raw data into explainable numerical features.
    """

    # Business hours definition
    BUSINESS_HOURS_START = 8
    BUSINESS_HOURS_END = 18

    def __init__(self, sensitive_tcodes: Optional[Set[str]] = None):
        """
        Initialize extractor.

        Args:
            sensitive_tcodes: Set of sensitive transaction codes
        """
        self.sensitive_tcodes = sensitive_tcodes or {
            "SU01", "SU10", "PFCG", "SM59", "SE38",
            "F-53", "F110", "FK01", "ME21N", "XK01",
        }

    def extract_user_role_features(
        self,
        user_id: str,
        role_id: str,
        usage_logs: List[Dict[str, Any]],
        role_permissions: List[str],
        sod_violations: List[Dict[str, Any]],
        certification_date: Optional[datetime] = None,
        role_assignment_date: Optional[datetime] = None,
        peer_usage: Optional[Dict[str, List[str]]] = None,
        control_results: Optional[List[Dict[str, Any]]] = None,
    ) -> UserRoleFeatures:
        """
        Extract features for a user-role combination.

        Args:
            user_id: User identifier
            role_id: Role identifier
            usage_logs: List of usage log entries
            role_permissions: List of permissions/tcodes assigned
            sod_violations: List of SoD violations
            certification_date: Last certification date
            role_assignment_date: When role was assigned
            peer_usage: Usage data for peer comparison
            control_results: Control evaluation results

        Returns:
            UserRoleFeatures with extracted features
        """
        features = UserRoleFeatures(
            user_id=user_id,
            role_id=role_id,
        )

        # Extract usage features
        self._extract_usage_features(
            features, usage_logs, role_permissions
        )

        # Extract behavior features
        self._extract_behavior_features(
            features, usage_logs, peer_usage
        )

        # Extract risk features
        self._extract_risk_features(
            features, role_permissions, sod_violations
        )

        # Extract governance features
        self._extract_governance_features(
            features, certification_date, role_assignment_date
        )

        # Extract control features
        self._extract_control_features(
            features, control_results
        )

        return features

    def _extract_usage_features(
        self,
        features: UserRoleFeatures,
        usage_logs: List[Dict[str, Any]],
        role_permissions: List[str]
    ) -> None:
        """Extract usage-related features."""
        if not usage_logs:
            features.unused_tcode_ratio = 1.0 if role_permissions else 0.0
            return

        # Total executions
        features.tcode_usage_frequency = len(usage_logs)

        # Unique tcodes used
        used_tcodes = set()
        sensitive_used = 0

        for log in usage_logs:
            tcode = log.get("tcode", "")
            used_tcodes.add(tcode)
            if tcode in self.sensitive_tcodes:
                sensitive_used += 1

        features.unique_tcodes_used = len(used_tcodes)

        # Unused ratio
        if role_permissions:
            unused = len(set(role_permissions) - used_tcodes)
            features.unused_tcode_ratio = unused / len(role_permissions)
            features.permission_utilization = (
                len(used_tcodes) / len(role_permissions) * 100
            )

        # Sensitive ratio
        if usage_logs:
            features.sensitive_tcode_ratio = sensitive_used / len(usage_logs)

    def _extract_behavior_features(
        self,
        features: UserRoleFeatures,
        usage_logs: List[Dict[str, Any]],
        peer_usage: Optional[Dict[str, List[str]]]
    ) -> None:
        """Extract behavior-related features."""
        if not usage_logs:
            return

        after_hours_count = 0
        weekend_count = 0
        firefighter_count = 0
        hourly_distribution = defaultdict(int)

        for log in usage_logs:
            timestamp = log.get("timestamp")
            if isinstance(timestamp, datetime):
                hour = timestamp.hour
                hourly_distribution[hour] += 1

                # After hours
                if hour < self.BUSINESS_HOURS_START or hour >= self.BUSINESS_HOURS_END:
                    after_hours_count += 1

                # Weekend
                if timestamp.weekday() >= 5:
                    weekend_count += 1

            # Firefighter usage
            if log.get("is_firefighter", False):
                firefighter_count += 1

        total = len(usage_logs)
        features.after_hours_ratio = after_hours_count / total
        features.weekend_access_ratio = weekend_count / total
        features.firefighter_dependency = firefighter_count

        # Access pattern variance
        if hourly_distribution:
            values = list(hourly_distribution.values())
            mean = sum(values) / len(values)
            variance = sum((v - mean) ** 2 for v in values) / len(values)
            features.access_pattern_variance = variance

        # Peer deviation
        if peer_usage:
            used_tcodes = {log.get("tcode") for log in usage_logs}
            peer_scores = []

            for peer_id, peer_tcodes in peer_usage.items():
                if peer_id != features.user_id:
                    peer_set = set(peer_tcodes)
                    if peer_set:
                        overlap = len(used_tcodes & peer_set)
                        union = len(used_tcodes | peer_set)
                        similarity = overlap / union if union else 0
                        peer_scores.append(similarity)

            if peer_scores:
                avg_similarity = sum(peer_scores) / len(peer_scores)
                features.peer_deviation_score = (1 - avg_similarity) * 100

    def _extract_risk_features(
        self,
        features: UserRoleFeatures,
        role_permissions: List[str],
        sod_violations: List[Dict[str, Any]]
    ) -> None:
        """Extract risk-related features."""
        # SoD violations
        features.sod_violation_count = len(sod_violations)

        # Toxic path exposure (simplified calculation)
        toxic_paths = sum(
            1 for v in sod_violations
            if v.get("severity") == "CRITICAL"
        )
        features.toxic_path_exposure = min(100, toxic_paths * 25)

        # Privilege breadth
        features.privilege_breadth = len(role_permissions)

        # Sensitive data access
        if role_permissions:
            sensitive = sum(
                1 for p in role_permissions
                if p in self.sensitive_tcodes
            )
            features.sensitive_data_access = sensitive

    def _extract_governance_features(
        self,
        features: UserRoleFeatures,
        certification_date: Optional[datetime],
        role_assignment_date: Optional[datetime]
    ) -> None:
        """Extract governance-related features."""
        now = datetime.now()

        if certification_date:
            features.days_since_certification = (now - certification_date).days
        else:
            features.days_since_certification = 365  # Assume never certified

        if role_assignment_date:
            features.role_age_days = (now - role_assignment_date).days
        else:
            features.role_age_days = 180  # Default assumption

        # Review compliance (simplified)
        if features.days_since_certification <= 90:
            features.review_compliance_score = 100
        elif features.days_since_certification <= 180:
            features.review_compliance_score = 75
        elif features.days_since_certification <= 365:
            features.review_compliance_score = 50
        else:
            features.review_compliance_score = 25

    def _extract_control_features(
        self,
        features: UserRoleFeatures,
        control_results: Optional[List[Dict[str, Any]]]
    ) -> None:
        """Extract control-related features."""
        if not control_results:
            return

        failures = sum(
            1 for c in control_results
            if not c.get("passed", True)
        )
        features.control_failure_count = failures

        mitigated = sum(
            1 for c in control_results
            if c.get("has_mitigating_control", False)
        )
        if control_results:
            features.mitigating_control_coverage = (
                mitigated / len(control_results) * 100
            )

    def extract_batch(
        self,
        user_role_data: List[Dict[str, Any]]
    ) -> FeatureSet:
        """
        Extract features for multiple user-role combinations.

        Args:
            user_role_data: List of data dicts with user/role info

        Returns:
            FeatureSet with all extracted features
        """
        feature_set = FeatureSet(
            name=f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            description="Batch feature extraction",
        )

        for data in user_role_data:
            try:
                features = self.extract_user_role_features(
                    user_id=data["user_id"],
                    role_id=data["role_id"],
                    usage_logs=data.get("usage_logs", []),
                    role_permissions=data.get("permissions", []),
                    sod_violations=data.get("sod_violations", []),
                    certification_date=data.get("certification_date"),
                    role_assignment_date=data.get("assignment_date"),
                    peer_usage=data.get("peer_usage"),
                    control_results=data.get("control_results"),
                )
                feature_set.add_features(features)
            except Exception as e:
                logger.warning(f"Failed to extract features for {data}: {e}")

        return feature_set
