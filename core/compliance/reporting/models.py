# Compliance Reporting Models
# Core data structures for all audit reports

"""
Core models for compliance reporting.

These models represent the data structures auditors work with.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Set
from datetime import datetime, date, timedelta
from enum import Enum
import uuid


# ============================================================
# ENUMS
# ============================================================

class UserStatus(Enum):
    """User account status."""
    ACTIVE = "ACTIVE"
    LOCKED = "LOCKED"
    EXPIRED = "EXPIRED"
    TERMINATED = "TERMINATED"
    SUSPENDED = "SUSPENDED"
    PENDING = "PENDING"


class UserType(Enum):
    """Types of users."""
    DIALOG = "DIALOG"           # Regular interactive user
    SYSTEM = "SYSTEM"           # System/technical user
    SERVICE = "SERVICE"         # Service account
    COMMUNICATION = "COMMUNICATION"  # RFC/Integration user
    REFERENCE = "REFERENCE"     # Reference user (no login)
    GENERIC = "GENERIC"         # Generic/shared account
    FIREFIGHTER = "FIREFIGHTER"  # Emergency access
    EXTERNAL = "EXTERNAL"       # Vendor/contractor


class RiskLevel(Enum):
    """Risk levels for access."""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


class ChangeType(Enum):
    """Types of changes tracked."""
    CREATE = "CREATE"
    MODIFY = "MODIFY"
    DELETE = "DELETE"
    LOCK = "LOCK"
    UNLOCK = "UNLOCK"
    ASSIGN = "ASSIGN"
    UNASSIGN = "UNASSIGN"
    EXPIRE = "EXPIRE"
    EXTEND = "EXTEND"


class ReportFormat(Enum):
    """Report export formats."""
    PDF = "PDF"
    EXCEL = "EXCEL"
    CSV = "CSV"
    JSON = "JSON"
    HTML = "HTML"


class ReportFrequency(Enum):
    """Scheduled report frequency."""
    DAILY = "DAILY"
    WEEKLY = "WEEKLY"
    MONTHLY = "MONTHLY"
    QUARTERLY = "QUARTERLY"
    ON_DEMAND = "ON_DEMAND"


# ============================================================
# USER MODELS
# ============================================================

@dataclass
class User:
    """User master record."""
    user_id: str = ""
    username: str = ""
    full_name: str = ""
    email: str = ""

    # Employment
    employee_id: str = ""
    department: str = ""
    cost_center: str = ""
    manager_id: str = ""
    job_title: str = ""

    # Status
    status: UserStatus = UserStatus.ACTIVE
    user_type: UserType = UserType.DIALOG
    is_locked: bool = False
    lock_reason: str = ""

    # Dates
    created_date: Optional[date] = None
    last_login: Optional[datetime] = None
    password_changed: Optional[date] = None
    password_expires: Optional[date] = None
    valid_from: Optional[date] = None
    valid_to: Optional[date] = None
    termination_date: Optional[date] = None

    # Settings
    allow_multiple_logons: bool = False
    password_never_expires: bool = False

    # Risk
    risk_score: int = 0
    risk_level: RiskLevel = RiskLevel.LOW
    sod_conflict_count: int = 0
    critical_access_count: int = 0

    # Assignments
    roles: List[str] = field(default_factory=list)
    profiles: List[str] = field(default_factory=list)
    groups: List[str] = field(default_factory=list)

    # Metadata
    created_by: str = ""
    modified_by: str = ""
    modified_date: Optional[datetime] = None

    def is_terminated(self) -> bool:
        """Check if user is terminated but still exists."""
        if self.termination_date:
            return self.termination_date <= date.today() and self.status != UserStatus.TERMINATED
        return False

    def is_expired(self) -> bool:
        """Check if user validity has expired."""
        if self.valid_to:
            return self.valid_to < date.today()
        return False

    def is_password_expired(self) -> bool:
        """Check if password has expired."""
        if self.password_expires and not self.password_never_expires:
            return self.password_expires < date.today()
        return False

    def days_since_last_login(self) -> Optional[int]:
        """Days since last login."""
        if self.last_login:
            return (datetime.now() - self.last_login).days
        return None

    def is_generic_account(self) -> bool:
        """Check if this is a generic/shared account."""
        generic_patterns = ["SAP*", "DDIC", "EARLYWATCH", "ADMIN", "TEST", "GENERIC", "SHARED"]
        return any(p.lower() in self.username.lower() for p in generic_patterns) or self.user_type == UserType.GENERIC

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "username": self.username,
            "full_name": self.full_name,
            "email": self.email,
            "department": self.department,
            "status": self.status.value,
            "user_type": self.user_type.value,
            "is_locked": self.is_locked,
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "risk_score": self.risk_score,
            "risk_level": self.risk_level.value,
            "roles": self.roles,
            "sod_conflict_count": self.sod_conflict_count,
            "critical_access_count": self.critical_access_count,
        }


# ============================================================
# ROLE MODELS
# ============================================================

@dataclass
class Role:
    """Role definition."""
    role_id: str = ""
    role_name: str = ""
    description: str = ""

    # Classification
    role_type: str = "SINGLE"  # SINGLE, COMPOSITE, DERIVED
    is_critical: bool = False
    is_privileged: bool = False
    business_function: str = ""

    # Risk
    risk_score: int = 0
    risk_level: RiskLevel = RiskLevel.LOW

    # Contents
    transactions: List[str] = field(default_factory=list)
    authorization_objects: List[str] = field(default_factory=list)
    profiles: List[str] = field(default_factory=list)

    # Assignment stats
    user_count: int = 0
    active_user_count: int = 0

    # Metadata
    owner: str = ""
    created_by: str = ""
    created_date: Optional[date] = None
    modified_by: str = ""
    modified_date: Optional[datetime] = None
    last_reviewed: Optional[date] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "role_id": self.role_id,
            "role_name": self.role_name,
            "description": self.description,
            "role_type": self.role_type,
            "is_critical": self.is_critical,
            "risk_score": self.risk_score,
            "risk_level": self.risk_level.value,
            "user_count": self.user_count,
            "transaction_count": len(self.transactions),
            "owner": self.owner,
        }


@dataclass
class RoleAssignment:
    """User-Role assignment."""
    assignment_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    user_id: str = ""
    role_id: str = ""

    # Validity
    valid_from: Optional[date] = None
    valid_to: Optional[date] = None

    # Status
    is_active: bool = True
    is_direct: bool = True  # Direct or inherited
    inherited_from: str = ""  # If inherited, from which role

    # Approval
    requested_by: str = ""
    approved_by: str = ""
    assigned_date: Optional[datetime] = None
    request_id: str = ""

    def is_expired(self) -> bool:
        if self.valid_to:
            return self.valid_to < date.today()
        return False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "assignment_id": self.assignment_id,
            "user_id": self.user_id,
            "role_id": self.role_id,
            "valid_from": self.valid_from.isoformat() if self.valid_from else None,
            "valid_to": self.valid_to.isoformat() if self.valid_to else None,
            "is_active": self.is_active,
            "is_direct": self.is_direct,
            "approved_by": self.approved_by,
        }


# ============================================================
# AUTHORIZATION MODELS
# ============================================================

@dataclass
class Transaction:
    """Transaction/Function code."""
    tcode: str = ""
    description: str = ""

    # Classification
    is_critical: bool = False
    risk_level: RiskLevel = RiskLevel.LOW
    category: str = ""  # FINANCIAL, MASTER_DATA, CONFIG, SECURITY, etc.

    # Authorization requirements
    required_auth_objects: List[str] = field(default_factory=list)

    # Usage
    total_users_with_access: int = 0
    usage_count_last_90_days: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tcode": self.tcode,
            "description": self.description,
            "is_critical": self.is_critical,
            "risk_level": self.risk_level.value,
            "category": self.category,
            "users_with_access": self.total_users_with_access,
        }


@dataclass
class AuthorizationObject:
    """Authorization object definition."""
    object_id: str = ""
    object_name: str = ""
    description: str = ""

    # Classification
    is_critical: bool = False
    risk_level: RiskLevel = RiskLevel.LOW

    # Fields
    fields: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "object_id": self.object_id,
            "object_name": self.object_name,
            "is_critical": self.is_critical,
            "risk_level": self.risk_level.value,
        }


# ============================================================
# SOD MODELS
# ============================================================

@dataclass
class SoDRule:
    """Segregation of Duties rule."""
    rule_id: str = ""
    rule_name: str = ""
    description: str = ""

    # Functions
    function_1: str = ""
    function_1_name: str = ""
    function_2: str = ""
    function_2_name: str = ""

    # Risk
    risk_level: RiskLevel = RiskLevel.HIGH
    business_risk: str = ""

    # Control
    control_id: str = ""
    mitigating_control: str = ""

    # Status
    is_active: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "rule_name": self.rule_name,
            "function_1": self.function_1,
            "function_2": self.function_2,
            "risk_level": self.risk_level.value,
            "business_risk": self.business_risk,
        }


@dataclass
class SoDViolation:
    """SoD violation instance."""
    violation_id: str = field(default_factory=lambda: f"SOD-{str(uuid.uuid4())[:8]}")
    rule_id: str = ""
    rule_name: str = ""

    # User
    user_id: str = ""
    username: str = ""
    user_department: str = ""

    # Conflict details
    function_1: str = ""
    function_1_source: str = ""  # Role that provides this
    function_2: str = ""
    function_2_source: str = ""

    # Risk
    risk_level: RiskLevel = RiskLevel.HIGH
    risk_score: int = 0

    # Mitigation
    is_mitigated: bool = False
    mitigation_control: str = ""
    mitigation_owner: str = ""
    mitigation_expires: Optional[date] = None

    # Status
    status: str = "OPEN"  # OPEN, MITIGATED, ACCEPTED, REMEDIATED
    detected_date: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "violation_id": self.violation_id,
            "rule_id": self.rule_id,
            "rule_name": self.rule_name,
            "user_id": self.user_id,
            "username": self.username,
            "function_1": self.function_1,
            "function_2": self.function_2,
            "risk_level": self.risk_level.value,
            "status": self.status,
            "is_mitigated": self.is_mitigated,
        }


# ============================================================
# FIREFIGHTER/EMERGENCY ACCESS MODELS
# ============================================================

@dataclass
class FirefighterID:
    """Firefighter (emergency access) ID."""
    ff_id: str = ""
    ff_name: str = ""
    description: str = ""

    # Configuration
    system_id: str = ""
    max_duration_hours: int = 4
    requires_reason: bool = True
    requires_approval: bool = True

    # Assignment
    owner_id: str = ""
    owner_name: str = ""
    assigned_users: List[str] = field(default_factory=list)

    # Risk
    risk_level: RiskLevel = RiskLevel.CRITICAL
    transactions_available: List[str] = field(default_factory=list)

    # Status
    is_active: bool = True
    is_checked_out: bool = False
    current_user: str = ""

    # Stats
    total_usages: int = 0
    usage_last_30_days: int = 0
    avg_duration_minutes: float = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ff_id": self.ff_id,
            "ff_name": self.ff_name,
            "system_id": self.system_id,
            "owner_name": self.owner_name,
            "is_checked_out": self.is_checked_out,
            "current_user": self.current_user,
            "total_usages": self.total_usages,
            "usage_last_30_days": self.usage_last_30_days,
        }


@dataclass
class FirefighterUsage:
    """Firefighter usage log entry."""
    usage_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    ff_id: str = ""
    ff_name: str = ""

    # User
    user_id: str = ""
    username: str = ""
    user_department: str = ""

    # Session
    checkout_time: datetime = field(default_factory=datetime.now)
    checkin_time: Optional[datetime] = None
    duration_minutes: int = 0

    # Reason
    reason: str = ""
    ticket_number: str = ""

    # Approval
    approved_by: str = ""
    approval_time: Optional[datetime] = None

    # Activity
    transactions_executed: List[str] = field(default_factory=list)
    actions_performed: int = 0
    critical_actions: int = 0

    # Review
    reviewed: bool = False
    reviewed_by: str = ""
    review_date: Optional[datetime] = None
    review_comments: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "usage_id": self.usage_id,
            "ff_id": self.ff_id,
            "username": self.username,
            "checkout_time": self.checkout_time.isoformat(),
            "checkin_time": self.checkin_time.isoformat() if self.checkin_time else None,
            "duration_minutes": self.duration_minutes,
            "reason": self.reason,
            "actions_performed": self.actions_performed,
            "critical_actions": self.critical_actions,
            "reviewed": self.reviewed,
        }


# ============================================================
# CHANGE LOG MODELS
# ============================================================

@dataclass
class ChangeLogEntry:
    """Change log entry."""
    log_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])

    # What changed
    object_type: str = ""  # USER, ROLE, ASSIGNMENT, AUTH
    object_id: str = ""
    object_name: str = ""

    # Change details
    change_type: ChangeType = ChangeType.MODIFY
    field_changed: str = ""
    old_value: str = ""
    new_value: str = ""

    # Who/When
    changed_by: str = ""
    changed_at: datetime = field(default_factory=datetime.now)

    # Context
    request_id: str = ""
    reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "log_id": self.log_id,
            "object_type": self.object_type,
            "object_id": self.object_id,
            "change_type": self.change_type.value,
            "field_changed": self.field_changed,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "changed_by": self.changed_by,
            "changed_at": self.changed_at.isoformat(),
        }


# ============================================================
# SECURITY LOG MODELS
# ============================================================

@dataclass
class LoginEvent:
    """Login/authentication event."""
    event_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])

    # User
    user_id: str = ""
    username: str = ""

    # Event
    event_type: str = "LOGIN"  # LOGIN, LOGOUT, FAILED_LOGIN
    success: bool = True
    failure_reason: str = ""

    # Context
    timestamp: datetime = field(default_factory=datetime.now)
    ip_address: str = ""
    client_type: str = ""
    system_id: str = ""

    # Session
    session_id: str = ""

    # Anomaly detection
    is_anomalous: bool = False
    anomaly_reasons: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "username": self.username,
            "event_type": self.event_type,
            "success": self.success,
            "timestamp": self.timestamp.isoformat(),
            "ip_address": self.ip_address,
            "is_anomalous": self.is_anomalous,
        }


@dataclass
class SecurityEvent:
    """Security-related event."""
    event_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])

    # Event
    event_type: str = ""
    severity: str = "INFO"  # INFO, WARNING, CRITICAL

    # Actor
    user_id: str = ""
    username: str = ""

    # Details
    description: str = ""
    details: Dict[str, Any] = field(default_factory=dict)

    # Context
    timestamp: datetime = field(default_factory=datetime.now)
    system_id: str = ""
    transaction: str = ""

    # Risk
    risk_score: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "severity": self.severity,
            "username": self.username,
            "description": self.description,
            "timestamp": self.timestamp.isoformat(),
            "risk_score": self.risk_score,
        }


# ============================================================
# REPORT MODELS
# ============================================================

@dataclass
class ReportResult:
    """Result of a report execution."""
    report_id: str = field(default_factory=lambda: f"RPT-{datetime.now().strftime('%Y%m%d%H%M%S')}")
    report_type: str = ""
    report_name: str = ""

    # Execution
    executed_at: datetime = field(default_factory=datetime.now)
    executed_by: str = ""
    execution_time_seconds: float = 0

    # Parameters
    parameters: Dict[str, Any] = field(default_factory=dict)

    # Results
    total_records: int = 0
    records: List[Dict[str, Any]] = field(default_factory=list)

    # Summary
    summary: Dict[str, Any] = field(default_factory=dict)

    # Risk metrics
    critical_findings: int = 0
    high_findings: int = 0
    medium_findings: int = 0
    low_findings: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id": self.report_id,
            "report_type": self.report_type,
            "report_name": self.report_name,
            "executed_at": self.executed_at.isoformat(),
            "executed_by": self.executed_by,
            "total_records": self.total_records,
            "summary": self.summary,
            "findings": {
                "critical": self.critical_findings,
                "high": self.high_findings,
                "medium": self.medium_findings,
                "low": self.low_findings,
            },
        }
