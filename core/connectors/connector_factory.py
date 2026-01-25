"""
Connector Factory

Factory pattern for creating and managing system connectors.
Provides a registry for connector types and centralized management.
"""

from typing import Dict, Type, Optional, List, Any
from dataclasses import dataclass, field
from datetime import datetime
import logging
import asyncio

from .base import BaseConnector, ConnectorConfig, ConnectionStatus
from .sap_connector import SAPConnector, SAPConfig
from .cloud_connectors import AWSIAMConnector, AWSConfig, AzureADConnector, AzureConfig
from .hr_connectors import WorkdayConnector, WorkdayConfig, SuccessFactorsConnector, SuccessFactorsConfig

logger = logging.getLogger(__name__)


@dataclass
class ConnectorRegistration:
    """Registration info for a connector type"""
    connector_class: Type[BaseConnector]
    config_class: Type[ConnectorConfig]
    display_name: str
    description: str
    category: str  # sap, cloud, hr, database, identity


class ConnectorRegistry:
    """
    Registry of available connector types.

    Allows registration and lookup of connector implementations.
    """

    def __init__(self):
        self._registry: Dict[str, ConnectorRegistration] = {}
        self._register_defaults()

    def _register_defaults(self):
        """Register built-in connector types"""
        # SAP Connectors
        self.register(
            "sap_ecc",
            SAPConnector,
            SAPConfig,
            "SAP ECC",
            "SAP ERP Central Component (ECC 6.0)",
            "sap"
        )
        self.register(
            "sap_s4hana",
            SAPConnector,
            SAPConfig,
            "SAP S/4HANA",
            "SAP S/4HANA On-Premise",
            "sap"
        )
        self.register(
            "sap_s4hana_cloud",
            SAPConnector,
            SAPConfig,
            "SAP S/4HANA Cloud",
            "SAP S/4HANA Cloud Edition",
            "sap"
        )

        # Cloud Connectors
        self.register(
            "aws_iam",
            AWSIAMConnector,
            AWSConfig,
            "AWS IAM",
            "Amazon Web Services Identity and Access Management",
            "cloud"
        )
        self.register(
            "azure_ad",
            AzureADConnector,
            AzureConfig,
            "Azure AD",
            "Microsoft Azure Active Directory / Entra ID",
            "identity"
        )

        # HR Connectors
        self.register(
            "workday",
            WorkdayConnector,
            WorkdayConfig,
            "Workday",
            "Workday Human Capital Management",
            "hr"
        )
        self.register(
            "successfactors",
            SuccessFactorsConnector,
            SuccessFactorsConfig,
            "SAP SuccessFactors",
            "SAP SuccessFactors Employee Central",
            "hr"
        )

    def register(
        self,
        type_id: str,
        connector_class: Type[BaseConnector],
        config_class: Type[ConnectorConfig],
        display_name: str,
        description: str,
        category: str
    ):
        """Register a new connector type"""
        self._registry[type_id] = ConnectorRegistration(
            connector_class=connector_class,
            config_class=config_class,
            display_name=display_name,
            description=description,
            category=category
        )
        logger.debug(f"Registered connector type: {type_id}")

    def get(self, type_id: str) -> Optional[ConnectorRegistration]:
        """Get a connector registration by type ID"""
        return self._registry.get(type_id)

    def list_types(self) -> List[Dict]:
        """List all registered connector types"""
        return [
            {
                "type_id": type_id,
                "display_name": reg.display_name,
                "description": reg.description,
                "category": reg.category
            }
            for type_id, reg in self._registry.items()
        ]

    def list_by_category(self, category: str) -> List[Dict]:
        """List connector types by category"""
        return [
            {
                "type_id": type_id,
                "display_name": reg.display_name,
                "description": reg.description,
            }
            for type_id, reg in self._registry.items()
            if reg.category == category
        ]


# Global registry instance
connector_registry = ConnectorRegistry()


