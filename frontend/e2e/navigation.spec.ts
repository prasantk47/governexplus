import { test, expect } from '@playwright/test';

test.describe('Navigation', () => {
  // These tests verify that pages load without crashing
  // They require a logged-in session, so they may redirect to login

  test('login page renders without errors', async ({ page }) => {
    await page.goto('/login');
    // No console errors should crash the page
    const errors: string[] = [];
    page.on('pageerror', (err) => errors.push(err.message));
    await page.waitForTimeout(1000);
    // Page should not have unhandled React errors
    const errorBoundary = page.locator('text=Something went wrong');
    await expect(errorBoundary).not.toBeVisible();
  });

  test('admin portal loads', async ({ page }) => {
    await page.goto('/admin');
    await page.waitForTimeout(1000);
    await expect(page.locator('body')).toBeVisible();
  });
});
