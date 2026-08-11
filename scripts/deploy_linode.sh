#!/usr/bin/env bash
# Deploy TASI Vision lean stack to Linode Nanode
# Usage:
#   export LINODE_HOST=45.79.193.19
#   export SSH_KEY=~/.ssh/tasi_linode
#   ./scripts/deploy_linode.sh

set -euo pipefail

HOST="${LINODE_HOST:-45.79.193.19}"
USER="${LINODE_USER:-root}"
KEY="${SSH_KEY:-$HOME/.ssh/tasi_linode}"
REMOTE_DIR="${REMOTE_DIR:-/opt/tasi-vision}"
BRANCH="${DEPLOY_BRANCH:-cursor/tasi-ai-platform-blueprint-9345}"

SSH=(ssh -i "$KEY" -o StrictHostKeyChecking=accept-new -o IdentitiesOnly=yes "${USER}@${HOST}")
SCP=(scp -i "$KEY" -o StrictHostKeyChecking=accept-new -o IdentitiesOnly=yes)

echo "==> Checking SSH to ${USER}@${HOST}"
"${SSH[@]}" 'echo connected; free -h | head -2; df -h / | tail -1'

echo "==> Installing docker if needed"
"${SSH[@]}" 'command -v docker >/dev/null || (curl -fsSL https://get.docker.com | sh)'
"${SSH[@]}" 'docker compose version >/dev/null 2>&1 || true'

echo "==> Syncing repository"
"${SSH[@]}" "mkdir -p ${REMOTE_DIR}"
# Prefer git clone from GitHub if available; fallback to rsync of workspace
if "${SSH[@]}" "test -d ${REMOTE_DIR}/.git"; then
  "${SSH[@]}" "cd ${REMOTE_DIR} && git fetch origin && git checkout ${BRANCH} && git pull origin ${BRANCH}"
else
  # rsync from local workspace (this machine)
  ROOT="$(cd "$(dirname "$0")/.." && pwd)"
  rsync -az --delete \
    --exclude '.git' \
    --exclude 'node_modules' \
    --exclude '.venv' \
    --exclude 'data/ohlcv' \
    --exclude '__pycache__' \
    -e "ssh -i ${KEY} -o IdentitiesOnly=yes" \
    "${ROOT}/" "${USER}@${HOST}:${REMOTE_DIR}/"
fi

echo "==> Uploading .env (secrets stay on server)"
if [[ -f "${ROOT:-$(cd "$(dirname "$0")/.." && pwd)}/.env" ]]; then
  ROOT="$(cd "$(dirname "$0")/.." && pwd)"
  # Rewrite public URLs for this host
  tmp="$(mktemp)"
  sed \
    -e "s|^ALLOWED_ORIGINS=.*|ALLOWED_ORIGINS=http://${HOST},http://${HOST}:3000,http://${HOST}:80|" \
    -e "s|^VITE_API_URL=.*|VITE_API_URL=http://${HOST}:8000|" \
    -e "s|^VITE_WS_URL=.*|VITE_WS_URL=ws://${HOST}:8000|" \
    "${ROOT}/.env" > "$tmp"
  grep -q '^POSTGRES_PASSWORD=' "$tmp" || echo 'POSTGRES_PASSWORD=changeme_prod' >> "$tmp"
  grep -q '^PUBLIC_API_URL=' "$tmp" || echo "PUBLIC_API_URL=http://${HOST}:8000" >> "$tmp"
  grep -q '^PUBLIC_WS_URL=' "$tmp" || echo "PUBLIC_WS_URL=ws://${HOST}:8000" >> "$tmp"
  "${SCP[@]}" "$tmp" "${USER}@${HOST}:${REMOTE_DIR}/.env"
  rm -f "$tmp"
else
  echo "WARNING: local .env missing — ensure ${REMOTE_DIR}/.env exists on server"
fi

echo "==> Building and starting lean stack"
"${SSH[@]}" "cd ${REMOTE_DIR} && docker compose -f docker-compose.linode.yml up -d --build"

echo "==> Waiting for health"
sleep 8
"${SSH[@]}" "curl -fsS http://127.0.0.1:8000/api/health && echo && curl -fsS http://127.0.0.1:8000/api/stream/status | head -c 400 && echo"

echo "==> Done"
echo "Frontend: http://${HOST}/"
echo "API docs: http://${HOST}:8000/docs"
echo "WS live:  ws://${HOST}:8000/ws/live"
