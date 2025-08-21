import logging
from fastapi import FastAPI
from app.api import router
from app.scheduler import scheduler
from app.config import settings
from app.db import engine, Base
import time
from sqlalchemy import text
from typing import Callable
from fastapi import Request, Response
import json

app = FastAPI(title="Trustle Task Scheduler")
app.include_router(router)

@app.on_event("startup")
async def on_startup():
    # configure logging
    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    handler = logging.StreamHandler()

    class JsonFormatter(logging.Formatter):
        def format(self, record: logging.LogRecord) -> str:
            payload = {
                "ts": self.formatTime(record, datefmt="%Y-%m-%dT%H:%M:%S%z"),
                "level": record.levelname,
                "logger": record.name,
                "msg": record.getMessage(),
            }
            if record.exc_info:
                payload["exc_info"] = self.formatException(record.exc_info)
            return json.dumps(payload, ensure_ascii=False)

    if settings.log_json:
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(name)s: %(message)s'))
    root_logger.addHandler(handler)
    root_logger.setLevel(level)
    logging.getLogger("uvicorn").setLevel(level)
    logging.getLogger("uvicorn.error").setLevel(level)
    logging.getLogger("uvicorn.access").setLevel(level)
    # wait for DB and create tables
    deadline = time.time() + 60
    last_err = None
    while time.time() < deadline:
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            break
        except Exception as e:
            last_err = e
            time.sleep(1)
    if last_err:
        logging.info("DB readiness check result: %s", type(last_err).__name__)
    # create tables (idempotent)
    Base.metadata.create_all(bind=engine)
    if settings.scheduler_enable:
        scheduler.start()

@app.on_event("shutdown")
async def on_shutdown():
    if settings.scheduler_enable:
        scheduler.stop()

@app.middleware("http")
async def logging_middleware(request: Request, call_next: Callable[[Request], Response]):
    start = time.perf_counter()
    try:
        response = await call_next(request)
        return response
    finally:
        duration = (time.perf_counter() - start) * 1000
        logging.getLogger("http").info(
            "method=%s path=%s status=%s duration_ms=%.2f client=%s",
            request.method,
            request.url.path,
            getattr(response, "status_code", "-"),
            duration,
            request.client.host if request.client else "-",
        )

@app.get("/healthz")
async def healthz():
    return {"status": "ok"}
