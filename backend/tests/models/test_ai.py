from app.models import SQLModel


def test_ai_audit_models_use_the_ai_database_namespace() -> None:
    tables = SQLModel.metadata.tables

    assert "ai_run" in tables
    assert "ai_tool_call" in tables

    run_table = tables["ai_run"]
    tool_call_table = tables["ai_tool_call"]

    assert {index.name for index in run_table.indexes} >= {
        "ix_ai_run_request_id",
        "ix_ai_run_user_id",
    }
    assert {constraint.name for constraint in run_table.constraints} >= {
        "ck_ai_run_max_tool_calls",
        "ck_ai_run_used_tool_calls",
        "fk_ai_run_user",
        "fk_ai_run_created_by",
        "fk_ai_run_updated_by",
    }
    assert {constraint.name for constraint in tool_call_table.constraints} >= {
        "ck_ai_tool_call_sequence",
        "uq_ai_tool_call_run_sequence",
        "fk_ai_tool_call_run",
        "fk_ai_tool_call_created_by",
        "fk_ai_tool_call_updated_by",
    }
    assert run_table.c.status.type.name == "ai_run_status"
    assert tool_call_table.c.status.type.name == "ai_tool_call_status"
