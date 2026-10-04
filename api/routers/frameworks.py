"""
Framework Management API Router

CRUD for GRC framework definitions and their hierarchical requirements
(COSO, COBIT, ISO 27001, SOX, custom).  Used by both Process Control
(PC-03) and the cross-module framework coverage report (XI-07).

Direct DB queries — no manager class needed.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
import uuid

from db.database import get_db
from db.models.grc_foundation import FrameworkDefinition, FrameworkType, FrameworkRequirement

router = APIRouter(tags=["Frameworks"])


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

def _new_id(prefix: str = "FW") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


def _framework_or_404(db: Session, framework_id: str, tenant_id: str) -> FrameworkDefinition:
    fw = db.query(FrameworkDefinition).filter(
        FrameworkDefinition.framework_id == framework_id,
        FrameworkDefinition.tenant_id == tenant_id,
        FrameworkDefinition.is_active.is_(True),
    ).first()
    if not fw:
        raise HTTPException(status_code=404, detail=f"Framework '{framework_id}' not found")
    return fw


def _req_or_404(db: Session, requirement_id: str, tenant_id: str) -> FrameworkRequirement:
    req = db.query(FrameworkRequirement).filter(
        FrameworkRequirement.requirement_id == requirement_id,
        FrameworkRequirement.tenant_id == tenant_id,
    ).first()
    if not req:
        raise HTTPException(status_code=404, detail=f"Requirement '{requirement_id}' not found")
    return req


def _build_req_tree(requirements: List[FrameworkRequirement]) -> List[Dict[str, Any]]:
    """Assemble requirements into a nested tree (parent → children)."""
    by_pk: Dict[int, Dict[str, Any]] = {}
    for r in requirements:
        d = r.to_dict()
        d["children"] = []
        by_pk[r.id] = d

    roots: List[Dict[str, Any]] = []
    for r in requirements:
        if r.parent_requirement_id and r.parent_requirement_id in by_pk:
            by_pk[r.parent_requirement_id]["children"].append(by_pk[r.id])
        elif not r.parent_requirement_id:
            roots.append(by_pk[r.id])

    return roots


# ===========================================================================
# Framework CRUD
# ===========================================================================

@router.post("/", status_code=201)
def create_framework(
    body: Dict[str, Any] = Body(default={}),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Create a new GRC framework definition."""
    try:
        framework_type = FrameworkType(body.get("framework_type", "custom"))
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid framework_type. Valid values: {[e.value for e in FrameworkType]}",
        )

    # Prevent duplicate framework_id within tenant
    existing = db.query(FrameworkDefinition).filter(
        FrameworkDefinition.framework_id == body.get("framework_id", ""),
        FrameworkDefinition.tenant_id == tenant_id,
    ).first()
    if existing and body.get("framework_id"):
        raise HTTPException(status_code=409, detail=f"Framework ID '{body['framework_id']}' already exists")

    fw = FrameworkDefinition(
        tenant_id=tenant_id,
        framework_id=body.get("framework_id") or _new_id("FW"),
        name=body["name"],
        version=body.get("version"),
        description=body.get("description"),
        framework_type=framework_type,
        structure=body.get("structure"),
        is_active=True,
    )
    db.add(fw)
    db.commit()
    db.refresh(fw)
    return fw.to_dict()


