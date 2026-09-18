"""
Maharashtra Education/Enrollment System Simulator.
Uses completely different schema from Revenue — student-centric, not family-centric.
This is NOT a real government system — prototype simulation only.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
from enum import Enum
import asyncio
import time


class EducationFetchResult(str, Enum):
    FOUND = "FOUND"
    NOT_FOUND = "NOT_FOUND"
    TIMEOUT = "TIMEOUT"
    SYSTEM_ERROR = "SYSTEM_ERROR"


# Education system uses student_name + birth_date as primary key (not family_id)
# Completely different schema from Revenue system
EDUCATION_RECORDS = {
    "EDU-1001": {
        "student_id": "EDU-1001",
        "student_name": "Priya Sharma",          # Full name (Revenue used abbreviated)
        "birth_date": "2005-08-14",              # Different key name from Identity (uses dob)
        "course_code": "BE-ECE",
        "course_name": "Bachelor of Engineering – Electronics & Communication",
        "institution_code": "MH-PUN-042",
        "institution_name": "COEP Technological University",
        "enrollment": "ACTIVE",
        "enrollment_year": "2023",
        "academic_year": "2025-26",
        "source": "EDUCATION_DEPT_MH",
        "source_version": "v3.1",
        "last_verified": "2026-07-01",
    },
    "EDU-1002": {
        "student_id": "EDU-1002",
        "student_name": "Aditya Kulkarni",
        "birth_date": "2004-03-22",
        "course_code": "ME-MECH",
        "course_name": "Master of Engineering – Mechanical",
        "institution_code": "MH-PUN-041",
        "institution_name": "College of Engineering Pune",
        "enrollment": "ACTIVE",
        "enrollment_year": "2024",
        "academic_year": "2025-26",
        "source": "EDUCATION_DEPT_MH",
        "source_version": "v3.1",
        "last_verified": "2026-07-15",
    },
    # Identity conflict case — Ravi Kumar with DOB 2004-05-12
    "EDU-2001": {
        "student_id": "EDU-2001",
        "student_name": "Ravi Kumar",
        "birth_date": "2004-05-12",
        "course_code": "BE-CS",
        "course_name": "Bachelor of Engineering – Computer Science",
        "institution_code": "MH-MUM-011",
        "institution_name": "VJTI Mumbai",
        "enrollment": "ACTIVE",
        "enrollment_year": "2022",
        "academic_year": "2025-26",
        "source": "EDUCATION_DEPT_MH",
        "source_version": "v3.1",
        "last_verified": "2026-07-20",
    },
    # Policy/consent case
    "EDU-3001": {
        "student_id": "EDU-3001",
        "student_name": "Sunita Patil",
        "birth_date": "2006-02-28",
        "course_code": "BA-ECON",
        "course_name": "Bachelor of Arts – Economics",
        "institution_code": "MH-NAG-005",
        "institution_name": "RTM Nagpur University",
        "enrollment": "ACTIVE",
        "enrollment_year": "2024",
        "academic_year": "2025-26",
        "source": "EDUCATION_DEPT_MH",
        "source_version": "v3.1",
        "last_verified": "2026-07-01",
    },
    # Failure/recovery case
    "EDU-4001": {
        "student_id": "EDU-4001",
        "student_name": "Vikram Rathod",
        "birth_date": "2003-07-19",
        "course_code": "BE-CIVIL",
        "course_name": "Bachelor of Engineering – Civil",
        "institution_code": "MH-AUR-009",
        "institution_name": "GECA Aurangabad",
        "enrollment": "ACTIVE",
        "enrollment_year": "2021",
        "academic_year": "2025-26",
        "source": "EDUCATION_DEPT_MH",
        "source_version": "v3.1",
        "last_verified": "2026-07-20",
    },
    "EDU-1003": {
        "student_id": "EDU-1003",
        "student_name": "Meera Joshi",
        "birth_date": "2005-12-05",
        "course_code": "BSC-PHY",
        "course_name": "Bachelor of Science – Physics",
        "institution_code": "MH-PUN-050",
        "institution_name": "Savitribai Phule Pune University",
        "enrollment": "ACTIVE",
        "enrollment_year": "2023",
        "academic_year": "2025-26",
        "source": "EDUCATION_DEPT_MH",
        "source_version": "v3.1",
        "last_verified": "2026-07-05",
    },
}


@dataclass
class EducationResponse:
    result: EducationFetchResult
    data: Optional[dict] = None
    error: Optional[str] = None
    response_time_ms: int = 0
    system_name: str = "EDUCATION_SYSTEM_MH_v3.1"
    schema_version: str = "edu-schema-v3.1"


async def fetch_enrollment_record(student_id: str) -> EducationResponse:
    """
    Simulate fetching from the Education System.
    Returns education system's own schema — different from Revenue and Identity.
    """
    start = time.monotonic()
    await asyncio.sleep(0.08)  # simulate latency

    record = EDUCATION_RECORDS.get(student_id)
    elapsed = int((time.monotonic() - start) * 1000)

    if not record:
        return EducationResponse(
            result=EducationFetchResult.NOT_FOUND,
            error=f"No enrollment record found for student_id='{student_id}'.",
            response_time_ms=elapsed,
        )

    return EducationResponse(
        result=EducationFetchResult.FOUND,
        data=record,
        response_time_ms=elapsed,
    )
