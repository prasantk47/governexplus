"""
Integration Connectors Module

Provides connectivity to external systems including SAP, Active Directory,
Azure AD, and other enterprise applications.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from enum import Enum
from abc import ABC, abstractmethod
import uuid


class ConnectionStatus(Enum):
    """Connection status"""
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"
    TESTING = "testing"
    CONFIGURING = "configuring"


class ConnectorType(Enum):
    """Types of connectors"""
    SAP_RFC = "sap_rfc"
    SAP_ODATA = "sap_odata"
    ACTIVE_DIRECTORY = "active_directory"
    AZURE_AD = "azure_ad"
    OKTA = "okta"
    LDAP = "ldap"
    REST_API = "rest_api"
    DATABASE = "database"
    SERVICENOW = "servicenow"
    CUSTOM = "custom"


class SyncDirection(Enum):
    """Data sync direction"""
    INBOUND = "inbound"      # Pull from external system
    OUTBOUND = "outbound"    # Push to external system
    BIDIRECTIONAL = "bidirectional"


@dataclass
class ConnectorConfig:
    """Configuration for a connector"""
    config_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    connector_type: ConnectorType = ConnectorType.REST_API

    # Connection settings
    host: str = ""
    port: int = 0
    use_ssl: bool = True
    timeout_seconds: int = 30

    # Authentication
    auth_type: str = "basic"  # basic, oauth2, api_key, certificate, kerberos
    username: str = ""
    # password stored securely, not in config
    client_id: str = ""
    tenant_id: str = ""
    certificate_path: str = ""

    # SAP-specific
    system_id: str = ""
    client: str = ""
    language: str = "EN"
    router_string: str = ""

    # Sync settings
    sync_direction: SyncDirection = SyncDirection.INBOUND
    sync_interval_minutes: int = 60
    batch_size: int = 1000

    # Mapping
    field_mappings: Dict[str, str] = field(default_factory=dict)
    filter_criteria: Dict[str, Any] = field(default_factory=dict)

    # Status
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    modified_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict:
        return {
            "config_id": self.config_id,
            "name": self.name,
            "connector_type": self.connector_type.value,
            "host": self.host,
            "port": self.port,
            "use_ssl": self.use_ssl,
            "timeout_seconds": self.timeout_seconds,
            "auth_type": self.auth_type,
            "username": self.username,
            "client_id": self.client_id,
            "tenant_id": self.tenant_id,
            "system_id": self.system_id,
            "client": self.client,
            "language": self.language,
            "sync_direction": self.sync_direction.value,
            "sync_interval_minutes": self.sync_interval_minutes,
            "batch_size": self.batch_size,
            "field_mappings": self.field_mappings,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat(),
            "modified_at": self.modified_at.isoformat()
        }


@dataclass
class SyncJob:
    """A data synchronization job"""
    job_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    connector_id: str = ""
    job_type: str = ""  # full_sync, incremental, users, roles, etc.
    status: str = "pending"  # pending, running, completed, failed
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    records_processed: int = 0
    records_created: int = 0
    records_updated: int = 0
    records_failed: int = 0
    error_message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "job_id": self.job_id,
            "connector_id": self.connector_id,
            "job_type": self.job_type,
            "status": self.status,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "records_processed": self.records_processed,
            "records_created": self.records_created,
            "records_updated": self.records_updated,
            "records_failed": self.records_failed,
            "error_message": self.error_message,
            "details": self.details
        }


class Connector(ABC):
    """Base class for all connectors"""

    def __init__(self, config: ConnectorConfig):
        self.config = config
        self.connector_id = str(uuid.uuid4())[:8]
        self.status = ConnectionStatus.DISCONNECTED
        self.last_connected: Optional[datetime] = None
        self.last_sync: Optional[datetime] = None
        self.error_message: str = ""
        self.sync_jobs: List[SyncJob] = []

    @abstractmethod
    def connect(self) -> bool:
        """Establish connection to the system"""
        pass

    @abstractmethod
    def disconnect(self) -> bool:
        """Close connection"""
        pass

    @abstractmethod
    def test_connection(self) -> Dict:
        """Test the connection"""
        pass

    @abstractmethod
    def get_users(self, filters: Dict = None) -> List[Dict]:
        """Get users from the system"""
        pass

    @abstractmethod
    def get_roles(self, filters: Dict = None) -> List[Dict]:
        """Get roles from the system"""
        pass

    @abstractmethod
    def get_user_roles(self, user_id: str) -> List[Dict]:
        """Get roles assigned to a user"""
        pass

    def get_status(self) -> Dict:
        """Get connector status"""
        return {
            "connector_id": self.connector_id,
            "name": self.config.name,
            "type": self.config.connector_type.value,
            "status": self.status.value,
            "last_connected": self.last_connected.isoformat() if self.last_connected else None,
            "last_sync": self.last_sync.isoformat() if self.last_sync else None,
            "error_message": self.error_message
        }

    def create_sync_job(self, job_type: str) -> SyncJob:
        """Create a new sync job"""
        job = SyncJob(
            connector_id=self.connector_id,
            job_type=job_type
        )
        self.sync_jobs.append(job)
        return job


class SAPConnector(Connector):
    """SAP System Connector (RFC/BAPI)"""

    # Common BAPIs for user/role management
    BAPIS = {
        "user_list": "BAPI_USER_GETLIST",
        "user_detail": "BAPI_USER_GET_DETAIL",
        "role_list": "PRGN_RFC_READ_ROLES",
        "user_roles": "BAPI_USER_GET_DETAIL",
        "auth_check": "AUTHORITY_CHECK"
    }

    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self._connection = None

    def connect(self) -> bool:
        """Connect to SAP system via RFC"""
        try:
            self.status = ConnectionStatus.TESTING
            # In real implementation, would use pyrfc:
            # from pyrfc import Connection
            # self._connection = Connection(
            #     user=self.config.username,
            #     passwd=password,
            #     ashost=self.config.host,
            #     sysnr=str(self.config.port),
            #     client=self.config.client,
            #     lang=self.config.language
            # )

            # Mock successful connection
            self.status = ConnectionStatus.CONNECTED
            self.last_connected = datetime.now()
            self.error_message = ""
            return True

        except Exception as e:
            self.status = ConnectionStatus.ERROR
            self.error_message = str(e)
            return False

    def disconnect(self) -> bool:
        """Disconnect from SAP"""
        self._connection = None
        self.status = ConnectionStatus.DISCONNECTED
        return True

    def test_connection(self) -> Dict:
        """Test SAP connection"""
        result = {
            "success": False,
            "system_info": {},
            "message": ""
        }

        try:
            if self.connect():
                # Would normally call RFC_SYSTEM_INFO
                result["success"] = True
                result["system_info"] = {
                    "system_id": self.config.system_id,
                    "client": self.config.client,
                    "host": self.config.host,
                    "release": "SAP ECC 6.0"  # Mock
                }
                result["message"] = "Connection successful"
        except Exception as e:
            result["message"] = str(e)

        return result

    def get_users(self, filters: Dict = None) -> List[Dict]:
        """Get users from SAP"""
        # Mock data - would use BAPI_USER_GETLIST
        return [
            {
                "user_id": "JSMITH",
                "first_name": "John",
                "last_name": "Smith",
                "email": "jsmith@example.com",
                "department": "Finance",
                "user_type": "Dialog",
                "valid_from": "2020-01-01",
                "valid_to": "9999-12-31",
                "locked": False
            },
            {
                "user_id": "MBROWN",
                "first_name": "Mary",
                "last_name": "Brown",
                "email": "mbrown@example.com",
                "department": "Procurement",
                "user_type": "Dialog",
                "valid_from": "2019-06-15",
                "valid_to": "9999-12-31",
                "locked": False
            }
        ]

    def get_roles(self, filters: Dict = None) -> List[Dict]:
        """Get roles from SAP"""
        # Mock data - would use PRGN_RFC_READ_ROLES
        return [
            {
                "role_id": "Z_FI_AP_CLERK",
                "description": "Accounts Payable Clerk",
                "role_type": "single",
                "composite_roles": [],
                "profiles": ["Z_FI_AP_CLERK_P"]
            },
            {
                "role_id": "Z_MM_PO_CREATE",
                "description": "Purchase Order Creator",
                "role_type": "single",
                "composite_roles": [],
                "profiles": ["Z_MM_PO_P"]
            }
        ]

    def get_user_roles(self, user_id: str) -> List[Dict]:
        """Get roles for a user"""
        # Mock data - would use BAPI_USER_GET_DETAIL
        return [
            {
                "role_id": "Z_FI_AP_CLERK",
                "valid_from": "2020-01-01",
                "valid_to": "9999-12-31",
                "org_levels": {"BUKRS": ["1000", "2000"]}
            }
        ]

    def get_user_authorizations(self, user_id: str) -> List[Dict]:
        """Get detailed authorizations for a user"""
        # Mock data
        return [
            {
                "auth_object": "F_BKPF_BUK",
                "field": "BUKRS",
                "values": ["1000", "2000"],
                "activity": ["01", "02", "03"]
            },
            {
                "auth_object": "S_TCODE",
                "field": "TCD",
                "values": ["FB01", "FB02", "FB03", "F110"]
            }
        ]

    def sync_users(self) -> SyncJob:
        """Sync users from SAP"""
        job = self.create_sync_job("users")
        job.status = "running"
        job.started_at = datetime.now()

        try:
            users = self.get_users()
            job.records_processed = len(users)
            job.records_created = len(users)  # Simplified
            job.status = "completed"
        except Exception as e:
            job.status = "failed"
            job.error_message = str(e)

        job.completed_at = datetime.now()
        self.last_sync = datetime.now()
        return job


class ActiveDirectoryConnector(Connector):
    """Active Directory Connector"""

    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self._connection = None

    def connect(self) -> bool:
        """Connect to Active Directory via LDAP"""
        try:
            self.status = ConnectionStatus.TESTING
            # In real implementation, would use ldap3:
            # from ldap3 import Server, Connection, ALL
            # server = Server(self.config.host, get_info=ALL)
            # self._connection = Connection(server, user=..., password=...)

            # Mock connection
            self.status = ConnectionStatus.CONNECTED
            self.last_connected = datetime.now()
            return True

        except Exception as e:
            self.status = ConnectionStatus.ERROR
            self.error_message = str(e)
            return False

    def disconnect(self) -> bool:
        self._connection = None
        self.status = ConnectionStatus.DISCONNECTED
        return True

    def test_connection(self) -> Dict:
        result = {
            "success": False,
            "domain_info": {},
            "message": ""
        }

        try:
            if self.connect():
                result["success"] = True
                result["domain_info"] = {
                    "domain": "corp.example.com",
                    "domain_controller": self.config.host,
                    "forest": "example.com"
                }
                result["message"] = "Connection successful"
        except Exception as e:
            result["message"] = str(e)

        return result

    def get_users(self, filters: Dict = None) -> List[Dict]:
        """Get users from AD"""
        return [
            {
                "sam_account_name": "jsmith",
                "display_name": "John Smith",
                "email": "jsmith@example.com",
                "department": "Finance",
                "title": "AP Clerk",
                "manager": "mwilson",
                "enabled": True,
                "groups": ["Finance_Users", "AP_Team"]
            }
        ]

    def get_roles(self, filters: Dict = None) -> List[Dict]:
        """Get groups from AD (treated as roles)"""
        return [
            {
                "group_name": "Finance_Users",
                "description": "Finance department users",
                "group_type": "Security",
                "member_count": 45
            },
            {
                "group_name": "Domain Admins",
                "description": "Domain administrators",
                "group_type": "Security",
                "member_count": 5
            }
        ]

    def get_user_roles(self, user_id: str) -> List[Dict]:
        """Get groups for a user"""
        return [
            {"group_name": "Finance_Users"},
            {"group_name": "AP_Team"}
        ]

    def get_user_groups(self, user_id: str) -> List[str]:
        """Get all groups including nested"""
        return ["Finance_Users", "AP_Team", "All_Employees"]


class AzureADConnector(Connector):
    """Azure Active Directory Connector"""

    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self._token = None
        self._token_expiry = None

    def connect(self) -> bool:
        """Connect to Azure AD via Graph API"""
        try:
            self.status = ConnectionStatus.TESTING
            # In real implementation, would use msal:
            # from msal import ConfidentialClientApplication
            # app = ConfidentialClientApplication(
            #     self.config.client_id,
            #     authority=f"https://login.microsoftonline.com/{self.config.tenant_id}",
            #     client_credential=client_secret
            # )
            # token = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])

            # Mock connection
            self._token = "mock_token"
            self._token_expiry = datetime.now() + timedelta(hours=1)
            self.status = ConnectionStatus.CONNECTED
            self.last_connected = datetime.now()
            return True

        except Exception as e:
            self.status = ConnectionStatus.ERROR
            self.error_message = str(e)
            return False

    def disconnect(self) -> bool:
        self._token = None
        self.status = ConnectionStatus.DISCONNECTED
        return True

    def test_connection(self) -> Dict:
        result = {
            "success": False,
            "tenant_info": {},
            "message": ""
        }

        try:
            if self.connect():
                result["success"] = True
                result["tenant_info"] = {
                    "tenant_id": self.config.tenant_id,
                    "display_name": "Example Corp",
                    "verified_domains": ["example.com"]
                }
                result["message"] = "Connection successful"
        except Exception as e:
            result["message"] = str(e)

        return result

    def get_users(self, filters: Dict = None) -> List[Dict]:
        """Get users from Azure AD"""
        return [
            {
                "id": "user-guid-1",
                "user_principal_name": "jsmith@example.com",
                "display_name": "John Smith",
                "mail": "jsmith@example.com",
                "department": "Finance",
                "job_title": "AP Clerk",
                "account_enabled": True
            }
        ]

    def get_roles(self, filters: Dict = None) -> List[Dict]:
        """Get directory roles from Azure AD"""
        return [
            {
                "id": "role-guid-1",
                "display_name": "Global Administrator",
                "description": "Full access to all Azure AD features"
            },
            {
                "id": "role-guid-2",
                "display_name": "User Administrator",
                "description": "Manage users and groups"
            }
        ]

    def get_user_roles(self, user_id: str) -> List[Dict]:
        """Get role assignments for a user"""
        return [
            {"role_name": "User Administrator", "assignment_type": "Direct"}
        ]

    def get_enterprise_apps(self) -> List[Dict]:
        """Get enterprise applications"""
        return [
            {
                "app_id": "app-guid-1",
                "display_name": "SAP Cloud Platform",
                "app_roles": ["User", "Admin"]
            }
        ]


class GenericRESTConnector(Connector):
    """Generic REST API Connector"""

    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self._session = None

    def connect(self) -> bool:
        try:
            self.status = ConnectionStatus.TESTING
            # Would use requests library
            self.status = ConnectionStatus.CONNECTED
            self.last_connected = datetime.now()
            return True
        except Exception as e:
            self.status = ConnectionStatus.ERROR
            self.error_message = str(e)
            return False

    def disconnect(self) -> bool:
        self._session = None
        self.status = ConnectionStatus.DISCONNECTED
        return True

    def test_connection(self) -> Dict:
        return {
            "success": True,
            "endpoint": f"{self.config.host}",
            "message": "Connection successful"
        }

    def get_users(self, filters: Dict = None) -> List[Dict]:
        # Would make REST API call
        return []

    def get_roles(self, filters: Dict = None) -> List[Dict]:
        return []

    def get_user_roles(self, user_id: str) -> List[Dict]:
        return []

    def call_api(
        self,
        method: str,
        endpoint: str,
        params: Dict = None,
        data: Dict = None
    ) -> Dict:
        """Generic API call"""
        # Would use requests library
        return {"status": "success"}


class ConnectorManager:
    """
    Connector Manager.

    Manages all system connectors, synchronization,
    and data integration.
    """

    def __init__(self):
        self.connectors: Dict[str, Connector] = {}
        self.configs: Dict[str, ConnectorConfig] = {}
        self._initialize_demo_connectors()

    def _initialize_demo_connectors(self):
        """Initialize demo connectors"""
        # SAP ECC Connector
        sap_config = ConnectorConfig(
            name="SAP ECC Production",
            connector_type=ConnectorType.SAP_RFC,
            host="sap-ecc.example.com",
            port=3300,
            system_id="ECP",
            client="100",
            username="RFC_USER"
        )
        self.configs[sap_config.config_id] = sap_config
        self.connectors[sap_config.config_id] = SAPConnector(sap_config)

        # Active Directory Connector
        ad_config = ConnectorConfig(
            name="Corporate Active Directory",
            connector_type=ConnectorType.ACTIVE_DIRECTORY,
            host="dc01.corp.example.com",
            port=389,
            auth_type="kerberos"
        )
        self.configs[ad_config.config_id] = ad_config
        self.connectors[ad_config.config_id] = ActiveDirectoryConnector(ad_config)

        # Azure AD Connector
        azure_config = ConnectorConfig(
            name="Azure AD Tenant",
            connector_type=ConnectorType.AZURE_AD,
            host="graph.microsoft.com",
            tenant_id="tenant-guid",
            client_id="client-guid",
            auth_type="oauth2"
        )
        self.configs[azure_config.config_id] = azure_config
        self.connectors[azure_config.config_id] = AzureADConnector(azure_config)

    # =========================================================================
    # Connector Management
    # =========================================================================

    def create_connector(
        self,
        name: str,
        connector_type: ConnectorType,
        host: str,
        **kwargs
    ) -> Connector:
        """Create a new connector"""
        config = ConnectorConfig(
            name=name,
            connector_type=connector_type,
            host=host
        )

        for key, value in kwargs.items():
            if hasattr(config, key):
                setattr(config, key, value)

        self.configs[config.config_id] = config

        # Create appropriate connector instance
        if connector_type == ConnectorType.SAP_RFC:
            connector = SAPConnector(config)
        elif connector_type == ConnectorType.ACTIVE_DIRECTORY:
            connector = ActiveDirectoryConnector(config)
        elif connector_type == ConnectorType.AZURE_AD:
            connector = AzureADConnector(config)
        else:
            connector = GenericRESTConnector(config)

        self.connectors[config.config_id] = connector
        return connector

    def get_connector(self, config_id: str) -> Optional[Connector]:
        """Get a connector by config ID"""
        return self.connectors.get(config_id)

    def list_connectors(
        self,
        connector_type: ConnectorType = None,
        is_active: bool = None
    ) -> List[Dict]:
        """List all connectors with their status"""
        result = []

        for config_id, connector in self.connectors.items():
            config = self.configs.get(config_id)
            if not config:
                continue

            if connector_type and config.connector_type != connector_type:
                continue
            if is_active is not None and config.is_active != is_active:
                continue

            result.append({
                "config": config.to_dict(),
                "status": connector.get_status()
            })

        return result

    def update_config(
        self,
        config_id: str,
        **updates
    ) -> ConnectorConfig:
        """Update connector configuration"""
        if config_id not in self.configs:
            raise ValueError(f"Connector {config_id} not found")

        config = self.configs[config_id]

        for key, value in updates.items():
            if hasattr(config, key) and key not in ['config_id', 'created_at']:
                setattr(config, key, value)

        config.modified_at = datetime.now()
        return config

    def delete_connector(self, config_id: str) -> bool:
        """Delete a connector"""
        if config_id not in self.connectors:
            return False

        connector = self.connectors[config_id]
        connector.disconnect()

        del self.connectors[config_id]
        del self.configs[config_id]
        return True

    # =========================================================================
    # Connection Operations
    # =========================================================================

    def connect(self, config_id: str) -> Dict:
        """Connect a specific connector"""
        if config_id not in self.connectors:
            raise ValueError(f"Connector {config_id} not found")

        connector = self.connectors[config_id]
        success = connector.connect()

        return {
            "config_id": config_id,
            "success": success,
            "status": connector.status.value,
            "error": connector.error_message
        }

    def disconnect(self, config_id: str) -> Dict:
        """Disconnect a specific connector"""
        if config_id not in self.connectors:
            raise ValueError(f"Connector {config_id} not found")

        connector = self.connectors[config_id]
        success = connector.disconnect()

        return {
            "config_id": config_id,
            "success": success,
            "status": connector.status.value
        }

    def test_connection(self, config_id: str) -> Dict:
        """Test a connector"""
        if config_id not in self.connectors:
            raise ValueError(f"Connector {config_id} not found")

        connector = self.connectors[config_id]
        return connector.test_connection()

    def connect_all(self) -> Dict:
        """Connect all active connectors"""
        results = {}
        for config_id, config in self.configs.items():
            if config.is_active:
                results[config_id] = self.connect(config_id)
        return results

    # =========================================================================
    # Data Operations
    # =========================================================================

    def get_users(self, config_id: str, filters: Dict = None) -> List[Dict]:
        """Get users from a connector"""
        if config_id not in self.connectors:
            raise ValueError(f"Connector {config_id} not found")

        connector = self.connectors[config_id]
        return connector.get_users(filters)

    def get_roles(self, config_id: str, filters: Dict = None) -> List[Dict]:
        """Get roles from a connector"""
        if config_id not in self.connectors:
            raise ValueError(f"Connector {config_id} not found")

        connector = self.connectors[config_id]
        return connector.get_roles(filters)

    def get_user_roles(self, config_id: str, user_id: str) -> List[Dict]:
        """Get user roles from a connector"""
        if config_id not in self.connectors:
            raise ValueError(f"Connector {config_id} not found")

        connector = self.connectors[config_id]
        return connector.get_user_roles(user_id)

    def sync_data(self, config_id: str, sync_type: str = "full") -> SyncJob:
        """Run data synchronization"""
        if config_id not in self.connectors:
            raise ValueError(f"Connector {config_id} not found")

        connector = self.connectors[config_id]

        # Create and run sync job
        job = connector.create_sync_job(sync_type)
        job.status = "running"
        job.started_at = datetime.now()

        try:
            if sync_type == "users":
                users = connector.get_users()
                job.records_processed = len(users)
                job.records_created = len(users)
            elif sync_type == "roles":
                roles = connector.get_roles()
                job.records_processed = len(roles)
                job.records_created = len(roles)
            else:  # full
                users = connector.get_users()
                roles = connector.get_roles()
                job.records_processed = len(users) + len(roles)

            job.status = "completed"
        except Exception as e:
            job.status = "failed"
            job.error_message = str(e)

        job.completed_at = datetime.now()
        return job

    def get_sync_jobs(
        self,
        config_id: str = None,
        status: str = None
    ) -> List[SyncJob]:
        """Get sync jobs"""
        jobs = []

        for connector in self.connectors.values():
            for job in connector.sync_jobs:
                if config_id and job.connector_id != config_id:
                    continue
                if status and job.status != status:
                    continue
                jobs.append(job)

        return jobs

    # =========================================================================
    # Statistics
    # =========================================================================

    def get_statistics(self) -> Dict:
        """Get connector statistics"""
        total = len(self.connectors)
        connected = len([c for c in self.connectors.values()
                        if c.status == ConnectionStatus.CONNECTED])
        active_configs = len([c for c in self.configs.values() if c.is_active])

        by_type = {}
        for ct in ConnectorType:
            by_type[ct.value] = len([
                c for c in self.configs.values()
                if c.connector_type == ct
            ])

        total_jobs = sum(len(c.sync_jobs) for c in self.connectors.values())

        return {
            "total_connectors": total,
            "connected": connected,
            "disconnected": total - connected,
            "active_configs": active_configs,
            "by_type": by_type,
            "total_sync_jobs": total_jobs
        }