@router.get("/")
def list_frameworks(
    framework_type: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """List all active frameworks for this tenant."""
    q = db.query(FrameworkDefinition).filter(
        FrameworkDefinition.tenant_id == tenant_id,
        FrameworkDefinition.is_active.is_(True),
    )
    if framework_type:
        try:
            q = q.filter(FrameworkDefinition.framework_type == FrameworkType(framework_type))
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid framework_type: {framework_type}")
    if search:
        q = q.filter(FrameworkDefinition.name.ilike(f"%{search}%"))

    frameworks = q.order_by(FrameworkDefinition.name).all()
    return {"total": len(frameworks), "frameworks": [fw.to_dict() for fw in frameworks]}


@router.get("/{framework_id}")
def get_framework(
    framework_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Get a framework with its full requirements tree."""
    fw = _framework_or_404(db, framework_id, tenant_id)
    data = fw.to_dict()

    requirements = db.query(FrameworkRequirement).filter(
        FrameworkRequirement.framework_id == fw.id,
        FrameworkRequirement.tenant_id == tenant_id,
    ).order_by(FrameworkRequirement.level, FrameworkRequirement.sort_order).all()

    data["requirements_count"] = len(requirements)
    data["requirements_tree"] = _build_req_tree(requirements)
    return data


@router.put("/{framework_id}")
def update_framework(
    framework_id: str,
    body: Dict[str, Any] = Body(default={}),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Update framework metadata."""
    fw = _framework_or_404(db, framework_id, tenant_id)

    if "name" in body:
        fw.name = body["name"]
    if "version" in body:
        fw.version = body["version"]
    if "description" in body:
        fw.description = body["description"]
    if "structure" in body:
        fw.structure = body["structure"]
    if "framework_type" in body:
        try:
            fw.framework_type = FrameworkType(body["framework_type"])
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid framework_type: {body['framework_type']}")
    if "is_active" in body:
        fw.is_active = body["is_active"]

    db.commit()
    db.refresh(fw)
    return fw.to_dict()


# ===========================================================================
# Requirements CRUD
# ===========================================================================

@router.post("/{framework_id}/requirements", status_code=201)
def add_requirement(
    framework_id: str,
    body: Dict[str, Any] = Body(default={}),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Add a requirement (principle / control objective) to a framework."""
    fw = _framework_or_404(db, framework_id, tenant_id)

    # Resolve optional parent requirement
    parent_pk: Optional[int] = None
    if body.get("parent_requirement_id"):
        parent_req = db.query(FrameworkRequirement).filter(
            FrameworkRequirement.requirement_id == body["parent_requirement_id"],
            FrameworkRequirement.framework_id == fw.id,
            FrameworkRequirement.tenant_id == tenant_id,
        ).first()
        if not parent_req:
            raise HTTPException(
                status_code=404,
                detail=f"Parent requirement '{body['parent_requirement_id']}' not found in framework",
            )
        parent_pk = parent_req.id

    # Calculate level
    level = 0
    if parent_pk:
        parent_req_obj = db.query(FrameworkRequirement).filter(
            FrameworkRequirement.id == parent_pk
        ).first()
        level = (parent_req_obj.level + 1) if parent_req_obj else 1

    req = FrameworkRequirement(
        tenant_id=tenant_id,
        framework_id=fw.id,
        requirement_id=body.get("requirement_id") or _new_id("REQ"),
        title=body["title"],
        description=body.get("description"),
        parent_requirement_id=parent_pk,
        level=level,
        sort_order=body.get("sort_order", 0),
        category=body.get("category"),
    )
    db.add(req)
    db.commit()
    db.refresh(req)
    return req.to_dict()


@router.get("/{framework_id}/requirements")
def list_requirements(
    framework_id: str,
    flat: bool = Query(default=False, description="Return a flat list instead of a tree"),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """List requirements for a framework, optionally as a nested tree."""
    fw = _framework_or_404(db, framework_id, tenant_id)
    requirements = db.query(FrameworkRequirement).filter(
        FrameworkRequirement.framework_id == fw.id,
        FrameworkRequirement.tenant_id == tenant_id,
    ).order_by(FrameworkRequirement.level, FrameworkRequirement.sort_order).all()

    if flat:
        return {"total": len(requirements), "requirements": [r.to_dict() for r in requirements]}

    return {
        "framework_id": framework_id,
        "total": len(requirements),
        "requirements": _build_req_tree(requirements),
    }


@router.put("/requirements/{requirement_id}")
def update_requirement(
    requirement_id: str,
    body: Dict[str, Any] = Body(default={}),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Update a framework requirement."""
    req = _req_or_404(db, requirement_id, tenant_id)

    if "title" in body:
        req.title = body["title"]
    if "description" in body:
        req.description = body["description"]
    if "category" in body:
        req.category = body["category"]
    if "sort_order" in body:
        req.sort_order = body["sort_order"]

    # Re-parent if requested
    if "parent_requirement_id" in body:
        if body["parent_requirement_id"] is None:
            req.parent_requirement_id = None
            req.level = 0
        else:
            parent_req = db.query(FrameworkRequirement).filter(
                FrameworkRequirement.requirement_id == body["parent_requirement_id"],
                FrameworkRequirement.tenant_id == tenant_id,
            ).first()
            if not parent_req:
                raise HTTPException(status_code=404, detail="Parent requirement not found")
            req.parent_requirement_id = parent_req.id
            req.level = parent_req.level + 1

    db.commit()
    db.refresh(req)
    return req.to_dict()


@router.delete("/requirements/{requirement_id}", status_code=204)
def delete_requirement(
    requirement_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Delete a framework requirement (hard delete — requirement must have no children)."""
    req = _req_or_404(db, requirement_id, tenant_id)

    child_count = db.query(FrameworkRequirement).filter(
        FrameworkRequirement.parent_requirement_id == req.id,
        FrameworkRequirement.tenant_id == tenant_id,
    ).count()
    if child_count > 0:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot delete requirement with {child_count} child requirement(s). "
                   "Delete children first.",
        )
    db.delete(req)
    db.commit()
