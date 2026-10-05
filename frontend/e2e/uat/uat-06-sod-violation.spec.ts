/**
 * UAT-06 · Access Request with SoD Violation · @P0
 * Persona: P08 (Business User) then P06 (IT Security Admin)
 * Ref: qa/UAT_SCRIPT.md — Group B
 */
import { test, expect, loginAs, evidence, assertPageLoaded, getToken, apiGet } from './uat-helpers';

const UAT = 'UAT-06';

test.describe('UAT-06 · SoD Violation in Access Request @P0', () => {
  test('Step 1-4: Request role with potential SoD conflict', async ({ page }) => {
    await loginAs(page, 'P08');

    await test.step('Navigate to request access', async () => {
      await page.goto('/access-requests/new');
      await page.waitForLoadState('networkidle').catch(() => {});
      await assertPageLoaded(page);
      await evidence(page, UAT, 1, 'request-page');
    });

    await test.step('Select a role that may conflict', async () => {
      // Try to find and select a role
      const search = page.locator('input[placeholder*="search" i], input[type="search"]').first();
      if (await search.isVisible({ timeout: 3000 }).catch(() => false)) {
        await search.fill('ROLE_FI');
        await page.waitForTimeout(1000);
      }
      await evidence(page, UAT, 2, 'role-selected');
    });

    await test.step('Check for SoD warning', async () => {
      // Look for any risk/SoD/conflict warning
      const warning = page.locator('[class*="warning"], [class*="alert"], [class*="conflict"], [class*="sod"], [class*="risk"]')
        .filter({ hasText: /conflict|violation|risk|sod|segregation/i }).first();
      if (await warning.isVisible({ timeout: 5000 }).catch(() => false)) {
        await evidence(page, UAT, 3, 'sod-warning');
      } else {
        await evidence(page, UAT, 3, 'no-sod-warning');
      }
    });

    await test.step('Submit despite warning (or note block)', async () => {
      const submitBtn = page.getByRole('button', { name: /submit|request/i }).first();
      if (await submitBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
        await submitBtn.click();
        await page.waitForTimeout(2000);
      }
      await evidence(page, UAT, 4, 'submitted-or-blocked');
    });
  });

  test('Step 5-6: IT Security views violations', async ({ page }) => {
    await loginAs(page, 'P06');

    await test.step('Navigate to SoD Violations', async () => {
      await page.goto('/risk/violations');
      await page.waitForLoadState('networkidle').catch(() => {});
      await assertPageLoaded(page);
      await evidence(page, UAT, 5, 'violations-list');
    });

    await test.step('View violation details', async () => {
      const row = page.locator('tr, [class*="row"], [class*="item"]').first();
      if (await row.isVisible({ timeout: 5000 }).catch(() => false)) {
        await row.click();
        await page.waitForTimeout(1000);
        await evidence(page, UAT, 6, 'violation-detail');
      }
    });
  });
});
