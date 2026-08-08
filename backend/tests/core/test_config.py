from pathlib import Path
from unittest.mock import Mock

import pytest
from pydantic import ValidationError

from app.core import db
from app.core.config import Settings
from app.core.env import get_env_file


def make_settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "FIRST_SUPERUSER": "test@example.com",
        "FIRST_SUPERUSER_PASSWORD": "test-password",
        "POSTGRES_SERVER": "localhost",
        "POSTGRES_USER": "test",
        "PROJECT_NAME": "test",
        "REDIS_HOST": "redis",
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


def test_celery_urls_percent_encode_the_redis_password() -> None:
    settings = make_settings(REDIS_PASSWORD="pass:/@word")

    assert settings.celery_broker_url == "redis://:pass%3A%2F%40word@redis:6379/0"
    assert (
        settings.celery_result_backend_url == "redis://:pass%3A%2F%40word@redis:6379/1"
    )
    assert settings.redis_cache_url == "redis://:pass%3A%2F%40word@redis:6379/2"


def test_celery_urls_omit_authentication_without_a_redis_password() -> None:
    settings = make_settings()

    assert settings.celery_broker_url == "redis://redis:6379/0"
    assert settings.celery_result_backend_url == "redis://redis:6379/1"
    assert settings.redis_cache_url == "redis://redis:6379/2"


def test_read_replica_uri_is_none_without_a_replica_host() -> None:
    settings = make_settings()

    assert settings.SQLALCHEMY_READ_REPLICA_URI is None


def test_read_replica_uri_reuses_the_primary_connection_fields() -> None:
    settings = make_settings(
        POSTGRES_READ_REPLICA_SERVER="postgres-read",
        POSTGRES_PORT=5433,
        POSTGRES_USER="replica-user",
        POSTGRES_PASSWORD="replica-password",
        POSTGRES_DB="replica-db",
    )

    assert str(settings.SQLALCHEMY_READ_REPLICA_URI) == (
        "postgresql+psycopg://replica-user:replica-password@postgres-read:5433/replica-db"
    )


def test_read_engine_reuses_the_write_engine_without_a_replica(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    write_engine = object()
    create_engine = Mock()
    monkeypatch.setattr(db, "create_engine", create_engine)

    assert db._create_read_engine(write_engine, None) is write_engine
    create_engine.assert_not_called()
    assert db.engine is db.write_engine


def test_read_engine_uses_a_distinct_configured_replica(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    write_engine = object()
    read_engine = object()
    create_engine = Mock(return_value=read_engine)
    monkeypatch.setattr(db, "create_engine", create_engine)

    assert (
        db._create_read_engine(write_engine, "postgresql://postgres-read/app")
        is read_engine
    )
    create_engine.assert_called_once_with("postgresql://postgres-read/app")


@pytest.mark.parametrize(
    "setting_name",
    [
        "CACHE_REDIS_CONNECT_TIMEOUT_SECONDS",
        "CACHE_REDIS_SOCKET_TIMEOUT_SECONDS",
        "CELERY_VISIBILITY_TIMEOUT_SECONDS",
        "CELERY_RESULT_EXPIRES_SECONDS",
    ],
)
def test_celery_timeouts_must_be_positive(setting_name: str) -> None:
    with pytest.raises(ValidationError, match="greater than 0"):
        make_settings(**{setting_name: 0})


def test_redis_password_cannot_use_the_default_outside_local() -> None:
    with pytest.raises(ValidationError, match="REDIS_PASSWORD"):
        make_settings(ENVIRONMENT="production", REDIS_PASSWORD="changethis")


def test_redis_password_is_required_in_production() -> None:
    with pytest.raises(ValidationError, match="REDIS_PASSWORD"):
        make_settings(ENVIRONMENT="production")


def test_settings_env_file_uses_app_env_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    configured_path = tmp_path / ".env.production"
    monkeypatch.setenv("APP_ENV_FILE", str(configured_path))

    assert get_env_file() == configured_path
