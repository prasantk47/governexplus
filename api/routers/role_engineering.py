"""
Role Engineering API Router

Endpoints for role design, business roles, and role analysis.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

from core.role_engineering import (
    RoleDesigner, RoleType, RoleStatus, Permission, PermissionType,
    BusinessRoleManager, BusinessRoleStatus, ApprovalRequirement,
    RoleAnalyzer
)

router = APIRouter(tags=["Role Engineering"])

# Initialize components
role_designer = RoleDesigner()
business_role_manager = BusinessRoleManager()
role_analyzer = RoleAnalyzer(role_designer)


# =============================================================================
# Request Models
# =============================================================================

class CreateRoleRequest(BaseModel):
    name: str = Field(..., min_length=3)
    description: str = Field(..., min_length=10)
    role_type: str = Field(default="single")
    template_id: Optional[str] = None
    business_process: Optional[str] = None
    department: Optional[str] = None
    owner: Optional[str] = None


class AddPermissionRequest(BaseModel):
    auth_object: str
    field_values: Dict[str, List[str]] = Field(default_factory=dict)
    transaction_codes: List[str] = Field(default_factory=list)
    description: str = ""
    is_critical: bool = False
    risk_level: str = "low"


class CreateCompositeRoleRequest(BaseModel):
    name: str
    description: str
    child_role_ids: List[str]


class CreateDerivedRoleRequest(BaseModel):
    name: str
    parent_role_id: str
    org_level_values: Dict[str, List[str]]


class CreateBusinessRoleRequest(BaseModel):
    name: str = Field(..., min_length=3)
    description: str
    business_process: str
    department: str
    job_function: Optional[str] = None
    job_titles: List[str] = Field(default_factory=list)
    risk_level: str = "low"


class AddTechnicalMappingRequest(BaseModel):
    technical_role_id: str
    system_id: str = "SAP_ECC"
    is_required: bool = True
    condition: str = ""
    org_level_template: Dict[str, str] = Field(default_factory=dict)


class AssignBusinessRoleRequest(BaseModel):
    user_id: str
    valid_from: Optional[datetime] = None
    valid_to: Optional[datetime] = None
    org_level_values: Dict[str, List[str]] = Field(default_factory=dict)


class CompareRolesRequest(BaseModel):
    role_a_id: str
    role_b_id: str
    role_a_data: Optional[Dict] = None
    role_b_data: Optional[Dict] = None


class AnalyzeUserSodRequest(BaseModel):
    user_roles: List[str]


class GapAnalysisRequest(BaseModel):
    required_transactions: List[str]
    current_roles: List[str]


# =============================================================================
# Role Designer Endpoints
# =============================================================================

@router.post("/roles")
async def create_role(
    request: CreateRoleRequest,
    created_by: str = Query(...)
):
    """Create a new role"""
    try:
        role_type = RoleType(request.role_type)
    except ValueError:
        role_type = RoleType.SINGLE

    role = role_designer.create_role(
        name=request.name,
        description=request.description,
        role_type=role_type,
        created_by=created_by,
        template_id=request.template_id,
        business_process=request.business_process or "",
        department=request.department or "",
        owner=request.owner or ""
    )

    return role.to_dict()


@router.get("/roles")
async def list_roles(
    status: Optional[str] = Query(None),
    role_type: Optional[str] = Query(None),
    department: Optional[str] = Query(None),
    owner: Optional[str] = Query(None),
    search: Optional[str] = Query(None)
):
    """List roles with filters"""
    status_enum = RoleStatus(status) if status else None
    type_enum = RoleType(role_type) if role_type else None

    roles = role_designer.list_roles(
        status=status_enum,
        role_type=type_enum,
        department=department,
        owner=owner,
        search=search
    )

    return {
        "total": len(roles),
        "roles": [r.to_dict() for r in roles]
    }


@router.get("/roles/{role_id}")
async def get_role(role_id: str):
    """Get a role by ID"""
    role = role_designer.get_role(role_id)
    if not role:
        raise HTTPException(status_code=404, detail=f"Role {role_id} not found")
    return role.to_dict()


@router.post("/roles/{role_id}/permissions")
async def add_permission(
    role_id: str,
    request: AddPermissionRequest,
    modified_by: str = Query(...)
):
    """Add a permission to a role"""
    try:
        permission = Permission(
            permission_type=PermissionType.AUTHORIZATION,
            auth_object=request.auth_object,
            field_values=request.field_values,
            transaction_codes=request.transaction_codes,
            description=request.description,
            is_critical=request.is_critical,
            risk_level=request.risk_level
        )

        role = role_designer.add_permission(role_id, permission, modified_by)
        return role.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/roles/{role_id}/transactions")
async def add_transaction(
    role_id: str,
    transaction_code: str = Query(...),
    modified_by: str = Query(...)
):
    """Add a transaction code to a role"""
    try:
        role = role_designer.add_transaction(role_id, transaction_code, modified_by)
        return role.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/roles/{role_id}/permissions/{permission_id}")
async def remove_permission(
    role_id: str,
    permission_id: str,
    modified_by: str = Query(...)
):
    """Remove a permission from a role"""
    try:
        role = role_designer.remove_permission(role_id, permission_id, modified_by)
        return role.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/roles/composite")
async def create_composite_role(
    request: CreateCompositeRoleRequest,
    created_by: str = Query(...)
):
    """Create a composite role"""
    try:
        role = role_designer.create_composite_role(
            name=request.name,
            description=request.description,
            child_role_ids=request.child_role_ids,
            created_by=created_by
        )
        return role.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/roles/derived")
async def create_derived_role(
    request: CreateDerivedRoleRequest,
    created_by: str = Query(...)
):
    """Create a derived role"""
    try:
        role = role_designer.create_derived_role(
            name=request.name,
            parent_role_id=request.parent_role_id,
            org_level_values=request.org_level_values,
            created_by=created_by
        )
        return role.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/roles/{role_id}/test")
async def test_role(
    role_id: str,
    test_types: List[str] = Query(default=["sod_check", "permission_analysis", "naming_check", "completeness"])
):
    """Run tests on a role"""
    try:
        results = role_designer.test_role(role_id, test_types)
        return {
            "role_id": role_id,
            "tests_run": len(results),
            "all_passed": all(r.passed for r in results),
            "results": [r.to_dict() for r in results]
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/roles/{role_id}/simulate")
async def simulate_user_access(
    role_id: str,
    user_id: str = Query(...),
    existing_roles: List[str] = Query(default=[])
):
    """Simulate what access a user would have with this role"""
    try:
        result = role_designer.simulate_user_access(role_id, user_id, existing_roles)
        return result.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/roles/{role_id}/versions")
async def create_version(
    role_id: str,
    change_summary: str = Query(...),
    modified_by: str = Query(...)
):
    """Create a new version of a role"""
    try:
        version = role_designer.create_version(role_id, change_summary, modified_by)
        return version.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/roles/{role_id}/versions/compare")
async def compare_versions(
    role_id: str,
    version_a: int = Query(...),
    version_b: int = Query(...)
):
    """Compare two versions of a role"""
    try:
        return role_designer.compare_versions(role_id, version_a, version_b)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/roles/{role_id}/submit")
async def submit_for_review(
    role_id: str,
    submitted_by: str = Query(...)
):
    """Submit role for approval review"""
    try:
        role = role_designer.submit_for_review(role_id, submitted_by)
        return role.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/roles/{role_id}/approve")
async def approve_role(
    role_id: str,
    approved_by: str = Query(...)
):
    """Approve a role"""
    try:
        role = role_designer.approve_role(role_id, approved_by)
        return role.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/roles/{role_id}/activate")
async def activate_role(
    role_id: str,
    activated_by: str = Query(...)
):
    """Activate a role"""
    try:
        role = role_designer.activate_role(role_id, activated_by)
        return role.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/roles/{role_id}/documentation")
async def get_role_documentation(role_id: str):
    """Generate documentation for a role"""
    try:
        doc = role_designer.generate_documentation(role_id)
        return {"role_id": role_id, "documentation": doc}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/roles/templates")
async def list_templates():
    """List available role templates"""
    templates = role_designer.get_templates()
    return {
        "total": len(templates),
        "templates": [t.to_dict() for t in templates]
    }


@router.post("/roles/validate-name")
async def validate_role_name(
    role_id: str = Query(...),
    role_type: str = Query(default="single")
):
    """Validate role name against conventions"""
    try:
        type_enum = RoleType(role_type)
    except ValueError:
        type_enum = RoleType.SINGLE

    return role_designer.validate_role_name(role_id, type_enum)


@router.get("/roles/suggest-name")
async def suggest_role_name(
    description: str = Query(...),
    role_type: str = Query(default="single"),
    department: str = Query(default="")
):
    """Suggest a role name based on description"""
    try:
        type_enum = RoleType(role_type)
    except ValueError:
        type_enum = RoleType.SINGLE

    suggestion = role_designer.suggest_role_name(description, type_enum, department)
    return {"suggested_name": suggestion}


# =============================================================================
# Business Role Endpoints
# =============================================================================

@router.post("/business-roles")
async def create_business_role(
    request: CreateBusinessRoleRequest,
    created_by: str = Query(...)
):
    """Create a new business role"""
    role = business_role_manager.create_business_role(
        name=request.name,
        description=request.description,
        business_process=request.business_process,
        department=request.department,
        created_by=created_by,
        job_function=request.job_function or "",
        job_titles=request.job_titles,
        risk_level=request.risk_level
    )
    return role.to_dict()


@router.get("/business-roles")
async def list_business_roles(
    status: Optional[str] = Query(None),
    department: Optional[str] = Query(None),
    business_process: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    search: Optional[str] = Query(None)
):
    """List business roles with filters"""
    status_enum = BusinessRoleStatus(status) if status else None

    roles = business_role_manager.list_business_roles(
        status=status_enum,
        department=department,
        business_process=business_process,
        category=category,
        search=search
    )

    return {
        "total": len(roles),
        "roles": [r.to_dict() for r in roles]
    }


@router.get("/business-roles/{role_id}")
async def get_business_role(role_id: str):
    """Get a business role by ID"""
    role = business_role_manager.get_business_role(role_id)
    if not role:
        raise HTTPException(status_code=404, detail=f"Business role {role_id} not found")
    return role.to_dict()


@router.post("/business-roles/{role_id}/technical-mappings")
async def add_technical_mapping(
    role_id: str,
    request: AddTechnicalMappingRequest,
    modified_by: str = Query(...)
):
    """Add a technical role mapping"""
    try:
        role = business_role_manager.add_technical_mapping(
            role_id=role_id,
            technical_role_id=request.technical_role_id,
            system_id=request.system_id,
            is_required=request.is_required,
            condition=request.condition,
            org_level_template=request.org_level_template,
            modified_by=modified_by
        )
        return role.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/business-roles/{role_id}/technical-roles")
async def get_technical_roles(
    role_id: str,
    org_level_values: Optional[str] = Query(None)
):
    """Get resolved technical roles for a business role"""
    try:
        org_levels = {}
        if org_level_values:
            import json
            org_levels = json.loads(org_level_values)

        technical_roles = business_role_manager.get_technical_roles_for_business_role(
            role_id, org_levels
        )
        return {"role_id": role_id, "technical_roles": technical_roles}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/business-roles/{role_id}/assign")
async def assign_business_role(
    role_id: str,
    request: AssignBusinessRoleRequest,
    assigned_by: str = Query(...)
):
    """Assign a business role to a user"""
    try:
        assignment = business_role_manager.assign_role(
            role_id=role_id,
            user_id=request.user_id,
            assigned_by=assigned_by,
            valid_from=request.valid_from,
            valid_to=request.valid_to,
            org_level_values=request.org_level_values
        )
        return assignment.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/business-roles/user/{user_id}/assignments")
async def get_user_business_roles(
    user_id: str,
    include_expired: bool = Query(default=False)
):
    """Get business role assignments for a user"""
    assignments = business_role_manager.get_user_assignments(user_id, include_expired)
    return {
        "user_id": user_id,
        "total": len(assignments),
        "assignments": [a.to_dict() for a in assignments]
    }


@router.get("/catalog")
async def get_role_catalog(
    category: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    requestable_only: bool = Query(default=True)
):
    """Get the role catalog for self-service"""
    catalog = business_role_manager.get_catalog(category, search, requestable_only)
    return {"total": len(catalog), "roles": catalog}


@router.get("/catalog/categories")
async def get_catalog_categories():
    """Get catalog categories with role counts"""
    return business_role_manager.get_catalog_categories()


@router.get("/business-roles/popular")
async def get_popular_roles(limit: int = Query(default=10, le=50)):
    """Get most popular business roles"""
    return business_role_manager.get_popular_roles(limit)


# =============================================================================
# Role Analysis Endpoints
# =============================================================================

@router.post("/analyze/compare")
async def compare_roles(request: CompareRolesRequest):
    """Compare two roles"""
    try:
        comparison = role_analyzer.compare_roles(
            request.role_a_id,
            request.role_b_id,
            request.role_a_data,
            request.role_b_data
        )
        return comparison.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/analyze/similar/{role_id}")
async def find_similar_roles(
    role_id: str,
    threshold: float = Query(default=70.0, ge=0, le=100)
):
    """Find roles similar to a given role"""
    try:
        similar = role_analyzer.find_similar_roles(role_id, threshold)
        return {"role_id": role_id, "threshold": threshold, "similar_roles": similar}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/analyze/conflicts")
async def detect_conflicts(role_ids: Optional[List[str]] = None):
    """Detect conflicts in roles"""
    try:
        conflicts = role_analyzer.detect_conflicts(role_ids)
        return {
            "conflicts_found": len(conflicts),
            "conflicts": [c.to_dict() for c in conflicts]
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/analyze/user-sod")
async def analyze_user_sod(request: AnalyzeUserSodRequest):
    """Analyze SoD conflicts for a user's combined roles"""
    conflicts = role_analyzer.analyze_user_sod(request.user_roles)
    return {
        "user_roles": request.user_roles,
        "conflicts_found": len(conflicts),
        "conflicts": [c.to_dict() for c in conflicts]
    }


@router.post("/analyze/gaps")
async def analyze_permission_gaps(request: GapAnalysisRequest):
    """Analyze permission gaps"""
    try:
        gaps = role_analyzer.analyze_permission_gaps(
            request.required_transactions,
            request.current_roles
        )
        return {
            "gaps_found": len(gaps),
            "gaps": [g.to_dict() for g in gaps]
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/analyze/optimizations")
async def recommend_optimizations():
    """Get role optimization recommendations"""
    try:
        recommendations = role_analyzer.recommend_optimizations()
        return {
            "recommendations_count": len(recommendations),
            "recommendations": [r.to_dict() for r in recommendations]
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/analyze/role/{role_id}/usage")
async def get_role_usage_report(role_id: str):
    """Get usage report for a role"""
    try:
        return role_analyzer.get_role_usage_report(role_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# =============================================================================
# Statistics
# =============================================================================

@router.get("/statistics")
async def get_role_engineering_statistics():
    """Get combined role engineering statistics"""
    return {
        "role_designer": role_designer.get_statistics(),
        "business_roles": business_role_manager.get_statistics(),
        "analyzer": role_analyzer.get_statistics()
    }
