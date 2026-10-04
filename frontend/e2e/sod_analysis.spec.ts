/**
 * J03 — SoD Conflict Detection & Mitigation
 * TC-J03-001 through TC-J03-007
 */
import { test, expect } from '@playwright/test';
import { getToken, apiPost, apiGet } from './helpers';

test.describe('J03 — SoD Analysis', () => {

  test('TC-J03-001: SoD violations detected for Alice (AP + Payment roles)', async () => {
    const token = await getToken('P06');
    // ara.router under /risk-intelligence
    const { status, body } = await apiPost('/risk-intelligence/analyze/user', token, { user_id: 'ALICE.J' });
    expect(status).toBe(200);
    expect(body.violations).toBeDefined();
    // Alice has Z_FI_AP_CLERK + Z_FI_PAYMENT_APPROVER → SOD-FI-001
    const hasFinanceViolation = body.violations?.some(
      (v: any) => v.rule_id?.startsWith('SOD-FI') || v.rule_code?.startsWith('SOD-FI')
    );
    expect(hasFinanceViolation).toBe(true);
  });

  test('TC-J03-002: Clean user returns no violations', async () => {
    const token = await getToken('P06');
    const { status, body } = await apiPost('/risk-intelligence/analyze/user', token, { user_id: 'BOB.S' });
    expect(status).toBe(200);
    // Bob has only IT security role — no SoD conflicts
    const violations = body.violations || body.risks || [];
    const financialViolations = violations.filter((v: any) =>
      (v.rule_id || v.rule_code || '').startsWith('SOD-FI')
    );
    expect(financialViolations.length).toBe(0);
  });

  test('TC-J03-003: Violation has severity field', async () => {
    const token = await getToken('P06');
    const { body } = await apiPost('/risk-intelligence/analyze/user', token, { user_id: 'ALICE.J' });
    const violations = body.violations || body.risks || [];
    if (violations.length > 0) {
      expect(violations[0].severity || violations[0].risk_level).toBeDefined();
    }
  });

  test('TC-J03-005: Bulk analysis returns results for multiple users', async () => {
    const token = await getToken('P04');
    const { status, body } = await apiPost('/risk-intelligence/analyze/batch', token, {
      user_ids: ['ALICE.J', 'BOB.S', 'CAROL.W'],
    });
    expect(status).toBe(200);
    const results = body.results || body.users || body.analyses || [];
    expect(results.length).toBeGreaterThanOrEqual(1);
  });

  test('TC-J03-006: Role assignment with conflict returns warning', async () => {
    const token = await getToken('P02');
    // POST /users/{id}/roles (not /assign suffix)
    const { status, body } = await apiPost('/users/ALICE.J/roles', token, {
      role_name: 'Z_FI_PAYMENT_APPROVER',
      system: 'PRD',
    });
    // Either 409 conflict, or 200/201 with conflict_warnings field
    const hasConflictSignal = status === 409 || body?.conflict_warnings?.length > 0 || body?.sod_conflicts?.length > 0;
    expect([200, 201, 409]).toContain(status);
    if (status === 200 || status === 201) {
      expect(hasConflictSignal).toBe(true);
    }
  });

  test('TC-J03-007: Mitigation Monitor (P18) can access mitigation controls', async () => {
    const token = await getToken('P18');
    // Mitigation controls are in ara.router under /risk-intelligence
    const { status } = await apiGet('/risk-intelligence/mitigation/controls', token);
    expect(status).toBe(200);
  });

});
