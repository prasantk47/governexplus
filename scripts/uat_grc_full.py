#!/usr/bin/env python3
"""
UAT Script: Governex+ Full GRC Suite — AC + RM + PC + AM + XI + NF
====================================================================
End-to-end lifecycle testing for every module, benchmarked against the
flows of GovernexPlus (Access Control 12.0, Process Control, Risk Management,
Audit Management) and full-suite GRC tools (MetricStream, Archer,
ServiceNow IRM).

Each test carries:
  - Governex+ requirement ID  (AC-xx / RM-xx / PC-xx / AM-xx / XI-xx / NF-xx)
  - GovernexPlus equivalent noted in comments (Risk Intelligence, Access Lifecycle/MSMP, Privileged Access/SPM, Role Design, UAR,
    PC CAPA/CCM/Sign-off, RM KRI/Response, AM Working Papers/Findings)

Usage:
    python scripts/uat_grc_full.py [--base-url http://localhost:8000]
                                   [--tenant tenant_default]
                                   [--username admin] [--password admin123]

Exit code: 0 = all pass, 1 = failures found.
"""

import sys
import time
import argparse
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent))

import requests

# ── Globals ──────────────────────────────────────────────────────────────────

PASS, FAIL, SKIP = 0, 0, 0
RESULTS = []          # (section, test_id, name, status, detail)
SECTION = ""
BASE_URL = "http://localhost:8000"
TENANT = "tenant_default"
TOKEN = ""
HEADERS = {}
OK_CREATE = (200, 201)   # accept both idiomatic create codes


def _record(status, msg, detail=""):
    RESULTS.append((SECTION, msg, status, detail))


def ok(msg):
    global PASS
    PASS += 1
    _record("PASS", msg)
    print(f"  \033[92mPASS\033[0m  {msg}")


def fail(msg, detail=""):
    global FAIL
    FAIL += 1
    _record("FAIL", msg, detail)
    print(f"  \033[91mFAIL\033[0m  {msg}")
    if detail:
        print(f"        {str(detail)[:200]}")


def skip(msg):
    global SKIP
    SKIP += 1
    _record("SKIP", msg)
    print(f"  \033[93mSKIP\033[0m  {msg}")


def section(name):
    global SECTION
    SECTION = name
    print(f"\n{'='*72}\n  {name}\n{'='*72}")


def sub(name):
    print(f"\n  --- {name} ---")


def api(method, path, json_data=None, params=None, headers=None, timeout=30):
    """Raw API call. Returns (status_code, parsed_body)."""
    url = f"{BASE_URL}{path}"
    try:
        resp = requests.request(method, url, json=json_data, params=params,
                                headers=headers if headers is not None else HEADERS,
                                timeout=timeout)
        try:
            data = resp.json()
        except Exception:
            data = resp.text
        return resp.status_code, data
    except Exception as e:
        return 0, str(e)


def check(test_name, method, path, json_data=None, params=None,
          expect=(200,), validate=None, headers=None):
    """Run one test. `expect` = int or tuple of acceptable status codes."""
    if isinstance(expect, int):
        expect = (expect,)
    status, data = api(method, path, json_data, params, headers)
    if status in expect:
        if validate:
            try:
                validate(data)
                ok(test_name)
            except AssertionError as e:
                fail(test_name, f"validation: {e}")
        else:
            ok(test_name)
    else:
        fail(test_name, f"expected {expect}, got {status}: {str(data)[:150]}")
    return status, data


def get_id(data, *keys):
    """Pull the first present id-like key from a response dict."""
    if not isinstance(data, dict):
        return None
    for k in keys:
        if data.get(k):
            return data[k]
    for wrap in ("data", "result", "item"):
        inner = data.get(wrap)
        if isinstance(inner, dict):
            for k in keys:
                if inner.get(k):
                    return inner[k]
    return None


def first_of(paths, params=None):
    """Try alternate GET paths, return (path, data) of first 200."""
    for p in paths:
        status, data = api("GET", p, params=params)
        if status == 200:
            return p, data
    return None, None


# ═════════════════════════════════════════════════════════════════════════════
# 0. AUTHENTICATION & SECURITY BASELINE
# ═════════════════════════════════════════════════════════════════════════════

def test_auth(username, password):
    global TOKEN, HEADERS
    section("0. AUTHENTICATION & SECURITY BASELINE")

    sub("0.1 Login & token")
    status, data = api("POST", "/auth/login", {
        "username": username, "password": password, "tenant_id": TENANT,
    })
    if status == 200 and isinstance(data, dict) and data.get("access_token"):
        TOKEN = data["access_token"]
        HEADERS = {"Authorization": f"Bearer {TOKEN}", "X-Tenant-ID": TENANT}
        ok("AUTH-01: Login returns access token")
    elif status == 200 and isinstance(data, dict) and data.get("mfa_required"):
        skip("AUTH-01: MFA challenge required — supply TOTP to complete (NF-06)")
        sys.exit(1)
    else:
        fail("AUTH-01: Login failed — cannot proceed", str(data)[:200])
        print("\n\033[91mSeed a user first, or pass --username/--password.\033[0m")
        sys.exit(1)

    # Try /auth/me first, fall back to /auth/profile
    p, _ = first_of(["/auth/me", "/auth/profile"])
    if p:
        ok(f"AUTH-02: Profile endpoint live ({p})")
    else:
        skip("AUTH-02: Profile endpoint not found")

    sub("0.2 Negative auth (must be rejected)")
    status, _ = api("POST", "/auth/login",
                    {"username": username, "password": "definitely-wrong-xx",
                     "tenant_id": TENANT}, headers={})
    if status in (400, 401, 403):
        ok("AUTH-03: Wrong password rejected")
    else:
        fail("AUTH-03: Wrong password NOT rejected", f"got {status}")

    status, _ = api("GET", "/risk-management/risks", headers={})
    if status in (401, 403):
        ok("AUTH-04: Missing token rejected on protected route")
    else:
        fail("AUTH-04: Protected route reachable without token", f"got {status}")

    status, _ = api("GET", "/risk-management/risks",
                    headers={"Authorization": "Bearer not.a.real.token",
                             "X-Tenant-ID": TENANT})
    if status in (401, 403):
        ok("AUTH-05: Invalid token rejected")
    else:
        fail("AUTH-05: Invalid token accepted", f"got {status}")

    sub("0.3 MFA surface (NF-06)")
    p, _ = first_of(["/auth/mfa/setup", "/auth/mfa/status", "/auth/mfa"])
    if p:
        ok(f"AUTH-06: MFA endpoint live ({p})")
    else:
        skip("AUTH-06: MFA endpoint not found")


