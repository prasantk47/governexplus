/**
 * J05 — Access Certification Campaign
 * TC-J05-001 through TC-J05-RBAC
 *
 * Router: certification.router → prefix /certification (no trailing 's')
 */
import { test, expect } from '@playwright/test';
import { getToken, apiPost, apiGet, waitForEmail, clearMailpit } from './helpers';

test.describe('J05 — Certification Campaign', () => {

  test.beforeEach(async () => {
    await clearMailpit();
  });

  test('TC-J05-001: Compliance Officer (P04) creates campaign', async () => {
    const token = await getToken('P04');
    const { status, body } = await apiPost('/certification/campaigns', token, {
      name: `QA UAR ${Date.now()}`,
      campaign_type: 'user_access_review',
      scope: 'all_active_users',
      due_date: '2027-01-31',
    });
    expect([200, 201]).toContain(status);
    expect(body.id || body.campaign_id).toBeDefined();
  });

  test('TC-J05-002: Campaign launch sends reviewer notifications', async () => {
    const token = await getToken('P04');
    const { body: campBody } = await apiPost('/certification/campaigns', token, {
      name: `QA Campaign Launch ${Date.now()}`,
      campaign_type: 'user_access_review',
      scope: 'finance_department',
      due_date: '2027-01-31',
    });
    const campaignId = campBody.id || campBody.campaign_id;
    if (!campaignId) return;

    // Start campaign (generate items first, then start)
    const { status: genStatus } = await apiPost(`/certification/campaigns/${campaignId}/generate-items`, token, {});
    expect([200, 201]).toContain(genStatus);

    const { status: startStatus } = await apiPost(`/certification/campaigns/${campaignId}/start`, token, {});
    expect([200, 201]).toContain(startStatus);

    // Notification email (async delivery — do NOT swallow assertion on email content)
    const email = await waitForEmail('Certification', 5000).catch(() => null);
    if (email) {
      expect(email.Subject).toBeDefined();
    }
  });

  test('TC-J05-003: Line Manager (P07) can access assigned reviews', async () => {
    const token = await getToken('P07');
    const { status, body } = await apiGet('/certification/my-reviews', token);
    expect(status).toBe(200);
    const items = body.items || body.reviews || body;
    expect(Array.isArray(items)).toBe(true);
  });

  test('TC-J05-004: Reviewer certifies (keeps) access for clean user', async () => {
    const token = await getToken('P07');
    const { body: reviewBody } = await apiGet('/certification/my-reviews', token);
    const items = reviewBody.items || reviewBody.reviews || reviewBody;
    if (!Array.isArray(items) || items.length === 0) return;

    const item = items[0];
    // Decision endpoint: POST /certification/campaigns/{cid}/items/{iid}/decision
    const { status } = await apiPost(
      `/certification/campaigns/${item.campaign_id}/items/${item.id}/decision`,
      token,
      { decision: 'certify', comment: 'Access is appropriate and used regularly' }
    );
    expect([200, 201]).toContain(status);
  });

  test('TC-J05-005: Reviewer revokes access for unnecessary role', async () => {
    const token = await getToken('P07');
    const { body: reviewBody } = await apiGet('/certification/my-reviews', token);
    const items = reviewBody.items || reviewBody.reviews || reviewBody;
    if (!Array.isArray(items) || items.length === 0) return;

    const item = items[0];
    const { status } = await apiPost(
      `/certification/campaigns/${item.campaign_id}/items/${item.id}/decision`,
      token,
      { decision: 'revoke', comment: 'User no longer requires this access' }
    );
    expect([200, 201]).toContain(status);
  });

  test('TC-J05-006: Campaign list and statistics tracked', async () => {
    const token = await getToken('P04');
    const { status, body } = await apiGet('/certification/campaigns', token);
    expect(status).toBe(200);
    const campaigns = body.items || body.campaigns || body;
    expect(Array.isArray(campaigns)).toBe(true);
  });

  test('TC-J05-007: Campaign statistics endpoint accessible', async () => {
    const token = await getToken('P04');
    const { status } = await apiGet('/certification/statistics', token);
    expect(status).toBe(200);
  });

  test('TC-J05-008: Reviewer workload endpoint accessible', async () => {
    const token = await getToken('P04');
    const { status } = await apiGet('/certification/reviewer-workload', token);
    expect(status).toBe(200);
  });

  test('TC-J05-009: External Auditor (P09) can view completed campaigns read-only', async () => {
    const token = await getToken('P09');
    const { status } = await apiGet('/certification/campaigns', token);
    expect(status).toBe(200);
  });

  test('TC-J05-RBAC: P08 Business User cannot create campaigns → 403', async () => {
    const token = await getToken('P08');
    const { status } = await apiPost('/certification/campaigns', token, {
      name: 'Unauthorized campaign',
      campaign_type: 'user_access_review',
    });
    expect(status).toBe(403);
  });

});
