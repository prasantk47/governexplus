# Behavior Clustering
# Discover real job patterns from usage

"""
Behavior Clustering for Role Design.

SAP GRC: "Finance users"
GOVERNEX+: Discovers actual job patterns:
- Vendor onboarding specialists
- Invoice posting clerks
- Payment approvers
- Reporting-only users
"""

from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional, Any, Tuple
from datetime import datetime
from enum import Enum
import logging
from collections import defaultdict
import math

from .features import UserRoleFeatures, FeatureSet

logger = logging.getLogger(__name__)


class ClusteringAlgorithm(Enum):
    """Available clustering algorithms."""
    KMEANS = "KMEANS"
    DBSCAN = "DBSCAN"
    HIERARCHICAL = "HIERARCHICAL"


@dataclass
class ClusteringConfig:
    """Configuration for clustering."""
    algorithm: ClusteringAlgorithm = ClusteringAlgorithm.KMEANS

    # K-Means params
    n_clusters: int = 5
    max_iterations: int = 100
    convergence_threshold: float = 0.001

    # DBSCAN params
    eps: float = 0.5
    min_samples: int = 3

    # Feature selection
    use_features: List[str] = field(default_factory=lambda: [
        "tcode_usage_frequency",
        "unique_tcodes_used",
        "unused_tcode_ratio",
        "sensitive_tcode_ratio",
        "sod_violation_count",
        "after_hours_ratio",
    ])

    # Normalization
    normalize: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "algorithm": self.algorithm.value,
            "n_clusters": self.n_clusters,
            "max_iterations": self.max_iterations,
            "use_features": self.use_features,
            "normalize": self.normalize,
        }


@dataclass
class ClusterProfile:
    """
    Profile of a discovered cluster.

    Represents a real job pattern.
    """
    cluster_id: int
    name: str = ""
    description: str = ""

    # Members
    member_count: int = 0
    member_user_ids: List[str] = field(default_factory=list)

    # Centroid (average feature values)
    centroid: Dict[str, float] = field(default_factory=dict)

    # Characteristic features
    dominant_features: List[Tuple[str, float]] = field(default_factory=list)
    distinctive_tcodes: List[str] = field(default_factory=list)

    # Risk profile
    avg_risk_score: float = 0.0
    has_sod_violations: bool = False

    # Suggested role
    suggested_role_name: str = ""
    confidence: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cluster_id": self.cluster_id,
            "name": self.name,
            "description": self.description,
            "member_count": self.member_count,
            "centroid": {k: round(v, 4) for k, v in self.centroid.items()},
            "dominant_features": [
                {"feature": f, "value": round(v, 4)}
                for f, v in self.dominant_features[:5]
            ],
            "distinctive_tcodes": self.distinctive_tcodes[:10],
            "avg_risk_score": round(self.avg_risk_score, 2),
            "has_sod_violations": self.has_sod_violations,
            "suggested_role_name": self.suggested_role_name,
            "confidence": round(self.confidence, 4),
        }


@dataclass
class ClusterResult:
    """
    Complete clustering result.

    Contains all discovered job patterns.
    """
    result_id: str
    created_at: datetime = field(default_factory=datetime.now)
    config: Optional[ClusteringConfig] = None

    # Results
    n_clusters: int = 0
    clusters: List[ClusterProfile] = field(default_factory=list)
    user_assignments: Dict[str, int] = field(default_factory=dict)

    # Quality metrics
    silhouette_score: float = 0.0
    inertia: float = 0.0
    cluster_separation: float = 0.0

    # Noise (DBSCAN)
    noise_points: List[str] = field(default_factory=list)

    def get_cluster(self, cluster_id: int) -> Optional[ClusterProfile]:
        """Get cluster by ID."""
        for cluster in self.clusters:
            if cluster.cluster_id == cluster_id:
                return cluster
        return None

    def get_user_cluster(self, user_id: str) -> Optional[ClusterProfile]:
        """Get cluster for a user."""
        cluster_id = self.user_assignments.get(user_id)
        if cluster_id is not None:
            return self.get_cluster(cluster_id)
        return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "result_id": self.result_id,
            "created_at": self.created_at.isoformat(),
            "config": self.config.to_dict() if self.config else None,
            "n_clusters": self.n_clusters,
            "clusters": [c.to_dict() for c in self.clusters],
            "quality_metrics": {
                "silhouette_score": round(self.silhouette_score, 4),
                "inertia": round(self.inertia, 4),
                "cluster_separation": round(self.cluster_separation, 4),
            },
            "noise_points_count": len(self.noise_points),
        }


