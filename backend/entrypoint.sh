#!/bin/sh
set -e

# Start bgutil PO Token HTTP provider server on port 4416 in background
echo "[entrypoint] Starting bgutil PO Token provider on 127.0.0.1:4416..."
node /srv/pot-server/build/main.js --host 127.0.0.1 --port 4416 &
POT_PID=$!

# Wait for POT server to become ready (up to 10 seconds)
for i in $(seq 1 20); do
    if curl -s http://127.0.0.1:4416/ping > /dev/null 2>&1; then
        echo "[entrypoint] bgutil PO Token provider is ready on port 4416."
        break
    fi
    sleep 0.5
done

# Start FastAPI application with uvicorn
echo "[entrypoint] Starting uvicorn on port 8000..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
