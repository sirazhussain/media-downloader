"""Pure URL helpers. Validation itself lives in app.core.security."""

from urllib.parse import urlparse

from app.core.security import validate_media_url

__all__ = ["validate_media_url", "extract_host"]


def extract_host(url: str) -> str:
    """Return the lowercased host of a URL, or '' if it has none."""
    try:
        return (urlparse(url or "").hostname or "").lower()
    except ValueError:
        return ""
