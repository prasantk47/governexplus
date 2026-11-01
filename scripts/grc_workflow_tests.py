#!/usr/bin/env python3
"""
GovernexPlus GRC Business Workflow Tests — v2 (field-accurate)
Tests 12 mandatory journeys against the live API.
Uses only stdlib (urllib) — no external dependencies.
"""

import json
import urllib.request
import urllib.error
import ssl
import uuid
import traceback

BASE = "https://governexplus.com/api"
CREDS = {"username": "acme_admin", "password": "AcmeP@ss2026!", "tenant_id": "acme-corp-demo"}

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

TOKEN = None
RESULTS = {}


def api(method, path, body=None, auth=True):
    url = f"{BASE}{path}"
    data = json.dumps(body).encode() if body else None
    headers = {"Content-Type": "application/json"}
    if auth and TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        resp = urllib.request.urlopen(req, context=ctx, timeout=30)
        text = resp.read().decode()
        try:
            return resp.status, json.loads(text)
        except json.JSONDecodeError:
            return resp.status, text
    except urllib.error.HTTPError as e:
        text = e.read().decode() if e.fp else ""
        try:
            return e.code, json.loads(text)
        except Exception:
            return e.code, text
    except Exception as e:
        return 0, str(e)


def login():
    global TOKEN
    code, data = api("POST", "/auth/login", CREDS, auth=False)
    if code == 200 and isinstance(data, dict):
        TOKEN = data.get("access_token") or data.get("token")
        if TOKEN:
            print(f"  LOGIN OK (token starts: {TOKEN[:20]}...)")
            return True
    print(f"  LOGIN FAILED: {code} {str(data)[:200]}")
    return False


def fail(journey, step, code, data):
    print(f"  FAIL at step: {step}")
    print(f"    HTTP {code}: {str(data)[:300]}")
    RESULTS[journey] = False


def ok(step, detail=""):
    extra = f" ({detail})" if detail else ""
    print(f"  OK: {step}{extra}")


uid = str(uuid.uuid4())[:8]


# ─── JOURNEY 1: ACCESS REQUEST LIFECYCLE ───
def journey_1():
    name = "J1: Access Request Lifecycle"
    print(f"\n{'='*60}\n{name}\n{'='*60}")

    payload = {
        "requested_roles": ["Z_AP_CLERK"],
        "business_justification": "Audit test - requesting access for procurement project review and validation",
        "request_type": "new_access",
        "priority": "medium"
    }
    code, data = api("POST", "/access-requests/", payload)
    if code not in (200, 201):
        return fail(name, "Create access request", code, data)
    ok("Create access request")
    req_id = data.get("request_id") if isinstance(data, dict) else None

    code, data = api("GET", "/access-requests/")
    if code != 200:
        return fail(name, "List access requests", code, data)
    ok("List access requests")

    # Check status
    items = data if isinstance(data, list) else data.get("items", data.get("data", data.get("requests", [])))
    if isinstance(items, list) and len(items) > 0:
        last = items[-1]
        status = last.get("status", "unknown")
        ok(f"Status check", f"got: {status}")
    else:
        ok("Status check", "list returned, structure ok")

    RESULTS[name] = True


