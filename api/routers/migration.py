"""
Migration Analyzer API Router

Provides endpoints for SAP security consultants to analyze the security
impact of migrating from SAP ECC 6.0 to S/4HANA.

Covers:
- Transaction code mapping and obsolescence
- Authorization object delta analysis
- Role-by-role migration readiness scoring
- User impact assessment
- Phased migration plan generation
- Fiori app catalog and requirements
- Migration simulation for selected roles
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any

from core.migration.analyzer import (
    MigrationAnalyzer,
    MigrationRisk,
    MigrationStatus,
    RoleMigrationAssessment,
)

router = APIRouter(tags=["Migration Analyzer"])

# Single shared analyzer instance (knowledge base is read-only)
_analyzer = MigrationAnalyzer()


# =============================================================================
# Request / Response Models
# =============================================================================

class RoleInput(BaseModel):
    """Describes an ECC role submitted for migration assessment."""
    role_id: str = Field(..., description="Technical role name (e.g. Z_FI_AP_CLERK)")
    role_name: str = Field(..., description="Human-readable role description")
    tcodes: List[str] = Field(default_factory=list, description="ECC transaction codes in this role")
    auth_objects: List[str] = Field(default_factory=list, description="Authorization object names in this role")


class UserInput(BaseModel):
    """Describes an ECC user for impact analysis."""
    user_id: str = Field(..., description="SAP user ID")
    user_name: str = Field(..., description="Full name of the user")
    roles: List[str] = Field(default_factory=list, description="Role IDs assigned to this user")
    department: str = Field(default="Unknown", description="Organizational department")


class SimulationRequest(BaseModel):
    """Request body for migration simulation."""
    roles: List[RoleInput] = Field(..., description="Roles to simulate migration for")
    users: List[UserInput] = Field(default_factory=list, description="Users in scope")
    include_plan: bool = Field(default=True, description="Include migration plan in response")


class UserImpactRequest(BaseModel):
    """Request body for user impact analysis with pre-assessed roles."""
    users: List[UserInput]
    role_assessments: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Pre-computed role assessments keyed by role_id. "
                    "If omitted, heuristic impact detection is used."
    )


# =============================================================================
# Endpoints
# =============================================================================

@router.get(
    "/overview",
    summary="Migration readiness dashboard",
    description=(
        "Returns aggregate statistics and knowledge base coverage for the Migration Analyzer. "
        "Suitable as a dashboard entry point for SAP consultants."
    ),
)
def get_overview():
    """
    High-level overview of the migration analyzer knowledge base and readiness metrics.

    Returns counts of mapped transactions, Fiori apps, auth object changes,
    simplification items and the list of business processes covered.
    """
    stats = _analyzer.get_overview_stats()
    return {
        "knowledge_base": stats,
        "migration_guide": {
            "critical_simplification_items": [
                si for si in _analyzer.get_simplification_items()
                if si.get("impact") == "critical"
            ],
            "top_risk_areas": [
                "Business Partner (BP) replaces FK01 / XK01 / FD01 / VD01",
                "Universal Journal (ACDOCA) replaces BSEG / BSAD / BSAK / BSIS",
                "Fiori apps require new S_FIORI_APP authorization object",
                "New Asset Accounting (FI-AA) is mandatory in S/4HANA",
                "Material Ledger is mandatory in S/4HANA",
                "Logistics Information System (LIS) reports are obsolete",
            ],
        },
        "version": "S/4HANA 2023",
    }


@router.get(
    "/transactions/mapping",
    summary="Full ECC to S/4HANA transaction mapping",
    description=(
        "Returns the complete knowledge base of ECC transaction code mappings "
        "to their S/4HANA equivalents, Fiori apps or obsolescence status."
    ),
)
def get_transaction_mapping(
    business_process: Optional[str] = Query(
        None,
        description="Filter by business process (Finance, Procurement, Sales, etc.)"
    ),
    status: Optional[str] = Query(
        None,
        description="Filter by migration status: compatible, replaced, fiori_only, obsolete, changed, new"
    ),
    risk: Optional[str] = Query(
        None,
        description="Filter by risk level: low, medium, high, critical"
    ),
):
    """
    Returns ECC transaction codes with their S/4HANA equivalents, Fiori app IDs,
    migration status and notes. Optionally filter by business process, status or risk.
    """
    mappings = _analyzer.get_all_transaction_mappings()

    if business_process:
        mappings = [m for m in mappings
                    if m.get("business_process", "").lower() == business_process.lower()]

    if status:
        try:
            MigrationStatus(status)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status '{status}'. Valid values: "
                       f"{[s.value for s in MigrationStatus]}"
            )
        mappings = [m for m in mappings if m.get("status") == status]

    if risk:
        try:
            MigrationRisk(risk)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid risk '{risk}'. Valid values: "
                       f"{[r.value for r in MigrationRisk]}"
            )
        mappings = [m for m in mappings if m.get("risk") == risk]

    return {
        "total": len(mappings),
        "filters_applied": {
            "business_process": business_process,
            "status": status,
            "risk": risk,
        },
        "mappings": mappings,
    }


@router.get(
    "/transactions/obsolete",
    summary="Obsolete ECC transactions",
    description=(
        "Returns all ECC transaction codes that are obsolete in S/4HANA "
        "with the reason for obsolescence and related SAP simplification item."
    ),
)
def get_obsolete_transactions(
    business_process: Optional[str] = Query(
        None,
        description="Filter by business process"
    ),
):
    """
    List of ECC transaction codes that no longer exist in S/4HANA.
    Includes reason, simplification item reference and affected business process.
    """
    obsolete = _analyzer.get_obsolete_transactions()

    if business_process:
        obsolete = [o for o in obsolete
                    if o.get("business_process", "").lower() == business_process.lower()]

    return {
        "total": len(obsolete),
        "business_process_filter": business_process,
        "obsolete_transactions": obsolete,
        "note": (
            "Roles containing these transactions must be updated before S/4HANA go-live. "
            "Users will lose GUI access; equivalent functionality is in Fiori or removed."
        ),
    }


@router.get(
    "/roles/{role_id}/assessment",
    summary="Single role migration assessment",
    description=(
        "Perform a full migration readiness assessment for one ECC role. "
        "Supply transaction codes and authorization objects via query parameters."
    ),
)
def assess_role(
    role_id: str,
    role_name: Optional[str] = Query(None, description="Human-readable role name"),
    tcodes: Optional[str] = Query(
        None,
        description="Comma-separated list of ECC transaction codes in this role"
    ),
    auth_objects: Optional[str] = Query(
        None,
        description="Comma-separated list of authorization object names in this role"
    ),
):
    """
    Returns a detailed migration assessment for a single role including:
    - Transaction compatibility breakdown
    - Authorization object delta
    - Readiness score (0-100)
    - Risk rating
    - Recommended actions
    - Effort estimate in person-days
    - Relevant SAP simplification item references
    """
    tcode_list = [t.strip().upper() for t in tcodes.split(",") if t.strip()] if tcodes else []
    auth_list = [a.strip().upper() for a in auth_objects.split(",") if a.strip()] if auth_objects else []

    if not tcode_list and not auth_list:
        raise HTTPException(
            status_code=400,
            detail="Supply at least one tcode or auth_object for assessment. "
                   "Use ?tcodes=FB01,MIRO,VA01&auth_objects=F_BKPF_BUK,M_BEST_BSA"
        )

    assessment = _analyzer.assess_role(
        role_id=role_id,
        role_name=role_name or role_id,
        ecc_tcodes=tcode_list,
        ecc_auth_objects=auth_list,
    )
    return assessment.to_dict()


@router.post(
    "/roles/assessment",
    summary="Batch role migration assessment",
    description=(
        "Submit a list of ECC roles and receive a migration readiness assessment "
        "for each, plus an aggregated summary."
    ),
)
def assess_roles_batch(roles: List[RoleInput]):
    """
    Batch assessment of multiple ECC roles.

    Returns per-role assessments with readiness scores, risk ratings and
    recommended actions, plus an aggregate summary across all roles.
    """
    if not roles:
        raise HTTPException(status_code=400, detail="Supply at least one role for assessment.")

    if len(roles) > 200:
        raise HTTPException(status_code=400, detail="Maximum 200 roles per batch request.")

    assessments: List[RoleMigrationAssessment] = []
    results = []

    for role_input in roles:
        assessment = _analyzer.assess_role(
            role_id=role_input.role_id,
            role_name=role_input.role_name,
            ecc_tcodes=[t.upper() for t in role_input.tcodes],
            ecc_auth_objects=[a.upper() for a in role_input.auth_objects],
        )
        assessments.append(assessment)
        results.append(assessment.to_dict())

    risk_distribution: Dict[str, int] = {r.value: 0 for r in MigrationRisk}
    auto_migrate_count = 0
    for a in assessments:
        risk_distribution[a.risk.value] += 1
        if a.can_auto_migrate:
            auto_migrate_count += 1

    avg_score = sum(a.readiness_score for a in assessments) / len(assessments)
    total_effort = sum(a.estimated_effort_days for a in assessments)

    return {
        "total_roles": len(assessments),
        "summary": {
            "average_readiness_score": round(avg_score, 1),
            "total_estimated_effort_days": round(total_effort, 2),
            "risk_distribution": risk_distribution,
            "roles_eligible_for_auto_migration": auto_migrate_count,
            "roles_requiring_manual_work": len(assessments) - auto_migrate_count,
        },
        "assessments": results,
    }


@router.post(
    "/user-impact",
    summary="User impact analysis",
    description=(
        "Analyze how many users will be affected by the migration, "
        "which users will lose access and which need new roles or Fiori training."
    ),
)
def analyze_user_impact(body: UserImpactRequest):
    """
    User impact report for the S/4HANA migration.

    Accepts a list of users (with their current role assignments) and
    optionally pre-computed role assessments. Returns per-user impact
    details and an aggregated summary by department.
    """
    users_as_dicts = [u.dict() for u in body.users]

    # Rebuild role assessments from dict payload if provided
    role_map: Optional[Dict[str, RoleMigrationAssessment]] = None
    if body.role_assessments:
        # Accept pre-computed assessments from the batch endpoint
        # Here we only need the structured fields used by analyze_user_impact
        role_map = {}
        for role_id, data in body.role_assessments.items():
            try:
                # Re-assess using data fields to produce a typed object
                assessment = _analyzer.assess_role(
                    role_id=data.get("role_id", role_id),
                    role_name=data.get("role_name", role_id),
                    ecc_tcodes=data.get("tcodes", []),
                    ecc_auth_objects=data.get("auth_objects", []),
                )
                role_map[role_id] = assessment
            except Exception:
                continue

    report = _analyzer.analyze_user_impact(
        users=users_as_dicts,
        role_assessments=role_map,
    )
    return report.to_dict()


@router.post(
    "/plan",
    summary="Generate migration plan",
    description=(
        "Generate a phased, prioritized migration plan from a set of role assessments. "
        "Returns a 5-phase plan with tasks, effort estimates, critical path and risk register."
    ),
)
def generate_migration_plan(
    roles: List[RoleInput],
    total_users: int = Query(0, description="Total number of end users in scope"),
):
    """
    Produces a complete, phased migration project plan including:

    - Phase 1: Preparation (inventory, BP assessment, Fiori design)
    - Phase 2: Design (role redesign, auth object mapping)
    - Phase 3: Build (role build, Fiori config, BP migration)
    - Phase 4: Test (regression, SoD re-validation, Fiori testing)
    - Phase 5: Go-live (training, transport, post-go-live review)

    Each phase contains prioritized tasks with effort estimates,
    dependencies and risk ratings.
    """
    if not roles:
        raise HTTPException(status_code=400, detail="Supply at least one role to generate a plan.")

    assessments: List[RoleMigrationAssessment] = []
    for role_input in roles:
        assessment = _analyzer.assess_role(
            role_id=role_input.role_id,
            role_name=role_input.role_name,
            ecc_tcodes=[t.upper() for t in role_input.tcodes],
            ecc_auth_objects=[a.upper() for a in role_input.auth_objects],
        )
        assessments.append(assessment)

    plan = _analyzer.generate_plan(assessments, total_users=total_users)
    return plan.to_dict()


@router.post(
    "/simulate",
    summary="Simulate migration for selected roles",
    description=(
        "Run a complete migration simulation: assess all provided roles, "
        "compute user impact and optionally generate a migration plan. "
        "Use this for a comprehensive pre-migration health check."
    ),
)
def simulate_migration(body: SimulationRequest):
    """
    End-to-end migration simulation for a set of roles and users.

    Steps performed:
    1. Assess each role for migration readiness.
    2. Analyze user impact using the role assessments.
    3. Optionally generate a phased migration plan.

    Returns a consolidated report suitable for executive presentation
    or export to project management tools.
    """
    if not body.roles:
        raise HTTPException(status_code=400, detail="Supply at least one role for simulation.")

    if len(body.roles) > 200:
        raise HTTPException(status_code=400, detail="Maximum 200 roles per simulation.")

    # Step 1: Assess roles
    assessments: List[RoleMigrationAssessment] = []
    for role_input in body.roles:
        assessment = _analyzer.assess_role(
            role_id=role_input.role_id,
            role_name=role_input.role_name,
            ecc_tcodes=[t.upper() for t in role_input.tcodes],
            ecc_auth_objects=[a.upper() for a in role_input.auth_objects],
        )
        assessments.append(assessment)

    role_map = {a.role_id: a for a in assessments}

    risk_distribution: Dict[str, int] = {r.value: 0 for r in MigrationRisk}
    for a in assessments:
        risk_distribution[a.risk.value] += 1

    avg_score = sum(a.readiness_score for a in assessments) / len(assessments)
    total_effort = sum(a.estimated_effort_days for a in assessments)
    auto_migrate = [a.role_id for a in assessments if a.can_auto_migrate]
    manual_needed = [a.role_id for a in assessments if not a.can_auto_migrate]

    # Collect all unique Fiori apps required across all roles
    all_fiori: set = set()
    for a in assessments:
        all_fiori.update(a.transaction_impact.required_fiori_apps)

    # Step 2: User impact
    users_as_dicts = [u.dict() for u in body.users]
    user_report = _analyzer.analyze_user_impact(
        users=users_as_dicts,
        role_assessments=role_map,
    )

    # Step 3: Migration plan (optional)
    plan_data: Optional[dict] = None
    if body.include_plan:
        plan = _analyzer.generate_plan(assessments, total_users=len(body.users))
        plan_data = plan.to_dict()

    return {
        "simulation_summary": {
            "total_roles_analyzed": len(assessments),
            "total_users_in_scope": len(body.users),
            "average_readiness_score": round(avg_score, 1),
            "total_estimated_effort_days": round(total_effort, 2),
            "risk_distribution": risk_distribution,
            "roles_eligible_for_auto_migration": auto_migrate,
            "roles_requiring_manual_work": manual_needed,
            "required_fiori_apps": sorted(all_fiori),
        },
        "role_assessments": [a.to_dict() for a in assessments],
        "user_impact": user_report.to_dict(),
        "migration_plan": plan_data,
    }


@router.get(
    "/fiori-requirements",
    summary="Fiori app catalog and requirements",
    description=(
        "Returns the full Fiori app catalog with app IDs, names, catalogs, "
        "semantic objects, required authorization objects and the ECC tcodes they replace."
    ),
)
def get_fiori_requirements(
    replaces_tcode: Optional[str] = Query(
        None,
        description="Filter: return only apps that replace this ECC tcode (e.g. MIRO)"
    ),
    business_process: Optional[str] = Query(
        None,
        description="Filter by business process (Finance, Procurement, Sales, etc.)"
    ),
):
    """
    Fiori app catalog for S/4HANA migration planning.

    Each entry includes the Fiori app ID, name, semantic object/action,
    the Fiori catalog it belongs to, the ECC tcodes it replaces and
    the authorization objects required to run the app.

    Use this endpoint to determine what Fiori authorizations (S_FIORI_APP)
    must be added to roles that currently contain classic GUI tcodes.
    """
    apps = _analyzer.get_fiori_apps()

    if replaces_tcode:
        tcode_upper = replaces_tcode.upper()
        apps = [a for a in apps if tcode_upper in a.get("replaces_tcodes", [])]

    if business_process:
        apps = [a for a in apps
                if a.get("business_process", "").lower() == business_process.lower()]

    return {
        "total": len(apps),
        "filters_applied": {
            "replaces_tcode": replaces_tcode,
            "business_process": business_process,
        },
        "fiori_apps": apps,
        "notes": [
            "All Fiori users require S_FIORI_APP authorization object with the app ID.",
            "Backend OData services require S_START authorization object.",
            "Fiori catalogs must be assigned to PFCG roles via the Fiori Launchpad designer.",
        ],
    }


@router.get(
    "/auth-changes",
    summary="Authorization object changes between ECC and S/4HANA",
    description=(
        "Returns all known authorization object changes including new objects, "
        "deprecated objects and objects with changed behavior in S/4HANA."
    ),
)
def get_auth_changes(
    change_type: Optional[str] = Query(
        None,
        description="Filter by change type: new, deprecated, changed, renamed"
    ),
    business_process: Optional[str] = Query(
        None,
        description="Filter by business process"
    ),
):
    """
    Authorization object delta between ECC 6.0 and S/4HANA.

    Use this to identify which auth objects must be added, removed or
    reconfigured in your S/4HANA roles. Critical for security architects
    designing the target authorization concept.
    """
    changes = _analyzer.get_auth_object_changes()

    if change_type:
        changes = [c for c in changes if c.get("change_type") == change_type]

    if business_process:
        changes = [c for c in changes
                   if c.get("business_process", "").lower() == business_process.lower()]

    counts: Dict[str, int] = {}
    for c in changes:
        ct = c.get("change_type", "unknown")
        counts[ct] = counts.get(ct, 0) + 1

    return {
        "total": len(changes),
        "by_change_type": counts,
        "filters_applied": {
            "change_type": change_type,
            "business_process": business_process,
        },
        "auth_object_changes": changes,
    }


@router.get(
    "/simplification-items",
    summary="SAP simplification list items",
    description=(
        "Returns the SAP simplification list items most relevant to "
        "security and authorization migration from ECC to S/4HANA."
    ),
)
def get_simplification_items(
    impact: Optional[str] = Query(
        None,
        description="Filter by impact level: critical, high, medium, low"
    ),
):
    """
    Relevant SAP simplification list entries that affect security authorizations.

    Each entry includes the simplification item ID, title, description,
    impact rating and the affected ECC transaction codes.
    Consult these during the Preparation phase of the migration project.
    """
    items = _analyzer.get_simplification_items()

    if impact:
        items = [i for i in items if i.get("impact") == impact]

    return {
        "total": len(items),
        "impact_filter": impact,
        "simplification_items": items,
        "reference": "SAP Simplification Item Catalog for SAP S/4HANA",
    }
