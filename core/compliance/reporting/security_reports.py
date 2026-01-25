# Login & Security Audit Logs
# Evidence of Monitoring and Detection

"""
Security Reports for GOVERNEX+.

SAP Equivalent: SM20 (Security Audit Log), SM19 (Configuration)

AUDIT FOCUS:
- Evidence of monitoring
- Detection capabilities
- Anomaly identification
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, date, timedelta
from collections import defaultdict

from .models import (
    User, LoginEvent, SecurityEvent, UserStatus, RiskLevel, ReportResult
)


# ============================================================
# LOGIN AUDIT REPORT
# ============================================================

class LoginAuditReport:
    """
    Complete login audit report.

    SAP Equivalent: SM20 filtered for login events

    Shows all login activity including:
    - Successful logins
    - Failed logins
    - Logouts
    - Session information
    """

    def __init__(
        self,
        login_provider: Optional[Callable] = None,
        user_provider: Optional[Callable] = None
    ):
        self._login_provider = login_provider or (lambda: [])
        self._user_provider = user_provider or (lambda: [])

    def execute(
        self,
        days: int = 30,
        user_ids: Optional[List[str]] = None,
        include_successful: bool = True,
        include_failed: bool = True
    ) -> ReportResult:
        """
        Generate login audit report.

        Args:
            days: Number of days to look back
            user_ids: Filter to specific users
            include_successful: Include successful logins
            include_failed: Include failed logins
        """
        result = ReportResult(
            report_type="LOGIN_AUDIT",
            report_name=f"Login Audit Report (Last {days} Days)",
        )

        start_time = datetime.now()
        cutoff = datetime.now() - timedelta(days=days)

        logins = self._login_provider()
        users = {u.user_id: u for u in self._user_provider()}

        # Filter logins
        filtered = []
        for login in logins:
            if login.timestamp < cutoff:
                continue
            if user_ids and login.user_id not in user_ids:
                continue
            if not include_successful and login.success:
                continue
            if not include_failed and not login.success:
                continue
            filtered.append(login)

        # Build findings
        findings = []
        for login in filtered:
            user = users.get(login.user_id)

            # Determine severity
            if not login.success:
                severity = "MEDIUM"
                result.medium_findings += 1
            elif login.is_anomalous:
                severity = "HIGH"
                result.high_findings += 1
            else:
                severity = "INFO"
                result.low_findings += 1

            finding = {
                "event_id": login.event_id,
                "user_id": login.user_id,
                "username": login.username,
                "user_status": user.status.value if user else "UNKNOWN",
                "event_type": login.event_type,
                "success": login.success,
                "failure_reason": login.failure_reason,
                "timestamp": login.timestamp.isoformat(),
                "date": login.timestamp.strftime("%Y-%m-%d"),
                "time": login.timestamp.strftime("%H:%M:%S"),
                "ip_address": login.ip_address,
                "client_type": login.client_type,
                "system_id": login.system_id,
                "is_anomalous": login.is_anomalous,
                "anomaly_reasons": login.anomaly_reasons,
                "severity": severity,
            }
            findings.append(finding)

        # Sort by timestamp descending
        findings.sort(key=lambda x: x["timestamp"], reverse=True)

        result.records = findings
        result.total_records = len(findings)

        # Build summary
        successful = sum(1 for f in findings if f["success"])
        failed = sum(1 for f in findings if not f["success"])
        anomalous = sum(1 for f in findings if f["is_anomalous"])

        result.summary = {
            "total_events": len(findings),
            "successful_logins": successful,
            "failed_logins": failed,
            "anomalous_logins": anomalous,
            "unique_users": len(set(f["user_id"] for f in findings)),
            "unique_ips": len(set(f["ip_address"] for f in findings)),
            "by_system": self._group_by_field(findings, "system_id"),
            "by_client_type": self._group_by_field(findings, "client_type"),
            "by_date": self._group_by_field(findings, "date"),
        }

        result.execution_time_seconds = (datetime.now() - start_time).total_seconds()
        result.parameters = {"days": days, "user_ids": user_ids}

        return result

    def _group_by_field(self, findings: List[Dict], field: str) -> Dict[str, int]:
        """Group findings by field."""
        groups = {}
        for f in findings:
            key = f.get(field, "Unknown")
            groups[key] = groups.get(key, 0) + 1
        return dict(sorted(groups.items(), key=lambda x: x[1], reverse=True))


# ============================================================
# FAILED LOGIN REPORT
# ============================================================

class FailedLoginReport:
    """
    Failed login attempts.

    SAP Equivalent: SM20 filtered for failed logins

    CRITICAL FOR:
    - Password guessing detection
    - Brute force attack detection
    - Account lockout monitoring
    """

    def __init__(
        self,
        login_provider: Optional[Callable] = None,
        user_provider: Optional[Callable] = None
    ):
        self._login_provider = login_provider or (lambda: [])
        self._user_provider = user_provider or (lambda: [])

    ATTACK_THRESHOLD = 5  # failures before flagging as potential attack

    def execute(self, days: int = 7) -> ReportResult:
        """Generate failed login report."""
        result = ReportResult(
            report_type="FAILED_LOGINS",
            report_name=f"Failed Login Report (Last {days} Days)",
        )

        start_time = datetime.now()
        cutoff = datetime.now() - timedelta(days=days)

        logins = self._login_provider()
        users = {u.user_id: u for u in self._user_provider()}

        # Filter to failed logins
        failed_logins = [
            login for login in logins
            if not login.success and login.timestamp >= cutoff
        ]

        # Group by user
        user_failures: Dict[str, List[LoginEvent]] = defaultdict(list)
        for login in failed_logins:
            user_failures[login.user_id].append(login)

        # Group by IP
        ip_failures: Dict[str, List[LoginEvent]] = defaultdict(list)
        for login in failed_logins:
            ip_failures[login.ip_address].append(login)

        # Build findings
        findings = []

        # User-based analysis
        for user_id, failures in user_failures.items():
            user = users.get(user_id)
            is_attack = len(failures) >= self.ATTACK_THRESHOLD

            if is_attack:
                severity = "CRITICAL"
                result.critical_findings += 1
            elif len(failures) >= 3:
                severity = "HIGH"
                result.high_findings += 1
            else:
                severity = "MEDIUM"
                result.medium_findings += 1

            finding = {
                "analysis_type": "BY_USER",
                "user_id": user_id,
                "username": failures[0].username,
                "user_status": user.status.value if user else "UNKNOWN",
                "failure_count": len(failures),
                "unique_ips": len(set(f.ip_address for f in failures)),
                "first_failure": min(f.timestamp for f in failures).isoformat(),
                "last_failure": max(f.timestamp for f in failures).isoformat(),
                "failure_reasons": list(set(f.failure_reason for f in failures if f.failure_reason)),
                "is_potential_attack": is_attack,
                "severity": severity,
                "recommendation": "Lock account and investigate" if is_attack else "Monitor",
            }
            findings.append(finding)

        # IP-based analysis (detect distributed attacks)
        for ip, failures in ip_failures.items():
            if len(failures) < self.ATTACK_THRESHOLD:
                continue

            unique_users = set(f.user_id for f in failures)
            is_distributed = len(unique_users) > 3

            finding = {
                "analysis_type": "BY_IP",
                "ip_address": ip,
                "failure_count": len(failures),
                "unique_users_targeted": len(unique_users),
                "first_failure": min(f.timestamp for f in failures).isoformat(),
                "last_failure": max(f.timestamp for f in failures).isoformat(),
                "is_potential_attack": True,
                "is_distributed_attack": is_distributed,
                "severity": "CRITICAL",
                "recommendation": "Block IP and investigate",
            }
            findings.append(finding)
            result.critical_findings += 1

        # Sort by severity and count
        severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
        findings.sort(key=lambda x: (severity_order.get(x["severity"], 4), -x["failure_count"]))

        result.records = findings
        result.total_records = len(findings)

        result.summary = {
            "total_failed_attempts": len(failed_logins),
            "unique_users_affected": len(user_failures),
            "unique_ips": len(ip_failures),
            "potential_attacks": sum(1 for f in findings if f.get("is_potential_attack")),
            "users_to_lock": [
                f["user_id"] for f in findings
                if f.get("analysis_type") == "BY_USER" and f.get("is_potential_attack")
            ],
            "ips_to_block": [
                f["ip_address"] for f in findings
                if f.get("analysis_type") == "BY_IP" and f.get("is_potential_attack")
            ],
        }

        result.execution_time_seconds = (datetime.now() - start_time).total_seconds()

        return result


# ============================================================
# SECURITY EVENT LOG
# ============================================================

class SecurityEventLog:
    """
    General security events.

    SAP Equivalent: SM20 (Security Audit Log)

    Covers all security-relevant events beyond logins.
    """

    def __init__(self, event_provider: Optional[Callable] = None):
        self._event_provider = event_provider or (lambda: [])

    def execute(
        self,
        days: int = 30,
        severity_filter: Optional[List[str]] = None,
        event_types: Optional[List[str]] = None
    ) -> ReportResult:
        """Generate security event log."""
        result = ReportResult(
            report_type="SECURITY_EVENT_LOG",
            report_name=f"Security Event Log (Last {days} Days)",
        )

        start_time = datetime.now()
        cutoff = datetime.now() - timedelta(days=days)

        events = self._event_provider()

        # Filter events
        filtered = []
        for event in events:
            if event.timestamp < cutoff:
                continue
            if severity_filter and event.severity not in severity_filter:
                continue
            if event_types and event.event_type not in event_types:
                continue
            filtered.append(event)

        # Build findings
        findings = []
        for event in filtered:
            if event.severity == "CRITICAL":
                result.critical_findings += 1
            elif event.severity == "WARNING":
                result.high_findings += 1
            else:
                result.low_findings += 1

            finding = {
                "event_id": event.event_id,
                "event_type": event.event_type,
                "severity": event.severity,
                "timestamp": event.timestamp.isoformat(),
                "user_id": event.user_id,
                "username": event.username,
                "description": event.description,
                "system_id": event.system_id,
                "transaction": event.transaction,
                "details": event.details,
                "risk_score": event.risk_score,
            }
            findings.append(finding)

        # Sort by timestamp
        findings.sort(key=lambda x: x["timestamp"], reverse=True)

        result.records = findings
        result.total_records = len(findings)

        result.summary = {
            "total_events": len(findings),
            "by_severity": self._group_by_field(findings, "severity"),
            "by_event_type": self._group_by_field(findings, "event_type"),
            "by_system": self._group_by_field(findings, "system_id"),
            "critical_events": result.critical_findings,
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
# ANOMALOUS ACCESS REPORT
# ============================================================

class AnomalousAccessReport:
    """
    Detect anomalous access patterns.

    Uses behavioral analytics to identify suspicious activity.
    """

    def __init__(
        self,
        login_provider: Optional[Callable] = None,
        activity_provider: Optional[Callable] = None,
        user_provider: Optional[Callable] = None
    ):
        self._login_provider = login_provider or (lambda: [])
        self._activity_provider = activity_provider or (lambda: [])
        self._user_provider = user_provider or (lambda: [])

    def execute(self, days: int = 30) -> ReportResult:
        """Generate anomalous access report."""
        result = ReportResult(
            report_type="ANOMALOUS_ACCESS",
            report_name=f"Anomalous Access Report (Last {days} Days)",
        )

        start_time = datetime.now()
        cutoff = datetime.now() - timedelta(days=days)

        logins = self._login_provider()
        activities = self._activity_provider()
        users = {u.user_id: u for u in self._user_provider()}

        findings = []

        # 1. Unusual time logins (outside business hours)
        for login in logins:
            if login.timestamp < cutoff:
                continue
            hour = login.timestamp.hour
            is_after_hours = hour < 6 or hour > 22
            is_weekend = login.timestamp.weekday() >= 5

            if (is_after_hours or is_weekend) and login.success:
                finding = {
                    "anomaly_type": "UNUSUAL_TIME",
                    "user_id": login.user_id,
                    "username": login.username,
                    "timestamp": login.timestamp.isoformat(),
                    "hour": hour,
                    "is_weekend": is_weekend,
                    "ip_address": login.ip_address,
                    "description": f"Login at unusual time ({login.timestamp.strftime('%H:%M')} on {'weekend' if is_weekend else 'weekday'})",
                    "severity": "MEDIUM",
                    "risk_score": 40,
                }
                findings.append(finding)
                result.medium_findings += 1

        # 2. Unusual IP addresses (for users with established patterns)
        user_ips: Dict[str, set] = defaultdict(set)
        for login in logins:
            if login.success and login.timestamp < cutoff - timedelta(days=30):
                user_ips[login.user_id].add(login.ip_address)

        for login in logins:
            if login.timestamp < cutoff:
                continue
            if login.success and login.ip_address not in user_ips[login.user_id] and len(user_ips[login.user_id]) >= 3:
                finding = {
                    "anomaly_type": "NEW_IP",
                    "user_id": login.user_id,
                    "username": login.username,
                    "timestamp": login.timestamp.isoformat(),
                    "ip_address": login.ip_address,
                    "known_ips": list(user_ips[login.user_id])[:5],
                    "description": f"Login from new IP address {login.ip_address}",
                    "severity": "HIGH",
                    "risk_score": 60,
                }
                findings.append(finding)
                result.high_findings += 1

        # 3. Dormant account activity
        for login in logins:
            if login.timestamp < cutoff:
                continue
            user = users.get(login.user_id)
            if user and user.last_login and login.success:
                days_dormant = (login.timestamp - user.last_login).days
                if days_dormant > 90:
                    finding = {
                        "anomaly_type": "DORMANT_ACCOUNT",
                        "user_id": login.user_id,
                        "username": login.username,
                        "timestamp": login.timestamp.isoformat(),
                        "days_dormant": days_dormant,
                        "description": f"Activity on dormant account (inactive {days_dormant} days)",
                        "severity": "HIGH",
                        "risk_score": 70,
                    }
                    findings.append(finding)
                    result.high_findings += 1

        # 4. Terminated user access
        for login in logins:
            if login.timestamp < cutoff:
                continue
            user = users.get(login.user_id)
            if user and user.status == UserStatus.TERMINATED and login.success:
                finding = {
                    "anomaly_type": "TERMINATED_USER",
                    "user_id": login.user_id,
                    "username": login.username,
                    "timestamp": login.timestamp.isoformat(),
                    "user_status": user.status.value,
                    "termination_date": user.termination_date.isoformat() if user.termination_date else None,
                    "description": "Access by terminated user",
                    "severity": "CRITICAL",
                    "risk_score": 100,
                }
                findings.append(finding)
                result.critical_findings += 1

        # Sort by risk score
        findings.sort(key=lambda x: x["risk_score"], reverse=True)

        result.records = findings
        result.total_records = len(findings)

        result.summary = {
            "total_anomalies": len(findings),
            "by_type": self._group_by_field(findings, "anomaly_type"),
            "by_severity": self._group_by_field(findings, "severity"),
            "unique_users": len(set(f["user_id"] for f in findings)),
            "avg_risk_score": sum(f["risk_score"] for f in findings) / len(findings) if findings else 0,
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


# ============================================================
# COMPLIANCE SCORECARD
# ============================================================

class ComplianceScorecard:
    """
    Overall compliance scorecard.

    Executive summary of compliance posture.
    """

    def __init__(
        self,
        user_report: Optional[Callable] = None,
        sod_report: Optional[Callable] = None,
        ff_report: Optional[Callable] = None,
        login_report: Optional[Callable] = None
    ):
        self._user_report = user_report
        self._sod_report = sod_report
        self._ff_report = ff_report
        self._login_report = login_report

    def execute(self) -> ReportResult:
        """Generate compliance scorecard."""
        result = ReportResult(
            report_type="COMPLIANCE_SCORECARD",
            report_name="Compliance Scorecard",
        )

        start_time = datetime.now()

        # Collect metrics from sub-reports
        metrics = {
            "user_access": self._score_user_access(),
            "sod_compliance": self._score_sod(),
            "privileged_access": self._score_privileged(),
            "monitoring": self._score_monitoring(),
        }

        # Calculate overall score
        overall_score = sum(m["score"] for m in metrics.values()) / len(metrics)

        # Determine rating
        if overall_score >= 90:
            rating = "EXCELLENT"
        elif overall_score >= 75:
            rating = "GOOD"
        elif overall_score >= 60:
            rating = "NEEDS_IMPROVEMENT"
        elif overall_score >= 40:
            rating = "POOR"
        else:
            rating = "CRITICAL"

        scorecard = {
            "report_date": datetime.now().isoformat(),
            "overall_score": overall_score,
            "overall_rating": rating,
            "category_scores": metrics,
            "key_findings": self._get_key_findings(metrics),
            "recommendations": self._get_recommendations(metrics),
            "trend": "STABLE",  # Would compare to previous period
        }

        if overall_score < 60:
            result.critical_findings += 1
        elif overall_score < 75:
            result.high_findings += 1

        result.records = [scorecard]
        result.total_records = 1

        result.summary = {
            "overall_score": overall_score,
            "overall_rating": rating,
            "areas_of_concern": [k for k, v in metrics.items() if v["score"] < 70],
        }

        result.execution_time_seconds = (datetime.now() - start_time).total_seconds()

        return result

    def _score_user_access(self) -> Dict[str, Any]:
        """Score user access management."""
        # Would call actual user report
        # This is a placeholder showing the structure
        return {
            "score": 85,
            "findings": {
                "terminated_users_active": 3,
                "generic_users_unlocked": 1,
                "no_login_90_days": 45,
            },
            "weight": 0.25,
        }

    def _score_sod(self) -> Dict[str, Any]:
        """Score SoD compliance."""
        return {
            "score": 70,
            "findings": {
                "total_violations": 156,
                "critical_violations": 12,
                "unmitigated": 34,
            },
            "weight": 0.30,
        }

    def _score_privileged(self) -> Dict[str, Any]:
        """Score privileged access management."""
        return {
            "score": 80,
            "findings": {
                "ff_review_rate": 92,
                "superuser_count": 15,
                "critical_roles": 8,
            },
            "weight": 0.25,
        }

    def _score_monitoring(self) -> Dict[str, Any]:
        """Score security monitoring."""
        return {
            "score": 75,
            "findings": {
                "anomalies_detected": 23,
                "failed_logins": 456,
                "audit_log_enabled": True,
            },
            "weight": 0.20,
        }

    def _get_key_findings(self, metrics: Dict[str, Any]) -> List[str]:
        """Extract key findings."""
        findings = []

        if metrics["user_access"]["score"] < 70:
            findings.append("User access management needs attention")

        if metrics["sod_compliance"]["findings"]["unmitigated"] > 20:
            findings.append(f"{metrics['sod_compliance']['findings']['unmitigated']} SoD violations without mitigating controls")

        if metrics["sod_compliance"]["findings"]["critical_violations"] > 0:
            findings.append(f"{metrics['sod_compliance']['findings']['critical_violations']} critical SoD violations require immediate remediation")

        return findings

    def _get_recommendations(self, metrics: Dict[str, Any]) -> List[str]:
        """Generate recommendations."""
        recommendations = []

        if metrics["user_access"]["findings"]["terminated_users_active"] > 0:
            recommendations.append("Lock all terminated user accounts immediately")

        if metrics["sod_compliance"]["score"] < 75:
            recommendations.append("Implement role redesign to reduce SoD conflicts")

        if metrics["privileged_access"]["findings"]["ff_review_rate"] < 95:
            recommendations.append("Improve firefighter usage review process")

        recommendations.append("Continue regular access reviews and certifications")

        return recommendations
