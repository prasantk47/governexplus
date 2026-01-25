# Event-Driven Re-Evaluation Engine
# Continuous workflow adaptation based on real-time events

"""
Event-Driven Re-Evaluation for GOVERNEX+.

THIS IS WHAT MAKES GOVERNEX+ TRULY DYNAMIC:
- MSMP: Static paths, no runtime changes
- GOVERNEX+: Continuous re-evaluation on any relevant event

Event Types:
1. Risk Events - Risk score changes, new SoD detected
2. Approval Events - Approvals, rejections, escalations
3. SLA Events - Breaches, warnings, predictions
4. External Events - Fraud alerts, control failures
5. User Events - Role changes, terminations
6. System Events - System unavailable, provisioning failures

Architecture:
- Event Bus: Central event distribution
- Event Handlers: Process specific event types
- Re-Evaluators: Determine workflow impact
- Action Executors: Apply changes to workflows
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable, Set
from datetime import datetime, timedelta
from enum import Enum
from abc import ABC, abstractmethod
import logging
import uuid
import asyncio
from collections import defaultdict

logger = logging.getLogger(__name__)


# ============================================================
# EVENT TYPES
# ============================================================

class EventType(Enum):
    """All event types that can trigger re-evaluation."""

    # Risk Events
    RISK_SCORE_CHANGED = "RISK_SCORE_CHANGED"
    SOD_CONFLICT_DETECTED = "SOD_CONFLICT_DETECTED"
    SOD_CONFLICT_RESOLVED = "SOD_CONFLICT_RESOLVED"
    SENSITIVE_ACCESS_DETECTED = "SENSITIVE_ACCESS_DETECTED"
    RISK_LEVEL_ESCALATED = "RISK_LEVEL_ESCALATED"

    # Approval Events
    APPROVAL_RECEIVED = "APPROVAL_RECEIVED"
    REJECTION_RECEIVED = "REJECTION_RECEIVED"
    APPROVAL_DELEGATED = "APPROVAL_DELEGATED"
    APPROVAL_ESCALATED = "APPROVAL_ESCALATED"
    APPROVER_CHANGED = "APPROVER_CHANGED"

    # SLA Events
    SLA_WARNING = "SLA_WARNING"
    SLA_BREACH = "SLA_BREACH"
    SLA_BREACH_PREDICTED = "SLA_BREACH_PREDICTED"
    ESCALATION_TRIGGERED = "ESCALATION_TRIGGERED"

    # External Events (from integrations)
    FRAUD_ALERT = "FRAUD_ALERT"
    CONTROL_FAILURE = "CONTROL_FAILURE"
    AUDIT_FINDING = "AUDIT_FINDING"
    POLICY_VIOLATION = "POLICY_VIOLATION"
    SECURITY_INCIDENT = "SECURITY_INCIDENT"

    # User Events
    USER_TERMINATED = "USER_TERMINATED"
    USER_ROLE_CHANGED = "USER_ROLE_CHANGED"
    USER_DEPARTMENT_CHANGED = "USER_DEPARTMENT_CHANGED"
    MANAGER_CHANGED = "MANAGER_CHANGED"

    # System Events
    SYSTEM_UNAVAILABLE = "SYSTEM_UNAVAILABLE"
    SYSTEM_RECOVERED = "SYSTEM_RECOVERED"
    PROVISIONING_FAILED = "PROVISIONING_FAILED"
    PROVISIONING_RETRIED = "PROVISIONING_RETRIED"

    # Workflow Events
    WORKFLOW_STARTED = "WORKFLOW_STARTED"
    WORKFLOW_COMPLETED = "WORKFLOW_COMPLETED"
    WORKFLOW_CANCELLED = "WORKFLOW_CANCELLED"
    STEP_COMPLETED = "STEP_COMPLETED"

    # Custom Events
    CUSTOM = "CUSTOM"


class EventPriority(Enum):
    """Event processing priority."""
    CRITICAL = 1   # Process immediately (fraud, security)
    HIGH = 2       # Process urgently (SLA breach)
    NORMAL = 3     # Standard processing (approvals)
    LOW = 4        # Background processing (info updates)


class EventSource(Enum):
    """Source of events."""
    WORKFLOW_ENGINE = "WORKFLOW_ENGINE"
    RISK_ENGINE = "RISK_ENGINE"
    SLA_MANAGER = "SLA_MANAGER"
    PROVISIONING_ENGINE = "PROVISIONING_ENGINE"
    EXTERNAL_SYSTEM = "EXTERNAL_SYSTEM"
    USER_ACTION = "USER_ACTION"
    SCHEDULER = "SCHEDULER"
    KAFKA = "KAFKA"
    WEBHOOK = "WEBHOOK"


# ============================================================
# EVENT MODEL
# ============================================================

@dataclass
class WorkflowEvent:
    """
    A workflow event that may trigger re-evaluation.
    """
    event_id: str = field(default_factory=lambda: f"EVT-{str(uuid.uuid4())[:12]}")
    event_type: EventType = EventType.CUSTOM
    priority: EventPriority = EventPriority.NORMAL
    source: EventSource = EventSource.WORKFLOW_ENGINE

    # Context
    request_id: Optional[str] = None
    item_id: Optional[str] = None
    workflow_id: Optional[str] = None
    step_id: Optional[str] = None
    user_id: Optional[str] = None

    # Payload
    payload: Dict[str, Any] = field(default_factory=dict)

    # Metadata
    timestamp: datetime = field(default_factory=datetime.now)
    correlation_id: Optional[str] = None  # Link related events
    causation_id: Optional[str] = None    # What caused this event

    # Processing state
    processed: bool = False
    processed_at: Optional[datetime] = None
    processing_results: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "priority": self.priority.value,
            "source": self.source.value,
            "context": {
                "request_id": self.request_id,
                "item_id": self.item_id,
                "workflow_id": self.workflow_id,
                "step_id": self.step_id,
                "user_id": self.user_id,
            },
            "payload": self.payload,
            "timestamp": self.timestamp.isoformat(),
            "correlation_id": self.correlation_id,
            "processed": self.processed,
        }

    @classmethod
    def risk_score_changed(
        cls,
        request_id: str,
        item_id: Optional[str],
        old_score: int,
        new_score: int,
        reason: str
    ) -> "WorkflowEvent":
        """Factory for risk score change event."""
        # Determine priority based on score delta
        delta = new_score - old_score
        if delta >= 30:
            priority = EventPriority.CRITICAL
        elif delta >= 15:
            priority = EventPriority.HIGH
        else:
            priority = EventPriority.NORMAL

        return cls(
            event_type=EventType.RISK_SCORE_CHANGED,
            priority=priority,
            source=EventSource.RISK_ENGINE,
            request_id=request_id,
            item_id=item_id,
            payload={
                "old_score": old_score,
                "new_score": new_score,
                "delta": delta,
                "reason": reason,
            }
        )

    @classmethod
    def sla_breach(
        cls,
        workflow_id: str,
        step_id: str,
        breach_hours: float,
        escalate_to: List[str]
    ) -> "WorkflowEvent":
        """Factory for SLA breach event."""
        return cls(
            event_type=EventType.SLA_BREACH,
            priority=EventPriority.HIGH,
            source=EventSource.SLA_MANAGER,
            workflow_id=workflow_id,
            step_id=step_id,
            payload={
                "breach_hours": breach_hours,
                "escalate_to": escalate_to,
            }
        )

    @classmethod
    def fraud_alert(
        cls,
        user_id: str,
        alert_type: str,
        confidence: float,
        details: Dict[str, Any]
    ) -> "WorkflowEvent":
        """Factory for fraud alert event."""
        return cls(
            event_type=EventType.FRAUD_ALERT,
            priority=EventPriority.CRITICAL,
            source=EventSource.EXTERNAL_SYSTEM,
            user_id=user_id,
            payload={
                "alert_type": alert_type,
                "confidence": confidence,
                "details": details,
            }
        )


# ============================================================
# RE-EVALUATION ACTIONS
# ============================================================

class ReEvaluationAction(Enum):
    """Actions that can result from re-evaluation."""
    NO_CHANGE = "NO_CHANGE"

    # Workflow modifications
    ADD_APPROVAL_STEP = "ADD_APPROVAL_STEP"
    REMOVE_APPROVAL_STEP = "REMOVE_APPROVAL_STEP"
    CHANGE_APPROVER = "CHANGE_APPROVER"
    ESCALATE_STEP = "ESCALATE_STEP"

    # Status changes
    HOLD_WORKFLOW = "HOLD_WORKFLOW"
    RESUME_WORKFLOW = "RESUME_WORKFLOW"
    CANCEL_WORKFLOW = "CANCEL_WORKFLOW"

    # Item actions
    HOLD_ITEM = "HOLD_ITEM"
    RELEASE_ITEM = "RELEASE_ITEM"
    REJECT_ITEM = "REJECT_ITEM"
    REVOKE_PROVISIONING = "REVOKE_PROVISIONING"

    # Notifications
    NOTIFY_REQUESTER = "NOTIFY_REQUESTER"
    NOTIFY_APPROVER = "NOTIFY_APPROVER"
    NOTIFY_SECURITY = "NOTIFY_SECURITY"

    # Re-evaluation
    TRIGGER_RISK_RECALC = "TRIGGER_RISK_RECALC"
    TRIGGER_PROVISIONING_EVAL = "TRIGGER_PROVISIONING_EVAL"


@dataclass
class ReEvaluationResult:
    """Result of event-driven re-evaluation."""
    event_id: str
    event_type: EventType
    actions_taken: List[ReEvaluationAction] = field(default_factory=list)
    action_details: List[Dict[str, Any]] = field(default_factory=list)
    workflow_modified: bool = False
    notifications_sent: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "actions_taken": [a.value for a in self.actions_taken],
            "action_details": self.action_details,
            "workflow_modified": self.workflow_modified,
            "notifications_sent": self.notifications_sent,
            "timestamp": self.timestamp.isoformat(),
        }


# ============================================================
# EVENT HANDLERS (PLUGGABLE)
# ============================================================

class EventHandler(ABC):
    """Base class for event handlers."""

    @abstractmethod
    def can_handle(self, event: WorkflowEvent) -> bool:
        """Check if this handler can process the event."""
        pass

    @abstractmethod
    def handle(self, event: WorkflowEvent, context: Dict[str, Any]) -> ReEvaluationResult:
        """Process the event and return actions."""
        pass


class RiskChangeHandler(EventHandler):
    """Handles risk score changes."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.high_risk_threshold = self.config.get("high_risk_threshold", 70)
        self.critical_risk_threshold = self.config.get("critical_risk_threshold", 85)

    def can_handle(self, event: WorkflowEvent) -> bool:
        return event.event_type in [
            EventType.RISK_SCORE_CHANGED,
            EventType.SOD_CONFLICT_DETECTED,
            EventType.RISK_LEVEL_ESCALATED,
        ]

    def handle(self, event: WorkflowEvent, context: Dict[str, Any]) -> ReEvaluationResult:
        result = ReEvaluationResult(
            event_id=event.event_id,
            event_type=event.event_type,
        )

        if event.event_type == EventType.RISK_SCORE_CHANGED:
            new_score = event.payload.get("new_score", 0)
            old_score = event.payload.get("old_score", 0)

            # Critical risk: Hold everything
            if new_score >= self.critical_risk_threshold:
                result.actions_taken.append(ReEvaluationAction.HOLD_WORKFLOW)
                result.actions_taken.append(ReEvaluationAction.NOTIFY_SECURITY)
                result.action_details.append({
                    "action": "HOLD_WORKFLOW",
                    "reason": f"Risk score {new_score} exceeds critical threshold {self.critical_risk_threshold}",
                })
                result.workflow_modified = True

            # High risk: Add security review step
            elif new_score >= self.high_risk_threshold and old_score < self.high_risk_threshold:
                result.actions_taken.append(ReEvaluationAction.ADD_APPROVAL_STEP)
                result.action_details.append({
                    "action": "ADD_APPROVAL_STEP",
                    "step_type": "SECURITY_REVIEW",
                    "reason": f"Risk score increased to {new_score}, security review required",
                })
                result.workflow_modified = True

            # Risk decreased: Check if we can remove steps
            elif new_score < old_score:
                result.actions_taken.append(ReEvaluationAction.TRIGGER_RISK_RECALC)
                result.action_details.append({
                    "action": "TRIGGER_RISK_RECALC",
                    "reason": f"Risk score decreased from {old_score} to {new_score}",
                })

        elif event.event_type == EventType.SOD_CONFLICT_DETECTED:
            result.actions_taken.append(ReEvaluationAction.HOLD_ITEM)
            result.actions_taken.append(ReEvaluationAction.ADD_APPROVAL_STEP)
            result.action_details.append({
                "action": "SOD_RESPONSE",
                "step_type": "SOD_REVIEW",
                "reason": "SoD conflict detected, additional review required",
            })
            result.workflow_modified = True

        return result


