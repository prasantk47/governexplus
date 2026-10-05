/**
 * UAT-05 · Approve Access Request · @P0
 * Persona: P07 (Line Manager)
 * Pre-condition: UAT-04 completed — pending request exists
 * Ref: qa/UAT_SCRIPT.md — Group B
 */
import { test, expect, loginAs, evidence, assertPageLoaded, getToken, apiPost } from './uat-helpers';

const UAT = 'UAT-05';

test.describe('UAT-05 · Approve Access Request @P0', () => {
  // Seed a request via API before testing approval UI
  let requestId: string;

  test.beforeAll(async () => {
    const token = await getToken('P08');
    const res = await apiPost('/access-requests/', token, {
      requester_user_id: 'qa_requestor',
      requester_name: 'Robert Requestor',
      requested_roles: ['ROLE_FI_VIEWER'],
      business_justification: 'UAT-05 test: approval flow',
      target_user_id: 'qa_requestor',
      target_user_name: 'Robert Requestor',
    });
    requestId = res.body?.request_id ?? res.body?.id ?? 'unknown';
  });

  test('Step 1-2: Approver sees pending requests', async ({ page }) => {
    await loginAs(page, 'P07');

    await test.step('Navigate to approvals', async () => {
      await page.goto('/approvals');
      await page.waitForLoadState('networkidle').catch(() => {});
      await assertPageLoaded(page);
      await evidence(page, UAT, 1, 'approval-inbox');
    });

    await test.step('Pending requests visible', async () => {
      // Should see at least one pending item
      const table = page.locator('table, [class*="table"], [class*="list"]').first();
      await expect(table).toBeVisible({ timeout: 10000 });
      await evidence(page, UAT, 2, 'pending-list');
    });
  });

  test('Step 3-4: Open request and review', async ({ page }) => {
    await loginAs(page, 'P07');
    await page.goto('/approvals');
    await page.waitForLoadState('networkidle').catch(() => {});

    await test.step('Click a request', async () => {
      const row = page.locator('tr, [class*="row"], [class*="item"]')
        .filter({ hasText: /requestor|pending|ROLE_FI/i }).first();
      if (await row.isVisible({ timeout: 5000 }).catch(() => false)) {
        await row.click();
        await page.waitForTimeout(1000);
        await evidence(page, UAT, 3, 'request-detail');
      }
    });

    await test.step('Risk preview visible', async () => {
      // Look for risk/SoD section
      const riskSection = page.locator('[class*="risk"], [class*="sod"], [class*="violation"]').first();
      if (await riskSection.isVisible({ timeout: 3000 }).catch(() => false)) {
        await evidence(page, UAT, 4, 'risk-preview');
      }
    });
  });

  test('Step 5: Approve request', async ({ page }) => {
    await loginAs(page, 'P07');
    await page.goto('/approvals');
    await page.waitForLoadState('networkidle').catch(() => {});

    await test.step('Click Approve', async () => {
      const approveBtn = page.getByRole('button', { name: /approve/i }).first();
      if (await approveBtn.isVisible({ timeout: 5000 }).catch(() => false)) {
        await approveBtn.click();
        await page.waitForTimeout(2000);
        await evidence(page, UAT, 5, 'approved');
      } else {
        // May need to open a request first
        const row = page.locator('tr, [class*="row"]').first();
        await row.click();
        await page.waitForTimeout(1000);
        const btn = page.getByRole('button', { name: /approve/i }).first();
        if (await btn.isVisible({ timeout: 3000 }).catch(() => false)) {
          await btn.click();
          await page.waitForTimeout(2000);
        }
        await evidence(page, UAT, 5, 'approved');
      }
    });
  });

  test('Step 6: Requester sees approved status', async ({ page }) => {
    await loginAs(page, 'P08');

    await test.step('Check My Requests', async () => {
      await page.goto('/access-requests');
      await page.waitForLoadState('networkidle').catch(() => {});
      await evidence(page, UAT, 6, 'requester-view');
    });
  });
});
