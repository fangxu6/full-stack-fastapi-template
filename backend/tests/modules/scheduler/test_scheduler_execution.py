import uuid
from datetime import UTC, datetime

import pytest
from pydantic import Field

from app.models.scheduler import SchedulerRunStatus, SchedulerRunTrigger
from app.modules.scheduler import execution
from app.modules.scheduler.contracts import (
    ScheduledTask,
    ScheduledTaskConfig,
    ScheduledTaskContext,
    ScheduledTaskSkipped,
    SchedulerRunOutcome,
)

RUN_ID = 42
ACTOR_ID = uuid.UUID("00000000-0000-0000-0000-000000000042")
TRIGGER = SchedulerRunTrigger.MANUAL_NOW
PLANNED_AT = datetime(2026, 8, 6, 8, 0, tzinfo=UTC)
STARTED_AT = datetime(2026, 8, 6, 8, 0, 1, tzinfo=UTC)


def run_execution(
    monkeypatch: pytest.MonkeyPatch,
    task_class: type[ScheduledTask],
    config: dict[str, object] | None = None,
) -> SchedulerRunOutcome:
    monkeypatch.setattr(execution, "resolve_task_class", lambda _: task_class)
    return execution.execute(
        run_id=RUN_ID,
        class_path="app.modules.test.scheduled_tasks.TestTask",
        config_snapshot=config or {},
        actor_id=ACTOR_ID,
        trigger=TRIGGER,
        planned_at=PLANNED_AT,
        started_at=STARTED_AT,
    )


class SuccessfulTask(ScheduledTask):
    config_model = ScheduledTaskConfig

    def run(
        self, *, context: ScheduledTaskContext, config: ScheduledTaskConfig
    ) -> None:
        del context, config


class SkippedTask(ScheduledTask):
    config_model = ScheduledTaskConfig

    def run(
        self, *, context: ScheduledTaskContext, config: ScheduledTaskConfig
    ) -> None:
        del context, config
        raise ScheduledTaskSkipped("NOTHING_TO_DO", "No work was due")


class FailingTask(ScheduledTask):
    config_model = ScheduledTaskConfig

    def run(
        self, *, context: ScheduledTaskContext, config: ScheduledTaskConfig
    ) -> None:
        del context, config
        raise RuntimeError("private failure detail")


class ValueErrorTask(ScheduledTask):
    config_model = ScheduledTaskConfig

    def run(
        self, *, context: ScheduledTaskContext, config: ScheduledTaskConfig
    ) -> None:
        del context, config
        raise ValueError("private validation detail")


class RequiredConfig(ScheduledTaskConfig):
    quantity: int = Field(gt=0)


class RequiredConfigTask(ScheduledTask):
    config_model = RequiredConfig

    def run(self, *, context: ScheduledTaskContext, config: RequiredConfig) -> None:
        del context, config


def test_execute_returns_succeeded(monkeypatch: pytest.MonkeyPatch) -> None:
    outcome = run_execution(monkeypatch, SuccessfulTask)

    assert outcome.status is SchedulerRunStatus.SUCCEEDED
    assert outcome.error_category is None
    assert outcome.error_summary is None


def test_execute_preserves_controlled_skip(monkeypatch: pytest.MonkeyPatch) -> None:
    outcome = run_execution(monkeypatch, SkippedTask)

    assert outcome.status is SchedulerRunStatus.SKIPPED
    assert outcome.error_category == "NOTHING_TO_DO"
    assert outcome.error_summary == "No work was due"


@pytest.mark.parametrize("task_class", [FailingTask, ValueErrorTask])
def test_execute_classifies_task_errors_as_execution_failures(
    monkeypatch: pytest.MonkeyPatch,
    task_class: type[ScheduledTask],
) -> None:
    outcome = run_execution(monkeypatch, task_class)

    assert outcome.status is SchedulerRunStatus.FAILED
    assert outcome.error_category == "EXECUTION_FAILED"
    assert outcome.error_summary == "Scheduled task execution failed"


def test_execute_classifies_resolver_failure_as_configuration_invalid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_resolver(_: str) -> type[ScheduledTask]:
        raise ValueError("private class-path detail")

    monkeypatch.setattr(execution, "resolve_task_class", fail_resolver)
    outcome = execution.execute(
        run_id=RUN_ID,
        class_path="invalid",
        config_snapshot={},
        actor_id=ACTOR_ID,
        trigger=TRIGGER,
        planned_at=PLANNED_AT,
        started_at=STARTED_AT,
    )

    assert outcome.status is SchedulerRunStatus.FAILED
    assert outcome.error_category == "CONFIGURATION_INVALID"
    assert outcome.error_summary == "Scheduled task configuration is invalid"


def test_execute_classifies_config_validation_failure_as_configuration_invalid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    outcome = run_execution(monkeypatch, RequiredConfigTask)

    assert outcome.status is SchedulerRunStatus.FAILED
    assert outcome.error_category == "CONFIGURATION_INVALID"
    assert outcome.error_summary == "Scheduled task configuration is invalid"


def test_execute_passes_scheduler_context_to_task(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: list[ScheduledTaskContext] = []

    class ContextTask(ScheduledTask):
        config_model = ScheduledTaskConfig

        def run(
            self,
            *,
            context: ScheduledTaskContext,
            config: ScheduledTaskConfig,
        ) -> None:
            del config
            captured.append(context)

    outcome = run_execution(monkeypatch, ContextTask)

    assert outcome.status is SchedulerRunStatus.SUCCEEDED
    assert captured == [
        ScheduledTaskContext(
            run_id=RUN_ID,
            actor_id=ACTOR_ID,
            trigger=TRIGGER,
            planned_at=PLANNED_AT,
            started_at=STARTED_AT,
        )
    ]
