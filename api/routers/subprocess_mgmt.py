"""
Subprocess Hierarchy API Router

Covers PC-SAP-GAP-06: Multi-level subprocess decomposition with linked
controls and risks.  Endpoints support unlimited nesting via the
self-referential parent_subprocess_id FK.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
import uuid

from db.database import get_db
from db.models.process_control import SubProcess

router = APIRouter(tags=["Subprocess Management"])


# ---------------------------------------------------------------------------
# Tenant helpers
# ---------------------------------------------------------------------------

def _get_tenant_id() -> str:
    from core.tenant import get_current_tenant
    ctx = get_current_tenant()
    return ctx.tenant_id if ctx else "default"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def _subprocess_or_404(db: Session, subprocess_id: str, tenant_id: str) -> SubProcess:
    s = db.query(SubProcess).filter(
        SubProcess.subprocess_id == subprocess_id,
        SubProcess.tenant_id == tenant_id,
        SubProcess.is_active.is_(True),
    ).first()
    if not s:
        raise HTTPException(status_code=404, detail=f"Subprocess '{subprocess_id}' not found")
    return s


def _build_tree_node(sp: SubProcess, child_map: Dict[int, List[SubProcess]]) -> Dict[str, Any]:
    """Recursively build a tree node dict from a SubProcess record."""
    node = sp.to_dict()
    children = child_map.get(sp.id, [])
    node["children"] = [_build_tree_node(c, child_map) for c in
                        sorted(children, key=lambda x: x.sort_order)]
    return node


# ===========================================================================
# Subprocess CRUD
# ===========================================================================

@router.post("/", status_code=201)
def create_subprocess(
    body: Dict[str, Any] = Body(default={}),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Create a subprocess node in the hierarchy."""
    parent_pk = None
    level = 1
    if body.get("parent_subprocess_id"):
        parent = db.query(SubProcess).filter(
            SubProcess.subprocess_id == body["parent_subprocess_id"],
            SubProcess.tenant_id == tenant_id,
            SubProcess.is_active.is_(True),
        ).first()
        if not parent:
            raise HTTPException(
                status_code=404,
                detail=f"Parent subprocess '{body['parent_subprocess_id']}' not found",
            )
        parent_pk = parent.id
        level = parent.level + 1

    sp = SubProcess(
        tenant_id=tenant_id,
        subprocess_id=body.get("subprocess_id") or _new_id("SUB"),
        name=body["name"],
        description=body.get("description"),
        process_name=body["process_name"],
        parent_subprocess_id=parent_pk,
        org_unit_id=body.get("org_unit_id"),
        owner_id=body.get("owner_id"),
        owner_name=body.get("owner_name"),
        level=level,
        sort_order=body.get("sort_order", 0),
        risk_ids=body.get("risk_ids", []),
        control_ids=body.get("control_ids", []),
        is_active=True,
    )
    db.add(sp)
    db.commit()
    db.refresh(sp)
    return sp.to_dict()


