FROM python:3.12-slim

# Node.js is required for both yt-dlp EJS challenge solving and bgutil PO Token generation
COPY --from=node:22-slim /usr/local/bin/node /usr/local/bin/node
COPY --from=node:22-slim /usr/local/lib/node_modules /usr/local/lib/node_modules
RUN ln -sf /usr/local/lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm

# ffmpeg for media muxing, curl for health checks, git for cloning the provider
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg ca-certificates curl git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /srv/app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Clone and build official bgutil PO Token HTTP provider server
RUN git clone --depth 1 https://github.com/Brainicism/bgutil-ytdlp-pot-provider.git /srv/pot-server \
    && cd /srv/pot-server/server \
    && npm ci \
    && npx tsc

# Create non-root application user and grant permissions
RUN useradd --create-home --uid 10001 appuser \
    && chown -R appuser:appuser /srv/pot-server

COPY --chown=appuser:appuser app ./app
COPY --chown=appuser:appuser entrypoint.sh .
RUN chmod +x entrypoint.sh

USER appuser

EXPOSE 8000

CMD ["./entrypoint.sh"]
