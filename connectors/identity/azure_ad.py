"""
Azure AD Connector

Integration with Microsoft Entra ID (Azure AD) for identity and access management.
Supports user sync, group management, and application role assignments.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging
import asyncio

logger = logging.getLogger(__name__)


@dataclass
class AzureADConfig:
    """Azure AD connection configuration"""
    tenant_id: str
    client_id: str
    client_secret: str  # Would be retrieved from secrets manager in production

    # Endpoints
    authority: str = ""
    graph_endpoint: str = "https://graph.microsoft.com/v1.0"

    # Sync options
    sync_users: bool = True
    sync_groups: bool = True
    sync_app_roles: bool = True

    # Filters
    user_filter: str = ""  # OData filter for users
    group_filter: str = ""  # OData filter for groups

    # Attribute mapping
    user_attribute_map: Dict[str, str] = field(default_factory=dict)
    group_attribute_map: Dict[str, str] = field(default_factory=dict)

    def __post_init__(self):
        if not self.authority:
            self.authority = f"https://login.microsoftonline.com/{self.tenant_id}"

        if not self.user_attribute_map:
            self.user_attribute_map = {
                "id": "azure_id",
                "userPrincipalName": "user_id",
                "mail": "email",
                "displayName": "full_name",
                "givenName": "first_name",
                "surname": "last_name",
                "department": "department",
                "jobTitle": "job_title",
                "officeLocation": "location",
                "manager": "manager_id",
                "accountEnabled": "is_active"
            }


@dataclass
class AzureUser:
    """Azure AD user"""
    azure_id: str
    user_principal_name: str
    email: str
    display_name: str
    first_name: str
    last_name: str
    department: str
    job_title: str
    location: str
    manager_id: Optional[str]
    is_active: bool
    created_at: Optional[datetime]
    last_sign_in: Optional[datetime]
    groups: List[str] = field(default_factory=list)
    app_roles: List[str] = field(default_factory=list)


@dataclass
class AzureGroup:
    """Azure AD group"""
    group_id: str
    display_name: str
    description: str
    group_type: str  # security, unified (M365)
    mail_enabled: bool
    security_enabled: bool
    member_count: int
    created_at: Optional[datetime]


class AzureADConnector:
    """
    Azure AD Connector

    Provides:
    1. User synchronization from Azure AD
    2. Group membership sync
    3. Application role assignments
    4. Real-time change detection via webhooks
    5. Provisioning operations
    """

    def __init__(self, config: AzureADConfig):
        self.config = config
        self._access_token: Optional[str] = None
        self._token_expires: Optional[datetime] = None

    # ==================== Authentication ====================

    async def authenticate(self) -> bool:
        """Authenticate with Azure AD using client credentials"""
        try:
            # In production, use MSAL library
            # from msal import ConfidentialClientApplication

            # Simulated authentication
            logger.info(f"Authenticating with Azure AD tenant: {self.config.tenant_id}")

            # Would call:
            # app = ConfidentialClientApplication(
            #     self.config.client_id,
            #     authority=self.config.authority,
            #     client_credential=self.config.client_secret
            # )
            # result = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])

            self._access_token = "simulated_token"
            self._token_expires = datetime.utcnow()

            logger.info("Successfully authenticated with Azure AD")
            return True

        except Exception as e:
            logger.error(f"Azure AD authentication failed: {e}")
            return False

    async def _ensure_authenticated(self):
        """Ensure we have a valid access token"""
        if not self._access_token or (self._token_expires and datetime.utcnow() >= self._token_expires):
            await self.authenticate()

    # ==================== User Operations ====================

    async def get_users(
        self,
        filter_query: str = None,
        select_fields: List[str] = None,
        top: int = 100
    ) -> List[AzureUser]:
        """Get users from Azure AD"""
        await self._ensure_authenticated()

        logger.info("Fetching users from Azure AD")

        # In production, would call Graph API:
        # GET https://graph.microsoft.com/v1.0/users
        #   ?$filter={filter_query}
        #   &$select={select_fields}
        #   &$top={top}
        #   &$expand=manager

        # Simulated response
        users = [
            AzureUser(
                azure_id="aad-001",
                user_principal_name="jsmith@company.onmicrosoft.com",
                email="jsmith@company.com",
                display_name="John Smith",
                first_name="John",
                last_name="Smith",
                department="Finance",
                job_title="Senior Accountant",
                location="New York",
                manager_id="aad-mgr-001",
                is_active=True,
                created_at=datetime(2024, 1, 15),
                last_sign_in=datetime(2026, 1, 16),
                groups=["grp-finance", "grp-all-employees"],
                app_roles=["SAP_User", "Power_BI_User"]
            ),
            AzureUser(
                azure_id="aad-002",
                user_principal_name="mbrown@company.onmicrosoft.com",
                email="mbrown@company.com",
                display_name="Mary Brown",
                first_name="Mary",
                last_name="Brown",
                department="Procurement",
                job_title="Procurement Manager",
                location="Chicago",
                manager_id="aad-mgr-002",
                is_active=True,
                created_at=datetime(2023, 6, 1),
                last_sign_in=datetime(2026, 1, 17),
                groups=["grp-procurement", "grp-managers", "grp-all-employees"],
                app_roles=["SAP_User", "Ariba_User"]
            ),
        ]

        return users

    async def get_user(self, user_id: str) -> Optional[AzureUser]:
        """Get a single user by ID or UPN"""
        await self._ensure_authenticated()

        # GET https://graph.microsoft.com/v1.0/users/{user_id}

        users = await self.get_users()
        return next((u for u in users if u.azure_id == user_id or u.user_principal_name == user_id), None)

    async def get_user_groups(self, user_id: str) -> List[AzureGroup]:
        """Get groups a user belongs to"""
        await self._ensure_authenticated()

        # GET https://graph.microsoft.com/v1.0/users/{user_id}/memberOf

        return [
            AzureGroup(
                group_id="grp-finance",
                display_name="Finance Department",
                description="All Finance department members",
                group_type="security",
                mail_enabled=False,
                security_enabled=True,
                member_count=50,
                created_at=datetime(2020, 1, 1)
            )
        ]

    async def get_user_app_role_assignments(self, user_id: str) -> List[Dict[str, Any]]:
        """Get application role assignments for a user"""
        await self._ensure_authenticated()

        # GET https://graph.microsoft.com/v1.0/users/{user_id}/appRoleAssignments

        return [
            {
                "id": "assignment-001",
                "app_id": "sap-enterprise-app",
                "app_display_name": "SAP S/4HANA",
                "role_id": "sap-user-role",
                "role_display_name": "SAP User",
                "assigned_at": datetime(2025, 1, 1).isoformat()
            }
        ]

    # ==================== Group Operations ====================

    async def get_groups(
        self,
        filter_query: str = None,
        top: int = 100
    ) -> List[AzureGroup]:
        """Get groups from Azure AD"""
        await self._ensure_authenticated()

        # GET https://graph.microsoft.com/v1.0/groups

        return [
            AzureGroup(
                group_id="grp-finance",
                display_name="Finance Department",
                description="All Finance department members",
                group_type="security",
                mail_enabled=False,
                security_enabled=True,
                member_count=50,
                created_at=datetime(2020, 1, 1)
            ),
            AzureGroup(
                group_id="grp-sap-users",
                display_name="SAP Users",
                description="Users with SAP access",
                group_type="security",
                mail_enabled=False,
                security_enabled=True,
                member_count=200,
                created_at=datetime(2020, 1, 1)
            ),
        ]

    async def get_group_members(self, group_id: str) -> List[AzureUser]:
        """Get members of a group"""
        await self._ensure_authenticated()

        # GET https://graph.microsoft.com/v1.0/groups/{group_id}/members

        return await self.get_users()  # Simplified

    # ==================== Sync Operations ====================

    async def sync_users_to_grc(self) -> Dict[str, Any]:
        """Sync Azure AD users to GRC platform"""
        logger.info("Starting Azure AD user sync")

        users = await self.get_users()

        created = 0
        updated = 0
        errors = []

        for user in users:
            try:
                # Map to GRC user format
                grc_user = {
                    "user_id": user.user_principal_name.split("@")[0].upper(),
                    "email": user.email,
                    "full_name": user.display_name,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "department": user.department,
                    "status": "active" if user.is_active else "inactive",
                    "source_system": "azure_ad",
                    "external_id": user.azure_id,
                    "manager_id": user.manager_id,
                    "last_synced_at": datetime.utcnow().isoformat()
                }

                # In production, upsert to database
                # existing = db.query(User).filter(User.external_id == user.azure_id).first()
                # if existing:
                #     updated += 1
                # else:
                #     created += 1

                created += 1  # Simulated

            except Exception as e:
                errors.append({"user": user.user_principal_name, "error": str(e)})

        return {
            "source": "azure_ad",
            "users_processed": len(users),
            "created": created,
            "updated": updated,
            "errors": errors,
            "synced_at": datetime.utcnow().isoformat()
        }

    async def sync_groups_to_grc(self) -> Dict[str, Any]:
        """Sync Azure AD groups to GRC as roles"""
        logger.info("Starting Azure AD group sync")

        groups = await self.get_groups()

        synced = 0
        for group in groups:
            # Map group to GRC role
            grc_role = {
                "role_id": f"AAD_{group.group_id}",
                "role_name": group.display_name,
                "description": group.description,
                "role_type": "azure_ad_group",
                "source_system": "azure_ad",
                "external_id": group.group_id,
                "user_count": group.member_count
            }
            synced += 1

        return {
            "source": "azure_ad",
            "groups_processed": len(groups),
            "synced": synced,
            "synced_at": datetime.utcnow().isoformat()
        }

    # ==================== Provisioning Operations ====================

    async def add_user_to_group(self, user_id: str, group_id: str) -> bool:
        """Add a user to an Azure AD group"""
        await self._ensure_authenticated()

        # POST https://graph.microsoft.com/v1.0/groups/{group_id}/members/$ref
        # Body: { "@odata.id": "https://graph.microsoft.com/v1.0/users/{user_id}" }

        logger.info(f"Adding user {user_id} to group {group_id}")
        return True

    async def remove_user_from_group(self, user_id: str, group_id: str) -> bool:
        """Remove a user from an Azure AD group"""
        await self._ensure_authenticated()

        # DELETE https://graph.microsoft.com/v1.0/groups/{group_id}/members/{user_id}/$ref

        logger.info(f"Removing user {user_id} from group {group_id}")
        return True

    async def assign_app_role(
        self,
        user_id: str,
        app_id: str,
        role_id: str
    ) -> bool:
        """Assign an application role to a user"""
        await self._ensure_authenticated()

        # POST https://graph.microsoft.com/v1.0/users/{user_id}/appRoleAssignments
        # Body: { "principalId": user_id, "resourceId": app_id, "appRoleId": role_id }

        logger.info(f"Assigning app role {role_id} to user {user_id}")
        return True

    async def revoke_app_role(
        self,
        user_id: str,
        assignment_id: str
    ) -> bool:
        """Revoke an application role assignment"""
        await self._ensure_authenticated()

        # DELETE https://graph.microsoft.com/v1.0/users/{user_id}/appRoleAssignments/{assignment_id}

        logger.info(f"Revoking app role assignment {assignment_id} from user {user_id}")
        return True

    # ==================== Change Detection ====================

    async def get_delta_changes(self, delta_link: str = None) -> Dict[str, Any]:
        """Get incremental changes using delta query"""
        await self._ensure_authenticated()

        # GET https://graph.microsoft.com/v1.0/users/delta
        # or GET {delta_link} for subsequent calls

        return {
            "changes": [],
            "delta_link": "https://graph.microsoft.com/v1.0/users/delta?$deltatoken=xxx"
        }

    # ==================== Connection Test ====================

    async def test_connection(self) -> Dict[str, Any]:
        """Test Azure AD connection"""
        try:
            authenticated = await self.authenticate()

            if authenticated:
                # Try to fetch organization info
                # GET https://graph.microsoft.com/v1.0/organization

                return {
                    "status": "connected",
                    "tenant_id": self.config.tenant_id,
                    "message": "Successfully connected to Azure AD"
                }
            else:
                return {
                    "status": "failed",
                    "tenant_id": self.config.tenant_id,
                    "message": "Authentication failed"
                }

        except Exception as e:
            return {
                "status": "error",
                "tenant_id": self.config.tenant_id,
                "message": str(e)
            }
