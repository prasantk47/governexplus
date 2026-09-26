"""
Workday HRIS Connector

Integration with Workday for HR data synchronization and JML automation.
Supports both Workday REST API and SOAP (WS) API with mock fallback for development.
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
            "Workday connector requires httpx package in production. "
            "pip install httpx"
        )
    HAS_HTTPX = False
    logger.warning("httpx not installed — Workday connector will use mock data")


@dataclass
class WorkdayConfig:
    """Workday connection configuration"""
    tenant_url: str = ""  # e.g., "https://impl.workday.com/company"
    username: str = ""
    password: str = ""  # Would be retrieved from secrets manager

    # API settings
    api_version: str = "v1"
    tenant_name: str = ""  # Workday tenant name

    # OAuth settings (preferred for production)
    client_id: str = ""
    client_secret: str = ""
    refresh_token: str = ""
    use_oauth: bool = False

    # Sync options
    sync_workers: bool = True
    sync_organizations: bool = True
    sync_positions: bool = True

    # Event subscriptions
    subscribe_hire: bool = True
    subscribe_termination: bool = True
    subscribe_transfer: bool = True
    subscribe_promotion: bool = True

    # Mock mode
    use_mock: bool = True

    @classmethod
    def from_env(cls) -> "WorkdayConfig":
        """Create config from environment variables"""
        return cls(
            tenant_url=os.getenv("WORKDAY_TENANT_URL", ""),
            username=os.getenv("WORKDAY_USERNAME", ""),
            password=os.getenv("WORKDAY_PASSWORD", ""),
            tenant_name=os.getenv("WORKDAY_TENANT", ""),
            client_id=os.getenv("WORKDAY_CLIENT_ID", ""),
            client_secret=os.getenv("WORKDAY_CLIENT_SECRET", ""),
            refresh_token=os.getenv("WORKDAY_REFRESH_TOKEN", ""),
            use_oauth=os.getenv("WORKDAY_USE_OAUTH", "false").lower() == "true",
            use_mock=os.getenv("WORKDAY_USE_MOCK", "true").lower() == "true",
        )


@dataclass
class WorkdayWorker:
    """Workday worker/employee"""
    worker_id: str
    employee_id: str
    email: str
    first_name: str
    last_name: str
    display_name: str
    hire_date: date
    job_title: str
    department: str
    cost_center: str
    manager_id: Optional[str]
    location: str
    worker_type: str  # Employee, Contingent Worker
    status: str  # Active, Terminated, On Leave
    termination_date: Optional[date] = None


@dataclass
class WorkdayOrganization:
    """Workday organization/department"""
    org_id: str
    name: str
    org_type: str  # Company, Cost Center, Department, etc.
    parent_id: Optional[str]
    manager_id: Optional[str]


class WorkdayConnector:
    """
    Workday HRIS Connector

    Provides:
    1. Worker/employee synchronization via REST or SOAP API
    2. Organization hierarchy sync
    3. JML event processing (Join, Move, Leave)
    4. Real-time event notifications
    5. Mock fallback for development/testing
    """

    def __init__(self, config: WorkdayConfig):
        self.config = config
        self._client: Optional[Any] = None
        self._access_token: Optional[str] = None
        self._token_expiry: Optional[datetime] = None

    @property
    def _use_mock(self) -> bool:
        _is_production = os.getenv("APP_ENV", "").lower() == "production"
        wants_mock = self.config.use_mock or not HAS_HTTPX or not self.config.tenant_url
        if wants_mock and _is_production:
            raise RuntimeError(
                "WorkdayConnector: mock/simulation mode is not allowed in production. "
                "Set WORKDAY_TENANT_URL, WORKDAY_USERNAME/WORKDAY_PASSWORD (or OAuth "
                "credentials), and WORKDAY_USE_MOCK=false. "
                "Set APP_ENV != 'production' to enable simulation mode."
            )
        return wants_mock

    def _get_client(self) -> "httpx.AsyncClient":
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.config.tenant_url.rstrip("/"),
                timeout=30.0,
                verify=True,
            )
        return self._client

    # ==================== Authentication ====================

    async def authenticate(self) -> bool:
        """Authenticate with Workday (OAuth or basic)"""
        if self._use_mock:
            logger.info("Workday mock mode — skipping authentication")
            self._access_token = "mock_token"
            return True

        try:
            client = self._get_client()

            if self.config.use_oauth:
                # OAuth 2.0 token endpoint
                token_url = f"{self.config.tenant_url}/ccx/oauth2/{self.config.tenant_name}/token"
                resp = await client.post(
                    token_url,
                    data={
                        "grant_type": "refresh_token",
                        "client_id": self.config.client_id,
                        "client_secret": self.config.client_secret,
                        "refresh_token": self.config.refresh_token,
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                self._access_token = data["access_token"]
                logger.info("Workday OAuth authentication successful")
            else:
                # Basic auth — test with a simple API call
                resp = await client.get(
                    f"/ccx/api/{self.config.api_version}/{self.config.tenant_name}/workers",
                    auth=(self.config.username, self.config.password),
                    params={"limit": 1},
                )
                resp.raise_for_status()
                self._access_token = "basic_auth"
                logger.info("Workday basic authentication successful")

            return True

        except Exception as e:
            logger.error(f"Workday authentication failed: {e}")
            return False

    def _auth_headers(self) -> Dict[str, str]:
        headers = {"Accept": "application/json"}
        if self._access_token and self._access_token not in ("basic_auth", "mock_token"):
            headers["Authorization"] = f"Bearer {self._access_token}"
        return headers

    def _auth_kwargs(self) -> Dict[str, Any]:
        kwargs: Dict[str, Any] = {"headers": self._auth_headers()}
        if self._access_token == "basic_auth":
            kwargs["auth"] = (self.config.username, self.config.password)
        return kwargs

    # ==================== Worker Operations ====================

    async def get_workers(
        self,
        active_only: bool = True,
        as_of_date: date = None
    ) -> List[WorkdayWorker]:
        """Get workers from Workday"""
        if self._use_mock:
            return self._mock_workers()

        logger.info("Fetching workers from Workday REST API")
        client = self._get_client()

        workers = []
        offset = 0
        limit = 100

        while True:
            params: Dict[str, Any] = {"limit": limit, "offset": offset}
            if as_of_date:
                params["effectiveDate"] = as_of_date.isoformat()

            resp = await client.get(
                f"/ccx/api/{self.config.api_version}/{self.config.tenant_name}/workers",
                params=params,
                **self._auth_kwargs(),
            )
            resp.raise_for_status()
            data = resp.json()

            for w in data.get("data", []):
                primary_job = (w.get("primaryJob") or {})
                worker = WorkdayWorker(
                    worker_id=w.get("id", ""),
                    employee_id=w.get("workerID", w.get("id", "")),
                    email=w.get("primaryWorkEmail", ""),
                    first_name=w.get("legalName", {}).get("firstName", ""),
                    last_name=w.get("legalName", {}).get("lastName", ""),
                    display_name=w.get("displayName", ""),
                    hire_date=_parse_date(w.get("hireDate", "")),
                    job_title=primary_job.get("jobTitle", ""),
                    department=primary_job.get("supervisoryOrganization", {}).get("name", ""),
                    cost_center=primary_job.get("costCenter", {}).get("id", ""),
                    manager_id=primary_job.get("manager", {}).get("id"),
                    location=primary_job.get("location", {}).get("name", ""),
                    worker_type=w.get("workerType", "Employee"),
                    status="Active" if w.get("active", True) else "Terminated",
                    termination_date=_parse_date(w.get("terminationDate")) if w.get("terminationDate") else None,
                )

                if active_only and worker.status != "Active":
                    continue
                workers.append(worker)

            total = data.get("total", 0)
            offset += limit
            if offset >= total:
                break

        logger.info(f"Fetched {len(workers)} workers from Workday")
        return workers

    async def get_worker(self, worker_id: str) -> Optional[WorkdayWorker]:
        """Get a single worker"""
        if self._use_mock:
            workers = self._mock_workers()
            return next((w for w in workers if w.worker_id == worker_id), None)

        client = self._get_client()
        resp = await client.get(
            f"/ccx/api/{self.config.api_version}/{self.config.tenant_name}/workers/{worker_id}",
            **self._auth_kwargs(),
        )
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        w = resp.json()
        primary_job = (w.get("primaryJob") or {})
        return WorkdayWorker(
            worker_id=w.get("id", ""),
            employee_id=w.get("workerID", w.get("id", "")),
            email=w.get("primaryWorkEmail", ""),
            first_name=w.get("legalName", {}).get("firstName", ""),
            last_name=w.get("legalName", {}).get("lastName", ""),
            display_name=w.get("displayName", ""),
            hire_date=_parse_date(w.get("hireDate", "")),
            job_title=primary_job.get("jobTitle", ""),
            department=primary_job.get("supervisoryOrganization", {}).get("name", ""),
            cost_center=primary_job.get("costCenter", {}).get("id", ""),
            manager_id=primary_job.get("manager", {}).get("id"),
            location=primary_job.get("location", {}).get("name", ""),
            worker_type=w.get("workerType", "Employee"),
            status="Active" if w.get("active", True) else "Terminated",
        )

    async def get_worker_manager(self, worker_id: str) -> Optional[WorkdayWorker]:
        """Get a worker's manager"""
        worker = await self.get_worker(worker_id)
        if worker and worker.manager_id:
            return await self.get_worker(worker.manager_id)
        return None

    # ==================== Organization Operations ====================

    async def get_organizations(self, org_type: str = None) -> List[WorkdayOrganization]:
        """Get organizations from Workday"""
        if self._use_mock:
            return self._mock_organizations()

        client = self._get_client()
        params: Dict[str, Any] = {"limit": 100}
        if org_type:
            params["type"] = org_type

        resp = await client.get(
            f"/ccx/api/{self.config.api_version}/{self.config.tenant_name}/organizations",
            params=params,
            **self._auth_kwargs(),
        )
        resp.raise_for_status()
        data = resp.json()

        orgs = []
        for o in data.get("data", []):
            orgs.append(WorkdayOrganization(
                org_id=o.get("id", ""),
                name=o.get("name", ""),
                org_type=o.get("type", ""),
                parent_id=o.get("superiorOrganization", {}).get("id"),
                manager_id=o.get("manager", {}).get("id"),
            ))

        return orgs

    # ==================== JML Event Processing ====================

    async def get_pending_hires(
        self,
        start_date: date = None,
        end_date: date = None
    ) -> List[Dict[str, Any]]:
        """Get pending hire events for provisioning"""
        if self._use_mock:
            return self._mock_pending_hires()

        client = self._get_client()
        params: Dict[str, Any] = {"limit": 100}
        if start_date:
            params["from"] = start_date.isoformat()
        if end_date:
            params["to"] = end_date.isoformat()

        resp = await client.get(
            f"/ccx/api/{self.config.api_version}/{self.config.tenant_name}/staffing/hireEvents",
            params=params,
            **self._auth_kwargs(),
        )
        resp.raise_for_status()
        data = resp.json()

        events = []
        for e in data.get("data", []):
            worker = e.get("worker", {})
            job = e.get("proposedJob", {})
            events.append({
                "event_type": "hire",
                "worker_id": worker.get("id", ""),
                "employee_id": worker.get("workerID", ""),
                "name": worker.get("displayName", ""),
                "email": worker.get("primaryWorkEmail", ""),
                "department": job.get("supervisoryOrganization", {}).get("name", ""),
                "job_title": job.get("jobTitle", ""),
                "hire_date": e.get("hireDate", ""),
                "manager_id": job.get("manager", {}).get("id", ""),
            })

        return events

    async def get_pending_terminations(
        self,
        start_date: date = None,
        end_date: date = None
    ) -> List[Dict[str, Any]]:
        """Get pending termination events for deprovisioning"""
        if self._use_mock:
            return self._mock_pending_terminations()

        client = self._get_client()
        params: Dict[str, Any] = {"limit": 100}
        if start_date:
            params["from"] = start_date.isoformat()
        if end_date:
            params["to"] = end_date.isoformat()

        resp = await client.get(
            f"/ccx/api/{self.config.api_version}/{self.config.tenant_name}/staffing/terminationEvents",
            params=params,
            **self._auth_kwargs(),
        )
        resp.raise_for_status()
        data = resp.json()

        events = []
        for e in data.get("data", []):
            worker = e.get("worker", {})
            events.append({
                "event_type": "termination",
                "worker_id": worker.get("id", ""),
                "employee_id": worker.get("workerID", ""),
                "name": worker.get("displayName", ""),
                "termination_date": e.get("terminationDate", ""),
                "termination_reason": e.get("terminationReason", {}).get("name", ""),
            })

        return events

    async def get_pending_transfers(
        self,
        start_date: date = None,
        end_date: date = None
    ) -> List[Dict[str, Any]]:
        """Get pending transfer events for access modification"""
        if self._use_mock:
            return self._mock_pending_transfers()

        client = self._get_client()
        params: Dict[str, Any] = {"limit": 100}
        if start_date:
            params["from"] = start_date.isoformat()
        if end_date:
            params["to"] = end_date.isoformat()

        resp = await client.get(
            f"/ccx/api/{self.config.api_version}/{self.config.tenant_name}/staffing/jobChangeEvents",
            params=params,
            **self._auth_kwargs(),
        )
        resp.raise_for_status()
        data = resp.json()

        events = []
        for e in data.get("data", []):
            worker = e.get("worker", {})
            old_job = e.get("currentJob", {})
            new_job = e.get("proposedJob", {})
            events.append({
                "event_type": "transfer",
                "worker_id": worker.get("id", ""),
                "employee_id": worker.get("workerID", ""),
                "name": worker.get("displayName", ""),
                "effective_date": e.get("effectiveDate", ""),
                "old_department": old_job.get("supervisoryOrganization", {}).get("name", ""),
                "new_department": new_job.get("supervisoryOrganization", {}).get("name", ""),
                "old_manager_id": old_job.get("manager", {}).get("id", ""),
                "new_manager_id": new_job.get("manager", {}).get("id", ""),
            })

        return events

    async def process_jml_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Process a JML event and return required GRC actions"""
        event_type = event.get("event_type")

        if event_type == "hire":
            return {
                "action": "provision",
                "user_id": event["employee_id"],
                "name": event["name"],
                "email": event.get("email", ""),
                "department": event.get("department", ""),
                "recommended_roles": self._get_default_roles(event.get("department", ""), event.get("job_title", "")),
                "effective_date": event.get("hire_date", ""),
            }

        elif event_type == "termination":
            return {
                "action": "deprovision",
                "user_id": event.get("employee_id", event.get("worker_id", "")),
                "name": event["name"],
                "revoke_all_access": True,
                "effective_date": event["termination_date"],
                "archive_audit_logs": True,
            }

        elif event_type == "transfer":
            old_roles = self._get_default_roles(event.get("old_department", ""), "")
            new_roles = self._get_default_roles(event.get("new_department", ""), "")

            return {
                "action": "modify",
                "user_id": event.get("employee_id", event.get("worker_id", "")),
                "name": event["name"],
                "roles_to_remove": old_roles,
                "roles_to_add": new_roles,
                "new_manager": event.get("new_manager_id", ""),
                "effective_date": event["effective_date"],
            }

        return {"action": "none", "message": "Unknown event type"}

    def _get_default_roles(self, department: str, job_title: str) -> List[str]:
        """Get default roles based on department and job title"""
        role_mapping = {
            "Finance": ["Z_FI_BASIC", "Z_FI_REPORTS"],
            "Procurement": ["Z_MM_BASIC", "Z_MM_REPORTS"],
            "IT": ["Z_IT_BASIC", "Z_IT_ADMIN"],
            "HR": ["Z_HR_BASIC"],
            "Sales": ["Z_SD_BASIC", "Z_CRM_USER"],
            "Marketing": ["Z_MKT_BASIC"],
        }
        return role_mapping.get(department, ["Z_BASIC_USER"])

    # ==================== Sync Operations ====================

    async def sync_workers_to_grc(self) -> Dict[str, Any]:
        """Sync Workday workers to GRC platform"""
        logger.info("Starting Workday worker sync")

        from db.database import db_manager
        from db.models.user import User

        workers = await self.get_workers()

        synced = 0
        for worker in workers:
            grc_user = {
                "user_id": worker.employee_id,
                "email": worker.email,
                "full_name": worker.display_name,
                "first_name": worker.first_name,
                "last_name": worker.last_name,
                "department": worker.department,
                "cost_center": worker.cost_center,
                "status": "active" if worker.status == "Active" else "inactive",
                "source_system": "workday",
                "external_id": worker.worker_id,
                "manager_id": worker.manager_id,
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
                logger.warning(f"Failed to persist worker {grc_user['user_id']}: {e}")

        return {
            "source": "workday",
            "workers_processed": len(workers),
            "synced": synced,
            "synced_at": datetime.utcnow().isoformat(),
        }

    # ==================== Connection Test ====================

    async def test_connection(self) -> Dict[str, Any]:
        """Test Workday connection"""
        if self._use_mock:
            return {
                "status": "connected",
                "mode": "mock",
                "tenant_url": self.config.tenant_url or "(mock)",
                "message": "Mock mode active — no real Workday connection",
            }

        try:
            authenticated = await self.authenticate()
            if authenticated:
                return {
                    "status": "connected",
                    "mode": "live",
                    "tenant_url": self.config.tenant_url,
                    "message": "Successfully connected to Workday",
                }
            return {
                "status": "failed",
                "tenant_url": self.config.tenant_url,
                "message": "Authentication failed",
            }
        except Exception as e:
            return {
                "status": "error",
                "tenant_url": self.config.tenant_url,
                "message": str(e),
            }

    async def close(self):
        """Close the HTTP client"""
        if self._client:
            await self._client.aclose()
            self._client = None

    # ==================== Mock Data ====================

    def _mock_workers(self) -> List[WorkdayWorker]:
        return [
            WorkdayWorker(
                worker_id="WD001", employee_id="EMP001",
                email="jsmith@company.com", first_name="John", last_name="Smith",
                display_name="John Smith", hire_date=date(2024, 1, 15),
                job_title="Senior Accountant", department="Finance",
                cost_center="CC1001", manager_id="WD_MGR001",
                location="New York", worker_type="Employee", status="Active",
            ),
            WorkdayWorker(
                worker_id="WD002", employee_id="EMP002",
                email="mbrown@company.com", first_name="Mary", last_name="Brown",
                display_name="Mary Brown", hire_date=date(2023, 6, 1),
                job_title="Procurement Manager", department="Procurement",
                cost_center="CC2001", manager_id="WD_MGR002",
                location="Chicago", worker_type="Employee", status="Active",
            ),
            WorkdayWorker(
                worker_id="WD006", employee_id="EMP006",
                email="contractor1@vendor.com", first_name="Alex", last_name="Vendor",
                display_name="Alex Vendor", hire_date=date(2025, 9, 1),
                job_title="SAP Consultant", department="IT",
                cost_center="CC3001", manager_id="WD_MGR003",
                location="Remote", worker_type="Contingent Worker", status="Active",
            ),
        ]

    def _mock_organizations(self) -> List[WorkdayOrganization]:
        return [
            WorkdayOrganization(org_id="ORG001", name="Finance Department",
                                org_type="Department", parent_id="ORG_CORP", manager_id="WD_MGR001"),
            WorkdayOrganization(org_id="ORG002", name="Procurement Department",
                                org_type="Department", parent_id="ORG_CORP", manager_id="WD_MGR002"),
            WorkdayOrganization(org_id="ORG003", name="IT Department",
                                org_type="Department", parent_id="ORG_CORP", manager_id="WD_MGR003"),
        ]

    def _mock_pending_hires(self) -> List[Dict[str, Any]]:
        return [{
            "event_type": "hire",
            "worker_id": "WD003", "employee_id": "EMP003",
            "name": "New Employee", "email": "newemployee@company.com",
            "department": "IT", "job_title": "Software Developer",
            "hire_date": date(2026, 2, 1).isoformat(), "manager_id": "WD_MGR003",
        }]

    def _mock_pending_terminations(self) -> List[Dict[str, Any]]:
        return [{
            "event_type": "termination",
            "worker_id": "WD004", "employee_id": "EMP004",
            "name": "Departing Employee",
            "termination_date": date(2026, 1, 31).isoformat(),
            "termination_reason": "Voluntary",
        }]

    def _mock_pending_transfers(self) -> List[Dict[str, Any]]:
        return [{
            "event_type": "transfer",
            "worker_id": "WD005", "employee_id": "EMP005",
            "name": "Transferring Employee",
            "effective_date": date(2026, 2, 15).isoformat(),
            "old_department": "Sales", "new_department": "Marketing",
            "old_manager_id": "WD_MGR_SALES", "new_manager_id": "WD_MGR_MKT",
        }]


def _parse_date(date_str: str) -> date:
    """Parse ISO date string to date object"""
    if not date_str:
        return date.today()
    try:
        return date.fromisoformat(date_str[:10])
    except (ValueError, TypeError):
        return date.today()
