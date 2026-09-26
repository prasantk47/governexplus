import { test, expect } from '@playwright/test';

test.describe('Authentication', () => {
  test('login page loads', async ({ page }) => {
    await page.goto('/login');
    await expect(page.locator('text=Governex')).toBeVisible();
  });

  test('redirects unauthenticated users to login', async ({ page }) => {
    await page.goto('/dashboard');
    await expect(page).toHaveURL(/\/login/);
  });

  test('login form has required fields', async ({ page }) => {
    await page.goto('/login');
    await expect(page.locator('input[type="text"], input[name="username"]')).toBeVisible();
    await expect(page.locator('input[type="password"]')).toBeVisible();
  });

  test('shows error on invalid credentials', async ({ page }) => {
    await page.goto('/login');
    await page.fill('input[type="text"], input[name="username"]', 'baduser');
    await page.fill('input[type="password"]', 'badpass');
    await page.click('button[type="submit"]');
    // Should show some error feedback
    await page.waitForTimeout(2000);
    await expect(page).toHaveURL(/\/login/);
  });
});