class SLAEventHandler(EventHandler):
    """Handles SLA-related events."""

    def can_handle(self, event: WorkflowEvent) -> bool:
        return event.event_type in [
            EventType.SLA_WARNING,
            EventType.SLA_BREACH,
            EventType.SLA_BREACH_PREDICTED,
        ]

    def handle(self, event: WorkflowEvent, context: Dict[str, Any]) -> ReEvaluationResult:
        result = ReEvaluationResult(
            event_id=event.event_id,
            event_type=event.event_type,
        )

        if event.event_type == EventType.SLA_BREACH:
            escalate_to = event.payload.get("escalate_to", [])
            result.actions_taken.append(ReEvaluationAction.ESCALATE_STEP)
            result.actions_taken.append(ReEvaluationAction.NOTIFY_APPROVER)
            result.action_details.append({
                "action": "ESCALATE_STEP",
                "escalate_to": escalate_to,
                "reason": f"SLA breached by {event.payload.get('breach_hours', 0):.1f} hours",
            })
            result.notifications_sent = escalate_to
            result.workflow_modified = True

        elif event.event_type == EventType.SLA_WARNING:
            result.actions_taken.append(ReEvaluationAction.NOTIFY_APPROVER)
            result.action_details.append({
                "action": "WARNING_SENT",
                "remaining_hours": event.payload.get("remaining_hours", 0),
            })

        elif event.event_type == EventType.SLA_BREACH_PREDICTED:
            # Predictive escalation
            if event.payload.get("probability", 0) > 0.8:
                result.actions_taken.append(ReEvaluationAction.ESCALATE_STEP)
                result.action_details.append({
                    "action": "PREDICTIVE_ESCALATION",
                    "probability": event.payload.get("probability"),
                    "reason": "High probability of SLA breach",
                })
                result.workflow_modified = True

        return result


