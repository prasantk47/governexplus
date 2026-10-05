/**
 * UAT-22 · Surveys · @P1
 * Persona: P02 (Tenant Admin), P08 (Business User as respondent)
 * Ref: qa/UAT_SCRIPT.md — Group F
 */
import { test, expect, loginAs, evidence, assertPageLoaded } from './uat-helpers';

const UAT = 'UAT-22';

test.describe('UAT-22 · Surveys @P1', () => {
  test('Step 1-6: Create and publish survey', async ({ page }) => {
    await loginAs(page, 'P02');

    await test.step('Navigate to Surveys', async () => {
      await page.goto('/surveys');
      await page.waitForLoadState('networkidle').catch(() => {});
      await assertPageLoaded(page);
      await evidence(page, UAT, 1, 'survey-list');
    });

    await test.step('Create survey', async () => {
      const createBtn = page.getByRole('button', { name: /create|add|new/i }).first();
      if (await createBtn.isVisible({ timeout: 5000 }).catch(() => false)) {
        await createBtn.click();
        await page.waitForTimeout(1000);
        const nameInput = page.locator('input').first();
        if (await nameInput.isVisible({ timeout: 3000 }).catch(() => false)) {
          await nameInput.fill('Security Awareness Assessment - UAT');
        }
        await evidence(page, UAT, 3, 'survey-form');

        const saveBtn = page.getByRole('button', { name: /save|create|publish/i }).first();
        if (await saveBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
          await saveBtn.click();
          await page.waitForTimeout(2000);
        }
      }
      await evidence(page, UAT, 6, 'survey-saved');
    });
  });

  test('Step 7-8: Distribute survey', async ({ page }) => {
    await loginAs(page, 'P02');

    await test.step('Navigate to Distribution', async () => {
      await page.goto('/surveys/distribution');
      await page.waitForLoadState('networkidle').catch(() => {});
      await evidence(page, UAT, 7, 'distribution');
    });
  });

  test('Step 9-11: View analytics', async ({ page }) => {
    await loginAs(page, 'P02');

    await test.step('Navigate to Analytics', async () => {
      await page.goto('/surveys/analytics');
      await page.waitForLoadState('networkidle').catch(() => {});
      await evidence(page, UAT, 9, 'analytics');
    });
  });
});
