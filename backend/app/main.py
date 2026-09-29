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

from fastapi import Depends, FastAPI, status
from sqlalchemy.orm import Session

from app import models
from app.database import Base, engine, get_db
from app.schemas import AssetCreate, AssetRead


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
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/")
def read_root():
    return {"message": "Secure Fullstack Lab API is running"}


@app.get("/api/hello")
def read_hello():
    return {"message": "Hello from FastAPI 👋"}


@app.get("/api/assets", response_model=list[AssetRead])
def list_assets(db: Session = Depends(get_db)):
    """Return all assets stored in the database."""
    return db.query(models.Asset).order_by(models.Asset.id).all()


@app.post(
    "/api/assets",
    response_model=AssetRead,
    status_code=status.HTTP_201_CREATED,
)
def create_asset(payload: AssetCreate, db: Session = Depends(get_db)):
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
