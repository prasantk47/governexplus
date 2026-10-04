"""
Platform Configuration API Router

Provides runtime configuration endpoints that read/write to the database.
Changes take effect on the next request without requiring a service restart.

Endpoints:
  POST /config/workflows/{workflow_type}        — update approval stage config
  GET  /config/workflows/{workflow_type}        — read workflow stage config
  POST /config/sla                              — update SLA thresholds
  GET  /config/sla                              — read SLA config
  POST /config/rbac/grants                      — grant an RBAC permission
  GET  /config/rbac/grants                      — list all RBAC grants
  POST /config/notification-templates/{code}   — update notification template body
  GET  /config/notification-templates/{code}   — read notification template
  GET  /config/notification-templates          — list all notification templates
  POST /config/feature-flags/{flag}            — toggle a feature flag
  GET  /config/feature-flags                   — list all feature flags
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import Column, Integer, String, JSON, DateTime, UniqueConstraint, text
from sqlalchemy.orm import Session

from api.dependencies import get_current_user
from db.database import get_db
from db.models.base import Base


# ---------------------------------------------------------------------------
# Inline ORM model (avoids a separate models file for this lightweight table)
# ---------------------------------------------------------------------------

class PlatformConfig(Base):
    __tablename__ = "platform_config"
    __table_args__ = (
        UniqueConstraint("tenant_id", "namespace", "config_key", name="uq_platform_config"),
        {"extend_existing": True},
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(String(100), nullable=False, index=True)
    namespace = Column(String(100), nullable=False)
    config_key = Column(String(255), nullable=False)
    config_value = Column(JSON, nullable=True)
    updated_by = Column(String(100), nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ---------------------------------------------------------------------------
# RBAC
# ---------------------------------------------------------------------------

_CONFIG_ADMIN_ROLES = {"platform_admin", "tenant_admin", "admin", "super_admin"}


def _require_admin(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    caller_roles = set(current_user.get("roles", []) or [current_user.get("role", "")])
    if not (caller_roles & _CONFIG_ADMIN_ROLES):
        raise HTTPException(status_code=403, detail="Configuration changes require admin role")
    return current_user


def _get_tenant_id() -> str:
    from core.tenant import get_current_tenant
    ctx = get_current_tenant()
    return ctx.tenant_id if ctx else "default"


router = APIRouter(tags=["Platform Configuration"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _upsert_config(
    db: Session,
    tenant_id: str,
    namespace: str,
    key: str,
    value: Any,
    updated_by: str,
) -> PlatformConfig:
    """Insert or update a config entry."""
    try:
        row = (
            db.query(PlatformConfig)
            .filter_by(tenant_id=tenant_id, namespace=namespace, config_key=key)
            .first()
        )
        if row:
            row.config_value = value
            row.updated_by = updated_by
            row.updated_at = datetime.utcnow()
        else:
            row = PlatformConfig(
                tenant_id=tenant_id,
                namespace=namespace,
                config_key=key,
                config_value=value,
                updated_by=updated_by,
            )
            db.add(row)
        db.commit()
        db.refresh(row)
        return row
    except Exception:
        db.rollback()
        raise


def _get_config(db: Session, tenant_id: str, namespace: str, key: str) -> Optional[PlatformConfig]:
    try:
        return (
            db.query(PlatformConfig)
            .filter_by(tenant_id=tenant_id, namespace=namespace, config_key=key)
            .first()
        )
    except Exception:
        return None


def _list_config(db: Session, tenant_id: str, namespace: str) -> List[PlatformConfig]:
    try:
        return db.query(PlatformConfig).filter_by(tenant_id=tenant_id, namespace=namespace).all()
    except Exception:
        return []


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class WorkflowStageConfig(BaseModel):
    stages: List[Dict[str, Any]] = Field(..., description="Ordered list of approval stages")


class SLAConfig(BaseModel):
    module: str = Field(..., description="Module name, e.g. access_requests")
    warning_hours: int = Field(default=24, ge=1)
    breach_hours: int = Field(default=48, ge=1)


class RBACGrantConfig(BaseModel):
    role: str = Field(..., description="Role name to grant permission to")
    permission: str = Field(..., description="Permission identifier")
    resource: str = Field(..., description="Resource path or pattern")


class NotificationTemplateUpdate(BaseModel):
    subject: Optional[str] = Field(default=None)
    body: str = Field(..., description="Template body with {{variable}} placeholders")
    html_body: Optional[str] = Field(default=None)


class FeatureFlagUpdate(BaseModel):
    enabled: bool = Field(..., description="Whether the feature flag is enabled")
    description: Optional[str] = Field(default=None)


# ---------------------------------------------------------------------------
# Workflow endpoints
# ---------------------------------------------------------------------------

@router.post("/workflows/{workflow_type}", summary="Update workflow stage configuration")
def update_workflow_config(
    workflow_type: str,
    body: WorkflowStageConfig,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(_require_admin),
    tenant_id: str = Depends(_get_tenant_id),
) -> Dict[str, Any]:
    """Update the approval stage configuration for a workflow type."""
    row = _upsert_config(
        db, tenant_id, "workflows", workflow_type,
        {"stages": body.stages, "workflow_type": workflow_type},
        current_user.get("sub", "system"),
    )
    return {
        "status": "ok",
        "workflow_type": workflow_type,
        "stages": body.stages,
        "stage_count": len(body.stages),
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


@router.get("/workflows/{workflow_type}", summary="Read workflow stage configuration")
def get_workflow_config(
    workflow_type: str,
    db: Session = Depends(get_db),
    _: Dict[str, Any] = Depends(get_current_user),
    tenant_id: str = Depends(_get_tenant_id),
) -> Dict[str, Any]:
    row = _get_config(db, tenant_id, "workflows", workflow_type)
    if not row:
        # Return default 2-stage approval workflow
        return {
            "workflow_type": workflow_type,
            "stages": [
                {"name": "manager_approval", "required": True, "sla_hours": 24},
                {"name": "security_review", "required": False, "sla_hours": 48},
            ],
            "source": "default",
        }
    val = row.config_value or {}
    return {
        "workflow_type": workflow_type,
        "stages": val.get("stages", []),
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        "updated_by": row.updated_by,
        "source": "database",
    }


# ---------------------------------------------------------------------------
# SLA endpoints
# ---------------------------------------------------------------------------

@router.post("/sla", summary="Update SLA thresholds")
def update_sla_config(
    body: SLAConfig,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(_require_admin),
    tenant_id: str = Depends(_get_tenant_id),
) -> Dict[str, Any]:
    """Update SLA warning and breach thresholds for a module."""
    row = _upsert_config(
        db, tenant_id, "sla", body.module,
        {"module": body.module, "warning_hours": body.warning_hours, "breach_hours": body.breach_hours},
        current_user.get("sub", "system"),
    )
    return {
        "status": "ok",
        "module": body.module,
        "warning_hours": body.warning_hours,
        "breach_hours": body.breach_hours,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


@router.get("/sla", summary="Read SLA configuration")
def get_sla_config(
    module: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _: Dict[str, Any] = Depends(get_current_user),
    tenant_id: str = Depends(_get_tenant_id),
) -> Dict[str, Any]:
    if module:
        row = _get_config(db, tenant_id, "sla", module)
        if not row:
            return {"module": module, "warning_hours": 24, "breach_hours": 48, "source": "default"}
        return {**row.config_value, "source": "database",
                "updated_at": row.updated_at.isoformat() if row.updated_at else None}
    rows = _list_config(db, tenant_id, "sla")
    return {
        "items": [
            {**r.config_value, "updated_at": r.updated_at.isoformat() if r.updated_at else None}
            for r in rows
        ]
    }


# ---------------------------------------------------------------------------
# RBAC grants endpoints
# ---------------------------------------------------------------------------

@router.post("/rbac/grants", summary="Grant an RBAC permission")
def create_rbac_grant(
    body: RBACGrantConfig,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(_require_admin),
    tenant_id: str = Depends(_get_tenant_id),
) -> Dict[str, Any]:
    """Grant a permission to a role. Changes take effect immediately."""
    grant_key = f"{body.role}:{body.permission}"
    row = _upsert_config(
        db, tenant_id, "rbac_grants", grant_key,
        {"role": body.role, "permission": body.permission, "resource": body.resource, "active": True},
        current_user.get("sub", "system"),
    )
    return {
        "status": "ok",
        "role": body.role,
        "permission": body.permission,
        "resource": body.resource,
        "grant_id": row.id,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


@router.get("/rbac/grants", summary="List RBAC permission grants")
def list_rbac_grants(
    role: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _: Dict[str, Any] = Depends(get_current_user),
    tenant_id: str = Depends(_get_tenant_id),
) -> Dict[str, Any]:
    rows = _list_config(db, tenant_id, "rbac_grants")
    items = [r.config_value for r in rows if r.config_value]
    if role:
        items = [i for i in items if i.get("role") == role]
    return {"items": items, "total": len(items)}


# ---------------------------------------------------------------------------
# Notification template endpoints
# ---------------------------------------------------------------------------

# Seed defaults so GET always returns something useful
_DEFAULT_TEMPLATES = {
    "ACCESS_REQUEST_SUBMITTED": {
        "code": "ACCESS_REQUEST_SUBMITTED",
        "subject": "Access Request Submitted — {{role_name}}",
        "body": "Dear {{approver_name}},\n\n{{requester_name}} has submitted an access request for {{role_name}}.\n\nPlease review: {{review_url}}",
    },
    "ACCESS_REQUEST_APPROVED": {
        "code": "ACCESS_REQUEST_APPROVED",
        "subject": "Access Request Approved — {{role_name}}",
        "body": "Dear {{requester_name}},\n\nYour access request for {{role_name}} has been approved.",
    },
    "ACCESS_REQUEST_REJECTED": {
        "code": "ACCESS_REQUEST_REJECTED",
        "subject": "Access Request Rejected — {{role_name}}",
        "body": "Dear {{requester_name}},\n\nYour access request for {{role_name}} has been rejected. Reason: {{reason}}",
    },
    "SOD_VIOLATION_DETECTED": {
        "code": "SOD_VIOLATION_DETECTED",
        "subject": "SoD Violation Detected — {{rule_name}}",
        "body": "A Segregation of Duties violation has been detected for user {{user_name}}.\n\nRule: {{rule_name}}\nSeverity: {{severity}}",
    },
    "CERTIFICATION_REMINDER": {
        "code": "CERTIFICATION_REMINDER",
        "subject": "Access Certification Reminder — {{campaign_name}}",
        "body": "Dear {{reviewer_name}},\n\nYou have pending access certifications in campaign {{campaign_name}}.\nDeadline: {{deadline}}",
    },
}


@router.post(
    "/notification-templates/{code}",
    summary="Update notification template body",
)
def update_notification_template(
    code: str,
    body: NotificationTemplateUpdate,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(_require_admin),
    tenant_id: str = Depends(_get_tenant_id),
) -> Dict[str, Any]:
    """Update notification template subject/body. Changes take effect immediately."""
    existing = _get_config(db, tenant_id, "notification_templates", code)
    current_val = (existing.config_value if existing else None) or _DEFAULT_TEMPLATES.get(code, {})
    new_val = {
        "code": code,
        "subject": body.subject if body.subject is not None else current_val.get("subject", ""),
        "body": body.body,
        "html_body": body.html_body or current_val.get("html_body"),
    }
    row = _upsert_config(
        db, tenant_id, "notification_templates", code,
        new_val, current_user.get("sub", "system"),
    )
    return {
        "status": "ok",
        "code": code,
        **new_val,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


@router.get(
    "/notification-templates",
    summary="List all notification templates",
)
def list_notification_templates(
    db: Session = Depends(get_db),
    _: Dict[str, Any] = Depends(get_current_user),
    tenant_id: str = Depends(_get_tenant_id),
) -> Dict[str, Any]:
    rows = _list_config(db, tenant_id, "notification_templates")
    db_templates = {r.config_key: r.config_value for r in rows if r.config_value}
    merged = {**_DEFAULT_TEMPLATES, **db_templates}
    return {"items": list(merged.values()), "total": len(merged)}


@router.get(
    "/notification-templates/{code}",
    summary="Read a notification template",
)
def get_notification_template(
    code: str,
    db: Session = Depends(get_db),
    _: Dict[str, Any] = Depends(get_current_user),
    tenant_id: str = Depends(_get_tenant_id),
) -> Dict[str, Any]:
    row = _get_config(db, tenant_id, "notification_templates", code)
    if row and row.config_value:
        return {**row.config_value, "source": "database"}
    default = _DEFAULT_TEMPLATES.get(code)
    if default:
        return {**default, "source": "default"}
    raise HTTPException(status_code=404, detail=f"Template '{code}' not found")


# ---------------------------------------------------------------------------
# Feature flags
# ---------------------------------------------------------------------------

_DEFAULT_FLAGS = {
    "ai_risk_narratives": {"flag": "ai_risk_narratives", "enabled": True, "description": "AI-generated risk narratives"},
    "sod_simulation": {"flag": "sod_simulation", "enabled": True, "description": "SoD simulation mode"},
    "auto_mitigation": {"flag": "auto_mitigation", "enabled": False, "description": "Automatic risk mitigation suggestions"},
    "cross_system_sod": {"flag": "cross_system_sod", "enabled": True, "description": "Cross-system SoD analysis"},
    "ml_role_mining": {"flag": "ml_role_mining", "enabled": True, "description": "ML-powered role mining"},
    "digital_twin": {"flag": "digital_twin", "enabled": True, "description": "Digital twin access simulation"},
}


@router.post("/feature-flags/{flag}", summary="Enable or disable a feature flag")
def update_feature_flag(
    flag: str,
    body: FeatureFlagUpdate,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(_require_admin),
    tenant_id: str = Depends(_get_tenant_id),
) -> Dict[str, Any]:
    val = {
        "flag": flag,
        "enabled": body.enabled,
        "description": body.description or _DEFAULT_FLAGS.get(flag, {}).get("description", ""),
    }
    row = _upsert_config(
        db, tenant_id, "feature_flags", flag,
        val, current_user.get("sub", "system"),
    )
    return {
        "status": "ok",
        **val,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


@router.get("/feature-flags", summary="List all feature flags")
def list_feature_flags(
    db: Session = Depends(get_db),
    _: Dict[str, Any] = Depends(get_current_user),
    tenant_id: str = Depends(_get_tenant_id),
) -> Dict[str, Any]:
    rows = _list_config(db, tenant_id, "feature_flags")
    db_flags = {r.config_key: r.config_value for r in rows if r.config_value}
    merged = {**_DEFAULT_FLAGS, **db_flags}
    return {"items": list(merged.values()), "total": len(merged)}
