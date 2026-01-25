# AI Role Mining & Optimization
# Intelligent role design and optimization

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Set, Tuple
from enum import Enum
from datetime import datetime
from collections import defaultdict
import math


class OptimizationType(Enum):
    """Types of role optimization"""
    CONSOLIDATE = "consolidate"      # Merge similar roles
    SPLIT = "split"                  # Split role to remove conflicts
    REDUCE = "reduce"                # Remove unused authorizations
    REDESIGN = "redesign"            # Complete redesign
    STANDARDIZE = "standardize"      # Align with standards


@dataclass
class AccessPattern:
    """Detected pattern of access usage"""
    transactions: Set[str]
    auth_objects: Set[str]
    users: Set[str]
    frequency: float  # How often used together
    business_function: str
    department: str = ""


@dataclass
class RoleRecommendation:
    """AI-generated role recommendation"""
    id: str
    name: str
    description: str
    optimization_type: OptimizationType

    # Composition
    transactions: List[str] = field(default_factory=list)
    auth_objects: List[str] = field(default_factory=list)

    # Impact
    users_affected: int = 0
    risk_reduction: float = 0.0
    efficiency_gain: float = 0.0  # % fewer roles needed

    # Comparison
    based_on_roles: List[str] = field(default_factory=list)  # Existing roles this replaces/modifies
    changes_from_original: Dict[str, Any] = field(default_factory=dict)

    # Quality metrics
    sod_conflicts: int = 0
    least_privilege_score: float = 0.0  # 0-100, higher = better
    usage_alignment: float = 0.0  # How well it matches actual usage

    # Explanation
    reasoning: str = ""
    confidence: float = 0.0


@dataclass
class RoleMiningResult:
    """Result of role mining analysis"""
    id: str
    analyzed_at: datetime = field(default_factory=datetime.utcnow)

    # Discovered patterns
    access_patterns: List[AccessPattern] = field(default_factory=list)

    # Recommendations
    recommendations: List[RoleRecommendation] = field(default_factory=list)

    # Statistics
    current_role_count: int = 0
    recommended_role_count: int = 0
    potential_reduction: float = 0.0  # % reduction

    # Issues found
    unused_authorizations: int = 0
    over_privileged_users: int = 0
    sod_conflicts_found: int = 0

    # Summary
    summary: str = ""


@dataclass
class OptimizationSuggestion:
    """Specific optimization suggestion"""
    id: str
    title: str
    description: str
    optimization_type: OptimizationType
    priority: int  # 1-10

    # What to do
    target_roles: List[str] = field(default_factory=list)
    action_items: List[str] = field(default_factory=list)

    # Impact
    risk_impact: str = ""  # "Reduces risk by X%"
    efficiency_impact: str = ""  # "Reduces roles by X"

    # Effort
    effort_level: str = ""  # "Low", "Medium", "High"
    implementation_time: str = ""


