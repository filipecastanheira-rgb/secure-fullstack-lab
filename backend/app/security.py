"""
Security primitives for the Secure Fullstack Lab.

This module centralises:
- password hashing and verification (argon2id)
- JWT creation and validation

Keeping all cryptographic operations here means:
- the algorithm and parameters are defined in exactly one place;
- changing them later does not require touching every endpoint;
- the code that handles secrets is small and auditable.
"""

from datetime import datetime, timedelta, timezone
from pathlib import Path
import secrets

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import (
    InvalidHashError,
    VerificationError,
    VerifyMismatchError,
)
from fastapi import HTTPException, status


# =============================================================================
# Password hashing (argon2id)
# =============================================================================

# Argon2id is the current recommendation from OWASP and NIST for password
# hashing. It is memory-hard, which makes GPU-based cracking orders of
# magnitude more expensive than against bcrypt or PBKDF2.
#
# Defaults from argon2-cffi are already reasonable. In a production system,
# these would be tuned so that hashing takes ~100-500ms on the target
# hardware.
_hasher = PasswordHasher()


def hash_password(plain_password: str) -> str:
    """
    Hash a plain-text password using argon2id.

    Returns the full encoded hash (algorithm, parameters, salt, and digest
    combined in a single string). This is what gets stored in the
    database — never the plain password.
    """
    return _hasher.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain-text password against a stored argon2id hash.

    Returns True if the password matches, False otherwise. Never raises
    for a wrong password — exceptions are caught and converted to a
    boolean so that callers do not leak information through error
    behaviour.
    """
    try:
        _hasher.verify(hashed_password, plain_password)
        return True
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


# =============================================================================
# JWT
# =============================================================================

# The JWT secret must persist across restarts (otherwise every restart
# invalidates every token) and must never be committed to the repository.
# It is generated on first run and stored in `backend/.jwt_secret`, which
# is gitignored. In a production deployment, this would come from an
# environment variable injected by the deployment system.
_JWT_SECRET_FILE = Path(__file__).parent.parent / ".jwt_secret"
_JWT_ALGORITHM = "HS256"
_ACCESS_TOKEN_EXPIRES_MINUTES = 15


def _load_or_create_jwt_secret() -> str:
    """
    Load the JWT secret from disk, or create it on first run.

    The file is written with restrictive permissions (0600) so that only
    the owner can read it.
    """
    if _JWT_SECRET_FILE.exists():
        return _JWT_SECRET_FILE.read_text().strip()

    secret = secrets.token_urlsafe(64)
    _JWT_SECRET_FILE.write_text(secret)
    _JWT_SECRET_FILE.chmod(0o600)
    return secret


_JWT_SECRET = _load_or_create_jwt_secret()


def create_access_token(subject: str, role: str) -> str:
    """
    Create a signed JWT access token.

    `subject` is the user identifier (typically the user id as a string).
    `role` is embedded in the token so that downstream checks can authorise
    without hitting the database on every request.

    The token expires in 15 minutes. Short lifetimes are the standard
    mitigation for the fact that JWTs cannot be revoked before they expire.
    """
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "role": role,
        "iat": now,
        "exp": now + timedelta(minutes=_ACCESS_TOKEN_EXPIRES_MINUTES),
    }
    return jwt.encode(payload, _JWT_SECRET, algorithm=_JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    """
    Decode and validate a JWT.

    Raises HTTPException(401) on any failure — expired, invalid signature,
    malformed, or algorithm confusion. The message is deliberately generic
    so that a client cannot distinguish between "expired" and "tampered",
    which would leak information about the token's state.
    """
    try:
        return jwt.decode(token, _JWT_SECRET, algorithms=[_JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )
