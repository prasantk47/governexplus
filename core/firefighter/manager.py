"""
Firefighter / Emergency Access Management (EAM)

Provides controlled, audited emergency access to privileged accounts.
Equivalent to SAP GRC Firefighter functionality with modern enhancements.

Key Features:
- Request and approval workflow for emergency access
- Time-limited session management
- Full activity logging and monitoring
- Automatic session termination
- Supervisor review requirements
"""

import uuid
import secrets
import hashlib
import logging
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from enum import Enum
import json
import asyncio

logger = logging.getLogger(__name__)


class SessionStatus(Enum):
    """Firefighter session status"""
    REQUESTED = "requested"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    ACTIVE = "active"
    COMPLETED = "completed"
    EXPIRED = "expired"
    REVOKED = "revoked"
    REJECTED = "rejected"


class RequestPriority(Enum):
    """Emergency request priority levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ReasonCode(Enum):
    """
    Structured reason codes for firefighter access.

    Each code maps to specific approval routing and SLA requirements.
    """
    PROD_INCIDENT = "prod_incident"           # Production incident resolution
    CHANGE_MANAGEMENT = "change_management"   # Scheduled change implementation
    AUDIT_REQUEST = "audit_request"           # Audit/compliance requirement
    SECURITY_INCIDENT = "security_incident"   # Security event response
    DATA_CORRECTION = "data_correction"       # Critical data fix
    MONTH_END = "month_end"                   # Month/quarter/year-end close
    SYSTEM_MAINTENANCE = "system_maintenance" # System maintenance activity
    DISASTER_RECOVERY = "disaster_recovery"   # DR/BCP execution
    REGULATORY = "regulatory"                 # Regulatory compliance deadline
    OTHER = "other"                           # Requires additional justification


@dataclass
class ReasonCodeConfig:
    """Configuration for a reason code"""
    code: ReasonCode
    label: str
    description: str
    requires_ticket: bool
    requires_justification: bool
    default_priority: RequestPriority
    max_duration_hours: int
    approval_chain: List[str]  # Approval roles required
    sla_minutes: int           # Approval SLA
    auto_approve_eligible: bool
    controller_review_sla_hours: int  # Post-session review SLA

    def to_dict(self) -> Dict:
        return {
            'code': self.code.value,
            'label': self.label,
            'description': self.description,
            'requires_ticket': self.requires_ticket,
            'requires_justification': self.requires_justification,
            'default_priority': self.default_priority.value,
            'max_duration_hours': self.max_duration_hours,
            'approval_chain': self.approval_chain,
            'sla_minutes': self.sla_minutes,
            'auto_approve_eligible': self.auto_approve_eligible,
            'controller_review_sla_hours': self.controller_review_sla_hours
        }


# Reason Code Catalog - Enterprise Configuration
REASON_CODE_CATALOG: Dict[ReasonCode, ReasonCodeConfig] = {
    ReasonCode.PROD_INCIDENT: ReasonCodeConfig(
        code=ReasonCode.PROD_INCIDENT,
        label="Production Incident",
        description="Resolution of active production incident affecting business operations",
        requires_ticket=True,
        requires_justification=True,
        default_priority=RequestPriority.CRITICAL,
        max_duration_hours=4,
        approval_chain=["ff_owner", "it_manager"],
        sla_minutes=15,
        auto_approve_eligible=False,
        controller_review_sla_hours=24
    ),
    ReasonCode.CHANGE_MANAGEMENT: ReasonCodeConfig(
        code=ReasonCode.CHANGE_MANAGEMENT,
        label="Change Management",
        description="Implementation of pre-approved change request",
        requires_ticket=True,
        requires_justification=False,
        default_priority=RequestPriority.MEDIUM,
        max_duration_hours=8,
        approval_chain=["ff_owner"],
        sla_minutes=60,
        auto_approve_eligible=True,
        controller_review_sla_hours=48
    ),
    ReasonCode.AUDIT_REQUEST: ReasonCodeConfig(
        code=ReasonCode.AUDIT_REQUEST,
        label="Audit Request",
        description="Access required for audit or compliance verification",
        requires_ticket=True,
        requires_justification=True,
        default_priority=RequestPriority.MEDIUM,
        max_duration_hours=4,
        approval_chain=["ff_owner", "compliance_manager"],
        sla_minutes=30,
        auto_approve_eligible=False,
        controller_review_sla_hours=24
    ),
    ReasonCode.SECURITY_INCIDENT: ReasonCodeConfig(
        code=ReasonCode.SECURITY_INCIDENT,
        label="Security Incident",
        description="Response to security event or breach investigation",
        requires_ticket=True,
        requires_justification=True,
        default_priority=RequestPriority.CRITICAL,
        max_duration_hours=4,
        approval_chain=["security_manager", "ciso"],
        sla_minutes=10,
        auto_approve_eligible=False,
        controller_review_sla_hours=8
    ),
    ReasonCode.DATA_CORRECTION: ReasonCodeConfig(
        code=ReasonCode.DATA_CORRECTION,
        label="Data Correction",
        description="Critical data fix or correction",
        requires_ticket=True,
        requires_justification=True,
        default_priority=RequestPriority.HIGH,
        max_duration_hours=2,
        approval_chain=["ff_owner", "data_owner"],
        sla_minutes=30,
        auto_approve_eligible=False,
        controller_review_sla_hours=24
    ),
    ReasonCode.MONTH_END: ReasonCodeConfig(
        code=ReasonCode.MONTH_END,
        label="Month/Quarter/Year End Close",
        description="Period-end closing activities",
        requires_ticket=False,
        requires_justification=True,
        default_priority=RequestPriority.HIGH,
        max_duration_hours=6,
        approval_chain=["ff_owner", "finance_manager"],
        sla_minutes=30,
        auto_approve_eligible=True,
        controller_review_sla_hours=48
    ),
    ReasonCode.SYSTEM_MAINTENANCE: ReasonCodeConfig(
        code=ReasonCode.SYSTEM_MAINTENANCE,
        label="System Maintenance",
        description="Scheduled or emergency system maintenance",
        requires_ticket=True,
        requires_justification=False,
        default_priority=RequestPriority.MEDIUM,
        max_duration_hours=8,
        approval_chain=["ff_owner", "it_manager"],
        sla_minutes=60,
        auto_approve_eligible=True,
        controller_review_sla_hours=72
    ),
    ReasonCode.DISASTER_RECOVERY: ReasonCodeConfig(
        code=ReasonCode.DISASTER_RECOVERY,
        label="Disaster Recovery",
        description="DR/BCP procedure execution",
        requires_ticket=True,
        requires_justification=True,
        default_priority=RequestPriority.CRITICAL,
        max_duration_hours=8,
        approval_chain=["ff_owner"],
        sla_minutes=5,
        auto_approve_eligible=False,
        controller_review_sla_hours=24
    ),
    ReasonCode.REGULATORY: ReasonCodeConfig(
        code=ReasonCode.REGULATORY,
        label="Regulatory Deadline",
        description="Regulatory compliance deadline requirement",
        requires_ticket=True,
        requires_justification=True,
        default_priority=RequestPriority.HIGH,
        max_duration_hours=4,
        approval_chain=["ff_owner", "compliance_manager"],
        sla_minutes=30,
        auto_approve_eligible=False,
        controller_review_sla_hours=24
    ),
    ReasonCode.OTHER: ReasonCodeConfig(
        code=ReasonCode.OTHER,
        label="Other",
        description="Other reason - requires detailed justification",
        requires_ticket=True,
        requires_justification=True,
        default_priority=RequestPriority.LOW,
        max_duration_hours=2,
        approval_chain=["ff_owner", "security_manager"],
        sla_minutes=120,
        auto_approve_eligible=False,
        controller_review_sla_hours=24
    )
}


class ReviewStatus(Enum):
    """Controller review status"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    APPROVED = "approved"
    FLAGGED = "flagged"
    ESCALATED = "escalated"


