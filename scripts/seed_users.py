#!/usr/bin/env python3
"""
User Seed Script

Populates the database with initial user data for testing and demo purposes.
Creates users across multiple departments with varying risk levels and statuses.

Run:
    python scripts/seed_users.py
    python scripts/seed_users.py --tenant tenant_acme --count 50
    python scripts/seed_users.py --clear  # Clear existing users first
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
from db.models.user import User, Role, UserRole, UserType, UserStatus


# Sample data pools
FIRST_NAMES = [
    "John", "Jane", "Michael", "Sarah", "David", "Emily", "Robert", "Lisa",
    "William", "Jennifer", "James", "Maria", "Thomas", "Patricia", "Charles",
    "Linda", "Daniel", "Elizabeth", "Matthew", "Barbara", "Anthony", "Susan",
    "Richard", "Jessica", "Mark", "Karen", "Steven", "Nancy", "Paul", "Betty",
    "Andrew", "Margaret", "Joshua", "Sandra", "Kenneth", "Ashley", "Kevin", "Dorothy"
]

LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
    "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson",
    "Thomas", "Taylor", "Moore", "Jackson", "Martin", "Lee", "Perez", "Thompson",
    "White", "Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson", "Walker",
    "Young", "Allen", "King", "Wright", "Scott", "Torres", "Nguyen", "Hill", "Flores"
]

DEPARTMENTS = [
    "Finance", "IT Operations", "Human Resources", "Sales", "Marketing",
    "Procurement", "Legal & Compliance", "Operations", "Engineering",
    "Customer Support", "Research & Development", "Quality Assurance"
]

LOCATIONS = [
    "New York", "London", "Singapore", "Frankfurt", "Tokyo", "Sydney",
    "San Francisco", "Chicago", "Mumbai", "Dubai", "Toronto", "Paris"
]

# SAP-style roles for demo
ROLES_DATA = [
    {"role_id": "SAP_FI_DISPLAY", "role_name": "Finance Display", "risk_level": "low"},
    {"role_id": "SAP_FI_POST", "role_name": "Finance Posting", "risk_level": "medium"},
    {"role_id": "SAP_FI_ADMIN", "role_name": "Finance Administrator", "risk_level": "high"},
    {"role_id": "SAP_MM_DISPLAY", "role_name": "Materials Display", "risk_level": "low"},
    {"role_id": "SAP_MM_CREATE_PO", "role_name": "Create Purchase Order", "risk_level": "medium"},
    {"role_id": "SAP_MM_RELEASE_PO", "role_name": "Release Purchase Order", "risk_level": "high"},
    {"role_id": "SAP_HR_DISPLAY", "role_name": "HR Display", "risk_level": "low"},
    {"role_id": "SAP_HR_MAINTAIN", "role_name": "HR Maintenance", "risk_level": "high"},
    {"role_id": "SAP_SD_DISPLAY", "role_name": "Sales Display", "risk_level": "low"},
    {"role_id": "SAP_SD_CREATE_SO", "role_name": "Create Sales Order", "risk_level": "medium"},
    {"role_id": "SAP_BASIS_ADMIN", "role_name": "Basis Administrator", "risk_level": "critical"},
    {"role_id": "SAP_SECURITY_ADMIN", "role_name": "Security Administrator", "risk_level": "critical"},
]


def generate_user_id(first_name: str, last_name: str, existing_ids: set) -> str:
    """Generate a unique user ID"""
    base_id = f"{first_name[0].lower()}{last_name.lower()}"[:12]
    user_id = base_id
    counter = 1
    while user_id in existing_ids:
        user_id = f"{base_id}{counter}"
        counter += 1
    return user_id


def generate_email(first_name: str, last_name: str, domain: str = "company.com") -> str:
    """Generate email address"""
    return f"{first_name.lower()}.{last_name.lower()}@{domain}"


def generate_risk_score(user_type: UserType, role_count: int, has_high_risk: bool) -> float:
    """Generate risk score based on user attributes"""
    base_score = random.uniform(5, 25)

    if user_type == UserType.SERVICE:
        base_score += random.uniform(10, 20)
    elif user_type == UserType.SYSTEM:
        base_score += random.uniform(15, 30)

    base_score += role_count * random.uniform(2, 5)

    if has_high_risk:
        base_score += random.uniform(20, 40)

    return min(base_score, 100)


def create_users(
    session,
    tenant_id: str,
    count: int = 30,
    clear_existing: bool = False
):
    """Create seed users in the database"""

    if clear_existing:
        print(f"Clearing existing users for tenant {tenant_id}...")
        session.query(UserRole).filter(UserRole.tenant_id == tenant_id).delete()
        session.query(User).filter(User.tenant_id == tenant_id).delete()
        session.query(Role).filter(Role.tenant_id == tenant_id).delete()
        session.commit()
        print("Existing data cleared.")

    # Create roles first
    print("Creating roles...")
    roles = []
    for role_data in ROLES_DATA:
        existing_role = session.query(Role).filter(
            Role.tenant_id == tenant_id,
            Role.role_id == role_data["role_id"]
        ).first()

        if not existing_role:
            role = Role(
                tenant_id=tenant_id,
                role_id=role_data["role_id"],
                role_name=role_data["role_name"],
                description=f"SAP role for {role_data['role_name']}",
                risk_level=role_data["risk_level"],
                is_sensitive=role_data["risk_level"] in ["high", "critical"],
                is_active=True,
                source_system="SAP"
            )
            session.add(role)
            roles.append(role)
        else:
            roles.append(existing_role)

    session.commit()
    print(f"Created {len([r for r in roles if r.id is None])} new roles (+ existing)")

    # Reload roles to get IDs
    roles = session.query(Role).filter(Role.tenant_id == tenant_id).all()

    # Create users
    print(f"Creating {count} users...")
    existing_ids = set(
        r[0] for r in session.query(User.user_id).filter(
            User.tenant_id == tenant_id
        ).all()
    )

    users_created = 0
    for i in range(count):
        first_name = random.choice(FIRST_NAMES)
        last_name = random.choice(LAST_NAMES)
        user_id = generate_user_id(first_name, last_name, existing_ids)
        existing_ids.add(user_id)

        # Determine user type (mostly dialog, some service accounts)
        user_type_weights = [
            (UserType.DIALOG, 0.85),
            (UserType.SERVICE, 0.10),
            (UserType.SYSTEM, 0.03),
            (UserType.COMMUNICATION, 0.02)
        ]
        user_type = random.choices(
            [t[0] for t in user_type_weights],
            weights=[t[1] for t in user_type_weights]
        )[0]

        # Determine status (mostly active)
        status_weights = [
            (UserStatus.ACTIVE, 0.80),
            (UserStatus.LOCKED, 0.08),
            (UserStatus.DISABLED, 0.07),
            (UserStatus.EXPIRED, 0.05)
        ]
        status = random.choices(
            [s[0] for s in status_weights],
            weights=[s[1] for s in status_weights]
        )[0]

        department = random.choice(DEPARTMENTS)
        location = random.choice(LOCATIONS)

        # Generate dates
        created_days_ago = random.randint(30, 730)
        created_at = datetime.utcnow() - timedelta(days=created_days_ago)

        last_login = None
        if status == UserStatus.ACTIVE:
            login_days_ago = random.randint(0, 30)
            last_login = datetime.utcnow() - timedelta(days=login_days_ago)

        # Assign random roles
        num_roles = random.randint(1, 5)
        user_roles = random.sample(roles, min(num_roles, len(roles)))
        has_high_risk = any(r.risk_level in ["high", "critical"] for r in user_roles)

        # Generate violation count
        violation_count = 0
        if has_high_risk and random.random() < 0.3:
            violation_count = random.randint(1, 5)

        risk_score = generate_risk_score(user_type, len(user_roles), has_high_risk)

        user = User(
            tenant_id=tenant_id,
            user_id=user_id,
            username=user_id,
            email=generate_email(first_name, last_name),
            full_name=f"{first_name} {last_name}",
            department=department,
            location=location,
            cost_center=f"CC{random.randint(1000, 9999)}",
            company_code=f"CC{random.randint(10, 99)}",
            user_type=user_type,
            status=status,
            source_system="SAP",
            system_client="100",
            risk_score=round(risk_score, 1),
            violation_count=violation_count,
            last_login=last_login,
            created_at=created_at,
            updated_at=datetime.utcnow()
        )
        session.add(user)
        session.flush()  # Get user ID

        # Create role assignments
        for role in user_roles:
            user_role = UserRole(
                tenant_id=tenant_id,
                user_id=user.id,
                role_id=role.id,
                assigned_by="system",
                assigned_at=created_at + timedelta(days=random.randint(0, 30)),
                valid_from=created_at,
                is_active=True
            )
            session.add(user_role)

        users_created += 1
        if users_created % 10 == 0:
            print(f"  Created {users_created}/{count} users...")

    session.commit()
    print(f"Successfully created {users_created} users")

    # Print summary
    print("\n" + "=" * 60)
    print("SEED DATA SUMMARY")
    print("=" * 60)

    total_users = session.query(User).filter(User.tenant_id == tenant_id).count()
    active_users = session.query(User).filter(
        User.tenant_id == tenant_id,
        User.status == UserStatus.ACTIVE
    ).count()
    high_risk = session.query(User).filter(
        User.tenant_id == tenant_id,
        User.risk_score >= 60
    ).count()
    with_violations = session.query(User).filter(
        User.tenant_id == tenant_id,
        User.violation_count > 0
    ).count()

    print(f"  Tenant:         {tenant_id}")
    print(f"  Total Users:    {total_users}")
    print(f"  Active Users:   {active_users}")
    print(f"  High Risk:      {high_risk}")
    print(f"  With Violations: {with_violations}")
    print(f"  Roles Created:  {len(roles)}")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="Seed database with test users"
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
        help="Number of users to create (default: 30)"
    )
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Clear existing users before seeding"
    )
    parser.add_argument(
        "--db-url",
        default=None,
        help="Database URL (default: from DATABASE_URL env var)"
    )

    args = parser.parse_args()

    print("=" * 60)
    print("Governex+ User Seed Script")
    print("=" * 60)

    # Initialize database
    if args.db_url:
        os.environ['DATABASE_URL'] = args.db_url

    db_manager.init()
    db_manager.create_tables()

    print(f"Database: {db_manager.database_url.split('@')[-1] if '@' in db_manager.database_url else db_manager.database_url}")
    print()

    # Create users
    with db_manager.session_scope() as session:
        create_users(
            session,
            tenant_id=args.tenant,
            count=args.count,
            clear_existing=args.clear
        )

    print("\nSeeding complete!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
