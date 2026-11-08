"""
GAP-2: GRC Platform Configuration Logging Router
"""
import hashlib
import json
import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from db.database import get_db
from db.models.config_logging import ConfigChangeLog, ConfigVersion

router = APIRouter()


def _compute_checksum(data: dict) -> str:
    return hashlib.sha256(json.dumps(data, sort_keys=True, default=str).encode()).hexdigest()


@router.get("/events")
def list_events(
    module: str = None,
    object_type: str = None,
    actor: str = None,
    result: str = None,
    limit: int = 200,
    db: Session = Depends(get_db),
):
    q = db.query(ConfigChangeLog)
    if module:
        q = q.filter(ConfigChangeLog.module == module)
    if object_type:
        q = q.filter(ConfigChangeLog.object_type == object_type)
    if actor:
        q = q.filter(ConfigChangeLog.actor == actor)
    if result:
        q = q.filter(ConfigChangeLog.result == result)
    return [r.to_dict() for r in q.order_by(ConfigChangeLog.created_at.desc()).limit(limit).all()]


@router.post("/events")
def log_config_change(body: dict, db: Session = Depends(get_db)):
    event_data = {
        "module": body["module"],
        "object_type": body["object_type"],
        "object_id": body["object_id"],
        "event_type": body.get("event_type", "update"),
        "before_value": body.get("before_value"),
        "after_value": body.get("after_value"),
        "actor": body.get("actor", "system"),
        "timestamp": datetime.utcnow().isoformat(),
    }
    rec = ConfigChangeLog(
        id=str(uuid.uuid4()),
        tenant_id=body.get("tenant_id", "default"),
        event_id=body.get("event_id", f"EVT-{uuid.uuid4().hex[:8].upper()}"),
        event_type=body.get("event_type", "update"),
        module=body["module"],
        object_type=body["object_type"],
        object_id=body["object_id"],
        object_name=body.get("object_name"),
        before_value=body.get("before_value"),
        after_value=body.get("after_value"),
        changed_fields=body.get("changed_fields"),
        actor=body.get("actor", "system"),
        actor_role=body.get("actor_role"),
        delegated_by=body.get("delegated_by"),
        source=body.get("source", "ui"),
        requires_approval=body.get("requires_approval", False),
        approved_by=body.get("approved_by"),
        change_request_id=body.get("change_request_id"),
        reason=body.get("reason"),
        ip_address=body.get("ip_address"),
        session_id=body.get("session_id"),
        checksum=_compute_checksum(event_data),
        result=body.get("result", "success"),
        error_details=body.get("error_details"),
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)
    return rec.to_dict()


@router.get("/events/{event_id}")
def get_event(event_id: str, db: Session = Depends(get_db)):
    rec = db.query(ConfigChangeLog).filter(
        (ConfigChangeLog.id == event_id) | (ConfigChangeLog.event_id == event_id)
    ).first()
    if not rec:
        raise HTTPException(404, "Event not found")
    return rec.to_dict()


@router.get("/versions")
def list_versions(
    module: str = None,
    object_type: str = None,
    object_id: str = None,
    db: Session = Depends(get_db),
):
    q = db.query(ConfigVersion)
    if module:
        q = q.filter(ConfigVersion.module == module)
    if object_type:
        q = q.filter(ConfigVersion.object_type == object_type)
    if object_id:
        q = q.filter(ConfigVersion.object_id == object_id)
    return [r.to_dict() for r in q.order_by(ConfigVersion.version_number.desc()).limit(100).all()]


@router.post("/versions")
def create_version(body: dict, db: Session = Depends(get_db)):
    existing = db.query(ConfigVersion).filter(
        ConfigVersion.module == body["module"],
        ConfigVersion.object_type == body["object_type"],
        ConfigVersion.object_id == body["object_id"],
    ).order_by(ConfigVersion.version_number.desc()).first()
    next_ver = (existing.version_number + 1) if existing else 1
    rec = ConfigVersion(
        id=str(uuid.uuid4()),
        tenant_id=body.get("tenant_id", "default"),
        module=body["module"],
        object_type=body["object_type"],
        object_id=body["object_id"],
        version_number=next_ver,
        config_snapshot=body["config_snapshot"],
        changed_by=body.get("changed_by", "system"),
        change_reason=body.get("change_reason"),
        change_request_id=body.get("change_request_id"),
        is_active=True,
        deployed_at=datetime.utcnow() if body.get("deployed") else None,
        deployed_by=body.get("deployed_by"),
    )
    if existing:
        existing.is_active = False
    db.add(rec)
    db.commit()
    db.refresh(rec)
    return rec.to_dict()


@router.get("/versions/{version_id}")
def get_version(version_id: str, db: Session = Depends(get_db)):
    rec = db.query(ConfigVersion).filter(ConfigVersion.id == version_id).first()
    if not rec:
        raise HTTPException(404, "Version not found")
    return rec.to_dict()


@router.get("/reports/privileged-activity")
def privileged_activity_report(days: int = 30, db: Session = Depends(get_db)):
    from sqlalchemy import func
    cutoff = datetime.utcnow() - __import__("datetime").timedelta(days=days)
    q = db.query(ConfigChangeLog).filter(
        ConfigChangeLog.created_at >= cutoff,
        ConfigChangeLog.object_type.in_([
            "sod_rule", "kri_threshold", "approval_workflow",
            "scoring_methodology", "control_definition", "user_role",
            "retention_policy", "audit_log_config",
        ]),
    )
    events = [r.to_dict() for r in q.order_by(ConfigChangeLog.created_at.desc()).all()]
    return {"period_days": days, "count": len(events), "events": events}


@router.get("/reports/ruleset-changes")
def ruleset_change_report(db: Session = Depends(get_db)):
    q = db.query(ConfigChangeLog).filter(
        ConfigChangeLog.object_type.in_(["sod_rule", "risk_scoring", "kri_threshold", "control_logic"])
    ).order_by(ConfigChangeLog.created_at.desc()).limit(100)
    return [r.to_dict() for r in q.all()]


@router.get("/summary")
def config_logging_summary(db: Session = Depends(get_db)):
    from sqlalchemy import func
    by_module = db.query(ConfigChangeLog.module, func.count()).group_by(ConfigChangeLog.module).all()
    by_type = db.query(ConfigChangeLog.event_type, func.count()).group_by(ConfigChangeLog.event_type).all()
    total = sum(c for _, c in by_module)
    return {
        "total_events": total,
        "by_module": {m: c for m, c in by_module},
        "by_event_type": {t: c for t, c in by_type},
    }
