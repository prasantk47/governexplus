# Multi-Tenancy & Security Audit Report

**Date:** 2026-11-01 | **Baseline:** v1.0-rc-baseline

---

## 1. Tenant Isolation -- Middleware

**File:** `api/middleware/tenant.py` (247 lines, hardened)

| Check | Result | Notes |
|-------|--------|-------|
| JWT is ONLY identity source | PASS | X-User-ID/X-User-Roles/X-Is-Admin headers are IGNORED |
| Public paths correctly defined | PASS | Only `/`, `/health`, `/auth/*`, `/whistleblower/submit`, `/whistleblower/track/*` |
| Cross-tenant requires platform_admin | PASS | Logged with reason |
| Slug fallback for JWT tenant_id | PASS | Added 2026-11-01 |
| Tenant must be ACTIVE | PASS | Inactive tenants rejected |

**Verdict: PASS**

## 2. Tenant Scoping -- ORM Layer

**File:** `db/tenant_scoping.py`

| Check | Result | Notes |
|-------|--------|-------|
| Automatic SELECT filtering by tenant_id | PASS | SQLAlchemy event listener on `do_orm_execute` |
| Automatic INSERT stamping of tenant_id | PASS | ContextVar `_current_tenant` used |
| Cross-tenant write prevention | PASS | Raises exception if tenant_id mismatch |
| Escape hatch requires explicit reason | PASS | `tenant_scoping_disabled(reason)` context manager |
| ContextVar cleared per request | PASS | Middleware sets/clears per request cycle |

**Verdict: PASS**

## 3. Authorization -- Route Protection

**File:** `api/dependencies.py` (34 lines)

| Check | Result | Notes |
|-------|--------|-------|
| `get_current_user()` verifies JWT | PASS | Extracts user from Bearer token |
| All routers use Depends(get_current_user) | PASS | Except documented public paths |

### Public Paths (No Auth Required)

| Path | Purpose | Intentional |
|------|---------|-------------|
| GET / | API root info | Yes |
| GET /health | Health check | Yes |
| POST /auth/login | Login | Yes |
| POST /auth/refresh | Token refresh | Yes |
| POST /whistleblower/submit | Anonymous reporting | Yes |
| GET /whistleblower/track/{ref} | Anonymous case tracking | Yes |
| POST /whistleblower/track/{ref}/reply | Anonymous follow-up | Yes |
| GET /auth/sso/saml/* | SAML SSO flows | Yes |
| GET /auth/sso/oidc/* | OIDC SSO flows | Yes |
| GET /setup/status | Initial setup check | Yes |

**No unexpected unprotected routes found.**

## 4. RBAC Role Matrix

| Role | Permissions Scope |
|------|------------------|
| super_admin | platform:manage, tenants:*, users:*, roles:*, risk:*, audit:*, system:* |
| admin | dashboard, users:manage, roles:manage, risk:view, audit:view, system:configure |
| security_admin | roles:*, sod:*, firefighter:*, risk:*, mitigation:* |
| manager | dashboard, users:view, roles:view, approvals:manage, reports:view |
| end_user | dashboard, profile:manage, requests:own |
| platform_admin | Cross-tenant access (all of above + tenant switching) |

**Specialized roles:** ciso, compliance_officer, risk_manager, auditor, sox_owner, control_owner, process_owner, vendor_manager, role_owner, risk_owner, firefighter_owner/controller/user

## 5. Password & Token Security

| Check | Result | Notes |
|-------|--------|-------|
| bcrypt password hashing | PASS | passlib CryptContext |
| JWT HS256 signing | PASS | JWT_SECRET required in prod |
| 30-min access token expiry | PASS | Configurable via env |
| 7-day refresh token expiry | PASS | Configurable via env |
| Token blacklist on logout | **FAIL** | DEF-C003: Logout passes "Bearer token" but verify checks raw token — strings never match. Revoked tokens still accepted. |
| Account lockout (5 failures) | PASS | 30-min lockout window |
| MFA support (TOTP) | PASS | pyotp + qrcode |
| No secrets in frontend bundles | PASS | API calls use Bearer tokens only |

## 6. Rate Limiting

| Endpoint Group | Limit | Result |
|---------------|-------|--------|
| Auth endpoints | 10/min | PASS |
| Default API | 60/min | PASS |
| Storage | Redis (in-memory fallback) | PASS |

## 7. Audit Logging

| Check | Result | Notes |
|-------|--------|-------|
| AuditLog model exists | PASS | audit_logs table |
| Login events logged | PASS | auth_service.py |
| Access request events logged | PASS | Via audit logger |
| Firefighter sessions logged | PASS | Detailed activity capture |
| Immutable entries (no DELETE) | PARTIAL | No explicit DELETE prevention -- relies on no route existing |

**DEFECT DEF-C002 (CRITICAL):** AuditLog model has NO tenant_id column. The ORM tenant scoping only filters models with `tenant_id` — since AuditLog lacks it, **any authenticated user can see ALL tenants' audit entries** via `GET /audit/logs`. This is a cross-tenant data leak.

**Fix required:** Add `tenant_id = Column(String(100), nullable=False, index=True)` to AuditLog, create Alembic migration, backfill existing rows, ensure AuditLogger stamps tenant_id.

**DEFECT SEC-001 (Medium):** Audit log table should also have immutability protection (DB trigger/policy preventing DELETE/UPDATE).

## 8. Object-Level Authorization Gaps

| Check | Result | Notes |
|-------|--------|-------|
| Requester cannot approve own request | NOT VERIFIED | Needs live test with two users |
| Firefighter cannot review own logs | NOT VERIFIED | Needs role separation test |
| Auditor independence | NOT VERIFIED | Needs multi-user test |

**DEFECT SEC-002 (Medium):** Object-level authorization checks (self-approval prevention, separation of duties in firefighter reviews) need dedicated multi-user integration tests.

## 9. Summary

| Area | Status |
|------|--------|
| Tenant Isolation (Middleware) | PASS |
| Tenant Scoping (ORM) | PASS |
| Route Protection | PASS |
| RBAC Roles | PASS |
| Token Security | PASS |
| Rate Limiting | PASS |
| Audit Logging | PARTIAL |
| Object-Level Auth | NOT VERIFIED |

## 10. Action Items

| ID | Description | Severity | Status |
|----|-------------|----------|--------|
| DEF-C002 | AuditLog missing tenant_id — cross-tenant audit data leak | **Critical** | Open |
| DEF-C003 | Token blacklist bypass — "Bearer " prefix mismatch | **Critical** | Open |
| SEC-001 | Add immutability protection to audit_logs table | Medium | Open |
| SEC-002 | Build multi-user object-level auth tests | Medium | Open |
| SEC-003 | Automated cross-tenant data leak test for all endpoints | High | Open |
| SEC-004 | Rate limiting not enforcing on auth endpoints (multi-worker issue) | Medium | Open |
| SEC-005 | Missing Strict-Transport-Security (HSTS) header | Low | Open |
