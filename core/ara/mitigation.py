# Mitigation Control Management
# Compensating controls and risk acceptance for GOVERNEX+

"""
Mitigation Control Management for Access Risk Analysis.

Provides:
- Mitigation control definitions
- Control assignment to risks
- Control effectiveness tracking
- Risk acceptance workflow
- Exception management
"""

from typing import List, Optional, Dict, Any, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from uuid import uuid4
import logging

from .models import Risk, RiskSeverity, RiskStatus

logger = logging.getLogger(__name__)


class ControlType(Enum):
    """Type of mitigating control."""
    PREVENTIVE = "preventive"      # Prevents risk from occurring
    DETECTIVE = "detective"        # Detects risk occurrence
    CORRECTIVE = "corrective"      # Corrects after occurrence
    COMPENSATING = "compensating"  # Compensates for risk


class ControlStatus(Enum):
    """Control status."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"
    EXPIRED = "expired"


class ExceptionStatus(Enum):
    """Risk exception status."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    REVOKED = "revoked"


@dataclass
class MitigationControl:
    """
    Mitigating control definition.

    Represents a compensating control that reduces risk.
    """
    control_id: str = field(default_factory=lambda: f"CTL_{str(uuid4())[:8]}")
    name: str = ""
    description: str = ""
    control_type: ControlType = ControlType.COMPENSATING

    # Control details
    business_process: str = ""
    control_owner: str = ""
    control_executor: str = ""

    # Effectiveness
    risk_reduction_percent: int = 20  # How much risk is reduced
    effectiveness_rating: str = "medium"  # low, medium, high

    # Frequency
    frequency: str = "continuous"  # continuous, daily, weekly, monthly, quarterly
    last_executed: Optional[datetime] = None
    next_due: Optional[datetime] = None

    # Status
    status: ControlStatus = ControlStatus.ACTIVE
    valid_from: datetime = field(default_factory=datetime.now)
    valid_to: Optional[datetime] = None

    # Audit
    created_at: datetime = field(default_factory=datetime.now)
    created_by: str = ""
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None

    # Linked risks
    applicable_risk_types: List[str] = field(default_factory=list)
    applicable_rule_ids: List[str] = field(default_factory=list)

    def is_active(self) -> bool:
        """Check if control is currently active."""
        if self.status != ControlStatus.ACTIVE:
            return False

        now = datetime.now()
        if self.valid_from and now < self.valid_from:
            return False
        if self.valid_to and now > self.valid_to:
            return False

        return True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "control_id": self.control_id,
            "name": self.name,
            "description": self.description,
            "control_type": self.control_type.value,
            "business_process": self.business_process,
            "control_owner": self.control_owner,
            "risk_reduction_percent": self.risk_reduction_percent,
            "effectiveness_rating": self.effectiveness_rating,
            "frequency": self.frequency,
            "status": self.status.value,
            "valid_from": self.valid_from.isoformat() if self.valid_from else None,
            "valid_to": self.valid_to.isoformat() if self.valid_to else None,
            "is_active": self.is_active(),
        }


@dataclass
class ControlAssignment:
    """Assignment of a control to a risk."""
    assignment_id: str = field(default_factory=lambda: f"ASN_{str(uuid4())[:8]}")
    control_id: str = ""
    risk_id: str = ""
    user_id: Optional[str] = None

    # Assignment details
    assigned_at: datetime = field(default_factory=datetime.now)
    assigned_by: str = ""
    justification: str = ""

    # Effectiveness
    effectiveness_override: Optional[int] = None  # Override default effectiveness

    # Status
    is_active: bool = True
    deactivated_at: Optional[datetime] = None
    deactivated_by: Optional[str] = None
    deactivation_reason: Optional[str] = None


