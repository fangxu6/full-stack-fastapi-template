from typing import Annotated, Any

from pydantic import BeforeValidator, EmailStr, Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

from app.core.config import settings
from app.core.env import get_env_file


def _parse_recipients(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    return [item.strip() for item in value.split(",") if item.strip()]


class SchedulerSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=get_env_file(), env_ignore_empty=True, extra="ignore"
    )
    SCHEDULED_TASK_ALERT_RECIPIENTS: Annotated[
        list[EmailStr], NoDecode, BeforeValidator(_parse_recipients)
    ] = Field(default_factory=list)

    @field_validator("SCHEDULED_TASK_ALERT_RECIPIENTS")
    @classmethod
    def _unique_recipients(cls, value: list[EmailStr]) -> list[EmailStr]:
        normalized = [str(recipient).casefold() for recipient in value]
        if len(normalized) != len(set(normalized)):
            raise ValueError(
                "scheduled task alert recipients cannot contain duplicates"
            )
        return value


scheduler_settings = SchedulerSettings()


def validate_scheduler_runtime_settings() -> None:
    if settings.ENVIRONMENT == "local":
        return
    if (
        not settings.emails_enabled
        or not scheduler_settings.SCHEDULED_TASK_ALERT_RECIPIENTS
    ):
        raise ValueError(
            "scheduled task Worker and Beat require SMTP and SCHEDULED_TASK_ALERT_RECIPIENTS outside local"
        )
