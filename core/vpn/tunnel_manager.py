"""
VPN Tunnel Manager for GovernexPlus
====================================
Manages Cisco AnyConnect VPN tunnels required for SAP RFC connectivity.

Supports:
- Cisco AnyConnect CLI (vpncli / anyconnect)
- OpenConnect (open-source alternative)
- Per-connector VPN profiles
- Auto-connect before SAP operations
- Health monitoring and auto-reconnect
- Encrypted credential storage

Usage:
    manager = VPNTunnelManager()
    await manager.connect("sap-prod-vpn")
    # ... SAP RFC operations ...
    await manager.disconnect("sap-prod-vpn")
"""

import asyncio
import logging
import os
import platform
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


class VPNStatus(str, Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    DISCONNECTING = "disconnecting"
    ERROR = "error"
    RECONNECTING = "reconnecting"


class VPNProvider(str, Enum):
    CISCO_ANYCONNECT = "cisco_anyconnect"
    OPENCONNECT = "openconnect"
    IPSEC = "ipsec"


@dataclass
class VPNConfig:
    """VPN tunnel configuration."""
    tunnel_id: str
    name: str
    provider: VPNProvider = VPNProvider.CISCO_ANYCONNECT
    gateway: str = ""                   # VPN gateway hostname/IP
    group: str = ""                     # VPN group/profile name
    username: str = ""
    password: str = ""                  # encrypted at rest in DB
    certificate_path: str = ""          # client cert path (optional)
    auth_type: str = "password"         # password | certificate | totp
    totp_secret: str = ""              # for 2FA
    split_tunnel: bool = True           # only route SAP traffic
    routes: List[str] = field(default_factory=list)  # manual routes for split tunnel
    dns_servers: List[str] = field(default_factory=list)
    mtu: int = 1406
    idle_timeout: int = 3600            # seconds before auto-disconnect
    reconnect_attempts: int = 3
    reconnect_delay: int = 10           # seconds between retries
    pre_connect_script: str = ""        # script to run before connecting
    post_connect_script: str = ""       # script to run after connecting
    linked_connector_ids: List[str] = field(default_factory=list)  # SAP connectors that need this VPN


class VPNTunnel:
    """Represents a live VPN tunnel instance."""

    def __init__(self, config: VPNConfig):
        self.config = config
        self.status = VPNStatus.DISCONNECTED
        self.connected_at: Optional[datetime] = None
        self.local_ip: Optional[str] = None
        self.remote_ip: Optional[str] = None
        self.bytes_sent: int = 0
        self.bytes_received: int = 0
        self.last_error: Optional[str] = None
        self.pid: Optional[int] = None
        self._process: Optional[asyncio.subprocess.Process] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tunnel_id": self.config.tunnel_id,
            "name": self.config.name,
            "provider": self.config.provider.value,
            "gateway": self.config.gateway,
            "group": self.config.group,
            "status": self.status.value,
            "connected_at": self.connected_at.isoformat() if self.connected_at else None,
            "local_ip": self.local_ip,
            "remote_ip": self.remote_ip,
            "bytes_sent": self.bytes_sent,
            "bytes_received": self.bytes_received,
            "last_error": self.last_error,
            "pid": self.pid,
            "linked_connectors": self.config.linked_connector_ids,
            "uptime_seconds": (
                int((datetime.utcnow() - self.connected_at).total_seconds())
                if self.connected_at else 0
            ),
        }


