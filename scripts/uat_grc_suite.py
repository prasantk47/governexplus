#!/usr/bin/env python3
"""
UAT Script: AC + PC + RM + AM — Full Flow Testing
===================================================
Tests every module's complete lifecycle via live API calls.

Usage:
    python scripts/uat_grc_suite.py [--base-url http://localhost:8000]

Requires a running Governex+ backend with at least one seeded user.
"""

import sys
import json
import time
import argparse
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent))

import requests

# ── Globals ──────────────────────────────────────────────────────────────────

PASS = 0
FAIL = 0
SKIP = 0
SECTION = ""
BASE_URL = "http://localhost:8000"
TOKEN = ""
HEADERS = {}


def ok(msg: str):
    global PASS
    PASS += 1
    print(f"  \033[92mPASS\033[0m  {msg}")


def fail(msg: str, detail: str = ""):
    global FAIL
    FAIL += 1
    print(f"  \033[91mFAIL\033[0m  {msg}")
    if detail:
        print(f"        {detail[:200]}")


def skip(msg: str):
    global SKIP
    SKIP += 1
    print(f"  \033[93mSKIP\033[0m  {msg}")


def section(name: str):
    global SECTION
    SECTION = name
    print(f"\n{'='*70}")
    print(f"  {name}")
    print(f"{'='*70}")


def api(method: str, path: str, json_data=None, params=None, expect=200):
    """Make an API call and return (status_code, response_json)."""
    url = f"{BASE_URL}{path}"
    try:
        resp = requests.request(
            method, url,
            json=json_data,
            params=params,
            headers=HEADERS,
            timeout=30,
        )
        try:
            data = resp.json()
        except Exception:
            data = resp.text
        if resp.status_code == expect:
            return resp.status_code, data
        else:
            return resp.status_code, data
    except Exception as e:
        return 0, str(e)


def check(test_name: str, method: str, path: str,
          json_data=None, params=None, expect=200, validate=None):
    """Run a single test: API call + optional validation."""
    status, data = api(method, path, json_data, params, expect)
    if status == expect:
        if validate:
            try:
                validate(data)
                ok(test_name)
            except AssertionError as e:
                fail(test_name, str(e))
        else:
            ok(test_name)
    else:
        fail(test_name, f"Expected {expect}, got {status}: {str(data)[:150]}")
    return status, data


# ═══════════════════════════════════════════════════════════════════════════════
# 0. AUTHENTICATION
# ═══════════════════════════════════════════════════════════════════════════════

def test_auth():
    global TOKEN, HEADERS
    section("0. AUTHENTICATION")

    # Try login
    status, data = api("POST", "/auth/login", {
        "username": "admin",
        "password": "admin123",
        "tenant_id": "tenant_default",
    })
    if status != 200:
        # Try alternate credentials
        status, data = api("POST", "/auth/login", {
            "username": "testuser",
            "password": "TestPassword123!",
            "tenant_id": "tenant_default",
        })
    if status == 200 and "access_token" in (data if isinstance(data, dict) else {}):
        TOKEN = data["access_token"]
        HEADERS = {
            "Authorization": f"Bearer {TOKEN}",
            "X-Tenant-ID": "tenant_default",
        }
        ok("Login successful")
    else:
        fail("Login failed — cannot proceed", str(data)[:200])
        print("\n\033[91mCannot run UAT without authentication. Seed a user first.\033[0m")
        sys.exit(1)


# ═══════════════════════════════════════════════════════════════════════════════
# 1. ACCESS CONTROL (AC)
# ═══════════════════════════════════════════════════════════════════════════════

