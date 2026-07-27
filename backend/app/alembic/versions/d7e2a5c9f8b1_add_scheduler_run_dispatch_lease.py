"""add_scheduler_run_dispatch_lease

Revision ID: d7e2a5c9f8b1
Revises: 6e8f2b1c4d7a
Create Date: 2026-07-27
"""

import sqlalchemy as sa
from alembic import op


revision = "d7e2a5c9f8b1"
down_revision = "6e8f2b1c4d7a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "scheduler_run",
        sa.Column("next_dispatch_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.execute(
        "UPDATE scheduler_run SET next_dispatch_at = created_at "
        "WHERE status = 'QUEUED'"
    )
    op.create_index(
        "ix_scheduler_run_queued_dispatch",
        "scheduler_run",
        ["next_dispatch_at", "created_at"],
        postgresql_where=sa.text("status = 'QUEUED'"),
    )


def downgrade() -> None:
    op.drop_index("ix_scheduler_run_queued_dispatch", table_name="scheduler_run")
    op.drop_column("scheduler_run", "next_dispatch_at")
