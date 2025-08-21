import os
import typer
import requests
from typing import Optional
from datetime import datetime

app = typer.Typer(add_completion=False)

API_URL = os.environ.get("API_URL", "http://localhost:8000")
API_KEY = os.environ.get("API_KEY")

def headers():
    h = {"Content-Type": "application/json"}
    if API_KEY:
        h["x-api-key"] = API_KEY
    return h

@app.command()
def list_tasks():
    r = requests.get(f"{API_URL}/tasks", headers=headers())
    r.raise_for_status()
    typer.echo(r.json())

@app.command()
def create(
    name: str = typer.Argument(...),
    task_type: str = typer.Option("sleep", help="sleep|counter|http"),
    schedule: str = typer.Option("interval", help="interval|once|cron"),
    interval_seconds: Optional[int] = typer.Option(None),
    next_run_at: Optional[str] = typer.Option(None, help="ISO datetime for once"),
    cron_expression: Optional[str] = typer.Option(None, help="cron expression"),
    duration: Optional[int] = typer.Option(None, help="sleep duration sec"),
    url: Optional[str] = typer.Option(None, help="http url"),
    timeout_seconds: Optional[int] = typer.Option(None, help="soft timeout sec"),
):
    params = {}
    if duration is not None:
        params["duration"] = duration
    if url is not None:
        params["url"] = url
    payload = {
        "name": name,
        "type": task_type,
        "schedule_type": schedule,
        "interval_seconds": interval_seconds,
        "next_run_at": next_run_at,
        "cron_expression": cron_expression,
        "params": params or None,
        "timeout_seconds": timeout_seconds,
    }
    r = requests.post(f"{API_URL}/tasks", json=payload, headers=headers())
    if r.status_code >= 400:
        typer.secho(r.text, fg=typer.colors.RED)
        raise typer.Exit(1)
    typer.echo(r.json())

@app.command()
def executions(task_id: int):
    r = requests.get(f"{API_URL}/tasks/{task_id}/executions", headers=headers())
    r.raise_for_status()
    typer.echo(r.json())

@app.command()
def delete(task_id: int):
    r = requests.delete(f"{API_URL}/tasks/{task_id}", headers=headers())
    r.raise_for_status()
    typer.echo(r.json())

if __name__ == "__main__":
    app()
