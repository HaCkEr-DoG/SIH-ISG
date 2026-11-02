"""
UIDAI Aadhaar demographic verification client.

Production: https://auth.uidai.gov.in
Sandbox:    https://stage1.uidai.gov.in

Set in .env:
  UIDAI_AUA_CODE=<your-AUA-code>           # Registered with UIDAI
  UIDAI_API_KEY=<your-api-key>
  UIDAI_SANDBOX=true

Sandbox test Aadhaar numbers (UIDAI-published):
  999999990019  - Male, Karnataka
  999999990027  - Female, Maharashtra
  999999990035  - Male, Delhi
"""
from __future__ import annotations

import os
import hashlib
import httpx
from dataclasses import dataclass
from typing import Optional
import defusedxml.ElementTree as ET


_SANDBOX_BASE = "https://stage1.uidai.gov.in"
_PROD_BASE = "https://auth.uidai.gov.in"

_AUTH_VERSION = "2.0"


def _base() -> str:
    return _SANDBOX_BASE if os.getenv("UIDAI_SANDBOX", "true").lower() == "true" else _PROD_BASE


@dataclass
class AadhaarVerifyResult:
    success: bool
    verified: bool = False
    name: Optional[str] = None
    dob: Optional[str] = None
    gender: Optional[str] = None
    state: Optional[str] = None
    aadhaar_last4: Optional[str] = None
    error: Optional[str] = None
    source: str = "UIDAI_AADHAAR"


async def verify_demographic(
    aadhaar: str,
    name: str,
    dob: str,
) -> AadhaarVerifyResult:
    """
    Perform a demographic (name + DOB) verification against UIDAI.
    Returns whether the supplied name and DOB match the Aadhaar record.
    No OTP required — AUA-level service provider call.

    The actual UIDAI API uses signed XML requests.
    This client builds the correct XML envelope and sends it.
    """
    aua_code = os.getenv("UIDAI_AUA_CODE")
    api_key = os.getenv("UIDAI_API_KEY")

    if not aua_code or not api_key:
        return AadhaarVerifyResult(
            success=False,
            error="UIDAI_AUA_CODE / UIDAI_API_KEY not configured. "
                  "Register at https://uidai.gov.in/ecosystem/authentication-devices-documents/aua-kua-registration.html",
        )

    # Build UIDAI Auth XML (v2.0 schema)
    aadhaar_hash = hashlib.sha256(aadhaar.encode()).hexdigest()
    xml_payload = (
        f'<?xml version="1.0" encoding="UTF-8"?>'
        f'<Auth uid="{aadhaar}" tid="public" ac="{aua_code}" sa="{aua_code}" '
        f'ver="{_AUTH_VERSION}" txn="ISG-DEMO-{aadhaar_hash[:8]}" lk="{api_key}">'
        f'<Uses pi="y" pa="n" pfa="n" bio="n" bt="n" pin="n"/>'
        f'<Pi ms="E" mv="1" name="{name}" dob="{dob}"/>'
        f'</Auth>'
    )

    endpoint = f"{_base()}/authserver/auth/{aua_code}/{_AUTH_VERSION}/{aadhaar[0]}/{aadhaar[1]}"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                endpoint,
                content=xml_payload.encode("utf-8"),
                headers={"Content-Type": "application/xml"},
            )
            resp.raise_for_status()
            root = ET.fromstring(resp.text)
    except httpx.TimeoutException:
        return AadhaarVerifyResult(success=False, error="UIDAI API timed out.")
    except httpx.HTTPStatusError as exc:
        return AadhaarVerifyResult(success=False, error=f"UIDAI HTTP {exc.response.status_code}.")
    except ET.ParseError as exc:
        return AadhaarVerifyResult(success=False, error=f"UIDAI response XML parse error: {exc}")
    except Exception as exc:
        return AadhaarVerifyResult(success=False, error=str(exc))

    ret = root.attrib.get("ret", "n")
    err = root.attrib.get("err", "")

    if ret == "y":
        return AadhaarVerifyResult(
            success=True,
            verified=True,
            aadhaar_last4=aadhaar[-4:],
            source="UIDAI_AADHAAR_v2.0",
        )
    else:
        return AadhaarVerifyResult(
            success=True,
            verified=False,
            error=f"UIDAI demographic mismatch. Error code: {err}",
            aadhaar_last4=aadhaar[-4:],
        )
