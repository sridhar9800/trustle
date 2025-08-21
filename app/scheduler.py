import threading
import time
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
from sqlalchemy import select, update, and_, text
from sqlalchemy.orm import Session
import logging
from croniter import croniter

from app.db import SessionLocal
from app.models import Task
from app.tasks import execute_task
from app.config import settings

class Scheduler:
    def __init__(self):
        self._stop = threading.Event()
        self._executor: ThreadPoolExecutor | None = None
        self._thread: threading.Thread | None = None
        self._log = logging.getLogger("scheduler")

    def start(self):
        # If already running, do nothing
        if self._thread and self._thread.is_alive():
            self._log.info("Scheduler already running")
            return
        self._log.info("Scheduler starting")
        self._stop.clear()
        # Recreate executor if needed (it may have been shut down)
        if self._executor is None:
            self._executor = ThreadPoolExecutor(max_workers=settings.max_worker_threads)
        # Always create a fresh thread on start
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._log.info("Scheduler stopping")
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=5)
        if self._executor:
            self._executor.shutdown(wait=True)
            self._executor = None
        self._thread = None
        # Clear the stop flag so a future start() can proceed
        self._stop.clear()

    def _run(self):
        while not self._stop.is_set():
            try:
                self._tick()
            except Exception:
                # avoid tight loop on unexpected errors
                self._log.exception("Tick error")
                time.sleep(settings.scheduler_poll_interval_seconds)
            time.sleep(settings.scheduler_poll_interval_seconds)

    def _tick(self):
        now = datetime.utcnow()
        with SessionLocal() as db:
            # lock due tasks, avoid overlap by checking running flag and setting it under lock
            due_tasks = db.execute(
                text(
                    """
                    SELECT * FROM tasks
                    WHERE (next_run_at IS NOT NULL AND next_run_at <= :now)
                      AND running = FALSE
                    FOR UPDATE SKIP LOCKED
                    """
                ), {"now": now}
            ).mappings().all()
            self._log.debug("tick at=%s due_count=%d", now.isoformat(), len(due_tasks))

            for row in due_tasks:
                task = db.get(Task, row["id"])
                if not task:
                    continue
                task.running = True
                # compute next_run_at before releasing
                if task.schedule_type == "interval" and task.interval_seconds:
                    current_utc = datetime.utcnow()
                    task.next_run_at = current_utc + timedelta(seconds=task.interval_seconds)
                elif task.schedule_type == "cron" and task.cron_expression:
                    try:
                        itr = croniter(task.cron_expression, now)
                        task.next_run_at = itr.get_next(datetime)
                    except Exception:
                        # invalid cron at runtime -> disable further runs
                        self._log.error("Invalid cron for task %s; disabling future runs", task.id)
                        task.next_run_at = None
                else:
                    task.next_run_at = None
                db.add(task)
                db.commit()
                self._log.info(
                    "dispatch task_id=%s type=%s schedule=%s next_run_at=%s",
                    task.id,
                    task.type,
                    task.schedule_type,
                    task.next_run_at.isoformat() if task.next_run_at else None,
                )
                self._executor.submit(self._run_task_safe, task.id)

    def _run_task_safe(self, task_id: int):
        with SessionLocal() as db:
            task = db.get(Task, task_id)
            if not task:
                return
            try:
                start = time.perf_counter()
                self._log.info("start task_id=%s type=%s", task.id, task.type)
                exec_rec = execute_task(db, task)
                # soft timeout marking: if duration exceeded configured timeout, mark as timeout
                timeout = task.timeout_seconds or settings.default_task_timeout_seconds
                duration = (exec_rec.finished_at - exec_rec.started_at).total_seconds() if exec_rec.finished_at else (time.perf_counter() - start)
                if duration > timeout and exec_rec.status == "success":
                    exec_rec.status = "timeout"
                    exec_rec.detail = f"Exceeded timeout of {timeout}s"
                    db.add(exec_rec)
                    db.commit()
                self._log.info(
                    "finish task_id=%s status=%s duration_s=%.3f",
                    task.id,
                    exec_rec.status,
                    duration,
                )
            finally:
                # mark not running
                task.running = False
                # deterministically schedule the next interval run
                if task.schedule_type == "interval" and task.interval_seconds:
                    now_utc = datetime.utcnow()
                    task.next_run_at = now_utc + timedelta(seconds=task.interval_seconds)
                db.add(task)
                db.commit()

scheduler = Scheduler()
