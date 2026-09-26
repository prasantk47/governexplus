"""
Access Request Management (ARM) — Shopping Cart Engine

SAP GRC-style access request workflow:
- Browse a catalog of available roles/entitlements
- Add items to a shopping cart with justification
- Real-time SoD conflict checking against existing user access
- Duplicate detection (user already has this role)
- Peer-based role recommendations
- Submit cart as access request(s) routed through approval workflow
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum
import uuid
import logging

from core.rules.sod_ruleset import SoDRulesetLibrary, RiskLevel, BusinessProcess

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class CatalogCategory(Enum):
    FINANCE = "Finance"
    PROCUREMENT = "Procurement"
    HR = "Human Resources"
    IT = "IT Administration"
    SALES = "Sales"
    WAREHOUSE = "Warehouse"
    QUALITY = "Quality Management"
    PLANT_MAINTENANCE = "Plant Maintenance"
    BASIS = "Basis / Security"
    CROSS_FUNCTIONAL = "Cross-Functional"


class CartStatus(Enum):
    DRAFT = "draft"
    CHECKING = "checking"
    READY = "ready"
    SUBMITTED = "submitted"
    CANCELLED = "cancelled"


class RequestDuration(Enum):
    PERMANENT = "permanent"
    THIRTY_DAYS = "30_days"
    SIXTY_DAYS = "60_days"
    NINETY_DAYS = "90_days"
    SIX_MONTHS = "6_months"
    ONE_YEAR = "1_year"
    CUSTOM = "custom"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class AccessCatalogItem:
    """A single role or entitlement available in the catalog."""
    role_id: str
    role_name: str
    system: str
    description: str
    risk_level: str  # low / medium / high / critical
    category: str
    auto_approvable: bool = False
    owner: str = ""
    transaction_codes: List[str] = field(default_factory=list)
    business_process: str = ""
    sap_role_type: str = "single"  # single, composite, derived
    requires_justification: bool = True
    max_duration: str = "permanent"
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "role_id": self.role_id,
            "role_name": self.role_name,
            "system": self.system,
            "description": self.description,
            "risk_level": self.risk_level,
            "category": self.category,
            "auto_approvable": self.auto_approvable,
            "owner": self.owner,
            "transaction_codes": self.transaction_codes,
            "business_process": self.business_process,
            "sap_role_type": self.sap_role_type,
            "requires_justification": self.requires_justification,
            "max_duration": self.max_duration,
            "tags": self.tags,
        }


@dataclass
class CartItem:
    """An item in the user's shopping cart."""
    item_id: str
    catalog_item: AccessCatalogItem
    justification: str = ""
    requested_for: str = ""  # user_id the access is being requested for
    requested_duration: str = "permanent"
    custom_end_date: Optional[str] = None
    added_at: str = ""
    priority: str = "normal"  # low, normal, high, critical

    def __post_init__(self):
        if not self.item_id:
            self.item_id = str(uuid.uuid4())
        if not self.added_at:
            self.added_at = datetime.utcnow().isoformat()

    def to_dict(self) -> Dict:
        return {
            "item_id": self.item_id,
            "catalog_item": self.catalog_item.to_dict(),
            "justification": self.justification,
            "requested_for": self.requested_for,
            "requested_duration": self.requested_duration,
            "custom_end_date": self.custom_end_date,
            "added_at": self.added_at,
            "priority": self.priority,
        }


@dataclass
class SoDConflict:
    """A detected SoD conflict between cart items or with existing access."""
    conflict_id: str
    rule_id: str
    rule_name: str
    risk_level: str
    item1_role_id: str
    item1_role_name: str
    item2_role_id: str
    item2_role_name: str
    description: str
    recommendation: str = ""
    is_existing_access: bool = False  # True if conflict is with role the user already has
    can_mitigate: bool = True

    def to_dict(self) -> Dict:
        return {
            "conflict_id": self.conflict_id,
            "rule_id": self.rule_id,
            "rule_name": self.rule_name,
            "risk_level": self.risk_level,
            "item1_role_id": self.item1_role_id,
            "item1_role_name": self.item1_role_name,
            "item2_role_id": self.item2_role_id,
            "item2_role_name": self.item2_role_name,
            "description": self.description,
            "recommendation": self.recommendation,
            "is_existing_access": self.is_existing_access,
            "can_mitigate": self.can_mitigate,
        }