class FraudAlertHandler(EventHandler):
    """Handles fraud and security alerts."""

    def can_handle(self, event: WorkflowEvent) -> bool:
        return event.event_type in [
            EventType.FRAUD_ALERT,
            EventType.SECURITY_INCIDENT,
            EventType.POLICY_VIOLATION,
        ]

    def handle(self, event: WorkflowEvent, context: Dict[str, Any]) -> ReEvaluationResult:
        result = ReEvaluationResult(
            event_id=event.event_id,
            event_type=event.event_type,
        )

        confidence = event.payload.get("confidence", 0)

        # High confidence: Immediate hold
        if confidence >= 0.9:
            result.actions_taken.append(ReEvaluationAction.HOLD_WORKFLOW)
            result.actions_taken.append(ReEvaluationAction.NOTIFY_SECURITY)
            result.action_details.append({
                "action": "IMMEDIATE_HOLD",
                "reason": f"High-confidence fraud alert ({confidence:.0%})",
                "alert_type": event.payload.get("alert_type"),
            })
            result.workflow_modified = True

        # Medium confidence: Flag for review
        elif confidence >= 0.7:
            result.actions_taken.append(ReEvaluationAction.ADD_APPROVAL_STEP)
            result.actions_taken.append(ReEvaluationAction.NOTIFY_SECURITY)
            result.action_details.append({
                "action": "SECURITY_REVIEW_ADDED",
                "reason": f"Fraud alert requires review ({confidence:.0%})",
            })
            result.workflow_modified = True

        # Low confidence: Log and continue
        else:
            result.actions_taken.append(ReEvaluationAction.NO_CHANGE)
            result.action_details.append({
                "action": "LOGGED",
                "reason": f"Low-confidence alert logged ({confidence:.0%})",
            })

        return result


