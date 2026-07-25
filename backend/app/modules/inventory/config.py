import json
import uuid
from typing import Annotated, Any

from pydantic import BeforeValidator, EmailStr, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.env import get_env_file


def _parse_json_mapping(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    try:
        return json.loads(value)
    except json.JSONDecodeError as err:
        raise ValueError("must be valid JSON") from err


class InventorySettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=get_env_file(),
        env_ignore_empty=True,
        extra="ignore",
    )

    INVENTORY_DAILY_REPORT_RECIPIENTS: Annotated[
        dict[uuid.UUID, list[EmailStr]], BeforeValidator(_parse_json_mapping)
    ] = Field(default_factory=dict)

    @field_validator("INVENTORY_DAILY_REPORT_RECIPIENTS")
    @classmethod
    def _validate_daily_report_recipients(
        cls, value: dict[uuid.UUID, list[EmailStr]]
    ) -> dict[uuid.UUID, list[EmailStr]]:
        for recipients in value.values():
            if not recipients:
                raise ValueError(
                    "inventory daily report recipient lists cannot be empty"
                )
            normalized = [str(recipient).casefold() for recipient in recipients]
            if len(set(normalized)) != len(normalized):
                raise ValueError(
                    "inventory daily report recipients cannot contain duplicates"
                )
        return value


inventory_settings = InventorySettings()
