"""
Authentication API Router

Endpoints for authentication, token management, user sessions, and TOTP-based MFA.
Uses JWT tokens with proper expiration and refresh handling.

MFA flow
--------
1. POST /auth/login  →  password OK, MFA enabled
        ⟶ 200  { requires_mfa: true, user_id, mfa_session }
2. POST /auth/mfa/verify  ←  { user_id, code, mfa_session }
        ⟶ 200  { access_token, refresh_token, … }   (full JWT)

MFA enrollment flow
-------------------
1. POST /auth/mfa/setup         ← (authenticated)  →  { secret, uri, qr_code_base64 }
2. POST /auth/mfa/verify-setup  ← { secret, code }  →  { message }   (MFA now active)

Disable
-------
POST /auth/mfa/disable  ← { code }  →  { message }
"""

import os
import secrets
from datetime import datetime, timedelta
from typing import Optional

import jwt
from fastapi import APIRouter, Depends, HTTPException, Header, Request
from sqlalchemy.orm import Session

from db.database import get_db
from db.models.user import User
from services.auth_service import (
    AuthService,
    JWT_SECRET,
    JWT_ALGORITHM,
    SESSION_TIMEOUT_MINUTES,
    ROLE_PERMISSIONS,
)
from core.auth import MFAService
from api.schemas.auth import (
    LoginRequest,
    RefreshTokenRequest,
    TokenResponse,
    ProfileResponse,
    AuthStatusResponse,
    MFASetupResponse,
    MFAVerifySetupRequest,
    MFAVerifyRequest,
    MFADisableRequest,
    MFAChallengeResponse,
)
from api.middleware.rate_limit import limiter, RATE_LIMIT_AUTH

router = APIRouter(tags=["Authentication"])

# Default tenant for demo
DEFAULT_TENANT = "tenant_default"

# Short-lived MFA session tokens: 5-minute window
MFA_SESSION_EXPIRE_MINUTES = 5
MFA_SESSION_CLAIM = "mfa_session"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_tenant_id(x_tenant_id: Optional[str] = Header(None)) -> str:
    """Get tenant ID from header or use default."""
    return x_tenant_id or DEFAULT_TENANT


