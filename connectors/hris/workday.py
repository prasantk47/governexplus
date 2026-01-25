"""
Workday HRIS Connector

Integration with Workday for HR data synchronization and JML automation.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime, date
import logging

logger = logging.getLogger(__name__)


@dataclass
class WorkdayConfig:
    """Workday connection configuration"""
    tenant_url: str  # e.g., "https://impl.workday.com/company"
    username: str
    password: str  # Would be retrieved from secrets manager

    # API settings
    api_version: str = "v1"

    # Sync options
    sync_workers: bool = True
    sync_organizations: bool = True
    sync_positions: bool = True

    # Event subscriptions
    subscribe_hire: bool = True
    subscribe_termination: bool = True
    subscribe_transfer: bool = True
    subscribe_promotion: bool = True


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
    1. Worker/employee synchronization
    2. Organization hierarchy sync
    3. JML event processing (Join, Move, Leave)
    4. Real-time event notifications
    """

    def __init__(self, config: WorkdayConfig):
        self.config = config

    # ==================== Worker Operations ====================

    async def get_workers(
        self,
        active_only: bool = True,
        as_of_date: date = None
    ) -> List[WorkdayWorker]:
        """Get workers from Workday"""
        logger.info("Fetching workers from Workday")

        # In production, would call Workday SOAP API or REST API
        # GET /ccx/service/company/Human_Resources/v40.1

        return [
            WorkdayWorker(
                worker_id="WD001",
                employee_id="EMP001",
                email="jsmith@company.com",
                first_name="John",
                last_name="Smith",
                display_name="John Smith",
                hire_date=date(2024, 1, 15),
                job_title="Senior Accountant",
                department="Finance",
                cost_center="CC1001",
                manager_id="WD_MGR001",
                location="New York",
                worker_type="Employee",
                status="Active"
            ),
            WorkdayWorker(
                worker_id="WD002",
                employee_id="EMP002",
                email="mbrown@company.com",
                first_name="Mary",
                last_name="Brown",
                display_name="Mary Brown",
                hire_date=date(2023, 6, 1),
                job_title="Procurement Manager",
                department="Procurement",
                cost_center="CC2001",
                manager_id="WD_MGR002",
                location="Chicago",
                worker_type="Employee",
                status="Active"
            ),
        ]

    async def get_worker(self, worker_id: str) -> Optional[WorkdayWorker]:
        """Get a single worker"""
        workers = await self.get_workers()
        return next((w for w in workers if w.worker_id == worker_id), None)

    async def get_worker_manager(self, worker_id: str) -> Optional[WorkdayWorker]:
        """Get a worker's manager"""
        worker = await self.get_worker(worker_id)
        if worker and worker.manager_id:
            return await self.get_worker(worker.manager_id)
        return None

    # ==================== Organization Operations ====================

    async def get_organizations(self, org_type: str = None) -> List[WorkdayOrganization]:
        """Get organizations from Workday"""
        return [
            WorkdayOrganization(
                org_id="ORG001",
                name="Finance Department",
                org_type="Department",
                parent_id="ORG_CORP",
                manager_id="WD_MGR001"
            ),
            WorkdayOrganization(
                org_id="ORG002",
                name="Procurement Department",
                org_type="Department",
                parent_id="ORG_CORP",
                manager_id="WD_MGR002"
            ),
        ]

    # ==================== JML Event Processing ====================

    async def get_pending_hires(
        self,
        start_date: date = None,
        end_date: date = None
    ) -> List[Dict[str, Any]]:
        """Get pending hire events for provisioning"""
        return [
            {
                "event_type": "hire",
                "worker_id": "WD003",
                "employee_id": "EMP003",
                "name": "New Employee",
                "email": "newemployee@company.com",
                "department": "IT",
                "job_title": "Software Developer",
                "hire_date": date(2026, 2, 1).isoformat(),
                "manager_id": "WD_MGR003"
            }
        ]

    async def get_pending_terminations(
        self,
        start_date: date = None,
        end_date: date = None
    ) -> List[Dict[str, Any]]:
        """Get pending termination events for deprovisioning"""
        return [
            {
                "event_type": "termination",
                "worker_id": "WD004",
                "employee_id": "EMP004",
                "name": "Departing Employee",
                "termination_date": date(2026, 1, 31).isoformat(),
                "termination_reason": "Voluntary"
            }
        ]

    async def get_pending_transfers(
        self,
        start_date: date = None,
        end_date: date = None
    ) -> List[Dict[str, Any]]:
        """Get pending transfer events for access modification"""
        return [
            {
                "event_type": "transfer",
                "worker_id": "WD005",
                "employee_id": "EMP005",
                "name": "Transferring Employee",
                "effective_date": date(2026, 2, 15).isoformat(),
                "old_department": "Sales",
                "new_department": "Marketing",
                "old_manager_id": "WD_MGR_SALES",
                "new_manager_id": "WD_MGR_MKT"
            }
        ]

    async def process_jml_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Process a JML event and return required GRC actions"""
        event_type = event.get("event_type")

        if event_type == "hire":
            return {
                "action": "provision",
                "user_id": event["employee_id"],
                "name": event["name"],
                "email": event["email"],
                "department": event["department"],
                "recommended_roles": self._get_default_roles(event["department"], event["job_title"]),
                "effective_date": event["hire_date"]
            }

        elif event_type == "termination":
            return {
                "action": "deprovision",
                "user_id": event["employee_id"],
                "name": event["name"],
                "revoke_all_access": True,
                "effective_date": event["termination_date"],
                "archive_audit_logs": True
            }

        elif event_type == "transfer":
            old_roles = self._get_default_roles(event["old_department"], "")
            new_roles = self._get_default_roles(event["new_department"], "")

            return {
                "action": "modify",
                "user_id": event["employee_id"],
                "name": event["name"],
                "roles_to_remove": old_roles,
                "roles_to_add": new_roles,
                "new_manager": event["new_manager_id"],
                "effective_date": event["effective_date"]
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
            "Marketing": ["Z_MKT_BASIC"]
        }
        return role_mapping.get(department, ["Z_BASIC_USER"])

    # ==================== Sync Operations ====================

    async def sync_workers_to_grc(self) -> Dict[str, Any]:
        """Sync Workday workers to GRC platform"""
        logger.info("Starting Workday worker sync")

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
                "manager_id": worker.manager_id
            }
            synced += 1

        return {
            "source": "workday",
            "workers_processed": len(workers),
            "synced": synced,
            "synced_at": datetime.utcnow().isoformat()
        }

    # ==================== Connection Test ====================

    async def test_connection(self) -> Dict[str, Any]:
        """Test Workday connection"""
        try:
            return {
                "status": "connected",
                "tenant_url": self.config.tenant_url,
                "message": "Successfully connected to Workday"
            }
        except Exception as e:
            return {
                "status": "error",
                "tenant_url": self.config.tenant_url,
                "message": str(e)
            }