@dataclass
class RiskException:
    """
    Risk exception/acceptance record.

    Formal acceptance of a risk without mitigation.
    """
    exception_id: str = field(default_factory=lambda: f"EXC_{str(uuid4())[:8]}")
    risk_id: str = ""
    user_id: Optional[str] = None

    # Exception details
    status: ExceptionStatus = ExceptionStatus.PENDING
    justification: str = ""
    business_reason: str = ""

    # Approval
    requested_by: str = ""
    requested_at: datetime = field(default_factory=datetime.now)
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None

    # Validity
    valid_from: Optional[datetime] = None
    valid_to: Optional[datetime] = None
    auto_expire: bool = True

    # Review
    requires_periodic_review: bool = True
    review_frequency_days: int = 90
    last_review: Optional[datetime] = None
    next_review: Optional[datetime] = None

    def is_valid(self) -> bool:
        """Check if exception is currently valid."""
        if self.status != ExceptionStatus.APPROVED:
            return False

        now = datetime.now()
        if self.valid_from and now < self.valid_from:
            return False
        if self.valid_to and now > self.valid_to:
            return False

        return True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "exception_id": self.exception_id,
            "risk_id": self.risk_id,
            "user_id": self.user_id,
            "status": self.status.value,
            "justification": self.justification,
            "business_reason": self.business_reason,
            "requested_by": self.requested_by,
            "requested_at": self.requested_at.isoformat(),
            "approved_by": self.approved_by,
            "valid_from": self.valid_from.isoformat() if self.valid_from else None,
            "valid_to": self.valid_to.isoformat() if self.valid_to else None,
            "is_valid": self.is_valid(),
            "next_review": self.next_review.isoformat() if self.next_review else None,
        }


