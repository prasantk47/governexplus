# Workflows API Router
# MSMP Multi-Stage Multi-Path Workflow Management

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
from datetime import datetime

from core.workflow import (
    MSMPEngine, WorkflowPath, WorkflowStage,
    ParallelPath, AgentRule, AgentRuleType
)

router = APIRouter(prefix="/workflows", tags=["Workflows"])

# Global engine instance
workflow_engine = MSMPEngine()


# ==================== Request/Response Models ====================

class CreateWorkflowRequest(BaseModel):
    id: str
    name: str
    description: str = ""
    stages: List[Dict[str, Any]]
    conditions: Dict[str, Any] = {}


class AgentRuleRequest(BaseModel):
    id: str
    name: str
    rule_type: str
    description: str = ""
    priority: int = 100
    conditions: Dict[str, Any] = {}
    agent_expression: str = ""


class ProcessStageRequest(BaseModel):
    request_id: str
    workflow_id: str
    stage_index: int
    action: str  # approve, reject
    agent_id: str
    comments: str = ""


class DetermineAgentsRequest(BaseModel):
    workflow_id: str
    stage_index: int
    path_index: int = 0
    request_context: Dict[str, Any]


# ==================== Workflow Definitions ====================

@router.get("/")
async def list_workflows():
    """
    List all workflow definitions

    Returns both pre-built and custom workflows.
    """
    return {
        "workflows": [
            {
                "id": wf.id,
                "name": wf.name,
                "description": wf.description,
                "stages_count": len(wf.stages),
                "has_parallel_paths": any(len(s.parallel_paths) > 0 for s in wf.stages),
                "conditions": wf.conditions
            }
            for wf in workflow_engine.workflows.values()
        ]
    }


@router.get("/{workflow_id}")
async def get_workflow(workflow_id: str):
    """Get detailed workflow definition"""
    if workflow_id not in workflow_engine.workflows:
        raise HTTPException(status_code=404, detail="Workflow not found")

    wf = workflow_engine.workflows[workflow_id]

    return {
        "id": wf.id,
        "name": wf.name,
        "description": wf.description,
        "conditions": wf.conditions,
        "stages": [
            {
                "name": stage.name,
                "order": stage.order,
                "required": stage.required,
                "agent_rules": [
                    {
                        "id": rule.id,
                        "name": rule.name,
                        "type": rule.rule_type.value,
                        "priority": rule.priority
                    }
                    for rule in stage.agent_rules
                ],
                "parallel_paths": [
                    {
                        "id": path.id,
                        "name": path.name,
                        "required": path.required,
                        "agent_rules": [
                            {"id": r.id, "name": r.name, "type": r.rule_type.value}
                            for r in path.agent_rules
                        ]
                    }
                    for path in stage.parallel_paths
                ],
                "approval_mode": stage.approval_mode
            }
            for stage in wf.stages
        ]
    }


@router.post("/")
async def create_workflow(request: CreateWorkflowRequest):
    """Create a new custom workflow"""
    if request.id in workflow_engine.workflows:
        raise HTTPException(status_code=400, detail="Workflow ID already exists")

    stages = []
    for i, stage_data in enumerate(request.stages):
        # Parse agent rules
        agent_rules = []
        for rule_data in stage_data.get("agent_rules", []):
            try:
                rule_type = AgentRuleType(rule_data.get("rule_type", "static"))
            except ValueError:
                rule_type = AgentRuleType.STATIC

            agent_rules.append(AgentRule(
                id=rule_data.get("id", f"rule_{i}"),
                name=rule_data.get("name", ""),
                rule_type=rule_type,
                priority=rule_data.get("priority", 100),
                conditions=rule_data.get("conditions", {}),
                agent_expression=rule_data.get("agent_expression", "")
            ))

        stages.append(WorkflowStage(
            name=stage_data.get("name", f"Stage {i+1}"),
            order=i,
            required=stage_data.get("required", True),
            agent_rules=agent_rules,
            approval_mode=stage_data.get("approval_mode", "any")
        ))

    workflow = WorkflowPath(
        id=request.id,
        name=request.name,
        description=request.description,
        stages=stages,
        conditions=request.conditions
    )

    workflow_engine.workflows[request.id] = workflow

    return {
        "success": True,
        "workflow_id": request.id,
        "message": f"Workflow '{request.name}' created successfully"
    }


