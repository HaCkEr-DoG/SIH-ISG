"""
Seed data for ISG prototype — synthetic data only.
Covers all 7 demo scenarios deterministically.
"""
from datetime import datetime, timezone, timedelta
import uuid
import hashlib
import json

from sqlalchemy.orm import Session
from models import (
    ScholarshipApplication, ConsentRecord, PolicyRecord,
    ContractRecord,
)


def seed_all(db: Session):
    if db.query(PolicyRecord).count() > 0:
        return  # already seeded

    _seed_policy(db)
    _seed_contract(db)
    _seed_applications(db)
    _seed_consents(db)
    db.commit()
    print("✓ Seed data loaded.")


def _seed_policy(db: Session):
    policy_data = {
        "policy_id": "POL-SCH-MH-001",
        "version": "1.2",
        "purpose": "SCHOLARSHIP_ELIGIBILITY_CHECK",
        "allowed_data": ["income", "enrollment", "identity"],
        "roles": ["SCHOLARSHIP_PORTAL", "REVENUE_DEPT", "EDUCATION_DEPT", "IDENTITY_SYSTEM"],
        "legal_basis": "Maharashtra_Scholarship_Rules_2019",
        "consent_required": True,
        "risk_level": "MEDIUM",
        "status": "ACTIVE",
    }
    policy_hash = hashlib.sha256(json.dumps(policy_data, sort_keys=True).encode()).hexdigest()[:16]

    db.add(PolicyRecord(
        id=str(uuid.uuid4()),
        policy_id=policy_data["policy_id"],
        version=policy_data["version"],
        purpose=policy_data["purpose"],
        allowed_data=policy_data["allowed_data"],
        roles=policy_data["roles"],
        legal_basis=policy_data["legal_basis"],
        consent_required=policy_data["consent_required"],
        risk_level=policy_data["risk_level"],
        effective_from=datetime(2024, 4, 1, tzinfo=timezone.utc),
        effective_until=None,
        status="ACTIVE",
        policy_hash=policy_hash,
    ))


def _seed_contract(db: Session):
    mapping = {
        "revenue.income_value + income_period": "annual_family_income (requires ANNUAL FY)",
        "education.enrollment": "enrollment_status (ACTIVE required)",
        "identity.name + dob": "verified_student_identity",
    }
    contract_hash = hashlib.sha256(json.dumps(mapping, sort_keys=True).encode()).hexdigest()[:16]

    db.add(ContractRecord(
        id=str(uuid.uuid4()),
        contract_id="SCH-MH-001",
        version="1.0",
        source_system="SCHOLARSHIP_PORTAL",
        target_system="SCHOLARSHIP_DISBURSEMENT_SYSTEM",
        purpose="SCHOLARSHIP_ELIGIBILITY_CHECK",
        semantic_mapping=mapping,
        preconditions=["consent_valid", "identity_verified", "enrollment_active"],
        postconditions=["eligibility_record_created"],
        assumptions=["no_unauthorized_monthly_to_annual_conversion"],
        compiler_version="ISG-1.0",
        vocabulary_version="SCH-VOCAB-1.0",
        status="ACTIVE",
        contract_hash=contract_hash,
        activated_at=datetime(2024, 4, 1, tzinfo=timezone.utc),
    ))


APPLICATIONS = [
    # SCENARIO 1 — VALID: Priya Sharma
    {"id": "APP-1001", "applicant_name": "Priya Sharma", "applicant_dob": "2005-08-14",
     "applicant_id_ref": "ID-1001", "course": "BE-ECE", "family_id": "FAM-1001"},

    # SCENARIO 2 — SEMANTIC ATTACK: Ravi Kumar (monthly income)
    {"id": "APP-2001", "applicant_name": "Ravi Kumar", "applicant_dob": "2004-05-12",
     "applicant_id_ref": "ID-2001", "course": "BE-CS", "family_id": "FAM-2001"},

    # SCENARIO 3 — IDENTITY ATTACK: Ravi Kumar (DOB conflict)
    {"id": "APP-2002", "applicant_name": "Ravi Kumar", "applicant_dob": "2005-05-12",
     "applicant_id_ref": "ID-2001", "course": "BE-CS", "family_id": "FAM-1001"},

    # SCENARIO 4 — CONSENT/POLICY: Sunita Patil (consent will be revoked mid-flow)
    {"id": "APP-3001", "applicant_name": "Sunita Patil", "applicant_dob": "2006-02-28",
     "applicant_id_ref": "ID-3001", "course": "BA-ECON", "family_id": "FAM-3001"},

    # SCENARIO 5 — TIMEOUT/RECOVERY: Vikram Rathod
    {"id": "APP-4001", "applicant_name": "Vikram Rathod", "applicant_dob": "2003-07-19",
     "applicant_id_ref": "ID-4001", "course": "BE-CIVIL", "family_id": "FAM-4001"},

    # Additional valid cases
    {"id": "APP-1002", "applicant_name": "Aditya Kulkarni", "applicant_dob": "2004-03-22",
     "applicant_id_ref": "ID-1002", "course": "ME-MECH", "family_id": "FAM-1002"},
    {"id": "APP-1003", "applicant_name": "Meera Joshi", "applicant_dob": "2005-12-05",
     "applicant_id_ref": "ID-1003", "course": "BSC-PHY", "family_id": "FAM-1003"},
]


def _seed_applications(db: Session):
    for a in APPLICATIONS:
        if not db.query(ScholarshipApplication).filter_by(id=a["id"]).first():
            db.add(ScholarshipApplication(
                id=a["id"],
                applicant_name=a["applicant_name"],
                applicant_dob=a["applicant_dob"],
                applicant_id_ref=a["applicant_id_ref"],
                course=a["course"],
                family_id=a["family_id"],
                purpose="SCHOLARSHIP_ELIGIBILITY_CHECK",
                consent_given=True,
            ))


def _seed_consents(db: Session):
    now = datetime.now(timezone.utc)
    for a in APPLICATIONS:
        if not db.query(ConsentRecord).filter_by(application_id=a["id"]).first():
            db.add(ConsentRecord(
                id=str(uuid.uuid4()),
                citizen_id=a["applicant_id_ref"],
                application_id=a["id"],
                purpose="SCHOLARSHIP_ELIGIBILITY_CHECK",
                granted_at=now - timedelta(hours=1),
                expires_at=now + timedelta(days=30),
                revoked=False,
            ))
