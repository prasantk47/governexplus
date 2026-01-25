# SoD Rules API Router
# Separation of Duties Ruleset Management

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
from datetime import datetime

from core.rules.sod_ruleset import (
    SoDRulesetLibrary, BusinessFunction, SoDRule,
    RiskLevel, BusinessProcess
)

router = APIRouter(prefix="/sod-rules", tags=["SoD Rules"])

# Global engine instance
sod_library = SoDRulesetLibrary()


# ==================== Request/Response Models ====================

class RiskAnalysisRequest(BaseModel):
    user_id: str
    transaction_codes: List[str] = []
    auth_objects: List[Dict[str, Any]] = []
    roles: List[str] = []


class BulkEnableRequest(BaseModel):
    rule_ids: List[str]
    enabled: bool


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
async def analyze_user_access(request: RiskAnalysisRequest):
    """
    Analyze user access for SoD violations

    Check transaction codes or auth objects against the ruleset.
    """
    violations = []
    user_tcodes = set(request.transaction_codes)

    for rule in sod_library.get_all_rules():
        func1_tcodes = set(rule.function1.transaction_codes)
        func2_tcodes = set(rule.function2.transaction_codes)

        # Check if user has access to both conflicting functions
        has_func1 = bool(user_tcodes & func1_tcodes)
        has_func2 = bool(user_tcodes & func2_tcodes)

        if has_func1 and has_func2:
            violations.append({
                "rule_id": rule.rule_id,
                "rule_name": rule.name,
                "risk_level": rule.risk_level.value,
                "function1": rule.function1.name,
                "function2": rule.function2.name,
                "conflicting_tcodes_func1": list(user_tcodes & func1_tcodes),
                "conflicting_tcodes_func2": list(user_tcodes & func2_tcodes),
                "risk_description": rule.risk_description,
                "business_impact": rule.business_impact,
                "recommendation": rule.recommendation
            })

    return {
        "user_id": request.user_id,
        "analysis_date": datetime.utcnow().isoformat(),
        "violations_found": len(violations),
        "violations": violations,
        "risk_summary": {
            "critical": len([v for v in violations if v["risk_level"] == "critical"]),
            "high": len([v for v in violations if v["risk_level"] == "high"]),
            "medium": len([v for v in violations if v["risk_level"] == "medium"]),
            "low": len([v for v in violations if v["risk_level"] == "low"])
        }
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
    """Export the complete ruleset for backup"""
    functions = sod_library.get_all_functions()
    rules = sod_library.get_all_rules(active_only=False)

    return {
        "version": "1.0",
        "exported_at": datetime.utcnow().isoformat(),
        "statistics": sod_library.get_statistics(),
        "functions": [f.to_dict() for f in functions],
        "rules": [r.to_dict() for r in rules]
    }
