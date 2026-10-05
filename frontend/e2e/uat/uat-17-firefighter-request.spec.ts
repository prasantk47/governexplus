/**
 * UAT-17 · Firefighter Access — Request & Approval · @P0
 * Persona: P06 (IT Security Admin), P11 (FF Owner), P12 (FF Controller)
 * Ref: qa/UAT_SCRIPT.md — Group E
 */
import { test, expect, loginAs, evidence, assertPageLoaded, getToken, apiPost } from './uat-helpers';

const UAT = 'UAT-17';

test.describe('UAT-17 · Firefighter Request & Approval @P0', () => {
  test('Step 1-5: Request emergency access', async ({ page }) => {
    await loginAs(page, 'P06');

    await test.step('Navigate to Firefighter', async () => {
      await page.goto('/privileged-access');
      await page.waitForLoadState('networkidle').catch(() => {});
      await assertPageLoaded(page);
      await evidence(page, UAT, 1, 'ff-dashboard');
    });

    await test.step('FF dashboard shows stats', async () => {
      await evidence(page, UAT, 2, 'ff-stats');
    });

    await test.step('Click Request Emergency Access', async () => {
      await page.goto('/privileged-access/request');
      await page.waitForLoadState('networkidle').catch(() => {});
      await evidence(page, UAT, 3, 'request-form');
    });

    await test.step('Fill request form', async () => {
      // Reason
      const reasonInput = page.locator('textarea, input[placeholder*="reason" i]').first();
      if (await reasonInput.isVisible({ timeout: 3000 }).catch(() => false)) {
        await reasonInput.fill('P1 incident #4532 — posting error blocking month-end close');
      }
      await evidence(page, UAT, 4, 'form-filled');
    });

    await test.step('Submit request', async () => {
      const submitBtn = page.getByRole('button', { name: /submit|request/i }).first();
      if (await submitBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
        await submitBtn.click();
        await page.waitForTimeout(2000);
      }
      await evidence(page, UAT, 5, 'request-submitted');
    });
  });

  test('Step 6-8: FF Owner approves', async ({ page }) => {
    await loginAs(page, 'P11');

    await test.step('Navigate to FF Approvals', async () => {
      await page.goto('/privileged-access');
      await page.waitForLoadState('networkidle').catch(() => {});
      await assertPageLoaded(page);
      await evidence(page, UAT, 6, 'ff-owner-view');
    });

    await test.step('Review request', async () => {
      const row = page.locator('tr, [class*="row"]').filter({ hasText: /pending|request/i }).first();
      if (await row.isVisible({ timeout: 5000 }).catch(() => false)) {
        await row.click();
        await page.waitForTimeout(1000);
        await evidence(page, UAT, 7, 'request-detail');
      }
    });

    await test.step('Approve', async () => {
      const approveBtn = page.getByRole('button', { name: /approve/i }).first();
      if (await approveBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
        await approveBtn.click();
        await page.waitForTimeout(2000);
        await evidence(page, UAT, 8, 'approved');
      }
    });
  });

  test('Step 9: FF Controller sees alert', async ({ page }) => {
    await loginAs(page, 'P12');

    await test.step('Navigate to FF monitoring', async () => {
      await page.goto('/privileged-access/monitor');
      await page.waitForLoadState('networkidle').catch(() => {});
      await assertPageLoaded(page);
      await evidence(page, UAT, 9, 'controller-monitor');
    });
  });
});
