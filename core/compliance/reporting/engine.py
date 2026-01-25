# Report Engine
# Core reporting infrastructure for GOVERNEX+

"""
Report Engine - The backbone of compliance reporting.

This module provides:
- Report execution engine
- Report scheduling
- Export to multiple formats
- Custom report templates
- Report distribution

Enterprise Features:
- Scheduled report generation (daily, weekly, monthly)
- Multiple export formats (PDF, Excel, CSV, JSON)
- Email distribution lists
- Report versioning and history
- Custom templates
- API access for integration
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable, Type, Union
from datetime import datetime, date, timedelta
from enum import Enum
from abc import ABC, abstractmethod
import uuid
import json
import io
import csv

from .models import (
    ReportResult, ReportFormat, ReportFrequency, RiskLevel
)


# ============================================================
# REPORT REGISTRY
# ============================================================

class ReportCategory(Enum):
    """Report categories."""
    USER_MASTER = "USER_MASTER"
    ROLE_ASSIGNMENT = "ROLE_ASSIGNMENT"
    CRITICAL_ACCESS = "CRITICAL_ACCESS"
    SOD = "SOD"
    FIREFIGHTER = "FIREFIGHTER"
    CHANGE_LOG = "CHANGE_LOG"
    SECURITY = "SECURITY"
    COMPLIANCE = "COMPLIANCE"


@dataclass
class ReportDefinition:
    """Definition of a report type."""
    report_id: str = ""
    name: str = ""
    description: str = ""
    category: ReportCategory = ReportCategory.COMPLIANCE

    # Execution
    report_class: str = ""  # Class name to instantiate
    default_parameters: Dict[str, Any] = field(default_factory=dict)

    # Metadata
    owner: str = "SYSTEM"
    is_critical: bool = False  # Auditors frequently request this
    typical_use_case: str = ""
    sap_equivalent: str = ""  # e.g., "SUIM > User > By Transaction"

    # Access
    required_role: str = "AUDITOR"
    is_public: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id": self.report_id,
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
            "sap_equivalent": self.sap_equivalent,
            "is_critical": self.is_critical,
        }


# Standard report registry
STANDARD_REPORTS: Dict[str, ReportDefinition] = {
    # User Reports
    "USER_LIST": ReportDefinition(
        report_id="USER_LIST",
        name="User Master List",
        description="List all users with their status and key attributes",
        category=ReportCategory.USER_MASTER,
        report_class="UserListReport",
        is_critical=True,
        sap_equivalent="SUIM > User > By Address Data",
        typical_use_case="User population analysis, license compliance",
    ),
    "TERMINATED_USERS": ReportDefinition(
        report_id="TERMINATED_USERS",
        name="Terminated Users with Access",
        description="Terminated employees who still have active access",
        category=ReportCategory.USER_MASTER,
        report_class="TerminatedUserReport",
        is_critical=True,
        sap_equivalent="Custom - No direct equivalent",
        typical_use_case="Access recertification, security audit",
    ),
    "GENERIC_ACCOUNTS": ReportDefinition(
        report_id="GENERIC_ACCOUNTS",
        name="Generic/Shared Accounts",
        description="SAP*, DDIC, and other generic accounts",
        category=ReportCategory.USER_MASTER,
        report_class="GenericUserReport",
        is_critical=True,
        sap_equivalent="SU01 with pattern search",
        typical_use_case="Security audit, password policy compliance",
    ),

    # Role Reports
    "USERS_BY_ROLE": ReportDefinition(
        report_id="USERS_BY_ROLE",
        name="Users by Role",
        description="List users assigned to specific roles",
        category=ReportCategory.ROLE_ASSIGNMENT,
        report_class="UsersByRoleReport",
        is_critical=True,
        sap_equivalent="SUIM > User > By Role",
        typical_use_case="Role membership review, access certification",
    ),
    "ROLES_BY_USER": ReportDefinition(
        report_id="ROLES_BY_USER",
        name="Roles by User",
        description="List all roles assigned to a user",
        category=ReportCategory.ROLE_ASSIGNMENT,
        report_class="RolesByUserReport",
        is_critical=True,
        sap_equivalent="SU01 > Roles tab, SUIM > User > By Role",
        typical_use_case="User access review, joiner/mover/leaver",
    ),
    "CRITICAL_ROLES": ReportDefinition(
        report_id="CRITICAL_ROLES",
        name="Critical Role Assignments",
        description="Users with SAP_ALL, SAP_NEW, or custom critical roles",
        category=ReportCategory.ROLE_ASSIGNMENT,
        report_class="CriticalRoleReport",
        is_critical=True,
        sap_equivalent="SUIM > User > By Role > SAP_ALL",
        typical_use_case="Privileged access review, security audit",
    ),

    # Critical Access Reports
    "CRITICAL_TRANSACTIONS": ReportDefinition(
        report_id="CRITICAL_TRANSACTIONS",
        name="Critical Transaction Access",
        description="Users with access to sensitive transactions",
        category=ReportCategory.CRITICAL_ACCESS,
        report_class="CriticalTransactionReport",
        is_critical=True,
        sap_equivalent="SUIM > User > By Transaction Code",
        typical_use_case="Sensitive access review, SOX compliance",
    ),
    "AUTH_OBJECTS": ReportDefinition(
        report_id="AUTH_OBJECTS",
        name="Authorization Object Analysis",
        description="Users with specific authorization objects and values",
        category=ReportCategory.CRITICAL_ACCESS,
        report_class="AuthorizationObjectReport",
        is_critical=True,
        sap_equivalent="SUIM > User > By Authorization Values",
        typical_use_case="Debug authorization, S_DEVELOP analysis",
    ),
    "DIRECT_TABLE_ACCESS": ReportDefinition(
        report_id="DIRECT_TABLE_ACCESS",
        name="Direct Table Access",
        description="Users who can modify tables directly via SE16N/SM30",
        category=ReportCategory.CRITICAL_ACCESS,
        report_class="DirectTableAccessReport",
        is_critical=True,
        sap_equivalent="SUIM > By Auth Object > S_TABU_DIS",
        typical_use_case="Data integrity audit, change management",
    ),

    # SoD Reports
    "SOD_CONFLICTS": ReportDefinition(
        report_id="SOD_CONFLICTS",
        name="Segregation of Duties Conflicts",
        description="Users with conflicting access (THE critical audit report)",
        category=ReportCategory.SOD,
        report_class="SoDConflictReport",
        is_critical=True,
        sap_equivalent="SAP GRC Access Control - Risk Analysis",
        typical_use_case="SOX compliance, internal audit, access certification",
    ),
    "SOD_RISK_MATRIX": ReportDefinition(
        report_id="SOD_RISK_MATRIX",
        name="SoD Risk Matrix",
        description="Heat map of SoD violations by department/function",
        category=ReportCategory.SOD,
        report_class="SoDRiskMatrix",
        is_critical=False,
        sap_equivalent="SAP GRC Dashboards",
        typical_use_case="Executive reporting, risk assessment",
    ),
    "SOD_MITIGATIONS": ReportDefinition(
        report_id="SOD_MITIGATIONS",
        name="SoD Mitigation Status",
        description="Status of mitigating controls for SoD violations",
        category=ReportCategory.SOD,
        report_class="SoDMitigationReport",
        is_critical=True,
        sap_equivalent="SAP GRC - Mitigating Control Report",
        typical_use_case="Control effectiveness, audit evidence",
    ),

    # Firefighter Reports
    "FF_USAGE": ReportDefinition(
        report_id="FF_USAGE",
        name="Firefighter Usage Report",
        description="Emergency access sessions and activities",
        category=ReportCategory.FIREFIGHTER,
        report_class="FirefighterUsageReport",
        is_critical=True,
        sap_equivalent="SAP GRC EAM - FF Log Report",
        typical_use_case="Emergency access review, audit evidence",
    ),
    "FF_LOG": ReportDefinition(
        report_id="FF_LOG",
        name="Firefighter Activity Log",
        description="Detailed log of actions during FF sessions",
        category=ReportCategory.FIREFIGHTER,
        report_class="FirefighterLogReport",
        is_critical=True,
        sap_equivalent="SAP GRC EAM - Transaction Log",
        typical_use_case="Post-incident review, audit evidence",
    ),
    "PRIVILEGED_ACCESS": ReportDefinition(
        report_id="PRIVILEGED_ACCESS",
        name="Privileged Access Review",
        description="All privileged/superuser access for review",
        category=ReportCategory.FIREFIGHTER,
        report_class="PrivilegedAccessReview",
        is_critical=True,
        sap_equivalent="Custom - combines multiple reports",
        typical_use_case="Periodic access review, SOC2 compliance",
    ),

    # Change Reports
    "USER_CHANGES": ReportDefinition(
        report_id="USER_CHANGES",
        name="User Master Change Log",
        description="All changes to user master records",
        category=ReportCategory.CHANGE_LOG,
        report_class="UserChangeLog",
        is_critical=True,
        sap_equivalent="SUIM > Environment > Changes to User Master",
        typical_use_case="Audit trail, change management",
    ),
    "ROLE_CHANGES": ReportDefinition(
        report_id="ROLE_CHANGES",
        name="Role Change Log",
        description="All changes to roles and authorizations",
        category=ReportCategory.CHANGE_LOG,
        report_class="RoleChangeLog",
        is_critical=True,
        sap_equivalent="PFCG > Changes tab, SUIM > Changes to Roles",
        typical_use_case="Audit trail, segregation of duties",
    ),
    "ACCESS_TIMELINE": ReportDefinition(
        report_id="ACCESS_TIMELINE",
        name="Access Change Timeline",
        description="Chronological view of all access changes",
        category=ReportCategory.CHANGE_LOG,
        report_class="AccessChangeTimeline",
        is_critical=False,
        sap_equivalent="Custom - combines multiple change reports",
        typical_use_case="Incident investigation, audit evidence",
    ),

    # Security Reports
    "LOGIN_AUDIT": ReportDefinition(
        report_id="LOGIN_AUDIT",
        name="Login Audit Report",
        description="Login history with anomaly detection",
        category=ReportCategory.SECURITY,
        report_class="LoginAuditReport",
        is_critical=True,
        sap_equivalent="SM20, ST03N",
        typical_use_case="Security audit, incident investigation",
    ),
    "FAILED_LOGINS": ReportDefinition(
        report_id="FAILED_LOGINS",
        name="Failed Login Analysis",
        description="Failed login attempts with brute force detection",
        category=ReportCategory.SECURITY,
        report_class="FailedLoginReport",
        is_critical=True,
        sap_equivalent="SM20 filtered for failed logons",
        typical_use_case="Security monitoring, attack detection",
    ),
    "ANOMALOUS_ACCESS": ReportDefinition(
        report_id="ANOMALOUS_ACCESS",
        name="Anomalous Access Report",
        description="Unusual access patterns and behaviors",
        category=ReportCategory.SECURITY,
        report_class="AnomalousAccessReport",
        is_critical=True,
        sap_equivalent="No direct equivalent - behavioral analytics",
        typical_use_case="Threat detection, insider threat",
    ),

    # Compliance Reports
    "COMPLIANCE_SCORECARD": ReportDefinition(
        report_id="COMPLIANCE_SCORECARD",
        name="Compliance Scorecard",
        description="Overall compliance status and metrics",
        category=ReportCategory.COMPLIANCE,
        report_class="ComplianceScorecard",
        is_critical=True,
        sap_equivalent="SAP GRC Dashboards",
        typical_use_case="Executive reporting, board updates",
    ),
}


# ============================================================
# BASE REPORT CLASS
# ============================================================

class BaseReport(ABC):
    """Abstract base class for all reports."""

    def __init__(self):
        self.report_id: str = ""
        self.name: str = ""
        self.description: str = ""
        self.parameters: Dict[str, Any] = {}

    @abstractmethod
    def execute(self, **kwargs) -> ReportResult:
        """Execute the report and return results."""
        pass

    @abstractmethod
    def get_parameter_schema(self) -> Dict[str, Any]:
        """Return JSON schema for report parameters."""
        pass


# ============================================================
# REPORT ENGINE
# ============================================================

@dataclass
class ReportExecution:
    """Record of a report execution."""
    execution_id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    report_id: str = ""
    report_name: str = ""

    # Execution details
    executed_by: str = ""
    executed_at: datetime = field(default_factory=datetime.now)
    execution_time_ms: int = 0
    status: str = "SUCCESS"  # SUCCESS, FAILED, CANCELLED

    # Parameters and results
    parameters: Dict[str, Any] = field(default_factory=dict)
    result_count: int = 0
    result_location: str = ""  # File path or S3 location

    # Errors
    error_message: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "execution_id": self.execution_id,
            "report_id": self.report_id,
            "report_name": self.report_name,
            "executed_by": self.executed_by,
            "executed_at": self.executed_at.isoformat(),
            "execution_time_ms": self.execution_time_ms,
            "status": self.status,
            "parameters": self.parameters,
            "result_count": self.result_count,
        }


@dataclass
class ReportEngine:
    """
    Core report execution engine.

    Responsibilities:
    - Execute reports on demand
    - Track execution history
    - Manage report cache
    - Handle errors gracefully
    """

    engine_id: str = field(default_factory=lambda: f"ENG-{str(uuid.uuid4())[:8]}")

    # Report registry
    report_registry: Dict[str, ReportDefinition] = field(default_factory=lambda: STANDARD_REPORTS.copy())

    # Report instances (populated by registration)
    report_instances: Dict[str, BaseReport] = field(default_factory=dict)

    # Execution history
    execution_history: List[ReportExecution] = field(default_factory=list)
    max_history: int = 1000

    # Cache
    cache_enabled: bool = True
    cache_ttl_seconds: int = 300  # 5 minutes
    cache: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    def register_report(self, report_class: Type[BaseReport], definition: ReportDefinition) -> None:
        """Register a report class with its definition."""
        self.report_registry[definition.report_id] = definition
        self.report_instances[definition.report_id] = report_class()

    def get_available_reports(self, category: Optional[ReportCategory] = None) -> List[ReportDefinition]:
        """Get list of available reports, optionally filtered by category."""
        reports = list(self.report_registry.values())
        if category:
            reports = [r for r in reports if r.category == category]
        return sorted(reports, key=lambda r: r.name)

    def get_critical_reports(self) -> List[ReportDefinition]:
        """Get reports commonly requested by auditors."""
        return [r for r in self.report_registry.values() if r.is_critical]

    def execute_report(
        self,
        report_id: str,
        parameters: Dict[str, Any],
        user_id: str = "SYSTEM",
    ) -> ReportResult:
        """Execute a report by ID."""
        start_time = datetime.now()

        # Create execution record
        execution = ReportExecution(
            report_id=report_id,
            executed_by=user_id,
            parameters=parameters,
        )

        try:
            # Check registry
            if report_id not in self.report_registry:
                raise ValueError(f"Unknown report: {report_id}")

            definition = self.report_registry[report_id]
            execution.report_name = definition.name

            # Check cache
            cache_key = self._get_cache_key(report_id, parameters)
            if self.cache_enabled and cache_key in self.cache:
                cached = self.cache[cache_key]
                if (datetime.now() - cached["timestamp"]).seconds < self.cache_ttl_seconds:
                    execution.status = "CACHED"
                    return cached["result"]

            # Execute report
            if report_id in self.report_instances:
                report = self.report_instances[report_id]
                result = report.execute(**parameters)
            else:
                # Create placeholder result for unregistered reports
                result = ReportResult(
                    report_type=report_id,
                    report_name=definition.name,
                    executed_by=user_id,
                    parameters=parameters,
                )

            # Update execution record
            execution.status = "SUCCESS"
            execution.result_count = result.total_records
            execution.execution_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)

            # Update cache
            if self.cache_enabled:
                self.cache[cache_key] = {
                    "timestamp": datetime.now(),
                    "result": result,
                }

            return result

        except Exception as e:
            execution.status = "FAILED"
            execution.error_message = str(e)
            raise

        finally:
            # Record execution
            self._record_execution(execution)

    def _get_cache_key(self, report_id: str, parameters: Dict[str, Any]) -> str:
        """Generate cache key from report ID and parameters."""
        param_str = json.dumps(parameters, sort_keys=True, default=str)
        return f"{report_id}:{hash(param_str)}"

    def _record_execution(self, execution: ReportExecution) -> None:
        """Record execution in history."""
        self.execution_history.append(execution)
        # Trim history if needed
        if len(self.execution_history) > self.max_history:
            self.execution_history = self.execution_history[-self.max_history:]

    def get_execution_history(
        self,
        report_id: Optional[str] = None,
        user_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[ReportExecution]:
        """Get report execution history."""
        history = self.execution_history

        if report_id:
            history = [e for e in history if e.report_id == report_id]
        if user_id:
            history = [e for e in history if e.executed_by == user_id]

        return sorted(history, key=lambda e: e.executed_at, reverse=True)[:limit]

    def clear_cache(self) -> None:
        """Clear the report cache."""
        self.cache.clear()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "engine_id": self.engine_id,
            "available_reports": len(self.report_registry),
            "cache_enabled": self.cache_enabled,
            "cached_reports": len(self.cache),
            "executions_today": len([
                e for e in self.execution_history
                if e.executed_at.date() == date.today()
            ]),
        }


# ============================================================
# REPORT SCHEDULER
# ============================================================

@dataclass
class ScheduledReport:
    """Configuration for a scheduled report."""
    schedule_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    report_id: str = ""
    report_name: str = ""

    # Schedule
    frequency: ReportFrequency = ReportFrequency.WEEKLY
    day_of_week: int = 1  # 1=Monday for weekly
    day_of_month: int = 1  # For monthly
    time_of_day: str = "06:00"  # HH:MM

    # Parameters
    parameters: Dict[str, Any] = field(default_factory=dict)

    # Distribution
    recipients: List[str] = field(default_factory=list)
    export_format: ReportFormat = ReportFormat.PDF
    include_summary: bool = True

    # Status
    is_active: bool = True
    created_by: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    last_status: str = ""

    def calculate_next_run(self) -> datetime:
        """Calculate the next run time based on frequency."""
        now = datetime.now()
        hour, minute = map(int, self.time_of_day.split(":"))

        if self.frequency == ReportFrequency.DAILY:
            next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if next_run <= now:
                next_run += timedelta(days=1)

        elif self.frequency == ReportFrequency.WEEKLY:
            days_ahead = self.day_of_week - now.weekday()
            if days_ahead <= 0:
                days_ahead += 7
            next_run = now + timedelta(days=days_ahead)
            next_run = next_run.replace(hour=hour, minute=minute, second=0, microsecond=0)

        elif self.frequency == ReportFrequency.MONTHLY:
            if now.day >= self.day_of_month:
                # Next month
                if now.month == 12:
                    next_run = now.replace(year=now.year + 1, month=1, day=self.day_of_month)
                else:
                    next_run = now.replace(month=now.month + 1, day=self.day_of_month)
            else:
                next_run = now.replace(day=self.day_of_month)
            next_run = next_run.replace(hour=hour, minute=minute, second=0, microsecond=0)

        elif self.frequency == ReportFrequency.QUARTERLY:
            quarter_start_months = [1, 4, 7, 10]
            current_quarter = (now.month - 1) // 3
            next_quarter = (current_quarter + 1) % 4
            next_month = quarter_start_months[next_quarter]
            next_year = now.year if next_month > now.month else now.year + 1
            next_run = datetime(next_year, next_month, self.day_of_month, hour, minute)

        else:
            next_run = now + timedelta(days=1)

        self.next_run = next_run
        return next_run

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schedule_id": self.schedule_id,
            "report_id": self.report_id,
            "report_name": self.report_name,
            "frequency": self.frequency.value,
            "time_of_day": self.time_of_day,
            "recipients": self.recipients,
            "export_format": self.export_format.value,
            "is_active": self.is_active,
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "next_run": self.next_run.isoformat() if self.next_run else None,
            "last_status": self.last_status,
        }


@dataclass
class ReportScheduler:
    """
    Report scheduling engine.

    Manages scheduled reports:
    - Create/update/delete schedules
    - Track execution times
    - Handle distribution
    """

    scheduler_id: str = field(default_factory=lambda: f"SCHED-{str(uuid.uuid4())[:8]}")

    # Schedules
    schedules: Dict[str, ScheduledReport] = field(default_factory=dict)

    # Engine reference
    engine: Optional[ReportEngine] = None

    # Distribution handlers
    distribution_handlers: Dict[str, Callable] = field(default_factory=dict)

    def create_schedule(
        self,
        report_id: str,
        frequency: ReportFrequency,
        recipients: List[str],
        parameters: Optional[Dict[str, Any]] = None,
        export_format: ReportFormat = ReportFormat.PDF,
        time_of_day: str = "06:00",
        created_by: str = "SYSTEM",
    ) -> ScheduledReport:
        """Create a new report schedule."""
        schedule = ScheduledReport(
            report_id=report_id,
            report_name=STANDARD_REPORTS.get(report_id, ReportDefinition()).name,
            frequency=frequency,
            time_of_day=time_of_day,
            parameters=parameters or {},
            recipients=recipients,
            export_format=export_format,
            created_by=created_by,
        )
        schedule.calculate_next_run()
        self.schedules[schedule.schedule_id] = schedule
        return schedule

    def update_schedule(self, schedule_id: str, updates: Dict[str, Any]) -> ScheduledReport:
        """Update an existing schedule."""
        if schedule_id not in self.schedules:
            raise ValueError(f"Schedule not found: {schedule_id}")

        schedule = self.schedules[schedule_id]

        for key, value in updates.items():
            if hasattr(schedule, key):
                setattr(schedule, key, value)

        schedule.calculate_next_run()
        return schedule

    def delete_schedule(self, schedule_id: str) -> None:
        """Delete a schedule."""
        if schedule_id in self.schedules:
            del self.schedules[schedule_id]

    def get_due_schedules(self) -> List[ScheduledReport]:
        """Get schedules that are due to run."""
        now = datetime.now()
        due = []

        for schedule in self.schedules.values():
            if schedule.is_active and schedule.next_run and schedule.next_run <= now:
                due.append(schedule)

        return due

    def run_schedule(self, schedule_id: str) -> ReportResult:
        """Execute a scheduled report."""
        if schedule_id not in self.schedules:
            raise ValueError(f"Schedule not found: {schedule_id}")

        schedule = self.schedules[schedule_id]

        try:
            # Execute report
            if self.engine:
                result = self.engine.execute_report(
                    schedule.report_id,
                    schedule.parameters,
                    user_id=f"SCHEDULER:{schedule.schedule_id}",
                )
            else:
                result = ReportResult(
                    report_type=schedule.report_id,
                    report_name=schedule.report_name,
                )

            # Update schedule
            schedule.last_run = datetime.now()
            schedule.last_status = "SUCCESS"
            schedule.calculate_next_run()

            # Distribute report
            self._distribute_report(schedule, result)

            return result

        except Exception as e:
            schedule.last_run = datetime.now()
            schedule.last_status = f"FAILED: {str(e)}"
            schedule.calculate_next_run()
            raise

    def _distribute_report(self, schedule: ScheduledReport, result: ReportResult) -> None:
        """Distribute report to recipients."""
        # In real implementation, this would email or store the report
        pass

    def get_active_schedules(self) -> List[ScheduledReport]:
        """Get all active schedules."""
        return [s for s in self.schedules.values() if s.is_active]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scheduler_id": self.scheduler_id,
            "total_schedules": len(self.schedules),
            "active_schedules": len(self.get_active_schedules()),
            "schedules": [s.to_dict() for s in self.schedules.values()],
        }


# ============================================================
# REPORT EXPORTER
# ============================================================

@dataclass
class ExportOptions:
    """Options for report export."""
    format: ReportFormat = ReportFormat.PDF
    include_header: bool = True
    include_footer: bool = True
    include_summary: bool = True
    include_charts: bool = True
    page_size: str = "A4"
    orientation: str = "landscape"
    company_name: str = "GOVERNEX+"
    logo_path: str = ""


@dataclass
class ReportExporter:
    """
    Export reports to various formats.

    Supported formats:
    - PDF: Formatted report with headers, charts, and branding
    - Excel: Tabular data with formatting and multiple sheets
    - CSV: Raw data export
    - JSON: API-friendly format
    - HTML: Web-viewable format
    """

    exporter_id: str = field(default_factory=lambda: f"EXP-{str(uuid.uuid4())[:8]}")

    # Default options
    default_options: ExportOptions = field(default_factory=ExportOptions)

    def export(
        self,
        result: ReportResult,
        format: ReportFormat,
        options: Optional[ExportOptions] = None,
    ) -> Union[bytes, str, Dict[str, Any]]:
        """Export report result to specified format."""
        options = options or self.default_options

        if format == ReportFormat.CSV:
            return self._export_csv(result)
        elif format == ReportFormat.JSON:
            return self._export_json(result)
        elif format == ReportFormat.EXCEL:
            return self._export_excel(result, options)
        elif format == ReportFormat.PDF:
            return self._export_pdf(result, options)
        elif format == ReportFormat.HTML:
            return self._export_html(result, options)
        else:
            raise ValueError(f"Unsupported format: {format}")

    def _export_csv(self, result: ReportResult) -> str:
        """Export to CSV format."""
        if not result.records:
            return ""

        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=result.records[0].keys())
        writer.writeheader()
        writer.writerows(result.records)
        return output.getvalue()

    def _export_json(self, result: ReportResult) -> Dict[str, Any]:
        """Export to JSON format."""
        return {
            "report_id": result.report_id,
            "report_type": result.report_type,
            "report_name": result.report_name,
            "executed_at": result.executed_at.isoformat(),
            "executed_by": result.executed_by,
            "parameters": result.parameters,
            "summary": result.summary,
            "findings": {
                "critical": result.critical_findings,
                "high": result.high_findings,
                "medium": result.medium_findings,
                "low": result.low_findings,
            },
            "total_records": result.total_records,
            "data": result.records,
        }

    def _export_excel(self, result: ReportResult, options: ExportOptions) -> bytes:
        """Export to Excel format."""
        # In real implementation, would use openpyxl or xlsxwriter
        # For now, return placeholder
        return b"EXCEL_PLACEHOLDER"

    def _export_pdf(self, result: ReportResult, options: ExportOptions) -> bytes:
        """Export to PDF format."""
        # In real implementation, would use reportlab or weasyprint
        # For now, return placeholder
        return b"PDF_PLACEHOLDER"

    def _export_html(self, result: ReportResult, options: ExportOptions) -> str:
        """Export to HTML format."""
        html_parts = [
            "<!DOCTYPE html>",
            "<html><head>",
            f"<title>{result.report_name}</title>",
            "<style>",
            "body { font-family: Arial, sans-serif; margin: 20px; }",
            "h1 { color: #333; }",
            "table { border-collapse: collapse; width: 100%; }",
            "th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }",
            "th { background-color: #4CAF50; color: white; }",
            "tr:nth-child(even) { background-color: #f2f2f2; }",
            ".summary { background-color: #f9f9f9; padding: 15px; margin: 15px 0; }",
            ".critical { color: #d32f2f; font-weight: bold; }",
            ".high { color: #f57c00; font-weight: bold; }",
            "</style>",
            "</head><body>",
        ]

        # Header
        if options.include_header:
            html_parts.append(f"<h1>{result.report_name}</h1>")
            html_parts.append(f"<p>Generated: {result.executed_at.strftime('%Y-%m-%d %H:%M:%S')}</p>")
            html_parts.append(f"<p>Generated by: {result.executed_by}</p>")

        # Summary
        if options.include_summary and result.summary:
            html_parts.append("<div class='summary'>")
            html_parts.append("<h2>Summary</h2>")
            for key, value in result.summary.items():
                html_parts.append(f"<p><strong>{key}:</strong> {value}</p>")
            html_parts.append("</div>")

        # Findings summary
        if result.critical_findings > 0 or result.high_findings > 0:
            html_parts.append("<div class='summary'>")
            html_parts.append("<h2>Findings</h2>")
            if result.critical_findings > 0:
                html_parts.append(f"<p class='critical'>Critical: {result.critical_findings}</p>")
            if result.high_findings > 0:
                html_parts.append(f"<p class='high'>High: {result.high_findings}</p>")
            if result.medium_findings > 0:
                html_parts.append(f"<p>Medium: {result.medium_findings}</p>")
            if result.low_findings > 0:
                html_parts.append(f"<p>Low: {result.low_findings}</p>")
            html_parts.append("</div>")

        # Data table
        if result.records:
            html_parts.append(f"<h2>Data ({result.total_records} records)</h2>")
            html_parts.append("<table>")

            # Headers
            headers = result.records[0].keys()
            html_parts.append("<tr>")
            for header in headers:
                html_parts.append(f"<th>{header}</th>")
            html_parts.append("</tr>")

            # Rows
            for record in result.records:
                html_parts.append("<tr>")
                for value in record.values():
                    html_parts.append(f"<td>{value}</td>")
                html_parts.append("</tr>")

            html_parts.append("</table>")

        # Footer
        if options.include_footer:
            html_parts.append(f"<p style='margin-top: 20px; color: #666;'>{options.company_name} - Compliance Report</p>")

        html_parts.append("</body></html>")

        return "\n".join(html_parts)


# ============================================================
# REPORT TEMPLATE
# ============================================================

@dataclass
class TemplateSection:
    """Section within a report template."""
    section_id: str = ""
    name: str = ""
    section_type: str = ""  # HEADER, SUMMARY, TABLE, CHART, FOOTER
    content: str = ""
    data_binding: str = ""  # Field to bind data to
    visible: bool = True
    order: int = 0


@dataclass
class ReportTemplate:
    """
    Customizable report template.

    Allows customization of:
    - Report layout
    - Fields included
    - Sorting and filtering
    - Branding
    """

    template_id: str = field(default_factory=lambda: f"TPL-{str(uuid.uuid4())[:8]}")
    name: str = ""
    description: str = ""
    base_report: str = ""  # Report ID this template is based on

    # Sections
    sections: List[TemplateSection] = field(default_factory=list)

    # Field customization
    included_fields: List[str] = field(default_factory=list)
    field_labels: Dict[str, str] = field(default_factory=dict)  # Custom labels
    field_formats: Dict[str, str] = field(default_factory=dict)  # date, currency, etc.

    # Filtering
    default_filters: Dict[str, Any] = field(default_factory=dict)
    allowed_filters: List[str] = field(default_factory=list)

    # Sorting
    default_sort_field: str = ""
    default_sort_direction: str = "ASC"

    # Branding
    header_text: str = ""
    footer_text: str = ""
    logo_position: str = "TOP_LEFT"
    primary_color: str = "#4CAF50"

    # Access
    owner: str = ""
    is_public: bool = False
    created_at: datetime = field(default_factory=datetime.now)

    def add_section(
        self,
        name: str,
        section_type: str,
        content: str = "",
        data_binding: str = "",
    ) -> TemplateSection:
        """Add a section to the template."""
        section = TemplateSection(
            section_id=f"SEC-{len(self.sections) + 1}",
            name=name,
            section_type=section_type,
            content=content,
            data_binding=data_binding,
            order=len(self.sections),
        )
        self.sections.append(section)
        return section

    def apply_to_result(self, result: ReportResult) -> ReportResult:
        """Apply template customizations to a report result."""
        # Filter fields
        if self.included_fields:
            filtered_records = []
            for record in result.records:
                filtered_records.append({
                    k: v for k, v in record.items()
                    if k in self.included_fields
                })
            result.records = filtered_records

        # Apply field labels
        if self.field_labels:
            renamed_records = []
            for record in result.records:
                renamed = {}
                for k, v in record.items():
                    new_key = self.field_labels.get(k, k)
                    renamed[new_key] = v
                renamed_records.append(renamed)
            result.records = renamed_records

        # Sort
        if self.default_sort_field and result.records:
            reverse = self.default_sort_direction == "DESC"
            try:
                result.records = sorted(
                    result.records,
                    key=lambda x: x.get(self.default_sort_field, ""),
                    reverse=reverse,
                )
            except (TypeError, KeyError):
                pass  # Skip sort if field not found or not sortable

        return result

    def to_dict(self) -> Dict[str, Any]:
        return {
            "template_id": self.template_id,
            "name": self.name,
            "description": self.description,
            "base_report": self.base_report,
            "sections": [
                {
                    "section_id": s.section_id,
                    "name": s.name,
                    "section_type": s.section_type,
                    "order": s.order,
                }
                for s in self.sections
            ],
            "included_fields": self.included_fields,
            "field_labels": self.field_labels,
            "owner": self.owner,
            "is_public": self.is_public,
        }


# ============================================================
# FACTORY FUNCTIONS
# ============================================================

def create_report_engine() -> ReportEngine:
    """Create a configured report engine."""
    engine = ReportEngine()
    # Register standard reports
    for report_id, definition in STANDARD_REPORTS.items():
        engine.report_registry[report_id] = definition
    return engine


def create_report_scheduler(engine: ReportEngine) -> ReportScheduler:
    """Create a report scheduler linked to an engine."""
    scheduler = ReportScheduler(engine=engine)
    return scheduler


def create_standard_template(
    name: str,
    base_report: str,
    included_fields: List[str],
) -> ReportTemplate:
    """Create a standard report template."""
    template = ReportTemplate(
        name=name,
        base_report=base_report,
        included_fields=included_fields,
    )

    # Add default sections
    template.add_section("Header", "HEADER")
    template.add_section("Summary", "SUMMARY", data_binding="summary")
    template.add_section("Data", "TABLE", data_binding="records")
    template.add_section("Footer", "FOOTER")

    return template


def create_sod_audit_template() -> ReportTemplate:
    """Create a template specifically for SoD audit reports."""
    template = ReportTemplate(
        name="SoD Audit Report",
        description="Standard format for SoD conflict audits",
        base_report="SOD_CONFLICTS",
        included_fields=[
            "violation_id", "username", "user_department",
            "rule_name", "function_1", "function_2",
            "risk_level", "status", "is_mitigated",
        ],
        field_labels={
            "violation_id": "Violation ID",
            "username": "User",
            "user_department": "Department",
            "rule_name": "SoD Rule",
            "function_1": "Function 1",
            "function_2": "Function 2",
            "risk_level": "Risk Level",
            "status": "Status",
            "is_mitigated": "Mitigated?",
        },
        default_sort_field="risk_level",
        default_sort_direction="DESC",
        header_text="Segregation of Duties Conflict Report",
        footer_text="Confidential - For Audit Purposes Only",
    )

    template.add_section("Executive Summary", "SUMMARY")
    template.add_section("Violation Details", "TABLE")
    template.add_section("Risk Distribution", "CHART")

    return template


def create_firefighter_audit_template() -> ReportTemplate:
    """Create a template for firefighter usage audits."""
    template = ReportTemplate(
        name="Firefighter Usage Audit",
        description="Emergency access usage report for audit",
        base_report="FF_USAGE",
        included_fields=[
            "usage_id", "ff_id", "username", "user_department",
            "checkout_time", "checkin_time", "duration_minutes",
            "reason", "ticket_number", "actions_performed",
            "critical_actions", "reviewed", "reviewed_by",
        ],
        field_labels={
            "usage_id": "Session ID",
            "ff_id": "Firefighter ID",
            "username": "User",
            "checkout_time": "Start Time",
            "checkin_time": "End Time",
            "duration_minutes": "Duration (min)",
            "actions_performed": "Actions",
            "critical_actions": "Critical Actions",
            "reviewed": "Reviewed?",
        },
        default_sort_field="checkout_time",
        default_sort_direction="DESC",
    )

    return template
