# SQLModel's type stubs cannot express ``Field`` with SQLAlchemy column options.
# mypy: disable-error-code=call-overload

import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime
from sqlmodel import Field, SQLModel


def get_datetime_utc() -> datetime:
    return datetime.now(UTC)


class AuditFields(SQLModel):
    # The audit listener replaces these actor placeholders before every flush.
    created_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # ty:ignore[invalid-argument-type]
        sa_column_kwargs={"comment": "创建时间"},
        nullable=False,
    )
    created_by: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        foreign_key="user.id",
        nullable=False,
        ondelete="RESTRICT",
        sa_column_kwargs={"comment": "创建人标识"},
    )
    updated_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # ty:ignore[invalid-argument-type]
        sa_column_kwargs={"comment": "更新时间"},
        nullable=False,
    )
    updated_by: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        foreign_key="user.id",
        nullable=False,
        ondelete="RESTRICT",
        sa_column_kwargs={"comment": "更新人标识"},
    )
    deleted_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),  # ty:ignore[invalid-argument-type]
        sa_column_kwargs={"comment": "删除时间"},
        nullable=True,
    )
