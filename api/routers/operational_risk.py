"""
Operational Risk / RCSA API Router

Basel II/III operational loss event capture, RCSA (Risk & Control
Self-Assessment), loss database with event types and business lines.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import uuid

from db.database import get_db
from db.models.governance_extended import OperationalLossEvent

router = APIRouter(tags=["Operational Risk / RCSA"])


def _get_tenant_id() -> str:
    from core.tenant import get_current_tenant
    ctx = get_current_tenant()
    return ctx.tenant_id if ctx else "default"


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def _event_or_404(db: Session, event_id: str, tenant_id: str) -> OperationalLossEvent:
    e = db.query(OperationalLossEvent).filter(
        OperationalLossEvent.event_id == event_id,
        OperationalLossEvent.tenant_id == tenant_id,
        OperationalLossEvent.is_active.is_(True),
    ).first()
    if not e:
        raise HTTPException(status_code=404, detail=f"Loss event '{event_id}' not found")
    return e


# Basel II event type categories
BASEL_EVENT_TYPES = [
    "internal_fraud", "external_fraud", "employment_practices",
    "clients_products_practices", "damage_to_assets",
    "business_disruption", "execution_delivery", "system_failures",
]

# Basel II business lines
BUSINESS_LINES = [
    "corporate_finance", "trading_sales", "retail_banking",
    "commercial_banking", "payment_settlement", "agency_services",
    "asset_management", "retail_brokerage",
]


@router.get("/loss-events")
def list_loss_events(
    status: Optional[str] = Query(None),
    event_type: Optional[str] = Query(None),
    business_line: Optional[str] = Query(None),
    min_gross_loss: Optional[float] = Query(None),
    is_near_miss: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    q = db.query(OperationalLossEvent).filter(
        OperationalLossEvent.tenant_id == tenant_id,
        OperationalLossEvent.is_active.is_(True),
    )
    if status:
        q = q.filter(OperationalLossEvent.status == status)
    if event_type:
        q = q.filter(OperationalLossEvent.event_type == event_type)
    if business_line:
        q = q.filter(OperationalLossEvent.business_line == business_line)
    if min_gross_loss is not None:
        q = q.filter(OperationalLossEvent.gross_loss_amount >= min_gross_loss)
    if is_near_miss is not None:
        q = q.filter(OperationalLossEvent.is_near_miss == is_near_miss)
    events = q.order_by(OperationalLossEvent.occurred_at.desc()).all()
    result = []
    for e in events:
        d = e.to_dict()
        d["event_date"] = d.get("occurred_at")
        d["gross_loss_amount"] = d.get("gross_loss")
        d["net_loss_amount"] = d.get("net_loss")
        result.append(d)
    return {"events": result, "total": len(result)}


@router.post("/loss-events", status_code=201)
def create_loss_event(
    body: Dict[str, Any] = Body(default={}),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    e = OperationalLossEvent(
        event_id=_new_id("OPLOSS"),
        tenant_id=tenant_id,
        title=body["title"],
        description=body.get("description", ""),
        event_type=body.get("event_type", "execution_delivery"),
        business_line=body.get("business_line"),
        occurred_at=datetime.fromisoformat(body["event_date"]) if body.get("event_date") else datetime.utcnow(),
        detected_at=datetime.utcnow(),
        gross_loss=body.get("gross_loss_amount"),
        net_loss=body.get("net_loss_amount"),
        recoveries=body.get("recovery_amount"),
        currency=body.get("currency", "USD"),
        is_near_miss=bool(body.get("is_near_miss", False)),
        root_cause_category=body.get("root_cause_category"),
        root_cause_description=body.get("root_cause_description"),
        reported_by=body.get("reported_by"),
        status="reported",
    )
    db.add(e)
    db.commit()
    db.refresh(e)
    return e.to_dict()


@router.get("/loss-events/{event_id}")
def get_loss_event(
    event_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    return _event_or_404(db, event_id, tenant_id).to_dict()


@router.put("/loss-events/{event_id}")
def update_loss_event(
    event_id: str,
    body: Dict[str, Any] = Body(default={}),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    e = _event_or_404(db, event_id, tenant_id)
    updatable = [
        "title", "description", "event_type", "business_line",
        "gross_loss", "net_loss", "recoveries", "currency",
        "is_near_miss", "root_cause_category", "root_cause_description",
        "corrective_actions", "preventive_actions", "status",
    ]
    for k in updatable:
        if k in body:
            setattr(e, k, body[k])
    if body.get("status") == "closed" and not e.reviewed_at:
        e.reviewed_at = datetime.utcnow()
        e.reviewed_by = body.get("reviewed_by")
    db.commit()
    db.refresh(e)
    return e.to_dict()


@router.get("/loss-database/summary")
def loss_database_summary(
    days: int = Query(365, ge=30, le=1825),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    since = datetime.utcnow() - timedelta(days=days)
    events = db.query(OperationalLossEvent).filter(
        OperationalLossEvent.tenant_id == tenant_id,
        OperationalLossEvent.occurred_at >= since,
        OperationalLossEvent.is_active.is_(True),
    ).all()

    by_type: Dict[str, Dict[str, Any]] = {}
    for et in BASEL_EVENT_TYPES:
        matched = [e for e in events if e.event_type == et]
        by_type[et] = {
            "count": len(matched),
            "total_gross_loss": sum(float(e.gross_loss or 0) for e in matched),
            "total_net_loss": sum(float(e.net_loss or 0) for e in matched),
        }

    by_line: Dict[str, Dict[str, Any]] = {}
    for bl in BUSINESS_LINES:
        matched = [e for e in events if e.business_line == bl]
        by_line[bl] = {
            "count": len(matched),
            "total_gross_loss": sum(float(e.gross_loss or 0) for e in matched),
        }

    total_gross = sum(float(e.gross_loss or 0) for e in events)
    total_net = sum(float(e.net_loss or 0) for e in events)
    total_recovery = sum(float(e.recoveries or 0) for e in events)

    return {
        "period_days": days,
        "total_events": len(events),
        "near_misses": sum(1 for e in events if e.is_near_miss),
        "total_gross_loss": round(total_gross, 2),
        "total_net_loss": round(total_net, 2),
        "total_recovery": round(total_recovery, 2),
        "by_event_type": by_type,
        "by_business_line": by_line,
    }


@router.get("/reference/event-types")
def get_event_types():
    return {"event_types": BASEL_EVENT_TYPES}


@router.get("/reference/business-lines")
def get_business_lines():
    return {"business_lines": BUSINESS_LINES}
