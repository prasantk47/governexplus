"""
Azure AD Connector

Integration with Microsoft Entra ID (Azure AD) for identity and access management.
Supports user sync, group management, and application role assignments.

Uses the ``msal`` library for OAuth2 client-credentials authentication and
``httpx`` (async) for Microsoft Graph API calls.  When ``msal`` is not
installed the connector falls back to static mock data so that development
and testing can proceed without Azure credentials.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta, timezone
import logging
import asyncio

import httpx

# --------------------------------------------------------------------------- #
# Optional MSAL import -- fall back to mock mode when the library is absent.  #
# --------------------------------------------------------------------------- #
try:
    from msal import ConfidentialClientApplication  # type: ignore[import-untyped]
    MSAL_AVAILABLE = True
except ImportError:
    import os as _os
    if _os.getenv("APP_ENV", "").lower() == "production":
        raise RuntimeError(
            "Azure AD connector requires msal package in production. "
            "pip install msal"
        )
    ConfidentialClientApplication = None  # type: ignore[misc,assignment]
    MSAL_AVAILABLE = False

logger = logging.getLogger(__name__)

GRAPH_SCOPES = ["https://graph.microsoft.com/.default"]

# Default fields requested from the Graph /users endpoint
_DEFAULT_USER_SELECT = [
    "id", "userPrincipalName", "mail", "displayName", "givenName",
    "surname", "department", "jobTitle", "officeLocation",
    "accountEnabled", "createdDateTime", "signInActivity",
]


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
                "accountEnabled": "is_active",
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


# =========================================================================== #
# Mock helpers -- used when MSAL is not installed                             #
# =========================================================================== #

def _mock_users() -> List[AzureUser]:
    """Return static mock users for development / testing."""
    return [
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
            app_roles=["SAP_User", "Power_BI_User"],
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
            app_roles=["SAP_User", "Ariba_User"],
        ),
    ]


def _mock_groups() -> List[AzureGroup]:
    """Return static mock groups for development / testing."""
    return [
        AzureGroup(
            group_id="grp-finance",
            display_name="Finance Department",
            description="All Finance department members",
            group_type="security",
            mail_enabled=False,
            security_enabled=True,
            member_count=50,
            created_at=datetime(2020, 1, 1),
        ),
        AzureGroup(
            group_id="grp-sap-users",
            display_name="SAP Users",
            description="Users with SAP access",
            group_type="security",
            mail_enabled=False,
            security_enabled=True,
            member_count=200,
            created_at=datetime(2020, 1, 1),
        ),
    ]


# =========================================================================== #
# Graph API response parsing helpers                                          #
# =========================================================================== #

def _parse_datetime(value: Optional[str]) -> Optional[datetime]:
    """Parse an ISO-8601 datetime string returned by Graph API."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


def _parse_user(data: Dict[str, Any]) -> AzureUser:
    """Convert a Graph API user JSON object into an AzureUser dataclass."""
    sign_in = data.get("signInActivity") or {}
    return AzureUser(
        azure_id=data.get("id", ""),
        user_principal_name=data.get("userPrincipalName", ""),
        email=data.get("mail") or data.get("userPrincipalName", ""),
        display_name=data.get("displayName", ""),
        first_name=data.get("givenName", ""),
        last_name=data.get("surname", ""),
        department=data.get("department") or "",
        job_title=data.get("jobTitle") or "",
        location=data.get("officeLocation") or "",
        manager_id=None,  # populated separately via /manager endpoint
        is_active=data.get("accountEnabled", True),
        created_at=_parse_datetime(data.get("createdDateTime")),
        last_sign_in=_parse_datetime(sign_in.get("lastSignInDateTime")),
    )


def _parse_group(data: Dict[str, Any]) -> AzureGroup:
    """Convert a Graph API group JSON object into an AzureGroup dataclass."""
    group_types = data.get("groupTypes") or []
    gtype = "unified" if "Unified" in group_types else "security"
    return AzureGroup(
        group_id=data.get("id", ""),
        display_name=data.get("displayName", ""),
        description=data.get("description") or "",
        group_type=gtype,
        mail_enabled=data.get("mailEnabled", False),
        security_enabled=data.get("securityEnabled", False),
        member_count=0,  # Graph does not return this by default
        created_at=_parse_datetime(data.get("createdDateTime")),
    )


