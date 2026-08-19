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

# Pin release so stale APP_VERSION env does not hide the build
export APP_VERSION="2.3.0"

echo "[tasi] boot PORT=${PORT} STATIC_DIR=${STATIC_DIR:-/app/static} DB=${DATABASE_URL%%\?*}"
ls -la "${STATIC_DIR:-/app/static}" | head -20 || true
python -c "from app.main import app; print('[tasi] app', app.version, 'ok')"
exec python -m uvicorn app.main:app --host 0.0.0.0 --port "${PORT}" --proxy-headers --forwarded-allow-ips='*' --log-level info
