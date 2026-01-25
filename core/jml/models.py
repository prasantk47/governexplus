"""
JML Models

Data models for Joiner/Mover/Leaver lifecycle events and provisioning.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from enum import Enum
import uuid


class JMLEventType(Enum):
    """Types of JML events"""
    JOINER = "joiner"           # New employee
    MOVER = "mover"             # Role/department change
    LEAVER = "leaver"           # Termination
    CONTRACTOR_START = "contractor_start"
    CONTRACTOR_END = "contractor_end"
    LEAVE_START = "leave_start"   # Extended leave
    LEAVE_END = "leave_end"       # Return from leave
    REHIRE = "rehire"


class ProvisioningStatus(Enum):
    """Status of a provisioning action"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    AWAITING_APPROVAL = "awaiting_approval"
    SCHEDULED = "scheduled"


class ProvisioningActionType(Enum):
    """Types of provisioning actions"""
    GRANT_ROLE = "grant_role"
    REVOKE_ROLE = "revoke_role"
    CREATE_ACCOUNT = "create_account"
    DISABLE_ACCOUNT = "disable_account"
    ENABLE_ACCOUNT = "enable_account"
    DELETE_ACCOUNT = "delete_account"
    MODIFY_PROFILE = "modify_profile"
    RESET_PASSWORD = "reset_password"
    SET_EXPIRY = "set_expiry"
    TRANSFER_OWNERSHIP = "transfer_ownership"


@dataclass
class AccessProfile:
    """
    Defines standard access for a job role/position.

    Maps job titles, departments, or positions to default access.
    """
    profile_id: str = field(default_factory=lambda: f"PROF-{uuid.uuid4().hex[:6].upper()}")
    name: str = ""
    description: str = ""

    # Matching criteria
    job_titles: List[str] = field(default_factory=list)
    departments: List[str] = field(default_factory=list)
    locations: List[str] = field(default_factory=list)
    cost_centers: List[str] = field(default_factory=list)
    employee_types: List[str] = field(default_factory=list)  # FTE, contractor, etc.

    # Access to provision
    roles: List[Dict] = field(default_factory=list)  # {system, role_name, duration}
    groups: List[Dict] = field(default_factory=list)  # AD/LDAP groups
    entitlements: List[Dict] = field(default_factory=list)  # Specific entitlements

    # Options
    is_active: bool = True
    priority: int = 100  # Higher = applied first if multiple match
    requires_approval: bool = False
    auto_expire_days: Optional[int] = None  # For contractors

    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    last_modified: datetime = field(default_factory=datetime.now)
    owner_id: str = ""

    def matches(self, employee_data: Dict) -> bool:
        """Check if profile matches employee attributes"""
        if not self.is_active:
            return False

        if self.job_titles and employee_data.get("job_title") not in self.job_titles:
            return False
        if self.departments and employee_data.get("department") not in self.departments:
            return False
        if self.locations and employee_data.get("location") not in self.locations:
            return False
        if self.cost_centers and employee_data.get("cost_center") not in self.cost_centers:
            return False
        if self.employee_types and employee_data.get("employee_type") not in self.employee_types:
            return False

        return True

    def to_dict(self) -> Dict:
        return {
            "profile_id": self.profile_id,
            "name": self.name,
            "description": self.description,
            "job_titles": self.job_titles,
            "departments": self.departments,
            "locations": self.locations,
            "employee_types": self.employee_types,
            "roles": self.roles,
            "groups": self.groups,
            "is_active": self.is_active,
            "priority": self.priority,
            "requires_approval": self.requires_approval,
            "auto_expire_days": self.auto_expire_days
        }


@dataclass
class ProvisioningAction:
    """A single provisioning action to be executed"""
    action_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    event_id: str = ""

    # Action details
    action_type: ProvisioningActionType = ProvisioningActionType.GRANT_ROLE
    target_system: str = ""
    target_user_id: str = ""

    # What to provision
    role_name: Optional[str] = None
    group_name: Optional[str] = None
    entitlement: Optional[Dict] = None

    # Status
    status: ProvisioningStatus = ProvisioningStatus.PENDING
    scheduled_time: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Results
    success: bool = False
    error_message: Optional[str] = None
    result_details: Dict = field(default_factory=dict)

    # Retry handling
    retry_count: int = 0
    max_retries: int = 3

    def to_dict(self) -> Dict:
        return {
            "action_id": self.action_id,
            "event_id": self.event_id,
            "action_type": self.action_type.value,
            "target_system": self.target_system,
            "target_user_id": self.target_user_id,
            "role_name": self.role_name,
            "group_name": self.group_name,
            "status": self.status.value,
            "scheduled_time": self.scheduled_time.isoformat() if self.scheduled_time else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "success": self.success,
            "error_message": self.error_message,
            "retry_count": self.retry_count
        }