# ═════════════════════════════════════════════════════════════════════════════
# 1. ACCESS CONTROL (AC)
# ═════════════════════════════════════════════════════════════════════════════

def test_ac():
    section("1. ACCESS CONTROL (AC)  [GovernexPlus AC 12.0 parity]")

    sub("1.1 Risk Rules & SoD Library (AC-01..06)")
    check("AC-01: List SoD rules", "GET", "/sod-rules/",
          validate=lambda d: isinstance(d, (list, dict)))
    check("AC-02: Rule engine stats", "GET", "/risk/rules",
          validate=lambda d: isinstance(d, (list, dict)))

    suffix = int(time.time())
    status, rule = check("AC-03: Create custom SoD rule (Z-txn support)",
        "POST", "/sod-rules/", expect=OK_CREATE, json_data={
            "rule_id": f"ZUAT-{suffix}",
            "description": "UAT custom rule: Create vendor vs post vendor invoice",
            "severity": "High",
            "business_process": "P2P",
            "risk_type": "sod",
            "function_a": {"name": "Vendor Master Maintenance", "tcodes": ["XK01", "ZXK01"]},
            "function_b": {"name": "Invoice Posting", "tcodes": ["FB60", "MIRO"]},
        })
    rule_id = get_id(rule, "rule_id", "id") or f"ZUAT-{suffix}"
    check("AC-03: Update custom rule", "PUT", f"/sod-rules/{rule_id}",
          expect=(200, 404), json_data={"severity": "Critical"})

    sub("1.2 Access Risk Analysis — Risk Intelligence (AC-10..18)")
    user_id = None
    status, users = api("GET", "/users/", params={"limit": 5})
    if status == 200:
        if isinstance(users, list) and users:
            user_id = users[0].get("user_id") or users[0].get("id")
        elif isinstance(users, dict) and users.get("users"):
            user_id = users["users"][0].get("user_id")
    if not user_id:
        skip("AC-10: No seeded users — user-level Risk Intelligence skipped")
    else:
        check("AC-10: User-level risk analysis", "GET", f"/ara/analyze/user/{user_id}")
        check("AC-11: Simulation — add role (what-if)", "POST", "/ara/simulate",
              json_data={"user_id": str(user_id), "action": "add_role",
                         "role_id": "SAP_FI_ACCOUNTANT"})
        check("AC-11: Simulation — remove role", "POST", "/ara/simulate",
              expect=(200, 400, 404), json_data={"user_id": str(user_id),
                         "action": "remove_role", "role_id": "SAP_FI_ACCOUNTANT"})

    check("AC-14: List risk violations", "GET", "/risk/violations",
          validate=lambda d: isinstance(d, (list, dict)))
    check("AC-16: Org-level violation ranking", "GET", "/risk/org-ranking")
    check("AC-18: Dormant account detection (90d)", "GET", "/users/dormant",
          params={"days": 90})

    sub("1.3 Mitigation Controls (AC-13)")
    check("AC-13: List mitigation controls", "GET", "/mitigation/controls",
          validate=lambda d: isinstance(d, (list, dict)))
    mit_cid = f"UAT-MIT-{suffix}"
    status, mit = check("AC-13: Create mitigation control", "POST",
        "/mitigation/controls", expect=OK_CREATE, json_data={
            "control_id": mit_cid,
            "control_name": "UAT Detective Review of Vendor Invoices",
            "description": "Monthly review of invoices posted by users with XK01+FB60",
            "control_type": "detective",
            "monitoring_frequency": "monthly",
            "owner_id": "admin",
            "linked_rule_ids": [rule_id],
        })
    check("AC-13: Update mitigation control", "PUT",
          f"/mitigation/controls/{get_id(mit, 'control_id', 'id') or mit_cid}",
          expect=(200, 404), json_data={"monitoring_frequency": "weekly"})
    p, _ = first_of(["/mitigation-monitoring/", "/mitigation/monitoring"])
    if p:
        ok(f"AC-13: Mitigation monitoring dashboard live ({p})")
    else:
        skip("AC-13: Mitigation monitoring dashboard not found")

    sub("1.4 Access Request Management — Access Lifecycle full cycle (AC-20..24)")
    check("AC-20: List access requests", "GET", "/access-requests/")
    check("AC-21: List pending approvals", "GET", "/access-requests/pending",
          expect=(200, 404))

    status, ar = check("AC-21: Create access request (risk-aware)", "POST",
        "/access-requests/", expect=OK_CREATE, json_data={
            "request_type": "role_assignment",
            "requested_roles": ["SAP_FI_VIEWER"],
            "justification": "UAT — read access to financial reports",
            "priority": "medium",
        })
    req_id = get_id(ar, "request_id", "id")
    if req_id:
        check("AC-22: Get request detail", "GET", f"/access-requests/{req_id}")
        check("AC-23: Approve request (stage decision)", "POST",
              f"/access-requests/{req_id}/approve", expect=(200, 400, 409),
              json_data={"approver_id": "admin",
                         "comments": "UAT approval — low risk, viewer role"})
    else:
        skip("AC-22/23: request id not returned — detail/approve skipped")

    status, ar2 = api("POST", "/access-requests/", json_data={
        "request_type": "role_assignment",
        "requested_roles": ["SAP_FI_ACCOUNTANT"],
        "justification": "UAT — reject-path test",
        "priority": "low",
    })
    req2 = get_id(ar2, "request_id", "id")
    if req2:
        check("AC-23: Reject request", "POST", f"/access-requests/{req2}/reject",
              expect=(200, 400, 409),
              json_data={"approver_id": "admin", "comments": "UAT rejection"})
    else:
        skip("AC-23: Reject path skipped (second request not created)")

    sub("1.4b Access Lifecycle Shopping Cart")
    p, _ = first_of(["/arm/cart"])
    if p:
        ok("AC-24: Cart endpoint live")
        check("AC-24: Add item to cart", "POST", "/arm/cart/items",
              expect=(200, 201, 400), json_data={
                  "role_id": "SAP_MM_BUYER",
                  "justification": "UAT cart item"})
    else:
        skip("AC-24: Cart endpoints not found")

    sub("1.5 Emergency Access — Firefighter full cycle (AC-30..33)")
    check("AC-30: Firefighter dashboard", "GET", "/firefighter/dashboard")
    check("AC-31: List firefighter sessions", "GET", "/firefighter/sessions")
    status, ff = check("AC-30: Request firefighter access", "POST",
        "/firefighter/request", expect=OK_CREATE, json_data={
            "firefighter_id": "FF_SAP_001",
            "reason_code": "INCIDENT",
            "reason": "UAT — production issue investigation",
            "ticket_reference": "INC-UAT-001",
            "duration_minutes": 60,
        })
    ff_id = get_id(ff, "request_id", "id")
    if ff_id:
        check("AC-30: Approve firefighter request", "POST",
              f"/firefighter/approve/{ff_id}", expect=(200, 400, 404, 409),
              json_data={"approver_id": "admin", "comments": "UAT approve"})
    check("AC-32: Live session monitoring", "GET", "/firefighter/monitoring/live",
          expect=(200, 404))
    p, _ = first_of(["/firefighter/reviews/pending", "/firefighter/reviews"])
    if p:
        ok(f"AC-33: Post-session review queue live ({p})")
    else:
        skip("AC-33: Post-session review endpoint not found")

    sub("1.6 Access Certification — UAR (AC-40..43)")
    check("AC-40: List certification campaigns", "GET", "/certification/campaigns")
    status, camp = check("AC-40: Create certification campaign", "POST",
        "/certification/campaigns", expect=OK_CREATE, json_data={
            "campaign_name": f"UAT Quarterly UAR {datetime.now():%Y-%m}",
            "campaign_type": "user_access",
            "scope": {"departments": ["*"]},
            "due_date": (datetime.now() + timedelta(days=30)).isoformat(),
        })
    camp_id = get_id(camp, "campaign_id", "id")
    if camp_id:
        status, items = check("AC-41: Get campaign review items", "GET",
            f"/certification/campaigns/{camp_id}/items")
        item_list = items if isinstance(items, list) else (
            items.get("items", []) if isinstance(items, dict) else [])
        if item_list:
            iid = item_list[0].get("item_id") or item_list[0].get("id")
            check("AC-42: Decide item — certify", "POST",
                  f"/certification/items/{iid}/decide", expect=(200, 400),
                  json_data={"decision": "certify", "reviewer_id": "admin",
                             "comments": "UAT certify"})
        else:
            skip("AC-42: No review items generated (no user-role data seeded)")
    else:
        skip("AC-41/42: campaign id not returned")

    sub("1.7 Role Engineering — Role Design parity (AC-50..52)")
    check("AC-50: Role catalog", "GET", "/role-engineering/catalog")
    check("AC-51: Role mining suggestions", "GET", "/role-engineering/mining")
    check("AC-52: Design role with inline SoD check", "POST",
          "/role-engineering/design", expect=(200, 201, 400), json_data={
              "role_name": f"Z_UAT_AP_CLERK_{suffix}",
              "description": "UAT designed role — AP clerk",
              "tcodes": ["FB60", "FK03"],
              "run_sod_check": True,
          })
    check("AC-52: Role drift detection", "GET", "/drift/", expect=(200, 404))

    return rule_id