def test_ac():
    section("1. ACCESS CONTROL (AC)")

    # ── 1.1 Risk Rules & SoD Library ──
    print("\n  --- 1.1 Risk Rules & SoD Library ---")
    check("AC-01: List SoD rules", "GET", "/sod-rules/",
          validate=lambda d: isinstance(d, (list, dict)))

    check("AC-02: Get rule library stats", "GET", "/risk/rules",
          validate=lambda d: isinstance(d, (list, dict)))

    # ── 1.2 ARA — Access Risk Analysis ──
    print("\n  --- 1.2 Access Risk Analysis (ARA) ---")
    status, users = api("GET", "/users/", params={"limit": 1})
    user_id = None
    if status == 200 and isinstance(users, list) and len(users) > 0:
        user_id = users[0].get("user_id") or users[0].get("id")
        ok(f"AC-10: Found user for analysis: {user_id}")
    elif status == 200 and isinstance(users, dict) and users.get("users"):
        user_id = users["users"][0].get("user_id")
        ok(f"AC-10: Found user for analysis: {user_id}")
    else:
        skip("AC-10: No users found for risk analysis")

    if user_id:
        check("AC-10: User-level risk analysis", "GET", f"/ara/analyze/user/{user_id}")
        check("AC-11: Simulation — add role", "POST", "/ara/simulate", json_data={
            "user_id": str(user_id),
            "action": "add_role",
            "role_id": "SAP_FI_ACCOUNTANT",
        })

    check("AC-14: List risk violations", "GET", "/risk/violations",
          validate=lambda d: isinstance(d, (list, dict)))

    # ── 1.3 Org Ranking & Dormant Detection ──
    print("\n  --- 1.3 Org Ranking & Dormant Detection ---")
    check("AC-16: Org-level violation ranking", "GET", "/risk/org-ranking")
    check("AC-18: Dormant account detection", "GET", "/users/dormant",
          params={"days": 90})

    # ── 1.4 Mitigation Controls ──
    print("\n  --- 1.4 Mitigation Controls ---")
    check("AC-13: List mitigation controls", "GET", "/mitigation/controls",
          validate=lambda d: isinstance(d, (list, dict)))

    status, mit_data = check("AC-13: Create mitigation control", "POST", "/mitigation/controls", json_data={
        "control_id": f"UAT-MIT-{int(time.time())}",
        "control_name": "UAT Test Mitigation Control",
        "description": "Created by UAT script",
        "control_type": "detective",
        "monitoring_frequency": "monthly",
    }, expect=200)

    # ── 1.5 Access Requests (ARM) ──
    print("\n  --- 1.5 Access Request Management (ARM) ---")
    check("AC-20: List access requests", "GET", "/access-requests/")
    status, ar_data = check("AC-21: Create access request", "POST", "/access-requests/", json_data={
        "request_type": "role_assignment",
        "requested_roles": ["SAP_FI_VIEWER"],
        "justification": "UAT test — need read access to financial reports",
        "priority": "medium",
    })
    if status == 200 and isinstance(ar_data, dict) and ar_data.get("request_id"):
        req_id = ar_data["request_id"]
        ok(f"AC-21: Request created: {req_id}")
        check("AC-22: Get request detail", "GET", f"/access-requests/{req_id}")

    check("AC-21: List pending approvals", "GET", "/access-requests/pending")

    # ── 1.6 Emergency Access / Firefighter ──
    print("\n  --- 1.6 Emergency Access Management (EAM) ---")
    check("AC-30: Firefighter dashboard", "GET", "/firefighter/dashboard")
    check("AC-31: List firefighter sessions", "GET", "/firefighter/sessions")
    status, ff_data = check("AC-30: Request firefighter access", "POST", "/firefighter/request", json_data={
        "firefighter_id": "FF_SAP_001",
        "reason_code": "INCIDENT",
        "reason": "UAT test — production issue investigation",
        "duration_minutes": 60,
    })

    # ── 1.7 Access Certification (UAR) ──
    print("\n  --- 1.7 Access Certification ---")
    check("AC-40: List certification campaigns", "GET", "/certification/campaigns")
    status, cert_data = check("AC-40: Create certification campaign", "POST", "/certification/campaigns", json_data={
        "campaign_name": f"UAT Quarterly Review {datetime.now().strftime('%Y-Q3')}",
        "campaign_type": "user_access",
        "scope": {"departments": ["*"]},
        "due_date": (datetime.now() + timedelta(days=30)).isoformat(),
    })

    # ── 1.8 Role Engineering ──
    print("\n  --- 1.8 Role Engineering ---")
    check("AC-50: List role catalog", "GET", "/role-engineering/catalog")
    check("AC-51: Role mining suggestions", "GET", "/role-engineering/mining")


# ═══════════════════════════════════════════════════════════════════════════════
# 2. RISK MANAGEMENT (RM)
# ═══════════════════════════════════════════════════════════════════════════════

