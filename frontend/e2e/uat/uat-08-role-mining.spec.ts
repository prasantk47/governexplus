/**
 * UAT-08 · Role Mining · @P1
 * Persona: P21 (Role Owner)
 * Ref: qa/UAT_SCRIPT.md — Group B
 */
import { test, expect, loginAs, evidence, assertPageLoaded } from './uat-helpers';

const UAT = 'UAT-08';

test.describe('UAT-08 · Role Mining @P1', () => {
  test('Step 1-6: Run role mining', async ({ page }) => {
    await loginAs(page, 'P21');

    await test.step('Navigate to Role Mining', async () => {
      await page.goto('/intelligence/role-intelligence');
      await page.waitForLoadState('networkidle').catch(() => {});
      await assertPageLoaded(page);
      await evidence(page, UAT, 1, 'role-mining');
    });

    await test.step('Configure and run mining', async () => {
      const runBtn = page.getByRole('button', { name: /run|mine|analyze/i }).first();
      if (await runBtn.isVisible({ timeout: 5000 }).catch(() => false)) {
        await runBtn.click();
        await page.waitForTimeout(3000);
      }
      await evidence(page, UAT, 3, 'mining-results');
    });
  });
});
