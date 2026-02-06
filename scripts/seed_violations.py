#!/usr/bin/env python3
"""
Violations Seed Script

Populates the database with initial SoD rules and violations for testing.

Run:
    python scripts/seed_violations.py
    python scripts/seed_violations.py --tenant tenant_acme
    python scripts/seed_violations.py --clear  # Clear existing first
"""

import argparse
import sys
import os
import random
import uuid
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from db.database import db_manager
from db.models.risk import RiskRuleModel, RiskViolation, RiskSeverityLevel, ViolationStatus
from db.models.user import User


# Standard SoD Rules
SOD_RULES = [
    {
        "rule_id": "SOD-P2P-001",
        "name": "Create PO / Release PO",
        "description": "User should not be able to both create and release purchase orders",
        "rule_type": "sod",
        "severity": RiskSeverityLevel.HIGH,
        "risk_category": "Procure-to-Pay",
        "rule_definition": {
            "function1": "Create Purchase Order",
            "function2": "Release Purchase Order",
            "function1_transactions": ["ME21N", "ME21"],
            "function2_transactions": ["ME29N", "ME28"]
        },
        "mitigation_controls": ["Dual approval workflow", "Periodic audit review"]
    },
    {
        "rule_id": "SOD-P2P-002",
        "name": "Create Vendor / Process Payment",
        "description": "User should not be able to both create vendors and process payments",
        "rule_type": "sod",
        "severity": RiskSeverityLevel.CRITICAL,
        "risk_category": "Procure-to-Pay",
        "rule_definition": {
            "function1": "Create Vendor Master",
            "function2": "Execute Payment Run",
            "function1_transactions": ["XK01", "FK01"],
            "function2_transactions": ["F110", "F111"]
        },
        "mitigation_controls": ["Segregated approval workflow", "Vendor audit"]
    },
    {
        "rule_id": "SOD-P2P-003",
        "name": "Create PO / Post Invoice",
        "description": "User should not be able to both create POs and post invoices",
        "rule_type": "sod",
        "severity": RiskSeverityLevel.HIGH,
        "risk_category": "Procure-to-Pay",
        "rule_definition": {
            "function1": "Create Purchase Order",
            "function2": "Post Invoice",
            "function1_transactions": ["ME21N"],
            "function2_transactions": ["MIRO", "FB60"]
        },
        "mitigation_controls": ["Three-way matching", "Invoice approval workflow"]
    },
    {
        "rule_id": "SOD-FI-001",
        "name": "Post Journal Entry / Approve Journal Entry",
        "description": "User should not be able to both post and approve journal entries",
        "rule_type": "sod",
        "severity": RiskSeverityLevel.HIGH,
        "risk_category": "Financial Accounting",
        "rule_definition": {
            "function1": "Post Journal Entry",
            "function2": "Approve Journal Entry",
            "function1_transactions": ["FB01", "FB50"],
            "function2_transactions": ["FBV2", "FBRA"]
        },
        "mitigation_controls": ["Journal entry approval workflow"]
    },
    {
        "rule_id": "SOD-FI-002",
        "name": "Maintain GL Account / Post to GL",
        "description": "User should not be able to both maintain GL accounts and post to them",
        "rule_type": "sod",
        "severity": RiskSeverityLevel.MEDIUM,
        "risk_category": "Financial Accounting",
        "rule_definition": {
            "function1": "Maintain GL Account",
            "function2": "Post to GL Account",
            "function1_transactions": ["FS00", "FSS0"],
            "function2_transactions": ["FB01", "FB50"]
        },
        "mitigation_controls": ["Periodic GL account review"]
    },
    {
        "rule_id": "SOD-HR-001",
        "name": "Maintain HR Master / Run Payroll",
        "description": "User should not be able to both maintain HR data and run payroll",
        "rule_type": "sod",
        "severity": RiskSeverityLevel.CRITICAL,
        "risk_category": "Human Resources",
        "rule_definition": {
            "function1": "Maintain HR Master",
            "function2": "Execute Payroll",
            "function1_transactions": ["PA30", "PA20"],
            "function2_transactions": ["PC00_M99_CALC", "PC00_M99_CIPE"]
        },
        "mitigation_controls": ["Payroll approval workflow", "HR audit"]
    },
    {
        "rule_id": "SOD-SD-001",
        "name": "Maintain Customer / Post Customer Invoice",
        "description": "User should not be able to both maintain customers and post invoices",
        "rule_type": "sod",
        "severity": RiskSeverityLevel.MEDIUM,
        "risk_category": "Order-to-Cash",
        "rule_definition": {
            "function1": "Maintain Customer Master",
            "function2": "Post Customer Invoice",
            "function1_transactions": ["XD01", "VD01"],
            "function2_transactions": ["VF01", "FB70"]
        },
        "mitigation_controls": ["Customer credit review"]
    },
    {
        "rule_id": "SOD-SEC-001",
        "name": "User Admin / Role Admin",
        "description": "User administration should be segregated from role administration",
        "rule_type": "sod",
        "severity": RiskSeverityLevel.CRITICAL,
        "risk_category": "Security Administration",
        "rule_definition": {
            "function1": "User Administration",
            "function2": "Role Administration",
            "function1_transactions": ["SU01", "SU10"],
            "function2_transactions": ["PFCG", "SU24"]
        },
        "mitigation_controls": ["Security admin segregation policy"]
    },
    {
        "rule_id": "SOD-SEC-002",
        "name": "Transport Release / Debug in Production",
        "description": "Development and transport admin should not have debug access in production",
        "rule_type": "sod",
        "severity": RiskSeverityLevel.CRITICAL,
        "risk_category": "Security Administration",
        "rule_definition": {
            "function1": "Release Transport",
            "function2": "Debug in Production",
            "function1_transactions": ["SE09", "SE10"],
            "function2_transactions": ["SE38", "SE80"]
        },
        "mitigation_controls": ["Development access review"]
    },
    {
        "rule_id": "SOD-MM-001",
        "name": "Maintain Material / Post Goods Movement",
        "description": "Material maintenance should be segregated from goods movements",
        "rule_type": "sod",
        "severity": RiskSeverityLevel.MEDIUM,
        "risk_category": "Materials Management",
        "rule_definition": {
            "function1": "Maintain Material Master",
            "function2": "Post Goods Movement",
            "function1_transactions": ["MM01", "MM02"],
            "function2_transactions": ["MIGO", "MB01"]
        },
        "mitigation_controls": ["Inventory audit"]
    }
]

