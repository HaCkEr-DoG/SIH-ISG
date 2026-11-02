"""
Income / ITR verification via DigiLocker (CBDT e-Filing document pull).

Flow:
  1. Citizen consents via DigiLocker OAuth (one-time, 180-day profile).
  2. ISG pulls the citizen's ITR XML document from their DigiLocker.
  3. Income figures are extracted directly from the ITR — no self-declaration.

When DigiLocker credentials are not configured, falls back to enrolled test
income records so the demo runs without DigiLocker app registration.

Set in .env:
  DIGILOCKER_CLIENT_ID=<your-app-client-id>
  DIGILOCKER_CLIENT_SECRET=<your-app-client-secret>
  DIGILOCKER_SANDBOX=true
"""
from __future__ import annotations

import asyncio
import os
import time
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from clients.digilocker import fetch_itr_document, DigiLockerResult


class RevenueFetchResult(str, Enum):
    FOUND = "FOUND"
    NOT_FOUND = "NOT_FOUND"
    TIMEOUT = "TIMEOUT"
    SYSTEM_ERROR = "SYSTEM_ERROR"


# Access tokens per family — in production these come from the DigiLocker
# OAuth callback and are stored (encrypted) in the CitizenProfile table.
# These placeholder tokens trigger test-mode paths in the DigiLocker client
# when real credentials are not configured.
FAMILY_DIGILOCKER_TOKEN: dict[str, str] = {
    "FAM-1001": "dl_test_token_fam1001",
    "FAM-1002": "dl_test_token_fam1002",
    "FAM-1003": "dl_test_token_fam1003",
    "FAM-2001": "dl_test_token_fam2001",
    "FAM-3001": "dl_test_token_fam3001",
    "FAM-4001": "dl_test_token_fam4001",
    "FAM-6001": "dl_test_token_fam6001",
    "FAM-6002": "dl_test_token_fam6002",
}

# Test income records — used when DigiLocker credentials are absent.
# These mirror the ITR data that would be pulled from the real DigiLocker.
# income_period MONTHLY is an intentional semantic-mismatch test case.
TEST_INCOME_RECORDS: dict[str, dict] = {
    "FAM-1001": {
        "family_id": "FAM-1001",
        "beneficiary_name": "Priya S.",
        "income_value": 180000,
        "income_period": "ANNUAL",
        "period_reference": "FY2025-26",
        "currency": "INR",
        "source": "CBDT_EFILING_DIGILOCKER",
        "assessment_type": "ITR_VERIFIED",
        "family_members": 4,
    },
    "FAM-1002": {
        "family_id": "FAM-1002",
        "beneficiary_name": "Aditya K.",
        "income_value": 250000,
        "income_period": "ANNUAL",
        "period_reference": "FY2025-26",
        "currency": "INR",
        "source": "CBDT_EFILING_DIGILOCKER",
        "assessment_type": "ITR_VERIFIED",
        "family_members": 3,
    },
    # Semantic mismatch: income submitted as MONTHLY — ISG must HOLD this.
    "FAM-2001": {
        "family_id": "FAM-2001",
        "beneficiary_name": "Ravi K.",
        "income_value": 20000,
        "income_period": "MONTHLY",
        "period_reference": "APR2025",
        "currency": "INR",
        "source": "CBDT_EFILING_DIGILOCKER",
        "assessment_type": "PAYSLIP",
        "family_members": 5,
    },
    "FAM-3001": {
        "family_id": "FAM-3001",
        "beneficiary_name": "Sunita P.",
        "income_value": 120000,
        "income_period": "ANNUAL",
        "period_reference": "FY2025-26",
        "currency": "INR",
        "source": "CBDT_EFILING_DIGILOCKER",
        "assessment_type": "ITR_VERIFIED",
        "family_members": 3,
    },
    "FAM-4001": {
        "family_id": "FAM-4001",
        "beneficiary_name": "Vikram R.",
        "income_value": 95000,
        "income_period": "ANNUAL",
        "period_reference": "FY2025-26",
        "currency": "INR",
        "source": "CBDT_EFILING_DIGILOCKER",
        "assessment_type": "ITR_VERIFIED",
        "family_members": 4,
    },
    "FAM-1003": {
        "family_id": "FAM-1003",
        "beneficiary_name": "Meera J.",
        "income_value": 160000,
        "income_period": "ANNUAL",
        "period_reference": "FY2025-26",
        "currency": "INR",
        "source": "CBDT_EFILING_DIGILOCKER",
        "assessment_type": "ITR_VERIFIED",
        "family_members": 5,
    },
    "FAM-6001": {
        "family_id": "FAM-6001",
        "beneficiary_name": "Lakshmi D.",
        "income_value": 96000,
        "income_period": "ANNUAL",
        "period_reference": "FY2025-26",
        "currency": "INR",
        "source": "CBDT_EFILING_DIGILOCKER",
        "assessment_type": "ITR_VERIFIED",
        "family_members": 5,
    },
    # Semantic mismatch: MONTHLY income for Ramesh — ISG must HOLD.
    "FAM-6002": {
        "family_id": "FAM-6002",
        "beneficiary_name": "Ramesh N.",
        "income_value": 18000,
        "income_period": "MONTHLY",
        "period_reference": "OCT2025",
        "currency": "INR",
        "source": "CBDT_EFILING_DIGILOCKER",
        "assessment_type": "PAYSLIP",
        "family_members": 4,
    },
}

