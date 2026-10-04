"""
QA Environment Seeder
=====================
Seeds the 16 test personas, a demo tenant, and mock connector configs
into the QA database. Safe to re-run — uses upsert logic.

Usage:
    # From repo root (with QA stack running):
    python qa/seed_qa.py

    # Or via the API (when stack is healthy):
    python qa/seed_qa.py --via-api http://localhost:9000
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import uuid
from pathlib import Path

# ── Paths ────────────────────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).parent.parent
PERSONAS_FILE = Path(__file__).parent / "personas.json"

sys.path.insert(0, str(REPO_ROOT))


def seed_via_db() -> None:
    """Direct DB seeding — requires DATABASE_URL in env."""
    os.environ.setdefault(
        "DATABASE_URL",
        "postgresql://grc_user:grc_qa_password@localhost:5432/grc_qa",
    )
    os.environ.setdefault("APP_ENV", "testing")
    os.environ.setdefault("JWT_SECRET", "qa-jwt-secret-do-not-use-in-production")

    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import sessionmaker

    from db.models import Base
    from db.models.user import User
    from services.auth_service import AuthService

    data = json.loads(PERSONAS_FILE.read_text(encoding="utf-8"))
    tenant_id = data["tenant_id"]
    personas = data["personas"]

    db_url = os.environ["DATABASE_URL"]
    engine = create_engine(db_url)
    Base.metadata.create_all(bind=engine)

    Session = sessionmaker(bind=engine)
    db = Session()

    inserted = 0
    updated = 0
    errors = []

    for p in personas:
        try:
            existing = db.query(User).filter_by(username=p["username"], tenant_id=tenant_id).first()
            pw_hash = AuthService.hash_password(p["password"])

            if existing is None:
                user = User(
                    user_id=p["persona_id"],
                    username=p["username"],
                    email=p["email"],
                    full_name=p["full_name"],
                    department=p["department"],
                    status="active",
                    password_hash=pw_hash,
                    tenant_id=tenant_id,
                    user_type=p.get("user_type", "standard"),
                )
                db.add(user)
                inserted += 1
                action = "inserted"
            else:
                existing.email = p["email"]
                existing.full_name = p["full_name"]
                existing.department = p["department"]
                existing.status = "active"
                existing.password_hash = pw_hash
                existing.user_type = p.get("user_type", "standard")
                updated += 1
                action = "updated"

            db.commit()
            print(f"  [{p['persona_id']}] {p['role']:30s} {action}")

        except Exception as exc:
            db.rollback()
            msg = f"  [{p['persona_id']}] FAILED: {exc}"
            errors.append(msg)
            print(msg)

    db.close()
    print(f"\nDone: {inserted} inserted, {updated} updated, {len(errors)} errors")
    if errors:
        sys.exit(1)


def seed_via_api(base_url: str) -> None:
    """Seed via API — requires the stack to be healthy and an admin token."""
    import http.client
    import urllib.parse

    print(f"Seeding via API at {base_url} ...")

    data = json.loads(PERSONAS_FILE.read_text(encoding="utf-8"))
    tenant_id = data["tenant_id"]
    personas = data["personas"]

    # Step 1: get admin token (uses platform_admin credentials)
    admin = next(p for p in personas if p["persona_id"] == "P01")

    parsed = urllib.parse.urlparse(base_url)
    host = parsed.netloc
    conn = http.client.HTTPConnection(host, timeout=10)

    payload = json.dumps({"username": admin["username"], "password": admin["password"]})
    conn.request("POST", "/auth/login", payload, {"Content-Type": "application/json"})
    resp = conn.getresponse()
    if resp.status != 200:
        print(f"  Admin login failed: {resp.status} — seed the platform admin first via DB")
        sys.exit(1)

    token = json.loads(resp.read())["access_token"]
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
        "X-Tenant-ID": tenant_id,
    }

    for p in personas:
        if p["persona_id"] == "P01":
            continue  # admin already exists

        body = json.dumps({
            "user_id": p["persona_id"],
            "username": p["username"],
            "email": p["email"],
            "full_name": p["full_name"],
            "department": p["department"],
            "password": p["password"],
            "user_type": p.get("user_type", "standard"),
            "roles": p.get("roles", []),
        })
        conn.request("POST", "/auth/register", body, headers)
        resp = conn.getresponse()
        _ = resp.read()
        status = "ok" if resp.status in (200, 201, 409) else f"FAIL({resp.status})"
        print(f"  [{p['persona_id']}] {p['role']:30s} {status}")

    conn.close()
    print("\nDone.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed QA test personas")
    parser.add_argument(
        "--via-api",
        metavar="BASE_URL",
        help="Seed via API instead of direct DB (e.g. http://localhost:9000)",
    )
    args = parser.parse_args()

    print(f"GovernexPlus QA Seeder — {PERSONAS_FILE.name}")
    print("=" * 60)

    personas = json.loads(PERSONAS_FILE.read_text(encoding="utf-8"))
    print(f"Tenant: {personas['tenant_id']}")
    print(f"Personas: {len(personas['personas'])}")
    print()

    if args.via_api:
        seed_via_api(args.via_api)
    else:
        seed_via_db()


if __name__ == "__main__":
    main()
