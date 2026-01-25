"""
Role Mining Module

Uses clustering algorithms to discover optimal role structures
from existing user access patterns.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple, Any
from datetime import datetime
from enum import Enum
from collections import defaultdict
import uuid
import math


class ClusteringAlgorithm(Enum):
    """Available clustering algorithms"""
    KMEANS = "kmeans"
    HIERARCHICAL = "hierarchical"
    DBSCAN = "dbscan"
    ROLE_HIERARCHY = "role_hierarchy"


class MiningStatus(Enum):
    """Status of a mining job"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Permission:
    """A single permission/entitlement"""
    permission_id: str
    system: str
    object_type: str  # tcode, auth_object, table, etc.
    object_name: str
    field: str = ""
    value: str = ""

    def to_tuple(self) -> tuple:
        return (self.system, self.object_type, self.object_name, self.field, self.value)

    def to_dict(self) -> Dict:
        return {
            "permission_id": self.permission_id,
            "system": self.system,
            "object_type": self.object_type,
            "object_name": self.object_name,
            "field": self.field,
            "value": self.value
        }


@dataclass
class UserAccessVector:
    """Represents a user's access as a feature vector"""
    user_id: str
    department: str = ""
    job_title: str = ""
    permissions: Set[str] = field(default_factory=set)  # Set of permission IDs
    roles: Set[str] = field(default_factory=set)
    attributes: Dict[str, Any] = field(default_factory=dict)

    def to_binary_vector(self, all_permissions: List[str]) -> List[int]:
        """Convert to binary feature vector"""
        return [1 if p in self.permissions else 0 for p in all_permissions]


@dataclass
class RoleCluster:
    """A discovered role cluster"""
    cluster_id: str = field(default_factory=lambda: f"CLUSTER-{uuid.uuid4().hex[:8].upper()}")
    suggested_role_name: str = ""
    description: str = ""

    # Members
    user_ids: List[str] = field(default_factory=list)
    user_count: int = 0

    # Permissions
    core_permissions: List[Permission] = field(default_factory=list)  # Shared by all/most
    common_permissions: List[Permission] = field(default_factory=list)  # Shared by majority
    outlier_permissions: List[Permission] = field(default_factory=list)  # Rare permissions

    # Metrics
    cohesion_score: float = 0.0  # How similar users are within cluster
    separation_score: float = 0.0  # How different from other clusters
    coverage_score: float = 0.0  # What % of user permissions are covered
    permission_overlap_pct: float = 0.0

    # Characteristics
    departments: List[str] = field(default_factory=list)
    job_titles: List[str] = field(default_factory=list)
    primary_department: str = ""
    primary_job_title: str = ""

    # Risk assessment
    sod_conflicts: List[Dict] = field(default_factory=list)
    risk_score: float = 0.0

    def to_dict(self) -> Dict:
        return {
            "cluster_id": self.cluster_id,
            "suggested_role_name": self.suggested_role_name,
            "description": self.description,
            "user_count": self.user_count,
            "user_ids": self.user_ids[:10],  # First 10
            "core_permissions": [p.to_dict() for p in self.core_permissions],
            "common_permissions": [p.to_dict() for p in self.common_permissions],
            "cohesion_score": round(self.cohesion_score, 3),
            "separation_score": round(self.separation_score, 3),
            "coverage_score": round(self.coverage_score, 3),
            "permission_overlap_pct": round(self.permission_overlap_pct, 1),
            "departments": self.departments,
            "job_titles": self.job_titles,
            "primary_department": self.primary_department,
            "primary_job_title": self.primary_job_title,
            "sod_conflicts": self.sod_conflicts,
            "risk_score": round(self.risk_score, 2)
        }


