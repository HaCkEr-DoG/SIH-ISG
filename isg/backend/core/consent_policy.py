"""
ISG Consent Registry and Policy Engine.
Consent state is checked live before any effect boundary.
Policy must be versioned and explicitly active.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
from datetime import datetime, timezone
from enum import Enum
from sqlalchemy.orm import Session
from models import ConsentRecord, PolicyRecord


class ConsentCheckResult(str, Enum):
    VALID = "VALID"
    REVOKED = "REVOKED"
    EXPIRED = "EXPIRED"
    NOT_FOUND = "NOT_FOUND"
    NOT_REQUIRED = "NOT_REQUIRED"


class PolicyCheckResult(str, Enum):
    PASS = "PASS"
    PURPOSE_MISMATCH = "PURPOSE_MISMATCH"
    ROLE_UNAUTHORIZED = "ROLE_UNAUTHORIZED"
    DATA_NOT_ALLOWED = "DATA_NOT_ALLOWED"
    POLICY_INACTIVE = "POLICY_INACTIVE"
    POLICY_NOT_FOUND = "POLICY_NOT_FOUND"
    GOVERNANCE_REQUIRED = "GOVERNANCE_REQUIRED"


@dataclass
class ConsentCheckReport:
    result: ConsentCheckResult
    citizen_id: str
    application_id: str
    purpose: str
    explanation: str
    revoked_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None

    def is_valid(self) -> bool:
        return self.result == ConsentCheckResult.VALID

    def to_dict(self) -> dict:
        return {
            "result": self.result.value,
            "citizen_id": self.citizen_id,
            "application_id": self.application_id,
            "purpose": self.purpose,
            "explanation": self.explanation,
            "revoked_at": self.revoked_at.isoformat() if self.revoked_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "is_valid": self.is_valid(),
        }


@dataclass
class PolicyCheckReport:
    result: PolicyCheckResult
    policy_id: Optional[str]
    policy_version: Optional[str]
    explanation: str
    blocking: bool

    def to_dict(self) -> dict:
        return {
            "result": self.result.value,
            "policy_id": self.policy_id,
            "policy_version": self.policy_version,
            "explanation": self.explanation,
            "blocking": self.blocking,
        }


class ConsentRegistry:
    """Manages consent records and performs live consent validation."""

    def check_consent(
        self, db: Session, citizen_id: str, application_id: str, purpose: str
    ) -> ConsentCheckReport:
        """
        Live consent check. This MUST be called before any effect boundary.
        Consent revocation MUST be detected even after an initial valid check.
        """
        record = (
            db.query(ConsentRecord)
            .filter(
                ConsentRecord.citizen_id == citizen_id,
                ConsentRecord.application_id == application_id,
                ConsentRecord.purpose == purpose,
            )
            .first()
        )

        if not record:
            return ConsentCheckReport(
                result=ConsentCheckResult.NOT_FOUND,
                citizen_id=citizen_id,
                application_id=application_id,
                purpose=purpose,
                explanation=f"No consent record found for citizen '{citizen_id}', application '{application_id}', purpose '{purpose}'.",
            )

        now = datetime.now(timezone.utc)

        if record.revoked:
            return ConsentCheckReport(
                result=ConsentCheckResult.REVOKED,
                citizen_id=citizen_id,
                application_id=application_id,
                purpose=purpose,
                explanation=(
                    f"Consent was REVOKED at {record.revoked_at}. "
                    f"Reason: {record.revocation_reason or 'Not specified'}. "
                    "Effect cannot proceed without valid consent."
                ),
                revoked_at=record.revoked_at,
            )

        def _as_aware(dt) -> datetime:
            """Normalize a possibly-naive datetime to UTC-aware."""
            if dt is None:
                return dt
            if hasattr(dt, 'tzinfo') and dt.tzinfo is None:
                return dt.replace(tzinfo=timezone.utc)
            return dt

        expires = _as_aware(record.expires_at)
        if expires and expires < now:
            return ConsentCheckReport(
                result=ConsentCheckResult.EXPIRED,
                citizen_id=citizen_id,
                application_id=application_id,
                purpose=purpose,
                explanation=(
                    f"Consent EXPIRED at {expires}. "
                    "Effect cannot proceed with expired consent."
                ),
                expires_at=expires,
            )

        return ConsentCheckReport(
            result=ConsentCheckResult.VALID,
            citizen_id=citizen_id,
            application_id=application_id,
            purpose=purpose,
            explanation="Consent is current, not revoked, and not expired.",
            expires_at=record.expires_at,
        )

    def revoke_consent(
        self,
        db: Session,
        citizen_id: str,
        application_id: str,
        purpose: str,
        reason: str = "CITIZEN_REQUESTED",
    ) -> bool:
        """Revoke consent. This takes effect immediately for all future checks."""
        record = (
            db.query(ConsentRecord)
            .filter(
                ConsentRecord.citizen_id == citizen_id,
                ConsentRecord.application_id == application_id,
                ConsentRecord.purpose == purpose,
            )
            .first()
        )
        if not record:
            return False
        record.revoked = True
        record.revoked_at = datetime.now(timezone.utc)
        record.revocation_reason = reason
        db.commit()
        return True


class PolicyEngine:
    """Validates that a requested operation is authorized under current policy."""

    def check_policy(
        self,
        db: Session,
        purpose: str,
        requested_data_fields: list[str],
        role: str = "SCHOLARSHIP_PORTAL",
    ) -> PolicyCheckReport:
        """Evaluate active policy for the given purpose."""
        policy = (
            db.query(PolicyRecord)
            .filter(
                PolicyRecord.purpose == purpose,
                PolicyRecord.status == "ACTIVE",
            )
            .first()
        )

        if not policy:
            return PolicyCheckReport(
                result=PolicyCheckResult.POLICY_NOT_FOUND,
                policy_id=None,
                policy_version=None,
                explanation=f"No active policy found for purpose '{purpose}'. Cannot authorize operation.",
                blocking=True,
            )

        now = datetime.now(timezone.utc)
        if policy.effective_until and policy.effective_until < now:
            return PolicyCheckReport(
                result=PolicyCheckResult.POLICY_INACTIVE,
                policy_id=policy.policy_id,
                policy_version=policy.version,
                explanation=f"Policy '{policy.policy_id}' v{policy.version} has expired.",
                blocking=True,
            )

        if role not in policy.roles:
            return PolicyCheckReport(
                result=PolicyCheckResult.ROLE_UNAUTHORIZED,
                policy_id=policy.policy_id,
                policy_version=policy.version,
                explanation=f"Role '{role}' is not authorized under policy '{policy.policy_id}'.",
                blocking=True,
            )

        allowed = set(policy.allowed_data)
        for field in requested_data_fields:
            if field not in allowed:
                return PolicyCheckReport(
                    result=PolicyCheckResult.DATA_NOT_ALLOWED,
                    policy_id=policy.policy_id,
                    policy_version=policy.version,
                    explanation=(
                        f"Field '{field}' is not permitted under policy '{policy.policy_id}' v{policy.version} "
                        f"for purpose '{purpose}'."
                    ),
                    blocking=True,
                )

        return PolicyCheckReport(
            result=PolicyCheckResult.PASS,
            policy_id=policy.policy_id,
            policy_version=policy.version,
            explanation=(
                f"Policy '{policy.policy_id}' v{policy.version} authorizes this operation "
                f"for role '{role}' and purpose '{purpose}'."
            ),
            blocking=False,
        )
