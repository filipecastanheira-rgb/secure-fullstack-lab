"""
Test package.

The application reads JWT_SECRET_FILE and DATABASE_URL at import time, and
their defaults point to /var/lib/secure-fullstack, which only exists on the
deployed host. pytest imports this package before conftest.py, so the
defaults are set here, before anything imports `app`. Variables that are
already set (CI, or a developer's own) are left untouched.
"""

import os
import tempfile

_TMP = tempfile.mkdtemp(prefix="secure-fullstack-tests-")
os.environ.setdefault("JWT_SECRET_FILE", os.path.join(_TMP, "jwt_secret"))
os.environ.setdefault("DATABASE_URL", f"sqlite:///{os.path.join(_TMP, 'lab.db')}")
