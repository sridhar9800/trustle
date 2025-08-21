#!/usr/bin/env bash
set -euo pipefail
IMAGE=${1:-trustle-task-scheduler:local}
docker build -t "$IMAGE" .
