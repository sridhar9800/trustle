#!/usr/bin/env bash
set -euo pipefail
export API_URL=${API_URL:-http://localhost:8000}
# API_KEY is optional; pass via environment when needed
python -m app.client "$@"
