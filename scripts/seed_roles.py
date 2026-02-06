#!/usr/bin/env python3
"""
Role Seed Script

Populates the database with initial role data for testing and demo purposes.
Creates roles across multiple systems with varying risk levels.

Run:
    python scripts/seed_roles.py
    python scripts/seed_roles.py --tenant tenant_acme --count 20
    python scripts/seed_roles.py --clear  # Clear existing roles first
"""

import argparse
import sys
import os
import random
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from db.database import db_manager
from db.models.user import Role


# SAP Roles
SAP_ROLES = [
    # Finance Roles
    {"role_id": "SAP_FI_DISPLAY", "role_name": "Finance Display", "description": "Display financial documents and reports", "role_type": "single", "risk_level": "low", "department": "Finance"},
    {"role_id": "SAP_FI_POSTING", "role_name": "Finance Posting", "description": "Post financial documents", "role_type": "single", "risk_level": "medium", "department": "Finance"},
    {"role_id": "SAP_FI_ADMIN", "role_name": "Finance Administrator", "description": "Full finance administration", "role_type": "single", "risk_level": "high", "department": "Finance"},
    {"role_id": "SAP_AP_CLERK", "role_name": "Accounts Payable Clerk", "description": "AP invoice processing", "role_type": "single", "risk_level": "medium", "department": "Finance"},
    {"role_id": "SAP_AR_CLERK", "role_name": "Accounts Receivable Clerk", "description": "AR invoice and payment processing", "role_type": "single", "risk_level": "medium", "department": "Finance"},
    {"role_id": "SAP_PAYMENT_RUN", "role_name": "Payment Run Execution", "description": "Execute payment runs", "role_type": "single", "risk_level": "critical", "department": "Finance"},

    # Materials Management Roles
    {"role_id": "SAP_MM_DISPLAY", "role_name": "Materials Display", "description": "Display materials and purchasing documents", "role_type": "single", "risk_level": "low", "department": "Procurement"},
    {"role_id": "SAP_MM_CREATE_PO", "role_name": "Create Purchase Order", "description": "Create purchase orders", "role_type": "single", "risk_level": "medium", "department": "Procurement"},
    {"role_id": "SAP_MM_RELEASE_PO", "role_name": "Release Purchase Order", "description": "Approve and release purchase orders", "role_type": "single", "risk_level": "high", "department": "Procurement"},
    {"role_id": "SAP_MM_GOODS_RECEIPT", "role_name": "Goods Receipt", "description": "Post goods receipts", "role_type": "single", "risk_level": "medium", "department": "Procurement"},
    {"role_id": "SAP_VENDOR_MASTER", "role_name": "Vendor Master Maintenance", "description": "Create and maintain vendor master records", "role_type": "single", "risk_level": "high", "department": "Procurement"},

    # HR Roles
    {"role_id": "SAP_HR_DISPLAY", "role_name": "HR Display", "description": "Display HR master data", "role_type": "single", "risk_level": "low", "department": "Human Resources"},
    {"role_id": "SAP_HR_MAINTAIN", "role_name": "HR Maintenance", "description": "Maintain HR master data", "role_type": "single", "risk_level": "high", "department": "Human Resources"},
    {"role_id": "SAP_PAYROLL_RUN", "role_name": "Payroll Run", "description": "Execute payroll processing", "role_type": "single", "risk_level": "critical", "department": "Human Resources"},
    {"role_id": "SAP_ORG_MGMT", "role_name": "Organization Management", "description": "Maintain organizational structure", "role_type": "single", "risk_level": "high", "department": "Human Resources"},

    # Sales Roles
    {"role_id": "SAP_SD_DISPLAY", "role_name": "Sales Display", "description": "Display sales documents", "role_type": "single", "risk_level": "low", "department": "Sales"},
    {"role_id": "SAP_SD_CREATE_SO", "role_name": "Create Sales Order", "description": "Create sales orders", "role_type": "single", "risk_level": "medium", "department": "Sales"},
    {"role_id": "SAP_SD_PRICING", "role_name": "Pricing Maintenance", "description": "Maintain pricing conditions", "role_type": "single", "risk_level": "high", "department": "Sales"},
    {"role_id": "SAP_CUSTOMER_MASTER", "role_name": "Customer Master Maintenance", "description": "Create and maintain customer master records", "role_type": "single", "risk_level": "high", "department": "Sales"},

    # IT/Basis Roles
    {"role_id": "SAP_BASIS_ADMIN", "role_name": "Basis Administrator", "description": "SAP Basis administration", "role_type": "single", "risk_level": "critical", "department": "IT"},
    {"role_id": "SAP_SECURITY_ADMIN", "role_name": "Security Administrator", "description": "User and role administration", "role_type": "single", "risk_level": "critical", "department": "IT"},
    {"role_id": "SAP_DEVELOPER", "role_name": "Developer", "description": "ABAP development access", "role_type": "single", "risk_level": "critical", "department": "IT"},
    {"role_id": "SAP_TRANSPORT_ADMIN", "role_name": "Transport Administrator", "description": "Transport management", "role_type": "single", "risk_level": "critical", "department": "IT"},

    # Business Roles (Composite)
    {"role_id": "BR_AP_MANAGER", "role_name": "AP Manager", "description": "Accounts Payable Manager business role", "role_type": "business", "risk_level": "high", "department": "Finance"},
    {"role_id": "BR_PROCUREMENT", "role_name": "Procurement Specialist", "description": "Full procurement capabilities", "role_type": "business", "risk_level": "high", "department": "Procurement"},
    {"role_id": "BR_HR_SPECIALIST", "role_name": "HR Specialist", "description": "HR administration specialist", "role_type": "business", "risk_level": "high", "department": "Human Resources"},
    {"role_id": "BR_SALES_REP", "role_name": "Sales Representative", "description": "Sales order processing", "role_type": "business", "risk_level": "medium", "department": "Sales"},

    # Emergency/Firefighter Roles
    {"role_id": "SAP_FIREFIGHTER_FI", "role_name": "Firefighter Finance", "description": "Emergency access for finance", "role_type": "emergency", "risk_level": "critical", "department": "IT"},
    {"role_id": "SAP_FIREFIGHTER_BASIS", "role_name": "Firefighter Basis", "description": "Emergency access for Basis", "role_type": "emergency", "risk_level": "critical", "department": "IT"},
]


