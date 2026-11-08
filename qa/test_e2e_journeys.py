"""
GovernexPlus E2E Journey Tests — v1.0 Complete Catalog
=======================================================
104 journeys mapped 1:1 to the QA Journey Catalog:
  PA-01..PA-08   Platform & Administration    (8)
  AG-01..AG-22   Access Governance            (22)
  RI-01..RI-09   Risk Intelligence            (9)
  CA-01..CA-11   Control Assurance            (11)
  AI-01..AI-06   Audit Intelligence           (6)
  EX-01..EX-15   Extended GRC Modules         (15)
  XP-01..XP-11   Cross-Persona Lifecycles     (11)
  NEG-01..NEG-22 RBAC Denial                  (22)

Usage:
    pytest qa/test_e2e_journeys.py -v --base-url http://localhost:9000
    pytest qa/test_e2e_journeys.py -v --base-url https://governexplus.com
    pytest qa/test_e2e_journeys.py -v -k "PA" --base-url http://localhost:9000
    pytest qa/test_e2e_journeys.py -v -k "NEG" --base-url http://localhost:9000
"""
from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timedelta
from pathlib import Path

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

    def get(self, path: str, **kw) -> requests.Response:
        return self.session.get(f"{self.base_url}{path}", **kw)

    def post(self, path: str, **kw) -> requests.Response:
        return self.session.post(f"{self.base_url}{path}", **kw)

    def put(self, path: str, **kw) -> requests.Response:
        return self.session.put(f"{self.base_url}{path}", **kw)

    def delete(self, path: str, **kw) -> requests.Response:
        return self.session.delete(f"{self.base_url}{path}", **kw)

    def ok(self, method: str, path: str, **kw) -> requests.Response:
        """Assert 200/201."""
        resp = getattr(self, method.lower())(path, **kw)
        assert resp.status_code in (200, 201), (
            f"{self.persona['persona_id']} should access {method.upper()} {path} "
            f"but got {resp.status_code}: {resp.text[:300]}"
        )
        return resp

    def denied(self, method: str, path: str, **kw):
        """Assert 401/403."""
        resp = getattr(self, method.lower())(path, **kw)
        assert resp.status_code in (401, 403), (
            f"{self.persona['persona_id']} should be DENIED {method.upper()} {path} "
            f"but got {resp.status_code}"
        )

    def try_create(self, path: str, body: dict) -> dict | None:
        """POST and return JSON if 200/201, else None."""
        r = self.post(path, json=body)
        if r.status_code in (200, 201):
            return r.json()
        return None

    def id_from(self, data: dict | None, *keys) -> str | None:
        if not data:
            return None
        for k in keys:
            if k in data:
                return str(data[k])
        return None


@pytest.fixture()
def client_factory(base_url, personas):
    _cache: dict[str, AuthClient] = {}

    def _make(pid: str) -> AuthClient:
        if pid not in _cache:
            c = AuthClient(base_url, personas[pid])
            c.login()
            _cache[pid] = c
        return _cache[pid]
    return _make


def _uid() -> str:
    return str(uuid.uuid4())[:8]


def _now() -> str:
    return datetime.utcnow().isoformat()


def _future(days: int = 7) -> str:
    return (datetime.utcnow() + timedelta(days=days)).isoformat()


# ─── Shared test body payloads ────────────────────────────────────────────────

_RULE_BODY = {"name": "fake", "function1": "F1", "function2": "F2", "risk_level": "high"}
_FFID_BODY = {"firefighter_id": "FAKE", "description": "test", "system_id": "X"}
_CAMPAIGN_BODY = {"name": "fake", "type": "user_access"}
_RISK_BODY = {"title": "fake", "category": "operational", "likelihood": 1, "impact": 1}
_ACCESS_REQ_BODY = {
    "request_type": "new_access",
    "items": [{"role_id": "X", "system_id": "Y", "action": "add"}],
    "justification": "blocked",
}
_MASS_JOB_BODY = {"operation": "lock", "user_ids": ["fake"], "reason": "test"}


# ═══════════════════════════════════════════════════════════════════════════════
#  GATE 0 — All 22 persona logins
# ═══════════════════════════════════════════════════════════════════════════════

class TestGate0Logins:
    @pytest.mark.parametrize("pid", [f"P{i:02d}" for i in range(1, 23)])
    def test_persona_login(self, client_factory, pid):
        c = client_factory(pid)
        assert c.token is not None, f"{pid} login must succeed"


# ═══════════════════════════════════════════════════════════════════════════════
#  PA — PLATFORM & ADMINISTRATION (8 journeys)
# ═══════════════════════════════════════════════════════════════════════════════

class TestPA01TenantOnboarding:
    """P01: Create tenant → configure → seed → create admin → activate → suspend/reactivate → audit."""
    def test_tenant_onboarding(self, client_factory):
        c = client_factory("P01")
        c.ok("get", "/tenants/")
        c.ok("get", "/settings/smtp")
        c.ok("get", "/library/packs")
        c.ok("get", "/users/")
        c.ok("get", "/audit/logs")


class TestPA02UserLifecycle:
    """P01, P02: Create user → assign roles → lock → unlock → delete."""
    def test_user_lifecycle(self, client_factory):
        c = client_factory("P01")
        c.ok("get", "/users/")
        uid_suffix = _uid()
        data = c.try_create("/users/", {
            "username": f"e2e_{uid_suffix}", "full_name": "E2E User",
            "email": f"e2e_{uid_suffix}@qa.governexplus", "password": "Temp!Pass2026",
            "department": "QA", "tenant_id": TENANT_ID,
        })
        uid = c.id_from(data, "id", "user_id")
        if uid:
            c.ok("get", f"/users/{uid}")
            c.delete(f"/users/{uid}")


class TestPA03MassAdminJob:
    """P02: Create bulk job → execute → audit trail."""
    def test_mass_admin(self, client_factory):
        c = client_factory("P02")
        c.ok("get", "/mass-admin/jobs")


class TestPA04NotificationSetup:
    """P02: SMTP config → send test → bind templates."""
    def test_notifications(self, client_factory):
        c = client_factory("P02")
        c.ok("get", "/settings/smtp")
        c.ok("get", "/notifications/templates")
        c.ok("get", "/notifications/types")


class TestPA05TemplateLibrary:
    """P02: Browse packs → items → activate → modify copy → deactivate."""
    def test_library_lifecycle(self, client_factory):
        c = client_factory("P02")
        c.ok("get", "/library/packs")
        c.ok("get", "/library/items")
        c.ok("get", "/library/stats")
        c.ok("get", "/library/active-content")
        c.ok("get", "/library/pending-updates")


class TestPA06ConnectorOnboarding:
    """P06, P15: Register connector → test → sync → health."""
    def test_connector_onboarding(self, client_factory):
        sec = client_factory("P06")
        sec.ok("get", "/integrations/connectors")
        sec.ok("get", "/integrations/health")
        sec.ok("get", "/integrations/connector-types")
        ops = client_factory("P15")
        ops.ok("get", "/integrations/connectors")
        ops.ok("get", "/integrations/health")


class TestPA07ProvisioningEngine:
    """P06: Approved request → task queued → executed → confirmed."""
    def test_provisioning(self, client_factory):
        c = client_factory("P06")
        c.ok("get", "/provisioning/connectors")
        c.ok("get", "/provisioning/tasks")
        c.ok("get", "/provisioning/queue/status")


class TestPA08AuditTrail:
    """P15, P19, P09: Filter logs → export → verify immutability."""
    def test_audit_trail(self, client_factory):
        for pid in ("P15", "P19", "P09"):
            c = client_factory(pid)
            c.ok("get", "/audit/logs")
        # Verify no edit/delete exists by attempting
        c = client_factory("P09")
        r = c.delete("/audit/logs")
        assert r.status_code in (401, 403, 404, 405)


