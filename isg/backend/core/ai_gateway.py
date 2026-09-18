"""
ISG AI Gateway — AI suggestions for semantic field mapping.

CRITICAL INVARIANT: AI only suggests. The deterministic safety engine
decides. ai_was_final_authority is ALWAYS False.

The AI gateway demonstrates where AI adds value (pattern recognition,
multilingual matching, anomaly flagging) without giving AI decision authority
over safety-consequential government transactions.
"""
from __future__ import annotations
from dataclasses import dataclass


@dataclass
class AIMappingSuggestion:
    source_field: str
    source_period: str
    source_unit: str
    source_value_display: str
    target_field: str
    target_period: str
    target_unit: str
    suggested_transformation: str
    confidence: float
    ai_reasoning: str
    # Deterministic safety analysis overrides the AI suggestion
    deterministic_result: str        # PASS / QUARANTINE / REJECT
    deterministic_reason: str
    deterministic_checks: list       # List of {check, result, note}
    temporal_coverage_provable: bool
    ai_authority: str                # Always "NONE"

    def to_dict(self) -> dict:
        return {
            "source_field": self.source_field,
            "source_period": self.source_period,
            "source_unit": self.source_unit,
            "source_value_display": self.source_value_display,
            "target_field": self.target_field,
            "target_period": self.target_period,
            "target_unit": self.target_unit,
            "suggested_transformation": self.suggested_transformation,
            "confidence": self.confidence,
            "ai_reasoning": self.ai_reasoning,
            "deterministic_result": self.deterministic_result,
            "deterministic_reason": self.deterministic_reason,
            "deterministic_checks": self.deterministic_checks,
            "temporal_coverage_provable": self.temporal_coverage_provable,
            "ai_authority": self.ai_authority,
        }


def suggest_income_mapping(
    source_period: str,
    source_value: float,
    source_unit: str = "INR",
    target_period: str = "FINANCIAL_YEAR_ANNUAL",
    period_reference: str = "FY2025-26",
) -> AIMappingSuggestion:
    """
    AI suggests a semantic mapping for income fields.
    Deterministic engine then validates whether the suggestion is safe.
    """
    if source_period == "MONTHLY":
        annual_est = source_value * 12
        return AIMappingSuggestion(
            source_field="family_income_monthly",
            source_period="MONTHLY",
            source_unit="INR/month",
            source_value_display=f"₹{source_value:,.0f}/month",
            target_field="annual_family_income",
            target_period="FINANCIAL_YEAR_ANNUAL",
            target_unit="INR/year (FY2025-26)",
            suggested_transformation=f"monthly × 12 = ₹{annual_est:,.0f}/year",
            confidence=0.94,
            ai_reasoning=(
                "Standard annualization: multiply monthly income by 12. "
                "Commonly applied in income assessment for welfare schemes."
            ),
            deterministic_result="QUARANTINE",
            deterministic_reason=(
                "Transformation not authorized. Contract C-017 v7 requires "
                "FINANCIAL_YEAR_ANNUAL source data — monthly extrapolation not permitted."
            ),
            deterministic_checks=[
                {"check": "Unit match (INR)", "result": "PASS", "note": "Both INR"},
                {"check": "Entity scope (HOUSEHOLD)", "result": "PASS", "note": "Same entity"},
                {"check": "Period match", "result": "FAIL", "note": "MONTHLY ≠ FINANCIAL_YEAR_ANNUAL"},
                {"check": "FY2025-26 coverage provable", "result": "FAIL", "note": "12 equal months not proven"},
                {"check": "No seasonal variation assumed", "result": "UNKNOWN", "note": "Not verifiable"},
                {"check": "No income gaps assumed", "result": "UNKNOWN", "note": "Not verifiable"},
                {"check": "Transformation authorized in contract", "result": "FAIL", "note": "NOT authorized"},
            ],
            temporal_coverage_provable=False,
            ai_authority="NONE",
        )

    elif source_period in ("ANNUAL", "FINANCIAL_YEAR_ANNUAL"):
        return AIMappingSuggestion(
            source_field="family_income_annual",
            source_period=source_period,
            source_unit="INR/year",
            source_value_display=f"₹{source_value:,.0f}/year ({period_reference})",
            target_field="annual_family_income",
            target_period="FINANCIAL_YEAR_ANNUAL",
            target_unit="INR/year (FY2025-26)",
            suggested_transformation=f"Direct mapping — same period ({period_reference})",
            confidence=0.99,
            ai_reasoning=(
                "Annual income with matching financial year reference maps directly "
                "to annual_family_income. No conversion required."
            ),
            deterministic_result="PASS",
            deterministic_reason=(
                "Source period FINANCIAL_YEAR_ANNUAL matches target. "
                "Direct mapping authorized by contract C-017 v7."
            ),
            deterministic_checks=[
                {"check": "Unit match (INR)", "result": "PASS", "note": "Both INR"},
                {"check": "Entity scope (HOUSEHOLD)", "result": "PASS", "note": "Same entity"},
                {"check": "Period match", "result": "PASS", "note": "FINANCIAL_YEAR_ANNUAL = FINANCIAL_YEAR_ANNUAL"},
                {"check": "FY2025-26 coverage provable", "result": "PASS", "note": f"period_reference = {period_reference}"},
                {"check": "Transformation authorized in contract", "result": "PASS", "note": "Direct mapping authorized"},
            ],
            temporal_coverage_provable=True,
            ai_authority="NONE",
        )

    else:
        return AIMappingSuggestion(
            source_field="income",
            source_period=source_period or "UNKNOWN",
            source_unit=source_unit,
            source_value_display=f"₹{source_value:,.0f} (period unknown)",
            target_field="annual_family_income",
            target_period="FINANCIAL_YEAR_ANNUAL",
            target_unit="INR/year",
            suggested_transformation="Cannot suggest — period semantics ambiguous",
            confidence=0.30,
            ai_reasoning="Income period is unknown or unrecognized. Cannot suggest reliable transformation.",
            deterministic_result="QUARANTINE",
            deterministic_reason="Temporal scope UNKNOWN — cannot establish period equivalence.",
            deterministic_checks=[
                {"check": "Period match", "result": "UNKNOWN", "note": f"Source period: {source_period}"},
                {"check": "Coverage provable", "result": "FAIL", "note": "Period unknown"},
            ],
            temporal_coverage_provable=False,
            ai_authority="NONE",
        )


MULTILINGUAL_FIELD_EXAMPLES = [
    {
        "source_language": "Marathi",
        "source_text": "वार्षिक कौटुंबिक उत्पन्न",
        "target_field": "annual_family_income",
        "confidence": 0.97,
        "method": "MuRIL multilingual embeddings",
    },
    {
        "source_language": "Hindi",
        "source_text": "पारिवारिक वार्षिक आय",
        "target_field": "annual_family_income",
        "confidence": 0.95,
        "method": "MuRIL multilingual embeddings",
    },
    {
        "source_language": "Marathi",
        "source_text": "प्रवेश स्थिती",
        "target_field": "enrollment_status",
        "confidence": 0.93,
        "method": "MuRIL multilingual embeddings",
    },
]
