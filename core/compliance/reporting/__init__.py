# Compliance Reporting Module
# Auditor-Ready Reports for GOVERNEX+

"""
Compliance Reporting Engine for GOVERNEX+.

This module provides all reports auditors request during SOX, SOC2, and IT audits.
Equivalent to SAP GRC SUIM but with modern features.

Report Categories:
1. User Master Data & Basic Lists
2. Role & Authorization Assignments
3. Critical & Sensitive Authorizations
4. Segregation of Duties (SoD) Conflicts
5. Privileged / Emergency / Firefighter Access
6. Change Logs for User & Role Maintenance
7. Login & Security Audit Logs

Key Improvements over SAP SUIM:
- Real-time dashboards
- Risk-scored results
- Automated anomaly detection
- Scheduled report generation
- Export to multiple formats
- API access for integration
"""

from .user_reports import (
    UserMasterReport,
    UserListReport,
    TerminatedUserReport,
    GenericUserReport,
    PasswordPolicyReport,
    ConcurrentSessionReport,
    UserComparisonReport,
)

from .role_reports import (
    RoleAssignmentReport,
    UsersByRoleReport,
    RolesByUserReport,
    CriticalRoleReport,
    RoleComparisonReport,
    OrphanedRoleReport,
)

from .authorization_reports import (
    CriticalTransactionReport,
    AuthorizationObjectReport,
    SensitiveAccessReport,
    TransactionUsageReport,
    DirectTableAccessReport,
)

from .sod_reports import (
    SoDConflictReport,
    SoDViolationSummary,
    SoDRiskMatrix,
    SoDMitigationReport,
    SoDTrendAnalysis,
)

from .firefighter_reports import (
    FirefighterUsageReport,
    FirefighterLogReport,
    EmergencyAccessSummary,
    SuperuserActivityReport,
    PrivilegedAccessReview,
)

from .change_reports import (
    UserChangeLog,
    RoleChangeLog,
    AuthorizationChangeLog,
    AccessChangeTimeline,
    ProvisioningAuditTrail,
)

from .security_reports import (
    LoginAuditReport,
    FailedLoginReport,
    SecurityEventLog,
    AnomalousAccessReport,
    ComplianceScorecard,
)

from .dashboard import (
    AuditorDashboard,
    ComplianceMetrics,
    RiskHeatmap,
    TrendAnalytics,
)

from .engine import (
    ReportEngine,
    ReportScheduler,
    ReportExporter,
    ReportTemplate,
)

__all__ = [
    # User Reports
    "UserMasterReport",
    "UserListReport",
    "TerminatedUserReport",
    "GenericUserReport",
    "PasswordPolicyReport",
    "ConcurrentSessionReport",
    "UserComparisonReport",
    # Role Reports
    "RoleAssignmentReport",
    "UsersByRoleReport",
    "RolesByUserReport",
    "CriticalRoleReport",
    "RoleComparisonReport",
    "OrphanedRoleReport",
    # Authorization Reports
    "CriticalTransactionReport",
    "AuthorizationObjectReport",
    "SensitiveAccessReport",
    "TransactionUsageReport",
    "DirectTableAccessReport",
    # SoD Reports
    "SoDConflictReport",
    "SoDViolationSummary",
    "SoDRiskMatrix",
    "SoDMitigationReport",
    "SoDTrendAnalysis",
    # Firefighter Reports
    "FirefighterUsageReport",
    "FirefighterLogReport",
    "EmergencyAccessSummary",
    "SuperuserActivityReport",
    "PrivilegedAccessReview",
    # Change Reports
    "UserChangeLog",
    "RoleChangeLog",
    "AuthorizationChangeLog",
    "AccessChangeTimeline",
    "ProvisioningAuditTrail",
    # Security Reports
    "LoginAuditReport",
    "FailedLoginReport",
    "SecurityEventLog",
    "AnomalousAccessReport",
    "ComplianceScorecard",
    # Dashboard
    "AuditorDashboard",
    "ComplianceMetrics",
    "RiskHeatmap",
    "TrendAnalytics",
    # Engine
    "ReportEngine",
    "ReportScheduler",
    "ReportExporter",
    "ReportTemplate",
]
