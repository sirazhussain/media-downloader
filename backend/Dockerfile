FROM python:3.12-slim

# Node.js is required for both yt-dlp EJS and bgutil PO Token generation
COPY --from=node:22-slim /usr/local/bin/node /usr/local/bin/node
COPY --from=node:22-slim /usr/local/lib/node_modules /usr/local/lib/node_modules
RUN ln -sf /usr/local/lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm

# ffmpeg is required for the mux fallback path that merges
# video-only + audio streams into a single file for selected qualities.
# curl is used for health checking the local POT server in entrypoint.sh.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /srv/app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy prebuilt bgutil PO Token server from official image
COPY --from=brainicism/bgutil-ytdlp-pot-provider:latest /app /srv/pot-server

# Create non-root application user
RUN useradd --create-home --uid 10001 appuser

COPY --chown=appuser:appuser app ./app
COPY --chown=appuser:appuser entrypoint.sh .
RUN chmod +x entrypoint.sh

USER appuser

EXPOSE 8000

CMD ["./entrypoint.sh"]