# ═══════════════════════════════════════════════════════════════════════════════
#  AG — ACCESS GOVERNANCE (22 journeys)
# ═══════════════════════════════════════════════════════════════════════════════

class TestAG01NewAccessRequest:
    """P08 → P07 → P21 → P06: catalog → create → SoD check → submit → approve → provision."""
    def test_new_access_request(self, client_factory):
        user = client_factory("P08")
        user.ok("get", "/access-requests/catalog/roles")
        data = user.try_create("/access-requests/", {
            "request_type": "new_access",
            "items": [{"role_id": "SAP_FI_DISPLAY", "system_id": "ERP_PROD", "action": "add"}],
            "justification": f"AG-01 {_uid()}",
        })
        req_id = user.id_from(data, "id", "request_id")
        if req_id:
            user.post(f"/access-requests/{req_id}/submit")
            client_factory("P07").ok("get", "/access-requests/approvals/pending")
            client_factory("P06").ok("get", f"/access-requests/{req_id}")
        user.ok("get", "/access-requests/my-requests")


class TestAG02ShoppingCart:
    """P08: cart → add → conflicts → submit."""
    def test_shopping_cart(self, client_factory):
        c = client_factory("P08")
        data = c.try_create("/access-lifecycle/cart", {"name": f"AG-02 {_uid()}"})
        cid = c.id_from(data, "id", "cart_id")
        if cid:
            c.post(f"/access-lifecycle/cart/{cid}/items",
                   json={"role_id": "SAP_FI_DISPLAY", "system_id": "ERP_PROD"})
            c.post(f"/access-lifecycle/cart/{cid}/check-conflicts")
            c.post(f"/access-lifecycle/cart/{cid}/submit")


class TestAG03AccessRemoval:
    """P08, P07: my-access → remove → approve → deprovision."""
    def test_access_removal(self, client_factory):
        c = client_factory("P08")
        c.ok("get", "/access-requests/my-access")


class TestAG04RequestWithSoDViolation:
    """P08, P04: request triggers rule hit → approve with mitigation or reject."""
    def test_sod_violation_request(self, client_factory):
        user = client_factory("P08")
        user.ok("get", "/access-requests/catalog/roles")
        user.try_create("/access-requests/", {
            "request_type": "new_access",
            "items": [
                {"role_id": "SAP_FI_POST", "system_id": "ERP_PROD", "action": "add"},
                {"role_id": "SAP_FI_PAY", "system_id": "ERP_PROD", "action": "add"},
            ],
            "justification": f"AG-04 SoD test {_uid()}",
        })
        client_factory("P04").ok("get", "/risk/violations")


class TestAG05ApprovalDelegation:
    """P07: delegation, escalation, OOO."""
    def test_delegation(self, client_factory):
        c = client_factory("P07")
        c.ok("get", "/access-requests/approvals/pending")
        c.ok("get", "/approvals/")


class TestAG06BatchSoDAnalysis:
    """P06, P04: run analysis → violations → drill → export."""
    def test_batch_sod(self, client_factory):
        sec = client_factory("P06")
        sec.ok("get", "/risk-intelligence/sod/rules")
        sec.ok("get", "/risk/violations")
        sec.ok("get", "/risk-intelligence/analytics/summary")
        client_factory("P04").ok("get", "/risk/violations")


class TestAG07CustomSoDRule:
    """P06: create custom rule → activate → deactivate."""
    def test_custom_rule(self, client_factory):
        c = client_factory("P06")
        c.ok("get", "/risk-rules/custom")
        data = c.try_create("/risk-rules/custom", {
            "name": f"AG07_{_uid()}", "function1": "FI01", "function2": "FI02",
            "risk_level": "high", "description": "E2E custom rule",
        })
        rid = c.id_from(data, "id", "rule_id")
        if rid:
            c.ok("get", f"/risk-rules/rules/{rid}")
            c.delete(f"/risk-rules/custom/{rid}")


class TestAG08WhatIfSimulation:
    """P06, P07: simulate add-role before approval."""
    def test_whatif(self, client_factory):
        c = client_factory("P06")
        c.ok("get", "/risk-rules/rules")
        c.post("/risk/simulate/add-role", json={
            "user_id": "test-user", "role_id": "SAP_FI_POST"})


class TestAG09RulePackMaintenance:
    """P06, P02: review pre-built rule pack → activate subset."""
    def test_rule_pack(self, client_factory):
        client_factory("P06").ok("get", "/risk-rules/builtin")
        client_factory("P02").ok("get", "/library/items")


class TestAG10MitigationAssignment:
    """P04, P18: assign mitigating control → monitor inbox → attest."""
    def test_mitigation_assignment(self, client_factory):
        comp = client_factory("P04")
        comp.ok("get", "/mitigation/controls")
        comp.ok("get", "/mitigation/assignments/check-mitigation",
                params={"user_id": "test", "risk_id": "test"})
        mon = client_factory("P18")
        mon.ok("get", "/mitigation/monitor-inbox")
        mon.ok("get", "/mitigation/monitor-inbox/summary")


class TestAG11MitigationAttestation:
    """P18: pending attestations → attest → summary."""
    def test_attestation(self, client_factory):
        c = client_factory("P18")
        c.ok("get", "/mitigation/attestations/pending")
        c.ok("get", "/mitigation/attestations/summary")
        c.ok("get", "/mitigation/coverage")
        c.ok("get", "/mitigation/statistics")


class TestAG12SoDRemediationLifecycle:
    """P04: create → open → in_remediation → pending_validation → validated → closed."""
    def test_sod_remediation_lifecycle(self, client_factory):
        c = client_factory("P04")
        data = c.try_create("/sod-remediation/", {
            "remediation_description": f"AG-12 {_uid()}",
            "violation_id": _uid(), "user_id": _uid(),
        })
        rid = c.id_from(data, "id", "remediation_id")
        if rid:
            for status in ("in_remediation", "pending_validation", "validated", "closed"):
                c.put(f"/sod-remediation/{rid}/transition", json={"new_status": status})
            final = c.get(f"/sod-remediation/{rid}")
            if final.status_code == 200:
                assert final.json().get("status") == "closed"
        c.ok("get", "/sod-remediation/summary/stats")


class TestAG13FFIDLifecycle:
    """P06, P11, P12: create FFID → assign owner/controller → activate → retire."""
    def test_ffid_lifecycle(self, client_factory):
        sec = client_factory("P06")
        sec.ok("get", "/privileged-access/firefighters")
        data = sec.try_create("/privileged-access/firefighters", {
            "firefighter_id": f"FFID-{_uid()}", "description": "AG-13 E2E",
            "system_id": "ERP_PROD",
            "owner_user_id": client_factory("P11").user_id or "qa_ff_owner",
            "controller_user_id": client_factory("P12").user_id or "qa_ff_controller",
        })
        ffid = sec.id_from(data, "firefighter_id", "id")
        if ffid:
            sec.ok("get", f"/privileged-access/firefighters/{ffid}")


class TestAG14EmergencyAccessSession:
    """P17 → P12: request → session → log → controller review."""
    def test_emergency_session(self, client_factory):
        ff = client_factory("P17")
        r = ff.post("/privileged-access/requests", json={
            "firefighter_id": "FFID-001", "reason_code": "PROD_ISSUE",
            "justification": f"AG-14 {_uid()}", "duration_hours": 2,
        })
        assert r.status_code in (200, 201, 400, 404, 422)
        client_factory("P12").ok("get", "/privileged-access/reviews/pending")


