"""
Role API Schemas
Pydantic models for role management request/response validation
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class RoleType(str, Enum):
    """Role types"""
    SINGLE = "single"
    COMPOSITE = "composite"
    DERIVED = "derived"
    TEMPLATE = "template"
    EMERGENCY = "emergency"
    BUSINESS = "business"
    TECHNICAL = "technical"


class RoleStatus(str, Enum):
    """Role lifecycle status"""
    DRAFT = "draft"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"


class RiskLevel(str, Enum):
    """Risk classification levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# =============================================================================
# Request Schemas
# =============================================================================

class RoleCreate(BaseModel):
    """Schema for creating a new role"""
    role_id: str = Field(..., min_length=1, max_length=100, description="Unique role identifier")
    role_name: str = Field(..., min_length=1, max_length=255, description="Role display name")
    description: Optional[str] = Field(None, max_length=1000)
    role_type: RoleType = Field(default=RoleType.SINGLE)
    source_system: str = Field(default="SAP", max_length=50)
    system_client: Optional[str] = Field(None, max_length=10)
    risk_level: RiskLevel = Field(default=RiskLevel.MEDIUM)
    is_sensitive: bool = Field(default=False)
    owner_user_id: Optional[str] = Field(None, max_length=50)
    owner_email: Optional[str] = Field(None, max_length=255)
    parent_role_id: Optional[str] = Field(None, max_length=100)
    department: Optional[str] = Field(None, max_length=100)
    business_process: Optional[str] = Field(None, max_length=100)


class RoleUpdate(BaseModel):
    """Schema for updating an existing role"""
    role_name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    role_type: Optional[RoleType] = None
    risk_level: Optional[RiskLevel] = None
    is_sensitive: Optional[bool] = None
    owner_user_id: Optional[str] = Field(None, max_length=50)
    owner_email: Optional[str] = Field(None, max_length=255)
    status: Optional[RoleStatus] = None
    department: Optional[str] = Field(None, max_length=100)
    business_process: Optional[str] = Field(None, max_length=100)


class RoleFilters(BaseModel):
    """Filters for listing roles"""
    search: Optional[str] = None
    status: Optional[RoleStatus] = None
    role_type: Optional[RoleType] = None
    risk_level: Optional[RiskLevel] = None
    department: Optional[str] = None
    owner_user_id: Optional[str] = None
    source_system: Optional[str] = None
    is_sensitive: Optional[bool] = None


class PermissionCreate(BaseModel):
    """Schema for adding a permission to a role"""
    auth_object: str = Field(..., min_length=1, max_length=50)
    field: str = Field(..., min_length=1, max_length=50)
    value: str = Field(..., min_length=1, max_length=255)
    activity: Optional[str] = Field(None, max_length=10)
    is_sensitive: bool = Field(default=False)
    risk_level: RiskLevel = Field(default=RiskLevel.LOW)


class CompositeRoleCreate(BaseModel):
    """Schema for creating a composite role"""
    role_id: str = Field(..., min_length=1, max_length=100)
    role_name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    child_role_ids: List[str] = Field(..., min_items=1)
    owner_user_id: Optional[str] = None


class DerivedRoleCreate(BaseModel):
    """Schema for creating a derived role"""
    role_id: str = Field(..., min_length=1, max_length=100)
    role_name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    parent_role_id: str = Field(..., min_length=1, max_length=100)
    org_level_values: Dict[str, str] = Field(default_factory=dict)
    owner_user_id: Optional[str] = None


class BusinessRoleCreate(BaseModel):
    """Schema for creating a business role"""
    role_id: str = Field(..., min_length=1, max_length=100)
    role_name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    department: Optional[str] = None
    business_process: Optional[str] = None
    category: Optional[str] = None
    is_requestable: bool = Field(default=True)
    owner_user_id: Optional[str] = None
    technical_role_ids: List[str] = Field(default_factory=list)


class TechnicalMappingCreate(BaseModel):
    """Schema for mapping technical roles to a business role"""
    technical_role_id: str = Field(..., min_length=1, max_length=100)
    org_level_conditions: Dict[str, str] = Field(default_factory=dict)
    is_mandatory: bool = Field(default=True)