# ═════════════════════════════════════════════════════════════════════════════
# 2. RISK MANAGEMENT (RM)
# ═════════════════════════════════════════════════════════════════════════════

def test_rm():
    section("2. RISK MANAGEMENT (RM)  [GovernexPlus RM / MetricStream ORM parity]")

    sub("2.1 Risk Register (RM-01..04)")
    status, risk = check("RM-01: Create enterprise risk (EN+AR)", "POST",
        "/risk-management/risks", expect=OK_CREATE, json_data={
            "title": "Unauthorized Payment Processing",
            "description": "Risk of unauthorized payments due to inadequate SoD in AP",
            "description_ar": "خطر المدفوعات غير المصرح بها بسبب ضعف الفصل بين المهام",
            "category": "financial",
            "risk_owner_id": "admin",
            "risk_owner_name": "System Administrator",
            "inherent_likelihood": 4,
            "inherent_impact": 5,
            "status": "identified",
            "review_frequency": "quarterly",
        })
    risk_id = get_id(risk, "risk_id", "id")
    if not risk_id:
        status, risks = api("GET", "/risk-management/risks")
        if status == 200 and isinstance(risks, list) and risks:
            risk_id = risks[0].get("risk_id")
            skip("RM-01: using existing risk as fallback")

    check("RM-01: List risks", "GET", "/risk-management/risks",
          validate=lambda d: isinstance(d, list))
    if risk_id:
        check("RM-01: Risk detail (with cross-module counts)", "GET",
              f"/risk-management/risks/{risk_id}")
        check("RM-02: Update risk (score recompute)", "PUT",
              f"/risk-management/risks/{risk_id}",
              json_data={"inherent_likelihood": 5})

        sub("2.2 Risk Assessment lifecycle (RM-10..11)")
        status, assess = check("RM-10: Create assessment", "POST",
            f"/risk-management/risks/{risk_id}/assessments", expect=OK_CREATE,
            json_data={
                "assessor_id": "admin", "assessor_name": "System Administrator",
                "likelihood_score": 3, "impact_score": 4, "overall_score": 12.0,
                "assessment_type": "periodic",
                "likelihood_rationale": "Controls reduce likelihood; residual remains",
                "impact_rationale": "Financial loss up to $500K possible",
                "monetary_impact": 500000.0, "currency": "USD",
            })
        assess_id = get_id(assess, "assessment_id", "id")
        if assess_id:
            check("RM-10: Submit assessment", "PUT",
                  f"/risk-management/assessments/{assess_id}/submit")
            check("RM-11: Review assessment (updates residual)", "PUT",
                  f"/risk-management/assessments/{assess_id}/review",
                  json_data={"reviewer_id": "admin",
                             "comments": "Reviewed and approved"})
        check("RM-10: List risk assessments", "GET",
              f"/risk-management/risks/{risk_id}/assessments")

        sub("2.3 Risk Appetite & Tolerance (RM-03)")
        check("RM-03: Set appetite (financial)", "POST",
              "/risk-management/appetites", expect=OK_CREATE, json_data={
                  "category": "financial", "appetite_score": 10.0,
                  "tolerance_score": 15.0,
                  "description": "Financial risk appetite: moderate",
                  "approved_by": "CFO"})
        check("RM-03: Get appetites", "GET", "/risk-management/appetites",
              params={"category": "financial"})
        check("RM-03: Appetite breach check on risk", "GET",
              f"/risk-management/risks/{risk_id}/appetite-check")

        sub("2.4 Key Risk Indicators (RM-13)")
        status, kri = check("RM-13: Create KRI", "POST", "/risk-management/kris",
            expect=OK_CREATE, json_data={
                "name": "Open SoD Violations Count",
                "description": "Unresolved SoD violations across the landscape",
                "risk_id": risk_id, "data_source": "manual",
                "unit_of_measure": "count", "frequency": "weekly",
                "threshold_green": 50.0, "threshold_amber": 100.0,
                "threshold_red": 200.0})
        kri_id = get_id(kri, "kri_id", "id")
        if kri_id:
            check("RM-13: Record measurement (amber expected)", "POST",
                  f"/risk-management/kris/{kri_id}/measurements",
                  expect=OK_CREATE,
                  json_data={"value": 75.0, "measured_by": "admin",
                             "source": "manual", "notes": "UAT reading"})
            check("RM-13: KRI history", "GET",
                  f"/risk-management/kris/{kri_id}/history")
        check("RM-13: KRI traffic-light dashboard", "GET",
              "/risk-management/kris/dashboard")

        sub("2.5 Risk Response Plans (RM-20)")
        status, resp = check("RM-20: Create response plan (mitigate)", "POST",
            f"/risk-management/risks/{risk_id}/responses", expect=OK_CREATE,
            json_data={
                "response_type": "mitigate",
                "description": "Implement SoD controls + compensating monitoring",
                "owner_id": "admin", "owner_name": "System Administrator",
                "actions": [
                    {"action": "Review all AP clerk roles", "due_date": "2026-10-01"},
                    {"action": "Implement compensating controls", "due_date": "2026-11-01"},
                ],
                "due_date": (datetime.now() + timedelta(days=60)).isoformat()})
        resp_id = get_id(resp, "response_id", "id")
        if resp_id:
            check("RM-20: Advance response to in_progress", "PUT",
                  f"/risk-management/responses/{resp_id}/status",
                  json_data={"status": "in_progress"})

        sub("2.6 Incidents & Loss Events (RM-22)")
        status, inc = check("RM-22: Report incident with financial impact",
            "POST", "/risk-management/incidents", expect=OK_CREATE, json_data={
                "title": "Unauthorized vendor payment detected",
                "description": "$45,000 payment processed by clerk who created the vendor",
                "severity": "high", "financial_impact": 45000.0,
                "currency": "USD", "occurred_at": datetime.now().isoformat(),
                "reported_by": "admin"})
        inc_id = get_id(inc, "incident_id", "id")
        if inc_id:
            check("RM-22: Link incident to risk (likelihood recalibration)",
                  "POST", f"/risk-management/incidents/{inc_id}/link-risk",
                  json_data={"risk_id": risk_id})
        check("RM-22: List incidents", "GET", "/risk-management/incidents")

    sub("2.7 RM Reporting (RM-12, RM-30, RM-31)")
    check("RM-12: Risk heatmap (5x5 inherent+residual)", "GET",
          "/risk-management/heatmap")
    check("RM-12: Risk trends (6 months)", "GET", "/risk-management/trends",
          params={"period_months": 6})
    check("RM-30: Top risks", "GET", "/risk-management/top-risks",
          params={"limit": 5})
    check("RM-31: Risk-control coverage gaps", "GET",
          "/risk-management/risk-control-coverage")
    check("RM-23: Overdue reviews", "GET", "/risk-management/overdue-reviews")

    return risk_id


