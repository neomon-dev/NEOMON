import os
from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


_BACKEND_DIR = Path(__file__).resolve().parents[1]
_RECOVERED_DB = _BACKEND_DIR / "backups" / "recovery_experiments" / "neomon_recovered.db"
DEFAULT_DATABASE_PATH = _RECOVERED_DB if _RECOVERED_DB.exists() else _BACKEND_DIR / "neomon.db"
DEFAULT_DATABASE_URL = f"sqlite+aiosqlite:///{DEFAULT_DATABASE_PATH.as_posix()}"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_prefix="NEOMON_",
        extra="ignore",
    )

    app_name: str = "NEOMON API"
    environment: str = "development"
    debug: bool = False
    port: int = Field(default=8001, ge=1, le=65535)
    api_version: str = "v1"
    database_url: str = DEFAULT_DATABASE_URL
    allowed_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:3000", "http://127.0.0.1:3000"]
    )
    allowed_local_provider_hosts: list[str] = Field(
        default_factory=lambda: ["localhost", "127.0.0.1", "::1"]
    )
    demo_mode: bool = True
    request_timeout_seconds: float = Field(default=15.0, gt=0, le=120)
    local_inference_timeout_seconds: float = Field(default=300.0, gt=0, le=1800)
    provider_queue_wait_timeout_seconds: float = Field(default=600.0, gt=0, le=3600)
    provider_queue_max_size: int = Field(default=50, ge=1, le=500)
    analysis_overall_timeout_seconds: float = Field(default=1800.0, gt=0, le=7200)
    local_provider_max_concurrency: int = Field(default=1, ge=1, le=10)
    remote_provider_max_concurrency: int = Field(default=4, ge=1, le=20)
    provider_retry_count: int = Field(default=2, ge=0, le=5)

    # Production Database Configuration
    database_pool_size: int = Field(default=10, ge=1, le=50)
    database_max_overflow: int = Field(default=20, ge=0, le=50)
    database_pool_timeout: float = Field(default=30.0, gt=0, le=120)
    database_pool_recycle: int = Field(default=1800, ge=60, le=7200)
    database_pool_pre_ping: bool = True

    # Redis and Caching
    redis_url: str | None = None
    cache_default_ttl_seconds: int = Field(default=300, ge=1, le=86400)

    # Background Job Worker
    worker_enabled: bool = True
    worker_concurrency: int = Field(default=4, ge=1, le=16)
    worker_poll_interval_seconds: float = Field(default=1.0, gt=0.1, le=10.0)
    worker_graceful_shutdown_timeout: float = Field(default=15.0, gt=1.0, le=60.0)
    job_heartbeat_timeout_seconds: int = Field(default=120, ge=30, le=600)

    @property
    def worker_poll_interval(self) -> float:
        return self.worker_poll_interval_seconds

    @property
    def rate_limit_general_rpm(self) -> int:
        return self.rate_limit_default_rpm

    # Rate Limiting
    rate_limit_enabled: bool = True
    rate_limit_auth_rpm: int = Field(default=10, ge=1, le=120)
    rate_limit_research_rpm: int = Field(default=30, ge=1, le=300)
    rate_limit_export_rpm: int = Field(default=20, ge=1, le=200)
    rate_limit_default_rpm: int = Field(default=120, ge=1, le=1000)
    trusted_proxies: list[str] = Field(default_factory=lambda: ["127.0.0.1", "::1"])

    # Observability & Logging
    log_level: str = "INFO"
    log_format: str = "auto"  # "auto", "json", "human"

    # Tavily Search Provider Configuration
    tavily_api_key: str | None = None
    tavily_enabled: bool = True
    tavily_search_depth: str = "advanced"  # "basic" or "advanced"
    tavily_max_results: int = Field(default=10, ge=1, le=20)
    tavily_include_domains: list[str] = Field(default_factory=list)
    tavily_exclude_domains: list[str] = Field(default_factory=list)
    tavily_request_timeout_seconds: float = Field(default=20.0, gt=0, le=120)

    unpaywall_email: str | None = None
    unpaywall_api_key: str | None = None
    research_user_agent: str = "NEOMON/0.3 (+https://github.com/neomon-dev/NEOMON)"
    research_max_document_bytes: int = Field(default=5_000_000, ge=100_000, le=50_000_000)
    initial_admin_password: str | None = None

    # n8n Automation Integration
    n8n_webhook_url: str | None = None
    n8n_api_key: str | None = None
    n8n_service_token: str | None = None

    @field_validator("database_url", mode="before")
    @classmethod
    def resolve_and_normalize_database_url(cls, value: object) -> object:
        # Honor standard DATABASE_URL environment variable if NEOMON_DATABASE_URL was not set
        if not os.environ.get("NEOMON_DATABASE_URL") and os.environ.get("DATABASE_URL"):
            value = os.environ.get("DATABASE_URL")
        elif not value:
            value = os.environ.get("DATABASE_URL") or DEFAULT_DATABASE_URL
        if isinstance(value, str):
            v_clean = value.strip()
            if v_clean.startswith("postgres://"):
                return "postgresql+asyncpg://" + v_clean[len("postgres://"):]
            elif v_clean.startswith("postgresql://") and not v_clean.startswith("postgresql+"):
                return "postgresql+asyncpg://" + v_clean[len("postgresql://"):]
            elif v_clean.startswith("sqlite://") and not v_clean.startswith("sqlite+"):
                return "sqlite+aiosqlite://" + v_clean[len("sqlite://"):]
            return v_clean
        return value

    @field_validator("tavily_api_key", mode="before")
    @classmethod
    def resolve_tavily_api_key(cls, value: object) -> object:
        if value:
            return value
        # Fall back to standard TAVILY_API_KEY if NEOMON_ prefix was not provided
        return os.environ.get("TAVILY_API_KEY") or None

    @field_validator("allowed_origins", "allowed_local_provider_hosts", "tavily_include_domains", "tavily_exclude_domains", "trusted_proxies", mode="before")
    @classmethod
    def parse_allowed_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

