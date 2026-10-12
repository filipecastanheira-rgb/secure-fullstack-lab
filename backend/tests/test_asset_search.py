"""
Tests for the search parameter of GET /api/assets.

The search parameter accepts a free-text string used to filter assets by
hostname. It is bound as a query parameter (`:search`), never
interpolated into the SQL text.

This file contains the regression test for the SQL injection exercise
(Phase 7). See `docs/vuln-exercise-sqli.md` for the full exercise.
"""

import pytest

from app import models
from tests.conftest import auth_header


@pytest.fixture()
def searchable_assets(db_session, test_admin):
    """
    Three assets owned by the admin user, for search tests.

    The hostnames are chosen so that:
    - a substring search finds a specific subset
    - a payload like `' OR 1=1--` finds nothing
    """
    assets = [
        models.Asset(
            hostname="ubuntu-lab",
            ip_address="10.0.0.1",
            os="Ubuntu",
            owner_id=test_admin.id,
        ),
        models.Asset(
            hostname="kali-attacker",
            ip_address="10.0.0.2",
            os="Kali",
            owner_id=test_admin.id,
        ),
        models.Asset(
            hostname="windows-workstation",
            ip_address="10.0.0.3",
            os="Windows",
            owner_id=test_admin.id,
        ),
    ]
    for asset in assets:
        db_session.add(asset)
    db_session.commit()
    return assets


def test_search_filters_by_hostname_substring(client, admin_token, searchable_assets):
    """
    A plain substring search returns only the matching assets.

    This is the control test: the endpoint behaves as expected for
    legitimate input.
    """
    response = client.get(
        "/api/assets",
        params={"search": "ubuntu"},
        headers=auth_header(admin_token),
    )
    assert response.status_code == 200
    hostnames = {a["hostname"] for a in response.json()}
    assert hostnames == {"ubuntu-lab"}


def test_search_with_empty_string_returns_all(client, admin_token, searchable_assets):
    """
    An empty search returns every asset owned by the caller.

    The `LIKE '%%'` pattern matches any hostname. This is the intended
    behaviour when no filter is provided.
    """
    response = client.get(
        "/api/assets",
        params={"search": ""},
        headers=auth_header(admin_token),
    )
    assert response.status_code == 200
    assert len(response.json()) == 3


def test_sql_injection_payload_returns_no_rows(client, admin_token, searchable_assets):
    """
    Regression test for the SQL injection exercise (Phase 7).

    The payload `' OR 1=1--` was used against the vulnerable version of
    this endpoint to bypass the search filter. Against the fixed version,
    the payload is treated as a literal string — no hostname contains
    the literal text `' OR 1=1--`, so the search returns no rows.

    If this test fails, the search parameter is being interpolated into
    the SQL text again. The fix that introduced parameter binding has
    been reverted.

    See `docs/vuln-exercise-sqli.md` for the full exercise.
    """
    response = client.get(
        "/api/assets",
        params={"search": "' OR 1=1--"},
        headers=auth_header(admin_token),
    )
    assert response.status_code == 200
    assert response.json() == []


def test_sql_injection_payload_with_union_returns_no_rows(client, admin_token, searchable_assets):
    """
    A UNION-based payload must also be treated as a literal string.

    A second payload class, to guard against a partial fix that only
    neutralised the boolean-based injection.
    """
    response = client.get(
        "/api/assets",
        params={"search": "' UNION SELECT * FROM users--"},
        headers=auth_header(admin_token),
    )
    assert response.status_code == 200
    assert response.json() == []


def test_search_cannot_see_other_users_assets(
    client,
    admin_token,
    user_token,
    searchable_assets,
    db_session,
    test_user,
):
    """
    The search filter operates on the caller's assets only.

    A user searching by a hostname that belongs to another user sees
    nothing, because the ownership filter is applied at the query level
    in addition to the search filter.
    """
    # Give the regular user an asset with a searchable hostname
    other = models.Asset(
        hostname="user-private-host",
        ip_address="10.0.0.99",
        os="Linux",
        owner_id=test_user.id,
    )
    db_session.add(other)
    db_session.commit()

    # Admin searches for a hostname that only the user owns
    response = client.get(
        "/api/assets",
        params={"search": "user-private-host"},
        headers=auth_header(admin_token),
    )
    assert response.status_code == 200
    assert response.json() == []

    # The user can find their own asset with the same search
    response = client.get(
        "/api/assets",
        params={"search": "user-private-host"},
        headers=auth_header(user_token),
    )
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["hostname"] == "user-private-host"
