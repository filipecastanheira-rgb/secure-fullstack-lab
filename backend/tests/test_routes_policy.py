"""
Policy test: every endpoint requires authentication unless explicitly
listed as public.

This test exists to prevent a class of mistake that does not show up
in any other scanner: a new endpoint added without the
`Depends(get_current_user)` dependency. Ruff does not know what a
dependency is. Bandit does not know what an endpoint is. The DAST
baseline scan does not authenticate, so it does not see the difference
between 401 and 200 for a new route.

The test does, because it is written to know what the policy is, and
it fails when the code disagrees with it.
"""


from app.main import app

# Endpoints that are intentionally public. Every other route must
# require authentication.
#
# Adding a route to this list is a deliberate decision. If a route ends
# up here by accident, it will pass without auth — so the list is
# short and every entry has a reason.
PUBLIC_ROUTES = {
    ("GET", "/"),
    ("GET", "/api/hello"),
    ("POST", "/api/auth/login"),
    ("POST", "/api/auth/refresh"),
    # Logout is authenticated by the refresh token in the body, which
    # the access token may no longer be valid alongside.
    ("POST", "/api/auth/logout"),
    # OpenAPI and documentation. FastAPI serves these by default.
    # In production they would be disabled (see threat model §7.2 I2).
    ("GET", "/docs"),
    ("GET", "/openapi.json"),
    ("GET", "/docs/oauth2-redirect"),
    ("GET", "/redoc"),
}


def _route_requires_auth(method: str, path: str) -> bool:
    return (method, path) not in PUBLIC_ROUTES


def _routes_to_check():
    """
    Yield (method, path) for every route in the application that should
    be tested. Paths with parameters are excluded — testing them requires
    a concrete id, and the parameterised endpoints are covered by the
    dedicated tests in test_auth.py.
    """
    for route in app.routes:
        methods = getattr(route, "methods", None)
        path = getattr(route, "path", None)
        if not methods or not path:
            continue
        if "{" in path:  # parameterised route — skip here
            continue
        for method in methods:
            if method in {"HEAD", "OPTIONS"}:
                continue
            yield method, path


def test_every_non_public_route_requires_authentication(client):
    """
    For each non-public route, a request without a token must return 401.

    A failure here means one of two things:
    1. A new endpoint was added without an authentication dependency.
       Fix: add Depends(get_current_user) to the endpoint.
    2. The endpoint is intentionally public but not listed in PUBLIC_ROUTES.
       Fix: add it to the list, with a comment explaining why.

    Both are correct responses. Silently ignoring the failure is not.
    """
    failures = []

    for method, path in _routes_to_check():
        if not _route_requires_auth(method, path):
            continue

        response = client.request(method, path)
        if response.status_code != 401:
            failures.append(
                f"{method} {path} returned {response.status_code}, expected 401"
            )

    assert not failures, (
        "The following routes do not require authentication, but are not "
        "listed as public:\n" + "\n".join(failures)
    )
