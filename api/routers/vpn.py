"""
VPN Tunnel Management Router
==============================
CRUD for VPN tunnel configs + connect/disconnect/status operations.
Used to manage Cisco AnyConnect tunnels required for SAP RFC connectivity.
"""
import logging
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db.database import get_db
from db.models.vpn_config import VPNTunnelConfig
from core.vpn.tunnel_manager import VPNTunnelManager, VPNConfig, VPNProvider, VPNStatus

logger = logging.getLogger(__name__)
router = APIRouter()

# ── Schemas ──────────────────────────────────────────────────────────────────

class VPNTunnelCreate(BaseModel):
    name: str
    provider: str = "cisco_anyconnect"
    gateway: str
    group: str = ""
    username: str = ""
    password: str = ""
    certificate_path: str = ""
    auth_type: str = "password"
    split_tunnel: bool = True
    routes: List[str] = []
    dns_servers: List[str] = []
    mtu: int = 1406
    idle_timeout: int = 3600
    reconnect_attempts: int = 3
    reconnect_delay: int = 10
    pre_connect_script: str = ""
    post_connect_script: str = ""
    linked_connector_ids: List[str] = []
    enabled: bool = True


class VPNTunnelUpdate(BaseModel):
    name: Optional[str] = None
    provider: Optional[str] = None
    gateway: Optional[str] = None
    group: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    certificate_path: Optional[str] = None
    auth_type: Optional[str] = None
    split_tunnel: Optional[bool] = None
    routes: Optional[List[str]] = None
    dns_servers: Optional[List[str]] = None
    mtu: Optional[int] = None
    idle_timeout: Optional[int] = None
    reconnect_attempts: Optional[int] = None
    reconnect_delay: Optional[int] = None
    pre_connect_script: Optional[str] = None
    post_connect_script: Optional[str] = None
    linked_connector_ids: Optional[List[str]] = None
    enabled: Optional[bool] = None


# ── Helpers ──────────────────────────────────────────────────────────────────

def _get_tenant_id() -> str:
    from api.middleware.tenant import _current_tenant_id
    return _current_tenant_id.get("")


