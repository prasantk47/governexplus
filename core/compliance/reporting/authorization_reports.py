# Critical & Sensitive Authorization Reports
# Equivalent to SAP SUIM Authorization Analysis

"""
Authorization Reports for GOVERNEX+.

SAP Equivalent: SUIM > User > By Transaction Code
               SUIM > Authorization > Check Object Usage

AUDITOR'S PRIMARY TOOL for answering:
"Who can do sensitive things?"

CRITICAL TRANSACTIONS (Examples):
- Financial: F-02, F-44, FB02, F110, OB52
- Master Data: XK01, XD01, MK01
- Configuration: SPRO, SE16N, SA38, SE11
- Security: SU01, PFCG, SE10
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable, Set
from datetime import datetime, date, timedelta

from .models import (
    User, Role, Transaction, AuthorizationObject,
    RoleAssignment, UserStatus, RiskLevel, ReportResult
)


# ============================================================
# CRITICAL TRANSACTION DEFINITIONS
# ============================================================

# Pre-defined critical transactions by category
CRITICAL_TRANSACTIONS = {
    "FINANCIAL": {
        "F-02": {"name": "Enter G/L Account Document", "risk": "HIGH"},
        "F-44": {"name": "Clear Customer/Vendor", "risk": "HIGH"},
        "FB02": {"name": "Change Document", "risk": "CRITICAL"},
        "F110": {"name": "Automatic Payment Program", "risk": "CRITICAL"},
        "OB52": {"name": "Open/Close Posting Periods", "risk": "CRITICAL"},
        "FBL1N": {"name": "Vendor Line Items", "risk": "MEDIUM"},
        "FBL5N": {"name": "Customer Line Items", "risk": "MEDIUM"},
        "FBCJ": {"name": "Cash Journal", "risk": "HIGH"},
    },
    "MASTER_DATA": {
        "XK01": {"name": "Create Vendor", "risk": "HIGH"},
        "XK02": {"name": "Change Vendor", "risk": "HIGH"},
        "XD01": {"name": "Create Customer", "risk": "MEDIUM"},
        "XD02": {"name": "Change Customer", "risk": "MEDIUM"},
        "MK01": {"name": "Create Purchasing Info Record", "risk": "MEDIUM"},
        "MM01": {"name": "Create Material", "risk": "MEDIUM"},
        "BP": {"name": "Business Partner Maintenance", "risk": "HIGH"},
    },
    "CONFIGURATION": {
        "SPRO": {"name": "IMG/Customizing", "risk": "CRITICAL"},
        "SE16N": {"name": "Direct Table Access", "risk": "CRITICAL"},
        "SE16": {"name": "Data Browser", "risk": "CRITICAL"},
        "SA38": {"name": "ABAP Execute Program", "risk": "CRITICAL"},
        "SE11": {"name": "ABAP Dictionary", "risk": "CRITICAL"},
        "SE37": {"name": "Function Builder", "risk": "HIGH"},
        "SE38": {"name": "ABAP Editor", "risk": "CRITICAL"},
        "SE80": {"name": "Object Navigator", "risk": "CRITICAL"},
        "SM30": {"name": "Table View Maintenance", "risk": "HIGH"},
        "SM31": {"name": "Table Maintenance", "risk": "HIGH"},
    },
    "SECURITY": {
        "SU01": {"name": "User Maintenance", "risk": "CRITICAL"},
        "SU10": {"name": "Mass User Maintenance", "risk": "CRITICAL"},
        "PFCG": {"name": "Role Maintenance", "risk": "CRITICAL"},
        "SU24": {"name": "Auth Object Assignment", "risk": "CRITICAL"},
        "SE10": {"name": "Transport Organizer", "risk": "HIGH"},
        "STMS": {"name": "Transport Management", "risk": "HIGH"},
        "SM21": {"name": "System Log", "risk": "MEDIUM"},
        "SM50": {"name": "Process Overview", "risk": "HIGH"},
        "SM37": {"name": "Job Overview", "risk": "MEDIUM"},
    },
    "BASIS": {
        "SM59": {"name": "RFC Destinations", "risk": "CRITICAL"},
        "STRUST": {"name": "Trust Manager", "risk": "CRITICAL"},
        "RZ10": {"name": "Profile Parameter Maintenance", "risk": "CRITICAL"},
        "RZ11": {"name": "Profile Parameter Display", "risk": "HIGH"},
        "SM19": {"name": "Security Audit Config", "risk": "CRITICAL"},
        "SM20": {"name": "Security Audit Log", "risk": "MEDIUM"},
    },
}

# Critical authorization objects
CRITICAL_AUTH_OBJECTS = {
    "S_TABU_CLI": {"name": "Cross-Client Table Maintenance", "risk": "CRITICAL"},
    "S_TABU_DIS": {"name": "Table Display Authorization", "risk": "HIGH"},
    "S_DEVELOP": {"name": "ABAP Workbench", "risk": "CRITICAL"},
    "S_ADMI_FCD": {"name": "System Administration Functions", "risk": "CRITICAL"},
    "S_USER_AGR": {"name": "User Master Maintenance - Role Assignment", "risk": "CRITICAL"},
    "S_USER_GRP": {"name": "User Master Maintenance - User Groups", "risk": "HIGH"},
    "S_USER_PRO": {"name": "User Master Maintenance - Profiles", "risk": "CRITICAL"},
    "S_USER_AUT": {"name": "User Master Maintenance - Authorizations", "risk": "CRITICAL"},
    "S_TCODE": {"name": "Transaction Code Check", "risk": "HIGH"},
    "S_PROGRAM": {"name": "ABAP Program Check", "risk": "HIGH"},
    "S_RFC": {"name": "RFC Authorization", "risk": "HIGH"},
    "S_DATASET": {"name": "File Access", "risk": "HIGH"},
    "S_PATH": {"name": "File Path Access", "risk": "HIGH"},
    "S_CTS_ADMI": {"name": "CTS Administration", "risk": "CRITICAL"},
    "S_TRANSPRT": {"name": "Transport Authorization", "risk": "HIGH"},
}


# ============================================================
# CRITICAL TRANSACTION REPORT
# ============================================================

class CriticalTransactionReport:
    """
    Users with access to critical transactions.

    SAP Equivalent: SUIM > User > By Transaction Code

    THIS IS A TOP AUDITOR REQUEST.
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
        transactions: Optional[List[str]] = None,
        categories: Optional[List[str]] = None,
        include_inactive_users: bool = False
    ) -> ReportResult:
        """
        Find all users with access to specified critical transactions.

        Args:
            transactions: Specific T-codes to check (e.g., ["SU01", "F110"])
            categories: Categories to check (e.g., ["FINANCIAL", "SECURITY"])
            include_inactive_users: Include locked/expired users
        """
        result = ReportResult(
            report_type="CRITICAL_TRANSACTIONS",
            report_name="Users with Critical Transaction Access",
        )

        start_time = datetime.now()

        # Build list of transactions to check
        tcodes_to_check = self._build_tcode_list(transactions, categories)

        users = {u.user_id: u for u in self._user_provider()}
        roles = {r.role_id: r for r in self._role_provider()}
        assignments = self._assignment_provider()

        # Build user-to-transactions mapping
        user_transactions = self._map_user_transactions(
            users, roles, assignments, tcodes_to_check, include_inactive_users
        )

        findings = []
        for user_id, user_tcodes in user_transactions.items():
            user = users.get(user_id)
            if not user:
                continue

            for tcode, details in user_tcodes.items():
                tcode_info = self._get_tcode_info(tcode)
                risk = tcode_info.get("risk", "MEDIUM")

                # Determine severity
                if risk == "CRITICAL":
                    severity = "CRITICAL"
                    result.critical_findings += 1
                elif risk == "HIGH":
                    severity = "HIGH"
                    result.high_findings += 1
                else:
                    severity = "MEDIUM"
                    result.medium_findings += 1

                finding = {
                    "transaction_code": tcode,
                    "transaction_name": tcode_info.get("name", "Unknown"),
                    "transaction_category": details.get("category", "OTHER"),
                    "transaction_risk": risk,
                    "user_id": user.user_id,
                    "username": user.username,
                    "full_name": user.full_name,
                    "department": user.department,
                    "user_status": user.status.value,
                    "user_type": user.user_type.value,
                    "access_via_role": details.get("role_id", ""),
                    "role_name": details.get("role_name", ""),
                    "last_login": user.last_login.isoformat() if user.last_login else None,
                    "severity": severity,
                }
                findings.append(finding)

        result.total_records = len(findings)
        result.records = findings

        # Summary
        result.summary = {
            "transactions_checked": len(tcodes_to_check),
            "total_findings": len(findings),
            "unique_users": len(set(f["user_id"] for f in findings)),
            "by_transaction": self._summarize_by_tcode(findings),
            "by_category": self._summarize_by_category(findings),
            "by_department": self._summarize_by_field(findings, "department"),
        }

        result.execution_time_seconds = (datetime.now() - start_time).total_seconds()
        result.parameters = {"transactions": transactions, "categories": categories}

        return result

    def _build_tcode_list(
        self,
        transactions: Optional[List[str]],
        categories: Optional[List[str]]
    ) -> Set[str]:
        """Build list of T-codes to check."""
        tcodes = set()

        if transactions:
            tcodes.update(transactions)

        if categories:
            for cat in categories:
                if cat in CRITICAL_TRANSACTIONS:
                    tcodes.update(CRITICAL_TRANSACTIONS[cat].keys())

        # If nothing specified, use all critical transactions
        if not tcodes:
            for cat_tcodes in CRITICAL_TRANSACTIONS.values():
                tcodes.update(cat_tcodes.keys())

        return tcodes

    def _map_user_transactions(
        self,
        users: Dict[str, User],
        roles: Dict[str, Role],
        assignments: List[RoleAssignment],
        tcodes: Set[str],
        include_inactive: bool
    ) -> Dict[str, Dict[str, Any]]:
        """Map users to their transactions."""
        user_tcodes: Dict[str, Dict[str, Any]] = {}

        for assignment in assignments:
            if not assignment.is_active:
                continue

            user = users.get(assignment.user_id)
            role = roles.get(assignment.role_id)

            if not user or not role:
                continue

            # Filter inactive users
            if not include_inactive and user.status != UserStatus.ACTIVE:
                continue

            # Check role transactions
            for tcode in role.transactions:
                if tcode in tcodes:
                    if user.user_id not in user_tcodes:
                        user_tcodes[user.user_id] = {}

                    if tcode not in user_tcodes[user.user_id]:
                        category = self._get_tcode_category(tcode)
                        user_tcodes[user.user_id][tcode] = {
                            "role_id": role.role_id,
                            "role_name": role.role_name,
                            "category": category,
                        }

        return user_tcodes

    def _get_tcode_info(self, tcode: str) -> Dict[str, str]:
        """Get transaction information."""
        for category, tcodes in CRITICAL_TRANSACTIONS.items():
            if tcode in tcodes:
                return {**tcodes[tcode], "category": category}
        return {"name": "Unknown", "risk": "MEDIUM", "category": "OTHER"}

    def _get_tcode_category(self, tcode: str) -> str:
        """Get transaction category."""
        for category, tcodes in CRITICAL_TRANSACTIONS.items():
            if tcode in tcodes:
                return category
        return "OTHER"

    def _summarize_by_tcode(self, findings: List[Dict]) -> Dict[str, int]:
        """Summarize findings by transaction."""
        summary = {}
        for f in findings:
            tcode = f["transaction_code"]
            summary[tcode] = summary.get(tcode, 0) + 1
        return dict(sorted(summary.items(), key=lambda x: x[1], reverse=True))

    def _summarize_by_category(self, findings: List[Dict]) -> Dict[str, int]:
        """Summarize findings by category."""
        summary = {}
        for f in findings:
            cat = f["transaction_category"]
            summary[cat] = summary.get(cat, 0) + 1
        return summary

    def _summarize_by_field(self, findings: List[Dict], field: str) -> Dict[str, int]:
        """Summarize findings by field."""
        summary = {}
        for f in findings:
            val = f.get(field, "Unknown")
            summary[val] = summary.get(val, 0) + 1
        return summary


