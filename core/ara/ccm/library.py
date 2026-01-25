# Control Library
# Built-in controls for common governance scenarios

"""
Control Library for CCM.

Provides pre-built controls for common scenarios:
- SoD enforcement
- Firefighter monitoring
- Privilege management
- Access certification
"""

from typing import Dict, List, Optional, Any
import logging

from .controls import (
    Control,
    ControlType,
    ControlFrequency,
    ControlAssertion,
    AssertionType,
)

logger = logging.getLogger(__name__)


# Built-in controls
BUILTIN_CONTROLS = [
    # SoD Controls
    Control(
        control_id="CCM-SOD-001",
        name="Vendor Payment SoD Control",
        description="Prevents users from having both vendor creation and payment execution capabilities",
        control_type=ControlType.PREVENTIVE,
        frequency=ControlFrequency.REAL_TIME,
        control_owner="Finance Controller",
        business_process="Procure-to-Pay",
        must_not_exist_actions={"CREATE_VENDOR", "EXECUTE_PAYMENT"},
        data_sources=["AGR_1251", "USR02"],
        alert_on_failure=True,
        alert_recipients=["security_team", "finance_controller"],
        severity_on_failure="CRITICAL",
        regulatory_references=["SOX 404", "COSO IC 2013"],
        control_objective="Segregate vendor master maintenance from payment execution",
    ),
    Control(
        control_id="CCM-SOD-002",
        name="Customer Credit SoD Control",
        description="Prevents users from creating customers and modifying credit limits",
        control_type=ControlType.PREVENTIVE,
        frequency=ControlFrequency.REAL_TIME,
        control_owner="Credit Manager",
        business_process="Order-to-Cash",
        must_not_exist_actions={"CREATE_CUSTOMER", "MODIFY_CREDIT_LIMIT"},
        data_sources=["AGR_1251", "USR02"],
        alert_on_failure=True,
        severity_on_failure="HIGH",
        regulatory_references=["SOX 404"],
        control_objective="Segregate customer master from credit management",
    ),
    Control(
        control_id="CCM-SOD-003",
        name="Payroll SoD Control",
        description="Prevents users from hiring employees and executing payroll",
        control_type=ControlType.PREVENTIVE,
        frequency=ControlFrequency.REAL_TIME,
        control_owner="HR Director",
        business_process="HR/Payroll",
        must_not_exist_actions={"HIRE_EMPLOYEE", "EXECUTE_PAYROLL"},
        data_sources=["AGR_1251", "USR02"],
        alert_on_failure=True,
        severity_on_failure="CRITICAL",
        regulatory_references=["SOX 404", "IRS Guidelines"],
        control_objective="Prevent ghost employee fraud",
    ),

    # Firefighter Controls
    Control(
        control_id="CCM-FF-001",
        name="Firefighter Session Logging",
        description="Ensures all firefighter sessions are logged with full audit trail",
        control_type=ControlType.DETECTIVE,
        frequency=ControlFrequency.REAL_TIME,
        control_owner="Security Manager",
        business_process="Emergency Access",
        assertion=ControlAssertion(
            assertion_type=AssertionType.MUST_EXIST,
            target="session.audit_log",
            condition={"required": ["session_start", "session_end", "actions_performed"]},
        ),
        data_sources=["FFLOG", "SM21"],
        alert_on_failure=True,
        severity_on_failure="CRITICAL",
        control_objective="Complete audit trail for emergency access",
    ),
    Control(
        control_id="CCM-FF-002",
        name="Firefighter Session Duration",
        description="Ensures firefighter sessions do not exceed maximum duration",
        control_type=ControlType.PREVENTIVE,
        frequency=ControlFrequency.HOURLY,
        control_owner="Security Manager",
        business_process="Emergency Access",
        assertion=ControlAssertion(
            assertion_type=AssertionType.COUNT_LESS_THAN,
            target="session.duration_hours",
            threshold=8,
        ),
        data_sources=["FFLOG"],
        alert_on_failure=True,
        auto_remediate=True,
        remediation_action="TERMINATE_SESSION",
        severity_on_failure="HIGH",
        control_objective="Limit emergency access duration",
    ),

    # Privilege Controls
    Control(
        control_id="CCM-PRIV-001",
        name="Sensitive Privilege Limit",
        description="Ensures users do not exceed maximum sensitive privileges",
        control_type=ControlType.PREVENTIVE,
        frequency=ControlFrequency.DAILY,
        control_owner="Security Manager",
        business_process="Access Management",
        assertion=ControlAssertion(
            assertion_type=AssertionType.COUNT_LESS_THAN,
            target="user.sensitive_privileges",
            threshold=10,
        ),
        data_sources=["AGR_1251", "USR02"],
        alert_on_failure=True,
        severity_on_failure="HIGH",
        control_objective="Limit privilege accumulation",
    ),
    Control(
        control_id="CCM-PRIV-002",
        name="Unused Privilege Detection",
        description="Identifies privileges not used in 90 days",
        control_type=ControlType.DETECTIVE,
        frequency=ControlFrequency.WEEKLY,
        control_owner="Access Manager",
        business_process="Access Management",
        data_sources=["STAD", "AGR_1251"],
        alert_on_failure=True,
        severity_on_failure="MEDIUM",
        control_objective="Remove unnecessary access rights",
    ),

    # Access Certification Controls
    Control(
        control_id="CCM-CERT-001",
        name="Access Certification Compliance",
        description="Ensures all users have current access certification",
        control_type=ControlType.DETECTIVE,
        frequency=ControlFrequency.DAILY,
        control_owner="Compliance Manager",
        business_process="Access Governance",
        data_sources=["CERT_LOG"],
        alert_on_failure=True,
        severity_on_failure="HIGH",
        regulatory_references=["SOX 404", "ISO 27001"],
        control_objective="Regular access validation",
    ),

    # Security Controls
    Control(
        control_id="CCM-SEC-001",
        name="Debug Access Control",
        description="Prevents debug access combined with production data modification",
        control_type=ControlType.PREVENTIVE,
        frequency=ControlFrequency.REAL_TIME,
        control_owner="Basis Manager",
        business_process="Security Administration",
        must_not_exist_actions={"DEBUG_PROGRAM", "MODIFY_PRODUCTION_DATA"},
        data_sources=["AGR_1251", "USR02"],
        alert_on_failure=True,
        severity_on_failure="CRITICAL",
        control_objective="Prevent unauthorized data manipulation",
    ),
    Control(
        control_id="CCM-SEC-002",
        name="User Role Assignment Control",
        description="Prevents single user from creating users and assigning roles",
        control_type=ControlType.PREVENTIVE,
        frequency=ControlFrequency.REAL_TIME,
        control_owner="Security Manager",
        business_process="Security Administration",
        must_not_exist_actions={"CREATE_USER", "ASSIGN_ROLE"},
        data_sources=["AGR_1251", "USR02"],
        alert_on_failure=True,
        severity_on_failure="CRITICAL",
        control_objective="Prevent privilege escalation",
    ),
]


