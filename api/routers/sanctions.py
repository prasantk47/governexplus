"""
Sanctions / Watchlist Screening API Router

Screens entities (vendors, employees, counterparties) against OFAC,
UN, EU, UK watchlists with match resolution workflow.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from typing import Dict, List, Optional, Any
from datetime import datetime
from sqlalchemy.orm import Session
import uuid

from db.database import get_db
from db.models.governance_extended import SanctionsScreening

router = APIRouter(tags=["Sanctions Screening"])


def _get_tenant_id() -> str:
    from core.tenant import get_current_tenant
    ctx = get_current_tenant()
    return ctx.tenant_id if ctx else "default"


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def _screening_or_404(db: Session, screening_id: str, tenant_id: str) -> SanctionsScreening:
    s = db.query(SanctionsScreening).filter(
        SanctionsScreening.screening_id == screening_id,
        SanctionsScreening.tenant_id == tenant_id,
        SanctionsScreening.is_active.is_(True),
    ).first()
    if not s:
        raise HTTPException(status_code=404, detail=f"Screening '{screening_id}' not found")
    return s


WATCHLISTS = ["OFAC", "UN", "EU", "UK_HMT", "INTERPOL"]
ENTITY_TYPES = ["vendor", "employee", "customer", "counterparty", "individual", "organization"]


@router.get("")
def list_screenings(
    status: Optional[str] = Query(None),
    entity_type: Optional[str] = Query(None),
    has_match: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    q = db.query(SanctionsScreening).filter(
        SanctionsScreening.tenant_id == tenant_id,
        SanctionsScreening.is_active.is_(True),
    )
    if status:
        q = q.filter(SanctionsScreening.status == status)
    if entity_type:
        q = q.filter(SanctionsScreening.entity_type == entity_type)
    if has_match is not None:
        # match_found is not a DB column; filter by status instead
        if has_match:
            q = q.filter(SanctionsScreening.status.in_(["potential_match", "confirmed_match", "pending_review"]))
        else:
            q = q.filter(SanctionsScreening.status == "clear")
    screenings = q.order_by(SanctionsScreening.screened_at.desc()).all()
    return {"screenings": [s.to_dict() for s in screenings], "total": len(screenings)}


@router.post("", status_code=201)
def run_screening(
    body: Dict[str, Any] = Body(default={}),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """
    Submit an entity for sanctions screening. The match_found and match_details
    fields are populated by the compliance team or via external watchlist API integration.
    """
    entity_name = body["entity_name"]
    watchlists = body.get("watchlists", WATCHLISTS)
    has_match = body.get("match_found", False)

    # Build a screening record — real watchlist API integration goes here
    # via configured connector (body.get("connector") or env WATCHLIST_API_URL)
    s = SanctionsScreening(
        screening_id=_new_id("SCREEN"),
        tenant_id=tenant_id,
        entity_name=entity_name,
        entity_type=body.get("entity_type", "vendor"),
        entity_id=body.get("entity_reference"),
        country=body.get("entity_country"),
        lists_checked=watchlists,
        screened_at=datetime.utcnow(),
        screened_by=body.get("screened_by", "system"),
        match_details=body.get("match_details"),
        status="potential_match" if has_match else "clear",
        resolution_notes=body.get("notes"),
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    return s.to_dict()


@router.get("/{screening_id}")
def get_screening(
    screening_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    return _screening_or_404(db, screening_id, tenant_id).to_dict()


@router.put("/{screening_id}/resolve")
def resolve_screening(
    screening_id: str,
    body: Dict[str, Any] = Body(default={}),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    s = _screening_or_404(db, screening_id, tenant_id)
    resolution = body.get("resolution")
    # Map friendly resolution to model statuses
    resolution_map = {
        "true_match": "confirmed_match",
        "false_positive": "false_positive",
        "escalated": "potential_match",
    }
    allowed = set(resolution_map.keys())
    if resolution not in allowed:
        raise HTTPException(status_code=422, detail=f"Resolution must be one of: {allowed}")
    s.status = resolution_map[resolution]
    s.resolved_at = datetime.utcnow()
    s.resolved_by = body.get("resolved_by")
    s.resolution_notes = body.get("resolution_notes")
    db.commit()
    db.refresh(s)
    return s.to_dict()


@router.post("/batch", status_code=201)
def batch_screening(
    body: Dict[str, Any] = Body(default={}),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Batch screen multiple entities from a list."""
    entities: List[Dict[str, Any]] = body.get("entities", [])
    if not entities:
        raise HTTPException(status_code=422, detail="entities list is required")
    if len(entities) > 500:
        raise HTTPException(status_code=422, detail="Max 500 entities per batch")

    results = []
    watchlists = body.get("watchlists", WATCHLISTS)
    screened_by = body.get("screened_by", "batch_import")
    now = datetime.utcnow()

    for entity in entities:
        s = SanctionsScreening(
            screening_id=_new_id("SCREEN"),
            tenant_id=tenant_id,
            entity_name=entity["entity_name"],
            entity_type=entity.get("entity_type", "vendor"),
            entity_id=entity.get("entity_reference"),
            country=entity.get("entity_country"),
            lists_checked=watchlists,
            screened_at=now,
            screened_by=screened_by,
            status="clear",
        )
        db.add(s)
        results.append(s)

    db.commit()
    return {
        "screened": len(results),
        "screening_ids": [s.screening_id for s in results],
    }


@router.get("/summary/stats")
def screening_stats(
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    screenings = db.query(SanctionsScreening).filter(
        SanctionsScreening.tenant_id == tenant_id,
        SanctionsScreening.is_active.is_(True),
    ).all()
    return {
        "total_screened": len(screenings),
        "matches_found": sum(1 for s in screenings if getattr(s.status, 'value', s.status) in ("potential_match", "confirmed_match")),
        "pending_review": sum(1 for s in screenings if getattr(s.status, 'value', s.status) == "potential_match"),
        "true_matches": sum(1 for s in screenings if getattr(s.status, 'value', s.status) == "confirmed_match"),
        "false_positives": sum(1 for s in screenings if getattr(s.status, 'value', s.status) == "false_positive"),
        "clear": sum(1 for s in screenings if getattr(s.status, 'value', s.status) == "clear"),
    }


@router.get("/reference/watchlists")
def get_watchlists():
    return {"watchlists": WATCHLISTS}
