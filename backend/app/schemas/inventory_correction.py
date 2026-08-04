import uuid
from datetime import UTC, date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from sqlmodel import SQLModel
from sqlmodel._compat import SQLModelConfig

from app.models.inventory import (
    InventoryCorrectionAttemptOrigin,
    InventoryCorrectionAttemptStatus,
    InventoryCorrectionFailureCategory,
    InventoryCorrectionOperation,
    InventoryCorrectionRequestStatus,
    InventoryCorrectionWorkItemStatus,
    InventoryDocumentType,
)
from app.schemas.inventory import InventoryLineCreate


class InventoryCorrectionLineProposal(InventoryLineCreate):
    model_config = SQLModelConfig(extra="forbid", str_strip_whitespace=True)


class InventoryCorrectionDocumentProposal(SQLModel):
    model_config = SQLModelConfig(extra="forbid", str_strip_whitespace=True)

    document_type: InventoryDocumentType
    business_date: date
    processing_unit_id: uuid.UUID
    receiving_unit_id: uuid.UUID | None = None
    document_number: str = Field(min_length=1, max_length=64)
    remarks: str | None = None
    lines: list[InventoryCorrectionLineProposal] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_document(self) -> InventoryCorrectionDocumentProposal:
        if self.document_type is InventoryDocumentType.FINISHED_SHIPMENT:
            if self.receiving_unit_id is None:
                raise ValueError("Finished shipments require a receiving unit")
            if any(line.quantity_meters is None for line in self.lines):
                raise ValueError("Finished shipments require meters on every line")
        elif self.receiving_unit_id is not None:
            raise ValueError("Only finished shipments accept a receiving unit")
        return self


class InventoryCorrectionRequestCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    document_id: uuid.UUID
    operation: InventoryCorrectionOperation
    expected_updated_at: datetime
    proposal: InventoryCorrectionDocumentProposal | None = None
    reason: str = Field(min_length=1, max_length=500)

    @field_validator("expected_updated_at")
    @classmethod
    def validate_expected_updated_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("expected_updated_at must be timezone-aware")
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def validate_operation_proposal(self) -> InventoryCorrectionRequestCreate:
        if self.operation is InventoryCorrectionOperation.UPDATE_DOCUMENT:
            if self.proposal is None:
                raise ValueError("UPDATE_DOCUMENT requires a proposal")
        elif self.proposal is not None:
            raise ValueError("Only UPDATE_DOCUMENT accepts a proposal")
        return self


class InventoryCorrectionAttemptPublic(SQLModel):
    id: int
    sequence: int
    origin: InventoryCorrectionAttemptOrigin
    status: InventoryCorrectionAttemptStatus
    scheduler_run_id: int | None
    started_at: datetime | None
    finished_at: datetime | None
    failure_category: InventoryCorrectionFailureCategory | None


class InventoryCorrectionWorkItemPublic(SQLModel):
    id: int
    request_id: int
    document_id: uuid.UUID
    expected_updated_at: datetime
    proposal_hash: str
    handler_type: str
    status: InventoryCorrectionWorkItemStatus
    current_attempt_sequence: int
    terminal_failure_category: InventoryCorrectionFailureCategory | None
    attempts: list[InventoryCorrectionAttemptPublic]
    created_at: datetime
    updated_at: datetime


class InventoryCorrectionRequestPublic(SQLModel):
    id: int
    document_id: uuid.UUID
    operation: InventoryCorrectionOperation
    expected_updated_at: datetime
    proposal: dict[str, object] | None
    proposal_hash: str
    reason: str
    status: InventoryCorrectionRequestStatus
    reviewer_id: uuid.UUID | None
    decided_at: datetime | None
    work_item: InventoryCorrectionWorkItemPublic | None = None
    created_at: datetime
    updated_at: datetime


class InventoryCorrectionRequestsPublic(SQLModel):
    data: list[InventoryCorrectionRequestPublic]
    count: int


class InventoryCorrectionWorkItemsPublic(SQLModel):
    data: list[InventoryCorrectionWorkItemPublic]
    count: int
