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
from core.integrations.connectors import ConnectorType
from core.identity.ad_sap_mapping import ADSAPMappingEngine
from core.scheduler.automation_jobs import AutomationScheduler

router = APIRouter(tags=["Integrations"])

connector_manager = ConnectorManager()
mapping_engine = ADSAPMappingEngine()
automation_scheduler = AutomationScheduler()

# Map API type strings to ConnectorType enum
_TYPE_MAP = {
    "sap": ConnectorType.SAP_RFC,
    "sap_rfc": ConnectorType.SAP_RFC,
    "sap_odata": ConnectorType.SAP_ODATA,
    "active_directory": ConnectorType.ACTIVE_DIRECTORY,
    "azure_ad": ConnectorType.AZURE_AD,
    "okta": ConnectorType.OKTA,
    "ldap": ConnectorType.LDAP,
    "generic_rest": ConnectorType.REST_API,
    "rest_api": ConnectorType.REST_API,
    "database": ConnectorType.DATABASE,
    "servicenow": ConnectorType.SERVICENOW,
    "custom": ConnectorType.CUSTOM,
}


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


class ADSAPMappingRequest(BaseModel):
    ad_group: str
    sap_role: str
    sap_system: str = "DEFAULT"
    auto_provision: bool = True
    description: str = ""


class ADSAPSyncRequest(BaseModel):
    user_ids: Optional[List[str]] = None


# Connector Management Endpoints
@router.get("/connectors")
async def list_connectors(
    connector_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None)
):
    """List all configured connectors"""
    type_enum = _TYPE_MAP.get(connector_type) if connector_type else None
    connectors_data = connector_manager.list_connectors(connector_type=type_enum)

    # Manager returns list of {"config": ..., "status": ...} dicts
    # Flatten into connector info list
    result = []
    for item in connectors_data:
        config = item.get("config", {})
        st = item.get("status", {})
        entry = {**config, **st}
        result.append(entry)

    return {
        "total": len(result),
        "connectors": result
    }


@router.get("/connectors/{connector_id}")
async def get_connector(connector_id: str):
    """Get connector details"""
    connector = connector_manager.get_connector(connector_id)
    if not connector:
        raise HTTPException(status_code=404, detail="Connector not found")
    info = connector.get_info()
    return info


@router.post("/connectors")
async def create_connector(request: ConnectorConfigRequest):
    """Create a new connector"""
    type_enum = _TYPE_MAP.get(request.connector_type)
    if not type_enum:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown connector type: {request.connector_type}. "
                   f"Valid types: {list(_TYPE_MAP.keys())}"
        )
    try:
        connector = connector_manager.create_connector(
            name=request.name,
            connector_type=type_enum,
            host=request.host,
            port=request.port,
            username=request.username,
            password=request.password,
            use_ssl=request.use_ssl,
        )
        return connector.get_info()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/connectors/{connector_id}")
async def update_connector(connector_id: str, request: UpdateConnectorRequest):
    """Update connector configuration"""
    try:
        updates = {k: v for k, v in request.model_dump().items() if v is not None}
        connector_manager.update_config(config_id=connector_id, **updates)
        connector = connector_manager.get_connector(connector_id)
        if connector:
            return connector.get_info()
        raise ValueError(f"Connector {connector_id} not found")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/connectors/{connector_id}")
async def delete_connector(connector_id: str):
    """Delete a connector"""
    deleted = connector_manager.delete_connector(connector_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Connector {connector_id} not found")
    return {"status": "deleted", "connector_id": connector_id}


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


# ============================================================
# AD-SAP Mapping Endpoints
# ============================================================

@router.get("/ad-sap-mappings")
async def list_ad_sap_mappings(
    ad_group: Optional[str] = Query(None),
    sap_role: Optional[str] = Query(None),
):
    """List all AD group to SAP role mappings."""
    if ad_group:
        mappings = mapping_engine.get_mappings_for_group(ad_group)
    elif sap_role:
        mappings = mapping_engine.get_mappings_for_role(sap_role)
    else:
        mappings = mapping_engine.get_all_mappings()

    return {
        "total": len(mappings),
        "mappings": [m.to_dict() for m in mappings],
        "stats": mapping_engine.get_stats(),
    }


@router.post("/ad-sap-mappings")
async def add_ad_sap_mapping(request: ADSAPMappingRequest):
    """Add a new AD group to SAP role mapping."""
    try:
        mapping = mapping_engine.add_mapping(
            ad_group=request.ad_group,
            sap_role=request.sap_role,
            sap_system=request.sap_system,
            auto_provision=request.auto_provision,
            description=request.description,
        )
        return mapping.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/ad-sap-mappings/{mapping_id}")
async def remove_ad_sap_mapping(mapping_id: str):
    """Remove an AD-SAP mapping by ID."""
    removed = mapping_engine.remove_mapping_by_id(mapping_id)
    if not removed:
        raise HTTPException(status_code=404, detail=f"Mapping {mapping_id} not found")
    return {"status": "deleted", "mapping_id": mapping_id}


@router.post("/ad-sap-mappings/sync")
async def trigger_ad_sap_sync(request: ADSAPSyncRequest = None):
    """Trigger AD to SAP role synchronization."""
    user_ids = request.user_ids if request else None
    result = mapping_engine.bulk_sync(user_ids=user_ids)
    return result.to_dict()


# ============================================================
# Automation Job Endpoints
# ============================================================

@router.get("/automation/jobs")
async def list_automation_jobs():
    """List all scheduled automation jobs."""
    jobs = automation_scheduler.get_jobs()
    return {
        "total": len(jobs),
        "jobs": [j.to_dict() for j in jobs],
    }


@router.post("/automation/jobs/{job_name}/run")
async def trigger_automation_job(job_name: str):
    """Trigger a specific automation job manually."""
    job_def = automation_scheduler.get_job(job_name)
    if not job_def:
        raise HTTPException(status_code=404, detail=f"Job '{job_name}' not found")

    result = await automation_scheduler.run_job(job_name)
    return result.to_dict()


@router.get("/automation/history")
async def get_automation_history(limit: int = Query(default=20, le=100)):
    """Get recent automation job execution history."""
    history = automation_scheduler.get_job_history(limit=limit)
    return {
        "total": len(history),
        "history": [h.to_dict() for h in history],
    }
