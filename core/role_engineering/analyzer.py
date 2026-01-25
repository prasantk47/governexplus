"""
Role Analyzer - Role Comparison, Optimization, and Gap Analysis

Provides tools for analyzing roles, finding gaps, optimizing
role structures, and detecting conflicts.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Any, Tuple
from datetime import datetime
from enum import Enum
import uuid


class ConflictType(Enum):
    """Types of role conflicts"""
    SOD_VIOLATION = "sod_violation"
    DUPLICATE_PERMISSION = "duplicate_permission"
    OVERLAPPING_ROLES = "overlapping_roles"
    CIRCULAR_REFERENCE = "circular_reference"
    ORPHANED_PERMISSION = "orphaned_permission"


class GapType(Enum):
    """Types of permission gaps"""
    MISSING_TRANSACTION = "missing_transaction"
    MISSING_AUTH_OBJECT = "missing_auth_object"
    INSUFFICIENT_ORG_LEVEL = "insufficient_org_level"
    MISSING_ACTIVITY = "missing_activity"


@dataclass
class RoleConflict:
    """A detected conflict between roles or permissions"""
    conflict_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    conflict_type: ConflictType = ConflictType.SOD_VIOLATION
    severity: str = "high"
    role_ids: List[str] = field(default_factory=list)
    description: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    remediation: str = ""
    detected_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict:
        return {
            "conflict_id": self.conflict_id,
            "conflict_type": self.conflict_type.value,
            "severity": self.severity,
            "role_ids": self.role_ids,
            "description": self.description,
            "details": self.details,
            "remediation": self.remediation,
            "detected_at": self.detected_at.isoformat()
        }


@dataclass
class PermissionGap:
    """A detected gap in permissions"""
    gap_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    gap_type: GapType = GapType.MISSING_TRANSACTION
    role_id: str = ""
    user_id: str = ""
    description: str = ""
    required: Dict[str, Any] = field(default_factory=dict)
    current: Dict[str, Any] = field(default_factory=dict)
    recommendation: str = ""

    def to_dict(self) -> Dict:
        return {
            "gap_id": self.gap_id,
            "gap_type": self.gap_type.value,
            "role_id": self.role_id,
            "user_id": self.user_id,
            "description": self.description,
            "required": self.required,
            "current": self.current,
            "recommendation": self.recommendation
        }


@dataclass
class RoleComparison:
    """Result of comparing two roles"""
    comparison_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    role_a_id: str = ""
    role_b_id: str = ""
    timestamp: datetime = field(default_factory=datetime.now)

    # Permission differences
    permissions_only_in_a: List[Dict] = field(default_factory=list)
    permissions_only_in_b: List[Dict] = field(default_factory=list)
    permissions_in_both: List[Dict] = field(default_factory=list)

    # Transaction differences
    transactions_only_in_a: List[str] = field(default_factory=list)
    transactions_only_in_b: List[str] = field(default_factory=list)
    transactions_in_both: List[str] = field(default_factory=list)

    # Similarity metrics
    permission_similarity: float = 0.0
    transaction_similarity: float = 0.0
    overall_similarity: float = 0.0

    # Conflicts
    combined_sod_conflicts: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "comparison_id": self.comparison_id,
            "role_a_id": self.role_a_id,
            "role_b_id": self.role_b_id,
            "timestamp": self.timestamp.isoformat(),
            "permissions_only_in_a": self.permissions_only_in_a,
            "permissions_only_in_b": self.permissions_only_in_b,
            "permissions_in_both": self.permissions_in_both,
            "transactions_only_in_a": self.transactions_only_in_a,
            "transactions_only_in_b": self.transactions_only_in_b,
            "transactions_in_both": self.transactions_in_both,
            "permission_similarity": round(self.permission_similarity, 2),
            "transaction_similarity": round(self.transaction_similarity, 2),
            "overall_similarity": round(self.overall_similarity, 2),
            "combined_sod_conflicts": self.combined_sod_conflicts
        }


@dataclass
class RoleOptimization:
    """Optimization recommendation for roles"""
    optimization_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    optimization_type: str = ""  # merge, split, consolidate, cleanup
    affected_roles: List[str] = field(default_factory=list)
    description: str = ""
    impact: str = ""
    savings_estimate: str = ""
    recommendations: List[Dict] = field(default_factory=list)
    risk_assessment: str = ""
    implementation_steps: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "optimization_id": self.optimization_id,
            "optimization_type": self.optimization_type,
            "affected_roles": self.affected_roles,
            "description": self.description,
            "impact": self.impact,
            "savings_estimate": self.savings_estimate,
            "recommendations": self.recommendations,
            "risk_assessment": self.risk_assessment,
            "implementation_steps": self.implementation_steps
        }


class RoleAnalyzer:
    """
    Role Analyzer - Comprehensive role analysis tool.

    Provides:
    - Role comparison
    - Permission gap analysis
    - Role optimization recommendations
    - Conflict detection
    - Usage analysis
    """

    # SoD conflict definitions
    SOD_CONFLICTS = [
        {
            "id": "SOD001",
            "name": "Vendor Master vs Payment",
            "set_a": ["XK01", "FK01", "XK02", "FK02"],
            "set_b": ["F110", "F-53", "FBV0"],
            "severity": "critical",
            "description": "Creating/modifying vendors and processing payments"
        },
        {
            "id": "SOD002",
            "name": "Purchase Order vs Goods Receipt",
            "set_a": ["ME21N", "ME22N", "ME29N"],
            "set_b": ["MIGO", "MB01", "MB1A"],
            "severity": "high",
            "description": "Creating POs and receiving goods"
        },
        {
            "id": "SOD003",
            "name": "Purchase Order vs Invoice",
            "set_a": ["ME21N", "ME22N", "ME29N"],
            "set_b": ["MIRO", "MIR7"],
            "severity": "high",
            "description": "Creating POs and posting invoices"
        },
        {
            "id": "SOD004",
            "name": "HR Master vs Payroll",
            "set_a": ["PA30", "PA40"],
            "set_b": ["PU30", "PC00_M99_CALC"],
            "severity": "critical",
            "description": "Maintaining HR data and running payroll"
        },
        {
            "id": "SOD005",
            "name": "User Administration vs Role Administration",
            "set_a": ["SU01", "SU10"],
            "set_b": ["PFCG", "SU24"],
            "severity": "critical",
            "description": "Managing users and managing roles"
        },
        {
            "id": "SOD006",
            "name": "Journal Entry vs Approval",
            "set_a": ["FB01", "FB50", "F-02"],
            "set_b": ["FBV2", "FBV0"],
            "severity": "high",
            "description": "Posting journal entries and approving them"
        },
        {
            "id": "SOD007",
            "name": "Customer Master vs Credit",
            "set_a": ["XD01", "XD02", "FD01", "FD02"],
            "set_b": ["FD32", "UKM_MY_CUSTOMER"],
            "severity": "medium",
            "description": "Creating customers and managing credit limits"
        },
        {
            "id": "SOD008",
            "name": "Sales Order vs Delivery",
            "set_a": ["VA01", "VA02"],
            "set_b": ["VL01N", "VL02N"],
            "severity": "medium",
            "description": "Creating sales orders and creating deliveries"
        }
    ]

    def __init__(self, role_designer=None):
        self.role_designer = role_designer
        self.comparison_history: List[RoleComparison] = []
        self.detected_conflicts: List[RoleConflict] = []
        self.detected_gaps: List[PermissionGap] = []
        self.optimization_recommendations: List[RoleOptimization] = []

    # =========================================================================
    # Role Comparison
    # =========================================================================

    def compare_roles(
        self,
        role_a_id: str,
        role_b_id: str,
        role_a_data: Dict = None,
        role_b_data: Dict = None
    ) -> RoleComparison:
        """
        Compare two roles and identify differences.

        Args:
            role_a_id: First role ID
            role_b_id: Second role ID
            role_a_data: Optional role data (if not using role_designer)
            role_b_data: Optional role data (if not using role_designer)

        Returns:
            RoleComparison with detailed differences
        """
        # Get role data
        if role_a_data:
            perms_a = {p.get("permission_id", str(i)): p
                      for i, p in enumerate(role_a_data.get("permissions", []))}
            tcodes_a = set(role_a_data.get("transaction_codes", []))
        elif self.role_designer and role_a_id in self.role_designer.roles:
            role_a = self.role_designer.roles[role_a_id]
            perms_a = {p.permission_id: p.to_dict() for p in role_a.permissions}
            tcodes_a = set(role_a.transaction_codes)
        else:
            raise ValueError(f"Role {role_a_id} not found")

        if role_b_data:
            perms_b = {p.get("permission_id", str(i)): p
                      for i, p in enumerate(role_b_data.get("permissions", []))}
            tcodes_b = set(role_b_data.get("transaction_codes", []))
        elif self.role_designer and role_b_id in self.role_designer.roles:
            role_b = self.role_designer.roles[role_b_id]
            perms_b = {p.permission_id: p.to_dict() for p in role_b.permissions}
            tcodes_b = set(role_b.transaction_codes)
        else:
            raise ValueError(f"Role {role_b_id} not found")

        comparison = RoleComparison(
            role_a_id=role_a_id,
            role_b_id=role_b_id
        )

        # Compare permissions by auth object
        auth_objects_a = {p.get("auth_object"): p for p in perms_a.values()}
        auth_objects_b = {p.get("auth_object"): p for p in perms_b.values()}

        only_in_a = set(auth_objects_a.keys()) - set(auth_objects_b.keys())
        only_in_b = set(auth_objects_b.keys()) - set(auth_objects_a.keys())
        in_both = set(auth_objects_a.keys()) & set(auth_objects_b.keys())

        comparison.permissions_only_in_a = [auth_objects_a[ao] for ao in only_in_a if ao]
        comparison.permissions_only_in_b = [auth_objects_b[ao] for ao in only_in_b if ao]
        comparison.permissions_in_both = [auth_objects_a[ao] for ao in in_both if ao]

        # Compare transactions
        comparison.transactions_only_in_a = list(tcodes_a - tcodes_b)
        comparison.transactions_only_in_b = list(tcodes_b - tcodes_a)
        comparison.transactions_in_both = list(tcodes_a & tcodes_b)

        # Calculate similarity
        total_perms = len(only_in_a) + len(only_in_b) + len(in_both)
        if total_perms > 0:
            comparison.permission_similarity = len(in_both) / total_perms * 100

        total_tcodes = len(tcodes_a | tcodes_b)
        if total_tcodes > 0:
            comparison.transaction_similarity = len(tcodes_a & tcodes_b) / total_tcodes * 100

        comparison.overall_similarity = (
            comparison.permission_similarity * 0.6 +
            comparison.transaction_similarity * 0.4
        )

        # Check combined SoD conflicts
        combined_tcodes = tcodes_a | tcodes_b
        comparison.combined_sod_conflicts = self._check_sod_conflicts(combined_tcodes)

        self.comparison_history.append(comparison)
        return comparison

    def find_similar_roles(
        self,
        role_id: str,
        threshold: float = 70.0
    ) -> List[Dict]:
        """Find roles similar to a given role"""
        if not self.role_designer:
            raise ValueError("Role designer not configured")

        results = []

        for other_id in self.role_designer.roles:
            if other_id == role_id:
                continue

            comparison = self.compare_roles(role_id, other_id)

            if comparison.overall_similarity >= threshold:
                results.append({
                    "role_id": other_id,
                    "name": self.role_designer.roles[other_id].name,
                    "similarity": comparison.overall_similarity,
                    "common_transactions": len(comparison.transactions_in_both),
                    "common_permissions": len(comparison.permissions_in_both)
                })

        results.sort(key=lambda x: x["similarity"], reverse=True)
        return results

    # =========================================================================
    # SoD Conflict Detection
    # =========================================================================

    def _check_sod_conflicts(self, transaction_codes: Set[str]) -> List[str]:
        """Check transaction codes for SoD conflicts"""
        conflicts = []

        for sod in self.SOD_CONFLICTS:
            has_set_a = bool(transaction_codes & set(sod["set_a"]))
            has_set_b = bool(transaction_codes & set(sod["set_b"]))

            if has_set_a and has_set_b:
                conflicts.append(sod["id"])

        return conflicts

    def detect_conflicts(
        self,
        role_ids: List[str] = None
    ) -> List[RoleConflict]:
        """Detect conflicts in roles"""
        if not self.role_designer:
            raise ValueError("Role designer not configured")

        conflicts = []
        roles_to_check = role_ids or list(self.role_designer.roles.keys())

        # Check each role for internal SoD
        for role_id in roles_to_check:
            role = self.role_designer.roles.get(role_id)
            if not role:
                continue

            tcodes = set(role.transaction_codes)

            for sod in self.SOD_CONFLICTS:
                has_set_a = tcodes & set(sod["set_a"])
                has_set_b = tcodes & set(sod["set_b"])

                if has_set_a and has_set_b:
                    conflict = RoleConflict(
                        conflict_type=ConflictType.SOD_VIOLATION,
                        severity=sod["severity"],
                        role_ids=[role_id],
                        description=f"SoD violation: {sod['name']}",
                        details={
                            "sod_rule_id": sod["id"],
                            "conflicting_set_a": list(has_set_a),
                            "conflicting_set_b": list(has_set_b)
                        },
                        remediation=f"Remove either {list(has_set_a)} or {list(has_set_b)} from role"
                    )
                    conflicts.append(conflict)

        # Check for duplicate permissions across roles
        permission_usage = {}  # auth_object -> [role_ids]

        for role_id in roles_to_check:
            role = self.role_designer.roles.get(role_id)
            if not role:
                continue

            for perm in role.permissions:
                key = f"{perm.auth_object}:{perm.field_values}"
                if key not in permission_usage:
                    permission_usage[key] = []
                permission_usage[key].append(role_id)

        for key, role_ids_with_perm in permission_usage.items():
            if len(role_ids_with_perm) > 3:  # Threshold for flagging
                conflict = RoleConflict(
                    conflict_type=ConflictType.DUPLICATE_PERMISSION,
                    severity="low",
                    role_ids=role_ids_with_perm,
                    description=f"Same permission in {len(role_ids_with_perm)} roles",
                    details={"permission_key": key},
                    remediation="Consider consolidating into a shared role"
                )
                conflicts.append(conflict)

        # Check composite roles for circular references
        for role_id in roles_to_check:
            role = self.role_designer.roles.get(role_id)
            if not role or not role.child_roles:
                continue

            visited = set()
            if self._has_circular_reference(role_id, visited):
                conflict = RoleConflict(
                    conflict_type=ConflictType.CIRCULAR_REFERENCE,
                    severity="critical",
                    role_ids=[role_id],
                    description="Circular reference detected in composite role",
                    remediation="Review and fix role hierarchy"
                )
                conflicts.append(conflict)

        self.detected_conflicts.extend(conflicts)
        return conflicts

    def _has_circular_reference(
        self,
        role_id: str,
        visited: Set[str],
        path: List[str] = None
    ) -> bool:
        """Check for circular references in composite roles"""
        if path is None:
            path = []

        if role_id in visited:
            return True

        visited.add(role_id)
        path.append(role_id)

        role = self.role_designer.roles.get(role_id)
        if role and role.child_roles:
            for child_id in role.child_roles:
                if self._has_circular_reference(child_id, visited.copy(), path.copy()):
                    return True

        return False

    def analyze_user_sod(
        self,
        user_roles: List[str]
    ) -> List[RoleConflict]:
        """Analyze SoD conflicts for a user's combined roles"""
        if not self.role_designer:
            raise ValueError("Role designer not configured")

        # Aggregate all transactions
        all_transactions = set()

        for role_id in user_roles:
            role = self.role_designer.roles.get(role_id)
            if role:
                all_transactions.update(role.transaction_codes)

        conflicts = []

        for sod in self.SOD_CONFLICTS:
            has_set_a = all_transactions & set(sod["set_a"])
            has_set_b = all_transactions & set(sod["set_b"])

            if has_set_a and has_set_b:
                # Find which roles contribute to conflict
                contributing_roles_a = []
                contributing_roles_b = []

                for role_id in user_roles:
                    role = self.role_designer.roles.get(role_id)
                    if role:
                        if set(role.transaction_codes) & set(sod["set_a"]):
                            contributing_roles_a.append(role_id)
                        if set(role.transaction_codes) & set(sod["set_b"]):
                            contributing_roles_b.append(role_id)

                conflict = RoleConflict(
                    conflict_type=ConflictType.SOD_VIOLATION,
                    severity=sod["severity"],
                    role_ids=list(set(contributing_roles_a + contributing_roles_b)),
                    description=f"User SoD violation: {sod['name']}",
                    details={
                        "sod_rule_id": sod["id"],
                        "conflicting_set_a": list(has_set_a),
                        "conflicting_set_b": list(has_set_b),
                        "roles_contributing_set_a": contributing_roles_a,
                        "roles_contributing_set_b": contributing_roles_b
                    },
                    remediation=f"Remove one of these roles: {contributing_roles_a} or {contributing_roles_b}"
                )
                conflicts.append(conflict)

        return conflicts

    # =========================================================================
    # Permission Gap Analysis
    # =========================================================================

    def analyze_permission_gaps(
        self,
        required_transactions: List[str],
        current_roles: List[str]
    ) -> List[PermissionGap]:
        """Analyze permission gaps between required and current access"""
        if not self.role_designer:
            raise ValueError("Role designer not configured")

        gaps = []

        # Get current transactions
        current_transactions = set()
        for role_id in current_roles:
            role = self.role_designer.roles.get(role_id)
            if role:
                current_transactions.update(role.transaction_codes)

        # Find missing transactions
        missing = set(required_transactions) - current_transactions

        for tcode in missing:
            gap = PermissionGap(
                gap_type=GapType.MISSING_TRANSACTION,
                description=f"Missing transaction code: {tcode}",
                required={"transaction_code": tcode},
                current={"available_transactions": list(current_transactions)},
                recommendation=f"Assign a role containing {tcode}"
            )
            gaps.append(gap)

        # Find roles that could fill the gaps
        for gap in gaps:
            tcode = gap.required.get("transaction_code")
            suitable_roles = []

            for role_id, role in self.role_designer.roles.items():
                if tcode in role.transaction_codes:
                    suitable_roles.append({
                        "role_id": role_id,
                        "name": role.name,
                        "risk_level": role.risk_level
                    })

            gap.recommendation = f"Consider roles: {suitable_roles[:3]}" if suitable_roles else "No suitable role found"

        self.detected_gaps.extend(gaps)
        return gaps

    def analyze_over_provisioning(
        self,
        user_id: str,
        user_roles: List[str],
        usage_data: Dict[str, List[str]] = None
    ) -> List[PermissionGap]:
        """Analyze over-provisioned access"""
        if not self.role_designer:
            raise ValueError("Role designer not configured")

        gaps = []
        usage_data = usage_data or {}

        # Get all transactions user has
        all_transactions = set()
        for role_id in user_roles:
            role = self.role_designer.roles.get(role_id)
            if role:
                all_transactions.update(role.transaction_codes)

        # Get used transactions
        used_transactions = set(usage_data.get("used_transactions", []))

        # Find unused transactions
        unused = all_transactions - used_transactions

        if unused:
            gap = PermissionGap(
                gap_type=GapType.MISSING_ACTIVITY,
                user_id=user_id,
                description=f"User has {len(unused)} unused transactions",
                required={"expected_usage": list(used_transactions)},
                current={"all_transactions": list(all_transactions), "unused": list(unused)},
                recommendation="Consider removing roles with unused transactions"
            )
            gaps.append(gap)

        return gaps

    # =========================================================================
    # Role Optimization
    # =========================================================================

    def recommend_optimizations(self) -> List[RoleOptimization]:
        """Generate role optimization recommendations"""
        if not self.role_designer:
            raise ValueError("Role designer not configured")

        recommendations = []

        # 1. Find roles that could be merged (high similarity)
        checked_pairs = set()
        for role_a_id in self.role_designer.roles:
            for role_b_id in self.role_designer.roles:
                if role_a_id >= role_b_id:
                    continue

                pair = (role_a_id, role_b_id)
                if pair in checked_pairs:
                    continue
                checked_pairs.add(pair)

                comparison = self.compare_roles(role_a_id, role_b_id)

                if comparison.overall_similarity > 85:
                    rec = RoleOptimization(
                        optimization_type="merge",
                        affected_roles=[role_a_id, role_b_id],
                        description=f"Roles {role_a_id} and {role_b_id} are {comparison.overall_similarity:.0f}% similar",
                        impact="Reduced complexity and maintenance",
                        savings_estimate="~50% reduction in maintenance overhead",
                        recommendations=[
                            {"action": "merge", "target": role_a_id, "into": role_b_id}
                        ],
                        risk_assessment="Low - roles are highly similar",
                        implementation_steps=[
                            f"1. Review differences between {role_a_id} and {role_b_id}",
                            "2. Create merged role with combined permissions",
                            "3. Reassign users to merged role",
                            "4. Deprecate original roles"
                        ]
                    )
                    recommendations.append(rec)

        # 2. Find roles with too many transactions (should be split)
        for role_id, role in self.role_designer.roles.items():
            if len(role.transaction_codes) > 50:
                rec = RoleOptimization(
                    optimization_type="split",
                    affected_roles=[role_id],
                    description=f"Role {role_id} has {len(role.transaction_codes)} transactions - consider splitting",
                    impact="Improved maintainability and granular access control",
                    recommendations=[
                        {"action": "split", "role": role_id,
                         "suggestion": "Split by business function"}
                    ],
                    risk_assessment="Medium - requires careful user reassignment",
                    implementation_steps=[
                        "1. Analyze transaction usage patterns",
                        "2. Identify logical groupings",
                        "3. Create new focused roles",
                        "4. Migrate users gradually"
                    ]
                )
                recommendations.append(rec)

        # 3. Find unused roles
        for role_id, role in self.role_designer.roles.items():
            if hasattr(role, 'current_assignments') and role.current_assignments == 0:
                rec = RoleOptimization(
                    optimization_type="cleanup",
                    affected_roles=[role_id],
                    description=f"Role {role_id} has no active assignments",
                    impact="Reduced clutter and maintenance",
                    recommendations=[
                        {"action": "deprecate", "role": role_id}
                    ],
                    risk_assessment="Low - no users affected",
                    implementation_steps=[
                        "1. Verify role is truly unused",
                        "2. Archive role documentation",
                        "3. Deprecate or archive role"
                    ]
                )
                recommendations.append(rec)

        # 4. Find roles that could be consolidated into composite
        business_process_roles = {}
        for role_id, role in self.role_designer.roles.items():
            bp = role.business_process
            if bp:
                if bp not in business_process_roles:
                    business_process_roles[bp] = []
                business_process_roles[bp].append(role_id)

        for bp, role_ids in business_process_roles.items():
            if len(role_ids) > 5:
                rec = RoleOptimization(
                    optimization_type="consolidate",
                    affected_roles=role_ids,
                    description=f"Business process '{bp}' has {len(role_ids)} roles - consider composite role",
                    impact="Simplified role assignment",
                    recommendations=[
                        {"action": "create_composite", "business_process": bp,
                         "child_roles": role_ids}
                    ],
                    risk_assessment="Low - structural change only",
                    implementation_steps=[
                        f"1. Review all {len(role_ids)} roles in {bp}",
                        "2. Identify common assignment patterns",
                        "3. Create composite role(s)",
                        "4. Update documentation"
                    ]
                )
                recommendations.append(rec)

        self.optimization_recommendations = recommendations
        return recommendations

    def get_role_usage_report(
        self,
        role_id: str
    ) -> Dict:
        """Generate usage report for a role"""
        if not self.role_designer:
            raise ValueError("Role designer not configured")

        role = self.role_designer.roles.get(role_id)
        if not role:
            raise ValueError(f"Role {role_id} not found")

        # Find similar roles
        similar = self.find_similar_roles(role_id, threshold=60)

        # Detect conflicts
        tcodes = set(role.transaction_codes)
        sod_issues = self._check_sod_conflicts(tcodes)

        return {
            "role_id": role_id,
            "name": role.name,
            "status": role.status.value,
            "statistics": {
                "total_permissions": len(role.permissions),
                "total_transactions": len(role.transaction_codes),
                "has_wildcards": any(
                    "*" in str(p.field_values.values())
                    for p in role.permissions
                ),
                "is_sensitive": role.is_sensitive
            },
            "similar_roles": similar[:5],
            "sod_conflicts": sod_issues,
            "risk_level": role.risk_level,
            "recommendations": self._get_role_recommendations(role)
        }

    def _get_role_recommendations(self, role) -> List[str]:
        """Get recommendations for a specific role"""
        recommendations = []

        if len(role.transaction_codes) > 50:
            recommendations.append("Consider splitting role - too many transactions")

        if not role.owner:
            recommendations.append("Assign an owner for accountability")

        if not role.documentation:
            recommendations.append("Add documentation for compliance")

        if role.risk_level in ["high", "critical"] and not role.requires_approval:
            recommendations.append("Enable approval requirement for high-risk role")

        # Check for wildcards
        for perm in role.permissions:
            if "*" in str(perm.field_values.values()):
                recommendations.append(f"Review wildcard in {perm.auth_object}")
                break

        return recommendations

    # =========================================================================
    # Statistics
    # =========================================================================

    def get_statistics(self) -> Dict:
        """Get analyzer statistics"""
        return {
            "comparisons_performed": len(self.comparison_history),
            "conflicts_detected": len(self.detected_conflicts),
            "gaps_identified": len(self.detected_gaps),
            "optimizations_recommended": len(self.optimization_recommendations),
            "conflicts_by_type": {
                ct.value: len([c for c in self.detected_conflicts if c.conflict_type == ct])
                for ct in ConflictType
            },
            "conflicts_by_severity": {
                sev: len([c for c in self.detected_conflicts if c.severity == sev])
                for sev in ["critical", "high", "medium", "low"]
            }
        }
