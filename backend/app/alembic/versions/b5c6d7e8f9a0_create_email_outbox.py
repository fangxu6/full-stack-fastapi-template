"""create_email_outbox

Revision ID: b5c6d7e8f9a0
Revises: a8b4c2d6e9f0
Create Date: 2026-07-29
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "b5c6d7e8f9a0"
down_revision = "a8b4c2d6e9f0"
branch_labels = None
depends_on = None


email_outbox_kind = postgresql.ENUM(
    "RENDERED",
    "ACCOUNT_SET_PASSWORD",
    "PASSWORD_RECOVERY",
    name="email_outbox_kind",
    create_type=False,
)
email_outbox_status = postgresql.ENUM(
    "PENDING",
    "LEASED",
    "RETRY_WAIT",
    "DELIVERED",
    "FAILED",
    name="email_outbox_status",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    email_outbox_kind.create(bind, checkfirst=True)
    email_outbox_status.create(bind, checkfirst=True)
    op.create_table(
        "email_outbox",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("kind", email_outbox_kind, nullable=False),
        sa.Column("recipient", sa.String(length=320), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("subject", sa.String(length=255), nullable=True),
        sa.Column("html_content", sa.Text(), nullable=True),
        sa.Column("status", email_outbox_status, nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error_category", sa.String(length=64), nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "attempt_count >= 0 AND attempt_count <= 8",
            name="ck_email_outbox_attempt_count",
        ),
        sa.CheckConstraint(
            "(kind = 'RENDERED' AND user_id IS NULL "
            "AND subject IS NOT NULL AND html_content IS NOT NULL) OR "
            "(kind IN ('ACCOUNT_SET_PASSWORD', 'PASSWORD_RECOVERY') "
            "AND user_id IS NOT NULL AND subject IS NULL AND html_content IS NULL)",
            name="ck_email_outbox_payload",
        ),
        sa.CheckConstraint(
            "last_error_category IS NULL OR last_error_category IN "
            "('SMTP_NOT_CONFIGURED', 'SMTP_DELIVERY_FAILED', "
            "'DELIVERY_LEASE_EXPIRED', 'RECIPIENT_INVALID', "
            "'MAX_ATTEMPTS_EXCEEDED')",
            name="ck_email_outbox_error_category",
        ),
        sa.CheckConstraint(
            "status <> 'LEASED' OR lease_expires_at IS NOT NULL",
            name="ck_email_outbox_lease",
        ),
        sa.CheckConstraint(
            "status <> 'DELIVERED' OR delivered_at IS NOT NULL",
            name="ck_email_outbox_delivered_at",
        ),
        sa.CheckConstraint(
            "status <> 'FAILED' OR failed_at IS NOT NULL",
            name="ck_email_outbox_failed_at",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["user.id"], name="fk_email_outbox_user", ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["created_by"], ["user.id"], name="fk_email_outbox_created_by", ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["updated_by"], ["user.id"], name="fk_email_outbox_updated_by", ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_email_outbox"),
    )
    op.create_index(
        "ix_email_outbox_due",
        "email_outbox",
        ["next_attempt_at", "id"],
        postgresql_where=sa.text("status IN ('PENDING', 'RETRY_WAIT')"),
    )
    op.create_index(
        "ix_email_outbox_lease",
        "email_outbox",
        ["lease_expires_at", "id"],
        postgresql_where=sa.text("status = 'LEASED'"),
    )


def downgrade() -> None:
    op.drop_index("ix_email_outbox_lease", table_name="email_outbox")
    op.drop_index("ix_email_outbox_due", table_name="email_outbox")
    op.drop_table("email_outbox")
    bind = op.get_bind()
    email_outbox_status.drop(bind, checkfirst=True)
    email_outbox_kind.drop(bind, checkfirst=True)
