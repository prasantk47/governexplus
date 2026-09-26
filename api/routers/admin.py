"""
Super Admin API Router
Platform administration endpoints for super admin users

Provides:
- Super admin authentication
- Tenant management backed by the database (create, view, suspend, delete)
- User management across tenants
- Platform statistics
- System configuration
"""

import json
import logging
import re
import secrets
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from db.database import get_db
from db.models.tenant import AdminSession, Tenant, TIER_DEFAULT_MODULES, TIER_MAX_USERS
from db.models.user import User
from api.middleware.rate_limit import limiter, RATE_LIMIT_AUTH

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Super Admin"])


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class AdminLoginRequest(BaseModel):
    email: str
    password: str = Field(..., min_length=8)


class AdminLoginResponse(BaseModel):
    success: bool
    token: str = ""
    admin: Dict[str, Any] = {}
    message: str = ""


class CreateTenantRequest(BaseModel):
    company_name: str
    admin_email: str
    admin_name: str
    admin_password: str = ""
    tier: str = "professional"
    trial_days: int = 14
    modules: List[str] = []


class TenantUserRequest(BaseModel):
    email: str
    name: str
    role: str = "user"
    department: str = ""
    password: str = ""


class UpdateTenantRequest(BaseModel):
    name: Optional[str] = None
    tier: Optional[str] = None
    status: Optional[str] = None
    modules: Optional[List[str]] = None
    max_users: Optional[int] = None


# ---------------------------------------------------------------------------
# Session expiry (hours).  Admin sessions time out after this period.
# ---------------------------------------------------------------------------
ADMIN_SESSION_HOURS = 8


# ---------------------------------------------------------------------------
# Auth dependency — every admin endpoint (except login) must present a valid
# session token in the Authorization: Bearer <token> header.
# ---------------------------------------------------------------------------

