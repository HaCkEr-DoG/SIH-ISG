"""
DigiLocker API client — citizen identity and ITR document pull.

Production:  https://api.digitallocker.gov.in
Sandbox:     https://sandbox.digilocker.gov.in

Set in .env:
  DIGILOCKER_CLIENT_ID=<your-app-client-id>
  DIGILOCKER_CLIENT_SECRET=<your-app-client-secret>
  DIGILOCKER_SANDBOX=true          # use sandbox endpoint
  DIGILOCKER_REDIRECT_URI=http://localhost:8000/api/citizen/digilocker/callback

Flow used here: Authorization Code Grant (citizen grants consent once).
For departmental pulls (e-District / Resident pulls), use the Pull URI pattern.
"""
from __future__ import annotations

import os
import httpx
from dataclasses import dataclass
from typing import Optional
import xml.etree.ElementTree as ET


_SANDBOX_BASE = "https://sandbox.digilocker.gov.in"
_PROD_BASE = "https://api.digitallocker.gov.in"


def _base() -> str:
    return _SANDBOX_BASE if os.getenv("DIGILOCKER_SANDBOX", "true").lower() == "true" else _PROD_BASE


@dataclass
class DigiLockerToken:
    access_token: str
    token_type: str
    expires_in: int
    digilocker_id: str
    name: str
    dob: str
    gender: str
    eaadhaar: str  # masked Aadhaar


@dataclass
class ITRDocument:
    assessment_year: str
    gross_total_income: int
    taxable_income: int
    pan: str
    name: str
    filing_date: str
    source: str = "CBDT_EFILING_DIGILOCKER"
    verified: bool = True


@dataclass
class DigiLockerResult:
    success: bool
    token: Optional[DigiLockerToken] = None
    itr: Optional[ITRDocument] = None
    error: Optional[str] = None


async def exchange_code_for_token(auth_code: str) -> DigiLockerResult:
    """
    Exchange an OAuth2 authorization code for a DigiLocker access token.
    Called after the citizen completes the consent redirect.
    """
    client_id = os.getenv("DIGILOCKER_CLIENT_ID")
    client_secret = os.getenv("DIGILOCKER_CLIENT_SECRET")
    redirect_uri = os.getenv("DIGILOCKER_REDIRECT_URI", "http://localhost:8000/api/citizen/digilocker/callback")

    if not client_id or not client_secret:
        return DigiLockerResult(success=False, error="DIGILOCKER_CLIENT_ID / SECRET not configured.")

    payload = {
        "code": auth_code,
        "grant_type": "authorization_code",
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(f"{_base()}/public/oauth2/1/token", data=payload)
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPStatusError as exc:
        return DigiLockerResult(success=False, error=f"DigiLocker token exchange failed: HTTP {exc.response.status_code}.")
    except Exception as exc:
        return DigiLockerResult(success=False, error=str(exc))

    token = DigiLockerToken(
        access_token=data["access_token"],
        token_type=data.get("token_type", "Bearer"),
        expires_in=data.get("expires_in", 3600),
        digilocker_id=data.get("digilockerid", ""),
        name=data.get("name", ""),
        dob=data.get("dob", ""),
        gender=data.get("gender", ""),
        eaadhaar=data.get("eaadhaar", ""),
    )
    return DigiLockerResult(success=True, token=token)


async def fetch_itr_document(access_token: str, assessment_year: str = "2025-26") -> DigiLockerResult:
    """
    Pull the citizen's ITR (Income Tax Return) document from their DigiLocker.
    Document URI: in.gov.cbdt-itd-itr  (CBDT e-Filing ITR)
    Returns parsed income figures.
    """
    headers = {"Authorization": f"Bearer {access_token}"}
    doc_uri = f"in.gov.cbdt-itd-itr-{assessment_year.replace('-', '')}"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{_base()}/public/oauth2/3/xml/issued/{doc_uri}",
                headers=headers,
            )
            resp.raise_for_status()
            xml_data = resp.text
    except httpx.HTTPStatusError as exc:
        return DigiLockerResult(success=False, error=f"DigiLocker ITR fetch failed: HTTP {exc.response.status_code}.")
    except Exception as exc:
        return DigiLockerResult(success=False, error=str(exc))

    try:
        root = ET.fromstring(xml_data)
        ns = {"itr": "http://incometaxindiaefiling.gov.in/ITR"}
        gross_income = int(root.findtext(".//GrossTotalIncome", default="0"))
        taxable_income = int(root.findtext(".//TotalIncome", default="0"))
        pan = root.findtext(".//PAN", default="")
        name = root.findtext(".//AssesseeName", default="")
        filing_date = root.findtext(".//FilingDate", default="")
    except ET.ParseError as exc:
        return DigiLockerResult(success=False, error=f"ITR XML parse error: {exc}")

    itr = ITRDocument(
        assessment_year=assessment_year,
        gross_total_income=gross_income,
        taxable_income=taxable_income,
        pan=pan,
        name=name,
        filing_date=filing_date,
    )
    return DigiLockerResult(success=True, itr=itr)


def build_authorize_url(state: str = "") -> str:
    """Build the OAuth2 authorize URL to redirect the citizen to DigiLocker."""
    client_id = os.getenv("DIGILOCKER_CLIENT_ID", "")
    redirect_uri = os.getenv("DIGILOCKER_REDIRECT_URI", "http://localhost:8000/api/citizen/digilocker/callback")
    return (
        f"{_base()}/public/oauth2/1/authorize"
        f"?response_type=code"
        f"&client_id={client_id}"
        f"&redirect_uri={redirect_uri}"
        f"&state={state}"
        f"&scope=files.issueddocs"
    )
