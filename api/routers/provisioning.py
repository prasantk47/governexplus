"""
Provisioning API Router

REST API endpoints for provisioning operations:
- Connector management
- Task submission and tracking
- Real-time status updates
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum
import logging

from core.connectors import (
    ConnectorFactory, connector_factory, connector_registry,
    SAPConfig, AWSConfig, AzureConfig, WorkdayConfig, SuccessFactorsConfig
)
from core.provisioning import (
    ProvisioningEngine, provisioning_engine,
    ProvisioningTask, ProvisioningStep, ProvisioningAction, ProvisioningStatus,
    ProvisioningQueue, TaskPriority
)
from core.provisioning.queue import provisioning_queue

logger = logging.getLogger(__name__)
router = APIRouter()


# =============================================================================
# Request/Response Models
# =============================================================================

class ConnectorConfigRequest(BaseModel):
    """Request model for creating a connector"""
    connector_id: str = Field(..., description="Unique connector ID")
    type_id: str = Field(..., description="Connector type (sap_ecc, aws_iam, etc.)")
    name: str = Field(..., description="Display name")
    host: str = Field(..., description="Host/endpoint")
    port: Optional[int] = None
    username: str = ""
    password: str = ""
    enabled: bool = True
    extra_config: Dict[str, Any] = Field(default_factory=dict)


class TestConnectionRequest(BaseModel):
    """Request model for testing a connection"""
    connector_id: str


class ProvisionUserRequest(BaseModel):
    """Request model for provisioning a new user"""
    user_id: str
    first_name: str
    last_name: str
    email: str
    department: Optional[str] = None
    job_title: Optional[str] = None
    manager_id: Optional[str] = None
    target_systems: List[str]
    initial_password: Optional[str] = None
    source_type: str = "manual"
    source_id: str = ""


class AssignRolesRequest(BaseModel):
    """Request model for assigning roles"""
    user_id: str
    roles: List[Dict[str, Any]]  # [{system, role_name, valid_from?, valid_to?}]
    source_type: str = "access_request"
    source_id: str = ""
    priority: str = "normal"


class RevokeRolesRequest(BaseModel):
    """Request model for revoking roles"""
    user_id: str
    roles: List[Dict[str, str]]  # [{system, role_name}]
    source_type: str = "access_request"
    source_id: str = ""


class DeprovisionUserRequest(BaseModel):
    """Request model for deprovisioning a user"""
    user_id: str
    target_systems: List[str]
    action: str = "lock"  # lock, disable, delete
    source_type: str = "jml_event"
    source_id: str = ""


class ExecuteOperationRequest(BaseModel):
    """Request model for executing a connector operation"""
    connector_id: str
    operation: str
    parameters: Dict[str, Any] = Field(default_factory=dict)


# =============================================================================
# Connector Management Endpoints
# =============================================================================

@router.get("/connector-types")
async def list_connector_types():
    """List all available connector types"""
    return {
        "types": connector_registry.list_types(),
        "categories": {
            "sap": connector_registry.list_by_category("sap"),
            "cloud": connector_registry.list_by_category("cloud"),
            "identity": connector_registry.list_by_category("identity"),
            "hr": connector_registry.list_by_category("hr")
        }
    }


@router.post("/connectors")
async def create_connector(request: ConnectorConfigRequest):
    """Create a new connector"""
    try:
        # Build config dict based on type
        config_dict = {
            "name": request.name,
            "host": request.host,
            "port": request.port,
            "username": request.username,
            "password": request.password,
            "enabled": request.enabled,
            **request.extra_config
        }

        connector = await connector_factory.create_connector(
            request.connector_id,
            request.type_id,
            config_dict
        )

        return {
            "success": True,
            "connector_id": request.connector_id,
            "status": connector.get_status()
        }

    except Exception as e:
        logger.error(f"Failed to create connector: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/connectors")
async def list_connectors():
    """List all configured connectors"""
    return {
        "connectors": connector_factory.list_connectors()
    }


@router.get("/connectors/{connector_id}")
async def get_connector(connector_id: str):
    """Get connector details"""
    status = connector_factory.get_status(connector_id)
    if not status:
        raise HTTPException(status_code=404, detail="Connector not found")

    return status


@router.delete("/connectors/{connector_id}")
async def delete_connector(connector_id: str):
    """Delete a connector"""
    success = await connector_factory.remove_connector(connector_id)
    if not success:
        raise HTTPException(status_code=404, detail="Connector not found")

    return {"success": True, "message": f"Connector {connector_id} deleted"}


@router.post("/connectors/{connector_id}/connect")
async def connect_connector(connector_id: str):
    """Connect a specific connector"""
    connector = await connector_factory.get_connector(connector_id)
    if not connector:
        raise HTTPException(status_code=404, detail="Connector not found")

    try:
        await connector.connect()
        return {
            "success": True,
            "status": connector.get_status()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/connectors/{connector_id}/disconnect")
async def disconnect_connector(connector_id: str):
    """Disconnect a specific connector"""
    connector = await connector_factory.get_connector(connector_id)
    if not connector:
        raise HTTPException(status_code=404, detail="Connector not found")

    await connector.disconnect()
    return {
        "success": True,
        "status": connector.get_status()
    }


@router.post("/connectors/{connector_id}/test")
async def test_connector(connector_id: str):
    """Test a connector's connection"""
    result = await connector_factory.test_connection(connector_id)
    return result