@dataclass
class ActivityLog:
    """Single activity entry during firefighter session"""
    log_id: str
    session_id: str
    timestamp: datetime
    action_type: str  # 'TCODE_EXECUTE', 'DATA_CHANGE', 'REPORT_RUN', etc.
    action_details: Dict[str, Any]

    # Context
    client_ip: Optional[str] = None
    user_agent: Optional[str] = None
    sap_gui_version: Optional[str] = None

    # Risk indicators
    is_sensitive: bool = False
    requires_review: bool = False

    def to_dict(self) -> Dict:
        return {
            **asdict(self),
            'timestamp': self.timestamp.isoformat()
        }


@dataclass
class FirefighterRequest:
    """Request for emergency/firefighter access"""
    request_id: str
    requester_user_id: str
    requester_name: str
    requester_email: str

    # Target system and account
    target_system: str
    firefighter_id: str

    # Request details - Structured Reason Code
    reason_code: ReasonCode = ReasonCode.OTHER
    reason_code_config: Optional[ReasonCodeConfig] = None
    reason: str = ""  # Additional description
    business_justification: str = ""
    planned_actions: List[str] = field(default_factory=list)  # List of actions to be performed
    ticket_reference: Optional[str] = None

    # Timing
    requested_duration: timedelta = field(default_factory=lambda: timedelta(hours=2))
    requested_at: datetime = field(default_factory=datetime.now)
    needed_by: Optional[datetime] = None

    # Priority and categorization
    priority: RequestPriority = RequestPriority.MEDIUM
    category: str = "general"  # Derived from reason_code

    # Approval workflow
    status: SessionStatus = SessionStatus.REQUESTED
    approvers: List[str] = field(default_factory=list)
    approval_chain: List[str] = field(default_factory=list)  # Full approval chain
    current_approval_step: int = 0
    approvals: List[Dict[str, Any]] = field(default_factory=list)  # Approval history
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None

    # SLA tracking
    approval_sla: Optional[datetime] = None  # When approval must be completed by
    sla_breached: bool = False

    # Risk assessment
    risk_score: float = 0.0
    requires_dual_approval: bool = False

    def to_dict(self) -> Dict:
        return {
            'request_id': self.request_id,
            'requester_user_id': self.requester_user_id,
            'requester_name': self.requester_name,
            'requester_email': self.requester_email,
            'target_system': self.target_system,
            'firefighter_id': self.firefighter_id,
            'reason_code': self.reason_code.value,
            'reason_code_label': REASON_CODE_CATALOG[self.reason_code].label if self.reason_code in REASON_CODE_CATALOG else 'Other',
            'reason': self.reason,
            'business_justification': self.business_justification,
            'planned_actions': self.planned_actions,
            'ticket_reference': self.ticket_reference,
            'requested_at': self.requested_at.isoformat(),
            'needed_by': self.needed_by.isoformat() if self.needed_by else None,
            'approved_at': self.approved_at.isoformat() if self.approved_at else None,
            'requested_duration': str(self.requested_duration),
            'requested_duration_hours': self.requested_duration.total_seconds() / 3600,
            'status': self.status.value,
            'priority': self.priority.value,
            'approval_chain': self.approval_chain,
            'current_approval_step': self.current_approval_step,
            'approvals': self.approvals,
            'approval_sla': self.approval_sla.isoformat() if self.approval_sla else None,
            'sla_breached': self.sla_breached,
            'risk_score': self.risk_score,
            'requires_dual_approval': self.requires_dual_approval
        }


@dataclass
class ControllerReview:
    """Controller review record for completed firefighter session"""
    review_id: str
    session_id: str
    controller_id: str  # Assigned controller
    controller_name: str
    controller_email: str

    # Status and timing
    status: ReviewStatus = ReviewStatus.PENDING
    assigned_at: datetime = field(default_factory=datetime.now)
    sla_deadline: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Review details
    approved: Optional[bool] = None
    findings: List[str] = field(default_factory=list)
    comments: str = ""
    flagged_activities: List[str] = field(default_factory=list)  # Activity IDs

    # Escalation
    escalated: bool = False
    escalated_to: Optional[str] = None
    escalated_at: Optional[datetime] = None
    escalation_reason: Optional[str] = None

    # SLA tracking
    sla_breached: bool = False

    def to_dict(self) -> Dict:
        return {
            'review_id': self.review_id,
            'session_id': self.session_id,
            'controller_id': self.controller_id,
            'controller_name': self.controller_name,
            'controller_email': self.controller_email,
            'status': self.status.value,
            'assigned_at': self.assigned_at.isoformat(),
            'sla_deadline': self.sla_deadline.isoformat() if self.sla_deadline else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'approved': self.approved,
            'findings': self.findings,
            'comments': self.comments,
            'flagged_activities': self.flagged_activities,
            'escalated': self.escalated,
            'escalated_to': self.escalated_to,
            'escalated_at': self.escalated_at.isoformat() if self.escalated_at else None,
            'escalation_reason': self.escalation_reason,
            'sla_breached': self.sla_breached
        }


