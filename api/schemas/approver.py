"""
Approver Management API Schemas
Pydantic models for request/response validation
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime
from enum import Enum


class ApproverType(str, Enum):
    """Approver persona types"""
    LINE_MANAGER = "LINE_MANAGER"
    ROLE_OWNER = "ROLE_OWNER"
    PROCESS_OWNER = "PROCESS_OWNER"
    DATA_OWNER = "DATA_OWNER"
    SECURITY_OFFICER = "SECURITY_OFFICER"
    COMPLIANCE_OFFICER = "COMPLIANCE_OFFICER"
    SYSTEM_OWNER = "SYSTEM_OWNER"
    DELEGATE = "DELEGATE"
    AI_RECOMMENDED = "AI_RECOMMENDED"
    GOVERNANCE_DESK = "GOVERNANCE_DESK"
    CISO = "CISO"


class ApproverStatus(str, Enum):
    """Approver status"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"


# =============================================================================
# Request Schemas
# =============================================================================

class ApproverCreate(BaseModel):
    """Create new approver"""
    approver_id: str = Field(..., min_length=1, max_length=100)
    name: str = Field(..., min_length=1, max_length=255)
    email: Optional[str] = Field(None, max_length=255)
    approver_type: ApproverType
    process_scope: List[str] = Field(default_factory=list)
    system_scope: List[str] = Field(default_factory=list)
    department: Optional[str] = Field(None, max_length=100)
    job_title: Optional[str] = Field(None, max_length=255)


class ApproverUpdate(BaseModel):
    """Update approver (all fields optional)"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    email: Optional[str] = Field(None, max_length=255)
    approver_type: Optional[ApproverType] = None
    process_scope: Optional[List[str]] = None
    system_scope: Optional[List[str]] = None
    department: Optional[str] = Field(None, max_length=100)
    job_title: Optional[str] = Field(None, max_length=255)
    status: Optional[ApproverStatus] = None


class SetOOORequest(BaseModel):
    """Set out-of-office"""
    ooo_until: datetime
    delegate_id: Optional[str] = Field(None, max_length=100)
    reason: Optional[str] = Field(None, max_length=500, description="Reason/justification for OOO")


class ToggleAvailabilityRequest(BaseModel):
    """Toggle availability"""
    is_available: bool


# =============================================================================
# Response Schemas
# =============================================================================

class ApproverSummary(BaseModel):
    """Approver summary for list views"""
    id: int
    approver_id: str
    name: str
    email: Optional[str] = None
    approver_type: str
    department: Optional[str] = None
    status: str
    is_available: bool
    is_ooo: bool
    ooo_until: Optional[datetime] = None
    delegate_id: Optional[str] = None
    ooo_reason: Optional[str] = None
    ooo_approved_by: Optional[str] = None
    avg_response_hours: float = 0.0
    approval_rate: float = 0.0
    current_queue_size: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ApproverDetailResponse(ApproverSummary):
    """Full approver detail"""
    process_scope: List[str] = []
    system_scope: List[str] = []
    job_title: Optional[str] = None
    is_active: bool = True


class PaginatedApproversResponse(BaseModel):
    """Paginated list response"""
    items: List[ApproverSummary]
    total: int
    limit: int
    offset: int
    has_more: bool


class ApproverStatsResponse(BaseModel):
    """Approver statistics"""
    total: int
    active: int
    available: int
    ooo: int
    by_type: Dict[str, int]


class ApproverTypeInfo(BaseModel):
    """Approver type metadata"""
    type: str
    label: str
    description: str
