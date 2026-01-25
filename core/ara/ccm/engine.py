# Control Evaluation Engine
# Evaluates controls against live data

"""
Control Evaluation Engine for CCM.

Evaluates controls continuously and generates:
- Pass/fail results
- Violation details
- Evidence for audit
- Alerts on failure
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable, Set
from datetime import datetime
import logging
import uuid

from .controls import (
    Control,
    ControlType,
    ControlStatus,
    ControlAssertion,
    ControlEvidence,
    AssertionType,
)

logger = logging.getLogger(__name__)


@dataclass
class ControlViolation:
    """A specific violation found during control evaluation."""
    violation_id: str
    control_id: str
    entity_id: str  # User, role, or system that violated
    entity_type: str

    # Violation details
    violation_type: str
    description: str
    severity: str = "HIGH"

    # Evidence
    violating_values: List[Any] = field(default_factory=list)
    expected_condition: str = ""
    actual_condition: str = ""

    # Impact
    risk_impact: str = ""
    affected_users: int = 0

    # Resolution
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None
    resolution_notes: str = ""

    # Timestamps
    detected_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "violation_id": self.violation_id,
            "control_id": self.control_id,
            "entity_id": self.entity_id,
            "entity_type": self.entity_type,
            "violation_type": self.violation_type,
            "description": self.description,
            "severity": self.severity,
            "violating_values": self.violating_values,
            "expected_condition": self.expected_condition,
            "actual_condition": self.actual_condition,
            "risk_impact": self.risk_impact,
            "affected_users": self.affected_users,
            "resolved": self.resolved,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "resolved_by": self.resolved_by,
            "resolution_notes": self.resolution_notes,
            "detected_at": self.detected_at.isoformat(),
        }


@dataclass
class ControlEvaluationResult:
    """Result of evaluating a control."""
    control_id: str
    control_name: str
    evaluation_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])

    # Result
    passed: bool = True
    status: str = "PASS"  # PASS, FAIL, ERROR, SKIPPED

    # Metrics
    entities_checked: int = 0
    violations_found: int = 0
    violations: List[ControlViolation] = field(default_factory=list)

    # Evidence
    evidence: Optional[ControlEvidence] = None

    # Timing
    evaluation_started: datetime = field(default_factory=datetime.now)
    evaluation_completed: Optional[datetime] = None
    duration_ms: int = 0

    # Error handling
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "control_id": self.control_id,
            "control_name": self.control_name,
            "evaluation_id": self.evaluation_id,
            "passed": self.passed,
            "status": self.status,
            "entities_checked": self.entities_checked,
            "violations_found": self.violations_found,
            "violations": [v.to_dict() for v in self.violations],
            "evaluation_started": self.evaluation_started.isoformat(),
            "evaluation_completed": self.evaluation_completed.isoformat() if self.evaluation_completed else None,
            "duration_ms": self.duration_ms,
            "error_message": self.error_message,
        }


@dataclass
class ControlConfig:
    """Configuration for control evaluation."""
    # Execution
    max_entities_per_evaluation: int = 10000
    timeout_seconds: int = 300
    parallel_evaluations: int = 4

    # Evidence
    store_evidence: bool = True
    evidence_retention_days: int = 365

    # Alerting
    alert_on_failure: bool = True
    alert_cooldown_minutes: int = 60  # Don't re-alert within this period


class ControlEngine:
    """
    Evaluates controls against context data.

    Key capabilities:
    - Evaluate single controls or batches
    - Generate violations and evidence
    - Support for custom evaluation functions
    - Real-time and scheduled evaluation
    """

    def __init__(self, config: Optional[ControlConfig] = None):
        """
        Initialize control engine.

        Args:
            config: Engine configuration
        """
        self.config = config or ControlConfig()
        self._controls: Dict[str, Control] = {}
        self._custom_evaluators: Dict[str, Callable] = {}
        self._violation_counter = 0

    def register_control(self, control: Control):
        """Register a control for evaluation."""
        self._controls[control.control_id] = control
        logger.info(f"Registered control: {control.control_id}")

    def register_evaluator(
        self,
        control_id: str,
        evaluator: Callable[[Control, Dict[str, Any]], List[ControlViolation]]
    ):
        """Register a custom evaluator function for a control."""
        self._custom_evaluators[control_id] = evaluator

    def evaluate(
        self,
        control: Control,
        context: Dict[str, Any]
    ) -> ControlEvaluationResult:
        """
        Evaluate a control against context.

        Args:
            control: Control to evaluate
            context: Data context containing entities to check

        Returns:
            ControlEvaluationResult with pass/fail and violations
        """
        start_time = datetime.now()

        result = ControlEvaluationResult(
            control_id=control.control_id,
            control_name=control.name,
            evaluation_started=start_time,
        )

        try:
            # Check if control is active
            if control.status != ControlStatus.ACTIVE:
                result.status = "SKIPPED"
                result.error_message = f"Control status is {control.status.value}"
                return result

            # Use custom evaluator if registered
            if control.control_id in self._custom_evaluators:
                violations = self._custom_evaluators[control.control_id](control, context)
            else:
                violations = self._evaluate_control(control, context)

            result.violations = violations
            result.violations_found = len(violations)
            result.passed = len(violations) == 0
            result.status = "PASS" if result.passed else "FAIL"

            # Count entities checked
            result.entities_checked = context.get("entity_count", 0)

            # Generate evidence
            if self.config.store_evidence:
                result.evidence = self._generate_evidence(control, result)

        except Exception as e:
            logger.error(f"Control evaluation error: {e}")
            result.status = "ERROR"
            result.error_message = str(e)
            result.passed = False

        # Complete timing
        result.evaluation_completed = datetime.now()
        result.duration_ms = int(
            (result.evaluation_completed - start_time).total_seconds() * 1000
        )

        # Update control last evaluation
        control.last_evaluation = result.evaluation_completed
        control.last_result = result.passed

        return result

    def _evaluate_control(
        self,
        control: Control,
        context: Dict[str, Any]
    ) -> List[ControlViolation]:
        """Core control evaluation logic."""
        violations = []

        # Simple must_not_exist check
        if control.must_not_exist_actions:
            violations.extend(
                self._check_must_not_exist(control, context)
            )

        # Assertion-based evaluation
        if control.assertion:
            violations.extend(
                self._evaluate_assertion(control, control.assertion, context)
            )

        return violations

    def _check_must_not_exist(
        self,
        control: Control,
        context: Dict[str, Any]
    ) -> List[ControlViolation]:
        """Check that forbidden actions do not exist together."""
        violations = []
        forbidden = control.must_not_exist_actions

        # Check each entity in context
        entities = context.get("entities", [])

        for entity in entities:
            entity_id = entity.get("id", "unknown")
            entity_actions = set(entity.get("actions", []))

            # Check if entity has all forbidden actions
            if forbidden.issubset(entity_actions):
                self._violation_counter += 1
                violation = ControlViolation(
                    violation_id=f"V-{control.control_id}-{self._violation_counter}",
                    control_id=control.control_id,
                    entity_id=entity_id,
                    entity_type=entity.get("type", "USER"),
                    violation_type="FORBIDDEN_COMBINATION",
                    description=f"Entity has forbidden action combination",
                    severity=control.severity_on_failure,
                    violating_values=list(forbidden),
                    expected_condition=f"Should NOT have: {forbidden}",
                    actual_condition=f"Has: {entity_actions & forbidden}",
                )
                violations.append(violation)

        return violations

    def _evaluate_assertion(
        self,
        control: Control,
        assertion: ControlAssertion,
        context: Dict[str, Any]
    ) -> List[ControlViolation]:
        """Evaluate a control assertion."""
        violations = []
        entities = context.get("entities", [])

        for entity in entities:
            entity_id = entity.get("id", "unknown")

            # Get target value from entity
            target_value = self._get_nested_value(entity, assertion.target)

            if assertion.assertion_type == AssertionType.MUST_NOT_EXIST:
                forbidden = set(assertion.condition.get("actions", []))
                if isinstance(target_value, (list, set)):
                    if forbidden.issubset(set(target_value)):
                        violations.append(self._create_violation(
                            control, entity_id, entity.get("type", "USER"),
                            "MUST_NOT_EXIST_VIOLATION",
                            f"Has forbidden values: {forbidden}",
                            target_value,
                        ))

            elif assertion.assertion_type == AssertionType.COUNT_LESS_THAN:
                if target_value and len(target_value) >= assertion.threshold:
                    violations.append(self._create_violation(
                        control, entity_id, entity.get("type", "USER"),
                        "COUNT_EXCEEDED",
                        f"Count {len(target_value)} exceeds threshold {assertion.threshold}",
                        target_value,
                    ))

            elif assertion.assertion_type == AssertionType.MUST_EXIST:
                required = assertion.condition.get("required", [])
                if isinstance(target_value, (list, set)):
                    if not set(required).issubset(set(target_value)):
                        violations.append(self._create_violation(
                            control, entity_id, entity.get("type", "USER"),
                            "MUST_EXIST_MISSING",
                            f"Missing required values: {set(required) - set(target_value)}",
                            target_value,
                        ))

        return violations

    def _get_nested_value(self, obj: Dict, path: str) -> Any:
        """Get nested value from dict using dot notation."""
        parts = path.split(".")
        value = obj

        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            else:
                return None

        return value

    def _create_violation(
        self,
        control: Control,
        entity_id: str,
        entity_type: str,
        violation_type: str,
        description: str,
        violating_values: Any
    ) -> ControlViolation:
        """Create a violation object."""
        self._violation_counter += 1
        return ControlViolation(
            violation_id=f"V-{control.control_id}-{self._violation_counter}",
            control_id=control.control_id,
            entity_id=entity_id,
            entity_type=entity_type,
            violation_type=violation_type,
            description=description,
            severity=control.severity_on_failure,
            violating_values=list(violating_values) if isinstance(violating_values, (list, set)) else [violating_values],
        )

    def _generate_evidence(
        self,
        control: Control,
        result: ControlEvaluationResult
    ) -> ControlEvidence:
        """Generate evidence for the evaluation."""
        return ControlEvidence(
            evidence_id=f"E-{result.evaluation_id}",
            control_id=control.control_id,
            evaluation_time=result.evaluation_started,
            passed=result.passed,
            violation_found=result.violations_found > 0,
            entities_checked=result.entities_checked,
            violations_count=result.violations_found,
            violation_details=[v.to_dict() for v in result.violations[:100]],
            data_sources=control.data_sources,
            retention_days=control.retention_days,
        )

    def evaluate_all(
        self,
        context: Dict[str, Any]
    ) -> List[ControlEvaluationResult]:
        """Evaluate all registered controls."""
        results = []

        for control in self._controls.values():
            if control.status == ControlStatus.ACTIVE:
                result = self.evaluate(control, context)
                results.append(result)

        return results

    def get_control(self, control_id: str) -> Optional[Control]:
        """Get a registered control."""
        return self._controls.get(control_id)

    def get_all_controls(self) -> List[Control]:
        """Get all registered controls."""
        return list(self._controls.values())

    def get_active_controls(self) -> List[Control]:
        """Get all active controls."""
        return [c for c in self._controls.values() if c.status == ControlStatus.ACTIVE]
