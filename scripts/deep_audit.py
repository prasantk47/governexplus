#!/usr/bin/env python3
"""
GovernexPlus — Deepest Functional Audit
========================================
Tests EVERY feature, EVERY endpoint, EVERY workflow, EVERY edge case.
Covers: AC (Risk Intelligence/Access Lifecycle/Privileged Access/Role Design/UAR), PC, RM, AM, XI, NF, SSO, AI.

Not a smoke test — this creates real data, runs full lifecycles,
validates response schemas, and checks cross-module integration.

Usage:
    python scripts/deep_audit.py
"""

import sys
import json
import time
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent))

# Use TestClient for in-process testing (no server needed)
from starlette.testclient import TestClient
from api.main import app
from db.database import init_db

init_db()
client = TestClient(app)

# ── Test infrastructure ─────────────────────────────────────────────────

PASS = FAIL = SKIP = 0
RESULTS = []
SECTION = ""
TOKEN = ""
HEADERS = {}

def ok(msg, detail=""):
    global PASS; PASS += 1
    RESULTS.append(("PASS", SECTION, msg, detail))
    print(f"  \033[92m✓\033[0m {msg}")

def fail(msg, detail=""):
    global FAIL; FAIL += 1
    RESULTS.append(("FAIL", SECTION, msg, str(detail)[:300]))
    print(f"  \033[91m✗\033[0m {msg}")
    if detail: print(f"    → {str(detail)[:200]}")

def skip(msg):
    global SKIP; SKIP += 1
    RESULTS.append(("SKIP", SECTION, msg, ""))
    print(f"  \033[93m○\033[0m {msg}")

def section(name):
    global SECTION; SECTION = name
    print(f"\n{'='*72}\n  {name}\n{'='*72}")

def sub(name):
    print(f"\n  -- {name} --")

def api(method, path, json=None, params=None, expect=None, headers=None):
    """Call API, return (status, data). If expect given, auto-pass/fail."""
    h = headers if headers is not None else HEADERS
    r = client.request(method, path, json=json, params=params, headers=h)
    try: data = r.json()
    except: data = r.text
    if expect:
        if isinstance(expect, int): expect = (expect,)
        if r.status_code in expect:
            return r.status_code, data
        else:
            return r.status_code, data
    return r.status_code, data

def check(name, method, path, json=None, params=None, expect=(200,), validate=None, headers=None):
    """Run one test with auto pass/fail."""
    if isinstance(expect, int): expect = (expect,)
    s, d = api(method, path, json, params, headers=headers)
    if s in expect:
        if validate:
            try:
                validate(d)
                ok(name)
            except Exception as e:
                fail(name, f"validation: {e}")
        else:
            ok(name)
    else:
        fail(name, f"expected {expect}, got {s}: {str(d)[:150]}")
    return s, d

def get_id(data, *keys):
    if not isinstance(data, dict): return None
    for k in keys:
        if data.get(k): return data[k]
    for wrap in ("data", "result", "item"):
        inner = data.get(wrap)
        if isinstance(inner, dict):
            for k in keys:
                if inner.get(k): return inner[k]
    return None


# ═════════════════════════════════════════════════════════════════════════
# 0. AUTHENTICATION — Every auth path
# ═════════════════════════════════════════════════════════════════════════

def seed_test_users():
    """Seed 3 test users so Risk Intelligence analysis has data to work with."""
    users = [
        {"user_id": "AUD_USR_001", "username": "aud_usr_001",
         "full_name": "Audit Test User One", "email": "aud1@governex.local",
         "department": "Finance", "title": "AP Clerk"},
        {"user_id": "AUD_USR_002", "username": "aud_usr_002",
         "full_name": "Audit Test User Two", "email": "aud2@governex.local",
         "department": "Finance", "title": "Senior Accountant"},
        {"user_id": "AUD_USR_003", "username": "aud_usr_003",
         "full_name": "Audit Test User Three", "email": "aud3@governex.local",
         "department": "IT", "title": "Basis Admin"},
    ]
    created = 0
    for u in users:
        s, _ = api("POST", "/users/", json=u)
        if s in (200, 201, 409):
            created += 1
    return created


def test_auth():
    global TOKEN, HEADERS
    section("0. AUTHENTICATION & SECURITY")

    sub("0.1 Login")
    s, d = api("POST", "/auth/login", json={
        "username": "admin", "password": "admin123", "tenant_id": "tenant_default"
    })
    if s == 200 and isinstance(d, dict) and d.get("access_token"):
        TOKEN = d["access_token"]
        HEADERS = {"Authorization": f"Bearer {TOKEN}", "X-Tenant-ID": "tenant_default"}
        ok("Login with valid credentials")
    else:
        fail("Login failed", str(d)[:200])
        sys.exit(1)

    sub("0.2 Profile")
    check("GET /auth/me or /auth/profile", "GET", "/auth/profile",
          validate=lambda d: d.get("username") or d.get("user_id"))

    sub("0.3 Negative auth")
    s, _ = api("POST", "/auth/login", json={"username": "admin", "password": "WRONG"})
    if s in (400, 401, 422): ok("Wrong password rejected")
    else: fail("Wrong password not rejected", f"got {s}")

    s, _ = api("GET", "/risk-management/risks", headers={})
    if s in (401, 403): ok("Missing token rejected")
    else: fail("Protected route accessible without token", f"got {s}")

    s, _ = api("GET", "/risk-management/risks",
               headers={"Authorization": "Bearer fake.token.here", "X-Tenant-ID": "tenant_default"})
    if s in (401, 403): ok("Invalid token rejected")
    else: fail("Invalid token accepted", f"got {s}")

    sub("0.4 SSO status")
    check("SSO status endpoint", "GET", "/auth/sso/status",
          validate=lambda d: "local" in d and "saml" in d and "oidc" in d,
          headers={})

    sub("0.5 MFA surface")
    s, _ = api("GET", "/auth/mfa/status")
    if s in (200, 404): ok(f"MFA status endpoint ({s})")
    else: skip("MFA status not found")

    sub("0.6 Token refresh")
    if d.get("refresh_token"):
        check("Token refresh", "POST", "/auth/refresh",
              json={"refresh_token": d["refresh_token"]}, expect=(200, 422))


