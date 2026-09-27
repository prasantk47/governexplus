"""
Tests for Audit Management (AM) module — AM-01 through AM-32

Covers:
  TestAuditUniverse          — create entity, list, compute risk score
  TestAuditPlanning          — create plan, submit, approve, list, generate risk-based plan
  TestAuditResources         — register resource, list, availability query
  TestEngagementLifecycle    — create engagement, advance through all stages
                               PLANNED → ANNOUNCED → FIELDWORK → DRAFT_REPORT
                               → FINAL_REPORT → CLOSED
  TestWorkPrograms           — create template, list templates, clone
  TestProcedures             — create procedure, complete (preparer), review (reviewer)
  TestWorkpapers             — create workpaper, review (approve and reject)
  TestFindings               — create CCCE finding, management response,
                               link to risk, link to control
  TestActions                — create action, close with evidence, overdue list
  TestTimeTracking           — record time, time summary
  TestAMReporting            — audit dashboard, committee report, engagement report
"""

import pytest


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TENANT = "tenant_default"
BASE = "/audit-management"


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
# Module-level helpers
# ---------------------------------------------------------------------------

def _create_entity(client, headers, *, name="Test Auditable Entity", risk_score=None):
    """Helper: create an auditable entity and return its entity_id."""
    body = {
        "name": name,
        "description": "Finance department AP process",
        "entity_type": "process",
        "audit_frequency": "annual",
        "primary_auditor_id": "AUD001",
    }
    if risk_score is not None:
        body["risk_score"] = risk_score
    resp = client.post(f"{BASE}/entities", json=body, headers=headers)
    assert resp.status_code == 201
    return resp.json()["entity_id"]


def _create_plan(client, headers, *, name="Annual Audit Plan 2026"):
    """Helper: create an audit plan and return its plan_id."""
    resp = client.post(
        f"{BASE}/plans",
        json={
            "name": name,
            "plan_type": "annual",
            "fiscal_year": 2026,
            "period_start": "2026-01-01T00:00:00",
            "period_end": "2026-12-31T00:00:00",
            "total_audit_hours": 2000,
            "prepared_by": "CAE001",
        },
        headers=headers,
    )
    assert resp.status_code == 201
    return resp.json()["plan_id"]


def _create_engagement(client, headers, *, title="Test Engagement"):
    """Helper: create a minimal engagement and return its engagement_id."""
    resp = client.post(
        f"{BASE}/engagements",
        json={
            "title": title,
            "objective": "Evaluate effectiveness of AP controls",
            "engagement_type": "operational",
            "lead_auditor_id": "AUD001",
            "lead_auditor_name": "Lead Auditor",
            "budget_hours": 80,
            "risk_rating": "high",
        },
        headers=headers,
    )
    assert resp.status_code == 201
    return resp.json()["engagement_id"]


def _create_finding(client, headers, engagement_id, *, title="Test Finding"):
    """Helper: create a finding and return its finding_id."""
    resp = client.post(
        f"{BASE}/engagements/{engagement_id}/findings",
        json={
            "title": title,
            "condition": "Dual approvals not enforced",
            "criteria": "Policy requires dual approval for all payments > $5,000",
            "cause": "System configuration error",
            "effect": "Potential for unauthorised payments",
            "recommendation": "Reconfigure approval workflow",
            "severity": "high",
            "category": "access_control",
        },
        headers=headers,
    )
    assert resp.status_code == 201
    return resp.json()["finding_id"]


# ===========================================================================
# TestAuditUniverse
# ===========================================================================

