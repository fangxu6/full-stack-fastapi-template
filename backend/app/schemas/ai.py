import uuid
from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

from app.models.inventory import InventoryDocumentType, InventoryLedgerKind
from app.schemas.inventory import (
    InventoryBalancesPublic,
    InventoryDocumentsPublic,
    InventoryLedgerEntriesPublic,
    MasterUnitsPublic,
)


class AiInventoryQueryRequest(BaseModel):
    question: str = Field(min_length=1, max_length=1_000)


class AiInventoryCitation(BaseModel):
    source: str
    summary: str


class AiInventoryQueryResponse(BaseModel):
    run_id: uuid.UUID
    answer: str
    citations: list[AiInventoryCitation]


class AiInternalBalancesRequest(BaseModel):
    run_id: uuid.UUID
    actor_user_id: uuid.UUID
    ledger_kind: InventoryLedgerKind
    skip: int = Field(default=0, ge=0)
    limit: int = Field(default=20, ge=1, le=20)
    processing_unit_id: uuid.UUID | None = None
    item_name: str | None = Field(default=None, min_length=1, max_length=255)


class AiInternalBalancesResponse(BaseModel):
    tool_name: Literal["balances"]
    source: Literal["inventory:balances"]
    result: InventoryBalancesPublic


class AiInternalUnitsRequest(BaseModel):
    run_id: uuid.UUID
    actor_user_id: uuid.UUID
    skip: int = Field(default=0, ge=0)
    limit: int = Field(default=20, ge=1, le=20)
    name: str | None = Field(default=None, min_length=1, max_length=255)
    is_active: bool | None = None


class AiInternalUnitsResponse(BaseModel):
    tool_name: Literal["processing_units", "receiving_units"]
    source: Literal["inventory:processing_units", "inventory:receiving_units"]
    result: MasterUnitsPublic


class AiInternalDocumentsRequest(BaseModel):
    run_id: uuid.UUID
    actor_user_id: uuid.UUID
    skip: int = Field(default=0, ge=0)
    limit: int = Field(default=20, ge=1, le=20)
    document_type: InventoryDocumentType | None = None
    business_date_from: date | None = None
    business_date_to: date | None = None
    processing_unit_id: uuid.UUID | None = None
    receiving_unit_id: uuid.UUID | None = None
    document_number: str | None = Field(default=None, min_length=1, max_length=64)


class AiInternalDocumentsResponse(BaseModel):
    tool_name: Literal["documents"]
    source: Literal["inventory:documents"]
    result: InventoryDocumentsPublic


class AiInternalLedgerRequest(BaseModel):
    run_id: uuid.UUID
    actor_user_id: uuid.UUID
    ledger_kind: InventoryLedgerKind
    processing_unit_id: uuid.UUID
    item_name: str = Field(min_length=1, max_length=255)
    wool_content: str = Field(min_length=1, max_length=255)
    skip: int = Field(default=0, ge=0)
    limit: int = Field(default=20, ge=1, le=20)
    item_code: str | None = Field(default=None, max_length=255)
    color_code: str | None = Field(default=None, max_length=255)
    dye_lot_no: str | None = Field(default=None, max_length=255)


class AiInternalLedgerResponse(BaseModel):
    tool_name: Literal["ledger"]
    source: Literal["inventory:ledger"]
    result: InventoryLedgerEntriesPublic
