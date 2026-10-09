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
from sqlalchemy import text
from sqlalchemy.orm import Session

from app import models
from app.database import Base, engine, get_db
from app.dependencies import get_current_user, require_admin
from app.schemas import (
    AssetCreate,
    AssetRead,
    LoginRequest,
    RefreshRequest,
    TokenResponse,
    UserCreate,
    UserRead,
)
from app.security import (
    create_access_token,
    create_refresh_token,
    decode_token_of_type,
    hash_password,
    verify_password,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Runs on startup (before the first request) and on shutdown.

    We use it to create database tables. SQLAlchemy's create_all is
    idempotent: it creates only tables that do not exist yet.
    """
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="Secure Fullstack Lab API",
    version="0.4.0",
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
    search: str = "",
    db: Session = Depends(get_db),
    _: models.User = Depends(get_current_user),
):
    """
    Return all assets stored in the database, optionally filtered by
    hostname.

    The `search` parameter is bound as a query parameter (`:search`),
    never interpolated into the SQL text. This is what makes the endpoint
    resistant to SQL injection: whatever the caller sends is treated as a
    value, not as code.

    This is the fixed version of the exercise in `docs/vuln-exercise-sqli.md`.
    The vulnerable version (string interpolation) was merged into `main`
    deliberately for the exercise, and the difference is documented there.
    """
    query = text(
        "SELECT id, hostname, ip_address, os, created_at "
        "FROM assets WHERE hostname LIKE :search ORDER BY id"
    )
    result = db.execute(query, {"search": f"%{search}%"}).fetchall()
    return [
        {
            "id": row[0],
            "hostname": row[1],
            "ip_address": row[2],
            "os": row[3],
            "created_at": row[4],
        }
        for row in result
    ]


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
    Authenticate a user and return a JWT access token and refresh token.

    On success: 200 with a TokenResponse containing both tokens.
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

    subject = str(user.id)
    return TokenResponse(
        access_token=create_access_token(subject=subject, role=user.role),
        refresh_token=create_refresh_token(subject=subject, role=user.role),
    )


@app.post("/api/auth/refresh", response_model=TokenResponse)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)):
    """
    Exchange a valid refresh token for a new pair of tokens.

    The refresh endpoint only accepts tokens whose `type` claim is
    "refresh". An access token presented here is rejected, which prevents
    a stolen access token from extending its own lifetime.

    Returns both a new access token AND a new refresh token. Rotating the
    refresh token on every use is the safer behaviour: if a refresh token
    is leaked, it stops being valid the next time the legitimate client
    refreshes. Without rotation, a stolen refresh token remains usable for
    its full 7-day lifetime.

    Note: this implementation does not yet track revoked refresh tokens,
    so a leaked refresh token that has not been used since the leak would
    still work until it is replaced by the next legitimate refresh. A
    full revocation scheme (a token version counter per user) is a future
    improvement.
    """
    token_payload = decode_token_of_type(payload.refresh_token, "refresh")

    subject = token_payload.get("sub")
    if subject is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_id = int(subject)
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None

    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    new_subject = str(user.id)
    return TokenResponse(
        access_token=create_access_token(subject=new_subject, role=user.role),
        refresh_token=create_refresh_token(subject=new_subject, role=user.role),
    )
