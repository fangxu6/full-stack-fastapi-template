"""Scheduler service tests."""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from pydantic import BaseModel, SecretStr
from sqlmodel import Session, select

from app.core.audit import bind_audit_actor
from app.models.scheduler import SchedulerJob, SchedulerRun
from app.modules.scheduler import service
from app.modules.scheduler.contracts import ScheduledTask, ScheduledTaskConfig
from app.modules.scheduler.cron import matches_cron
from app.schemas.scheduler import SchedulerJobCreate
from tests.utils.user import create_random_user

INVENTORY_CREATE_CLASS = (
    "app.modules.inventory.scheduled_tasks.InventoryDailyReportCreateTask"
)
INVENTORY_RETRY_CLASS = (
    "app.modules.inventory.scheduled_tasks.InventoryDailyReportRetryTask"
)


def test_definition_rejects_untrusted_path_and_credentials() -> None:
    with pytest.raises(ValueError, match="not allowed"):
        service.validate_definition(
            class_path="os.system",
            cron_expression="0 8 * * *",
            config={},
        )
    with pytest.raises(ValueError, match="cannot contain credentials"):
        service.validate_definition(
            class_path=INVENTORY_RETRY_CLASS,
            cron_expression="0 8 * * *",
            config={"api_token": "secret"},
        )


@pytest.mark.parametrize(
    "key",
    [
        "credential",
        "authorization",
        "access_key",
        "accessKey",
        "connection-string",
    ],
)
def test_definition_rejects_credential_key_variants(key: str) -> None:
    with pytest.raises(ValueError, match="cannot contain credentials"):
        service.validate_definition(
            class_path=INVENTORY_RETRY_CLASS,
            cron_expression="0 8 * * *",
            config={key: "value"},
        )


class NestedSecretConfig(BaseModel):
    password: SecretStr


class SecretSchemaConfig(ScheduledTaskConfig):
    nested: NestedSecretConfig | None = None
    choices: list[SecretStr] = []
    union_value: SecretStr | str | None = None


class SecretSchemaTask(ScheduledTask):
    config_model = SecretSchemaConfig

    def run(self, *, context: object, config: SecretSchemaConfig) -> None:
        del context, config


class DefaultManualOperationsTask(ScheduledTask):
    config_model = ScheduledTaskConfig

    def run(self, *, context: object, config: ScheduledTaskConfig) -> None:
        del context, config


class ReplaySafeBackfillTask(ScheduledTask):
    config_model = ScheduledTaskConfig
    allow_backfill = True

    def run(self, *, context: object, config: ScheduledTaskConfig) -> None:
        del context, config


class ManualOperationsDisabledTask(ScheduledTask):
    config_model = ScheduledTaskConfig
    allow_run_now = False
    allow_backfill = False

    def run(self, *, context: object, config: ScheduledTaskConfig) -> None:
        del context, config


def test_task_capabilities_require_explicit_backfill_opt_in(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        service, "resolve_task_class", lambda _: DefaultManualOperationsTask
    )

    assert service.task_capabilities(class_path=INVENTORY_RETRY_CLASS) == (True, False)


@pytest.mark.parametrize("class_path", (INVENTORY_CREATE_CLASS, INVENTORY_RETRY_CLASS))
def test_inventory_tasks_remain_ineligible_for_backfill(class_path: str) -> None:
    assert service.task_capabilities(class_path=class_path) == (True, False)


def test_preview_cron_returns_five_future_shanghai_schedule_times() -> None:
    now = datetime(2026, 7, 26, 0, 0, tzinfo=UTC)

    base_at, next_run_ats = service.preview_cron(cron_expression="0 8 * * *", now=now)

    assert base_at == now
    assert next_run_ats == [
        datetime(2026, 7, 27, 0, 0, tzinfo=UTC),
        datetime(2026, 7, 28, 0, 0, tzinfo=UTC),
        datetime(2026, 7, 29, 0, 0, tzinfo=UTC),
        datetime(2026, 7, 30, 0, 0, tzinfo=UTC),
        datetime(2026, 7, 31, 0, 0, tzinfo=UTC),
    ]


def test_preview_cron_iterates_across_month_boundaries() -> None:
    _, next_run_ats = service.preview_cron(
        cron_expression="0 8 1 * *",
        now=datetime(2026, 1, 31, 0, 0, tzinfo=UTC),
    )

    assert next_run_ats == [
        datetime(2026, 2, 1, 0, 0, tzinfo=UTC),
        datetime(2026, 3, 1, 0, 0, tzinfo=UTC),
        datetime(2026, 4, 1, 0, 0, tzinfo=UTC),
        datetime(2026, 5, 1, 0, 0, tzinfo=UTC),
        datetime(2026, 6, 1, 0, 0, tzinfo=UTC),
    ]


