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
    )

    app_name: str = "media-downloader"
    app_version: str = "1.0.0"
    log_level: str = "INFO"

    # Comma-separated list, e.g. "http://localhost:3000,https://app.example.com"
    cors_origins: list[str] = ["http://localhost:3000"]

    max_url_length: int = 2048
    max_download_bytes: int = 2_147_483_648  # 2 GiB
    max_duration_seconds: int = 14400  # 4 hours
    rate_limit_info_per_min: int = 20
    rate_limit_download_per_min: int = 5
    request_timeout_seconds: int = 30
    yt_dlp_socket_timeout: int = 15

    @field_validator("cors_origins", mode="before")
    @classmethod
    def split_cors_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