def get_client_ip(request: Request) -> Optional[str]:
    """Get client IP address from request."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


def _create_mfa_session_token(user_id: int, tenant_id: str) -> str:
    """
    Create a short-lived (5 min) JWT whose 'type' is 'mfa_session'.
    This token is only valid for the /auth/mfa/verify endpoint.
    """
    now = datetime.utcnow()
    payload = {
        "sub": str(user_id),
        "tenant_id": tenant_id,
        "type": MFA_SESSION_CLAIM,
        "iat": now,
        "exp": now + timedelta(minutes=MFA_SESSION_EXPIRE_MINUTES),
        "jti": secrets.token_hex(16),  # unique nonce prevents replay
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def _verify_mfa_session_token(token: str, expected_user_id: int) -> Optional[dict]:
    """
    Verify the short-lived MFA session token.
    Returns the payload if valid, None otherwise.
    """
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        if payload.get("type") != MFA_SESSION_CLAIM:
            return None
        if int(payload.get("sub", -1)) != expected_user_id:
            return None
        return payload
    except jwt.PyJWTError:
        return None


def _get_db_user_by_int_id(db: Session, user_id: int) -> Optional[User]:
    """Fetch a User row by its integer PK."""
    return db.query(User).filter(User.id == user_id).first()


# ---------------------------------------------------------------------------
# Authentication Endpoints
# ---------------------------------------------------------------------------

@router.post("/login")
@limiter.limit(RATE_LIMIT_AUTH)
async def login(
    request: Request,
    login_data: LoginRequest,
    db: Session = Depends(get_db),
):
    """
    Authenticate user and return JWT tokens **or** an MFA challenge.

    - **username**: Username or email
    - **password**: User password
    - **tenant_id**: Optional tenant identifier

    If the user has MFA enabled:
        Returns `{ requires_mfa: true, user_id, mfa_session }`.
        The client must then call `POST /auth/mfa/verify` with the TOTP code.

    Otherwise:
        Returns the standard `{ access_token, refresh_token, … }` response.
    """
    auth_service = AuthService(db)
    tenant_id = login_data.tenant_id or DEFAULT_TENANT
    ip_address = get_client_ip(request)

    # Try DB authentication first, fall back to dev mode
    token_response, error = auth_service.authenticate(
        tenant_id=tenant_id,
        username=login_data.username,
        password=login_data.password,
        ip_address=ip_address,
    )

    if not token_response:
        token_response, error = auth_service.authenticate_dev(
            username=login_data.username,
            password=login_data.password,
            tenant_id=tenant_id,
        )

    if not token_response:
        raise HTTPException(
            status_code=401,
            detail=error or "Authentication failed",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # -----------------------------------------------------------------------
    # MFA gate: if the user has MFA enabled we must NOT return the JWT yet.
    # Instead, return a short-lived MFA session token so the client can call
    # /auth/mfa/verify with the TOTP code.
    # -----------------------------------------------------------------------
    # Resolve the DB User record to check mfa_enabled.
    # token_response.user.id is the user_id string (not the integer PK).
    db_user = (
        db.query(User)
        .filter(
            User.tenant_id == tenant_id,
            User.user_id == token_response.user.id,
        )
        .first()
    )

    if db_user and getattr(db_user, "mfa_enabled", False):
        mfa_session = _create_mfa_session_token(db_user.id, tenant_id)
        return MFAChallengeResponse(
            requires_mfa=True,
            user_id=db_user.id,
            mfa_session=mfa_session,
        )

    return token_response


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    refresh_data: RefreshTokenRequest,
    db: Session = Depends(get_db),
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
            headers={"WWW-Authenticate": "Bearer"},
        )

    return token_response


@router.post("/logout")
async def logout(
    request: Request,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
):
    """
    Logout user and invalidate session.
    In production this adds the token to a blacklist.
    """
    auth_service = AuthService(db)

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
    tenant_id: str = Depends(get_tenant_id),
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
            password_expires_at=None,
        )

    # Enrich mfa_enabled from DB if possible
    db_user = (
        db.query(User)
        .filter(User.tenant_id == tenant_id, User.user_id == user_id)
        .first()
    )
    if db_user:
        profile.mfa_enabled = bool(getattr(db_user, "mfa_enabled", False))

    return profile


@router.get("/status", response_model=AuthStatusResponse)
async def get_auth_status(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
):
    """Check authentication status. Returns whether the current token is valid."""
    if not authorization or not authorization.startswith("Bearer "):
        return AuthStatusResponse(
            authenticated=False,
            user=None,
            tenant_id=tenant_id,
            session_expires_at=None,
        )

    token = authorization[7:]
    auth_service = AuthService(db)

    payload, error = auth_service.verify_token(token)
    if not payload:
        return AuthStatusResponse(
            authenticated=False,
            user=None,
            tenant_id=tenant_id,
            session_expires_at=None,
        )

    from api.schemas.auth import UserInfoResponse

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
        last_login=None,
    )

    return AuthStatusResponse(
        authenticated=True,
        user=user_info,
        tenant_id=payload.get("tenant_id", tenant_id),
        session_expires_at=datetime.fromtimestamp(payload.get("exp", 0)),
    )


@router.post("/verify")
async def verify_token_endpoint(
    authorization: str = Header(..., description="Bearer token"),
    db: Session = Depends(get_db),
):
    """Verify if a token is valid. Returns token payload if valid."""
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
        "expires_at": payload.get("exp"),
    }


# ---------------------------------------------------------------------------
# MFA Endpoints
# ---------------------------------------------------------------------------

@router.post("/mfa/setup", response_model=MFASetupResponse)
async def mfa_setup(
    authorization: str = Header(..., description="Bearer token"),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
):
    """
    Generate a new TOTP secret + QR code for the authenticated user.

    The client should display the QR code to the user (or allow manual secret entry),
    then call `POST /auth/mfa/verify-setup` with the 6-digit code to activate MFA.
    The secret is **not** stored yet — it is only persisted after successful verification.

    Returns:
        secret        — base32 TOTP secret (for manual entry in authenticator apps)
        uri           — otpauth:// URI (encode this as a QR code on the client)
        qr_code_base64 — PNG QR code as base64 string, ready for `<img src="data:image/png;base64,…">`
    """
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")

    token = authorization[7:]
    auth_service = AuthService(db)
    payload, error = auth_service.verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail=error or "Invalid token")

    user_id_str = payload.get("sub")
    db_user = (
        db.query(User)
        .filter(User.tenant_id == payload.get("tenant_id", tenant_id), User.user_id == user_id_str)
        .first()
    )

    # Determine an email/label to embed in the QR code
    email = (db_user.email if db_user else None) or user_id_str

    secret = MFAService.generate_secret()
    uri = MFAService.get_totp_uri(secret, email)
    qr_b64 = MFAService.generate_qr_base64(uri)

    return MFASetupResponse(secret=secret, uri=uri, qr_code_base64=qr_b64)


@router.post("/mfa/verify-setup")
async def mfa_verify_setup(
    body: MFAVerifySetupRequest,
    authorization: str = Header(..., description="Bearer token"),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
):
    """
    Verify the TOTP code and **activate** MFA for the authenticated user.

    The client must supply both the `secret` (received from `/auth/mfa/setup`) and
    a valid `code` generated by the authenticator app.  On success the secret is
    persisted and MFA is enabled.

    Body:
        secret — base32 secret from /auth/mfa/setup
        code   — 6-digit TOTP code
    """
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")

    token = authorization[7:]
    auth_service = AuthService(db)
    payload, error = auth_service.verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail=error or "Invalid token")

    if not MFAService.verify_totp(body.secret, body.code):
        raise HTTPException(
            status_code=400,
            detail="Invalid TOTP code. Check your authenticator app and try again.",
        )

    user_id_str = payload.get("sub")
    db_user = (
        db.query(User)
        .filter(User.tenant_id == payload.get("tenant_id", tenant_id), User.user_id == user_id_str)
        .first()
    )
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    # Persist secret + enable flag directly via the session already open
    db_user.mfa_secret = body.secret
    db_user.mfa_enabled = True
    db.commit()

    return {"message": "MFA has been enabled for your account."}


@router.post("/mfa/verify", response_model=TokenResponse)
@limiter.limit(RATE_LIMIT_AUTH)
async def mfa_verify(
    request: Request,
    body: MFAVerifyRequest,
    db: Session = Depends(get_db),
):
    """
    Exchange a valid TOTP code + MFA session token for a full JWT pair.

    Call this after `/auth/login` returns `{ requires_mfa: true }`.

    Body:
        user_id     — integer DB PK from the MFA challenge response
        code        — 6-digit TOTP code from the authenticator app
        mfa_session — short-lived token from the login MFA challenge response

    Returns the standard token response on success.
    """
    # Verify the short-lived MFA session token
    mfa_payload = _verify_mfa_session_token(body.mfa_session, body.user_id)
    if not mfa_payload:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired MFA session. Please log in again.",
        )

    # Load the user
    db_user = _get_db_user_by_int_id(db, body.user_id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    if not getattr(db_user, "mfa_enabled", False) or not db_user.mfa_secret:
        raise HTTPException(status_code=400, detail="MFA is not enabled for this account")

    # Verify the TOTP code
    if not MFAService.verify_totp(db_user.mfa_secret, body.code):
        raise HTTPException(
            status_code=401,
            detail="Invalid TOTP code. Please try again.",
        )

    # TOTP valid — issue full JWT pair
    tenant_id = mfa_payload.get("tenant_id", DEFAULT_TENANT)
    auth_service = AuthService(db)
    user_role = auth_service._determine_role(db_user)
    token_response = auth_service._create_tokens(db_user, tenant_id, user_role)

    return token_response


@router.post("/mfa/disable")
async def mfa_disable(
    body: MFADisableRequest,
    authorization: str = Header(..., description="Bearer token"),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
):
    """
    Disable MFA for the authenticated user.

    The user must supply a valid current TOTP code to confirm they still control
    the authenticator app.  This prevents an attacker with a stolen session from
    silently disabling MFA.

    Body:
        code — 6-digit TOTP code from the current authenticator app
    """
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")

    token = authorization[7:]
    auth_service = AuthService(db)
    payload, error = auth_service.verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail=error or "Invalid token")

    user_id_str = payload.get("sub")
    db_user = (
        db.query(User)
        .filter(User.tenant_id == payload.get("tenant_id", tenant_id), User.user_id == user_id_str)
        .first()
    )
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    if not getattr(db_user, "mfa_enabled", False):
        raise HTTPException(status_code=400, detail="MFA is not enabled on this account")

    if not db_user.mfa_secret:
        raise HTTPException(status_code=500, detail="MFA secret is missing — contact support")

    # Require a valid TOTP code before disabling
    if not MFAService.verify_totp(db_user.mfa_secret, body.code):
        raise HTTPException(
            status_code=401,
            detail="Invalid TOTP code. MFA has not been disabled.",
        )

    # Clear MFA
    db_user.mfa_secret = None
    db_user.mfa_enabled = False
    db.commit()

    return {"message": "MFA has been disabled for your account."}
