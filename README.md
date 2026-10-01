# Media Downloader

A self-hosted web app for downloading public media that you own or are authorised to download. Paste a supported URL, review its available formats, and save the selected file through your browser.

> **Use responsibly.** You are responsible for complying with copyright law and the terms of the source platform. This project is for public content you own or have permission to download. It does not bypass DRM, paywalls, or access controls.

## Features

- Supports YouTube videos, Shorts, embeds, and `youtu.be` links, plus public Instagram Reels.
- Shows a media preview with title, thumbnail, uploader, duration, and available formats.
- Lets users choose video or audio formats, resolution, extension, and reported file size when available.
- Streams downloads to the browser; the browser controls the destination folder and filename prompt.
- Offers a shareable `/download?url=...` route that pre-fills a supported URL.
- Uses FastAPI, Next.js, TypeScript, Tailwind CSS, and Docker Compose.
- Includes a health endpoint and interactive OpenAPI documentation.

## How it works

```text
Browser -> Next.js UI -> FastAPI API -> yt-dlp/source platform
   ^                                             |
   +--------------- streamed download -----------+
```

The API validates the URL, reads public metadata, and validates the selected format again before downloading. Directly streamable formats are proxied in chunks. Formats that need yt-dlp/FFmpeg processing use a temporary directory and are removed after the response is finished; media is not retained as an application library.

## Quick start

### Requirements

- Node.js 20+ and npm
- Python 3.12+
- FFmpeg is recommended for formats that need audio/video merging
- Docker Desktop is optional for containerised setup

### Windows (PowerShell)

```powershell
Copy-Item .env.example .env
.\start-dev.ps1
```

The launcher creates the Python virtual environment and installs frontend packages on first run. It starts the frontend at `http://localhost:3000` and the API at `http://localhost:8000`.

### macOS / Linux or manual setup

In one terminal, start the API:

```bash
cp .env.example .env
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

In a second terminal, start the frontend:

```bash
cd frontend
npm ci
npm run dev
```

Open `http://localhost:3000`, paste a supported public URL, click **Analyze**, select a format, and click **Download**.

### Docker Compose

```bash
cp .env.example .env
docker compose up --build
```

Visit `http://localhost:3000`. Stop the stack with `docker compose down`.

## API

Interactive API documentation is available at `http://localhost:8000/api/docs` while the backend is running.

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/api/v1/health` | Health check |
| `POST` | `/api/v1/media/info` | Read media metadata and available formats |
| `POST` | `/api/v1/media/download` | Stream a selected format |
| `GET` | `/api/v1/media/download` | Browser-friendly download URL |

Example metadata request:

```bash
curl -X POST http://localhost:8000/api/v1/media/info \
  -H "Content-Type: application/json" \
  -d '{"url":"https://www.youtube.com/watch?v=VIDEO_ID"}'
```

Example download request:

```bash
curl -X POST http://localhost:8000/api/v1/media/download \
  -H "Content-Type: application/json" \
  -d '{"url":"https://www.youtube.com/watch?v=VIDEO_ID","format_id":"18"}' \
  --output media.mp4
```

The metadata response includes a `formats` array. Use one of its `format_id` values in the download request. API failures use a stable envelope:

```json
{ "error": { "code": "MEDIA_UNAVAILABLE", "message": "This media is currently unavailable." } }
```

## Configuration and secrets

Copy `.env.example` to `.env`; `.env` is ignored by Git and must never be committed. The example file has placeholders only.

| Variable | Purpose |
| --- | --- |
| `CORS_ORIGINS` | Comma-separated origins allowed to call the API. Set your real frontend origin in production. |
| `NEXT_PUBLIC_API_URL` | Public API base URL embedded into the frontend build. Do not put secrets here. |
| `MAX_URL_LENGTH`, `MAX_DOWNLOAD_BYTES`, `MAX_DURATION_SECONDS` | Input and resource limits. |
| `RATE_LIMIT_INFO_PER_MIN`, `RATE_LIMIT_DOWNLOAD_PER_MIN` | Per-IP limits for metadata and download requests. |
| `REQUEST_TIMEOUT_SECONDS`, `LOG_LEVEL` | Request and logging configuration. |
| `POT_PROVIDER_URL` | Internal PO-token provider address used by the backend. |
| `PROXY_URL` | Optional upstream proxy URL. Treat proxy credentials as a secret. |
| `YOUTUBE_COOKIES` | Optional server-side cookie material. Treat as highly sensitive; never expose it to the frontend or commit it. |

For production, use your deployment platform's secret manager rather than a checked-in `.env` file. Restrict `CORS_ORIGINS`, set sensible download limits, and run the service behind HTTPS and an ingress/reverse proxy with appropriate request limits.

## Security model

- Accepts only recognised YouTube and Instagram URL patterns over HTTP(S).
- Rejects IP-literal hosts, localhost, and addresses that resolve to private, loopback, link-local, multicast, or reserved ranges to mitigate SSRF.
- Revalidates the URL and requested format on the server before each download.
- Applies separate in-memory, per-IP rate limits to metadata and download endpoints. For multi-instance deployments, place a shared limiter at the edge or replace the store with a shared implementation.
- Sanitises download filenames and returns controlled error messages rather than tracebacks or server paths.
- Avoids logging complete user URLs, cookies, tokens, and secrets.

Read [SECURITY.md](SECURITY.md) before reporting a vulnerability.

## Development

Run the backend test suite:

```bash
cd backend
python -m pytest tests -q
```

Run frontend checks:

```bash
cd frontend
npm ci
npm run typecheck
npm run lint
npm run build
```

## Project layout

```text
backend/       FastAPI application, yt-dlp integration, and pytest suite
frontend/      Next.js application and TypeScript UI components
.env.example   Safe environment-variable template
docker-compose.yml
start-dev.ps1  Windows development launcher
```

## Contributing

Contributions are welcome. Please read [CONTRIBUTING.md](CONTRIBUTING.md) and [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md), open an issue for substantial changes, and keep pull requests focused with tests and documentation updates where relevant.

## Security and licence

Security reporting instructions are in [SECURITY.md](SECURITY.md).

**A licence has not been selected yet.** Before publishing this repository as open source, add a `LICENSE` file with the licence you choose. Until then, others do not automatically have permission to reuse the code.
