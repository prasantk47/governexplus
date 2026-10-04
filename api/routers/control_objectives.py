"""
Control Objectives API Router

Covers PC-SAP-GAP-05: Formal control objective entity linking controls to
specific objectives.  Provides objective-based control mapping and gap
analysis (objectives without any linked controls).
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
import uuid

from db.database import get_db
from db.models.process_control import (
    ControlObjective, ObjectiveStatus,
    ProcessControl,
)
from db.models.risk_management import EnterpriseRisk

router = APIRouter(tags=["Control Objectives"])


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


def _objective_or_404(db: Session, objective_id: str, tenant_id: str) -> ControlObjective:
    o = db.query(ControlObjective).filter(
        ControlObjective.objective_id == objective_id,
        ControlObjective.tenant_id == tenant_id,
        ControlObjective.is_active.is_(True),
    ).first()
    if not o:
        raise HTTPException(status_code=404, detail=f"Control objective '{objective_id}' not found")
    return o


def _enrich_objective(obj: ControlObjective, db: Session, tenant_id: str) -> Dict[str, Any]:
    """
    Return the objective dict enriched with full control and risk detail
    for the GET /{objective_id} endpoint.
    """
    data = obj.to_dict()

    # Expand linked controls
    ctrl_ids = obj.control_ids or []
    controls = db.query(ProcessControl).filter(
        ProcessControl.control_id.in_(ctrl_ids),
        ProcessControl.tenant_id == tenant_id,
    ).all() if ctrl_ids else []
    data["linked_controls"] = [
        {
            "control_id": c.control_id,
            "name": c.name,
            "control_type": c.control_type.value if c.control_type else None,
            "status": c.status.value if c.status else None,
        }
        for c in controls
    ]

    # Expand linked risks
    risk_ids = obj.risk_ids or []
    risks = db.query(EnterpriseRisk).filter(
        EnterpriseRisk.risk_id.in_(risk_ids),
        EnterpriseRisk.tenant_id == tenant_id,
    ).all() if risk_ids else []
    data["linked_risks"] = [
        {
            "risk_id": r.risk_id,
            "title": r.title,
            "category": r.category.value if r.category else None,
            "status": r.status.value if r.status else None,
        }
        for r in risks
    ]
    data["is_covered"] = len(controls) > 0
    return data


# ===========================================================================
# Control Objectives CRUD
# ===========================================================================

@router.post("/", status_code=201)
def create_objective(
    body: Dict[str, Any] = Body(default={}),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Create a new control objective."""
    o = ControlObjective(
        tenant_id=tenant_id,
        objective_id=body.get("objective_id") or _new_id("COBJ"),
        title=body["title"],
        description=body.get("description"),
        process_name=body.get("process_name"),
        subprocess_name=body.get("subprocess_name"),
        framework_requirement_id=body.get("framework_requirement_id"),
        risk_ids=body.get("risk_ids", []),
        control_ids=body.get("control_ids", []),
        owner_id=body.get("owner_id"),
        owner_name=body.get("owner_name"),
        status=ObjectiveStatus.ACTIVE,
        is_active=True,
    )
    db.add(o)
    db.commit()
    db.refresh(o)
    return o.to_dict()


