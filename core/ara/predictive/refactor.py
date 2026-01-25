# Auto-Role Refactoring Suggestions
# Intelligent role redesign recommendations

"""
Role Refactoring Engine for GOVERNEX+.

SAP GRC detects risk but does not tell how to fix roles.

GOVERNEX+:
- Detects → Explains → Suggests redesign

Refactoring triggers:
- Role is toxic (graph-based)
- Role has low usage density
- Role mixes unrelated business actions
- Role repeatedly causes SoD violations
"""

from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional, Any
from datetime import datetime
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class RefactorAction(Enum):
    """Types of refactoring actions."""
    SPLIT_ROLE = "SPLIT_ROLE"
    MERGE_ROLES = "MERGE_ROLES"
    REMOVE_PRIVILEGES = "REMOVE_PRIVILEGES"
    REDESIGN = "REDESIGN"
    DEPRECATE = "DEPRECATE"


class RefactorPriority(Enum):
    """Priority levels for refactoring."""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


@dataclass
class PrivilegeAnalysis:
    """Analysis of privilege usage within a role."""
    privilege_id: str
    tcode: str
    description: str

    # Usage metrics
    usage_count: int = 0
    last_used: Optional[datetime] = None
    unique_users: int = 0

    # Classification
    is_sensitive: bool = False
    business_action: str = ""

    # Recommendation
    keep: bool = True
    reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "privilege_id": self.privilege_id,
            "tcode": self.tcode,
            "description": self.description,
            "usage_count": self.usage_count,
            "last_used": self.last_used.isoformat() if self.last_used else None,
            "unique_users": self.unique_users,
            "is_sensitive": self.is_sensitive,
            "business_action": self.business_action,
            "keep": self.keep,
            "reason": self.reason,
        }


@dataclass
class RoleSplitRecommendation:
    """Recommendation for splitting a role."""
    new_role_name: str
    business_function: str
    privileges_to_include: List[str]
    privileges_to_exclude: List[str]
    rationale: str
    estimated_users: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "new_role_name": self.new_role_name,
            "business_function": self.business_function,
            "privileges_to_include": self.privileges_to_include,
            "privileges_to_exclude": self.privileges_to_exclude,
            "rationale": self.rationale,
            "estimated_users": self.estimated_users,
        }


@dataclass
class RefactorSuggestion:
    """
    Complete refactoring suggestion for a role.

    Contains:
    - Action to take
    - Detailed analysis
    - Implementation steps
    - Impact assessment
    """
    suggestion_id: str
    role_id: str
    action: RefactorAction
    priority: RefactorPriority

    # Analysis
    trigger_reason: str
    toxicity_score: float = 0
    usage_density: float = 0  # % of privileges actually used

    # Privilege breakdown
    total_privileges: int = 0
    frequently_used: int = 0
    rarely_used: int = 0
    never_used: int = 0

    # Detailed analysis
    privilege_analysis: List[PrivilegeAnalysis] = field(default_factory=list)

    # For split recommendations
    split_recommendations: List[RoleSplitRecommendation] = field(default_factory=list)

    # For remove privileges
    privileges_to_remove: List[str] = field(default_factory=list)

    # Impact
    affected_users: int = 0
    sod_conflicts_resolved: int = 0
    risk_reduction_estimate: int = 0  # Points

    # Implementation
    implementation_steps: List[str] = field(default_factory=list)
    estimated_effort: str = ""  # "LOW", "MEDIUM", "HIGH"

    # Metadata
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "suggestion_id": self.suggestion_id,
            "role_id": self.role_id,
            "action": self.action.value,
            "priority": self.priority.value,
            "trigger_reason": self.trigger_reason,
            "toxicity_score": round(self.toxicity_score, 2),
            "usage_density": round(self.usage_density, 4),
            "privilege_breakdown": {
                "total": self.total_privileges,
                "frequently_used": self.frequently_used,
                "rarely_used": self.rarely_used,
                "never_used": self.never_used,
            },
            "split_recommendations": [r.to_dict() for r in self.split_recommendations],
            "privileges_to_remove": self.privileges_to_remove,
            "affected_users": self.affected_users,
            "sod_conflicts_resolved": self.sod_conflicts_resolved,
            "risk_reduction_estimate": self.risk_reduction_estimate,
            "implementation_steps": self.implementation_steps,
            "estimated_effort": self.estimated_effort,
            "created_at": self.created_at.isoformat(),
        }


