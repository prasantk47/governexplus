# Role & Authorization Assignment Reports
# Equivalent to SAP SUIM Role Reports

"""
Role Reports for GOVERNEX+.

SAP Equivalent: SUIM > User > By Role and related reports

AUDIT USE CASES:
- Who has which roles
- Critical role assignments
- Role comparison
- Orphaned roles
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable, Set
from datetime import datetime, date, timedelta

from .models import (
    User, Role, RoleAssignment, UserStatus, RiskLevel, ReportResult
)


# ============================================================
# USERS BY ROLE REPORT
# ============================================================

class UsersByRoleReport:
    """
    All users assigned to a specific role.

    SAP Equivalent: SUIM > User > By Role

    CRITICAL FOR:
    - Who has SAP_ALL, SAP_NEW
    - Who has powerful custom roles
    """

    def __init__(
        self,
        user_provider: Optional[Callable] = None,
        role_provider: Optional[Callable] = None,
        assignment_provider: Optional[Callable] = None
    ):
        self._user_provider = user_provider or (lambda: [])
        self._role_provider = role_provider or (lambda: [])
        self._assignment_provider = assignment_provider or (lambda: [])

    def execute(
        self,
        role_ids: List[str],
        include_inactive_users: bool = False
    ) -> ReportResult:
        """Get all users with specified roles."""
        result = ReportResult(
            report_type="USERS_BY_ROLE",
            report_name=f"Users with Roles: {', '.join(role_ids)}",
        )

        start_time = datetime.now()

        users = {u.user_id: u for u in self._user_provider()}
        roles = {r.role_id: r for r in self._role_provider()}
        assignments = self._assignment_provider()

        findings = []

        for role_id in role_ids:
            role = roles.get(role_id)
            if not role:
                continue

            # Find users with this role
            role_assignments = [a for a in assignments if a.role_id == role_id and a.is_active]

            for assignment in role_assignments:
                user = users.get(assignment.user_id)
                if not user:
                    continue

                # Filter inactive users
                if not include_inactive_users and user.status != UserStatus.ACTIVE:
                    continue

                # Determine severity
                if role.is_critical or role.is_privileged:
                    severity = "HIGH"
                    result.high_findings += 1
                else:
                    severity = "INFO"
                    result.low_findings += 1

                finding = {
                    "role_id": role_id,
                    "role_name": role.role_name,
                    "role_is_critical": role.is_critical,
                    "role_risk_score": role.risk_score,
                    "user_id": user.user_id,
                    "username": user.username,
                    "full_name": user.full_name,
                    "department": user.department,
                    "user_status": user.status.value,
                    "assignment_date": assignment.assigned_date.isoformat() if assignment.assigned_date else None,
                    "valid_from": assignment.valid_from.isoformat() if assignment.valid_from else None,
                    "valid_to": assignment.valid_to.isoformat() if assignment.valid_to else None,
                    "approved_by": assignment.approved_by,
                    "is_direct": assignment.is_direct,
                    "severity": severity,
                }
                findings.append(finding)

        result.total_records = len(findings)
        result.records = findings

        # Summary by role
        role_summary = {}
        for role_id in role_ids:
            role_users = [f for f in findings if f["role_id"] == role_id]
            role = roles.get(role_id)
            role_summary[role_id] = {
                "role_name": role.role_name if role else role_id,
                "total_users": len(role_users),
                "active_users": sum(1 for f in role_users if f["user_status"] == "ACTIVE"),
                "is_critical": role.is_critical if role else False,
            }

        result.summary = {
            "total_assignments": len(findings),
            "unique_users": len(set(f["user_id"] for f in findings)),
            "by_role": role_summary,
        }

        result.execution_time_seconds = (datetime.now() - start_time).total_seconds()
        result.parameters = {"role_ids": role_ids, "include_inactive_users": include_inactive_users}

        return result


# ============================================================
# ROLES BY USER REPORT
# ============================================================

class RolesByUserReport:
    """
    All roles assigned to a specific user.

    SAP Equivalent: SU01 > Roles tab

    AUDIT USE:
    - Review what a critical user can do
    - Sample testing of access assignments
    """

    def __init__(
        self,
        user_provider: Optional[Callable] = None,
        role_provider: Optional[Callable] = None,
        assignment_provider: Optional[Callable] = None
    ):
        self._user_provider = user_provider or (lambda: [])
        self._role_provider = role_provider or (lambda: [])
        self._assignment_provider = assignment_provider or (lambda: [])

    def execute(
        self,
        user_ids: List[str],
        include_expired: bool = False
    ) -> ReportResult:
        """Get all roles for specified users."""
        result = ReportResult(
            report_type="ROLES_BY_USER",
            report_name=f"Roles for Users: {', '.join(user_ids)}",
        )

        start_time = datetime.now()

        users = {u.user_id: u for u in self._user_provider()}
        roles = {r.role_id: r for r in self._role_provider()}
        assignments = self._assignment_provider()

        findings = []

        for user_id in user_ids:
            user = users.get(user_id)
            if not user:
                continue

            # Find roles for this user
            user_assignments = [a for a in assignments if a.user_id == user_id]

            if not include_expired:
                user_assignments = [a for a in user_assignments if not a.is_expired()]

            for assignment in user_assignments:
                role = roles.get(assignment.role_id)
                if not role:
                    continue

                # Calculate risk contribution
                if role.is_critical:
                    severity = "CRITICAL"
                    result.critical_findings += 1
                elif role.is_privileged or role.risk_score > 70:
                    severity = "HIGH"
                    result.high_findings += 1
                elif role.risk_score > 40:
                    severity = "MEDIUM"
                    result.medium_findings += 1
                else:
                    severity = "LOW"
                    result.low_findings += 1

                finding = {
                    "user_id": user_id,
                    "username": user.username,
                    "full_name": user.full_name,
                    "role_id": role.role_id,
                    "role_name": role.role_name,
                    "role_type": role.role_type,
                    "role_description": role.description,
                    "role_risk_score": role.risk_score,
                    "role_is_critical": role.is_critical,
                    "role_is_privileged": role.is_privileged,
                    "assignment_date": assignment.assigned_date.isoformat() if assignment.assigned_date else None,
                    "valid_to": assignment.valid_to.isoformat() if assignment.valid_to else None,
                    "is_expired": assignment.is_expired(),
                    "is_direct": assignment.is_direct,
                    "inherited_from": assignment.inherited_from,
                    "approved_by": assignment.approved_by,
                    "severity": severity,
                }
                findings.append(finding)

        result.total_records = len(findings)
        result.records = findings

        # Summary by user
        user_summary = {}
        for user_id in user_ids:
            user_roles = [f for f in findings if f["user_id"] == user_id]
            user = users.get(user_id)
            user_summary[user_id] = {
                "username": user.username if user else user_id,
                "total_roles": len(user_roles),
                "critical_roles": sum(1 for f in user_roles if f["role_is_critical"]),
                "privileged_roles": sum(1 for f in user_roles if f["role_is_privileged"]),
                "total_risk_score": user.risk_score if user else 0,
            }

        result.summary = {
            "total_assignments": len(findings),
            "unique_roles": len(set(f["role_id"] for f in findings)),
            "by_user": user_summary,
        }

        result.execution_time_seconds = (datetime.now() - start_time).total_seconds()
        result.parameters = {"user_ids": user_ids, "include_expired": include_expired}

        return result


# ============================================================
# ROLE ASSIGNMENT REPORT (COMPREHENSIVE)
# ============================================================

class RoleAssignmentReport:
    """
    Complete role-to-user assignment report.

    Shows all assignments with full audit trail.
    """

    def __init__(
        self,
        user_provider: Optional[Callable] = None,
        role_provider: Optional[Callable] = None,
        assignment_provider: Optional[Callable] = None
    ):
        self._user_provider = user_provider or (lambda: [])
        self._role_provider = role_provider or (lambda: [])
        self._assignment_provider = assignment_provider or (lambda: [])

    def execute(
        self,
        filter_critical_only: bool = False,
        filter_department: Optional[str] = None,
        include_inactive: bool = False
    ) -> ReportResult:
        """Get all role assignments."""
        result = ReportResult(
            report_type="ROLE_ASSIGNMENTS",
            report_name="Role Assignment Report",
        )

        start_time = datetime.now()

        users = {u.user_id: u for u in self._user_provider()}
        roles = {r.role_id: r for r in self._role_provider()}
        assignments = self._assignment_provider()

        findings = []

        for assignment in assignments:
            if not assignment.is_active and not include_inactive:
                continue

            user = users.get(assignment.user_id)
            role = roles.get(assignment.role_id)

            if not user or not role:
                continue

            # Apply filters
            if filter_critical_only and not role.is_critical:
                continue

            if filter_department and user.department != filter_department:
                continue

            finding = {
                "assignment_id": assignment.assignment_id,
                "user_id": user.user_id,
                "username": user.username,
                "user_department": user.department,
                "user_status": user.status.value,
                "role_id": role.role_id,
                "role_name": role.role_name,
                "role_risk_score": role.risk_score,
                "role_is_critical": role.is_critical,
                "assigned_date": assignment.assigned_date.isoformat() if assignment.assigned_date else None,
                "valid_from": assignment.valid_from.isoformat() if assignment.valid_from else None,
                "valid_to": assignment.valid_to.isoformat() if assignment.valid_to else None,
                "approved_by": assignment.approved_by,
                "request_id": assignment.request_id,
                "is_direct": assignment.is_direct,
            }
            findings.append(finding)

            if role.is_critical:
                result.critical_findings += 1
            elif role.risk_score > 70:
                result.high_findings += 1

        result.total_records = len(findings)
        result.records = findings

        result.summary = {
            "total_assignments": len(findings),
            "unique_users": len(set(f["user_id"] for f in findings)),
            "unique_roles": len(set(f["role_id"] for f in findings)),
            "critical_assignments": result.critical_findings,
            "by_department": self._group_by(findings, "user_department"),
        }

        result.execution_time_seconds = (datetime.now() - start_time).total_seconds()

        return result

    def _group_by(self, records: List[Dict], field: str) -> Dict[str, int]:
        """Group records by field."""
        groups = {}
        for r in records:
            key = r.get(field, "Unknown")
            groups[key] = groups.get(key, 0) + 1
        return groups


# ============================================================
# CRITICAL ROLE REPORT
# ============================================================

class CriticalRoleReport:
    """
    Report on critical/powerful roles.

    AUDIT FOCUS:
    - SAP_ALL, SAP_NEW assignments
    - Custom "power" roles
    - Roles with sensitive authorizations
    """

    CRITICAL_ROLE_PATTERNS = [
        "SAP_ALL", "SAP_NEW", "S_A.ADMIN", "ADMIN", "SUPER",
        "FULL_ACCESS", "ALL_ACCESS", "DEVELOPER", "BASIS"
    ]

    def __init__(
        self,
        user_provider: Optional[Callable] = None,
        role_provider: Optional[Callable] = None,
        assignment_provider: Optional[Callable] = None
    ):
        self._user_provider = user_provider or (lambda: [])
        self._role_provider = role_provider or (lambda: [])
        self._assignment_provider = assignment_provider or (lambda: [])

    def execute(self) -> ReportResult:
        """Report on critical role assignments."""
        result = ReportResult(
            report_type="CRITICAL_ROLES",
            report_name="Critical Role Assignment Report",
        )

        start_time = datetime.now()

        users = {u.user_id: u for u in self._user_provider()}
        roles = {r.role_id: r for r in self._role_provider()}
        assignments = self._assignment_provider()

        # Find critical roles
        critical_roles = []
        for role in roles.values():
            is_critical = (
                role.is_critical or
                role.is_privileged or
                any(p.lower() in role.role_name.lower() for p in self.CRITICAL_ROLE_PATTERNS) or
                role.risk_score >= 80
            )
            if is_critical:
                critical_roles.append(role)

        # Find all assignments to critical roles
        findings = []
        for role in critical_roles:
            role_assignments = [a for a in assignments if a.role_id == role.role_id and a.is_active]

            for assignment in role_assignments:
                user = users.get(assignment.user_id)
                if not user:
                    continue

                # Severity based on user type
                if user.user_type == UserType.DIALOG:
                    severity = "CRITICAL"
                    result.critical_findings += 1
                else:
                    severity = "HIGH"
                    result.high_findings += 1

                finding = {
                    "role_id": role.role_id,
                    "role_name": role.role_name,
                    "role_risk_score": role.risk_score,
                    "critical_reason": self._get_critical_reason(role),
                    "user_id": user.user_id,
                    "username": user.username,
                    "full_name": user.full_name,
                    "user_type": user.user_type.value,
                    "department": user.department,
                    "assigned_date": assignment.assigned_date.isoformat() if assignment.assigned_date else None,
                    "approved_by": assignment.approved_by,
                    "business_justification": "",  # Would come from request
                    "severity": severity,
                    "recommendation": "Review business need and apply least privilege",
                }
                findings.append(finding)

        result.total_records = len(findings)
        result.records = findings

        result.summary = {
            "critical_roles_found": len(critical_roles),
            "total_critical_assignments": len(findings),
            "unique_users_with_critical": len(set(f["user_id"] for f in findings)),
            "by_role": {
                r.role_id: sum(1 for f in findings if f["role_id"] == r.role_id)
                for r in critical_roles
            },
            "dialog_users_with_critical": sum(1 for f in findings if f["user_type"] == "DIALOG"),
        }

        result.execution_time_seconds = (datetime.now() - start_time).total_seconds()

        return result

    def _get_critical_reason(self, role: Role) -> str:
        """Determine why role is critical."""
        reasons = []
        if role.is_critical:
            reasons.append("Marked as critical")
        if role.is_privileged:
            reasons.append("Privileged role")
        if role.risk_score >= 80:
            reasons.append(f"High risk score ({role.risk_score})")
        for pattern in self.CRITICAL_ROLE_PATTERNS:
            if pattern.lower() in role.role_name.lower():
                reasons.append(f"Matches pattern: {pattern}")
                break
        return "; ".join(reasons) if reasons else "Unknown"


# Need to import UserType
from .models import UserType


# ============================================================
# ROLE COMPARISON REPORT
# ============================================================

class RoleComparisonReport:
    """
    Compare two roles.

    USE CASES:
    - Verify derived roles match parent
    - Compare roles across systems
    """

    def __init__(self, role_provider: Optional[Callable] = None):
        self._role_provider = role_provider or (lambda: [])

    def execute(self, role_1_id: str, role_2_id: str) -> ReportResult:
        """Compare two roles."""
        result = ReportResult(
            report_type="ROLE_COMPARISON",
            report_name=f"Role Comparison: {role_1_id} vs {role_2_id}",
        )

        start_time = datetime.now()

        roles = {r.role_id: r for r in self._role_provider()}
        role_1 = roles.get(role_1_id)
        role_2 = roles.get(role_2_id)

        if not role_1 or not role_2:
            result.summary = {"error": "One or both roles not found"}
            return result

        # Compare transactions
        tcodes_1 = set(role_1.transactions)
        tcodes_2 = set(role_2.transactions)

        # Compare auth objects
        auth_1 = set(role_1.authorization_objects)
        auth_2 = set(role_2.authorization_objects)

        comparison = {
            "role_1": role_1.to_dict(),
            "role_2": role_2.to_dict(),
            "transactions": {
                "common": list(tcodes_1 & tcodes_2),
                "only_role_1": list(tcodes_1 - tcodes_2),
                "only_role_2": list(tcodes_2 - tcodes_1),
            },
            "authorization_objects": {
                "common": list(auth_1 & auth_2),
                "only_role_1": list(auth_1 - auth_2),
                "only_role_2": list(auth_2 - auth_1),
            },
            "risk_comparison": {
                "role_1_risk": role_1.risk_score,
                "role_2_risk": role_2.risk_score,
                "difference": role_1.risk_score - role_2.risk_score,
            },
            "match_percentage": {
                "transactions": len(tcodes_1 & tcodes_2) / max(len(tcodes_1 | tcodes_2), 1) * 100,
                "auth_objects": len(auth_1 & auth_2) / max(len(auth_1 | auth_2), 1) * 100,
            },
        }

        result.records = [comparison]
        result.total_records = 1

        result.summary = {
            "common_transactions": len(tcodes_1 & tcodes_2),
            "unique_to_role_1": len(tcodes_1 - tcodes_2),
            "unique_to_role_2": len(tcodes_2 - tcodes_1),
            "transaction_match_pct": comparison["match_percentage"]["transactions"],
        }

        result.execution_time_seconds = (datetime.now() - start_time).total_seconds()
        result.parameters = {"role_1_id": role_1_id, "role_2_id": role_2_id}

        return result


# ============================================================
# ORPHANED ROLE REPORT
# ============================================================

class OrphanedRoleReport:
    """
    Roles with no active users assigned.

    AUDIT CONCERN:
    - May indicate cleanup needed
    - May be roles created but never used
    - Could be roles for terminated users
    """

    def __init__(
        self,
        role_provider: Optional[Callable] = None,
        assignment_provider: Optional[Callable] = None
    ):
        self._role_provider = role_provider or (lambda: [])
        self._assignment_provider = assignment_provider or (lambda: [])

    def execute(self, inactive_days: int = 180) -> ReportResult:
        """Find roles with no active assignments."""
        result = ReportResult(
            report_type="ORPHANED_ROLES",
            report_name="Orphaned Roles Report",
        )

        start_time = datetime.now()

        roles = list(self._role_provider())
        assignments = self._assignment_provider()

        # Find roles with active assignments
        active_role_ids = set(
            a.role_id for a in assignments
            if a.is_active and not a.is_expired()
        )

        findings = []
        for role in roles:
            if role.role_id not in active_role_ids:
                finding = {
                    **role.to_dict(),
                    "finding_type": "NO_ACTIVE_ASSIGNMENTS",
                    "last_modified": role.modified_date.isoformat() if role.modified_date else None,
                    "days_since_modified": (datetime.now() - role.modified_date).days if role.modified_date else None,
                    "recommendation": "Review for deletion or archive",
                }
                findings.append(finding)
                result.low_findings += 1

        result.total_records = len(findings)
        result.records = findings

        result.summary = {
            "total_roles": len(roles),
            "orphaned_roles": len(findings),
            "orphaned_percentage": len(findings) / len(roles) * 100 if roles else 0,
        }

        result.execution_time_seconds = (datetime.now() - start_time).total_seconds()

        return result
