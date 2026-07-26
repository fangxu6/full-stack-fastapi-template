"""Scheduler settings tests."""

import pytest
from pydantic import ValidationError

from app.core.config import settings
from app.modules.scheduler import config
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


@pytest.mark.parametrize(
    "recipients",
    ["not-an-email", "ops@example.com, OPS@example.com"],
)
def test_alert_recipients_reject_invalid_values(recipients: str) -> None:
    with pytest.raises(ValidationError):
        make_scheduler_settings(SCHEDULED_TASK_ALERT_RECIPIENTS=recipients)


def test_runtime_settings_allow_local_without_smtp(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "ENVIRONMENT", "local")
    monkeypatch.setattr(
        config.scheduler_settings, "SCHEDULED_TASK_ALERT_RECIPIENTS", []
    )

    config.validate_scheduler_runtime_settings()


def test_runtime_settings_require_smtp_and_recipients_outside_local(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "ENVIRONMENT", "staging")
    monkeypatch.setattr(settings, "SMTP_HOST", None)
    monkeypatch.setattr(
        config.scheduler_settings, "SCHEDULED_TASK_ALERT_RECIPIENTS", []
    )

    with pytest.raises(ValueError, match="require SMTP"):
        config.validate_scheduler_runtime_settings()