class ConnectorFactory:
    """
    Factory for creating and managing connector instances.

    Handles connector lifecycle:
    - Creation from configuration
    - Connection pooling
    - Status monitoring
    - Graceful shutdown
    """

    def __init__(self, registry: Optional[ConnectorRegistry] = None):
        self.registry = registry or connector_registry
        self._connectors: Dict[str, BaseConnector] = {}
        self._lock = asyncio.Lock()

    async def create_connector(
        self,
        connector_id: str,
        type_id: str,
        config_dict: Dict[str, Any]
    ) -> BaseConnector:
        """
        Create a new connector instance.

        Args:
            connector_id: Unique identifier for this connector instance
            type_id: The connector type (e.g., 'sap_ecc', 'aws_iam')
            config_dict: Configuration dictionary

        Returns:
            The created connector instance
        """
        registration = self.registry.get(type_id)
        if not registration:
            raise ValueError(f"Unknown connector type: {type_id}")

        # Create config instance
        config_dict["connector_id"] = connector_id
        config_dict["system_type"] = type_id
        config = registration.config_class(**config_dict)

        # Create connector instance
        connector = registration.connector_class(config)

        async with self._lock:
            self._connectors[connector_id] = connector

        logger.info(f"Created connector: {connector_id} (type: {type_id})")
        return connector

    async def get_connector(self, connector_id: str) -> Optional[BaseConnector]:
        """Get a connector by ID"""
        return self._connectors.get(connector_id)

    async def get_or_create(
        self,
        connector_id: str,
        type_id: str,
        config_dict: Dict[str, Any]
    ) -> BaseConnector:
        """Get existing connector or create new one"""
        connector = await self.get_connector(connector_id)
        if connector:
            return connector
        return await self.create_connector(connector_id, type_id, config_dict)

    async def remove_connector(self, connector_id: str) -> bool:
        """Remove and disconnect a connector"""
        async with self._lock:
            connector = self._connectors.pop(connector_id, None)

        if connector:
            try:
                await connector.disconnect()
            except Exception as e:
                logger.error(f"Error disconnecting {connector_id}: {e}")
            logger.info(f"Removed connector: {connector_id}")
            return True
        return False

    async def connect_all(self):
        """Connect all registered connectors"""
        tasks = []
        for connector_id, connector in self._connectors.items():
            if connector.config.enabled and not connector.is_connected:
                tasks.append(self._connect_safe(connector_id, connector))

        if tasks:
            await asyncio.gather(*tasks)

    async def _connect_safe(self, connector_id: str, connector: BaseConnector):
        """Safely connect a single connector"""
        try:
            await connector.connect()
            logger.info(f"Connected: {connector_id}")
        except Exception as e:
            logger.error(f"Failed to connect {connector_id}: {e}")

    async def disconnect_all(self):
        """Disconnect all connectors"""
        tasks = []
        for connector_id, connector in self._connectors.items():
            if connector.is_connected:
                tasks.append(self._disconnect_safe(connector_id, connector))

        if tasks:
            await asyncio.gather(*tasks)

    async def _disconnect_safe(self, connector_id: str, connector: BaseConnector):
        """Safely disconnect a single connector"""
        try:
            await connector.disconnect()
            logger.info(f"Disconnected: {connector_id}")
        except Exception as e:
            logger.error(f"Error disconnecting {connector_id}: {e}")

    def list_connectors(self) -> List[Dict]:
        """List all connector instances with their status"""
        return [
            connector.get_status()
            for connector in self._connectors.values()
        ]

    def get_status(self, connector_id: str) -> Optional[Dict]:
        """Get status of a specific connector"""
        connector = self._connectors.get(connector_id)
        return connector.get_status() if connector else None

    async def test_connection(self, connector_id: str) -> Dict:
        """Test a connector's connection"""
        connector = self._connectors.get(connector_id)
        if not connector:
            return {"success": False, "error": "Connector not found"}

        result = await connector.test_connection()
        return result.to_dict()

    async def execute(self, connector_id: str, operation: str, **params) -> Dict:
        """Execute an operation on a connector"""
        connector = self._connectors.get(connector_id)
        if not connector:
            return {"success": False, "error": "Connector not found"}

        result = await connector.execute(operation, **params)
        return result.to_dict()


# Global factory instance
connector_factory = ConnectorFactory()
