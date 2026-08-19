#!/bin/sh
set -eu
PORT="${PORT:-8080}"

# Fix common Railway misconfiguration left from templates
case "${DATABASE_URL:-}" in
  *localhost*|*127.0.0.1*|*@::1*)
    echo "[tasi] overriding broken localhost DATABASE_URL → sqlite"
    export DATABASE_URL="sqlite:////tmp/tasi_vision.db"
    ;;
esac

# Unreachable local Redis blocks the async loop (sync client timeouts).
case "${REDIS_URL:-}" in
  ""|*localhost*|*127.0.0.1*|*::1*|*0.0.0.0*)
    echo "[tasi] disabling local/broken REDIS_URL (fail-open, no Redis)"
    export REDIS_URL="redis://127.0.0.1:6379/0"
    ;;
esac

# Pin release so stale APP_VERSION env does not hide the build
export APP_VERSION="2.4.1"

echo "[tasi] boot PORT=${PORT} STATIC_DIR=${STATIC_DIR:-/app/static} DB=${DATABASE_URL%%\?*} REDIS=${REDIS_URL%%\?*}"
ls -la "${STATIC_DIR:-/app/static}" | head -20 || true
python -c "from app.main import app; print('[tasi] app', app.version, 'ok')"
exec python -m uvicorn app.main:app --host 0.0.0.0 --port "${PORT}" --proxy-headers --forwarded-allow-ips='*' --log-level info
