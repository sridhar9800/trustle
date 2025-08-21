# Trustle Task Scheduler - Solution

## Overview
A FastAPI-based task scheduler with a persistent PostgreSQL backend and an in-process scheduler that supports non-overlapping per-task execution, concurrent different tasks, interval and one-time schedules, and durable state across restarts. Packaged with Docker, docker-compose for local dev, and Kubernetes manifests tailored for Minikube.

Key modules:
- `app/models.py`: SQLAlchemy models `Task`, `Execution` and enums.
- `app/scheduler.py`: Background scheduler with thread pool, Postgres row locking to prevent self-overlap.
- `app/tasks.py`: Task executors for `sleep`, `counter`, `http` types.
- `app/api.py`: CRUD and query endpoints.
- `app/main.py`: FastAPI app wiring and lifecycle hooks.
 - `app/config.py`: Centralized settings (env-driven), logging knobs.
 - `app/db.py`: SQLAlchemy engine and session setup (with `echo` toggle).

## Design Decisions
- **Persistence**: PostgreSQL via SQLAlchemy ORM. Tables are created on startup in `app/main.py` (`Base.metadata.create_all`), after a DB readiness check.
- **Non-overlap & Concurrency**: Use `SELECT ... FOR UPDATE SKIP LOCKED` to atomically pick due tasks and flip `running=true` before queuing work; per-task `running` flag avoids self-overlap. Different tasks can proceed concurrently via `ThreadPoolExecutor`.
- **Scheduling semantics**:
  - `interval`: `next_run_at = now + interval_seconds` set when picked up. Ensures consistent progression even if execution takes time; no drift accumulation due to tick granularity.
  - `once`: `next_run_at` is cleared after selection so job will not repeat.
- **Resilience**: If the app crashes while `running=true`, the task would remain locked out. A production-ready system would include a heartbeat/lease or stuck-run recovery. For this challenge scope, we keep it simple.
- **Config**: `app/config.py` with `.env` support. `SCHEDULER_ENABLE` allows disabling scheduler during specialized tests (we enable it in tests here).
- **HTTP task**: default target is `https://httpbin.org/status/200`, overridable via env or task params.

### Bonus Features Implemented
- **API key authentication**: If `API_KEY` is set, all API routes require header `x-api-key: <API_KEY>`. See `app/api.py`.
- **Cron scheduling**: `schedule_type="cron"` with `cron_expression` using `croniter`. `next_run_at` auto-computed on creation and on each tick. See `app/scheduler.py` and `app/api.py`.
- **Soft task timeouts**: Per-task `timeout_seconds` or global `DEFAULT_TASK_TIMEOUT_SECONDS` (default 30s). Executions exceeding timeout are marked `timeout`. See `app/scheduler.py`.
- **Comprehensive logging**:
  - Configurable via `LOG_LEVEL`, `LOG_JSON`, and `SQLALCHEMY_ECHO` (see `app/config.py`).
  - Root logger configured at startup in `app/main.py` (plain text or JSON). HTTP middleware logs method/path/status/duration/client.
  - `app/scheduler.py` logs ticks, dispatches, execution start/finish, durations, and next scheduling.
  - `app/tasks.py` logs task-specific details (`sleep`, `counter`, `http`) and errors.
  - `app/api.py` logs create/update/delete and query counts. `/healthz` is public for probes.
- **CLI client**: `app/client.py` using Typer. Supports listing tasks, creating tasks (interval/once/cron), viewing executions, and deleting. Uses `API_URL` and `API_KEY` env vars.

## API Endpoints
- `POST /tasks` Schedule a task
- `PATCH /tasks/{id}` Update schedule/params
- `GET /tasks/{id}` Get task
- `GET /tasks/{id}/executions` Execution history for a task
- `GET /executions` All executions (desc)
- `GET /upcoming` Tasks with a `next_run_at`
- `DELETE /tasks/{id}` Delete a task
- `GET /healthz` Health probe (no auth)

Schemas are in `app/schemas.py`. See auto docs at `/docs`.

### Using the endpoints in Docker (docker-compose)
Once the stack is up (`make compose-up` or `bash scripts/compose-up.sh`), the API is at `http://localhost:8000` and the default API key is `changeme` (see `docker-compose.yml`).

