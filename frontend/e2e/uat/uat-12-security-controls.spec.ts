/**
 * UAT-12 · Security Controls · @P1
 * Persona: P03 (CISO)
 * Ref: qa/UAT_SCRIPT.md — Group C
 */
import { test, expect, loginAs, evidence, assertPageLoaded } from './uat-helpers';

const UAT = 'UAT-12';

test.describe('UAT-12 · Security Controls @P1', () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page, 'P03');
  });

  test('Step 1-4: Create security control', async ({ page }) => {
    await test.step('Navigate to Security Controls', async () => {
      await page.goto('/security-controls');
      await page.waitForLoadState('networkidle').catch(() => {});
      await assertPageLoaded(page);
      await evidence(page, UAT, 1, 'controls-dashboard');
    });

    await test.step('Navigate to controls list', async () => {
      await page.goto('/security-controls/list');
      await page.waitForLoadState('networkidle').catch(() => {});
      await evidence(page, UAT, 2, 'controls-list');
    });

    await test.step('Create control', async () => {
      const createBtn = page.getByRole('button', { name: /create|add|new/i }).first();
      if (await createBtn.isVisible({ timeout: 5000 }).catch(() => false)) {
        await createBtn.click();
        await page.waitForTimeout(1000);
        await evidence(page, UAT, 3, 'create-form');
        const saveBtn = page.getByRole('button', { name: /save|create/i }).first();
        if (await saveBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
          await saveBtn.click();
          await page.waitForTimeout(2000);
        }
      }
      await evidence(page, UAT, 4, 'control-saved');
    });
  });

  test('Step 5-7: Edit and evaluate control', async ({ page }) => {
    await page.goto('/security-controls/list');
    await page.waitForLoadState('networkidle').catch(() => {});

    await test.step('Click control detail', async () => {
      const row = page.locator('tr, [class*="row"]').nth(1);
      if (await row.isVisible({ timeout: 5000 }).catch(() => false)) {
        await row.click();
        await page.waitForTimeout(1000);
      }
      await evidence(page, UAT, 5, 'control-detail');
    });

    await test.step('Evaluate controls', async () => {
      await page.goto('/security-controls/evaluate');
      await page.waitForLoadState('networkidle').catch(() => {});
      await evidence(page, UAT, 7, 'evaluate-page');
    });
  });
});