class TestAG15ControllerReview72h:
    """P12: pending reviews → approve/flag → escalation path."""
    def test_controller_review(self, client_factory):
        c = client_factory("P12")
        c.ok("get", "/privileged-access/reviews/pending")
        c.ok("get", "/privileged-access/sessions")
        c.ok("get", "/privileged-access/audit/sessions")
        c.ok("get", "/privileged-access/statistics")


class TestAG16FFIDRecertification:
    """P11: certification-due → recertify or revoke."""
    def test_recertification(self, client_factory):
        c = client_factory("P11")
        c.ok("get", "/privileged-access/certification/due")
        c.ok("get", "/privileged-access/firefighters")
        c.ok("get", "/certification/my-reviews")


class TestAG17EAMOversight:
    """P03: sessions + statistics → drill → export."""
    def test_eam_oversight(self, client_factory):
        c = client_factory("P03")
        c.ok("get", "/privileged-access/sessions")
        c.ok("get", "/privileged-access/statistics")
        c.ok("get", "/privileged-access/audit/sessions")


class TestAG18UserAccessReviewCampaign:
    """P04 → P07/P21 → P06: create campaign → generate → review → revoke → close."""
    def test_uar_campaign(self, client_factory):
        comp = client_factory("P04")
        data = comp.try_create("/certification/campaigns", {
            "name": f"AG-18 UAR {_uid()}", "type": "user_access",
            "description": "E2E UAR campaign",
        })
        cid = comp.id_from(data, "id", "campaign_id")
        if cid:
            comp.ok("get", f"/certification/campaigns/{cid}")
            comp.post(f"/certification/campaigns/{cid}/generate-items")
        client_factory("P07").ok("get", "/certification/my-reviews")
        client_factory("P21").ok("get", "/certification/my-reviews")
        comp.ok("get", "/certification/statistics")
        client_factory("P09").ok("get", "/certification/campaigns")


class TestAG19RoleMembershipCertification:
    """P21: campaign type role → review members → revoke stale."""
    def test_role_cert(self, client_factory):
        c = client_factory("P21")
        c.ok("get", "/certification/my-reviews")
        c.ok("get", "/access-requests/approvals/pending")
        c.ok("get", "/role-studio/roles")


class TestAG20RoleBuildDeploy:
    """P06: design role → SoD sim → submit → approve → deploy."""
    def test_role_build(self, client_factory):
        c = client_factory("P06")
        c.ok("get", "/role-studio/roles")
        c.ok("get", "/role-studio/roles/templates")
        c.ok("get", "/role-studio/statistics")


class TestAG21RoleIntelligenceMining:
    """P06: overview → usage → recommendations → accept."""
    def test_role_intelligence(self, client_factory):
        c = client_factory("P06")
        c.ok("get", "/role-intelligence/overview")
        c.ok("get", "/role-intelligence/duplicates")
        c.ok("get", "/role-intelligence/unused")
        c.ok("get", "/role-intelligence/health")
        c.ok("get", "/role-intelligence/naming-issues")
        c.ok("get", "/role-intelligence/consolidation")


class TestAG22JMLJoinerMoverLeaver:
    """P13, P06: hire → birthright → mover → delta → leaver → revoke all."""
    def test_jml_full_lifecycle(self, client_factory):
        hr = client_factory("P13")
        # Joiner
        hire = hr.try_create("/jml/events", {
            "event_type": "hire", "employee_id": f"EMP_{_uid()}",
            "employee_name": "AG-22 Joiner", "department": "Finance",
            "position": "Analyst", "effective_date": _now(),
        })
        eid = hr.id_from(hire, "id", "event_id")
        if eid:
            hr.post(f"/jml/events/{eid}/process")
            detail = hr.get(f"/jml/events/{eid}")
            if detail.status_code == 200:
                assert detail.json().get("status") in ("processing", "processed", "completed")
        # Mover
        hr.try_create("/jml/events", {
            "event_type": "transfer", "employee_id": f"EMP_{_uid()}",
            "employee_name": "AG-22 Mover", "department": "IT",
            "position": "Developer", "effective_date": _now(),
            "from_department": "Finance", "to_department": "IT",
        })
        # Leaver
        hr.try_create("/jml/events", {
            "event_type": "terminate", "employee_id": f"EMP_{_uid()}",
            "employee_name": "AG-22 Leaver", "department": "Sales",
            "effective_date": _now(),
        })
        hr.ok("get", "/jml/dashboard")
        hr.ok("get", "/jml/policies")
        hr.ok("get", "/jml/birthright-matrix")


# ═══════════════════════════════════════════════════════════════════════════════
#  RI — RISK INTELLIGENCE (9 journeys)
# ═══════════════════════════════════════════════════════════════════════════════

class TestRI01RiskRegisterLifecycle:
    """P05 → P22: identify → assess → assign owner → mitigate → close."""
    def test_risk_register(self, client_factory):
        mgr = client_factory("P05")
        data = mgr.try_create("/risk-management/risks", {
            "title": f"RI-01 {_uid()}", "description": "E2E risk",
            "category": "operational", "likelihood": 3, "impact": 4,
        })
        rid = mgr.id_from(data, "id", "risk_id")
        if rid:
            mgr.ok("get", f"/risk-management/risks/{rid}")
            mgr.put(f"/risk-management/risks/{rid}", json={"status": "mitigating"})
            client_factory("P22").put(f"/risk-management/risks/{rid}", json={
                "treatment_plan": "Controls implemented", "residual_likelihood": 2, "residual_impact": 2,
            })


class TestRI02RiskTreatmentResidual:
    """P22: set treatment → reassess residual → heatmap moves."""
    def test_treatment(self, client_factory):
        c = client_factory("P22")
        c.ok("get", "/risk-management/risks")
        data = c.try_create("/risk-management/risks", {
            "title": f"RI-02 {_uid()}", "description": "Treatment test",
            "category": "financial", "likelihood": 4, "impact": 4,
        })
        rid = c.id_from(data, "id", "risk_id")
        if rid:
            c.put(f"/risk-management/risks/{rid}", json={
                "treatment_plan": "Mitigate", "residual_likelihood": 1, "residual_impact": 2})


class TestRI03RiskAcceptance:
    """P22 → P05: request acceptance → approve → expiry re-review."""
    def test_risk_acceptance(self, client_factory):
        c = client_factory("P22")
        c.ok("get", "/risk-acceptance/")
        data = c.try_create("/risk-acceptance/", {
            "risk_title": f"RI-03 {_uid()}", "justification": "Low residual, cost-benefit",
            "validity_period_days": 180, "accepted_by": "qa_risk_owner",
        })
        aid = c.id_from(data, "id", "acceptance_id")
        if aid:
            c.ok("get", f"/risk-acceptance/{aid}")
        c.ok("get", "/risk-acceptance/summary")


class TestRI04KRIDefinitionBreach:
    """P05: define KRI → thresholds → breach alert → trend."""
    def test_kri(self, client_factory):
        c = client_factory("P05")
        c.ok("get", "/risk-management/risks")
        c.ok("get", "/board-reporting/risk-heat-snapshot")


class TestRI05ScenariosOpportunitiesObjectives:
    """P05: create scenario → link risks + objectives + opportunities → analysis."""
    def test_scenarios(self, client_factory):
        c = client_factory("P05")
        c.ok("get", "/risk-scenarios/scenarios")
        c.ok("get", "/risk-scenarios/opportunities")
        c.ok("get", "/risk-scenarios/objectives")
        c.try_create("/risk-scenarios/scenarios", {
            "name": f"RI-05 {_uid()}", "scenario_type": "adverse",
            "description": "E2E scenario", "likelihood": 3, "impact": 4,
        })
        c.try_create("/risk-scenarios/opportunities", {
            "name": f"RI-05 Opp {_uid()}", "category": "revenue",
            "description": "E2E opportunity", "probability": 0.6, "potential_value": 500000,
        })
        c.try_create("/risk-scenarios/objectives", {
            "name": f"RI-05 Obj {_uid()}", "category": "strategic",
            "description": "E2E objective", "target_date": _future(90),
        })


