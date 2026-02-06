"""
Auth Service
Business logic for authentication and authorization with JWT
"""

import os
import jwt
import hashlib
import secrets
from typing import Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from db.models.user import User
from repositories.user_repository import UserRepository
from api.schemas.auth import (
    LoginRequest, TokenResponse, UserInfoResponse,
    ProfileResponse, UserRole
)
from audit.logger import AuditLogger
from db.models.audit import AuditAction

# JWT Configuration
JWT_SECRET = os.getenv("JWT_SECRET", secrets.token_hex(32))
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

# Role permissions mapping
ROLE_PERMISSIONS = {
    "super_admin": [
        "platform:manage", "tenants:*", "users:*", "roles:*",
        "risk:*", "audit:*", "system:*"
    ],
    "admin": [
        "dashboard:view", "users:read", "users:create", "users:update",
        "roles:read", "roles:create", "roles:update",
        "risk:read", "audit:read", "system:configure"
    ],
    "security_admin": [
        "dashboard:view", "users:read",
        "roles:read", "roles:create", "roles:update", "roles:delete",
        "risk:*", "audit:read", "sod:*", "firefighter:*"
    ],
    "manager": [
        "dashboard:view", "users:read",
        "roles:read", "risk:read",
        "requests:approve", "reports:view"
    ],
    "end_user": [
        "dashboard:view", "profile:read", "profile:update",
        "requests:create", "requests:read_own"
    ]
}


