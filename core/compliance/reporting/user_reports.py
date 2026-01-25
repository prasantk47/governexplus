# User Master Data & Basic Lists Reports
# Equivalent to SAP SUIM User Reports

"""
User Reports for GOVERNEX+.

SAP Equivalent: SUIM > User > User List and related reports

These reports are the auditor's first stop:
- User List (complete, filterable)
- Terminated Users (should be locked)
- Generic Users (SAP*, DDIC, etc.)
- Password Policy Violations
- Concurrent Session Users
- User Comparison
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, date, timedelta
from enum import Enum

from .models import (
    User, UserStatus, UserType, RiskLevel, ReportResult
)


# ============================================================
# USER LIST REPORT (SUIM Equivalent)
# ============================================================

@dataclass
class UserListFilter:
    """Filters for user list report."""
    # Status filters
    statuses: List[UserStatus] = field(default_factory=list)
    user_types: List[UserType] = field(default_factory=list)
    include_locked: bool = True
    include_expired: bool = True

    # Date filters
    created_after: Optional[date] = None
    created_before: Optional[date] = None
    last_login_after: Optional[date] = None
    last_login_before: Optional[date] = None
    no_login_days: Optional[int] = None  # Users who haven't logged in for X days

    # Department/org filters
    departments: List[str] = field(default_factory=list)
    cost_centers: List[str] = field(default_factory=list)
    managers: List[str] = field(default_factory=list)

    # Risk filters
    min_risk_score: Optional[int] = None
    max_risk_score: Optional[int] = None
    risk_levels: List[RiskLevel] = field(default_factory=list)
    has_sod_conflicts: Optional[bool] = None
    has_critical_access: Optional[bool] = None

    # Role filters
    with_roles: List[str] = field(default_factory=list)
    without_roles: List[str] = field(default_factory=list)

    # Text search
    search_text: str = ""


class UserListReport:
    """
    Complete, filterable user list.

    SAP Equivalent: SUIM > User > User List
    """

    def __init__(self, data_provider: Optional[Callable] = None):
        """
        Initialize report.

        Args:
            data_provider: Function that returns list of User objects
        """
        self._data_provider = data_provider or self._mock_data_provider
        self._users: List[User] = []

    def execute(
        self,
        filters: Optional[UserListFilter] = None,
        sort_by: str = "username",
        ascending: bool = True,
        limit: Optional[int] = None
    ) -> ReportResult:
        """
        Execute the user list report.

        Returns filterable, sortable list of all users.
        """
        result = ReportResult(
            report_type="USER_LIST",
            report_name="User Master List",
        )

        start_time = datetime.now()

        # Get users
        self._users = self._data_provider()
        filtered_users = self._apply_filters(self._users, filters or UserListFilter())

        # Sort
        filtered_users = self._sort_users(filtered_users, sort_by, ascending)

        # Apply limit
        if limit:
            filtered_users = filtered_users[:limit]

        # Build result
        result.total_records = len(filtered_users)
        result.records = [u.to_dict() for u in filtered_users]

        # Calculate summary
        result.summary = self._calculate_summary(filtered_users)

        # Calculate findings
        result.critical_findings = sum(1 for u in filtered_users if u.risk_level == RiskLevel.CRITICAL)
        result.high_findings = sum(1 for u in filtered_users if u.risk_level == RiskLevel.HIGH)
        result.medium_findings = sum(1 for u in filtered_users if u.risk_level == RiskLevel.MEDIUM)
        result.low_findings = sum(1 for u in filtered_users if u.risk_level == RiskLevel.LOW)

        result.execution_time_seconds = (datetime.now() - start_time).total_seconds()
        result.parameters = filters.__dict__ if filters else {}

        return result

    def _apply_filters(self, users: List[User], filters: UserListFilter) -> List[User]:
        """Apply filters to user list."""
        result = users

        # Status filters
        if filters.statuses:
            result = [u for u in result if u.status in filters.statuses]

        if filters.user_types:
            result = [u for u in result if u.user_type in filters.user_types]

        if not filters.include_locked:
            result = [u for u in result if not u.is_locked]

        if not filters.include_expired:
            result = [u for u in result if not u.is_expired()]

        # Date filters
        if filters.created_after:
            result = [u for u in result if u.created_date and u.created_date >= filters.created_after]

        if filters.created_before:
            result = [u for u in result if u.created_date and u.created_date <= filters.created_before]

        if filters.last_login_after:
            result = [u for u in result if u.last_login and u.last_login.date() >= filters.last_login_after]

        if filters.no_login_days:
            cutoff = datetime.now() - timedelta(days=filters.no_login_days)
            result = [u for u in result if not u.last_login or u.last_login < cutoff]

        # Department filters
        if filters.departments:
            result = [u for u in result if u.department in filters.departments]

        if filters.cost_centers:
            result = [u for u in result if u.cost_center in filters.cost_centers]

        # Risk filters
        if filters.min_risk_score is not None:
            result = [u for u in result if u.risk_score >= filters.min_risk_score]

        if filters.max_risk_score is not None:
            result = [u for u in result if u.risk_score <= filters.max_risk_score]

        if filters.risk_levels:
            result = [u for u in result if u.risk_level in filters.risk_levels]

        if filters.has_sod_conflicts is not None:
            if filters.has_sod_conflicts:
                result = [u for u in result if u.sod_conflict_count > 0]
            else:
                result = [u for u in result if u.sod_conflict_count == 0]

        if filters.has_critical_access is not None:
            if filters.has_critical_access:
                result = [u for u in result if u.critical_access_count > 0]
            else:
                result = [u for u in result if u.critical_access_count == 0]

        # Role filters
        if filters.with_roles:
            result = [u for u in result if any(r in u.roles for r in filters.with_roles)]

        if filters.without_roles:
            result = [u for u in result if not any(r in u.roles for r in filters.without_roles)]

        # Text search
        if filters.search_text:
            search = filters.search_text.lower()
            result = [
                u for u in result
                if search in u.username.lower()
                or search in u.full_name.lower()
                or search in u.email.lower()
            ]

        return result

    def _sort_users(self, users: List[User], sort_by: str, ascending: bool) -> List[User]:
        """Sort users by field."""
        key_map = {
            "username": lambda u: u.username,
            "full_name": lambda u: u.full_name,
            "department": lambda u: u.department,
            "risk_score": lambda u: u.risk_score,
            "last_login": lambda u: u.last_login or datetime.min,
            "created_date": lambda u: u.created_date or date.min,
        }

        key_func = key_map.get(sort_by, lambda u: u.username)
        return sorted(users, key=key_func, reverse=not ascending)

    def _calculate_summary(self, users: List[User]) -> Dict[str, Any]:
        """Calculate summary statistics."""
        active_count = sum(1 for u in users if u.status == UserStatus.ACTIVE and not u.is_locked)
        locked_count = sum(1 for u in users if u.is_locked)
        expired_count = sum(1 for u in users if u.is_expired())
        never_logged_in = sum(1 for u in users if not u.last_login)
        no_login_90_days = sum(1 for u in users if u.days_since_last_login() and u.days_since_last_login() > 90)

        return {
            "total_users": len(users),
            "active_users": active_count,
            "locked_users": locked_count,
            "expired_users": expired_count,
            "never_logged_in": never_logged_in,
            "no_login_90_days": no_login_90_days,
            "by_status": {s.value: sum(1 for u in users if u.status == s) for s in UserStatus},
            "by_type": {t.value: sum(1 for u in users if u.user_type == t) for t in UserType},
            "by_risk_level": {r.value: sum(1 for u in users if u.risk_level == r) for r in RiskLevel},
            "with_sod_conflicts": sum(1 for u in users if u.sod_conflict_count > 0),
            "with_critical_access": sum(1 for u in users if u.critical_access_count > 0),
        }

    def _mock_data_provider(self) -> List[User]:
        """Mock data for testing."""
        return []


class UserMasterReport(UserListReport):
    """Alias for UserListReport - complete user master data."""
    pass


# ============================================================
# TERMINATED USER REPORT
# ============================================================

class TerminatedUserReport:
    """
    Users who should be deactivated but aren't.

    CRITICAL AUDIT FINDING:
    Users with termination date in HR but still active in system.
    """

    def __init__(self, data_provider: Optional[Callable] = None):
        self._data_provider = data_provider or (lambda: [])

    def execute(self) -> ReportResult:
        """Find terminated users who are still active."""
        result = ReportResult(
            report_type="TERMINATED_USERS",
            report_name="Terminated Users Still Active",
        )

        start_time = datetime.now()
        users = self._data_provider()

        # Find violations
        violations = []
        for user in users:
            if user.is_terminated() and not user.is_locked:
                violations.append({
                    **user.to_dict(),
                    "violation": "TERMINATED_NOT_LOCKED",
                    "termination_date": user.termination_date.isoformat() if user.termination_date else None,
                    "days_since_termination": (date.today() - user.termination_date).days if user.termination_date else 0,
                    "severity": "CRITICAL",
                })

        result.total_records = len(violations)
        result.records = violations
        result.critical_findings = len(violations)

        result.summary = {
            "total_violations": len(violations),
            "by_department": self._group_by_field(violations, "department"),
            "avg_days_since_termination": sum(v["days_since_termination"] for v in violations) / len(violations) if violations else 0,
            "oldest_violation": max((v["days_since_termination"] for v in violations), default=0),
        }

        result.execution_time_seconds = (datetime.now() - start_time).total_seconds()

        return result

    def _group_by_field(self, records: List[Dict], field: str) -> Dict[str, int]:
        """Group records by field."""
        groups = {}
        for r in records:
            key = r.get(field, "Unknown")
            groups[key] = groups.get(key, 0) + 1
        return groups


# ============================================================
# GENERIC USER REPORT
# ============================================================

class GenericUserReport:
    """
    Generic/Default/Shared users.

    AUDIT FOCUS:
    - SAP*, DDIC, EARLYWATCH must be locked
    - No business operations on generic accounts
    """

    GENERIC_PATTERNS = [
        "SAP*", "DDIC", "EARLYWATCH", "ADMIN", "TEST", "DEMO",
        "GENERIC", "SHARED", "BATCH", "INTERFACE", "RFC",
        "SERVICE", "SYSTEM", "SUPPORT", "HELPDESK"
    ]

    def __init__(self, data_provider: Optional[Callable] = None):
        self._data_provider = data_provider or (lambda: [])

    def execute(self, include_locked: bool = True) -> ReportResult:
        """Find generic/default users."""
        result = ReportResult(
            report_type="GENERIC_USERS",
            report_name="Generic and Default Users",
        )

        start_time = datetime.now()
        users = self._data_provider()

        # Find generic users
        findings = []
        for user in users:
            if user.is_generic_account():
                severity = "CRITICAL" if not user.is_locked else "INFO"
                finding = {
                    **user.to_dict(),
                    "finding_type": "GENERIC_ACCOUNT",
                    "pattern_matched": self._get_matched_pattern(user.username),
                    "severity": severity,
                    "recommendation": "Lock account" if not user.is_locked else "Verify no business use",
                }

                if include_locked or not user.is_locked:
                    findings.append(finding)

                    if severity == "CRITICAL":
                        result.critical_findings += 1
                    elif user.last_login and user.last_login > datetime.now() - timedelta(days=30):
                        result.high_findings += 1  # Recently used generic account

        result.total_records = len(findings)
        result.records = findings

        result.summary = {
            "total_generic_users": len(findings),
            "unlocked_critical": result.critical_findings,
            "recently_used": result.high_findings,
            "by_pattern": self._group_by_pattern(findings),
        }

        result.execution_time_seconds = (datetime.now() - start_time).total_seconds()

        return result

    def _get_matched_pattern(self, username: str) -> str:
        """Get the pattern that matched."""
        for pattern in self.GENERIC_PATTERNS:
            if pattern.lower().replace("*", "") in username.lower():
                return pattern
        return "CUSTOM_GENERIC"

    def _group_by_pattern(self, findings: List[Dict]) -> Dict[str, int]:
        """Group by matched pattern."""
        groups = {}
        for f in findings:
            pattern = f.get("pattern_matched", "OTHER")
            groups[pattern] = groups.get(pattern, 0) + 1
        return groups


# ============================================================
# PASSWORD POLICY REPORT
# ============================================================

class PasswordPolicyReport:
    """
    Password policy compliance report.

    AUDIT CHECKS:
    - Passwords set to never expire
    - Expired passwords
    - Password age > policy
    """

    def __init__(
        self,
        data_provider: Optional[Callable] = None,
        max_password_age_days: int = 90
    ):
        self._data_provider = data_provider or (lambda: [])
        self.max_password_age_days = max_password_age_days

    def execute(self) -> ReportResult:
        """Check password policy compliance."""
        result = ReportResult(
            report_type="PASSWORD_POLICY",
            report_name="Password Policy Compliance",
        )

        start_time = datetime.now()
        users = self._data_provider()

        findings = []
        never_expires = []
        expired = []
        aged = []

        for user in users:
            # Skip locked/inactive users
            if user.is_locked or user.status != UserStatus.ACTIVE:
                continue

            # Check never expires
            if user.password_never_expires:
                finding = {
                    **user.to_dict(),
                    "violation_type": "PASSWORD_NEVER_EXPIRES",
                    "severity": "HIGH",
                    "recommendation": "Enable password expiration",
                }
                findings.append(finding)
                never_expires.append(user)
                result.high_findings += 1

            # Check expired
            elif user.is_password_expired():
                finding = {
                    **user.to_dict(),
                    "violation_type": "PASSWORD_EXPIRED",
                    "password_expires": user.password_expires.isoformat() if user.password_expires else None,
                    "severity": "MEDIUM",
                    "recommendation": "Force password change",
                }
                findings.append(finding)
                expired.append(user)
                result.medium_findings += 1

            # Check age
            elif user.password_changed:
                age_days = (date.today() - user.password_changed).days
                if age_days > self.max_password_age_days:
                    finding = {
                        **user.to_dict(),
                        "violation_type": "PASSWORD_AGED",
                        "password_age_days": age_days,
                        "max_allowed_days": self.max_password_age_days,
                        "severity": "LOW",
                        "recommendation": "Review password rotation policy",
                    }
                    findings.append(finding)
                    aged.append(user)
                    result.low_findings += 1

        result.total_records = len(findings)
        result.records = findings

        result.summary = {
            "total_violations": len(findings),
            "never_expires": len(never_expires),
            "expired": len(expired),
            "aged_passwords": len(aged),
            "compliance_rate": 1 - (len(findings) / len(users)) if users else 1,
        }

        result.execution_time_seconds = (datetime.now() - start_time).total_seconds()

        return result


# ============================================================
# CONCURRENT SESSION REPORT
# ============================================================

class ConcurrentSessionReport:
    """
    Users allowed multiple concurrent logins.

    AUDIT CONCERN:
    Multiple logins can indicate:
    - Shared credentials
    - Account compromise
    - Policy violation
    """

    def __init__(self, data_provider: Optional[Callable] = None):
        self._data_provider = data_provider or (lambda: [])

    def execute(self) -> ReportResult:
        """Find users with multiple login capability."""
        result = ReportResult(
            report_type="CONCURRENT_SESSIONS",
            report_name="Users with Multiple Login Allowed",
        )

        start_time = datetime.now()
        users = self._data_provider()

        findings = []
        for user in users:
            if user.allow_multiple_logons and user.status == UserStatus.ACTIVE:
                # Higher risk for dialog users
                if user.user_type == UserType.DIALOG:
                    severity = "MEDIUM"
                    result.medium_findings += 1
                else:
                    severity = "LOW"
                    result.low_findings += 1

                finding = {
                    **user.to_dict(),
                    "finding_type": "MULTIPLE_LOGONS_ALLOWED",
                    "severity": severity,
                    "recommendation": "Review business need for multiple sessions",
                }
                findings.append(finding)

        result.total_records = len(findings)
        result.records = findings

        result.summary = {
            "total_with_multiple_logon": len(findings),
            "dialog_users": sum(1 for f in findings if f["user_type"] == UserType.DIALOG.value),
            "system_users": sum(1 for f in findings if f["user_type"] != UserType.DIALOG.value),
        }

        result.execution_time_seconds = (datetime.now() - start_time).total_seconds()

        return result


# ============================================================
# USER COMPARISON REPORT
# ============================================================

class UserComparisonReport:
    """
    Compare access between two users.

    SAP Equivalent: SUIM > User > User Comparison

    USE CASES:
    - Verify test user matches production user
    - Compare access across environments
    - Identify excessive permissions
    """

    def __init__(self, data_provider: Optional[Callable] = None):
        self._data_provider = data_provider or (lambda: [])

    def execute(
        self,
        user_1_id: str,
        user_2_id: str
    ) -> ReportResult:
        """Compare two users' access."""
        result = ReportResult(
            report_type="USER_COMPARISON",
            report_name=f"User Comparison: {user_1_id} vs {user_2_id}",
        )

        start_time = datetime.now()
        users = self._data_provider()

        user_1 = next((u for u in users if u.user_id == user_1_id), None)
        user_2 = next((u for u in users if u.user_id == user_2_id), None)

        if not user_1 or not user_2:
            result.summary = {"error": "One or both users not found"}
            return result

        # Compare roles
        roles_1 = set(user_1.roles)
        roles_2 = set(user_2.roles)

        common_roles = roles_1 & roles_2
        only_user_1 = roles_1 - roles_2
        only_user_2 = roles_2 - roles_1

        comparison = {
            "user_1": user_1.to_dict(),
            "user_2": user_2.to_dict(),
            "roles": {
                "common": list(common_roles),
                "only_user_1": list(only_user_1),
                "only_user_2": list(only_user_2),
            },
            "risk_comparison": {
                "user_1_risk_score": user_1.risk_score,
                "user_2_risk_score": user_2.risk_score,
                "difference": user_1.risk_score - user_2.risk_score,
            },
            "sod_comparison": {
                "user_1_conflicts": user_1.sod_conflict_count,
                "user_2_conflicts": user_2.sod_conflict_count,
            },
            "match_percentage": len(common_roles) / max(len(roles_1), len(roles_2), 1) * 100,
        }

        result.records = [comparison]
        result.total_records = 1

        result.summary = {
            "common_roles": len(common_roles),
            "unique_to_user_1": len(only_user_1),
            "unique_to_user_2": len(only_user_2),
            "match_percentage": comparison["match_percentage"],
        }

        result.execution_time_seconds = (datetime.now() - start_time).total_seconds()
        result.parameters = {"user_1_id": user_1_id, "user_2_id": user_2_id}

        return result
