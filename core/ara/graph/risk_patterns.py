# Risk Patterns for Graph-Based SoD Detection
# Define forbidden action combinations as patterns

"""
Risk Patterns replace static SoD pairs.

Instead of:
    "FK01 conflicts with F-53"

We define:
    "Any path that enables both CREATE_VENDOR and EXECUTE_PAYMENT"

This catches indirect violations through role combinations.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional, Any
from enum import Enum
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class PatternSeverity(Enum):
    """Severity levels for risk patterns."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class PatternType(Enum):
    """Types of risk patterns."""
    SOD = "SOD"  # Segregation of duties violation
    SENSITIVE = "SENSITIVE"  # Sensitive access pattern
    ESCALATION = "ESCALATION"  # Privilege escalation path
    FRAUD = "FRAUD"  # Fraud-enabling pattern
    COMPLIANCE = "COMPLIANCE"  # Regulatory compliance pattern


@dataclass
class RiskPattern:
    """
    Definition of a risk pattern.

    A pattern matches when a user can reach all forbidden actions
    through any combination of roles and privileges.
    """
    pattern_id: str
    name: str
    description: str
    pattern_type: PatternType = PatternType.SOD
    severity: PatternSeverity = PatternSeverity.HIGH

    # Forbidden actions - user must NOT be able to reach ALL of these
    forbidden_actions: Set[str] = field(default_factory=set)

    # Optional: specific roles that trigger this pattern
    trigger_roles: Set[str] = field(default_factory=set)

    # Optional: specific tcodes that trigger this pattern
    trigger_tcodes: Set[str] = field(default_factory=set)

    # Risk scoring
    base_risk_score: int = 75

    # Business context
    business_process: str = ""
    regulatory_reference: str = ""
    control_objective: str = ""

    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    created_by: str = "SYSTEM"
    is_active: bool = True

    def matches_actions(self, user_actions: Set[str]) -> bool:
        """Check if user's actions match this pattern."""
        return self.forbidden_actions.issubset(user_actions)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pattern_id": self.pattern_id,
            "name": self.name,
            "description": self.description,
            "pattern_type": self.pattern_type.value,
            "severity": self.severity.value,
            "forbidden_actions": list(self.forbidden_actions),
            "trigger_roles": list(self.trigger_roles),
            "trigger_tcodes": list(self.trigger_tcodes),
            "base_risk_score": self.base_risk_score,
            "business_process": self.business_process,
            "regulatory_reference": self.regulatory_reference,
            "control_objective": self.control_objective,
            "is_active": self.is_active,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RiskPattern":
        return cls(
            pattern_id=data["pattern_id"],
            name=data["name"],
            description=data["description"],
            pattern_type=PatternType(data.get("pattern_type", "SOD")),
            severity=PatternSeverity(data.get("severity", "HIGH")),
            forbidden_actions=set(data.get("forbidden_actions", [])),
            trigger_roles=set(data.get("trigger_roles", [])),
            trigger_tcodes=set(data.get("trigger_tcodes", [])),
            base_risk_score=data.get("base_risk_score", 75),
            business_process=data.get("business_process", ""),
            regulatory_reference=data.get("regulatory_reference", ""),
            control_objective=data.get("control_objective", ""),
            is_active=data.get("is_active", True),
        )


