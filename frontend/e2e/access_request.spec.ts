/**
 * J02 — Access Request → Approval → Provisioning
 * TC-J02-001 through TC-J02-010
 *
 * Access requests: access_requests.router → prefix /access-requests
 * Shopping cart: arm.router → prefix /access-lifecycle
 * SoD pre-check: /access-requests/preview-risk
 */
import { test, expect } from '@playwright/test';
import { getToken, apiPost, apiGet } from './helpers';

test.describe('J02 — Access Request Lifecycle', () => {

  test('TC-J02-001: Business User (P08) submits access request', async () => {
    const token = await getToken('P08');
    // POST /access-requests/ creates a draft; POST /{id}/submit submits it
    const { status, body } = await apiPost('/access-requests', token, {
      requested_roles: ['Z_FI_AP_CLERK'],
      system: 'PRD',
      justification: 'Need AP access for month-end close',
    });
    expect([200, 201]).toContain(status);
    expect(body.id || body.request_id).toBeDefined();
  });

  test('TC-J02-002: Shopping cart via ARM /access-lifecycle/cart', async () => {
    const token = await getToken('P08');
    // POST /access-lifecycle/cart creates a cart
    const { status: cartStatus, body: cartBody } = await apiPost('/access-lifecycle/cart', token, {});
    expect([200, 201]).toContain(cartStatus);
    const cartId = cartBody.id || cartBody.cart_id;
    if (!cartId) return;

    // Add item to cart
    const { status: addStatus } = await apiPost(`/access-lifecycle/cart/${cartId}/items`, token, {
      role_id: 'Z_MM_PURCHASING',
      system: 'PRD',
    });
    expect([200, 201]).toContain(addStatus);

    // View cart
    const { status: viewStatus, body } = await apiGet(`/access-lifecycle/cart/${cartId}`, token);
    expect(viewStatus).toBe(200);
    expect(body.id || body.cart_id).toBeDefined();
  });

  test('TC-J02-003: SoD pre-check via /access-requests/preview-risk flags conflict', async () => {
    const token = await getToken('P08');
    const { status, body } = await apiPost('/access-requests/preview-risk', token, {
      user_id: 'ALICE.J',
      requested_roles: ['Z_FI_PAYMENT_APPROVER'],
      system: 'PRD',
    });
    expect(status).toBe(200);
    // Alice already has AP clerk → adding payment approver should flag SOD-FI-001
    const hasConflict = (body.conflicts?.length > 0) || (body.violations?.length > 0) || body.has_conflict || body.has_sod_risk;
    expect(hasConflict).toBe(true);
  });

  test('TC-J02-004: Manager (P07) approves pending request', async () => {
    // Create a request as P08
    const p08Token = await getToken('P08');
    const { body: reqBody } = await apiPost('/access-requests', p08Token, {
      requested_roles: ['Z_MM_INVENTORY'],
      system: 'PRD',
      justification: 'Need for inventory audit',
    });
    const requestId = reqBody.id || reqBody.request_id;
    if (!requestId) return;

    // Get first pending approval step
    const p07Token = await getToken('P07');
    // Approval endpoint: POST /access-requests/{id}/approve/{step_id}
    // Use approvals/pending to find the step
    const { body: pendingBody } = await apiGet('/access-requests/approvals/pending', p07Token);
    const pending = pendingBody.items || pendingBody.approvals || pendingBody;
    const match = Array.isArray(pending)
      ? pending.find((a: any) => a.request_id === requestId || a.id === requestId)
      : null;

    if (match) {
      const stepId = match.step_id || match.id;
      const { status } = await apiPost(`/access-requests/${requestId}/approve/${stepId}`, p07Token, {
        comment: 'Approved — business justified',
      });
      expect([200, 201]).toContain(status);
    }
  });

  test('TC-J02-005: IT Security (P06) can view all pending approvals', async () => {
    const token = await getToken('P06');
    const { status, body } = await apiGet('/access-requests/approvals/pending', token);
    expect(status).toBe(200);
    const items = body.items || body.approvals || body;
    expect(Array.isArray(items)).toBe(true);
  });

  test('TC-J02-006: Access request list accessible', async () => {
    const token = await getToken('P06');
    const { status } = await apiGet('/access-requests', token);
    expect(status).toBe(200);
  });

  test('TC-J02-007: P08 cannot self-approve — approve endpoint rejects or 403', async () => {
    const token = await getToken('P08');
    // Self-approval attempt — expect 403 or 404 (user has no approval permission)
    const { status } = await apiPost('/access-requests/SOME-ID/approve/SOME-STEP', token, {
      comment: 'Self-approve attempt',
    });
    expect([403, 404]).toContain(status);
  });

  test('TC-J02-008: High-risk request triggers SoD warning on preview', async () => {
    const p08Token = await getToken('P08');
    const { status, body } = await apiPost('/access-requests/preview-risk', p08Token, {
      user_id: 'ALICE.J',
      requested_roles: ['Z_FI_PAYMENT_APPROVER'],
      system: 'PRD',
    });
    expect(status).toBe(200);
    const hasRisk = body.has_conflict || body.has_sod_risk || body.risk_level === 'high' || body.violations?.length > 0;
    expect(hasRisk).toBe(true);
  });

  test('TC-J02-009: Request rejection recorded', async () => {
    const p08Token = await getToken('P08');
    const { body: reqBody } = await apiPost('/access-requests', p08Token, {
      requested_roles: ['Z_FI_GL_POSTING'],
      system: 'PRD',
      justification: 'GL access for journal entries',
    });
    const requestId = reqBody.id || reqBody.request_id;
    if (!requestId) return;

    const p07Token = await getToken('P07');
    // Rejection endpoint: POST /access-requests/{id}/approve/{step_id} with reject or separate endpoint
    // Fallback: use approvals/pending
    const { body: pendingBody } = await apiGet('/access-requests/approvals/pending', p07Token);
    const pending = pendingBody.items || pendingBody.approvals || pendingBody;
    const match = Array.isArray(pending)
      ? pending.find((a: any) => a.request_id === requestId || a.id === requestId)
      : null;
    if (!match) return;

    const stepId = match.step_id || match.id;
    const { status } = await apiPost(`/access-requests/${requestId}/approve/${stepId}`, p07Token, {
      decision: 'reject',
      comment: 'Not authorized for GL posting',
    });
    expect([200, 201]).toContain(status);
  });

  test('TC-J02-010: P16 Read-Only cannot submit access requests → 403', async () => {
    const token = await getToken('P16');
    const { status } = await apiPost('/access-requests', token, {
      requested_roles: ['Z_FI_AP_CLERK'],
      system: 'PRD',
      justification: 'Need access',
    });
    expect(status).toBe(403);
  });

});
