"""
Access Request Models

Data models for the access request and approval workflow system.
Supports multi-level approvals, risk-based routing, and SLA tracking.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime, date, timedelta
from enum import Enum
import uuid


# =============================================================================
# User Details Models for Access Requests
# =============================================================================

@dataclass
class UserOrganization:
    """Organization details for a user in access request context"""
    company_code: str = ""
    company_name: str = ""
    cost_center: str = ""
    cost_center_name: str = ""
    department: str = ""
    department_name: str = ""
    org_unit: str = ""
    location: str = ""
    country: str = ""
    region: str = ""
    business_unit: str = ""

    def to_dict(self) -> Dict:
        return {
            "company_code": self.company_code,
            "company_name": self.company_name,
            "cost_center": self.cost_center,
            "cost_center_name": self.cost_center_name,
            "department": self.department,
            "department_name": self.department_name,
            "org_unit": self.org_unit,
            "location": self.location,
            "country": self.country,
            "region": self.region,
            "business_unit": self.business_unit
        }


@dataclass
class UserManager:
    """Manager information for access request routing"""
    user_id: str = ""
    employee_id: str = ""
    name: str = ""
    email: str = ""
    title: str = ""
    department: str = ""

    def to_dict(self) -> Dict:
        return {
            "user_id": self.user_id,
            "employee_id": self.employee_id,
            "name": self.name,
            "email": self.email,
            "title": self.title,
            "department": self.department
        }


@dataclass
class UserRiskContext:
    """Risk context for a user in access requests"""
    risk_level: str = "low"
    risk_score: float = 0.0
    sod_violation_count: int = 0
    sensitive_access_count: int = 0
    active_mitigations: int = 0
    certification_status: str = "not_certified"
    last_certification_date: Optional[datetime] = None
    high_risk_roles: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "risk_level": self.risk_level,
            "risk_score": self.risk_score,
            "sod_violation_count": self.sod_violation_count,
            "sensitive_access_count": self.sensitive_access_count,
            "active_mitigations": self.active_mitigations,
            "certification_status": self.certification_status,
            "last_certification_date": self.last_certification_date.isoformat() if self.last_certification_date else None,
            "high_risk_roles": self.high_risk_roles
        }


@dataclass
class UserAccessContext:
    """Current access context for a user"""
    total_roles: int = 0
    total_profiles: int = 0
    systems: List[str] = field(default_factory=list)
    current_roles: List[Dict] = field(default_factory=list)
    privileged_access: bool = False
    firefighter_eligible: bool = False

    def to_dict(self) -> Dict:
        return {
            "total_roles": self.total_roles,
            "total_profiles": self.total_profiles,
            "systems": self.systems,
            "current_roles": self.current_roles,
            "privileged_access": self.privileged_access,
            "firefighter_eligible": self.firefighter_eligible
        }


@dataclass
class UserDetails:
    """
    Comprehensive user details for access request context.
    Aggregated from HR, Identity Provider, SAP, and GRC systems.
    """
    # Primary identifiers
    user_id: str = ""
    employee_id: str = ""
    ad_account: str = ""
    upn: str = ""  # User Principal Name

    # Personal information
    first_name: str = ""
    last_name: str = ""
    full_name: str = ""
    display_name: str = ""
    email: str = ""
    phone: str = ""

    # Job information
    job_title: str = ""
    job_code: str = ""
    job_family: str = ""
    employment_type: str = "full_time"  # full_time, contractor, vendor, etc.

    # Organization
    organization: UserOrganization = field(default_factory=UserOrganization)

    # Manager (for approval routing)
    manager: Optional[UserManager] = None
    secondary_manager: Optional[UserManager] = None  # Matrix reporting

    # Dates
    hire_date: Optional[date] = None
    termination_date: Optional[date] = None
    position_start_date: Optional[date] = None

    # Account status
    status: str = "active"  # active, inactive, locked, terminated
    is_locked: bool = False

    # SAP-specific
    sap_user_type: str = ""  # Dialog, System, Service
    sap_license_type: str = ""
    sap_valid_from: Optional[date] = None
    sap_valid_to: Optional[date] = None
    sap_last_login: Optional[datetime] = None

    # Risk context
    risk_context: UserRiskContext = field(default_factory=UserRiskContext)

    # Current access
    access_context: UserAccessContext = field(default_factory=UserAccessContext)

    # Data source tracking
    data_sources: List[str] = field(default_factory=list)
    last_sync: Optional[datetime] = None

    def to_dict(self) -> Dict:
        return {
            "user_id": self.user_id,
            "employee_id": self.employee_id,
            "ad_account": self.ad_account,
            "upn": self.upn,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "full_name": self.full_name,
            "display_name": self.display_name,
            "email": self.email,
            "phone": self.phone,
            "job_title": self.job_title,
            "job_code": self.job_code,
            "job_family": self.job_family,
            "employment_type": self.employment_type,
            "organization": self.organization.to_dict(),
            "manager": self.manager.to_dict() if self.manager else None,
            "secondary_manager": self.secondary_manager.to_dict() if self.secondary_manager else None,
            "hire_date": self.hire_date.isoformat() if self.hire_date else None,
            "termination_date": self.termination_date.isoformat() if self.termination_date else None,
            "position_start_date": self.position_start_date.isoformat() if self.position_start_date else None,
            "status": self.status,
            "is_locked": self.is_locked,
            "sap_user_type": self.sap_user_type,
            "sap_license_type": self.sap_license_type,
            "sap_valid_from": self.sap_valid_from.isoformat() if self.sap_valid_from else None,
            "sap_valid_to": self.sap_valid_to.isoformat() if self.sap_valid_to else None,
            "sap_last_login": self.sap_last_login.isoformat() if self.sap_last_login else None,
            "risk_context": self.risk_context.to_dict(),
            "access_context": self.access_context.to_dict(),
            "data_sources": self.data_sources,
            "last_sync": self.last_sync.isoformat() if self.last_sync else None
        }

    def to_summary(self) -> Dict:
        """Brief summary for lists"""
        return {
            "user_id": self.user_id,
            "employee_id": self.employee_id,
            "full_name": self.full_name,
            "email": self.email,
            "job_title": self.job_title,
            "department": self.organization.department,
            "status": self.status,
            "risk_level": self.risk_context.risk_level
        }


# =============================================================================
# Enums
# =============================================================================

class RequestType(Enum):
    """Types of access requests"""
    NEW_ACCESS = "new_access"           # Request new role/permission
    MODIFY_ACCESS = "modify_access"     # Change existing access
    REMOVE_ACCESS = "remove_access"     # Revoke access
    EMERGENCY_ACCESS = "emergency"       # Firefighter/emergency
    TEMPORARY_ACCESS = "temporary"       # Time-bound access
    ROLE_EXTENSION = "extension"         # Extend expiring access
    ACCESS_TRANSFER = "transfer"         # Transfer access to new role


class AccessRequestStatus(Enum):
    """Status of access request"""
    DRAFT = "draft"
    SUBMITTED = "submitted"
    PENDING_RISK_REVIEW = "pending_risk_review"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    PROVISIONING = "provisioning"
    PROVISIONED = "provisioned"
    FAILED = "failed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class ApprovalStatus(Enum):
    """Status of an approval step"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    DELEGATED = "delegated"
    ESCALATED = "escalated"
    SKIPPED = "skipped"
    TIMED_OUT = "timed_out"