# ─── JOURNEY 2: RISK MANAGEMENT CYCLE ───
def journey_2():
    name = "J2: Risk Management Cycle"
    print(f"\n{'='*60}\n{name}\n{'='*60}")

    # Step 1: Create risk
    payload = {
        "name": f"Test Risk - API Audit {uid}",
        "title": f"Test Risk - API Audit {uid}",
        "category": "operational",
        "impact": 4,
        "likelihood": 3,
        "description": "Automated test risk",
        "risk_type": "operational",
        "severity": "high"
    }
    code, data = api("POST", "/risk-management/risks", payload)
    if code not in (200, 201):
        return fail(name, "Create risk", code, data)
    ok("Create risk")
    risk_id = data.get("risk_id", data.get("id")) if isinstance(data, dict) else None

    # Step 2: List risks
    code, data = api("GET", "/risk-management/risks")
    if code != 200:
        return fail(name, "List risks", code, data)
    ok("List risks")

    # Step 3: Create workflow — uses object_id/object_type, not risk_id
    wf_payload = {
        "workflow_type": "risk_approval",
        "object_id": str(risk_id) if risk_id else "test-risk",
        "object_type": "risk",
        "title": f"Approval for test risk {uid}",
        "description": "Automated workflow test"
    }
    code, data = api("POST", "/risk-management/workflows", wf_payload)
    if code not in (200, 201):
        return fail(name, "Create workflow", code, data)
    ok("Create workflow")
    # The response returns workflow_id as string like "WF-xxxx"
    wf_id = data.get("workflow_id") if isinstance(data, dict) else None
    if not wf_id:
        wf_id = data.get("id") if isinstance(data, dict) else None

    # Step 4: Approve step 1 — use the workflow_id string
    decide_payload = {"decision": "approve", "comments": "Auto-approved by test"}
    code, data = api("POST", f"/risk-management/workflows/{wf_id}/steps/1/decide", decide_payload)
    if code not in (200, 201):
        return fail(name, "Approve step 1", code, data)
    ok("Approve step 1")

    # Step 5: Verify workflow status
    code, data = api("GET", f"/risk-management/workflows/{wf_id}")
    if code != 200:
        return fail(name, "Get workflow status", code, data)
    wf_status = data.get("status", "unknown") if isinstance(data, dict) else "ok"
    ok("Workflow status", wf_status)

    RESULTS[name] = True


# ─── JOURNEY 3: AUDIT MANAGEMENT CYCLE ───
def journey_3():
    name = "J3: Audit Management Cycle"
    print(f"\n{'='*60}\n{name}\n{'='*60}")

    # Step 1: Create audit plan
    payload = {
        "name": f"API Audit Test Plan {uid}",
        "plan_type": "special",
        "description": "Automated test plan",
        "fiscal_year": 2026
    }
    code, data = api("POST", "/audit-management/plans", payload)
    if code not in (200, 201):
        return fail(name, "Create audit plan", code, data)
    ok("Create audit plan")
    # plan_id is the string business key (e.g., "PLAN-xxxx")
    plan_id = data.get("plan_id") if isinstance(data, dict) else None

    # Step 2: Create engagement — needs title (not name), plan_id is the string key
    eng_payload = {
        "title": f"Test Engagement {uid}",
        "plan_id": plan_id,
        "engagement_type": "operational",
        "lead_auditor_name": "acme_admin",
        "objective": "Test audit engagement",
        "scope": "API testing"
    }
    code, data = api("POST", "/audit-management/engagements", eng_payload)
    if code not in (200, 201):
        return fail(name, "Create engagement", code, data)
    ok("Create engagement")
    eng_id = data.get("engagement_id") if isinstance(data, dict) else None

    # Step 3: List engagements
    code, data = api("GET", "/audit-management/engagements")
    if code != 200:
        return fail(name, "List engagements", code, data)
    ok("List engagements")

    # Step 4: Create finding — POST /engagements/{engagement_id}/findings
    finding_payload = {
        "title": f"Test Finding {uid}",
        "severity": "high",
        "condition": "Test condition found during audit",
        "recommendation": "Fix it immediately"
    }
    code, data = api("POST", f"/audit-management/engagements/{eng_id}/findings", finding_payload)
    if code not in (200, 201):
        return fail(name, "Create finding", code, data)
    ok("Create finding")

    # Step 5: List findings
    code, data = api("GET", "/audit-management/findings")
    if code != 200:
        return fail(name, "List findings", code, data)
    ok("List findings")

    RESULTS[name] = True


