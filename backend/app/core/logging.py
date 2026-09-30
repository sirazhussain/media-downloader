"""Structured logging helpers.

Privacy rule: never log full user-supplied URLs, cookies, tokens, or secrets.
Log only the URL host (via ``safe_host``) when host context is needed.
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

_configured = False

_EXTRA_KEYS = (
    "method",
    "path",
    "platform",
    "status_code",
    "duration_ms",
    "error_code",
    "client_ip",
    "host",
)


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key in _EXTRA_KEYS:
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = value
        if record.exc_info and record.exc_info[0] is not None:
            payload["exc_type"] = record.exc_info[0].__name__
        return json.dumps(payload, default=str)


def configure_logging(level: str = "INFO") -> None:
    """Configure the root logger once with a JSON-ish formatter."""
    global _configured
    if _configured:
        return
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(_JsonFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level.upper())
    _configured = True


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def safe_host(url: str) -> str:
    """Return only the host portion of a URL for safe logging."""
    try:
        return (urlparse(url).hostname or "").lower()
    except Exception:
        return ""