# ============================================================
# AUTHORIZATION OBJECT REPORT
# ============================================================

class AuthorizationObjectReport:
    """
    Analyze authorization objects.

    SAP Equivalent: SUIM > Authorization > Check Object Usage

    Finds which roles/profiles contain powerful authorization objects.
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
        auth_objects: Optional[List[str]] = None,
        include_all_critical: bool = True
    ) -> ReportResult:
        """
        Find all users/roles with specified authorization objects.

        Args:
            auth_objects: Specific objects to check
            include_all_critical: Include all predefined critical objects
        """
        result = ReportResult(
            report_type="AUTHORIZATION_OBJECTS",
            report_name="Authorization Object Analysis",
        )

        start_time = datetime.now()

        # Build list of auth objects to check
        objects_to_check = set(auth_objects or [])
        if include_all_critical or not objects_to_check:
            objects_to_check.update(CRITICAL_AUTH_OBJECTS.keys())

        users = {u.user_id: u for u in self._user_provider()}
        roles = list(self._role_provider())
        assignments = self._assignment_provider()

        findings = []

        # Find roles with these auth objects
        for role in roles:
            role_auth_objects = set(role.authorization_objects)
            matching_objects = role_auth_objects & objects_to_check

            if not matching_objects:
                continue

            # Find users with this role
            role_assignments = [a for a in assignments if a.role_id == role.role_id and a.is_active]

            for auth_obj in matching_objects:
                obj_info = CRITICAL_AUTH_OBJECTS.get(auth_obj, {"name": "Unknown", "risk": "MEDIUM"})

                # Count users
                for assignment in role_assignments:
                    user = users.get(assignment.user_id)
                    if not user or user.status != UserStatus.ACTIVE:
                        continue

                    risk = obj_info.get("risk", "MEDIUM")
                    if risk == "CRITICAL":
                        result.critical_findings += 1
                    elif risk == "HIGH":
                        result.high_findings += 1

                    finding = {
                        "auth_object": auth_obj,
                        "auth_object_name": obj_info.get("name", "Unknown"),
                        "auth_object_risk": obj_info.get("risk", "MEDIUM"),
                        "role_id": role.role_id,
                        "role_name": role.role_name,
                        "user_id": user.user_id,
                        "username": user.username,
                        "department": user.department,
                    }
                    findings.append(finding)

        result.total_records = len(findings)
        result.records = findings

        result.summary = {
            "objects_checked": len(objects_to_check),
            "total_findings": len(findings),
            "by_auth_object": self._summarize_by_field(findings, "auth_object"),
            "by_role": self._summarize_by_field(findings, "role_name"),
            "unique_users": len(set(f["user_id"] for f in findings)),
        }

        result.execution_time_seconds = (datetime.now() - start_time).total_seconds()

        return result

    def _summarize_by_field(self, findings: List[Dict], field: str) -> Dict[str, int]:
        """Summarize by field."""
        summary = {}
        for f in findings:
            val = f.get(field, "Unknown")
            summary[val] = summary.get(val, 0) + 1
        return summary


# ============================================================
# SENSITIVE ACCESS REPORT
# ============================================================

class SensitiveAccessReport:
    """
    Combined sensitive access report.

    Combines:
    - Critical transactions
    - Critical auth objects
    - User risk scoring
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

        self._tcode_report = CriticalTransactionReport(
            user_provider, role_provider, assignment_provider
        )
        self._auth_report = AuthorizationObjectReport(
            user_provider, role_provider, assignment_provider
        )

    def execute(self) -> ReportResult:
        """Generate comprehensive sensitive access report."""
        result = ReportResult(
            report_type="SENSITIVE_ACCESS",
            report_name="Comprehensive Sensitive Access Report",
        )

        start_time = datetime.now()

        # Run sub-reports
        tcode_result = self._tcode_report.execute()
        auth_result = self._auth_report.execute()

        # Combine unique users
        users_with_critical = set()
        user_risk_details: Dict[str, Dict[str, Any]] = {}

        # Process T-code findings
        for finding in tcode_result.records:
            user_id = finding["user_id"]
            users_with_critical.add(user_id)

            if user_id not in user_risk_details:
                user_risk_details[user_id] = {
                    "username": finding["username"],
                    "department": finding["department"],
                    "critical_transactions": [],
                    "critical_auth_objects": [],
                    "risk_score": 0,
                }

            user_risk_details[user_id]["critical_transactions"].append(
                finding["transaction_code"]
            )
            # Add risk
            if finding["transaction_risk"] == "CRITICAL":
                user_risk_details[user_id]["risk_score"] += 30
            elif finding["transaction_risk"] == "HIGH":
                user_risk_details[user_id]["risk_score"] += 20
            else:
                user_risk_details[user_id]["risk_score"] += 10

        # Process auth object findings
        for finding in auth_result.records:
            user_id = finding["user_id"]
            users_with_critical.add(user_id)

            if user_id not in user_risk_details:
                user_risk_details[user_id] = {
                    "username": finding["username"],
                    "department": finding["department"],
                    "critical_transactions": [],
                    "critical_auth_objects": [],
                    "risk_score": 0,
                }

            user_risk_details[user_id]["critical_auth_objects"].append(
                finding["auth_object"]
            )
            # Add risk
            if finding["auth_object_risk"] == "CRITICAL":
                user_risk_details[user_id]["risk_score"] += 30
            elif finding["auth_object_risk"] == "HIGH":
                user_risk_details[user_id]["risk_score"] += 20

        # Build findings sorted by risk
        findings = []
        for user_id, details in user_risk_details.items():
            # Determine severity
            if details["risk_score"] >= 80:
                severity = "CRITICAL"
                result.critical_findings += 1
            elif details["risk_score"] >= 50:
                severity = "HIGH"
                result.high_findings += 1
            else:
                severity = "MEDIUM"
                result.medium_findings += 1

            findings.append({
                "user_id": user_id,
                "username": details["username"],
                "department": details["department"],
                "risk_score": details["risk_score"],
                "critical_transactions": details["critical_transactions"],
                "critical_transaction_count": len(details["critical_transactions"]),
                "critical_auth_objects": details["critical_auth_objects"],
                "critical_auth_object_count": len(details["critical_auth_objects"]),
                "severity": severity,
            })

        # Sort by risk score
        findings.sort(key=lambda x: x["risk_score"], reverse=True)

        result.total_records = len(findings)
        result.records = findings

        result.summary = {
            "users_with_sensitive_access": len(findings),
            "highest_risk_score": max((f["risk_score"] for f in findings), default=0),
            "by_severity": {
                "CRITICAL": result.critical_findings,
                "HIGH": result.high_findings,
                "MEDIUM": result.medium_findings,
            },
            "most_common_transactions": tcode_result.summary.get("by_transaction", {})[:10] if isinstance(tcode_result.summary.get("by_transaction"), list) else {},
            "most_common_auth_objects": auth_result.summary.get("by_auth_object", {}),
        }

        result.execution_time_seconds = (datetime.now() - start_time).total_seconds()

        return result


