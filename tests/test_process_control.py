"""
Tests for Process Control (PC) module — PC-01 through PC-32

Covers:
  TestControlLibrary          — create, list, get, update (version bump), retire
  TestControlTesting          — create test, record effective result, record ineffective
                                result (auto-deficiency created)
  TestDeficiencyManagement    — create, remediate (OPEN→REMEDIATED), verify (→VERIFIED_CLOSED)
  TestCCM                     — create rule, execute (pass + fail with auto-deficiency), dashboard
  TestEvidence                — upload evidence, get, set legal hold
  TestSignOff                 — create sign-off, submit certification, hierarchy, pending list
  TestPCDashboard             — control dashboard, audit-ready package
"""

import pytest


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TENANT = "tenant_default"
BASE = "/process-control"


# ---------------------------------------------------------------------------
# Module-scoped fixtures: login once per module to avoid auth rate limiting.
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def auth_token(module_client, module_test_user):
    """Login once per module to avoid rate limiting."""
    resp = module_client.post(
        "/auth/login",
        json={"username": "testuser", "password": "TestPassword123!", "tenant_id": TENANT},
        headers={"X-Tenant-ID": TENANT},
    )
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    return resp.json()["access_token"]


@pytest.fixture(scope="module")
def headers(auth_token):
    """Auth headers for all requests."""
    return {"Authorization": f"Bearer {auth_token}", "X-Tenant-ID": TENANT}


# Alias so test methods can use the shared client via a familiar name.
@pytest.fixture(scope="module")
def client(module_client):
    return module_client


# ---------------------------------------------------------------------------
# Module-level helper: create a control (uses headers dict directly).
# ---------------------------------------------------------------------------

def _create_control(client, headers, *, name="Test Control", status_after_create=None):
    """Helper: create and optionally activate a control, returning its control_id.

    ControlType values:  preventive | detective | corrective
    ControlNature values: manual | automated | it_dependent
    ControlFrequency values: continuous | daily | weekly | monthly | quarterly | annual | adhoc
    """
    resp = client.post(
        f"{BASE}/controls",
        json={
            "name": name,
            "objective": "Ensure segregation of duties in financial processing",
            "description": "Four-eyes principle for all payments above threshold",
            "control_type": "preventive",
            "control_nature": "manual",
            "frequency": "monthly",
            "process_name": "Accounts Payable",
            "owner_id": "OWN001",
            "owner_name": "Control Owner",
        },
        headers=headers,
    )
    assert resp.status_code == 201
    control_id = resp.json()["control_id"]
    if status_after_create:
        client.put(
            f"{BASE}/controls/{control_id}",
            json={"status": status_after_create},
            headers=headers,
        )
    return control_id


# ===========================================================================
# TestControlLibrary
# ===========================================================================

