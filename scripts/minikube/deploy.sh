#!/usr/bin/env bash
set -euo pipefail
kubectl apply -f k8s/postgres.yaml
kubectl apply -f k8s/api.yaml
echo "Deployed to Minikube namespace 'trustle'"
