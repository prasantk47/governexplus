# SLA and Escalation Manager
# Intelligent SLA tracking and automatic escalation

"""
SLA Manager for GOVERNEX+.

Provides:
- Dynamic SLA based on risk
- Automatic escalation
- Intelligent reminders
- SLA prediction
- Breach prevention

Key Principle:
MSMP: Static SLA, manual escalation
GOVERNEX+: Dynamic SLA, predictive escalation
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from enum import Enum
import logging

from .models import (
    Workflow, WorkflowStep, WorkflowStatus, StepStatus,
    ApproverTypeEnum, WorkflowConfig, EscalationConfig
)

logger = logging.getLogger(__name__)


class SLAStatus(Enum):
    """SLA status for a step or workflow."""
    ON_TRACK = "ON_TRACK"           # Within SLA
    WARNING = "WARNING"             # SLA at risk
    CRITICAL = "CRITICAL"           # Near breach
    BREACHED = "BREACHED"           # Past SLA
    ESCALATED = "ESCALATED"         # Escalation triggered
    COMPLETED = "COMPLETED"         # Step completed


class EscalationTrigger(Enum):
    """What triggered an escalation."""
    SLA_WARNING = "SLA_WARNING"
    SLA_BREACH = "SLA_BREACH"
    APPROVER_OOO = "APPROVER_OOO"
    APPROVER_UNRESPONSIVE = "APPROVER_UNRESPONSIVE"
    MANUAL = "MANUAL"
    PREDICTIVE = "PREDICTIVE"       # AI predicted delay


@dataclass
class SLACheck:
    """Result of an SLA check."""
    step_id: str
    status: SLAStatus
    elapsed_hours: float
    sla_hours: float
    remaining_hours: float
    percentage_used: float
    recommendation: str = ""
    escalation_needed: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_id": self.step_id,
            "status": self.status.value,
            "elapsed_hours": round(self.elapsed_hours, 2),
            "sla_hours": self.sla_hours,
            "remaining_hours": round(self.remaining_hours, 2),
            "percentage_used": round(self.percentage_used, 1),
            "recommendation": self.recommendation,
            "escalation_needed": self.escalation_needed,
        }


@dataclass
class EscalationAction:
    """An escalation action to take."""
    action_id: str = ""
    trigger: EscalationTrigger = EscalationTrigger.SLA_BREACH
    step_id: str = ""
    workflow_id: str = ""

    # Who
    from_approver_id: str = ""
    to_approver_id: str = ""
    to_approver_type: Optional[ApproverTypeEnum] = None

    # When
    triggered_at: datetime = field(default_factory=datetime.now)

    # Details
    reason: str = ""
    original_sla_hours: float = 0.0
    elapsed_hours: float = 0.0

    # Execution
    executed: bool = False
    executed_at: Optional[datetime] = None
    notification_sent: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action_id": self.action_id,
            "trigger": self.trigger.value,
            "step_id": self.step_id,
            "workflow_id": self.workflow_id,
            "from_approver": self.from_approver_id,
            "to_approver": self.to_approver_id,
            "to_approver_type": self.to_approver_type.value if self.to_approver_type else None,
            "triggered_at": self.triggered_at.isoformat(),
            "reason": self.reason,
            "elapsed_hours": round(self.elapsed_hours, 2),
            "executed": self.executed,
        }


@dataclass
class SLAConfig:
    """SLA configuration."""
    # Default SLAs by risk level
    sla_by_risk: Dict[str, float] = field(default_factory=lambda: {
        "LOW": 72.0,
        "MEDIUM": 48.0,
        "HIGH": 24.0,
        "CRITICAL": 8.0,
    })

    # Warning thresholds
    warning_threshold: float = 0.75   # Warn at 75% of SLA
    critical_threshold: float = 0.90  # Critical at 90% of SLA

    # Reminder configuration
    send_reminders: bool = True
    reminder_intervals_hours: List[float] = field(default_factory=lambda: [12.0, 6.0, 2.0])

    # Escalation configuration
    escalation_config: EscalationConfig = field(default_factory=EscalationConfig)

    # Business hours (optional)
    use_business_hours: bool = False
    business_start_hour: int = 8
    business_end_hour: int = 18
    exclude_weekends: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sla_by_risk": self.sla_by_risk,
            "warning_threshold": self.warning_threshold,
            "critical_threshold": self.critical_threshold,
            "send_reminders": self.send_reminders,
            "reminder_intervals": self.reminder_intervals_hours,
            "escalation": self.escalation_config.to_dict(),
            "business_hours": {
                "enabled": self.use_business_hours,
                "start": self.business_start_hour,
                "end": self.business_end_hour,
                "exclude_weekends": self.exclude_weekends,
            },
        }


class SLAManager:
    """
    Manages SLA tracking and escalation.

    Features:
    - Dynamic SLA calculation
    - Real-time status monitoring
    - Automatic escalation
    - Predictive escalation (AI-ready)
    """

    def __init__(self, config: Optional[SLAConfig] = None):
        """Initialize SLA manager."""
        self.config = config or SLAConfig()

        # Pending escalations
        self._pending_escalations: List[EscalationAction] = []

        # Escalation history
        self._escalation_history: List[EscalationAction] = []

        # Callbacks
        self._on_escalation: Optional[Callable[[EscalationAction], None]] = None
        self._on_reminder: Optional[Callable[[WorkflowStep, str], None]] = None
        self._on_breach: Optional[Callable[[WorkflowStep], None]] = None

    def check_step_sla(self, step: WorkflowStep) -> SLACheck:
        """
        Check SLA status for a workflow step.

        Args:
            step: The workflow step to check

        Returns:
            SLACheck with status and recommendations
        """
        # Calculate elapsed time
        start_time = step.activated_at or step.created_at
        elapsed = (datetime.now() - start_time).total_seconds() / 3600

        # Apply business hours if configured
        if self.config.use_business_hours:
            elapsed = self._calculate_business_hours(start_time, datetime.now())

        sla_hours = step.sla_hours
        remaining = max(0, sla_hours - elapsed)
        percentage = (elapsed / sla_hours * 100) if sla_hours > 0 else 100

        # Determine status
        if step.is_complete():
            status = SLAStatus.COMPLETED
            recommendation = "Step completed"
            escalation_needed = False
        elif percentage >= 100:
            status = SLAStatus.BREACHED
            recommendation = "SLA breached - immediate escalation required"
            escalation_needed = True
        elif percentage >= self.config.critical_threshold * 100:
            status = SLAStatus.CRITICAL
            recommendation = f"Critical: Only {remaining:.1f}h remaining - escalation recommended"
            escalation_needed = True
        elif percentage >= self.config.warning_threshold * 100:
            status = SLAStatus.WARNING
            recommendation = f"Warning: {remaining:.1f}h remaining - send reminder"
            escalation_needed = False
        else:
            status = SLAStatus.ON_TRACK
            recommendation = f"On track: {remaining:.1f}h remaining"
            escalation_needed = False

        return SLACheck(
            step_id=step.step_id,
            status=status,
            elapsed_hours=elapsed,
            sla_hours=sla_hours,
            remaining_hours=remaining,
            percentage_used=percentage,
            recommendation=recommendation,
            escalation_needed=escalation_needed,
        )

    def check_workflow_sla(self, workflow: Workflow) -> Dict[str, Any]:
        """
        Check SLA status for entire workflow.

        Returns aggregate status and per-step details.
        """
        step_checks = [self.check_step_sla(step) for step in workflow.steps]

        # Aggregate status
        breached_count = len([c for c in step_checks if c.status == SLAStatus.BREACHED])
        critical_count = len([c for c in step_checks if c.status == SLAStatus.CRITICAL])
        warning_count = len([c for c in step_checks if c.status == SLAStatus.WARNING])

        if breached_count > 0:
            overall_status = SLAStatus.BREACHED
        elif critical_count > 0:
            overall_status = SLAStatus.CRITICAL
        elif warning_count > 0:
            overall_status = SLAStatus.WARNING
        else:
            overall_status = SLAStatus.ON_TRACK

        # Calculate workflow-level metrics
        total_sla = workflow.get_total_sla_hours()
        elapsed = workflow.get_elapsed_hours()

        return {
            "workflow_id": workflow.workflow_id,
            "overall_status": overall_status.value,
            "total_sla_hours": total_sla,
            "elapsed_hours": round(elapsed, 2),
            "remaining_hours": round(max(0, total_sla - elapsed), 2),
            "breached_steps": breached_count,
            "critical_steps": critical_count,
            "warning_steps": warning_count,
            "step_checks": [c.to_dict() for c in step_checks],
            "needs_attention": overall_status in [SLAStatus.BREACHED, SLAStatus.CRITICAL],
        }

    def create_escalation(
        self,
        step: WorkflowStep,
        workflow: Workflow,
        trigger: EscalationTrigger,
        to_approver_id: Optional[str] = None,
        to_approver_type: Optional[ApproverTypeEnum] = None,
        reason: str = ""
    ) -> EscalationAction:
        """
        Create an escalation action.

        Args:
            step: Step to escalate
            workflow: Parent workflow
            trigger: What triggered escalation
            to_approver_id: Target approver (optional)
            to_approver_type: Target approver type (optional)
            reason: Reason for escalation

        Returns:
            EscalationAction
        """
        # Determine escalation target
        if not to_approver_type:
            to_approver_type = self._get_escalation_target(step.approver_type)

        sla_check = self.check_step_sla(step)

        action = EscalationAction(
            action_id=f"ESC-{datetime.now().strftime('%Y%m%d%H%M%S')}-{step.step_id[:4]}",
            trigger=trigger,
            step_id=step.step_id,
            workflow_id=workflow.workflow_id,
            from_approver_id=step.approver_id or "",
            to_approver_id=to_approver_id or "",
            to_approver_type=to_approver_type,
            reason=reason or f"Escalated due to {trigger.value}",
            original_sla_hours=step.sla_hours,
            elapsed_hours=sla_check.elapsed_hours,
        )

        self._pending_escalations.append(action)

        logger.info(
            f"Created escalation {action.action_id} for step {step.step_id} "
            f"(trigger: {trigger.value})"
        )

        return action

    def execute_escalation(
        self,
        action: EscalationAction,
        resolved_approver_id: Optional[str] = None,
        resolved_approver_name: Optional[str] = None
    ) -> bool:
        """
        Execute an escalation action.

        Args:
            action: Escalation to execute
            resolved_approver_id: Resolved target approver ID
            resolved_approver_name: Resolved target approver name

        Returns:
            Success status
        """
        if action.executed:
            logger.warning(f"Escalation {action.action_id} already executed")
            return False

        # Update action
        if resolved_approver_id:
            action.to_approver_id = resolved_approver_id
        action.executed = True
        action.executed_at = datetime.now()

        # Call callback
        if self._on_escalation:
            try:
                self._on_escalation(action)
            except Exception as e:
                logger.error(f"Escalation callback failed: {e}")

        # Move to history
        self._pending_escalations = [
            a for a in self._pending_escalations
            if a.action_id != action.action_id
        ]
        self._escalation_history.append(action)

        logger.info(
            f"Executed escalation {action.action_id}: "
            f"{action.from_approver_id} -> {action.to_approver_id}"
        )

        return True

    def _get_escalation_target(
        self,
        from_type: ApproverTypeEnum
    ) -> ApproverTypeEnum:
        """Determine escalation target based on source approver type."""
        escalation_chain = {
            ApproverTypeEnum.LINE_MANAGER: ApproverTypeEnum.SECURITY_OFFICER,
            ApproverTypeEnum.ROLE_OWNER: ApproverTypeEnum.SECURITY_OFFICER,
            ApproverTypeEnum.PROCESS_OWNER: ApproverTypeEnum.SECURITY_OFFICER,
            ApproverTypeEnum.SECURITY_OFFICER: ApproverTypeEnum.COMPLIANCE_OFFICER,
            ApproverTypeEnum.COMPLIANCE_OFFICER: ApproverTypeEnum.CISO,
            ApproverTypeEnum.DATA_OWNER: ApproverTypeEnum.COMPLIANCE_OFFICER,
            ApproverTypeEnum.SYSTEM_OWNER: ApproverTypeEnum.SECURITY_OFFICER,
        }
        return escalation_chain.get(from_type, ApproverTypeEnum.GOVERNANCE_DESK)

    def get_sla_for_risk(self, risk_level: str) -> float:
        """Get SLA hours for a risk level."""
        return self.config.sla_by_risk.get(risk_level.upper(), 24.0)

    def _calculate_business_hours(
        self,
        start: datetime,
        end: datetime
    ) -> float:
        """Calculate elapsed business hours between two times."""
        if not self.config.use_business_hours:
            return (end - start).total_seconds() / 3600

        business_hours = 0.0
        current = start

        while current < end:
            # Skip weekends
            if self.config.exclude_weekends and current.weekday() >= 5:
                current += timedelta(days=1)
                current = current.replace(hour=self.config.business_start_hour, minute=0, second=0)
                continue

            # Check if within business hours
            if self.config.business_start_hour <= current.hour < self.config.business_end_hour:
                # Calculate how much of this hour counts
                next_hour = current.replace(minute=0, second=0) + timedelta(hours=1)
                count_until = min(end, next_hour)

                if current.hour >= self.config.business_end_hour - 1:
                    # Last business hour
                    end_of_day = current.replace(hour=self.config.business_end_hour, minute=0, second=0)
                    count_until = min(count_until, end_of_day)

                business_hours += (count_until - current).total_seconds() / 3600
                current = count_until
            else:
                # Outside business hours, jump to next business hour
                if current.hour < self.config.business_start_hour:
                    current = current.replace(hour=self.config.business_start_hour, minute=0, second=0)
                else:
                    # After business hours, jump to next day
                    current += timedelta(days=1)
                    current = current.replace(hour=self.config.business_start_hour, minute=0, second=0)

        return business_hours

    def get_reminder_schedule(self, step: WorkflowStep) -> List[datetime]:
        """Get scheduled reminder times for a step."""
        if not self.config.send_reminders:
            return []

        reminders = []
        due_at = step.due_at or (step.created_at + timedelta(hours=step.sla_hours))

        for hours_before in self.config.reminder_intervals_hours:
            reminder_time = due_at - timedelta(hours=hours_before)
            if reminder_time > datetime.now():
                reminders.append(reminder_time)

        return sorted(reminders)

    def check_all_workflows(
        self,
        workflows: List[Workflow]
    ) -> List[Dict[str, Any]]:
        """
        Check SLA status for multiple workflows.

        Returns list of workflows needing attention.
        """
        results = []

        for workflow in workflows:
            if workflow.is_complete():
                continue

            check = self.check_workflow_sla(workflow)

            if check["needs_attention"]:
                results.append({
                    "workflow_id": workflow.workflow_id,
                    "status": check["overall_status"],
                    "breached_steps": check["breached_steps"],
                    "critical_steps": check["critical_steps"],
                    "elapsed_hours": check["elapsed_hours"],
                    "recommended_action": (
                        "ESCALATE" if check["breached_steps"] > 0
                        else "REMIND"
                    ),
                })

        return sorted(results, key=lambda x: x["elapsed_hours"], reverse=True)

    def predict_breach(
        self,
        step: WorkflowStep,
        approver_avg_response_hours: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Predict if a step will breach SLA.

        Uses approver historical response time if available.
        """
        sla_check = self.check_step_sla(step)

        if step.is_complete():
            return {
                "will_breach": False,
                "confidence": 1.0,
                "reason": "Step already completed",
            }

        # If we have historical data
        if approver_avg_response_hours:
            predicted_completion = step.activated_at + timedelta(hours=approver_avg_response_hours)
            will_breach = predicted_completion > step.due_at

            return {
                "will_breach": will_breach,
                "confidence": 0.7,  # Moderate confidence with historical data
                "predicted_completion": predicted_completion.isoformat(),
                "approver_avg_hours": approver_avg_response_hours,
                "sla_hours": step.sla_hours,
                "reason": (
                    f"Approver typically responds in {approver_avg_response_hours:.1f}h, "
                    f"SLA is {step.sla_hours}h"
                ),
            }

        # Without historical data, use simple heuristics
        if sla_check.percentage_used > 50:
            likelihood = sla_check.percentage_used / 100
            return {
                "will_breach": likelihood > 0.75,
                "confidence": 0.3,  # Low confidence without data
                "likelihood": round(likelihood, 2),
                "reason": f"{sla_check.percentage_used:.0f}% of SLA used without response",
            }

        return {
            "will_breach": False,
            "confidence": 0.5,
            "reason": "Insufficient data for prediction",
        }

    def register_callbacks(
        self,
        on_escalation: Optional[Callable[[EscalationAction], None]] = None,
        on_reminder: Optional[Callable[[WorkflowStep, str], None]] = None,
        on_breach: Optional[Callable[[WorkflowStep], None]] = None
    ) -> None:
        """Register callback functions."""
        self._on_escalation = on_escalation
        self._on_reminder = on_reminder
        self._on_breach = on_breach

    def get_escalation_history(
        self,
        workflow_id: Optional[str] = None,
        since: Optional[datetime] = None
    ) -> List[EscalationAction]:
        """Get escalation history."""
        history = self._escalation_history

        if workflow_id:
            history = [a for a in history if a.workflow_id == workflow_id]

        if since:
            history = [a for a in history if a.triggered_at >= since]

        return sorted(history, key=lambda a: a.triggered_at, reverse=True)

    def get_pending_escalations(self) -> List[EscalationAction]:
        """Get pending escalations."""
        return list(self._pending_escalations)

    def generate_sla_report(
        self,
        workflows: List[Workflow]
    ) -> Dict[str, Any]:
        """Generate SLA compliance report."""
        total = len(workflows)
        completed = [w for w in workflows if w.is_complete()]
        active = [w for w in workflows if not w.is_complete()]

        # Calculate breach rates
        breached = 0
        total_elapsed = 0.0
        total_sla = 0.0

        for w in completed:
            elapsed = w.get_elapsed_hours()
            sla = w.get_total_sla_hours()
            total_elapsed += elapsed
            total_sla += sla
            if elapsed > sla:
                breached += 1

        active_checks = [self.check_workflow_sla(w) for w in active]
        active_at_risk = len([c for c in active_checks if c["needs_attention"]])

        return {
            "generated_at": datetime.now().isoformat(),
            "summary": {
                "total_workflows": total,
                "completed": len(completed),
                "active": len(active),
                "breached": breached,
                "active_at_risk": active_at_risk,
            },
            "metrics": {
                "compliance_rate": round((len(completed) - breached) / len(completed) * 100, 1) if completed else 100,
                "avg_elapsed_hours": round(total_elapsed / len(completed), 2) if completed else 0,
                "avg_sla_hours": round(total_sla / len(completed), 2) if completed else 0,
            },
            "escalations": {
                "pending": len(self._pending_escalations),
                "total_executed": len(self._escalation_history),
            },
        }
