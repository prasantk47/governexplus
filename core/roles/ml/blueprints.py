# Role Blueprint Generator
# AI-suggested role designs from behavior clusters

"""
Role Blueprint Generation for GOVERNEX+.

AI generates candidate roles from discovered clusters:
- Based on actual usage (not guesswork)
- Automatically removes unused permissions
- Prevents SoD by design
"""

from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional, Any, Tuple
from datetime import datetime
from enum import Enum
import logging

from .clustering import ClusterProfile, ClusterResult

logger = logging.getLogger(__name__)


class BlueprintStatus(Enum):
    """Status of a role blueprint."""
    DRAFT = "DRAFT"
    VALIDATED = "VALIDATED"
    BLOCKED = "BLOCKED"
    APPROVED = "APPROVED"
    IMPLEMENTED = "IMPLEMENTED"


class ValidationResult(Enum):
    """Result of blueprint validation."""
    SAFE = "SAFE"
    WARNING = "WARNING"
    BLOCKED = "BLOCKED"


@dataclass
class PermissionRecommendation:
    """Recommendation for a permission."""
    permission_id: str
    action: str  # "INCLUDE", "EXCLUDE", "REVIEW"
    reason: str
    confidence: float = 0.0
    usage_percentage: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "permission_id": self.permission_id,
            "action": self.action,
            "reason": self.reason,
            "confidence": round(self.confidence, 4),
            "usage_percentage": round(self.usage_percentage, 2),
        }


@dataclass
class BlueprintValidation:
    """Validation result for a blueprint."""
    result: ValidationResult = ValidationResult.SAFE
    can_proceed: bool = True
    block_reason: str = ""

    # Findings
    sod_conflicts: List[Dict[str, Any]] = field(default_factory=list)
    toxic_paths: List[Dict[str, Any]] = field(default_factory=list)
    excessive_permissions: List[str] = field(default_factory=list)

    # Risk metrics
    predicted_risk_score: float = 0.0
    risk_delta: float = 0.0  # vs current state

    # Recommendations
    required_changes: List[str] = field(default_factory=list)
    suggested_splits: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "result": self.result.value,
            "can_proceed": self.can_proceed,
            "block_reason": self.block_reason,
            "sod_conflicts": self.sod_conflicts,
            "toxic_paths": self.toxic_paths,
            "excessive_permissions": self.excessive_permissions,
            "predicted_risk_score": round(self.predicted_risk_score, 2),
            "risk_delta": round(self.risk_delta, 2),
            "required_changes": self.required_changes,
            "suggested_splits": self.suggested_splits,
        }


