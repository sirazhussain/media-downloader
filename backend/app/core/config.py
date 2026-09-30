"""Application configuration via environment variables (pydantic-settings)."""

from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All runtime configuration. No secrets are hard-coded here."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "media-downloader"
    app_version: str = "1.0.0"
    log_level: str = "INFO"

    # Comma-separated list or wildcard, e.g. "*", or "https://a.com,https://b.com"
    cors_origins: str | list[str] = ["http://localhost:3000"]

    max_url_length: int = 2048
    max_download_bytes: int = 10_737_418_240  # 10 GiB (supports 4GB and 8GB videos)
    max_duration_seconds: int = 14400  # 4 hours
    rate_limit_info_per_min: int = 60
    rate_limit_download_per_min: int = 30
    request_timeout_seconds: int = 1800  # 30 min for large file streaming
    yt_dlp_socket_timeout: int = 30
    youtube_cookies: str | None = None

    @field_validator("cors_origins", mode="after")
    @classmethod
    def split_cors_origins(cls, value: object) -> list[str]:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        if isinstance(value, list):
            return [str(origin).strip() for origin in value if str(origin).strip()]
        return ["http://localhost:3000"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