# =========================================================================== #
# Connector                                                                   #
# =========================================================================== #

class AzureADConnector:
    """
    Azure AD Connector

    Provides:
    1. User synchronization from Azure AD
    2. Group membership sync
    3. Application role assignments
    4. Real-time change detection via webhooks
    5. Provisioning operations

    When the ``msal`` package is installed, all operations hit the real
    Microsoft Graph API.  Otherwise the connector returns static mock data
    so that developers without Azure credentials can still work on the
    rest of the platform.
    """

    def __init__(self, config: AzureADConfig):
        self.config = config
        self._access_token: Optional[str] = None
        self._token_expires: Optional[datetime] = None
        self._msal_app: Optional[Any] = None
        self._http: Optional[httpx.AsyncClient] = None
        self._use_mock = not MSAL_AVAILABLE

        if self._use_mock:
            logger.warning(
                "msal library not installed -- Azure AD connector running "
                "in MOCK mode.  Install msal to enable real Graph API calls."
            )

    # ------------------------------------------------------------------ #
    # Internal helpers                                                    #
    # ------------------------------------------------------------------ #

    def _get_msal_app(self) -> Any:
        """Lazy-initialise the MSAL ConfidentialClientApplication."""
        if self._msal_app is None:
            self._msal_app = ConfidentialClientApplication(
                client_id=self.config.client_id,
                authority=self.config.authority,
                client_credential=self.config.client_secret,
            )
        return self._msal_app

    async def _get_http_client(self) -> httpx.AsyncClient:
        """Return a shared async httpx client, creating one if needed."""
        if self._http is None or self._http.is_closed:
            self._http = httpx.AsyncClient(
                base_url=self.config.graph_endpoint,
                timeout=httpx.Timeout(30.0),
            )
        return self._http

    def _auth_headers(self) -> Dict[str, str]:
        """Return Authorization header dict with the current bearer token."""
        return {
            "Authorization": f"Bearer {self._access_token}",
            "Content-Type": "application/json",
        }

    async def _graph_get(
        self, path: str, params: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Perform an authenticated GET against Microsoft Graph."""
        await self._ensure_authenticated()
        client = await self._get_http_client()
        resp = await client.get(path, params=params, headers=self._auth_headers())
        resp.raise_for_status()
        return resp.json()

    async def _graph_post(
        self, path: str, json_body: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Perform an authenticated POST against Microsoft Graph."""
        await self._ensure_authenticated()
        client = await self._get_http_client()
        resp = await client.post(path, json=json_body, headers=self._auth_headers())
        resp.raise_for_status()
        if resp.status_code == 204:
            return {}
        return resp.json()

    async def _graph_patch(
        self, path: str, json_body: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Perform an authenticated PATCH against Microsoft Graph."""
        await self._ensure_authenticated()
        client = await self._get_http_client()
        resp = await client.patch(path, json=json_body, headers=self._auth_headers())
        resp.raise_for_status()
        if resp.status_code == 204:
            return {}
        return resp.json()

    async def _graph_delete(self, path: str) -> None:
        """Perform an authenticated DELETE against Microsoft Graph."""
        await self._ensure_authenticated()
        client = await self._get_http_client()
        resp = await client.delete(path, headers=self._auth_headers())
        resp.raise_for_status()

    async def _graph_get_all_pages(
        self, path: str, params: Optional[Dict[str, str]] = None
    ) -> List[Dict[str, Any]]:
        """GET with automatic pagination -- follows @odata.nextLink."""
        results: List[Dict[str, Any]] = []
        await self._ensure_authenticated()
        client = await self._get_http_client()

        url: Optional[str] = path
        current_params = params

        while url:
            resp = await client.get(
                url, params=current_params, headers=self._auth_headers()
            )
            resp.raise_for_status()
            data = resp.json()
            results.extend(data.get("value", []))
            next_link = data.get("@odata.nextLink")
            if next_link:
                url = next_link
                current_params = None
            else:
                url = None

        return results

    # ==================== Authentication ====================

    async def authenticate(self) -> bool:
        """Authenticate with Azure AD using client credentials flow."""
        if self._use_mock:
            logger.info(
                "Mock mode: simulating authentication for tenant %s",
                self.config.tenant_id,
            )
            self._access_token = "mock_token"
            self._token_expires = datetime.now(timezone.utc) + timedelta(hours=1)
            return True

        try:
            logger.info(
                "Authenticating with Azure AD tenant: %s", self.config.tenant_id
            )

            app = self._get_msal_app()

            # Try the token cache first (MSAL caches tokens internally)
            result = app.acquire_token_silent(GRAPH_SCOPES, account=None)
            if not result:
                result = app.acquire_token_for_client(scopes=GRAPH_SCOPES)

            if "access_token" in result:
                self._access_token = result["access_token"]
                expires_in = result.get("expires_in", 3600)
                self._token_expires = datetime.now(timezone.utc) + timedelta(
                    seconds=int(expires_in) - 120  # refresh 2 min early
                )
                logger.info("Successfully authenticated with Azure AD")
                return True

            error = result.get("error_description") or result.get("error", "unknown")
            logger.error("Azure AD token acquisition failed: %s", error)
            return False

        except Exception as e:
            logger.error("Azure AD authentication failed: %s", e)
            return False

    async def _ensure_authenticated(self):
        """Ensure we have a valid (non-expired) access token."""
        if self._access_token and self._token_expires:
            if datetime.now(timezone.utc) < self._token_expires:
                return
        success = await self.authenticate()
        if not success and not self._use_mock:
            raise RuntimeError("Failed to authenticate with Azure AD")

    # ==================== User Operations ====================

    async def get_users(
        self,
        filter_query: str = None,
        select_fields: List[str] = None,
        top: int = 100,
    ) -> List[AzureUser]:
        """
        List users from Azure AD.

        Args:
            filter_query: OData $filter expression.
            select_fields: List of Graph user properties to request.
            top: Page size (max 999 per Graph API).

        Returns:
            List of AzureUser objects.
        """
        if self._use_mock:
            logger.info("Mock mode: returning static user list")
            return _mock_users()

        await self._ensure_authenticated()
        logger.info("Fetching users from Azure AD")

        params: Dict[str, str] = {}
        fields = select_fields or _DEFAULT_USER_SELECT
        params["$select"] = ",".join(fields)
        params["$top"] = str(min(top, 999))
        if filter_query:
            params["$filter"] = filter_query
        elif self.config.user_filter:
            params["$filter"] = self.config.user_filter

        raw_users = await self._graph_get_all_pages("/users", params=params)
        return [_parse_user(u) for u in raw_users]

    async def get_user(self, user_id: str) -> Optional[AzureUser]:
        """
        Get a single user by object ID or userPrincipalName.

        Args:
            user_id: Azure AD object ID or UPN.
        """
        if self._use_mock:
            mock = _mock_users()
            return next(
                (u for u in mock if u.azure_id == user_id or u.user_principal_name == user_id),
                None,
            )

        try:
            data = await self._graph_get(
                f"/users/{user_id}",
                params={"$select": ",".join(_DEFAULT_USER_SELECT)},
            )
            return _parse_user(data)
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                return None
            raise

    async def get_user_groups(self, user_id: str) -> List[AzureGroup]:
        """Get the security groups and directory roles a user belongs to."""
        if self._use_mock:
            return [_mock_groups()[0]]

        raw = await self._graph_get_all_pages(f"/users/{user_id}/memberOf")
        return [
            _parse_group(item)
            for item in raw
            if item.get("@odata.type") == "#microsoft.graph.group"
        ]

    async def get_user_app_role_assignments(
        self, user_id: str
    ) -> List[Dict[str, Any]]:
        """Get application role assignments for a user."""
        if self._use_mock:
            return [
                {
                    "id": "assignment-001",
                    "app_id": "sap-enterprise-app",
                    "app_display_name": "SAP S/4HANA",
                    "role_id": "sap-user-role",
                    "role_display_name": "SAP User",
                    "assigned_at": datetime(2025, 1, 1).isoformat(),
                }
            ]

        raw = await self._graph_get_all_pages(
            f"/users/{user_id}/appRoleAssignments"
        )
        return [
            {
                "id": item.get("id"),
                "app_id": item.get("resourceId"),
                "app_display_name": item.get("resourceDisplayName"),
                "role_id": item.get("appRoleId"),
                "role_display_name": item.get("appRoleId"),
                "assigned_at": item.get("createdDateTime"),
            }
            for item in raw
        ]

    # ==================== Group Operations ====================

    async def get_groups(
        self,
        filter_query: str = None,
        top: int = 100,
    ) -> List[AzureGroup]:
        """List security groups from Azure AD."""
        if self._use_mock:
            logger.info("Mock mode: returning static group list")
            return _mock_groups()

        await self._ensure_authenticated()
        logger.info("Fetching groups from Azure AD")

        params: Dict[str, str] = {
            "$select": "id,displayName,description,groupTypes,mailEnabled,securityEnabled,createdDateTime",
            "$top": str(min(top, 999)),
        }
        if filter_query:
            params["$filter"] = filter_query
        elif self.config.group_filter:
            params["$filter"] = self.config.group_filter

        raw = await self._graph_get_all_pages("/groups", params=params)
        return [_parse_group(g) for g in raw]

    async def get_group_members(self, group_id: str) -> List[AzureUser]:
        """Get members of a group."""
        if self._use_mock:
            return _mock_users()

        raw = await self._graph_get_all_pages(
            f"/groups/{group_id}/members",
            params={"$select": ",".join(_DEFAULT_USER_SELECT)},
        )
        return [
            _parse_user(item)
            for item in raw
            if item.get("@odata.type") == "#microsoft.graph.user"
        ]

    # ==================== Provisioning Operations ====================

    async def disable_user(self, user_id: str) -> bool:
        """Disable a user account (set accountEnabled = false)."""
        if self._use_mock:
            logger.info("Mock mode: simulating disable for user %s", user_id)
            return True

        logger.info("Disabling user %s in Azure AD", user_id)
        await self._graph_patch(
            f"/users/{user_id}", json_body={"accountEnabled": False}
        )
        return True

    async def enable_user(self, user_id: str) -> bool:
        """Enable a user account (set accountEnabled = true)."""
        if self._use_mock:
            logger.info("Mock mode: simulating enable for user %s", user_id)
            return True

        logger.info("Enabling user %s in Azure AD", user_id)
        await self._graph_patch(
            f"/users/{user_id}", json_body={"accountEnabled": True}
        )
        return True

    async def add_user_to_group(self, user_id: str, group_id: str) -> bool:
        """Add a user to an Azure AD group."""
        if self._use_mock:
            logger.info(
                "Mock mode: simulating add user %s to group %s", user_id, group_id
            )
            return True

        logger.info("Adding user %s to group %s", user_id, group_id)
        body = {
            "@odata.id": f"{self.config.graph_endpoint}/directoryObjects/{user_id}"
        }
        await self._graph_post(f"/groups/{group_id}/members/$ref", json_body=body)
        return True

    async def remove_user_from_group(self, user_id: str, group_id: str) -> bool:
        """Remove a user from an Azure AD group."""
        if self._use_mock:
            logger.info(
                "Mock mode: simulating remove user %s from group %s",
                user_id,
                group_id,
            )
            return True

        logger.info("Removing user %s from group %s", user_id, group_id)
        await self._graph_delete(f"/groups/{group_id}/members/{user_id}/$ref")
        return True

    async def assign_app_role(
        self,
        user_id: str,
        app_id: str,
        role_id: str,
    ) -> bool:
        """Assign an application role to a user."""
        if self._use_mock:
            logger.info("Mock mode: simulating app role assignment")
            return True

        logger.info("Assigning app role %s to user %s", role_id, user_id)
        body = {
            "principalId": user_id,
            "resourceId": app_id,
            "appRoleId": role_id,
        }
        await self._graph_post(
            f"/users/{user_id}/appRoleAssignments", json_body=body
        )
        return True

    async def revoke_app_role(
        self,
        user_id: str,
        assignment_id: str,
    ) -> bool:
        """Revoke an application role assignment."""
        if self._use_mock:
            logger.info("Mock mode: simulating app role revocation")
            return True

        logger.info(
            "Revoking app role assignment %s from user %s", assignment_id, user_id
        )
        await self._graph_delete(
            f"/users/{user_id}/appRoleAssignments/{assignment_id}"
        )
        return True

    # ==================== Sync Operations ====================

    async def sync_users_to_grc(self) -> Dict[str, Any]:
        """Sync Azure AD users to GRC platform."""
        logger.info("Starting Azure AD user sync")

        users = await self.get_users()

        created = 0
        updated = 0
        errors: List[Dict[str, str]] = []

        for user in users:
            try:
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
                    "last_synced_at": datetime.now(timezone.utc).isoformat(),
                }

                # In production, upsert to database
                # existing = db.query(User).filter(User.external_id == user.azure_id).first()
                # if existing:
                #     updated += 1
                # else:
                #     created += 1

                created += 1  # Placeholder

            except Exception as e:
                errors.append({"user": user.user_principal_name, "error": str(e)})

        return {
            "source": "azure_ad",
            "users_processed": len(users),
            "created": created,
            "updated": updated,
            "errors": errors,
            "synced_at": datetime.now(timezone.utc).isoformat(),
        }

    async def sync_groups_to_grc(self) -> Dict[str, Any]:
        """Sync Azure AD groups to GRC as roles."""
        logger.info("Starting Azure AD group sync")

        groups = await self.get_groups()

        synced = 0
        for group in groups:
            grc_role = {
                "role_id": f"AAD_{group.group_id}",
                "role_name": group.display_name,
                "description": group.description,
                "role_type": "azure_ad_group",
                "source_system": "azure_ad",
                "external_id": group.group_id,
                "user_count": group.member_count,
            }
            synced += 1

        return {
            "source": "azure_ad",
            "groups_processed": len(groups),
            "synced": synced,
            "synced_at": datetime.now(timezone.utc).isoformat(),
        }

    # ==================== Change Detection ====================

    async def get_delta_changes(self, delta_link: str = None) -> Dict[str, Any]:
        """Get incremental changes using Graph delta query."""
        if self._use_mock:
            return {
                "changes": [],
                "delta_link": "https://graph.microsoft.com/v1.0/users/delta?$deltatoken=mock",
            }

        if delta_link:
            # delta_link is an absolute URL -- call it directly
            await self._ensure_authenticated()
            client = await self._get_http_client()
            resp = await client.get(delta_link, headers=self._auth_headers())
            resp.raise_for_status()
            data = resp.json()
        else:
            data = await self._graph_get(
                "/users/delta",
                params={"$select": ",".join(_DEFAULT_USER_SELECT)},
            )

        return {
            "changes": data.get("value", []),
            "delta_link": data.get("@odata.deltaLink")
                or data.get("@odata.nextLink", ""),
        }

    # ==================== Connection Test ====================

    async def test_connection(self) -> Dict[str, Any]:
        """Test Azure AD connection."""
        try:
            authenticated = await self.authenticate()

            if not authenticated:
                return {
                    "status": "failed",
                    "tenant_id": self.config.tenant_id,
                    "message": "Authentication failed",
                    "mock_mode": self._use_mock,
                }

            if not self._use_mock:
                # Verify Graph access by fetching organisation info
                org_data = await self._graph_get("/organization")
                org_name = ""
                orgs = org_data.get("value", [])
                if orgs:
                    org_name = orgs[0].get("displayName", "")

                return {
                    "status": "connected",
                    "tenant_id": self.config.tenant_id,
                    "organization": org_name,
                    "message": "Successfully connected to Azure AD",
                    "mock_mode": False,
                }

            return {
                "status": "connected",
                "tenant_id": self.config.tenant_id,
                "message": "Mock mode -- no real connection established",
                "mock_mode": True,
            }

        except Exception as e:
            return {
                "status": "error",
                "tenant_id": self.config.tenant_id,
                "message": str(e),
                "mock_mode": self._use_mock,
            }

    # ==================== Cleanup ====================

    async def close(self) -> None:
        """Close the underlying httpx client (call on shutdown)."""
        if self._http and not self._http.is_closed:
            await self._http.aclose()
            self._http = None
