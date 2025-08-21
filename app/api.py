from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from sqlalchemy import select
import logging

from app.db import get_db
from app.models import Task, Execution
from app.schemas import TaskCreate, TaskUpdate, TaskOut, ExecutionOut
from app.config import settings
from croniter import croniter

def require_api_key(x_api_key: str | None = Header(default=None)):
    if settings.api_key and x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Unauthorized")

router = APIRouter(dependencies=[Depends(require_api_key)])
log = logging.getLogger("api")

# table creation happens at app startup (see app.main)

@router.post("/tasks", response_model=TaskOut)
def create_task(payload: TaskCreate, db: Session = Depends(get_db)):
    log.info("create_task name=%s type=%s schedule=%s", payload.name, payload.type, payload.schedule_type)
    if payload.schedule_type == "interval" and not payload.interval_seconds:
        raise HTTPException(status_code=400, detail="interval_seconds is required for interval schedule")
    if payload.schedule_type == "once" and not payload.next_run_at:
        raise HTTPException(status_code=400, detail="next_run_at is required for once schedule")
    if payload.schedule_type == "cron":
        if not payload.cron_expression:
            raise HTTPException(status_code=400, detail="cron_expression is required for cron schedule")
        # validate cron expression
        try:
            _ = croniter(payload.cron_expression, datetime.utcnow())
        except Exception:
            raise HTTPException(status_code=400, detail="invalid cron_expression")

    task = Task(
        name=payload.name,
        type=payload.type,
        schedule_type=payload.schedule_type,
        interval_seconds=payload.interval_seconds,
        cron_expression=payload.cron_expression,
        next_run_at=(
            payload.next_run_at
            or (
                datetime.utcnow()
                if payload.schedule_type == "interval"
                else (croniter(payload.cron_expression, datetime.utcnow()).get_next(datetime) if payload.schedule_type == "cron" else None)
            )
        ),
        params=payload.params or {},
        timeout_seconds=payload.timeout_seconds,
        running=False,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    log.info("task_created id=%s next_run_at=%s", task.id, task.next_run_at)
    return task

@router.patch("/tasks/{task_id}", response_model=TaskOut)
def update_task(task_id: int, payload: TaskUpdate, db: Session = Depends(get_db)):
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    log.info("update_task id=%s", task_id)

    if payload.schedule_type:
        task.schedule_type = payload.schedule_type
    if payload.interval_seconds is not None:
        task.interval_seconds = payload.interval_seconds
    if payload.next_run_at is not None:
        task.next_run_at = payload.next_run_at
    if payload.cron_expression is not None:
        # validate if provided
        if payload.cron_expression:
            try:
                _ = croniter(payload.cron_expression, datetime.utcnow())
            except Exception:
                raise HTTPException(status_code=400, detail="invalid cron_expression")
        task.cron_expression = payload.cron_expression
    if payload.params is not None:
        task.params = payload.params
    if payload.timeout_seconds is not None:
        task.timeout_seconds = payload.timeout_seconds

    db.add(task)
    db.commit()
    db.refresh(task)
    return task

@router.get("/tasks/{task_id}", response_model=TaskOut)
def get_task(task_id: int, db: Session = Depends(get_db)):
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    log.debug("get_task id=%s", task_id)
    return task

@router.get("/tasks", response_model=list[TaskOut])
def list_tasks(db: Session = Depends(get_db)):
    items = db.query(Task).order_by(Task.id.asc()).all()
    log.debug("list_tasks count=%s", len(items))
    return items

@router.get("/tasks/{task_id}/executions", response_model=list[ExecutionOut])
def get_task_executions(task_id: int, db: Session = Depends(get_db)):
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    execs = db.execute(select(Execution).where(Execution.task_id == task_id).order_by(Execution.started_at.asc())).scalars().all()
    log.debug("get_task_executions task_id=%s count=%s", task_id, len(execs))
    return execs

@router.get("/executions", response_model=list[ExecutionOut])
def list_executions(db: Session = Depends(get_db)):
    execs = db.execute(select(Execution).order_by(Execution.started_at.desc())).scalars().all()
    log.debug("list_executions count=%s", len(execs))
    return execs

@router.get("/upcoming", response_model=list[TaskOut])
def list_upcoming(db: Session = Depends(get_db)):
    tasks = db.query(Task).filter(Task.next_run_at != None).order_by(Task.next_run_at.asc()).all()
    log.debug("list_upcoming count=%s", len(tasks))
    return tasks

@router.delete("/tasks/{task_id}")
def delete_task(task_id: int, db: Session = Depends(get_db)):
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    log.info("delete_task id=%s", task_id)
    db.delete(task)
    db.commit()
    return {"deleted": True}

