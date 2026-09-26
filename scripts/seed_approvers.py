#!/usr/bin/env python3
"""
Approver Seed Script
Populates the database with initial approver personas for demo.

Usage:
    python scripts/seed_approvers.py
    python scripts/seed_approvers.py --tenant tenant_acme
    python scripts/seed_approvers.py --clear
"""

import argparse
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from db.database import db_manager
from db.models.approver import ApproverModel


DEMO_APPROVERS = [
    {
        "approver_id": "APP-LM-001",
        "name": "Sarah Johnson",
        "email": "sjohnson@company.com",
        "approver_type": "LINE_MANAGER",
        "department": "Operations",
        "job_title": "VP Operations",
        "process_scope": ["P2P", "O2C"],
        "system_scope": ["SAP_PRD"],
    },
    {
        "approver_id": "APP-LM-002",
        "name": "David Kim",
        "email": "dkim@company.com",
        "approver_type": "LINE_MANAGER",
        "department": "Finance",
        "job_title": "Finance Director",
        "process_scope": ["FI", "CO"],
        "system_scope": ["SAP_PRD", "SAP_QAS"],
    },
    {
        "approver_id": "APP-RO-001",
        "name": "Emily Davis",
        "email": "edavis@company.com",
        "approver_type": "ROLE_OWNER",
        "department": "IT",
        "job_title": "SAP Basis Lead",
        "process_scope": [],
        "system_scope": ["SAP_PRD", "SAP_QAS", "SAP_DEV"],
    },
    {
        "approver_id": "APP-PO-001",
        "name": "Robert Martinez",
        "email": "rmartinez@company.com",
        "approver_type": "PROCESS_OWNER",
        "department": "Procurement",
        "job_title": "Head of Procurement",
        "process_scope": ["P2P", "MM"],
        "system_scope": ["SAP_PRD"],
    },
    {
        "approver_id": "APP-DO-001",
        "name": "Lisa Chen",
        "email": "lchen@company.com",
        "approver_type": "DATA_OWNER",
        "department": "Data Governance",
        "job_title": "Chief Data Officer",
        "process_scope": [],
        "system_scope": [],
    },
    {
        "approver_id": "APP-SO-001",
        "name": "Michael Chen",
        "email": "mchen@company.com",
        "approver_type": "SECURITY_OFFICER",
        "department": "IT Security",
        "job_title": "Sr. Security Analyst",
        "process_scope": [],
        "system_scope": [],
    },
    {
        "approver_id": "APP-CO-001",
        "name": "Patricia Brown",
        "email": "pbrown@company.com",
        "approver_type": "COMPLIANCE_OFFICER",
        "department": "Compliance",
        "job_title": "VP Compliance",
        "process_scope": [],
        "system_scope": [],
    },
    {
        "approver_id": "APP-SYS-001",
        "name": "James Wilson",
        "email": "jwilson@company.com",
        "approver_type": "SYSTEM_OWNER",
        "department": "IT Infrastructure",
        "job_title": "SAP System Manager",
        "process_scope": [],
        "system_scope": ["SAP_PRD", "SAP_QAS"],
    },
    {
        "approver_id": "APP-GD-001",
        "name": "Amanda Taylor",
        "email": "ataylor@company.com",
        "approver_type": "GOVERNANCE_DESK",
        "department": "GRC",
        "job_title": "GRC Manager",
        "process_scope": [],
        "system_scope": [],
    },
    {
        "approver_id": "APP-CISO-001",
        "name": "Thomas Anderson",
        "email": "tanderson@company.com",
        "approver_type": "CISO",
        "department": "Information Security",
        "job_title": "Chief Information Security Officer",
        "process_scope": [],
        "system_scope": [],
    },
    {
        "approver_id": "APP-DEL-001",
        "name": "Jennifer White",
        "email": "jwhite@company.com",
        "approver_type": "DELEGATE",
        "department": "IT Security",
        "job_title": "Security Analyst",
        "process_scope": [],
        "system_scope": [],
    },
]


def seed_approvers(tenant_id: str = "tenant_default", clear: bool = False):
    """Seed approver data into the database."""
    db_manager.init()
    db_manager.create_tables()
    session = db_manager.get_session()

    try:
        if clear:
            deleted = session.query(ApproverModel).filter(
                ApproverModel.tenant_id == tenant_id
            ).delete()
            session.commit()
            print(f"Cleared {deleted} existing approvers for tenant '{tenant_id}'")

        created = 0
        skipped = 0

        for data in DEMO_APPROVERS:
            existing = session.query(ApproverModel).filter(
                ApproverModel.tenant_id == tenant_id,
                ApproverModel.approver_id == data["approver_id"]
            ).first()

            if existing:
                skipped += 1
                continue

            approver = ApproverModel(
                tenant_id=tenant_id,
                status="active",
                is_active=True,
                is_available=True,
                is_ooo=False,
                **data
            )
            session.add(approver)
            created += 1

        session.commit()

        # Summary
        total = session.query(ApproverModel).filter(
            ApproverModel.tenant_id == tenant_id
        ).count()

        print(f"\n{'=' * 50}")
        print("APPROVER SEED SUMMARY")
        print(f"{'=' * 50}")
        print(f"Tenant:    {tenant_id}")
        print(f"Created:   {created}")
        print(f"Skipped:   {skipped} (already exist)")
        print(f"Total:     {total}")
        print(f"{'=' * 50}")

    finally:
        session.close()


def main():
    parser = argparse.ArgumentParser(description="Seed approver data")
    parser.add_argument("--tenant", default="tenant_default", help="Tenant ID")
    parser.add_argument("--clear", action="store_true", help="Clear existing before seeding")
    args = parser.parse_args()

    seed_approvers(tenant_id=args.tenant, clear=args.clear)
    print("\nApprover seeding complete!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
