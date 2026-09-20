"""Durable event publication and delivery facts."""

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
    UniqueConstraint,
    text,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlmodel import Field

from app.models.base import AuditFields


class EventDeliveryState(StrEnum):
    PENDING = "PENDING"
    LEASED = "LEASED"
    RETRY_WAIT = "RETRY_WAIT"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"


class EventDeliveryErrorCategory(StrEnum):
    HANDLER_NOT_REGISTERED = "HANDLER_NOT_REGISTERED"
    HANDLER_EVENT_TYPE_MISMATCH = "HANDLER_EVENT_TYPE_MISMATCH"
    SCHEMA_VERSION_UNSUPPORTED = "SCHEMA_VERSION_UNSUPPORTED"
    HANDLER_REJECTED = "HANDLER_REJECTED"
    HANDLER_EXECUTION_FAILED = "HANDLER_EXECUTION_FAILED"
    EXECUTION_LEASE_EXPIRED = "EXECUTION_LEASE_EXPIRED"


class EventPublication(AuditFields, table=True):
    __tablename__ = "event_publication"
    __table_args__ = (
        UniqueConstraint("event_id", name="uq_event_publication_event_id"),
        CheckConstraint(
            "schema_version > 0", name="ck_event_publication_schema_version"
        ),
        CheckConstraint(
            "jsonb_typeof(payload) = 'object'",
            name="ck_event_publication_payload_object",
        ),
        Index(
            "ix_event_publication_created_at",
            "created_at",
            "id",
        ),
        {"comment": "不可变事件发布事实"},
    )

    id: int | None = Field(
        default=None,
        sa_column=Column(
            BigInteger,
            Identity(always=True),
            primary_key=True,
            comment="事件发布内部标识",
        ),
    )
    event_id: uuid.UUID = Field(
        sa_column=Column(PGUUID(as_uuid=True), nullable=False, comment="事件幂等标识"),
    )
    event_type: str = Field(
        max_length=128, sa_column_kwargs={"comment": "事件类型代码"}
    )
    producer: str = Field(
        max_length=128, sa_column_kwargs={"comment": "事件生产者代码"}
    )
    schema_version: int = Field(sa_column_kwargs={"comment": "事件契约版本"})
    resource_type: str = Field(
        max_length=128, sa_column_kwargs={"comment": "资源类型代码"}
    )
    resource_id: str = Field(
        max_length=128, sa_column_kwargs={"comment": "资源定位标识"}
    )
    occurred_at: datetime = Field(
        sa_type=DateTime(timezone=True),  # ty:ignore[invalid-argument-type]
        sa_column_kwargs={"comment": "业务事件发生时间"},
    )
    request_id: str | None = Field(
        default=None, max_length=32, sa_column_kwargs={"comment": "请求关联标识"}
    )
    trace_id: str = Field(max_length=128, sa_column_kwargs={"comment": "事件追踪标识"})
    idempotency_key: str = Field(
        max_length=128, sa_column_kwargs={"comment": "消费者幂等键"}
    )
    payload: dict[str, object] = Field(
        sa_type=JSONB, sa_column_kwargs={"comment": "事件数据快照"}
    )


class EventDelivery(AuditFields, table=True):
    __tablename__ = "event_delivery"
    __table_args__ = (
        UniqueConstraint(
            "publication_id",
            "handler_key",
            name="uq_event_delivery_publication_handler",
        ),
        CheckConstraint(
            "attempt_count >= 0 AND attempt_count <= 8",
            name="ck_event_delivery_attempt_count",
        ),
        CheckConstraint(
            "state <> 'LEASED' OR "
            "(lease_token IS NOT NULL AND lease_expires_at IS NOT NULL "
            "AND next_attempt_at IS NULL AND next_dispatch_at IS NULL "
            "AND completed_at IS NULL AND failed_at IS NULL)",
            name="ck_event_delivery_active_lease",
        ),
        CheckConstraint(
            "state NOT IN ('PENDING', 'RETRY_WAIT') OR "
            "(next_attempt_at IS NOT NULL AND next_dispatch_at IS NOT NULL "
            "AND lease_token IS NULL AND lease_expires_at IS NULL "
            "AND completed_at IS NULL AND failed_at IS NULL)",
            name="ck_event_delivery_retry_schedule",
        ),
        CheckConstraint(
            "state <> 'SUCCEEDED' OR "
            "(completed_at IS NOT NULL AND next_attempt_at IS NULL "
            "AND next_dispatch_at IS NULL AND lease_token IS NULL "
            "AND lease_expires_at IS NULL AND failed_at IS NULL)",
            name="ck_event_delivery_succeeded_fields",
        ),
        CheckConstraint(
            "state <> 'FAILED' OR "
            "(failed_at IS NOT NULL AND next_attempt_at IS NULL "
            "AND next_dispatch_at IS NULL AND lease_token IS NULL "
            "AND lease_expires_at IS NULL AND completed_at IS NULL)",
            name="ck_event_delivery_failed_fields",
        ),
        Index(
            "ix_event_delivery_due",
            "next_attempt_at",
            "next_dispatch_at",
            "id",
            postgresql_where=text("state IN ('PENDING', 'RETRY_WAIT')"),
        ),
        Index(
            "ix_event_delivery_expired_lease",
            "lease_expires_at",
            "id",
            postgresql_where=text("state = 'LEASED'"),
        ),
        {"comment": "事件处理器投递生命周期事实"},
    )

    id: int | None = Field(
        default=None,
        sa_column=Column(
            BigInteger,
            Identity(always=True),
            primary_key=True,
            comment="事件投递内部标识",
        ),
    )
    publication_id: int = Field(
        sa_column=Column(
            BigInteger,
            ForeignKey(
                "event_publication.id",
                name="fk_event_delivery_publication",
                ondelete="RESTRICT",
            ),
            nullable=False,
            comment="关联事件发布标识",
        )
    )
    handler_key: str = Field(
        max_length=128, sa_column_kwargs={"comment": "处理器稳定代码"}
    )
    state: EventDeliveryState = Field(
        default=EventDeliveryState.PENDING,
        sa_type=SAEnum(  # ty:ignore[invalid-argument-type]
            EventDeliveryState, name="event_delivery_state"
        ),
        sa_column_kwargs={"comment": "事件投递状态"},
    )
    attempt_count: int = Field(default=0, sa_column_kwargs={"comment": "执行尝试次数"})
    next_attempt_at: datetime | None = Field(
        sa_type=DateTime(timezone=True),  # ty:ignore[invalid-argument-type]
        sa_column_kwargs={"comment": "下一次执行时间"},
    )
    next_dispatch_at: datetime | None = Field(
        sa_type=DateTime(timezone=True),  # ty:ignore[invalid-argument-type]
        sa_column_kwargs={"comment": "下一次派发时间"},
    )
    lease_token: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PGUUID(as_uuid=True), nullable=True, comment="执行租约令牌"),
    )
    lease_expires_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),  # ty:ignore[invalid-argument-type]
        sa_column_kwargs={"comment": "执行租约到期时间"},
    )
    last_error_category: EventDeliveryErrorCategory | None = Field(
        default=None,
        sa_type=SAEnum(  # ty:ignore[invalid-argument-type]
            EventDeliveryErrorCategory, name="event_delivery_error_category"
        ),
        sa_column_kwargs={"comment": "最后错误分类"},
    )
    completed_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),  # ty:ignore[invalid-argument-type]
        sa_column_kwargs={"comment": "投递完成时间"},
    )
    failed_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),  # ty:ignore[invalid-argument-type]
        sa_column_kwargs={"comment": "投递失败时间"},
    )