@dataclass
class RoleBlueprint:
    """
    AI-suggested role design.

    Based on actual usage, not assumptions.
    """
    blueprint_id: str
    name: str
    description: str

    # Source
    source_cluster_id: int = -1
    derived_from_users: int = 0

    # Permissions
    included_permissions: List[str] = field(default_factory=list)
    excluded_permissions: List[str] = field(default_factory=list)
    permission_recommendations: List[PermissionRecommendation] = field(default_factory=list)

    # Business alignment
    business_process: str = ""
    job_function: str = ""

    # Risk analysis
    predicted_risk_score: float = 0.0
    has_sod_conflicts: bool = False
    is_toxic: bool = False

    # Confidence
    confidence: float = 0.0
    evidence_strength: str = ""  # STRONG, MODERATE, WEAK

    # Validation
    status: BlueprintStatus = BlueprintStatus.DRAFT
    validation: Optional[BlueprintValidation] = None

    # Comparison
    similar_existing_roles: List[str] = field(default_factory=list)
    replaces_roles: List[str] = field(default_factory=list)
    consolidates_roles: List[str] = field(default_factory=list)

    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    created_by: str = "AI"
    approved_by: str = ""
    approved_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "blueprint_id": self.blueprint_id,
            "name": self.name,
            "description": self.description,
            "source_cluster_id": self.source_cluster_id,
            "derived_from_users": self.derived_from_users,
            "included_permissions": self.included_permissions,
            "excluded_permissions": self.excluded_permissions,
            "permission_recommendations": [
                r.to_dict() for r in self.permission_recommendations
            ],
            "business_process": self.business_process,
            "job_function": self.job_function,
            "predicted_risk_score": round(self.predicted_risk_score, 2),
            "has_sod_conflicts": self.has_sod_conflicts,
            "is_toxic": self.is_toxic,
            "confidence": round(self.confidence, 4),
            "evidence_strength": self.evidence_strength,
            "status": self.status.value,
            "validation": self.validation.to_dict() if self.validation else None,
            "similar_existing_roles": self.similar_existing_roles,
            "replaces_roles": self.replaces_roles,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class BlueprintSuggestion:
    """
    Complete suggestion including original and alternatives.
    """
    primary_blueprint: RoleBlueprint
    alternative_blueprints: List[RoleBlueprint] = field(default_factory=list)

    # Impact analysis
    users_affected: int = 0
    permission_reduction: float = 0.0
    risk_reduction: float = 0.0

    # Action required
    recommended_action: str = ""  # "IMPLEMENT", "REVIEW", "SPLIT", "REJECT"
    action_rationale: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "primary_blueprint": self.primary_blueprint.to_dict(),
            "alternative_blueprints": [
                b.to_dict() for b in self.alternative_blueprints
            ],
            "users_affected": self.users_affected,
            "permission_reduction": round(self.permission_reduction, 2),
            "risk_reduction": round(self.risk_reduction, 2),
            "recommended_action": self.recommended_action,
            "action_rationale": self.action_rationale,
        }


