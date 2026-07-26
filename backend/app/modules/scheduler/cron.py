from datetime import UTC, datetime, timedelta
from typing import Any, cast
from zoneinfo import ZoneInfo

from celery.schedules import crontab  # type: ignore[import-untyped]

SCHEDULER_TIMEZONE = ZoneInfo("Asia/Shanghai")


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise ValueError("scheduled task timestamps must be timezone-aware")
    return value.astimezone(SCHEDULER_TIMEZONE)


def parse_cron(expression: str) -> Any:
    fields = expression.split()
    if len(fields) != 5:
        raise ValueError("cron expression must contain exactly five fields")
    minute, hour, day_of_month, month_of_year, day_of_week = fields
    return crontab(
        minute=minute,
        hour=hour,
        day_of_month=day_of_month,
        month_of_year=month_of_year,
        day_of_week=day_of_week,
    )


def next_run_at(expression: str, *, after: datetime) -> datetime:
    schedule = parse_cron(expression)
    current = _aware(after)
    schedule.nowfun = lambda: current
    remaining = cast(timedelta, schedule.remaining_estimate(current))
    return (current + remaining).astimezone(UTC)


def scheduled_in_current_minute(planned_at: datetime, *, now: datetime) -> bool:
    return _aware(planned_at).replace(second=0, microsecond=0) == _aware(now).replace(
        second=0, microsecond=0
    )


def matches_cron(expression: str, *, at: datetime) -> bool:
    current = _aware(at).replace(second=0, microsecond=0)
    return next_run_at(
        expression, after=current - timedelta(minutes=1)
    ) == current.astimezone(UTC)
