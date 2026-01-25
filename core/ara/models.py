# Access Risk Analysis Data Models
# Core data structures for GOVERNEX+ ARA

"""
Data models for Access Risk Analysis.

Defines all entities used in risk detection, scoring, and remediation.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Set
from datetime import datetime, timedelta
from uuid import uuid4


# =============================================================================
# Enumerations
# =============================================================================

class RiskSeverity(Enum):
    """Risk severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

    @property
    def score_weight(self) -> float:
        """Get score weight for severity."""
        weights = {
            RiskSeverity.LOW: 0.25,
            RiskSeverity.MEDIUM: 0.5,
            RiskSeverity.HIGH: 0.75,
            RiskSeverity.CRITICAL: 1.0,
        }
        return weights[self]

    @classmethod
    def from_score(cls, score: int) -> "RiskSeverity":
        """Derive severity from risk score (0-100)."""
        if score >= 80:
            return cls.CRITICAL
        elif score >= 60:
            return cls.HIGH
        elif score >= 40:
            return cls.MEDIUM
        else:
            return cls.LOW


class RiskCategory(Enum):
    """Risk category classification."""
    FINANCIAL = "financial"
    IT = "it"
    HR = "hr"
    COMPLIANCE = "compliance"
    OPERATIONAL = "operational"
    SECURITY = "security"
    FRAUD = "fraud"
    DATA_PRIVACY = "data_privacy"


class RiskStatus(Enum):
    """Risk lifecycle status."""
    OPEN = "open"
    MITIGATED = "mitigated"
    ACCEPTED = "accepted"
    REMEDIATED = "remediated"
    EXPIRED = "expired"
    CLOSED = "closed"


class RiskType(Enum):
    """Type of risk detected."""
    SOD_CONFLICT = "sod_conflict"
    SENSITIVE_ACCESS = "sensitive_access"
    CRITICAL_ACTION = "critical_action"
    EXCESSIVE_ACCESS = "excessive_access"
    UNUSED_ACCESS = "unused_access"
    BEHAVIORAL_ANOMALY = "behavioral_anomaly"
    POLICY_VIOLATION = "policy_violation"
    PRIVILEGED_ACCESS = "privileged_access"


class ConflictType(Enum):
    """Type of SoD conflict."""
    USER_LEVEL = "user_level"
    ROLE_LEVEL = "role_level"
    PROFILE_LEVEL = "profile_level"
    CROSS_ROLE = "cross_role"
    CROSS_SYSTEM = "cross_system"


# =============================================================================
# Core Risk Models
# =============================================================================

