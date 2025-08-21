from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    app_name: str = "trustle-task-scheduler"
    database_url: str = Field(default="postgresql://postgres:postgres@localhost:5432/trustle")
    http_task_url: str = Field(default="https://httpbin.org/status/200")
    scheduler_poll_interval_seconds: float = 0.5
    max_worker_threads: int = 8
    scheduler_enable: bool = True
    api_key: str | None = None
    default_task_timeout_seconds: int = 30
    # logging
    log_level: str = Field(default="INFO", description="Python logging level (DEBUG, INFO, WARNING, ERROR)")
    log_json: bool = Field(default=False, description="Emit logs in JSON format if true")
    sqlalchemy_echo: bool = Field(default=False, description="Enable SQLAlchemy engine echo for debugging")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
