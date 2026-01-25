"""
Productive Test Simulation (PTS) API Router for Governex+

Test role changes before deployment without affecting production.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

from core.role_testing import PTSSimulator, SimulationResult, SimulationScenario
from core.role_testing.simulator import pts_simulator, ChangeType

router = APIRouter(tags=["Productive Test Simulation"])


# =============================================================================
# Request Models
# =============================================================================

class ChangeRequest(BaseModel):
    """A proposed change to simulate"""
    change_type: str = Field(..., example="add_role")
    target_user: str = Field(default="", example="jsmith")
    target_users: List[str] = Field(default_factory=list)
    role_id: str = Field(default="", example="SAP_FI_ACCOUNTANT")
    role_name: str = Field(default="", example="Finance Accountant")
    permissions: List[Dict[str, Any]] = Field(default_factory=list)
    justification: str = Field(default="")


class CreateScenarioRequest(BaseModel):
    """Request to create a simulation scenario"""
    name: str = Field(..., example="Q1 Finance Role Update")
    description: str = Field(..., example="Adding new finance roles for Q1 reporting")
    changes: List[ChangeRequest]
    include_sod_check: bool = Field(default=True)
    include_sensitive_check: bool = Field(default=True)
    include_compliance_check: bool = Field(default=True)
    include_usage_analysis: bool = Field(default=True)
    target_system: str = Field(default="SAP ECC")
    target_client: str = Field(default="100")


class AddTestRequest(BaseModel):
    """Request to add a test scenario"""
    name: str = Field(..., example="Test vendor creation")
    user_id: str = Field(..., example="jsmith")
    transaction_code: str = Field(..., example="XK01")
    expected_result: str = Field(default="success")
    description: str = Field(default="")


# =============================================================================
# Scenario Management
# =============================================================================

@router.post("/scenarios")
async def create_scenario(
    request: CreateScenarioRequest,
    created_by: str = Query(..., example="admin@company.com")
):
    """
    Create a new simulation scenario.

    A scenario defines the changes you want to test and the conditions
    for the simulation.
    """
    changes = [c.model_dump() for c in request.changes]

    scenario = pts_simulator.create_scenario(
        name=request.name,
        description=request.description,
        created_by=created_by,
        changes=changes,
        include_sod_check=request.include_sod_check,
        include_sensitive_check=request.include_sensitive_check,
        include_compliance_check=request.include_compliance_check,
        include_usage_analysis=request.include_usage_analysis,
        target_system=request.target_system,
        target_client=request.target_client
    )

    return {
        "status": "success",
        "scenario_id": scenario.scenario_id,
        "message": f"Scenario '{request.name}' created successfully",
        "scenario": scenario.to_dict()
    }


@router.get("/scenarios/{scenario_id}")
async def get_scenario(scenario_id: str):
    """Get a scenario by ID"""
    scenario = pts_simulator.get_scenario(scenario_id)
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")

    return scenario.to_dict()


@router.post("/scenarios/{scenario_id}/tests")
async def add_test_scenario(scenario_id: str, request: AddTestRequest):
    """Add a test scenario to validate the changes"""
    try:
        test = pts_simulator.add_test_scenario(
            scenario_id=scenario_id,
            name=request.name,
            user_id=request.user_id,
            transaction_code=request.transaction_code,
            expected_result=request.expected_result,
            description=request.description
        )

        return {
            "status": "success",
            "test_id": test.scenario_id,
            "message": f"Test '{request.name}' added to scenario"
        }

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# =============================================================================
# Simulation Execution
# =============================================================================

@router.post("/scenarios/{scenario_id}/run")
async def run_simulation(scenario_id: str):
    """
    Run a complete simulation for a scenario.

    This will:
    1. Analyze each proposed change for impact
    2. Check for SoD conflicts
    3. Identify sensitive access grants
    4. Detect privilege escalations
    5. Execute test scenarios
    6. Generate recommendations
    """
    try:
        result = pts_simulator.run_simulation(scenario_id)

        return {
            "status": "success",
            "simulation_id": result.simulation_id,
            "overall_impact": result.overall_impact.value,
            "can_proceed": result.can_proceed,
            "summary": {
                "total_changes": result.total_changes,
                "changes_with_issues": result.changes_with_issues,
                "total_tests": result.total_tests,
                "tests_passed": result.tests_passed,
                "tests_failed": result.tests_failed,
                "blockers_count": len(result.blockers),
                "warnings_count": len(result.warnings)
            },
            "execution_time_seconds": result.execution_time_seconds,
            "result": result.to_dict()
        }

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/simulations/{simulation_id}")
async def get_simulation(simulation_id: str):
    """Get detailed simulation results"""
    result = pts_simulator.get_simulation(simulation_id)
    if not result:
        raise HTTPException(status_code=404, detail="Simulation not found")

    return result.to_dict()


@router.get("/simulations")
async def list_simulations(limit: int = Query(50, le=200)):
    """List recent simulations"""
    return {
        "simulations": pts_simulator.list_simulations(limit)
    }


# =============================================================================
# Quick Simulation (One-Step)
# =============================================================================

@router.post("/quick-simulate")
async def quick_simulate(
    request: CreateScenarioRequest,
    created_by: str = Query(..., example="admin@company.com")
):
    """
    Create and immediately run a simulation in one step.

    Useful for quick what-if analysis.
    """
    changes = [c.model_dump() for c in request.changes]

    # Create scenario
    scenario = pts_simulator.create_scenario(
        name=request.name,
        description=request.description,
        created_by=created_by,
        changes=changes,
        include_sod_check=request.include_sod_check,
        include_sensitive_check=request.include_sensitive_check,
        include_compliance_check=request.include_compliance_check,
        include_usage_analysis=request.include_usage_analysis,
        target_system=request.target_system,
        target_client=request.target_client
    )

    # Run simulation immediately
    result = pts_simulator.run_simulation(scenario.scenario_id)

    return {
        "status": "success",
        "scenario_id": scenario.scenario_id,
        "simulation_id": result.simulation_id,
        "overall_impact": result.overall_impact.value,
        "can_proceed": result.can_proceed,
        "blockers": result.blockers,
        "warnings": result.warnings,
        "recommendations": result.recommendations,
        "summary": {
            "changes_analyzed": result.total_changes,
            "issues_found": result.changes_with_issues,
            "sod_conflicts": sum(len(ia.sod_conflicts) for ia in result.impact_analyses),
            "privilege_escalations": sum(len(ia.privilege_escalations) for ia in result.impact_analyses)
        }
    }


# =============================================================================
# Reference Data
# =============================================================================

@router.get("/change-types")
async def list_change_types():
    """List all available change types"""
    return {
        "change_types": [
            {"value": ct.value, "name": ct.name}
            for ct in ChangeType
        ]
    }


@router.get("/statistics")
async def get_statistics():
    """Get PTS statistics"""
    return pts_simulator.get_statistics()


# =============================================================================
# Demo
# =============================================================================

@router.post("/demo/sample-scenario")
async def create_demo_scenario(created_by: str = Query(default="demo@governexplus.com")):
    """Create a sample scenario for demonstration"""

    scenario = pts_simulator.create_scenario(
        name="Demo: Finance Role Assignment",
        description="Testing assignment of finance roles to new team member",
        created_by=created_by,
        changes=[
            {
                "change_type": "add_role",
                "target_user": "jsmith",
                "role_id": "SAP_FI_ACCOUNTANT",
                "role_name": "Finance Accountant",
                "justification": "New hire in Finance department"
            },
            {
                "change_type": "add_role",
                "target_user": "jsmith",
                "role_id": "SAP_FI_REPORTER",
                "role_name": "Finance Reporter",
                "justification": "Needs reporting access"
            }
        ]
    )

    # Add test scenarios
    pts_simulator.add_test_scenario(
        scenario.scenario_id,
        "Test journal entry creation",
        "jsmith",
        "FB01",
        "success"
    )

    pts_simulator.add_test_scenario(
        scenario.scenario_id,
        "Test financial report access",
        "jsmith",
        "F.01",
        "success"
    )

    # Run simulation
    result = pts_simulator.run_simulation(scenario.scenario_id)

    return {
        "status": "success",
        "scenario_id": scenario.scenario_id,
        "simulation_id": result.simulation_id,
        "result": result.to_dict()
    }