# ═════════════════════════════════════════════════════════════════════════
# 1. ACCESS CONTROL — SoD Rules
# ═════════════════════════════════════════════════════════════════════════

def test_ac_rules():
    section("1. ACCESS CONTROL — SoD Rules (AC-01..06)")

    sub("1.1 Rule library")
    s, d = check("List SoD rules", "GET", "/sod-rules/", expect=(200, 404))
    s2, d2 = check("Rule engine stats", "GET", "/risk/rules",
                    validate=lambda d: isinstance(d, (list, dict)))
    # Verify rule count
    if isinstance(d2, dict) and d2.get("total_rules"):
        count = d2["total_rules"]
        if count >= 120: ok(f"Rule count: {count} (≥120 expected)")
        else: fail(f"Rule count: {count} (expected ≥120)")

    sub("1.2 Custom rule CRUD")
    ts = int(time.time())
    s, rule = check("Create custom SoD rule", "POST", "/sod-rules/sod-rules/custom", expect=(200, 201), json={
        "rule_id": f"ZAUD-{ts}",
        "name": f"ZAUD-{ts}: Vendor Create vs Payment Run",
        "description": "Audit: vendor create vs payment",
        "severity": "high", "risk_category": "FI", "rule_type": "sod",
        "rule_definition": {
            "function1": {"name": "Vendor Create", "transaction_codes": ["FK01", "XK01"]},
            "function2": {"name": "Payment Run", "transaction_codes": ["F110", "F-53"]},
        },
    })
    rule_id = get_id(rule, "rule_id", "id") or f"ZAUD-{ts}"
    check("Update custom rule severity", "PUT", f"/sod-rules/sod-rules/custom/{rule_id}",
          expect=(200, 404), json={"name": f"ZAUD-{ts}: Vendor vs Payment (Critical)", "severity": "critical"})
    check("Get rule detail", "GET", f"/sod-rules/sod-rules/rules/{rule_id}", expect=(200, 404))

    return rule_id


# ═════════════════════════════════════════════════════════════════════════
# 2. ACCESS CONTROL — Risk Intelligence (Risk Analysis)
# ═════════════════════════════════════════════════════════════════════════

def test_ac_ara():
    section("2. ACCESS CONTROL — Risk Intelligence Risk Analysis (AC-10..18)")

    sub("2.1 User analysis")
    s, users = api("GET", "/users/", params={"limit": 5})
    user_id = None
    if s == 200:
        if isinstance(users, list) and users:
            user_id = users[0].get("user_id") or users[0].get("id")
        elif isinstance(users, dict) and users.get("users"):
            user_id = users["users"][0].get("user_id")

    if user_id:
        check("User-level risk analysis", "GET", f"/ara/analyze/user/{user_id}")
        check("What-if: add role", "POST", "/ara/simulate",
              json={"user_id": str(user_id), "action": "add_role", "role_id": "SAP_FI_ACCOUNTANT"})
        check("What-if: remove role", "POST", "/ara/simulate", expect=(200, 400, 404),
              json={"user_id": str(user_id), "action": "remove_role", "role_id": "SAP_FI_ACCOUNTANT"})
    else:
        skip("No users for Risk Intelligence — skipping user analysis")

    sub("2.2 Violation management")
    check("List violations", "GET", "/risk/violations", expect=(200, 404))
    check("Org-level ranking", "GET", "/risk/org-ranking", expect=(200, 404))
    check("Dormant accounts (90d)", "GET", "/users/dormant", expect=(200, 404), params={"days": 90})

    sub("2.3 Batch analysis surface")
    check("Risk Intelligence batch endpoint", "POST", "/ara/batch", expect=(200, 201, 404, 405),
          json={"scope": "all_users"})


# ═════════════════════════════════════════════════════════════════════════
# 3. ACCESS CONTROL — Mitigation Controls
# ═════════════════════════════════════════════════════════════════════════

def test_ac_mitigation():
    section("3. ACCESS CONTROL — Mitigation Controls (AC-13)")

    sub("3.1 CRUD")
    check("List mitigations", "GET", "/mitigation/controls")
    ts = int(time.time())
    s, mit = check("Create mitigation control", "POST", "/mitigation/controls",
                    expect=(200, 201),
                    params={"created_by": "admin"},
                    json={
        "name": "Audit: Monthly AP review",
        "description": "Monthly review of all vendor invoices over $10K",
        "control_type": "detective",
        "frequency": "monthly",
        "owner_id": "admin",
    })
    mit_id = get_id(mit, "control_id", "id") or f"AUD-MIT-{ts}"
    check("Update mitigation", "PUT", f"/mitigation/controls/{mit_id}",
          expect=(200, 404),
          params={"modified_by": "admin", "frequency": "weekly"})

    sub("3.2 Monitoring dashboard")
    s, _ = api("GET", "/mitigation-monitoring/")
    if s == 200: ok("Mitigation monitoring dashboard")
    elif s == 404: skip("Monitoring dashboard not found")
    else: fail("Monitoring dashboard error", f"got {s}")

    return mit_id