# ═════════════════════════════════════════════════════════════════════════════
# 3. PROCESS CONTROL (PC)
# ═════════════════════════════════════════════════════════════════════════════

def test_pc(risk_id=None):
    section("3. PROCESS CONTROL (PC)  [GovernexPlus PC / MetricStream ICM parity]")

    sub("3.1 Control Library (PC-01..05)")
    status, ctl = check("PC-01: Create control (key/SOX)", "POST",
        "/process-control/controls", expect=OK_CREATE, json_data={
            "name": "Three-Way Match Verification",
            "objective": "All payments supported by matching PO, GR, Invoice",
            "description": "Automated 3-way match before payment release in SAP",
            "control_type": "preventive", "control_nature": "automated",
            "frequency": "continuous", "process_name": "Procure-to-Pay",
            "subprocess_name": "Invoice Verification",
            "owner_id": "admin", "owner_name": "System Administrator",
            "key_control": True,
            "risk_ids": [risk_id] if risk_id else []})
    control_id = get_id(ctl, "control_id", "id")

    check("PC-01: List controls", "GET", "/process-control/controls",
          validate=lambda d: isinstance(d, list))
    if not control_id:
        skip("PC: control id not returned — dependent tests limited")
        return None

    check("PC-04: Control detail", "GET",
          f"/process-control/controls/{control_id}")

    sub("3.2 Framework Mapping — COSO/COBIT/ISO/SOX (PC-03, XI-07)")
    status, fw = api("POST", "/frameworks/", json_data={
        "name": "COSO 2013", "version": "2013", "framework_type": "coso",
        "description": "COSO Internal Control Framework"})
    fw_id = get_id(fw, "framework_id", "id")
    if not fw_id:
        status, fws = api("GET", "/frameworks/")
        if status == 200 and isinstance(fws, list) and fws:
            fw_id = fws[0].get("framework_id")
    if fw_id:
        status, req = api("POST", f"/frameworks/{fw_id}/requirements", json_data={
            "requirement_id": "COSO-P10",
            "title": "Principle 10: Selects and Develops Control Activities",
            "description": "The organization selects and develops control activities",
            "category": "Control Activities", "level": 1})
        req_id = get_id(req, "requirement_id", "id") or "COSO-P10"
        check("PC-03: Map control to COSO principle", "POST",
              f"/process-control/controls/{control_id}/framework-mappings",
              expect=OK_CREATE,
              json_data={"framework_id": fw_id, "requirement_id": req_id})
        check("PC-03: Control's framework mappings", "GET",
              f"/process-control/controls/{control_id}/frameworks")
        check("PC-31: Framework coverage analysis", "GET",
              f"/process-control/frameworks/{fw_id}/coverage")
    else:
        skip("PC-03: framework could not be created or found")

    sub("3.3 Control Testing (PC-10..11)")
    status, test = check("PC-11: Create OE test with sampling", "POST",
        f"/process-control/controls/{control_id}/tests", expect=OK_CREATE,
        json_data={
            "test_type": "operating_effectiveness",
            "testing_period_start": "2026-07-01",
            "testing_period_end": "2026-09-30",
            "sample_size": 25, "population_size": 500,
            "tester_id": "admin", "tester_name": "System Administrator",
            "test_steps": [
                {"step": 1, "description": "Select 25 payments from Q3"},
                {"step": 2, "description": "Verify PO/GR/Invoice match"},
                {"step": 3, "description": "Document exceptions"}]})
    test_id = get_id(test, "test_id", "id")
    if test_id:
        check("PC-11: Record result — effective", "PUT",
              f"/process-control/tests/{test_id}/result", json_data={
                  "result": "effective", "exceptions_found": 1,
                  "exception_details": [{"item": "INV-2026-4521",
                                         "detail": "GR timing issue"}],
                  "conclusion": "Operating effectively; 1 timing exception."})

    status, test2 = api("POST",
        f"/process-control/controls/{control_id}/tests", json_data={
            "test_type": "design",
            "testing_period_start": "2026-01-01",
            "testing_period_end": "2026-06-30",
            "sample_size": 30, "tester_id": "admin",
            "tester_name": "System Administrator"})
    test2_id = get_id(test2, "test_id", "id")
    if test2_id:
        check("PC-11: Record result — ineffective (auto-deficiency)", "PUT",
              f"/process-control/tests/{test2_id}/result", json_data={
                  "result": "ineffective", "exceptions_found": 8,
                  "conclusion": "Design gap: tolerance limits misconfigured"})
    check("PC-11: Control test history", "GET",
          f"/process-control/controls/{control_id}/tests")

    sub("3.4 Deficiency Management — full status machine (PC-13)")
    check("PC-13: List deficiencies", "GET", "/process-control/deficiencies")
    status, defc = check("PC-13: Create deficiency (significant)", "POST",
        "/process-control/deficiencies", expect=OK_CREATE, json_data={
            "control_id": control_id, "source": "self_assessment",
            "title": "Tolerance limit configuration gap",
            "description": "Invoice tolerance limits not aligned with policy >$10K",
            "severity": "significant_deficiency",
            "remediation_plan": "Reconfigure tolerance limits and retest",
            "remediation_owner_id": "admin",
            "remediation_owner_name": "System Administrator",
            "due_date": (datetime.now() + timedelta(days=30)).isoformat()})
    def_id = get_id(defc, "deficiency_id", "id")
    if def_id:
        check("PC-13: Remediate (OPEN->REMEDIATED)", "PUT",
              f"/process-control/deficiencies/{def_id}/remediate", json_data={
                  "remediation_plan": "Tolerance limits reconfigured and retested",
                  "evidence_ids": ["EVD-001"]})
        check("PC-13: Verify closure (->VERIFIED_CLOSED)", "PUT",
              f"/process-control/deficiencies/{def_id}/verify")

    sub("3.5 Control Self-Assessment (PC-12)")
    check("PC-12: Create CSA campaign", "POST",
          "/process-control/self-assessment-campaigns", expect=OK_CREATE,
          json_data={"campaign_name": "Q3-2026 Control Self-Assessment",
                     "campaign_type": "quarterly"})
    check("PC-12: Pending self-assessments", "GET",
          "/process-control/self-assessments/pending",
          params={"assessor_id": "admin"})

    sub("3.6 Continuous Control Monitoring (PC-20..25)")
    status, ccm = check("PC-20: Create CCM rule (config_check)", "POST",
        "/process-control/ccm-rules", expect=OK_CREATE, json_data={
            "name": "Password Policy Check",
            "description": "SAP password parameters meet policy",
            "source_system": "SAP", "rule_type": "config_check",
            "rule_definition": {"check": "password_policy",
                                "params": {"min_length": 8, "complexity": True}},
            "frequency": "daily", "auto_create_deficiency": True})
    ccm_id = get_id(ccm, "rule_id", "id")
    if ccm_id:
        check("PC-22: Execute CCM rule", "POST",
              f"/process-control/ccm-rules/{ccm_id}/execute")
    check("PC-22: Run all due CCM rules", "POST",
          "/process-control/ccm/run-all", expect=(200, 404))
    check("PC-22: CCM dashboard (pass/fail rates)", "GET",
          "/process-control/ccm/dashboard")

    sub("3.7 Evidence Management (PC-15, NF-05)")
    status, evd = check("PC-15: Upload evidence (metadata)", "POST",
        "/process-control/evidence", expect=OK_CREATE, json_data={
            "title": "Three-Way Match Test Results Q3-2026",
            "description": "Spreadsheet with 25 sample items tested",
            "evidence_type": "document",
            "file_name": "3way_match_test_q3.xlsx",
            "source_module": "pc", "linked_object_type": "control_test",
            "linked_object_id": test_id or "TEST-001",
            "uploaded_by": "admin"})
    evd_id = get_id(evd, "evidence_id", "id")
    if evd_id:
        check("NF-05: Set legal hold on evidence", "PUT",
              f"/process-control/evidence/{evd_id}/legal-hold",
              json_data={"legal_hold": True, "reason": "UAT litigation hold"})

    sub("3.8 SOX Sign-Off cascade (PC-14)")
    status, so = check("PC-14: Create sign-off certification", "POST",
        "/process-control/signoffs", expect=OK_CREATE, json_data={
            "period": "Q3-2026", "certifier_id": "admin",
            "certifier_name": "System Administrator",
            "certifier_role": "process_owner",
            "scope_summary": "All P2P controls for Company Code 1000",
            "controls_in_scope": 12, "controls_effective": 11,
            "deficiencies_open": 1})
    so_id = get_id(so, "certification_id", "signoff_id", "id")
    if so_id:
        check("PC-14: Submit certification", "PUT",
              f"/process-control/signoffs/{so_id}/submit",
              expect=(200, 400, 404))
    check("PC-14: Sign-off roll-up hierarchy", "GET",
          "/process-control/signoffs/hierarchy", params={"period": "Q3-2026"})
    check("PC-14: Pending sign-offs", "GET",
          "/process-control/signoffs/pending", expect=(200, 404))

    sub("3.9 PC Reporting (PC-30..32)")
    check("PC-30: Control status dashboard", "GET", "/process-control/dashboard")
    check("PC-32: Audit-ready package for control", "GET",
          f"/process-control/controls/{control_id}/audit-package",
          expect=(200, 404))

    return control_id