class TestControlLibrary:
    """PC-01: Control library CRUD with versioning."""

    def test_create_control_returns_201(self, client, headers):
        resp = client.post(
            f"{BASE}/controls",
            json={
                "name": "Payment Dual Authorisation",
                "objective": "Prevent unauthorised payments",
                "control_type": "preventive",
                "control_nature": "manual",
                # ControlFrequency enum: "adhoc" is valid; "per_transaction" is not.
                "frequency": "adhoc",
                "process_name": "Accounts Payable",
                "key_control": True,
            },
            headers=headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Payment Dual Authorisation"
        assert data["status"] == "draft"
        assert data["version"] == 1
        assert data["key_control"] is True

    def test_create_control_invalid_type_returns_400(self, client, headers):
        resp = client.post(
            f"{BASE}/controls",
            json={"name": "Bad Control", "control_type": "magical"},
            headers=headers,
        )
        assert resp.status_code == 400

    def test_list_controls_returns_created(self, client, headers):
        _create_control(client, headers, name="Listed Control Alpha")
        resp = client.get(f"{BASE}/controls", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "controls" in data
        assert data["total"] >= 1
        names = [c["name"] for c in data["controls"]]
        assert "Listed Control Alpha" in names

    def test_list_controls_filter_by_type(self, client, headers):
        client.post(
            f"{BASE}/controls",
            json={"name": "Pure Detective", "control_type": "detective",
                  "control_nature": "manual", "frequency": "monthly"},
            headers=headers,
        )
        resp = client.get(f"{BASE}/controls?control_type=detective", headers=headers)
        assert resp.status_code == 200
        for c in resp.json()["controls"]:
            assert c["control_type"] == "detective"

    def test_get_control_by_id(self, client, headers):
        control_id = _create_control(client, headers, name="Specific Control")
        resp = client.get(f"{BASE}/controls/{control_id}", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["control_id"] == control_id
        assert resp.json()["name"] == "Specific Control"

    def test_get_nonexistent_control_returns_404(self, client, headers):
        resp = client.get(f"{BASE}/controls/CTRL_doesnotexist", headers=headers)
        assert resp.status_code == 404

    def test_update_control_bumps_version(self, client, headers):
        control_id = _create_control(client, headers, name="Version Bump Control")
        resp = client.put(
            f"{BASE}/controls/{control_id}",
            json={
                "name": "Version Bump Control (v2)",
                "objective": "Updated objective",
                "status": "active",
                "changed_by": "USR001",
                "change_summary": "Updated objective after review",
            },
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Version Bump Control (v2)"
        assert data["version"] == 2
        assert len(data["change_history"]) == 1
        assert data["change_history"][0]["changed_by"] == "USR001"

    def test_retire_control_sets_inactive(self, client, headers):
        control_id = _create_control(client, headers, name="Retirable Control")
        resp = client.put(
            f"{BASE}/controls/{control_id}/retire",
            json={"reason": "Process redesign"},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "retired"
        # Retired control should 404 on GET (is_active=False)
        get_resp = client.get(f"{BASE}/controls/{control_id}", headers=headers)
        assert get_resp.status_code == 404

    def test_add_framework_mapping(self, client, headers):
        control_id = _create_control(client, headers, name="Framework Mapped Control")
        resp = client.post(
            f"{BASE}/controls/{control_id}/framework-mappings",
            json={"framework_id": "SOX", "requirement_id": "ITGC-01"},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert any(
            m["framework_id"] == "SOX" and m["requirement_id"] == "ITGC-01"
            for m in data["framework_mappings"]
        )

    def test_add_duplicate_framework_mapping_is_idempotent(self, client, headers):
        control_id = _create_control(client, headers, name="Idempotent Mapping Control")
        payload = {"framework_id": "ISO27001", "requirement_id": "A.9.4.1"}
        client.post(f"{BASE}/controls/{control_id}/framework-mappings",
                    json=payload, headers=headers)
        resp = client.post(f"{BASE}/controls/{control_id}/framework-mappings",
                           json=payload, headers=headers)
        assert resp.status_code == 200
        # Should only appear once
        mappings = resp.json()["framework_mappings"]
        matching = [m for m in mappings if m["framework_id"] == "ISO27001"]
        assert len(matching) == 1


# ===========================================================================
# TestControlTesting
# ===========================================================================

class TestControlTesting:
    """PC-11: Control test lifecycle, including auto-deficiency on ineffective result.

    TestType enum values: design | operating_effectiveness | walkthrough
    """

    def test_create_test_returns_201(self, client, headers):
        control_id = _create_control(client, headers, name="Tested Control")
        resp = client.post(
            f"{BASE}/controls/{control_id}/tests",
            json={
                "test_type": "operating_effectiveness",
                "testing_period_start": "2026-07-01T00:00:00",
                "testing_period_end": "2026-09-30T00:00:00",
                "sample_size": 25,
                "population_size": 120,
                "tester_id": "TST001",
                "tester_name": "Test Analyst",
                "test_steps": ["Pull population", "Select sample", "Review approvals"],
            },
            headers=headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "planned"
        assert data["sample_size"] == 25
        assert data["exceptions_found"] == 0

    def test_list_tests_for_control(self, client, headers):
        control_id = _create_control(client, headers, name="Multi-Test Control")
        for _ in range(2):
            client.post(
                f"{BASE}/controls/{control_id}/tests",
                # TestType enum: "design" (not "design_effectiveness")
                json={"test_type": "design", "sample_size": 10},
                headers=headers,
            )
        resp = client.get(f"{BASE}/controls/{control_id}/tests", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["total"] == 2

    def test_record_effective_result(self, client, headers):
        control_id = _create_control(client, headers, name="Effective Control")
        test_resp = client.post(
            f"{BASE}/controls/{control_id}/tests",
            json={"test_type": "operating_effectiveness", "sample_size": 30},
            headers=headers,
        )
        test_id = test_resp.json()["test_id"]
        resp = client.put(
            f"{BASE}/tests/{test_id}/result",
            json={
                "result": "effective",
                "exceptions_found": 0,
                "conclusion": "Control operates as designed; no exceptions noted",
            },
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["result"] == "effective"
        assert data["status"] == "completed"
        assert data["exceptions_found"] == 0

    def test_record_ineffective_result_auto_creates_deficiency(self, client, headers):
        control_id = _create_control(client, headers, name="Ineffective Control")
        test_resp = client.post(
            f"{BASE}/controls/{control_id}/tests",
            json={"test_type": "operating_effectiveness", "sample_size": 20},
            headers=headers,
        )
        test_id = test_resp.json()["test_id"]
        resp = client.put(
            f"{BASE}/tests/{test_id}/result",
            json={
                "result": "ineffective",
                "exceptions_found": 5,
                "exception_details": "Approvals missing on 5 of 20 sampled transactions",
                "conclusion": "Control not operating effectively — approval step bypassed",
                "create_deficiency": True,
            },
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["result"] == "ineffective"
        # Auto-deficiency should now exist for this control
        def_resp = client.get(f"{BASE}/deficiencies?control_id={control_id}",
                               headers=headers)
        assert def_resp.status_code == 200
        assert def_resp.json()["total"] >= 1

    def test_record_partially_effective_creates_observation(self, client, headers):
        control_id = _create_control(client, headers, name="Partial Control")
        test_resp = client.post(
            f"{BASE}/controls/{control_id}/tests",
            json={"test_type": "operating_effectiveness", "sample_size": 15},
            headers=headers,
        )
        test_id = test_resp.json()["test_id"]
        resp = client.put(
            f"{BASE}/tests/{test_id}/result",
            json={
                "result": "partially_effective",
                "exceptions_found": 2,
                "conclusion": "Minor exceptions in documentation",
                "create_deficiency": True,
            },
            headers=headers,
        )
        assert resp.status_code == 200
        # Auto-deficiency created with observation severity
        def_resp = client.get(f"{BASE}/deficiencies?control_id={control_id}",
                               headers=headers)
        assert def_resp.json()["total"] >= 1
        deficiency = def_resp.json()["deficiencies"][0]
        assert deficiency["severity"] == "observation"

    def test_record_result_invalid_value_returns_400(self, client, headers):
        control_id = _create_control(client, headers, name="Result Test Control")
        test_resp = client.post(
            f"{BASE}/controls/{control_id}/tests",
            json={"test_type": "operating_effectiveness"},
            headers=headers,
        )
        test_id = test_resp.json()["test_id"]
        resp = client.put(
            f"{BASE}/tests/{test_id}/result",
            json={"result": "sort_of_ok"},
            headers=headers,
        )
        assert resp.status_code == 400


# ===========================================================================
# TestDeficiencyManagement
# ===========================================================================

class TestDeficiencyManagement:
    """PC-13: Deficiency lifecycle OPEN → REMEDIATED → VERIFIED_CLOSED."""

    def test_create_deficiency_returns_201(self, client, headers):
        control_id = _create_control(client, headers, name="Deficiency Host Control")
        resp = client.post(
            f"{BASE}/deficiencies",
            json={
                "control_id": control_id,
                "title": "Missing dual-approval for payments",
                "description": "AP team processed payments without second approval",
                "severity": "significant_deficiency",
                "root_cause": "Workflow configuration error",
                "remediation_plan": "Reconfigure approval workflow",
                "remediation_owner_id": "OWN001",
                "remediation_owner_name": "Remediation Owner",
                "due_date": "2027-01-31T00:00:00",
            },
            headers=headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "Missing dual-approval for payments"
        assert data["status"] == "open"
        assert data["severity"] == "significant_deficiency"

    def test_list_deficiencies(self, client, headers):
        control_id = _create_control(client, headers, name="List Deficiency Control")
        client.post(
            f"{BASE}/deficiencies",
            json={"control_id": control_id, "title": "Listed Deficiency",
                  "severity": "control_gap"},
            headers=headers,
        )
        resp = client.get(f"{BASE}/deficiencies", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "deficiencies" in data
        assert data["total"] >= 1

    def test_filter_deficiencies_by_status(self, client, headers):
        control_id = _create_control(client, headers, name="Filter Def Control")
        client.post(
            f"{BASE}/deficiencies",
            json={"control_id": control_id, "title": "Open Deficiency", "severity": "observation"},
            headers=headers,
        )
        resp = client.get(f"{BASE}/deficiencies?status=open", headers=headers)
        assert resp.status_code == 200
        for d in resp.json()["deficiencies"]:
            assert d["status"] == "open"

    def test_remediate_transitions_to_remediated(self, client, headers):
        control_id = _create_control(client, headers, name="Remediate Control")
        def_resp = client.post(
            f"{BASE}/deficiencies",
            json={"control_id": control_id, "title": "Remediable Deficiency",
                  "severity": "material_weakness"},
            headers=headers,
        )
        deficiency_id = def_resp.json()["deficiency_id"]
        resp = client.put(
            f"{BASE}/deficiencies/{deficiency_id}/remediate",
            json={"remediation_notes": "Approval workflow reconfigured and tested"},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "remediated"
        assert data["completed_at"] is not None

    def test_verify_transitions_to_verified_closed(self, client, headers):
        control_id = _create_control(client, headers, name="Verify Control")
        def_resp = client.post(
            f"{BASE}/deficiencies",
            json={"control_id": control_id, "title": "Verifiable Deficiency",
                  "severity": "control_gap"},
            headers=headers,
        )
        deficiency_id = def_resp.json()["deficiency_id"]
        # Remediate first
        client.put(f"{BASE}/deficiencies/{deficiency_id}/remediate",
                   json={"remediation_notes": "Fixed"}, headers=headers)
        # Then verify
        resp = client.put(
            f"{BASE}/deficiencies/{deficiency_id}/verify",
            json={"verified_by": "VERIFIER001"},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "verified_closed"
        assert data["verified_by"] == "VERIFIER001"
        assert data["verified_at"] is not None

    def test_update_deficiency_fields(self, client, headers):
        control_id = _create_control(client, headers, name="Update Def Control")
        def_resp = client.post(
            f"{BASE}/deficiencies",
            json={"control_id": control_id, "title": "Old Title", "severity": "observation"},
            headers=headers,
        )
        deficiency_id = def_resp.json()["deficiency_id"]
        resp = client.put(
            f"{BASE}/deficiencies/{deficiency_id}",
            json={
                "title": "Updated Title",
                "root_cause": "Root cause identified",
                "severity": "significant_deficiency",
            },
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "Updated Title"
        assert data["severity"] == "significant_deficiency"

    def test_deficiency_for_nonexistent_control_returns_404(self, client, headers):
        resp = client.post(
            f"{BASE}/deficiencies",
            json={"control_id": "CTRL_doesnotexist", "title": "Orphan Deficiency",
                  "severity": "observation"},
            headers=headers,
        )
        assert resp.status_code == 404


# ===========================================================================
# TestCCM
# ===========================================================================

class TestCCM:
    """PC-20, PC-22: Continuous Control Monitoring rule create, execute, dashboard.

    CCMRuleType enum values: config_check | data_pattern | threshold | sod_bridge
    """

    def test_create_ccm_rule_returns_201(self, client, headers):
        resp = client.post(
            f"{BASE}/ccm-rules",
            json={
                "name": "Vendor Master Change Monitor",
                "description": "Detect unauthorised vendor master changes",
                "rule_type": "config_check",
                "source_system": "SAP ERP",
                "rule_definition": {"table": "LFB1", "field": "BANKN", "monitor": "all_changes"},
                "frequency": "daily",
                "auto_create_deficiency": True,
                "severity_on_breach": "significant_deficiency",
            },
            headers=headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Vendor Master Change Monitor"
        assert data["rule_type"] == "config_check"
        assert data["auto_create_deficiency"] is True

    def test_execute_ccm_rule_pass(self, client, headers):
        rule_resp = client.post(
            f"{BASE}/ccm-rules",
            # CCMRuleType enum: "threshold" (not "threshold_check")
            json={"name": "Pass Rule", "rule_type": "threshold",
                  "frequency": "daily", "auto_create_deficiency": False},
            headers=headers,
        )
        rule_id = rule_resp.json()["rule_id"]
        resp = client.post(
            f"{BASE}/ccm-rules/{rule_id}/execute",
            json={"result": "pass", "findings_count": 0, "duration_ms": 450},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["execution"]["result"] == "pass"
        assert data["auto_deficiency_id"] is None

    def test_execute_ccm_rule_fail_creates_deficiency(self, client, headers):
        control_id = _create_control(client, headers, name="CCM-Linked Control",
                                     status_after_create="active")
        rule_resp = client.post(
            f"{BASE}/ccm-rules",
            json={
                "name": "Fail Rule With Deficiency",
                # CCMRuleType enum: "sod_bridge" (not "sod_check")
                "rule_type": "sod_bridge",
                "frequency": "daily",
                "auto_create_deficiency": True,
                "severity_on_breach": "observation",
                "control_id": control_id,
            },
            headers=headers,
        )
        rule_id = rule_resp.json()["rule_id"]
        resp = client.post(
            f"{BASE}/ccm-rules/{rule_id}/execute",
            json={
                "result": "fail",
                "findings_count": 3,
                "findings_detail": {"users_in_conflict": ["U001", "U002", "U003"]},
            },
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["execution"]["result"] == "fail"
        assert data["auto_deficiency_id"] is not None

    def test_execute_ccm_rule_invalid_result_returns_400(self, client, headers):
        rule_resp = client.post(
            f"{BASE}/ccm-rules",
            json={"name": "Bad Result Rule", "rule_type": "config_check", "frequency": "daily"},
            headers=headers,
        )
        rule_id = rule_resp.json()["rule_id"]
        resp = client.post(
            f"{BASE}/ccm-rules/{rule_id}/execute",
            json={"result": "maybe"},
            headers=headers,
        )
        assert resp.status_code == 400

    def test_ccm_dashboard_returns_aggregates(self, client, headers):
        # Create two CCM rules
        for i in range(2):
            rule_resp = client.post(
                f"{BASE}/ccm-rules",
                json={"name": f"Dashboard Rule {i}", "rule_type": "config_check",
                      "frequency": "daily"},
                headers=headers,
            )
            rule_id = rule_resp.json()["rule_id"]
            # Execute to set a last_result
            client.post(
                f"{BASE}/ccm-rules/{rule_id}/execute",
                json={"result": "pass", "findings_count": 0},
                headers=headers,
            )
        resp = client.get(f"{BASE}/ccm/dashboard", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        for key in ("total_rules", "passing", "failing", "never_run", "pass_rate", "rules"):
            assert key in data
        assert data["total_rules"] >= 2

    def test_run_all_ccm_executes_active_rules(self, client, headers):
        client.post(
            f"{BASE}/ccm-rules",
            # CCMRuleType enum: "threshold" (not "threshold_check")
            json={"name": "Batch Rule", "rule_type": "threshold", "frequency": "daily"},
            headers=headers,
        )
        resp = client.post(f"{BASE}/ccm/run-all", json={}, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "executed_rules" in data
        assert data["executed_rules"] >= 1

    def test_sod_bridge_with_violations_creates_fail_result(self, client, headers):
        resp = client.post(
            f"{BASE}/ccm/sod-bridge",
            json={"violation_ids": ["VIO001", "VIO002", "VIO003"]},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["violations_bridged"] == 3
        assert data["result"] == "fail"

    def test_sod_bridge_without_violations_creates_pass_result(self, client, headers):
        resp = client.post(
            f"{BASE}/ccm/sod-bridge",
            json={"violation_ids": []},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["result"] == "pass"


# ===========================================================================
# TestEvidence
# ===========================================================================

class TestEvidence:
    """PC-15: Evidence upload, retrieval, legal hold."""

    def test_create_evidence_returns_201(self, client, headers):
        resp = client.post(
            f"{BASE}/evidence",
            json={
                "title": "Q3 2026 AP Approval Report",
                "description": "Export of all AP approvals for Q3 testing",
                "evidence_type": "document",
                "file_name": "ap_approvals_q3_2026.xlsx",
                "file_size": 204800,
                "mime_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                "source_module": "pc",
                "linked_object_type": "process_control",
                "linked_object_id": "CTRL001",
                "uploaded_by": "TST001",
                "retention_until": "2032-09-30T00:00:00",
            },
            headers=headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "Q3 2026 AP Approval Report"
        assert data["status"] == "active"
        assert data["legal_hold"] is False
        assert data["version"] == 1

    def test_get_evidence_by_id(self, client, headers):
        create_resp = client.post(
            f"{BASE}/evidence",
            json={"title": "Specific Evidence", "evidence_type": "screenshot",
                  "uploaded_by": "USR001"},
            headers=headers,
        )
        evidence_id = create_resp.json()["evidence_id"]
        resp = client.get(f"{BASE}/evidence/{evidence_id}", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["evidence_id"] == evidence_id

    def test_get_nonexistent_evidence_returns_404(self, client, headers):
        resp = client.get(f"{BASE}/evidence/EVID_doesnotexist", headers=headers)
        assert resp.status_code == 404

    def test_list_evidence_filter_by_module(self, client, headers):
        client.post(
            f"{BASE}/evidence",
            json={"title": "PC Evidence", "source_module": "pc", "uploaded_by": "U1"},
            headers=headers,
        )
        client.post(
            f"{BASE}/evidence",
            json={"title": "AM Evidence", "source_module": "am", "uploaded_by": "U1"},
            headers=headers,
        )
        resp = client.get(f"{BASE}/evidence?source_module=pc", headers=headers)
        assert resp.status_code == 200
        for e in resp.json()["evidence"]:
            assert e["source_module"] == "pc"

    def test_set_legal_hold_true(self, client, headers):
        create_resp = client.post(
            f"{BASE}/evidence",
            json={"title": "Legal Hold Evidence", "evidence_type": "document",
                  "uploaded_by": "USR001"},
            headers=headers,
        )
        evidence_id = create_resp.json()["evidence_id"]
        resp = client.put(
            f"{BASE}/evidence/{evidence_id}/legal-hold",
            json={"legal_hold": True},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["legal_hold"] is True

    def test_release_legal_hold(self, client, headers):
        create_resp = client.post(
            f"{BASE}/evidence",
            json={"title": "Release Hold Evidence", "uploaded_by": "USR001"},
            headers=headers,
        )
        evidence_id = create_resp.json()["evidence_id"]
        # Set hold
        client.put(f"{BASE}/evidence/{evidence_id}/legal-hold",
                   json={"legal_hold": True}, headers=headers)
        # Release
        resp = client.put(
            f"{BASE}/evidence/{evidence_id}/legal-hold",
            json={"legal_hold": False},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["legal_hold"] is False

    def test_list_evidence_filter_legal_hold(self, client, headers):
        # Create one normal, one held
        evid_resp = client.post(
            f"{BASE}/evidence",
            json={"title": "Held Evidence", "uploaded_by": "U1"},
            headers=headers,
        )
        evidence_id = evid_resp.json()["evidence_id"]
        client.put(f"{BASE}/evidence/{evidence_id}/legal-hold",
                   json={"legal_hold": True}, headers=headers)
        resp = client.get(f"{BASE}/evidence?legal_hold=true", headers=headers)
        assert resp.status_code == 200
        for e in resp.json()["evidence"]:
            assert e["legal_hold"] is True


# ===========================================================================
# TestSignOff
# ===========================================================================

class TestSignOff:
    """PC-14: SOX-style sign-off certifications."""

    def test_create_signoff_returns_201(self, client, headers):
        resp = client.post(
            f"{BASE}/signoffs",
            json={
                "period": "Q3-2026",
                "certifier_id": "MGR001",
                "certifier_name": "Finance Manager",
                "certifier_role": "Process Owner",
                "scope_summary": "AP and AR controls for Q3 2026",
                "controls_in_scope": 12,
                "controls_effective": 11,
                "deficiencies_open": 1,
            },
            headers=headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["period"] == "Q3-2026"
        assert data["status"] == "pending"
        assert data["controls_in_scope"] == 12

    def test_submit_signoff_transitions_to_certified(self, client, headers):
        create_resp = client.post(
            f"{BASE}/signoffs",
            json={"period": "Q3-2026", "certifier_id": "MGR001"},
            headers=headers,
        )
        certification_id = create_resp.json()["certification_id"]
        resp = client.put(
            f"{BASE}/signoffs/{certification_id}/submit",
            json={
                "statement": "I certify that all controls are adequately designed and operating effectively",
                "exceptions": [],
                "comments": "No material issues noted",
            },
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "certified"
        assert data["certified_at"] is not None

    def test_submit_signoff_with_exceptions(self, client, headers):
        create_resp = client.post(
            f"{BASE}/signoffs",
            json={"period": "Q3-2026", "certifier_id": "MGR002"},
            headers=headers,
        )
        certification_id = create_resp.json()["certification_id"]
        resp = client.put(
            f"{BASE}/signoffs/{certification_id}/submit",
            json={
                "statement": "Certifying with noted exceptions",
                "exceptions": ["Control CTRL005 ineffective during testing"],
            },
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "certified_with_exceptions"

    def test_get_pending_signoffs(self, client, headers):
        client.post(
            f"{BASE}/signoffs",
            json={"period": "Q3-2026", "certifier_id": "MGR003"},
            headers=headers,
        )
        resp = client.get(f"{BASE}/signoffs/pending", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "signoffs" in data
        assert data["total"] >= 1
        for s in data["signoffs"]:
            assert s["status"] == "pending"

    def test_get_pending_signoffs_filtered_by_certifier(self, client, headers):
        client.post(
            f"{BASE}/signoffs",
            json={"period": "Q3-2026", "certifier_id": "SPECIFIC_MGR"},
            headers=headers,
        )
        resp = client.get(
            f"{BASE}/signoffs/pending?certifier_id=SPECIFIC_MGR",
            headers=headers,
        )
        assert resp.status_code == 200
        for s in resp.json()["signoffs"]:
            assert s["certifier_id"] == "SPECIFIC_MGR"

    def test_signoff_hierarchy_parent_child(self, client, headers):
        # Create parent sign-off
        parent_resp = client.post(
            f"{BASE}/signoffs",
            json={"period": "FY2026", "certifier_id": "CFO001"},
            headers=headers,
        )
        parent_cert_id = parent_resp.json()["certification_id"]

        # Create child sign-off referencing parent
        client.post(
            f"{BASE}/signoffs",
            json={"period": "FY2026", "certifier_id": "MGR001",
                  "parent_certification_id": parent_cert_id},
            headers=headers,
        )
        resp = client.get(f"{BASE}/signoffs/hierarchy?period=FY2026", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["period"] == "FY2026"
        assert "hierarchy" in data
        # The parent should be in the root list
        root_ids = [s["certification_id"] for s in data["hierarchy"]]
        assert parent_cert_id in root_ids


# ===========================================================================
# TestPCDashboard
# ===========================================================================

class TestPCDashboard:
    """PC-31, PC-32: Process control dashboard and audit-ready package."""

    def test_dashboard_returns_all_metrics(self, client, headers):
        resp = client.get(f"{BASE}/dashboard", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        for key in ("total_controls", "active_controls", "open_deficiencies",
                    "pending_tests", "pending_signoffs"):
            assert key in data
        # Numeric values
        assert isinstance(data["total_controls"], int)
        assert isinstance(data["open_deficiencies"], int)

    def test_dashboard_reflects_seeded_data(self, client, headers):
        _create_control(client, headers, name="Dashboard Seed Control")
        resp = client.get(f"{BASE}/dashboard", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["total_controls"] >= 1

    def test_audit_package_returns_complete_bundle(self, client, headers):
        control_id = _create_control(client, headers, name="Audit Package Control")

        # Add a test
        test_resp = client.post(
            f"{BASE}/controls/{control_id}/tests",
            json={"test_type": "operating_effectiveness", "sample_size": 10},
            headers=headers,
        )
        test_id = test_resp.json()["test_id"]
        client.put(
            f"{BASE}/tests/{test_id}/result",
            json={"result": "effective", "exceptions_found": 0},
            headers=headers,
        )

        # Add evidence
        client.post(
            f"{BASE}/evidence",
            json={"title": "Audit Evidence", "linked_object_type": "process_control",
                  "linked_object_id": control_id, "uploaded_by": "U1"},
            headers=headers,
        )

        resp = client.get(f"{BASE}/controls/{control_id}/audit-package",
                           headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "control" in data
        assert "recent_tests" in data
        assert "deficiencies" in data
        assert "evidence" in data
        assert "generated_at" in data
        assert data["control"]["control_id"] == control_id
        assert len(data["recent_tests"]) >= 1
