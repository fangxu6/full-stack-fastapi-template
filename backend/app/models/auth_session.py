# SQLModel's type stubs cannot express ``Field`` with SQLAlchemy column options.
# mypy: disable-error-code=call-overload

import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlmodel import Field, SQLModel

from .base import get_datetime_utc


class AuthSession(SQLModel, table=True):
    __tablename__ = "auth_session"
    __table_args__ = (
        Index("ix_auth_session_user_id", "user_id"),
        Index("ix_auth_session_active", "user_id", "revoked_at", "expires_at"),
        {"comment": "用户认证会话"},
    )

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(
            PGUUID(as_uuid=True),
            primary_key=True,
            nullable=False,
            comment="认证会话唯一标识",
        ),
    )
    user_id: uuid.UUID = Field(
        sa_column=Column(
            PGUUID(as_uuid=True),
            ForeignKey("user.id", name="fk_auth_session_user", ondelete="CASCADE"),
            nullable=False,
            comment="会话所属用户标识",
        )
    )
    created_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_column=Column(
            DateTime(timezone=True), nullable=False, comment="会话创建时间"
        ),
    )
    expires_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True), nullable=False, comment="会话过期时间"
        ),
    )
    revoked_at: datetime | None = Field(
        default=None,
        sa_column=Column(
            DateTime(timezone=True), nullable=True, comment="会话撤销时间"
        ),
    )
