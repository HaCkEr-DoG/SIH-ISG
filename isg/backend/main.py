"""
UNBOUND ISG — Interoperability Safety Gateway
FastAPI application entry point.
Prototype simulation using synthetic data. Not a production government system.
"""
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager

from config import get_settings
from database import _get_engine, _get_session_local, Base
from api.demo import router as demo_router
from api.audit_routes import router as audit_router
from api.governance import router as governance_router
from api.safety_suite import router as safety_router
from seed.seed_data import seed_all

_BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
_FRONTEND_BUILD = os.path.normpath(os.path.join(_BACKEND_DIR, "..", "frontend", "build"))
_SERVE_FRONTEND = os.path.isdir(_FRONTEND_BUILD)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables
    Base.metadata.create_all(bind=_get_engine())
    # Seed demo data
    db = _get_session_local()()
    try:
        seed_all(db)
    finally:
        db.close()
    yield


app = FastAPI(
    title="UNBOUND ISG — Interoperability Safety Gateway",
    description=(
        "Prototype implementation for SIH 2026 PS26129. "
        "Demonstrates safe cross-system government data exchange. "
        "Synthetic data only — not a production system."
    ),
    version="1.0.0-prototype",
    lifespan=lifespan,
)

_settings = get_settings()
_origins = [o.strip() for o in _settings.allowed_origins.split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=_origins != ["*"],
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(demo_router)
app.include_router(audit_router)
app.include_router(governance_router)
app.include_router(safety_router)

if _SERVE_FRONTEND:
    _assets_dir = os.path.join(_FRONTEND_BUILD, "assets")
    if os.path.isdir(_assets_dir):
        app.mount("/assets", StaticFiles(directory=_assets_dir), name="assets")


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "ISG Backend"}


@app.get("/{full_path:path}", include_in_schema=False)
async def spa_fallback(full_path: str):
    if _SERVE_FRONTEND:
        candidate = os.path.join(_FRONTEND_BUILD, full_path)
        if os.path.isfile(candidate):
            return FileResponse(candidate)
        return FileResponse(os.path.join(_FRONTEND_BUILD, "index.html"))
    return {
        "system": "UNBOUND ISG — Interoperability Safety Gateway",
        "version": "1.0.0-prototype",
        "status": "OPERATIONAL",
        "docs": "/docs",
    }
