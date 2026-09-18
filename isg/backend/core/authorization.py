"""
ISG Authorization Lease and Effect Envelope.
An AuthorizationLease is scoped, time-bounded, single-use, and request-bound.
An expired or mismatched lease MUST fail.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime, timezone, timedelta
from enum import Enum
import hashlib
import json
import uuid
from sqlalchemy.orm import Session
from models import AuthorizationLease, EffectRecord
from config import get_settings

settings = get_settings()


class LeaseValidationResult(str, Enum):
    VALID = "VALID"
    EXPIRED = "EXPIRED"
    ALREADY_USED = "ALREADY_USED"
    REVOKED = "REVOKED"
    PARAMETER_MISMATCH = "PARAMETER_MISMATCH"
    NOT_FOUND = "NOT_FOUND"
    ENVIRONMENT_MISMATCH = "ENVIRONMENT_MISMATCH"


@dataclass
class EffectEnvelope:
    """Defines the authorized effect for a transaction."""
    effect_id: str
    transaction_id: str
    operation: str
    target: str
    effect_class: str               # READ / WRITE / IDEMPOTENT_WRITE
    purpose: str
    environment: str                # demo / staging / production
    parameters: dict
    parameter_hash: str
    validity_window_start: datetime
    validity_window_end: datetime
    reversibility: str              # REVERSIBLE / IRREVERSIBLE / CONDITIONAL
    max_effect_value: Optional[float] = None

    @classmethod
    def create(
        cls,
        transaction_id: str,
        operation: str,
        target: str,
        effect_class: str,
        purpose: str,
        environment: str,
        parameters: dict,
        reversibility: str = "CONDITIONAL",
        validity_seconds: int = 300,
        max_effect_value: Optional[float] = None,
    ) -> "EffectEnvelope":
        now = datetime.now(timezone.utc)
        param_hash = hashlib.sha256(
            json.dumps(parameters, sort_keys=True).encode()
        ).hexdigest()[:16]
        return cls(
            effect_id=str(uuid.uuid4()),
            transaction_id=transaction_id,
            operation=operation,
            target=target,
            effect_class=effect_class,
            purpose=purpose,
            environment=environment,
            parameters=parameters,
            parameter_hash=param_hash,
            validity_window_start=now,
            validity_window_end=now + timedelta(seconds=validity_seconds),
            reversibility=reversibility,
            max_effect_value=max_effect_value,
        )

    def is_within_validity_window(self) -> bool:
        now = datetime.now(timezone.utc)
        return self.validity_window_start <= now <= self.validity_window_end

    def to_dict(self) -> dict:
        return {
            "effect_id": self.effect_id,
            "transaction_id": self.transaction_id,
            "operation": self.operation,
            "target": self.target,
            "effect_class": self.effect_class,
            "purpose": self.purpose,
            "environment": self.environment,
            "parameter_hash": self.parameter_hash,
            "validity_window_start": self.validity_window_start.isoformat(),
            "validity_window_end": self.validity_window_end.isoformat(),
            "reversibility": self.reversibility,
            "max_effect_value": self.max_effect_value,
        }


class AuthorizationLeaseManager:
    """
    Issues, validates, and uses authorization leases.
    A lease is strictly single-use for consequential writes.
    """

    def issue_lease(
        self,
        db: Session,
        transaction_id: str,
        envelope: EffectEnvelope,
    ) -> AuthorizationLease:
        """Issue a new authorization lease. Replaces any existing lease for this transaction."""
        now = datetime.now(timezone.utc)
        lease = AuthorizationLease(
            id=str(uuid.uuid4()),
            transaction_id=transaction_id,
            effect_id=envelope.effect_id,
            operation=envelope.operation,
            target=envelope.target,
            purpose=envelope.purpose,
            environment=envelope.environment,
            parameter_hash=envelope.parameter_hash,
            issued_at=now,
            expires_at=envelope.validity_window_end,
            used=False,
            revoked=False,
        )
        # Remove old lease if any
        db.query(AuthorizationLease).filter(
            AuthorizationLease.transaction_id == transaction_id
        ).delete()
        db.add(lease)
        db.commit()
        db.refresh(lease)
        return lease

    def validate_lease(
        self,
        db: Session,
        transaction_id: str,
        expected_parameter_hash: str,
        expected_environment: str,
    ) -> tuple[LeaseValidationResult, Optional[AuthorizationLease]]:
        """
        Validate the lease before executing an effect.
        This is the Live Authorization Recheck.
        """
        lease = (
            db.query(AuthorizationLease)
            .filter(AuthorizationLease.transaction_id == transaction_id)
            .first()
        )
        if not lease:
            return LeaseValidationResult.NOT_FOUND, None

        if lease.revoked:
            return LeaseValidationResult.REVOKED, lease

        if lease.used:
            return LeaseValidationResult.ALREADY_USED, lease

        now = datetime.now(timezone.utc)
        exp = lease.expires_at if lease.expires_at.tzinfo else lease.expires_at.replace(tzinfo=timezone.utc)
        if exp < now:
            return LeaseValidationResult.EXPIRED, lease

        if lease.parameter_hash != expected_parameter_hash:
            return LeaseValidationResult.PARAMETER_MISMATCH, lease

        if lease.environment != expected_environment:
            return LeaseValidationResult.ENVIRONMENT_MISMATCH, lease

        return LeaseValidationResult.VALID, lease

    def consume_lease(self, db: Session, lease: AuthorizationLease) -> None:
        """Mark lease as used. Single-use enforcement."""
        lease.used = True
        lease.used_at = datetime.now(timezone.utc)
        db.commit()

    def revoke_lease(
        self, db: Session, transaction_id: str, reason: str
    ) -> bool:
        """Revoke an active lease — e.g., consent was revoked."""
        lease = (
            db.query(AuthorizationLease)
            .filter(AuthorizationLease.transaction_id == transaction_id)
            .first()
        )
        if not lease or lease.used:
            return False
        lease.revoked = True
        lease.revoked_at = datetime.now(timezone.utc)
        lease.revocation_reason = reason
        db.commit()
        return True
