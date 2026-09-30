"""Chunked streaming of media bytes to the HTTP response.

Primary path: stream the direct media URL with httpx, yielding 64 KiB
chunks, enforcing the max-download size while streaming. The server never
retains the bytes. Fallback path: stream a temporary muxed file chunk by
chunk (the route deletes it in a ``finally`` block).
"""

from __future__ import annotations

import ipaddress
from collections.abc import AsyncIterator
from urllib.parse import urlparse

import httpx

from app.core.config import Settings
from app.core.logging import get_logger
from app.core.security import DownloadTooLargeError, MediaUnavailableError, SSRFBlockedError

logger = get_logger(__name__)

_CHUNK_SIZE = 262_144  # 256 KiB — larger chunks = faster throughput for big files


def _assert_remote_url_allowed(url: str) -> None:
    """Light SSRF guard for stream targets: block non-public IP literals."""
    try:
        host = (urlparse(url).hostname or "").lower()
    except ValueError as exc:
        raise MediaUnavailableError("The media source URL is invalid.") from exc
    if not host:
        raise MediaUnavailableError("The media source URL is invalid.")
    try:
        ip = ipaddress.ip_address(host.strip("[]"))
    except ValueError:
        return  # hostname provided by yt-dlp extraction; not user-controlled
    if (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    ):
        raise SSRFBlockedError("The media source target is not allowed.")


class StreamingService:
    def __init__(self, settings: Settings) -> None:
        self._max_bytes = settings.max_download_bytes
        self._timeout = settings.request_timeout_seconds

    async def stream_remote(
        self,
        url: str,
        custom_headers: dict[str, str] | None = None,
    ) -> AsyncIterator[bytes]:
        """Yield media bytes from a direct URL, aborting past the size cap."""
        _assert_remote_url_allowed(url)
        total = 0
        client_kwargs: dict[str, object] = {
            "timeout": self._timeout,
            "follow_redirects": True,
            "max_redirects": 5,
        }

        req_headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept": "*/*",
            "Accept-Encoding": "identity",
        }
        if custom_headers:
            for k, v in custom_headers.items():
                if v and k.lower() not in ("host", "content-length"):
                    req_headers[k] = str(v)

        try:
            async with httpx.AsyncClient(**client_kwargs) as client:
                async with client.stream(
                    "GET",
                    url,
                    headers=req_headers,
                ) as response:
                    if response.status_code >= 400:
                        logger.warning(
                            "Remote stream returned HTTP %d for %s",
                            response.status_code,
                            url[:80],
                        )
                        raise MediaUnavailableError(
                            "The media source returned an error."
                        )
                    async for chunk in response.aiter_bytes(_CHUNK_SIZE):
                        total += len(chunk)
                        if total > self._max_bytes:
                            raise DownloadTooLargeError()
                        yield chunk
        except httpx.HTTPError as exc:
            raise MediaUnavailableError(
                "Could not stream the media from its source."
            ) from exc

    async def stream_file(self, path: str) -> AsyncIterator[bytes]:
        """Yield a local temp file chunk by chunk (caller deletes it after)."""
        total = 0
        # Blocking reads are acceptable here: one sequential read per request.
        with open(path, "rb") as handle:
            while True:
                chunk = handle.read(_CHUNK_SIZE)
                if not chunk:
                    break
                total += len(chunk)
                if total > self._max_bytes:
                    raise DownloadTooLargeError()
                yield chunk
