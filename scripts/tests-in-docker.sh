#!/usr/bin/env bash
set -euo pipefail
docker compose -f docker-compose.yml -f docker-compose.tests.yml run --rm tests "$@"