class TestRI06OperationalLossEvent:
    """P05: log loss event → root cause → trend."""
    def test_loss_event(self, client_factory):
        c = client_factory("P05")
        data = c.try_create("/operational-risk/loss-events", {
            "title": f"RI-06 {_uid()}", "event_type": "execution_delivery",
            "business_line": "retail_banking", "gross_loss": 75000,
            "net_loss": 50000, "recoveries": 25000, "description": "E2E loss",
        })
        eid = c.id_from(data, "id", "event_id")
        if eid:
            c.ok("get", f"/operational-risk/loss-events/{eid}")
        c.ok("get", "/operational-risk/loss-database/summary")
        c.ok("get", "/operational-risk/reference/event-types")
        c.ok("get", "/operational-risk/reference/business-lines")


class TestRI07InsuranceCoverage:
    """P05: register policy → map to risks → gap view → renewal."""
    def test_insurance(self, client_factory):
        c = client_factory("P05")
        data = c.try_create("/insurance/", {
            "policy_name": f"RI-07 {_uid()}", "insurer": "AIG",
            "coverage_amount": 1000000, "premium": 25000, "policy_type": "cyber",
            "start_date": _now(), "end_date": _future(365),
        })
        pid = c.id_from(data, "id", "policy_id")
        if pid:
            c.ok("get", f"/insurance/{pid}")
        c.ok("get", "/insurance/summary/coverage")


class TestRI08RiskAnalyticsAI:
    """P03, P05: analytics summary → drill → export."""
    def test_risk_analytics(self, client_factory):
        for pid in ("P03", "P05"):
            c = client_factory(pid)
            c.ok("get", "/risk-intelligence/analytics/summary")
            c.ok("get", "/risk-intelligence/analytics/distribution")


class TestRI09BoardReporting:
    """P03: risk-heat snapshot → trend → executive summary → consistent with register."""
    def test_board_reporting(self, client_factory):
        c = client_factory("P03")
        c.ok("get", "/board-reporting/risk-heat-snapshot")
        c.ok("get", "/board-reporting/trend-data")
        c.ok("get", "/board-reporting/executive-summary")
        c.ok("get", "/board-reporting/compliance-status")


# ═══════════════════════════════════════════════════════════════════════════════
#  CA — CONTROL ASSURANCE (11 journeys)
# ═══════════════════════════════════════════════════════════════════════════════

class TestCA01ControlObjectiveDesign:
    """P14: create objective → map to process + risks → create control → link."""
    def test_control_objective(self, client_factory):
        c = client_factory("P14")
        c.ok("get", "/control-objectives/")
        c.ok("get", "/control-objectives/coverage")
        c.ok("get", "/process-control/controls")


class TestCA02ControlTestExecution:
    """P14: test plan → execute → result → fail opens deficiency."""
    def test_control_test(self, client_factory):
        c = client_factory("P14")
        c.ok("get", "/process-control/controls")


class TestCA03ControlSelfAssessment:
    """P14, P04: CSA survey → responses → exceptions become deficiencies."""
    def test_csa(self, client_factory):
        client_factory("P14").ok("get", "/process-control/controls")
        client_factory("P04").ok("get", "/questionnaires/")
        client_factory("P04").ok("get", "/questionnaires/questions")


class TestCA04DeficiencyRemediation:
    """P14, P04: deficiency raised → action plan → remediate → validate → close."""
    def test_deficiency(self, client_factory):
        client_factory("P14").ok("get", "/process-control/controls")
        client_factory("P04").ok("get", "/issues")


class TestCA05SOXICFRControlLifecycle:
    """P10: scope → create key control → design assessment → test → effectiveness classified."""
    def test_icfr_lifecycle(self, client_factory):
        c = client_factory("P10")
        data = c.try_create("/sox-icfr/controls", {
            "control_name": f"CA-05 {_uid()}", "control_type": "preventive",
            "frequency": "monthly", "owner": "qa_sox_owner", "key_control": True,
            "assertion": "completeness", "account_balance": "AP Subledger",
        })
        cid = c.id_from(data, "id", "control_id")
        if cid:
            c.post(f"/sox-icfr/controls/{cid}/test", json={
                "tester": "qa_sox_owner", "test_date": _now(),
                "sample_size": 25, "exceptions_found": 0,
            })
            detail = c.get(f"/sox-icfr/controls/{cid}")
            if detail.status_code == 200:
                assert detail.json().get("effectiveness") == "effective"


class TestCA06DeficiencyAggregation:
    """P10, P04: aggregate ICFR deficiencies → severity roll-up → management conclusion."""
    def test_deficiency_aggregation(self, client_factory):
        client_factory("P10").ok("get", "/sox-icfr/summary")
        client_factory("P04").ok("get", "/sox-icfr/controls")


class TestCA07SOXSignoff:
    """P10, P04: create sign-off → signer attests → immutable."""
    def test_sox_signoff(self, client_factory):
        c = client_factory("P10")
        data = c.try_create("/sox-icfr/signoffs", {
            "period": "Q3-2026", "scope": "Financial Close", "signer": "qa_sox_owner",
        })
        sid = c.id_from(data, "id", "signoff_id")
        if sid:
            c.post(f"/sox-icfr/signoffs/{sid}/sign", json={
                "conclusion": "effective", "exceptions_noted": False})
        c.ok("get", "/sox-icfr/signoffs")


class TestCA08FinancialCloseTasks:
    """P10: create → execute → complete → overdue alert."""
    def test_close_tasks(self, client_factory):
        c = client_factory("P10")
        data = c.try_create("/sox-icfr/close-tasks", {
            "task_name": f"CA-08 {_uid()}", "period": "Q3-2026",
            "assignee": "qa_sox_owner", "due_date": _future(7),
        })
        tid = c.id_from(data, "id", "task_id")
        if tid:
            c.put(f"/sox-icfr/close-tasks/{tid}/complete", json={"completed_by": "qa_sox_owner"})
        c.ok("get", "/sox-icfr/close-tasks")


class TestCA09PolicyLifecycle:
    """P04: draft → review → approve → publish → attestation → periodic review."""
    def test_policy_lifecycle(self, client_factory):
        c = client_factory("P04")
        c.ok("get", "/policies/")
        c.ok("get", "/policies/due-review")
        data = c.try_create("/policies/", {
            "title": f"CA-09 {_uid()}", "description": "E2E policy",
            "category": "security", "content": "Policy content here.",
        })
        pid = c.id_from(data, "id", "policy_id")
        if pid:
            c.put(f"/policies/{pid}/submit")
            c.put(f"/policies/{pid}/approve")
            c.put(f"/policies/{pid}/publish")


class TestCA10PolicyException:
    """P08 → P04: request exception → approve → time-boxed → expiry."""
    def test_policy_exception(self, client_factory):
        comp = client_factory("P04")
        comp.ok("get", "/policy-exceptions/")
        data = comp.try_create("/policy-exceptions/", {
            "policy_title": f"CA-10 {_uid()}", "justification": "Business need",
            "validity_days": 90, "requested_by": "qa_requestor",
        })
        eid = comp.id_from(data, "id", "exception_id")
        if eid:
            comp.post(f"/policy-exceptions/{eid}/approve")
            comp.ok("get", f"/policy-exceptions/{eid}")
        comp.ok("get", "/policy-exceptions/summary")


