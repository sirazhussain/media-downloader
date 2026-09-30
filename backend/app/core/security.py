"""Security primitives: SSRF-safe URL validation, rate limiting, filename sanitization.

Single source of truth for URL allow-listing and SSRF protection.
"""

from __future__ import annotations

import ipaddress
import re
import socket
import threading
import time
from abc import ABC, abstractmethod
from collections import deque
from urllib.parse import urlparse


# ---------------------------------------------------------------------------
# Application errors (mapped to clean API error envelopes in app.main)
# ---------------------------------------------------------------------------
class MediaDownloaderError(Exception):
    code: str = "INTERNAL_ERROR"
    message: str = "An unexpected error occurred."
    status_code: int = 500

    def __init__(
        self,
        message: str | None = None,
        *,
        code: str | None = None,
        status_code: int | None = None,
    ) -> None:
        super().__init__(message or self.message)
        if message is not None:
            self.message = message
        if code is not None:
            self.code = code
        if status_code is not None:
            self.status_code = status_code


class InvalidURLError(MediaDownloaderError):
    code = "INVALID_URL"
    message = "The provided URL is invalid."
    status_code = 400


class UnsupportedPlatformError(MediaDownloaderError):
    code = "UNSUPPORTED_PLATFORM"
    message = "This platform or URL type is not supported."
    status_code = 422


class SSRFBlockedError(MediaDownloaderError):
    code = "SSRF_BLOCKED"
    message = "The URL target is not allowed."
    status_code = 400


class AuthRequiredError(MediaDownloaderError):
    code = "AUTH_REQUIRED"
    message = (
        "This content requires authentication or is otherwise restricted, "
        "so it cannot be retrieved."
    )
    status_code = 403


class MediaUnavailableError(MediaDownloaderError):
    code = "MEDIA_UNAVAILABLE"
    message = "This media is currently unavailable."
    status_code = 422


class FormatNotAvailableError(MediaDownloaderError):
    code = "FORMAT_UNAVAILABLE"
    message = "The requested format is not available for this media."
    status_code = 422


class MediaTooLongError(MediaDownloaderError):
    code = "MEDIA_TOO_LONG"
    message = "This media exceeds the maximum supported duration."
    status_code = 422


class DownloadTooLargeError(MediaDownloaderError):
    code = "DOWNLOAD_TOO_LARGE"
    message = "This download exceeds the maximum supported size."
    status_code = 413


class MuxingUnavailableError(MediaDownloaderError):
    code = "FORMAT_REQUIRES_MUXING_UNAVAILABLE"
    message = (
        "This quality requires audio/video merging, which is currently "
        "unavailable on this server. Please choose a combined format."
    )
    status_code = 422


class RateLimitedError(MediaDownloaderError):
    code = "RATE_LIMITED"
    message = "Too many requests. Please slow down and try again."
    status_code = 429


# ---------------------------------------------------------------------------
# URL validation / platform detection
# ---------------------------------------------------------------------------
YOUTUBE_HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be"}
INSTAGRAM_HOSTS = {"instagram.com", "www.instagram.com"}
LINKEDIN_HOSTS = {"linkedin.com", "www.linkedin.com"}
TWITTER_HOSTS = {"twitter.com", "www.twitter.com", "x.com", "www.x.com"}
FACEBOOK_HOSTS = {
    "facebook.com", "www.facebook.com", "m.facebook.com",
    "fb.watch", "www.fb.watch",
}
SNAPCHAT_HOSTS = {"snapchat.com", "www.snapchat.com", "story.snapchat.com", "t.snapchat.com"}
ALLOWED_HOSTS = (
    YOUTUBE_HOSTS | INSTAGRAM_HOSTS | LINKEDIN_HOSTS
    | TWITTER_HOSTS | FACEBOOK_HOSTS | SNAPCHAT_HOSTS
)

