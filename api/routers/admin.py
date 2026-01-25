"""
Super Admin API Router
Platform administration endpoints for super admin users

Provides:
- Super admin authentication
- Tenant management (create, view, suspend, delete)
- User management across tenants
- Platform statistics
- System configuration
"""

from fastapi import APIRouter, HTTPException, Query, Header, Depends
from pydantic import BaseModel, EmailStr
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import json
import hashlib
import secrets
from pathlib import Path

router = APIRouter(prefix="/admin", tags=["Super Admin"])


# ==================== Models ====================

class AdminLoginRequest(BaseModel):
    email: str
    password: str


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


# ==================== Helper Functions ====================

def load_super_admin() -> Optional[Dict]:
    """Load super admin from config"""
    config_file = Path(__file__).parent.parent.parent / "config" / "super_admin.json"
    if config_file.exists():
        with open(config_file, 'r') as f:
            return json.load(f)
    return None


def verify_password(password: str, hashed: str) -> bool:
    """Verify password against hash"""
    try:
        salt, hash_value = hashed.split(":")
        return hashlib.sha256(f"{salt}{password}".encode()).hexdigest() == hash_value
    except:
        return False


def generate_token() -> str:
    """Generate session token"""
    return f"admin_{secrets.token_hex(32)}"


def hash_password(password: str) -> str:
    """Hash password with salt"""
    salt = secrets.token_hex(16)
    hashed = hashlib.sha256(f"{salt}{password}".encode()).hexdigest()
    return f"{salt}:{hashed}"


# In-memory storage for demo (replace with database in production)
admin_sessions: Dict[str, Dict] = {}
tenants_db: Dict[str, Dict] = {}
tenant_users_db: Dict[str, List[Dict]] = {}

# Initialize with demo tenants
_init_tenants = {
    "tenant_acme": {
        "id": "tenant_acme",
        "name": "Acme Corporation",
        "slug": "acme",
        "admin_email": "admin@acme.com",
        "admin_name": "John Smith",
        "tier": "enterprise",
        "status": "active",
        "created_at": (datetime.now() - timedelta(days=90)).isoformat(),
        "users_count": 156,
        "max_users": 500,
        "systems_connected": 4,
        "modules": ["access_management", "risk_analytics", "compliance", "ai_assistant"],
        "last_activity": datetime.now().isoformat(),
        "billing": {
            "plan": "Enterprise Annual",
            "amount": 2500,
            "currency": "USD",
            "next_billing": (datetime.now() + timedelta(days=30)).isoformat()
        }
    },
    "tenant_globex": {
        "id": "tenant_globex",
        "name": "Globex Industries",
        "slug": "globex",
        "admin_email": "admin@globex.com",
        "admin_name": "Jane Doe",
        "tier": "professional",
        "status": "active",
        "created_at": (datetime.now() - timedelta(days=45)).isoformat(),
        "users_count": 42,
        "max_users": 100,
        "systems_connected": 2,
        "modules": ["access_management", "compliance"],
        "last_activity": (datetime.now() - timedelta(hours=2)).isoformat(),
        "billing": {
            "plan": "Professional Monthly",
            "amount": 499,
            "currency": "USD",
            "next_billing": (datetime.now() + timedelta(days=15)).isoformat()
        }
    },
    "tenant_initech": {
        "id": "tenant_initech",
        "name": "Initech Solutions",
        "slug": "initech",
        "admin_email": "admin@initech.com",
        "admin_name": "Peter Gibbons",
        "tier": "starter",
        "status": "trial",
        "created_at": (datetime.now() - timedelta(days=7)).isoformat(),
        "trial_ends": (datetime.now() + timedelta(days=7)).isoformat(),
        "users_count": 8,
        "max_users": 25,
        "systems_connected": 1,
        "modules": ["access_management"],
        "last_activity": (datetime.now() - timedelta(hours=12)).isoformat(),
        "billing": None
    },
    "tenant_umbrella": {
        "id": "tenant_umbrella",
        "name": "Umbrella Corp",
        "slug": "umbrella",
        "admin_email": "admin@umbrella.com",
        "admin_name": "Albert Wesker",
        "tier": "professional",
        "status": "suspended",
        "suspended_reason": "Payment overdue",
        "created_at": (datetime.now() - timedelta(days=120)).isoformat(),
        "users_count": 28,
        "max_users": 100,
        "systems_connected": 2,
        "modules": ["access_management", "compliance"],
        "last_activity": (datetime.now() - timedelta(days=5)).isoformat(),
        "billing": {
            "plan": "Professional Monthly",
            "amount": 499,
            "currency": "USD",
            "overdue_amount": 998,
            "next_billing": None
        }
    }
}
tenants_db.update(_init_tenants)

