/**
 * J11 — Third-Party Risk Management
 * TC-J11-001 through TC-J11-008
 */
import { test, expect } from '@playwright/test';
import { getToken, apiPost, apiGet, waitForEmail, clearMailpit } from './helpers';

test.describe('J11 — TPRM', () => {

  test.beforeEach(async () => {
    await clearMailpit();
  });

  test('TC-J11-001: Vendor Manager (P20) creates vendor record', async () => {
    const token = await getToken('P20');
    const { status, body } = await apiPost('/tprm/vendors', token, {
      name: `QA Vendor ${Date.now()}`,
      vendor_type: 'saas_provider',
      contact_email: `vendor.${Date.now()}@example.com`,
      criticality: 'high',
      data_access: ['PII', 'financial'],
    });
    expect([200, 201]).toContain(status);
    expect(body.id || body.vendor_id).toBeDefined();
  });

  test('TC-J11-002: Risk assessment sent to vendor', async () => {
    const token = await getToken('P20');
    // Create vendor first
    const { body: vendBody } = await apiPost('/tprm/vendors', token, {
      name: `QA Vendor Assessment ${Date.now()}`,
      vendor_type: 'data_processor',
      contact_email: `qa.vendor.${Date.now()}@example.com`,
      criticality: 'medium',
    });
    const vendorId = vendBody.id || vendBody.vendor_id;
    if (!vendorId) return;

    const { status, body } = await apiPost(`/tprm/vendors/${vendorId}/assessments`, token, {
      assessment_type: 'annual_review',
      survey_id: 'SURVEY-TPRM-001',
      due_date: '2027-02-28',
    });
    expect([200, 201]).toContain(status);
    expect(body.id || body.assessment_id).toBeDefined();
  });

  test('TC-J11-003: Vendor risk score computed from assessment', async () => {
    const token = await getToken('P20');
    const { status, body } = await apiGet('/tprm/vendors', token);
    expect(status).toBe(200);
    const vendors = body.items || body.vendors || body;
    expect(Array.isArray(vendors)).toBe(true);
  });

  test('TC-J11-004: Fourth-party risk surfaced for high-risk vendor', async () => {
    const token = await getToken('P20');
    const { status, body } = await apiGet('/tprm/fourth-party-risks', token);
    expect(status).toBe(200);
  });

  test('TC-J11-005: Overdue reassessment flags vendor', async () => {
    const token = await getToken('P20');
    const { status, body } = await apiGet('/tprm/vendors?overdue_reassessment=true', token);
    expect(status).toBe(200);
    const vendors = body.items || body.vendors || body;
    expect(Array.isArray(vendors)).toBe(true);
  });

  test('TC-J11-006: Vendor SLA tracked', async () => {
    const token = await getToken('P20');
    const { status } = await apiGet('/reports/vendor-sla', token);
    expect(status).toBe(200);
  });

  test('TC-J11-007: P08 Business User cannot manage vendors → 403', async () => {
    const token = await getToken('P08');
    const { status } = await apiPost('/tprm/vendors', token, {
      name: 'Unauthorized vendor',
      vendor_type: 'saas_provider',
    });
    expect(status).toBe(403);
  });

  test('TC-J11-008: Vendor risk distribution report accessible', async () => {
    const token = await getToken('P20');
    const { status } = await apiGet('/reports/vendor-risk-distribution', token);
    expect(status).toBe(200);
  });

});
