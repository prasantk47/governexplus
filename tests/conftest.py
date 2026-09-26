"""
Shared test fixtures for GovernexPlus.

Provides:
- In-memory SQLite test database
- Test FastAPI client
- Pre-seeded user fixtures
"""

import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Set test environment before importing app code
os.environ["APP_ENV"] = "testing"
os.environ["JWT_SECRET"] = "test-secret-key-for-testing-only"

from db.models import Base
from db.models.user import User
from db.database import get_db
from services.auth_service import AuthService


@pytest.fixture(scope="function")
def db_engine():
    """Create a fresh in-memory SQLite engine per test."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture(scope="function")
def db_session(db_engine):
    """Create a new database session for a test."""
    Session = sessionmaker(bind=db_engine, autocommit=False, autoflush=False)
    session = Session()
    yield session
    session.rollback()
    session.close()


@pytest.fixture(scope="function")
def test_user(db_session) -> User:
    """Create a test user with bcrypt-hashed password."""
    password_hash = AuthService.hash_password("TestPassword123!")
    user = User(
        user_id="TEST001",
        username="testuser",
        email="test@example.com",
        full_name="Test User",
        department="Finance",
        status="active",
        password_hash=password_hash,
        tenant_id="tenant_default",
        user_type="standard",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture(scope="function")
def admin_user(db_session) -> User:
    """Create an admin user (security dept triggers security_admin role)."""
    password_hash = AuthService.hash_password("AdminPass123!")
    user = User(
        user_id="ADMIN001",
        username="admin",
        email="admin@example.com",
        full_name="Admin User",
        department="Security Administration",
        status="active",
        password_hash=password_hash,
        tenant_id="tenant_default",
        user_type="admin",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture(scope="function")
def locked_user(db_session) -> User:
    """Create a locked user."""
    password_hash = AuthService.hash_password("LockedPass123!")
    user = User(
        user_id="LOCKED001",
        username="lockeduser",
        email="locked@example.com",
        full_name="Locked User",
        department="Finance",
        status="locked",
        password_hash=password_hash,
        tenant_id="tenant_default",
        user_type="standard",
        failed_login_count=5,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture(scope="function")
def auth_service(db_session) -> AuthService:
    """Create an AuthService instance with test DB."""
    return AuthService(db_session)


def _make_test_client(db_engine):
    """Shared helper: build a TestClient wired to the given engine."""
    from fastapi.testclient import TestClient
    from api.main import app as fastapi_app

    Session = sessionmaker(bind=db_engine, autocommit=False, autoflush=False)

    def override_get_db():
        session = Session()
        try:
            yield session
        finally:
            session.close()

    fastapi_app.dependency_overrides[get_db] = override_get_db
    test_client = TestClient(fastapi_app)

    original_get = test_client.get
    original_post = test_client.post

    def _merge_headers(kwargs):
        headers = kwargs.get("headers", {})
        if "X-Tenant-ID" not in headers:
            headers["X-Tenant-ID"] = "tenant_demo"
            kwargs["headers"] = headers
        return kwargs

    def get_with_tenant(url, **kwargs):
        return original_get(url, **_merge_headers(kwargs))

    def post_with_tenant(url, **kwargs):
        return original_post(url, **_merge_headers(kwargs))

    test_client.get = get_with_tenant
    test_client.post = post_with_tenant
    return test_client, fastapi_app


@pytest.fixture(scope="function")
def client(db_engine):
    """Create a test HTTP client with overridden DB (function scope)."""
    test_client, fastapi_app = _make_test_client(db_engine)
    yield test_client
    fastapi_app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Module-scoped fixtures — used by test modules that share a single login
# token across all tests to avoid hitting the auth rate limit.
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def module_db_engine():
    """Single in-memory SQLite engine shared across a whole test module."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture(scope="module")
def module_db_session(module_db_engine):
    """Single DB session for the module (not rolled back between tests)."""
    Session = sessionmaker(bind=module_db_engine, autocommit=False, autoflush=False)
    session = Session()
    yield session
    session.close()


@pytest.fixture(scope="module")
def module_test_user(module_db_session) -> User:
    """Create a test user once for the whole module."""
    password_hash = AuthService.hash_password("TestPassword123!")
    user = User(
        user_id="TEST001",
        username="testuser",
        email="test@example.com",
        full_name="Test User",
        department="Finance",
        status="active",
        password_hash=password_hash,
        tenant_id="tenant_default",
        user_type="standard",
    )
    module_db_session.add(user)
    module_db_session.commit()
    module_db_session.refresh(user)
    return user


@pytest.fixture(scope="module")
def module_client(module_db_engine):
    """Test HTTP client shared across a whole test module."""
    test_client, fastapi_app = _make_test_client(module_db_engine)
    yield test_client
    fastapi_app.dependency_overrides.clear()
