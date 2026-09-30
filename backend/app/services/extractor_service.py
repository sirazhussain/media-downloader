"""yt-dlp integration used strictly as a Python library.

Hard legal boundary: yt-dlp is configured WITHOUT cookies, WITHOUT
``cookies-from-browser``, and WITHOUT any username/password or session
handling. Only publicly accessible media can be retrieved. When yt-dlp
reports that content is private, login-gated, or DRM-protected, a clean
application error is raised instead of attempting any bypass.
"""

from __future__ import annotations

import os
import re
import shutil
import tempfile

from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError, ExtractorError

from app.core.config import get_settings
from app.core.logging import get_logger, safe_host
from app.core.security import (
    AuthRequiredError,
    FormatNotAvailableError,
    MediaDownloaderError,
    MediaUnavailableError,
    MuxingUnavailableError,
)
from app.schemas.media import MediaFormat

logger = get_logger(__name__)

_FORMAT_ID_RE = re.compile(r"^[\w\-.]+$")


class ResolvedFormat:
    """A validated, downloadable format chosen from fresh extraction data."""

    def __init__(
        self,
        *,
        format_id: str,
        ext: str,
        title: str | None,
        direct_url: str | None,
        needs_mux: bool,
        filesize: int | None,
    ) -> None:
        self.format_id = format_id
        self.ext = ext
        self.title = title
        self.direct_url = direct_url
        self.needs_mux = needs_mux
        self.filesize = filesize


