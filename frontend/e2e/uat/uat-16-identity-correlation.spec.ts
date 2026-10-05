/**
 * UAT-16 · Identity Correlation · @P1
 * Persona: P13 (HR Manager)
 * Ref: qa/UAT_SCRIPT.md — Group D
 */
import { test, expect, loginAs, evidence, assertPageLoaded } from './uat-helpers';

const UAT = 'UAT-16';

test.describe('UAT-16 · Identity Correlation @P1', () => {
  test('Step 1-7: View identity correlation', async ({ page }) => {
    await loginAs(page, 'P13');

    await test.step('Navigate to Identity Correlation', async () => {
      await page.goto('/intelligence/identity');
      await page.waitForLoadState('networkidle').catch(() => {});
      await assertPageLoaded(page);
      await evidence(page, UAT, 1, 'identity-overview');
    });

    await test.step('View correlation stats', async () => {
      await evidence(page, UAT, 3, 'correlation-stats');
    });

    await test.step('Run correlation', async () => {
      const runBtn = page.getByRole('button', { name: /run|correlate|scan/i }).first();
      if (await runBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
        await runBtn.click();
        await page.waitForTimeout(3000);
      }
      await evidence(page, UAT, 4, 'correlation-results');
    });
  });
});
