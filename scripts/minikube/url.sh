#!/usr/bin/env bash
set -euo pipefail
minikube service -n trustle task-scheduler --url
