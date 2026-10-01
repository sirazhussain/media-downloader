# Feature reference

This document describes the functionality currently implemented in Media Downloader. For installation, configuration, API examples, and security guidance, see the [README](README.md).

## Supported URLs

| Platform | Supported public URL types |
| --- | --- |
| YouTube | `youtube.com/watch`, `youtube.com/shorts`, `youtube.com/embed`, and `youtu.be` |
| Instagram | `instagram.com/reel` |

The service intentionally rejects unsupported hosts, non-HTTP(S) schemes, private-network addresses, and DRM-protected media. It does not bypass login or other access controls.

## User flow

1. Paste a supported URL into the web interface.
2. Analyze the media to view its title, thumbnail, uploader, duration, and formats.
3. Select a video or audio format. The interface shows quality, extension, dimensions, and file size when the source reports them.
4. Start the download. The selected media is streamed to the browser, which decides where to save the file.

The `/download?url=...` page accepts a supported URL as a query parameter and starts the analysis flow with the field pre-filled.

## Download handling

- Public metadata and formats are obtained through yt-dlp.
- The backend refreshes the source information and checks the requested format before a download starts.
- Directly available media is relayed in chunks to avoid loading the entire file into memory.
- Some formats need yt-dlp and FFmpeg to retrieve or merge streams. These use a short-lived temporary directory that is removed after streaming completes.
- The API sends `Content-Disposition` headers with a sanitised filename. It cannot choose a user's downloads folder.

## Safeguards

- URL allow-listing and SSRF checks.
- Configurable duration, byte, URL-length, timeout, and rate limits.
- Per-IP in-memory limits for analysis and downloads.
- Safe filenames and a uniform API error format.
- Logging designed to avoid complete URLs and credential material.

## Known deployment considerations

- Rate-limit counters live in the application process. Add an edge limiter or shared store when horizontally scaling.
- Browser downloads can consume substantial client and server bandwidth. Configure the resource limits before public deployment.
- `YOUTUBE_COOKIES` and credential-bearing `PROXY_URL` values are optional server-side secrets. Keep them in a secret manager and out of Git, logs, and client-side variables.
- Platform availability and individual formats can change at any time because source platforms control their public delivery endpoints.