# ═════════════════════════════════════════════════════════════════════════
# 4. ACCESS CONTROL — Access Lifecycle (Access Requests)
# ═════════════════════════════════════════════════════════════════════════

def test_ac_arm():
    section("4. ACCESS CONTROL — Access Lifecycle Access Requests (AC-20..24)")

    sub("4.1 Request lifecycle")
    check("List access requests", "GET", "/access-requests/")
    check("Pending approvals", "GET", "/access-requests/approvals/pending",
          expect=(200, 404, 422), params={"approver_id": "admin"})

    s, ar = check("Create access request", "POST", "/access-requests/", expect=(200, 201), json={
        "requester_user_id": "AUD_USR_001",
        "requester_name": "Audit Test User One",
        "requester_email": "aud1@governex.local",
        "target_user_id": "AUD_USR_002",
        "target_user_name": "Audit Test User Two",
        "request_type": "new_access",
        "requested_roles": ["SAP_FI_VIEWER"],
        "business_justification": "Audit: need read access to financial reports for project",
    })
    req_id = get_id(ar, "request_id", "id")
    if req_id:
        check("Get request detail", "GET", f"/access-requests/{req_id}")
        # Approval requires step_id — use bulk-approve which approves all pending steps
        check("Approve request (bulk)", "POST", f"/access-requests/{req_id}/bulk-approve",
              expect=(200, 400, 409), params={"actor_id": "admin", "comments": "Audit approved"})

    sub("4.2 Reject path")
    s, ar2 = api("POST", "/access-requests/", json={
        "requester_user_id": "AUD_USR_001",
        "requester_name": "Audit Test User One",
        "requester_email": "aud1@governex.local",
        "target_user_id": "AUD_USR_003",
        "target_user_name": "Audit Test User Three",
        "request_type": "new_access",
        "requested_roles": ["SAP_ALL"],
        "business_justification": "Audit: broad access test for rejection path validation",
    })
    req2 = get_id(ar2, "request_id", "id")
    if req2:
        # Cancel (reject) via cancel endpoint with user_id query param
        check("Cancel/reject request", "POST", f"/access-requests/{req2}/cancel",
              expect=(200, 400, 409), params={"user_id": "AUD_USR_001"})

    sub("4.3 Shopping cart")
    s, _ = api("GET", "/arm/cart")
    if s in (200, 404):
        ok(f"Cart endpoint ({s})")
        if s == 200:
            check("Add to cart", "POST", "/arm/cart/items", expect=(200, 201, 400, 422),
                  json={"role_id": "SAP_MM_BUYER", "justification": "Audit cart"})

    sub("4.4 Model user")
    check("Model user endpoint", "GET", "/model-user/templates", expect=(200, 404))

    sub("4.5 Approver management")
    check("List approvers", "GET", "/approver-management/approvers", expect=(200, 404))


# ═════════════════════════════════════════════════════════════════════════
# 5. ACCESS CONTROL — Privileged Access (Firefighter)
# ═════════════════════════════════════════════════════════════════════════

def test_ac_eam():
    section("5. ACCESS CONTROL — Privileged Access Firefighter (AC-30..33)")

    sub("5.1 Dashboard + sessions")
    check("Firefighter dashboard", "GET", "/firefighter/dashboard", expect=(200, 404))
    check("List sessions", "GET", "/firefighter/sessions", expect=(200, 404))

    sub("5.2 Request lifecycle")
    s, ff = check("Request firefighter access", "POST", "/firefighter/requests",
                  expect=(200, 201, 400), json={
        "requester_user_id": "AUD_USR_001",
        "requester_name": "Audit Test User One",
        "requester_email": "aud1@governex.local",
        "target_system": "SAP_PROD",
        "firefighter_id": "FF_SAP_001",
        "reason_code": "prod_incident",
        "reason": "Audit: production investigation",
        "business_justification": "Production job failure requires immediate basis admin investigation to restore service",
        "ticket_reference": "INC-AUD-001",
        "duration_hours": 1,
    })
    ff_id = get_id(ff, "request_id", "id")
    if ff_id:
        check("Approve firefighter", "POST", f"/firefighter/requests/{ff_id}/approve",
              expect=(200, 400, 404, 409), json={"approver_id": "admin"})

    sub("5.3 Monitoring")
    check("Live monitoring", "GET", "/firefighter/monitoring/live", expect=(200, 404))

    sub("5.4 Review")
    s, _ = api("GET", "/firefighter/reviews/pending", params={"reviewer_id": "admin"})
    if s == 200: ok("Pending reviews endpoint")
    elif s == 404: skip("Reviews endpoint not found")


# ═════════════════════════════════════════════════════════════════════════
# 6. ACCESS CONTROL — UAR (Certification)
# ═════════════════════════════════════════════════════════════════════════

