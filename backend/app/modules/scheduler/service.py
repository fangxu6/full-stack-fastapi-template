import importlib
import re
import uuid
from datetime import UTC, datetime, timedelta
from typing import cast

from pydantic import ValidationError
from sqlalchemy import func
from sqlmodel import Session, col, select

from app.core.exceptions import AppError, ConflictError
from app.models.base import get_datetime_utc
from app.models.scheduler import (
    SchedulerJob,
    SchedulerRun,
    SchedulerRunStatus,
    SchedulerRunTrigger,
)
from app.modules.scheduler import run_lifecycle, scheduler_alerts
from app.modules.scheduler.contracts import ScheduledTask, ScheduledTaskConfig
from app.modules.scheduler.cron import matches_cron, next_run_at
from app.modules.scheduler.run_lifecycle import (
    SchedulerJobNotFoundError,
)
from app.schemas.scheduler import SchedulerJobCreate, SchedulerJobUpdate

CLASS_PATH = re.compile(
    r"^app\.modules\.[a-z][a-z0-9_]*\.scheduled_tasks\.[A-Z][A-Za-z0-9_]*$"
)
CAMEL_CASE_BOUNDARY = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")
NON_ALPHANUMERIC = re.compile(r"[^a-z0-9]+")
SENSITIVE_KEY_NAMES = frozenset(
    {
        "password",
        "token",
        "secret",
        "credential",
        "authorization",
        "api_key",
        "access_key",
        "private_key",
        "dsn",
        "connection_string",
    }
)
SENSITIVE_KEY_SEGMENTS = frozenset(
    {"password", "token", "secret", "credential", "authorization", "dsn"}
)
SENSITIVE_KEY_COMPOUNDS = frozenset(
    {"api_key", "access_key", "private_key", "connection_string"}
)
LEASE_DURATION: timedelta = run_lifecycle.LEASE_DURATION
CRON_PREVIEW_COUNT = 5
BACKFILL_MAX_AGE = timedelta(days=365)
INVENTORY_BOOTSTRAP_JOBS = (
    (
        "inventory.daily_report.create",
        "Inventory daily report creation",
        "app.modules.inventory.scheduled_tasks.InventoryDailyReportCreateTask",
        "0 8 * * *",
    ),
    (
        "inventory.daily_report.retry",
        "Inventory daily report delivery retry",
        "app.modules.inventory.scheduled_tasks.InventoryDailyReportRetryTask",
        "*/15 * * * *",
    ),
    (
        "inventory.document_correction.apply",
        "Inventory document correction application",
        "app.modules.inventory.scheduled_tasks.InventoryCorrectionApplyTask",
        "* * * * *",
    ),
)


class SchedulerValidationError(AppError):
    status_code = 422
    detail = "Scheduled task definition is invalid"


def utc_now(value: datetime | None = None) -> datetime:
    current = value or get_datetime_utc()
    if current.tzinfo is None:
        raise ValueError("scheduled task timestamps must be timezone-aware")
    return current.astimezone(UTC)


def preview_cron(
    *, cron_expression: str, now: datetime | None = None
) -> tuple[datetime, list[datetime]]:
    base_at = utc_now(now)
    cursor = base_at
    next_run_ats: list[datetime] = []
    try:
        for _ in range(CRON_PREVIEW_COUNT):
            cursor = next_run_at(cron_expression, after=cursor)
            next_run_ats.append(cursor)
    except ValueError as error:
        raise SchedulerValidationError(str(error)) from error
    return base_at, next_run_ats


def _normalized_key(key: str) -> str:
    return NON_ALPHANUMERIC.sub(
        "_", CAMEL_CASE_BOUNDARY.sub("_", key).casefold()
    ).strip("_")


def _is_credential_key(key: str) -> bool:
    normalized = _normalized_key(key)
    if normalized in SENSITIVE_KEY_NAMES:
        return True
    if any(compound in normalized for compound in SENSITIVE_KEY_COMPOUNDS):
        return True
    return bool(set(normalized.split("_")) & SENSITIVE_KEY_SEGMENTS)


def _validate_no_credentials(value: object) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if not isinstance(key, str) or _is_credential_key(key):
                raise ValueError(
                    "scheduled task configuration cannot contain credentials"
                )
            _validate_no_credentials(child)
    elif isinstance(value, list):
        for child in value:
            _validate_no_credentials(child)


def _schema_declares_credentials(schema: object) -> bool:
    if isinstance(schema, dict):
        if schema.get("format") == "password":
            return True
        return any(_schema_declares_credentials(child) for child in schema.values())
    if isinstance(schema, list):
        return any(_schema_declares_credentials(child) for child in schema)
    return False


