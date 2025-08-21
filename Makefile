APP_NAME=trustle-task-scheduler
IMG_LOCAL=$(APP_NAME):local
IMG_MINIKUBE=task-scheduler:minikube

.PHONY: help
help:
	@echo "Common targets:"
	@echo "  make venv             - create venv and install deps"
	@echo "  make run              - run uvicorn locally"
	@echo "  make test             - run pytest on host"
	@echo "  make tests-in-docker  - run pytest inside docker-compose"
	@echo "  make docker-build     - build local docker image"
	@echo "  make compose-up       - run docker-compose (api+postgres)"
	@echo "  make compose-down     - stop and remove compose stack"
	@echo "  make mk-image         - build image into minikube docker daemon"
	@echo "  make mk-deploy        - deploy to minikube"
	@echo "  make mk-url           - show minikube service url"
	@echo "  make client ARGS=...  - run CLI client, e.g., ARGS=\"list_tasks\""

venv:
	bash scripts/setup-venv.sh

run:
	bash scripts/run-local.sh

test:
	bash scripts/run-tests.sh

tests-in-docker:
	bash scripts/tests-in-docker.sh

docker-build:
	bash scripts/docker-build.sh $(IMG_LOCAL)

compose-up:
	bash scripts/compose-up.sh

compose-down:
	bash scripts/compose-down.sh

mk-image:
	bash scripts/minikube/build-image.sh $(IMG_MINIKUBE)

mk-deploy:
	bash scripts/minikube/deploy.sh

mk-url:
	bash scripts/minikube/url.sh

client:
	bash scripts/client.sh $(ARGS)
