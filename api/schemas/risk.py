"""
Risk API Schemas
Pydantic models for risk analysis request/response validation
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class ViolationStatus(str, Enum):
    """Violation lifecycle status"""
    OPEN = "open"
    IN_REVIEW = "in_review"
    MITIGATED = "mitigated"
    ACCEPTED = "accepted"
    CLOSED = "closed"


class ViolationSeverity(str, Enum):
    """Violation severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ViolationType(str, Enum):
    """Types of risk violations"""
    SOD_CONFLICT = "sod_conflict"
    EXCESSIVE_ACCESS = "excessive_access"
    SENSITIVE_ACCESS = "sensitive_access"
    DORMANT_ACCOUNT = "dormant_account"
    ORPHANED_ACCOUNT = "orphaned_account"
    POLICY_VIOLATION = "policy_violation"


class RuleStatus(str, Enum):
    """SoD rule status"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    DRAFT = "draft"


# =============================================================================
# Request Schemas
# =============================================================================

class ViolationCreate(BaseModel):
    """Schema for creating a violation"""
    user_id: str = Field(..., min_length=1, max_length=50)
    rule_id: Optional[str] = Field(None, max_length=100)
    violation_type: ViolationType
    severity: ViolationSeverity = ViolationSeverity.MEDIUM
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    conflicting_roles: List[str] = Field(default_factory=list)
    conflicting_permissions: List[str] = Field(default_factory=list)
    source_system: str = Field(default="SAP", max_length=50)


class ViolationUpdate(BaseModel):
    """Schema for updating a violation"""
    status: Optional[ViolationStatus] = None
    severity: Optional[ViolationSeverity] = None
    mitigation_notes: Optional[str] = Field(None, max_length=1000)
    reviewer_id: Optional[str] = Field(None, max_length=50)
    resolution_date: Optional[datetime] = None


class ViolationFilters(BaseModel):
    """Filters for listing violations"""
    search: Optional[str] = None
    status: Optional[ViolationStatus] = None
    severity: Optional[ViolationSeverity] = None
    violation_type: Optional[ViolationType] = None
    user_id: Optional[str] = None
    rule_id: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None


class SodRuleCreate(BaseModel):
    """Schema for creating a SoD rule"""
    rule_id: str = Field(..., min_length=1, max_length=100)
    rule_name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    category: str = Field(default="General", max_length=100)
    severity: ViolationSeverity = ViolationSeverity.HIGH
    function1: str = Field(..., min_length=1, max_length=255)
    function2: str = Field(..., min_length=1, max_length=255)
    function1_transactions: List[str] = Field(default_factory=list)
    function2_transactions: List[str] = Field(default_factory=list)
    source_system: str = Field(default="SAP", max_length=50)
    business_process: Optional[str] = Field(None, max_length=100)
    mitigation_controls: List[str] = Field(default_factory=list)
    is_custom: bool = Field(default=False)


class SodRuleUpdate(BaseModel):
    """Schema for updating a SoD rule"""
    rule_name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    category: Optional[str] = Field(None, max_length=100)
    severity: Optional[ViolationSeverity] = None
    status: Optional[RuleStatus] = None
    mitigation_controls: Optional[List[str]] = None


class UserAnalysisRequest(BaseModel):
    """Request for analyzing a user's risk"""
    user_id: str = Field(..., min_length=1, max_length=50)
    include_details: bool = Field(default=True)
    rule_ids: Optional[List[str]] = None


class RoleSimulationRequest(BaseModel):
    """Request for simulating role assignment"""
    user_id: str = Field(..., min_length=1, max_length=50)
    role_ids: List[str] = Field(..., min_items=1)
    include_current_roles: bool = Field(default=True)


# =============================================================================
# Response Schemas
# =============================================================================

class ViolationSummary(BaseModel):
    """Summary violation information for lists"""
    id: int
    violation_id: str
    user_id: str
    user_name: Optional[str] = None
    department: Optional[str] = None
    rule_id: Optional[str] = None
    rule_name: Optional[str] = None
    violation_type: str
    severity: str
    status: str
    title: str
    source_system: str = "SAP"
    detected_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ViolationDetailResponse(BaseModel):
    """Detailed violation information"""
    id: int
    violation_id: str
    user_id: str
    user_name: Optional[str] = None
    department: Optional[str] = None
    rule_id: Optional[str] = None
    rule_name: Optional[str] = None
    violation_type: str
    severity: str
    status: str
    title: str
    description: Optional[str] = None
    conflicting_roles: List[str] = []
    conflicting_permissions: List[str] = []
    source_system: str = "SAP"
    mitigation_notes: Optional[str] = None
    reviewer_id: Optional[str] = None
    resolution_date: Optional[datetime] = None
    detected_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ViolationResponse(BaseModel):
    """Standard violation response"""
    id: int
    violation_id: str
    user_id: str
    violation_type: str
    severity: str
    status: str
    title: str
    detected_at: datetime

    class Config:
        from_attributes = True


class PaginatedViolationsResponse(BaseModel):
    """Paginated violations list response"""
    items: List[ViolationSummary]
    total: int
    limit: int
    offset: int
    has_more: bool


class ViolationStatsResponse(BaseModel):
    """Violation statistics for dashboard"""
    total_violations: int
    open_violations: int
    critical_violations: int
    high_violations: int
    mitigated_last_30_days: int
    by_type: Dict[str, int]
    by_severity: Dict[str, int]
    by_status: Dict[str, int]
    trend: List[Dict[str, Any]]


class SodRuleSummary(BaseModel):
    """Summary SoD rule information"""
    id: int
    rule_id: str
    rule_name: str
    description: Optional[str] = None
    category: str
    severity: str
    status: str
    function1: str
    function2: str
    violation_count: int = 0
    source_system: str = "SAP"
    is_custom: bool = False
    created_at: datetime

    class Config:
        from_attributes = True


class SodRuleDetailResponse(BaseModel):
    """Detailed SoD rule information"""
    id: int
    rule_id: str
    rule_name: str
    description: Optional[str] = None
    category: str
    severity: str
    status: str
    function1: str
    function2: str
    function1_transactions: List[str] = []
    function2_transactions: List[str] = []
    violation_count: int = 0
    source_system: str = "SAP"
    business_process: Optional[str] = None
    mitigation_controls: List[str] = []
    is_custom: bool = False
    last_run: Optional[datetime] = None
    created_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PaginatedSodRulesResponse(BaseModel):
    """Paginated SoD rules list response"""
    items: List[SodRuleSummary]
    total: int
    limit: int
    offset: int
    has_more: bool


class RiskAnalysisResult(BaseModel):
    """Result of risk analysis for a user"""
    user_id: str
    username: Optional[str] = None
    risk_score: float
    risk_level: str
    total_violations: int
    violations_by_severity: Dict[str, int]
    violations: List[ViolationSummary] = []
    sensitive_access_count: int = 0
    high_risk_roles: List[str] = []
    analysis_timestamp: datetime


class RoleSimulationResult(BaseModel):
    """Result of role assignment simulation"""
    user_id: str
    current_risk_score: float
    projected_risk_score: float
    new_violations: List[Dict[str, Any]] = []
    recommendation: str  # APPROVE, REVIEW_REQUIRED, DENY
    risk_delta: float
    affected_users: int = 1
    compliance_impact: str
    insights: List[str] = []
