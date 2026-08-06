from datetime import UTC, datetime

import pytest

from app.modules.inventory.correction_workflow import normalize_timestamp


def test_normalize_timestamp_rejects_naive_values() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        normalize_timestamp(datetime(2026, 8, 7))


def test_normalize_timestamp_returns_utc() -> None:
    value = normalize_timestamp(datetime(2026, 8, 7, 8, tzinfo=UTC))

    assert value.tzinfo is UTC
    assert value.hour == 8