- Health (no auth):
```bash
curl http://localhost:8000/healthz
```

- Create a task (interval sleep):
```bash
curl -X POST http://localhost:8000/tasks \
  -H 'Content-Type: application/json' \
  -H 'x-api-key: changeme' \
  -d '{
        "name":"demo-sleep",
        "type":"sleep",
        "schedule_type":"interval",
        "interval_seconds":2,
        "params":{"duration":1}
      }'
```

- List tasks:
```bash
curl -H 'x-api-key: changeme' http://localhost:8000/tasks
```

- Get executions for task id 1:
```bash
curl -H 'x-api-key: changeme' http://localhost:8000/tasks/1/executions
```

- Delete task id 1:
```bash
curl -X DELETE -H 'x-api-key: changeme' http://localhost:8000/tasks/1
```

### Using the endpoints on Minikube
Deploy with `make mk-image && make mk-deploy`. The service `task-scheduler` is a NodePort on 30080 in namespace `trustle` (see `k8s/api.yaml`).

- Get the URL (creates a local tunnel; keep terminal open):
```bash
minikube service -n trustle task-scheduler --url
```
Use the printed URL in place of `$URL` below.

- Health:
```bash
URL=$(minikube service -n trustle task-scheduler --url | tail -n1)
curl "$URL/healthz"
```

- Create a task (interval sleep):
```bash
curl -X POST "$URL/tasks" \
  -H 'Content-Type: application/json' \
  -H 'x-api-key: changeme' \
  -d '{
        "name":"demo-sleep",
        "type":"sleep",
        "schedule_type":"interval",
        "interval_seconds":2,
        "params":{"duration":1}
      }'
```

- List tasks:
```bash
curl -H 'x-api-key: changeme' "$URL/tasks"
```

- Port-forward alternative (simple localhost without tunnel):
```bash
kubectl -n trustle port-forward svc/task-scheduler 8000:8000
# in another terminal
curl -H 'x-api-key: changeme' http://localhost:8000/tasks
```

## Architecture (Mermaid)

```mermaid
flowchart LR
    Client-->API[FastAPI Router]
    API-->DB[(PostgreSQL)]
    API-->Sched[Scheduler Thread]
    Sched-->Pool[ThreadPoolExecutor]
    Pool-->Tasks[Task Runners]
    Tasks--writes-->DB
    Sched--reads/writes-->DB
```

### Scheduler tick and execution
```mermaid
sequenceDiagram
    participant T as Scheduler
    participant DB as PostgreSQL
    participant E as Executor Thread
    T->>DB: SELECT due tasks FOR UPDATE SKIP LOCKED
    DB-->>T: rows (due tasks)
    T->>DB: set running=true
    T->>DB: compute next_run_at
    T->>E: submit(task_id)
    E->>DB: insert Execution(status=running)
    E->>E: run task (sleep/counter/http)
    E->>DB: update Execution(status, result, finished_at)
    E->>DB: set task.running=false
    E->>DB: compute next_run_at
```

## Testing Strategy
- **What runs**: Pytest executes end-to-end tests against a live FastAPI app with the in-process scheduler and a PostgreSQL instance launched via Testcontainers.
- **Scenarios covered** (`tests/test_scheduler.py`):
  - Create an interval `sleep` task (e.g., 2s) and verify an `Execution` record with correct result fields (slept seconds).
  - Validate task state transitions: `running` flag, `next_run_at` updates after execution, and persisted `params` updates (for `counter`).
  - Exercise the API endpoints used by the client: create, list tasks, fetch executions.

Run tests:
```
make test
```
Requires Docker daemon for Testcontainers.

Run tests inside Docker (Testcontainers-in-Docker):
```
docker build -t trustle-task-scheduler:local .
docker compose -f docker-compose.yml -f docker-compose.tests.yml run --rm tests
```
Notes:
- `docker-compose.tests.yml` mounts the Docker socket and project, sets `TESTCONTAINERS_RYUK_DISABLED=true`, `PYTHONPATH=/app`, and `TESTCONTAINERS_HOST_OVERRIDE=host.docker.internal` with `extra_hosts` for connectivity.