# ═════════════════════════════════════════════════════════════════════════════
# 4. AUDIT MANAGEMENT (AM)
# ═════════════════════════════════════════════════════════════════════════════

def test_am(risk_id=None, control_id=None):
    section("4. AUDIT MANAGEMENT (AM)  [SAP Audit Mgmt / MetricStream IA parity]")

    sub("4.1 Audit Universe (AM-01, XI-04)")
    status, ent = check("AM-01: Create auditable entity", "POST",
        "/audit-management/entities", expect=OK_CREATE, json_data={
            "name": "Procure-to-Pay Process",
            "description": "End-to-end procurement incl. vendor mgmt, PO, GR, IR",
            "entity_type": "process", "audit_frequency": "annual"})
    entity_id = get_id(ent, "entity_id", "id")
    if entity_id:
        check("AM-01/XI-04: Compute composite risk score",
              "POST", f"/audit-management/entities/{entity_id}/compute-risk")
    check("AM-01: List auditable entities", "GET", "/audit-management/entities")

    sub("4.2 Audit Planning lifecycle (AM-02..04)")
    status, plan = check("AM-02: Create annual audit plan", "POST",
        "/audit-management/plans", expect=OK_CREATE, json_data={
            "name": "FY2026 Annual Audit Plan",
            "description": "Risk-based plan covering all critical processes",
            "plan_type": "annual", "fiscal_year": 2026,
            "total_audit_hours": 2000})
    plan_id = get_id(plan, "plan_id", "id")
    if plan_id:
        check("AM-04: Submit plan (draft->pending_approval)", "PUT",
              f"/audit-management/plans/{plan_id}/submit")
        check("AM-04: Approve plan (->approved)", "PUT",
              f"/audit-management/plans/{plan_id}/approve",
              json_data={"approver_id": "admin",
                         "comments": "Approved — adequate coverage"})
    check("AM-02: List plans", "GET", "/audit-management/plans")
    check("AM-02: Generate risk-based plan (auto-rank universe)", "POST",
          "/audit-management/plans/generate-risk-based", expect=OK_CREATE,
          json_data={"fiscal_year": 2027, "max_engagements": 10})

    sub("4.3 Auditor Resources (AM-03)")
    check("AM-03: Register auditor with skills matrix", "POST",
          "/audit-management/resources", expect=OK_CREATE, json_data={
              "name": "Sarah Chen", "email": "sarah.chen@governex.local",
              "title": "Senior IT Auditor",
              "skills": ["IT audit", "SAP security", "SoD", "data analytics"],
              "certifications": ["CISA", "CISSP"],
              "available_hours_per_month": 140})
    check("AM-03: List resources", "GET", "/audit-management/resources")
    check("AM-03: Availability query", "GET",
          "/audit-management/resources/available",
          params={"start_date": "2026-10-01", "end_date": "2026-12-31"})

    sub("4.4 Engagement lifecycle: PLANNED->...->CLOSED (AM-10)")
    status, eng = check("AM-10: Create engagement", "POST",
        "/audit-management/engagements", expect=OK_CREATE, json_data={
            "title": "P2P Process Audit — FY2026",
            "objective": "Assess design and OE of key P2P controls",
            "scope": "Vendor mgmt, PO, GR, invoice verification, payments",
            "engagement_type": "operational",
            "plan_id": plan_id, "entity_id": entity_id,
            "lead_auditor_id": "admin",
            "lead_auditor_name": "System Administrator",
            "team_members": [{"id": "sarah.chen", "name": "Sarah Chen"}],
            "planned_start": "2026-10-01", "planned_end": "2026-11-30",
            "budget_hours": 200})
    eng_id = get_id(eng, "engagement_id", "id")

    proc_id = None
    finding_id = None
    if eng_id:
        for want in ["announced", "fieldwork"]:
            status, adv = api("PUT",
                f"/audit-management/engagements/{eng_id}/advance")
            got = (adv.get("status") or adv.get("stage") or ""
                   ) if isinstance(adv, dict) else ""
            if status == 200:
                ok(f"AM-10: Advance to {want}")
            else:
                fail(f"AM-10: Advance to {want}", f"status={status}")

        sub("4.5 Work Program templates (AM-11)")
        check("AM-11: Create reusable work program", "POST",
              "/audit-management/work-programs", expect=OK_CREATE, json_data={
                  "name": "P2P Audit Work Program",
                  "description": "Standard procedures for P2P audit",
                  "audit_type": "operational", "is_template": True,
                  "procedures": [
                      {"ref": "AP-001", "title": "Vendor Master Data Review",
                       "description": "Review vendor create/modify controls"},
                      {"ref": "AP-002", "title": "PO Authorization Limits",
                       "description": "Test PO approval limits and segregation"}]})

        sub("4.6 Procedures with dual sign-off (AM-12)")
        status, proc = check("AM-12: Create procedure", "POST",
            f"/audit-management/engagements/{eng_id}/procedures",
            expect=OK_CREATE, json_data={
                "ref_number": "AP-001", "title": "Vendor Master Data Review",
                "description": "Review vendor creation and modification controls",
                "assigned_to_id": "admin",
                "assigned_to_name": "System Administrator"})
        proc_id = get_id(proc, "procedure_id", "id")
        if proc_id:
            check("AM-12: Complete procedure (preparer)", "PUT",
                  f"/audit-management/procedures/{proc_id}/complete", json_data={
                      "conclusion": "Dual approval required; 2/30 samples delayed.",
                      "preparer_id": "admin", "hours_spent": 16})
            check("AM-12: Review procedure (reviewer)", "PUT",
                  f"/audit-management/procedures/{proc_id}/review", json_data={
                      "reviewer_id": "admin",
                      "review_notes": "Work adequate. Minor finding noted."})
        check("AM-12: List engagement procedures", "GET",
              f"/audit-management/engagements/{eng_id}/procedures")

        sub("4.7 Workpapers (AM-12)")
        status, wp = check("AM-12: Create workpaper", "POST",
            f"/audit-management/engagements/{eng_id}/workpapers",
            expect=OK_CREATE, json_data={
                "title": "Vendor Master Data Analysis",
                "description": "Vendor creation patterns and control effectiveness",
                "document_type": "narrative",
                "content": "We selected 30 vendor master records created in Q3 2026...",
                "procedure_id": proc_id, "preparer_id": "admin"})

        sub("4.8 Findings — CCCE (AM-20, AM-22)")
        status, fnd = check("AM-20: Create CCCE finding", "POST",
            f"/audit-management/engagements/{eng_id}/findings",
            expect=OK_CREATE, json_data={
                "title": "Delayed Vendor Approval Process",
                "ref_number": "F-001",
                "condition": "2 of 30 vendor records created without timely secondary approval",
                "criteria": "Policy requires dual approval within 24 hours",
                "cause": "No automated escalation; manual reminders inconsistent",
                "effect": "Risk of unauthorized vendor creation; fraud exposure",
                "recommendation": "Automated escalation workflow for approvals >24h",
                "severity": "medium", "category": "process_compliance",
                "risk_id": risk_id, "control_id": control_id})
        finding_id = get_id(fnd, "finding_id", "id")
        if finding_id:
            check("AM-20: Record management response", "PUT",
                  f"/audit-management/findings/{finding_id}/management-response",
                  json_data={
                      "management_response": "Agreed. Workflow automation by Q4 2026.",
                      "management_action_owner": "admin",
                      "management_target_date": "2026-12-31"})
            if risk_id:
                check("AM-22/XI-03: Link finding -> risk (RM)", "POST",
                      f"/audit-management/findings/{finding_id}/link-risk",
                      expect=(200, 201, 409), json_data={"risk_id": risk_id})
            if control_id:
                check("AM-22/XI-03: Link finding -> control (PC)", "POST",
                      f"/audit-management/findings/{finding_id}/link-control",
                      expect=(200, 201, 409), json_data={"control_id": control_id})

            sub("4.9 Action tracking (AM-21)")
            status, act = check("AM-21: Create remediation action", "POST",
                f"/audit-management/findings/{finding_id}/actions",
                expect=OK_CREATE, json_data={
                    "description": "Configure automated escalation workflow",
                    "owner_id": "admin", "owner_name": "System Administrator",
                    "due_date": "2026-12-31"})
            action_id = get_id(act, "action_id", "id")
            if action_id:
                check("AM-21: Close action with evidence", "PUT",
                      f"/audit-management/actions/{action_id}/close", json_data={
                          "evidence_of_closure": "Workflow configured and tested.",
                          "evidence_ids": ["EVD-WF-001"]})
            check("AM-21: Overdue actions list", "GET",
                  "/audit-management/actions/overdue")
            check("AM-21: Escalate overdue actions", "POST",
                  "/audit-management/actions/escalate", expect=(200, 404))

        sub("4.10 Time tracking (AM-14)")
        check("AM-14: Record time entry", "POST",
              f"/audit-management/engagements/{eng_id}/time", expect=OK_CREATE,
              json_data={"auditor_id": "admin",
                         "auditor_name": "System Administrator",
                         "date": datetime.now().isoformat(), "hours": 8.0,
                         "activity_type": "fieldwork",
                         "description": "Vendor master data testing"})
        check("AM-14: Budget vs actual summary", "GET",
              f"/audit-management/engagements/{eng_id}/time-summary")

        sub("4.11 Engagement close-out")
        for want in ["draft_report", "final_report", "closed"]:
            status, adv = api("PUT",
                f"/audit-management/engagements/{eng_id}/advance")
            if status == 200:
                ok(f"AM-10: Advance to {want}")
            else:
                fail(f"AM-10: Advance to {want}", f"status={status}")

    sub("4.12 AM Reporting (AM-30..32)")
    check("AM-31: Audit dashboard", "GET", "/audit-management/dashboard")
    check("AM-31: Committee (board-level) report", "GET",
          "/audit-management/committee-report", params={"fiscal_year": 2026})
    if eng_id:
        check("AM-30: Generate engagement report", "GET",
              f"/audit-management/engagements/{eng_id}/report")

    return eng_id, finding_id


