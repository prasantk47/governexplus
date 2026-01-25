# Setup Wizard API Router
# Zero Training Experience - Guided Setup

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
from datetime import datetime

from core.setup import (
    SetupWizard, SetupStep, SetupStatus,
    SystemConnection, ConnectionType,
    QuickStartTemplate, TemplateType
)

router = APIRouter(prefix="/setup", tags=["Setup Wizard"])

# Global wizard instance (would be per-tenant in production)
wizard = SetupWizard()


# ==================== Request/Response Models ====================

class TemplateSelectionRequest(BaseModel):
    template_id: str


class StepDataRequest(BaseModel):
    step_id: str
    data: Dict[str, Any]


class ConnectionRequest(BaseModel):
    name: str
    connection_type: str
    host: str
    port: int = 3300
    client: str = ""
    username: str = ""
    password: str = ""
    use_sso: bool = False


class ConfigImportRequest(BaseModel):
    config: Dict[str, Any]


# ==================== Progress & Status ====================

@router.get("/")
async def get_setup_status():
    """
    Get current setup wizard status and progress

    Returns overall progress, current step, and estimated time remaining.
    """
    return {
        "progress": wizard.get_progress(),
        "steps_by_category": {
            category: [
                {
                    "id": step.id,
                    "name": step.name,
                    "status": step.status.value,
                    "required": step.required,
                    "auto_complete": step.auto_complete
                }
                for step in steps
            ]
            for category, steps in wizard.get_steps_by_category().items()
        }
    }


@router.get("/progress")
async def get_progress():
    """Get setup progress summary"""
    return wizard.get_progress()


# ==================== Templates ====================

@router.get("/templates")
async def list_templates():
    """
    List available quick-start templates

    Templates provide pre-configured settings for different organization types.
    """
    return {
        "templates": [
            {
                "id": t.id,
                "name": t.name,
                "description": t.description,
                "type": t.template_type.value,
                "features": t.features,
                "recommended_for": t.recommended_for
            }
            for t in wizard.templates.values()
        ]
    }


@router.get("/templates/{template_id}")
async def get_template(template_id: str):
    """Get details for a specific template"""
    if template_id not in wizard.templates:
        raise HTTPException(status_code=404, detail="Template not found")

    t = wizard.templates[template_id]
    return {
        "id": t.id,
        "name": t.name,
        "description": t.description,
        "type": t.template_type.value,
        "features": t.features,
        "default_settings": t.default_settings,
        "recommended_for": t.recommended_for
    }


@router.post("/templates/apply")
async def apply_template(request: TemplateSelectionRequest):
    """
    Apply a quick-start template

    This pre-fills many configuration steps with recommended defaults.
    """
    result = wizard.apply_template(request.template_id)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


# ==================== Quick Setup ====================

@router.post("/quick-setup")
async def quick_setup(template_id: str = "standard"):
    """
    One-click quick setup with a template

    Automatically completes all auto-completable steps.
    Returns list of steps that need manual input.
    """
    result = wizard.quick_setup(template_id)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


# ==================== Steps ====================

@router.get("/steps")
async def list_steps():
    """List all setup steps with their status"""
    return {
        "steps": [
            {
                "id": step.id,
                "name": step.name,
                "description": step.description,
                "category": step.category,
                "order": step.order,
                "status": step.status.value,
                "required": step.required,
                "estimated_minutes": step.estimated_minutes,
                "auto_complete": step.auto_complete,
                "help_url": step.help_url
            }
            for step in sorted(wizard.steps.values(), key=lambda s: s.order)
        ]
    }


@router.get("/steps/{step_id}")
async def get_step(step_id: str):
    """
    Get step details including guidance and defaults

    Returns helpful information for completing the step.
    """
    if step_id not in wizard.steps:
        raise HTTPException(status_code=404, detail="Step not found")

    step = wizard.steps[step_id]
    return {
        "step": {
            "id": step.id,
            "name": step.name,
            "description": step.description,
            "category": step.category,
            "status": step.status.value,
            "required": step.required,
            "estimated_minutes": step.estimated_minutes,
            "auto_complete": step.auto_complete,
            "data": step.data,
            "validation_errors": step.validation_errors
        },
        "guidance": wizard._get_step_guidance(step_id),
        "defaults": wizard._get_step_defaults(step_id)
    }


