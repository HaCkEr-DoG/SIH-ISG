"""
System Passport Registry.
Each government system connected to ISG must have a passport declaring
its capabilities, schema, and data authority.
ISG validates passports before permitting interoperability.
"""
from __future__ import annotations
from dataclasses import dataclass
import hashlib


@dataclass
class SystemCapabilities:
    read: bool = False
    write: bool = False
    idempotency: bool = False
    status_check: bool = False
    rollback: bool = False


@dataclass
class SystemPassport:
    system_id: str
    name: str
    owner: str
    interface: str
    schema_version: str
    schema_hash: str
    capabilities: SystemCapabilities
    data_authority: str
    status: str
    description: str
    id_scheme: str
    sample_fields: list
    color: str

    def to_dict(self) -> dict:
        return {
            "system_id": self.system_id,
            "name": self.name,
            "owner": self.owner,
            "interface": self.interface,
            "schema_version": self.schema_version,
            "schema_hash": self.schema_hash,
            "capabilities": {
                "READ": self.capabilities.read,
                "WRITE": self.capabilities.write,
                "IDEMPOTENCY": self.capabilities.idempotency,
                "STATUS_CHECK": self.capabilities.status_check,
                "ROLLBACK": self.capabilities.rollback,
            },
            "data_authority": self.data_authority,
            "status": self.status,
            "description": self.description,
            "id_scheme": self.id_scheme,
            "sample_fields": self.sample_fields,
            "color": self.color,
        }


PASSPORT_REGISTRY: dict[str, SystemPassport] = {
    "REV-001": SystemPassport(
        system_id="REV-001",
        name="Revenue System",
        owner="Revenue Department, Maharashtra",
        interface="REST / OpenAPI",
        schema_version="v2.7",
        schema_hash=hashlib.sha256(b"revenue-schema-v2.7-mh").hexdigest()[:16],
        capabilities=SystemCapabilities(read=True, write=False, idempotency=True, status_check=True, rollback=False),
        data_authority="Revenue Department",
        status="ACTIVE",
        description="Family income and tax assessment records. Primary key: family_id (FAM-xxxx). "
                    "Provides income evidence for welfare schemes. Data in INR; period may vary — "
                    "ISG must validate temporal scope before use.",
        id_scheme="family_id (FAM-xxxx)",
        sample_fields=["family_id", "beneficiary_name", "income_value", "income_period",
                       "period_reference", "currency", "assessed_date", "assessment_type"],
        color="#1e3a5f",
    ),
    "EDU-001": SystemPassport(
        system_id="EDU-001",
        name="Education System",
        owner="Education Department, Maharashtra",
        interface="REST / OpenAPI",
        schema_version="v3.1",
        schema_hash=hashlib.sha256(b"education-schema-v3.1-mh").hexdigest()[:16],
        capabilities=SystemCapabilities(read=True, write=False, idempotency=True, status_check=True, rollback=False),
        data_authority="Education Department",
        status="ACTIVE",
        description="Student enrollment and academic records. Primary key: student_id (EDU-xxxx). "
                    "Uses birth_date (not dob) — field-name diverges from Identity System. "
                    "ISG maps these semantically via contract.",
        id_scheme="student_id (EDU-xxxx)",
        sample_fields=["student_id", "student_name", "birth_date", "course_code",
                       "course_name", "enrollment", "academic_year", "institution_code", "last_verified"],
        color="#14532d",
    ),
    "IDN-001": SystemPassport(
        system_id="IDN-001",
        name="Identity System",
        owner="UIDAI Proxy — Maharashtra",
        interface="REST / OpenAPI",
        schema_version="v1.5",
        schema_hash=hashlib.sha256(b"identity-schema-v1.5-uidai").hexdigest()[:16],
        capabilities=SystemCapabilities(read=True, write=False, idempotency=True, status_check=True, rollback=False),
        data_authority="UIDAI / Identity Authority",
        status="ACTIVE",
        description="Citizen identity verification via Aadhaar-linked proxy. Returns candidate sets — "
                    "may return multiple candidates for the same query. ISG runs consequence-aware "
                    "identity resolution to select the correct citizen.",
        id_scheme="identity_ref (ID-xxxx)",
        sample_fields=["identity_ref", "name", "dob", "verification_status",
                       "evidence_type", "identity_provider", "last_verified"],
        color="#312e81",
    ),
    "SCH-001": SystemPassport(
        system_id="SCH-001",
        name="Scholarship System",
        owner="Social Welfare Dept., Maharashtra",
        interface="REST / OpenAPI",
        schema_version="v1.2",
        schema_hash=hashlib.sha256(b"scholarship-schema-v1.2-sw").hexdigest()[:16],
        capabilities=SystemCapabilities(read=True, write=True, idempotency=True, status_check=True, rollback=True),
        data_authority="Social Welfare Department",
        status="ACTIVE",
        description="Scholarship eligibility and disbursement. Effect target — ISG writes eligibility "
                    "decisions here only after all safety checks pass and an authorization lease is "
                    "issued. Supports idempotent writes and rollback.",
        id_scheme="application_id (APP-xxxx)",
        sample_fields=["application_id", "applicant_name", "eligibility_status",
                       "scheme_code", "annual_family_income", "enrollment_status", "disbursement_ref"],
        color="#7c3aed",
    ),
}
