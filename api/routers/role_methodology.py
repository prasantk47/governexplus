"""
Role Methodology and Prerequisites API Router

Adds DB-backed role methodology lifecycle, prerequisites, and reaffirmation
campaign management on top of the existing role_engineering router.

These endpoints complement /role-engineering/* using the DB models for
persistent role records rather than the in-memory RoleDesigner singleton.

Prefix: /role-methodology
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import uuid

from db.database import get_db

router = APIRouter(tags=["Role Methodology"])

# ---------------------------------------------------------------------------
# Tenant helpers
# ---------------------------------------------------------------------------

def _get_tenant_id() -> str:
    from core.tenant import get_current_tenant
    ctx = get_current_tenant()
    return ctx.tenant_id if ctx else "default"


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


# ---------------------------------------------------------------------------
# Lazy DB model import helpers
# ---------------------------------------------------------------------------

def _get_role_model():
    """Lazy-import DB role model to avoid circular imports."""
    from db.models.user import Role
    return Role


# ---------------------------------------------------------------------------
# Methodology stages (ordered lifecycle)
# ---------------------------------------------------------------------------

_METHODOLOGY_STAGES = [
    "requirements_gathering",
    "design",
    "risk_review",
    "business_approval",
    "technical_build",
    "testing",
    "go_live",
    "post_implementation_review",
]


def _role_or_404(db: Session, role_id: str, tenant_id: str):
    """Return a DB Role record or raise 404."""
    Role = _get_role_model()
    r = db.query(Role).filter(
        Role.role_id == role_id,
        Role.tenant_id == tenant_id,
    ).first()
    if not r:
        raise HTTPException(status_code=404, detail=f"Role '{role_id}' not found")
    return r


# ===========================================================================
# Prerequisites  (role-to-role dependency graph)
# ===========================================================================

@router.put("/roles/{role_id}/prerequisites")
def set_prerequisites(
    role_id: str,
    body: Dict[str, Any] = Body(default={}),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """
    Set (replace) the prerequisite role list for a role.

    Body: { "prerequisite_role_ids": ["ROLE_001", "ROLE_002"] }

    Prerequisite role IDs are validated to exist.  The list is stored in
    the role's metadata_ JSON under the key "prerequisites".
    """
    role = _role_or_404(db, role_id, tenant_id)
    Role = _get_role_model()

    prereq_ids: List[str] = body.get("prerequisite_role_ids", [])
    validated, not_found = [], []
    for pid in prereq_ids:
        exists = db.query(Role).filter(
            Role.role_id == pid,
            Role.tenant_id == tenant_id,
        ).first()
        (validated if exists else not_found).append(pid)

    if not_found:
        raise HTTPException(
            status_code=404,
            detail=f"Prerequisite role(s) not found: {not_found}",
        )

    meta = dict(role.metadata_ or {})
    meta["prerequisites"] = validated
    meta["prerequisites_updated_at"] = datetime.utcnow().isoformat()
    meta["prerequisites_updated_by"] = body.get("updated_by")
    role.metadata_ = meta
    db.commit()
    return {
        "role_id": role_id,
        "prerequisite_role_ids": validated,
        "updated_at": meta["prerequisites_updated_at"],
    }


@router.get("/roles/{role_id}/prerequisites")
def get_prerequisites(
    role_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """
    Get the prerequisite roles for a role, with their detail.
    """
    role = _role_or_404(db, role_id, tenant_id)
    Role = _get_role_model()

    meta = role.metadata_ or {}
    prereq_ids: List[str] = meta.get("prerequisites", [])

    prereqs = []
    for pid in prereq_ids:
        pr = db.query(Role).filter(
            Role.role_id == pid,
            Role.tenant_id == tenant_id,
        ).first()
        if pr:
            prereqs.append({
                "role_id": pr.role_id,
                "role_name": pr.role_name,
                "description": getattr(pr, "description", None),
            })
        else:
            prereqs.append({"role_id": pid, "role_name": None, "status": "not_found"})

    return {
        "role_id": role_id,
        "prerequisite_count": len(prereqs),
        "prerequisites": prereqs,
    }


# ===========================================================================
# Methodology Stage
# ===========================================================================

@router.put("/roles/{role_id}/methodology-stage")
def advance_methodology_stage(
    role_id: str,
    body: Dict[str, Any] = Body(default={}),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """
    Advance (or explicitly set) the methodology stage for a role.

    Ordered stages: requirements_gathering → design → risk_review →
    business_approval → technical_build → testing → go_live →
    post_implementation_review

    Body:
      stage (optional) : explicitly set to this stage (must be a valid stage)
      advanced_by      : user performing the advance
      notes            : optional notes
    """
    role = _role_or_404(db, role_id, tenant_id)
    meta = dict(role.metadata_ or {})

    current_stage = meta.get("methodology_stage")
    target_stage = body.get("stage")

    if target_stage:
        if target_stage not in _METHODOLOGY_STAGES:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid stage '{target_stage}'. Valid stages: {_METHODOLOGY_STAGES}",
            )
        new_stage = target_stage
    else:
        # Auto-advance to next stage
        if current_stage is None:
            new_stage = _METHODOLOGY_STAGES[0]
        else:
            try:
                idx = _METHODOLOGY_STAGES.index(current_stage)
            except ValueError:
                new_stage = _METHODOLOGY_STAGES[0]
            else:
                if idx >= len(_METHODOLOGY_STAGES) - 1:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Role is already at the final methodology stage '{current_stage}'",
                    )
                new_stage = _METHODOLOGY_STAGES[idx + 1]

    # Build stage history entry
    history = meta.get("methodology_history", [])
    history.append({
        "from_stage": current_stage,
        "to_stage": new_stage,
        "advanced_by": body.get("advanced_by"),
        "notes": body.get("notes"),
        "timestamp": datetime.utcnow().isoformat(),
    })
    meta["methodology_stage"] = new_stage
    meta["methodology_history"] = history
    meta["methodology_stage_updated_at"] = datetime.utcnow().isoformat()
    role.metadata_ = meta
    db.commit()

    return {
        "role_id": role_id,
        "previous_stage": current_stage,
        "current_stage": new_stage,
        "stage_index": _METHODOLOGY_STAGES.index(new_stage),
        "total_stages": len(_METHODOLOGY_STAGES),
        "is_final_stage": new_stage == _METHODOLOGY_STAGES[-1],
        "updated_at": meta["methodology_stage_updated_at"],
    }


# ===========================================================================
# Reaffirmation
# ===========================================================================

@router.get("/roles/{role_id}/reaffirmation-status")
def get_reaffirmation_status(
    role_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """
    Check whether a role needs reaffirmation.

    Roles store their reaffirmation schedule in metadata_:
      reaffirmation_days        : int — days between required reaffirmations
      last_reaffirmed_at        : ISO datetime
      next_reaffirmation_due_at : ISO datetime (computed from last + days)
    """
    role = _role_or_404(db, role_id, tenant_id)
    meta = role.metadata_ or {}

    reaffirmation_days = meta.get("reaffirmation_days", 365)
    last_str = meta.get("last_reaffirmed_at")

    if last_str:
        last_dt = datetime.fromisoformat(last_str)
        due_dt = last_dt + timedelta(days=reaffirmation_days)
        needs_reaffirmation = datetime.utcnow() >= due_dt
    else:
        # Never reaffirmed — treat created_at as baseline
        baseline = role.created_at or datetime.utcnow()
        due_dt = baseline + timedelta(days=reaffirmation_days)
        needs_reaffirmation = datetime.utcnow() >= due_dt
        last_str = None

    return {
        "role_id": role_id,
        "role_name": role.role_name,
        "reaffirmation_days": reaffirmation_days,
        "last_reaffirmed_at": last_str,
        "next_reaffirmation_due_at": due_dt.isoformat(),
        "needs_reaffirmation": needs_reaffirmation,
        "days_overdue": max(0, (datetime.utcnow() - due_dt).days) if needs_reaffirmation else 0,
    }


@router.post("/roles/reaffirmation-campaign")
def create_reaffirmation_campaign(
    body: Dict[str, Any] = Body(default={}),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """
    Create a reaffirmation campaign for all roles past their reaffirmation_days.

    Scans all roles in the tenant and returns a campaign record listing which
    roles need reaffirmation.  Optionally accepts role_ids to scope the check.

    Body:
      role_ids       : list of role_ids to check (omit = all roles)
      created_by     : campaign initiator
      campaign_name  : optional campaign label
    """
    Role = _get_role_model()

    q = db.query(Role).filter(Role.tenant_id == tenant_id)
    scoped_ids: List[str] = body.get("role_ids", [])
    if scoped_ids:
        q = q.filter(Role.role_id.in_(scoped_ids))

    all_roles = q.all()
    now = datetime.utcnow()

    overdue_roles = []
    for role in all_roles:
        meta = role.metadata_ or {}
        reaffirmation_days = meta.get("reaffirmation_days", 365)
        last_str = meta.get("last_reaffirmed_at")

        if last_str:
            last_dt = datetime.fromisoformat(last_str)
        else:
            last_dt = role.created_at or now

        due_dt = last_dt + timedelta(days=reaffirmation_days)
        if now >= due_dt:
            overdue_roles.append({
                "role_id": role.role_id,
                "role_name": role.role_name,
                "last_reaffirmed_at": last_str,
                "due_at": due_dt.isoformat(),
                "days_overdue": max(0, (now - due_dt).days),
            })

    campaign_id = _new_id("RCAMPAIGN")
    return {
        "campaign_id": campaign_id,
        "campaign_name": body.get("campaign_name", f"Reaffirmation Campaign {now.strftime('%Y-%m-%d')}"),
        "created_by": body.get("created_by"),
        "created_at": now.isoformat(),
        "roles_scanned": len(all_roles),
        "roles_requiring_reaffirmation": len(overdue_roles),
        "roles": overdue_roles,
    }
