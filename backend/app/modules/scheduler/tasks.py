from datetime import UTC, datetime, timedelta

from pydantic import ValidationError
from sqlmodel import Session, col, select

from app.core.celery import celery_app
from app.core.config import settings
from app.core.db import engine
from app.core.exceptions import ConflictError
from app.core.observability import log_event
from app.models.scheduler import (
    SchedulerJob,
    SchedulerRun,
    SchedulerRunStatus,
    SchedulerRunTrigger,
)
from app.modules.scheduler.config import scheduler_settings
from app.modules.scheduler.contracts import ScheduledTaskContext, ScheduledTaskSkipped
from app.modules.scheduler.cron import next_run_at, scheduled_in_current_minute
from app.modules.scheduler.service import (
    LEASE_DURATION,
    create_run,
    resolve_task_class,
    utc_now,
    validate_definition,
)
from app.utils import send_email

ALERT_INTERVAL = timedelta(hours=1)
DISPATCH_BATCH_SIZE = 100


def _send_alert(
    *,
    job_id: int,
    kind: str,
    category: str,
    summary: str,
    planned_at: datetime,
) -> None:
    now = utc_now()
    with Session(engine) as session:
        job = session.get(SchedulerJob, job_id)
        if job is None:
            return
        if kind == "OVERLAP":
            alerted_at = job.overlap_alerted_at
        elif kind == "CONFIGURATION":
            alerted_at = job.configuration_alerted_at
        else:
            alerted_at = job.run_failure_alerted_at
        if alerted_at is not None and now - alerted_at < ALERT_INTERVAL:
            return
        if kind == "OVERLAP":
            job.overlap_alerted_at = now
        elif kind == "CONFIGURATION":
            job.configuration_alerted_at = now
        else:
            job.run_failure_alerted_at = now
        session.add(job)
        session.commit()
        name = job.name
    recipients = scheduler_settings.SCHEDULED_TASK_ALERT_RECIPIENTS
    if not settings.emails_enabled or not recipients:
        log_event(event_name="scheduler.alert.unsent", severity="WARNING")
        return
    subject = f"{settings.PROJECT_NAME} - Scheduled task alert"
    content = (
        f"<p>Task: {name} (#{job_id})</p>"
        f"<p>Category: {category}</p>"
        f"<p>Planned at: {planned_at}</p>"
        f"<p>Summary: {summary}</p>"
    )
    for recipient in recipients:
        try:
            send_email(email_to=str(recipient), subject=subject, html_content=content)
        except Exception:
            log_event(event_name="scheduler.alert.unsent", severity="WARNING")


def _dispatch_now(now: datetime | None = None) -> datetime:
    if now is None:
        return utc_now()
    if now.tzinfo is None:
        raise ValueError("scheduled task timestamps must be timezone-aware")
    return now.astimezone(UTC)


def _next_scan_at(now: datetime) -> datetime:
    return now.replace(second=0, microsecond=0) + timedelta(minutes=1)


def _retry_dispatch_on_next_scan(*, run_id: int, now: datetime) -> None:
    with Session(engine) as session:
        run = session.exec(
            select(SchedulerRun).where(SchedulerRun.id == run_id).with_for_update()
        ).first()
        if run is None or run.status is not SchedulerRunStatus.QUEUED:
            return
        run.next_dispatch_at = _next_scan_at(now)
        session.add(run)
        session.commit()


