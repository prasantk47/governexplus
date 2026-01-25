"""
Integration & Connectors API Router

Endpoints for managing system connectors and data synchronization.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime

from core.integrations import (
    ConnectorManager, ConnectionStatus
)

router = APIRouter(tags=["Integrations"])

connector_manager = ConnectorManager()


# Request Models
class ConnectorConfigRequest(BaseModel):
    name: str
    connector_type: str
    host: str
    port: int
    username: str
    password: str
    use_ssl: bool = True
    additional_config: Dict = Field(default_factory=dict)


class UpdateConnectorRequest(BaseModel):
    name: Optional[str] = None
    host: Optional[str] = None
    port: Optional[int] = None
    username: Optional[str] = None
    password: Optional[str] = None
    use_ssl: Optional[bool] = None
    additional_config: Optional[Dict] = None


class SyncConfigRequest(BaseModel):
    sync_users: bool = True
    sync_roles: bool = True
    sync_assignments: bool = True
    full_sync: bool = False


# Connector Management Endpoints
@router.get("/connectors")
async def list_connectors(
    connector_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None)
):
    """List all configured connectors"""
    status_enum = ConnectionStatus(status) if status else None
    connectors = connector_manager.list_connectors(connector_type, status_enum)
    return {
        "total": len(connectors),
        "connectors": [c.get_info() for c in connectors]
    }


@router.get("/connectors/{connector_id}")
async def get_connector(connector_id: str):
    """Get connector details"""
    connector = connector_manager.get_connector(connector_id)
    if not connector:
        raise HTTPException(status_code=404, detail="Connector not found")
    return connector.get_info()


@router.post("/connectors")
async def create_connector(request: ConnectorConfigRequest):
    """Create a new connector"""
    try:
        connector = connector_manager.create_connector(
            name=request.name,
            connector_type=request.connector_type,
            host=request.host,
            port=request.port,
            username=request.username,
            password=request.password,
            use_ssl=request.use_ssl,
            additional_config=request.additional_config
        )
        return connector.get_info()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/connectors/{connector_id}")
async def update_connector(connector_id: str, request: UpdateConnectorRequest):
    """Update connector configuration"""
    try:
        connector = connector_manager.update_connector(
            connector_id=connector_id,
            name=request.name,
            host=request.host,
            port=request.port,
            username=request.username,
            password=request.password,
            use_ssl=request.use_ssl,
            additional_config=request.additional_config
        )
        return connector.get_info()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/connectors/{connector_id}")
async def delete_connector(connector_id: str):
    """Delete a connector"""
    try:
        connector_manager.delete_connector(connector_id)
        return {"status": "deleted", "connector_id": connector_id}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# Connection Management
@router.post("/connectors/{connector_id}/connect")
async def connect(connector_id: str):
    """Establish connection to a system"""
    try:
        result = connector_manager.connect(connector_id)
        return {
            "connector_id": connector_id,
            "status": "connected" if result else "failed",
            "connected_at": datetime.now().isoformat()
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/connectors/{connector_id}/disconnect")
async def disconnect(connector_id: str):
    """Disconnect from a system"""
    try:
        connector_manager.disconnect(connector_id)
        return {
            "connector_id": connector_id,
            "status": "disconnected"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/connectors/{connector_id}/test")
async def test_connection(connector_id: str):
    """Test connector connection"""
    try:
        result = connector_manager.test_connection(connector_id)
        return {
            "connector_id": connector_id,
            "success": result["success"],
            "latency_ms": result.get("latency_ms"),
            "message": result.get("message"),
            "tested_at": datetime.now().isoformat()
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/connectors/{connector_id}/status")
async def get_connection_status(connector_id: str):
    """Get current connection status"""
    try:
        status = connector_manager.get_connection_status(connector_id)
        return status
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# Data Synchronization
@router.post("/connectors/{connector_id}/sync")
async def sync_data(
    connector_id: str,
    request: SyncConfigRequest
):
    """Synchronize data from connected system"""
    try:
        result = connector_manager.sync_data(
            connector_id=connector_id,
            sync_users=request.sync_users,
            sync_roles=request.sync_roles,
            sync_assignments=request.sync_assignments,
            full_sync=request.full_sync
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/connectors/{connector_id}/sync/status")
async def get_sync_status(connector_id: str):
    """Get synchronization status"""
    try:
        status = connector_manager.get_sync_status(connector_id)
        return status
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/connectors/{connector_id}/sync/history")
async def get_sync_history(
    connector_id: str,
    limit: int = Query(default=10, le=100)
):
    """Get synchronization history"""
    try:
        history = connector_manager.get_sync_history(connector_id, limit)
        return {"total": len(history), "history": history}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# Data Retrieval
@router.get("/connectors/{connector_id}/users")
async def get_users(
    connector_id: str,
    search: Optional[str] = Query(None),
    limit: int = Query(default=100, le=1000),
    offset: int = Query(default=0)
):
    """Get users from connected system"""
    try:
        users = connector_manager.get_users(connector_id, search, limit, offset)
        return users
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/connectors/{connector_id}/users/{user_id}")
async def get_user(connector_id: str, user_id: str):
    """Get specific user from connected system"""
    try:
        user = connector_manager.get_user(connector_id, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return user
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/connectors/{connector_id}/roles")
async def get_roles(
    connector_id: str,
    search: Optional[str] = Query(None),
    limit: int = Query(default=100, le=1000),
    offset: int = Query(default=0)
):
    """Get roles from connected system"""
    try:
        roles = connector_manager.get_roles(connector_id, search, limit, offset)
        return roles
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/connectors/{connector_id}/roles/{role_id}")
async def get_role(connector_id: str, role_id: str):
    """Get specific role from connected system"""
    try:
        role = connector_manager.get_role(connector_id, role_id)
        if not role:
            raise HTTPException(status_code=404, detail="Role not found")
        return role
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/connectors/{connector_id}/assignments")
async def get_assignments(
    connector_id: str,
    user_id: Optional[str] = Query(None),
    role_id: Optional[str] = Query(None),
    limit: int = Query(default=100, le=1000),
    offset: int = Query(default=0)
):
    """Get role assignments from connected system"""
    try:
        assignments = connector_manager.get_assignments(
            connector_id, user_id, role_id, limit, offset
        )
        return assignments
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# Connector Types & Capabilities
@router.get("/connector-types")
async def list_connector_types():
    """List available connector types"""
    return {
        "connector_types": [
            {
                "type": "sap",
                "name": "SAP ERP",
                "description": "SAP ERP system connector via RFC",
                "capabilities": ["users", "roles", "assignments", "transactions", "auth_objects"],
                "required_config": ["client", "system_number", "language"]
            },
            {
                "type": "active_directory",
                "name": "Active Directory",
                "description": "Microsoft Active Directory connector via LDAP",
                "capabilities": ["users", "groups", "memberships", "ous"],
                "required_config": ["base_dn", "domain"]
            },
            {
                "type": "azure_ad",
                "name": "Azure Active Directory",
                "description": "Azure AD connector via Microsoft Graph API",
                "capabilities": ["users", "groups", "roles", "applications", "service_principals"],
                "required_config": ["tenant_id", "client_id", "client_secret"]
            },
            {
                "type": "generic_rest",
                "name": "Generic REST API",
                "description": "Generic REST API connector for custom systems",
                "capabilities": ["users", "roles", "custom"],
                "required_config": ["base_url", "auth_type"]
            }
        ]
    }


# Health & Monitoring
@router.get("/health")
async def get_integrations_health():
    """Get overall integrations health status"""
    return connector_manager.get_health_status()


@router.get("/metrics")
async def get_integration_metrics():
    """Get integration metrics"""
    return connector_manager.get_metrics()


# Import/Export Configuration
@router.get("/connectors/{connector_id}/export-config")
async def export_connector_config(connector_id: str):
    """Export connector configuration (without sensitive data)"""
    try:
        config = connector_manager.export_config(connector_id)
        return config
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/import-config")
async def import_connector_config(config: Dict):
    """Import connector configuration"""
    try:
        connector = connector_manager.import_config(config)
        return connector.get_info()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