def create_roles(
    session,
    tenant_id: str,
    count: int = 30,
    clear_existing: bool = False
):
    """Create seed roles in the database"""

    if clear_existing:
        print(f"Clearing existing roles for tenant {tenant_id}...")
        session.query(Role).filter(Role.tenant_id == tenant_id).delete()
        session.commit()
        print("Existing roles cleared.")

    print(f"Creating {min(count, len(SAP_ROLES))} roles...")

    roles_to_create = SAP_ROLES[:count]
    roles_created = 0

    for role_data in roles_to_create:
        # Check if role already exists
        existing = session.query(Role).filter(
            Role.tenant_id == tenant_id,
            Role.role_id == role_data["role_id"]
        ).first()

        if existing:
            print(f"  Role {role_data['role_id']} already exists, skipping...")
            continue

        # Generate additional data
        created_days_ago = random.randint(30, 365)
        created_at = datetime.utcnow() - timedelta(days=created_days_ago)
        user_count = random.randint(5, 150)
        transaction_count = random.randint(3, 50)

        role = Role(
            tenant_id=tenant_id,
            role_id=role_data["role_id"],
            role_name=role_data["role_name"],
            description=role_data["description"],
            role_type=role_data["role_type"],
            risk_level=role_data["risk_level"],
            is_sensitive=role_data["risk_level"] in ["high", "critical"],
            source_system="SAP",
            system_client="100",
            is_active=True,
            user_count=user_count,
            transaction_count=transaction_count,
            created_at=created_at,
            updated_at=datetime.utcnow()
        )
        session.add(role)
        roles_created += 1

    session.commit()
    print(f"Successfully created {roles_created} roles")

    # Print summary
    print("\n" + "=" * 60)
    print("ROLE SEED SUMMARY")
    print("=" * 60)

    total_roles = session.query(Role).filter(Role.tenant_id == tenant_id).count()
    high_risk = session.query(Role).filter(
        Role.tenant_id == tenant_id,
        Role.risk_level.in_(["high", "critical"])
    ).count()

    print(f"  Tenant:        {tenant_id}")
    print(f"  Total Roles:   {total_roles}")
    print(f"  High Risk:     {high_risk}")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="Seed database with test roles"
    )
    parser.add_argument(
        "--tenant",
        default="tenant_default",
        help="Tenant ID (default: tenant_default)"
    )
    parser.add_argument(
        "--count",
        type=int,
        default=30,
        help="Number of roles to create (default: 30)"
    )
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Clear existing roles before seeding"
    )
    parser.add_argument(
        "--db-url",
        default=None,
        help="Database URL (default: from DATABASE_URL env var)"
    )

    args = parser.parse_args()

    print("=" * 60)
    print("Governex+ Role Seed Script")
    print("=" * 60)

    if args.db_url:
        os.environ['DATABASE_URL'] = args.db_url

    db_manager.init()
    db_manager.create_tables()

    print(f"Database: {db_manager.database_url.split('@')[-1] if '@' in db_manager.database_url else db_manager.database_url}")
    print()

    with db_manager.session_scope() as session:
        create_roles(
            session,
            tenant_id=args.tenant,
            count=args.count,
            clear_existing=args.clear
        )

    print("\nSeeding complete!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