class ApprovalAction(Enum):
    """Actions that can be taken on an approval"""
    APPROVE = "approve"
    REJECT = "reject"
    DELEGATE = "delegate"
    REQUEST_INFO = "request_info"
    ESCALATE = "escalate"


@dataclass
class RequestedAccess:
    """Represents a single piece of requested access"""
    access_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    access_type: str = "role"  # role, profile, entitlement, group
    access_name: str = ""
    access_description: str = ""
    system: str = "SAP"

    # Timing
    valid_from: Optional[datetime] = None
    valid_to: Optional[datetime] = None
    is_temporary: bool = False

    # Risk info (populated after analysis)
    risk_score: float = 0.0
    violations: List[Dict] = field(default_factory=list)
    requires_mitigation: bool = False

    def to_dict(self) -> Dict:
        return {
            "access_id": self.access_id,
            "access_type": self.access_type,
            "access_name": self.access_name,
            "access_description": self.access_description,
            "system": self.system,
            "valid_from": self.valid_from.isoformat() if self.valid_from else None,
            "valid_to": self.valid_to.isoformat() if self.valid_to else None,
            "is_temporary": self.is_temporary,
            "risk_score": self.risk_score,
            "violations": self.violations
        }


@dataclass
class ApprovalStep:
    """Represents a single approval step in the workflow"""
    step_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    step_number: int = 1
    step_name: str = ""
    step_type: str = "approval"  # approval, review, notification

    # Approvers
    approver_type: str = "user"  # user, role, manager, security_team
    approver_ids: List[str] = field(default_factory=list)
    approver_names: List[str] = field(default_factory=list)
    require_all: bool = False  # True = all must approve, False = any one

    # Status
    status: ApprovalStatus = ApprovalStatus.PENDING

    # Actions taken
    actioned_by: Optional[str] = None
    actioned_by_name: Optional[str] = None
    actioned_at: Optional[datetime] = None
    action: Optional[ApprovalAction] = None
    comments: str = ""

    # Delegation
    delegated_to: Optional[str] = None
    delegated_by: Optional[str] = None

    # SLA
    sla_hours: int = 48
    due_date: Optional[datetime] = None
    escalation_triggered: bool = False

    # Attachments/Evidence
    attachments: List[Dict] = field(default_factory=list)

    def is_overdue(self) -> bool:
        if self.due_date and self.status == ApprovalStatus.PENDING:
            return datetime.now() > self.due_date
        return False

    def to_dict(self) -> Dict:
        return {
            "step_id": self.step_id,
            "step_number": self.step_number,
            "step_name": self.step_name,
            "step_type": self.step_type,
            "approver_type": self.approver_type,
            "approver_ids": self.approver_ids,
            "approver_names": self.approver_names,
            "status": self.status.value,
            "actioned_by": self.actioned_by,
            "actioned_at": self.actioned_at.isoformat() if self.actioned_at else None,
            "action": self.action.value if self.action else None,
            "comments": self.comments,
            "sla_hours": self.sla_hours,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "is_overdue": self.is_overdue()
        }