def resolve_task_class(class_path: str) -> type[ScheduledTask]:
    if not CLASS_PATH.fullmatch(class_path):
        raise ValueError("scheduled task class path is not allowed")
    module_name, class_name = class_path.rsplit(".", 1)
    try:
        target = getattr(importlib.import_module(module_name), class_name, None)
    except ImportError as error:
        raise ValueError("scheduled task class cannot be imported") from error
    if (
        not isinstance(target, type)
        or not issubclass(target, ScheduledTask)
        or target is ScheduledTask
    ):
        raise ValueError("scheduled task class must inherit ScheduledTask")
    config_model = getattr(target, "config_model", None)
    if not isinstance(config_model, type) or not issubclass(
        config_model, ScheduledTaskConfig
    ):
        raise ValueError("scheduled task class must declare ScheduledTaskConfig")
    if _schema_declares_credentials(config_model.model_json_schema()):
        raise ValueError("scheduled task configuration cannot declare credentials")
    return target


def task_capabilities(*, class_path: str) -> tuple[bool, bool]:
    try:
        task_class = resolve_task_class(class_path)
    except ValueError as error:
        raise SchedulerValidationError(str(error)) from error
    return task_class.allow_run_now, task_class.allow_backfill


def validate_definition(
    *, class_path: str, cron_expression: str, config: dict[str, object]
) -> dict[str, object]:
    task_class = resolve_task_class(class_path)
    next_run_at(cron_expression, after=get_datetime_utc())
    _validate_no_credentials(config)
    try:
        snapshot = task_class.config_model.model_validate(config).model_dump(
            mode="json"
        )
    except ValidationError as error:
        raise ValueError("scheduled task configuration is invalid") from error
    _validate_no_credentials(snapshot)
    return cast(dict[str, object], snapshot)


def task_schema(class_path: str) -> dict[str, object]:
    try:
        return cast(
            dict[str, object],
            resolve_task_class(class_path).config_model.model_json_schema(),
        )
    except ValueError as error:
        raise SchedulerValidationError(str(error)) from error


def get_job(
    *, session: Session, job_id: int, include_deleted: bool = False
) -> SchedulerJob:
    job = session.get(SchedulerJob, job_id)
    if job is None or (job.deleted_at is not None and not include_deleted):
        raise SchedulerJobNotFoundError
    return job


def list_jobs(
    *, session: Session, skip: int, limit: int, include_deleted: bool
) -> tuple[list[SchedulerJob], int]:
    filters = [] if include_deleted else [col(SchedulerJob.deleted_at).is_(None)]
    count = session.exec(
        select(func.count()).select_from(SchedulerJob).where(*filters)
    ).one()
    jobs = list(
        session.exec(
            select(SchedulerJob)
            .where(*filters)
            .order_by(
                col(SchedulerJob.created_at).desc(),
                col(SchedulerJob.id).desc(),
            )
            .offset(skip)
            .limit(limit)
        ).all()
    )
    return jobs, int(count)


def create_job(
    *,
    session: Session,
    job_in: SchedulerJobCreate,
    now: datetime | None = None,
) -> SchedulerJob:
    current = utc_now(now)
    try:
        config = validate_definition(
            class_path=job_in.class_path,
            cron_expression=job_in.cron_expression,
            config=job_in.config,
        )
    except ValueError as error:
        raise SchedulerValidationError(str(error)) from error
    job = SchedulerJob(
        name=job_in.name.strip(),
        class_path=job_in.class_path,
        cron_expression=job_in.cron_expression,
        config=config,
        enabled=False,
        next_run_at=next_run_at(job_in.cron_expression, after=current),
    )
    session.add(job)
    session.flush()
    session.refresh(job)
    return job


def update_job(
    *,
    session: Session,
    job_id: int,
    job_in: SchedulerJobUpdate,
    now: datetime | None = None,
) -> SchedulerJob:
    job = get_job(session=session, job_id=job_id)
    values = job_in.model_dump(exclude_unset=True)
    if any(values.get(field) is None for field in values):
        raise SchedulerValidationError("scheduled task fields cannot be null")
    class_path = cast(str, values.get("class_path", job.class_path))
    cron_expression = cast(str, values.get("cron_expression", job.cron_expression))
    config = cast(dict[str, object], values.get("config", job.config))
    try:
        job.config = validate_definition(
            class_path=class_path, cron_expression=cron_expression, config=config
        )
    except ValueError as error:
        raise SchedulerValidationError(str(error)) from error
    job.class_path = class_path
    job.cron_expression = cron_expression
    if "name" in values:
        job.name = cast(str, values["name"]).strip()
    current = utc_now(now)
    job.next_run_at = next_run_at(cron_expression, after=current)
    if job.id is None:
        raise RuntimeError("scheduled task must be persisted")
    scheduler_alerts.clear_configuration_alert(session=session, job_id=job.id)
    session.add(job)
    session.flush()
    session.refresh(job)
    return job