class MediaExtractor:
    """Thin, honest wrapper around yt-dlp. All yt-dlp specifics live here."""

    def __init__(self, *, socket_timeout: int = 15) -> None:
        self._socket_timeout = socket_timeout

    @staticmethod
    def _get_cookiefile() -> str | None:
        """Write YOUTUBE_COOKIES to a temp file if provided in settings."""
        import base64
        import re
        import tempfile
        from pathlib import Path

        cookies = get_settings().youtube_cookies
        if not cookies or not cookies.strip():
            return None

        content = cookies.strip()
        try:
            decoded = base64.b64decode(content).decode("utf-8")
            if "# Netscape" in decoded or "\t" in decoded:
                content = decoded
        except Exception:
            pass

        # Reconstruct newlines if flattened into spaces by Azure Portal UI single-line env var
        if "\n" not in content or content.count("\n") < 3:
            content = re.sub(
                r"\s+(#|\.?[a-zA-Z0-9_-]+\.[a-zA-Z]{2,}\s+(?:TRUE|FALSE))",
                r"\n\1",
                content,
            )

        cookie_path = Path(tempfile.gettempdir()) / "yt_cookies.txt"
        cookie_path.write_text(content.strip() + "\n", encoding="utf-8")
        return str(cookie_path)

    # -- yt-dlp configuration ------------------------------------------------
    def _base_opts(self) -> dict:
        opts: dict[str, object] = {
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
            "socket_timeout": self._socket_timeout,
            "retries": 2,
            "js_runtimes": {"node": {}},
            "remote_components": ["ejs:github"],
        }
        cookiefile = self._get_cookiefile()
        if cookiefile:
            opts["cookiefile"] = cookiefile
        return opts

    # -- metadata -------------------------------------------------------------
    def get_info(self, url: str) -> dict:
        """Extract metadata without downloading. Maps yt-dlp failures to
        clean application errors (never leaks tracebacks)."""
        opts = {**self._base_opts(), "skip_download": True}
        try:
            with YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
        except DownloadError as exc:
            raise self._map_download_error(exc) from exc
        except ExtractorError as exc:
            raise MediaUnavailableError(
                "Could not extract media information from this URL."
            ) from exc

        if not info or info.get("_type") not in (None, "video"):
            raise MediaUnavailableError("No downloadable video found at this URL.")
        if info.get("is_live"):
            raise MediaUnavailableError("Live streams are not supported.")
        return info

    def _map_download_error(self, exc: DownloadError) -> MediaDownloaderError:
        msg = str(exc).lower()
        if "drm" in msg:
            return MediaUnavailableError(
                "DRM-protected content is not supported."
            )
        if any(
            marker in msg
            for marker in (
                "private video",
                "this video is private",
                "private account",
                "only available to",
            )
        ):
            return MediaUnavailableError(
                "This content is private or unavailable, so it cannot be retrieved."
            )
        if any(
            marker in msg
            for marker in (
                "login required",
                "log in",
                "sign in",
                "age-verification",
                "age gated",
                "confirm your age",
            )
        ):
            return AuthRequiredError()
        if any(marker in msg for marker in ("not available in your country", "geo")):
            return MediaUnavailableError(
                "This content is not available in your region."
            )
        return MediaUnavailableError("This media is currently unavailable.")

    # -- format normalization ---------------------------------------------------
    def normalize_formats(self, info: dict) -> list[MediaFormat]:
        """Build the public format list from yt-dlp's real format data.

        No hard-coded quality ladder: only formats yt-dlp actually reports
        are listed. Deduped by (height, ext, has_video, has_audio); combined
        (progressive) formats sort before video-only ones at the same height.
        """
        seen: set[tuple[int, str, bool, bool]] = set()
        formats: list[MediaFormat] = []

        for raw in info.get("formats") or []:
            format_id = str(raw.get("format_id") or "")
            ext = str(raw.get("ext") or "")
            if not format_id or not ext:
                continue
            has_video = self._has_stream(raw.get("vcodec"))
            has_audio = self._has_stream(raw.get("acodec"))

            # Many platforms (LinkedIn, Facebook, Snapchat) serve progressive
            # mp4 files but don't expose vcodec/acodec metadata.  When both
            # are unknown *and* there is a direct URL, assume it is a
            # combined video+audio stream.
            if not has_video and not has_audio:
                direct_url = raw.get("url") or ""
                if direct_url and ext in ("mp4", "webm", "m4v"):
                    has_video = True
                    has_audio = True
                else:
                    continue

            # Try to extract height from format_note or URL when missing.
            height = raw.get("height")
            if not isinstance(height, int) or height <= 0:
                height = self._infer_height(raw)

            if has_video and isinstance(height, int) and height > 0:
                quality = f"{height}p"
                dedup_height = height
            elif not has_video:
                quality = "audio"
                dedup_height = 0
            else:
                quality = "video"
                dedup_height = 0

            key = (dedup_height, ext, has_video, has_audio)
            if key in seen:
                continue
            seen.add(key)

            filesize = raw.get("filesize") or raw.get("filesize_approx")
            formats.append(
                MediaFormat(
                    format_id=format_id,
                    ext=ext,
                    quality=quality,
                    width=raw.get("width"),
                    height=height if isinstance(height, int) else None,
                    filesize=filesize if isinstance(filesize, int) else None,
                    has_video=has_video,
                    has_audio=has_audio,
                )
            )

        formats.sort(
            key=lambda f: (
                f.height if f.height is not None else -1,
                f.has_audio,
                f.has_video,
            ),
            reverse=True,
        )
        return formats

    @staticmethod
    def _has_stream(codec: object) -> bool:
        return bool(codec) and codec != "none"

    # Height inference for platforms that don't provide explicit metadata.
    _HEIGHT_RE = re.compile(r"(\d{3,4})p")

    @classmethod
    def _infer_height(cls, raw: dict) -> int | None:
        """Try to pull a resolution height from format_note or the URL itself.

        LinkedIn URLs look like ``/mp4-720p-30fp-crf28/…`` — this helper
        picks up the ``720`` and returns it as an int.
        """
        for field in ("format_note", "format", "url"):
            value = raw.get(field)
            if not isinstance(value, str):
                continue
            m = cls._HEIGHT_RE.search(value)
            if m:
                return int(m.group(1))
        return None

    # -- download resolution ------------------------------------------------------
    def resolve_format(self, url: str, format_id: str) -> ResolvedFormat:
        """Re-extract and validate ``format_id`` against fresh data.

        Never trusts the browser-supplied format id on its own.
        """
        if not _FORMAT_ID_RE.fullmatch(format_id):
            raise FormatNotAvailableError("The requested format id is invalid.")

        info = self.get_info(url)
        title = info.get("title")

        for raw in info.get("formats") or []:
            if str(raw.get("format_id")) != format_id:
                continue
            ext = str(raw.get("ext") or "mp4")
            has_video = self._has_stream(raw.get("vcodec"))
            has_audio = self._has_stream(raw.get("acodec"))

            # Progressive mp4 without explicit codec info (LinkedIn, FB, etc.)
            if not has_video and not has_audio:
                direct_url = raw.get("url")
                if direct_url and ext in ("mp4", "webm", "m4v"):
                    has_video = True
                    has_audio = True

            needs_mux = has_video and not has_audio
            direct_url = raw.get("url")
            if needs_mux or not direct_url:
                return ResolvedFormat(
                    format_id=format_id,
                    ext=ext,
                    title=title,
                    direct_url=None,
                    needs_mux=True,
                    filesize=None,
                )
            filesize = raw.get("filesize") or raw.get("filesize_approx")
            return ResolvedFormat(
                format_id=format_id,
                ext=ext,
                title=title,
                direct_url=str(direct_url),
                needs_mux=False,
                filesize=filesize if isinstance(filesize, int) else None,
            )

        raise FormatNotAvailableError(
            f"Format '{format_id}' is not available for this media."
        )

    # -- mux fallback (temporary file, always deleted) ------------------------------
    def download_to_temp(self, url: str, format_id: str) -> str:
        """Download + merge a video-only format to a temp file.

        Clearly-marked fallback path for formats that cannot be streamed
        directly. The caller MUST delete the returned file when done.
        Raises :class:`MuxingUnavailableError` when ffmpeg is absent.
        """
        if not _FORMAT_ID_RE.fullmatch(format_id):
            raise FormatNotAvailableError("The requested format id is invalid.")
        if shutil.which("ffmpeg") is None:
            raise MuxingUnavailableError()

        tmpdir = tempfile.mkdtemp(prefix="media_dl_")
        outtmpl = os.path.join(tmpdir, "media.%(ext)s")
        opts = {
            **self._base_opts(),
            "format": f"{format_id}+bestaudio/best",
            "outtmpl": outtmpl,
            "merge_output_format": "mp4",
        }
        try:
            with YoutubeDL(opts) as ydl:
                ydl.download([url])
        except (DownloadError, ExtractorError) as exc:
            remove_temp_dir(tmpdir)
            raise MediaUnavailableError(
                "This media could not be retrieved."
            ) from exc

        files = [
            os.path.join(tmpdir, name)
            for name in os.listdir(tmpdir)
            if os.path.isfile(os.path.join(tmpdir, name))
        ]
        if not files:
            remove_temp_dir(tmpdir)
            raise MediaUnavailableError("This media could not be retrieved.")
        logger.info(
            "mux fallback produced temp file",
            extra={"host": safe_host(url)},
        )
        return max(files, key=os.path.getsize)


def remove_temp_dir(path: str) -> None:
    """Best-effort removal of a temp dir created by :meth:`MediaExtractor.download_to_temp`."""
    try:
        shutil.rmtree(path, ignore_errors=True)
    except Exception:
        logger.warning("failed to remove temp dir", extra={"path": path})