# Built-in risk patterns for common SoD violations
BUILTIN_RISK_PATTERNS = [
    # Procure-to-Pay (P2P) Patterns
    RiskPattern(
        pattern_id="GRAPH-P2P-001",
        name="Vendor Creation + Payment Execution",
        description="User can create vendors and execute payments, enabling ghost vendor fraud",
        pattern_type=PatternType.FRAUD,
        severity=PatternSeverity.CRITICAL,
        forbidden_actions={"CREATE_VENDOR", "EXECUTE_PAYMENT"},
        trigger_tcodes={"FK01", "XK01", "F-53", "F110"},
        base_risk_score=95,
        business_process="Procure-to-Pay",
        control_objective="Segregate vendor master maintenance from payment execution",
    ),
    RiskPattern(
        pattern_id="GRAPH-P2P-002",
        name="Vendor Creation + Invoice Entry",
        description="User can create vendors and enter invoices",
        pattern_type=PatternType.SOD,
        severity=PatternSeverity.HIGH,
        forbidden_actions={"CREATE_VENDOR", "ENTER_INVOICE"},
        trigger_tcodes={"FK01", "XK01", "FB60", "MIRO"},
        base_risk_score=85,
        business_process="Procure-to-Pay",
        control_objective="Segregate vendor master maintenance from invoice processing",
    ),
    RiskPattern(
        pattern_id="GRAPH-P2P-003",
        name="Purchase Order + Goods Receipt",
        description="User can create POs and post goods receipts",
        pattern_type=PatternType.SOD,
        severity=PatternSeverity.HIGH,
        forbidden_actions={"CREATE_PO", "POST_GOODS_RECEIPT"},
        trigger_tcodes={"ME21N", "ME22N", "MIGO"},
        base_risk_score=80,
        business_process="Procure-to-Pay",
        control_objective="Segregate purchasing from receiving",
    ),
    RiskPattern(
        pattern_id="GRAPH-P2P-004",
        name="Full P2P Cycle",
        description="User can perform complete procure-to-pay cycle",
        pattern_type=PatternType.FRAUD,
        severity=PatternSeverity.CRITICAL,
        forbidden_actions={"CREATE_VENDOR", "CREATE_PO", "POST_GOODS_RECEIPT", "EXECUTE_PAYMENT"},
        base_risk_score=100,
        business_process="Procure-to-Pay",
        control_objective="Prevent single-user completion of entire P2P cycle",
    ),

    # Order-to-Cash (O2C) Patterns
    RiskPattern(
        pattern_id="GRAPH-O2C-001",
        name="Customer Creation + Credit Limit",
        description="User can create customers and modify credit limits",
        pattern_type=PatternType.SOD,
        severity=PatternSeverity.HIGH,
        forbidden_actions={"CREATE_CUSTOMER", "MODIFY_CREDIT_LIMIT"},
        trigger_tcodes={"FD01", "XD01", "FD32"},
        base_risk_score=80,
        business_process="Order-to-Cash",
        control_objective="Segregate customer master from credit management",
    ),
    RiskPattern(
        pattern_id="GRAPH-O2C-002",
        name="Sales Order + Billing",
        description="User can create sales orders and process billing",
        pattern_type=PatternType.SOD,
        severity=PatternSeverity.MEDIUM,
        forbidden_actions={"CREATE_SALES_ORDER", "PROCESS_BILLING"},
        trigger_tcodes={"VA01", "VF01"},
        base_risk_score=65,
        business_process="Order-to-Cash",
        control_objective="Segregate order entry from billing",
    ),

    # Finance Patterns
    RiskPattern(
        pattern_id="GRAPH-FIN-001",
        name="GL Posting + Bank Reconciliation",
        description="User can post GL entries and reconcile bank accounts",
        pattern_type=PatternType.SOD,
        severity=PatternSeverity.HIGH,
        forbidden_actions={"POST_GL_ENTRY", "RECONCILE_BANK"},
        trigger_tcodes={"FB01", "FB50", "FF67", "FEBAN"},
        base_risk_score=85,
        business_process="Finance",
        control_objective="Segregate journal posting from bank reconciliation",
    ),
    RiskPattern(
        pattern_id="GRAPH-FIN-002",
        name="Asset Acquisition + Asset Retirement",
        description="User can acquire and retire assets",
        pattern_type=PatternType.SOD,
        severity=PatternSeverity.MEDIUM,
        forbidden_actions={"ACQUIRE_ASSET", "RETIRE_ASSET"},
        trigger_tcodes={"AS01", "ABAVN"},
        base_risk_score=70,
        business_process="Finance",
        control_objective="Segregate asset lifecycle management",
    ),

    # HR/Payroll Patterns
    RiskPattern(
        pattern_id="GRAPH-HR-001",
        name="Employee Hiring + Payroll Run",
        description="User can hire employees and execute payroll",
        pattern_type=PatternType.FRAUD,
        severity=PatternSeverity.CRITICAL,
        forbidden_actions={"HIRE_EMPLOYEE", "EXECUTE_PAYROLL"},
        trigger_tcodes={"PA40", "PC00_M99_CALC"},
        base_risk_score=95,
        business_process="HR/Payroll",
        control_objective="Prevent ghost employee fraud",
    ),
    RiskPattern(
        pattern_id="GRAPH-HR-002",
        name="Salary Change + Payroll Run",
        description="User can change salaries and execute payroll",
        pattern_type=PatternType.SOD,
        severity=PatternSeverity.HIGH,
        forbidden_actions={"CHANGE_SALARY", "EXECUTE_PAYROLL"},
        trigger_tcodes={"PA30", "PC00_M99_CALC"},
        base_risk_score=85,
        business_process="HR/Payroll",
        control_objective="Segregate salary maintenance from payroll execution",
    ),

    # Basis/Security Patterns
    RiskPattern(
        pattern_id="GRAPH-SEC-001",
        name="User Creation + Role Assignment",
        description="User can create users and assign roles",
        pattern_type=PatternType.ESCALATION,
        severity=PatternSeverity.CRITICAL,
        forbidden_actions={"CREATE_USER", "ASSIGN_ROLE"},
        trigger_tcodes={"SU01", "PFCG", "SU10"},
        base_risk_score=95,
        business_process="Security Administration",
        control_objective="Segregate user management from role assignment",
    ),
    RiskPattern(
        pattern_id="GRAPH-SEC-002",
        name="Role Modification + Transport Release",
        description="User can modify roles and release transports",
        pattern_type=PatternType.ESCALATION,
        severity=PatternSeverity.HIGH,
        forbidden_actions={"MODIFY_ROLE", "RELEASE_TRANSPORT"},
        trigger_tcodes={"PFCG", "SE09", "SE10"},
        base_risk_score=85,
        business_process="Security Administration",
        control_objective="Prevent unauthorized role deployment",
    ),
    RiskPattern(
        pattern_id="GRAPH-SEC-003",
        name="Debug + Production Modify",
        description="User can debug and modify production data",
        pattern_type=PatternType.ESCALATION,
        severity=PatternSeverity.CRITICAL,
        forbidden_actions={"DEBUG_PROGRAM", "MODIFY_PRODUCTION_DATA"},
        trigger_tcodes={"SE38", "SA38", "SE16N"},
        base_risk_score=100,
        business_process="Basis Administration",
        control_objective="Prevent unauthorized data manipulation",
    ),
]