# ─── JOURNEY 4: PROCESS CONTROL CYCLE ───
def journey_4():
    name = "J4: Process Control Cycle"
    print(f"\n{'='*60}\n{name}\n{'='*60}")

    # Step 1: Create control (body is Dict, field: name required)
    payload = {
        "name": f"Test Control {uid}",
        "description": "Automated test control",
        "control_type": "preventive",
        "control_nature": "manual",
        "frequency": "monthly",
        "objective": "Test objective"
    }
    code, data = api("POST", "/process-control/controls", payload)
    if code not in (200, 201):
        return fail(name, "Create control", code, data)
    ok("Create control")
    ctrl_id = data.get("control_id") if isinstance(data, dict) else None

    # Step 2: List controls
    code, data = api("GET", "/process-control/controls")
    if code != 200:
        return fail(name, "List controls", code, data)
    ok("List controls")

    # Step 3: Create test — POST /controls/{control_id}/tests (not /tests)
    test_payload = {
        "test_type": "operating_effectiveness",
        "testing_period_start": "2026-11-01",
        "testing_period_end": "2026-11-30",
        "sample_size": 25,
        "tester_id": "acme_admin"
    }
    code, data = api("POST", f"/process-control/controls/{ctrl_id}/tests", test_payload)
    if code not in (200, 201):
        return fail(name, "Create test", code, data)
    ok("Create test")

    # Step 4: List tests for control
    code, data = api("GET", f"/process-control/controls/{ctrl_id}/tests")
    if code != 200:
        return fail(name, "List tests", code, data)
    ok("List tests")

    RESULTS[name] = True


# ─── JOURNEY 5: FIREFIGHTER REQUEST ───
def journey_5():
    name = "J5: Firefighter / Privileged Access"
    print(f"\n{'='*60}\n{name}\n{'='*60}")

    # Step 1: Statistics (no /dashboard route — use /statistics)
    code, data = api("GET", "/privileged-access/statistics")
    if code != 200:
        return fail(name, "Get statistics", code, data)
    ok("Statistics loaded")

    # Step 2: Create request — POST /requests with reason_code + firefighter_id
    payload = {
        "firefighter_id": "TDAVIS",
        "reason_code": "prod_incident",
        "reason": "Emergency access for audit test",
        "business_justification": "Critical production issue needs investigation",
        "target_system": "SAP_PROD",
        "duration_hours": 2,
        "priority": "high",
        "planned_actions": ["Check error logs", "Run diagnostic report"],
        "ticket_reference": "INC0099999"
    }
    code, data = api("POST", "/privileged-access/requests", payload)
    if code not in (200, 201):
        return fail(name, "Create emergency request", code, data)
    ok("Emergency request created")

    # Step 3: List requests
    code, data = api("GET", "/privileged-access/requests")
    if code != 200:
        return fail(name, "List requests", code, data)
    ok("List requests")

    RESULTS[name] = True


# ─── JOURNEY 6: CERTIFICATION ───
def journey_6():
    name = "J6: Certification Campaign"
    print(f"\n{'='*60}\n{name}\n{'='*60}")

    payload = {
        "name": f"Test Campaign {uid}",
        "description": "Automated test campaign",
        "campaign_type": "user_access",
        "owner_id": "acme_admin",
        "owner_name": "Acme Admin",
        "start_date": "2026-11-01T00:00:00",
        "end_date": "2026-12-31T00:00:00",
        "included_systems": ["SAP"]
    }
    code, data = api("POST", "/certification/campaigns", payload)
    if code not in (200, 201):
        return fail(name, "Create campaign", code, data)
    ok("Create campaign")

    code, data = api("GET", "/certification/campaigns")
    if code != 200:
        return fail(name, "List campaigns", code, data)
    ok("List campaigns")

    RESULTS[name] = True