@router.post("/connectors/execute")
async def execute_operation(request: ExecuteOperationRequest):
    """Execute an operation on a connector"""
    result = await connector_factory.execute(
        request.connector_id,
        request.operation,
        **request.parameters
    )
    return result


# =============================================================================
# User/Role Query Endpoints
# =============================================================================

@router.get("/connectors/{connector_id}/users")
async def list_users(connector_id: str, pattern: Optional[str] = None):
    """List users from a connected system"""
    filters = {}
    if pattern:
        filters["username_pattern"] = pattern

    result = await connector_factory.execute(connector_id, "list_users", filters=filters)
    return result


@router.get("/connectors/{connector_id}/users/{user_id}")
async def get_user(connector_id: str, user_id: str):
    """Get user details from a connected system"""
    result = await connector_factory.execute(connector_id, "get_user", user_id=user_id)
    return result


@router.get("/connectors/{connector_id}/users/{user_id}/roles")
async def get_user_roles(connector_id: str, user_id: str):
    """Get user's roles from a connected system"""
    result = await connector_factory.execute(connector_id, "get_user_roles", user_id=user_id)
    return result


@router.get("/connectors/{connector_id}/roles")
async def list_roles(connector_id: str, pattern: Optional[str] = None):
    """List available roles from a connected system"""
    filters = {}
    if pattern:
        filters["role_pattern"] = pattern

    result = await connector_factory.execute(connector_id, "list_roles", filters=filters)
    return result


# =============================================================================
# Provisioning Endpoints
# =============================================================================

@router.post("/provision/user")
async def provision_user(request: ProvisionUserRequest, background_tasks: BackgroundTasks):
    """Provision a new user across systems"""
    user_data = {
        "user_id": request.user_id,
        "first_name": request.first_name,
        "last_name": request.last_name,
        "email": request.email,
        "department": request.department,
        "job_title": request.job_title,
        "manager_id": request.manager_id,
        "initial_password": request.initial_password or "Init1234!"
    }

    task = await provisioning_engine.provision_user(
        user_id=request.user_id,
        user_data=user_data,
        target_systems=request.target_systems,
        source_type=request.source_type,
        source_id=request.source_id
    )

    return {
        "success": task.status in (ProvisioningStatus.COMPLETED, ProvisioningStatus.PARTIALLY_COMPLETED),
        "task": task.to_dict()
    }


@router.post("/provision/roles/assign")
async def assign_roles(request: AssignRolesRequest):
    """Assign roles to a user"""
    priority_map = {
        "critical": TaskPriority.CRITICAL,
        "high": TaskPriority.HIGH,
        "normal": TaskPriority.NORMAL,
        "low": TaskPriority.LOW
    }

    task = await provisioning_engine.assign_roles(
        user_id=request.user_id,
        roles=request.roles,
        source_type=request.source_type,
        source_id=request.source_id
    )

    return {
        "success": task.status in (ProvisioningStatus.COMPLETED, ProvisioningStatus.PARTIALLY_COMPLETED),
        "task": task.to_dict()
    }