@router.post("/steps/{step_id}/start")
async def start_step(step_id: str):
    """Start working on a step"""
    result = wizard.start_step(step_id)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/steps/{step_id}/complete")
async def complete_step(step_id: str, request: StepDataRequest):
    """Complete a step with the provided data"""
    result = wizard.complete_step(step_id, request.data)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("errors", result.get("error")))
    return result


@router.post("/steps/{step_id}/skip")
async def skip_step(step_id: str):
    """Skip an optional step"""
    result = wizard.skip_step(step_id)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/steps/{step_id}/auto-complete")
async def auto_complete_step(step_id: str):
    """Auto-complete a step using smart defaults"""
    result = wizard.auto_complete_step(step_id)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/steps/next")
async def get_next_step():
    """Get the next incomplete step"""
    step = wizard.get_next_step()
    if not step:
        return {"message": "All steps complete", "next_step": None}

    return {
        "next_step": {
            "id": step.id,
            "name": step.name,
            "description": step.description,
            "category": step.category
        },
        "guidance": wizard._get_step_guidance(step.id)
    }


# ==================== Connections ====================

@router.get("/connections")
async def list_connections():
    """List configured system connections"""
    return {
        "connections": [
            {
                "id": conn.id,
                "name": conn.name,
                "type": conn.connection_type.value,
                "host": conn.host,
                "port": conn.port,
                "enabled": conn.enabled,
                "test_status": conn.test_status,
                "last_tested": conn.last_tested.isoformat() if conn.last_tested else None
            }
            for conn in wizard.connections.values()
        ]
    }


@router.post("/connections")
async def add_connection(request: ConnectionRequest):
    """Add a new system connection"""
    try:
        conn_type = ConnectionType(request.connection_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid connection type: {request.connection_type}")

    connection = SystemConnection(
        name=request.name,
        connection_type=conn_type,
        host=request.host,
        port=request.port,
        client=request.client,
        username=request.username,
        use_sso=request.use_sso
    )

    result = wizard.add_connection(connection)
    return result


@router.post("/connections/{connection_id}/test")
async def test_connection(connection_id: str):
    """Test a system connection"""
    result = wizard.test_connection(connection_id)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


# ==================== Finalization ====================

@router.post("/finalize")
async def finalize_setup():
    """
    Finalize and complete the setup wizard

    Validates all required steps are complete and activates the platform.
    """
    result = wizard.finalize_setup()
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result)
    return result


@router.get("/summary")
async def get_setup_summary():
    """Get a summary of the completed setup"""
    return wizard._generate_setup_summary()


# ==================== Configuration Export/Import ====================

@router.get("/config/export")
async def export_config():
    """Export current configuration for backup"""
    return wizard.export_config()


@router.post("/config/import")
async def import_config(request: ConfigImportRequest):
    """Import a previously exported configuration"""
    result = wizard.import_config(request.config)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


# ==================== Help & Documentation ====================

@router.get("/help")
async def get_help():
    """Get help and documentation links"""
    return {
        "getting_started": "/docs/setup/getting-started",
        "video_tutorials": [
            {"title": "Quick Start Guide", "url": "/docs/videos/quick-start"},
            {"title": "Connecting SAP Systems", "url": "/docs/videos/sap-connection"},
            {"title": "Configuring SoD Rules", "url": "/docs/videos/sod-rules"}
        ],
        "documentation": {
            "setup_guide": "/docs/setup",
            "admin_guide": "/docs/admin",
            "user_guide": "/docs/user",
            "api_reference": "/docs/api"
        },
        "support": {
            "email": "support@grc-platform.com",
            "knowledge_base": "/support/kb"
        }
    }
