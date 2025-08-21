import time
from datetime import datetime
from typing import Any
import httpx
from sqlalchemy.orm import Session
from app.models import Task, Execution
from app.config import settings
import logging

log = logging.getLogger("tasks")

def run_sleep_task(db: Session, task: Task) -> dict[str, Any]:
    duration = int(task.params.get("duration", 2)) if task.params else 2
    start = time.perf_counter()
    log.debug("sleep_task start task_id=%s duration=%s", task.id, duration)
    time.sleep(duration)
    elapsed = time.perf_counter() - start
    log.info("sleep_task finish task_id=%s slept=%.3fs", task.id, elapsed)
    return {"slept_seconds": elapsed}


def run_counter_task(db: Session, task: Task) -> dict[str, Any]:
    # store counter in params and persist
    count = int(task.params.get("count", 0)) if task.params else 0
    count += 1
    if task.params is None:
        task.params = {}
    task.params["count"] = count
    db.add(task)
    db.commit()
    log.info("counter_task increment task_id=%s count=%s", task.id, count)
    return {"count": count}


def run_http_task(db: Session, task: Task) -> dict[str, Any]:
    url = (task.params or {}).get("url") or settings.http_task_url
    start = time.perf_counter()
    log.debug("http_task start task_id=%s url=%s", task.id, url)
    with httpx.Client(timeout=10) as client:
        resp = client.get(url)
        elapsed = time.perf_counter() - start
        log.info("http_task finish task_id=%s status=%s elapsed=%.3fs", task.id, resp.status_code, elapsed)
        return {"status_code": resp.status_code, "elapsed_seconds": elapsed}


def execute_task(db: Session, task: Task) -> Execution:
    exec_rec = Execution(task_id=task.id, status="running", started_at=datetime.utcnow())
    db.add(exec_rec)
    db.commit()
    db.refresh(exec_rec)
    try:
        if task.type == "sleep":
            result = run_sleep_task(db, task)
        elif task.type == "counter":
            result = run_counter_task(db, task)
        elif task.type == "http":
            result = run_http_task(db, task)
        else:
            raise ValueError(f"Unknown task type {task.type}")
        exec_rec.status = "success"
        exec_rec.result = result
        exec_rec.finished_at = datetime.utcnow()
    except Exception as e:
        log.exception("task execution error task_id=%s type=%s", task.id, task.type)
        exec_rec.status = "failed"
        exec_rec.detail = str(e)
        exec_rec.finished_at = datetime.utcnow()
    finally:
        db.add(exec_rec)
        db.commit()
    return exec_rec
