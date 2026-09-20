"""Immutable event and handler contracts."""

import copy
import json
import math
import re
import uuid
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from typing import cast

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.observability import REQUEST_ID_PATTERN, current_request_id

MAX_PAYLOAD_BYTES = 65_536
MAX_PAYLOAD_DEPTH = 32
_CODE_PATTERN = re.compile(r"^[^\s]{1,128}$")


class EventContractError(ValueError):
    """Raised when an event or registration violates the kernel contract."""


class EventPublicationConflict(EventContractError):
    """The event ID was previously used for different event semantics."""


class EventHandlerRegistrationError(EventContractError):
    """A handler registration is invalid or duplicated."""


class PermanentEventError(Exception):
    """A handler rejected an event without a retryable execution failure."""


def _validate_json_value(value: object, *, depth: int = 1) -> None:
    if depth > MAX_PAYLOAD_DEPTH:
        raise EventContractError("event payload exceeds the maximum nesting depth")
    if value is None or isinstance(value, str | bool | int):
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            raise EventContractError("event payload contains a non-finite number")
        return
    if isinstance(value, list):
        for item in value:
            _validate_json_value(item, depth=depth + 1)
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise EventContractError("event payload keys must be strings")
            _validate_json_value(item, depth=depth + 1)
        return
    raise EventContractError("event payload contains a non-JSON value")


def normalize_payload(payload: Mapping[str, object]) -> dict[str, object]:
    if not isinstance(payload, dict):
        raise EventContractError("event payload must be a JSON object")
    copied = copy.deepcopy(dict(payload))
    _validate_json_value(copied)
    try:
        encoded = json.dumps(
            copied,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    except (TypeError, ValueError) as error:
        raise EventContractError("event payload is not strict JSON") from error
    if len(encoded) > MAX_PAYLOAD_BYTES:
        raise EventContractError("event payload exceeds 65536 UTF-8 bytes")
    return cast(dict[str, object], json.loads(encoded.decode("utf-8")))


def normalize_timestamp(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise EventContractError("occurred_at must be timezone-aware")
    return value.astimezone(UTC)


class EventEnvelope(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    event_id: uuid.UUID
    event_type: str = Field(min_length=1, max_length=128)
    producer: str = Field(min_length=1, max_length=128)
    schema_version: int = Field(gt=0)
    resource_type: str = Field(min_length=1, max_length=128)
    resource_id: str = Field(min_length=1, max_length=128)
    occurred_at: datetime
    request_id: str | None = Field(default=None, max_length=32)
    trace_id: str = Field(default="", min_length=1, max_length=128)
    idempotency_key: str = Field(default="", min_length=1, max_length=128)
    payload: dict[str, object]

    @field_validator("event_type", "producer", "resource_type", "resource_id")
    @classmethod
    def _validate_code(cls, value: str) -> str:
        if not _CODE_PATTERN.fullmatch(value):
            raise EventContractError("event contract codes must be non-blank")
        return value

    @field_validator("request_id")
    @classmethod
    def _validate_request_id(cls, value: str | None) -> str | None:
        if value is not None and REQUEST_ID_PATTERN.fullmatch(value) is None:
            raise EventContractError(
                "request_id must be a lowercase 32-character hex ID"
            )
        return value

    @field_validator("trace_id", "idempotency_key")
    @classmethod
    def _validate_context_value(cls, value: str) -> str:
        if not value.strip():
            raise EventContractError("event context values must be non-blank")
        return value

    @field_validator("occurred_at")
    @classmethod
    def _normalize_occurred_at(cls, value: datetime) -> datetime:
        return normalize_timestamp(value)

    @field_validator("payload")
    @classmethod
    def _normalize_payload(cls, value: dict[str, object]) -> dict[str, object]:
        return normalize_payload(value)

    @model_validator(mode="before")
    @classmethod
    def _fill_context_defaults(cls, value: object) -> object:
        if not isinstance(value, dict):
            return value
        values = dict(value)
        event_id = values.get("event_id")
        try:
            event_uuid = (
                event_id
                if isinstance(event_id, uuid.UUID)
                else uuid.UUID(str(event_id))
            )
        except AttributeError, ValueError:
            event_uuid = None
        if not values.get("request_id"):
            values["request_id"] = current_request_id()
        if not values.get("trace_id") and event_uuid is not None:
            values["trace_id"] = event_uuid.hex
        if not values.get("idempotency_key") and event_uuid is not None:
            values["idempotency_key"] = str(event_uuid)
        return values


type EventHandler = Callable[[EventEnvelope], None]


class EventHandlerRegistration(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    handler_key: str = Field(min_length=1, max_length=128)
    event_type: str = Field(min_length=1, max_length=128)
    schema_versions: frozenset[int] = Field(min_length=1)
    handler: EventHandler

    @field_validator("schema_versions")
    @classmethod
    def _validate_schema_versions(cls, value: frozenset[int]) -> frozenset[int]:
        if not value or any(version <= 0 for version in value):
            raise EventHandlerRegistrationError("schema versions must be positive")
        return value

    @field_validator("handler")
    @classmethod
    def _validate_handler(cls, value: EventHandler) -> EventHandler:
        if not callable(value):
            raise EventHandlerRegistrationError("event handler must be callable")
        return value

    @field_validator("handler_key", "event_type")
    @classmethod
    def _validate_registration_code(cls, value: str) -> str:
        if _CODE_PATTERN.fullmatch(value) is None:
            raise EventHandlerRegistrationError(
                "event handler codes must be non-blank and contain no whitespace"
            )
        return value
