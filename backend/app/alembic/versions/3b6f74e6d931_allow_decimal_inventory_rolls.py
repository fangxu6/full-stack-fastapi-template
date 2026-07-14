"""allow decimal inventory rolls

Revision ID: 3b6f74e6d931
Revises: c9b1f4e7a2d0
Create Date: 2026-07-14

"""

from decimal import Decimal

import sqlalchemy as sa
from alembic import op

revision = "3b6f74e6d931"
down_revision = "c9b1f4e7a2d0"
branch_labels = None
depends_on = None


FRACTIONAL_ROLLS = sa.text(
    """
    WITH source_rolls AS (
        SELECT
            line.id AS line_id,
            movement.id AS movement_id,
            opening.id AS opening_id,
            line.quantity_rolls AS current_rolls,
            movement.rolls_delta AS current_delta,
            movement.movement_type::text AS movement_type,
            ABS(
                CASE document.document_type::text
                    WHEN 'RAW_RECEIPT' THEN COALESCE(
                        NULLIF(source.raw_cells ->> '入库', '')::numeric,
                        NULLIF(source.raw_cells ->> '入库匹数', '')::numeric,
                        NULLIF(source.raw_cells ->> '入库数量', '')::numeric
                    )
                    WHEN 'RAW_RETURN' THEN COALESCE(
                        NULLIF(source.raw_cells ->> '入库', '')::numeric,
                        NULLIF(source.raw_cells ->> '入库匹数', '')::numeric,
                        NULLIF(source.raw_cells ->> '入库数量', '')::numeric
                    )
                    WHEN 'FINISHED_RECEIPT' THEN
                        NULLIF(source.raw_cells ->> '入库匹数', '')::numeric
                    WHEN 'FINISHED_SHIPMENT' THEN
                        NULLIF(source.raw_cells ->> '出库匹数', '')::numeric
                END
            ) AS expected_rolls
        FROM inventory_document_line AS line
        JOIN inventory_document AS document ON document.id = line.document_id
        JOIN inventory_ledger_entry AS movement
            ON movement.document_line_id = line.id
        JOIN legacy_import_row AS source
            ON source.id = movement.legacy_import_row_id
        LEFT JOIN inventory_ledger_entry AS opening
            ON opening.legacy_import_row_id = source.id
            AND opening.movement_type = 'MIGRATION_RECONCILIATION_OPENING'
            AND opening.ledger_kind = movement.ledger_kind
            AND opening.processing_unit_id = movement.processing_unit_id
            AND opening.item_name = movement.item_name
            AND opening.item_code IS NOT DISTINCT FROM movement.item_code
            AND opening.wool_content = movement.wool_content
            AND opening.color_code IS NOT DISTINCT FROM movement.color_code
            AND opening.dye_lot_no IS NOT DISTINCT FROM movement.dye_lot_no
    )
    SELECT *
    FROM source_rolls
    WHERE expected_rolls IS NOT NULL
      AND expected_rolls <> TRUNC(expected_rolls)
      AND expected_rolls <> current_rolls
    """
)


def upgrade() -> None:
    op.alter_column(
        "inventory_document_line",
        "quantity_rolls",
        existing_type=sa.Integer(),
        type_=sa.Numeric(18, 2),
        existing_nullable=False,
        postgresql_using="quantity_rolls::numeric(18, 2)",
    )
    op.alter_column(
        "inventory_ledger_entry",
        "rolls_delta",
        existing_type=sa.Integer(),
        type_=sa.Numeric(18, 2),
        existing_nullable=False,
        postgresql_using="rolls_delta::numeric(18, 2)",
    )

    bind = op.get_bind()
    for row in bind.execute(FRACTIONAL_ROLLS).mappings():
        expected_rolls = Decimal(str(row["expected_rolls"]))
        if expected_rolls != expected_rolls.quantize(Decimal("0.01")):
            raise RuntimeError(
                "Historical roll quantity exceeds the supported two-decimal precision"
            )

        current_delta = Decimal(str(row["current_delta"]))
        new_delta = (
            -expected_rolls
            if row["movement_type"] in {"RAW_RETURN", "FINISHED_SHIPMENT"}
            else expected_rolls
        )
        delta_difference = new_delta - current_delta

        if delta_difference < 0 and row["opening_id"] is None:
            raise RuntimeError(
                "Cannot safely repair a historical outbound decimal roll without "
                "a matching reconciliation opening"
            )

        bind.execute(
            sa.text(
                "UPDATE inventory_document_line "
                "SET quantity_rolls = :expected_rolls "
                "WHERE id = :line_id"
            ),
            {"expected_rolls": expected_rolls, "line_id": row["line_id"]},
        )
        bind.execute(
            sa.text(
                "UPDATE inventory_ledger_entry "
                "SET rolls_delta = :new_delta "
                "WHERE id = :movement_id"
            ),
            {"new_delta": new_delta, "movement_id": row["movement_id"]},
        )
        if row["opening_id"] is not None:
            bind.execute(
                sa.text(
                    "UPDATE inventory_ledger_entry "
                    "SET rolls_delta = rolls_delta - :delta_difference "
                    "WHERE id = :opening_id"
                ),
                {
                    "delta_difference": delta_difference,
                    "opening_id": row["opening_id"],
                },
            )


def downgrade() -> None:
    bind = op.get_bind()
    for table_name, column_name in (
        ("inventory_document_line", "quantity_rolls"),
        ("inventory_ledger_entry", "rolls_delta"),
    ):
        has_fractional_values = bind.execute(
            sa.text(
                f"SELECT EXISTS (SELECT 1 FROM {table_name} "
                f"WHERE {column_name} <> TRUNC({column_name}))"
            )
        ).scalar_one()
        if has_fractional_values:
            raise RuntimeError(
                f"Cannot downgrade while {table_name}.{column_name} contains "
                "fractional roll quantities"
            )

    op.alter_column(
        "inventory_ledger_entry",
        "rolls_delta",
        existing_type=sa.Numeric(18, 2),
        type_=sa.Integer(),
        existing_nullable=False,
        postgresql_using="rolls_delta::integer",
    )
    op.alter_column(
        "inventory_document_line",
        "quantity_rolls",
        existing_type=sa.Numeric(18, 2),
        type_=sa.Integer(),
        existing_nullable=False,
        postgresql_using="quantity_rolls::integer",
    )
