"""
SMTP Configuration API Router

Allows tenant admins to configure their own SMTP server for email notifications.
Config is stored in Tenant.settings['smtp'] — no migration required.
"""

from __future__ import annotations

import smtplib
import ssl
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from db.database import get_db
from db.models.tenant import Tenant
from core.notifications.delivery import SMTPClient, EmailPayload
from api.dependencies import get_current_user
from core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(tags=["SMTP Configuration"])

DEFAULT_TENANT = "tenant_default"


def _get_tenant_id(x_tenant_id: Optional[str] = Header(None)) -> str:
    return x_tenant_id or DEFAULT_TENANT


class SmtpConfigRequest(BaseModel):
    host: str = Field(..., description="SMTP server hostname, e.g. smtp.gmail.com")
    port: int = Field(587, ge=1, le=65535)
    username: str = Field(..., description="SMTP authentication username / email")
    password: str = Field(..., description="SMTP authentication password or app password")
    from_email: str = Field("noreply@governexplus.com", description="Sender email address")
    from_name: str = Field("GovernexPlus", description="Sender display name")
    use_tls: bool = Field(True, description="Use STARTTLS (recommended)")
    is_enabled: bool = Field(True, description="Enable this config for outgoing notifications")


class SmtpTestRequest(BaseModel):
    to: str = Field(..., description="Test recipient email address")
    # Optional: if omitted, uses saved config; if provided, tests inline config
    host: Optional[str] = None
    port: Optional[int] = None
    username: Optional[str] = None
    password: Optional[str] = None
    from_email: Optional[str] = None
    from_name: Optional[str] = None
    use_tls: Optional[bool] = None


def _get_tenant(tenant_id: str, db: Session) -> Tenant:
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail=f"Tenant '{tenant_id}' not found")
    return tenant


# ---------------------------------------------------------------------------
# GET /settings/smtp
# ---------------------------------------------------------------------------

@router.get("/smtp")
async def get_smtp_config(
    tenant_id: str = Depends(_get_tenant_id),
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user),
) -> Dict[str, Any]:
    """Return current SMTP configuration for this tenant. Password is masked."""
    tenant = _get_tenant(tenant_id, db)
    settings = tenant.settings or {}
    cfg = settings.get("smtp") or {}

    return {
        "tenant_id": tenant_id,
        "configured": bool(cfg.get("host") and cfg.get("username")),
        "is_enabled": cfg.get("is_enabled", False),
        "host": cfg.get("host", ""),
        "port": cfg.get("port", 587),
        "username": cfg.get("username", ""),
        "password": "••••••••" if cfg.get("password") else "",
        "from_email": cfg.get("from_email", "noreply@governexplus.com"),
        "from_name": cfg.get("from_name", "GovernexPlus"),
        "use_tls": cfg.get("use_tls", True),
    }


# ---------------------------------------------------------------------------
# PUT /settings/smtp
# ---------------------------------------------------------------------------

@router.put("/smtp")
async def save_smtp_config(
    req: SmtpConfigRequest,
    tenant_id: str = Depends(_get_tenant_id),
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user),
) -> Dict[str, Any]:
    """Save (create or update) SMTP configuration for this tenant."""
    tenant = _get_tenant(tenant_id, db)
    settings = dict(tenant.settings or {})

    settings["smtp"] = {
        "host": req.host,
        "port": req.port,
        "username": req.username,
        "password": req.password,
        "from_email": req.from_email,
        "from_name": req.from_name,
        "use_tls": req.use_tls,
        "is_enabled": req.is_enabled,
    }

    tenant.settings = settings
    db.add(tenant)
    db.commit()

    logger.info("smtp_config.saved", tenant_id=tenant_id, host=req.host)
    return {
        "message": "SMTP configuration saved",
        "tenant_id": tenant_id,
        "host": req.host,
        "port": req.port,
        "username": req.username,
        "from_email": req.from_email,
        "is_enabled": req.is_enabled,
    }


# ---------------------------------------------------------------------------
# POST /settings/smtp/test
# ---------------------------------------------------------------------------

@router.post("/smtp/test")
async def test_smtp_config(
    req: SmtpTestRequest,
    tenant_id: str = Depends(_get_tenant_id),
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user),
) -> Dict[str, Any]:
    """Send a test email using either the provided inline config or the saved config."""
    # Build config dict: inline fields override saved config
    tenant = _get_tenant(tenant_id, db)
    settings = tenant.settings or {}
    saved = settings.get("smtp") or {}

    config = {
        "host": req.host or saved.get("host", ""),
        "port": req.port or saved.get("port", 587),
        "username": req.username or saved.get("username", ""),
        "password": req.password or saved.get("password", ""),
        "from_email": req.from_email or saved.get("from_email", "noreply@governexplus.com"),
        "use_tls": req.use_tls if req.use_tls is not None else saved.get("use_tls", True),
    }

    if not config["host"] or not config["username"] or not config["password"]:
        raise HTTPException(
            status_code=400,
            detail="SMTP host, username, and password are required for the test.",
        )

    client = SMTPClient.from_dict(config)
    payload = EmailPayload(
        to=[req.to],
        subject="GovernexPlus SMTP Test",
        body=(
            "This is a test email from GovernexPlus.\n\n"
            "If you received this, your SMTP configuration is working correctly."
        ),
        html_body=(
            "<p>This is a test email from <strong>GovernexPlus</strong>.</p>"
            "<p>If you received this, your SMTP configuration is working correctly.</p>"
        ),
    )

    success, error = client.send(payload)

    if success:
        logger.info("smtp_test.success", tenant_id=tenant_id, to=req.to)
        return {"success": True, "message": f"Test email sent to {req.to}"}
    else:
        logger.warning("smtp_test.failed", tenant_id=tenant_id, error=error)
        raise HTTPException(status_code=502, detail=f"SMTP test failed: {error}")


# ---------------------------------------------------------------------------
# DELETE /settings/smtp
# ---------------------------------------------------------------------------

@router.delete("/smtp")
async def delete_smtp_config(
    tenant_id: str = Depends(_get_tenant_id),
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user),
) -> Dict[str, Any]:
    """Remove SMTP configuration for this tenant (revert to system default)."""
    tenant = _get_tenant(tenant_id, db)
    settings = dict(tenant.settings or {})
    settings.pop("smtp", None)
    tenant.settings = settings
    db.add(tenant)
    db.commit()
    logger.info("smtp_config.deleted", tenant_id=tenant_id)
    return {"message": "SMTP configuration removed. System default will be used."}