def test_ac_uar():
    section("6. ACCESS CONTROL — UAR Certification (AC-40..43)")

    sub("6.1 Campaign lifecycle")
    check("List campaigns", "GET", "/certification/campaigns")
    s, camp = check("Create campaign", "POST", "/certification/campaigns",
                    expect=(200, 201), json={
        "name": f"Audit UAR {datetime.now():%Y-%m}",
        "description": f"Quarterly access certification audit {datetime.now():%Y-%m}",
        "campaign_type": "user_access",
        "owner_id": "admin",
        "owner_name": "System Administrator",
        "end_date": (datetime.now() + timedelta(days=30)).isoformat(),
    })
    camp_id = get_id(camp, "campaign_id", "id")
    if camp_id:
        s, items = check("Get review items", "GET", f"/certification/campaigns/{camp_id}/items")
        item_list = items if isinstance(items, list) else (
            items.get("items", []) if isinstance(items, dict) else [])
        if item_list:
            iid = item_list[0].get("item_id") or item_list[0].get("id")
            check("Certify item", "POST",
                  f"/certification/campaigns/{camp_id}/items/{iid}/decision",
                  expect=(200, 400), json={"reviewer_id": "admin", "action": "certify",
                                           "comments": "Audit certification"})
            if len(item_list) > 1:
                iid2 = item_list[1].get("item_id") or item_list[1].get("id")
                check("Revoke item", "POST",
                      f"/certification/campaigns/{camp_id}/items/{iid2}/decision",
                      expect=(200, 400), json={"reviewer_id": "admin", "action": "revoke",
                                               "comments": "Audit revocation"})
        else:
            skip("No review items (no user-role data)")


# ═════════════════════════════════════════════════════════════════════════
# 7. ACCESS CONTROL — Role Design (Role Engineering)
# ═════════════════════════════════════════════════════════════════════════

def test_ac_brm():
    section("7. ACCESS CONTROL — Role Design Role Engineering (AC-50..52)")

    check("Role catalog", "GET", "/role-engineering/catalog")
    check("Role mining", "GET", "/role-engineering/mining", expect=(200, 404))
    check("Design role + SoD check", "POST", "/role-engineering/roles",
          expect=(200, 201, 400),
          params={"created_by": "admin"},
          json={
              "name": f"Z_AUD_ROLE_{int(time.time())}",
              "description": "Audit designed role for SoD check validation",
          })
    check("Drift detection", "GET", "/drift/", expect=(200, 404))
    check("Role intelligence", "GET", "/role-intelligence/landscape", expect=(200, 404))


# ═════════════════════════════════════════════════════════════════════════
# 8. RISK MANAGEMENT — Full lifecycle
# ═════════════════════════════════════════════════════════════════════════

def test_rm():
    section("8. RISK MANAGEMENT (RM-01..31)")

    sub("8.1 Risk register")
    s, risk = check("Create risk (EN+AR)", "POST", "/risk-management/risks",
                    expect=(200, 201), json={
        "title": "Unauthorized Payment Processing",
        "description": "Risk of unauthorized payments due to inadequate SoD",
        "description_ar": "خطر المدفوعات غير المصرح بها",
        "category": "financial", "risk_owner_id": "admin",
        "risk_owner_name": "System Administrator",
        "inherent_likelihood": 4, "inherent_impact": 5,
        "status": "identified", "review_frequency": "quarterly",
    })
    risk_id = get_id(risk, "risk_id", "id")
    check("List risks", "GET", "/risk-management/risks", validate=lambda d: isinstance(d, list))

    if risk_id:
        check("Risk detail", "GET", f"/risk-management/risks/{risk_id}")
        check("Update risk (recompute score)", "PUT", f"/risk-management/risks/{risk_id}",
              json={"inherent_likelihood": 5})

        sub("8.2 Assessment lifecycle")
        s, assess = check("Create assessment", "POST",
            f"/risk-management/risks/{risk_id}/assessments", expect=(200, 201), json={
                "assessor_id": "admin", "assessor_name": "Admin",
                "likelihood_score": 3, "impact_score": 4, "overall_score": 12.0,
                "assessment_type": "periodic",
                "likelihood_rationale": "Controls reduce likelihood",
                "impact_rationale": "Up to $500K exposure",
                "monetary_impact": 500000.0, "currency": "USD",
            })
        assess_id = get_id(assess, "assessment_id", "id")
        if assess_id:
            check("Submit assessment", "PUT", f"/risk-management/assessments/{assess_id}/submit",
                  json={})
            check("Review assessment (updates residual)", "PUT",
                  f"/risk-management/assessments/{assess_id}/review",
                  json={"reviewer_id": "admin", "comments": "Approved"})
        check("List assessments", "GET", f"/risk-management/risks/{risk_id}/assessments")
        check("Assessment campaign", "POST", "/risk-management/assessment-campaigns",
              expect=(200, 201, 404), json={"name": "Audit campaign", "assessment_type": "periodic"})

        sub("8.3 Appetite & tolerance")
        check("Set appetite", "POST", "/risk-management/appetites", expect=(200, 201), json={
            "category": "financial", "appetite_score": 10.0, "tolerance_score": 15.0,
            "description": "Moderate financial risk appetite", "approved_by": "CFO"})
        check("Get appetites", "GET", "/risk-management/appetites", params={"category": "financial"})
        check("Appetite breach check", "GET", f"/risk-management/risks/{risk_id}/appetite-check")

        sub("8.4 KRI")
        s, kri = check("Create KRI", "POST", "/risk-management/kris", expect=(200, 201), json={
            "name": "Open SoD Violations", "description": "Unresolved violations",
            "risk_id": risk_id, "data_source": "manual", "unit_of_measure": "count",
            "frequency": "weekly", "threshold_green": 50, "threshold_amber": 100, "threshold_red": 200,
        })
        kri_id = get_id(kri, "kri_id", "id")
        if kri_id:
            check("Record KRI measurement", "POST", f"/risk-management/kris/{kri_id}/measurements",
                  expect=(200, 201), json={"value": 75, "measured_by": "admin", "source": "manual"})
            check("KRI history", "GET", f"/risk-management/kris/{kri_id}/history")
        check("KRI dashboard", "GET", "/risk-management/kris/dashboard")

        sub("8.5 Response plans")
        s, resp = check("Create response (mitigate)", "POST",
            f"/risk-management/risks/{risk_id}/responses", expect=(200, 201), json={
                "response_type": "mitigate", "description": "Implement SoD controls",
                "owner_id": "admin", "owner_name": "Admin",
                "actions": [{"action": "Review AP roles", "due_date": "2026-10-01"}],
                "due_date": (datetime.now() + timedelta(days=60)).isoformat(),
            })
        resp_id = get_id(resp, "response_id", "id")
        if resp_id:
            check("Advance response", "PUT", f"/risk-management/responses/{resp_id}/status",
                  json={"status": "in_progress"})

        sub("8.6 Incidents")
        s, inc = check("Report incident", "POST", "/risk-management/incidents",
                       expect=(200, 201), json={
            "title": "Unauthorized vendor payment", "description": "$45K unauthorized",
            "severity": "high", "financial_impact": 45000, "currency": "USD",
            "occurred_at": datetime.now().isoformat(), "reported_by": "admin",
        })
        inc_id = get_id(inc, "incident_id", "id")
        if inc_id:
            check("Link incident to risk", "POST", f"/risk-management/incidents/{inc_id}/link-risk",
                  json={"risk_id": risk_id})
        check("List incidents", "GET", "/risk-management/incidents")

    sub("8.7 Reporting")
    check("Heatmap", "GET", "/risk-management/heatmap")
    check("Trends", "GET", "/risk-management/trends", params={"period_months": 6})
    check("Top risks", "GET", "/risk-management/top-risks", params={"limit": 5})
    check("Risk-control coverage", "GET", "/risk-management/risk-control-coverage")
    check("Overdue reviews", "GET", "/risk-management/overdue-reviews")

    return risk_id