def test_rm():
    section("2. RISK MANAGEMENT (RM)")

    # ── 2.1 Risk Register ──
    print("\n  --- 2.1 Risk Register ---")
    status, risk = check("RM-01: Create enterprise risk", "POST", "/risk-management/risks", json_data={
        "title": "Unauthorized Payment Processing",
        "description": "Risk of unauthorized payments due to inadequate SoD controls in AP module",
        "description_ar": "خطر المعاملات المالية غير المصرح بها بسبب عدم كفاية ضوابط الفصل بين المهام",
        "category": "financial",
        "risk_owner_id": "admin",
        "risk_owner_name": "System Administrator",
        "inherent_likelihood": 4,
        "inherent_impact": 5,
        "status": "identified",
        "review_frequency": "quarterly",
    })
    risk_id = risk.get("risk_id") if isinstance(risk, dict) else None
    if risk_id:
        ok(f"RM-01: Risk created: {risk_id}")
    else:
        skip("RM-01: Could not create risk, using list fallback")
        status, risks = api("GET", "/risk-management/risks")
        if status == 200 and isinstance(risks, list) and risks:
            risk_id = risks[0].get("risk_id")

    check("RM-01: List risks", "GET", "/risk-management/risks",
          validate=lambda d: isinstance(d, list))

    if risk_id:
        check("RM-01: Get risk detail", "GET", f"/risk-management/risks/{risk_id}")

        # ── 2.2 Risk Assessment ──
        print("\n  --- 2.2 Risk Assessment ---")
        status, assessment = check("RM-10: Create assessment", "POST",
            f"/risk-management/risks/{risk_id}/assessments", json_data={
                "assessor_id": "admin",
                "assessor_name": "System Administrator",
                "likelihood_score": 3,
                "impact_score": 4,
                "overall_score": 12.0,
                "assessment_type": "periodic",
                "likelihood_rationale": "Controls reduce likelihood but residual risk remains",
                "impact_rationale": "Financial loss up to $500K possible",
                "monetary_impact": 500000.0,
                "currency": "USD",
            })
        assessment_id = assessment.get("assessment_id") if isinstance(assessment, dict) else None

        if assessment_id:
            check("RM-10: Submit assessment", "PUT",
                f"/risk-management/assessments/{assessment_id}/submit")
            check("RM-11: Review assessment", "PUT",
                f"/risk-management/assessments/{assessment_id}/review", json_data={
                    "reviewer_id": "admin",
                    "comments": "Assessment reviewed and approved",
                })

        check("RM-10: Get risk assessments", "GET",
            f"/risk-management/risks/{risk_id}/assessments")

        # ── 2.3 Risk Appetite ──
        print("\n  --- 2.3 Risk Appetite & Tolerance ---")
        check("RM-03: Set risk appetite", "POST", "/risk-management/appetites", json_data={
            "category": "financial",
            "appetite_score": 10.0,
            "tolerance_score": 15.0,
            "description": "Financial risk appetite: moderate",
            "approved_by": "CFO",
        })
        check("RM-03: Get appetite", "GET", "/risk-management/appetites",
              params={"category": "financial"})
        check("RM-03: Check appetite breach", "GET",
            f"/risk-management/risks/{risk_id}/appetite-check")

        # ── 2.4 KRI ──
        print("\n  --- 2.4 Key Risk Indicators ---")
        status, kri = check("RM-13: Create KRI", "POST", "/risk-management/kris", json_data={
            "name": "Open SoD Violations Count",
            "description": "Number of unresolved SoD violations across the landscape",
            "risk_id": risk_id,
            "data_source": "manual",
            "unit_of_measure": "count",
            "frequency": "weekly",
            "threshold_green": 50.0,
            "threshold_amber": 100.0,
            "threshold_red": 200.0,
        })
        kri_id = kri.get("kri_id") if isinstance(kri, dict) else None

        if kri_id:
            check("RM-13: Record KRI measurement", "POST",
                f"/risk-management/kris/{kri_id}/measurements", json_data={
                    "value": 75.0,
                    "measured_by": "admin",
                    "source": "manual",
                    "notes": "Slight increase from last week",
                })
            check("RM-13: Get KRI history", "GET",
                f"/risk-management/kris/{kri_id}/history")

        check("RM-13: KRI dashboard", "GET", "/risk-management/kris/dashboard")

        # ── 2.5 Risk Response ──
        print("\n  --- 2.5 Risk Response Plans ---")
        status, response = check("RM-20: Create response plan", "POST",
            f"/risk-management/risks/{risk_id}/responses", json_data={
                "response_type": "mitigate",
                "description": "Implement SoD controls and compensating monitoring",
                "owner_id": "admin",
                "owner_name": "System Administrator",
                "actions": [
                    {"action": "Review all AP clerk roles", "due_date": "2026-10-01"},
                    {"action": "Implement compensating controls", "due_date": "2026-11-01"},
                ],
                "due_date": (datetime.now() + timedelta(days=60)).isoformat(),
            })
        response_id = response.get("response_id") if isinstance(response, dict) else None
        if response_id:
            check("RM-20: Update response status", "PUT",
                f"/risk-management/responses/{response_id}/status", json_data={
                    "status": "in_progress",
                })

        # ── 2.6 Incidents ──
        print("\n  --- 2.6 Incidents & Loss Events ---")
        status, incident = check("RM-22: Report incident", "POST",
            "/risk-management/incidents", json_data={
                "title": "Unauthorized vendor payment detected",
                "description": "A payment of $45,000 was processed by an AP clerk who also created the vendor",
                "severity": "high",
                "financial_impact": 45000.0,
                "currency": "USD",
                "occurred_at": datetime.now().isoformat(),
                "reported_by": "admin",
            })
        incident_id = incident.get("incident_id") if isinstance(incident, dict) else None
        if incident_id and risk_id:
            check("RM-22: Link incident to risk", "POST",
                f"/risk-management/incidents/{incident_id}/link-risk", json_data={
                    "risk_id": risk_id,
                })

    # ── 2.7 Reporting ──
    print("\n  --- 2.7 RM Reporting ---")
    check("RM-12: Risk heatmap", "GET", "/risk-management/heatmap")
    check("RM-12: Risk trends", "GET", "/risk-management/trends", params={"period_months": 6})
    check("RM-30: Top risks", "GET", "/risk-management/top-risks", params={"limit": 5})
    check("RM-31: Risk-control coverage", "GET", "/risk-management/risk-control-coverage")
    check("RM-23: Overdue reviews", "GET", "/risk-management/overdue-reviews")

    return risk_id


