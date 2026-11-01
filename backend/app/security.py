"""
Security primitives for the Secure Fullstack Lab.

This module centralises:
- password hashing and verification (argon2id)
- JWT creation and validation (access tokens and refresh tokens)

Keeping all cryptographic operations here means:
- the algorithm and parameters are defined in exactly one place;
- changing them later does not require touching every endpoint;
- the code that handles secrets is small and auditable.
"""

import os
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

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


# A valid argon2id hash of a throwaway password, computed once at import.
# The login endpoint verifies against it when the email does not exist, so
# that unknown and known emails cost the same amount of work and the
# response time does not reveal which accounts exist.
DUMMY_PASSWORD_HASH = hash_password("throwaway-password-for-timing-equalisation")


# =============================================================================
# JWT
# =============================================================================

# The JWT secret must persist across restarts (otherwise every restart
# invalidates every token) and must never be committed to the repository.
# It is generated on first run and stored in the file named by the
# `JWT_SECRET_FILE` environment variable, which defaults to
# `/var/lib/secure-fullstack/.jwt_secret` (outside the repository). In a
# production deployment, this would come from an
# environment variable injected by the deployment system.
_JWT_SECRET_FILE = Path(
    os.environ.get("JWT_SECRET_FILE", "/var/lib/secure-fullstack/.jwt_secret")
)
_JWT_ALGORITHM = "HS256"
_ACCESS_TOKEN_EXPIRES_MINUTES = 15
_REFRESH_TOKEN_EXPIRES_DAYS = 7


def _load_or_create_jwt_secret() -> str:
    """
    Load the JWT secret from disk, or create it on first run.

    The file is written with restrictive permissions (0600) so that only
    the owner can read it.
    """
    if _JWT_SECRET_FILE.exists():
        return _JWT_SECRET_FILE.read_text().strip()

    secret = secrets.token_urlsafe(64)
    # Create the file with mode 0600 from the start. Writing first and
    # calling chmod afterwards leaves a window in which the secret is
    # readable with the default permissions. O_EXCL makes creation fail
    # instead of overwriting a file that appeared in the meantime.
    fd = os.open(_JWT_SECRET_FILE, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write(secret)
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

    The `type` claim is set to "access" so that this token cannot be used
    where a refresh token is required (and vice versa).
    """
    now = datetime.now(UTC)
    payload = {
        "sub": subject,
        "role": role,
        "type": "access",
        "iat": now,
        "exp": now + timedelta(minutes=_ACCESS_TOKEN_EXPIRES_MINUTES),
    }
    return jwt.encode(payload, _JWT_SECRET, algorithm=_JWT_ALGORITHM)


def new_token_id() -> str:
    """Return a random identifier for a refresh token or a token family."""
    return str(uuid.uuid4())


def refresh_token_lifetime() -> timedelta:
    """Return how long a refresh token stays valid."""
    return timedelta(days=_REFRESH_TOKEN_EXPIRES_DAYS)


def create_refresh_token(subject: str, role: str, jti: str) -> str:
    """
    Create a signed JWT refresh token.

    A refresh token is longer-lived than an access token (7 days vs 15
    minutes) and exists solely to obtain new access tokens without asking
    the user to log in again.

    It carries a `type` claim set to "refresh", which the access-token
    verification path explicitly rejects. Without that claim, a stolen
    refresh token would work as an access token, and the two-token model
    would collapse into a single, longer-lived one.

    `jti` identifies this token in the refresh_tokens table, which is what
    allows a token to be used once and a family to be revoked.
    """
    now = datetime.now(UTC)
    payload = {
        "sub": subject,
        "role": role,
        "type": "refresh",
        "jti": jti,
        "iat": now,
        "exp": now + timedelta(days=_REFRESH_TOKEN_EXPIRES_DAYS),
    }
    return jwt.encode(payload, _JWT_SECRET, algorithm=_JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    """
    Decode and validate a JWT, without checking its `type` claim.

    Raises HTTPException(401) on any failure — expired, invalid signature,
    malformed, or algorithm confusion. The message is deliberately generic
    so that a client cannot distinguish between "expired" and "tampered",
    which would leak information about the token's state.

    Callers that need to enforce a specific token type should use
    `decode_token_of_type` instead of calling this function directly.
    """
    try:
        return jwt.decode(token, _JWT_SECRET, algorithms=[_JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        # `from None` keeps the client response uniform. The distinction
        # between expired and invalid remains in the internal log (via the
        # original exception class) but is not surfaced to the caller.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None


def decode_token_of_type(token: str, expected_type: str) -> dict:
    """
    Decode a JWT and require that it declares the expected `type`.

    Raises 401 if the token is invalid, expired, or carries a different
    `type` than expected. This is what keeps access tokens and refresh
    tokens in their own lanes: a refresh token presented to an endpoint
    that expects an access token is rejected even though the signature is
    valid.
    """
    payload = decode_token(token)
    if payload.get("type") != expected_type:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload
