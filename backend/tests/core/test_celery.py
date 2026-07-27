import os
import subprocess
import sys
from pathlib import Path
from typing import cast
from unittest.mock import patch

import pytest

from app.core.celery import celery_app
from app.core.config import settings
from app.core.tasks import runtime_ping, send_scheduled_test_email
from app.utils import EmailData


def _runtime_environment(tmp_path: Path) -> dict[str, str]:
    environment = os.environ.copy()
    environment.update(
        {
            "APP_ENV_FILE": str(tmp_path / "scheduler-runtime.env"),
            "ENVIRONMENT": "production",
            "FIRST_SUPERUSER": str(settings.FIRST_SUPERUSER),
            "FIRST_SUPERUSER_PASSWORD": settings.FIRST_SUPERUSER_PASSWORD,
            "POSTGRES_DB": settings.POSTGRES_DB,
            "POSTGRES_PASSWORD": settings.POSTGRES_PASSWORD,
            "POSTGRES_SERVER": settings.POSTGRES_SERVER,
            "POSTGRES_USER": settings.POSTGRES_USER,
            "PROJECT_NAME": settings.PROJECT_NAME,
            "REDIS_PASSWORD": settings.REDIS_PASSWORD,
        }
    )
    environment.pop("SMTP_HOST", None)
    environment.pop("EMAILS_FROM_EMAIL", None)
    environment.pop("SCHEDULED_TASK_ALERT_RECIPIENTS", None)
    return environment


@pytest.mark.parametrize("command", ["worker", "beat"])
def test_celery_cli_refuses_missing_alert_runtime_settings(
    tmp_path: Path, command: str
) -> None:
    environment = _runtime_environment(tmp_path)
    (tmp_path / "scheduler-runtime.env").write_text("", encoding="utf-8")

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "celery",
            "-A",
            "app.core.celery:celery_app",
            command,
            "--help",
        ],
        capture_output=True,
        cwd=Path(__file__).resolve().parents[2],
        env=environment,
        text=True,
        timeout=10,
    )

    assert completed.returncode != 0
    assert "require SMTP" in completed.stderr


def test_fastapi_import_does_not_require_alert_runtime_settings(tmp_path: Path) -> None:
    environment = _runtime_environment(tmp_path)
    (tmp_path / "scheduler-runtime.env").write_text("", encoding="utf-8")

    completed = subprocess.run(
        [sys.executable, "-c", "from app.main import app; print(app.title)"],
        capture_output=True,
        cwd=Path(__file__).resolve().parents[2],
        env=environment,
        text=True,
        timeout=10,
    )

    assert completed.returncode == 0, completed.stderr


def test_runtime_ping_executes_eagerly() -> None:
    previous = celery_app.conf.task_always_eager
    celery_app.conf.task_always_eager = True
    try:
        result = celery_app.tasks["runtime.ping"].delay("ping")
    finally:
        celery_app.conf.task_always_eager = previous

    assert result.get(timeout=1) == "ping"


@pytest.mark.parametrize(
    ("value", "message"),
    [(42, "must be a string"), ("x" * 65, "64 characters or fewer")],
)
def test_runtime_ping_rejects_invalid_values(value: object, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        runtime_ping(cast(str, value))


def test_scheduler_beat_tasks_are_registered() -> None:
    celery_app.loader.import_default_modules()

    assert celery_app.conf.timezone == "Asia/Shanghai"
    assert celery_app.conf.beat_schedule["scheduler-scan-due-jobs"]["task"] == (
        "scheduler.scan_due_jobs"
    )
    assert celery_app.conf.beat_schedule["scheduler-cleanup-runs"]["task"] == (
        "scheduler.cleanup_runs"
    )
    assert celery_app.conf.beat_schedule["runtime-daily-test-email"]["task"] == (
        "runtime.send_test_email"
    )
    assert settings.CELERY_VISIBILITY_TIMEOUT_SECONDS == 3600
    assert "inventory.daily_report.deliver" in celery_app.tasks
    assert "scheduler.scan_due_jobs" in celery_app.tasks
    assert "scheduler.execute_run" in celery_app.tasks
    assert "scheduler.cleanup_runs" in celery_app.tasks
    assert "runtime.send_test_email" in celery_app.tasks


def test_scheduled_test_email_uses_the_configured_recipient() -> None:
    email_data = EmailData(html_content="<p>test</p>", subject="Test email")
    with (
        patch(
            "app.core.tasks.generate_test_email", return_value=email_data
        ) as generate,
        patch("app.core.tasks.send_email") as send,
    ):
        send_scheduled_test_email()

    recipient = str(settings.EMAIL_TEST_USER)
    generate.assert_called_once_with(email_to=recipient)
    send.assert_called_once_with(
        email_to=recipient,
        subject=email_data.subject,
        html_content=email_data.html_content,
    )
