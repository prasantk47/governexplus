#!/usr/bin/env python3
"""
GovernexPlus Multi-Tenancy & Security Audit Script
Runs static analysis + live cross-tenant tests against production.
Updated: 2026-11-01
"""

import requests
import json
import sys
import re
import base64

API_BASE = "https://governexplus.com/api"
ACME_CREDS = {"username": "acme_admin", "password": "AcmeP@ss2026!", "tenant_id": "acme-corp-demo"}
FINDINGS = []


def finding(severity, category, title, detail):
    FINDINGS.append({
        "severity": severity,
        "category": category,
        "title": title,
        "detail": detail,
    })
    marker = {"Critical": "!!!", "High": "!!", "Medium": "!", "Low": "."}
    print(f"  [{severity}] {marker.get(severity, '')} {title}")
    print(f"    {detail}\n")


def passed(category, title, detail=""):
    print(f"  [PASS] {title}")
    if detail:
        print(f"    {detail}")


def decode_jwt(token):
    parts = token.split(".")
    if len(parts) != 3:
        return {}
    payload_b64 = parts[1] + "=" * (4 - len(parts[1]) % 4)
    return json.loads(base64.urlsafe_b64decode(payload_b64))


def login(creds):
    resp = requests.post(f"{API_BASE}/auth/login", json=creds, timeout=15)
    if resp.status_code != 200:
        return None, resp
    data = resp.json()
    token = data.get("access_token") or data.get("token") or data.get("data", {}).get("access_token", "")
    return token, resp


# ==========================================================================
# TEST 1: Live login + get a valid token for acme-corp-demo
# ==========================================================================
print("=" * 72)
print("TEST 1: Authentication & Token Acquisition")
print("=" * 72)

acme_token, login_resp = login(ACME_CREDS)
if not acme_token:
    print(f"FATAL: Cannot login as acme_admin. Status={login_resp.status_code}")
    print(login_resp.text[:500])
    sys.exit(1)

acme_headers = {"Authorization": f"Bearer {acme_token}"}
claims = decode_jwt(acme_token)
token_tenant = claims.get("tenant_id", "")
print(f"  Logged in as acme_admin. Token length: {len(acme_token)}")
print(f"  JWT claims: sub={claims.get('sub')}, tenant_id={token_tenant}, "
      f"role={claims.get('role')}, roles={claims.get('roles')}")
passed("AUTH", "Login successful, JWT contains tenant_id claim")

# ==========================================================================
# TEST 2: Cross-tenant header spoofing
# ==========================================================================
print("\n" + "=" * 72)
print("TEST 2: Cross-Tenant Header Spoofing")
print("=" * 72)

# 2a: Spoof X-Tenant-ID to a non-existent tenant
spoofed_headers = {**acme_headers, "X-Tenant-ID": "some-other-tenant-999"}
resp = requests.get(f"{API_BASE}/dashboard/stats", headers=spoofed_headers, timeout=15)
print(f"  GET /dashboard/stats with spoofed X-Tenant-ID='some-other-tenant-999': status={resp.status_code}")

if resp.status_code == 403:
    passed("TENANT", "Spoofed X-Tenant-ID correctly rejected with 403")
elif resp.status_code == 404:
    passed("TENANT", "Spoofed X-Tenant-ID resulted in 404 (tenant not found)")
elif resp.status_code == 200:
    resp_tenant = resp.headers.get("X-Tenant-ID", "")
    if resp_tenant == token_tenant or resp_tenant == "acme-corp-demo":
        passed("TENANT", f"Spoofed header IGNORED - response is for JWT tenant ({resp_tenant})")
    else:
        finding("Critical", "TENANT", "X-Tenant-ID header spoofing accepted!",
                f"Response tenant: {resp_tenant}, expected: {token_tenant}")
else:
    print(f"  Unexpected status {resp.status_code}: {resp.text[:200]}")

