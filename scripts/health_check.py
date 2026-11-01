#!/usr/bin/env python3
"""GovernexPlus Production API Health Check"""

import urllib.request
import urllib.error
import json
import ssl

BASE = "https://governexplus.com/api"
TIMEOUT = 15

# Disable SSL verification if needed
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

ENDPOINTS = [
    "/dashboard/summary",
    "/dashboard/stats",
    "/users",
    "/access-requests",
    "/approvals",
    "/certification/campaigns",
    "/certification/statistics",
    "/privileged-access/dashboard",
    "/risk/dashboard",
    "/risk/rules",
    "/risk-rules",
    "/risk-management/risks",
    "/risk-management/kris",
    "/risk-management/workflows",
    "/risk-management/heatmap",
    "/risk-management/incidents",
    "/process-control/controls",
    "/process-control/tests",
    "/process-control/deficiencies",
    "/audit-management/plans",
    "/audit-management/engagements",
    "/audit-management/findings",
    "/audit/violations",
    "/tprm/vendors",
    "/tprm/issues",
    "/jml/events",
    "/jml/policies",
    "/bcm/plans",
    "/bcm/activations",
    "/bcm/dashboard",
    "/fraud/rules",
    "/fraud/alerts",
    "/fraud/cases",
    "/fraud/dashboard",
    "/whistleblower/cases",
    "/whistleblower/dashboard",
    "/surveys",
    "/library/packs",
    "/library/items",
    "/access-reports/summary",
    "/integrations",
    "/integrations/connectors",
    "/workflows",
    "/notifications",
    "/reports",
    "/settings/smtp",
    "/role-studio/roles",
    "/mitigation/controls",
    "/security-controls",
    "/provisioning/requests",
    "/intelligence/search",
    "/ai/copilot/status",
]

def login():
    url = f"{BASE}/auth/login"
    payload = json.dumps({
        "username": "acme_admin",
        "password": "AcmeP@ss2026!",
        "tenant_id": "acme-corp-demo"
    }).encode()
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"}, method="POST")
    try:
        resp = urllib.request.urlopen(req, timeout=TIMEOUT, context=ctx)
        body = json.loads(resp.read().decode())
        token = body.get("access_token") or body.get("token")
        print(f"[LOGIN] OK - token: {token[:40]}...")
        return token
    except Exception as e:
        print(f"[LOGIN] FAILED: {e}")
        if hasattr(e, 'read'):
            print(f"  Body: {e.read().decode()[:200]}")
        return None

def test_endpoint(path, token):
    url = f"{BASE}{path}"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    req = urllib.request.Request(url, headers=headers, method="GET")
    try:
        resp = urllib.request.urlopen(req, timeout=TIMEOUT, context=ctx)
        body = resp.read().decode()
        return resp.getcode(), body[:100]
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode()[:100]
        except:
            pass
        return e.code, body
    except Exception as e:
        return 0, str(e)[:100]

def main():
    token = login()
    if not token:
        print("Cannot proceed without token.")
        return

    results = []
    for ep in ENDPOINTS:
        status, body = test_endpoint(ep, token)
        results.append((ep, status, body))
        indicator = "OK" if status == 200 else f"!{status}"
        print(f"  [{indicator:>4}] {ep}")

    # Summary table
    groups = {}
    for ep, status, body in results:
        groups.setdefault(status, []).append((ep, body))

    print("\n" + "=" * 90)
    print("SUMMARY BY STATUS CODE")
    print("=" * 90)

    for code in sorted(groups.keys()):
        items = groups[code]
        label = {0: "CONN ERROR", 200: "OK", 400: "BAD REQUEST", 401: "UNAUTHORIZED",
                 403: "FORBIDDEN", 404: "NOT FOUND", 405: "METHOD NOT ALLOWED",
                 422: "VALIDATION ERROR", 500: "SERVER ERROR"}.get(code, f"HTTP {code}")
        print(f"\n--- {code} {label} ({len(items)} endpoints) ---")
        for ep, body in items:
            snippet = body.replace("\n", " ")[:80]
            print(f"  {ep:<45} {snippet}")

    total = len(results)
    ok = sum(1 for _, s, _ in results if s == 200)
    print(f"\n{'=' * 90}")
    print(f"TOTAL: {total} endpoints | OK: {ok} | FAILING: {total - ok}")
    print(f"{'=' * 90}")

if __name__ == "__main__":
    main()
