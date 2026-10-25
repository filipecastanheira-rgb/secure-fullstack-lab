"""
Tests for the ip_address validation of POST /api/assets.

The field is typed as IPvAnyAddress in AssetCreate, so anything that is
not a valid IPv4 or IPv6 address is rejected with HTTP 422 before it
reaches the database.
"""

import pytest

from tests.conftest import auth_header


def _payload(ip_address):
    return {"hostname": "ip-test", "ip_address": ip_address, "os": "Test"}


@pytest.mark.parametrize(
    "bad_ip",
    ["not-an-ip", "999.1.1.1", "10.0.0", "<script>x</script>", "10.0.0.1; DROP"],
)
def test_create_asset_rejects_invalid_ip(client, admin_token, bad_ip):
    """A value that is not an IP address is rejected with 422."""
    response = client.post(
        "/api/assets", json=_payload(bad_ip), headers=auth_header(admin_token)
    )
    assert response.status_code == 422


@pytest.mark.parametrize("good_ip", ["10.0.0.1", "192.168.1.173", "2001:db8::1"])
def test_create_asset_accepts_valid_ip_as_text(client, admin_token, good_ip):
    """Valid IPv4 and IPv6 addresses are accepted and returned as text."""
    response = client.post(
        "/api/assets", json=_payload(good_ip), headers=auth_header(admin_token)
    )
    assert response.status_code == 201
    assert response.json()["ip_address"] == good_ip
