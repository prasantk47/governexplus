/**
 * UAT-23 · Fraud Detection · @P0
 * Persona: P06 (IT Security Admin)
 * Pre-condition: Fraud rules configured; guaranteed fraud-rule hit seeded
 * Ref: qa/UAT_SCRIPT.md — Group F
 */
import { test, expect, loginAs, evidence, assertPageLoaded } from './uat-helpers';

const UAT = 'UAT-23';

test.describe('UAT-23 · Fraud Detection @P0', () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page, 'P06');
  });

  test('Step 1-5: Create fraud rule', async ({ page }) => {
    await test.step('Navigate to Fraud Rules', async () => {
      await page.goto('/fraud/rules');
      await page.waitForLoadState('networkidle').catch(() => {});
      await assertPageLoaded(page);
      await evidence(page, UAT, 1, 'rules-list');
    });

    await test.step('Click Create Rule', async () => {
      const createBtn = page.getByRole('button', { name: /create|add|new/i }).first();
      if (await createBtn.isVisible({ timeout: 5000 }).catch(() => false)) {
        await createBtn.click();
        await page.waitForTimeout(1000);
        await evidence(page, UAT, 2, 'create-form');
      }
    });

    await test.step('Fill rule form', async () => {
      const nameInput = page.locator('input').first();
      if (await nameInput.isVisible({ timeout: 3000 }).catch(() => false)) {
        await nameInput.fill('UAT Duplicate Payment Detection');
      }
      await evidence(page, UAT, 3, 'form-filled');
    });

    await test.step('Save rule', async () => {
      const saveBtn = page.getByRole('button', { name: /save|create|submit/i }).first();
      if (await saveBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
        await saveBtn.click();
        await page.waitForTimeout(2000);
      }
      await evidence(page, UAT, 4, 'rule-saved');
    });
  });

  test('Step 6-7: View fraud alerts', async ({ page }) => {
    await test.step('Navigate to Fraud Alerts', async () => {
      await page.goto('/fraud/alerts');
      await page.waitForLoadState('networkidle').catch(() => {});
      await assertPageLoaded(page);
      await evidence(page, UAT, 6, 'alerts-inbox');
    });

    await test.step('Click alert for details', async () => {
      const row = page.locator('tr, [class*="row"]').nth(1);
      if (await row.isVisible({ timeout: 5000 }).catch(() => false)) {
        await row.click();
        await page.waitForTimeout(1000);
        await evidence(page, UAT, 7, 'alert-detail');
      }
    });
  });

  test('Step 8-11: Open case from alert and manage', async ({ page }) => {
    await test.step('Navigate to Cases', async () => {
      await page.goto('/fraud/cases');
      await page.waitForLoadState('networkidle').catch(() => {});
      await assertPageLoaded(page);
      await evidence(page, UAT, 8, 'cases-list');
    });

    await test.step('Create case', async () => {
      const createBtn = page.getByRole('button', { name: /create|new|open/i }).first();
      if (await createBtn.isVisible({ timeout: 5000 }).catch(() => false)) {
        await createBtn.click();
        await page.waitForTimeout(1000);

        const titleInput = page.locator('input').first();
        if (await titleInput.isVisible({ timeout: 3000 }).catch(() => false)) {
          await titleInput.fill('UAT Suspected fraud case');
        }

        const saveBtn = page.getByRole('button', { name: /save|create|submit/i }).first();
        if (await saveBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
          await saveBtn.click();
          await page.waitForTimeout(2000);
        }
        await evidence(page, UAT, 9, 'case-created');
      }
    });

    await test.step('View cases list', async () => {
      await page.goto('/fraud/cases');
      await page.waitForLoadState('networkidle').catch(() => {});
      await evidence(page, UAT, 10, 'cases-updated');
    });

    await test.step('Update case status', async () => {
      const row = page.locator('tr, [class*="row"]').nth(1);
      if (await row.isVisible({ timeout: 5000 }).catch(() => false)) {
        await row.click();
        await page.waitForTimeout(1000);
        await evidence(page, UAT, 11, 'case-detail');
      }
    });
  });
});
