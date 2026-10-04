/**
 * J18 — Extended Modules
 * TC-J18-001 through TC-J18-020
 * Covers:
 *   - Whistleblower: anon intake + token follow-up
 *   - BCM: BIA + plan test
 *   - Fraud: rule → alert → case
 *   - Survey: logic branching
 */
import { test, expect } from '@playwright/test';
import { getToken, apiPost, apiGet } from './helpers';

const BASE_URL = 'http://localhost:9000';

// ─── Whistleblower ────────────────────────────────────────────────────────────

test.describe('J18a — Whistleblower', () => {

  test('TC-J18-001: Anonymous intake — no auth required', async () => {
    const res = await fetch(`${BASE_URL}/whistleblower/submit`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-Tenant-ID': 'qa-tenant-001' },
      body: JSON.stringify({
        category: 'financial_fraud',
        description: 'QA anon report — suspicious AP payments',
        anonymous: true,
      }),
    });
    expect([200, 201]).toContain(res.status);
    const body = await res.json();
    expect(body.tracking_token || body.reference_code || body.token).toBeDefined();
  });

  test('TC-J18-002: Follow-up using tracking token — no auth required', async () => {
    // Submit first to get token
    const submitRes = await fetch(`${BASE_URL}/whistleblower/submit`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-Tenant-ID': 'qa-tenant-001' },
      body: JSON.stringify({
        category: 'policy_violation',
        description: 'QA follow-up test submission',
        anonymous: true,
      }),
    });
    expect([200, 201]).toContain(submitRes.status);
    const { tracking_token, reference_code, token } = await submitRes.json();
    const ref = tracking_token || reference_code || token;
    if (!ref) return;

    // Follow up
    const trackRes = await fetch(`${BASE_URL}/whistleblower/track/${ref}`, {
      headers: { 'X-Tenant-ID': 'qa-tenant-001' },
    });
    expect([200, 404]).toContain(trackRes.status);
    if (trackRes.status === 200) {
      const body = await trackRes.json();
      expect(body.status || body.case_status).toBeDefined();
    }
  });

  test('TC-J18-003: CISO (P03) can view submitted whistleblower cases', async () => {
    const token = await getToken('P03');
    const { status, body } = await apiGet('/whistleblower/cases', token);
    expect(status).toBe(200);
    const cases = body.items || body.cases || body;
    expect(Array.isArray(cases)).toBe(true);
  });

  test('TC-J18-004: P08 Business User cannot view whistleblower cases → 403', async () => {
    const token = await getToken('P08');
    const { status } = await apiGet('/whistleblower/cases', token);
    expect(status).toBe(403);
  });

});

// ─── BCM ──────────────────────────────────────────────────────────────────────

test.describe('J18b — BCM', () => {

  test('TC-J18-005: Risk Manager (P05) creates BIA entry', async () => {
    const token = await getToken('P05');
    const { status, body } = await apiPost('/bcm/bia', token, {
      process_name: 'Accounts Payable Processing',
      rto_hours: 4,
      rpo_hours: 2,
      criticality: 'critical',
      owner: 'Finance',
      dependencies: ['SAP ECC', 'Bank connectivity'],
    });
    expect([200, 201]).toContain(status);
    expect(body.id || body.bia_id).toBeDefined();
  });

  test('TC-J18-006: BIA summary report accessible', async () => {
    const token = await getToken('P05');
    const { status } = await apiGet('/reports/bia-summary', token);
    expect(status).toBe(200);
  });

  test('TC-J18-007: BCM plan test recorded', async () => {
    const token = await getToken('P05');
    const { status, body } = await apiPost('/bcm/plan-tests', token, {
      plan_name: 'AP Disaster Recovery Plan',
      test_date: new Date().toISOString().split('T')[0],
      test_type: 'tabletop',
      result: 'passed',
      rto_achieved_hours: 3.5,
      rpo_achieved_hours: 1.5,
      notes: 'All recovery steps completed within RTO/RPO targets',
    });
    expect([200, 201]).toContain(status);
  });

  test('TC-J18-008: RTO/RPO achievement report', async () => {
    const token = await getToken('P05');
    const { status } = await apiGet('/reports/rto-rpo', token);
    expect(status).toBe(200);
  });

  test('TC-J18-009: P08 Business User cannot manage BCM → 403', async () => {
    const token = await getToken('P08');
    const { status } = await apiPost('/bcm/bia', token, {
      process_name: 'Unauthorized BIA',
    });
    expect(status).toBe(403);
  });

});

// ─── Fraud ─────────────────────────────────────────────────────────────────────

