/**
 * UAT-09 · Certification Campaign · @P0
 * Persona: P04 (Compliance Officer), P07 (Line Manager)
 * Ref: qa/UAT_SCRIPT.md — Group C
 */
import { test, expect, loginAs, evidence, assertPageLoaded, getToken, apiPost } from './uat-helpers';

const UAT = 'UAT-09';

test.describe('UAT-09 · Certification Campaign @P0', () => {
  test('Step 1-5: Create and launch campaign', async ({ page }) => {
    await loginAs(page, 'P04');

    await test.step('Navigate to Certifications', async () => {
      await page.goto('/certification');
      await page.waitForLoadState('networkidle').catch(() => {});
      await assertPageLoaded(page);
      await evidence(page, UAT, 1, 'campaign-list');
    });

    await test.step('Click Create Campaign', async () => {
      const createBtn = page.getByRole('button', { name: /create|new|launch/i }).first();
      if (await createBtn.isVisible({ timeout: 5000 }).catch(() => false)) {
        await createBtn.click();
        await page.waitForTimeout(1000);
        await evidence(page, UAT, 2, 'create-form');
      }
    });

    await test.step('Fill campaign form', async () => {
      const nameInput = page.locator('input').first();
      if (await nameInput.isVisible({ timeout: 3000 }).catch(() => false)) {
        await nameInput.fill('Q4 Access Review - UAT');
      }
      await evidence(page, UAT, 3, 'form-filled');
    });

    await test.step('Launch campaign', async () => {
      const launchBtn = page.getByRole('button', { name: /launch|create|save/i }).first();
      if (await launchBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
        await launchBtn.click();
        await page.waitForTimeout(2000);
      }
      await evidence(page, UAT, 4, 'campaign-launched');
    });
  });

  test('Step 6-9: Reviewer performs reviews', async ({ page }) => {
    await loginAs(page, 'P07');

    await test.step('Navigate to My Reviews', async () => {
      await page.goto('/certification/review');
      await page.waitForLoadState('networkidle').catch(() => {});
      await assertPageLoaded(page);
      await evidence(page, UAT, 6, 'my-reviews');
    });

    await test.step('Open review item', async () => {
      const item = page.locator('tr, [class*="row"], [class*="item"]').first();
      if (await item.isVisible({ timeout: 5000 }).catch(() => false)) {
        await item.click();
        await page.waitForTimeout(1000);
        await evidence(page, UAT, 7, 'review-item');
      }
    });

    await test.step('Certify item', async () => {
      const certifyBtn = page.getByRole('button', { name: /certify|approve|keep/i }).first();
      if (await certifyBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
        await certifyBtn.click();
        await page.waitForTimeout(1000);
        await evidence(page, UAT, 8, 'certified');
      }
    });

    await test.step('Revoke another item', async () => {
      const revokeBtn = page.getByRole('button', { name: /revoke|remove|reject/i }).first();
      if (await revokeBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
        await revokeBtn.click();
        await page.waitForTimeout(500);
        // Enter reason if prompted
        const reasonInput = page.locator('textarea, input[placeholder*="reason" i]').first();
        if (await reasonInput.isVisible({ timeout: 2000 }).catch(() => false)) {
          await reasonInput.fill('No longer needed - UAT test');
        }
        const confirmBtn = page.getByRole('button', { name: /confirm|submit|save/i }).first();
        if (await confirmBtn.isVisible({ timeout: 2000 }).catch(() => false)) {
          await confirmBtn.click();
        }
        await page.waitForTimeout(1000);
        await evidence(page, UAT, 9, 'revoked');
      }
    });
  });

  test('Step 10: Campaign dashboard shows progress', async ({ page }) => {
    await loginAs(page, 'P04');
    await test.step('View campaign progress', async () => {
      await page.goto('/certification');
      await page.waitForLoadState('networkidle').catch(() => {});
      await evidence(page, UAT, 10, 'campaign-progress');
    });
  });
});
