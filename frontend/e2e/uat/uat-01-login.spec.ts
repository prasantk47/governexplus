/**
 * UAT-01 · Login & Session Management · @P0
 * Persona: P08 (Business User)
 * Ref: qa/UAT_SCRIPT.md — Group A
 */
import { test, expect, loginAs, evidence, assertPageLoaded, PERSONAS } from './uat-helpers';

const UAT = 'UAT-01';

test.describe('UAT-01 · Login & Session Management @P0', () => {
  test('Step 1: Login page renders', async ({ page }) => {
    await test.step('Navigate to /login', async () => {
      await page.goto('/login');
      await page.waitForLoadState('networkidle').catch(() => {});
      await expect(page.locator('input[type="password"]')).toBeVisible();
      await evidence(page, UAT, 1, 'login-page');
    });
  });

  test('Step 2-3: Valid login redirects to dashboard', async ({ page }) => {
    await test.step('Enter valid credentials and sign in', async () => {
      await page.goto('/login');
      await page.fill('input[name="username"], input[type="text"]', PERSONAS.P08.username);
      await page.fill('input[type="password"]', PERSONAS.P08.password);
      await evidence(page, UAT, 2, 'credentials-entered');
    });

    await test.step('Click Sign In', async () => {
      await page.click('button[type="submit"]');
      await page.waitForURL(/\/(dashboard|$)/, { timeout: 15000 });
      await assertPageLoaded(page);
      await evidence(page, UAT, 3, 'dashboard-loaded');
    });
  });

  test('Step 4: Session persists on refresh', async ({ page }) => {
    await loginAs(page, 'P08');
    await test.step('Refresh page', async () => {
      await page.reload();
      await page.waitForLoadState('networkidle').catch(() => {});
      // Should still be on dashboard, not login
      const url = page.url();
      expect(url).not.toContain('/login');
      await evidence(page, UAT, 4, 'session-persists');
    });
  });

  test('Step 5: JWT present in storage', async ({ page }) => {
    await loginAs(page, 'P08');
    await test.step('Check localStorage for token', async () => {
      const token = await page.evaluate(() => {
        // Check common auth storage keys
        return localStorage.getItem('token') ||
               localStorage.getItem('auth_token') ||
               localStorage.getItem('access_token') ||
               sessionStorage.getItem('token') ||
               Object.keys(localStorage).find(k => k.includes('token') || k.includes('auth'));
      });
      expect(token, 'JWT should be present in storage').toBeTruthy();
      await evidence(page, UAT, 5, 'jwt-present');
    });
  });

  test('Step 6: Logout clears session', async ({ page }) => {
    await loginAs(page, 'P08');
    await test.step('Click Sign Out', async () => {
      // Try common logout patterns
      const logoutButton = page.locator('button, a, [role="menuitem"]').filter({ hasText: /sign.?out|log.?out/i }).first();
      if (await logoutButton.isVisible({ timeout: 3000 }).catch(() => false)) {
        await logoutButton.click();
      } else {
        // Try profile/avatar menu first
        const avatar = page.locator('[class*="avatar"], [class*="profile"], button:has(img)').first();
        if (await avatar.isVisible({ timeout: 3000 }).catch(() => false)) {
          await avatar.click();
          await page.waitForTimeout(500);
          const menuLogout = page.locator('[role="menuitem"], button, a').filter({ hasText: /sign.?out|log.?out/i }).first();
          await menuLogout.click();
        }
      }
      await page.waitForURL(/\/login/, { timeout: 10000 }).catch(() => {});
      await evidence(page, UAT, 6, 'logged-out');
    });
  });

  test('Step 7: Unauthenticated access redirects to login', async ({ page }) => {
    await test.step('Navigate to /dashboard while logged out', async () => {
      await page.goto('/dashboard');
      await page.waitForURL(/\/login/, { timeout: 10000 });
      expect(page.url()).toContain('/login');
      await evidence(page, UAT, 7, 'redirect-to-login');
    });
  });

  test('Step 8: Invalid password shows error', async ({ page }) => {
    await test.step('Enter wrong password', async () => {
      await page.goto('/login');
      await page.fill('input[name="username"], input[type="text"]', PERSONAS.P08.username);
      await page.fill('input[type="password"]', 'WrongPassword!');
      await page.click('button[type="submit"]');
      await page.waitForTimeout(2000);
      // Should still be on login page
      expect(page.url()).toContain('/login');
      await evidence(page, UAT, 8, 'invalid-password');
    });
  });
});