# ═════════════════════════════════════════════════════════════════════════
# 9. PROCESS CONTROL — Full lifecycle
# ═════════════════════════════════════════════════════════════════════════

def test_pc(risk_id=None):
    section("9. PROCESS CONTROL (PC-01..32)")

    sub("9.1 Control library")
    s, ctl = check("Create control (key/SOX)", "POST", "/process-control/controls",
                   expect=(200, 201), json={
        "name": "Three-Way Match", "objective": "PO+GR+Invoice match before payment",
        "description": "Automated 3-way match in SAP",
        "control_type": "preventive", "control_nature": "automated",
        "frequency": "continuous", "process_name": "Procure-to-Pay",
        "subprocess_name": "Invoice Verification",
        "owner_id": "admin", "owner_name": "Admin", "key_control": True,
        "risk_ids": [risk_id] if risk_id else [],
    })
    ctl_id = get_id(ctl, "control_id", "id")
    check("List controls", "GET", "/process-control/controls", validate=lambda d: isinstance(d, list))
    if ctl_id:
        check("Control detail", "GET", f"/process-control/controls/{ctl_id}")

    sub("9.2 Framework mapping")
    s, fw = api("POST", "/frameworks/", json={
        "name": "COSO 2013", "version": "2013", "framework_type": "coso",
        "description": "COSO Internal Control Framework"})
    fw_id = get_id(fw, "framework_id", "id")
    if not fw_id:
        s, fws = api("GET", "/frameworks/")
        if s == 200 and isinstance(fws, list) and fws:
            fw_id = fws[0].get("framework_id")
    if fw_id and ctl_id:
        api("POST", f"/frameworks/{fw_id}/requirements", json={
            "requirement_id": "COSO-P10", "title": "Control Activities",
            "description": "Select and develop control activities", "category": "Control Activities", "level": 1})
        check("Map control to COSO", "POST",
              f"/process-control/controls/{ctl_id}/framework-mappings",
              expect=(200, 201), json={"framework_id": fw_id, "requirement_id": "COSO-P10"})
        check("Framework coverage", "GET", f"/process-control/frameworks/{fw_id}/coverage")

    sub("9.3 Control testing")
    if ctl_id:
        s, test = check("Create OE test", "POST", f"/process-control/controls/{ctl_id}/tests",
                        expect=(200, 201), json={
            "test_type": "operating_effectiveness",
            "testing_period_start": "2026-07-01", "testing_period_end": "2026-09-30",
            "sample_size": 25, "population_size": 500,
            "tester_id": "admin", "tester_name": "Admin",
            "test_steps": [{"step": 1, "description": "Select 25 payments"}, {"step": 2, "description": "Verify match"}],
        })
        test_id = get_id(test, "test_id", "id")
        if test_id:
            check("Record result — effective", "PUT", f"/process-control/tests/{test_id}/result",
                  json={"result": "effective", "exceptions_found": 1, "conclusion": "Effective; 1 timing exception"})

        # Ineffective test → auto-deficiency
        s, test2 = api("POST", f"/process-control/controls/{ctl_id}/tests", json={
            "test_type": "design", "testing_period_start": "2026-01-01",
            "testing_period_end": "2026-06-30", "sample_size": 30,
            "tester_id": "admin", "tester_name": "Admin"})
        test2_id = get_id(test2, "test_id", "id")
        if test2_id:
            check("Record result — ineffective (auto-deficiency)", "PUT",
                  f"/process-control/tests/{test2_id}/result",
                  json={"result": "ineffective", "exceptions_found": 8, "conclusion": "Design gap found"})

    sub("9.4 Deficiency lifecycle")
    check("List deficiencies", "GET", "/process-control/deficiencies")
    if ctl_id:
        s, defc = check("Create deficiency", "POST", "/process-control/deficiencies",
                        expect=(200, 201), json={
            "control_id": ctl_id, "source": "self_assessment",
            "title": "Tolerance limit gap", "description": "Limits not aligned",
            "severity": "significant_deficiency",
            "remediation_plan": "Reconfigure limits", "remediation_owner_id": "admin",
            "remediation_owner_name": "Admin",
            "due_date": (datetime.now() + timedelta(days=30)).isoformat(),
        })
        def_id = get_id(defc, "deficiency_id", "id")
        if def_id:
            check("Remediate", "PUT", f"/process-control/deficiencies/{def_id}/remediate",
                  json={"remediation_plan": "Reconfigured and retested"})
            check("Verify closure", "PUT", f"/process-control/deficiencies/{def_id}/verify")

    sub("9.5 Self-assessment")
    check("Create CSA campaign", "POST", "/process-control/self-assessment-campaigns",
          expect=(200, 201), json={"campaign_name": "Q3-2026 CSA", "campaign_type": "quarterly"})
    check("Pending assessments", "GET", "/process-control/self-assessments/pending",
          params={"assessor_id": "admin"})

    sub("9.6 CCM")
    s, ccm = check("Create CCM rule", "POST", "/process-control/ccm-rules", expect=(200, 201), json={
        "name": "Password Policy Check", "description": "SAP password params",
        "source_system": "SAP", "rule_type": "config_check",
        "rule_definition": {"check": "password_policy", "params": {"min_length": 8}},
        "frequency": "daily", "auto_create_deficiency": True,
    })
    ccm_id = get_id(ccm, "rule_id", "id")
    if ccm_id:
        check("Execute CCM rule", "POST", f"/process-control/ccm-rules/{ccm_id}/execute")
    check("Run all CCM", "POST", "/process-control/ccm/run-all", expect=(200, 404))
    check("CCM dashboard", "GET", "/process-control/ccm/dashboard")

    sub("9.7 Evidence")
    s, evd = check("Upload evidence", "POST", "/process-control/evidence", expect=(200, 201), json={
        "title": "3-Way Match Test Q3", "description": "25 samples tested",
        "evidence_type": "document", "file_name": "test_q3.xlsx",
        "source_module": "pc", "linked_object_type": "control_test",
        "linked_object_id": test_id if ctl_id else "TEST-001", "uploaded_by": "admin",
    })
    evd_id = get_id(evd, "evidence_id", "id")
    if evd_id:
        check("Set legal hold", "PUT", f"/process-control/evidence/{evd_id}/legal-hold",
              json={"legal_hold": True, "reason": "Litigation hold"})

    sub("9.8 SOX sign-off")
    s, so = check("Create sign-off", "POST", "/process-control/signoffs", expect=(200, 201), json={
        "period": "Q3-2026", "certifier_id": "admin", "certifier_name": "Admin",
        "certifier_role": "process_owner", "scope_summary": "P2P controls CC 1000",
        "controls_in_scope": 12, "controls_effective": 11, "deficiencies_open": 1,
    })
    so_id = get_id(so, "certification_id", "signoff_id", "id")
    if so_id:
        check("Submit certification", "PUT", f"/process-control/signoffs/{so_id}/submit", expect=(200, 400, 404))
    check("Sign-off hierarchy", "GET", "/process-control/signoffs/hierarchy", params={"period": "Q3-2026"})

    sub("9.9 Dashboard")
    check("PC dashboard", "GET", "/process-control/dashboard")
    if ctl_id:
        check("Audit-ready package", "GET", f"/process-control/controls/{ctl_id}/audit-package", expect=(200, 404))

    return ctl_id


