"""
Template Library Router
=======================
Endpoints for browsing the global template library, activating items for a tenant,
managing activations, copy-on-write customization, and reviewing pending updates.
"""

import uuid
import logging
import hashlib
import json
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import or_, func

from db.session import get_db
from db.models.template_library import TemplatePack, TemplateItem, TenantItemActivation
from api.dependencies import get_current_user
from core.library.seeder import seed_library

logger = logging.getLogger(__name__)
router = APIRouter()


def _get_tenant_id(current_user=Depends(get_current_user)) -> str:
    return current_user.get("tenant_id", "default")


def _checksum(payload: dict) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


# ---------------------------------------------------------------------------
# PACKS
# ---------------------------------------------------------------------------

@router.get("/packs")
async def list_packs(
    status: Optional[str] = None,
    module: Optional[str] = None,
    db: Session = Depends(get_db),
):
    q = db.query(TemplatePack)
    if status:
        q = q.filter(TemplatePack.status == status)
    if module and module != "all":
        q = q.filter(or_(TemplatePack.module == module, TemplatePack.module == "all"))
    packs = q.order_by(TemplatePack.name).all()
    return {"packs": [p.to_dict() for p in packs], "total": len(packs)}


# ---------------------------------------------------------------------------
# BROWSE LIBRARY
# ---------------------------------------------------------------------------

