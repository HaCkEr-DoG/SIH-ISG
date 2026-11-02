"""
India Post Pincode API client.
Endpoint: https://api.postalpincode.in/pincode/{pincode}
Free — no API key required. Returns real district / state / post office data.
"""
from __future__ import annotations

import httpx
from dataclasses import dataclass, field
from typing import Optional

_BASE = "https://api.postalpincode.in/pincode"
_TIMEOUT = 6.0


@dataclass
class PostOfficeRecord:
    name: str
    branch_type: str
    delivery_status: str
    district: str
    division: str
    region: str
    state: str
    country: str
    pincode: str
    circle: str


@dataclass
class PincodeResult:
    success: bool
    pincode: str
    offices: list[PostOfficeRecord] = field(default_factory=list)
    error: Optional[str] = None

    @property
    def primary(self) -> Optional[PostOfficeRecord]:
        """Return the head post office, or the first office."""
        for o in self.offices:
            if o.branch_type == "Head Post Office":
                return o
        return self.offices[0] if self.offices else None


async def lookup_pincode(pincode: str) -> PincodeResult:
    """
    Call the real India Post Pincode API.
    Returns post office records for the given pincode, including real district and state.
    """
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(f"{_BASE}/{pincode}")
            resp.raise_for_status()
            payload = resp.json()
    except httpx.TimeoutException:
        return PincodeResult(success=False, pincode=pincode, error="India Post API timed out.")
    except httpx.HTTPStatusError as exc:
        return PincodeResult(success=False, pincode=pincode, error=f"India Post API HTTP {exc.response.status_code}.")
    except Exception as exc:
        return PincodeResult(success=False, pincode=pincode, error=str(exc))

    if not payload or payload[0].get("Status") != "Success":
        return PincodeResult(
            success=False,
            pincode=pincode,
            error=payload[0].get("Message", "Pincode not found.") if payload else "Empty response.",
        )

    offices = [
        PostOfficeRecord(
            name=po.get("Name", ""),
            branch_type=po.get("BranchType", ""),
            delivery_status=po.get("DeliveryStatus", ""),
            district=po.get("District", ""),
            division=po.get("Division", ""),
            region=po.get("Region", ""),
            state=po.get("State", ""),
            country=po.get("Country", "India"),
            pincode=po.get("Pincode", pincode),
            circle=po.get("Circle", ""),
        )
        for po in payload[0].get("PostOffice", [])
    ]

    return PincodeResult(success=True, pincode=pincode, offices=offices)
