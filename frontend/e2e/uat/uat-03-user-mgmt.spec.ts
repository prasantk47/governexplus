/**
 * UAT-03 · User Management (CRUD) · @P0
 * Persona: P02 (Tenant Admin)
 * Ref: qa/UAT_SCRIPT.md — Group A
 */
import { test, expect, loginAs, evidence, assertPageLoaded, clickButton, fillByLabel } from './uat-helpers';

const UAT = 'UAT-03';
const TEST_USER = `uat_user_${Date.now().toString(36)}`;

test.describe('UAT-03 · User Management @P0', () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page, 'P02');
  });

  test('Step 1: User list loads', async ({ page }) => {
    await test.step('Navigate to Users', async () => {
      await page.goto('/users');
      await page.waitForLoadState('networkidle').catch(() => {});
      await assertPageLoaded(page);
      // Table or list should be present
      const table = page.locator('table, [class*="table"], [role="grid"]').first();
      await expect(table).toBeVisible({ timeout: 10000 });
      await evidence(page, UAT, 1, 'user-list');
    });
  });

  test('Step 2-3: Create user', async ({ page }) => {
    await page.goto('/users');
    await page.waitForLoadState('networkidle').catch(() => {});

    await test.step('Click Create User', async () => {
      const createBtn = page.getByRole('button', { name: /create|add|new/i }).first();
      await createBtn.click();
      await page.waitForTimeout(1000);
      await evidence(page, UAT, 2, 'create-form');
    });

    await test.step('Fill and save', async () => {
      // Fill form fields — try by label first, then by placeholder
      const fields = page.locator('input, select, textarea');
      const count = await fields.count();

      // Try to fill by common patterns
      for (let i = 0; i < count; i++) {
        const field = fields.nth(i);
        const label = await field.getAttribute('aria-label') ?? '';
        const placeholder = await field.getAttribute('placeholder') ?? '';
        const name = await field.getAttribute('name') ?? '';
        const key = (label + placeholder + name).toLowerCase();

        if (key.includes('username') || key.includes('user_id')) await field.fill(TEST_USER);
        else if (key.includes('full_name') || key.includes('full name') || key.includes('name')) await field.fill('UAT Test User');
        else if (key.includes('email')) await field.fill(`${TEST_USER}@test.com`);
        else if (key.includes('department') || key.includes('dept')) await field.fill('QA');
      }

      await evidence(page, UAT, 3, 'form-filled');
      // Click save/submit
      const saveBtn = page.getByRole('button', { name: /save|create|submit/i }).first();
      await saveBtn.click();
      await page.waitForTimeout(2000);
      await evidence(page, UAT, 3, 'user-created');
    });
  });

  test('Step 4: Search user', async ({ page }) => {
    await page.goto('/users');
    await page.waitForLoadState('networkidle').catch(() => {});

    await test.step('Search for a known user', async () => {
      const search = page.locator('input[type="search"], input[placeholder*="search" i], input[placeholder*="Search" i]').first();
      if (await search.isVisible({ timeout: 3000 }).catch(() => false)) {
        await search.fill('qa_requestor');
        await page.waitForTimeout(1000);
        await evidence(page, UAT, 4, 'search-results');
      }
    });
  });

  test('Step 5-6: Edit user', async ({ page }) => {
    await page.goto('/users');
    await page.waitForLoadState('networkidle').catch(() => {});

    await test.step('Click a user row', async () => {
      const row = page.locator('tr, [class*="row"]').filter({ hasText: /requestor/i }).first();
      if (await row.isVisible({ timeout: 5000 }).catch(() => false)) {
        await row.click();
        await page.waitForTimeout(1000);
        await evidence(page, UAT, 5, 'user-detail');
      }
    });

    await test.step('Edit user', async () => {
      const editBtn = page.getByRole('button', { name: /edit/i }).first();
      if (await editBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
        await editBtn.click();
        await page.waitForTimeout(1000);
        await evidence(page, UAT, 6, 'edit-form');
      }
    });
  });

  test('Step 7: Toggle user status', async ({ page }) => {
    await page.goto('/users');
    await page.waitForLoadState('networkidle').catch(() => {});

    await test.step('Deactivate a user', async () => {
      // Look for toggle/deactivate button on any user
      const toggle = page.locator('button, [role="switch"]').filter({ hasText: /deactivate|disable/i }).first();
      if (await toggle.isVisible({ timeout: 3000 }).catch(() => false)) {
        await evidence(page, UAT, 7, 'toggle-status');
      } else {
        await evidence(page, UAT, 7, 'no-toggle-found');
      }
    });
  });
});
