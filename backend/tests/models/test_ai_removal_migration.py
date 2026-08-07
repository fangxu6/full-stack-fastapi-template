from pathlib import Path
from typing import Any, cast
from uuid import uuid4

from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, create_engine, inspect
from sqlalchemy.engine import make_url

from app.core.config import settings
from app.core.db import engine

MIGRATION_PREDECESSOR = "8c4d1e7a2b5f"
ALEMBIC_CONFIG_PATH = Path(__file__).resolve().parents[2] / "alembic.ini"


def _alembic_config() -> Config:
    config = Config(str(ALEMBIC_CONFIG_PATH))
    config.set_main_option(
        "script_location",
        str(ALEMBIC_CONFIG_PATH.parent / "app" / "alembic"),
    )
    return config


def _retired_objects_exist(bind: Engine) -> bool:
    inspector = cast(Any, inspect(bind))
    return {
        "ai_run",
        "ai_tool_call",
    }.issubset(inspector.get_table_names()) and {
        "ai_run_status",
        "ai_tool_call_status",
    }.issubset({enum["name"] for enum in inspector.get_enums()})


def _retired_objects_are_removed(bind: Engine) -> bool:
    inspector = cast(Any, inspect(bind))
    return {
        "ai_run",
        "ai_tool_call",
    }.isdisjoint(inspector.get_table_names()) and {
        "ai_run_status",
        "ai_tool_call_status",
    }.isdisjoint({enum["name"] for enum in inspector.get_enums()})


def test_current_schema_has_no_retired_ai_audit_objects() -> None:
    assert _retired_objects_are_removed(engine)


def test_ai_removal_migration_round_trips_on_isolated_database() -> None:
    original_database = settings.POSTGRES_DB
    temporary_database = f"ai_removal_{uuid4().hex[:12]}_test"
    maintenance_url = make_url(str(settings.SQLALCHEMY_DATABASE_URI)).set(
        database="postgres"
    )
    maintenance_engine = create_engine(maintenance_url)
    isolated_engine = None
    database_created = False
    try:
        with maintenance_engine.connect() as connection:
            connection = connection.execution_options(isolation_level="AUTOCOMMIT")
            connection.exec_driver_sql(f'CREATE DATABASE "{temporary_database}"')
        database_created = True

        settings.POSTGRES_DB = temporary_database
        isolated_engine = create_engine(str(settings.SQLALCHEMY_DATABASE_URI))
        config = _alembic_config()

        command.upgrade(config, "head")
        command.downgrade(config, MIGRATION_PREDECESSOR)
        assert _retired_objects_exist(isolated_engine)

        command.upgrade(config, "head")
        assert _retired_objects_are_removed(isolated_engine)

        command.downgrade(config, MIGRATION_PREDECESSOR)
        assert _retired_objects_exist(isolated_engine)

        command.upgrade(config, "head")
        assert _retired_objects_are_removed(isolated_engine)
    finally:
        if isolated_engine is not None:
            isolated_engine.dispose()
        settings.POSTGRES_DB = original_database
        if database_created:
            with maintenance_engine.connect() as connection:
                connection = connection.execution_options(isolation_level="AUTOCOMMIT")
                connection.exec_driver_sql(f'DROP DATABASE "{temporary_database}"')
        maintenance_engine.dispose()
