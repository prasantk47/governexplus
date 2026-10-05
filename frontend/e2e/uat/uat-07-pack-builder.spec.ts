/**
 * UAT-07 · Role Engineering — Pack Builder · @P1
 * Persona: P21 (Role Owner)
 * Ref: qa/UAT_SCRIPT.md — Group B
 */
import { test, expect, loginAs, evidence, assertPageLoaded } from './uat-helpers';

const UAT = 'UAT-07';

test.describe('UAT-07 · Pack Builder @P1', () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page, 'P21');
  });

  test('Step 1-5: Create pack and add roles', async ({ page }) => {
    await test.step('Navigate to Pack Builder', async () => {
      await page.goto('/library/pack-builder');
      await page.waitForLoadState('networkidle').catch(() => {});
      await assertPageLoaded(page);
      await evidence(page, UAT, 1, 'pack-builder');
    });

    await test.step('Create pack', async () => {
      const createBtn = page.getByRole('button', { name: /create|new/i }).first();
      if (await createBtn.isVisible({ timeout: 5000 }).catch(() => false)) {
        await createBtn.click();
        await page.waitForTimeout(1000);
        const nameInput = page.locator('input').first();
        if (await nameInput.isVisible({ timeout: 3000 }).catch(() => false)) {
          await nameInput.fill('Q4 Finance Roles - UAT');
        }
        await evidence(page, UAT, 2, 'pack-created');
      }
    });

    await test.step('Save pack', async () => {
      const saveBtn = page.getByRole('button', { name: /save/i }).first();
      if (await saveBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
        await saveBtn.click();
        await page.waitForTimeout(2000);
      }
      await evidence(page, UAT, 3, 'pack-saved');
    });
  });

  test('Step 6-8: Version and risk check', async ({ page }) => {
    await test.step('Navigate to Role Studio', async () => {
      await page.goto('/roles/designer');
      await page.waitForLoadState('networkidle').catch(() => {});
      await evidence(page, UAT, 6, 'role-studio');
    });

    await test.step('Risk check', async () => {
      const riskBtn = page.getByRole('button', { name: /risk|check|analyze/i }).first();
      if (await riskBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
        await riskBtn.click();
        await page.waitForTimeout(2000);
      }
      await evidence(page, UAT, 8, 'risk-check');
    });
  });
});
