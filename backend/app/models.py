"""
ORM models for the Secure Fullstack Lab.

Each class here maps to a database table. SQLAlchemy translates class
attributes into columns and instances into rows.
"""

from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Asset(Base):
    """
    A single host/asset tracked in the lab inventory.

    Each asset is owned by exactly one user. Ownership is the basis of the
    IDOR demonstration in Phase 7: without an owner, there is no "another
    user's asset" to attempt to access.
    """

    __tablename__ = "assets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    hostname: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    ip_address: Mapped[str] = mapped_column(String(45), nullable=False)
    os: Mapped[str] = mapped_column(String(100), nullable=False)
    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(UTC),
        nullable=False,
    )


class User(Base):
    """
    An authenticated user of the application.

    `password_hash` stores the argon2id hash of the password, never the
    password itself. `role` is a simple string for now — a dedicated Role
    table would be introduced if roles ever need their own metadata.
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(
        String(254),
        nullable=False,
        unique=True,
        index=True,
    )
    # argon2id hashes are ~95-100 chars depending on parameters.
    # 255 gives plenty of headroom.
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="user",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(UTC),
        nullable=False,
    )


class RefreshToken(Base):
    """
    Server-side record of an issued refresh token.

    Only the `jti` (token id) is stored, never the token itself. All
    refresh tokens issued from one login share a `family_id`. Each token
    can be used once: `used_at` is set when it is exchanged for a new
    one. Presenting a token that was already used is treated as theft and
    revokes the whole family (`revoked_at`).
    """

    __tablename__ = "refresh_tokens"

    jti: Mapped[str] = mapped_column(String(36), primary_key=True)
    family_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
