/**
 * UAT-02 · Dashboard & Navigation · @P0
 * Persona: P02 (Tenant Admin)
 * Ref: qa/UAT_SCRIPT.md — Group A
 */
import { test, expect, loginAs, evidence, assertPageLoaded, assertVisible } from './uat-helpers';

const UAT = 'UAT-02';

test.describe('UAT-02 · Dashboard & Navigation @P0', () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page, 'P02');
  });

  test('Step 1: Dashboard loads with stat cards', async ({ page }) => {
    await test.step('Verify dashboard content', async () => {
      await assertPageLoaded(page);
      // Stat cards should be visible
      const cards = page.locator('[class*="stat"], [class*="card"], [class*="metric"]');
      const count = await cards.count();
      expect(count, 'Dashboard should have stat cards').toBeGreaterThan(0);
      await evidence(page, UAT, 1, 'dashboard-stats');
    });
  });

  test('Step 2: Sidebar navigation visible', async ({ page }) => {
    await test.step('Check sidebar', async () => {
      const sidebar = page.locator('nav, aside, [class*="sidebar"], [class*="Sidebar"]').first();
      await expect(sidebar).toBeVisible({ timeout: 5000 });
      await evidence(page, UAT, 2, 'sidebar');
    });
  });

  test('Step 3: Navigate to each major section', async ({ page }) => {
    const sections = [
      { path: '/access-requests', name: 'access-requests' },
      { path: '/certification', name: 'certification' },
      { path: '/privileged-access', name: 'firefighter' },
      { path: '/risk', name: 'risk' },
      { path: '/risk-management', name: 'risk-management' },
      { path: '/process-control', name: 'process-control' },
      { path: '/jml', name: 'jml' },
      { path: '/tprm', name: 'tprm' },
      { path: '/fraud', name: 'fraud' },
      { path: '/bcm', name: 'bcm' },
      { path: '/surveys', name: 'surveys' },
      { path: '/reports', name: 'reports' },
      { path: '/library', name: 'library' },
      { path: '/users', name: 'users' },
    ];

    for (const section of sections) {
      await test.step(`Navigate to ${section.name}`, async () => {
        await page.goto(section.path);
        await page.waitForLoadState('networkidle').catch(() => {});
        await assertPageLoaded(page);
        await evidence(page, UAT, 3, section.name);
      });
    }
  });

  test('Step 4-5: Dark mode toggle', async ({ page }) => {
    await test.step('Toggle dark mode', async () => {
      const toggle = page.locator('button, [role="switch"]').filter({ hasText: /dark|theme|moon/i }).first()
        .or(page.locator('[class*="theme"], [class*="dark-mode"], [aria-label*="theme"]').first());

      if (await toggle.isVisible({ timeout: 3000 }).catch(() => false)) {
        await toggle.click();
        await page.waitForTimeout(500);
        await evidence(page, UAT, 4, 'dark-mode');
        // Toggle back
        await toggle.click();
        await page.waitForTimeout(500);
        await evidence(page, UAT, 5, 'light-mode');
      } else {
        // Dark mode toggle may be in a menu — capture current state
        await evidence(page, UAT, 4, 'theme-toggle-not-found');
      }
    });
  });

  test('Step 6-7: Mobile responsive', async ({ page }) => {
    await test.step('Resize to mobile', async () => {
      await page.setViewportSize({ width: 375, height: 812 });
      await page.waitForTimeout(500);
      await evidence(page, UAT, 6, 'mobile-view');
    });

    await test.step('Check hamburger menu', async () => {
      const hamburger = page.locator('button[aria-label*="menu"], button[class*="hamburger"], [class*="mobile-menu"]').first()
        .or(page.locator('button:has(svg)').filter({ hasText: '' }).first());
      if (await hamburger.isVisible({ timeout: 3000 }).catch(() => false)) {
        await hamburger.click();
        await page.waitForTimeout(500);
        await evidence(page, UAT, 7, 'mobile-menu-open');
      }
      // Reset viewport
      await page.setViewportSize({ width: 1280, height: 720 });
    });
  });
});
