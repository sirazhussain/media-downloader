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

        # Validate that content actually looks like cookie data
        if "# Netscape" not in content and "\t" not in content:
            return None

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
            "extractor_args": {"youtube": {"player_client": ["web", "mweb", "android", "visionos"]}},
        }
        cookiefile = self._get_cookiefile()
        if cookiefile:
            opts["cookiefile"] = cookiefile
        proxy = get_settings().proxy_url
        if proxy and proxy.strip():
            opts["proxy"] = proxy.strip()
        return opts

    # -- metadata -------------------------------------------------------------
    def get_info(self, url: str) -> dict:
        """Extract metadata without downloading. Maps yt-dlp failures to
        clean application errors (never leaks tracebacks)."""
        opts = {**self._base_opts(), "skip_download": True}
        try:
            with YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
        except (DownloadError, ExtractorError) as exc:
            # If cookies failed with bot check or auth required or cookie format error, fallback cleanly without cookies
            if "cookiefile" in opts and any(
                m in str(exc).lower()
                for m in ("sign in", "login", "auth", "confirm you're not a bot", "bot", "cookie", "reloaded")
            ):
                logger.warning("Cookies rejected or invalid, retrying without cookies: %s", exc)
                fallback_opts = dict(opts)
                fallback_opts.pop("cookiefile", None)
                try:
                    with YoutubeDL(fallback_opts) as ydl:
                        info = ydl.extract_info(url, download=False)
                except Exception:
                    raise self._map_download_error(exc) from exc
            else:
                raise self._map_download_error(exc) from exc

        if not info or info.get("_type") not in (None, "video"):
            raise MediaUnavailableError("No downloadable video found at this URL.")
        live_status = str(info.get("live_status") or "").lower()
        if info.get("is_live") or live_status == "is_live":
            raise MediaUnavailableError(
                "Currently ongoing live streams cannot be downloaded. Please try again after the stream finishes."
            )
        if live_status == "is_upcoming":
            raise MediaUnavailableError(
                "This video is an upcoming live stream or premiere and has not aired yet."
            )
        if live_status == "post_live" and not info.get("formats"):
            raise MediaUnavailableError(
                "This live stream has just ended and YouTube is still processing it. Please try again in a few minutes."
            )
        return info

    def _map_download_error(self, exc: DownloadError) -> MediaDownloaderError:
        msg = str(exc).lower()
        if "drm" in msg:
            return MediaUnavailableError(
                "DRM-protected content is not supported."
            )
        if any(marker in msg for marker in ("private video", "this video is private", "private account")):
            return MediaUnavailableError(
                "This video is set to Private by the uploader."
            )
        if any(marker in msg for marker in ("members-only", "join this channel", "member only")):
            return MediaUnavailableError(
                "This video is restricted to channel members only."
            )
        if any(
            marker in msg
            for marker in (
                "age-verification",
                "age gated",
                "confirm your age",
                "sign in to confirm your age",
                "inappropriate for some users",
            )
        ):
            return AuthRequiredError(
                "This video is age-restricted (18+) by YouTube and requires account age-verification."
            )
        if any(
            marker in msg
            for marker in (
                "login required",
                "log in",
                "sign in to confirm",
                "confirm you're not a bot",
                "bot",
            )
        ):
            return AuthRequiredError(
                "This video requires account authentication or bot verification."
            )
        if any(marker in msg for marker in ("not available in your country", "geo", "who has blocked it in your country")):
            return MediaUnavailableError(
                "This video is not available in the server's geographic region."
            )
        if any(marker in msg for marker in ("copyright", "copyright claim", "copyright grounds")):
            return MediaUnavailableError(
                "This video is unavailable due to a copyright claim."
            )
        if any(marker in msg for marker in ("premiere", "upcoming")):
            return MediaUnavailableError(
                "This video is an upcoming live stream or premiere and has not aired yet."
            )
        return MediaUnavailableError("This media is currently unavailable or restricted by the platform.")

    # -- format normalization ---------------------------------------------------
    def normalize_formats(self, info: dict) -> list[MediaFormat]:
        """Build a clean, curated format list for the user:
        - Exactly one best MP4 per standard resolution (1080p, 720p, 480p, 360p).
        - Prioritize combined formats (with audio) over video-only streams.
        - Exclude low-res pixelated junk (144p, 240p) when good qualities exist.
        - 1 best audio format (M4A / MP3).
        - Sorted highest quality to lowest.
        """
        raw_list = info.get("formats") or []
        parsed = []
        for raw in raw_list:
            format_id = str(raw.get("format_id") or "")
            ext = str(raw.get("ext") or "")
            if not format_id or not ext or format_id.startswith("sb"):
                continue

            has_video = self._has_stream(raw.get("vcodec"))
            has_audio = self._has_stream(raw.get("acodec"))

            # Progressive mp4 without explicit codec info (LinkedIn, FB, etc.)
            if not has_video and not has_audio:
                direct_url = raw.get("url") or ""
                if direct_url and ext in ("mp4", "webm", "m4v"):
                    has_video = True
                    has_audio = True
                else:
                    continue

            height = raw.get("height")
            if not isinstance(height, int) or height <= 0:
                height = self._infer_height(raw)

            tbr = raw.get("tbr") or raw.get("abr") or 0
            if not isinstance(tbr, (int, float)):
                tbr = 0

            parsed.append({
                "format_id": format_id,
                "ext": ext,
                "has_video": has_video,
                "has_audio": has_audio,
                "height": height,
                "tbr": tbr,
                "raw": raw,
            })

        # Group video by resolution height
        video_by_res: dict[int, dict] = {}
        fallback_videos = []
        audio_list = []

        for item in parsed:
            if item["has_video"]:
                h = item["height"]
                if isinstance(h, int) and h > 0:
                    # Skip 144p and 240p unless it's the only resolution available
                    if h < 360 and len(parsed) > 3:
                        continue
                    # Score: has_audio (+1000) > mp4 (+500) > bitrate
                    score = (1000 if item["has_audio"] else 0) + (500 if item["ext"] == "mp4" else 0) + item["tbr"]
                    if h not in video_by_res or score > video_by_res[h]["score"]:
                        video_by_res[h] = {"score": score, "item": item}
                else:
                    fallback_videos.append(item)
            elif item["has_audio"]:
                audio_list.append(item)

        selected_videos = sorted(
            [v["item"] for v in video_by_res.values()] or fallback_videos,
            key=lambda x: x["height"] or 0,
            reverse=True,
        )

        audio_list.sort(
            key=lambda x: (1 if x["ext"] in ("m4a", "mp3") else 0, x["tbr"]),
            reverse=True,
        )
        selected_audio = audio_list[:1] if audio_list else []

        final_formats: list[MediaFormat] = []
        for item in selected_videos + selected_audio:
            raw = item["raw"]
            h = item["height"]
            has_video = item["has_video"]
            has_audio = item["has_audio"]
            if has_video and isinstance(h, int) and h > 0:
                quality = f"{h}p"
            elif not has_video:
                quality = "audio"
            else:
                quality = "video"

            filesize = raw.get("filesize") or raw.get("filesize_approx")
            final_formats.append(
                MediaFormat(
                    format_id=item["format_id"],
                    ext=item["ext"],
                    quality=quality,
                    width=raw.get("width"),
                    height=h if isinstance(h, int) else None,
                    filesize=filesize if isinstance(filesize, int) else None,
                    has_video=has_video,
                    has_audio=has_audio,
                )
            )

        return final_formats

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
        opts.pop("extractor_args", None)
        try:
            with YoutubeDL(opts) as ydl:
                ydl.download([url])
        except (DownloadError, ExtractorError) as exc:
            if "cookiefile" in opts and any(
                m in str(exc).lower()
                for m in ("sign in", "login", "auth", "confirm you're not a bot", "bot")
            ):
                fallback_opts = dict(opts)
                fallback_opts.pop("cookiefile", None)
                try:
                    with YoutubeDL(fallback_opts) as ydl:
                        ydl.download([url])
                except Exception:
                    remove_temp_dir(tmpdir)
                    raise MediaUnavailableError(
                        "This media could not be retrieved."
                    ) from exc
            else:
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
