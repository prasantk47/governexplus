/**
 * UAT-14 · Process Control · @P1
 * Persona: P14 (Process Owner), P10 (SOX Control Owner)
 * Ref: qa/UAT_SCRIPT.md — Group D
 */
import { test, expect, loginAs, evidence, assertPageLoaded } from './uat-helpers';

const UAT = 'UAT-14';

test.describe('UAT-14 · Process Control @P1', () => {
  test('Step 1-5: View process control pages', async ({ page }) => {
    await loginAs(page, 'P14');

    await test.step('Navigate to Process Control', async () => {
      await page.goto('/process-control');
      await page.waitForLoadState('networkidle').catch(() => {});
      await assertPageLoaded(page);
      await evidence(page, UAT, 1, 'control-library');
    });

    await test.step('Navigate to Testing', async () => {
      await page.goto('/process-control/testing');
      await page.waitForLoadState('networkidle').catch(() => {});
      await evidence(page, UAT, 3, 'testing');
    });

    await test.step('Navigate to Deficiencies', async () => {
      await page.goto('/process-control/deficiencies');
      await page.waitForLoadState('networkidle').catch(() => {});
      await evidence(page, UAT, 4, 'deficiencies');
    });

    await test.step('Navigate to CCM', async () => {
      await page.goto('/process-control/ccm');
      await page.waitForLoadState('networkidle').catch(() => {});
      await evidence(page, UAT, 5, 'ccm');
    });
  });

  test('Step 6-8: SOX Control Owner view', async ({ page }) => {
    await loginAs(page, 'P10');

    await test.step('SOX owner views process control', async () => {
      await page.goto('/process-control');
      await page.waitForLoadState('networkidle').catch(() => {});
      await assertPageLoaded(page);
      await evidence(page, UAT, 6, 'sox-owner-view');
    });
  });
});
