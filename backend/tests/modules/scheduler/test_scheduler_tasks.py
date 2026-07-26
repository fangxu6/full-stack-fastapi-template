from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest
from sqlmodel import Session, select

from app.core.config import settings
from app.models.scheduler import (
    SchedulerJob,
    SchedulerRun,
    SchedulerRunStatus,
    SchedulerRunTrigger,
)
from app.modules.scheduler import service, tasks
from app.modules.scheduler.config import scheduler_settings
from app.modules.scheduler.contracts import ScheduledTask, ScheduledTaskConfig
from app.schemas.scheduler import SchedulerJobCreate
from tests.utils.user import create_random_user

INVENTORY_RETRY_CLASS = (
    "app.modules.inventory.scheduled_tasks.InventoryDailyReportRetryTask"
)


class SuccessfulTask(ScheduledTask):
    config_model = ScheduledTaskConfig

    def run(self, *, context: object, config: ScheduledTaskConfig) -> None:
        del context, config


class FailingTask(ScheduledTask):
    config_model = ScheduledTaskConfig

    def run(self, *, context: object, config: ScheduledTaskConfig) -> None:
        del context, config
        raise RuntimeError("business failure")


def create_job(*, session: Session, now: datetime) -> SchedulerJob:
    actor = create_random_user(session)
    job = service.create_job(
        session=session,
        actor=actor,
        job_in=SchedulerJobCreate(
            name="Scheduler task test",
            class_path=INVENTORY_RETRY_CLASS,
            cron_expression="* * * * *",
            config={},
        ),
        now=now,
    )
    job.enabled = True
    job.next_run_at = now
    session.add(job)
    session.commit()
    session.refresh(job)
    return job


def test_scan_creates_only_current_minute_run(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    now = datetime(2026, 7, 26, 0, 0, 30, tzinfo=UTC)
    job = create_job(session=db, now=now)
    monkeypatch.setattr(tasks, "utc_now", lambda: now)

    with patch.object(
        tasks.celery_app.tasks["scheduler.execute_run"], "delay"
    ) as delay:
        tasks.scan_due_jobs()

    runs = list(
        db.exec(select(SchedulerRun).where(SchedulerRun.job_id == job.id)).all()
    )
    assert [run.status for run in runs] == [SchedulerRunStatus.QUEUED]
    assert runs[0].id is not None
    delay.assert_any_call(runs[0].id)


def test_scan_skips_missed_time_and_records_overlap(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    now = datetime(2026, 7, 26, 0, 0, 30, tzinfo=UTC)
    missed = create_job(session=db, now=now)
    missed.next_run_at = now - timedelta(minutes=1)
    overlap = create_job(session=db, now=now)
    service.create_run(
        session=db,
        job=overlap,
        trigger=SchedulerRunTrigger.MANUAL_NOW,
        planned_at=now,
        requested_by=overlap.created_by,
        now=now,
    )
    monkeypatch.setattr(tasks, "utc_now", lambda: now)
    monkeypatch.setattr(tasks, "_send_alert", lambda **_: None)

    with patch.object(tasks.celery_app.tasks["scheduler.execute_run"], "delay"):
        tasks.scan_due_jobs()

    db.expire_all()
    assert (
        db.exec(select(SchedulerRun).where(SchedulerRun.job_id == missed.id)).all()
        == []
    )
    skipped = db.exec(
        select(SchedulerRun).where(
            SchedulerRun.job_id == overlap.id,
            SchedulerRun.status == SchedulerRunStatus.SKIPPED,
        )
    ).one()
    assert skipped.error_category == "OVERLAPPING_ACTIVE_RUN"


@pytest.mark.parametrize(
    ("task_class", "expected_status", "expected_category"),
    [
        (SuccessfulTask, SchedulerRunStatus.SUCCEEDED, None),
        (FailingTask, SchedulerRunStatus.FAILED, "EXECUTION_FAILED"),
    ],
)
def test_execute_run_records_safe_terminal_state(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
    task_class: type[ScheduledTask],
    expected_status: SchedulerRunStatus,
    expected_category: str | None,
) -> None:
    now = datetime(2026, 7, 26, 0, 0, tzinfo=UTC)
    job = create_job(session=db, now=now)
    run = service.create_run(
        session=db,
        job=job,
        trigger=SchedulerRunTrigger.MANUAL_NOW,
        planned_at=now,
        requested_by=job.created_by,
        now=now,
    )
    assert run.id is not None
    monkeypatch.setattr(tasks, "resolve_task_class", lambda _: task_class)
    monkeypatch.setattr(tasks, "_send_alert", lambda **_: None)

    tasks.execute_run(run.id)
    tasks.execute_run(run.id)

    db.expire_all()
    persisted = db.get(SchedulerRun, run.id)
    assert persisted is not None
    assert persisted.status is expected_status
    assert persisted.error_category == expected_category
    assert persisted.attempt_count == 1
    assert persisted.finished_at is not None


def test_alert_is_rate_limited_and_cleanup_removes_old_runs(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    now = datetime(2026, 7, 26, 0, 0, tzinfo=UTC)
    job = create_job(session=db, now=now)
    old_run = service.create_run(
        session=db,
        job=job,
        trigger=SchedulerRunTrigger.MANUAL_NOW,
        planned_at=now - timedelta(days=91),
        requested_by=job.created_by,
        status=SchedulerRunStatus.SUCCEEDED,
        now=now - timedelta(days=91),
    )
    assert old_run.id is not None
    monkeypatch.setattr(settings, "SMTP_HOST", "smtp.example.com")
    monkeypatch.setattr(settings, "EMAILS_FROM_EMAIL", "sender@example.com")
    monkeypatch.setattr(
        scheduler_settings, "SCHEDULED_TASK_ALERT_RECIPIENTS", ["ops@example.com"]
    )

    with patch("app.modules.scheduler.tasks.send_email") as send_email:
        tasks._send_alert(
            job_id=job.id or 0,
            kind="FAILURE",
            category="EXECUTION_FAILED",
            summary="Scheduled task execution failed",
            planned_at=now,
        )
        tasks._send_alert(
            job_id=job.id or 0,
            kind="FAILURE",
            category="EXECUTION_FAILED",
            summary="Scheduled task execution failed",
            planned_at=now,
        )

    assert send_email.call_count == 1
    assert service.cleanup_runs(session=db, now=now) == 1
    assert db.get(SchedulerRun, old_run.id) is None
