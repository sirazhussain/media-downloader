"""yt-dlp integration used strictly as a Python library.

Design principles:
- Only publicly accessible media is retrieved. Private, login-gated, or DRM-protected
  media raises structured application errors.
- By default, operations run without user credentials using PO Token generation.
- Optional Netscape cookie support (via YOUTUBE_COOKIES) is available for self-hosted instances.
- PO Token Provider (bgutil HTTP server) handles YouTube Proof-of-Origin challenge tokens.
- Media retrieval for YouTube is executed by yt-dlp natively to preserve session context and avoid 403 Forbidden errors.
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


class YtDlpLogger:
    """Routes yt-dlp internal messages to Python's logging system."""

    def debug(self, msg: str) -> None:
        if not msg.startswith("[debug] "):
            logger.debug("yt-dlp: %s", msg)

    def info(self, msg: str) -> None:
        logger.info("yt-dlp: %s", msg)

    def warning(self, msg: str) -> None:
        logger.warning("yt-dlp: %s", msg)

    def error(self, msg: str) -> None:
        logger.error("yt-dlp: %s", msg)


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
        http_headers: dict[str, str] | None = None,
    ) -> None:
        self.format_id = format_id
        self.ext = ext
        self.title = title
        self.direct_url = direct_url
        self.needs_mux = needs_mux
        self.filesize = filesize
        self.http_headers = http_headers or {}


class InfoCache:
    """Thread-safe LRU+TTL cache for extracted media info."""

    def __init__(self, maxsize: int = 200, ttl: int = 300) -> None:
        import time
        from collections import OrderedDict

        self._cache: OrderedDict[str, tuple[float, dict]] = OrderedDict()
        self._maxsize = maxsize
        self._ttl = ttl

    def get(self, url: str) -> dict | None:
        import time

        if url in self._cache:
            ts, info = self._cache[url]
            if time.time() - ts < self._ttl:
                self._cache.move_to_end(url)
                return info
            del self._cache[url]
        return None

    def set(self, url: str, info: dict) -> None:
        import time

        self._cache[url] = (time.time(), info)
        if len(self._cache) > self._maxsize:
            self._cache.popitem(last=False)