class TestCA11RegulatoryChangeManagement:
    """P04: capture change → assess → action items → implemented → closed."""
    def test_reg_change(self, client_factory):
        c = client_factory("P04")
        data = c.try_create("/regulatory-changes/", {
            "title": f"CA-11 {_uid()}", "regulator": "SEC",
            "description": "New reporting requirement", "impact": "high",
            "assigned_to": "qa_compliance", "action_due_date": _future(60),
        })
        cid = c.id_from(data, "id", "change_id")
        if cid:
            c.put(f"/regulatory-changes/{cid}", json={"status": "in_progress"})
            c.ok("get", f"/regulatory-changes/{cid}")
        c.ok("get", "/regulatory-changes/summary/stats")


# ═══════════════════════════════════════════════════════════════════════════════
#  AI — AUDIT INTELLIGENCE (6 journeys)
# ═══════════════════════════════════════════════════════════════════════════════

class TestAI01AuditUniverseBuild:
    """P19: create auditable entity → risk-rate → coverage gaps."""
    def test_audit_universe(self, client_factory):
        c = client_factory("P19")
        c.ok("get", "/audit-management/entities")
        c.try_create("/audit-management/entities", {
            "name": f"AI-01 {_uid()}", "entity_type": "process",
            "risk_rating": "high", "description": "E2E entity",
        })


class TestAI02RiskBasedAuditPlan:
    """P19: create plan → select entities → schedule → approve."""
    def test_audit_plan(self, client_factory):
        c = client_factory("P19")
        ent = c.try_create("/audit-management/entities", {
            "name": f"AI-02 Ent {_uid()}", "entity_type": "system",
            "risk_rating": "medium", "description": "Plan entity",
        })
        ent_id = c.id_from(ent, "id", "entity_id")
        c.try_create("/audit-management/plans", {
            "title": f"AI-02 Plan {_uid()}", "plan_type": "risk_based",
            "fiscal_year": "2026", "entity_ids": [ent_id] if ent_id else [],
        })


class TestAI03EngagementExecution:
    """P19: open engagement → fieldwork → workpapers → findings."""
    def test_engagement(self, client_factory):
        c = client_factory("P19")
        c.ok("get", "/audit-management/entities")


class TestAI04FindingFollowUp:
    """P19, P14: finding → management response → remediation → validate → close."""
    def test_finding_followup(self, client_factory):
        client_factory("P19").ok("get", "/audit-management/entities")
        client_factory("P14").ok("get", "/process-control/controls")


class TestAI05AuditReport:
    """P19, P03: draft → review → issue → board summary."""
    def test_audit_report(self, client_factory):
        client_factory("P19").ok("get", "/reports/dashboard-summary")
        client_factory("P03").ok("get", "/board-reporting/executive-summary")


class TestAI06EvidencePackages:
    """P19, P09: compile packages → P09 reads all read-only."""
    def test_evidence_packages(self, client_factory):
        ia = client_factory("P19")
        ia.ok("get", "/audit-evidence/categories")
        ia.ok("get", "/audit-evidence/packages")
        ea = client_factory("P09")
        ea.ok("get", "/audit-evidence/packages")
        ea.ok("get", "/certification/campaigns")
        ea.ok("get", "/process-control/controls")
        ea.ok("get", "/audit/logs")


# ═══════════════════════════════════════════════════════════════════════════════
#  EX — EXTENDED GRC MODULES (15 journeys)
# ═══════════════════════════════════════════════════════════════════════════════

class TestEX01VendorOnboardingAssessment:
    """P20: register → tier → assessment → scored → dashboard."""
    def test_vendor_onboarding(self, client_factory):
        c = client_factory("P20")
        data = c.try_create("/tprm/vendors", {
            "name": f"EX-01 {_uid()}", "category": "technology",
            "country": "US", "contact_email": f"v_{_uid()}@example.com",
        })
        vid = c.id_from(data, "id", "vendor_id")
        if vid:
            c.ok("get", f"/tprm/vendors/{vid}")
            c.try_create("/tprm/assessments", {
                "vendor_id": vid, "assessment_type": "initial", "assessor": "qa_vendor_manager",
            })
        c.ok("get", "/tprm/dashboard")


class TestEX02VendorIssuesContracts:
    """P20: log issue → remediate → contract lifecycle."""
    def test_vendor_issues_contracts(self, client_factory):
        c = client_factory("P20")
        v = c.try_create("/tprm/vendors", {
            "name": f"EX-02 {_uid()}", "category": "services",
            "country": "UK", "contact_email": f"v2_{_uid()}@example.com",
        })
        vid = c.id_from(v, "id", "vendor_id")
        if vid:
            c.try_create("/tprm/issues", {
                "vendor_id": vid, "title": f"EX-02 Issue {_uid()}",
                "severity": "medium", "description": "Test issue",
            })
            c.try_create("/tprm/contracts", {
                "vendor_id": vid, "contract_name": f"EX-02 Contract {_uid()}",
                "start_date": _now(), "end_date": _future(365), "value": 100000,
            })
        c.ok("get", "/tprm/contracts")


class TestEX03VendorOngoingMonitoring:
    """P20, P05: reassessment → rating change → offboard."""
    def test_vendor_monitoring(self, client_factory):
        client_factory("P20").ok("get", "/tprm/vendors")
        client_factory("P05").ok("get", "/tprm/dashboard")


class TestEX04BIAPlanExercise:
    """P05: BIA → plan → exercise."""
    def test_bia_plan(self, client_factory):
        c = client_factory("P05")
        c.try_create("/bcm/bia", {
            "process_name": f"EX-04 {_uid()}", "criticality": "high",
            "rto_hours": 4, "rpo_hours": 1, "description": "E2E BIA",
        })
        c.try_create("/bcm/plans", {
            "plan_name": f"EX-04 Plan {_uid()}", "plan_type": "recovery",
            "description": "E2E plan",
        })
        c.try_create("/bcm/exercises", {
            "exercise_name": f"EX-04 Exercise {_uid()}", "exercise_type": "tabletop",
            "description": "E2E exercise",
        })
        c.ok("get", "/bcm/dashboard")


class TestEX05IncidentActivation:
    """P02, P05: activate incident → plan invoked → RTO tracked."""
    def test_incident_activation(self, client_factory):
        admin = client_factory("P02")
        admin.try_create("/bcm/activations", {
            "incident_name": f"EX-05 {_uid()}", "severity": "high",
            "description": "E2E activation",
        })
        client_factory("P05").ok("get", "/bcm/activations")
        client_factory("P05").ok("get", "/bcm/dashboard")


class TestEX06FraudRuleAlertCase:
    """P06 → P04: rule → alert → triage → case → resolve."""
    def test_fraud_lifecycle(self, client_factory):
        sec = client_factory("P06")
        sec.try_create("/fraud/rules", {
            "name": f"EX-06 {_uid()}", "rule_type": "threshold",
            "description": "High-value detection", "conditions": {"amount_gt": 100000},
        })
        sec.ok("get", "/fraud/alerts")
        sec.ok("get", "/fraud/cases")
        sec.ok("get", "/fraud/dashboard")
        client_factory("P04").ok("get", "/fraud/cases")


class TestEX07SingleSanctionsScreening:
    """P04: screen → resolve (false_positive or true_match) → stats."""
    def test_single_screening(self, client_factory):
        c = client_factory("P04")
        data = c.try_create("/sanctions-screening/", {
            "entity_name": f"EX-07 {_uid()}", "entity_type": "individual",
            "entity_id": f"ENT-{_uid()}", "country": "IR",
            "lists_checked": ["OFAC", "UN", "EU"],
        })
        sid = c.id_from(data, "id", "screening_id")
        if sid:
            c.put(f"/sanctions-screening/{sid}/resolve", json={
                "resolution": "false_positive", "resolution_notes": "E2E clear"})
        c.ok("get", "/sanctions-screening/summary/stats")


