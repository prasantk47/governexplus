# BRF+ vs GOVERNEX+ Side-by-Side Demo
# Demonstrates the transformation from BRF+ to modern decision intelligence

"""
Side-by-Side Comparison: BRF+ vs GOVERNEX+

This demo shows:
1. Same request processed by both systems
2. BRF+ limitations vs GOVERNEX+ advantages
3. Full explainability chain
4. Migration path from BRF+ rules
"""

from datetime import datetime, timedelta
from typing import Dict, Any

from .models import (
    ApprovalRequest, ApprovalContext, Approver, ApproverType,
    RequestContext, RiskContext, UserContext, ApprovalStatus
)
from .engine import ApproverDeterminationEngine
from .rules import ApprovalRuleEngine, BUILTIN_RULES
from .converter import BRFPlusConverter
from .explainability import ExplainabilityEngine, Audience
from .optimizer import ApproverOptimizer
from .delegation import DelegationManager
from .kpis import ApprovalKPIEngine


def simulate_brfplus_routing(request: Dict[str, Any]) -> Dict[str, Any]:
    """
    Simulate how SAP BRF+ would route this request.

    BRF+ characteristics:
    - Static decision tables
    - No risk awareness
    - No explanations
    - No optimization
    """
    # BRF+ uses hardcoded decision tables
    approvers = []

    # Rule 1: Production system -> System Owner (always)
    if request.get("is_production"):
        approvers.append("SYSTEM_OWNER")

    # Rule 2: Cost > 10000 -> Finance Manager (static threshold)
    if request.get("cost_center_impact", 0) > 10000:
        approvers.append("FINANCE_MANAGER")

    # Rule 3: Sensitive role -> Role Owner (always)
    if "sensitive" in request.get("role_id", "").lower():
        approvers.append("ROLE_OWNER")

    # Default: Line Manager
    if not approvers:
        approvers.append("LINE_MANAGER")

    return {
        "system": "BRF+",
        "approvers": approvers,
        "sla_hours": 48,  # Static SLA
        "risk_score": None,  # No risk calculation
        "explanation": None,  # No explanation
        "optimization": None,  # No optimization
        "delegation": None,  # Manual delegation only
        "what_if": None,  # No what-if
    }


def simulate_governex_routing(request: Dict[str, Any]) -> Dict[str, Any]:
    """
    Simulate how GOVERNEX+ routes this request.

    GOVERNEX+ characteristics:
    - Dynamic, risk-adaptive
    - Full explainability
    - AI optimization
    - Automatic delegation
    """
    # Create context
    context = ApprovalContext(
        request=RequestContext(
            request_id=request.get("request_id", "REQ-001"),
            request_type=request.get("request_type", "ROLE_ASSIGNMENT"),
            system_id=request.get("system_id", "SAP_ECC"),
            is_production=request.get("is_production", False),
            business_process=request.get("business_process", ""),
        ),
        risk=RiskContext(
            risk_score=request.get("risk_score", 45),
            sod_conflicts=request.get("sod_conflicts", []),
            sensitive_data_access=request.get("sensitive_data", []),
            toxic_combinations=[],
            high_privilege_indicators=[],
        ),
        user=UserContext(
            user_id=request.get("requester_id", "user123"),
            user_name=request.get("requester_name", "John Doe"),
            department=request.get("department", "Finance"),
            manager_id=request.get("manager_id", "mgr456"),
        ),
    )

    # Initialize engines
    engine = ApproverDeterminationEngine()
    rule_engine = ApprovalRuleEngine()
    explainer = ExplainabilityEngine(rule_engine)
    optimizer = ApproverOptimizer()

    # Determine approvers
    result = engine.determine(
        ApprovalRequest(
            request_id=context.request.request_id,
            request_type=context.request.request_type,
            system_id=context.request.system_id,
            requester_id=context.user.user_id,
            is_production=context.request.is_production,
            risk_score=context.risk.risk_score,
        )
    )

    # Get explanation
    explanation = explainer.explain(
        ApprovalRequest(
            request_id=context.request.request_id,
            request_type=context.request.request_type,
            system_id=context.request.system_id,
            requester_id=context.user.user_id,
            risk_score=context.risk.risk_score,
        ),
        context,
        result.matched_rules if hasattr(result, 'matched_rules') else [],
        result.approvers,
        audience=Audience.REQUESTER,
    )

    return {
        "system": "GOVERNEX+",
        "approvers": [a.approver_type.value for a in result.approvers],
        "sla_hours": result.sla_hours,
        "risk_score": context.risk.risk_score,
        "risk_level": "MEDIUM" if context.risk.risk_score <= 50 else "HIGH",
        "explanation": explanation.summary,
        "approver_reasons": explanation.approver_explanations,
        "optimization": "AI-optimized approver selection available",
        "delegation": "Automatic delegation on OOO",
        "what_if": "What-if analysis available",
    }


