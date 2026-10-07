"""
Entry point for the Secure Fullstack Lab API.

Responsible only for:
- creating the FastAPI app
- creating database tables on startup
- defining HTTP endpoints

Note: CORS middleware was removed after Nginx was introduced as a reverse
proxy. The browser and the API are now served from the same origin, so
cross-origin requests no longer occur. If the architecture changes and the
frontend is served from a different host/port again, CORS will need to be
reintroduced with an explicit origin allowlist.
"""

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy.orm import Session

from app import models
from app.database import Base, engine, get_db
from app.dependencies import get_current_user, require_admin
from app.schemas import (
    AssetCreate,
    AssetRead,
    LoginRequest,
    TokenResponse,
    UserCreate,
    UserRead,
)
from app.security import create_access_token, hash_password, verify_password


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Runs on startup (before the first request) and on shutdown.

    We use it to create database tables. SQLAlchemy's create_all is
    idempotent: it creates only tables that do not exist yet. This means
    adding a new model (e.g. User) does not require a migration tool for
    now — the table is created on the next startup.
    """
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="Secure Fullstack Lab API",
    version="0.3.0",
    lifespan=lifespan,
)


@app.get("/")
def read_root():
    return {"message": "Secure Fullstack Lab API is running"}


@app.get("/api/hello")
def read_hello():
    return {"message": "Hello from FastAPI 👋"}


# =============================================================================
# Assets
# =============================================================================
# Both endpoints require an authenticated user. Any authenticated user can
# list and create assets. Ownership and per-user filtering will be added in
# a later phase (Phase 7, IDOR demonstration).

@app.get("/api/assets", response_model=list[AssetRead])
def list_assets(
    db: Session = Depends(get_db),
    _: models.User = Depends(get_current_user),
):
    """Return all assets stored in the database."""
    return db.query(models.Asset).order_by(models.Asset.id).all()


@app.post(
    "/api/assets",
    response_model=AssetRead,
    status_code=status.HTTP_201_CREATED,
)
def create_asset(
    payload: AssetCreate,
    db: Session = Depends(get_db),
    _: models.User = Depends(get_current_user),
):
    """Create a new asset from a validated JSON payload."""
    asset = models.Asset(
        hostname=payload.hostname,
        ip_address=payload.ip_address,
        os=payload.os,
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return asset


# =============================================================================
# Users
# =============================================================================

@app.post(
    "/api/users",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
)
def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_admin),
):
    """
    Create a new user.

    Requires administrator privileges. The bootstrap problem (creating the
    first admin when no user exists yet) was solved manually during
    development — the endpoint was unauthenticated for one session, and an
    admin user was created via curl. After that, the endpoint was locked
    down. In a production system, a separate bootstrap mechanism
    (environment-seeded admin, or a one-time setup command) would be used.
    """
    existing = (
        db.query(models.User)
        .filter(models.User.email == payload.email)
        .first()
    )
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists.",
        )

    user = models.User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        role=payload.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@app.get("/api/users/me", response_model=UserRead)
def read_current_user(
    current_user: models.User = Depends(get_current_user),
):
    """
    Return the profile of the currently authenticated user.

    This is the simplest authenticated endpoint — it exists to verify that
    the authentication flow works end-to-end: login returns a token, the
    token is sent in the Authorization header, the dependency validates
    it, and the endpoint returns the user the token represents.
    """
    return current_user


# =============================================================================
# Authentication
# =============================================================================

@app.post("/api/auth/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    """
    Authenticate a user and return a JWT access token.

    On success: 200 with a TokenResponse.
    On failure: 401 with a generic message.

    The message is deliberately the same whether the email does not exist
    or the password is wrong. Distinguishing between the two would allow
    an attacker to enumerate valid accounts.
    """
    user = (
        db.query(models.User)
        .filter(models.User.email == payload.email)
        .first()
    )

    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token(subject=str(user.id), role=user.role)
    return TokenResponse(access_token=token)