@router.get("/")
def list_subprocesses(
    process_name: Optional[str] = Query(None),
    parent_subprocess_id: Optional[str] = Query(None, description="Business key of parent subprocess"),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    q = db.query(SubProcess).filter(
        SubProcess.tenant_id == tenant_id,
        SubProcess.is_active.is_(True),
    )
    if process_name:
        q = q.filter(SubProcess.process_name == process_name)
    if parent_subprocess_id:
        parent = db.query(SubProcess).filter(
            SubProcess.subprocess_id == parent_subprocess_id,
            SubProcess.tenant_id == tenant_id,
        ).first()
        if parent:
            q = q.filter(SubProcess.parent_subprocess_id == parent.id)
        else:
            return {"total": 0, "subprocesses": []}
    sps = q.order_by(SubProcess.sort_order.asc(), SubProcess.name.asc()).all()
    return {"total": len(sps), "subprocesses": [s.to_dict() for s in sps]}


@router.get("/tree")
def get_subprocess_tree(
    process_name: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """
    Return the full subprocess tree grouped by process_name.

    If process_name is given, returns the tree for that process only.
    Each node contains a 'children' list of its direct descendants.
    """
    q = db.query(SubProcess).filter(
        SubProcess.tenant_id == tenant_id,
        SubProcess.is_active.is_(True),
    )
    if process_name:
        q = q.filter(SubProcess.process_name == process_name)

    all_sps = q.order_by(SubProcess.sort_order.asc()).all()

    # Index children by parent PK
    child_map: Dict[int, List[SubProcess]] = {}
    for sp in all_sps:
        if sp.parent_subprocess_id:
            child_map.setdefault(sp.parent_subprocess_id, []).append(sp)

    # Roots are nodes with no parent within this tenant / process filter
    roots = [sp for sp in all_sps if sp.parent_subprocess_id is None]

    # Group by process_name
    tree: Dict[str, List[Dict]] = {}
    for root in roots:
        pn = root.process_name
        tree.setdefault(pn, [])
        tree[pn].append(_build_tree_node(root, child_map))

    return {"process_count": len(tree), "tree": tree}


@router.get("/{subprocess_id}")
def get_subprocess(
    subprocess_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Get subprocess detail with immediate children."""
    sp = _subprocess_or_404(db, subprocess_id, tenant_id)
    data = sp.to_dict()
    children = db.query(SubProcess).filter(
        SubProcess.parent_subprocess_id == sp.id,
        SubProcess.tenant_id == tenant_id,
        SubProcess.is_active.is_(True),
    ).order_by(SubProcess.sort_order.asc()).all()
    data["children"] = [c.to_dict() for c in children]
    return data


@router.put("/{subprocess_id}")
def update_subprocess(
    subprocess_id: str,
    body: Dict[str, Any] = Body(default={}),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    sp = _subprocess_or_404(db, subprocess_id, tenant_id)
    scalar_fields = [
        "name", "description", "process_name", "org_unit_id",
        "owner_id", "owner_name", "sort_order", "risk_ids", "control_ids",
    ]
    for field in scalar_fields:
        if field in body:
            setattr(sp, field, body[field])
    db.commit()
    db.refresh(sp)
    return sp.to_dict()


@router.delete("/{subprocess_id}", status_code=204)
def delete_subprocess(
    subprocess_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Soft delete a subprocess (sets is_active=False)."""
    sp = _subprocess_or_404(db, subprocess_id, tenant_id)
    # Cascade soft delete to children
    def _soft_delete(node: SubProcess) -> None:
        node.is_active = False
        children = db.query(SubProcess).filter(
            SubProcess.parent_subprocess_id == node.id,
            SubProcess.tenant_id == tenant_id,
            SubProcess.is_active.is_(True),
        ).all()
        for child in children:
            _soft_delete(child)

    _soft_delete(sp)
    db.commit()
    return None


# ===========================================================================
# Link management
# ===========================================================================

@router.post("/{subprocess_id}/link-controls")
def link_controls(
    subprocess_id: str,
    body: Dict[str, Any] = Body(default={}),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """
    Link process control IDs to a subprocess.

    Body: { "control_ids": ["CTRL_001", ...], "replace": false }
    """
    sp = _subprocess_or_404(db, subprocess_id, tenant_id)
    new_ids: List[str] = body.get("control_ids", [])
    if not new_ids:
        raise HTTPException(status_code=400, detail="control_ids list is required")

    existing = list(sp.control_ids or [])
    if body.get("replace", False):
        sp.control_ids = new_ids
    else:
        sp.control_ids = existing + [c for c in new_ids if c not in existing]

    db.commit()
    return {"subprocess_id": subprocess_id, "control_ids": sp.control_ids}


@router.post("/{subprocess_id}/link-risks")
def link_risks(
    subprocess_id: str,
    body: Dict[str, Any] = Body(default={}),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """
    Link enterprise risk IDs to a subprocess.

    Body: { "risk_ids": ["RISK_001", ...], "replace": false }
    """
    sp = _subprocess_or_404(db, subprocess_id, tenant_id)
    new_ids: List[str] = body.get("risk_ids", [])
    if not new_ids:
        raise HTTPException(status_code=400, detail="risk_ids list is required")

    existing = list(sp.risk_ids or [])
    if body.get("replace", False):
        sp.risk_ids = new_ids
    else:
        sp.risk_ids = existing + [r for r in new_ids if r not in existing]

    db.commit()
    return {"subprocess_id": subprocess_id, "risk_ids": sp.risk_ids}