class TestAuditUniverse:
    """AM-01: Auditable entity management."""

    def test_create_entity_returns_201(self, client, headers):
        resp = client.post(
            f"{BASE}/entities",
            json={
                "name": "Accounts Payable Process",
                "description": "Vendor invoice processing and payment",
                "entity_type": "process",
                "audit_frequency": "annual",
                "primary_auditor_id": "AUD001",
                "risk_score": 18.5,
            },
            headers=headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Accounts Payable Process"
        assert data["entity_type"] == "process"
        assert data["is_active"] is True
        assert data["risk_score"] == 18.5

    def test_create_entity_invalid_type_returns_400(self, client, headers):
        resp = client.post(
            f"{BASE}/entities",
            json={"name": "Bad Entity", "entity_type": "invisible_object"},
            headers=headers,
        )
        assert resp.status_code == 400

    def test_list_entities_returns_created(self, client, headers):
        _create_entity(client, headers, name="Listed Entity Alpha")
        resp = client.get(f"{BASE}/entities", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "entities" in data
        assert data["total"] >= 1
        names = [e["name"] for e in data["entities"]]
        assert "Listed Entity Alpha" in names

    def test_list_entities_ordered_by_risk_score_desc(self, client, headers):
        _create_entity(client, headers, name="Low Risk Entity", risk_score=5.0)
        _create_entity(client, headers, name="High Risk Entity", risk_score=22.0)
        resp = client.get(f"{BASE}/entities", headers=headers)
        assert resp.status_code == 200
        entities = resp.json()["entities"]
        # Scored entities should appear before unscored; highest risk first
        scored = [e for e in entities if e.get("risk_score") is not None]
        if len(scored) >= 2:
            assert scored[0]["risk_score"] >= scored[1]["risk_score"]

    def test_list_entities_search_filter(self, client, headers):
        _create_entity(client, headers, name="Procurement Process")
        resp = client.get(f"{BASE}/entities?search=Procurement", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1

    def test_compute_risk_score(self, client, headers):
        entity_id = _create_entity(client, headers, name="Risk Score Entity")
        resp = client.post(
            f"{BASE}/entities/{entity_id}/compute-risk",
            json={
                "weights": {"inherent_risk": 0.4, "control_effectiveness": 0.35,
                             "last_audit_recency": 0.25},
                "scores": {"inherent_risk": 20.0, "control_effectiveness": 15.0,
                           "last_audit_recency": 10.0},
            },
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["entity_id"] == entity_id
        assert "computed_risk_score" in data
        # 0.4*20 + 0.35*15 + 0.25*10 = 8+5.25+2.5 = 15.75
        assert abs(data["computed_risk_score"] - 15.75) < 0.01

    def test_update_entity(self, client, headers):
        entity_id = _create_entity(client, headers, name="Updatable Entity")
        resp = client.put(
            f"{BASE}/entities/{entity_id}",
            json={"name": "Updatable Entity (Revised)", "audit_frequency": "semi_annual"},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Updatable Entity (Revised)"
        assert data["audit_frequency"] == "semi_annual"

    def test_get_nonexistent_entity_returns_404(self, client, headers):
        resp = client.put(
            f"{BASE}/entities/ENT_doesnotexist",
            json={"name": "Ghost Entity"},
            headers=headers,
        )
        assert resp.status_code == 404


# ===========================================================================
# TestAuditPlanning
# ===========================================================================

class TestAuditPlanning:
    """AM-02: Audit plan create, list, submit, approve, risk-based generation."""

    def test_create_plan_returns_201(self, client, headers):
        resp = client.post(
            f"{BASE}/plans",
            json={
                "name": "FY2026 Annual Audit Plan",
                "plan_type": "annual",
                "fiscal_year": 2026,
                "period_start": "2026-01-01T00:00:00",
                "period_end": "2026-12-31T00:00:00",
                "total_audit_hours": 3000,
                "allocated_budget": 500000.0,
                "prepared_by": "CAE001",
                "risk_methodology": "Risk-based with inherent risk scoring",
            },
            headers=headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "FY2026 Annual Audit Plan"
        assert data["status"] == "draft"
        assert data["fiscal_year"] == 2026

    def test_list_plans_returns_created(self, client, headers):
        _create_plan(client, headers, name="Listed Plan Alpha")
        resp = client.get(f"{BASE}/plans", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "plans" in data
        assert data["total"] >= 1

    def test_get_plan_by_id(self, client, headers):
        plan_id = _create_plan(client, headers, name="Specific Plan")
        resp = client.get(f"{BASE}/plans/{plan_id}", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["plan_id"] == plan_id

    def test_get_nonexistent_plan_returns_404(self, client, headers):
        resp = client.get(f"{BASE}/plans/PLAN_doesnotexist", headers=headers)
        assert resp.status_code == 404

    def test_submit_plan_transitions_to_pending_approval(self, client, headers):
        plan_id = _create_plan(client, headers)
        resp = client.put(f"{BASE}/plans/{plan_id}/submit", json={}, headers=headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "pending_approval"

    def test_approve_plan_transitions_to_approved(self, client, headers):
        plan_id = _create_plan(client, headers)
        client.put(f"{BASE}/plans/{plan_id}/submit", json={}, headers=headers)
        resp = client.put(
            f"{BASE}/plans/{plan_id}/approve",
            json={"approved_by": "BOARD001"},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "approved"
        assert data["approved_by"] == "BOARD001"
        assert data["approved_at"] is not None

    def test_list_plans_filter_by_status(self, client, headers):
        plan_id = _create_plan(client, headers)
        client.put(f"{BASE}/plans/{plan_id}/submit", json={}, headers=headers)
        client.put(f"{BASE}/plans/{plan_id}/approve", json={"approved_by": "X"},
                   headers=headers)
        resp = client.get(f"{BASE}/plans?status=approved", headers=headers)
        assert resp.status_code == 200
        for p in resp.json()["plans"]:
            assert p["status"] == "approved"

    def test_generate_risk_based_plan(self, client, headers):
        # Create entities with risk scores
        for i, score in enumerate([25.0, 18.0, 12.0]):
            _create_entity(client, headers, name=f"High Risk Entity {i}", risk_score=score)

        resp = client.post(
            f"{BASE}/plans/generate-risk-based",
            json={"fiscal_year": 2027, "top_n": 3, "prepared_by": "CAE001"},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "plan_id" in data
        assert data["fiscal_year"] == 2027
        assert data["entities_included"] >= 1
        assert len(data["engagements_created"]) >= 1

    def test_update_plan_fields(self, client, headers):
        plan_id = _create_plan(client, headers)
        resp = client.put(
            f"{BASE}/plans/{plan_id}",
            json={"total_audit_hours": 2500, "risk_methodology": "Updated methodology"},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["total_audit_hours"] == 2500


# ===========================================================================
# TestAuditResources
# ===========================================================================

class TestAuditResources:
    """AM-03: Auditor resource management."""

    def test_create_resource_returns_201(self, client, headers):
        resp = client.post(
            f"{BASE}/resources",
            json={
                "auditor_id": "AUD_SMITH",
                "name": "Sarah Smith",
                "email": "sarah.smith@audit.com",
                "title": "Senior IT Auditor",
                "skills": ["GovernexPlus", "Data Analytics", "CISA"],
                "certifications": ["CISA", "CIA"],
                "available_hours_per_month": 160.0,
                "is_external": False,
            },
            headers=headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Sarah Smith"
        assert data["is_active"] is True
        assert "CISA" in data["skills"]

    def test_list_resources(self, client, headers):
        client.post(
            f"{BASE}/resources",
            json={"name": "Listed Auditor", "available_hours_per_month": 120.0},
            headers=headers,
        )
        resp = client.get(f"{BASE}/resources", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "resources" in data
        assert data["total"] >= 1

    def test_list_resources_filter_external(self, client, headers):
        client.post(
            f"{BASE}/resources",
            json={"name": "External Consultant", "is_external": True,
                  "available_hours_per_month": 80.0},
            headers=headers,
        )
        resp = client.get(f"{BASE}/resources?is_external=true", headers=headers)
        assert resp.status_code == 200
        for r in resp.json()["resources"]:
            assert r["is_external"] is True

    def test_availability_query_min_hours(self, client, headers):
        client.post(
            f"{BASE}/resources",
            json={"name": "Busy Auditor", "available_hours_per_month": 20.0,
                  "is_external": False},
            headers=headers,
        )
        client.post(
            f"{BASE}/resources",
            json={"name": "Available Auditor", "available_hours_per_month": 150.0,
                  "is_external": False},
            headers=headers,
        )
        resp = client.get(f"{BASE}/resources/available?min_hours=100", headers=headers)
        assert resp.status_code == 200
        for r in resp.json()["auditors"]:
            assert r["available_hours_per_month"] >= 100

    def test_update_resource(self, client, headers):
        create_resp = client.post(
            f"{BASE}/resources",
            json={"auditor_id": "AUD_UPDATE", "name": "Update Auditor",
                  "available_hours_per_month": 160.0},
            headers=headers,
        )
        auditor_id = create_resp.json()["auditor_id"]
        resp = client.put(
            f"{BASE}/resources/{auditor_id}",
            json={"available_hours_per_month": 120.0, "title": "Principal Auditor"},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["available_hours_per_month"] == 120.0


# ===========================================================================
# TestEngagementLifecycle
# ===========================================================================

class TestEngagementLifecycle:
    """AM-10: Full engagement lifecycle PLANNED → ANNOUNCED → FIELDWORK
    → DRAFT_REPORT → FINAL_REPORT → CLOSED."""

    def test_create_engagement_returns_201(self, client, headers):
        resp = client.post(
            f"{BASE}/engagements",
            json={
                "title": "AP Process Audit 2026",
                "objective": "Evaluate AP control environment",
                "scope": "All AP transactions > $1,000 in FY2026",
                "engagement_type": "operational",
                "lead_auditor_id": "AUD001",
                "lead_auditor_name": "Lead Auditor",
                "team_members": ["AUD002", "AUD003"],
                "planned_start": "2026-10-01T00:00:00",
                "planned_end": "2026-11-30T00:00:00",
                "budget_hours": 120,
                "risk_rating": "high",
            },
            headers=headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "AP Process Audit 2026"
        assert data["status"] == "planned"
        assert data["engagement_type"] == "operational"

    def test_list_engagements(self, client, headers):
        _create_engagement(client, headers, title="Listed Engagement Alpha")
        resp = client.get(f"{BASE}/engagements", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "engagements" in data
        assert data["total"] >= 1

    def test_get_engagement_by_id(self, client, headers):
        engagement_id = _create_engagement(client, headers, title="Specific Engagement")
        resp = client.get(f"{BASE}/engagements/{engagement_id}", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["engagement_id"] == engagement_id

    def test_advance_planned_to_announced(self, client, headers):
        engagement_id = _create_engagement(client, headers)
        resp = client.put(
            f"{BASE}/engagements/{engagement_id}/advance", json={}, headers=headers
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "announced"

    def test_advance_through_all_stages(self, client, headers):
        """Full lifecycle: PLANNED → ANNOUNCED → FIELDWORK → DRAFT_REPORT → FINAL_REPORT → CLOSED."""
        engagement_id = _create_engagement(client, headers)

        expected_stages = [
            "announced",
            "fieldwork",
            "draft_report",
            "final_report",
            "closed",
        ]
        for expected_status in expected_stages:
            resp = client.put(
                f"{BASE}/engagements/{engagement_id}/advance", json={}, headers=headers
            )
            assert resp.status_code == 200, (
                f"Advance failed at expected status '{expected_status}': {resp.text}"
            )
            assert resp.json()["status"] == expected_status

    def test_advance_past_closed_returns_400(self, client, headers):
        engagement_id = _create_engagement(client, headers)
        # Advance all the way to CLOSED
        for _ in range(5):
            client.put(
                f"{BASE}/engagements/{engagement_id}/advance", json={}, headers=headers
            )
        # One more advance should fail
        resp = client.put(
            f"{BASE}/engagements/{engagement_id}/advance", json={}, headers=headers
        )
        assert resp.status_code == 400

    def test_fieldwork_advance_sets_actual_start(self, client, headers):
        engagement_id = _create_engagement(client, headers)
        # Advance twice: PLANNED → ANNOUNCED → FIELDWORK
        client.put(f"{BASE}/engagements/{engagement_id}/advance", json={}, headers=headers)
        resp = client.put(
            f"{BASE}/engagements/{engagement_id}/advance", json={}, headers=headers
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "fieldwork"
        assert resp.json()["actual_start"] is not None

    def test_list_engagements_filter_by_status(self, client, headers):
        engagement_id = _create_engagement(client, headers, title="Filter Status Engagement")
        client.put(f"{BASE}/engagements/{engagement_id}/advance", json={},
                   headers=headers)  # → announced
        resp = client.get(f"{BASE}/engagements?status=announced", headers=headers)
        assert resp.status_code == 200
        for e in resp.json()["engagements"]:
            assert e["status"] == "announced"

    def test_update_engagement_fields(self, client, headers):
        engagement_id = _create_engagement(client, headers)
        resp = client.put(
            f"{BASE}/engagements/{engagement_id}",
            json={"budget_hours": 200, "risk_rating": "critical"},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["budget_hours"] == 200


# ===========================================================================
# TestWorkPrograms
# ===========================================================================

class TestWorkPrograms:
    """AM-11: Work program templates."""

    def test_create_work_program_template_returns_201(self, client, headers):
        resp = client.post(
            f"{BASE}/work-programs",
            json={
                "name": "AP Standard Audit Program",
                "description": "Standard work program for AP process audits",
                "audit_type": "operational",
                "is_template": True,
                "procedures": [
                    {"step": 1, "title": "Obtain population of invoices"},
                    {"step": 2, "title": "Select statistical sample"},
                    {"step": 3, "title": "Test approval controls"},
                ],
            },
            headers=headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "AP Standard Audit Program"
        assert data["is_template"] is True
        assert data["version"] == 1

    def test_list_work_program_templates(self, client, headers):
        client.post(
            f"{BASE}/work-programs",
            json={"name": "Listed Template", "audit_type": "financial", "is_template": True},
            headers=headers,
        )
        resp = client.get(f"{BASE}/work-programs/templates", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "templates" in data
        for t in data["templates"]:
            assert t["is_template"] is True

    def test_list_templates_filter_by_audit_type(self, client, headers):
        client.post(
            f"{BASE}/work-programs",
            json={"name": "IT Audit Template", "audit_type": "it", "is_template": True},
            headers=headers,
        )
        resp = client.get(f"{BASE}/work-programs/templates?audit_type=it",
                           headers=headers)
        assert resp.status_code == 200
        for t in resp.json()["templates"]:
            assert t["audit_type"] == "it"

    def test_clone_work_program(self, client, headers):
        create_resp = client.post(
            f"{BASE}/work-programs",
            json={"name": "Original Template", "audit_type": "operational", "is_template": True,
                  "procedures": [{"step": 1, "title": "Step One"}]},
            headers=headers,
        )
        program_id = create_resp.json()["program_id"]
        resp = client.post(
            f"{BASE}/work-programs/{program_id}/clone",
            json={"name": "Clone for Q4 Engagement"},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Clone for Q4 Engagement"
        assert data["is_template"] is False
        assert data["program_id"] != program_id  # New ID assigned


# ===========================================================================
# TestProcedures
# ===========================================================================

class TestProcedures:
    """AM-11/AM-12: Procedure management with preparer / reviewer sign-off."""

    def test_create_procedure_returns_201(self, client, headers):
        engagement_id = _create_engagement(client, headers)
        resp = client.post(
            f"{BASE}/engagements/{engagement_id}/procedures",
            json={
                "ref_number": "PC-001",
                "title": "Test Dual Approval Control",
                "description": "Select 25 transactions and verify dual approval",
                "assigned_to_id": "AUD002",
                "assigned_to_name": "Junior Auditor",
            },
            headers=headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "Test Dual Approval Control"
        assert data["status"] == "not_started"
        assert data["hours_spent"] == 0.0

    def test_list_procedures_for_engagement(self, client, headers):
        engagement_id = _create_engagement(client, headers)
        for i in range(3):
            client.post(
                f"{BASE}/engagements/{engagement_id}/procedures",
                json={"title": f"Procedure {i}", "assigned_to_id": "AUD001"},
                headers=headers,
            )
        resp = client.get(
            f"{BASE}/engagements/{engagement_id}/procedures",
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["total"] == 3

    def test_complete_procedure_by_preparer(self, client, headers):
        engagement_id = _create_engagement(client, headers)
        proc_resp = client.post(
            f"{BASE}/engagements/{engagement_id}/procedures",
            json={"title": "Completable Procedure", "assigned_to_id": "AUD002"},
            headers=headers,
        )
        procedure_id = proc_resp.json()["procedure_id"]
        resp = client.put(
            f"{BASE}/procedures/{procedure_id}/complete",
            json={
                "conclusion": "Control is operating effectively; no exceptions noted",
                "preparer_id": "AUD002",
                "hours_spent": 4.5,
            },
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "completed"
        assert data["preparer_id"] == "AUD002"
        assert data["prepared_at"] is not None
        assert data["hours_spent"] == 4.5

    def test_review_procedure_by_reviewer(self, client, headers):
        engagement_id = _create_engagement(client, headers)
        proc_resp = client.post(
            f"{BASE}/engagements/{engagement_id}/procedures",
            json={"title": "Reviewable Procedure", "assigned_to_id": "AUD002"},
            headers=headers,
        )
        procedure_id = proc_resp.json()["procedure_id"]
        # Complete first
        client.put(
            f"{BASE}/procedures/{procedure_id}/complete",
            json={"conclusion": "Work complete", "preparer_id": "AUD002"},
            headers=headers,
        )
        # Review
        resp = client.put(
            f"{BASE}/procedures/{procedure_id}/review",
            json={"reviewer_id": "AUD001", "review_notes": "Reviewed and approved"},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "reviewed"
        assert data["reviewer_id"] == "AUD001"
        assert data["reviewed_at"] is not None

    def test_update_procedure_fields(self, client, headers):
        engagement_id = _create_engagement(client, headers)
        proc_resp = client.post(
            f"{BASE}/engagements/{engagement_id}/procedures",
            json={"title": "Original Procedure Title"},
            headers=headers,
        )
        procedure_id = proc_resp.json()["procedure_id"]
        resp = client.put(
            f"{BASE}/procedures/{procedure_id}",
            json={"title": "Updated Procedure Title", "hours_spent": 2.0},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["title"] == "Updated Procedure Title"


# ===========================================================================
# TestWorkpapers
# ===========================================================================

class TestWorkpapers:
    """AM-12: Workpaper creation and review workflow."""

    def test_create_workpaper_returns_201(self, client, headers):
        engagement_id = _create_engagement(client, headers)
        resp = client.post(
            f"{BASE}/engagements/{engagement_id}/workpapers",
            json={
                "title": "AP Sample Selection Workpaper",
                "description": "Documents sample selection methodology and results",
                "document_type": "narrative",
                "file_name": "ap_sample_q3.xlsx",
                "content": "Sample of 25 transactions selected using MUS methodology",
                "preparer_id": "AUD002",
                "cross_references": ["PC-001", "PC-002"],
            },
            headers=headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "AP Sample Selection Workpaper"
        assert data["status"] == "draft"
        assert data["review_status"] == "pending_review"
        assert data["version"] == 1

    def test_list_workpapers_for_engagement(self, client, headers):
        engagement_id = _create_engagement(client, headers)
        for i in range(2):
            client.post(
                f"{BASE}/engagements/{engagement_id}/workpapers",
                json={"title": f"Workpaper {i}", "document_type": "schedule"},
                headers=headers,
            )
        resp = client.get(
            f"{BASE}/engagements/{engagement_id}/workpapers", headers=headers
        )
        assert resp.status_code == 200
        assert resp.json()["total"] == 2

    def test_review_workpaper_approved(self, client, headers):
        engagement_id = _create_engagement(client, headers)
        wp_resp = client.post(
            f"{BASE}/engagements/{engagement_id}/workpapers",
            json={"title": "Approved Workpaper", "document_type": "narrative"},
            headers=headers,
        )
        workpaper_id = wp_resp.json()["workpaper_id"]
        resp = client.put(
            f"{BASE}/workpapers/{workpaper_id}/review",
            json={
                "reviewer_id": "AUD001",
                "review_note": "Workpaper is complete and accurate",
                "approved": True,
            },
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["review_status"] == "reviewed"
        assert data["status"] == "final"
        assert data["reviewer_id"] == "AUD001"
        assert data["reviewed_at"] is not None

    def test_review_workpaper_revision_needed(self, client, headers):
        engagement_id = _create_engagement(client, headers)
        wp_resp = client.post(
            f"{BASE}/engagements/{engagement_id}/workpapers",
            json={"title": "Needs Revision Workpaper", "document_type": "narrative"},
            headers=headers,
        )
        workpaper_id = wp_resp.json()["workpaper_id"]
        resp = client.put(
            f"{BASE}/workpapers/{workpaper_id}/review",
            json={
                "reviewer_id": "AUD001",
                "review_note": "Sample size insufficient — please increase to 30",
                "approved": False,
            },
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["review_status"] == "revision_needed"
        assert data["status"] == "draft"  # Stays draft until approved

    def test_update_workpaper_content(self, client, headers):
        engagement_id = _create_engagement(client, headers)
        wp_resp = client.post(
            f"{BASE}/engagements/{engagement_id}/workpapers",
            json={"title": "Editable Workpaper", "content": "Original content"},
            headers=headers,
        )
        workpaper_id = wp_resp.json()["workpaper_id"]
        resp = client.put(
            f"{BASE}/workpapers/{workpaper_id}",
            json={"content": "Updated content after revisions"},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["content"] == "Updated content after revisions"


# ===========================================================================
# TestFindings
# ===========================================================================

class TestFindings:
    """AM-20: CCCE finding lifecycle — create, management response, cross-module links."""

    def test_create_finding_returns_201(self, client, headers):
        engagement_id = _create_engagement(client, headers)
        resp = client.post(
            f"{BASE}/engagements/{engagement_id}/findings",
            json={
                "ref_number": "FND-001",
                "title": "Dual Approval Not Enforced",
                "condition": "25% of sampled transactions lacked second approval",
                "criteria": "Policy mandates dual approval for payments > $5,000",
                "cause": "System configuration bypassed approval workflow",
                "effect": "Risk of fraudulent or erroneous payments",
                "recommendation": "Reconfigure SAP workflow and re-test within 30 days",
                "severity": "high",
                "category": "access_control",
                "repeat_finding": False,
            },
            headers=headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "Dual Approval Not Enforced"
        assert data["status"] == "draft"
        assert data["severity"] == "high"

    def test_list_findings(self, client, headers):
        engagement_id = _create_engagement(client, headers)
        _create_finding(client, headers, engagement_id, title="Listed Finding")
        resp = client.get(f"{BASE}/findings", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "findings" in data
        assert data["total"] >= 1

    def test_list_findings_filter_by_severity(self, client, headers):
        engagement_id = _create_engagement(client, headers)
        client.post(
            f"{BASE}/engagements/{engagement_id}/findings",
            json={"title": "Critical Finding", "severity": "critical"},
            headers=headers,
        )
        client.post(
            f"{BASE}/engagements/{engagement_id}/findings",
            json={"title": "Low Finding", "severity": "low"},
            headers=headers,
        )
        resp = client.get(f"{BASE}/findings?severity=critical", headers=headers)
        assert resp.status_code == 200
        for f in resp.json()["findings"]:
            assert f["severity"] == "critical"

    def test_management_response_transitions_status(self, client, headers):
        engagement_id = _create_engagement(client, headers)
        finding_id = _create_finding(client, headers, engagement_id)
        resp = client.put(
            f"{BASE}/findings/{finding_id}/management-response",
            json={
                "management_response": "Management agrees with finding. Workflow will be reconfigured.",
                "management_action_owner": "AP Manager",
                "management_target_date": "2026-12-31T00:00:00",
            },
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "management_response_received"
        assert data["management_response"] is not None
        assert data["management_target_date"] is not None

    def test_link_finding_to_risk(self, client, headers):
        engagement_id = _create_engagement(client, headers)
        finding_id = _create_finding(client, headers, engagement_id)
        # Create a risk first
        risk_resp = client.post(
            "/risk-management/risks",
            json={"title": "Linked Risk", "category": "operational"},
            headers=headers,
        )
        risk_id = risk_resp.json()["risk_id"]
        resp = client.post(
            f"{BASE}/findings/{finding_id}/link-risk",
            json={"risk_id": risk_id},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["linked_risk_id"] == risk_id

    def test_link_finding_to_nonexistent_risk_returns_404(self, client, headers):
        engagement_id = _create_engagement(client, headers)
        finding_id = _create_finding(client, headers, engagement_id)
        resp = client.post(
            f"{BASE}/findings/{finding_id}/link-risk",
            json={"risk_id": "RISK_doesnotexist"},
            headers=headers,
        )
        assert resp.status_code == 404

    def test_link_finding_to_control(self, client, headers):
        engagement_id = _create_engagement(client, headers)
        finding_id = _create_finding(client, headers, engagement_id)
        # Create a control
        ctrl_resp = client.post(
            "/process-control/controls",
            json={"name": "Linked Control", "control_type": "preventive",
                  "control_nature": "manual", "frequency": "monthly"},
            headers=headers,
        )
        control_id = ctrl_resp.json()["control_id"]
        resp = client.post(
            f"{BASE}/findings/{finding_id}/link-control",
            json={"control_id": control_id},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["linked_control_id"] == control_id

    def test_update_finding_status(self, client, headers):
        engagement_id = _create_engagement(client, headers)
        finding_id = _create_finding(client, headers, engagement_id)
        resp = client.put(
            f"{BASE}/findings/{finding_id}",
            json={"status": "final"},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "final"

    def test_check_repeat_finding(self, client, headers):
        engagement_id = _create_engagement(client, headers)
        # Create the same finding title twice (in different engagements conceptually, both in same)
        _create_finding(client, headers, engagement_id, title="Recurring Control Gap")
        finding2_resp = client.post(
            f"{BASE}/engagements/{engagement_id}/findings",
            json={"title": "Recurring Control Gap", "severity": "medium"},
            headers=headers,
        )
        finding2_id = finding2_resp.json()["finding_id"]
        resp = client.get(
            f"{BASE}/findings/{finding2_id}/check-repeat",
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_repeat"] is True
        assert len(data["prior_findings"]) >= 1


# ===========================================================================
# TestActions
# ===========================================================================

class TestActions:
    """AM-21: Management action tracking."""

    def _setup(self, client, headers):
        """Create engagement + finding, return (engagement_id, finding_id)."""
        engagement_id = _create_engagement(client, headers)
        finding_id = _create_finding(client, headers, engagement_id)
        return engagement_id, finding_id

    def test_create_action_returns_201(self, client, headers):
        _, finding_id = self._setup(client, headers)
        resp = client.post(
            f"{BASE}/findings/{finding_id}/actions",
            json={
                "description": "Reconfigure SAP workflow to enforce dual approval",
                "owner_id": "AP_MGR001",
                "owner_name": "AP Process Manager",
                "due_date": "2026-12-31T00:00:00",
            },
            headers=headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["description"] == "Reconfigure SAP workflow to enforce dual approval"
        assert data["status"] == "open"
        assert data["escalation_level"] == 0

    def test_close_action_with_evidence(self, client, headers):
        _, finding_id = self._setup(client, headers)
        action_resp = client.post(
            f"{BASE}/findings/{finding_id}/actions",
            json={"description": "Fix implemented", "owner_id": "MGR001",
                  "due_date": "2026-12-31T00:00:00"},
            headers=headers,
        )
        action_id = action_resp.json()["action_id"]
        resp = client.put(
            f"{BASE}/actions/{action_id}/close",
            json={
                "evidence_of_closure": "Workflow configuration change request CAB-2026-0045",
                "evidence_ids": ["EVID001", "EVID002"],
                "verified_by": "CAE001",
            },
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "closed_verified"
        assert data["completed_at"] is not None
        assert data["evidence_of_closure"] is not None
        assert data["verified_by"] == "CAE001"

    def test_close_action_without_verifier_stays_completed(self, client, headers):
        _, finding_id = self._setup(client, headers)
        action_resp = client.post(
            f"{BASE}/findings/{finding_id}/actions",
            json={"description": "Simple fix", "owner_id": "MGR001",
                  "due_date": "2026-12-31T00:00:00"},
            headers=headers,
        )
        action_id = action_resp.json()["action_id"]
        resp = client.put(
            f"{BASE}/actions/{action_id}/close",
            json={"evidence_of_closure": "Fix deployed to production"},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "completed"

    def test_overdue_actions_list(self, client, headers):
        _, finding_id = self._setup(client, headers)
        # Create action with past due date
        action_resp = client.post(
            f"{BASE}/findings/{finding_id}/actions",
            json={"description": "Overdue Action",
                  "owner_id": "MGR001",
                  "due_date": "2025-01-01T00:00:00"},  # Past date
            headers=headers,
        )
        action_id = action_resp.json()["action_id"]
        resp = client.get(f"{BASE}/actions/overdue", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "total_overdue" in data
        assert "actions" in data
        # Our overdue action should appear
        overdue_ids = [a["action_id"] for a in data["actions"]]
        assert action_id in overdue_ids

    def test_update_action_fields(self, client, headers):
        _, finding_id = self._setup(client, headers)
        action_resp = client.post(
            f"{BASE}/findings/{finding_id}/actions",
            json={"description": "Original description", "owner_id": "MGR001",
                  "due_date": "2027-06-30T00:00:00"},
            headers=headers,
        )
        action_id = action_resp.json()["action_id"]
        resp = client.put(
            f"{BASE}/actions/{action_id}",
            json={"description": "Updated description", "owner_name": "New Owner"},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["description"] == "Updated description"


# ===========================================================================
# TestTimeTracking
# ===========================================================================

class TestTimeTracking:
    """AM-14: Time logging and summary reporting."""

    def test_log_time_returns_201(self, client, headers):
        engagement_id = _create_engagement(client, headers)
        resp = client.post(
            f"{BASE}/engagements/{engagement_id}/time",
            json={
                "auditor_id": "AUD001",
                "auditor_name": "Lead Auditor",
                "date": "2026-10-15T00:00:00",
                "hours": 7.5,
                "activity_type": "fieldwork",
                "description": "AP sample testing — invoice approval review",
            },
            headers=headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["hours"] == 7.5
        assert data["activity_type"] == "fieldwork"

    def test_time_accumulates_on_engagement(self, client, headers):
        engagement_id = _create_engagement(client, headers)
        for hours in [4.0, 6.5, 3.0]:
            client.post(
                f"{BASE}/engagements/{engagement_id}/time",
                json={"auditor_id": "AUD001", "hours": hours,
                      "date": "2026-10-15T00:00:00"},
                headers=headers,
            )
        summary_resp = client.get(
            f"{BASE}/engagements/{engagement_id}/time-summary",
            headers=headers,
        )
        assert summary_resp.status_code == 200
        data = summary_resp.json()
        assert data["total_hours"] == 13.5

    def test_time_summary_breakdown_by_auditor(self, client, headers):
        engagement_id = _create_engagement(client, headers)
        client.post(
            f"{BASE}/engagements/{engagement_id}/time",
            json={"auditor_id": "AUD001", "hours": 5.0, "date": "2026-10-15T00:00:00"},
            headers=headers,
        )
        client.post(
            f"{BASE}/engagements/{engagement_id}/time",
            json={"auditor_id": "AUD002", "hours": 3.0, "date": "2026-10-15T00:00:00"},
            headers=headers,
        )
        resp = client.get(
            f"{BASE}/engagements/{engagement_id}/time-summary",
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "by_auditor" in data
        assert data["by_auditor"].get("AUD001") == 5.0
        assert data["by_auditor"].get("AUD002") == 3.0

    def test_time_summary_breakdown_by_activity(self, client, headers):
        engagement_id = _create_engagement(client, headers)
        client.post(
            f"{BASE}/engagements/{engagement_id}/time",
            json={"auditor_id": "AUD001", "hours": 4.0, "date": "2026-10-15T00:00:00",
                  "activity_type": "fieldwork"},
            headers=headers,
        )
        client.post(
            f"{BASE}/engagements/{engagement_id}/time",
            json={"auditor_id": "AUD001", "hours": 2.0, "date": "2026-10-15T00:00:00",
                  "activity_type": "reporting"},
            headers=headers,
        )
        resp = client.get(
            f"{BASE}/engagements/{engagement_id}/time-summary",
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "by_activity" in data
        assert data["by_activity"].get("fieldwork") == 4.0
        assert data["by_activity"].get("reporting") == 2.0

    def test_time_summary_shows_budget_hours(self, client, headers):
        engagement_id = _create_engagement(client, headers)
        client.post(
            f"{BASE}/engagements/{engagement_id}/time",
            json={"auditor_id": "AUD001", "hours": 10.0, "date": "2026-10-01T00:00:00"},
            headers=headers,
        )
        resp = client.get(
            f"{BASE}/engagements/{engagement_id}/time-summary",
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "budget_hours" in data
        assert "entries" in data

    def test_auditor_utilization_endpoint(self, client, headers):
        engagement_id = _create_engagement(client, headers)
        # Register auditor resource first so available_hours is known
        client.post(
            f"{BASE}/resources",
            json={"auditor_id": "AUD_UTIL", "name": "Utilization Auditor",
                  "available_hours_per_month": 160.0},
            headers=headers,
        )
        client.post(
            f"{BASE}/engagements/{engagement_id}/time",
            json={"auditor_id": "AUD_UTIL", "hours": 40.0, "date": "2026-10-01T00:00:00"},
            headers=headers,
        )
        resp = client.get(f"{BASE}/auditors/AUD_UTIL/utilization", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["auditor_id"] == "AUD_UTIL"
        assert data["total_hours_logged"] == 40.0
        assert data["available_hours_per_month"] == 160.0
        assert data["utilization_pct"] == 25.0


# ===========================================================================
# TestAMReporting
# ===========================================================================

class TestAMReporting:
    """AM-31, AM-32: Dashboard, committee report, engagement report."""

    def _seed_audit_data(self, client, headers):
        """Create plan, entity, engagement, finding, action for reporting tests."""
        entity_id = _create_entity(client, headers, name="Reporting Entity", risk_score=15.0)
        plan_id = _create_plan(client, headers, name="Reporting Plan")
        engagement_id = _create_engagement(client, headers, title="Reporting Engagement")
        finding_id = _create_finding(client, headers, engagement_id,
                                     title="Reporting Finding")
        action_resp = client.post(
            f"{BASE}/findings/{finding_id}/actions",
            json={"description": "Reporting Action", "owner_id": "MGR001",
                  "due_date": "2027-01-31T00:00:00"},
            headers=headers,
        )
        return {
            "entity_id": entity_id,
            "plan_id": plan_id,
            "engagement_id": engagement_id,
            "finding_id": finding_id,
            "action_id": action_resp.json()["action_id"],
        }

    def test_audit_dashboard_returns_all_metrics(self, client, headers):
        resp = client.get(f"{BASE}/dashboard", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        for key in ("total_auditable_entities", "engagements_in_progress",
                    "open_findings", "critical_open_findings", "overdue_actions"):
            assert key in data
        assert isinstance(data["total_auditable_entities"], int)
        assert isinstance(data["open_findings"], int)

    def test_audit_dashboard_reflects_seeded_data(self, client, headers):
        self._seed_audit_data(client, headers)
        resp = client.get(f"{BASE}/dashboard", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        # We created an entity and a finding
        assert data["total_auditable_entities"] >= 1
        assert data["open_findings"] >= 1

    def test_committee_report_returns_required_fields(self, client, headers):
        self._seed_audit_data(client, headers)
        resp = client.get(f"{BASE}/committee-report?fiscal_year=2026",
                           headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        for key in ("fiscal_year", "audit_plans", "total_engagements",
                    "completed_engagements", "completion_rate",
                    "open_findings", "critical_findings", "high_findings",
                    "overdue_management_actions", "generated_at"):
            assert key in data
        assert data["fiscal_year"] == 2026
        assert 0 <= data["completion_rate"] <= 100

    def test_engagement_report_returns_findings_and_actions(self, client, headers):
        engagement_id = _create_engagement(client, headers, title="Report Engagement")
        finding_id = _create_finding(client, headers, engagement_id, title="Report Finding")
        client.post(
            f"{BASE}/findings/{finding_id}/actions",
            json={"description": "Action for report", "owner_id": "MGR001",
                  "due_date": "2027-06-30T00:00:00"},
            headers=headers,
        )
        resp = client.get(
            f"{BASE}/engagements/{engagement_id}/report",
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "engagement" in data
        assert "findings" in data
        assert "actions" in data
        assert "findings_count" in data
        assert "severity_summary" in data
        assert "report_generated_at" in data
        assert data["findings_count"] >= 1
        assert len(data["findings"]) >= 1
        assert len(data["actions"]) >= 1

    def test_engagement_report_severity_summary(self, client, headers):
        engagement_id = _create_engagement(client, headers)
        # Create two findings with different severities
        client.post(
            f"{BASE}/engagements/{engagement_id}/findings",
            json={"title": "High Finding", "severity": "high"},
            headers=headers,
        )
        client.post(
            f"{BASE}/engagements/{engagement_id}/findings",
            json={"title": "Medium Finding", "severity": "medium"},
            headers=headers,
        )
        resp = client.get(
            f"{BASE}/engagements/{engagement_id}/report", headers=headers
        )
        assert resp.status_code == 200
        severity_summary = resp.json()["severity_summary"]
        assert severity_summary.get("high", 0) >= 1
        assert severity_summary.get("medium", 0) >= 1

    def test_committee_report_without_year_uses_current(self, client, headers):
        resp = client.get(f"{BASE}/committee-report", headers=headers)
        assert resp.status_code == 200
        from datetime import datetime
        assert resp.json()["fiscal_year"] == datetime.utcnow().year
