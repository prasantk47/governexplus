"""
Base Connector Classes

Abstract base classes and interfaces for all system connectors.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
from enum import Enum
import logging
import asyncio
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)


class ConnectionStatus(Enum):
    """Connection status states"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"
    RECONNECTING = "reconnecting"


class ConnectorError(Exception):
    """Base exception for connector errors"""
    def __init__(self, message: str, code: str = "UNKNOWN", details: Optional[Dict] = None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}
        self.timestamp = datetime.now()

    def to_dict(self) -> Dict:
        return {
            "error": self.message,
            "code": self.code,
            "details": self.details,
            "timestamp": self.timestamp.isoformat()
        }


class AuthenticationError(ConnectorError):
    """Authentication failed"""
    def __init__(self, message: str, details: Optional[Dict] = None):
        super().__init__(message, "AUTH_FAILED", details)


class ConnectionError(ConnectorError):
    """Connection failed"""
    def __init__(self, message: str, details: Optional[Dict] = None):
        super().__init__(message, "CONNECTION_FAILED", details)


class OperationError(ConnectorError):
    """Operation execution failed"""
    def __init__(self, message: str, operation: str, details: Optional[Dict] = None):
        super().__init__(message, "OPERATION_FAILED", {"operation": operation, **(details or {})})


@dataclass
class ConnectorConfig:
    """Base configuration for all connectors"""
    connector_id: str
    name: str
    system_type: str
    host: str
    port: Optional[int] = None
    username: str = ""
    password: str = ""

    # Connection settings
    timeout: int = 30  # seconds
    max_retries: int = 3
    retry_delay: int = 5  # seconds
    pool_size: int = 5

    # SSL/TLS
    use_ssl: bool = True
    verify_ssl: bool = True
    cert_path: Optional[str] = None

    # Additional settings
    extra_config: Dict[str, Any] = field(default_factory=dict)

    # Status
    enabled: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    last_modified: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict:
        return {
            "connector_id": self.connector_id,
            "name": self.name,
            "system_type": self.system_type,
            "host": self.host,
            "port": self.port,
            "username": self.username,
            "timeout": self.timeout,
            "max_retries": self.max_retries,
            "pool_size": self.pool_size,
            "use_ssl": self.use_ssl,
            "enabled": self.enabled,
            "extra_config": self.extra_config
        }


@dataclass
class OperationResult:
    """Result of a connector operation"""
    success: bool
    operation: str
    data: Optional[Dict] = None
    error: Optional[str] = None
    error_code: Optional[str] = None
    duration_ms: float = 0
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict:
        return {
            "success": self.success,
            "operation": self.operation,
            "data": self.data,
            "error": self.error,
            "error_code": self.error_code,
            "duration_ms": self.duration_ms,
            "timestamp": self.timestamp.isoformat()
        }