@dataclass
class JMLEvent:
    """
    A JML lifecycle event from HR.

    Represents a joiner, mover, or leaver event that triggers
    provisioning/deprovisioning actions.
    """
    event_id: str = field(default_factory=lambda: f"JML-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}")

    # Event type
    event_type: JMLEventType = JMLEventType.JOINER

    # Employee info
    employee_id: str = ""
    employee_name: str = ""
    employee_email: str = ""

    # Current attributes
    job_title: str = ""
    department: str = ""
    manager_id: str = ""
    manager_name: str = ""
    location: str = ""
    cost_center: str = ""
    employee_type: str = "FTE"  # FTE, contractor, temp, etc.
    company_code: str = ""

    # For movers - previous values
    previous_job_title: Optional[str] = None
    previous_department: Optional[str] = None
    previous_manager_id: Optional[str] = None
    previous_location: Optional[str] = None
    previous_cost_center: Optional[str] = None

    # Dates
    effective_date: datetime = field(default_factory=datetime.now)
    termination_date: Optional[datetime] = None
    contract_end_date: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.now)

    # Processing status
    status: ProvisioningStatus = ProvisioningStatus.PENDING
    processed_at: Optional[datetime] = None
    processed_by: Optional[str] = None

    # Source
    source_system: str = "HR"
    source_event_id: Optional[str] = None  # ID from HR system

    # Provisioning
    actions: List[ProvisioningAction] = field(default_factory=list)
    matched_profiles: List[str] = field(default_factory=list)

    # Options
    requires_approval: bool = False
    approval_status: Optional[str] = None
    approved_by: Optional[str] = None
    notes: str = ""

    def get_employee_attributes(self) -> Dict:
        """Get employee attributes for profile matching"""
        return {
            "employee_id": self.employee_id,
            "job_title": self.job_title,
            "department": self.department,
            "location": self.location,
            "cost_center": self.cost_center,
            "employee_type": self.employee_type,
            "company_code": self.company_code
        }

    def get_previous_attributes(self) -> Dict:
        """Get previous attributes (for movers)"""
        return {
            "job_title": self.previous_job_title,
            "department": self.previous_department,
            "manager_id": self.previous_manager_id,
            "location": self.previous_location,
            "cost_center": self.previous_cost_center
        }

    def calculate_progress(self) -> Dict:
        """Calculate processing progress"""
        if not self.actions:
            return {"progress": 0, "completed": 0, "total": 0, "failed": 0}

        completed = sum(1 for a in self.actions if a.status == ProvisioningStatus.COMPLETED)
        failed = sum(1 for a in self.actions if a.status == ProvisioningStatus.FAILED)
        total = len(self.actions)

        return {
            "progress": round((completed / total) * 100, 1) if total else 0,
            "completed": completed,
            "failed": failed,
            "total": total,
            "pending": total - completed - failed
        }

    def to_dict(self) -> Dict:
        progress = self.calculate_progress()

        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "employee_id": self.employee_id,
            "employee_name": self.employee_name,
            "employee_email": self.employee_email,
            "job_title": self.job_title,
            "department": self.department,
            "manager_id": self.manager_id,
            "manager_name": self.manager_name,
            "location": self.location,
            "employee_type": self.employee_type,
            "effective_date": self.effective_date.isoformat(),
            "termination_date": self.termination_date.isoformat() if self.termination_date else None,
            "status": self.status.value,
            "requires_approval": self.requires_approval,
            "approval_status": self.approval_status,
            "matched_profiles": self.matched_profiles,
            "action_count": len(self.actions),
            "progress": progress,
            "created_at": self.created_at.isoformat(),
            "processed_at": self.processed_at.isoformat() if self.processed_at else None,
            "source_system": self.source_system
        }

    def to_summary(self) -> Dict:
        """Brief summary for list views"""
        progress = self.calculate_progress()

        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "employee_name": self.employee_name,
            "job_title": self.job_title,
            "department": self.department,
            "effective_date": self.effective_date.isoformat(),
            "status": self.status.value,
            "progress_percent": progress["progress"]
        }


@dataclass
class JMLProcessingRule:
    """Rules for processing JML events"""
    rule_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    description: str = ""

    # When to apply
    event_types: List[JMLEventType] = field(default_factory=list)
    conditions: Dict[str, Any] = field(default_factory=dict)

    # What to do
    actions: List[Dict] = field(default_factory=list)
    delay_days: int = 0  # Delay execution
    requires_approval: bool = False
    approver_type: str = "manager"  # manager, security, hr

    # Status
    is_active: bool = True
    priority: int = 100

    def to_dict(self) -> Dict:
        return {
            "rule_id": self.rule_id,
            "name": self.name,
            "description": self.description,
            "event_types": [e.value for e in self.event_types],
            "conditions": self.conditions,
            "actions": self.actions,
            "delay_days": self.delay_days,
            "requires_approval": self.requires_approval,
            "is_active": self.is_active,
            "priority": self.priority
        }
