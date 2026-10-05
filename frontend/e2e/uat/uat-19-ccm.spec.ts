/**
 * UAT-19 · Continuous Controls Monitoring (CCM) · @P1
 * Persona: P03 (CISO), P19 (Internal Auditor)
 * Ref: qa/UAT_SCRIPT.md — Group E
 */
import { test, expect, loginAs, evidence, assertPageLoaded } from './uat-helpers';

const UAT = 'UAT-19';

test.describe('UAT-19 · CCM @P1', () => {
  test('Step 1-5: CISO views CCM', async ({ page }) => {
    await loginAs(page, 'P03');

    await test.step('Navigate to Controls Monitoring', async () => {
      await page.goto('/process-control/ccm');
      await page.waitForLoadState('networkidle').catch(() => {});
      await assertPageLoaded(page);
      await evidence(page, UAT, 1, 'ccm-dashboard');
    });

    await test.step('View active monitors', async () => {
      await evidence(page, UAT, 3, 'monitors');
    });

    await test.step('View exceptions', async () => {
      await evidence(page, UAT, 5, 'exceptions');
    });
  });

  test('Step 6-8: Internal Auditor reviews', async ({ page }) => {
    await loginAs(page, 'P19');

    await test.step('Auditor views CCM', async () => {
      await page.goto('/process-control/ccm');
      await page.waitForLoadState('networkidle').catch(() => {});
      await evidence(page, UAT, 6, 'auditor-ccm');
    });
  });
});
