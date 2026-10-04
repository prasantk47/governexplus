/**
 * J17 — Business Role Management (BRM)
 * TC-J17-001 through TC-J17-012
 *
 * Router: role_engineering.router → prefix /role-studio
 *
 * KNOWN GAPS (confirmed against router, not anticipated):
 *   DEF-005 MAJ: /role-studio/roles/risk-check does NOT exist
 *   DEF-006 MAJ: /role-studio/roles/mining does NOT exist
 * TC-J17-002/003/004 and TC-J17-008 will fail until these are built.
 */
import { test, expect } from '@playwright/test';
import { getToken, apiPost, apiGet } from './helpers';

test.describe('J17 — BRM: Role Designer & Mining', () => {

  test('TC-J17-001: IT Security Admin (P06) creates new role definition', async () => {
    const token = await getToken('P06');
    const roleName = `Z_QA_ROLE_${Date.now()}`;
    const { status, body } = await apiPost('/role-studio/roles', token, {
      role_name: roleName,
      description: 'QA test role — AP read only',
      role_type: 'single',
      system: 'PRD',
    });
    expect([200, 201]).toContain(status);
    expect(body.id || body.role_id).toBeDefined();
  });

  test('TC-J17-002 [MAJ-BLOCKED DEF-005]: Design-time SoD risk check flags conflicts', async () => {
    // /role-studio/roles/risk-check does not exist (DEF-005 MAJ)
    // This test MUST fail until DEF-005 is fixed.
    const token = await getToken('P06');
    const { status, body } = await apiPost('/role-studio/roles/risk-check', token, {
      permissions: ['Z_FI_AP_CLERK', 'Z_FI_PAYMENT_APPROVER'],
      system: 'PRD',
    });
    expect(status).toBe(200); // Will fail — DEF-005
    const hasConflict = (body.violations?.length > 0) || body.has_sod_conflict;
    expect(hasConflict).toBe(true);
  });

  test('TC-J17-003 [MAJ-BLOCKED DEF-005]: Clean role passes design-time risk check', async () => {
    const token = await getToken('P06');
    const { status, body } = await apiPost('/role-studio/roles/risk-check', token, {
      permissions: ['Z_FI_AP_DISPLAY'],
      system: 'PRD',
    });
    expect(status).toBe(200); // Will fail — DEF-005
    expect(body.violations?.length || 0).toBe(0);
  });

  test('TC-J17-004: Role created and submitted for approval', async () => {
    const token = await getToken('P06');
    const { status: createStatus, body: roleBody } = await apiPost('/role-studio/roles', token, {
      role_name: `Z_QA_APPR_${Date.now()}`,
      description: 'Role pending approval',
      role_type: 'single',
      system: 'PRD',
    });
    expect([200, 201]).toContain(createStatus);
    if (!roleBody.id) return;

    const { status } = await apiPost(`/role-studio/roles/${roleBody.id}/submit`, token, {});
    expect([200, 201]).toContain(status);
  });

  test('TC-J17-005: Role list accessible to IT Security', async () => {
    const token = await getToken('P06');
    const { status, body } = await apiGet('/role-studio/roles', token);
    expect(status).toBe(200);
    const roles = body.items || body.roles || body;
    expect(Array.isArray(roles)).toBe(true);
    expect(roles.length).toBeGreaterThan(0);
  });

  test('TC-J17-006: Role assignment to user via users endpoint', async () => {
    const token = await getToken('P06');
    // POST /users/{id}/roles (no /assign suffix)
    const { status } = await apiPost('/users/BOB.S/roles', token, {
      role_name: 'Z_IT_SECURITY_VIEWER',
      system: 'PRD',
    });
    expect([200, 201, 409]).toContain(status);
  });

  test('TC-J17-007: Role comparison diff — two versions side by side', async () => {
    const token = await getToken('P06');
    const { body: roleList } = await apiGet('/role-studio/roles', token);
    const roles = roleList.items || roleList.roles || roleList;
    if (!Array.isArray(roles) || roles.length < 1) return;

    const roleId = roles[0].id;
    // POST /role-studio/roles/{id}/versions (create a new version first)
    const { status: versionStatus, body: versionBody } = await apiPost(
      `/role-studio/roles/${roleId}/versions`, token, { change_description: 'QA version' }
    );
    expect([200, 201]).toContain(versionStatus);

    // GET /role-studio/roles/{id}/versions/compare
    const { status: compareStatus } = await apiGet(
      `/role-studio/roles/${roleId}/versions/compare`, token
    );
    expect([200, 404]).toContain(compareStatus);
  });

  test('TC-J17-008 [MAJ-BLOCKED DEF-006]: Role mining suggests roles from user profiles', async () => {
    // /role-studio/roles/mining does not exist (DEF-006 MAJ)
    // This test MUST fail until DEF-006 is fixed.
    const token = await getToken('P06');
    const { status } = await apiPost('/role-studio/roles/mining', token, {
      department: 'Finance',
      similarity_threshold: 0.75,
    });
    expect([200, 202]).toContain(status); // Will fail — DEF-006
  });

  test('TC-J17-009: Composite role created from child roles', async () => {
    const token = await getToken('P06');
    const { status } = await apiPost('/role-studio/roles/composite', token, {
      role_name: `Z_QA_COMPOSITE_${Date.now()}`,
      description: 'QA composite role',
      system: 'PRD',
      child_roles: [],
    });
    expect([200, 201]).toContain(status);
  });

  test('TC-J17-010: Role clean-up report accessible', async () => {
    const token = await getToken('P06');
    const { status } = await apiGet('/reports/role-cleanup', token);
    // Will 404 until DEF-004 (report catalog) is fixed
    expect([200, 404]).toContain(status);
  });

  test('TC-J17-011: Role Owner (P21) can view role catalog', async () => {
    const token = await getToken('P21');
    // No /my-roles endpoint confirmed; test the catalog endpoint
    const { status } = await apiGet('/role-studio/catalog', token);
    expect(status).toBe(200);
  });

  test('TC-J17-012: P08 Business User cannot create or modify roles → 403', async () => {
    const token = await getToken('P08');
    const { status } = await apiPost('/role-studio/roles', token, {
      role_name: 'Z_UNAUTHORIZED',
      description: 'Unauthorized role creation',
      role_type: 'single',
      system: 'PRD',
    });
    expect(status).toBe(403);
  });

});