class MediaExtractor:
    """Thin, honest wrapper around yt-dlp. All yt-dlp specifics live here."""

    _cache = InfoCache(maxsize=200, ttl=300)

    def __init__(self, *, socket_timeout: int = 30) -> None:
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
    @staticmethod
    def _has_cookies() -> bool:
        """True if cookies are configured."""
        return MediaExtractor._get_cookiefile() is not None

    def _base_opts(
        self,
        *,
        use_cookies: bool = True,
        use_android_client: bool = False,
    ) -> dict:
        """Build yt-dlp options.

        Configures:
        - Custom YtDlpLogger routing to application logging
        - Node.js runtime for JavaScript challenge solving
        - bgutil PO Token HTTP provider on pot_provider_url
        - Netscape cookies if available
        - Android client only when explicitly requested as a last-resort fallback
        """
        settings = get_settings()
        pot_url = settings.pot_provider_url.strip() if settings.pot_provider_url else "http://127.0.0.1:4416"
        opts: dict[str, object] = {
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
            "updatetime": False,
            "continuedl": False,
            "logger": YtDlpLogger(),
            "socket_timeout": self._socket_timeout,
            "retries": 3,
            "js_runtimes": {"node": {}},
            "remote_components": ["ejs:github"],
        }

        extractor_args: dict[str, dict] = {}
        if use_android_client:
            extractor_args["youtube"] = {"player_client": ["android"]}
        else:
            extractor_args["youtubepot-bgutilhttp"] = {"base_url": [pot_url]}

        opts["extractor_args"] = extractor_args

        if use_cookies and self._has_cookies():
            cookiefile = self._get_cookiefile()
            if cookiefile:
                opts["cookiefile"] = cookiefile

        proxy = settings.proxy_url
        if proxy and proxy.strip():
            opts["proxy"] = proxy.strip()

        return opts

    # -- metadata -------------------------------------------------------------
    _BOT_MARKERS = ("sign in to confirm", "confirm you're not a bot", "bot verification", "sign in with your google")

    def get_info(self, url: str, use_cache: bool = True) -> dict:
        """Extract metadata without downloading.

        Platform-aware extraction:
        - Non-YouTube (TikTok, Twitter/X, Instagram, etc.): Direct clean extraction.
        - YouTube: Multi-strategy fallback chain (Cookies+PO -> PO Token -> Android client).
        Maps yt-dlp failures to clean application errors.
        Uses TTL cache to prevent redundant network calls.
        """
        if use_cache:
            cached = self._cache.get(url)
            if cached is not None:
                return cached

        is_youtube = any(yt_host in url.lower() for yt_host in ("youtube.com", "youtu.be"))
        info = None
        last_exc: Exception | None = None

        if not is_youtube:
            # Direct extraction for non-YouTube platforms
            opts = {**self._base_opts(use_cookies=False, use_android_client=False), "skip_download": True}
            try:
                with YoutubeDL(opts) as ydl:
                    info = ydl.extract_info(url, download=False)
            except (DownloadError, ExtractorError) as exc:
                if isinstance(exc, DownloadError):
                    raise self._map_download_error(exc) from exc
                raise MediaUnavailableError("Could not retrieve information for this media.") from exc
        else:
            # --- YouTube Strategy 1: Cookies + PO Token (when cookies provided) ---
            if self._has_cookies():
                opts = {**self._base_opts(use_cookies=True), "skip_download": True}
                try:
                    with YoutubeDL(opts) as ydl:
                        info = ydl.extract_info(url, download=False)
                    logger.info("YouTube extraction succeeded with cookies + PO Token")
                except (DownloadError, ExtractorError) as exc:
                    last_exc = exc
                    logger.warning("YouTube Strategy 1 (cookies) failed: %s", str(exc)[:200])
                    info = None

            # --- YouTube Strategy 2: PO Token without cookies (bot-check bypass from datacenter IPs) ---
            if info is None:
                opts = {**self._base_opts(use_cookies=False, use_android_client=False), "skip_download": True}
                try:
                    with YoutubeDL(opts) as ydl:
                        info = ydl.extract_info(url, download=False)
                    logger.info("YouTube extraction succeeded with PO Token (no cookies)")
                except (DownloadError, ExtractorError) as exc:
                    last_exc = exc
                    logger.warning("YouTube Strategy 2 (PO token without cookies) failed: %s", str(exc)[:200])
                    info = None

            # --- YouTube Strategy 3: Android client fallback (best-effort) ---
            if info is None:
                opts = {**self._base_opts(use_cookies=False, use_android_client=True), "skip_download": True}
                try:
                    with YoutubeDL(opts) as ydl:
                        info = ydl.extract_info(url, download=False)
                    logger.info("YouTube extraction succeeded with android client fallback")
                except (DownloadError, ExtractorError) as exc:
                    err_to_map = exc or last_exc
                    if isinstance(err_to_map, DownloadError):
                        raise self._map_download_error(err_to_map) from err_to_map
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

        self._cache.set(url, info)
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
                "sign in to confirm",
                "confirm you're not a bot",
                "sign in with your google",
            )
        ):
            return AuthRequiredError(
                "This video requires account authentication or bot verification."
            )
        if any(marker in msg for marker in ("not available in your country", "geo restriction", "geo-blocked", "geographically", "who has blocked it in your country")):
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
            if (
                not format_id
                or not ext
                or format_id.startswith("sb")
                or (format_id.startswith("6") and len(format_id) == 3)
            ):
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

        # YouTube direct media URLs (googlevideo.com) are strictly tied to yt-dlp session/IP context
        # and expire quickly. Fetching them via separate HTTP clients (httpx) causes 403 Forbidden.
        # Therefore, YouTube downloads MUST always be retrieved via yt-dlp's download_to_temp.
        is_youtube = any(yt_host in url.lower() for yt_host in ("youtube.com", "youtu.be"))

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

            # Route through yt-dlp download_to_temp if YouTube, mux needed, or direct_url missing
            if is_youtube or needs_mux or not direct_url:
                return ResolvedFormat(
                    format_id=format_id,
                    ext=ext,
                    title=title,
                    direct_url=None,
                    needs_mux=True,
                    filesize=None,
                )
            filesize = raw.get("filesize") or raw.get("filesize_approx")
            http_headers = raw.get("http_headers") or {}
            return ResolvedFormat(
                format_id=format_id,
                ext=ext,
                title=title,
                direct_url=str(direct_url),
                needs_mux=False,
                filesize=filesize if isinstance(filesize, int) else None,
                http_headers=http_headers,
            )

        # Resilient fallback: dynamic streams or format IDs can vary across proxy IPs.
        # Fall back to muxing with yt-dlp which can resolve the stream gracefully.
        logger.info(
            "Format '%s' not found in raw list; falling back to resilient muxing for %s",
            format_id,
            safe_host(url),
        )
        return ResolvedFormat(
            format_id=format_id,
            ext="mp4",
            title=title,
            direct_url=None,
            needs_mux=True,
            filesize=None,
        )

    # -- mux / temp file download (temporary file, always deleted) ------------------
    def download_to_temp(self, url: str, format_id: str) -> str:
        """Download + merge a video format to a temp file via yt-dlp.

        Directs yt-dlp to retrieve media directly, avoiding 403 Forbidden errors
        caused by external HTTP clients fetching googlevideo URLs.
        The caller MUST delete the returned file when done.
        """
        if not _FORMAT_ID_RE.fullmatch(format_id):
            raise FormatNotAvailableError("The requested format id is invalid.")

        has_ffmpeg = shutil.which("ffmpeg") is not None

        if format_id in ("140", "249", "250", "251") or "audio" in format_id.lower():
            format_spec = f"{format_id}/bestaudio/best"
            merge_fmt = "m4a"
        else:
            # First try merging format_id + bestaudio; if format_id already has audio or merging fails,
            # fall back to format_id directly, then bestvideo+bestaudio, then best.
            format_spec = f"{format_id}+bestaudio/{format_id}/bestvideo+bestaudio/best"
            merge_fmt = "mp4"

        # If ffmpeg is absent and format requires muxing, check if fallback is possible
        if not has_ffmpeg and "+" in format_spec:
            # Without ffmpeg, try direct single stream if possible
            format_spec = f"{format_id}/best"

        tmpdir = tempfile.mkdtemp(prefix="media_dl_")
        outtmpl = os.path.join(tmpdir, "media.%(ext)s")

        is_youtube = any(yt_host in url.lower() for yt_host in ("youtube.com", "youtu.be"))
        download_success = False
        last_exc: Exception | None = None

        if not is_youtube:
            # Direct download for non-YouTube platforms (TikTok, Twitter/X, Instagram, etc.)
            opts = {
                **self._base_opts(use_cookies=False, use_android_client=False),
                "format": format_spec,
                "outtmpl": outtmpl,
                "merge_output_format": merge_fmt,
            }
            try:
                with YoutubeDL(opts) as ydl:
                    ydl.download([url])
                download_success = True
            except (DownloadError, ExtractorError) as exc:
                last_exc = exc
                logger.warning("Download failed for %s: %s", safe_host(url), str(exc)[:200])
        else:
            # YouTube Strategy 1: cookies + PO Token (best quality)
            if self._has_cookies():
                opts = {
                    **self._base_opts(use_cookies=True),
                    "format": format_spec,
                    "outtmpl": outtmpl,
                    "merge_output_format": merge_fmt,
                }
                try:
                    with YoutubeDL(opts) as ydl:
                        ydl.download([url])
                    download_success = True
                except (DownloadError, ExtractorError) as exc:
                    last_exc = exc
                    logger.warning("YouTube download attempt with cookies failed: %s", str(exc)[:200])

            # YouTube Strategy 2: PO Token without cookies (bot-check bypass from datacenter IPs)
            if not download_success:
                opts_pot = {
                    **self._base_opts(use_cookies=False, use_android_client=False),
                    "format": format_spec,
                    "outtmpl": outtmpl,
                    "merge_output_format": merge_fmt,
                }
                try:
                    with YoutubeDL(opts_pot) as ydl:
                        ydl.download([url])
                    download_success = True
                except (DownloadError, ExtractorError) as exc:
                    last_exc = exc
                    logger.warning("YouTube download attempt with PO token failed: %s", str(exc)[:200])

            # YouTube Strategy 3: Android client fallback (best-effort)
            if not download_success:
                is_audio = format_id in ("140", "249", "250", "251") or "audio" in format_id.lower()
                android_fmt = "bestaudio/best" if is_audio else f"{format_id}/best[ext=mp4]/best/18"
                fallback_opts = {
                    **self._base_opts(use_cookies=False, use_android_client=True),
                    "format": android_fmt,
                    "outtmpl": outtmpl,
                    "merge_output_format": merge_fmt,
                }
                try:
                    with YoutubeDL(fallback_opts) as ydl:
                        ydl.download([url])
                    download_success = True
                except Exception as exc:
                    last_exc = exc

        if not download_success:
            remove_temp_dir(tmpdir)
            err_to_map = last_exc
            if isinstance(err_to_map, DownloadError):
                raise self._map_download_error(err_to_map) from err_to_map
            raise MediaUnavailableError("This media could not be retrieved.") from err_to_map

        files = [
            os.path.join(tmpdir, name)
            for name in os.listdir(tmpdir)
            if os.path.isfile(os.path.join(tmpdir, name))
        ]
        if not files:
            remove_temp_dir(tmpdir)
            raise MediaUnavailableError("This media could not be retrieved.")
        logger.info(
            "temp file download produced",
            extra={"host": safe_host(url)},
        )
        return max(files, key=os.path.getsize)


def remove_temp_dir(path: str) -> None:
    """Best-effort removal of a temp dir created by :meth:`MediaExtractor.download_to_temp`."""
    try:
        shutil.rmtree(path, ignore_errors=True)
    except Exception:
        logger.warning("failed to remove temp dir", extra={"path": path})
