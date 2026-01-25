"""
GRC Connectors - Base Classes

Abstract base classes and factory for system connectors.
Supports SAP, Azure AD, AWS IAM, and custom REST APIs.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class ConnectionType(Enum):
    """Supported connection types"""
    RFC = "rfc"          # SAP RFC (pyrfc)
    DATABASE = "db"       # Direct database
    REST = "rest"         # REST/OData API
    SOAP = "soap"         # SOAP/Web Services
    LDAP = "ldap"         # LDAP/Active Directory


@dataclass
class ConnectionConfig:
    """Configuration for system connections"""
    name: str
    connection_type: ConnectionType
    host: str
    port: int = 443

    # Authentication
    username: Optional[str] = None
    password: Optional[str] = None
    api_key: Optional[str] = None
    oauth_client_id: Optional[str] = None
    oauth_client_secret: Optional[str] = None
    certificate_path: Optional[str] = None

    # SAP-specific
    sap_client: Optional[str] = None
    sap_sysnr: Optional[str] = "00"
    sap_language: str = "EN"

    # Connection pool
    pool_size: int = 5
    timeout: int = 30

    # SSL/TLS
    verify_ssl: bool = True

    # Additional parameters
    extra_params: Dict[str, Any] = field(default_factory=dict)


class BaseConnector(ABC):
    """
    Abstract base class for all system connectors.

    Implement this for each system you need to connect to.
    """

    def __init__(self, config: ConnectionConfig):
        self.config = config
        self.connection = None
        self.connected = False
        self._connection_pool = []

    @abstractmethod
    def connect(self) -> bool:
        """Establish connection to the system"""
        pass

    @abstractmethod
    def disconnect(self) -> bool:
        """Close the connection"""
        pass

    @abstractmethod
    def test_connection(self) -> Dict[str, Any]:
        """Test the connection and return status"""
        pass

    @abstractmethod
    def get_users(self, filters: Optional[Dict] = None) -> List[Dict]:
        """Get list of users from the system"""
        pass

    @abstractmethod
    def get_user_details(self, user_id: str) -> Dict:
        """Get detailed user information including roles/permissions"""
        pass

    @abstractmethod
    def get_roles(self, filters: Optional[Dict] = None) -> List[Dict]:
        """Get list of roles/profiles from the system"""
        pass

    @abstractmethod
    def get_role_details(self, role_id: str) -> Dict:
        """Get detailed role information including permissions"""
        pass

    @abstractmethod
    def get_user_entitlements(self, user_id: str) -> List[Dict]:
        """Get all entitlements/authorizations for a user"""
        pass

    def health_check(self) -> Dict[str, Any]:
        """Perform health check on the connection"""
        try:
            result = self.test_connection()
            return {
                "status": "healthy",
                "system": self.config.name,
                "connection_type": self.config.connection_type.value,
                "details": result
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "system": self.config.name,
                "error": str(e)
            }


class ConnectorFactory:
    """Factory for creating system connectors"""

    _connectors: Dict[str, type] = {}

    @classmethod
    def register(cls, system_type: str, connector_class: type):
        """Register a connector class for a system type"""
        cls._connectors[system_type.lower()] = connector_class

    @classmethod
    def create(cls, system_type: str, config: ConnectionConfig) -> BaseConnector:
        """Create a connector instance"""
        connector_class = cls._connectors.get(system_type.lower())
        if not connector_class:
            raise ValueError(f"Unknown system type: {system_type}. "
                           f"Available: {list(cls._connectors.keys())}")
        return connector_class(config)

    @classmethod
    def available_connectors(cls) -> List[str]:
        """List available connector types"""
        return list(cls._connectors.keys())