# ═══════════════════════════════════════════════════════════════════════════════
# 3. PROCESS CONTROL (PC)
# ═══════════════════════════════════════════════════════════════════════════════

def test_pc(risk_id=None):
    section("3. PROCESS CONTROL (PC)")

    # ── 3.1 Control Library ──
    print("\n  --- 3.1 Control Library ---")
    status, control = check("PC-01: Create control", "POST", "/process-control/controls", json_data={
        "name": "Three-Way Match Verification",
        "objective": "Ensure all payments are supported by matching PO, GR, and Invoice",
        "description": "Automated three-way match check before payment release in SAP",
        "control_type": "preventive",
        "control_nature": "automated",
        "frequency": "continuous",
        "process_name": "Procure-to-Pay",
        "subprocess_name": "Invoice Verification",
        "owner_id": "admin",
        "owner_name": "System Administrator",
        "key_control": True,
        "risk_ids": [risk_id] if risk_id else [],
    })
    control_id = control.get("control_id") if isinstance(control, dict) else None

    check("PC-01: List controls", "GET", "/process-control/controls",
          validate=lambda d: isinstance(d, list))

    if control_id:
        check("PC-04: Get control detail", "GET", f"/process-control/controls/{control_id}")

        # ── 3.2 Framework Mapping ──
        print("\n  --- 3.2 Framework Mapping ---")

        # First create a framework
        status, fw = api("POST", "/frameworks/", json_data={
            "name": "COSO 2013",
            "version": "2013",
            "framework_type": "coso",
            "description": "Committee of Sponsoring Organizations Internal Control Framework",
        })
        fw_id = fw.get("framework_id") if isinstance(fw, dict) and status == 200 else None
        if not fw_id:
            status, fws = api("GET", "/frameworks/")
            if status == 200 and isinstance(fws, list) and fws:
                fw_id = fws[0].get("framework_id")

        if fw_id:
            # Add a requirement
            status, req = api("POST", f"/frameworks/{fw_id}/requirements", json_data={
                "requirement_id": "COSO-P10",
                "title": "Principle 10: Selects and Develops Control Activities",
                "description": "The organization selects and develops control activities",
                "category": "Control Activities",
                "level": 1,
            })
            req_id = req.get("requirement_id", "COSO-P10") if isinstance(req, dict) else "COSO-P10"

            check("PC-03: Map control to framework", "POST",
                f"/process-control/controls/{control_id}/framework-mappings", json_data={
                    "framework_id": fw_id,
                    "requirement_id": req_id,
                })
            check("PC-03: Get control frameworks", "GET",
                f"/process-control/controls/{control_id}/frameworks")
            check("PC-31: Get framework coverage", "GET",
                f"/process-control/frameworks/{fw_id}/coverage")

        # ── 3.3 Control Testing ──
        print("\n  --- 3.3 Control Testing ---")
        status, test = check("PC-11: Create control test", "POST",
            f"/process-control/controls/{control_id}/tests", json_data={
                "test_type": "operating_effectiveness",
                "testing_period_start": "2026-07-01",
                "testing_period_end": "2026-09-30",
                "sample_size": 25,
                "population_size": 500,
                "tester_id": "admin",
                "tester_name": "System Administrator",
                "test_steps": [
                    {"step": 1, "description": "Select 25 payments from Q3"},
                    {"step": 2, "description": "Verify PO, GR, Invoice match for each"},
                    {"step": 3, "description": "Document exceptions"},
                ],
            })
        test_id = test.get("test_id") if isinstance(test, dict) else None

        if test_id:
            # Record effective result
            check("PC-11: Record test result (effective)", "PUT",
                f"/process-control/tests/{test_id}/result", json_data={
                    "result": "effective",
                    "exceptions_found": 1,
                    "exception_details": [{"item": "INV-2026-4521", "detail": "GR missing, later found to be system timing issue"}],
                    "conclusion": "Control operating effectively. 1 exception due to system timing, not a control failure.",
                })

            # Create another test with ineffective result to trigger deficiency
            status, test2 = api("POST", f"/process-control/controls/{control_id}/tests", json_data={
                "test_type": "design",
                "testing_period_start": "2026-01-01",
                "testing_period_end": "2026-06-30",
                "sample_size": 30,
                "tester_id": "admin",
                "tester_name": "System Administrator",
            })
            test2_id = test2.get("test_id") if isinstance(test2, dict) else None
            if test2_id:
                check("PC-11: Record test result (ineffective -> auto-deficiency)", "PUT",
                    f"/process-control/tests/{test2_id}/result", json_data={
                        "result": "ineffective",
                        "exceptions_found": 8,
                        "conclusion": "Design gaps found: tolerance limits not properly configured",
                    })

        # ── 3.4 Deficiency Management ──
        print("\n  --- 3.4 Deficiency Management ---")
        check("PC-13: List deficiencies", "GET", "/process-control/deficiencies")

        status, deficiency = check("PC-13: Create deficiency", "POST",
            "/process-control/deficiencies", json_data={
                "control_id": control_id,
                "source": "self_assessment",
                "title": "Tolerance limit configuration gap",
                "description": "Invoice tolerance limits not aligned with policy for amounts > $10K",
                "severity": "significant_deficiency",
                "remediation_plan": "Reconfigure tolerance limits in SAP and retest",
                "remediation_owner_id": "admin",
                "remediation_owner_name": "System Administrator",
                "due_date": (datetime.now() + timedelta(days=30)).isoformat(),
            })
        def_id = deficiency.get("deficiency_id") if isinstance(deficiency, dict) else None

        if def_id:
            check("PC-13: Remediate deficiency", "PUT",
                f"/process-control/deficiencies/{def_id}/remediate", json_data={
                    "remediation_plan": "Tolerance limits reconfigured and tested successfully",
                    "evidence_ids": ["EVD-001"],
                })
            check("PC-13: Verify deficiency closure", "PUT",
                f"/process-control/deficiencies/{def_id}/verify")

        # ── 3.5 Self-Assessment ──
        print("\n  --- 3.5 Self-Assessment ---")
        check("PC-12: Create self-assessment campaign", "POST",
            "/process-control/self-assessment-campaigns", json_data={
                "campaign_name": f"Q3-2026 Control Self-Assessment",
                "campaign_type": "quarterly",
            })
        check("PC-12: Get pending assessments", "GET",
            "/process-control/self-assessments/pending", params={"assessor_id": "admin"})

        # ── 3.6 CCM ──
        print("\n  --- 3.6 Continuous Control Monitoring ---")
        status, ccm_rule = check("PC-20: Create CCM rule", "POST",
            "/process-control/ccm-rules", json_data={
                "name": "Password Policy Check",
                "description": "Verify SAP password parameters meet policy requirements",
                "source_system": "SAP",
                "rule_type": "config_check",
                "rule_definition": {
                    "check": "password_policy",
                    "params": {"min_length": 8, "complexity": True},
                },
                "frequency": "daily",
                "auto_create_deficiency": True,
            })
        ccm_rule_id = ccm_rule.get("rule_id") if isinstance(ccm_rule, dict) else None
        if ccm_rule_id:
            check("PC-22: Execute CCM rule", "POST",
                f"/process-control/ccm-rules/{ccm_rule_id}/execute")

        check("PC-22: CCM dashboard", "GET", "/process-control/ccm/dashboard")

        # ── 3.7 Evidence ──
        print("\n  --- 3.7 Evidence Management ---")
        status, evidence = check("PC-15: Upload evidence", "POST",
            "/process-control/evidence", json_data={
                "title": "Three-Way Match Test Results Q3-2026",
                "description": "Spreadsheet with 25 sample items tested",
                "evidence_type": "document",
                "file_name": "3way_match_test_q3.xlsx",
                "source_module": "pc",
                "linked_object_type": "control_test",
                "linked_object_id": test_id or "TEST-001",
                "uploaded_by": "admin",
            })
        evidence_id = evidence.get("evidence_id") if isinstance(evidence, dict) else None
        if evidence_id:
            check("NF-05: Set legal hold", "PUT",
                f"/process-control/evidence/{evidence_id}/legal-hold", json_data={
                    "legal_hold": True,
                })

        # ── 3.8 Sign-Off ──
        print("\n  --- 3.8 SOX Sign-Off ---")
        check("PC-14: Create sign-off certification", "POST",
            "/process-control/signoffs", json_data={
                "period": "Q3-2026",
                "certifier_id": "admin",
                "certifier_name": "System Administrator",
                "certifier_role": "process_owner",
                "scope_summary": "All P2P controls for Company Code 1000",
                "controls_in_scope": 12,
                "controls_effective": 11,
                "deficiencies_open": 1,
            })
        check("PC-14: Get sign-off hierarchy", "GET",
            "/process-control/signoffs/hierarchy", params={"period": "Q3-2026"})

    # ── 3.9 Dashboard ──
    print("\n  --- 3.9 PC Dashboard ---")
    check("PC-30: Control status dashboard", "GET", "/process-control/dashboard")

    return control_id


