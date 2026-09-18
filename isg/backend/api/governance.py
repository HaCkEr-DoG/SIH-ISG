"""
ISG Governance API — System Passports, Contract Registry, AI Mapping Studio.
"""
from __future__ import annotations
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from core.passport_registry import PASSPORT_REGISTRY
from core.contract_registry import CONTRACT_REGISTRY
from core.ai_gateway import suggest_income_mapping, MULTILINGUAL_FIELD_EXAMPLES

router = APIRouter(prefix="/api/governance", tags=["governance"])


# ── PASSPORTS ────────────────────────────────────────────────────────────────

@router.get("/passports")
async def list_passports():
    return [p.to_dict() for p in PASSPORT_REGISTRY.values()]


@router.get("/passports/{system_id}")
async def get_passport(system_id: str):
    p = PASSPORT_REGISTRY.get(system_id)
    if not p:
        raise HTTPException(status_code=404, detail=f"System '{system_id}' not found in passport registry.")
    return p.to_dict()


# ── CONTRACTS ─────────────────────────────────────────────────────────────────

@router.get("/contracts")
async def list_contracts():
    return [
        {
            "contract_id": c.contract_id,
            "version": c.version,
            "source_system_id": c.source_system_id,
            "source_system_name": c.source_system_name,
            "target_system_id": c.target_system_id,
            "target_system_name": c.target_system_name,
            "purpose": c.purpose,
            "status": c.status,
            "description": c.description,
            "consent_required": c.consent_required,
        }
        for c in CONTRACT_REGISTRY.values()
    ]


@router.get("/contracts/{contract_id}")
async def get_contract(contract_id: str):
    c = CONTRACT_REGISTRY.get(contract_id)
    if not c:
        raise HTTPException(status_code=404, detail=f"Contract '{contract_id}' not found.")
    return c.to_dict()


# ── AI MAPPING STUDIO ─────────────────────────────────────────────────────────

class MappingRequest(BaseModel):
    source_period: str
    source_value: float
    source_unit: Optional[str] = "INR"
    target_period: Optional[str] = "FINANCIAL_YEAR_ANNUAL"
    period_reference: Optional[str] = "FY2025-26"


@router.post("/ai/mapping-suggestion")
async def get_ai_mapping_suggestion(req: MappingRequest):
    """
    Request an AI-suggested semantic field mapping.
    The response always includes both the AI suggestion AND
    the deterministic safety analysis that overrides it.
    ai_authority is always NONE.
    """
    suggestion = suggest_income_mapping(
        source_period=req.source_period,
        source_value=req.source_value,
        source_unit=req.source_unit or "INR",
        target_period=req.target_period or "FINANCIAL_YEAR_ANNUAL",
        period_reference=req.period_reference or "FY2025-26",
    )
    return suggestion.to_dict()


@router.get("/ai/multilingual-examples")
async def get_multilingual_examples():
    """Examples of AI multilingual field name matching (Marathi/Hindi → English)."""
    return MULTILINGUAL_FIELD_EXAMPLES


# ── SCHEMA DRIFT SIMULATION ───────────────────────────────────────────────────

_schema_drift_active = False
_drifted_schema = {
    "system_id": "REV-001",
    "old_version": "v2.7",
    "new_version": "v2.8",
    "changes": [
        {
            "type": "FIELD_RENAMED",
            "old_field": "income_value",
            "new_field": "income_amount",
            "impact": "HIGH",
            "affected_contracts": ["C-017"],
        },
        {
            "type": "FIELD_SPLIT",
            "old_field": "income_period",
            "new_fields": ["income_frequency", "income_fiscal_year"],
            "impact": "HIGH",
            "affected_contracts": ["C-017"],
        },
    ],
    "contract_status": "QUARANTINED — revalidation required",
    "isg_action": "Contract C-017 suspended. Semantic revalidation initiated.",
}


@router.post("/schema-drift/simulate")
async def simulate_schema_drift():
    global _schema_drift_active
    _schema_drift_active = True
    return {
        "drift_detected": True,
        "system": "Revenue System",
        **_drifted_schema,
    }


@router.post("/schema-drift/reset")
async def reset_schema_drift():
    global _schema_drift_active
    _schema_drift_active = False
    return {"drift_detected": False, "message": "Schema drift cleared. Contract C-017 restored to ACTIVE."}


@router.get("/schema-drift/status")
async def schema_drift_status():
    if _schema_drift_active:
        return {"drift_detected": True, **_drifted_schema}
    return {
        "drift_detected": False,
        "message": "All system schemas match their registered versions.",
    }