class RoleRefactorEngine:
    """
    Generates intelligent role refactoring suggestions.

    Key capabilities:
    - Analyzes privilege usage patterns
    - Identifies role toxicity
    - Suggests optimal role splits
    - Estimates impact and effort
    """

    # Thresholds
    LOW_USAGE_THRESHOLD = 0.3  # Below 30% usage = underutilized
    RARELY_USED_THRESHOLD = 10  # Less than 10 uses = rarely used
    NEVER_USED_DAYS = 90  # Not used in 90 days = never used
    MAX_PRIVILEGES_PER_ROLE = 50  # Above this = too broad
    MIN_USERS_FOR_ROLE = 3  # Below this = consider deprecation

    def __init__(self):
        """Initialize refactor engine."""
        self._suggestion_counter = 0

    def analyze_role(
        self,
        role_id: str,
        privileges: List[Dict[str, Any]],
        usage_data: Dict[str, Dict[str, Any]],
        user_count: int,
        toxicity_score: float = 0,
        sod_conflicts: int = 0
    ) -> Optional[RefactorSuggestion]:
        """
        Analyze a role and generate refactoring suggestion.

        Args:
            role_id: Role identifier
            privileges: List of privileges in the role
            usage_data: Usage data per privilege {priv_id: {count, last_used, ...}}
            user_count: Number of users with this role
            toxicity_score: Toxicity score from ToxicRoleDetector
            sod_conflicts: Number of SoD conflicts involving this role

        Returns:
            RefactorSuggestion if refactoring recommended, None otherwise
        """
        # Analyze privileges
        privilege_analysis = self._analyze_privileges(privileges, usage_data)

        # Calculate usage metrics
        frequently_used = len([p for p in privilege_analysis if p.usage_count >= self.RARELY_USED_THRESHOLD])
        rarely_used = len([p for p in privilege_analysis if 0 < p.usage_count < self.RARELY_USED_THRESHOLD])
        never_used = len([p for p in privilege_analysis if p.usage_count == 0])

        total_privileges = len(privilege_analysis)
        usage_density = frequently_used / max(total_privileges, 1)

        # Determine action
        action, priority, reason = self._determine_action(
            total_privileges=total_privileges,
            usage_density=usage_density,
            never_used=never_used,
            user_count=user_count,
            toxicity_score=toxicity_score,
            sod_conflicts=sod_conflicts,
        )

        if action is None:
            return None

        # Create suggestion
        self._suggestion_counter += 1
        suggestion_id = f"REFACTOR-{role_id}-{self._suggestion_counter}"

        suggestion = RefactorSuggestion(
            suggestion_id=suggestion_id,
            role_id=role_id,
            action=action,
            priority=priority,
            trigger_reason=reason,
            toxicity_score=toxicity_score,
            usage_density=usage_density,
            total_privileges=total_privileges,
            frequently_used=frequently_used,
            rarely_used=rarely_used,
            never_used=never_used,
            privilege_analysis=privilege_analysis,
            affected_users=user_count,
            sod_conflicts_resolved=sod_conflicts if action in [RefactorAction.SPLIT_ROLE, RefactorAction.REDESIGN] else 0,
        )

        # Generate specific recommendations based on action
        if action == RefactorAction.SPLIT_ROLE:
            suggestion.split_recommendations = self._generate_split_recommendations(
                role_id, privilege_analysis, user_count
            )
            suggestion.risk_reduction_estimate = min(30, toxicity_score * 0.4)
            suggestion.estimated_effort = "MEDIUM"

        elif action == RefactorAction.REMOVE_PRIVILEGES:
            suggestion.privileges_to_remove = [
                p.privilege_id for p in privilege_analysis if not p.keep
            ]
            suggestion.risk_reduction_estimate = min(20, len(suggestion.privileges_to_remove) * 2)
            suggestion.estimated_effort = "LOW"

        elif action == RefactorAction.REDESIGN:
            suggestion.split_recommendations = self._generate_split_recommendations(
                role_id, privilege_analysis, user_count
            )
            suggestion.risk_reduction_estimate = min(50, toxicity_score * 0.6)
            suggestion.estimated_effort = "HIGH"

        elif action == RefactorAction.DEPRECATE:
            suggestion.risk_reduction_estimate = 10
            suggestion.estimated_effort = "LOW"

        # Generate implementation steps
        suggestion.implementation_steps = self._generate_implementation_steps(
            action, role_id, suggestion
        )

        return suggestion

    def _analyze_privileges(
        self,
        privileges: List[Dict[str, Any]],
        usage_data: Dict[str, Dict[str, Any]]
    ) -> List[PrivilegeAnalysis]:
        """Analyze each privilege in the role."""
        analysis = []

        for priv in privileges:
            priv_id = priv.get("id") or priv.get("privilege_id", "")
            usage = usage_data.get(priv_id, {})

            pa = PrivilegeAnalysis(
                privilege_id=priv_id,
                tcode=priv.get("tcode", ""),
                description=priv.get("description", ""),
                usage_count=usage.get("count", 0),
                unique_users=usage.get("unique_users", 0),
                is_sensitive=priv.get("is_sensitive", False),
                business_action=priv.get("business_action", ""),
            )

            last_used = usage.get("last_used")
            if last_used:
                if isinstance(last_used, str):
                    pa.last_used = datetime.fromisoformat(last_used)
                else:
                    pa.last_used = last_used

            # Determine if privilege should be kept
            if pa.usage_count == 0:
                pa.keep = False
                pa.reason = "Never used"
            elif pa.last_used:
                days_since = (datetime.now() - pa.last_used).days
                if days_since > self.NEVER_USED_DAYS:
                    pa.keep = False
                    pa.reason = f"Not used in {days_since} days"

            analysis.append(pa)

        return analysis

    def _determine_action(
        self,
        total_privileges: int,
        usage_density: float,
        never_used: int,
        user_count: int,
        toxicity_score: float,
        sod_conflicts: int
    ) -> tuple[Optional[RefactorAction], Optional[RefactorPriority], str]:
        """Determine the appropriate refactoring action."""
        # Critical toxicity -> Redesign
        if toxicity_score >= 75:
            return (
                RefactorAction.REDESIGN,
                RefactorPriority.CRITICAL,
                f"Critical toxicity score ({toxicity_score:.0f})"
            )

        # High toxicity or multiple SoD conflicts -> Split
        if toxicity_score >= 50 or sod_conflicts >= 3:
            return (
                RefactorAction.SPLIT_ROLE,
                RefactorPriority.HIGH,
                f"High toxicity ({toxicity_score:.0f}) or SoD conflicts ({sod_conflicts})"
            )

        # Too few users -> Deprecate
        if user_count < self.MIN_USERS_FOR_ROLE:
            return (
                RefactorAction.DEPRECATE,
                RefactorPriority.LOW,
                f"Only {user_count} users assigned"
            )

        # Too many privileges -> Split
        if total_privileges > self.MAX_PRIVILEGES_PER_ROLE:
            return (
                RefactorAction.SPLIT_ROLE,
                RefactorPriority.MEDIUM,
                f"Exceeds maximum privileges ({total_privileges})"
            )

        # Low usage density -> Remove unused
        if usage_density < self.LOW_USAGE_THRESHOLD and never_used > 5:
            return (
                RefactorAction.REMOVE_PRIVILEGES,
                RefactorPriority.MEDIUM,
                f"Low usage density ({usage_density:.0%}), {never_used} unused privileges"
            )

        # No action needed
        return (None, None, "")

    def _generate_split_recommendations(
        self,
        role_id: str,
        privilege_analysis: List[PrivilegeAnalysis],
        user_count: int
    ) -> List[RoleSplitRecommendation]:
        """Generate recommendations for splitting a role."""
        recommendations = []

        # Group privileges by business action
        action_groups: Dict[str, List[PrivilegeAnalysis]] = {}
        for pa in privilege_analysis:
            action = pa.business_action or "GENERAL"
            if action not in action_groups:
                action_groups[action] = []
            action_groups[action].append(pa)

        # Create split recommendation for each group
        for i, (action, privs) in enumerate(action_groups.items()):
            if len(privs) < 2:
                continue

            priv_ids = [p.privilege_id for p in privs if p.keep]
            excluded = [p.privilege_id for p in privilege_analysis if p.privilege_id not in priv_ids]

            recommendations.append(RoleSplitRecommendation(
                new_role_name=f"{role_id}_{action.replace(' ', '_').upper()}",
                business_function=action,
                privileges_to_include=priv_ids,
                privileges_to_exclude=excluded,
                rationale=f"Separate {action} functions into dedicated role",
                estimated_users=user_count // len(action_groups),
            ))

        return recommendations[:5]  # Max 5 recommendations

    def _generate_implementation_steps(
        self,
        action: RefactorAction,
        role_id: str,
        suggestion: RefactorSuggestion
    ) -> List[str]:
        """Generate implementation steps for the refactoring."""
        steps = []

        if action == RefactorAction.SPLIT_ROLE:
            steps.extend([
                f"1. Create new roles based on business function groupings",
                f"2. Copy relevant privileges to each new role",
                f"3. Test new roles in development/QA environment",
                f"4. Identify users for each new role based on job function",
                f"5. Assign users to appropriate new roles",
                f"6. Remove original role '{role_id}' from users",
                f"7. Deprecate original role after transition period",
            ])

        elif action == RefactorAction.REMOVE_PRIVILEGES:
            count = len(suggestion.privileges_to_remove)
            steps.extend([
                f"1. Review {count} unused privileges for removal",
                f"2. Verify none are needed for business operations",
                f"3. Remove privileges from role in development",
                f"4. Test role functionality after removal",
                f"5. Transport changes to production",
                f"6. Monitor for any access issues",
            ])

        elif action == RefactorAction.REDESIGN:
            steps.extend([
                f"1. Document current role usage and business requirements",
                f"2. Design new role structure based on business functions",
                f"3. Create new roles with minimal necessary privileges",
                f"4. Develop migration plan for existing users",
                f"5. Test new roles thoroughly",
                f"6. Execute phased migration",
                f"7. Decommission old role",
            ])

        elif action == RefactorAction.DEPRECATE:
            steps.extend([
                f"1. Identify alternative roles for existing users",
                f"2. Migrate {suggestion.affected_users} users to alternative roles",
                f"3. Remove role from all users",
                f"4. Mark role as deprecated",
                f"5. Delete role after retention period",
            ])

        return steps

    def analyze_roles_batch(
        self,
        roles: List[Dict[str, Any]]
    ) -> List[RefactorSuggestion]:
        """
        Analyze multiple roles and return all suggestions.

        Args:
            roles: List of role dicts with id, privileges, usage_data, user_count, etc.

        Returns:
            List of RefactorSuggestion sorted by priority
        """
        suggestions = []

        for role in roles:
            suggestion = self.analyze_role(
                role_id=role["id"],
                privileges=role.get("privileges", []),
                usage_data=role.get("usage_data", {}),
                user_count=role.get("user_count", 0),
                toxicity_score=role.get("toxicity_score", 0),
                sod_conflicts=role.get("sod_conflicts", 0),
            )
            if suggestion:
                suggestions.append(suggestion)

        # Sort by priority
        priority_order = {
            RefactorPriority.CRITICAL: 0,
            RefactorPriority.HIGH: 1,
            RefactorPriority.MEDIUM: 2,
            RefactorPriority.LOW: 3,
        }
        suggestions.sort(key=lambda s: priority_order[s.priority])

        return suggestions
