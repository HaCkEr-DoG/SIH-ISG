"""
ISG Audit Engine — Tamper-evident event records for every significant decision.
Every audit event links to a real transaction state.
"""
from __future__ import annotations
from datetime import datetime, timezone
from typing import Optional, Any
from sqlalchemy.orm import Session
from models import AuditEvent
import hashlib
import json
import uuid


AUDIT_STAGES = {
    "AUTHENTICATION": "Authentication & Authority Check",
    "PASSPORT": "Service Passport Validation",
    "CONTRACT": "Contract Validation",
    "STRUCTURAL_VALIDATION": "Structural Validation",
    "DATA_QUALITY": "Data Quality Check",
    "SEMANTIC_VALIDATION": "Semantic Validation",
    "PROVENANCE": "Provenance Check",
    "FRESHNESS": "Freshness Check",
    "IDENTITY": "Identity Pipeline",
    "FIELD_AUTHORIZATION": "Field Authorization",
    "PURPOSE": "Purpose Validation",
    "POLICY": "Policy Engine",
    "CONSENT": "Consent Registry (Initial)",
    "RISK": "Risk Assessment",
    "PARTICIPANT_CAPABILITY": "Participant Capability Check",
    "IDEMPOTENCY": "Idempotency / Replay Check",
    "EFFECT_AUTHORIZATION": "Effect Authorization",
    "LIVE_CONSENT_RECHECK": "Live Consent Recheck",
    "LIVE_AUTHORIZATION_RECHECK": "Live Authorization Recheck",
    "BOUNDED_EFFECT": "Bounded Effect Execution",
    "OBSERVATION": "Effect Observation",
    "RECOVERY": "Recovery / Reconciliation",
    "SAFETY_KERNEL": "Safety Kernel Decision",
    "TERMINAL_STATE": "Terminal State",
}


class AuditEngine:
    """
    Records every significant ISG decision with evidence.
    Events are chained by sequence number for ordering.
    Uses SHA-256 payload hash for tamper-evidence (not tamper-proof).
    """

    def _compute_hash(self, data: dict) -> str:
        payload = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(payload.encode()).hexdigest()

    def record(
        self,
        db: Session,
        transaction_id: str,
        event_type: str,
        stage: str,
        result: str,
        detail: Optional[str] = None,
        evidence: Optional[dict] = None,
        sequence: Optional[int] = None,
    ) -> AuditEvent:
        """Record an audit event. Evidence dict is hashed for tamper-evidence."""
        if sequence is None:
            # Auto-increment
            last = (
                db.query(AuditEvent)
                .filter(AuditEvent.transaction_id == transaction_id)
                .order_by(AuditEvent.sequence.desc())
                .first()
            )
            sequence = (last.sequence + 1) if last else 1

        evidence_data = evidence or {}
        payload = {
            "transaction_id": transaction_id,
            "event_type": event_type,
            "stage": stage,
            "result": result,
            "detail": detail,
            "evidence": evidence_data,
            "sequence": sequence,
        }
        payload_hash = self._compute_hash(payload)

        event = AuditEvent(
            id=str(uuid.uuid4()),
            transaction_id=transaction_id,
            event_type=event_type,
            stage=stage,
            result=result,
            detail=detail,
            payload_hash=payload_hash,
            evidence=evidence_data,
            sequence=sequence,
        )
        db.add(event)
        db.commit()
        return event

    def get_trail(self, db: Session, transaction_id: str) -> list[AuditEvent]:
        return (
            db.query(AuditEvent)
            .filter(AuditEvent.transaction_id == transaction_id)
            .order_by(AuditEvent.sequence)
            .all()
        )

    def build_decision_capsule(
        self,
        db: Session,
        transaction_id: str,
        transaction: Any,
        application: Any,
    ) -> dict:
        """
        Build the human-readable Decision Capsule from real audit trail.
        Every field must correspond to actual transaction state.
        """
        events = self.get_trail(db, transaction_id)

        capsule = {
            "transaction_id": transaction_id,
            "application_id": transaction.application_id,
            "applicant_name": application.applicant_name if application else "UNKNOWN",
            "submitted_at": application.submitted_at.isoformat() if application and application.submitted_at else None,
            "final_state": transaction.status.value,
            "safety_decision": transaction.safety_decision,
            "quarantine_reason": transaction.quarantine_reason,
            "rejection_reason": transaction.rejection_reason,
            "effect_authorized": transaction.effect_authorized,
            "effect_observed": transaction.effect_observed,
            "effect_verified": transaction.effect_verified,
            "state_version": transaction.state_version,
            "audit_trail": [
                {
                    "sequence": e.sequence,
                    "stage": e.stage,
                    "event_type": e.event_type,
                    "result": e.result,
                    "detail": e.detail,
                    "evidence": e.evidence,
                    "payload_hash": e.payload_hash,
                    "recorded_at": e.created_at.isoformat() if e.created_at else None,
                }
                for e in events
            ],
            "summary": _build_summary(transaction, events),
            "prototype_disclaimer": (
                "Prototype simulation using synthetic data. "
                "Not a production government system."
            ),
        }
        return capsule


def _build_summary(transaction: Any, events: list[AuditEvent]) -> dict:
    """Extract key decision points from the audit trail for summary display."""
    stages_seen = {}
    for e in events:
        stages_seen[e.stage] = {"result": e.result, "detail": e.detail}

    def get(stage: str) -> Optional[dict]:
        return stages_seen.get(stage)

    return {
        "who": "SCHOLARSHIP_PORTAL → ISG → [REVENUE, EDUCATION, IDENTITY]",
        "what": "Maharashtra Scholarship Eligibility Verification",
        "why": "Citizen-initiated scholarship application — verification of income, enrollment, and identity",
        "policy": get("POLICY"),
        "contract": get("CONTRACT"),
        "semantic_check": get("SEMANTIC_VALIDATION"),
        "identity_decision": get("IDENTITY"),
        "consent_initial": get("CONSENT"),
        "consent_recheck": get("LIVE_CONSENT_RECHECK"),
        "safety_kernel": get("SAFETY_KERNEL"),
        "effect_authorization": get("EFFECT_AUTHORIZATION"),
        "observation": get("OBSERVATION"),
        "recovery": get("RECOVERY"),
        "final_state": transaction.status.value,
    }
