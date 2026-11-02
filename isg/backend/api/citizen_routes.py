"""
ISG Citizen Verification API — Verify Once, Apply Everywhere.

With one consent tap this endpoint pulls verified income, identity and
residency records straight from source agencies, runs BISF safety checks,
and returns a cross-program eligibility profile.

No document uploads. Source-pulled data cannot be forged.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from auth import verify_token
from models import CitizenProfile, ScholarshipApplication, ConsentRecord
from simulators.revenue_simulator import fetch_income_record, RevenueFetchResult
from simulators.identity_simulator import fetch_identity_candidates, IdentityFetchResult
from simulators.residency_simulator import fetch_residency_record, ResidencyFetchResult

router = APIRouter(
    prefix="/api/citizen",
    tags=["citizen"],
    dependencies=[Depends(verify_token)],
)

# ── Program definitions ───────────────────────────────────────────────────────

PROGRAMS = [
    {
        "id": "NSP-001",
        "name": "National Scholarship Portal",
        "dept": "Education Dept / UGC",
        "income_limit": 250000,
        "description": "Merit-cum-means scholarship for undergraduate and postgraduate students.",
        "legal_basis": "NSP_Guidelines_2024",
        "annual_benefit_inr": 75000,
    },
    {
        "id": "PMJAY-001",
        "name": "PM Jan Arogya Yojana",
        "dept": "Health & Family Welfare",
        "income_limit": 500000,
        "description": "Health cover of ₹5 lakh per family per year for secondary and tertiary care.",
        "legal_basis": "PMJAY_Act_2018",
        "annual_benefit_inr": 500000,
    },
    {
        "id": "NFSA-001",
        "name": "National Food Security (Ration Card)",
        "dept": "Civil Supplies / PDS",
        "income_limit": 150000,
        "description": "Subsidised food grains under the National Food Security Act.",
        "legal_basis": "NFSA_2013",
        "annual_benefit_inr": 12000,
    },
    {
        "id": "PMAY-001",
        "name": "PM Awaas Yojana (Housing Subsidy)",
        "dept": "Housing & Urban Development",
        "income_limit": 300000,
        "description": "Interest subsidy on home loans for economically weaker sections.",
        "legal_basis": "PMAY_Urban_Guidelines_2022",
        "annual_benefit_inr": 267000,
    },
    {
        "id": "PMKISAN-001",
        "name": "PM-KISAN (Farmer Income Support)",
        "dept": "Ministry of Agriculture",
        "income_limit": 200000,
        "description": "Direct income support of ₹6,000/year to eligible farmer families.",
        "legal_basis": "PMKISAN_Guidelines_2019",
        "annual_benefit_inr": 6000,
    },
    {
        "id": "AAY-001",
        "name": "Antyodaya Anna Yojana",
        "dept": "Civil Supplies / PDS",
        "income_limit": 80000,
        "description": "Highly subsidised food grains (35 kg/month) for the poorest families.",
        "legal_basis": "NFSA_2013_AAY",
        "annual_benefit_inr": 18000,
    },
]

# ── Fraud intelligence heuristics ────────────────────────────────────────────

def _run_fraud_heuristics(profile: "CitizenProfile") -> dict:
    signals = []
    score = 0

    # H1: Income is in hold state (semantic or identity issue)
    if profile.verification_status == "HOLD":
        signals.append({
            "code": "PROFILE_ON_HOLD",
            "severity": "HIGH",
            "weight": 40,
            "detail": profile.hold_reason or "Profile flagged for human review.",
        })
        score += 40

    # H2: Income suspiciously close to a program threshold
    if profile.income_annual_inr and profile.verification_status == "VERIFIED":
        for prog in PROGRAMS:
            ratio = profile.income_annual_inr / prog["income_limit"]
            if 0.92 <= ratio <= 1.0:
                signals.append({
                    "code": "INCOME_NEAR_THRESHOLD",
                    "severity": "MEDIUM",
                    "weight": 20,
                    "detail": (
                        f"Income ₹{profile.income_annual_inr:,} is within 8% of "
                        f"{prog['name']} limit ₹{prog['income_limit']:,}."
                    ),
                })
                score += 20
                break

    # H3: Missing residency — could indicate ghost beneficiary
    if not profile.residency_district:
        signals.append({
            "code": "RESIDENCY_UNVERIFIED",
            "severity": "MEDIUM",
            "weight": 15,
            "detail": "No verified district on record — address source unavailable.",
        })
        score += 15

    # H4: Missing identity evidence
    if not profile.identity_evidence_type:
        signals.append({
            "code": "IDENTITY_UNVERIFIED",
            "severity": "HIGH",
            "weight": 30,
            "detail": "Identity evidence not confirmed — Aadhaar/registry check failed.",
        })
        score += 30

    # H5: Income in extreme low range (possible under-declaration)
    if profile.income_annual_inr is not None and profile.income_annual_inr < 10000:
        signals.append({
            "code": "SUSPICIOUSLY_LOW_INCOME",
            "severity": "LOW",
            "weight": 10,
            "detail": f"Declared annual income ₹{profile.income_annual_inr:,} is unusually low.",
        })
        score += 10

    score = min(score, 100)
    if score >= 60:
        risk_level = "HIGH"
    elif score >= 25:
        risk_level = "MEDIUM"
    else:
        risk_level = "LOW"

    return {
        "fraud_risk_score": score,
        "risk_level": risk_level,
        "signals": signals,
        "signal_count": len(signals),
    }


def _check_eligibility(income_annual: Optional[int]) -> list[dict]:
    if income_annual is None:
        return [
            {**p, "eligible": False, "reason": "Income could not be verified — on hold."}
            for p in PROGRAMS
        ]
    return [
        {
            **p,
            "eligible": income_annual <= p["income_limit"],
            "reason": (
                f"Annual income ₹{income_annual:,} is within the ₹{p['income_limit']:,} limit."
                if income_annual <= p["income_limit"]
                else f"Annual income ₹{income_annual:,} exceeds the ₹{p['income_limit']:,} limit."
            ),
        }
        for p in PROGRAMS
    ]


# ── Request / Response models ─────────────────────────────────────────────────

class VerifyRequest(BaseModel):
    citizen_id: str
    family_id: str
    name: str
    dob: str


class AgentEnrollRequest(BaseModel):
    citizen_id: str
    program_id: str
    agent_id: str = "AI_AGENT_001"


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/citizens")
async def list_citizens(db: Session = Depends(get_db)):
    """Return the list of pre-seeded citizens for the demo picker."""
    apps = db.query(ScholarshipApplication).all()
    seen = {}
    for a in apps:
        if a.applicant_id_ref not in seen:
            seen[a.applicant_id_ref] = {
                "citizen_id": a.applicant_id_ref,
                "name": a.applicant_name,
                "dob": a.applicant_dob,
                "family_id": a.family_id,
                "purpose": a.purpose,
            }
    return {"citizens": list(seen.values())}


@router.post("/verify")
async def verify_citizen(body: VerifyRequest, db: Session = Depends(get_db)):
    """
    Pull verified income, identity and residency from source agencies.
    Runs BISF safety checks. Stores a CitizenProfile.
    Returns cross-program eligibility — no document uploads needed.
    """
    now = datetime.now(timezone.utc)

    # Fetch from all three source agencies in parallel
    income_resp, identity_resp, residency_resp = await asyncio.gather(
        fetch_income_record(body.family_id),
        fetch_identity_candidates(body.citizen_id),
        fetch_residency_record(body.citizen_id),
    )

    checks = []
    income_annual: Optional[int] = None
    income_hold: Optional[str] = None
    identity_evidence: Optional[str] = None
    residency_district: Optional[str] = None
    residency_address: Optional[str] = None
    overall_status = "VERIFIED"
    hold_reason: Optional[str] = None

    # ── Income check ──────────────────────────────────────────────────────────
    if income_resp.result == RevenueFetchResult.FOUND:
        rec = income_resp.data
        if rec["income_period"] != "ANNUAL":
            income_hold = (
                f"Source reports income as {rec['income_period']} (₹{rec['income_value']:,}). "
                f"Annual figure required — cannot compare to program threshold without authorised conversion."
            )
            overall_status = "HOLD"
            hold_reason = income_hold
            checks.append({
                "source": income_resp.system_name,
                "field": "income",
                "status": "HOLD",
                "detail": income_hold,
                "raw": {"value": rec["income_value"], "period": rec["income_period"]},
            })
        else:
            income_annual = rec["income_value"]
            checks.append({
                "source": income_resp.system_name,
                "field": "income",
                "status": "VERIFIED",
                "detail": f"Annual income ₹{income_annual:,} ({rec['period_reference']}) — ITR/assessment verified.",
                "raw": {"value": income_annual, "period": "ANNUAL", "ref": rec["period_reference"]},
            })
    elif income_resp.result == RevenueFetchResult.TIMEOUT:
        overall_status = "HOLD"
        hold_reason = "Revenue system timed out — income unverified."
        checks.append({
            "source": "REVENUE_DEPT_MH",
            "field": "income",
            "status": "TIMEOUT",
            "detail": income_resp.error,
        })
    else:
        checks.append({
            "source": "REVENUE_DEPT_MH",
            "field": "income",
            "status": "NOT_FOUND",
            "detail": income_resp.error,
        })

    # ── Identity check ────────────────────────────────────────────────────────
    if identity_resp.result == IdentityFetchResult.FOUND and identity_resp.candidates:
        cand = identity_resp.candidates[0]
        name_match = cand["name"].lower() == body.name.lower()
        dob_match = cand["dob"] == body.dob
        if name_match and dob_match:
            identity_evidence = cand["evidence_type"]
            checks.append({
                "source": identity_resp.system_name,
                "field": "identity",
                "status": "VERIFIED",
                "detail": f"Name and date of birth confirmed. Evidence: {cand['evidence_type']}.",
                "raw": {"evidence_type": cand["evidence_type"], "provider": cand["identity_provider"]},
            })
        else:
            if overall_status != "HOLD":
                overall_status = "HOLD"
            hold_reason = hold_reason or "Identity mismatch between claimed and registry record."
            checks.append({
                "source": identity_resp.system_name,
                "field": "identity",
                "status": "MISMATCH",
                "detail": f"Name match: {name_match}, DOB match: {dob_match}.",
            })
    elif identity_resp.result == IdentityFetchResult.MULTIPLE_CANDIDATES:
        if overall_status != "HOLD":
            overall_status = "HOLD"
        hold_reason = hold_reason or "Multiple identity candidates — DOB conflict. Human review required."
        checks.append({
            "source": identity_resp.system_name,
            "field": "identity",
            "status": "HOLD",
            "detail": f"{len(identity_resp.candidates)} candidates with the same name but different DOBs.",
        })
    else:
        checks.append({
            "source": "IDENTITY_SYSTEM_MH",
            "field": "identity",
            "status": "NOT_FOUND",
            "detail": identity_resp.error,
        })

    # ── Residency check ───────────────────────────────────────────────────────
    if residency_resp.result == ResidencyFetchResult.FOUND:
        rec = residency_resp.data
        residency_district = rec["district"]
        residency_address = rec["address"]
        checks.append({
            "source": residency_resp.system_name,
            "field": "residency",
            "status": "VERIFIED",
            "detail": f"{rec['address']}, {rec['district']}, {rec['state']}.",
            "raw": {"district": rec["district"], "pin": rec["pin"], "since": rec["residency_since"]},
        })
    else:
        checks.append({
            "source": "ADDRESS_REGISTRY_MH",
            "field": "residency",
            "status": "NOT_FOUND",
            "detail": residency_resp.error,
        })

    # ── Eligibility ───────────────────────────────────────────────────────────
    programs_eligible = _check_eligibility(income_annual if overall_status == "VERIFIED" else None)

    # ── Store / update profile ────────────────────────────────────────────────
    profile_data = {
        "citizen_id": body.citizen_id,
        "name": body.name,
        "income_annual_inr": income_annual,
        "residency_district": residency_district,
        "verification_status": overall_status,
    }
    profile_hash = hashlib.sha256(
        json.dumps(profile_data, sort_keys=True, default=str).encode()
    ).hexdigest()

    existing = db.query(CitizenProfile).filter_by(citizen_id=body.citizen_id).first()
    if existing:
        existing.name = body.name
        existing.dob = body.dob
        existing.income_annual_inr = income_annual
        existing.income_source_system = income_resp.system_name if income_resp.result == RevenueFetchResult.FOUND else None
        existing.income_verified_at = now if income_annual else None
        existing.income_hold_reason = income_hold
        existing.identity_evidence_type = identity_evidence
        existing.identity_source_system = identity_resp.system_name if identity_resp.result in (IdentityFetchResult.FOUND, IdentityFetchResult.MULTIPLE_CANDIDATES) else None
        existing.identity_verified_at = now if identity_evidence else None
        existing.residency_district = residency_district
        existing.residency_address = residency_address
        existing.residency_source_system = residency_resp.system_name if residency_resp.result == ResidencyFetchResult.FOUND else None
        existing.residency_verified_at = now if residency_district else None
        existing.programs_eligible = programs_eligible
        existing.profile_hash = profile_hash
        existing.verification_status = overall_status
        existing.hold_reason = hold_reason
        existing.expires_at = now + timedelta(days=180)
        profile = existing
    else:
        profile = CitizenProfile(
            id=str(uuid.uuid4()),
            citizen_id=body.citizen_id,
            name=body.name,
            dob=body.dob,
            income_annual_inr=income_annual,
            income_source_system=income_resp.system_name if income_resp.result == RevenueFetchResult.FOUND else None,
            income_verified_at=now if income_annual else None,
            income_hold_reason=income_hold,
            identity_evidence_type=identity_evidence,
            identity_source_system=identity_resp.system_name if identity_resp.result in (IdentityFetchResult.FOUND, IdentityFetchResult.MULTIPLE_CANDIDATES) else None,
            identity_verified_at=now if identity_evidence else None,
            residency_district=residency_district,
            residency_address=residency_address,
            residency_source_system=residency_resp.system_name if residency_resp.result == ResidencyFetchResult.FOUND else None,
            residency_verified_at=now if residency_district else None,
            programs_eligible=programs_eligible,
            profile_hash=profile_hash,
            verification_status=overall_status,
            hold_reason=hold_reason,
            expires_at=now + timedelta(days=180),
        )
        db.add(profile)

    db.commit()

    return {
        "citizen_id": body.citizen_id,
        "name": body.name,
        "verification_status": overall_status,
        "hold_reason": hold_reason,
        "profile_hash": profile_hash,
        "source_checks": checks,
        "programs_eligible": programs_eligible,
        "verified_at": now.isoformat(),
        "expires_at": (now + timedelta(days=180)).isoformat(),
        "fraud_note": (
            "All data pulled directly from source agencies. "
            "No documents were uploaded or accepted. "
            "Source-verified records cannot be forged."
        ),
    }


@router.get("/profile/{citizen_id}")
async def get_profile(citizen_id: str, db: Session = Depends(get_db)):
    profile = db.query(CitizenProfile).filter_by(citizen_id=citizen_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="No verified profile found. Run /api/citizen/verify first.")
    return {
        "citizen_id": profile.citizen_id,
        "name": profile.name,
        "dob": profile.dob,
        "verification_status": profile.verification_status,
        "hold_reason": profile.hold_reason,
        "income_annual_inr": profile.income_annual_inr,
        "income_source": profile.income_source_system,
        "income_hold_reason": profile.income_hold_reason,
        "identity_evidence": profile.identity_evidence_type,
        "identity_source": profile.identity_source_system,
        "residency_district": profile.residency_district,
        "residency_address": profile.residency_address,
        "residency_source": profile.residency_source_system,
        "programs_eligible": profile.programs_eligible,
        "profile_hash": profile.profile_hash,
        "created_at": profile.created_at.isoformat() if profile.created_at else None,
        "expires_at": profile.expires_at.isoformat() if profile.expires_at else None,
    }


@router.post("/agent/enroll")
async def agent_enroll(body: AgentEnrollRequest, db: Session = Depends(get_db)):
    """
    AI agent enrollment endpoint.
    An AI agent calls this with a citizen_id and program_id.
    BISF checks the verified profile and either authorises enrollment or blocks.
    The agent never sees raw PII — only the eligibility decision.
    """
    profile = db.query(CitizenProfile).filter_by(citizen_id=body.citizen_id).first()
    if not profile:
        return {
            "decision": "BLOCK",
            "reason": "No verified profile found for this citizen. Verification must happen before enrollment.",
            "agent_id": body.agent_id,
            "program_id": body.program_id,
        }

    if profile.verification_status == "HOLD":
        return {
            "decision": "HOLD",
            "reason": profile.hold_reason or "Profile is on hold — human review required before enrollment.",
            "agent_id": body.agent_id,
            "program_id": body.program_id,
        }

    program_result = next(
        (p for p in (profile.programs_eligible or []) if p["id"] == body.program_id),
        None,
    )
    if not program_result:
        return {
            "decision": "BLOCK",
            "reason": f"Program '{body.program_id}' not found.",
            "agent_id": body.agent_id,
            "program_id": body.program_id,
        }

    if program_result["eligible"]:
        return {
            "decision": "ENROLL",
            "program": program_result["name"],
            "reason": program_result["reason"],
            "profile_hash": profile.profile_hash,
            "agent_id": body.agent_id,
            "citizen_id": body.citizen_id,
            "note": "Enrollment authorised on verified source data. No documents required.",
        }
    else:
        return {
            "decision": "INELIGIBLE",
            "program": program_result["name"],
            "reason": program_result["reason"],
            "agent_id": body.agent_id,
            "citizen_id": body.citizen_id,
        }


@router.get("/fraud-score/{citizen_id}")
async def fraud_score(citizen_id: str, db: Session = Depends(get_db)):
    """
    Run fraud intelligence heuristics against a verified profile.
    Returns a risk score 0-100 and the specific signals detected.
    """
    profile = db.query(CitizenProfile).filter_by(citizen_id=citizen_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="No profile found. Run /verify first.")
    result = _run_fraud_heuristics(profile)
    return {
        "citizen_id": citizen_id,
        "name": profile.name,
        "verification_status": profile.verification_status,
        **result,
        "assessed_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/discover/{citizen_id}")
async def discover_benefits(citizen_id: str, db: Session = Depends(get_db)):
    """
    Find programs the citizen qualifies for based on their verified profile.
    Returns eligible programs with estimated annual benefit value.
    """
    profile = db.query(CitizenProfile).filter_by(citizen_id=citizen_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="No profile found. Run /verify first.")

    if profile.verification_status != "VERIFIED" or not profile.income_annual_inr:
        return {
            "citizen_id": citizen_id,
            "eligible_programs": [],
            "total_annual_benefit_inr": 0,
            "note": "Profile must be VERIFIED before benefit discovery.",
        }

    eligible = [
        {
            "id": p["id"],
            "name": p["name"],
            "dept": p["dept"],
            "description": p["description"],
            "annual_benefit_inr": p["annual_benefit_inr"],
            "income_limit": p["income_limit"],
            "reason": f"Annual income ₹{profile.income_annual_inr:,} within ₹{p['income_limit']:,} limit.",
        }
        for p in PROGRAMS
        if profile.income_annual_inr <= p["income_limit"]
    ]
    total_benefit = sum(p["annual_benefit_inr"] for p in eligible)

    return {
        "citizen_id": citizen_id,
        "name": profile.name,
        "income_annual_inr": profile.income_annual_inr,
        "eligible_programs": eligible,
        "eligible_count": len(eligible),
        "total_annual_benefit_inr": total_benefit,
        "note": (
            f"{len(eligible)} programs available. "
            f"Estimated ₹{total_benefit:,}/year in benefits. "
            "No separate applications needed — one verified profile covers all."
        ),
    }


@router.get("/analytics")
async def get_analytics(db: Session = Depends(get_db)):
    """
    Live system analytics drawn from the citizen profile database.
    Shows verification volume, hold rate, program enrollment, and fraud metrics.
    """
    profiles = db.query(CitizenProfile).all()
    total = len(profiles)
    verified = [p for p in profiles if p.verification_status == "VERIFIED"]
    on_hold = [p for p in profiles if p.verification_status == "HOLD"]

    # Program enrollment counts
    program_counts: dict[str, int] = {p["id"]: 0 for p in PROGRAMS}
    total_income_verified = 0
    for p in verified:
        if p.income_annual_inr:
            total_income_verified += p.income_annual_inr
        for prog in (p.programs_eligible or []):
            if prog.get("eligible") and prog["id"] in program_counts:
                program_counts[prog["id"]] += 1

    # Fraud prevented estimate: avg benefit × hold count
    avg_benefit = 200000
    fraud_prevented_inr = len(on_hold) * avg_benefit

    hold_rate = round(len(on_hold) / total * 100, 1) if total > 0 else 0.0

    return {
        "total_profiles": total,
        "verified_count": len(verified),
        "hold_count": len(on_hold),
        "hold_rate_pct": hold_rate,
        "total_income_verified_inr": total_income_verified,
        "fraud_signals_caught": len(on_hold),
        "estimated_fraud_prevented_inr": fraud_prevented_inr,
        "program_enrollment_counts": program_counts,
        "programs": [
            {
                "id": p["id"],
                "name": p["name"],
                "enrolled": program_counts.get(p["id"], 0),
            }
            for p in PROGRAMS
        ],
        "source_systems_live": [
            "INDIA_POST_PINCODE_API_v1",
            "UIDAI_AADHAAR_v2.0",
            "CBDT_EFILING_DIGILOCKER_v1",
        ],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
