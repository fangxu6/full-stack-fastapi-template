from pathlib import Path

import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.core.env import get_env_file


def make_settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "FIRST_SUPERUSER": "test@example.com",
        "FIRST_SUPERUSER_PASSWORD": "test-password",
        "POSTGRES_SERVER": "localhost",
        "POSTGRES_USER": "test",
        "PROJECT_NAME": "test",
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


def test_celery_urls_percent_encode_the_redis_password() -> None:
    settings = make_settings(REDIS_PASSWORD="pass:/@word")

    assert settings.celery_broker_url == "redis://:pass%3A%2F%40word@redis:6379/0"
    assert (
        settings.celery_result_backend_url == "redis://:pass%3A%2F%40word@redis:6379/1"
    )


def test_celery_urls_omit_authentication_without_a_redis_password() -> None:
    settings = make_settings()

    assert settings.celery_broker_url == "redis://redis:6379/0"
    assert settings.celery_result_backend_url == "redis://redis:6379/1"


@pytest.mark.parametrize(
    "setting_name",
    ["CELERY_VISIBILITY_TIMEOUT_SECONDS", "CELERY_RESULT_EXPIRES_SECONDS"],
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
