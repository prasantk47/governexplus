"""
Authentication API Router

Endpoints for authentication, token management, and user sessions.
Uses JWT tokens with proper expiration and refresh handling.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Header
from typing import Optional

from sqlalchemy.orm import Session
from db.database import get_db

from services.auth_service import AuthService
from api.schemas.auth import (
    LoginRequest,
    RefreshTokenRequest,
    TokenResponse,
    ProfileResponse,
    AuthStatusResponse
)

router = APIRouter(tags=["Authentication"])

# Default tenant for demo
DEFAULT_TENANT = "tenant_default"


def get_tenant_id(x_tenant_id: Optional[str] = Header(None)) -> str:
    """Get tenant ID from header or use default"""
    return x_tenant_id or DEFAULT_TENANT


def get_client_ip(request: Request) -> Optional[str]:
    """Get client IP address from request"""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


# =============================================================================
# Authentication Endpoints
# =============================================================================

@router.post("/login", response_model=TokenResponse)
async def login(
    request: Request,
    login_data: LoginRequest,
    db: Session = Depends(get_db)
):
    """
    Authenticate user and return JWT tokens.

    - **username**: Username or email
    - **password**: User password
    - **tenant_id**: Optional tenant identifier
    - **remember_me**: Extended token validity (not implemented yet)

    Returns access token (30 min) and refresh token (7 days).
    """
    auth_service = AuthService(db)
    tenant_id = login_data.tenant_id or DEFAULT_TENANT
    ip_address = get_client_ip(request)

    # Try database authentication first
    token_response, error = auth_service.authenticate(
        tenant_id=tenant_id,
        username=login_data.username,
        password=login_data.password,
        ip_address=ip_address
    )

    # Fall back to demo authentication if database auth fails
    if not token_response:
        token_response, error = auth_service.authenticate_demo(
            username=login_data.username,
            password=login_data.password,
            tenant_id=tenant_id
        )

    if not token_response:
        raise HTTPException(
            status_code=401,
            detail=error or "Authentication failed",
            headers={"WWW-Authenticate": "Bearer"}
        )

    return token_response


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    refresh_data: RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    """
    Refresh access token using refresh token.

    - **refresh_token**: Valid refresh token

    Returns new access token and refresh token.
    """
    auth_service = AuthService(db)

    token_response, error = auth_service.refresh_tokens(refresh_data.refresh_token)

    if not token_response:
        raise HTTPException(
            status_code=401,
            detail=error or "Token refresh failed",
            headers={"WWW-Authenticate": "Bearer"}
        )

    return token_response


@router.post("/logout")
async def logout(
    request: Request,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id)
):
    """
    Logout user and invalidate session.

    In production, this would add the token to a blacklist.
    """
    auth_service = AuthService(db)

    # Extract user ID from token if available
    user_id = "unknown"
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:]
        payload, _ = auth_service.verify_token(token)
        if payload:
            user_id = payload.get("sub", "unknown")

    auth_service.logout(tenant_id, user_id, authorization)

    return {"message": "Logged out successfully"}


@router.get("/profile", response_model=ProfileResponse)
async def get_profile(
    authorization: str = Header(..., description="Bearer token"),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id)
):
    """
    Get current user's profile.

    Requires valid access token in Authorization header.
    """
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")

    token = authorization[7:]
    auth_service = AuthService(db)

    payload, error = auth_service.verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail=error or "Invalid token")

    user_id = payload.get("sub")
    profile = auth_service.get_user_profile(tenant_id, user_id)

    if not profile:
        # Return profile from token payload for demo users
        return ProfileResponse(
            id=user_id,
            username=payload.get("username", user_id),
            email=None,
            full_name=payload.get("username", user_id),
            role=payload.get("role", "end_user"),
            permissions=payload.get("permissions", []),
            department=None,
            tenant_id=tenant_id,
            is_active=True,
            created_at=payload.get("iat"),
            last_login=None,
            mfa_enabled=False,
            password_expires_at=None
        )

    return profile


@router.get("/status", response_model=AuthStatusResponse)
async def get_auth_status(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id)
):
    """
    Check authentication status.

    Returns whether the current token is valid.
    """
    if not authorization or not authorization.startswith("Bearer "):
        return AuthStatusResponse(
            authenticated=False,
            user=None,
            tenant_id=tenant_id,
            session_expires_at=None
        )

    token = authorization[7:]
    auth_service = AuthService(db)

    payload, error = auth_service.verify_token(token)
    if not payload:
        return AuthStatusResponse(
            authenticated=False,
            user=None,
            tenant_id=tenant_id,
            session_expires_at=None
        )

    from api.schemas.auth import UserInfoResponse
    from datetime import datetime

    user_info = UserInfoResponse(
        id=payload.get("sub"),
        username=payload.get("username"),
        email=None,
        full_name=payload.get("username"),
        role=payload.get("role", "end_user"),
        permissions=payload.get("permissions", []),
        department=None,
        tenant_id=payload.get("tenant_id", tenant_id),
        is_active=True,
        last_login=None
    )

    return AuthStatusResponse(
        authenticated=True,
        user=user_info,
        tenant_id=payload.get("tenant_id", tenant_id),
        session_expires_at=datetime.fromtimestamp(payload.get("exp", 0))
    )


@router.post("/verify")
async def verify_token(
    authorization: str = Header(..., description="Bearer token"),
    db: Session = Depends(get_db)
):
    """
    Verify if a token is valid.

    Returns token payload if valid.
    """
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")

    token = authorization[7:]
    auth_service = AuthService(db)

    payload, error = auth_service.verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail=error or "Invalid token")

    return {
        "valid": True,
        "user_id": payload.get("sub"),
        "role": payload.get("role"),
        "tenant_id": payload.get("tenant_id"),
        "expires_at": payload.get("exp")
    }