@router.get("/items")
async def list_items(
    module: Optional[str] = None,
    item_type: Optional[str] = None,
    compliance_framework: Optional[str] = None,
    severity: Optional[str] = None,
    search: Optional[str] = None,
    status: str = "published",
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    q = db.query(TemplateItem).filter(TemplateItem.status == status)
    if module:
        q = q.filter(TemplateItem.module == module)
    if item_type:
        q = q.filter(TemplateItem.item_type == item_type)
    if severity:
        q = q.filter(TemplateItem.severity == severity)
    if compliance_framework:
        q = q.filter(TemplateItem.compliance_frameworks.contains([compliance_framework]))
    if search:
        pattern = f"%{search}%"
        q = q.filter(or_(
            TemplateItem.name.ilike(pattern),
            TemplateItem.description.ilike(pattern),
            TemplateItem.item_code.ilike(pattern),
        ))

    total = q.count()
    items = q.order_by(TemplateItem.module, TemplateItem.item_code)\
             .offset((page - 1) * page_size).limit(page_size).all()

    # Fetch activation status for this tenant in one query
    item_ids = [i.id for i in items]
    activations = {}
    if item_ids:
        rows = db.query(TenantItemActivation)\
                 .filter(TenantItemActivation.tenant_id == tenant_id,
                         TenantItemActivation.template_item_id.in_(item_ids)).all()
        activations = {r.template_item_id: r for r in rows}

    result = []
    for item in items:
        d = item.to_dict(include_payload=False)
        act = activations.get(item.id)
        d["activation"] = act.to_dict() if act else None
        d["is_active"] = act.is_active if act else False
        result.append(d)

    return {
        "items": result,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": (total + page_size - 1) // page_size,
        "facets": _get_facets(db),
    }


def _get_facets(db: Session) -> dict:
    modules = [r[0] for r in db.query(TemplateItem.module).distinct().order_by(TemplateItem.module).all()]
    item_types = [r[0] for r in db.query(TemplateItem.item_type).distinct().order_by(TemplateItem.item_type).all()]
    return {"modules": modules, "item_types": item_types}


@router.get("/items/{item_id}")
async def get_item(
    item_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    item = db.query(TemplateItem).filter(TemplateItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Template item not found")
    d = item.to_dict(include_payload=True)
    act = db.query(TenantItemActivation)\
            .filter_by(tenant_id=tenant_id, template_item_id=item_id).first()
    d["activation"] = act.to_dict() if act else None
    d["is_active"] = act.is_active if act else False
    return d


# ---------------------------------------------------------------------------
# ACTIVATION
# ---------------------------------------------------------------------------

@router.post("/items/{item_id}/activate")
async def activate_item(
    item_id: str,
    body: dict = {},
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
    current_user=Depends(get_current_user),
):
    item = db.query(TemplateItem).filter(TemplateItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Template item not found")

    act = db.query(TenantItemActivation)\
            .filter_by(tenant_id=tenant_id, template_item_id=item_id).first()
    if act:
        if act.is_active:
            return {"status": "already_active", "activation": act.to_dict(include_item=True)}
        act.is_active = True
        act.activated_at = datetime.utcnow()
        act.activated_by = current_user.get("sub")
        act.mappings = body.get("mappings", act.mappings)
    else:
        act = TenantItemActivation(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            template_item_id=item_id,
            is_active=True,
            activated_at=datetime.utcnow(),
            activated_by=current_user.get("sub"),
            mappings=body.get("mappings"),
        )
        db.add(act)
        # Increment global counter
        item.activation_count = (item.activation_count or 0) + 1

    db.commit()
    db.refresh(act)
    return {"status": "activated", "activation": act.to_dict(include_item=True)}


@router.post("/items/{item_id}/deactivate")
async def deactivate_item(
    item_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    act = db.query(TenantItemActivation)\
            .filter_by(tenant_id=tenant_id, template_item_id=item_id).first()
    if not act or not act.is_active:
        raise HTTPException(status_code=404, detail="Activation not found or already inactive")
    act.is_active = False
    db.commit()
    return {"status": "deactivated"}


@router.post("/items/{item_id}/customize")
async def customize_item(
    item_id: str,
    body: dict,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
    current_user=Depends(get_current_user),
):
    """Copy-on-write: first edit clones the global payload into copy_payload."""
    act = db.query(TenantItemActivation)\
            .filter_by(tenant_id=tenant_id, template_item_id=item_id).first()
    if not act or not act.is_active:
        raise HTTPException(status_code=400, detail="Item must be activated before customizing")

    payload = body.get("payload")
    if not payload:
        raise HTTPException(status_code=400, detail="payload is required")

    # First edit: seed copy from global if not already customized
    if act.copy_payload is None:
        act.copy_payload = act.template_item.payload.copy() if act.template_item else {}

    act.copy_payload = payload
    act.customized_at = datetime.utcnow()
    act.customized_by = current_user.get("sub")
    if body.get("mappings"):
        act.mappings = body["mappings"]

    db.commit()
    db.refresh(act)
    return {"status": "customized", "activation": act.to_dict(include_item=True)}


# ---------------------------------------------------------------------------
# ACTIVE CONTENT — what is actually running for this tenant
# ---------------------------------------------------------------------------

@router.get("/active-content")
async def get_active_content(
    module: Optional[str] = None,
    item_type: Optional[str] = None,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Returns effective payloads for all active items in this tenant."""
    q = db.query(TenantItemActivation)\
          .filter_by(tenant_id=tenant_id, is_active=True)\
          .join(TemplateItem, TenantItemActivation.template_item_id == TemplateItem.id)

    if module:
        q = q.filter(TemplateItem.module == module)
    if item_type:
        q = q.filter(TemplateItem.item_type == item_type)

    activations = q.all()
    result = []
    for act in activations:
        item = act.template_item
        d = {
            "activation_id": act.id,
            "item_code": item.item_code,
            "name": item.name,
            "module": item.module,
            "item_type": item.item_type,
            "is_customized": act.copy_payload is not None,
            "effective_payload": act.effective_payload(),
            "mappings": act.mappings or {},
        }
        result.append(d)
    return {"items": result, "total": len(result)}


# ---------------------------------------------------------------------------
# UPDATE REVIEW — pending updates from new global item versions
# ---------------------------------------------------------------------------

@router.get("/pending-updates")
async def get_pending_updates(
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    acts = db.query(TenantItemActivation)\
             .filter(TenantItemActivation.tenant_id == tenant_id,
                     TenantItemActivation.is_active == True,
                     TenantItemActivation.pending_update_version != None).all()
    result = []
    for act in acts:
        item = act.template_item
        d = act.to_dict(include_item=True)
        d["global_version"] = item.version if item else None
        d["global_payload"] = item.payload if item else None
        result.append(d)
    return {"updates": result, "total": len(result)}


@router.get("/items/{item_id}/diff")
async def get_item_diff(
    item_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Returns side-by-side diff of tenant's custom payload vs updated global."""
    act = db.query(TenantItemActivation)\
            .filter_by(tenant_id=tenant_id, template_item_id=item_id).first()
    if not act:
        raise HTTPException(status_code=404, detail="Activation not found")

    item = act.template_item
    return {
        "item_code": item.item_code if item else None,
        "global_version": item.version if item else None,
        "pending_update_version": act.pending_update_version,
        "tenant_payload": act.copy_payload,
        "global_payload": item.payload if item else None,
        "is_customized": act.copy_payload is not None,
    }


@router.post("/items/{item_id}/review-update")
async def review_update(
    item_id: str,
    body: dict,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
    current_user=Depends(get_current_user),
):
    """Accept, reject, or defer a pending update."""
    decision = body.get("decision")  # accept | reject | defer
    if decision not in ("accept", "reject", "defer"):
        raise HTTPException(status_code=400, detail="decision must be accept|reject|defer")

    act = db.query(TenantItemActivation)\
            .filter_by(tenant_id=tenant_id, template_item_id=item_id).first()
    if not act:
        raise HTTPException(status_code=404, detail="Activation not found")

    act.update_review_decision = decision
    act.update_reviewed_at = datetime.utcnow()
    act.notes = body.get("notes")

    if decision == "accept":
        # Apply global payload — clears customization unless tenant had changes
        if act.copy_payload is None:
            # No customization — just clear the pending flag
            pass
        else:
            # Replace copy with new global
            act.copy_payload = act.template_item.payload
        act.pending_update_version = None

    db.commit()
    return {"status": "review_recorded", "decision": decision}


# ---------------------------------------------------------------------------
# BULK ACTIVATE (Activation Wizard)
# ---------------------------------------------------------------------------

@router.post("/activate-bulk")
async def activate_bulk(
    body: dict,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
    current_user=Depends(get_current_user),
):
    """Activate a list of item_ids in one call (used by Activation Wizard)."""
    item_ids = body.get("item_ids", [])
    mappings_by_item = body.get("mappings", {})  # {item_id: {mapping_key: val}}

    if not item_ids:
        raise HTTPException(status_code=400, detail="item_ids required")

    items = db.query(TemplateItem).filter(TemplateItem.id.in_(item_ids)).all()
    existing_acts = {a.template_item_id: a for a in
                     db.query(TenantItemActivation)
                     .filter_by(tenant_id=tenant_id)
                     .filter(TenantItemActivation.template_item_id.in_(item_ids)).all()}

    activated = []
    skipped = []
    for item in items:
        if item.id in existing_acts:
            act = existing_acts[item.id]
            if act.is_active:
                skipped.append(item.id)
                continue
            act.is_active = True
            act.activated_at = datetime.utcnow()
            act.activated_by = current_user.get("sub")
        else:
            act = TenantItemActivation(
                id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                template_item_id=item.id,
                is_active=True,
                activated_at=datetime.utcnow(),
                activated_by=current_user.get("sub"),
                mappings=mappings_by_item.get(item.id),
            )
            db.add(act)
            item.activation_count = (item.activation_count or 0) + 1
        activated.append(item.id)

    db.commit()
    return {"activated": len(activated), "skipped": len(skipped), "activated_ids": activated}


# ---------------------------------------------------------------------------
# SEEDER ENDPOINT (admin only)
# ---------------------------------------------------------------------------

@router.post("/seed")
async def trigger_seed(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Trigger the day-one seeder (idempotent). Admin only."""
    if not current_user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin only")

    def _run_seed():
        from db.session import SessionLocal
        with SessionLocal() as s:
            result = seed_library(s)
            logger.info("Seeder result: %s", result)

    background_tasks.add_task(_run_seed)
    return {"status": "seeding_started"}


@router.get("/stats")
async def get_library_stats(
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    total_items = db.query(func.count(TemplateItem.id)).scalar()
    active_for_tenant = db.query(func.count(TenantItemActivation.id))\
                          .filter_by(tenant_id=tenant_id, is_active=True).scalar()
    customized = db.query(func.count(TenantItemActivation.id))\
                   .filter(TenantItemActivation.tenant_id == tenant_id,
                           TenantItemActivation.is_active == True,
                           TenantItemActivation.copy_payload != None).scalar()
    pending_updates = db.query(func.count(TenantItemActivation.id))\
                        .filter(TenantItemActivation.tenant_id == tenant_id,
                                TenantItemActivation.pending_update_version != None).scalar()

    by_module = db.query(TemplateItem.module, func.count(TemplateItem.id))\
                  .filter(TemplateItem.status == "published")\
                  .group_by(TemplateItem.module).all()

    return {
        "total_library_items": total_items,
        "active_for_tenant": active_for_tenant,
        "customized": customized,
        "pending_updates": pending_updates,
        "adoption_rate": round(active_for_tenant / total_items * 100, 1) if total_items else 0,
        "by_module": {m: c for m, c in by_module},
    }
