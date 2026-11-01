"""
Maharashtra Address / Residency Registry Simulator.
Returns verified address and district from the municipal registry.
This is NOT a real government system — prototype simulation only.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
from enum import Enum
import asyncio
import time


class ResidencyFetchResult(str, Enum):
    FOUND = "FOUND"
    NOT_FOUND = "NOT_FOUND"
    TIMEOUT = "TIMEOUT"
    SYSTEM_ERROR = "SYSTEM_ERROR"


RESIDENCY_RECORDS = {
    "ID-1001": {
        "citizen_id": "ID-1001",
        "name": "Priya Sharma",
        "address": "Flat 4B, Adarsh Nagar, Pune",
        "district": "Pune",
        "state": "Maharashtra",
        "pin": "411001",
        "residency_since": "2020-06-01",
        "verified_by": "MUNICIPAL_REGISTRY_MH",
        "source": "ADDRESS_REGISTRY_MH",
        "source_version": "v1.2",
    },
    "ID-1002": {
        "citizen_id": "ID-1002",
        "name": "Aditya Kulkarni",
        "address": "12, Shivaji Road, Nashik",
        "district": "Nashik",
        "state": "Maharashtra",
        "pin": "422001",
        "residency_since": "2018-03-15",
        "verified_by": "MUNICIPAL_REGISTRY_MH",
        "source": "ADDRESS_REGISTRY_MH",
        "source_version": "v1.2",
    },
    "ID-2001": {
        "citizen_id": "ID-2001",
        "name": "Ravi Kumar",
        "address": "23, Gandhi Chowk, Nagpur",
        "district": "Nagpur",
        "state": "Maharashtra",
        "pin": "440001",
        "residency_since": "2019-09-01",
        "verified_by": "MUNICIPAL_REGISTRY_MH",
        "source": "ADDRESS_REGISTRY_MH",
        "source_version": "v1.2",
    },
    "ID-3001": {
        "citizen_id": "ID-3001",
        "name": "Sunita Patil",
        "address": "7, Sadar Bazaar, Aurangabad",
        "district": "Aurangabad",
        "state": "Maharashtra",
        "pin": "431001",
        "residency_since": "2021-01-10",
        "verified_by": "MUNICIPAL_REGISTRY_MH",
        "source": "ADDRESS_REGISTRY_MH",
        "source_version": "v1.2",
    },
    "ID-4001": {
        "citizen_id": "ID-4001",
        "name": "Vikram Rathod",
        "address": "55, MG Road, Solapur",
        "district": "Solapur",
        "state": "Maharashtra",
        "pin": "413001",
        "residency_since": "2017-11-20",
        "verified_by": "MUNICIPAL_REGISTRY_MH",
        "source": "ADDRESS_REGISTRY_MH",
        "source_version": "v1.2",
    },
    "ID-1003": {
        "citizen_id": "ID-1003",
        "name": "Meera Joshi",
        "address": "88, Peth Area, Kolhapur",
        "district": "Kolhapur",
        "state": "Maharashtra",
        "pin": "416001",
        "residency_since": "2022-04-01",
        "verified_by": "MUNICIPAL_REGISTRY_MH",
        "source": "ADDRESS_REGISTRY_MH",
        "source_version": "v1.2",
    },
    "ID-6001": {
        "citizen_id": "ID-6001",
        "name": "Lakshmi Devi",
        "address": "14, Ram Nagar, Thane",
        "district": "Thane",
        "state": "Maharashtra",
        "pin": "400601",
        "residency_since": "2016-08-12",
        "verified_by": "MUNICIPAL_REGISTRY_MH",
        "source": "ADDRESS_REGISTRY_MH",
        "source_version": "v1.2",
    },
    "ID-6002": {
        "citizen_id": "ID-6002",
        "name": "Ramesh Nair",
        "address": "9, Azad Nagar, Mumbai",
        "district": "Mumbai",
        "state": "Maharashtra",
        "pin": "400058",
        "residency_since": "2015-05-30",
        "verified_by": "MUNICIPAL_REGISTRY_MH",
        "source": "ADDRESS_REGISTRY_MH",
        "source_version": "v1.2",
    },
}


@dataclass
class ResidencyResponse:
    result: ResidencyFetchResult
    data: Optional[dict] = None
    error: Optional[str] = None
    response_time_ms: int = 0
    system_name: str = "ADDRESS_REGISTRY_MH_v1.2"
    schema_version: str = "residency-schema-v1.2"


async def fetch_residency_record(citizen_id: str) -> ResidencyResponse:
    """
    Simulate fetching from the Municipal Address Registry.
    Returns verified residency data — ISG safety checks still apply.
    """
    start = time.monotonic()
    await asyncio.sleep(0.09)
    elapsed = int((time.monotonic() - start) * 1000)

    record = RESIDENCY_RECORDS.get(citizen_id)
    if not record:
        return ResidencyResponse(
            result=ResidencyFetchResult.NOT_FOUND,
            error=f"No residency record found for citizen_id='{citizen_id}'.",
            response_time_ms=elapsed,
        )

    return ResidencyResponse(
        result=ResidencyFetchResult.FOUND,
        data=record,
        response_time_ms=elapsed,
    )
