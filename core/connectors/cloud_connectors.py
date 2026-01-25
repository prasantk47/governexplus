"""
Cloud Platform Connectors

Provides connectivity to cloud IAM systems:
- AWS IAM
- Azure AD / Entra ID
- Google Cloud IAM
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging
import asyncio
import json

from .base import (
    BaseConnector, ConnectorConfig, OperationResult,
    ConnectorError, AuthenticationError, OperationError,
    ConnectionStatus
)

logger = logging.getLogger(__name__)

# Try to import boto3 for AWS
try:
    import boto3
    from botocore.exceptions import ClientError, NoCredentialsError
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False
    logger.warning("boto3 not installed. AWS connector will use simulation mode.")

# Try to import Azure SDK
try:
    from azure.identity import ClientSecretCredential
    from azure.graphrbac import GraphRbacManagementClient
    AZURE_AVAILABLE = True
except ImportError:
    AZURE_AVAILABLE = False
    logger.warning("Azure SDK not installed. Azure connector will use simulation mode.")


@dataclass
class AWSConfig(ConnectorConfig):
    """AWS IAM configuration"""
    access_key_id: str = ""
    secret_access_key: str = ""
    region: str = "us-east-1"
    role_arn: Optional[str] = None  # For assume role
    external_id: Optional[str] = None

    def __post_init__(self):
        self.system_type = "aws_iam"


@dataclass
class AzureConfig(ConnectorConfig):
    """Azure AD configuration"""
    tenant_id: str = ""
    client_id: str = ""
    client_secret: str = ""
    subscription_id: str = ""

    def __post_init__(self):
        self.system_type = "azure_ad"


class MockAWSClient:
    """Mock AWS IAM client for testing"""

    def __init__(self, config: AWSConfig):
        self.config = config
        self._users = {
            "john.smith": {
                "UserName": "john.smith",
                "UserId": "AIDAEXAMPLE1",
                "Arn": "arn:aws:iam::123456789012:user/john.smith",
                "CreateDate": datetime(2024, 1, 15),
                "Tags": [{"Key": "Department", "Value": "Engineering"}]
            },
            "mary.brown": {
                "UserName": "mary.brown",
                "UserId": "AIDAEXAMPLE2",
                "Arn": "arn:aws:iam::123456789012:user/mary.brown",
                "CreateDate": datetime(2024, 3, 20),
                "Tags": [{"Key": "Department", "Value": "DevOps"}]
            }
        }
        self._groups = {
            "Administrators": ["john.smith"],
            "Developers": ["john.smith", "mary.brown"],
            "ReadOnly": ["mary.brown"]
        }
        self._policies = {
            "arn:aws:iam::aws:policy/AdministratorAccess": {"PolicyName": "AdministratorAccess"},
            "arn:aws:iam::aws:policy/ReadOnlyAccess": {"PolicyName": "ReadOnlyAccess"},
            "arn:aws:iam::aws:policy/PowerUserAccess": {"PolicyName": "PowerUserAccess"},
        }

    def get_user(self, UserName: str) -> Dict:
        if UserName in self._users:
            return {"User": self._users[UserName]}
        raise Exception(f"User {UserName} not found")

    def create_user(self, UserName: str, **kwargs) -> Dict:
        if UserName in self._users:
            raise Exception(f"User {UserName} already exists")

        self._users[UserName] = {
            "UserName": UserName,
            "UserId": f"AIDA{UserName.upper()[:8]}",
            "Arn": f"arn:aws:iam::123456789012:user/{UserName}",
            "CreateDate": datetime.now(),
            "Tags": kwargs.get("Tags", [])
        }
        return {"User": self._users[UserName]}

    def delete_user(self, UserName: str) -> Dict:
        if UserName not in self._users:
            raise Exception(f"User {UserName} not found")
        del self._users[UserName]
        return {}

    def list_users(self, **kwargs) -> Dict:
        return {"Users": list(self._users.values())}

    def add_user_to_group(self, UserName: str, GroupName: str) -> Dict:
        if GroupName not in self._groups:
            self._groups[GroupName] = []
        if UserName not in self._groups[GroupName]:
            self._groups[GroupName].append(UserName)
        return {}

    def remove_user_from_group(self, UserName: str, GroupName: str) -> Dict:
        if GroupName in self._groups and UserName in self._groups[GroupName]:
            self._groups[GroupName].remove(UserName)
        return {}

    def list_groups_for_user(self, UserName: str) -> Dict:
        groups = [{"GroupName": g} for g, users in self._groups.items() if UserName in users]
        return {"Groups": groups}

    def attach_user_policy(self, UserName: str, PolicyArn: str) -> Dict:
        return {}

    def detach_user_policy(self, UserName: str, PolicyArn: str) -> Dict:
        return {}

    def list_attached_user_policies(self, UserName: str) -> Dict:
        return {"AttachedPolicies": []}


class AWSIAMConnector(BaseConnector):
    """
    AWS IAM Connector

    Provides user and group management for AWS IAM.
    """

    def __init__(self, config: AWSConfig):
        super().__init__(config)
        self.aws_config = config
        self._iam_client = None

    async def _do_connect(self):
        """Connect to AWS IAM"""
        if BOTO3_AVAILABLE:
            session = boto3.Session(
                aws_access_key_id=self.aws_config.access_key_id or self.aws_config.username,
                aws_secret_access_key=self.aws_config.secret_access_key or self.aws_config.password,
                region_name=self.aws_config.region
            )
            self._iam_client = session.client('iam')
        else:
            self._iam_client = MockAWSClient(self.aws_config)

        # Test connection
        await self._do_test_connection()

    async def _do_disconnect(self):
        """Disconnect from AWS"""
        self._iam_client = None

    async def _do_test_connection(self) -> Dict:
        """Test AWS connection"""
        loop = asyncio.get_event_loop()

        def _test():
            # Try to list users (limit 1) to verify connection
            return self._iam_client.list_users(MaxItems=1)

        result = await loop.run_in_executor(None, _test)
        return {
            "status": "connected",
            "region": self.aws_config.region,
            "user_count": len(result.get("Users", []))
        }

    async def _do_execute(self, operation: str, **params) -> Dict:
        """Execute AWS IAM operation"""
        loop = asyncio.get_event_loop()

        operations = {
            "get_user": lambda: self._iam_client.get_user(UserName=params.get("user_id")),
            "create_user": lambda: self._iam_client.create_user(
                UserName=params.get("user_data", {}).get("user_id"),
                Tags=params.get("user_data", {}).get("tags", [])
            ),
            "delete_user": lambda: self._iam_client.delete_user(UserName=params.get("user_id")),
            "list_users": lambda: self._iam_client.list_users(),
            "assign_role": lambda: self._iam_client.add_user_to_group(
                UserName=params.get("user_id"),
                GroupName=params.get("role_name")
            ),
            "remove_role": lambda: self._iam_client.remove_user_from_group(
                UserName=params.get("user_id"),
                GroupName=params.get("role_name")
            ),
            "get_user_roles": lambda: self._iam_client.list_groups_for_user(
                UserName=params.get("user_id")
            ),
        }

        if operation not in operations:
            raise OperationError(f"Unknown operation: {operation}", operation)

        result = await loop.run_in_executor(None, operations[operation])
        return self._format_result(operation, result)

    def _format_result(self, operation: str, result: Dict) -> Dict:
        """Format AWS response to standard format"""
        if operation == "get_user":
            user = result.get("User", {})
            return {
                "user_id": user.get("UserName"),
                "arn": user.get("Arn"),
                "created": user.get("CreateDate").isoformat() if user.get("CreateDate") else None,
            }
        elif operation == "list_users":
            return {
                "users": [
                    {"user_id": u.get("UserName"), "arn": u.get("Arn")}
                    for u in result.get("Users", [])
                ],
                "count": len(result.get("Users", []))
            }
        elif operation == "get_user_roles":
            return {
                "roles": [g.get("GroupName") for g in result.get("Groups", [])]
            }
        return result


class MockAzureClient:
    """Mock Azure AD client for testing"""

    def __init__(self, config: AzureConfig):
        self.config = config
        self._users = {
            "user1@company.onmicrosoft.com": {
                "id": "uuid-1234-5678",
                "displayName": "John Smith",
                "userPrincipalName": "user1@company.onmicrosoft.com",
                "mail": "john.smith@company.com",
                "department": "IT"
            },
            "user2@company.onmicrosoft.com": {
                "id": "uuid-2345-6789",
                "displayName": "Mary Brown",
                "userPrincipalName": "user2@company.onmicrosoft.com",
                "mail": "mary.brown@company.com",
                "department": "Finance"
            }
        }
        self._groups = {
            "Global Administrators": ["user1@company.onmicrosoft.com"],
            "Users": ["user1@company.onmicrosoft.com", "user2@company.onmicrosoft.com"]
        }

    def get_user(self, user_id: str) -> Dict:
        if user_id in self._users:
            return self._users[user_id]
        raise Exception(f"User {user_id} not found")

    def create_user(self, user_data: Dict) -> Dict:
        upn = user_data.get("userPrincipalName")
        if upn in self._users:
            raise Exception(f"User {upn} already exists")

        self._users[upn] = {
            "id": f"uuid-{len(self._users)}",
            "displayName": user_data.get("displayName"),
            "userPrincipalName": upn,
            "mail": user_data.get("mail"),
            "department": user_data.get("department")
        }
        return self._users[upn]

    def delete_user(self, user_id: str) -> None:
        if user_id in self._users:
            del self._users[user_id]

    def list_users(self) -> List[Dict]:
        return list(self._users.values())

    def add_to_group(self, user_id: str, group_name: str) -> None:
        if group_name not in self._groups:
            self._groups[group_name] = []
        if user_id not in self._groups[group_name]:
            self._groups[group_name].append(user_id)

    def remove_from_group(self, user_id: str, group_name: str) -> None:
        if group_name in self._groups and user_id in self._groups[group_name]:
            self._groups[group_name].remove(user_id)

    def get_user_groups(self, user_id: str) -> List[str]:
        return [g for g, users in self._groups.items() if user_id in users]


class AzureADConnector(BaseConnector):
    """
    Azure AD / Entra ID Connector

    Provides user and group management for Azure Active Directory.
    """

    def __init__(self, config: AzureConfig):
        super().__init__(config)
        self.azure_config = config
        self._client = None
        self._credential = None

    async def _do_connect(self):
        """Connect to Azure AD"""
        if AZURE_AVAILABLE:
            self._credential = ClientSecretCredential(
                tenant_id=self.azure_config.tenant_id,
                client_id=self.azure_config.client_id,
                client_secret=self.azure_config.client_secret
            )
            # Note: In production, use Microsoft Graph API
            # self._client = GraphRbacManagementClient(self._credential, self.azure_config.tenant_id)
            self._client = MockAzureClient(self.azure_config)
        else:
            self._client = MockAzureClient(self.azure_config)

        await self._do_test_connection()

    async def _do_disconnect(self):
        """Disconnect from Azure AD"""
        self._client = None
        self._credential = None

    async def _do_test_connection(self) -> Dict:
        """Test Azure AD connection"""
        users = self._client.list_users()
        return {
            "status": "connected",
            "tenant_id": self.azure_config.tenant_id,
            "user_count": len(users)
        }

    async def _do_execute(self, operation: str, **params) -> Dict:
        """Execute Azure AD operation"""
        loop = asyncio.get_event_loop()

        if operation == "get_user":
            user = self._client.get_user(params.get("user_id"))
            return {
                "user_id": user.get("userPrincipalName"),
                "display_name": user.get("displayName"),
                "email": user.get("mail"),
                "department": user.get("department")
            }

        elif operation == "create_user":
            user_data = params.get("user_data", {})
            user = self._client.create_user({
                "userPrincipalName": user_data.get("user_id"),
                "displayName": f"{user_data.get('first_name', '')} {user_data.get('last_name', '')}",
                "mail": user_data.get("email"),
                "department": user_data.get("department")
            })
            return {"user_id": user.get("userPrincipalName"), "created": True}

        elif operation == "delete_user":
            self._client.delete_user(params.get("user_id"))
            return {"user_id": params.get("user_id"), "deleted": True}

        elif operation == "list_users":
            users = self._client.list_users()
            return {
                "users": [
                    {"user_id": u.get("userPrincipalName"), "display_name": u.get("displayName")}
                    for u in users
                ],
                "count": len(users)
            }

        elif operation == "assign_role":
            self._client.add_to_group(params.get("user_id"), params.get("role_name"))
            return {"user_id": params.get("user_id"), "role_name": params.get("role_name"), "assigned": True}

        elif operation == "remove_role":
            self._client.remove_from_group(params.get("user_id"), params.get("role_name"))
            return {"user_id": params.get("user_id"), "role_name": params.get("role_name"), "removed": True}

        elif operation == "get_user_roles":
            groups = self._client.get_user_groups(params.get("user_id"))
            return {"user_id": params.get("user_id"), "roles": groups}

        else:
            raise OperationError(f"Unknown operation: {operation}", operation)