@dataclass
class Risk:
    """
    Core risk entity.

    Represents a detected access risk with full context and history.
    """
    risk_id: str = field(default_factory=lambda: str(uuid4())[:12])
    risk_type: RiskType = RiskType.SOD_CONFLICT
    severity: RiskSeverity = RiskSeverity.MEDIUM
    category: RiskCategory = RiskCategory.COMPLIANCE
    status: RiskStatus = RiskStatus.OPEN

    # Risk details
    title: str = ""
    description: str = ""
    business_impact: str = ""

    # Entity references
    user_id: Optional[str] = None
    role_id: Optional[str] = None
    system_id: str = "SAP"

    # Access details
    conflicting_functions: List[str] = field(default_factory=list)
    conflicting_tcodes: List[str] = field(default_factory=list)
    conflicting_auth_objects: List[str] = field(default_factory=list)
    conflicting_roles: List[str] = field(default_factory=list)

    # Scoring
    base_score: int = 50
    context_score: int = 0
    usage_score: int = 0
    final_score: int = 50

    # Context factors
    context_factors: Dict[str, Any] = field(default_factory=dict)

    # Timestamps
    detected_at: datetime = field(default_factory=datetime.now)
    last_evaluated: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None

    # Mitigation
    mitigation_id: Optional[str] = None
    mitigation_status: Optional[str] = None

    # Audit
    detected_by: str = "ARA_ENGINE"
    rule_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "risk_id": self.risk_id,
            "risk_type": self.risk_type.value,
            "severity": self.severity.value,
            "category": self.category.value,
            "status": self.status.value,
            "title": self.title,
            "description": self.description,
            "business_impact": self.business_impact,
            "user_id": self.user_id,
            "role_id": self.role_id,
            "system_id": self.system_id,
            "conflicting_functions": self.conflicting_functions,
            "conflicting_tcodes": self.conflicting_tcodes,
            "conflicting_auth_objects": self.conflicting_auth_objects,
            "conflicting_roles": self.conflicting_roles,
            "base_score": self.base_score,
            "context_score": self.context_score,
            "usage_score": self.usage_score,
            "final_score": self.final_score,
            "context_factors": self.context_factors,
            "detected_at": self.detected_at.isoformat(),
            "last_evaluated": self.last_evaluated.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "mitigation_id": self.mitigation_id,
            "mitigation_status": self.mitigation_status,
            "rule_id": self.rule_id,
        }

    def update_score(self, base: int = None, context: int = None, usage: int = None):
        """Update risk scores and recalculate final score."""
        if base is not None:
            self.base_score = base
        if context is not None:
            self.context_score = context
        if usage is not None:
            self.usage_score = usage

        # Calculate final score (weighted average)
        self.final_score = int(
            self.base_score * 0.5 +
            self.context_score * 0.3 +
            self.usage_score * 0.2
        )

        # Update severity based on final score
        self.severity = RiskSeverity.from_score(self.final_score)
        self.last_evaluated = datetime.now()


# =============================================================================
# SoD Models
# =============================================================================

@dataclass
class SoDFunction:
    """
    Business function for SoD analysis.

    A function represents a business capability (e.g., "Create Vendor").
    """
    function_id: str
    name: str
    description: str = ""
    category: RiskCategory = RiskCategory.FINANCIAL

    # Access components
    tcodes: List[str] = field(default_factory=list)
    auth_objects: List[Dict[str, Any]] = field(default_factory=list)
    roles: List[str] = field(default_factory=list)

    # Risk attributes
    sensitivity: RiskSeverity = RiskSeverity.MEDIUM
    business_process: str = ""


@dataclass
class SoDRule:
    """
    Segregation of Duties rule definition.

    Defines which functions conflict with each other.
    """
    rule_id: str
    name: str
    description: str = ""

    # Conflicting functions
    function_1: str = ""  # Function ID
    function_2: str = ""  # Function ID

    # Alternative: direct access specification
    function_1_tcodes: List[str] = field(default_factory=list)
    function_1_auth_objects: List[Dict[str, Any]] = field(default_factory=list)
    function_2_tcodes: List[str] = field(default_factory=list)
    function_2_auth_objects: List[Dict[str, Any]] = field(default_factory=list)

    # Risk attributes
    severity: RiskSeverity = RiskSeverity.HIGH
    category: RiskCategory = RiskCategory.FINANCIAL
    business_impact: str = ""

    # Rule metadata
    enabled: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    created_by: str = ""
    version: int = 1

    # Organizational scope
    org_scope: Optional[Dict[str, List[str]]] = None  # e.g., {"company_code": ["1000"]}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "name": self.name,
            "description": self.description,
            "function_1": self.function_1,
            "function_2": self.function_2,
            "function_1_tcodes": self.function_1_tcodes,
            "function_1_auth_objects": self.function_1_auth_objects,
            "function_2_tcodes": self.function_2_tcodes,
            "function_2_auth_objects": self.function_2_auth_objects,
            "severity": self.severity.value,
            "category": self.category.value,
            "business_impact": self.business_impact,
            "enabled": self.enabled,
            "version": self.version,
        }


