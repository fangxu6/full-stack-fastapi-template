import pytest
from pydantic import ValidationError

from app.modules.inventory.config import InventorySettings


def make_inventory_settings(**overrides: object) -> InventorySettings:
    return InventorySettings(_env_file=None, **overrides)


def test_daily_report_recipients_parse_from_json() -> None:
    settings = make_inventory_settings(
        INVENTORY_DAILY_REPORT_RECIPIENTS=(
            '{"00000000-0000-0000-0000-000000000001": ["daily@example.com"]}'
        )
    )

    assert str(next(iter(settings.INVENTORY_DAILY_REPORT_RECIPIENTS))) == (
        "00000000-0000-0000-0000-000000000001"
    )
    assert list(settings.INVENTORY_DAILY_REPORT_RECIPIENTS.values()) == [
        ["daily@example.com"]
    ]


@pytest.mark.parametrize(
    "recipients",
    [
        '{"00000000-0000-0000-0000-000000000001": []}',
        '{"00000000-0000-0000-0000-000000000001": ["bad-email"]}',
        '{"00000000-0000-0000-0000-000000000001": ["daily@example.com", "DAILY@example.com"]}',
    ],
)
def test_daily_report_recipients_reject_invalid_mappings(recipients: str) -> None:
    with pytest.raises(ValidationError):
        make_inventory_settings(INVENTORY_DAILY_REPORT_RECIPIENTS=recipients)
