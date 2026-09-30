"""Orchestration between validation, extraction, and API schemas."""

from app.core.config import Settings
from app.core.logging import get_logger, safe_host
from app.core.security import MediaTooLongError, MediaUnavailableError, validate_media_url
from app.schemas.media import MediaInfoResponse
from app.services.extractor_service import MediaExtractor, ResolvedFormat

logger = get_logger(__name__)


class MediaService:
    """Thin orchestration layer; routes call this, never yt-dlp directly."""

    def __init__(self, extractor: MediaExtractor, settings: Settings) -> None:
        self._extractor = extractor
        self._settings = settings

    def get_media_info(self, raw_url: str) -> MediaInfoResponse:
        platform, url = validate_media_url(
            raw_url, max_length=self._settings.max_url_length
        )
        info = self._extractor.get_info(url)

        duration_raw = info.get("duration")
        duration = int(duration_raw) if isinstance(duration_raw, (int, float)) else None
        if duration is not None and duration > self._settings.max_duration_seconds:
            raise MediaTooLongError(
                "This media exceeds the maximum supported duration."
            )

        formats = self._extractor.normalize_formats(info)
        if not formats:
            raise MediaUnavailableError(
                "No downloadable formats were found for this media."
            )

        logger.info(
            "media info resolved",
            extra={"platform": platform, "host": safe_host(url)},
        )
        return MediaInfoResponse(
            platform=platform,
            id=str(info.get("id") or ""),
            title=str(info.get("title") or "Untitled"),
            thumbnail=info.get("thumbnail"),
            duration=duration,
            uploader=info.get("uploader"),
            formats=formats,
        )

    def resolve_download(
        self, raw_url: str, format_id: str
    ) -> tuple[str, str, ResolvedFormat]:
        """Re-validate the URL and the format id; returns (platform, url, format)."""
        platform, url = validate_media_url(
            raw_url, max_length=self._settings.max_url_length
        )
        resolved = self._extractor.resolve_format(url, format_id)
        logger.info(
            "download format resolved",
            extra={"platform": platform, "host": safe_host(url)},
        )
        return platform, url, resolved
