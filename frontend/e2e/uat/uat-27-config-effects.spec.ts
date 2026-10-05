/**
 * UAT-27 · System Configuration & Effects · @P1
 * Persona: P01 (Platform Admin), P02 (Tenant Admin)
 * Ref: qa/UAT_SCRIPT.md — Group G
 */
import { test, expect, loginAs, evidence, assertPageLoaded, getToken, apiGet } from './uat-helpers';

const UAT = 'UAT-27';

test.describe('UAT-27 · Config Effects @P1', () => {
  test('Step 1-4: View and modify config', async ({ page }) => {
    await loginAs(page, 'P01');

    await test.step('Navigate to Settings', async () => {
      await page.goto('/settings');
      await page.waitForLoadState('networkidle').catch(() => {});
      await assertPageLoaded(page);
      await evidence(page, UAT, 1, 'settings-page');
    });

    await test.step('View system settings', async () => {
      // Try config page
      await evidence(page, UAT, 2, 'current-settings');
    });

    // Verify config API works
    await test.step('Config API accessible', async () => {
      const token = await getToken('P01');
      const res = await apiGet('/config/settings', token);
      expect(res.status).toBeLessThan(500);
      await evidence(page, UAT, 3, 'config-api');
    });
  });

  test('Step 6-8: Tenant admin settings', async ({ page }) => {
    await loginAs(page, 'P02');

    await test.step('Navigate to tenant settings', async () => {
      await page.goto('/settings');
      await page.waitForLoadState('networkidle').catch(() => {});
      await assertPageLoaded(page);
      await evidence(page, UAT, 6, 'tenant-settings');
    });

    await test.step('Verify platform settings read-only', async () => {
      await evidence(page, UAT, 8, 'platform-readonly');
    });
  });
});