# Initialize demo users per tenant
tenant_users_db["tenant_acme"] = [
    {"id": "user_1", "email": "admin@acme.com", "name": "John Smith", "role": "admin", "department": "IT", "status": "active", "last_login": datetime.now().isoformat()},
    {"id": "user_2", "email": "jane@acme.com", "name": "Jane Wilson", "role": "user", "department": "Finance", "status": "active", "last_login": (datetime.now() - timedelta(hours=2)).isoformat()},
    {"id": "user_3", "email": "bob@acme.com", "name": "Bob Johnson", "role": "user", "department": "HR", "status": "active", "last_login": (datetime.now() - timedelta(days=1)).isoformat()},
]


# ==================== Authentication ====================

@router.post("/login", response_model=AdminLoginResponse)
async def admin_login(request: AdminLoginRequest):
    """
    Authenticate super admin user

    Returns session token for subsequent API calls.
    """
    admin = load_super_admin()

    # Allow demo login if no super admin configured
    if not admin:
        if request.email == "admin@governex.local" and request.password == "admin123":
            token = generate_token()
            admin_sessions[token] = {
                "email": request.email,
                "name": "Demo Admin",
                "logged_in_at": datetime.now().isoformat()
            }
            return AdminLoginResponse(
                success=True,
                token=token,
                admin={
                    "email": request.email,
                    "name": "Demo Admin",
                    "role": "super_admin"
                },
                message="Logged in successfully (demo mode)"
            )
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Verify credentials
    if request.email != admin.get("email"):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not verify_password(request.password, admin.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Create session
    token = generate_token()
    admin_sessions[token] = {
        "email": admin["email"],
        "name": admin["name"],
        "logged_in_at": datetime.now().isoformat()
    }

    return AdminLoginResponse(
        success=True,
        token=token,
        admin={
            "email": admin["email"],
            "name": admin["name"],
            "role": "super_admin",
            "permissions": admin.get("permissions", [])
        },
        message="Logged in successfully"
    )


@router.post("/logout")
async def admin_logout(authorization: str = Header(None)):
    """Logout and invalidate session"""
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1]
        if token in admin_sessions:
            del admin_sessions[token]

    return {"success": True, "message": "Logged out"}


