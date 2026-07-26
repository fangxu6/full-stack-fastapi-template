"""Scheduler service tests."""

import pytest
from sqlmodel import Session, select

from app.core.config import settings
from app.models.scheduler import SchedulerJob
from app.modules.scheduler import service
from app.schemas.scheduler import SchedulerJobCreate
from tests.utils.user import create_random_user

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


def test_create_job_defaults_disabled_and_freezes_config(db: Session) -> None:
    actor = create_random_user(db)

    job = service.create_job(
        session=db,
        actor=actor,
        job_in=SchedulerJobCreate(
            name="Retry report delivery",
            class_path=INVENTORY_RETRY_CLASS,
            cron_expression="*/15 * * * *",
            config={},
        ),
    )

    assert job.id is not None
    assert not job.enabled
    run = service.run_now(session=db, actor=actor, job_id=job.id)
    assert run.config == {}
    assert run.class_path == INVENTORY_RETRY_CLASS


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

    from app import crud

    user = crud.get_user_by_email(session=db, email=settings.FIRST_SUPERUSER)
    assert user is not None
    service.bootstrap_inventory_jobs(session=db, actor=user)
    db.refresh(retry_job)
    assert retry_job.cron_expression == "0 9 * * *"
