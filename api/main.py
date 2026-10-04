# Load .env before any other imports read os.getenv
from dotenv import load_dotenv
load_dotenv()

"""
Governex+ Platform - Main API Application

A comprehensive Python-based Governance, Risk, and Compliance platform
providing GovernexPlus Access Control functionality with modern enhancements.
Updated: Auth endpoints added
Domain: governexplus.com

Features:
- Risk Analysis & SoD Detection
- Firefighter/Emergency Access Management
- User & Role Management
- Comprehensive Audit Logging
- REST API Interface
"""

import os
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from contextlib import asynccontextmanager
import time

from core.logging import setup_logging, get_logger
from services.auth_service import AuthService, JWT_SECRET
from db.database import get_db
from api.dependencies import get_current_user

# Initialize structured logging BEFORE anything else logs
setup_logging()

from api.routers import (
    risk_analysis, users, firefighter, audit, access_requests,
    certification, dashboard, firefighter_monitoring,
    role_engineering, mitigation, cross_system,
    reporting, integrations, user_profiles,
    # New GovernexPlus modules
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
    # Super Admin Portal
    admin,
    # Approvals inbox
    approvals,
    # Simple reports for demo
    reports,
    # JWT Authentication
    auth,
    # Approver Management
    approver_management,
    # Risk Intelligence Engine
    ara,
    # GovernEx+ Differentiators
    governex_plus,
    # ARM Shopping Cart
    arm,
    # Role Intelligence Engine
    role_intelligence,
    # Access Troubleshooter
    troubleshooter,
    # ECC to S/4HANA Migration Analyzer
    migration,
    # Role Drift Detection
    drift,
    # Audit Evidence Center
    audit_evidence,
    # Access Timeline
    timeline,
    # Fiori Security Analyzer
    fiori,
    # Upgrade Impact Analyzer
    upgrade,
    # Identity Correlation
    identity_correlation,
    # Organizational Rules Engine
    org_rules,
    # Mass Administration
    mass_admin,
    # Repository Sync
    repo_sync,
    # Role Transport Management
    transport,
    # Custom Transaction Analysis
    custom_tcode,
    # Access Reports (transaction usage, user complete access, auth object lookup)
    access_reports,
    # GRC Suite — Enterprise Risk Engine, Control Intelligence, Audit Command Center
    risk_mgmt,
    process_ctrl,
    audit_mgmt,
    org_hierarchy,
    frameworks,
    grc_dashboard,
)
from api.routers import sso as sso_router
# Role Redesign Copilot
from api.routers import role_redesign
# Migration Copilot — ECC → S/4HANA
from api.routers import migration_copilot
# New delivery, model-user, and monitoring modules
from api.routers import notification_delivery, model_user, mitigation_monitoring
# SMTP configuration (per-tenant email settings)
from api.routers import smtp_config as smtp_config_router
# GRC Intelligence Engine (the brain)
from api.routers import grc_intelligence
# Internationalisation
from api.routers import i18n as i18n_router
# Document Retention & Legal Hold
from api.routers import retention as retention_router
# GRC AI Assistant (XI-08)
from api.routers import ai_grc
# Audit Evidence Agent — AI-driven evidence assembly
from api.routers import evidence_agent
# GRC Digital Twin — live connected GRC state model
from api.routers import digital_twin
# Prometheus metrics endpoint
from api.routers import metrics as metrics_router
from api.middleware import TenantMiddleware, SecurityHeadersMiddleware
from api.middleware.rate_limit import setup_rate_limiting, limiter, RATE_LIMIT_AUTH
from db.database import init_db, db_manager
from db.tenant_scoping import install_tenant_scoping

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Sentry error tracking — enabled only when SENTRY_DSN env var is set
# ---------------------------------------------------------------------------
_app_env = os.getenv("APP_ENV", "development")
_sentry_dsn = os.getenv("SENTRY_DSN", "")
if _sentry_dsn:
    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
        sentry_sdk.init(
            dsn=_sentry_dsn,
            integrations=[FastApiIntegration(), SqlalchemyIntegration()],
            traces_sample_rate=float(os.getenv("SENTRY_TRACES_RATE", "0.1")),
            environment=_app_env,
        )
        logger.info("Sentry error tracking enabled")
    except ImportError:
        logger.warning("SENTRY_DSN set but sentry-sdk not installed")