SAMPLE_USERS = [
    "JSMITH", "MBROWN", "TDAVIS", "AWILSON", "RJOHNSON",
    "KSANCHEZ", "MGARCIA", "PLEE", "JCHEN", "AWRIGHT"
]


def create_rules_and_violations(
    session,
    tenant_id: str,
    clear_existing: bool = False
):
    """Create SoD rules and sample violations"""

    if clear_existing:
        print(f"Clearing existing rules and violations for tenant {tenant_id}...")
        session.query(RiskViolation).filter(RiskViolation.tenant_id == tenant_id).delete()
        session.query(RiskRuleModel).filter(RiskRuleModel.tenant_id == tenant_id).delete()
        session.commit()
        print("Existing data cleared.")

    # Create SoD Rules
    print("Creating SoD rules...")
    rules_created = 0

    for rule_data in SOD_RULES:
        existing = session.query(RiskRuleModel).filter(
            RiskRuleModel.tenant_id == tenant_id,
            RiskRuleModel.rule_id == rule_data["rule_id"]
        ).first()

        if existing:
            print(f"  Rule {rule_data['rule_id']} already exists, skipping...")
            continue

        rule = RiskRuleModel(
            tenant_id=tenant_id,
            rule_id=rule_data["rule_id"],
            name=rule_data["name"],
            description=rule_data["description"],
            rule_type=rule_data["rule_type"],
            severity=rule_data["severity"],
            risk_category=rule_data["risk_category"],
            rule_definition=rule_data["rule_definition"],
            mitigation_controls=rule_data["mitigation_controls"],
            is_enabled=True,
            created_by="system",
            created_at=datetime.utcnow() - timedelta(days=random.randint(30, 365)),
            updated_at=datetime.utcnow()
        )
        session.add(rule)
        rules_created += 1

    session.commit()
    print(f"Created {rules_created} SoD rules")

    # Get users from database or use sample list
    users = session.query(User).filter(User.tenant_id == tenant_id).limit(10).all()
    user_ids = [u.user_id for u in users] if users else SAMPLE_USERS

    # Create sample violations
    print("Creating sample violations...")
    violations_created = 0
    rules = session.query(RiskRuleModel).filter(RiskRuleModel.tenant_id == tenant_id).all()

    for rule in rules:
        # Create 1-5 violations per rule
        num_violations = random.randint(1, 5)

        for _ in range(num_violations):
            user_id = random.choice(user_ids)
            detected_days_ago = random.randint(1, 90)

            # Random status with weight towards open
            status_weights = [
                (ViolationStatus.OPEN, 0.50),
                (ViolationStatus.IN_PROGRESS, 0.20),
                (ViolationStatus.MITIGATED, 0.15),
                (ViolationStatus.ACCEPTED, 0.10),
                (ViolationStatus.CLOSED, 0.05)
            ]
            status = random.choices(
                [s[0] for s in status_weights],
                weights=[s[1] for s in status_weights]
            )[0]

            violation = RiskViolation(
                tenant_id=tenant_id,
                violation_id=f"VIO-{uuid.uuid4().hex[:8].upper()}",
                rule_id=rule.rule_id,
                rule_name=rule.name,
                rule_type=rule.rule_type,
                user_external_id=user_id,
                username=user_id,
                severity=rule.severity,
                severity_score=random.randint(50, 95),
                risk_category=rule.risk_category,
                conflicting_functions=rule.rule_definition.get("function1", "") + " / " + rule.rule_definition.get("function2", ""),
                conflicting_entitlements=rule.rule_definition.get("function1_transactions", []) + rule.rule_definition.get("function2_transactions", []),
                business_impact=rule.description,
                status=status,
                detected_at=datetime.utcnow() - timedelta(days=detected_days_ago),
                detected_by="system",
                is_mitigated=status in [ViolationStatus.MITIGATED, ViolationStatus.ACCEPTED],
                created_at=datetime.utcnow() - timedelta(days=detected_days_ago),
                updated_at=datetime.utcnow()
            )

            if status in [ViolationStatus.MITIGATED, ViolationStatus.CLOSED]:
                violation.resolved_at = datetime.utcnow() - timedelta(days=random.randint(0, detected_days_ago-1))
                violation.resolved_by = "security_admin"
                violation.resolution_notes = "Reviewed and mitigated through workflow"

            session.add(violation)
            violations_created += 1

            # Update rule violation count
            rule.violation_count = (rule.violation_count or 0) + 1
            rule.last_triggered_at = violation.detected_at

    session.commit()
    print(f"Created {violations_created} violations")

    # Print summary
    print("\n" + "=" * 60)
    print("VIOLATIONS SEED SUMMARY")
    print("=" * 60)

    total_rules = session.query(RiskRuleModel).filter(
        RiskRuleModel.tenant_id == tenant_id
    ).count()

    total_violations = session.query(RiskViolation).filter(
        RiskViolation.tenant_id == tenant_id
    ).count()

    open_violations = session.query(RiskViolation).filter(
        RiskViolation.tenant_id == tenant_id,
        RiskViolation.status == ViolationStatus.OPEN
    ).count()

    critical = session.query(RiskViolation).filter(
        RiskViolation.tenant_id == tenant_id,
        RiskViolation.severity == RiskSeverityLevel.CRITICAL,
        RiskViolation.status == ViolationStatus.OPEN
    ).count()

    print(f"  Tenant:            {tenant_id}")
    print(f"  Total Rules:       {total_rules}")
    print(f"  Total Violations:  {total_violations}")
    print(f"  Open Violations:   {open_violations}")
    print(f"  Critical Open:     {critical}")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="Seed database with SoD rules and violations"
    )
    parser.add_argument(
        "--tenant",
        default="tenant_default",
        help="Tenant ID (default: tenant_default)"
    )
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Clear existing data before seeding"
    )
    parser.add_argument(
        "--db-url",
        default=None,
        help="Database URL (default: from DATABASE_URL env var)"
    )

    args = parser.parse_args()

    print("=" * 60)
    print("Governex+ Violations Seed Script")
    print("=" * 60)

    if args.db_url:
        os.environ['DATABASE_URL'] = args.db_url

    db_manager.init()
    db_manager.create_tables()

    print(f"Database: {db_manager.database_url.split('@')[-1] if '@' in db_manager.database_url else db_manager.database_url}")
    print()

    with db_manager.session_scope() as session:
        create_rules_and_violations(
            session,
            tenant_id=args.tenant,
            clear_existing=args.clear
        )

    print("\nSeeding complete!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