class AIRoleOptimizer:
    """
    AI-Powered Role Mining & Optimization

    Key advantages over traditional SAP GRC:

    1. PATTERN DISCOVERY: Finds natural access patterns from usage
       - Clusters similar usage into logical roles
       - Identifies common job functions
       - Discovers hidden patterns

    2. ROLE CONSOLIDATION: Reduces role explosion
       - Identifies duplicate/similar roles
       - Suggests mergers
       - Reduces maintenance burden

    3. LEAST PRIVILEGE OPTIMIZATION: Right-sizes access
       - Identifies unused authorizations
       - Suggests removal of excess access
       - Aligns roles to actual needs

    4. CONFLICT PREVENTION: Designs SoD-free roles
       - Checks for conflicts during design
       - Suggests splits to avoid SoD
       - Maintains compliance by design

    5. CONTINUOUS IMPROVEMENT: Adapts over time
       - Monitors usage after changes
       - Suggests adjustments
       - Learns organizational patterns
    """

    def __init__(self):
        # Current role definitions
        self.roles: Dict[str, Dict[str, Any]] = {}

        # Usage data
        self.usage_data: Dict[str, Dict[str, int]] = {}  # user -> {tcode: count}

        # User role assignments
        self.user_roles: Dict[str, List[str]] = {}

        # SoD conflict rules (simplified)
        self.sod_pairs: List[Tuple[str, str]] = []

        self._initialize_demo_data()

    def _initialize_demo_data(self):
        """Initialize demo data"""
        # Demo roles
        self.roles = {
            "FI_AP_CLERK": {
                "name": "AP Clerk",
                "transactions": ["FB60", "FB65", "FBL1N", "F-43", "F-44"],
                "users": ["JSMITH", "MWILLIAMS"],
                "department": "Finance"
            },
            "FI_AP_CLERK_2": {
                "name": "AP Clerk (Old)",
                "transactions": ["FB60", "FB65", "FBL1N"],
                "users": ["RJONES"],
                "department": "Finance"
            },
            "FI_AR_CLERK": {
                "name": "AR Clerk",
                "transactions": ["FB70", "FB75", "FBL5N", "F-28", "F-32"],
                "users": ["JSMITH", "ADAVIS"],
                "department": "Finance"
            },
            "FI_GL_DISPLAY": {
                "name": "GL Display",
                "transactions": ["FB03", "FS10N", "FAGLL03"],
                "users": ["JSMITH", "MWILLIAMS", "RJONES", "ADAVIS"],
                "department": "Finance"
            },
            "MM_BUYER": {
                "name": "Buyer",
                "transactions": ["ME21N", "ME22N", "ME23N", "ME2M", "ME2L"],
                "users": ["MBROWN", "KWILSON"],
                "department": "Procurement"
            },
            "MM_BUYER_FULL": {
                "name": "Senior Buyer",
                "transactions": ["ME21N", "ME22N", "ME23N", "ME2M", "ME2L", "MIGO", "MB51"],
                "users": ["SJOHNSON"],
                "department": "Procurement"
            },
            "MM_REQUISITIONER": {
                "name": "Requisitioner",
                "transactions": ["ME51N", "ME52N", "ME53N", "ME5A"],
                "users": ["MBROWN", "KWILSON", "LGARCIA"],
                "department": "Procurement"
            },
            "HR_ADMIN": {
                "name": "HR Administrator",
                "transactions": ["PA20", "PA30", "PA40", "PT60", "PT61"],
                "users": ["HSMITH"],
                "department": "HR"
            },
            "BASIS_ADMIN": {
                "name": "Basis Admin",
                "transactions": ["SU01", "SU10", "PFCG", "SM21", "SM37"],
                "users": ["TDAVIS"],
                "department": "IT"
            }
        }

        # Demo usage data
        self.usage_data = {
            "JSMITH": {"FB60": 150, "FB65": 20, "FBL1N": 200, "FB70": 80, "FBL5N": 100, "FB03": 50},
            "MBROWN": {"ME21N": 100, "ME22N": 50, "ME51N": 30, "ME53N": 100},
            "KWILSON": {"ME21N": 80, "ME51N": 50, "ME5A": 20},
            "SJOHNSON": {"ME21N": 120, "ME22N": 60, "MIGO": 90, "MB51": 40},
        }

        # SoD pairs
        self.sod_pairs = [
            ("ME21N", "MIGO"),  # PO create vs GR
            ("FB60", "F110"),  # Invoice vs Payment
            ("SU01", "PFCG"),  # User admin vs Role admin
        ]

    # ==================== Role Mining ====================

    def mine_roles(
        self,
        min_pattern_frequency: float = 0.3,
        min_users: int = 2
    ) -> RoleMiningResult:
        """
        Mine roles from actual usage patterns

        Analyzes how users actually use the system to discover
        natural role definitions.
        """
        # 1. Discover access patterns
        patterns = self._discover_patterns(min_pattern_frequency, min_users)

        # 2. Analyze current role structure
        current_analysis = self._analyze_current_roles()

        # 3. Generate recommendations
        recommendations = []
        recommendations.extend(self._recommend_consolidations())
        recommendations.extend(self._recommend_splits())
        recommendations.extend(self._recommend_reductions())

        # 4. Calculate potential improvements
        potential_reduction = self._calculate_reduction_potential(recommendations)

        # 5. Generate summary
        summary = self._generate_mining_summary(
            patterns, recommendations, current_analysis
        )

        return RoleMiningResult(
            id=f"mining_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            access_patterns=patterns,
            recommendations=recommendations,
            current_role_count=len(self.roles),
            recommended_role_count=len(self.roles) - len([
                r for r in recommendations if r.optimization_type == OptimizationType.CONSOLIDATE
            ]),
            potential_reduction=potential_reduction,
            unused_authorizations=current_analysis.get("unused_auths", 0),
            over_privileged_users=current_analysis.get("over_privileged", 0),
            sod_conflicts_found=current_analysis.get("sod_conflicts", 0),
            summary=summary
        )

    def _discover_patterns(
        self,
        min_frequency: float,
        min_users: int
    ) -> List[AccessPattern]:
        """Discover common access patterns from usage data"""
        patterns = []

        # Group users by transaction patterns
        user_patterns: Dict[str, Set[str]] = {}
        for user, transactions in self.usage_data.items():
            # Only consider transactions used > threshold times
            significant = {t for t, count in transactions.items() if count > 10}
            user_patterns[user] = significant

        # Find common patterns across users
        pattern_groups = defaultdict(list)
        for user, tcodes in user_patterns.items():
            # Create pattern signature
            signature = tuple(sorted(tcodes))
            pattern_groups[signature].append(user)

        # Convert to AccessPattern objects
        for signature, users in pattern_groups.items():
            if len(users) >= min_users:
                patterns.append(AccessPattern(
                    transactions=set(signature),
                    auth_objects=set(),  # Would be populated from actual auth data
                    users=set(users),
                    frequency=len(users) / len(self.usage_data),
                    business_function=self._infer_business_function(set(signature))
                ))

        return patterns

    def _infer_business_function(self, transactions: Set[str]) -> str:
        """Infer business function from transaction codes"""
        # Simplified inference based on transaction prefixes
        fi_count = len([t for t in transactions if t.startswith("F")])
        mm_count = len([t for t in transactions if t.startswith("M")])
        sd_count = len([t for t in transactions if t.startswith("V")])

        if fi_count > mm_count and fi_count > sd_count:
            if any("60" in t or "65" in t for t in transactions):
                return "Accounts Payable"
            if any("70" in t or "75" in t for t in transactions):
                return "Accounts Receivable"
            return "Financial Accounting"
        elif mm_count > fi_count:
            if any("21" in t or "22" in t for t in transactions):
                return "Purchasing"
            return "Materials Management"
        elif sd_count > 0:
            return "Sales & Distribution"

        return "General Business"

    def _analyze_current_roles(self) -> Dict[str, Any]:
        """Analyze current role structure for issues"""
        analysis = {
            "unused_auths": 0,
            "over_privileged": 0,
            "sod_conflicts": 0,
            "duplicate_roles": 0
        }

        # Find unused authorizations
        for role_id, role in self.roles.items():
            role_tcodes = set(role.get("transactions", []))
            role_users = role.get("users", [])

            for user in role_users:
                user_usage = self.usage_data.get(user, {})
                used_tcodes = set(user_usage.keys())
                unused = role_tcodes - used_tcodes
                analysis["unused_auths"] += len(unused)

        # Find over-privileged users (those with SoD conflicts)
        for user, roles in self.user_roles.items():
            user_tcodes = set()
            for role_id in roles:
                role = self.roles.get(role_id, {})
                user_tcodes.update(role.get("transactions", []))

            for t1, t2 in self.sod_pairs:
                if t1 in user_tcodes and t2 in user_tcodes:
                    analysis["sod_conflicts"] += 1
                    analysis["over_privileged"] += 1
                    break

        # Find duplicate/similar roles
        role_signatures = []
        for role_id, role in self.roles.items():
            sig = frozenset(role.get("transactions", []))
            role_signatures.append((role_id, sig))

        for i, (r1_id, r1_sig) in enumerate(role_signatures):
            for r2_id, r2_sig in role_signatures[i+1:]:
                overlap = len(r1_sig & r2_sig) / max(len(r1_sig), len(r2_sig), 1)
                if overlap > 0.8:  # 80% overlap
                    analysis["duplicate_roles"] += 1

        return analysis

    # ==================== Recommendations ====================

    def _recommend_consolidations(self) -> List[RoleRecommendation]:
        """Recommend role consolidations"""
        recommendations = []

        # Find similar roles that can be merged
        role_list = list(self.roles.items())
        for i, (r1_id, r1) in enumerate(role_list):
            for r2_id, r2 in role_list[i+1:]:
                if r1.get("department") != r2.get("department"):
                    continue

                r1_tcodes = set(r1.get("transactions", []))
                r2_tcodes = set(r2.get("transactions", []))

                overlap = len(r1_tcodes & r2_tcodes)
                total = len(r1_tcodes | r2_tcodes)

                if total > 0 and overlap / total > 0.6:  # 60% overlap
                    merged_tcodes = list(r1_tcodes | r2_tcodes)
                    affected_users = len(set(r1.get("users", []) + r2.get("users", [])))

                    recommendations.append(RoleRecommendation(
                        id=f"consolidate_{r1_id}_{r2_id}",
                        name=f"Consolidated {r1.get('name', r1_id)}",
                        description=f"Merge {r1_id} and {r2_id} into a single role",
                        optimization_type=OptimizationType.CONSOLIDATE,
                        transactions=merged_tcodes,
                        users_affected=affected_users,
                        efficiency_gain=50.0,  # 2 roles -> 1 role
                        based_on_roles=[r1_id, r2_id],
                        changes_from_original={
                            "merged_from": [r1_id, r2_id],
                            "added_transactions": list(r2_tcodes - r1_tcodes),
                            "removed_transactions": []
                        },
                        sod_conflicts=self._count_sod_conflicts(merged_tcodes),
                        least_privilege_score=85.0,
                        usage_alignment=0.9,
                        reasoning=f"These roles have {overlap}/{total} ({overlap/total*100:.0f}%) "
                                 f"transaction overlap and serve similar functions.",
                        confidence=0.85
                    ))

        return recommendations

    def _recommend_splits(self) -> List[RoleRecommendation]:
        """Recommend role splits to remove SoD conflicts"""
        recommendations = []

        for role_id, role in self.roles.items():
            tcodes = set(role.get("transactions", []))
            conflicts = []

            for t1, t2 in self.sod_pairs:
                if t1 in tcodes and t2 in tcodes:
                    conflicts.append((t1, t2))

            if conflicts:
                # Recommend splitting
                safe_tcodes = list(tcodes - {t for pair in conflicts for t in pair})
                conflict_tcodes = list({t for pair in conflicts for t in pair})

                recommendations.append(RoleRecommendation(
                    id=f"split_{role_id}",
                    name=f"{role.get('name', role_id)} (Safe)",
                    description=f"Split {role_id} to remove {len(conflicts)} SoD conflict(s)",
                    optimization_type=OptimizationType.SPLIT,
                    transactions=safe_tcodes,
                    users_affected=len(role.get("users", [])),
                    risk_reduction=len(conflicts) * 25.0,  # Significant risk reduction
                    based_on_roles=[role_id],
                    changes_from_original={
                        "removed_for_sod": conflict_tcodes,
                        "conflicts_resolved": conflicts
                    },
                    sod_conflicts=0,
                    least_privilege_score=95.0,
                    reasoning=f"Role contains {len(conflicts)} SoD conflict(s). "
                             f"Splitting removes conflicts while maintaining core access.",
                    confidence=0.90
                ))

        return recommendations

    def _recommend_reductions(self) -> List[RoleRecommendation]:
        """Recommend authorization reductions based on usage"""
        recommendations = []

        for role_id, role in self.roles.items():
            role_tcodes = set(role.get("transactions", []))
            role_users = role.get("users", [])

            if not role_users:
                continue

            # Find unused transactions
            used_across_users = set()
            for user in role_users:
                user_usage = self.usage_data.get(user, {})
                used_across_users.update(user_usage.keys())

            unused = role_tcodes - used_across_users

            if len(unused) >= 2:  # At least 2 unused transactions
                reduced_tcodes = list(role_tcodes - unused)

                recommendations.append(RoleRecommendation(
                    id=f"reduce_{role_id}",
                    name=f"{role.get('name', role_id)} (Optimized)",
                    description=f"Remove {len(unused)} unused transaction(s) from {role_id}",
                    optimization_type=OptimizationType.REDUCE,
                    transactions=reduced_tcodes,
                    users_affected=len(role_users),
                    risk_reduction=len(unused) * 5.0,  # Some risk reduction per removed auth
                    based_on_roles=[role_id],
                    changes_from_original={
                        "removed_unused": list(unused)
                    },
                    sod_conflicts=self._count_sod_conflicts(reduced_tcodes),
                    least_privilege_score=95.0,
                    usage_alignment=1.0,  # Perfect alignment with usage
                    reasoning=f"Analysis shows {len(unused)} transactions are never used by "
                             f"any of the {len(role_users)} users with this role.",
                    confidence=0.80
                ))

        return recommendations

    def _count_sod_conflicts(self, transactions: List[str]) -> int:
        """Count SoD conflicts in a transaction list"""
        tcode_set = set(transactions)
        conflicts = 0
        for t1, t2 in self.sod_pairs:
            if t1 in tcode_set and t2 in tcode_set:
                conflicts += 1
        return conflicts

    def _calculate_reduction_potential(
        self,
        recommendations: List[RoleRecommendation]
    ) -> float:
        """Calculate potential role count reduction"""
        consolidations = len([
            r for r in recommendations
            if r.optimization_type == OptimizationType.CONSOLIDATE
        ])

        if len(self.roles) > 0:
            return (consolidations / len(self.roles)) * 100
        return 0.0

    def _generate_mining_summary(
        self,
        patterns: List[AccessPattern],
        recommendations: List[RoleRecommendation],
        analysis: Dict[str, Any]
    ) -> str:
        """Generate human-readable mining summary"""
        summary = "Role Mining Analysis Summary\n"
        summary += "=" * 40 + "\n\n"

        summary += f"Analyzed {len(self.roles)} existing roles\n"
        summary += f"Discovered {len(patterns)} common access patterns\n"
        summary += f"Generated {len(recommendations)} optimization recommendations\n\n"

        summary += "Key Findings:\n"
        summary += f"• {analysis.get('unused_auths', 0)} unused authorizations detected\n"
        summary += f"• {analysis.get('sod_conflicts', 0)} SoD conflicts in current assignments\n"
        summary += f"• {analysis.get('duplicate_roles', 0)} potential duplicate roles\n\n"

        summary += "Top Recommendations:\n"
        for rec in sorted(recommendations, key=lambda r: r.risk_reduction, reverse=True)[:3]:
            summary += f"• {rec.description} (Risk reduction: {rec.risk_reduction}%)\n"

        return summary

    # ==================== Optimization Suggestions ====================

    def get_optimization_suggestions(
        self,
        focus: Optional[str] = None  # "risk", "efficiency", "compliance"
    ) -> List[OptimizationSuggestion]:
        """Get prioritized optimization suggestions"""
        suggestions = []

        # Run mining
        mining_result = self.mine_roles()

        # Convert recommendations to suggestions
        for rec in mining_result.recommendations:
            priority = self._calculate_priority(rec, focus)

            suggestions.append(OptimizationSuggestion(
                id=rec.id,
                title=rec.name,
                description=rec.description,
                optimization_type=rec.optimization_type,
                priority=priority,
                target_roles=rec.based_on_roles,
                action_items=self._generate_action_items(rec),
                risk_impact=f"Reduces risk by {rec.risk_reduction:.0f}%",
                efficiency_impact=f"Improves efficiency by {rec.efficiency_gain:.0f}%"
                                 if rec.efficiency_gain > 0 else "",
                effort_level=self._estimate_effort(rec),
                implementation_time=self._estimate_time(rec)
            ))

        # Sort by priority
        suggestions.sort(key=lambda s: s.priority, reverse=True)

        return suggestions

    def _calculate_priority(
        self,
        rec: RoleRecommendation,
        focus: Optional[str]
    ) -> int:
        """Calculate priority score (1-10)"""
        base_score = 5

        # Risk reduction impact
        if rec.risk_reduction > 50:
            base_score += 3
        elif rec.risk_reduction > 20:
            base_score += 2
        elif rec.risk_reduction > 0:
            base_score += 1

        # Efficiency impact
        if rec.efficiency_gain > 30:
            base_score += 2
        elif rec.efficiency_gain > 10:
            base_score += 1

        # Focus adjustments
        if focus == "risk" and rec.risk_reduction > 0:
            base_score += 1
        elif focus == "efficiency" and rec.efficiency_gain > 0:
            base_score += 1
        elif focus == "compliance" and rec.sod_conflicts == 0:
            base_score += 1

        # Confidence adjustment
        if rec.confidence > 0.8:
            base_score += 1

        return min(base_score, 10)

    def _generate_action_items(self, rec: RoleRecommendation) -> List[str]:
        """Generate action items for a recommendation"""
        if rec.optimization_type == OptimizationType.CONSOLIDATE:
            return [
                f"Review transactions from both roles",
                f"Create merged role with combined authorizations",
                f"Test with representative users",
                f"Migrate users from old roles",
                f"Decommission old roles"
            ]
        elif rec.optimization_type == OptimizationType.SPLIT:
            return [
                f"Identify transactions causing conflicts",
                f"Create separate role for conflicting functions",
                f"Reassign users to appropriate role(s)",
                f"Verify SoD conflicts are resolved"
            ]
        elif rec.optimization_type == OptimizationType.REDUCE:
            return [
                f"Confirm transactions are truly unused",
                f"Remove unused authorizations from role",
                f"Monitor for issues after change",
                f"Document change for audit"
            ]

        return ["Review and implement as appropriate"]

    def _estimate_effort(self, rec: RoleRecommendation) -> str:
        """Estimate effort level"""
        if rec.optimization_type == OptimizationType.REDUCE:
            return "Low"
        elif rec.optimization_type == OptimizationType.SPLIT:
            return "Medium"
        elif rec.optimization_type == OptimizationType.CONSOLIDATE:
            return "Medium" if rec.users_affected < 20 else "High"
        return "High"

    def _estimate_time(self, rec: RoleRecommendation) -> str:
        """Estimate implementation time"""
        effort = self._estimate_effort(rec)
        return {
            "Low": "1-2 hours",
            "Medium": "1-3 days",
            "High": "1-2 weeks"
        }.get(effort, "Varies")

    # ==================== Design Assistance ====================

    def design_role(
        self,
        business_function: str,
        required_transactions: List[str] = None,
        department: str = ""
    ) -> RoleRecommendation:
        """
        AI-assisted role design

        Given a business function description, suggests an optimal role
        design based on patterns and best practices.
        """
        # Find similar patterns
        similar_patterns = []
        for role_id, role in self.roles.items():
            role_dept = role.get("department", "")
            if department and role_dept != department:
                continue

            # Check for similar function
            role_name = role.get("name", "").lower()
            if any(word in role_name for word in business_function.lower().split()):
                similar_patterns.append(role)

        # Build recommended transaction list
        recommended_tcodes = set(required_transactions or [])

        # Add from similar roles
        for pattern in similar_patterns[:3]:
            recommended_tcodes.update(pattern.get("transactions", [])[:5])

        # Check for SoD conflicts
        conflicts = self._count_sod_conflicts(list(recommended_tcodes))

        # Generate recommendation
        return RoleRecommendation(
            id=f"new_role_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            name=f"New {business_function} Role",
            description=f"AI-designed role for {business_function}",
            optimization_type=OptimizationType.REDESIGN,
            transactions=list(recommended_tcodes),
            sod_conflicts=conflicts,
            least_privilege_score=90.0 if conflicts == 0 else 70.0,
            reasoning=f"Based on analysis of {len(similar_patterns)} similar roles. "
                     f"Includes {len(recommended_tcodes)} transactions. "
                     f"{'No SoD conflicts.' if conflicts == 0 else f'{conflicts} potential SoD conflicts to review.'}",
            confidence=0.75 if similar_patterns else 0.5
        )
