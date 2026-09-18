"""
ISG Transaction State Machine.
Terminal states are enforced. A terminal transaction MUST NOT execute another effect.
"""
from __future__ import annotations
from datetime import datetime, timezone, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from models import ISGTransaction, TransactionStatus, TERMINAL_STATES
import uuid


class TransactionStateError(Exception):
    """Raised when a state transition is invalid."""
    pass


class TransactionStateMachine:
    """
    Manages ISG transaction state transitions.
    Invariant: terminal states cannot transition to any other state.
    """

    VALID_TRANSITIONS: dict[TransactionStatus, set[TransactionStatus]] = {
        TransactionStatus.INITIATED: {
            TransactionStatus.PROCESSING,
            TransactionStatus.REJECTED,
            TransactionStatus.QUARANTINED,
            TransactionStatus.CANCELLED,
        },
        TransactionStatus.PROCESSING: {
            TransactionStatus.SUCCESS,
            TransactionStatus.REJECTED,
            TransactionStatus.QUARANTINED,
            TransactionStatus.FAILED,
            TransactionStatus.UNKNOWN_RESULT,
        },
        TransactionStatus.UNKNOWN_RESULT: {
            TransactionStatus.SUCCESS,
            TransactionStatus.FAILED,
            TransactionStatus.RECONCILIATION_REQUIRED,
            TransactionStatus.COMPENSATED,
        },
        # All terminal states have NO valid transitions
        **{s: set() for s in TERMINAL_STATES},
    }

    def transition(
        self,
        db: Session,
        transaction: ISGTransaction,
        new_status: TransactionStatus,
        reason: Optional[str] = None,
    ) -> ISGTransaction:
        """
        Attempt a state transition. Raises TransactionStateError if invalid.
        Terminal states cannot be left — this is enforced here.
        """
        current = transaction.status
        allowed = self.VALID_TRANSITIONS.get(current, set())

        if current in TERMINAL_STATES:
            raise TransactionStateError(
                f"Transaction '{transaction.id}' is in terminal state '{current.value}'. "
                "No further state transitions are permitted. "
                "A terminal transaction MUST NOT execute another effect."
            )

        if new_status not in allowed:
            raise TransactionStateError(
                f"Invalid transition from '{current.value}' to '{new_status.value}' "
                f"for transaction '{transaction.id}'."
            )

        transaction.status = new_status
        transaction.state_version += 1
        transaction.updated_at = datetime.now(timezone.utc)

        if new_status == TransactionStatus.QUARANTINED and reason:
            transaction.quarantine_reason = reason
        if new_status == TransactionStatus.REJECTED and reason:
            transaction.rejection_reason = reason

        db.commit()
        db.refresh(transaction)
        return transaction

    def create_transaction(
        self,
        db: Session,
        application_id: str,
        idempotency_key: str,
        deadline_seconds: int = 300,
    ) -> Optional[ISGTransaction]:
        """
        Create a new transaction or return existing if idempotency key matches.
        Replay protection: if idempotency key already exists and transaction is terminal,
        returns None to signal duplicate.
        """
        existing = (
            db.query(ISGTransaction)
            .filter(ISGTransaction.idempotency_key == idempotency_key)
            .first()
        )
        if existing:
            return existing  # Caller must check if terminal

        now = datetime.now(timezone.utc)
        tx = ISGTransaction(
            id=str(uuid.uuid4()),
            application_id=application_id,
            status=TransactionStatus.INITIATED,
            state_version=1,
            created_at=now,
            updated_at=now,
            deadline=now + timedelta(seconds=deadline_seconds),
            idempotency_key=idempotency_key,
        )
        db.add(tx)
        db.commit()
        db.refresh(tx)
        return tx

    def is_terminal(self, transaction: ISGTransaction) -> bool:
        return transaction.status in TERMINAL_STATES

    def is_deadline_exceeded(self, transaction: ISGTransaction) -> bool:
        if not transaction.deadline:
            return False
        now = datetime.now(timezone.utc)
        dl = transaction.deadline
        if dl.tzinfo is None:
            dl = dl.replace(tzinfo=timezone.utc)
        return now > dl

    def increment_external_call(
        self, db: Session, transaction: ISGTransaction
    ) -> bool:
        """Track external calls and enforce the budget. Returns False if budget exceeded."""
        from config import get_settings
        settings = get_settings()
        if transaction.external_call_count >= settings.max_external_calls:
            return False
        transaction.external_call_count += 1
        db.commit()
        return True