class BehaviorClusterer:
    """
    Clusters users by actual work behavior.

    Instead of "Finance users", discovers:
    - Vendor onboarding specialists
    - Invoice posting clerks
    - Payment approvers
    """

    def __init__(self, config: Optional[ClusteringConfig] = None):
        """Initialize clusterer."""
        self.config = config or ClusteringConfig()
        self._result_counter = 0

    def cluster(
        self,
        feature_set: FeatureSet,
        tcode_data: Optional[Dict[str, List[str]]] = None
    ) -> ClusterResult:
        """
        Perform behavior clustering.

        Args:
            feature_set: Features for all users
            tcode_data: Optional mapping of user_id -> tcodes used

        Returns:
            ClusterResult with discovered patterns
        """
        self._result_counter += 1
        result = ClusterResult(
            result_id=f"CLU-{datetime.now().strftime('%Y%m%d%H%M%S')}-{self._result_counter}",
            config=self.config,
        )

        if not feature_set.features:
            return result

        # Extract feature matrix
        matrix, user_ids = self._prepare_matrix(feature_set)

        if not matrix:
            return result

        # Run clustering algorithm
        if self.config.algorithm == ClusteringAlgorithm.KMEANS:
            labels, centroids = self._kmeans(matrix)
        elif self.config.algorithm == ClusteringAlgorithm.DBSCAN:
            labels, centroids = self._dbscan(matrix)
        else:
            labels, centroids = self._hierarchical(matrix)

        # Build result
        result.n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
        result.user_assignments = {
            user_ids[i]: labels[i]
            for i in range(len(user_ids))
            if labels[i] >= 0
        }

        # Handle noise points
        result.noise_points = [
            user_ids[i]
            for i in range(len(user_ids))
            if labels[i] == -1
        ]

        # Build cluster profiles
        result.clusters = self._build_profiles(
            matrix, labels, user_ids, centroids, feature_set, tcode_data
        )

        # Calculate quality metrics
        result.silhouette_score = self._calculate_silhouette(matrix, labels)
        result.inertia = self._calculate_inertia(matrix, labels, centroids)
        result.cluster_separation = self._calculate_separation(centroids)

        return result

    def _prepare_matrix(
        self,
        feature_set: FeatureSet
    ) -> Tuple[List[List[float]], List[str]]:
        """Prepare feature matrix for clustering."""
        feature_names = UserRoleFeatures.feature_names()
        feature_indices = [
            feature_names.index(f)
            for f in self.config.use_features
            if f in feature_names
        ]

        if not feature_indices:
            feature_indices = list(range(len(feature_names)))

        matrix = []
        user_ids = []

        for features in feature_set.features:
            vector = features.to_vector()
            selected = [vector[i] for i in feature_indices]
            matrix.append(selected)
            user_ids.append(features.user_id)

        # Normalize if configured
        if self.config.normalize and matrix:
            matrix = self._normalize_matrix(matrix)

        return matrix, user_ids

    def _normalize_matrix(
        self,
        matrix: List[List[float]]
    ) -> List[List[float]]:
        """Min-max normalize the matrix."""
        if not matrix:
            return matrix

        n_features = len(matrix[0])
        mins = [float('inf')] * n_features
        maxs = [float('-inf')] * n_features

        # Find min/max
        for row in matrix:
            for i, val in enumerate(row):
                mins[i] = min(mins[i], val)
                maxs[i] = max(maxs[i], val)

        # Normalize
        normalized = []
        for row in matrix:
            norm_row = []
            for i, val in enumerate(row):
                range_val = maxs[i] - mins[i]
                if range_val > 0:
                    norm_row.append((val - mins[i]) / range_val)
                else:
                    norm_row.append(0.0)
            normalized.append(norm_row)

        return normalized

    def _kmeans(
        self,
        matrix: List[List[float]]
    ) -> Tuple[List[int], List[List[float]]]:
        """K-Means clustering implementation."""
        n_samples = len(matrix)
        n_features = len(matrix[0]) if matrix else 0
        k = min(self.config.n_clusters, n_samples)

        if n_samples == 0 or k == 0:
            return [], []

        # Initialize centroids (simple random selection)
        step = max(1, n_samples // k)
        centroids = [matrix[i * step % n_samples] for i in range(k)]

        labels = [0] * n_samples

        for iteration in range(self.config.max_iterations):
            # Assign points to nearest centroid
            new_labels = []
            for point in matrix:
                distances = [
                    self._euclidean_distance(point, centroid)
                    for centroid in centroids
                ]
                new_labels.append(distances.index(min(distances)))

            # Check convergence
            if new_labels == labels:
                break
            labels = new_labels

            # Update centroids
            new_centroids = []
            for c in range(k):
                cluster_points = [
                    matrix[i] for i in range(n_samples)
                    if labels[i] == c
                ]
                if cluster_points:
                    new_centroid = [
                        sum(p[f] for p in cluster_points) / len(cluster_points)
                        for f in range(n_features)
                    ]
                    new_centroids.append(new_centroid)
                else:
                    new_centroids.append(centroids[c])
            centroids = new_centroids

        return labels, centroids

    def _dbscan(
        self,
        matrix: List[List[float]]
    ) -> Tuple[List[int], List[List[float]]]:
        """DBSCAN clustering implementation."""
        n_samples = len(matrix)
        labels = [-1] * n_samples
        current_cluster = 0

        for i in range(n_samples):
            if labels[i] != -1:
                continue

            # Find neighbors
            neighbors = self._get_neighbors(matrix, i)

            if len(neighbors) < self.config.min_samples:
                continue  # Noise point

            # Start new cluster
            labels[i] = current_cluster
            seed_set = list(neighbors)

            while seed_set:
                q = seed_set.pop()
                if labels[q] == -1:
                    labels[q] = current_cluster
                if labels[q] != current_cluster:
                    continue

                q_neighbors = self._get_neighbors(matrix, q)
                if len(q_neighbors) >= self.config.min_samples:
                    seed_set.extend([
                        n for n in q_neighbors
                        if labels[n] == -1
                    ])

            current_cluster += 1

        # Calculate centroids
        centroids = []
        for c in range(current_cluster):
            cluster_points = [
                matrix[i] for i in range(n_samples)
                if labels[i] == c
            ]
            if cluster_points:
                n_features = len(matrix[0])
                centroid = [
                    sum(p[f] for p in cluster_points) / len(cluster_points)
                    for f in range(n_features)
                ]
                centroids.append(centroid)

        return labels, centroids

    def _hierarchical(
        self,
        matrix: List[List[float]]
    ) -> Tuple[List[int], List[List[float]]]:
        """Simplified hierarchical clustering."""
        # For simplicity, use K-Means as fallback
        return self._kmeans(matrix)

    def _get_neighbors(
        self,
        matrix: List[List[float]],
        point_idx: int
    ) -> Set[int]:
        """Get neighbors within eps distance."""
        neighbors = set()
        point = matrix[point_idx]

        for i, other in enumerate(matrix):
            if self._euclidean_distance(point, other) <= self.config.eps:
                neighbors.add(i)

        return neighbors

    def _euclidean_distance(
        self,
        a: List[float],
        b: List[float]
    ) -> float:
        """Calculate Euclidean distance."""
        return math.sqrt(sum((a[i] - b[i]) ** 2 for i in range(len(a))))

    def _build_profiles(
        self,
        matrix: List[List[float]],
        labels: List[int],
        user_ids: List[str],
        centroids: List[List[float]],
        feature_set: FeatureSet,
        tcode_data: Optional[Dict[str, List[str]]]
    ) -> List[ClusterProfile]:
        """Build cluster profiles."""
        profiles = []
        feature_names = self.config.use_features

        cluster_ids = sorted(set(l for l in labels if l >= 0))

        for cluster_id in cluster_ids:
            members = [
                user_ids[i] for i in range(len(labels))
                if labels[i] == cluster_id
            ]

            profile = ClusterProfile(
                cluster_id=cluster_id,
                member_count=len(members),
                member_user_ids=members,
            )

            # Set centroid
            if cluster_id < len(centroids):
                centroid = centroids[cluster_id]
                profile.centroid = {
                    feature_names[i]: centroid[i]
                    for i in range(min(len(feature_names), len(centroid)))
                }

                # Find dominant features
                feature_values = list(zip(feature_names, centroid))
                profile.dominant_features = sorted(
                    feature_values,
                    key=lambda x: x[1],
                    reverse=True
                )[:5]

            # Find distinctive tcodes
            if tcode_data:
                tcode_counts: Dict[str, int] = defaultdict(int)
                for user_id in members:
                    for tcode in tcode_data.get(user_id, []):
                        tcode_counts[tcode] += 1

                if tcode_counts:
                    sorted_tcodes = sorted(
                        tcode_counts.items(),
                        key=lambda x: x[1],
                        reverse=True
                    )
                    profile.distinctive_tcodes = [t[0] for t in sorted_tcodes[:10]]

            # Calculate risk profile
            member_features = [
                f for f in feature_set.features
                if f.user_id in members
            ]
            if member_features:
                total_sod = sum(f.sod_violation_count for f in member_features)
                profile.has_sod_violations = total_sod > 0

                # Simplified risk score
                profile.avg_risk_score = sum(
                    f.toxic_path_exposure for f in member_features
                ) / len(member_features)

            # Generate name suggestion
            profile.name, profile.suggested_role_name = self._suggest_names(profile)
            profile.confidence = self._calculate_profile_confidence(profile)

            profiles.append(profile)

        return profiles

    def _suggest_names(
        self,
        profile: ClusterProfile
    ) -> Tuple[str, str]:
        """Suggest names based on cluster characteristics."""
        # Based on dominant tcodes and features
        tcodes = profile.distinctive_tcodes

        # Simple heuristics for naming
        if any(t in ["FK01", "FK02", "XK01"] for t in tcodes):
            return "Vendor Specialists", "FI_VENDOR_MANAGEMENT"
        elif any(t in ["FB60", "MIRO", "FV60"] for t in tcodes):
            return "Invoice Processors", "FI_INVOICE_PROCESSING"
        elif any(t in ["F-53", "F110", "F-28"] for t in tcodes):
            return "Payment Processors", "FI_PAYMENT_EXECUTION"
        elif any(t in ["FBL3N", "FBL5N", "FS10N"] for t in tcodes):
            return "Reporting Users", "FI_REPORTING"
        elif any(t in ["ME21N", "ME22N", "ME23N"] for t in tcodes):
            return "Procurement Specialists", "MM_PROCUREMENT"
        elif any(t in ["VA01", "VA02", "VA03"] for t in tcodes):
            return "Sales Order Processors", "SD_ORDER_PROCESSING"
        else:
            return f"Cluster {profile.cluster_id}", f"ROLE_CLUSTER_{profile.cluster_id}"

    def _calculate_profile_confidence(
        self,
        profile: ClusterProfile
    ) -> float:
        """Calculate confidence in profile classification."""
        confidence = 0.5  # Base confidence

        # More members = higher confidence
        if profile.member_count >= 10:
            confidence += 0.2
        elif profile.member_count >= 5:
            confidence += 0.1

        # Distinctive tcodes = higher confidence
        if len(profile.distinctive_tcodes) >= 5:
            confidence += 0.15
        elif len(profile.distinctive_tcodes) >= 3:
            confidence += 0.1

        # Low risk = higher confidence
        if not profile.has_sod_violations:
            confidence += 0.1

        return min(0.95, confidence)

    def _calculate_silhouette(
        self,
        matrix: List[List[float]],
        labels: List[int]
    ) -> float:
        """Calculate silhouette score (simplified)."""
        if len(set(labels)) <= 1:
            return 0.0

        n_samples = len(matrix)
        scores = []

        for i in range(n_samples):
            if labels[i] == -1:
                continue

            # a(i) = avg distance to same cluster
            same_cluster = [
                self._euclidean_distance(matrix[i], matrix[j])
                for j in range(n_samples)
                if labels[j] == labels[i] and i != j
            ]
            a_i = sum(same_cluster) / len(same_cluster) if same_cluster else 0

            # b(i) = min avg distance to other clusters
            b_i = float('inf')
            for c in set(labels):
                if c == labels[i] or c == -1:
                    continue
                other_cluster = [
                    self._euclidean_distance(matrix[i], matrix[j])
                    for j in range(n_samples)
                    if labels[j] == c
                ]
                if other_cluster:
                    avg_dist = sum(other_cluster) / len(other_cluster)
                    b_i = min(b_i, avg_dist)

            if b_i == float('inf'):
                b_i = a_i

            # Silhouette for point i
            if max(a_i, b_i) > 0:
                s_i = (b_i - a_i) / max(a_i, b_i)
                scores.append(s_i)

        return sum(scores) / len(scores) if scores else 0.0

    def _calculate_inertia(
        self,
        matrix: List[List[float]],
        labels: List[int],
        centroids: List[List[float]]
    ) -> float:
        """Calculate inertia (within-cluster sum of squares)."""
        inertia = 0.0
        for i, point in enumerate(matrix):
            if labels[i] >= 0 and labels[i] < len(centroids):
                dist = self._euclidean_distance(point, centroids[labels[i]])
                inertia += dist ** 2
        return inertia

    def _calculate_separation(
        self,
        centroids: List[List[float]]
    ) -> float:
        """Calculate average inter-cluster distance."""
        if len(centroids) < 2:
            return 0.0

        distances = []
        for i in range(len(centroids)):
            for j in range(i + 1, len(centroids)):
                distances.append(
                    self._euclidean_distance(centroids[i], centroids[j])
                )

        return sum(distances) / len(distances) if distances else 0.0

    def find_optimal_k(
        self,
        feature_set: FeatureSet,
        min_k: int = 2,
        max_k: int = 10
    ) -> Dict[str, Any]:
        """
        Find optimal number of clusters using elbow method.

        Args:
            feature_set: Features to analyze
            min_k: Minimum clusters to try
            max_k: Maximum clusters to try

        Returns:
            Dict with analysis results
        """
        matrix, _ = self._prepare_matrix(feature_set)
        if not matrix:
            return {"error": "No data"}

        results = []
        for k in range(min_k, min(max_k + 1, len(matrix))):
            self.config.n_clusters = k
            labels, centroids = self._kmeans(matrix)
            inertia = self._calculate_inertia(matrix, labels, centroids)
            silhouette = self._calculate_silhouette(matrix, labels)

            results.append({
                "k": k,
                "inertia": inertia,
                "silhouette": silhouette,
            })

        # Find elbow (simplified)
        if len(results) >= 3:
            deltas = []
            for i in range(1, len(results)):
                delta = results[i-1]["inertia"] - results[i]["inertia"]
                deltas.append(delta)

            # Find where decrease slows down
            optimal_idx = 0
            for i in range(1, len(deltas)):
                if deltas[i] < deltas[i-1] * 0.5:
                    optimal_idx = i
                    break

            optimal_k = results[optimal_idx]["k"]
        else:
            optimal_k = min_k

        return {
            "results": results,
            "optimal_k": optimal_k,
            "recommendation": f"Use {optimal_k} clusters based on elbow analysis",
        }