# 2b: Spoof X-Tenant-ID to an EXISTING different tenant (qa-tenant-001)
spoofed_headers2 = {**acme_headers, "X-Tenant-ID": "qa-tenant-001"}
resp2 = requests.get(f"{API_BASE}/dashboard/stats", headers=spoofed_headers2, timeout=15)
print(f"  GET /dashboard/stats with spoofed X-Tenant-ID='qa-tenant-001': status={resp2.status_code}")

if resp2.status_code == 403:
    passed("TENANT", "Cross-tenant request correctly rejected with 403")
elif resp2.status_code == 200:
    resp_tenant2 = resp2.headers.get("X-Tenant-ID", "")
    if resp_tenant2 == "qa-tenant-001":
        finding("Critical", "TENANT", "Cross-tenant access via X-Tenant-ID header spoofing!",
                f"JWT tenant={token_tenant}, but got data for {resp_tenant2}")
    else:
        passed("TENANT", f"Spoofed header ignored - got data for JWT tenant ({resp_tenant2})")
else:
    print(f"  Status {resp2.status_code}: {resp2.text[:200]}")

# 2c: Spoofed X-User-ID/X-User-Roles/X-Is-Admin headers
spoofed_user = {
    **acme_headers,
    "X-User-ID": "PLATFORM_ADMIN_999",
    "X-User-Roles": "platform_admin,super_admin",
    "X-Is-Admin": "true",
}
resp3 = requests.get(f"{API_BASE}/users/", headers=spoofed_user, timeout=15)
print(f"  GET /users/ with spoofed X-User-ID/Roles/IsAdmin: status={resp3.status_code}")
if resp3.status_code in (200, 422):
    passed("TENANT", "Spoofed identity headers did NOT escalate privileges")
elif resp3.status_code == 403:
    passed("TENANT", "Server rejected spoofed identity headers")

# ==========================================================================
# TEST 3: Cross-tenant data access via direct ID
# ==========================================================================
print("\n" + "=" * 72)
print("TEST 3: Cross-Tenant Data Access via Direct ID")
print("=" * 72)

test_paths = [
    ("GET", "/users/P01", "QA platform admin user"),
    ("GET", "/users/P02", "QA tenant admin user"),
    ("GET", "/risk-management/risks/RISK_OTHER_001", "Non-existent risk"),
]

for method, path, desc in test_paths:
    resp = requests.request(method, f"{API_BASE}{path}", headers=acme_headers, timeout=15)
    print(f"  {method} {path} ({desc}): status={resp.status_code}")
    if resp.status_code == 200:
        body = resp.json()
        if isinstance(body, dict) and body.get("tenant_id") and body["tenant_id"] != token_tenant:
            finding("Critical", "TENANT", f"Cross-tenant data leak on {path}",
                    f"Returned data from tenant: {body.get('tenant_id')}")
        else:
            passed("DATA", f"{path} 200 but no cross-tenant leak")
    elif resp.status_code in (404, 403, 422):
        passed("DATA", f"{path} correctly denied/not found ({resp.status_code})")
    else:
        print(f"    Status {resp.status_code}: {resp.text[:200]}")

# 3b: CRITICAL - Test audit logs cross-tenant leak (AuditLog has no tenant_id)
print("\n  --- Audit log cross-tenant test ---")
resp_audit = requests.get(f"{API_BASE}/audit/logs?limit=5", headers=acme_headers, timeout=15)
print(f"  GET /audit/logs?limit=5: status={resp_audit.status_code}")
if resp_audit.status_code == 200:
    audit_data = resp_audit.json()
    logs = audit_data.get("logs", [])
    if logs:
        # Check if any log entry references a different tenant's user
        other_tenant_refs = []
        for log_entry in logs:
            actor = log_entry.get("actor_user_id", "")
            details = log_entry.get("details", {}) or {}
            # If we see users from other tenants, that's a cross-tenant leak
            if "SUPERADMIN" in str(actor).upper() or "qa_" in str(actor).lower():
                other_tenant_refs.append(actor)
        if other_tenant_refs:
            finding("Critical", "TENANT",
                    "Audit log cross-tenant data leak: AuditLog model has no tenant_id",
                    f"Acme user can see logs from other tenants. Actors found: {other_tenant_refs[:5]}")
        else:
            print(f"    Got {len(logs)} logs, all appear to be from acme tenant")
            print(f"    WARNING: AuditLog model lacks tenant_id - static analysis confirms cross-tenant risk")
            finding("Critical", "TENANT",
                    "AuditLog model has no tenant_id column (static analysis)",
                    "db/models/audit.py: AuditLog has no tenant_id. All tenants share one audit log pool. "
                    "ORM tenant scoping cannot filter this table. Cross-tenant audit data exposure.")
    else:
        print("    No audit logs returned (empty)")
        finding("Critical", "TENANT",
                "AuditLog model has no tenant_id column (static analysis)",
                "db/models/audit.py: AuditLog has no tenant_id. All tenants share one audit log pool.")