@router.get("/verify")
async def verify_session(authorization: str = Header(None)):
    """Verify if current session is valid"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")

    token = authorization.split(" ")[1]
    session = admin_sessions.get(token)

    if not session:
        raise HTTPException(status_code=401, detail="Session expired")

    return {
        "valid": True,
        "admin": {
            "email": session["email"],
            "name": session["name"]
        }
    }


# ==================== Dashboard Statistics ====================

@router.get("/dashboard/stats")
async def get_dashboard_stats():
    """Get platform-wide statistics for admin dashboard"""
    active_tenants = sum(1 for t in tenants_db.values() if t["status"] == "active")
    trial_tenants = sum(1 for t in tenants_db.values() if t["status"] == "trial")
    total_users = sum(t.get("users_count", 0) for t in tenants_db.values())

    return {
        "tenants": {
            "total": len(tenants_db),
            "active": active_tenants,
            "trial": trial_tenants,
            "suspended": sum(1 for t in tenants_db.values() if t["status"] == "suspended")
        },
        "users": {
            "total": total_users,
            "active_today": int(total_users * 0.65),
            "new_this_month": 47
        },
        "revenue": {
            "mrr": 15750,
            "arr": 189000,
            "growth": 12.5
        },
        "systems": {
            "connected": sum(t.get("systems_connected", 0) for t in tenants_db.values()),
            "sync_healthy": 95
        },
        "api": {
            "calls_today": 125000,
            "avg_latency_ms": 45,
            "error_rate": 0.02
        },
        "recent_activity": [
            {"type": "tenant_created", "tenant": "Initech Solutions", "time": "7 days ago"},
            {"type": "upgrade", "tenant": "Acme Corporation", "from": "professional", "to": "enterprise", "time": "2 weeks ago"},
            {"type": "payment_failed", "tenant": "Umbrella Corp", "time": "5 days ago"},
        ]
    }


# ==================== Tenant Management ====================

@router.get("/tenants")
async def list_all_tenants(
    status: Optional[str] = None,
    tier: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = Query(50, le=200)
):
    """List all tenants with optional filters"""
    tenants = list(tenants_db.values())

    if status:
        tenants = [t for t in tenants if t["status"] == status]

    if tier:
        tenants = [t for t in tenants if t["tier"] == tier]

    if search:
        search_lower = search.lower()
        tenants = [t for t in tenants if
                   search_lower in t["name"].lower() or
                   search_lower in t.get("admin_email", "").lower()]

    return {
        "tenants": tenants[:limit],
        "total": len(tenants),
        "filters": {
            "status": status,
            "tier": tier,
            "search": search
        }
    }


@router.get("/tenants/{tenant_id}")
async def get_tenant_details(tenant_id: str):
    """Get detailed information about a tenant"""
    tenant = tenants_db.get(tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    # Add user list
    users = tenant_users_db.get(tenant_id, [])

    return {
        **tenant,
        "users": users,
        "user_stats": {
            "total": len(users),
            "admins": sum(1 for u in users if u["role"] == "admin"),
            "active": sum(1 for u in users if u["status"] == "active")
        }
    }


@router.post("/tenants")
async def create_tenant(request: CreateTenantRequest):
    """
    Create a new tenant (onboard new organization)

    This creates:
    - Tenant record
    - Admin user for the tenant
    - Default configuration
    """
    import secrets
    import re

    # Generate tenant ID and slug
    slug = re.sub(r'[^a-z0-9]+', '-', request.company_name.lower()).strip('-')
    tenant_id = f"tenant_{slug}_{secrets.token_hex(4)}"

    # Check if slug exists
    if any(t["slug"] == slug for t in tenants_db.values()):
        slug = f"{slug}-{secrets.token_hex(2)}"

    # Generate password if not provided
    admin_password = request.admin_password or secrets.token_urlsafe(12)

    # Default modules based on tier
    tier_modules = {
        "starter": ["access_management"],
        "professional": ["access_management", "compliance", "risk_analytics"],
        "enterprise": ["access_management", "compliance", "risk_analytics", "ai_assistant", "advanced_ml"]
    }

    modules = request.modules if request.modules else tier_modules.get(request.tier, ["access_management"])

    # Create tenant
    tenant = {
        "id": tenant_id,
        "name": request.company_name,
        "slug": slug,
        "admin_email": request.admin_email,
        "admin_name": request.admin_name,
        "tier": request.tier,
        "status": "trial" if request.trial_days > 0 else "active",
        "created_at": datetime.now().isoformat(),
        "trial_ends": (datetime.now() + timedelta(days=request.trial_days)).isoformat() if request.trial_days > 0 else None,
        "users_count": 1,
        "max_users": {"starter": 25, "professional": 100, "enterprise": 500}.get(request.tier, 25),
        "systems_connected": 0,
        "modules": modules,
        "last_activity": datetime.now().isoformat(),
        "billing": None
    }

    tenants_db[tenant_id] = tenant

    # Create admin user
    admin_user = {
        "id": f"user_{secrets.token_hex(4)}",
        "email": request.admin_email,
        "name": request.admin_name,
        "role": "admin",
        "department": "Administration",
        "status": "active",
        "password_hash": hash_password(admin_password),
        "created_at": datetime.now().isoformat(),
        "last_login": None
    }

    tenant_users_db[tenant_id] = [admin_user]

    return {
        "success": True,
        "tenant": tenant,
        "admin_credentials": {
            "email": request.admin_email,
            "password": admin_password,
            "login_url": f"https://{slug}.governex.io/login"
        },
        "message": f"Tenant '{request.company_name}' created successfully"
    }


@router.put("/tenants/{tenant_id}")
async def update_tenant(tenant_id: str, request: UpdateTenantRequest):
    """Update tenant settings"""
    tenant = tenants_db.get(tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    if request.name:
        tenant["name"] = request.name

    if request.tier:
        tenant["tier"] = request.tier
        # Update max users based on tier
        tenant["max_users"] = {"starter": 25, "professional": 100, "enterprise": 500}.get(request.tier, tenant["max_users"])

    if request.status:
        tenant["status"] = request.status

    if request.modules:
        tenant["modules"] = request.modules

    if request.max_users:
        tenant["max_users"] = request.max_users

    tenant["updated_at"] = datetime.now().isoformat()

    return {"success": True, "tenant": tenant}


@router.post("/tenants/{tenant_id}/suspend")
async def suspend_tenant(tenant_id: str, reason: str = ""):
    """Suspend a tenant"""
    tenant = tenants_db.get(tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    tenant["status"] = "suspended"
    tenant["suspended_at"] = datetime.now().isoformat()
    tenant["suspended_reason"] = reason

    return {"success": True, "message": f"Tenant {tenant['name']} suspended"}


@router.post("/tenants/{tenant_id}/activate")
async def activate_tenant(tenant_id: str):
    """Activate or reactivate a tenant"""
    tenant = tenants_db.get(tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    tenant["status"] = "active"
    tenant.pop("suspended_at", None)
    tenant.pop("suspended_reason", None)

    return {"success": True, "message": f"Tenant {tenant['name']} activated"}


@router.delete("/tenants/{tenant_id}")
async def delete_tenant(tenant_id: str, confirm: bool = False):
    """Delete a tenant (requires confirmation)"""
    if not confirm:
        raise HTTPException(status_code=400, detail="Confirmation required. Set confirm=true")

    tenant = tenants_db.get(tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    del tenants_db[tenant_id]
    tenant_users_db.pop(tenant_id, None)

    return {"success": True, "message": f"Tenant {tenant['name']} deleted"}


# ==================== Tenant User Management ====================

@router.get("/tenants/{tenant_id}/users")
async def list_tenant_users(tenant_id: str):
    """List all users in a tenant"""
    if tenant_id not in tenants_db:
        raise HTTPException(status_code=404, detail="Tenant not found")

    users = tenant_users_db.get(tenant_id, [])
    return {"users": users, "total": len(users)}


@router.post("/tenants/{tenant_id}/users")
async def create_tenant_user(tenant_id: str, request: TenantUserRequest):
    """Create a new user in a tenant"""
    if tenant_id not in tenants_db:
        raise HTTPException(status_code=404, detail="Tenant not found")

    tenant = tenants_db[tenant_id]

    # Check user limit
    current_users = len(tenant_users_db.get(tenant_id, []))
    if current_users >= tenant.get("max_users", 25):
        raise HTTPException(status_code=400, detail="User limit reached for this tenant")

    password = request.password or secrets.token_urlsafe(12)

    user = {
        "id": f"user_{secrets.token_hex(4)}",
        "email": request.email,
        "name": request.name,
        "role": request.role,
        "department": request.department,
        "status": "active",
        "password_hash": hash_password(password),
        "created_at": datetime.now().isoformat(),
        "last_login": None
    }

    if tenant_id not in tenant_users_db:
        tenant_users_db[tenant_id] = []

    tenant_users_db[tenant_id].append(user)
    tenant["users_count"] = len(tenant_users_db[tenant_id])

    return {
        "success": True,
        "user": {k: v for k, v in user.items() if k != "password_hash"},
        "credentials": {
            "email": request.email,
            "password": password
        }
    }


@router.delete("/tenants/{tenant_id}/users/{user_id}")
async def delete_tenant_user(tenant_id: str, user_id: str):
    """Delete a user from a tenant"""
    if tenant_id not in tenants_db:
        raise HTTPException(status_code=404, detail="Tenant not found")

    users = tenant_users_db.get(tenant_id, [])
    user = next((u for u in users if u["id"] == user_id), None)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    tenant_users_db[tenant_id] = [u for u in users if u["id"] != user_id]
    tenants_db[tenant_id]["users_count"] = len(tenant_users_db[tenant_id])

    return {"success": True, "message": "User deleted"}


# ==================== Available Tiers & Modules ====================

@router.get("/tiers")
async def list_available_tiers():
    """List available subscription tiers"""
    return {
        "tiers": [
            {
                "id": "starter",
                "name": "Starter",
                "price_monthly": 99,
                "price_annual": 990,
                "max_users": 25,
                "max_systems": 2,
                "modules": ["access_management"],
                "features": ["Basic SoD Analysis", "User Access Reviews", "Email Support"]
            },
            {
                "id": "professional",
                "name": "Professional",
                "price_monthly": 499,
                "price_annual": 4990,
                "max_users": 100,
                "max_systems": 5,
                "modules": ["access_management", "compliance", "risk_analytics"],
                "features": ["Advanced SoD Rules", "Compliance Frameworks", "Risk Scoring", "Priority Support"]
            },
            {
                "id": "enterprise",
                "name": "Enterprise",
                "price_monthly": 2500,
                "price_annual": 25000,
                "max_users": 500,
                "max_systems": 20,
                "modules": ["access_management", "compliance", "risk_analytics", "ai_assistant", "advanced_ml"],
                "features": ["AI Assistant", "ML Role Mining", "Custom Integrations", "Dedicated Support", "SLA"]
            }
        ]
    }


@router.get("/modules")
async def list_available_modules():
    """List available platform modules"""
    return {
        "modules": [
            {"id": "access_management", "name": "Access Management", "description": "User provisioning, role management, access requests"},
            {"id": "compliance", "name": "Compliance", "description": "Compliance frameworks, assessments, certifications"},
            {"id": "risk_analytics", "name": "Risk Analytics", "description": "Risk scoring, SoD analysis, violation detection"},
            {"id": "ai_assistant", "name": "AI Assistant", "description": "Natural language queries, intelligent recommendations"},
            {"id": "advanced_ml", "name": "Advanced ML", "description": "Role mining, anomaly detection, predictive analytics"},
            {"id": "firefighter", "name": "Firefighter Access", "description": "Emergency access management"},
            {"id": "siem_integration", "name": "SIEM Integration", "description": "Security event monitoring and correlation"},
        ]
    }
