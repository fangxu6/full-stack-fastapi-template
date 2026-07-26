from dataclasses import dataclass
from datetime import datetime
from typing import ClassVar

from pydantic import BaseModel, ConfigDict

from app.models.scheduler import SchedulerRunTrigger


class ScheduledTaskConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")


@dataclass(frozen=True)
class ScheduledTaskContext:
    run_id: int
    trigger: SchedulerRunTrigger
    planned_at: datetime
    started_at: datetime


class ScheduledTaskSkipped(Exception):
    def __init__(self, category: str, summary: str) -> None:
        self.category = category
        self.summary = summary
        super().__init__(summary)


class ScheduledTask:
    config_model: ClassVar[type[ScheduledTaskConfig]]

    def run(
        self, *, context: ScheduledTaskContext, config: ScheduledTaskConfig
    ) -> None:
        raise NotImplementedError
