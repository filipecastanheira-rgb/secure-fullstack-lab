"""
Pytest fixtures shared by all tests.

Fixtures are functions that pytest injects into test functions by name.
Anything defined here is available to every test file in the project
without an explicit import.

The goal of this file is to make each test read as a declaration of intent
(what is being verified) rather than a repeated block of setup code.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.security import hash_password
from app import models


# =============================================================================
# Database
# =============================================================================

@pytest.fixture()
def db_session():
    """
    Provide a fresh, in-memory SQLite database for a single test.

    `StaticPool` is used so that all connections from the same engine share
    the same in-memory database. Without it, SQLite creates a new empty
    database for each connection — which would defeat the purpose.

    The database is created (via create_all) when the fixture starts and
    discarded when the test ends. Every test sees a clean state.
    """
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    Base.metadata.create_all(bind=engine)

    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


# =============================================================================
# HTTP client
# =============================================================================

@pytest.fixture()
def client(db_session):
    """
    FastAPI TestClient wired to the test database.

    `app.dependency_overrides` is FastAPI's mechanism for swapping a
    dependency's implementation during tests. Here we replace `get_db`
    (which normally returns a session to `lab.db`) with a function that
    returns the test session.

    The override is removed after the test, so that subsequent tests get
    the real dependency back.
    """
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# =============================================================================
# Users
# =============================================================================

ADMIN_EMAIL = "admin@test.com"
ADMIN_PASSWORD = "admin-password-muito-longa-ok"

USER_EMAIL = "user@test.com"
USER_PASSWORD = "user-password-muito-longa-ok"


@pytest.fixture()
def test_admin(db_session):
    """Create an admin user in the test database."""
    user = models.User(
        email=ADMIN_EMAIL,
        password_hash=hash_password(ADMIN_PASSWORD),
        role="admin",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture()
def test_user(db_session):
    """Create a regular user in the test database."""
    user = models.User(
        email=USER_EMAIL,
        password_hash=hash_password(USER_PASSWORD),
        role="user",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


# =============================================================================
# Tokens
# =============================================================================

@pytest.fixture()
def admin_token(client, test_admin):
    """
    Obtain a valid access token for the admin user by calling the login
    endpoint. Using the real endpoint (rather than minting a token
    directly) means the fixture exercises the same code path the client
    would, so a broken login flow fails tests immediately.
    """
    response = client.post(
        "/api/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


@pytest.fixture()
def user_token(client, test_user):
    """Obtain a valid access token for the regular user."""
    response = client.post(
        "/api/auth/login",
        json={"email": USER_EMAIL, "password": USER_PASSWORD},
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def auth_header(token: str) -> dict:
    """Build an Authorization header from a token. Convenience helper."""
    return {"Authorization": f"Bearer {token}"}
