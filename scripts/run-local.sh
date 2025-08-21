#!/usr/bin/env bash
set -euo pipefail
export DATABASE_URL=${DATABASE_URL:-postgresql://postgres:postgres@localhost:5432/trustle}
export SCHEDULER_ENABLE=${SCHEDULER_ENABLE:-true}
uvicorn app.main:app --reload
