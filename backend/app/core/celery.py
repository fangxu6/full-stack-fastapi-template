from typing import Any, Literal

from celery import Celery  # type: ignore[import-untyped]
from celery.schedules import crontab  # type: ignore[import-untyped]
from celery.signals import task_postrun, task_prerun  # type: ignore[import-untyped]

from app.core.config import settings
from app.core.observability import (
    bind_task_context,
    clear_task_context,
    configure_observability,
    has_task_context,
    log_event,
    normalize_task_id,
    normalize_task_name,
)
from app.modules.scheduler.config import validate_scheduler_runtime_settings

configure_observability()
validate_scheduler_runtime_settings()

celery_app: Any = Celery(
    "app",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend_url,
    include=[
        "app.core.tasks",
        "app.modules.inventory.tasks",
        "app.modules.scheduler.tasks",
    ],
)
celery_app.conf.update(
    accept_content=["json"],
    broker_connection_retry_on_startup=True,
    broker_transport_options={
        "visibility_timeout": settings.CELERY_VISIBILITY_TIMEOUT_SECONDS
    },
    beat_schedule={
        "runtime-daily-test-email": {
            "task": "runtime.send_test_email",
            "schedule": crontab(hour=9, minute=0),
        },
        "scheduler-scan-due-jobs": {
            "task": "scheduler.scan_due_jobs",
            "schedule": crontab(minute="*"),
        },
        "scheduler-cleanup-runs": {
            "task": "scheduler.cleanup_runs",
            "schedule": crontab(hour=3, minute=30),
        },
    },
    enable_utc=True,
    result_expires=settings.CELERY_RESULT_EXPIRES_SECONDS,
    result_serializer="json",
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_serializer="json",
    timezone="Asia/Shanghai",
    worker_prefetch_multiplier=1,
)


def _registered_application_task_name(sender: Any) -> str | None:
    if getattr(sender, "app", None) is not celery_app:
        return None
    task_name = normalize_task_name(getattr(sender, "name", None))
    if task_name is None:
        return None
    registered_tasks = getattr(celery_app, "tasks", None)
    if registered_tasks is None:
        return None
    return task_name if registered_tasks.get(task_name) is sender else None


def _log_task_prerun(
    *,
    signal: Any,
    sender: Any,
    task_id: Any,
    task: Any,
    **signal_payload: Any,
) -> None:
    del signal, task, signal_payload
    try:
        clear_task_context()
        safe_task_id = normalize_task_id(task_id)
        safe_task_name = _registered_application_task_name(sender)
        if safe_task_id is None or safe_task_name is None:
            return
        if bind_task_context(task_id=safe_task_id, task_name=safe_task_name):
            log_event(event_name="task.started", severity="INFO")
    except Exception:
        clear_task_context()


def _log_task_postrun(
    *,
    signal: Any,
    sender: Any,
    task_id: Any,
    state: Any,
    **signal_payload: Any,
) -> None:
    del signal, sender, task_id, signal_payload
    try:
        event_name: Literal["task.completed", "task.failed"] | None = None
        if state == "SUCCESS":
            event_name = "task.completed"
        elif state == "FAILURE":
            event_name = "task.failed"
        if event_name is not None and has_task_context():
            log_event(event_name=event_name, severity="INFO")
    except Exception:
        pass
    finally:
        clear_task_context()


task_prerun.connect(_log_task_prerun, weak=False)
task_postrun.connect(_log_task_postrun, weak=False)