@dataclass
class ConflictCheckResult:
    """Result of SoD conflict checking on the cart."""
    checked_at: str = ""
    total_items: int = 0
    conflicts: List[SoDConflict] = field(default_factory=list)
    has_critical: bool = False
    has_high: bool = False
    can_submit: bool = True
    summary: str = ""

    def __post_init__(self):
        if not self.checked_at:
            self.checked_at = datetime.utcnow().isoformat()

    def to_dict(self) -> Dict:
        return {
            "checked_at": self.checked_at,
            "total_items": self.total_items,
            "conflict_count": len(self.conflicts),
            "conflicts": [c.to_dict() for c in self.conflicts],
            "has_critical": self.has_critical,
            "has_high": self.has_high,
            "can_submit": self.can_submit,
            "summary": self.summary,
        }


# ---------------------------------------------------------------------------
# Shopping Cart
# ---------------------------------------------------------------------------

class ShoppingCart:
    """
    ARM shopping cart — collects role/entitlement requests
    with real-time SoD checking and duplicate detection.
    """

    def __init__(
        self,
        cart_id: str = "",
        requester_id: str = "",
        tenant_id: str = "tenant_default",
    ):
        self.cart_id = cart_id or str(uuid.uuid4())
        self.requester_id = requester_id
        self.tenant_id = tenant_id
        self.items: Dict[str, CartItem] = {}
        self.status = CartStatus.DRAFT
        self.created_at = datetime.utcnow().isoformat()
        self.updated_at = self.created_at
        self.last_conflict_check: Optional[ConflictCheckResult] = None
        self._sod_library = SoDRulesetLibrary()

    # ------------------------------------------------------------------
    # Cart operations
    # ------------------------------------------------------------------

    def add_item(
        self,
        catalog_item: AccessCatalogItem,
        justification: str = "",
        requested_for: str = "",
        requested_duration: str = "permanent",
        custom_end_date: Optional[str] = None,
        priority: str = "normal",
        existing_roles: Optional[List[str]] = None,
    ) -> Tuple[CartItem, List[str]]:
        """
        Add an item to the cart.

        Returns (CartItem, warnings) where warnings may include
        duplicate-detection messages.

        Raises ValueError on hard duplicates.
        """
        warnings: List[str] = []

        # Duplicate detection — already in cart
        for existing in self.items.values():
            if existing.catalog_item.role_id == catalog_item.role_id:
                if existing.requested_for == (requested_for or self.requester_id):
                    raise ValueError(
                        f"Role '{catalog_item.role_name}' ({catalog_item.role_id}) "
                        f"is already in the cart for user "
                        f"'{requested_for or self.requester_id}'."
                    )

        # Duplicate detection — user already has this role
        target_user = requested_for or self.requester_id
        if existing_roles and catalog_item.role_id in existing_roles:
            warnings.append(
                f"User '{target_user}' already has role "
                f"'{catalog_item.role_name}' ({catalog_item.role_id}). "
                f"Requesting again may result in rejection."
            )

        item = CartItem(
            item_id=str(uuid.uuid4()),
            catalog_item=catalog_item,
            justification=justification,
            requested_for=target_user,
            requested_duration=requested_duration,
            custom_end_date=custom_end_date,
            priority=priority,
        )
        self.items[item.item_id] = item
        self.updated_at = datetime.utcnow().isoformat()
        self.status = CartStatus.DRAFT  # reset after modification

        logger.info(
            "Cart item added",
            extra={
                "cart_id": self.cart_id,
                "item_id": item.item_id,
                "role_id": catalog_item.role_id,
                "requested_for": target_user,
            },
        )

        return item, warnings

    def remove_item(self, item_id: str) -> bool:
        """Remove an item from the cart. Returns True if removed."""
        if item_id not in self.items:
            raise ValueError(f"Item '{item_id}' not found in cart.")
        del self.items[item_id]
        self.updated_at = datetime.utcnow().isoformat()
        self.status = CartStatus.DRAFT
        return True

    def clear(self):
        """Remove all items from the cart."""
        self.items.clear()
        self.status = CartStatus.DRAFT
        self.updated_at = datetime.utcnow().isoformat()

    # ------------------------------------------------------------------
    # SoD conflict checking
    # ------------------------------------------------------------------

    def check_conflicts(
        self,
        existing_user_roles: Optional[List[str]] = None,
    ) -> ConflictCheckResult:
        """
        Run SoD conflict analysis on all items in the cart,
        including cross-checks against the user's existing roles.

        The check compares transaction codes assigned to each role
        against the SoD ruleset's business functions to find violations.
        """
        self.status = CartStatus.CHECKING
        conflicts: List[SoDConflict] = []

        # Build a map: role_id -> set of tcodes (from cart items)
        cart_tcode_map: Dict[str, Tuple[str, List[str]]] = {}
        for item in self.items.values():
            role_id = item.catalog_item.role_id
            cart_tcode_map[role_id] = (
                item.catalog_item.role_name,
                item.catalog_item.transaction_codes,
            )

        all_rules = self._sod_library.get_all_rules(active_only=True)

        # Check cart items against each other
        role_ids = list(cart_tcode_map.keys())
        for i in range(len(role_ids)):
            for j in range(i + 1, len(role_ids)):
                rid_a, rid_b = role_ids[i], role_ids[j]
                name_a, tcodes_a = cart_tcode_map[rid_a]
                name_b, tcodes_b = cart_tcode_map[rid_b]

                for rule in all_rules:
                    f1_tcodes = set(rule.function1.transaction_codes)
                    f2_tcodes = set(rule.function2.transaction_codes)

                    overlap_a1 = set(tcodes_a) & f1_tcodes
                    overlap_b2 = set(tcodes_b) & f2_tcodes
                    overlap_a2 = set(tcodes_a) & f2_tcodes
                    overlap_b1 = set(tcodes_b) & f1_tcodes

                    if (overlap_a1 and overlap_b2) or (overlap_a2 and overlap_b1):
                        conflicts.append(SoDConflict(
                            conflict_id=str(uuid.uuid4()),
                            rule_id=rule.rule_id,
                            rule_name=rule.name,
                            risk_level=rule.risk_level.value,
                            item1_role_id=rid_a,
                            item1_role_name=name_a,
                            item2_role_id=rid_b,
                            item2_role_name=name_b,
                            description=rule.risk_description or rule.description,
                            recommendation=rule.recommendation,
                            is_existing_access=False,
                        ))

        # Check cart items against existing user roles (simulated via tcodes)
        if existing_user_roles:
            existing_tcode_map = self._resolve_existing_roles(existing_user_roles)
            for rid_cart, (name_cart, tcodes_cart) in cart_tcode_map.items():
                for rid_exist, (name_exist, tcodes_exist) in existing_tcode_map.items():
                    for rule in all_rules:
                        f1_tcodes = set(rule.function1.transaction_codes)
                        f2_tcodes = set(rule.function2.transaction_codes)

                        oc1 = set(tcodes_cart) & f1_tcodes
                        oe2 = set(tcodes_exist) & f2_tcodes
                        oc2 = set(tcodes_cart) & f2_tcodes
                        oe1 = set(tcodes_exist) & f1_tcodes

                        if (oc1 and oe2) or (oc2 and oe1):
                            conflicts.append(SoDConflict(
                                conflict_id=str(uuid.uuid4()),
                                rule_id=rule.rule_id,
                                rule_name=rule.name,
                                risk_level=rule.risk_level.value,
                                item1_role_id=rid_cart,
                                item1_role_name=name_cart,
                                item2_role_id=rid_exist,
                                item2_role_name=name_exist,
                                description=rule.risk_description or rule.description,
                                recommendation=rule.recommendation,
                                is_existing_access=True,
                            ))

        has_critical = any(c.risk_level == "critical" for c in conflicts)
        has_high = any(c.risk_level == "high" for c in conflicts)

        result = ConflictCheckResult(
            total_items=len(self.items),
            conflicts=conflicts,
            has_critical=has_critical,
            has_high=has_high,
            can_submit=not has_critical,
            summary=self._build_conflict_summary(conflicts),
        )

        self.last_conflict_check = result
        self.status = CartStatus.READY if result.can_submit else CartStatus.DRAFT
        return result

    def _resolve_existing_roles(
        self, role_ids: List[str]
    ) -> Dict[str, Tuple[str, List[str]]]:
        """
        Resolve existing role IDs to (name, tcodes) tuples.
        Uses the catalog if the role is known; otherwise returns
        empty tcodes (no conflict possible).
        """
        catalog = AccessCatalog()
        result: Dict[str, Tuple[str, List[str]]] = {}
        for rid in role_ids:
            item = catalog.get_item(rid)
            if item:
                result[rid] = (item.role_name, item.transaction_codes)
            else:
                result[rid] = (rid, [])
        return result

    @staticmethod
    def _build_conflict_summary(conflicts: List[SoDConflict]) -> str:
        if not conflicts:
            return "No SoD conflicts detected. Cart is ready for submission."
        by_level: Dict[str, int] = {}
        for c in conflicts:
            by_level[c.risk_level] = by_level.get(c.risk_level, 0) + 1
        parts = [f"{count} {level}" for level, count in sorted(by_level.items())]
        existing = sum(1 for c in conflicts if c.is_existing_access)
        msg = f"{len(conflicts)} SoD conflict(s) detected ({', '.join(parts)})."
        if existing:
            msg += f" {existing} conflict(s) with existing user access."
        return msg

    # ------------------------------------------------------------------
    # Recommendations
    # ------------------------------------------------------------------

    def get_recommendations(
        self,
        user_id: str,
        department: str,
    ) -> List[Dict]:
        """
        Suggest roles based on department and peer analysis.

        Returns a ranked list of catalog items commonly assigned to
        users in the same department that are not yet in the cart.
        """
        catalog = AccessCatalog()
        dept_roles = catalog.get_items_by_category(department)

        # Exclude items already in cart
        cart_role_ids = {item.catalog_item.role_id for item in self.items.values()}

        recommendations = []
        for item in dept_roles:
            if item.role_id in cart_role_ids:
                continue
            recommendations.append({
                "catalog_item": item.to_dict(),
                "reason": f"Commonly assigned to {department} department members",
                "peer_usage_pct": _simulated_peer_pct(item.role_id, department),
                "risk_level": item.risk_level,
            })

        # Sort: auto-approvable & low-risk first, then by peer usage
        recommendations.sort(
            key=lambda r: (
                0 if r["catalog_item"]["auto_approvable"] else 1,
                {"low": 0, "medium": 1, "high": 2, "critical": 3}.get(r["risk_level"], 4),
                -r["peer_usage_pct"],
            )
        )

        return recommendations[:10]

    # ------------------------------------------------------------------
    # Submission
    # ------------------------------------------------------------------

    def submit(self) -> Dict:
        """
        Convert the cart to one or more access requests.

        Returns a summary dict with request IDs.

        Raises ValueError if cart is empty or has critical conflicts.
        """
        if not self.items:
            raise ValueError("Cannot submit an empty cart.")

        if self.last_conflict_check and self.last_conflict_check.has_critical:
            raise ValueError(
                "Cart has critical SoD conflicts that must be resolved before submission. "
                "Remove conflicting items or provide mitigation controls."
            )

        # Group items by requested_for user (one request per target user)
        by_user: Dict[str, List[CartItem]] = {}
        for item in self.items.values():
            target = item.requested_for or self.requester_id
            by_user.setdefault(target, []).append(item)

        requests_created = []
        for target_user, items in by_user.items():
            request_id = f"AR-{uuid.uuid4().hex[:8].upper()}"
            requests_created.append({
                "request_id": request_id,
                "requested_for": target_user,
                "requested_by": self.requester_id,
                "item_count": len(items),
                "items": [
                    {
                        "role_id": it.catalog_item.role_id,
                        "role_name": it.catalog_item.role_name,
                        "system": it.catalog_item.system,
                        "justification": it.justification,
                        "duration": it.requested_duration,
                        "priority": it.priority,
                    }
                    for it in items
                ],
                "conflict_count": (
                    len(self.last_conflict_check.conflicts)
                    if self.last_conflict_check else 0
                ),
                "submitted_at": datetime.utcnow().isoformat(),
            })

        self.status = CartStatus.SUBMITTED
        self.updated_at = datetime.utcnow().isoformat()

        logger.info(
            "Cart submitted",
            extra={
                "cart_id": self.cart_id,
                "request_count": len(requests_created),
                "total_items": len(self.items),
            },
        )

        return {
            "cart_id": self.cart_id,
            "status": self.status.value,
            "requests": requests_created,
            "submitted_at": self.updated_at,
        }

    # ------------------------------------------------------------------
    # Approval time estimation
    # ------------------------------------------------------------------

    def estimate_approval_time(self) -> Dict:
        """
        Predict how long approval will take based on item risk levels,
        conflict state, and historical averages.
        """
        if not self.items:
            return {"estimated_hours": 0, "breakdown": [], "notes": []}

        breakdown = []
        notes: List[str] = []
        total_hours = 0.0

        # Base hours by risk level
        risk_hours = {"low": 4, "medium": 12, "high": 24, "critical": 48}

        for item in self.items.values():
            risk = item.catalog_item.risk_level
            base = risk_hours.get(risk, 24)

            # Auto-approvable items are fast
            if item.catalog_item.auto_approvable and risk == "low":
                hours = 1.0
            else:
                hours = float(base)

            # Temporary requests are faster
            if item.requested_duration != "permanent":
                hours *= 0.75

            breakdown.append({
                "role_id": item.catalog_item.role_id,
                "role_name": item.catalog_item.role_name,
                "risk_level": risk,
                "estimated_hours": round(hours, 1),
            })
            total_hours = max(total_hours, hours)  # parallel approval = max

        # SoD conflicts add delay
        if self.last_conflict_check and self.last_conflict_check.conflicts:
            conflict_penalty = len(self.last_conflict_check.conflicts) * 8
            total_hours += conflict_penalty
            notes.append(
                f"Added {conflict_penalty}h for "
                f"{len(self.last_conflict_check.conflicts)} SoD conflict(s) "
                f"requiring additional review."
            )

        # Multiple items may slow things slightly
        if len(self.items) > 3:
            total_hours += 4
            notes.append("Added 4h for bulk request review (>3 items).")

        return {
            "estimated_hours": round(total_hours, 1),
            "estimated_business_days": round(total_hours / 8, 1),
            "breakdown": breakdown,
            "notes": notes,
        }

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> Dict:
        return {
            "cart_id": self.cart_id,
            "requester_id": self.requester_id,
            "tenant_id": self.tenant_id,
            "status": self.status.value,
            "item_count": len(self.items),
            "items": [item.to_dict() for item in self.items.values()],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "last_conflict_check": (
                self.last_conflict_check.to_dict()
                if self.last_conflict_check else None
            ),
        }


