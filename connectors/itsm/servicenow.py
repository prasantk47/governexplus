"""
ServiceNow Connector

Integration with ServiceNow REST API for ITSM ticket management
and identity governance. Supports Basic Auth and OAuth2 client credentials.

Table API reference: https://developer.servicenow.com/dev.do#!/reference/api/latest/rest/c_TableAPI
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum
import logging
import os

import httpx

from ..base import ConnectorFactory

_IS_PRODUCTION = os.getenv("APP_ENV", "").lower() == "production"

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

class AuthMethod(Enum):
    """Supported ServiceNow authentication methods."""
    BASIC = "basic"
    OAUTH2 = "oauth2"


@dataclass
class ServiceNowConfig:
    """ServiceNow connection configuration.

    Parameters
    ----------
    instance_url : str
        Full URL of the ServiceNow instance, e.g. https://mycompany.service-now.com.
    auth_method : AuthMethod
        BASIC for username/password, OAUTH2 for client-credentials grant.
    username / password : str | None
        Required when auth_method is BASIC.
    client_id / client_secret : str | None
        Required when auth_method is OAUTH2.
    timeout : int
        HTTP request timeout in seconds.
    verify_ssl : bool
        Whether to verify TLS certificates.
    use_mock : bool
        When True, return mock data instead of making real HTTP calls.
    """

    instance_url: str
    auth_method: AuthMethod = AuthMethod.BASIC

    # Basic auth
    username: Optional[str] = None
    password: Optional[str] = None

    # OAuth2 client credentials
    client_id: Optional[str] = None
    client_secret: Optional[str] = None

    # Connection settings
    timeout: int = 30
    verify_ssl: bool = True
    use_mock: bool = False

    # Default request headers / query params
    default_headers: Dict[str, str] = field(default_factory=dict)

    @property
    def table_api_url(self) -> str:
        return f"{self.instance_url.rstrip(chr(47))}/api/now/table"

    def __post_init__(self):
        if self.auth_method == AuthMethod.BASIC:
            if not self.username or not self.password:
                raise ValueError(
                    "username and password are required for Basic auth"
                )
        elif self.auth_method == AuthMethod.OAUTH2:
            if not self.client_id or not self.client_secret:
                raise ValueError(
                    "client_id and client_secret are required for OAuth2"
                )

# ---------------------------------------------------------------------------
# Mock data (used when use_mock=True or as fallback)
# ---------------------------------------------------------------------------

_MOCK_INCIDENTS: Dict[str, Dict[str, Any]] = {
    "INC0010001": {
        "sys_id": "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4",
        "number": "INC0010001",
        "short_description": "SoD violation detected for user JSMITH",
        "description": (
            "Segregation of Duties conflict: user holds both "
            "AP Manager and Vendor Maintenance roles."
        ),
        "state": "1",
        "priority": "2",
        "category": "Security",
        "assignment_group": "GRC Team",
        "caller_id": "admin",
        "sys_created_on": "2026-07-15 10:30:00",
        "sys_updated_on": "2026-07-15 10:30:00",
    },
    "INC0010002": {
        "sys_id": "b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5",
        "number": "INC0010002",
        "short_description": "Emergency access request - production issue",
        "description": (
            "Firefighter access required for SAP production system "
            "to resolve payment run failure."
        ),
        "state": "2",
        "priority": "1",
        "category": "Access",
        "assignment_group": "SAP Basis",
        "caller_id": "tdavis",
        "sys_created_on": "2026-07-20 08:15:00",
        "sys_updated_on": "2026-07-20 09:00:00",
    },
}

_MOCK_CHANGE_REQUESTS: Dict[str, Dict[str, Any]] = {
    "CHG0000001": {
        "sys_id": "c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6",
        "number": "CHG0000001",
        "short_description": "Remove excessive SAP_ALL profile from TDAVIS",
        "description": "Remediation: remove SAP_ALL profile assignment per GRC policy.",
        "state": "new",
        "type": "Standard",
        "priority": "2",
        "assignment_group": "SAP Security",
        "sys_created_on": "2026-07-22 14:00:00",
        "sys_updated_on": "2026-07-22 14:00:00",
    },
}

_MOCK_USERS: Dict[str, Dict[str, Any]] = {
    "u001": {
        "sys_id": "u001",
        "user_name": "john.smith",
        "first_name": "John",
        "last_name": "Smith",
        "email": "john.smith@company.com",
        "department": "Finance",
        "active": "true",
        "title": "Accounts Payable Manager",
    },
    "u002": {
        "sys_id": "u002",
        "user_name": "mary.brown",
        "first_name": "Mary",
        "last_name": "Brown",
        "email": "mary.brown@company.com",
        "department": "Procurement",
        "active": "true",
        "title": "Procurement Specialist",
    },
    "u003": {
        "sys_id": "u003",
        "user_name": "tom.davis",
        "first_name": "Tom",
        "last_name": "Davis",
        "email": "tom.davis@company.com",
        "department": "IT",
        "active": "true",
        "title": "SAP Basis Admin",
    },
}

_MOCK_GROUPS: List[Dict[str, Any]] = [
    {
        "sys_id": "g001",
        "group": {"value": "grp_grc", "display_value": "GRC Team"},
        "user": {"value": "u001"},
    },
    {
        "sys_id": "g002",
        "group": {"value": "grp_sap_sec", "display_value": "SAP Security"},
        "user": {"value": "u001"},
    },
    {
        "sys_id": "g003",
        "group": {"value": "grp_procurement", "display_value": "Procurement"},
        "user": {"value": "u002"},
    },
    {
        "sys_id": "g004",
        "group": {"value": "grp_basis", "display_value": "SAP Basis"},
        "user": {"value": "u003"},
    },
]

_MOCK_ROLES: List[Dict[str, Any]] = [
    {"sys_id": "r001", "name": "itil", "description": "ITIL user role"},
    {"sys_id": "r002", "name": "approver_user", "description": "Approval authority"},
    {"sys_id": "r003", "name": "admin", "description": "System administrator"},
    {"sys_id": "r004", "name": "sn_grc.manager", "description": "GRC Manager"},
]

# ---------------------------------------------------------------------------
# Connector
# ---------------------------------------------------------------------------

class ServiceNowConnector:
    """Async connector to the ServiceNow REST (Table) API.

    Provides helpers for ITSM ticket management (incidents, change requests,
    service catalog requests) and identity-governance operations (users, groups,
    roles).

    All public methods are async and use httpx.AsyncClient.
    """

    def __init__(self, config: ServiceNowConfig):
        if config.use_mock and _IS_PRODUCTION:
            raise RuntimeError(
                "ServiceNowConnector: mock mode is not allowed in production. "
                "Set use_mock=False and provide a real ServiceNow instance_url with "
                "valid credentials. Set APP_ENV != 'production' to enable simulation mode."
            )
        self.config = config
        self._client: Optional[httpx.AsyncClient] = None
        self._oauth_token: Optional[str] = None
        self._token_expiry: Optional[datetime] = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def connect(self) -> bool:
        """Create the underlying HTTP client and optionally obtain an
        OAuth2 token."""
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            **self.config.default_headers,
        }

        auth = None
        if self.config.auth_method == AuthMethod.BASIC:
            auth = httpx.BasicAuth(self.config.username, self.config.password)

        self._client = httpx.AsyncClient(
            base_url=self.config.instance_url.rstrip("/"),
            headers=headers,
            auth=auth,
            timeout=self.config.timeout,
            verify=self.config.verify_ssl,
        )

        if self.config.auth_method == AuthMethod.OAUTH2:
            await self._obtain_oauth_token()

        logger.info(
            "ServiceNow connector connected to %s", self.config.instance_url
        )
        return True

    async def disconnect(self) -> bool:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
        self._oauth_token = None
        self._token_expiry = None
        logger.info("ServiceNow connector disconnected")
        return True

    async def test_connection(self) -> Dict[str, Any]:
        """Verify connectivity by fetching instance metadata."""
        if self.config.use_mock:
            return {
                "status": "ok",
                "mode": "mock",
                "instance": self.config.instance_url,
            }

        resp = await self._request(
            "GET",
            "/api/now/table/sys_properties",
            params={
                "sysparm_query": "name=instance_name",
                "sysparm_limit": "1",
            },
        )
        return {
            "status": "ok",
            "mode": "live",
            "instance": self.config.instance_url,
            "details": resp,
        }

    # ------------------------------------------------------------------
    # OAuth2 helpers
    # ------------------------------------------------------------------

    async def _obtain_oauth_token(self) -> None:
        """Perform OAuth2 client-credentials grant."""
        token_url = f"{self.config.instance_url.rstrip(chr(47))}/oauth_token.do"
        async with httpx.AsyncClient(verify=self.config.verify_ssl) as tmp:
            resp = await tmp.post(
                token_url,
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.config.client_id,
                    "client_secret": self.config.client_secret,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            self._oauth_token = data["access_token"]
            logger.info("OAuth2 token obtained for ServiceNow instance")

    # ------------------------------------------------------------------
    # Low-level HTTP helper
    # ------------------------------------------------------------------

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        json_body: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Execute an HTTP request against the ServiceNow REST API.

        Raises httpx.HTTPStatusError on 4xx/5xx responses.
        """
        if self._client is None:
            await self.connect()

        headers: Dict[str, str] = {}
        if self._oauth_token:
            headers["Authorization"] = f"Bearer {self._oauth_token}"

        resp = await self._client.request(
            method,
            path,
            params=params,
            json=json_body,
            headers=headers,
        )
        resp.raise_for_status()
        return resp.json()

    # ==================================================================
    # ITSM Operations (Table API)
    # ==================================================================

    async def create_incident(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create an incident record."""
        if self.config.use_mock:
            mock_number = f"INC{10003 + len(_MOCK_INCIDENTS):07d}"
            record = {
                "sys_id": f"mock_{mock_number}",
                "number": mock_number,
                **data,
                "state": data.get("state", "1"),
                "sys_created_on": datetime.utcnow().isoformat(),
                "sys_updated_on": datetime.utcnow().isoformat(),
            }
            logger.info("Mock incident created: %s", mock_number)
            return {"result": record}

        return await self._request(
            "POST", "/api/now/table/incident", json_body=data
        )

    async def get_incident(self, sys_id: str) -> Dict[str, Any]:
        """Retrieve a single incident by sys_id."""
        if self.config.use_mock:
            for inc in _MOCK_INCIDENTS.values():
                if inc["sys_id"] == sys_id or inc["number"] == sys_id:
                    return {"result": inc}
            return {"result": {}}

        return await self._request(
            "GET", f"/api/now/table/incident/{sys_id}"
        )

    async def update_incident(
        self, sys_id: str, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update an existing incident."""
        if self.config.use_mock:
            for inc in _MOCK_INCIDENTS.values():
                if inc["sys_id"] == sys_id or inc["number"] == sys_id:
                    inc.update(data)
                    inc["sys_updated_on"] = datetime.utcnow().isoformat()
                    return {"result": inc}
            return {"result": {}}

        return await self._request(
            "PATCH", f"/api/now/table/incident/{sys_id}", json_body=data
        )

    async def create_change_request(
        self, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a change request."""
        if self.config.use_mock:
            mock_number = f"CHG{2 + len(_MOCK_CHANGE_REQUESTS):07d}"
            record = {
                "sys_id": f"mock_{mock_number}",
                "number": mock_number,
                **data,
                "state": data.get("state", "new"),
                "sys_created_on": datetime.utcnow().isoformat(),
                "sys_updated_on": datetime.utcnow().isoformat(),
            }
            logger.info("Mock change request created: %s", mock_number)
            return {"result": record}

        return await self._request(
            "POST", "/api/now/table/change_request", json_body=data
        )

    async def get_change_request(self, sys_id: str) -> Dict[str, Any]:
        """Retrieve a single change request by sys_id."""
        if self.config.use_mock:
            for cr in _MOCK_CHANGE_REQUESTS.values():
                if cr["sys_id"] == sys_id or cr["number"] == sys_id:
                    return {"result": cr}
            return {"result": {}}

        return await self._request(
            "GET", f"/api/now/table/change_request/{sys_id}"
        )

    async def create_request(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a service-catalog request (sc_request)."""
        if self.config.use_mock:
            mock_number = f"REQ{1:07d}"
            record = {
                "sys_id": f"mock_{mock_number}",
                "number": mock_number,
                **data,
                "state": data.get("state", "requested"),
                "sys_created_on": datetime.utcnow().isoformat(),
                "sys_updated_on": datetime.utcnow().isoformat(),
            }
            logger.info("Mock catalog request created: %s", mock_number)
            return {"result": record}

        return await self._request(
            "POST", "/api/now/table/sc_request", json_body=data
        )

    async def search_tickets(
        self,
        query: str,
        table: str = "incident",
        *,
        limit: int = 50,
        offset: int = 0,
        order_by: str = "-sys_created_on",
        fields: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Search tickets using ServiceNow encoded query syntax."""
        if self.config.use_mock:
            source = (
                _MOCK_INCIDENTS
                if table == "incident"
                else _MOCK_CHANGE_REQUESTS
            )
            results = list(source.values())
            return {"result": results[:limit]}

        params: Dict[str, Any] = {
            "sysparm_query": query,
            "sysparm_limit": str(limit),
            "sysparm_offset": str(offset),
            "sysparm_display_value": "true",
            "sysparm_orderby": order_by,
        }
        if fields:
            params["sysparm_fields"] = ",".join(fields)

        return await self._request(
            "GET", f"/api/now/table/{table}", params=params
        )

    # ==================================================================
    # Identity / Governance Operations
    # ==================================================================

    async def get_users(
        self,
        filters: Optional[Dict[str, str]] = None,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """Retrieve users from sys_user table."""
        if self.config.use_mock:
            users = list(_MOCK_USERS.values())
            if filters:
                for key, val in filters.items():
                    users = [
                        u for u in users
                        if str(u.get(key, "")).lower() == str(val).lower()
                    ]
            return {"result": users[offset : offset + limit]}

        query_parts = [
            f"{k}={v}" for k, v in (filters or {}).items()
        ]
        params: Dict[str, Any] = {
            "sysparm_limit": str(limit),
            "sysparm_offset": str(offset),
        }
        if query_parts:
            params["sysparm_query"] = "^".join(query_parts)

        return await self._request(
            "GET", "/api/now/table/sys_user", params=params
        )

    async def get_user(self, sys_id: str) -> Dict[str, Any]:
        """Retrieve a single user by sys_id."""
        if self.config.use_mock:
            user = _MOCK_USERS.get(sys_id, {})
            return {"result": user}

        return await self._request(
            "GET", f"/api/now/table/sys_user/{sys_id}"
        )

    async def get_user_groups(self, user_sys_id: str) -> Dict[str, Any]:
        """Retrieve groups for a user via sys_user_grmember table."""
        if self.config.use_mock:
            memberships = [
                g for g in _MOCK_GROUPS
                if g["user"]["value"] == user_sys_id
            ]
            return {"result": memberships}

        return await self._request(
            "GET",
            "/api/now/table/sys_user_grmember",
            params={
                "sysparm_query": f"user={user_sys_id}",
                "sysparm_display_value": "true",
            },
        )

    async def disable_user(self, sys_id: str) -> Dict[str, Any]:
        """Disable a user by setting active=false."""
        if self.config.use_mock:
            if sys_id in _MOCK_USERS:
                _MOCK_USERS[sys_id]["active"] = "false"
                return {"result": _MOCK_USERS[sys_id]}
            return {"result": {}}

        return await self._request(
            "PATCH",
            f"/api/now/table/sys_user/{sys_id}",
            json_body={"active": "false"},
        )

    async def get_roles(
        self,
        filters: Optional[Dict[str, str]] = None,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """Retrieve roles from sys_user_role table."""
        if self.config.use_mock:
            roles = list(_MOCK_ROLES)
            if filters:
                for key, val in filters.items():
                    roles = [
                        r for r in roles
                        if str(r.get(key, "")).lower() == str(val).lower()
                    ]
            return {"result": roles[offset : offset + limit]}

        query_parts = [
            f"{k}={v}" for k, v in (filters or {}).items()
        ]
        params: Dict[str, Any] = {
            "sysparm_limit": str(limit),
            "sysparm_offset": str(offset),
        }
        if query_parts:
            params["sysparm_query"] = "^".join(query_parts)

        return await self._request(
            "GET", "/api/now/table/sys_user_role", params=params
        )

    # ==================================================================
    # GRC Integration helpers
    # ==================================================================

    async def link_access_request(
        self,
        request_id: str,
        ticket_number: str,
    ) -> Dict[str, Any]:
        """Link a GovernexPlus access request to a ServiceNow ticket.

        Adds a work note to the ServiceNow ticket referencing the internal
        access-request ID so both systems stay in sync.

        Parameters
        ----------
        request_id : str
            GovernexPlus internal access request ID.
        ticket_number : str
            ServiceNow ticket number (e.g. INC0010001).
        """
        work_note = (
            f"[GovernexPlus] Access request {request_id} has been linked "
            f"to this ticket.\n"
            f"Track the request in GovernexPlus for approval status and "
            f"SoD analysis."
        )

        if self.config.use_mock:
            logger.info(
                "Mock: linked access request %s to ticket %s",
                request_id,
                ticket_number,
            )
            return {
                "result": {
                    "linked": True,
                    "request_id": request_id,
                    "ticket_number": ticket_number,
                    "work_note": work_note,
                }
            }

        # Determine table from ticket prefix
        if ticket_number.startswith("INC"):
            table = "incident"
        elif ticket_number.startswith("CHG"):
            table = "change_request"
        elif ticket_number.startswith("REQ"):
            table = "sc_request"
        else:
            table = "incident"

        # Look up the ticket by number to get sys_id
        lookup = await self._request(
            "GET",
            f"/api/now/table/{table}",
            params={
                "sysparm_query": f"number={ticket_number}",
                "sysparm_limit": "1",
                "sysparm_fields": "sys_id,number",
            },
        )
        results = lookup.get("result", [])
        if not results:
            raise ValueError(
                f"Ticket {ticket_number} not found in ServiceNow"
            )

        sys_id = results[0]["sys_id"]
        return await self._request(
            "PATCH",
            f"/api/now/table/{table}/{sys_id}",
            json_body={"work_notes": work_note},
        )

    async def create_grc_ticket(
        self, violation: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a ServiceNow incident from a GovernexPlus SoD violation.

        Parameters
        ----------
        violation : dict
            SoD violation details. Expected keys:
            - rule_id (str): the SoD rule identifier
            - rule_name (str): human-readable rule name
            - user_id (str): affected user
            - risk_level (str): high | medium | low
            - conflicting_roles (list[str]): roles in conflict
            - description (str, optional): additional detail

        Returns
        -------
        dict
            The created incident record.
        """
        risk = violation.get("risk_level", "medium").lower()
        priority_map = {
            "critical": "1",
            "high": "1",
            "medium": "2",
            "low": "3",
        }
        priority = priority_map.get(risk, "2")

        conflicting = ", ".join(
            violation.get("conflicting_roles", [])
        )
        short_desc = (
            f"SoD Violation [{violation.get('rule_id', 'N/A')}]: "
            f"{violation.get('rule_name', 'Unnamed Rule')} - "
            f"User {violation.get('user_id', 'unknown')}"
        )
        description = (
            f"GovernexPlus has detected a Segregation of Duties "
            f"violation.\n\n"
            f"Rule: {violation.get('rule_id', 'N/A')} - "
            f"{violation.get('rule_name', '')}\n"
            f"User: {violation.get('user_id', 'unknown')}\n"
            f"Risk Level: {risk.upper()}\n"
            f"Conflicting Roles: {conflicting}\n\n"
            f"{violation.get('description', '')}"
        )

        incident_data = {
            "short_description": short_desc,
            "description": description,
            "priority": priority,
            "category": "Security",
            "subcategory": "GRC - SoD Violation",
            "impact": "2" if risk in ("critical", "high") else "3",
            "urgency": priority,
            "assignment_group": "GRC Team",
            "caller_id": "governexplus_integration",
        }

        return await self.create_incident(incident_data)


# ---------------------------------------------------------------------------
# Register with ConnectorFactory
# ---------------------------------------------------------------------------
ConnectorFactory.register("servicenow", ServiceNowConnector)
