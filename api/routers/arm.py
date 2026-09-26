# ARM (Access Request Management) — Shopping Cart API
# SAP GRC-style role request workflow with SoD conflict checking

from fastapi import APIRouter, HTTPException, Query, Header, Depends
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
from datetime import datetime
import json

from sqlalchemy.orm import Session

from core.arm.shopping_cart import (
    AccessCatalog,
    AccessCatalogItem,
    CartItem,
    ShoppingCart,
    CartStatus,
)
from db.database import get_db
from db.models.operations import ShoppingCartModel

router = APIRouter(prefix="/arm", tags=["ARM - Shopping Cart"])

# ---------------------------------------------------------------------------
# Module-level singletons
# ---------------------------------------------------------------------------
_catalog = AccessCatalog()

# In-memory write-through cache: cart_id -> ShoppingCart
# Populated on first access; authoritative store is the DB.
_carts: Dict[str, ShoppingCart] = {}


def _get_tenant_id(
    x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID"),
) -> str:
    return x_tenant_id or "tenant_default"


# ---------------------------------------------------------------------------
# Serialization helpers
# ---------------------------------------------------------------------------

def _cart_status_to_db(status: CartStatus) -> str:
    """Map CartStatus enum to the coarse DB status string."""
    if status == CartStatus.SUBMITTED:
        return "submitted"
    if status == CartStatus.CANCELLED:
        return "cancelled"
    return "open"


def _catalog_item_from_dict(d: Dict) -> AccessCatalogItem:
    """
    Reconstruct an AccessCatalogItem from its to_dict() representation.

    Tries the live catalog first (cheaper); falls back to rebuilding from
    the persisted dict so the cart works even if the catalog changes.
    """
    item = _catalog.get_item(d["role_id"])
    if item:
        return item
    return AccessCatalogItem(
        role_id=d["role_id"],
        role_name=d["role_name"],
        system=d.get("system", ""),
        description=d.get("description", ""),
        risk_level=d.get("risk_level", "low"),
        category=d.get("category", ""),
        auto_approvable=d.get("auto_approvable", False),
        owner=d.get("owner", ""),
        transaction_codes=d.get("transaction_codes", []),
        business_process=d.get("business_process", ""),
        sap_role_type=d.get("sap_role_type", "single"),
        requires_justification=d.get("requires_justification", True),
        max_duration=d.get("max_duration", "permanent"),
        tags=d.get("tags", []),
    )


def _cart_item_from_dict(d: Dict) -> CartItem:
    """Reconstruct a CartItem from its to_dict() representation."""
    catalog_item = _catalog_item_from_dict(d["catalog_item"])
    return CartItem(
        item_id=d["item_id"],
        catalog_item=catalog_item,
        justification=d.get("justification", ""),
        requested_for=d.get("requested_for", ""),
        requested_duration=d.get("requested_duration", "permanent"),
        custom_end_date=d.get("custom_end_date"),
        added_at=d.get("added_at", ""),
        priority=d.get("priority", "normal"),
    )


def _cart_from_db(row: ShoppingCartModel) -> ShoppingCart:
    """
    Reconstruct a ShoppingCart from a ShoppingCartModel DB row.

    Creates the ShoppingCart with the original cart_id so IDs remain
    stable across restarts.
    """
    cart = ShoppingCart(
        cart_id=row.id,
        requester_id=row.requester_id,
        tenant_id=row.tenant_id,
    )
    # Restore timestamps
    cart.created_at = row.cart_created_at or cart.created_at
    cart.updated_at = row.cart_updated_at or cart.updated_at

    # Restore items
    try:
        items_data: List[Dict] = json.loads(row.items_json or "[]")
    except (json.JSONDecodeError, TypeError):
        items_data = []

    for item_dict in items_data:
        try:
            item = _cart_item_from_dict(item_dict)
            cart.items[item.item_id] = item
        except Exception:
            # Skip corrupted item entries rather than failing the whole cart
            pass

    # Restore status
    if row.status == "submitted":
        cart.status = CartStatus.SUBMITTED
    elif row.status == "cancelled":
        cart.status = CartStatus.CANCELLED
    else:
        cart.status = CartStatus.DRAFT

    return cart


def _persist_cart(cart: ShoppingCart, db: Session) -> None:
    """
    Write (INSERT or UPDATE) a ShoppingCart to the database.

    Serialises all cart items into the items_json column.
    """
    items_data = [item.to_dict() for item in cart.items.values()]
    items_json = json.dumps(items_data)
    db_status = _cart_status_to_db(cart.status)

    row = db.get(ShoppingCartModel, cart.cart_id)
    if row is None:
        row = ShoppingCartModel(
            id=cart.cart_id,
            requester_id=cart.requester_id,
            tenant_id=cart.tenant_id,
            status=db_status,
            items_json=items_json,
            cart_created_at=cart.created_at,
            cart_updated_at=cart.updated_at,
        )
        db.add(row)
    else:
        row.requester_id = cart.requester_id
        row.tenant_id = cart.tenant_id
        row.status = db_status
        row.items_json = items_json
        row.cart_updated_at = cart.updated_at

    db.commit()


