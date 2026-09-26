# SoD Rules API Router
# Separation of Duties Ruleset Management — Built-in + Custom Rules

from fastapi import APIRouter, HTTPException, Query, Depends, UploadFile, File, Header
from fastapi.responses import Response
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
from datetime import datetime
from sqlalchemy.orm import Session

from core.rules.sod_ruleset import (
    SoDRulesetLibrary, BusinessFunction, SoDRule,
    RiskLevel, BusinessProcess
)
from core.rules.custom_ruleset import CustomRulesetManager
from db.database import get_db

router = APIRouter(prefix="/sod-rules", tags=["SoD Rules"])

# Global engine instance
sod_library = SoDRulesetLibrary()


def _get_tenant_id(x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID")) -> str:
    return x_tenant_id or "tenant_default"


# ==================== Request/Response Models ====================

class RiskAnalysisRequest(BaseModel):
    user_id: str
    transaction_codes: List[str] = []
    auth_objects: List[Dict[str, Any]] = []
    roles: List[str] = []


class BulkEnableRequest(BaseModel):
    rule_ids: List[str]
    enabled: bool


class CustomRuleRequest(BaseModel):
    rule_id: Optional[str] = None
    name: str
    description: str = ""
    rule_type: str = "sod"
    severity: str = "high"
    risk_category: str = "GEN"
    rule_definition: Dict[str, Any] = {}
    business_justification: str = ""
    mitigation_controls: List[str] = []
    recommended_actions: List[str] = []
    applies_to_systems: List[str] = ["*"]
    applies_to_departments: List[str] = ["*"]
    exception_users: List[str] = []
    exception_roles: List[str] = []
    is_enabled: bool = True


class CloneRuleRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    risk_level: Optional[str] = None
    risk_description: Optional[str] = None


class ImportRulesetRequest(BaseModel):
    content: str
    format: str = "yaml"
    mode: str = "merge"  # merge, replace, append


# ==================== Business Functions ====================

@router.get("/functions")
async def list_business_functions(
    business_process: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = Query(default=100, le=500),
    offset: int = 0
):
    """
    List business functions

    Filter by business_process (FI, MM, SD, HR, BASIS) or search.
    """
    functions = sod_library.get_all_functions()

    # Apply filters
    if business_process:
        try:
            bp = BusinessProcess(business_process)
            functions = sod_library.get_functions_by_process(bp)
        except ValueError:
            pass

    if search:
        search_lower = search.lower()
        functions = [
            f for f in functions
            if search_lower in f.name.lower()
            or search_lower in f.description.lower()
            or search_lower in f.function_id.lower()
        ]

    total = len(functions)
    functions = functions[offset:offset + limit]

    return {
        "functions": [f.to_dict() for f in functions],
        "total": total
    }


@router.get("/functions/{function_id}")
async def get_business_function(function_id: str):
    """Get business function details"""
    func = sod_library.get_function(function_id)
    if not func:
        raise HTTPException(status_code=404, detail="Function not found")
    return func.to_dict()


# ==================== SoD Rules ====================

@router.get("/rules")
async def list_sod_rules(
    business_process: Optional[str] = None,
    risk_level: Optional[str] = None,
    sox_relevant: Optional[bool] = None,
    active_only: bool = True,
    search: Optional[str] = None,
    limit: int = Query(default=100, le=500),
    offset: int = 0
):
    """
    List SoD rules

    Filter by business process, risk level, or compliance relevance.
    """
    rules = sod_library.get_all_rules(active_only=active_only)

    # Apply filters
    if business_process:
        try:
            bp = BusinessProcess(business_process)
            rules = sod_library.get_rules_by_process(bp)
        except ValueError:
            pass

    if risk_level:
        try:
            level = RiskLevel(risk_level)
            rules = [r for r in rules if r.risk_level == level]
        except ValueError:
            pass

    if sox_relevant is not None:
        rules = [r for r in rules if r.sox_relevant == sox_relevant]

    if search:
        search_lower = search.lower()
        rules = [
            r for r in rules
            if search_lower in r.name.lower()
            or search_lower in r.description.lower()
            or search_lower in r.rule_id.lower()
        ]

    total = len(rules)
    rules = rules[offset:offset + limit]

    return {
        "rules": [r.to_dict() for r in rules],
        "total": total
    }


@router.get("/rules/{rule_id}")
async def get_sod_rule(rule_id: str):
    """Get SoD rule details"""
    rule = sod_library.get_rule(rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    return rule.to_dict()


@router.get("/rules/sox-relevant")
async def get_sox_relevant_rules():
    """Get all SOX-relevant rules"""
    rules = sod_library.get_sox_relevant_rules()
    return {
        "rules": [r.to_dict() for r in rules],
        "total": len(rules)
    }


@router.get("/rules/gdpr-relevant")
async def get_gdpr_relevant_rules():
    """Get all GDPR-relevant rules"""
    rules = sod_library.get_gdpr_relevant_rules()
    return {
        "rules": [r.to_dict() for r in rules],
        "total": len(rules)
    }


# ==================== Risk Analysis ====================

@router.post("/analyze")
async def analyze_user_access(
    request: RiskAnalysisRequest,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """
    Analyze user access for SoD violations.

    Uses the tenant's effective ruleset (built-in rules filtered by
    tenant preferences + tenant custom rules).
    """
    mgr = CustomRulesetManager(db, tenant_id)
    violations = []
    user_tcodes = set(request.transaction_codes)

    # 1. Check built-in rules (respecting tenant enable/disable)
    builtin_rules = mgr.get_builtin_rules(include_disabled=False)
    for rule_dict in builtin_rules:
        func1 = rule_dict.get("function1", {})
        func2 = rule_dict.get("function2", {})
        func1_tcodes = set(func1.get("transaction_codes", []))
        func2_tcodes = set(func2.get("transaction_codes", []))

        has_func1 = bool(user_tcodes & func1_tcodes)
        has_func2 = bool(user_tcodes & func2_tcodes)

        if has_func1 and has_func2:
            violations.append({
                "rule_id": rule_dict["rule_id"],
                "rule_name": rule_dict["name"],
                "risk_level": rule_dict["risk_level"],
                "source": "builtin",
                "function1": func1.get("name", ""),
                "function2": func2.get("name", ""),
                "conflicting_tcodes_func1": list(user_tcodes & func1_tcodes),
                "conflicting_tcodes_func2": list(user_tcodes & func2_tcodes),
                "risk_description": rule_dict.get("risk_description", ""),
                "business_impact": rule_dict.get("business_impact", ""),
                "recommendation": rule_dict.get("recommendation", ""),
            })

    # 2. Check custom rules
    custom_rules = mgr.get_custom_rules(include_disabled=False)
    for crule in custom_rules:
        defn = crule.get("rule_definition", {})
        func1 = defn.get("function1", {})
        func2 = defn.get("function2", {})
        func1_tcodes = set(func1.get("transaction_codes", []))
        func2_tcodes = set(func2.get("transaction_codes", []))

        has_func1 = bool(user_tcodes & func1_tcodes)
        has_func2 = bool(user_tcodes & func2_tcodes)

        if has_func1 and has_func2:
            violations.append({
                "rule_id": crule["rule_id"],
                "rule_name": crule["name"],
                "risk_level": crule.get("risk_level", "medium"),
                "source": crule.get("source", "custom"),
                "function1": func1.get("name", "Custom Function A"),
                "function2": func2.get("name", "Custom Function B"),
                "conflicting_tcodes_func1": list(user_tcodes & func1_tcodes),
                "conflicting_tcodes_func2": list(user_tcodes & func2_tcodes),
                "risk_description": crule.get("business_justification", ""),
                "business_impact": "",
                "recommendation": (crule.get("recommended_actions") or [""])[0],
            })

    stats = mgr.get_ruleset_stats()

    return {
        "user_id": request.user_id,
        "tenant_id": tenant_id,
        "analysis_date": datetime.utcnow().isoformat(),
        "violations_found": len(violations),
        "violations": violations,
        "risk_summary": {
            "critical": len([v for v in violations if v["risk_level"] == "critical"]),
            "high": len([v for v in violations if v["risk_level"] == "high"]),
            "medium": len([v for v in violations if v["risk_level"] == "medium"]),
            "low": len([v for v in violations if v["risk_level"] == "low"]),
        },
        "ruleset_used": stats,
    }


@router.post("/simulate")
async def simulate_access_change(
    user_id: str,
    current_tcodes: List[str] = [],
    add_tcodes: List[str] = [],
    remove_tcodes: List[str] = []
):
    """
    Simulate access change impact

    Check what new violations would occur with proposed changes.
    """
    # Calculate new access
    current = set(current_tcodes)
    new_access = (current | set(add_tcodes)) - set(remove_tcodes)

    # Analyze current state
    current_request = RiskAnalysisRequest(
        user_id=user_id,
        transaction_codes=list(current)
    )
    current_analysis = await analyze_user_access(current_request)

    # Analyze new state
    new_request = RiskAnalysisRequest(
        user_id=user_id,
        transaction_codes=list(new_access)
    )
    new_analysis = await analyze_user_access(new_request)

    # Find new violations
    current_rule_ids = {v["rule_id"] for v in current_analysis["violations"]}
    new_violations = [
        v for v in new_analysis["violations"]
        if v["rule_id"] not in current_rule_ids
    ]

    # Find resolved violations
    new_rule_ids = {v["rule_id"] for v in new_analysis["violations"]}
    resolved_violations = [
        v for v in current_analysis["violations"]
        if v["rule_id"] not in new_rule_ids
    ]

    return {
        "user_id": user_id,
        "simulation_date": datetime.utcnow().isoformat(),
        "current_violations": current_analysis["violations_found"],
        "projected_violations": new_analysis["violations_found"],
        "new_violations": new_violations,
        "resolved_violations": resolved_violations,
        "net_change": new_analysis["violations_found"] - current_analysis["violations_found"],
        "recommendation": "Approve" if len(new_violations) == 0 else "Review Required"
    }


# ==================== Business Processes ====================

@router.get("/business-processes")
async def list_business_processes():
    """List available business processes"""
    return {
        "processes": [
            {"value": bp.value, "name": bp.name}
            for bp in BusinessProcess
        ],
        "descriptions": {
            "FI": "Financial Accounting",
            "MM": "Materials Management / Procurement",
            "SD": "Sales & Distribution",
            "HR": "Human Resources",
            "BASIS": "Basis/Security Administration",
            "TR": "Treasury",
            "AA": "Asset Accounting",
            "WM": "Warehouse Management",
            "QM": "Quality Management",
            "PM": "Plant Maintenance",
            "PS": "Project System",
            "GEN": "General / Cross-Process"
        }
    }


@router.get("/risk-levels")
async def list_risk_levels():
    """List available risk levels"""
    return {
        "risk_levels": [
            {
                "value": rl.value,
                "name": rl.name,
                "description": {
                    "critical": "Highest priority - potential for fraud or major regulatory violations",
                    "high": "Significant risk - should be remediated or mitigated",
                    "medium": "Moderate risk - review recommended",
                    "low": "Lower priority - monitor as needed"
                }.get(rl.value, "")
            }
            for rl in RiskLevel
        ]
    }


# ==================== Statistics ====================

@router.get("/stats")
async def get_sod_stats():
    """Get SoD ruleset statistics"""
    return sod_library.get_statistics()


@router.get("/coverage")
async def get_coverage_report():
    """Get rule coverage report by business process"""
    coverage = {}
    for bp in BusinessProcess:
        functions = sod_library.get_functions_by_process(bp)
        rules = sod_library.get_rules_by_process(bp)

        coverage[bp.value] = {
            "business_process": bp.name,
            "functions_count": len(functions),
            "rules_count": len(rules),
            "critical_rules": len([r for r in rules if r.risk_level == RiskLevel.CRITICAL]),
            "high_rules": len([r for r in rules if r.risk_level == RiskLevel.HIGH]),
            "sox_relevant": len([r for r in rules if r.sox_relevant])
        }

    return {"coverage": coverage}


# ==================== Export ====================

@router.get("/export")
async def export_ruleset():
    """Export the complete built-in ruleset"""
    functions = sod_library.get_all_functions()
    rules = sod_library.get_all_rules(active_only=False)

    return {
        "version": "1.0",
        "exported_at": datetime.utcnow().isoformat(),
        "statistics": sod_library.get_statistics(),
        "functions": [f.to_dict() for f in functions],
        "rules": [r.to_dict() for r in rules]
    }


# ==========================================================================
# CUSTOM RULESET MANAGEMENT
# Tenants can toggle built-in rules, clone & edit, or create from scratch
# ==========================================================================

@router.get("/effective")
async def get_effective_ruleset(
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """
    Get the effective ruleset for this tenant.
    Combines enabled built-in rules + custom rules.
    """
    mgr = CustomRulesetManager(db, tenant_id)
    rules = mgr.get_effective_ruleset()
    stats = mgr.get_ruleset_stats()
    return {"rules": rules, "stats": stats, "total": len(rules)}


@router.get("/custom")
async def list_custom_rules(
    include_disabled: bool = False,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """List all custom rules for this tenant."""
    mgr = CustomRulesetManager(db, tenant_id)
    rules = mgr.get_custom_rules(include_disabled=include_disabled)
    return {"rules": rules, "total": len(rules)}


@router.post("/custom")
async def create_custom_rule(
    request: CustomRuleRequest,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """
    Create a brand-new custom SoD rule.

    Define your own business functions, transaction codes,
    and conflict definitions specific to your organization.
    """
    mgr = CustomRulesetManager(db, tenant_id)
    return mgr.create_custom_rule(request.model_dump())


@router.put("/custom/{rule_id}")
async def update_custom_rule(
    rule_id: str,
    request: CustomRuleRequest,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Update an existing custom rule."""
    mgr = CustomRulesetManager(db, tenant_id)
    try:
        return mgr.update_custom_rule(rule_id, request.model_dump(exclude_unset=True))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/custom/{rule_id}")
async def delete_custom_rule(
    rule_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """
    Delete a custom rule.
    If it was cloned from a built-in, the original is re-enabled.
    """
    mgr = CustomRulesetManager(db, tenant_id)
    try:
        return mgr.delete_custom_rule(rule_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==================== Built-in Rule Toggle ====================

@router.get("/builtin")
async def list_builtin_rules_with_status(
    include_disabled: bool = True,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """
    List all built-in rules with tenant-specific enable/disable status.
    Shows which rules the tenant has toggled off or cloned.
    """
    mgr = CustomRulesetManager(db, tenant_id)
    rules = mgr.get_builtin_rules(include_disabled=include_disabled)
    return {"rules": rules, "total": len(rules)}


@router.put("/builtin/{rule_id}/toggle")
async def toggle_builtin_rule(
    rule_id: str,
    enabled: bool = True,
    reason: str = "",
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """
    Enable or disable a built-in rule for your organization.
    Disabled rules are skipped during risk analysis.
    """
    mgr = CustomRulesetManager(db, tenant_id)
    try:
        return mgr.toggle_builtin_rule(rule_id, enabled, reason=reason)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/builtin/bulk-toggle")
async def bulk_toggle_builtin_rules(
    request: BulkEnableRequest,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Enable or disable multiple built-in rules at once."""
    mgr = CustomRulesetManager(db, tenant_id)
    return mgr.bulk_toggle_rules(request.rule_ids, request.enabled)


# ==================== Clone & Customize ====================

@router.post("/builtin/{rule_id}/clone")
async def clone_builtin_rule(
    rule_id: str,
    request: CloneRuleRequest = None,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """
    Clone a built-in rule to create your own customizable version.

    - The original built-in rule is automatically disabled
    - A new custom copy is created that you can freely edit
    - Deleting the clone re-enables the original
    """
    mgr = CustomRulesetManager(db, tenant_id)
    mods = request.model_dump(exclude_none=True) if request else {}
    try:
        return mgr.clone_builtin_rule(rule_id, modifications=mods)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ==================== Import / Export Custom Rules ====================

@router.get("/custom/export")
async def export_custom_ruleset(
    format: str = "yaml",
    include_builtins: bool = True,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """
    Export your custom rules and preferences as YAML or JSON.
    Use this to back up your ruleset or transfer to another instance.
    """
    mgr = CustomRulesetManager(db, tenant_id)
    content = mgr.export_ruleset(format=format, include_builtins=include_builtins)
    media_type = "application/x-yaml" if format == "yaml" else "application/json"
    filename = f"ruleset_{tenant_id}_{datetime.utcnow().strftime('%Y%m%d')}.{format}"
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.post("/custom/import")
async def import_custom_ruleset(
    request: ImportRulesetRequest,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """
    Import rules from YAML or JSON content.

    Modes:
    - **merge**: Add new rules, skip existing (safe default)
    - **replace**: Delete all custom rules first, then import
    - **append**: Add all rules with new IDs (no duplicate check)
    """
    mgr = CustomRulesetManager(db, tenant_id)
    try:
        return mgr.import_ruleset(
            content=request.content,
            format=request.format,
            mode=request.mode,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Import failed: {str(e)}")


# ==================== Ruleset Stats ====================

@router.get("/custom/stats")
async def get_custom_ruleset_stats(
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Get statistics about your ruleset configuration."""
    mgr = CustomRulesetManager(db, tenant_id)
    return mgr.get_ruleset_stats()
