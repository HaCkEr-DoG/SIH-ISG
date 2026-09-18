"""
ISG Semantic IR — Typed intermediate representation for cross-system field mapping.
All semantic decisions are deterministic and explicitly traced.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Optional
from enum import Enum
import hashlib
import json


class SemanticType(str, Enum):
    CURRENCY_AMOUNT = "CURRENCY_AMOUNT"
    PERSON_NAME = "PERSON_NAME"
    DATE = "DATE"
    ENROLLMENT_STATUS = "ENROLLMENT_STATUS"
    IDENTIFIER = "IDENTIFIER"
    COURSE_CODE = "COURSE_CODE"
    PERIOD = "PERIOD"
    FINANCIAL_YEAR = "FINANCIAL_YEAR"


class TemporalScope(str, Enum):
    MONTHLY = "MONTHLY"
    ANNUAL = "ANNUAL"
    FINANCIAL_YEAR_ANNUAL = "FINANCIAL_YEAR_ANNUAL"
    POINT_IN_TIME = "POINT_IN_TIME"
    UNKNOWN = "UNKNOWN"


class SemanticCheckResult(str, Enum):
    PASS = "PASS"
    TEMPORAL_MISMATCH = "TEMPORAL_MISMATCH"
    UNIT_MISMATCH = "UNIT_MISMATCH"
    COVERAGE_GAP = "COVERAGE_GAP"
    MAPPING_AMBIGUOUS = "MAPPING_AMBIGUOUS"
    MISSING_FIELD = "MISSING_FIELD"
    TYPE_MISMATCH = "TYPE_MISMATCH"


@dataclass
class SemanticField:
    """Typed semantic representation of a single field from a source system."""
    field_name: str
    semantic_type: SemanticType
    value: Any
    unit: Optional[str] = None
    currency: Optional[str] = "INR"
    temporal_scope: TemporalScope = TemporalScope.UNKNOWN
    period_reference: Optional[str] = None
    entity_scope: Optional[str] = None
    provenance_system: str = "UNKNOWN"
    provenance_version: str = "UNKNOWN"
    freshness_days: Optional[int] = None
    is_derived: bool = False
    derivation_basis: Optional[str] = None
    null_semantics: str = "NOT_APPLICABLE"

    def to_dict(self) -> dict:
        return {
            "field_name": self.field_name,
            "semantic_type": self.semantic_type.value,
            "value": self.value,
            "unit": self.unit,
            "currency": self.currency,
            "temporal_scope": self.temporal_scope.value,
            "period_reference": self.period_reference,
            "entity_scope": self.entity_scope,
            "provenance_system": self.provenance_system,
            "provenance_version": self.provenance_version,
            "freshness_days": self.freshness_days,
            "is_derived": self.is_derived,
            "derivation_basis": self.derivation_basis,
        }


@dataclass
class SemanticCheckReport:
    """Result of validating a semantic IR against a target contract field."""
    field_name: str
    result: SemanticCheckResult
    source_temporal_scope: Optional[str] = None
    target_temporal_scope: Optional[str] = None
    explanation: str = ""
    blocking: bool = False
    technical_code: str = ""

    def to_dict(self) -> dict:
        return {
            "field_name": self.field_name,
            "result": self.result.value,
            "source_temporal_scope": self.source_temporal_scope,
            "target_temporal_scope": self.target_temporal_scope,
            "explanation": self.explanation,
            "blocking": self.blocking,
            "technical_code": self.technical_code,
        }


class SemanticValidator:
    """
    Validates whether source semantic IR can safely satisfy a target contract field.
    Core rule: never silently convert or extrapolate unless transformation is
    explicitly authorized, proven, and assumption-free.
    """

    def validate_income_field(
        self,
        source: SemanticField,
        target_scope: TemporalScope,
        target_period_reference: Optional[str],
        authorized_transformations: list[str],
    ) -> SemanticCheckReport:
        """
        Validate that a source income field satisfies a target income requirement.
        Key: MONTHLY income CANNOT be silently multiplied to satisfy ANNUAL FY requirement.
        """
        if source.semantic_type != SemanticType.CURRENCY_AMOUNT:
            return SemanticCheckReport(
                field_name=source.field_name,
                result=SemanticCheckResult.TYPE_MISMATCH,
                explanation="Source field is not a currency amount.",
                blocking=True,
                technical_code="SEM-001-TYPE-MISMATCH",
            )

        # Direct temporal scope match
        if source.temporal_scope == target_scope:
            if target_scope == TemporalScope.FINANCIAL_YEAR_ANNUAL:
                if source.period_reference != target_period_reference:
                    return SemanticCheckReport(
                        field_name=source.field_name,
                        result=SemanticCheckResult.COVERAGE_GAP,
                        source_temporal_scope=source.temporal_scope.value,
                        target_temporal_scope=target_scope.value,
                        explanation=(
                            f"Source income covers period '{source.period_reference}' "
                            f"but target requires period '{target_period_reference}'. "
                            "Period coverage does not match."
                        ),
                        blocking=True,
                        technical_code="SEM-002-PERIOD-MISMATCH",
                    )
            return SemanticCheckReport(
                field_name=source.field_name,
                result=SemanticCheckResult.PASS,
                source_temporal_scope=source.temporal_scope.value,
                target_temporal_scope=target_scope.value,
                explanation="Temporal scope matches target requirement.",
                blocking=False,
            )

        # MONTHLY → FINANCIAL_YEAR_ANNUAL: this is the dangerous implicit conversion
        if (
            source.temporal_scope == TemporalScope.MONTHLY
            and target_scope == TemporalScope.FINANCIAL_YEAR_ANNUAL
        ):
            transformation_key = "MONTHLY_TO_ANNUAL_FY_MULTIPLY_12"
            if transformation_key in authorized_transformations:
                # Even if authorized, flag as derived
                return SemanticCheckReport(
                    field_name=source.field_name,
                    result=SemanticCheckResult.PASS,
                    source_temporal_scope=source.temporal_scope.value,
                    target_temporal_scope=target_scope.value,
                    explanation=(
                        "Authorized transformation applied: monthly × 12. "
                        "Result is a derived estimate, not actual annual figure. "
                        f"Assumes 12 equal months covering full FY {target_period_reference}."
                    ),
                    blocking=False,
                    technical_code="SEM-DERIVED-ESTIMATE",
                )
            # Not authorized → BLOCK
            return SemanticCheckReport(
                field_name=source.field_name,
                result=SemanticCheckResult.TEMPORAL_MISMATCH,
                source_temporal_scope=source.temporal_scope.value,
                target_temporal_scope=target_scope.value,
                explanation=(
                    "Transaction stopped: source provides MONTHLY income, "
                    "but the target contract requires ANNUAL financial-year income. "
                    "The conversion from monthly to annual (×12) is not an authorized transformation "
                    f"for this contract. It would require assuming 12 equal months covering "
                    f"the full financial year {target_period_reference}, which is not proven. "
                    "ISG does not automatically extrapolate financial figures."
                ),
                blocking=True,
                technical_code="SEM-003-TEMPORAL-MISMATCH-MONTHLY-TO-FY",
            )

        # ANNUAL → FINANCIAL_YEAR_ANNUAL (with period check)
        if (
            source.temporal_scope == TemporalScope.ANNUAL
            and target_scope == TemporalScope.FINANCIAL_YEAR_ANNUAL
        ):
            if source.period_reference != target_period_reference:
                return SemanticCheckReport(
                    field_name=source.field_name,
                    result=SemanticCheckResult.COVERAGE_GAP,
                    source_temporal_scope=source.temporal_scope.value,
                    target_temporal_scope=target_scope.value,
                    explanation=(
                        f"Source annual income covers '{source.period_reference}' "
                        f"but target financial year is '{target_period_reference}'. "
                        "Period reference does not match."
                    ),
                    blocking=True,
                    technical_code="SEM-004-FY-PERIOD-GAP",
                )
            return SemanticCheckReport(
                field_name=source.field_name,
                result=SemanticCheckResult.PASS,
                source_temporal_scope=source.temporal_scope.value,
                target_temporal_scope=target_scope.value,
                explanation="Annual income with matching financial year period.",
                blocking=False,
            )

        return SemanticCheckReport(
            field_name=source.field_name,
            result=SemanticCheckResult.MAPPING_AMBIGUOUS,
            source_temporal_scope=source.temporal_scope.value,
            target_temporal_scope=target_scope.value,
            explanation=(
                f"Cannot establish safe mapping from '{source.temporal_scope.value}' "
                f"to '{target_scope.value}'. No authorized transformation exists."
            ),
            blocking=True,
            technical_code="SEM-005-NO-SAFE-MAPPING",
        )

    def validate_enrollment_field(
        self, source: SemanticField, required_status: str
    ) -> SemanticCheckReport:
        if source.semantic_type != SemanticType.ENROLLMENT_STATUS:
            return SemanticCheckReport(
                field_name=source.field_name,
                result=SemanticCheckResult.TYPE_MISMATCH,
                explanation="Expected enrollment status field.",
                blocking=True,
                technical_code="SEM-006-TYPE-MISMATCH",
            )
        if source.value != required_status:
            return SemanticCheckReport(
                field_name=source.field_name,
                result=SemanticCheckResult.COVERAGE_GAP,
                explanation=f"Enrollment status is '{source.value}', not '{required_status}'.",
                blocking=True,
                technical_code="SEM-007-ENROLLMENT-STATUS-FAIL",
            )
        return SemanticCheckReport(
            field_name=source.field_name,
            result=SemanticCheckResult.PASS,
            explanation=f"Enrollment status '{source.value}' satisfies requirement.",
            blocking=False,
        )


def compute_semantic_ir_hash(fields: list[SemanticField]) -> str:
    data = json.dumps([f.to_dict() for f in fields], sort_keys=True)
    return hashlib.sha256(data.encode()).hexdigest()[:16]
