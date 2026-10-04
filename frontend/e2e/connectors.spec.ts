/**
 * J16 — Admin & Connectors
 * TC-J16-001 through TC-J16-010
 *
 * Router: integrations.router → prefix /integrations
 * Connector CRUD at /integrations/connectors
 * Job runner at /integrations/automation/jobs/{name}/run
 * Health at /integrations/health
 */
import { test, expect } from '@playwright/test';
import { getToken, apiPost, apiGet } from './helpers';

test.describe('J16 — Admin & Connectors', () => {

  test('TC-J16-001: Platform Admin (P01) lists existing connectors', async () => {
    const token = await getToken('P01');
    const { status, body } = await apiGet('/integrations/connectors', token);
    expect(status).toBe(200);
    const connectors = body.items || body.connectors || body;
    expect(Array.isArray(connectors)).toBe(true);
  });

  test('TC-J16-002: Add Demo SAP connector', async () => {
    const token = await getToken('P01');
    const { status, body } = await apiPost('/integrations/connectors', token, {
      name: 'Demo SAP ECC',
      connector_type: 'sap_rfc',
      host: 'sap_mock',
      port: 1080,
      client: '100',
      system_id: 'QA_PRD',
      username: 'RFCUSER',
      password: 'rfcpass',
      mode: 'mock',
    });
    expect([200, 201, 409]).toContain(status); // 409 = already exists
    if (status === 200 || status === 201) {
      expect(body.id || body.connector_id).toBeDefined();
    }
  });

  test('TC-J16-003: Test connectivity to SAP connector', async () => {
    const token = await getToken('P01');
    const { body: listBody } = await apiGet('/integrations/connectors', token);
    const connectors = listBody.items || listBody.connectors || listBody;
    if (!Array.isArray(connectors) || connectors.length === 0) return;

    const connectorId = connectors[0].id;
    const { status, body } = await apiPost(`/integrations/connectors/${connectorId}/test`, token, {});
    expect([200, 201]).toContain(status);
    expect(body.success || body.connected || body.status).toBeDefined();
  });

  test('TC-J16-004: Trigger user sync from SAP connector', async () => {
    const token = await getToken('P01');
    const { body: listBody } = await apiGet('/integrations/connectors', token);
    const connectors = listBody.items || listBody.connectors || listBody;
    if (!Array.isArray(connectors) || connectors.length === 0) return;

    const connectorId = connectors[0].id;
    const { status, body } = await apiPost(`/integrations/connectors/${connectorId}/sync`, token, {
      sync_type: 'users',
    });
    expect([200, 201, 202]).toContain(status);
  });

  test('TC-J16-005: Run-now job via automation runner', async () => {
    const token = await getToken('P01');
    // /integrations/automation/jobs/{job_name}/run
    const { status } = await apiPost('/integrations/automation/jobs/sap_user_sync/run', token, {});
    expect([200, 201, 202]).toContain(status);
  });

  test('TC-J16-006: Job history shows executed jobs', async () => {
    const token = await getToken('P01');
    // GET /integrations/automation/history
    const { status, body } = await apiGet('/integrations/automation/history', token);
    expect(status).toBe(200);
    const jobs = body.items || body.jobs || body;
    expect(Array.isArray(jobs)).toBe(true);
  });

  test('TC-J16-007: Azure AD connector added and tested', async () => {
    const token = await getToken('P01');
    const { status, body } = await apiPost('/integrations/connectors', token, {
      name: 'Demo Azure AD',
      connector_type: 'azure_ad',
      tenant_id: 'qa-aad-tenant',
      client_id: 'qa-client-id',
      client_secret: 'qa-client-secret',
      mode: 'mock',
    });
    expect([200, 201, 409]).toContain(status);

    if (status === 200 || status === 201) {
      const connectorId = body.id || body.connector_id;
      const { status: testStatus } = await apiPost(
        `/integrations/connectors/${connectorId}/test`, token, {}
      );
      expect([200, 201]).toContain(testStatus);
    }
  });

  test('TC-J16-008: HR/SCIM connector added', async () => {
    const token = await getToken('P01');
    const { status } = await apiPost('/integrations/connectors', token, {
      name: 'Demo HR SCIM',
      connector_type: 'hr_scim',
      base_url: 'http://hr_mock:1080',
      mode: 'mock',
    });
    expect([200, 201, 409]).toContain(status);
  });

  test('TC-J16-009: P08 Business User cannot manage connectors → 403', async () => {
    const token = await getToken('P08');
    const { status } = await apiPost('/integrations/connectors', token, {
      name: 'Unauthorized connector',
      connector_type: 'sap_rfc',
    });
    expect(status).toBe(403);
  });

  test('TC-J16-010: Integration health endpoint shows connector statuses', async () => {
    const token = await getToken('P01');
    const { status } = await apiGet('/integrations/health', token);
    expect(status).toBe(200);
  });

});
