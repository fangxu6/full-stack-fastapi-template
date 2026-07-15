import pytest

from tests.conftest import is_safe_test_database


@pytest.mark.parametrize(
    "database_name",
    [
        "aiadmin_test",
        "aiadmin_pytest",
        "feature_inventory_test",
    ],
)
def test_safe_test_database_names_are_allowed(database_name: str) -> None:
    assert is_safe_test_database(database_name)


@pytest.mark.parametrize(
    "database_name",
    [
        "",
        "aiadmin",
        "postgres",
        "template1",
        "aiadmin-prod",
        "aiadmin_test_backup",
    ],
)
def test_non_test_database_names_are_rejected(database_name: str) -> None:
    assert not is_safe_test_database(database_name)
