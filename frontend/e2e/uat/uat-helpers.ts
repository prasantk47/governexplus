/**
 * UAT-specific helpers. Wraps the base helpers with screenshot evidence capture.
 * Every numbered step in UAT_SCRIPT.md = a test.step() with a screenshot.
 */
import { test, Page, expect } from '@playwright/test';
import { loginAs, getToken, apiGet, apiPost, PERSONAS, type PersonaId } from '../helpers';
import * as path from 'path';
import * as fs from 'fs';

export { loginAs, getToken, apiGet, apiPost, PERSONAS, type PersonaId };
export { test, expect };

const EVIDENCE_ROOT = path.resolve(__dirname, '../../../qa/uat-evidence');

/** Capture a screenshot and save to qa/uat-evidence/UAT-xx/step-nn.png */
export async function evidence(page: Page, uatId: string, stepNum: number, label?: string) {
  const dir = path.join(EVIDENCE_ROOT, uatId);
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
  const filename = `step-${String(stepNum).padStart(2, '0')}${label ? '-' + label : ''}.png`;
  await page.screenshot({ path: path.join(dir, filename), fullPage: false });
}

/** Login and capture evidence */
export async function loginAndEvidence(page: Page, persona: PersonaId, uatId: string, stepNum: number) {
  await loginAs(page, persona);
  await evidence(page, uatId, stepNum, 'login');
}

/** Navigate to a path, wait for load, capture evidence */
export async function navigateAndEvidence(page: Page, urlPath: string, uatId: string, stepNum: number, label?: string) {
  await page.goto(urlPath);
  await page.waitForLoadState('networkidle').catch(() => {});
  await evidence(page, uatId, stepNum, label ?? urlPath.replace(/\//g, '-').slice(1));
}

/** Assert page has no error state (no 500 page, no blank body) */
export async function assertPageLoaded(page: Page) {
  // No "500" error page
  const body = await page.locator('body').textContent();
  expect(body).not.toContain('Internal Server Error');
  // Page has some visible content
  const visible = await page.locator('body').isVisible();
  expect(visible).toBe(true);
}

/** Assert an element is visible */
export async function assertVisible(page: Page, selector: string, description?: string) {
  const loc = page.locator(selector).first();
  await expect(loc, description ?? `Expected ${selector} to be visible`).toBeVisible({ timeout: 10000 });
}

/** Assert an element is NOT visible */
export async function assertNotVisible(page: Page, selector: string, description?: string) {
  const loc = page.locator(selector).first();
  await expect(loc, description ?? `Expected ${selector} to be hidden`).not.toBeVisible({ timeout: 5000 });
}

/** Assert text appears on page */
export async function assertTextVisible(page: Page, text: string) {
  await expect(page.getByText(text, { exact: false }).first()).toBeVisible({ timeout: 10000 });
}

/** Fill a form field by label */
export async function fillByLabel(page: Page, label: string, value: string) {
  const field = page.getByLabel(label, { exact: false }).first();
  await field.fill(value);
}

/** Select from a dropdown by label */
export async function selectByLabel(page: Page, label: string, value: string) {
  const select = page.getByLabel(label, { exact: false }).first();
  await select.selectOption(value);
}

/** Click a button by text */
export async function clickButton(page: Page, text: string) {
  await page.getByRole('button', { name: text, exact: false }).first().click();
}

/** Wait for toast message */
export async function waitForToast(page: Page, text: string) {
  await expect(
    page.locator('[role="status"], .Toastify, [class*="toast"]').filter({ hasText: text }).first()
  ).toBeVisible({ timeout: 10000 });
}

/** P0/P1 tag for test.describe */
export const P0 = { tag: '@P0' } as const;
export const P1 = { tag: '@P1' } as const;
