"""
VPN Tunnel Configuration Model
"""
import uuid
from sqlalchemy import Column, String, Integer, Boolean, JSON, Text
from .base import Base, TimestampMixin


class VPNTunnelConfig(Base, TimestampMixin):
    __tablename__ = "vpn_tunnel_configs"

    id = Column(String(50), primary_key=True, default=lambda: str(uuid.uuid4())[:12])
    tenant_id = Column(String(100), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    provider = Column(String(50), nullable=False, default="cisco_anyconnect")
    gateway = Column(String(255), nullable=False)
    group = Column(String(200), default="")
    username = Column(String(200), default="")
    password_encrypted = Column(Text, default="")
    certificate_path = Column(String(500), default="")
    auth_type = Column(String(50), default="password")
    split_tunnel = Column(Boolean, default=True)
    routes = Column(JSON, default=list)
    dns_servers = Column(JSON, default=list)
    mtu = Column(Integer, default=1406)
    idle_timeout = Column(Integer, default=3600)
    reconnect_attempts = Column(Integer, default=3)
    reconnect_delay = Column(Integer, default=10)
    pre_connect_script = Column(Text, default="")
    post_connect_script = Column(Text, default="")
    linked_connector_ids = Column(JSON, default=list)
    enabled = Column(Boolean, default=True)
    status = Column(String(50), default="disconnected")
    last_connected_at = Column(String(50), default="")
    last_error = Column(Text, default="")
