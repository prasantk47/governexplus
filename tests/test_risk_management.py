"""
Tests for Risk Management (RM) module — RM-01 through RM-31

Covers:
  TestRiskRegister       — create, list, get, update, soft delete
  TestRiskAssessment     — create, submit, review, list
  TestRiskAppetite       — set, get, breach check (within / approaching / breach)
  TestKRI                — create, record measurement (auto-status), dashboard, history
  TestRiskResponse       — create, advance status to in_progress then completed
  TestRiskIncident       — report, link to risk, list incidents
  TestRiskReporting      — heatmap, trends, top risks, overdue reviews, risk-control coverage
"""

import pytest


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TENANT = "tenant_default"
BASE = "/risk-management"


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


# ===========================================================================
# TestRiskRegister
# ===========================================================================

class TestRiskRegister:
    """RM-01: Risk register CRUD."""

    def test_create_risk_returns_201(self, client, headers):
        resp = client.post(
            f"{BASE}/risks",
            json={
                "title": "Unauthorised Payment Processing",
                "description": "Risk that payments are processed without dual authorisation",
                "category": "financial",
                "inherent_likelihood": 3,
                "inherent_impact": 4,
                "risk_owner_id": "OWN001",
                "risk_owner_name": "Jane Doe",
                "review_frequency": "quarterly",
                "next_review_date": "2027-03-31T00:00:00",
            },
            headers=headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "Unauthorised Payment Processing"
        assert data["inherent_score"] == 12  # 3 × 4
        assert data["status"] == "identified"
        assert data["is_active"] is True

    def test_list_risks_returns_created(self, client, headers):
        # Create first
        client.post(
            f"{BASE}/risks",
            json={"title": "Listed Risk Alpha", "category": "operational",
                  "inherent_likelihood": 2, "inherent_impact": 2},
            headers=headers,
        )
        resp = client.get(f"{BASE}/risks", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "risks" in data
        assert data["total"] >= 1
        titles = [r["title"] for r in data["risks"]]
        assert "Listed Risk Alpha" in titles

    def test_list_risks_filter_by_category(self, client, headers):
        # RiskCategory enum value is "it_cyber" (not "it")
        client.post(
            f"{BASE}/risks",
            json={"title": "IT Risk Beta", "category": "it_cyber",
                  "inherent_likelihood": 2, "inherent_impact": 3},
            headers=headers,
        )
        resp = client.get(f"{BASE}/risks?category=it_cyber", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        for r in data["risks"]:
            assert r["category"] == "it_cyber"

    def test_get_risk_by_id(self, client, headers):
        create_resp = client.post(
            f"{BASE}/risks",
            json={"title": "Specific Risk", "category": "compliance",
                  "inherent_likelihood": 1, "inherent_impact": 5},
            headers=headers,
        )
        risk_id = create_resp.json()["risk_id"]
        resp = client.get(f"{BASE}/risks/{risk_id}", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["risk_id"] == risk_id
        assert resp.json()["title"] == "Specific Risk"

    def test_get_nonexistent_risk_returns_404(self, client, headers):
        resp = client.get(f"{BASE}/risks/RISK_doesnotexist", headers=headers)
        assert resp.status_code == 404

    def test_update_risk_score_recompute(self, client, headers):
        create_resp = client.post(
            f"{BASE}/risks",
            json={"title": "Updatable Risk", "category": "operational",
                  "inherent_likelihood": 2, "inherent_impact": 2},
            headers=headers,
        )
        risk_id = create_resp.json()["risk_id"]
        resp = client.put(
            f"{BASE}/risks/{risk_id}",
            json={
                "title": "Updatable Risk (v2)",
                "inherent_likelihood": 4,
                "inherent_impact": 4,
                "inherent_score": 16,
                "status": "assessed",
            },
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "Updatable Risk (v2)"
        assert data["inherent_score"] == 16

    def test_soft_delete_risk(self, client, headers):
        create_resp = client.post(
            f"{BASE}/risks",
            json={"title": "Deletable Risk", "category": "operational"},
            headers=headers,
        )
        risk_id = create_resp.json()["risk_id"]
        del_resp = client.delete(f"{BASE}/risks/{risk_id}", headers=headers)
        assert del_resp.status_code == 204
        # After soft delete, GET should 404
        get_resp = client.get(f"{BASE}/risks/{risk_id}", headers=headers)
        assert get_resp.status_code == 404

    def test_create_risk_invalid_category_returns_400(self, client, headers):
        resp = client.post(
            f"{BASE}/risks",
            json={"title": "Bad Risk", "category": "not_a_real_category"},
            headers=headers,
        )
        assert resp.status_code == 400


# ===========================================================================
# TestRiskAssessment
# ===========================================================================

class TestRiskAssessment:
    """RM-10, RM-11: Risk assessment lifecycle."""

    def _create_risk(self, client, headers):
        resp = client.post(
            f"{BASE}/risks",
            json={"title": "Assessment Target Risk", "category": "operational",
                  "inherent_likelihood": 3, "inherent_impact": 3},
            headers=headers,
        )
        assert resp.status_code == 201
        return resp.json()["risk_id"]

    def test_create_assessment_returns_201(self, client, headers):
        risk_id = self._create_risk(client, headers)
        resp = client.post(
            f"{BASE}/risks/{risk_id}/assessments",
            json={
                "likelihood_score": 3,
                "impact_score": 4,
                "assessment_type": "periodic",
                "assessor_id": "ASR001",
                "assessor_name": "John Assessor",
                "likelihood_rationale": "Historical frequency indicates 3/5",
                "impact_rationale": "Financial loss potential is high",
            },
            headers=headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["overall_score"] == 12  # 3 × 4
        assert data["status"] == "draft"
        assert data["assessment_type"] == "periodic"

    def test_list_assessments_for_risk(self, client, headers):
        risk_id = self._create_risk(client, headers)
        # Create two assessments
        for i in range(2):
            client.post(
                f"{BASE}/risks/{risk_id}/assessments",
                json={"likelihood_score": i + 1, "impact_score": 2, "assessment_type": "adhoc"},
                headers=headers,
            )
        resp = client.get(f"{BASE}/risks/{risk_id}/assessments", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2

    def test_submit_assessment_transitions_to_submitted(self, client, headers):
        risk_id = self._create_risk(client, headers)
        asmt_resp = client.post(
            f"{BASE}/risks/{risk_id}/assessments",
            json={"likelihood_score": 2, "impact_score": 3, "assessment_type": "periodic"},
            headers=headers,
        )
        assessment_id = asmt_resp.json()["assessment_id"]
        submit_resp = client.put(
            f"{BASE}/assessments/{assessment_id}/submit",
            json={},
            headers=headers,
        )
        assert submit_resp.status_code == 200
        assert submit_resp.json()["status"] == "submitted"

    def test_submit_already_submitted_returns_400(self, client, headers):
        risk_id = self._create_risk(client, headers)
        asmt_resp = client.post(
            f"{BASE}/risks/{risk_id}/assessments",
            json={"likelihood_score": 2, "impact_score": 2, "assessment_type": "periodic"},
            headers=headers,
        )
        assessment_id = asmt_resp.json()["assessment_id"]
        client.put(f"{BASE}/assessments/{assessment_id}/submit", json={}, headers=headers)
        # Second submit should fail
        resp = client.put(
            f"{BASE}/assessments/{assessment_id}/submit", json={}, headers=headers
        )
        assert resp.status_code == 400

    def test_review_assessment_transitions_to_reviewed(self, client, headers):
        risk_id = self._create_risk(client, headers)
        asmt_resp = client.post(
            f"{BASE}/risks/{risk_id}/assessments",
            json={"likelihood_score": 4, "impact_score": 4, "assessment_type": "adhoc"},
            headers=headers,
        )
        assessment_id = asmt_resp.json()["assessment_id"]
        # Submit first
        client.put(f"{BASE}/assessments/{assessment_id}/submit", json={}, headers=headers)
        # Review
        review_resp = client.put(
            f"{BASE}/assessments/{assessment_id}/review",
            json={"reviewed_by": "REVIEWER01", "comments": "Scores validated"},
            headers=headers,
        )
        assert review_resp.status_code == 200
        data = review_resp.json()
        assert data["status"] == "reviewed"
        assert data["reviewed_by"] == "REVIEWER01"

    def test_assessment_campaign_creates_assessments_for_category(self, client, headers):
        # Create two risks in the same category
        for i in range(2):
            client.post(
                f"{BASE}/risks",
                json={"title": f"Campaign Risk {i}", "category": "strategic",
                      "inherent_likelihood": 2, "inherent_impact": 3},
                headers=headers,
            )
        resp = client.post(
            f"{BASE}/assessment-campaigns",
            json={"category": "strategic", "assessor_id": "CAMP001", "assessor_name": "Campaign User"},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "campaign_id" in data
        assert data["assessments_created"] >= 2


# ===========================================================================
# TestRiskAppetite
# ===========================================================================

class TestRiskAppetite:
    """RM-03: Risk appetite set/get/breach logic."""

    def test_set_appetite_returns_201(self, client, headers):
        resp = client.post(
            f"{BASE}/appetites",
            json={
                "category": "financial",
                "appetite_score": 9.0,
                "tolerance_score": 16.0,
                "description": "Board-approved financial risk appetite",
                "approved_by": "BOARD001",
            },
            headers=headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["appetite_score"] == 9.0
        assert data["tolerance_score"] == 16.0
        assert data["category"] == "financial"

    def test_get_appetites_returns_list(self, client, headers):
        client.post(
            f"{BASE}/appetites",
            json={"category": "operational", "appetite_score": 6.0, "tolerance_score": 12.0},
            headers=headers,
        )
        resp = client.get(f"{BASE}/appetites", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "appetites" in data
        assert data["total"] >= 1

    def test_get_appetites_filter_by_category(self, client, headers):
        client.post(
            f"{BASE}/appetites",
            json={"category": "it", "appetite_score": 8.0, "tolerance_score": 15.0},
            headers=headers,
        )
        resp = client.get(f"{BASE}/appetites?category=it", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        for a in data["appetites"]:
            assert a["category"] == "it"

    def test_appetite_upsert_updates_existing(self, client, headers):
        client.post(
            f"{BASE}/appetites",
            json={"category": "compliance", "appetite_score": 5.0, "tolerance_score": 10.0},
            headers=headers,
        )
        # Upsert with new scores
        resp = client.post(
            f"{BASE}/appetites",
            json={"category": "compliance", "appetite_score": 7.0, "tolerance_score": 14.0},
            headers=headers,
        )
        assert resp.status_code == 201
        assert resp.json()["appetite_score"] == 7.0

    def test_appetite_breach_check_within(self, client, headers):
        # Create appetite for 'all' category
        client.post(
            f"{BASE}/appetites",
            json={"category": "all", "appetite_score": 10.0, "tolerance_score": 20.0},
            headers=headers,
        )
        # Create risk with low residual score
        risk_resp = client.post(
            f"{BASE}/risks",
            json={"title": "Low Risk", "category": "strategic",
                  "residual_score": 4.0, "inherent_likelihood": 2, "inherent_impact": 2},
            headers=headers,
        )
        risk_id = risk_resp.json()["risk_id"]
        resp = client.get(f"{BASE}/risks/{risk_id}/appetite-check", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "within_appetite"
        assert data["appetite_breach"] is False
        assert data["tolerance_breach"] is False

    def test_appetite_breach_check_appetite_breach(self, client, headers):
        client.post(
            f"{BASE}/appetites",
            json={"category": "all", "appetite_score": 6.0, "tolerance_score": 15.0},
            headers=headers,
        )
        risk_resp = client.post(
            f"{BASE}/risks",
            json={"title": "Appetite-Breach Risk", "category": "operational",
                  "residual_score": 9.0, "inherent_likelihood": 3, "inherent_impact": 3},
            headers=headers,
        )
        risk_id = risk_resp.json()["risk_id"]
        resp = client.get(f"{BASE}/risks/{risk_id}/appetite-check", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["appetite_breach"] is True
        assert data["tolerance_breach"] is False
        assert data["status"] == "appetite_breach"

    def test_appetite_breach_check_tolerance_breach(self, client, headers):
        client.post(
            f"{BASE}/appetites",
            json={"category": "all", "appetite_score": 5.0, "tolerance_score": 10.0},
            headers=headers,
        )
        risk_resp = client.post(
            f"{BASE}/risks",
            json={"title": "Tolerance-Breach Risk", "category": "financial",
                  "residual_score": 18.0, "inherent_likelihood": 5, "inherent_impact": 4},
            headers=headers,
        )
        risk_id = risk_resp.json()["risk_id"]
        resp = client.get(f"{BASE}/risks/{risk_id}/appetite-check", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["tolerance_breach"] is True
        assert data["appetite_breach"] is True
        assert data["status"] == "tolerance_breach"


# ===========================================================================
# TestKRI
# ===========================================================================

class TestKRI:
    """RM-13: Key Risk Indicator create / measure / dashboard / history."""

    def test_create_kri_returns_201(self, client, headers):
        resp = client.post(
            f"{BASE}/kris",
            json={
                "name": "Late Payment Rate",
                "description": "% of invoices paid after due date",
                "unit_of_measure": "percent",
                "frequency": "monthly",
                "threshold_green": 5.0,
                "threshold_amber": 10.0,
                "threshold_red": 20.0,
                "owner_id": "OWN001",
            },
            headers=headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Late Payment Rate"
        assert data["status"] == "normal"
        assert data["threshold_red"] == 20.0

    def test_record_measurement_normal_status(self, client, headers):
        kri_resp = client.post(
            f"{BASE}/kris",
            json={"name": "Incident Count", "threshold_green": 5.0,
                  "threshold_amber": 10.0, "threshold_red": 20.0},
            headers=headers,
        )
        kri_id = kri_resp.json()["kri_id"]
        resp = client.post(
            f"{BASE}/kris/{kri_id}/measurements",
            json={"value": 3.0, "measured_by": "ANALYST001", "notes": "Monthly reading"},
            headers=headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["measurement"]["value"] == 3.0
        assert data["kri_status"] == "normal"

    def test_record_measurement_warning_status(self, client, headers):
        kri_resp = client.post(
            f"{BASE}/kris",
            json={"name": "Access Violations", "threshold_green": 5.0,
                  "threshold_amber": 10.0, "threshold_red": 20.0},
            headers=headers,
        )
        kri_id = kri_resp.json()["kri_id"]
        resp = client.post(
            f"{BASE}/kris/{kri_id}/measurements",
            json={"value": 12.0},
            headers=headers,
        )
        assert resp.status_code == 201
        assert resp.json()["kri_status"] == "warning"

    def test_record_measurement_breach_status(self, client, headers):
        kri_resp = client.post(
            f"{BASE}/kris",
            json={"name": "Overdue Reviews", "threshold_green": 2.0,
                  "threshold_amber": 5.0, "threshold_red": 10.0},
            headers=headers,
        )
        kri_id = kri_resp.json()["kri_id"]
        resp = client.post(
            f"{BASE}/kris/{kri_id}/measurements",
            json={"value": 15.0},
            headers=headers,
        )
        assert resp.status_code == 201
        assert resp.json()["kri_status"] == "breach"

    def test_kri_dashboard_contains_totals(self, client, headers):
        # Create KRI for visibility on dashboard
        client.post(
            f"{BASE}/kris",
            json={"name": "Dashboard KRI", "threshold_amber": 5.0, "threshold_red": 10.0},
            headers=headers,
        )
        resp = client.get(f"{BASE}/kris/dashboard", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "total_kris" in data
        assert "normal" in data
        assert "warning" in data
        assert "breach" in data
        assert "kris" in data

    def test_kri_history_shows_all_measurements(self, client, headers):
        kri_resp = client.post(
            f"{BASE}/kris",
            json={"name": "History KRI", "threshold_amber": 5.0, "threshold_red": 10.0},
            headers=headers,
        )
        kri_id = kri_resp.json()["kri_id"]
        # Record three measurements
        for val in [2.0, 6.0, 11.0]:
            client.post(
                f"{BASE}/kris/{kri_id}/measurements",
                json={"value": val},
                headers=headers,
            )
        resp = client.get(f"{BASE}/kris/{kri_id}/history", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_measurements"] == 3
        assert len(data["measurements"]) == 3

    def test_kri_measurement_for_nonexistent_kri_returns_404(self, client, headers):
        resp = client.post(
            f"{BASE}/kris/KRI_doesnotexist/measurements",
            json={"value": 5.0},
            headers=headers,
        )
        assert resp.status_code == 404


# ===========================================================================
# TestRiskResponse
# ===========================================================================

class TestRiskResponse:
    """RM-20: Risk response lifecycle."""

    def _create_risk(self, client, headers):
        resp = client.post(
            f"{BASE}/risks",
            json={"title": "Response Target Risk", "category": "operational",
                  "inherent_likelihood": 3, "inherent_impact": 3},
            headers=headers,
        )
        return resp.json()["risk_id"]

    def test_create_response_returns_201(self, client, headers):
        risk_id = self._create_risk(client, headers)
        resp = client.post(
            f"{BASE}/risks/{risk_id}/responses",
            json={
                "response_type": "mitigate",
                "description": "Implement dual-authorisation control for payments >$10k",
                "owner_id": "OWN002",
                "owner_name": "Control Owner",
                "actions": ["Deploy approval workflow", "Train AP team"],
                "due_date": "2027-06-30T00:00:00",
            },
            headers=headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["response_type"] == "mitigate"
        assert data["status"] == "planned"
        assert len(data["actions"]) == 2

    def test_list_responses_for_risk(self, client, headers):
        risk_id = self._create_risk(client, headers)
        client.post(
            f"{BASE}/risks/{risk_id}/responses",
            json={"response_type": "accept", "description": "Accept residual risk"},
            headers=headers,
        )
        resp = client.get(f"{BASE}/risks/{risk_id}/responses", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1

    def test_update_response_status_to_in_progress(self, client, headers):
        risk_id = self._create_risk(client, headers)
        create_resp = client.post(
            f"{BASE}/risks/{risk_id}/responses",
            json={"response_type": "mitigate", "description": "Mitigation plan"},
            headers=headers,
        )
        response_id = create_resp.json()["response_id"]
        resp = client.put(
            f"{BASE}/responses/{response_id}/status",
            json={"status": "in_progress"},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "in_progress"

    def test_update_response_status_to_completed_sets_timestamp(self, client, headers):
        risk_id = self._create_risk(client, headers)
        create_resp = client.post(
            f"{BASE}/risks/{risk_id}/responses",
            json={"response_type": "transfer", "description": "Transfer via insurance"},
            headers=headers,
        )
        response_id = create_resp.json()["response_id"]
        # Advance through in_progress
        client.put(
            f"{BASE}/responses/{response_id}/status",
            json={"status": "in_progress"},
            headers=headers,
        )
        resp = client.put(
            f"{BASE}/responses/{response_id}/status",
            json={"status": "completed", "effectiveness_rating": 4},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "completed"
        assert data["completed_at"] is not None
        assert data["effectiveness_rating"] == 4

    def test_update_response_invalid_status_returns_400(self, client, headers):
        risk_id = self._create_risk(client, headers)
        create_resp = client.post(
            f"{BASE}/risks/{risk_id}/responses",
            json={"response_type": "avoid", "description": "Avoid activity"},
            headers=headers,
        )
        response_id = create_resp.json()["response_id"]
        resp = client.put(
            f"{BASE}/responses/{response_id}/status",
            json={"status": "not_a_real_status"},
            headers=headers,
        )
        assert resp.status_code == 400


# ===========================================================================
# TestRiskIncident
# ===========================================================================

class TestRiskIncident:
    """RM-22: Incident report, link to risk, list."""

    def test_report_incident_returns_201(self, client, headers):
        resp = client.post(
            f"{BASE}/incidents",
            json={
                "title": "Duplicate Payment Detected",
                "description": "AP system processed the same invoice twice",
                "severity": "high",
                "financial_impact": 50000.0,
                "currency": "USD",
                "occurred_at": "2026-09-01T10:00:00",
                "reported_by": "U001",
            },
            headers=headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "Duplicate Payment Detected"
        assert data["severity"] == "high"
        assert data["status"] == "reported"
        assert data["financial_impact"] == 50000.0

    def test_list_incidents(self, client, headers):
        client.post(
            f"{BASE}/incidents",
            json={"title": "System Outage", "severity": "critical"},
            headers=headers,
        )
        resp = client.get(f"{BASE}/incidents", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "incidents" in data
        assert data["total"] >= 1

    def test_list_incidents_filter_by_severity(self, client, headers):
        client.post(
            f"{BASE}/incidents",
            json={"title": "Critical Incident", "severity": "critical"},
            headers=headers,
        )
        client.post(
            f"{BASE}/incidents",
            json={"title": "Low Incident", "severity": "low"},
            headers=headers,
        )
        resp = client.get(f"{BASE}/incidents?severity=critical", headers=headers)
        assert resp.status_code == 200
        for inc in resp.json()["incidents"]:
            assert inc["severity"] == "critical"

    def test_link_incident_to_risk(self, client, headers):
        risk_resp = client.post(
            f"{BASE}/risks",
            json={"title": "Linkable Risk", "category": "operational"},
            headers=headers,
        )
        risk_id = risk_resp.json()["risk_id"]
        inc_resp = client.post(
            f"{BASE}/incidents",
            json={"title": "Linkable Incident", "severity": "medium"},
            headers=headers,
        )
        incident_id = inc_resp.json()["incident_id"]
        link_resp = client.post(
            f"{BASE}/incidents/{incident_id}/link-risk",
            json={"risk_id": risk_id},
            headers=headers,
        )
        assert link_resp.status_code == 200
        data = link_resp.json()
        assert data["success"] is True
        assert data["linked_risk_id"] == risk_id

    def test_update_incident_status_to_resolved(self, client, headers):
        inc_resp = client.post(
            f"{BASE}/incidents",
            json={"title": "Resolvable Incident", "severity": "low"},
            headers=headers,
        )
        incident_id = inc_resp.json()["incident_id"]
        resp = client.put(
            f"{BASE}/incidents/{incident_id}",
            json={"status": "resolved", "root_cause": "Process failure"},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "resolved"
        assert data["resolved_at"] is not None

    def test_report_incident_invalid_severity_returns_400(self, client, headers):
        resp = client.post(
            f"{BASE}/incidents",
            json={"title": "Bad Incident", "severity": "apocalyptic"},
            headers=headers,
        )
        assert resp.status_code == 400


# ===========================================================================
# TestRiskReporting
# ===========================================================================

class TestRiskReporting:
    """RM-25 through RM-31: Reporting endpoints."""

    def _seed_risks(self, client, headers):
        """Create a set of risks with varied scores for reporting tests."""
        risks = [
            {"title": "High Risk A", "category": "financial",
             "inherent_likelihood": 4, "inherent_impact": 5,
             "residual_likelihood": 3, "residual_impact": 4, "residual_score": 12.0,
             "related_control_ids": ["CTRL001"]},
            {"title": "Medium Risk B", "category": "operational",
             "inherent_likelihood": 3, "inherent_impact": 3,
             "residual_likelihood": 2, "residual_impact": 2, "residual_score": 4.0},
            # RiskCategory enum value is "it_cyber" (not "it")
            {"title": "Low Risk C", "category": "it_cyber",
             "inherent_likelihood": 1, "inherent_impact": 2,
             "residual_score": 1.0},
        ]
        for r in risks:
            client.post(f"{BASE}/risks", json=r, headers=headers)

    def test_heatmap_returns_25_cells(self, client, headers):
        self._seed_risks(client, headers)
        resp = client.get(f"{BASE}/heatmap", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "heatmap" in data
        assert len(data["heatmap"]) == 25  # 5×5 grid
        assert "total_risks" in data
        # Verify zone labels exist
        zones = {cell["zone"] for cell in data["heatmap"]}
        assert "low" in zones

    def test_heatmap_cells_have_correct_structure(self, client, headers):
        resp = client.get(f"{BASE}/heatmap", headers=headers)
        assert resp.status_code == 200
        cell = resp.json()["heatmap"][0]
        for key in ("likelihood", "impact", "score", "count", "zone"):
            assert key in cell

    def test_trends_returns_period_data(self, client, headers):
        resp = client.get(f"{BASE}/trends?period_months=12", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["period_months"] == 12
        assert "trend" in data

    def test_top_risks_returns_ordered_list(self, client, headers):
        self._seed_risks(client, headers)
        resp = client.get(f"{BASE}/top-risks?limit=5", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "top_risks" in data
        # Verify ordering: first risk should have highest or equal residual_score
        scores = [r.get("residual_score") for r in data["top_risks"] if r.get("residual_score")]
        if len(scores) >= 2:
            assert scores[0] >= scores[1]

    def test_overdue_reviews_only_includes_past_dates(self, client, headers):
        # Past review date
        client.post(
            f"{BASE}/risks",
            json={"title": "Overdue Review Risk", "category": "operational",
                  "next_review_date": "2025-01-01T00:00:00"},
            headers=headers,
        )
        # Future review date — should NOT appear
        client.post(
            f"{BASE}/risks",
            json={"title": "On-time Review Risk", "category": "operational",
                  "next_review_date": "2030-01-01T00:00:00"},
            headers=headers,
        )
        resp = client.get(f"{BASE}/overdue-reviews", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        titles = [r["title"] for r in data["risks"]]
        assert "Overdue Review Risk" in titles
        assert "On-time Review Risk" not in titles

    def test_risk_control_coverage_returns_percentages(self, client, headers):
        self._seed_risks(client, headers)
        resp = client.get(f"{BASE}/risk-control-coverage", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "total_risks" in data
        assert "covered" in data
        assert "uncovered" in data
        assert "coverage_pct" in data
        assert 0.0 <= data["coverage_pct"] <= 100.0

    def test_review_attestation_advances_next_review_date(self, client, headers):
        risk_resp = client.post(
            f"{BASE}/risks",
            json={"title": "Attestation Risk", "category": "compliance",
                  "next_review_date": "2025-06-01T00:00:00",
                  "review_frequency": "quarterly"},
            headers=headers,
        )
        risk_id = risk_resp.json()["risk_id"]
        resp = client.post(
            f"{BASE}/risks/{risk_id}/review-attestation",
            json={"attested_by": "OWNER001"},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["attested_by"] == "OWNER001"
        assert "next_review_date" in data
        # New date should be in the future
        from datetime import datetime
        new_date = datetime.fromisoformat(data["next_review_date"])
        assert new_date > datetime.utcnow()
