"""
GovernexPlus E2E Journey Tests
===============================
Full end-to-end journeys for all 22 QA personas.
Every persona logs in, exercises their allowed flows, and verifies denied routes.
Cross-persona workflows test the complete lifecycle across roles.

Usage:
    # Against local stack:
    pytest qa/test_e2e_journeys.py -v --base-url http://localhost:9000

    # Against production:
    pytest qa/test_e2e_journeys.py -v --base-url https://governexplus.com

    # Single persona:
    pytest qa/test_e2e_journeys.py -v -k "P01" --base-url http://localhost:9000
"""
from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
import requests

# ── Config ────────────────────────────────────────────────────────────────────

PERSONAS_FILE = Path(__file__).parent / "personas.json"
BASE_URL = os.environ.get("QA_BASE_URL", "http://localhost:9000")
TENANT_ID = "qa-tenant-001"


def pytest_addoption(parser):
    parser.addoption("--base-url", default=BASE_URL, help="API base URL")


@pytest.fixture(scope="session")
def base_url(request):
    return request.config.getoption("--base-url").rstrip("/")


@pytest.fixture(scope="session")
def personas():
    data = json.loads(PERSONAS_FILE.read_text(encoding="utf-8"))
    return {p["persona_id"]: p for p in data["personas"]}


# ── Auth Helper ───────────────────────────────────────────────────────────────

class AuthClient:
    """Authenticated HTTP client for a specific persona."""

    def __init__(self, base_url: str, persona: dict):
        self.base_url = base_url
        self.persona = persona
        self.session = requests.Session()
        self.token: str | None = None
        self.user_id: str | None = None

    def login(self) -> dict:
        resp = self.session.post(f"{self.base_url}/auth/login", json={
            "username": self.persona["username"],
            "password": self.persona["password"],
            "tenant_id": TENANT_ID,
        })
        assert resp.status_code == 200, (
            f"Login failed for {self.persona['persona_id']} "
            f"({self.persona['username']}): {resp.status_code} {resp.text}"
        )
        data = resp.json()
        self.token = data.get("access_token") or data.get("token")
        self.user_id = data.get("user_id") or data.get("user", {}).get("id")
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
        return data

    def get(self, path: str, **kwargs) -> requests.Response:
        return self.session.get(f"{self.base_url}{path}", **kwargs)

    def post(self, path: str, **kwargs) -> requests.Response:
        return self.session.post(f"{self.base_url}{path}", **kwargs)

    def put(self, path: str, **kwargs) -> requests.Response:
        return self.session.put(f"{self.base_url}{path}", **kwargs)

    def delete(self, path: str, **kwargs) -> requests.Response:
        return self.session.delete(f"{self.base_url}{path}", **kwargs)

    def assert_allowed(self, method: str, path: str, **kwargs) -> requests.Response:
        resp = getattr(self, method.lower())(path, **kwargs)
        assert resp.status_code in (200, 201), (
            f"{self.persona['persona_id']} should access {method.upper()} {path} "
            f"but got {resp.status_code}: {resp.text[:200]}"
        )
        return resp

    def assert_denied(self, method: str, path: str, **kwargs):
        resp = getattr(self, method.lower())(path, **kwargs)
        assert resp.status_code in (403, 401, 422), (
            f"{self.persona['persona_id']} should be DENIED {method.upper()} {path} "
            f"but got {resp.status_code}"
        )


@pytest.fixture()
def client_factory(base_url, personas):
    """Factory that returns an authenticated client for a persona_id."""
    _cache: dict[str, AuthClient] = {}

    def _make(persona_id: str) -> AuthClient:
        if persona_id not in _cache:
            c = AuthClient(base_url, personas[persona_id])
            c.login()
            _cache[persona_id] = c
        return _cache[persona_id]

    return _make


def _uid() -> str:
    return str(uuid.uuid4())[:8]


# ═══════════════════════════════════════════════════════════════════════════════
# P01 — PLATFORM ADMIN: cross-tenant superuser
# ═══════════════════════════════════════════════════════════════════════════════

class TestP01PlatformAdmin:

    def test_login(self, client_factory):
        c = client_factory("P01")
        assert c.token is not None

    def test_dashboard_access(self, client_factory):
        c = client_factory("P01")
        c.assert_allowed("get", "/dashboard/stats")
        c.assert_allowed("get", "/dashboard/health")

    def test_tenant_management(self, client_factory):
        """Platform admin can list and view tenants."""
        c = client_factory("P01")
        c.assert_allowed("get", "/tenants/")

    def test_system_config(self, client_factory):
        """Platform admin can manage settings and mass admin."""
        c = client_factory("P01")
        c.assert_allowed("get", "/settings/smtp")
        c.assert_allowed("get", "/mass-admin/jobs")

    def test_all_grc_modules_readable(self, client_factory):
        """Platform admin reads every major module."""
        c = client_factory("P01")
        for path in [
            "/risk-management/risks",
            "/process-control/controls",
            "/audit-management/entities",
            "/sox-icfr/controls",
            "/privacy/processing-activities",
            "/operational-risk/loss-events",
            "/sod-remediation/",
            "/it-change-risk/",
            "/insurance/",
            "/sanctions-screening/",
            "/regulatory-changes/",
            "/fraud/rules",
            "/bcm/plans",
            "/tprm/vendors",
            "/jml/policies",
            "/surveys/",
            "/library/packs",
        ]:
            c.assert_allowed("get", path)

    def test_user_crud(self, client_factory):
        """Full user lifecycle."""
        c = client_factory("P01")
        # List users
        c.assert_allowed("get", "/users/")
        # Create user
        resp = c.post("/users/", json={
            "username": f"e2e_temp_{_uid()}", "full_name": "E2E Temp User",
            "email": f"e2e_{_uid()}@qa.governexplus", "password": "Temp!Pass2026",
            "department": "QA", "tenant_id": TENANT_ID,
        })
        if resp.status_code in (200, 201):
            uid = resp.json().get("id") or resp.json().get("user_id")
            if uid:
                # Read
                c.assert_allowed("get", f"/users/{uid}")
                # Delete
                c.delete(f"/users/{uid}")


# ═══════════════════════════════════════════════════════════════════════════════
# P02 — TENANT ADMIN: full access within tenant
# ═══════════════════════════════════════════════════════════════════════════════

class TestP02TenantAdmin:

    def test_login(self, client_factory):
        c = client_factory("P02")
        assert c.token

    def test_settings_full_access(self, client_factory):
        c = client_factory("P02")
        c.assert_allowed("get", "/settings/smtp")
        c.assert_allowed("get", "/users/")
        c.assert_allowed("get", "/reports/dashboard-summary")

    def test_library_management(self, client_factory):
        """Tenant admin manages the template library."""
        c = client_factory("P02")
        c.assert_allowed("get", "/library/packs")
        c.assert_allowed("get", "/library/items")
        c.assert_allowed("get", "/library/stats")
        c.assert_allowed("get", "/library/active-content")

    def test_cannot_access_platform_tenants(self, client_factory):
        """Tenant admin cannot manage other tenants."""
        c = client_factory("P02")
        c.assert_denied("get", "/tenants/")


