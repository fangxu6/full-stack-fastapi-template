"""create_audit_event_table

Revision ID: aa03e8f7c9b1
Revises: 3e0ac19b57b1
Create Date: 2026-08-03
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "aa03e8f7c9b1"
down_revision = "3e0ac19b57b1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "audit_event",
        sa.Column(
            "id",
            sa.BigInteger(),
            sa.Identity(always=True),
            nullable=False,
            comment="审计事件唯一标识",
        ),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
            comment="事件发生时间",
        ),
        sa.Column(
            "actor_user_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
            comment="操作者用户标识",
        ),
        sa.Column("request_id", sa.Text(), nullable=True, comment="请求关联标识"),
        sa.Column("action", sa.String(length=128), nullable=False, comment="事件动作"),
        sa.Column(
            "resource_type",
            sa.String(length=64),
            nullable=False,
            comment="资源类型",
        ),
        sa.Column(
            "resource_id",
            sa.String(length=128),
            nullable=False,
            comment="资源标识",
        ),
        sa.Column(
            "changes",
            postgresql.JSONB(),
            nullable=False,
            comment="变更摘要",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(changes) = 'object'",
            name="ck_audit_event_changes_object",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_audit_event"),
        comment="语义变更审计事件",
    )
    op.create_index(
        "ix_audit_event_occurred_at",
        "audit_event",
        [sa.text("occurred_at DESC")],
        unique=False,
    )
    op.create_index(
        "ix_audit_event_resource_time",
        "audit_event",
        ["resource_type", "resource_id", sa.text("occurred_at DESC")],
        unique=False,
    )
    op.create_index(
        "ix_audit_event_actor_time",
        "audit_event",
        ["actor_user_id", sa.text("occurred_at DESC")],
        unique=False,
    )


def downgrade() -> None:
    has_audit_events = op.get_bind().execute(
        sa.text("SELECT EXISTS (SELECT 1 FROM audit_event)")
    ).scalar()
    if has_audit_events:
        raise RuntimeError("cannot downgrade audit_event while it contains audit records")
    op.drop_index("ix_audit_event_actor_time", table_name="audit_event")
    op.drop_index("ix_audit_event_resource_time", table_name="audit_event")
    op.drop_index("ix_audit_event_occurred_at", table_name="audit_event")
    op.drop_table("audit_event")
