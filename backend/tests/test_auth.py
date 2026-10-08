"""
Tests for authentication and authorisation.

Each test verifies one property of the system. They use the fixtures
defined in `conftest.py` (a fresh in-memory database and a TestClient
wired to it), so no test can affect another, and none of them touches the
real `lab.db`.
"""

import pytest

from app import models
from tests.conftest import auth_header


# =============================================================================
# Login
# =============================================================================

def test_login_success(client, test_admin):
    """Valid credentials return 200 with an access token."""
    response = client.post(
        "/api/auth/login",
        json={"email": "admin@test.com", "password": "admin-password-muito-longa-ok"},
    )
    assert response.status_code == 200
    body = response.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"
    assert len(body["access_token"]) > 50


def test_login_wrong_password(client, test_admin):
    """A wrong password returns 401 with the generic message."""
    response = client.post(
        "/api/auth/login",
        json={"email": "admin@test.com", "password": "esta-password-esta-errada"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password."


def test_login_nonexistent_email(client):
    """
    A non-existent email returns 401 with the SAME message.

    This is the user enumeration prevention: the response for "no such
    user" must be indistinguishable from "wrong password".
    """
    response = client.post(
        "/api/auth/login",
        json={"email": "nao-existe@test.com", "password": "alguma-password-aqui"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password."


def test_login_inactive_user(client, db_session):
    """
    An inactive user cannot authenticate, and gets the same message.

    A separate test (not just "user not found") because the code path
    explicitly checks is_active after verifying the password. This
    confirms the inactive branch is exercised.
    """
    from app.security import hash_password

    user = models.User(
        email="inactive@test.com",
        password_hash=hash_password("inactive-password-longa"),
        role="user",
        is_active=False,
    )
    db_session.add(user)
    db_session.commit()

    response = client.post(
        "/api/auth/login",
        json={"email": "inactive@test.com", "password": "inactive-password-longa"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password."


# =============================================================================
# Protected endpoints — authentication
# =============================================================================

def test_protected_endpoint_without_token(client):
    """A protected endpoint rejects a request with no Authorization header."""
    response = client.get("/api/users/me")
    assert response.status_code == 401
    assert "WWW-Authenticate" in response.headers


def test_protected_endpoint_with_invalid_token(client):
    """A malformed or tampered token is rejected with 401."""
    response = client.get(
        "/api/users/me",
        headers={"Authorization": "Bearer not-a-real-jwt"},
    )
    assert response.status_code == 401


def test_protected_endpoint_with_valid_token(client, admin_token):
    """A valid token grants access."""
    response = client.get("/api/users/me", headers=auth_header(admin_token))
    assert response.status_code == 200


# =============================================================================
# /api/users/me
# =============================================================================

def test_users_me_returns_current_user(client, admin_token, test_admin):
    """The endpoint returns the user the token represents."""
    response = client.get("/api/users/me", headers=auth_header(admin_token))
    assert response.status_code == 200
    body = response.json()
    assert body["email"] == "admin@test.com"
    assert body["role"] == "admin"
    assert body["id"] == test_admin.id


def test_user_read_does_not_expose_password_hash(client, admin_token):
    """
    The response schema must never include password_hash.

    This is the field-level access control (level 3 in the threat model).
    If this test ever fails, a data leak has been introduced — the hash
    is not a password, but it is sensitive material.
    """
    response = client.get("/api/users/me", headers=auth_header(admin_token))
    assert response.status_code == 200
    assert "password_hash" not in response.json()
    assert "password" not in response.json()


# =============================================================================
# RBAC — POST /api/users
# =============================================================================

def test_create_user_as_admin(client, admin_token):
    """An admin can create a new user."""
    response = client.post(
        "/api/users",
        headers=auth_header(admin_token),
        json={
            "email": "novo@test.com",
            "password": "password-nova-muito-longa",
            "role": "user",
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "novo@test.com"
    assert body["role"] == "user"
    assert "password_hash" not in body


def test_create_user_as_regular_user_forbidden(client, user_token):
    """
    A regular user (authenticated, but not admin) receives 403 — not 401.

    This is the RBAC distinction: the request is authenticated, but the
    principal is not allowed. 403 tells the client not to retry with a new
    token, which 401 would misleadingly suggest.
    """
    response = client.post(
        "/api/users",
        headers=auth_header(user_token),
        json={
            "email": "outro@test.com",
            "password": "outra-password-muito-longa",
            "role": "user",
        },
    )
    assert response.status_code == 403


def test_create_user_without_token(client):
    """No token means no user creation, even for a valid payload."""
    response = client.post(
        "/api/users",
        json={
            "email": "sem-token@test.com",
            "password": "password-muito-longa-ok",
            "role": "user",
        },
    )
    assert response.status_code == 401


def test_create_user_duplicate_email(client, admin_token, test_user):
    """Creating a user with an existing email returns 409."""
    response = client.post(
        "/api/users",
        headers=auth_header(admin_token),
        json={
            "email": "user@test.com",  # already exists (test_user fixture)
            "password": "password-qualquer-longa",
            "role": "user",
        },
    )
    assert response.status_code == 409


# =============================================================================
# Assets — now protected
# =============================================================================

def test_assets_require_authentication(client):
    """GET /api/assets without a token returns 401."""
    response = client.get("/api/assets")
    assert response.status_code == 401


def test_assets_list_with_token(client, admin_token):
    """GET /api/assets with a valid token returns an empty list on a fresh DB."""
    response = client.get("/api/assets", headers=auth_header(admin_token))
    assert response.status_code == 200
    assert response.json() == []


# =============================================================================
# Refresh tokens
# =============================================================================

def test_login_returns_both_tokens(client, test_admin):
    """Login returns both an access token and a refresh token."""
    response = client.post(
        "/api/auth/login",
        json={"email": "admin@test.com", "password": "admin-password-muito-longa-ok"},
    )
    assert response.status_code == 200
    body = response.json()
    assert "access_token" in body
    assert "refresh_token" in body
    assert body["access_token"] != body["refresh_token"]


def test_refresh_with_valid_refresh_token(client, test_admin):
    """A valid refresh token returns a new pair of tokens."""
    login = client.post(
        "/api/auth/login",
        json={"email": "admin@test.com", "password": "admin-password-muito-longa-ok"},
    )
    refresh_token = login.json()["refresh_token"]

    response = client.post(
        "/api/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert response.status_code == 200
    body = response.json()
    assert "access_token" in body
    assert "refresh_token" in body


def test_refresh_rejects_access_token(client, test_admin):
    """
    An access token cannot be used to refresh.

    Without the `type` claim check, an access token (short-lived) could be
    used to obtain new tokens indefinitely — collapsing the two-token model
    into a single long-lived one.
    """
    login = client.post(
        "/api/auth/login",
        json={"email": "admin@test.com", "password": "admin-password-muito-longa-ok"},
    )
    access_token = login.json()["access_token"]

    response = client.post(
        "/api/auth/refresh",
        json={"refresh_token": access_token},
    )
    assert response.status_code == 401


def test_protected_endpoint_rejects_refresh_token(client, test_admin):
    """
    A refresh token cannot be used as an access token.

    This is the mirror image of the previous test: the refresh token is
    longer-lived (7 days) and must never work on endpoints that expect a
    short-lived access token.
    """
    login = client.post(
        "/api/auth/login",
        json={"email": "admin@test.com", "password": "admin-password-muito-longa-ok"},
    )
    refresh_token = login.json()["refresh_token"]

    response = client.get(
        "/api/users/me",
        headers={"Authorization": f"Bearer {refresh_token}"},
    )
    assert response.status_code == 401
