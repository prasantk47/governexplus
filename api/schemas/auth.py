"""
Auth API Schemas
Pydantic models for authentication request/response validation
"""

from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class UserRole(str, Enum):
    """User roles in the platform"""
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    SECURITY_ADMIN = "security_admin"
    MANAGER = "manager"
    END_USER = "end_user"


# =============================================================================
# Request Schemas
# =============================================================================

class LoginRequest(BaseModel):
    """Login request schema"""
    username: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=1, max_length=255)
    tenant_id: Optional[str] = Field(None, max_length=100)
    remember_me: bool = Field(default=False)


class RefreshTokenRequest(BaseModel):
    """Refresh token request"""
    refresh_token: str = Field(..., min_length=1)


class ChangePasswordRequest(BaseModel):
    """Change password request"""
    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8, max_length=255)


class ResetPasswordRequest(BaseModel):
    """Reset password request"""
    email: EmailStr
    tenant_id: Optional[str] = None


class VerifyResetTokenRequest(BaseModel):
    """Verify reset token and set new password"""
    token: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8, max_length=255)


class RegisterUserRequest(BaseModel):
    """Register new user request (admin only)"""
    username: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=255)
    full_name: str = Field(..., min_length=1, max_length=200)
    role: UserRole = Field(default=UserRole.END_USER)
    department: Optional[str] = Field(None, max_length=100)


# =============================================================================
# Response Schemas
# =============================================================================

class TokenResponse(BaseModel):
    """Token response after login"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds
    user: "UserInfoResponse"


class UserInfoResponse(BaseModel):
    """User information in token response"""
    id: str
    username: str
    email: Optional[str] = None
    full_name: str
    role: str
    permissions: List[str] = []
    department: Optional[str] = None
    tenant_id: Optional[str] = None
    is_active: bool = True
    last_login: Optional[datetime] = None


class ProfileResponse(BaseModel):
    """User profile response"""
    id: str
    username: str
    email: Optional[str] = None
    full_name: str
    role: str
    permissions: List[str] = []
    department: Optional[str] = None
    tenant_id: Optional[str] = None
    is_active: bool = True
    created_at: datetime
    last_login: Optional[datetime] = None
    mfa_enabled: bool = False
    password_expires_at: Optional[datetime] = None


class SessionInfo(BaseModel):
    """Active session information"""
    session_id: str
    device: Optional[str] = None
    ip_address: Optional[str] = None
    location: Optional[str] = None
    created_at: datetime
    last_activity: datetime
    is_current: bool = False


class AuthStatusResponse(BaseModel):
    """Authentication status response"""
    authenticated: bool
    user: Optional[UserInfoResponse] = None
    tenant_id: Optional[str] = None
    session_expires_at: Optional[datetime] = None
