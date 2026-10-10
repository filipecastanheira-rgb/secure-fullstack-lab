"""
Tests for row-level authorisation on assets.

These tests verify a property that no scanner checks: a user must only be
able to read their own assets. This is the L2 level of the three-level
authorisation model (see threat model §7.3).

The SQL injection exercise showed what a SAST scanner detects and does
not detect. This file shows the complement: what a written test can
detect that a pattern-based scanner cannot. A missing `owner_id` filter
is not a syntax error and not an unsafe pattern. It is a missing
condition, and only a test that knows the policy can find it.
"""

import pytest

from app import models
from tests.conftest import auth_header


@pytest.fixture()
def admin_asset(db_session, test_admin):
    """An asset owned by the admin user."""
    asset = models.Asset(
        hostname="admin-server",
        ip_address="10.10.10.1",
        os="Ubuntu",
        owner_id=test_admin.id,
    )
    db_session.add(asset)
    db_session.commit()
    db_session.refresh(asset)
    return asset


@pytest.fixture()
def user_asset(db_session, test_user):
    """An asset owned by the regular user."""
    asset = models.Asset(
        hostname="user-laptop",
        ip_address="10.10.10.2",
        os="Windows",
        owner_id=test_user.id,
    )
    db_session.add(asset)
    db_session.commit()
    db_session.refresh(asset)
    return asset


# =============================================================================
# Happy path — each user reads their own asset
# =============================================================================

def test_admin_can_read_own_asset(client, admin_token, admin_asset):
    """A user can read an asset they own."""
    response = client.get(
        f"/api/assets/{admin_asset.id}",
        headers=auth_header(admin_token),
    )
    assert response.status_code == 200
    assert response.json()["hostname"] == "admin-server"


def test_user_can_read_own_asset(client, user_token, user_asset):
    """A user can read an asset they own."""
    response = client.get(
        f"/api/assets/{user_asset.id}",
        headers=auth_header(user_token),
    )
    assert response.status_code == 200
    assert response.json()["hostname"] == "user-laptop"


# =============================================================================
# IDOR — cross-user access must be denied
# =============================================================================

def test_user_cannot_read_admins_asset(client, user_token, admin_asset):
    """
    A regular user must not be able to read an asset owned by another user.

    This is the regression test for the IDOR exercise. If it fails, the
    ownership filter has been removed from the get_asset endpoint — the
    exact pattern that was introduced and fixed in Phase 7.

    The endpoint returns 404 (not 403), so an attacker cannot distinguish
    "does not exist" from "exists but belongs to someone else". The test
    asserts 404, not 403, to lock in that decision.
    """
    response = client.get(
        f"/api/assets/{admin_asset.id}",
        headers=auth_header(user_token),
    )
    assert response.status_code == 404


def test_admin_cannot_read_users_asset(client, admin_token, user_asset):
    """
    The reverse direction: an admin is not implicitly authorised to read
    every asset. Admin status confers the ability to manage *users*, not
    to bypass ownership on assets.

    If a future change grants admins cross-user asset access, this test
    will fail and force a deliberate decision: either keep the current
    policy, or change the test with the policy change.
    """
    response = client.get(
        f"/api/assets/{user_asset.id}",
        headers=auth_header(admin_token),
    )
    assert response.status_code == 404


def test_unauthenticated_cannot_read_any_asset(client, admin_asset, user_asset):
    """No token, no access — regardless of whose asset it is."""
    for asset in (admin_asset, user_asset):
        response = client.get(f"/api/assets/{asset.id}")
        assert response.status_code == 401


# =============================================================================
# List endpoint — ownership filter is applied at the query level
# =============================================================================

def test_list_shows_only_own_assets(client, admin_token, user_token, admin_asset, user_asset):
    """
    The list endpoint returns only the caller's assets.

    This complements the get-by-id tests: the ownership filter must be
    present in both endpoints. A fix applied to one but not the other
    would pass half of these tests and fail the other half.
    """
    admin_response = client.get("/api/assets", headers=auth_header(admin_token))
    user_response = client.get("/api/assets", headers=auth_header(user_token))

    admin_hostnames = {a["hostname"] for a in admin_response.json()}
    user_hostnames = {a["hostname"] for a in user_response.json()}

    assert "admin-server" in admin_hostnames
    assert "user-laptop" not in admin_hostnames

    assert "user-laptop" in user_hostnames
    assert "admin-server" not in user_hostnames
