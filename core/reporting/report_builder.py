"""
Advanced Report Builder

SAP GRC-equivalent report generation with custom report builder,
templates, scheduling, and multi-format export.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union
from enum import Enum
from datetime import datetime, date, timedelta
import json
import csv
import io
import uuid


class ReportType(Enum):
    """Standard report types"""
    # Risk Reports
    SOD_VIOLATIONS = "sod_violations"
    SENSITIVE_ACCESS = "sensitive_access"
    RISK_SUMMARY = "risk_summary"
    RISK_TRENDS = "risk_trends"

    # User Reports
    USER_ACCESS = "user_access"
    USER_ROLES = "user_roles"
    USER_ACTIVITY = "user_activity"
    ORPHAN_ACCOUNTS = "orphan_accounts"

    # Role Reports
    ROLE_USAGE = "role_usage"
    ROLE_OWNERS = "role_owners"
    UNUSED_ROLES = "unused_roles"
    ROLE_CONFLICTS = "role_conflicts"

    # Firefighter Reports
    FIREFIGHTER_USAGE = "firefighter_usage"
    FIREFIGHTER_SESSIONS = "firefighter_sessions"
    EMERGENCY_ACCESS_AUDIT = "emergency_access_audit"

    # Compliance Reports
    COMPLIANCE_STATUS = "compliance_status"
    CONTROL_EFFECTIVENESS = "control_effectiveness"
    AUDIT_TRAIL = "audit_trail"
    CERTIFICATION_STATUS = "certification_status"

    # Access Request Reports
    REQUEST_STATUS = "request_status"
    APPROVAL_METRICS = "approval_metrics"
    SLA_COMPLIANCE = "sla_compliance"

    # Custom
    CUSTOM = "custom"


class OutputFormat(Enum):
    """Report output formats"""
    JSON = "json"
    CSV = "csv"
    EXCEL = "excel"
    PDF = "pdf"
    HTML = "html"


class AggregationType(Enum):
    """Data aggregation types"""
    COUNT = "count"
    SUM = "sum"
    AVG = "avg"
    MIN = "min"
    MAX = "max"
    DISTINCT = "distinct"


@dataclass
class ReportColumn:
    """Report column definition"""
    name: str
    display_name: str
    data_type: str = "string"  # string, number, date, boolean
    width: int = 100
    sortable: bool = True
    filterable: bool = True
    aggregation: Optional[AggregationType] = None
    format_string: str = ""  # e.g., "{:.2f}" for numbers, "%Y-%m-%d" for dates
    visible: bool = True


@dataclass
class ReportFilter:
    """Report filter definition"""
    field: str
    operator: str  # eq, ne, gt, lt, gte, lte, contains, in, between
    value: Any
    value2: Any = None  # For 'between' operator


@dataclass
class ReportSort:
    """Report sort definition"""
    field: str
    direction: str = "asc"  # asc, desc


@dataclass
class ReportDefinition:
    """Custom report definition"""
    report_id: str
    tenant_id: str
    name: str
    description: str
    report_type: ReportType

    # Data source
    data_source: str  # Table/view name or query identifier
    base_query: str = ""  # SQL or query definition

    # Columns
    columns: List[ReportColumn] = field(default_factory=list)

    # Default filters and sorting
    default_filters: List[ReportFilter] = field(default_factory=list)
    default_sort: List[ReportSort] = field(default_factory=list)

    # Grouping
    group_by: List[str] = field(default_factory=list)

    # Parameters
    parameters: Dict[str, Any] = field(default_factory=dict)

    # Output
    default_format: OutputFormat = OutputFormat.JSON
    row_limit: int = 10000

    # Scheduling
    is_scheduled: bool = False
    schedule_cron: str = ""
    recipients: List[str] = field(default_factory=list)

    # Metadata
    category: str = ""
    tags: List[str] = field(default_factory=list)
    is_public: bool = False
    created_by: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ReportExecution:
    """Report execution record"""
    execution_id: str
    report_id: str
    tenant_id: str

    # Execution parameters
    filters: List[ReportFilter] = field(default_factory=list)
    parameters: Dict[str, Any] = field(default_factory=dict)
    output_format: OutputFormat = OutputFormat.JSON

    # Status
    status: str = "running"  # running, completed, failed
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None

    # Results
    row_count: int = 0
    file_path: Optional[str] = None
    file_size_bytes: int = 0
    error_message: Optional[str] = None

    # Requester
    requested_by: str = ""


class ReportBuilder:
    """
    Advanced Report Builder

    Provides:
    1. Pre-built standard reports
    2. Custom report designer
    3. Multi-format export (JSON, CSV, Excel, PDF)
    4. Report scheduling
    5. Parameter-driven reports
    6. Drill-down capabilities
    """

    def __init__(self):
        self.definitions: Dict[str, ReportDefinition] = {}
        self.executions: Dict[str, ReportExecution] = {}

        # Initialize standard reports
        self._initialize_standard_reports()

    def _initialize_standard_reports(self):
        """Initialize standard report templates"""

        # SoD Violations Report
        self.create_report_definition(
            tenant_id="__system__",
            name="SoD Violations Report",
            description="Lists all Segregation of Duties violations with user and rule details",
            report_type=ReportType.SOD_VIOLATIONS,
            data_source="risk_violations",
            columns=[
                ReportColumn("violation_id", "Violation ID"),
                ReportColumn("user_id", "User ID"),
                ReportColumn("user_name", "User Name"),
                ReportColumn("department", "Department"),
                ReportColumn("rule_id", "Rule ID"),
                ReportColumn("rule_name", "Rule Name"),
                ReportColumn("risk_level", "Risk Level"),
                ReportColumn("function_1", "Function 1"),
                ReportColumn("function_2", "Function 2"),
                ReportColumn("status", "Status"),
                ReportColumn("detected_at", "Detected Date", data_type="date"),
                ReportColumn("mitigation_id", "Mitigation Control"),
            ],
            category="Risk",
            tags=["sod", "violations", "risk"],
            is_public=True
        )

        # User Access Report
        self.create_report_definition(
            tenant_id="__system__",
            name="User Access Report",
            description="Complete access listing for users including roles and entitlements",
            report_type=ReportType.USER_ACCESS,
            data_source="user_access_view",
            columns=[
                ReportColumn("user_id", "User ID"),
                ReportColumn("user_name", "User Name"),
                ReportColumn("email", "Email"),
                ReportColumn("department", "Department"),
                ReportColumn("manager", "Manager"),
                ReportColumn("role_id", "Role ID"),
                ReportColumn("role_name", "Role Name"),
                ReportColumn("role_type", "Role Type"),
                ReportColumn("risk_level", "Risk Level"),
                ReportColumn("valid_from", "Valid From", data_type="date"),
                ReportColumn("valid_to", "Valid To", data_type="date"),
                ReportColumn("source_system", "System"),
            ],
            category="User",
            tags=["user", "access", "roles"],
            is_public=True
        )

        # Firefighter Usage Report
        self.create_report_definition(
            tenant_id="__system__",
            name="Firefighter Usage Report",
            description="Emergency access usage statistics and trends",
            report_type=ReportType.FIREFIGHTER_USAGE,
            data_source="firefighter_sessions",
            columns=[
                ReportColumn("session_id", "Session ID"),
                ReportColumn("firefighter_id", "Firefighter ID"),
                ReportColumn("user_id", "User"),
                ReportColumn("user_name", "User Name"),
                ReportColumn("reason", "Reason"),
                ReportColumn("started_at", "Start Time", data_type="date"),
                ReportColumn("ended_at", "End Time", data_type="date"),
                ReportColumn("duration_hours", "Duration (hrs)", data_type="number"),
                ReportColumn("activity_count", "Activities"),
                ReportColumn("sensitive_actions", "Sensitive Actions"),
                ReportColumn("review_status", "Review Status"),
            ],
            category="Firefighter",
            tags=["firefighter", "emergency", "eam"],
            is_public=True
        )

        # Compliance Status Report
        self.create_report_definition(
            tenant_id="__system__",
            name="Compliance Status Report",
            description="Overall compliance status across frameworks",
            report_type=ReportType.COMPLIANCE_STATUS,
            data_source="compliance_summary",
            columns=[
                ReportColumn("framework", "Framework"),
                ReportColumn("total_controls", "Total Controls", data_type="number"),
                ReportColumn("compliant", "Compliant", data_type="number"),
                ReportColumn("non_compliant", "Non-Compliant", data_type="number"),
                ReportColumn("not_assessed", "Not Assessed", data_type="number"),
                ReportColumn("compliance_rate", "Compliance %", data_type="number", format_string="{:.1f}%"),
                ReportColumn("last_assessment", "Last Assessment", data_type="date"),
            ],
            category="Compliance",
            tags=["compliance", "audit", "sox", "gdpr"],
            is_public=True
        )

        # Certification Status Report
        self.create_report_definition(
            tenant_id="__system__",
            name="Certification Campaign Status",
            description="Access certification campaign progress and statistics",
            report_type=ReportType.CERTIFICATION_STATUS,
            data_source="certification_campaigns",
            columns=[
                ReportColumn("campaign_id", "Campaign ID"),
                ReportColumn("campaign_name", "Campaign Name"),
                ReportColumn("campaign_type", "Type"),
                ReportColumn("status", "Status"),
                ReportColumn("start_date", "Start Date", data_type="date"),
                ReportColumn("end_date", "End Date", data_type="date"),
                ReportColumn("total_items", "Total Items", data_type="number"),
                ReportColumn("completed", "Completed", data_type="number"),
                ReportColumn("certified", "Certified", data_type="number"),
                ReportColumn("revoked", "Revoked", data_type="number"),
                ReportColumn("completion_rate", "Completion %", data_type="number", format_string="{:.1f}%"),
            ],
            category="Certification",
            tags=["certification", "review", "attestation"],
            is_public=True
        )

        # Risk Trends Report
        self.create_report_definition(
            tenant_id="__system__",
            name="Risk Trends Report",
            description="Historical risk metrics and trends over time",
            report_type=ReportType.RISK_TRENDS,
            data_source="risk_metrics_history",
            columns=[
                ReportColumn("period", "Period", data_type="date"),
                ReportColumn("total_violations", "Total Violations", data_type="number"),
                ReportColumn("critical_violations", "Critical", data_type="number"),
                ReportColumn("high_violations", "High", data_type="number"),
                ReportColumn("medium_violations", "Medium", data_type="number"),
                ReportColumn("mitigated", "Mitigated", data_type="number"),
                ReportColumn("remediated", "Remediated", data_type="number"),
                ReportColumn("average_risk_score", "Avg Risk Score", data_type="number", format_string="{:.1f}"),
            ],
            group_by=["period"],
            category="Risk",
            tags=["risk", "trends", "analytics"],
            is_public=True
        )

        # SLA Compliance Report
        self.create_report_definition(
            tenant_id="__system__",
            name="SLA Compliance Report",
            description="Access request SLA compliance metrics",
            report_type=ReportType.SLA_COMPLIANCE,
            data_source="access_requests",
            columns=[
                ReportColumn("period", "Period"),
                ReportColumn("total_requests", "Total Requests", data_type="number"),
                ReportColumn("completed_on_time", "On Time", data_type="number"),
                ReportColumn("completed_late", "Late", data_type="number"),
                ReportColumn("pending", "Pending", data_type="number"),
                ReportColumn("sla_compliance_rate", "SLA %", data_type="number", format_string="{:.1f}%"),
                ReportColumn("avg_completion_hours", "Avg Hours", data_type="number", format_string="{:.1f}"),
            ],
            category="Operations",
            tags=["sla", "performance", "requests"],
            is_public=True
        )

    # ==================== Report Definition Management ====================

    def create_report_definition(
        self,
        tenant_id: str,
        name: str,
        description: str,
        report_type: ReportType,
        data_source: str,
        columns: List[ReportColumn] = None,
        default_filters: List[ReportFilter] = None,
        default_sort: List[ReportSort] = None,
        group_by: List[str] = None,
        parameters: Dict[str, Any] = None,
        category: str = "",
        tags: List[str] = None,
        is_public: bool = False,
        created_by: str = ""
    ) -> ReportDefinition:
        """Create a new report definition"""
        report_id = f"RPT_{report_type.value}_{uuid.uuid4().hex[:8]}"

        definition = ReportDefinition(
            report_id=report_id,
            tenant_id=tenant_id,
            name=name,
            description=description,
            report_type=report_type,
            data_source=data_source,
            columns=columns or [],
            default_filters=default_filters or [],
            default_sort=default_sort or [],
            group_by=group_by or [],
            parameters=parameters or {},
            category=category,
            tags=tags or [],
            is_public=is_public,
            created_by=created_by
        )

        self.definitions[report_id] = definition
        return definition

    def get_report_definition(self, report_id: str) -> Optional[ReportDefinition]:
        """Get report definition by ID"""
        return self.definitions.get(report_id)

    def get_reports_by_tenant(
        self,
        tenant_id: str,
        include_system: bool = True
    ) -> List[ReportDefinition]:
        """Get all reports available to a tenant"""
        reports = []

        for report in self.definitions.values():
            if report.tenant_id == tenant_id:
                reports.append(report)
            elif include_system and report.tenant_id == "__system__" and report.is_public:
                reports.append(report)

        return reports

    def get_reports_by_category(
        self,
        tenant_id: str,
        category: str
    ) -> List[ReportDefinition]:
        """Get reports by category"""
        return [
            r for r in self.get_reports_by_tenant(tenant_id)
            if r.category.lower() == category.lower()
        ]

    def search_reports(
        self,
        tenant_id: str,
        query: str
    ) -> List[ReportDefinition]:
        """Search reports by name, description, or tags"""
        query_lower = query.lower()
        results = []

        for report in self.get_reports_by_tenant(tenant_id):
            if (query_lower in report.name.lower() or
                query_lower in report.description.lower() or
                any(query_lower in tag.lower() for tag in report.tags)):
                results.append(report)

        return results

    # ==================== Report Execution ====================

    def execute_report(
        self,
        report_id: str,
        tenant_id: str,
        filters: List[ReportFilter] = None,
        parameters: Dict[str, Any] = None,
        output_format: OutputFormat = OutputFormat.JSON,
        requested_by: str = ""
    ) -> ReportExecution:
        """Execute a report and return results"""
        definition = self.definitions.get(report_id)
        if not definition:
            raise ValueError(f"Report not found: {report_id}")

        execution_id = f"EXEC_{report_id}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"

        execution = ReportExecution(
            execution_id=execution_id,
            report_id=report_id,
            tenant_id=tenant_id,
            filters=filters or definition.default_filters,
            parameters=parameters or definition.parameters,
            output_format=output_format,
            requested_by=requested_by
        )

        self.executions[execution_id] = execution

        try:
            # Generate report data
            data = self._generate_report_data(definition, execution)

            # Format output
            output = self._format_output(definition, data, output_format)

            execution.status = "completed"
            execution.completed_at = datetime.utcnow()
            execution.row_count = len(data)
            execution.file_size_bytes = len(str(output))

            return execution

        except Exception as e:
            execution.status = "failed"
            execution.error_message = str(e)
            execution.completed_at = datetime.utcnow()
            return execution

    def _generate_report_data(
        self,
        definition: ReportDefinition,
        execution: ReportExecution
    ) -> List[Dict[str, Any]]:
        """Generate report data (would query actual data source in production)"""
        # This is a simulation - in production, this would:
        # 1. Build SQL query from definition
        # 2. Apply filters and parameters
        # 3. Execute against database
        # 4. Return results

        # Simulated data based on report type
        if definition.report_type == ReportType.SOD_VIOLATIONS:
            return self._generate_sod_violations_data(execution)
        elif definition.report_type == ReportType.USER_ACCESS:
            return self._generate_user_access_data(execution)
        elif definition.report_type == ReportType.FIREFIGHTER_USAGE:
            return self._generate_firefighter_data(execution)
        elif definition.report_type == ReportType.COMPLIANCE_STATUS:
            return self._generate_compliance_data(execution)
        elif definition.report_type == ReportType.CERTIFICATION_STATUS:
            return self._generate_certification_data(execution)
        elif definition.report_type == ReportType.RISK_TRENDS:
            return self._generate_risk_trends_data(execution)
        else:
            return []

    def _generate_sod_violations_data(self, execution: ReportExecution) -> List[Dict[str, Any]]:
        """Generate sample SoD violations data"""
        return [
            {
                "violation_id": "VIO_001",
                "user_id": "JSMITH",
                "user_name": "John Smith",
                "department": "Finance",
                "rule_id": "SOD_P2P_001",
                "rule_name": "P2P: Create PO & Approve PO",
                "risk_level": "high",
                "function_1": "Create Purchase Order",
                "function_2": "Approve Purchase Order",
                "status": "open",
                "detected_at": "2026-01-15",
                "mitigation_id": None
            },
            {
                "violation_id": "VIO_002",
                "user_id": "MBROWN",
                "user_name": "Mary Brown",
                "department": "Procurement",
                "rule_id": "SOD_P2P_002",
                "rule_name": "P2P: Vendor Master & Payments",
                "risk_level": "critical",
                "function_1": "Maintain Vendor Master",
                "function_2": "Process Vendor Payments",
                "status": "mitigated",
                "detected_at": "2026-01-10",
                "mitigation_id": "MIT_001"
            },
        ]

    def _generate_user_access_data(self, execution: ReportExecution) -> List[Dict[str, Any]]:
        """Generate sample user access data"""
        return [
            {
                "user_id": "JSMITH",
                "user_name": "John Smith",
                "email": "jsmith@company.com",
                "department": "Finance",
                "manager": "AMANAGER",
                "role_id": "Z_FI_AP_CLERK",
                "role_name": "AP Clerk",
                "role_type": "single",
                "risk_level": "medium",
                "valid_from": "2025-01-01",
                "valid_to": "2026-12-31",
                "source_system": "SAP_ECC_PRD"
            },
        ]

    def _generate_firefighter_data(self, execution: ReportExecution) -> List[Dict[str, Any]]:
        """Generate sample firefighter usage data"""
        return [
            {
                "session_id": "FF_SESSION_001",
                "firefighter_id": "FF_EMERGENCY_01",
                "user_id": "TDAVIS",
                "user_name": "Tom Davis",
                "reason": "Production incident - order processing failure",
                "started_at": "2026-01-16 14:30:00",
                "ended_at": "2026-01-16 16:45:00",
                "duration_hours": 2.25,
                "activity_count": 45,
                "sensitive_actions": 3,
                "review_status": "pending"
            },
        ]

    def _generate_compliance_data(self, execution: ReportExecution) -> List[Dict[str, Any]]:
        """Generate sample compliance data"""
        return [
            {
                "framework": "SOX",
                "total_controls": 50,
                "compliant": 45,
                "non_compliant": 3,
                "not_assessed": 2,
                "compliance_rate": 90.0,
                "last_assessment": "2026-01-01"
            },
            {
                "framework": "GDPR",
                "total_controls": 30,
                "compliant": 28,
                "non_compliant": 1,
                "not_assessed": 1,
                "compliance_rate": 93.3,
                "last_assessment": "2026-01-05"
            },
        ]

    def _generate_certification_data(self, execution: ReportExecution) -> List[Dict[str, Any]]:
        """Generate sample certification data"""
        return [
            {
                "campaign_id": "CERT_2026_Q1",
                "campaign_name": "Q1 2026 User Access Review",
                "campaign_type": "user_access",
                "status": "active",
                "start_date": "2026-01-01",
                "end_date": "2026-01-31",
                "total_items": 500,
                "completed": 350,
                "certified": 320,
                "revoked": 30,
                "completion_rate": 70.0
            },
        ]

    def _generate_risk_trends_data(self, execution: ReportExecution) -> List[Dict[str, Any]]:
        """Generate sample risk trends data"""
        data = []
        base_date = datetime.utcnow() - timedelta(days=180)

        for i in range(6):
            period_date = base_date + timedelta(days=30 * i)
            data.append({
                "period": period_date.strftime("%Y-%m"),
                "total_violations": 150 - (i * 10),
                "critical_violations": 20 - (i * 2),
                "high_violations": 50 - (i * 5),
                "medium_violations": 80 - (i * 3),
                "mitigated": 30 + (i * 5),
                "remediated": 20 + (i * 3),
                "average_risk_score": 65 - (i * 3)
            })

        return data

    def _format_output(
        self,
        definition: ReportDefinition,
        data: List[Dict[str, Any]],
        output_format: OutputFormat
    ) -> Union[str, bytes]:
        """Format report output"""
        if output_format == OutputFormat.JSON:
            return json.dumps({
                "report": {
                    "id": definition.report_id,
                    "name": definition.name,
                    "generated_at": datetime.utcnow().isoformat()
                },
                "data": data,
                "row_count": len(data)
            }, indent=2, default=str)

        elif output_format == OutputFormat.CSV:
            if not data:
                return ""

            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=data[0].keys())
            writer.writeheader()
            writer.writerows(data)
            return output.getvalue()

        elif output_format == OutputFormat.HTML:
            return self._generate_html_report(definition, data)

        else:
            # For Excel and PDF, would use libraries like openpyxl, reportlab
            return json.dumps(data, default=str)

    def _generate_html_report(
        self,
        definition: ReportDefinition,
        data: List[Dict[str, Any]]
    ) -> str:
        """Generate HTML report"""
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>{definition.name}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        h1 {{ color: #333; }}
        table {{ border-collapse: collapse; width: 100%; margin-top: 20px; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #4CAF50; color: white; }}
        tr:nth-child(even) {{ background-color: #f2f2f2; }}
        .header {{ margin-bottom: 20px; }}
        .footer {{ margin-top: 20px; font-size: 12px; color: #666; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>{definition.name}</h1>
        <p>{definition.description}</p>
        <p>Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC</p>
        <p>Total Records: {len(data)}</p>
    </div>

    <table>
        <thead>
            <tr>
"""
        # Headers
        if data:
            for key in data[0].keys():
                col = next((c for c in definition.columns if c.name == key), None)
                display_name = col.display_name if col else key
                html += f"                <th>{display_name}</th>\n"

        html += """            </tr>
        </thead>
        <tbody>
"""
        # Data rows
        for row in data:
            html += "            <tr>\n"
            for value in row.values():
                html += f"                <td>{value}</td>\n"
            html += "            </tr>\n"

        html += """        </tbody>
    </table>

    <div class="footer">
        <p>GRC Zero Trust Platform - Report Builder</p>
    </div>
</body>
</html>
"""
        return html

    # ==================== Report Scheduling ====================

    def schedule_report(
        self,
        report_id: str,
        cron_expression: str,
        recipients: List[str],
        output_format: OutputFormat = OutputFormat.PDF
    ) -> ReportDefinition:
        """Schedule a report for recurring execution"""
        definition = self.definitions.get(report_id)
        if not definition:
            raise ValueError(f"Report not found: {report_id}")

        definition.is_scheduled = True
        definition.schedule_cron = cron_expression
        definition.recipients = recipients
        definition.default_format = output_format
        definition.updated_at = datetime.utcnow()

        return definition

    def unschedule_report(self, report_id: str) -> bool:
        """Remove report from schedule"""
        definition = self.definitions.get(report_id)
        if definition:
            definition.is_scheduled = False
            definition.schedule_cron = ""
            definition.recipients = []
            definition.updated_at = datetime.utcnow()
            return True
        return False

    def get_scheduled_reports(self, tenant_id: str) -> List[ReportDefinition]:
        """Get all scheduled reports for a tenant"""
        return [
            r for r in self.definitions.values()
            if r.tenant_id == tenant_id and r.is_scheduled
        ]

    # ==================== Report Templates ====================

    def clone_report(
        self,
        report_id: str,
        new_name: str,
        tenant_id: str,
        created_by: str
    ) -> ReportDefinition:
        """Clone an existing report as a new custom report"""
        source = self.definitions.get(report_id)
        if not source:
            raise ValueError(f"Report not found: {report_id}")

        new_report = self.create_report_definition(
            tenant_id=tenant_id,
            name=new_name,
            description=f"Cloned from: {source.name}",
            report_type=source.report_type,
            data_source=source.data_source,
            columns=source.columns.copy(),
            default_filters=source.default_filters.copy(),
            default_sort=source.default_sort.copy(),
            group_by=source.group_by.copy(),
            parameters=source.parameters.copy(),
            category=source.category,
            tags=source.tags.copy(),
            is_public=False,
            created_by=created_by
        )

        return new_report

    # ==================== Execution History ====================

    def get_execution_history(
        self,
        report_id: str = None,
        tenant_id: str = None,
        limit: int = 100
    ) -> List[ReportExecution]:
        """Get report execution history"""
        executions = list(self.executions.values())

        if report_id:
            executions = [e for e in executions if e.report_id == report_id]
        if tenant_id:
            executions = [e for e in executions if e.tenant_id == tenant_id]

        executions.sort(key=lambda e: e.started_at, reverse=True)
        return executions[:limit]


# Singleton instance
report_builder = ReportBuilder()
