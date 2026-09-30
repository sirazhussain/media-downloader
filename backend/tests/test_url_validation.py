"""URL validation / platform detection tests (no real network)."""

import pytest

from app.core.security import (
    InvalidURLError,
    SSRFBlockedError,
    UnsupportedPlatformError,
    validate_media_url,
)


@pytest.mark.parametrize(
    "url",
    [
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://youtube.com/watch?v=dQw4w9WgXcQ&t=10s",
        "https://m.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://youtu.be/dQw4w9WgXcQ",
        "https://www.youtube.com/shorts/dQw4w9WgXcQ",
        "https://www.youtube.com/embed/dQw4w9WgXcQ",
    ],
)
def test_valid_youtube_urls(url: str) -> None:
    platform, canonical = validate_media_url(url)
    assert platform == "youtube"
    assert canonical.startswith("https://")


def test_valid_instagram_reel() -> None:
    platform, canonical = validate_media_url("https://www.instagram.com/reel/C8AbCDefGh1/")
    assert platform == "instagram"
    assert "/reel/" in canonical


@pytest.mark.parametrize(
    "url",
    [
        "ftp://www.youtube.com/watch?v=dQw4w9WgXcQ",  # bad scheme
        "not a url",
        "",
        "https://",  # no host
    ],
)
def test_invalid_urls_rejected(url: str) -> None:
    with pytest.raises(InvalidURLError):
        validate_media_url(url)


@pytest.mark.parametrize(
    "url",
    [
        "https://vimeo.com/12345",
        "https://www.tiktok.com/@user/video/123",
        "https://example.com/video.mp4",
    ],
)
def test_unsupported_domains_rejected(url: str) -> None:
    with pytest.raises(UnsupportedPlatformError):
        validate_media_url(url)


def test_instagram_non_reel_paths_rejected() -> None:
    with pytest.raises(UnsupportedPlatformError):
        validate_media_url("https://www.instagram.com/p/C8AbCDefGh1/")
    with pytest.raises(UnsupportedPlatformError):
        validate_media_url("https://www.instagram.com/stories/user/123")


def test_youtube_non_video_paths_rejected() -> None:
    with pytest.raises(UnsupportedPlatformError):
        validate_media_url("https://www.youtube.com/channel/UC1234567890")


@pytest.mark.parametrize(
    "url",
    [
        "http://localhost/video",
        "http://localhost:3000/",
        "http://127.0.0.1/watch?v=abc123",
        "http://0.0.0.0/",
        "http://192.168.1.1/video.mp4",
        "http://10.0.0.5/x",
        "http://172.16.0.9/x",
        "http://[::1]/x",
    ],
)
def test_ssrf_targets_rejected(url: str) -> None:
    with pytest.raises((SSRFBlockedError, UnsupportedPlatformError, InvalidURLError)):
        validate_media_url(url)


def test_private_ip_literal_on_allowed_host_rejected() -> None:
    # IP literals are never allowed, even hypothetically on an allowed domain shape.
    with pytest.raises(SSRFBlockedError):
        validate_media_url("http://93.184.216.34/")


def test_host_resolving_to_private_range_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    import socket

    def fake_private_getaddrinfo(host, port, *args, **kwargs):  # type: ignore[no-untyped-def]
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.9.8.7", port))]

    monkeypatch.setattr(
        "app.core.security.socket.getaddrinfo", fake_private_getaddrinfo
    )
    with pytest.raises(SSRFBlockedError):
        validate_media_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ")


def test_overly_long_url_rejected() -> None:
    with pytest.raises(InvalidURLError):
        validate_media_url("https://www.youtube.com/watch?v=" + "a" * 3000)


def test_fragment_stripped_from_canonical_url() -> None:
    _, canonical = validate_media_url("https://youtu.be/dQw4w9WgXcQ#t=30")
    assert "#t=30" not in canonical