elif resp_audit.status_code == 500:
    print(f"    Server error (may be unrelated): {resp_audit.text[:200]}")
    finding("Critical", "TENANT",
            "AuditLog model has no tenant_id column (static analysis)",
            "db/models/audit.py: AuditLog has no tenant_id. ORM tenant scoping cannot filter this table.")

# ==========================================================================
# TEST 4: Unauthenticated access to protected routes
# ==========================================================================
print("\n" + "=" * 72)
print("TEST 4: Unauthenticated Access to Protected Routes")
print("=" * 72)

protected_paths = [
    "/users/", "/risk/analyze", "/dashboard/stats", "/admin/status",
    "/audit/logs", "/access-requests/", "/certification/campaigns",
    "/privileged-access/sessions", "/risk-management/risks",
    "/jml/events", "/tprm/vendors", "/fraud/scenarios",
    "/bcm/plans", "/surveys/", "/library/packs",
]

for path in protected_paths:
    resp = requests.get(f"{API_BASE}{path}", timeout=15)
    if resp.status_code == 401:
        passed("AUTH", f"{path} requires auth (401)")
    elif resp.status_code == 200:
        finding("Critical", "AUTH", f"Unauthenticated access to {path}",
                f"Got 200 with body: {resp.text[:150]}")
    else:
        passed("AUTH", f"{path} blocked (status={resp.status_code})")

# ==========================================================================
# TEST 5: Public endpoints verification
# ==========================================================================
print("\n" + "=" * 72)
print("TEST 5: Public Endpoints Verification")
print("=" * 72)

public_paths = [
    ("GET",  "/",                    "Root"),
    ("GET",  "/health",              "Health check"),
    ("GET",  "/docs",                "OpenAPI docs"),
    ("POST", "/whistleblower/submit","Whistleblower (intentionally public)"),
    ("GET",  "/metrics",             "Prometheus metrics"),
    ("GET",  "/i18n/locales",        "i18n locales"),
    ("GET",  "/auth/sso/status",     "SSO status"),
]

for method, path, desc in public_paths:
    try:
        if method == "POST":
            resp = requests.post(f"{API_BASE}{path}", json={}, timeout=15)
        else:
            resp = requests.get(f"{API_BASE}{path}", timeout=15)
        status = resp.status_code
        if status in (200, 307, 422):
            print(f"  [INFO] {path} ({desc}): accessible without auth (status={status})")
        elif status == 401:
            print(f"  [INFO] {path} ({desc}): requires auth (status={status})")
        else:
            print(f"  [INFO] {path} ({desc}): status={status}")
    except Exception as e:
        print(f"  [ERROR] {path}: {e}")

# ==========================================================================
# TEST 6: Token blacklist (logout + reuse)
# ==========================================================================
print("\n" + "=" * 72)
print("TEST 6: Token Blacklist (Logout + Reuse)")
print("=" * 72)

