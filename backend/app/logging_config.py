"""
Structured JSON logging for the Secure Fullstack Lab API.

The default Uvicorn logging emits human-readable text lines. That works
for interactive debugging but is not analysable: a log aggregation tool
cannot filter by user, correlate by IP, or compute latency percentiles
without parsing a free-form string.

This module configures the Python logging system to emit one JSON object
per event. Each HTTP request produces one log record with well-defined
fields. The destination is stdout, which systemd captures and forwards
to journald.

The policy on what is NOT logged is deliberate and documented in
`docs/password-policy.md` §3.6: credentials, tokens, passwords, and
request bodies are never written to logs.
"""

import json
import logging
import sys
import time
from datetime import datetime, timezone

from starlette.middleware.base import BaseHTTPMiddleware

# Field names that are part of every LogRecord by default. They are
# skipped during JSON serialisation to avoid polluting the payload with
# Python internals. Only fields explicitly passed via `extra=` are kept.
_RESERVED_LOG_RECORD_FIELDS = {
    "name", "msg", "args", "levelname", "levelno", "pathname", "filename",
    "module", "exc_info", "exc_text", "stack_info", "lineno", "funcName",
    "created", "msecs", "relativeCreated", "thread", "threadName",
    "processName", "process", "message", "taskName",
}


class JsonFormatter(logging.Formatter):
    """
    Render a LogRecord as a single-line JSON object.

    Fields attached via `logger.info(..., extra={...})` are merged into
    the JSON payload at the top level. This lets a request-specific field
    — the HTTP method, the status code — appear as a first-class key
    rather than being embedded in a message string.
    """

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.fromtimestamp(
                record.created, tz=timezone.utc
            ).isoformat(),
            "level": record.levelname.lower(),
            "logger": record.name,
            "message": record.getMessage(),
        }

        for key, value in record.__dict__.items():
            if key in _RESERVED_LOG_RECORD_FIELDS:
                continue
            payload[key] = value

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, default=str)


def setup_logging(level: int = logging.INFO) -> None:
    """
    Configure the root logger to emit JSON to stdout.

    Any pre-existing handler is replaced, so that our formatter is the
    only one producing output. Uvicorn's own access log is intentionally
    left configured as-is — the middleware added in this module produces
    the structured access records instead.
    """
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)


def _client_ip(request) -> str:
    """
    Return the client IP as seen by the application.

    Nginx sets X-Real-IP on every proxied request. If the header is
    missing (for example, when the API is reached directly on the
    loopback interface during tests), the socket peer address is used.
    """
    forwarded = request.headers.get("x-real-ip")
    if forwarded:
        return forwarded
    if request.client:
        return request.client.host
    return "unknown"


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Emit one structured log record per HTTP request.

    Captured fields:
    - method, path, query
    - status_code
    - duration_ms (monotonic clock)
    - client_ip (from X-Real-IP, or the socket peer as fallback)
    - user_agent
    - user_id (set by get_current_user in request.state, if authenticated)

    Deliberately NOT captured: request body, response body, headers other
    than User-Agent. In particular the Authorization header is never
    logged — it contains the JWT.
    """

    async def dispatch(self, request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000.0

        logging.getLogger("app.request").info(
            "http_request",
            extra={
                "event": "http_request",
                "method": request.method,
                "path": request.url.path,
                "query": str(request.url.query),
                "status_code": response.status_code,
                "duration_ms": round(duration_ms, 2),
                "client_ip": _client_ip(request),
                "user_agent": request.headers.get("user-agent", ""),
                "user_id": getattr(request.state, "user_id", None),
            },
        )

        return response
