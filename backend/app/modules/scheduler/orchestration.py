from datetime import UTC, datetime

from sqlmodel import Session, col, select

from app.core.audit import bind_audit_actor, clear_audit_actor, require_system_actor
from app.core.celery import celery_app
from app.core.db import engine
from app.core.exceptions import ConflictError
from app.core.observability import log_event
from app.models.scheduler import (
    SchedulerJob,
    SchedulerRunStatus,
    SchedulerRunTrigger,
)
from app.modules.scheduler import execution, run_lifecycle
from app.modules.scheduler.cron import next_run_at, scheduled_in_current_minute
from app.modules.scheduler.scheduler_alerts import clear_success_alerts
from app.modules.scheduler.scheduler_alerts import send_alert as _send_alert
from app.modules.scheduler.service import (
    LEASE_DURATION,
    utc_now,
    validate_definition,
)

DISPATCH_BATCH_SIZE = 100


def _dispatch_now(now: datetime | None = None) -> datetime:
    if now is None:
        return utc_now()
    if now.tzinfo is None:
        raise ValueError("scheduled task timestamps must be timezone-aware")
    return now.astimezone(UTC)


def _retry_dispatch_on_next_scan(*, run_id: int, now: datetime) -> None:
    with Session(engine) as session:
        run_lifecycle.release_dispatch(session=session, run_id=run_id, now=now)
        session.commit()


def dispatch_queued_runs(
    *, run_ids: list[int] | None = None, now: datetime | None = None
) -> None:
    current = _dispatch_now(now)
    if run_ids is not None and not run_ids:
        return
    with Session(engine) as session:
        dispatch_ids = run_lifecycle.claim_dispatchable_runs(
            session=session,
            now=current,
            run_ids=run_ids,
            lease_duration=LEASE_DURATION,
            limit=DISPATCH_BATCH_SIZE,
        )
        session.commit()
    for run_id in dispatch_ids:
        try:
            celery_app.tasks["scheduler.execute_run"].delay(run_id)
        except Exception:
            _retry_dispatch_on_next_scan(run_id=run_id, now=current)
            log_event(event_name="scheduler.enqueue.failed", severity="ERROR")


def scan_due_jobs() -> None:
    now = utc_now()
    alerts: list[tuple[int, str, str, str, datetime]] = []
    with Session(engine) as session:
        actor_id = require_system_actor(session=session)
        bind_audit_actor(session=session, actor_id=actor_id)
        try:
            jobs = list(
                session.exec(
                    select(SchedulerJob)
                    .where(
                        col(SchedulerJob.enabled).is_(True),
                        col(SchedulerJob.deleted_at).is_(None),
                        col(SchedulerJob.next_run_at) <= now,
                    )
                    .with_for_update(skip_locked=True)
                ).all()
            )
            for job in jobs:
                if job.id is None:
                    raise RuntimeError("scheduled task must be persisted")
                if not scheduled_in_current_minute(job.next_run_at, now=now):
                    job.next_run_at = next_run_at(job.cron_expression, after=now)
                    session.add(job)
                    continue
                planned_at = job.next_run_at
                job.next_run_at = next_run_at(job.cron_expression, after=planned_at)
                session.add(job)
                try:
                    validate_definition(
                        class_path=job.class_path,
                        cron_expression=job.cron_expression,
                        config=job.config,
                    )
                    run_lifecycle.create_run(
                        session=session,
                        job=job,
                        trigger=SchedulerRunTrigger.SCHEDULED,
                        planned_at=planned_at,
                        requested_by=None,
                        now=now,
                    )
                except ValueError:
                    run_lifecycle.create_run(
                        session=session,
                        job=job,
                        trigger=SchedulerRunTrigger.SCHEDULED,
                        planned_at=planned_at,
                        requested_by=None,
                        status=SchedulerRunStatus.FAILED,
                        error_category="CONFIGURATION_INVALID",
                        error_summary="Scheduled task configuration is invalid",
                        require_no_active=False,
                        now=now,
                    )
                    alerts.append(
                        (
                            job.id,
                            "CONFIGURATION",
                            "CONFIGURATION_INVALID",
                            "Scheduled task configuration is invalid",
                            planned_at,
                        )
                    )
                    continue
                except ConflictError:
                    run_lifecycle.create_run(
                        session=session,
                        job=job,
                        trigger=SchedulerRunTrigger.SCHEDULED,
                        planned_at=planned_at,
                        requested_by=None,
                        status=SchedulerRunStatus.SKIPPED,
                        error_category="OVERLAPPING_ACTIVE_RUN",
                        error_summary="Scheduled task has an active run",
                        require_no_active=False,
                        now=now,
                    )
                    alerts.append(
                        (
                            job.id,
                            "OVERLAP",
                            "OVERLAPPING_ACTIVE_RUN",
                            "Scheduled task has an active run",
                            planned_at,
                        )
                    )
                    continue
            session.commit()
        finally:
            clear_audit_actor(session=session)
    dispatch_queued_runs(now=now)
    for job_id, kind, category, summary, planned_at in alerts:
        _send_alert(
            job_id=job_id,
            kind=kind,
            category=category,
            summary=summary,
            planned_at=planned_at,
            actor_id=actor_id,
        )


def execute_run(run_id: int) -> None:
    if not isinstance(run_id, int):
        raise ValueError("scheduler run id must be an integer")
    with Session(engine) as session:
        now = utc_now()
        run = run_lifecycle.claim_execution(
            session=session,
            run_id=run_id,
            now=now,
            lease_duration=LEASE_DURATION,
        )
        if run is None:
            return
        class_path = run.class_path
        config_snapshot = dict(run.config)
        trigger = run.trigger
        planned_at = run.planned_at
        job_id = run.job_id
        actor_id = run.requested_by or require_system_actor(session=session)
        started_at = run.started_at or now
        session.commit()
    outcome = execution.execute(
        run_id=run_id,
        class_path=class_path,
        config_snapshot=config_snapshot,
        actor_id=actor_id,
        trigger=trigger,
        planned_at=planned_at,
        started_at=started_at,
    )
    with Session(engine) as session:
        bind_audit_actor(session=session, actor_id=actor_id)
        try:
            run = run_lifecycle.finish_outcome(
                session=session,
                run_id=run_id,
                outcome=outcome,
            )
            if run is None:
                return
            if outcome.status is SchedulerRunStatus.SUCCEEDED:
                clear_success_alerts(session=session, job_id=job_id)
            session.commit()
        finally:
            clear_audit_actor(session=session)
    if outcome.status is SchedulerRunStatus.FAILED:
        _send_alert(
            job_id=job_id,
            kind=(
                "CONFIGURATION"
                if outcome.error_category == "CONFIGURATION_INVALID"
                else "FAILURE"
            ),
            category=outcome.error_category or "EXECUTION_FAILED",
            summary=outcome.error_summary or "Scheduled task execution failed",
            planned_at=planned_at,
            actor_id=actor_id,
        )


def cleanup_scheduled_runs() -> None:
    with Session(engine) as session:
        run_lifecycle.cleanup_runs(session=session)
        session.commit()
