"""
Org Hierarchy API Router

Manages the hierarchical organisational unit structure shared across all
GRC modules (XI-01, RM-02, PC-02).

Direct DB queries — no manager class needed.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
import uuid

from db.database import get_db
from db.models.grc_foundation import OrgUnit, OrgUnitType

router = APIRouter(tags=["Org Hierarchy"])


# ---------------------------------------------------------------------------
# Tenant helpers
# ---------------------------------------------------------------------------

def _get_tenant_id() -> str:
    from core.tenant import get_current_tenant
    ctx = get_current_tenant()
    return ctx.tenant_id if ctx else "default"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _new_id(prefix: str = "OU") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


def _unit_or_404(db: Session, unit_id: str, tenant_id: str) -> OrgUnit:
    unit = db.query(OrgUnit).filter(
        OrgUnit.unit_id == unit_id,
        OrgUnit.tenant_id == tenant_id,
        OrgUnit.is_active.is_(True),
    ).first()
    if not unit:
        raise HTTPException(status_code=404, detail=f"Org unit '{unit_id}' not found")
    return unit


def _compute_level_and_path(db: Session, parent_pk: Optional[int]) -> tuple:
    """Return (level, path_string) for a new child unit."""
    if parent_pk is None:
        return 0, None
    parent = db.query(OrgUnit).filter(OrgUnit.id == parent_pk).first()
    if not parent:
        return 0, None
    parent_path = parent.path or str(parent.id)
    return parent.level + 1, f"{parent_path}/{parent.id}"


def _unit_to_dict(unit: OrgUnit) -> Dict[str, Any]:
    return unit.to_dict()


def _build_tree(units: List[OrgUnit]) -> List[Dict[str, Any]]:
    """Recursively assemble a nested tree structure from a flat list of OrgUnits."""
    by_pk: Dict[int, Dict[str, Any]] = {}
    for u in units:
        d = _unit_to_dict(u)
        d["children"] = []
        by_pk[u.id] = d

    roots: List[Dict[str, Any]] = []
    for u in units:
        if u.parent_id and u.parent_id in by_pk:
            by_pk[u.parent_id]["children"].append(by_pk[u.id])
        elif not u.parent_id:
            roots.append(by_pk[u.id])

    return roots


# ===========================================================================
# Endpoints
# ===========================================================================

@router.post("/units", status_code=201)
def create_org_unit(
    body: Dict[str, Any] = Body(default={}),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Create a new organisational unit."""
    try:
        unit_type = OrgUnitType(body.get("unit_type", "department"))
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid unit_type. Valid values: {[e.value for e in OrgUnitType]}",
        )

    # Resolve parent by unit_id string if provided
    parent_pk: Optional[int] = None
    if body.get("parent_unit_id"):
        parent = db.query(OrgUnit).filter(
            OrgUnit.unit_id == body["parent_unit_id"],
            OrgUnit.tenant_id == tenant_id,
        ).first()
        if not parent:
            raise HTTPException(status_code=404, detail=f"Parent unit '{body['parent_unit_id']}' not found")
        parent_pk = parent.id
    elif body.get("parent_id"):
        # Also accept raw integer PK for internal use
        parent_pk = body["parent_id"]

    level, path = _compute_level_and_path(db, parent_pk)

    unit = OrgUnit(
        tenant_id=tenant_id,
        unit_id=body.get("unit_id") or _new_id(),
        name=body["name"],
        unit_type=unit_type,
        parent_id=parent_pk,
        level=level,
        path=path,
        manager_user_id=body.get("manager_user_id"),
        country=body.get("country"),
        region=body.get("region"),
        is_active=True,
        metadata_=body.get("metadata"),
    )
    db.add(unit)
    db.commit()
    db.refresh(unit)
    return unit.to_dict()


