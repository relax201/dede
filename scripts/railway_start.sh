#!/bin/sh
set -eu
PORT="${PORT:-8080}"
echo "[tasi] boot PORT=${PORT} STATIC_DIR=${STATIC_DIR:-/app/static}"
ls -la "${STATIC_DIR:-/app/static}" | head -20 || true
python -c "from app.main import app; print('[tasi] app', app.version, 'ok')"
exec python -m uvicorn app.main:app --host 0.0.0.0 --port "${PORT}" --proxy-headers --forwarded-allow-ips='*' --log-level info