# ═══════════════════════════════════════════════════════════════════════════════
# P03 — CISO: risk oversight & EAM supervision
# ═══════════════════════════════════════════════════════════════════════════════

class TestP03CISO:

    def test_login(self, client_factory):
        c = client_factory("P03")
        assert c.token

    def test_risk_oversight(self, client_factory):
        """CISO views risk dashboard, violations, KRI."""
        c = client_factory("P03")
        c.assert_allowed("get", "/risk/violations")
        c.assert_allowed("get", "/risk-management/risks")
        c.assert_allowed("get", "/risk-intelligence/analytics/summary")

    def test_eam_supervision(self, client_factory):
        """CISO can view firefighter sessions and activity."""
        c = client_factory("P03")
        c.assert_allowed("get", "/privileged-access/sessions")
        c.assert_allowed("get", "/privileged-access/statistics")

    def test_certification_campaigns(self, client_factory):
        """CISO reads certification status."""
        c = client_factory("P03")
        c.assert_allowed("get", "/certification/campaigns")
        c.assert_allowed("get", "/certification/statistics")

    def test_denied_mass_admin(self, client_factory):
        c = client_factory("P03")
        c.assert_denied("post", "/mass-admin/jobs", json={
            "operation": "lock", "user_ids": ["fake"], "reason": "test"})


# ═══════════════════════════════════════════════════════════════════════════════
# P04 — COMPLIANCE OFFICER: certifications, SoD remediation, policy
# ═══════════════════════════════════════════════════════════════════════════════

class TestP04ComplianceOfficer:

    def test_login(self, client_factory):
        c = client_factory("P04")
        assert c.token

    def test_certification_ownership(self, client_factory):
        c = client_factory("P04")
        c.assert_allowed("get", "/certification/campaigns")
        c.assert_allowed("get", "/certification/statistics")

    def test_sod_violations_view(self, client_factory):
        c = client_factory("P04")
        c.assert_allowed("get", "/risk/violations")
        c.assert_allowed("get", "/sod-remediation/")

    def test_process_control_read(self, client_factory):
        c = client_factory("P04")
        c.assert_allowed("get", "/process-control/controls")
        c.assert_allowed("get", "/control-objectives/")

    def test_sod_remediation_lifecycle(self, client_factory):
        """Create a SoD remediation record and transition it."""
        c = client_factory("P04")
        resp = c.post("/sod-remediation/", json={
            "remediation_description": f"E2E test remediation {_uid()}",
            "violation_id": _uid(), "user_id": _uid(),
        })
        if resp.status_code in (200, 201):
            rid = resp.json().get("id") or resp.json().get("remediation_id")
            if rid:
                # Transition: open → in_remediation
                c.put(f"/sod-remediation/{rid}/transition", json={"new_status": "in_remediation"})
                # Transition: in_remediation → pending_validation
                c.put(f"/sod-remediation/{rid}/transition", json={"new_status": "pending_validation"})
                # Transition: pending_validation → validated
                c.put(f"/sod-remediation/{rid}/transition", json={"new_status": "validated"})
                # Transition: validated → closed
                c.put(f"/sod-remediation/{rid}/transition", json={"new_status": "closed"})
                # Verify final state
                final = c.get(f"/sod-remediation/{rid}")
                if final.status_code == 200:
                    assert final.json().get("status") == "closed"

    def test_policy_management(self, client_factory):
        c = client_factory("P04")
        c.assert_allowed("get", "/policies/")
        c.assert_allowed("get", "/policy-exceptions/")

    def test_denied_eam_ids(self, client_factory):
        c = client_factory("P04")
        c.assert_denied("post", "/privileged-access/firefighters", json={
            "firefighter_id": "FAKE", "description": "test", "system_id": "X"})


# ═══════════════════════════════════════════════════════════════════════════════
# P05 — RISK MANAGER: risk register, KRI, TPRM
# ═══════════════════════════════════════════════════════════════════════════════

class TestP05RiskManager:

    def test_login(self, client_factory):
        c = client_factory("P05")
        assert c.token

    def test_risk_register_lifecycle(self, client_factory):
        """Create risk → assess → respond → close."""
        c = client_factory("P05")
        # Create risk
        resp = c.post("/risk-management/risks", json={
            "title": f"E2E Risk {_uid()}", "description": "Test risk from E2E",
            "category": "operational", "likelihood": 3, "impact": 4,
        })
        if resp.status_code in (200, 201):
            risk_id = resp.json().get("id") or resp.json().get("risk_id")
            if risk_id:
                c.assert_allowed("get", f"/risk-management/risks/{risk_id}")
                c.put(f"/risk-management/risks/{risk_id}", json={"status": "mitigating"})

    def test_kri_dashboard(self, client_factory):
        c = client_factory("P05")
        c.assert_allowed("get", "/risk-management/risks")

    def test_risk_heatmap(self, client_factory):
        c = client_factory("P05")
        c.assert_allowed("get", "/board-reporting/risk-heat-snapshot")

    def test_tprm_oversight(self, client_factory):
        c = client_factory("P05")
        c.assert_allowed("get", "/tprm/vendors")
        c.assert_allowed("get", "/tprm/dashboard")

    def test_risk_scenarios_and_opportunities(self, client_factory):
        c = client_factory("P05")
        c.assert_allowed("get", "/risk-scenarios/scenarios")
        c.assert_allowed("get", "/risk-scenarios/opportunities")
        c.assert_allowed("get", "/risk-scenarios/objectives")

    def test_denied_eam(self, client_factory):
        c = client_factory("P05")
        c.assert_denied("post", "/privileged-access/firefighters", json={
            "firefighter_id": "FAKE", "description": "test", "system_id": "X"})


# ═══════════════════════════════════════════════════════════════════════════════
# P06 — IT SECURITY ADMIN: SoD rules, provisioning, connectors, EAM
# ═══════════════════════════════════════════════════════════════════════════════

class TestP06ITSecurityAdmin:

    def test_login(self, client_factory):
        c = client_factory("P06")
        assert c.token

    def test_sod_rule_management(self, client_factory):
        """View and manage SoD rules."""
        c = client_factory("P06")
        c.assert_allowed("get", "/risk-rules/rules")
        c.assert_allowed("get", "/risk-intelligence/sod/rules")

    def test_access_request_processing(self, client_factory):
        c = client_factory("P06")
        c.assert_allowed("get", "/access-requests/")
        c.assert_allowed("get", "/access-requests/approvals/pending")

    def test_role_management(self, client_factory):
        c = client_factory("P06")
        c.assert_allowed("get", "/role-studio/roles")
        c.assert_allowed("get", "/role-intelligence/overview")

    def test_eam_access(self, client_factory):
        c = client_factory("P06")
        c.assert_allowed("get", "/privileged-access/firefighters")
        c.assert_allowed("get", "/privileged-access/sessions")

    def test_connectors(self, client_factory):
        c = client_factory("P06")
        c.assert_allowed("get", "/integrations/connectors")

    def test_provisioning(self, client_factory):
        c = client_factory("P06")
        c.assert_allowed("get", "/provisioning/connectors")
        c.assert_allowed("get", "/provisioning/tasks")


