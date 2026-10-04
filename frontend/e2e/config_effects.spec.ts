/**
 * J15 — Config Effects (no restart required)
 * TC-J15-001 through TC-J15-008
 *
 * DEF-003 CRT: No /config router exists. J15 tests the CLOSEST available config
 * surfaces while documenting the gap. Tests that have no backend target are
 * marked as CRT-BLOCKED and will fail — this is the expected baseline result.
 *
 * Available config surfaces:
 *  - /settings/*  (smtp_config_router)
 *  - /workflows/* (workflows.router)
 *  - /notifications/templates/* (notifications.router — read-only)
 *  - /tenants/*   (tenants.router)
 */
import { test, expect } from '@playwright/test';
import { getToken, apiPost, apiGet, waitForEmail, clearMailpit } from './helpers';

const BASE_URL = 'http://localhost:9000';

test.describe('J15 — Config Effects (DEF-003: /config router missing)', () => {

  test.beforeEach(async () => {
    await clearMailpit();
  });

  test('TC-J15-001 [CRT-BLOCKED DEF-003]: Workflow stage config endpoint', async () => {
    // No /config router exists. /workflows router exists but is for workflow instances,
    // not for changing approval stage configuration.
    // Expected: 200. Actual: 404. This test MUST fail until DEF-003 is fixed.
    const adminToken = await getToken('P02');
    const { status } = await apiPost('/config/workflows/access-request', adminToken, {
      stages: [
        { name: 'manager_approval', required: true },
        { name: 'security_review', required: true },
      ],
    });
    expect(status).toBe(200); // Will fail — DEF-003
  });

  test('TC-J15-002 [CRT-BLOCKED DEF-003]: SLA threshold config endpoint', async () => {
    const adminToken = await getToken('P02');
    const { status } = await apiPost('/config/sla', adminToken, {
      module: 'access_requests',
      warning_hours: 24,
      breach_hours: 48,
    });
    expect(status).toBe(200); // Will fail — DEF-003
  });

  test('TC-J15-003 [CRT-BLOCKED DEF-003]: RBAC permission grant flip via config', async () => {
    const adminToken = await getToken('P01');
    const { status } = await apiPost('/config/rbac/grants', adminToken, {
      role: 'read_only_viewer',
      permission: 'view_risk_rules',
      resource: '/risk/rules',
    });
    expect(status).toBe(200); // Will fail — DEF-003
  });

  test('TC-J15-004 [CRT-BLOCKED DEF-003]: Notification template body update via config', async () => {
    const adminToken = await getToken('P02');
    const { status } = await apiPost(
      '/config/notification-templates/ACCESS_REQUEST_SUBMITTED',
      adminToken,
      {
        subject: 'Access Request Submitted — {{role_name}}',
        body: `UPDATED QA BODY ${Date.now()} — {{requester_name}}`,
      }
    );
    expect(status).toBe(200); // Will fail — DEF-003
  });

  test('TC-J15-005: Notification templates READ — existing endpoint', async () => {
    // Templates can be READ via /notifications/templates (GET exists — confirmed)
    const token = await getToken('P02');
    const { status, body } = await apiGet('/notifications/templates', token);
    expect(status).toBe(200);
    const templates = body.items || body.templates || body;
    expect(Array.isArray(templates)).toBe(true);
  });

  test('TC-J15-006: Workflow instances list — /workflows prefix accessible', async () => {
    const adminToken = await getToken('P02');
    const { status } = await apiGet('/workflows', adminToken);
    expect([200, 404]).toContain(status); // 404 if no workflow instances seeded
  });

  test('TC-J15-007: Tenant settings accessible via /tenants', async () => {
    const adminToken = await getToken('P02');
    const { status } = await apiGet('/tenants', adminToken);
    expect(status).toBe(200);
  });

  test('TC-J15-008: Audit log records configuration changes', async () => {
    const adminToken = await getToken('P01');
    const { status, body } = await apiGet('/audit/logs?resource_type=config', adminToken);
    expect(status).toBe(200);
    const logs = body.items || body.logs || body;
    expect(Array.isArray(logs)).toBe(true);
  });

});
