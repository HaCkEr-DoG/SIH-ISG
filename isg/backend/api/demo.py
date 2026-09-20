"""
ISG Demo API — triggers real backend scenarios for each demo button.
Every button executes genuine backend safety logic.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
import uuid

from database import get_db
from models import (
    ScholarshipApplication, ISGTransaction, TransactionStatus,
    ConsentRecord, TERMINAL_STATES,
)
from core.isg_pipeline import run_scholarship_pipeline, run_recovery_pipeline
from core.audit_engine import AuditEngine
from core.consent_policy import ConsentRegistry
from seed.seed_data import seed_all
from auth import verify_token

router = APIRouter(prefix="/api/demo", tags=["demo"], dependencies=[Depends(verify_token)])
_audit = AuditEngine()
_consent_registry = ConsentRegistry()


class DemoRunRequest(BaseModel):
    scenario: str  # VALID | SEMANTIC_MISMATCH | IDENTITY_MISMATCH | CONSENT_FAILURE | TIMEOUT | RECOVERY | REPLAY


class ResetRequest(BaseModel):
    pass


@router.post("/reset")
async def reset_demo(db: Session = Depends(get_db)):
    """Reset all demo transactions so scenarios can be re-run cleanly."""
    db.query(ISGTransaction).delete()
    from models import AuditEvent, AuthorizationLease, EffectRecord
    db.query(AuditEvent).delete()
    db.query(AuthorizationLease).delete()
    db.query(EffectRecord).delete()
    # Restore consents
    from models import ConsentRecord
    db.query(ConsentRecord).delete()
    db.commit()
    # Re-seed consents
    from seed.seed_data import _seed_consents
    _seed_consents(db)
    db.commit()
    return {"status": "reset", "message": "Demo reset complete. All scenarios ready."}


@router.post("/run")
async def run_demo_scenario(req: DemoRunRequest, db: Session = Depends(get_db)):
    """
    Run a named demo scenario. Every scenario triggers real backend processing.
    No hard-coded results.
    """
    scenario = req.scenario.upper()

    scenario_map = {
        "VALID": _run_valid,
        "SEMANTIC_MISMATCH": _run_semantic_mismatch,
        "IDENTITY_MISMATCH": _run_identity_mismatch,
        "CONSENT_FAILURE": _run_consent_failure,
        "TIMEOUT": _run_timeout,
        "RECOVERY": _run_recovery,
        "REPLAY": _run_replay,
    }

    handler = scenario_map.get(scenario)
    if not handler:
        raise HTTPException(status_code=400, detail=f"Unknown scenario: {scenario}")

    return await handler(db)


async def _get_or_create_tx(
    db: Session, app_id: str, idempotency_suffix: str
) -> tuple[ScholarshipApplication, ISGTransaction]:
    app = db.query(ScholarshipApplication).filter_by(id=app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail=f"Application {app_id} not found. Run /api/demo/reset first.")

    from core.transaction_sm import TransactionStateMachine
    tx_sm = TransactionStateMachine()
    idem_key = f"{app_id}-{idempotency_suffix}"
    tx = tx_sm.create_transaction(db, app.id, idempotency_key=idem_key)
    return app, tx


async def _run_valid(db: Session) -> dict:
    app, tx = await _get_or_create_tx(db, "APP-1001", "valid-v1")
    if tx.status in TERMINAL_STATES:
        return _already_done(tx, "VALID")
    result = await run_scholarship_pipeline(db, app, tx)
    return _format_result(result, "VALID — Priya Sharma")


async def _run_semantic_mismatch(db: Session) -> dict:
    app, tx = await _get_or_create_tx(db, "APP-2001", "semantic-v1")
    if tx.status in TERMINAL_STATES:
        return _already_done(tx, "SEMANTIC_MISMATCH")
    result = await run_scholarship_pipeline(db, app, tx)
    return _format_result(result, "SEMANTIC MISMATCH — Ravi Kumar (monthly income)")


async def _run_identity_mismatch(db: Session) -> dict:
    app, tx = await _get_or_create_tx(db, "APP-2002", "identity-v1")
    if tx.status in TERMINAL_STATES:
        return _already_done(tx, "IDENTITY_MISMATCH")
    result = await run_scholarship_pipeline(db, app, tx)
    return _format_result(result, "IDENTITY MISMATCH — Ravi Kumar (DOB conflict)")


async def _run_consent_failure(db: Session) -> dict:
    """
    Consent failure scenario: consent is valid at initial check,
    then revoked BEFORE the live recheck (simulating mid-flight revocation).
    The pipeline's live recheck catches it before any effect executes.
    """
    app, tx = await _get_or_create_tx(db, "APP-3001", "consent-v1")
    if tx.status in TERMINAL_STATES:
        return _already_done(tx, "CONSENT_FAILURE")

    result = await run_scholarship_pipeline(
        db, app, tx,
        revoke_consent_before_live_recheck=True,
    )
    return _format_result(result, "CONSENT FAILURE — Sunita Patil (consent revoked mid-flow)")


async def _run_timeout(db: Session) -> dict:
    """Timeout scenario: Revenue system times out → UNKNOWN_RESULT."""
    app, tx = await _get_or_create_tx(db, "APP-4001", "timeout-v1")
    if tx.status == TransactionStatus.UNKNOWN_RESULT:
        return _already_done(tx, "TIMEOUT")
    if tx.status in TERMINAL_STATES:
        return _already_done(tx, "TIMEOUT")
    result = await run_scholarship_pipeline(db, app, tx, simulate_timeout=True)
    return _format_result(result, "TIMEOUT — Vikram Rathod (Revenue system timeout)")


async def _run_recovery(db: Session) -> dict:
    """Recovery scenario: resolve UNKNOWN_RESULT transaction."""
    # First ensure there's an UNKNOWN_RESULT transaction
    idem_key = "APP-4001-timeout-v1"
    tx = db.query(ISGTransaction).filter_by(idempotency_key=idem_key).first()

    if not tx or tx.status not in (TransactionStatus.UNKNOWN_RESULT,):
        # Need to create the timeout first
        app, tx = await _get_or_create_tx(db, "APP-4001", "timeout-v1")
        if tx.status not in TERMINAL_STATES and tx.status != TransactionStatus.UNKNOWN_RESULT:
            await run_scholarship_pipeline(db, app, tx, simulate_timeout=True)
            db.refresh(tx)

    if tx.status in TERMINAL_STATES:
        return _already_done(tx, "RECOVERY")

    result = await run_recovery_pipeline(db, tx, simulate_effect_already_occurred=False)
    return _format_result(result, "RECOVERY — Vikram Rathod (safe retry after timeout)")


async def _run_replay(db: Session) -> dict:
    """Replay/duplicate scenario: same idempotency key submitted twice."""
    idem_key = "APP-1001-replay-v1"

    # Create first transaction normally
    app = db.query(ScholarshipApplication).filter_by(id="APP-1001").first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found.")

    from core.transaction_sm import TransactionStateMachine
    tx_sm = TransactionStateMachine()
    tx1 = tx_sm.create_transaction(db, app.id, idempotency_key=idem_key)

    if tx1.status not in TERMINAL_STATES:
        await run_scholarship_pipeline(db, app, tx1)
        db.refresh(tx1)

    # Now attempt duplicate — same idempotency key
    tx2 = tx_sm.create_transaction(db, app.id, idempotency_key=idem_key)

    # tx2 is the same transaction (idempotency key matched existing)
    if tx2.id == tx1.id:
        # This IS replay — tx2 is terminal, effect cannot run again
        return {
            "scenario": "REPLAY",
            "label": "REPLAY PROTECTION — Duplicate request blocked",
            "transaction_id": tx1.id,
            "status": tx1.status.value,
            "decision": "REJECT",
            "replay_detected": True,
            "explanation": (
                "A transaction with this idempotency key already exists in state "
                f"'{tx1.status.value}'. ISG returned the existing transaction result "
                "and did NOT execute a duplicate effect. "
                "Terminal transactions cannot execute additional effects."
            ),
            "technical_code": "SK-003-REPLAY-DETECTED",
        }

    return {"scenario": "REPLAY", "error": "Unexpected: separate transactions created."}


def _format_result(result, label: str) -> dict:
    return {
        "scenario": label,
        "transaction_id": result.transaction_id,
        "status": result.status,
        "decision": result.decision,
        "primary_reason": result.primary_reason,
        "explanation": result.explanation,
        "technical_code": result.technical_code,
        "stages": result.stages,
    }


def _already_done(tx: ISGTransaction, scenario: str) -> dict:
    return {
        "scenario": scenario,
        "transaction_id": tx.id,
        "status": tx.status.value,
        "decision": tx.safety_decision or tx.status.value,
        "primary_reason": "Transaction already processed.",
        "explanation": (
            f"This transaction is already in terminal state '{tx.status.value}'. "
            "Run /api/demo/reset to reset and re-run scenarios."
        ),
        "technical_code": "ALREADY-TERMINAL",
        "stages": [],
    }


@router.get("/applications")
async def list_applications(db: Session = Depends(get_db)):
    """List all seeded demo applications with their scenario descriptions."""
    apps = db.query(ScholarshipApplication).all()
    scenarios = {
        "APP-1001": "VALID — Priya Sharma (all checks pass)",
        "APP-2001": "SEMANTIC MISMATCH — Ravi Kumar (monthly income)",
        "APP-2002": "IDENTITY MISMATCH — Ravi Kumar (DOB conflict)",
        "APP-3001": "CONSENT FAILURE — Sunita Patil (consent revoked mid-flow)",
        "APP-4001": "TIMEOUT/RECOVERY — Vikram Rathod",
        "APP-1002": "VALID — Aditya Kulkarni",
        "APP-1003": "VALID — Meera Joshi",
    }
    return [
        {
            "id": a.id,
            "applicant_name": a.applicant_name,
            "applicant_dob": a.applicant_dob,
            "course": a.course,
            "family_id": a.family_id,
            "scenario": scenarios.get(a.id, ""),
        }
        for a in apps
    ]