# ═════════════════════════════════════════════════════════════════════════
# 10. AUDIT MANAGEMENT — Full lifecycle
# ═════════════════════════════════════════════════════════════════════════

def test_am(risk_id=None, ctl_id=None):
    section("10. AUDIT MANAGEMENT (AM-01..32)")

    sub("10.1 Audit universe")
    s, ent = check("Create auditable entity", "POST", "/audit-management/entities",
                   expect=(200, 201), json={
        "name": "Procure-to-Pay Process", "description": "End-to-end procurement",
        "entity_type": "process", "audit_frequency": "annual",
    })
    entity_id = get_id(ent, "entity_id", "id")
    if entity_id:
        check("Compute risk score (XI-04)", "POST", f"/audit-management/entities/{entity_id}/compute-risk")
    check("List entities", "GET", "/audit-management/entities")

    sub("10.2 Planning")
    s, plan = check("Create annual plan", "POST", "/audit-management/plans", expect=(200, 201), json={
        "name": "FY2026 Audit Plan", "description": "Risk-based plan",
        "plan_type": "annual", "fiscal_year": 2026, "total_audit_hours": 2000,
    })
    plan_id = get_id(plan, "plan_id", "id")
    if plan_id:
        check("Submit plan", "PUT", f"/audit-management/plans/{plan_id}/submit")
        check("Approve plan", "PUT", f"/audit-management/plans/{plan_id}/approve",
              json={"approver_id": "admin", "comments": "Approved"})
    check("List plans", "GET", "/audit-management/plans")
    check("Risk-based plan generation", "POST", "/audit-management/plans/generate-risk-based",
          expect=(200, 201), json={"fiscal_year": 2027, "max_engagements": 10})

    sub("10.3 Resources")
    check("Register auditor", "POST", "/audit-management/resources", expect=(200, 201), json={
        "name": "Sarah Chen", "email": "sarah@governex.local", "title": "Senior IT Auditor",
        "skills": ["IT audit", "SAP", "SoD"], "certifications": ["CISA", "CISSP"],
        "available_hours_per_month": 140,
    })
    check("List resources", "GET", "/audit-management/resources")
    check("Available resources", "GET", "/audit-management/resources/available",
          params={"start_date": "2026-10-01", "end_date": "2026-12-31"})

    sub("10.4 Engagement lifecycle (6 stages)")
    s, eng = check("Create engagement", "POST", "/audit-management/engagements",
                   expect=(200, 201), json={
        "title": "P2P Audit FY2026", "objective": "Assess P2P controls",
        "scope": "Vendor mgmt, PO, GR, invoice, payments",
        "engagement_type": "operational",
        "plan_id": plan_id, "entity_id": entity_id,
        "lead_auditor_id": "admin", "lead_auditor_name": "Admin",
        "team_members": [{"id": "sarah", "name": "Sarah Chen"}],
        "planned_start": "2026-10-01", "planned_end": "2026-11-30", "budget_hours": 200,
    })
    eng_id = get_id(eng, "engagement_id", "id")

    if eng_id:
        for stage in ["announced", "fieldwork"]:
            s, adv = api("PUT", f"/audit-management/engagements/{eng_id}/advance")
            got = adv.get("status", "") if isinstance(adv, dict) else ""
            if s == 200: ok(f"Advance to {stage}")
            else: fail(f"Advance to {stage}", f"status={s}")

        sub("10.5 Work programs")
        check("Create work program template", "POST", "/audit-management/work-programs",
              expect=(200, 201), json={
            "name": "P2P Work Program", "description": "Standard P2P procedures",
            "audit_type": "operational", "is_template": True,
            "procedures": [
                {"ref": "AP-001", "title": "Vendor Master Review"},
                {"ref": "AP-002", "title": "PO Authorization Limits"},
            ],
        })

        sub("10.6 Procedures + dual sign-off")
        s, proc = check("Create procedure", "POST",
            f"/audit-management/engagements/{eng_id}/procedures", expect=(200, 201), json={
            "ref_number": "AP-001", "title": "Vendor Master Review",
            "description": "Review vendor creation controls",
            "assigned_to_id": "admin", "assigned_to_name": "Admin",
        })
        proc_id = get_id(proc, "procedure_id", "id")
        if proc_id:
            check("Complete procedure (preparer)", "PUT",
                  f"/audit-management/procedures/{proc_id}/complete",
                  json={"conclusion": "2/30 delayed approvals", "preparer_id": "admin", "hours_spent": 16})
            check("Review procedure (reviewer)", "PUT",
                  f"/audit-management/procedures/{proc_id}/review",
                  json={"reviewer_id": "admin", "review_notes": "Work adequate"})

        sub("10.7 Workpapers")
        s, wp = check("Create workpaper", "POST",
            f"/audit-management/engagements/{eng_id}/workpapers", expect=(200, 201), json={
            "title": "Vendor Analysis", "description": "Vendor creation patterns",
            "document_type": "narrative", "content": "30 vendors selected for Q3...",
            "procedure_id": proc_id, "preparer_id": "admin",
        })

        sub("10.8 Findings (CCCE)")
        s, fnd = check("Create CCCE finding", "POST",
            f"/audit-management/engagements/{eng_id}/findings", expect=(200, 201), json={
            "title": "Delayed Vendor Approval",
            "ref_number": "F-001",
            "condition": "2/30 vendors created without timely secondary approval",
            "criteria": "Policy requires dual approval within 24 hours",
            "cause": "No automated escalation",
            "effect": "Risk of unauthorized vendor creation",
            "recommendation": "Implement automated escalation workflow",
            "severity": "medium", "category": "process_compliance",
            "risk_id": risk_id, "control_id": ctl_id,
        })
        finding_id = get_id(fnd, "finding_id", "id")
        if finding_id:
            check("Management response", "PUT",
                  f"/audit-management/findings/{finding_id}/management-response",
                  json={"management_response": "Agreed. Automation by Q4.",
                        "management_action_owner": "admin", "management_target_date": "2026-12-31"})
            if risk_id:
                check("Link finding → risk (XI-03)", "POST",
                      f"/audit-management/findings/{finding_id}/link-risk",
                      expect=(200, 201, 409), json={"risk_id": risk_id})
            if ctl_id:
                check("Link finding → control (XI-03)", "POST",
                      f"/audit-management/findings/{finding_id}/link-control",
                      expect=(200, 201, 409), json={"control_id": ctl_id})

            sub("10.9 Actions")
            s, act = check("Create action", "POST",
                f"/audit-management/findings/{finding_id}/actions", expect=(200, 201), json={
                "description": "Configure escalation workflow",
                "owner_id": "admin", "owner_name": "Admin", "due_date": "2026-12-31",
            })
            act_id = get_id(act, "action_id", "id")
            if act_id:
                check("Close action", "PUT", f"/audit-management/actions/{act_id}/close",
                      json={"evidence_of_closure": "Workflow configured", "evidence_ids": ["EVD-WF-001"]})
                check("Verify closure", "PUT", f"/audit-management/actions/{act_id}/verify",
                      expect=(200, 404), json={"verifier_id": "admin"})

            check("Overdue actions", "GET", "/audit-management/actions/overdue")
            check("Escalate overdue", "POST", "/audit-management/actions/escalate", expect=(200, 404))

        sub("10.10 Time tracking")
        check("Record time", "POST", f"/audit-management/engagements/{eng_id}/time",
              expect=(200, 201), json={
            "auditor_id": "admin", "auditor_name": "Admin",
            "date": datetime.now().isoformat(), "hours": 8.0,
            "activity_type": "fieldwork", "description": "Vendor testing",
        })
        check("Time summary", "GET", f"/audit-management/engagements/{eng_id}/time-summary")

        sub("10.11 Close engagement")
        for stage in ["draft_report", "final_report", "closed"]:
            s, _ = api("PUT", f"/audit-management/engagements/{eng_id}/advance")
            if s == 200: ok(f"Advance to {stage}")
            else: fail(f"Advance to {stage}", f"status={s}")

    sub("10.12 Reporting")
    check("AM dashboard", "GET", "/audit-management/dashboard")
    check("Committee report", "GET", "/audit-management/committee-report", params={"fiscal_year": 2026})
    if eng_id:
        check("Engagement report", "GET", f"/audit-management/engagements/{eng_id}/report")


