# Media Downloader

A full-stack web application that lets users download **media they own or are
authorized to download** from supported public sources. Paste a URL, pick a
quality/format, and the file streams straight through the backend into the
browser's normal download flow — **nothing is ever stored permanently on the
server**.

- **Frontend:** Next.js 14 + TypeScript + Tailwind CSS + shadcn/ui-style components + Lucide icons
- **Backend:** FastAPI (Python 3.12+) + `yt-dlp` (used as a Python library, never shelled out)
- **Storage:** none — no S3, no R2, no database, no Redis. Streaming only.

---

## Table of contents

- [How it works (architecture)](#how-it-works-architecture)
- [Supported platforms](#supported-platforms)
- [Requirements](#requirements)
- [Installation](#installation)
- [Running with Docker](#running-with-docker)
- [API documentation](#api-documentation)
- [Configuration](#configuration)
- [Security](#security)
- [Browser download behavior (important)](#browser-download-behavior-important)
- [Legal / usage notice](#legal--usage-notice)
- [Testing](#testing)
- [Project structure](#project-structure)

---

## How it works (architecture)

### Metadata flow

```
Browser → Next.js → FastAPI POST /api/v1/media/info → yt-dlp
        → normalized metadata + formats → Next.js UI
```

### Download flow

```
Browser → Next.js → FastAPI POST /api/v1/media/download → yt-dlp
        → chunked stream → FastAPI StreamingResponse → Browser
        → user's local Downloads folder
```

Key design points:

- The backend **validates the URL twice** (once on `/info`, again on `/download`)
  and **re-validates the `format_id`** against a fresh extraction — a format ID
  sent by the browser is never trusted blindly.
- Media is **streamed in chunks** (`StreamingResponse`, 64 KiB chunks) directly
  from the source to the HTTP response. There is no "download fully, save to
  disk, then send" step.
- The only exception is when a chosen format is video-only and needs its audio
  muxed: then a **temporary file** is used for the duration of that single
  request and **deleted reliably in a `finally` block**. If muxing isn't
  possible, the API returns a clean `FORMAT_REQUIRES_MUXING_UNAVAILABLE` error
  instead of pretending otherwise.
- Filenames are sanitized (no `/ \ : * ? " < > |`, no control characters, no
  CR/LF header injection) and sent via RFC 5987 `Content-Disposition`.

---

## Supported platforms

Provider-based detection (`PlatformDetector` → `YouTubeProvider`,
`InstagramProvider`) — extensible for future providers.

| Platform | Accepted URLs |
|---|---|
| YouTube | `youtube.com/watch`, `youtube.com/shorts/*`, `youtube.com/embed/*`, `youtu.be/*` |
| Instagram | `instagram.com/reel/*` |

Only **publicly accessible** content is supported. Anything else is rejected
with a clean error — see [Legal / usage notice](#legal--usage-notice).

---

## Requirements

- **Node.js** 20+ and npm
- **Python** 3.12+
- **FFmpeg** — only needed for the (rare) server-side mux fallback path;
  install via your OS package manager (`apt install ffmpeg`, `brew install ffmpeg`,
  or [ffmpeg.org](https://ffmpeg.org/download.html)). Without it, muxed
  downloads return a clear error; everything else works.
- **Docker** (optional) for containerized runs

---

## Installation

### 1. Clone / unzip, then configure

```bash
cd media-downloader
cp .env.example .env   # adjust values as needed
```

### 2. Backend

```bash
cd backend
python -m venv .venv

# macOS / Linux:
source .venv/bin/activate
# Windows (PowerShell):
# .venv\Scripts\Activate.ps1
# Windows (cmd):
# .venv\Scripts\activate.bat

pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Backend runs at `http://localhost:8000`. Interactive API docs at
`http://localhost:8000/docs`.

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at `http://localhost:3000`. It talks to the backend URL in
`NEXT_PUBLIC_API_URL` (defaults to `http://localhost:8000`).

Quick sanity checks:

```bash
# backend health
curl http://localhost:8000/api/v1/health
# → {"status":"ok"}
```

---

### Run Both Together (Frontend + Backend)

Instead of opening two separate terminals manually, you can run both services together with a single command from the project root:

- **PowerShell:**
  ```powershell
  .\start-dev.ps1
  ```
- **Or via npm:**
  ```bash
  npm run dev
  ```

This will automatically check `.env`, dependencies, and start both the FastAPI backend (`http://localhost:8000`) and Next.js frontend (`http://localhost:3000`) in separate windows.

---

## Running with Docker

```bash
cp .env.example .env
docker compose up --build
```

- Frontend → `http://localhost:3000`
- Backend → `http://localhost:8000`

Services: `frontend`, `backend`. No database/Redis containers — none are needed
for the MVP.

---

## API documentation

### `GET /api/v1/health`

```json
{ "status": "ok" }
```

### `POST /api/v1/media/info`

Request:

```json
{ "url": "https://www.youtube.com/watch?v=..." }
```

Response — normalized (raw yt-dlp internals are not exposed):

```json
{
  "platform": "youtube",
  "id": "dQw4w9WgXcQ",
  "title": "Example Video",
  "thumbnail": "https://...",
  "duration": 212,
  "uploader": "Example Channel",
  "formats": [
    {
      "format_id": "18",
      "ext": "mp4",
      "quality": "360p",
      "width": 640,
      "height": 360,
      "filesize": 12345678,
      "has_video": true,
      "has_audio": true
    }
  ]
}
```

Qualities are derived from the **actual** formats yt-dlp reports — nothing is
hard-coded. Video-only (`has_audio: false`) and audio-only formats are labeled
explicitly.

Errors use a uniform envelope:

```json
{ "error": { "code": "MEDIA_UNAVAILABLE", "message": "This media is currently unavailable." } }
```

No tracebacks, filesystem paths, or secrets are ever returned.

### `POST /api/v1/media/download`

Request:

```json
{ "url": "https://www.youtube.com/watch?v=...", "format_id": "18" }
```

Response: `200` with the media bytes streamed and headers like:

```
Content-Type: video/mp4
Content-Disposition: attachment; filename="Example Video.mp4"; filename*=UTF-8''Example%20Video.mp4
```

The browser then performs a normal file download.

---

## Configuration

All settings are environment-driven (see `.env.example`):

| Variable | Default | Purpose |
|---|---|---|
| `CORS_ORIGINS` | `http://localhost:3000` | Allowed frontend origins (comma-separated; never `*` in prod) |
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | Backend base URL for the frontend |
| `MAX_URL_LENGTH` | `2048` | Rejected if longer |
| `MAX_DOWNLOAD_BYTES` | `2147483648` (2 GiB) | Stream aborts past this |
| `MAX_DURATION_SECONDS` | `14400` (4 h) | Media longer than this is refused |
| `RATE_LIMIT_INFO_PER_MIN` | `20` | Per-IP limit on `/media/info` |
| `RATE_LIMIT_DOWNLOAD_PER_MIN` | `5` | Per-IP limit on `/media/download` |
| `REQUEST_TIMEOUT_SECONDS` | `30` | yt-dlp socket timeout |
| `LOG_LEVEL` | `INFO` | — |

---

## Security

- **Allowlist URL validation** — only the six supported hosts are accepted;
  everything else (including other video sites) is rejected.
- **SSRF protection** — non-HTTP(S) schemes, IP-literal hosts, `localhost`,
  and hostnames resolving to private/loopback/link-local/multicast/reserved
  ranges are rejected. The downloader cannot be used as an internal-network proxy.
- **In-memory rate limiting** per client IP on both media endpoints, behind a
  small abstract store interface so Redis can replace it later without touching
  route code.
- **Server-side re-validation** — the download endpoint re-validates the URL
  and the `format_id`; client input is never trusted.
- **Safe filenames** — sanitized, length-limited, CR/LF-free.
- **Structured logging** — logs method/path/platform/status/duration/error
  code only. Never full URLs (host only), cookies, tokens, or secrets.
- **No auth material, ever** — no cookies, no `cookies-from-browser`, no login
  flows. Private/login-walled/DRM content fails closed with a clean error.

---

## Browser download behavior (important)

The backend **cannot choose where the file lands on the user's computer**.
It only sends:

```
Content-Disposition: attachment; filename="..."
```

The **browser** decides the final location (usually the user's Downloads
folder, per their browser settings). The UI states this plainly:

> Your download will be saved by your browser.

---

## Legal / usage notice

**Only download content you own or are authorized to download** (your own
uploads, Creative Commons / public-domain works, or content whose creator or
platform explicitly permits downloading).

This application:

- works only with **publicly accessible** content on supported platforms;
- does **not** bypass DRM, paywalls, private accounts, or authentication;
- does **not** use or steal cookies, sessions, or credentials;
- does **not** circumvent access controls.

Users are responsible for respecting platform Terms of Service and applicable
copyright law. If content requires login, is private, or is DRM-protected, the
app refuses it with a clear error instead of attempting a workaround.

---

## Testing

Backend (51 tests, fully offline — network extraction is mocked):

```bash
cd backend
source .venv/bin/activate
python -m pytest tests/ -q
```

Covers: URL validation (valid YouTube/Shorts/`youtu.be`, valid Instagram
reels, bad schemes, unsupported domains, localhost/private-IP literals,
DNS-resolves-to-private, over-long URLs), API error envelopes, rate limiter,
filename sanitization, and stream-target guards.

Frontend:

```bash
cd frontend
npm run typecheck   # tsc --noEmit (strict)
npm run lint
npm run build
```

---

## Project structure

```
media-downloader/
├── frontend/                 # Next.js 14 + TypeScript + Tailwind
│   ├── app/
│   │   ├── page.tsx          # hero + downloader flow
│   │   ├── download/page.tsx # /download?url=… deep link
│   │   ├── layout.tsx
│   │   └── globals.css
│   ├── components/
│   │   ├── downloader/       # UrlInput, MediaPreview, QualitySelector,
│   │   │                     # FormatSelector, DownloadButton,
│   │   │                     # DownloadProgress, ErrorMessage, Downloader
│   │   └── ui/               # shadcn/ui-style primitives
│   ├── lib/                  # api.ts, validators.ts (zod), utils.ts
│   ├── types/media.ts
│   ├── package.json
│   └── Dockerfile
├── backend/                  # FastAPI + yt-dlp (Python library)
│   ├── app/
│   │   ├── main.py           # app factory, CORS, middleware, handlers
│   │   ├── api/routes/       # health.py, media.py
│   │   ├── core/             # config.py, security.py, logging.py
│   │   ├── schemas/          # media.py, download.py (Pydantic)
│   │   ├── services/         # media_service, extractor_service, streaming_service
│   │   └── utils/            # url_validator.py, filename.py
│   ├── tests/                # pytest suite (offline)
│   ├── requirements.txt
│   └── Dockerfile
├── docker-compose.yml
├── .env.example
└── README.md
```
