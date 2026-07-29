"""Scheduler settings tests."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from app.modules.scheduler.config import SchedulerSettings


def make_scheduler_settings(**overrides: object) -> SchedulerSettings:
    return SchedulerSettings(_env_file=None, **overrides)


def test_alert_recipients_parse_from_csv() -> None:
    scheduler_settings = make_scheduler_settings(
        SCHEDULED_TASK_ALERT_RECIPIENTS="ops@example.com, oncall@example.com"
    )

    assert [
        str(value) for value in scheduler_settings.SCHEDULED_TASK_ALERT_RECIPIENTS
    ] == [
        "ops@example.com",
        "oncall@example.com",
    ]


def test_alert_recipients_parse_from_process_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "SCHEDULED_TASK_ALERT_RECIPIENTS", "ops@example.com, oncall@example.com"
    )

    scheduler_settings = SchedulerSettings(_env_file=None)

    assert [
        str(value) for value in scheduler_settings.SCHEDULED_TASK_ALERT_RECIPIENTS
    ] == [
        "ops@example.com",
        "oncall@example.com",
    ]


def test_alert_recipients_parse_from_dotenv(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "SCHEDULED_TASK_ALERT_RECIPIENTS=ops@example.com, oncall@example.com\n",
        encoding="utf-8",
    )

    scheduler_settings = SchedulerSettings(_env_file=env_file)

    assert [
        str(value) for value in scheduler_settings.SCHEDULED_TASK_ALERT_RECIPIENTS
    ] == [
        "ops@example.com",
        "oncall@example.com",
    ]


@pytest.mark.parametrize(
    "recipients",
    ["not-an-email", "ops@example.com, OPS@example.com"],
)
def test_alert_recipients_reject_invalid_values(recipients: str) -> None:
    with pytest.raises(ValidationError):
        make_scheduler_settings(SCHEDULED_TASK_ALERT_RECIPIENTS=recipients)


def test_alert_recipients_are_optional() -> None:
    assert make_scheduler_settings().SCHEDULED_TASK_ALERT_RECIPIENTS == []
