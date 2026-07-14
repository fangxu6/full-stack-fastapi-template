# SQLModel exposes ORM columns as their Python value type to mypy, while this
# module must also pass SQLAlchemy column descriptors through ``Field``.
# mypy's current SQLModel overloads cannot represent that combination.
# mypy: disable-error-code=call-overload

import uuid
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Index,
    Numeric,
    UniqueConstraint,
)
from sqlalchemy import (
    Enum as SAEnum,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel

from app.models.base import get_datetime_utc


class InventoryDocumentType(StrEnum):
    RAW_RECEIPT = "RAW_RECEIPT"
    RAW_RETURN = "RAW_RETURN"
    FINISHED_SHIPMENT = "FINISHED_SHIPMENT"
    FINISHED_RECEIPT = "FINISHED_RECEIPT"


class InventoryLedgerKind(StrEnum):
    RAW = "RAW"
    FINISHED = "FINISHED"


class InventoryMovementType(StrEnum):
    RAW_RECEIPT = "RAW_RECEIPT"
    RAW_RETURN = "RAW_RETURN"
    FINISHED_RECEIPT = "FINISHED_RECEIPT"
    FINISHED_SHIPMENT = "FINISHED_SHIPMENT"
    MIGRATION_RECONCILIATION_OPENING = "MIGRATION_RECONCILIATION_OPENING"


class LegacyWorkbookKind(StrEnum):
    RAW = "RAW"
    FINISHED = "FINISHED"


class AuditFields(SQLModel):
    created_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # ty:ignore[invalid-argument-type]
        nullable=False,
    )
    created_by: uuid.UUID = Field(
        foreign_key="user.id", nullable=False, ondelete="RESTRICT"
    )
    updated_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # ty:ignore[invalid-argument-type]
        nullable=False,
    )
    updated_by: uuid.UUID = Field(
        foreign_key="user.id", nullable=False, ondelete="RESTRICT"
    )
    deleted_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),  # ty:ignore[invalid-argument-type]
        nullable=True,
    )


class ProcessingUnit(AuditFields, table=True):
    __tablename__ = "processing_unit"
    __table_args__ = (UniqueConstraint("normalized_name"),)

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str = Field(max_length=255)
    normalized_name: str = Field(max_length=255)
    is_active: bool = Field(default=True)


class ReceivingUnit(AuditFields, table=True):
    __tablename__ = "receiving_unit"
    __table_args__ = (UniqueConstraint("normalized_name"),)

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str = Field(max_length=255)
    normalized_name: str = Field(max_length=255)
    is_active: bool = Field(default=True)


