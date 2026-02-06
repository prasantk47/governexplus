"""
Governex+ Platform - Main API Application

A comprehensive Python-based Governance, Risk, and Compliance platform
providing SAP GRC Access Control-like functionality with modern enhancements.
Updated: Auth endpoints added
Domain: governexplus.com

Features:
- Risk Analysis & SoD Detection
- Firefighter/Emergency Access Management
- User & Role Management
- Comprehensive Audit Logging
- REST API Interface
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from contextlib import asynccontextmanager
import logging
import time

from api.routers import (
    risk_analysis, users, firefighter, audit, access_requests,
    certification, dashboard, policy, jml, firefighter_monitoring,
    ml, role_engineering, mitigation, cross_system, compliance,
    reporting, integrations, user_profiles,
    # New SAP GRC-equivalent modules
    setup, notifications, workflows, sod_rules,
    # AI Intelligence module
    ai,
    # Multi-tenant SaaS
    tenants,
    # Mobile API
    mobile,
    # Provisioning Engine
    provisioning,
    # SAP Security Controls
    security_controls,
    # XAMS-inspired modules
    siem,  # SIEM Connector
    pts,   # Productive Test Simulation
    # Super Admin Portal
    admin,
    # Approvals inbox
    approvals,
    # Simple reports for demo
    reports,
    # JWT Authentication
    auth,
)
from api.middleware import TenantMiddleware
from db.database import init_db, db_manager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup/shutdown events"""
    # Startup
    logger.info("Starting Governex+ Platform...")
    init_db()
    logger.info("Database initialized")
    yield
    # Shutdown
    logger.info("Shutting down Governex+ Platform...")


# Create FastAPI application
app = FastAPI(
    title="Governex+ Platform",
    description="""
    A comprehensive Governance, Risk, and Compliance platform built in Python.

    **Domain:** governexplus.com

    ## Features

    * **Risk Analysis** - SoD conflict detection, sensitive access identification
    * **Firefighter/EAM** - Emergency access management with full audit trail
    * **User Management** - User and role queries from connected SAP systems
    * **Access Requests** - Role request portal with risk preview and workflow
    * **Certification** - Access review campaigns and periodic certification
    * **Audit Logging** - Complete audit trail for compliance
    * **Security Controls** - SAP security configuration monitoring

    ## API Modules

    * `/risk` - Risk analysis and rule management
    * `/users` - User and role queries
    * `/firefighter` - Emergency access management
    * `/access-requests` - Access request submission and approval
    * `/certification` - Access certification campaigns
    * `/audit` - Audit logs and compliance reports
    * `/security-controls` - SAP security controls management

    Built as a modern alternative/complement to SAP GRC Access Control.
    """,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Multi-tenant middleware
app.add_middleware(TenantMiddleware)


# Request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


# Helper to get CORS headers
def get_cors_headers(request: Request) -> dict:
    origin = request.headers.get("origin", "*")
    return {
        "Access-Control-Allow-Origin": origin,
        "Access-Control-Allow-Credentials": "true",
        "Access-Control-Allow-Methods": "*",
        "Access-Control-Allow-Headers": "*",
    }


# HTTP Exception handler with CORS headers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail},
        headers=get_cors_headers(request)
    )


# Validation error handler with CORS headers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={"error": "Validation error", "detail": exc.errors()},
        headers=get_cors_headers(request)
    )


# General exception handler with CORS headers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc) if app.debug else "An unexpected error occurred"
        },
        headers=get_cors_headers(request)
    )


# Include routers
app.include_router(
    risk_analysis.router,
    prefix="/risk",
    tags=["Risk Analysis"]
)

app.include_router(
    users.router,
    prefix="/users",
    tags=["Users"]
)

app.include_router(
    firefighter.router,
    prefix="/firefighter",
    tags=["Firefighter"]
)

app.include_router(
    audit.router,
    prefix="/audit",
    tags=["Audit"]
)

app.include_router(
    access_requests.router,
    prefix="/access-requests",
    tags=["Access Requests"]
)

app.include_router(
    certification.router,
    prefix="/certification",
    tags=["Certification"]
)

app.include_router(
    dashboard.router,
    prefix="/dashboard",
    tags=["Dashboard"]
)

app.include_router(
    policy.router,
    prefix="/policy",
    tags=["Policy"]
)

app.include_router(
    jml.router,
    prefix="/jml",
    tags=["JML"]
)

app.include_router(
    firefighter_monitoring.router,
    prefix="/firefighter/monitoring",
    tags=["Firefighter Monitoring"]
)