# ---------------------------------------------------------------------------
# Cart lookup — cache-first, fall back to DB
# ---------------------------------------------------------------------------

def _load_cart(cart_id: str, db: Session) -> ShoppingCart:
    """
    Return the ShoppingCart for cart_id.

    Checks the in-process memory cache first; on a miss queries the DB
    and repopulates the cache.  Raises 404 if not found in either.
    """
    if cart_id in _carts:
        return _carts[cart_id]

    row = db.get(ShoppingCartModel, cart_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"Cart '{cart_id}' not found.")

    cart = _cart_from_db(row)
    _carts[cart_id] = cart
    return cart


# ---------------------------------------------------------------------------
# Pydantic request / response models
# ---------------------------------------------------------------------------

class AddItemRequest(BaseModel):
    role_id: str
    justification: str = ""
    requested_for: str = ""
    requested_duration: str = "permanent"
    custom_end_date: Optional[str] = None
    priority: str = "normal"
    existing_roles: List[str] = []


class CreateCartRequest(BaseModel):
    requester_id: str = ""


class ConflictCheckRequest(BaseModel):
    existing_user_roles: List[str] = []


class SubmitCartRequest(BaseModel):
    """Optional body — kept for future fields like comments."""
    comments: str = ""


# ---------------------------------------------------------------------------
# Catalog endpoints
# ---------------------------------------------------------------------------

@router.get("/catalog")
async def browse_catalog(
    system: Optional[str] = Query(None, description="Filter by system (e.g. 'SAP ECC')"),
    category: Optional[str] = Query(None, description="Filter by category (e.g. 'Finance')"),
    risk_level: Optional[str] = Query(None, description="Filter by risk level (low/medium/high/critical)"),
    auto_approvable: Optional[bool] = Query(None, description="Filter by auto-approvable flag"),
    business_process: Optional[str] = Query(None, description="Filter by SAP process (FI, MM, SD, HR, BASIS, ...)"),
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
):
    """
    Browse the access catalog.

    Returns available roles/entitlements with optional filtering by
    system, category, risk level, business process, or auto-approvable flag.
    """
    items = _catalog.filter_items(
        system=system,
        category=category,
        risk_level=risk_level,
        auto_approvable=auto_approvable,
        business_process=business_process,
    )

    total = len(items)
    page = items[offset: offset + limit]

    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "items": [item.to_dict() for item in page],
        "filters_applied": {
            k: v for k, v in {
                "system": system,
                "category": category,
                "risk_level": risk_level,
                "auto_approvable": auto_approvable,
                "business_process": business_process,
            }.items() if v is not None
        },
    }


@router.get("/catalog/search")
async def search_catalog(
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(default=20, le=100),
):
    """
    Search the access catalog by keyword.

    Searches across role name, description, tags, and transaction codes.
    """
    results = _catalog.search(q)
    return {
        "query": q,
        "total": len(results),
        "items": [item.to_dict() for item in results[:limit]],
    }


@router.get("/catalog/{role_id}")
async def get_catalog_item(role_id: str):
    """Get a single catalog item by role ID."""
    item = _catalog.get_item(role_id)
    if not item:
        raise HTTPException(status_code=404, detail=f"Catalog item '{role_id}' not found.")
    return item.to_dict()


# ---------------------------------------------------------------------------
# Cart lifecycle endpoints
# ---------------------------------------------------------------------------

@router.post("/cart")
async def create_cart(
    body: CreateCartRequest,
    x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID"),
    db: Session = Depends(get_db),
):
    """
    Create a new shopping cart session.

    Returns the cart ID used for all subsequent operations.
    The cart is persisted to the database immediately on creation.
    """
    tenant_id = x_tenant_id or "tenant_default"
    cart = ShoppingCart(
        requester_id=body.requester_id or "anonymous",
        tenant_id=tenant_id,
    )
    # Persist to DB
    _persist_cart(cart, db)
    # Populate memory cache
    _carts[cart.cart_id] = cart
    return cart.to_dict()


@router.get("/cart/{cart_id}")
async def get_cart(cart_id: str, db: Session = Depends(get_db)):
    """Get cart status and contents."""
    cart = _load_cart(cart_id, db)
    result = cart.to_dict()
    result["approval_estimate"] = cart.estimate_approval_time()
    return result


@router.delete("/cart/{cart_id}")
async def cancel_cart(cart_id: str, db: Session = Depends(get_db)):
    """Cancel / delete a cart."""
    cart = _load_cart(cart_id, db)

    if cart.status == CartStatus.SUBMITTED:
        raise HTTPException(
            status_code=400,
            detail="Cannot cancel a cart that has already been submitted.",
        )

    # Update DB row status to cancelled
    row = db.get(ShoppingCartModel, cart_id)
    if row is not None:
        row.status = "cancelled"
        db.commit()

    # Remove from in-memory cache
    _carts.pop(cart_id, None)

    return {"message": f"Cart '{cart_id}' cancelled and removed."}


