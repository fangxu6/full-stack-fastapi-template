"""create_scheduler_task_tables

Revision ID: 8c4d1e7a2b5f
Revises: 2c4e8f1a6b7d
Create Date: 2026-07-26
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "8c4d1e7a2b5f"
down_revision = "2c4e8f1a6b7d"
branch_labels = None
depends_on = None

scheduler_run_status = postgresql.ENUM("QUEUED", "RUNNING", "SUCCEEDED", "FAILED", "SKIPPED", "CANCELLED", name="scheduler_run_status", create_type=False)
scheduler_run_trigger = postgresql.ENUM("SCHEDULED", "MANUAL_NOW", "MANUAL_BACKFILL", name="scheduler_run_trigger", create_type=False)


def upgrade() -> None:
    bind = op.get_bind()
    scheduler_run_status.create(bind, checkfirst=True)
    scheduler_run_trigger.create(bind, checkfirst=True)
    op.create_table(
        "scheduler_job",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("class_path", sa.String(length=255), nullable=False),
        sa.Column("cron_expression", sa.String(length=128), nullable=False),
        sa.Column("config", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("bootstrap_key", sa.String(length=128), nullable=True),
        sa.Column("run_failure_alerted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("overlap_alerted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("configuration_alerted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["created_by"], ["user.id"], name="fk_scheduler_job_created_by", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["updated_by"], ["user.id"], name="fk_scheduler_job_updated_by", ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name="pk_scheduler_job"),
    )
    op.create_index("ix_scheduler_job_ready", "scheduler_job", ["next_run_at"], postgresql_where=sa.text("enabled AND deleted_at IS NULL"))
    op.create_index("uq_scheduler_job_bootstrap_key", "scheduler_job", ["bootstrap_key"], unique=True, postgresql_where=sa.text("bootstrap_key IS NOT NULL"))
    op.create_table(
        "scheduler_run",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("job_id", sa.BigInteger(), nullable=False),
        sa.Column("status", scheduler_run_status, nullable=False),
        sa.Column("trigger", scheduler_run_trigger, nullable=False),
        sa.Column("planned_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("class_path", sa.String(length=255), nullable=False),
        sa.Column("config", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("requested_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("error_category", sa.String(length=64), nullable=True),
        sa.Column("error_summary", sa.String(length=512), nullable=True),
        sa.CheckConstraint("attempt_count >= 0", name="ck_scheduler_run_attempt_count"),
        sa.CheckConstraint("(trigger = 'SCHEDULED' AND requested_by IS NULL) OR (trigger <> 'SCHEDULED' AND requested_by IS NOT NULL)", name="ck_scheduler_run_requester"),
        sa.ForeignKeyConstraint(["job_id"], ["scheduler_job.id"], name="fk_scheduler_run_job", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["requested_by"], ["user.id"], name="fk_scheduler_run_requested_by", ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name="pk_scheduler_run"),
    )
    op.create_index("ix_scheduler_run_job_created_at", "scheduler_run", ["job_id", "created_at"])
    op.create_index("ix_scheduler_run_finished_at", "scheduler_run", ["finished_at"])
    op.create_index("uq_scheduler_run_job_active", "scheduler_run", ["job_id"], unique=True, postgresql_where=sa.text("status IN ('QUEUED', 'RUNNING')"))


def downgrade() -> None:
    op.drop_index("uq_scheduler_run_job_active", table_name="scheduler_run")
    op.drop_index("ix_scheduler_run_finished_at", table_name="scheduler_run")
    op.drop_index("ix_scheduler_run_job_created_at", table_name="scheduler_run")
    op.drop_table("scheduler_run")
    op.drop_index("uq_scheduler_job_bootstrap_key", table_name="scheduler_job")
    op.drop_index("ix_scheduler_job_ready", table_name="scheduler_job")
    op.drop_table("scheduler_job")
    bind = op.get_bind()
    scheduler_run_trigger.drop(bind, checkfirst=True)
    scheduler_run_status.drop(bind, checkfirst=True)
