# Change Logs for User & Role Maintenance
# Critical Audit Trail

"""
Change Log Reports for GOVERNEX+.

SAP Equivalent: SM21, SUIM > Environment > Changes

AUDIT REQUIREMENT:
Every change to users, roles, and authorizations must be traceable.

Questions auditors ask:
- Who changed what?
- When did they change it?
- What was the old value?
- Was it authorized?
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, date, timedelta
from collections import defaultdict

from .models import (
    User, Role, ChangeLogEntry, ChangeType, RiskLevel, ReportResult
)


# ============================================================
# USER CHANGE LOG
# ============================================================

class UserChangeLog:
    """
    Changes to user master records.

    SAP Equivalent: SUIM > Environment > Changes to User Master Records

    TRACKS:
    - User creation
    - User deletion/lock
    - Role assignments
    - Parameter changes
    - Password resets
    """

    def __init__(self, change_provider: Optional[Callable] = None):
        self._change_provider = change_provider or (lambda: [])

    def execute(
        self,
        days: int = 90,
        user_ids: Optional[List[str]] = None,
        change_types: Optional[List[ChangeType]] = None,
        changed_by: Optional[str] = None
    ) -> ReportResult:
        """
        Generate user change log.

        Args:
            days: Number of days to look back
            user_ids: Filter to specific users
            change_types: Filter to specific change types
            changed_by: Filter to changes made by specific user
        """
        result = ReportResult(
            report_type="USER_CHANGE_LOG",
            report_name=f"User Change Log (Last {days} Days)",
        )

        start_time = datetime.now()
        cutoff = datetime.now() - timedelta(days=days)

        changes = self._change_provider()

        # Filter changes
        filtered = []
        for change in changes:
            if change.object_type != "USER":
                continue
            if change.changed_at < cutoff:
                continue
            if user_ids and change.object_id not in user_ids:
                continue
            if change_types and change.change_type not in change_types:
                continue
            if changed_by and change.changed_by != changed_by:
                continue
            filtered.append(change)

        # Build findings
        findings = []
        for change in filtered:
            # Classify severity
            if change.change_type == ChangeType.CREATE:
                severity = "MEDIUM"
                result.medium_findings += 1
            elif change.change_type == ChangeType.DELETE:
                severity = "HIGH"
                result.high_findings += 1
            elif change.field_changed in ["roles", "profiles", "authorizations"]:
                severity = "HIGH"
                result.high_findings += 1
            elif change.field_changed == "password":
                severity = "MEDIUM"
                result.medium_findings += 1
            elif change.change_type == ChangeType.UNLOCK:
                severity = "MEDIUM"
                result.medium_findings += 1
            else:
                severity = "LOW"
                result.low_findings += 1

            finding = {
                "change_id": change.log_id,
                "user_id": change.object_id,
                "username": change.object_name,
                "change_type": change.change_type.value,
                "field_changed": change.field_changed,
                "old_value": change.old_value,
                "new_value": change.new_value,
                "changed_by": change.changed_by,
                "changed_at": change.changed_at.isoformat(),
                "request_id": change.request_id,
                "reason": change.reason,
                "severity": severity,
            }
            findings.append(finding)

        # Sort by timestamp descending
        findings.sort(key=lambda x: x["changed_at"], reverse=True)

        result.records = findings
        result.total_records = len(findings)

        # Build summary
        result.summary = {
            "total_changes": len(findings),
            "by_change_type": self._group_by_field(findings, "change_type"),
            "by_field_changed": self._group_by_field(findings, "field_changed"),
            "by_changed_by": self._group_by_field(findings, "changed_by"),
            "unique_users_changed": len(set(f["user_id"] for f in findings)),
            "user_creations": sum(1 for f in findings if f["change_type"] == "CREATE"),
            "user_deletions": sum(1 for f in findings if f["change_type"] == "DELETE"),
            "role_changes": sum(1 for f in findings if "role" in f["field_changed"].lower()),
        }

        result.execution_time_seconds = (datetime.now() - start_time).total_seconds()
        result.parameters = {
            "days": days,
            "user_ids": user_ids,
            "change_types": [c.value for c in change_types] if change_types else None,
        }

        return result

    def _group_by_field(self, findings: List[Dict], field: str) -> Dict[str, int]:
        """Group findings by field."""
        groups = {}
        for f in findings:
            key = f.get(field, "Unknown")
            groups[key] = groups.get(key, 0) + 1
        return dict(sorted(groups.items(), key=lambda x: x[1], reverse=True))


# ============================================================
# ROLE CHANGE LOG
# ============================================================

class RoleChangeLog:
    """
    Changes to role definitions.

    SAP Equivalent: PFCG > Changes tab

    TRACKS:
    - Role creation/deletion
    - Transaction changes
    - Authorization changes
    - Profile generation
    """

    def __init__(self, change_provider: Optional[Callable] = None):
        self._change_provider = change_provider or (lambda: [])

    def execute(
        self,
        days: int = 90,
        role_ids: Optional[List[str]] = None,
        critical_only: bool = False
    ) -> ReportResult:
        """Generate role change log."""
        result = ReportResult(
            report_type="ROLE_CHANGE_LOG",
            report_name=f"Role Change Log (Last {days} Days)",
        )

        start_time = datetime.now()
        cutoff = datetime.now() - timedelta(days=days)

        changes = self._change_provider()

        # Filter changes
        filtered = []
        for change in changes:
            if change.object_type != "ROLE":
                continue
            if change.changed_at < cutoff:
                continue
            if role_ids and change.object_id not in role_ids:
                continue
            filtered.append(change)

        # Build findings
        findings = []
        for change in filtered:
            # Classify severity
            if change.change_type == ChangeType.CREATE:
                severity = "HIGH"
                result.high_findings += 1
            elif change.change_type == ChangeType.DELETE:
                severity = "CRITICAL"
                result.critical_findings += 1
            elif change.field_changed in ["authorization", "auth_object", "auth_value"]:
                severity = "HIGH"
                result.high_findings += 1
            elif change.field_changed == "transaction":
                severity = "MEDIUM"
                result.medium_findings += 1
            else:
                severity = "LOW"
                result.low_findings += 1

            if critical_only and severity not in ["CRITICAL", "HIGH"]:
                continue

            finding = {
                "change_id": change.log_id,
                "role_id": change.object_id,
                "role_name": change.object_name,
                "change_type": change.change_type.value,
                "field_changed": change.field_changed,
                "old_value": change.old_value,
                "new_value": change.new_value,
                "changed_by": change.changed_by,
                "changed_at": change.changed_at.isoformat(),
                "severity": severity,
            }
            findings.append(finding)

        findings.sort(key=lambda x: x["changed_at"], reverse=True)

        result.records = findings
        result.total_records = len(findings)

        result.summary = {
            "total_changes": len(findings),
            "by_change_type": self._group_by_field(findings, "change_type"),
            "by_field_changed": self._group_by_field(findings, "field_changed"),
            "unique_roles_changed": len(set(f["role_id"] for f in findings)),
            "role_creations": sum(1 for f in findings if f["change_type"] == "CREATE"),
            "role_deletions": sum(1 for f in findings if f["change_type"] == "DELETE"),
            "authorization_changes": sum(1 for f in findings if "auth" in f["field_changed"].lower()),
        }

        result.execution_time_seconds = (datetime.now() - start_time).total_seconds()

        return result

    def _group_by_field(self, findings: List[Dict], field: str) -> Dict[str, int]:
        """Group by field."""
        groups = {}
        for f in findings:
            key = f.get(field, "Unknown")
            groups[key] = groups.get(key, 0) + 1
        return dict(sorted(groups.items(), key=lambda x: x[1], reverse=True))


# ============================================================
# AUTHORIZATION CHANGE LOG
# ============================================================

class AuthorizationChangeLog:
    """
    Changes to authorization values.

    Detailed tracking of authorization modifications.
    """

    def __init__(self, change_provider: Optional[Callable] = None):
        self._change_provider = change_provider or (lambda: [])

    def execute(
        self,
        days: int = 90,
        auth_objects: Optional[List[str]] = None
    ) -> ReportResult:
        """Generate authorization change log."""
        result = ReportResult(
            report_type="AUTHORIZATION_CHANGE_LOG",
            report_name=f"Authorization Change Log (Last {days} Days)",
        )

        start_time = datetime.now()
        cutoff = datetime.now() - timedelta(days=days)

        changes = self._change_provider()

        # Filter to authorization-related changes
        filtered = []
        for change in changes:
            if change.changed_at < cutoff:
                continue
            if "auth" not in change.field_changed.lower() and change.object_type != "AUTHORIZATION":
                continue
            if auth_objects and change.object_id not in auth_objects:
                continue
            filtered.append(change)

        # Build findings
        findings = []
        for change in filtered:
            # Check if it's a critical auth object
            critical_objects = ["S_TABU_CLI", "S_DEVELOP", "S_ADMI_FCD", "S_USER_GRP"]
            is_critical = any(obj in str(change.object_id) or obj in str(change.field_changed) for obj in critical_objects)

            if is_critical:
                severity = "CRITICAL"
                result.critical_findings += 1
            else:
                severity = "HIGH"
                result.high_findings += 1

            finding = {
                "change_id": change.log_id,
                "object_type": change.object_type,
                "object_id": change.object_id,
                "field_changed": change.field_changed,
                "old_value": change.old_value,
                "new_value": change.new_value,
                "changed_by": change.changed_by,
                "changed_at": change.changed_at.isoformat(),
                "is_critical": is_critical,
                "severity": severity,
            }
            findings.append(finding)

        findings.sort(key=lambda x: x["changed_at"], reverse=True)

        result.records = findings
        result.total_records = len(findings)

        result.summary = {
            "total_changes": len(findings),
            "critical_changes": result.critical_findings,
            "by_object": self._group_by_field(findings, "object_id"),
            "by_changed_by": self._group_by_field(findings, "changed_by"),
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
# ACCESS CHANGE TIMELINE
# ============================================================

class AccessChangeTimeline:
    """
    Timeline view of access changes.

    Shows all access-related changes in chronological order.
    """

    def __init__(self, change_provider: Optional[Callable] = None):
        self._change_provider = change_provider or (lambda: [])

    def execute(
        self,
        user_id: Optional[str] = None,
        days: int = 365
    ) -> ReportResult:
        """
        Generate access change timeline.

        Args:
            user_id: Specific user to track
            days: Time period
        """
        result = ReportResult(
            report_type="ACCESS_TIMELINE",
            report_name=f"Access Change Timeline" + (f" for {user_id}" if user_id else ""),
        )

        start_time = datetime.now()
        cutoff = datetime.now() - timedelta(days=days)

        changes = self._change_provider()

        # Filter changes
        filtered = []
        for change in changes:
            if change.changed_at < cutoff:
                continue

            # Include access-related changes
            is_access_related = (
                change.object_type in ["USER", "ROLE", "ASSIGNMENT", "AUTHORIZATION"] or
                change.change_type in [ChangeType.ASSIGN, ChangeType.UNASSIGN] or
                "role" in change.field_changed.lower() or
                "auth" in change.field_changed.lower()
            )

            if not is_access_related:
                continue

            if user_id:
                # If filtering by user, only include changes affecting this user
                if change.object_id != user_id and change.object_type != "USER":
                    continue

            filtered.append(change)

        # Build timeline
        timeline = []
        for change in sorted(filtered, key=lambda x: x.changed_at, reverse=True):
            event = {
                "timestamp": change.changed_at.isoformat(),
                "date": change.changed_at.strftime("%Y-%m-%d"),
                "time": change.changed_at.strftime("%H:%M:%S"),
                "event_type": self._classify_event(change),
                "object_type": change.object_type,
                "object_id": change.object_id,
                "object_name": change.object_name,
                "change_type": change.change_type.value,
                "description": self._build_description(change),
                "changed_by": change.changed_by,
                "request_id": change.request_id,
            }
            timeline.append(event)

        result.records = timeline
        result.total_records = len(timeline)

        # Group by date for visualization
        by_date = defaultdict(int)
        for event in timeline:
            by_date[event["date"]] += 1

        result.summary = {
            "total_events": len(timeline),
            "period_days": days,
            "events_by_date": dict(sorted(by_date.items())),
            "event_types": self._group_by_field(timeline, "event_type"),
        }

        result.execution_time_seconds = (datetime.now() - start_time).total_seconds()

        return result

    def _classify_event(self, change: ChangeLogEntry) -> str:
        """Classify change into event type."""
        if change.change_type == ChangeType.CREATE and change.object_type == "USER":
            return "USER_CREATED"
        elif change.change_type == ChangeType.DELETE and change.object_type == "USER":
            return "USER_DELETED"
        elif change.change_type == ChangeType.ASSIGN:
            return "ROLE_ASSIGNED"
        elif change.change_type == ChangeType.UNASSIGN:
            return "ROLE_REMOVED"
        elif change.change_type == ChangeType.LOCK:
            return "USER_LOCKED"
        elif change.change_type == ChangeType.UNLOCK:
            return "USER_UNLOCKED"
        elif "role" in change.field_changed.lower():
            return "ROLE_MODIFIED"
        elif "auth" in change.field_changed.lower():
            return "AUTHORIZATION_CHANGED"
        else:
            return "OTHER"

    def _build_description(self, change: ChangeLogEntry) -> str:
        """Build human-readable description."""
        if change.change_type == ChangeType.CREATE:
            return f"Created {change.object_type.lower()} '{change.object_name}'"
        elif change.change_type == ChangeType.DELETE:
            return f"Deleted {change.object_type.lower()} '{change.object_name}'"
        elif change.change_type == ChangeType.ASSIGN:
            return f"Assigned to '{change.new_value}'"
        elif change.change_type == ChangeType.UNASSIGN:
            return f"Removed from '{change.old_value}'"
        elif change.change_type == ChangeType.MODIFY:
            return f"Changed {change.field_changed}: '{change.old_value}' → '{change.new_value}'"
        else:
            return f"{change.change_type.value} on {change.object_type}"

    def _group_by_field(self, records: List[Dict], field: str) -> Dict[str, int]:
        """Group by field."""
        groups = {}
        for r in records:
            key = r.get(field, "Unknown")
            groups[key] = groups.get(key, 0) + 1
        return dict(sorted(groups.items(), key=lambda x: x[1], reverse=True))


# ============================================================
# PROVISIONING AUDIT TRAIL
# ============================================================

class ProvisioningAuditTrail:
    """
    Audit trail for access provisioning.

    Links requests → approvals → provisioning → changes.
    """

    def __init__(
        self,
        request_provider: Optional[Callable] = None,
        change_provider: Optional[Callable] = None
    ):
        self._request_provider = request_provider or (lambda: [])
        self._change_provider = change_provider or (lambda: [])

    def execute(
        self,
        days: int = 90,
        request_id: Optional[str] = None
    ) -> ReportResult:
        """Generate provisioning audit trail."""
        result = ReportResult(
            report_type="PROVISIONING_AUDIT",
            report_name="Provisioning Audit Trail",
        )

        start_time = datetime.now()
        cutoff = datetime.now() - timedelta(days=days)

        requests = self._request_provider()
        changes = self._change_provider()

        # Build audit trail
        findings = []

        for request in requests:
            if request.get("submitted_at", datetime.min) < cutoff:
                continue
            if request_id and request.get("request_id") != request_id:
                continue

            # Find related changes
            related_changes = [
                c for c in changes
                if c.request_id == request.get("request_id")
            ]

            trail = {
                "request_id": request.get("request_id"),
                "request_type": request.get("request_type"),
                "requester": request.get("requester_name"),
                "target_user": request.get("target_user_name"),
                "submitted_at": request.get("submitted_at", "").isoformat() if isinstance(request.get("submitted_at"), datetime) else str(request.get("submitted_at", "")),
                "status": request.get("status"),
                "items_requested": request.get("items", []),
                "approvals": request.get("approvals", []),
                "provisioning_events": [
                    {
                        "change_id": c.log_id,
                        "change_type": c.change_type.value,
                        "object": f"{c.object_type}:{c.object_id}",
                        "timestamp": c.changed_at.isoformat(),
                        "changed_by": c.changed_by,
                    }
                    for c in related_changes
                ],
                "is_complete": request.get("status") in ["COMPLETED", "PROVISIONED"],
                "has_provisioning_record": len(related_changes) > 0,
            }

            # Check for anomalies
            if trail["is_complete"] and not trail["has_provisioning_record"]:
                trail["anomaly"] = "COMPLETED_NO_CHANGES"
                result.high_findings += 1

            findings.append(trail)

        result.records = findings
        result.total_records = len(findings)

        result.summary = {
            "total_requests": len(findings),
            "with_provisioning_record": sum(1 for f in findings if f["has_provisioning_record"]),
            "anomalies": sum(1 for f in findings if "anomaly" in f),
            "by_status": self._group_by_field(findings, "status"),
        }

        result.execution_time_seconds = (datetime.now() - start_time).total_seconds()

        return result

    def _group_by_field(self, findings: List[Dict], field: str) -> Dict[str, int]:
        """Group by field."""
        groups = {}
        for f in findings:
            key = f.get(field, "Unknown")
            groups[key] = groups.get(key, 0) + 1
        return groups