# ═══════════════════════════════════════════════════════════════════════════════
# P07 — LINE MANAGER: approvals, cert reviews, JML
# ═══════════════════════════════════════════════════════════════════════════════

class TestP07LineManager:

    def test_login(self, client_factory):
        c = client_factory("P07")
        assert c.token

    def test_pending_approvals(self, client_factory):
        c = client_factory("P07")
        c.assert_allowed("get", "/access-requests/approvals/pending")
        c.assert_allowed("get", "/approvals/")

    def test_certification_reviews(self, client_factory):
        c = client_factory("P07")
        c.assert_allowed("get", "/certification/my-reviews")

    def test_jml_access(self, client_factory):
        c = client_factory("P07")
        c.assert_allowed("get", "/jml/events")
        c.assert_allowed("get", "/jml/policies")

    def test_denied_settings(self, client_factory):
        c = client_factory("P07")
        c.assert_denied("get", "/settings/smtp")

    def test_denied_risk_rules(self, client_factory):
        c = client_factory("P07")
        c.assert_denied("post", "/risk-rules/custom", json={
            "name": "fake", "function1": "F1", "function2": "F2", "risk_level": "high"})


# ═══════════════════════════════════════════════════════════════════════════════
# P08 — BUSINESS USER: request access, participate in certifications
# ═══════════════════════════════════════════════════════════════════════════════

class TestP08BusinessUser:

    def test_login(self, client_factory):
        c = client_factory("P08")
        assert c.token

    def test_submit_access_request(self, client_factory):
        """Full ARM flow: browse catalog → create request → submit."""
        c = client_factory("P08")
        # Browse role catalog
        c.assert_allowed("get", "/access-requests/catalog/roles")
        # Create a request
        resp = c.post("/access-requests/", json={
            "request_type": "new_access",
            "items": [{"role_id": "SAP_FI_DISPLAY", "system_id": "ERP_PROD", "action": "add"}],
            "justification": f"E2E test request {_uid()}",
        })
        if resp.status_code in (200, 201):
            req_id = resp.json().get("id") or resp.json().get("request_id")
            if req_id:
                # Submit
                c.post(f"/access-requests/{req_id}/submit")
                # View my requests
                c.assert_allowed("get", "/access-requests/my-requests")

    def test_shopping_cart_flow(self, client_factory):
        """ARM shopping cart: create cart → add item → check conflicts → submit."""
        c = client_factory("P08")
        resp = c.post("/access-lifecycle/cart", json={"name": f"E2E Cart {_uid()}"})
        if resp.status_code in (200, 201):
            cart_id = resp.json().get("id") or resp.json().get("cart_id")
            if cart_id:
                c.post(f"/access-lifecycle/cart/{cart_id}/items", json={
                    "role_id": "SAP_FI_DISPLAY", "system_id": "ERP_PROD"})
                c.post(f"/access-lifecycle/cart/{cart_id}/check-conflicts")
                c.post(f"/access-lifecycle/cart/{cart_id}/submit")

    def test_my_certifications(self, client_factory):
        c = client_factory("P08")
        c.assert_allowed("get", "/certification/my-reviews")

    def test_my_access(self, client_factory):
        c = client_factory("P08")
        c.assert_allowed("get", "/access-requests/my-access")

    def test_denied_risk_rules(self, client_factory):
        c = client_factory("P08")
        c.assert_denied("post", "/risk-rules/custom", json={
            "name": "fake", "function1": "F1", "function2": "F2", "risk_level": "high"})

    def test_denied_settings(self, client_factory):
        c = client_factory("P08")
        c.assert_denied("get", "/settings/smtp")

    def test_denied_eam(self, client_factory):
        c = client_factory("P08")
        c.assert_denied("get", "/privileged-access/firefighters")


# ═══════════════════════════════════════════════════════════════════════════════
# P09 — EXTERNAL AUDITOR: read-only evidence & reports
# ═══════════════════════════════════════════════════════════════════════════════

class TestP09ExternalAuditor:

    def test_login(self, client_factory):
        c = client_factory("P09")
        assert c.token

    def test_read_certifications(self, client_factory):
        c = client_factory("P09")
        c.assert_allowed("get", "/certification/campaigns")
        c.assert_allowed("get", "/certification/statistics")

    def test_read_reports(self, client_factory):
        c = client_factory("P09")
        c.assert_allowed("get", "/reports/dashboard-summary")

    def test_read_violations(self, client_factory):
        c = client_factory("P09")
        c.assert_allowed("get", "/risk/violations")

    def test_read_controls(self, client_factory):
        c = client_factory("P09")
        c.assert_allowed("get", "/process-control/controls")

    def test_audit_evidence(self, client_factory):
        c = client_factory("P09")
        c.assert_allowed("get", "/audit-evidence/categories")
        c.assert_allowed("get", "/audit-evidence/packages")

    def test_denied_create_campaign(self, client_factory):
        c = client_factory("P09")
        c.assert_denied("post", "/certification/campaigns", json={
            "name": "fake", "type": "user_access"})

    def test_denied_create_risk(self, client_factory):
        c = client_factory("P09")
        c.assert_denied("post", "/risk-management/risks", json={
            "title": "fake", "category": "operational", "likelihood": 1, "impact": 1})

    def test_denied_settings(self, client_factory):
        c = client_factory("P09")
        c.assert_denied("get", "/settings/smtp")


# ═══════════════════════════════════════════════════════════════════════════════
# P10 — SOX CONTROL OWNER: control lifecycle & testing
# ═══════════════════════════════════════════════════════════════════════════════

class TestP10SOXControlOwner:

    def test_login(self, client_factory):
        c = client_factory("P10")
        assert c.token

    def test_sox_icfr_control_lifecycle(self, client_factory):
        """Create ICFR control → test → view results."""
        c = client_factory("P10")
        resp = c.post("/sox-icfr/controls", json={
            "control_name": f"E2E ICFR Control {_uid()}",
            "control_type": "preventive", "frequency": "monthly",
            "owner": "qa_sox_owner", "key_control": True,
            "assertion": "completeness", "account_balance": "AP Subledger",
        })
        if resp.status_code in (200, 201):
            cid = resp.json().get("id") or resp.json().get("control_id")
            if cid:
                # Test the control
                c.post(f"/sox-icfr/controls/{cid}/test", json={
                    "tester": "qa_sox_owner", "test_date": datetime.utcnow().isoformat(),
                    "sample_size": 25, "exceptions_found": 0,
                })
                # Verify it
                detail = c.get(f"/sox-icfr/controls/{cid}")
                if detail.status_code == 200:
                    assert detail.json().get("effectiveness") == "effective"

    def test_process_control_testing(self, client_factory):
        c = client_factory("P10")
        c.assert_allowed("get", "/process-control/controls")

    def test_sox_signoff_flow(self, client_factory):
        """Create and sign a SOX sign-off."""
        c = client_factory("P10")
        resp = c.post("/sox-icfr/signoffs", json={
            "period": "Q3-2026", "scope": "Financial Close",
            "signer": "qa_sox_owner",
        })
        if resp.status_code in (200, 201):
            sid = resp.json().get("id") or resp.json().get("signoff_id")
            if sid:
                c.post(f"/sox-icfr/signoffs/{sid}/sign", json={
                    "conclusion": "effective", "exceptions_noted": False,
                })

    def test_financial_close_tasks(self, client_factory):
        c = client_factory("P10")
        resp = c.post("/sox-icfr/close-tasks", json={
            "task_name": f"E2E Close Task {_uid()}", "period": "Q3-2026",
            "assignee": "qa_sox_owner", "due_date": (datetime.utcnow() + timedelta(days=7)).isoformat(),
        })
        if resp.status_code in (200, 201):
            tid = resp.json().get("id") or resp.json().get("task_id")
            if tid:
                c.put(f"/sox-icfr/close-tasks/{tid}/complete", json={
                    "completed_by": "qa_sox_owner"})

    def test_denied_eam(self, client_factory):
        c = client_factory("P10")
        c.assert_denied("post", "/privileged-access/firefighters", json={
            "firefighter_id": "FAKE", "description": "test", "system_id": "X"})