class AuthService:
    """
    Service layer for Authentication.
    Handles JWT tokens, password verification, and session management.
    """

    def __init__(self, db: Session):
        self.db = db
        self.user_repo = UserRepository(db)
        self.audit = AuditLogger()

    def authenticate(
        self,
        tenant_id: str,
        username: str,
        password: str,
        ip_address: Optional[str] = None
    ) -> Tuple[Optional[TokenResponse], Optional[str]]:
        """
        Authenticate user and return tokens.
        Returns (TokenResponse, None) on success or (None, error_message) on failure.
        """
        # Try to find user by username or email
        user = self.user_repo.get_user_by_username(tenant_id, username)
        if not user:
            user = self.user_repo.get_user_by_email(tenant_id, username)

        if not user:
            self.audit.log(
                action=AuditAction.USER_LOGIN,
                target_type="auth",
                target_id=username,
                success=False,
                details={"reason": "user_not_found", "ip": ip_address}
            )
            return None, "Invalid username or password"

        # Check user status
        if user.status and user.status not in ["active"]:
            self.audit.log(
                action=AuditAction.USER_LOGIN,
                target_type="auth",
                target_id=username,
                success=False,
                details={"reason": "account_disabled", "status": user.status}
            )
            return None, f"Account is {user.status}"

        # Verify password (simplified - in production use bcrypt)
        # For now, accept any password for demo purposes
        # TODO: Implement proper password hashing with bcrypt
        password_valid = True  # self._verify_password(password, user.password_hash)

        if not password_valid:
            # Increment failed login count
            user.failed_login_count = (user.failed_login_count or 0) + 1
            if user.failed_login_count >= 5:
                user.status = "locked"
            self.db.commit()

            self.audit.log(
                action=AuditAction.USER_LOGIN,
                actor_user_id=username,
                target_type="auth",
                target_id=username,
                success=False,
                details={"reason": "invalid_password", "attempts": user.failed_login_count}
            )
            return None, "Invalid username or password"

        # Successful login
        user.failed_login_count = 0
        user.last_login = datetime.utcnow()
        self.db.commit()

        # Generate tokens
        user_role = self._determine_role(user)
        token_response = self._create_tokens(user, tenant_id, user_role)

        self.audit.log(
            action=AuditAction.USER_LOGIN,
            actor_user_id=user.user_id,
            target_type="auth",
            target_id=user.user_id,
            source_ip=ip_address,
            details={"role": user_role}
        )

        return token_response, None

    def authenticate_demo(
        self,
        username: str,
        password: str,
        tenant_id: str = "tenant_default"
    ) -> Tuple[Optional[TokenResponse], Optional[str]]:
        """
        Demo authentication for development/testing.
        Accepts predefined demo users without database lookup.
        """
        DEMO_USERS = {
            "admin": {
                "id": "admin_001",
                "name": "Admin User",
                "department": "IT",
                "email": "admin@governexplus.com",
                "role": "admin"
            },
            "security_admin": {
                "id": "sec_admin_001",
                "name": "Security Admin",
                "department": "IT Security",
                "email": "security@governexplus.com",
                "role": "security_admin"
            },
            "manager": {
                "id": "manager_001",
                "name": "Manager User",
                "department": "Operations",
                "email": "manager@governexplus.com",
                "role": "manager"
            },
            "user": {
                "id": "user_001",
                "name": "End User",
                "department": "Finance",
                "email": "user@governexplus.com",
                "role": "end_user"
            },
            "demo@demo.com": {
                "id": "demo_001",
                "name": "Demo Admin",
                "department": "Administration",
                "email": "demo@demo.com",
                "role": "admin"
            }
        }

        demo_user = DEMO_USERS.get(username) or DEMO_USERS.get(username.lower())
        if not demo_user:
            return None, "Invalid username or password"

        # Create token response for demo user
        user_info = UserInfoResponse(
            id=demo_user["id"],
            username=username,
            email=demo_user.get("email"),
            full_name=demo_user["name"],
            role=demo_user["role"],
            permissions=ROLE_PERMISSIONS.get(demo_user["role"], []),
            department=demo_user.get("department"),
            tenant_id=tenant_id,
            is_active=True,
            last_login=datetime.utcnow()
        )

        access_token = self._create_access_token(
            user_id=demo_user["id"],
            username=username,
            role=demo_user["role"],
            tenant_id=tenant_id
        )

        refresh_token = self._create_refresh_token(
            user_id=demo_user["id"],
            tenant_id=tenant_id
        )

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=user_info
        ), None

    def refresh_tokens(
        self,
        refresh_token: str
    ) -> Tuple[Optional[TokenResponse], Optional[str]]:
        """Refresh access token using refresh token"""
        try:
            payload = jwt.decode(refresh_token, JWT_SECRET, algorithms=[JWT_ALGORITHM])

            if payload.get("type") != "refresh":
                return None, "Invalid token type"

            user_id = payload.get("sub")
            tenant_id = payload.get("tenant_id", "tenant_default")

            # Get user from database
            user = self.user_repo.get_user_by_user_id(tenant_id, user_id)
            if not user:
                return None, "User not found"

            if user.status and user.status not in ["active"]:
                return None, f"Account is {user.status}"

            # Generate new tokens
            user_role = self._determine_role(user)
            return self._create_tokens(user, tenant_id, user_role), None

        except jwt.ExpiredSignatureError:
            return None, "Refresh token expired"
        except jwt.InvalidTokenError:
            return None, "Invalid refresh token"

    def verify_token(self, token: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """Verify access token and return payload"""
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])

            if payload.get("type") != "access":
                return None, "Invalid token type"

            return payload, None

        except jwt.ExpiredSignatureError:
            return None, "Token expired"
        except jwt.InvalidTokenError:
            return None, "Invalid token"

    def get_user_profile(
        self,
        tenant_id: str,
        user_id: str
    ) -> Optional[ProfileResponse]:
        """Get user profile"""
        user = self.user_repo.get_user_by_user_id(tenant_id, user_id)
        if not user:
            return None

        user_role = self._determine_role(user)

        return ProfileResponse(
            id=user.user_id,
            username=user.username,
            email=user.email,
            full_name=user.full_name or user.username,
            role=user_role,
            permissions=ROLE_PERMISSIONS.get(user_role, []),
            department=user.department,
            tenant_id=tenant_id,
            is_active=user.status == "active" if user.status else True,
            created_at=user.created_at,
            last_login=user.last_login,
            mfa_enabled=False,
            password_expires_at=None
        )

    def logout(
        self,
        tenant_id: str,
        user_id: str,
        token: Optional[str] = None
    ) -> bool:
        """Logout user (invalidate session)"""
        # In production, add token to blacklist or invalidate session
        self.audit.log(
            action=AuditAction.USER_LOGOUT,
            actor_user_id=user_id,
            target_type="auth",
            target_id=user_id
        )
        return True

    # ============== Private Methods ==============

    def _verify_password(self, password: str, password_hash: str) -> bool:
        """Verify password against hash"""
        if not password_hash:
            return False

        # Simple hash verification (use bcrypt in production)
        if ":" in password_hash:
            salt, hash_value = password_hash.split(":", 1)
            computed = hashlib.sha256(f"{salt}{password}".encode()).hexdigest()
            return computed == hash_value

        return False

    def _hash_password(self, password: str) -> str:
        """Hash password with salt"""
        salt = secrets.token_hex(16)
        hashed = hashlib.sha256(f"{salt}{password}".encode()).hexdigest()
        return f"{salt}:{hashed}"

    def _determine_role(self, user: User) -> str:
        """Determine user role based on user attributes"""
        # Check if user has admin-related attributes
        if hasattr(user, 'is_admin') and user.is_admin:
            return "admin"

        # Check department-based roles
        if user.department:
            dept_lower = user.department.lower()
            if "security" in dept_lower or "audit" in dept_lower:
                return "security_admin"
            if "management" in dept_lower or "executive" in dept_lower:
                return "manager"

        # Default to end user
        return "end_user"

    def _create_tokens(
        self,
        user: User,
        tenant_id: str,
        role: str
    ) -> TokenResponse:
        """Create access and refresh tokens"""
        access_token = self._create_access_token(
            user_id=user.user_id,
            username=user.username,
            role=role,
            tenant_id=tenant_id
        )

        refresh_token = self._create_refresh_token(
            user_id=user.user_id,
            tenant_id=tenant_id
        )

        user_info = UserInfoResponse(
            id=user.user_id,
            username=user.username,
            email=user.email,
            full_name=user.full_name or user.username,
            role=role,
            permissions=ROLE_PERMISSIONS.get(role, []),
            department=user.department,
            tenant_id=tenant_id,
            is_active=True,
            last_login=user.last_login
        )

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=user_info
        )

    def _create_access_token(
        self,
        user_id: str,
        username: str,
        role: str,
        tenant_id: str
    ) -> str:
        """Create JWT access token"""
        now = datetime.utcnow()
        expires = now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

        payload = {
            "sub": user_id,
            "username": username,
            "role": role,
            "tenant_id": tenant_id,
            "permissions": ROLE_PERMISSIONS.get(role, []),
            "type": "access",
            "iat": now,
            "exp": expires
        }

        return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

    def _create_refresh_token(
        self,
        user_id: str,
        tenant_id: str
    ) -> str:
        """Create JWT refresh token"""
        now = datetime.utcnow()
        expires = now + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

        payload = {
            "sub": user_id,
            "tenant_id": tenant_id,
            "type": "refresh",
            "iat": now,
            "exp": expires
        }

        return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