app.include_router(
    ml.router,
    prefix="/ml",
    tags=["Machine Learning"]
)

app.include_router(
    role_engineering.router,
    prefix="/role-engineering",
    tags=["Role Engineering"]
)

app.include_router(
    mitigation.router,
    prefix="/mitigation",
    tags=["Mitigation Controls"]
)

app.include_router(
    cross_system.router,
    prefix="/cross-system",
    tags=["Cross-System"]
)

app.include_router(
    compliance.router,
    prefix="/compliance",
    tags=["Compliance"]
)

app.include_router(
    reporting.router,
    prefix="/reporting",
    tags=["Reporting"]
)

app.include_router(
    integrations.router,
    prefix="/integrations",
    tags=["Integrations"]
)

app.include_router(
    user_profiles.router,
    prefix="/user-profiles",
    tags=["User Profiles"]
)

app.include_router(
    setup.router,
    prefix="/setup",
    tags=["Setup Wizard"]
)

app.include_router(
    notifications.router,
    prefix="/notifications",
    tags=["Notifications"]
)

app.include_router(
    workflows.router,
    prefix="/workflows",
    tags=["Workflows"]
)

app.include_router(
    sod_rules.router,
    prefix="/sod-rules",
    tags=["SoD Rules"]
)

app.include_router(
    ai.router,
    prefix="/ai",
    tags=["AI Intelligence"]
)

app.include_router(
    tenants.router,
    prefix="/tenants",
    tags=["Tenants"]
)

app.include_router(
    mobile.router,
    prefix="/mobile",
    tags=["Mobile API"]
)

app.include_router(
    provisioning.router,
    prefix="/provisioning",
    tags=["Provisioning Engine"]
)

app.include_router(
    security_controls.router,
    prefix="/security-controls",
    tags=["SAP Security Controls"]
)

# XAMS-inspired modules
app.include_router(
    siem.router,
    prefix="/siem",
    tags=["SIEM Connector"]
)

app.include_router(
    pts.router,
    prefix="/pts",
    tags=["Productive Test Simulation"]
)

app.include_router(
    admin.router,
    prefix="/admin",
    tags=["Super Admin Portal"]
)

app.include_router(
    approvals.router,
    prefix="/approvals",
    tags=["Approvals"]
)

app.include_router(
    reports.router,
    prefix="/reports",
    tags=["Reports"]
)

# JWT Authentication (new enterprise-grade auth)
app.include_router(
    auth.router,
    prefix="/auth",
    tags=["Authentication"]
)


# =============================================================================
# Root Endpoints
# =============================================================================

@app.get("/", tags=["System"])
async def root():
    """API root - returns basic information about the platform"""
    return {
        "name": "Governex+",
        "version": "1.0.0",
        "description": "Intelligent Governance — Secure. Compliant. Intelligent.",
        "modules": {
            "risk_analysis": "/risk",
            "users": "/users",
            "firefighter": "/firefighter",
            "firefighter_monitoring": "/firefighter/monitoring",
            "access_requests": "/access-requests",
            "certification": "/certification",
            "dashboard": "/dashboard",
            "policy": "/policy",
            "jml": "/jml",
            "ml": "/ml",
            "role_engineering": "/role-engineering",
            "mitigation": "/mitigation",
            "cross_system": "/cross-system",
            "compliance": "/compliance",
            "reporting": "/reporting",
            "integrations": "/integrations",
            "user_profiles": "/user-profiles",
            "audit": "/audit",
            "setup": "/setup",
            "notifications": "/notifications",
            "workflows": "/workflows",
            "sod_rules": "/sod-rules",
            "ai": "/ai",
            "security_controls": "/security-controls",
            "siem": "/siem",
            "pts": "/pts",
            "admin": "/admin"
        },
        "documentation": {
            "swagger": "/docs",
            "redoc": "/redoc"
        }
    }


@app.get("/health", tags=["System"])
async def health_check():
    """Health check endpoint"""
    db_health = db_manager.health_check()

    return {
        "status": "healthy" if db_health["status"] == "healthy" else "degraded",
        "components": {
            "api": "healthy",
            "database": db_health
        },
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }


# =============================================================================
# Authentication Endpoints
# =============================================================================

from pydantic import BaseModel

class LoginRequest(BaseModel):
    username: str
    password: str

