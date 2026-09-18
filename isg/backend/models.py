"""SQLAlchemy database models for ISG prototype."""
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime, Text, JSON,
    ForeignKey, Enum as SAEnum, Index
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from database import Base


class TransactionStatus(str, enum.Enum):
    INITIATED = "INITIATED"
    PROCESSING = "PROCESSING"
    SUCCESS = "SUCCESS"
    REJECTED = "REJECTED"
    QUARANTINED = "QUARANTINED"
    FAILED = "FAILED"
    COMPENSATED = "COMPENSATED"
    RECONCILIATION_REQUIRED = "RECONCILIATION_REQUIRED"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"
    UNKNOWN_RESULT = "UNKNOWN_RESULT"


TERMINAL_STATES = {
    TransactionStatus.SUCCESS,
    TransactionStatus.REJECTED,
    TransactionStatus.QUARANTINED,
    TransactionStatus.FAILED,
    TransactionStatus.COMPENSATED,
    TransactionStatus.RECONCILIATION_REQUIRED,
    TransactionStatus.EXPIRED,
    TransactionStatus.CANCELLED,
}


class ScholarshipApplication(Base):
    __tablename__ = "scholarship_applications"

    id = Column(String, primary_key=True)
    applicant_name = Column(String, nullable=False)
    applicant_dob = Column(String, nullable=False)
    applicant_id_ref = Column(String, nullable=False)
    course = Column(String, nullable=False)
    family_id = Column(String, nullable=False)
    purpose = Column(String, default="SCHOLARSHIP_ELIGIBILITY_CHECK")
    submitted_at = Column(DateTime, server_default=func.now())
    consent_given = Column(Boolean, default=True)
    consent_revoked_at = Column(DateTime, nullable=True)

    transactions = relationship("ISGTransaction", back_populates="application")


class ISGTransaction(Base):
    __tablename__ = "isg_transactions"

    id = Column(String, primary_key=True)
    application_id = Column(String, ForeignKey("scholarship_applications.id"), nullable=False)
    status = Column(SAEnum(TransactionStatus), default=TransactionStatus.INITIATED, nullable=False)
    state_version = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    deadline = Column(DateTime, nullable=True)
    retry_count = Column(Integer, default=0)
    external_call_count = Column(Integer, default=0)
    correction_depth = Column(Integer, default=0)
    idempotency_key = Column(String, nullable=True)

    # Safety decision summary
    safety_decision = Column(String, nullable=True)
    quarantine_reason = Column(String, nullable=True)
    rejection_reason = Column(String, nullable=True)

    # Effect tracking
    effect_authorized = Column(Boolean, default=False)
    effect_observed = Column(Boolean, default=False)
    effect_verified = Column(Boolean, default=False)

    application = relationship("ScholarshipApplication", back_populates="transactions")
    audit_events = relationship("AuditEvent", back_populates="transaction")
    authorization_lease = relationship("AuthorizationLease", back_populates="transaction", uselist=False)

    __table_args__ = (
        Index("ix_isg_transactions_idempotency", "idempotency_key"),
    )


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id = Column(String, primary_key=True)
    transaction_id = Column(String, ForeignKey("isg_transactions.id"), nullable=False)
    event_type = Column(String, nullable=False)
    stage = Column(String, nullable=False)
    result = Column(String, nullable=False)
    detail = Column(Text, nullable=True)
    payload_hash = Column(String, nullable=True)
    evidence = Column(JSON, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    sequence = Column(Integer, nullable=False)

    transaction = relationship("ISGTransaction", back_populates="audit_events")


class AuthorizationLease(Base):
    __tablename__ = "authorization_leases"

    id = Column(String, primary_key=True)
    transaction_id = Column(String, ForeignKey("isg_transactions.id"), nullable=False, unique=True)
    effect_id = Column(String, nullable=False)
    operation = Column(String, nullable=False)
    target = Column(String, nullable=False)
    purpose = Column(String, nullable=False)
    environment = Column(String, nullable=False)
    parameter_hash = Column(String, nullable=False)
    issued_at = Column(DateTime, server_default=func.now())
    expires_at = Column(DateTime, nullable=False)
    used = Column(Boolean, default=False)
    used_at = Column(DateTime, nullable=True)
    revoked = Column(Boolean, default=False)
    revoked_at = Column(DateTime, nullable=True)
    revocation_reason = Column(String, nullable=True)

    transaction = relationship("ISGTransaction", back_populates="authorization_lease")


class ConsentRecord(Base):
    __tablename__ = "consent_records"

    id = Column(String, primary_key=True)
    citizen_id = Column(String, nullable=False)
    application_id = Column(String, nullable=False)
    purpose = Column(String, nullable=False)
    granted_at = Column(DateTime, server_default=func.now())
    expires_at = Column(DateTime, nullable=True)
    revoked = Column(Boolean, default=False)
    revoked_at = Column(DateTime, nullable=True)
    revocation_reason = Column(String, nullable=True)


class PolicyRecord(Base):
    __tablename__ = "policy_records"

    id = Column(String, primary_key=True)
    policy_id = Column(String, nullable=False)
    version = Column(String, nullable=False)
    purpose = Column(String, nullable=False)
    allowed_data = Column(JSON, nullable=False)
    roles = Column(JSON, nullable=False)
    legal_basis = Column(String, nullable=False)
    consent_required = Column(Boolean, default=True)
    risk_level = Column(String, nullable=False)
    effective_from = Column(DateTime, nullable=False)
    effective_until = Column(DateTime, nullable=True)
    status = Column(String, default="ACTIVE")
    policy_hash = Column(String, nullable=False)


class ContractRecord(Base):
    __tablename__ = "contract_records"

    id = Column(String, primary_key=True)
    contract_id = Column(String, nullable=False)
    version = Column(String, nullable=False)
    source_system = Column(String, nullable=False)
    target_system = Column(String, nullable=False)
    purpose = Column(String, nullable=False)
    semantic_mapping = Column(JSON, nullable=False)
    preconditions = Column(JSON, nullable=False)
    postconditions = Column(JSON, nullable=False)
    assumptions = Column(JSON, nullable=False)
    compiler_version = Column(String, nullable=False)
    vocabulary_version = Column(String, nullable=False)
    status = Column(String, default="ACTIVE")
    contract_hash = Column(String, nullable=False)
    activated_at = Column(DateTime, nullable=False)


class EffectRecord(Base):
    __tablename__ = "effect_records"

    id = Column(String, primary_key=True)
    transaction_id = Column(String, ForeignKey("isg_transactions.id"), nullable=False)
    effect_id = Column(String, nullable=False, unique=True)
    operation = Column(String, nullable=False)
    target = Column(String, nullable=False)
    effect_class = Column(String, nullable=False)
    purpose = Column(String, nullable=False)
    environment = Column(String, nullable=False)
    parameter_hash = Column(String, nullable=False)
    validity_window_start = Column(DateTime, nullable=False)
    validity_window_end = Column(DateTime, nullable=False)
    reversibility = Column(String, nullable=False)
    status = Column(String, default="PENDING")
    observed_at = Column(DateTime, nullable=True)
    verified_at = Column(DateTime, nullable=True)
    external_reference = Column(String, nullable=True)
