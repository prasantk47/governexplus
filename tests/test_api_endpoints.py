"""
Tests for API endpoints — health, auth, root.
"""

import pytest
from services.auth_service import AuthService


class TestRootEndpoints:
    """Tests for root/system endpoints."""

    def test_root_returns_platform_info(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Governex+"
        assert "modules" in data

    def test_health_check(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] in ("healthy", "degraded")
        assert "components" in data

    def test_docs_accessible(self, client):
        resp = client.get("/docs")
        assert resp.status_code == 200


class TestAuthEndpoints:
    """Tests for /auth/* endpoints."""

    def test_login_success(self, client, test_user):
        resp = client.post("/auth/login", json={
            "username": "testuser",
            "password": "TestPassword123!",
            "tenant_id": "tenant_default",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    def test_login_wrong_password(self, client, test_user):
        resp = client.post("/auth/login", json={
            "username": "testuser",
            "password": "wrongpassword123",
            "tenant_id": "tenant_default",
        })
        assert resp.status_code == 401

    def test_login_missing_user(self, client):
        resp = client.post("/auth/login", json={
            "username": "ghost",
            "password": "whatever123",
            "tenant_id": "tenant_default",
        })
        assert resp.status_code == 401

    def test_profile_requires_auth(self, client):
        # The hardened middleware rejects requests without a valid JWT
        resp = client.get("/auth/profile")
        assert resp.status_code == 401  # Authentication required

    def test_profile_with_valid_token(self, client, test_user):
        # Login first
        login_resp = client.post("/auth/login", json={
            "username": "testuser",
            "password": "TestPassword123!",
            "tenant_id": "tenant_default",
        })
        token = login_resp.json()["access_token"]

        # Get profile via auth router (uses Authorization header + tenant)
        resp = client.get(
            "/auth/profile",
            headers={
                "Authorization": f"Bearer {token}",
                "X-Tenant-ID": "tenant_default",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["username"] == "testuser"

    def test_logout_returns_success(self, client, test_user):
        # Login
        login_resp = client.post("/auth/login", json={
            "username": "testuser",
            "password": "TestPassword123!",
            "tenant_id": "tenant_default",
        })
        token = login_resp.json()["access_token"]

        # Logout via auth router
        resp = client.post(
            "/auth/logout",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200

    def test_token_blacklisted_after_logout(self, auth_service, test_user):
        """Verify token blacklisting at the service level."""
        token_resp, _ = auth_service.authenticate(
            "tenant_default", "testuser", "TestPassword123!"
        )
        token = token_resp.access_token

        auth_service.logout("tenant_default", "TEST001", token)

        # Token should be blacklisted
        result, error = auth_service.verify_token(token)
        assert result is None
        assert "revoked" in error.lower()

    def test_info_requires_auth(self, client):
        resp = client.get("/info")
        # HTTPBearer with auto_error=False returns 401 when no token
        assert resp.status_code in (401, 403)


class TestValidation:
    """Tests for request validation."""

    def test_login_missing_fields(self, client):
        resp = client.post("/auth/login", json={})
        assert resp.status_code == 422

    def test_login_empty_body(self, client):
        resp = client.post("/auth/login")
        assert resp.status_code == 422
