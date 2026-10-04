/**
 * TC-PAGE — Full Page/Action Sweep
 * TC-PAGE-001 through TC-PAGE-024
 *
 * Uses confirmed router prefixes from api/main.py:
 *   /certification/*        certification.router
 *   /privileged-access/*    firefighter.router
 *   /risk-intelligence/*    ara.router
 *   /risk-management/*      risk_mgmt.router
 *   /role-studio/*          role_engineering.router
 *   /process-control/*      process_ctrl.router
 *   /audit-management/*     audit_mgmt.router
 *   /risk/*                 risk_analysis.router (SoD violations, rules, analyze)
 *   /mitigation/*           mitigation.router
 */
import { test, expect } from '@playwright/test';
import { getToken, apiGet, apiPost } from './helpers';

// TC-PAGE-001: Dashboard
test('TC-PAGE-001: Dashboard stats endpoint returns data', async () => {
  const token = await getToken('P02');
  const { status } = await apiGet('/dashboard', token);
  expect(status).toBe(200);
});

// TC-PAGE-002: User Management
test('TC-PAGE-002: User list accessible to IT Security', async () => {
  const token = await getToken('P06');
  const { status, body } = await apiGet('/users', token);
  expect(status).toBe(200);
  const users = body.items || body.users || body;
  expect(Array.isArray(users)).toBe(true);
  expect(users.length).toBeGreaterThan(0);
});

// TC-PAGE-003: ARA / SoD — risk violations list
test('TC-PAGE-003: ARA violations list accessible', async () => {
  const token = await getToken('P06');
  // risk_analysis.router has GET /violations under prefix /risk
  const { status } = await apiGet('/risk/violations', token);
  expect(status).toBe(200);
});

// TC-PAGE-004: Access Request Management
test('TC-PAGE-004: ARM access request list', async () => {
  const token = await getToken('P06');
  const { status } = await apiGet('/access-requests', token);
  expect(status).toBe(200);
});

// TC-PAGE-005: EAM / Firefighter sessions
test('TC-PAGE-005: EAM session list accessible', async () => {
  const token = await getToken('P11');
  const { status } = await apiGet('/privileged-access/sessions', token);
  expect(status).toBe(200);
});

// TC-PAGE-006: Access Certification
test('TC-PAGE-006: Certification campaigns list', async () => {
  const token = await getToken('P04');
  const { status } = await apiGet('/certification/campaigns', token);
  expect(status).toBe(200);
});

// TC-PAGE-007: JML events
test('TC-PAGE-007: JML events list accessible', async () => {
  const token = await getToken('P13');
  const { status } = await apiGet('/jml/events', token);
  expect(status).toBe(200);
});

// TC-PAGE-008: BRM — role catalog
test('TC-PAGE-008: Role catalog accessible', async () => {
  const token = await getToken('P06');
  const { status } = await apiGet('/role-studio/roles', token);
  expect(status).toBe(200);
});

// TC-PAGE-009: Risk Management
test('TC-PAGE-009: Risk register accessible', async () => {
  const token = await getToken('P05');
  const { status } = await apiGet('/risk-management/risks', token);
  expect(status).toBe(200);
});

// TC-PAGE-010: Process Controls
test('TC-PAGE-010: Controls inventory accessible', async () => {
  const token = await getToken('P10');
  const { status } = await apiGet('/process-control/controls', token);
  expect(status).toBe(200);
});

// TC-PAGE-011: Audit Management
test('TC-PAGE-011: Audit plans list accessible', async () => {
  const token = await getToken('P19');
  const { status } = await apiGet('/audit-management/plans', token);
  expect(status).toBe(200);
});

// TC-PAGE-012: TPRM
test('TC-PAGE-012: Vendor inventory accessible', async () => {
  const token = await getToken('P20');
  const { status } = await apiGet('/tprm/vendors', token);
  expect(status).toBe(200);
});

// TC-PAGE-013: BCM
test('TC-PAGE-013: BCM BIA list accessible', async () => {
  const token = await getToken('P05');
  const { status } = await apiGet('/bcm/bia', token);
  expect(status).toBe(200);
});

// TC-PAGE-014: Fraud
test('TC-PAGE-014: Fraud rules list accessible', async () => {
  const token = await getToken('P05');
  const { status } = await apiGet('/fraud/rules', token);
  expect(status).toBe(200);
});

// TC-PAGE-015: Survey
test('TC-PAGE-015: Survey list accessible', async () => {
  const token = await getToken('P04');
  const { status } = await apiGet('/surveys', token);
  expect(status).toBe(200);
});

// TC-PAGE-016: Template Library
test('TC-PAGE-016: Library items list accessible', async () => {
  const token = await getToken('P02');
  const { status } = await apiGet('/library/items', token);
  expect(status).toBe(200);
});

// TC-PAGE-017: Report schedules
test('TC-PAGE-017: Report schedules list accessible', async () => {
  const token = await getToken('P04');
  const { status } = await apiGet('/reporting/schedules', token);
  expect(status).toBe(200);
});

// TC-PAGE-018: Admin Connectors
test('TC-PAGE-018: Connectors list accessible to Platform Admin', async () => {
  const token = await getToken('P01');
  const { status } = await apiGet('/integrations/connectors', token);
  expect(status).toBe(200);
});

// TC-PAGE-019: Audit Log
test('TC-PAGE-019: Audit log accessible to CISO', async () => {
  const token = await getToken('P03');
  const { status } = await apiGet('/audit/logs', token);
  expect(status).toBe(200);
});

// TC-PAGE-020: Mitigation Monitor
test('TC-PAGE-020: Mitigation Monitor (P18) accesses mitigation controls', async () => {
  const token = await getToken('P18');
  const { status } = await apiGet('/risk-intelligence/mitigation/controls', token);
  expect(status).toBe(200);
});

// TC-PAGE-021: Internal Auditor
test('TC-PAGE-021: Internal Auditor (P19) reads audit engagements', async () => {
  const token = await getToken('P19');
  const { status } = await apiGet('/audit-management/engagements', token);
  expect(status).toBe(200);
});

// TC-PAGE-022: Line Manager approval queue
test('TC-PAGE-022: Line Manager (P07) accesses approval queue', async () => {
  const token = await getToken('P07');
  const { status } = await apiGet('/access-requests/approvals/pending', token);
  expect(status).toBe(200);
});

// TC-PAGE-023: Read-Only viewer denied any write
test('TC-PAGE-023: Read-Only (P16) denied write action', async () => {
  const token = await getToken('P16');
  const { status } = await apiPost('/risk-management/risks', token, {
    name: 'Probe',
    category: 'operational',
    likelihood: 1,
    impact: 1,
  });
  expect(status).toBe(403);
});

// TC-PAGE-024: Whistleblower public submit — no auth needed
test('TC-PAGE-024: Whistleblower submit — no auth needed', async () => {
  const res = await fetch('http://localhost:9000/whistleblower/submit', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-Tenant-ID': 'qa-tenant-001' },
    body: JSON.stringify({
      category: 'other',
      description: 'Page sweep probe',
      anonymous: true,
    }),
  });
  expect([200, 201]).toContain(res.status);
});
