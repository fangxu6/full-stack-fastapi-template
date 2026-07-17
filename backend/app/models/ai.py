import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    UniqueConstraint,
)
from sqlalchemy import (
    Enum as SAEnum,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlmodel import Field, SQLModel

from app.models.base import get_datetime_utc


class AiRunStatus(StrEnum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class AiToolCallStatus(StrEnum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class AiRun(SQLModel, table=True):
    __tablename__ = "ai_run"
    __table_args__ = (
        CheckConstraint("max_tool_calls > 0", name="ck_ai_run_max_tool_calls"),
        CheckConstraint(
            "used_tool_calls >= 0 AND used_tool_calls <= max_tool_calls",
            name="ck_ai_run_used_tool_calls",
        ),
        Index("ix_ai_run_request_id", "request_id"),
        Index("ix_ai_run_user_id", "user_id"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    request_id: str = Field(max_length=128)
    user_id: uuid.UUID = Field(
        sa_column=Column(
            PGUUID(as_uuid=True),
            ForeignKey("user.id", name="fk_ai_run_user", ondelete="RESTRICT"),
            nullable=False,
        )
    )
    status: AiRunStatus = Field(  # type: ignore[call-overload]
        sa_type=SAEnum(AiRunStatus, name="ai_run_status")  # ty:ignore[invalid-argument-type]
    )
    question_hash: str = Field(max_length=64)
    allowed_scopes: list[str] = Field(default_factory=list, sa_type=JSONB)
    max_tool_calls: int = Field(default=3)
    used_tool_calls: int = Field(default=0)
    provider: str | None = Field(default=None, max_length=64)
    model: str | None = Field(default=None, max_length=128)
    error_category: str | None = Field(default=None, max_length=64)
    started_at: datetime = Field(  # type: ignore[call-overload]
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # ty:ignore[invalid-argument-type]
    )
    completed_at: datetime | None = Field(  # type: ignore[call-overload]
        default=None,
        sa_type=DateTime(timezone=True),  # ty:ignore[invalid-argument-type]
    )
    created_at: datetime = Field(  # type: ignore[call-overload]
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # ty:ignore[invalid-argument-type]
    )
    created_by: uuid.UUID = Field(
        sa_column=Column(
            PGUUID(as_uuid=True),
            ForeignKey("user.id", name="fk_ai_run_created_by", ondelete="RESTRICT"),
            nullable=False,
        )
    )
    updated_at: datetime = Field(  # type: ignore[call-overload]
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # ty:ignore[invalid-argument-type]
    )
    updated_by: uuid.UUID = Field(
        sa_column=Column(
            PGUUID(as_uuid=True),
            ForeignKey("user.id", name="fk_ai_run_updated_by", ondelete="RESTRICT"),
            nullable=False,
        )
    )
    deleted_at: datetime | None = Field(  # type: ignore[call-overload]
        default=None,
        sa_type=DateTime(timezone=True),  # ty:ignore[invalid-argument-type]
    )


class AiToolCall(SQLModel, table=True):
    __tablename__ = "ai_tool_call"
    __table_args__ = (
        CheckConstraint('"sequence" > 0', name="ck_ai_tool_call_sequence"),
        UniqueConstraint("run_id", "sequence", name="uq_ai_tool_call_run_sequence"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    run_id: uuid.UUID = Field(
        sa_column=Column(
            PGUUID(as_uuid=True),
            ForeignKey("ai_run.id", name="fk_ai_tool_call_run", ondelete="CASCADE"),
            nullable=False,
        )
    )
    sequence: int
    tool_name: str = Field(max_length=64)
    status: AiToolCallStatus = Field(  # type: ignore[call-overload]
        sa_type=SAEnum(AiToolCallStatus, name="ai_tool_call_status")  # ty:ignore[invalid-argument-type]
    )
    input_summary: dict[str, object] = Field(sa_type=JSONB)
    source_summary: dict[str, object] = Field(sa_type=JSONB)
    error_category: str | None = Field(default=None, max_length=64)
    created_at: datetime = Field(  # type: ignore[call-overload]
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # ty:ignore[invalid-argument-type]
    )
    created_by: uuid.UUID = Field(
        sa_column=Column(
            PGUUID(as_uuid=True),
            ForeignKey(
                "user.id", name="fk_ai_tool_call_created_by", ondelete="RESTRICT"
            ),
            nullable=False,
        )
    )
    updated_at: datetime = Field(  # type: ignore[call-overload]
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # ty:ignore[invalid-argument-type]
    )
    updated_by: uuid.UUID = Field(
        sa_column=Column(
            PGUUID(as_uuid=True),
            ForeignKey(
                "user.id", name="fk_ai_tool_call_updated_by", ondelete="RESTRICT"
            ),
            nullable=False,
        )
    )
    deleted_at: datetime | None = Field(  # type: ignore[call-overload]
        default=None,
        sa_type=DateTime(timezone=True),  # ty:ignore[invalid-argument-type]
    )
