"""
Entry point for the Secure Fullstack Lab API.

Responsible only for:
- creating the FastAPI app
- configuring CORS
- creating database tables on startup
- defining HTTP endpoints
"""

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app import models
from app.database import Base, engine, get_db
from app.schemas import AssetCreate, AssetRead

# Origins allowed to call this API.
# Keep this in sync with the frontend's host — when the lab network changes,
# update here (and only here).
ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://192.168.1.173:5173",
]


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

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
