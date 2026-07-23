from collections.abc import Generator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlmodel import Session, delete

from app.core.config import settings
from app.core.db import engine, init_db
from app.main import app
from app.models import (
    AiRun,
    AiToolCall,
    IamPermission,
    IamRole,
    IamRolePermission,
    IamUserRole,
    InventoryDocument,
    InventoryDocumentLine,
    InventoryImportBatch,
    InventoryLedgerEntry,
    Item,
    LegacyImportRow,
    ProcessingUnit,
    ReceivingUnit,
    User,
)
from tests.utils.user import authentication_token_from_email
from tests.utils.utils import get_superuser_token_headers

SAFE_TEST_DATABASE_SUFFIXES = ("_test", "_pytest")
UNSAFE_DATABASE_NAMES = {"", "aiadmin", "postgres", "template0", "template1"}
ALEMBIC_CONFIG_PATH = Path(__file__).resolve().parents[1] / "alembic.ini"


def is_safe_test_database(database_name: str) -> bool:
    normalized_name = database_name.strip().lower()
    return normalized_name not in UNSAFE_DATABASE_NAMES and normalized_name.endswith(
        SAFE_TEST_DATABASE_SUFFIXES
    )


def assert_safe_test_database(database_name: str) -> None:
    if is_safe_test_database(database_name):
        return
    pytest.exit(
        "Refusing to run destructive tests against database "
        f"{database_name!r}. Set POSTGRES_DB to an isolated test database "
        "ending with '_test' or '_pytest'.",
        returncode=2,
    )


def upgrade_test_database() -> None:
    alembic_config = Config(str(ALEMBIC_CONFIG_PATH))
    alembic_config.set_main_option(
        "script_location", str(ALEMBIC_CONFIG_PATH.parent / "app" / "alembic")
    )
    command.upgrade(alembic_config, "head")


@pytest.fixture(scope="session", autouse=True)
def db() -> Generator[Session]:
    assert_safe_test_database(settings.POSTGRES_DB)
    upgrade_test_database()
    with Session(engine) as session:
        init_db(session)
        yield session
        for model in (
            AiToolCall,
            AiRun,
            InventoryLedgerEntry,
            InventoryDocumentLine,
            LegacyImportRow,
            InventoryDocument,
            InventoryImportBatch,
            ProcessingUnit,
            ReceivingUnit,
            Item,
            IamUserRole,
            IamRolePermission,
            IamRole,
            IamPermission,
            User,
        ):
            session.execute(delete(model))
        session.commit()


@pytest.fixture(scope="module")
def client() -> Generator[TestClient]:
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def superuser_token_headers(client: TestClient) -> dict[str, str]:
    return get_superuser_token_headers(client)


@pytest.fixture(scope="module")
def normal_user_token_headers(client: TestClient, db: Session) -> dict[str, str]:
    return authentication_token_from_email(
        client=client, email=settings.EMAIL_TEST_USER, db=db
    )
