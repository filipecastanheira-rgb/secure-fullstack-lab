"""
Refresh token rotation, reuse detection and logout.

Each refresh token can be used once. Presenting a used token revokes the
whole family, so a stolen token and the legitimate client's token both
stop working and the user has to log in again.
"""

from datetime import UTC, datetime, timedelta

import jwt

from app import models, security
from app.main import _purge_expired_refresh_tokens

from .conftest import ADMIN_EMAIL, ADMIN_PASSWORD


def _login(client):
    response = client.post(
        "/api/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
    )
    assert response.status_code == 200, response.text
    return response.json()


def _refresh(client, token):
    return client.post("/api/auth/refresh", json={"refresh_token": token})


def test_refresh_token_is_recorded_on_login(client, db_session, test_admin):
    _login(client)
    rows = db_session.query(models.RefreshToken).all()
    assert len(rows) == 1
    assert rows[0].used_at is None
    assert rows[0].revoked_at is None


def test_refresh_rotates_within_the_same_family(client, db_session, test_admin):
    first = _login(client)
    response = _refresh(client, first["refresh_token"])
    assert response.status_code == 200
    assert response.json()["refresh_token"] != first["refresh_token"]
    rows = db_session.query(models.RefreshToken).all()
    assert len(rows) == 2
    assert len({row.family_id for row in rows}) == 1


def test_reused_refresh_token_is_rejected(client, test_admin):
    first = _login(client)
    assert _refresh(client, first["refresh_token"]).status_code == 200
    assert _refresh(client, first["refresh_token"]).status_code == 401


def test_reuse_revokes_the_whole_family(client, test_admin):
    first = _login(client)
    second = _refresh(client, first["refresh_token"]).json()
    # Replaying the first token is theft: the newer token must die too.
    assert _refresh(client, first["refresh_token"]).status_code == 401
    assert _refresh(client, second["refresh_token"]).status_code == 401


def test_logout_revokes_the_family(client, test_admin):
    tokens = _login(client)
    response = client.post(
        "/api/auth/logout", json={"refresh_token": tokens["refresh_token"]}
    )
    assert response.status_code == 204
    assert _refresh(client, tokens["refresh_token"]).status_code == 401


def test_logout_is_idempotent(client, test_admin):
    tokens = _login(client)
    body = {"refresh_token": tokens["refresh_token"]}
    assert client.post("/api/auth/logout", json=body).status_code == 204
    assert client.post("/api/auth/logout", json=body).status_code == 204


def test_logout_rejects_access_token(client, test_admin):
    tokens = _login(client)
    response = client.post(
        "/api/auth/logout", json={"refresh_token": tokens["access_token"]}
    )
    assert response.status_code == 401


def test_refresh_token_without_jti_is_rejected(client, test_admin):
    now = datetime.now(UTC)
    token = jwt.encode(
        {
            "sub": str(test_admin.id),
            "role": "admin",
            "type": "refresh",
            "iat": now,
            "exp": now + timedelta(days=1),
        },
        security._JWT_SECRET,
        algorithm=security._JWT_ALGORITHM,
    )
    assert _refresh(client, token).status_code == 401


def test_expired_record_is_rejected(client, db_session, test_admin):
    tokens = _login(client)
    row = db_session.query(models.RefreshToken).one()
    row.expires_at = datetime.now(UTC).replace(tzinfo=None) - timedelta(minutes=1)
    db_session.commit()
    assert _refresh(client, tokens["refresh_token"]).status_code == 401


def test_purge_removes_only_expired_rows(db_session, test_admin):
    now = datetime.now(UTC).replace(tzinfo=None)
    db_session.add_all(
        [
            models.RefreshToken(
                jti="00000000-0000-0000-0000-000000000001",
                family_id="family-expired",
                user_id=test_admin.id,
                expires_at=now - timedelta(minutes=1),
            ),
            models.RefreshToken(
                jti="00000000-0000-0000-0000-000000000002",
                family_id="family-valid",
                user_id=test_admin.id,
                expires_at=now + timedelta(days=1),
            ),
        ]
    )
    db_session.commit()

    assert _purge_expired_refresh_tokens(db_session) == 1

    remaining = db_session.query(models.RefreshToken).all()
    assert [r.family_id for r in remaining] == ["family-valid"]
