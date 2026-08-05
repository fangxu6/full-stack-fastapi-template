# SQLModel's type stubs cannot express ``Field`` with SQLAlchemy column options.
# mypy: disable-error-code=call-overload

import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Text,
    text,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlmodel import Field

from app.models.base import AuditFields


class EmailOutboxKind(StrEnum):
    RENDERED = "RENDERED"
    ACCOUNT_SET_PASSWORD = "ACCOUNT_SET_PASSWORD"
    PASSWORD_RECOVERY = "PASSWORD_RECOVERY"


class EmailOutboxStatus(StrEnum):
    PENDING = "PENDING"
    LEASED = "LEASED"
    RETRY_WAIT = "RETRY_WAIT"
    DELIVERED = "DELIVERED"
    FAILED = "FAILED"


class EmailOutbox(AuditFields, table=True):
    __tablename__ = "email_outbox"
    __table_args__ = (
        CheckConstraint(
            "attempt_count >= 0 AND attempt_count <= 8",
            name="ck_email_outbox_attempt_count",
        ),
        CheckConstraint(
            "(kind = 'RENDERED' AND user_id IS NULL "
            "AND subject IS NOT NULL AND html_content IS NOT NULL) OR "
            "(kind IN ('ACCOUNT_SET_PASSWORD', 'PASSWORD_RECOVERY') "
            "AND user_id IS NOT NULL AND subject IS NULL AND html_content IS NULL)",
            name="ck_email_outbox_payload",
        ),
        CheckConstraint(
            "last_error_category IS NULL OR last_error_category IN "
            "('SMTP_NOT_CONFIGURED', 'SMTP_DELIVERY_FAILED', "
            "'DELIVERY_LEASE_EXPIRED', 'RECIPIENT_INVALID', "
            "'MAX_ATTEMPTS_EXCEEDED', 'TOKEN_SUPERSEDED')",
            name="ck_email_outbox_error_category",
        ),
        CheckConstraint(
            "status <> 'LEASED' OR lease_expires_at IS NOT NULL",
            name="ck_email_outbox_lease",
        ),
        CheckConstraint(
            "status <> 'DELIVERED' OR delivered_at IS NOT NULL",
            name="ck_email_outbox_delivered_at",
        ),
        CheckConstraint(
            "status <> 'FAILED' OR failed_at IS NOT NULL",
            name="ck_email_outbox_failed_at",
        ),
        CheckConstraint(
            "kind = 'RENDERED' OR password_reset_version IS NOT NULL "
            "OR status IN ('FAILED', 'DELIVERED')",
            name="ck_email_outbox_password_reset_version",
        ),
        Index(
            "ix_email_outbox_due",
            "next_attempt_at",
            "id",
            postgresql_where=text("status IN ('PENDING', 'RETRY_WAIT')"),
        ),
        Index(
            "ix_email_outbox_lease",
            "lease_expires_at",
            "id",
            postgresql_where=text("status = 'LEASED'"),
        ),
    )

    id: int | None = Field(
        default=None,
        sa_column=Column(BigInteger, Identity(always=True), primary_key=True),
    )
    kind: EmailOutboxKind = Field(
        sa_type=SAEnum(EmailOutboxKind, name="email_outbox_kind")  # ty:ignore[invalid-argument-type]
    )
    recipient: str = Field(max_length=320)
    user_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            PGUUID(as_uuid=True),
            ForeignKey(
                "user.id",
                name="fk_email_outbox_user",
                ondelete="RESTRICT",
            ),
            nullable=True,
        ),
    )
    password_reset_version: int | None = Field(
        default=None,
        sa_column_kwargs={"comment": "密码链接版本快照"},
    )
    subject: str | None = Field(default=None, max_length=255)
    html_content: str | None = Field(
        default=None,
        sa_type=Text,
    )
    status: EmailOutboxStatus = Field(
        default=EmailOutboxStatus.PENDING,
        sa_type=SAEnum(EmailOutboxStatus, name="email_outbox_status"),  # ty:ignore[invalid-argument-type]
    )
    attempt_count: int = Field(default=0)
    next_attempt_at: datetime = Field(
        sa_type=DateTime(timezone=True)  # ty:ignore[invalid-argument-type]
    )
    lease_expires_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),  # ty:ignore[invalid-argument-type]
    )
    last_error_category: str | None = Field(default=None, max_length=64)
    delivered_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),  # ty:ignore[invalid-argument-type]
    )
    failed_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),  # ty:ignore[invalid-argument-type]
    )