class BaseConnector(ABC):
    """
    Abstract base class for all system connectors.

    Provides common functionality:
    - Connection lifecycle management
    - Retry logic
    - Error handling
    - Logging
    - Metrics collection
    """

    def __init__(self, config: ConnectorConfig):
        self.config = config
        self.status = ConnectionStatus.DISCONNECTED
        self._connection = None
        self._last_error: Optional[ConnectorError] = None
        self._connected_at: Optional[datetime] = None
        self._operation_count = 0
        self._error_count = 0
        self._callbacks: Dict[str, List[Callable]] = {
            "on_connect": [],
            "on_disconnect": [],
            "on_error": [],
            "on_operation": []
        }

    @property
    def is_connected(self) -> bool:
        return self.status == ConnectionStatus.CONNECTED

    @property
    def connector_id(self) -> str:
        return self.config.connector_id

    @property
    def system_type(self) -> str:
        return self.config.system_type

    def register_callback(self, event: str, callback: Callable):
        """Register a callback for connector events"""
        if event in self._callbacks:
            self._callbacks[event].append(callback)

    def _trigger_callbacks(self, event: str, *args, **kwargs):
        """Trigger registered callbacks"""
        for callback in self._callbacks.get(event, []):
            try:
                callback(*args, **kwargs)
            except Exception as e:
                logger.error(f"Callback error for {event}: {e}")

    async def connect(self) -> bool:
        """
        Establish connection to the target system.
        Implements retry logic.
        """
        if self.is_connected:
            return True

        self.status = ConnectionStatus.CONNECTING
        last_error = None

        for attempt in range(self.config.max_retries):
            try:
                logger.info(f"Connecting to {self.config.name} (attempt {attempt + 1}/{self.config.max_retries})")

                # Call implementation-specific connect
                await self._do_connect()

                self.status = ConnectionStatus.CONNECTED
                self._connected_at = datetime.now()
                self._last_error = None

                logger.info(f"Successfully connected to {self.config.name}")
                self._trigger_callbacks("on_connect", self)

                return True

            except Exception as e:
                last_error = e
                self._error_count += 1
                logger.warning(f"Connection attempt {attempt + 1} failed: {e}")

                if attempt < self.config.max_retries - 1:
                    await asyncio.sleep(self.config.retry_delay)

        # All attempts failed
        self.status = ConnectionStatus.ERROR
        self._last_error = ConnectorError(str(last_error), "CONNECTION_FAILED")
        self._trigger_callbacks("on_error", self, self._last_error)

        raise ConnectionError(f"Failed to connect after {self.config.max_retries} attempts: {last_error}")

    async def disconnect(self):
        """Disconnect from the target system"""
        if not self.is_connected:
            return

        try:
            await self._do_disconnect()
            logger.info(f"Disconnected from {self.config.name}")
        except Exception as e:
            logger.error(f"Error during disconnect: {e}")
        finally:
            self.status = ConnectionStatus.DISCONNECTED
            self._connection = None
            self._trigger_callbacks("on_disconnect", self)

    async def reconnect(self) -> bool:
        """Reconnect to the target system"""
        self.status = ConnectionStatus.RECONNECTING
        await self.disconnect()
        return await self.connect()

    async def test_connection(self) -> OperationResult:
        """Test the connection to the target system"""
        start_time = datetime.now()

        try:
            if not self.is_connected:
                await self.connect()

            # Call implementation-specific test
            result = await self._do_test_connection()

            duration = (datetime.now() - start_time).total_seconds() * 1000

            return OperationResult(
                success=True,
                operation="test_connection",
                data=result,
                duration_ms=duration
            )

        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds() * 1000
            return OperationResult(
                success=False,
                operation="test_connection",
                error=str(e),
                error_code="TEST_FAILED",
                duration_ms=duration
            )

    async def execute(self, operation: str, **params) -> OperationResult:
        """
        Execute an operation on the target system.

        Args:
            operation: The operation name
            **params: Operation parameters

        Returns:
            OperationResult with success/failure and data
        """
        start_time = datetime.now()
        self._operation_count += 1

        try:
            if not self.is_connected:
                await self.connect()

            # Call implementation-specific execute
            result = await self._do_execute(operation, **params)

            duration = (datetime.now() - start_time).total_seconds() * 1000

            op_result = OperationResult(
                success=True,
                operation=operation,
                data=result,
                duration_ms=duration
            )

            self._trigger_callbacks("on_operation", self, op_result)
            return op_result

        except Exception as e:
            self._error_count += 1
            duration = (datetime.now() - start_time).total_seconds() * 1000

            op_result = OperationResult(
                success=False,
                operation=operation,
                error=str(e),
                error_code="OPERATION_FAILED",
                duration_ms=duration
            )

            self._trigger_callbacks("on_error", self, e)
            return op_result

    @asynccontextmanager
    async def session(self):
        """Context manager for connection sessions"""
        try:
            await self.connect()
            yield self
        finally:
            await self.disconnect()

    def get_status(self) -> Dict:
        """Get current connector status"""
        return {
            "connector_id": self.connector_id,
            "name": self.config.name,
            "system_type": self.system_type,
            "status": self.status.value,
            "is_connected": self.is_connected,
            "connected_at": self._connected_at.isoformat() if self._connected_at else None,
            "last_error": self._last_error.to_dict() if self._last_error else None,
            "operation_count": self._operation_count,
            "error_count": self._error_count,
            "enabled": self.config.enabled
        }

    # Abstract methods to be implemented by subclasses

    @abstractmethod
    async def _do_connect(self):
        """Implementation-specific connection logic"""
        pass

    @abstractmethod
    async def _do_disconnect(self):
        """Implementation-specific disconnection logic"""
        pass

    @abstractmethod
    async def _do_test_connection(self) -> Dict:
        """Implementation-specific connection test"""
        pass

    @abstractmethod
    async def _do_execute(self, operation: str, **params) -> Dict:
        """Implementation-specific operation execution"""
        pass

    # User Management Interface (optional, override in subclasses)

    async def get_user(self, user_id: str) -> OperationResult:
        """Get user details"""
        return await self.execute("get_user", user_id=user_id)

    async def create_user(self, user_data: Dict) -> OperationResult:
        """Create a new user"""
        return await self.execute("create_user", user_data=user_data)

    async def update_user(self, user_id: str, user_data: Dict) -> OperationResult:
        """Update user details"""
        return await self.execute("update_user", user_id=user_id, user_data=user_data)

    async def delete_user(self, user_id: str) -> OperationResult:
        """Delete a user"""
        return await self.execute("delete_user", user_id=user_id)

    async def lock_user(self, user_id: str) -> OperationResult:
        """Lock a user account"""
        return await self.execute("lock_user", user_id=user_id)

    async def unlock_user(self, user_id: str) -> OperationResult:
        """Unlock a user account"""
        return await self.execute("unlock_user", user_id=user_id)

    async def reset_password(self, user_id: str, new_password: str) -> OperationResult:
        """Reset user password"""
        return await self.execute("reset_password", user_id=user_id, new_password=new_password)

    async def assign_role(self, user_id: str, role_name: str, valid_from: Optional[datetime] = None, valid_to: Optional[datetime] = None) -> OperationResult:
        """Assign a role to a user"""
        return await self.execute("assign_role", user_id=user_id, role_name=role_name, valid_from=valid_from, valid_to=valid_to)

    async def remove_role(self, user_id: str, role_name: str) -> OperationResult:
        """Remove a role from a user"""
        return await self.execute("remove_role", user_id=user_id, role_name=role_name)

    async def get_user_roles(self, user_id: str) -> OperationResult:
        """Get all roles assigned to a user"""
        return await self.execute("get_user_roles", user_id=user_id)

    async def list_users(self, filters: Optional[Dict] = None) -> OperationResult:
        """List users with optional filters"""
        return await self.execute("list_users", filters=filters or {})

    async def list_roles(self, filters: Optional[Dict] = None) -> OperationResult:
        """List available roles"""
        return await self.execute("list_roles", filters=filters or {})
