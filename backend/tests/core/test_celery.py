import json
import os
import subprocess
import sys
from pathlib import Path
from typing import cast
from unittest.mock import patch

import pytest
import structlog
from celery.signals import task_postrun, task_prerun  # type: ignore[import-untyped]
from sqlmodel import Session, select

from app.core.celery import celery_app
from app.core.config import settings
from app.core.observability import clear_task_context, configure_observability
from app.core.tasks import runtime_ping, send_scheduled_test_email
from app.models import EmailOutbox, EmailOutboxKind
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
def test_celery_cli_allows_missing_smtp_and_alert_recipients(
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

    assert completed.returncode == 0, completed.stderr


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


def test_celery_worker_import_configures_json_task_events() -> None:
    task_id = "12345678-1234-4234-8234-123456789abc"
    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            "\n".join(
                (
                    "from app.core.celery import celery_app",
                    "celery_app.loader.import_default_modules()",
                    "celery_app.conf.task_always_eager = True",
                    (
                        'result = celery_app.tasks["runtime.ping"].apply_async('
                        f'args=("ping",), task_id="{task_id}")'
                    ),
                    'assert result.get(timeout=1) == "ping"',
                )
            ),
        ],
        capture_output=True,
        cwd=Path(__file__).resolve().parents[2],
        env=os.environ.copy(),
        text=True,
        timeout=10,
    )

    assert completed.returncode == 0, completed.stderr
    payloads = [
        json.loads(line) for line in completed.stdout.splitlines() if line.strip()
    ]
    assert [payload["event_name"] for payload in payloads] == [
        "task.started",
        "task.completed",
    ]
    assert all(
        payload["schema_version"] == 1
        and payload["severity"] == "INFO"
        and payload["task_id"] == task_id
        and payload["task_name"] == "runtime.ping"
        for payload in payloads
    )


def test_eager_task_with_rejected_task_id_emits_no_lifecycle_events(
    capsys: pytest.CaptureFixture[str],
) -> None:
    configure_observability()
    clear_task_context()
    task = celery_app.tasks["runtime.ping"]
    previous = celery_app.conf.task_always_eager
    celery_app.conf.task_always_eager = True
    try:
        result = task.apply_async(args=("ping",), task_id="not-a-canonical-task-id")
    finally:
        celery_app.conf.task_always_eager = previous

    assert result.get(timeout=1) == "ping"
    assert structlog.contextvars.get_contextvars() == {}
    assert capsys.readouterr().out == ""


def test_eager_failure_then_success_emits_isolated_lifecycle_events(
    capsys: pytest.CaptureFixture[str],
) -> None:
    failure_task_name = "runtime.observability_failure"
    failure_task_id = "12345678-1234-4234-8234-123456789abc"
    success_task_id = "22345678-1234-4234-8234-123456789abc"

    @celery_app.task(name=failure_task_name)
    def fail_for_observability_regression() -> None:
        raise RuntimeError("private task failure")

    configure_observability()
    clear_task_context()
    successful_task = celery_app.tasks["runtime.ping"]
    previous = celery_app.conf.task_always_eager
    celery_app.conf.task_always_eager = True
    try:
        failed_result = fail_for_observability_regression.apply_async(
            task_id=failure_task_id
        )
        successful_result = successful_task.apply_async(
            args=("safe-success",), task_id=success_task_id
        )
    finally:
        celery_app.conf.task_always_eager = previous

    assert failed_result.failed()
    assert successful_result.get(timeout=1) == "safe-success"
    assert structlog.contextvars.get_contextvars() == {}

    output = capsys.readouterr().out
    payloads = [json.loads(line) for line in output.splitlines() if line.strip()]
    assert [payload["event_name"] for payload in payloads] == [
        "task.started",
        "task.failed",
        "task.started",
        "task.completed",
    ]
    assert [(payload["task_id"], payload["task_name"]) for payload in payloads] == [
        (failure_task_id, failure_task_name),
        (failure_task_id, failure_task_name),
        (success_task_id, "runtime.ping"),
        (success_task_id, "runtime.ping"),
    ]
    assert all(
        payload["schema_version"] == 1 and payload["severity"] == "INFO"
        for payload in payloads
    )
    assert all(
        set(payload)
        == {
            "environment",
            "event_name",
            "schema_version",
            "severity",
            "task_id",
            "task_name",
            "timestamp",
        }
        for payload in payloads
    )
    assert "private task failure" not in output
    assert "safe-success" not in output


