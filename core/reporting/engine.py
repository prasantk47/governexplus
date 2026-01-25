"""
Reporting & Analytics Engine

Provides comprehensive reporting capabilities including
templates, scheduling, and multiple output formats.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from enum import Enum
import uuid
import json


class ReportType(Enum):
    """Types of reports"""
    EXECUTIVE_SUMMARY = "executive_summary"
    RISK_ANALYSIS = "risk_analysis"
    SOD_VIOLATIONS = "sod_violations"
    ACCESS_REVIEW = "access_review"
    CERTIFICATION = "certification"
    FIREFIGHTER = "firefighter"
    COMPLIANCE = "compliance"
    USER_ACCESS = "user_access"
    ROLE_ANALYSIS = "role_analysis"
    AUDIT_TRAIL = "audit_trail"
    CUSTOM = "custom"


class ReportFormat(Enum):
    """Output formats for reports"""
    JSON = "json"
    CSV = "csv"
    PDF = "pdf"
    EXCEL = "excel"
    HTML = "html"


class ScheduleFrequency(Enum):
    """Report scheduling frequency"""
    ONCE = "once"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"


@dataclass
class ReportParameter:
    """A parameter for report customization"""
    name: str
    display_name: str
    param_type: str  # string, date, list, boolean, number
    required: bool = False
    default_value: Any = None
    options: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "display_name": self.display_name,
            "param_type": self.param_type,
            "required": self.required,
            "default_value": self.default_value,
            "options": self.options
        }


@dataclass
class ReportTemplate:
    """A reusable report template"""
    template_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    description: str = ""
    report_type: ReportType = ReportType.CUSTOM
    category: str = ""

    # Template structure
    sections: List[Dict] = field(default_factory=list)
    parameters: List[ReportParameter] = field(default_factory=list)

    # Formatting
    supported_formats: List[ReportFormat] = field(default_factory=list)
    default_format: ReportFormat = ReportFormat.JSON

    # Access
    is_public: bool = True
    owner: str = ""
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict:
        return {
            "template_id": self.template_id,
            "name": self.name,
            "description": self.description,
            "report_type": self.report_type.value,
            "category": self.category,
            "sections": self.sections,
            "parameters": [p.to_dict() for p in self.parameters],
            "supported_formats": [f.value for f in self.supported_formats],
            "default_format": self.default_format.value,
            "is_public": self.is_public,
            "owner": self.owner,
            "created_at": self.created_at.isoformat()
        }


@dataclass
class ReportSchedule:
    """Schedule for automated report generation"""
    schedule_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    template_id: str = ""
    name: str = ""
    frequency: ScheduleFrequency = ScheduleFrequency.WEEKLY
    is_active: bool = True

    # Schedule details
    day_of_week: int = 0  # 0=Monday for weekly
    day_of_month: int = 1  # For monthly
    time_of_day: str = "08:00"

    # Parameters
    parameters: Dict[str, Any] = field(default_factory=dict)
    output_format: ReportFormat = ReportFormat.PDF

    # Distribution
    recipients: List[str] = field(default_factory=list)
    email_subject: str = ""
    include_attachment: bool = True

    # Tracking
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    run_count: int = 0
    created_by: str = ""

    def to_dict(self) -> Dict:
        return {
            "schedule_id": self.schedule_id,
            "template_id": self.template_id,
            "name": self.name,
            "frequency": self.frequency.value,
            "is_active": self.is_active,
            "day_of_week": self.day_of_week,
            "day_of_month": self.day_of_month,
            "time_of_day": self.time_of_day,
            "parameters": self.parameters,
            "output_format": self.output_format.value,
            "recipients": self.recipients,
            "email_subject": self.email_subject,
            "include_attachment": self.include_attachment,
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "next_run": self.next_run.isoformat() if self.next_run else None,
            "run_count": self.run_count,
            "created_by": self.created_by
        }


@dataclass
class Report:
    """A generated report"""
    report_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    template_id: str = ""
    name: str = ""
    report_type: ReportType = ReportType.CUSTOM

    # Generation details
    generated_at: datetime = field(default_factory=datetime.now)
    generated_by: str = ""
    parameters_used: Dict[str, Any] = field(default_factory=dict)
    format: ReportFormat = ReportFormat.JSON

    # Content
    data: Dict[str, Any] = field(default_factory=dict)
    summary: Dict[str, Any] = field(default_factory=dict)
    sections: List[Dict] = field(default_factory=list)

    # Status
    status: str = "completed"  # generating, completed, failed
    error_message: str = ""

    # Storage
    file_path: str = ""
    file_size: int = 0

    def to_dict(self) -> Dict:
        return {
            "report_id": self.report_id,
            "template_id": self.template_id,
            "name": self.name,
            "report_type": self.report_type.value,
            "generated_at": self.generated_at.isoformat(),
            "generated_by": self.generated_by,
            "parameters_used": self.parameters_used,
            "format": self.format.value,
            "summary": self.summary,
            "status": self.status,
            "error_message": self.error_message
        }


class ReportingEngine:
    """
    Reporting & Analytics Engine.

    Provides comprehensive reporting capabilities including:
    - Pre-built report templates
    - Custom report builder
    - Multiple output formats
    - Scheduled report generation
    - Report distribution
    """

    def __init__(self):
        self.templates: Dict[str, ReportTemplate] = {}
        self.schedules: Dict[str, ReportSchedule] = {}
        self.reports: Dict[str, Report] = {}
        self._initialize_standard_templates()

    def _initialize_standard_templates(self):
        """Initialize standard report templates"""
        # Executive Summary
        self.templates["exec_summary"] = ReportTemplate(
            template_id="exec_summary",
            name="Executive Summary Report",
            description="High-level overview of GRC status",
            report_type=ReportType.EXECUTIVE_SUMMARY,
            category="Executive",
            sections=[
                {"id": "overview", "name": "Overview", "order": 1},
                {"id": "risk_summary", "name": "Risk Summary", "order": 2},
                {"id": "compliance", "name": "Compliance Status", "order": 3},
                {"id": "key_metrics", "name": "Key Metrics", "order": 4},
                {"id": "recommendations", "name": "Recommendations", "order": 5}
            ],
            parameters=[
                ReportParameter("date_from", "From Date", "date", required=True),
                ReportParameter("date_to", "To Date", "date", required=True)
            ],
            supported_formats=[ReportFormat.PDF, ReportFormat.HTML, ReportFormat.JSON],
            default_format=ReportFormat.PDF
        )

        # SoD Violations Report
        self.templates["sod_violations"] = ReportTemplate(
            template_id="sod_violations",
            name="SoD Violations Report",
            description="Detailed SoD violations and conflicts",
            report_type=ReportType.SOD_VIOLATIONS,
            category="Risk",
            sections=[
                {"id": "summary", "name": "Violation Summary", "order": 1},
                {"id": "by_severity", "name": "By Severity", "order": 2},
                {"id": "by_user", "name": "By User", "order": 3},
                {"id": "by_rule", "name": "By Rule", "order": 4},
                {"id": "mitigations", "name": "Mitigations", "order": 5}
            ],
            parameters=[
                ReportParameter("severity", "Severity Filter", "list", options=["all", "critical", "high", "medium", "low"]),
                ReportParameter("department", "Department", "string"),
                ReportParameter("include_mitigated", "Include Mitigated", "boolean", default_value=True)
            ],
            supported_formats=[ReportFormat.PDF, ReportFormat.EXCEL, ReportFormat.CSV, ReportFormat.JSON],
            default_format=ReportFormat.PDF
        )

        # User Access Report
        self.templates["user_access"] = ReportTemplate(
            template_id="user_access",
            name="User Access Report",
            description="Complete user access across all systems",
            report_type=ReportType.USER_ACCESS,
            category="Access",
            sections=[
                {"id": "user_info", "name": "User Information", "order": 1},
                {"id": "roles", "name": "Assigned Roles", "order": 2},
                {"id": "permissions", "name": "Permissions", "order": 3},
                {"id": "risk_summary", "name": "Risk Summary", "order": 4}
            ],
            parameters=[
                ReportParameter("user_id", "User ID", "string", required=True),
                ReportParameter("include_history", "Include History", "boolean", default_value=False)
            ],
            supported_formats=[ReportFormat.PDF, ReportFormat.JSON],
            default_format=ReportFormat.PDF
        )

        # Certification Campaign Report
        self.templates["certification"] = ReportTemplate(
            template_id="certification",
            name="Certification Campaign Report",
            description="Access certification campaign results",
            report_type=ReportType.CERTIFICATION,
            category="Certification",
            sections=[
                {"id": "campaign_summary", "name": "Campaign Summary", "order": 1},
                {"id": "completion", "name": "Completion Status", "order": 2},
                {"id": "decisions", "name": "Certification Decisions", "order": 3},
                {"id": "revocations", "name": "Revocations", "order": 4}
            ],
            parameters=[
                ReportParameter("campaign_id", "Campaign ID", "string", required=True)
            ],
            supported_formats=[ReportFormat.PDF, ReportFormat.EXCEL, ReportFormat.JSON],
            default_format=ReportFormat.PDF
        )

        # Firefighter Usage Report
        self.templates["firefighter"] = ReportTemplate(
            template_id="firefighter",
            name="Firefighter Usage Report",
            description="Emergency access usage and activities",
            report_type=ReportType.FIREFIGHTER,
            category="Emergency Access",
            sections=[
                {"id": "usage_summary", "name": "Usage Summary", "order": 1},
                {"id": "sessions", "name": "Sessions", "order": 2},
                {"id": "activities", "name": "Activities", "order": 3},
                {"id": "alerts", "name": "Alerts", "order": 4}
            ],
            parameters=[
                ReportParameter("date_from", "From Date", "date", required=True),
                ReportParameter("date_to", "To Date", "date", required=True),
                ReportParameter("firefighter_id", "Firefighter ID", "string")
            ],
            supported_formats=[ReportFormat.PDF, ReportFormat.EXCEL, ReportFormat.JSON],
            default_format=ReportFormat.PDF
        )

        # Compliance Report
        self.templates["compliance"] = ReportTemplate(
            template_id="compliance",
            name="Compliance Status Report",
            description="Compliance framework assessment status",
            report_type=ReportType.COMPLIANCE,
            category="Compliance",
            sections=[
                {"id": "overview", "name": "Compliance Overview", "order": 1},
                {"id": "by_framework", "name": "By Framework", "order": 2},
                {"id": "gaps", "name": "Compliance Gaps", "order": 3},
                {"id": "action_items", "name": "Action Items", "order": 4}
            ],
            parameters=[
                ReportParameter("framework", "Framework", "list", options=["all", "SOX", "GDPR", "SOC2"]),
                ReportParameter("include_evidence", "Include Evidence", "boolean", default_value=False)
            ],
            supported_formats=[ReportFormat.PDF, ReportFormat.HTML, ReportFormat.JSON],
            default_format=ReportFormat.PDF
        )

        # Audit Trail Report
        self.templates["audit_trail"] = ReportTemplate(
            template_id="audit_trail",
            name="Audit Trail Report",
            description="Complete audit trail of activities",
            report_type=ReportType.AUDIT_TRAIL,
            category="Audit",
            sections=[
                {"id": "summary", "name": "Activity Summary", "order": 1},
                {"id": "by_action", "name": "By Action Type", "order": 2},
                {"id": "by_user", "name": "By User", "order": 3},
                {"id": "details", "name": "Detailed Log", "order": 4}
            ],
            parameters=[
                ReportParameter("date_from", "From Date", "date", required=True),
                ReportParameter("date_to", "To Date", "date", required=True),
                ReportParameter("action_type", "Action Type", "string"),
                ReportParameter("user_id", "User ID", "string")
            ],
            supported_formats=[ReportFormat.PDF, ReportFormat.EXCEL, ReportFormat.CSV, ReportFormat.JSON],
            default_format=ReportFormat.PDF
        )

    # =========================================================================
    # Template Management
    # =========================================================================

    def create_template(
        self,
        name: str,
        description: str,
        report_type: ReportType,
        category: str,
        sections: List[Dict],
        parameters: List[Dict] = None,
        owner: str = ""
    ) -> ReportTemplate:
        """Create a custom report template"""
        template = ReportTemplate(
            name=name,
            description=description,
            report_type=report_type,
            category=category,
            sections=sections,
            owner=owner,
            is_public=False,
            supported_formats=[ReportFormat.JSON, ReportFormat.PDF, ReportFormat.CSV]
        )

        if parameters:
            for param in parameters:
                template.parameters.append(ReportParameter(**param))

        self.templates[template.template_id] = template
        return template

    def get_template(self, template_id: str) -> Optional[ReportTemplate]:
        """Get a template by ID"""
        return self.templates.get(template_id)

    def list_templates(
        self,
        category: str = None,
        report_type: ReportType = None
    ) -> List[ReportTemplate]:
        """List templates with filters"""
        templates = list(self.templates.values())

        if category:
            templates = [t for t in templates if t.category == category]
        if report_type:
            templates = [t for t in templates if t.report_type == report_type]

        return templates

    # =========================================================================
    # Report Generation
    # =========================================================================

    def generate_report(
        self,
        template_id: str,
        parameters: Dict[str, Any],
        generated_by: str,
        output_format: ReportFormat = None
    ) -> Report:
        """Generate a report from a template"""
        if template_id not in self.templates:
            raise ValueError(f"Template {template_id} not found")

        template = self.templates[template_id]

        report = Report(
            template_id=template_id,
            name=f"{template.name} - {datetime.now().strftime('%Y-%m-%d')}",
            report_type=template.report_type,
            generated_by=generated_by,
            parameters_used=parameters,
            format=output_format or template.default_format
        )

        try:
            # Generate data based on report type
            report.data = self._generate_report_data(template, parameters)
            report.summary = self._generate_summary(template, report.data)
            report.sections = self._populate_sections(template, report.data)
            report.status = "completed"
        except Exception as e:
            report.status = "failed"
            report.error_message = str(e)

        self.reports[report.report_id] = report
        return report

    def _generate_report_data(
        self,
        template: ReportTemplate,
        parameters: Dict
    ) -> Dict:
        """Generate report data based on type"""
        # In a real implementation, this would query actual data sources
        # For demo, return sample data

        if template.report_type == ReportType.EXECUTIVE_SUMMARY:
            return {
                "total_users": 1250,
                "active_sod_violations": 45,
                "critical_violations": 8,
                "compliance_score": 87.5,
                "open_risks": 23,
                "pending_certifications": 156,
                "firefighter_sessions_30d": 12,
                "trends": {
                    "violations": "decreasing",
                    "compliance": "improving"
                }
            }

        elif template.report_type == ReportType.SOD_VIOLATIONS:
            return {
                "total_violations": 45,
                "by_severity": {
                    "critical": 8,
                    "high": 15,
                    "medium": 12,
                    "low": 10
                },
                "by_department": {
                    "Finance": 18,
                    "Procurement": 12,
                    "IT": 8,
                    "HR": 7
                },
                "mitigated": 28,
                "unmitigated": 17,
                "violations": []  # Would contain detailed list
            }

        elif template.report_type == ReportType.COMPLIANCE:
            return {
                "overall_score": 85.5,
                "frameworks": {
                    "SOX": {"score": 92, "gaps": 3},
                    "GDPR": {"score": 78, "gaps": 5},
                    "SOC2": {"score": 88, "gaps": 4}
                },
                "key_controls_compliant": 45,
                "total_key_controls": 52,
                "pending_assessments": 8
            }

        return {"message": "Report data generated"}

    def _generate_summary(
        self,
        template: ReportTemplate,
        data: Dict
    ) -> Dict:
        """Generate report summary"""
        return {
            "report_type": template.report_type.value,
            "generated_at": datetime.now().isoformat(),
            "key_findings": [
                "Summary point 1",
                "Summary point 2"
            ],
            "data_points": len(data)
        }

    def _populate_sections(
        self,
        template: ReportTemplate,
        data: Dict
    ) -> List[Dict]:
        """Populate template sections with data"""
        populated = []
        for section in template.sections:
            populated.append({
                "id": section["id"],
                "name": section["name"],
                "order": section["order"],
                "content": data.get(section["id"], {})
            })
        return populated

    def get_report(self, report_id: str) -> Optional[Report]:
        """Get a report by ID"""
        return self.reports.get(report_id)

    def list_reports(
        self,
        report_type: ReportType = None,
        generated_by: str = None,
        limit: int = 50
    ) -> List[Report]:
        """List generated reports"""
        reports = list(self.reports.values())

        if report_type:
            reports = [r for r in reports if r.report_type == report_type]
        if generated_by:
            reports = [r for r in reports if r.generated_by == generated_by]

        # Sort by generation date
        reports.sort(key=lambda r: r.generated_at, reverse=True)
        return reports[:limit]

    # =========================================================================
    # Scheduling
    # =========================================================================

    def create_schedule(
        self,
        template_id: str,
        name: str,
        frequency: ScheduleFrequency,
        parameters: Dict[str, Any],
        recipients: List[str],
        created_by: str,
        **kwargs
    ) -> ReportSchedule:
        """Create a report schedule"""
        if template_id not in self.templates:
            raise ValueError(f"Template {template_id} not found")

        schedule = ReportSchedule(
            template_id=template_id,
            name=name,
            frequency=frequency,
            parameters=parameters,
            recipients=recipients,
            created_by=created_by
        )

        for key, value in kwargs.items():
            if hasattr(schedule, key):
                setattr(schedule, key, value)

        # Calculate next run
        schedule.next_run = self._calculate_next_run(schedule)

        self.schedules[schedule.schedule_id] = schedule
        return schedule

    def _calculate_next_run(self, schedule: ReportSchedule) -> datetime:
        """Calculate next run time for a schedule"""
        now = datetime.now()

        if schedule.frequency == ScheduleFrequency.DAILY:
            return now + timedelta(days=1)
        elif schedule.frequency == ScheduleFrequency.WEEKLY:
            days_until = (schedule.day_of_week - now.weekday()) % 7
            return now + timedelta(days=days_until or 7)
        elif schedule.frequency == ScheduleFrequency.MONTHLY:
            # Next month, specified day
            if now.day >= schedule.day_of_month:
                month = now.month + 1
                year = now.year + (1 if month > 12 else 0)
                month = month if month <= 12 else 1
            else:
                month = now.month
                year = now.year
            return datetime(year, month, schedule.day_of_month)
        elif schedule.frequency == ScheduleFrequency.QUARTERLY:
            # Next quarter
            quarter_start_month = ((now.month - 1) // 3 + 1) * 3 + 1
            year = now.year + (1 if quarter_start_month > 12 else 0)
            quarter_start_month = quarter_start_month if quarter_start_month <= 12 else 1
            return datetime(year, quarter_start_month, 1)

        return now + timedelta(days=1)

    def run_schedule(self, schedule_id: str) -> Report:
        """Manually run a scheduled report"""
        if schedule_id not in self.schedules:
            raise ValueError(f"Schedule {schedule_id} not found")

        schedule = self.schedules[schedule_id]

        report = self.generate_report(
            template_id=schedule.template_id,
            parameters=schedule.parameters,
            generated_by="SCHEDULER",
            output_format=schedule.output_format
        )

        # Update schedule
        schedule.last_run = datetime.now()
        schedule.next_run = self._calculate_next_run(schedule)
        schedule.run_count += 1

        return report

    def list_schedules(
        self,
        is_active: bool = None
    ) -> List[ReportSchedule]:
        """List report schedules"""
        schedules = list(self.schedules.values())

        if is_active is not None:
            schedules = [s for s in schedules if s.is_active == is_active]

        return schedules

    def get_due_schedules(self) -> List[ReportSchedule]:
        """Get schedules that are due to run"""
        now = datetime.now()
        return [
            s for s in self.schedules.values()
            if s.is_active and s.next_run and s.next_run <= now
        ]

    # =========================================================================
    # Statistics
    # =========================================================================

    def get_statistics(self) -> Dict:
        """Get reporting statistics"""
        return {
            "total_templates": len(self.templates),
            "custom_templates": len([t for t in self.templates.values() if not t.is_public]),
            "total_reports_generated": len(self.reports),
            "active_schedules": len([s for s in self.schedules.values() if s.is_active]),
            "reports_by_type": {
                rt.value: len([r for r in self.reports.values() if r.report_type == rt])
                for rt in ReportType
            }
        }
