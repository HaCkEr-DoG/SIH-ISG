# UNBOUND ISG — Interoperability Safety Gateway
**SIH 2026 · Problem Statement PS26129**

> Prototype simulation using synthetic data. Not a production government system.

## What This Is

ISG is a safety/control layer that sits between government systems with different schemas, identifiers, semantics, and policies. It determines whether information and requested effects can safely cross system boundaries.

**Prototype use case:** Maharashtra Scholarship Eligibility Verification — connecting Revenue, Education, and Identity systems that each speak a different schema.

## Quick Start

```bash
cd isg
docker compose up --build
```

- **Frontend:** http://localhost:3000  
- **Backend API:** http://localhost:8000  
- **API Docs:** http://localhost:8000/docs

## Demo Scenarios (all trigger real backend logic)

| Scenario | Applicant | What ISG demonstrates |
|---|---|---|
| ✓ Valid Application | Priya Sharma | All checks pass → ALLOW → SUCCESS |
| ⚡ Semantic Mismatch | Ravi Kumar | Monthly income ≠ annual FY → QUARANTINE |
| ⚡ Identity Mismatch | Ravi Kumar | Same name, conflicting DOB → QUARANTINE |
| ⚡ Consent Failure | Sunita Patil | Consent revoked before effect → QUARANTINE |
| ⏱ External Timeout | Vikram Rathod | Revenue timeout → UNKNOWN_RESULT |
| ↺ Recovery | Vikram Rathod | Idempotency check → safe retry → SUCCESS |
| ⛔ Replay | Priya Sharma | Duplicate key → REJECT (no duplicate effect) |

## Architecture

```
Citizen Portal
      ↓
ISG Safety Pipeline:
  AUTH → CONTRACT → STRUCTURE → DATA QUALITY → SEMANTICS → PROVENANCE
  → FRESHNESS → IDENTITY → POLICY → CONSENT → RISK → CAPABILITY
  → IDEMPOTENCY → EFFECT AUTH → LIVE RECHECK → BOUNDED EFFECT
  → OBSERVATION → RECOVERY → AUDIT → TERMINAL STATE
      ↓
┌──────────────────┐
│  Revenue System  │  v2.7 · family_id (FAM-xxxx)
│  Education Sys.  │  v3.1 · student_id (EDU-xxxx)
│  Identity Sys.   │  v1.5 · identity_ref (ID-xxxx)
└──────────────────┘
      ↓
Decision Capsule + Audit Trail
```

## Running Tests

```bash
cd backend
python -m pytest tests/test_safety_invariants.py -v
```

All 16 safety invariant tests must pass. These prove:
- Unknown evidence cannot become ALLOW
- AI cannot authorize
- Terminal transactions cannot execute
- Expired/revoked leases are blocked
- Revoked consent blocks effects
- DOB conflicts quarantine identity
- Monthly income quarantines (semantic check)
- Replay is blocked

## Key Safety Properties Proven by Tests

1. Missing identity → BLOCK (never silent pass)
2. Missing consent → BLOCK
3. Missing policy → BLOCK
4. AI never authorizes (`ai_was_final_authority` always False)
5. Terminal state → no transitions
6. Expired lease → BLOCK
7. Revoked consent → BLOCK
8. Identity DOB collision → QUARANTINE (even if one matches)
9. Monthly income vs FY annual → QUARANTINE
10. Duplicate idempotency key → REJECT

## What Is Simulated vs Real

| Component | Status |
|---|---|
| ISG Safety Pipeline | Real backend logic |
| Semantic validation | Real deterministic checks |
| Identity pipeline | Real calibrated matching |
| Policy/consent engine | Real DB-backed state |
| Authorization leases | Real single-use, time-bounded |
| Transaction state machine | Real enforced terminal states |
| Audit trail | Real tamper-evident records |
| Revenue System | **Simulated** (synthetic data) |
| Education System | **Simulated** (synthetic data) |
| Identity System | **Simulated** (synthetic data) |
| Government API access | **NOT claimed** |
| Production certification | **NOT claimed** |
| Universal rollback | **NOT claimed** |

## Disclaimer

This prototype simulates government systems using entirely synthetic data. It does not connect to any real Maharashtra government system, does not use any real citizen data, and does not claim production readiness, official certification, or legal authority.
