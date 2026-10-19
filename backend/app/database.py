"""
Database setup for the Secure Fullstack Lab.

Uses SQLAlchemy as an abstraction layer over the database engine.
Currently backed by SQLite; switching to PostgreSQL later only requires
changing DATABASE_URL — no application code needs to change.
"""

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

# SQLite file lives inside the backend/ folder as `lab.db`.
# check_same_thread=False is required by SQLite when accessed from FastAPI's
# thread pool. It is safe because each request gets its own session.
DATABASE_URL = os.environ.get(
    "DATABASE_URL", "sqlite:////var/lib/secure-fullstack/lab.db"
)

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Base class that every ORM model will inherit from."""


def get_db():
    """
    FastAPI dependency: yields a database session per request and closes it
    afterwards, even if the request raises an exception.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
