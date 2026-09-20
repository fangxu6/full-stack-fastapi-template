import importlib.util
import re
from pathlib import Path

from app.models import EventDelivery, EventPublication


def test_event_tables_use_the_platform_database_contract() -> None:
    for model, expected_name in (
        (EventPublication, "event_publication"),
        (EventDelivery, "event_delivery"),
    ):
        table = model.__table__  # type: ignore[union-attr]
        assert table.name == expected_name
        assert table.comment and re.search(r"[\u4e00-\u9fff]", table.comment)
        assert all(
            column.comment and re.search(r"[\u4e00-\u9fff]", column.comment)
            for column in table.columns
        )
        assert table.primary_key.columns["id"].identity is not None


def test_event_migration_is_forward_and_namespace_scoped() -> None:
    migration_path = (
        Path(__file__).resolve().parents[3]
        / "app"
        / "alembic"
        / "versions"
        / "0f2e7a9c4b61_create_event_callback_kernel_tables.py"
    )
    spec = importlib.util.spec_from_file_location("event_migration", migration_path)
    assert spec is not None and spec.loader is not None
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)

    assert migration.revision == "0f2e7a9c4b61"
    assert migration.down_revision == "f6a1b2c3d4e5"
    assert migration.event_delivery_state.name == "event_delivery_state"
    assert migration.event_delivery_error_category.name == (
        "event_delivery_error_category"
    )
    assert (
        "HANDLER_EVENT_TYPE_MISMATCH" in migration.event_delivery_error_category.enums
    )