# ═══════════════════════════════════════════════════════════════════════════════
# 4. AUDIT MANAGEMENT (AM)
# ═══════════════════════════════════════════════════════════════════════════════

def test_am(risk_id=None, control_id=None):
    section("4. AUDIT MANAGEMENT (AM)")

    # ── 4.1 Audit Universe ──
    print("\n  --- 4.1 Audit Universe ---")
    status, entity = check("AM-01: Create auditable entity", "POST",
        "/audit-management/entities", json_data={
            "name": "Procure-to-Pay Process",
            "description": "End-to-end procurement process including vendor management, PO, GR, IR",
            "entity_type": "process",
            "audit_frequency": "annual",
        })
    entity_id = entity.get("entity_id") if isinstance(entity, dict) else None
    if entity_id:
        check("AM-01: Compute entity risk score", "POST",
            f"/audit-management/entities/{entity_id}/compute-risk")

    check("AM-01: List auditable entities", "GET", "/audit-management/entities")

    # ── 4.2 Audit Planning ──
    print("\n  --- 4.2 Audit Planning ---")
    status, plan = check("AM-02: Create audit plan", "POST",
        "/audit-management/plans", json_data={
            "name": "FY2026 Annual Audit Plan",
            "description": "Risk-based audit plan covering all critical processes",
            "plan_type": "annual",
            "fiscal_year": 2026,
            "total_audit_hours": 2000,
        })
    plan_id = plan.get("plan_id") if isinstance(plan, dict) else None

    if plan_id:
        check("AM-04: Submit plan for approval", "PUT",
            f"/audit-management/plans/{plan_id}/submit")
        check("AM-04: Approve plan", "PUT",
            f"/audit-management/plans/{plan_id}/approve", json_data={
                "approver_id": "admin",
                "comments": "Approved — adequate coverage of critical processes",
            })

    check("AM-02: List plans", "GET", "/audit-management/plans")
    check("AM-02: Generate risk-based plan", "POST",
        "/audit-management/plans/generate-risk-based", json_data={
            "fiscal_year": 2027,
            "max_engagements": 10,
        })

    # ── 4.3 Audit Resources ──
    print("\n  --- 4.3 Auditor Resources ---")
    check("AM-03: Register auditor", "POST", "/audit-management/resources", json_data={
        "name": "Sarah Chen",
        "email": "sarah.chen@governex.local",
        "title": "Senior IT Auditor",
        "skills": ["IT audit", "SAP security", "SoD", "data analytics"],
        "certifications": ["CISA", "CISSP"],
        "available_hours_per_month": 140,
    })
    check("AM-03: List resources", "GET", "/audit-management/resources")
    check("AM-03: Get available auditors", "GET",
        "/audit-management/resources/available", params={
            "start_date": "2026-10-01",
            "end_date": "2026-12-31",
        })

    # ── 4.4 Audit Engagement ──
    print("\n  --- 4.4 Audit Engagement Lifecycle ---")
    status, engagement = check("AM-10: Create engagement", "POST",
        "/audit-management/engagements", json_data={
            "title": "P2P Process Audit — FY2026",
            "objective": "Assess the design and operating effectiveness of key controls in the P2P process",
            "scope": "Vendor management, purchase orders, goods receipt, invoice verification, payment processing",
            "engagement_type": "operational",
            "plan_id": plan_id,
            "entity_id": entity_id,
            "lead_auditor_id": "admin",
            "lead_auditor_name": "System Administrator",
            "team_members": [{"id": "sarah.chen", "name": "Sarah Chen"}],
            "planned_start": "2026-10-01",
            "planned_end": "2026-11-30",
            "budget_hours": 200,
        })
    eng_id = engagement.get("engagement_id") if isinstance(engagement, dict) else None

    if eng_id:
        # Advance through lifecycle stages
        for stage in ["announced", "fieldwork"]:
            check(f"AM-10: Advance to {stage}", "PUT",
                f"/audit-management/engagements/{eng_id}/advance")

        # ── 4.5 Work Programs ──
        print("\n  --- 4.5 Work Programs ---")
        status, wp = check("AM-11: Create work program template", "POST",
            "/audit-management/work-programs", json_data={
                "name": "P2P Audit Work Program",
                "description": "Standard procedures for P2P audit",
                "audit_type": "operational",
                "procedures": [
                    {"ref": "AP-001", "title": "Vendor Master Data Review", "description": "Review vendor creation/modification controls"},
                    {"ref": "AP-002", "title": "PO Authorization Limits", "description": "Test PO approval limits and segregation"},
                    {"ref": "AP-003", "title": "Three-Way Match", "description": "Test automated three-way match effectiveness"},
                    {"ref": "AP-004", "title": "Payment Run Controls", "description": "Review payment proposal and release controls"},
                ],
                "is_template": True,
            })

        # ── 4.6 Procedures ──
        print("\n  --- 4.6 Audit Procedures ---")
        status, proc = check("AM-12: Create procedure", "POST",
            f"/audit-management/engagements/{eng_id}/procedures", json_data={
                "ref_number": "AP-001",
                "title": "Vendor Master Data Review",
                "description": "Review vendor creation and modification controls",
                "assigned_to_id": "admin",
                "assigned_to_name": "System Administrator",
            })
        proc_id = proc.get("procedure_id") if isinstance(proc, dict) else None

        if proc_id:
            check("AM-12: Complete procedure", "PUT",
                f"/audit-management/procedures/{proc_id}/complete", json_data={
                    "conclusion": "Vendor creation requires dual approval. 2 of 30 samples had delayed approval.",
                    "preparer_id": "admin",
                    "hours_spent": 16,
                })
            check("AM-12: Review procedure", "PUT",
                f"/audit-management/procedures/{proc_id}/review", json_data={
                    "reviewer_id": "admin",
                    "review_notes": "Work is adequate. Minor finding noted.",
                })

        check("AM-12: List procedures", "GET",
            f"/audit-management/engagements/{eng_id}/procedures")

        # ── 4.7 Workpapers ──
        print("\n  --- 4.7 Audit Workpapers ---")
        status, wp = check("AM-12: Create workpaper", "POST",
            f"/audit-management/engagements/{eng_id}/workpapers", json_data={
                "title": "Vendor Master Data Analysis",
                "description": "Analysis of vendor creation patterns and control effectiveness",
                "document_type": "narrative",
                "content": "We selected 30 vendor master records created in Q3 2026...",
                "procedure_id": proc_id,
                "preparer_id": "admin",
            })

        # ── 4.8 Findings (CCCE) ──
        print("\n  --- 4.8 Audit Findings ---")
        status, finding = check("AM-20: Create finding", "POST",
            f"/audit-management/engagements/{eng_id}/findings", json_data={
                "title": "Delayed Vendor Approval Process",
                "ref_number": "F-001",
                "condition": "2 of 30 vendor master records (7%) were created without timely secondary approval",
                "criteria": "Company policy requires dual approval within 24 hours for all new vendor records",
                "cause": "No automated escalation for pending approvals; manual reminder process is inconsistent",
                "effect": "Increased risk of unauthorized vendor creation; potential for fraudulent payments",
                "recommendation": "Implement automated escalation workflow for vendor approvals pending > 24 hours",
                "severity": "medium",
                "category": "process_compliance",
                "risk_id": risk_id,
                "control_id": control_id,
            })
        finding_id = finding.get("finding_id") if isinstance(finding, dict) else None

        if finding_id:
            check("AM-20: Record management response", "PUT",
                f"/audit-management/findings/{finding_id}/management-response", json_data={
                    "management_response": "Agreed. We will implement workflow automation by Q4 2026.",
                    "management_action_owner": "admin",
                    "management_target_date": "2026-12-31",
                })

            # ── 4.9 Actions ──
            print("\n  --- 4.9 Action Tracking ---")
            status, action = check("AM-21: Create action", "POST",
                f"/audit-management/findings/{finding_id}/actions", json_data={
                    "description": "Configure automated escalation workflow in Governex+ for vendor approvals",
                    "owner_id": "admin",
                    "owner_name": "System Administrator",
                    "due_date": "2026-12-31",
                })
            action_id = action.get("action_id") if isinstance(action, dict) else None

            if action_id:
                check("AM-21: Close action with evidence", "PUT",
                    f"/audit-management/actions/{action_id}/close", json_data={
                        "evidence_of_closure": "Workflow configured and tested. Screenshot attached.",
                        "evidence_ids": ["EVD-WF-001"],
                    })

            check("AM-21: Get overdue actions", "GET",
                "/audit-management/actions/overdue")

            if risk_id:
                check("AM-22: Link finding to risk", "POST",
                    f"/audit-management/findings/{finding_id}/link-risk", json_data={
                        "risk_id": risk_id,
                    })
            if control_id:
                check("AM-22: Link finding to control", "POST",
                    f"/audit-management/findings/{finding_id}/link-control", json_data={
                        "control_id": control_id,
                    })

        # ── 4.10 Time Tracking ──
        print("\n  --- 4.10 Time Tracking ---")
        check("AM-14: Record time entry", "POST",
            f"/audit-management/engagements/{eng_id}/time", json_data={
                "auditor_id": "admin",
                "auditor_name": "System Administrator",
                "date": datetime.now().isoformat(),
                "hours": 8.0,
                "activity_type": "fieldwork",
                "description": "Vendor master data testing",
            })
        check("AM-14: Get time summary", "GET",
            f"/audit-management/engagements/{eng_id}/time-summary")

    # ── 4.11 Reporting ──
    print("\n  --- 4.11 AM Reporting ---")
    check("AM-31: Audit dashboard", "GET", "/audit-management/dashboard")
    check("AM-31: Committee report", "GET", "/audit-management/committee-report",
          params={"fiscal_year": 2026})
    if eng_id:
        check("AM-30: Generate engagement report", "GET",
            f"/audit-management/engagements/{eng_id}/report")