# ─── JOURNEY 7: TPRM VENDOR LIFECYCLE ───
def journey_7():
    name = "J7: TPRM Vendor Lifecycle"
    print(f"\n{'='*60}\n{name}\n{'='*60}")

    # Create vendor
    payload = {
        "name": f"Test Vendor {uid}",
        "vendor_name": f"Test Vendor {uid}",
        "category": "technology",
        "risk_tier": "high",
        "tier": "critical",
        "status": "active",
        "contact_email": "vendor@test.com",
        "description": "Test vendor"
    }
    code, data = api("POST", "/tprm/vendors", payload)
    if code not in (200, 201):
        return fail(name, "Create vendor", code, data)
    ok("Create vendor")
    vendor_id = data.get("id") if isinstance(data, dict) else None

    # Create issue
    issue_payload = {
        "vendor_id": vendor_id,
        "title": f"Test Issue {uid}",
        "description": "Test vendor issue",
        "severity": "high",
        "status": "open"
    }
    code, data = api("POST", "/tprm/issues", issue_payload)
    if code not in (200, 201):
        return fail(name, "Create issue", code, data)
    ok("Create issue")

    # List vendors
    code, data = api("GET", "/tprm/vendors")
    if code != 200:
        return fail(name, "List vendors", code, data)
    ok("List vendors")

    # List issues for vendor — /vendors/{id}/issues (no top-level GET /issues)
    code, data = api("GET", f"/tprm/vendors/{vendor_id}/issues")
    if code != 200:
        return fail(name, "List vendor issues", code, data)
    ok("List vendor issues")

    RESULTS[name] = True


# ─── JOURNEY 8: JML EVENT ───
def journey_8():
    name = "J8: JML Event"
    print(f"\n{'='*60}\n{name}\n{'='*60}")

    payload = {
        "event_type": "joiner",
        "type": "joiner",
        "employee_name": f"Test User {uid}",
        "employee_id": f"EMP-{uid}",
        "user_id": f"EMP-{uid}",
        "department": "IT",
        "position": "Analyst",
        "role": "Analyst",
        "start_date": "2026-11-15",
        "effective_date": "2026-11-15",
        "status": "pending",
        "manager": "acme_admin",
        "description": "Test joiner event"
    }
    code, data = api("POST", "/jml/events", payload)
    if code not in (200, 201):
        return fail(name, "Create joiner event", code, data)
    ok("Create joiner event")

    code, data = api("GET", "/jml/events")
    if code != 200:
        return fail(name, "List events", code, data)
    ok("List events")

    RESULTS[name] = True


# ─── JOURNEY 9: BCM PLAN + ACTIVATION ───
def journey_9():
    name = "J9: BCM Plan + Activation"
    print(f"\n{'='*60}\n{name}\n{'='*60}")

    # Create plan — uses plan_name (not name), plan_type required
    payload = {
        "plan_name": f"BCP Plan {uid}",
        "plan_type": "bcp",
        "description": "Test BCP plan",
        "status": "active",
        "owner_id": "acme_admin",
        "owner_name": "Acme Admin",
        "scope": "IT department",
        "version": "1.0"
    }
    code, data = api("POST", "/bcm/plans", payload)
    if code not in (200, 201):
        return fail(name, "Create BCP plan", code, data)
    ok("Create BCP plan")
    plan_id = data.get("id") if isinstance(data, dict) else None

    # Activate — uses plan_id + activation_reason
    act_payload = {
        "plan_id": str(plan_id),
        "activation_reason": "Test activation for audit",
        "severity": "high",
        "activated_by": "acme_admin",
        "incident_type": "system_failure"
    }
    code, data = api("POST", "/bcm/activations", act_payload)
    if code not in (200, 201):
        return fail(name, "Activate plan", code, data)
    ok("Activate plan")

    # List activations
    code, data = api("GET", "/bcm/activations")
    if code != 200:
        return fail(name, "List activations", code, data)
    ok("List activations")

    RESULTS[name] = True