async def require_admin_session(
    authorization: str = Header(None),
    db: Session = Depends(get_db),
) -> Dict:
    """Verify that the request carries a valid admin session token.

    Returns the session dict on success; raises 401 otherwise.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Admin authentication required")

    token = authorization.split(" ", 1)[1]
    session = db.query(AdminSession).filter(AdminSession.token == token).first()
    if not session or session.is_expired():
        if session:
            db.delete(session)
            db.commit()
        raise HTTPException(status_code=401, detail="Invalid or expired admin session")

    return session.to_dict()


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def load_super_admin() -> Optional[Dict]:
    """Load super admin credentials from config/super_admin.json."""
    config_file = Path(__file__).parent.parent.parent / "config" / "super_admin.json"
    if config_file.exists():
        with open(config_file, "r") as f:
            return json.load(f)
    return None


def verify_password(password: str, hashed: str) -> bool:
    """Verify a plaintext password against a bcrypt hash."""
    from passlib.context import CryptContext
    pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
    try:
        return pwd_ctx.verify(password, hashed)
    except Exception:
        return False


def hash_password(password: str) -> str:
    """Hash a plaintext password with bcrypt."""
    from passlib.context import CryptContext
    pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
    return pwd_ctx.hash(password)


def generate_token() -> str:
    """Generate a random admin session token."""
    return f"admin_{secrets.token_hex(32)}"


def _slugify(text: str) -> str:
    """Convert a company name into a URL-safe slug."""
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def _tenant_to_api(tenant: Tenant, users: List[Dict] | None = None) -> Dict[str, Any]:
    """
    Convert a Tenant ORM object to the API response dict expected by
    the frontend and super-admin dashboard.
    """
    data = tenant.to_dict()
    # Compatibility shim: expose modules_enabled as 'modules'
    data["modules"] = data.pop("modules_enabled", [])
    # Placeholder: user counts are stored on the User table; for listing
    # endpoints we avoid an N+1 query and return 0 by default.
    data.setdefault("users_count", 0)
    data.setdefault("systems_connected", 0)
    data.setdefault("last_activity", data.get("updated_at"))
    data.setdefault("billing", None)
    if users is not None:
        data["users"] = users
        data["user_stats"] = {
            "total": len(users),
            "admins": sum(1 for u in users if u.get("role") == "admin"),
            "active": sum(1 for u in users if u.get("status") == "active"),
        }
    return data


def seed_default_tenant(db: Session) -> None:
    """
    Ensure the built-in default tenant exists in the database.

    Called once at application startup via init_db / lifespan hooks and
    may also be called lazily from any endpoint that uses get_db.
    """
    existing = db.query(Tenant).filter(Tenant.id == "tenant_default").first()
    if existing:
        return

    default_tenant = Tenant(
        id="tenant_default",
        name="Default Organization",
        slug="default",
        status="active",
        tier="enterprise",
        admin_email="admin@governexplus.local",
        admin_name="Platform Admin",
        max_users=TIER_MAX_USERS.get("enterprise", 1000),
        modules_enabled=TIER_DEFAULT_MODULES.get("enterprise", []),
        settings={},
    )
    db.add(default_tenant)
    try:
        db.commit()
        logger.info("Default tenant seeded into database.")
    except Exception as exc:
        db.rollback()
        logger.warning("Could not seed default tenant (may already exist): %s", exc)


# ---------------------------------------------------------------------------
# Authentication endpoints
# ---------------------------------------------------------------------------

@router.post("/login", response_model=AdminLoginResponse)
@limiter.limit(RATE_LIMIT_AUTH)
async def admin_login(request: Request, body: AdminLoginRequest, db: Session = Depends(get_db)):
    """
    Authenticate a super admin user.

    Returns a session token for subsequent API calls.
    """
    admin = load_super_admin()

    if not admin:
        raise HTTPException(
            status_code=503,
            detail="Super admin not configured. Run the setup wizard first.",
        )

    if body.email != admin.get("email"):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not verify_password(body.password, admin.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Prune expired sessions
    db.query(AdminSession).filter(AdminSession.expires_at < datetime.utcnow()).delete()

    token = generate_token()
    session = AdminSession(
        token=token,
        email=admin["email"],
        name=admin["name"],
        logged_in_at=datetime.utcnow(),
        expires_at=datetime.utcnow() + timedelta(hours=ADMIN_SESSION_HOURS),
    )
    db.add(session)
    db.commit()

    return AdminLoginResponse(
        success=True,
        token=token,
        admin={
            "email": admin["email"],
            "name": admin["name"],
            "role": "super_admin",
            "permissions": admin.get("permissions", []),
        },
        message="Logged in successfully",
    )


@router.post("/logout")
async def admin_logout(
    authorization: str = Header(None),
    db: Session = Depends(get_db),
):
    """Logout and invalidate the current session token."""
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ", 1)[1]
        db.query(AdminSession).filter(AdminSession.token == token).delete()
        db.commit()

    return {"success": True, "message": "Logged out"}


@router.get("/verify")
async def verify_session(
    authorization: str = Header(None),
    db: Session = Depends(get_db),
):
    """Return 200 if the bearer token maps to a live admin session."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")

    token = authorization.split(" ", 1)[1]
    session = db.query(AdminSession).filter(AdminSession.token == token).first()

    if not session or session.is_expired():
        if session:
            db.delete(session)
            db.commit()
        raise HTTPException(status_code=401, detail="Session expired or invalid")

    return {
        "valid": True,
        "admin": {
            "email": session.email,
            "name": session.name,
        },
    }


# ---------------------------------------------------------------------------
# Dashboard statistics
# ---------------------------------------------------------------------------

@router.get("/dashboard/stats")
async def get_dashboard_stats(
    db: Session = Depends(get_db),
    _admin: Dict = Depends(require_admin_session),
):
    """Return platform-wide statistics for the admin dashboard."""
    seed_default_tenant(db)

    tenants = db.query(Tenant).filter(Tenant.is_deleted == False).all()  # noqa: E712

    total = len(tenants)
    active = sum(1 for t in tenants if t.status == "active")
    trial = sum(1 for t in tenants if t.status == "trial")
    suspended = sum(1 for t in tenants if t.status == "suspended")

    # Count platform users across all tenants
    total_users = db.query(User).count()

    return {
        "tenants": {
            "total": total,
            "active": active,
            "trial": trial,
            "suspended": suspended,
        },
        "users": {
            "total": total_users,
            "active_today": 0,       # Requires last_login aggregation — left for future
            "new_this_month": 0,
        },
        "revenue": {
            "mrr": 0,
            "arr": 0,
            "growth": 0.0,
        },
        "systems": {
            "connected": 0,
            "sync_healthy": 100,
        },
        "api": {
            "calls_today": 0,
            "avg_latency_ms": 0,
            "error_rate": 0.0,
        },
        "recent_activity": [],
    }


# ---------------------------------------------------------------------------
# Tenant management
# ---------------------------------------------------------------------------