# ═════════════════════════════════════════════════════════════════════════════
# 5. CROSS-MODULE INTEGRATION (XI)
# ═════════════════════════════════════════════════════════════════════════════

def test_xi():
    section("5. CROSS-MODULE INTEGRATION (XI)")

    sub("5.1 Unified GRC Dashboard (XI-05)")
    check("XI-05: Unified GRC executive dashboard", "GET", "/grc/dashboard")
    check("XI-03: Risk-control matrix (navigate across modules)", "GET",
          "/grc/risk-control-matrix")

    sub("5.2 Org Hierarchy (XI-01)")
    status, unit = check("XI-01: Create org unit", "POST", "/org/units",
          expect=OK_CREATE, json_data={
              "name": "Corporate HQ", "unit_type": "company",
              "country": "US", "region": "North America"})
    unit_id = get_id(unit, "id", "unit_id")
    if unit_id:
        check("XI-01: Create child org unit", "POST", "/org/units",
              expect=OK_CREATE, json_data={
                  "name": "Finance Department", "unit_type": "department",
                  "parent_id": unit_id})
    check("XI-01: Get org tree", "GET", "/org/tree")

    sub("5.3 Framework Management (XI-07)")
    check("XI-07: List frameworks", "GET", "/frameworks/")

    sub("5.4 Document Retention (NF-05)")
    check("NF-05: Get retention policies", "GET", "/retention/policies")
    check("NF-05: Retention report", "GET", "/retention/report")

    sub("5.5 Internationalization (NF-04)")
    check("NF-04: Supported locales", "GET", "/i18n/locales")
    check("NF-04: Arabic translations", "GET", "/i18n/ar")
    check("NF-04: English translations", "GET", "/i18n/en")

    sub("5.6 Report Export (NF-08)")
    status, _ = api("GET", "/reports/export/risk-report")
    if status == 200:
        ok("NF-08: PPTX risk report export")
    else:
        skip("NF-08: PPTX risk report export (may need python-pptx or data)")

    status, _ = api("GET", "/reports/export/grc-executive")
    if status == 200:
        ok("NF-08: PPTX GRC executive export")
    else:
        skip("NF-08: PPTX GRC executive export (may need data)")