def run_comparison_demo():
    """Run side-by-side comparison demonstration."""
    print("=" * 70)
    print("BRF+ vs GOVERNEX+ APPROVER DETERMINATION COMPARISON")
    print("=" * 70)
    print()

    # Test scenarios
    scenarios = [
        {
            "name": "Low-Risk Standard Request",
            "request": {
                "request_id": "REQ-001",
                "request_type": "ROLE_ASSIGNMENT",
                "system_id": "SAP_ECC",
                "is_production": False,
                "risk_score": 18,
                "requester_id": "user001",
                "requester_name": "Alice Smith",
                "department": "Sales",
                "role_id": "Z_SALES_DISPLAY",
            }
        },
        {
            "name": "High-Risk Production Request",
            "request": {
                "request_id": "REQ-002",
                "request_type": "ROLE_ASSIGNMENT",
                "system_id": "SAP_PROD",
                "is_production": True,
                "risk_score": 75,
                "sod_conflicts": ["Create PO / Approve PO"],
                "sensitive_data": ["FINANCIAL", "CUSTOMER_PII"],
                "requester_id": "user002",
                "requester_name": "Bob Jones",
                "department": "Procurement",
                "role_id": "Z_PROCURE_SENSITIVE",
                "cost_center_impact": 50000,
            }
        },
        {
            "name": "Critical CISO-Level Request",
            "request": {
                "request_id": "REQ-003",
                "request_type": "ROLE_ASSIGNMENT",
                "system_id": "SAP_PROD",
                "is_production": True,
                "risk_score": 92,
                "sod_conflicts": ["Full Basis Admin"],
                "sensitive_data": ["ALL_DATA_ACCESS"],
                "requester_id": "user003",
                "requester_name": "Charlie Brown",
                "department": "IT",
                "role_id": "SAP_ALL",
                "cost_center_impact": 0,
            }
        },
    ]

    for scenario in scenarios:
        print("-" * 70)
        print(f"SCENARIO: {scenario['name']}")
        print("-" * 70)
        print()

        request = scenario["request"]

        # BRF+ routing
        brfplus = simulate_brfplus_routing(request)

        # GOVERNEX+ routing
        governex = simulate_governex_routing(request)

        # Display comparison
        print(f"{'Attribute':<25} {'BRF+':<20} {'GOVERNEX+':<25}")
        print("-" * 70)

        print(f"{'Approvers':<25} {', '.join(brfplus['approvers']):<20} {', '.join(governex['approvers']):<25}")
        print(f"{'SLA (hours)':<25} {brfplus['sla_hours']:<20} {governex['sla_hours']:<25}")
        print(f"{'Risk Score':<25} {'N/A':<20} {governex['risk_score']:<25}")
        print(f"{'Risk Level':<25} {'N/A':<20} {governex.get('risk_level', 'N/A'):<25}")
        print(f"{'Explanation':<25} {'None':<20} {'Available':<25}")
        print(f"{'AI Optimization':<25} {'No':<20} {'Yes':<25}")
        print(f"{'Auto Delegation':<25} {'No':<20} {'Yes':<25}")
        print(f"{'What-If Analysis':<25} {'No':<20} {'Yes':<25}")

        print()
        print("GOVERNEX+ Explanation for Requester:")
        print(f"  {governex['explanation']}")
        print()

        if governex.get("approver_reasons"):
            print("GOVERNEX+ Approver Justifications:")
            for ar in governex["approver_reasons"][:3]:
                print(f"  - {ar.get('approver', 'Unknown')}: {ar.get('reason', 'N/A')}")
        print()

    # Summary of advantages
    print("=" * 70)
    print("GOVERNEX+ ADVANTAGES OVER BRF+")
    print("=" * 70)
    print()

    advantages = [
        ("Risk-Adaptive Routing", "Routes based on calculated risk score, not just static rules"),
        ("Full Explainability", "Every decision explained for requesters, approvers, and auditors"),
        ("AI Optimization", "Learns from approver performance to optimize selection"),
        ("Automatic Delegation", "Handles OOO and SLA risks automatically"),
        ("What-If Analysis", "Test 'what if' scenarios before submitting"),
        ("SLA Intelligence", "Dynamic SLA based on risk and complexity"),
        ("YAML Rules", "No ABAP expertise needed, version-controlled rules"),
        ("Audit Trail", "Complete determination path for compliance"),
        ("Conflict Detection", "Detects conflicts of interest automatically"),
        ("KPI Dashboard", "Real-time performance monitoring"),
    ]

    for i, (feature, description) in enumerate(advantages, 1):
        print(f"{i:2}. {feature}")
        print(f"    {description}")
        print()