@router.get("/tenants")
async def list_all_tenants(
    status: Optional[str] = None,
    tier: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
    _admin: Dict = Depends(require_admin_session),
):
    """List all tenants with optional filters for status, tier, and name search."""
    seed_default_tenant(db)

    query = db.query(Tenant).filter(Tenant.is_deleted == False)  # noqa: E712

    if status:
        query = query.filter(Tenant.status == status)

    if tier:
        query = query.filter(Tenant.tier == tier)

    if search:
        search_pattern = f"%{search.lower()}%"
        query = query.filter(
            Tenant.name.ilike(search_pattern) | Tenant.admin_email.ilike(search_pattern)
        )

    tenants = query.limit(limit).all()

    return {
        "tenants": [_tenant_to_api(t) for t in tenants],
        "total": len(tenants),
        "filters": {
            "status": status,
            "tier": tier,
            "search": search,
        },
    }


@router.get("/tenants/{tenant_id}")
async def get_tenant_details(
    tenant_id: str,
    db: Session = Depends(get_db),
    _admin: Dict = Depends(require_admin_session),
):
    """Return full details for a single tenant, including its platform users."""
    tenant = db.query(Tenant).filter(
        Tenant.id == tenant_id, Tenant.is_deleted == False  # noqa: E712
    ).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    # Fetch users belonging to this tenant
    db_users = db.query(User).filter(User.tenant_id == tenant_id).all()
    users = [
        {
            "id": u.id,
            "email": u.email,
            "name": u.full_name,
            "role": u.user_type,
            "department": u.department,
            "status": u.status,
            "last_login": u.last_login.isoformat() if u.last_login else None,
        }
        for u in db_users
    ]

    return _tenant_to_api(tenant, users=users)


@router.post("/tenants")
async def create_tenant(
    request: CreateTenantRequest,
    db: Session = Depends(get_db),
    _admin: Dict = Depends(require_admin_session),
):
    """
    Onboard a new tenant organisation.

    Creates the Tenant record and a platform User record for the admin.
    Returns the generated credentials so they can be communicated to the customer.
    """
    slug = _slugify(request.company_name)

    # Ensure slug uniqueness
    existing_slug = db.query(Tenant).filter(Tenant.slug == slug).first()
    if existing_slug:
        slug = f"{slug}-{secrets.token_hex(2)}"

    tenant_id = f"tenant_{slug}_{secrets.token_hex(4)}"
    admin_password = request.admin_password or secrets.token_urlsafe(12)

    modules = request.modules if request.modules else TIER_DEFAULT_MODULES.get(request.tier, ["access_management"])
    max_users = TIER_MAX_USERS.get(request.tier, 25)

    is_trial = request.trial_days > 0
    trial_ends = datetime.utcnow() + timedelta(days=request.trial_days) if is_trial else None

    tenant = Tenant(
        id=tenant_id,
        name=request.company_name,
        slug=slug,
        admin_email=request.admin_email,
        admin_name=request.admin_name,
        tier=request.tier,
        status="trial" if is_trial else "active",
        trial_ends=trial_ends,
        max_users=max_users,
        modules_enabled=modules,
        settings={},
    )
    db.add(tenant)

    # Create the tenant admin as a platform User
    admin_user = User(
        tenant_id=tenant_id,
        user_id=f"admin_{secrets.token_hex(4)}",
        username=request.admin_email.split("@")[0],
        email=request.admin_email,
        full_name=request.admin_name,
        department="Administration",
        user_type="dialog",
        status="active",
        password_hash=hash_password(admin_password),
        is_platform_user=True,
    )
    db.add(admin_user)

    try:
        db.commit()
        db.refresh(tenant)
    except Exception as exc:
        db.rollback()
        logger.error("Failed to create tenant '%s': %s", request.company_name, exc)
        raise HTTPException(status_code=500, detail="Failed to create tenant. See server logs.")

    return {
        "success": True,
        "tenant": _tenant_to_api(tenant),
        "admin_credentials": {
            "email": request.admin_email,
            "password": admin_password,
            "login_url": "https://governexplus.com/login",
        },
        "message": f"Tenant '{request.company_name}' created successfully",
    }


