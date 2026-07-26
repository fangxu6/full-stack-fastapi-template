from datetime import UTC, datetime

import pytest

from app.modules.scheduler.cron import (
    matches_cron,
    next_run_at,
    scheduled_in_current_minute,
)


def test_next_run_and_current_minute_use_shanghai_timezone() -> None:
    current = datetime(2026, 7, 26, 0, 0, 59, tzinfo=UTC)

    assert scheduled_in_current_minute(
        datetime(2026, 7, 26, 0, 0, tzinfo=UTC), now=current
    )
    assert next_run_at("0 8 * * *", after=current) == datetime(
        2026, 7, 27, 0, 0, tzinfo=UTC
    )


def test_cron_uses_celery_day_and_weekday_semantics() -> None:
    matching = datetime(2026, 6, 1, 0, 0, tzinfo=UTC)
    non_matching_weekday = datetime(2026, 7, 1, 0, 0, tzinfo=UTC)

    assert matches_cron("0 8 1 * 1", at=matching)
    assert not matches_cron("0 8 1 * 1", at=non_matching_weekday)


@pytest.mark.parametrize("expression", ["", "0 8 * * * *", "0 8 * *"])
def test_cron_requires_exactly_five_fields(expression: str) -> None:
    with pytest.raises(ValueError, match="exactly five"):
        next_run_at(expression, after=datetime(2026, 7, 26, tzinfo=UTC))