_ID_PATTERN = r"[\w\-]{6,}"
_YOUTUBE_SHORT_ID = re.compile(rf"^/{_ID_PATTERN}/?$")
_YOUTUBE_SHORTS = re.compile(rf"^/shorts/{_ID_PATTERN}/?$")
_YOUTUBE_EMBED = re.compile(rf"^/embed/{_ID_PATTERN}/?$")
_INSTAGRAM_REEL = re.compile(r"^/reel/[\w\-\.]+/?$")
# LinkedIn: /posts/..., /feed/update/...  or  /embed/feed/update/...
_LINKEDIN_POST = re.compile(r"^/(posts|feed/update|embed/feed/update)/[\w\-:]+/?$")
_LINKEDIN_VIDEO = re.compile(r"^/video/[\w\-]+/?$")
# Twitter/X: /<user>/status/<id>
_TWITTER_STATUS = re.compile(r"^/[\w]+/status/\d+/?$")
# Facebook: /watch, /reel/, /<user>/videos/, /share/v/
_FACEBOOK_WATCH = re.compile(r"^/(watch(/\d+)?|reel/\d+|[\w.]+/videos/\d+|share/v/\d+)/?$")
# Snapchat: /spotlight/, /add/<user>/<story>
_SNAPCHAT_SPOTLIGHT = re.compile(r"^/(spotlight/[\w\-]+|add/[\w\.\-]+(/[\w\-]+)?)/?$")


def _detect_platform(host: str, path: str, query: str) -> str:
    if host == "youtu.be":
        if _YOUTUBE_SHORT_ID.fullmatch(path):
            return "youtube"
        raise UnsupportedPlatformError("Only direct youtu.be video links are supported.")

    if host in YOUTUBE_HOSTS:
        if path == "/watch" and "v=" in query:
            return "youtube"
        if _YOUTUBE_SHORTS.fullmatch(path) or _YOUTUBE_EMBED.fullmatch(path):
            return "youtube"
        raise UnsupportedPlatformError(
            "Only YouTube watch, Shorts, and youtu.be links are supported."
        )

    if host in INSTAGRAM_HOSTS:
        if _INSTAGRAM_REEL.fullmatch(path):
            return "instagram"
        raise UnsupportedPlatformError(
            "Only public Instagram reels (instagram.com/reel/...) are supported."
        )

    if host in LINKEDIN_HOSTS:
        if _LINKEDIN_POST.fullmatch(path) or _LINKEDIN_VIDEO.fullmatch(path):
            return "linkedin"
        raise UnsupportedPlatformError(
            "Only LinkedIn video posts (linkedin.com/posts/... or linkedin.com/video/...) are supported."
        )

    if host in TWITTER_HOSTS:
        if _TWITTER_STATUS.fullmatch(path):
            return "twitter"
        raise UnsupportedPlatformError(
            "Only Twitter/X status posts (x.com/<user>/status/<id>) are supported."
        )

    if host in FACEBOOK_HOSTS:
        if host in {"fb.watch", "www.fb.watch"}:
            return "facebook"
        if _FACEBOOK_WATCH.fullmatch(path):
            return "facebook"
        raise UnsupportedPlatformError(
            "Only Facebook video URLs (facebook.com/watch, /reel/, /videos/) are supported."
        )

    if host in SNAPCHAT_HOSTS:
        if _SNAPCHAT_SPOTLIGHT.fullmatch(path):
            return "snapchat"
        raise UnsupportedPlatformError(
            "Only Snapchat Spotlight URLs (snapchat.com/spotlight/...) are supported."
        )

    raise UnsupportedPlatformError(f"Domain '{host}' is not supported.")


def _assert_public_dns(host: str) -> None:
    """Reject hosts that resolve to non-public addresses (SSRF protection)."""
    try:
        addr_infos = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise InvalidURLError(f"Could not resolve host '{host}'.") from exc

    for info in addr_infos:
        ip = ipaddress.ip_address(info[4][0])
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_reserved
            or ip.is_unspecified
        ):
            raise SSRFBlockedError(
                f"Host '{host}' resolves to a non-public address."
            )


