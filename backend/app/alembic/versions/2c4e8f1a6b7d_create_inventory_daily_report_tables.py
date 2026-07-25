"""create_inventory_daily_report_tables

Revision ID: 2c4e8f1a6b7d
Revises: 7b22a1c9e5d4
Create Date: 2026-07-25

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "2c4e8f1a6b7d"
down_revision = "7b22a1c9e5d4"
branch_labels = None
depends_on = None


inventory_daily_report_status = postgresql.ENUM(
    "PENDING",
    "RETRY_WAIT",
    "DELIVERED",
    "FAILED",
    name="inventory_daily_report_status",
    create_type=False,
)
inventory_daily_report_delivery_status = postgresql.ENUM(
    "PENDING",
    "DELIVERING",
    "RETRY_WAIT",
    "DELIVERED",
    "FAILED",
    name="inventory_daily_report_delivery_status",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    inventory_daily_report_status.create(bind, checkfirst=True)
    inventory_daily_report_delivery_status.create(bind, checkfirst=True)

    op.create_table(
        "inventory_daily_report",
        sa.Column(
            "id", sa.BigInteger(), sa.Identity(always=True), nullable=False
        ),
        sa.Column("processing_unit_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("business_date", sa.Date(), nullable=False),
        sa.Column("processing_unit_name", sa.String(length=255), nullable=False),
        sa.Column("snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", inventory_daily_report_status, nullable=False),
        sa.Column("recipients_resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolution_attempt_count", sa.Integer(), nullable=False),
        sa.Column(
            "next_recipient_attempt_at", sa.DateTime(timezone=True), nullable=False
        ),
        sa.Column("last_error_category", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "resolution_attempt_count >= 0 AND resolution_attempt_count <= 8",
            name="ck_inventory_daily_report_resolution_attempts",
        ),
        sa.ForeignKeyConstraint(
            ["processing_unit_id"],
            ["processing_unit.id"],
            name="fk_inventory_daily_report_processing_unit",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_inventory_daily_report"),
        sa.UniqueConstraint(
            "processing_unit_id",
            "business_date",
            name="uq_inventory_daily_report_unit_date",
        ),
    )
    op.create_index(
        "ix_inventory_daily_report_recipient_retry",
        "inventory_daily_report",
        ["status", "next_recipient_attempt_at"],
        unique=False,
    )

    op.create_table(
        "inventory_daily_report_delivery",
        sa.Column(
            "id", sa.BigInteger(), sa.Identity(always=True), nullable=False
        ),
        sa.Column("report_id", sa.BigInteger(), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("status", inventory_daily_report_delivery_status, nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error_category", sa.String(length=64), nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "attempt_count >= 0 AND attempt_count <= 8",
            name="ck_inventory_daily_report_delivery_attempts",
        ),
        sa.ForeignKeyConstraint(
            ["report_id"],
            ["inventory_daily_report.id"],
            name="fk_inventory_daily_report_delivery_report",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_inventory_daily_report_delivery"),
        sa.UniqueConstraint(
            "report_id",
            "email",
            name="uq_inventory_daily_report_delivery_report_email",
        ),
    )
    op.create_index(
        "ix_inventory_daily_report_delivery_retry",
        "inventory_daily_report_delivery",
        ["status", "next_attempt_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_inventory_daily_report_delivery_retry",
        table_name="inventory_daily_report_delivery",
    )
    op.drop_table("inventory_daily_report_delivery")
    op.drop_index(
        "ix_inventory_daily_report_recipient_retry",
        table_name="inventory_daily_report",
    )
    op.drop_table("inventory_daily_report")

    bind = op.get_bind()
    inventory_daily_report_delivery_status.drop(bind, checkfirst=True)
    inventory_daily_report_status.drop(bind, checkfirst=True)