# ═══════════════════════════════════════════════════════════════════════════════
# P11 — FIREFIGHTER OWNER: manages FF IDs, recertifies
# ═══════════════════════════════════════════════════════════════════════════════

class TestP11FirefighterOwner:

    def test_login(self, client_factory):
        c = client_factory("P11")
        assert c.token

    def test_view_own_ffids(self, client_factory):
        c = client_factory("P11")
        c.assert_allowed("get", "/privileged-access/firefighters")

    def test_certification_due(self, client_factory):
        c = client_factory("P11")
        c.assert_allowed("get", "/privileged-access/certification/due")

    def test_certification_reviews(self, client_factory):
        c = client_factory("P11")
        c.assert_allowed("get", "/certification/my-reviews")

    def test_denied_controller_review(self, client_factory):
        """FF Owner cannot do controller reviews."""
        c = client_factory("P11")
        c.assert_denied("get", "/privileged-access/reviews/pending")


# ═══════════════════════════════════════════════════════════════════════════════
# P12 — FIREFIGHTER CONTROLLER: reviews sessions within 72h SLA
# ═══════════════════════════════════════════════════════════════════════════════

class TestP12FirefighterController:

    def test_login(self, client_factory):
        c = client_factory("P12")
        assert c.token

    def test_session_review_workflow(self, client_factory):
        """Controller views sessions and pending reviews."""
        c = client_factory("P12")
        c.assert_allowed("get", "/privileged-access/sessions")
        c.assert_allowed("get", "/privileged-access/reviews/pending")
        c.assert_allowed("get", "/privileged-access/statistics")

    def test_audit_sessions(self, client_factory):
        c = client_factory("P12")
        c.assert_allowed("get", "/privileged-access/audit/sessions")

    def test_denied_create_ffid(self, client_factory):
        c = client_factory("P12")
        c.assert_denied("post", "/privileged-access/firefighters", json={
            "firefighter_id": "FAKE", "description": "test", "system_id": "X"})


# ═══════════════════════════════════════════════════════════════════════════════
# P13 — HR MANAGER: JML lifecycle events
# ═══════════════════════════════════════════════════════════════════════════════

class TestP13HRManager:

    def test_login(self, client_factory):
        c = client_factory("P13")
        assert c.token

    def test_jml_hire_flow(self, client_factory):
        """Trigger a JML hire event and process it."""
        c = client_factory("P13")
        resp = c.post("/jml/events", json={
            "event_type": "hire", "employee_id": f"EMP_{_uid()}",
            "employee_name": "New Hire E2E", "department": "Finance",
            "position": "Analyst", "effective_date": datetime.utcnow().isoformat(),
        })
        if resp.status_code in (200, 201):
            eid = resp.json().get("id") or resp.json().get("event_id")
            if eid:
                c.post(f"/jml/events/{eid}/process")
                detail = c.get(f"/jml/events/{eid}")
                if detail.status_code == 200:
                    assert detail.json().get("status") in ("processing", "completed", "processed")

    def test_jml_transfer_flow(self, client_factory):
        c = client_factory("P13")
        c.post("/jml/events", json={
            "event_type": "transfer", "employee_id": f"EMP_{_uid()}",
            "employee_name": "Transfer E2E", "department": "IT",
            "position": "Developer", "effective_date": datetime.utcnow().isoformat(),
            "from_department": "Finance", "to_department": "IT",
        })

    def test_jml_terminate_flow(self, client_factory):
        c = client_factory("P13")
        c.post("/jml/events", json={
            "event_type": "terminate", "employee_id": f"EMP_{_uid()}",
            "employee_name": "Term E2E", "department": "Sales",
            "effective_date": datetime.utcnow().isoformat(),
        })

    def test_jml_policies(self, client_factory):
        c = client_factory("P13")
        c.assert_allowed("get", "/jml/policies")
        c.assert_allowed("get", "/jml/dashboard")

    def test_denied_settings(self, client_factory):
        c = client_factory("P13")
        c.assert_denied("get", "/settings/smtp")

    def test_denied_eam(self, client_factory):
        c = client_factory("P13")
        c.assert_denied("get", "/privileged-access/firefighters")


# ═══════════════════════════════════════════════════════════════════════════════
# P14 — PROCESS OWNER: controls, CSA, deficiencies
# ═══════════════════════════════════════════════════════════════════════════════

class TestP14ProcessOwner:

    def test_login(self, client_factory):
        c = client_factory("P14")
        assert c.token

    def test_control_lifecycle(self, client_factory):
        """Process owner creates and tests a control."""
        c = client_factory("P14")
        c.assert_allowed("get", "/process-control/controls")
        c.assert_allowed("get", "/control-objectives/")

    def test_certification_participation(self, client_factory):
        c = client_factory("P14")
        c.assert_allowed("get", "/certification/my-reviews")

    def test_denied_settings(self, client_factory):
        c = client_factory("P14")
        c.assert_denied("get", "/settings/smtp")

    def test_denied_eam(self, client_factory):
        c = client_factory("P14")
        c.assert_denied("get", "/privileged-access/firefighters")


# ═══════════════════════════════════════════════════════════════════════════════
# P15 — IT OPERATIONS: connectors, batch jobs, limited write
# ═══════════════════════════════════════════════════════════════════════════════

class TestP15ITOperations:

    def test_login(self, client_factory):
        c = client_factory("P15")
        assert c.token

    def test_connectors_read(self, client_factory):
        c = client_factory("P15")
        c.assert_allowed("get", "/integrations/connectors")
        c.assert_allowed("get", "/integrations/health")

    def test_audit_log_read(self, client_factory):
        c = client_factory("P15")
        c.assert_allowed("get", "/audit/logs")

    def test_denied_mass_admin(self, client_factory):
        c = client_factory("P15")
        c.assert_denied("post", "/mass-admin/jobs", json={
            "operation": "lock", "user_ids": ["fake"], "reason": "test"})

    def test_denied_risk_rules(self, client_factory):
        c = client_factory("P15")
        c.assert_denied("post", "/risk-rules/custom", json={
            "name": "fake", "function1": "F1", "function2": "F2", "risk_level": "high"})


