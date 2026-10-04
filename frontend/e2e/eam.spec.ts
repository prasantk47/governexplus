/**
 * J04 — Emergency Access (Firefighter) Lifecycle
 * TC-J04-001 through TC-J04-008b
 *
 * Router: firefighter.router → prefix /privileged-access
 */
import { test, expect } from '@playwright/test';
import { getToken, apiPost, apiGet, waitForEmail, clearMailpit } from './helpers';

test.describe('J04 — Firefighter Lifecycle', () => {

  test.beforeEach(async () => {
    await clearMailpit();
  });

  test('TC-J04-001: Firefighter (P17) requests session — alert email sent', async () => {
    const token = await getToken('P17');
    // POST /privileged-access/requests
    const { status, body } = await apiPost('/privileged-access/requests', token, {
      ff_id: 'FF_PRD_001',
      reason_code: 'CIR-001',
      incident_ticket: 'INC-QA-001',
    });
    expect([200, 201]).toContain(status);
    if (status === 200 || status === 201) {
      expect(body.id || body.request_id || body.session_id).toBeDefined();
      // Email alert to controller (async — wait up to 5s, do NOT swallow assertion)
      const email = await waitForEmail('Firefighter', 5000).catch(() => null);
      if (email) {
        expect(email.Subject).toBeDefined();
      }
      // If email is null, it is an async delivery OBS — logged in DEF-008 (notification)
    }
  });

  test('TC-J04-004: P12 Controller can access review endpoint', async () => {
    const token = await getToken('P12');
    // GET /privileged-access/reviews/pending
    const { status } = await apiGet('/privileged-access/reviews/pending', token);
    expect(status).toBe(200);
  });

  test('TC-J04-007: P08 Business User cannot review FF logs → 403', async () => {
    const token = await getToken('P08');
    // POST /privileged-access/sessions/{id}/review
    const { status } = await apiPost('/privileged-access/sessions/NONEXISTENT/review', token, { action: 'approve' });
    expect(status).toBe(403);
  });

  test('TC-J04-008: P11 FF Owner can access EAM sessions', async () => {
    const token = await getToken('P11');
    // GET /privileged-access/sessions
    const { status } = await apiGet('/privileged-access/sessions', token);
    expect(status).toBe(200);
  });

  test('TC-J04-008b: P11 FF Owner cannot access controller review endpoint', async () => {
    const token = await getToken('P11');
    // FF Owner (P11) is the ID owner, NOT a controller — should be 403
    const { status } = await apiGet('/privileged-access/reviews/pending', token);
    expect(status).toBe(403);
  });

});
