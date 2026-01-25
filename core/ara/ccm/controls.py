# Control Definitions
# Controls as code for continuous monitoring

"""
Control Models for CCM.

Controls are defined as code/configuration and evaluated continuously.
Each control specifies:
- What to check (assertion)
- How often (frequency)
- What evidence to collect
- What action to take on failure
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Set
from datetime import datetime
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class ControlType(Enum):
    """Types of controls."""
    PREVENTIVE = "PREVENTIVE"  # Block before it happens
    DETECTIVE = "DETECTIVE"  # Detect after it happens
    CORRECTIVE = "CORRECTIVE"  # Fix after detection
    COMPENSATING = "COMPENSATING"  # Alternate control


class ControlFrequency(Enum):
    """How often to evaluate the control."""
    REAL_TIME = "REAL_TIME"  # On every event
    HOURLY = "HOURLY"
    DAILY = "DAILY"
    WEEKLY = "WEEKLY"
    MONTHLY = "MONTHLY"


class ControlStatus(Enum):
    """Current status of a control."""
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    DISABLED = "DISABLED"
    FAILED = "FAILED"  # Control evaluation itself failed


class AssertionType(Enum):
    """Types of control assertions."""
    MUST_NOT_EXIST = "MUST_NOT_EXIST"  # Condition must not be true
    MUST_EXIST = "MUST_EXIST"  # Condition must be true
    COUNT_LESS_THAN = "COUNT_LESS_THAN"
    COUNT_EQUALS = "COUNT_EQUALS"
    COUNT_GREATER_THAN = "COUNT_GREATER_THAN"
    ALL_MATCH = "ALL_MATCH"
    NONE_MATCH = "NONE_MATCH"


@dataclass
class ControlAssertion:
    """
    The condition that the control checks.

    Examples:
    - User must not have both CREATE_VENDOR and EXECUTE_PAYMENT
    - No user should have more than 5 sensitive privileges
    - All firefighter sessions must be logged
    """
    assertion_type: AssertionType
    target: str  # What to check (e.g., "user.actions", "role.privileges")
    condition: Dict[str, Any] = field(default_factory=dict)
    threshold: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "assertion_type": self.assertion_type.value,
            "target": self.target,
            "condition": self.condition,
            "threshold": self.threshold,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ControlAssertion":
        return cls(
            assertion_type=AssertionType(data["assertion_type"]),
            target=data["target"],
            condition=data.get("condition", {}),
            threshold=data.get("threshold"),
        )


@dataclass
class ControlEvidence:
    """
    Evidence collected when control is evaluated.

    Provides audit trail for control effectiveness.
    """
    evidence_id: str
    control_id: str
    evaluation_time: datetime = field(default_factory=datetime.now)

    # Result
    passed: bool = True
    violation_found: bool = False

    # Details
    entities_checked: int = 0
    violations_count: int = 0
    violation_details: List[Dict[str, Any]] = field(default_factory=list)

    # Data sources used
    data_sources: List[str] = field(default_factory=list)

    # Retention
    retention_days: int = 365

    def to_dict(self) -> Dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "control_id": self.control_id,
            "evaluation_time": self.evaluation_time.isoformat(),
            "passed": self.passed,
            "violation_found": self.violation_found,
            "entities_checked": self.entities_checked,
            "violations_count": self.violations_count,
            "violation_details": self.violation_details,
            "data_sources": self.data_sources,
        }


@dataclass
class Control:
    """
    A continuous control definition.

    Controls are evaluated continuously based on their frequency
    and generate evidence for audit.
    """
    control_id: str
    name: str
    description: str

    # Classification
    control_type: ControlType = ControlType.DETECTIVE
    frequency: ControlFrequency = ControlFrequency.DAILY

    # Ownership
    control_owner: str = ""
    business_process: str = ""

    # Assertion - what to check
    assertion: Optional[ControlAssertion] = None

    # For simple assertions, direct config
    must_not_exist_actions: Set[str] = field(default_factory=set)
    must_exist_conditions: List[Dict[str, Any]] = field(default_factory=list)

    # Evidence configuration
    data_sources: List[str] = field(default_factory=list)
    retention_days: int = 365

    # Alerting
    alert_on_failure: bool = True
    alert_recipients: List[str] = field(default_factory=list)
    severity_on_failure: str = "HIGH"

    # Remediation
    auto_remediate: bool = False
    remediation_action: str = ""

    # Regulatory reference
    regulatory_references: List[str] = field(default_factory=list)
    control_objective: str = ""

    # Status
    status: ControlStatus = ControlStatus.ACTIVE
    last_evaluation: Optional[datetime] = None
    last_result: Optional[bool] = None

    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    created_by: str = "SYSTEM"
    version: str = "1.0"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "control_id": self.control_id,
            "name": self.name,
            "description": self.description,
            "control_type": self.control_type.value,
            "frequency": self.frequency.value,
            "control_owner": self.control_owner,
            "business_process": self.business_process,
            "assertion": self.assertion.to_dict() if self.assertion else None,
            "must_not_exist_actions": list(self.must_not_exist_actions),
            "must_exist_conditions": self.must_exist_conditions,
            "data_sources": self.data_sources,
            "retention_days": self.retention_days,
            "alert_on_failure": self.alert_on_failure,
            "alert_recipients": self.alert_recipients,
            "severity_on_failure": self.severity_on_failure,
            "auto_remediate": self.auto_remediate,
            "remediation_action": self.remediation_action,
            "regulatory_references": self.regulatory_references,
            "control_objective": self.control_objective,
            "status": self.status.value,
            "last_evaluation": self.last_evaluation.isoformat() if self.last_evaluation else None,
            "last_result": self.last_result,
            "version": self.version,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Control":
        assertion = None
        if data.get("assertion"):
            assertion = ControlAssertion.from_dict(data["assertion"])

        return cls(
            control_id=data["control_id"],
            name=data["name"],
            description=data.get("description", ""),
            control_type=ControlType(data.get("control_type", "DETECTIVE")),
            frequency=ControlFrequency(data.get("frequency", "DAILY")),
            control_owner=data.get("control_owner", ""),
            business_process=data.get("business_process", ""),
            assertion=assertion,
            must_not_exist_actions=set(data.get("must_not_exist_actions", [])),
            must_exist_conditions=data.get("must_exist_conditions", []),
            data_sources=data.get("data_sources", []),
            retention_days=data.get("retention_days", 365),
            alert_on_failure=data.get("alert_on_failure", True),
            alert_recipients=data.get("alert_recipients", []),
            severity_on_failure=data.get("severity_on_failure", "HIGH"),
            auto_remediate=data.get("auto_remediate", False),
            remediation_action=data.get("remediation_action", ""),
            regulatory_references=data.get("regulatory_references", []),
            control_objective=data.get("control_objective", ""),
            status=ControlStatus(data.get("status", "ACTIVE")),
        )

    @classmethod
    def from_yaml(cls, yaml_content: str) -> "Control":
        """Load control from YAML."""
        try:
            import yaml
            data = yaml.safe_load(yaml_content)
            return cls.from_dict(data)
        except ImportError:
            raise ImportError("PyYAML required for YAML parsing")

    def to_yaml(self) -> str:
        """Export control to YAML."""
        try:
            import yaml
            return yaml.dump(self.to_dict(), default_flow_style=False)
        except ImportError:
            raise ImportError("PyYAML required for YAML export")
