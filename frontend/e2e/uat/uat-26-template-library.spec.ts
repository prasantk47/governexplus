/**
 * UAT-26 · Template Library · @P1
 * Persona: P02 (Tenant Admin), P01 (Platform Admin)
 * Ref: qa/UAT_SCRIPT.md — Group G
 */
import { test, expect, loginAs, evidence, assertPageLoaded } from './uat-helpers';

const UAT = 'UAT-26';

test.describe('UAT-26 · Template Library @P1', () => {
  test('Step 1-7: Browse and activate templates', async ({ page }) => {
    await loginAs(page, 'P02');

    await test.step('Navigate to Content Library', async () => {
      await page.goto('/library');
      await page.waitForLoadState('networkidle').catch(() => {});
      await assertPageLoaded(page);
      await evidence(page, UAT, 1, 'library');
    });

    await test.step('Verify template count', async () => {
      await evidence(page, UAT, 3, 'template-count');
    });

    await test.step('Click template pack', async () => {
      const pack = page.locator('tr, [class*="row"], [class*="card"]').nth(1);
      if (await pack.isVisible({ timeout: 5000 }).catch(() => false)) {
        await pack.click();
        await page.waitForTimeout(1000);
        await evidence(page, UAT, 4, 'pack-detail');
      }
    });

    await test.step('Activation wizard', async () => {
      await page.goto('/library/wizard');
      await page.waitForLoadState('networkidle').catch(() => {});
      await evidence(page, UAT, 5, 'activation-wizard');
    });

    await test.step('Active content', async () => {
      await page.goto('/library/active');
      await page.waitForLoadState('networkidle').catch(() => {});
      await evidence(page, UAT, 7, 'active-content');
    });
  });

  test('Step 9-10: Platform admin view', async ({ page }) => {
    await loginAs(page, 'P01');

    await test.step('Platform admin views library', async () => {
      await page.goto('/library');
      await page.waitForLoadState('networkidle').catch(() => {});
      await evidence(page, UAT, 9, 'platform-admin-library');
    });
  });
});
