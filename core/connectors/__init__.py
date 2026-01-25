"""
System Connectors Module

Provides connectivity to various enterprise systems:
- SAP ECC/S4HANA (via RFC/BAPI)
- Cloud platforms (AWS IAM, Azure AD)
- HR Systems (Workday, SuccessFactors)
- Databases (Oracle, SQL Server)
- Identity Providers (Okta, Ping)
"""

from .base import BaseConnector, ConnectorConfig, ConnectionStatus, ConnectorError
from .sap_connector import SAPConnector, SAPConfig, SAPConnectionPool
from .cloud_connectors import AWSIAMConnector, AzureADConnector, AWSConfig, AzureConfig
from .hr_connectors import WorkdayConnector, SuccessFactorsConnector, WorkdayConfig, SuccessFactorsConfig
from .connector_factory import ConnectorFactory, connector_registry, connector_factory

__all__ = [
    # Base
    "BaseConnector",
    "ConnectorConfig",
    "ConnectionStatus",
    "ConnectorError",
    # SAP
    "SAPConnector",
    "SAPConfig",
    "SAPConnectionPool",
    # Cloud
    "AWSIAMConnector",
    "AzureADConnector",
    "AWSConfig",
    "AzureConfig",
    # HR
    "WorkdayConnector",
    "SuccessFactorsConnector",
    "WorkdayConfig",
    "SuccessFactorsConfig",
    # Factory
    "ConnectorFactory",
    "connector_registry",
    "connector_factory",
]
