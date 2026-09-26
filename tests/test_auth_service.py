"""
Tests for AuthService — authentication, JWT tokens, password hashing.
"""

import pytest
import jwt
from datetime import datetime, timedelta

from services.auth_service import AuthService, JWT_SECRET, JWT_ALGORITHM


class TestPasswordHashing:
    """Tests for bcrypt password hashing."""

    def test_hash_password_produces_bcrypt_hash(self):
        hashed = AuthService.hash_password("MyPassword123!")
        assert hashed.startswith("$2b$")

    def test_hash_password_different_each_time(self):
        h1 = AuthService.hash_password("same")
        h2 = AuthService.hash_password("same")
        assert h1 != h2  # bcrypt uses random salt

    def test_verify_correct_password(self, auth_service):
        hashed = AuthService.hash_password("correct")
        assert auth_service._verify_password("correct", hashed) is True

    def test_verify_wrong_password(self, auth_service):
        hashed = AuthService.hash_password("correct")
        assert auth_service._verify_password("wrong", hashed) is False

    def test_verify_empty_hash_returns_false(self, auth_service):
        assert auth_service._verify_password("any", "") is False
        assert auth_service._verify_password("any", None) is False


class TestAuthentication:
    """Tests for login flow."""

    def test_login_success(self, auth_service, test_user):
        token_resp, error = auth_service.authenticate(
            tenant_id="tenant_default",
            username="testuser",
            password="TestPassword123!",
        )
        assert error is None
        assert token_resp is not None
        assert token_resp.access_token
        assert token_resp.refresh_token
        assert token_resp.token_type == "bearer"
        assert token_resp.user.username == "testuser"

    def test_login_by_email(self, auth_service, test_user):
        token_resp, error = auth_service.authenticate(
            tenant_id="tenant_default",
            username="test@example.com",
            password="TestPassword123!",
        )
        assert error is None
        assert token_resp is not None

    def test_login_wrong_password(self, auth_service, test_user):
        token_resp, error = auth_service.authenticate(
            tenant_id="tenant_default",
            username="testuser",
            password="WrongPassword!",
        )
        assert token_resp is None
        assert error == "Invalid username or password"

    def test_login_unknown_user(self, auth_service):
        token_resp, error = auth_service.authenticate(
            tenant_id="tenant_default",
            username="nobody",
            password="whatever",
        )
        assert token_resp is None
        assert error == "Invalid username or password"

    def test_login_locked_user(self, auth_service, locked_user):
        token_resp, error = auth_service.authenticate(
            tenant_id="tenant_default",
            username="lockeduser",
            password="LockedPass123!",
        )
        assert token_resp is None
        assert "locked" in error.lower()

    def test_account_locks_after_5_failures(self, auth_service, test_user, db_session):
        for _ in range(5):
            auth_service.authenticate(
                tenant_id="tenant_default",
                username="testuser",
                password="wrong",
            )

        db_session.refresh(test_user)
        assert test_user.status == "locked"
        assert test_user.failed_login_count >= 5

    def test_successful_login_resets_failure_count(self, auth_service, test_user, db_session):
        # Fail twice
        auth_service.authenticate("tenant_default", "testuser", "wrong")
        auth_service.authenticate("tenant_default", "testuser", "wrong")
        # Then succeed
        auth_service.authenticate("tenant_default", "testuser", "TestPassword123!")

        db_session.refresh(test_user)
        assert test_user.failed_login_count == 0


class TestTokens:
    """Tests for JWT token creation and verification."""

    def test_access_token_is_valid_jwt(self, auth_service, test_user):
        token_resp, _ = auth_service.authenticate(
            "tenant_default", "testuser", "TestPassword123!"
        )
        payload = jwt.decode(token_resp.access_token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        assert payload["sub"] == "TEST001"
        assert payload["type"] == "access"
        assert payload["tenant_id"] == "tenant_default"

    def test_refresh_token_type(self, auth_service, test_user):
        token_resp, _ = auth_service.authenticate(
            "tenant_default", "testuser", "TestPassword123!"
        )
        payload = jwt.decode(token_resp.refresh_token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        assert payload["type"] == "refresh"

    def test_verify_valid_token(self, auth_service, test_user):
        token_resp, _ = auth_service.authenticate(
            "tenant_default", "testuser", "TestPassword123!"
        )
        payload, error = auth_service.verify_token(token_resp.access_token)
        assert error is None
        assert payload["sub"] == "TEST001"

    def test_verify_expired_token(self, auth_service):
        # Manually create an expired token
        payload = {
            "sub": "TEST001",
            "type": "access",
            "exp": datetime.utcnow() - timedelta(hours=1),
            "iat": datetime.utcnow() - timedelta(hours=2),
        }
        expired_token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
        result, error = auth_service.verify_token(expired_token)
        assert result is None
        assert "expired" in error.lower()

    def test_verify_invalid_token(self, auth_service):
        result, error = auth_service.verify_token("not.a.valid.token")
        assert result is None
        assert error is not None

    def test_verify_refresh_token_as_access_fails(self, auth_service, test_user):
        token_resp, _ = auth_service.authenticate(
            "tenant_default", "testuser", "TestPassword123!"
        )
        result, error = auth_service.verify_token(token_resp.refresh_token)
        assert result is None
        assert "invalid token type" in error.lower()


class TestLogout:
    """Tests for token blacklisting / logout."""

    def test_logout_blacklists_token(self, auth_service, test_user):
        token_resp, _ = auth_service.authenticate(
            "tenant_default", "testuser", "TestPassword123!"
        )
        token = token_resp.access_token

        auth_service.logout("tenant_default", "TEST001", token)

        assert AuthService.is_token_blacklisted(token) is True

        # Verify returns error for blacklisted token
        result, error = auth_service.verify_token(token)
        assert result is None
        assert "revoked" in error.lower()

    def test_non_blacklisted_token_works(self, auth_service, test_user):
        # Clear blacklist to avoid collision with test_logout_blacklists_token
        # (same user + same-second JWT → identical token string)
        AuthService._blacklisted_tokens.clear()
        token_resp, _ = auth_service.authenticate(
            "tenant_default", "testuser", "TestPassword123!"
        )
        assert AuthService.is_token_blacklisted(token_resp.access_token) is False


class TestRoleDetermination:
    """Tests for role assignment logic."""

    def test_admin_username_gets_admin_role(self, auth_service, admin_user):
        # username "admin" maps to admin role by username check
        token_resp, _ = auth_service.authenticate(
            "tenant_default", "admin", "AdminPass123!"
        )
        assert token_resp.user.role == "admin"

    def test_finance_user_gets_end_user_role(self, auth_service, test_user):
        token_resp, _ = auth_service.authenticate(
            "tenant_default", "testuser", "TestPassword123!"
        )
        assert token_resp.user.role == "end_user"

    def test_security_dept_user_gets_security_admin(self, auth_service, test_user, db_session):
        # Change username to something neutral, set security department
        test_user.username = "secuser"
        test_user.department = "IT Security"
        db_session.commit()

        token_resp, _ = auth_service.authenticate(
            "tenant_default", "secuser", "TestPassword123!"
        )
        assert token_resp.user.role == "security_admin"
