"""
Security primitives for the Secure Fullstack Lab.

This module centralises password hashing and verification so that:
- the algorithm and parameters are defined in exactly one place;
- changing them later (e.g. increasing argon2 memory cost) does not
  require touching every endpoint that handles credentials;
- future security features (JWT signing, token generation) can live here
  without scattering cryptographic code across the codebase.
"""

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError, InvalidHashError


# Argon2id is the current recommendation from OWASP and NIST for password
# hashing. It is memory-hard, which makes GPU-based cracking orders of
# magnitude more expensive than against bcrypt or PBKDF2.
#
# Defaults from argon2-cffi are already reasonable for a lab. In a
# production system, these would be tuned so that hashing takes ~100-500ms
# on the target hardware.
_hasher = PasswordHasher()


def hash_password(plain_password: str) -> str:
    """
    Hash a plain-text password using argon2id.

    Returns the full encoded hash (algorithm, parameters, salt, and digest
    combined in a single string). This string is what gets stored in the
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
