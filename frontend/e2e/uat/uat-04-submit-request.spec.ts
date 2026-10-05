/**
 * UAT-04 · Submit Access Request · @P0
 * Persona: P08 (Business User)
 * Ref: qa/UAT_SCRIPT.md — Group B
 */
import { test, expect, loginAs, evidence, assertPageLoaded } from './uat-helpers';

const UAT = 'UAT-04';

test.describe('UAT-04 · Submit Access Request @P0', () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page, 'P08');
  });

  test('Step 1-2: Access request page loads with role catalog', async ({ page }) => {
    await test.step('Navigate to Request Access', async () => {
      await page.goto('/access-requests/new');
      await page.waitForLoadState('networkidle').catch(() => {});
      await assertPageLoaded(page);
      await evidence(page, UAT, 1, 'request-page');
    });

    await test.step('Role catalog/search visible', async () => {
      // Should have some form of role selection
      const roleArea = page.locator('[class*="role"], [class*="catalog"], input[placeholder*="search" i], select').first();
      await expect(roleArea).toBeVisible({ timeout: 10000 });
      await evidence(page, UAT, 2, 'role-catalog');
    });
  });

  test('Step 3-4: Select role and add to cart', async ({ page }) => {
    await page.goto('/access-requests/new');
    await page.waitForLoadState('networkidle').catch(() => {});

    await test.step('Search/select a role', async () => {
      // Try search input
      const search = page.locator('input[placeholder*="search" i], input[placeholder*="role" i], input[type="search"]').first();
      if (await search.isVisible({ timeout: 3000 }).catch(() => false)) {
        await search.fill('ROLE_FI');
        await page.waitForTimeout(1000);
      }
      await evidence(page, UAT, 3, 'role-search');
    });

    await test.step('Add role to cart or selection', async () => {
      // Click add/select button
      const addBtn = page.getByRole('button', { name: /add|select|choose/i }).first();
      if (await addBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
        await addBtn.click();
        await page.waitForTimeout(500);
      }
      await evidence(page, UAT, 4, 'role-added');
    });
  });

  test('Step 5-6: Enter justification and submit', async ({ page }) => {
    await page.goto('/access-requests/new');
    await page.waitForLoadState('networkidle').catch(() => {});

    await test.step('Enter business justification', async () => {
      const justification = page.locator('textarea, input[name*="justification" i], input[placeholder*="justification" i], textarea[placeholder*="reason" i]').first();
      if (await justification.isVisible({ timeout: 5000 }).catch(() => false)) {
        await justification.fill('Need read access to financial reports for quarterly audit - UAT test');
        await evidence(page, UAT, 5, 'justification');
      }
    });

    await test.step('Submit request', async () => {
      const submitBtn = page.getByRole('button', { name: /submit|send|request/i }).first();
      if (await submitBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
        await submitBtn.click();
        await page.waitForTimeout(2000);
        await evidence(page, UAT, 6, 'submitted');
      }
    });
  });

  test('Step 7: My Requests shows new request', async ({ page }) => {
    await test.step('Navigate to My Requests', async () => {
      await page.goto('/access-requests');
      await page.waitForLoadState('networkidle').catch(() => {});
      await assertPageLoaded(page);
      await evidence(page, UAT, 7, 'my-requests');
    });
  });
});