def test_task_lifecycle_logs_safe_success_and_clears_context(
    capsys: pytest.CaptureFixture[str],
) -> None:
    configure_observability()
    clear_task_context()
    task = celery_app.tasks["runtime.ping"]
    task_id = "12345678-1234-4234-8234-123456789abc"

    structlog.contextvars.bind_contextvars(
        request_id="a" * 32,
        actor_kind="authenticated",
    )
    task_prerun.send(
        sender=task,
        task_id=task_id,
        task=task,
        args=("recipient@example.com",),
        kwargs={"token": "secret-token"},
    )

    assert structlog.contextvars.get_contextvars() == {
        "task_id": task_id,
        "task_name": "runtime.ping",
    }

    task_postrun.send(
        sender=task,
        task_id=task_id,
        task=task,
        args=("recipient@example.com",),
        kwargs={"token": "secret-token"},
        retval="private-result",
        state="SUCCESS",
    )

    assert structlog.contextvars.get_contextvars() == {}
    payloads = [line for line in capsys.readouterr().out.splitlines() if line.strip()]
    assert len(payloads) == 2
    assert '"event_name": "task.started"' in payloads[0]
    assert '"event_name": "task.completed"' in payloads[1]
    assert all('"severity": "INFO"' in line for line in payloads)
    assert all(
        secret not in "\n".join(payloads)
        for secret in (
            "recipient@example.com",
            "secret-token",
            "private-result",
            "a" * 32,
        )
    )


def test_task_postrun_logs_failure_without_exception_payload(
    capsys: pytest.CaptureFixture[str],
) -> None:
    configure_observability()
    task = celery_app.tasks["runtime.ping"]
    task_id = "12345678-1234-4234-8234-123456789abc"

    task_prerun.send(
        sender=task,
        task_id=task_id,
        task=task,
        args=("actor-uuid",),
        kwargs={"run_id": "delivery-123"},
    )
    task_postrun.send(
        sender=task,
        task_id=task_id,
        task=task,
        args=("actor-uuid",),
        kwargs={"run_id": "delivery-123"},
        retval=None,
        state="FAILURE",
        exception=RuntimeError("private exception text"),
        traceback="private traceback",
    )

    assert structlog.contextvars.get_contextvars() == {}
    output = capsys.readouterr().out
    assert '"event_name": "task.failed"' in output
    assert '"severity": "INFO"' in output
    assert "actor-uuid" not in output
    assert "delivery-123" not in output
    assert "private exception text" not in output
    assert "private traceback" not in output


def test_task_postrun_clears_context_without_terminal_event(
    capsys: pytest.CaptureFixture[str],
) -> None:
    configure_observability()
    task = celery_app.tasks["runtime.ping"]
    task_id = "12345678-1234-4234-8234-123456789abc"

    task_prerun.send(sender=task, task_id=task_id, task=task, args=(), kwargs={})
    task_postrun.send(
        sender=task,
        task_id=task_id,
        task=task,
        args=(),
        kwargs={},
        retval=None,
        state="RETRY",
    )

    assert structlog.contextvars.get_contextvars() == {}
    output = capsys.readouterr().out
    assert '"event_name": "task.started"' in output
    assert '"event_name": "task.completed"' not in output
    assert '"event_name": "task.failed"' not in output


def test_task_prerun_rejects_invalid_identity_without_binding(
    capsys: pytest.CaptureFixture[str],
) -> None:
    configure_observability()

    class InvalidTask:
        app = celery_app
        name = "celery.fake"

    invalid_task = InvalidTask()

    task_prerun.send(
        sender=invalid_task,
        task_id="caller-controlled-invalid-id",
        task=invalid_task,
        args=("secret",),
        kwargs={"token": "secret-token"},
    )

    assert structlog.contextvars.get_contextvars() == {}
    assert capsys.readouterr().out == ""


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
    assert celery_app.conf.beat_schedule["email-outbox-scan-due"]["task"] == (
        "email_outbox.scan_due"
    )
    assert settings.CELERY_VISIBILITY_TIMEOUT_SECONDS == 3600
    assert "inventory.daily_report.deliver" in celery_app.tasks
    assert "scheduler.scan_due_jobs" in celery_app.tasks
    assert "scheduler.execute_run" in celery_app.tasks
    assert "scheduler.cleanup_runs" in celery_app.tasks
    assert "runtime.send_test_email" in celery_app.tasks
    assert "email_outbox.scan_due" in celery_app.tasks
    assert "email_outbox.deliver" in celery_app.tasks


def test_scheduled_test_email_queues_the_configured_recipient(db: Session) -> None:
    email_data = EmailData(html_content="<p>test</p>", subject="Test email")
    with (
        patch(
            "app.core.tasks.generate_test_email", return_value=email_data
        ) as generate,
    ):
        send_scheduled_test_email()

    recipient = str(settings.EMAIL_TEST_USER)
    generate.assert_called_once_with(email_to=recipient)
    db.expire_all()
    outbox = db.exec(
        select(EmailOutbox).where(EmailOutbox.recipient == recipient)
    ).one()
    assert outbox.kind is EmailOutboxKind.RENDERED
    assert outbox.subject == email_data.subject
    assert outbox.html_content == email_data.html_content