@dataclass
class FirefighterSession:
    """Active firefighter session"""
    session_id: str
    request_id: str

    # Users
    requester_user_id: str
    requester_name: str = ""
    requester_email: str = ""
    firefighter_id: str = ""

    # Target
    target_system: str = ""

    # Reason code details
    reason_code: ReasonCode = ReasonCode.OTHER
    reason: str = ""
    planned_actions: List[str] = field(default_factory=list)
    ticket_reference: Optional[str] = None

    # Session timing
    start_time: datetime = field(default_factory=datetime.now)
    end_time: datetime = field(default_factory=datetime.now)
    actual_end_time: Optional[datetime] = None
    original_end_time: Optional[datetime] = None  # For tracking extensions

    # Extension tracking
    extension_count: int = 0
    max_extensions: int = 2
    extension_history: List[Dict[str, Any]] = field(default_factory=list)

    # Status
    status: SessionStatus = SessionStatus.ACTIVE

    # Security
    session_token: str = ""
    mfa_verified: bool = False

    # Activity tracking
    activities: List[ActivityLog] = field(default_factory=list)
    activity_count: int = 0
    sensitive_activity_count: int = 0

    # Controller Review
    requires_review: bool = True
    controller_id: Optional[str] = None
    controller_review: Optional[ControllerReview] = None
    review_sla_hours: int = 24

    # Legacy fields for compatibility
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    review_comments: Optional[str] = None

    # Approval metadata
    approver: str = ""

    def is_active(self) -> bool:
        """Check if session is currently active"""
        if self.status != SessionStatus.ACTIVE:
            return False
        return datetime.now() < self.end_time

    def remaining_time(self) -> timedelta:
        """Get remaining session time"""
        if not self.is_active():
            return timedelta(0)
        return self.end_time - datetime.now()

    def can_extend(self) -> bool:
        """Check if session can be extended"""
        return (
            self.status == SessionStatus.ACTIVE
            and self.extension_count < self.max_extensions
        )

    def to_dict(self) -> Dict:
        return {
            'session_id': self.session_id,
            'request_id': self.request_id,
            'requester_user_id': self.requester_user_id,
            'requester_name': self.requester_name,
            'firefighter_id': self.firefighter_id,
            'target_system': self.target_system,
            'reason_code': self.reason_code.value,
            'reason': self.reason,
            'planned_actions': self.planned_actions,
            'ticket_reference': self.ticket_reference,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat(),
            'actual_end_time': self.actual_end_time.isoformat() if self.actual_end_time else None,
            'original_end_time': self.original_end_time.isoformat() if self.original_end_time else None,
            'status': self.status.value,
            'mfa_verified': self.mfa_verified,
            'activity_count': self.activity_count,
            'sensitive_activity_count': self.sensitive_activity_count,
            'extension_count': self.extension_count,
            'can_extend': self.can_extend(),
            'remaining_time_minutes': int(self.remaining_time().total_seconds() / 60),
            'requires_review': self.requires_review,
            'controller_id': self.controller_id,
            'controller_review': self.controller_review.to_dict() if self.controller_review else None,
            'review_sla_hours': self.review_sla_hours
        }