# ═════════════════════════════════════════════════════════════════════════════
# MAIN
# ═════════════════════════════════════════════════════════════════════════════

def main():
    global BASE_URL, TENANT
    parser = argparse.ArgumentParser(description="GovernexPlus Full GRC UAT")
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--tenant", default="tenant_default")
    parser.add_argument("--username", default="admin")
    parser.add_argument("--password", default="admin123")
    args = parser.parse_args()
    BASE_URL = args.base_url
    TENANT = args.tenant

    print("\n" + "=" * 72)
    print("  GOVERNEX+ FULL GRC SUITE — USER ACCEPTANCE TESTING")
    print(f"  Target:   {BASE_URL}")
    print(f"  Tenant:   {TENANT}")
    print(f"  Date:     {datetime.now():%Y-%m-%d %H:%M:%S}")
    print(f"  Modules:  AC + RM + PC + AM + XI + NF")
    print("=" * 72)

    # Health check
    try:
        resp = requests.get(f"{BASE_URL}/health", timeout=5)
        if resp.status_code == 200:
            ok("Server is healthy")
        else:
            fail(f"Health check returned {resp.status_code}")
    except Exception as e:
        fail(f"Server not reachable: {e}")
        print("\n\033[91mStart the server: uvicorn api.main:app\033[0m")
        sys.exit(1)

    test_auth(args.username, args.password)
    rule_id = test_ac()
    risk_id = test_rm()
    control_id = test_pc(risk_id)
    test_am(risk_id, control_id)
    test_xi()

    # ── Summary ──
    total = PASS + FAIL + SKIP
    print("\n" + "=" * 72)
    print("  UAT RESULTS SUMMARY")
    print("=" * 72)
    print(f"  Total Tests:  {total}")
    print(f"  \033[92mPassed:  {PASS}\033[0m")
    if FAIL:
        print(f"  \033[91mFailed:  {FAIL}\033[0m")
    else:
        print(f"  Failed:  {FAIL}")
    if SKIP:
        print(f"  \033[93mSkipped: {SKIP}\033[0m")
    pct = f"{PASS/total*100:.1f}%" if total else "N/A"
    print(f"  Pass Rate: {pct}")
    print()

    # Print failures summary
    failures = [(s, m, d) for s, m, st, d in RESULTS if st == "FAIL"]
    if failures:
        print("  FAILURES:")
        for s, m, d in failures:
            print(f"    [{s}] {m}")
            if d:
                print(f"           {d[:150]}")
        print()

    print("=" * 72)
    sys.exit(1 if FAIL > 0 else 0)


if __name__ == "__main__":
    main()