def _active_run(*, session: Session, job_id: int) -> SchedulerRun | None:
    return run_lifecycle.active_run(session=session, job_id=job_id)


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
    return run_lifecycle.create_run(
        session=session,
        job=job,
        trigger=trigger,
        planned_at=planned_at,
        requested_by=requested_by,
        status=status,
        error_category=error_category,
        error_summary=error_summary,
        require_no_active=require_no_active,
        now=now,
    )


def run_now(
    *, session: Session, actor_id: uuid.UUID, job_id: int, now: datetime | None = None
) -> SchedulerRun:
    current = utc_now(now)
    job = get_job(session=session, job_id=job_id)
    can_run_now, _ = task_capabilities(class_path=job.class_path)
    if not can_run_now:
        raise SchedulerValidationError(
            "scheduled task does not support immediate execution"
        )
    return create_run(
        session=session,
        job=job,
        trigger=SchedulerRunTrigger.MANUAL_NOW,
        planned_at=current,
        requested_by=actor_id,
        now=current,
    )


def backfill(
    *,
    session: Session,
    actor_id: uuid.UUID,
    job_id: int,
    planned_at: datetime,
    now: datetime | None = None,
) -> SchedulerRun:
    current = utc_now(now)
    if (
        planned_at.tzinfo is None
        or planned_at >= current
        or current - planned_at > BACKFILL_MAX_AGE
    ):
        raise SchedulerValidationError(
            "backfill time must be within the previous 365 days"
        )
    job = get_job(session=session, job_id=job_id)
    try:
        cron_matches = matches_cron(job.cron_expression, at=planned_at)
    except ValueError as error:
        raise SchedulerValidationError(
            "scheduled task cron expression is invalid"
        ) from error
    if not cron_matches:
        raise SchedulerValidationError(
            "backfill time must match the task cron expression"
        )
    _, can_backfill = task_capabilities(class_path=job.class_path)
    if not can_backfill:
        raise SchedulerValidationError("scheduled task does not support backfill")
    return create_run(
        session=session,
        job=job,
        trigger=SchedulerRunTrigger.MANUAL_BACKFILL,
        planned_at=planned_at,
        requested_by=actor_id,
        now=current,
    )


def set_enabled(
    *,
    session: Session,
    job_id: int,
    enabled: bool,
    now: datetime | None = None,
) -> SchedulerJob:
    job = get_job(session=session, job_id=job_id)
    current = utc_now(now)
    job.enabled = enabled
    job.next_run_at = next_run_at(job.cron_expression, after=current)
    if not enabled:
        run_lifecycle.cancel_queued_runs(session=session, job_id=job_id, now=current)
    session.add(job)
    session.flush()
    session.refresh(job)
    return job


def delete_job(*, session: Session, job_id: int, now: datetime | None = None) -> None:
    if run_lifecycle.active_run(session=session, job_id=job_id) is not None:
        raise ConflictError(
            "Disable the scheduled task and wait for active runs before deletion"
        )
    job = get_job(session=session, job_id=job_id)
    current = utc_now(now)
    job.enabled = False
    job.deleted_at = current
    session.add(job)
    session.flush()


def restore_job(
    *, session: Session, job_id: int, now: datetime | None = None
) -> SchedulerJob:
    job = get_job(session=session, job_id=job_id, include_deleted=True)
    current = utc_now(now)
    job.deleted_at = None
    job.enabled = False
    job.next_run_at = next_run_at(job.cron_expression, after=current)
    session.add(job)
    session.flush()
    session.refresh(job)
    return job


def list_runs(
    *, session: Session, job_id: int, skip: int, limit: int
) -> tuple[list[SchedulerRun], int]:
    get_job(session=session, job_id=job_id)
    predicate = SchedulerRun.job_id == job_id
    count = session.exec(
        select(func.count()).select_from(SchedulerRun).where(predicate)
    ).one()
    runs = list(
        session.exec(
            select(SchedulerRun)
            .where(predicate)
            .order_by(
                col(SchedulerRun.created_at).desc(),
                col(SchedulerRun.id).desc(),
            )
            .offset(skip)
            .limit(limit)
        ).all()
    )
    return runs, int(count)


def cleanup_runs(*, session: Session, now: datetime | None = None) -> int:
    return run_lifecycle.cleanup_runs(session=session, now=now)


def bootstrap_inventory_jobs(*, session: Session) -> None:
    current = utc_now()
    added = False
    for bootstrap_key, name, class_path, cron_expression in INVENTORY_BOOTSTRAP_JOBS:
        existing = session.exec(
            select(SchedulerJob).where(SchedulerJob.bootstrap_key == bootstrap_key)
        ).first()
        if existing is not None:
            continue
        session.add(
            SchedulerJob(
                name=name,
                class_path=class_path,
                cron_expression=cron_expression,
                config={},
                enabled=True,
                next_run_at=next_run_at(cron_expression, after=current),
                bootstrap_key=bootstrap_key,
            )
        )
        added = True
    if added:
        session.flush()
