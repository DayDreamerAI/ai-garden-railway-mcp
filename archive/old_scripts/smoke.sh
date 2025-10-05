#!/usr/bin/env bash
set -euo pipefail
BASE="${1:-}"
if [[ -z "${BASE}" ]]; then
  echo "Usage: ./smoke.sh https://<service>.up.railway.app"
  exit 2
fi
echo "-> /health"
curl -i "${BASE%/}/health" || true
echo
echo "-> /sse (show first lines)"
curl -i -N "${BASE%/}/sse" | head -n 20
