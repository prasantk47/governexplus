#!/usr/bin/env python3
"""Quick UAT smoke test via TestClient — no server needed."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)
PASS = FAIL = 0

def check(name, method, path, json_data=None, headers=None, expect=(200,)):
    global PASS, FAIL
    r = client.request(method, path, json=json_data, headers=headers)
    if r.status_code in expect:
        PASS += 1
        print(f"  \033[92mPASS\033[0m  {name} ({r.status_code})")
    else:
        FAIL += 1
        print(f"  \033[91mFAIL\033[0m  {name} (got {r.status_code}, expected {expect})")
        print(f"        {str(r.text)[:150]}")
    return r

# === AUTH ===
print("\n=== AUTH ===")
r = client.post("/auth/login", json={"username": "admin", "password": "admin123", "tenant_id": "tenant_default"})
if r.status_code != 200:
    print(f"LOGIN FAILED: {r.status_code} {r.text[:200]}")
    sys.exit(1)
token = r.json()["access_token"]
H = {"Authorization": f"Bearer {token}", "X-Tenant-ID": "tenant_default"}
PASS += 1
print(f"  \033[92mPASS\033[0m  Login")
check("Profile", "GET", "/auth/profile", headers=H, expect=(200, 404))
# Negative auth
r2 = client.post("/auth/login", json={"username": "admin", "password": "wrong", "tenant_id": "tenant_default"})
if r2.status_code in (400, 401, 403, 422):
    PASS += 1; print(f"  \033[92mPASS\033[0m  Wrong password rejected ({r2.status_code})")
else:
    FAIL += 1; print(f"  \033[91mFAIL\033[0m  Wrong password NOT rejected ({r2.status_code})")

# === AC ===
print("\n=== ACCESS CONTROL ===")
check("SoD Rules", "GET", "/sod-rules", headers=H, expect=(200, 404))
check("Risk Rules", "GET", "/risk/rules", headers=H)
check("Violations", "GET", "/risk/violations", headers=H, expect=(200, 404))
check("Access Requests", "GET", "/access-requests/", headers=H)
check("Firefighter Dashboard", "GET", "/firefighter/dashboard", headers=H, expect=(200, 404))
check("Certification Campaigns", "GET", "/certification/campaigns", headers=H)
check("Mitigation Controls", "GET", "/mitigation/controls", headers=H)
check("Role Catalog", "GET", "/role-engineering/catalog", headers=H)
check("ARM Cart", "POST", "/arm/cart", headers=H, expect=(200, 201, 404, 405, 422))

# === RM ===
print("\n=== RISK MANAGEMENT ===")
r = check("Create Risk", "POST", "/risk-management/risks", headers=H, expect=(200,201),
    json_data={"title": "UAT Test Risk", "description": "Test", "category": "financial",
               "risk_owner_id": "admin", "inherent_likelihood": 4, "inherent_impact": 5, "status": "identified"})
risk_id = r.json().get("risk_id") if r.status_code in (200,201) else None
check("List Risks", "GET", "/risk-management/risks", headers=H)
if risk_id:
    check("Risk Detail", "GET", f"/risk-management/risks/{risk_id}", headers=H)
    check("Create Assessment", "POST", f"/risk-management/risks/{risk_id}/assessments", headers=H, expect=(200,201),
        json_data={"assessor_id": "admin", "likelihood_score": 3, "impact_score": 4, "assessment_type": "periodic"})
    check("Set Appetite", "POST", "/risk-management/appetites", headers=H, expect=(200,201),
        json_data={"category": "financial", "appetite_score": 10, "tolerance_score": 15})
    check("Appetite Check", "GET", f"/risk-management/risks/{risk_id}/appetite-check", headers=H)
    check("Create KRI", "POST", "/risk-management/kris", headers=H, expect=(200,201),
        json_data={"name": "UAT KRI", "data_source": "manual", "threshold_green": 50, "threshold_amber": 100, "threshold_red": 200})
    check("Create Response", "POST", f"/risk-management/risks/{risk_id}/responses", headers=H, expect=(200,201),
        json_data={"response_type": "mitigate", "description": "Fix it", "owner_id": "admin"})
    check("Create Incident", "POST", "/risk-management/incidents", headers=H, expect=(200,201),
        json_data={"title": "UAT Incident", "severity": "high", "reported_by": "admin"})
check("Heatmap", "GET", "/risk-management/heatmap", headers=H)
check("Top Risks", "GET", "/risk-management/top-risks", headers=H)
check("KRI Dashboard", "GET", "/risk-management/kris/dashboard", headers=H)
check("Overdue Reviews", "GET", "/risk-management/overdue-reviews", headers=H)

# === PC ===
print("\n=== PROCESS CONTROL ===")
r = check("Create Control", "POST", "/process-control/controls", headers=H, expect=(200,201),
    json_data={"name": "UAT Control", "control_type": "preventive", "control_nature": "automated",
               "frequency": "daily", "process_name": "P2P", "owner_id": "admin"})
ctl_id = r.json().get("control_id") if r.status_code in (200,201) else None
check("List Controls", "GET", "/process-control/controls", headers=H)
if ctl_id:
    check("Control Detail", "GET", f"/process-control/controls/{ctl_id}", headers=H)
    r2 = check("Create Test", "POST", f"/process-control/controls/{ctl_id}/tests", headers=H, expect=(200,201),
        json_data={"test_type": "operating_effectiveness", "sample_size": 25, "tester_id": "admin"})
    test_id = r2.json().get("test_id") if r2.status_code in (200,201) else None
    if test_id:
        check("Record Test Result", "PUT", f"/process-control/tests/{test_id}/result", headers=H,
            json_data={"result": "effective", "exceptions_found": 0, "conclusion": "OK"})
    check("Create Deficiency", "POST", "/process-control/deficiencies", headers=H, expect=(200,201),
        json_data={"control_id": ctl_id, "source": "test", "title": "UAT Def", "severity": "control_gap"})
    check("Create CCM Rule", "POST", "/process-control/ccm-rules", headers=H, expect=(200,201),
        json_data={"name": "UAT CCM", "source_system": "SAP", "rule_type": "config_check",
                   "rule_definition": {"check": "test"}, "frequency": "daily"})
    check("Upload Evidence", "POST", "/process-control/evidence", headers=H, expect=(200,201),
        json_data={"title": "UAT Evidence", "evidence_type": "document", "source_module": "pc",
                   "linked_object_type": "control_test", "linked_object_id": test_id or "T1", "uploaded_by": "admin"})
    check("Create Signoff", "POST", "/process-control/signoffs", headers=H, expect=(200,201),
        json_data={"period": "Q3-2026", "certifier_id": "admin", "certifier_name": "Admin",
                   "certifier_role": "process_owner", "controls_in_scope": 10, "controls_effective": 9, "deficiencies_open": 1})
check("Deficiencies", "GET", "/process-control/deficiencies", headers=H)
check("CCM Dashboard", "GET", "/process-control/ccm/dashboard", headers=H)
check("PC Dashboard", "GET", "/process-control/dashboard", headers=H)

# === AM ===
print("\n=== AUDIT MANAGEMENT ===")
r = check("Create Entity", "POST", "/audit-management/entities", headers=H, expect=(200,201),
    json_data={"name": "UAT P2P Process", "entity_type": "process", "audit_frequency": "annual"})
entity_id = r.json().get("entity_id") if r.status_code in (200,201) else None
r = check("Create Plan", "POST", "/audit-management/plans", headers=H, expect=(200,201),
    json_data={"name": "FY2026 Plan", "plan_type": "annual", "fiscal_year": 2026})
plan_id = r.json().get("plan_id") if r.status_code in (200,201) else None
check("List Plans", "GET", "/audit-management/plans", headers=H)
r = check("Create Engagement", "POST", "/audit-management/engagements", headers=H, expect=(200,201),
    json_data={"title": "UAT Audit", "engagement_type": "operational", "lead_auditor_id": "admin"})
eng_id = r.json().get("engagement_id") if r.status_code in (200,201) else None
if eng_id:
    check("Advance Engagement", "PUT", f"/audit-management/engagements/{eng_id}/advance", headers=H, expect=(200, 422))
    r = check("Create Finding (CCCE)", "POST", f"/audit-management/engagements/{eng_id}/findings", headers=H, expect=(200,201),
        json_data={"title": "UAT Finding", "condition": "Gap found", "criteria": "Policy requires X",
                   "cause": "Process gap", "effect": "Risk exposure", "recommendation": "Fix it", "severity": "medium"})
    finding_id = r.json().get("finding_id") if r.status_code in (200,201) else None
    if finding_id:
        check("Management Response", "PUT", f"/audit-management/findings/{finding_id}/management-response", headers=H,
            json_data={"management_response": "Agreed", "management_action_owner": "admin", "management_target_date": "2026-12-31"})
        check("Create Action", "POST", f"/audit-management/findings/{finding_id}/actions", headers=H, expect=(200,201),
            json_data={"description": "Fix the gap", "owner_id": "admin", "due_date": "2026-12-31"})
    check("Register Resource", "POST", "/audit-management/resources", headers=H, expect=(200,201),
        json_data={"name": "UAT Auditor", "email": "auditor@test.com", "skills": ["IT audit"]})
check("AM Dashboard", "GET", "/audit-management/dashboard", headers=H)
check("Committee Report", "GET", "/audit-management/committee-report", headers=H)
check("Overdue Actions", "GET", "/audit-management/actions/overdue", headers=H)

# === XI ===
print("\n=== CROSS-MODULE INTEGRATION ===")
check("GRC Dashboard", "GET", "/grc/dashboard", headers=H)
check("Risk-Control Matrix", "GET", "/grc/risk-control-matrix", headers=H)
check("Org Units", "GET", "/org/units", headers=H)
check("Frameworks", "GET", "/frameworks/", headers=H)

# === GRC Intelligence ===
print("\n=== GRC INTELLIGENCE ===")
check("Health Score", "GET", "/grc-intelligence/health", headers=H)
check("Attention Items", "GET", "/grc-intelligence/attention", headers=H)
check("Dashboard (CFO)", "GET", "/grc-intelligence/dashboard/cfo", headers=H)
check("Dashboard (CISO)", "GET", "/grc-intelligence/dashboard/ciso", headers=H)
check("Dashboard (CAE)", "GET", "/grc-intelligence/dashboard/cae", headers=H)
if risk_id:
    check("Explain Risk", "POST", "/grc-intelligence/explain", headers=H,
        json_data={"object_type": "risk", "object_id": risk_id})
    check("Investigate Risk", "POST", "/grc-intelligence/investigate", headers=H,
        json_data={"risk_id": risk_id})
    check("Recommend", "POST", "/grc-intelligence/recommend", headers=H, expect=(200, 400, 404),
        json_data={"object_type": "deficiency", "object_id": "test"})
check("Fix Preview", "POST", "/grc-intelligence/fix-preview", headers=H,
    json_data={"action": "remove_access", "target_id": "USR001"})

# === Summary ===
total = PASS + FAIL
print(f"\n{'='*60}")
print(f"  RESULTS: {PASS} PASS / {FAIL} FAIL / {total} TOTAL")
print(f"  PASS RATE: {PASS/total*100:.0f}%" if total else "  NO TESTS RUN")
print(f"{'='*60}")
sys.exit(1 if FAIL else 0)
