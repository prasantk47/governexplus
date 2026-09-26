"""
Upgrade Impact Analyzer API Router

Exposes endpoints for analyzing the security impact of SAP version upgrades.

Covers deprecated authorization objects, new requirements, simplification items,
affected roles, simulation, and remediation planning.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

from core.upgrade.analyzer import (
    UpgradeImpactAnalyzer,
    UpgradeImpact,
    AffectedRole,
    DeprecatedObject,
    NewRequirement,
    SimplificationItem,
    UpgradeSimulation,
    RemediationPlan,
    RemediationTask,
    ImpactSeverity,
    ChangeType,
    SUPPORTED_VERSION_PAIRS,
)

router = APIRouter(tags=["Upgrade Impact Analyzer"])

_analyzer = UpgradeImpactAnalyzer()


# ===========================================================================
# Request / Response models
# ===========================================================================

class AnalyzeUpgradeRequest(BaseModel):
    """Request body for a full upgrade impact analysis."""
    from_version: str
    to_version: str


class SimulateUpgradeRequest(BaseModel):
    """Request body for simulating upgrade impact on specific roles."""
    role_ids: List[str]
    from_version: str = "ECC 6.0 EHP8"
    to_version: str = "S/4HANA 2022"


class RemediationPlanRequest(BaseModel):
    """Request body for generating a remediation plan."""
    from_version: str = "ECC 6.0 EHP8"
    to_version: str = "S/4HANA 2022"


class DeprecatedObjectResponse(BaseModel):
    object_name: str
    object_type: str
    deprecated_in: str
    removed_in: Optional[str]
    replacement: Optional[str]
    impact: str
    change_type: str
    description: str
    affected_business_areas: List[str]


class NewRequirementResponse(BaseModel):
    object_name: str
    object_type: str
    introduced_in: str
    mandatory: bool
    description: str
    example_value: str
    related_fiori_apps: List[str]
    affected_business_areas: List[str]
    impact: str


class SimplificationItemResponse(BaseModel):
    item_id: str
    title: str
    description: str
    affected_version: str
    change_type: str
    impact: str
    action_required: str
    affected_objects: List[str]


class AffectedRoleResponse(BaseModel):
    role_id: str
    role_name: str
    role_type: str
    business_area: str
    deprecated_objects_count: int
    new_objects_count: int
    simplification_items_count: int
    overall_impact: str
    requires_redesign: bool
    notes: str


class UpgradeImpactResponse(BaseModel):
    from_version: str
    to_version: str
    analysis_timestamp: str
    total_deprecated_objects: int
    total_new_requirements: int
    total_simplification_items: int
    total_affected_roles: int
    critical_items: int
    deprecated_objects: List[DeprecatedObjectResponse]
    new_requirements: List[NewRequirementResponse]
    simplification_items: List[SimplificationItemResponse]
    affected_roles: List[AffectedRoleResponse]
    executive_summary: str
    estimated_remediation_effort: str


class RoleSimulationResponse(BaseModel):
    role_id: str
    role_name: str
    current_objects: List[str]
    deprecated_in_role: List[str]
    new_required: List[str]
    net_change: int
    impact: str
    action_items: List[str]


class UpgradeSimulationResponse(BaseModel):
    from_version: str
    to_version: str
    simulation_timestamp: str
    role_results: List[RoleSimulationResponse]
    total_deprecated: int
    total_new: int
    roles_requiring_redesign: int
    estimated_effort_hours: float


class RemediationTaskResponse(BaseModel):
    task_id: str
    title: str
    description: str
    action: str
    priority: str
    estimated_hours: float
    affected_roles: List[str]
    objects_involved: List[str]
    prerequisite_tasks: List[str]


class RemediationPlanResponse(BaseModel):
    from_version: str
    to_version: str
    generated_at: str
    total_tasks: int
    total_estimated_hours: float
    phases: Dict[str, List[RemediationTaskResponse]]
    critical_path: List[str]
    notes: List[str]


# ===========================================================================
# Serialization helpers
# ===========================================================================

def _serialize_deprecated(obj: DeprecatedObject) -> DeprecatedObjectResponse:
    return DeprecatedObjectResponse(
        object_name=obj.object_name,
        object_type=obj.object_type,
        deprecated_in=obj.deprecated_in,
        removed_in=obj.removed_in,
        replacement=obj.replacement,
        impact=obj.impact.value,
        change_type=obj.change_type.value,
        description=obj.description,
        affected_business_areas=obj.affected_business_areas,
    )


def _serialize_new_req(req: NewRequirement) -> NewRequirementResponse:
    return NewRequirementResponse(
        object_name=req.object_name,
        object_type=req.object_type,
        introduced_in=req.introduced_in,
        mandatory=req.mandatory,
        description=req.description,
        example_value=req.example_value,
        related_fiori_apps=req.related_fiori_apps,
        affected_business_areas=req.affected_business_areas,
        impact=req.impact.value,
    )


def _serialize_simp(item: SimplificationItem) -> SimplificationItemResponse:
    return SimplificationItemResponse(
        item_id=item.item_id,
        title=item.title,
        description=item.description,
        affected_version=item.affected_version,
        change_type=item.change_type.value,
        impact=item.impact.value,
        action_required=item.action_required,
        affected_objects=item.affected_objects,
    )


def _serialize_role(role: AffectedRole) -> AffectedRoleResponse:
    return AffectedRoleResponse(
        role_id=role.role_id,
        role_name=role.role_name,
        role_type=role.role_type,
        business_area=role.business_area,
        deprecated_objects_count=role.deprecated_objects_count,
        new_objects_count=role.new_objects_count,
        simplification_items_count=role.simplification_items_count,
        overall_impact=role.overall_impact.value,
        requires_redesign=role.requires_redesign,
        notes=role.notes,
    )


def _serialize_impact(impact: UpgradeImpact) -> UpgradeImpactResponse:
    return UpgradeImpactResponse(
        from_version=impact.from_version,
        to_version=impact.to_version,
        analysis_timestamp=impact.analysis_timestamp,
        total_deprecated_objects=impact.total_deprecated_objects,
        total_new_requirements=impact.total_new_requirements,
        total_simplification_items=impact.total_simplification_items,
        total_affected_roles=impact.total_affected_roles,
        critical_items=impact.critical_items,
        deprecated_objects=[_serialize_deprecated(d) for d in impact.deprecated_objects],
        new_requirements=[_serialize_new_req(n) for n in impact.new_requirements],
        simplification_items=[_serialize_simp(s) for s in impact.simplification_items],
        affected_roles=[_serialize_role(r) for r in impact.affected_roles],
        executive_summary=impact.executive_summary,
        estimated_remediation_effort=impact.estimated_remediation_effort,
    )


def _serialize_simulation(sim: UpgradeSimulation) -> UpgradeSimulationResponse:
    return UpgradeSimulationResponse(
        from_version=sim.from_version,
        to_version=sim.to_version,
        simulation_timestamp=sim.simulation_timestamp,
        role_results=[
            RoleSimulationResponse(
                role_id=r.role_id,
                role_name=r.role_name,
                current_objects=r.current_objects,
                deprecated_in_role=r.deprecated_in_role,
                new_required=r.new_required,
                net_change=r.net_change,
                impact=r.impact.value,
                action_items=r.action_items,
            )
            for r in sim.role_results
        ],
        total_deprecated=sim.total_deprecated,
        total_new=sim.total_new,
        roles_requiring_redesign=sim.roles_requiring_redesign,
        estimated_effort_hours=sim.estimated_effort_hours,
    )


def _serialize_plan(plan: RemediationPlan) -> RemediationPlanResponse:
    serialized_phases: Dict[str, List[RemediationTaskResponse]] = {}
    for phase_name, tasks in plan.phases.items():
        serialized_phases[phase_name] = [
            RemediationTaskResponse(
                task_id=t.task_id,
                title=t.title,
                description=t.description,
                action=t.action.value,
                priority=t.priority.value,
                estimated_hours=t.estimated_hours,
                affected_roles=t.affected_roles,
                objects_involved=t.objects_involved,
                prerequisite_tasks=t.prerequisite_tasks,
            )
            for t in tasks
        ]
    return RemediationPlanResponse(
        from_version=plan.from_version,
        to_version=plan.to_version,
        generated_at=plan.generated_at,
        total_tasks=plan.total_tasks,
        total_estimated_hours=plan.total_estimated_hours,
        phases=serialized_phases,
        critical_path=plan.critical_path,
        notes=plan.notes,
    )


# ===========================================================================
# Endpoints
# ===========================================================================

@router.get(
    "/versions",
    summary="List supported upgrade version pairs",
    description=(
        "Returns all supported SAP version upgrade paths (ECC 6.0 EHP7/8 to "
        "S/4HANA releases, and S/4HANA release-to-release upgrades)."
    ),
)
def list_versions():
    return _analyzer.get_supported_versions()


@router.post(
    "/analyze",
    response_model=UpgradeImpactResponse,
    summary="Run upgrade impact analysis",
    description=(
        "Performs a full security and authorization impact analysis for the "
        "specified upgrade path. Returns deprecated objects, new requirements, "
        "simplification items, affected roles, and an executive summary."
    ),
)
def analyze_upgrade(request: AnalyzeUpgradeRequest):
    try:
        impact = _analyzer.analyze_upgrade(request.from_version, request.to_version)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return _serialize_impact(impact)


@router.get(
    "/affected-roles",
    response_model=List[AffectedRoleResponse],
    summary="Get affected roles",
    description=(
        "Returns all business roles expected to be impacted by a standard "
        "ECC to S/4HANA upgrade, with impact severity and redesign flags."
    ),
)
def get_affected_roles():
    roles = _analyzer.get_affected_roles()
    return [_serialize_role(r) for r in roles]


@router.get(
    "/deprecated/{version}",
    response_model=List[DeprecatedObjectResponse],
    summary="Get deprecated objects for version",
    description=(
        "Returns all deprecated authorization objects and transactions up to "
        "and including the specified target version. "
        "Valid versions: S/4HANA 1909, S/4HANA 2020, S/4HANA 2021, "
        "S/4HANA 2022, S/4HANA 2023."
    ),
)
def get_deprecated(version: str):
    deprecated = _analyzer.get_deprecated_objects(version)
    return [_serialize_deprecated(d) for d in deprecated]


@router.get(
    "/new-requirements/{version}",
    response_model=List[NewRequirementResponse],
    summary="Get new authorization requirements for version",
    description=(
        "Returns all new authorization requirements introduced up to and "
        "including the specified target S/4HANA version."
    ),
)
def get_new_requirements(version: str):
    reqs = _analyzer.get_new_requirements(version)
    return [_serialize_new_req(r) for r in reqs]


@router.post(
    "/simulate",
    response_model=UpgradeSimulationResponse,
    summary="Simulate upgrade for selected roles",
    description=(
        "Simulates the upgrade impact for a specific list of role IDs. "
        "Returns per-role deprecated objects, new requirements, and effort estimates."
    ),
)
def simulate_upgrade(request: SimulateUpgradeRequest):
    if not request.role_ids:
        raise HTTPException(
            status_code=400,
            detail="role_ids must contain at least one role ID.",
        )
    try:
        sim = _analyzer.simulate_upgrade(
            request.role_ids, request.from_version, request.to_version
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return _serialize_simulation(sim)


@router.get(
    "/remediation-plan",
    response_model=RemediationPlanResponse,
    summary="Get remediation plan",
    description=(
        "Generates a phased, task-level remediation plan for upgrading from "
        "ECC to S/4HANA. Covers 5 phases: Assessment, Design, Build, Test, Cutover. "
        "Use query parameters from_version and to_version to customize the plan."
    ),
)
def get_remediation_plan(
    from_version: str = Query(default="ECC 6.0 EHP8", description="Source version"),
    to_version: str = Query(default="S/4HANA 2022", description="Target version"),
):
    plan = _analyzer.generate_remediation_plan(from_version, to_version)
    return _serialize_plan(plan)
