from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from functools import lru_cache
import os


class Settings(BaseSettings):
    model_config = ConfigDict(env_file=".env")

    # Default to SQLite for local demo; override with DATABASE_URL for Docker/Postgres
    database_url: str = "sqlite:///./isg_demo.db"
    secret_key: str = "isg-demo-key-sih2026-change-in-prod"
    demo_api_key: str = "isg-demo-token-sih2026"
    allowed_origins: str = "http://localhost:3000"
    debug: bool = False
    isg_version: str = "1.0.0-prototype"
    environment: str = "demo"

    # DigiLocker API (income / ITR pull)
    digilocker_client_id: str = ""
    digilocker_client_secret: str = ""
    digilocker_sandbox: bool = True
    digilocker_redirect_uri: str = "http://localhost:8000/api/citizen/digilocker/callback"

    # UIDAI Aadhaar (demographic verification)
    uidai_aua_code: str = ""
    uidai_api_key: str = ""
    uidai_sandbox: bool = True

    identity_match_threshold_high_consequence: float = 0.95
    identity_match_threshold_low_consequence: float = 0.80
    lease_ttl_seconds: int = 300
    max_external_calls: int = 10
    max_retry_attempts: int = 3
    max_correction_depth: int = 3
    max_compensation_depth: int = 3


@lru_cache()
def get_settings() -> Settings:
    return Settings()
