from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from functools import lru_cache
import os


class Settings(BaseSettings):
    model_config = ConfigDict(env_file=".env")

    # Default to SQLite for local demo; override with DATABASE_URL for Docker/Postgres
    database_url: str = "sqlite:///./isg_demo.db"
    secret_key: str = "isg-prototype-secret-key-2026-sih"
    debug: bool = True
    isg_version: str = "1.0.0-prototype"
    environment: str = "demo"

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