def _row_to_dict(row: VPNTunnelConfig) -> dict:
    return {
        "id": row.id,
        "tenant_id": row.tenant_id,
        "name": row.name,
        "provider": row.provider,
        "gateway": row.gateway,
        "group": row.group,
        "username": row.username,
        "auth_type": row.auth_type,
        "split_tunnel": row.split_tunnel,
        "routes": row.routes or [],
        "dns_servers": row.dns_servers or [],
        "mtu": row.mtu,
        "idle_timeout": row.idle_timeout,
        "reconnect_attempts": row.reconnect_attempts,
        "reconnect_delay": row.reconnect_delay,
        "linked_connector_ids": row.linked_connector_ids or [],
        "enabled": row.enabled,
        "status": row.status,
        "last_connected_at": row.last_connected_at,
        "last_error": row.last_error,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def _db_to_vpn_config(row: VPNTunnelConfig) -> VPNConfig:
    """Convert DB row to VPNConfig for the tunnel manager."""
    return VPNConfig(
        tunnel_id=row.id,
        name=row.name,
        provider=VPNProvider(row.provider) if row.provider else VPNProvider.CISCO_ANYCONNECT,
        gateway=row.gateway,
        group=row.group or "",
        username=row.username or "",
        password=row.password_encrypted or "",  # decrypted in production
        certificate_path=row.certificate_path or "",
        auth_type=row.auth_type or "password",
        split_tunnel=row.split_tunnel if row.split_tunnel is not None else True,
        routes=row.routes or [],
        dns_servers=row.dns_servers or [],
        mtu=row.mtu or 1406,
        idle_timeout=row.idle_timeout or 3600,
        reconnect_attempts=row.reconnect_attempts or 3,
        reconnect_delay=row.reconnect_delay or 10,
        pre_connect_script=row.pre_connect_script or "",
        post_connect_script=row.post_connect_script or "",
        linked_connector_ids=row.linked_connector_ids or [],
    )


# ── CRUD ─────────────────────────────────────────────────────────────────────

@router.get("/")
def list_tunnels(db: Session = Depends(get_db)):
    tenant_id = _get_tenant_id()
    rows = db.query(VPNTunnelConfig).filter(VPNTunnelConfig.tenant_id == tenant_id).all()

    # Merge live status from tunnel manager
    mgr = VPNTunnelManager.get_instance()
    results = []
    for row in rows:
        d = _row_to_dict(row)
        live = mgr.get_tunnel(row.id)
        if live:
            d["status"] = live.status.value
            d["local_ip"] = live.local_ip
            d["remote_ip"] = live.remote_ip
            d["connected_at"] = live.connected_at.isoformat() if live.connected_at else None
            d["uptime_seconds"] = (
                int((datetime.utcnow() - live.connected_at).total_seconds())
                if live.connected_at else 0
            )
        results.append(d)
    return results


@router.post("/")
def create_tunnel(body: VPNTunnelCreate, db: Session = Depends(get_db)):
    tenant_id = _get_tenant_id()
    row = VPNTunnelConfig(
        tenant_id=tenant_id,
        name=body.name,
        provider=body.provider,
        gateway=body.gateway,
        group=body.group,
        username=body.username,
        password_encrypted=body.password,  # TODO: encrypt with Fernet
        certificate_path=body.certificate_path,
        auth_type=body.auth_type,
        split_tunnel=body.split_tunnel,
        routes=body.routes,
        dns_servers=body.dns_servers,
        mtu=body.mtu,
        idle_timeout=body.idle_timeout,
        reconnect_attempts=body.reconnect_attempts,
        reconnect_delay=body.reconnect_delay,
        pre_connect_script=body.pre_connect_script,
        post_connect_script=body.post_connect_script,
        linked_connector_ids=body.linked_connector_ids,
        enabled=body.enabled,
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    # Register in tunnel manager
    mgr = VPNTunnelManager.get_instance()
    mgr.register_tunnel(_db_to_vpn_config(row))

    return _row_to_dict(row)


@router.get("/{tunnel_id}")
def get_tunnel(tunnel_id: str, db: Session = Depends(get_db)):
    tenant_id = _get_tenant_id()
    row = db.query(VPNTunnelConfig).filter(
        VPNTunnelConfig.id == tunnel_id,
        VPNTunnelConfig.tenant_id == tenant_id,
    ).first()
    if not row:
        raise HTTPException(404, "Tunnel not found")

    d = _row_to_dict(row)
    mgr = VPNTunnelManager.get_instance()
    live = mgr.get_tunnel(tunnel_id)
    if live:
        d["status"] = live.status.value
        d["local_ip"] = live.local_ip
        d["remote_ip"] = live.remote_ip
    return d


@router.put("/{tunnel_id}")
def update_tunnel(tunnel_id: str, body: VPNTunnelUpdate, db: Session = Depends(get_db)):
    tenant_id = _get_tenant_id()
    row = db.query(VPNTunnelConfig).filter(
        VPNTunnelConfig.id == tunnel_id,
        VPNTunnelConfig.tenant_id == tenant_id,
    ).first()
    if not row:
        raise HTTPException(404, "Tunnel not found")

    for field_name, value in body.dict(exclude_unset=True).items():
        if field_name == "password":
            setattr(row, "password_encrypted", value)
        else:
            setattr(row, field_name, value)
    db.commit()
    db.refresh(row)

    # Re-register in tunnel manager
    mgr = VPNTunnelManager.get_instance()
    mgr.register_tunnel(_db_to_vpn_config(row))

    return _row_to_dict(row)


@router.delete("/{tunnel_id}")
def delete_tunnel(tunnel_id: str, db: Session = Depends(get_db)):
    tenant_id = _get_tenant_id()
    row = db.query(VPNTunnelConfig).filter(
        VPNTunnelConfig.id == tunnel_id,
        VPNTunnelConfig.tenant_id == tenant_id,
    ).first()
    if not row:
        raise HTTPException(404, "Tunnel not found")

    mgr = VPNTunnelManager.get_instance()
    mgr.remove_tunnel(tunnel_id)

    db.delete(row)
    db.commit()
    return {"deleted": True, "id": tunnel_id}


# ── Connect / Disconnect / Reconnect ────────────────────────────────────────

@router.post("/{tunnel_id}/connect")
async def connect_tunnel(tunnel_id: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    tenant_id = _get_tenant_id()
    row = db.query(VPNTunnelConfig).filter(
        VPNTunnelConfig.id == tunnel_id,
        VPNTunnelConfig.tenant_id == tenant_id,
    ).first()
    if not row:
        raise HTTPException(404, "Tunnel not found")
    if not row.enabled:
        raise HTTPException(400, "Tunnel is disabled")

    mgr = VPNTunnelManager.get_instance()

    # Ensure config is registered
    if not mgr.get_tunnel(tunnel_id):
        mgr.register_tunnel(_db_to_vpn_config(row))

    try:
        result = await mgr.connect(tunnel_id)

        # Update DB status
        row.status = "connected"
        row.last_connected_at = datetime.utcnow().isoformat()
        row.last_error = ""
        db.commit()

        return result
    except Exception as e:
        row.status = "error"
        row.last_error = str(e)
        db.commit()
        raise HTTPException(500, f"VPN connect failed: {e}")


@router.post("/{tunnel_id}/disconnect")
async def disconnect_tunnel(tunnel_id: str, db: Session = Depends(get_db)):
    tenant_id = _get_tenant_id()
    row = db.query(VPNTunnelConfig).filter(
        VPNTunnelConfig.id == tunnel_id,
        VPNTunnelConfig.tenant_id == tenant_id,
    ).first()
    if not row:
        raise HTTPException(404, "Tunnel not found")

    mgr = VPNTunnelManager.get_instance()
    try:
        result = await mgr.disconnect(tunnel_id)
        row.status = "disconnected"
        row.last_error = ""
        db.commit()
        return result
    except Exception as e:
        raise HTTPException(500, f"VPN disconnect failed: {e}")


@router.post("/{tunnel_id}/reconnect")
async def reconnect_tunnel(tunnel_id: str, db: Session = Depends(get_db)):
    tenant_id = _get_tenant_id()
    row = db.query(VPNTunnelConfig).filter(
        VPNTunnelConfig.id == tunnel_id,
        VPNTunnelConfig.tenant_id == tenant_id,
    ).first()
    if not row:
        raise HTTPException(404, "Tunnel not found")

    mgr = VPNTunnelManager.get_instance()
    if not mgr.get_tunnel(tunnel_id):
        mgr.register_tunnel(_db_to_vpn_config(row))

    try:
        result = await mgr.reconnect(tunnel_id)
        row.status = "connected"
        row.last_connected_at = datetime.utcnow().isoformat()
        row.last_error = ""
        db.commit()
        return result
    except Exception as e:
        row.status = "error"
        row.last_error = str(e)
        db.commit()
        raise HTTPException(500, f"VPN reconnect failed: {e}")


# ── Status & Health ──────────────────────────────────────────────────────────

@router.get("/status/anyconnect")
async def anyconnect_status():
    """Check Cisco AnyConnect CLI status on the server."""
    mgr = VPNTunnelManager.get_instance()
    return await mgr.get_anyconnect_status()


@router.get("/status/all")
def all_tunnels_status():
    """Get live status of all registered tunnels."""
    mgr = VPNTunnelManager.get_instance()
    return mgr.list_tunnels()


@router.post("/{tunnel_id}/test")
async def test_tunnel_connectivity(tunnel_id: str, db: Session = Depends(get_db)):
    """Test if the VPN gateway is reachable (ping)."""
    tenant_id = _get_tenant_id()
    row = db.query(VPNTunnelConfig).filter(
        VPNTunnelConfig.id == tunnel_id,
        VPNTunnelConfig.tenant_id == tenant_id,
    ).first()
    if not row:
        raise HTTPException(404, "Tunnel not found")

    mgr = VPNTunnelManager.get_instance()
    reachable = await mgr._ping_gateway(row.gateway)
    return {
        "tunnel_id": tunnel_id,
        "gateway": row.gateway,
        "reachable": reachable,
    }