class UserEventHandler(EventHandler):
    """Handles user-related events."""

    def can_handle(self, event: WorkflowEvent) -> bool:
        return event.event_type in [
            EventType.USER_TERMINATED,
            EventType.USER_ROLE_CHANGED,
            EventType.MANAGER_CHANGED,
            EventType.USER_DEPARTMENT_CHANGED,
        ]

    def handle(self, event: WorkflowEvent, context: Dict[str, Any]) -> ReEvaluationResult:
        result = ReEvaluationResult(
            event_id=event.event_id,
            event_type=event.event_type,
        )

        if event.event_type == EventType.USER_TERMINATED:
            # Cancel all pending workflows for terminated user
            result.actions_taken.append(ReEvaluationAction.CANCEL_WORKFLOW)
            result.actions_taken.append(ReEvaluationAction.REVOKE_PROVISIONING)
            result.action_details.append({
                "action": "TERMINATION_RESPONSE",
                "reason": "User terminated, all pending access cancelled",
            })
            result.workflow_modified = True

        elif event.event_type == EventType.MANAGER_CHANGED:
            # Update approver if manager was the approver
            old_manager = event.payload.get("old_manager")
            new_manager = event.payload.get("new_manager")
            result.actions_taken.append(ReEvaluationAction.CHANGE_APPROVER)
            result.action_details.append({
                "action": "APPROVER_UPDATED",
                "old_approver": old_manager,
                "new_approver": new_manager,
                "reason": "Manager changed, approver updated",
            })
            result.workflow_modified = True

        elif event.event_type == EventType.USER_DEPARTMENT_CHANGED:
            # Re-evaluate risk based on new department
            result.actions_taken.append(ReEvaluationAction.TRIGGER_RISK_RECALC)
            result.action_details.append({
                "action": "RISK_RECALC",
                "reason": "Department changed, risk needs re-evaluation",
            })

        return result