@dataclass
class SoDConflict:
    """
    Detected SoD conflict.

    Represents an actual conflict found during analysis.
    """
    conflict_id: str = field(default_factory=lambda: str(uuid4())[:12])
    rule: SoDRule = None
    conflict_type: ConflictType = ConflictType.USER_LEVEL

    # Entity
    user_id: Optional[str] = None
    role_id: Optional[str] = None

    # Conflict details
    function_1_access: Dict[str, Any] = field(default_factory=dict)
    function_2_access: Dict[str, Any] = field(default_factory=dict)

    # Source of access
    function_1_roles: List[str] = field(default_factory=list)
    function_2_roles: List[str] = field(default_factory=list)

    # Scoring
    severity: RiskSeverity = RiskSeverity.HIGH
    risk_score: int = 70

    detected_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "conflict_id": self.conflict_id,
            "rule_id": self.rule.rule_id if self.rule else None,
            "rule_name": self.rule.name if self.rule else None,
            "conflict_type": self.conflict_type.value,
            "user_id": self.user_id,
            "role_id": self.role_id,
            "function_1_access": self.function_1_access,
            "function_2_access": self.function_2_access,
            "function_1_roles": self.function_1_roles,
            "function_2_roles": self.function_2_roles,
            "severity": self.severity.value,
            "risk_score": self.risk_score,
            "detected_at": self.detected_at.isoformat(),
        }


@dataclass
class SoDRuleSet:
    """Collection of SoD rules."""
    ruleset_id: str
    name: str
    description: str = ""
    rules: List[SoDRule] = field(default_factory=list)
    functions: Dict[str, SoDFunction] = field(default_factory=dict)
    version: int = 1
    created_at: datetime = field(default_factory=datetime.now)


# =============================================================================
# Context Models
# =============================================================================

@dataclass
class UserContext:
    """
    User context for risk evaluation.

    Provides contextual information that affects risk scoring.
    """
    user_id: str

    # Employment context
    employment_type: str = "employee"  # employee, contractor, vendor
    department: str = ""
    job_title: str = ""
    tenure_days: int = 0
    manager_id: Optional[str] = None

    # Access context
    is_privileged_user: bool = False
    is_emergency_access: bool = False
    access_level: str = "standard"  # standard, elevated, admin

    # Activity context
    last_login: Optional[datetime] = None
    login_count_30d: int = 0
    transaction_count_30d: int = 0
    sensitive_action_count_30d: int = 0

    # Location/time context
    current_location: str = "internal"  # internal, external, unknown
    is_business_hours: bool = True
    timezone: str = "UTC"

    # Device context
    device_type: str = "managed"  # managed, unmanaged, unknown
    device_trust_level: str = "high"  # high, medium, low

    # Risk history
    previous_violations: int = 0
    open_risks: int = 0


@dataclass
class RiskContext:
    """
    Full context for risk evaluation.

    Combines user context with environmental factors.
    """
    user_context: Optional[UserContext] = None

    # Time context
    evaluation_time: datetime = field(default_factory=datetime.now)
    is_business_hours: bool = True
    is_month_end: bool = False
    is_year_end: bool = False

    # System context
    system_id: str = "SAP"
    environment: str = "production"  # production, test, dev

    # Request context (for simulations)
    is_simulation: bool = False
    requested_roles: List[str] = field(default_factory=list)
    requested_by: Optional[str] = None
    request_reason: Optional[str] = None


# =============================================================================
# Analysis Results
# =============================================================================

