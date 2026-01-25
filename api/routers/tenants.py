# Tenant Management API Router
# Multi-tenant SaaS management endpoints

from fastapi import APIRouter, HTTPException, Query, Header, Depends
from pydantic import BaseModel, EmailStr
from typing import Dict, List, Optional, Any
from datetime import datetime

from core.tenant import (
    TenantManager, Tenant, TenantStatus, TenantTier, TenantConfig,
    TenantOnboarding, OnboardingStatus,
    BillingManager, UsageMeter, UsageType,
    TenantIsolation, DataIsolationStrategy,
    get_current_tenant, TenantContext
)

router = APIRouter(prefix="/tenants", tags=["Tenants"])

# Initialize services
tenant_manager = TenantManager()
onboarding = TenantOnboarding()
billing = BillingManager()
isolation = TenantIsolation()


# ==================== Request/Response Models ====================

class SignupRequest(BaseModel):
    email: str
    company_name: str = ""


class VerifyEmailRequest(BaseModel):
    token: str


class OnboardingStepRequest(BaseModel):
    step_id: str
    data: Dict[str, Any] = {}


class CreateTenantRequest(BaseModel):
    name: str
    owner_email: str
    tier: str = "free"
    trial_days: int = 14


class UpdateTenantRequest(BaseModel):
    name: Optional[str] = None
    config: Optional[Dict[str, Any]] = None


class UpgradeTierRequest(BaseModel):
    new_tier: str


class SubscriptionRequest(BaseModel):
    plan_id: str
    payment_method_id: str = ""


class UsageRecordRequest(BaseModel):
    usage_type: str
    quantity: float = 1.0
    metadata: Dict[str, Any] = {}


# ==================== Public Onboarding Endpoints ====================

@router.post("/signup")
async def start_signup(request: SignupRequest):
    """
    Start the self-service signup process

    Sends verification email and creates onboarding session.
    """
    result = onboarding.start_signup(
        email=request.email,
        company_name=request.company_name
    )
    return result


@router.post("/verify-email")
async def verify_email(request: VerifyEmailRequest):
    """Verify email address with token from email"""
    result = onboarding.verify_email(request.token)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/onboarding/{session_id}")
async def get_onboarding_status(session_id: str):
    """Get current onboarding status"""
    status = onboarding.get_session_status(session_id)
    if "error" in status:
        raise HTTPException(status_code=404, detail=status["error"])
    return status


@router.post("/onboarding/{session_id}/step")
async def submit_onboarding_step(session_id: str, request: OnboardingStepRequest):
    """Submit data for an onboarding step"""
    result = onboarding.submit_step(
        session_id=session_id,
        step_id=request.step_id,
        data=request.data
    )
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error", "Step failed"))
    return result


@router.post("/onboarding/{session_id}/skip")
async def skip_onboarding_step(session_id: str, step_id: str):
    """Skip an optional onboarding step"""
    result = onboarding.skip_step(session_id, step_id)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


# ==================== Tenant Management (Admin) ====================

@router.post("/")
async def create_tenant(request: CreateTenantRequest):
    """
    Create a new tenant (admin operation)

    For self-service signups, use /signup instead.
    """
    try:
        tier = TenantTier(request.tier)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid tier: {request.tier}")

    result = tenant_manager.create_tenant(
        name=request.name,
        owner_email=request.owner_email,
        tier=tier,
        trial_days=request.trial_days
    )

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])

    return result


@router.get("/")
async def list_tenants(
    status: Optional[str] = None,
    tier: Optional[str] = None,
    limit: int = Query(default=50, le=200)
):
    """List all tenants (platform admin only)"""
    status_filter = None
    tier_filter = None

    if status:
        try:
            status_filter = TenantStatus(status)
        except ValueError:
            pass

    if tier:
        try:
            tier_filter = TenantTier(tier)
        except ValueError:
            pass

    tenants = tenant_manager.list_tenants(
        status=status_filter,
        tier=tier_filter,
        limit=limit
    )

    return {
        "tenants": [
            {
                "id": t.id,
                "name": t.name,
                "slug": t.slug,
                "status": t.status.value,
                "tier": t.tier.value,
                "owner_email": t.owner_email,
                "current_users": t.current_users,
                "created_at": t.created_at.isoformat()
            }
            for t in tenants
        ],
        "total": len(tenants)
    }


@router.get("/{tenant_id}")
async def get_tenant(tenant_id: str):
    """Get tenant details"""
    summary = tenant_manager.get_tenant_summary(tenant_id)
    if "error" in summary:
        raise HTTPException(status_code=404, detail=summary["error"])
    return summary


