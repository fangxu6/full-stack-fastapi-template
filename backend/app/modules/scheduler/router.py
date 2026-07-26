from fastapi import APIRouter, Depends, Query

from app.api.deps import CurrentUser, SessionDep
from app.core.observability import log_event
from app.modules.iam.dependencies import permission_required
from app.modules.scheduler import service
from app.schemas.scheduler import (
    SchedulerJobCreate,
    SchedulerJobPublic,
    SchedulerJobsPublic,
    SchedulerJobUpdate,
    SchedulerRunBackfill,
    SchedulerRunPublic,
    SchedulerRunsPublic,
    SchedulerTaskSchemaPublic,
)

router = APIRouter(prefix="/scheduler", tags=["scheduler"])


def _job(job: object) -> SchedulerJobPublic:
    return SchedulerJobPublic.model_validate(job, from_attributes=True)


def _run(run: object) -> SchedulerRunPublic:
    return SchedulerRunPublic.model_validate(run, from_attributes=True)


def _enqueue_run(run: SchedulerRunPublic) -> None:
    try:
        from app.core.celery import celery_app

        celery_app.send_task("scheduler.execute_run", args=[run.id])
    except Exception:
        log_event(event_name="scheduler.enqueue.failed", severity="ERROR")


@router.get(
    "/jobs",
    dependencies=[Depends(permission_required("scheduler.jobs.read"))],
    response_model=SchedulerJobsPublic,
)
def read_jobs(
    session: SessionDep,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    include_deleted: bool = False,
) -> SchedulerJobsPublic:
    jobs, count = service.list_jobs(
        session=session, skip=skip, limit=limit, include_deleted=include_deleted
    )
    return SchedulerJobsPublic(data=[_job(job) for job in jobs], count=count)


@router.post(
    "/jobs",
    dependencies=[Depends(permission_required("scheduler.jobs.manage"))],
    response_model=SchedulerJobPublic,
)
def create_job(
    session: SessionDep, current_user: CurrentUser, body: SchedulerJobCreate
) -> SchedulerJobPublic:
    return _job(service.create_job(session=session, actor=current_user, job_in=body))


@router.get(
    "/jobs/{job_id}",
    dependencies=[Depends(permission_required("scheduler.jobs.read"))],
    response_model=SchedulerJobPublic,
)
def read_job(job_id: int, session: SessionDep) -> SchedulerJobPublic:
    return _job(service.get_job(session=session, job_id=job_id))


@router.put(
    "/jobs/{job_id}",
    dependencies=[Depends(permission_required("scheduler.jobs.manage"))],
    response_model=SchedulerJobPublic,
)
def update_job(
    job_id: int,
    session: SessionDep,
    current_user: CurrentUser,
    body: SchedulerJobUpdate,
) -> SchedulerJobPublic:
    return _job(
        service.update_job(
            session=session, actor=current_user, job_id=job_id, job_in=body
        )
    )


@router.post(
    "/jobs/{job_id}/enable",
    dependencies=[Depends(permission_required("scheduler.jobs.manage"))],
    response_model=SchedulerJobPublic,
)
def enable_job(
    job_id: int, session: SessionDep, current_user: CurrentUser
) -> SchedulerJobPublic:
    return _job(
        service.set_enabled(
            session=session, actor=current_user, job_id=job_id, enabled=True
        )
    )


@router.post(
    "/jobs/{job_id}/disable",
    dependencies=[Depends(permission_required("scheduler.jobs.manage"))],
    response_model=SchedulerJobPublic,
)
def disable_job(
    job_id: int, session: SessionDep, current_user: CurrentUser
) -> SchedulerJobPublic:
    return _job(
        service.set_enabled(
            session=session, actor=current_user, job_id=job_id, enabled=False
        )
    )


@router.delete(
    "/jobs/{job_id}",
    dependencies=[Depends(permission_required("scheduler.jobs.manage"))],
)
def delete_job(
    job_id: int, session: SessionDep, current_user: CurrentUser
) -> dict[str, str]:
    service.delete_job(session=session, actor=current_user, job_id=job_id)
    return {"message": "Scheduled task deleted"}


@router.post(
    "/jobs/{job_id}/restore",
    dependencies=[Depends(permission_required("scheduler.jobs.manage"))],
    response_model=SchedulerJobPublic,
)
def restore_job(
    job_id: int, session: SessionDep, current_user: CurrentUser
) -> SchedulerJobPublic:
    return _job(service.restore_job(session=session, actor=current_user, job_id=job_id))


@router.post(
    "/jobs/{job_id}/run-now",
    dependencies=[Depends(permission_required("scheduler.jobs.manage"))],
    response_model=SchedulerRunPublic,
)
def run_now(
    job_id: int, session: SessionDep, current_user: CurrentUser
) -> SchedulerRunPublic:
    run = _run(service.run_now(session=session, actor=current_user, job_id=job_id))
    _enqueue_run(run)
    return run


@router.post(
    "/jobs/{job_id}/backfill",
    dependencies=[Depends(permission_required("scheduler.jobs.manage"))],
    response_model=SchedulerRunPublic,
)
def backfill(
    job_id: int,
    session: SessionDep,
    current_user: CurrentUser,
    body: SchedulerRunBackfill,
) -> SchedulerRunPublic:
    run = _run(
        service.backfill(
            session=session,
            actor=current_user,
            job_id=job_id,
            planned_at=body.planned_at,
        )
    )
    _enqueue_run(run)
    return run


@router.get(
    "/jobs/{job_id}/runs",
    dependencies=[Depends(permission_required("scheduler.jobs.read"))],
    response_model=SchedulerRunsPublic,
)
def read_runs(
    job_id: int,
    session: SessionDep,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
) -> SchedulerRunsPublic:
    runs, count = service.list_runs(
        session=session, job_id=job_id, skip=skip, limit=limit
    )
    return SchedulerRunsPublic(data=[_run(run) for run in runs], count=count)


@router.get(
    "/task-schema",
    dependencies=[Depends(permission_required("scheduler.jobs.read"))],
    response_model=SchedulerTaskSchemaPublic,
)
def read_task_schema(class_path: str) -> SchedulerTaskSchemaPublic:
    return SchedulerTaskSchemaPublic(
        class_path=class_path,
        json_schema=service.task_schema(class_path),
    )