class RoleBlueprintGenerator:
    """
    Generates role blueprints from behavior clusters.

    Key capabilities:
    - Generate role designs from clusters
    - Validate against SoD rules
    - Suggest permission removals
    - Calculate risk reduction
    """

    # SoD rules for validation
    SOD_RULES = [
        {"actions": {"CREATE_VENDOR", "EXECUTE_PAYMENT"}, "severity": "CRITICAL"},
        {"actions": {"CREATE_PO", "POST_GOODS_RECEIPT"}, "severity": "HIGH"},
        {"actions": {"HIRE_EMPLOYEE", "EXECUTE_PAYROLL"}, "severity": "CRITICAL"},
        {"actions": {"CREATE_USER", "ASSIGN_ROLE"}, "severity": "CRITICAL"},
        {"actions": {"CREATE_INVOICE", "APPROVE_INVOICE"}, "severity": "HIGH"},
    ]

    # Toxic paths (complete fraud cycles)
    TOXIC_PATHS = [
        {"name": "P2P Fraud", "actions": {"CREATE_VENDOR", "CREATE_PO", "EXECUTE_PAYMENT"}},
        {"name": "Payroll Fraud", "actions": {"HIRE_EMPLOYEE", "CHANGE_SALARY", "EXECUTE_PAYROLL"}},
        {"name": "Privilege Escalation", "actions": {"CREATE_USER", "ASSIGN_ROLE", "MODIFY_ROLE"}},
    ]

    # Permission to business action mapping
    PERMISSION_ACTIONS = {
        "FK01": "CREATE_VENDOR",
        "FK02": "MODIFY_VENDOR",
        "XK01": "CREATE_VENDOR",
        "ME21N": "CREATE_PO",
        "ME22N": "MODIFY_PO",
        "MIGO": "POST_GOODS_RECEIPT",
        "F-53": "EXECUTE_PAYMENT",
        "F110": "EXECUTE_PAYMENT",
        "FB60": "CREATE_INVOICE",
        "MIRO": "CREATE_INVOICE",
        "PA40": "HIRE_EMPLOYEE",
        "PA30": "CHANGE_SALARY",
        "PC00_M99_CIPE": "EXECUTE_PAYROLL",
        "SU01": "CREATE_USER",
        "PFCG": "MODIFY_ROLE",
        "SU10": "ASSIGN_ROLE",
    }

    def __init__(self):
        """Initialize generator."""
        self._blueprint_counter = 0

    def generate_from_cluster(
        self,
        cluster: ClusterProfile,
        user_permissions: Dict[str, List[str]],
        usage_data: Optional[Dict[str, Dict[str, int]]] = None,
        existing_roles: Optional[List[Dict[str, Any]]] = None
    ) -> BlueprintSuggestion:
        """
        Generate role blueprint from a behavior cluster.

        Args:
            cluster: Discovered behavior cluster
            user_permissions: Mapping of user_id -> permissions
            usage_data: Optional usage counts per user/permission
            existing_roles: Optional list of existing roles for comparison

        Returns:
            BlueprintSuggestion with primary and alternative blueprints
        """
        self._blueprint_counter += 1

        # Analyze permissions across cluster members
        permission_analysis = self._analyze_cluster_permissions(
            cluster, user_permissions, usage_data
        )

        # Create primary blueprint
        blueprint = self._create_blueprint(
            cluster, permission_analysis
        )

        # Validate blueprint
        blueprint.validation = self._validate_blueprint(blueprint)
        if blueprint.validation.result == ValidationResult.BLOCKED:
            blueprint.status = BlueprintStatus.BLOCKED
        elif blueprint.validation.result == ValidationResult.WARNING:
            blueprint.status = BlueprintStatus.DRAFT
        else:
            blueprint.status = BlueprintStatus.VALIDATED

        # Find similar existing roles
        if existing_roles:
            blueprint.similar_existing_roles = self._find_similar_roles(
                blueprint, existing_roles
            )

        # Create alternatives if blocked
        alternatives = []
        if blueprint.status == BlueprintStatus.BLOCKED:
            alternatives = self._generate_alternatives(
                cluster, permission_analysis, blueprint.validation
            )

        # Calculate impact
        total_perms = sum(
            len(user_permissions.get(u, []))
            for u in cluster.member_user_ids
        )
        included_perms = len(blueprint.included_permissions) * cluster.member_count
        permission_reduction = (
            (total_perms - included_perms) / total_perms * 100
            if total_perms > 0 else 0
        )

        # Determine recommended action
        recommended_action, rationale = self._determine_action(
            blueprint, alternatives
        )

        return BlueprintSuggestion(
            primary_blueprint=blueprint,
            alternative_blueprints=alternatives,
            users_affected=cluster.member_count,
            permission_reduction=permission_reduction,
            risk_reduction=blueprint.validation.risk_delta if blueprint.validation else 0,
            recommended_action=recommended_action,
            action_rationale=rationale,
        )

    def generate_from_clustering_result(
        self,
        result: ClusterResult,
        user_permissions: Dict[str, List[str]],
        usage_data: Optional[Dict[str, Dict[str, int]]] = None,
        existing_roles: Optional[List[Dict[str, Any]]] = None
    ) -> List[BlueprintSuggestion]:
        """
        Generate blueprints for all clusters.

        Args:
            result: Complete clustering result
            user_permissions: Mapping of user_id -> permissions
            usage_data: Optional usage counts
            existing_roles: Optional existing roles

        Returns:
            List of suggestions for each cluster
        """
        suggestions = []

        for cluster in result.clusters:
            suggestion = self.generate_from_cluster(
                cluster, user_permissions, usage_data, existing_roles
            )
            suggestions.append(suggestion)

        return suggestions

    def _analyze_cluster_permissions(
        self,
        cluster: ClusterProfile,
        user_permissions: Dict[str, List[str]],
        usage_data: Optional[Dict[str, Dict[str, int]]]
    ) -> Dict[str, Any]:
        """Analyze permission distribution in cluster."""
        permission_counts: Dict[str, int] = {}
        permission_usage: Dict[str, int] = {}
        total_members = cluster.member_count

        for user_id in cluster.member_user_ids:
            perms = user_permissions.get(user_id, [])
            for perm in perms:
                permission_counts[perm] = permission_counts.get(perm, 0) + 1

                if usage_data and user_id in usage_data:
                    usage = usage_data[user_id].get(perm, 0)
                    permission_usage[perm] = permission_usage.get(perm, 0) + usage

        # Categorize permissions
        consistently_used = []  # Used by most members
        sometimes_used = []  # Used by some members
        rarely_used = []  # Used by few members
        never_used = []  # Assigned but never used

        for perm, count in permission_counts.items():
            ratio = count / total_members
            usage = permission_usage.get(perm, 0)

            if ratio >= 0.8 and usage > 0:
                consistently_used.append(perm)
            elif ratio >= 0.5 and usage > 0:
                sometimes_used.append(perm)
            elif usage > 0:
                rarely_used.append(perm)
            else:
                never_used.append(perm)

        return {
            "permission_counts": permission_counts,
            "permission_usage": permission_usage,
            "consistently_used": consistently_used,
            "sometimes_used": sometimes_used,
            "rarely_used": rarely_used,
            "never_used": never_used,
            "total_members": total_members,
        }

    def _create_blueprint(
        self,
        cluster: ClusterProfile,
        permission_analysis: Dict[str, Any]
    ) -> RoleBlueprint:
        """Create blueprint from analysis."""
        self._blueprint_counter += 1
        blueprint_id = f"BP-{datetime.now().strftime('%Y%m%d')}-{self._blueprint_counter}"

        # Included permissions: consistently + sometimes used
        included = (
            permission_analysis["consistently_used"] +
            permission_analysis["sometimes_used"]
        )

        # Excluded: never used
        excluded = permission_analysis["never_used"]

        # Generate recommendations
        recommendations = []

        for perm in permission_analysis["consistently_used"]:
            usage_pct = (
                permission_analysis["permission_counts"].get(perm, 0) /
                permission_analysis["total_members"] * 100
            )
            recommendations.append(PermissionRecommendation(
                permission_id=perm,
                action="INCLUDE",
                reason=f"Used by {usage_pct:.0f}% of cluster members",
                confidence=0.9,
                usage_percentage=usage_pct,
            ))

        for perm in permission_analysis["sometimes_used"]:
            usage_pct = (
                permission_analysis["permission_counts"].get(perm, 0) /
                permission_analysis["total_members"] * 100
            )
            recommendations.append(PermissionRecommendation(
                permission_id=perm,
                action="INCLUDE",
                reason=f"Used by {usage_pct:.0f}% of cluster members",
                confidence=0.7,
                usage_percentage=usage_pct,
            ))

        for perm in permission_analysis["rarely_used"]:
            usage_pct = (
                permission_analysis["permission_counts"].get(perm, 0) /
                permission_analysis["total_members"] * 100
            )
            recommendations.append(PermissionRecommendation(
                permission_id=perm,
                action="REVIEW",
                reason=f"Only used by {usage_pct:.0f}% - consider separate role",
                confidence=0.6,
                usage_percentage=usage_pct,
            ))

        for perm in permission_analysis["never_used"]:
            recommendations.append(PermissionRecommendation(
                permission_id=perm,
                action="EXCLUDE",
                reason="Never used by any cluster member",
                confidence=0.95,
                usage_percentage=0.0,
            ))

        # Calculate evidence strength
        if cluster.member_count >= 20:
            evidence_strength = "STRONG"
        elif cluster.member_count >= 10:
            evidence_strength = "MODERATE"
        else:
            evidence_strength = "WEAK"

        return RoleBlueprint(
            blueprint_id=blueprint_id,
            name=cluster.suggested_role_name or f"ROLE_CLUSTER_{cluster.cluster_id}",
            description=f"AI-generated role based on {cluster.member_count} users with similar behavior patterns",
            source_cluster_id=cluster.cluster_id,
            derived_from_users=cluster.member_count,
            included_permissions=included,
            excluded_permissions=excluded,
            permission_recommendations=recommendations,
            job_function=cluster.name,
            confidence=cluster.confidence,
            evidence_strength=evidence_strength,
        )

    def _validate_blueprint(
        self,
        blueprint: RoleBlueprint
    ) -> BlueprintValidation:
        """Validate blueprint against SoD and toxic paths."""
        validation = BlueprintValidation()

        # Map permissions to business actions
        blueprint_actions = set()
        for perm in blueprint.included_permissions:
            action = self.PERMISSION_ACTIONS.get(perm)
            if action:
                blueprint_actions.add(action)

        # Check SoD conflicts
        for rule in self.SOD_RULES:
            if rule["actions"].issubset(blueprint_actions):
                validation.sod_conflicts.append({
                    "actions": list(rule["actions"]),
                    "severity": rule["severity"],
                })
                blueprint.has_sod_conflicts = True

        # Check toxic paths
        for path in self.TOXIC_PATHS:
            if path["actions"].issubset(blueprint_actions):
                validation.toxic_paths.append({
                    "name": path["name"],
                    "actions": list(path["actions"]),
                })
                blueprint.is_toxic = True

        # Calculate risk score
        risk_score = 0
        if validation.sod_conflicts:
            critical = sum(1 for c in validation.sod_conflicts if c["severity"] == "CRITICAL")
            high = sum(1 for c in validation.sod_conflicts if c["severity"] == "HIGH")
            risk_score += critical * 30 + high * 15

        if validation.toxic_paths:
            risk_score += len(validation.toxic_paths) * 25

        if len(blueprint.included_permissions) > 50:
            risk_score += 10
            validation.excessive_permissions = [
                f"Role has {len(blueprint.included_permissions)} permissions (>50)"
            ]

        validation.predicted_risk_score = min(100, risk_score)
        blueprint.predicted_risk_score = validation.predicted_risk_score

        # Determine result
        critical_conflicts = [
            c for c in validation.sod_conflicts
            if c["severity"] == "CRITICAL"
        ]

        if validation.toxic_paths:
            validation.result = ValidationResult.BLOCKED
            validation.can_proceed = False
            validation.block_reason = f"Role enables fraud path: {validation.toxic_paths[0]['name']}"
            validation.required_changes.append(
                "Split role to prevent complete fraud path"
            )
        elif critical_conflicts:
            validation.result = ValidationResult.BLOCKED
            validation.can_proceed = False
            validation.block_reason = f"Critical SoD conflict: {critical_conflicts[0]['actions']}"
            validation.required_changes.append(
                f"Remove one of: {', '.join(critical_conflicts[0]['actions'])}"
            )
        elif validation.sod_conflicts:
            validation.result = ValidationResult.WARNING
            validation.can_proceed = True
        else:
            validation.result = ValidationResult.SAFE
            validation.can_proceed = True

        # Generate split suggestions for blocked roles
        if not validation.can_proceed:
            validation.suggested_splits = self._generate_split_suggestions(
                blueprint, validation
            )

        return validation

    def _generate_split_suggestions(
        self,
        blueprint: RoleBlueprint,
        validation: BlueprintValidation
    ) -> List[Dict[str, Any]]:
        """Generate suggestions for splitting a blocked role."""
        splits = []

        if validation.toxic_paths:
            path = validation.toxic_paths[0]
            path_actions = set(path["actions"])

            # Find permissions that enable each action
            action_perms: Dict[str, List[str]] = {}
            for perm in blueprint.included_permissions:
                action = self.PERMISSION_ACTIONS.get(perm)
                if action and action in path_actions:
                    if action not in action_perms:
                        action_perms[action] = []
                    action_perms[action].append(perm)

            # Suggest splitting by first action
            if len(action_perms) >= 2:
                actions_list = list(action_perms.keys())
                split1_action = actions_list[0]
                split2_actions = actions_list[1:]

                split1_perms = action_perms[split1_action]
                split2_perms = []
                for a in split2_actions:
                    split2_perms.extend(action_perms[a])

                other_perms = [
                    p for p in blueprint.included_permissions
                    if p not in split1_perms and p not in split2_perms
                ]

                splits.append({
                    "role_1": {
                        "name": f"{blueprint.name}_A",
                        "permissions": split1_perms + other_perms[:len(other_perms)//2],
                        "action": split1_action,
                    },
                    "role_2": {
                        "name": f"{blueprint.name}_B",
                        "permissions": split2_perms + other_perms[len(other_perms)//2:],
                        "actions": split2_actions,
                    },
                })

        return splits

    def _find_similar_roles(
        self,
        blueprint: RoleBlueprint,
        existing_roles: List[Dict[str, Any]]
    ) -> List[str]:
        """Find existing roles similar to the blueprint."""
        similar = []
        blueprint_perms = set(blueprint.included_permissions)

        for role in existing_roles:
            role_perms = set(role.get("permissions", []))
            if role_perms and blueprint_perms:
                overlap = len(blueprint_perms & role_perms)
                union = len(blueprint_perms | role_perms)
                similarity = overlap / union if union else 0

                if similarity >= 0.7:
                    similar.append(role.get("role_id", role.get("name", "Unknown")))

        return similar

    def _generate_alternatives(
        self,
        cluster: ClusterProfile,
        permission_analysis: Dict[str, Any],
        validation: BlueprintValidation
    ) -> List[RoleBlueprint]:
        """Generate alternative blueprints when primary is blocked."""
        alternatives = []

        if validation.suggested_splits:
            for i, split in enumerate(validation.suggested_splits):
                for j, role_data in enumerate([split.get("role_1"), split.get("role_2")]):
                    if role_data:
                        self._blueprint_counter += 1
                        alt = RoleBlueprint(
                            blueprint_id=f"BP-ALT-{self._blueprint_counter}",
                            name=role_data["name"],
                            description=f"Split role {i+1} part {j+1}",
                            source_cluster_id=cluster.cluster_id,
                            derived_from_users=cluster.member_count,
                            included_permissions=role_data["permissions"],
                            status=BlueprintStatus.DRAFT,
                        )
                        alt.validation = self._validate_blueprint(alt)
                        if alt.validation.can_proceed:
                            alternatives.append(alt)

        return alternatives

    def _determine_action(
        self,
        blueprint: RoleBlueprint,
        alternatives: List[RoleBlueprint]
    ) -> Tuple[str, str]:
        """Determine recommended action."""
        if blueprint.status == BlueprintStatus.VALIDATED:
            return "IMPLEMENT", f"Role design is safe with {blueprint.confidence:.0%} confidence"

        if blueprint.status == BlueprintStatus.BLOCKED:
            if alternatives:
                return "SPLIT", f"Original blocked; {len(alternatives)} alternative designs available"
            else:
                return "REJECT", f"Role blocked: {blueprint.validation.block_reason}"

        return "REVIEW", "Manual review recommended before implementation"

    def refine_blueprint(
        self,
        blueprint: RoleBlueprint,
        action: str,
        permission_id: Optional[str] = None,
        reason: str = ""
    ) -> RoleBlueprint:
        """
        Refine a blueprint based on human feedback.

        Args:
            blueprint: Blueprint to refine
            action: "ADD", "REMOVE", "MOVE_TO_REVIEW"
            permission_id: Permission to act on
            reason: Reason for the change

        Returns:
            Updated blueprint
        """
        if not permission_id:
            return blueprint

        if action == "ADD":
            if permission_id not in blueprint.included_permissions:
                blueprint.included_permissions.append(permission_id)
            if permission_id in blueprint.excluded_permissions:
                blueprint.excluded_permissions.remove(permission_id)

        elif action == "REMOVE":
            if permission_id in blueprint.included_permissions:
                blueprint.included_permissions.remove(permission_id)
            if permission_id not in blueprint.excluded_permissions:
                blueprint.excluded_permissions.append(permission_id)

        # Re-validate
        blueprint.validation = self._validate_blueprint(blueprint)
        blueprint.status = BlueprintStatus.DRAFT

        return blueprint
