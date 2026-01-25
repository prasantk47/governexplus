# Privileged / Emergency / Firefighter Access Reports
# Critical for Audit

"""
Firefighter (Emergency Access) Reports for GOVERNEX+.

SAP Equivalent: GRC Access Control - Superuser Privilege Management (SPM)

MAJOR AUDIT FOCUS AREA:
- All Firefighter/emergency access must be logged
- Every action must be traceable
- Regular review required
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, date, timedelta
from collections import defaultdict

from .models import (
    User, FirefighterID, FirefighterUsage, UserStatus, RiskLevel, ReportResult
)


# ============================================================
# FIREFIGHTER USAGE REPORT
# ============================================================

class FirefighterUsageReport:
    """
    Firefighter usage summary.

    Shows who used what firefighter ID and when.
    """

    def __init__(
        self,
        ff_provider: Optional[Callable] = None,
        usage_provider: Optional[Callable] = None,
        user_provider: Optional[Callable] = None
    ):
        self._ff_provider = ff_provider or (lambda: [])
        self._usage_provider = usage_provider or (lambda: [])
        self._user_provider = user_provider or (lambda: [])

    def execute(
        self,
        days: int = 30,
        ff_ids: Optional[List[str]] = None,
        user_ids: Optional[List[str]] = None
    ) -> ReportResult:
        """
        Generate firefighter usage report.

        Args:
            days: Number of days to look back
            ff_ids: Filter by specific firefighter IDs
            user_ids: Filter by users who checked out
        """
        result = ReportResult(
            report_type="FIREFIGHTER_USAGE",
            report_name=f"Firefighter Usage Report (Last {days} Days)",
        )

        start_time = datetime.now()
        cutoff = datetime.now() - timedelta(days=days)

        ff_ids_map = {ff.ff_id: ff for ff in self._ff_provider()}
        usages = self._usage_provider()
        users = {u.user_id: u for u in self._user_provider()}

        # Filter usages
        filtered_usages = []
        for usage in usages:
            if usage.checkout_time < cutoff:
                continue
            if ff_ids and usage.ff_id not in ff_ids:
                continue
            if user_ids and usage.user_id not in user_ids:
                continue
            filtered_usages.append(usage)

        # Build findings
        findings = []
        for usage in filtered_usages:
            ff = ff_ids_map.get(usage.ff_id)
            user = users.get(usage.user_id)

            # Determine severity based on duration and actions
            if usage.duration_minutes > 240:  # > 4 hours
                severity = "HIGH"
                result.high_findings += 1
            elif usage.critical_actions > 0:
                severity = "HIGH"
                result.high_findings += 1
            elif not usage.reviewed:
                severity = "MEDIUM"
                result.medium_findings += 1
            else:
                severity = "LOW"
                result.low_findings += 1

            finding = {
                "usage_id": usage.usage_id,
                "ff_id": usage.ff_id,
                "ff_name": ff.ff_name if ff else usage.ff_id,
                "ff_owner": ff.owner_name if ff else "",
                "user_id": usage.user_id,
                "username": user.username if user else usage.username,
                "user_department": user.department if user else "",
                "checkout_time": usage.checkout_time.isoformat(),
                "checkin_time": usage.checkin_time.isoformat() if usage.checkin_time else "STILL_ACTIVE",
                "duration_minutes": usage.duration_minutes,
                "reason": usage.reason,
                "ticket_number": usage.ticket_number,
                "approved_by": usage.approved_by,
                "transactions_executed": usage.transactions_executed,
                "total_actions": usage.actions_performed,
                "critical_actions": usage.critical_actions,
                "reviewed": usage.reviewed,
                "reviewed_by": usage.reviewed_by if usage.reviewed else "",
                "severity": severity,
            }
            findings.append(finding)

        # Sort by checkout time descending
        findings.sort(key=lambda x: x["checkout_time"], reverse=True)

        result.records = findings
        result.total_records = len(findings)

        # Build summary
        result.summary = {
            "period_days": days,
            "total_usages": len(findings),
            "unique_users": len(set(f["user_id"] for f in findings)),
            "unique_ff_ids": len(set(f["ff_id"] for f in findings)),
            "total_duration_hours": sum(f["duration_minutes"] for f in findings) / 60,
            "avg_duration_minutes": sum(f["duration_minutes"] for f in findings) / len(findings) if findings else 0,
            "unreviewed_count": sum(1 for f in findings if not f["reviewed"]),
            "still_active": sum(1 for f in findings if f["checkin_time"] == "STILL_ACTIVE"),
            "by_ff_id": self._group_by_field(findings, "ff_id"),
            "by_user": self._group_by_field(findings, "username"),
        }

        result.execution_time_seconds = (datetime.now() - start_time).total_seconds()
        result.parameters = {"days": days, "ff_ids": ff_ids, "user_ids": user_ids}

        return result

    def _group_by_field(self, findings: List[Dict], field: str) -> Dict[str, int]:
        """Group findings by field."""
        groups = {}
        for f in findings:
            key = f.get(field, "Unknown")
            groups[key] = groups.get(key, 0) + 1
        return groups


# ============================================================
# FIREFIGHTER LOG REPORT
# ============================================================

class FirefighterLogReport:
    """
    Detailed activity log for firefighter sessions.

    Shows every action performed during emergency access.
    """

    def __init__(
        self,
        usage_provider: Optional[Callable] = None,
        activity_provider: Optional[Callable] = None
    ):
        self._usage_provider = usage_provider or (lambda: [])
        self._activity_provider = activity_provider or (lambda: [])

    def execute(
        self,
        usage_id: Optional[str] = None,
        ff_id: Optional[str] = None,
        days: int = 7
    ) -> ReportResult:
        """
        Generate detailed activity log.

        Args:
            usage_id: Specific usage session
            ff_id: All usages for a firefighter ID
            days: Time period to search
        """
        result = ReportResult(
            report_type="FIREFIGHTER_LOG",
            report_name="Firefighter Activity Log",
        )

        start_time = datetime.now()
        cutoff = datetime.now() - timedelta(days=days)

        usages = self._usage_provider()
        activities = self._activity_provider()

        # Filter usages
        target_usages = []
        for usage in usages:
            if usage_id and usage.usage_id != usage_id:
                continue
            if ff_id and usage.ff_id != ff_id:
                continue
            if usage.checkout_time < cutoff:
                continue
            target_usages.append(usage)

        # Build activity log
        findings = []
        for usage in target_usages:
            # Get activities for this session
            session_activities = [
                a for a in activities
                if a.get("usage_id") == usage.usage_id or (
                    a.get("ff_id") == usage.ff_id and
                    usage.checkout_time <= a.get("timestamp", datetime.min) <= (usage.checkin_time or datetime.now())
                )
            ]

            for activity in session_activities:
                # Classify activity risk
                is_critical = activity.get("is_critical", False) or activity.get("transaction", "") in [
                    "FB02", "FK02", "XK02", "F110", "SU01", "PFCG"
                ]

                if is_critical:
                    severity = "CRITICAL"
                    result.critical_findings += 1
                else:
                    severity = "INFO"

                finding = {
                    "usage_id": usage.usage_id,
                    "ff_id": usage.ff_id,
                    "username": usage.username,
                    "activity_timestamp": activity.get("timestamp", "").isoformat() if isinstance(activity.get("timestamp"), datetime) else str(activity.get("timestamp", "")),
                    "transaction": activity.get("transaction", ""),
                    "transaction_description": activity.get("description", ""),
                    "action": activity.get("action", ""),
                    "object_type": activity.get("object_type", ""),
                    "object_id": activity.get("object_id", ""),
                    "old_value": activity.get("old_value", ""),
                    "new_value": activity.get("new_value", ""),
                    "is_critical": is_critical,
                    "severity": severity,
                }
                findings.append(finding)

        # Sort by timestamp
        findings.sort(key=lambda x: x["activity_timestamp"])

        result.records = findings
        result.total_records = len(findings)

        result.summary = {
            "total_activities": len(findings),
            "critical_activities": result.critical_findings,
            "sessions_analyzed": len(target_usages),
            "by_transaction": self._group_by_field(findings, "transaction"),
        }

        result.execution_time_seconds = (datetime.now() - start_time).total_seconds()

        return result

    def _group_by_field(self, findings: List[Dict], field: str) -> Dict[str, int]:
        """Group by field."""
        groups = {}
        for f in findings:
            key = f.get(field, "Unknown")
            groups[key] = groups.get(key, 0) + 1
        return dict(sorted(groups.items(), key=lambda x: x[1], reverse=True)[:20])


# ============================================================
# EMERGENCY ACCESS SUMMARY
# ============================================================

class EmergencyAccessSummary:
    """
    Executive summary of emergency access.

    For management reporting and audit committees.
    """

    def __init__(
        self,
        ff_provider: Optional[Callable] = None,
        usage_provider: Optional[Callable] = None
    ):
        self._ff_provider = ff_provider or (lambda: [])
        self._usage_provider = usage_provider or (lambda: [])

    def execute(self, months: int = 6) -> ReportResult:
        """Generate executive summary."""
        result = ReportResult(
            report_type="EMERGENCY_ACCESS_SUMMARY",
            report_name=f"Emergency Access Summary ({months} Months)",
        )

        start_time = datetime.now()
        cutoff = datetime.now() - timedelta(days=months * 30)

        ff_ids = list(self._ff_provider())
        usages = [u for u in self._usage_provider() if u.checkout_time >= cutoff]

        # Monthly breakdown
        monthly_usage: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {"count": 0, "duration": 0, "users": set(), "reviewed": 0}
        )

        for usage in usages:
            month = usage.checkout_time.strftime("%Y-%m")
            monthly_usage[month]["count"] += 1
            monthly_usage[month]["duration"] += usage.duration_minutes
            monthly_usage[month]["users"].add(usage.user_id)
            if usage.reviewed:
                monthly_usage[month]["reviewed"] += 1

        # Build trend
        monthly_records = []
        for month, data in sorted(monthly_usage.items()):
            monthly_records.append({
                "month": month,
                "usage_count": data["count"],
                "total_duration_hours": data["duration"] / 60,
                "unique_users": len(data["users"]),
                "reviewed_count": data["reviewed"],
                "review_rate": data["reviewed"] / data["count"] * 100 if data["count"] else 0,
            })

        # Overall metrics
        total_usages = len(usages)
        total_reviewed = sum(1 for u in usages if u.reviewed)
        total_duration = sum(u.duration_minutes for u in usages)

        # Firefighter ID analysis
        ff_usage = defaultdict(int)
        for usage in usages:
            ff_usage[usage.ff_id] += 1

        most_used = sorted(ff_usage.items(), key=lambda x: x[1], reverse=True)[:5]

        # User analysis
        user_usage = defaultdict(int)
        for usage in usages:
            user_usage[usage.user_id] += 1

        top_users = sorted(user_usage.items(), key=lambda x: x[1], reverse=True)[:5]

        summary_record = {
            "period_months": months,
            "total_usages": total_usages,
            "total_duration_hours": total_duration / 60,
            "avg_duration_minutes": total_duration / total_usages if total_usages else 0,
            "review_completion_rate": total_reviewed / total_usages * 100 if total_usages else 0,
            "active_firefighter_ids": len([ff for ff in ff_ids if ff.is_active]),
            "total_firefighter_ids": len(ff_ids),
            "monthly_trend": monthly_records,
            "most_used_ff_ids": [{"ff_id": f, "count": c} for f, c in most_used],
            "top_users": [{"user_id": u, "count": c} for u, c in top_users],
        }

        # Risk assessment
        if total_usages > 0:
            if total_reviewed / total_usages < 0.8:
                summary_record["risk_flag"] = "LOW_REVIEW_RATE"
                result.high_findings += 1

        result.records = [summary_record]
        result.total_records = 1

        result.summary = {
            "total_usages": total_usages,
            "review_rate": total_reviewed / total_usages * 100 if total_usages else 0,
            "trend": "INCREASING" if len(monthly_records) >= 2 and monthly_records[-1]["usage_count"] > monthly_records[-2]["usage_count"] else "STABLE",
        }

        result.execution_time_seconds = (datetime.now() - start_time).total_seconds()

        return result


# ============================================================
# SUPERUSER ACTIVITY REPORT
# ============================================================

class SuperuserActivityReport:
    """
    Report on superuser/admin activity.

    Covers both firefighter and standing privileged access.
    """

    def __init__(
        self,
        user_provider: Optional[Callable] = None,
        activity_provider: Optional[Callable] = None
    ):
        self._user_provider = user_provider or (lambda: [])
        self._activity_provider = activity_provider or (lambda: [])

    SUPERUSER_INDICATORS = [
        "SAP_ALL", "SAP_NEW", "S_A.ADMIN", "ADMIN", "SUPER",
        "FULL_ACCESS", "BASIS", "DEVELOPER"
    ]

    def execute(self, days: int = 30) -> ReportResult:
        """Report on superuser activity."""
        result = ReportResult(
            report_type="SUPERUSER_ACTIVITY",
            report_name=f"Superuser Activity Report (Last {days} Days)",
        )

        start_time = datetime.now()
        cutoff = datetime.now() - timedelta(days=days)

        users = list(self._user_provider())
        activities = self._activity_provider()

        # Identify superusers
        superusers = []
        for user in users:
            is_super = any(
                pattern.lower() in role.lower()
                for role in user.roles
                for pattern in self.SUPERUSER_INDICATORS
            ) or user.is_privileged if hasattr(user, 'is_privileged') else False

            if is_super:
                superusers.append(user)

        superuser_ids = {u.user_id for u in superusers}

        # Filter activities
        super_activities = [
            a for a in activities
            if a.get("user_id") in superuser_ids and
            a.get("timestamp", datetime.min) >= cutoff
        ]

        # Build findings
        findings = []
        for activity in super_activities:
            user = next((u for u in superusers if u.user_id == activity.get("user_id")), None)

            # Critical activity check
            is_critical = activity.get("transaction", "") in [
                "SU01", "PFCG", "SE16N", "SE38", "SM59", "STMS"
            ]

            if is_critical:
                result.critical_findings += 1

            finding = {
                "user_id": activity.get("user_id", ""),
                "username": user.username if user else "",
                "user_type": user.user_type.value if user else "",
                "timestamp": activity.get("timestamp", "").isoformat() if isinstance(activity.get("timestamp"), datetime) else str(activity.get("timestamp", "")),
                "transaction": activity.get("transaction", ""),
                "action": activity.get("action", ""),
                "is_critical": is_critical,
            }
            findings.append(finding)

        # Sort by timestamp
        findings.sort(key=lambda x: x["timestamp"], reverse=True)

        result.records = findings
        result.total_records = len(findings)

        result.summary = {
            "superuser_count": len(superusers),
            "total_activities": len(findings),
            "critical_activities": result.critical_findings,
            "by_user": self._group_by_field(findings, "username"),
            "by_transaction": self._group_by_field(findings, "transaction"),
        }

        result.execution_time_seconds = (datetime.now() - start_time).total_seconds()

        return result

    def _group_by_field(self, findings: List[Dict], field: str) -> Dict[str, int]:
        """Group by field."""
        groups = {}
        for f in findings:
            key = f.get(field, "Unknown")
            groups[key] = groups.get(key, 0) + 1
        return dict(sorted(groups.items(), key=lambda x: x[1], reverse=True)[:10])


# ============================================================
# PRIVILEGED ACCESS REVIEW
# ============================================================

class PrivilegedAccessReview:
    """
    Comprehensive privileged access review.

    Combines:
    - Firefighter IDs
    - Superuser roles
    - Standing privileged access
    """

    def __init__(
        self,
        ff_provider: Optional[Callable] = None,
        user_provider: Optional[Callable] = None,
        role_provider: Optional[Callable] = None
    ):
        self._ff_provider = ff_provider or (lambda: [])
        self._user_provider = user_provider or (lambda: [])
        self._role_provider = role_provider or (lambda: [])

    def execute(self) -> ReportResult:
        """Generate privileged access review."""
        result = ReportResult(
            report_type="PRIVILEGED_ACCESS_REVIEW",
            report_name="Privileged Access Review",
        )

        start_time = datetime.now()

        ff_ids = list(self._ff_provider())
        users = list(self._user_provider())
        roles = {r.role_id: r for r in self._role_provider()}

        findings = []

        # 1. Firefighter ID holders
        for ff in ff_ids:
            for assigned_user in ff.assigned_users:
                user = next((u for u in users if u.user_id == assigned_user), None)
                finding = {
                    "access_type": "FIREFIGHTER",
                    "ff_id": ff.ff_id,
                    "ff_name": ff.ff_name,
                    "user_id": assigned_user,
                    "username": user.username if user else assigned_user,
                    "department": user.department if user else "",
                    "owner": ff.owner_name,
                    "risk_level": "CRITICAL",
                    "last_reviewed": ff.last_reviewed if hasattr(ff, 'last_reviewed') else None,
                    "requires_review": True,
                }
                findings.append(finding)
                result.critical_findings += 1

        # 2. Users with critical roles
        critical_patterns = ["SAP_ALL", "SAP_NEW", "ADMIN", "SUPER", "DEVELOPER", "BASIS"]
        for user in users:
            if user.status != UserStatus.ACTIVE:
                continue

            for role_id in user.roles:
                role = roles.get(role_id)
                if not role:
                    continue

                is_critical = role.is_critical or any(
                    p.lower() in role.role_name.lower() for p in critical_patterns
                )

                if is_critical:
                    finding = {
                        "access_type": "CRITICAL_ROLE",
                        "role_id": role_id,
                        "role_name": role.role_name,
                        "user_id": user.user_id,
                        "username": user.username,
                        "department": user.department,
                        "owner": role.owner,
                        "risk_level": "HIGH",
                        "last_reviewed": role.last_reviewed.isoformat() if role.last_reviewed else None,
                        "requires_review": not role.last_reviewed or (date.today() - role.last_reviewed).days > 90,
                    }
                    findings.append(finding)
                    result.high_findings += 1

        result.records = findings
        result.total_records = len(findings)

        # Summary
        ff_holders = sum(1 for f in findings if f["access_type"] == "FIREFIGHTER")
        critical_role_holders = sum(1 for f in findings if f["access_type"] == "CRITICAL_ROLE")
        needs_review = sum(1 for f in findings if f["requires_review"])

        result.summary = {
            "total_privileged_access": len(findings),
            "firefighter_holders": ff_holders,
            "critical_role_holders": critical_role_holders,
            "unique_users": len(set(f["user_id"] for f in findings)),
            "requires_review": needs_review,
            "review_overdue_pct": needs_review / len(findings) * 100 if findings else 0,
        }

        result.execution_time_seconds = (datetime.now() - start_time).total_seconds()

        return result
