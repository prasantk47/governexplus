"""
Risk Analysis API Router

Endpoints for running risk analysis, managing rules, and viewing violations.
User/role/entitlement data is sourced from the database.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, DefaultDict
from datetime import datetime
from collections import defaultdict

from sqlalchemy.orm import Session
from sqlalchemy import func

from core.rules import RuleEngine, RiskSeverity, RuleType
from core.rules.models import Entitlement, UserAccess, RiskCategory
from db.database import get_db
from db.models.user import User, Role, UserRole, UserEntitlement
from db.models.risk import RiskViolation

router = APIRouter(tags=["Risk Analysis"])

# Per-tenant engine registry
_engines: Dict[str, RuleEngine] = {}


def _get_tenant_id() -> str:
    from core.tenant import get_current_tenant
    ctx = get_current_tenant()
    return ctx.tenant_id if ctx else "default"


def _get_engine(tenant_id: str = Depends(_get_tenant_id)) -> RuleEngine:
    if tenant_id not in _engines:
        _engines[tenant_id] = RuleEngine()
    return _engines[tenant_id]


def _build_user_access_from_db(user_id: str, db: Session) -> UserAccess:
    """Build a UserAccess object from DB data for the rule engine."""
    user = db.query(User).filter(
        (User.username == user_id) | (User.user_id == user_id)
    ).first()
    if not user:
        raise ValueError(f"User {user_id} not found")

    # Get roles
    user_roles = (
        db.query(UserRole, Role)
        .join(Role, UserRole.role_id == Role.id)
        .filter(UserRole.user_id == user.id)
        .all()
    )
    role_names = [r.role_id if hasattr(r, 'role_id') else r.name for _, r in user_roles]

    # Get entitlements
    db_entitlements = db.query(UserEntitlement).filter(
        UserEntitlement.user_id == user.id
    ).all()

    entitlements = [
        Entitlement(
            auth_object=e.auth_object,
            field=e.auth_field or "VALUE",
            value=e.auth_value or "",
            system=e.source_system or "SAP",
            attributes={"source_role": e.source_role or ""}
        )
        for e in db_entitlements
    ]

    return UserAccess(
        user_id=user.username or str(user.id),
        username=user.username or "",
        full_name=user.full_name or user.username or "",
        department=user.department or "",
        cost_center=getattr(user, 'cost_center', '') or "",
        company_code=getattr(user, 'company_code', '') or "",
        roles=role_names,
        entitlements=entitlements,
    )


def _build_role_entitlements_from_db(role_id: str, db: Session) -> tuple:
    """Get role details and entitlements from DB."""
    role = db.query(Role).filter(
        (Role.role_id == role_id) | (Role.name == role_id)
    ).first()
    if not role:
        raise ValueError(f"Role {role_id} not found")

    # Get entitlements sourced from this role
    ents = db.query(UserEntitlement).filter(
        UserEntitlement.source_role == role_id
    ).all()

    entitlements = [
        Entitlement(
            auth_object=e.auth_object,
            field=e.auth_field or "VALUE",
            value=e.auth_value or "",
            system=e.source_system or "SAP",
        )
        for e in ents
    ]

    return role, entitlements


# =============================================================================
# Request/Response Models
# =============================================================================

class EntitlementModel(BaseModel):
    auth_object: str = Field(..., example="S_TCODE")
    field: str = Field(..., example="TCD")
    value: str = Field(..., example="FK01")
    activity: Optional[str] = None
    system: str = Field(default="SAP")


class UserAnalysisRequest(BaseModel):
    user_id: str = Field(..., example="JSMITH")
    include_details: bool = Field(default=True)
    rule_ids: Optional[List[str]] = Field(default=None, description="Specific rules to check")


class BatchAnalysisRequest(BaseModel):
    user_ids: List[str] = Field(..., min_length=1, max_length=100)
    rule_ids: Optional[List[str]] = None


class RuleResponse(BaseModel):
    rule_id: str
    name: str
    description: str
    rule_type: str
    severity: str
    risk_category: str
    enabled: bool


class ViolationResponse(BaseModel):
    violation_id: str
    rule_id: str
    rule_name: str
    severity: int
    severity_name: str
    risk_category: str
    conflicting_entitlements: List[Dict]
    business_impact: str
    mitigation_controls: List[str]


class AnalysisResultResponse(BaseModel):
    user_id: str
    username: str
    risk_score: float
    total_violations: int
    violations_by_severity: Dict[str, int]
    violations: List[ViolationResponse]
    analysis_timestamp: str


# =============================================================================
# Risk Analysis Endpoints
# =============================================================================

@router.post("/analyze/user", response_model=AnalysisResultResponse)
async def analyze_user_access(
    request: UserAnalysisRequest,
    db: Session = Depends(get_db),
    engine: RuleEngine = Depends(_get_engine),
):
    """
    Analyze a single user's access for SoD violations and sensitive access.
    Retrieves user entitlements from the database.
    """
    try:
        user_access = _build_user_access_from_db(request.user_id, db)

        violations = engine.evaluate_user(user_access, request.rule_ids)
        summary = engine.get_risk_summary(violations)

        violation_responses = [
            ViolationResponse(
                violation_id=v.violation_id,
                rule_id=v.rule_id,
                rule_name=v.rule_name,
                severity=v.severity.value,
                severity_name=v.severity.name,
                risk_category=v.risk_category.value,
                conflicting_entitlements=v.conflicting_entitlements,
                business_impact=v.business_impact,
                mitigation_controls=v.mitigation_controls
            )
            for v in violations
        ]

        return AnalysisResultResponse(
            user_id=request.user_id,
            username=user_access.full_name,
            risk_score=summary['aggregate_risk_score'],
            total_violations=summary['total_violations'],
            violations_by_severity=summary['by_severity'],
            violations=violation_responses,
            analysis_timestamp=datetime.now().isoformat()
        )

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@router.post("/analyze/batch")
async def analyze_batch_users(
    request: BatchAnalysisRequest,
    db: Session = Depends(get_db),
    engine: RuleEngine = Depends(_get_engine),
):
    """Analyze multiple users in batch."""
    results = []
    errors = []

    for user_id in request.user_ids:
        try:
            user_access = _build_user_access_from_db(user_id, db)
            violations = engine.evaluate_user(user_access, request.rule_ids)
            summary = engine.get_risk_summary(violations)

            results.append({
                'user_id': user_id,
                'username': user_access.full_name,
                'risk_score': summary['aggregate_risk_score'],
                'violation_count': summary['total_violations'],
                'highest_severity': summary.get('highest_severity', 0),
                'status': 'analyzed'
            })
        except Exception as e:
            errors.append({'user_id': user_id, 'error': str(e), 'status': 'failed'})

    results.sort(key=lambda x: x['risk_score'], reverse=True)

    return {
        'total_users': len(request.user_ids),
        'analyzed': len(results),
        'failed': len(errors),
        'results': results,
        'errors': errors,
        'analysis_timestamp': datetime.now().isoformat()
    }


@router.post("/analyze/role/{role_id}")
async def analyze_role(
    role_id: str,
    db: Session = Depends(get_db),
    engine: RuleEngine = Depends(_get_engine),
):
    """Analyze a role for potential risks."""
    try:
        role, entitlements = _build_role_entitlements_from_db(role_id, db)

        synthetic_user = UserAccess(
            user_id=f"ROLE_CHECK_{role_id}",
            username=f"Role Analysis: {role_id}",
            full_name=role.description or role.name or role_id,
            department="N/A",
            roles=[role_id],
            entitlements=entitlements
        )

        violations = engine.evaluate_user(synthetic_user)
        summary = engine.get_risk_summary(violations)

        return {
            'role_id': role_id,
            'role_name': role.description or role.name,
            'risk_score': summary['aggregate_risk_score'],
            'violation_count': summary['total_violations'],
            'violations': [
                {'rule_id': v.rule_id, 'rule_name': v.rule_name, 'severity': v.severity.name}
                for v in violations
            ]
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# =============================================================================
# Violation List — used by Dashboard and Risk pages
# =============================================================================

@router.get("/violations", summary="List all risk violations")
async def list_violations(
    limit: int = Query(50, ge=1, le=500),
    status: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """List risk violations from the database."""
    from db.models.risk import RiskViolation
    q = db.query(RiskViolation)
    if status:
        q = q.filter(RiskViolation.status == status)
    if severity:
        q = q.filter(RiskViolation.severity == severity)
    violations = q.order_by(RiskViolation.created_at.desc()).limit(limit).all()
    return [v.to_dict() for v in violations]


# =============================================================================
# AC-16: Org-Level Risk Ranking
# =============================================================================

@router.get("/org-ranking", summary="Org-level risk ranking by violation count and weighted score (AC-16)")
async def get_org_ranking(
    group_by: str = Query("department", description="Group dimension: 'department' or 'company_code'"),
    limit: int = Query(20, ge=1, le=200, description="Maximum org units to return"),
    min_violations: int = Query(0, ge=0, description="Minimum violation count to include"),
    db: Session = Depends(get_db),
    engine: RuleEngine = Depends(_get_engine),
):
    """
    Rank org units (departments or company codes) by their aggregate risk posture.

    For each org unit the endpoint returns:
    - **org_unit**: The org dimension value (department name or company code)
    - **user_count**: Number of distinct users in this org unit
    - **violation_count**: Total number of open violations
    - **weighted_score**: Sum of severity_score across all violations — higher = worse
    - **avg_score_per_user**: weighted_score / user_count
    - **top_violations**: Top 5 rules triggered most frequently in this org unit
    - **severity_breakdown**: Count by severity level

    Uses persisted RiskViolation rows joined to User for org attributes.
    """
    if group_by not in ("department", "company_code"):
        raise HTTPException(
            status_code=400,
            detail="group_by must be 'department' or 'company_code'",
        )

    try:
        org_attr = User.department if group_by == "department" else User.company_code

        # Aggregate violations by org unit
        rows = (
            db.query(
                org_attr.label("org_unit"),
                func.count(RiskViolation.id).label("violation_count"),
                func.sum(RiskViolation.severity_score).label("weighted_score"),
                func.count(func.distinct(RiskViolation.user_id)).label("user_count"),
            )
            .join(User, User.id == RiskViolation.user_id)
            .filter(
                RiskViolation.status.in_(["open", "new", "active"]),
                org_attr.isnot(None),
                org_attr != "",
            )
            .group_by(org_attr)
            .order_by(func.sum(RiskViolation.severity_score).desc())
            .limit(limit * 3)
            .all()
        )

        # Top violations per org unit
        violation_detail_q = (
            db.query(
                org_attr.label("org_unit"),
                RiskViolation.rule_id,
                RiskViolation.rule_name,
                func.count(RiskViolation.id).label("count"),
                func.max(RiskViolation.severity_score).label("max_score"),
            )
            .join(User, User.id == RiskViolation.user_id)
            .filter(
                RiskViolation.status.in_(["open", "new", "active"]),
                org_attr.isnot(None),
                org_attr != "",
            )
            .group_by(org_attr, RiskViolation.rule_id, RiskViolation.rule_name)
            .all()
        )

        top_viol_by_org: Dict[str, List[Dict]] = defaultdict(list)
        for vd in violation_detail_q:
            top_viol_by_org[vd.org_unit].append({
                "rule_id": vd.rule_id,
                "rule_name": vd.rule_name,
                "count": vd.count,
                "max_score": vd.max_score,
            })
        for org_key in top_viol_by_org:
            top_viol_by_org[org_key] = sorted(
                top_viol_by_org[org_key], key=lambda x: x["count"], reverse=True
            )[:5]

        # Severity breakdown per org unit
        sev_q = (
            db.query(
                org_attr.label("org_unit"),
                RiskViolation.severity.label("severity"),
                func.count(RiskViolation.id).label("count"),
            )
            .join(User, User.id == RiskViolation.user_id)
            .filter(
                RiskViolation.status.in_(["open", "new", "active"]),
                org_attr.isnot(None),
                org_attr != "",
            )
            .group_by(org_attr, RiskViolation.severity)
            .all()
        )

        sev_by_org: Dict[str, Dict[str, int]] = defaultdict(
            lambda: {"critical": 0, "high": 0, "medium": 0, "low": 0}
        )
        for sv in sev_q:
            sev_val = sv.severity.value if hasattr(sv.severity, "value") else str(sv.severity)
            sev_by_org[sv.org_unit][sev_val] = sv.count

        # Assemble ranking
        ranking = []
        for row in rows:
            if not row.org_unit:
                continue
            violation_count = row.violation_count or 0
            if violation_count < min_violations:
                continue
            user_count = max(row.user_count or 1, 1)
            weighted_score = float(row.weighted_score or 0)

            ranking.append({
                "org_unit": row.org_unit,
                "group_by": group_by,
                "user_count": user_count,
                "violation_count": violation_count,
                "weighted_score": round(weighted_score, 1),
                "avg_score_per_user": round(weighted_score / user_count, 1),
                "severity_breakdown": dict(sev_by_org.get(row.org_unit, {})),
                "top_violations": top_viol_by_org.get(row.org_unit, []),
            })

        ranking.sort(key=lambda x: x["weighted_score"], reverse=True)
        ranking = ranking[:limit]

        return {
            "group_by": group_by,
            "total_org_units": len(ranking),
            "generated_at": datetime.utcnow().isoformat(),
            "ranking": ranking,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Org ranking failed: {str(e)}")


# =============================================================================
# Rule Management Endpoints
# =============================================================================

@router.get("/rules", response_model=List[RuleResponse])
async def list_rules(
    rule_type: Optional[str] = Query(None, description="Filter by rule type"),
    category: Optional[str] = Query(None, description="Filter by risk category"),
    enabled_only: bool = Query(True, description="Only return enabled rules"),
    engine: RuleEngine = Depends(_get_engine),
):
    """List all available risk rules."""
    rules = []
    for rule_id, rule in engine.rules.items():
        if enabled_only and not rule.enabled:
            continue
        if rule_type and rule.rule_type.value != rule_type:
            continue
        if category and rule.risk_category.value != category:
            continue

        rules.append(RuleResponse(
            rule_id=rule.rule_id,
            name=rule.name,
            description=rule.description,
            rule_type=rule.rule_type.value,
            severity=rule.severity.name,
            risk_category=rule.risk_category.value,
            enabled=rule.enabled
        ))
    return rules


@router.get("/rules/{rule_id}")
async def get_rule_details(
    rule_id: str,
    engine: RuleEngine = Depends(_get_engine),
):
    """Get detailed information about a specific rule."""
    rule = engine.rules.get(rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail=f"Rule {rule_id} not found")

    return {
        'rule_id': rule.rule_id,
        'name': rule.name,
        'description': rule.description,
        'rule_type': rule.rule_type.value,
        'severity': rule.severity.name,
        'severity_score': rule.severity.value,
        'risk_category': rule.risk_category.value,
        'business_justification': rule.business_justification,
        'mitigation_controls': rule.mitigation_controls,
        'recommended_actions': rule.recommended_actions,
        'applies_to_systems': rule.applies_to_systems,
        'applies_to_departments': rule.applies_to_departments,
        'enabled': rule.enabled,
        'version': rule.version
    }


@router.get("/rules/statistics")
async def get_rule_statistics(engine: RuleEngine = Depends(_get_engine)):
    """Get statistics about loaded rules."""
    return engine.get_statistics()


# =============================================================================
# Simulation Endpoints
# =============================================================================

@router.post("/simulate/add-role")
async def simulate_role_addition(
    user_id: str = Query(..., description="User to simulate"),
    role_id: str = Query(..., description="Role to add"),
    db: Session = Depends(get_db),
    engine: RuleEngine = Depends(_get_engine),
):
    """Simulate what would happen if a role was added to a user."""
    try:
        current_user = _build_user_access_from_db(user_id, db)
        current_violations = engine.evaluate_user(current_user)

        # Get new role entitlements
        role, new_entitlements = _build_role_entitlements_from_db(role_id, db)

        future_user = UserAccess(
            user_id=current_user.user_id,
            username=current_user.username,
            full_name=current_user.full_name,
            department=current_user.department,
            roles=current_user.roles + [role_id],
            entitlements=current_user.entitlements + new_entitlements
        )
        future_violations = engine.evaluate_user(future_user)

        current_rule_ids = {v.rule_id for v in current_violations}
        new_violations = [v for v in future_violations if v.rule_id not in current_rule_ids]

        current_summary = engine.get_risk_summary(current_violations)
        future_summary = engine.get_risk_summary(future_violations)

        return {
            'user_id': user_id,
            'role_to_add': role_id,
            'simulation_result': {
                'current_state': {
                    'risk_score': current_summary['aggregate_risk_score'],
                    'violation_count': current_summary['total_violations']
                },
                'future_state': {
                    'risk_score': future_summary['aggregate_risk_score'],
                    'violation_count': future_summary['total_violations']
                },
                'risk_increase': future_summary['aggregate_risk_score'] - current_summary['aggregate_risk_score'],
                'new_violations': [
                    {
                        'rule_id': v.rule_id,
                        'rule_name': v.rule_name,
                        'severity': v.severity.name,
                        'risk_category': v.risk_category.value
                    }
                    for v in new_violations
                ]
            },
            'recommendation': 'APPROVE' if not new_violations else 'REVIEW_REQUIRED'
        }

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