# ---------------------------------------------------------------------------
# Cart item endpoints
# ---------------------------------------------------------------------------

@router.post("/cart/{cart_id}/items")
async def add_item_to_cart(
    cart_id: str,
    body: AddItemRequest,
    db: Session = Depends(get_db),
):
    """
    Add a role/entitlement to the shopping cart.

    Performs duplicate detection against:
    - Items already in the cart
    - Roles the user already has (if existing_roles provided)

    Returns the added item and any warnings.
    The cart is persisted to the database after each modification.
    """
    cart = _load_cart(cart_id, db)

    if cart.status == CartStatus.SUBMITTED:
        raise HTTPException(status_code=400, detail="Cart has already been submitted.")

    # Resolve catalog item
    catalog_item = _catalog.get_item(body.role_id)
    if not catalog_item:
        raise HTTPException(
            status_code=404,
            detail=f"Role '{body.role_id}' not found in catalog.",
        )

    try:
        item, warnings = cart.add_item(
            catalog_item=catalog_item,
            justification=body.justification,
            requested_for=body.requested_for,
            requested_duration=body.requested_duration,
            custom_end_date=body.custom_end_date,
            priority=body.priority,
            existing_roles=body.existing_roles if body.existing_roles else None,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))

    # Persist updated cart to DB
    _persist_cart(cart, db)

    return {
        "item": item.to_dict(),
        "warnings": warnings,
        "cart_item_count": len(cart.items),
    }


@router.delete("/cart/{cart_id}/items/{item_id}")
async def remove_item_from_cart(
    cart_id: str,
    item_id: str,
    db: Session = Depends(get_db),
):
    """Remove an item from the cart."""
    cart = _load_cart(cart_id, db)

    if cart.status == CartStatus.SUBMITTED:
        raise HTTPException(status_code=400, detail="Cart has already been submitted.")

    try:
        cart.remove_item(item_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    # Persist updated cart to DB
    _persist_cart(cart, db)

    return {
        "message": f"Item '{item_id}' removed.",
        "cart_item_count": len(cart.items),
    }


# ---------------------------------------------------------------------------
# SoD conflict checking
# ---------------------------------------------------------------------------

@router.post("/cart/{cart_id}/check-conflicts")
async def check_conflicts(
    cart_id: str,
    body: ConflictCheckRequest,
    db: Session = Depends(get_db),
):
    """
    Run SoD conflict analysis on the cart.

    Checks all items against each other and optionally against the
    user's existing roles. Returns conflict details and whether the
    cart can be submitted.
    """
    cart = _load_cart(cart_id, db)

    if not cart.items:
        raise HTTPException(status_code=400, detail="Cart is empty — nothing to check.")

    result = cart.check_conflicts(
        existing_user_roles=body.existing_user_roles if body.existing_user_roles else None,
    )

    # Persist status change (CHECKING -> READY or back to DRAFT)
    _persist_cart(cart, db)

    return result.to_dict()


# ---------------------------------------------------------------------------
# Recommendations
# ---------------------------------------------------------------------------

@router.get("/cart/{cart_id}/recommendations")
async def get_recommendations(
    cart_id: str,
    user_id: str = Query("", description="User to get recommendations for"),
    department: str = Query("", description="Department for peer-based suggestions"),
    db: Session = Depends(get_db),
):
    """
    Get role recommendations based on department and peer analysis.

    Returns roles commonly assigned to users in the same department
    that are not yet in the cart.
    """
    cart = _load_cart(cart_id, db)

    if not department:
        return {
            "recommendations": [],
            "message": "Provide a 'department' query parameter for peer-based recommendations.",
        }

    recommendations = cart.get_recommendations(
        user_id=user_id or cart.requester_id,
        department=department,
    )

    return {
        "user_id": user_id or cart.requester_id,
        "department": department,
        "recommendation_count": len(recommendations),
        "recommendations": recommendations,
    }


# ---------------------------------------------------------------------------
# Submission
# ---------------------------------------------------------------------------

@router.post("/cart/{cart_id}/submit")
async def submit_cart(
    cart_id: str,
    body: SubmitCartRequest = SubmitCartRequest(),
    db: Session = Depends(get_db),
):
    """
    Submit the cart as access request(s).

    Creates one access request per target user. Fails if the cart
    is empty or has unresolved critical SoD conflicts.
    The cart status is updated to 'submitted' in the database.
    """
    cart = _load_cart(cart_id, db)

    if cart.status == CartStatus.SUBMITTED:
        raise HTTPException(status_code=400, detail="Cart has already been submitted.")

    try:
        result = cart.submit()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    # Persist submitted status to DB
    _persist_cart(cart, db)

    return result


# ---------------------------------------------------------------------------
# Approval time estimate (standalone)
# ---------------------------------------------------------------------------

@router.get("/cart/{cart_id}/estimate")
async def estimate_approval_time(cart_id: str, db: Session = Depends(get_db)):
    """
    Predict how long approval will take for the current cart contents.
    """
    cart = _load_cart(cart_id, db)
    return cart.estimate_approval_time()
