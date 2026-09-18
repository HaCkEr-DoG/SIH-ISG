"""
Interoperability Contract Registry.
Contracts are executable governance artifacts specifying exactly what data
may flow between which systems, under what conditions, and with what effects.
ISG enforces contracts at every pipeline stage.
"""
from __future__ import annotations
from dataclasses import dataclass


@dataclass
class FreshnessRule:
    field: str
    max_days: int
    reason: str


@dataclass
class FieldMapping:
    source_field: str
    target_field: str
    source_period: str
    target_period: str
    requires_transformation: bool
    transformation_authorized: bool
    note: str


@dataclass
class Contract:
    contract_id: str
    version: int
    source_system_id: str
    source_system_name: str
    target_system_id: str
    target_system_name: str
    purpose: str
    allowed_data_fields: list
    identity_requirement: str
    freshness_rules: list
    consent_required: bool
    allowed_effect: str
    policy_id: str
    policy_version: str
    status: str
    effective_from: str
    description: str
    field_mappings: list

    def to_dict(self) -> dict:
        return {
            "contract_id": self.contract_id,
            "version": self.version,
            "source_system_id": self.source_system_id,
            "source_system_name": self.source_system_name,
            "target_system_id": self.target_system_id,
            "target_system_name": self.target_system_name,
            "purpose": self.purpose,
            "allowed_data_fields": self.allowed_data_fields,
            "identity_requirement": self.identity_requirement,
            "freshness_rules": [
                {"field": r.field, "max_days": r.max_days, "reason": r.reason}
                for r in self.freshness_rules
            ],
            "consent_required": self.consent_required,
            "allowed_effect": self.allowed_effect,
            "policy_id": self.policy_id,
            "policy_version": self.policy_version,
            "status": self.status,
            "effective_from": self.effective_from,
            "description": self.description,
            "field_mappings": [
                {
                    "source_field": m.source_field,
                    "target_field": m.target_field,
                    "source_period": m.source_period,
                    "target_period": m.target_period,
                    "requires_transformation": m.requires_transformation,
                    "transformation_authorized": m.transformation_authorized,
                    "note": m.note,
                }
                for m in self.field_mappings
            ],
        }


CONTRACT_REGISTRY: dict[str, Contract] = {
    "C-017": Contract(
        contract_id="C-017",
        version=7,
        source_system_id="REV-001",
        source_system_name="Revenue System",
        target_system_id="SCH-001",
        target_system_name="Scholarship System",
        purpose="SCHOLARSHIP_ELIGIBILITY_CHECK",
        allowed_data_fields=["income_value", "income_period", "period_reference"],
        identity_requirement="VERIFIED_CITIZEN",
        freshness_rules=[
            FreshnessRule(
                field="income",
                max_days=365,
                reason="Income data must be from the current financial year."
            )
        ],
        consent_required=True,
        allowed_effect="ELIGIBILITY_VERIFICATION_WRITE",
        policy_id="POL-SCH-MH-001",
        policy_version="v1.2",
        status="ACTIVE",
        effective_from="2024-04-01",
        description=(
            "Revenue Department → Scholarship System. "
            "Annual family income for Maharashtra scholarship eligibility. "
            "Only FINANCIAL_YEAR_ANNUAL period data accepted. "
            "Monthly income NOT authorized for extrapolation."
        ),
        field_mappings=[
            FieldMapping(
                source_field="income_value",
                target_field="annual_family_income",
                source_period="FINANCIAL_YEAR_ANNUAL",
                target_period="FINANCIAL_YEAR_ANNUAL",
                requires_transformation=False,
                transformation_authorized=False,
                note="Direct mapping only when income_period = ANNUAL and period_reference contains 'FY'. "
                     "Monthly→Annual conversion is NOT authorized by this contract."
            )
        ],
    ),
    "C-018": Contract(
        contract_id="C-018",
        version=3,
        source_system_id="EDU-001",
        source_system_name="Education System",
        target_system_id="SCH-001",
        target_system_name="Scholarship System",
        purpose="SCHOLARSHIP_ELIGIBILITY_CHECK",
        allowed_data_fields=["enrollment", "course_code", "academic_year"],
        identity_requirement="VERIFIED_CITIZEN",
        freshness_rules=[
            FreshnessRule(
                field="enrollment",
                max_days=180,
                reason="Enrollment status must be verified within the current academic semester."
            )
        ],
        consent_required=True,
        allowed_effect="ELIGIBILITY_VERIFICATION_WRITE",
        policy_id="POL-SCH-MH-001",
        policy_version="v1.2",
        status="ACTIVE",
        effective_from="2024-04-01",
        description=(
            "Education Department → Scholarship System. "
            "Student enrollment status for scholarship eligibility. "
            "enrollment must be ACTIVE. Note: Education System uses 'birth_date' "
            "while Identity System uses 'dob' — ISG handles field-name divergence."
        ),
        field_mappings=[
            FieldMapping(
                source_field="enrollment",
                target_field="enrollment_status",
                source_period="POINT_IN_TIME",
                target_period="POINT_IN_TIME",
                requires_transformation=False,
                transformation_authorized=True,
                note="Direct mapping. Value must be ACTIVE. "
                     "Field birth_date (Education) ≠ dob (Identity): same semantic, different key name."
            )
        ],
    ),
    "C-019": Contract(
        contract_id="C-019",
        version=2,
        source_system_id="IDN-001",
        source_system_name="Identity System",
        target_system_id="SCH-001",
        target_system_name="Scholarship System",
        purpose="SCHOLARSHIP_ELIGIBILITY_CHECK",
        allowed_data_fields=["verification_status", "identity_ref"],
        identity_requirement="VERIFIED_CITIZEN",
        freshness_rules=[
            FreshnessRule(
                field="identity",
                max_days=365,
                reason="Identity verification must be within one year."
            )
        ],
        consent_required=True,
        allowed_effect="ELIGIBILITY_VERIFICATION_WRITE",
        policy_id="POL-SCH-MH-001",
        policy_version="v1.2",
        status="ACTIVE",
        effective_from="2024-04-01",
        description=(
            "Identity System → Scholarship System. "
            "Citizen identity verification for scholarship. "
            "May return multiple candidates — ISG runs consequence-aware resolution. "
            "Ambiguous identity (name collision + DOB conflict) → QUARANTINE."
        ),
        field_mappings=[
            FieldMapping(
                source_field="verification_status",
                target_field="identity_verified",
                source_period="POINT_IN_TIME",
                target_period="POINT_IN_TIME",
                requires_transformation=False,
                transformation_authorized=True,
                note="Must be VERIFIED. UNVERIFIED or DISPUTED → QUARANTINE."
            )
        ],
    ),
}