def _run_alembic_migrations():
    """Run Alembic migrations on startup if configured."""
    auto_migrate = os.getenv("AUTO_MIGRATE", "false").lower() in ("1", "true", "yes")
    if not auto_migrate:
        return
    try:
        from alembic.config import Config
        from alembic import command
        alembic_cfg = Config("alembic.ini")
        command.upgrade(alembic_cfg, "head")
        logger.info("Alembic migrations applied successfully")
    except Exception as exc:
        logger.error(f"Alembic migration failed: {exc}")
        raise


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup/shutdown events"""
    # Startup
    logger.info("Starting Governex+ Platform...")
    _run_alembic_migrations()
    init_db()
    install_tenant_scoping()
    logger.info("Database initialized, tenant scoping active")

    # Seed Template Library (idempotent)
    try:
        from db.database import db_manager
        from core.library.seeder import seed_library
        s = db_manager.get_session()
        try:
            result = seed_library(s)
            logger.info("Template library seeder: %s", result)
        finally:
            s.close()
    except Exception as e:
        logger.warning("Template library seeder failed (non-fatal): %s", e)

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

    * **Risk Intelligence** - SoD conflict detection, sensitive access identification
    * **Privileged Access Governor** - Emergency access management with full audit trail
    * **User Management** - User and role queries from connected systems
    * **Access Lifecycle** - Role request portal with risk preview and workflow
    * **Certification** - Access review campaigns and periodic certification
    * **Audit Logging** - Complete audit trail for compliance
    * **Security Controls** - Security configuration monitoring

    ## API Modules

    * `/risk` - Risk intelligence and rule management
    * `/users` - User and role queries
    * `/firefighter` - Privileged access management
    * `/access-requests` - Access lifecycle submission and approval
    * `/certification` - Access certification campaigns
    * `/audit` - Audit logs and compliance reports
    * `/security-controls` - Security controls management

    Built as a modern alternative/complement to GovernexPlus Access Control.
    """,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware — restricted to configured origins
_cors_origins_raw = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000,http://localhost:4500,http://localhost:9000")
_allowed_origins = [o.strip() for o in _cors_origins_raw.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Tenant-ID", "X-Request-ID"],
)

# Session middleware — required for OIDC state (uses signed cookies, no server store)
from starlette.middleware.sessions import SessionMiddleware
app.add_middleware(SessionMiddleware, secret_key=os.getenv("SESSION_SECRET", JWT_SECRET))

# Security headers middleware — runs outermost so headers appear on all responses
app.add_middleware(SecurityHeadersMiddleware)

# Multi-tenant middleware
app.add_middleware(TenantMiddleware)

# Rate limiting
setup_rate_limiting(app)


# Request timing middleware with structured logging
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    import structlog
    start_time = time.time()

    # Bind request context for all logs during this request
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(
        request_path=request.url.path,
        request_method=request.method,
        client_ip=(request.client.host if request.client else "unknown") if hasattr(request, 'client') else "unknown",
        tenant_id=request.headers.get("X-Tenant-ID", "default"),
    )

    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)

    # Record Prometheus metrics
    from api.routers.metrics import REQUEST_COUNT, REQUEST_LATENCY
    REQUEST_COUNT.labels(
        method=request.method,
        endpoint=request.url.path,
        status=response.status_code,
    ).inc()
    REQUEST_LATENCY.labels(
        method=request.method,
        endpoint=request.url.path,
    ).observe(process_time)

    logger.info(
        "request.completed",
        status_code=response.status_code,
        duration_ms=round(process_time * 1000, 2),
    )
    return response


