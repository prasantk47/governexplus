"""
SAP SuccessFactors HRIS Connector

Integration with SAP SuccessFactors for HR data synchronization and JML automation.
Uses OData API v2 with mock fallback for development.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime, date
import logging
import os

logger = logging.getLogger(__name__)

# Optional httpx for real API calls
try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    if os.getenv("APP_ENV", "").lower() == "production":
        raise RuntimeError(
            "SuccessFactors connector requires httpx package in production. "
            "pip install httpx"
        )
    HAS_HTTPX = False
    logger.warning("httpx not installed — SuccessFactors connector will use mock data")


@dataclass
class SuccessFactorsConfig:
    """SuccessFactors connection configuration"""
    api_url: str = ""  # e.g., "https://api4.successfactors.com"
    company_id: str = ""
    username: str = ""
    password: str = ""  # Would be retrieved from secrets manager

    # OAuth settings (SAML Bearer Assertion flow)
    client_id: str = ""
    client_secret: str = ""
    assertion: str = ""  # SAML assertion for OAuth
    use_oauth: bool = False

    # Sync options
    sync_employees: bool = True
    sync_organizations: bool = True
    sync_positions: bool = True
    sync_job_info: bool = True

    # Mock mode
    use_mock: bool = True

    @classmethod
    def from_env(cls) -> "SuccessFactorsConfig":
        """Create config from environment variables"""
        return cls(
            api_url=os.getenv("SF_API_URL", ""),
            company_id=os.getenv("SF_COMPANY_ID", ""),
            username=os.getenv("SF_USERNAME", ""),
            password=os.getenv("SF_PASSWORD", ""),
            client_id=os.getenv("SF_CLIENT_ID", ""),
            client_secret=os.getenv("SF_CLIENT_SECRET", ""),
            use_oauth=os.getenv("SF_USE_OAUTH", "false").lower() == "true",
            use_mock=os.getenv("SF_USE_MOCK", "true").lower() == "true",
        )


@dataclass
class SFEmployee:
    """SuccessFactors employee"""
    person_id: str
    user_id: str
    email: str
    first_name: str
    last_name: str
    display_name: str
    hire_date: date
    job_title: str
    department: str
    division: str
    cost_center: str
    manager_id: Optional[str]
    location: str
    employment_type: str  # Full-time, Part-time, Contractor
    status: str  # Active, Terminated, On Leave
    termination_date: Optional[date] = None


@dataclass
class SFOrganization:
    """SuccessFactors organization unit"""
    org_id: str
    name: str
    org_type: str
    parent_id: Optional[str]
    head_of_unit_id: Optional[str]


class SuccessFactorsConnector:
    """
    SAP SuccessFactors Connector

    Provides:
    1. Employee synchronization via OData API v2
    2. Organization hierarchy sync
    3. JML event processing
    4. Real-time event notifications via Integration Center
    5. Mock fallback for development/testing
    """

    def __init__(self, config: SuccessFactorsConfig):
        self.config = config
        self._client: Optional[Any] = None
        self._access_token: Optional[str] = None

    @property
    def _use_mock(self) -> bool:
        _is_production = os.getenv("APP_ENV", "").lower() == "production"
        wants_mock = self.config.use_mock or not HAS_HTTPX or not self.config.api_url
        if wants_mock and _is_production:
            raise RuntimeError(
                "SuccessFactorsConnector: mock/simulation mode is not allowed in production. "
                "Set SF_API_URL, SF_COMPANY_ID, SF_USERNAME/SF_PASSWORD (or OAuth credentials), "
                "and SF_USE_MOCK=false. "
                "Set APP_ENV != 'production' to enable simulation mode."
            )
        return wants_mock

    def _get_client(self) -> "httpx.AsyncClient":
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.config.api_url.rstrip("/"),
                timeout=30.0,
                verify=True,
            )
        return self._client

    # ==================== Authentication ====================

    async def authenticate(self) -> bool:
        """Authenticate with SuccessFactors"""
        if self._use_mock:
            logger.info("SuccessFactors mock mode — skipping authentication")
            self._access_token = "mock_token"
            return True

        try:
            client = self._get_client()

            if self.config.use_oauth:
                # OAuth 2.0 SAML Bearer Assertion flow
                resp = await client.post(
                    "/oauth/token",
                    data={
                        "company_id": self.config.company_id,
                        "client_id": self.config.client_id,
                        "grant_type": "urn:ietf:params:oauth:grant-type:saml2-bearer",
                        "assertion": self.config.assertion,
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                self._access_token = data["access_token"]
                logger.info(f"SuccessFactors OAuth authentication successful: {self.config.company_id}")
            else:
                # Basic authentication test
                resp = await client.get(
                    "/odata/v2/User",
                    auth=(f"{self.config.username}@{self.config.company_id}", self.config.password),
                    params={"$top": 1, "$format": "json"},
                )
                resp.raise_for_status()
                self._access_token = "basic_auth"
                logger.info(f"SuccessFactors basic auth successful: {self.config.company_id}")

            return True

        except Exception as e:
            logger.error(f"SuccessFactors authentication failed: {e}")
            return False

    def _auth_kwargs(self) -> Dict[str, Any]:
        headers = {"Accept": "application/json"}
        kwargs: Dict[str, Any] = {"headers": headers}
        if self._access_token and self._access_token not in ("basic_auth", "mock_token"):
            headers["Authorization"] = f"Bearer {self._access_token}"
        elif self._access_token == "basic_auth":
            kwargs["auth"] = (
                f"{self.config.username}@{self.config.company_id}",
                self.config.password,
            )
        return kwargs

    # ==================== Employee Operations ====================

    async def get_employees(
        self,
        active_only: bool = True,
        modified_since: datetime = None
    ) -> List[SFEmployee]:
        """Get employees from SuccessFactors"""
        if self._use_mock:
            return self._mock_employees()

        logger.info("Fetching employees from SuccessFactors OData API")
        client = self._get_client()

        employees = []
        skip = 0
        top = 100

        while True:
            filter_parts = []
            if active_only:
                filter_parts.append("status eq 'A'")
            if modified_since:
                filter_parts.append(f"lastModifiedDateTime ge datetimeoffset'{modified_since.isoformat()}'")

            params: Dict[str, Any] = {
                "$format": "json",
                "$top": top,
                "$skip": skip,
                "$expand": "empInfo,empInfo/jobInfoNav",
            }
            if filter_parts:
                params["$filter"] = " and ".join(filter_parts)

            resp = await client.get("/odata/v2/User", params=params, **self._auth_kwargs())
            resp.raise_for_status()
            data = resp.json()

            results = data.get("d", {}).get("results", [])
            if not results:
                break

            for u in results:
                job_info = {}
                emp_info = u.get("empInfo", {})
                if emp_info:
                    job_nav = emp_info.get("jobInfoNav", {})
                    if isinstance(job_nav, dict):
                        job_results = job_nav.get("results", [])
                        if job_results:
                            job_info = job_results[0]
                    elif isinstance(job_nav, list) and job_nav:
                        job_info = job_nav[0]

                emp = SFEmployee(
                    person_id=u.get("personIdExternal", u.get("userId", "")),
                    user_id=u.get("userId", ""),
                    email=u.get("email", ""),
                    first_name=u.get("firstName", ""),
                    last_name=u.get("lastName", ""),
                    display_name=f"{u.get('firstName', '')} {u.get('lastName', '')}".strip(),
                    hire_date=_parse_sf_date(u.get("hireDate", "")),
                    job_title=job_info.get("jobTitle", u.get("title", "")),
                    department=job_info.get("department", u.get("department", "")),
                    division=job_info.get("division", u.get("division", "")),
                    cost_center=job_info.get("costCenter", ""),
                    manager_id=u.get("manager", ""),
                    location=job_info.get("location", u.get("location", "")),
                    employment_type=job_info.get("employeeClass", "Full-time"),
                    status="Active" if u.get("status", "A") == "A" else "Terminated",
                )
                employees.append(emp)

            skip += top
            if len(results) < top:
                break

        logger.info(f"Fetched {len(employees)} employees from SuccessFactors")
        return employees

    async def get_employee(self, user_id: str) -> Optional[SFEmployee]:
        """Get a single employee"""
        if self._use_mock:
            employees = self._mock_employees()
            return next((e for e in employees if e.user_id == user_id), None)

        client = self._get_client()
        resp = await client.get(
            f"/odata/v2/User('{user_id}')",
            params={"$format": "json", "$expand": "empInfo,empInfo/jobInfoNav"},
            **self._auth_kwargs(),
        )
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        u = resp.json().get("d", {})

        job_info = {}
        emp_info = u.get("empInfo", {})
        if emp_info:
            job_nav = emp_info.get("jobInfoNav", {})
            if isinstance(job_nav, dict):
                job_results = job_nav.get("results", [])
                if job_results:
                    job_info = job_results[0]

        return SFEmployee(
            person_id=u.get("personIdExternal", u.get("userId", "")),
            user_id=u.get("userId", ""),
            email=u.get("email", ""),
            first_name=u.get("firstName", ""),
            last_name=u.get("lastName", ""),
            display_name=f"{u.get('firstName', '')} {u.get('lastName', '')}".strip(),
            hire_date=_parse_sf_date(u.get("hireDate", "")),
            job_title=job_info.get("jobTitle", u.get("title", "")),
            department=job_info.get("department", u.get("department", "")),
            division=job_info.get("division", u.get("division", "")),
            cost_center=job_info.get("costCenter", ""),
            manager_id=u.get("manager", ""),
            location=job_info.get("location", u.get("location", "")),
            employment_type=job_info.get("employeeClass", "Full-time"),
            status="Active" if u.get("status", "A") == "A" else "Terminated",
        )

    async def get_employee_manager(self, user_id: str) -> Optional[SFEmployee]:
        """Get an employee's manager"""
        employee = await self.get_employee(user_id)
        if employee and employee.manager_id:
            return await self.get_employee(employee.manager_id)
        return None

    # ==================== Organization Operations ====================

    async def get_organizations(self) -> List[SFOrganization]:
        """Get organization units from SuccessFactors"""
        if self._use_mock:
            return self._mock_organizations()

        client = self._get_client()
        resp = await client.get(
            "/odata/v2/FODepartment",
            params={"$format": "json", "$top": 500},
            **self._auth_kwargs(),
        )
        resp.raise_for_status()
        data = resp.json()

        orgs = []
        for o in data.get("d", {}).get("results", []):
            orgs.append(SFOrganization(
                org_id=o.get("externalCode", ""),
                name=o.get("name_defaultValue", o.get("name", "")),
                org_type="Department",
                parent_id=o.get("parent", None),
                head_of_unit_id=o.get("headOfUnit", None),
            ))

        return orgs

    # ==================== JML Event Processing ====================

    async def get_new_hires(
        self,
        start_date: date,
        end_date: date
    ) -> List[Dict[str, Any]]:
        """Get new hire events"""
        if self._use_mock:
            return self._mock_new_hires()

        client = self._get_client()
        params = {
            "$format": "json",
            "$filter": f"startDate ge datetime'{start_date.isoformat()}' and eventReason eq 'HIRNEW'",
            "$top": 200,
        }
        resp = await client.get("/odata/v2/EmpJob", params=params, **self._auth_kwargs())
        resp.raise_for_status()
        data = resp.json()

        events = []
        for e in data.get("d", {}).get("results", []):
            events.append({
                "event_type": "hire",
                "person_id": e.get("userId", ""),
                "user_id": e.get("userId", ""),
                "name": e.get("userId", ""),  # Would need User entity lookup
                "email": "",
                "department": e.get("department", ""),
                "job_title": e.get("jobTitle", ""),
                "hire_date": e.get("startDate", ""),
                "manager_id": e.get("managerId", ""),
            })

        return events

    async def get_terminations(
        self,
        start_date: date,
        end_date: date
    ) -> List[Dict[str, Any]]:
        """Get termination events"""
        if self._use_mock:
            return self._mock_terminations()

        client = self._get_client()
        params = {
            "$format": "json",
            "$filter": f"endDate ge datetime'{start_date.isoformat()}' and (eventReason eq 'TERM' or eventReason eq 'TERVOL')",
            "$top": 200,
        }
        resp = await client.get("/odata/v2/EmpJob", params=params, **self._auth_kwargs())
        resp.raise_for_status()
        data = resp.json()

        events = []
        for e in data.get("d", {}).get("results", []):
            events.append({
                "event_type": "termination",
                "person_id": e.get("userId", ""),
                "user_id": e.get("userId", ""),
                "name": e.get("userId", ""),
                "termination_date": e.get("endDate", ""),
                "termination_reason": e.get("eventReason", ""),
            })

        return events

    async def get_transfers(
        self,
        start_date: date,
        end_date: date
    ) -> List[Dict[str, Any]]:
        """Get transfer events"""
        if self._use_mock:
            return self._mock_transfers()

        client = self._get_client()
        params = {
            "$format": "json",
            "$filter": f"startDate ge datetime'{start_date.isoformat()}' and eventReason eq 'DATATRANS'",
            "$top": 200,
        }
        resp = await client.get("/odata/v2/EmpJob", params=params, **self._auth_kwargs())
        resp.raise_for_status()
        data = resp.json()

        events = []
        for e in data.get("d", {}).get("results", []):
            events.append({
                "event_type": "transfer",
                "person_id": e.get("userId", ""),
                "user_id": e.get("userId", ""),
                "name": e.get("userId", ""),
                "effective_date": e.get("startDate", ""),
                "old_department": "",  # Would need previous record
                "new_department": e.get("department", ""),
                "old_manager_id": "",
                "new_manager_id": e.get("managerId", ""),
            })

        return events

    async def process_jml_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Process a JML event and return required GRC actions"""
        event_type = event.get("event_type")

        if event_type == "hire":
            return {
                "action": "provision",
                "user_id": event.get("user_id", event.get("person_id", "")),
                "name": event["name"],
                "email": event.get("email", ""),
                "department": event.get("department", ""),
                "recommended_roles": self._get_default_roles(event.get("department", "")),
                "effective_date": event.get("hire_date", ""),
            }

        elif event_type == "termination":
            return {
                "action": "deprovision",
                "user_id": event.get("user_id", event.get("person_id", "")),
                "name": event["name"],
                "revoke_all_access": True,
                "effective_date": event["termination_date"],
            }

        elif event_type == "transfer":
            return {
                "action": "modify",
                "user_id": event.get("user_id", event.get("person_id", "")),
                "name": event["name"],
                "roles_to_remove": self._get_default_roles(event.get("old_department", "")),
                "roles_to_add": self._get_default_roles(event.get("new_department", "")),
                "new_manager": event.get("new_manager_id", ""),
                "effective_date": event.get("effective_date", ""),
            }

        return {"action": "none"}

    def _get_default_roles(self, department: str) -> List[str]:
        """Get default roles based on department"""
        role_mapping = {
            "Finance": ["Z_FI_BASIC", "Z_FI_REPORTS"],
            "Procurement": ["Z_MM_BASIC", "Z_MM_REPORTS"],
            "IT": ["Z_IT_BASIC"],
            "HR": ["Z_HR_BASIC"],
            "Sales": ["Z_SD_BASIC"],
            "Marketing": ["Z_MKT_BASIC"],
        }
        return role_mapping.get(department, ["Z_BASIC_USER"])

    # ==================== Sync Operations ====================

    async def sync_employees_to_grc(self) -> Dict[str, Any]:
        """Sync SuccessFactors employees to GRC platform"""
        logger.info("Starting SuccessFactors employee sync")

        from db.database import db_manager
        from db.models.user import User

        employees = await self.get_employees()

        synced = 0
        for emp in employees:
            grc_user = {
                "user_id": emp.user_id,
                "email": emp.email,
                "full_name": emp.display_name,
                "first_name": emp.first_name,
                "last_name": emp.last_name,
                "department": emp.department,
                "cost_center": emp.cost_center,
                "status": "active" if emp.status == "Active" else "inactive",
                "source_system": "successfactors",
                "external_id": emp.person_id,
                "manager_id": emp.manager_id,
            }
            try:
                with db_manager.session_scope() as db:
                    tenant_id = grc_user.get("tenant_id", "tenant_default")
                    existing = db.query(User).filter_by(
                        user_id=grc_user["user_id"],
                        tenant_id=tenant_id,
                    ).first()
                    if existing:
                        for key, value in grc_user.items():
                            if hasattr(existing, key) and key != "user_id":
                                setattr(existing, key, value)
                    else:
                        db_user = User(
                            user_id=grc_user["user_id"],
                            username=grc_user.get("user_id", ""),
                            email=grc_user.get("email", ""),
                            full_name=grc_user.get("full_name", ""),
                            department=grc_user.get("department", ""),
                            status=grc_user.get("status", "active"),
                            user_type="employee",
                            tenant_id=tenant_id,
                        )
                        db.add(db_user)
                synced += 1
            except Exception as e:
                logger.warning(f"Failed to persist employee {grc_user['user_id']}: {e}")

        return {
            "source": "successfactors",
            "employees_processed": len(employees),
            "synced": synced,
            "synced_at": datetime.utcnow().isoformat(),
        }

    # ==================== Connection Test ====================

    async def test_connection(self) -> Dict[str, Any]:
        """Test SuccessFactors connection"""
        if self._use_mock:
            return {
                "status": "connected",
                "mode": "mock",
                "company_id": self.config.company_id or "(mock)",
                "message": "Mock mode active — no real SuccessFactors connection",
            }

        try:
            authenticated = await self.authenticate()
            if authenticated:
                return {
                    "status": "connected",
                    "mode": "live",
                    "company_id": self.config.company_id,
                    "message": "Successfully connected to SuccessFactors",
                }
            return {
                "status": "failed",
                "company_id": self.config.company_id,
                "message": "Authentication failed",
            }
        except Exception as e:
            return {
                "status": "error",
                "company_id": self.config.company_id,
                "message": str(e),
            }

    async def close(self):
        """Close the HTTP client"""
        if self._client:
            await self._client.aclose()
            self._client = None

    # ==================== Mock Data ====================

    def _mock_employees(self) -> List[SFEmployee]:
        return [
            SFEmployee(
                person_id="SF001", user_id="JSMITH",
                email="jsmith@company.com", first_name="John", last_name="Smith",
                display_name="John Smith", hire_date=date(2024, 1, 15),
                job_title="Senior Accountant", department="Finance",
                division="Corporate", cost_center="CC1001",
                manager_id="SF_MGR001", location="New York",
                employment_type="Full-time", status="Active",
            ),
            SFEmployee(
                person_id="SF002", user_id="MBROWN",
                email="mbrown@company.com", first_name="Mary", last_name="Brown",
                display_name="Mary Brown", hire_date=date(2023, 6, 1),
                job_title="Procurement Manager", department="Procurement",
                division="Operations", cost_center="CC2001",
                manager_id="SF_MGR002", location="Chicago",
                employment_type="Full-time", status="Active",
            ),
            SFEmployee(
                person_id="SF006", user_id="KJONES",
                email="kjones@company.com", first_name="Karen", last_name="Jones",
                display_name="Karen Jones", hire_date=date(2025, 3, 10),
                job_title="HR Business Partner", department="HR",
                division="Corporate", cost_center="CC4001",
                manager_id="SF_MGR004", location="Dallas",
                employment_type="Full-time", status="Active",
            ),
        ]

    def _mock_organizations(self) -> List[SFOrganization]:
        return [
            SFOrganization(org_id="DEPT_FIN", name="Finance Department",
                           org_type="Department", parent_id="DIV_CORP", head_of_unit_id="SF_MGR001"),
            SFOrganization(org_id="DEPT_PROC", name="Procurement Department",
                           org_type="Department", parent_id="DIV_OPS", head_of_unit_id="SF_MGR002"),
            SFOrganization(org_id="DEPT_HR", name="Human Resources",
                           org_type="Department", parent_id="DIV_CORP", head_of_unit_id="SF_MGR004"),
        ]

    def _mock_new_hires(self) -> List[Dict[str, Any]]:
        return [{
            "event_type": "hire",
            "person_id": "SF003", "user_id": "NEWUSER",
            "name": "New Employee", "email": "newuser@company.com",
            "department": "IT", "job_title": "Software Developer",
            "hire_date": date(2026, 2, 1).isoformat(), "manager_id": "SF_MGR003",
        }]

    def _mock_terminations(self) -> List[Dict[str, Any]]:
        return [{
            "event_type": "termination",
            "person_id": "SF004", "user_id": "TERMUSER",
            "name": "Departing Employee",
            "termination_date": date(2026, 1, 31).isoformat(),
            "termination_reason": "TERVOL",
        }]

    def _mock_transfers(self) -> List[Dict[str, Any]]:
        return [{
            "event_type": "transfer",
            "person_id": "SF005", "user_id": "TRANSUSER",
            "name": "Transferring Employee",
            "effective_date": date(2026, 2, 15).isoformat(),
            "old_department": "Sales", "new_department": "Marketing",
            "old_manager_id": "SF_MGR_SALES", "new_manager_id": "SF_MGR_MKT",
        }]


def _parse_sf_date(date_val: Any) -> date:
    """Parse SuccessFactors date (OData format or ISO string)"""
    if not date_val:
        return date.today()
    if isinstance(date_val, str):
        # Handle OData date format: /Date(1234567890000)/
        if date_val.startswith("/Date("):
            try:
                ms = int(date_val.replace("/Date(", "").replace(")/", "").split("+")[0].split("-")[0])
                return datetime.utcfromtimestamp(ms / 1000).date()
            except (ValueError, TypeError):
                return date.today()
        # ISO format
        try:
            return date.fromisoformat(date_val[:10])
        except (ValueError, TypeError):
            return date.today()
    return date.today()
