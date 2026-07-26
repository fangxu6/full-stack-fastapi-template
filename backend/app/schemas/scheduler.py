import uuid
from datetime import datetime
from typing import Any

from pydantic import Field
from sqlmodel import SQLModel
from sqlmodel._compat import SQLModelConfig

from app.models.scheduler import SchedulerRunStatus, SchedulerRunTrigger

JsonObject = dict[str, Any]


class SchedulerJobCreate(SQLModel):
    model_config = SQLModelConfig(extra="forbid")
    name: str = Field(min_length=1, max_length=128)
    class_path: str = Field(min_length=1, max_length=255)
    cron_expression: str = Field(min_length=1, max_length=128)
    config: JsonObject = Field(default_factory=dict)


class SchedulerJobUpdate(SQLModel):
    model_config = SQLModelConfig(extra="forbid")
    name: str | None = Field(default=None, min_length=1, max_length=128)
    class_path: str | None = Field(default=None, min_length=1, max_length=255)
    cron_expression: str | None = Field(default=None, min_length=1, max_length=128)
    config: JsonObject | None = None


class SchedulerRunBackfill(SQLModel):
    model_config = SQLModelConfig(extra="forbid")
    planned_at: datetime


class SchedulerJobPublic(SQLModel):
    id: int
    name: str
    class_path: str
    cron_expression: str
    config: JsonObject
    enabled: bool
    next_run_at: datetime
    deleted_at: datetime | None
    created_at: datetime
    created_by: uuid.UUID
    updated_at: datetime
    updated_by: uuid.UUID


class SchedulerJobsPublic(SQLModel):
    data: list[SchedulerJobPublic]
    count: int


class SchedulerRunPublic(SQLModel):
    id: int
    job_id: int
    status: SchedulerRunStatus
    trigger: SchedulerRunTrigger
    planned_at: datetime
    class_path: str
    config: JsonObject
    requested_by: uuid.UUID | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    attempt_count: int
    error_category: str | None
    error_summary: str | None


class SchedulerRunsPublic(SQLModel):
    data: list[SchedulerRunPublic]
    count: int


class SchedulerTaskSchemaPublic(SQLModel):
    class_path: str
    json_schema: JsonObject