@router.get("/")
def list_objectives(
    process_name: Optional[str] = Query(None),
    framework_requirement_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    q = db.query(ControlObjective).filter(
        ControlObjective.tenant_id == tenant_id,
        ControlObjective.is_active.is_(True),
    )
    if process_name:
        q = q.filter(ControlObjective.process_name == process_name)
    if framework_requirement_id is not None:
        q = q.filter(ControlObjective.framework_requirement_id == framework_requirement_id)
    if status:
        try:
            q = q.filter(ControlObjective.status == ObjectiveStatus(status))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid status")
    objectives = q.order_by(ControlObjective.created_at.asc()).all()
    return {"total": len(objectives), "objectives": [o.to_dict() for o in objectives]}


@router.get("/coverage")
def get_coverage_gaps(
    process_name: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """
    Return objectives that have no linked controls (control gap analysis).

    Useful for identifying areas where objectives exist but no controls
    have been designed to meet them.
    """
    q = db.query(ControlObjective).filter(
        ControlObjective.tenant_id == tenant_id,
        ControlObjective.is_active.is_(True),
        ControlObjective.status == ObjectiveStatus.ACTIVE,
    )
    if process_name:
        q = q.filter(ControlObjective.process_name == process_name)

    all_objectives = q.all()

    # An objective is a gap if control_ids is null/empty
    gap_objectives = [
        o for o in all_objectives
        if not (o.control_ids and len(o.control_ids) > 0)
    ]
    covered = [
        o for o in all_objectives
        if o.control_ids and len(o.control_ids) > 0
    ]

    return {
        "total_objectives": len(all_objectives),
        "covered_count": len(covered),
        "gap_count": len(gap_objectives),
        "coverage_pct": (
            round(len(covered) / len(all_objectives) * 100, 1)
            if all_objectives else 0.0
        ),
        "gaps": [o.to_dict() for o in gap_objectives],
    }


@router.get("/{objective_id}")
def get_objective(
    objective_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Get control objective with full linked risk and control detail."""
    obj = _objective_or_404(db, objective_id, tenant_id)
    return _enrich_objective(obj, db, tenant_id)


@router.put("/{objective_id}")
def update_objective(
    objective_id: str,
    body: Dict[str, Any] = Body(default={}),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    obj = _objective_or_404(db, objective_id, tenant_id)
    scalar_fields = [
        "title", "description", "process_name", "subprocess_name",
        "framework_requirement_id", "owner_id", "owner_name",
    ]
    for field in scalar_fields:
        if field in body:
            setattr(obj, field, body[field])
    if "status" in body:
        try:
            obj.status = ObjectiveStatus(body["status"])
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid status")
    db.commit()
    db.refresh(obj)
    return obj.to_dict()


# ===========================================================================
# Link management
# ===========================================================================

@router.post("/{objective_id}/link-controls")
def link_controls(
    objective_id: str,
    body: Dict[str, Any] = Body(default={}),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """
    Link process control IDs to a control objective.

    Body: { "control_ids": ["CTRL_001", ...], "replace": false }

    Validates that each control_id exists in the tenant.
    """
    obj = _objective_or_404(db, objective_id, tenant_id)
    new_ids: List[str] = body.get("control_ids", [])
    if not new_ids:
        raise HTTPException(status_code=400, detail="control_ids list is required")

    validated, not_found = [], []
    for cid in new_ids:
        exists = db.query(ProcessControl).filter(
            ProcessControl.control_id == cid,
            ProcessControl.tenant_id == tenant_id,
        ).first()
        (validated if exists else not_found).append(cid)

    existing = list(obj.control_ids or [])
    if body.get("replace", False):
        obj.control_ids = validated
    else:
        obj.control_ids = existing + [c for c in validated if c not in existing]

    db.commit()
    return {
        "objective_id": objective_id,
        "control_ids": obj.control_ids,
        "not_found": not_found,
    }


@router.post("/{objective_id}/link-risks")
def link_risks(
    objective_id: str,
    body: Dict[str, Any] = Body(default={}),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """
    Link enterprise risk IDs to a control objective.

    Body: { "risk_ids": ["RISK_001", ...], "replace": false }

    Validates that each risk_id exists in the tenant.
    """
    obj = _objective_or_404(db, objective_id, tenant_id)
    new_ids: List[str] = body.get("risk_ids", [])
    if not new_ids:
        raise HTTPException(status_code=400, detail="risk_ids list is required")

    validated, not_found = [], []
    for rid in new_ids:
        exists = db.query(EnterpriseRisk).filter(
            EnterpriseRisk.risk_id == rid,
            EnterpriseRisk.tenant_id == tenant_id,
        ).first()
        (validated if exists else not_found).append(rid)

    existing = list(obj.risk_ids or [])
    if body.get("replace", False):
        obj.risk_ids = validated
    else:
        obj.risk_ids = existing + [r for r in validated if r not in existing]

    db.commit()
    return {
        "objective_id": objective_id,
        "risk_ids": obj.risk_ids,
        "not_found": not_found,
    }
