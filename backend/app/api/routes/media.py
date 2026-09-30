"""Media endpoints: metadata lookup and authorized media download streaming."""

from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncIterator
from urllib.parse import quote

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from app.core.config import get_settings
from app.core.logging import get_logger, safe_host
from app.core.security import RateLimiter
from app.schemas.media import (
    DownloadRequest,
    MediaInfoRequest,
    MediaInfoResponse,
)
from app.services.extractor_service import MediaExtractor, remove_temp_dir
from app.services.media_service import MediaService
from app.services.streaming_service import StreamingService
from app.utils.filename import build_safe_filename

logger = get_logger(__name__)
router = APIRouter(prefix="/media", tags=["media"])

_settings = get_settings()
_extractor = MediaExtractor(socket_timeout=_settings.yt_dlp_socket_timeout)
_media_service = MediaService(_extractor, _settings)
_streaming_service = StreamingService(_settings)
_rate_limiter = RateLimiter()

_EXT_CONTENT_TYPES = {
    "mp4": "video/mp4",
    "webm": "video/webm",
    "mkv": "video/x-matroska",
    "mov": "video/quicktime",
    "m4a": "audio/mp4",
    "mp3": "audio/mpeg",
    "opus": "audio/opus",
    "ogg": "audio/ogg",
    "wav": "audio/wav",
}


def _client_ip(request: Request) -> str:
    if request.client is not None:
        return request.client.host
    return "unknown"


def _content_type_for_ext(ext: str) -> str:
    return _EXT_CONTENT_TYPES.get(ext.lower(), "application/octet-stream")


def _content_disposition(filename: str) -> str:
    """RFC 6266/5987 Content-Disposition; filename is pre-sanitized (no CR/LF)."""
    ascii_name = filename.encode("ascii", "ignore").decode("ascii") or "download"
    return f'attachment; filename="{ascii_name}"; filename*=UTF-8\'\'{quote(filename)}'


@router.post("/info", response_model=MediaInfoResponse, summary="Get media metadata")
async def media_info(payload: MediaInfoRequest, request: Request) -> MediaInfoResponse:
    _rate_limiter.check(
        f"info:{_client_ip(request)}",
        _settings.rate_limit_info_per_min,
        window_seconds=60,
    )
    # yt-dlp is blocking; keep the event loop free.
    return await asyncio.to_thread(_media_service.get_media_info, payload.url)


@router.post("/download", summary="Stream authorized media to the browser")
async def download_media(payload: DownloadRequest, request: Request) -> StreamingResponse:
    _rate_limiter.check(
        f"download:{_client_ip(request)}",
        _settings.rate_limit_download_per_min,
        window_seconds=60,
    )
    _platform, url, resolved = await asyncio.to_thread(
        _media_service.resolve_download, payload.url, payload.format_id
    )

    filename = build_safe_filename(resolved.title or "download", resolved.ext)
    headers = {"Content-Disposition": _content_disposition(filename)}
    media_type = _content_type_for_ext(resolved.ext)

    if resolved.needs_mux or not resolved.direct_url:
        # Clearly-marked fallback: yt-dlp merges to a temp file, we stream it
        # chunk by chunk, and the file is deleted in the generator's finally.
        tmp_path = await asyncio.to_thread(
            _extractor.download_to_temp, url, resolved.format_id
        )

        async def _file_stream() -> AsyncIterator[bytes]:
            try:
                async for chunk in _streaming_service.stream_file(tmp_path):
                    yield chunk
            finally:
                remove_temp_dir(os.path.dirname(tmp_path))

        logger.info(
            "download started (mux fallback)",
            extra={"host": safe_host(url), "client_ip": _client_ip(request)},
        )
        return StreamingResponse(_file_stream(), media_type=media_type, headers=headers)

    async def _remote_stream() -> AsyncIterator[bytes]:
        async for chunk in _streaming_service.stream_remote(resolved.direct_url or ""):
            yield chunk

    if resolved.filesize:
        headers["Content-Length"] = str(resolved.filesize)
    logger.info(
        "download started (direct stream)",
        extra={"host": safe_host(url), "client_ip": _client_ip(request)},
    )
    return StreamingResponse(_remote_stream(), media_type=media_type, headers=headers)
