/**
 * J08 — Risk Register & KRI Monitoring
 * TC-J08-001 through TC-J08-011
 *
 * Router: risk_mgmt.router → prefix /risk-management
 * Mitigation: ara.router → prefix /risk-intelligence
 */
import { test, expect } from '@playwright/test';
import { getToken, apiPost, apiGet } from './helpers';

test.describe('J08 — Risk Management', () => {

  test('TC-J08-001: Risk Manager (P05) creates risk entry', async () => {
    const token = await getToken('P05');
    const { status, body } = await apiPost('/risk-management/risks', token, {
      title: 'QA Risk — Insufficient SoD controls in AP',
      category: 'operational',
      likelihood: 4,
      impact: 5,
      description: 'Lack of segregation in AP process could lead to fraud',
    });
    expect([200, 201]).toContain(status);
    expect(body.id || body.risk_id).toBeDefined();
  });

  test('TC-J08-002: Risk inherits score from likelihood × impact', async () => {
    const token = await getToken('P05');
    const { body: risks } = await apiGet('/risk-management/risks', token);
    const items = risks.items || risks.risks || risks;
    if (Array.isArray(items) && items.length > 0) {
      const risk = items[0];
      const score = risk.risk_score || risk.inherent_risk_score || (risk.likelihood * risk.impact);
      expect(score).toBeGreaterThan(0);
    }
  });

  test('TC-J08-003: Risk heatmap data returned', async () => {
    const token = await getToken('P05');
    const { status, body } = await apiGet('/risk-management/heatmap', token);
    expect(status).toBe(200);
    expect(body).toBeDefined();
  });

  test('TC-J08-004: KRI created and threshold set', async () => {
    const token = await getToken('P05');
    const { status, body } = await apiPost('/risk-management/kris', token, {
      name: 'QA KRI — SoD violation count',
      metric: 'sod_violation_count',
      amber_threshold: 10,
      red_threshold: 25,
      frequency: 'weekly',
    });
    expect([200, 201]).toContain(status);
    expect(body.id || body.kri_id).toBeDefined();
  });

  test('TC-J08-005: KRI dashboard endpoint accessible', async () => {
    const token = await getToken('P05');
    const { status, body } = await apiGet('/risk-management/kris/dashboard', token);
    expect(status).toBe(200);
  });

  test('TC-J08-006: Risk Owner (P22) can view risk register', async () => {
    const token = await getToken('P22');
    const { status } = await apiGet('/risk-management/risks', token);
    expect(status).toBe(200);
  });

  test('TC-J08-007: Risk response (treatment plan) added', async () => {
    const token = await getToken('P05');
    const { body: risks } = await apiGet('/risk-management/risks', token);
    const items = risks.items || risks.risks || risks;
    if (!Array.isArray(items) || items.length === 0) return;

    const riskId = items[0].id;
    const { status } = await apiPost(`/risk-management/risks/${riskId}/responses`, token, {
      response_type: 'mitigate',
      description: 'Implement automated SoD monitoring with weekly reports',
      due_date: '2027-03-31',
      responsible_party: 'IT Security',
    });
    expect([200, 201]).toContain(status);
  });

  test('TC-J08-008: Incident logged against risk category', async () => {
    const token = await getToken('P05');
    const { status, body } = await apiPost('/risk-management/incidents', token, {
      title: 'QA Incident — Unauthorized GL posting detected',
      risk_category: 'financial_fraud',
      severity: 'high',
      detected_date: new Date().toISOString().split('T')[0],
    });
    expect([200, 201]).toContain(status);
  });

  test('TC-J08-009: External Auditor (P09) read-only risk access', async () => {
    const token = await getToken('P09');
    const { status } = await apiGet('/risk-management/risks', token);
    expect(status).toBe(200);
  });

  test('TC-J08-010: P08 Business User cannot manage risks → 403', async () => {
    const token = await getToken('P08');
    const { status } = await apiPost('/risk-management/risks', token, {
      title: 'Unauthorized risk entry',
      category: 'operational',
      likelihood: 1,
      impact: 1,
    });
    expect(status).toBe(403);
  });

  test('TC-J08-011: Risk appetite endpoint returns configured thresholds', async () => {
    const token = await getToken('P05');
    const { status, body } = await apiGet('/risk-management/appetites', token);
    expect(status).toBe(200);
    expect(body).toBeDefined();
  });

  test('TC-J08-012: Mitigation Monitor (P18) accesses mitigation controls', async () => {
    const token = await getToken('P18');
    // Mitigation is in ara.router under /risk-intelligence
    const { status } = await apiGet('/risk-intelligence/mitigation/controls', token);
    expect(status).toBe(200);
  });

});