TIMEOUT_FAMILIES = {"FAM-4001"}


@dataclass
class RevenueResponse:
    result: RevenueFetchResult
    data: Optional[dict] = None
    error: Optional[str] = None
    response_time_ms: int = 0
    system_name: str = "CBDT_EFILING_DIGILOCKER_v1"
    schema_version: str = "revenue-schema-v3.0"


def _has_digilocker_config() -> bool:
    return bool(
        os.getenv("DIGILOCKER_CLIENT_ID") and os.getenv("DIGILOCKER_CLIENT_SECRET")
    )


async def fetch_income_record(
    family_id: str, simulate_timeout: bool = False
) -> RevenueResponse:
    """
    Fetch income data for a family via DigiLocker ITR document pull.
    When DigiLocker credentials are configured, calls the real DigiLocker API.
    Without credentials, returns pre-enrolled test ITR records (demo mode).
    """
    start = time.monotonic()

    if simulate_timeout or family_id in TIMEOUT_FAMILIES:
        await asyncio.sleep(0.3)
        elapsed = int((time.monotonic() - start) * 1000)
        return RevenueResponse(
            result=RevenueFetchResult.TIMEOUT,
            error=f"DigiLocker connection timed out for family '{family_id}'.",
            response_time_ms=elapsed,
        )

    token = FAMILY_DIGILOCKER_TOKEN.get(family_id)

    if _has_digilocker_config() and token and not token.startswith("dl_test_"):
        # Real DigiLocker call — citizen has completed OAuth consent.
        dl_result: DigiLockerResult = await fetch_itr_document(token)
        elapsed = int((time.monotonic() - start) * 1000)

        if not dl_result.success or not dl_result.itr:
            return RevenueResponse(
                result=RevenueFetchResult.NOT_FOUND,
                error=dl_result.error or "ITR document not found in DigiLocker.",
                response_time_ms=elapsed,
            )

        itr = dl_result.itr
        return RevenueResponse(
            result=RevenueFetchResult.FOUND,
            data={
                "family_id": family_id,
                "beneficiary_name": itr.name,
                "income_value": itr.gross_total_income,
                "income_period": "ANNUAL",
                "period_reference": f"FY{itr.assessment_year}",
                "currency": "INR",
                "source": "CBDT_EFILING_DIGILOCKER",
                "assessment_type": "ITR_VERIFIED",
                "pan": itr.pan,
                "filing_date": itr.filing_date,
            },
            response_time_ms=elapsed,
        )

    # DigiLocker not configured — use enrolled test ITR records.
    await asyncio.sleep(0.10)
    elapsed = int((time.monotonic() - start) * 1000)
    record = TEST_INCOME_RECORDS.get(family_id)

    if not record:
        return RevenueResponse(
            result=RevenueFetchResult.NOT_FOUND,
            error=f"No ITR record found for family_id='{family_id}'.",
            response_time_ms=elapsed,
        )

    return RevenueResponse(
        result=RevenueFetchResult.FOUND,
        data=record,
        response_time_ms=elapsed,
    )