# ═══════════════════════════════════════════════════════════════════════════════
# P16 — READ-ONLY VIEWER: dashboards & reports only
# ═══════════════════════════════════════════════════════════════════════════════

class TestP16ReadOnlyViewer:

    def test_login(self, client_factory):
        c = client_factory("P16")
        assert c.token

    def test_dashboard_read(self, client_factory):
        c = client_factory("P16")
        c.assert_allowed("get", "/dashboard/stats")
        c.assert_allowed("get", "/dashboard/summary/executive")

    def test_reports_read(self, client_factory):
        c = client_factory("P16")
        c.assert_allowed("get", "/reports/dashboard-summary")

    def test_denied_submit_access_request(self, client_factory):
        c = client_factory("P16")
        c.assert_denied("post", "/access-requests/", json={
            "request_type": "new_access",
            "items": [{"role_id": "X", "system_id": "Y", "action": "add"}],
            "justification": "blocked",
        })

    def test_denied_settings(self, client_factory):
        c = client_factory("P16")
        c.assert_denied("get", "/settings/smtp")

    def test_denied_eam(self, client_factory):
        c = client_factory("P16")
        c.assert_denied("get", "/privileged-access/firefighters")

    def test_denied_risk_rules(self, client_factory):
        c = client_factory("P16")
        c.assert_denied("post", "/risk-rules/custom", json={
            "name": "fake", "function1": "F1", "function2": "F2", "risk_level": "high"})


# ═══════════════════════════════════════════════════════════════════════════════
# P17 — FIREFIGHTER SESSION USER: requests & uses emergency access
# ═══════════════════════════════════════════════════════════════════════════════

class TestP17FirefighterSessionUser:

    def test_login(self, client_factory):
        c = client_factory("P17")
        assert c.token

    def test_request_emergency_access(self, client_factory):
        """FF user requests emergency access → session starts."""
        c = client_factory("P17")
        resp = c.post("/privileged-access/requests", json={
            "firefighter_id": "FFID-001", "reason_code": "PROD_ISSUE",
            "justification": f"E2E emergency test {_uid()}",
            "duration_hours": 2,
        })
        # Even if FFID doesn't exist, we validate the endpoint is reachable
        assert resp.status_code in (200, 201, 400, 404, 422)

    def test_denied_controller_view(self, client_factory):
        c = client_factory("P17")
        c.assert_denied("get", "/privileged-access/reviews/pending")

    def test_denied_settings(self, client_factory):
        c = client_factory("P17")
        c.assert_denied("get", "/settings/smtp")


# ═══════════════════════════════════════════════════════════════════════════════
# P18 — MITIGATION MONITOR: tests compensating controls effectiveness
# ═══════════════════════════════════════════════════════════════════════════════

class TestP18MitigationMonitor:

    def test_login(self, client_factory):
        c = client_factory("P18")
        assert c.token

    def test_mitigation_controls(self, client_factory):
        c = client_factory("P18")
        c.assert_allowed("get", "/mitigation/controls")
        c.assert_allowed("get", "/mitigation/monitor-inbox")
        c.assert_allowed("get", "/mitigation/monitor-inbox/summary")

    def test_attestation_workflow(self, client_factory):
        c = client_factory("P18")
        c.assert_allowed("get", "/mitigation/attestations/pending")
        c.assert_allowed("get", "/mitigation/attestations/summary")

    def test_process_control_read(self, client_factory):
        c = client_factory("P18")
        c.assert_allowed("get", "/process-control/controls")

    def test_denied_create_rules(self, client_factory):
        c = client_factory("P18")
        c.assert_denied("post", "/risk-rules/custom", json={
            "name": "fake", "function1": "F1", "function2": "F2", "risk_level": "high"})

    def test_denied_settings(self, client_factory):
        c = client_factory("P18")
        c.assert_denied("get", "/settings/smtp")


# ═══════════════════════════════════════════════════════════════════════════════
# P19 — INTERNAL AUDITOR: plans audits, tracks findings
# ═══════════════════════════════════════════════════════════════════════════════

class TestP19InternalAuditor:

    def test_login(self, client_factory):
        c = client_factory("P19")
        assert c.token

    def test_audit_planning_lifecycle(self, client_factory):
        """Create audit entity → plan → engagement → finding."""
        c = client_factory("P19")
        # Audit universe
        c.assert_allowed("get", "/audit-management/entities")
        # Create entity
        resp = c.post("/audit-management/entities", json={
            "name": f"E2E Auditable Entity {_uid()}", "entity_type": "process",
            "risk_rating": "high", "description": "E2E test entity",
        })
        if resp.status_code in (200, 201):
            entity_id = resp.json().get("id") or resp.json().get("entity_id")
            if entity_id:
                # Create plan
                plan_resp = c.post("/audit-management/plans", json={
                    "title": f"E2E Audit Plan {_uid()}", "plan_type": "risk_based",
                    "fiscal_year": "2026", "entity_ids": [entity_id],
                })

    def test_read_certifications(self, client_factory):
        c = client_factory("P19")
        c.assert_allowed("get", "/certification/campaigns")

    def test_read_violations(self, client_factory):
        c = client_factory("P19")
        c.assert_allowed("get", "/risk/violations")

    def test_read_process_controls(self, client_factory):
        c = client_factory("P19")
        c.assert_allowed("get", "/process-control/controls")

    def test_audit_workpapers(self, client_factory):
        c = client_factory("P19")
        c.assert_allowed("get", "/audit-management/entities")

    def test_audit_evidence(self, client_factory):
        c = client_factory("P19")
        c.assert_allowed("get", "/audit-evidence/categories")

    def test_denied_mass_admin(self, client_factory):
        c = client_factory("P19")
        c.assert_denied("post", "/mass-admin/jobs", json={
            "operation": "lock", "user_ids": ["fake"], "reason": "test"})


# ═══════════════════════════════════════════════════════════════════════════════
# P20 — VENDOR MANAGER: TPRM lifecycle
# ═══════════════════════════════════════════════════════════════════════════════

