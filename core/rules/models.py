"""
GRC Rules Engine - Data Models

These models define the structure for permissions, entitlements, and conflict sets
that form the foundation of Segregation of Duties (SoD) analysis.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum
from datetime import datetime


class RiskSeverity(Enum):
    """Risk severity levels aligned with SAP GRC standards"""
    LOW = 10
    MEDIUM = 30
    HIGH = 60
    CRITICAL = 100


class RuleType(Enum):
    """Types of access control rules"""
    SOD = "segregation_of_duties"
    SENSITIVE = "sensitive_access"
    CRITICAL_ACTION = "critical_action"
    BEHAVIORAL = "behavioral_anomaly"
    CONTEXTUAL = "contextual_risk"
    ATTRIBUTE = "attribute_based"
    COMPOSITE = "composite_rule"


class RiskCategory(Enum):
    """Business risk categories"""
    FINANCIAL = "Financial"
    PROCUREMENT = "Procurement"
    HR_PAYROLL = "HR & Payroll"
    IT_SECURITY = "IT Security"
    MASTER_DATA = "Master Data"
    BASIS = "Basis Administration"
    INVENTORY = "Inventory Management"
    SALES = "Sales & Distribution"
    CUSTOM = "Custom"


@dataclass
class Entitlement:
    """
    Represents a single authorization/entitlement in SAP or other systems.

    Maps to SAP authorization objects like S_TCODE, F_BKPF_BUK, etc.
    """
    auth_object: str  # e.g., 'S_TCODE', 'F_BKPF_BUK'
    field: str        # e.g., 'TCD', 'BUKRS', 'ACTVT'
    value: str        # e.g., 'FK01', '1000', '01'

    # Optional: activity field for finer control
    activity: Optional[str] = None  # Create(01), Change(02), Display(03), Delete(06)

    # System context
    system: str = "SAP"
    system_type: str = "ECC"  # ECC, S4HANA, BW, etc.

    # Additional attributes for complex matching
    attributes: Dict[str, Any] = field(default_factory=dict)

    def to_key(self) -> str:
        """Generate unique key for this entitlement"""
        base = f"{self.system}:{self.auth_object}:{self.field}:{self.value}"
        if self.activity:
            base += f":{self.activity}"
        return base

    def matches(self, other: 'Entitlement', strict: bool = False) -> bool:
        """Check if this entitlement matches another (supports wildcards)"""
        if self.auth_object != other.auth_object:
            return False
        if self.field != other.field:
            return False

        # Support wildcard matching
        if self.value == "*" or other.value == "*":
            return True

        if strict:
            return self.value == other.value and self.activity == other.activity

        return self.value == other.value


@dataclass
class Permission:
    """
    High-level permission combining multiple entitlements.

    Represents a business action like "Create Vendor" which may require
    multiple underlying SAP authorizations.
    """
    permission_id: str
    name: str
    description: str
    entitlements: List[Entitlement]

    # Business context
    business_process: str = ""
    risk_level: RiskSeverity = RiskSeverity.MEDIUM

    # System scope
    system: str = "SAP"

    def to_key(self) -> str:
        return f"{self.system}:{self.permission_id}"

    def user_has_permission(self, user_entitlements: List[Entitlement]) -> bool:
        """Check if user has ALL required entitlements for this permission"""
        user_keys = {e.to_key() for e in user_entitlements}
        required_keys = {e.to_key() for e in self.entitlements}
        return required_keys.issubset(user_keys)


@dataclass
class ConflictSet:
    """
    Represents a set of conflicting functions/permissions.

    If a user has permissions from BOTH sides of a conflict set,
    it represents an SoD violation.
    """
    name: str
    description: str

    # Side A of the conflict (e.g., "Vendor Creation")
    function_a_name: str
    function_a_entitlements: List[Entitlement]

    # Side B of the conflict (e.g., "Payment Execution")
    function_b_name: str
    function_b_entitlements: List[Entitlement]

    # Optional: Additional conflicting functions (for N-way conflicts)
    additional_functions: List[Dict] = field(default_factory=list)

    def check_conflict(self, user_entitlements: List[Entitlement]) -> Dict:
        """
        Check if user has conflicting entitlements.

        Returns dict with conflict details or empty dict if no conflict.
        """
        user_keys = {e.to_key() for e in user_entitlements}

        # Check function A
        func_a_keys = {e.to_key() for e in self.function_a_entitlements}
        has_func_a = func_a_keys.issubset(user_keys)

        # Check function B
        func_b_keys = {e.to_key() for e in self.function_b_entitlements}
        has_func_b = func_b_keys.issubset(user_keys)

        if has_func_a and has_func_b:
            return {
                "has_conflict": True,
                "conflict_name": self.name,
                "function_a": {
                    "name": self.function_a_name,
                    "entitlements": [e.to_key() for e in self.function_a_entitlements]
                },
                "function_b": {
                    "name": self.function_b_name,
                    "entitlements": [e.to_key() for e in self.function_b_entitlements]
                }
            }

        return {"has_conflict": False}


@dataclass
class UserAccess:
    """Represents a user's complete access profile"""
    user_id: str
    username: str
    full_name: str

    # Organizational data
    department: str
    cost_center: str = ""
    company_code: str = ""

    # Access assignments
    roles: List[str] = field(default_factory=list)
    profiles: List[str] = field(default_factory=list)
    entitlements: List[Entitlement] = field(default_factory=list)

    # Context
    employment_type: str = "FULL_TIME"  # FULL_TIME, CONTRACTOR, VENDOR
    risk_score: float = 0.0
    last_login: Optional[datetime] = None

    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    modified_at: datetime = field(default_factory=datetime.now)


@dataclass
class RiskViolation:
    """Represents a detected risk/violation"""
    violation_id: str
    rule_id: str
    rule_name: str
    rule_type: RuleType
    severity: RiskSeverity

    # User context
    user_id: str
    username: str

    # Violation details
    conflicting_entitlements: List[Dict]
    risk_category: RiskCategory
    business_impact: str

    # Remediation
    recommended_actions: List[str] = field(default_factory=list)
    mitigation_controls: List[str] = field(default_factory=list)

    # Status tracking
    status: str = "OPEN"  # OPEN, MITIGATED, REMEDIATED, ACCEPTED, FALSE_POSITIVE
    detected_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict:
        return {
            "violation_id": self.violation_id,
            "rule_id": self.rule_id,
            "rule_name": self.rule_name,
            "rule_type": self.rule_type.value,
            "severity": self.severity.value,
            "severity_name": self.severity.name,
            "user_id": self.user_id,
            "username": self.username,
            "conflicting_entitlements": self.conflicting_entitlements,
            "risk_category": self.risk_category.value,
            "business_impact": self.business_impact,
            "recommended_actions": self.recommended_actions,
            "mitigation_controls": self.mitigation_controls,
            "status": self.status,
            "detected_at": self.detected_at.isoformat()
        }
