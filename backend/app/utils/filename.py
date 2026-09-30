"""Safe download filename construction."""

import re

from app.core.security import sanitize_filename_component

_EXT_RE = re.compile(r"^[a-z0-9]{1,10}$")


def build_safe_filename(title: str, ext: str | None) -> str:
    """Build a filesystem- and header-safe ``<title>.<ext>`` filename."""
    stem = sanitize_filename_component(title.strip()) if title and title.strip() else "download"
    safe_ext = (ext or "").lower().strip()
    if not _EXT_RE.fullmatch(safe_ext):
        safe_ext = "bin"
    return f"{stem}.{safe_ext}"