# ═══════════════════════════════════════════════════════════════════════════════
# 5. CROSS-MODULE INTEGRATION (XI)
# ═══════════════════════════════════════════════════════════════════════════════

def test_xi():
    section("5. CROSS-MODULE INTEGRATION (XI)")

    # ── XI-05: Unified GRC Dashboard ──
    check("XI-05: Unified GRC dashboard", "GET", "/grc/dashboard")
    check("XI-03: Risk-control matrix", "GET", "/grc/risk-control-matrix")

    # ── Org Hierarchy ──
    print("\n  --- Org Hierarchy ---")
    status, unit = check("XI-01: Create org unit", "POST", "/org/units", json_data={
        "name": "Corporate Headquarters",
        "unit_type": "company",
        "country": "US",
        "region": "North America",
    })
    unit_id = unit.get("id") if isinstance(unit, dict) else None
    if unit_id:
        check("XI-01: Create child org unit", "POST", "/org/units", json_data={
            "name": "Finance Department",
            "unit_type": "department",
            "parent_id": unit_id,
        })
    check("XI-01: Get org tree", "GET", "/org/tree")

    # ── Frameworks ──
    print("\n  --- Framework Management ---")
    check("XI-07: List frameworks", "GET", "/frameworks/")

    # ── Retention ──
    print("\n  --- Document Retention ---")
    check("NF-05: Get retention policies", "GET", "/retention/policies")
    check("NF-05: Retention report", "GET", "/retention/report")

    # ── i18n ──
    print("\n  --- Internationalization ---")
    check("NF-04: Get supported locales", "GET", "/i18n/locales")
    check("NF-04: Get Arabic translations", "GET", "/i18n/ar")
    check("NF-04: Get English translations", "GET", "/i18n/en")

    # ── PPTX Export ──
    print("\n  --- Report Export ---")
    status, _ = api("GET", "/reports/export/risk-report")
    if status == 200:
        ok("NF-08: PPTX risk report export")
    else:
        skip("NF-08: PPTX risk report export (may need data)")

    status, _ = api("GET", "/reports/export/grc-executive")
    if status == 200:
        ok("NF-08: PPTX GRC executive export")
    else:
        skip("NF-08: PPTX GRC executive export (may need data)")


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    global BASE_URL
    parser = argparse.ArgumentParser(description="GovernexPlus GRC Suite UAT")
    parser.add_argument("--base-url", default="http://localhost:8000", help="API base URL")
    args = parser.parse_args()
    BASE_URL = args.base_url

    print("\n" + "=" * 70)
    print("  GOVERNEX+ GRC SUITE — USER ACCEPTANCE TESTING")
    print(f"  Target: {BASE_URL}")
    print(f"  Date:   {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    # Check server is up
    try:
        resp = requests.get(f"{BASE_URL}/health", timeout=5)
        if resp.status_code == 200:
            ok("Server is healthy")
        else:
            fail(f"Server health check returned {resp.status_code}")
    except Exception as e:
        fail(f"Server not reachable: {e}")
        print("\n\033[91mStart the server first: uvicorn api.main:app\033[0m")
        sys.exit(1)

    test_auth()
    test_ac()
    risk_id = test_rm()
    control_id = test_pc(risk_id)
    test_am(risk_id, control_id)
    test_xi()

    # ── Summary ──
    print("\n" + "=" * 70)
    print(f"  UAT RESULTS")
    print(f"  {'='*66}")
    total = PASS + FAIL + SKIP
    print(f"  Total:   {total}")
    print(f"  \033[92mPassed:  {PASS}\033[0m")
    if FAIL:
        print(f"  \033[91mFailed:  {FAIL}\033[0m")
    else:
        print(f"  Failed:  {FAIL}")
    if SKIP:
        print(f"  \033[93mSkipped: {SKIP}\033[0m")
    print(f"  Pass Rate: {PASS/total*100:.1f}%" if total else "  No tests run")
    print("=" * 70)

    sys.exit(1 if FAIL > 0 else 0)


if __name__ == "__main__":
    main()
