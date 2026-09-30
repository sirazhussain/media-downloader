#!/bin/sh
set -e

# Determine POT provider server location
POT_MAIN=""
if [ -f "/srv/pot-server/server/build/main.js" ]; then
    POT_MAIN="/srv/pot-server/server/build/main.js"
elif [ -f "/srv/pot-server/build/main.js" ]; then
    POT_MAIN="/srv/pot-server/build/main.js"
fi

# Only start local POT provider if POT_PROVIDER_URL is localhost / 127.0.0.1 (or unset)
POT_URL="${POT_PROVIDER_URL:-http://127.0.0.1:4416}"
if echo "$POT_URL" | grep -Eq "127\.0\.0\.1|localhost"; then
    if [ -n "$POT_MAIN" ]; then
        echo "[entrypoint] Starting bgutil PO Token provider on 127.0.0.1:4416..."
        node "$POT_MAIN" --host 127.0.0.1 --port 4416 &
        POT_PID=$!

        # Wait for POT server to become ready (up to 10 seconds)
        for i in $(seq 1 20); do
            if curl -s http://127.0.0.1:4416/ping > /dev/null 2>&1; then
                echo "[entrypoint] bgutil PO Token provider is ready on port 4416."
                break
            fi
            sleep 0.5
        done
    else
        echo "[entrypoint] WARNING: POT provider binary not found, continuing without local provider..."
    fi
else
    echo "[entrypoint] Using external POT provider at $POT_URL"
fi

# Start FastAPI application with uvicorn
echo "[entrypoint] Starting uvicorn on port 8000..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
