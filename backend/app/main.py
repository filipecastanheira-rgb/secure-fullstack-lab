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

from fastapi import Depends, FastAPI, HTTPException, Query, Response, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app import models
from app.database import Base, engine, get_db
from app.dependencies import get_current_user, require_admin
from app.logging_config import RequestLoggingMiddleware, setup_logging
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
    DUMMY_PASSWORD_HASH,
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


# Configure structured JSON logging before the app is created. Every
# request will produce one JSON record on stdout, which systemd forwards
# to journald. See app/logging_config.py for the field list.
setup_logging()

app = FastAPI(
    title="Secure Fullstack Lab API",
    version="0.4.0",
    lifespan=lifespan,
)

# Log one structured record per HTTP request. The middleware runs after
# the response is generated, so it can capture the status code and the
# duration; the user id is set by get_current_user via request.state.
app.add_middleware(RequestLoggingMiddleware)

# CORS is intentionally not configured here.
#
# The application is served by Nginx on a single origin
# (https://<UBUNTU_IP>), with the frontend and the API under the same
# hostname. There are no cross-origin requests, so no CORS policy is
# required.
#
# If the architecture changes and the frontend is served from a different
# origin in the future, CORS must be reintroduced with an explicit
# allowlist of known origins. Wildcards combined with
# `allow_credentials=True` are not acceptable — see
# `docs/vuln-exercise-cors.md` for the demonstration of why.


@app.get("/")
def read_root():
    return {"message": "Secure Fullstack Lab API is running"}


@app.get("/api/hello")
def read_hello():
    return {"message": "Hello from FastAPI 👋"}


# =============================================================================
# Assets
# =============================================================================
# Both endpoints require an authenticated user, and both are scoped to the
# owner. A user can only list and create their own assets. Cross-user
# access is checked at the endpoint level (row-level authorization) — see
# the IDOR exercise for the deliberate weakness in the companion endpoint.

@app.get("/api/assets", response_model=list[AssetRead])
def list_assets(
    search: str = "",
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Return the assets owned by the authenticated user, optionally filtered
    by hostname.

    Two filters apply: ownership (only the user's own assets) and the
    optional hostname search. The ownership filter is enforced at the
    query level, so a client cannot bypass it with query parameters.

    The `search` parameter is bound as a query parameter (`:search`),
    never interpolated into the SQL text. This is the fixed version of
    the SQL injection exercise.

    The result is paginated with `limit` (default 100, maximum 500) and
    `offset` (default 0). Results are ordered by id, so pages are stable.
    A client that sends no parameters receives at most the first 100
    assets.
    """
    # Escape LIKE wildcards so that the search is a literal substring match.
    escaped_search = (
        search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    )
    query = text(
        "SELECT id, hostname, ip_address, os, owner_id, created_at "
        "FROM assets WHERE owner_id = :owner_id "
        "AND hostname LIKE :search ESCAPE '\\' ORDER BY id "
        "LIMIT :limit OFFSET :offset"
    )
    result = db.execute(
        query,
        {
            "owner_id": current_user.id,
            "search": f"%{escaped_search}%",
            "limit": limit,
            "offset": offset,
        },
    ).fetchall()
    return [
        {
            "id": row[0],
            "hostname": row[1],
            "ip_address": row[2],
            "os": row[3],
            "owner_id": row[4],
            "created_at": row[5],
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
    current_user: models.User = Depends(get_current_user),
):
    """
    Create a new asset owned by the authenticated user.

    The owner is set from the authenticated user, not from the request
    body. If `owner_id` were a field in `AssetCreate`, a client could
    create assets owned by other users (mass assignment).
    """
    asset = models.Asset(
        hostname=payload.hostname,
        ip_address=str(payload.ip_address),
        os=payload.os,
        owner_id=current_user.id,
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return asset

@app.get("/api/assets/{asset_id}", response_model=AssetRead)
def get_asset(
    asset_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Return a single asset by id, if the authenticated user owns it.

    The query filters on both `id` and `owner_id`. This is the row-level
    authorisation that the vulnerable version was missing: a user can
    only retrieve an asset that belongs to them. Another user's asset is
    indistinguishable from a non-existent asset — both return 404, so
    the endpoint does not reveal whether a given id exists.

    This is the fixed version of the IDOR exercise in
    `docs/vuln-exercise-idor.md`. The vulnerable version (no ownership
    filter) was merged into `main` deliberately for the exercise, and the
    difference is documented there.

    Note on the 404 response: returning 404 (rather than 403) for an
    asset that exists but belongs to another user is deliberate. A 403
    would confirm to the caller that the asset exists — an information
    leak. A 404 is indistinguishable from a genuinely non-existent id.
    """
    asset = (
        db.query(models.Asset)
        .filter(
            models.Asset.id == asset_id,
            models.Asset.owner_id == current_user.id,
        )
        .first()
    )
    if asset is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset not found.",
        )
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
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)):
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

    # Always run one argon2 verification, even when the email does not exist,
    # so the response time does not reveal whether the account exists.
    password_hash = (
        user.password_hash if user is not None else DUMMY_PASSWORD_HASH
    )
    password_ok = verify_password(payload.password, password_hash)

    if user is None or not password_ok:
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
    # Responses that carry tokens must never be stored by browsers or proxies.
    response.headers["Cache-Control"] = "no-store"
    return TokenResponse(
        access_token=create_access_token(subject=subject, role=user.role),
        refresh_token=create_refresh_token(subject=subject, role=user.role),
    )


@app.post("/api/auth/refresh", response_model=TokenResponse)
def refresh(payload: RefreshRequest, response: Response, db: Session = Depends(get_db)):
    """
    Exchange a valid refresh token for a new pair of tokens.

    The refresh endpoint only accepts tokens whose `type` claim is
    "refresh". An access token presented here is rejected, which prevents
    a stolen access token from extending its own lifetime.

    Returns both a new access token AND a new refresh token. This is token
    reissue, not rotation in the security sense: the endpoint is stateless
    and does not invalidate the refresh token that was presented. The
    previous refresh token stays valid until its own 7-day expiry, so a
    leaked token keeps working even after the legitimate client refreshes.

    What does stop a leaked token: the user is re-read from the database on
    every refresh, so deactivating the account (is_active = False) blocks
    further refreshes, and the role comes from the database, not from the
    old token.

    Not implemented: revocation and reuse detection. Closing this gap needs
    a `jti` claim with a persistent denylist, or a token version counter
    per user (see Known gaps in the README).
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
    # Responses that carry tokens must never be stored by browsers or proxies.
    response.headers["Cache-Control"] = "no-store"
    return TokenResponse(
        access_token=create_access_token(subject=new_subject, role=user.role),
        refresh_token=create_refresh_token(subject=new_subject, role=user.role),
    )
