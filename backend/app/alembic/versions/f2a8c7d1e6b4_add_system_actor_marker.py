"""add_system_actor_marker.

This revision is forward-only after an audited row references the System Actor.
Recovery from that point is a forward fix or a database backup restore.

Revision ID: f2a8c7d1e6b4
Revises: d7e2a5c9f8b1
Create Date: 2026-07-28
"""

import sqlalchemy as sa
from alembic import op


revision = "f2a8c7d1e6b4"
down_revision = "d7e2a5c9f8b1"
branch_labels = None
depends_on = None


AUDIT_TABLES = (
    "processing_unit",
    "receiving_unit",
    "inventory_document",
    "inventory_document_line",
    "inventory_import_batch",
    "legacy_import_row",
    "inventory_ledger_entry",
    "scheduler_job",
)


def upgrade() -> None:
    op.add_column(
        "user",
        sa.Column(
            "is_system_actor",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.create_index(
        "uq_user_system_actor",
        "user",
        ["is_system_actor"],
        unique=True,
        postgresql_where=sa.text("is_system_actor"),
    )
    op.alter_column("user", "is_system_actor", server_default=None)


def downgrade() -> None:
    connection = op.get_bind()
    system_actor_id = connection.execute(
        sa.text('SELECT id FROM "user" WHERE is_system_actor IS TRUE')
    ).scalar_one_or_none()
    if system_actor_id is not None:
        for table_name in AUDIT_TABLES:
            has_reference = connection.execute(
                sa.text(
                    f"SELECT EXISTS ("
                    f"SELECT 1 FROM {table_name} "
                    f"WHERE created_by = :actor_id OR updated_by = :actor_id"
                    f")"
                ),
                {"actor_id": system_actor_id},
            ).scalar_one()
            if has_reference:
                raise RuntimeError(
                    "Cannot downgrade System Actor support after it has audit references"
                )
    op.drop_index("uq_user_system_actor", table_name="user")
    op.drop_column("user", "is_system_actor")
