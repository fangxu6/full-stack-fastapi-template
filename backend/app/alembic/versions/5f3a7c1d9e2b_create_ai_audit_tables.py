"""create_ai_audit_tables

Revision ID: 5f3a7c1d9e2b
Revises: 4d7e8f9a0b1c
Create Date: 2026-07-17

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "5f3a7c1d9e2b"
down_revision = "4d7e8f9a0b1c"
branch_labels = None
depends_on = None


ai_run_status = postgresql.ENUM(
    "PENDING",
    "COMPLETED",
    "FAILED",
    name="ai_run_status",
    create_type=False,
)
ai_tool_call_status = postgresql.ENUM(
    "PENDING",
    "COMPLETED",
    "FAILED",
    name="ai_tool_call_status",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    ai_run_status.create(bind, checkfirst=True)
    ai_tool_call_status.create(bind, checkfirst=True)

    op.create_table(
        "ai_run",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("request_id", sa.String(length=128), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", ai_run_status, nullable=False),
        sa.Column("question_hash", sa.String(length=64), nullable=False),
        sa.Column("allowed_scopes", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("max_tool_calls", sa.Integer(), nullable=False),
        sa.Column("used_tool_calls", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=True),
        sa.Column("model", sa.String(length=128), nullable=True),
        sa.Column("error_category", sa.String(length=64), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("max_tool_calls > 0", name="ck_ai_run_max_tool_calls"),
        sa.CheckConstraint(
            "used_tool_calls >= 0 AND used_tool_calls <= max_tool_calls",
            name="ck_ai_run_used_tool_calls",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["user.id"], name="fk_ai_run_user", ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["user.id"],
            name="fk_ai_run_created_by",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["updated_by"],
            ["user.id"],
            name="fk_ai_run_updated_by",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_ai_run"),
    )
    op.create_index("ix_ai_run_request_id", "ai_run", ["request_id"], unique=False)
    op.create_index("ix_ai_run_user_id", "ai_run", ["user_id"], unique=False)

    op.create_table(
        "ai_tool_call",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("tool_name", sa.String(length=64), nullable=False),
        sa.Column("status", ai_tool_call_status, nullable=False),
        sa.Column("input_summary", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("source_summary", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("error_category", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint('"sequence" > 0', name="ck_ai_tool_call_sequence"),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["user.id"],
            name="fk_ai_tool_call_created_by",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["run_id"], ["ai_run.id"], name="fk_ai_tool_call_run", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["updated_by"],
            ["user.id"],
            name="fk_ai_tool_call_updated_by",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_ai_tool_call"),
        sa.UniqueConstraint("run_id", "sequence", name="uq_ai_tool_call_run_sequence"),
    )


def downgrade() -> None:
    op.drop_table("ai_tool_call")
    op.drop_index("ix_ai_run_user_id", table_name="ai_run")
    op.drop_index("ix_ai_run_request_id", table_name="ai_run")
    op.drop_table("ai_run")

    bind = op.get_bind()
    ai_tool_call_status.drop(bind, checkfirst=True)
    ai_run_status.drop(bind, checkfirst=True)
