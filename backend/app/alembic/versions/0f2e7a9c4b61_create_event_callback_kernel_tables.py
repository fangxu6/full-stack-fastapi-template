"""Create event callback kernel tables.

Revision ID: 0f2e7a9c4b61
Revises: f6a1b2c3d4e5
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0f2e7a9c4b61"
down_revision = "f6a1b2c3d4e5"
branch_labels = None
depends_on = None

event_delivery_state = postgresql.ENUM(
    "PENDING",
    "LEASED",
    "RETRY_WAIT",
    "SUCCEEDED",
    "FAILED",
    name="event_delivery_state",
    create_type=False,
)
event_delivery_error_category = postgresql.ENUM(
    "HANDLER_NOT_REGISTERED",
    "HANDLER_EVENT_TYPE_MISMATCH",
    "SCHEMA_VERSION_UNSUPPORTED",
    "HANDLER_REJECTED",
    "HANDLER_EXECUTION_FAILED",
    "EXECUTION_LEASE_EXPIRED",
    name="event_delivery_error_category",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    event_delivery_state.create(bind, checkfirst=True)
    event_delivery_error_category.create(bind, checkfirst=True)

    op.create_table(
        "event_publication",
        sa.Column(
            "id",
            sa.BigInteger(),
            sa.Identity(always=True),
            nullable=False,
            comment="事件发布内部标识",
        ),
        sa.Column(
            "event_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            comment="事件幂等标识",
        ),
        sa.Column(
            "event_type", sa.String(length=128), nullable=False, comment="事件类型代码"
        ),
        sa.Column(
            "producer", sa.String(length=128), nullable=False, comment="事件生产者代码"
        ),
        sa.Column(
            "schema_version", sa.Integer(), nullable=False, comment="事件契约版本"
        ),
        sa.Column(
            "resource_type",
            sa.String(length=128),
            nullable=False,
            comment="资源类型代码",
        ),
        sa.Column(
            "resource_id", sa.String(length=128), nullable=False, comment="资源定位标识"
        ),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            nullable=False,
            comment="业务事件发生时间",
        ),
        sa.Column(
            "request_id", sa.String(length=32), nullable=True, comment="请求关联标识"
        ),
        sa.Column(
            "trace_id", sa.String(length=128), nullable=False, comment="事件追踪标识"
        ),
        sa.Column(
            "idempotency_key",
            sa.String(length=128),
            nullable=False,
            comment="消费者幂等键",
        ),
        sa.Column(
            "payload",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            comment="事件数据快照",
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, comment="创建时间"
        ),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            comment="创建人标识",
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, comment="更新时间"
        ),
        sa.Column(
            "updated_by",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            comment="更新人标识",
        ),
        sa.Column(
            "deleted_at", sa.DateTime(timezone=True), nullable=True, comment="删除时间"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_event_publication"),
        sa.UniqueConstraint("event_id", name="uq_event_publication_event_id"),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["user.id"],
            name="fk_event_publication_created_by",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["updated_by"],
            ["user.id"],
            name="fk_event_publication_updated_by",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "schema_version > 0", name="ck_event_publication_schema_version"
        ),
        sa.CheckConstraint(
            "jsonb_typeof(payload) = 'object'",
            name="ck_event_publication_payload_object",
        ),
        comment="不可变事件发布事实",
    )
    op.create_index(
        "ix_event_publication_created_at", "event_publication", ["created_at", "id"]
    )

    op.create_table(
        "event_delivery",
        sa.Column(
            "id",
            sa.BigInteger(),
            sa.Identity(always=True),
            nullable=False,
            comment="事件投递内部标识",
        ),
        sa.Column(
            "publication_id",
            sa.BigInteger(),
            nullable=False,
            comment="关联事件发布标识",
        ),
        sa.Column(
            "handler_key",
            sa.String(length=128),
            nullable=False,
            comment="处理器稳定代码",
        ),
        sa.Column(
            "state", event_delivery_state, nullable=False, comment="事件投递状态"
        ),
        sa.Column(
            "attempt_count", sa.Integer(), nullable=False, comment="执行尝试次数"
        ),
        sa.Column(
            "next_attempt_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="下一次执行时间",
        ),
        sa.Column(
            "next_dispatch_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="下一次派发时间",
        ),
        sa.Column(
            "lease_token",
            postgresql.UUID(as_uuid=True),
            nullable=True,
            comment="执行租约令牌",
        ),
        sa.Column(
            "lease_expires_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="执行租约到期时间",
        ),
        sa.Column(
            "last_error_category",
            event_delivery_error_category,
            nullable=True,
            comment="最后错误分类",
        ),
        sa.Column(
            "completed_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="投递完成时间",
        ),
        sa.Column(
            "failed_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="投递失败时间",
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, comment="创建时间"
        ),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            comment="创建人标识",
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, comment="更新时间"
        ),
        sa.Column(
            "updated_by",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            comment="更新人标识",
        ),
        sa.Column(
            "deleted_at", sa.DateTime(timezone=True), nullable=True, comment="删除时间"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_event_delivery"),
        sa.UniqueConstraint(
            "publication_id",
            "handler_key",
            name="uq_event_delivery_publication_handler",
        ),
        sa.ForeignKeyConstraint(
            ["publication_id"],
            ["event_publication.id"],
            name="fk_event_delivery_publication",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["user.id"],
            name="fk_event_delivery_created_by",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["updated_by"],
            ["user.id"],
            name="fk_event_delivery_updated_by",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "attempt_count >= 0 AND attempt_count <= 8",
            name="ck_event_delivery_attempt_count",
        ),
        sa.CheckConstraint(
            "state <> 'LEASED' OR (lease_token IS NOT NULL AND lease_expires_at IS NOT NULL AND next_attempt_at IS NULL AND next_dispatch_at IS NULL AND completed_at IS NULL AND failed_at IS NULL)",
            name="ck_event_delivery_active_lease",
        ),
        sa.CheckConstraint(
            "state NOT IN ('PENDING', 'RETRY_WAIT') OR (next_attempt_at IS NOT NULL AND next_dispatch_at IS NOT NULL AND lease_token IS NULL AND lease_expires_at IS NULL AND completed_at IS NULL AND failed_at IS NULL)",
            name="ck_event_delivery_retry_schedule",
        ),
        sa.CheckConstraint(
            "state <> 'SUCCEEDED' OR (completed_at IS NOT NULL AND next_attempt_at IS NULL AND next_dispatch_at IS NULL AND lease_token IS NULL AND lease_expires_at IS NULL AND failed_at IS NULL)",
            name="ck_event_delivery_succeeded_fields",
        ),
        sa.CheckConstraint(
            "state <> 'FAILED' OR (failed_at IS NOT NULL AND next_attempt_at IS NULL AND next_dispatch_at IS NULL AND lease_token IS NULL AND lease_expires_at IS NULL AND completed_at IS NULL)",
            name="ck_event_delivery_failed_fields",
        ),
        comment="事件处理器投递生命周期事实",
    )
    op.create_index(
        "ix_event_delivery_due",
        "event_delivery",
        ["next_attempt_at", "next_dispatch_at", "id"],
        postgresql_where=sa.text("state IN ('PENDING', 'RETRY_WAIT')"),
    )
    op.create_index(
        "ix_event_delivery_expired_lease",
        "event_delivery",
        ["lease_expires_at", "id"],
        postgresql_where=sa.text("state = 'LEASED'"),
    )


def downgrade() -> None:
    bind = op.get_bind()
    for table_name in ("event_delivery", "event_publication"):
        exists = bind.execute(
            sa.text(f"SELECT EXISTS (SELECT 1 FROM {table_name} LIMIT 1)")
        ).scalar()
        if exists:
            raise RuntimeError(
                "event callback tables contain facts; use an isolated empty database for downgrade"
            )
    op.drop_table("event_delivery")
    op.drop_table("event_publication")
    event_delivery_error_category.drop(bind, checkfirst=True)
    event_delivery_state.drop(bind, checkfirst=True)
