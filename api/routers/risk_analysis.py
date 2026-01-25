"""
Risk Analysis API Router

Endpoints for running risk analysis, managing rules, and viewing violations.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

from core.rules import RuleEngine, RiskSeverity, RuleType
from core.rules.models import Entitlement, UserAccess, RiskCategory
from connectors.sap.mock_connector import SAPMockConnector
from connectors.base import ConnectionConfig, ConnectionType
from db.database import get_db
from sqlalchemy.orm import Session

router = APIRouter(tags=["Risk Analysis"])

# Initialize rule engine (singleton)
rule_engine = RuleEngine()

# Initialize mock SAP connector for demo
mock_config = ConnectionConfig(
    name="SAP_DEV",
    connection_type=ConnectionType.RFC,
    host="mock.sap.local",
    sap_client="100"
)
sap_connector = SAPMockConnector(mock_config)
sap_connector.connect()


# =============================================================================
# Request/Response Models
# =============================================================================

class EntitlementModel(BaseModel):
    """Entitlement/authorization model"""
    auth_object: str = Field(..., example="S_TCODE")
    field: str = Field(..., example="TCD")
    value: str = Field(..., example="FK01")
    activity: Optional[str] = None
    system: str = Field(default="SAP")


class UserAnalysisRequest(BaseModel):
    """Request model for user risk analysis"""
    user_id: str = Field(..., example="JSMITH")
    include_details: bool = Field(default=True)
    rule_ids: Optional[List[str]] = Field(default=None, description="Specific rules to check")


class BatchAnalysisRequest(BaseModel):
    """Request for batch user analysis"""
    user_ids: List[str] = Field(..., min_length=1, max_length=100)
    rule_ids: Optional[List[str]] = None


class RuleResponse(BaseModel):
    """Rule information response"""
    rule_id: str
    name: str
    description: str
    rule_type: str
    severity: str
    risk_category: str
    enabled: bool


class ViolationResponse(BaseModel):
    """Violation detail response"""
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
    """Risk analysis result response"""
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
async def analyze_user_access(request: UserAnalysisRequest):
    """
    Analyze a single user's access for SoD violations and sensitive access.

    This endpoint retrieves the user's entitlements from SAP and evaluates
    them against the defined risk rules.
    """
    try:
        # Get user details from SAP
        user_details = sap_connector.get_user_details(request.user_id)

        # Get user entitlements
        entitlements = sap_connector.get_user_entitlements_as_objects(request.user_id)

        # Create UserAccess object for rule engine
        user_access = UserAccess(
            user_id=user_details['user_id'],
            username=user_details['username'],
            full_name=user_details['full_name'],
            department=user_details['department'],
            cost_center=user_details.get('cost_center', ''),
            company_code=user_details.get('company_code', ''),
            roles=[r['role_name'] for r in user_details.get('roles', [])],
            entitlements=entitlements
        )

        # Run risk analysis
        violations = rule_engine.evaluate_user(user_access, request.rule_ids)

        # Get summary
        summary = rule_engine.get_risk_summary(violations)

        # Format response
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
            username=user_details['full_name'],
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
async def analyze_batch_users(request: BatchAnalysisRequest):
    """
    Analyze multiple users in batch.

    Returns aggregated results for all users.
    """
    results = []
    errors = []

    for user_id in request.user_ids:
        try:
            user_details = sap_connector.get_user_details(user_id)
            entitlements = sap_connector.get_user_entitlements_as_objects(user_id)

            user_access = UserAccess(
                user_id=user_id,
                username=user_details['username'],
                full_name=user_details['full_name'],
                department=user_details['department'],
                cost_center=user_details.get('cost_center', ''),
                roles=[r['role_name'] for r in user_details.get('roles', [])],
                entitlements=entitlements
            )

            violations = rule_engine.evaluate_user(user_access, request.rule_ids)
            summary = rule_engine.get_risk_summary(violations)

            results.append({
                'user_id': user_id,
                'username': user_details['full_name'],
                'risk_score': summary['aggregate_risk_score'],
                'violation_count': summary['total_violations'],
                'highest_severity': summary.get('highest_severity', 0),
                'status': 'analyzed'
            })

        except Exception as e:
            errors.append({
                'user_id': user_id,
                'error': str(e),
                'status': 'failed'
            })

    # Sort by risk score descending
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
async def analyze_role(role_id: str):
    """
    Analyze a role for potential risks.

    Checks what violations would occur if a user had only this role.
    """
    try:
        role_details = sap_connector.get_role_details(role_id)

        # Build entitlements from role
        entitlements = []
        for tcode in role_details.get('transactions', []):
            entitlements.append(Entitlement(
                auth_object='S_TCODE',
                field='TCD',
                value=tcode['tcode'],
                system='SAP'
            ))

        # Create synthetic user with just this role
        synthetic_user = UserAccess(
            user_id=f"ROLE_CHECK_{role_id}",
            username=f"Role Analysis: {role_id}",
            full_name=role_details['description'],
            department="N/A",
            roles=[role_id],
            entitlements=entitlements
        )

        violations = rule_engine.evaluate_user(synthetic_user)
        summary = rule_engine.get_risk_summary(violations)

        return {
            'role_id': role_id,
            'role_name': role_details['description'],
            'transaction_count': len(role_details.get('transactions', [])),
            'risk_score': summary['aggregate_risk_score'],
            'violation_count': summary['total_violations'],
            'violations': [
                {
                    'rule_id': v.rule_id,
                    'rule_name': v.rule_name,
                    'severity': v.severity.name
                }
                for v in violations
            ]
        }

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# =============================================================================
# Rule Management Endpoints
# =============================================================================

@router.get("/rules", response_model=List[RuleResponse])
async def list_rules(
    rule_type: Optional[str] = Query(None, description="Filter by rule type"),
    category: Optional[str] = Query(None, description="Filter by risk category"),
    enabled_only: bool = Query(True, description="Only return enabled rules")
):
    """
    List all available risk rules.
    """
    rules = []

    for rule_id, rule in rule_engine.rules.items():
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
async def get_rule_details(rule_id: str):
    """
    Get detailed information about a specific rule.
    """
    rule = rule_engine.rules.get(rule_id)
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
async def get_rule_statistics():
    """
    Get statistics about loaded rules.
    """
    return rule_engine.get_statistics()


# =============================================================================
# Simulation Endpoints
# =============================================================================

@router.post("/simulate/add-role")
async def simulate_role_addition(
    user_id: str = Query(..., description="User to simulate"),
    role_id: str = Query(..., description="Role to add")
):
    """
    Simulate what would happen if a role was added to a user.

    This is useful for pre-request risk analysis in access request workflows.
    """
    try:
        # Get current user access
        user_details = sap_connector.get_user_details(user_id)
        current_entitlements = sap_connector.get_user_entitlements_as_objects(user_id)

        # Get role entitlements
        role_details = sap_connector.get_role_details(role_id)
        new_entitlements = []
        for tcode in role_details.get('transactions', []):
            new_entitlements.append(Entitlement(
                auth_object='S_TCODE',
                field='TCD',
                value=tcode['tcode'],
                system='SAP'
            ))

        # Analyze current state
        current_user = UserAccess(
            user_id=user_id,
            username=user_details['username'],
            full_name=user_details['full_name'],
            department=user_details['department'],
            roles=[r['role_name'] for r in user_details.get('roles', [])],
            entitlements=current_entitlements
        )
        current_violations = rule_engine.evaluate_user(current_user)

        # Analyze with new role
        future_user = UserAccess(
            user_id=user_id,
            username=user_details['username'],
            full_name=user_details['full_name'],
            department=user_details['department'],
            roles=[r['role_name'] for r in user_details.get('roles', [])] + [role_id],
            entitlements=current_entitlements + new_entitlements
        )
        future_violations = rule_engine.evaluate_user(future_user)

        # Find new violations
        current_rule_ids = {v.rule_id for v in current_violations}
        new_violations = [v for v in future_violations if v.rule_id not in current_rule_ids]

        current_summary = rule_engine.get_risk_summary(current_violations)
        future_summary = rule_engine.get_risk_summary(future_violations)

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


# Legacy endpoint for backwards compatibility
@router.post("/analyze")
def analyze_access(payload: dict):
    """Legacy analyze endpoint - use /analyze/user instead"""
    return {
        "risk_score": 82,
        "violations": ["FI_P2P_001"],
        "decision": "ESCALATE",
        "message": "This is a legacy endpoint. Please use /analyze/user for full functionality."
    }
