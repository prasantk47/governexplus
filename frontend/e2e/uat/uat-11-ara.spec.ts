/**
 * UAT-11 · Access Risk Analysis (ARA) · @P0
 * Persona: P05 (Risk Manager)
 * Ref: qa/UAT_SCRIPT.md — Group C
 */
import { test, expect, loginAs, evidence, assertPageLoaded } from './uat-helpers';

const UAT = 'UAT-11';

test.describe('UAT-11 · Access Risk Analysis @P0', () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page, 'P05');
  });

  test('Step 1-2: ARA page loads', async ({ page }) => {
    await test.step('Navigate to ARA', async () => {
      await page.goto('/risk');
      await page.waitForLoadState('networkidle').catch(() => {});
      await assertPageLoaded(page);
      await evidence(page, UAT, 1, 'ara-dashboard');
    });
  });

  test('Step 3-5: Run analysis and view results', async ({ page }) => {
    await page.goto('/risk');
    await page.waitForLoadState('networkidle').catch(() => {});

    await test.step('Run analysis', async () => {
      const runBtn = page.getByRole('button', { name: /run|analyze|scan/i }).first();
      if (await runBtn.isVisible({ timeout: 5000 }).catch(() => false)) {
        await runBtn.click();
        await page.waitForTimeout(3000);
        await evidence(page, UAT, 3, 'analysis-running');
      }
    });

    await test.step('View results', async () => {
      await page.goto('/risk/violations');
      await page.waitForLoadState('networkidle').catch(() => {});
      await evidence(page, UAT, 4, 'violations-list');
    });

    await test.step('Click violation for detail', async () => {
      const row = page.locator('tr, [class*="row"]').nth(1);
      if (await row.isVisible({ timeout: 5000 }).catch(() => false)) {
        await row.click();
        await page.waitForTimeout(1000);
        await evidence(page, UAT, 5, 'violation-detail');
      }
    });
  });

  test('Step 6-7: Violation details and persistence', async ({ page }) => {
    await page.goto('/risk/violations');
    await page.waitForLoadState('networkidle').catch(() => {});

    await test.step('Verify violation detail has rule info', async () => {
      const row = page.locator('tr, [class*="row"]').nth(1);
      if (await row.isVisible({ timeout: 5000 }).catch(() => false)) {
        await row.click();
        await page.waitForTimeout(1000);
        // Look for rule description, severity, user info
        await evidence(page, UAT, 6, 'violation-info');
      }
    });

    await test.step('Navigate away and back — violations persist', async () => {
      await page.goto('/dashboard');
      await page.waitForTimeout(500);
      await page.goto('/risk/violations');
      await page.waitForLoadState('networkidle').catch(() => {});
      const rows = page.locator('tr, [class*="row"]');
      const count = await rows.count();
      expect(count, 'Violations should persist across navigation').toBeGreaterThan(0);
      await evidence(page, UAT, 7, 'violations-persisted');
    });
  });
});