## Local Development
- Python virtualenv: `make venv`
- Run locally (expects Postgres running at `DATABASE_URL`):
```
export DATABASE_URL=postgresql://postgres:postgres@localhost:5432/trustle
export SCHEDULER_ENABLE=true
make run
```
- Or with Docker Compose (brings up Postgres + API):
```
make compose-up
```
Visit `http://localhost:8000/docs`.

## Docker
- Build local image: `make docker-build`
- Compose stack: `make compose-up`
  - Sets `API_KEY=changeme` by default; include `-H 'x-api-key: changeme'` when calling the API.

## Minikube Deployment
Prereqs: `minikube`, `kubectl`.

Steps:
1. Point Docker build to Minikube and build image:
```
make mk-image
```
2. Deploy manifests:
```
make mk-deploy
```
3. Get URL:
```
make mk-url
```
This uses a NodePort service `task-scheduler` on port `30080` within namespace `trustle`.
The deployment sets `API_KEY=changeme`; pass `-H 'x-api-key: changeme'` when calling the service.

Manifests:
- `k8s/postgres.yaml`: Namespace `trustle`, Postgres `Secret`, `PVC`, `Deployment`, `Service`.
- `k8s/api.yaml`: API `Deployment` + `Service` (NodePort). The app reads `DATABASE_URL` pointing to the Postgres service.

## Trade-offs & Future Enhancements
- **Stuck runs**: Add timeout, lease/heartbeat columns (e.g., `running_since`, `run_timeout_sec`) and periodic recovery.
- **Multiple replicas**: Current `FOR UPDATE SKIP LOCKED` design supports multiple API pods safely coordinating on the same DB.
- **Observability**: Metrics and tracing could complement the current comprehensive logging.
- **Auth/Rate limit**: Could add FastAPI dependencies or gateways for auth; rate-limiting via a proxy or token bucket.



## How I Used AI (targeted to tooling)
- **Docker**
  - Goal: Build a reproducible image and compose stack (API + Postgres) and run tests inside Docker.
  - Prompts:
    - “Create a Dockerfile for a FastAPI app with uvicorn and system deps for psycopg2; expose 8000.”
    - “Write a docker-compose.yml for api+postgres with proper DATABASE_URL and ports.”
    - “Add a compose profile to run pytest with Testcontainers; mount docker socket safely.”
- **Minikube**
  - Goal: Build image directly into Minikube’s Docker, deploy manifests, and expose the service.
  - Prompts:
    - “How to build an image into the Minikube Docker daemon and reference it in a Deployment?”
    - “Provide Kubernetes manifests: Namespace, Postgres (Secret/PVC/Deployment/Service), API Deployment+Service (NodePort).”
    - “Show commands and scripts to deploy and get the service URL on Minikube.”
- **Testing**
  - Goal: Use pytest + Testcontainers for PostgreSQL and exercise real scheduler flows.
  - Prompts:
    - “Write a pytest that spins up Postgres using testcontainers, configures DATABASE_URL, and runs FastAPI app with scheduler enabled.”
    - “Test creating an interval sleep task and assert an execution record with expected fields.”
    - “Demonstrate running tests inside Docker Compose with access to the host Docker daemon.”

- **Diagrams (Mermaid)**
  - Goal: Quickly visualize the architecture and the scheduler’s execution flow.
  - Prompt:
    - “Given a FastAPI service with modules api/scheduler/tasks and a Postgres DB, produce Mermaid diagrams: (1) a flowchart showing Client → FastAPI router → Scheduler thread and DB interactions, and (2) a sequence diagram for one scheduler tick: select due tasks with FOR UPDATE SKIP LOCKED, mark running, compute next_run_at, submit to executor, write Execution running/finished rows, and clear running. Use concise node labels.”
  - I iterated by asking to rename nodes for clarity and ensure edges include ‘reads/writes’ annotations.

## Environment
- Example env: `.env.example`. App settings in `app/config.py`.

## Running Notes
- First startup will create tables automatically.
- The HTTP task reaches out to httpbin; in restricted networks, override URL via env or task params.