class ProvisioningEventHandler(EventHandler):
    """Handles provisioning-related events."""

    def can_handle(self, event: WorkflowEvent) -> bool:
        return event.event_type in [
            EventType.PROVISIONING_FAILED,
            EventType.SYSTEM_UNAVAILABLE,
            EventType.SYSTEM_RECOVERED,
        ]

    def handle(self, event: WorkflowEvent, context: Dict[str, Any]) -> ReEvaluationResult:
        result = ReEvaluationResult(
            event_id=event.event_id,
            event_type=event.event_type,
        )

        if event.event_type == EventType.PROVISIONING_FAILED:
            retry_count = event.payload.get("retry_count", 0)
            max_retries = context.get("max_retries", 3)

            if retry_count < max_retries:
                result.actions_taken.append(ReEvaluationAction.TRIGGER_PROVISIONING_EVAL)
                result.action_details.append({
                    "action": "RETRY_PROVISIONING",
                    "retry_count": retry_count + 1,
                    "reason": "Provisioning failed, scheduling retry",
                })
            else:
                result.actions_taken.append(ReEvaluationAction.HOLD_ITEM)
                result.actions_taken.append(ReEvaluationAction.NOTIFY_REQUESTER)
                result.action_details.append({
                    "action": "PROVISIONING_HELD",
                    "reason": f"Provisioning failed after {max_retries} retries",
                })
                result.workflow_modified = True

        elif event.event_type == EventType.SYSTEM_RECOVERED:
            # Re-trigger provisioning for held items
            result.actions_taken.append(ReEvaluationAction.RELEASE_ITEM)
            result.actions_taken.append(ReEvaluationAction.TRIGGER_PROVISIONING_EVAL)
            result.action_details.append({
                "action": "SYSTEM_RECOVERED",
                "reason": "System recovered, re-evaluating held items",
            })

        return result


# ============================================================
# EVENT BUS
# ============================================================

class EventBus:
    """
    Central event distribution system.

    Features:
    - Publish/subscribe model
    - Priority-based processing
    - Event persistence
    - Dead letter queue
    """

    def __init__(self):
        self._handlers: List[EventHandler] = []
        self._subscribers: Dict[EventType, List[Callable]] = defaultdict(list)
        self._event_store: List[WorkflowEvent] = []
        self._dead_letter_queue: List[WorkflowEvent] = []
        self._processing = False
        self._event_queue: List[WorkflowEvent] = []

    def register_handler(self, handler: EventHandler) -> None:
        """Register an event handler."""
        self._handlers.append(handler)
        logger.info(f"Registered handler: {handler.__class__.__name__}")

    def subscribe(self, event_type: EventType, callback: Callable) -> None:
        """Subscribe to specific event type."""
        self._subscribers[event_type].append(callback)

    def unsubscribe(self, event_type: EventType, callback: Callable) -> None:
        """Unsubscribe from event type."""
        if callback in self._subscribers[event_type]:
            self._subscribers[event_type].remove(callback)

    def publish(self, event: WorkflowEvent) -> None:
        """
        Publish an event to the bus.

        Events are queued and processed by priority.
        """
        self._event_store.append(event)
        self._event_queue.append(event)

        # Sort by priority (lower number = higher priority)
        self._event_queue.sort(key=lambda e: e.priority.value)

        logger.info(f"Event published: {event.event_type.value} [{event.event_id}]")

    def process_events(self, context: Dict[str, Any] = None) -> List[ReEvaluationResult]:
        """
        Process all queued events.

        Returns list of re-evaluation results.
        """
        context = context or {}
        results = []

        while self._event_queue:
            event = self._event_queue.pop(0)

            try:
                result = self._process_single_event(event, context)
                results.append(result)

                # Notify subscribers
                for callback in self._subscribers.get(event.event_type, []):
                    try:
                        callback(event, result)
                    except Exception as e:
                        logger.error(f"Subscriber callback failed: {e}")

                event.processed = True
                event.processed_at = datetime.now()
                event.processing_results.append(result.to_dict())

            except Exception as e:
                logger.error(f"Event processing failed: {e}")
                self._dead_letter_queue.append(event)

        return results

    def _process_single_event(
        self,
        event: WorkflowEvent,
        context: Dict[str, Any]
    ) -> ReEvaluationResult:
        """Process a single event through handlers."""

        # Find matching handlers
        matching_handlers = [h for h in self._handlers if h.can_handle(event)]

        if not matching_handlers:
            return ReEvaluationResult(
                event_id=event.event_id,
                event_type=event.event_type,
                actions_taken=[ReEvaluationAction.NO_CHANGE],
                action_details=[{"reason": "No handler for event type"}],
            )

        # Aggregate results from all handlers
        combined_result = ReEvaluationResult(
            event_id=event.event_id,
            event_type=event.event_type,
        )

        for handler in matching_handlers:
            result = handler.handle(event, context)
            combined_result.actions_taken.extend(result.actions_taken)
            combined_result.action_details.extend(result.action_details)
            combined_result.notifications_sent.extend(result.notifications_sent)
            if result.workflow_modified:
                combined_result.workflow_modified = True

        return combined_result

    def get_event_history(
        self,
        request_id: Optional[str] = None,
        event_type: Optional[EventType] = None,
        limit: int = 100
    ) -> List[WorkflowEvent]:
        """Get event history with optional filters."""
        events = self._event_store

        if request_id:
            events = [e for e in events if e.request_id == request_id]
        if event_type:
            events = [e for e in events if e.event_type == event_type]

        return events[-limit:]

    def get_dead_letter_queue(self) -> List[WorkflowEvent]:
        """Get events that failed processing."""
        return list(self._dead_letter_queue)

    def retry_dead_letters(self, context: Dict[str, Any] = None) -> List[ReEvaluationResult]:
        """Retry processing dead letter events."""
        events = self._dead_letter_queue.copy()
        self._dead_letter_queue.clear()

        for event in events:
            self.publish(event)

        return self.process_events(context)


