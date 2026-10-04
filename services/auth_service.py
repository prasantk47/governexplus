"""
Auth Service
Business logic for authentication and authorization with JWT
"""

import hashlib
import os
import jwt
import secrets
from typing import Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from passlib.context import CryptContext

from core.logging import get_logger

from db.models.user import User
from repositories.user_repository import UserRepository
from api.schemas.auth import (
    LoginRequest, TokenResponse, UserInfoResponse,
    ProfileResponse, UserRole
)
from audit.logger import AuditLogger
from db.models.audit import AuditAction

logger = get_logger(__name__)

# JWT Configuration — SECRET_KEY must be set in production
_jwt_secret_env = os.getenv("JWT_SECRET", "")
_app_env = os.getenv("APP_ENV", "development")
if not _jwt_secret_env:
    if _app_env == "production":
        raise RuntimeError(
            "FATAL: JWT_SECRET environment variable is required in production. "
            "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\""
        )
    _jwt_secret_env = secrets.token_hex(32)
    logger.warning(
        "JWT_SECRET not set — using random key. "
        "Tokens will NOT survive restarts. Set JWT_SECRET in .env for production."
    )
JWT_SECRET = _jwt_secret_env
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

# Session and lockout configuration
SESSION_TIMEOUT_MINUTES = int(os.getenv("SESSION_TIMEOUT_MINUTES", "30"))
MAX_FAILED_LOGINS = int(os.getenv("MAX_FAILED_LOGINS", "5"))
ACCOUNT_LOCKOUT_MINUTES = int(os.getenv("ACCOUNT_LOCKOUT_MINUTES", "30"))

# Password hashing — bcrypt with automatic salt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