# Demo users for authentication
DEMO_USERS = {
    "admin": {"name": "Admin User", "department": "IT", "email": "admin@governexplus.com", "role": "admin"},
    "security_admin": {"name": "Security Admin", "department": "IT Security", "email": "security@governexplus.com", "role": "security_admin"},
    "manager": {"name": "Manager User", "department": "Operations", "email": "manager@governexplus.com", "role": "manager"},
    "user": {"name": "End User", "department": "Finance", "email": "user@governexplus.com", "role": "end_user"},
    "JSMITH": {"name": "John Smith", "department": "Finance", "email": "jsmith@governexplus.com", "role": "end_user"},
    "MBROWN": {"name": "Mary Brown", "department": "Procurement", "email": "mbrown@governexplus.com", "role": "manager"},
    # Tenant admins (created during onboarding)
    "demo@demo.com": {"name": "Demo Admin", "department": "Administration", "email": "demo@demo.com", "role": "admin"},
}

@app.post("/auth/login", tags=["Auth"])
async def login(request: LoginRequest):
    """
    Login endpoint for authentication.

    Demo credentials (any password works):
    - admin / admin - Full admin access
    - security_admin / admin - Security admin access
    - manager / admin - Manager/approver access
    - user / admin - End user access
    """
    username = request.username

    # Accept any user from DEMO_USERS or any username containing role keywords
    if username in DEMO_USERS:
        user_data = DEMO_USERS[username]
    elif "admin" in username.lower() and "security" not in username.lower():
        user_data = {"name": f"Admin ({username})", "department": "IT", "email": f"{username}@governexplus.com", "role": "admin"}
    elif "security" in username.lower():
        user_data = {"name": f"Security Admin ({username})", "department": "IT Security", "email": f"{username}@governexplus.com", "role": "security_admin"}
    elif "manager" in username.lower():
        user_data = {"name": f"Manager ({username})", "department": "Operations", "email": f"{username}@governexplus.com", "role": "manager"}
    else:
        user_data = {"name": f"User ({username})", "department": "General", "email": f"{username}@governexplus.com", "role": "end_user"}

    return {
        "access_token": f"governex_token_{username}_{int(time.time())}",
        "refresh_token": f"governex_refresh_{username}_{int(time.time())}",
        "token_type": "bearer",
        "user": {
            "user_id": username,
            "id": username,
            "display_name": user_data["name"],
            **user_data
        }
    }

@app.post("/auth/logout", tags=["Auth"])
async def logout():
    """Logout endpoint - invalidates tokens"""
    return {"message": "Logged out successfully"}

@app.get("/auth/profile", tags=["Auth"])
async def get_profile():
    """Get current user profile"""
    return {
        "user_id": "admin",
        "name": "Admin User",
        "department": "IT",
        "email": "admin@governexplus.com",
        "roles": ["ADMIN", "GRC_MANAGER"]
    }


@app.get("/info", tags=["System"])
async def system_info():
    """Get system information and statistics"""
    from core.rules import RuleEngine

    rule_engine = RuleEngine()

    return {
        "platform": "Governex+",
        "version": "1.0.0",
        "capabilities": [
            "Segregation of Duties (SoD) Analysis",
            "Sensitive Access Detection",
            "Firefighter/Emergency Access Management",
            "Access Request Simulation",
            "Batch Risk Analysis",
            "Comprehensive Audit Logging",
            "Compliance Reporting"
        ],
        "statistics": {
            "rules_loaded": len(rule_engine.rules),
            "rule_categories": list(rule_engine.rule_index_by_category.keys())
        },
        "supported_systems": [
            "SAP ECC",
            "SAP S/4HANA",
            "Mock/Demo System"
        ]
    }


# =============================================================================
# Demo Endpoints
# =============================================================================

@app.get("/demo/users", tags=["Demo"])
async def get_demo_users():
    """Get list of demo users for testing"""
    return {
        "demo_users": [
            {
                "user_id": "JSMITH",
                "name": "John Smith",
                "department": "Finance",
                "risk_profile": "HIGH - Has P2P SoD conflict"
            },
            {
                "user_id": "MBROWN",
                "name": "Mary Brown",
                "department": "Procurement",
                "risk_profile": "MEDIUM - PO and GR access"
            },
            {
                "user_id": "TDAVIS",
                "name": "Tom Davis",
                "department": "IT",
                "risk_profile": "CRITICAL - SAP_ALL profile"
            },
            {
                "user_id": "AWILSON",
                "name": "Alice Wilson",
                "department": "HR",
                "risk_profile": "CRITICAL - HR data and payroll access"
            }
        ],
        "firefighter_ids": [
            {
                "id": "FF_EMERGENCY_01",
                "description": "General emergency access",
                "status": "available"
            }
        ]
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
