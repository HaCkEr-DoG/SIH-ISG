"""
ISG Safety Kernel — The authoritative individual safety decision point.
Result: ALLOW | REJECT | QUARANTINE | DEFER.
No other component may independently authorize a consequential effect.
AI is never the final authority.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum
from core.semantic_ir import SemanticCheckReport, SemanticCheckResult
from core.identity_pipeline import IdentityDecisionRecord, IdentityDecision
from core.consent_policy import ConsentCheckReport, PolicyCheckReport, ConsentCheckResult, PolicyCheckResult
from core.authorization import LeaseValidationResult


class KernelDecision(str, Enum):
    ALLOW = "ALLOW"
    REJECT = "REJECT"
    QUARANTINE = "QUARANTINE"
    DEFER = "DEFER"


@dataclass
class SafetyKernelInput:
    """All inputs to the Safety Kernel decision."""
    transaction_id: str
    # Semantic checks
    semantic_reports: list[SemanticCheckReport] = field(default_factory=list)
    # Identity decision
    identity_decision: Optional[IdentityDecisionRecord] = None
    # Consent
    consent_check: Optional[ConsentCheckReport] = None
    # Policy
    policy_check: Optional[PolicyCheckReport] = None
    # Freshness
    evidence_fresh: bool = True
    freshness_detail: str = ""
    # Provenance
    provenance_valid: bool = True
    provenance_detail: str = ""
    # Data quality
    data_quality_pass: bool = True
    data_quality_detail: str = ""
    # Participant capability
    participant_capability_adequate: bool = True
    participant_detail: str = ""
    # Lease validation (for effect execution)
    lease_validation: Optional[LeaseValidationResult] = None
    # Extra flags
    idempotency_duplicate: bool = False
    deadline_exceeded: bool = False
    external_call_budget_exceeded: bool = False


@dataclass
class SafetyKernelResult:
    """Authoritative safety decision output."""
    decision: KernelDecision
    primary_reason: str
    blocking_checks: list[str]
    passed_checks: list[str]
    explanation: str
    technical_code: str
    ai_was_final_authority: bool = False   # Always False — invariant

    def to_dict(self) -> dict:
        return {
            "decision": self.decision.value,
            "primary_reason": self.primary_reason,
            "blocking_checks": self.blocking_checks,
            "passed_checks": self.passed_checks,
            "explanation": self.explanation,
            "technical_code": self.technical_code,
            "ai_was_final_authority": self.ai_was_final_authority,
        }


class SafetyKernel:
    """
    Deterministic safety decision engine.
    Evaluates all check results and produces an authoritative decision.

    Invariants (from INVARIANT_REGISTRY):
    - UNKNOWN mandatory evidence cannot become ALLOW
    - AI cannot authorize
    - Terminal transaction cannot execute
    - Expired lease cannot execute
    - Revoked consent cannot authorize
    """

    def decide(self, inp: SafetyKernelInput) -> SafetyKernelResult:
        """
        Evaluate all safety checks and produce an authoritative decision.
        Uses priority ordering: hard blocks first.
        """
        blocking = []
        passed = []

        # --- Hard blocks (automatic QUARANTINE/REJECT) ---

        # Deadline exceeded
        if inp.deadline_exceeded:
            return SafetyKernelResult(
                decision=KernelDecision.REJECT,
                primary_reason="Transaction deadline exceeded.",
                blocking_checks=["DEADLINE_EXCEEDED"],
                passed_checks=passed,
                explanation="Transaction has exceeded its authorized time window.",
                technical_code="SK-001-DEADLINE-EXCEEDED",
            )

        # External call budget
        if inp.external_call_budget_exceeded:
            return SafetyKernelResult(
                decision=KernelDecision.REJECT,
                primary_reason="External call budget exceeded.",
                blocking_checks=["EXTERNAL_CALL_BUDGET"],
                passed_checks=passed,
                explanation="Transaction has exceeded the authorized number of external system calls.",
                technical_code="SK-002-BUDGET-EXCEEDED",
            )

        # Idempotency duplicate
        if inp.idempotency_duplicate:
            return SafetyKernelResult(
                decision=KernelDecision.REJECT,
                primary_reason="Duplicate/replay request detected.",
                blocking_checks=["IDEMPOTENCY_DUPLICATE"],
                passed_checks=passed,
                explanation=(
                    "A transaction with this idempotency key has already been processed. "
                    "Replay is not authorized."
                ),
                technical_code="SK-003-REPLAY-DETECTED",
            )

        # Provenance
        if not inp.provenance_valid:
            blocking.append(f"PROVENANCE_INVALID: {inp.provenance_detail}")
        else:
            passed.append("PROVENANCE_VALID")

        # Data quality
        if not inp.data_quality_pass:
            blocking.append(f"DATA_QUALITY_FAIL: {inp.data_quality_detail}")
        else:
            passed.append("DATA_QUALITY_PASS")

        # Semantic checks
        blocking_semantic = [r for r in inp.semantic_reports if r.blocking]
        if blocking_semantic:
            for r in blocking_semantic:
                blocking.append(f"SEMANTIC_{r.result.value}: {r.field_name}")
        else:
            passed.append("SEMANTIC_VALIDATION_PASS")

        # Identity decision
        if inp.identity_decision is None:
            blocking.append("IDENTITY_MISSING: No identity evaluation performed")
        elif inp.identity_decision.decision == IdentityDecision.QUARANTINE:
            blocking.append(f"IDENTITY_QUARANTINE: {inp.identity_decision.technical_code}")
        elif inp.identity_decision.decision == IdentityDecision.REJECT:
            blocking.append(f"IDENTITY_REJECT: {inp.identity_decision.technical_code}")
        else:
            passed.append(f"IDENTITY_ACCEPTED: {inp.identity_decision.matched_ref}")

        # Policy
        if inp.policy_check is None:
            blocking.append("POLICY_MISSING: No policy check performed")
        elif inp.policy_check.blocking:
            blocking.append(f"POLICY_{inp.policy_check.result.value}")
        else:
            passed.append(f"POLICY_PASS: {inp.policy_check.policy_id} v{inp.policy_check.policy_version}")

        # Consent (initial check)
        if inp.consent_check is None:
            blocking.append("CONSENT_MISSING: No consent check performed")
        elif not inp.consent_check.is_valid():
            blocking.append(f"CONSENT_{inp.consent_check.result.value}")
        else:
            passed.append("CONSENT_VALID")

        # Evidence freshness
        if not inp.evidence_fresh:
            blocking.append(f"FRESHNESS_FAIL: {inp.freshness_detail}")
        else:
            passed.append("FRESHNESS_PASS")

        # Participant capability
        if not inp.participant_capability_adequate:
            blocking.append(f"PARTICIPANT_CAPABILITY: {inp.participant_detail}")
        else:
            passed.append("PARTICIPANT_CAPABILITY_ADEQUATE")

        # Lease validation (for effect phase only)
        if inp.lease_validation is not None:
            if inp.lease_validation == LeaseValidationResult.VALID:
                passed.append("LEASE_VALID")
            elif inp.lease_validation == LeaseValidationResult.EXPIRED:
                blocking.append("LEASE_EXPIRED: Authorization lease has expired")
            elif inp.lease_validation == LeaseValidationResult.ALREADY_USED:
                blocking.append("LEASE_USED: Authorization lease already consumed")
            elif inp.lease_validation == LeaseValidationResult.REVOKED:
                blocking.append("LEASE_REVOKED: Authorization lease revoked (consent or policy change)")
            else:
                blocking.append(f"LEASE_INVALID: {inp.lease_validation.value}")

        # Final decision
        if not blocking:
            primary = "All safety checks passed."
            decision = KernelDecision.ALLOW
            code = "SK-OK-ALLOW"
            explanation = (
                "All ISG safety checks have passed deterministically. "
                "Transaction is authorized to proceed to effect execution."
            )
        else:
            # Choose quarantine vs reject based on nature of block
            quarantine_triggers = {"SEMANTIC_", "IDENTITY_", "CONSENT_REVOKED", "CONSENT_EXPIRED"}
            reject_triggers = {"LEASE_", "IDEMPOTENCY_", "DEADLINE_", "POLICY_ROLE"}

            is_quarantine = any(
                any(b.startswith(t) for t in quarantine_triggers)
                for b in blocking
            )
            decision = KernelDecision.QUARANTINE if is_quarantine else KernelDecision.REJECT
            primary = blocking[0]
            code = f"SK-BLOCK-{'QUARANTINE' if is_quarantine else 'REJECT'}"
            explanation = (
                f"Safety Kernel {'QUARANTINED' if is_quarantine else 'REJECTED'} this transaction. "
                f"Blocking checks: {'; '.join(blocking)}. "
                f"Passed checks: {'; '.join(passed) if passed else 'None'}."
            )

        return SafetyKernelResult(
            decision=decision,
            primary_reason=primary,
            blocking_checks=blocking,
            passed_checks=passed,
            explanation=explanation,
            technical_code=code,
            ai_was_final_authority=False,  # INVARIANT: always False
        )