class FirefighterManager:
    """
    Main Firefighter/Emergency Access Manager.

    Handles the complete lifecycle:
    1. Request submission
    2. Risk assessment
    3. Approval workflow
    4. Session creation and monitoring
    5. Activity logging
    6. Session termination
    7. Supervisor review
    """

    def __init__(self,
                 storage_backend=None,
                 notification_handler: Optional[Callable] = None,
                 sap_connector=None):
        """
        Initialize Firefighter Manager.

        Args:
            storage_backend: Database/storage for persistence (optional, uses in-memory if None)
            notification_handler: Callback for sending notifications
            sap_connector: SAP connector for provisioning access
        """
        self.storage = storage_backend

        # In-memory storage for development/testing
        self.requests: Dict[str, FirefighterRequest] = {}
        self.sessions: Dict[str, FirefighterSession] = {}
        self.active_sessions_by_ff: Dict[str, str] = {}  # firefighter_id -> session_id

        self.notification_handler = notification_handler
        self.sap_connector = sap_connector

        # Configuration
        self.config = {
            'max_session_duration': timedelta(hours=8),
            'default_session_duration': timedelta(hours=2),
            'require_mfa': True,
            'require_dual_approval_threshold': 70,  # Risk score threshold
            'auto_terminate_idle_after': timedelta(minutes=30),
            'require_review': True,
            'sensitive_tcodes': ['SE16N', 'SE11', 'SU01', 'PFCG', 'SM30', 'SM31'],
        }

        # Approver configuration (would come from directory/config)
        self.approver_matrix = {
            'default': ['security.admin@company.com', 'it.manager@company.com'],
            'finance': ['finance.manager@company.com', 'cfo@company.com'],
            'hr': ['hr.director@company.com', 'chro@company.com'],
            'it': ['it.director@company.com', 'ciso@company.com']
        }

        logger.info("FirefighterManager initialized")

    # ==========================================================================
    # Request Management
    # ==========================================================================

    async def submit_request(self,
                           requester_user_id: str,
                           requester_name: str,
                           requester_email: str,
                           target_system: str,
                           firefighter_id: str,
                           reason_code: ReasonCode,
                           reason: str = "",
                           business_justification: str = "",
                           planned_actions: Optional[List[str]] = None,
                           duration: Optional[timedelta] = None,
                           priority: Optional[RequestPriority] = None,
                           ticket_reference: Optional[str] = None) -> FirefighterRequest:
        """
        Submit a new firefighter access request with structured reason code.

        Args:
            requester_user_id: ID of the user requesting access
            requester_name: Full name of requester
            requester_email: Email for notifications
            target_system: Target SAP system
            firefighter_id: Firefighter account to use
            reason_code: Structured reason code from REASON_CODE_CATALOG
            reason: Additional description/details
            business_justification: Detailed justification (required for some codes)
            planned_actions: List of actions to be performed during session
            duration: Requested session duration (capped by reason code config)
            priority: Request priority level (defaults from reason code config)
            ticket_reference: Related incident/change ticket (required for some codes)

        Returns:
            FirefighterRequest object
        """
        # Get reason code configuration
        if reason_code not in REASON_CODE_CATALOG:
            raise ValueError(f"Invalid reason code: {reason_code}")

        reason_config = REASON_CODE_CATALOG[reason_code]

        # Validate required fields based on reason code
        if reason_config.requires_ticket and not ticket_reference:
            raise ValueError(f"Reason code '{reason_config.label}' requires a ticket reference")

        if reason_config.requires_justification and not business_justification:
            raise ValueError(f"Reason code '{reason_config.label}' requires business justification")

        # Validate firefighter ID is available
        if self.sap_connector:
            availability = self.sap_connector.check_firefighter_availability(firefighter_id)
            if not availability.get('available'):
                raise ValueError(f"Firefighter ID {firefighter_id} is not available: "
                               f"{availability.get('error', 'Unknown reason')}")

        # Check if firefighter already has active session
        if firefighter_id in self.active_sessions_by_ff:
            raise ValueError(f"Firefighter ID {firefighter_id} already has an active session")

        # Determine duration - cap by reason code max
        max_duration = timedelta(hours=reason_config.max_duration_hours)
        requested_duration = duration or self.config['default_session_duration']
        if requested_duration > max_duration:
            requested_duration = max_duration
            logger.warning(f"Duration capped to reason code maximum: {max_duration}")

        # Determine priority - use reason code default if not specified
        request_priority = priority or reason_config.default_priority

        # Create request
        request = FirefighterRequest(
            request_id=self._generate_request_id(),
            requester_user_id=requester_user_id,
            requester_name=requester_name,
            requester_email=requester_email,
            target_system=target_system,
            firefighter_id=firefighter_id,
            reason_code=reason_code,
            reason_code_config=reason_config,
            reason=reason,
            business_justification=business_justification,
            planned_actions=planned_actions or [],
            requested_duration=requested_duration,
            priority=request_priority,
            ticket_reference=ticket_reference,
            status=SessionStatus.REQUESTED,
            category=reason_code.value
        )

        # Set approval chain from reason code config
        request.approval_chain = reason_config.approval_chain.copy()
        request.approvers = self._resolve_approvers(reason_config.approval_chain, target_system)

        # Calculate approval SLA
        request.approval_sla = datetime.now() + timedelta(minutes=reason_config.sla_minutes)

        # Perform risk assessment
        request.risk_score = await self._assess_risk(request)

        # Determine if dual approval is required
        request.requires_dual_approval = (
            request.risk_score >= self.config['require_dual_approval_threshold']
            or len(reason_config.approval_chain) > 1
        )

        # Update status
        request.status = SessionStatus.PENDING_APPROVAL

        # Store request
        self.requests[request.request_id] = request

        # Send notifications to approvers
        await self._notify_approvers(request)

        logger.info(f"Firefighter request {request.request_id} submitted by {requester_user_id} "
                   f"with reason code {reason_code.value}")

        return request

    def _resolve_approvers(self, approval_chain: List[str], target_system: str) -> List[str]:
        """
        Resolve approval chain roles to actual approver user IDs.

        In production, this would query the organization directory.
        """
        # Role to approver mapping (would come from config/directory in production)
        role_mapping = {
            'ff_owner': ['ff.owner@company.com'],
            'it_manager': ['it.manager@company.com'],
            'security_manager': ['security.manager@company.com'],
            'ciso': ['ciso@company.com'],
            'compliance_manager': ['compliance.manager@company.com'],
            'finance_manager': ['finance.manager@company.com'],
            'data_owner': ['data.owner@company.com']
        }

        approvers = []
        for role in approval_chain:
            role_approvers = role_mapping.get(role, self.approver_matrix.get('default', []))
            approvers.extend(role_approvers)

        return list(set(approvers))  # Remove duplicates

    @staticmethod
    def get_reason_codes() -> List[Dict]:
        """Get all available reason codes with their configurations"""
        return [config.to_dict() for config in REASON_CODE_CATALOG.values()]

    @staticmethod
    def get_reason_code_config(code: ReasonCode) -> Optional[ReasonCodeConfig]:
        """Get configuration for a specific reason code"""
        return REASON_CODE_CATALOG.get(code)

    async def approve_request(self,
                            request_id: str,
                            approver_id: str,
                            comments: Optional[str] = None) -> FirefighterSession:
        """
        Approve a firefighter request and create session.

        Args:
            request_id: ID of the request to approve
            approver_id: ID of the approver
            comments: Optional approval comments

        Returns:
            FirefighterSession object
        """

        request = self.requests.get(request_id)
        if not request:
            raise ValueError(f"Request {request_id} not found")

        if request.status != SessionStatus.PENDING_APPROVAL:
            raise ValueError(f"Request is not pending approval (status: {request.status.value})")

        if approver_id not in request.approvers:
            raise PermissionError(f"User {approver_id} is not authorized to approve this request")

        # Update request
        request.approved_by = approver_id
        request.approved_at = datetime.now()
        request.status = SessionStatus.APPROVED

        # Create session
        session = await self._create_session(request)

        # Notify requester
        await self._notify_requester(request, session, approved=True)

        logger.info(f"Request {request_id} approved by {approver_id}")

        return session

    async def reject_request(self,
                           request_id: str,
                           approver_id: str,
                           reason: str) -> FirefighterRequest:
        """Reject a firefighter request"""

        request = self.requests.get(request_id)
        if not request:
            raise ValueError(f"Request {request_id} not found")

        if request.status != SessionStatus.PENDING_APPROVAL:
            raise ValueError(f"Request is not pending approval")

        if approver_id not in request.approvers:
            raise PermissionError(f"User {approver_id} is not authorized")

        request.status = SessionStatus.REJECTED
        request.rejection_reason = reason

        # Notify requester
        await self._notify_requester(request, None, approved=False, reason=reason)

        logger.info(f"Request {request_id} rejected by {approver_id}: {reason}")

        return request

    # ==========================================================================
    # Session Management
    # ==========================================================================

    async def _create_session(self, request: FirefighterRequest) -> FirefighterSession:
        """Create a new firefighter session from approved request"""

        # Get review SLA from reason code config
        review_sla_hours = 24  # Default
        if request.reason_code in REASON_CODE_CATALOG:
            review_sla_hours = REASON_CODE_CATALOG[request.reason_code].controller_review_sla_hours

        start_time = datetime.now()
        end_time = start_time + request.requested_duration

        session = FirefighterSession(
            session_id=self._generate_session_id(),
            request_id=request.request_id,
            requester_user_id=request.requester_user_id,
            requester_name=request.requester_name,
            requester_email=request.requester_email,
            firefighter_id=request.firefighter_id,
            target_system=request.target_system,
            reason_code=request.reason_code,
            reason=request.reason,
            planned_actions=request.planned_actions,
            ticket_reference=request.ticket_reference,
            start_time=start_time,
            end_time=end_time,
            original_end_time=end_time,
            status=SessionStatus.ACTIVE,
            session_token=self._generate_session_token(),
            review_sla_hours=review_sla_hours,
            approver=request.approved_by or ""
        )

        # Provision access in SAP
        if self.sap_connector:
            # Unlock firefighter ID
            unlock_result = self.sap_connector.unlock_firefighter(request.firefighter_id)
            if not unlock_result.get('success'):
                raise RuntimeError(f"Failed to unlock firefighter: {unlock_result.get('message')}")

            # Set temporary password
            temp_password = self._generate_temp_password()
            pwd_result = self.sap_connector.set_temporary_password(
                request.firefighter_id, temp_password
            )
            if not pwd_result.get('success'):
                # Roll back - lock the account
                self.sap_connector.lock_firefighter(request.firefighter_id)
                raise RuntimeError(f"Failed to set password: {pwd_result.get('message')}")

            # Store password securely for requester retrieval
            # In production, use a secure vault or encrypted storage
            session.session_token = f"{session.session_token}:{temp_password}"

        # Store session
        self.sessions[session.session_id] = session
        self.active_sessions_by_ff[request.firefighter_id] = session.session_id

        # Schedule auto-termination
        asyncio.create_task(self._schedule_auto_terminate(session))

        # Log session start
        await self.log_activity(
            session.session_id,
            'SESSION_START',
            {'reason': request.reason, 'approver': request.approved_by}
        )

        logger.info(f"Session {session.session_id} created for {request.requester_user_id}")

        return session

    async def get_session_credentials(self,
                                     session_id: str,
                                     requester_user_id: str) -> Dict:
        """
        Get credentials for an active session.

        Only the original requester can retrieve credentials.
        """
        session = self.sessions.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        if session.requester_user_id != requester_user_id:
            raise PermissionError("Only the requester can retrieve session credentials")

        if not session.is_active():
            raise ValueError("Session is no longer active")

        # Parse token (contains password in demo - use secure storage in production)
        parts = session.session_token.split(':')
        password = parts[1] if len(parts) > 1 else None

        return {
            'firefighter_id': session.firefighter_id,
            'password': password,  # Would be retrieved from secure vault in production
            'valid_until': session.end_time.isoformat(),
            'remaining_time': str(session.remaining_time())
        }

    async def end_session(self,
                         session_id: str,
                         ended_by: str,
                         reason: str = "Normal completion") -> FirefighterSession:
        """End an active firefighter session"""

        session = self.sessions.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        if session.status != SessionStatus.ACTIVE:
            raise ValueError(f"Session is not active (status: {session.status.value})")

        # Update session
        session.status = SessionStatus.COMPLETED
        session.actual_end_time = datetime.now()

        # Lock firefighter in SAP
        if self.sap_connector:
            self.sap_connector.lock_firefighter(session.firefighter_id)

        # Remove from active sessions
        if session.firefighter_id in self.active_sessions_by_ff:
            del self.active_sessions_by_ff[session.firefighter_id]

        # Log session end
        await self.log_activity(
            session_id,
            'SESSION_END',
            {'ended_by': ended_by, 'reason': reason}
        )

        # Trigger review workflow if required
        if session.requires_review:
            await self._initiate_review(session)

        logger.info(f"Session {session_id} ended by {ended_by}: {reason}")

        return session

    async def revoke_session(self,
                           session_id: str,
                           revoked_by: str,
                           reason: str) -> FirefighterSession:
        """Revoke/force-terminate an active session"""

        session = self.sessions.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        session.status = SessionStatus.REVOKED
        session.actual_end_time = datetime.now()

        # Immediately lock firefighter
        if self.sap_connector:
            self.sap_connector.lock_firefighter(session.firefighter_id)

        # Remove from active sessions
        if session.firefighter_id in self.active_sessions_by_ff:
            del self.active_sessions_by_ff[session.firefighter_id]

        # Log revocation
        await self.log_activity(
            session_id,
            'SESSION_REVOKED',
            {'revoked_by': revoked_by, 'reason': reason},
            is_sensitive=True,
            requires_review=True
        )

        # Alert security team
        await self._alert_security(session, reason)

        logger.warning(f"Session {session_id} REVOKED by {revoked_by}: {reason}")

        return session

    # ==========================================================================
    # Session Extension
    # ==========================================================================

    async def extend_session(self,
                            session_id: str,
                            requested_by: str,
                            extension_minutes: int,
                            reason: str,
                            approved_by: Optional[str] = None) -> FirefighterSession:
        """
        Extend an active firefighter session.

        Args:
            session_id: Session to extend
            requested_by: User requesting extension
            extension_minutes: Additional time in minutes
            reason: Justification for extension
            approved_by: Approver (if pre-approved)

        Returns:
            Updated FirefighterSession
        """
        session = self.sessions.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        if not session.is_active():
            raise ValueError("Session is not active - cannot extend")

        if not session.can_extend():
            raise ValueError(f"Session has reached maximum extensions ({session.max_extensions})")

        # Cap extension to reasonable limits
        max_extension = 120  # 2 hours max per extension
        extension_minutes = min(extension_minutes, max_extension)

        # Record extension
        extension_record = {
            'extension_number': session.extension_count + 1,
            'requested_by': requested_by,
            'approved_by': approved_by or requested_by,
            'extension_minutes': extension_minutes,
            'reason': reason,
            'previous_end_time': session.end_time.isoformat(),
            'new_end_time': (session.end_time + timedelta(minutes=extension_minutes)).isoformat(),
            'timestamp': datetime.now().isoformat()
        }

        # Update session
        session.end_time = session.end_time + timedelta(minutes=extension_minutes)
        session.extension_count += 1
        session.extension_history.append(extension_record)

        # Log the extension
        await self.log_activity(
            session_id,
            'SESSION_EXTENDED',
            extension_record
        )

        # Reschedule auto-termination
        asyncio.create_task(self._schedule_auto_terminate(session))

        logger.info(f"Session {session_id} extended by {extension_minutes} minutes "
                   f"(extension #{session.extension_count})")

        return session

    # ==========================================================================
    # Controller Review Management
    # ==========================================================================

    async def _initiate_review(self, session: FirefighterSession):
        """Initiate controller review workflow with SLA tracking"""

        # Assign controller based on firefighter ID owner
        controller = self._get_assigned_controller(session.firefighter_id)

        # Calculate review SLA deadline
        sla_deadline = datetime.now() + timedelta(hours=session.review_sla_hours)

        # Create controller review record
        review = ControllerReview(
            review_id=f"FFR-{session.session_id}",
            session_id=session.session_id,
            controller_id=controller['id'],
            controller_name=controller['name'],
            controller_email=controller['email'],
            status=ReviewStatus.PENDING,
            sla_deadline=sla_deadline
        )

        session.controller_id = controller['id']
        session.controller_review = review

        # Send notification to controller
        if self.notification_handler:
            await self.notification_handler(
                recipient=controller['email'],
                subject=f"[ACTION REQUIRED] Firefighter Session Review: {session.session_id}",
                message=f"A firefighter session requires your review.\n\n"
                       f"Session ID: {session.session_id}\n"
                       f"User: {session.requester_name}\n"
                       f"Firefighter ID: {session.firefighter_id}\n"
                       f"Reason: {session.reason}\n"
                       f"Duration: {session.start_time} - {session.actual_end_time or session.end_time}\n"
                       f"Activity Count: {session.activity_count}\n"
                       f"Sensitive Activities: {session.sensitive_activity_count}\n\n"
                       f"SLA Deadline: {sla_deadline.isoformat()}\n\n"
                       f"Please review the session activities and submit your findings."
            )

        # Schedule SLA breach check
        asyncio.create_task(self._check_review_sla(session))

        logger.info(f"Review initiated for session {session.session_id}, "
                   f"assigned to {controller['name']}, SLA: {sla_deadline}")

    def _get_assigned_controller(self, firefighter_id: str) -> Dict[str, str]:
        """Get the assigned controller for a firefighter ID"""
        # In production, this would query a controller assignment table
        # For now, use a default mapping
        controller_mapping = {
            'FF_EMERGENCY_01': {
                'id': 'controller1',
                'name': 'SAP Controller',
                'email': 'sap.controller@company.com'
            },
            'FF_EMERGENCY_02': {
                'id': 'controller1',
                'name': 'SAP Controller',
                'email': 'sap.controller@company.com'
            },
            'FF_BASIS_01': {
                'id': 'controller2',
                'name': 'Basis Controller',
                'email': 'basis.controller@company.com'
            }
        }

        return controller_mapping.get(firefighter_id, {
            'id': 'default_controller',
            'name': 'Default Controller',
            'email': 'ff.controller@company.com'
        })

    async def _check_review_sla(self, session: FirefighterSession):
        """Check and escalate if review SLA is breached"""
        if not session.controller_review:
            return

        review = session.controller_review
        if not review.sla_deadline:
            return

        # Wait until SLA deadline
        wait_seconds = (review.sla_deadline - datetime.now()).total_seconds()
        if wait_seconds > 0:
            await asyncio.sleep(wait_seconds)

        # Check if review is still pending
        current_session = self.sessions.get(session.session_id)
        if not current_session or not current_session.controller_review:
            return

        current_review = current_session.controller_review
        if current_review.status == ReviewStatus.PENDING:
            # Mark SLA as breached
            current_review.sla_breached = True

            # Escalate
            await self._escalate_review_sla(current_session)

    async def _escalate_review_sla(self, session: FirefighterSession):
        """Escalate review when SLA is breached"""
        if not session.controller_review:
            return

        review = session.controller_review
        review.escalated = True
        review.escalated_to = 'security.manager@company.com'
        review.escalated_at = datetime.now()
        review.escalation_reason = 'Review SLA breached'
        review.status = ReviewStatus.ESCALATED

        logger.warning(f"Review SLA breached for session {session.session_id}, escalating")

        if self.notification_handler:
            await self.notification_handler(
                recipient='security.manager@company.com',
                subject=f"[ESCALATION] Review SLA Breached: {session.session_id}",
                message=f"The controller review for session {session.session_id} "
                       f"has not been completed within the SLA.\n\n"
                       f"Original Controller: {review.controller_name}\n"
                       f"SLA Deadline: {review.sla_deadline}\n"
                       f"Session User: {session.requester_name}\n"
                       f"Activity Count: {session.activity_count}"
            )

    async def start_controller_review(self, session_id: str, controller_id: str) -> ControllerReview:
        """Mark controller review as in progress"""
        session = self.sessions.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        if not session.controller_review:
            raise ValueError("No controller review assigned for this session")

        review = session.controller_review
        if review.controller_id != controller_id:
            raise PermissionError("You are not the assigned controller for this review")

        review.status = ReviewStatus.IN_PROGRESS
        review.started_at = datetime.now()

        logger.info(f"Controller review started for session {session_id}")

        return review

    async def complete_controller_review(self,
                                        session_id: str,
                                        controller_id: str,
                                        approved: bool,
                                        findings: List[str],
                                        comments: str,
                                        flagged_activities: Optional[List[str]] = None) -> ControllerReview:
        """
        Complete controller review for a session.

        Args:
            session_id: Session being reviewed
            controller_id: Controller completing the review
            approved: Whether activities are approved
            findings: List of findings from review
            comments: Review comments
            flagged_activities: Activity IDs that are flagged

        Returns:
            Updated ControllerReview
        """
        session = self.sessions.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        if not session.controller_review:
            raise ValueError("No controller review assigned")

        review = session.controller_review
        if review.controller_id != controller_id:
            raise PermissionError("Not authorized to complete this review")

        # Update review
        review.status = ReviewStatus.APPROVED if approved else ReviewStatus.FLAGGED
        review.completed_at = datetime.now()
        review.approved = approved
        review.findings = findings
        review.comments = comments
        review.flagged_activities = flagged_activities or []

        # Update session legacy fields for compatibility
        session.reviewed_by = controller_id
        session.reviewed_at = review.completed_at
        session.review_comments = comments

        # If flagged, escalate to security
        if not approved:
            await self._escalate_review(session, controller_id, comments)

        logger.info(f"Controller review completed for session {session_id}: "
                   f"{'Approved' if approved else 'Flagged'}")

        return review

    # ==========================================================================
    # Audit Evidence Export
    # ==========================================================================

    async def generate_audit_evidence(self, session_id: str) -> Dict[str, Any]:
        """
        Generate comprehensive audit evidence package for a session.

        Returns a complete audit trail including:
        - Request details
        - Approval chain
        - Session timeline
        - All activities
        - Controller review
        - Evidence hash for integrity

        Args:
            session_id: Session to generate evidence for

        Returns:
            Complete audit evidence package
        """
        session = self.sessions.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        request = self.requests.get(session.request_id)

        # Compile evidence package
        evidence = {
            'evidence_id': f"AUD-{session_id}-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            'generated_at': datetime.now().isoformat(),
            'generated_by': 'GOVERNEX+ Firefighter Module',

            # Request Information
            'request': {
                'request_id': request.request_id if request else 'N/A',
                'requester': {
                    'user_id': session.requester_user_id,
                    'name': session.requester_name,
                    'email': session.requester_email
                },
                'reason_code': session.reason_code.value,
                'reason_code_label': REASON_CODE_CATALOG[session.reason_code].label if session.reason_code in REASON_CODE_CATALOG else 'Other',
                'reason_description': session.reason,
                'planned_actions': session.planned_actions,
                'ticket_reference': session.ticket_reference,
                'business_justification': request.business_justification if request else '',
                'requested_at': request.requested_at.isoformat() if request else None,
                'requested_duration_hours': request.requested_duration.total_seconds() / 3600 if request else None
            },

            # Approval Information
            'approval': {
                'approval_chain': request.approval_chain if request else [],
                'approvals': request.approvals if request else [],
                'final_approver': request.approved_by if request else None,
                'approved_at': request.approved_at.isoformat() if request and request.approved_at else None,
                'approval_sla': request.approval_sla.isoformat() if request and request.approval_sla else None,
                'sla_breached': request.sla_breached if request else False,
                'risk_score': request.risk_score if request else 0
            },

            # Session Information
            'session': {
                'session_id': session.session_id,
                'firefighter_id': session.firefighter_id,
                'target_system': session.target_system,
                'start_time': session.start_time.isoformat(),
                'end_time': session.end_time.isoformat(),
                'actual_end_time': session.actual_end_time.isoformat() if session.actual_end_time else None,
                'original_end_time': session.original_end_time.isoformat() if session.original_end_time else None,
                'status': session.status.value,
                'duration_minutes': int((session.actual_end_time or session.end_time - session.start_time).total_seconds() / 60) if session.actual_end_time else int((datetime.now() - session.start_time).total_seconds() / 60),
                'extension_count': session.extension_count,
                'extension_history': session.extension_history,
                'mfa_verified': session.mfa_verified
            },

            # Activity Log
            'activities': {
                'total_count': session.activity_count,
                'sensitive_count': session.sensitive_activity_count,
                'log': [activity.to_dict() for activity in session.activities]
            },

            # Controller Review
            'controller_review': session.controller_review.to_dict() if session.controller_review else {
                'status': 'pending',
                'controller_id': session.controller_id,
                'reviewed_by': session.reviewed_by,
                'reviewed_at': session.reviewed_at.isoformat() if session.reviewed_at else None,
                'comments': session.review_comments
            },

            # Compliance Metadata
            'compliance': {
                'sox_relevant': True,
                'gdpr_relevant': False,  # Would be determined by data accessed
                'retention_period_days': 2555,  # 7 years for SOX
                'data_classification': 'confidential'
            }
        }

        # Generate evidence hash for integrity
        evidence_json = json.dumps(evidence, sort_keys=True, default=str)
        evidence['integrity_hash'] = hashlib.sha256(evidence_json.encode()).hexdigest()

        logger.info(f"Audit evidence generated for session {session_id}")

        return evidence

    async def export_audit_evidence(self,
                                   session_id: str,
                                   format: str = 'json') -> Dict[str, Any]:
        """
        Export audit evidence in specified format.

        Args:
            session_id: Session to export
            format: Export format ('json', 'csv', 'pdf_data')

        Returns:
            Export package with content and metadata
        """
        evidence = await self.generate_audit_evidence(session_id)

        if format == 'json':
            content = json.dumps(evidence, indent=2, default=str)
            mime_type = 'application/json'
            filename = f"firefighter_audit_{session_id}_{datetime.now().strftime('%Y%m%d')}.json"

        elif format == 'csv':
            # Generate CSV for activities
            import csv
            import io
            output = io.StringIO()
            writer = csv.writer(output)

            # Header
            writer.writerow(['Session ID', 'Timestamp', 'Action Type', 'Details', 'Sensitive', 'Client IP'])

            # Activities
            for activity in evidence['activities']['log']:
                writer.writerow([
                    session_id,
                    activity['timestamp'],
                    activity['action_type'],
                    json.dumps(activity['action_details']),
                    activity['is_sensitive'],
                    activity.get('client_ip', '')
                ])

            content = output.getvalue()
            mime_type = 'text/csv'
            filename = f"firefighter_activities_{session_id}_{datetime.now().strftime('%Y%m%d')}.csv"

        elif format == 'pdf_data':
            # Return structured data for PDF generation
            content = evidence
            mime_type = 'application/json'
            filename = f"firefighter_audit_{session_id}_{datetime.now().strftime('%Y%m%d')}.pdf"

        else:
            raise ValueError(f"Unsupported export format: {format}")

        return {
            'content': content,
            'mime_type': mime_type,
            'filename': filename,
            'session_id': session_id,
            'generated_at': datetime.now().isoformat(),
            'integrity_hash': evidence['integrity_hash']
        }

    async def get_sessions_for_audit(self,
                                    start_date: Optional[datetime] = None,
                                    end_date: Optional[datetime] = None,
                                    status: Optional[SessionStatus] = None,
                                    firefighter_id: Optional[str] = None) -> List[Dict]:
        """
        Get sessions matching audit criteria.

        Args:
            start_date: Filter by start date
            end_date: Filter by end date
            status: Filter by status
            firefighter_id: Filter by firefighter ID

        Returns:
            List of matching sessions with summary info
        """
        results = []

        for session in self.sessions.values():
            # Apply filters
            if start_date and session.start_time < start_date:
                continue
            if end_date and session.start_time > end_date:
                continue
            if status and session.status != status:
                continue
            if firefighter_id and session.firefighter_id != firefighter_id:
                continue

            # Include summary info
            results.append({
                **session.to_dict(),
                'review_status': session.controller_review.status.value if session.controller_review else 'pending',
                'has_sensitive_activities': session.sensitive_activity_count > 0,
                'audit_evidence_available': True
            })

        return results

    # ==========================================================================
    # Activity Logging
    # ==========================================================================

    async def log_activity(self,
                          session_id: str,
                          action_type: str,
                          action_details: Dict,
                          client_ip: Optional[str] = None,
                          user_agent: Optional[str] = None,
                          is_sensitive: bool = False,
                          requires_review: bool = False) -> ActivityLog:
        """Log an activity during a firefighter session"""

        session = self.sessions.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        # Check if action involves sensitive TCODEs
        tcode = action_details.get('tcode', '')
        if tcode in self.config['sensitive_tcodes']:
            is_sensitive = True
            requires_review = True

        activity = ActivityLog(
            log_id=str(uuid.uuid4()),
            session_id=session_id,
            timestamp=datetime.now(),
            action_type=action_type,
            action_details=action_details,
            client_ip=client_ip,
            user_agent=user_agent,
            is_sensitive=is_sensitive,
            requires_review=requires_review
        )

        session.activities.append(activity)
        session.activity_count += 1

        # Track sensitive activities
        if is_sensitive:
            session.sensitive_activity_count += 1
            # Alert in real-time
            await self._alert_sensitive_activity(session, activity)

        return activity

    async def get_session_activities(self, session_id: str) -> List[Dict]:
        """Get all activities for a session"""
        session = self.sessions.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        return [a.to_dict() for a in session.activities]

    # ==========================================================================
    # Review Management
    # ==========================================================================

    async def submit_review(self,
                          session_id: str,
                          reviewer_id: str,
                          approved: bool,
                          comments: str) -> FirefighterSession:
        """Submit supervisor review for a completed session"""

        session = self.sessions.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        if session.status not in [SessionStatus.COMPLETED, SessionStatus.EXPIRED]:
            raise ValueError("Session must be completed before review")

        session.reviewed_by = reviewer_id
        session.reviewed_at = datetime.now()
        session.review_comments = comments

        if not approved:
            # Escalate to security
            await self._escalate_review(session, reviewer_id, comments)

        logger.info(f"Session {session_id} reviewed by {reviewer_id}: "
                   f"{'Approved' if approved else 'Flagged'}")

        return session

    async def get_pending_reviews(self, reviewer_id: str) -> List[Dict]:
        """Get sessions pending review for a reviewer"""
        pending = []

        for session in self.sessions.values():
            if (session.status in [SessionStatus.COMPLETED, SessionStatus.EXPIRED]
                and session.requires_review
                and session.reviewed_by is None):
                pending.append(session.to_dict())

        return pending

    # ==========================================================================
    # Helper Methods
    # ==========================================================================

    def _generate_request_id(self) -> str:
        """Generate unique request ID"""
        timestamp = datetime.now().strftime('%y%m%d%H%M')
        return f"FFR-{timestamp}-{secrets.token_hex(4).upper()}"

    def _generate_session_id(self) -> str:
        """Generate unique session ID"""
        timestamp = datetime.now().strftime('%y%m%d%H%M')
        return f"FFS-{timestamp}-{secrets.token_hex(4).upper()}"

    def _generate_session_token(self) -> str:
        """Generate secure session token"""
        return secrets.token_urlsafe(32)

    def _generate_temp_password(self) -> str:
        """Generate temporary password"""
        # Generate a password that meets SAP requirements
        import string
        chars = string.ascii_letters + string.digits + "!@#$%"
        password = ''.join(secrets.choice(chars) for _ in range(16))
        return password

    async def _assess_risk(self, request: FirefighterRequest) -> float:
        """Assess risk score for a request"""
        score = 0.0

        # Priority-based risk
        priority_scores = {
            RequestPriority.LOW: 10,
            RequestPriority.MEDIUM: 25,
            RequestPriority.HIGH: 50,
            RequestPriority.CRITICAL: 70
        }
        score += priority_scores.get(request.priority, 25)

        # Duration-based risk
        hours = request.requested_duration.total_seconds() / 3600
        if hours > 4:
            score += 15
        if hours > 6:
            score += 10

        # Time-based risk (outside business hours)
        hour = datetime.now().hour
        if hour < 8 or hour > 18:
            score += 15

        # Weekend risk
        if datetime.now().weekday() >= 5:
            score += 10

        return min(score, 100)

    def _determine_approvers(self, request: FirefighterRequest) -> List[str]:
        """Determine appropriate approvers based on request"""
        category = request.category.lower()

        if category in self.approver_matrix:
            return self.approver_matrix[category]

        return self.approver_matrix['default']

    async def _schedule_auto_terminate(self, session: FirefighterSession):
        """Schedule automatic session termination"""
        remaining = (session.end_time - datetime.now()).total_seconds()

        if remaining > 0:
            await asyncio.sleep(remaining)

            # Check if still active
            current_session = self.sessions.get(session.session_id)
            if current_session and current_session.status == SessionStatus.ACTIVE:
                current_session.status = SessionStatus.EXPIRED
                current_session.actual_end_time = datetime.now()

                # Lock firefighter
                if self.sap_connector:
                    self.sap_connector.lock_firefighter(session.firefighter_id)

                # Remove from active
                if session.firefighter_id in self.active_sessions_by_ff:
                    del self.active_sessions_by_ff[session.firefighter_id]

                logger.info(f"Session {session.session_id} auto-terminated (expired)")

    async def _notify_approvers(self, request: FirefighterRequest):
        """Send notifications to approvers"""
        if self.notification_handler:
            for approver in request.approvers:
                await self.notification_handler(
                    recipient=approver,
                    subject=f"Firefighter Access Request: {request.request_id}",
                    message=f"User {request.requester_name} has requested firefighter access.\n"
                           f"System: {request.target_system}\n"
                           f"Reason: {request.reason}\n"
                           f"Risk Score: {request.risk_score}"
                )

    async def _notify_requester(self,
                              request: FirefighterRequest,
                              session: Optional[FirefighterSession],
                              approved: bool,
                              reason: str = ""):
        """Notify requester of request status"""
        if self.notification_handler:
            if approved:
                message = (f"Your firefighter access request has been approved.\n"
                          f"Session ID: {session.session_id}\n"
                          f"Valid until: {session.end_time}")
            else:
                message = (f"Your firefighter access request has been rejected.\n"
                          f"Reason: {reason}")

            await self.notification_handler(
                recipient=request.requester_email,
                subject=f"Firefighter Request {request.request_id}: "
                       f"{'Approved' if approved else 'Rejected'}",
                message=message
            )

    async def _alert_sensitive_activity(self,
                                       session: FirefighterSession,
                                       activity: ActivityLog):
        """Alert on sensitive activity during session"""
        logger.warning(f"SENSITIVE ACTIVITY in session {session.session_id}: "
                      f"{activity.action_type} - {activity.action_details}")

        if self.notification_handler:
            await self.notification_handler(
                recipient='security@company.com',
                subject=f"[ALERT] Sensitive Activity - Session {session.session_id}",
                message=f"Sensitive activity detected:\n"
                       f"User: {session.requester_user_id}\n"
                       f"Firefighter: {session.firefighter_id}\n"
                       f"Action: {activity.action_type}\n"
                       f"Details: {json.dumps(activity.action_details)}"
            )

    async def _alert_security(self, session: FirefighterSession, reason: str):
        """Alert security team"""
        logger.critical(f"SECURITY ALERT for session {session.session_id}: {reason}")

    async def _initiate_review(self, session: FirefighterSession):
        """Initiate supervisor review workflow"""
        logger.info(f"Review initiated for session {session.session_id}")

    async def _escalate_review(self,
                             session: FirefighterSession,
                             reviewer_id: str,
                             comments: str):
        """Escalate flagged session to security"""
        logger.warning(f"Session {session.session_id} flagged by reviewer {reviewer_id}")

    # ==========================================================================
    # Query Methods
    # ==========================================================================

    def get_request(self, request_id: str) -> Optional[FirefighterRequest]:
        """Get request by ID"""
        return self.requests.get(request_id)

    def get_session(self, session_id: str) -> Optional[FirefighterSession]:
        """Get session by ID"""
        return self.sessions.get(session_id)

    def get_active_sessions(self) -> List[Dict]:
        """Get all active sessions"""
        return [
            s.to_dict() for s in self.sessions.values()
            if s.status == SessionStatus.ACTIVE
        ]

    def get_pending_requests(self) -> List[Dict]:
        """Get all pending approval requests"""
        return [
            r.to_dict() for r in self.requests.values()
            if r.status == SessionStatus.PENDING_APPROVAL
        ]

    def get_user_sessions(self, user_id: str) -> List[Dict]:
        """Get all sessions for a user"""
        return [
            s.to_dict() for s in self.sessions.values()
            if s.requester_user_id == user_id
        ]

    def get_statistics(self) -> Dict[str, Any]:
        """Get firefighter usage statistics"""
        total_sessions = len(self.sessions)
        active = sum(1 for s in self.sessions.values() if s.status == SessionStatus.ACTIVE)
        completed = sum(1 for s in self.sessions.values() if s.status == SessionStatus.COMPLETED)
        revoked = sum(1 for s in self.sessions.values() if s.status == SessionStatus.REVOKED)

        return {
            'total_requests': len(self.requests),
            'pending_requests': sum(1 for r in self.requests.values()
                                   if r.status == SessionStatus.PENDING_APPROVAL),
            'total_sessions': total_sessions,
            'active_sessions': active,
            'completed_sessions': completed,
            'revoked_sessions': revoked,
            'pending_reviews': sum(1 for s in self.sessions.values()
                                  if s.requires_review and s.reviewed_by is None)
        }
