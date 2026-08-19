#!/usr/bin/env bash
# Helper notes for Railway CLI deploy (requires RAILWAY_TOKEN)
set -euo pipefail

cat <<'EOF'
تاسي فيجن — Railway deploy hints
================================

1) Create token: https://railway.app/account/tokens
2) export RAILWAY_TOKEN=...
3) railway whoami

Dashboard path (no CLI):
  See docs/RAILWAY.md
  Services: Postgres + Redis + api (Dockerfile.railway.api) + web (Dockerfile.railway.web)

CLI sketch:
  railway init
  railway add --database postgres
  railway add --database redis
  # Then create/link api + web services and set variables from docs/RAILWAY.md
EOF