@dataclass
class MiningResult:
    """Result of a role mining operation"""
    job_id: str = field(default_factory=lambda: f"MINE-{uuid.uuid4().hex[:8].upper()}")
    status: MiningStatus = MiningStatus.PENDING
    algorithm: ClusteringAlgorithm = ClusteringAlgorithm.KMEANS

    # Input stats
    total_users: int = 0
    total_permissions: int = 0
    unique_permissions: int = 0

    # Results
    clusters: List[RoleCluster] = field(default_factory=list)
    optimal_cluster_count: int = 0

    # Quality metrics
    silhouette_score: float = 0.0  # -1 to 1, higher is better
    calinski_harabasz_score: float = 0.0  # Higher is better
    total_coverage: float = 0.0  # % of permissions covered by suggested roles

    # Recommendations
    recommended_roles: List[Dict] = field(default_factory=list)
    redundant_roles: List[Dict] = field(default_factory=list)
    role_consolidation_suggestions: List[Dict] = field(default_factory=list)

    # Timing
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: float = 0.0

    # Errors
    error_message: Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            "job_id": self.job_id,
            "status": self.status.value,
            "algorithm": self.algorithm.value,
            "total_users": self.total_users,
            "total_permissions": self.total_permissions,
            "unique_permissions": self.unique_permissions,
            "cluster_count": len(self.clusters),
            "optimal_cluster_count": self.optimal_cluster_count,
            "silhouette_score": round(self.silhouette_score, 3),
            "total_coverage": round(self.total_coverage, 1),
            "recommended_roles": self.recommended_roles,
            "redundant_roles": self.redundant_roles,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": round(self.duration_seconds, 2),
            "error_message": self.error_message
        }


