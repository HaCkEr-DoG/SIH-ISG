"""
UNBOUND ISG — Interoperability Safety Gateway
FastAPI application entry point.
Prototype simulation using synthetic data. Not a production government system.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from database import _get_engine, _get_session_local, Base
from api.demo import router as demo_router
from api.audit_routes import router as audit_router
from api.governance import router as governance_router
from api.safety_suite import router as safety_router
from seed.seed_data import seed_all


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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(demo_router)
app.include_router(audit_router)
app.include_router(governance_router)
app.include_router(safety_router)


@app.get("/")
async def root():
    return {
        "system": "UNBOUND ISG — Interoperability Safety Gateway",
        "version": "2.0.0-prototype",
        "status": "OPERATIONAL",
        "disclaimer": "Prototype simulation using synthetic data. Not a production government system.",
        "endpoints": {
            "demo": "/api/demo/run",
            "reset": "/api/demo/reset",
            "applications": "/api/demo/applications",
            "transactions": "/api/audit/transactions",
            "capsule": "/api/audit/capsule/{transaction_id}",
            "audit": "/api/audit/transaction/{transaction_id}",
            "passports": "/api/governance/passports",
            "contracts": "/api/governance/contracts",
            "ai_mapping": "/api/governance/ai/mapping-suggestion",
            "schema_drift": "/api/governance/schema-drift/status",
            "safety_tests": "/api/safety/tests",
            "run_tests": "/api/safety/run-tests",
            "docs": "/docs",
        },
    }


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "ISG Backend"}