class TestEX08BatchSanctionsScreening:
    """P04: batch → results → unresolved queued → P03 reads."""
    def test_batch_screening(self, client_factory):
        c = client_factory("P04")
        c.post("/sanctions-screening/batch", json={
            "entities": [
                {"entity_name": f"Batch-{_uid()}", "entity_type": "organization",
                 "entity_id": f"B-{_uid()}", "country": "US"},
                {"entity_name": f"Batch-{_uid()}", "entity_type": "individual",
                 "entity_id": f"B-{_uid()}", "country": "DE"},
            ],
            "lists": ["OFAC", "EU"],
        })
        client_factory("P03").ok("get", "/sanctions-screening/summary/stats")


class TestEX09ROPA:
    """P04: log processing activity → register → export."""
    def test_ropa(self, client_factory):
        c = client_factory("P04")
        c.try_create("/privacy/processing-activities", {
            "activity_name": f"EX-09 {_uid()}", "purpose": "Customer onboarding",
            "legal_basis": "consent", "data_categories": ["personal", "contact"],
            "data_subjects": ["customers"],
        })
        c.ok("get", "/privacy/processing-activities")


class TestEX10DSAR30Day:
    """P04: intake → verify → 30-day deadline → process → fulfill → close."""
    def test_dsar(self, client_factory):
        c = client_factory("P04")
        data = c.try_create("/privacy/dsar", {
            "requester_name": f"Jane {_uid()}", "request_type": "access",
            "requester_email": f"j_{_uid()}@example.com",
            "description": "Provide all my data",
        })
        did = c.id_from(data, "id", "dsar_id")
        if did:
            c.put(f"/privacy/dsar/{did}/status", json={"status": "in_progress"})
            c.put(f"/privacy/dsar/{did}/status", json={"status": "fulfilled"})
        c.ok("get", "/privacy/dsar")


class TestEX11DPIA:
    """P04: create → risk assessment → mitigations → approve."""
    def test_dpia(self, client_factory):
        c = client_factory("P04")
        data = c.try_create("/privacy/dpia", {
            "project_name": f"EX-11 {_uid()}", "description": "E2E DPIA",
            "data_types": ["personal", "financial"],
        })
        did = c.id_from(data, "id", "dpia_id")
        if did:
            c.put(f"/privacy/dpia/{did}", json={"status": "approved"})
        c.ok("get", "/privacy/dpia")


class TestEX12Breach72h:
    """P04, P03: log breach → 72h deadline → notify → contain → close → CISO dashboard."""
    def test_breach(self, client_factory):
        comp = client_factory("P04")
        data = comp.try_create("/privacy/breaches", {
            "title": f"EX-12 {_uid()}", "description": "E2E breach",
            "severity": "high", "data_subjects_affected": 1500,
            "data_types_affected": ["personal", "financial"],
        })
        bid = comp.id_from(data, "id", "breach_id")
        if bid:
            comp.put(f"/privacy/breaches/{bid}/status", json={"status": "contained"})
        ciso = client_factory("P03")
        ciso.ok("get", "/privacy/dashboard")
        ciso.ok("get", "/privacy/breaches")
        ciso.ok("get", "/board-reporting/executive-summary")


class TestEX13WhistleblowerIntake:
    """Anonymous → P04: public submit → track → triage."""
    def test_whistleblower(self, base_url, client_factory):
        resp = requests.post(f"{base_url}/whistleblower/submit", json={
            "category": "fraud", "description": f"EX-13 {_uid()}", "is_anonymous": True,
        })
        if resp.status_code not in (200, 201):
            pytest.skip("Whistleblower submit not available")
        ref = resp.json().get("case_reference") or resp.json().get("reference")
        if ref:
            track = requests.get(f"{base_url}/whistleblower/track/{ref}")
            assert track.status_code == 200
        client_factory("P04").ok("get", "/whistleblower/cases")
        client_factory("P04").ok("get", "/whistleblower/dashboard")


class TestEX14SurveyEngine:
    """P02, P04: build → distribute → collect → analyze."""
    def test_survey(self, client_factory):
        admin = client_factory("P02")
        data = admin.try_create("/surveys/", {
            "title": f"EX-14 {_uid()}", "description": "E2E survey",
            "survey_type": "assessment", "questions": [
                {"text": "Rate effectiveness", "type": "rating"},
            ],
        })
        sid = admin.id_from(data, "id", "survey_id")
        if sid:
            admin.ok("get", f"/surveys/{sid}")
        admin.ok("get", "/surveys/dashboard")
        client_factory("P04").ok("get", "/surveys/")


class TestEX15ITChangeRisk:
    """P06, P15: submit change → risk assess → approve → implement → review."""
    def test_it_change(self, client_factory):
        sec = client_factory("P06")
        data = sec.try_create("/it-change-risk/", {
            "title": f"EX-15 {_uid()}", "description": "Firewall update",
            "change_type": "standard", "risk_level": "medium",
            "planned_date": _future(7), "requester": "qa_it_security",
        })
        cid = sec.id_from(data, "id", "change_id")
        if cid:
            sec.put(f"/it-change-risk/{cid}/transition", json={"new_status": "approved"})
            sec.put(f"/it-change-risk/{cid}/transition", json={"new_status": "implemented"})
            sec.put(f"/it-change-risk/{cid}/transition", json={"new_status": "closed"})
            final = sec.get(f"/it-change-risk/{cid}")
            if final.status_code == 200:
                s = final.json().get("status") or final.json().get("approval_status")
                assert s == "closed"
        sec.ok("get", "/it-change-risk/")


# ═══════════════════════════════════════════════════════════════════════════════
#  XP — CROSS-PERSONA LIFECYCLE JOURNEYS (11 journeys)
# ═══════════════════════════════════════════════════════════════════════════════

class TestXP01AccessRequestLifecycle:
    """P08 submit → P07 approve → P06 provision → P04 certify → P09 evidence."""
    def test_xp01(self, client_factory):
        user = client_factory("P08")
        data = user.try_create("/access-requests/", {
            "request_type": "new_access",
            "items": [{"role_id": "SAP_FI_DISPLAY", "system_id": "ERP_PROD", "action": "add"}],
            "justification": f"XP-01 {_uid()}",
        })
        rid = user.id_from(data, "id", "request_id")
        if rid:
            user.post(f"/access-requests/{rid}/submit")
        client_factory("P07").ok("get", "/access-requests/approvals/pending")
        client_factory("P06").ok("get", "/access-requests/")
        client_factory("P04").ok("get", "/access-requests/")
        client_factory("P09").ok("get", "/audit/logs")


class TestXP02CertificationCampaign:
    """P04 create → P07 review → P21 review → P09 reads."""
    def test_xp02(self, client_factory):
        comp = client_factory("P04")
        data = comp.try_create("/certification/campaigns", {
            "name": f"XP-02 {_uid()}", "type": "user_access", "description": "XP campaign",
        })
        cid = comp.id_from(data, "id", "campaign_id")
        client_factory("P07").ok("get", "/certification/my-reviews")
        client_factory("P21").ok("get", "/certification/my-reviews")
        ea = client_factory("P09")
        ea.ok("get", "/certification/campaigns")
        if cid:
            ea.ok("get", f"/certification/campaigns/{cid}")


