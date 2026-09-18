"""
Maharashtra Revenue/Income System Simulator.
Exposes its own schema and identity model (family_id based).
Simulates reliability failures and timeouts.
This is NOT a real government system — prototype simulation only.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
from enum import Enum
import asyncio
import time


class RevenueFetchResult(str, Enum):
    FOUND = "FOUND"
    NOT_FOUND = "NOT_FOUND"
    TIMEOUT = "TIMEOUT"
    SYSTEM_ERROR = "SYSTEM_ERROR"


# Revenue system uses its own schema — different from Education/Identity
REVENUE_RECORDS = {
    # Valid annual FY cases
    "FAM-1001": {
        "family_id": "FAM-1001",
        "beneficiary_name": "Priya S.",          # Different name format than Education
        "income_value": 180000,
        "income_period": "ANNUAL",
        "period_reference": "FY2025-26",
        "currency": "INR",
        "source": "REVENUE_DEPT_MH",
        "source_version": "v2.7",
        "assessed_date": "2025-12-01",
        "assessment_type": "SELF_DECLARATION_VERIFIED",
        "family_members": 4,
    },
    "FAM-1002": {
        "family_id": "FAM-1002",
        "beneficiary_name": "Aditya K.",
        "income_value": 250000,
        "income_period": "ANNUAL",
        "period_reference": "FY2025-26",
        "currency": "INR",
        "source": "REVENUE_DEPT_MH",
        "source_version": "v2.7",
        "assessed_date": "2025-11-15",
        "assessment_type": "ITR_VERIFIED",
        "family_members": 3,
    },
    # SEMANTIC ATTACK: Monthly income (not annual FY) — will fail semantic check
    "FAM-2001": {
        "family_id": "FAM-2001",
        "beneficiary_name": "Ravi K.",
        "income_value": 20000,
        "income_period": "MONTHLY",           # <-- MONTHLY, not ANNUAL FY
        "period_reference": "APR2025",
        "currency": "INR",
        "source": "REVENUE_DEPT_MH",
        "source_version": "v2.7",
        "assessed_date": "2025-04-30",
        "assessment_type": "PAYSLIP",
        "family_members": 5,
    },
    # Policy/consent error case — valid income
    "FAM-3001": {
        "family_id": "FAM-3001",
        "beneficiary_name": "Sunita P.",
        "income_value": 120000,
        "income_period": "ANNUAL",
        "period_reference": "FY2025-26",
        "currency": "INR",
        "source": "REVENUE_DEPT_MH",
        "source_version": "v2.7",
        "assessed_date": "2025-10-10",
        "assessment_type": "VERIFIED",
        "family_members": 3,
    },
    # Timeout / failure case
    "FAM-4001": {
        "family_id": "FAM-4001",
        "beneficiary_name": "Vikram R.",
        "income_value": 95000,
        "income_period": "ANNUAL",
        "period_reference": "FY2025-26",
        "currency": "INR",
        "source": "REVENUE_DEPT_MH",
        "source_version": "v2.7",
        "assessed_date": "2025-09-20",
        "assessment_type": "VERIFIED",
        "family_members": 4,
    },
    # Additional valid cases
    "FAM-1003": {
        "family_id": "FAM-1003",
        "beneficiary_name": "Meera J.",
        "income_value": 160000,
        "income_period": "ANNUAL",
        "period_reference": "FY2025-26",
        "currency": "INR",
        "source": "REVENUE_DEPT_MH",
        "source_version": "v2.7",
        "assessed_date": "2025-11-01",
        "assessment_type": "VERIFIED",
        "family_members": 5,
    },
}

# Systems that should simulate timeouts for specific family IDs
TIMEOUT_FAMILIES = {"FAM-4001"}


@dataclass
class RevenueResponse:
    result: RevenueFetchResult
    data: Optional[dict] = None
    error: Optional[str] = None
    response_time_ms: int = 0
    system_name: str = "REVENUE_SYSTEM_MH_v2.7"
    schema_version: str = "revenue-schema-v2.7"


async def fetch_income_record(
    family_id: str, simulate_timeout: bool = False
) -> RevenueResponse:
    """
    Simulate fetching from the Revenue System.
    Returns revenue system's own schema — ISG must perform semantic mapping.
    """
    start = time.monotonic()
    await asyncio.sleep(0.1)  # simulate network latency

    if simulate_timeout or family_id in TIMEOUT_FAMILIES:
        # Simulate a real timeout — ISG must handle UNKNOWN_RESULT
        await asyncio.sleep(0.2)
        elapsed = int((time.monotonic() - start) * 1000)
        return RevenueResponse(
            result=RevenueFetchResult.TIMEOUT,
            error=f"Revenue System connection timed out after 300ms for family '{family_id}'.",
            response_time_ms=elapsed,
        )

    record = REVENUE_RECORDS.get(family_id)
    elapsed = int((time.monotonic() - start) * 1000)

    if not record:
        return RevenueResponse(
            result=RevenueFetchResult.NOT_FOUND,
            error=f"No income record found for family_id='{family_id}'.",
            response_time_ms=elapsed,
        )

    return RevenueResponse(
        result=RevenueFetchResult.FOUND,
        data=record,
        response_time_ms=elapsed,
    )
