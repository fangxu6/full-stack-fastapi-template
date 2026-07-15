import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import model_validator
from sqlmodel import Field, SQLModel

from app.models.inventory import InventoryDocumentType


class MasterUnitCreate(SQLModel):
    name: str = Field(min_length=1, max_length=255)


class MasterUnitUpdate(SQLModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    is_active: bool | None = None


class MasterUnitPublic(SQLModel):
    id: uuid.UUID
    name: str
    is_active: bool


class MasterUnitsPublic(SQLModel):
    data: list[MasterUnitPublic]
    count: int


class InventoryLineBase(SQLModel):
    item_name: str = Field(min_length=1, max_length=255)
    item_code: str | None = Field(default=None, max_length=255)
    wool_content: str = Field(min_length=1, max_length=255)
    color_code: str | None = Field(default=None, max_length=255)
    dye_lot_no: str | None = Field(default=None, max_length=255)
    quantity_meters: Decimal | None = Field(default=None, gt=0)


class InventoryLineCreate(InventoryLineBase):
    quantity_rolls: Decimal = Field(gt=0, max_digits=18, decimal_places=2)


class InventoryDocumentCreate(SQLModel):
    document_type: InventoryDocumentType
    business_date: date
    processing_unit_id: uuid.UUID
    receiving_unit_id: uuid.UUID | None = None
    document_number: str = Field(min_length=1, max_length=64)
    remarks: str | None = None
    lines: list[InventoryLineCreate] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_document(self) -> InventoryDocumentCreate:
        if self.document_type is InventoryDocumentType.FINISHED_SHIPMENT:
            if self.receiving_unit_id is None:
                raise ValueError("Finished shipments require a receiving unit")
            if any(line.quantity_meters is None for line in self.lines):
                raise ValueError("Finished shipments require meters on every line")
        elif self.receiving_unit_id is not None:
            raise ValueError("Only finished shipments accept a receiving unit")
        return self


class InventoryLinePublic(InventoryLineBase):
    id: uuid.UUID
    line_no: int
    quantity_rolls: Decimal = Field(ge=0, max_digits=18, decimal_places=2)


class InventoryDocumentPublic(SQLModel):
    id: uuid.UUID
    document_type: InventoryDocumentType
    business_date: date
    processing_unit_id: uuid.UUID
    receiving_unit_id: uuid.UUID | None
    document_number: str | None
    remarks: str | None
    deleted_at: datetime | None
    lines: list[InventoryLinePublic]


class InventoryDocumentsPublic(SQLModel):
    data: list[InventoryDocumentPublic]
    count: int


class InventoryLedgerEntryPublic(SQLModel):
    id: uuid.UUID
    ledger_kind: str
    movement_type: str
    business_date: date
    processing_unit_id: uuid.UUID
    document_line_id: uuid.UUID | None
    item_name: str
    item_code: str | None
    wool_content: str
    color_code: str | None
    dye_lot_no: str | None
    rolls_delta: Decimal
    meters_delta: Decimal
    reason: str | None


class InventoryLedgerEntriesPublic(SQLModel):
    data: list[InventoryLedgerEntryPublic]
    count: int


class InventoryBalancePublic(SQLModel):
    processing_unit_id: uuid.UUID
    item_name: str
    item_code: str | None = None
    wool_content: str
    color_code: str | None = None
    dye_lot_no: str | None = None
    rolls_balance: Decimal
    meters_balance: Decimal


class InventoryBalancesPublic(SQLModel):
    data: list[InventoryBalancePublic]
    count: int


class InventorySuggestionsPublic(SQLModel):
    data: list[str]