@router.put("/tenants/{tenant_id}")
async def update_tenant(
    tenant_id: str,
    request: UpdateTenantRequest,
    db: Session = Depends(get_db),
    _admin: Dict = Depends(require_admin_session),
):
    """Update mutable fields on an existing tenant."""
    tenant = db.query(Tenant).filter(
        Tenant.id == tenant_id, Tenant.is_deleted == False  # noqa: E712
    ).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    if request.name is not None:
        tenant.name = request.name

    if request.tier is not None:
        tenant.tier = request.tier
        # Adjust max_users to tier default unless caller also supplied max_users
        if request.max_users is None:
            tenant.max_users = TIER_MAX_USERS.get(request.tier, tenant.max_users)

    if request.status is not None:
        tenant.status = request.status

    if request.modules is not None:
        tenant.modules_enabled = request.modules

    if request.max_users is not None:
        tenant.max_users = request.max_users

    tenant.updated_at = datetime.utcnow()

    try:
        db.commit()
        db.refresh(tenant)
    except Exception as exc:
        db.rollback()
        logger.error("Failed to update tenant '%s': %s", tenant_id, exc)
        raise HTTPException(status_code=500, detail="Failed to update tenant. See server logs.")

    return {"success": True, "tenant": _tenant_to_api(tenant)}


@router.post("/tenants/{tenant_id}/suspend")
async def suspend_tenant(
    tenant_id: str,
    reason: str = "",
    db: Session = Depends(get_db),
    _admin: Dict = Depends(require_admin_session),
):
    """Suspend a tenant, blocking all access for its users."""
    tenant = db.query(Tenant).filter(
        Tenant.id == tenant_id, Tenant.is_deleted == False  # noqa: E712
    ).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    tenant.status = "suspended"
    tenant.suspended_at = datetime.utcnow()
    tenant.suspended_reason = reason or None
    tenant.updated_at = datetime.utcnow()

    db.commit()
    return {"success": True, "message": f"Tenant '{tenant.name}' suspended"}


@router.post("/tenants/{tenant_id}/activate")
async def activate_tenant(
    tenant_id: str,
    db: Session = Depends(get_db),
    _admin: Dict = Depends(require_admin_session),
):
    """Activate (or reactivate) a tenant, removing suspension flags."""
    tenant = db.query(Tenant).filter(
        Tenant.id == tenant_id, Tenant.is_deleted == False  # noqa: E712
    ).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    tenant.status = "active"
    tenant.suspended_at = None
    tenant.suspended_reason = None
    tenant.updated_at = datetime.utcnow()

    db.commit()
    return {"success": True, "message": f"Tenant '{tenant.name}' activated"}


@router.delete("/tenants/{tenant_id}")
async def delete_tenant(
    tenant_id: str,
    confirm: bool = False,
    db: Session = Depends(get_db),
    _admin: Dict = Depends(require_admin_session),
):
    """
    Soft-delete a tenant.

    Requires ?confirm=true to prevent accidental deletion.
    The record is retained in the database with is_deleted=True.
    """
    if not confirm:
        raise HTTPException(
            status_code=400, detail="Confirmation required. Add ?confirm=true to the request."
        )

    tenant = db.query(Tenant).filter(
        Tenant.id == tenant_id, Tenant.is_deleted == False  # noqa: E712
    ).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    tenant.is_deleted = True
    tenant.updated_at = datetime.utcnow()

    db.commit()
    return {"success": True, "message": f"Tenant '{tenant.name}' deleted"}


# ---------------------------------------------------------------------------
# Tenant user management
# ---------------------------------------------------------------------------

@router.get("/tenants/{tenant_id}/users")
async def list_tenant_users(
    tenant_id: str,
    db: Session = Depends(get_db),
    _admin: Dict = Depends(require_admin_session),
):
    """List all platform users belonging to a tenant."""
    tenant = db.query(Tenant).filter(
        Tenant.id == tenant_id, Tenant.is_deleted == False  # noqa: E712
    ).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    db_users = db.query(User).filter(User.tenant_id == tenant_id).all()
    users = [
        {
            "id": u.id,
            "email": u.email,
            "name": u.full_name,
            "role": u.user_type,
            "department": u.department,
            "status": u.status,
            "last_login": u.last_login.isoformat() if u.last_login else None,
        }
        for u in db_users
    ]
    return {"users": users, "total": len(users)}


