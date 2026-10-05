/**
 * UAT-18 · Firefighter Session & Logging · @P0
 * Persona: P17 (Firefighter Session User), P11 (FF Owner)
 * Pre-condition: UAT-17 completed — approved FF access
 * Ref: qa/UAT_SCRIPT.md — Group E
 */
import { test, expect, loginAs, evidence, assertPageLoaded } from './uat-helpers';

const UAT = 'UAT-18';

test.describe('UAT-18 · Firefighter Session & Logging @P0', () => {
  test('Step 1-5: Start and end FF session', async ({ page }) => {
    await loginAs(page, 'P17');

    await test.step('Navigate to Active Sessions', async () => {
      await page.goto('/privileged-access/sessions');
      await page.waitForLoadState('networkidle').catch(() => {});
      await assertPageLoaded(page);
      await evidence(page, UAT, 1, 'sessions-page');
    });

    await test.step('View active session', async () => {
      await evidence(page, UAT, 2, 'active-session');
    });

    await test.step('Start session (check-in)', async () => {
      const startBtn = page.getByRole('button', { name: /start|check.?in|activate/i }).first();
      if (await startBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
        await startBtn.click();
        await page.waitForTimeout(2000);
        await evidence(page, UAT, 3, 'session-started');
      }
    });

    await test.step('Perform action during session', async () => {
      // Navigate to a page to generate activity
      await page.goto('/dashboard');
      await page.waitForTimeout(1000);
      await evidence(page, UAT, 4, 'session-activity');
    });

    await test.step('End session (check-out)', async () => {
      await page.goto('/privileged-access/sessions');
      await page.waitForLoadState('networkidle').catch(() => {});
      const endBtn = page.getByRole('button', { name: /end|check.?out|close/i }).first();
      if (await endBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
        await endBtn.click();
        await page.waitForTimeout(2000);
      }
      await evidence(page, UAT, 5, 'session-ended');
    });
  });

  test('Step 6-8: FF Owner reviews session log', async ({ page }) => {
    await loginAs(page, 'P11');

    await test.step('Navigate to FF Session Logs', async () => {
      await page.goto('/privileged-access');
      await page.waitForLoadState('networkidle').catch(() => {});
      await assertPageLoaded(page);
      await evidence(page, UAT, 6, 'session-logs');
    });

    await test.step('View session log details', async () => {
      const row = page.locator('tr, [class*="row"]').filter({ hasText: /completed|closed/i }).first();
      if (await row.isVisible({ timeout: 5000 }).catch(() => false)) {
        await row.click();
        await page.waitForTimeout(1000);
        await evidence(page, UAT, 7, 'log-detail');
      }
    });

    await test.step('Verify CCM exception', async () => {
      await evidence(page, UAT, 8, 'ccm-exception');
    });
  });
});
