# Regression Suite README

**Date:** 2026-11-01 | **Baseline:** v1.0-rc-baseline

---

## Overview

The regression suite consists of multiple test layers designed to prove GovernexPlus works end-to-end and to prevent regressions on every change.

## Test Layers

### 1. Backend Unit Tests (pytest)
**Location:** `tests/`
**Framework:** pytest + SQLite in-memory
**Run:** `python -m pytest tests/ --tb=short -q`

**Current Status:** 7 pass, 16 fail (enum serialization issue with SQLite -- DEF-H004)

**Existing test files:**
- test_auth_service.py (23 tests -- login, tokens, logout, role determination)
- test_api_endpoints.py
- test_audit_management.py
- test_risk_management.py
- test_process_control.py
- test_sod_rules.py
- test_custom_ruleset.py
- test_drift.py
- test_e2e_golden_flow.py
- test_fiori.py
- test_identity_correlation.py
- test_migration.py
- test_notification_delivery.py
- test_role_intelligence.py
- test_troubleshooter.py

**Fix needed:** Resolve enum serialization in audit logger for SQLite compatibility.

### 2. Live API Health Check
**Location:** `scripts/health_check.py`
**Run:** `python scripts/health_check.py`
**Purpose:** Tests 52 key endpoints against production
**Current results:** 30 OK, 19 404 (path differences), 2 405, 1 500

### 3. Extensive Data Seeder (Integration Test)
**Location:** `scripts/seed_extensive.py`
**Run:** `python scripts/seed_extensive.py`
**Purpose:** Creates 171 records across all 10 modules via live API
**Current results:** 171/171 records created, 0 failures

### 4. Two-Tenant Isolation Test
**Status:** NOT YET BUILT
**Requirement:** Iterate all CRUD endpoints, verify Tenant A token cannot access Tenant B data

### 5. Migration Drift Test
**Status:** NOT YET BUILT
**Requirement:** Compare Base.metadata with live DB schema, report drift

### 6. Playwright E2E Suite
**Status:** NOT YET BUILT
**Requirement:** Cover all 12 mandatory business journeys from Phase 8

---

## CI Integration Plan

### Smoke Suite (~10 min, every PR)
- [ ] Backend unit tests (pytest)
- [ ] API health check (scripts/health_check.py)
- [ ] Frontend build (npm run build)

### Full Suite (nightly + pre-release)
- [ ] All smoke tests
- [ ] Extensive data seeder
- [ ] Tenant isolation test
- [ ] Migration drift test
- [ ] Playwright E2E journeys

### Release Gate
CI must be GREEN on full suite before any release tag.

---

## How to Run Locally

```bash
# Backend tests
cd d:/Governexplus
python -m pytest tests/ --tb=short -q

# API health check (requires production access)
python scripts/health_check.py

# Extensive seeder (requires production access)
python scripts/seed_extensive.py

# Frontend build
cd frontend
npm run build
```

## How to Run on Server

```bash
ssh root@212.47.75.51
cd /opt/governexplus/app
source venv/bin/activate
python -m pytest tests/ --tb=short -q
```

---

## Test Data Fixtures

### conftest.py Fixtures
- `db_engine` -- Fresh SQLite per test
- `db_session` -- Transaction-isolated session
- `test_user` -- Standard user (Finance dept)
- `admin_user` -- Admin user (Security dept)
- `locked_user` -- Locked account (5 failed logins)
- `auth_service` -- AuthService with test DB
- `client` -- FastAPI TestClient with overridden DB
- `module_*` variants -- Shared across test module (avoids rate limit on auth)

### Production Test Tenant
- Tenant: `acme-corp-demo`
- Admin: `acme_admin` / `AcmeP@ss2026!`
- Data: 171+ seeded records across all modules
