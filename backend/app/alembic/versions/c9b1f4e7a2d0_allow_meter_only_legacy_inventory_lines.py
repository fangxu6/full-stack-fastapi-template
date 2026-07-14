"""allow meter-only legacy inventory lines

Revision ID: c9b1f4e7a2d0
Revises: 9d7ba96f52cd
Create Date: 2026-07-14

"""

from alembic import op


revision = "c9b1f4e7a2d0"
down_revision = "9d7ba96f52cd"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint(
        "ck_inventory_document_line_rolls",
        "inventory_document_line",
        type_="check",
    )
    op.create_check_constraint(
        "ck_inventory_document_line_rolls",
        "inventory_document_line",
        "quantity_rolls >= 0",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_inventory_document_line_rolls",
        "inventory_document_line",
        type_="check",
    )
    op.create_check_constraint(
        "ck_inventory_document_line_rolls",
        "inventory_document_line",
        "quantity_rolls > 0",
    )
