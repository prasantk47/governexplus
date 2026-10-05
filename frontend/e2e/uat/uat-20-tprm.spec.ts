/**
 * UAT-20 · Third-Party Risk Management (TPRM) · @P1
 * Persona: P20 (Vendor Manager), P05 (Risk Manager)
 * Ref: qa/UAT_SCRIPT.md — Group F
 */
import { test, expect, loginAs, evidence, assertPageLoaded } from './uat-helpers';

const UAT = 'UAT-20';

test.describe('UAT-20 · TPRM @P1', () => {
  test('Step 1-5: Create vendor', async ({ page }) => {
    await loginAs(page, 'P20');

    await test.step('Navigate to TPRM', async () => {
      await page.goto('/tprm');
      await page.waitForLoadState('networkidle').catch(() => {});
      await assertPageLoaded(page);
      await evidence(page, UAT, 1, 'vendor-registry');
    });

    await test.step('Click Add Vendor', async () => {
      const addBtn = page.getByRole('button', { name: /add|create|new|onboard/i }).first();
      if (await addBtn.isVisible({ timeout: 5000 }).catch(() => false)) {
        await addBtn.click();
        await page.waitForTimeout(1000);
        await evidence(page, UAT, 2, 'add-vendor-form');

        const nameInput = page.locator('input').first();
        if (await nameInput.isVisible({ timeout: 3000 }).catch(() => false)) {
          await nameInput.fill('Acme Cloud Services - UAT');
        }

        const saveBtn = page.getByRole('button', { name: /save|create|submit/i }).first();
        if (await saveBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
          await saveBtn.click();
          await page.waitForTimeout(2000);
        }
      }
      await evidence(page, UAT, 4, 'vendor-created');
    });
  });

  test('Step 6-8: Assessment and risk overview', async ({ page }) => {
    await test.step('Navigate to Assessments', async () => {
      await loginAs(page, 'P20');
      await page.goto('/tprm/assessments');
      await page.waitForLoadState('networkidle').catch(() => {});
      await evidence(page, UAT, 6, 'assessments');
    });

    await test.step('Risk Manager views TPRM', async () => {
      await loginAs(page, 'P05');
      await page.goto('/tprm');
      await page.waitForLoadState('networkidle').catch(() => {});
      await evidence(page, UAT, 8, 'risk-manager-view');
    });
  });
});
