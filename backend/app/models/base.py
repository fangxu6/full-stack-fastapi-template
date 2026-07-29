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
        nullable=False,
    )
    created_by: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        foreign_key="user.id",
        nullable=False,
        ondelete="RESTRICT",
    )
    updated_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # ty:ignore[invalid-argument-type]
        nullable=False,
    )
    updated_by: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        foreign_key="user.id",
        nullable=False,
        ondelete="RESTRICT",
    )
    deleted_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),  # ty:ignore[invalid-argument-type]
        nullable=True,
    )
