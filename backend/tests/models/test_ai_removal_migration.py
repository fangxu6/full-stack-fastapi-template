from sqlalchemy import inspect

from app.core.db import engine


def test_current_schema_has_no_retired_ai_audit_objects() -> None:
    inspector = inspect(engine)

    assert "ai_run" not in inspector.get_table_names()
    assert "ai_tool_call" not in inspector.get_table_names()
    assert {
        enum["name"] for enum in inspector.get_enums()
    }.isdisjoint({"ai_run_status", "ai_tool_call_status"})
