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

from pydantic import BaseModel, ConfigDict, Field


class AssetBase(BaseModel):
    """Fields shared by all Asset schemas."""
    hostname: str = Field(..., min_length=1, max_length=100)
    ip_address: str = Field(..., min_length=1, max_length=45)
    os: str = Field(..., min_length=1, max_length=100)


class AssetCreate(AssetBase):
    """Payload required to create a new asset."""
    pass


class AssetRead(AssetBase):
    """Asset representation returned by the API."""
    id: int
    created_at: datetime

    # Allows Pydantic to read data directly from SQLAlchemy objects.
    model_config = ConfigDict(from_attributes=True)
