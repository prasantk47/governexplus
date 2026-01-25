# Usage Metering & Billing
# Track usage and manage subscriptions

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum
from datetime import datetime, timedelta
from collections import defaultdict
import uuid


class UsageType(Enum):
    """Types of metered usage"""
    API_CALLS = "api_calls"
    USERS = "users"
    SYSTEMS = "systems"
    STORAGE_GB = "storage_gb"
    RISK_ANALYSES = "risk_analyses"
    ACCESS_REQUESTS = "access_requests"
    CERTIFICATIONS = "certifications"
    AI_QUERIES = "ai_queries"
    REPORTS = "reports"


class BillingInterval(Enum):
    """Billing intervals"""
    MONTHLY = "monthly"
    ANNUAL = "annual"


class InvoiceStatus(Enum):
    """Invoice status"""
    DRAFT = "draft"
    PENDING = "pending"
    PAID = "paid"
    OVERDUE = "overdue"
    VOID = "void"


@dataclass
class UsageRecord:
    """Individual usage record"""
    id: str = ""
    tenant_id: str = ""
    usage_type: UsageType = UsageType.API_CALLS
    quantity: float = 0.0
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.id:
            self.id = f"usage_{uuid.uuid4().hex[:12]}"


@dataclass
class BillingPlan:
    """Subscription plan definition"""
    id: str
    name: str
    tier: str
    interval: BillingInterval = BillingInterval.MONTHLY

    # Pricing
    base_price: float = 0.0
    price_per_user: float = 0.0
    price_per_system: float = 0.0
    price_per_gb: float = 0.0

    # Included amounts
    included_users: int = 0
    included_systems: int = 0
    included_storage_gb: float = 0.0
    included_api_calls: int = 0

    # Overage rates
    overage_per_user: float = 0.0
    overage_per_system: float = 0.0
    overage_per_gb: float = 0.0
    overage_per_1k_api: float = 0.0

    # Discounts
    annual_discount: float = 0.0  # % discount for annual billing

    # Features
    features: List[str] = field(default_factory=list)


@dataclass
class Invoice:
    """Invoice for billing"""
    id: str = ""
    tenant_id: str = ""
    plan_id: str = ""
    status: InvoiceStatus = InvoiceStatus.DRAFT

    # Period
    period_start: datetime = field(default_factory=datetime.utcnow)
    period_end: datetime = field(default_factory=datetime.utcnow)

    # Amounts
    base_amount: float = 0.0
    usage_amount: float = 0.0
    discount_amount: float = 0.0
    tax_amount: float = 0.0
    total_amount: float = 0.0

    # Line items
    line_items: List[Dict[str, Any]] = field(default_factory=list)

    # Payment
    due_date: datetime = field(default_factory=datetime.utcnow)
    paid_date: Optional[datetime] = None
    payment_method: str = ""
    payment_id: str = ""

    # Metadata
    created_at: datetime = field(default_factory=datetime.utcnow)
    currency: str = "USD"

    def __post_init__(self):
        if not self.id:
            self.id = f"inv_{uuid.uuid4().hex[:12]}"


