"""add_system_actor_key.

Revision ID: a8b4c2d6e9f0
Revises: f2a8c7d1e6b4
Create Date: 2026-07-29
"""

import sqlalchemy as sa
from alembic import op


revision = "a8b4c2d6e9f0"
down_revision = "f2a8c7d1e6b4"
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
        sa.Column("system_actor_key", sa.String(length=100), nullable=True),
    )
    connection = op.get_bind()
    connection.execute(
        sa.text(
            "UPDATE \"user\" SET system_actor_key = 'system', is_active = FALSE "
            "WHERE is_system_actor IS TRUE"
        )
    )
    op.drop_index("uq_user_system_actor", table_name="user")
    op.create_index(
        "uq_user_system_actor_key",
        "user",
        ["system_actor_key"],
        unique=True,
        postgresql_where=sa.text("is_system_actor"),
    )
    op.create_check_constraint(
        "ck_user_system_actor_key",
        "user",
        "(is_system_actor AND is_active IS FALSE AND system_actor_key IS NOT NULL "
        "AND btrim(system_actor_key) <> '') "
        "OR (NOT is_system_actor AND system_actor_key IS NULL)",
    )


def downgrade() -> None:
    connection = op.get_bind()
    system_actor_ids = connection.execute(
        sa.text('SELECT id FROM "user" WHERE is_system_actor IS TRUE')
    ).scalars().all()
    if len(system_actor_ids) > 1:
        raise RuntimeError(
            "Cannot downgrade System Actor keys after multiple System Actors exist"
        )
    for system_actor_id in system_actor_ids:
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
    op.drop_constraint("ck_user_system_actor_key", "user", type_="check")
    op.drop_index("uq_user_system_actor_key", table_name="user")
    op.drop_column("user", "system_actor_key")
    op.create_index(
        "uq_user_system_actor",
        "user",
        ["is_system_actor"],
        unique=True,
        postgresql_where=sa.text("is_system_actor"),
    )