@router.delete("/{workflow_id}")
async def delete_workflow(workflow_id: str):
    """Delete a custom workflow"""
    if workflow_id not in workflow_engine.workflows:
        raise HTTPException(status_code=404, detail="Workflow not found")

    # Prevent deletion of built-in workflows
    if workflow_id.startswith("wf_"):
        raise HTTPException(status_code=400, detail="Cannot delete built-in workflows")

    del workflow_engine.workflows[workflow_id]
    return {"success": True, "message": "Workflow deleted"}


# ==================== Agent Rules ====================

@router.get("/agent-rules")
async def list_agent_rules():
    """List all agent rule definitions"""
    return {
        "rules": [
            {
                "id": rule.id,
                "name": rule.name,
                "type": rule.rule_type.value,
                "description": rule.description,
                "priority": rule.priority
            }
            for rule in workflow_engine.agent_rules.values()
        ]
    }


@router.get("/agent-rules/types")
async def list_agent_rule_types():
    """List available agent rule types"""
    return {
        "types": [
            {
                "value": rt.value,
                "name": rt.name,
                "description": {
                    "static": "Fixed list of approvers",
                    "manager": "Requester's manager chain",
                    "role_owner": "Owner of the requested role",
                    "security_team": "Security team members",
                    "cost_center_owner": "Cost center owner/manager",
                    "department_head": "Department head",
                    "custom_lookup": "Custom lookup from external source",
                    "expression": "Dynamic expression-based determination"
                }.get(rt.value, "")
            }
            for rt in AgentRuleType
        ]
    }


@router.get("/agent-rules/{rule_id}")
async def get_agent_rule(rule_id: str):
    """Get agent rule details"""
    if rule_id not in workflow_engine.agent_rules:
        raise HTTPException(status_code=404, detail="Agent rule not found")

    rule = workflow_engine.agent_rules[rule_id]
    return {
        "id": rule.id,
        "name": rule.name,
        "type": rule.rule_type.value,
        "description": rule.description,
        "priority": rule.priority,
        "conditions": rule.conditions,
        "agent_expression": rule.agent_expression
    }


@router.post("/agent-rules")
async def create_agent_rule(request: AgentRuleRequest):
    """Create a new agent rule"""
    try:
        rule_type = AgentRuleType(request.rule_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid rule type: {request.rule_type}")

    rule = AgentRule(
        id=request.id,
        name=request.name,
        rule_type=rule_type,
        description=request.description,
        priority=request.priority,
        conditions=request.conditions,
        agent_expression=request.agent_expression
    )

    workflow_engine.agent_rules[request.id] = rule

    return {
        "success": True,
        "rule_id": request.id,
        "message": f"Agent rule '{request.name}' created successfully"
    }


# ==================== Workflow Selection ====================

@router.post("/select")
async def select_workflow(request_context: Dict[str, Any]):
    """
    Select the appropriate workflow for a request

    Evaluates request context against workflow conditions.
    """
    result = workflow_engine.select_workflow(request_context)
    return result


@router.post("/determine-agents")
async def determine_agents(request: DetermineAgentsRequest):
    """
    Determine approvers for a workflow stage

    Uses dynamic agent rules (BRF+ style) to find appropriate approvers.
    """
    result = workflow_engine.determine_agents(
        workflow_id=request.workflow_id,
        stage_index=request.stage_index,
        path_index=request.path_index,
        request_context=request.request_context
    )

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])

    return result


# ==================== Workflow Execution ====================

@router.post("/start")
async def start_workflow(request_id: str, workflow_id: str, context: Dict[str, Any]):
    """
    Start a workflow for a request

    Creates workflow instance and determines first stage approvers.
    """
    result = workflow_engine.start_workflow(
        request_id=request_id,
        workflow_id=workflow_id,
        context=context
    )

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])

    return result


@router.get("/instances/{request_id}")
async def get_workflow_instance(request_id: str):
    """Get workflow instance status for a request"""
    if request_id not in workflow_engine.active_workflows:
        raise HTTPException(status_code=404, detail="Workflow instance not found")

    instance = workflow_engine.active_workflows[request_id]
    return {
        "request_id": request_id,
        "workflow_id": instance["workflow_id"],
        "current_stage": instance["current_stage"],
        "status": instance["status"],
        "started_at": instance["started_at"].isoformat(),
        "stages": instance["stages"],
        "parallel_status": instance.get("parallel_status", {})
    }


