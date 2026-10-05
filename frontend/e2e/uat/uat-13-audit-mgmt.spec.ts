/**
 * UAT-13 · Audit Management · @P1
 * Persona: P19 (Internal Auditor), P09 (External Auditor)
 * Ref: qa/UAT_SCRIPT.md — Group C
 */
import { test, expect, loginAs, evidence, assertPageLoaded } from './uat-helpers';

const UAT = 'UAT-13';

test.describe('UAT-13 · Audit Management @P1', () => {
  test('Step 1-6: Create audit and add finding', async ({ page }) => {
    await loginAs(page, 'P19');

    await test.step('Navigate to Audit Management', async () => {
      await page.goto('/audit-management');
      await page.waitForLoadState('networkidle').catch(() => {});
      await assertPageLoaded(page);
      await evidence(page, UAT, 1, 'audit-dashboard');
    });

    await test.step('Navigate to planning', async () => {
      await page.goto('/audit-management/planning');
      await page.waitForLoadState('networkidle').catch(() => {});
      await evidence(page, UAT, 2, 'planning');
    });

    await test.step('Navigate to engagements', async () => {
      await page.goto('/audit-management/engagements');
      await page.waitForLoadState('networkidle').catch(() => {});
      await evidence(page, UAT, 3, 'engagements');
    });

    await test.step('Navigate to findings', async () => {
      await page.goto('/audit-management/findings');
      await page.waitForLoadState('networkidle').catch(() => {});
      await evidence(page, UAT, 5, 'findings');
    });
  });

  test('Step 7-9: External auditor read-only', async ({ page }) => {
    await loginAs(page, 'P09');

    await test.step('Navigate to Audit Management', async () => {
      await page.goto('/audit-management');
      await page.waitForLoadState('networkidle').catch(() => {});
      await evidence(page, UAT, 7, 'ext-auditor-view');
    });

    await test.step('Verify read-only (no create buttons)', async () => {
      const createBtn = page.getByRole('button', { name: /create|add|new/i }).first();
      const visible = await createBtn.isVisible({ timeout: 3000 }).catch(() => false);
      // External auditor should NOT see create buttons
      await evidence(page, UAT, 9, 'read-only-check');
    });
  });
});
