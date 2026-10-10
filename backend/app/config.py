"""
config.py — the ONLY place environment variables are read in the entire application.

All other modules import `get_settings()` from here. Never import `os.environ` or
`os.getenv` directly anywhere else in the codebase.
"""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_BACKEND_DIR = Path(__file__).resolve().parent.parent
_REPO_ROOT = _BACKEND_DIR.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(_REPO_ROOT / ".env", _BACKEND_DIR / ".env", ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Core ────────────────────────────────────────────────────────────────
    environment: Literal["local", "staging", "production"] = "local"
    log_level: str = "INFO"
    api_base_url: str = ""
    frontend_url: str = ""
    secret_key: str = ""

    # ── Database ─────────────────────────────────────────────────────────────
    database_url: str = ""
    database_pool_size: int = 20
    database_max_overflow: int = 10

    # ── Redis ─────────────────────────────────────────────────────────────────
    redis_url: str = ""
    celery_broker_url: str = ""
    celery_result_backend: str = ""

    # ── Auth (Self-Contained JWT & Clerk) ─────────────────────────────────────
    jwt_secret: str = ""
    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = 1440  # 24 hours
    clerk_secret_key: str = ""
    clerk_publishable_key: str = ""
    next_public_clerk_publishable_key: str = ""
    clerk_jwks_url: str = ""
    clerk_webhook_secret: str = ""
    auth_issuer: str = ""
    auth_audience: str = ""

    # ── LLM ──────────────────────────────────────────────────────────────────
    llm_provider: str = ""
    gemini_api_key: str = ""
    google_api_key: str = ""
    gemini_base_url: str = ""
    anthropic_api_key: str = ""
    anthropic_base_url: str = ""
    openai_api_key: str = ""
    openai_base_url: str = ""
    llm_model_extraction: str = ""
    llm_model_classification: str = ""
    llm_model_entity_resolution: str = ""
    llm_model_explanation: str = ""
    llm_model_investigation: str = ""
    llm_max_retries: int = 2
    llm_timeout_seconds: int = 60
    default_monthly_token_budget: int = 5_000_000

    embedding_provider: str = ""
    embedding_api_key: str = ""
    embedding_model: str = ""
    embedding_dimensions: int = 1024

    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_host: str = ""

    # ── External data sources ─────────────────────────────────────────────────
    data_gov_in_api_key: str = ""
    gdelt_user_agent: str = ""
    gdelt_min_request_interval_seconds: int = 6
    ofac_sls_base_url: str = ""
    federal_register_base_url: str = ""
    gleif_base_url: str = ""
    eu_sanctions_token: str = ""
    eurlex_ws_username: str = ""
    eurlex_ws_password: str = ""

    # Price intelligence sources (Phase 14b)
    fred_api_key: str = ""
    ecb_fx_base_url: str = ""
    world_bank_api_base_url: str = ""

    # ── Storage (AWS) ─────────────────────────────────────────────────────────
    aws_region: str = ""
    s3_bucket_documents: str = ""
    s3_bucket_raw_payloads: str = ""
    s3_bucket_exports: str = ""

    # ── Email / chat ──────────────────────────────────────────────────────────
    email_provider: str = ""
    email_provider_api_key: str = ""
    email_from_address: str = ""
    slack_client_id: str = ""
    slack_client_secret: str = ""
    teams_app_id: str = ""
    teams_app_password: str = ""

    # ── Observability ─────────────────────────────────────────────────────────
    sentry_dsn: str = ""
    otel_exporter_otlp_endpoint: str = ""
    otel_service_name: str = ""

    # ── Security ─────────────────────────────────────────────────────────────
    encryption_key: str = ""
    allowed_origins: str = ""
    rate_limit_per_user_hour: int = 1000
    max_upload_size_mb: int = 25
    clamav_host: str = ""

    @field_validator("log_level")
    @classmethod
    def _upper_log_level(cls, v: str) -> str:
        return v.upper()

    @property
    def allowed_origins_list(self) -> list[str]:
        if not self.allowed_origins:
            return []
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the singleton Settings instance. Cached after first call."""
    return Settings()
