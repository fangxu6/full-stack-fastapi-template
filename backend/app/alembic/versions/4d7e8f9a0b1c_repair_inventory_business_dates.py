"""repair inventory business dates from legacy workbook cells

Revision ID: 4d7e8f9a0b1c
Revises: 3b6f74e6d931
Create Date: 2026-07-15

"""

import re
from datetime import date, datetime
from decimal import Decimal

import sqlalchemy as sa
from alembic import op
from openpyxl.utils.datetime import CALENDAR_WINDOWS_1900, from_excel

revision = "4d7e8f9a0b1c"
down_revision = "3b6f74e6d931"
branch_labels = None
depends_on = None


SOURCE_ROWS = sa.text(
    """
    SELECT id, workbook_name, worksheet_name, source_row_number,
           raw_cells ->> '日期' AS raw_date
    FROM legacy_import_row AS source
    WHERE EXISTS (
        SELECT 1
        FROM inventory_ledger_entry AS entry
        WHERE entry.legacy_import_row_id = source.id
    )
    """
)


def _parse_source_date(value: object) -> date | None:
    text = str(value or "").strip()
    if not text:
        return None

    year_closing_match = re.fullmatch(r"(\d{4})年结存", text)
    if year_closing_match:
        return date(int(year_closing_match.group(1)), 12, 31)

    try:
        numeric_value = Decimal(text)
    except Exception:
        numeric_value = None
    if numeric_value is not None and 30_000 <= numeric_value <= 100_000:
        converted = from_excel(float(numeric_value), CALENDAR_WINDOWS_1900)
        return converted.date() if isinstance(converted, datetime) else converted

    slash_date_match = re.fullmatch(r"(\d{4})/(\d{1,2})/(\d{1,2})", text)
    if slash_date_match:
        return date(
            int(slash_date_match.group(1)),
            int(slash_date_match.group(2)),
            int(slash_date_match.group(3)),
        )

    try:
        return datetime.fromisoformat(text.replace("/", "-")).date()
    except ValueError:
        return None


def upgrade() -> None:
    bind = op.get_bind()
    for row in bind.execute(SOURCE_ROWS).mappings():
        business_date = _parse_source_date(row["raw_date"])
        if business_date is None:
            raise RuntimeError(
                "Cannot repair inventory business date for "
                f"{row['workbook_name']} / {row['worksheet_name']} / "
                f"row {row['source_row_number']}: {row['raw_date']!r}"
            )

        bind.execute(
            sa.text(
                """
                UPDATE inventory_document
                SET business_date = :business_date
                WHERE id IN (
                    SELECT line.document_id
                    FROM inventory_document_line AS line
                    JOIN inventory_ledger_entry AS entry
                      ON entry.document_line_id = line.id
                    WHERE entry.legacy_import_row_id = :source_id
                )
                """
            ),
            {"business_date": business_date, "source_id": row["id"]},
        )
        bind.execute(
            sa.text(
                """
                UPDATE inventory_ledger_entry
                SET business_date = :business_date
                WHERE legacy_import_row_id = :source_id
                """
            ),
            {"business_date": business_date, "source_id": row["id"]},
        )


def downgrade() -> None:
    raise RuntimeError(
        "Inventory business date repair is irreversible; restore the pre-migration "
        "database backup instead of downgrading."
    )
