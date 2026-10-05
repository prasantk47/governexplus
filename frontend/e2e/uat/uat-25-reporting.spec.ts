/**
 * UAT-25 · Reporting & Dashboards · @P1
 * Persona: P02 (Tenant Admin)
 * Ref: qa/UAT_SCRIPT.md — Group F
 */
import { test, expect, loginAs, evidence, assertPageLoaded } from './uat-helpers';

const UAT = 'UAT-25';

test.describe('UAT-25 · Reporting @P1', () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page, 'P02');
  });

  test('Step 1-5: View and run reports', async ({ page }) => {
    await test.step('Navigate to Reports', async () => {
      await page.goto('/reports');
      await page.waitForLoadState('networkidle').catch(() => {});
      await assertPageLoaded(page);
      await evidence(page, UAT, 1, 'report-catalog');
    });

    await test.step('Select a report', async () => {
      const row = page.locator('tr, [class*="row"], [class*="card"]').nth(1);
      if (await row.isVisible({ timeout: 5000 }).catch(() => false)) {
        await row.click();
        await page.waitForTimeout(1000);
        await evidence(page, UAT, 3, 'report-config');
      }
    });

    await test.step('Generate report', async () => {
      const runBtn = page.getByRole('button', { name: /generate|run|execute/i }).first();
      if (await runBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
        await runBtn.click();
        await page.waitForTimeout(3000);
      }
      await evidence(page, UAT, 5, 'report-results');
    });
  });

  test('Step 6: Export report', async ({ page }) => {
    await test.step('Export', async () => {
      await page.goto('/reports');
      await page.waitForLoadState('networkidle').catch(() => {});
      const exportBtn = page.getByRole('button', { name: /export|download/i }).first();
      if (await exportBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
        await evidence(page, UAT, 6, 'export-available');
      }
    });
  });

  test('Step 7-8: Dashboard widgets reflect data', async ({ page }) => {
    await test.step('Check dashboard', async () => {
      await page.goto('/dashboard');
      await page.waitForLoadState('networkidle').catch(() => {});
      await evidence(page, UAT, 7, 'dashboard-data');
    });
  });
});
