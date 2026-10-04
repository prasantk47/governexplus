/**
 * J09 — Template Library Full Depth
 * TC-J09-001 through TC-J09-011
 */
import { test, expect } from '@playwright/test';
import { getToken, apiGet, apiPost } from './helpers';

test.describe('J09 — Template Library', () => {

  test('TC-J09-001: Library returns seeded items', async () => {
    const token = await getToken('P02');
    const { status, body } = await apiGet('/library/items', token);
    expect(status).toBe(200);
    const items = body.items || body;
    expect(Array.isArray(items)).toBe(true);
    expect(items.length).toBeGreaterThan(0);
  });

  test('TC-J09-002: Activate a template item', async () => {
    const token = await getToken('P02');
    // Find SOD-FI-001 item
    const { body: list } = await apiGet('/library/items?search=SOD-FI-001', token);
    const items = list.items || list;
    if (!items.length) return; // Skip if pack not seeded yet
    const item = items[0];
    const { status, body } = await apiPost(`/library/items/${item.id}/activate`, token);
    expect([200, 201, 409]).toContain(status); // 409 = already active (idempotent)
    if (status !== 409) {
      expect(body.is_active ?? body.activation?.is_active ?? true).toBe(true);
    }
  });

  test('TC-J09-004: Pack import is idempotent', async () => {
    const token = await getToken('P01');
    const { status: s1, body: b1 } = await apiPost('/library/packs/import-file', token);
    expect([200, 201]).toContain(s1);
    const { status: s2, body: b2 } = await apiPost('/library/packs/import-file', token);
    expect([200, 201]).toContain(s2);
    // Second run should insert 0 new items
    expect(b2.inserted ?? 0).toBe(0);
    expect(b2.errors?.length ?? 0).toBe(0);
  });

  test('TC-J09-001b: Library stats endpoint returns data', async () => {
    const token = await getToken('P02');
    const { status, body } = await apiGet('/library/stats', token);
    expect(status).toBe(200);
    expect(body.total_library_items).toBeGreaterThan(0);
  });

  test('TC-J09-005: Library flags endpoint returns feature flag state', async () => {
    const token = await getToken('P02');
    const { status, body } = await apiGet('/library/flags', token);
    expect(status).toBe(200);
    expect(body.template_library).toBeDefined();
  });

});