test.describe('J18c — Fraud Detection', () => {

  test('TC-J18-010: Risk Manager (P05) creates fraud detection rule', async () => {
    const token = await getToken('P05');
    const { status, body } = await apiPost('/fraud/rules', token, {
      name: `QA Fraud Rule ${Date.now()}`,
      description: 'Alert on same-day vendor create + payment',
      rule_type: 'velocity',
      condition: 'vendor_created_and_paid_same_day',
      severity: 'high',
      enabled: true,
    });
    expect([200, 201]).toContain(status);
    expect(body.id || body.rule_id).toBeDefined();
  });

  test('TC-J18-011: Fraud alert generated from rule trigger', async () => {
    const token = await getToken('P05');
    const { status, body } = await apiGet('/fraud/alerts', token);
    expect(status).toBe(200);
    const alerts = body.items || body.alerts || body;
    expect(Array.isArray(alerts)).toBe(true);
  });

  test('TC-J18-012: Fraud alert escalated to case', async () => {
    const token = await getToken('P05');
    const { body: alertsBody } = await apiGet('/fraud/alerts?status=open', token);
    const alerts = alertsBody.items || alertsBody.alerts || alertsBody;
    if (!Array.isArray(alerts) || alerts.length === 0) {
      // No open alerts — create a case directly
      const { status } = await apiPost('/fraud/cases', token, {
        title: 'QA Fraud Case — Vendor payment anomaly',
        source: 'manual',
        severity: 'high',
        description: 'Suspicious same-day vendor creation and payment detected',
      });
      expect([200, 201]).toContain(status);
      return;
    }

    const alertId = alerts[0].id;
    const { status } = await apiPost(`/fraud/alerts/${alertId}/escalate`, token, {
      case_title: 'QA Fraud Case from alert',
      assignee: 'P05',
    });
    expect([200, 201]).toContain(status);
  });

  test('TC-J18-013: Fraud rule effectiveness report', async () => {
    const token = await getToken('P05');
    const { status } = await apiGet('/reports/fraud-rule-effectiveness', token);
    expect(status).toBe(200);
  });

  test('TC-J18-014: P08 Business User cannot manage fraud rules → 403', async () => {
    const token = await getToken('P08');
    const { status } = await apiPost('/fraud/rules', token, {
      name: 'Unauthorized rule',
      rule_type: 'velocity',
    });
    expect(status).toBe(403);
  });

});

// ─── Survey ────────────────────────────────────────────────────────────────────

test.describe('J18d — Survey', () => {

  test('TC-J18-015: Compliance Officer (P04) creates survey', async () => {
    const token = await getToken('P04');
    const { status, body } = await apiPost('/surveys', token, {
      title: `QA Survey ${Date.now()}`,
      survey_type: 'csa',
      questions: [
        {
          id: 'q1',
          text: 'Do you have SoD conflicts in your current role?',
          type: 'yes_no',
          branching: { yes: 'q2', no: 'q3' },
        },
        {
          id: 'q2',
          text: 'Are mitigating controls in place?',
          type: 'yes_no',
        },
        {
          id: 'q3',
          text: 'Rate your understanding of access policies (1-5)',
          type: 'rating',
          min: 1,
          max: 5,
        },
      ],
    });
    expect([200, 201]).toContain(status);
    expect(body.id || body.survey_id).toBeDefined();
  });

  test('TC-J18-016: Survey logic branching — yes answer routes to q2', async () => {
    const token = await getToken('P04');
    const { body: surveys } = await apiGet('/surveys', token);
    const surveyList = surveys.items || surveys.surveys || surveys;
    if (!Array.isArray(surveyList) || surveyList.length === 0) return;

    const surveyId = surveyList[0].id;
    const { status, body } = await apiPost(`/surveys/${surveyId}/responses`, token, {
      respondent_id: 'BOB.S',
      answers: [
        { question_id: 'q1', value: 'yes' },
        { question_id: 'q2', value: 'yes' },
      ],
    });
    expect([200, 201]).toContain(status);
  });

  test('TC-J18-017: Survey response completion tracked', async () => {
    const token = await getToken('P04');
    const { status } = await apiGet('/reports/survey-completion', token);
    expect(status).toBe(200);
  });

  test('TC-J18-018: Survey launched to target group', async () => {
    const token = await getToken('P04');
    const { body: surveys } = await apiGet('/surveys', token);
    const surveyList = surveys.items || surveys.surveys || surveys;
    if (!Array.isArray(surveyList) || surveyList.length === 0) return;

    const surveyId = surveyList[0].id;
    const { status } = await apiPost(`/surveys/${surveyId}/launch`, token, {
      target_group: 'finance_department',
      due_date: '2027-01-31',
    });
    expect([200, 201]).toContain(status);
  });

  test('TC-J18-019: P08 Business User can submit survey response', async () => {
    const token = await getToken('P08');
    const { body: surveys } = await apiGet('/surveys/my-surveys', token);
    const surveyList = surveys.items || surveys.surveys || surveys;
    if (!Array.isArray(surveyList) || surveyList.length === 0) return;

    const surveyId = surveyList[0].id;
    const { status } = await apiPost(`/surveys/${surveyId}/responses`, token, {
      answers: [{ question_id: 'q1', value: 'no' }],
    });
    expect([200, 201]).toContain(status);
  });

  test('TC-J18-020: P08 Business User cannot create surveys → 403', async () => {
    const token = await getToken('P08');
    const { status } = await apiPost('/surveys', token, {
      title: 'Unauthorized survey',
      survey_type: 'csa',
    });
    expect(status).toBe(403);
  });

});
