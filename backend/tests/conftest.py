from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, delete

from app.core.config import settings
from app.core.db import engine, init_db
from app.main import app
from app.models import (
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


@pytest.fixture(scope="session", autouse=True)
def db() -> Generator[Session]:
    assert_safe_test_database(settings.POSTGRES_DB)
    with Session(engine) as session:
        init_db(session)
        yield session
        for model in (
            InventoryLedgerEntry,
            InventoryDocumentLine,
            LegacyImportRow,
            InventoryDocument,
            InventoryImportBatch,
            ProcessingUnit,
            ReceivingUnit,
            Item,
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