# Safe CORS headers for error responses — only allow configured origins
def get_cors_headers(request: Request) -> dict:
    origin = request.headers.get("origin", "")
    allowed = origin if origin in _allowed_origins else _allowed_origins[0] if _allowed_origins else ""
    return {
        "Access-Control-Allow-Origin": allowed,
        "Access-Control-Allow-Credentials": "true",
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


# General exception handler — never leak internals
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("unhandled_exception", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error"},
        headers=get_cors_headers(request)
    )


# Auth dependency list for use in router includes
_require_auth = [Depends(get_current_user)]

# Include routers — all require authentication except /auth
app.include_router(
    risk_analysis.router,
    prefix="/risk",
    tags=["Risk Intelligence Engine"],
    dependencies=_require_auth,
)

app.include_router(
    users.router, prefix="/users", tags=["Users"],
    dependencies=_require_auth,
)
app.include_router(
    firefighter.router, prefix="/privileged-access", tags=["Privileged Access Governor"],
    dependencies=_require_auth,
)
app.include_router(
    audit.router, prefix="/audit", tags=["Audit"],
    dependencies=_require_auth,
)
app.include_router(
    access_requests.router, prefix="/access-requests", tags=["Access Lifecycle Manager"],
    dependencies=_require_auth,
)
app.include_router(
    certification.router, prefix="/certification", tags=["Certification"],
    dependencies=_require_auth,
)
app.include_router(
    dashboard.router, prefix="/dashboard", tags=["Dashboard"],
    dependencies=_require_auth,
)


app.include_router(
    firefighter_monitoring.router, prefix="/privileged-access/monitoring",
    tags=["Privileged Access Governor - Monitoring"], dependencies=_require_auth,
)


app.include_router(
    role_engineering.router, prefix="/role-studio", tags=["Role Design Studio"],
    dependencies=_require_auth,
)
app.include_router(
    mitigation.router, prefix="/mitigation", tags=["Mitigation Controls"],
    dependencies=_require_auth,
)
app.include_router(
    cross_system.router, prefix="/cross-system", tags=["Cross-System"],
    dependencies=_require_auth,
)


app.include_router(
    reporting.router, prefix="/reporting", tags=["Reporting"],
    dependencies=_require_auth,
)
app.include_router(
    integrations.router, prefix="/integrations", tags=["Integrations"],
    dependencies=_require_auth,
)
app.include_router(
    user_profiles.router, prefix="/user-profiles", tags=["User Profiles"],
    dependencies=_require_auth,
)
app.include_router(
    setup.router, prefix="/setup", tags=["Setup Wizard"],
    dependencies=_require_auth,
)
app.include_router(
    notifications.router, prefix="/notifications", tags=["Notifications"],
    dependencies=_require_auth,
)
app.include_router(
    workflows.router, prefix="/workflows", tags=["Workflows"],
    dependencies=_require_auth,
)
app.include_router(
    sod_rules.router, prefix="/risk-rules", tags=["Risk Rules"],
    dependencies=_require_auth,
)
app.include_router(
    ai.router, prefix="/ai", tags=["AI Intelligence"],
    dependencies=_require_auth,
)
app.include_router(
    tenants.router, prefix="/tenants", tags=["Tenants"],
    dependencies=_require_auth,
)
app.include_router(
    mobile.router, prefix="/mobile", tags=["Mobile API"],
    dependencies=_require_auth,
)
app.include_router(
    provisioning.router, prefix="/provisioning", tags=["Provisioning Engine"],
    dependencies=_require_auth,
)
app.include_router(
    security_controls.router, prefix="/security-controls",
    tags=["Security Controls"], dependencies=_require_auth,
)


app.include_router(
    admin.router, prefix="/admin", tags=["Super Admin Portal"],
    dependencies=_require_auth,
)
app.include_router(
    approvals.router, prefix="/approvals", tags=["Approvals"],
    dependencies=_require_auth,
)
app.include_router(
    reports.router, prefix="/reports", tags=["Reports"],
    dependencies=_require_auth,
)

# JWT Authentication — NO auth dependency (login/refresh must be public)
app.include_router(
    auth.router, prefix="/auth", tags=["Authentication"],
)

# SSO — SAML 2.0 + OAuth2/OIDC (public — handles its own auth)
app.include_router(
    sso_router.router, prefix="/auth", tags=["Single Sign-On"],
)

# Internationalisation — public so the login page can also use translations
app.include_router(
    i18n_router.router, prefix="/i18n", tags=["Internationalisation"],
)

# Document Retention & Legal Hold
app.include_router(
    retention_router.router, prefix="/retention",
    tags=["Document Retention & Legal Hold"], dependencies=_require_auth,
)

app.include_router(
    approver_management.router, prefix="/approver-management",
    tags=["Approver Management"], dependencies=_require_auth,
)
app.include_router(
    ara.router, prefix="/risk-intelligence", tags=["Risk Intelligence Engine"],
    dependencies=_require_auth,
)
app.include_router(
    governex_plus.router, prefix="/governex", tags=["GovernEx+ Advanced"],
    dependencies=_require_auth,
)
app.include_router(
    arm.router, prefix="/access-lifecycle", tags=["Access Lifecycle Manager - Cart"],
    dependencies=_require_auth,
)
app.include_router(
    role_intelligence.router, prefix="/role-intelligence",
    tags=["Role Design Studio - Intelligence"], dependencies=_require_auth,
)
app.include_router(
    troubleshooter.router, prefix="/troubleshooter",
    tags=["Access Troubleshooter"], dependencies=_require_auth,
)
app.include_router(
    migration.router, prefix="/migration", tags=["Migration Analyzer"],
    dependencies=_require_auth,
)
app.include_router(
    drift.router, prefix="/drift", tags=["Role Drift Detection"],
    dependencies=_require_auth,
)
app.include_router(
    audit_evidence.router, prefix="/audit-evidence",
    tags=["Audit Evidence Center"], dependencies=_require_auth,
)
app.include_router(
    timeline.router, prefix="/timeline", tags=["Access Timeline"],
    dependencies=_require_auth,
)
app.include_router(
    fiori.router, prefix="/fiori", tags=["Fiori Security Analyzer"],
    dependencies=_require_auth,
)
app.include_router(
    upgrade.router, prefix="/upgrade", tags=["Upgrade Impact Analyzer"],
    dependencies=_require_auth,
)
app.include_router(
    identity_correlation.router, prefix="/identity-correlation",
    tags=["Identity Correlation"], dependencies=_require_auth,
)
app.include_router(
    org_rules.router, prefix="/org-rules", tags=["Organizational Rules"],
    dependencies=_require_auth,
)
app.include_router(
    mass_admin.router, prefix="/mass-admin", tags=["Mass Administration"],
    dependencies=_require_auth,
)
app.include_router(
    repo_sync.router, prefix="/repo-sync", tags=["Repository Sync"],
    dependencies=_require_auth,
)
app.include_router(
    transport.router, prefix="/transport", tags=["Role Transport Management"],
    dependencies=_require_auth,
)
app.include_router(
    custom_tcode.router, prefix="/custom-tcode",
    tags=["Custom Transaction Analysis"], dependencies=_require_auth,
)
app.include_router(
    access_reports.router, prefix="/access-reports",
    tags=["Access Reports"], dependencies=_require_auth,
)
app.include_router(
    notification_delivery.router, prefix="/notification-delivery",
    tags=["Notification Delivery"], dependencies=_require_auth,
)
app.include_router(
    smtp_config_router.router, prefix="/settings",
    tags=["SMTP Configuration"], dependencies=_require_auth,
)
app.include_router(
    model_user.router, prefix="/model-user", tags=["Model User & Templates"],
    dependencies=_require_auth,
)
app.include_router(
    mitigation_monitoring.router, prefix="/controls-monitoring",
    tags=["Controls Monitoring"], dependencies=_require_auth,
)
app.include_router(
    ai_grc.router,
    tags=["GRC AI Assistant"],
    dependencies=_require_auth,
)

# ── GRC Suite Modules ──────────────────────────────────────────────────────
app.include_router(
    risk_mgmt.router, prefix="/risk-management",
    tags=["Enterprise Risk Engine"], dependencies=_require_auth,
)
app.include_router(
    process_ctrl.router, prefix="/process-control",
    tags=["Control Intelligence"], dependencies=_require_auth,
)
app.include_router(
    audit_mgmt.router, prefix="/audit-management",
    tags=["Audit Command Center"], dependencies=_require_auth,
)
app.include_router(
    org_hierarchy.router, prefix="/org",
    tags=["Org Hierarchy"], dependencies=_require_auth,
)
app.include_router(
    frameworks.router, prefix="/frameworks",
    tags=["Compliance Frameworks"], dependencies=_require_auth,
)
app.include_router(
    grc_dashboard.router, prefix="/grc",
    tags=["GRC Command Center"], dependencies=_require_auth,
)

# ── GRC Intelligence Engine ─────────────────────────────────────────────────
app.include_router(
    grc_intelligence.router, prefix="/grc-intelligence",
    tags=["GRC Intelligence"], dependencies=_require_auth,
)

# ── Role Redesign Copilot ────────────────────────────────────────────────────
app.include_router(
    role_redesign.router, prefix="/role-redesign",
    tags=["Role Redesign Copilot"], dependencies=_require_auth,
)

# ── Migration Copilot — ECC → S/4HANA ────────────────────────────────────────
app.include_router(
    migration_copilot.router, prefix="/migration-copilot",
    tags=["Migration Copilot"], dependencies=_require_auth,
)

# ── Audit Evidence Agent ──────────────────────────────────────────────────────
app.include_router(
    evidence_agent.router, prefix="/evidence-agent",
    tags=["Audit Evidence Agent"], dependencies=_require_auth,
)

# ── GRC Digital Twin ──────────────────────────────────────────────────────────
app.include_router(
    digital_twin.router, prefix="/digital-twin",
    tags=["GRC Digital Twin"], dependencies=_require_auth,
)

# ── GovernexPlus Feature Modules ──────────────────────────────────────────────
from api.routers import (
    risk_scenarios,
    policy_mgmt,
    question_library,
    subprocess_mgmt,
    control_objectives,
    role_methodology,
)

app.include_router(
    risk_scenarios.router, prefix="/risk-scenarios",
    tags=["Risk Scenarios & Opportunities"], dependencies=_require_auth,
)
app.include_router(
    policy_mgmt.router, prefix="/policies",
    tags=["Policy Management"], dependencies=_require_auth,
)
app.include_router(
    question_library.router, prefix="/questionnaires",
    tags=["Question Library & Questionnaires"], dependencies=_require_auth,
)
app.include_router(
    subprocess_mgmt.router, prefix="/subprocesses",
    tags=["Subprocess Management"], dependencies=_require_auth,
)
app.include_router(
    control_objectives.router, prefix="/control-objectives",
    tags=["Control Objectives"], dependencies=_require_auth,
)
app.include_router(
    role_methodology.router, prefix="/role-methodology",
    tags=["Role Methodology"], dependencies=_require_auth,
)

# ── Extended Modules — JML, TPRM, Fraud, BCM, Whistleblower, Survey ──────────
from api.routers import jml, tprm, fraud, bcm, whistleblower, survey as survey_router

app.include_router(
    jml.router, prefix="/jml",
    tags=["JML - Joiner Mover Leaver"], dependencies=_require_auth,
)
app.include_router(
    tprm.router, prefix="/tprm",
    tags=["Third-Party Risk Management"], dependencies=_require_auth,
)
app.include_router(
    fraud.router, prefix="/fraud",
    tags=["Fraud Detection"], dependencies=_require_auth,
)
app.include_router(
    bcm.router, prefix="/bcm",
    tags=["Business Continuity Management"], dependencies=_require_auth,
)
# Whistleblower: public submit/track endpoints need no auth — handled inside the router
app.include_router(
    whistleblower.router, prefix="/whistleblower",
    tags=["Whistleblower Intake"],
)
app.include_router(
    survey_router.router, prefix="/surveys",
    tags=["Survey Engine"], dependencies=_require_auth,
)

# ── Template Library — global content library with per-tenant activation ─────
from api.routers import library as library_router

app.include_router(
    library_router.router, prefix="/library",
    tags=["Template Library"], dependencies=_require_auth,
)

# Seed the template library on startup (idempotent)
# ── Prometheus Metrics — public (no auth) for Prometheus scraper ──────────────
app.include_router(metrics_router.router, tags=["Metrics"])


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
            "risk_intelligence_engine": "/risk",
            "users": "/users",
            "privileged_access_governor": "/privileged-access",
            "privileged_access_governor_monitoring": "/privileged-access/monitoring",
            "access_lifecycle_manager": "/access-requests",
            "certification": "/certification",
            "dashboard": "/dashboard",
            "role_design_studio": "/role-studio",
            "mitigation": "/mitigation",
            "cross_system": "/cross-system",
            "reporting": "/reporting",
            "integrations": "/integrations",
            "user_profiles": "/user-profiles",
            "audit": "/audit",
            "setup": "/setup",
            "notifications": "/notifications",
            "workflows": "/workflows",
            "sod_rules": "/risk-rules",
            "ai": "/ai",
            "security_controls": "/security-controls",
            "admin": "/admin",
            "ara": "/risk-intelligence",
            "governex_plus": "/governex",
            "enterprise_risk_engine": "/risk-management",
            "control_intelligence": "/process-control",
            "audit_command_center": "/audit-management",
            "org_hierarchy": "/org",
            "compliance_frameworks": "/frameworks",
            "grc_command_center": "/grc",
            "grc_intelligence": "/grc-intelligence",
            "role_redesign_copilot": "/role-redesign",
            "migration_copilot": "/migration-copilot",
            "evidence_agent": "/evidence-agent",
            "digital_twin": "/digital-twin",
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
# Authentication Endpoints — Real JWT
# =============================================================================

from pydantic import BaseModel
from sqlalchemy.orm import Session as DBSession

_security = HTTPBearer(auto_error=False)


class LoginRequest(BaseModel):
    username: str
    password: str
    tenant_id: str = "tenant_default"


@app.post("/auth/login", tags=["Auth"])
@limiter.limit(RATE_LIMIT_AUTH)
async def login(request: Request, body: LoginRequest, db: DBSession = Depends(get_db)):
    """
    Authenticate with username/password, returns JWT tokens.
    Rate limited to prevent brute-force attacks.
    """
    auth_svc = AuthService(db)
    token_response, error = auth_svc.authenticate(
        tenant_id=body.tenant_id,
        username=body.username,
        password=body.password,
    )
    if error:
        raise HTTPException(status_code=401, detail=error)
    return token_response


@app.post("/auth/logout", tags=["Auth"])
async def logout(
    credentials: HTTPAuthorizationCredentials = Depends(_security),
    user=Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    """Logout — revokes the current token"""
    token = credentials.credentials if credentials else None
    auth_svc = AuthService(db)
    auth_svc.logout(
        tenant_id=user.get("tenant_id", "tenant_default"),
        user_id=user.get("sub", ""),
        token=token,
    )
    return {"message": "Logged out successfully"}


@app.get("/auth/profile", tags=["Auth"])
async def get_profile(
    user=Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    """Get current authenticated user profile"""
    auth_svc = AuthService(db)
    profile = auth_svc.get_user_profile(
        tenant_id=user.get("tenant_id", "tenant_default"),
        user_id=user.get("sub", ""),
    )
    if not profile:
        raise HTTPException(status_code=404, detail="User profile not found")
    return profile


@app.get("/info", tags=["System"])
async def system_info(user=Depends(get_current_user)):
    """Get system information and statistics (requires auth)"""
    from core.rules import RuleEngine

    rule_engine = RuleEngine()

    return {
        "platform": "Governex+",
        "version": "1.0.0",
        "capabilities": [
            "Segregation of Duties (SoD) Analysis",
            "Sensitive Access Detection",
            "Firefighter/Emergency Access Management",
            "Access Request with Risk Preview",
            "Batch Risk Analysis",
            "Comprehensive Audit Logging",
            "Compliance Reporting",
            "Auto-Remediation Suggestions",
            "Role Engineering & Optimization",
            "Cross-System SoD Analysis",
        ],
        "statistics": {
            "rules_loaded": len(rule_engine.rules),
            "rule_categories": list(rule_engine.rule_index_by_category.keys())
        },
        "supported_systems": [
            "SAP ECC 6.0",
            "SAP S/4HANA",
        ]
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
