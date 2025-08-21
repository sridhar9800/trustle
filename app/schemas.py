from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional, Literal, Any

TaskType = Literal["sleep", "counter", "http"]
ScheduleType = Literal["interval", "once", "cron"]

class TaskCreate(BaseModel):
    name: str
    type: TaskType
    schedule_type: ScheduleType
    interval_seconds: Optional[int] = Field(default=None, ge=1)
    next_run_at: Optional[datetime] = None
    cron_expression: Optional[str] = None
    params: Optional[dict] = None
    timeout_seconds: Optional[int] = Field(default=None, ge=1)

class TaskUpdate(BaseModel):
    schedule_type: Optional[ScheduleType] = None
    interval_seconds: Optional[int] = Field(default=None, ge=1)
    next_run_at: Optional[datetime] = None
    cron_expression: Optional[str] = None
    params: Optional[dict] = None
    timeout_seconds: Optional[int] = Field(default=None, ge=1)

class TaskOut(BaseModel):
    id: int
    name: str
    type: TaskType
    schedule_type: ScheduleType
    interval_seconds: Optional[int]
    cron_expression: Optional[str]
    next_run_at: Optional[datetime]
    params: Optional[dict]
    timeout_seconds: Optional[int]
    running: bool

    class Config:
        from_attributes = True

class ExecutionOut(BaseModel):
    id: int
    task_id: int
    started_at: datetime
    finished_at: Optional[datetime]
    status: str
    detail: Optional[str]
    result: Optional[dict]

    class Config:
        from_attributes = True
