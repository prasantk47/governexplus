# Peer Group Analysis for Behavioral Anomaly Detection
# Comparing user behavior against peers with similar roles

"""
Peer Analysis for Access Risk Analysis.

Provides:
- Peer group formation based on roles/department
- Behavior comparison against peers
- Statistical deviation detection
- Peer-based anomaly scoring

Why this matters:
- Same behavior can be normal for one role, anomalous for another
- Peer comparison provides context-aware detection
- Auditors understand "different from peers" better than raw scores
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Set, Tuple
from datetime import datetime
from collections import defaultdict
import logging
import statistics

from .features import BehaviorFeatureVector

logger = logging.getLogger(__name__)


@dataclass
class PeerDeviationResult:
    """
    Result of peer comparison analysis.

    Shows how a user deviates from their peer group.
    """
    user_id: str
    peer_group_id: str
    peer_group_size: int = 0

    # Deviation metrics
    is_significant_deviation: bool = False
    overall_deviation_score: float = 0.0  # 0-1, higher = more different

    # Feature-level deviations (Z-scores)
    feature_deviations: Dict[str, float] = field(default_factory=dict)
    significant_features: List[str] = field(default_factory=list)

    # Peer comparison stats
    peer_avg_volume: float = 0.0
    user_volume: float = 0.0
    volume_percentile: float = 0.0

    # Explanation
    explanation: str = ""
    risk_adjustment: int = 0

    analyzed_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "peer_group_id": self.peer_group_id,
            "peer_group_size": self.peer_group_size,
            "is_significant_deviation": self.is_significant_deviation,
            "overall_deviation_score": round(self.overall_deviation_score, 4),
            "feature_deviations": {
                k: round(v, 4) for k, v in self.feature_deviations.items()
            },
            "significant_features": self.significant_features,
            "peer_avg_volume": self.peer_avg_volume,
            "user_volume": self.user_volume,
            "volume_percentile": round(self.volume_percentile, 2),
            "explanation": self.explanation,
            "risk_adjustment": self.risk_adjustment,
            "analyzed_at": self.analyzed_at.isoformat(),
        }


@dataclass
class PeerGroup:
    """
    Definition of a peer group for comparison.

    Groups can be formed by:
    - Role (users with same role)
    - Department (users in same department)
    - Job function (users with similar responsibilities)
    - Custom grouping
    """
    group_id: str
    name: str
    members: Set[str] = field(default_factory=set)

    # Group criteria
    roles: Set[str] = field(default_factory=set)
    departments: Set[str] = field(default_factory=set)

    # Aggregate statistics
    feature_stats: Dict[str, Dict[str, float]] = field(default_factory=dict)
    member_vectors: Dict[str, BehaviorFeatureVector] = field(default_factory=dict)

    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    last_updated: datetime = field(default_factory=datetime.now)

    def add_member(
        self,
        user_id: str,
        feature_vector: BehaviorFeatureVector
    ):
        """Add a member with their feature vector."""
        self.members.add(user_id)
        self.member_vectors[user_id] = feature_vector
        self.last_updated = datetime.now()

    def remove_member(self, user_id: str):
        """Remove a member from the group."""
        self.members.discard(user_id)
        self.member_vectors.pop(user_id, None)
        self.last_updated = datetime.now()

    def calculate_stats(self):
        """Calculate aggregate statistics for the group."""
        if not self.member_vectors:
            return

        feature_names = BehaviorFeatureVector.feature_names()
        vectors = [v.to_vector() for v in self.member_vectors.values()]

        for i, name in enumerate(feature_names):
            values = [v[i] for v in vectors]
            if values:
                self.feature_stats[name] = {
                    "mean": statistics.mean(values),
                    "std": statistics.stdev(values) if len(values) > 1 else 0,
                    "min": min(values),
                    "max": max(values),
                    "median": statistics.median(values),
                    "count": len(values),
                }

        self.last_updated = datetime.now()


class PeerGroupAnalyzer:
    """
    Analyzes user behavior relative to peer groups.

    Key capabilities:
    - Automatic peer group formation
    - Feature-level deviation analysis
    - Percentile ranking within peers
    - Risk adjustment based on peer comparison
    """

    # Threshold for significant deviation (Z-score)
    DEVIATION_THRESHOLD = 2.0

    # Minimum peer group size for reliable comparison
    MIN_PEER_GROUP_SIZE = 5

    # Risk adjustment levels
    HIGH_DEVIATION_ADJUSTMENT = 20
    MEDIUM_DEVIATION_ADJUSTMENT = 10
    LOW_DEVIATION_ADJUSTMENT = 5

    def __init__(self):
        """Initialize peer group analyzer."""
        self.peer_groups: Dict[str, PeerGroup] = {}
        self.user_to_groups: Dict[str, Set[str]] = defaultdict(set)

    def create_peer_group(
        self,
        group_id: str,
        name: str,
        roles: Optional[Set[str]] = None,
        departments: Optional[Set[str]] = None
    ) -> PeerGroup:
        """
        Create a new peer group.

        Args:
            group_id: Unique identifier
            name: Human-readable name
            roles: Roles that define this group
            departments: Departments that define this group

        Returns:
            Created PeerGroup
        """
        group = PeerGroup(
            group_id=group_id,
            name=name,
            roles=roles or set(),
            departments=departments or set()
        )
        self.peer_groups[group_id] = group
        return group

    def add_user_to_group(
        self,
        user_id: str,
        group_id: str,
        feature_vector: BehaviorFeatureVector
    ):
        """
        Add a user to a peer group.

        Args:
            user_id: User identifier
            group_id: Peer group ID
            feature_vector: User's behavior features
        """
        group = self.peer_groups.get(group_id)
        if not group:
            logger.warning(f"Peer group {group_id} not found")
            return

        group.add_member(user_id, feature_vector)
        self.user_to_groups[user_id].add(group_id)

    def update_group_stats(self, group_id: str):
        """Recalculate statistics for a peer group."""
        group = self.peer_groups.get(group_id)
        if group:
            group.calculate_stats()

    def update_all_stats(self):
        """Recalculate statistics for all peer groups."""
        for group in self.peer_groups.values():
            group.calculate_stats()

    def analyze_user(
        self,
        user_id: str,
        feature_vector: BehaviorFeatureVector,
        group_id: Optional[str] = None
    ) -> PeerDeviationResult:
        """
        Analyze a user's behavior against their peer group.

        Args:
            user_id: User identifier
            feature_vector: User's current behavior features
            group_id: Optional specific group to compare against

        Returns:
            PeerDeviationResult with deviation analysis
        """
        # Determine peer group
        if group_id:
            groups_to_check = [group_id]
        else:
            groups_to_check = list(self.user_to_groups.get(user_id, set()))

        if not groups_to_check:
            return PeerDeviationResult(
                user_id=user_id,
                peer_group_id="none",
                explanation="No peer group assigned"
            )

        # Analyze against primary peer group
        primary_group_id = groups_to_check[0]
        group = self.peer_groups.get(primary_group_id)

        if not group or len(group.members) < self.MIN_PEER_GROUP_SIZE:
            return PeerDeviationResult(
                user_id=user_id,
                peer_group_id=primary_group_id,
                peer_group_size=len(group.members) if group else 0,
                explanation="Peer group too small for reliable comparison"
            )

        # Ensure stats are calculated
        if not group.feature_stats:
            group.calculate_stats()

        result = PeerDeviationResult(
            user_id=user_id,
            peer_group_id=primary_group_id,
            peer_group_size=len(group.members)
        )

        # Calculate feature-level deviations
        user_vector = feature_vector.to_vector()
        feature_names = BehaviorFeatureVector.feature_names()
        total_deviation = 0
        significant_count = 0

        for i, name in enumerate(feature_names):
            stats = group.feature_stats.get(name, {})
            if not stats:
                continue

            mean = stats.get("mean", 0)
            std = stats.get("std", 0)

            if std > 0:
                z_score = (user_vector[i] - mean) / std
            else:
                z_score = 0

            result.feature_deviations[name] = z_score
            total_deviation += abs(z_score)

            if abs(z_score) > self.DEVIATION_THRESHOLD:
                result.significant_features.append(name)
                significant_count += 1

        # Calculate overall deviation score (normalized)
        avg_deviation = total_deviation / len(feature_names) if feature_names else 0
        result.overall_deviation_score = min(1.0, avg_deviation / 3)  # Normalize to 0-1

        # Volume comparison
        result.user_volume = feature_vector.tcode_exec_count
        volume_stats = group.feature_stats.get("tcode_exec_count", {})
        result.peer_avg_volume = volume_stats.get("mean", 0)

        # Calculate percentile
        if group.member_vectors:
            volumes = [v.tcode_exec_count for v in group.member_vectors.values()]
            volumes_sorted = sorted(volumes)
            position = sum(1 for v in volumes_sorted if v <= result.user_volume)
            result.volume_percentile = (position / len(volumes_sorted)) * 100

        # Determine if significant deviation
        result.is_significant_deviation = (
            significant_count >= 2 or
            avg_deviation > self.DEVIATION_THRESHOLD or
            result.volume_percentile > 95 or
            result.volume_percentile < 5
        )

        # Calculate risk adjustment
        if result.is_significant_deviation:
            if avg_deviation > 3 or significant_count >= 4:
                result.risk_adjustment = self.HIGH_DEVIATION_ADJUSTMENT
            elif avg_deviation > 2 or significant_count >= 2:
                result.risk_adjustment = self.MEDIUM_DEVIATION_ADJUSTMENT
            else:
                result.risk_adjustment = self.LOW_DEVIATION_ADJUSTMENT

        # Generate explanation
        result.explanation = self._generate_explanation(result)

        return result

    def _generate_explanation(self, result: PeerDeviationResult) -> str:
        """Generate human-readable explanation of peer deviation."""
        if not result.is_significant_deviation:
            return "Behavior consistent with peer group"

        explanations = []

        # Feature descriptions
        feature_descriptions = {
            "tcode_exec_count": "transaction volume",
            "sensitive_tcode_ratio": "sensitive transaction ratio",
            "after_hours_ratio": "off-hours activity",
            "weekend_ratio": "weekend activity",
            "unused_privilege_ratio": "unused privileges",
        }

        for feature in result.significant_features[:3]:
            deviation = result.feature_deviations.get(feature, 0)
            desc = feature_descriptions.get(feature, feature.replace("_", " "))
            direction = "higher" if deviation > 0 else "lower"
            explanations.append(f"{abs(deviation):.1f}x {direction} {desc} than peers")

        if result.volume_percentile > 95:
            explanations.append(f"activity in top {100 - result.volume_percentile:.0f}% of peers")
        elif result.volume_percentile < 5:
            explanations.append(f"activity in bottom {result.volume_percentile:.0f}% of peers")

        if explanations:
            return "Deviates from peer group: " + "; ".join(explanations)
        return "Behavior deviates significantly from peer patterns"

    def get_peer_metrics(
        self,
        user_id: str,
        group_id: Optional[str] = None
    ) -> Dict[str, float]:
        """
        Get peer comparison metrics for risk scoring.

        Args:
            user_id: User identifier
            group_id: Optional specific group

        Returns:
            Metrics dictionary for use in risk scoring
        """
        groups = [group_id] if group_id else list(self.user_to_groups.get(user_id, set()))

        if not groups:
            return {"avg_volume": 0, "deviation_score": 0}

        group = self.peer_groups.get(groups[0])
        if not group or not group.feature_stats:
            return {"avg_volume": 0, "deviation_score": 0}

        volume_stats = group.feature_stats.get("tcode_exec_count", {})

        return {
            "avg_volume": volume_stats.get("mean", 0),
            "std_volume": volume_stats.get("std", 0),
            "peer_count": len(group.members),
            "deviation_score": 0,  # Updated after analysis
        }

    def auto_assign_groups(
        self,
        user_id: str,
        user_roles: Set[str],
        user_department: str,
        feature_vector: BehaviorFeatureVector
    ):
        """
        Automatically assign user to appropriate peer groups.

        Args:
            user_id: User identifier
            user_roles: User's roles
            user_department: User's department
            feature_vector: User's behavior features
        """
        assigned = False

        for group in self.peer_groups.values():
            # Match by role
            if group.roles and group.roles & user_roles:
                self.add_user_to_group(user_id, group.group_id, feature_vector)
                assigned = True

            # Match by department
            if group.departments and user_department in group.departments:
                self.add_user_to_group(user_id, group.group_id, feature_vector)
                assigned = True

        if not assigned:
            logger.debug(f"User {user_id} not assigned to any peer group")
