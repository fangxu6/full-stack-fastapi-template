# SQLModel's type stubs cannot express ``Field`` with SQLAlchemy column options.
# mypy: disable-error-code=call-overload

import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    text,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlmodel import Field, SQLModel

from app.models.base import AuditFields, get_datetime_utc


class SchedulerRunStatus(StrEnum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"
    CANCELLED = "CANCELLED"


class SchedulerRunTrigger(StrEnum):
    SCHEDULED = "SCHEDULED"
    MANUAL_NOW = "MANUAL_NOW"
    MANUAL_BACKFILL = "MANUAL_BACKFILL"


class SchedulerJob(AuditFields, table=True):
    __tablename__ = "scheduler_job"
    __table_args__ = (
        Index(
            "ix_scheduler_job_ready",
            "next_run_at",
            postgresql_where=text("enabled AND deleted_at IS NULL"),
        ),
        Index(
            "uq_scheduler_job_bootstrap_key",
            "bootstrap_key",
            unique=True,
            postgresql_where=text("bootstrap_key IS NOT NULL"),
        ),
    )

    id: int | None = Field(
        default=None,
        sa_column=Column(BigInteger, Identity(always=True), primary_key=True),
    )
    name: str = Field(max_length=128)
    class_path: str = Field(max_length=255)
    cron_expression: str = Field(max_length=128)
    config: dict[str, object] = Field(default_factory=dict, sa_type=JSONB)
    enabled: bool = Field(default=False)
    next_run_at: datetime = Field(
        sa_type=DateTime(timezone=True)  # ty:ignore[invalid-argument-type]
    )
    bootstrap_key: str | None = Field(default=None, max_length=128)
    run_failure_alerted_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),  # ty:ignore[invalid-argument-type]
    )
    overlap_alerted_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),  # ty:ignore[invalid-argument-type]
    )
    configuration_alerted_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),  # ty:ignore[invalid-argument-type]
    )


class SchedulerRun(SQLModel, table=True):
    __tablename__ = "scheduler_run"
    __table_args__ = (
        CheckConstraint("attempt_count >= 0", name="ck_scheduler_run_attempt_count"),
        CheckConstraint(
            "(trigger = 'SCHEDULED' AND requested_by IS NULL) OR "
            "(trigger <> 'SCHEDULED' AND requested_by IS NOT NULL)",
            name="ck_scheduler_run_requester",
        ),
        Index("ix_scheduler_run_job_created_at", "job_id", "created_at"),
        Index("ix_scheduler_run_finished_at", "finished_at"),
        Index(
            "ix_scheduler_run_queued_dispatch",
            "next_dispatch_at",
            "created_at",
            postgresql_where=text("status = 'QUEUED'"),
        ),
        Index(
            "uq_scheduler_run_job_active",
            "job_id",
            unique=True,
            postgresql_where=text("status IN ('QUEUED', 'RUNNING')"),
        ),
    )

    id: int | None = Field(
        default=None,
        sa_column=Column(BigInteger, Identity(always=True), primary_key=True),
    )
    job_id: int = Field(
        sa_column=Column(
            BigInteger,
            ForeignKey(
                "scheduler_job.id",
                name="fk_scheduler_run_job",
                ondelete="RESTRICT",
            ),
            nullable=False,
        )
    )
    status: SchedulerRunStatus = Field(
        default=SchedulerRunStatus.QUEUED,
        sa_type=SAEnum(  # ty:ignore[invalid-argument-type]
            SchedulerRunStatus, name="scheduler_run_status"
        ),
    )
    trigger: SchedulerRunTrigger = Field(
        sa_type=SAEnum(  # ty:ignore[invalid-argument-type]
            SchedulerRunTrigger, name="scheduler_run_trigger"
        )
    )
    planned_at: datetime = Field(
        sa_type=DateTime(timezone=True)  # ty:ignore[invalid-argument-type]
    )
    class_path: str = Field(max_length=255)
    config: dict[str, object] = Field(default_factory=dict, sa_type=JSONB)
    requested_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            PGUUID(as_uuid=True),
            ForeignKey(
                "user.id",
                name="fk_scheduler_run_requested_by",
                ondelete="RESTRICT",
            ),
            nullable=True,
        ),
    )
    created_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # ty:ignore[invalid-argument-type]
    )
    next_dispatch_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),  # ty:ignore[invalid-argument-type]
    )
    started_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),  # ty:ignore[invalid-argument-type]
    )
    finished_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),  # ty:ignore[invalid-argument-type]
    )
    lease_expires_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),  # ty:ignore[invalid-argument-type]
    )
    attempt_count: int = Field(default=0)
    error_category: str | None = Field(default=None, max_length=64)
    error_summary: str | None = Field(default=None, max_length=512)