class RoleMiner:
    """
    Role Mining Engine using clustering algorithms.

    Discovers optimal role structures from user access patterns.
    Supports multiple algorithms and provides quality metrics.
    """

    def __init__(self, rule_engine=None):
        self.rule_engine = rule_engine
        self.jobs: Dict[str, MiningResult] = {}
        self.permission_index: Dict[str, Permission] = {}

    def mine_roles(
        self,
        user_access_data: List[Dict],
        algorithm: ClusteringAlgorithm = ClusteringAlgorithm.KMEANS,
        min_cluster_size: int = 3,
        max_clusters: int = 20,
        min_permission_frequency: float = 0.7,  # 70% of users must have permission
        include_risk_analysis: bool = True
    ) -> MiningResult:
        """
        Mine roles from user access data.

        Args:
            user_access_data: List of user access records with permissions
            algorithm: Clustering algorithm to use
            min_cluster_size: Minimum users per cluster
            max_clusters: Maximum number of clusters to consider
            min_permission_frequency: Min % of users that must have a permission for it to be core
            include_risk_analysis: Check discovered roles for SoD conflicts

        Returns:
            MiningResult with discovered clusters and recommendations
        """
        result = MiningResult(
            algorithm=algorithm,
            started_at=datetime.now()
        )

        try:
            # Parse user data into vectors
            users, all_permissions = self._prepare_data(user_access_data)
            result.total_users = len(users)
            result.unique_permissions = len(all_permissions)
            result.total_permissions = sum(len(u.permissions) for u in users)

            if len(users) < min_cluster_size:
                result.status = MiningStatus.FAILED
                result.error_message = f"Not enough users ({len(users)}) for clustering"
                return result

            result.status = MiningStatus.RUNNING

            # Perform clustering based on algorithm
            if algorithm == ClusteringAlgorithm.KMEANS:
                clusters = self._kmeans_clustering(users, all_permissions, max_clusters, min_cluster_size)
            elif algorithm == ClusteringAlgorithm.HIERARCHICAL:
                clusters = self._hierarchical_clustering(users, all_permissions, max_clusters, min_cluster_size)
            elif algorithm == ClusteringAlgorithm.DBSCAN:
                clusters = self._dbscan_clustering(users, all_permissions, min_cluster_size)
            else:
                clusters = self._role_hierarchy_mining(users, all_permissions, min_cluster_size)

            # Analyze each cluster
            for cluster in clusters:
                self._analyze_cluster(cluster, users, all_permissions, min_permission_frequency)

                # Check for SoD conflicts if requested
                if include_risk_analysis and self.rule_engine:
                    self._check_cluster_risks(cluster)

            # Filter out small clusters
            clusters = [c for c in clusters if c.user_count >= min_cluster_size]

            # Calculate quality metrics
            result.clusters = clusters
            result.optimal_cluster_count = len(clusters)
            result.silhouette_score = self._calculate_silhouette(clusters, users, all_permissions)
            result.total_coverage = self._calculate_coverage(clusters, users)

            # Generate recommendations
            result.recommended_roles = self._generate_role_recommendations(clusters)
            result.redundant_roles = self._find_redundant_roles(clusters)
            result.role_consolidation_suggestions = self._suggest_consolidations(clusters)

            result.status = MiningStatus.COMPLETED

        except Exception as e:
            result.status = MiningStatus.FAILED
            result.error_message = str(e)

        result.completed_at = datetime.now()
        result.duration_seconds = (result.completed_at - result.started_at).total_seconds()

        self.jobs[result.job_id] = result
        return result

    def _prepare_data(self, user_access_data: List[Dict]) -> Tuple[List[UserAccessVector], List[str]]:
        """Prepare user data for clustering"""
        users = []
        all_permissions = set()

        for record in user_access_data:
            user = UserAccessVector(
                user_id=record.get("user_id", ""),
                department=record.get("department", ""),
                job_title=record.get("job_title", ""),
                permissions=set(),
                roles=set(record.get("roles", [])),
                attributes=record.get("attributes", {})
            )

            # Process permissions
            for perm in record.get("permissions", []):
                if isinstance(perm, dict):
                    perm_id = f"{perm.get('system', 'SAP')}:{perm.get('object_name', '')}:{perm.get('value', '')}"
                    permission = Permission(
                        permission_id=perm_id,
                        system=perm.get("system", "SAP"),
                        object_type=perm.get("object_type", "tcode"),
                        object_name=perm.get("object_name", ""),
                        field=perm.get("field", ""),
                        value=perm.get("value", "")
                    )
                    self.permission_index[perm_id] = permission
                    user.permissions.add(perm_id)
                    all_permissions.add(perm_id)
                else:
                    user.permissions.add(str(perm))
                    all_permissions.add(str(perm))

            users.append(user)

        return users, sorted(list(all_permissions))

    def _kmeans_clustering(
        self,
        users: List[UserAccessVector],
        all_permissions: List[str],
        max_clusters: int,
        min_cluster_size: int
    ) -> List[RoleCluster]:
        """K-Means clustering implementation"""
        # Convert to binary vectors
        vectors = [u.to_binary_vector(all_permissions) for u in users]

        # Find optimal k using elbow method
        best_k = min(max_clusters, len(users) // min_cluster_size)
        best_k = max(2, best_k)

        # Simple k-means implementation
        clusters = self._simple_kmeans(vectors, best_k, users)

        return clusters

    def _simple_kmeans(
        self,
        vectors: List[List[int]],
        k: int,
        users: List[UserAccessVector],
        max_iterations: int = 100
    ) -> List[RoleCluster]:
        """Simple K-Means implementation without external dependencies"""
        import random

        n = len(vectors)
        dim = len(vectors[0]) if vectors else 0

        if n == 0 or dim == 0:
            return []

        # Initialize centroids randomly
        centroid_indices = random.sample(range(n), min(k, n))
        centroids = [vectors[i][:] for i in centroid_indices]

        assignments = [-1] * n

        for _ in range(max_iterations):
            # Assign points to nearest centroid
            new_assignments = []
            for vec in vectors:
                min_dist = float('inf')
                best_cluster = 0
                for i, centroid in enumerate(centroids):
                    dist = self._euclidean_distance(vec, centroid)
                    if dist < min_dist:
                        min_dist = dist
                        best_cluster = i
                new_assignments.append(best_cluster)

            # Check for convergence
            if new_assignments == assignments:
                break
            assignments = new_assignments

            # Update centroids
            for i in range(k):
                cluster_vectors = [vectors[j] for j in range(n) if assignments[j] == i]
                if cluster_vectors:
                    centroids[i] = [
                        sum(v[d] for v in cluster_vectors) / len(cluster_vectors)
                        for d in range(dim)
                    ]

        # Create cluster objects
        clusters = []
        for i in range(k):
            cluster_users = [users[j] for j in range(n) if assignments[j] == i]
            if cluster_users:
                cluster = RoleCluster(
                    user_ids=[u.user_id for u in cluster_users],
                    user_count=len(cluster_users)
                )
                clusters.append(cluster)

        return clusters

    def _hierarchical_clustering(
        self,
        users: List[UserAccessVector],
        all_permissions: List[str],
        max_clusters: int,
        min_cluster_size: int
    ) -> List[RoleCluster]:
        """Hierarchical/Agglomerative clustering"""
        vectors = [u.to_binary_vector(all_permissions) for u in users]
        n = len(vectors)

        # Start with each user in their own cluster
        cluster_assignments = list(range(n))
        active_clusters = set(range(n))

        # Distance matrix
        distances = {}
        for i in range(n):
            for j in range(i + 1, n):
                distances[(i, j)] = self._jaccard_distance(
                    set(users[i].permissions),
                    set(users[j].permissions)
                )

        # Merge until we reach desired number of clusters
        target_clusters = min(max_clusters, n // min_cluster_size)

        while len(active_clusters) > target_clusters:
            # Find closest pair
            min_dist = float('inf')
            merge_pair = None

            for i in active_clusters:
                for j in active_clusters:
                    if i < j:
                        key = (min(i, j), max(i, j))
                        if key in distances and distances[key] < min_dist:
                            min_dist = distances[key]
                            merge_pair = (i, j)

            if merge_pair is None:
                break

            # Merge clusters
            c1, c2 = merge_pair
            for k in range(n):
                if cluster_assignments[k] == c2:
                    cluster_assignments[k] = c1

            active_clusters.remove(c2)

            # Update distances (average linkage)
            for c in active_clusters:
                if c != c1:
                    key1 = (min(c1, c), max(c1, c))
                    key2 = (min(c2, c), max(c2, c))
                    if key1 in distances and key2 in distances:
                        distances[key1] = (distances[key1] + distances.get(key2, 0)) / 2

        # Create cluster objects
        cluster_map = defaultdict(list)
        for i, c in enumerate(cluster_assignments):
            cluster_map[c].append(users[i])

        clusters = []
        for cluster_users in cluster_map.values():
            if len(cluster_users) >= min_cluster_size:
                cluster = RoleCluster(
                    user_ids=[u.user_id for u in cluster_users],
                    user_count=len(cluster_users)
                )
                clusters.append(cluster)

        return clusters

    def _dbscan_clustering(
        self,
        users: List[UserAccessVector],
        all_permissions: List[str],
        min_cluster_size: int
    ) -> List[RoleCluster]:
        """DBSCAN clustering for density-based discovery"""
        eps = 0.3  # Distance threshold
        min_samples = min_cluster_size

        n = len(users)
        labels = [-1] * n  # -1 means unvisited
        cluster_id = 0

        for i in range(n):
            if labels[i] != -1:
                continue

            # Find neighbors
            neighbors = self._get_neighbors(users, i, eps)

            if len(neighbors) < min_samples:
                labels[i] = -2  # Noise
                continue

            # Start new cluster
            labels[i] = cluster_id
            seed_set = list(neighbors)

            j = 0
            while j < len(seed_set):
                q = seed_set[j]
                if labels[q] == -2:  # Was noise, now border point
                    labels[q] = cluster_id
                elif labels[q] == -1:  # Unvisited
                    labels[q] = cluster_id
                    q_neighbors = self._get_neighbors(users, q, eps)
                    if len(q_neighbors) >= min_samples:
                        seed_set.extend(q_neighbors)
                j += 1

            cluster_id += 1

        # Create cluster objects
        cluster_map = defaultdict(list)
        for i, label in enumerate(labels):
            if label >= 0:
                cluster_map[label].append(users[i])

        clusters = []
        for cluster_users in cluster_map.values():
            cluster = RoleCluster(
                user_ids=[u.user_id for u in cluster_users],
                user_count=len(cluster_users)
            )
            clusters.append(cluster)

        return clusters

    def _role_hierarchy_mining(
        self,
        users: List[UserAccessVector],
        all_permissions: List[str],
        min_cluster_size: int
    ) -> List[RoleCluster]:
        """Mine hierarchical role structures based on permission inheritance"""
        # Group users by department first
        dept_groups = defaultdict(list)
        for user in users:
            dept_groups[user.department or "Unknown"].append(user)

        clusters = []

        for dept, dept_users in dept_groups.items():
            if len(dept_users) < min_cluster_size:
                continue

            # Further group by job title within department
            title_groups = defaultdict(list)
            for user in dept_users:
                title_groups[user.job_title or "Unknown"].append(user)

            for title, title_users in title_groups.items():
                if len(title_users) >= min_cluster_size:
                    cluster = RoleCluster(
                        suggested_role_name=f"{dept}_{title}".replace(" ", "_").upper(),
                        user_ids=[u.user_id for u in title_users],
                        user_count=len(title_users),
                        primary_department=dept,
                        primary_job_title=title
                    )
                    clusters.append(cluster)

        return clusters

    def _get_neighbors(self, users: List[UserAccessVector], idx: int, eps: float) -> List[int]:
        """Get neighbors within eps distance"""
        neighbors = []
        for i, user in enumerate(users):
            if i != idx:
                dist = self._jaccard_distance(users[idx].permissions, user.permissions)
                if dist <= eps:
                    neighbors.append(i)
        return neighbors

    def _euclidean_distance(self, v1: List[float], v2: List[float]) -> float:
        """Calculate Euclidean distance"""
        return math.sqrt(sum((a - b) ** 2 for a, b in zip(v1, v2)))

    def _jaccard_distance(self, s1: Set, s2: Set) -> float:
        """Calculate Jaccard distance (1 - Jaccard similarity)"""
        if not s1 and not s2:
            return 0.0
        intersection = len(s1 & s2)
        union = len(s1 | s2)
        return 1.0 - (intersection / union) if union > 0 else 1.0

    def _analyze_cluster(
        self,
        cluster: RoleCluster,
        users: List[UserAccessVector],
        all_permissions: List[str],
        min_frequency: float
    ):
        """Analyze a cluster to extract core permissions and metrics"""
        cluster_users = [u for u in users if u.user_id in cluster.user_ids]
        if not cluster_users:
            return

        # Count permission frequencies
        perm_counts = defaultdict(int)
        for user in cluster_users:
            for perm in user.permissions:
                perm_counts[perm] += 1

        n_users = len(cluster_users)
        core_threshold = min_frequency * n_users
        common_threshold = 0.5 * n_users

        core_perms = []
        common_perms = []
        outlier_perms = []

        for perm, count in perm_counts.items():
            perm_obj = self.permission_index.get(perm, Permission(
                permission_id=perm,
                system="SAP",
                object_type="unknown",
                object_name=perm
            ))

            if count >= core_threshold:
                core_perms.append(perm_obj)
            elif count >= common_threshold:
                common_perms.append(perm_obj)
            else:
                outlier_perms.append(perm_obj)

        cluster.core_permissions = core_perms
        cluster.common_permissions = common_perms
        cluster.outlier_permissions = outlier_perms

        # Calculate permission overlap
        if perm_counts:
            avg_overlap = sum(perm_counts.values()) / len(perm_counts) / n_users * 100
            cluster.permission_overlap_pct = avg_overlap

        # Extract departments and job titles
        departments = defaultdict(int)
        job_titles = defaultdict(int)
        for user in cluster_users:
            if user.department:
                departments[user.department] += 1
            if user.job_title:
                job_titles[user.job_title] += 1

        cluster.departments = list(departments.keys())
        cluster.job_titles = list(job_titles.keys())

        if departments:
            cluster.primary_department = max(departments, key=departments.get)
        if job_titles:
            cluster.primary_job_title = max(job_titles, key=job_titles.get)

        # Generate suggested name
        if not cluster.suggested_role_name:
            dept = cluster.primary_department or "GENERAL"
            title = cluster.primary_job_title or "USER"
            cluster.suggested_role_name = f"Z_{dept[:3]}_{title[:5]}".upper().replace(" ", "_")

        # Calculate cohesion (average similarity within cluster)
        if len(cluster_users) > 1:
            similarities = []
            for i, u1 in enumerate(cluster_users):
                for u2 in cluster_users[i + 1:]:
                    sim = 1.0 - self._jaccard_distance(u1.permissions, u2.permissions)
                    similarities.append(sim)
            cluster.cohesion_score = sum(similarities) / len(similarities) if similarities else 0.0

    def _check_cluster_risks(self, cluster: RoleCluster):
        """Check discovered role for SoD conflicts"""
        if not self.rule_engine:
            return

        # Combine core + common permissions for risk check
        all_perms = cluster.core_permissions + cluster.common_permissions

        # Would call rule engine here in production
        # For now, simple pattern-based check
        conflicts = []

        # Example: Check for common SoD patterns
        tcode_perms = [p for p in all_perms if p.object_type == "tcode"]
        tcodes = {p.object_name.upper() for p in tcode_perms}

        # P2P conflict check
        vendor_tcodes = {"XK01", "FK01", "XK02", "FK02"}
        payment_tcodes = {"F110", "FB10", "F-53"}
        if vendor_tcodes & tcodes and payment_tcodes & tcodes:
            conflicts.append({
                "type": "SoD",
                "severity": "critical",
                "description": "Vendor creation and payment processing",
                "conflicting_permissions": list(vendor_tcodes & tcodes) + list(payment_tcodes & tcodes)
            })

        cluster.sod_conflicts = conflicts
        cluster.risk_score = len(conflicts) * 25  # Simple scoring

    def _calculate_silhouette(
        self,
        clusters: List[RoleCluster],
        users: List[UserAccessVector],
        all_permissions: List[str]
    ) -> float:
        """Calculate silhouette score for clustering quality"""
        if len(clusters) < 2:
            return 0.0

        # Map users to clusters
        user_cluster = {}
        for i, cluster in enumerate(clusters):
            for uid in cluster.user_ids:
                user_cluster[uid] = i

        silhouettes = []
        user_map = {u.user_id: u for u in users}

        for user in users:
            if user.user_id not in user_cluster:
                continue

            my_cluster = user_cluster[user.user_id]

            # a = average distance to same cluster
            same_cluster_users = [user_map[uid] for uid in clusters[my_cluster].user_ids
                                   if uid != user.user_id and uid in user_map]
            if same_cluster_users:
                a = sum(self._jaccard_distance(user.permissions, u.permissions)
                       for u in same_cluster_users) / len(same_cluster_users)
            else:
                a = 0

            # b = minimum average distance to other clusters
            b = float('inf')
            for i, cluster in enumerate(clusters):
                if i == my_cluster:
                    continue
                other_users = [user_map[uid] for uid in cluster.user_ids if uid in user_map]
                if other_users:
                    avg_dist = sum(self._jaccard_distance(user.permissions, u.permissions)
                                  for u in other_users) / len(other_users)
                    b = min(b, avg_dist)

            if b == float('inf'):
                b = 0

            # Silhouette
            if max(a, b) > 0:
                s = (b - a) / max(a, b)
            else:
                s = 0

            silhouettes.append(s)

        return sum(silhouettes) / len(silhouettes) if silhouettes else 0.0

    def _calculate_coverage(self, clusters: List[RoleCluster], users: List[UserAccessVector]) -> float:
        """Calculate what % of user permissions are covered by suggested roles"""
        total_perms = 0
        covered_perms = 0

        for user in users:
            total_perms += len(user.permissions)

            # Find user's cluster
            for cluster in clusters:
                if user.user_id in cluster.user_ids:
                    core_perm_ids = {p.permission_id for p in cluster.core_permissions}
                    covered_perms += len(user.permissions & core_perm_ids)
                    break

        return (covered_perms / total_perms * 100) if total_perms > 0 else 0.0

    def _generate_role_recommendations(self, clusters: List[RoleCluster]) -> List[Dict]:
        """Generate role creation recommendations"""
        recommendations = []

        for cluster in sorted(clusters, key=lambda c: c.cohesion_score, reverse=True):
            if cluster.cohesion_score < 0.3:
                continue  # Skip poorly cohesive clusters

            rec = {
                "suggested_role_name": cluster.suggested_role_name,
                "description": f"Auto-generated role for {cluster.primary_department} {cluster.primary_job_title}",
                "user_count": cluster.user_count,
                "permission_count": len(cluster.core_permissions),
                "confidence_score": round(cluster.cohesion_score * 100, 1),
                "risk_level": "high" if cluster.sod_conflicts else "low",
                "core_permissions": [p.to_dict() for p in cluster.core_permissions[:20]]
            }
            recommendations.append(rec)

        return recommendations

    def _find_redundant_roles(self, clusters: List[RoleCluster]) -> List[Dict]:
        """Find potentially redundant/overlapping roles"""
        redundant = []

        for i, c1 in enumerate(clusters):
            for c2 in clusters[i + 1:]:
                # Check permission overlap
                p1 = {p.permission_id for p in c1.core_permissions}
                p2 = {p.permission_id for p in c2.core_permissions}

                if not p1 or not p2:
                    continue

                overlap = len(p1 & p2) / min(len(p1), len(p2))

                if overlap > 0.8:  # 80% overlap
                    redundant.append({
                        "role_1": c1.suggested_role_name,
                        "role_2": c2.suggested_role_name,
                        "overlap_percentage": round(overlap * 100, 1),
                        "recommendation": "Consider merging these roles"
                    })

        return redundant

    def _suggest_consolidations(self, clusters: List[RoleCluster]) -> List[Dict]:
        """Suggest role consolidation opportunities"""
        suggestions = []

        # Group by department
        dept_clusters = defaultdict(list)
        for cluster in clusters:
            if cluster.primary_department:
                dept_clusters[cluster.primary_department].append(cluster)

        for dept, dept_cluster_list in dept_clusters.items():
            if len(dept_cluster_list) > 3:
                suggestions.append({
                    "type": "department_consolidation",
                    "department": dept,
                    "current_role_count": len(dept_cluster_list),
                    "recommendation": f"Consider consolidating {len(dept_cluster_list)} roles in {dept} department"
                })

        return suggestions

    def get_job(self, job_id: str) -> Optional[MiningResult]:
        """Get a mining job by ID"""
        return self.jobs.get(job_id)

    def get_job_clusters(self, job_id: str) -> List[RoleCluster]:
        """Get clusters from a mining job"""
        job = self.jobs.get(job_id)
        return job.clusters if job else []
