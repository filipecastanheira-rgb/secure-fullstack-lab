"""
Policy test: the API does not emit CORS headers by default.

The application is served by Nginx on a single origin (frontend and API
share the same hostname). There are no cross-origin requests, so no CORS
policy should be configured.

This test exists because CORS misconfiguration is the kind of problem
that comes back. A developer debugging a cross-origin issue may add a
permissive `CORSMiddleware` configuration to make things work locally,
and forget to remove it. If that happens, this test fails, and the
introduction becomes deliberate rather than accidental.

See `docs/vuln-exercise-cors.md` for the demonstration of what happens
when `allow_origins=["*"]` is combined with `allow_credentials=True`.
"""



def test_api_does_not_emit_cors_headers(client):
    """
    A request with an Origin header must not receive CORS response headers.

    The absence of `Access-Control-Allow-Origin` is what makes the browser
    refuse cross-origin reads. If the header is present — even echoing a
    specific origin — the browser will allow the response to be read.
    """
    response = client.get(
        "/api/hello",
        headers={"Origin": "https://evil.example.com"},
    )

    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers
    assert "access-control-allow-credentials" not in response.headers


def test_api_does_not_emit_cors_preflight_headers(client):
    """
    A preflight request (OPTIONS) must not be answered with CORS headers.

    Browsers send a preflight OPTIONS request before cross-origin requests
    that use methods or headers outside the simple set. A server that
    responds with `Access-Control-Allow-Methods` and
    `Access-Control-Allow-Headers` is advertising that the cross-origin
    request is permitted.
    """
    response = client.options(
        "/api/hello",
        headers={
            "Origin": "https://evil.example.com",
            "Access-Control-Request-Method": "GET",
        },
    )

    # The API has no OPTIONS handler for this route. Starlette returns 405
    # Method Not Allowed. That is fine — what matters is what headers came
    # back with it.
    assert "access-control-allow-origin" not in response.headers
    assert "access-control-allow-methods" not in response.headers
    assert "access-control-allow-headers" not in response.headers
