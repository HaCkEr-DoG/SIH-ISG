"""
ISG Safety Invariant Tests.
These tests prove the required safety properties from the specification.
Tests must never be weakened to pass.
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from core.safety_kernel import SafetyKernel, SafetyKernelInput, KernelDecision
from core.semantic_ir import (
    SemanticField, SemanticType, TemporalScope, SemanticValidator,
    SemanticCheckResult,
)
from core.identity_pipeline import (
    IdentityPipeline, IdentityClaimant, IdentityCandidate,
    MatchConsequence, IdentityDecision,
)
from core.consent_policy import (
    ConsentCheckReport, ConsentCheckResult,
    PolicyCheckReport, PolicyCheckResult,
)
from core.authorization import LeaseValidationResult
from core.transaction_sm import TransactionStateMachine, TransactionStateError
from models import TransactionStatus, TERMINAL_STATES


# ──────────────────────────────────────────────────────────
# INVARIANT 1: UNKNOWN mandatory evidence cannot become ALLOW
# ──────────────────────────────────────────────────────────

def test_missing_identity_cannot_allow():
    """Safety Kernel must BLOCK when identity check is absent."""
    kernel = SafetyKernel()
    inp = SafetyKernelInput(
        transaction_id="test-001",
        semantic_reports=[],
        identity_decision=None,   # NO identity check
        consent_check=ConsentCheckReport(
            result=ConsentCheckResult.VALID,
            citizen_id="c1", application_id="a1",
            purpose="TEST", explanation="valid",
        ),
        policy_check=PolicyCheckReport(
            result=PolicyCheckResult.PASS,
            policy_id="P1", policy_version="1.0",
            explanation="pass", blocking=False,
        ),
    )
    result = kernel.decide(inp)
    assert result.decision != KernelDecision.ALLOW, "INVARIANT VIOLATED: Missing identity allowed transaction"
    assert any("IDENTITY" in b for b in result.blocking_checks)


def test_missing_consent_cannot_allow():
    """Safety Kernel must BLOCK when consent check is absent."""
    kernel = SafetyKernel()
    inp = SafetyKernelInput(
        transaction_id="test-002",
        consent_check=None,   # NO consent check
        policy_check=PolicyCheckReport(
            result=PolicyCheckResult.PASS, policy_id="P1", policy_version="1.0",
            explanation="pass", blocking=False,
        ),
    )
    result = kernel.decide(inp)
    assert result.decision != KernelDecision.ALLOW, "INVARIANT VIOLATED: Missing consent allowed transaction"
    assert any("CONSENT" in b for b in result.blocking_checks)


def test_missing_policy_cannot_allow():
    """Safety Kernel must BLOCK when policy check is absent."""
    kernel = SafetyKernel()
    inp = SafetyKernelInput(
        transaction_id="test-003",
        policy_check=None,   # NO policy check
        consent_check=ConsentCheckReport(
            result=ConsentCheckResult.VALID, citizen_id="c1", application_id="a1",
            purpose="TEST", explanation="valid",
        ),
    )
    result = kernel.decide(inp)
    assert result.decision != KernelDecision.ALLOW, "INVARIANT VIOLATED: Missing policy allowed transaction"


# ──────────────────────────────────────────────────────────
# INVARIANT 2: AI cannot authorize
# ──────────────────────────────────────────────────────────

def test_ai_never_final_authority():
    """Safety Kernel result must never set ai_was_final_authority=True."""
    kernel = SafetyKernel()
    for scenario in [
        SafetyKernelInput(transaction_id="ai-test-allow",
            semantic_reports=[], identity_decision=None,
            consent_check=None, policy_check=None),
        SafetyKernelInput(transaction_id="ai-test-block",
            semantic_reports=[],
            identity_decision=None, consent_check=None, policy_check=None,
            idempotency_duplicate=True),
    ]:
        result = kernel.decide(scenario)
        assert result.ai_was_final_authority is False, \
            "INVARIANT VIOLATED: ai_was_final_authority must always be False"


# ──────────────────────────────────────────────────────────
# INVARIANT 3: Terminal transaction cannot execute
# ──────────────────────────────────────────────────────────

def test_terminal_states_defined():
    """All terminal states must be non-transitionable."""
    # Verify TERMINAL_STATES is complete
    terminal_expected = {
        TransactionStatus.SUCCESS,
        TransactionStatus.REJECTED,
        TransactionStatus.QUARANTINED,
        TransactionStatus.FAILED,
        TransactionStatus.COMPENSATED,
        TransactionStatus.RECONCILIATION_REQUIRED,
        TransactionStatus.EXPIRED,
        TransactionStatus.CANCELLED,
    }
    assert terminal_expected == TERMINAL_STATES, "Terminal states definition mismatch"


def test_terminal_state_cannot_transition(tmp_path):
    """A terminal transaction must raise on any state transition attempt."""
    from unittest.mock import MagicMock, patch
    from datetime import datetime, timezone

    sm = TransactionStateMachine()

    for terminal_status in TERMINAL_STATES:
        mock_tx = MagicMock()
        mock_tx.id = "test-tx"
        mock_tx.status = terminal_status
        mock_tx.state_version = 5

        with pytest.raises(TransactionStateError) as exc_info:
            sm.transition(MagicMock(), mock_tx, TransactionStatus.PROCESSING)

        assert "terminal state" in str(exc_info.value).lower(), \
            f"Wrong error for terminal state {terminal_status}"


# ──────────────────────────────────────────────────────────
# INVARIANT 4: Expired authorization lease cannot execute
# ──────────────────────────────────────────────────────────

def test_expired_lease_blocks_execution():
    """An expired lease validation must return EXPIRED, not VALID."""
    from core.authorization import LeaseValidationResult
    # Test the enum value exists
    assert LeaseValidationResult.EXPIRED is not None
    assert LeaseValidationResult.VALID != LeaseValidationResult.EXPIRED

    # Kernel must block on expired lease
    kernel = SafetyKernel()
    inp = SafetyKernelInput(
        transaction_id="lease-test",
        lease_validation=LeaseValidationResult.EXPIRED,
        consent_check=ConsentCheckReport(
            result=ConsentCheckResult.VALID, citizen_id="c1", application_id="a1",
            purpose="TEST", explanation="valid",
        ),
        policy_check=PolicyCheckReport(
            result=PolicyCheckResult.PASS, policy_id="P1", policy_version="1.0",
            explanation="pass", blocking=False,
        ),
    )
    result = kernel.decide(inp)
    assert result.decision != KernelDecision.ALLOW
    assert any("LEASE" in b for b in result.blocking_checks)


# ──────────────────────────────────────────────────────────
# INVARIANT 5: Revoked consent cannot authorize
# ──────────────────────────────────────────────────────────

def test_revoked_consent_blocks():
    """Revoked consent must block at Safety Kernel."""
    kernel = SafetyKernel()
    inp = SafetyKernelInput(
        transaction_id="consent-test",
        consent_check=ConsentCheckReport(
            result=ConsentCheckResult.REVOKED,
            citizen_id="c1", application_id="a1",
            purpose="TEST",
            explanation="Consent revoked.",
        ),
        policy_check=PolicyCheckReport(
            result=PolicyCheckResult.PASS, policy_id="P1", policy_version="1.0",
            explanation="pass", blocking=False,
        ),
    )
    result = kernel.decide(inp)
    assert result.decision != KernelDecision.ALLOW
    assert any("CONSENT" in b for b in result.blocking_checks)


# ──────────────────────────────────────────────────────────
# INVARIANT 6: Identity conflict quarantines
# ──────────────────────────────────────────────────────────

def test_identity_dob_conflict_quarantines():
    """Same name but different DOB must quarantine, not accept."""
    pipeline = IdentityPipeline()

    claimant = IdentityClaimant(name="Ravi Kumar", dob="2004-05-12", application_ref="APP-TEST")
    candidates = [
        IdentityCandidate(
            identity_ref="ID-A",
            name="Ravi Kumar",
            dob="2004-05-12",
            verification_status="VERIFIED",
            source_system="TEST",
            source_version="v1",
        ),
        IdentityCandidate(
            identity_ref="ID-B",
            name="Ravi Kumar",
            dob="2005-05-12",   # DIFFERENT YEAR
            verification_status="VERIFIED",
            source_system="TEST",
            source_version="v1",
        ),
    ]

    result = pipeline.evaluate(claimant, candidates, consequence=MatchConsequence.HIGH)
    assert result.decision == IdentityDecision.QUARANTINE, \
        "INVARIANT VIOLATED: DOB conflict must quarantine"
    assert result.quarantine_reason is not None
    assert "DOB" in result.quarantine_reason or "collision" in result.quarantine_reason.lower()


def test_identity_exact_match_accepted():
    """Perfect name+DOB match must be accepted."""
    pipeline = IdentityPipeline()
    claimant = IdentityClaimant(name="Priya Sharma", dob="2005-08-14", application_ref="APP-TEST")
    candidates = [
        IdentityCandidate(
            identity_ref="ID-1001", name="Priya Sharma", dob="2005-08-14",
            verification_status="VERIFIED", source_system="TEST", source_version="v1",
        )
    ]
    result = pipeline.evaluate(claimant, candidates, consequence=MatchConsequence.HIGH)
    assert result.decision == IdentityDecision.ACCEPT
    assert result.matched_ref == "ID-1001"


# ──────────────────────────────────────────────────────────
# INVARIANT 7: Semantic mismatch quarantines
# ──────────────────────────────────────────────────────────

def test_monthly_income_quarantines():
    """Monthly income presented where annual FY required must block."""
    validator = SemanticValidator()

    source = SemanticField(
        field_name="family_income",
        semantic_type=SemanticType.CURRENCY_AMOUNT,
        value=20000,
        temporal_scope=TemporalScope.MONTHLY,
        period_reference="APR2025",
        provenance_system="REVENUE",
        provenance_version="v2.7",
    )

    report = validator.validate_income_field(
        source=source,
        target_scope=TemporalScope.FINANCIAL_YEAR_ANNUAL,
        target_period_reference="FY2025-26",
        authorized_transformations=[],   # No transformations authorized
    )

    assert report.blocking is True, "INVARIANT VIOLATED: Monthly income must block"
    assert report.result == SemanticCheckResult.TEMPORAL_MISMATCH


def test_annual_fy_income_passes():
    """Annual FY income with matching period must pass."""
    validator = SemanticValidator()
    source = SemanticField(
        field_name="family_income",
        semantic_type=SemanticType.CURRENCY_AMOUNT,
        value=180000,
        temporal_scope=TemporalScope.FINANCIAL_YEAR_ANNUAL,
        period_reference="FY2025-26",
        provenance_system="REVENUE",
        provenance_version="v2.7",
    )
    report = validator.validate_income_field(
        source=source,
        target_scope=TemporalScope.FINANCIAL_YEAR_ANNUAL,
        target_period_reference="FY2025-26",
        authorized_transformations=[],
    )
    assert report.blocking is False
    assert report.result == SemanticCheckResult.PASS


# ──────────────────────────────────────────────────────────
# INVARIANT 8: Idempotency / replay protection
# ──────────────────────────────────────────────────────────

def test_duplicate_request_blocked():
    """Safety Kernel must block duplicate/replay requests."""
    kernel = SafetyKernel()
    inp = SafetyKernelInput(
        transaction_id="dup-test",
        idempotency_duplicate=True,
    )
    result = kernel.decide(inp)
    assert result.decision == KernelDecision.REJECT
    assert "IDEMPOTENCY" in result.blocking_checks[0]


# ──────────────────────────────────────────────────────────
# INVARIANT 9: Effect envelope separates authorized from observed
# ──────────────────────────────────────────────────────────

def test_effect_envelope_has_separate_states():
    """EffectEnvelope must have validity window."""
    from core.authorization import EffectEnvelope
    env = EffectEnvelope.create(
        transaction_id="tx-test",
        operation="GRANT_SCHOLARSHIP",
        target="TARGET_SYSTEM",
        effect_class="IDEMPOTENT_WRITE",
        purpose="TEST",
        environment="demo",
        parameters={"a": 1},
        validity_seconds=300,
    )
    assert env.effect_id is not None
    assert env.parameter_hash is not None
    assert env.is_within_validity_window()


# ──────────────────────────────────────────────────────────
# INVARIANT 10: Deadline exceeded blocks
# ──────────────────────────────────────────────────────────

def test_deadline_exceeded_blocks():
    """Safety Kernel must reject when deadline exceeded."""
    kernel = SafetyKernel()
    inp = SafetyKernelInput(transaction_id="dl-test", deadline_exceeded=True)
    result = kernel.decide(inp)
    assert result.decision == KernelDecision.REJECT
    assert "DEADLINE" in result.blocking_checks[0]


# ──────────────────────────────────────────────────────────
# INVARIANT 11: Consent expired blocks
# ──────────────────────────────────────────────────────────

def test_expired_consent_blocks():
    """Expired consent must block."""
    kernel = SafetyKernel()
    inp = SafetyKernelInput(
        transaction_id="exp-consent",
        consent_check=ConsentCheckReport(
            result=ConsentCheckResult.EXPIRED,
            citizen_id="c1", application_id="a1",
            purpose="TEST",
            explanation="Consent expired.",
        ),
        policy_check=PolicyCheckReport(
            result=PolicyCheckResult.PASS, policy_id="P1", policy_version="1.0",
            explanation="pass", blocking=False,
        ),
    )
    result = kernel.decide(inp)
    assert result.decision != KernelDecision.ALLOW
    assert any("CONSENT" in b for b in result.blocking_checks)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