class MitigationManager:
    """
    Manager for mitigation controls and risk exceptions.

    Handles control lifecycle and risk acceptance workflow.
    """

    def __init__(self):
        # Storage (in production, use database)
        self.controls: Dict[str, MitigationControl] = {}
        self.assignments: Dict[str, ControlAssignment] = {}
        self.exceptions: Dict[str, RiskException] = {}

        # Index by risk
        self.risk_assignments: Dict[str, List[str]] = {}  # risk_id -> assignment_ids
        self.risk_exceptions: Dict[str, str] = {}  # risk_id -> exception_id

        # Load default controls
        self._load_default_controls()

    def create_control(self, control: MitigationControl) -> MitigationControl:
        """Create a new mitigation control."""
        self.controls[control.control_id] = control
        logger.info(f"Created control: {control.control_id} - {control.name}")
        return control

    def get_control(self, control_id: str) -> Optional[MitigationControl]:
        """Get a control by ID."""
        return self.controls.get(control_id)

    def list_controls(
        self,
        control_type: Optional[ControlType] = None,
        status: Optional[ControlStatus] = None,
        active_only: bool = True
    ) -> List[MitigationControl]:
        """List controls with optional filtering."""
        result = []

        for control in self.controls.values():
            if active_only and not control.is_active():
                continue
            if control_type and control.control_type != control_type:
                continue
            if status and control.status != status:
                continue

            result.append(control)

        return result

    def assign_control(
        self,
        control_id: str,
        risk_id: str,
        assigned_by: str,
        justification: str = "",
        user_id: Optional[str] = None
    ) -> Optional[ControlAssignment]:
        """
        Assign a control to mitigate a risk.

        Args:
            control_id: Control to assign
            risk_id: Risk to mitigate
            assigned_by: User making assignment
            justification: Reason for assignment
            user_id: Optional user scope

        Returns:
            ControlAssignment if successful
        """
        control = self.get_control(control_id)
        if not control:
            logger.warning(f"Control not found: {control_id}")
            return None

        if not control.is_active():
            logger.warning(f"Control not active: {control_id}")
            return None

        assignment = ControlAssignment(
            control_id=control_id,
            risk_id=risk_id,
            user_id=user_id,
            assigned_by=assigned_by,
            justification=justification,
        )

        self.assignments[assignment.assignment_id] = assignment

        # Index
        if risk_id not in self.risk_assignments:
            self.risk_assignments[risk_id] = []
        self.risk_assignments[risk_id].append(assignment.assignment_id)

        logger.info(f"Assigned control {control_id} to risk {risk_id}")
        return assignment

    def get_risk_mitigations(self, risk_id: str) -> List[Dict[str, Any]]:
        """
        Get all mitigations for a risk.

        Returns controls and their effectiveness.
        """
        mitigations = []

        assignment_ids = self.risk_assignments.get(risk_id, [])
        for aid in assignment_ids:
            assignment = self.assignments.get(aid)
            if not assignment or not assignment.is_active:
                continue

            control = self.get_control(assignment.control_id)
            if not control or not control.is_active():
                continue

            effectiveness = (
                assignment.effectiveness_override
                if assignment.effectiveness_override is not None
                else control.risk_reduction_percent
            )

            mitigations.append({
                "assignment_id": assignment.assignment_id,
                "control_id": control.control_id,
                "control_name": control.name,
                "control_type": control.control_type.value,
                "risk_reduction_percent": effectiveness,
                "effectiveness_rating": control.effectiveness_rating,
            })

        return mitigations

    def calculate_mitigated_score(
        self,
        risk: Risk
    ) -> int:
        """
        Calculate risk score after applying mitigations.

        Args:
            risk: Risk to calculate

        Returns:
            Mitigated risk score
        """
        mitigations = self.get_risk_mitigations(risk.risk_id)

        if not mitigations:
            return risk.final_score

        # Apply mitigations (diminishing returns for multiple controls)
        remaining_risk = risk.final_score

        for i, mitigation in enumerate(mitigations):
            reduction = mitigation["risk_reduction_percent"]

            # Diminishing returns for subsequent controls
            if i > 0:
                reduction = reduction * 0.7  # 30% less effective

            remaining_risk = remaining_risk * (1 - reduction / 100)

        return max(0, int(remaining_risk))

    def request_exception(
        self,
        risk_id: str,
        requested_by: str,
        justification: str,
        business_reason: str,
        valid_days: int = 90,
        user_id: Optional[str] = None
    ) -> RiskException:
        """
        Request a risk exception (acceptance).

        Args:
            risk_id: Risk to accept
            requested_by: User requesting exception
            justification: Technical justification
            business_reason: Business justification
            valid_days: How long exception is valid
            user_id: Optional user scope

        Returns:
            Created exception request
        """
        exception = RiskException(
            risk_id=risk_id,
            user_id=user_id,
            status=ExceptionStatus.PENDING,
            justification=justification,
            business_reason=business_reason,
            requested_by=requested_by,
            valid_from=datetime.now(),
            valid_to=datetime.now() + timedelta(days=valid_days),
        )

        # Set review date
        exception.next_review = datetime.now() + timedelta(
            days=exception.review_frequency_days
        )

        self.exceptions[exception.exception_id] = exception
        logger.info(f"Exception requested for risk {risk_id}: {exception.exception_id}")

        return exception

    def approve_exception(
        self,
        exception_id: str,
        approved_by: str,
        valid_days: Optional[int] = None
    ) -> Optional[RiskException]:
        """
        Approve a risk exception.

        Args:
            exception_id: Exception to approve
            approved_by: Approver user ID
            valid_days: Override validity period

        Returns:
            Updated exception if successful
        """
        exception = self.exceptions.get(exception_id)
        if not exception:
            return None

        if exception.status != ExceptionStatus.PENDING:
            logger.warning(f"Exception {exception_id} not pending")
            return None

        exception.status = ExceptionStatus.APPROVED
        exception.approved_by = approved_by
        exception.approved_at = datetime.now()

        if valid_days:
            exception.valid_to = datetime.now() + timedelta(days=valid_days)

        # Index
        self.risk_exceptions[exception.risk_id] = exception.exception_id

        logger.info(f"Exception {exception_id} approved by {approved_by}")
        return exception

    def reject_exception(
        self,
        exception_id: str,
        rejected_by: str,
        reason: str
    ) -> Optional[RiskException]:
        """Reject a risk exception request."""
        exception = self.exceptions.get(exception_id)
        if not exception:
            return None

        exception.status = ExceptionStatus.REJECTED
        exception.rejection_reason = reason
        exception.approved_by = rejected_by  # Store who rejected
        exception.approved_at = datetime.now()

        logger.info(f"Exception {exception_id} rejected by {rejected_by}")
        return exception

    def get_risk_exception(self, risk_id: str) -> Optional[RiskException]:
        """Get active exception for a risk."""
        exception_id = self.risk_exceptions.get(risk_id)
        if not exception_id:
            return None

        exception = self.exceptions.get(exception_id)
        if exception and exception.is_valid():
            return exception

        return None

    def check_expiring_exceptions(
        self,
        days_ahead: int = 30
    ) -> List[RiskException]:
        """Find exceptions expiring soon."""
        cutoff = datetime.now() + timedelta(days=days_ahead)

        expiring = []
        for exception in self.exceptions.values():
            if exception.status == ExceptionStatus.APPROVED:
                if exception.valid_to and exception.valid_to <= cutoff:
                    expiring.append(exception)

        return expiring

    def check_review_due(self) -> List[RiskException]:
        """Find exceptions needing review."""
        now = datetime.now()

        due_for_review = []
        for exception in self.exceptions.values():
            if exception.status == ExceptionStatus.APPROVED:
                if exception.next_review and exception.next_review <= now:
                    due_for_review.append(exception)

        return due_for_review

    def update_risk_status(self, risk: Risk) -> Risk:
        """
        Update risk status based on mitigations and exceptions.

        Args:
            risk: Risk to update

        Returns:
            Updated risk
        """
        # Check for active exception
        exception = self.get_risk_exception(risk.risk_id)
        if exception and exception.is_valid():
            risk.status = RiskStatus.ACCEPTED
            risk.mitigation_status = "accepted"
            return risk

        # Check for active mitigations
        mitigations = self.get_risk_mitigations(risk.risk_id)
        if mitigations:
            risk.status = RiskStatus.MITIGATED
            risk.mitigation_status = "mitigated"
            risk.mitigation_id = mitigations[0]["control_id"]
            return risk

        # No mitigation
        risk.status = RiskStatus.OPEN
        risk.mitigation_status = None
        risk.mitigation_id = None

        return risk

    def get_control_effectiveness_report(self) -> Dict[str, Any]:
        """Generate control effectiveness report."""
        report = {
            "total_controls": len(self.controls),
            "active_controls": len([c for c in self.controls.values() if c.is_active()]),
            "total_assignments": len(self.assignments),
            "active_assignments": len([a for a in self.assignments.values() if a.is_active]),
            "by_type": {},
            "by_effectiveness": {},
        }

        for control in self.controls.values():
            ctype = control.control_type.value
            report["by_type"][ctype] = report["by_type"].get(ctype, 0) + 1

            eff = control.effectiveness_rating
            report["by_effectiveness"][eff] = report["by_effectiveness"].get(eff, 0) + 1

        return report

    def _load_default_controls(self):
        """Load default mitigation controls."""
        default_controls = [
            MitigationControl(
                control_id="CTL_DUAL_APPROVAL",
                name="Dual Approval for Sensitive Transactions",
                description="Requires two-person approval for sensitive financial transactions",
                control_type=ControlType.PREVENTIVE,
                business_process="Finance",
                risk_reduction_percent=40,
                effectiveness_rating="high",
                frequency="continuous",
                applicable_risk_types=["sod_conflict", "sensitive_access"],
            ),
            MitigationControl(
                control_id="CTL_TRANSACTION_LOG",
                name="Transaction Log Review",
                description="Daily review of sensitive transaction logs by supervisor",
                control_type=ControlType.DETECTIVE,
                business_process="All",
                risk_reduction_percent=25,
                effectiveness_rating="medium",
                frequency="daily",
                applicable_risk_types=["sod_conflict", "behavioral_anomaly"],
            ),
            MitigationControl(
                control_id="CTL_PERIODIC_CERT",
                name="Periodic Access Certification",
                description="Quarterly review and certification of access rights",
                control_type=ControlType.DETECTIVE,
                business_process="All",
                risk_reduction_percent=20,
                effectiveness_rating="medium",
                frequency="quarterly",
                applicable_risk_types=["excessive_access", "unused_access"],
            ),
            MitigationControl(
                control_id="CTL_RECONCILIATION",
                name="Daily Reconciliation",
                description="Daily reconciliation of key accounts",
                control_type=ControlType.DETECTIVE,
                business_process="Finance",
                risk_reduction_percent=35,
                effectiveness_rating="high",
                frequency="daily",
                applicable_risk_types=["sod_conflict"],
            ),
            MitigationControl(
                control_id="CTL_AUDIT_TRAIL",
                name="Enhanced Audit Trail Monitoring",
                description="Real-time monitoring of audit trail for suspicious activity",
                control_type=ControlType.DETECTIVE,
                business_process="IT Security",
                risk_reduction_percent=30,
                effectiveness_rating="high",
                frequency="continuous",
                applicable_risk_types=["sensitive_access", "privileged_access"],
            ),
        ]

        for control in default_controls:
            self.create_control(control)

        logger.info(f"Loaded {len(default_controls)} default mitigation controls")