# ============================================================
# TRANSACTION USAGE REPORT
# ============================================================

class TransactionUsageReport:
    """
    Track actual usage of transactions.

    CRITICAL FOR:
    - Verifying if sensitive access is being used
    - Detecting unauthorized activity
    - Supporting least privilege
    """

    def __init__(self, usage_provider: Optional[Callable] = None):
        self._usage_provider = usage_provider or (lambda: [])

    def execute(
        self,
        transactions: Optional[List[str]] = None,
        days: int = 90
    ) -> ReportResult:
        """Report on transaction usage."""
        result = ReportResult(
            report_type="TRANSACTION_USAGE",
            report_name=f"Transaction Usage (Last {days} Days)",
        )

        start_time = datetime.now()
        usage_data = self._usage_provider()

        cutoff = datetime.now() - timedelta(days=days)

        # Filter by date and transactions
        filtered_usage = [
            u for u in usage_data
            if u.get("timestamp", datetime.min) >= cutoff
            and (not transactions or u.get("transaction") in transactions)
        ]

        # Aggregate by transaction
        tcode_usage: Dict[str, Dict[str, Any]] = {}
        for usage in filtered_usage:
            tcode = usage.get("transaction", "")
            if tcode not in tcode_usage:
                tcode_usage[tcode] = {
                    "transaction": tcode,
                    "execution_count": 0,
                    "unique_users": set(),
                    "last_executed": None,
                }

            tcode_usage[tcode]["execution_count"] += 1
            tcode_usage[tcode]["unique_users"].add(usage.get("user_id", ""))
            exec_time = usage.get("timestamp")
            if exec_time and (not tcode_usage[tcode]["last_executed"] or exec_time > tcode_usage[tcode]["last_executed"]):
                tcode_usage[tcode]["last_executed"] = exec_time

        # Convert to findings
        findings = []
        for tcode, data in tcode_usage.items():
            tcode_info = self._get_tcode_info(tcode)

            findings.append({
                "transaction": tcode,
                "transaction_name": tcode_info.get("name", "Unknown"),
                "is_critical": tcode in {t for cat in CRITICAL_TRANSACTIONS.values() for t in cat},
                "execution_count": data["execution_count"],
                "unique_users": len(data["unique_users"]),
                "last_executed": data["last_executed"].isoformat() if data["last_executed"] else None,
            })

        findings.sort(key=lambda x: x["execution_count"], reverse=True)

        result.total_records = len(findings)
        result.records = findings

        result.summary = {
            "period_days": days,
            "total_transactions_used": len(findings),
            "total_executions": sum(f["execution_count"] for f in findings),
            "critical_transactions_used": sum(1 for f in findings if f["is_critical"]),
        }

        result.execution_time_seconds = (datetime.now() - start_time).total_seconds()

        return result

    def _get_tcode_info(self, tcode: str) -> Dict[str, str]:
        """Get transaction info."""
        for cat, tcodes in CRITICAL_TRANSACTIONS.items():
            if tcode in tcodes:
                return tcodes[tcode]
        return {"name": "Unknown", "risk": "LOW"}


