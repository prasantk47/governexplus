# Role Engineering and Refactoring
# Auto decomposition, consolidation, and permission clustering

"""
Role Engineering for GOVERNEX+.

Provides:
- Auto role decomposition (split oversized roles)
- Role consolidation (merge similar roles)
- Permission clustering (ML-assisted grouping)
- Data-driven role design
"""

from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional, Any, Tuple
from datetime import datetime
from collections import defaultdict
from enum import Enum
import logging

from .models import Role, Permission, PermissionType, RoleType

logger = logging.getLogger(__name__)


class RecommendationType(Enum):
    """Types of role design recommendations."""
    DECOMPOSE = "DECOMPOSE"
    CONSOLIDATE = "CONSOLIDATE"
    RESTRUCTURE = "RESTRUCTURE"
    REMOVE_PERMISSIONS = "REMOVE_PERMISSIONS"
    ADD_PERMISSIONS = "ADD_PERMISSIONS"


@dataclass
class PermissionCluster:
    """
    A cluster of permissions that are used together.

    ML-assisted grouping based on:
    - Co-occurrence in usage
    - Business process alignment
    - User assignment patterns
    """
    cluster_id: str
    name: str
    permissions: Set[str] = field(default_factory=set)

    # Cluster characteristics
    business_process: str = ""
    cohesion_score: float = 0.0  # How tightly related (0-1)
    usage_correlation: float = 0.0  # How often used together (0-1)

    # Users who need this cluster
    typical_users: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cluster_id": self.cluster_id,
            "name": self.name,
            "permissions": list(self.permissions),
            "business_process": self.business_process,
            "cohesion_score": round(self.cohesion_score, 4),
            "usage_correlation": round(self.usage_correlation, 4),
            "permission_count": len(self.permissions),
        }


@dataclass
class DecompositionSuggestion:
    """Suggestion for splitting a role."""
    suggestion_id: str
    source_role_id: str
    source_role_name: str

    # Proposed new roles
    proposed_roles: List[Dict[str, Any]] = field(default_factory=list)

    # Rationale
    reason: str = ""
    primary_trigger: str = ""  # "size", "toxicity", "sod", "usage"

    # Impact
    risk_reduction_estimate: float = 0.0
    affected_users: int = 0

    # Effort
    complexity: str = "MEDIUM"  # LOW, MEDIUM, HIGH
    estimated_steps: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "suggestion_id": self.suggestion_id,
            "source_role_id": self.source_role_id,
            "source_role_name": self.source_role_name,
            "proposed_roles": self.proposed_roles,
            "reason": self.reason,
            "primary_trigger": self.primary_trigger,
            "risk_reduction_estimate": round(self.risk_reduction_estimate, 2),
            "affected_users": self.affected_users,
            "complexity": self.complexity,
        }


@dataclass
class ConsolidationSuggestion:
    """Suggestion for merging roles."""
    suggestion_id: str
    roles_to_merge: List[str] = field(default_factory=list)
    role_names: List[str] = field(default_factory=list)

    # Proposed merged role
    merged_role_name: str = ""
    merged_permissions: Set[str] = field(default_factory=set)

    # Overlap analysis
    overlap_percentage: float = 0.0
    unique_to_each: Dict[str, Set[str]] = field(default_factory=dict)

    # Rationale
    reason: str = ""

    # Impact
    role_reduction: int = 0
    complexity_reduction: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "suggestion_id": self.suggestion_id,
            "roles_to_merge": self.roles_to_merge,
            "role_names": self.role_names,
            "merged_role_name": self.merged_role_name,
            "merged_permission_count": len(self.merged_permissions),
            "overlap_percentage": round(self.overlap_percentage, 2),
            "reason": self.reason,
            "role_reduction": self.role_reduction,
        }


@dataclass
class RoleDesignRecommendation:
    """Complete role design recommendation."""
    recommendation_id: str
    recommendation_type: RecommendationType
    priority: str = "MEDIUM"  # LOW, MEDIUM, HIGH, CRITICAL

    # Target
    target_role_ids: List[str] = field(default_factory=list)

    # Details
    decomposition: Optional[DecompositionSuggestion] = None
    consolidation: Optional[ConsolidationSuggestion] = None
    permission_changes: List[Dict[str, Any]] = field(default_factory=list)

    # Rationale
    summary: str = ""
    detailed_rationale: str = ""
    evidence: List[str] = field(default_factory=list)

    # Impact
    risk_impact: float = 0.0
    user_impact: int = 0
    effort_estimate: str = ""

    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "recommendation_id": self.recommendation_id,
            "recommendation_type": self.recommendation_type.value,
            "priority": self.priority,
            "target_role_ids": self.target_role_ids,
            "decomposition": self.decomposition.to_dict() if self.decomposition else None,
            "consolidation": self.consolidation.to_dict() if self.consolidation else None,
            "summary": self.summary,
            "evidence": self.evidence,
            "risk_impact": round(self.risk_impact, 2),
            "effort_estimate": self.effort_estimate,
            "created_at": self.created_at.isoformat(),
        }


