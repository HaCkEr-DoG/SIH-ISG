"""
Identity verification via UIDAI Aadhaar demographic authentication.

Production: https://auth.uidai.gov.in (requires AUA registration)
Sandbox:    https://stage1.uidai.gov.in

Set in .env:
  UIDAI_AUA_CODE=<your-AUA-code>
  UIDAI_API_KEY=<your-api-key>
  UIDAI_SANDBOX=true

When UIDAI credentials are not configured the module falls back to verified
test records so the demo runs without an AUA account. Set credentials for
actual Aadhaar verification against the UIDAI sandbox or production.
"""
from __future__ import annotations

import asyncio
import os
import time
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from clients.uidai import verify_demographic


class IdentityFetchResult(str, Enum):
    FOUND = "FOUND"
    NOT_FOUND = "NOT_FOUND"
    MULTIPLE_CANDIDATES = "MULTIPLE_CANDIDATES"
    TIMEOUT = "TIMEOUT"
    SYSTEM_ERROR = "SYSTEM_ERROR"


# Aadhaar numbers per citizen.
# Sandbox test numbers (UIDAI-published) are used when UIDAI creds are absent.
# Replace with real / registered test Aadhaar numbers for UIDAI sandbox use.
CITIZEN_AADHAAR: dict[str, str] = {
    "ID-1001": "999999990019",   # UIDAI sandbox test — Maharashtra female
    "ID-1002": "999999990027",   # UIDAI sandbox test — Maharashtra male
    "ID-1003": "999999990035",   # UIDAI sandbox test
    "ID-2001": "999999990043",   # UIDAI sandbox test (identity conflict demo)
    "ID-3001": "999999990051",
    "ID-4001": "999999990069",
    "ID-6001": "999999990077",   # Lakshmi Devi — health scenario
    "ID-6002": "999999990085",   # Ramesh Nair — health scenario
}

# Name and DOB per citizen — used for UIDAI demographic match.
# Also used as fallback when UIDAI credentials are not configured.
CITIZEN_IDENTITY: dict[str, dict] = {
    "ID-1001": {"name": "Priya Sharma",    "dob": "2005-08-14", "evidence_type": "AADHAAR_LINKED"},
    "ID-1002": {"name": "Aditya Kulkarni", "dob": "2004-03-22", "evidence_type": "AADHAAR_LINKED"},
    "ID-1003": {"name": "Meera Joshi",     "dob": "2005-12-05", "evidence_type": "AADHAAR_LINKED"},
    # Identity conflict case — two records with the same name, different DOB
    "ID-2001": {"name": "Ravi Kumar",      "dob": "2004-05-12", "evidence_type": "AADHAAR_LINKED",
                "_conflict_dob": "2005-05-12"},
    "ID-3001": {"name": "Sunita Patil",    "dob": "2006-02-28", "evidence_type": "AADHAAR_LINKED"},
    "ID-4001": {"name": "Vikram Rathod",   "dob": "2003-07-19", "evidence_type": "AADHAAR_LINKED"},
    "ID-6001": {"name": "Lakshmi Devi",    "dob": "1985-03-10", "evidence_type": "AADHAAR_LINKED"},
    "ID-6002": {"name": "Ramesh Nair",     "dob": "1979-07-22", "evidence_type": "AADHAAR_LINKED"},
}


@dataclass
class IdentityResponse:
    result: IdentityFetchResult
    candidates: Optional[list[dict]] = None
    error: Optional[str] = None
    response_time_ms: int = 0
    system_name: str = "UIDAI_AADHAAR_v2.0"
    schema_version: str = "identity-schema-v2.0"


def _has_uidai_config() -> bool:
    return bool(os.getenv("UIDAI_AUA_CODE") and os.getenv("UIDAI_API_KEY"))


async def fetch_identity_candidates(identity_ref: str) -> IdentityResponse:
    """
    Verify a citizen's identity against UIDAI Aadhaar.
    When UIDAI credentials are configured, calls the real UIDAI API.
    Without credentials, returns pre-verified test records (demo mode).
    """
    start = time.monotonic()

    stored = CITIZEN_IDENTITY.get(identity_ref)
    if not stored:
        elapsed = int((time.monotonic() - start) * 1000)
        return IdentityResponse(
            result=IdentityFetchResult.NOT_FOUND,
            error=f"No identity record for ref='{identity_ref}'.",
            response_time_ms=elapsed,
        )

    aadhaar = CITIZEN_AADHAAR.get(identity_ref, "")

    # Identity conflict demo: ID-2001 has a conflicting DOB in the registry.
    if stored.get("_conflict_dob"):
        elapsed = int((time.monotonic() - start) * 1000)
        conflict_candidate = {
            "identity_ref": identity_ref + "_B",
            "name": stored["name"],
            "dob": stored["_conflict_dob"],
            "identity_provider": "UIDAI_AADHAAR_v2.0",
            "evidence_type": stored["evidence_type"],
        }
        primary_candidate = {
            "identity_ref": identity_ref,
            "name": stored["name"],
            "dob": stored["dob"],
            "identity_provider": "UIDAI_AADHAAR_v2.0",
            "evidence_type": stored["evidence_type"],
        }
        return IdentityResponse(
            result=IdentityFetchResult.MULTIPLE_CANDIDATES,
            candidates=[primary_candidate, conflict_candidate],
            response_time_ms=elapsed,
        )

    if _has_uidai_config() and aadhaar:
        # Call the real UIDAI API — demographic match against name + DOB.
        # The caller supplies name and DOB when calling verify_citizen; we pass
        # the enrolled values here so ISG can compare claimed vs. registered.
        uidai_result = await verify_demographic(
            aadhaar=aadhaar,
            name=stored["name"],
            dob=stored["dob"],
        )
        elapsed = int((time.monotonic() - start) * 1000)

        if not uidai_result.success:
            return IdentityResponse(
                result=IdentityFetchResult.SYSTEM_ERROR,
                error=uidai_result.error,
                response_time_ms=elapsed,
                system_name="UIDAI_AADHAAR_v2.0",
            )

        if not uidai_result.verified:
            return IdentityResponse(
                result=IdentityFetchResult.NOT_FOUND,
                error=uidai_result.error or "UIDAI demographic verification failed.",
                response_time_ms=elapsed,
                system_name="UIDAI_AADHAAR_v2.0",
            )

        candidate = {
            "identity_ref": identity_ref,
            "name": stored["name"],
            "dob": stored["dob"],
            "identity_provider": "UIDAI_AADHAAR_v2.0",
            "verification_status": "VERIFIED",
            "evidence_type": stored["evidence_type"],
            "aadhaar_last4": aadhaar[-4:],
            "source": "UIDAI_AADHAAR_v2.0",
        }
    else:
        # UIDAI credentials not configured — use pre-enrolled test record.
        # Suitable for demo without AUA registration.
        await asyncio.sleep(0.12)
        elapsed = int((time.monotonic() - start) * 1000)
        candidate = {
            "identity_ref": identity_ref,
            "name": stored["name"],
            "dob": stored["dob"],
            "identity_provider": "UIDAI_AADHAAR_v2.0",
            "verification_status": "VERIFIED",
            "evidence_type": stored["evidence_type"],
            "aadhaar_last4": aadhaar[-4:] if aadhaar else "XXXX",
            "source": "UIDAI_TEST_RECORD",
        }

    return IdentityResponse(
        result=IdentityFetchResult.FOUND,
        candidates=[candidate],
        response_time_ms=elapsed,
    )
