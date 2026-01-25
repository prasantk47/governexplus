"""
HR System Connectors

Provides connectivity to HR systems for JML automation:
- Workday
- SAP SuccessFactors
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


@dataclass
class WorkdayConfig(ConnectorConfig):
    """Workday configuration"""
    tenant_name: str = ""
    api_version: str = "v1"
    integration_system_id: str = ""

    def __post_init__(self):
        self.system_type = "workday"

    def get_base_url(self) -> str:
        return f"https://{self.host}/ccx/service/{self.tenant_name}"


@dataclass
class SuccessFactorsConfig(ConnectorConfig):
    """SAP SuccessFactors configuration"""
    company_id: str = ""
    api_server: str = ""

    def __post_init__(self):
        self.system_type = "successfactors"


class MockWorkdayClient:
    """Mock Workday client for testing"""

    def __init__(self, config: WorkdayConfig):
        self.config = config
        self._employees = {
            "EMP001": {
                "Worker_ID": "EMP001",
                "Legal_Name": {"First_Name": "John", "Last_Name": "Smith"},
                "Email_Address": "jsmith@company.com",
                "Job_Profile": "Senior Developer",
                "Supervisory_Organization": "Engineering",
                "Location": "New York",
                "Hire_Date": "2024-01-15",
                "Termination_Date": None,
                "Worker_Status": "Active",
                "Manager_ID": "MGR001"
            },
            "EMP002": {
                "Worker_ID": "EMP002",
                "Legal_Name": {"First_Name": "Mary", "Last_Name": "Brown"},
                "Email_Address": "mbrown@company.com",
                "Job_Profile": "Financial Analyst",
                "Supervisory_Organization": "Finance",
                "Location": "Chicago",
                "Hire_Date": "2024-03-20",
                "Termination_Date": None,
                "Worker_Status": "Active",
                "Manager_ID": "MGR002"
            },
            "EMP003": {
                "Worker_ID": "EMP003",
                "Legal_Name": {"First_Name": "Tom", "Last_Name": "Wilson"},
                "Email_Address": "twilson@company.com",
                "Job_Profile": "HR Specialist",
                "Supervisory_Organization": "Human Resources",
                "Location": "Boston",
                "Hire_Date": "2023-06-01",
                "Termination_Date": "2025-01-31",
                "Worker_Status": "Termination_In_Progress",
                "Manager_ID": "MGR003"
            }
        }

    def get_worker(self, worker_id: str) -> Dict:
        if worker_id in self._employees:
            return self._employees[worker_id]
        raise Exception(f"Worker {worker_id} not found")

    def get_workers(self, filters: Optional[Dict] = None) -> List[Dict]:
        workers = list(self._employees.values())
        if filters:
            if "status" in filters:
                workers = [w for w in workers if w.get("Worker_Status") == filters["status"]]
            if "organization" in filters:
                workers = [w for w in workers if w.get("Supervisory_Organization") == filters["organization"]]
        return workers

    def get_organization_assignments(self, worker_id: str) -> Dict:
        if worker_id in self._employees:
            emp = self._employees[worker_id]
            return {
                "Worker_ID": worker_id,
                "Organization": emp.get("Supervisory_Organization"),
                "Job_Profile": emp.get("Job_Profile"),
                "Location": emp.get("Location"),
                "Manager_ID": emp.get("Manager_ID")
            }
        raise Exception(f"Worker {worker_id} not found")

    def get_pending_terminations(self) -> List[Dict]:
        return [
            w for w in self._employees.values()
            if w.get("Worker_Status") == "Termination_In_Progress"
        ]

    def get_new_hires(self, since_date: str) -> List[Dict]:
        return [
            w for w in self._employees.values()
            if w.get("Hire_Date", "") >= since_date and w.get("Worker_Status") == "Active"
        ]

    def get_job_changes(self, since_date: str) -> List[Dict]:
        # Mock: return empty for now
        return []


class WorkdayConnector(BaseConnector):
    """
    Workday Connector

    Provides read-only access to Workday worker data for JML automation.
    """

    def __init__(self, config: WorkdayConfig):
        super().__init__(config)
        self.workday_config = config
        self._client = None

    async def _do_connect(self):
        """Connect to Workday"""
        # In production, would use Workday SOAP/REST APIs
        self._client = MockWorkdayClient(self.workday_config)
        await self._do_test_connection()

    async def _do_disconnect(self):
        """Disconnect from Workday"""
        self._client = None

    async def _do_test_connection(self) -> Dict:
        """Test Workday connection"""
        workers = self._client.get_workers()
        return {
            "status": "connected",
            "tenant": self.workday_config.tenant_name,
            "worker_count": len(workers)
        }

    async def _do_execute(self, operation: str, **params) -> Dict:
        """Execute Workday operation"""
        if operation == "get_user":
            worker = self._client.get_worker(params.get("user_id"))
            return self._format_worker(worker)

        elif operation == "list_users":
            workers = self._client.get_workers(params.get("filters"))
            return {
                "users": [self._format_worker(w) for w in workers],
                "count": len(workers)
            }

        elif operation == "get_organization":
            org = self._client.get_organization_assignments(params.get("user_id"))
            return org

        elif operation == "get_pending_terminations":
            terminations = self._client.get_pending_terminations()
            return {
                "terminations": [self._format_worker(w) for w in terminations],
                "count": len(terminations)
            }

        elif operation == "get_new_hires":
            since = params.get("since_date", datetime.now().strftime("%Y-%m-%d"))
            hires = self._client.get_new_hires(since)
            return {
                "new_hires": [self._format_worker(w) for w in hires],
                "count": len(hires)
            }

        elif operation == "get_job_changes":
            since = params.get("since_date", datetime.now().strftime("%Y-%m-%d"))
            changes = self._client.get_job_changes(since)
            return {
                "job_changes": changes,
                "count": len(changes)
            }

        else:
            raise OperationError(f"Unknown operation: {operation}", operation)

    def _format_worker(self, worker: Dict) -> Dict:
        """Format Workday worker to standard format"""
        name = worker.get("Legal_Name", {})
        return {
            "employee_id": worker.get("Worker_ID"),
            "first_name": name.get("First_Name", ""),
            "last_name": name.get("Last_Name", ""),
            "email": worker.get("Email_Address"),
            "job_title": worker.get("Job_Profile"),
            "department": worker.get("Supervisory_Organization"),
            "location": worker.get("Location"),
            "hire_date": worker.get("Hire_Date"),
            "termination_date": worker.get("Termination_Date"),
            "status": worker.get("Worker_Status"),
            "manager_id": worker.get("Manager_ID")
        }


class MockSuccessFactorsClient:
    """Mock SuccessFactors client for testing"""

    def __init__(self, config: SuccessFactorsConfig):
        self.config = config
        self._employees = {
            "SF001": {
                "userId": "SF001",
                "firstName": "Alice",
                "lastName": "Johnson",
                "email": "ajohnson@company.com",
                "jobTitle": "Product Manager",
                "department": "Product",
                "location": "San Francisco",
                "hireDate": "2024-02-01",
                "status": "active",
                "managerId": "SFMGR01"
            },
            "SF002": {
                "userId": "SF002",
                "firstName": "Bob",
                "lastName": "Davis",
                "email": "bdavis@company.com",
                "jobTitle": "Sales Representative",
                "department": "Sales",
                "location": "Dallas",
                "hireDate": "2024-04-15",
                "status": "active",
                "managerId": "SFMGR02"
            }
        }

    def get_employee(self, user_id: str) -> Dict:
        if user_id in self._employees:
            return self._employees[user_id]
        raise Exception(f"Employee {user_id} not found")

    def get_employees(self, filters: Optional[Dict] = None) -> List[Dict]:
        return list(self._employees.values())

    def get_job_info(self, user_id: str) -> Dict:
        if user_id in self._employees:
            emp = self._employees[user_id]
            return {
                "userId": user_id,
                "jobTitle": emp.get("jobTitle"),
                "department": emp.get("department"),
                "managerId": emp.get("managerId")
            }
        raise Exception(f"Employee {user_id} not found")


class SuccessFactorsConnector(BaseConnector):
    """
    SAP SuccessFactors Connector

    Provides read-only access to SuccessFactors employee data.
    """

    def __init__(self, config: SuccessFactorsConfig):
        super().__init__(config)
        self.sf_config = config
        self._client = None

    async def _do_connect(self):
        """Connect to SuccessFactors"""
        self._client = MockSuccessFactorsClient(self.sf_config)
        await self._do_test_connection()

    async def _do_disconnect(self):
        """Disconnect from SuccessFactors"""
        self._client = None

    async def _do_test_connection(self) -> Dict:
        """Test SuccessFactors connection"""
        employees = self._client.get_employees()
        return {
            "status": "connected",
            "company_id": self.sf_config.company_id,
            "employee_count": len(employees)
        }

    async def _do_execute(self, operation: str, **params) -> Dict:
        """Execute SuccessFactors operation"""
        if operation == "get_user":
            emp = self._client.get_employee(params.get("user_id"))
            return self._format_employee(emp)

        elif operation == "list_users":
            employees = self._client.get_employees(params.get("filters"))
            return {
                "users": [self._format_employee(e) for e in employees],
                "count": len(employees)
            }

        elif operation == "get_job_info":
            job = self._client.get_job_info(params.get("user_id"))
            return job

        else:
            raise OperationError(f"Unknown operation: {operation}", operation)

    def _format_employee(self, emp: Dict) -> Dict:
        """Format SuccessFactors employee to standard format"""
        return {
            "employee_id": emp.get("userId"),
            "first_name": emp.get("firstName", ""),
            "last_name": emp.get("lastName", ""),
            "email": emp.get("email"),
            "job_title": emp.get("jobTitle"),
            "department": emp.get("department"),
            "location": emp.get("location"),
            "hire_date": emp.get("hireDate"),
            "status": emp.get("status"),
            "manager_id": emp.get("managerId")
        }
