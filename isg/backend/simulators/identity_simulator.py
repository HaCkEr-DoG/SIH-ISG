"""
Maharashtra Identity Verification System Simulator.
Uses identity_ref and name+dob as keys. Different schema from Revenue and Education.
Contains the identity conflict cases for Attack #2.
This is NOT a real government system — prototype simulation only.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
from enum import Enum
import asyncio
import time


class IdentityFetchResult(str, Enum):
    FOUND = "FOUND"
    NOT_FOUND = "NOT_FOUND"
    MULTIPLE_CANDIDATES = "MULTIPLE_CANDIDATES"
    TIMEOUT = "TIMEOUT"
    SYSTEM_ERROR = "SYSTEM_ERROR"


# Identity system candidates — indexed by identity_ref
# Note: schema uses "name" and "dob" (not student_name/birth_date from Education)
IDENTITY_RECORDS = {
    "ID-1001": {
        "identity_ref": "ID-1001",
        "name": "Priya Sharma",
        "dob": "2005-08-14",
        "identity_provider": "UIDAI_PROXY_MH",
        "verification_status": "VERIFIED",
        "last_verified": "2025-09-15",
        "evidence_type": "AADHAAR_LINKED",
        "source": "IDENTITY_SYSTEM_MH",
        "source_version": "v1.5",
    },
    "ID-1002": {
        "identity_ref": "ID-1002",
        "name": "Aditya Kulkarni",
        "dob": "2004-03-22",
        "identity_provider": "UIDAI_PROXY_MH",
        "verification_status": "VERIFIED",
        "last_verified": "2025-10-01",
        "evidence_type": "AADHAAR_LINKED",
        "source": "IDENTITY_SYSTEM_MH",
        "source_version": "v1.5",
    },
    # IDENTITY ATTACK #2: Two records with same name but different DOB
    # Record A: Ravi Kumar, DOB 2004-05-12
    "ID-2001": {
        "identity_ref": "ID-2001",
        "name": "Ravi Kumar",
        "dob": "2004-05-12",
        "identity_provider": "UIDAI_PROXY_MH",
        "verification_status": "VERIFIED",
        "last_verified": "2025-08-20",
        "evidence_type": "AADHAAR_LINKED",
        "source": "IDENTITY_SYSTEM_MH",
        "source_version": "v1.5",
    },
    # Record B: Ravi Kumar, DOB 2005-05-12 — SAME NAME, DIFFERENT YEAR
    "ID-2002": {
        "identity_ref": "ID-2002",
        "name": "Ravi Kumar",
        "dob": "2005-05-12",
        "identity_provider": "UIDAI_PROXY_MH",
        "verification_status": "VERIFIED",
        "last_verified": "2025-08-22",
        "evidence_type": "AADHAAR_LINKED",
        "source": "IDENTITY_SYSTEM_MH",
        "source_version": "v1.5",
    },
    # Policy/consent case
    "ID-3001": {
        "identity_ref": "ID-3001",
        "name": "Sunita Patil",
        "dob": "2006-02-28",
        "identity_provider": "UIDAI_PROXY_MH",
        "verification_status": "VERIFIED",
        "last_verified": "2025-09-10",
        "evidence_type": "AADHAAR_LINKED",
        "source": "IDENTITY_SYSTEM_MH",
        "source_version": "v1.5",
    },
    # Recovery case
    "ID-4001": {
        "identity_ref": "ID-4001",
        "name": "Vikram Rathod",
        "dob": "2003-07-19",
        "identity_provider": "UIDAI_PROXY_MH",
        "verification_status": "VERIFIED",
        "last_verified": "2025-09-25",
        "evidence_type": "AADHAAR_LINKED",
        "source": "IDENTITY_SYSTEM_MH",
        "source_version": "v1.5",
    },
    "ID-1003": {
        "identity_ref": "ID-1003",
        "name": "Meera Joshi",
        "dob": "2005-12-05",
        "identity_provider": "UIDAI_PROXY_MH",
        "verification_status": "VERIFIED",
        "last_verified": "2025-10-01",
        "evidence_type": "AADHAAR_LINKED",
        "source": "IDENTITY_SYSTEM_MH",
        "source_version": "v1.5",
    },
}

# Map from application identity_ref to candidate set
# For identity attack: ID-2001 returns BOTH conflicting records
IDENTITY_CANDIDATE_SETS: dict[str, list[str]] = {
    "ID-1001": ["ID-1001"],
    "ID-1002": ["ID-1002"],
    "ID-2001": ["ID-2001", "ID-2002"],   # Both returned for the conflict case
    "ID-3001": ["ID-3001"],
    "ID-4001": ["ID-4001"],
    "ID-1003": ["ID-1003"],
}


@dataclass
class IdentityResponse:
    result: IdentityFetchResult
    candidates: Optional[list[dict]] = None
    error: Optional[str] = None
    response_time_ms: int = 0
    system_name: str = "IDENTITY_SYSTEM_MH_v1.5"
    schema_version: str = "identity-schema-v1.5"


async def fetch_identity_candidates(identity_ref: str) -> IdentityResponse:
    """
    Simulate fetching identity candidates from the Identity System.
    Returns all matching candidates — ISG must perform calibrated matching.
    Note: identity system uses its own schema (name/dob) vs Education (student_name/birth_date).
    """
    start = time.monotonic()
    await asyncio.sleep(0.12)  # identity systems are typically slower

    candidate_refs = IDENTITY_CANDIDATE_SETS.get(identity_ref)
    elapsed = int((time.monotonic() - start) * 1000)

    if not candidate_refs:
        return IdentityResponse(
            result=IdentityFetchResult.NOT_FOUND,
            error=f"No identity candidates for ref='{identity_ref}'.",
            response_time_ms=elapsed,
        )

    candidates = [IDENTITY_RECORDS[ref] for ref in candidate_refs if ref in IDENTITY_RECORDS]

    if len(candidates) > 1:
        return IdentityResponse(
            result=IdentityFetchResult.MULTIPLE_CANDIDATES,
            candidates=candidates,
            response_time_ms=elapsed,
        )

    return IdentityResponse(
        result=IdentityFetchResult.FOUND,
        candidates=candidates,
        response_time_ms=elapsed,
    )
