from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


DEFAULT_DATABASE_PATH = Path(__file__).resolve().parents[1] / "neomon.db"
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
    tavily_api_key: str | None = None
    unpaywall_email: str | None = None
    unpaywall_api_key: str | None = None
    research_user_agent: str = "NEOMON/0.3 (+https://github.com/neomon-dev/NEOMON)"
    research_max_document_bytes: int = Field(default=5_000_000, ge=100_000, le=50_000_000)

    @field_validator("allowed_origins", "allowed_local_provider_hosts", mode="before")
    @classmethod
    def parse_allowed_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
