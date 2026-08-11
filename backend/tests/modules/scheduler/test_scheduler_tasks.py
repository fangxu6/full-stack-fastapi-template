from datetime import UTC, datetime, timedelta
from inspect import getsource
from threading import Event, Thread
from unittest.mock import patch

import pytest
from sqlmodel import Session, select

from app.core.audit import bind_audit_actor
from app.core.db import engine
from app.models import EmailOutbox, User
from app.models.scheduler import (
    SchedulerJob,
    SchedulerRun,
    SchedulerRunStatus,
    SchedulerRunTrigger,
)
from app.modules.scheduler import (
    orchestration as tasks,
)
from app.modules.scheduler import (
    run_lifecycle,
    scheduler_alerts,
    service,
)
from app.modules.scheduler import (
    tasks as celery_tasks,
)
from app.modules.scheduler.config import scheduler_settings
from app.modules.scheduler.contracts import SchedulerRunOutcome
from app.schemas.scheduler import SchedulerJobCreate
from tests.utils.user import create_random_user

INVENTORY_RETRY_CLASS = (
    "app.modules.inventory.scheduled_tasks.InventoryDailyReportRetryTask"
)


def create_job(*, session: Session, now: datetime) -> SchedulerJob:
    actor = create_random_user(session)
    bind_audit_actor(session=session, actor_id=actor.id)
    job = service.create_job(
        session=session,
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


def test_run_lifecycle_owns_claim_and_terminal_persistence(db: Session) -> None:
    now = datetime(2026, 7, 26, 0, 0, tzinfo=UTC)
    job = create_job(session=db, now=now)
    job.enabled = False
    db.add(job)
    db.commit()
    run = run_lifecycle.create_run(
        session=db,
        job=job,
        trigger=SchedulerRunTrigger.MANUAL_NOW,
        planned_at=now,
        requested_by=job.created_by,
        now=now,
    )
    assert run.id is not None
    db.commit()

    claimed = run_lifecycle.claim_execution(session=db, run_id=run.id, now=now)
    assert claimed is not None
    assert claimed.status is SchedulerRunStatus.RUNNING
    db.commit()

    finished = run_lifecycle.finish_outcome(
        session=db,
        run_id=run.id,
        outcome=SchedulerRunOutcome(
            status=SchedulerRunStatus.SUCCEEDED,
            error_category=None,
            error_summary=None,
        ),
        finished_at=now,
    )
    assert finished is not None
    db.commit()
    db.refresh(finished)
    assert finished.status is SchedulerRunStatus.SUCCEEDED
    assert finished.lease_expires_at is None
    assert finished.next_dispatch_at is None


def test_cancel_queued_runs_locks_before_execution_claim(db: Session) -> None:
    now = datetime(2026, 8, 11, 0, 0, tzinfo=UTC)
    job = create_job(session=db, now=now)
    run = run_lifecycle.create_run(
        session=db,
        job=job,
        trigger=SchedulerRunTrigger.MANUAL_NOW,
        planned_at=now,
        requested_by=job.created_by,
        now=now,
    )
    assert job.id is not None
    assert run.id is not None
    db.commit()

    cancel_session = Session(engine)
    claim_session = Session(engine)
    cancel_selected = Event()
    release_cancel = Event()
    claim_started = Event()
    claim_finished = Event()
    cancelled: list[int] = []
    claimed: list[bool] = []
    errors: list[BaseException] = []
    original_cancel_exec = cancel_session.exec
    original_claim_exec = claim_session.exec

    def pause_cancel_after_select(*args: object, **kwargs: object) -> object:
        result = original_cancel_exec(*args, **kwargs)
        cancel_selected.set()
        assert release_cancel.wait(timeout=5)
        return result

    def note_claim_start(*args: object, **kwargs: object) -> object:
        claim_started.set()
        return original_claim_exec(*args, **kwargs)

    cancel_session.exec = pause_cancel_after_select  # type: ignore[method-assign]
    claim_session.exec = note_claim_start  # type: ignore[method-assign]

    def cancel() -> None:
        try:
            cancelled.append(
                run_lifecycle.cancel_queued_runs(
                    session=cancel_session, job_id=job.id or 0, now=now
                )
            )
            cancel_session.commit()
        except BaseException as error:
            cancel_session.rollback()
            errors.append(error)
        finally:
            cancel_session.close()

    def claim() -> None:
        try:
            claimed.append(
                run_lifecycle.claim_execution(
                    session=claim_session, run_id=run.id or 0, now=now
                )
                is not None
            )
            claim_session.commit()
        except BaseException as error:
            claim_session.rollback()
            errors.append(error)
        finally:
            claim_finished.set()
            claim_session.close()

    cancel_thread = Thread(target=cancel)
    claim_thread = Thread(target=claim)
    cancel_thread.start()
    assert cancel_selected.wait(timeout=5)
    claim_thread.start()
    assert claim_started.wait(timeout=5)
    try:
        assert not claim_finished.wait(timeout=0.2)
    finally:
        release_cancel.set()
        cancel_thread.join(timeout=5)
        claim_thread.join(timeout=5)

    assert not cancel_thread.is_alive()
    assert not claim_thread.is_alive()
    assert errors == []
    assert cancelled == [1]
    assert claimed == [False]
    db.expire_all()
    persisted = db.get(SchedulerRun, run.id)
    assert persisted is not None
    assert persisted.status is SchedulerRunStatus.CANCELLED


def test_scheduler_alerts_reset_job_failure_and_overlap_throttles(
    db: Session,
) -> None:
    now = datetime(2026, 7, 26, 0, 0, tzinfo=UTC)
    job = create_job(session=db, now=now)
    job.enabled = False
    db.add(job)
    db.commit()
    job.run_failure_alerted_at = now
    job.overlap_alerted_at = now
    db.add(job)
    db.commit()

    scheduler_alerts.clear_success_alerts(session=db, job_id=job.id or 0)
    db.commit()
    db.refresh(job)
    assert job.run_failure_alerted_at is None
    assert job.overlap_alerted_at is None


def test_scheduler_alert_timestamp_writes_stay_in_alert_module() -> None:
    assert "configuration_alerted_at" not in getsource(service.update_job)


def test_scheduler_alerts_reset_configuration_throttle(db: Session) -> None:
    now = datetime(2026, 8, 6, 0, 0, tzinfo=UTC)
    job = create_job(session=db, now=now)
    job.configuration_alerted_at = now
    db.add(job)
    db.commit()

    scheduler_alerts.clear_configuration_alert(session=db, job_id=job.id or 0)
    db.commit()

    db.refresh(job)
    assert job.configuration_alerted_at is None


def test_scan_creates_only_current_minute_run(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    now = datetime(2026, 7, 26, 0, 0, 30, tzinfo=UTC)
    job = create_job(session=db, now=now)
    monkeypatch.setattr(tasks, "utc_now", lambda: now)

    with patch.object(
        celery_tasks.celery_app.tasks["scheduler.execute_run"], "delay"
    ) as delay:
        tasks.scan_due_jobs()
        tasks.scan_due_jobs()

    runs = list(
        db.exec(select(SchedulerRun).where(SchedulerRun.job_id == job.id)).all()
    )
    assert [run.status for run in runs] == [SchedulerRunStatus.QUEUED]
    assert runs[0].id is not None
    delay.assert_called_once_with(runs[0].id)
    system_actor = db.exec(select(User).where(User.system_actor_key == "system")).one()
    db.expire_all()
    persisted_job = db.get(SchedulerJob, job.id)
    assert persisted_job is not None
    assert persisted_job.updated_by == system_actor.id


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
    db.commit()
    monkeypatch.setattr(tasks, "utc_now", lambda: now)
    monkeypatch.setattr(tasks, "_send_alert", lambda **_: None)

    with patch.object(celery_tasks.celery_app.tasks["scheduler.execute_run"], "delay"):
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


def test_execute_run_persists_outcome_and_skips_duplicate_execution(
    db: Session, monkeypatch: pytest.MonkeyPatch
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
    db.commit()
    outcome = SchedulerRunOutcome(
        status=SchedulerRunStatus.FAILED,
        error_category="EXECUTION_FAILED",
        error_summary="Scheduled task execution failed",
    )
    execute_calls: list[dict[str, object]] = []
    alert_calls: list[dict[str, object]] = []

    def fake_execute(**kwargs: object) -> SchedulerRunOutcome:
        execute_calls.append(kwargs)
        return outcome

    monkeypatch.setattr(tasks.execution, "execute", fake_execute)
    monkeypatch.setattr(
        tasks,
        "_send_alert",
        lambda **kwargs: alert_calls.append(kwargs),
    )

    tasks.execute_run(run.id)
    tasks.execute_run(run.id)

    db.expire_all()
    persisted = db.get(SchedulerRun, run.id)
    assert persisted is not None
    assert persisted.status is SchedulerRunStatus.FAILED
    assert persisted.error_category == "EXECUTION_FAILED"
    assert persisted.attempt_count == 1
    assert persisted.finished_at is not None
    assert len(execute_calls) == 1
    assert len(alert_calls) == 1
    assert alert_calls[0]["kind"] == "FAILURE"


def test_manual_execution_updates_the_job_as_the_requesting_actor(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    now = datetime(2026, 7, 26, 0, 0, tzinfo=UTC)
    job = create_job(session=db, now=now)
    job.run_failure_alerted_at = now
    db.add(job)
    run = service.run_now(
        session=db, actor_id=job.created_by, job_id=job.id or 0, now=now
    )
    assert run.id is not None
    db.commit()
    monkeypatch.setattr(
        tasks.execution,
        "execute",
        lambda **_: SchedulerRunOutcome(
            status=SchedulerRunStatus.SUCCEEDED,
            error_category=None,
            error_summary=None,
        ),
    )

    tasks.execute_run(run.id)

    db.expire_all()
    persisted_job = db.get(SchedulerJob, job.id)
    assert persisted_job is not None
    assert persisted_job.updated_by == run.requested_by
    assert persisted_job.run_failure_alerted_at is None


def test_lease_reclaim_updates_the_job_as_the_original_requesting_actor(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    now = datetime(2026, 7, 26, 0, 0, tzinfo=UTC)
    job = create_job(session=db, now=now)
    job.run_failure_alerted_at = now
    run = service.run_now(
        session=db, actor_id=job.created_by, job_id=job.id or 0, now=now
    )
    run.status = SchedulerRunStatus.RUNNING
    run.lease_expires_at = now - timedelta(seconds=1)
    db.add_all((job, run))
    db.commit()
    assert run.id is not None
    monkeypatch.setattr(tasks, "utc_now", lambda: now)
    monkeypatch.setattr(
        tasks.execution,
        "execute",
        lambda **_: SchedulerRunOutcome(
            status=SchedulerRunStatus.SUCCEEDED,
            error_category=None,
            error_summary=None,
        ),
    )

    tasks.execute_run(run.id)

    db.expire_all()
    persisted_job = db.get(SchedulerJob, job.id)
    persisted_run = db.get(SchedulerRun, run.id)
    assert persisted_job is not None
    assert persisted_run is not None
    assert persisted_job.updated_by == run.requested_by
    assert persisted_run.attempt_count == 1


def test_scheduler_alert_updates_the_job_as_the_system_actor(db: Session) -> None:
    now = datetime(2026, 7, 26, 0, 0, tzinfo=UTC)
    job = create_job(session=db, now=now)
    system_actor = db.exec(select(User).where(User.system_actor_key == "system")).one()

    tasks._send_alert(
        job_id=job.id or 0,
        kind="FAILURE",
        category="EXECUTION_FAILED",
        summary="Scheduled task execution failed",
        planned_at=now,
        actor_id=system_actor.id,
    )

    db.expire_all()
    persisted_job = db.get(SchedulerJob, job.id)
    assert persisted_job is not None
    assert persisted_job.updated_by == system_actor.id


def test_dispatch_retries_broker_failure_on_the_next_scan_minute(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    now = datetime(2026, 7, 26, 0, 0, 30, tzinfo=UTC)
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
    db.commit()
    monkeypatch.setattr(tasks, "utc_now", lambda: now)

    with patch.object(
        celery_tasks.celery_app.tasks["scheduler.execute_run"],
        "delay",
        side_effect=RuntimeError("broker unavailable"),
    ):
        tasks.dispatch_queued_runs()

    db.expire_all()
    persisted = db.get(SchedulerRun, run.id)
    assert persisted is not None
    assert persisted.status is SchedulerRunStatus.QUEUED
    assert persisted.next_dispatch_at == datetime(2026, 7, 26, 0, 1, tzinfo=UTC)


def test_dispatch_claims_no_more_than_the_fixed_batch_limit(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    now = datetime(2026, 7, 26, 1, 0, tzinfo=UTC)
    actor = create_random_user(db)
    bind_audit_actor(session=db, actor_id=actor.id)
    jobs = [
        SchedulerJob(
            name=f"Dispatch limit {index}",
            class_path=INVENTORY_RETRY_CLASS,
            cron_expression="* * * * *",
            config={},
            enabled=False,
            next_run_at=now,
        )
        for index in range(tasks.DISPATCH_BATCH_SIZE + 1)
    ]
    db.add_all(jobs)
    db.commit()
    db.add_all(
        [
            SchedulerRun(
                job_id=job.id or 0,
                status=SchedulerRunStatus.QUEUED,
                trigger=SchedulerRunTrigger.MANUAL_NOW,
                planned_at=now,
                class_path=job.class_path,
                config={},
                requested_by=actor.id,
                created_at=now,
                next_dispatch_at=now,
            )
            for job in jobs
        ]
    )
    db.commit()
    monkeypatch.setattr(tasks, "utc_now", lambda: now)

    with patch.object(
        celery_tasks.celery_app.tasks["scheduler.execute_run"], "delay"
    ) as delay:
        tasks.dispatch_queued_runs()

    assert tasks.DISPATCH_BATCH_SIZE == 100
    assert delay.call_count == tasks.DISPATCH_BATCH_SIZE


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
    db.commit()
    monkeypatch.setattr(
        scheduler_settings, "SCHEDULED_TASK_ALERT_RECIPIENTS", ["ops@example.com"]
    )
    assert job.created_by is not None

    tasks._send_alert(
        job_id=job.id or 0,
        kind="FAILURE",
        category="EXECUTION_FAILED",
        summary="Scheduled task execution failed",
        planned_at=now,
        actor_id=job.created_by,
    )
    tasks._send_alert(
        job_id=job.id or 0,
        kind="FAILURE",
        category="EXECUTION_FAILED",
        summary="Scheduled task execution failed",
        planned_at=now,
        actor_id=job.created_by,
    )

    assert (
        len(
            db.exec(
                select(EmailOutbox).where(EmailOutbox.recipient == "ops@example.com")
            ).all()
        )
        == 1
    )
    assert service.cleanup_runs(session=db, now=now) == 1
    db.commit()
    assert db.get(SchedulerRun, old_run.id) is None
