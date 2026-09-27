"""
config.py — the ONLY place environment variables are read in the entire application.

All other modules import `get_settings()` from here. Never import `os.environ` or
`os.getenv` directly anywhere else in the codebase.
"""

from functools import lru_cache
from typing import Literal

from pydantic import AnyUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Core ────────────────────────────────────────────────────────────────
    environment: Literal["local", "staging", "production"] = "local"
    log_level: str = "INFO"
    api_base_url: str = "http://localhost:8000"
    frontend_url: str = "http://localhost:3000"
    secret_key: str = "change-me-in-production"

    # ── Database ─────────────────────────────────────────────────────────────
    database_url: str = (
        "postgresql+asyncpg://provenance:provenance@localhost:5432/provenance"
    )
    database_pool_size: int = 20
    database_max_overflow: int = 10

    # ── Redis ─────────────────────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # ── Auth (Clerk) ──────────────────────────────────────────────────────────
    clerk_secret_key: str = ""
    clerk_publishable_key: str = ""
    clerk_jwks_url: str = ""
    clerk_webhook_secret: str = ""
    auth_issuer: str = ""
    auth_audience: str = ""

    # ── LLM ──────────────────────────────────────────────────────────────────
    llm_provider: str = "anthropic"
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    llm_model_extraction: str = "claude-3-5-sonnet-20241022"
    llm_model_classification: str = "claude-3-haiku-20240307"
    llm_model_explanation: str = "claude-3-5-sonnet-20241022"
    llm_model_investigation: str = "claude-3-5-sonnet-20241022"
    llm_max_retries: int = 2
    llm_timeout_seconds: int = 60
    default_monthly_token_budget: int = 5_000_000

    embedding_provider: str = "voyage"
    embedding_api_key: str = ""
    embedding_model: str = "voyage-3"
    embedding_dimensions: int = 1024

    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_host: str = "https://cloud.langfuse.com"

    # ── External data sources ─────────────────────────────────────────────────
    data_gov_in_api_key: str = ""
    gdelt_user_agent: str = "Provenance/1.0 (supply-chain-risk; contact@provenance.app)"
    gdelt_min_request_interval_seconds: int = 6
    ofac_sls_base_url: str = "https://sanctionslistservice.ofac.treas.gov"
    federal_register_base_url: str = "https://www.federalregister.gov/api/v1"
    gleif_base_url: str = "https://api.gleif.org/api/v1"
    eu_sanctions_token: str = ""
    eurlex_ws_username: str = ""
    eurlex_ws_password: str = ""

    # Price intelligence sources (Phase 14b)
    fred_api_key: str = ""
    ecb_fx_base_url: str = "https://data-api.ecb.europa.eu"
    world_bank_api_base_url: str = "https://api.worldbank.org/v2"

    # ── Storage (AWS) ─────────────────────────────────────────────────────────
    aws_region: str = "ap-south-1"
    s3_bucket_documents: str = "provenance-documents-local"
    s3_bucket_raw_payloads: str = "provenance-raw-payloads-local"
    s3_bucket_exports: str = "provenance-exports-local"

    # ── Email / chat ──────────────────────────────────────────────────────────
    email_provider: str = "resend"
    email_provider_api_key: str = ""
    email_from_address: str = "noreply@provenance.app"
    slack_client_id: str = ""
    slack_client_secret: str = ""
    teams_app_id: str = ""
    teams_app_password: str = ""

    # ── Observability ─────────────────────────────────────────────────────────
    sentry_dsn: str = ""
    otel_exporter_otlp_endpoint: str = ""
    otel_service_name: str = "provenance-api"

    # ── Security ─────────────────────────────────────────────────────────────
    encryption_key: str = ""
    allowed_origins: str = "http://localhost:3000"
    rate_limit_per_user_hour: int = 1000
    max_upload_size_mb: int = 25
    clamav_host: str = ""

    @field_validator("log_level")
    @classmethod
    def _upper_log_level(cls, v: str) -> str:
        return v.upper()

    @property
    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the singleton Settings instance. Cached after first call."""
    return Settings()