def dispatch_queued_runs(
    *, run_ids: list[int] | None = None, now: datetime | None = None
) -> None:
    current = _dispatch_now(now)
    if run_ids is not None and not run_ids:
        return
    with Session(engine) as session:
        query = (
            select(SchedulerRun)
            .where(
                SchedulerRun.status == SchedulerRunStatus.QUEUED,
                col(SchedulerRun.next_dispatch_at).is_not(None),
                col(SchedulerRun.next_dispatch_at) <= current,
            )
            .order_by(col(SchedulerRun.created_at), col(SchedulerRun.id))
            .limit(DISPATCH_BATCH_SIZE)
            .with_for_update(skip_locked=True)
        )
        if run_ids is not None:
            query = query.where(col(SchedulerRun.id).in_(run_ids))
        runs = list(session.exec(query).all())
        dispatch_ids: list[int] = []
        for run in runs:
            if run.id is None:
                raise RuntimeError("scheduled task run must be persisted")
            run.next_dispatch_at = current + LEASE_DURATION
            session.add(run)
            dispatch_ids.append(run.id)
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
                create_run(
                    session=session,
                    job=job,
                    trigger=SchedulerRunTrigger.SCHEDULED,
                    planned_at=planned_at,
                    requested_by=None,
                    now=now,
                )
            except ValueError:
                create_run(
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
                create_run(
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
    dispatch_queued_runs(now=now)
    for job_id, kind, category, summary, planned_at in alerts:
        _send_alert(
            job_id=job_id,
            kind=kind,
            category=category,
            summary=summary,
            planned_at=planned_at,
        )


def execute_run(run_id: int) -> None:
    if not isinstance(run_id, int):
        raise ValueError("scheduler run id must be an integer")
    with Session(engine) as session:
        run = session.exec(
            select(SchedulerRun).where(SchedulerRun.id == run_id).with_for_update()
        ).first()
        if run is None or run.status is SchedulerRunStatus.CANCELLED:
            return
        now = utc_now()
        if run.status is SchedulerRunStatus.RUNNING and (
            run.lease_expires_at is None or run.lease_expires_at > now
        ):
            return
        if run.status not in {SchedulerRunStatus.QUEUED, SchedulerRunStatus.RUNNING}:
            return
        run.status = SchedulerRunStatus.RUNNING
        run.started_at = now
        run.lease_expires_at = now + LEASE_DURATION
        run.next_dispatch_at = None
        run.attempt_count += 1
        session.add(run)
        session.commit()
        session.refresh(run)
        class_path = run.class_path
        config_snapshot = run.config
        trigger = run.trigger
        planned_at = run.planned_at
        job_id = run.job_id
    status: SchedulerRunStatus
    category: str | None
    summary: str | None
    try:
        task_class = resolve_task_class(class_path)
        config = task_class.config_model.model_validate(config_snapshot)
        task = task_class()
    except ValidationError, ValueError:
        status, category, summary = (
            SchedulerRunStatus.FAILED,
            "CONFIGURATION_INVALID",
            "Scheduled task configuration is invalid",
        )
    else:
        try:
            task.run(
                context=ScheduledTaskContext(
                    run_id=run_id,
                    trigger=trigger,
                    planned_at=planned_at,
                    started_at=now,
                ),
                config=config,
            )
            status, category, summary = SchedulerRunStatus.SUCCEEDED, None, None
        except ScheduledTaskSkipped as skipped:
            status, category, summary = (
                SchedulerRunStatus.SKIPPED,
                skipped.category,
                skipped.summary,
            )
        except Exception:
            status, category, summary = (
                SchedulerRunStatus.FAILED,
                "EXECUTION_FAILED",
                "Scheduled task execution failed",
            )
    with Session(engine) as session:
        run = session.get(SchedulerRun, run_id)
        if run is None:
            return
        run.status = status
        run.error_category = category
        run.error_summary = summary
        run.finished_at = utc_now()
        run.lease_expires_at = None
        run.next_dispatch_at = None
        session.add(run)
        job = session.get(SchedulerJob, job_id)
        if job is not None and status is SchedulerRunStatus.SUCCEEDED:
            job.run_failure_alerted_at = None
            job.overlap_alerted_at = None
            session.add(job)
        session.commit()
    if status is SchedulerRunStatus.FAILED:
        _send_alert(
            job_id=job_id,
            kind="CONFIGURATION" if category == "CONFIGURATION_INVALID" else "FAILURE",
            category=category or "EXECUTION_FAILED",
            summary=summary or "Scheduled task execution failed",
            planned_at=planned_at,
        )


def cleanup_scheduled_runs() -> None:
    from app.modules.scheduler.service import cleanup_runs

    with Session(engine) as session:
        cleanup_runs(session=session)
        session.commit()


celery_app.task(name="scheduler.scan_due_jobs", ignore_result=True)(scan_due_jobs)
celery_app.task(name="scheduler.execute_run", ignore_result=True)(execute_run)
celery_app.task(name="scheduler.cleanup_runs", ignore_result=True)(
    cleanup_scheduled_runs
)