# ============================================================
# RE-EVALUATION ENGINE
# ============================================================

class ReEvaluationEngine:
    """
    Coordinates event-driven workflow re-evaluation.

    This is the brain that ties everything together:
    - Receives events from any source
    - Routes to appropriate handlers
    - Applies changes to workflows
    - Maintains full audit trail
    """

    def __init__(self):
        self.event_bus = EventBus()
        self._action_executors: Dict[ReEvaluationAction, Callable] = {}
        self._audit_log: List[Dict[str, Any]] = []

        # Register default handlers
        self._register_default_handlers()

    def _register_default_handlers(self) -> None:
        """Register built-in event handlers."""
        self.event_bus.register_handler(RiskChangeHandler())
        self.event_bus.register_handler(SLAEventHandler())
        self.event_bus.register_handler(FraudAlertHandler())
        self.event_bus.register_handler(UserEventHandler())
        self.event_bus.register_handler(ProvisioningEventHandler())

    def register_handler(self, handler: EventHandler) -> None:
        """Register a custom event handler."""
        self.event_bus.register_handler(handler)

    def register_action_executor(
        self,
        action: ReEvaluationAction,
        executor: Callable
    ) -> None:
        """Register an executor for a re-evaluation action."""
        self._action_executors[action] = executor

    def emit_event(self, event: WorkflowEvent) -> None:
        """Emit an event for processing."""
        self.event_bus.publish(event)
        self._audit("EVENT_EMITTED", event.to_dict())

    def process_pending_events(
        self,
        context: Dict[str, Any] = None
    ) -> List[ReEvaluationResult]:
        """
        Process all pending events and execute actions.

        This is the main entry point for event processing.
        """
        context = context or {}

        # Process events
        results = self.event_bus.process_events(context)

        # Execute actions
        for result in results:
            self._execute_actions(result, context)

        return results

    def _execute_actions(
        self,
        result: ReEvaluationResult,
        context: Dict[str, Any]
    ) -> None:
        """Execute the actions from a re-evaluation result."""
        for action in result.actions_taken:
            if action == ReEvaluationAction.NO_CHANGE:
                continue

            executor = self._action_executors.get(action)
            if executor:
                try:
                    executor(result, context)
                    self._audit("ACTION_EXECUTED", {
                        "event_id": result.event_id,
                        "action": action.value,
                    })
                except Exception as e:
                    logger.error(f"Action execution failed: {e}")
                    self._audit("ACTION_FAILED", {
                        "event_id": result.event_id,
                        "action": action.value,
                        "error": str(e),
                    })
            else:
                logger.warning(f"No executor for action: {action.value}")

    def _audit(self, event_type: str, details: Dict[str, Any]) -> None:
        """Add audit entry."""
        self._audit_log.append({
            "event_type": event_type,
            "timestamp": datetime.now().isoformat(),
            "details": details,
        })

    def get_audit_log(
        self,
        event_id: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get audit log entries."""
        entries = self._audit_log
        if event_id:
            entries = [e for e in entries if e["details"].get("event_id") == event_id]
        return entries[-limit:]

    # ============================================================
    # CONVENIENCE METHODS FOR COMMON EVENTS
    # ============================================================

    def on_risk_change(
        self,
        request_id: str,
        item_id: Optional[str],
        old_score: int,
        new_score: int,
        reason: str
    ) -> List[ReEvaluationResult]:
        """Handle risk score change."""
        event = WorkflowEvent.risk_score_changed(
            request_id, item_id, old_score, new_score, reason
        )
        self.emit_event(event)
        return self.process_pending_events()

    def on_sla_breach(
        self,
        workflow_id: str,
        step_id: str,
        breach_hours: float,
        escalate_to: List[str]
    ) -> List[ReEvaluationResult]:
        """Handle SLA breach."""
        event = WorkflowEvent.sla_breach(
            workflow_id, step_id, breach_hours, escalate_to
        )
        self.emit_event(event)
        return self.process_pending_events()

    def on_fraud_alert(
        self,
        user_id: str,
        alert_type: str,
        confidence: float,
        details: Dict[str, Any]
    ) -> List[ReEvaluationResult]:
        """Handle fraud alert."""
        event = WorkflowEvent.fraud_alert(
            user_id, alert_type, confidence, details
        )
        self.emit_event(event)
        return self.process_pending_events()

    def on_user_terminated(
        self,
        user_id: str,
        effective_date: datetime,
        reason: str
    ) -> List[ReEvaluationResult]:
        """Handle user termination."""
        event = WorkflowEvent(
            event_type=EventType.USER_TERMINATED,
            priority=EventPriority.CRITICAL,
            source=EventSource.EXTERNAL_SYSTEM,
            user_id=user_id,
            payload={
                "effective_date": effective_date.isoformat(),
                "reason": reason,
            }
        )
        self.emit_event(event)
        return self.process_pending_events()

    def on_approval_received(
        self,
        workflow_id: str,
        step_id: str,
        item_id: Optional[str],
        approver_id: str
    ) -> List[ReEvaluationResult]:
        """Handle approval received."""
        event = WorkflowEvent(
            event_type=EventType.APPROVAL_RECEIVED,
            priority=EventPriority.NORMAL,
            source=EventSource.USER_ACTION,
            workflow_id=workflow_id,
            step_id=step_id,
            item_id=item_id,
            payload={"approver_id": approver_id}
        )
        self.emit_event(event)
        return self.process_pending_events()


# ============================================================
# KAFKA INTEGRATION (OPTIONAL)
# ============================================================

class KafkaEventAdapter:
    """
    Adapter for Kafka event streams.

    Bridges external Kafka topics to the internal event bus.
    """

    def __init__(
        self,
        engine: ReEvaluationEngine,
        topic_mappings: Optional[Dict[str, EventType]] = None
    ):
        self.engine = engine
        self.topic_mappings = topic_mappings or self._default_topic_mappings()
        self._running = False

    def _default_topic_mappings(self) -> Dict[str, EventType]:
        """Default Kafka topic to event type mappings."""
        return {
            "risk.score.changed": EventType.RISK_SCORE_CHANGED,
            "risk.sod.detected": EventType.SOD_CONFLICT_DETECTED,
            "fraud.alert": EventType.FRAUD_ALERT,
            "user.terminated": EventType.USER_TERMINATED,
            "user.role.changed": EventType.USER_ROLE_CHANGED,
            "control.failed": EventType.CONTROL_FAILURE,
            "system.unavailable": EventType.SYSTEM_UNAVAILABLE,
        }

    def on_kafka_message(self, topic: str, message: Dict[str, Any]) -> None:
        """
        Process incoming Kafka message.

        Called by Kafka consumer integration.
        """
        event_type = self.topic_mappings.get(topic, EventType.CUSTOM)

        event = WorkflowEvent(
            event_type=event_type,
            source=EventSource.KAFKA,
            request_id=message.get("request_id"),
            item_id=message.get("item_id"),
            user_id=message.get("user_id"),
            payload=message.get("payload", message),
            correlation_id=message.get("correlation_id"),
        )

        # Set priority based on event type
        if event_type in [EventType.FRAUD_ALERT, EventType.USER_TERMINATED]:
            event.priority = EventPriority.CRITICAL
        elif event_type in [EventType.RISK_SCORE_CHANGED, EventType.SOD_CONFLICT_DETECTED]:
            event.priority = EventPriority.HIGH

        self.engine.emit_event(event)

    def process_batch(self, messages: List[tuple]) -> List[ReEvaluationResult]:
        """
        Process a batch of Kafka messages.

        Args:
            messages: List of (topic, message) tuples
        """
        for topic, message in messages:
            self.on_kafka_message(topic, message)

        return self.engine.process_pending_events()


# ============================================================
# WEBHOOK INTEGRATION (OPTIONAL)
# ============================================================

class WebhookEventAdapter:
    """
    Adapter for webhook-based events.

    Receives events from external systems via HTTP webhooks.
    """

    def __init__(
        self,
        engine: ReEvaluationEngine,
        webhook_config: Optional[Dict[str, Any]] = None
    ):
        self.engine = engine
        self.config = webhook_config or {}
        self._webhook_secrets: Dict[str, str] = self.config.get("secrets", {})

    def validate_webhook(self, source: str, signature: str, payload: str) -> bool:
        """Validate webhook signature."""
        import hmac
        import hashlib

        secret = self._webhook_secrets.get(source)
        if not secret:
            return False

        expected = hmac.new(
            secret.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(signature, expected)

    def on_webhook_received(
        self,
        source: str,
        event_type_str: str,
        payload: Dict[str, Any]
    ) -> List[ReEvaluationResult]:
        """
        Process incoming webhook.

        Args:
            source: The webhook source identifier
            event_type_str: String event type from webhook
            payload: Webhook payload
        """
        # Map string to EventType
        try:
            event_type = EventType(event_type_str)
        except ValueError:
            event_type = EventType.CUSTOM

        event = WorkflowEvent(
            event_type=event_type,
            source=EventSource.WEBHOOK,
            request_id=payload.get("request_id"),
            item_id=payload.get("item_id"),
            user_id=payload.get("user_id"),
            workflow_id=payload.get("workflow_id"),
            payload=payload,
            correlation_id=payload.get("correlation_id"),
        )

        self.engine.emit_event(event)
        return self.engine.process_pending_events()


# ============================================================
# SCHEDULED RE-EVALUATION
# ============================================================

class ScheduledReEvaluator:
    """
    Runs periodic re-evaluation checks.

    For things that need continuous monitoring:
    - SLA tracking
    - Risk score updates
    - Stale workflow detection
    """

    def __init__(
        self,
        engine: ReEvaluationEngine,
        check_interval_seconds: int = 60
    ):
        self.engine = engine
        self.check_interval = check_interval_seconds
        self._running = False
        self._checks: List[Callable] = []

    def register_check(self, check: Callable[[], List[WorkflowEvent]]) -> None:
        """Register a periodic check that may emit events."""
        self._checks.append(check)

    def run_checks(self) -> List[ReEvaluationResult]:
        """Run all registered checks."""
        for check in self._checks:
            try:
                events = check()
                for event in events:
                    self.engine.emit_event(event)
            except Exception as e:
                logger.error(f"Check failed: {e}")

        return self.engine.process_pending_events()

    async def start_async(self) -> None:
        """Start async periodic checking."""
        self._running = True
        while self._running:
            self.run_checks()
            await asyncio.sleep(self.check_interval)

    def stop(self) -> None:
        """Stop periodic checking."""
        self._running = False


# ============================================================
# EXAMPLE USAGE
# ============================================================

def create_default_engine() -> ReEvaluationEngine:
    """Create engine with default configuration."""
    engine = ReEvaluationEngine()

    # Register action executors
    engine.register_action_executor(
        ReEvaluationAction.HOLD_WORKFLOW,
        lambda r, c: logger.info(f"Holding workflow for event {r.event_id}")
    )
    engine.register_action_executor(
        ReEvaluationAction.NOTIFY_SECURITY,
        lambda r, c: logger.info(f"Notifying security for event {r.event_id}")
    )
    engine.register_action_executor(
        ReEvaluationAction.ADD_APPROVAL_STEP,
        lambda r, c: logger.info(f"Adding approval step for event {r.event_id}")
    )
    engine.register_action_executor(
        ReEvaluationAction.ESCALATE_STEP,
        lambda r, c: logger.info(f"Escalating step for event {r.event_id}")
    )

    return engine
