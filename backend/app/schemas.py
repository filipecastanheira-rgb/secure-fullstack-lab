"""
Pydantic schemas for the Secure Fullstack Lab API.

Schemas define the *shape* of data that enters and leaves the API.
They are separate from ORM models on purpose:
- models.py describes what is stored in the database
- schemas.py describes what is exposed over HTTP

Keeping them separate means we can change the API contract without
touching the database, and vice-versa.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

# =============================================================================
# Assets
# =============================================================================

class AssetBase(BaseModel):
    """Fields shared by all Asset schemas."""
    hostname: str = Field(..., min_length=1, max_length=100)
    ip_address: str = Field(..., min_length=1, max_length=45)
    os: str = Field(..., min_length=1, max_length=100)


class AssetCreate(AssetBase):
    """
    Payload required to create a new asset.

    Note: `owner_id` is deliberately NOT a field here. It is assigned by
    the server from the authenticated user. If it were a field, a client
    could create an asset owned by someone else (mass assignment).
    """


class AssetRead(AssetBase):
    """Asset representation returned by the API."""
    id: int
    owner_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# Users
# =============================================================================

class UserCreate(BaseModel):
    """
    Payload to create a new user.

    `role` is restricted to the two values the application currently
    supports. When the API is public, this field will be removed from
    UserCreate and set only by an administrator endpoint.
    """
    email: EmailStr
    password: str = Field(..., min_length=15, max_length=128)
    role: Literal["user", "admin"] = "user"


class UserRead(BaseModel):
    """
    User representation returned by the API.

    Note: `password_hash` is deliberately absent. This is the whole point
    of separating schemas from models — the hash exists in the database
    but is never serialised to a client, even by accident.
    """
    id: int
    email: EmailStr
    role: str
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# Authentication
# =============================================================================

class LoginRequest(BaseModel):
    """
    Login credentials.

    Deliberately does not use the same constraints as UserCreate — we do
    not want to reveal the password policy (min length, complexity) to
    an attacker who is guessing credentials. The only thing that matters
    here is whether the provided password matches the stored hash.
    """
    email: EmailStr
    password: str = Field(..., min_length=1, max_length=128)


class TokenResponse(BaseModel):
    """
    Returned by the login endpoint on success.

    Both tokens are included:
    - access_token: short-lived (15 min), used for every authenticated call
    - refresh_token: long-lived (7 days), used only against /api/auth/refresh

    In a production deployment, the refresh token would be set as an
    HttpOnly cookie rather than returned in the JSON body, so that
    JavaScript cannot read it. For this lab (no browser storage
    considerations yet), it is returned in the body and the client is
    expected to store it appropriately.
    """
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    """
    Payload for POST /api/auth/refresh.

    Only the refresh token is required. The user identity and role are
    read from the token itself; they are not re-sent by the client.
    """
    refresh_token: str