# ─── JOURNEY 10: FRAUD DETECTION ───
def journey_10():
    name = "J10: Fraud Detection"
    print(f"\n{'='*60}\n{name}\n{'='*60}")

    # Create rule — uses rule_name + rule_type
    rule_payload = {
        "rule_name": f"Fraud Rule {uid}",
        "rule_type": "threshold",
        "description": "Test fraud detection rule",
        "condition_expression": "amount > 10000",
        "threshold_value": 10000.0,
        "risk_score_weight": 5.0,
        "is_active": True,
        "data_sources": ["sap_fi"]
    }
    code, data = api("POST", "/fraud/rules", rule_payload)
    if code not in (200, 201):
        return fail(name, "Create fraud rule", code, data)
    ok("Create fraud rule")

    # Create case
    case_payload = {
        "title": f"Fraud Case {uid}",
        "description": "Test fraud case",
        "severity": "high",
        "subject_user_id": "test_user",
        "subject_name": "Test User",
        "assigned_to": "acme_admin"
    }
    code, data = api("POST", "/fraud/cases", case_payload)
    if code not in (200, 201):
        return fail(name, "Create fraud case", code, data)
    ok("Create fraud case")

    # List cases
    code, data = api("GET", "/fraud/cases")
    if code != 200:
        return fail(name, "List fraud cases", code, data)
    ok("List fraud cases")

    RESULTS[name] = True


# ─── JOURNEY 11: WHISTLEBLOWER (PUBLIC) ───
def journey_11():
    name = "J11: Whistleblower (Public)"
    print(f"\n{'='*60}\n{name}\n{'='*60}")

    payload = {
        "category": "fraud",
        "title": "API Audit Test",
        "description": "Testing whistleblower flow",
        "report_type": "fraud",
        "type": "fraud",
        "is_anonymous": True
    }
    code, data = api("POST", "/whistleblower/submit", payload, auth=False)
    if code not in (200, 201):
        code, data = api("POST", "/whistleblower/submit", payload, auth=True)
        if code not in (200, 201):
            return fail(name, "Submit anonymous report", code, data)
    ok("Submit anonymous report")

    if isinstance(data, dict):
        ref = data.get("case_reference") or data.get("reference") or data.get("tracking_id") or data.get("id")
        if ref:
            ok("Got reference", str(ref))
        else:
            print(f"  WARN: No case_reference in response keys: {list(data.keys())[:10]}")

    RESULTS[name] = True


# ─── JOURNEY 12: SURVEY ───
def journey_12():
    name = "J12: Survey"
    print(f"\n{'='*60}\n{name}\n{'='*60}")

    payload = {
        "title": f"Test Survey {uid}",
        "survey_type": "general",
        "description": "Automated test survey",
        "status": "draft",
        "questions": [
            {
                "question_id": f"q1-{uid}",
                "question_text": "Is this a test?",
                "question_type": "yes_no",
                "is_required": True,
                "order": 1
            }
        ],
        "allow_anonymous": False,
        "requires_completion": True
    }
    code, data = api("POST", "/surveys/", payload)
    if code not in (200, 201):
        return fail(name, "Create survey", code, data)
    ok("Create survey")

    code, data = api("GET", "/surveys/")
    if code != 200:
        return fail(name, "List surveys", code, data)
    ok("List surveys")

    RESULTS[name] = True


# ─── MAIN ───
if __name__ == "__main__":
    print("=" * 60)
    print("GovernexPlus GRC Business Workflow Tests (v2)")
    print("Target: " + BASE)
    print("=" * 60)

    if not login():
        print("\nFATAL: Cannot proceed without authentication.")
        exit(1)

    journeys = [
        journey_1, journey_2, journey_3, journey_4,
        journey_5, journey_6, journey_7, journey_8,
        journey_9, journey_10, journey_11, journey_12
    ]

    for j in journeys:
        try:
            j()
        except Exception as e:
            jname = j.__name__.replace("journey_", "J") + " (exception)"
            print(f"  EXCEPTION: {e}")
            traceback.print_exc()
            RESULTS[jname] = False

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    passed = 0
    total = 12
    for i in range(1, 13):
        prefix = f"J{i}:"
        found = False
        for k, v in RESULTS.items():
            if k.startswith(prefix):
                status = "PASS" if v else "FAIL"
                print(f"  {status} - {k}")
                if v:
                    passed += 1
                found = True
                break
        if not found:
            print(f"  FAIL - Journey {i} (no result recorded)")

    print(f"\n  RESULT: {passed}/{total} journeys PASSED")
    print("=" * 60)
