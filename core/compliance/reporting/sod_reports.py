# Segregation of Duties (SoD) Reports
# The Core of GRC Audit

"""
SoD Reports for GOVERNEX+.

SAP Equivalent: SAP GRC Access Control Risk Analysis Reports

SEGREGATION OF DUTIES is the heart of access control auditing.
These reports answer: "Who can do conflicting things?"

Examples of SoD:
- Create Vendor + Post Payment = Fraud risk
- Create PO + Approve PO = Procurement fraud
- Create User + Assign Roles = Security bypass
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable, Set, Tuple
from datetime import datetime, date, timedelta
from collections import defaultdict

from .models import (
    User, Role, RoleAssignment, SoDRule, SoDViolation,
    UserStatus, RiskLevel, ReportResult
)


# ============================================================
# PREDEFINED SOD RULES
# ============================================================

STANDARD_SOD_RULES = [
    # Financial SoD
    {
        "rule_id": "FIN-001",
        "name": "Vendor Master + Payment Processing",
        "function_1": "VENDOR_MASTER",
        "function_1_name": "Create/Maintain Vendor Master",
        "function_2": "PAYMENT_PROCESSING",
        "function_2_name": "Process Payments",
        "risk_level": "CRITICAL",
        "business_risk": "User can create fake vendor and pay them (fraud)",
    },
    {
        "rule_id": "FIN-002",
        "name": "Customer Master + AR Posting",
        "function_1": "CUSTOMER_MASTER",
        "function_1_name": "Create/Maintain Customer Master",
        "function_2": "AR_POSTING",
        "function_2_name": "Post AR Documents",
        "risk_level": "HIGH",
        "business_risk": "User can create fake customer and manipulate receivables",
    },
    {
        "rule_id": "FIN-003",
        "name": "GL Posting + Period Control",
        "function_1": "GL_POSTING",
        "function_1_name": "Post GL Documents",
        "function_2": "PERIOD_CONTROL",
        "function_2_name": "Open/Close Posting Periods",
        "risk_level": "HIGH",
        "business_risk": "User can post to closed periods, manipulate financials",
    },
    # Procurement SoD
    {
        "rule_id": "PROC-001",
        "name": "Create PO + Approve PO",
        "function_1": "PO_CREATE",
        "function_1_name": "Create Purchase Orders",
        "function_2": "PO_APPROVE",
        "function_2_name": "Approve Purchase Orders",
        "risk_level": "CRITICAL",
        "business_risk": "User can create and approve own purchase orders",
    },
    {
        "rule_id": "PROC-002",
        "name": "Vendor Master + PO Create",
        "function_1": "VENDOR_MASTER",
        "function_1_name": "Create/Maintain Vendor Master",
        "function_2": "PO_CREATE",
        "function_2_name": "Create Purchase Orders",
        "risk_level": "HIGH",
        "business_risk": "User can create vendor and immediately place orders",
    },
    {
        "rule_id": "PROC-003",
        "name": "Goods Receipt + Invoice Processing",
        "function_1": "GOODS_RECEIPT",
        "function_1_name": "Post Goods Receipt",
        "function_2": "INVOICE_PROCESSING",
        "function_2_name": "Process Vendor Invoices",
        "risk_level": "MEDIUM",
        "business_risk": "User can confirm receipt and process payment",
    },
    # Security SoD
    {
        "rule_id": "SEC-001",
        "name": "User Maintenance + Role Assignment",
        "function_1": "USER_MAINTENANCE",
        "function_1_name": "Create/Maintain Users",
        "function_2": "ROLE_ASSIGNMENT",
        "function_2_name": "Assign Roles to Users",
        "risk_level": "CRITICAL",
        "business_risk": "User can create users and grant access (security bypass)",
    },
    {
        "rule_id": "SEC-002",
        "name": "Role Maintenance + Transport",
        "function_1": "ROLE_MAINTENANCE",
        "function_1_name": "Create/Maintain Roles",
        "function_2": "TRANSPORT_RELEASE",
        "function_2_name": "Release Transports",
        "risk_level": "CRITICAL",
        "business_risk": "User can create roles and transport to production",
    },
    # HR SoD
    {
        "rule_id": "HR-001",
        "name": "HR Master + Payroll",
        "function_1": "HR_MASTER",
        "function_1_name": "Maintain HR Master Data",
        "function_2": "PAYROLL_RUN",
        "function_2_name": "Execute Payroll",
        "risk_level": "CRITICAL",
        "business_risk": "User can modify salary and run payroll",
    },
    # Inventory SoD
    {
        "rule_id": "INV-001",
        "name": "Inventory Posting + Inventory Adjustment",
        "function_1": "INVENTORY_POSTING",
        "function_1_name": "Post Inventory Movements",
        "function_2": "INVENTORY_ADJUSTMENT",
        "function_2_name": "Adjust Inventory",
        "risk_level": "HIGH",
        "business_risk": "User can move and adjust inventory (theft risk)",
    },
]

# Function to Transaction mapping (simplified)
FUNCTION_TCODES = {
    "VENDOR_MASTER": ["XK01", "XK02", "FK01", "FK02", "MK01", "MK02"],
    "PAYMENT_PROCESSING": ["F110", "F-53", "F-58", "FBZP"],
    "CUSTOMER_MASTER": ["XD01", "XD02", "FD01", "FD02"],
    "AR_POSTING": ["FB70", "FBL5N", "F-28"],
    "GL_POSTING": ["F-02", "FB01", "FB50"],
    "PERIOD_CONTROL": ["OB52", "MMRV"],
    "PO_CREATE": ["ME21N", "ME21", "ME22N"],
    "PO_APPROVE": ["ME28", "ME29N"],
    "GOODS_RECEIPT": ["MIGO", "MB01"],
    "INVOICE_PROCESSING": ["MIRO", "FB60"],
    "USER_MAINTENANCE": ["SU01", "SU10", "SU01D"],
    "ROLE_ASSIGNMENT": ["SU01", "PFCG"],
    "ROLE_MAINTENANCE": ["PFCG", "SU24"],
    "TRANSPORT_RELEASE": ["SE10", "SE09", "STMS"],
    "HR_MASTER": ["PA30", "PA20"],
    "PAYROLL_RUN": ["PC00_M99_CALC", "PC00_M40_CALC"],
    "INVENTORY_POSTING": ["MIGO", "MB1A", "MB1B", "MB1C"],
    "INVENTORY_ADJUSTMENT": ["MI04", "MI07", "MI09"],
}


# ============================================================
# SOD CONFLICT REPORT
# ============================================================

class SoDConflictReport:
    """
    Detect SoD conflicts for users.

    THE MOST CRITICAL AUDIT REPORT.
    """

    def __init__(
        self,
        user_provider: Optional[Callable] = None,
        role_provider: Optional[Callable] = None,
        assignment_provider: Optional[Callable] = None,
        custom_rules: Optional[List[SoDRule]] = None
    ):
        self._user_provider = user_provider or (lambda: [])
        self._role_provider = role_provider or (lambda: [])
        self._assignment_provider = assignment_provider or (lambda: [])
        self._rules = self._load_rules(custom_rules)

    def _load_rules(self, custom_rules: Optional[List[SoDRule]]) -> List[SoDRule]:
        """Load SoD rules."""
        rules = []

        # Load standard rules
        for rule_data in STANDARD_SOD_RULES:
            rule = SoDRule(
                rule_id=rule_data["rule_id"],
                rule_name=rule_data["name"],
                function_1=rule_data["function_1"],
                function_1_name=rule_data["function_1_name"],
                function_2=rule_data["function_2"],
                function_2_name=rule_data["function_2_name"],
                risk_level=RiskLevel[rule_data["risk_level"]],
                business_risk=rule_data["business_risk"],
            )
            rules.append(rule)

        # Add custom rules
        if custom_rules:
            rules.extend(custom_rules)

        return rules

    def execute(
        self,
        user_ids: Optional[List[str]] = None,
        departments: Optional[List[str]] = None,
        include_mitigated: bool = True
    ) -> ReportResult:
        """
        Detect SoD conflicts.

        Args:
            user_ids: Specific users to check (None = all)
            departments: Filter by department
            include_mitigated: Include conflicts with mitigating controls
        """
        result = ReportResult(
            report_type="SOD_CONFLICTS",
            report_name="Segregation of Duties Conflict Report",
        )

        start_time = datetime.now()

        users = {u.user_id: u for u in self._user_provider()}
        roles = {r.role_id: r for r in self._role_provider()}
        assignments = self._assignment_provider()

        # Build user-to-functions map
        user_functions = self._build_user_functions(users, roles, assignments)

        # Check each user against each rule
        violations = []
        for user_id, functions in user_functions.items():
            user = users.get(user_id)
            if not user or user.status != UserStatus.ACTIVE:
                continue

            # Apply filters
            if user_ids and user_id not in user_ids:
                continue
            if departments and user.department not in departments:
                continue

            for rule in self._rules:
                if not rule.is_active:
                    continue

                # Check if user has both conflicting functions
                has_func_1 = rule.function_1 in functions
                has_func_2 = rule.function_2 in functions

                if has_func_1 and has_func_2:
                    violation = SoDViolation(
                        rule_id=rule.rule_id,
                        rule_name=rule.rule_name,
                        user_id=user_id,
                        username=user.username,
                        user_department=user.department,
                        function_1=rule.function_1,
                        function_1_source=functions[rule.function_1]["role"],
                        function_2=rule.function_2,
                        function_2_source=functions[rule.function_2]["role"],
                        risk_level=rule.risk_level,
                    )

                    # Calculate risk score
                    if rule.risk_level == RiskLevel.CRITICAL:
                        violation.risk_score = 100
                        result.critical_findings += 1
                    elif rule.risk_level == RiskLevel.HIGH:
                        violation.risk_score = 75
                        result.high_findings += 1
                    elif rule.risk_level == RiskLevel.MEDIUM:
                        violation.risk_score = 50
                        result.medium_findings += 1
                    else:
                        violation.risk_score = 25
                        result.low_findings += 1

                    violations.append(violation)

        # Convert to records
        result.records = [v.to_dict() for v in violations]
        result.total_records = len(violations)

        # Build summary
        result.summary = self._build_summary(violations)

        result.execution_time_seconds = (datetime.now() - start_time).total_seconds()
        result.parameters = {
            "user_ids": user_ids,
            "departments": departments,
            "include_mitigated": include_mitigated,
        }

        return result

    def _build_user_functions(
        self,
        users: Dict[str, User],
        roles: Dict[str, Role],
        assignments: List[RoleAssignment]
    ) -> Dict[str, Dict[str, Dict[str, Any]]]:
        """
        Build mapping of user -> functions they can perform.

        Returns: {user_id: {function: {role: role_id, tcodes: [...]}}}
        """
        user_functions: Dict[str, Dict[str, Dict[str, Any]]] = defaultdict(dict)

        for assignment in assignments:
            if not assignment.is_active:
                continue

            role = roles.get(assignment.role_id)
            if not role:
                continue

            # Check which functions this role provides
            role_tcodes = set(role.transactions)

            for function, tcodes in FUNCTION_TCODES.items():
                if role_tcodes & set(tcodes):
                    # User has this function via this role
                    if function not in user_functions[assignment.user_id]:
                        user_functions[assignment.user_id][function] = {
                            "role": role.role_id,
                            "role_name": role.role_name,
                            "tcodes": list(role_tcodes & set(tcodes)),
                        }

        return dict(user_functions)

    def _build_summary(self, violations: List[SoDViolation]) -> Dict[str, Any]:
        """Build report summary."""
        by_rule = defaultdict(int)
        by_department = defaultdict(int)
        by_risk = defaultdict(int)

        users_with_violations = set()

        for v in violations:
            by_rule[v.rule_id] += 1
            by_department[v.user_department] += 1
            by_risk[v.risk_level.value] += 1
            users_with_violations.add(v.user_id)

        return {
            "total_violations": len(violations),
            "unique_users_with_violations": len(users_with_violations),
            "by_rule": dict(by_rule),
            "by_department": dict(by_department),
            "by_risk_level": dict(by_risk),
            "rules_violated": len(by_rule),
        }


# ============================================================
# SOD VIOLATION SUMMARY
# ============================================================

class SoDViolationSummary:
    """
    Executive summary of SoD violations.

    For management and audit committee reporting.
    """

    def __init__(self, conflict_report: Optional[SoDConflictReport] = None):
        self._conflict_report = conflict_report or SoDConflictReport()

    def execute(self) -> ReportResult:
        """Generate executive summary."""
        result = ReportResult(
            report_type="SOD_SUMMARY",
            report_name="SoD Violation Executive Summary",
        )

        start_time = datetime.now()

        # Get detailed conflicts
        detailed = self._conflict_report.execute()

        # Build executive summary
        total_users = len(set(r["user_id"] for r in detailed.records))
        total_violations = len(detailed.records)

        # Risk distribution
        risk_dist = {
            "CRITICAL": detailed.critical_findings,
            "HIGH": detailed.high_findings,
            "MEDIUM": detailed.medium_findings,
            "LOW": detailed.low_findings,
        }

        # Top violations by rule
        rule_counts = defaultdict(int)
        for r in detailed.records:
            rule_counts[r["rule_name"]] += 1

        top_violations = sorted(rule_counts.items(), key=lambda x: x[1], reverse=True)[:10]

        # Top departments
        dept_counts = defaultdict(int)
        for r in detailed.records:
            dept_counts[r["user_department"]] += 1

        top_departments = sorted(dept_counts.items(), key=lambda x: x[1], reverse=True)[:10]

        # Build summary records
        summary_record = {
            "report_date": datetime.now().isoformat(),
            "total_violations": total_violations,
            "unique_users_affected": total_users,
            "risk_distribution": risk_dist,
            "top_violations": [{"rule": r, "count": c} for r, c in top_violations],
            "top_departments": [{"department": d, "count": c} for d, c in top_departments],
            "critical_action_required": detailed.critical_findings > 0,
            "recommendations": self._generate_recommendations(detailed),
        }

        result.records = [summary_record]
        result.total_records = 1

        result.summary = {
            "total_violations": total_violations,
            "users_affected": total_users,
            "critical_violations": risk_dist["CRITICAL"],
        }

        result.critical_findings = detailed.critical_findings
        result.high_findings = detailed.high_findings

        result.execution_time_seconds = (datetime.now() - start_time).total_seconds()

        return result

    def _generate_recommendations(self, detailed: ReportResult) -> List[str]:
        """Generate actionable recommendations."""
        recommendations = []

        if detailed.critical_findings > 0:
            recommendations.append(
                f"URGENT: {detailed.critical_findings} critical SoD violations require immediate remediation"
            )

        if detailed.high_findings > 10:
            recommendations.append(
                "Consider implementing role redesign to reduce high-risk SoD conflicts"
            )

        if detailed.total_records > 100:
            recommendations.append(
                "High volume of violations suggests need for comprehensive access review"
            )

        recommendations.append(
            "Ensure all violations have documented mitigating controls or business justification"
        )

        return recommendations


# ============================================================
# SOD RISK MATRIX
# ============================================================

class SoDRiskMatrix:
    """
    Visual risk matrix of SoD conflicts.

    Shows which function combinations are most problematic.
    """

    def __init__(self, conflict_report: Optional[SoDConflictReport] = None):
        self._conflict_report = conflict_report or SoDConflictReport()

    def execute(self) -> ReportResult:
        """Generate risk matrix."""
        result = ReportResult(
            report_type="SOD_RISK_MATRIX",
            report_name="SoD Risk Matrix",
        )

        start_time = datetime.now()

        # Get detailed conflicts
        detailed = self._conflict_report.execute()

        # Build function-pair matrix
        matrix: Dict[Tuple[str, str], Dict[str, Any]] = {}

        for record in detailed.records:
            key = (record["function_1"], record["function_2"])
            if key not in matrix:
                matrix[key] = {
                    "function_1": record["function_1"],
                    "function_2": record["function_2"],
                    "rule_name": record["rule_name"],
                    "violation_count": 0,
                    "users": set(),
                    "risk_level": record["risk_level"],
                }

            matrix[key]["violation_count"] += 1
            matrix[key]["users"].add(record["user_id"])

        # Convert to records
        matrix_records = []
        for key, data in matrix.items():
            matrix_records.append({
                "function_1": data["function_1"],
                "function_2": data["function_2"],
                "rule_name": data["rule_name"],
                "violation_count": data["violation_count"],
                "unique_users": len(data["users"]),
                "risk_level": data["risk_level"],
                "heat_score": data["violation_count"] * self._risk_multiplier(data["risk_level"]),
            })

        # Sort by heat score
        matrix_records.sort(key=lambda x: x["heat_score"], reverse=True)

        result.records = matrix_records
        result.total_records = len(matrix_records)

        result.summary = {
            "unique_function_pairs": len(matrix_records),
            "highest_heat_score": matrix_records[0]["heat_score"] if matrix_records else 0,
        }

        result.execution_time_seconds = (datetime.now() - start_time).total_seconds()

        return result

    def _risk_multiplier(self, risk_level: str) -> int:
        """Get risk multiplier for heat score."""
        multipliers = {
            "CRITICAL": 4,
            "HIGH": 3,
            "MEDIUM": 2,
            "LOW": 1,
        }
        return multipliers.get(risk_level, 1)


# ============================================================
# SOD MITIGATION REPORT
# ============================================================

class SoDMitigationReport:
    """
    Report on mitigated SoD violations.

    Shows which violations have controls in place.
    """

    def __init__(
        self,
        violation_provider: Optional[Callable] = None,
        mitigation_provider: Optional[Callable] = None
    ):
        self._violation_provider = violation_provider or (lambda: [])
        self._mitigation_provider = mitigation_provider or (lambda: [])

    def execute(self) -> ReportResult:
        """Report on mitigations."""
        result = ReportResult(
            report_type="SOD_MITIGATIONS",
            report_name="SoD Mitigation Status Report",
        )

        start_time = datetime.now()

        violations = self._violation_provider()
        mitigations = self._mitigation_provider()

        # Build mitigation lookup
        mitigation_lookup = {m.get("violation_id"): m for m in mitigations}

        findings = []
        mitigated_count = 0
        unmitigated_count = 0
        expired_count = 0

        for violation in violations:
            mitigation = mitigation_lookup.get(violation.violation_id)

            finding = {
                "violation_id": violation.violation_id,
                "rule_name": violation.rule_name,
                "user_id": violation.user_id,
                "username": violation.username,
                "risk_level": violation.risk_level.value,
                "is_mitigated": False,
                "mitigation_status": "UNMITIGATED",
                "mitigation_control": "",
                "mitigation_owner": "",
                "mitigation_expires": None,
            }

            if mitigation:
                finding["is_mitigated"] = True
                finding["mitigation_control"] = mitigation.get("control_name", "")
                finding["mitigation_owner"] = mitigation.get("owner", "")
                finding["mitigation_expires"] = mitigation.get("expiry_date")

                # Check if expired
                expiry = mitigation.get("expiry_date")
                if expiry and isinstance(expiry, date) and expiry < date.today():
                    finding["mitigation_status"] = "EXPIRED"
                    expired_count += 1
                    result.high_findings += 1
                else:
                    finding["mitigation_status"] = "ACTIVE"
                    mitigated_count += 1
            else:
                unmitigated_count += 1
                if violation.risk_level == RiskLevel.CRITICAL:
                    result.critical_findings += 1
                elif violation.risk_level == RiskLevel.HIGH:
                    result.high_findings += 1

            findings.append(finding)

        result.records = findings
        result.total_records = len(findings)

        result.summary = {
            "total_violations": len(findings),
            "mitigated": mitigated_count,
            "unmitigated": unmitigated_count,
            "expired_mitigations": expired_count,
            "mitigation_rate": mitigated_count / len(findings) * 100 if findings else 0,
        }

        result.execution_time_seconds = (datetime.now() - start_time).total_seconds()

        return result


# ============================================================
# SOD TREND ANALYSIS
# ============================================================

class SoDTrendAnalysis:
    """
    Analyze SoD violation trends over time.

    For tracking remediation progress.
    """

    def __init__(self, historical_provider: Optional[Callable] = None):
        self._historical_provider = historical_provider or (lambda: [])

    def execute(self, months: int = 12) -> ReportResult:
        """Generate trend analysis."""
        result = ReportResult(
            report_type="SOD_TRENDS",
            report_name=f"SoD Violation Trends ({months} months)",
        )

        start_time = datetime.now()

        # Get historical data
        historical = self._historical_provider()

        # Group by month
        monthly_data: Dict[str, Dict[str, int]] = defaultdict(
            lambda: {"violations": 0, "mitigated": 0, "remediated": 0}
        )

        for record in historical:
            month = record.get("month", "")
            monthly_data[month]["violations"] += record.get("violation_count", 0)
            monthly_data[month]["mitigated"] += record.get("mitigated_count", 0)
            monthly_data[month]["remediated"] += record.get("remediated_count", 0)

        # Sort by month
        sorted_months = sorted(monthly_data.keys())[-months:]

        trends = []
        prev_violations = None

        for month in sorted_months:
            data = monthly_data[month]
            trend_record = {
                "month": month,
                "violations": data["violations"],
                "mitigated": data["mitigated"],
                "remediated": data["remediated"],
                "net_violations": data["violations"] - data["remediated"],
                "mitigation_rate": data["mitigated"] / data["violations"] * 100 if data["violations"] else 0,
            }

            # Calculate trend
            if prev_violations is not None:
                change = data["violations"] - prev_violations
                trend_record["trend"] = "INCREASING" if change > 0 else "DECREASING" if change < 0 else "STABLE"
                trend_record["change"] = change
            else:
                trend_record["trend"] = "N/A"
                trend_record["change"] = 0

            prev_violations = data["violations"]
            trends.append(trend_record)

        result.records = trends
        result.total_records = len(trends)

        # Overall trend
        if trends and len(trends) >= 2:
            first_half = sum(t["violations"] for t in trends[:len(trends)//2])
            second_half = sum(t["violations"] for t in trends[len(trends)//2:])
            overall_trend = "IMPROVING" if second_half < first_half else "WORSENING" if second_half > first_half else "STABLE"
        else:
            overall_trend = "INSUFFICIENT_DATA"

        result.summary = {
            "months_analyzed": len(trends),
            "overall_trend": overall_trend,
            "current_month_violations": trends[-1]["violations"] if trends else 0,
            "avg_mitigation_rate": sum(t["mitigation_rate"] for t in trends) / len(trends) if trends else 0,
        }

        result.execution_time_seconds = (datetime.now() - start_time).total_seconds()

        return result