class VPNTunnelManager:
    """
    Manages VPN tunnel lifecycle for all configured tunnels.

    Singleton per process — call get_instance() or instantiate directly.
    """

    _instance: Optional["VPNTunnelManager"] = None

    def __init__(self):
        self._tunnels: Dict[str, VPNTunnel] = {}
        self._configs: Dict[str, VPNConfig] = {}
        self._health_tasks: Dict[str, asyncio.Task] = {}
        self._lock = asyncio.Lock()

    @classmethod
    def get_instance(cls) -> "VPNTunnelManager":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # ── Config Management ────────────────────────────────────────────────────

    def register_tunnel(self, config: VPNConfig):
        """Register a VPN tunnel configuration."""
        self._configs[config.tunnel_id] = config
        if config.tunnel_id not in self._tunnels:
            self._tunnels[config.tunnel_id] = VPNTunnel(config)
        logger.info(f"Registered VPN tunnel: {config.name} ({config.tunnel_id})")

    def remove_tunnel(self, tunnel_id: str):
        """Unregister a VPN tunnel."""
        self._configs.pop(tunnel_id, None)
        tunnel = self._tunnels.pop(tunnel_id, None)
        health_task = self._health_tasks.pop(tunnel_id, None)
        if health_task:
            health_task.cancel()
        logger.info(f"Removed VPN tunnel: {tunnel_id}")

    def get_tunnel(self, tunnel_id: str) -> Optional[VPNTunnel]:
        return self._tunnels.get(tunnel_id)

    def list_tunnels(self) -> List[Dict]:
        return [t.to_dict() for t in self._tunnels.values()]

    # ── Connection Lifecycle ─────────────────────────────────────────────────

    async def connect(self, tunnel_id: str) -> Dict:
        """Establish a VPN tunnel."""
        async with self._lock:
            tunnel = self._tunnels.get(tunnel_id)
            if not tunnel:
                raise ValueError(f"Unknown tunnel: {tunnel_id}")

            if tunnel.status == VPNStatus.CONNECTED:
                return tunnel.to_dict()

            tunnel.status = VPNStatus.CONNECTING
            tunnel.last_error = None
            config = tunnel.config

            for attempt in range(1, config.reconnect_attempts + 1):
                try:
                    logger.info(
                        f"Connecting VPN {config.name} → {config.gateway} "
                        f"(attempt {attempt}/{config.reconnect_attempts})"
                    )

                    # Run pre-connect script
                    if config.pre_connect_script:
                        await self._run_script(config.pre_connect_script, "pre-connect")

                    # Dispatch to provider
                    if config.provider == VPNProvider.CISCO_ANYCONNECT:
                        result = await self._connect_anyconnect(tunnel)
                    elif config.provider == VPNProvider.OPENCONNECT:
                        result = await self._connect_openconnect(tunnel)
                    else:
                        raise ValueError(f"Unsupported provider: {config.provider}")

                    tunnel.status = VPNStatus.CONNECTED
                    tunnel.connected_at = datetime.utcnow()
                    tunnel.local_ip = result.get("local_ip")
                    tunnel.remote_ip = result.get("remote_ip")
                    tunnel.pid = result.get("pid")

                    # Run post-connect script
                    if config.post_connect_script:
                        await self._run_script(config.post_connect_script, "post-connect")

                    # Add split-tunnel routes
                    if config.split_tunnel and config.routes:
                        await self._add_routes(config.routes)

                    # Start health monitor
                    self._start_health_monitor(tunnel_id)

                    logger.info(
                        f"VPN {config.name} connected. "
                        f"Local IP: {tunnel.local_ip}, Remote: {tunnel.remote_ip}"
                    )
                    return tunnel.to_dict()

                except Exception as e:
                    tunnel.last_error = str(e)
                    logger.warning(f"VPN connect attempt {attempt} failed: {e}")
                    if attempt < config.reconnect_attempts:
                        await asyncio.sleep(config.reconnect_delay)

            tunnel.status = VPNStatus.ERROR
            raise ConnectionError(
                f"Failed to connect VPN {config.name} after "
                f"{config.reconnect_attempts} attempts: {tunnel.last_error}"
            )

    async def disconnect(self, tunnel_id: str) -> Dict:
        """Tear down a VPN tunnel."""
        async with self._lock:
            tunnel = self._tunnels.get(tunnel_id)
            if not tunnel:
                raise ValueError(f"Unknown tunnel: {tunnel_id}")

            if tunnel.status == VPNStatus.DISCONNECTED:
                return tunnel.to_dict()

            tunnel.status = VPNStatus.DISCONNECTING

            # Stop health monitor
            health_task = self._health_tasks.pop(tunnel_id, None)
            if health_task:
                health_task.cancel()

            try:
                config = tunnel.config
                if config.provider == VPNProvider.CISCO_ANYCONNECT:
                    await self._disconnect_anyconnect(tunnel)
                elif config.provider == VPNProvider.OPENCONNECT:
                    await self._disconnect_openconnect(tunnel)

                # Remove split-tunnel routes
                if config.split_tunnel and config.routes:
                    await self._remove_routes(config.routes)

            except Exception as e:
                logger.error(f"Error disconnecting VPN {config.name}: {e}")
            finally:
                tunnel.status = VPNStatus.DISCONNECTED
                tunnel.connected_at = None
                tunnel.local_ip = None
                tunnel.remote_ip = None
                tunnel.pid = None

            logger.info(f"VPN {tunnel.config.name} disconnected")
            return tunnel.to_dict()

    async def reconnect(self, tunnel_id: str) -> Dict:
        """Reconnect a VPN tunnel."""
        tunnel = self._tunnels.get(tunnel_id)
        if tunnel:
            tunnel.status = VPNStatus.RECONNECTING
        await self.disconnect(tunnel_id)
        return await self.connect(tunnel_id)

    async def ensure_connected(self, tunnel_id: str) -> bool:
        """Ensure tunnel is connected; connect if not. Returns True if connected."""
        tunnel = self._tunnels.get(tunnel_id)
        if not tunnel:
            return False
        if tunnel.status == VPNStatus.CONNECTED:
            return True
        try:
            await self.connect(tunnel_id)
            return True
        except Exception:
            return False

    async def ensure_connected_for_connector(self, connector_id: str) -> bool:
        """Find and connect the VPN tunnel linked to a connector."""
        for tid, config in self._configs.items():
            if connector_id in config.linked_connector_ids:
                return await self.ensure_connected(tid)
        # No VPN required for this connector
        return True

    # ── Provider Implementations ─────────────────────────────────────────────

    async def _connect_anyconnect(self, tunnel: VPNTunnel) -> Dict:
        """Connect using Cisco AnyConnect CLI."""
        config = tunnel.config
        vpncli = self._find_anyconnect_cli()

        # Build the connect command with stdin piping for credentials
        # AnyConnect CLI expects interactive input:
        #   connect <gateway>
        #   <group_index_or_name>
        #   <username>
        #   <password>
        #   y  (accept banner)
        stdin_lines = [
            f"connect {config.gateway}",
        ]
        if config.group:
            stdin_lines.append(config.group)
        stdin_lines.append(config.username)
        stdin_lines.append(config.password)
        stdin_lines.append("y")  # accept certificate/banner

        stdin_data = "\n".join(stdin_lines) + "\n"

        proc = await asyncio.create_subprocess_exec(
            vpncli, "-s",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(input=stdin_data.encode()),
            timeout=60,
        )

        output = stdout.decode(errors="replace")
        err_output = stderr.decode(errors="replace")

        if proc.returncode != 0:
            raise ConnectionError(
                f"AnyConnect connect failed (rc={proc.returncode}): "
                f"{err_output or output}"
            )

        # Parse output for IP addresses
        local_ip = self._parse_field(output, "Client Address")
        remote_ip = config.gateway

        return {"local_ip": local_ip, "remote_ip": remote_ip, "pid": proc.pid}

    async def _disconnect_anyconnect(self, tunnel: VPNTunnel):
        """Disconnect Cisco AnyConnect."""
        vpncli = self._find_anyconnect_cli()
        proc = await asyncio.create_subprocess_exec(
            vpncli, "-s",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await asyncio.wait_for(
            proc.communicate(input=b"disconnect\n"),
            timeout=30,
        )

    async def _connect_openconnect(self, tunnel: VPNTunnel) -> Dict:
        """Connect using openconnect (open-source Cisco VPN client)."""
        config = tunnel.config

        cmd = [
            "openconnect",
            "--background",
            "--protocol=anyconnect",
            f"--user={config.username}",
            f"--passwd-on-stdin",
        ]
        if config.certificate_path:
            cmd.append(f"--certificate={config.certificate_path}")
        if config.group:
            cmd.append(f"--authgroup={config.group}")
        if config.mtu:
            cmd.append(f"--mtu={config.mtu}")
        cmd.append(config.gateway)

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(input=f"{config.password}\n".encode()),
            timeout=60,
        )

        output = stdout.decode(errors="replace")
        if proc.returncode not in (0, None):
            raise ConnectionError(
                f"openconnect failed (rc={proc.returncode}): "
                f"{stderr.decode(errors='replace') or output}"
            )

        local_ip = self._parse_field(output, "Connected as")
        return {"local_ip": local_ip, "remote_ip": config.gateway, "pid": proc.pid}

    async def _disconnect_openconnect(self, tunnel: VPNTunnel):
        """Disconnect openconnect by sending SIGINT to the background process."""
        if tunnel.pid:
            try:
                os.kill(tunnel.pid, 2)  # SIGINT
            except ProcessLookupError:
                pass

    # ── Health Monitoring ────────────────────────────────────────────────────

    def _start_health_monitor(self, tunnel_id: str):
        """Start background health check for a tunnel."""
        old_task = self._health_tasks.pop(tunnel_id, None)
        if old_task:
            old_task.cancel()

        async def _monitor():
            while True:
                await asyncio.sleep(30)  # check every 30s
                tunnel = self._tunnels.get(tunnel_id)
                if not tunnel or tunnel.status != VPNStatus.CONNECTED:
                    break
                try:
                    alive = await self._ping_gateway(tunnel.config.gateway)
                    if not alive:
                        logger.warning(f"VPN {tunnel.config.name} health check failed, reconnecting")
                        tunnel.status = VPNStatus.RECONNECTING
                        try:
                            await self.reconnect(tunnel_id)
                        except Exception as e:
                            logger.error(f"VPN auto-reconnect failed: {e}")
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Health monitor error: {e}")

        self._health_tasks[tunnel_id] = asyncio.create_task(_monitor())

    async def _ping_gateway(self, gateway: str) -> bool:
        """Ping the VPN gateway to verify connectivity."""
        is_win = platform.system().lower() == "windows"
        ping_cmd = ["ping", "-n" if is_win else "-c", "1", "-w", "3" if is_win else "3", gateway]
        try:
            proc = await asyncio.create_subprocess_exec(
                *ping_cmd,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await asyncio.wait_for(proc.wait(), timeout=10)
            return proc.returncode == 0
        except Exception:
            return False

    # ── Route Management ─────────────────────────────────────────────────────

    async def _add_routes(self, routes: List[str]):
        """Add static routes for split tunneling."""
        is_win = platform.system().lower() == "windows"
        for route in routes:
            try:
                if is_win:
                    cmd = ["route", "add", route, "mask", "255.255.255.0", "0.0.0.0"]
                else:
                    cmd = ["ip", "route", "add", f"{route}/24", "dev", "tun0"]
                proc = await asyncio.create_subprocess_exec(
                    *cmd, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL,
                )
                await proc.wait()
            except Exception as e:
                logger.warning(f"Failed to add route {route}: {e}")

    async def _remove_routes(self, routes: List[str]):
        """Remove split-tunnel routes."""
        is_win = platform.system().lower() == "windows"
        for route in routes:
            try:
                if is_win:
                    cmd = ["route", "delete", route]
                else:
                    cmd = ["ip", "route", "del", f"{route}/24", "dev", "tun0"]
                proc = await asyncio.create_subprocess_exec(
                    *cmd, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL,
                )
                await proc.wait()
            except Exception as e:
                logger.warning(f"Failed to remove route {route}: {e}")

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _find_anyconnect_cli(self) -> str:
        """Locate the Cisco AnyConnect CLI binary."""
        candidates = []
        if platform.system().lower() == "windows":
            candidates = [
                r"C:\Program Files (x86)\Cisco\Cisco AnyConnect Secure Mobility Client\vpncli.exe",
                r"C:\Program Files\Cisco\Cisco AnyConnect Secure Mobility Client\vpncli.exe",
                r"C:\Program Files (x86)\Cisco\Cisco Secure Client\vpncli.exe",
                r"C:\Program Files\Cisco\Cisco Secure Client\vpncli.exe",
            ]
        else:
            candidates = [
                "/opt/cisco/anyconnect/bin/vpn",
                "/opt/cisco/secureclient/bin/vpn",
                "/usr/local/bin/vpn",
            ]

        for path in candidates:
            if os.path.isfile(path):
                return path

        # Try PATH
        which = shutil.which("vpncli") or shutil.which("vpn")
        if which:
            return which

        raise FileNotFoundError(
            "Cisco AnyConnect CLI not found. Install AnyConnect or set path manually."
        )

    @staticmethod
    def _parse_field(output: str, field_name: str) -> Optional[str]:
        """Parse a field from CLI output like 'Client Address: 10.0.1.5'."""
        for line in output.splitlines():
            if field_name in line:
                parts = line.split(":", 1)
                if len(parts) == 2:
                    return parts[1].strip()
        return None

    async def _run_script(self, script: str, label: str):
        """Run a pre/post connect script."""
        try:
            proc = await asyncio.create_subprocess_shell(
                script,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
            if proc.returncode != 0:
                logger.warning(f"{label} script failed: {stderr.decode(errors='replace')}")
            else:
                logger.info(f"{label} script completed successfully")
        except Exception as e:
            logger.warning(f"{label} script error: {e}")

    # ── Status ───────────────────────────────────────────────────────────────

    async def get_anyconnect_status(self) -> Dict:
        """Get the current AnyConnect connection status from CLI."""
        try:
            vpncli = self._find_anyconnect_cli()
            proc = await asyncio.create_subprocess_exec(
                vpncli, "-s",
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(
                proc.communicate(input=b"state\nquit\n"),
                timeout=15,
            )
            output = stdout.decode(errors="replace")
            connected = "Connected" in output and "Disconnected" not in output
            return {
                "anyconnect_installed": True,
                "connected": connected,
                "raw_status": output.strip(),
            }
        except FileNotFoundError:
            return {"anyconnect_installed": False, "connected": False, "raw_status": "CLI not found"}
        except Exception as e:
            return {"anyconnect_installed": True, "connected": False, "raw_status": str(e)}