@router.get("/units")
def list_org_units(
    parent_id: Optional[str] = Query(None, description="Filter by parent unit_id"),
    unit_type: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """List org units with optional filters."""
    q = db.query(OrgUnit).filter(OrgUnit.tenant_id == tenant_id)

    if parent_id is not None:
        # Resolve the parent unit_id string to its PK
        parent = db.query(OrgUnit).filter(
            OrgUnit.unit_id == parent_id,
            OrgUnit.tenant_id == tenant_id,
        ).first()
        parent_pk = parent.id if parent else -1
        q = q.filter(OrgUnit.parent_id == parent_pk)

    if unit_type:
        try:
            q = q.filter(OrgUnit.unit_type == OrgUnitType(unit_type))
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid unit_type: {unit_type}")

    if is_active is not None:
        q = q.filter(OrgUnit.is_active == is_active)
    else:
        q = q.filter(OrgUnit.is_active.is_(True))

    if search:
        q = q.filter(OrgUnit.name.ilike(f"%{search}%"))

    units = q.order_by(OrgUnit.level, OrgUnit.name).all()
    return {"total": len(units), "units": [u.to_dict() for u in units]}


@router.get("/units/{unit_id}")
def get_org_unit(
    unit_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Get an org unit with its immediate children."""
    unit = _unit_or_404(db, unit_id, tenant_id)
    data = unit.to_dict()
    # Attach direct children
    children = db.query(OrgUnit).filter(
        OrgUnit.parent_id == unit.id,
        OrgUnit.tenant_id == tenant_id,
        OrgUnit.is_active.is_(True),
    ).order_by(OrgUnit.name).all()
    data["children"] = [c.to_dict() for c in children]
    return data


@router.put("/units/{unit_id}")
def update_org_unit(
    unit_id: str,
    body: Dict[str, Any] = Body(default={}),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Update an org unit's attributes."""
    unit = _unit_or_404(db, unit_id, tenant_id)

    if "name" in body:
        unit.name = body["name"]
    if "unit_type" in body:
        try:
            unit.unit_type = OrgUnitType(body["unit_type"])
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid unit_type: {body['unit_type']}")
    if "manager_user_id" in body:
        unit.manager_user_id = body["manager_user_id"]
    if "country" in body:
        unit.country = body["country"]
    if "region" in body:
        unit.region = body["region"]
    if "metadata" in body:
        unit.metadata_ = body["metadata"]

    # Handle parent re-assignment
    if "parent_unit_id" in body:
        if body["parent_unit_id"] is None:
            unit.parent_id = None
            unit.level = 0
            unit.path = None
        else:
            parent = db.query(OrgUnit).filter(
                OrgUnit.unit_id == body["parent_unit_id"],
                OrgUnit.tenant_id == tenant_id,
            ).first()
            if not parent:
                raise HTTPException(status_code=404, detail="Parent unit not found")
            unit.parent_id = parent.id
            level, path = _compute_level_and_path(db, parent.id)
            unit.level = level
            unit.path = path

    db.commit()
    db.refresh(unit)
    return unit.to_dict()


@router.delete("/units/{unit_id}", status_code=204)
def delete_org_unit(
    unit_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Soft-delete an org unit (sets is_active = False)."""
    unit = _unit_or_404(db, unit_id, tenant_id)
    # Check for active children
    child_count = db.query(OrgUnit).filter(
        OrgUnit.parent_id == unit.id,
        OrgUnit.tenant_id == tenant_id,
        OrgUnit.is_active.is_(True),
    ).count()
    if child_count > 0:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot delete org unit with {child_count} active child unit(s). "
                   "Deactivate or re-parent children first.",
        )
    unit.is_active = False
    db.commit()


@router.get("/tree")
def get_org_tree(
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Return the full organisational tree as a nested JSON structure."""
    units = db.query(OrgUnit).filter(
        OrgUnit.tenant_id == tenant_id,
        OrgUnit.is_active.is_(True),
    ).order_by(OrgUnit.level, OrgUnit.name).all()

    tree = _build_tree(units)
    return {
        "total_units": len(units),
        "tree": tree,
    }
