import uuid
from datetime import datetime

from pydantic import ValidationError

from app.models.scheduler import SchedulerRunStatus, SchedulerRunTrigger
from app.modules.scheduler.contracts import (
    ScheduledTaskContext,
    ScheduledTaskSkipped,
    SchedulerRunOutcome,
)
from app.modules.scheduler.service import resolve_task_class

CONFIGURATION_ERROR_CATEGORY = "CONFIGURATION_INVALID"
CONFIGURATION_ERROR_SUMMARY = "Scheduled task configuration is invalid"
EXECUTION_ERROR_CATEGORY = "EXECUTION_FAILED"
EXECUTION_ERROR_SUMMARY = "Scheduled task execution failed"


def execute(
    *,
    run_id: int,
    class_path: str,
    config_snapshot: dict[str, object],
    actor_id: uuid.UUID,
    trigger: SchedulerRunTrigger,
    planned_at: datetime,
    started_at: datetime,
) -> SchedulerRunOutcome:
    try:
        task_class = resolve_task_class(class_path)
        config = task_class.config_model.model_validate(config_snapshot)
        task = task_class()
    except ValidationError, ValueError:
        return SchedulerRunOutcome(
            status=SchedulerRunStatus.FAILED,
            error_category=CONFIGURATION_ERROR_CATEGORY,
            error_summary=CONFIGURATION_ERROR_SUMMARY,
        )

    try:
        task.run(
            context=ScheduledTaskContext(
                run_id=run_id,
                actor_id=actor_id,
                trigger=trigger,
                planned_at=planned_at,
                started_at=started_at,
            ),
            config=config,
        )
    except ScheduledTaskSkipped as skipped:
        return SchedulerRunOutcome(
            status=SchedulerRunStatus.SKIPPED,
            error_category=skipped.category,
            error_summary=skipped.summary,
        )
    except Exception:
        return SchedulerRunOutcome(
            status=SchedulerRunStatus.FAILED,
            error_category=EXECUTION_ERROR_CATEGORY,
            error_summary=EXECUTION_ERROR_SUMMARY,
        )

    return SchedulerRunOutcome(
        status=SchedulerRunStatus.SUCCEEDED,
        error_category=None,
        error_summary=None,
    )