@dataclass
class RiskAnalysisResult:
    """
    Result of risk analysis.

    Contains all detected risks and analysis metadata.
    """
    analysis_id: str = field(default_factory=lambda: str(uuid4())[:12])
    analysis_type: str = "full"  # full, sod_only, sensitive_only, simulation

    # Entity analyzed
    user_id: Optional[str] = None
    role_id: Optional[str] = None
    system_id: str = "SAP"

    # Results
    risks: List[Risk] = field(default_factory=list)
    sod_conflicts: List[SoDConflict] = field(default_factory=list)

    # Summary
    total_risks: int = 0
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0

    # Aggregate scores
    aggregate_risk_score: int = 0
    max_risk_score: int = 0

    # Context used
    context: Optional[RiskContext] = None

    # Timing
    analyzed_at: datetime = field(default_factory=datetime.now)
    duration_ms: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "analysis_id": self.analysis_id,
            "analysis_type": self.analysis_type,
            "user_id": self.user_id,
            "role_id": self.role_id,
            "system_id": self.system_id,
            "total_risks": self.total_risks,
            "critical_count": self.critical_count,
            "high_count": self.high_count,
            "medium_count": self.medium_count,
            "low_count": self.low_count,
            "aggregate_risk_score": self.aggregate_risk_score,
            "max_risk_score": self.max_risk_score,
            "analyzed_at": self.analyzed_at.isoformat(),
            "duration_ms": self.duration_ms,
            "risks": [r.to_dict() for r in self.risks],
            "sod_conflicts": [c.to_dict() for c in self.sod_conflicts],
        }

    def calculate_summary(self):
        """Calculate summary statistics."""
        self.total_risks = len(self.risks)
        self.critical_count = len([r for r in self.risks if r.severity == RiskSeverity.CRITICAL])
        self.high_count = len([r for r in self.risks if r.severity == RiskSeverity.HIGH])
        self.medium_count = len([r for r in self.risks if r.severity == RiskSeverity.MEDIUM])
        self.low_count = len([r for r in self.risks if r.severity == RiskSeverity.LOW])

        if self.risks:
            self.max_risk_score = max(r.final_score for r in self.risks)
            self.aggregate_risk_score = int(sum(r.final_score for r in self.risks) / len(self.risks))


@dataclass
class SimulationResult:
    """
    Result of risk simulation (pre-provisioning).

    Shows what risks would be created by granting access.
    """
    simulation_id: str = field(default_factory=lambda: str(uuid4())[:12])

    # Request details
    user_id: str = ""
    requested_roles: List[str] = field(default_factory=list)
    requested_tcodes: List[str] = field(default_factory=list)

    # Current state
    current_risks: List[Risk] = field(default_factory=list)
    current_risk_score: int = 0

    # Simulated state
    new_risks: List[Risk] = field(default_factory=list)
    simulated_risk_score: int = 0

    # Impact
    risk_delta: int = 0
    new_sod_conflicts: List[SoDConflict] = field(default_factory=list)
    new_sensitive_access: List[str] = field(default_factory=list)

    # Recommendation
    recommendation: str = "approve"  # approve, review, deny
    recommendation_reason: str = ""

    simulated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "simulation_id": self.simulation_id,
            "user_id": self.user_id,
            "requested_roles": self.requested_roles,
            "current_risk_score": self.current_risk_score,
            "simulated_risk_score": self.simulated_risk_score,
            "risk_delta": self.risk_delta,
            "new_risks_count": len(self.new_risks),
            "new_sod_conflicts_count": len(self.new_sod_conflicts),
            "recommendation": self.recommendation,
            "recommendation_reason": self.recommendation_reason,
            "simulated_at": self.simulated_at.isoformat(),
        }


@dataclass
class RemediationSuggestion:
    """
    Smart remediation suggestion.

    Provides actionable steps to reduce risk.
    """
    suggestion_id: str = field(default_factory=lambda: str(uuid4())[:8])
    risk_id: str = ""

    # Suggestion details
    action: str = ""  # remove_role, split_role, remove_tcode, add_mitigation
    target_type: str = ""  # role, tcode, auth_object
    target_id: str = ""
    target_name: str = ""

    # Impact analysis
    risk_reduction: int = 0  # Points reduced
    business_impact: str = ""
    affected_functions: List[str] = field(default_factory=list)

    # Effort estimation
    implementation_effort: str = "low"  # low, medium, high
    requires_approval: bool = False
    approvers: List[str] = field(default_factory=list)

    # Explanation
    rationale: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "suggestion_id": self.suggestion_id,
            "risk_id": self.risk_id,
            "action": self.action,
            "target_type": self.target_type,
            "target_id": self.target_id,
            "target_name": self.target_name,
            "risk_reduction": self.risk_reduction,
            "business_impact": self.business_impact,
            "implementation_effort": self.implementation_effort,
            "requires_approval": self.requires_approval,
            "rationale": self.rationale,
        }