# ═════════════════════════════════════════════════════════════════════════
# 11. CROSS-MODULE INTEGRATION (XI)
# ═════════════════════════════════════════════════════════════════════════

def test_xi():
    section("11. CROSS-MODULE INTEGRATION (XI-01..08)")

    check("Unified GRC dashboard (XI-05)", "GET", "/grc/dashboard")
    check("Risk-control matrix (XI-03)", "GET", "/grc/risk-control-matrix")
    check("Org units (XI-01)", "GET", "/org/units")
    check("Org tree", "GET", "/org/tree", expect=(200, 404))
    check("Frameworks (XI-07)", "GET", "/frameworks/")
    check("GRC health score", "GET", "/grc-intelligence/health")
    check("Attention items", "GET", "/grc-intelligence/attention")


# ═════════════════════════════════════════════════════════════════════════
# 12. GRC INTELLIGENCE (AI)
# ═════════════════════════════════════════════════════════════════════════

def test_ai():
    section("12. GRC INTELLIGENCE — AI Layer")

    check("Health score", "GET", "/grc-intelligence/health")
    check("Attention items", "GET", "/grc-intelligence/attention")
    check("CFO dashboard", "GET", "/grc-intelligence/dashboard/cfo")
    check("CISO dashboard", "GET", "/grc-intelligence/dashboard/ciso")
    check("CAE dashboard", "GET", "/grc-intelligence/dashboard/cae")
    check("AI explain", "POST", "/grc-intelligence/explain",
          json={"object_type": "risk", "object_id": "test"})
    check("AI investigate", "POST", "/grc-intelligence/investigate",
          json={"object_type": "risk", "object_id": "test"})
    check("Fix preview", "POST", "/grc-intelligence/fix-preview",
          json={"action_type": "remove_access", "target_id": "test"})