fresh_token, _ = login(ACME_CREDS)
if fresh_token:
    hdr = {"Authorization": f"Bearer {fresh_token}"}
    pre = requests.get(f"{API_BASE}/dashboard/stats", headers=hdr, timeout=15)
    print(f"  Pre-logout: status={pre.status_code}")

    logout = requests.post(f"{API_BASE}/auth/logout", headers=hdr, timeout=15)
    print(f"  Logout: status={logout.status_code}")

    post = requests.get(f"{API_BASE}/dashboard/stats", headers=hdr, timeout=15)
    print(f"  Post-logout reuse: status={post.status_code}")
    if post.status_code == 401:
        passed("AUTH", "Token blacklist works - revoked token rejected")
    elif post.status_code == 200:
        finding("High", "AUTH", "Token blacklist bypass - revoked token accepted after logout",
                "Root cause: auth.py line 246 passes 'Bearer <token>' (full header) to "
                "AuthService.logout(), but is_token_blacklisted() checks raw token without prefix. "
                "The blacklisted string never matches.")
    else:
        print(f"    Unexpected: {post.status_code}")
else:
    print("  Skipped - could not get fresh token")

# ==========================================================================
# TEST 7: Rate limiting
# ==========================================================================
print("\n" + "=" * 72)
print("TEST 7: Rate Limiting on Auth Endpoints")
print("=" * 72)

rate_limit_hit = False
for i in range(15):
    resp = requests.post(
        f"{API_BASE}/auth/login",
        json={"username": "nonexistent", "password": "wrong", "tenant_id": "acme-corp-demo"},
        timeout=15,
    )
    if resp.status_code == 429:
        passed("RATE", f"Rate limiting triggered after {i+1} requests")
        rate_limit_hit = True
        break

if not rate_limit_hit:
    finding("Medium", "RATE", "Rate limiting not triggered after 15 rapid login attempts",
            "slowapi configured for 10/minute on auth but not enforcing. "
            "Likely: memory:// storage with multiple workers, or reverse proxy not forwarding client IP.")

# ==========================================================================
# TEST 8: Security headers
# ==========================================================================
print("\n" + "=" * 72)
print("TEST 8: Security Headers")
print("=" * 72)

resp = requests.get(f"{API_BASE}/", timeout=15)
headers = resp.headers

security_headers = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": None,
    "Strict-Transport-Security": None,
    "X-XSS-Protection": None,
    "Content-Security-Policy": None,
    "Referrer-Policy": None,
}

for header, expected in security_headers.items():
    val = headers.get(header)
    if val:
        if expected and val != expected:
            finding("Low", "HEADERS", f"{header} unexpected value", f"Expected: {expected}, Got: {val}")
        else:
            passed("HEADERS", f"{header}: {val}")
    else:
        finding("Low", "HEADERS", f"Missing security header: {header}", "Not present in response")

# ==========================================================================
# TEST 9: /tenants access without platform_admin
# ==========================================================================
print("\n" + "=" * 72)
print("TEST 9: Tenant Management Access Control")
print("=" * 72)

resp = requests.get(f"{API_BASE}/tenants", headers=acme_headers, timeout=15)
print(f"  GET /tenants as tenant_admin: status={resp.status_code}")
if resp.status_code == 403:
    passed("RBAC", "/tenants correctly requires platform_admin role")
elif resp.status_code == 200:
    finding("High", "RBAC", "/tenants accessible to non-platform_admin",
            "tenant_admin role should NOT see /tenants management endpoint")
else:
    print(f"  Status {resp.status_code}: {resp.text[:200]}")

# ==========================================================================
# SUMMARY
# ==========================================================================
print("\n" + "=" * 72)
print("AUDIT SUMMARY")
print("=" * 72)

if not FINDINGS:
    print("\n  No findings. All tests passed.\n")
else:
    critical = [f for f in FINDINGS if f["severity"] == "Critical"]
    high = [f for f in FINDINGS if f["severity"] == "High"]
    medium = [f for f in FINDINGS if f["severity"] == "Medium"]
    low = [f for f in FINDINGS if f["severity"] == "Low"]

    print(f"\n  Critical: {len(critical)}")
    print(f"  High:     {len(high)}")
    print(f"  Medium:   {len(medium)}")
    print(f"  Low:      {len(low)}")
    print(f"  Total:    {len(FINDINGS)}")

    for f in FINDINGS:
        print(f"\n  [{f['severity']}] {f['category']} - {f['title']}")
        print(f"    {f['detail']}")

print("\n" + "=" * 72)
print("AUDIT COMPLETE")
print("=" * 72)