class InventoryDocument(AuditFields, table=True):
    __tablename__ = "inventory_document"
    __table_args__ = (
        CheckConstraint(
            "(document_type = 'FINISHED_SHIPMENT' AND receiving_unit_id IS NOT NULL) "
            "OR (document_type <> 'FINISHED_SHIPMENT' AND receiving_unit_id IS NULL)",
            name="ck_inventory_document_receiving_unit",
        ),
        CheckConstraint(
            "is_legacy OR (document_number IS NOT NULL AND btrim(document_number) <> '')",
            name="ck_inventory_document_number",
        ),
        Index("ix_inventory_document_type_date", "document_type", "business_date"),
        Index(
            "ix_inventory_document_processing_date",
            "processing_unit_id",
            "business_date",
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    document_type: InventoryDocumentType = Field(
        sa_type=SAEnum(InventoryDocumentType, name="inventory_document_type")  # ty:ignore[invalid-argument-type]
    )
    business_date: date
    processing_unit_id: uuid.UUID = Field(
        foreign_key="processing_unit.id", nullable=False, ondelete="RESTRICT"
    )
    receiving_unit_id: uuid.UUID | None = Field(
        default=None, foreign_key="receiving_unit.id", ondelete="RESTRICT"
    )
    document_number: str | None = Field(default=None, max_length=64)
    remarks: str | None = None
    is_legacy: bool = Field(default=False)


class InventoryDocumentLine(AuditFields, table=True):
    __tablename__ = "inventory_document_line"
    __table_args__ = (
        UniqueConstraint("document_id", "line_no"),
        CheckConstraint("line_no > 0", name="ck_inventory_document_line_number"),
        CheckConstraint("quantity_rolls >= 0", name="ck_inventory_document_line_rolls"),
        CheckConstraint(
            "quantity_meters IS NULL OR quantity_meters > 0",
            name="ck_inventory_document_line_meters",
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    document_id: uuid.UUID = Field(
        foreign_key="inventory_document.id", nullable=False, ondelete="CASCADE"
    )
    line_no: int
    item_name: str = Field(max_length=255)
    item_code: str | None = Field(default=None, max_length=255)
    wool_content: str = Field(max_length=255)
    color_code: str | None = Field(default=None, max_length=255)
    dye_lot_no: str | None = Field(default=None, max_length=255)
    quantity_rolls: int
    quantity_meters: Decimal | None = Field(default=None, sa_type=Numeric(18, 3))  # ty:ignore[invalid-argument-type]


class InventoryImportBatch(AuditFields, table=True):
    __tablename__ = "inventory_import_batch"
    __table_args__ = (UniqueConstraint("source_fingerprint"),)

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    source_fingerprint: str = Field(max_length=64)
    raw_workbook_sha256: str = Field(max_length=64)
    finished_workbook_sha256: str = Field(max_length=64)
    importer_version: str = Field(max_length=64)
    reconciliation_report: dict[str, object] = Field(sa_type=JSONB)
    imported_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # ty:ignore[invalid-argument-type]
    )


class LegacyImportRow(AuditFields, table=True):
    __tablename__ = "legacy_import_row"
    __table_args__ = (
        UniqueConstraint(
            "import_batch_id", "workbook_kind", "worksheet_name", "source_row_number"
        ),
        CheckConstraint("source_row_number > 0", name="ck_legacy_import_row_number"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    import_batch_id: uuid.UUID = Field(
        foreign_key="inventory_import_batch.id", nullable=False, ondelete="RESTRICT"
    )
    workbook_kind: LegacyWorkbookKind = Field(
        sa_type=SAEnum(LegacyWorkbookKind, name="legacy_workbook_kind")  # ty:ignore[invalid-argument-type]
    )
    workbook_name: str = Field(max_length=255)
    worksheet_name: str = Field(max_length=255)
    source_row_number: int
    raw_cells: dict[str, object] = Field(sa_type=JSONB)
    source_balance_snapshot: dict[str, object] = Field(sa_type=JSONB)
    requires_cleanup: bool = Field(default=False)


class InventoryLedgerEntry(AuditFields, table=True):
    __tablename__ = "inventory_ledger_entry"
    __table_args__ = (
        UniqueConstraint("document_line_id"),
        CheckConstraint(
            "(movement_type = 'MIGRATION_RECONCILIATION_OPENING' "
            "AND document_line_id IS NULL AND import_batch_id IS NOT NULL) "
            "OR (movement_type <> 'MIGRATION_RECONCILIATION_OPENING' "
            "AND document_line_id IS NOT NULL)",
            name="ck_inventory_ledger_entry_source",
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    ledger_kind: InventoryLedgerKind = Field(
        sa_type=SAEnum(InventoryLedgerKind, name="inventory_ledger_kind")  # ty:ignore[invalid-argument-type]
    )
    movement_type: InventoryMovementType = Field(
        sa_type=SAEnum(InventoryMovementType, name="inventory_movement_type")  # ty:ignore[invalid-argument-type]
    )
    business_date: date
    processing_unit_id: uuid.UUID = Field(
        foreign_key="processing_unit.id", nullable=False, ondelete="RESTRICT"
    )
    document_line_id: uuid.UUID | None = Field(
        default=None, foreign_key="inventory_document_line.id", ondelete="RESTRICT"
    )
    legacy_import_row_id: uuid.UUID | None = Field(
        default=None, foreign_key="legacy_import_row.id", ondelete="RESTRICT"
    )
    import_batch_id: uuid.UUID | None = Field(
        default=None, foreign_key="inventory_import_batch.id", ondelete="RESTRICT"
    )
    item_name: str = Field(max_length=255)
    item_code: str | None = Field(default=None, max_length=255)
    wool_content: str = Field(max_length=255)
    color_code: str | None = Field(default=None, max_length=255)
    dye_lot_no: str | None = Field(default=None, max_length=255)
    rolls_delta: int
    meters_delta: Decimal = Field(default=Decimal("0"), sa_type=Numeric(18, 3))  # ty:ignore[invalid-argument-type]
    reason: str | None = None
