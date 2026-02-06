"""
User Pydantic Schemas
Request/Response models for User API endpoints
"""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Any
from datetime import datetime
from enum import Enum


class UserStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    LOCKED = "locked"
    EXPIRED = "expired"


class UserType(str, Enum):
    DIALOG = "dialog"
    SERVICE = "service"
    SYSTEM = "system"
    COMMUNICATION = "communication"
    REFERENCE = "reference"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# ============== Request Schemas ==============

class UserCreate(BaseModel):
    """Schema for creating a new user"""
    user_id: str = Field(..., min_length=1, max_length=50, description="Unique user identifier")
    username: str = Field(..., min_length=1, max_length=100)
    email: Optional[EmailStr] = None
    full_name: str = Field(..., min_length=1, max_length=200)
    department: Optional[str] = Field(None, max_length=100)
    title: Optional[str] = Field(None, max_length=100)
    cost_center: Optional[str] = Field(None, max_length=50)
    company_code: Optional[str] = Field(None, max_length=10)
    manager_user_id: Optional[str] = Field(None, max_length=50)
    location: Optional[str] = Field(None, max_length=100)
    user_type: UserType = UserType.DIALOG
    password: Optional[str] = Field(None, min_length=8, description="Password for platform users")

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "USR001",
                "username": "jsmith",
                "email": "jsmith@company.com",
                "full_name": "John Smith",
                "department": "Finance",
                "title": "Senior Accountant",
                "user_type": "dialog"
            }
        }


class UserUpdate(BaseModel):
    """Schema for updating an existing user"""
    username: Optional[str] = Field(None, min_length=1, max_length=100)
    email: Optional[EmailStr] = None
    full_name: Optional[str] = Field(None, min_length=1, max_length=200)
    department: Optional[str] = Field(None, max_length=100)
    title: Optional[str] = Field(None, max_length=100)
    cost_center: Optional[str] = Field(None, max_length=50)
    company_code: Optional[str] = Field(None, max_length=10)
    manager_user_id: Optional[str] = Field(None, max_length=50)
    location: Optional[str] = Field(None, max_length=100)
    status: Optional[UserStatus] = None
    user_type: Optional[UserType] = None


class UserFilters(BaseModel):
    """Filters for querying users"""
    search: Optional[str] = None
    status: Optional[UserStatus] = None
    department: Optional[str] = None
    risk_level: Optional[RiskLevel] = None
    user_type: Optional[UserType] = None
    has_violations: Optional[bool] = None


class RoleAssignment(BaseModel):
    """Schema for assigning a role to a user"""
    role_id: str = Field(..., description="Role ID to assign")
    valid_from: Optional[datetime] = None
    valid_to: Optional[datetime] = None
    justification: Optional[str] = None


# ============== Response Schemas ==============

class UserSummary(BaseModel):
    """Brief user information for lists"""
    id: int
    user_id: str
    username: str
    email: Optional[str]
    full_name: Optional[str]
    department: Optional[str]
    title: Optional[str]
    status: str
    risk_score: float = 0.0
    risk_level: str = "low"
    violation_count: int = 0
    role_count: int = 0
    last_login: Optional[datetime] = None

    class Config:
        from_attributes = True


class RoleInfo(BaseModel):
    """Role information for user detail"""
    id: int
    role_id: str
    role_name: str
    role_type: Optional[str]
    risk_level: Optional[str]
    assigned_at: Optional[datetime]
    valid_from: Optional[datetime]
    valid_to: Optional[datetime]
    is_active: bool = True

    class Config:
        from_attributes = True


class ViolationInfo(BaseModel):
    """Violation information for user detail"""
    id: int
    violation_id: str
    rule_name: str
    severity: str
    status: str
    detected_at: datetime
    description: Optional[str]

    class Config:
        from_attributes = True


class EntitlementInfo(BaseModel):
    """Entitlement/authorization information"""
    id: int
    auth_object: str
    auth_field: str
    auth_value: str
    source_role: Optional[str]
    is_sensitive: bool = False

    class Config:
        from_attributes = True


class UserDetailResponse(BaseModel):
    """Complete user profile with related data"""
    id: int
    user_id: str
    username: str
    email: Optional[str]
    full_name: Optional[str]
    department: Optional[str]
    title: Optional[str]
    cost_center: Optional[str]
    company_code: Optional[str]
    manager_user_id: Optional[str]
    location: Optional[str]
    status: str
    user_type: str
    risk_score: float = 0.0
    risk_level: str = "low"
    violation_count: int = 0
    last_login: Optional[datetime]
    last_synced_at: Optional[datetime]
    created_at: datetime
    updated_at: Optional[datetime]

    # Related data
    roles: List[RoleInfo] = []
    violations: List[ViolationInfo] = []
    entitlements: List[EntitlementInfo] = []

    # Statistics
    total_roles: int = 0
    active_violations: int = 0
    sensitive_access_count: int = 0

    class Config:
        from_attributes = True


class UserResponse(BaseModel):
    """Standard user response"""
    id: int
    user_id: str
    username: str
    email: Optional[str]
    full_name: Optional[str]
    department: Optional[str]
    title: Optional[str]
    status: str
    risk_score: float = 0.0
    violation_count: int = 0
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class PaginatedUsersResponse(BaseModel):
    """Paginated list of users"""
    items: List[UserSummary]
    total: int
    limit: int
    offset: int
    has_more: bool


class UserStatsResponse(BaseModel):
    """User statistics for dashboard"""
    total_users: int
    active_users: int
    inactive_users: int
    suspended_users: int
    high_risk_users: int
    users_with_violations: int
    departments: List[dict]


class BulkOperationResult(BaseModel):
    """Result of bulk operations"""
    success_count: int
    failed_count: int
    errors: List[dict] = []
