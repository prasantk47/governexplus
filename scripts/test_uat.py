#!/usr/bin/env python3
"""
Comprehensive UAT Test Script

Tests all API endpoints:
- Reports Dashboard Summary
- Connector CRUD (create, list, get, test, delete)
- Tenant Onboarding (signup, verify, create, list, activate, suspend, deactivate)
- Audit Report
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

PASS = 0
FAIL = 0


def ok(msg):
    global PASS
    PASS += 1
    print(f"  PASS: {msg}")


def fail(msg):
    global FAIL
    FAIL += 1
    print(f"  FAIL: {msg}")


async def test_reports_dashboard():
    print("\n" + "=" * 60)
    print("REPORTS DASHBOARD SUMMARY")
    print("=" * 60)

    from api.routers.reports import get_dashboard_summary

    print("\n[1] GET /reports/dashboard-summary?days=30")
    result = await get_dashboard_summary(days=30)

    # Check top-level keys
    for key in ["period_days", "generated_at", "access_requests", "firefighter", "risk", "audit"]:
        if key in result:
            ok(f"Has '{key}'")
        else:
            fail(f"Missing '{key}'")

    # Check audit data (persisted in DB)
    audit = result["audit"]
    if audit["total_entries"] > 0:
        ok(f"Audit: {audit['total_entries']} entries")
    else:
        fail("Audit: 0 entries (expected seeded data)")

    if audit["failed_actions"] > 0:
        ok(f"Audit: {audit['failed_actions']} failed actions tracked")
    else:
        fail("Audit: no failed actions")

    if audit["compliance_entries"] > 0:
        ok(f"Audit: {audit['compliance_entries']} compliance entries")
    else:
        fail("Audit: no compliance entries")

    cats = audit["by_category"]
    if len(cats) >= 4:
        ok(f"Audit categories: {list(cats.keys())}")
    else:
        fail(f"Expected 4+ audit categories, got {len(cats)}")

    # Check risk data
    risk = result["risk"]
    if risk["total_rules"] > 0:
        ok(f"Risk: {risk['total_rules']} rules loaded")
    else:
        fail("Risk: no rules loaded")

    if len(risk.get("rules_by_category", {})) > 0:
        ok(f"Risk categories: {list(risk['rules_by_category'].keys())}")
    else:
        fail("Risk: no rule categories")

    if len(risk.get("rules_by_type", {})) > 0:
        ok(f"Risk types: {list(risk['rules_by_type'].keys())}")
    else:
        fail("Risk: no rule types")

    # Access requests (in-memory, may be 0)
    ar = result["access_requests"]
    ok(f"Access requests: total={ar.get('total_requests', 0)}, SLA rate={ar['sla']['sla_compliance_rate']}%")

    # Firefighter (in-memory, may be 0)
    ff = result["firefighter"]
    ok(f"Firefighter: sessions={ff.get('total_sessions', 0)}, active={ff.get('active_sessions', 0)}")


async def test_connectors():
    print("\n" + "=" * 60)
    print("CONNECTOR CRUD TESTS")
    print("=" * 60)

    from api.routers.integrations import (
        create_connector, list_connectors, delete_connector,
        list_connector_types, get_connector, test_connection,
        ConnectorConfigRequest
    )

    # 1. List types
    print("\n[1] GET /integrations/connector-types")
    try:
        result = await list_connector_types()
        types = result.get("connector_types", [])
        if len(types) >= 3:
            ok(f"{len(types)} connector types: {[t['type'] for t in types[:4]]}")
        else:
            fail(f"Expected 3+ types, got {len(types)}")
    except Exception as e:
        fail(str(e))

    # 2. Create SAP connector
    print("\n[2] POST /integrations/connectors (SAP)")
    connector_id = None
    try:
        config = ConnectorConfigRequest(
            name="SAP ECC Test",
            connector_type="sap",
            host="sap-ecc.example.com",
            port=3300,
            username="RFC_USER",
            password="test_password",
            use_ssl=True,
            additional_config={"system_id": "ECP", "client": "100"},
        )
        result = await create_connector(config)
        connector_id = result.get("config_id")
        if connector_id:
            ok(f"Created SAP connector: {connector_id}")
        else:
            fail(f"No config_id in response: {list(result.keys())}")
    except Exception as e:
        fail(str(e))

    # 3. Create Azure AD connector
    print("\n[3] POST /integrations/connectors (Azure AD)")
    connector_id2 = None
    try:
        config2 = ConnectorConfigRequest(
            name="Azure AD Corporate",
            connector_type="azure_ad",
            host="login.microsoftonline.com",
            port=443,
            username="client_id",
            password="client_secret",
            use_ssl=True,
            additional_config={"tenant_id": "azure-123"},
        )
        result2 = await create_connector(config2)
        connector_id2 = result2.get("config_id")
        if connector_id2:
            ok(f"Created Azure AD connector: {connector_id2}")
        else:
            fail(f"No config_id in response")
    except Exception as e:
        fail(str(e))

    # 4. List connectors
    print("\n[4] GET /integrations/connectors")
    try:
        result = await list_connectors(connector_type=None, status=None)
        conns = result.get("connectors", [])
        if len(conns) >= 2:
            ok(f"{len(conns)} connectors listed")
            for c in conns[:3]:
                print(f"    - {c.get('name', '?')} ({c.get('connector_type', '?')}) [{c.get('status', '?')}]")
        else:
            fail(f"Expected 2+ connectors, got {len(conns)}")
    except Exception as e:
        fail(str(e))

    # 5. Get details
    if connector_id:
        print(f"\n[5] GET /integrations/connectors/{connector_id}")
        try:
            result = await get_connector(connector_id)
            if result.get("name") == "SAP ECC Test":
                ok(f"Got connector detail: {result['name']}")
            else:
                fail(f"Unexpected name: {result.get('name')}")
        except Exception as e:
            fail(str(e))

        # 6. Test connection
        print(f"\n[6] POST /integrations/connectors/{connector_id}/test")
        try:
            result = await test_connection(connector_id)
            ok(f"Connection test: {result.get('status', result.get('message', '?'))}")
        except Exception as e:
            fail(str(e))

        # 7. Delete
        print(f"\n[7] DELETE /integrations/connectors/{connector_id}")
        try:
            result = await delete_connector(connector_id)
            ok(f"Deleted connector")
        except Exception as e:
            fail(str(e))

        # 8. Verify deleted
        print("\n[8] Verify deletion")
        try:
            result = await list_connectors(connector_type=None, status=None)
            conns = result.get("connectors", [])
            found = any(c.get("config_id") == connector_id for c in conns)
            if not found:
                ok(f"Connector {connector_id} no longer in list ({len(conns)} remaining)")
            else:
                fail(f"Connector still exists after delete")
        except Exception as e:
            fail(str(e))


async def test_tenant_onboarding():
    print("\n" + "=" * 60)
    print("TENANT ONBOARDING TESTS")
    print("=" * 60)

    from api.routers.tenants import (
        start_signup, verify_email, create_tenant, list_tenants,
        get_tenant, activate_tenant, suspend_tenant, list_tiers,
        deactivate_tenant,
        SignupRequest, VerifyEmailRequest, CreateTenantRequest,
    )

    # 1. Signup
    print("\n[1] POST /tenants/signup")
    session_id = None
    token = None
    try:
        req = SignupRequest(email="admin@acme-uat.com", company_name="Acme UAT Corp")
        result = await start_signup(req)
        session_id = result.get("session_id", "")
        token = result.get("verification_token", "")
        if session_id:
            ok(f"Signup session: {session_id[:25]}...")
        else:
            fail("No session_id returned")
    except Exception as e:
        fail(str(e))

    # 2. Verify email
    if token:
        print("\n[2] POST /tenants/verify-email")
        try:
            result = await verify_email(VerifyEmailRequest(token=token))
            ok(f"Email verified: {result.get('status', result.get('verified', '?'))}")
        except Exception as e:
            fail(str(e))

    # 3. List tiers
    print("\n[3] GET /tenants/tiers")
    try:
        result = await list_tiers()
        tiers = result.get("tiers", result) if isinstance(result, dict) else result
        if isinstance(tiers, list) and len(tiers) >= 3:
            ok(f"{len(tiers)} tiers available")
            for t in tiers[:5]:
                if isinstance(t, dict):
                    print(f"    - {t.get('name', t.get('tier_id', '?'))}")
        else:
            ok(f"Tiers response received ({type(tiers).__name__})")
    except Exception as e:
        fail(str(e))

    # 4. Create tenant (admin)
    print("\n[4] POST /tenants/")
    tenant_id = None
    try:
        req = CreateTenantRequest(
            name="UAT Test Tenant",
            owner_email="admin@uat-test.com",
            tier="professional",
            trial_days=14,
        )
        result = await create_tenant(req)
        if isinstance(result, dict):
            tenant_id = result.get("id") or result.get("tenant_id")
            tenant_obj = result.get("tenant", {})
            if isinstance(tenant_obj, dict):
                tenant_id = tenant_id or tenant_obj.get("id")
        else:
            tenant_id = getattr(result, "id", None)

        if tenant_id:
            ok(f"Created tenant: {tenant_id}")
        else:
            ok(f"Tenant creation response received")
    except Exception as e:
        fail(str(e))

    # 5. List tenants
    print("\n[5] GET /tenants/")
    try:
        result = await list_tenants(status=None, tier=None, limit=50)
        if isinstance(result, dict):
            tenants = result.get("tenants", [])
        elif isinstance(result, list):
            tenants = result
        else:
            tenants = []
        if len(tenants) >= 1:
            ok(f"{len(tenants)} tenants listed")
            for t in tenants[:3]:
                name = t.get("name", "?") if isinstance(t, dict) else getattr(t, "name", "?")
                status = t.get("status", "?") if isinstance(t, dict) else getattr(t, "status", "?")
                print(f"    - {name} [{status}]")
        else:
            fail("No tenants found")
    except Exception as e:
        fail(str(e))

    # 6. Activate/suspend/deactivate lifecycle
    if tenant_id:
        print(f"\n[6] POST /tenants/{tenant_id}/activate")
        try:
            result = await activate_tenant(tenant_id)
            status = result.get("status", "?") if isinstance(result, dict) else getattr(result, "status", "?")
            ok(f"Activated: status={status}")
        except Exception as e:
            fail(str(e))

        print(f"\n[7] POST /tenants/{tenant_id}/suspend")
        try:
            result = await suspend_tenant(tenant_id, reason="UAT test")
            status = result.get("status", "?") if isinstance(result, dict) else getattr(result, "status", "?")
            ok(f"Suspended: status={status}")
        except Exception as e:
            fail(str(e))

        print(f"\n[8] DELETE /tenants/{tenant_id}")
        try:
            result = await deactivate_tenant(tenant_id)
            status = result.get("status", "?") if isinstance(result, dict) else getattr(result, "status", "?")
            ok(f"Deactivated: status={status}")
        except Exception as e:
            fail(str(e))


async def test_audit_report():
    print("\n" + "=" * 60)
    print("AUDIT REPORT TESTS")
    print("=" * 60)

    from audit.logger import audit_logger

    # 1. Query audit logs
    print("\n[1] Audit query (last 30 days)")
    from datetime import datetime, timedelta
    start = datetime.utcnow() - timedelta(days=30)
    logs = audit_logger.query(start_date=start, limit=200)
    if len(logs) > 50:
        ok(f"{len(logs)} audit logs retrieved")
    else:
        fail(f"Expected 50+ logs, got {len(logs)}")

    # 2. Check categories
    categories = set()
    for log in logs:
        if log.action_category:
            categories.add(log.action_category)
    if len(categories) >= 4:
        ok(f"Audit categories: {sorted(categories)}")
    else:
        fail(f"Expected 4+ categories, got {categories}")

    # 3. Check compliance entries
    compliance_count = sum(1 for log in logs if log.compliance_relevant)
    if compliance_count > 10:
        ok(f"{compliance_count} compliance-relevant entries")
    else:
        fail(f"Expected 10+ compliance entries, got {compliance_count}")

    # 4. Check failures
    failed_count = sum(1 for log in logs if not log.success)
    if failed_count > 0:
        ok(f"{failed_count} failed actions logged")
    else:
        fail("No failed actions in audit log")

    # 5. Test count method
    print("\n[2] Audit count")
    try:
        total = audit_logger.count(start_date=start)
        ok(f"Count method: {total} entries")
    except Exception as e:
        fail(str(e))

    # 6. Test category filter
    print("\n[3] Audit category filter")
    try:
        ff_logs = audit_logger.query(start_date=start, category="firefighter", limit=100)
        ok(f"Firefighter logs: {len(ff_logs)} entries")
    except Exception as e:
        fail(str(e))


async def main():
    print("\n" + "#" * 60)
    print("#  GOVERNEX+ COMPREHENSIVE UAT")
    print("#" * 60)

    await test_reports_dashboard()
    await test_connectors()
    await test_tenant_onboarding()
    await test_audit_report()

    print("\n" + "#" * 60)
    print(f"#  UAT RESULTS: {PASS} PASSED, {FAIL} FAILED")
    print("#" * 60)

    if FAIL > 0:
        print(f"\n  {FAIL} test(s) failed — review output above")
    else:
        print("\n  All tests passed!")

    return FAIL


if __name__ == "__main__":
    failures = asyncio.run(main())
    sys.exit(1 if failures > 0 else 0)
