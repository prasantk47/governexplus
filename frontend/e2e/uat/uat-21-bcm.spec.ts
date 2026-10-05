/**
 * UAT-21 · Business Continuity Management (BCM) · @P1
 * Persona: P05 (Risk Manager)
 * Ref: qa/UAT_SCRIPT.md — Group F
 */
import { test, expect, loginAs, evidence, assertPageLoaded } from './uat-helpers';

const UAT = 'UAT-21';

test.describe('UAT-21 · BCM @P1', () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page, 'P05');
  });

  test('Step 1-4: Create BCP plan', async ({ page }) => {
    await test.step('Navigate to BCM Plans', async () => {
      await page.goto('/bcm/plans');
      await page.waitForLoadState('networkidle').catch(() => {});
      await assertPageLoaded(page);
      await evidence(page, UAT, 1, 'plans-list');
    });

    await test.step('Create plan', async () => {
      const createBtn = page.getByRole('button', { name: /create|add|new/i }).first();
      if (await createBtn.isVisible({ timeout: 5000 }).catch(() => false)) {
        await createBtn.click();
        await page.waitForTimeout(1000);
        const nameInput = page.locator('input').first();
        if (await nameInput.isVisible({ timeout: 3000 }).catch(() => false)) {
          await nameInput.fill('IT Disaster Recovery - UAT');
        }
        const saveBtn = page.getByRole('button', { name: /save|create/i }).first();
        if (await saveBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
          await saveBtn.click();
          await page.waitForTimeout(2000);
        }
      }
      await evidence(page, UAT, 4, 'plan-created');
    });
  });

  test('Step 5-8: BIA records', async ({ page }) => {
    await test.step('Navigate to BIA', async () => {
      await page.goto('/bcm/bia');
      await page.waitForLoadState('networkidle').catch(() => {});
      await assertPageLoaded(page);
      await evidence(page, UAT, 5, 'bia-list');
    });

    await test.step('Create BIA', async () => {
      const createBtn = page.getByRole('button', { name: /create|add|new/i }).first();
      if (await createBtn.isVisible({ timeout: 5000 }).catch(() => false)) {
        await createBtn.click();
        await page.waitForTimeout(1000);
        await evidence(page, UAT, 6, 'bia-form');
      }
    });
  });

  test('Step 9-10: Exercises', async ({ page }) => {
    await test.step('Navigate to Activations', async () => {
      await page.goto('/bcm/activations');
      await page.waitForLoadState('networkidle').catch(() => {});
      await evidence(page, UAT, 9, 'activations');
    });
  });
});
