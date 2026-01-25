#!/usr/bin/env python3
"""
Super Admin Initialization Script
Creates the platform super admin user for GRC Zero Trust Platform

Run this script once during initial setup:
    python scripts/init_super_admin.py

Or with custom credentials:
    python scripts/init_super_admin.py --email admin@yourcompany.com --password YourSecurePassword123!
"""

import argparse
import sys
import os
import hashlib
import secrets
import json
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def hash_password(password: str) -> str:
    """Hash password using SHA-256 with salt"""
    salt = secrets.token_hex(16)
    hashed = hashlib.sha256(f"{salt}{password}".encode()).hexdigest()
    return f"{salt}:{hashed}"


def verify_password(password: str, hashed: str) -> bool:
    """Verify password against hash"""
    salt, hash_value = hashed.split(":")
    return hashlib.sha256(f"{salt}{password}".encode()).hexdigest() == hash_value


def generate_api_key() -> str:
    """Generate secure API key for super admin"""
    return f"grc_super_{secrets.token_hex(32)}"


def create_super_admin(email: str, password: str, name: str = "Super Admin") -> dict:
    """Create super admin user record"""

    api_key = generate_api_key()
    hashed_password = hash_password(password)

    super_admin = {
        "id": "super_admin_001",
        "email": email,
        "password_hash": hashed_password,
        "name": name,
        "role": "super_admin",
        "permissions": [
            "platform:manage",
            "tenants:create",
            "tenants:read",
            "tenants:update",
            "tenants:delete",
            "tenants:suspend",
            "users:manage_all",
            "billing:manage",
            "system:configure",
            "audit:read_all",
            "support:access"
        ],
        "api_key": api_key,
        "created_at": datetime.utcnow().isoformat(),
        "is_active": True,
        "mfa_enabled": False,
        "last_login": None,
        "login_count": 0
    }

    return super_admin


def save_super_admin(admin_data: dict, config_dir: str = None) -> str:
    """Save super admin to configuration file"""

    if config_dir is None:
        config_dir = Path(__file__).parent.parent / "config"
    else:
        config_dir = Path(config_dir)

    config_dir.mkdir(parents=True, exist_ok=True)

    admin_file = config_dir / "super_admin.json"

    # Remove sensitive data for display
    display_data = {k: v for k, v in admin_data.items() if k != "password_hash"}

    with open(admin_file, 'w') as f:
        json.dump(admin_data, f, indent=2)

    # Set restrictive permissions on Unix systems
    if os.name != 'nt':
        os.chmod(admin_file, 0o600)

    return str(admin_file)


def load_super_admin(config_dir: str = None) -> dict:
    """Load existing super admin configuration"""

    if config_dir is None:
        config_dir = Path(__file__).parent.parent / "config"
    else:
        config_dir = Path(config_dir)

    admin_file = config_dir / "super_admin.json"

    if admin_file.exists():
        with open(admin_file, 'r') as f:
            return json.load(f)

    return None


def main():
    parser = argparse.ArgumentParser(
        description="Initialize GRC Zero Trust Platform Super Admin"
    )
    parser.add_argument(
        "--email",
        default="admin@governex.local",
        help="Super admin email (default: admin@governex.local)"
    )
    parser.add_argument(
        "--password",
        default=None,
        help="Super admin password (auto-generated if not provided)"
    )
    parser.add_argument(
        "--name",
        default="Platform Administrator",
        help="Super admin display name"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing super admin"
    )
    parser.add_argument(
        "--config-dir",
        default=None,
        help="Configuration directory path"
    )

    args = parser.parse_args()

    print("=" * 60)
    print("GRC Zero Trust Platform - Super Admin Setup")
    print("=" * 60)
    print()

    # Check for existing admin
    existing = load_super_admin(args.config_dir)
    if existing and not args.force:
        print("ERROR: Super admin already exists!")
        print(f"       Email: {existing.get('email')}")
        print()
        print("Use --force to overwrite existing admin configuration.")
        print()
        return 1

    # Generate password if not provided
    if args.password:
        password = args.password
        print("Using provided password")
    else:
        password = secrets.token_urlsafe(16)
        print("Generated secure password")

    # Create super admin
    admin_data = create_super_admin(
        email=args.email,
        password=password,
        name=args.name
    )

    # Save to file
    config_file = save_super_admin(admin_data, args.config_dir)

    print()
    print("-" * 60)
    print("SUPER ADMIN CREATED SUCCESSFULLY")
    print("-" * 60)
    print()
    print(f"  Email:     {args.email}")
    print(f"  Password:  {password}")
    print(f"  Name:      {args.name}")
    print(f"  API Key:   {admin_data['api_key']}")
    print()
    print(f"  Config:    {config_file}")
    print()
    print("-" * 60)
    print("IMPORTANT: Save these credentials securely!")
    print("          This password will not be displayed again.")
    print("-" * 60)
    print()
    print("Login at: http://localhost:5173/admin")
    print()
    print("Permissions granted:")
    for perm in admin_data['permissions']:
        print(f"  - {perm}")
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