# ---------------------------------------------------------------------------
# Access Catalog
# ---------------------------------------------------------------------------

class AccessCatalog:
    """
    Browsable catalog of available roles and entitlements.

    In production this would query SAP systems and a role repository.
    Here we provide a comprehensive set of realistic SAP roles.
    """

    def __init__(self):
        self._items: Dict[str, AccessCatalogItem] = {}
        self._init_catalog()

    def _init_catalog(self):
        """Populate catalog with realistic SAP roles."""
        items = [
            # ==================== FINANCE ====================
            AccessCatalogItem(
                role_id="SAP_FI_AP_CLERK",
                role_name="AP Clerk",
                system="SAP ECC",
                description="Accounts Payable clerk — process vendor invoices, post payments, manage aging reports",
                risk_level="medium",
                category="Finance",
                auto_approvable=False,
                owner="FI Team Lead",
                transaction_codes=["FB60", "FB65", "F110", "FBL1N", "MIRO"],
                business_process="FI",
                tags=["accounts-payable", "invoicing"],
            ),
            AccessCatalogItem(
                role_id="SAP_FI_AR_CLERK",
                role_name="AR Clerk",
                system="SAP ECC",
                description="Accounts Receivable clerk — manage customer invoices, incoming payments, dunning",
                risk_level="medium",
                category="Finance",
                auto_approvable=False,
                owner="FI Team Lead",
                transaction_codes=["FB70", "FB75", "F-28", "FBL5N", "F150"],
                business_process="FI",
                tags=["accounts-receivable", "collections"],
            ),
            AccessCatalogItem(
                role_id="SAP_FI_GL_ACCOUNTANT",
                role_name="GL Accountant",
                system="SAP ECC",
                description="General Ledger accountant — journal entries, period close, financial statements",
                risk_level="high",
                category="Finance",
                auto_approvable=False,
                owner="Controller",
                transaction_codes=["FB50", "FB01", "F-02", "FAGL_FC_VAL", "S_ALR_87012284"],
                business_process="FI",
                tags=["general-ledger", "period-close"],
            ),
            AccessCatalogItem(
                role_id="SAP_FI_ASSET_ACCT",
                role_name="Asset Accountant",
                system="SAP ECC",
                description="Fixed asset accounting — acquisitions, retirements, depreciation runs",
                risk_level="medium",
                category="Finance",
                auto_approvable=False,
                owner="Controller",
                transaction_codes=["AS01", "AS02", "ABAVN", "AFAB", "AW01N"],
                business_process="FI",
                tags=["fixed-assets", "depreciation"],
            ),
            AccessCatalogItem(
                role_id="SAP_FI_VENDOR_MASTER",
                role_name="Vendor Master Data Manager",
                system="SAP ECC",
                description="Create and maintain vendor master records, manage bank details",
                risk_level="high",
                category="Finance",
                auto_approvable=False,
                owner="Master Data Lead",
                transaction_codes=["FK01", "FK02", "FK03", "XK01", "XK02", "XK03"],
                business_process="FI",
                tags=["vendor-master", "master-data"],
            ),

            # ==================== PROCUREMENT ====================
            AccessCatalogItem(
                role_id="SAP_MM_BUYER",
                role_name="Buyer / Purchaser",
                system="SAP ECC",
                description="Create purchase orders, manage sourcing, negotiate with vendors",
                risk_level="medium",
                category="Procurement",
                auto_approvable=False,
                owner="Procurement Lead",
                transaction_codes=["ME21N", "ME22N", "ME23N", "ME2M", "ME2N"],
                business_process="MM",
                tags=["purchasing", "sourcing"],
            ),
            AccessCatalogItem(
                role_id="SAP_MM_REQ_CREATOR",
                role_name="Purchase Requisition Creator",
                system="SAP ECC",
                description="Create and manage purchase requisitions for goods and services",
                risk_level="low",
                category="Procurement",
                auto_approvable=True,
                owner="Procurement Lead",
                transaction_codes=["ME51N", "ME52N", "ME53N", "ME5A"],
                business_process="MM",
                tags=["requisition", "self-service"],
            ),
            AccessCatalogItem(
                role_id="SAP_MM_GR_PROCESSOR",
                role_name="Goods Receipt Processor",
                system="SAP ECC",
                description="Post goods receipts against purchase orders, manage receiving dock",
                risk_level="medium",
                category="Procurement",
                auto_approvable=False,
                owner="Warehouse Lead",
                transaction_codes=["MIGO", "MB01", "MB0A", "MB1C"],
                business_process="MM",
                tags=["goods-receipt", "receiving"],
            ),
            AccessCatalogItem(
                role_id="SAP_MM_INVOICE_VERIFY",
                role_name="Invoice Verification Clerk",
                system="SAP ECC",
                description="Verify and post vendor invoices against purchase orders (3-way match)",
                risk_level="medium",
                category="Procurement",
                auto_approvable=False,
                owner="AP Supervisor",
                transaction_codes=["MIRO", "MIR4", "MIR7", "MRBR"],
                business_process="MM",
                tags=["invoice-verification", "3-way-match"],
            ),
            AccessCatalogItem(
                role_id="SAP_MM_MATERIAL_MASTER",
                role_name="Material Master Data Manager",
                system="SAP ECC",
                description="Create and maintain material master records across all views",
                risk_level="medium",
                category="Procurement",
                auto_approvable=False,
                owner="Master Data Lead",
                transaction_codes=["MM01", "MM02", "MM03", "MM60"],
                business_process="MM",
                tags=["material-master", "master-data"],
            ),

            # ==================== SALES ====================
            AccessCatalogItem(
                role_id="SAP_SD_ORDER_MGMT",
                role_name="Sales Order Manager",
                system="SAP ECC",
                description="Create, modify, and manage sales orders and contracts",
                risk_level="medium",
                category="Sales",
                auto_approvable=False,
                owner="Sales Operations Lead",
                transaction_codes=["VA01", "VA02", "VA03", "VA05", "VA21"],
                business_process="SD",
                tags=["sales-order", "order-management"],
            ),
            AccessCatalogItem(
                role_id="SAP_SD_BILLING",
                role_name="Billing Clerk",
                system="SAP ECC",
                description="Create billing documents, process credit/debit memos, manage revenue",
                risk_level="high",
                category="Sales",
                auto_approvable=False,
                owner="Revenue Manager",
                transaction_codes=["VF01", "VF02", "VF03", "VF04", "VF11"],
                business_process="SD",
                tags=["billing", "revenue"],
            ),
            AccessCatalogItem(
                role_id="SAP_SD_DELIVERY",
                role_name="Delivery Processor",
                system="SAP ECC",
                description="Create outbound deliveries, post goods issues for shipments",
                risk_level="low",
                category="Sales",
                auto_approvable=True,
                owner="Logistics Lead",
                transaction_codes=["VL01N", "VL02N", "VL03N", "VL06O"],
                business_process="SD",
                tags=["delivery", "shipping"],
            ),
            AccessCatalogItem(
                role_id="SAP_SD_CUSTOMER_MASTER",
                role_name="Customer Master Data Manager",
                system="SAP ECC",
                description="Create and maintain customer master records and credit limits",
                risk_level="high",
                category="Sales",
                auto_approvable=False,
                owner="Master Data Lead",
                transaction_codes=["XD01", "XD02", "XD03", "FD32"],
                business_process="SD",
                tags=["customer-master", "master-data", "credit"],
            ),

            # ==================== HR ====================
            AccessCatalogItem(
                role_id="SAP_HR_PA_ADMIN",
                role_name="Personnel Administrator",
                system="SAP HCM",
                description="Maintain employee master data — hiring, transfers, terminations",
                risk_level="high",
                category="Human Resources",
                auto_approvable=False,
                owner="HR Manager",
                transaction_codes=["PA20", "PA30", "PA40", "PA61", "PA71"],
                business_process="HR",
                tags=["personnel", "employee-lifecycle"],
            ),
            AccessCatalogItem(
                role_id="SAP_HR_PAYROLL",
                role_name="Payroll Administrator",
                system="SAP HCM",
                description="Run payroll, manage wage types, post payroll results to FI",
                risk_level="critical",
                category="Human Resources",
                auto_approvable=False,
                owner="Payroll Manager",
                transaction_codes=["PC00_M99_CALC", "PC00_M99_CUST", "PU19", "PA03"],
                business_process="HR",
                tags=["payroll", "compensation"],
            ),
            AccessCatalogItem(
                role_id="SAP_HR_TIME_ADMIN",
                role_name="Time Administrator",
                system="SAP HCM",
                description="Manage time recording, attendance, leave quotas",
                risk_level="low",
                category="Human Resources",
                auto_approvable=True,
                owner="HR Manager",
                transaction_codes=["PA61", "PA62", "PTMW", "CAT2"],
                business_process="HR",
                tags=["time-management", "attendance"],
            ),
            AccessCatalogItem(
                role_id="SAP_HR_OM_ADMIN",
                role_name="Org Management Administrator",
                system="SAP HCM",
                description="Maintain organizational structure, positions, and reporting lines",
                risk_level="medium",
                category="Human Resources",
                auto_approvable=False,
                owner="HR Manager",
                transaction_codes=["PPOME", "PO10", "PO13", "PPOSE"],
                business_process="HR",
                tags=["org-management", "structure"],
            ),

            # ==================== IT / BASIS ====================
            AccessCatalogItem(
                role_id="SAP_BASIS_USER_ADMIN",
                role_name="User Administrator",
                system="SAP ECC",
                description="Create, lock/unlock, and manage SAP user accounts and authorizations",
                risk_level="critical",
                category="IT Administration",
                auto_approvable=False,
                owner="IT Security Lead",
                transaction_codes=["SU01", "SU02", "SU10", "PFCG", "SU53"],
                business_process="BASIS",
                tags=["user-admin", "security"],
            ),
            AccessCatalogItem(
                role_id="SAP_BASIS_ROLE_ADMIN",
                role_name="Role Administrator",
                system="SAP ECC",
                description="Create and modify authorization roles and profiles",
                risk_level="critical",
                category="IT Administration",
                auto_approvable=False,
                owner="IT Security Lead",
                transaction_codes=["PFCG", "SU02", "AGR_1016", "SU24"],
                business_process="BASIS",
                tags=["role-admin", "authorization"],
            ),
            AccessCatalogItem(
                role_id="SAP_BASIS_TRANSPORT",
                role_name="Transport Administrator",
                system="SAP ECC",
                description="Manage transport requests — create, release, import across systems",
                risk_level="high",
                category="IT Administration",
                auto_approvable=False,
                owner="Basis Lead",
                transaction_codes=["SE01", "SE09", "SE10", "STMS"],
                business_process="BASIS",
                tags=["transport", "change-management"],
            ),
            AccessCatalogItem(
                role_id="SAP_IT_DISPLAY_ONLY",
                role_name="IT Display Access",
                system="SAP ECC",
                description="Read-only access to system monitoring, logs, and configuration",
                risk_level="low",
                category="IT Administration",
                auto_approvable=True,
                owner="IT Security Lead",
                transaction_codes=["SM21", "SM37", "SM50", "ST22", "SU53"],
                business_process="BASIS",
                sap_role_type="composite",
                tags=["display", "monitoring", "read-only"],
            ),

            # ==================== CROSS-FUNCTIONAL / WAREHOUSE ====================
            AccessCatalogItem(
                role_id="SAP_WM_OPERATOR",
                role_name="Warehouse Operator",
                system="SAP ECC",
                description="Execute warehouse movements, stock transfers, physical inventory",
                risk_level="low",
                category="Warehouse",
                auto_approvable=True,
                owner="Warehouse Lead",
                transaction_codes=["LT01", "LT0E", "LS01N", "MI01"],
                business_process="WM",
                tags=["warehouse", "inventory"],
            ),
            AccessCatalogItem(
                role_id="SAP_QM_INSPECTOR",
                role_name="Quality Inspector",
                system="SAP ECC",
                description="Record quality inspection results, manage usage decisions",
                risk_level="low",
                category="Quality Management",
                auto_approvable=True,
                owner="Quality Lead",
                transaction_codes=["QA32", "QE51N", "QA11", "QA12"],
                business_process="QM",
                tags=["quality", "inspection"],
            ),
            AccessCatalogItem(
                role_id="SAP_PM_TECHNICIAN",
                role_name="Maintenance Technician",
                system="SAP ECC",
                description="Create and confirm maintenance orders, manage work center tasks",
                risk_level="low",
                category="Plant Maintenance",
                auto_approvable=True,
                owner="Maintenance Lead",
                transaction_codes=["IW31", "IW32", "IW41", "IW38"],
                business_process="PM",
                tags=["maintenance", "work-orders"],
            ),
        ]

        for item in items:
            self._items[item.role_id] = item

    # ------------------------------------------------------------------
    # Catalog queries
    # ------------------------------------------------------------------

    def get_all(self) -> List[AccessCatalogItem]:
        return list(self._items.values())

    def get_item(self, role_id: str) -> Optional[AccessCatalogItem]:
        return self._items.get(role_id)

    def search(self, query: str) -> List[AccessCatalogItem]:
        """Full-text search across name, description, tags, tcodes."""
        q = query.lower()
        results = []
        for item in self._items.values():
            searchable = " ".join([
                item.role_id.lower(),
                item.role_name.lower(),
                item.description.lower(),
                item.system.lower(),
                item.category.lower(),
                " ".join(item.tags),
                " ".join(item.transaction_codes).lower(),
            ])
            if q in searchable:
                results.append(item)
        return results

    def get_items_by_category(self, category: str) -> List[AccessCatalogItem]:
        """Filter catalog by category (case-insensitive partial match)."""
        cat = category.lower()
        return [
            item for item in self._items.values()
            if cat in item.category.lower()
        ]

    def get_items_by_system(self, system: str) -> List[AccessCatalogItem]:
        sys_lower = system.lower()
        return [
            item for item in self._items.values()
            if sys_lower in item.system.lower()
        ]

    def get_items_by_risk_level(self, risk_level: str) -> List[AccessCatalogItem]:
        return [
            item for item in self._items.values()
            if item.risk_level == risk_level.lower()
        ]

    def filter_items(
        self,
        system: Optional[str] = None,
        category: Optional[str] = None,
        risk_level: Optional[str] = None,
        auto_approvable: Optional[bool] = None,
        business_process: Optional[str] = None,
    ) -> List[AccessCatalogItem]:
        """Multi-criteria filter."""
        results = list(self._items.values())

        if system:
            s = system.lower()
            results = [i for i in results if s in i.system.lower()]
        if category:
            c = category.lower()
            results = [i for i in results if c in i.category.lower()]
        if risk_level:
            results = [i for i in results if i.risk_level == risk_level.lower()]
        if auto_approvable is not None:
            results = [i for i in results if i.auto_approvable == auto_approvable]
        if business_process:
            bp = business_process.upper()
            results = [i for i in results if i.business_process.upper() == bp]

        return results


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _simulated_peer_pct(role_id: str, department: str) -> float:
    """
    Simulated peer-usage percentage.
    In production this would query historical assignment data.
    """
    # Deterministic pseudo-random based on inputs
    h = hash(f"{role_id}:{department}") % 100
    return round(h / 100.0 * 80 + 20, 1)  # 20-100%
