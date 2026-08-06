import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, col, select

from app.core.config import settings
from app.core.exceptions import ConflictError, NotFoundError
from app.models.base import get_datetime_utc
from app.models.scheduler import (
    SchedulerJob,
    SchedulerRun,
    SchedulerRunStatus,
    SchedulerRunTrigger,
)

LEASE_DURATION = timedelta(seconds=settings.CELERY_VISIBILITY_TIMEOUT_SECONDS)
RUN_RETENTION = timedelta(days=90)


class SchedulerJobNotFoundError(NotFoundError):
    detail = "Scheduled task not found"


def utc_now(value: datetime | None = None) -> datetime:
    current = value or get_datetime_utc()
    if current.tzinfo is None:
        raise ValueError("scheduled task timestamps must be timezone-aware")
    return current.astimezone(UTC)


def _job_id(job: SchedulerJob) -> int:
    if job.id is None:
        raise RuntimeError("scheduled task must be persisted")
    return job.id


def active_run(*, session: Session, job_id: int) -> SchedulerRun | None:
    return session.exec(
        select(SchedulerRun).where(
            SchedulerRun.job_id == job_id,
            col(SchedulerRun.status).in_(
                (SchedulerRunStatus.QUEUED, SchedulerRunStatus.RUNNING)
            ),
        )
    ).first()


def create_run(
    *,
    session: Session,
    job: SchedulerJob,
    trigger: SchedulerRunTrigger,
    planned_at: datetime,
    requested_by: uuid.UUID | None,
    status: SchedulerRunStatus = SchedulerRunStatus.QUEUED,
    error_category: str | None = None,
    error_summary: str | None = None,
    require_no_active: bool = True,
    now: datetime | None = None,
) -> SchedulerRun:
    current = utc_now(now)
    job_id = _job_id(job)
    locked_job = session.exec(
        select(SchedulerJob).where(SchedulerJob.id == job_id).with_for_update()
    ).first()
    if locked_job is None:
        raise SchedulerJobNotFoundError()
    if require_no_active and active_run(session=session, job_id=job_id) is not None:
        raise ConflictError("Scheduled task already has an active run")
    run = SchedulerRun(
        job_id=job_id,
        status=status,
        trigger=trigger,
        planned_at=planned_at.astimezone(UTC),
        class_path=locked_job.class_path,
        config=locked_job.config,
        requested_by=requested_by,
        created_at=current,
        next_dispatch_at=current if status is SchedulerRunStatus.QUEUED else None,
        finished_at=current
        if status not in {SchedulerRunStatus.QUEUED, SchedulerRunStatus.RUNNING}
        else None,
        error_category=error_category,
        error_summary=error_summary,
    )
    try:
        with session.begin_nested():
            session.add(run)
            session.flush()
    except IntegrityError as error:
        raise ConflictError("Scheduled task already has an active run") from error
    return run


def claim_dispatchable_runs(
    *,
    session: Session,
    now: datetime,
    run_ids: list[int] | None = None,
    lease_duration: timedelta = LEASE_DURATION,
    limit: int = 100,
) -> list[int]:
    if run_ids is not None and not run_ids:
        return []
    current = utc_now(now)
    query = (
        select(SchedulerRun)
        .where(
            SchedulerRun.status == SchedulerRunStatus.QUEUED,
            col(SchedulerRun.next_dispatch_at).is_not(None),
            col(SchedulerRun.next_dispatch_at) <= current,
        )
        .order_by(col(SchedulerRun.created_at), col(SchedulerRun.id))
        .limit(limit)
        .with_for_update(skip_locked=True)
    )
    if run_ids is not None:
        query = query.where(col(SchedulerRun.id).in_(run_ids))
    runs = list(session.exec(query).all())
    dispatch_ids: list[int] = []
    for run in runs:
        if run.id is None:
            raise RuntimeError("scheduled task run must be persisted")
        run.next_dispatch_at = current + lease_duration
        session.add(run)
        dispatch_ids.append(run.id)
    session.flush()
    return dispatch_ids


def release_dispatch(*, session: Session, run_id: int, now: datetime) -> None:
    run = session.exec(
        select(SchedulerRun).where(SchedulerRun.id == run_id).with_for_update()
    ).first()
    if run is None or run.status is not SchedulerRunStatus.QUEUED:
        return
    current = utc_now(now)
    run.next_dispatch_at = current.replace(second=0, microsecond=0) + timedelta(
        minutes=1
    )
    session.add(run)
    session.flush()


def claim_execution(
    *,
    session: Session,
    run_id: int,
    now: datetime,
    lease_duration: timedelta = LEASE_DURATION,
) -> SchedulerRun | None:
    run = session.exec(
        select(SchedulerRun).where(SchedulerRun.id == run_id).with_for_update()
    ).first()
    if run is None or run.status is SchedulerRunStatus.CANCELLED:
        return None
    current = utc_now(now)
    if run.status is SchedulerRunStatus.RUNNING and (
        run.lease_expires_at is None or run.lease_expires_at > current
    ):
        return None
    if run.status not in {SchedulerRunStatus.QUEUED, SchedulerRunStatus.RUNNING}:
        return None
    run.status = SchedulerRunStatus.RUNNING
    run.started_at = current
    run.lease_expires_at = current + lease_duration
    run.next_dispatch_at = None
    run.attempt_count += 1
    session.add(run)
    session.flush()
    return run


def finish_run(
    *,
    session: Session,
    run_id: int,
    status: SchedulerRunStatus,
    error_category: str | None = None,
    error_summary: str | None = None,
    finished_at: datetime | None = None,
) -> SchedulerRun | None:
    run = session.get(SchedulerRun, run_id)
    if run is None:
        return None
    run.status = status
    run.error_category = error_category
    run.error_summary = error_summary
    run.finished_at = utc_now(finished_at)
    run.lease_expires_at = None
    run.next_dispatch_at = None
    session.add(run)
    session.flush()
    return run


def cancel_queued_runs(
    *, session: Session, job_id: int, now: datetime | None = None
) -> int:
    current = utc_now(now)
    queued = session.exec(
        select(SchedulerRun).where(
            SchedulerRun.job_id == job_id,
            SchedulerRun.status == SchedulerRunStatus.QUEUED,
        )
    ).all()
    for run in queued:
        run.status = SchedulerRunStatus.CANCELLED
        run.finished_at = current
        run.lease_expires_at = None
        run.next_dispatch_at = None
        session.add(run)
    session.flush()
    return len(queued)


def cleanup_runs(*, session: Session, now: datetime | None = None) -> int:
    cutoff = utc_now(now) - RUN_RETENTION
    runs = session.exec(
        select(SchedulerRun).where(
            col(SchedulerRun.finished_at).is_not(None),
            col(SchedulerRun.finished_at) < cutoff,
        )
    ).all()
    for run in runs:
        session.delete(run)
    session.flush()
    return len(runs)