class RoleEngineer:
    """
    Engineers optimal role designs.

    Key capabilities:
    - Decompose oversized roles
    - Consolidate similar roles
    - Cluster permissions by usage
    - Generate design recommendations
    """

    # Thresholds
    MAX_PERMISSIONS_PER_ROLE = 50
    MIN_OVERLAP_FOR_CONSOLIDATION = 0.7  # 70% overlap
    MIN_CLUSTER_SIZE = 3

    def __init__(self):
        """Initialize role engineer."""
        self._recommendation_counter = 0
        self._clusters: Dict[str, PermissionCluster] = {}

    def analyze_for_decomposition(
        self,
        role: Role,
        usage_data: Dict[str, Any] = None,
        sod_conflicts: List[str] = None,
        toxicity_score: float = 0
    ) -> Optional[DecompositionSuggestion]:
        """
        Analyze if a role should be decomposed.

        Args:
            role: Role to analyze
            usage_data: Usage analytics data
            sod_conflicts: SoD conflicts involving this role
            toxicity_score: Toxicity score from graph analysis

        Returns:
            DecompositionSuggestion if decomposition recommended
        """
        usage_data = usage_data or {}
        sod_conflicts = sod_conflicts or []

        # Check triggers
        triggers = []

        # 1. Size trigger
        if role.permission_count > self.MAX_PERMISSIONS_PER_ROLE:
            triggers.append(("size", f"Role has {role.permission_count} permissions (max: {self.MAX_PERMISSIONS_PER_ROLE})"))

        # 2. Toxicity trigger
        if toxicity_score > 50:
            triggers.append(("toxicity", f"Toxicity score: {toxicity_score}"))

        # 3. SoD trigger
        if len(sod_conflicts) > 2:
            triggers.append(("sod", f"{len(sod_conflicts)} SoD conflicts"))

        # 4. Usage disparity
        if usage_data:
            usage_density = usage_data.get("usage_density", 1.0)
            if usage_density < 0.3:
                triggers.append(("usage", f"Only {usage_density:.0%} of permissions used"))

        if not triggers:
            return None

        # Generate decomposition
        self._recommendation_counter += 1
        suggestion = DecompositionSuggestion(
            suggestion_id=f"DECOMP-{role.role_id}-{self._recommendation_counter}",
            source_role_id=role.role_id,
            source_role_name=role.role_name,
            primary_trigger=triggers[0][0],
            reason="; ".join(t[1] for t in triggers),
            affected_users=role.assignment_count,
        )

        # Generate proposed role splits
        suggestion.proposed_roles = self._generate_splits(role, usage_data)

        # Estimate complexity
        if len(suggestion.proposed_roles) > 3:
            suggestion.complexity = "HIGH"
        elif len(suggestion.proposed_roles) > 1:
            suggestion.complexity = "MEDIUM"
        else:
            suggestion.complexity = "LOW"

        # Estimate risk reduction
        suggestion.risk_reduction_estimate = min(40, toxicity_score * 0.5 + len(sod_conflicts) * 5)

        return suggestion

    def _generate_splits(
        self,
        role: Role,
        usage_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate proposed role splits."""
        splits = []

        # Group permissions by business action
        action_groups: Dict[str, List[Permission]] = defaultdict(list)
        no_action = []

        for perm in role.permissions:
            if perm.business_action:
                action_groups[perm.business_action].append(perm)
            else:
                no_action.append(perm)

        # Create a role for each business action group
        for action, perms in action_groups.items():
            if len(perms) >= self.MIN_CLUSTER_SIZE:
                splits.append({
                    "proposed_name": f"{role.role_id}_{action.upper().replace(' ', '_')}",
                    "business_function": action,
                    "permission_count": len(perms),
                    "permissions": [p.permission_id for p in perms],
                })

        # If no action grouping, split by usage
        if not splits and usage_data:
            frequently_used = usage_data.get("frequently_used", [])
            rarely_used = usage_data.get("rarely_used", [])

            if frequently_used:
                splits.append({
                    "proposed_name": f"{role.role_id}_CORE",
                    "business_function": "Core Functions",
                    "permission_count": len(frequently_used),
                    "permissions": frequently_used,
                })

            if rarely_used:
                splits.append({
                    "proposed_name": f"{role.role_id}_EXTENDED",
                    "business_function": "Extended Functions",
                    "permission_count": len(rarely_used),
                    "permissions": rarely_used,
                })

        # Fallback: split by permission type
        if not splits:
            tcode_perms = [p for p in role.permissions if p.permission_type == PermissionType.TCODE]
            other_perms = [p for p in role.permissions if p.permission_type != PermissionType.TCODE]

            if tcode_perms:
                splits.append({
                    "proposed_name": f"{role.role_id}_TRANSACTIONS",
                    "business_function": "Transaction Access",
                    "permission_count": len(tcode_perms),
                    "permissions": [p.permission_id for p in tcode_perms],
                })

            if other_perms:
                splits.append({
                    "proposed_name": f"{role.role_id}_AUTHORIZATIONS",
                    "business_function": "Authorization Objects",
                    "permission_count": len(other_perms),
                    "permissions": [p.permission_id for p in other_perms],
                })

        return splits

    def analyze_for_consolidation(
        self,
        roles: List[Role],
        min_overlap: float = None
    ) -> List[ConsolidationSuggestion]:
        """
        Analyze roles for consolidation opportunities.

        Args:
            roles: List of roles to analyze
            min_overlap: Minimum overlap percentage for consolidation

        Returns:
            List of consolidation suggestions
        """
        min_overlap = min_overlap or self.MIN_OVERLAP_FOR_CONSOLIDATION
        suggestions = []

        # Compare all pairs
        for i, role1 in enumerate(roles):
            perms1 = set(p.permission_id for p in role1.permissions)

            for role2 in roles[i + 1:]:
                perms2 = set(p.permission_id for p in role2.permissions)

                # Calculate overlap
                intersection = perms1 & perms2
                union = perms1 | perms2

                if not union:
                    continue

                overlap = len(intersection) / len(union)

                if overlap >= min_overlap:
                    self._recommendation_counter += 1

                    suggestion = ConsolidationSuggestion(
                        suggestion_id=f"CONSOL-{self._recommendation_counter}",
                        roles_to_merge=[role1.role_id, role2.role_id],
                        role_names=[role1.role_name, role2.role_name],
                        merged_role_name=f"{role1.role_name}_MERGED",
                        merged_permissions=union,
                        overlap_percentage=overlap * 100,
                        unique_to_each={
                            role1.role_id: perms1 - perms2,
                            role2.role_id: perms2 - perms1,
                        },
                        reason=f"{overlap:.0%} permission overlap between roles",
                        role_reduction=1,
                    )
                    suggestions.append(suggestion)

        return suggestions

    def cluster_permissions(
        self,
        usage_data: List[Dict[str, Any]],
        min_correlation: float = 0.5
    ) -> List[PermissionCluster]:
        """
        Cluster permissions based on co-occurrence.

        Args:
            usage_data: Usage records with user_id and permission_id
            min_correlation: Minimum correlation for clustering

        Returns:
            List of PermissionCluster
        """
        # Build user-permission matrix
        user_perms: Dict[str, Set[str]] = defaultdict(set)
        for record in usage_data:
            user_id = record.get("user_id")
            perm_id = record.get("permission_id")
            if user_id and perm_id:
                user_perms[user_id].add(perm_id)

        # Calculate co-occurrence
        perm_cooccurrence: Dict[Tuple[str, str], int] = defaultdict(int)
        perm_counts: Dict[str, int] = defaultdict(int)

        for user_id, perms in user_perms.items():
            perms_list = list(perms)
            for perm in perms_list:
                perm_counts[perm] += 1

            for i, perm1 in enumerate(perms_list):
                for perm2 in perms_list[i + 1:]:
                    key = tuple(sorted([perm1, perm2]))
                    perm_cooccurrence[key] += 1

        # Calculate correlations and cluster
        clusters = []
        clustered = set()

        for (perm1, perm2), cooccur_count in perm_cooccurrence.items():
            if perm1 in clustered and perm2 in clustered:
                continue

            # Jaccard similarity
            count1 = perm_counts[perm1]
            count2 = perm_counts[perm2]
            union = count1 + count2 - cooccur_count
            correlation = cooccur_count / union if union > 0 else 0

            if correlation >= min_correlation:
                # Find or create cluster
                existing_cluster = None
                for cluster in clusters:
                    if perm1 in cluster.permissions or perm2 in cluster.permissions:
                        existing_cluster = cluster
                        break

                if existing_cluster:
                    existing_cluster.permissions.add(perm1)
                    existing_cluster.permissions.add(perm2)
                    existing_cluster.usage_correlation = max(
                        existing_cluster.usage_correlation, correlation
                    )
                else:
                    cluster = PermissionCluster(
                        cluster_id=f"CLUSTER-{len(clusters) + 1}",
                        name=f"Permission Group {len(clusters) + 1}",
                        permissions={perm1, perm2},
                        usage_correlation=correlation,
                    )
                    clusters.append(cluster)

                clustered.add(perm1)
                clustered.add(perm2)

        # Filter small clusters
        clusters = [c for c in clusters if len(c.permissions) >= self.MIN_CLUSTER_SIZE]

        # Calculate cohesion scores
        for cluster in clusters:
            cluster.cohesion_score = self._calculate_cohesion(
                cluster.permissions, perm_cooccurrence, perm_counts
            )

        self._clusters = {c.cluster_id: c for c in clusters}
        return clusters

    def _calculate_cohesion(
        self,
        permissions: Set[str],
        cooccurrence: Dict[Tuple[str, str], int],
        counts: Dict[str, int]
    ) -> float:
        """Calculate internal cohesion of a cluster."""
        if len(permissions) < 2:
            return 1.0

        perms_list = list(permissions)
        total_pairs = 0
        correlated_pairs = 0

        for i, perm1 in enumerate(perms_list):
            for perm2 in perms_list[i + 1:]:
                total_pairs += 1
                key = tuple(sorted([perm1, perm2]))
                cooccur = cooccurrence.get(key, 0)

                count1 = counts.get(perm1, 1)
                count2 = counts.get(perm2, 1)
                union = count1 + count2 - cooccur

                correlation = cooccur / union if union > 0 else 0
                if correlation > 0.3:
                    correlated_pairs += 1

        return correlated_pairs / total_pairs if total_pairs > 0 else 0

    def generate_recommendations(
        self,
        roles: List[Role],
        usage_data: Dict[str, Dict[str, Any]] = None,
        toxicity_scores: Dict[str, float] = None,
        sod_conflicts: Dict[str, List[str]] = None
    ) -> List[RoleDesignRecommendation]:
        """
        Generate comprehensive role design recommendations.

        Args:
            roles: List of roles to analyze
            usage_data: Usage data per role
            toxicity_scores: Toxicity scores per role
            sod_conflicts: SoD conflicts per role

        Returns:
            List of prioritized recommendations
        """
        usage_data = usage_data or {}
        toxicity_scores = toxicity_scores or {}
        sod_conflicts = sod_conflicts or {}

        recommendations = []

        # 1. Decomposition recommendations
        for role in roles:
            decomp = self.analyze_for_decomposition(
                role,
                usage_data.get(role.role_id, {}),
                sod_conflicts.get(role.role_id, []),
                toxicity_scores.get(role.role_id, 0),
            )
            if decomp:
                self._recommendation_counter += 1
                rec = RoleDesignRecommendation(
                    recommendation_id=f"REC-DECOMP-{self._recommendation_counter}",
                    recommendation_type=RecommendationType.DECOMPOSE,
                    target_role_ids=[role.role_id],
                    decomposition=decomp,
                    summary=f"Decompose role '{role.role_name}' into {len(decomp.proposed_roles)} roles",
                    evidence=[decomp.reason],
                    risk_impact=decomp.risk_reduction_estimate,
                    priority="HIGH" if decomp.primary_trigger in ["toxicity", "sod"] else "MEDIUM",
                )
                recommendations.append(rec)

        # 2. Consolidation recommendations
        consolidations = self.analyze_for_consolidation(roles)
        for consol in consolidations:
            self._recommendation_counter += 1
            rec = RoleDesignRecommendation(
                recommendation_id=f"REC-CONSOL-{self._recommendation_counter}",
                recommendation_type=RecommendationType.CONSOLIDATE,
                target_role_ids=consol.roles_to_merge,
                consolidation=consol,
                summary=f"Consolidate {len(consol.roles_to_merge)} similar roles",
                evidence=[consol.reason],
                priority="LOW",
            )
            recommendations.append(rec)

        # Sort by priority
        priority_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
        recommendations.sort(key=lambda r: priority_order.get(r.priority, 99))

        return recommendations

    def get_cluster(self, cluster_id: str) -> Optional[PermissionCluster]:
        """Get a permission cluster by ID."""
        return self._clusters.get(cluster_id)