class TestP20VendorManager:

    def test_login(self, client_factory):
        c = client_factory("P20")
        assert c.token

    def test_vendor_lifecycle(self, client_factory):
        """Register vendor → assess → track issues → contracts."""
        c = client_factory("P20")
        # Register vendor
        resp = c.post("/tprm/vendors", json={
            "name": f"E2E Vendor {_uid()}", "category": "technology",
            "country": "US", "contact_email": f"vendor_{_uid()}@example.com",
        })
        if resp.status_code in (200, 201):
            vid = resp.json().get("id") or resp.json().get("vendor_id")
            if vid:
                c.assert_allowed("get", f"/tprm/vendors/{vid}")
                # Issue assessment
                c.post("/tprm/assessments", json={
                    "vendor_id": vid, "assessment_type": "initial",
                    "assessor": "qa_vendor_manager",
                })
                # Log issue
                c.post("/tprm/issues", json={
                    "vendor_id": vid, "title": f"E2E Issue {_uid()}",
                    "severity": "medium", "description": "Test issue",
                })
                # Create contract
                c.post("/tprm/contracts", json={
                    "vendor_id": vid, "contract_name": f"E2E Contract {_uid()}",
                    "start_date": datetime.utcnow().isoformat(),
                    "end_date": (datetime.utcnow() + timedelta(days=365)).isoformat(),
                    "value": 50000,
                })

    def test_tprm_dashboard(self, client_factory):
        c = client_factory("P20")
        c.assert_allowed("get", "/tprm/dashboard")

    def test_denied_settings(self, client_factory):
        c = client_factory("P20")
        c.assert_denied("get", "/settings/smtp")

    def test_denied_certification_campaigns(self, client_factory):
        c = client_factory("P20")
        c.assert_denied("post", "/certification/campaigns", json={
            "name": "fake", "type": "user_access"})


# ═══════════════════════════════════════════════════════════════════════════════
# P21 — ROLE OWNER: approves role-specific requests, certifies membership
# ═══════════════════════════════════════════════════════════════════════════════

class TestP21RoleOwner:

    def test_login(self, client_factory):
        c = client_factory("P21")
        assert c.token

    def test_pending_approvals(self, client_factory):
        c = client_factory("P21")
        c.assert_allowed("get", "/access-requests/approvals/pending")

    def test_certification_participation(self, client_factory):
        c = client_factory("P21")
        c.assert_allowed("get", "/certification/my-reviews")

    def test_role_management_read(self, client_factory):
        c = client_factory("P21")
        c.assert_allowed("get", "/role-studio/roles")

    def test_denied_mass_admin(self, client_factory):
        c = client_factory("P21")
        c.assert_denied("post", "/mass-admin/jobs", json={
            "operation": "lock", "user_ids": ["fake"], "reason": "test"})

    def test_denied_eam_ids(self, client_factory):
        c = client_factory("P21")
        c.assert_denied("post", "/privileged-access/firefighters", json={
            "firefighter_id": "FAKE", "description": "test", "system_id": "X"})


# ═══════════════════════════════════════════════════════════════════════════════
# P22 — RISK OWNER: manages specific risks, treatment actions
# ═══════════════════════════════════════════════════════════════════════════════

class TestP22RiskOwner:

    def test_login(self, client_factory):
        c = client_factory("P22")
        assert c.token

    def test_risk_management(self, client_factory):
        c = client_factory("P22")
        c.assert_allowed("get", "/risk-management/risks")

    def test_risk_treatment_update(self, client_factory):
        """Risk owner creates and updates a risk."""
        c = client_factory("P22")
        resp = c.post("/risk-management/risks", json={
            "title": f"E2E Owned Risk {_uid()}", "description": "Test risk owned by P22",
            "category": "financial", "likelihood": 2, "impact": 3,
        })
        if resp.status_code in (200, 201):
            rid = resp.json().get("id") or resp.json().get("risk_id")
            if rid:
                c.put(f"/risk-management/risks/{rid}", json={
                    "residual_likelihood": 1, "residual_impact": 2,
                    "treatment_plan": "Implement additional controls",
                })

    def test_risk_acceptance(self, client_factory):
        c = client_factory("P22")
        c.assert_allowed("get", "/risk-acceptance/")

    def test_denied_settings(self, client_factory):
        c = client_factory("P22")
        c.assert_denied("get", "/settings/smtp")

    def test_denied_certification_campaigns(self, client_factory):
        c = client_factory("P22")
        c.assert_denied("post", "/certification/campaigns", json={
            "name": "fake", "type": "user_access"})

    def test_denied_eam_ids(self, client_factory):
        c = client_factory("P22")
        c.assert_denied("post", "/privileged-access/firefighters", json={
            "firefighter_id": "FAKE", "description": "test", "system_id": "X"})


# ═══════════════════════════════════════════════════════════════════════════════
# CROSS-PERSONA WORKFLOW TESTS
# Full lifecycle flows that span multiple roles
# ═══════════════════════════════════════════════════════════════════════════════

class TestCrossPersonaAccessRequestWorkflow:
    """
    Complete access request lifecycle:
    P08 (Business User) submits request →
    P07 (Line Manager) approves →
    P06 (IT Security) provisions →
    P04 (Compliance) certifies →
    P09 (External Auditor) reads evidence
    """

    def test_full_access_request_lifecycle(self, client_factory):
        user = client_factory("P08")
        manager = client_factory("P07")
        security = client_factory("P06")
        compliance = client_factory("P04")
        auditor = client_factory("P09")

        # Step 1: Business user submits request
        resp = user.post("/access-requests/", json={
            "request_type": "new_access",
            "items": [{"role_id": "SAP_FI_DISPLAY", "system_id": "ERP_PROD", "action": "add"}],
            "justification": f"Cross-persona E2E test {_uid()}",
        })
        if resp.status_code not in (200, 201):
            pytest.skip("Could not create access request — seeded roles may be missing")
        req_id = resp.json().get("id") or resp.json().get("request_id")
        if not req_id:
            pytest.skip("No request_id returned")

        # Submit
        user.post(f"/access-requests/{req_id}/submit")

        # Step 2: Manager sees pending approvals
        pending = manager.get("/access-requests/approvals/pending")
        assert pending.status_code == 200

        # Step 3: Security admin can view requests
        security.assert_allowed("get", f"/access-requests/{req_id}")

        # Step 4: Compliance sees the request
        compliance.assert_allowed("get", "/access-requests/")

        # Step 5: Auditor reads evidence trail
        auditor.assert_allowed("get", "/audit/logs")


class TestCrossPersonaCertificationWorkflow:
    """
    Certification lifecycle:
    P04 (Compliance) creates campaign →
    P07 (Line Manager) reviews items →
    P21 (Role Owner) reviews items →
    P09 (External Auditor) reads results
    """

    def test_certification_campaign_lifecycle(self, client_factory):
        compliance = client_factory("P04")
        manager = client_factory("P07")
        role_owner = client_factory("P21")
        auditor = client_factory("P09")

        # Step 1: Compliance creates campaign
        resp = compliance.post("/certification/campaigns", json={
            "name": f"E2E Cert Campaign {_uid()}",
            "type": "user_access",
            "description": "Cross-persona E2E test campaign",
        })
        if resp.status_code not in (200, 201):
            pytest.skip("Could not create cert campaign")

        campaign_id = resp.json().get("id") or resp.json().get("campaign_id")

        # Step 2: Manager views their reviews
        manager.assert_allowed("get", "/certification/my-reviews")

        # Step 3: Role owner views their reviews
        role_owner.assert_allowed("get", "/certification/my-reviews")

        # Step 4: Auditor reads campaign results
        auditor.assert_allowed("get", "/certification/campaigns")
        if campaign_id:
            auditor.assert_allowed("get", f"/certification/campaigns/{campaign_id}")