def validate_media_url(raw_url: str, *, max_length: int = 2048) -> tuple[str, str]:
    """Validate a user-supplied media URL.

    Returns ``(platform, canonical_url)`` where platform is one of
    ``"youtube"``, ``"instagram"``, ``"linkedin"``, ``"twitter"``,
    ``"facebook"``, or ``"snapchat"``.  Raises a
    :class:`MediaDownloaderError` subclass carrying a public error code
    on any failure.
    """
    url = (raw_url or "").strip()
    if not url:
        raise InvalidURLError("URL must not be empty.")
    if len(url) > max_length:
        raise InvalidURLError(f"URL exceeds the maximum length of {max_length} characters.")

    try:
        parsed = urlparse(url)
    except ValueError as exc:
        raise InvalidURLError("The provided URL is invalid.") from exc

    if parsed.scheme not in ("http", "https"):
        raise InvalidURLError("Only http(s) URLs are supported.")

    host = (parsed.hostname or "").lower().rstrip(".")
    if not host:
        raise InvalidURLError("The URL must include a host.")

    if host == "localhost" or host.endswith(".localhost"):
        raise SSRFBlockedError("Localhost URLs are not allowed.")

    try:
        ipaddress.ip_address(host)
    except ValueError:
        pass  # not an IP literal; continue with hostname checks
    else:
        raise SSRFBlockedError("IP-literal hosts are not allowed.")

    if host not in ALLOWED_HOSTS:
        raise UnsupportedPlatformError(f"Domain '{host}' is not supported.")

    # DNS-level SSRF check: allow-listed hostnames must resolve publicly.
    _assert_public_dns(host)

    platform = _detect_platform(host, parsed.path or "/", parsed.query or "")
    canonical_url = parsed._replace(fragment="").geturl()
    return platform, canonical_url


# ---------------------------------------------------------------------------
# Rate limiting (in-memory; swappable for Redis via RateLimitStore)
# ---------------------------------------------------------------------------
class RateLimitStore(ABC):
    """Storage contract for rate limiting. A Redis implementation can replace
    :class:`InMemoryRateLimitStore` without touching callers."""

    @abstractmethod
    def is_allowed(self, key: str, limit: int, window_seconds: int) -> bool:
        """Return True and record a hit when the key is within budget."""


class InMemoryRateLimitStore(RateLimitStore):
    """Sliding-window rate limit store kept in process memory."""

    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def is_allowed(self, key: str, limit: int, window_seconds: int) -> bool:
        now = time.monotonic()
        cutoff = now - window_seconds
        with self._lock:
            bucket = self._hits.setdefault(key, deque())
            while bucket and bucket[0] <= cutoff:
                bucket.popleft()
            if len(bucket) >= limit:
                return False
            bucket.append(now)
            return True


class RateLimiter:
    """Fixed API over any :class:`RateLimitStore`."""

    def __init__(self, store: RateLimitStore | None = None) -> None:
        self._store = store or InMemoryRateLimitStore()

    def check(self, key: str, limit: int, window_seconds: int = 60) -> None:
        """Raise :class:`RateLimitedError` when the key exceeds its budget."""
        if not self._store.is_allowed(key, limit, window_seconds):
            raise RateLimitedError()


# ---------------------------------------------------------------------------
# Filename sanitization
# ---------------------------------------------------------------------------
_UNSAFE_FILENAME_CHARS = re.compile(r'[/\\:*?"<>|\x00-\x1f\x7f]')
_WHITESPACE_RUN = re.compile(r"\s+")


def sanitize_filename_component(value: str, *, max_length: int = 100) -> str:
    """Strip characters unsafe for filenames/HTTP headers.

    Removes ``/ \\ : * ? " < > |`` and control characters (which also blocks
    CR/LF header injection), collapses whitespace, and truncates.
    """
    cleaned = _UNSAFE_FILENAME_CHARS.sub("", value or "")
    cleaned = _WHITESPACE_RUN.sub(" ", cleaned).strip().strip(".")
    if not cleaned:
        cleaned = "download"
    if len(cleaned) > max_length:
        cleaned = cleaned[:max_length].rstrip() or "download"
    return cleaned
