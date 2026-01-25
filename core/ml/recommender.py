"""
Access Recommendation Engine

Provides intelligent access recommendations based on:
- Role similarity
- Peer access patterns
- Usage history
- Risk considerations
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple, Any
from datetime import datetime, timedelta
from enum import Enum
from collections import defaultdict
import uuid
import math


class RecommendationType(Enum):
    """Types of access recommendations"""
    ROLE_SUGGESTION = "role_suggestion"
    ROLE_REMOVAL = "role_removal"
    PERMISSION_ADDITION = "permission_addition"
    PERMISSION_REMOVAL = "permission_removal"
    ROLE_UPGRADE = "role_upgrade"
    ROLE_CONSOLIDATION = "role_consolidation"
    ACCESS_REVIEW = "access_review"
    SIMILAR_USER_ROLE = "similar_user_role"


class RecommendationReason(Enum):
    """Reasons for recommendations"""
    PEER_ACCESS = "peer_access"
    JOB_FUNCTION = "job_function"
    USAGE_PATTERN = "usage_pattern"
    UNUSED_ACCESS = "unused_access"
    RISK_REDUCTION = "risk_reduction"
    EFFICIENCY = "efficiency"
    COMPLIANCE = "compliance"
    ROLE_FIT = "role_fit"


@dataclass
class Recommendation:
    """An access recommendation"""
    recommendation_id: str = field(default_factory=lambda: f"REC-{uuid.uuid4().hex[:8].upper()}")
    rec_type: RecommendationType = RecommendationType.ROLE_SUGGESTION
    reason: RecommendationReason = RecommendationReason.PEER_ACCESS

    # Target
    user_id: str = ""
    user_name: str = ""

    # Recommendation details
    title: str = ""
    description: str = ""
    action: str = ""

    # What's being recommended
    recommended_roles: List[str] = field(default_factory=list)
    recommended_permissions: List[Dict] = field(default_factory=list)
    roles_to_remove: List[str] = field(default_factory=list)
    permissions_to_remove: List[Dict] = field(default_factory=list)

    # Confidence and impact
    confidence_score: float = 0.0  # 0-1
    impact_score: float = 0.0  # 0-1 (how much this improves things)
    risk_impact: float = 0.0  # Positive = increases risk, negative = decreases

    # Evidence
    evidence: List[Dict] = field(default_factory=list)
    similar_users: List[str] = field(default_factory=list)

    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: datetime = field(default_factory=lambda: datetime.now() + timedelta(days=30))
    priority: int = 50  # 1-100, higher = more important

    # Status
    status: str = "pending"  # pending, accepted, rejected, expired
    actioned_by: Optional[str] = None
    actioned_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            "recommendation_id": self.recommendation_id,
            "type": self.rec_type.value,
            "reason": self.reason.value,
            "user_id": self.user_id,
            "user_name": self.user_name,
            "title": self.title,
            "description": self.description,
            "action": self.action,
            "recommended_roles": self.recommended_roles,
            "recommended_permissions": self.recommended_permissions[:10],
            "roles_to_remove": self.roles_to_remove,
            "permissions_to_remove": self.permissions_to_remove[:10],
            "confidence_score": round(self.confidence_score, 2),
            "impact_score": round(self.impact_score, 2),
            "risk_impact": round(self.risk_impact, 2),
            "evidence": self.evidence[:5],
            "similar_users": self.similar_users[:5],
            "priority": self.priority,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat()
        }


@dataclass
class UserProfile:
    """User profile for recommendation engine"""
    user_id: str
    department: str = ""
    job_title: str = ""
    manager_id: str = ""
    location: str = ""
    hire_date: Optional[datetime] = None

    # Current access
    roles: Set[str] = field(default_factory=set)
    permissions: Set[str] = field(default_factory=set)

    # Usage data
    used_permissions: Set[str] = field(default_factory=set)
    unused_permissions: Set[str] = field(default_factory=set)
    usage_frequency: Dict[str, int] = field(default_factory=dict)

    # Historical
    access_requests: int = 0
    access_reviews: int = 0


class AccessRecommender:
    """
    Intelligent Access Recommendation Engine.

    Generates recommendations based on:
    - Peer group analysis
    - Role similarity matching
    - Usage pattern analysis
    - Risk optimization
    """

    def __init__(self, role_miner=None, risk_predictor=None):
        self.role_miner = role_miner
        self.risk_predictor = risk_predictor

        self.user_profiles: Dict[str, UserProfile] = {}
        self.recommendations: Dict[str, Recommendation] = {}

        # Caches
        self.peer_groups: Dict[str, List[str]] = defaultdict(list)  # dept+title -> users
        self.role_users: Dict[str, Set[str]] = defaultdict(set)  # role -> users
        self.role_permissions: Dict[str, Set[str]] = {}  # role -> permissions

        # Create sample data
        self._create_sample_data()

    def _create_sample_data(self):
        """Create sample data for demonstration"""
        # Sample roles and their permissions
        self.role_permissions = {
            "Z_FIN_ANALYST": {"FB03", "FBL1N", "FBL3N", "FBL5N", "FAGLL03", "F.01"},
            "Z_FIN_MANAGER": {"FB03", "FBL1N", "FBL3N", "FBL5N", "FAGLL03", "F.01", "FB01", "FB02", "F-02"},
            "Z_PROC_BUYER": {"ME21N", "ME22N", "ME23N", "ME51N", "ME52N", "ME53N", "ML81N"},
            "Z_PROC_MANAGER": {"ME21N", "ME22N", "ME23N", "ME51N", "ME52N", "ME53N", "ML81N", "ME29N", "ME2M"},
            "Z_HR_SPECIALIST": {"PA20", "PA30", "PA40", "PT61", "PT62", "PT63"},
            "Z_IT_SUPPORT": {"SU01D", "SM21", "ST22", "SM37", "AL11"},
        }

        # Sample users
        sample_users = [
            {"user_id": "JSMITH", "department": "Finance", "job_title": "Finance Analyst",
             "roles": ["Z_FIN_ANALYST"], "permissions": ["FB03", "FBL1N", "FBL3N", "FB01"]},
            {"user_id": "MBROWN", "department": "Finance", "job_title": "Finance Analyst",
             "roles": ["Z_FIN_ANALYST"], "permissions": ["FB03", "FBL1N", "FBL3N", "FBL5N", "FAGLL03"]},
            {"user_id": "TDAVIS", "department": "Finance", "job_title": "Finance Manager",
             "roles": ["Z_FIN_MANAGER"], "permissions": ["FB03", "FBL1N", "FB01", "FB02", "F-02"]},
            {"user_id": "AWILSON", "department": "Procurement", "job_title": "Buyer",
             "roles": ["Z_PROC_BUYER"], "permissions": ["ME21N", "ME22N", "ME23N"]},
            {"user_id": "RJONES", "department": "Procurement", "job_title": "Buyer",
             "roles": ["Z_PROC_BUYER"], "permissions": ["ME21N", "ME22N", "ME23N", "ME51N", "ME52N"]},
        ]

        for user_data in sample_users:
            profile = UserProfile(
                user_id=user_data["user_id"],
                department=user_data["department"],
                job_title=user_data["job_title"],
                roles=set(user_data["roles"]),
                permissions=set(user_data["permissions"])
            )
            self.user_profiles[profile.user_id] = profile

            # Index by peer group
            peer_key = f"{profile.department}:{profile.job_title}"
            self.peer_groups[peer_key].append(profile.user_id)

            # Index by role
            for role in profile.roles:
                self.role_users[role].add(profile.user_id)

    def generate_recommendations(
        self,
        user_id: str,
        user_data: Dict = None,
        include_risk_analysis: bool = True
    ) -> List[Recommendation]:
        """
        Generate all recommendations for a user.
        """
        # Build or update user profile
        profile = self._build_profile(user_id, user_data or {})
        self.user_profiles[user_id] = profile

        recommendations = []

        # 1. Peer-based recommendations
        peer_recs = self._generate_peer_recommendations(profile)
        recommendations.extend(peer_recs)

        # 2. Role consolidation recommendations
        consolidation_recs = self._generate_consolidation_recommendations(profile)
        recommendations.extend(consolidation_recs)

        # 3. Unused access recommendations
        unused_recs = self._generate_unused_access_recommendations(profile)
        recommendations.extend(unused_recs)

        # 4. Role upgrade recommendations
        upgrade_recs = self._generate_upgrade_recommendations(profile)
        recommendations.extend(upgrade_recs)

        # 5. Risk-based recommendations
        if include_risk_analysis:
            risk_recs = self._generate_risk_recommendations(profile)
            recommendations.extend(risk_recs)

        # Store recommendations
        for rec in recommendations:
            self.recommendations[rec.recommendation_id] = rec

        # Sort by priority
        recommendations.sort(key=lambda r: r.priority, reverse=True)

        return recommendations

    def _build_profile(self, user_id: str, user_data: Dict) -> UserProfile:
        """Build user profile from data"""
        existing = self.user_profiles.get(user_id)

        profile = UserProfile(
            user_id=user_id,
            department=user_data.get("department", existing.department if existing else ""),
            job_title=user_data.get("job_title", existing.job_title if existing else ""),
            manager_id=user_data.get("manager_id", ""),
            location=user_data.get("location", ""),
            roles=set(user_data.get("roles", existing.roles if existing else [])),
            permissions=set(user_data.get("permissions", existing.permissions if existing else []))
        )

        # Usage data
        used = set(user_data.get("used_permissions", []))
        profile.used_permissions = used
        profile.unused_permissions = profile.permissions - used

        return profile

    def _generate_peer_recommendations(self, profile: UserProfile) -> List[Recommendation]:
        """Generate recommendations based on peer access patterns"""
        recommendations = []

        peer_key = f"{profile.department}:{profile.job_title}"
        peers = [
            self.user_profiles[uid]
            for uid in self.peer_groups.get(peer_key, [])
            if uid != profile.user_id and uid in self.user_profiles
        ]

        if not peers:
            return recommendations

        # Find permissions common among peers but missing for this user
        peer_permissions = defaultdict(int)
        for peer in peers:
            for perm in peer.permissions:
                peer_permissions[perm] += 1

        # Permissions that most peers have but user doesn't
        missing_perms = []
        for perm, count in peer_permissions.items():
            if perm not in profile.permissions:
                coverage = count / len(peers)
                if coverage >= 0.6:  # At least 60% of peers have it
                    missing_perms.append((perm, coverage))

        if missing_perms:
            # Group by likely role
            missing_perms.sort(key=lambda x: x[1], reverse=True)

            rec = Recommendation(
                rec_type=RecommendationType.PERMISSION_ADDITION,
                reason=RecommendationReason.PEER_ACCESS,
                user_id=profile.user_id,
                title="Missing Common Access",
                description=f"Based on {len(peers)} peers with the same role, you may be missing common permissions",
                action="Request the following permissions commonly held by peers",
                recommended_permissions=[
                    {"permission": p, "peer_coverage": f"{c * 100:.0f}%"}
                    for p, c in missing_perms[:10]
                ],
                confidence_score=min(missing_perms, key=lambda x: x[1])[1] if missing_perms else 0,
                impact_score=0.3,
                evidence=[{"type": "peer_analysis", "peer_count": len(peers)}],
                similar_users=[p.user_id for p in peers[:5]],
                priority=60
            )
            recommendations.append(rec)

        # Find roles common among peers
        peer_roles = defaultdict(int)
        for peer in peers:
            for role in peer.roles:
                peer_roles[role] += 1

        missing_roles = []
        for role, count in peer_roles.items():
            if role not in profile.roles:
                coverage = count / len(peers)
                if coverage >= 0.5:
                    missing_roles.append((role, coverage))

        if missing_roles:
            missing_roles.sort(key=lambda x: x[1], reverse=True)
            role, coverage = missing_roles[0]

            rec = Recommendation(
                rec_type=RecommendationType.SIMILAR_USER_ROLE,
                reason=RecommendationReason.PEER_ACCESS,
                user_id=profile.user_id,
                title=f"Consider Role: {role}",
                description=f"{coverage * 100:.0f}% of peers with same job function have this role",
                action=f"Request role {role} to align with peer access",
                recommended_roles=[role],
                confidence_score=coverage,
                impact_score=0.5,
                evidence=[
                    {"type": "peer_role_analysis", "role": role, "coverage": coverage}
                ],
                similar_users=[
                    p.user_id for p in peers if role in p.roles
                ][:5],
                priority=70
            )
            recommendations.append(rec)

        return recommendations

    def _generate_consolidation_recommendations(self, profile: UserProfile) -> List[Recommendation]:
        """Recommend role consolidation opportunities"""
        recommendations = []

        if len(profile.roles) < 2:
            return recommendations

        # Check if user has roles that could be consolidated
        for role1 in profile.roles:
            for role2 in profile.roles:
                if role1 >= role2:
                    continue

                perms1 = self.role_permissions.get(role1, set())
                perms2 = self.role_permissions.get(role2, set())

                if perms1 and perms2:
                    overlap = len(perms1 & perms2) / min(len(perms1), len(perms2))

                    if overlap > 0.7:  # Significant overlap
                        rec = Recommendation(
                            rec_type=RecommendationType.ROLE_CONSOLIDATION,
                            reason=RecommendationReason.EFFICIENCY,
                            user_id=profile.user_id,
                            title="Role Consolidation Opportunity",
                            description=f"Roles {role1} and {role2} have {overlap * 100:.0f}% permission overlap",
                            action="Consider consolidating or reviewing these overlapping roles",
                            roles_to_remove=[role1] if len(perms1) < len(perms2) else [role2],
                            confidence_score=overlap,
                            impact_score=0.4,
                            risk_impact=-0.1,  # Reduces risk slightly
                            evidence=[
                                {"type": "overlap_analysis", "overlap_pct": overlap * 100}
                            ],
                            priority=50
                        )
                        recommendations.append(rec)

        return recommendations

    def _generate_unused_access_recommendations(self, profile: UserProfile) -> List[Recommendation]:
        """Recommend removal of unused access"""
        recommendations = []

        if not profile.unused_permissions:
            return recommendations

        # Group unused permissions by potential role
        role_unused = defaultdict(list)
        for perm in profile.unused_permissions:
            for role, perms in self.role_permissions.items():
                if perm in perms:
                    role_unused[role].append(perm)

        # If entire role is unused, recommend removal
        for role in profile.roles:
            role_perms = self.role_permissions.get(role, set())
            if role_perms:
                unused_ratio = len(profile.unused_permissions & role_perms) / len(role_perms)

                if unused_ratio > 0.8:  # 80% of role is unused
                    rec = Recommendation(
                        rec_type=RecommendationType.ROLE_REMOVAL,
                        reason=RecommendationReason.UNUSED_ACCESS,
                        user_id=profile.user_id,
                        title=f"Consider Removing Role: {role}",
                        description=f"{unused_ratio * 100:.0f}% of permissions in this role appear unused",
                        action=f"Review and consider removing role {role}",
                        roles_to_remove=[role],
                        permissions_to_remove=[
                            {"permission": p} for p in (profile.unused_permissions & role_perms)
                        ],
                        confidence_score=unused_ratio,
                        impact_score=0.6,
                        risk_impact=-0.2,  # Reduces risk
                        evidence=[
                            {"type": "usage_analysis", "unused_pct": unused_ratio * 100}
                        ],
                        priority=75
                    )
                    recommendations.append(rec)

        # Individual permission removal for high unused count
        if len(profile.unused_permissions) > 5:
            rec = Recommendation(
                rec_type=RecommendationType.PERMISSION_REMOVAL,
                reason=RecommendationReason.UNUSED_ACCESS,
                user_id=profile.user_id,
                title="Remove Unused Permissions",
                description=f"Found {len(profile.unused_permissions)} potentially unused permissions",
                action="Review and remove unused permissions to reduce attack surface",
                permissions_to_remove=[
                    {"permission": p} for p in list(profile.unused_permissions)[:20]
                ],
                confidence_score=0.7,
                impact_score=0.5,
                risk_impact=-0.15,
                evidence=[
                    {"type": "unused_count", "count": len(profile.unused_permissions)}
                ],
                priority=65
            )
            recommendations.append(rec)

        return recommendations

    def _generate_upgrade_recommendations(self, profile: UserProfile) -> List[Recommendation]:
        """Recommend role upgrades based on actual usage"""
        recommendations = []

        # Check if user is using permissions from a higher role
        for current_role in profile.roles:
            # Look for upgrade paths
            upgrade_map = {
                "Z_FIN_ANALYST": "Z_FIN_MANAGER",
                "Z_PROC_BUYER": "Z_PROC_MANAGER",
                "Z_HR_SPECIALIST": "Z_HR_MANAGER",
            }

            if current_role in upgrade_map:
                upgraded_role = upgrade_map[current_role]
                upgraded_perms = self.role_permissions.get(upgraded_role, set())
                current_perms = self.role_permissions.get(current_role, set())

                # Additional perms in upgraded role
                additional_perms = upgraded_perms - current_perms

                # Check if user already has some additional perms
                already_has = additional_perms & profile.permissions

                if len(already_has) >= len(additional_perms) * 0.5:
                    rec = Recommendation(
                        rec_type=RecommendationType.ROLE_UPGRADE,
                        reason=RecommendationReason.ROLE_FIT,
                        user_id=profile.user_id,
                        title=f"Consider Upgrade: {current_role} → {upgraded_role}",
                        description=f"You already have {len(already_has)} of {len(additional_perms)} additional permissions in the upgraded role",
                        action=f"Request upgrade from {current_role} to {upgraded_role} for better role alignment",
                        recommended_roles=[upgraded_role],
                        roles_to_remove=[current_role],
                        confidence_score=len(already_has) / len(additional_perms) if additional_perms else 0,
                        impact_score=0.4,
                        evidence=[
                            {
                                "type": "role_fit",
                                "current_role": current_role,
                                "upgraded_role": upgraded_role,
                                "additional_perms_held": len(already_has)
                            }
                        ],
                        priority=55
                    )
                    recommendations.append(rec)

        return recommendations

    def _generate_risk_recommendations(self, profile: UserProfile) -> List[Recommendation]:
        """Generate risk-based recommendations"""
        recommendations = []

        # Check for potentially risky access combinations
        risky_combos = [
            ({"FB01", "FB02"}, {"XK01", "FK01"}, "Vendor creation and payment posting"),
            ({"ME21N", "ME22N"}, {"MIGO", "MB01"}, "PO creation and goods receipt"),
            ({"PA30"}, {"PC00_M99_CALC"}, "HR maintenance and payroll processing"),
        ]

        for set1, set2, description in risky_combos:
            if (set1 & profile.permissions) and (set2 & profile.permissions):
                rec = Recommendation(
                    rec_type=RecommendationType.ACCESS_REVIEW,
                    reason=RecommendationReason.RISK_REDUCTION,
                    user_id=profile.user_id,
                    title="Potential SoD Risk Detected",
                    description=f"Your access includes: {description}",
                    action="Request review to ensure proper segregation or documented exception",
                    permissions_to_remove=[
                        {"permission": p, "reason": "Part of risky combination"}
                        for p in (set1 | set2) & profile.permissions
                    ],
                    confidence_score=0.8,
                    impact_score=0.7,
                    risk_impact=0.3,  # Current access has risk
                    evidence=[
                        {
                            "type": "sod_risk",
                            "description": description,
                            "permissions": list((set1 | set2) & profile.permissions)
                        }
                    ],
                    priority=85
                )
                recommendations.append(rec)

        return recommendations

    def get_recommendation(self, rec_id: str) -> Optional[Recommendation]:
        """Get a recommendation by ID"""
        return self.recommendations.get(rec_id)

    def accept_recommendation(self, rec_id: str, actioned_by: str) -> Recommendation:
        """Mark a recommendation as accepted"""
        rec = self.recommendations.get(rec_id)
        if not rec:
            raise ValueError(f"Recommendation {rec_id} not found")

        rec.status = "accepted"
        rec.actioned_by = actioned_by
        rec.actioned_at = datetime.now()
        return rec

    def reject_recommendation(self, rec_id: str, actioned_by: str, reason: str) -> Recommendation:
        """Mark a recommendation as rejected"""
        rec = self.recommendations.get(rec_id)
        if not rec:
            raise ValueError(f"Recommendation {rec_id} not found")

        rec.status = "rejected"
        rec.actioned_by = actioned_by
        rec.actioned_at = datetime.now()
        rec.rejection_reason = reason
        return rec

    def get_recommendations(
        self,
        user_id: str = None,
        rec_type: RecommendationType = None,
        status: str = None,
        min_confidence: float = None,
        limit: int = 50
    ) -> List[Recommendation]:
        """Get recommendations with filters"""
        results = []

        for rec in sorted(self.recommendations.values(), key=lambda r: r.priority, reverse=True):
            if user_id and rec.user_id != user_id:
                continue
            if rec_type and rec.rec_type != rec_type:
                continue
            if status and rec.status != status:
                continue
            if min_confidence and rec.confidence_score < min_confidence:
                continue

            results.append(rec)
            if len(results) >= limit:
                break

        return results

    def get_statistics(self) -> Dict:
        """Get recommendation statistics"""
        all_recs = list(self.recommendations.values())

        by_type = defaultdict(int)
        by_status = defaultdict(int)

        for rec in all_recs:
            by_type[rec.rec_type.value] += 1
            by_status[rec.status] += 1

        acceptance_rate = by_status.get("accepted", 0) / len(all_recs) if all_recs else 0

        return {
            "total_recommendations": len(all_recs),
            "by_type": dict(by_type),
            "by_status": dict(by_status),
            "acceptance_rate": round(acceptance_rate, 2),
            "avg_confidence": round(
                sum(r.confidence_score for r in all_recs) / len(all_recs), 2
            ) if all_recs else 0,
            "users_with_recommendations": len(set(r.user_id for r in all_recs))
        }
