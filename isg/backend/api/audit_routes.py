"""ISG Audit and Decision Capsule API."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from database import get_db
from models import ISGTransaction, ScholarshipApplication, TransactionStatus
from auth import verify_token
from core.audit_engine import AuditEngine

router = APIRouter(prefix="/api/audit", tags=["audit"], dependencies=[Depends(verify_token)])
_audit = AuditEngine()


@router.get("/transaction/{transaction_id}")
async def get_transaction_audit(transaction_id: str, db: Session = Depends(get_db)):
    """Get full audit trail for a transaction."""
    tx = db.query(ISGTransaction).filter_by(id=transaction_id).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found.")
    events = _audit.get_trail(db, transaction_id)
    return {
        "transaction_id": transaction_id,
        "status": tx.status.value,
        "safety_decision": tx.safety_decision,
        "state_version": tx.state_version,
        "audit_trail": [
            {
                "sequence": e.sequence,
                "stage": e.stage,
                "result": e.result,
                "detail": e.detail,
                "evidence": e.evidence,
                "payload_hash": e.payload_hash,
                "recorded_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in events
        ],
    }


@router.get("/capsule/{transaction_id}")
async def get_decision_capsule(transaction_id: str, db: Session = Depends(get_db)):
    """Get the human-readable Decision Capsule for a transaction."""
    tx = db.query(ISGTransaction).filter_by(id=transaction_id).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found.")
    app = db.query(ScholarshipApplication).filter_by(id=tx.application_id).first()
    capsule = _audit.build_decision_capsule(db, transaction_id, tx, app)
    return capsule


@router.get("/transactions")
async def list_transactions(db: Session = Depends(get_db)):
    """List all transactions with status."""
    txs = db.query(ISGTransaction).order_by(ISGTransaction.created_at.desc()).all()
    result = []
    for tx in txs:
        app = db.query(ScholarshipApplication).filter_by(id=tx.application_id).first()
        result.append({
            "transaction_id": tx.id,
            "application_id": tx.application_id,
            "applicant_name": app.applicant_name if app else "UNKNOWN",
            "status": tx.status.value,
            "safety_decision": tx.safety_decision,
            "quarantine_reason": tx.quarantine_reason,
            "created_at": tx.created_at.isoformat() if tx.created_at else None,
            "state_version": tx.state_version,
            "effect_authorized": tx.effect_authorized,
            "effect_observed": tx.effect_observed,
        })
    return result


class RemediationRequest(BaseModel):
    action: str  # "transform" | "request" | "reject"
    operator_note: str = ""


_ACTION_STATUS = {
    "transform": TransactionStatus.SUCCESS,
    "request":   TransactionStatus.INITIATED,
    "reject":    TransactionStatus.REJECTED,
}

_ACTION_LABEL = {
    "transform": "APPROVE_AND_FORWARD",
    "request":   "REQUEST_RESUBMISSION",
    "reject":    "REJECT_AND_BLOCK",
}


@router.post("/remediation/{transaction_id}")
async def apply_remediation(
    transaction_id: str,
    body: RemediationRequest,
    db: Session = Depends(get_db),
):
    """Operator applies a remediation action to a QUARANTINED transaction."""
    tx = db.query(ISGTransaction).filter_by(id=transaction_id).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found.")
    if tx.status != TransactionStatus.QUARANTINED:
        raise HTTPException(status_code=400, detail="Transaction is not in QUARANTINED state.")

    new_status = _ACTION_STATUS.get(body.action, TransactionStatus.INITIATED)
    label = _ACTION_LABEL.get(body.action, body.action.upper())

    # Append operator audit event
    import uuid, datetime
    from models import AuditEvent
    seq = len(tx.audit_events) + 1
    event = AuditEvent(
        id=str(uuid.uuid4()),
        transaction_id=transaction_id,
        event_type="OPERATOR_ACTION",
        stage="OPERATOR",
        result=label,
        detail=f"Operator applied remediation '{label}'. {body.operator_note}".strip(". ") + ".",
        payload_hash=None,
        evidence={"action": body.action, "operator_note": body.operator_note},
        created_at=datetime.datetime.utcnow(),
        sequence=seq,
    )
    db.add(event)

    tx.status = new_status
    tx.state_version += 1
    db.commit()

    return {
        "transaction_id": transaction_id,
        "action": label,
        "new_status": new_status.value,
        "message": f"Remediation '{label}' applied. Transaction is now {new_status.value}.",
    }


@router.post("/consent/revoke/{application_id}")
async def revoke_consent(
    application_id: str,
    reason: str = "CITIZEN_REQUESTED",
    db: Session = Depends(get_db),
):
    """Revoke consent for an application — demonstrates live consent state change."""
    from core.consent_policy import ConsentRegistry
    app = db.query(ScholarshipApplication).filter_by(id=application_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found.")
    cr = ConsentRegistry()
    revoked = cr.revoke_consent(
        db, citizen_id=app.applicant_id_ref,
        application_id=application_id,
        purpose=app.purpose,
        reason=reason,
    )
    return {
        "application_id": application_id,
        "revoked": revoked,
        "message": f"Consent revoked for {app.applicant_name}." if revoked else "No active consent found.",
    }