# ============================================================
# DIRECT TABLE ACCESS REPORT
# ============================================================

class DirectTableAccessReport:
    """
    Direct table access (SE16N, SE16) usage.

    CRITICAL AUDIT CONCERN:
    Direct table access bypasses application controls.
    """

    TABLE_ACCESS_TCODES = ["SE16", "SE16N", "SM30", "SM31"]

    def __init__(
        self,
        user_provider: Optional[Callable] = None,
        role_provider: Optional[Callable] = None,
        assignment_provider: Optional[Callable] = None,
        usage_provider: Optional[Callable] = None
    ):
        self._user_provider = user_provider or (lambda: [])
        self._role_provider = role_provider or (lambda: [])
        self._assignment_provider = assignment_provider or (lambda: [])
        self._usage_provider = usage_provider or (lambda: [])

    def execute(self, days: int = 90) -> ReportResult:
        """Report on direct table access."""
        result = ReportResult(
            report_type="DIRECT_TABLE_ACCESS",
            report_name="Direct Table Access Report",
        )

        start_time = datetime.now()

        # First, find users with access to table maintenance T-codes
        tcode_report = CriticalTransactionReport(
            self._user_provider, self._role_provider, self._assignment_provider
        )

        tcode_result = tcode_report.execute(transactions=self.TABLE_ACCESS_TCODES)

        # Then check actual usage
        usage_data = self._usage_provider()
        cutoff = datetime.now() - timedelta(days=days)

        table_usage = [
            u for u in usage_data
            if u.get("transaction") in self.TABLE_ACCESS_TCODES
            and u.get("timestamp", datetime.min) >= cutoff
        ]

        # Combine access + usage
        user_access: Dict[str, Dict[str, Any]] = {}

        # Add users with access
        for finding in tcode_result.records:
            user_id = finding["user_id"]
            if user_id not in user_access:
                user_access[user_id] = {
                    "user_id": user_id,
                    "username": finding["username"],
                    "department": finding["department"],
                    "has_access": True,
                    "usage_count": 0,
                    "tables_accessed": set(),
                }

        # Add usage data
        for usage in table_usage:
            user_id = usage.get("user_id", "")
            if user_id not in user_access:
                user_access[user_id] = {
                    "user_id": user_id,
                    "username": usage.get("username", ""),
                    "department": "",
                    "has_access": False,  # May have lost access
                    "usage_count": 0,
                    "tables_accessed": set(),
                }

            user_access[user_id]["usage_count"] += 1
            if usage.get("table_name"):
                user_access[user_id]["tables_accessed"].add(usage["table_name"])

        # Build findings
        findings = []
        for user_id, data in user_access.items():
            severity = "HIGH" if data["usage_count"] > 0 else "MEDIUM"
            if severity == "HIGH":
                result.high_findings += 1
            else:
                result.medium_findings += 1

            findings.append({
                "user_id": data["user_id"],
                "username": data["username"],
                "department": data["department"],
                "has_current_access": data["has_access"],
                "usage_count": data["usage_count"],
                "tables_accessed_count": len(data["tables_accessed"]),
                "tables_accessed": list(data["tables_accessed"]),
                "severity": severity,
            })

        findings.sort(key=lambda x: x["usage_count"], reverse=True)

        result.total_records = len(findings)
        result.records = findings

        result.summary = {
            "users_with_access": sum(1 for f in findings if f["has_current_access"]),
            "users_who_used": sum(1 for f in findings if f["usage_count"] > 0),
            "total_table_accesses": sum(f["usage_count"] for f in findings),
            "period_days": days,
        }

        result.execution_time_seconds = (datetime.now() - start_time).total_seconds()

        return result