@router.post("/provision/roles/revoke")
async def revoke_roles(request: RevokeRolesRequest):
    """Revoke roles from a user"""
    task = await provisioning_engine.revoke_roles(
        user_id=request.user_id,
        roles=request.roles,
        source_type=request.source_type,
        source_id=request.source_id
    )

    return {
        "success": task.status in (ProvisioningStatus.COMPLETED, ProvisioningStatus.PARTIALLY_COMPLETED),
        "task": task.to_dict()
    }


@router.post("/provision/deprovision")
async def deprovision_user(request: DeprovisionUserRequest):
    """Deprovision a user from systems"""
    task = await provisioning_engine.deprovision_user(
        user_id=request.user_id,
        target_systems=request.target_systems,
        action=request.action,
        source_type=request.source_type,
        source_id=request.source_id
    )

    return {
        "success": task.status in (ProvisioningStatus.COMPLETED, ProvisioningStatus.PARTIALLY_COMPLETED),
        "task": task.to_dict()
    }


# =============================================================================
# Task Management Endpoints
# =============================================================================

@router.get("/tasks")
async def list_tasks(
    status: Optional[str] = None,
    user_id: Optional[str] = None,
    source_type: Optional[str] = None,
    limit: int = 100
):
    """List provisioning tasks"""
    status_enum = None
    if status:
        try:
            status_enum = ProvisioningStatus(status)
        except ValueError:
            pass

    tasks = provisioning_engine.list_tasks(
        status=status_enum,
        user_id=user_id,
        source_type=source_type,
        limit=limit
    )

    return {
        "tasks": [t.to_summary() for t in tasks],
        "count": len(tasks)
    }


@router.get("/tasks/{task_id}")
async def get_task(task_id: str):
    """Get task details"""
    task = provisioning_engine.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    return task.to_dict()


@router.post("/tasks/{task_id}/cancel")
async def cancel_task(task_id: str):
    """Cancel a provisioning task"""
    success = await provisioning_engine.cancel_task(task_id)
    if not success:
        raise HTTPException(status_code=400, detail="Task cannot be cancelled")

    return {"success": True, "message": f"Task {task_id} cancelled"}


# =============================================================================
# Queue Management Endpoints
# =============================================================================

@router.get("/queue/status")
async def get_queue_status():
    """Get provisioning queue status"""
    return provisioning_queue.get_status()


@router.get("/queue/tasks")
async def list_queue_tasks(limit: int = 100):
    """List tasks in the queue"""
    return {
        "queued": provisioning_queue.list_queued(limit),
        "processing": provisioning_queue.list_processing(),
        "completed": provisioning_queue.list_completed(limit),
        "failed": provisioning_queue.list_failed(limit)
    }


@router.post("/queue/start")
async def start_queue():
    """Start the provisioning queue"""
    await provisioning_queue.start()
    return {"success": True, "status": provisioning_queue.get_status()}


@router.post("/queue/stop")
async def stop_queue():
    """Stop the provisioning queue"""
    await provisioning_queue.stop()
    return {"success": True, "status": provisioning_queue.get_status()}


@router.post("/queue/tasks/{task_id}/retry")
async def retry_failed_task(task_id: str):
    """Retry a failed task"""
    success = await provisioning_queue.retry_failed(task_id)
    if not success:
        raise HTTPException(status_code=404, detail="Task not found in failed queue")

    return {"success": True, "message": f"Task {task_id} requeued"}


@router.delete("/queue/tasks/{task_id}")
async def remove_from_queue(task_id: str):
    """Remove a task from the queue"""
    success = await provisioning_queue.cancel_task(task_id)
    if not success:
        raise HTTPException(status_code=404, detail="Task not found in queue")

    return {"success": True, "message": f"Task {task_id} removed from queue"}