class RiskPatternLibrary:
    """
    Library of risk patterns for graph-based detection.

    Manages patterns and provides lookup capabilities.
    """

    def __init__(self):
        """Initialize with built-in patterns."""
        self.patterns: Dict[str, RiskPattern] = {}
        self._load_builtin_patterns()

    def _load_builtin_patterns(self):
        """Load built-in patterns."""
        for pattern in BUILTIN_RISK_PATTERNS:
            self.patterns[pattern.pattern_id] = pattern

    def add_pattern(self, pattern: RiskPattern):
        """Add a custom pattern."""
        self.patterns[pattern.pattern_id] = pattern
        logger.info(f"Added pattern: {pattern.pattern_id}")

    def remove_pattern(self, pattern_id: str):
        """Remove a pattern."""
        if pattern_id in self.patterns:
            del self.patterns[pattern_id]

    def get_pattern(self, pattern_id: str) -> Optional[RiskPattern]:
        """Get a pattern by ID."""
        return self.patterns.get(pattern_id)

    def get_active_patterns(self) -> List[RiskPattern]:
        """Get all active patterns."""
        return [p for p in self.patterns.values() if p.is_active]

    def get_patterns_by_type(self, pattern_type: PatternType) -> List[RiskPattern]:
        """Get patterns by type."""
        return [
            p for p in self.patterns.values()
            if p.pattern_type == pattern_type and p.is_active
        ]

    def get_patterns_by_severity(self, min_severity: PatternSeverity) -> List[RiskPattern]:
        """Get patterns at or above a severity level."""
        severity_order = [
            PatternSeverity.LOW,
            PatternSeverity.MEDIUM,
            PatternSeverity.HIGH,
            PatternSeverity.CRITICAL
        ]
        min_index = severity_order.index(min_severity)

        return [
            p for p in self.patterns.values()
            if p.is_active and severity_order.index(p.severity) >= min_index
        ]

    def get_patterns_by_business_process(self, process: str) -> List[RiskPattern]:
        """Get patterns for a business process."""
        return [
            p for p in self.patterns.values()
            if p.is_active and process.lower() in p.business_process.lower()
        ]

    def find_matching_patterns(self, user_actions: Set[str]) -> List[RiskPattern]:
        """Find all patterns that match a user's actions."""
        return [
            p for p in self.patterns.values()
            if p.is_active and p.matches_actions(user_actions)
        ]

    def to_dict(self) -> Dict[str, Any]:
        """Serialize library to dictionary."""
        return {
            "patterns": [p.to_dict() for p in self.patterns.values()],
            "count": len(self.patterns),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RiskPatternLibrary":
        """Deserialize library from dictionary."""
        library = cls()
        library.patterns.clear()

        for pattern_data in data.get("patterns", []):
            pattern = RiskPattern.from_dict(pattern_data)
            library.patterns[pattern.pattern_id] = pattern

        return library

    def load_from_yaml(self, yaml_content: str):
        """Load patterns from YAML content."""
        try:
            import yaml
            data = yaml.safe_load(yaml_content)
            for pattern_data in data.get("patterns", []):
                pattern = RiskPattern.from_dict(pattern_data)
                self.patterns[pattern.pattern_id] = pattern
        except ImportError:
            logger.warning("PyYAML not available, cannot load YAML patterns")
        except Exception as e:
            logger.error(f"Error loading YAML patterns: {e}")

    def export_to_yaml(self) -> str:
        """Export patterns to YAML format."""
        try:
            import yaml
            data = {"patterns": [p.to_dict() for p in self.patterns.values()]}
            return yaml.dump(data, default_flow_style=False)
        except ImportError:
            logger.warning("PyYAML not available, cannot export to YAML")
            return ""