class UsageMeter:
    """
    Usage Metering System

    Tracks all metered usage for billing:
    - API calls
    - Active users
    - Connected systems
    - Storage consumption
    - Feature usage
    """

    def __init__(self):
        # Usage records by tenant
        self.records: Dict[str, List[UsageRecord]] = defaultdict(list)

        # Real-time counters (for rate limiting)
        self.counters: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))

        # Daily aggregates
        self.daily_aggregates: Dict[str, Dict[str, Dict[str, float]]] = defaultdict(
            lambda: defaultdict(lambda: defaultdict(float))
        )

    def record_usage(
        self,
        tenant_id: str,
        usage_type: UsageType,
        quantity: float = 1.0,
        metadata: Dict[str, Any] = None
    ) -> UsageRecord:
        """Record a usage event"""
        record = UsageRecord(
            tenant_id=tenant_id,
            usage_type=usage_type,
            quantity=quantity,
            metadata=metadata or {}
        )

        self.records[tenant_id].append(record)

        # Update real-time counter
        today = datetime.utcnow().strftime("%Y-%m-%d")
        self.counters[tenant_id][f"{usage_type.value}:{today}"] += int(quantity)

        # Update daily aggregate
        self.daily_aggregates[tenant_id][today][usage_type.value] += quantity

        return record

    def get_usage_summary(
        self,
        tenant_id: str,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Get usage summary for a period"""
        records = self.records.get(tenant_id, [])

        # Filter by date range
        period_records = [
            r for r in records
            if start_date <= r.timestamp <= end_date
        ]

        # Aggregate by type
        usage_by_type = defaultdict(float)
        for record in period_records:
            usage_by_type[record.usage_type.value] += record.quantity

        return {
            "tenant_id": tenant_id,
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "usage": dict(usage_by_type),
            "record_count": len(period_records)
        }

    def get_current_month_usage(self, tenant_id: str) -> Dict[str, Any]:
        """Get current month's usage"""
        now = datetime.utcnow()
        start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        return self.get_usage_summary(tenant_id, start_of_month, now)

    def check_rate_limit(
        self,
        tenant_id: str,
        usage_type: UsageType,
        limit: int
    ) -> Dict[str, Any]:
        """Check if tenant is within rate limit"""
        today = datetime.utcnow().strftime("%Y-%m-%d")
        current = self.counters[tenant_id].get(f"{usage_type.value}:{today}", 0)

        return {
            "within_limit": current < limit,
            "current": current,
            "limit": limit,
            "remaining": max(0, limit - current)
        }

    def get_daily_trend(
        self,
        tenant_id: str,
        usage_type: UsageType,
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """Get daily usage trend"""
        trend = []
        for i in range(days):
            date = (datetime.utcnow() - timedelta(days=i)).strftime("%Y-%m-%d")
            value = self.daily_aggregates[tenant_id][date].get(usage_type.value, 0)
            trend.append({"date": date, "value": value})

        trend.reverse()
        return trend


class BillingManager:
    """
    Billing Management System

    Handles:
    - Subscription plans
    - Invoice generation
    - Payment processing (integration)
    - Usage-based billing calculation
    """

    def __init__(self):
        self.plans: Dict[str, BillingPlan] = {}
        self.subscriptions: Dict[str, Dict[str, Any]] = {}  # tenant_id -> subscription
        self.invoices: Dict[str, List[Invoice]] = defaultdict(list)
        self.usage_meter = UsageMeter()

        self._initialize_plans()

    def _initialize_plans(self):
        """Initialize billing plans"""
        self.plans = {
            "free": BillingPlan(
                id="free",
                name="Free",
                tier="free",
                base_price=0,
                included_users=5,
                included_systems=1,
                included_storage_gb=0.5,
                included_api_calls=1000,
                features=["Basic risk analysis", "Manual access requests"]
            ),
            "starter_monthly": BillingPlan(
                id="starter_monthly",
                name="Starter",
                tier="starter",
                interval=BillingInterval.MONTHLY,
                base_price=99,
                included_users=25,
                included_systems=3,
                included_storage_gb=5,
                included_api_calls=10000,
                overage_per_user=5,
                overage_per_system=20,
                overage_per_gb=1,
                features=[
                    "SoD analysis",
                    "Access requests",
                    "Basic reporting",
                    "Email support"
                ]
            ),
            "starter_annual": BillingPlan(
                id="starter_annual",
                name="Starter (Annual)",
                tier="starter",
                interval=BillingInterval.ANNUAL,
                base_price=999,  # ~17% discount
                included_users=25,
                included_systems=3,
                included_storage_gb=5,
                included_api_calls=10000,
                annual_discount=17,
                features=[
                    "SoD analysis",
                    "Access requests",
                    "Basic reporting",
                    "Email support"
                ]
            ),
            "professional_monthly": BillingPlan(
                id="professional_monthly",
                name="Professional",
                tier="professional",
                interval=BillingInterval.MONTHLY,
                base_price=499,
                included_users=100,
                included_systems=10,
                included_storage_gb=50,
                included_api_calls=100000,
                overage_per_user=4,
                overage_per_system=15,
                overage_per_gb=0.5,
                features=[
                    "Everything in Starter",
                    "AI risk scoring",
                    "SSO integration",
                    "Advanced analytics",
                    "Priority support",
                    "SLA guarantee"
                ]
            ),
            "professional_annual": BillingPlan(
                id="professional_annual",
                name="Professional (Annual)",
                tier="professional",
                interval=BillingInterval.ANNUAL,
                base_price=4999,  # ~17% discount
                included_users=100,
                included_systems=10,
                included_storage_gb=50,
                included_api_calls=100000,
                annual_discount=17,
                features=[
                    "Everything in Starter",
                    "AI risk scoring",
                    "SSO integration",
                    "Advanced analytics",
                    "Priority support",
                    "SLA guarantee"
                ]
            ),
            "enterprise": BillingPlan(
                id="enterprise",
                name="Enterprise",
                tier="enterprise",
                interval=BillingInterval.ANNUAL,
                base_price=0,  # Custom pricing
                included_users=10000,
                included_systems=100,
                included_storage_gb=1000,
                included_api_calls=10000000,
                features=[
                    "Everything in Professional",
                    "Dedicated support",
                    "Custom integrations",
                    "On-premise option",
                    "Custom SLA",
                    "Dedicated account manager"
                ]
            )
        }

    # ==================== Subscriptions ====================

    def create_subscription(
        self,
        tenant_id: str,
        plan_id: str,
        payment_method_id: str = ""
    ) -> Dict[str, Any]:
        """Create a new subscription"""
        plan = self.plans.get(plan_id)
        if not plan:
            return {"success": False, "error": "Plan not found"}

        now = datetime.utcnow()

        if plan.interval == BillingInterval.MONTHLY:
            next_billing = now + timedelta(days=30)
        else:
            next_billing = now + timedelta(days=365)

        subscription = {
            "id": f"sub_{uuid.uuid4().hex[:12]}",
            "tenant_id": tenant_id,
            "plan_id": plan_id,
            "plan_name": plan.name,
            "status": "active",
            "current_period_start": now,
            "current_period_end": next_billing,
            "payment_method_id": payment_method_id,
            "created_at": now
        }

        self.subscriptions[tenant_id] = subscription

        return {
            "success": True,
            "subscription": subscription
        }

    def get_subscription(self, tenant_id: str) -> Optional[Dict[str, Any]]:
        """Get tenant's current subscription"""
        return self.subscriptions.get(tenant_id)

    def cancel_subscription(
        self,
        tenant_id: str,
        at_period_end: bool = True
    ) -> Dict[str, Any]:
        """Cancel a subscription"""
        subscription = self.subscriptions.get(tenant_id)
        if not subscription:
            return {"success": False, "error": "Subscription not found"}

        if at_period_end:
            subscription["cancel_at_period_end"] = True
            subscription["status"] = "canceling"
            message = f"Subscription will cancel at {subscription['current_period_end']}"
        else:
            subscription["status"] = "canceled"
            subscription["canceled_at"] = datetime.utcnow()
            message = "Subscription canceled immediately"

        return {
            "success": True,
            "message": message,
            "subscription": subscription
        }

    def change_plan(
        self,
        tenant_id: str,
        new_plan_id: str,
        prorate: bool = True
    ) -> Dict[str, Any]:
        """Change subscription plan"""
        subscription = self.subscriptions.get(tenant_id)
        if not subscription:
            return {"success": False, "error": "Subscription not found"}

        new_plan = self.plans.get(new_plan_id)
        if not new_plan:
            return {"success": False, "error": "Plan not found"}

        old_plan_id = subscription["plan_id"]
        old_plan = self.plans.get(old_plan_id)

        # Calculate proration if upgrading mid-cycle
        proration_amount = 0.0
        if prorate and old_plan:
            days_remaining = (subscription["current_period_end"] - datetime.utcnow()).days
            total_days = 30 if old_plan.interval == BillingInterval.MONTHLY else 365

            old_daily_rate = old_plan.base_price / total_days
            new_daily_rate = new_plan.base_price / total_days

            proration_amount = (new_daily_rate - old_daily_rate) * days_remaining

        subscription["plan_id"] = new_plan_id
        subscription["plan_name"] = new_plan.name

        return {
            "success": True,
            "old_plan": old_plan_id,
            "new_plan": new_plan_id,
            "proration_amount": round(proration_amount, 2),
            "message": f"Plan changed from {old_plan.name if old_plan else 'Unknown'} to {new_plan.name}"
        }

    # ==================== Invoicing ====================

    def generate_invoice(
        self,
        tenant_id: str,
        period_start: datetime = None,
        period_end: datetime = None
    ) -> Invoice:
        """Generate invoice for a billing period"""
        subscription = self.subscriptions.get(tenant_id)
        if not subscription:
            raise ValueError("No subscription found for tenant")

        plan = self.plans.get(subscription["plan_id"])
        if not plan:
            raise ValueError("Plan not found")

        # Default to current billing period
        if not period_start:
            period_start = subscription["current_period_start"]
        if not period_end:
            period_end = subscription["current_period_end"]

        # Get usage for period
        usage = self.usage_meter.get_usage_summary(
            tenant_id, period_start, period_end
        )

        # Calculate line items
        line_items = []

        # Base subscription
        line_items.append({
            "description": f"{plan.name} Subscription",
            "quantity": 1,
            "unit_price": plan.base_price,
            "amount": plan.base_price
        })

        # Usage-based charges (overages)
        usage_data = usage.get("usage", {})

        # User overage
        users = usage_data.get("users", 0)
        if users > plan.included_users:
            overage = users - plan.included_users
            overage_cost = overage * plan.overage_per_user
            line_items.append({
                "description": f"Additional users ({overage} users)",
                "quantity": overage,
                "unit_price": plan.overage_per_user,
                "amount": overage_cost
            })

        # System overage
        systems = usage_data.get("systems", 0)
        if systems > plan.included_systems:
            overage = systems - plan.included_systems
            overage_cost = overage * plan.overage_per_system
            line_items.append({
                "description": f"Additional systems ({overage} systems)",
                "quantity": overage,
                "unit_price": plan.overage_per_system,
                "amount": overage_cost
            })

        # Storage overage
        storage = usage_data.get("storage_gb", 0)
        if storage > plan.included_storage_gb:
            overage = storage - plan.included_storage_gb
            overage_cost = overage * plan.overage_per_gb
            line_items.append({
                "description": f"Additional storage ({overage:.2f} GB)",
                "quantity": overage,
                "unit_price": plan.overage_per_gb,
                "amount": overage_cost
            })

        # Calculate totals
        base_amount = plan.base_price
        usage_amount = sum(
            item["amount"] for item in line_items
            if item["description"] != f"{plan.name} Subscription"
        )
        total_before_tax = base_amount + usage_amount

        # Apply any discounts (e.g., annual discount already in price)
        discount_amount = 0.0

        # Tax (simplified - would use tax service)
        tax_rate = 0.0  # Would be based on location
        tax_amount = total_before_tax * tax_rate

        total_amount = total_before_tax - discount_amount + tax_amount

        # Create invoice
        invoice = Invoice(
            tenant_id=tenant_id,
            plan_id=plan.id,
            status=InvoiceStatus.PENDING,
            period_start=period_start,
            period_end=period_end,
            base_amount=base_amount,
            usage_amount=usage_amount,
            discount_amount=discount_amount,
            tax_amount=tax_amount,
            total_amount=round(total_amount, 2),
            line_items=line_items,
            due_date=period_end + timedelta(days=15)
        )

        self.invoices[tenant_id].append(invoice)

        return invoice

    def get_invoices(
        self,
        tenant_id: str,
        status: InvoiceStatus = None,
        limit: int = 10
    ) -> List[Invoice]:
        """Get invoices for a tenant"""
        invoices = self.invoices.get(tenant_id, [])

        if status:
            invoices = [i for i in invoices if i.status == status]

        return sorted(invoices, key=lambda i: i.created_at, reverse=True)[:limit]

    def pay_invoice(
        self,
        invoice_id: str,
        payment_method_id: str
    ) -> Dict[str, Any]:
        """Process payment for an invoice"""
        # Find invoice
        invoice = None
        for tenant_invoices in self.invoices.values():
            for inv in tenant_invoices:
                if inv.id == invoice_id:
                    invoice = inv
                    break

        if not invoice:
            return {"success": False, "error": "Invoice not found"}

        if invoice.status == InvoiceStatus.PAID:
            return {"success": False, "error": "Invoice already paid"}

        # Would process payment through Stripe/payment provider here
        invoice.status = InvoiceStatus.PAID
        invoice.paid_date = datetime.utcnow()
        invoice.payment_method = payment_method_id
        invoice.payment_id = f"pay_{uuid.uuid4().hex[:12]}"

        return {
            "success": True,
            "invoice_id": invoice_id,
            "amount_paid": invoice.total_amount,
            "payment_id": invoice.payment_id
        }

    # ==================== Usage Tracking Convenience ====================

    def track_api_call(self, tenant_id: str) -> None:
        """Track an API call"""
        self.usage_meter.record_usage(tenant_id, UsageType.API_CALLS, 1)

    def track_ai_query(self, tenant_id: str) -> None:
        """Track an AI feature usage"""
        self.usage_meter.record_usage(tenant_id, UsageType.AI_QUERIES, 1)

    def track_risk_analysis(self, tenant_id: str, users_analyzed: int = 1) -> None:
        """Track risk analysis usage"""
        self.usage_meter.record_usage(
            tenant_id, UsageType.RISK_ANALYSES, users_analyzed
        )

    def get_billing_summary(self, tenant_id: str) -> Dict[str, Any]:
        """Get comprehensive billing summary"""
        subscription = self.subscriptions.get(tenant_id)
        if not subscription:
            return {"error": "No subscription found"}

        plan = self.plans.get(subscription["plan_id"])
        current_usage = self.usage_meter.get_current_month_usage(tenant_id)
        recent_invoices = self.get_invoices(tenant_id, limit=3)

        return {
            "subscription": {
                "plan": plan.name if plan else "Unknown",
                "status": subscription["status"],
                "current_period_end": subscription["current_period_end"].isoformat(),
                "base_price": plan.base_price if plan else 0
            },
            "current_usage": current_usage["usage"],
            "limits": {
                "users": plan.included_users if plan else 0,
                "systems": plan.included_systems if plan else 0,
                "storage_gb": plan.included_storage_gb if plan else 0,
                "api_calls": plan.included_api_calls if plan else 0
            },
            "recent_invoices": [
                {
                    "id": inv.id,
                    "amount": inv.total_amount,
                    "status": inv.status.value,
                    "date": inv.created_at.isoformat()
                }
                for inv in recent_invoices
            ]
        }
