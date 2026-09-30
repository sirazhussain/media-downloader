"""Security unit tests: rate limiter, filename sanitization, streaming guards."""

import pytest

from app.core.security import (
    RateLimitedError,
    RateLimiter,
    sanitize_filename_component,
)
from app.services.streaming_service import _assert_remote_url_allowed
from app.utils.filename import build_safe_filename


def test_rate_limiter_allows_within_budget() -> None:
    limiter = RateLimiter()
    for _ in range(3):
        limiter.check("test-key", limit=3, window_seconds=60)


def test_rate_limiter_blocks_over_budget() -> None:
    limiter = RateLimiter()
    limiter.check("over-key", limit=2, window_seconds=60)
    limiter.check("over-key", limit=2, window_seconds=60)
    with pytest.raises(RateLimitedError) as exc_info:
        limiter.check("over-key", limit=2, window_seconds=60)
    assert exc_info.value.status_code == 429
    assert exc_info.value.code == "RATE_LIMITED"


def test_rate_limiter_keys_are_independent() -> None:
    limiter = RateLimiter()
    limiter.check("key-a", limit=1, window_seconds=60)
    limiter.check("key-b", limit=1, window_seconds=60)  # no error


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("My Amazing Video", "My Amazing Video"),
        ('a/b\\c:d*e?f"g<h>i|j', "abcdefghi j".replace(" ", "")),
        ("  spaced   out  ", "spaced out"),
        ("line\nbreak\r\ninjected", "linebreakinjected"),
        ("", "download"),
        ("...", "download"),
    ],
)
def test_sanitize_filename_component(raw: str, expected: str) -> None:
    assert sanitize_filename_component(raw) == expected


def test_sanitize_truncates_long_names() -> None:
    assert len(sanitize_filename_component("x" * 500)) == 100


def test_sanitize_never_contains_header_injection() -> None:
    cleaned = sanitize_filename_component('evil\r\nHeader: injected<>:"/\\|?*')
    assert "\r" not in cleaned and "\n" not in cleaned


def test_build_safe_filename() -> None:
    assert build_safe_filename("My Video: Part 1?", "mp4") == "My Video Part 1.mp4"
    assert build_safe_filename("", "webm") == "download.webm"
    assert build_safe_filename("x", "weird ext!") == "x.bin"


def test_remote_url_guard_blocks_ip_literals() -> None:
    from app.core.security import SSRFBlockedError

    with pytest.raises(SSRFBlockedError):
        _assert_remote_url_allowed("http://127.0.0.1/video.mp4")
    with pytest.raises(SSRFBlockedError):
        _assert_remote_url_allowed("http://10.0.0.1/video.mp4")


def test_remote_url_guard_allows_hostnames() -> None:
    # Hostnames from yt-dlp extraction pass (DNS-level check happens at URL validation).
    _assert_remote_url_allowed("https://rr1---sn.example.googlevideo.com/videoplayback")
