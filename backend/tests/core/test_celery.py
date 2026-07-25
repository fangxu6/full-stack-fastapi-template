from typing import cast
from unittest.mock import patch

import pytest

from app.core.celery import celery_app
from app.core.config import settings
from app.core.tasks import runtime_ping, send_scheduled_test_email
from app.utils import EmailData


def test_runtime_ping_executes_eagerly() -> None:
    previous = celery_app.conf.task_always_eager
    celery_app.conf.task_always_eager = True
    try:
        result = celery_app.tasks["runtime.ping"].delay("ping")
    finally:
        celery_app.conf.task_always_eager = previous

    assert result.get(timeout=1) == "ping"


@pytest.mark.parametrize(
    ("value", "message"),
    [(42, "must be a string"), ("x" * 65, "64 characters or fewer")],
)
def test_runtime_ping_rejects_invalid_values(value: object, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        runtime_ping(cast(str, value))


def test_inventory_daily_report_beat_tasks_are_registered() -> None:
    celery_app.loader.import_default_modules()

    assert celery_app.conf.timezone == "Asia/Shanghai"
    assert (
        celery_app.conf.beat_schedule["inventory-daily-report-create"]["task"]
        == "inventory.daily_report.create"
    )
    assert (
        celery_app.conf.beat_schedule["inventory-daily-report-retry"]["task"]
        == "inventory.daily_report.retry"
    )
    assert celery_app.conf.beat_schedule["runtime-daily-test-email"]["task"] == (
        "runtime.send_test_email"
    )
    assert settings.CELERY_VISIBILITY_TIMEOUT_SECONDS == 3600
    assert "inventory.daily_report.deliver" in celery_app.tasks
    assert "runtime.send_test_email" in celery_app.tasks


def test_scheduled_test_email_uses_the_configured_recipient() -> None:
    email_data = EmailData(html_content="<p>test</p>", subject="Test email")
    with (
        patch(
            "app.core.tasks.generate_test_email", return_value=email_data
        ) as generate,
        patch("app.core.tasks.send_email") as send,
    ):
        send_scheduled_test_email()

    recipient = str(settings.EMAIL_TEST_USER)
    generate.assert_called_once_with(email_to=recipient)
    send.assert_called_once_with(
        email_to=recipient,
        subject=email_data.subject,
        html_content=email_data.html_content,
    )
