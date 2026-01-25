"""
Mitigation Controls Module

Provides comprehensive management of compensating controls
for SoD violations and risk mitigation.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Any, Tuple
from datetime import datetime, timedelta
from enum import Enum
import uuid


class ControlType(Enum):
    """Types of mitigation controls"""
    DETECTIVE = "detective"          # Detects issues after they occur
    PREVENTIVE = "preventive"        # Prevents issues from occurring
    CORRECTIVE = "corrective"        # Corrects issues after detection
    MONITORING = "monitoring"        # Continuous monitoring
    REVIEW = "review"               # Periodic review
    APPROVAL = "approval"           # Approval-based control
    AUTOMATED = "automated"         # System-enforced control


class ControlStatus(Enum):
    """Control lifecycle status"""
    DRAFT = "draft"
    ACTIVE = "active"
    UNDER_REVIEW = "under_review"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"


class EffectivenessRating(Enum):
    """Control effectiveness ratings"""
    HIGHLY_EFFECTIVE = "highly_effective"     # 90-100%
    EFFECTIVE = "effective"                    # 70-89%
    PARTIALLY_EFFECTIVE = "partially_effective" # 50-69%
    INEFFECTIVE = "ineffective"                # Below 50%
    NOT_TESTED = "not_tested"


class AssignmentStatus(Enum):
    """Control assignment status"""
    ACTIVE = "active"
    PENDING_APPROVAL = "pending_approval"
    EXPIRED = "expired"
    REVOKED = "revoked"
    UNDER_REVIEW = "under_review"


@dataclass
class ControlEffectiveness:
    """Effectiveness metrics for a control"""
    effectiveness_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    control_id: str = ""
    rating: EffectivenessRating = EffectivenessRating.NOT_TESTED
    score: float = 0.0  # 0-100
    test_date: datetime = field(default_factory=datetime.now)
    tested_by: str = ""
    test_method: str = ""
    findings: List[str] = field(default_factory=list)
    evidence_references: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    next_test_date: Optional[datetime] = None

    def to_dict(self) -> Dict:
        return {
            "effectiveness_id": self.effectiveness_id,
            "control_id": self.control_id,
            "rating": self.rating.value,
            "score": self.score,
            "test_date": self.test_date.isoformat(),
            "tested_by": self.tested_by,
            "test_method": self.test_method,
            "findings": self.findings,
            "evidence_references": self.evidence_references,
            "recommendations": self.recommendations,
            "next_test_date": self.next_test_date.isoformat() if self.next_test_date else None
        }


@dataclass
class ControlAttestation:
    """Attestation record for a control"""
    attestation_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    control_id: str = ""
    assignment_id: str = ""
    attester_id: str = ""
    attester_name: str = ""
    attestation_date: datetime = field(default_factory=datetime.now)
    status: str = "attested"  # attested, declined, delegated
    comments: str = ""
    evidence_attached: bool = False
    evidence_description: str = ""
    valid_until: Optional[datetime] = None

    def to_dict(self) -> Dict:
        return {
            "attestation_id": self.attestation_id,
            "control_id": self.control_id,
            "assignment_id": self.assignment_id,
            "attester_id": self.attester_id,
            "attester_name": self.attester_name,
            "attestation_date": self.attestation_date.isoformat(),
            "status": self.status,
            "comments": self.comments,
            "evidence_attached": self.evidence_attached,
            "evidence_description": self.evidence_description,
            "valid_until": self.valid_until.isoformat() if self.valid_until else None
        }


@dataclass
class MitigationControl:
    """A mitigation control definition"""
    control_id: str = field(default_factory=lambda: f"MC_{str(uuid.uuid4())[:8].upper()}")
    name: str = ""
    description: str = ""
    control_type: ControlType = ControlType.DETECTIVE
    status: ControlStatus = ControlStatus.DRAFT

    # Risk linkage
    mitigated_risk_ids: List[str] = field(default_factory=list)  # SoD rule IDs this mitigates
    risk_reduction_percentage: float = 0.0  # How much risk is reduced (0-100)

    # Control details
    control_objective: str = ""
    control_activity: str = ""
    frequency: str = ""  # daily, weekly, monthly, quarterly, annually, continuous
    responsible_role: str = ""
    owner_id: str = ""
    owner_name: str = ""

    # Implementation
    implementation_details: str = ""
    automation_level: str = "manual"  # manual, semi-automated, fully-automated
    system_id: str = ""  # System where control is implemented
    technical_implementation: Dict[str, Any] = field(default_factory=dict)

    # Documentation
    documentation_url: str = ""
    evidence_requirements: List[str] = field(default_factory=list)
    test_procedures: List[str] = field(default_factory=list)

    # Compliance mapping
    compliance_frameworks: List[str] = field(default_factory=list)  # SOX, GDPR, etc.
    control_objectives: List[str] = field(default_factory=list)

    # Effectiveness tracking
    current_effectiveness: Optional[ControlEffectiveness] = None
    effectiveness_history: List[ControlEffectiveness] = field(default_factory=list)

    # Lifecycle
    created_at: datetime = field(default_factory=datetime.now)
    created_by: str = ""
    modified_at: datetime = field(default_factory=datetime.now)
    modified_by: str = ""
    approved_at: Optional[datetime] = None
    approved_by: str = ""
    valid_from: Optional[datetime] = None
    valid_to: Optional[datetime] = None

    # Metadata
    tags: List[str] = field(default_factory=list)
    category: str = ""

    def to_dict(self) -> Dict:
        return {
            "control_id": self.control_id,
            "name": self.name,
            "description": self.description,
            "control_type": self.control_type.value,
            "status": self.status.value,
            "mitigated_risk_ids": self.mitigated_risk_ids,
            "risk_reduction_percentage": self.risk_reduction_percentage,
            "control_objective": self.control_objective,
            "control_activity": self.control_activity,
            "frequency": self.frequency,
            "responsible_role": self.responsible_role,
            "owner_id": self.owner_id,
            "owner_name": self.owner_name,
            "implementation_details": self.implementation_details,
            "automation_level": self.automation_level,
            "system_id": self.system_id,
            "technical_implementation": self.technical_implementation,
            "documentation_url": self.documentation_url,
            "evidence_requirements": self.evidence_requirements,
            "test_procedures": self.test_procedures,
            "compliance_frameworks": self.compliance_frameworks,
            "control_objectives": self.control_objectives,
            "current_effectiveness": self.current_effectiveness.to_dict() if self.current_effectiveness else None,
            "created_at": self.created_at.isoformat(),
            "created_by": self.created_by,
            "modified_at": self.modified_at.isoformat(),
            "modified_by": self.modified_by,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "approved_by": self.approved_by,
            "valid_from": self.valid_from.isoformat() if self.valid_from else None,
            "valid_to": self.valid_to.isoformat() if self.valid_to else None,
            "tags": self.tags,
            "category": self.category
        }


@dataclass
class ControlAssignment:
    """Assignment of a control to mitigate a specific risk for a user/role"""
    assignment_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    control_id: str = ""
    risk_id: str = ""  # The specific SoD rule/risk being mitigated

    # Target
    target_type: str = ""  # user, role, org_unit
    target_id: str = ""
    target_name: str = ""

    # Assignment details
    status: AssignmentStatus = AssignmentStatus.ACTIVE
    assigned_at: datetime = field(default_factory=datetime.now)
    assigned_by: str = ""
    valid_from: datetime = field(default_factory=datetime.now)
    valid_to: Optional[datetime] = None
    justification: str = ""

    # Approval
    requires_approval: bool = True
    approved_at: Optional[datetime] = None
    approved_by: str = ""
    approval_comments: str = ""

    # Monitoring
    monitor_id: str = ""  # Person responsible for monitoring
    monitor_name: str = ""
    last_monitored: Optional[datetime] = None
    monitoring_frequency: str = "quarterly"

    # Attestation
    attestations: List[ControlAttestation] = field(default_factory=list)
    last_attestation: Optional[datetime] = None
    next_attestation_due: Optional[datetime] = None
    attestation_frequency_days: int = 90

    # Effectiveness at assignment level
    is_effective: bool = True
    effectiveness_notes: str = ""

    def to_dict(self) -> Dict:
        return {
            "assignment_id": self.assignment_id,
            "control_id": self.control_id,
            "risk_id": self.risk_id,
            "target_type": self.target_type,
            "target_id": self.target_id,
            "target_name": self.target_name,
            "status": self.status.value,
            "assigned_at": self.assigned_at.isoformat(),
            "assigned_by": self.assigned_by,
            "valid_from": self.valid_from.isoformat(),
            "valid_to": self.valid_to.isoformat() if self.valid_to else None,
            "justification": self.justification,
            "requires_approval": self.requires_approval,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "approved_by": self.approved_by,
            "approval_comments": self.approval_comments,
            "monitor_id": self.monitor_id,
            "monitor_name": self.monitor_name,
            "last_monitored": self.last_monitored.isoformat() if self.last_monitored else None,
            "monitoring_frequency": self.monitoring_frequency,
            "attestations": [a.to_dict() for a in self.attestations],
            "last_attestation": self.last_attestation.isoformat() if self.last_attestation else None,
            "next_attestation_due": self.next_attestation_due.isoformat() if self.next_attestation_due else None,
            "attestation_frequency_days": self.attestation_frequency_days,
            "is_effective": self.is_effective,
            "effectiveness_notes": self.effectiveness_notes
        }


class MitigationManager:
    """
    Mitigation Controls Manager.

    Manages compensating controls for SoD violations and risk mitigation.
    Provides:
    - Control definition and lifecycle management
    - Control assignment to users/roles
    - Effectiveness tracking and testing
    - Attestation workflows
    - Compliance monitoring
    """

    # Standard control templates
    CONTROL_TEMPLATES = [
        {
            "name": "Manager Review of Transactions",
            "type": ControlType.REVIEW,
            "description": "Manager reviews all transactions executed by user",
            "frequency": "daily",
            "evidence": ["Review log", "Manager sign-off", "Exception report"],
            "effectiveness": 75
        },
        {
            "name": "Dual Approval Requirement",
            "type": ControlType.APPROVAL,
            "description": "Second approval required for high-value transactions",
            "frequency": "per_transaction",
            "evidence": ["Approval records", "Workflow logs"],
            "effectiveness": 90
        },
        {
            "name": "Automated Monitoring Report",
            "type": ControlType.MONITORING,
            "description": "Automated report of conflicting activities",
            "frequency": "daily",
            "evidence": ["Automated report", "Exception analysis"],
            "effectiveness": 80
        },
        {
            "name": "Periodic Access Review",
            "type": ControlType.DETECTIVE,
            "description": "Quarterly review of user access rights",
            "frequency": "quarterly",
            "evidence": ["Review records", "Certification results"],
            "effectiveness": 70
        },
        {
            "name": "Transaction Limit Control",
            "type": ControlType.PREVENTIVE,
            "description": "System-enforced limits on transaction values",
            "frequency": "continuous",
            "evidence": ["System configuration", "Limit exception log"],
            "effectiveness": 95
        },
        {
            "name": "Reconciliation Control",
            "type": ControlType.DETECTIVE,
            "description": "Regular reconciliation of related records",
            "frequency": "monthly",
            "evidence": ["Reconciliation report", "Variance analysis"],
            "effectiveness": 85
        }
    ]

    # Standard risk-control mappings
    STANDARD_MAPPINGS = {
        "SOD001": ["Manager Review of Transactions", "Dual Approval Requirement"],
        "SOD002": ["Reconciliation Control", "Automated Monitoring Report"],
        "SOD003": ["Automated Monitoring Report", "Manager Review of Transactions"],
        "SOD004": ["Periodic Access Review", "Manager Review of Transactions"],
        "SOD005": ["Dual Approval Requirement", "Periodic Access Review"],
    }

    def __init__(self):
        self.controls: Dict[str, MitigationControl] = {}
        self.assignments: Dict[str, ControlAssignment] = {}
        self.user_assignments: Dict[str, List[str]] = {}  # user_id -> [assignment_ids]
        self.risk_assignments: Dict[str, List[str]] = {}  # risk_id -> [assignment_ids]
        self._initialize_standard_controls()

    def _initialize_standard_controls(self):
        """Initialize standard mitigation controls"""
        for template in self.CONTROL_TEMPLATES:
            control = MitigationControl(
                name=template["name"],
                description=template["description"],
                control_type=template["type"],
                frequency=template["frequency"],
                evidence_requirements=template["evidence"],
                risk_reduction_percentage=template["effectiveness"],
                status=ControlStatus.ACTIVE,
                created_by="SYSTEM"
            )
            self.controls[control.control_id] = control

    # =========================================================================
    # Control CRUD
    # =========================================================================

    def create_control(
        self,
        name: str,
        description: str,
        control_type: ControlType,
        created_by: str,
        **kwargs
    ) -> MitigationControl:
        """Create a new mitigation control"""
        control = MitigationControl(
            name=name,
            description=description,
            control_type=control_type,
            created_by=created_by,
            modified_by=created_by
        )

        for key, value in kwargs.items():
            if hasattr(control, key):
                setattr(control, key, value)

        self.controls[control.control_id] = control
        return control

    def update_control(
        self,
        control_id: str,
        modified_by: str,
        **updates
    ) -> MitigationControl:
        """Update a control"""
        if control_id not in self.controls:
            raise ValueError(f"Control {control_id} not found")

        control = self.controls[control_id]

        for key, value in updates.items():
            if hasattr(control, key) and key not in ['control_id', 'created_at', 'created_by']:
                setattr(control, key, value)

        control.modified_at = datetime.now()
        control.modified_by = modified_by

        return control

    def get_control(self, control_id: str) -> Optional[MitigationControl]:
        """Get a control by ID"""
        return self.controls.get(control_id)

    def list_controls(
        self,
        control_type: ControlType = None,
        status: ControlStatus = None,
        risk_id: str = None,
        category: str = None,
        search: str = None
    ) -> List[MitigationControl]:
        """List controls with filters"""
        controls = list(self.controls.values())

        if control_type:
            controls = [c for c in controls if c.control_type == control_type]
        if status:
            controls = [c for c in controls if c.status == status]
        if risk_id:
            controls = [c for c in controls if risk_id in c.mitigated_risk_ids]
        if category:
            controls = [c for c in controls if c.category == category]
        if search:
            search_lower = search.lower()
            controls = [c for c in controls if
                       search_lower in c.name.lower() or
                       search_lower in c.description.lower()]

        return controls

    def approve_control(
        self,
        control_id: str,
        approved_by: str
    ) -> MitigationControl:
        """Approve a control"""
        if control_id not in self.controls:
            raise ValueError(f"Control {control_id} not found")

        control = self.controls[control_id]
        control.status = ControlStatus.ACTIVE
        control.approved_at = datetime.now()
        control.approved_by = approved_by
        control.valid_from = datetime.now()

        return control

    def deprecate_control(
        self,
        control_id: str,
        deprecated_by: str,
        reason: str = ""
    ) -> MitigationControl:
        """Deprecate a control"""
        if control_id not in self.controls:
            raise ValueError(f"Control {control_id} not found")

        control = self.controls[control_id]
        control.status = ControlStatus.DEPRECATED
        control.valid_to = datetime.now()
        control.modified_at = datetime.now()
        control.modified_by = deprecated_by

        return control

    # =========================================================================
    # Control Assignment
    # =========================================================================

    def assign_control(
        self,
        control_id: str,
        risk_id: str,
        target_type: str,
        target_id: str,
        target_name: str,
        assigned_by: str,
        justification: str,
        valid_from: datetime = None,
        valid_to: datetime = None,
        monitor_id: str = "",
        monitor_name: str = "",
        requires_approval: bool = True
    ) -> ControlAssignment:
        """Assign a control to mitigate a specific risk for a target"""
        if control_id not in self.controls:
            raise ValueError(f"Control {control_id} not found")

        assignment = ControlAssignment(
            control_id=control_id,
            risk_id=risk_id,
            target_type=target_type,
            target_id=target_id,
            target_name=target_name,
            assigned_by=assigned_by,
            justification=justification,
            valid_from=valid_from or datetime.now(),
            valid_to=valid_to,
            monitor_id=monitor_id,
            monitor_name=monitor_name,
            requires_approval=requires_approval,
            status=AssignmentStatus.PENDING_APPROVAL if requires_approval else AssignmentStatus.ACTIVE
        )

        # Set attestation schedule
        assignment.next_attestation_due = datetime.now() + timedelta(
            days=assignment.attestation_frequency_days
        )

        self.assignments[assignment.assignment_id] = assignment

        # Track by target
        if target_type == "user":
            if target_id not in self.user_assignments:
                self.user_assignments[target_id] = []
            self.user_assignments[target_id].append(assignment.assignment_id)

        # Track by risk
        if risk_id not in self.risk_assignments:
            self.risk_assignments[risk_id] = []
        self.risk_assignments[risk_id].append(assignment.assignment_id)

        return assignment

    def approve_assignment(
        self,
        assignment_id: str,
        approved_by: str,
        comments: str = ""
    ) -> ControlAssignment:
        """Approve a control assignment"""
        if assignment_id not in self.assignments:
            raise ValueError(f"Assignment {assignment_id} not found")

        assignment = self.assignments[assignment_id]
        assignment.status = AssignmentStatus.ACTIVE
        assignment.approved_at = datetime.now()
        assignment.approved_by = approved_by
        assignment.approval_comments = comments

        return assignment

    def revoke_assignment(
        self,
        assignment_id: str,
        revoked_by: str,
        reason: str = ""
    ) -> ControlAssignment:
        """Revoke a control assignment"""
        if assignment_id not in self.assignments:
            raise ValueError(f"Assignment {assignment_id} not found")

        assignment = self.assignments[assignment_id]
        assignment.status = AssignmentStatus.REVOKED
        assignment.valid_to = datetime.now()
        assignment.effectiveness_notes = f"Revoked by {revoked_by}: {reason}"

        return assignment

    def get_user_assignments(
        self,
        user_id: str,
        include_expired: bool = False
    ) -> List[ControlAssignment]:
        """Get all control assignments for a user"""
        assignment_ids = self.user_assignments.get(user_id, [])
        assignments = [self.assignments[aid] for aid in assignment_ids]

        if not include_expired:
            now = datetime.now()
            assignments = [
                a for a in assignments
                if a.status == AssignmentStatus.ACTIVE and
                (a.valid_to is None or a.valid_to > now)
            ]

        return assignments

    def get_risk_mitigations(
        self,
        risk_id: str,
        include_expired: bool = False
    ) -> List[Dict]:
        """Get all mitigation controls for a specific risk"""
        assignment_ids = self.risk_assignments.get(risk_id, [])
        assignments = [self.assignments[aid] for aid in assignment_ids]

        if not include_expired:
            now = datetime.now()
            assignments = [
                a for a in assignments
                if a.status == AssignmentStatus.ACTIVE and
                (a.valid_to is None or a.valid_to > now)
            ]

        results = []
        for assignment in assignments:
            control = self.controls.get(assignment.control_id)
            if control:
                results.append({
                    "assignment": assignment.to_dict(),
                    "control": control.to_dict()
                })

        return results

    def is_risk_mitigated(
        self,
        risk_id: str,
        target_id: str,
        target_type: str = "user"
    ) -> Dict:
        """Check if a risk is mitigated for a target"""
        assignment_ids = self.risk_assignments.get(risk_id, [])

        active_assignments = []
        for aid in assignment_ids:
            assignment = self.assignments.get(aid)
            if (assignment and
                assignment.target_id == target_id and
                assignment.target_type == target_type and
                assignment.status == AssignmentStatus.ACTIVE):

                # Check if not expired
                if assignment.valid_to is None or assignment.valid_to > datetime.now():
                    active_assignments.append(assignment)

        is_mitigated = len(active_assignments) > 0

        # Calculate total risk reduction
        total_reduction = 0.0
        if is_mitigated:
            for assignment in active_assignments:
                control = self.controls.get(assignment.control_id)
                if control:
                    total_reduction = min(100, total_reduction + control.risk_reduction_percentage)

        return {
            "is_mitigated": is_mitigated,
            "risk_id": risk_id,
            "target_id": target_id,
            "active_controls": len(active_assignments),
            "risk_reduction_percentage": total_reduction,
            "assignments": [a.to_dict() for a in active_assignments]
        }

    # =========================================================================
    # Effectiveness Testing
    # =========================================================================

    def record_effectiveness_test(
        self,
        control_id: str,
        tested_by: str,
        score: float,
        test_method: str,
        findings: List[str] = None,
        evidence_references: List[str] = None,
        recommendations: List[str] = None
    ) -> ControlEffectiveness:
        """Record an effectiveness test for a control"""
        if control_id not in self.controls:
            raise ValueError(f"Control {control_id} not found")

        control = self.controls[control_id]

        # Determine rating from score
        if score >= 90:
            rating = EffectivenessRating.HIGHLY_EFFECTIVE
        elif score >= 70:
            rating = EffectivenessRating.EFFECTIVE
        elif score >= 50:
            rating = EffectivenessRating.PARTIALLY_EFFECTIVE
        else:
            rating = EffectivenessRating.INEFFECTIVE

        effectiveness = ControlEffectiveness(
            control_id=control_id,
            rating=rating,
            score=score,
            tested_by=tested_by,
            test_method=test_method,
            findings=findings or [],
            evidence_references=evidence_references or [],
            recommendations=recommendations or [],
            next_test_date=datetime.now() + timedelta(days=90)  # Default quarterly
        )

        # Update control
        if control.current_effectiveness:
            control.effectiveness_history.append(control.current_effectiveness)
        control.current_effectiveness = effectiveness

        return effectiveness

    def get_effectiveness_trend(
        self,
        control_id: str
    ) -> Dict:
        """Get effectiveness trend for a control"""
        if control_id not in self.controls:
            raise ValueError(f"Control {control_id} not found")

        control = self.controls[control_id]
        history = control.effectiveness_history.copy()
        if control.current_effectiveness:
            history.append(control.current_effectiveness)

        if not history:
            return {
                "control_id": control_id,
                "trend": "no_data",
                "data_points": []
            }

        data_points = [
            {
                "date": e.test_date.isoformat(),
                "score": e.score,
                "rating": e.rating.value
            }
            for e in history
        ]

        # Calculate trend
        if len(history) >= 2:
            recent_avg = sum(e.score for e in history[-3:]) / min(3, len(history))
            older_avg = sum(e.score for e in history[:-3]) / max(1, len(history) - 3) if len(history) > 3 else recent_avg

            if recent_avg > older_avg + 5:
                trend = "improving"
            elif recent_avg < older_avg - 5:
                trend = "declining"
            else:
                trend = "stable"
        else:
            trend = "insufficient_data"

        return {
            "control_id": control_id,
            "trend": trend,
            "current_score": control.current_effectiveness.score if control.current_effectiveness else None,
            "current_rating": control.current_effectiveness.rating.value if control.current_effectiveness else None,
            "data_points": data_points
        }

    # =========================================================================
    # Attestation
    # =========================================================================

    def create_attestation(
        self,
        assignment_id: str,
        attester_id: str,
        attester_name: str,
        status: str = "attested",
        comments: str = "",
        evidence_attached: bool = False,
        evidence_description: str = ""
    ) -> ControlAttestation:
        """Create an attestation for a control assignment"""
        if assignment_id not in self.assignments:
            raise ValueError(f"Assignment {assignment_id} not found")

        assignment = self.assignments[assignment_id]

        attestation = ControlAttestation(
            control_id=assignment.control_id,
            assignment_id=assignment_id,
            attester_id=attester_id,
            attester_name=attester_name,
            status=status,
            comments=comments,
            evidence_attached=evidence_attached,
            evidence_description=evidence_description,
            valid_until=datetime.now() + timedelta(days=assignment.attestation_frequency_days)
        )

        assignment.attestations.append(attestation)
        assignment.last_attestation = datetime.now()
        assignment.next_attestation_due = attestation.valid_until

        return attestation

    def get_pending_attestations(
        self,
        attester_id: str = None
    ) -> List[Dict]:
        """Get assignments needing attestation"""
        now = datetime.now()
        pending = []

        for assignment in self.assignments.values():
            if assignment.status != AssignmentStatus.ACTIVE:
                continue

            if assignment.next_attestation_due and assignment.next_attestation_due <= now:
                if attester_id and assignment.monitor_id != attester_id:
                    continue

                control = self.controls.get(assignment.control_id)
                pending.append({
                    "assignment": assignment.to_dict(),
                    "control_name": control.name if control else "Unknown",
                    "days_overdue": (now - assignment.next_attestation_due).days
                })

        return pending

    def get_attestation_summary(self) -> Dict:
        """Get attestation summary statistics"""
        now = datetime.now()
        total = 0
        current = 0
        overdue = 0
        upcoming = 0

        for assignment in self.assignments.values():
            if assignment.status != AssignmentStatus.ACTIVE:
                continue

            total += 1

            if assignment.next_attestation_due:
                if assignment.next_attestation_due <= now:
                    overdue += 1
                elif assignment.next_attestation_due <= now + timedelta(days=30):
                    upcoming += 1
                else:
                    current += 1
            else:
                current += 1

        return {
            "total_active_assignments": total,
            "current_attestations": current,
            "overdue_attestations": overdue,
            "upcoming_attestations": upcoming,
            "compliance_rate": round(current / total * 100, 1) if total > 0 else 100
        }

    # =========================================================================
    # Monitoring
    # =========================================================================

    def record_monitoring(
        self,
        assignment_id: str,
        monitored_by: str,
        is_effective: bool,
        notes: str = ""
    ) -> ControlAssignment:
        """Record monitoring activity for an assignment"""
        if assignment_id not in self.assignments:
            raise ValueError(f"Assignment {assignment_id} not found")

        assignment = self.assignments[assignment_id]
        assignment.last_monitored = datetime.now()
        assignment.is_effective = is_effective
        if notes:
            assignment.effectiveness_notes = notes

        return assignment

    def get_monitoring_schedule(self) -> List[Dict]:
        """Get upcoming monitoring schedule"""
        schedule = []

        for assignment in self.assignments.values():
            if assignment.status != AssignmentStatus.ACTIVE:
                continue

            # Determine next monitoring date based on frequency
            freq_days = {
                "daily": 1,
                "weekly": 7,
                "monthly": 30,
                "quarterly": 90
            }.get(assignment.monitoring_frequency, 90)

            last = assignment.last_monitored or assignment.assigned_at
            next_due = last + timedelta(days=freq_days)

            control = self.controls.get(assignment.control_id)
            schedule.append({
                "assignment_id": assignment.assignment_id,
                "control_name": control.name if control else "Unknown",
                "target_name": assignment.target_name,
                "monitor_name": assignment.monitor_name,
                "next_due": next_due.isoformat(),
                "frequency": assignment.monitoring_frequency
            })

        schedule.sort(key=lambda x: x["next_due"])
        return schedule

    # =========================================================================
    # Recommendations
    # =========================================================================

    def recommend_controls(
        self,
        risk_id: str
    ) -> List[Dict]:
        """Recommend controls for a specific risk"""
        recommendations = []

        # Check standard mappings
        standard_controls = self.STANDARD_MAPPINGS.get(risk_id, [])

        for control_name in standard_controls:
            # Find control by name
            control = next(
                (c for c in self.controls.values() if c.name == control_name),
                None
            )
            if control:
                recommendations.append({
                    "control_id": control.control_id,
                    "name": control.name,
                    "type": control.control_type.value,
                    "risk_reduction": control.risk_reduction_percentage,
                    "frequency": control.frequency,
                    "reason": "Standard recommended control for this risk type"
                })

        # Also recommend highly effective controls
        for control in self.controls.values():
            if (control.current_effectiveness and
                control.current_effectiveness.rating == EffectivenessRating.HIGHLY_EFFECTIVE and
                control.control_id not in [r["control_id"] for r in recommendations]):

                recommendations.append({
                    "control_id": control.control_id,
                    "name": control.name,
                    "type": control.control_type.value,
                    "risk_reduction": control.risk_reduction_percentage,
                    "frequency": control.frequency,
                    "reason": "Highly effective control"
                })

        return recommendations[:5]  # Top 5 recommendations

    # =========================================================================
    # Statistics & Reports
    # =========================================================================

    def get_statistics(self) -> Dict:
        """Get mitigation control statistics"""
        controls = list(self.controls.values())
        assignments = list(self.assignments.values())

        by_type = {}
        for ct in ControlType:
            by_type[ct.value] = len([c for c in controls if c.control_type == ct])

        by_status = {}
        for cs in ControlStatus:
            by_status[cs.value] = len([c for c in controls if c.status == cs])

        by_effectiveness = {}
        for er in EffectivenessRating:
            by_effectiveness[er.value] = len([
                c for c in controls
                if c.current_effectiveness and c.current_effectiveness.rating == er
            ])

        active_assignments = [a for a in assignments if a.status == AssignmentStatus.ACTIVE]

        return {
            "total_controls": len(controls),
            "by_type": by_type,
            "by_status": by_status,
            "by_effectiveness": by_effectiveness,
            "total_assignments": len(assignments),
            "active_assignments": len(active_assignments),
            "attestation_summary": self.get_attestation_summary(),
            "average_risk_reduction": round(
                sum(c.risk_reduction_percentage for c in controls) / len(controls), 1
            ) if controls else 0
        }

    def get_control_coverage_report(self) -> Dict:
        """Get report on risk coverage by controls"""
        # Collect all unique risks
        all_risks = set()
        for control in self.controls.values():
            all_risks.update(control.mitigated_risk_ids)
        for assignment in self.assignments.values():
            all_risks.add(assignment.risk_id)

        covered_risks = set()
        for assignment in self.assignments.values():
            if assignment.status == AssignmentStatus.ACTIVE:
                covered_risks.add(assignment.risk_id)

        return {
            "total_identified_risks": len(all_risks),
            "covered_risks": len(covered_risks),
            "uncovered_risks": len(all_risks - covered_risks),
            "coverage_percentage": round(len(covered_risks) / len(all_risks) * 100, 1) if all_risks else 100,
            "uncovered_risk_ids": list(all_risks - covered_risks)
        }