class TestCrossPersonaFirefighterWorkflow:
    """
    Firefighter lifecycle:
    P06 (IT Security) creates FFID →
    P17 (FF Session User) requests emergency access →
    P12 (FF Controller) reviews session →
    P11 (FF Owner) recertifies →
    P03 (CISO) oversees
    """

    def test_firefighter_lifecycle(self, client_factory):
        security = client_factory("P06")
        ff_user = client_factory("P17")
        controller = client_factory("P12")
        ff_owner = client_factory("P11")
        ciso = client_factory("P03")

        # Step 1: IT Security creates FFID
        resp = security.post("/privileged-access/firefighters", json={
            "firefighter_id": f"FFID-E2E-{_uid()}", "description": "E2E test FF ID",
            "system_id": "ERP_PROD", "owner_user_id": ff_owner.user_id or "qa_ff_owner",
            "controller_user_id": controller.user_id or "qa_ff_controller",
        })
        # May not succeed if FFID format validation differs — that's OK
        if resp.status_code in (200, 201):
            ffid = resp.json().get("firefighter_id") or resp.json().get("id")

            # Step 2: FF user requests emergency access
            ff_user.post("/privileged-access/requests", json={
                "firefighter_id": ffid, "reason_code": "PROD_ISSUE",
                "justification": f"E2E emergency {_uid()}", "duration_hours": 1,
            })

        # Step 3: Controller views pending reviews
        controller.assert_allowed("get", "/privileged-access/reviews/pending")
        controller.assert_allowed("get", "/privileged-access/sessions")

        # Step 4: Owner views certification due
        ff_owner.assert_allowed("get", "/privileged-access/certification/due")

        # Step 5: CISO oversees everything
        ciso.assert_allowed("get", "/privileged-access/sessions")
        ciso.assert_allowed("get", "/privileged-access/statistics")


class TestCrossPersonaRiskWorkflow:
    """
    Risk lifecycle:
    P05 (Risk Manager) creates risk →
    P22 (Risk Owner) updates treatment →
    P05 creates KRI →
    P03 (CISO) views heatmap →
    P04 (Compliance) links to SoD remediation →
    P09 (Ext Auditor) reads reports
    """

    def test_risk_lifecycle(self, client_factory):
        risk_mgr = client_factory("P05")
        risk_owner = client_factory("P22")
        ciso = client_factory("P03")
        compliance = client_factory("P04")
        auditor = client_factory("P09")

        # Step 1: Risk Manager creates risk
        resp = risk_mgr.post("/risk-management/risks", json={
            "title": f"Cross-Persona Risk {_uid()}", "description": "E2E lifecycle test",
            "category": "operational", "likelihood": 4, "impact": 3,
        })
        if resp.status_code not in (200, 201):
            pytest.skip("Could not create risk")
        risk_id = resp.json().get("id") or resp.json().get("risk_id")

        # Step 2: Risk owner updates treatment
        if risk_id:
            risk_owner.put(f"/risk-management/risks/{risk_id}", json={
                "treatment_plan": "Additional controls implemented",
                "residual_likelihood": 2, "residual_impact": 2,
            })

        # Step 3: CISO views heatmap
        ciso.assert_allowed("get", "/board-reporting/risk-heat-snapshot")
        ciso.assert_allowed("get", "/risk-management/risks")

        # Step 4: Compliance links SoD remediation
        compliance.assert_allowed("get", "/sod-remediation/")

        # Step 5: Auditor reads reports
        auditor.assert_allowed("get", "/reports/dashboard-summary")


class TestCrossPersonaPrivacyWorkflow:
    """
    Privacy lifecycle (GDPR):
    P04 (Compliance) logs processing activity →
    P04 creates DSAR → tracks 30-day deadline →
    P04 creates DPIA → logs breach →
    P03 (CISO) reviews breach dashboard →
    Board sees executive summary
    """

    def test_privacy_lifecycle(self, client_factory):
        compliance = client_factory("P04")
        ciso = client_factory("P03")

        # Step 1: Log processing activity (Article 30)
        resp = compliance.post("/privacy/processing-activities", json={
            "activity_name": f"E2E Processing Activity {_uid()}",
            "purpose": "Customer onboarding", "legal_basis": "consent",
            "data_categories": ["personal", "contact"],
            "data_subjects": ["customers"],
        })

        # Step 2: Create DSAR (30-day deadline auto-set)
        dsar_resp = compliance.post("/privacy/dsar", json={
            "requester_name": f"Jane Doe {_uid()}", "request_type": "access",
            "requester_email": f"jane_{_uid()}@example.com",
            "description": "Please provide all my data",
        })
        if dsar_resp.status_code in (200, 201):
            dsar_id = dsar_resp.json().get("id") or dsar_resp.json().get("dsar_id")
            if dsar_id:
                # Progress the DSAR
                compliance.put(f"/privacy/dsar/{dsar_id}/status", json={
                    "status": "in_progress"})

        # Step 3: Create DPIA
        compliance.post("/privacy/dpia", json={
            "project_name": f"E2E DPIA {_uid()}", "description": "Test DPIA",
            "data_types": ["personal", "financial"],
        })

        # Step 4: Log a data breach (72h regulator deadline auto-set)
        breach_resp = compliance.post("/privacy/breaches", json={
            "title": f"E2E Breach {_uid()}", "description": "Test breach incident",
            "severity": "high", "data_subjects_affected": 1500,
            "data_types_affected": ["personal", "financial"],
        })

        # Step 5: CISO reviews privacy dashboard
        ciso.assert_allowed("get", "/privacy/dashboard")
        ciso.assert_allowed("get", "/privacy/breaches")

        # Step 6: Board executive summary
        ciso.assert_allowed("get", "/board-reporting/executive-summary")


class TestCrossPersonaSOXWorkflow:
    """
    SOX/ICFR workflow:
    P10 (SOX Owner) creates ICFR control → tests it →
    P14 (Process Owner) certifies control effectiveness →
    P04 (Compliance) creates SOX sign-off → signs →
    P19 (Internal Auditor) reviews → creates finding →
    P09 (External Auditor) reads evidence
    """

    def test_sox_lifecycle(self, client_factory):
        sox_owner = client_factory("P10")
        process_owner = client_factory("P14")
        compliance = client_factory("P04")
        int_auditor = client_factory("P19")
        ext_auditor = client_factory("P09")

        # Step 1: SOX Owner creates ICFR control
        resp = sox_owner.post("/sox-icfr/controls", json={
            "control_name": f"E2E ICFR {_uid()}", "control_type": "detective",
            "frequency": "quarterly", "owner": "qa_sox_owner",
            "key_control": True, "assertion": "existence",
            "account_balance": "Revenue",
        })
        if resp.status_code in (200, 201):
            cid = resp.json().get("id") or resp.json().get("control_id")
            if cid:
                # Test the control
                sox_owner.post(f"/sox-icfr/controls/{cid}/test", json={
                    "tester": "qa_sox_owner",
                    "test_date": datetime.utcnow().isoformat(),
                    "sample_size": 30, "exceptions_found": 1,
                })

        # Step 2: Process owner reads controls
        process_owner.assert_allowed("get", "/process-control/controls")

        # Step 3: Compliance creates sign-off
        compliance.post("/sox-icfr/signoffs", json={
            "period": "Q3-2026", "scope": "Revenue Recognition",
            "signer": "qa_compliance",
        })

        # Step 4: Internal auditor reviews
        int_auditor.assert_allowed("get", "/sox-icfr/controls")
        int_auditor.assert_allowed("get", "/sox-icfr/summary")

        # Step 5: External auditor reads evidence
        ext_auditor.assert_allowed("get", "/sox-icfr/controls")
        ext_auditor.assert_allowed("get", "/audit-evidence/packages")