class ControlLibrary:
    """
    Library of controls.

    Provides access to built-in and custom controls.
    """

    def __init__(self):
        """Initialize with built-in controls."""
        self.controls: Dict[str, Control] = {}
        self._load_builtin_controls()

    def _load_builtin_controls(self):
        """Load built-in controls."""
        for control in BUILTIN_CONTROLS:
            self.controls[control.control_id] = control

    def add_control(self, control: Control):
        """Add a custom control."""
        self.controls[control.control_id] = control
        logger.info(f"Added control: {control.control_id}")

    def remove_control(self, control_id: str):
        """Remove a control."""
        if control_id in self.controls:
            del self.controls[control_id]

    def get_control(self, control_id: str) -> Optional[Control]:
        """Get a control by ID."""
        return self.controls.get(control_id)

    def get_all_controls(self) -> List[Control]:
        """Get all controls."""
        return list(self.controls.values())

    def get_controls_by_type(self, control_type: ControlType) -> List[Control]:
        """Get controls by type."""
        return [c for c in self.controls.values() if c.control_type == control_type]

    def get_controls_by_process(self, business_process: str) -> List[Control]:
        """Get controls by business process."""
        return [
            c for c in self.controls.values()
            if business_process.lower() in c.business_process.lower()
        ]

    def get_real_time_controls(self) -> List[Control]:
        """Get controls that run in real-time."""
        return [
            c for c in self.controls.values()
            if c.frequency == ControlFrequency.REAL_TIME
        ]

    def load_from_yaml(self, yaml_content: str):
        """Load controls from YAML content."""
        try:
            import yaml
            data = yaml.safe_load(yaml_content)
            for control_data in data.get("controls", []):
                control = Control.from_dict(control_data)
                self.controls[control.control_id] = control
        except ImportError:
            logger.warning("PyYAML not available")
        except Exception as e:
            logger.error(f"Error loading controls: {e}")

    def export_to_yaml(self) -> str:
        """Export controls to YAML format."""
        try:
            import yaml
            data = {"controls": [c.to_dict() for c in self.controls.values()]}
            return yaml.dump(data, default_flow_style=False)
        except ImportError:
            logger.warning("PyYAML not available")
            return ""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize library."""
        return {
            "controls": [c.to_dict() for c in self.controls.values()],
            "count": len(self.controls),
        }