APP_ENV = os.getenv("APP_ENV", "development")

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

    Supports three authentication backends (configurable via AUTH_BACKEND env var):
      - "local"    — bcrypt password hash (default)
      - "ldap"     — LDAP/Active Directory bind authentication
      - "graph"    — Microsoft Entra ID (Azure AD) via Graph API / MSAL
      - "ldap,local" or "graph,local" — try external first, fall back to local
    """

    # Authentication backend chain (comma-separated, tried in order)
    AUTH_BACKENDS = [b.strip().lower() for b in
                     os.getenv("AUTH_BACKEND", "local").split(",") if b.strip()]

    def __init__(self, db: Session):
        self.db = db
        self.user_repo = UserRepository(db)
        self.audit = AuditLogger()

    # ── External authentication backends ─────────────────────────────────

    def _authenticate_ldap(self, username: str, password: str) -> Tuple[bool, Optional[Dict]]:
        """
        Authenticate against LDAP/Active Directory.

        Env vars:
          LDAP_SERVER    — e.g. ldaps://ad.company.com:636
          LDAP_BASE_DN   — e.g. dc=company,dc=com
          LDAP_BIND_DN   — format string with {username}, e.g. cn={username},ou=users,dc=company,dc=com
          LDAP_USE_SSL   — true/false (default true)
          LDAP_SEARCH_FILTER — e.g. (sAMAccountName={username})

        Returns (True, user_attrs_dict) on success, (False, None) on failure.
        """
        try:
            import ldap3
        except ImportError:
            logger.error("ldap3 not installed — LDAP authentication unavailable")
            return False, None

        server_url = os.getenv("LDAP_SERVER", "")
        base_dn = os.getenv("LDAP_BASE_DN", "")
        bind_dn_template = os.getenv("LDAP_BIND_DN", "cn={username}," + base_dn)
        use_ssl = os.getenv("LDAP_USE_SSL", "true").lower() == "true"
        search_filter = os.getenv("LDAP_SEARCH_FILTER", "(sAMAccountName={username})")

        if not server_url:
            logger.error("LDAP_SERVER not configured")
            return False, None

        try:
            server = ldap3.Server(server_url, use_ssl=use_ssl, get_info=ldap3.ALL)
            bind_dn = bind_dn_template.format(username=username)
            conn = ldap3.Connection(server, user=bind_dn, password=password, auto_bind=True)

            # Search for user attributes
            user_filter = search_filter.format(username=username)
            conn.search(base_dn, user_filter, attributes=[
                "sAMAccountName", "mail", "displayName", "department",
                "title", "memberOf", "userPrincipalName"
            ])

            if conn.entries:
                entry = conn.entries[0]
                attrs = {
                    "username": str(getattr(entry, "sAMAccountName", username)),
                    "email": str(getattr(entry, "mail", "")),
                    "full_name": str(getattr(entry, "displayName", "")),
                    "department": str(getattr(entry, "department", "")),
                    "title": str(getattr(entry, "title", "")),
                    "source": "ldap",
                }
                conn.unbind()
                logger.info("LDAP auth succeeded for %s", username)
                return True, attrs

            conn.unbind()
            logger.info("LDAP bind succeeded but user not found in search: %s", username)
            return True, {"username": username, "source": "ldap"}

        except ldap3.core.exceptions.LDAPBindError:
            logger.info("LDAP bind failed for %s (invalid credentials)", username)
            return False, None
        except Exception as e:
            logger.error("LDAP auth error for %s: %s", username, str(e))
            return False, None

    def _authenticate_graph(self, username: str, password: str) -> Tuple[bool, Optional[Dict]]:
        """
        Authenticate against Microsoft Entra ID (Azure AD) using ROPC flow.

        Env vars:
          AZURE_CLIENT_ID     — App registration client ID
          AZURE_CLIENT_SECRET — App registration client secret (optional for ROPC)
          AZURE_TENANT_ID     — Azure AD tenant ID
          AZURE_AUTHORITY     — Override authority URL (optional)

        Returns (True, user_attrs_dict) on success, (False, None) on failure.
        """
        try:
            import msal
            import httpx
        except ImportError:
            logger.error("msal/httpx not installed — Graph API authentication unavailable")
            return False, None

        client_id = os.getenv("AZURE_CLIENT_ID", "")
        client_secret = os.getenv("AZURE_CLIENT_SECRET", "")
        tenant_id = os.getenv("AZURE_TENANT_ID", "")
        authority = os.getenv("AZURE_AUTHORITY", f"https://login.microsoftonline.com/{tenant_id}")

        if not client_id or not tenant_id:
            logger.error("AZURE_CLIENT_ID and AZURE_TENANT_ID required for Graph auth")
            return False, None

        try:
            # ROPC (Resource Owner Password Credential) flow
            app = msal.PublicClientApplication(client_id, authority=authority)
            scopes = ["https://graph.microsoft.com/.default"]

            result = app.acquire_token_by_username_password(
                username=username, password=password, scopes=scopes
            )

            if "access_token" not in result:
                error = result.get("error_description", result.get("error", "unknown"))
                logger.info("Graph auth failed for %s: %s", username, error)
                return False, None

            # Fetch user profile from Graph API
            token = result["access_token"]
            resp = httpx.get(
                "https://graph.microsoft.com/v1.0/me",
                headers={"Authorization": f"Bearer {token}"},
                params={"$select": "displayName,mail,department,jobTitle,userPrincipalName"},
                timeout=10,
            )

            if resp.status_code == 200:
                profile = resp.json()
                attrs = {
                    "username": profile.get("userPrincipalName", username).split("@")[0],
                    "email": profile.get("mail") or profile.get("userPrincipalName", ""),
                    "full_name": profile.get("displayName", ""),
                    "department": profile.get("department", ""),
                    "title": profile.get("jobTitle", ""),
                    "source": "azure_ad",
                }
                logger.info("Graph API auth succeeded for %s", username)
                return True, attrs

            logger.info("Graph auth token OK but /me failed (%d) for %s", resp.status_code, username)
            return True, {"username": username, "email": username, "source": "azure_ad"}

        except Exception as e:
            logger.error("Graph API auth error for %s: %s", username, str(e))
            return False, None

    def _ensure_local_user(self, tenant_id: str, username: str, attrs: Dict) -> User:
        """
        Ensure an externally-authenticated user exists locally.
        Creates or updates the local User record for JWT issuance.
        """
        user = self.user_repo.get_user_by_username(tenant_id, username)
        if not user:
            user = self.user_repo.get_user_by_email(tenant_id, attrs.get("email", ""))

        if not user:
            # Auto-provision: create local record for externally-authenticated user
            user = User(
                tenant_id=tenant_id,
                user_id=username.upper(),
                username=username,
                email=attrs.get("email", ""),
                full_name=attrs.get("full_name", username),
                department=attrs.get("department", ""),
                title=attrs.get("title", ""),
                source_system=attrs.get("source", "external"),
                status="active",
                is_platform_user=True,
            )
            self.db.add(user)
            self.db.commit()
            self.db.refresh(user)
            logger.info("Auto-provisioned local user for %s (source: %s)",
                        username, attrs.get("source"))
        else:
            # Update profile from external source
            if attrs.get("full_name"):
                user.full_name = attrs["full_name"]
            if attrs.get("email"):
                user.email = attrs["email"]
            if attrs.get("department"):
                user.department = attrs["department"]
            user.sync_source = attrs.get("source", "external")
            self.db.commit()

        return user

    # ── Main authentication method ───────────────────────────────────────

    def authenticate(
        self,
        tenant_id: str,
        username: str,
        password: str,
        ip_address: Optional[str] = None
    ) -> Tuple[Optional[TokenResponse], Optional[str]]:
        """
        Authenticate user and return tokens.
        Tries each configured backend in AUTH_BACKEND order.
        Returns (TokenResponse, None) on success or (None, error_message) on failure.
        """
        # Try external backends first (LDAP, Graph API)
        for backend in self.AUTH_BACKENDS:
            if backend == "ldap":
                success, attrs = self._authenticate_ldap(username, password)
                if success:
                    user = self._ensure_local_user(tenant_id, username, attrs or {})
                    user.failed_login_count = 0
                    user.last_login = datetime.utcnow()
                    self.db.commit()
                    user_role = self._determine_role(user)
                    token_response = self._create_tokens(user, tenant_id, user_role)
                    self.audit.log(
                        action=AuditAction.USER_LOGIN,
                        actor_user_id=user.user_id,
                        target_type="auth",
                        target_id=user.user_id,
                        source_ip=ip_address,
                        details={"role": user_role, "backend": "ldap"}
                    )
                    return token_response, None

            elif backend == "graph":
                success, attrs = self._authenticate_graph(username, password)
                if success:
                    user = self._ensure_local_user(tenant_id, username, attrs or {})
                    user.failed_login_count = 0
                    user.last_login = datetime.utcnow()
                    self.db.commit()
                    user_role = self._determine_role(user)
                    token_response = self._create_tokens(user, tenant_id, user_role)
                    self.audit.log(
                        action=AuditAction.USER_LOGIN,
                        actor_user_id=user.user_id,
                        target_type="auth",
                        target_id=user.user_id,
                        source_ip=ip_address,
                        details={"role": user_role, "backend": "graph_api"}
                    )
                    return token_response, None

            elif backend == "local":
                # Fall through to local authentication below
                break

        # ── Local (bcrypt) authentication ────────────────────────────────
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
                details={"reason": "user_not_found", "ip": ip_address,
                         "backends_tried": self.AUTH_BACKENDS}
            )
            return None, "Invalid username or password"

        # Check user status
        if user.status and user.status not in ["active"]:
            # Auto-unlock if lockout window has expired
            if user.status == "locked" and user.last_login is not None:
                lockout_expires = user.last_login + timedelta(minutes=ACCOUNT_LOCKOUT_MINUTES)
                if datetime.utcnow() >= lockout_expires:
                    user.status = "active"
                    user.failed_login_count = 0
                    self.db.commit()
                else:
                    self.audit.log(
                        action=AuditAction.USER_LOGIN,
                        target_type="auth",
                        target_id=username,
                        success=False,
                        details={"reason": "account_locked", "status": user.status}
                    )
                    remaining = int((lockout_expires - datetime.utcnow()).total_seconds() / 60)
                    return None, f"Account locked. Try again in {remaining} minute(s)."
            elif user.status != "locked":
                self.audit.log(
                    action=AuditAction.USER_LOGIN,
                    target_type="auth",
                    target_id=username,
                    success=False,
                    details={"reason": "account_disabled", "status": user.status}
                )
                return None, f"Account is {user.status}"

        # Check failed login count threshold before attempting password verify
        current_failures = user.failed_login_count or 0
        if current_failures >= MAX_FAILED_LOGINS:
            user.status = "locked"
            self.db.commit()
            self.audit.log(
                action=AuditAction.USER_LOGIN,
                target_type="auth",
                target_id=username,
                success=False,
                details={
                    "reason": "account_locked_max_failures",
                    "failed_count": current_failures,
                }
            )
            return None, (
                f"Account locked after {MAX_FAILED_LOGINS} failed attempts. "
                f"Contact your administrator or wait {ACCOUNT_LOCKOUT_MINUTES} minutes."
            )

        # Verify password with bcrypt
        password_valid = self._verify_password(password, user.password_hash)

        if not password_valid:
            # Increment failed login count
            user.failed_login_count = current_failures + 1
            if user.failed_login_count >= MAX_FAILED_LOGINS:
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

        # Successful login — reset failure counter
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

    def authenticate_dev(
        self,
        username: str,
        password: str,
        tenant_id: str = "tenant_default"
    ) -> Tuple[Optional[TokenResponse], Optional[str]]:
        """
        Dev-mode authentication — only active when APP_ENV=development.
        Uses DB users but falls back to seeded demo accounts.
        Always requires password verification.
        """
        if APP_ENV not in ("development", "testing"):
            return None, "Dev-mode authentication is disabled in production"

        # Try DB user first (even in dev mode, passwords must match)
        result, error = self.authenticate(tenant_id, username, password)
        if result:
            return result, None

        # If no DB user found, reject — run seed script to create users
        return None, (
            "User not found. Run 'python scripts/seed_all.py' to create initial users."
        )

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
        if AuthService.is_token_blacklisted(token):
            return None, "Token has been revoked"
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
            mfa_enabled=bool(getattr(user, "mfa_enabled", False)),
            password_expires_at=None
        )

    # Token blacklist — Redis if available, else in-memory fallback
    _blacklisted_tokens: set = set()
    _redis_client = None
    _redis_checked = False

    @classmethod
    def _get_redis(cls):
        """Lazy-init Redis connection for token blacklist."""
        if cls._redis_checked:
            return cls._redis_client
        cls._redis_checked = True
        redis_url = os.getenv("RATE_LIMIT_STORAGE", "memory://")
        if redis_url.startswith("redis://"):
            try:
                import redis
                cls._redis_client = redis.from_url(redis_url, decode_responses=True)
                cls._redis_client.ping()
                logger.info("Token blacklist using Redis")
            except Exception as exc:
                logger.warning(f"Redis unavailable for token blacklist, using memory: {exc}")
                cls._redis_client = None
        return cls._redis_client

    def logout(
        self,
        tenant_id: str,
        user_id: str,
        token: Optional[str] = None
    ) -> bool:
        """Logout user — blacklists the token until expiry"""
        if token:
            token_hash = hashlib.sha256(token.encode()).hexdigest()
            AuthService._blacklisted_tokens.add(token)

            # Persist to Redis (with TTL matching token expiry)
            r = AuthService._get_redis()
            if r:
                try:
                    r.setex(f"blacklist:{token_hash}", SESSION_TIMEOUT_MINUTES * 60, "1")
                except Exception:
                    pass

        self.audit.log(
            action=AuditAction.USER_LOGOUT,
            actor_user_id=user_id,
            target_type="auth",
            target_id=user_id
        )
        return True

    @classmethod
    def is_token_blacklisted(cls, token: str) -> bool:
        """Check if a token has been revoked (Redis → in-memory fallback)."""
        if token in cls._blacklisted_tokens:
            return True
        r = cls._get_redis()
        if r:
            try:
                token_hash = hashlib.sha256(token.encode()).hexdigest()
                if r.exists(f"blacklist:{token_hash}"):
                    cls._blacklisted_tokens.add(token)  # cache locally
                    return True
            except Exception:
                pass
        return False

    # ============== Private Methods ==============

    def _verify_password(self, password: str, password_hash: str) -> bool:
        """Verify password against bcrypt hash"""
        if not password_hash:
            return False
        return pwd_context.verify(password, password_hash)

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash password with bcrypt (automatic salt)"""
        return pwd_context.hash(password)

    # All recognized functional role values stored in user_type
    _KNOWN_ROLES = {
        "platform_admin", "tenant_admin", "admin", "super_admin",
        "ciso", "compliance_officer", "risk_manager",
        "security_admin", "it_security",
        "line_manager", "business_user",
        "external_auditor", "internal_auditor", "auditor",
        "control_owner", "sox_owner",
        "firefighter_owner", "firefighter_controller", "firefighter_user",
        "hr_manager", "process_owner", "it_operations",
        "read_only", "mitigation_monitor",
        "vendor_manager", "role_owner", "risk_owner",
        "manager", "end_user",
    }

    def _determine_role(self, user: User) -> str:
        """Determine user role from user_type (primary) or legacy fallbacks."""
        # user_type is the authoritative source — pass it through directly
        if hasattr(user, 'user_type') and user.user_type:
            ut = user.user_type.lower()
            if ut in self._KNOWN_ROLES:
                return ut

        # Legacy: is_admin flag
        if hasattr(user, 'is_admin') and user.is_admin:
            return "admin"

        # Legacy: well-known admin usernames
        uname = (user.username or "").lower()
        if uname in ("admin", "sysadmin", "administrator"):
            return "admin"

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
            expires_in=SESSION_TIMEOUT_MINUTES * 60,
            user=user_info
        )

    def _create_access_token(
        self,
        user_id: str,
        username: str,
        role: str,
        tenant_id: str
    ) -> str:
        """
        Create JWT access token.

        Expiry is controlled by SESSION_TIMEOUT_MINUTES (env var) so that
        the session idle-timeout and token lifetime are kept in sync.
        """
        now = datetime.utcnow()
        expires = now + timedelta(minutes=SESSION_TIMEOUT_MINUTES)

        payload = {
            "sub": user_id,
            "username": username,
            "role": role,
            "roles": [role],
            "tenant_id": tenant_id,
            "permissions": ROLE_PERMISSIONS.get(role, []),
            "type": "access",
            "iat": now,
            "exp": expires,
            "session_timeout_minutes": SESSION_TIMEOUT_MINUTES,
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