@dataclass
class AccessRequest:
    """
    Main access request entity.

    Tracks the full lifecycle of an access request from submission
    through approval to provisioning.
    """
    request_id: str = field(default_factory=lambda: f"AR-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}")

    # Request type
    request_type: RequestType = RequestType.NEW_ACCESS

    # Requester information (basic - for backwards compatibility)
    requester_user_id: str = ""
    requester_name: str = ""
    requester_email: str = ""
    requester_department: str = ""
    requester_manager_id: Optional[str] = None

    # Requester full details (comprehensive user profile)
    requester_details: Optional[UserDetails] = None

    # Target user (who access is for - may differ from requester)
    target_user_id: str = ""
    target_user_name: str = ""
    target_user_email: str = ""
    target_user_department: str = ""

    # Target user full details (comprehensive user profile)
    target_user_details: Optional[UserDetails] = None

    # Requested access items
    requested_items: List[RequestedAccess] = field(default_factory=list)

    # Business justification
    business_justification: str = ""
    ticket_reference: Optional[str] = None  # ServiceNow/Jira ticket
    project_code: Optional[str] = None

    # Timing
    requested_start_date: Optional[datetime] = None
    requested_end_date: Optional[datetime] = None
    is_temporary: bool = False

    # Status
    status: AccessRequestStatus = AccessRequestStatus.DRAFT

    # Risk analysis results
    overall_risk_score: float = 0.0
    risk_level: str = "low"  # low, medium, high, critical
    sod_violations: List[Dict] = field(default_factory=list)
    sensitive_access_flags: List[Dict] = field(default_factory=list)
    risk_accepted: bool = False
    risk_accepted_by: Optional[str] = None

    # Mitigation
    mitigations_required: List[Dict] = field(default_factory=list)
    mitigations_applied: List[Dict] = field(default_factory=list)

    # Approval workflow
    workflow_id: Optional[str] = None
    approval_steps: List[ApprovalStep] = field(default_factory=list)
    current_step: int = 0

    # Final decision
    final_decision: Optional[str] = None  # approved, rejected
    final_decision_by: Optional[str] = None
    final_decision_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None

    # Provisioning
    provisioning_status: Optional[str] = None
    provisioned_at: Optional[datetime] = None
    provisioning_errors: List[str] = field(default_factory=list)

    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    submitted_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    last_updated_at: datetime = field(default_factory=datetime.now)

    # Expiry tracking
    access_expires_at: Optional[datetime] = None
    expiry_notification_sent: bool = False

    def get_current_approvers(self) -> List[str]:
        """Get list of current pending approvers"""
        if self.current_step < len(self.approval_steps):
            step = self.approval_steps[self.current_step]
            if step.status == ApprovalStatus.PENDING:
                return step.approver_ids
        return []

    def get_pending_steps(self) -> List[ApprovalStep]:
        """Get all pending approval steps"""
        return [s for s in self.approval_steps if s.status == ApprovalStatus.PENDING]

    def is_fully_approved(self) -> bool:
        """Check if all approval steps are complete"""
        if not self.approval_steps:
            return False
        return all(
            s.status in [ApprovalStatus.APPROVED, ApprovalStatus.SKIPPED]
            for s in self.approval_steps
        )

    def calculate_sla_status(self) -> Dict:
        """Calculate overall SLA status"""
        overdue_steps = [s for s in self.approval_steps if s.is_overdue()]
        return {
            "total_steps": len(self.approval_steps),
            "completed_steps": len([s for s in self.approval_steps
                                   if s.status not in [ApprovalStatus.PENDING]]),
            "overdue_steps": len(overdue_steps),
            "is_on_track": len(overdue_steps) == 0
        }

    def to_dict(self) -> Dict:
        return {
            "request_id": self.request_id,
            "request_type": self.request_type.value,
            # Requester info
            "requester_user_id": self.requester_user_id,
            "requester_name": self.requester_name,
            "requester_email": self.requester_email,
            "requester_department": self.requester_department,
            "requester_details": self.requester_details.to_dict() if self.requester_details else None,
            # Target user info
            "target_user_id": self.target_user_id,
            "target_user_name": self.target_user_name,
            "target_user_email": self.target_user_email,
            "target_user_department": self.target_user_department,
            "target_user_details": self.target_user_details.to_dict() if self.target_user_details else None,
            # Request details
            "requested_items": [item.to_dict() for item in self.requested_items],
            "business_justification": self.business_justification,
            "ticket_reference": self.ticket_reference,
            "project_code": self.project_code,
            "is_temporary": self.is_temporary,
            "requested_start_date": self.requested_start_date.isoformat() if self.requested_start_date else None,
            "requested_end_date": self.requested_end_date.isoformat() if self.requested_end_date else None,
            # Status
            "status": self.status.value,
            # Risk
            "overall_risk_score": self.overall_risk_score,
            "risk_level": self.risk_level,
            "sod_violations": self.sod_violations,
            "sensitive_access_flags": self.sensitive_access_flags,
            "risk_accepted": self.risk_accepted,
            "mitigations_required": self.mitigations_required,
            "mitigations_applied": self.mitigations_applied,
            # Workflow
            "approval_steps": [s.to_dict() for s in self.approval_steps],
            "current_step": self.current_step,
            # Decisions
            "final_decision": self.final_decision,
            "final_decision_by": self.final_decision_by,
            "final_decision_at": self.final_decision_at.isoformat() if self.final_decision_at else None,
            "rejection_reason": self.rejection_reason,
            # Provisioning
            "provisioning_status": self.provisioning_status,
            "provisioned_at": self.provisioned_at.isoformat() if self.provisioned_at else None,
            # Timestamps
            "created_at": self.created_at.isoformat(),
            "submitted_at": self.submitted_at.isoformat() if self.submitted_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "access_expires_at": self.access_expires_at.isoformat() if self.access_expires_at else None,
            "sla_status": self.calculate_sla_status()
        }

    def to_summary(self) -> Dict:
        """Return a brief summary for list views"""
        return {
            "request_id": self.request_id,
            "request_type": self.request_type.value,
            "requester_name": self.requester_name,
            "target_user_name": self.target_user_name,
            "status": self.status.value,
            "risk_level": self.risk_level,
            "item_count": len(self.requested_items),
            "pending_approvers": self.get_current_approvers(),
            "created_at": self.created_at.isoformat(),
            "is_overdue": any(s.is_overdue() for s in self.approval_steps)
        }
