/**
 * Shared E2E helpers for GovernexPlus QA suite.
 * Requires the QA stack to be running (docker compose -f docker-compose.qa.yml up).
 */
import { Page, expect } from '@playwright/test';

export const API = 'http://localhost:9000';
export const MAILPIT = 'http://localhost:8025';

// ── Persona credentials from qa/personas.json ─────────────────────────────
export const PERSONAS = {
  P01: { username: 'qa_platform_admin', password: 'QaP@ss2026!Platform' },
  P02: { username: 'qa_tenant_admin', password: 'QaP@ss2026!Tenant' },
  P03: { username: 'qa_ciso', password: 'QaP@ss2026!CISO' },
  P04: { username: 'qa_compliance', password: 'QaP@ss2026!Compliance' },
  P05: { username: 'qa_risk_manager', password: 'QaP@ss2026!Risk' },
  P06: { username: 'qa_it_security', password: 'QaP@ss2026!Security' },
  P07: { username: 'qa_line_manager', password: 'QaP@ss2026!LineMgr' },
  P08: { username: 'qa_requestor', password: 'QaP@ss2026!Request' },
  P09: { username: 'qa_ext_auditor', password: 'QaP@ss2026!ExtAudit' },
  P10: { username: 'qa_sox_owner', password: 'QaP@ss2026!SOX' },
  P11: { username: 'qa_ff_owner', password: 'QaP@ss2026!FFOwner' },
  P12: { username: 'qa_ff_controller', password: 'QaP@ss2026!FFCtrl' },
  P13: { username: 'qa_hr_manager', password: 'QaP@ss2026!HRMgr' },
  P14: { username: 'qa_process_owner', password: 'QaP@ss2026!Process' },
  P15: { username: 'qa_it_ops', password: 'QaP@ss2026!ITOps' },
  P16: { username: 'qa_viewer', password: 'QaP@ss2026!View' },
  P17: { username: 'qa_firefighter', password: 'QaP@ss2026!FFUser' },
  P18: { username: 'qa_mitigation_monitor', password: 'QaP@ss2026!MitMon' },
  P19: { username: 'qa_int_auditor', password: 'QaP@ss2026!IntAudit' },
  P20: { username: 'qa_vendor_manager', password: 'QaP@ss2026!Vendor' },
  P21: { username: 'qa_role_owner', password: 'QaP@ss2026!RoleOwn' },
  P22: { username: 'qa_risk_owner', password: 'QaP@ss2026!RiskOwn' },
} as const;

export type PersonaId = keyof typeof PERSONAS;

// ── Login helper ──────────────────────────────────────────────────────────
export async function loginAs(page: Page, persona: PersonaId) {
  const creds = PERSONAS[persona];
  await page.goto('/login');
  await page.fill('input[name="username"], input[type="text"]', creds.username);
  await page.fill('input[type="password"]', creds.password);
  await page.click('button[type="submit"]');
  await page.waitForURL(/\/(dashboard|$)/, { timeout: 10000 });
}

// ── API token helper (for API-level assertions) ───────────────────────────
export async function getToken(persona: PersonaId): Promise<string> {
  const creds = PERSONAS[persona];
  const res = await fetch(`${API}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username: creds.username, password: creds.password, tenant_id: 'qa-tenant-001' }),
  });
  if (!res.ok) throw new Error(`Login failed for ${persona}: ${res.status}`);
  const data = await res.json();
  return data.access_token;
}

// ── API call helpers ──────────────────────────────────────────────────────
export async function apiGet(path: string, token: string): Promise<{ status: number; body: any }> {
  const res = await fetch(`${API}${path}`, {
    headers: { Authorization: `Bearer ${token}`, 'X-Tenant-ID': 'qa-tenant-001' },
  });
  let body: any;
  try { body = await res.json(); } catch { body = null; }
  return { status: res.status, body };
}

export async function apiPost(path: string, token: string, payload?: any): Promise<{ status: number; body: any }> {
  const res = await fetch(`${API}${path}`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
      'X-Tenant-ID': 'qa-tenant-001',
    },
    body: payload ? JSON.stringify(payload) : undefined,
  });
  let body: any;
  try { body = await res.json(); } catch { body = null; }
  return { status: res.status, body };
}

// ── Mailpit helper ────────────────────────────────────────────────────────
export async function getMailpitMessages(): Promise<any[]> {
  const res = await fetch(`${MAILPIT}/api/v1/messages`);
  const data = await res.json();
  return data.messages || [];
}

export async function clearMailpit(): Promise<void> {
  await fetch(`${MAILPIT}/api/v1/messages`, { method: 'DELETE' });
}

export async function waitForEmail(subjectFragment: string, timeoutMs = 10000): Promise<any> {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    const msgs = await getMailpitMessages();
    const match = msgs.find((m: any) => m.Subject?.includes(subjectFragment));
    if (match) return match;
    await new Promise(r => setTimeout(r, 500));
  }
  throw new Error(`No email with subject containing "${subjectFragment}" within ${timeoutMs}ms`);
}

// ── Assertion helpers ─────────────────────────────────────────────────────
export async function assertAllowed(path: string, token: string) {
  const { status } = await apiGet(path, token);
  expect(status, `Expected 200 on ${path}`).toBe(200);
}

export async function assertDenied(path: string, token: string) {
  const { status } = await apiGet(path, token);
  expect(status, `Expected 403 on ${path}`).toBe(403);
}

export async function assertPostDenied(path: string, token: string, body?: any) {
  const { status } = await apiPost(path, token, body);
  expect(status, `Expected 403 on POST ${path}`).toBe(403);
}
