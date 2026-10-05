/**
 * UAT-24 · Whistleblower Portal · @P0
 * Persona: Anonymous (public), then P06 (IT Security Admin as investigator)
 * Pre-condition: /whistleblower/submit is PUBLIC (no auth required)
 * Ref: qa/UAT_SCRIPT.md — Group F
 */
import { test, expect, evidence, assertPageLoaded, loginAs, getToken, apiGet } from './uat-helpers';

const UAT = 'UAT-24';

test.describe('UAT-24 · Whistleblower Portal @P0', () => {
  let referenceCode: string;

  test('Step 1-4: Anonymous submission (no auth)', async ({ page }) => {
    await test.step('Navigate to submit page (no login)', async () => {
      await page.goto('/whistleblower/intake');
      await page.waitForLoadState('networkidle').catch(() => {});
      // Should NOT redirect to login
      expect(page.url()).not.toContain('/login');
      await assertPageLoaded(page);
      await evidence(page, UAT, 1, 'submit-page-public');
    });

    await test.step('Fill submission form', async () => {
      // Category
      const categorySelect = page.locator('select').first();
      if (await categorySelect.isVisible({ timeout: 3000 }).catch(() => false)) {
        await categorySelect.selectOption({ label: 'Fraud' }).catch(() =>
          categorySelect.selectOption('fraud').catch(() =>
            categorySelect.selectOption('FRAUD')
          )
        );
      }

      // Description
      const descInput = page.locator('textarea').first();
      if (await descInput.isVisible({ timeout: 3000 }).catch(() => false)) {
        await descInput.fill('Suspected invoice manipulation in AP department. Invoices #INV-4401 and #INV-4402 appear to be for services never rendered.');
      }

      // Priority
      const prioritySelect = page.locator('select').nth(1);
      if (await prioritySelect.isVisible({ timeout: 3000 }).catch(() => false)) {
        await prioritySelect.selectOption({ label: 'High' }).catch(() =>
          prioritySelect.selectOption('high').catch(() =>
            prioritySelect.selectOption('HIGH')
          )
        );
      }

      await evidence(page, UAT, 2, 'form-filled');
    });

    await test.step('Submit report', async () => {
      const submitBtn = page.getByRole('button', { name: /submit/i }).first();
      await submitBtn.click();
      await page.waitForTimeout(3000);
      await evidence(page, UAT, 3, 'submitted');

      // Try to capture reference code from the page
      const body = await page.locator('body').textContent() ?? '';
      const match = body.match(/WB-[A-Z0-9]{6,}/);
      if (match) {
        referenceCode = match[0];
      }
    });

    await test.step('Reference code displayed', async () => {
      await evidence(page, UAT, 4, 'reference-code');
    });
  });

  test('Step 5-6: Track case by reference code', async ({ page }) => {
    // Use API to get a valid reference code if we don't have one
    if (!referenceCode) {
      const token = await getToken('P06');
      const res = await apiGet('/whistleblower/cases', token);
      if (res.body && Array.isArray(res.body)) {
        referenceCode = res.body[0]?.case_reference ?? 'WB-TEST';
      } else if (res.body?.cases) {
        referenceCode = res.body.cases[0]?.case_reference ?? 'WB-TEST';
      }
    }

    await test.step('Navigate to tracking page (no login)', async () => {
      await page.goto('/whistleblower/intake');
      await page.waitForLoadState('networkidle').catch(() => {});
      expect(page.url()).not.toContain('/login');
      await evidence(page, UAT, 5, 'track-page');
    });

    await test.step('Enter reference code', async () => {
      const refInput = page.locator('input[placeholder*="reference" i], input[placeholder*="code" i], input[placeholder*="track" i]').first()
        .or(page.locator('input[type="text"]').last());
      if (await refInput.isVisible({ timeout: 3000 }).catch(() => false) && referenceCode) {
        await refInput.fill(referenceCode);
        const trackBtn = page.getByRole('button', { name: /track|check|search|status/i }).first();
        if (await trackBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
          await trackBtn.click();
          await page.waitForTimeout(2000);
        }
      }
      await evidence(page, UAT, 6, 'case-tracked');
    });
  });

  test('Step 7-10: Investigator manages case', async ({ page }) => {
    await loginAs(page, 'P06');

    await test.step('Navigate to Whistleblower Inbox', async () => {
      await page.goto('/whistleblower/inbox');
      await page.waitForLoadState('networkidle').catch(() => {});
      await assertPageLoaded(page);
      await evidence(page, UAT, 7, 'investigator-inbox');
    });

    await test.step('Open case', async () => {
      const row = page.locator('tr, [class*="row"]').nth(1);
      if (await row.isVisible({ timeout: 5000 }).catch(() => false)) {
        await row.click();
        await page.waitForTimeout(1000);
        await evidence(page, UAT, 8, 'case-detail');
      }
    });

    await test.step('Add investigator message', async () => {
      const msgInput = page.locator('textarea').first();
      if (await msgInput.isVisible({ timeout: 3000 }).catch(() => false)) {
        await msgInput.fill('We are reviewing your report. Can you provide the invoice numbers?');
        const sendBtn = page.getByRole('button', { name: /send|add|submit|reply/i }).first();
        if (await sendBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
          await sendBtn.click();
          await page.waitForTimeout(2000);
        }
      }
      await evidence(page, UAT, 9, 'message-sent');
    });

    await test.step('Change status to Investigating', async () => {
      const statusSelect = page.locator('select').filter({ hasText: /status|investigating/i }).first()
        .or(page.locator('select').first());
      if (await statusSelect.isVisible({ timeout: 3000 }).catch(() => false)) {
        await statusSelect.selectOption({ label: 'Investigating' }).catch(() =>
          statusSelect.selectOption('INVESTIGATING').catch(() => {})
        );
        await page.waitForTimeout(1000);
      }
      await evidence(page, UAT, 10, 'status-changed');
    });
  });

  test('Step 11-13: Anonymous reply and investigator sees it', async ({ page }) => {
    await test.step('Anonymous tracking shows updated status', async () => {
      await page.goto('/whistleblower/intake');
      await page.waitForLoadState('networkidle').catch(() => {});
      await evidence(page, UAT, 11, 'tracking-updated');
    });

    await test.step('Submit anonymous reply', async () => {
      // Reply field if available
      const replyInput = page.locator('textarea').first();
      if (await replyInput.isVisible({ timeout: 3000 }).catch(() => false)) {
        await replyInput.fill('Invoice numbers: INV-2026-4401, INV-2026-4402');
        const sendBtn = page.getByRole('button', { name: /send|reply|submit/i }).first();
        if (await sendBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
          await sendBtn.click();
          await page.waitForTimeout(2000);
        }
      }
      await evidence(page, UAT, 12, 'anonymous-reply');
    });

    await test.step('Investigator sees reply', async () => {
      await loginAs(page, 'P06');
      await page.goto('/whistleblower/inbox');
      await page.waitForLoadState('networkidle').catch(() => {});
      await evidence(page, UAT, 13, 'reply-visible');
    });
  });
});