@router.put("/{tenant_id}")
async def update_tenant(tenant_id: str, request: UpdateTenantRequest):
    """Update tenant settings"""
    tenant = tenant_manager.get_tenant(tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    if request.name:
        tenant.name = request.name

    if request.config:
        # Update config fields
        for key, value in request.config.items():
            if hasattr(tenant.config, key):
                setattr(tenant.config, key, value)

    tenant.updated_at = datetime.utcnow()

    return {"success": True, "message": "Tenant updated"}


@router.post("/{tenant_id}/activate")
async def activate_tenant(tenant_id: str):
    """Activate a pending tenant"""
    result = tenant_manager.activate_tenant(tenant_id)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/{tenant_id}/suspend")
async def suspend_tenant(tenant_id: str, reason: str = ""):
    """Suspend a tenant"""
    result = tenant_manager.suspend_tenant(tenant_id, reason)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/{tenant_id}/reactivate")
async def reactivate_tenant(tenant_id: str):
    """Reactivate a suspended tenant"""
    result = tenant_manager.reactivate_tenant(tenant_id)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.delete("/{tenant_id}")
async def deactivate_tenant(tenant_id: str):
    """Deactivate (soft delete) a tenant"""
    result = tenant_manager.deactivate_tenant(tenant_id)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


# ==================== Tier Management ====================

@router.get("/tiers")
async def list_tiers():
    """List available subscription tiers"""
    return {
        "tiers": [
            {
                "id": tier.value,
                "name": tier.name,
                "limits": {
                    "max_users": limits.max_users,
                    "max_systems": limits.max_systems,
                    "max_roles": limits.max_roles,
                    "max_storage_gb": limits.max_storage_gb,
                    "sso_enabled": limits.sso_enabled,
                    "ai_features": limits.ai_features,
                    "advanced_analytics": limits.advanced_analytics,
                    "dedicated_support": limits.dedicated_support
                }
            }
            for tier, limits in tenant_manager.tier_limits.items()
        ]
    }


@router.post("/{tenant_id}/upgrade")
async def upgrade_tier(tenant_id: str, request: UpgradeTierRequest):
    """Upgrade tenant to a higher tier"""
    try:
        new_tier = TenantTier(request.new_tier)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid tier: {request.new_tier}")

    result = tenant_manager.upgrade_tier(tenant_id, new_tier)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/{tenant_id}/downgrade")
async def downgrade_tier(tenant_id: str, request: UpgradeTierRequest):
    """Downgrade tenant tier (with validation)"""
    try:
        new_tier = TenantTier(request.new_tier)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid tier: {request.new_tier}")

    result = tenant_manager.downgrade_tier(tenant_id, new_tier)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


# ==================== Usage & Limits ====================

@router.get("/{tenant_id}/usage")
async def get_usage(tenant_id: str):
    """Get tenant usage summary"""
    current_month = billing.usage_meter.get_current_month_usage(tenant_id)
    return current_month


@router.get("/{tenant_id}/usage/trend")
async def get_usage_trend(
    tenant_id: str,
    usage_type: str = "api_calls",
    days: int = Query(default=30, le=90)
):
    """Get usage trend over time"""
    try:
        u_type = UsageType(usage_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid usage type: {usage_type}")

    trend = billing.usage_meter.get_daily_trend(tenant_id, u_type, days)
    return {"trend": trend}


@router.post("/{tenant_id}/usage/record")
async def record_usage(tenant_id: str, request: UsageRecordRequest):
    """Record usage event (internal use)"""
    try:
        u_type = UsageType(request.usage_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid usage type: {request.usage_type}")

    record = billing.usage_meter.record_usage(
        tenant_id=tenant_id,
        usage_type=u_type,
        quantity=request.quantity,
        metadata=request.metadata
    )

    return {"success": True, "record_id": record.id}


@router.get("/{tenant_id}/limits/check")
async def check_limit(
    tenant_id: str,
    resource: str,
    requested: int = Query(default=1, ge=1)
):
    """Check if action is within tenant limits"""
    result = tenant_manager.check_limit(tenant_id, resource, requested)
    return result


# ==================== Billing ====================

@router.get("/plans")
async def list_plans():
    """List available billing plans"""
    return {
        "plans": [
            {
                "id": plan.id,
                "name": plan.name,
                "tier": plan.tier,
                "interval": plan.interval.value,
                "base_price": plan.base_price,
                "included_users": plan.included_users,
                "included_systems": plan.included_systems,
                "included_storage_gb": plan.included_storage_gb,
                "features": plan.features,
                "annual_discount": plan.annual_discount
            }
            for plan in billing.plans.values()
        ]
    }


@router.post("/{tenant_id}/subscription")
async def create_subscription(tenant_id: str, request: SubscriptionRequest):
    """Create or update subscription"""
    result = billing.create_subscription(
        tenant_id=tenant_id,
        plan_id=request.plan_id,
        payment_method_id=request.payment_method_id
    )
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/{tenant_id}/subscription")
async def get_subscription(tenant_id: str):
    """Get current subscription"""
    subscription = billing.get_subscription(tenant_id)
    if not subscription:
        raise HTTPException(status_code=404, detail="No subscription found")
    return subscription


@router.delete("/{tenant_id}/subscription")
async def cancel_subscription(tenant_id: str, immediate: bool = False):
    """Cancel subscription"""
    result = billing.cancel_subscription(tenant_id, at_period_end=not immediate)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/{tenant_id}/subscription/change-plan")
async def change_plan(tenant_id: str, request: SubscriptionRequest):
    """Change subscription plan"""
    result = billing.change_plan(tenant_id, request.plan_id)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/{tenant_id}/billing")
async def get_billing_summary(tenant_id: str):
    """Get comprehensive billing summary"""
    summary = billing.get_billing_summary(tenant_id)
    if "error" in summary:
        raise HTTPException(status_code=404, detail=summary["error"])
    return summary


@router.get("/{tenant_id}/invoices")
async def list_invoices(
    tenant_id: str,
    status: Optional[str] = None,
    limit: int = Query(default=10, le=50)
):
    """List invoices for tenant"""
    from core.tenant.billing import InvoiceStatus

    status_filter = None
    if status:
        try:
            status_filter = InvoiceStatus(status)
        except ValueError:
            pass

    invoices = billing.get_invoices(tenant_id, status=status_filter, limit=limit)

    return {
        "invoices": [
            {
                "id": inv.id,
                "status": inv.status.value,
                "period_start": inv.period_start.isoformat(),
                "period_end": inv.period_end.isoformat(),
                "total_amount": inv.total_amount,
                "due_date": inv.due_date.isoformat(),
                "paid_date": inv.paid_date.isoformat() if inv.paid_date else None
            }
            for inv in invoices
        ]
    }


@router.post("/{tenant_id}/invoices/generate")
async def generate_invoice(tenant_id: str):
    """Generate invoice for current period"""
    try:
        invoice = billing.generate_invoice(tenant_id)
        return {
            "success": True,
            "invoice_id": invoice.id,
            "total_amount": invoice.total_amount,
            "line_items": invoice.line_items
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==================== Data Isolation ====================

@router.get("/{tenant_id}/isolation")
async def get_isolation_info(tenant_id: str):
    """Get data isolation information"""
    db = isolation.databases.get(tenant_id)
    storage = isolation.storage.get(tenant_id)

    return {
        "tenant_id": tenant_id,
        "database": {
            "strategy": db.strategy.value if db else None,
            "encrypted": db.encrypted_at_rest if db else None,
            "provisioned": db is not None
        },
        "storage": {
            "bucket": storage.bucket_name if storage else None,
            "prefix": storage.prefix if storage else None,
            "encrypted": storage.encrypted if storage else None,
            "provisioned": storage is not None
        }
    }


@router.get("/{tenant_id}/data-residency")
async def get_data_residency(tenant_id: str):
    """Get data residency and compliance info"""
    return isolation.get_data_residency_info(tenant_id)


@router.post("/{tenant_id}/rotate-keys")
async def rotate_encryption_keys(tenant_id: str):
    """Rotate encryption keys for tenant"""
    result = isolation.rotate_encryption_keys(tenant_id)
    return result


# ==================== Multi-Tenant Info ====================

@router.get("/info")
async def get_multitenancy_info():
    """Get multi-tenancy platform information"""
    return {
        "platform": "GRC Zero Trust Platform",
        "multi_tenant": True,
        "features": {
            "self_service_signup": True,
            "automatic_provisioning": True,
            "tier_based_limits": True,
            "usage_based_billing": True,
            "data_isolation": True,
            "per_tenant_encryption": True,
            "custom_domains": True,
            "sso_support": True
        },
        "isolation_strategies": [s.value for s in DataIsolationStrategy],
        "available_tiers": [t.value for t in TenantTier],
        "compliance": {
            "gdpr": True,
            "sox": True,
            "hipaa_eligible": True,
            "iso27001": True
        }
    }
