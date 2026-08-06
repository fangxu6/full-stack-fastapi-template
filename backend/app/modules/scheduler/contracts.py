import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import ClassVar

from pydantic import BaseModel, ConfigDict

from app.models.scheduler import SchedulerRunStatus, SchedulerRunTrigger


class ScheduledTaskConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")


@dataclass(frozen=True)
class ScheduledTaskContext:
    run_id: int
    actor_id: uuid.UUID
    trigger: SchedulerRunTrigger
    planned_at: datetime
    started_at: datetime


@dataclass(frozen=True)
class SchedulerRunOutcome:
    status: SchedulerRunStatus
    error_category: str | None
    error_summary: str | None


class ScheduledTaskSkipped(Exception):
    def __init__(self, category: str, summary: str) -> None:
        self.category = category
        self.summary = summary
        super().__init__(summary)


class ScheduledTask:
    config_model: ClassVar[type[ScheduledTaskConfig]]
    allow_run_now: ClassVar[bool] = True
    allow_backfill: ClassVar[bool] = False

    def run(
        self, *, context: ScheduledTaskContext, config: ScheduledTaskConfig
    ) -> None:
        raise NotImplementedError
