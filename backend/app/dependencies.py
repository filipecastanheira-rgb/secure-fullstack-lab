"""
FastAPI dependencies for the Secure Fullstack Lab.

Dependencies are functions that FastAPI calls before running an endpoint.
They are used here to:
- extract and validate the JWT from the Authorization header
- fetch the authenticated user from the database
- enforce role requirements

This file exists separately from `security.py` (which contains only
cryptographic primitives, with no knowledge of FastAPI) and `main.py`
(which contains endpoints). Keeping them separate avoids mixing
frameworks, primitives, and application logic in the same module.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app import models
from app.database import get_db
from app.security import decode_token_of_type


# HTTPBearer extracts the token from the "Authorization: Bearer <token>"
# header. It also declares the security scheme in the OpenAPI docs, so the
# /docs page shows an "Authorize" button.
#
# auto_error=False means: if the header is missing, return None instead of
# raising automatically. We raise with a consistent message ourselves,
# so that the response shape is identical to the one used for invalid
# tokens (uniform error handling, as in the login endpoint).
_bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    db: Session = Depends(get_db),
) -> models.User:
    """
    Resolve the authenticated user from the request.

    Steps:
    1. Extract the Bearer token from the Authorization header.
    2. Decode and validate the JWT, requiring type == "access".
    3. Read the user id from the token subject.
    4. Fetch the user from the database.
    5. Reject if the user does not exist or is inactive.

    Requiring type == "access" is what prevents a refresh token (which is
    longer-lived and meant only for the /api/auth/refresh endpoint) from
    being used here. Without that check, a stolen refresh token would be
    accepted as an access token and the two-token model would be useless.

    Any failure raises HTTP 401 with a generic message. The client cannot
    distinguish between "missing header", "invalid signature", "expired",
    "wrong token type", "user does not exist", or "user is inactive".
    """
    _unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if credentials is None:
        raise _unauthorized

    payload = decode_token_of_type(credentials.credentials, "access")

    subject = payload.get("sub")
    if subject is None:
        raise _unauthorized

    try:
        user_id = int(subject)
    except (TypeError, ValueError):
        raise _unauthorized

    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user is None or not user.is_active:
        raise _unauthorized

    return user


def require_admin(
    user: models.User = Depends(get_current_user),
) -> models.User:
    """
    Dependency that requires the authenticated user to have the admin role.

    Usage:

        @app.post("/api/users")
        def create_user(..., _: models.User = Depends(require_admin)):
            ...

    Any user without the admin role receives 403 Forbidden. Note the
    difference from 401:
    - 401 means "you are not authenticated" (missing or invalid credentials)
    - 403 means "you are authenticated, but not allowed"

    Using 403 here is deliberate. The user IS authenticated — they simply
    do not have the privilege. Distinguishing 401 from 403 is important
    for debugging and for correct client behaviour.
    """
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This action requires administrator privileges.",
        )
    return user