def demo_brfplus_migration():
    """Demonstrate BRF+ to GOVERNEX+ migration."""
    print("=" * 70)
    print("BRF+ TO GOVERNEX+ MIGRATION DEMO")
    print("=" * 70)
    print()

    # Sample BRF+ rules (as they would be exported)
    brfplus_rules = [
        {
            "rule_id": "BRFPLUS_001",
            "rule_name": "Production System Approval",
            "conditions": [
                {"field": "SYSTEM_TYPE", "operator": "EQ", "value": "PROD"}
            ],
            "actions": [
                {"type": "SET_APPROVER", "value": "SYSTEM_OWNER"}
            ],
        },
        {
            "rule_id": "BRFPLUS_002",
            "rule_name": "High Value Approval",
            "conditions": [
                {"field": "COST_IMPACT", "operator": "GT", "value": "10000"}
            ],
            "actions": [
                {"type": "SET_APPROVER", "value": "FINANCE_MGR"}
            ],
        },
        {
            "rule_id": "BRFPLUS_003",
            "rule_name": "Sensitive Role Approval",
            "conditions": [
                {"field": "ROLE_CATEGORY", "operator": "EQ", "value": "SENSITIVE"}
            ],
            "actions": [
                {"type": "SET_APPROVER", "value": "ROLE_OWNER"},
                {"type": "SET_APPROVER", "value": "SECURITY_OFFICER"}
            ],
        },
    ]

    converter = BRFPlusConverter()
    result = converter.convert_from_dict(brfplus_rules)

    print(f"Conversion Results:")
    print(f"  Rules Converted: {result.rules_converted}")
    print(f"  Rules Failed: {result.rules_failed}")
    print(f"  Warnings: {len(result.warnings)}")
    print()

    print("Converted YAML Rules:")
    print("-" * 70)

    for rule in result.converted_rules[:2]:
        print(rule.to_yaml())
        print()

    print("-" * 70)
    print()

    # Show migration report
    print("Migration Report:")
    print(converter.generate_migration_report(result))


def demo_full_workflow():
    """Demonstrate full approval workflow with all GOVERNEX+ features."""
    print("=" * 70)
    print("FULL GOVERNEX+ WORKFLOW DEMONSTRATION")
    print("=" * 70)
    print()

    # Create a request
    request = ApprovalRequest(
        request_id="DEMO-001",
        request_type="ROLE_ASSIGNMENT",
        system_id="SAP_PROD",
        requester_id="demo_user",
        role_id="Z_FINANCE_ADMIN",
        is_production=True,
        risk_score=65,
        submitted_at=datetime.now(),
    )

    context = ApprovalContext(
        request=RequestContext(
            request_id=request.request_id,
            request_type=request.request_type,
            system_id=request.system_id,
            is_production=True,
            business_process="FINANCIAL_CLOSE",
        ),
        risk=RiskContext(
            risk_score=65,
            sod_conflicts=["Create Journal / Post Journal"],
            sensitive_data_access=["FINANCIAL_DATA"],
            toxic_combinations=[],
            high_privilege_indicators=["FINANCIAL_ADMIN"],
        ),
        user=UserContext(
            user_id="demo_user",
            user_name="Demo User",
            department="Finance",
            manager_id="finance_mgr",
        ),
    )

    print("Step 1: Request Submitted")
    print(f"  Request ID: {request.request_id}")
    print(f"  System: {request.system_id}")
    print(f"  Role: {request.role_id}")
    print()

    print("Step 2: Risk Assessment")
    print(f"  Risk Score: {context.risk.risk_score}/100")
    print(f"  Risk Level: HIGH (51-80)")
    print(f"  SoD Conflicts: {context.risk.sod_conflicts}")
    print(f"  Sensitive Data: {context.risk.sensitive_data_access}")
    print()

    print("Step 3: Approver Determination")
    engine = ApproverDeterminationEngine()
    result = engine.determine(request)

    print(f"  Approvers Required: {len(result.approvers)}")
    for approver in result.approvers:
        print(f"    - {approver.approver_type.value}: {approver.approver_name}")
    print(f"  SLA: {result.sla_hours} hours")
    print()

    print("Step 4: Explanation Generated")
    rule_engine = ApprovalRuleEngine()
    explainer = ExplainabilityEngine(rule_engine)
    explanation = explainer.explain(
        request, context,
        result.matched_rules if hasattr(result, 'matched_rules') else [],
        result.approvers,
        audience=Audience.REQUESTER,
    )
    print(f"  For Requester: {explanation.headline}")
    print(f"  Summary: {explanation.summary[:200]}...")
    print()

    print("Step 5: AI Optimization Available")
    optimizer = ApproverOptimizer()
    print("  AI can suggest optimal approver based on:")
    print("    - Historical response times")
    print("    - Current workload")
    print("    - Decision quality")
    print()

    print("Step 6: Delegation Configured")
    delegation_mgr = DelegationManager()
    print("  If primary approver is OOO:")
    print("    - Auto-delegate to configured backup")
    print("    - Escalate if SLA at risk")
    print("    - Fall back to Governance Desk")
    print()

    print("Step 7: KPIs Tracked")
    kpi_engine = ApprovalKPIEngine()
    print("  Metrics captured:")
    print("    - Time to approval")
    print("    - SLA compliance")
    print("    - Approver performance")
    print("    - Risk vs speed correlation")
    print()

    print("=" * 70)
    print("WORKFLOW COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    print("\n")
    run_comparison_demo()
    print("\n" * 2)
    demo_brfplus_migration()
    print("\n" * 2)
    demo_full_workflow()