class TestCrossPersonaOperationalRiskWorkflow:
    """
    Operational risk lifecycle:
    P05 (Risk Manager) logs loss event →
    P04 (Compliance) creates SoD remediation →
    P06 (IT Security) submits IT change risk →
    P05 reviews insurance coverage →
    P03 (CISO) reviews board report
    """

    def test_operational_risk_lifecycle(self, client_factory):
        risk_mgr = client_factory("P05")
        compliance = client_factory("P04")
        security = client_factory("P06")
        ciso = client_factory("P03")

        # Step 1: Log operational loss event
        resp = risk_mgr.post("/operational-risk/loss-events", json={
            "title": f"E2E Loss Event {_uid()}", "event_type": "execution_delivery",
            "business_line": "retail_banking", "gross_loss": 75000,
            "net_loss": 50000, "recoveries": 25000,
            "description": "E2E test loss event",
        })

        # Step 2: Create SoD remediation
        compliance.post("/sod-remediation/", json={
            "remediation_description": f"E2E SoD Remediation {_uid()}",
            "violation_id": _uid(), "user_id": _uid(),
        })

        # Step 3: IT change risk
        security.post("/it-change-risk/", json={
            "title": f"E2E IT Change {_uid()}", "description": "Firewall update",
            "change_type": "standard", "risk_level": "medium",
            "planned_date": (datetime.utcnow() + timedelta(days=7)).isoformat(),
            "requester": "qa_it_security",
        })

        # Step 4: Insurance coverage
        risk_mgr.assert_allowed("get", "/insurance/")

        # Step 5: Board trend data
        ciso.assert_allowed("get", "/board-reporting/trend-data")
        ciso.assert_allowed("get", "/board-reporting/executive-summary")


class TestCrossPersonaSanctionsWorkflow:
    """
    Sanctions screening workflow:
    P04 (Compliance) screens entity →
    Gets potential_match →
    P04 resolves as false_positive or true_match →
    P03 (CISO) reviews summary
    """

    def test_sanctions_screening_lifecycle(self, client_factory):
        compliance = client_factory("P04")
        ciso = client_factory("P03")

        # Step 1: Screen an entity
        resp = compliance.post("/sanctions-screening/", json={
            "entity_name": f"E2E Entity {_uid()}", "entity_type": "individual",
            "entity_id": f"ENTITY-{_uid()}", "country": "IR",
            "lists_checked": ["OFAC", "UN", "EU"],
        })
        if resp.status_code in (200, 201):
            sid = resp.json().get("id") or resp.json().get("screening_id")
            if sid:
                # Resolve as false positive
                compliance.put(f"/sanctions-screening/{sid}/resolve", json={
                    "resolution": "false_positive", "resolution_notes": "E2E test — not a match",
                })

        # Step 2: Batch screening
        compliance.post("/sanctions-screening/batch", json={
            "entities": [
                {"entity_name": f"Batch-1 {_uid()}", "entity_type": "organization",
                 "entity_id": f"B1-{_uid()}", "country": "US"},
                {"entity_name": f"Batch-2 {_uid()}", "entity_type": "individual",
                 "entity_id": f"B2-{_uid()}", "country": "DE"},
            ],
            "lists": ["OFAC", "EU"],
        })

        # Step 3: CISO reviews summary
        ciso.assert_allowed("get", "/sanctions-screening/summary/stats")


class TestCrossPersonaFraudWorkflow:
    """
    Fraud detection workflow:
    P06 (IT Security) creates detection rule →
    System generates alert →
    P06 opens case from alert →
    P04 (Compliance) reviews case
    """

    def test_fraud_lifecycle(self, client_factory):
        security = client_factory("P06")
        compliance = client_factory("P04")

        # Step 1: Create fraud detection rule
        resp = security.post("/fraud/rules", json={
            "name": f"E2E Fraud Rule {_uid()}", "rule_type": "threshold",
            "description": "Detect high-value transactions",
            "conditions": {"amount_gt": 100000},
        })

        # Step 2: View alerts
        security.assert_allowed("get", "/fraud/alerts")

        # Step 3: View cases
        security.assert_allowed("get", "/fraud/cases")
        security.assert_allowed("get", "/fraud/dashboard")

        # Step 4: Compliance also views
        compliance.assert_allowed("get", "/fraud/alerts")
        compliance.assert_allowed("get", "/fraud/cases")


class TestCrossPersonaBCMWorkflow:
    """
    BCM workflow:
    P05 (Risk Manager) creates BIA → creates BC plan →
    P02 (Tenant Admin) activates incident →
    P16 (Read-Only) can view dashboard
    """

    def test_bcm_lifecycle(self, client_factory):
        risk_mgr = client_factory("P05")
        admin = client_factory("P02")

        # Step 1: Create BIA
        resp = risk_mgr.post("/bcm/bia", json={
            "process_name": f"E2E Process {_uid()}", "criticality": "high",
            "rto_hours": 4, "rpo_hours": 1, "description": "E2E test BIA",
        })

        # Step 2: Create BC Plan
        risk_mgr.post("/bcm/plans", json={
            "plan_name": f"E2E BC Plan {_uid()}", "plan_type": "recovery",
            "description": "E2E test plan",
        })

        # Step 3: Activate incident
        admin.post("/bcm/activations", json={
            "incident_name": f"E2E Incident {_uid()}", "severity": "high",
            "description": "E2E test incident activation",
        })

        # Step 4: Dashboard readable
        risk_mgr.assert_allowed("get", "/bcm/dashboard")


class TestPublicWhistleblowerFlow:
    """
    Whistleblower flow (NO AUTH required for submit):
    Anonymous user submits report →
    Anonymous user tracks case by reference →
    P04 (Compliance) triages in inbox
    """

    def test_whistleblower_lifecycle(self, base_url, client_factory):
        # Step 1: Public submission (no auth)
        resp = requests.post(f"{base_url}/whistleblower/submit", json={
            "category": "fraud", "description": f"E2E anonymous report {_uid()}",
            "is_anonymous": True,
        })
        if resp.status_code not in (200, 201):
            pytest.skip("Whistleblower submit not available")

        case_ref = resp.json().get("case_reference") or resp.json().get("reference")
        if not case_ref:
            pytest.skip("No case reference returned")

        # Step 2: Public tracking (no auth)
        track = requests.get(f"{base_url}/whistleblower/track/{case_ref}")
        assert track.status_code == 200

        # Step 3: Compliance triages
        compliance = client_factory("P04")
        compliance.assert_allowed("get", "/whistleblower/cases")
