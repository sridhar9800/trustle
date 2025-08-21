#!/usr/bin/env bash
set -euo pipefail
IMAGE=${1:-task-scheduler:minikube}
eval $(minikube -p minikube docker-env)
docker build -t "$IMAGE" .
echo "Built $IMAGE in Minikube docker daemon"
