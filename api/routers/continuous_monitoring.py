"""
GAP-6: Continuous Monitoring Rules Engine Router
"""
import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from db.database import get_db
from db.models.continuous_monitoring import MonitoringRule, MonitoringAlert

router = APIRouter()


# ── Rules ─────────────────────────────────────────────────────────────────────

@router.get("/rules")
def list_rules(module: str = None, is_active: bool = None, db: Session = Depends(get_db)):
    q = db.query(MonitoringRule)
    if module:
        q = q.filter(MonitoringRule.module == module)
    if is_active is not None:
        q = q.filter(MonitoringRule.is_active == is_active)
    return [r.to_dict() for r in q.order_by(MonitoringRule.created_at.desc()).limit(200).all()]


@router.post("/rules")
def create_rule(body: dict, db: Session = Depends(get_db)):
    rec = MonitoringRule(
        id=str(uuid.uuid4()),
        tenant_id=body.get("tenant_id", "default"),
        rule_id=body.get("rule_id", f"MON-{uuid.uuid4().hex[:8].upper()}"),
        name=body["name"],
        description=body.get("description"),
        module=body["module"],
        event_type=body["event_type"],
        data_source=body.get("data_source"),
        target_object_type=body.get("target_object_type"),
        condition_type=body.get("condition_type", "threshold"),
        condition_config=body.get("condition_config", {}),
        severity=body.get("severity", "medium"),
        frequency_minutes=body.get("frequency_minutes", 60),
        is_active=body.get("is_active", True),
        auto_create_issue=body.get("auto_create_issue", False),
        notify_roles=body.get("notify_roles"),
        escalation_minutes=body.get("escalation_minutes"),
        escalation_to=body.get("escalation_to"),
        owner=body.get("owner"),
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)
    return rec.to_dict()


@router.get("/rules/{rule_id}")
def get_rule(rule_id: str, db: Session = Depends(get_db)):
    rec = db.query(MonitoringRule).filter(
        (MonitoringRule.id == rule_id) | (MonitoringRule.rule_id == rule_id)
    ).first()
    if not rec:
        raise HTTPException(404, "Rule not found")
    return rec.to_dict()


@router.put("/rules/{rule_id}")
def update_rule(rule_id: str, body: dict, db: Session = Depends(get_db)):
    rec = db.query(MonitoringRule).filter(
        (MonitoringRule.id == rule_id) | (MonitoringRule.rule_id == rule_id)
    ).first()
    if not rec:
        raise HTTPException(404, "Rule not found")
    for k, v in body.items():
        if hasattr(rec, k) and k not in ("id", "tenant_id", "rule_id"):
            setattr(rec, k, v)
    db.commit()
    db.refresh(rec)
    return rec.to_dict()


@router.put("/rules/{rule_id}/toggle")
def toggle_rule(rule_id: str, db: Session = Depends(get_db)):
    rec = db.query(MonitoringRule).filter(
        (MonitoringRule.id == rule_id) | (MonitoringRule.rule_id == rule_id)
    ).first()
    if not rec:
        raise HTTPException(404, "Rule not found")
    rec.is_active = not rec.is_active
    db.commit()
    db.refresh(rec)
    return rec.to_dict()


@router.delete("/rules/{rule_id}")
def delete_rule(rule_id: str, db: Session = Depends(get_db)):
    rec = db.query(MonitoringRule).filter(
        (MonitoringRule.id == rule_id) | (MonitoringRule.rule_id == rule_id)
    ).first()
    if not rec:
        raise HTTPException(404, "Rule not found")
    db.delete(rec)
    db.commit()
    return {"deleted": rule_id}


# ── Alerts ────────────────────────────────────────────────────────────────────

@router.get("/alerts")
def list_alerts(
    status: str = None,
    severity: str = None,
    module: str = None,
    db: Session = Depends(get_db),
):
    q = db.query(MonitoringAlert)
    if status:
        q = q.filter(MonitoringAlert.status == status)
    if severity:
        q = q.filter(MonitoringAlert.severity == severity)
    if module:
        q = q.filter(MonitoringAlert.module == module)
    return [r.to_dict() for r in q.order_by(MonitoringAlert.created_at.desc()).limit(200).all()]


@router.post("/alerts")
def create_alert(body: dict, db: Session = Depends(get_db)):
    rec = MonitoringAlert(
        id=str(uuid.uuid4()),
        tenant_id=body.get("tenant_id", "default"),
        alert_id=body.get("alert_id", f"ALR-{uuid.uuid4().hex[:8].upper()}"),
        rule_id=body.get("rule_id", "manual"),
        rule_name=body.get("rule_name"),
        module=body["module"],
        event_type=body["event_type"],
        severity=body.get("severity", "medium"),
        title=body["title"],
        description=body.get("description"),
        trigger_data=body.get("trigger_data"),
        target_object_type=body.get("target_object_type"),
        target_object_id=body.get("target_object_id"),
        affected_user=body.get("affected_user"),
        status="open",
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)
    return rec.to_dict()


@router.get("/alerts/{alert_id}")
def get_alert(alert_id: str, db: Session = Depends(get_db)):
    rec = db.query(MonitoringAlert).filter(
        (MonitoringAlert.id == alert_id) | (MonitoringAlert.alert_id == alert_id)
    ).first()
    if not rec:
        raise HTTPException(404, "Alert not found")
    return rec.to_dict()


@router.put("/alerts/{alert_id}/acknowledge")
def acknowledge_alert(alert_id: str, body: dict, db: Session = Depends(get_db)):
    rec = db.query(MonitoringAlert).filter(
        (MonitoringAlert.id == alert_id) | (MonitoringAlert.alert_id == alert_id)
    ).first()
    if not rec:
        raise HTTPException(404, "Alert not found")
    rec.status = "acknowledged"
    rec.acknowledged_by = body.get("actor", "system")
    rec.acknowledged_at = datetime.utcnow()
    db.commit()
    db.refresh(rec)
    return rec.to_dict()


@router.put("/alerts/{alert_id}/resolve")
def resolve_alert(alert_id: str, body: dict, db: Session = Depends(get_db)):
    rec = db.query(MonitoringAlert).filter(
        (MonitoringAlert.id == alert_id) | (MonitoringAlert.alert_id == alert_id)
    ).first()
    if not rec:
        raise HTTPException(404, "Alert not found")
    rec.status = "resolved"
    rec.resolved_by = body.get("actor", "system")
    rec.resolved_at = datetime.utcnow()
    rec.resolution_notes = body.get("notes")
    rec.linked_issue_id = body.get("linked_issue_id")
    db.commit()
    db.refresh(rec)
    return rec.to_dict()


@router.get("/dashboard")
def monitoring_dashboard(db: Session = Depends(get_db)):
    from sqlalchemy import func
    open_alerts = db.query(func.count()).filter(MonitoringAlert.status == "open").scalar()
    by_sev = db.query(MonitoringAlert.severity, func.count()).filter(
        MonitoringAlert.status.in_(["open", "acknowledged"])
    ).group_by(MonitoringAlert.severity).all()
    by_module = db.query(MonitoringAlert.module, func.count()).filter(
        MonitoringAlert.status.in_(["open", "acknowledged"])
    ).group_by(MonitoringAlert.module).all()
    active_rules = db.query(func.count()).filter(MonitoringRule.is_active == True).scalar()
    return {
        "open_alerts": open_alerts,
        "by_severity": {s: c for s, c in by_sev},
        "by_module": {m: c for m, c in by_module},
        "active_rules": active_rules,
    }
