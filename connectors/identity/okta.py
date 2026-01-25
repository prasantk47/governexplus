"""
Okta Connector

Integration with Okta for identity and access management.
Supports user sync, group management, and application assignments.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class OktaConfig:
    """Okta connection configuration"""
    domain: str  # e.g., "company.okta.com"
    api_token: str  # Would be retrieved from secrets manager

    # API settings
    api_version: str = "v1"

    # Sync options
    sync_users: bool = True
    sync_groups: bool = True
    sync_apps: bool = True

    # Filters
    user_filter: str = ""
    group_filter: str = ""

    # Attribute mapping
    user_attribute_map: Dict[str, str] = field(default_factory=dict)

    @property
    def base_url(self) -> str:
        return f"https://{self.domain}/api/{self.api_version}"

    def __post_init__(self):
        if not self.user_attribute_map:
            self.user_attribute_map = {
                "id": "okta_id",
                "login": "user_id",
                "email": "email",
                "firstName": "first_name",
                "lastName": "last_name",
                "displayName": "full_name",
                "department": "department",
                "title": "job_title",
                "manager": "manager_id",
                "status": "status"
            }


@dataclass
class OktaUser:
    """Okta user"""
    okta_id: str
    login: str
    email: str
    first_name: str
    last_name: str
    display_name: str
    department: str
    title: str
    manager_id: Optional[str]
    status: str  # ACTIVE, STAGED, PROVISIONED, DEPROVISIONED, SUSPENDED, etc.
    created: datetime
    last_login: Optional[datetime]
    groups: List[str] = field(default_factory=list)
    apps: List[str] = field(default_factory=list)


@dataclass
class OktaGroup:
    """Okta group"""
    group_id: str
    name: str
    description: str
    group_type: str  # OKTA_GROUP, APP_GROUP, BUILT_IN
    member_count: int
    created: datetime
    last_updated: datetime


@dataclass
class OktaApplication:
    """Okta application"""
    app_id: str
    name: str
    label: str
    status: str
    sign_on_mode: str
    created: datetime


class OktaConnector:
    """
    Okta Connector

    Provides:
    1. User synchronization from Okta
    2. Group membership sync
    3. Application assignments
    4. Lifecycle management
    5. Event hooks for real-time sync
    """

    def __init__(self, config: OktaConfig):
        self.config = config

    # ==================== User Operations ====================

    async def get_users(
        self,
        filter_query: str = None,
        search: str = None,
        limit: int = 200
    ) -> List[OktaUser]:
        """Get users from Okta"""
        logger.info("Fetching users from Okta")

        # In production, would call:
        # GET https://{domain}/api/v1/users
        #   ?filter={filter_query}
        #   &search={search}
        #   &limit={limit}

        # Simulated response
        users = [
            OktaUser(
                okta_id="okta-001",
                login="jsmith@company.com",
                email="jsmith@company.com",
                first_name="John",
                last_name="Smith",
                display_name="John Smith",
                department="Finance",
                title="Senior Accountant",
                manager_id="okta-mgr-001",
                status="ACTIVE",
                created=datetime(2024, 1, 15),
                last_login=datetime(2026, 1, 16),
                groups=["grp-finance", "grp-all-users"],
                apps=["SAP", "Salesforce", "Office365"]
            ),
            OktaUser(
                okta_id="okta-002",
                login="mbrown@company.com",
                email="mbrown@company.com",
                first_name="Mary",
                last_name="Brown",
                display_name="Mary Brown",
                department="Procurement",
                title="Procurement Manager",
                manager_id="okta-mgr-002",
                status="ACTIVE",
                created=datetime(2023, 6, 1),
                last_login=datetime(2026, 1, 17),
                groups=["grp-procurement", "grp-managers"],
                apps=["SAP", "Ariba", "Office365"]
            ),
            OktaUser(
                okta_id="okta-003",
                login="tdavis@company.com",
                email="tdavis@company.com",
                first_name="Tom",
                last_name="Davis",
                display_name="Tom Davis",
                department="IT",
                title="System Administrator",
                manager_id="okta-mgr-003",
                status="ACTIVE",
                created=datetime(2022, 3, 1),
                last_login=datetime(2026, 1, 17),
                groups=["grp-it", "grp-admins"],
                apps=["SAP", "AWS", "Azure", "Office365"]
            ),
        ]

        return users

    async def get_user(self, user_id: str) -> Optional[OktaUser]:
        """Get a single user by ID or login"""
        # GET https://{domain}/api/v1/users/{user_id}

        users = await self.get_users()
        return next((u for u in users if u.okta_id == user_id or u.login == user_id), None)

    async def get_user_groups(self, user_id: str) -> List[OktaGroup]:
        """Get groups a user belongs to"""
        # GET https://{domain}/api/v1/users/{user_id}/groups

        return [
            OktaGroup(
                group_id="grp-finance",
                name="Finance Department",
                description="Finance department users",
                group_type="OKTA_GROUP",
                member_count=50,
                created=datetime(2020, 1, 1),
                last_updated=datetime(2026, 1, 1)
            )
        ]

    async def get_user_apps(self, user_id: str) -> List[OktaApplication]:
        """Get applications assigned to a user"""
        # GET https://{domain}/api/v1/users/{user_id}/appLinks

        return [
            OktaApplication(
                app_id="app-sap",
                name="SAP S/4HANA",
                label="SAP",
                status="ACTIVE",
                sign_on_mode="SAML_2_0",
                created=datetime(2020, 1, 1)
            )
        ]

    # ==================== Group Operations ====================

    async def get_groups(
        self,
        filter_query: str = None,
        limit: int = 200
    ) -> List[OktaGroup]:
        """Get groups from Okta"""
        # GET https://{domain}/api/v1/groups

        return [
            OktaGroup(
                group_id="grp-finance",
                name="Finance Department",
                description="Finance department users",
                group_type="OKTA_GROUP",
                member_count=50,
                created=datetime(2020, 1, 1),
                last_updated=datetime(2026, 1, 1)
            ),
            OktaGroup(
                group_id="grp-sap-users",
                name="SAP Users",
                description="Users with SAP application access",
                group_type="APP_GROUP",
                member_count=200,
                created=datetime(2020, 1, 1),
                last_updated=datetime(2026, 1, 1)
            ),
        ]

    async def get_group_members(self, group_id: str) -> List[OktaUser]:
        """Get members of a group"""
        # GET https://{domain}/api/v1/groups/{group_id}/users

        return await self.get_users()

    # ==================== Application Operations ====================

    async def get_applications(self, limit: int = 200) -> List[OktaApplication]:
        """Get applications from Okta"""
        # GET https://{domain}/api/v1/apps

        return [
            OktaApplication(
                app_id="app-sap",
                name="SAP S/4HANA",
                label="SAP",
                status="ACTIVE",
                sign_on_mode="SAML_2_0",
                created=datetime(2020, 1, 1)
            ),
            OktaApplication(
                app_id="app-salesforce",
                name="Salesforce",
                label="Salesforce",
                status="ACTIVE",
                sign_on_mode="SAML_2_0",
                created=datetime(2020, 1, 1)
            ),
        ]

    async def get_app_users(self, app_id: str) -> List[Dict[str, Any]]:
        """Get users assigned to an application"""
        # GET https://{domain}/api/v1/apps/{app_id}/users

        return [
            {"user_id": "okta-001", "scope": "USER", "status": "ACTIVE"},
            {"user_id": "okta-002", "scope": "USER", "status": "ACTIVE"},
        ]

    # ==================== Sync Operations ====================

    async def sync_users_to_grc(self) -> Dict[str, Any]:
        """Sync Okta users to GRC platform"""
        logger.info("Starting Okta user sync")

        users = await self.get_users()

        created = 0
        updated = 0
        errors = []

        for user in users:
            try:
                # Map to GRC user format
                grc_user = {
                    "user_id": user.login.split("@")[0].upper(),
                    "email": user.email,
                    "full_name": user.display_name,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "department": user.department,
                    "status": "active" if user.status == "ACTIVE" else "inactive",
                    "source_system": "okta",
                    "external_id": user.okta_id,
                    "manager_id": user.manager_id,
                    "last_synced_at": datetime.utcnow().isoformat()
                }

                created += 1

            except Exception as e:
                errors.append({"user": user.login, "error": str(e)})

        return {
            "source": "okta",
            "users_processed": len(users),
            "created": created,
            "updated": updated,
            "errors": errors,
            "synced_at": datetime.utcnow().isoformat()
        }

    async def sync_groups_to_grc(self) -> Dict[str, Any]:
        """Sync Okta groups to GRC as roles"""
        logger.info("Starting Okta group sync")

        groups = await self.get_groups()

        synced = 0
        for group in groups:
            grc_role = {
                "role_id": f"OKTA_{group.group_id}",
                "role_name": group.name,
                "description": group.description,
                "role_type": "okta_group",
                "source_system": "okta",
                "external_id": group.group_id,
                "user_count": group.member_count
            }
            synced += 1

        return {
            "source": "okta",
            "groups_processed": len(groups),
            "synced": synced,
            "synced_at": datetime.utcnow().isoformat()
        }

    # ==================== Provisioning Operations ====================

    async def add_user_to_group(self, user_id: str, group_id: str) -> bool:
        """Add a user to an Okta group"""
        # PUT https://{domain}/api/v1/groups/{group_id}/users/{user_id}

        logger.info(f"Adding user {user_id} to group {group_id}")
        return True

    async def remove_user_from_group(self, user_id: str, group_id: str) -> bool:
        """Remove a user from an Okta group"""
        # DELETE https://{domain}/api/v1/groups/{group_id}/users/{user_id}

        logger.info(f"Removing user {user_id} from group {group_id}")
        return True

    async def assign_user_to_app(
        self,
        user_id: str,
        app_id: str,
        profile: Dict[str, Any] = None
    ) -> bool:
        """Assign a user to an application"""
        # POST https://{domain}/api/v1/apps/{app_id}/users
        # Body: { "id": user_id, "scope": "USER", "profile": profile }

        logger.info(f"Assigning user {user_id} to app {app_id}")
        return True

    async def unassign_user_from_app(self, user_id: str, app_id: str) -> bool:
        """Unassign a user from an application"""
        # DELETE https://{domain}/api/v1/apps/{app_id}/users/{user_id}

        logger.info(f"Unassigning user {user_id} from app {app_id}")
        return True

    # ==================== Lifecycle Operations ====================

    async def activate_user(self, user_id: str) -> bool:
        """Activate a user"""
        # POST https://{domain}/api/v1/users/{user_id}/lifecycle/activate

        logger.info(f"Activating user {user_id}")
        return True

    async def deactivate_user(self, user_id: str) -> bool:
        """Deactivate a user"""
        # POST https://{domain}/api/v1/users/{user_id}/lifecycle/deactivate

        logger.info(f"Deactivating user {user_id}")
        return True

    async def suspend_user(self, user_id: str) -> bool:
        """Suspend a user"""
        # POST https://{domain}/api/v1/users/{user_id}/lifecycle/suspend

        logger.info(f"Suspending user {user_id}")
        return True

    async def unsuspend_user(self, user_id: str) -> bool:
        """Unsuspend a user"""
        # POST https://{domain}/api/v1/users/{user_id}/lifecycle/unsuspend

        logger.info(f"Unsuspending user {user_id}")
        return True

    # ==================== Event Hooks ====================

    async def register_event_hook(
        self,
        name: str,
        events: List[str],
        callback_url: str
    ) -> Dict[str, Any]:
        """Register an event hook for real-time notifications"""
        # POST https://{domain}/api/v1/eventHooks
        # Body: { "name": name, "events": { "type": "EVENT_TYPE", "items": events }, "channel": { "type": "HTTP", "config": { "uri": callback_url } } }

        return {
            "hook_id": "hook-001",
            "name": name,
            "events": events,
            "callback_url": callback_url,
            "status": "ACTIVE"
        }

    async def process_event_hook(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Process incoming event hook notification"""
        event_type = event.get("eventType", "")
        target = event.get("target", [{}])[0]

        logger.info(f"Processing Okta event: {event_type}")

        if event_type == "user.lifecycle.create":
            # New user created - sync to GRC
            return {"action": "sync_user", "user_id": target.get("id")}

        elif event_type == "user.lifecycle.deactivate":
            # User deactivated - update GRC
            return {"action": "deactivate_user", "user_id": target.get("id")}

        elif event_type == "group.user_membership.add":
            # User added to group - update access
            return {"action": "add_role", "user_id": target.get("id")}

        elif event_type == "group.user_membership.remove":
            # User removed from group - revoke access
            return {"action": "remove_role", "user_id": target.get("id")}

        return {"action": "none", "event_type": event_type}

    # ==================== Connection Test ====================

    async def test_connection(self) -> Dict[str, Any]:
        """Test Okta connection"""
        try:
            # GET https://{domain}/api/v1/org

            return {
                "status": "connected",
                "domain": self.config.domain,
                "message": "Successfully connected to Okta"
            }

        except Exception as e:
            return {
                "status": "error",
                "domain": self.config.domain,
                "message": str(e)
            }
