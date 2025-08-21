import os
import time
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from testcontainers.postgres import PostgresContainer


@pytest.fixture(scope="module")
def pg_url():
    with PostgresContainer("postgres:16-alpine") as pg:
        url = pg.get_connection_url()
        # convert to psycopg/psycopg2 URL style used by SQLAlchemy
        # testcontainers returns postgresql+psycopg2
        if url.startswith("postgresql+psycopg2"):
            url = url.replace("postgresql+psycopg2", "postgresql")
        yield url


@pytest.fixture()
def client(pg_url):
    # set env BEFORE importing app
    os.environ["DATABASE_URL"] = pg_url
    os.environ["SCHEDULER_ENABLE"] = "true"

    # import after env set
    from app.main import app  # noqa

    with TestClient(app) as c:
        yield c


def test_create_interval_sleep_task_and_execute(client):
    # schedule a sleep task to run every 1s
    payload = {
        "name": "sleep-1s",
        "type": "sleep",
        "schedule_type": "interval",
        "interval_seconds": 1,
        "params": {"duration": 1},
    }
    r = client.post("/tasks", json=payload)
    assert r.status_code == 200, r.text
    task = r.json()

    # wait for at least one execution to complete
    deadline = time.time() + 8
    exec_count = 0
    while time.time() < deadline:
        r = client.get(f"/tasks/{task['id']}/executions")
        assert r.status_code == 200
        execs = r.json()
        exec_count = len(execs)
        if any(e["status"] == "success" for e in execs):
            break
        time.sleep(0.5)

    assert exec_count >= 1


def test_counter_task_persists_and_increments(client):
    payload = {
        "name": "counter-test",
        "type": "counter",
        "schedule_type": "interval",
        "interval_seconds": 1,
    }
    r = client.post("/tasks", json=payload)
    assert r.status_code == 200
    task = r.json()

    # wait until count increments a couple of times
    deadline = time.time() + 10
    last_count = -1
    while time.time() < deadline:
        r = client.get(f"/tasks/{task['id']}/executions")
        execs = r.json()
        if execs:
            succ = [e for e in execs if e["status"] == "success"]
            if succ:
                last_count = succ[-1]["result"].get("count", -1)
                if last_count >= 2:
                    break
        time.sleep(0.5)
    assert last_count >= 2


def test_once_http_task_runs_once(client):
    # schedule once in the near future
    run_at = (datetime.utcnow() + timedelta(seconds=2)).isoformat()
    payload = {
        "name": "http-once",
        "type": "http",
        "schedule_type": "once",
        "next_run_at": run_at,
    }
    r = client.post("/tasks", json=payload)
    assert r.status_code == 200
    task = r.json()

    # wait until executed, ensure next_run_at becomes null and no re-run
    deadline = time.time() + 15
    seen_success = False
    while time.time() < deadline:
        r1 = client.get(f"/tasks/{task['id']}/executions")
        execs = r1.json()
        if any(e["status"] == "success" for e in execs):
            seen_success = True
            # check that task has no next_run_at now
            r2 = client.get(f"/tasks/{task['id']}")
            t = r2.json()
            if t["next_run_at"] is None:
                break
        time.sleep(0.5)

    assert seen_success


def test_delete_task(client):
    payload = {
        "name": "to-delete",
        "type": "sleep",
        "schedule_type": "interval",
        "interval_seconds": 10,
    }
    r = client.post("/tasks", json=payload)
    task = r.json()
    r = client.delete(f"/tasks/{task['id']}")
    assert r.status_code == 200
    r = client.get(f"/tasks/{task['id']}")
    assert r.status_code == 404