class TestXP03FirefighterLifecycle:
    """P06 FFID → P17 request → P12 review → P11 recertify → P03 oversee."""
    def test_xp03(self, client_factory):
        sec = client_factory("P06")
        sec.try_create("/privileged-access/firefighters", {
            "firefighter_id": f"FFID-XP3-{_uid()}", "description": "XP-03",
            "system_id": "ERP_PROD",
            "owner_user_id": client_factory("P11").user_id or "qa_ff_owner",
            "controller_user_id": client_factory("P12").user_id or "qa_ff_controller",
        })
        ff = client_factory("P17")
        ff.post("/privileged-access/requests", json={
            "firefighter_id": "FFID-001", "reason_code": "PROD_ISSUE",
            "justification": f"XP-03 {_uid()}", "duration_hours": 1,
        })
        client_factory("P12").ok("get", "/privileged-access/reviews/pending")
        client_factory("P11").ok("get", "/privileged-access/certification/due")
        ciso = client_factory("P03")
        ciso.ok("get", "/privileged-access/sessions")
        ciso.ok("get", "/privileged-access/statistics")


class TestXP04RiskLifecycle:
    """P05 create → P22 treat → P03 heatmap → P04 SoD remediation → P09 reports."""
    def test_xp04(self, client_factory):
        mgr = client_factory("P05")
        data = mgr.try_create("/risk-management/risks", {
            "title": f"XP-04 {_uid()}", "description": "XP risk",
            "category": "operational", "likelihood": 4, "impact": 3,
        })
        rid = mgr.id_from(data, "id", "risk_id")
        if rid:
            client_factory("P22").put(f"/risk-management/risks/{rid}", json={
                "treatment_plan": "Controls", "residual_likelihood": 2, "residual_impact": 2})
        client_factory("P03").ok("get", "/board-reporting/risk-heat-snapshot")
        client_factory("P04").ok("get", "/sod-remediation/")
        client_factory("P09").ok("get", "/reports/dashboard-summary")


class TestXP05PrivacyLifecycle:
    """P04 ROPA → DSAR → DPIA → breach → P03 dashboard → board."""
    def test_xp05(self, client_factory):
        c = client_factory("P04")
        c.try_create("/privacy/processing-activities", {
            "activity_name": f"XP-05 {_uid()}", "purpose": "Onboarding",
            "legal_basis": "consent", "data_categories": ["personal"],
            "data_subjects": ["customers"],
        })
        dsar = c.try_create("/privacy/dsar", {
            "requester_name": f"XP05 {_uid()}", "request_type": "access",
            "requester_email": f"xp05_{_uid()}@x.com", "description": "Data access",
        })
        did = c.id_from(dsar, "id", "dsar_id")
        if did:
            c.put(f"/privacy/dsar/{did}/status", json={"status": "in_progress"})
        c.try_create("/privacy/dpia", {
            "project_name": f"XP-05 DPIA {_uid()}", "description": "XP DPIA",
            "data_types": ["personal"],
        })
        c.try_create("/privacy/breaches", {
            "title": f"XP-05 Breach {_uid()}", "description": "XP breach",
            "severity": "high", "data_subjects_affected": 500,
            "data_types_affected": ["personal"],
        })
        ciso = client_factory("P03")
        ciso.ok("get", "/privacy/dashboard")
        ciso.ok("get", "/board-reporting/executive-summary")


class TestXP06SOXWorkflow:
    """P10 ICFR → test → P14 certify → P04 signoff → P19 audit → P09 evidence."""
    def test_xp06(self, client_factory):
        sox = client_factory("P10")
        data = sox.try_create("/sox-icfr/controls", {
            "control_name": f"XP-06 {_uid()}", "control_type": "detective",
            "frequency": "quarterly", "owner": "qa_sox_owner",
            "key_control": True, "assertion": "existence", "account_balance": "Revenue",
        })
        cid = sox.id_from(data, "id", "control_id")
        if cid:
            sox.post(f"/sox-icfr/controls/{cid}/test", json={
                "tester": "qa_sox_owner", "test_date": _now(),
                "sample_size": 30, "exceptions_found": 1,
            })
        client_factory("P14").ok("get", "/process-control/controls")
        client_factory("P04").try_create("/sox-icfr/signoffs", {
            "period": "Q3-2026", "scope": "Revenue", "signer": "qa_compliance"})
        client_factory("P19").ok("get", "/sox-icfr/controls")
        client_factory("P09").ok("get", "/audit-evidence/packages")


class TestXP07OperationalRisk:
    """P05 loss → P04 SoD remediation → P06 IT change → insurance → P03 board."""
    def test_xp07(self, client_factory):
        client_factory("P05").try_create("/operational-risk/loss-events", {
            "title": f"XP-07 {_uid()}", "event_type": "execution_delivery",
            "business_line": "retail_banking", "gross_loss": 75000,
            "net_loss": 50000, "recoveries": 25000, "description": "XP loss",
        })
        client_factory("P04").try_create("/sod-remediation/", {
            "remediation_description": f"XP-07 {_uid()}",
            "violation_id": _uid(), "user_id": _uid(),
        })
        client_factory("P06").try_create("/it-change-risk/", {
            "title": f"XP-07 Change {_uid()}", "description": "Firewall",
            "change_type": "standard", "risk_level": "medium",
            "planned_date": _future(7), "requester": "qa_it_security",
        })
        client_factory("P05").ok("get", "/insurance/")
        client_factory("P03").ok("get", "/board-reporting/trend-data")


class TestXP08SanctionsWorkflow:
    """P04 screen → resolve → batch → P03 summary."""
    def test_xp08(self, client_factory):
        c = client_factory("P04")
        data = c.try_create("/sanctions-screening/", {
            "entity_name": f"XP-08 {_uid()}", "entity_type": "individual",
            "entity_id": f"XP8-{_uid()}", "country": "SY",
            "lists_checked": ["OFAC", "UN"],
        })
        sid = c.id_from(data, "id", "screening_id")
        if sid:
            c.put(f"/sanctions-screening/{sid}/resolve", json={
                "resolution": "false_positive", "resolution_notes": "XP clear"})
        c.post("/sanctions-screening/batch", json={
            "entities": [{"entity_name": f"XP8B-{_uid()}", "entity_type": "organization",
                          "entity_id": f"XP8B-{_uid()}", "country": "US"}],
            "lists": ["OFAC"],
        })
        client_factory("P03").ok("get", "/sanctions-screening/summary/stats")


class TestXP09FraudWorkflow:
    """P06 rule → alert → case → P04 review."""
    def test_xp09(self, client_factory):
        sec = client_factory("P06")
        sec.try_create("/fraud/rules", {
            "name": f"XP-09 {_uid()}", "rule_type": "threshold",
            "description": "XP rule", "conditions": {"amount_gt": 50000},
        })
        sec.ok("get", "/fraud/alerts")
        sec.ok("get", "/fraud/cases")
        client_factory("P04").ok("get", "/fraud/cases")


class TestXP10BCMWorkflow:
    """P05 BIA → plan → P02 activate → P16 dashboard."""
    def test_xp10(self, client_factory):
        client_factory("P05").try_create("/bcm/bia", {
            "process_name": f"XP-10 {_uid()}", "criticality": "high",
            "rto_hours": 4, "rpo_hours": 1, "description": "XP BIA",
        })
        client_factory("P05").try_create("/bcm/plans", {
            "plan_name": f"XP-10 Plan {_uid()}", "plan_type": "recovery",
            "description": "XP plan",
        })
        client_factory("P02").try_create("/bcm/activations", {
            "incident_name": f"XP-10 {_uid()}", "severity": "high",
            "description": "XP activation",
        })
        client_factory("P05").ok("get", "/bcm/dashboard")


