#!/usr/bin/env python3
"""Quick login test against Docker API."""
import urllib.request, json, sys

API = "http://localhost:9000"

def try_login(username, password, tenant_id):
    data = json.dumps({"username": username, "password": password, "tenant_id": tenant_id}).encode()
    req = urllib.request.Request(f"{API}/auth/login", data=data, headers={"Content-Type": "application/json"})
    try:
        resp = urllib.request.urlopen(req)
        d = json.loads(resp.read())
        print(f"  OK: {username} -> token={d.get('access_token','')[:40]}...")
        return True
    except Exception as e:
        body = e.read().decode()[:200] if hasattr(e, "read") else str(e)
        print(f"  FAIL: {username} -> {body}")
        return False

tenants = ["qa-tenant-001", "gvnx", "tenant_default"]
users = [
    ("qa_platform_admin", "QaP@ss2026!Platform"),
    ("qa_tenant_admin", "QaP@ss2026!Tenant"),
    ("qa_requestor", "QaP@ss2026!Request"),
]

for t in tenants:
    print(f"\nTenant: {t}")
    for u, p in users:
        try_login(u, p, t)