class RoleAssignmentCreate(BaseModel):
    """Schema for assigning a role to a user"""
    user_id: str = Field(..., min_length=1, max_length=50)
    valid_from: Optional[datetime] = None
    valid_to: Optional[datetime] = None
    justification: Optional[str] = Field(None, max_length=500)


# =============================================================================
# Response Schemas
# =============================================================================

class PermissionInfo(BaseModel):
    """Permission details in response"""
    id: int
    auth_object: str
    field: str
    value: str
    activity: Optional[str] = None
    is_sensitive: bool = False
    risk_level: str = "low"

    class Config:
        from_attributes = True


class RoleSummary(BaseModel):
    """Summary role information for lists"""
    id: int
    role_id: str
    role_name: str
    description: Optional[str] = None
    role_type: str
    status: str
    risk_level: str
    is_sensitive: bool = False
    source_system: str = "SAP"
    user_count: int = 0
    permission_count: int = 0
    sod_conflict_count: int = 0
    owner_user_id: Optional[str] = None
    owner_email: Optional[str] = None
    department: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class RoleDetailResponse(BaseModel):
    """Detailed role information"""
    id: int
    role_id: str
    role_name: str
    description: Optional[str] = None
    role_type: str
    status: str
    risk_level: str
    is_sensitive: bool = False
    source_system: str = "SAP"
    system_client: Optional[str] = None
    parent_role_id: Optional[str] = None
    owner_user_id: Optional[str] = None
    owner_email: Optional[str] = None
    department: Optional[str] = None
    business_process: Optional[str] = None
    user_count: int = 0
    transaction_count: int = 0
    permissions: List[PermissionInfo] = []
    child_roles: List[str] = []
    assigned_users: List[Dict[str, Any]] = []
    sod_conflicts: List[Dict[str, Any]] = []
    valid_from: Optional[datetime] = None
    valid_to: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class RoleResponse(BaseModel):
    """Standard role response after create/update"""
    id: int
    role_id: str
    role_name: str
    description: Optional[str] = None
    role_type: str
    status: str
    risk_level: str
    source_system: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PaginatedRolesResponse(BaseModel):
    """Paginated roles list response"""
    items: List[RoleSummary]
    total: int
    limit: int
    offset: int
    has_more: bool


class RoleStatsResponse(BaseModel):
    """Role statistics for dashboard"""
    total_roles: int
    active_roles: int
    draft_roles: int
    deprecated_roles: int
    high_risk_roles: int
    roles_with_sod_conflicts: int
    total_assignments: int
    by_type: Dict[str, int]
    by_system: Dict[str, int]
    by_department: List[Dict[str, Any]]


class BusinessRoleSummary(BaseModel):
    """Business role summary"""
    id: int
    role_id: str
    role_name: str
    description: Optional[str] = None
    department: Optional[str] = None
    business_process: Optional[str] = None
    category: Optional[str] = None
    status: str
    is_requestable: bool = True
    technical_role_count: int = 0
    user_count: int = 0
    owner_user_id: Optional[str] = None
    popularity_score: float = 0.0
    created_at: datetime

    class Config:
        from_attributes = True


class RoleCatalogEntry(BaseModel):
    """Role entry for self-service catalog"""
    role_id: str
    role_name: str
    description: Optional[str] = None
    category: Optional[str] = None
    department: Optional[str] = None
    risk_level: str
    is_requestable: bool = True
    approval_required: bool = True
    typical_users: List[str] = []
    popularity_score: float = 0.0


class RoleComparisonResult(BaseModel):
    """Result of comparing two roles"""
    role_a_id: str
    role_b_id: str
    similarity_score: float
    common_permissions: int
    unique_to_a: int
    unique_to_b: int
    sod_conflicts: List[Dict[str, Any]] = []
    recommendation: Optional[str] = None


class SodConflictInfo(BaseModel):
    """SoD conflict information"""
    rule_id: str
    rule_name: str
    severity: str
    function1: str
    function2: str
    conflicting_permissions: List[str] = []
    recommendation: Optional[str] = None