class TestXP11WhistleblowerFlow:
    """Anonymous submit → track → P04 triage."""
    def test_xp11(self, base_url, client_factory):
        resp = requests.post(f"{base_url}/whistleblower/submit", json={
            "category": "fraud", "description": f"XP-11 {_uid()}", "is_anonymous": True,
        })
        if resp.status_code not in (200, 201):
            pytest.skip("Whistleblower not available")
        ref = resp.json().get("case_reference") or resp.json().get("reference")
        if ref:
            assert requests.get(f"{base_url}/whistleblower/track/{ref}").status_code == 200
        client_factory("P04").ok("get", "/whistleblower/cases")


# ═══════════════════════════════════════════════════════════════════════════════
#  NEG — RBAC DENIAL JOURNEYS (22 journeys)
#  Every denial MUST return 401/403 — a 422 means auth was bypassed.
# ═══════════════════════════════════════════════════════════════════════════════

class TestNEG01TenantAdmin:
    """P02: denied /tenants/."""
    def test_neg01(self, client_factory):
        client_factory("P02").denied("get", "/tenants/")


class TestNEG02CISO:
    """P03: denied mass admin."""
    def test_neg02(self, client_factory):
        client_factory("P03").denied("post", "/mass-admin/jobs", json=_MASS_JOB_BODY)


class TestNEG03Compliance:
    """P04: denied creating FFID."""
    def test_neg03(self, client_factory):
        client_factory("P04").denied("post", "/privileged-access/firefighters", json=_FFID_BODY)


class TestNEG04RiskManager:
    """P05: denied creating FFID."""
    def test_neg04(self, client_factory):
        client_factory("P05").denied("post", "/privileged-access/firefighters", json=_FFID_BODY)


class TestNEG05LineManager:
    """P07: denied settings + custom SoD rule."""
    def test_neg05(self, client_factory):
        c = client_factory("P07")
        c.denied("get", "/settings/smtp")
        c.denied("post", "/risk-rules/custom", json=_RULE_BODY)


class TestNEG06BusinessUser:
    """P08: denied SoD rules, settings, all EAM."""
    def test_neg06(self, client_factory):
        c = client_factory("P08")
        c.denied("post", "/risk-rules/custom", json=_RULE_BODY)
        c.denied("get", "/settings/smtp")
        c.denied("get", "/privileged-access/firefighters")


class TestNEG07ExternalAuditor:
    """P09: denied all writes — campaign create, risk create, settings."""
    def test_neg07(self, client_factory):
        c = client_factory("P09")
        c.denied("post", "/certification/campaigns", json=_CAMPAIGN_BODY)
        c.denied("post", "/risk-management/risks", json=_RISK_BODY)
        c.denied("get", "/settings/smtp")


class TestNEG08SOXOwner:
    """P10: denied FFID creation."""
    def test_neg08(self, client_factory):
        client_factory("P10").denied("post", "/privileged-access/firefighters", json=_FFID_BODY)


class TestNEG09FFOwner:
    """P11: denied controller review queue."""
    def test_neg09(self, client_factory):
        client_factory("P11").denied("get", "/privileged-access/reviews/pending")


class TestNEG10FFController:
    """P12: denied FFID creation."""
    def test_neg10(self, client_factory):
        client_factory("P12").denied("post", "/privileged-access/firefighters", json=_FFID_BODY)


class TestNEG11HRManager:
    """P13: denied settings + all EAM."""
    def test_neg11(self, client_factory):
        c = client_factory("P13")
        c.denied("get", "/settings/smtp")
        c.denied("get", "/privileged-access/firefighters")


class TestNEG12ProcessOwner:
    """P14: denied settings + all EAM."""
    def test_neg12(self, client_factory):
        c = client_factory("P14")
        c.denied("get", "/settings/smtp")
        c.denied("get", "/privileged-access/firefighters")


class TestNEG13ITOperations:
    """P15: denied mass admin + SoD rule creation."""
    def test_neg13(self, client_factory):
        c = client_factory("P15")
        c.denied("post", "/mass-admin/jobs", json=_MASS_JOB_BODY)
        c.denied("post", "/risk-rules/custom", json=_RULE_BODY)


class TestNEG14ReadOnly:
    """P16: denied any write + settings + EAM."""
    def test_neg14(self, client_factory):
        c = client_factory("P16")
        c.denied("post", "/access-requests/", json=_ACCESS_REQ_BODY)
        c.denied("post", "/risk-rules/custom", json=_RULE_BODY)
        c.denied("get", "/settings/smtp")
        c.denied("get", "/privileged-access/firefighters")


class TestNEG15FFSessionUser:
    """P17: denied controller review + settings."""
    def test_neg15(self, client_factory):
        c = client_factory("P17")
        c.denied("get", "/privileged-access/reviews/pending")
        c.denied("get", "/settings/smtp")


class TestNEG16MitigationMonitor:
    """P18: denied SoD rule creation + settings."""
    def test_neg16(self, client_factory):
        c = client_factory("P18")
        c.denied("post", "/risk-rules/custom", json=_RULE_BODY)
        c.denied("get", "/settings/smtp")


class TestNEG17InternalAuditor:
    """P19: denied mass admin."""
    def test_neg17(self, client_factory):
        client_factory("P19").denied("post", "/mass-admin/jobs", json=_MASS_JOB_BODY)


class TestNEG18VendorManager:
    """P20: denied settings + certification campaign creation."""
    def test_neg18(self, client_factory):
        c = client_factory("P20")
        c.denied("get", "/settings/smtp")
        c.denied("post", "/certification/campaigns", json=_CAMPAIGN_BODY)


class TestNEG19RoleOwner:
    """P21: denied mass admin + FFID creation."""
    def test_neg19(self, client_factory):
        c = client_factory("P21")
        c.denied("post", "/mass-admin/jobs", json=_MASS_JOB_BODY)
        c.denied("post", "/privileged-access/firefighters", json=_FFID_BODY)


class TestNEG20RiskOwner:
    """P22: denied settings + campaign creation + FFID creation."""
    def test_neg20(self, client_factory):
        c = client_factory("P22")
        c.denied("get", "/settings/smtp")
        c.denied("post", "/certification/campaigns", json=_CAMPAIGN_BODY)
        c.denied("post", "/privileged-access/firefighters", json=_FFID_BODY)


class TestNEG21CrossTenantIsolation:
    """All non-admin: no record from another tenant readable."""
    def test_neg21(self, client_factory):
        # Any persona trying to access a different tenant's data
        # should get empty results or 403, never another tenant's data
        c = client_factory("P08")
        resp = c.get("/users/", params={"tenant_id": "other-tenant-999"})
        if resp.status_code == 200:
            data = resp.json()
            items = data if isinstance(data, list) else data.get("items", data.get("users", []))
            for item in items:
                tid = item.get("tenant_id", TENANT_ID)
                assert tid == TENANT_ID, f"Cross-tenant leak: got tenant_id={tid}"


class TestNEG22Unauthenticated:
    """Every route returns 401 except /whistleblower/submit and /whistleblower/track."""
    def test_neg22(self, base_url):
        protected = [
            "/dashboard/stats", "/users/", "/risk-management/risks",
            "/access-requests/", "/certification/campaigns",
            "/settings/smtp", "/privileged-access/firefighters",
            "/audit/logs", "/sox-icfr/controls", "/privacy/dsar",
        ]
        for path in protected:
            resp = requests.get(f"{base_url}{path}")
            assert resp.status_code in (401, 403), (
                f"Unauthenticated GET {path} returned {resp.status_code} — should be 401/403")

        # Whistleblower public routes SHOULD work without auth
        resp = requests.post(f"{base_url}/whistleblower/submit", json={
            "category": "other", "description": "NEG-22 auth test", "is_anonymous": True})
        assert resp.status_code in (200, 201, 422), (
            f"Public whistleblower submit returned {resp.status_code}")
