"""Download-specific schemas (re-exports; kept small by design)."""

from app.schemas.media import DownloadRequest, ErrorDetail, ErrorResponse

__all__ = ["DownloadRequest", "ErrorDetail", "ErrorResponse"]