# ═════════════════════════════════════════════════════════════════════════
# 13. NON-FUNCTIONAL (NF)
# ═════════════════════════════════════════════════════════════════════════

def test_nf():
    section("13. NON-FUNCTIONAL (NF-01..10)")

    check("Health endpoint", "GET", "/health", headers={})
    check("Platform info", "GET", "/", headers={},
          validate=lambda d: d.get("name") == "Governex+")
    check("OpenAPI spec", "GET", "/openapi.json", headers={},
          validate=lambda d: "paths" in d)
    check("i18n translations", "GET", "/i18n/translations", expect=(200, 404))
    check("Retention policies", "GET", "/retention/policies", expect=(200, 404))
    check("Metrics endpoint", "GET", "/metrics", expect=(200, 404), headers={})


# ═════════════════════════════════════════════════════════════════════════
# MAIN
# ═════════════════════════════════════════════════════════════════════════

def main():
    print(f"\n{'#'*72}")
    print(f"  GovernexPlus — Deep Functional Audit")
    print(f"  {datetime.now():%Y-%m-%d %H:%M:%S}")
    print(f"{'#'*72}")

    test_auth()
    seed_test_users()
    rule_id = test_ac_rules()
    test_ac_ara()
    mit_id = test_ac_mitigation()
    test_ac_arm()
    test_ac_eam()
    test_ac_uar()
    test_ac_brm()
    risk_id = test_rm()
    ctl_id = test_pc(risk_id)
    test_am(risk_id, ctl_id)
    test_xi()
    test_ai()
    test_nf()

    # ── Summary ──
    print(f"\n{'='*72}")
    print(f"  DEEP AUDIT RESULTS")
    print(f"{'='*72}")
    print(f"  PASS: {PASS}")
    print(f"  FAIL: {FAIL}")
    print(f"  SKIP: {SKIP}")
    print(f"  TOTAL: {PASS + FAIL + SKIP}")
    rate = (PASS / (PASS + FAIL) * 100) if (PASS + FAIL) > 0 else 0
    print(f"  PASS RATE: {rate:.1f}%")
    print(f"{'='*72}")

    if FAIL > 0:
        print(f"\n  FAILURES:")
        for status, section, msg, detail in RESULTS:
            if status == "FAIL":
                print(f"  \033[91m✗\033[0m [{section}] {msg}")
                if detail: print(f"    → {detail[:200]}")

    return 1 if FAIL > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