def test_preview_cron_preserves_day_and_weekday_and_semantics() -> None:
    base_at, next_run_ats = service.preview_cron(
        cron_expression="0 8 1 * 1",
        now=datetime(2026, 5, 31, 0, 0, tzinfo=UTC),
    )

    assert next_run_ats[0] == datetime(2026, 6, 1, 0, 0, tzinfo=UTC)
    assert len(next_run_ats) == service.CRON_PREVIEW_COUNT
    assert next_run_ats == sorted(next_run_ats)
    assert all(planned_at > base_at for planned_at in next_run_ats)
    assert all(matches_cron("0 8 1 * 1", at=planned_at) for planned_at in next_run_ats)


def test_preview_cron_rejects_invalid_expression() -> None:
    with pytest.raises(service.SchedulerValidationError, match="exactly five"):
        service.preview_cron(
            cron_expression="0 8 * *", now=datetime(2026, 7, 26, tzinfo=UTC)
        )


def test_definition_rejects_nested_container_and_union_secret_schema(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class_path = "app.modules.inventory.scheduled_tasks.SecretSchemaTask"
    monkeypatch.setattr(
        service.importlib,
        "import_module",
        lambda _: SimpleNamespace(SecretSchemaTask=SecretSchemaTask),
    )

    with pytest.raises(ValueError, match="cannot declare credentials"):
        service.validate_definition(
            class_path=class_path,
            cron_expression="0 8 * * *",
            config={},
        )

    with pytest.raises(service.SchedulerValidationError, match="cannot declare"):
        service.task_schema(class_path)


def test_create_job_defaults_disabled_and_freezes_config(db: Session) -> None:
    actor = create_random_user(db)
    bind_audit_actor(session=db, actor_id=actor.id)

    job = service.create_job(
        session=db,
        job_in=SchedulerJobCreate(
            name="Retry report delivery",
            class_path=INVENTORY_RETRY_CLASS,
            cron_expression="*/15 * * * *",
            config={},
        ),
    )

    assert job.id is not None
    assert not job.enabled
    assert job.created_by == actor.id
    run = service.run_now(session=db, actor_id=actor.id, job_id=job.id)
    assert run.config == {}
    assert run.class_path == INVENTORY_RETRY_CLASS


def test_manual_operations_are_rejected_before_creating_a_run(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    now = datetime(2026, 7, 31, 0, 0, tzinfo=UTC)
    actor = create_random_user(db)
    bind_audit_actor(session=db, actor_id=actor.id)
    job = service.create_job(
        session=db,
        job_in=SchedulerJobCreate(
            name="Disabled manual operations",
            class_path=INVENTORY_RETRY_CLASS,
            cron_expression="* * * * *",
            config={},
        ),
        now=now,
    )
    assert job.id is not None
    monkeypatch.setattr(
        service, "resolve_task_class", lambda _: ManualOperationsDisabledTask
    )

    with pytest.raises(service.SchedulerValidationError, match="immediate"):
        service.run_now(session=db, actor_id=actor.id, job_id=job.id)

    with pytest.raises(service.SchedulerValidationError, match="backfill"):
        service.backfill(
            session=db,
            actor_id=actor.id,
            job_id=job.id,
            planned_at=now - timedelta(minutes=1),
            now=now,
        )

    assert (
        db.exec(select(SchedulerRun).where(SchedulerRun.job_id == job.id)).all() == []
    )


def test_backfill_accepts_exactly_365_days_for_a_replay_safe_task(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    now = datetime(2026, 7, 31, 0, 0, tzinfo=UTC)
    planned_at = now - service.BACKFILL_MAX_AGE
    actor = create_random_user(db)
    bind_audit_actor(session=db, actor_id=actor.id)
    job = service.create_job(
        session=db,
        job_in=SchedulerJobCreate(
            name="Replay-safe backfill",
            class_path=INVENTORY_RETRY_CLASS,
            cron_expression="0 8 * * *",
            config={},
        ),
        now=now,
    )
    assert job.id is not None
    monkeypatch.setattr(service, "resolve_task_class", lambda _: ReplaySafeBackfillTask)

    run = service.backfill(
        session=db,
        actor_id=actor.id,
        job_id=job.id,
        planned_at=planned_at,
        now=now,
    )

    assert run.trigger is service.SchedulerRunTrigger.MANUAL_BACKFILL
    assert run.planned_at == planned_at
    assert run.requested_by == actor.id
    assert run.next_dispatch_at == now


def test_backfill_rejects_time_older_than_365_days_before_creating_a_run(
    db: Session,
) -> None:
    now = datetime(2026, 7, 31, 0, 0, tzinfo=UTC)
    actor = create_random_user(db)
    bind_audit_actor(session=db, actor_id=actor.id)
    job = service.create_job(
        session=db,
        job_in=SchedulerJobCreate(
            name="Too-old backfill",
            class_path=INVENTORY_RETRY_CLASS,
            cron_expression="0 8 * * *",
            config={},
        ),
        now=now,
    )
    assert job.id is not None

    with pytest.raises(service.SchedulerValidationError, match="previous 365 days"):
        service.backfill(
            session=db,
            actor_id=actor.id,
            job_id=job.id,
            planned_at=now - service.BACKFILL_MAX_AGE - timedelta(microseconds=1),
            now=now,
        )

    assert (
        db.exec(select(SchedulerRun).where(SchedulerRun.job_id == job.id)).all() == []
    )


def test_backfill_rejects_invalid_timestamps_before_creating_a_run(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    now = datetime(2026, 7, 31, 0, 0, tzinfo=UTC)
    actor = create_random_user(db)
    bind_audit_actor(session=db, actor_id=actor.id)
    job = service.create_job(
        session=db,
        job_in=SchedulerJobCreate(
            name="Invalid backfill timestamp",
            class_path=INVENTORY_RETRY_CLASS,
            cron_expression="0 8 * * *",
            config={},
        ),
        now=now,
    )
    assert job.id is not None
    monkeypatch.setattr(service, "resolve_task_class", lambda _: ReplaySafeBackfillTask)

    invalid_times = (
        (now, "previous 365 days"),
        (now + timedelta(minutes=1), "previous 365 days"),
        (datetime(2025, 7, 31, 0, 0), "previous 365 days"),
        (now - timedelta(days=1) + timedelta(minutes=1), "must match"),
    )
    for planned_at, message in invalid_times:
        with pytest.raises(service.SchedulerValidationError, match=message):
            service.backfill(
                session=db,
                actor_id=actor.id,
                job_id=job.id,
                planned_at=planned_at,
                now=now,
            )

    assert (
        db.exec(select(SchedulerRun).where(SchedulerRun.job_id == job.id)).all() == []
    )


def test_conflicting_run_creation_does_not_rollback_prior_batch_run(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    actor = create_random_user(db)
    bind_audit_actor(session=db, actor_id=actor.id)
    first_job = service.create_job(
        session=db,
        job_in=SchedulerJobCreate(
            name="First task",
            class_path=INVENTORY_RETRY_CLASS,
            cron_expression="* * * * *",
            config={},
        ),
    )
    second_job = service.create_job(
        session=db,
        job_in=SchedulerJobCreate(
            name="Second task",
            class_path=INVENTORY_RETRY_CLASS,
            cron_expression="* * * * *",
            config={},
        ),
    )
    service.create_run(
        session=db,
        job=first_job,
        trigger=service.SchedulerRunTrigger.MANUAL_NOW,
        planned_at=first_job.next_run_at,
        requested_by=actor.id,
    )
    pending = service.create_run(
        session=db,
        job=second_job,
        trigger=service.SchedulerRunTrigger.MANUAL_NOW,
        planned_at=second_job.next_run_at,
        requested_by=actor.id,
    )
    monkeypatch.setattr(service, "_active_run", lambda **_: None)

    with pytest.raises(service.ConflictError):
        service.create_run(
            session=db,
            job=first_job,
            trigger=service.SchedulerRunTrigger.MANUAL_NOW,
            planned_at=first_job.next_run_at,
            requested_by=actor.id,
        )

    db.commit()
    assert pending.id is not None
    assert db.get(service.SchedulerRun, pending.id) is not None


def test_inventory_bootstrap_is_idempotent_and_keeps_edits(db: Session) -> None:
    jobs = list(
        db.exec(
            select(SchedulerJob).where(SchedulerJob.bootstrap_key.is_not(None))
        ).all()
    )
    assert {job.bootstrap_key for job in jobs} == {
        "inventory.daily_report.create",
        "inventory.daily_report.retry",
    }
    retry_job = next(job for job in jobs if job.bootstrap_key.endswith("retry"))
    retry_job.cron_expression = "0 9 * * *"
    db.add(retry_job)
    db.commit()

    assert retry_job.created_by is not None
    bind_audit_actor(session=db, actor_id=retry_job.created_by)
    service.bootstrap_inventory_jobs(session=db)
    db.refresh(retry_job)
    assert retry_job.cron_expression == "0 9 * * *"
