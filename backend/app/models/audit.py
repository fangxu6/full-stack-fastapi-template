# SQLModel's type stubs cannot express ``Field`` with SQLAlchemy column options.
# mypy: disable-error-code=call-overload

import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Column,
    DateTime,
    Identity,
    Index,
    String,
    Text,
    desc,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlmodel import Field, SQLModel

from app.models.base import get_datetime_utc


class AuditEvent(SQLModel, table=True):
    __tablename__ = "audit_event"
    __table_args__ = (
        CheckConstraint(
            "jsonb_typeof(changes) = 'object'",
            name="ck_audit_event_changes_object",
        ),
        Index("ix_audit_event_occurred_at", desc("occurred_at")),
        Index(
            "ix_audit_event_resource_time",
            "resource_type",
            "resource_id",
            desc("occurred_at"),
        ),
        Index("ix_audit_event_actor_time", "actor_user_id", desc("occurred_at")),
        {"comment": "语义变更审计事件"},
    )

    id: int | None = Field(
        default=None,
        sa_column=Column(
            BigInteger,
            Identity(always=True),
            primary_key=True,
            comment="审计事件唯一标识",
        ),
    )
    occurred_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_column=Column(
            DateTime(timezone=True),
            nullable=False,
            server_default=text("now()"),
            comment="事件发生时间",
        ),
    )
    actor_user_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            PGUUID(as_uuid=True),
            nullable=True,
            comment="操作者用户标识",
        ),
    )
    request_id: str | None = Field(
        default=None,
        sa_column=Column(Text, nullable=True, comment="请求关联标识"),
    )
    action: str = Field(
        sa_column=Column(String(128), nullable=False, comment="事件动作"),
    )
    resource_type: str = Field(
        sa_column=Column(String(64), nullable=False, comment="资源类型"),
    )
    resource_id: str = Field(
        sa_column=Column(String(128), nullable=False, comment="资源标识"),
    )
    changes: dict[str, object] = Field(
        default_factory=dict,
        sa_column=Column(JSONB, nullable=False, comment="变更摘要"),
    )
