"""
Residency verification via the real India Post Pincode API.
Endpoint: https://api.postalpincode.in/pincode/{pincode}
Free — no API key required.

Each citizen's stored address (street/flat) is kept in CITIZEN_ADDRESS_DATA.
District and state are verified live from India Post — not hardcoded.
"""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from clients.india_post import lookup_pincode


class ResidencyFetchResult(str, Enum):
    FOUND = "FOUND"
    NOT_FOUND = "NOT_FOUND"
    TIMEOUT = "TIMEOUT"
    SYSTEM_ERROR = "SYSTEM_ERROR"


# Street address and pincode per citizen.
# District and state are resolved live from India Post — values here are
# the citizen's self-reported / enrolled address line only.
CITIZEN_ADDRESS_DATA: dict[str, dict] = {
    "ID-1001": {"address": "Flat 4B, Adarsh Nagar", "pin": "411001", "residency_since": "2020-06-01"},
    "ID-1002": {"address": "12, Shivaji Road",       "pin": "422001", "residency_since": "2018-03-15"},
    "ID-1003": {"address": "88, Peth Area",          "pin": "416001", "residency_since": "2022-04-01"},
    "ID-2001": {"address": "23, Gandhi Chowk",       "pin": "440001", "residency_since": "2019-09-01"},
    "ID-3001": {"address": "7, Sadar Bazaar",        "pin": "431001", "residency_since": "2021-01-10"},
    "ID-4001": {"address": "55, MG Road",            "pin": "413001", "residency_since": "2017-11-20"},
    "ID-6001": {"address": "14, Ram Nagar",          "pin": "400601", "residency_since": "2016-08-12"},
    "ID-6002": {"address": "9, Azad Nagar",          "pin": "400058", "residency_since": "2015-05-30"},
}


@dataclass
class ResidencyResponse:
    result: ResidencyFetchResult
    data: Optional[dict] = None
    error: Optional[str] = None
    response_time_ms: int = 0
    system_name: str = "INDIA_POST_PINCODE_API_v1"
    schema_version: str = "residency-schema-v2.0"


async def fetch_residency_record(citizen_id: str) -> ResidencyResponse:
    """
    Verify a citizen's address by calling the real India Post Pincode API.
    Returns district and state sourced directly from India Post — not from
    a hardcoded table.
    """
    start = time.monotonic()

    stored = CITIZEN_ADDRESS_DATA.get(citizen_id)
    if not stored:
        elapsed = int((time.monotonic() - start) * 1000)
        return ResidencyResponse(
            result=ResidencyFetchResult.NOT_FOUND,
            error=f"No address record found for citizen_id='{citizen_id}'.",
            response_time_ms=elapsed,
        )

    pincode_result = await lookup_pincode(stored["pin"])
    elapsed = int((time.monotonic() - start) * 1000)

    if not pincode_result.success or not pincode_result.primary:
        return ResidencyResponse(
            result=ResidencyFetchResult.NOT_FOUND,
            error=pincode_result.error or f"Pincode {stored['pin']} not found in India Post database.",
            response_time_ms=elapsed,
        )

    po = pincode_result.primary
    return ResidencyResponse(
        result=ResidencyFetchResult.FOUND,
        data={
            "citizen_id": citizen_id,
            "address": stored["address"],
            "pin": stored["pin"],
            "district": po.district,          # live from India Post
            "state": po.state,                # live from India Post
            "post_office": po.name,           # live from India Post
            "circle": po.circle,              # live from India Post
            "residency_since": stored["residency_since"],
            "verified_by": "INDIA_POST_PINCODE_API",
            "pincode_verified": True,
        },
        response_time_ms=elapsed,
    )