@router.post("/instances/{request_id}/process")
async def process_stage(request_id: str, request: ProcessStageRequest):
    """
    Process a workflow stage action (approve/reject)

    Handles parallel path completion and stage advancement.
    """
    result = workflow_engine.process_stage(
        request_id=request_id,
        stage_index=request.stage_index,
        action=request.action,
        agent_id=request.agent_id,
        comments=request.comments
    )

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])

    return result


@router.get("/instances/{request_id}/next-stage")
async def get_next_stage(request_id: str):
    """Get next stage info for a workflow"""
    if request_id not in workflow_engine.active_workflows:
        raise HTTPException(status_code=404, detail="Workflow instance not found")

    instance = workflow_engine.active_workflows[request_id]
    workflow = workflow_engine.workflows.get(instance["workflow_id"])

    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow definition not found")

    current = instance["current_stage"]
    if current >= len(workflow.stages):
        return {"message": "Workflow complete", "next_stage": None}

    next_stage = workflow.stages[current]
    return {
        "stage_index": current,
        "stage_name": next_stage.name,
        "required": next_stage.required,
        "has_parallel_paths": len(next_stage.parallel_paths) > 0
    }


# ==================== Workflow History ====================

@router.get("/history")
async def get_workflow_history(
    status: Optional[str] = None,
    limit: int = Query(default=50, le=200),
    offset: int = 0
):
    """Get workflow execution history"""
    history = list(workflow_engine.workflow_history)

    if status:
        history = [h for h in history if h.get("status") == status]

    total = len(history)
    history = history[offset:offset + limit]

    return {
        "history": history,
        "total": total
    }


@router.get("/history/{request_id}")
async def get_request_history(request_id: str):
    """Get workflow history for a specific request"""
    history = [
        h for h in workflow_engine.workflow_history
        if h.get("request_id") == request_id
    ]

    if not history:
        raise HTTPException(status_code=404, detail="No history found for request")

    return {"history": history}


# ==================== Workflow Statistics ====================

@router.get("/stats")
async def get_workflow_stats():
    """Get workflow statistics"""
    active_count = len(workflow_engine.active_workflows)
    completed_count = len([
        h for h in workflow_engine.workflow_history
        if h.get("status") == "completed"
    ])
    rejected_count = len([
        h for h in workflow_engine.workflow_history
        if h.get("status") == "rejected"
    ])

    # Workflows by type
    by_workflow = {}
    for instance in workflow_engine.active_workflows.values():
        wf_id = instance["workflow_id"]
        if wf_id not in by_workflow:
            by_workflow[wf_id] = 0
        by_workflow[wf_id] += 1

    return {
        "active_workflows": active_count,
        "completed_workflows": completed_count,
        "rejected_workflows": rejected_count,
        "by_workflow_type": by_workflow,
        "workflow_definitions": len(workflow_engine.workflows),
        "agent_rules": len(workflow_engine.agent_rules)
    }


# ==================== Pre-built Workflows Info ====================

@router.get("/prebuilt")
async def list_prebuilt_workflows():
    """List pre-built workflow templates"""
    prebuilt = [
        {
            "id": "wf_standard",
            "name": "Standard Approval",
            "description": "Manager and role owner approval",
            "use_case": "Normal access requests"
        },
        {
            "id": "wf_high_risk",
            "name": "High Risk Approval",
            "description": "Manager, role owner, and security team approval",
            "use_case": "Requests with high risk scores"
        },
        {
            "id": "wf_multi_system",
            "name": "Multi-System Approval",
            "description": "Parallel approval for each system",
            "use_case": "Requests spanning multiple systems"
        },
        {
            "id": "wf_low_risk",
            "name": "Low Risk Fast Track",
            "description": "Manager-only approval",
            "use_case": "Low risk requests for quick approval"
        },
        {
            "id": "wf_emergency",
            "name": "Emergency Access",
            "description": "Security team immediate approval",
            "use_case": "Emergency/firefighter requests"
        }
    ]

    return {"prebuilt_workflows": prebuilt}
