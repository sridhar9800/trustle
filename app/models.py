from datetime import datetime
from enum import Enum
from sqlalchemy import Column, Integer, String, DateTime, JSON, Boolean, Text, ForeignKey
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import relationship, Mapped, mapped_column
from app.db import Base

class TaskType(str, Enum):
    SLEEP = "sleep"
    COUNTER = "counter"
    HTTP = "http"

class ScheduleType(str, Enum):
    INTERVAL = "interval"
    ONCE = "once"
    CRON = "cron"

class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    schedule_type: Mapped[str] = mapped_column(String(50), nullable=False)
    interval_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cron_expression: Mapped[str | None] = mapped_column(String(255), nullable=True)
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    params: Mapped[dict | None] = mapped_column(MutableDict.as_mutable(JSON), nullable=True)
    timeout_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    running: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    executions = relationship("Execution", back_populates="task", cascade="all, delete-orphan")

class Execution(Base):
    __tablename__ = "executions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"), index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="running")
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    result: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    task = relationship("Task", back_populates="executions")
