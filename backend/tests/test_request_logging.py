"""
Tests for the request logging middleware.
"""

import logging

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.logging_config import RequestLoggingMiddleware


class _Capture(logging.Handler):
    def __init__(self):
        super().__init__()
        self.records = []

    def emit(self, record):
        self.records.append(record)


def test_unhandled_exception_is_logged_as_500():
    """
    A request that ends in an unhandled exception must still produce one
    log record, with status_code 500.

    Without it, only 5xx responses that the application builds itself are
    logged, and the errors that matter most for detection leave no trace.
    """
    app = FastAPI()
    app.add_middleware(RequestLoggingMiddleware)

    @app.get("/boom")
    def boom():
        raise RuntimeError("boom")

    logger = logging.getLogger("app.request")
    handler = _Capture()
    old_level = logger.level
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    try:
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/boom")
    finally:
        logger.removeHandler(handler)
        logger.setLevel(old_level)

    assert response.status_code == 500
    assert len(handler.records) == 1
    assert handler.records[0].status_code == 500
    assert handler.records[0].path == "/boom"