@router.post("/tenants/{tenant_id}/users")
async def create_tenant_user(
    tenant_id: str,
    request: TenantUserRequest,
    db: Session = Depends(get_db),
    _admin: Dict = Depends(require_admin_session),
):
    """Create a new platform user inside the specified tenant."""
    tenant = db.query(Tenant).filter(
        Tenant.id == tenant_id, Tenant.is_deleted == False  # noqa: E712
    ).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    # Enforce per-tenant user cap
    current_count = db.query(User).filter(User.tenant_id == tenant_id).count()
    if current_count >= tenant.max_users:
        raise HTTPException(
            status_code=400,
            detail=f"User limit ({tenant.max_users}) reached for tenant '{tenant.name}'",
        )

    password = request.password or secrets.token_urlsafe(12)

    user = User(
        tenant_id=tenant_id,
        user_id=f"user_{secrets.token_hex(4)}",
        username=request.email.split("@")[0],
        email=request.email,
        full_name=request.name,
        department=request.department,
        user_type=request.role,
        status="active",
        password_hash=hash_password(password),
        is_platform_user=True,
    )
    db.add(user)

    try:
        db.commit()
        db.refresh(user)
    except Exception as exc:
        db.rollback()
        logger.error("Failed to create user for tenant '%s': %s", tenant_id, exc)
        raise HTTPException(status_code=500, detail="Failed to create user. See server logs.")

    return {
        "success": True,
        "user": {
            "id": user.id,
            "email": user.email,
            "name": user.full_name,
            "role": user.user_type,
            "department": user.department,
            "status": user.status,
        },
        "credentials": {
            "email": request.email,
            "password": password,
        },
    }


@router.delete("/tenants/{tenant_id}/users/{user_id}")
async def delete_tenant_user(
    tenant_id: str,
    user_id: int,
    db: Session = Depends(get_db),
    _admin: Dict = Depends(require_admin_session),
):
    """Remove a user from a tenant by their integer primary-key ID."""
    tenant = db.query(Tenant).filter(
        Tenant.id == tenant_id, Tenant.is_deleted == False  # noqa: E712
    ).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    user = db.query(User).filter(
        User.id == user_id, User.tenant_id == tenant_id
    ).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    db.delete(user)
    db.commit()

    return {"success": True, "message": "User deleted"}


# ---------------------------------------------------------------------------
# Reference data: available tiers and modules
# ---------------------------------------------------------------------------

@router.get("/tiers")
async def list_available_tiers(
    _admin: Dict = Depends(require_admin_session),
):
    """Return the catalogue of available subscription tiers."""
    return {
        "tiers": [
            {
                "id": "starter",
                "name": "Starter",
                "price_monthly": 99,
                "price_annual": 990,
                "max_users": TIER_MAX_USERS["starter"],
                "max_systems": 2,
                "modules": TIER_DEFAULT_MODULES["starter"],
                "features": ["Basic SoD Analysis", "User Access Reviews", "Email Support"],
            },
            {
                "id": "professional",
                "name": "Professional",
                "price_monthly": 499,
                "price_annual": 4990,
                "max_users": TIER_MAX_USERS["professional"],
                "max_systems": 5,
                "modules": TIER_DEFAULT_MODULES["professional"],
                "features": [
                    "Advanced SoD Rules",
                    "Compliance Frameworks",
                    "Risk Scoring",
                    "Priority Support",
                ],
            },
            {
                "id": "enterprise",
                "name": "Enterprise",
                "price_monthly": 2500,
                "price_annual": 25000,
                "max_users": TIER_MAX_USERS["enterprise"],
                "max_systems": 20,
                "modules": TIER_DEFAULT_MODULES["enterprise"],
                "features": [
                    "AI Assistant",
                    "ML Role Mining",
                    "Custom Integrations",
                    "Dedicated Support",
                    "SLA",
                ],
            },
        ]
    }


@router.get("/modules")
async def list_available_modules(
    _admin: Dict = Depends(require_admin_session),
):
    """Return the catalogue of available platform modules."""
    return {
        "modules": [
            {
                "id": "access_management",
                "name": "Access Management",
                "description": "User provisioning, role management, access requests",
            },
            {
                "id": "compliance",
                "name": "Compliance",
                "description": "Compliance frameworks, assessments, certifications",
            },
            {
                "id": "risk_analytics",
                "name": "Risk Analytics",
                "description": "Risk scoring, SoD analysis, violation detection",
            },
            {
                "id": "ai_assistant",
                "name": "AI Assistant",
                "description": "Natural language queries, intelligent recommendations",
            },
            {
                "id": "advanced_ml",
                "name": "Advanced ML",
                "description": "Role mining, anomaly detection, predictive analytics",
            },
            {
                "id": "firefighter",
                "name": "Firefighter Access",
                "description": "Emergency access management",
            },
            {
                "id": "siem_integration",
                "name": "SIEM Integration",
                "description": "Security event monitoring and correlation",
            },
        ]
    }
